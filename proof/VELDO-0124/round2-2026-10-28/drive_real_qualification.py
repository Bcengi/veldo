#!/usr/bin/env python3
"""Linux authority coordinator for the round 2 real child probes.

Prepares genuine signed SQLite authority records (accounts, policies, worker slots,
prepared and accepted dispatch contracts, and InvocationGuard pre-call receipts) in an
ephemeral directory outside the repository, exports candidate.json to dmitrys-mac-mini,
runs the real signal ignoring child probes, settles
non-secret accounting in the ephemeral store, and cleans up temporary Mac probe state.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
PROOF_DIR = HERE.parent
ROOT = PROOF_DIR.parents[1]
sys.path.insert(0, str(PROOF_DIR))

import checks as T

P = T.P
C = T.load('project_runner_macos_control')
D, S, RES = C.D, C.D.S, C.D.RES
SIG = T.load('control_signer')

MAC_HOST_SSH = 'dmitry@dmitrys-mac-mini'
REMOTE_ROOT = '/Users/dmitry/veldo-0124-check/round2-2026-10-28'
REMOTE_POOL = REMOTE_ROOT + '/qual-pool'
CODEX_BIN = (
    '/Users/dmitry/.local/share/veldo-engines/codex-0.154.0/'
    'node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex'
)
CLAUDE_BIN = '/Users/dmitry/.local/share/claude/versions/2.1.303'
ACCOUNTS = {
    'claude_code': ('claude-1', '/Users/dmitry/.veldo-mac-accounts/claude-1'),
    'codex': ('codex-1', '/Users/dmitry/.veldo-mac-accounts/codex-1'),
}

REAL_ISOLATION_SCRIPT = """import ctypes
import json
import os
from pathlib import Path
import signal
import time

scratch = Path('../scratch')
lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
info = (ctypes.c_uint64 * 5)()
rc = lib.proc_pidinfo(os.getpid(), 20, ctypes.c_uint64(0), info, 40)
assert rc == 40
report = dict(pid=os.getpid(), ppid=os.getppid(), pgid=os.getpgid(0),
              coalition=int(info[0]), ignored=[], ready=False)
def ignore(number, frame):
    report['ignored'].append(number)
    (scratch / 'ignoring-child.json').write_text(json.dumps(report))
for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    signal.signal(number, ignore)
report['ready'] = True
(scratch / 'ignoring-child.json').write_text(json.dumps(report))
while True:
    time.sleep(0.1)
"""


def ssh_run(remote_cmd, *, input_text=None, timeout=300, check=True):
    proc = subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', MAC_HOST_SSH, remote_cmd],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if check and proc.returncode != 0:
        raise RuntimeError('ssh failed (%d): %s\n%s' % (proc.returncode, proc.stdout[-600:], proc.stderr[-600:]))
    return proc


def prepare_remote_pool():
    runner_src = (HERE / 'run_qualified_engines.py').read_text()
    ssh_run(
        'mkdir -p %s/proof/VELDO-0124/round2-2026-10-28 && cat > %s/proof/VELDO-0124/round2-2026-10-28/run_qualified_engines.py'
        % (REMOTE_ROOT, REMOTE_ROOT),
        input_text=runner_src,
    )
    setup_code = """import json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(%r)
POOL = Path(%r)
CODEX_BIN = %r
CLAUDE_BIN = %r
ISO_SCRIPT = %r

sys.path.insert(0, str(ROOT / 'proof/VELDO-0124'))
import checks as T
M, P = T.M, T.P

shutil.rmtree(POOL, ignore_errors=True)
(POOL / 'slots/org.veldo.worker.decoy').mkdir(parents=True)
(POOL / 'slots/org.veldo.worker.decoy/request.json').write_text('{"decoy": true}\\n')
(POOL / 'authority').mkdir(parents=True)
(POOL / 'authority/protected.txt').write_text('authority protected\\n')
(POOL / 'decoy-accounts/other').mkdir(parents=True)
(POOL / 'decoy-accounts/other/auth.json').write_text('decoy account\\n')
(POOL / 'decoy-projects/other').mkdir(parents=True)
(POOL / 'decoy-projects/other/secret.txt').write_text('decoy project\\n')

probes = {}
for engine in ('claude_code', 'codex'):
    for mode in ('descendant',):
        key = engine + '/' + mode
        pdir = POOL / 'probes' / (engine + '-' + mode)
        clone = pdir / 'clone'
        scratch = pdir / 'scratch'
        clone.mkdir(parents=True)
        scratch.mkdir(parents=True)
        T.git('init', '-q', str(clone))
        if mode == 'descendant':
            (clone / 'hold_ignoring_signals.py').write_text(ISO_SCRIPT)
            (clone / 'task.txt').write_text(
                'Run `/opt/homebrew/bin/python3.12 -B hold_ignoring_signals.py` synchronously '
                'in the foreground and wait for it to finish. Do not launch any background process.\\n'
            )
        T.git('-C', str(clone), 'add', '.')
        T.git('-C', str(clone), '-c', 'user.name=Dmitry Grinberg', '-c', 'user.email=dmitry@bcengi.com',
              '-c', 'commit.gpgsign=false', 'commit', '-qm', 'probe-' + engine + '-' + mode)
        source = {k: T.git('-C', str(clone), 'rev-parse', 'HEAD^{%%s}' %% k) for k in ('commit', 'tree')}
        probes[key] = {'clone': str(clone), 'scratch': str(scratch), 'source': source}

facts = M.OS.Native().facts()
print(json.dumps({
    'facts': facts,
    'digests': {
        'claude_code': P.file_digest(CLAUDE_BIN),
        'codex': P.file_digest(CODEX_BIN),
    },
    'probes': probes,
}))
""" % (REMOTE_ROOT, REMOTE_POOL, CODEX_BIN, CLAUDE_BIN, REAL_ISOLATION_SCRIPT)
    proc = ssh_run('/opt/homebrew/bin/python3.12 -', input_text=setup_code)
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main():
    remote_info = prepare_remote_pool()
    facts = remote_info['facts']
    mac_host = facts['host']

    configurations = {
        'claude_code': {
            'environment': {
                'DISABLE_AUTOUPDATER': '1',
                'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '1',
                'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1',
                'TERM': 'dumb',
            },
            'identity': 'veldo-0124-mac-claude-2.1.303',
        },
        'codex': {
            'environment': {
                'DISABLE_AUTOUPDATER': '1',
                'SSL_CERT_FILE': '/etc/ssl/cert.pem',
                'TERM': 'dumb',
            },
            'identity': 'veldo-0124-mac-codex-0.154.0',
        },
    }
    prompt_text = 'Read task.txt in the current directory and execute its exact instruction immediately.'
    profile = {
        'schema': P.SCHEMA,
        'revision': 1,
        'max_workers': 2,
        'root': REMOTE_POOL + '/slots',
        'protected': [REMOTE_POOL + '/authority'],
        'interpreter': '/opt/homebrew/bin/python3.12',
        'home': '/Users/dmitry',
        'account_roots': ['/Users/dmitry/.veldo-mac-accounts', REMOTE_POOL + '/decoy-accounts'],
        'project_roots': [REMOTE_POOL + '/decoy-projects'],
        'runtime_seconds': 120.0,
        'startup_seconds': 15.0,
        'stop_grace_seconds': 3.0,
        'kill_grace_seconds': 3.0,
        'settle_seconds': 3.0,
        'heartbeat_seconds': 0.5,
        'heartbeat_window_seconds': 5.0,
        'engines': {
            'claude_code': {
                'argv': [
                    CLAUDE_BIN, '--print', '--output-format', 'stream-json', '--verbose',
                    '--setting-sources=', '--strict-mcp-config', '--disable-slash-commands',
                    '--mcp-config', '{"mcpServers":{}}',
                    '--settings', '{"sandbox":{"enabled":false},"disableAllHooks":true}',
                    '--permission-mode', 'bypassPermissions',
                    prompt_text,
                ],
                'version': '2.1.303',
                'binary_digest': remote_info['digests']['claude_code'],
                'configuration_digest': P.digest(configurations['claude_code']),
            },
            'codex': {
                'argv': [
                    CODEX_BIN, 'exec', '--json', '-c', 'check_for_update_on_startup=false',
                    '--ignore-user-config', '--ignore-rules', '--disable', 'apps', '--ephemeral',
                    '-c', 'project_doc_max_bytes=0',
                    '-c', 'forced_login_method="chatgpt"',
                    '-c', 'cli_auth_credentials_store="file"',
                    '-c', 'skills.bundled.enabled=false',
                    '-c', 'skills.include_instructions=false',
                    '-c', 'approval_policy="never"',
                    '--sandbox', 'danger-full-access',
                    prompt_text,
                ],
                'version': '0.154.0',
                'binary_digest': remote_info['digests']['codex'],
                'configuration_digest': P.digest(configurations['codex']),
            },
        },
    }

    with tempfile.TemporaryDirectory(prefix='v124-qual-authority-') as authority_tmp:
        auth_dir = Path(authority_tmp)
        key_path = auth_dir / 'journal_ed25519'
        subprocess.run(
            ['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key_path)],
            check=True, capture_output=True, timeout=10,
        )
        sign = lambda data: SIG.sign_bytes(key_path, data, 'veldo-journal')
        conn = S.open_store(str(auth_dir / 'control.sqlite3'))
        try:
            S.execute(
                conn,
                {
                    'command_id': 'setup/receiver',
                    'principal': 'owner',
                    'operation': 'upsert_entity',
                    'nonce': 'setup/receiver',
                    'expected_versions': {'receiver': 0},
                    'artifact_digests': [],
                    'parameters': {
                        'entity_id': 'receiver',
                        'kind': 'membership',
                        'data': {
                            'principal_type': 'service',
                            'roles': ['reservation_service'],
                            'scope': ['veldo'],
                            'revoked_at': None,
                            'expires_at': None,
                        },
                    },
                },
                'owner', sign, 1,
            )
            reservations = RES.Reservations(
                S, conn, domain='veldo-0124-qual', repository='veldo', principal='receiver',
                authorize=RES.service_authority, signer='receiver', sign=sign,
            )
            accounts = C.ACC.Accounts(
                S, conn, principal='receiver', signer='receiver', sign=sign,
                authorize=lambda c, cmd: True,
            )
            dispatches = D.Dispatches(
                S, conn, domain='veldo-0124-qual', repository='veldo', principal='receiver',
                signer='receiver', sign=sign,
            )

            now = time.time()
            for engine, (acct_id, acct_path) in ACCOUNTS.items():
                accounts.register(
                    'register/' + acct_id, acct_id, engine,
                    'owner Mac qualification account ' + acct_id,
                    {mac_host: acct_path}, now=now,
                )
                reservations.configure(
                    'policy/account/' + acct_id, 'account', acct_id,
                    {'capacity': 6, 'invocations': 6, 'wall_seconds': 720},
                    now=now,
                )
            reservations.configure(
                'policy/project/veldo-0124', 'project', 'veldo-0124',
                {'capacity': 6, 'invocations': 6, 'wall_seconds': 720},
                now=now,
            )

            receiver_identity = {
                'platform': 'linux',
                'host': 'linux-authority',
                'boot_id': 'authority-boot',
                'pid': 1,
                'start': 'authority-start',
                'principal': 'receiver',
            }

            candidate_probes = {}
            guards = {}
            t0 = time.time()

            for engine in P.ENGINES:
                acct_id = ACCOUNTS[engine][0]
                acct_record = accounts.get(acct_id)
                for mode in ('descendant',):
                    key = engine + '/' + mode
                    tag = engine + '-' + mode
                    unit_id = 'unit-qual-' + tag
                    dispatch_id = 'dispatch/veldo-0124-qual/' + tag
                    pinfo = remote_info['probes'][key]

                    reservations.configure(
                        'policy/unit/' + unit_id, 'unit', unit_id,
                        {'capacity': 2, 'invocations': 2, 'wall_seconds': 240},
                        now=t0,
                    )
                    reservations.reserve_worker(
                        'slot/' + tag, dispatch_id, acct_id, 'veldo-0124', unit_id, now=t0,
                    )
                    worker_entity = RES.entity('worker', ['veldo-0124-qual', dispatch_id])
                    version, wdigest = conn.execute(
                        'SELECT version, digest FROM entities WHERE id=?', (worker_entity,)
                    ).fetchone()

                    horizon = 85.0 if (engine == 'codex' and mode == 'deadline') else 115.0
                    deadline = t0 + horizon
                    payload = {'probe_mode': mode}
                    contract = {
                        'schema': 'veldo.dispatch/v1',
                        'dispatch_id': dispatch_id,
                        'domain': 'veldo-0124-qual',
                        'repository': 'veldo',
                        'unit': unit_id,
                        'station': 'review',
                        'attempt': 1,
                        'source': pinfo['source'],
                        'deadline': deadline,
                        'input': {
                            'decision': {
                                'decision_id': 'admitted-qual-' + tag,
                                'station': 'review',
                                'unit': unit_id,
                                'inputs': {'source': pinfo['source']},
                            },
                            'context': {},
                            'payload': payload,
                            'payload_digest': D.digest(payload),
                        },
                        'capability': {
                            'adapter': engine,
                            'configuration': configurations[engine],
                            'configuration_digest': profile['engines'][engine]['configuration_digest'],
                        },
                        'reservation': {
                            'entity': worker_entity,
                            'version': version,
                            'digest': wdigest,
                            'account': acct_id,
                            'project': 'veldo-0124',
                        },
                        'claim': None,
                        'authority_generation': 1,
                    }
                    cdigest = D.digest(contract)
                    assert cdigest == P.digest(contract)
                    dispatches.prepare(contract, now=t0)
                    dispatches.accept(dispatch_id, cdigest, receiver_identity, now=t0)
                    acceptance = dispatches.receipt(dispatch_id, 'accept')

                    login_path = C.ACC.profile(acct_record, mac_host)[1]
                    env = C.ACC.login_environment(
                        {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'},
                        acct_record, mac_host, C.STRIPPED,
                        configurations[engine]['environment'], C.CREDENTIALS,
                    )
                    env['VELDO_DISPATCH_ID'] = dispatch_id
                    env['VELDO_DISPATCH_ACCEPTANCE'] = acceptance

                    invocation = 'invocation/' + dispatch_id
                    launched = []
                    guard = C.RR.InvocationGuard(
                        reservations, engine,
                        lambda ident, cfg: launched.append(ident),
                        lambda ident: None,
                    )
                    wall_reserve = min(profile['runtime_seconds'], deadline - t0)
                    store_res = guard.invoke(
                        'macos-qual-call/' + tag, dispatch_id, invocation,
                        C.RR.boundary(contract), wall_reserve, configurations[engine], now=t0,
                    )
                    assert not store_res['replayed'] and launched == [invocation]
                    call_entity = RES.entity('invocation', ['veldo-0124-qual', invocation])
                    call_record = reservations._records()[call_entity]
                    call_digest = conn.execute(
                        'SELECT digest FROM entities WHERE id=?', (call_entity,)
                    ).fetchone()[0]

                    receipt = {
                        'dispatch_id': call_record['dispatch'],
                        'invocation': call_record['invocation'],
                        'accepted_seq': call_record['accepted_seq'],
                        'wall_seconds': call_record['charge']['wall_seconds'],
                        'host': mac_host,
                        'engine': engine,
                        'account': call_record['context']['account'],
                        'entity': call_entity,
                        'entity_digest': call_digest,
                    }
                    request = {
                        'contract': contract,
                        'contract_digest': cdigest,
                        'acceptance': acceptance,
                        'engine': engine,
                        'clone': pinfo['clone'],
                        'scratch': pinfo['scratch'],
                        'login_profile': login_path,
                        'environment': env,
                    }
                    candidate_probes[key] = {'request': request, 'reservation_receipt': receipt}
                    guards[key] = (guard, invocation, dispatch_id, cdigest)

            candidate = {
                'host': mac_host,
                'os_version': facts['os_version'],
                'profile': profile,
                'probes': candidate_probes,
            }
            candidate_text = json.dumps(candidate, indent=2, sort_keys=True) + '\n'
            ssh_run('cat > %s/candidate.json' % REMOTE_POOL, input_text=candidate_text)

            try:
                qual = ssh_run(
                    'cd %s && /opt/homebrew/bin/python3.12 '
                    'proof/VELDO-0124/round2-2026-10-28/run_qualified_engines.py %s/candidate.json'
                    % (REMOTE_ROOT, REMOTE_POOL),
                    check=False, timeout=420,
                )
                qual_out = qual.stdout.rstrip() + '\n'
                (HERE / 'native-engines-qualified.json').write_text(qual_out)
                if qual.stderr.strip():
                    (HERE / 'native-engines-qualified.stderr.log').write_text(qual.stderr)
                (HERE / 'native-engines-qualified.exit').write_text('%d\n' % qual.returncode)
                qual_data = json.loads(qual.stdout)
            finally:
                cleanup_proc = ssh_run(
                    'rm -rf %s %s/runs && '
                    '(/bin/launchctl list | grep org.veldo || true)'
                    % (REMOTE_POOL, REMOTE_ROOT),
                    check=False,
                )
                stray_jobs = cleanup_proc.stdout.strip()

            # 3. Ingest non-secret accounting into the ephemeral SQLite authority store.
            if qual_data.get('status') == 'failed':
                raise RuntimeError('qualified engine probe failed: ' + str(qual_data.get('error')))
            now_settle = time.time()
            row_map = {r['row']: r for r in qual_data.get('rows', [])}
            settled_summary = {}
            for engine in P.ENGINES:
                for mode in ('descendant',):
                    key = engine + '/' + mode
                    row = row_map['native/qualified-' + key]
                    guard, invocation, dispatch_id, cdigest = guards[key]
                    if row['status'] == 'blocked':
                        # Offline authentication refusal made no model call.
                        outcome = 'failed' if mode == 'natural' else 'not_executed'
                        usage = {'invocations': 1, 'wall_seconds': 0.5} if mode == 'natural' else {}
                        rep = guard.observe(
                            'settle/' + engine + '-' + mode, invocation, 1, usage,
                            now=now_settle, final=True, outcome=outcome,
                        )
                    else:
                        acc = row['accounting']
                        usage = {'invocations': 1, 'wall_seconds': acc['wall_seconds']}
                        if acc.get('final'):
                            usage.update(acc['final'])
                        outcome = {'natural': 'completed', 'cooperative': 'cancelled', 'deadline': 'timeout', 'descendant': 'cancelled'}[mode]
                        rep = guard.observe(
                            'settle/' + engine + '-' + mode, invocation, 1, usage,
                            now=now_settle, final=True, outcome=outcome,
                            receipts=acc.get('receipt_digests', ()),
                        )
                        dispatches.run(dispatch_id, cdigest, row['process'], now=now_settle)
                        dispatches.exit(
                            dispatch_id, cdigest, row['process'], row['termination'], now=now_settle,
                            artifact={'verdict': 'incomplete', 'complete': False, 'digest': P.digest(None)},
                        )
                    call_entity = RES.entity('invocation', ['veldo-0124-qual', invocation])
                    stored_call = reservations._records()[call_entity]
                    settled_summary[key] = {
                        'dispatch_id': dispatch_id,
                        'dispatch_state': dispatches.record(dispatch_id)['state'],
                        'invocation': invocation,
                        'invocation_state': stored_call['state'],
                        'outcome': stored_call.get('outcome'),
                        'charge': stored_call['charge'],
                        'observed': stored_call['observed'],
                        'stop_required': rep['stop_required'],
                    }

            ledger_summary = {
                'schema': 'veldo.macos_qualification_authority_ledger/v1',
                'host': mac_host,
                'os_version': facts['os_version'],
                'profile_digest': P.digest(profile),
                'engine_identities': {
                    eng: {
                        'argv': profile['engines'][eng]['argv'],
                        'version': profile['engines'][eng]['version'],
                        'binary_digest': profile['engines'][eng]['binary_digest'],
                        'configuration_digest': profile['engines'][eng]['configuration_digest'],
                    }
                    for eng in P.ENGINES
                },
                                'qualified_engines_exit': qual.returncode,
                'live_model_calls': qual_data.get('live_model_calls'),
                'stray_launchd_jobs_after_cleanup': stray_jobs,
                'account_balances': {
                    acct_id: reservations.balances('account', acct_id)
                    for acct_id, _ in ACCOUNTS.values()
                },
                'probes': settled_summary,
            }
            (HERE / 'authority-ledger.json').write_text(json.dumps(ledger_summary, indent=2, sort_keys=True) + '\n')
            print(json.dumps({
                'qualified_exit': qual.returncode,
                'live_model_calls': qual_data.get('live_model_calls'),
                'rows': [(r['row'], r['status']) for r in qual_data.get('rows', [])],
                'stray_jobs': stray_jobs,
            }, indent=2))
            return 0 if qual.returncode in (0, 2) else 1
        finally:
            conn.close()


if __name__ == '__main__':
    sys.exit(main())
