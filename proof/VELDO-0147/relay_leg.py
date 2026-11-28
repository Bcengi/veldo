"""Main-node half of the VELDO-0147 relay leg on the real Mac. Run on the main node.

One dispatch goes the production way: a disposable Linux authority (the VELDO-0125 fixture's real
store, service and signatures) prepares it; control_launch.invoke_remote starts the SSH transport and
writes the prepared binding, the login frame of the dispatch's account and, for Claude Code, one secrets
frame; the Mac's production receiver (control_worker) mounts the login on a RAM disk, claims the dispatch
through the signed relay (control_relay on the Mac, carried back to this authority's socket inside the
same SSH connection) and runs the pinned engine. Nothing here is a qualification: the Mac profile is a
candidate and its qualification stamp is skipped, as in the VELDO-0124 and VELDO-0125 native probes.

The account's lease must be held for the whole Mac run (scripts/account_lease.sh flock) by this run's
holder. The account record and the MCP server are supplied by this driver, not read from an account
store or a keystore; the MCP value is a random test value, never a real credential.

Usage: python3 relay_leg.py <claude_code|codex> <ssh target> <out dir>
"""
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tarfile
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[2]
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', '-o', 'ServerAliveInterval=30',
       '-o', 'StreamLocalBindUnlink=yes', '-o', 'ExitOnForwardFailure=yes']
PY = '/opt/homebrew/bin/python3.12'
# A hang bound only (VELDO-0358 contracts.md): no verdict depends on how long anything takes.
WAIT_HANG_SECONDS = 600


def lease_held(account_dir):
    with open(Path(account_dir).resolve() / '.runner-lease', 'a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle, fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True


def main(engine, target, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if engine == 'claude_code':
        account_name = 'acct7'
        account_dir = Path(os.environ.get('CLAUDE_ACCOUNTS_ROOT') or Path(os.environ['CLAUDE_CONFIG_DIR']).parent) / account_name
    else:
        account_name, account_dir = 'codex1', Path.home() / '.codex'
    run = 'r4-%s-%s' % (engine.split('_')[0], time.strftime('%Y%m%d%H%M%S'))
    record = dict(schema='veldo.macos_relay_run/v1', spec='VELDO-0147', engine=engine, account=account_name,
                  run=run, qualification=False, lease_flock_held=lease_held(account_dir))
    if not record['lease_flock_held']:
        record['refusal'] = 'unavailable_service:account_lease_not_held'
        return record
    remote_root = 'veldo-mac-runs/veldo-0147-r4/' + run
    remote = 'cd %s && %s proof/VELDO-0147/relay_leg_remote.py' % (remote_root, PY)

    def ssh(command, data=None):
        return subprocess.run(SSH[:7] + [target, command], input=data, capture_output=True, timeout=WAIT_HANG_SECONDS)

    def reply(done, step):
        try:
            return json.loads(done.stdout.decode().strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise SystemExit('%s failed rc=%s: %s' % (step, done.returncode, done.stderr.decode()[-1500:]))

    code = subprocess.run(['git', 'archive', 'HEAD', '.veldo', 'proof/VELDO-0124', 'proof/VELDO-0125',
                           'proof/VELDO-0147/relay_leg_remote.py', 'engine/runtime/claude-qualification.json',
                           'engine/runtime/codex-qualification.json'], cwd=ROOT, capture_output=True, check=True).stdout
    shipped = ssh('mkdir -p %s && tar -x -C %s' % (remote_root, remote_root), code)
    assert shipped.returncode == 0, shipped.stderr.decode()[-500:]
    record['commit'] = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v147-relay-') as scratch:
        launch = None
        try:
            candidate = reply(ssh(remote + ' prepare ' + engine), 'prepare')
            record['mac'] = dict(os_version=candidate['facts'].get('os_version'), platform=candidate['facts'].get('platform'),
                                 binary_digest=candidate['binary_digest'])
            spec = importlib.util.spec_from_file_location('v147_authority', ROOT / 'proof/VELDO-0125/checks.py')
            T = importlib.util.module_from_spec(spec)
            sys.path.insert(0, str(ROOT / 'proof/VELDO-0125'))
            spec.loader.exec_module(T)
            f = T.Fixture(Path(scratch) / 'authority', remote=candidate)
            try:
                L = T.W.SV.L
                dispatch = 'dispatch/mac147/' + run
                contract = f.prepare(dispatch, ['macos'], source=candidate['source'], engine=engine,
                                     deadline_seconds=900)['contract']
                # The domain registry defaults to the directory above the installation: keep it in this scratch.
                f.config['domain_registry'] = str(Path(scratch) / 'domains.sqlite3')
                f.start(ipc=True)
                socket_path = '/tmp/veldo-0147-%s.sock' % run
                reply(ssh(remote + ' configure', json.dumps(dict(workspace=str(f.repo), binding=f.binding,
                                                                 socket=socket_path)).encode()), 'configure')
                # The dispatch's account as the account store would hold it: this main node's own profile of it.
                account = dict(id='account', status='active', provider=engine, profiles={'main': str(account_dir)})
                L.ACC.read = lambda conn, name: account if name == 'account' else None
                values = [v.encode() for v in L._organ('project_runner_macos_login').frame(
                    engine, account_dir, dispatch, 'account')[1]]
                if engine == 'claude_code':
                    test_value = 'veldo-0147-test-' + secrets.token_hex(16)
                    values.append(test_value.encode())
                    server = dict(id='tracker', revision=1, transport='http', command=None, arguments=[],
                                  url='https://tracker.invalid/mcp', environment={},
                                  headers={'Authorization': {'credential': 'tracker-token', 'handle':
                                           types.SimpleNamespace(reveal=lambda: 'Bearer ' + test_value)}})
                    L.DL.selections = lambda configuration: [('tracker', 1)]
                    L.DL.resolve = lambda conn, domain, configuration, keystore=None: [server]
                receiver = dict(argv=SSH + ['-R', socket_path + ':' + f.config['socket'], target, remote + ' receive'],
                                login='delivered', main_host='main')
                launch = L.invoke_remote(receiver, contract, f.ds)
                record['invoke'] = dict(result=launch.result, delivered=launch.delivered if launch.result == 'pending' else None,
                                        refusal=(launch.record or {}).get('refusal'))
                final = launch.wait(timeout=WAIT_HANG_SECONDS) if launch.result == 'pending' else launch.record
                record['authority'] = {k: final.get(k) for k in ('state', 'refusal', 'host', 'reason')}
                worker = f.conn.execute('SELECT data FROM entities WHERE id=?', ('worker:' + dispatch,)).fetchone()
                if worker:
                    data = json.loads(worker[0])
                    record['worker_record'] = dict(state=data.get('state'), host_is_mac=data.get('host') == candidate['facts']['host'],
                                                   charge=data.get('charge'), usage=data.get('usage'),
                                                   operations=[c.get('operation') for c in data.get('commands', [])],
                                                   returncode=((data.get('observation') or {}).get('termination') or {}).get('returncode'))
                record['mac_summary'] = reply(ssh(remote + ' summary ' + engine), 'summary')
                fetched = ssh(remote + ' fetch')
                scan = dict(files={}, credential_values=len(values))
                with tarfile.open(fileobj=io.BytesIO(fetched.stdout), mode='r:gz') as archive:
                    for member in archive.getmembers():
                        data = archive.extractfile(member).read()
                        scan['files'][member.name] = dict(bytes=len(data), values_found=sum(data.count(v) for v in values))
                        if member.name == 'engine.err' and 0 < len(data) <= 600 and not any(v in data for v in values):
                            # A short engine error is kept as text, with the Mac's own paths replaced.
                            import re
                            record['engine_err_text'] = re.sub(r'/(Users|private|var)/[^\s\'":]+', '<path>', data.decode(errors='replace'))
                        if member.name == 'engine.out':
                            kinds = {}
                            for line in data.splitlines():
                                try:
                                    event = json.loads(line)
                                except ValueError:
                                    continue
                                kind = str(event.get('type')) + ('/' + str(event.get('subtype')) if event.get('subtype') else '')
                                kinds[kind] = kinds.get(kind, 0) + 1
                                if event.get('type') == 'system' and event.get('subtype') == 'init':
                                    record['engine_init'] = dict(api_key_source=event.get('apiKeySource'),
                                                                 version=event.get('claude_code_version'),
                                                                 tools=event.get('tools'), mcp_servers=event.get('mcp_servers'))
                                if event.get('type') == 'result':
                                    record['engine_result'] = dict(subtype=event.get('subtype'), is_error=event.get('is_error'),
                                                                   turns=event.get('num_turns'))
                            record['engine_events'] = kinds
                            record['engine_out_sha256'] = hashlib.sha256(data).hexdigest()
                f.conn.commit()
                kept = json.dumps([record, contract]).encode() + b''.join(
                    p.read_bytes() for p in sorted(Path(f.store).parent.glob('*')) if p.is_file() and not p.name.endswith('.sock'))
                scan['main_node_kept_values_found'] = sum(kept.count(v) for v in values)
                scan['packet_keys'] = ['contract_digest', 'dispatch_id', 'domain', 'repository']
                record['scan'] = scan
            finally:
                if launch is not None and launch.child is not None:
                    launch._end_receiver()
                f.close()
        finally:
            record['clean'] = reply(ssh(remote + ' clean'), 'clean')
    return record


if __name__ == '__main__':
    result = main(*sys.argv[1:4])
    Path(sys.argv[3], 'relay-%s.json' % sys.argv[1]).write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
    print(json.dumps({k: result.get(k) for k in ('run', 'refusal', 'authority', 'invoke')}, sort_keys=True)[:1500])
