"""Main-node half of the VELDO-0147 Claude leg on the real Mac. Run on the main node.

The dispatch's account (a CLAUDE_CONFIG_DIR on the main node, named by --account) must already be
leased by this run's own runner (scripts/account_lease.sh: RUNNER_LEASES names its lease file with
an ancestor pid, and the flock is held). Its login goes to the Mac in one frame over SSH stdin,
onto a RAM disk, for this run only, and is detached after it. The engine's login handshake runs on
this side (control_engine_claude.Guard): the prompt is released only after the engine's initialize
answer confirms a subscription login. Everything kept is redacted with the run's exact values.

Usage: python3 mac_leg.py <account name> <ssh target> <out dir>
The account directory is resolved from CLAUDE_ACCOUNTS_ROOT (default: the accounts root beside
CLAUDE_CONFIG_DIR); nothing is printed but identifiers, booleans, counts and digests.
"""
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
VELDO = ROOT / 'engine/.veldo'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', '-o', 'ServerAliveInterval=30']
REMOTE = 'veldo-mac-runs/veldo-0147-r2'
PY = '/opt/homebrew/bin/python3.12'
PROMPT = ('This is a qualification unit. Do exactly these steps and nothing else. '
          '1) Use the Bash tool to run this exact command: ls /nonexistent-veldo-0147; echo leg-done '
          '(it is expected to print an error to its error stream). '
          '2) Use the Edit tool to change the line "status: draft" to "status: edited" in notes.txt. '
          '3) Reply with the single word DONE.')


def organ(name):
    spec = importlib.util.spec_from_file_location(name, VELDO / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ancestors():
    pid, seen = os.getpid(), set()
    while pid > 1 and pid not in seen:
        seen.add(pid)
        status = Path('/proc/%d/status' % pid).read_text()
        pid = int(next(l.split()[1] for l in status.splitlines() if l.startswith('PPid:')))
    return seen


def lease_held_by_this_run(account_dir):
    lease = str(Path(account_dir).resolve() / '.runner-lease')
    named = [l.split(' ', 1) for l in os.environ.get('RUNNER_LEASES', '').splitlines() if ' ' in l]
    ours = any(path == lease and int(pid) in ancestors() for pid, path in named)
    with open(lease, 'a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle, fcntl.LOCK_UN)
            held = False
        except BlockingIOError:
            held = True
    return dict(named_by_ancestor=ours, flock_held=held)


def ssh(target, args, data=None, timeout=300):
    return subprocess.run(SSH + [target, args], input=data, capture_output=True, timeout=timeout)


def redact(data, values):
    for value in values:
        data = data.replace(value.encode(), b'<redacted:credential>')
    return data


def main(account, target, out):
    out = Path(out)
    accounts_root = Path(os.environ.get('CLAUDE_ACCOUNTS_ROOT') or Path(os.environ['CLAUDE_CONFIG_DIR']).parent)
    account_dir = accounts_root / account
    run = 'r2-' + time.strftime('%Y%m%d%H%M%S')
    L, C = organ('project_runner_macos_login'), organ('control_engine_claude')
    record = dict(schema='veldo.macos_qualification_run/v1', spec='VELDO-0147', leg='AC1+AC3+AC4-login',
                  engine='claude_code', account=account, run=run, qualification=False)
    record['lease'] = lease_held_by_this_run(account_dir)
    if not all(record['lease'].values()):
        record['refusal'] = 'unavailable_service:account_lease_not_held'
        return record
    body, values = L.frame('claude_code', account_dir, run, account)
    record['frame'] = dict(bytes=len(body), files=sorted(json.loads(body)['files']),
                           refresh_credential_sent=b'refreshToken' in body, redaction_values=len(values))
    shipped = io.BytesIO()
    with tarfile.open(fileobj=shipped, mode='w') as archive:
        for path in (VELDO / 'project_runner_macos_login.py', VELDO / 'project_runner_macos_profile.py',
                     Path(__file__).with_name('mac_leg_remote.py')):
            archive.add(path, arcname=path.name)
    done = ssh(target, 'mkdir -p %s/code && tar -x -C %s/code' % (REMOTE, REMOTE), shipped.getvalue())
    assert done.returncode == 0, 'ship failed'
    record['code_digests'] = {p.name: 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest() for p in
                              (VELDO / 'project_runner_macos_login.py', VELDO / 'project_runner_macos_profile.py',
                               Path(__file__).with_name('mac_leg_remote.py'))}
    remote = 'cd %s/code && %s mac_leg_remote.py' % (REMOTE, PY)
    opened = ssh(target, remote + ' open ' + run, body)
    record['open'] = json.loads(opened.stdout or b'{}')
    try:
        if record['open'].get('status') != 'open':
            record['refusal'] = 'unavailable_service:login_delivery'
            return record
        guard = C.Guard()
        first, _ = guard.opening(PROMPT.encode())
        engine = subprocess.Popen(SSH + [target, remote + ' run ' + run], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        import threading
        errs = []
        reader = threading.Thread(target=lambda: errs.append(engine.stderr.read()))
        reader.start()
        engine.stdin.write(first)
        engine.stdin.flush()
        lines, closed, deadline = [], False, time.monotonic() + 900
        for line in iter(engine.stdout.readline, b''):
            lines.append(line)
            guard.feed(line)
            if guard.stop and not closed:
                engine.stdin.close(); closed = True
            released = guard.release()
            if released and not closed:
                engine.stdin.write(released); engine.stdin.flush()
            try:
                event = json.loads(line)
            except ValueError:
                event = {}
            if event.get('type') == 'result' and not closed:
                engine.stdin.close(); closed = True
            if time.monotonic() > deadline:
                engine.kill(); break
        if not closed:
            engine.stdin.close()
        engine.wait(timeout=120)
        reader.join()
        linux_out, linux_err = b''.join(lines), errs[0] if errs else b''
        record['guard'] = dict(confirmed=guard.confirmed, released=guard.released, stop=guard.stop,
                               source=guard.source)
    finally:
        closed_result = ssh(target, remote + ' close ' + run)
        record['close'] = json.loads(closed_result.stdout or b'{}')
    fetched = ssh(target, remote + ' fetch ' + run, timeout=120).stdout
    mac = {}
    with tarfile.open(fileobj=io.BytesIO(fetched), mode='r:gz') as archive:
        for member in archive.getmembers():
            mac[member.name] = archive.extractfile(member).read()
    summary = json.loads(mac.get('summary.json', b'{}'))
    record['mac'] = {k: summary.get(k) for k in ('binary_bound', 'binary_digest', 'policy_digest',
                     'policy_denies_keychain', 'readback', 'login_status', 'engine_exit', 'edit_diff', 'refusal')}
    # AC3: the record kept on Linux against what the engine emitted on the Mac, line by line and in
    # order, with the exact credential values replaced before the scan.
    kept_out, kept_err = redact(linux_out, values), redact(linux_err, values)
    mac_out, mac_err = redact(mac.get('engine.out', b''), values), redact(mac.get('engine.err', b''), values)
    events = [json.loads(l) for l in kept_out.splitlines() if l.strip().startswith(b'{')]
    tools = [b.get('name') for e in events if e.get('type') == 'assistant'
             for b in e.get('message', {}).get('content', []) if b.get('type') == 'tool_use']
    results = [b for e in events if e.get('type') == 'user'
               for b in (e.get('message', {}).get('content') or []) if isinstance(b, dict) and b.get('type') == 'tool_result']
    init = next((e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init'), {})
    final = next((e for e in events if e.get('type') == 'result'), {})
    record['execution_record'] = dict(
        stdout_lines=len(kept_out.splitlines()), stdout_digest='sha256:' + hashlib.sha256(kept_out).hexdigest(),
        stderr_lines=len(kept_err.splitlines()), stderr_digest='sha256:' + hashlib.sha256(kept_err).hexdigest(),
        stdout_identical_in_order=kept_out.splitlines() == mac_out.splitlines(),
        stderr_identical_in_order=kept_err.splitlines() == mac_err.splitlines(),
        tool_uses=tools, bash_error_output_seen=any('nonexistent-veldo-0147' in json.dumps(r) and
                                                    'No such file' in json.dumps(r) for r in results),
        init_api_key_source=init.get('apiKeySource'), init_tools=sorted(init.get('tools', [])),
        init_mcp_servers=init.get('mcp_servers'), init_model=init.get('model'),
        result_subtype=final.get('subtype'), result_is_error=final.get('is_error'))
    # AC4 on the Mac for the login: no value in the kept record, the Mac's command lines or environments.
    scanned = {'linux_stdout': kept_out, 'linux_stderr': kept_err}
    unredacted = {'linux_stdout': linux_out, 'linux_stderr': linux_err, 'mac_ps': mac.get('ps.txt', b''),
                  'mac_summary': mac.get('summary.json', b'')}
    record['scan'] = dict(
        value_in_redacted_record=any(v.encode() in d for v in values for d in scanned.values()),
        value_in_mac_process_commands_or_environment=any(v.encode() in mac.get('ps.txt', b'') for v in values),
        value_in_mac_summary=any(v.encode() in mac.get('summary.json', b'') for v in values),
        value_in_raw_stream_before_redaction=any(v.encode() in d for v in values for d in
                                                 (linux_out, linux_err)),
        ps_lines_scanned=len(mac.get('ps.txt', b'').splitlines()),
        redaction_marker_count=sum(d.count(b'<redacted:credential>') for d in scanned.values()))
    del unredacted
    record['cleaned'] = json.loads(ssh(target, remote + ' clean ' + run).stdout or b'{}')
    record['qualification'] = bool(
        record['guard']['confirmed'] and record['mac'].get('binary_bound') and record['close'].get('base_absent')
        and record['close'].get('keychain_unchanged') and not record['scan']['value_in_redacted_record']
        and not record['scan']['value_in_mac_process_commands_or_environment']
        and record['execution_record']['stdout_identical_in_order']
        and record['execution_record']['stderr_identical_in_order'])
    out.mkdir(parents=True, exist_ok=True)
    # The kept record itself names the account and the Mac's paths, so only its shape is committed:
    # one row per line, in order, of event type, subtype and tool name.
    shape = []
    for line in kept_out.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            shape.append(['unparsed']); continue
        inner = event.get('event') or {}
        names = [b.get('name') for b in (event.get('message') or {}).get('content') or []
                 if isinstance(b, dict) and b.get('type') == 'tool_use']
        shape.append([event.get('type'), event.get('subtype') or inner.get('type')] + names)
    (out / 'mac-claude-record-shape.json').write_text(json.dumps(dict(
        run=run, stdout_lines=len(shape), stderr_lines=len(kept_err.splitlines()), rows=shape)) + '\n')
    return record


if __name__ == '__main__':
    result = main(*sys.argv[1:4])
    print(json.dumps(result, sort_keys=True, indent=1))
    sys.exit(0 if result.get('qualification') else 2)
