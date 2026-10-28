#!/usr/bin/env python3
"""Linux authority coordinator for VELDO-0124 native Mac real CLI qualification.

Prepares genuine signed SQLite authority records (accounts, policies, worker slots,
prepared and accepted dispatch contracts, and InvocationGuard pre-call receipts) in an
ephemeral directory outside the repository, exports candidate.json to dmitrys-mac-mini,
runs both unmodified native_checks.py engines and run_qualified_engines.py, settles
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
REMOTE_ROOT = '/Users/dmitry/veldo-0124-check/native-2026-10-28'
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
import subprocess
import sys

targets = json.loads(Path('isolation_targets.json').read_text())
scratch = Path(targets['scratch'])
lib = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)


def get_coalition(pid):
    info = (ctypes.c_uint64 * 5)()
    rc = lib.proc_pidinfo(pid, 20, ctypes.c_uint64(0), info, 40)
    return int(info[0]) if rc == 40 else None


def attempt(fn):
    try:
        fn()
        return 'allowed'
    except PermissionError:
        return 'denied'
    except OSError as exc:
        return 'error:%d' % exc.errno


my_pid = os.getpid()
my_ppid = os.getppid()
my_pgid = os.getpgid(0)
my_sid = os.getsid(0)
my_coalition = get_coalition(my_pid)

grand = subprocess.run(
    [sys.executable, '-B', '-c',
     'import ctypes, json, os\\n'
     'os.setsid()\\n'
     'lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)\\n'
     'info = (ctypes.c_uint64 * 5)()\\n'
     'rc = lib.proc_pidinfo(os.getpid(), 20, ctypes.c_uint64(0), info, 40)\\n'
     'print(json.dumps({"pid": os.getpid(), "pgid": os.getpgid(0), "sid": os.getsid(0), '
     '"coalition": int(info[0]) if rc == 40 else None}))\\n'],
    capture_output=True, text=True, check=True, timeout=10,
)
setsid_child = json.loads(grand.stdout.strip())

writes = {
    'authority': attempt(lambda: open(targets['authority_write'], 'w').close()),
    'slots': attempt(lambda: open(targets['slots_write'], 'w').close()),
    'veldo_code': attempt(lambda: open(targets['code_write'], 'w').close()),
    'owner_home': attempt(lambda: open(targets['owner_write'], 'w').close()),
    'scratch': attempt(lambda: open(str(scratch / 'allowed-write.txt'), 'w').close()),
}
alias = scratch / 'authority-alias'
if not alias.exists():
    os.symlink(targets['authority_dir'], str(alias))
writes['authority_symlink_alias'] = attempt(lambda: open(str(alias / 'alias-write.txt'), 'w').close())

reads = {
    'other_account_claude': attempt(lambda: open(targets['other_account_claude'], 'rb').read(1)),
    'decoy_account': attempt(lambda: open(targets['decoy_account'], 'rb').read(1)),
    'decoy_project': attempt(lambda: open(targets['decoy_project'], 'rb').read(1)),
    'other_dispatch': attempt(lambda: open(targets['other_dispatch'], 'rb').read(1)),
    'own_clone': attempt(lambda: open('task.txt', 'rb').read(1)),
}

try:
    res = subprocess.run(['/bin/launchctl', 'submit', '-l', 'org.veldo.realprobe.codex', '--', '/usr/bin/true'],
                         capture_output=True, text=True, timeout=5)
    launchctl_exec = {'executed': True, 'rc': res.returncode}
except PermissionError:
    launchctl_exec = {'executed': False, 'refused': 'exec'}

port = ctypes.c_uint.in_dll(lib, 'bootstrap_port')
keychain = {}
for svc in ('com.apple.SecurityServer', 'com.apple.securityd', 'com.apple.securityd.xpc'):
    found = ctypes.c_uint(0)
    keychain[svc] = int(lib.bootstrap_look_up(port, svc.encode(), ctypes.byref(found)))

def get_ppid(pid):
    info = (ctypes.c_uint32 * 34)()
    rc = lib.proc_pidinfo(pid, 3, ctypes.c_uint64(0), info, 136)
    return int(info[4]) if rc == 136 else None


cur = my_pid
wrapper_pid = None
while cur and cur > 1:
    parent = get_ppid(cur)
    if parent == 1 and get_coalition(cur) == my_coalition:
        wrapper_pid = cur
        break
    cur = parent

sup_pid = int(Path(targets['supervisor_pid_file']).read_text().strip())
own_sleep = subprocess.Popen(['/bin/sleep', '10'])
sig_own = attempt(lambda: os.kill(own_sleep.pid, signal.SIGTERM))
own_sleep.kill()
own_sleep.wait()
sig_supervisor = attempt(lambda: os.kill(sup_pid, signal.SIGCONT))
sig_wrapper = attempt(lambda: os.kill(wrapper_pid, signal.SIGCONT)) if wrapper_pid else 'wrapper_not_found'

report = {
    'descendant': {'pid': my_pid, 'ppid': my_ppid, 'pgid': my_pgid, 'sid': my_sid, 'coalition': my_coalition},
    'setsid_grandchild': setsid_child,
    'wrapper_pid': wrapper_pid,
    'write': writes,
    'read': reads,
    'launchctl': launchctl_exec,
    'keychain': keychain,
    'signal': {'supervisor': sig_supervisor, 'wrapper': sig_wrapper, 'own_child': sig_own},
    'env_subset': {'HOME': os.environ.get('HOME'), 'TMPDIR': os.environ.get('TMPDIR')},
}
(scratch / 'real-isolation.json').write_text(json.dumps(report, indent=2) + '\\n')
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
        'mkdir -p %s/proof/VELDO-0124/native-2026-10-28 && cat > %s/proof/VELDO-0124/native-2026-10-28/run_qualified_engines.py'
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
    for mode in ('natural', 'cooperative', 'deadline'):
        key = engine + '/' + mode
        pdir = POOL / 'probes' / (engine + '-' + mode)
        clone = pdir / 'clone'
        scratch = pdir / 'scratch'
        clone.mkdir(parents=True)
        scratch.mkdir(parents=True)
        T.git('init', '-q', str(clone))
        if engine == 'codex' and mode == 'natural':
            targets = {
                'scratch': str(scratch),
                'authority_dir': str(POOL / 'authority'),
                'authority_write': str(POOL / 'authority/real-denied.txt'),
                'slots_write': str(POOL / 'slots/real-denied.txt'),
                'code_write': str(ROOT / '.veldo/real-denied.txt'),
                'owner_write': '/Users/dmitry/veldo-0124-real-denied.txt',
                'other_account_claude': '/Users/dmitry/.veldo-mac-accounts/claude-1/settings.json',
                'decoy_account': str(POOL / 'decoy-accounts/other/auth.json'),
                'decoy_project': str(POOL / 'decoy-projects/other/secret.txt'),
                'other_dispatch': str(POOL / 'slots/org.veldo.worker.decoy/request.json'),
                'supervisor_pid_file': str(POOL / 'supervisor.pid'),
            }
            (clone / 'isolation_targets.json').write_text(json.dumps(targets, indent=2) + '\\n')
            (clone / 'check_real_isolation.py').write_text(ISO_SCRIPT)
            (clone / 'task.txt').write_text(
                'Run `/opt/homebrew/bin/python3.12 -B check_real_isolation.py` in the current working directory. '
                'After it exits 0, reply with OK.\\n'
            )
        elif mode == 'natural':
            (clone / 'task.txt').write_text('Reply with OK.\\n')
        elif mode == 'cooperative':
            (clone / 'hold_for_stop.py').write_text('import time\\ntime.sleep(30)\\n')
            (clone / 'task.txt').write_text(
                'Run `/opt/homebrew/bin/python3.12 -B hold_for_stop.py` synchronously in the foreground '
                'and wait for it to finish before replying.\\n'
            )
        else:
            (clone / 'hold_until_deadline.py').write_text('import time\\nfor _ in range(5):\\n    time.sleep(30)\\n')
            (clone / 'task.txt').write_text(
                'Run `/opt/homebrew/bin/python3.12 -B hold_until_deadline.py` synchronously in the foreground '
                'and wait for it to exit before replying. Do not run it in the background.\\n'
            )
        T.git('-C', str(clone), 'add', '.')
        T.git('-C', str(clone), '-c', 'user.name=Veldo Qualification', '-c', 'user.email=qual@veldo.local',
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
        'max_workers': 6,
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
                for mode in ('natural', 'cooperative', 'deadline'):
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
                # 1. Exact unmodified native_checks.py engines run (fails at claude_code/natural local auth, 0 model calls).
                unmod = ssh_run(
                    'cd %s && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py engines %s/candidate.json'
                    % (REMOTE_ROOT, REMOTE_POOL),
                    check=False, timeout=120,
                )
                unmod_out = (unmod.stdout + ('\n' + unmod.stderr if unmod.stderr else '')).rstrip() + '\n'
                (HERE / 'native-engines-unmodified.json').write_text(unmod_out)
                (HERE / 'native-engines-unmodified.exit').write_text('%d\n' % unmod.returncode)
                ssh_run('rm -f %s/slots/*/engine.out %s/slots/*/engine.err' % (REMOTE_POOL, REMOTE_POOL))

                # 2. Companion runner recording Claude rows as blocked and running all 3 real Codex rows.
                qual = ssh_run(
                    'cd %s && /opt/homebrew/bin/python3.12 '
                    'proof/VELDO-0124/native-2026-10-28/run_qualified_engines.py %s/candidate.json'
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
                for mode in ('natural', 'cooperative', 'deadline'):
                    key = engine + '/' + mode
                    row = row_map['native/qualified-' + key]
                    guard, invocation, dispatch_id, cdigest = guards[key]
                    if row['status'] == 'blocked':
                        # Unmodified native_checks.py attempted claude_code/natural locally (rc!=0, 0 model calls);
                        # cooperative and deadline were not executed.
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
                        outcome = {'natural': 'completed', 'cooperative': 'cancelled', 'deadline': 'timeout'}[mode]
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
                'unmodified_engines_exit': unmod.returncode,
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
                'unmodified_exit': unmod.returncode,
                'qualified_exit': qual.returncode,
                'live_model_calls': qual_data.get('live_model_calls'),
                'rows': [(r['row'], r['status']) for r in qual_data.get('rows', [])],
                'stray_jobs': stray_jobs,
            }, indent=2))
            return 0 if qual.returncode in (0, 2) and unmod.returncode == 1 else 1
        finally:
            conn.close()


if __name__ == '__main__':
    sys.exit(main())
