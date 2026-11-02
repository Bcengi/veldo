"""VELDO-0220: the gate's own delegated scope and custody through teardown.

This whole suite needs the systemd user manager and is listed unconfined.
Fixtures use scratch locks, real gate helpers and stub stages. Creation is checked
outside and inside another scope; teardown is checked on kill, termination,
normal completion and a red stage, including a worker in a separate session.
"""


def _v220_gate_scope():
    import fcntl
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import time

    gate_source = ROOT / "scripts" / "verify.sh"
    host_source = ROOT / "scripts" / "gate_host.py"
    stated = json.loads((ROOT / 'scripts/gate_host.json').read_text())
    load = {'cores': 1, 'memory': '1G', 'source': 'fixture'}

    def row(name, condition, detail=''):
        expect('VELDO-0220 ' + name + (': ' + detail if detail and not condition else ''), condition)

    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    # A fixture gate only ever sees its own configuration: the variables a real gate's holder hands
    # its children (and the caller's wait) are dropped, so running inside a real gate changes nothing.
    env = {k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')}
    # Mutation workers start with a clean environment. Name the owner's runtime
    # directory explicitly, as the other suites that use the user manager do.
    env['XDG_RUNTIME_DIR'] = env.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    probe = r'''
import json, os, signal, subprocess, sys, time
from pathlib import Path
def cgroup(pid):
    try:
        return Path('/proc/%d/cgroup' % pid).read_text().split('::', 1)[1].strip()
    except (OSError, IndexError):
        return None
def parent(pid):
    try:
        return int(Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[1])
    except (OSError, IndexError, ValueError):
        return 0
holder = int(os.environ.get('VELDO_GATE_HOST_HOLDER') or 0)
chain, pid = [], os.getpid()
while pid > 1:
    chain.append([pid, cgroup(pid)])
    if pid == holder:
        break
    pid = parent(pid)
def descends(pid):
    while pid > 1:
        if pid == holder:
            return True
        pid = parent(pid)
    return False
out = {'pid': os.getpid(), 'holder': holder, 'chain': chain, 'scope': os.environ.get('VELDO_GATE_SCOPE'),
       'oom': int(Path('/proc/self/oom_score_adj').read_text())}
if out['scope']:
    base = Path('/sys/fs/cgroup') / out['scope'].lstrip('/')
    children = Path('/proc/%d/task/%d/children' % (holder, holder)).read_text().split()
    out['keepers'] = [int(pid) for pid in children if cgroup(int(pid)) != out['scope'] + '/gate']
    out['memory_max'] = (base / 'memory.max').read_text().strip()
    out['subtree'] = (base / 'cgroup.subtree_control').read_text().split()
    procs = {}
    for directory, _, _ in os.walk(base):
        for number in Path(directory, 'cgroup.procs').read_text().split():
            procs[number] = os.path.relpath(directory, base)
    out['procs'] = procs
    out['outsiders'] = [p for p in procs if not descends(int(p))]
    child = base / 'v220-worker'
    try:
        child.mkdir()
        out['child'] = (child / 'memory.max').is_file() and (child / 'cpu.stat').is_file()
        child.rmdir()
    except OSError as error:
        out['child'] = str(error)
if os.environ.get('V220_LINGER') and out['scope']:
    child = subprocess.Popen([sys.executable, '-c',
        'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(90)'],
        start_new_session=True)
    out['escaped'] = child.pid
    worker = base / 'escaped-worker'
    worker.mkdir()
    (worker / 'cgroup.procs').write_text(str(child.pid))
Path(os.environ['V220_PROBE']).write_text(json.dumps(out))
if os.environ.get('V220_HOLD'):
    Path(os.environ['V220_HOLD']).write_text(str(os.getpid()))
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        time.sleep(0.1)
sys.exit(1 if os.environ.get('V220_RED') else 0)
'''
    stubs = {
        'scripts/gate_candidate.py': 'import subprocess, sys\na = sys.argv\n'
                                     'sys.exit(subprocess.run(a[a.index("--") + 1:]).returncode)\n',
        'scripts/check_gate_mutations.py': 'import sys\nsys.exit(0)\n',
        'scripts/reuse_stamp.py': 'print(\'"force_fresh":false,"reused":{"mutation":0,"unit":0}\')\n',
        'scripts/v220_probe.py': probe,
        'scripts/check_lint.sh': 'exec python3 scripts/v220_probe.py\n',
        'scripts/selftest.py': '', 'scripts/check_first_use.py': '', 'scripts/secret_inventory.py': '',
        'scripts/check_install_and_run.py': '', 'scripts/check_generated.sh': 'exit 0\n',
        'scripts/check_docs.sh': 'exit 0\n', 'scripts/check_template_sync.sh': 'exit 0\n',
        '.veldo/validate.py': '', '.veldo/shape_gate.py': '', '.veldo/events.py': '',
    }

    def authority(top, name, lock, scope):
        root = top / name
        for relative, text in stubs.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text)
        shutil.copyfile(gate_source, root / 'scripts/verify.sh')
        shutil.copyfile(host_source, root / 'scripts/gate_host.py')
        config = {'schema': 'veldo.gate-host/v1', 'authority': 'VELDO-0220 fixture', 'lock': str(lock),
                  'load': load}
        config['scope'] = scope
        (root / 'scripts/gate_host.json').write_text(json.dumps(config))
        return root

    def start(root, probe_path, hold=None, red=False, prefix=(), extra=None):
        run_env = dict(env, V220_PROBE=str(probe_path), **(extra or {}))
        if hold:
            run_env['V220_HOLD'] = str(hold)
        if red:
            run_env['V220_RED'] = '1'
        # The output goes to a file, never a pipe: a stage a killed gate leaves running would hold a
        # pipe open, and reading it would wait for that stage rather than the gate.
        log = Path(str(probe_path) + '.log')
        with open(log, 'w') as handle:
            process = subprocess.Popen([*prefix, 'bash', str(root / 'scripts/verify.sh')], cwd=str(root.parent),
                                       env=run_env, stdout=handle, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, pass_fds=launcher_fds())
        process.log = log
        return process

    def finish(process, timeout=180):
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return process.returncode, process.log.read_text()

    def held(lock):
        """Whether someone holds the lock now; this check never keeps it."""
        fd = os.open(str(lock), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o664)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return False
        except BlockingIOError:
            return True
        finally:
            os.close(fd)

    def until(predicate, seconds=60):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if predicate():
                return True
            time.sleep(0.05)
        return predicate()

    def alive(pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        try:
            return Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0] != 'Z'
        except FileNotFoundError:
            return False

    def state(pid):
        """The process state letter, or None once it is gone."""
        try:
            return Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[0]
        except (FileNotFoundError, ProcessLookupError):
            return None

    def stop(pid):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    def records(root):
        stamp = root / '.veldo/last_verify'
        events = root / '.veldo/events.jsonl'
        return (json.loads(stamp.read_text()) if stamp.is_file() else None,
                [json.loads(line) for line in events.read_text().splitlines()] if events.is_file() else None)

    with tempfile.TemporaryDirectory(prefix='v220-scope-') as temporary:
        top = Path(temporary)
        scoped = authority(top, 'scoped', top / 'locks' / '.scope.lock', scope=stated['scope'])
        limit = str(module('v220_host', host_source).load(scoped / 'scripts/gate_host.json')['scope']['memory_max'])
        own = Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip()
        cases, seen = {}, {}
        caller = 'v220-caller-%d.scope' % os.getpid()
        for name, prefix in (('outside', ()), ('inside-a-scope', (
                'systemd-run', '--user', '--scope', '--quiet', '--collect', '--unit', caller,
                '-p', 'MemoryMax=1G'))):
            probe_path = top / ('probe-scope-' + name)
            gate = start(scoped, probe_path, prefix=prefix)
            code, out = finish(gate)
            seen[name] = got = json.loads(probe_path.read_text()) if probe_path.is_file() else {}
            scope = got.get('scope') or ''
            stamp = records(scoped)[0] or {}
            cases[name] = bool(
                code == 0 and re.fullmatch(r'.*/veldo-gate-[0-9]+-[0-9a-f]+\.scope', scope)
                and scope != own and not scope.endswith('/' + caller)
                and got.get('memory_max') == limit and got.get('oom') == stated['scope']['oom_score_adj']
                and got['chain'][-1][0] == gate.pid and got['holder'] == gate.pid
                and all(cg == scope + '/gate' for _, cg in got['chain'])
                and set(got['procs'].values()) == {'gate'} and got['outsiders'] == []
                and {'cpu', 'memory', 'pids'} <= set(got['subtree']) and got['child'] is True
                and stamp.get('host', {}).get('scope') == scope.rsplit('/', 1)[1]
                and stamp['host'].get('memory_max') == int(limit)
                and ('running in scope %s' % scope.rsplit('/', 1)[1]) in out
                and until(lambda: not Path('/sys/fs/cgroup' + scope).exists(), 15))
            if not cases[name]:
                seen[name] = dict(got, exit=code, out=out[-1500:])
        # Scope teardown must also reach a worker in another session and a delegated child
        # cgroup. Check the first instant we can take the lock, before any test cleanup.
        for name, number, red in (('killed', signal.SIGKILL, False),
                                  ('terminated', signal.SIGTERM, False),
                                  ('normal', None, False), ('red', None, True)):
            probe_path = top / ('probe-cleanup-' + name)
            hold = top / ('hold-cleanup-' + name) if number else None
            gate = start(scoped, probe_path, hold=hold, red=red, extra={'V220_LINGER': '1'})
            got = {}
            ready = until(lambda: (hold.exists() if hold else probe_path.exists())
                          or gate.poll() is not None) and probe_path.exists()
            if ready:
                got = json.loads(probe_path.read_text())
                custody = True
                if number:
                    keepers = got.get('keepers', [])
                    # A keeper that vanishes while stopped is recorded and reds the row; it never
                    # crashes the suite before the evidence is written.
                    evidence = got['keeper_evidence'] = {}
                    if len(keepers) == 1:
                        os.kill(keepers[0], signal.SIGSTOP)
                        evidence['stopped'] = until(lambda: state(keepers[0]) == 'T', 5)
                        evidence['before_signal'] = state(keepers[0])
                    try:
                        gate.send_signal(number)
                        finish(gate, 10)
                        custody = len(keepers) == 1 and held(top / 'locks' / '.scope.lock')
                    finally:
                        evidence['at_resume'] = [state(keeper) for keeper in keepers]
                        for keeper in keepers:
                            try:
                                os.kill(keeper, signal.SIGCONT)
                            except ProcessLookupError:
                                custody = False
                released = until(lambda: not held(top / 'locks' / '.scope.lock'), 10)
                dead = bool(got.get('escaped')) and not alive(got['escaped']) and not alive(got['pid'])
                cases['cleanup-' + name] = custody and released and dead
            else:
                cases['cleanup-' + name] = False
            code, out = finish(gate, 10)
            if not number:
                cases['cleanup-' + name] &= code == int(red)
            seen['cleanup-' + name] = dict(got, exit=code, out=out[-1500:])
            for key in ('escaped', 'pid'):
                if got.get(key):
                    stop(got[key])
            until(lambda: not held(top / 'locks' / '.scope.lock'), 10)
        row('host-scope/own-scope', all(cases.values()), json.dumps({'cases': cases, 'seen': seen}))


_v220_gate_scope()
