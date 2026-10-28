#!/usr/bin/env python3
"""Mac native real signal ignoring child probe runner for VELDO-0124.

Extends the candidate assertions with a real child readiness and signal observation.
Records native/qualified-claude_code/* as blocked when Mac claude-1 is not logged in
under Keychain-denied Seatbelt (VELDO-0147 setup token territory), rather than aborting
before native/qualified-codex/*. Deletes raw CLI outputs immediately after Meter parsing.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
PROOF_DIR = HERE.parent
sys.path.insert(0, str(PROOF_DIR))

import checks as T
import native_checks as NC

M, P = T.M, T.P
C = T.load('project_runner_macos_control')
CODEX_ENGINE = T.load('control_engine_codex')


def check_login_offline(host, policy, request, engine):
    """Run the CLI's own offline status check inside the exact Seatbelt policy."""
    dispatch = request['contract']['dispatch_id']
    run_paths = host.run_paths(dispatch, request['scratch'])
    for target in run_paths.values():
        Path(target).mkdir(mode=0o700, parents=True, exist_ok=True)
    exe = host.profile['engines'][engine]['argv'][0]
    try:
        if engine == 'claude_code':
            proc = subprocess.run(
                ['/usr/bin/sandbox-exec', '-p', policy, exe, 'auth', 'status', '--json'],
                cwd=request['clone'],
                env=request['environment'],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=15,
            )
            parsed = json.loads(proc.stdout) if proc.stdout.strip().startswith('{') else {}
            return {
                'rc': proc.returncode,
                'logged_in': bool(parsed.get('loggedIn')),
                'auth_method': parsed.get('authMethod'),
                'api_provider': parsed.get('apiProvider'),
            }
        proc = subprocess.run(
            ['/usr/bin/sandbox-exec', '-p', policy, exe,
             '-c', 'cli_auth_credentials_store="file"', 'login', 'status'],
            cwd=request['clone'],
            env=request['environment'],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
        )
        combined = (proc.stdout + '\n' + proc.stderr).strip()
        kind = next((label for prefix, label in CODEX_ENGINE.LOGIN_STATUS if prefix in combined), 'unknown')
        return {
            'rc': proc.returncode,
            'logged_in': proc.returncode == 0 and kind == 'chatgpt',
            'login_kind': kind,
        }
    finally:
        shutil.rmtree(run_paths['temp'], ignore_errors=True)


def verify_real_isolation(iso, run):
    """Verify real engine/descendant coalition membership and Seatbelt isolation."""
    assert iso['descendant']['coalition'] == run.coalition, iso
    assert iso['setsid_grandchild']['coalition'] == run.coalition, iso
    assert iso['setsid_grandchild']['sid'] == iso['setsid_grandchild']['pid'], iso
    assert iso['wrapper_pid'] == run.process['pid'], (iso['wrapper_pid'], run.process)
    denied_writes = ('authority', 'slots', 'veldo_code', 'owner_home', 'authority_symlink_alias')
    assert all(iso['write'][k] == 'denied' for k in denied_writes), iso['write']
    assert iso['write']['scratch'] == 'allowed', iso['write']
    denied_reads = ('other_account_claude', 'decoy_account', 'decoy_project', 'other_dispatch')
    assert all(iso['read'][k] == 'denied' for k in denied_reads), iso['read']
    assert iso['read']['own_clone'] == 'allowed', iso['read']
    assert iso['launchctl'] == {'executed': False, 'refused': 'exec'}, iso['launchctl']
    assert all(v == 1100 for v in iso['keychain'].values()), iso['keychain']
    assert iso['signal'] == {
        'supervisor': 'denied',
        'wrapper': 'denied',
        'own_child': 'allowed',
    }, iso['signal']


def run_probes(candidate_path):
    data = json.loads(Path(candidate_path).read_text())
    profile = data['profile']
    P.validate(profile)
    host = M.Supervisor(profile, None)
    assert profile['interpreter'] == NC.PINNED or os.access(profile['interpreter'], os.X_OK)
    facts = host.os.facts()
    assert facts['host'] == data['host'] and facts['os_version'] == data['os_version']
    (Path(profile['root']).parent / 'supervisor.pid').write_text(str(os.getpid()) + '\n')

    rows = []
    live_calls = 0
    login_cache = {}

    for engine in P.ENGINES:
        for mode in ('descendant',):
            item = data['probes'][engine + '/' + mode]
            request = item['request']
            receipt = item['reservation_receipt']
            dispatch_id = request['contract']['dispatch_id']

            assert request['engine'] == engine
            assert receipt['dispatch_id'] == dispatch_id
            assert receipt['invocation'] and receipt['accepted_seq'] > 0
            assert 0 < receipt['wall_seconds'] <= profile['runtime_seconds']
            assert time.time() < request['contract']['deadline']
            assert request['contract']['deadline'] - time.time() <= receipt['wall_seconds']
            assert receipt['host'] == facts['host'] and receipt['engine'] == engine
            assert receipt['account'] == request['contract']['reservation']['account']
            login_variable = C.ACC.PROFILES[engine]
            assert request['environment'][login_variable] == request['login_profile']
            assert not (set(request['environment']) & (C.CREDENTIALS - {login_variable}))
            assert request['contract_digest'] == P.digest(request['contract'])
            request['environment'].update(host.run_environment(dispatch_id, request['scratch']))
            assert request['acceptance'].startswith('sha256:')
            assert (profile['engines'][engine]['configuration_digest']
                    == request['contract']['capability']['configuration_digest'])
            assert P.file_digest(profile['engines'][engine]['argv'][0]) == profile['engines'][engine]['binary_digest']

            policy = host.admit(request)
            if engine not in login_cache:
                login_cache[engine] = check_login_offline(host, policy, request, engine)
            auth_info = login_cache[engine]

            if engine == 'claude_code' and not auth_info['logged_in']:
                rows.append({
                    'row': 'native/qualified-' + engine + '/' + mode,
                    'status': 'blocked',
                    'admitted_by_supervisor': True,
                    'auth_status': auth_info,
                    'reason': (
                        'Mac claude-1 account is not logged in under Keychain-denied Seatbelt '
                        '(claude auth status exited 1 with loggedIn=false, authMethod=none); '
                        'Mac Claude setup token requires CLAUDE_CODE_OAUTH_TOKEN, which '
                        'project_runner_macos_control.CREDENTIALS strips and '
                        'project_runner_macos_profile.claude_settings refuses as '
                        'unsupported_configuration:claude_settings_source (VELDO-0147 territory).'
                    ),
                    'reservation': receipt['invocation'],
                })
                continue

            assert auth_info['logged_in'], ('unexpected unauthenticated account', engine, auth_info)
            live_calls += 1
            started = time.monotonic()
            run = NC.probe_start(host, request)
            accounting = {}
            extra = {}
            try:
                if mode == 'descendant':
                    child_path = Path(request['scratch']) / 'ignoring-child.json'
                    NC.wait_marker(child_path, seconds=60)
                    child = json.loads(child_path.read_text())
                    assert child['ready'] and child['coalition'] == run.coalition, child
                    assert child['pid'] in host.os.members(run.coalition), child
                    assert child['pid'] != M.read(run.directory / 'worker.json')['process']['pid']
                    stopped_at = time.monotonic()
                    run.stop()
                if mode == 'cooperative':
                    NC.wait_marker(run.directory / 'worker.json')
                    run.stop()
                result = run.wait()
                elapsed = time.monotonic() - started
                if mode == 'descendant':
                    stop_elapsed = time.monotonic() - stopped_at
                    child = json.loads(child_path.read_text())
                    assert 15 in child['ignored'], child
                    assert any(s['stage'] == 'kill' for s in run.steps), run.steps
                    assert run.exit_seen and not host.os.members(run.coalition)
                    assert result['state'] == 'exited', result
                    assert NC.dead(child['pid']), child
                    assert stop_elapsed <= sum(profile[k] for k in (
                        'stop_grace_seconds', 'kill_grace_seconds', 'settle_seconds')) + 3
                    before_release = run.retirement()
                    assert all(before_release[k] for k in ('terminated', 'cleaned', 'outcome_known'))
                    run.release()
                    assert run.state == 'retired'
                    extra = dict(signal_ignoring_child=child, stop_elapsed=round(stop_elapsed, 3),
                                 before_release=before_release, released=True,
                                 live_members_before_release=[], os_exit_seen=run.exit_seen)

                out_file = run.directory / 'engine.out'
                err_file = run.directory / 'engine.err'
                raw_out = out_file.read_bytes() if out_file.exists() else b''
                out_file.unlink(missing_ok=True)
                err_file.unlink(missing_ok=True)
                meter = CODEX_ENGINE.Meter()
                events = meter.feed(raw_out)
                events.extend(meter.close())
                accounting = {
                    'turns': meter.turns,
                    'tokens': meter.tokens,
                    'final': meter.final(),
                    'limit': meter.limit(),
                    'receipt_digests': [e['receipt'] for e in events if 'receipt' in e],
                    'wall_seconds': round(elapsed, 3),
                    'output_bytes': len(raw_out),
                }
            finally:
                for private_name in ('engine.out', 'engine.err'):
                    (run.directory / private_name).unlink(missing_ok=True)
                NC.cleanup(host, dispatch_id)

            assert run.exit_seen and not host.os.members(run.coalition)
            if mode == 'natural':
                assert result['state'] == 'exited' and result['termination']['returncode'] == 0, result
                iso_path = Path(request['scratch']) / 'real-isolation.json'
                assert iso_path.exists(), 'real Codex run did not produce real-isolation.json'
                iso = json.loads(iso_path.read_text())
                verify_real_isolation(iso, run)
                extra['real_isolation'] = iso
            if mode == 'cooperative':
                assert result['state'] == 'exited', result
                assert any(s['stage'] == 'cooperative' for s in run.steps), run.steps
            if mode == 'deadline':
                assert run.cause == 'runtime_cap', 'candidate did not exercise a real elapsed deadline'

            rows.append({
                'row': 'native/qualified-' + engine + '/' + mode,
                'status': 'passed',
                'elapsed': round(elapsed, 3),
                'process': run.process,
                'worker': result.get('worker'),
                'coalition': run.coalition,
                'steps': run.steps,
                'cause': run.cause,
                'termination': result.get('termination'),
                'outcome': result['state'],
                'reservation': receipt['invocation'],
                'accounting': accounting,
                **extra,
            })

    return rows, live_calls, host.status()


def main():
    if sys.platform != 'darwin':
        print(json.dumps({'status': 'not_run', 'reason': 'requires_real_macos'}))
        return 2
    payload = {
        'schema': 'veldo.macos_native_observations/v1',
        'kind': 'native',
        'facts': M.OS.Native().facts(),
        'modules': str(Path(M.__file__).resolve().parent),
        'rows': [],
        'qualification_created': False,
    }
    try:
        rows, live_calls, pool_status = run_probes(sys.argv[1])
        payload['rows'] = rows
        payload['live_model_calls'] = live_calls
        payload['pool_status'] = pool_status
    except Exception as error:
        payload['status'] = 'failed'
        payload['error'] = type(error).__name__ + ': ' + str(error)[:400]
        print(json.dumps(payload, indent=2))
        return 1

    statuses = {r['status'] for r in rows}
    if 'failed' in statuses:
        payload['status'] = 'failed'
        code = 1
    elif statuses == {'passed'}:
        payload['status'] = 'passed'
        code = 0
    else:
        payload['status'] = 'blocked'
        code = 2
    print(json.dumps(payload, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
