"""Deliver a dispatch's account login to the Mac for one run, in memory only, VELDO-0147.

The main node holds every login. A Mac compute node never keeps one: for one run it gets
the dispatch's account profile on a RAM disk (hdiutil ram://, never backed by a file),
mounted at a private mount point inside a 0700 directory, and the disk is detached when the
run ends. Nothing reaches the Mac's keychain, a command line or the Mac's disk.

Two halves, one file, so both ends agree on the frame:

  Main node (Linux): frame(engine, profile) reads the account's own login directory
    (CLAUDE_CONFIG_DIR or CODEX_HOME) and returns the frame bytes and the exact values the
    run's redaction set must replace. The frame carries an access credential only: the
    refresh credential stays on the main node, because a refresh on the Mac would rotate
    it and log the main node's own copy out (one login, one holder). A Mac run therefore
    cannot outlive the access credential's expiry; frame() refuses one that would.
  Mac: `python3 project_runner_macos_login.py open <base>` reads one frame from stdin and
    mounts it at <base>/profile; `close <base>` detaches the disk and removes <base>. Both
    print one JSON line of identifiers, file names and sizes, never a value.

On the production path (VELDO-0125) both frames travel on the receiver's own SSH channel, as the
lines after the prepared binding: control_launch.invoke_remote writes them, control_worker reads
them and hands them to Delivery below. The second frame is the secrets frame (AC4): the run's MCP
servers with their credential values, written as one 0600 file in a 0700 directory on the same RAM
disk only after the authority accepted the launch, and gone with the disk when the run ends.

macOS facts this relies on (recorded in proof/VELDO-0147): Claude Code on macOS reads its
login from the keychain first and, when the keychain is unreachable (the run's Seatbelt
profile denies the SecurityServer lookups), from <CLAUDE_CONFIG_DIR>/.credentials.json.
An unprivileged user can attach and format a RAM disk; it mounts with noowners, so the
0700 parent directory, not the volume's modes, is what keeps other users out.
"""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCHEMA = 'veldo.macos_login_frame/v1'
MAX_FRAME = 256 * 1024
DISK_SECTORS = 16384  # 8 MiB of RAM: a login profile is a few kilobytes.
FILES = {'claude_code': ('.credentials.json',), 'codex': ('auth.json',)}
MARGIN_SECONDS = 1800  # an access credential must outlive the run by this much
SECRETS_SCHEMA = 'veldo.macos_secrets_frame/v1'
SECRETS_DIRECTORY, SECRETS_FILE = 'secrets', 'mcp.json'


class Refused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---- main node -------------------------------------------------------------------------

def _claude(profile, now):
    document = json.loads(Path(profile, '.credentials.json').read_text())
    oauth = document.get('claudeAiOauth') or {}
    if not oauth.get('accessToken') or oauth.get('subscriptionType') in (None, ''):
        raise Refused('unsupported_configuration:no_subscription_login')
    if oauth.get('expiresAt', 0) / 1000 - now < MARGIN_SECONDS:
        raise Refused('unavailable_service:login_expires_before_run')
    kept = {k: oauth[k] for k in ('accessToken', 'expiresAt', 'scopes', 'subscriptionType',
                                    'rateLimitTier') if k in oauth}
    return {'.credentials.json': json.dumps({'claudeAiOauth': kept})}, [oauth['accessToken']]


def _codex(profile, now):
    document = json.loads(Path(profile, 'auth.json').read_text())
    tokens = document.get('tokens') or {}
    if document.get('OPENAI_API_KEY') or not tokens.get('access_token'):
        raise Refused('unsupported_configuration:no_subscription_login')
    kept = {k: tokens[k] for k in ('id_token', 'access_token', 'account_id') if k in tokens}
    values = [v for k, v in sorted(kept.items()) if k != 'account_id' and isinstance(v, str)]
    out = {k: document[k] for k in document if k not in ('tokens', 'OPENAI_API_KEY')}
    out.update(OPENAI_API_KEY=None, tokens=kept)
    return {'auth.json': json.dumps(out)}, values


def frame(engine, profile, dispatch, account, now=None):
    """(frame bytes, exact values to redact) for one Mac run of <engine> with <profile>."""
    now = time.time() if now is None else now
    if engine not in FILES:
        raise Refused('unsupported_configuration:engine')
    files, values = (_claude if engine == 'claude_code' else _codex)(profile, now)
    body = json.dumps(dict(schema=SCHEMA, engine=engine, dispatch=dispatch, account=account,
                           files=files), sort_keys=True).encode() + b'\n'
    if len(body) > MAX_FRAME:
        raise Refused('invalid_input:frame_size')
    return body, values


def secrets_frame(dispatch, account, servers, credentials):
    """The one secrets frame of a Mac run: `servers` is the MCP configuration's server entries with
    their credential values in place, `credentials` the ids of the credentials inside it."""
    text = json.dumps({'mcpServers': servers}, sort_keys=True)
    body = json.dumps(dict(schema=SECRETS_SCHEMA, dispatch=dispatch, account=account,
                           credentials=sorted(credentials), files={SECRETS_FILE: text}),
                      sort_keys=True).encode() + b'\n'
    if len(body) > MAX_FRAME:
        raise Refused('invalid_input:frame_size')
    return body


# ---- Mac -------------------------------------------------------------------------------

def _run(argv):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)


def _mounted(path):
    listing = _run(['/sbin/mount']).stdout
    return any(line.split(' on ', 1)[1].startswith(str(path) + ' (') for line in listing.splitlines()
               if ' on ' in line)


def open_profile(base, stream):
    base = Path(base)
    if base.exists() or not base.is_absolute():
        raise Refused('stale_version:profile_base_exists')
    raw = stream.buffer.read(MAX_FRAME + 1) if hasattr(stream, 'buffer') else stream.read(MAX_FRAME + 1)
    if len(raw) > MAX_FRAME:
        raise Refused('invalid_input:frame_size')
    try:
        document = json.loads(raw)
    except ValueError:
        raise Refused('invalid_input:frame')
    if not isinstance(document, dict):
        raise Refused('invalid_input:frame')
    engine = document.get('engine')
    if document.get('schema') != SCHEMA or engine not in FILES:
        raise Refused('invalid_input:frame')
    files = document.get('files') or {}
    if set(files) != set(FILES[engine]) or not all(isinstance(v, str) for v in files.values()):
        raise Refused('invalid_input:frame_files')
    os.umask(0o077)
    base.mkdir(mode=0o700)
    mount = base / 'profile'
    mount.mkdir(mode=0o700)
    attached = _run(['/usr/bin/hdiutil', 'attach', '-nomount', '-nobrowse', 'ram://%d' % DISK_SECTORS])
    device = attached.stdout.strip().split()[0] if attached.returncode == 0 and attached.stdout.strip() else ''
    if not device.startswith('/dev/disk'):
        base.joinpath('profile').rmdir(); base.rmdir()
        raise Refused('unavailable_service:ram_disk')
    (base / 'device').write_text(device + '\n')
    try:
        if _run(['/sbin/newfs_hfs', '-v', 'VeldoLogin', device]).returncode != 0:
            raise Refused('unavailable_service:ram_disk_format')
        if _run(['/usr/sbin/diskutil', 'mount', '-mountPoint', str(mount), device]).returncode != 0:
            raise Refused('unavailable_service:ram_disk_mount')
        if not _mounted(mount.resolve()):
            raise Refused('unavailable_service:ram_disk_mount')
        (mount / '.metadata_never_index').touch(mode=0o600)
        os.chmod(mount, 0o700)
        sizes = {}
        for name, text in sorted(files.items()):
            descriptor = os.open(mount / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as out:
                out.write(text)
            sizes[name] = len(text.encode())
    except BaseException:
        close_profile(base)
        raise
    return dict(status='open', engine=engine, dispatch=document.get('dispatch'),
                account=document.get('account'), device=device, ram_disk=True,
                profile_mode=oct(os.stat(mount).st_mode & 0o777), base_mode=oct(os.stat(base).st_mode & 0o777),
                files=sizes)


def close_profile(base):
    base = Path(base)
    device = (base / 'device').read_text().strip() if (base / 'device').is_file() else ''
    mount = base / 'profile'
    detached = None
    if device.startswith('/dev/disk'):
        detached = _run(['/usr/bin/hdiutil', 'detach', '-force', device]).returncode == 0
    # Files are written only after the disk is mounted, so the bare mount point is empty here.
    if mount.is_dir() and not _mounted(mount.resolve()):
        mount.rmdir()
    if (base / 'device').exists():
        (base / 'device').unlink()
    if base.is_dir() and not any(base.iterdir()):
        base.rmdir()
    gone = not base.exists()
    return dict(status='closed' if gone else 'left_behind', device=device, detached=detached, removed=gone)


def write_secrets(base, raw):
    """Write the secrets frame's one file on the run's RAM disk; return ids and sizes, never a value."""
    document = json.loads(raw)
    files = document.get('files') or {}
    credentials = document.get('credentials')
    if (set(files) != {SECRETS_FILE} or not isinstance(files[SECRETS_FILE], str)
            or not isinstance(credentials, list) or not all(isinstance(c, str) for c in credentials)):
        raise Refused('invalid_input:frame_files')
    mount = Path(base) / 'profile'
    if not _mounted(mount.resolve()):
        raise Refused('unavailable_service:ram_disk_mount')
    directory = mount / SECRETS_DIRECTORY
    os.mkdir(directory, 0o700)
    descriptor = os.open(directory / SECRETS_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w') as out:
        out.write(files[SECRETS_FILE])
    return dict(status='written', credentials=credentials, file=SECRETS_DIRECTORY + '/' + SECRETS_FILE,
                size=len(files[SECRETS_FILE].encode()),
                file_mode=oct(os.stat(directory / SECRETS_FILE).st_mode & 0o777),
                directory_mode=oct(os.stat(directory).st_mode & 0o777))


class Delivery:
    """One run's frames in the Mac receiver (control_worker): checked on construction, before a clone
    or a disk is made; the login mounted before admission; the secrets file written only after the
    authority accepted the launch; everything detached and removed when the run ends."""

    def __init__(self, lines, base, dispatch, account, engine):
        self.base, self.frames, self.report = Path(base), {}, {}
        lines = [line.encode() if isinstance(line, str) else line for line in lines or ()]
        if len(lines) > 2:
            raise Refused('invalid_input:frame')
        for raw in lines:
            if len(raw) > MAX_FRAME:
                raise Refused('invalid_input:frame_size')
            try:
                document = json.loads(raw)
            except ValueError:
                raise Refused('invalid_input:frame')
            kind = {SCHEMA: 'login', SECRETS_SCHEMA: 'secrets'}.get(
                document.get('schema') if isinstance(document, dict) else None)
            if kind is None or kind in self.frames:
                raise Refused('invalid_input:frame')
            if document.get('dispatch') != dispatch or document.get('account') != account:
                raise Refused('binding_mismatch:' + kind + '_frame')
            self.frames[kind] = raw
        if 'login' not in self.frames:
            raise Refused('missing_evidence:login_frame')
        if json.loads(self.frames['login']).get('engine') != engine:
            raise Refused('binding_mismatch:login_frame')

    def open(self):
        """Mount the login; the directory the account's login variable names for this run."""
        self.report['login'] = open_profile(self.base, io.BytesIO(self.frames['login']))
        return str(self.base / 'profile')

    def secrets(self):
        if 'secrets' in self.frames:
            self.report['secrets'] = write_secrets(self.base, self.frames['secrets'])

    def close(self):
        if self.base.exists():
            self.report['close'] = close_profile(self.base)
        return self.report.get('close')


def main(argv):
    if len(argv) != 3 or argv[1] not in ('open', 'close'):
        print(json.dumps(dict(status='refused', refusal='invalid_input:usage')))
        return 2
    try:
        result = open_profile(argv[2], sys.stdin) if argv[1] == 'open' else close_profile(argv[2])
    except Refused as error:
        print(json.dumps(dict(status='refused', refusal=error.code)))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] in ('open', 'closed') else 4


if __name__ == '__main__':
    sys.exit(main(sys.argv))
