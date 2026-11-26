"""Mac half of the VELDO-0147 Claude leg. Runs from <Mac home>/veldo-mac-runs/veldo-0147-r2/code.

Every path is derived here from the Mac's own home and per-user temp directory, so no command line
carries a home path or a credential. Subcommands (one run id each):
  open RUN   read the login frame from stdin, mount it on a RAM disk (project_runner_macos_login)
  run RUN    start the pinned engine under the run's Seatbelt profile; relay its stdin, stdout and
             stderr over this SSH channel and keep the Mac's own copy of both streams
  close RUN  detach the RAM disk and confirm the login is gone and the keychain unchanged
  fetch RUN  tar the Mac-side observations (no login is ever inside them unredacted except the
             engine's own stream copy, which the main node redacts before anything is kept)
  clean RUN  remove the run's scratch
"""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tarfile
import threading

CODE = Path(__file__).resolve().parent
RUNS = CODE.parent / 'runs'
HOME = Path(pwd.getpwuid(os.getuid()).pw_dir)
PINNED = HOME / '.local/share/claude/versions/2.1.317'
PINNED_SHA = '09f153b46b5df9e8b3454716d682a91901de020cbca630f61dec1a015b32b5e9'
ACCOUNTS = HOME / '.veldo-mac-accounts'
PAID = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'OPENAI_API_KEY',
        'CODEX_API_KEY', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX')
BASELINE_ENV = {'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '1',
                'LANG': 'C.UTF-8', 'TERM': 'dumb', 'DISABLE_AUTOUPDATER': '1'}
FLAGS = ['--print', '--output-format', 'stream-json', '--verbose', '--input-format', 'stream-json',
         '--setting-sources', '', '--strict-mcp-config', '--disable-slash-commands',
         '--mcp-config', '{"mcpServers":{}}', '--settings', '{"disableAllHooks":true}',
         '--include-partial-messages', '--forward-subagent-text',
         '--tools=Bash,Edit,Read', '--allowedTools=Bash,Edit,Read', '--model', 'opus']


def organ(name):
    spec = importlib.util.spec_from_file_location(name, CODE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def user_temp():
    out = subprocess.run(['/usr/bin/getconf', 'DARWIN_USER_TEMP_DIR'], capture_output=True, text=True)
    return Path(out.stdout.strip()).resolve()


def login_base(run):
    return user_temp() / ('veldo-login-' + run)


def keychain():
    """Claude service names in the login keychain, from attributes only (dump-keychain without -d
    prints no secret data)."""
    out = subprocess.run(['/usr/bin/security', 'dump-keychain'], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL).stdout
    names = sorted(line.split('=', 1)[1].strip() for line in out.splitlines()
                   if '"svce"' in line and 'Claude' in line)
    return dict(claude_items=len(names), digest=hashlib.sha256('\n'.join(names).encode()).hexdigest())


def checked(run):
    if not run.replace('-', '').isalnum() or len(run) > 40:
        raise SystemExit('bad run id')
    return run


def cmd_open(run):
    L = organ('project_runner_macos_login')
    before = keychain()
    try:
        result = L.open_profile(login_base(run), sys.stdin)
    except L.Refused as error:
        result = dict(status='refused', refusal=error.code)
    RUNS.mkdir(mode=0o700, exist_ok=True)
    scratch = RUNS / run
    scratch.mkdir(mode=0o700)
    (scratch / 'keychain-before.json').write_text(json.dumps(before))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'open' else 3


# A hang bound only (VELDO-0358 contracts.md): no verdict depends on how long anything takes.
WAIT_HANG_SECONDS = 600

def pump(source, sinks, each=None):
    for chunk in iter(lambda: source.read1(65536), b''):
        for sink in sinks:
            sink.write(chunk)
            sink.flush()
        if each is not None:
            each()


def cmd_run(run):
    P = organ('project_runner_macos_profile')
    scratch = RUNS / run
    profile = login_base(run) / 'profile'
    clone, home = scratch / 'clone', scratch / 'home'
    temp = user_temp() / ('veldo-run-' + run)
    for path in (clone, home, temp):
        path.mkdir(mode=0o700)
    (clone / 'notes.txt').write_text('title: mac leg unit\nstatus: draft\n')
    git = dict(os.environ, GIT_AUTHOR_NAME='veldo', GIT_AUTHOR_EMAIL='veldo@localhost',
               GIT_COMMITTER_NAME='veldo', GIT_COMMITTER_EMAIL='veldo@localhost')
    for argv in (['init', '-q'], ['add', 'notes.txt'], ['commit', '-qm', 'unit']):
        subprocess.run(['/usr/bin/git', '-C', str(clone)] + argv, check=True, env=git,
                       stdin=subprocess.DEVNULL, capture_output=True)
    summary = dict(run=run, executable_version='2.1.317')
    actual = hashlib.sha256(PINNED.read_bytes()).hexdigest()
    summary['binary_digest'] = 'sha256:' + actual
    summary['binary_bound'] = actual == PINNED_SHA
    if not summary['binary_bound']:
        summary['refusal'] = 'unqualified_executable:digest_changed'
        (scratch / 'summary.json').write_text(json.dumps(summary, sort_keys=True))
        return 5
    policy = P.sandbox([str(clone), str(scratch), str(profile), str(home), str(temp)], [str(CODE)],
                       str(HOME), accounts=[str(ACCOUNTS)] if ACCOUNTS.is_dir() else [])
    summary['policy_digest'] = P.digest(policy)
    summary['policy_denies_keychain'] = 'com.apple.SecurityServer' in policy
    environment = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin', HOME=str(home), TMPDIR=str(temp),
                       TMP=str(temp), TEMP=str(temp), CLAUDE_CODE_TMPDIR=str(temp),
                       CLAUDE_CONFIG_DIR=str(profile), VELDO_DISPATCH_ID=run, **BASELINE_ENV)
    # Read-back (VELDO-0062 AC1 on the Mac): exactly the dispatch's profile and no paid-API credential.
    summary['readback'] = dict(
        names=sorted(environment), config_dir_is_delivered_profile=environment['CLAUDE_CONFIG_DIR'] == str(profile),
        profile_on_ram_disk=any(line.split(' on ', 1)[1].startswith(str(profile.resolve()) + ' (hfs')
                                for line in subprocess.run(['/sbin/mount'], capture_output=True, text=True)
                                .stdout.splitlines() if ' on ' in line),
        paid_present=sorted(n for n in PAID if n in environment))
    if summary['readback']['paid_present'] or not summary['readback']['config_dir_is_delivered_profile']:
        summary['refusal'] = 'paid_api:environment'
        (scratch / 'summary.json').write_text(json.dumps(summary, sort_keys=True))
        return 6
    sandboxed = ['/usr/bin/sandbox-exec', '-p', policy, str(PINNED)]
    status = subprocess.run(sandboxed + ['auth', 'status', '--json'], env=environment, cwd=clone,
                            stdin=subprocess.DEVNULL, capture_output=True, timeout=WAIT_HANG_SECONDS)
    try:
        report = json.loads(status.stdout)
    except ValueError:
        report = {}
    summary['login_status'] = dict(exit=status.returncode, logged_in=report.get('loggedIn') is True,
                                   method=report.get('authMethod') if report.get('authMethod') in
                                   ('claude.ai', 'none', None, 'api_key', 'oauth_token') else 'other')
    out_copy = open(scratch / 'engine.out', 'wb')
    err_copy = open(scratch / 'engine.err', 'wb')
    engine = subprocess.Popen(sandboxed + FLAGS, env=environment, cwd=clone, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Every process this run launched, command line and environment, kept for the main node's scan:
    # taken on the engine's 1st, 4th and 8th output chunk (while it works), never on a timer.
    snapshot, chunks = [], [0]

    def observe():
        chunks[0] += 1
        if chunks[0] in (1, 4, 8) and engine.poll() is None:
            snapshot.append(subprocess.run(['/bin/ps', '-E', '-ww', '-o', 'pid=,ppid=,command=', '-U',
                                            str(os.getuid())], capture_output=True, text=True).stdout)
    threads = [threading.Thread(target=pump, args=(engine.stdout, [out_copy, sys.stdout.buffer], observe)),
               threading.Thread(target=pump, args=(engine.stderr, [err_copy, sys.stderr.buffer]))]
    for thread in threads:
        thread.start()
    def forward():
        try:
            for chunk in iter(lambda: sys.stdin.buffer.read1(65536), b''):
                engine.stdin.write(chunk)
                engine.stdin.flush()
            engine.stdin.close()
        except (BrokenPipeError, ValueError, OSError):
            pass
    # The main node's input can stay open after the engine exits; the engine's exit ends the run.
    threading.Thread(target=forward, daemon=True).start()
    code = engine.wait(timeout=WAIT_HANG_SECONDS)
    for thread in threads:
        thread.join()
    out_copy.close()
    err_copy.close()
    (scratch / 'ps.txt').write_text('\n'.join(
        line for shot in snapshot for line in shot.splitlines() if 'sandbox-exec' in line
        or str(PINNED) in line or 'claude' in line.lower()))
    diff = subprocess.run(['/usr/bin/git', '-C', str(clone), 'diff'], capture_output=True, text=True).stdout
    summary.update(engine_exit=code, edit_diff=diff)
    shutil.rmtree(temp, ignore_errors=True)
    (scratch / 'summary.json').write_text(json.dumps(summary, sort_keys=True))
    return 0


def cmd_close(run):
    L = organ('project_runner_macos_login')
    base = login_base(run)
    result = L.close_profile(base)
    after = keychain()
    before = json.loads((RUNS / run / 'keychain-before.json').read_text())
    result.update(keychain_unchanged=after == before, keychain_claude_items=after['claude_items'],
                  base_absent=not base.exists())
    (RUNS / run / 'close.json').write_text(json.dumps(result, sort_keys=True))
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'closed' and result['base_absent'] else 4


def cmd_fetch(run):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name in ('summary.json', 'engine.out', 'engine.err', 'ps.txt', 'close.json', 'keychain-before.json'):
            path = RUNS / run / name
            if path.exists():
                archive.add(path, arcname=name)
    sys.stdout.buffer.write(buffer.getvalue())
    return 0


def cmd_clean(run):
    shutil.rmtree(RUNS / run, ignore_errors=True)
    print(json.dumps(dict(cleaned=not (RUNS / run).exists())))
    return 0


if __name__ == '__main__':
    command, run = sys.argv[1], checked(sys.argv[2])
    if command == 'run' and (CODE / 'role-settings.json').is_file():
        # The role's generated settings as production's handoff writes them (engine plugins off).
        FLAGS[FLAGS.index('--settings') + 1] = (CODE / 'role-settings.json').read_text()
    if command == 'run' and sys.argv[3:] == ['stderr']:
        # The engine-stderr leg: the binary's own debug stream on its error stream (--debug-to-stderr,
        # proof/VELDO-0060/cli-options.json), so the relayed record has a non-empty error stream.
        FLAGS.append('--debug-to-stderr')
    code = dict(open=cmd_open, run=cmd_run, close=cmd_close, fetch=cmd_fetch, clean=cmd_clean)[command](run)
    sys.stdout.flush(); sys.stderr.flush()
    os._exit(code)  # never wait on the input-forwarding thread
