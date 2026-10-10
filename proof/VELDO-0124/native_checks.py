#!/usr/bin/env python3
"""Pending native evidence. Never run by a Linux suite and never emits qualification.

python3 proof/VELDO-0124/native_checks.py lifecycle
python3 proof/VELDO-0124/native_checks.py containment
python3 proof/VELDO-0124/native_checks.py engines /absolute/candidate.json

The first two use synthetic engines and real Apple OS interfaces. The last uses
explicit operator supplied CLI argv and fresh disposable subscription profiles.
It does not log in or discover credentials. Read README.md before the engine probe.
"""
import contextlib
import copy
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checks as T

M, P = T.M, T.P
CHILD = '''import os, signal, subprocess, sys, time
from pathlib import Path
mode, scratch, forbidden = sys.argv[1:]
if mode == 'containment':
    Path(scratch, 'allowed').write_text('yes')
    try:
        Path(forbidden, 'denied').write_text('bad')
    except PermissionError:
        pass
    else:
        sys.exit(91)
    # Real inherited confinement, including a symlink to the protected target.
    os.symlink(forbidden, str(Path(scratch, 'alias')))
    child = subprocess.run([sys.executable, '-c',
        'from pathlib import Path; Path(__import__("sys").argv[1], "child-denied").write_text("bad")',
        str(Path(scratch, 'alias'))], capture_output=True)
    sys.exit(0 if child.returncode != 0 else 92)
if mode == 'natural':
    sys.exit(0)
if mode == 'descendant':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    child = subprocess.Popen([sys.executable, '-c',
        'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(120)'])
    Path(scratch, 'descendant.pid').write_text(str(child.pid))
Path(scratch, 'ready').write_text('ready')
while True:
    time.sleep(.02)
'''


def setup(base, mode, engine):
    paths, profile, unused, facts, request = T.fixture(base)
    profile.update(runtime_seconds=1.2, startup_seconds=10, heartbeat_seconds=.1, heartbeat_window_seconds=.5,
                   stop_grace_seconds=.2, kill_grace_seconds=.2, settle_seconds=2)
    executable = paths['authority'] / 'probe.py'
    executable.write_text(CHILD)
    # The entire test harness is trusted, read only to the worker. Nothing here
    # represents a qualified Claude/Codex binary or a native qualification stamp.
    profile['engines'][engine]['argv'] = [sys.executable, str(executable), mode,
                                         str(paths['scratch']), str(paths['authority'])]
    profile['engines'][engine]['binary_digest'] = P.file_digest(sys.executable)
    request['engine'] = request['contract']['capability']['adapter'] = engine
    request['contract']['deadline'] = time.time() + 20
    request['contract_digest'] = P.digest(request['contract'])
    request['environment'] = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(paths['login']),
                                  TMPDIR=str(paths['scratch']))
    return paths, profile, request


def probe_start(host, request):
    """Explicit candidate qualification probe, not the production start entry.
    Qualification has to be measured before an operator can admit this profile.
    This harness alone uses the private candidate path and never writes a stamp.
    """
    P.validate(host.profile)
    host.os.check_clone(request['clone'], request['contract']['source'])
    policy = P.sandbox([request['clone'], request['scratch'], request['login_profile']],
                       [str(host.root), str(Path(M.__file__).parent), *host.profile['protected']])
    return host._start(request, dict(probe=True, engine=request['engine'],
                                    profile_digest=P.digest(host.profile)), policy)


def wait_marker(path):
    until = time.monotonic() + 8
    while not path.exists() and time.monotonic() < until:
        time.sleep(.02)
    assert path.exists(), 'worker never reached readiness marker'


def primitive(base, engine, mode):
    paths, profile, request = setup(base, mode, engine)
    host = M.Supervisor(profile, None)
    run = probe_start(host, request)
    try:
        started = time.monotonic()
        if mode in ('cooperative', 'descendant'):
            wait_marker(paths['scratch'] / 'ready')
            run.stop()
        if mode == 'deadline':
            # Capacity is an independent attempted launch while the first job is live.
            other = copy.deepcopy(request)
            other['contract']['dispatch_id'] = 'dispatch/excess'
            other['contract_digest'] = P.digest(other['contract'])
            T.refused(lambda: probe_start(host, other), 'unavailable_service:concurrency')
        result = run.wait()
        elapsed = time.monotonic() - started
        assert run.exit_seen and not host.os.members(run.pgid), 'wrapper or ordinary descendant remains alive'
        assert elapsed <= profile['runtime_seconds'] + profile['kill_grace_seconds'] + profile['settle_seconds'] + 2
        if mode in ('natural', 'containment'):
            assert result['state'] == 'exited' and result['termination']['returncode'] == 0, result
        if mode == 'containment':
            assert (paths['scratch'] / 'allowed').exists()
            assert not (paths['authority'] / 'denied').exists()
            assert not (paths['authority'] / 'child-denied').exists()
        if mode == 'deadline':
            assert run.cause == 'runtime_cap' and any(s['stage'] == 'terminate' for s in run.steps)
        if mode == 'descendant':
            assert any(s['stage'] == 'kill' for s in run.steps), run.steps
        if result['state'] == 'unknown':
            assert host.status()['pending'] == 1
            T.refused(run.release, 'unknown_outcome:retirement')
        else:
            assert run.retirement()['terminated']
            run.release()
        return dict(row='native/' + engine + '/' + mode, status='passed', elapsed=elapsed,
                    process=run.process, worker=T.M.read(run.directory / 'worker.json'), pgid=run.pgid, steps=run.steps,
                    outcome=result['state'], group_empty=True)
    finally:
        with contextlib.suppress(Exception):
            if host.os.members(run.pgid):
                host.os.send(run.pgid, signal.SIGKILL)
        with contextlib.suppress(Exception):
            host.os.bootout(run.label)



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
                with contextlib.suppress(Exception):
                    if host.os.members(run.pgid):
                        host.os.send(run.pgid, signal.SIGKILL)
                with contextlib.suppress(Exception):
                    host.os.bootout(run.label)
            assert run.exit_seen and not host.os.members(run.pgid)
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
    if sys.platform != 'darwin':
        print(json.dumps(dict(status='not_run', reason='requires_real_macos')))
        return 2
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    result = dict(schema='veldo.macos_native_observations/v1', kind='native', facts=M.OS.Native().facts(), rows=[])
    try:
        if mode == 'engines':
            result['rows'] = engine_probe(sys.argv[2])
        elif mode in ('lifecycle', 'containment'):
            modes = ('natural', 'cooperative', 'deadline', 'descendant') if mode == 'lifecycle' else ('containment',)
            for engine in P.ENGINES:
                for case in modes:
                    with tempfile.TemporaryDirectory(prefix='veldo-0124-native-') as directory:
                        try:
                            result['rows'].append(primitive(Path(directory), engine, case))
                        except Exception:
                            result['rows'].append(dict(row='native/' + engine + '/' + case, status='failed'))
                            raise
        else:
            raise ValueError('expected lifecycle, containment or engines')
    except Exception as error:
        result.update(status='failed', error=type(error).__name__ + ': ' + str(error)[:300])
        print(json.dumps(result, indent=2))
        return 1
    result['status'] = 'passed'
    result['qualification_created'] = False
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
