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

  bin/     the FIXED EXECUTABLE: the entry points (this module, the launch receiver and the key
           custody wrapper), the architecture validator the receiver's recheck runs, and every module
           these load, derived from the engine at installation (closure()), never listed by hand,
           copied byte for byte and read-only (0400, the three entry points 0500, the
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

THE TELEGRAM CHANNEL (VELDO-0138). An installation given --channel-ingress copies that VELDO-0073
host configuration (veldo.telegram_ingress/v1, this account's own 0600 file naming THIS authority's
store, identities, generation, a served repository and the service's own journal principal and key;
anything else refuses installation by name) into config/channel-ingress.json. `serve` then opens the
Telegram ingress from it with control_channel_ingress.open_ingress and owns its lifetime
(control_service_channel). The ingress is inert until the owner activates it: every pass asks the
activation gate first, and a refused pass sends, acquires and writes nothing. Every POLL_SECONDS the
loop runs one pass (acquire, settle, present pending requests); a channel_activation_authorize packet
is applied by the ingress's own Activations organ, which admits only the owner's own signed command;
inspect reports the channel's status. A stop takes effect at the next exchange, and a restart keeps
the edge as the owner left it, because the record in the store decides every exchange. An ingress
that cannot be constructed leaves the service serving everything else, its refusal reported by name.

THE AUTHENTICATED API (VELDO-0130). An installation given an API service configuration as well
copies that veldo.api_service/v1 configuration (this authority's own, and the api edge its Telegram
ingress names; anything else refuses installation by name) into config/api-service.json, and `serve`
constructs the API's judge on the ingress's connection with the lock this instance holds
(control_service_api), so the authority, never the API process, runs every API command and read. An api_call packet, whose request
signature must be the enrolled api edge's in the API's request namespace (never a member key), is run by
it; a steward's enroll_api_credential or revoke_api_credential packet is admitted by
control_api_credentials; inspect reports the API's status. After every packet or channel pass that
advanced the journal, whoever sent it, the service sends the head record's hint to each subscribed API,
so a revocation committed here ends the API's sessions and closes their open streams. An API that cannot
be constructed leaves the service serving everything else, its refusal reported by name.

KEY DIRECTORY. The custody wrapper (VELDO-0067) denies a confined worker every file created directly
in an ancestor of a protected directory after the worker starts, so the key directory belongs where
workers never write directly: outside the home and temporary directories. It is judged as named: a
relative one is refused as relative, and where it is comes before whether it exists, so one inside a
worker directory is refused as that even when absent. On a host where this account can create nothing
else, placing it takes one root step, and installation refuses naming that step exactly
(missing_authority:key_directory:absent): it creates only the directories missing below the first
existing ancestor, and no printed step changes the mode or owner of a directory that exists. The
default is /var/lib/veldo/keys/<service id>.

WHAT IT IS NOT. No automatic restart or recovery (Release 2), no second host profile, remote
inspection or legacy status listener (Release 4), no network listener. Standard library only.
"""
import ast
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
import shlex
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
CH = _organ('control_service_channel')
CHANNEL_INGRESS = 'channel-ingress.json'
SA = _organ('control_service_api')
API_SERVICE = 'api-service.json'

# The store's own generic commands, taken before any service registers one of its own on this module
# (control_claim.Receiver adds claim_operation), so a claim transition is never reachable as one.
MUTATIONS = tuple(sorted(S.COMMAND_REGISTRY))

# The programs an installation runs by path: the service (the unit's ExecStart), the launch receiver
# with its trusted wrapper, and the key custody wrapper. The rest of the fixed executable is derived
# from what these and the architecture validator load (closure()), never listed by hand.
ENTRY_POINTS = ('control_service.py', 'control_launch.py', 'control_keys_custody.py')
# The one way an engine module loads a sibling: importlib.util.spec_from_file_location.
LOADER = 'spec_from_file_location'

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
# The fixed executable: derived at installation from what its programs load
# ---------------------------------------------------------------------------------------------

def _callee(call):
    function = call.func
    return function.id if isinstance(function, ast.Name) else function.attr if isinstance(function, ast.Attribute) else None


def _constants(node):
    """The '.py' file names an expression's string constants name (a path's last part)."""
    found = set()
    for part in ast.walk(node):
        if isinstance(part, ast.Constant) and isinstance(part.value, str):
            base = os.path.basename(part.value)
            if base.endswith('.py') and base != '.py' and not any(c.isspace() for c in part.value):
                found.add(base)
    return found


class _Loads:
    """One engine module, read for the siblings it loads. A load is a LOADER call, whose location names
    the file, or a call of a LOADER HELPER: a function whose LOADER call builds its location from one of
    its parameters (control_*'s organ(name), validate_checks' _organ(name, path)), called directly or
    bound with functools.partial, whose argument for that parameter names the file (a helper that
    appends '.py' takes the module's name). An import naming a sibling is a load too. A file is named
    by a string constant in the expression, or by a variable EVERY binding of which, anywhere in the
    module, is a plain assignment naming a file; a variable bound to a file in one place and to anything
    else in another names nothing for certain. A load site whose file this reading cannot name for
    certain, or a loader helper used other than by a call, is kept as unresolved."""

    def __init__(self, path):
        self.name = path.name
        self.tree = ast.parse(path.read_bytes(), str(path))
        parents = {child: parent for parent in ast.walk(self.tree) for child in ast.iter_child_nodes(parent)}
        # Every binding of every name: the files a plain assignment's value names, or none for any other
        # binding (a parameter, a loop or with target, an unpacking, an import, an exception name).
        plain = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                plain[id(node.targets[0])] = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
                plain[id(node.target)] = node.value
        bindings = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                value = plain.get(id(node))
                bindings.setdefault(node.id, []).append(_constants(value) if value is not None else set())
            elif isinstance(node, ast.arg):
                bindings.setdefault(node.arg, []).append(set())
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    bindings.setdefault((alias.asname or alias.name).partition('.')[0], []).append(set())
            elif isinstance(node, ast.ExceptHandler) and node.name:
                bindings.setdefault(node.name, []).append(set())
        self.bound = {name: set().union(*found) for name, found in bindings.items() if all(found)}
        self.mixed = {name for name, found in bindings.items() if any(found) and not all(found)}
        self.helpers, self.loads, self.unresolved, self.calls = {}, set(), [], []
        for call in (node for node in ast.walk(self.tree) if isinstance(node, ast.Call)):
            if _callee(call) != LOADER:
                self.calls.append(call)
                continue
            where = call.args[1] if len(call.args) > 1 else next(
                (k.value for k in call.keywords if k.arg == 'location'), None)
            scope = call
            while scope in parents and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scope = parents[scope]
            params = []
            if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = [a.arg for a in scope.args.posonlyargs + scope.args.args + scope.args.kwonlyargs]
            used = [p for p in params if where is not None
                    and any(isinstance(n, ast.Name) and n.id == p for n in ast.walk(where))]
            if used:
                self.helpers[scope.name] = {'params': params[1:] if params[:1] == ['self'] else params, 'used': used,
                                            'suffix': any(isinstance(n, ast.Constant) and n.value == '.py'
                                                          for n in ast.walk(where))}
                continue
            named = self.names(where) if where is not None else None
            if not named:
                self.unresolved.append('%s:%d' % (self.name, call.lineno))
            self.loads |= named or set()
        # A function that calls one of this module's loader helpers with an argument built from its own
        # parameter is a loader helper too (control_workflow's _organ(name) calls _sibling(alias,
        # name + '.py')); its call there names no file itself, so it is delegated, never unresolved.
        self.delegated = set()
        while True:
            found = False
            for call in self.calls:
                if id(call) in self.delegated or not isinstance(call.func, ast.Name) or call.func.id not in self.helpers:
                    continue
                scope = call
                while scope in parents and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    scope = parents[scope]
                if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)) or scope.name in self.helpers:
                    continue
                params = [a.arg for a in scope.args.posonlyargs + scope.args.args + scope.args.kwonlyargs]
                helper = self.helpers[call.func.id]
                given = dict(zip(helper['params'], call.args))
                given.update({k.arg: k.value for k in call.keywords if k.arg})
                values = [given[p] for p in helper['used'] if p in given]
                used = [p for p in params if any(isinstance(n, ast.Name) and n.id == p for v in values for n in ast.walk(v))]
                if not used:
                    continue
                self.helpers[scope.name] = {'params': params[1:] if params[:1] == ['self'] else params, 'used': used,
                                            'suffix': helper['suffix'] or any(isinstance(n, ast.Constant) and n.value == '.py'
                                                                              for v in values for n in ast.walk(v))}
                self.delegated.add(id(call))
                found = True
            if not found:
                break
        self.imports = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                self.imports |= {alias.name.partition('.')[0] + '.py' for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                self.imports.add(node.module.partition('.')[0] + '.py')

    def names(self, node):
        """The files `node` names for certain, or None when it uses a name bound to a file in one place
        and to something else in another."""
        found = _constants(node)
        for part in ast.walk(node):
            if isinstance(part, ast.Name):
                if part.id in self.mixed:
                    return None
                found |= self.bound.get(part.id, set())
        return found

    def resolve(self, helpers):
        """(files this module loads, unresolved load sites). A helper called by bare name is this
        module's own, or another module's it assigned to that name (fix_validation_record's
        `_load = _runner()._load`); one called as an attribute (E.organ) is any module's helper of that
        name."""
        named, unresolved, accounted = set(self.loads), list(self.unresolved), set()
        aliases = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                value = node.value
                held = value.attr if isinstance(value, ast.Attribute) else value.id if isinstance(value, ast.Name) else None
                if held in self.helpers or held in helpers:
                    aliases[node.targets[0].id] = held
                    accounted.add(id(value))

        def candidates(target):
            if isinstance(target, ast.Name):
                if target.id in self.helpers:
                    return [self.helpers[target.id]]
                held = aliases.get(target.id)
                return [self.helpers[held]] if held in self.helpers else helpers.get(held, [])
            if isinstance(target, ast.Attribute):
                return helpers.get(target.attr, [])
            return []

        for call in self.calls:
            if id(call) in self.delegated:
                accounted.add(id(call.func))
                continue
            target, args = call.func, list(call.args)
            if _callee(call) == 'partial' and args:
                target, args = args[0], args[1:]
            options = candidates(target)
            if not options:
                continue
            accounted.add(id(target))
            found, certain = set(), True
            for helper in options:
                given = dict(zip(helper['params'], args))
                given.update({k.arg: k.value for k in call.keywords if k.arg})
                for param in helper['used']:
                    value = given.get(param)
                    if value is None:
                        continue
                    files = self.names(value)
                    if files is None:
                        certain = False
                        continue
                    if not files and helper['suffix'] and isinstance(value, ast.Constant) and isinstance(value.value, str):
                        files = {value.value + '.py'}
                    found |= files
            if not found or not certain:
                unresolved.append('%s:%d' % (self.name, call.lineno))
            named |= found
        # A loader helper handed on as a value (to map, a table, a callback) loads what no call here names.
        for node in ast.walk(self.tree):
            handed = ((isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                       and (node.id in self.helpers or node.id in aliases))
                      or (isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and node.attr in helpers))
            if handed and id(node) not in accounted:
                unresolved.append('%s:%d' % (self.name, node.lineno))
        return named, unresolved


def closure():
    """The fixed executable's modules, derived from the engine directory an installation copies from
    (install() runs there, so the derivation reads the engine, never the installed copy). The seeds are
    ENTRY_POINTS and the architecture validator's declared files: the launch receiver's recheck builds
    a control_eligibility.Gate, whose ValidatorSnapshot loads the validator from ITS OWN directory by
    module name rather than through a load any source spells, so the validator's files are taken from
    the declaration of the module that loads them, control_eligibility.VALIDATOR_ROLES. (The
    scaffold's REQUIRED_SUBSTRATE declares a repository's gate, not what the snapshot loads, and
    init_scaffold.py is not laid down in an adopter's tree, where this installer runs too.) Then every
    module a member loads (_Loads), followed to a fixed point. A load naming a module this directory
    lacks, or a load site whose module no literal names, refuses installation by name, so an
    installed program is never short of a module it loads and never finds that out when it runs.
    Returns the sorted file names."""
    present = {path.name for path in HERE.glob('*.py')}
    seeds = set(ENTRY_POINTS) | {name for _role, name in EL.VALIDATOR_ROLES}
    readings = {}
    while True:
        # A pass reads with every helper the modules read so far define; a helper first read in this
        # pass can name more loads, so passes repeat until one reads no new module.
        helpers = {}
        for reading in readings.values():
            for name, helper in reading.helpers.items():
                helpers.setdefault(name, []).append(helper)
        known = len(readings)
        members, loaded_by, absent, unresolved = set(), {}, [], []
        todo = sorted(seeds, reverse=True)
        while todo:
            name = todo.pop()
            if name in members:
                continue
            if name not in present:
                absent.append('%s (loaded by %s)' % (name, loaded_by.get(name, 'the declared set')))
                continue
            members.add(name)
            if name not in readings:
                try:
                    readings[name] = _Loads(HERE / name)
                except (OSError, SyntaxError, ValueError) as error:
                    raise Refused('invalid_input:closure:unreadable', '%s: %s' % (name, type(error).__name__))
            named, sites = readings[name].resolve(helpers)
            unresolved += sites
            for dependency in sorted(named | (readings[name].imports & present), reverse=True):
                if dependency not in members:
                    loaded_by.setdefault(dependency, name)
                    todo.append(dependency)
        if len(readings) > known:
            continue
        if absent:
            raise Refused('invalid_input:closure:absent', '%s holds no %s' % (HERE, ', '.join(sorted(set(absent)))),
                          'install from a complete engine: python3 .veldo/init_scaffold.py <repository> lays down '
                          'every module it loads')
        if unresolved:
            raise Refused('invalid_input:closure:unresolved', 'no literal names the module loaded at %s'
                          % ', '.join(sorted(set(unresolved))), 'load the module there by a literal file name')
        return sorted(members)


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
    """Why `path` may not hold the protected keys, as named codes, first the one to act on; [] when it
    may. It must be absolute, as given, before anything resolves it; then its LOCATION is judged
    before whether it exists (neither inside nor above any directory in `writable`, where no one-time
    step could make it safe); then it must exist as a real directory of this account that nobody else
    can enter."""
    text = str(path)
    if not os.path.isabs(text):
        return ['invalid_input:key_directory:relative']
    problems = []
    real = os.path.realpath(text)
    if any(_within(real, os.path.realpath(root)) or _within(os.path.realpath(root), real) for root in writable):
        problems.append('invalid_input:key_directory:worker_writable')
    try:
        info = os.lstat(text)
    except FileNotFoundError:
        return problems + ['missing_authority:key_directory:absent']
    except OSError:
        return problems + ['unavailable_service:key_directory:unreadable']
    if stat.S_ISLNK(info.st_mode):
        return problems + ['invalid_input:key_directory:symlink']
    if not stat.S_ISDIR(info.st_mode):
        return problems + ['invalid_input:key_directory:not_a_directory']
    if info.st_uid != os.getuid():
        problems.append('invalid_input:key_directory:owner')
    if stat.S_IMODE(info.st_mode) & 0o077:
        problems.append('invalid_input:key_directory:mode')
    return problems


def _missing_below(path):
    """The directories `path` names that do not exist, outermost first: everything below its first
    existing ancestor, and nothing at or above it."""
    missing, current = [], os.path.normpath(str(path))
    while not os.path.lexists(current):
        missing.append(current)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return list(reversed(missing))


def key_directory_guidance(path, code):
    """What the operator does about `code`. Only a missing key directory is given commands, and they
    create exactly the directories below its first existing ancestor, each named only while it is
    missing: no printed command changes the mode or owner of a directory that exists."""
    user = pwd.getpwuid(os.getuid()).pw_name
    group = grp.getgrgid(os.getgid()).gr_name
    elsewhere = ('choose a new directory outside the home and temporary directories, for example %s/<service id>; '
                 'installation then prints the one-time root step that creates it, owned by %s'
                 % (DEFAULT_KEY_ROOT, user))
    if code.endswith(':absent'):
        missing = _missing_below(path)
        if not missing:
            return elsewhere
        steps = ['sudo install -d -m 0755 %s' % shlex.quote(d) for d in missing[:-1]]
        steps.append('sudo install -d -m 0700 -o %s -g %s %s' % (shlex.quote(user), shlex.quote(group),
                                                                 shlex.quote(missing[-1])))
        return ('create it once as root, owned by %s and closed to everyone else, making only the directories '
                'that are missing: %s' % (user, ' && '.join(steps)))
    if code.endswith(':mode'):
        return 'it is open to others; a key directory is one of its own, so ' + elsewhere
    if code.endswith(':owner'):
        return 'it does not belong to %s; a key directory is one of its own, so %s' % (user, elsewhere)
    if code.endswith(':relative'):
        return 'name it by its absolute path: ' + elsewhere
    return elsewhere


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
            receiver_principal='launch-receiver', runner=None, python=None, channel_ingress=None, api_service=None):
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
    # Judged as NAMED, never resolved first: a relative directory is refused as relative (it names a
    # different directory from every working directory), and a link to a safe directory is refused as a
    # link, because what it points at can change after this check.
    keys = str(key_directory) if key_directory else os.path.join(DEFAULT_KEY_ROOT, service)
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
    ingress = None
    if channel_ingress is not None:
        try:
            ingress = CH.installable(str(channel_ingress), first, principal, journal, repositories)
        except CH.Refused as error:
            raise Refused(error.code, error.detail, 'name the VELDO-0073 ingress configuration of this authority')
    api = None
    if api_service is not None:
        try:
            api = SA.installable(str(api_service), first, principal, journal, repositories,
                                 str(channel_ingress) if ingress is not None else None)
        except SA.Refused as error:
            raise Refused(error.code, error.detail, 'name the VELDO-0130 API service configuration of this authority')
    bin_dir, config_dir, state_dir = (os.path.join(home, n) for n in ('bin', 'config', 'state'))
    config_path = os.path.join(config_dir, 'service.json')
    values = {'SERVICE': service, 'DOMAIN': first['domain_uuid'], 'STORE': first['store_uuid'],
              'PYTHON': python, 'EXECUTABLE': os.path.join(bin_dir, 'control_service.py'), 'CONFIG': config_path}
    text = unit_text(values)
    fixed = {name: (HERE / name).read_bytes() for name in closure()}

    created, generated = [], False
    try:
        os.makedirs(os.path.dirname(first['store_path']), mode=0o700, exist_ok=True)
        os.makedirs(root, exist_ok=True)
        os.mkdir(home, 0o700)
        created.append(home)
        for directory in (bin_dir, config_dir, state_dir):
            os.mkdir(directory, 0o700)
        for name, data in fixed.items():
            _write(os.path.join(bin_dir, name), data, 0o500 if name in ENTRY_POINTS else 0o400)
        os.chmod(bin_dir, 0o500)
        if not os.path.lexists(journal):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'veldo-authority-' + service,
                            '-f', journal], check=True, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            generated = True
            os.chmod(journal, 0o600)
        _write(os.path.join(config_dir, 'enrollment_signers'), signers, 0o600)
        if ingress is not None:
            _write(os.path.join(config_dir, CHANNEL_INGRESS), ingress, 0o600)
        if api is not None:
            _write(os.path.join(config_dir, API_SERVICE), api, 0o600)
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
                  'closure': {name: _digest(data) for name, data in fixed.items()},
                  'template': _digest(TEMPLATE.read_bytes()),
                  'channel_ingress': os.path.join(config_dir, CHANNEL_INGRESS) if ingress is not None else None,
                  'api_service': os.path.join(config_dir, API_SERVICE) if api is not None else None}
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
            'executable': values['EXECUTABLE'], 'closure': sorted(fixed), 'receiver': config['receiver'], 'key_directory': keys,
            'journal_key': journal, 'journal_key_generated': generated, 'profile': qualification,
            'socket': config['socket'], 'lock': config['lock'], 'repositories': repositories,
            'channel_ingress': config['channel_ingress'], 'api_service': config['api_service'],
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
        # The Telegram channel (VELDO-0138): set by serve() when the installation names an ingress.
        self.channel, self.channel_refusal = None, None
        # The authenticated API (VELDO-0130): set by serve() when the installation names its configuration.
        self.api, self.api_refusal = None, None
        # The counts are the observation log's, so they cover every instance that served this
        # installation, not only this process.
        with contextlib.suppress(OSError):
            for line in Path(config['observations']).read_text().splitlines():
                with contextlib.suppress(ValueError, KeyError, TypeError):
                    self._tally(json.loads(line))

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
            # An API call speaks only for the API: its request is the api edge's, in its own namespace.
            if SA.AS.is_call(signed.get('command')):
                return self.api is not None and self.api.verifies(message, signature)
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
        if SA.AS.is_call(packet):
            observation.update(operation=SA.AS.CALL, call=packet.get('call'))
        before = self.watermark()
        try:
            if repository not in self.repositories:
                raise Refused('missing_authority:repository_not_served', 'this instance does not serve it')
            if isinstance(packet, dict) and packet.get('operation') == 'inspect' and 'command' not in packet:
                result = self.inspect(packet)
            elif SA.AS.is_call(packet):
                result = self.api_call(packet)
            elif command.get('operation') in SA.CR.OPERATIONS and 'envelope' in packet:
                result = self.api_credential(packet, observation)
            elif command.get('operation') == CH.AUTHORIZE:
                result = self.channel_command(packet, repository, observation)
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
        self.hint_after(before)
        return result

    def api_call(self, packet):
        """One API call (VELDO-0130), run by this instance's API judge; refused by name without one."""
        if self.api is None:
            raise Refused('unavailable_service:api:' + (self.api_refusal or 'not_configured'),
                          'this instance runs no authenticated API')
        return self.api.call(packet)

    def api_credential(self, packet, observation):
        """A steward's enroll_api_credential or revoke_api_credential, signed at the host."""
        if self.api is None:
            raise Refused('unavailable_service:api:' + (self.api_refusal or 'not_configured'),
                          'this instance runs no authenticated API')
        result = self.api.credential(packet)
        observation['accepted_versions'] = dict(result.pop('accepted_versions', None) or {})
        return result

    def hint_after(self, before):
        """After a packet or pass that advanced the journal, the head record's hint to every subscribed
        API; a failure is logged by name and never ends the service."""
        if self.api is None or self.watermark() <= before:
            return None
        try:
            sent = self.api.publish()
        except Exception as error:  # noqa: BLE001 - an unexpected fault is an unknown outcome, never success
            sent = {'outcome': 'refused', 'reason': 'unknown_outcome:' + type(error).__name__}
        if sent.get('dropped') or sent.get('reason'):
            self._log(dict(sent, kind='api', operation='api_hint', at=time.time(), domain_uuid=self.domain))
        return sent

    def api_status(self):
        if self.api is None:
            return {'available': False, 'configured': bool(self.config.get('api_service')),
                    'refusal': self.api_refusal}
        return dict(self.api.status(), configured=True)

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

    def channel_status(self):
        if self.channel is None:
            return {'available': False, 'configured': bool(self.config.get('channel_ingress')),
                    'refusal': self.channel_refusal}
        return dict(self.channel.status(), configured=True)

    def channel_command(self, packet, repository, observation):
        """The owner's channel_activation_authorize command, applied by the ingress's own Activations
        organ (VELDO-0073), which admits only the owner's own signed envelope. Refused by name, with
        nothing written, when this instance runs no channel or the command is for another repository."""
        if self.channel is None:
            raise Refused('unavailable_service:channel:' + (self.channel_refusal or 'not_configured'),
                          'this instance runs no Telegram channel')
        if repository != self.channel.ingress.activations.ids.get('repository_uuid'):
            raise Refused('invalid_input:channel:repository', 'the channel belongs to another repository')
        outcome = self.channel.authorize(packet)
        observation['accepted_versions'] = dict(outcome.get('accepted_versions') or {})
        if outcome.get('outcome') != 'accepted':
            code = outcome.get('reason') or 'unknown_outcome'
            return {'ok': False, 'reason': '%s:channel:%s' % (CH.ACT.REFUSALS.get(code, 'unknown_outcome'), code)}
        record = self.channel.record() or {}
        return {'ok': True, 'reason': CH.AUTHORIZE, 'action': outcome.get('action'), 'state': record.get('state'),
                'entity_version': record.get('entity_version')}

    def channel_pass(self):
        """One channel pass (control_service_channel.Channel.tick), logged when it did something or its
        outcome changed. A fault is an unknown outcome in the log, never the end of the service."""
        before = self.watermark()
        try:
            summary = self.channel.tick()
        except Exception as error:  # noqa: BLE001 - an unexpected fault is an unknown outcome, never success
            summary = {'outcome': 'refused', 'reason': 'unknown_outcome:' + type(error).__name__, 'notable': True}
        if summary.pop('notable', False):
            self._log(dict(summary, kind='channel', operation='channel_pass', at=time.time(), domain_uuid=self.domain))
        self.hint_after(before)
        return summary

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
                'counts': dict(self.counts, refusals=dict(self.refusals)), 'pending': self.pending(),
                'channel': self.channel_status(), 'api': self.api_status()}

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

    def _tally(self, observation):
        if observation.get('kind') in ('channel', 'api'):
            return
        self.counts[observation['outcome']] += 1
        if observation['outcome'] == 'refused':
            self.refusals[observation['refusal']] = self.refusals.get(observation['refusal'], 0) + 1

    def _count(self, observation):
        self._tally(observation)
        self._log(observation)

    def _log(self, observation):
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
            service.channel, service.channel_refusal = CH.open_channel(config.get('channel_ingress'))
            service.api, service.api_refusal = SA.open_api(config.get('api_service'), service.channel, lock,
                                                           os.path.dirname(config['observations']))
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
            next_pass = time.monotonic()
            try:
                while not stopping:
                    try:
                        response = CC.serve_one(listener, authority)
                    except socket.timeout:
                        response = None
                    except OSError:
                        if stopping:
                            break
                        raise
                    if response is not None:
                        service.observe_response(response)
                    if service.channel is not None and not stopping and time.monotonic() >= next_pass:
                        service.channel_pass()
                        next_pass = time.monotonic() + CH.POLL_SECONDS
            finally:
                notify('STOPPING=1')
                listener.close()
                with contextlib.suppress(OSError):
                    if os.stat(config['socket']).st_ino == inode:
                        os.unlink(config['socket'])
                if service.channel is not None:
                    with contextlib.suppress(Exception):
                        service.channel.close()
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
        ins.add_argument('--channel-ingress', help='the VELDO-0073 Telegram ingress configuration this instance runs')
        ins.add_argument('--api-service', help='the VELDO-0130 API service configuration this instance runs')
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
                             adapters=json.loads(Path(args.adapters).read_text()) if args.adapters else None,
                             channel_ingress=args.channel_ingress, api_service=args.api_service)
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
