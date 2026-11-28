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
    cannot outlive the access credential's expiry; frame() refuses, for both engines, a login
    that expires less than MARGIN_SECONDS after the run's deadline.
  Mac: `python3 project_runner_macos_login.py open <base>` reads one frame from stdin and
    mounts it at <base>/profile; `close <base>` detaches the disk and removes <base>. Both
    print one JSON line of identifiers, file names and sizes, never a value.

On the production path (VELDO-0125) the frame travels on the receiver's own SSH channel, as the
line after the prepared binding: control_launch.invoke_remote writes it, control_worker reads it
and hands it to Delivery below. It is the engine's own sign-in and the only credential a Mac run is
sent. No outside-service credential is delivered (VELDO-0254): a Mac run whose configuration names
an MCP server that needs one is refused on the main node before anything is sent, and any second
line here is refused by name.

macOS facts this relies on (recorded in proof/VELDO-0147): Claude Code on macOS reads its
login from the keychain first and, when the keychain is unreachable (the run's Seatbelt
profile denies the SecurityServer lookups), from <CLAUDE_CONFIG_DIR>/.credentials.json.
An unprivileged user can attach and format a RAM disk; it mounts with noowners, so the
0700 parent directory, not the volume's modes, is what keeps other users out of the mounted
files. The disk's two device nodes are another way to the same bytes: open_profile makes both
readable by their owner only before anything is written, and refuses a disk it cannot make so.
"""
import base64
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
MARGIN_SECONDS = 1800  # an access credential must outlive the run's deadline by this much
# The top-level fields of a Codex login file that are sent besides the access credentials: named, so a
# field a later Codex build adds is not sent until it is read and listed here.
CODEX_FIELDS = ('auth_mode', 'last_refresh')
EXPIRES = 'unavailable_service:login_expires_before_run'


class Refused(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


# ---- main node -------------------------------------------------------------------------

def _outlives(expiry, ends):
    """Refuse a login whose access credential expires less than MARGIN_SECONDS after `ends`."""
    if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or expiry - ends < MARGIN_SECONDS:
        raise Refused(EXPIRES)


def _jwt_expiry(token):
    """The `exp` of an access credential that is a JWT, or None when it cannot be read."""
    try:
        payload = token.split('.')[1]
        return json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4))).get('exp')
    except (AttributeError, IndexError, ValueError):
        return None


def _claude(profile, ends):
    document = json.loads(Path(profile, '.credentials.json').read_text())
    oauth = document.get('claudeAiOauth') or {}
    if not oauth.get('accessToken') or oauth.get('subscriptionType') in (None, ''):
        raise Refused('unsupported_configuration:no_subscription_login')
    expiry = oauth.get('expiresAt')
    _outlives(expiry / 1000 if isinstance(expiry, (int, float)) and not isinstance(expiry, bool) else None, ends)
    kept = {k: oauth[k] for k in ('accessToken', 'expiresAt', 'scopes', 'subscriptionType',
                                    'rateLimitTier') if k in oauth}
    return {'.credentials.json': json.dumps({'claudeAiOauth': kept})}, [oauth['accessToken']]


def _codex(profile, ends):
    document = json.loads(Path(profile, 'auth.json').read_text())
    tokens = document.get('tokens') or {}
    if document.get('OPENAI_API_KEY') or not tokens.get('access_token'):
        raise Refused('unsupported_configuration:no_subscription_login')
    # The Mac gets no refresh credential, so an access credential that ends during the run cannot be
    # renewed there. One whose expiry cannot be read is refused the same way.
    _outlives(_jwt_expiry(tokens['access_token']), ends)
    kept = {k: tokens[k] for k in ('id_token', 'access_token', 'account_id') if k in tokens}
    values = [v for k, v in sorted(kept.items()) if k != 'account_id' and isinstance(v, str)]
    # Codex 0.166.0 refuses a login file without this field ("missing field `refresh_token`", seen on the
    # real Mac). It is sent empty: the Mac can use the access credential but can never rotate the login.
    kept['refresh_token'] = ''
    out = {k: document[k] for k in CODEX_FIELDS if isinstance(document.get(k), str)}
    out.update(OPENAI_API_KEY=None, tokens=kept)
    return {'auth.json': json.dumps(out)}, values


def frame(engine, profile, dispatch, account, now=None, deadline=None):
    """(frame bytes, exact values to redact) for one Mac run of <engine> with <profile>. `deadline` is the
    run's own (the contract's, seconds since the epoch): the login must outlive it by MARGIN_SECONDS."""
    now = time.time() if now is None else now
    if engine not in FILES:
        raise Refused('unsupported_configuration:engine')
    ends = max(now, deadline) if isinstance(deadline, (int, float)) and not isinstance(deadline, bool) else now
    files, values = (_claude if engine == 'claude_code' else _codex)(profile, ends)
    body = json.dumps(dict(schema=SCHEMA, engine=engine, dispatch=dispatch, account=account,
                           files=files), sort_keys=True).encode() + b'\n'
    if len(body) > MAX_FRAME:
        raise Refused('invalid_input:frame_size')
    return body, values


# ---- Mac -------------------------------------------------------------------------------

def _run(argv):
    return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)


def _mounted(path):
    """The device /sbin/mount shows mounted on `path`, or None."""
    listing = _run(['/sbin/mount']).stdout
    for line in listing.splitlines():
        device, found, rest = line.partition(' on ')
        if found and rest.startswith(str(path) + ' ('):
            return device
    return None


def _nodes(device):
    """The block and the raw device node of one disk."""
    return [device, device.replace('/dev/disk', '/dev/rdisk', 1)]


def private_nodes(nodes):
    """Make each device node of the login's RAM disk readable and writable by this user only, and return
    the mode each was found with. macOS gives the nodes to the attaching user; any group or other bit lets
    another local account read the raw volume, login included. Refused by name when a node is not this
    user's or will not take the mode."""
    found = {}
    for node in nodes:
        try:
            before = os.stat(node)
            found[os.path.basename(node)] = oct(before.st_mode & 0o777)
            if before.st_uid != os.getuid():
                raise Refused('unavailable_service:ram_disk_private')
            if before.st_mode & 0o077:
                os.chmod(node, 0o600)
            if os.stat(node).st_mode & 0o077:
                raise Refused('unavailable_service:ram_disk_private')
        except OSError:
            raise Refused('unavailable_service:ram_disk_private') from None
    return found


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
        modes = dict(attached=private_nodes(_nodes(device)))
        if _run(['/sbin/newfs_hfs', '-v', 'VeldoLogin', device]).returncode != 0:
            raise Refused('unavailable_service:ram_disk_format')
        if _run(['/usr/sbin/diskutil', 'mount', '-mountPoint', str(mount), device]).returncode != 0:
            raise Refused('unavailable_service:ram_disk_mount')
        if _mounted(mount.resolve()) != device:
            raise Refused('unavailable_service:ram_disk_mount')
        # Again after the mount, in case mounting gave the nodes their first modes back; nothing of the
        # login is on the disk before this.
        modes['mounted'] = private_nodes(_nodes(device))
        modes['final'] = {os.path.basename(node): oct(os.stat(node).st_mode & 0o777) for node in _nodes(device)}
        (mount / '.metadata_never_index').touch(mode=0o600)
        os.chmod(mount, 0o700)
        sizes = {}
        for name, text in sorted(files.items()):
            descriptor = os.open(mount / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as out:
                out.write(text)
            sizes[name] = len(text.encode())
    except BaseException:
        close_profile(base, attached=device)
        raise
    return dict(status='open', engine=engine, dispatch=document.get('dispatch'),
                account=document.get('account'), device=device, ram_disk=True, device_modes=modes,
                profile_mode=oct(os.stat(mount).st_mode & 0o777), base_mode=oct(os.stat(base).st_mode & 0o777),
                files=sizes)


def close_profile(base, attached=None):
    """Detach the login's disk and remove <base>. The device name kept in <base>/device is only a name: after
    a restart it can belong to another run's login disk or to a disk the owner attached. So a disk is
    detached only when /sbin/mount shows that device on this base's own `profile` now, or when the caller
    attached it in this same call (`attached`, open_profile's own failure before the mount). Otherwise only
    the directories go."""
    base = Path(base)
    device = (base / 'device').read_text().strip() if (base / 'device').is_file() else ''
    mount = base / 'profile'
    detached = None
    ours = device.startswith('/dev/disk') and (
        device == attached or (mount.is_dir() and _mounted(mount.resolve()) == device))
    if ours:
        detached = _run(['/usr/bin/hdiutil', 'detach', '-force', device]).returncode == 0
    # Files are written only after the disk is mounted, so the bare mount point is empty here.
    if mount.is_dir() and _mounted(mount.resolve()) is None:
        mount.rmdir()
    # The name is kept while the disk is still mounted here, so a later close can detach it.
    if not mount.exists() and (base / 'device').exists():
        (base / 'device').unlink()
    if base.is_dir() and not any(base.iterdir()):
        base.rmdir()
    gone = not base.exists()
    return dict(status='closed' if gone else 'left_behind', device=device, detached=detached, removed=gone)


class Delivery:
    """One run's login frame in the Mac receiver (control_worker): checked on construction, before a
    clone or a disk is made; the login mounted before admission; detached and removed when the run ends.
    Exactly one line is accepted, and it must be the login frame of this dispatch, account and engine."""

    def __init__(self, lines, base, dispatch, account, engine):
        self.base, self.frames, self.report = Path(base), {}, {}
        lines = [line.encode() if isinstance(line, str) else line for line in lines or ()]
        if len(lines) > 1:
            raise Refused('invalid_input:frame')
        for raw in lines:
            if len(raw) > MAX_FRAME:
                raise Refused('invalid_input:frame_size')
            try:
                document = json.loads(raw)
            except ValueError:
                raise Refused('invalid_input:frame')
            kind = 'login' if isinstance(document, dict) and document.get('schema') == SCHEMA else None
            if kind is None:
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
