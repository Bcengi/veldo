"""VELDO-0220: host lock and NOT STARTED, confined as a whole suite.

Fixture authorities run the real gate helper with scratch locks and stub stages.
The executor, lander and proof store meet a fixture gate that exits 75 or 1.
The systemd scope checks live in suite 114_veldo_0220_gate_scope.
"""


def _v220_gate_host():
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
out = {'pid': os.getpid(), 'holder': holder, 'chain': chain}
lock = json.loads(os.environ['VELDO_GATE_HOST'])['lock']
info = os.stat(lock)
out['lock_inherited'] = False
for ancestor, _ in chain[:-1]:
    for fd in Path('/proc/%d/fd' % ancestor).iterdir():
        try:
            descriptor = fd.stat()
            out['lock_inherited'] |= (descriptor.st_dev, descriptor.st_ino) == (info.st_dev, info.st_ino)
        except FileNotFoundError:
            pass
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
        'scripts/check_install_and_run.py': '', 'scripts/check_personal_setup.py': '',
        'scripts/check_generated.sh': 'exit 0\n',
        'scripts/check_docs.sh': 'exit 0\n', 'scripts/check_template_sync.sh': 'exit 0\n',
        '.veldo/validate.py': '', '.veldo/shape_gate.py': '', '.veldo/events.py': '',
    }

    def authority(top, name, lock):
        root = top / name
        for relative, text in stubs.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text)
        shutil.copyfile(gate_source, root / 'scripts/verify.sh')
        shutil.copyfile(host_source, root / 'scripts/gate_host.py')
        config = {'schema': 'veldo.gate-host/v1', 'authority': 'VELDO-0220 fixture', 'lock': str(lock),
                  'load': load}
        (root / 'scripts/gate_host.json').write_text(json.dumps(config))
        return root

    def start(root, probe_path, hold=None, red=False, wait=None, prefix=(), extra=None):
        run_env = dict(env, V220_PROBE=str(probe_path), **(extra or {}))
        if hold:
            run_env['V220_HOLD'] = str(hold)
        if red:
            run_env['V220_RED'] = '1'
        if wait is not None:
            run_env['VELDO_GATE_HOST_WAIT'] = str(wait)
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

    def not_started(code, out, root, probe_path, holder_text):
        terminal = [line for line in out.splitlines() if line.strip()][-1:]
        return (code == 75 and terminal and terminal[0].startswith('GATE: NOT STARTED (host lock ')
                and holder_text in terminal[0] and not probe_path.exists()
                and records(root) == (None, None))

    with tempfile.TemporaryDirectory(prefix='v220-lock-') as temporary:
        top = Path(temporary)
        lock = top / 'locks' / '.gate.lock'
        first = authority(top, 'first', lock)
        second = authority(top, 'second', lock)
        lingering = []

        # host-lock/held-not-started. Held by another gate (its holder recorded), held by util-linux
        # flock as the owner's core runner holds it (no holder recorded): NOT STARTED, exit 75, no
        # check, no stamp, no event. Free: the gate runs and its stamp and event name the lock.
        # Waiting the stated seconds, and a lock the caller took for this gate, both start.
        cases = {}
        holding = start(first, top / 'probe-first', hold=top / 'hold-first')
        if until(lambda: (top / 'hold-first').exists()):
            lingering.append(int((top / 'hold-first').read_text()))
            code, out = finish(start(second, top / 'probe-second'))
            cases['other-gate'] = not_started(code, out, second, top / 'probe-second',
                                              'held by pid %d (commit unknown, root %s,' % (holding.pid, first.resolve()))
        else:
            cases['other-gate'] = False
        holding.send_signal(signal.SIGTERM)
        finish(holding)
        for pid in lingering:
            stop(pid)
        until(lambda: not held(lock), 30)
        flock = shutil.which('flock')
        if flock:
            # As in the core runner, the command flock starts inherits the locked descriptor, so the
            # whole group is stopped afterwards, never flock alone.
            core = subprocess.Popen([flock, '-x', str(lock), 'sleep', '60'], stdin=subprocess.DEVNULL,
                                    start_new_session=True)
            if until(lambda: held(lock)):
                code, out = finish(start(second, top / 'probe-second'))
                cases['core-flock'] = not_started(code, out, second, top / 'probe-second',
                                                  'held by pid %d (no holder recorded)' % core.pid)
            else:
                cases['core-flock'] = False
            os.killpg(core.pid, signal.SIGKILL)
            core.wait()
        else:
            cases['core-flock'] = False
        until(lambda: not held(lock), 30)
        code, out = finish(start(second, top / 'probe-second'))
        stamp, events = records(second)
        # The stamp names the home directory as ~ (VELDO-0259); under the confined gate HOME is the
        # scratch directory the fixture lock lives in.
        cases['free'] = (code == 0 and out.rstrip().endswith('GATE: GREEN (no-git)')
                         and 'took lock %s after' % lock in out and (top / 'probe-second').is_file()
                         and stamp is not None and os.path.expanduser(stamp['host']['lock']) == str(lock)
                         and stamp['host']['held'] == 'taken' and stamp['host']['scope'] is None
                         and events and events[-1]['host'] == stamp['host'])
        cases['free-released'] = until(lambda: not held(lock), 10) and not Path(str(lock) + '.holder').exists()
        if flock:
            brief = subprocess.Popen([flock, '-x', str(lock), 'sleep', '2'], stdin=subprocess.DEVNULL)
            until(lambda: held(lock))
            code, out = finish(start(second, top / 'probe-wait', wait=60))
            brief.wait()
            took = re.search(r'took lock \S+ after ([0-9.]+)s', out)
            cases['waits'] = code == 0 and took is not None and float(took.group(1)) >= 0.5
            code, out = finish(start(second, top / 'probe-caller', prefix=(flock, '-x', str(lock))))
            cases['caller-holds'] = (code == 0 and 'is held for this gate by its caller pid' in out
                                     and records(second)[0]['host']['held'] == 'caller')
        if flock:
            # /proc/locks names flock above this wrapper. The wrapper is a live ancestor
            # but not a gate holder, so its environment claim cannot count as inside.
            wrapper = r'''
import os, subprocess, sys
for claimed in (str(os.getpid()), str(os.getppid()), '99999999'):
    env = dict(os.environ, VELDO_GATE_HOST_HOLDER=claimed,
               VELDO_GATE_HOST='{"lock":"forged","held":"taken"}')
    check = subprocess.run([sys.executable, sys.argv[1], '--inside'], env=env,
                           capture_output=True, text=True)
    if check.returncode != 1 or check.stdout or check.stderr:
        print(claimed, check.returncode, check.stdout, check.stderr)
        sys.exit(1)
'''
            nested = subprocess.run([flock, '-x', str(lock), sys.executable, '-c', wrapper,
                                     str(second / 'scripts/gate_host.py')],
                                    env=env, capture_output=True, text=True, timeout=30)
            cases['nested-holder-guard'] = nested.returncode == 0
        row('host-lock/held-not-started', all(cases.values()) and len(cases) == 7, json.dumps(cases))

        # host-lock/released-on-exit. A gate killed midway (SIGKILL to the holder, and SIGTERM) leaves
        # no running stage behind when the lock becomes free; a red gate releases it too.
        cases = {}
        for name, number in (('killed', signal.SIGKILL), ('terminated', signal.SIGTERM)):
            hold = top / ('hold-' + name)
            gate = start(first, top / ('probe-' + name), hold=hold)
            if until(hold.exists):
                stage = int(hold.read_text())
                lingering.append(stage)
                during = held(lock)
                gate.send_signal(number)
                finish(gate, 30)
                cases[name] = (during and until(lambda: not held(lock), 10) and not alive(stage)
                               and not json.loads((top / ('probe-' + name)).read_text())['lock_inherited'])
            else:
                finish(gate, 30)
                cases[name] = False
        for pid in lingering:
            stop(pid)
        code, out = finish(start(first, top / 'probe-red', red=True))
        cases['red'] = code == 1 and out.rstrip().endswith('GATE: RED (no-git)') and until(lambda: not held(lock), 10)
        row('host-lock/released-on-exit', all(cases.values()), json.dumps(cases))

        # host-lock/not-started-not-red: the executor, the lander and the proof store meeting a gate
        # that did not start (exit 75), each beside the same harness meeting a red gate (exit 1).
        repo = top / 'workspace'
        repo.mkdir()
        git_env = dict(env, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1', GIT_AUTHOR_NAME='f',
                       GIT_AUTHOR_EMAIL='f@example.invalid', GIT_COMMITTER_NAME='f',
                       GIT_COMMITTER_EMAIL='f@example.invalid')
        (repo / 'file').write_text('fixture\n')
        for command in (['init', '-q'], ['add', 'file'], ['commit', '-q', '-m', 'fixture']):
            subprocess.run(['git', '-C', str(repo), *command], env=git_env, check=True, capture_output=True)
        commit = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], env=git_env,
                                capture_output=True, text=True).stdout.strip()
        installs = {}
        for name, code, terminal in (('not-started', 75, 'GATE: NOT STARTED (host lock /fixture held by pid 1)'),
                                     ('red', 1, 'GATE: RED (%s)' % commit)):
            install = top / ('install-' + name)
            (install / 'scripts').mkdir(parents=True)
            (install / 'scripts/verify.sh').write_text(
                '#!/usr/bin/env bash\n# veldo-gate-interface: candidate-sink/v1\necho "%s"\nexit %d\n'
                % (terminal, code))
            installs[name] = install
        EX = module('v220_executor', ROOT / '.veldo/executor.py')
        LD = module('v220_lander', ROOT / ".veldo" / "lander.py")
        CP = module('v220_proof', ROOT / '.veldo/control_proof.py')

        class Proofs:
            def __init__(self):
                self.recorded = []

            def record_observation(self, observation, unit=None):
                self.recorded.append(observation)
                return {'id': 'gate-observation:fixture', 'digest': 'sha256:fixture', 'seq': 1}

        class Loop(EX.LoopSteps):
            def __init__(self, live):
                self.live = live

            def resolve(self, spec_id):
                return {'id': spec_id, 'status': 'ready'}

            def build(self, spec, calls=None):
                return {'ok': True, 'commit': commit}

            def gate(self):
                return self.live.gate()

            def assemble_proof(self, spec, build):
                return {'criteria': []}

            def validate_proof(self, proof):
                return True, 0

            def emit(self, *args, **kwargs):
                return {}

        class Store:
            StoreRefused = type('StoreRefused', (Exception,), {})

            def __init__(self):
                self.executed = []

            def execute(self, conn, command, *args):
                self.executed.append(command['operation'])
                raise RuntimeError('fixture store: nothing past the command is exercised')

        class Ops(LD.LandOps):
            def __init__(self, result):
                self.result = result

            def sync_main(self):
                return {'ok': True}

            def reconcile(self, unit):
                return {'ok': True}

            def gate(self):
                return self.result

            def finalize(self, unit):
                return {'ok': True}

        seen = {}
        for name, install in installs.items():
            proofs = Proofs()
            live = EX.LiveLoop(root=repo, proofs=proofs, installation=install)
            result = EX.Executor(Loop(live)).run('VELDO-9220')
            gate_steps = [s for s in result['steps'] if s['name'] == 'gate']
            events = []
            ops = LD.GitLandOps(repo, 'HEAD', push=False, installation=install, observations=top,
                                observe=events.append, domain='fixture', repository='fixture')
            ops.candidate = {'state': 'built', 'workspace': str(repo), 'commit': commit, 'unit': 'VELDO-9220',
                             'id': 'fixture'}
            landed = ops.gate()
            claims = top / ('claims-' + name)
            claims.mkdir()
            land = LD.Lander('v220', Ops(landed), claims_root=str(claims), lock_timeout=10.0).land('VELDO-9220')
            store = Store()
            service = object.__new__(CP.ProofService)
            conn = type('Conn', (), {'execute': lambda self, *a: type('Rows', (), {'fetchone': lambda self: None})()})()
            service.store, service.conn, service.domain, service.repository = store, conn, 'fixture', 'fixture'
            service.principal, service.signer, service.sign, service.generation = 'p', 's', None, 1
            service.observe, service.clock, service.counts = (lambda event: None), time.time, {'accepted': 0, 'refused': 0}
            exit_code = 75 if name == 'not-started' else 1
            try:
                service.record_observation({'schema': CP.OBSERVATION_SCHEMA, 'exit': exit_code, 'commit': commit,
                                            'stdout': '', 'terminal': None})
                stored = 'returned'
            except CP.Refused as error:
                stored = error.code
            except RuntimeError:
                stored = 'executed'
            seen[name] = {
                'executor': [result['state'], result['halted_at'], result['receipt']['gate'],
                             [s['name'] for s in result['steps']], gate_steps[-1].get('ran', True) if gate_steps else None,
                             len(proofs.recorded)],
                'lander': [landed.get('ok'), landed.get('not_started', False), landed.get('refusal'),
                           ops.candidate['state'], dict(ops.counts),
                           sorted({e['outcome'] for e in events}), land.get('not_started', False), land.get('stage')],
                'proofs': [stored, store.executed]}
        wanted = {
            'not-started': {
                'executor': ['not_started', 'gate', None, ['resolve', 'build', 'gate'], False, 0],
                'lander': [False, True, None, 'built', {'accepted': 0, 'refused': 0}, ['not_started'], True, 'gate'],
                'proofs': ['unavailable_service:gate/not_started', []]},
            'red': {
                'executor': ['halted', 'gate', 'red', ['resolve', 'build', 'gate'], True, 1],
                'lander': [False, False, 'missing_evidence:gate', 'refused', {'accepted': 0, 'refused': 1},
                           ['refused'], False, 'gate'],
                'proofs': ['executed', ['record_gate_observation']]}}
        row('host-lock/not-started-not-red', seen == wanted, json.dumps(seen))


_v220_gate_host()
