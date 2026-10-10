#!/usr/bin/env python3
"""Native evidence. Never run by a Linux suite and never emits qualification.

/opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py lifecycle [engine]
/opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py containment [engine]
/opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py engines /absolute/candidate.json

Lifecycle and containment use synthetic engines on real launchd, coalitions, kqueue,
sandbox-exec, Git and processes, through the production admission, engine environment
and Seatbelt policy. Containment decoys live under a test owner home the check
creates; the real owner's files, logins and Keychain are never named. The engine
probe makes real model calls and is described in README.md.
"""
import contextlib
import copy
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import checks as T

M, P = T.M, T.P
C = T.load('project_runner_macos_control')
PINNED = '/opt/homebrew/bin/python3.12'  # this Mac's pinned trusted interpreter
WORK = HERE.parents[1] / 'runs'
KEYCHAIN = ('com.apple.SecurityServer', 'com.apple.securityd', 'com.apple.securityd.xpc')
CHILD = r'''import ctypes, json, os, shutil, signal, subprocess, sys, time
from pathlib import Path
mode, config = sys.argv[1], json.loads(Path(sys.argv[2]).read_text())
scratch = Path(config['scratch'])


def attempt(action):
    try:
        action()
        return 'allowed'
    except PermissionError:
        return 'denied'
    except OSError as error:
        return 'error:%d' % error.errno


if mode == 'containment':
    home, temp = os.environ['HOME'], os.environ['TMPDIR']
    report = dict(environment=dict(HOME=home, TMPDIR=temp), write={}, read={}, launchd={}, keychain={}, signal={})
    writes = dict(config['writes'], home=[home + '/allowed', 'w'], temp=[temp + '/allowed', 'w'],
                  derived=[home + '/Library/Developer/Xcode/DerivedData/allowed', 'w'],
                  simulator=[home + '/Library/Developer/CoreSimulator/allowed', 'w'])
    for name, (path, how) in writes.items():
        report['write'][name] = attempt(lambda: open(path, how).close())
    # Inherited confinement, through a symlink to a protected target.
    os.symlink(config['authority'], str(scratch / 'alias'))
    child = subprocess.run([sys.executable, '-c', 'import sys\ntry:\n open(sys.argv[1], "w").close()\n'
                            'except PermissionError:\n sys.exit(3)', str(scratch / 'alias' / 'child-denied')])
    report['write']['alias_child'] = 'denied' if child.returncode == 3 else 'rc:%d' % child.returncode
    for name, path in config['reads'].items():
        report['read'][name] = attempt(lambda: open(path, 'rb').read(1))
    uid, labels = os.getuid(), config['labels']
    plist = scratch / 'probe.plist'
    plist.write_text('<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict><key>Label</key>'
                     '<string>%s</string><key>ProgramArguments</key><array><string>/usr/bin/true</string>'
                     '</array><key>LimitLoadToSessionType</key><string>Background</string></dict></plist>'
                     % labels['bootstrap'])
    copied = str(scratch / 'lc')
    report['launchd']['copy'] = attempt(lambda: os.chmod(shutil.copyfile('/bin/launchctl', copied), 0o755))
    for name, argv in (('submit', ['/bin/launchctl', 'submit', '-l', labels['submit'], '--', '/bin/sleep', '30']),
                       ('bootstrap', ['/bin/launchctl', 'bootstrap', 'user/%d' % uid, str(plist)]),
                       ('copy_submit', [copied, 'submit', '-l', labels['copy_submit'], '--', '/bin/sleep', '30']),
                       ('copy_bootstrap', [copied, 'bootstrap', 'user/%d' % uid, str(plist)])):
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
            report['launchd'][name] = dict(executed=True, rc=result.returncode, err=result.stderr.strip()[:160])
        except PermissionError:
            report['launchd'][name] = dict(executed=False, refused='exec')
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    port = ctypes.c_uint.in_dll(library, 'bootstrap_port')
    for name in config['keychain']:
        found = ctypes.c_uint(0)
        report['keychain'][name] = library.bootstrap_look_up(port, name.encode(), ctypes.byref(found))
    report['signal']['supervisor'] = attempt(lambda: os.kill(config['supervisor'], signal.SIGCONT))
    report['signal']['wrapper'] = attempt(lambda: os.kill(os.getppid(), signal.SIGCONT))
    own = subprocess.Popen(['/bin/sleep', '30'])
    report['signal']['own_child'] = attempt(lambda: os.kill(own.pid, signal.SIGTERM))
    own.kill()
    own.wait()
    (scratch / 'report.json').write_text(json.dumps(report))
    sys.exit(0)
if mode == 'natural':
    sys.exit(0)
if mode == 'descendant':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    # Leaves the engine's process group and session, then ignores TERM.
    subprocess.Popen([sys.executable, '-c', 'import os, signal, sys, time\nos.setsid()\n'
                      'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                      'open(sys.argv[1], "w").write(str(os.getpid()))\ntime.sleep(120)',
                      str(scratch / 'descendant.pid')])
    while not (scratch / 'descendant.pid').exists() or not (scratch / 'descendant.pid').read_text():
        time.sleep(.02)
Path(scratch, 'ready').write_text('ready')
while True:
    time.sleep(.02)
'''


def setup(base, mode, engine, runtime=1.2):
    """A synthetic engine through the production admission and engine environment."""
    paths, profile, unused, facts, request = T.fixture(base)
    profile.update(interpreter=PINNED, runtime_seconds=runtime, startup_seconds=10, heartbeat_seconds=.1,
                   heartbeat_window_seconds=.5, stop_grace_seconds=.2, kill_grace_seconds=.2, settle_seconds=2)
    probe, config = paths['authority'] / 'probe.py', paths['authority'] / 'probe.json'
    probe.write_text(CHILD)
    # The harness is trusted and read only to the worker. Nothing here represents a
    # qualified Claude Code or Codex binary or a native qualification stamp.
    profile['engines'][engine]['argv'] = [sys.executable, str(probe), mode, str(config)] + (
        ['--sandbox', 'danger-full-access'] if engine == 'codex' else ['--print'])
    profile['engines'][engine]['binary_digest'] = P.file_digest(sys.executable)
    host = M.Supervisor(profile, None)
    dispatch = 'dispatch/native/%s/%s' % (engine, mode)
    contract = request['contract']
    contract.update(dispatch_id=dispatch, deadline=time.time() + runtime + 30)
    contract['capability']['adapter'] = engine
    account = dict(id='account', status='active', provider=engine,
                   profiles={host.os.facts()['host']: str(paths['login'])})
    login, environment = C.engine_environment(host, account, dispatch, request['scratch'], {})
    request.update(engine=engine, contract_digest=P.digest(contract), login_profile=login, environment=environment)
    return host, paths, request, config


def probe_start(host, request):
    """Explicit candidate qualification probe, not the production start entry.
    Qualification has to be measured before an operator can admit this profile.
    This harness alone skips it, uses production admission otherwise, and never
    writes a stamp.
    """
    policy = host.admit(request)
    return host._start(request, dict(probe=True, engine=request['engine'],
                                    profile_digest=P.digest(host.profile)), policy)


def wait_marker(path, seconds=8):
    until = time.monotonic() + seconds
    while not path.exists() and time.monotonic() < until:
        time.sleep(.02)
    assert path.exists(), 'never appeared: ' + path.name


def dead(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    return False


def cleanup(host, dispatch, labels=()):
    """Leave no process, launchd job or run temp directory behind."""
    slot = M.read(host.root / host.label(dispatch) / 'slot.json') or {}
    if slot.get('coalition'):
        with contextlib.suppress(Exception):
            for pid in host.os.members(slot['coalition']):
                if pid != os.getpid():
                    os.kill(pid, signal.SIGKILL)
    for label in (host.label(dispatch), *labels):
        subprocess.run(['/bin/launchctl', 'bootout', 'user/%d/%s' % (os.getuid(), label)], capture_output=True)
    for label in labels:
        subprocess.run(['/bin/launchctl', 'remove', label], capture_output=True)
    if slot.get('temp'):
        shutil.rmtree(slot['temp'], ignore_errors=True)


def settle(host, run):
    """An exited run is released, which frees the slot and removes its run temp."""
    assert run.exit_seen and not host.os.members(run.coalition), 'wrapper or descendant remains alive'
    assert run.retirement()['terminated']
    run.release()
    assert host.status()['pending'] == 0 and not Path(run.temp).exists()


def lifecycle(base, engine, mode):
    runtime = {'descendant': 6, 'hard-kill': 6}.get(mode, 1.2)
    host, paths, request, config = setup(base, 'blocked' if mode in ('deadline', 'hard-kill') else mode,
                                         engine, runtime)
    config.write_text(json.dumps(dict(scratch=str(paths['scratch']))))
    dispatch = request['contract']['dispatch_id']
    try:
        run = probe_start(host, request)
        started = time.monotonic()
        detail = {}
        if mode in ('cooperative', 'descendant', 'hard-kill'):
            wait_marker(paths['scratch'] / 'ready')
        if mode == 'descendant':
            escaped = int((paths['scratch'] / 'descendant.pid').read_text())
            worker = M.read(run.directory / 'worker.json')
            # The written PID left the engine's group and session but not the job's coalition.
            assert escaped in host.os.members(run.coalition), 'setsid child not found in the job coalition'
            assert os.getsid(escaped) == escaped and os.getpgid(escaped) != worker['pgid']
            detail = dict(descendant=escaped, descendant_pgid=os.getpgid(escaped), engine_pgid=worker['pgid'])
            run.stop()
        if mode == 'cooperative':
            run.stop()
        if mode == 'hard-kill':
            worker = M.read(run.directory / 'worker.json')
            os.killpg(worker['pgid'], signal.SIGKILL)  # an external group kill of the engine
            detail = dict(engine_pgid=worker['pgid'], wrapper_pgid=run.pgid)
        if mode == 'deadline':
            other = copy.deepcopy(request)
            other['contract']['dispatch_id'] = 'dispatch/excess'
            other['contract_digest'] = P.digest(other['contract'])
            other['environment'].update(host.run_environment('dispatch/excess', other['scratch']))
            T.refused(lambda: probe_start(host, other), 'unavailable_service:concurrency')
            detail = dict(excess='refused unavailable_service:concurrency')
        result = run.wait()
        elapsed = time.monotonic() - started
        assert result['state'] == 'exited', result
        code = result['termination']['returncode']
        if mode == 'natural':
            assert code == 0 and not run.steps
        if mode == 'cooperative':
            assert [s['stage'] for s in run.steps] == ['cooperative'] and code == -signal.SIGTERM
        if mode == 'deadline':
            assert run.cause == 'runtime_cap' and any(s['stage'] == 'terminate' for s in run.steps)
            assert elapsed <= runtime + 2.5
        if mode == 'descendant':
            # The supervisor, not the wrapper's later backstop, found and killed it.
            assert [s['stage'] for s in run.steps] == ['cooperative', 'terminate', 'kill'], run.steps
            assert code == -signal.SIGKILL and run.cause != 'runtime_cap' and elapsed < 4
            assert dead(detail['descendant']), 'setsid descendant still alive'
        if mode == 'hard-kill':
            # The wrapper survived the engine's group SIGKILL and recorded it.
            assert code == -signal.SIGKILL and not run.steps and elapsed < 4
        settle(host, run)
        return [dict(row='native/%s/%s' % (engine, mode), status='passed', elapsed=round(elapsed, 3),
                     process=run.process, worker=result['worker'], coalition=run.coalition, steps=run.steps,
                     returncode=code, outcome=result['state'], released=True, **detail)]
    finally:
        cleanup(host, dispatch)


def supervisor_loss(base, engine):
    """Kill the supervisor mid run: the wrapper still stops the engine at the deadline,
    and a restarted supervisor rebuilds the Run from slot.json and releases it."""
    host, paths, request, config = setup(base, 'blocked', engine, runtime=3)
    config.write_text(json.dumps(dict(scratch=str(paths['scratch']))))
    dispatch = request['contract']['dispatch_id']
    job = base / 'job.json'
    job.write_text(json.dumps(dict(profile=host.profile, request=request)))
    child = subprocess.Popen([sys.executable, __file__, 'supervise', str(job)], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_marker(paths['scratch'] / 'ready')
        directory = host.root / host.label(dispatch)
        slot = M.read(directory / 'slot.json')
        assert slot['state'] == 'running'
        child.kill()
        child.wait()
        killed = time.time()
        worker = M.read(directory / 'worker.json')
        until = time.monotonic() + 3 + 0.2 + 2 + 5
        while host.os.alive(worker['process']) and time.monotonic() < until:
            time.sleep(.02)
        stopped = time.time()
        assert not host.os.alive(worker['process']), 'engine outlived its deadline without a supervisor'
        assert killed < slot['deadline_wall'] - 1, 'supervisor was not killed mid run'
        assert slot['deadline_wall'] - .05 <= stopped <= slot['deadline_wall'] + 0.2 + 2 + 1, (stopped, slot)
        recorded = M.read(directory / 'result.json')
        assert recorded and recorded['deadline_stop'] and recorded['returncode'] == -signal.SIGTERM, recorded
        again = M.Supervisor(host.profile, None)
        rebuilt = again.recover(dispatch)
        result = rebuilt.wait()
        assert result['state'] == 'exited' and result['termination']['deadline_stop'], result
        settle(again, rebuilt)
        return [dict(row='native/%s/supervisor-loss' % engine, status='passed',
                     supervisor_killed_before_deadline=round(slot['deadline_wall'] - killed, 3),
                     engine_stopped_after_deadline=round(stopped - slot['deadline_wall'], 3),
                     wrapper_result=recorded, recovered=True, released=True)]
    finally:
        with contextlib.suppress(Exception):
            child.kill()
        cleanup(host, dispatch)


def supervise(path):
    job = json.loads(Path(path).read_text())
    host = M.Supervisor(job['profile'], None)
    run = probe_start(host, job['request'])
    run.wait()
    return 0


def lookups():
    library = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    port = ctypes.c_uint.in_dll(library, 'bootstrap_port')
    found = ctypes.c_uint(0)
    return {name: library.bootstrap_look_up(port, name.encode(), ctypes.byref(found)) for name in KEYCHAIN}


def job_exists(label):
    return subprocess.run(['/bin/launchctl', 'print', 'user/%d/%s' % (os.getuid(), label)],
                          capture_output=True).returncode == 0


def containment(base, engine):
    host, paths, request, config = setup(base, 'containment', engine)
    dispatch = request['contract']['dispatch_id']
    owner, directory = paths['owner'], host.root / host.label(dispatch)
    other = host.root / host.label('dispatch/other')
    code = Path(M.__file__).resolve().parent
    decoys = dict(ssh=owner / '.ssh/id_ed25519', claude=owner / '.claude/settings.json',
                  claude_json=owner / '.claude.json', claude_accounts=owner / '.claude-accounts/other/.credentials.json',
                  codex=owner / '.codex/auth.json', accounts=paths['accounts'] / 'other/auth.json',
                  projects=paths['projects'] / 'other/secret.txt', dispatches=other / 'request.json')
    allowed_reads = dict(own_login=paths['login'] / 'own.json', clone=paths['clone'] / 'source.txt',
                         owner_other=owner / 'readable.txt')
    for path in (*decoys.values(), *allowed_reads.values()):
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text('decoy written by the VELDO-0124 native check\n')
    reads = {**{k: str(v) for k, v in decoys.items()}, 'claude_case': str(owner / '.CLAUDE.json'),
             **{'allowed_' + k: str(v) for k, v in allowed_reads.items()}}
    denied_writes = dict(owner=[str(owner / 'decoy-write.txt'), 'w'], authority=[str(paths['authority'] / 'denied'), 'w'],
                         code=[str(code / 'veldo-0124-probe-denied'), 'w'], slot=[str(directory / 'slot.json'), 'r+'],
                         result=[str(directory / 'result.json'), 'a'])
    allowed_writes = dict(scratch=[str(paths['scratch'] / 'allowed'), 'w'],
                          clone=[str(paths['clone'] / '.git/veldo-allowed'), 'w'],
                          login=[str(paths['login'] / 'allowed'), 'w'], null=['/dev/null', 'w'])
    labels = {k: 'org.veldo.probe.%s.%s' % (engine, k) for k in ('submit', 'bootstrap', 'copy_submit', 'copy_bootstrap')}
    config.write_text(json.dumps(dict(scratch=str(paths['scratch']), authority=str(paths['authority']),
                                      writes=dict(denied_writes, **allowed_writes, tty=['/dev/tty', 'w']),
                                      reads=reads, labels=labels, keychain=KEYCHAIN, supervisor=os.getpid())))
    baseline = lookups()
    try:
        run = probe_start(host, request)
        result = run.wait()
        assert result['state'] == 'exited' and result['termination']['returncode'] == 0, result
        report = json.loads((paths['scratch'] / 'report.json').read_text())
        policy = M.read(directory / 'request.json')['sandbox']
        jobs = {k: job_exists(v) for k, v in labels.items()}
        assert report['environment'] == dict(HOME=request['environment']['HOME'],
                                             TMPDIR=request['environment']['TMPDIR'])
        settle(host, run)
    finally:
        cleanup(host, dispatch, labels.values())
        with contextlib.suppress(FileNotFoundError):
            (code / 'veldo-0124-probe-denied').unlink()
    w, r, l, k, s = (report[n] for n in ('write', 'read', 'launchd', 'keychain', 'signal'))
    checks = {
        'write': all(w[n] == 'denied' for n in denied_writes) and all(w[n] == 'allowed' for n in allowed_writes)
        and all(w[n] == 'allowed' for n in ('home', 'temp', 'derived', 'simulator'))
        and w['alias_child'] == 'denied' and w['tty'] != 'denied',
        'read': all(r[n] == 'denied' for n in (*decoys, 'claude_case'))
        and all(r['allowed_' + n] == 'allowed' for n in allowed_reads),
        # How launchd was refused: launchctl blocked at exec, the job-creation rule present,
        # the copied binary refused, and no job exists.
        'launchd': l['submit'] == l['bootstrap'] == dict(executed=False, refused='exec')
        and l['copy'] == 'allowed' and l['copy_submit'].get('rc') not in (0, None)
        and l['copy_bootstrap'].get('rc') not in (0, None) and not any(jobs.values())
        and '\n(deny job-creation)\n' in policy and '\n(deny process-exec (literal "/bin/launchctl"))\n' in policy,
        'keychain': any(v == 0 for v in baseline.values()) and all(k[n] != 0 for n in KEYCHAIN)
        and all(k[n] == 1100 for n in KEYCHAIN if baseline[n] == 0),
        'signal': s == dict(supervisor='denied', wrapper='denied', own_child='allowed'),
    }
    observed = dict(write=w, read=r, launchd=dict(l, jobs_created=jobs), keychain=dict(sandboxed=k, unsandboxed=baseline),
                    signal=s)
    return [dict(row='native/%s/%s' % (engine, name), status='passed' if ok else 'failed', observed=observed[name])
            for name, ok in checks.items()]


def engine_probe(candidate):
    """Real CLI launch/identity/deadline/stop only, using previously reserved calls.
    candidate supplies an accepted request and a finite pre-call receipt per probe.
    The authority's Receiver is the production reservation boundary; this offline
    operator harness cannot consult Linux authority keys and does not carry them.
    """
    data = json.loads(Path(candidate).read_text())
    control = T.load('project_runner_macos_control')
    profile = data['profile']
    P.validate(profile)
    host = M.Supervisor(profile, None)
    assert profile['interpreter'] == PINNED or os.access(profile['interpreter'], os.X_OK)
    facts = host.os.facts()
    assert facts['host'] == data['host'] and facts['os_version'] == data['os_version']
    rows = []
    for engine in P.ENGINES:
        for mode in ('natural', 'cooperative', 'deadline'):
            item = data['probes'][engine + '/' + mode]
            request = item['request']
            receipt = item['reservation_receipt']
            assert request['engine'] == engine
            assert receipt['dispatch_id'] == request['contract']['dispatch_id']
            assert receipt['invocation'] and receipt['accepted_seq'] > 0
            assert 0 < receipt['wall_seconds'] <= profile['runtime_seconds']
            assert time.time() < request['contract']['deadline']
            assert request['contract']['deadline'] - time.time() <= receipt['wall_seconds']
            assert receipt['host'] == facts['host'] and receipt['engine'] == engine
            assert receipt['account'] == request['contract']['reservation']['account']
            login_variable = control.ACC.PROFILES[engine]
            assert request['environment'][login_variable] == request['login_profile']
            assert not (set(request['environment']) & (control.CREDENTIALS - {login_variable}))
            assert request['contract_digest'] == P.digest(request['contract'])
            # The production run scoped HOME and TMPDIR, as the Receiver sets them.
            request['environment'].update(host.run_environment(request['contract']['dispatch_id'], request['scratch']))
            assert request['acceptance'].startswith('sha256:')
            assert profile['engines'][engine]['configuration_digest'] == request['contract']['capability']['configuration_digest']
            assert P.file_digest(profile['engines'][engine]['argv'][0]) == profile['engines'][engine]['binary_digest']
            run = probe_start(host, request)
            try:
                if mode == 'cooperative':
                    wait_marker(run.directory / 'worker.json')
                    run.stop()
                result = run.wait()
            finally:
                cleanup(host, request['contract']['dispatch_id'])
            assert run.exit_seen and not host.os.members(run.coalition)
            if mode == 'natural':
                assert result['state'] == 'exited' and result['termination']['returncode'] == 0
            if mode == 'deadline':
                assert run.cause == 'runtime_cap', 'candidate did not exercise a real elapsed deadline'
            rows.append(dict(row='native/qualified-' + engine + '/' + mode, status='passed',
                             process=run.process, worker=result.get('worker'), steps=run.steps,
                             outcome=result['state'], reservation=receipt['invocation']))
            # Usage is unsettled: the authority must ingest real CLI receipts before
            # reclaiming this slot. A candidate pool needs at least six worker slots.
    return rows


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'supervise':
        return supervise(sys.argv[2])
    if sys.platform != 'darwin':
        print(json.dumps(dict(status='not_run', reason='requires_real_macos')))
        return 2
    result = dict(schema='veldo.macos_native_observations/v1', kind='native', facts=M.OS.Native().facts(),
                  modules=str(Path(M.__file__).resolve().parent), rows=[])
    try:
        if mode == 'engines':
            result['rows'] = engine_probe(sys.argv[2])
        elif mode in ('lifecycle', 'containment'):
            engines = sys.argv[2:] or list(P.ENGINES)
            cases = (('natural', 'cooperative', 'deadline', 'descendant', 'hard-kill', 'supervisor-loss')
                     if mode == 'lifecycle' else ('containment',))
            WORK.mkdir(exist_ok=True)
            for engine in engines:
                for case in cases:
                    with tempfile.TemporaryDirectory(prefix='native-', dir=WORK) as directory:
                        try:
                            if case == 'containment':
                                rows = containment(Path(directory), engine)
                            elif case == 'supervisor-loss':
                                rows = supervisor_loss(Path(directory), engine)
                            else:
                                rows = lifecycle(Path(directory), engine, case)
                        except Exception as error:
                            rows = [dict(row='native/%s/%s' % (engine, case), status='failed',
                                         error=type(error).__name__ + ': ' + str(error)[:300])]
                        result['rows'].extend(rows)
        else:
            raise ValueError('expected lifecycle, containment or engines')
    except Exception as error:
        result.update(status='failed', error=type(error).__name__ + ': ' + str(error)[:300])
        print(json.dumps(result, indent=2))
        return 1
    result['status'] = 'passed' if all(r['status'] == 'passed' for r in result['rows']) else 'failed'
    result['qualification_created'] = False
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
