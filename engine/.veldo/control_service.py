#!/usr/bin/env python3
"""The authority service: installation, explicit start and stop, one scheduling instance under a
stable lock, signed local commands applied to the configured store, and nothing in its place while it
is absent (PLAN-0019 W32, VELDO-0047, design R75).

    python3 control_service.py install --workspace <enrolled clone> [--workspace ...] [options]
    python3 control_service.py start|stop|status|uninstall <unit>
    python3 control_service.py serve <installed service.json>      (what systemd runs)

INSTALLATION (`install`) is the one authorized step that lays an instance down, and it starts
nothing. For the enrolled workspaces of ONE coordination domain it verifies every enrollment binding
under this host's installed trust (control_eligibility.load_host_trust, the HostTrust every enrolled
entry point uses) and then lays down, under <install root>/<service id>:

  bin/     the FIXED EXECUTABLE: this module and the closure of modules it and the launch receiver
           load (CLOSURE), copied byte for byte and read-only (0400, the three entry points 0500, the
           directory 0500). The unit runs this copy, never a repository's.
  config/  the PROTECTED CONFIGURATION (0700): service.json (0600), a copy of the enrollment signers
           this host trusted at installation (0600), and one launch receiver configuration per
           repository (receiver-<repository>.json, 0600) naming this host's QUALIFIED linux-systemd
           worker profile (slice, lock and caps), without which the receiver launches nothing.
  state/   the service's observation log (0700).

and the unit, rendered from services/veldo-authority.service, in the owner's systemd user unit
directory. The key directory holding the journal signing key is placed outside the home and
temporary directories (KEY DIRECTORY below). A refused installation leaves nothing behind.

START AND STOP are explicit operations actions (`start`, `stop`, or systemctl --user start|stop
<unit>). The unit has no [Install] section and no Restart=, so nothing starts the authority at login
and an unexpected exit leaves it stopped, its committed store intact, until an operator starts it
again (automatic recovery is Release 2). Running while logged out needs systemd user-service
persistence (lingering), which is established separately.

ONE INSTANCE. `serve` takes an exclusive flock on a STABLE lock file beside the store
(<store directory>/authority.lock) before it opens the store or touches the socket. The file is
created once and never deleted or replaced, so every instance contends for one inode. A second
instance, by hand or through any unit, refuses as authority_lock_held (exit EXIT_LOCK_HELD) and
changes nothing: the first keeps its socket, its store and its lock.

THE REQUEST PATH. The socket is VELDO-0107's, beside the store (control_client.socket_path_for), 0600
in a 0700 directory, and control_client.Authority judges every request: the kernel's peer identity,
the request signature, and the workspace coordinate the request carries, resolved through its signed
enrollment binding. The request signature is verified against the store's own active keyring
(namespace veldo-command), the binding's under the enrollment signers installed with this instance
(namespace veldo-enrollment). One verifier serves both, keyed by the signed object's own schema, so
neither signature can stand in for the other. An accepted request reaches `apply` with its judged
coordinates; a repository this instance does not serve is refused. Then, by the packet:

  {"operation": "inspect", "entity_ids": [...]}   read-only: the watermark, the journal head, the
      named entities, the counts and the pending work.
  {"command": <claim command>, "signature": ...}  a claim operation, through control_claim.Receiver
      on this store (VELDO-0031), which authenticates the holder itself.
  {"command": <store command>, "signature": ...}  one of control_store's own generic commands
      (MUTATIONS). The command names domain_uuid, repository_uuid and store_uuid, which must be this
      store's and the request's own; its principal is an active member of a type admitted at command
      acceptance, whose scope covers the repository and whose active key signed the command
      (control_store.canonical_bytes). control_store.execute then commits it on the CONFIGURED store,
      and the answer is the committed receipt with the store's own watermark.

KEY DIRECTORY. The custody wrapper (VELDO-0067) denies a confined worker every file created directly
in an ancestor of a protected directory after the worker starts, so the key directory belongs where
workers never write directly: outside the home and temporary directories. On a host where this
account can create nothing else, placing it takes one root step, and installation refuses naming
that step exactly (missing_authority:key_directory:absent). The default is
/var/lib/veldo/keys/<service id>.

WHAT IT IS NOT. No automatic restart or recovery (Release 2), no second host profile, remote
inspection or legacy status listener (Release 4), no network listener. Standard library only.
"""
import contextlib
import fcntl
import grp
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import signal
import socket
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent


def _organ(name):
    spec = importlib.util.spec_from_file_location('authority_service_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CC = _organ('control_client')
E = _organ('control_enrollment')
CLM = _organ('control_claim')
S, CM, AC = CLM.S, CLM.CM, CLM.AC
EL = _organ('control_eligibility')
SIG = _organ('control_signer')
L = _organ('control_launch')
C = L.C

# The store's own generic commands, taken before any service registers one of its own on this module
# (control_claim.Receiver adds claim_operation), so a claim transition is never reachable as one.
MUTATIONS = tuple(sorted(S.COMMAND_REGISTRY))

# The fixed executable: every module the service and the launch receiver it configures load.
CLOSURE = ('authority_contract.py', 'claim.py', 'completion_contract.py',
           'control_channel_attribution.py', 'control_channel_enrollment.py',
           'control_channel_presentation.py', 'control_channel_projection.py', 'control_claim.py',
           'control_client.py', 'control_containment.py', 'control_decision_dependency.py',
           'control_dispatch.py', 'control_eligibility.py', 'control_enrollment.py', 'control_keys.py',
           'control_keys_custody.py', 'control_launch.py', 'control_membership.py',
           'control_reservations.py', 'control_service.py', 'control_signer.py',
           'control_signer_answers.py', 'control_snapshot.py', 'control_store.py', 'git_process.py')
ENTRY_POINTS = ('control_service.py', 'control_launch.py', 'control_keys_custody.py')

SCHEMA = 'veldo.authority_service/v1'
UNIT_SCHEMA = 'veldo.authority_unit/v1'
TEMPLATE = HERE / 'services' / 'veldo-authority.service'
LOCK_NAME = 'authority.lock'
DEFAULT_KEY_ROOT = '/var/lib/veldo/keys'
JOURNAL_KEY = 'journal'
EXIT_LOCK_HELD = 75
EXIT_REFUSED = 78
# The kernel's limit on a local socket path (sun_path), terminator included.
SOCKET_PATH_LIMIT = 108
ACTIVE_STATES = ('active', 'activating', 'deactivating', 'reloading', 'refreshing')
UNIT_NAME = re.compile(re.escape(CC.SERVICE_PREFIX) + r'[0-9a-f]{16}\.service')
# What may appear in a value written into the unit: nothing systemd would read as a specifier,
# a quote, a separator or a second argument.
UNIT_VALUE = re.compile(r'[A-Za-z0-9._/+-]+')

# The error taxonomy (the spec's observability contract). A refusal code's first part names its
# class, or the code is one of the named codes below; anything else is an unknown outcome, never
# success.
CLASSES = ('invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service',
           'missing_evidence', 'unknown_outcome')
NAMED = {
    'authority_lock_held': 'unavailable_service', 'not_authorized': 'missing_authority',
    'malformed_request': 'invalid_input', 'peer_not_authorized': 'missing_authority',
    'command_signature_invalid': 'missing_authority', 'coordinate_not_served': 'invalid_input',
    'unenrolled_workspace': 'missing_authority', 'peer_identity_unavailable': 'missing_authority',
    'authority_unavailable': 'unavailable_service', 'malformed_command': 'invalid_input',
    'unregistered_operation': 'invalid_input', 'transition_refused': 'invalid_input',
    'command_content_conflict': 'stale_subject', 'stale_version': 'stale_subject',
    'nonce_consumed': 'stale_subject', 'foreign_key_violation': 'invalid_input',
    'entity_owned': 'missing_authority', 'foreign_transition': 'missing_authority',
    'read_only_handle': 'unavailable_service', 'incomplete_transaction': 'unknown_outcome',
    'unowned': 'stale_subject', 'not_owner': 'missing_authority', 'stale_generation': 'stale_subject',
    'capability': 'missing_authority', 'parked': 'stale_subject', 'ownership_uncertain': 'unknown_outcome',
}


class Refused(Exception):
    """A named refusal: `code` (its class is taxonomy(code)), a detail without secrets, and, where an
    operator can act, the exact guidance."""

    def __init__(self, code, detail='', guidance=None):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail, self.guidance = code, detail, guidance


def taxonomy(code):
    head = str(code).split(':', 1)[0]
    return head if head in CLASSES else NAMED.get(head, 'unknown_outcome')


def _digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------------------------
# The key directory: outside every directory a worker writes into directly
# ---------------------------------------------------------------------------------------------

def worker_writable(environment=None):
    """Every directory a worker of this account writes into directly: the home directory (the
    account's own and the environment's) and the temporary directories (the platform's, the
    environment's, /tmp, /var/tmp, /dev/shm and the runtime directory). The environment only ever
    ADDS a place here; nothing read from it can take one away."""
    env = os.environ if environment is None else environment
    roots = {pwd.getpwuid(os.getuid()).pw_dir, '/tmp', '/var/tmp', '/dev/shm', tempfile.gettempdir(),
             '/run/user/%d' % os.getuid()}
    for name in ('HOME', 'TMPDIR', 'TEMP', 'TMP', 'XDG_RUNTIME_DIR'):
        value = env.get(name)
        if isinstance(value, str) and os.path.isabs(value):
            roots.add(value)
    return sorted({os.path.realpath(root) for root in roots})


def _within(path, root):
    return path == root or path.startswith(root.rstrip('/') + '/')


def key_directory_problems(path, writable):
    """Why `path` may not hold the protected keys, as named codes; [] when it may. It must exist as a
    real directory of this account that nobody else can enter, and be neither inside nor above any
    directory in `writable`."""
    text = str(path)
    if not os.path.isabs(text):
        return ['invalid_input:key_directory:relative']
    try:
        info = os.lstat(text)
    except FileNotFoundError:
        return ['missing_authority:key_directory:absent']
    except OSError:
        return ['unavailable_service:key_directory:unreadable']
    if stat.S_ISLNK(info.st_mode):
        return ['invalid_input:key_directory:symlink']
    if not stat.S_ISDIR(info.st_mode):
        return ['invalid_input:key_directory:not_a_directory']
    problems = []
    if info.st_uid != os.getuid():
        problems.append('invalid_input:key_directory:owner')
    real = os.path.realpath(text)
    if any(_within(real, os.path.realpath(root)) or _within(os.path.realpath(root), real) for root in writable):
        problems.append('invalid_input:key_directory:worker_writable')
    if stat.S_IMODE(info.st_mode) & 0o077:
        problems.append('invalid_input:key_directory:mode')
    return problems


def key_directory_guidance(path, code):
    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name
    if code.endswith(':absent'):
        return ('create it once as root, outside the home and temporary directories, owned by %s and '
                'closed to everyone else: sudo install -d -m 0755 %s && sudo install -d -m 0700 -o %s '
                '-g %s %s' % (user, os.path.dirname(str(path)), user, group, path))
    if code.endswith(':mode'):
        return 'close it to everyone else: chmod 0700 %s' % path
    if code.endswith(':owner'):
        return 'it must belong to %s: sudo chown %s:%s %s' % (user, user, group, path)
    return ('choose a directory outside the home and temporary directories, for example %s/<service id>, '
            'created once as root and owned by %s' % (DEFAULT_KEY_ROOT, user))


# ---------------------------------------------------------------------------------------------
# systemd, through a runner (a fake drives it in tests; nothing here runs systemctl otherwise)
# ---------------------------------------------------------------------------------------------

class Systemctl:
    """`systemctl --user <args>` against the owner's user manager, never prompting."""

    def run(self, args):
        env = C.tool_environment()
        proc = subprocess.run(['systemctl', '--user'] + list(args), capture_output=True, text=True,
                              timeout=60, env=env, stdin=subprocess.DEVNULL)
        return proc.returncode, proc.stdout, proc.stderr


def _unit(unit):
    if not isinstance(unit, str) or not UNIT_NAME.fullmatch(unit):
        raise Refused('invalid_input:unit', 'not an authority unit name')
    return unit


def status(unit, runner=None):
    """What the user manager reports for the unit: load and active state, main pid, restarts."""
    rc, out, _err = (runner or Systemctl()).run(
        ['show', '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID', '-p', 'NRestarts',
         '-p', 'Result', '-p', 'FragmentPath', _unit(unit)])
    shown = dict(line.split('=', 1) for line in out.splitlines() if '=' in line)
    return dict(shown, unit=unit, show_rc=rc)


def start(unit, runner=None):
    """The explicit operations start. The only path in this module that starts the service."""
    runner = runner or Systemctl()
    rc, _out, err = runner.run(['start', _unit(unit)])
    return dict(status(unit, runner), start_rc=rc, error=err.strip()[:400])


def stop(unit, runner=None):
    """The explicit operations stop; the unit stays stopped until an explicit start."""
    runner = runner or Systemctl()
    rc, _out, err = runner.run(['stop', _unit(unit)])
    return dict(status(unit, runner), stop_rc=rc, error=err.strip()[:400])


def default_install_root(environment=None):
    env = os.environ if environment is None else environment
    base = env.get('XDG_DATA_HOME') or ''
    if not os.path.isabs(base):
        base = os.path.join(pwd.getpwuid(os.getuid()).pw_dir, '.local', 'share')
    return os.path.join(base, 'veldo', 'authority')


def default_unit_dir():
    return _organ('supervisor').user_unit_dir()


def host_profile(install_root):
    """This host's default worker profile (VELDO-0040's linux-systemd provider): the shared worker
    slice, one admission lock for this host's installations, and every required cap."""
    return {'kind': C.LINUX, 'slice': C.DEFAULT_SLICE, 'lock': os.path.join(str(install_root), 'workers.lock'),
            'concurrency': 2, 'runtime_seconds': 4 * 3600, 'memory_bytes': 8 << 30,
            'cpu_percent': 100 * min(2, os.cpu_count() or 1), 'file_bytes': 4 << 30, 'tasks_max': 1024,
            'stop_grace_seconds': 10, 'kill_grace_seconds': 5}


def unit_text(values):
    """The unit, from the template, with every field filled and nothing systemd could misread."""
    text = TEMPLATE.read_text()
    for name, value in values.items():
        if not isinstance(value, str) or not UNIT_VALUE.fullmatch(value):
            raise Refused('invalid_input:unit_value:' + name.lower(), 'a value the unit cannot carry safely')
        text = text.replace('@%s@' % name, value)
    if re.search(r'@[A-Z_]+@', text) or UNIT_SCHEMA not in text:
        raise Refused('invalid_input:unit_template', 'the unit template is not %s' % UNIT_SCHEMA)
    return text


def _write(path, data, mode):
    """A new file with exactly `mode`, never through a link and never over an existing one."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data if isinstance(data, bytes) else data.encode('utf-8'))
    os.chmod(str(path), mode)


def _json(value):
    return json.dumps(value, indent=1, sort_keys=True) + '\n'


def _remove_tree(path):
    for directory, _dirs, _files in os.walk(str(path)):
        with contextlib.suppress(OSError):
            os.chmod(directory, 0o700)
    shutil.rmtree(str(path))


def install(workspaces, *, host_trust=None, key_directory=None, install_root=None, unit_dir=None,
            profile=None, adapters=None, writable=None, principal='authority',
            receiver_principal='launch-receiver', runner=None, python=None):
    """Lay down one authority instance for the enrolled `workspaces` of one domain. Starts nothing.
    Every check runs before anything is written; a refusal raises Refused and leaves nothing behind.
    Returns what it laid down."""
    runner = runner or Systemctl()
    python = os.path.realpath(python or sys.executable)
    trust_path = host_trust or EL.host_trust_path()
    try:
        trust = EL.load_host_trust(trust_path)
    except EL.Stopped as error:
        raise Refused('missing_authority:host_trust:' + error.reason, 'this host has no readable trust')
    if trust is None:
        raise Refused('missing_authority:host_trust:absent', 'this host has installed no trust',
                      'install this host\'s trust (%s) naming its identity and enrollment signers' % trust_path)
    workspaces = [os.path.realpath(str(w)) for w in (workspaces or [])]
    if not workspaces:
        raise Refused('invalid_input:workspaces', 'an installation serves at least one enrolled workspace')
    bindings = {}
    for workspace in workspaces:
        try:
            binding = E.read_binding(workspace)
            if binding is None:
                raise Refused('missing_authority:enrollment:not_enrolled', workspace)
            found = E.verify_binding(workspace, binding, trust.verifier(binding.get('enrolled_by'), workspace),
                                     trust.host_identity)
        except (E.EnrollmentRefused, EL.Stopped) as error:
            raise Refused('missing_authority:enrollment:' + getattr(error, 'reason', 'unanswerable'), workspace)
        if found:
            raise Refused('missing_authority:enrollment:' + found[0][0], workspace)
        bindings[workspace] = binding
    first = bindings[workspaces[0]]
    for binding in bindings.values():
        if any(binding[k] != first[k] for k in ('domain_uuid', 'store_uuid', 'store_path', 'authority_generation')):
            raise Refused('invalid_input:enrollment:domain', 'one instance serves one domain and one store')
    service, unit = CC.service_id(first), CC.service_unit(first)
    root = os.path.realpath(str(install_root or default_install_root()))
    home = os.path.join(root, service)
    unit_dir = os.path.realpath(str(unit_dir or default_unit_dir()))
    unit_path = os.path.join(unit_dir, unit)
    keys = os.path.realpath(str(key_directory)) if key_directory else os.path.join(DEFAULT_KEY_ROOT, service)
    problems = key_directory_problems(keys, worker_writable() if writable is None else writable)
    if problems:
        raise Refused(problems[0], keys, key_directory_guidance(keys, problems[0]))
    journal = os.path.join(keys, JOURNAL_KEY)
    if os.path.lexists(journal):
        info = os.lstat(journal)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise Refused('invalid_input:journal_key:mode', journal, 'chmod 0600 %s' % journal)
    profile = host_profile(root) if profile is None else profile
    qualification = C.qualify(profile)
    if not qualification['qualified']:
        raise Refused(qualification['refusal'], 'the worker profile is not qualified on this host')
    adapters = {} if adapters is None else adapters
    if not isinstance(adapters, dict) or not all(isinstance(v, dict) and isinstance(v.get('argv'), list)
                                                 for v in adapters.values()):
        raise Refused('invalid_input:adapters', 'adapters map each name to {argv: [...]}')
    for path in (home, unit_path):
        if os.path.lexists(path):
            raise Refused('invalid_input:already_installed', path,
                          'stop and uninstall it first: python3 control_service.py uninstall %s' % unit)
    if any(_within(home, w) or _within(w, home) for w in workspaces):
        raise Refused('invalid_input:install_root:inside_workspace', home)
    if len(os.fsencode(CC.socket_path_for(first))) >= SOCKET_PATH_LIMIT:
        raise Refused('invalid_input:socket:too_long', CC.socket_path_for(first),
                      'enroll the store at a shorter path: a local socket path holds under %d bytes' % SOCKET_PATH_LIMIT)
    signers = Path(os.path.realpath(trust.enrollment_signers)).read_bytes()
    repositories = {}
    for workspace, binding in bindings.items():
        repositories.setdefault(binding['repository_uuid'], []).append(workspace)
    bin_dir, config_dir, state_dir = (os.path.join(home, n) for n in ('bin', 'config', 'state'))
    config_path = os.path.join(config_dir, 'service.json')
    values = {'SERVICE': service, 'DOMAIN': first['domain_uuid'], 'STORE': first['store_uuid'],
              'PYTHON': python, 'EXECUTABLE': os.path.join(bin_dir, 'control_service.py'), 'CONFIG': config_path}
    text = unit_text(values)
    closure = {name: (HERE / name).read_bytes() for name in CLOSURE}

    created, generated = [], False
    try:
        os.makedirs(os.path.dirname(first['store_path']), mode=0o700, exist_ok=True)
        os.makedirs(root, exist_ok=True)
        os.mkdir(home, 0o700)
        created.append(home)
        for directory in (bin_dir, config_dir, state_dir):
            os.mkdir(directory, 0o700)
        for name, data in closure.items():
            _write(os.path.join(bin_dir, name), data, 0o500 if name in ENTRY_POINTS else 0o400)
        os.chmod(bin_dir, 0o500)
        if not os.path.lexists(journal):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'veldo-authority-' + service,
                            '-f', journal], check=True, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            generated = True
            os.chmod(journal, 0o600)
        _write(os.path.join(config_dir, 'enrollment_signers'), signers, 0o600)
        receivers = {}
        for repository, members in sorted(repositories.items()):
            path = os.path.join(config_dir, 'receiver-%s.json' % hashlib.sha256(repository.encode()).hexdigest()[:16])
            _write(path, _json({'store': first['store_path'], 'journal_key': journal, 'principal': receiver_principal,
                                'domain': first['domain_uuid'], 'repository': repository,
                                'authority_generation': first['authority_generation'], 'workspace': members[0],
                                'profile': profile, 'adapters': adapters}), 0o600)
            receivers[repository] = path
        config = {'schema': SCHEMA, 'service': service, 'unit': unit, 'domain_uuid': first['domain_uuid'],
                  'store_uuid': first['store_uuid'], 'store_path': first['store_path'],
                  'socket': CC.socket_path_for(first), 'lock': os.path.join(os.path.dirname(first['store_path']), LOCK_NAME),
                  'host_identity': trust.host_identity, 'authority_generation': first['authority_generation'],
                  'repositories': repositories, 'enrollments': {w: E.binding_digest(b) for w, b in bindings.items()},
                  'enrollment_signers': os.path.join(config_dir, 'enrollment_signers'), 'principal': principal,
                  'journal_key': journal, 'key_directory': keys,
                  'observations': os.path.join(state_dir, 'observations.jsonl'),
                  'executable': values['EXECUTABLE'], 'python': python,
                  'receiver': {'executable': os.path.join(bin_dir, 'control_launch.py'), 'configs': receivers},
                  'closure': {name: _digest(data) for name, data in closure.items()},
                  'template': _digest(TEMPLATE.read_bytes())}
        _write(config_path, _json(config), 0o600)
        os.makedirs(unit_dir, exist_ok=True)
        _write(unit_path, text, 0o644)
        created.append(unit_path)
    except BaseException:
        for path in reversed(created):
            with contextlib.suppress(OSError):
                if os.path.isdir(path):
                    _remove_tree(path)
                else:
                    os.unlink(path)
        if generated:
            for path in (journal, journal + '.pub'):
                with contextlib.suppress(OSError):
                    os.unlink(path)
        raise
    reload_rc, _out, _err = runner.run(['daemon-reload'])
    return {'service': service, 'unit': unit, 'unit_path': unit_path, 'home': home, 'config': config_path,
            'executable': values['EXECUTABLE'], 'receiver': config['receiver'], 'key_directory': keys,
            'journal_key': journal, 'journal_key_generated': generated, 'profile': qualification,
            'socket': config['socket'], 'lock': config['lock'], 'repositories': repositories,
            'daemon_reload_rc': reload_rc, 'started': False}


def uninstall(unit, *, install_root=None, unit_dir=None, runner=None):
    """Remove an installed instance: refuses while it runs (stop it first); keeps the store, its lock
    and the key directory, which are evidence and not the installation's to discard."""
    runner = runner or Systemctl()
    state = status(unit, runner)
    if state.get('ActiveState') in ACTIVE_STATES:
        raise Refused('invalid_input:active', unit, 'stop it first: systemctl --user stop %s' % unit)
    service = unit[len(CC.SERVICE_PREFIX):-len('.service')]
    home = os.path.join(os.path.realpath(str(install_root or default_install_root())), service)
    unit_path = os.path.join(os.path.realpath(str(unit_dir or default_unit_dir())), unit)
    removed = []
    if os.path.lexists(unit_path):
        os.unlink(unit_path)
        removed.append(unit_path)
    runner.run(['reset-failed', unit])
    runner.run(['daemon-reload'])
    if os.path.isdir(home):
        _remove_tree(home)
        removed.append(home)
    return {'unit': unit, 'removed': removed}


# ---------------------------------------------------------------------------------------------
# The service process
# ---------------------------------------------------------------------------------------------

def load_config(path):
    """The installed configuration, refused unless it is this account's own regular file that nobody
    else can read or write."""
    try:
        info = os.lstat(str(path))
    except OSError:
        raise Refused('missing_authority:config:absent', str(path))
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise Refused('invalid_input:config:mode', str(path), 'chmod 0600 %s' % path)
    try:
        config = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        raise Refused('invalid_input:config:unreadable', str(path))
    if not isinstance(config, dict) or config.get('schema') != SCHEMA:
        raise Refused('invalid_input:config:schema', str(path))
    return config


def acquire(path, config):
    """The one scheduling session: an exclusive flock on the stable lock file, which is created once
    and never removed. Refuses as authority_lock_held while another instance holds it."""
    fd = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        holder = os.pread(fd, 4096, 0).decode('utf-8', 'replace').strip()
        os.close(fd)
        raise Refused('authority_lock_held', 'another instance holds %s (%s)' % (path, holder or 'unknown'),
                      'one instance serves this store; stop it with systemctl --user stop %s' % config.get('unit'))
    os.ftruncate(fd, 0)
    os.pwrite(fd, json.dumps({'pid': os.getpid(), 'unit': config.get('unit'), 'since': time.time()}).encode(), 0)
    return fd


def notify(message):
    """sd_notify: tell the user manager our state (READY, STOPPING). False when nothing listens."""
    address = os.environ.get('NOTIFY_SOCKET')
    if not address:
        return False
    if address.startswith('@'):
        address = '\0' + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC) as channel:
        channel.connect(address)
        channel.sendall(message.encode('utf-8'))
    return True


def find_principals(signature, signers):
    """The principals whose key in `signers` made `signature` (no verification: that follows)."""
    with tempfile.TemporaryDirectory(prefix='veldo-principals') as directory:
        sig, allowed = Path(directory) / 'sig', Path(directory) / 'allowed_signers'
        sig.write_text(signature)
        allowed.write_text(signers)
        proc = subprocess.run(['ssh-keygen', '-Y', 'find-principals', '-s', str(sig), '-f', str(allowed)],
                              capture_output=True, text=True, timeout=10, stdin=subprocess.DEVNULL)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()] if proc.returncode == 0 else []


class Service:
    """One instance's judgment behind control_client.Authority, on the configured store connection."""

    def __init__(self, config, conn):
        self.config, self.conn = config, conn
        self.domain, self.store = config['domain_uuid'], config['store_uuid']
        self.repositories = dict(config['repositories'])
        self.principal, self.generation = config['principal'], config['authority_generation']
        self.enrollment_signers = Path(config['enrollment_signers']).read_text()
        self.receivers, self.counts, self.refusals = {}, {'accepted': 0, 'refused': 0}, {}

    def sign(self, data):
        return SIG.sign_bytes(self.config['journal_key'], data, L.JOURNAL_NAMESPACE)

    def watermark(self):
        return self.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

    # -- signatures --------------------------------------------------------------------------

    def verify(self, message, signature):
        """Every signature an Authority asks about, judged by the signed object's own schema: an
        enrollment binding under the installed enrollment signers, a request under the store's
        active keyring. Anything else does not verify."""
        if not isinstance(signature, str) or not signature.isascii() or not signature.strip():
            return False
        try:
            signed = json.loads(message)
        except ValueError:
            return False
        if not isinstance(signed, dict):
            return False
        if signed.get('schema') == E.BINDING_SCHEMA:
            principal = signed.get('enrolled_by')
            return (isinstance(principal, str) and bool(principal.strip()) and AC.ssh_keygen_verify(
                message, signature, self.enrollment_signers, principal, EL.ENROLLMENT_NAMESPACE)[0])
        if signed.get('schema') == CC.REQUEST_SCHEMA:
            return self._keyring_verifies(message, signature)
        return False

    def _keyring_verifies(self, message, signature):
        state, now = CM.authority_state(S, self.conn), time.time()
        lines = []
        for key in state['keyring']:
            principal = key.get('principal')
            if (isinstance(principal, str) and isinstance(key.get('public_key'), str)
                    and AC.active_member(AC.membership_entry(state['membership'], principal), now)[0]
                    and AC.active_key([key], principal, now) is key):
                lines.append(AC.allowed_signers_line(principal, key['public_key']))
        if not lines:
            return False
        signers = '\n'.join(lines) + '\n'
        return any(AC.ssh_keygen_verify(message, signature, signers, principal)[0]
                   for principal in find_principals(signature, signers))

    # -- the packets -------------------------------------------------------------------------

    def apply(self, packet, coordinates):
        repository = coordinates.get('repository_uuid')
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        observation = {'at': time.time(), 'domain_uuid': self.domain, 'repository_uuid': repository,
                       'workspace': coordinates.get('workspace'),
                       'operation': command.get('operation') or (packet.get('operation') if isinstance(packet, dict) else None),
                       'command_id': command.get('command_id'), 'unit_id': command.get('unit_id'),
                       'principal': command.get('principal'), 'accepted_versions': {}}
        try:
            if repository not in self.repositories:
                raise Refused('missing_authority:repository_not_served', 'this instance does not serve it')
            if isinstance(packet, dict) and packet.get('operation') == 'inspect' and 'command' not in packet:
                result = self.inspect(packet)
            elif command.get('operation') in CLM.OPERATIONS and 'unit_id' in command:
                receiver = self.receiver(repository)
                result = receiver.apply(packet)
                if receiver.observations:
                    observation['accepted_versions'] = receiver.observations[-1].get('accepted_versions', {})
            else:
                result = self.mutate(packet, command, repository)
                observation['accepted_versions'] = dict(command.get('expected_versions') or {})
        except Refused as error:
            result = {'ok': False, 'reason': error.code}
        except S.StoreRefused as error:
            result = {'ok': False, 'reason': error.code}
        except SIG.K.Refused:
            result = {'ok': False, 'reason': 'unavailable_service:signing'}
        except sqlite3.Error:
            result = {'ok': False, 'reason': 'unavailable_service:store'}
        except Exception as error:  # noqa: BLE001 - an unexpected fault is an unknown outcome, never success
            result = {'ok': False, 'reason': 'unknown_outcome:' + type(error).__name__}
        ok = bool(result.get('ok'))
        observation.update(outcome='accepted' if ok else 'refused', refusal=None if ok else result.get('reason'),
                           taxonomy=None if ok else taxonomy(result.get('reason')), watermark=self.watermark())
        self._count(observation)
        return result

    def receiver(self, repository):
        if repository not in self.receivers:
            self.receivers[repository] = CLM.Receiver(
                self.conn, {'domain_uuid': self.domain, 'store_uuid': self.store, 'repository_uuid': repository},
                self.principal, self.sign, self.generation)
        return self.receivers[repository]

    def mutate(self, packet, command, repository):
        signature = packet.get('signature') if isinstance(packet, dict) else None
        if not command or not isinstance(signature, str) or not signature.isascii():
            raise Refused('invalid_input:packet', 'a command mapping and its ASCII signature')
        expected = {'domain_uuid': self.domain, 'store_uuid': self.store, 'repository_uuid': repository}
        if any(command.get(k) != v for k, v in expected.items()):
            raise Refused('invalid_input:coordinates', 'the command names another domain, store or repository')
        if command.get('operation') not in MUTATIONS:
            raise Refused('invalid_input:operation', 'not one of the store\'s generic commands')
        principal, now = command.get('principal'), time.time()
        state = CM.authority_state(S, self.conn)
        member = AC.membership_entry(state['membership'], principal)
        active, why = AC.active_member(member, now)
        key = AC.active_key(state['keyring'], principal, now) if active else None
        if (not active or key is None or member.get('principal_type') not in AC.BOUNDARIES['command_acceptance']
                or not CM.scope_covers(member.get('scope'), repository)):
            raise Refused('not_authorized', why or 'membership, key or scope absent')
        verified, _detail = AC.ssh_keygen_verify(S.canonical_bytes(command), signature,
                                                 AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise Refused('not_authorized', 'the command signature is not the principal\'s')
        receipt = S.execute(self.conn, {k: command.get(k) for k in S.COMMAND_FIELDS}, self.principal, self.sign,
                            self.generation)
        return {'ok': True, 'reason': command['operation'], 'receipt': receipt}

    def inspect(self, packet):
        ids = packet.get('entity_ids') or []
        if not isinstance(ids, list) or len(ids) > 64 or not all(isinstance(i, str) for i in ids):
            raise Refused('invalid_input:entity_ids', 'at most 64 entity ids')
        head = self.conn.execute('SELECT seq, record_digest FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
        entities = {}
        for identity in ids:
            row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
            if row:
                entities[identity] = {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}
        return {'ok': True, 'reason': 'inspect', 'watermark': head[0] if head else 0,
                'journal_head': head[1] if head else S.GENESIS_DIGEST, 'entities': entities,
                'service': self.config['service'], 'unit': self.config['unit'],
                'counts': dict(self.counts, refusals=dict(self.refusals)), 'pending': self.pending()}

    def pending(self):
        claims = sum(1 for (data,) in self.conn.execute("SELECT data FROM entities WHERE kind='claim'")
                     if json.loads(data).get('state') not in (None, 'released'))
        effects = self.conn.execute("SELECT COUNT(*) FROM effects WHERE state='obligated'").fetchone()[0]
        return {'claims': claims, 'effects_obligated': effects}

    # -- observability -----------------------------------------------------------------------

    def observe_response(self, response):
        """A request the Authority refused before apply: observed here, with its named reason."""
        if isinstance(response, dict) and response.get('accepted') is False:
            self._count({'at': time.time(), 'domain_uuid': self.domain, 'operation': 'request', 'outcome': 'refused',
                         'refusal': response.get('reason'), 'taxonomy': taxonomy(response.get('reason')),
                         'watermark': self.watermark()})

    def _count(self, observation):
        self.counts[observation['outcome']] += 1
        if observation['outcome'] == 'refused':
            self.refusals[observation['refusal']] = self.refusals.get(observation['refusal'], 0) + 1
        fd = os.open(self.config['observations'], os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_CLOEXEC, 0o600)
        with os.fdopen(fd, 'a') as handle:
            handle.write(json.dumps(observation, sort_keys=True, default=str) + '\n')


def serve(config_path):
    """What the unit runs: the configuration, the lock, then the store and the socket, serving until
    SIGTERM. The lock comes first, so a second instance changes nothing."""
    config = load_config(config_path)
    lock = acquire(config['lock'], config)
    try:
        conn = S.open_store(config['store_path'])
        try:
            service = Service(config, conn)
            authority = CC.Authority(config['store_uuid'], config['domain_uuid'], config['store_path'], E,
                                     service.verify, config['host_identity'], service.apply,
                                     watermark=service.watermark,
                                     minimum_generation=config['authority_generation'], context=True)
            stopping = []
            signal.signal(signal.SIGTERM, lambda signum, frame: stopping.append(signum))
            signal.signal(signal.SIGINT, lambda signum, frame: stopping.append(signum))
            listener = CC.bind(config['socket'])
            inode = os.stat(config['socket']).st_ino
            listener.settimeout(0.25)
            notify('READY=1\nSTATUS=serving %s' % config['unit'])
            try:
                while not stopping:
                    try:
                        response = CC.serve_one(listener, authority)
                    except socket.timeout:
                        continue
                    except OSError:
                        if stopping:
                            break
                        raise
                    service.observe_response(response)
            finally:
                notify('STOPPING=1')
                listener.close()
                with contextlib.suppress(OSError):
                    if os.stat(config['socket']).st_ino == inode:
                        os.unlink(config['socket'])
        finally:
            conn.close()
    finally:
        os.close(lock)


# ---------------------------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------------------------

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv[:1] == ['serve']:
            if len(argv) != 2:
                raise Refused('invalid_input:usage', 'serve <installed service.json>')
            serve(argv[1])
            return 0
        import argparse
        parser = argparse.ArgumentParser(prog='control_service.py', description=__doc__.split('\n\n')[0])
        sub = parser.add_subparsers(dest='cmd', required=True)
        ins = sub.add_parser('install', help='lay down one authority instance (starts nothing)')
        ins.add_argument('--workspace', action='append', required=True)
        ins.add_argument('--host-trust')
        ins.add_argument('--key-directory')
        ins.add_argument('--install-root')
        ins.add_argument('--unit-dir')
        ins.add_argument('--profile', help='a JSON file with this host\'s worker profile')
        ins.add_argument('--adapters', help='a JSON file mapping adapter names to {argv: [...]}')
        for name in ('start', 'stop', 'status', 'uninstall'):
            one = sub.add_parser(name)
            one.add_argument('unit')
            if name == 'uninstall':
                one.add_argument('--install-root')
                one.add_argument('--unit-dir')
        args = parser.parse_args(argv)
        if args.cmd == 'install':
            report = install(args.workspace, host_trust=args.host_trust, key_directory=args.key_directory,
                             install_root=args.install_root, unit_dir=args.unit_dir,
                             profile=json.loads(Path(args.profile).read_text()) if args.profile else None,
                             adapters=json.loads(Path(args.adapters).read_text()) if args.adapters else None)
        elif args.cmd == 'uninstall':
            report = uninstall(args.unit, install_root=args.install_root, unit_dir=args.unit_dir)
        else:
            report = {'start': start, 'stop': stop, 'status': status}[args.cmd](args.unit)
        print(json.dumps(report, indent=1, sort_keys=True, default=str))
        return 0
    except Refused as error:
        sys.stderr.write(json.dumps({'refusal': error.code, 'taxonomy': taxonomy(error.code),
                                     'detail': error.detail, 'guidance': error.guidance}) + '\n')
        return EXIT_LOCK_HELD if error.code == 'authority_lock_held' else EXIT_REFUSED


if __name__ == '__main__':
    sys.exit(main())
