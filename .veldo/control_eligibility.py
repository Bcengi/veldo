"""Shared floor eligibility for every enabled station entry (PLAN-0019 W37, VELDO-0052, R52, R70).

WHAT THIS MODULE IS. The one eligibility service the floor's entries call: frontier selection, the
work loop's claim, plan run-check and the direct executor's build and review launches, the
dispatcher's build, review and publication, and every subscription CLI call a build or review makes. Each asks the same Gate for a
named decision over the accepted records in the real control store, with the predicates of ITS
station (completion_contract.ENTRY_PREDICATES, the shipped VELDO-0021 contract, plus current
admission everywhere under R52/R69, and priority everywhere under VELDO-0078: priority_current is the
backlog's executable question, control_backlog_priority.executable_record_problems, over the unit and
backlog records the decision consumed, so admitted but unprioritized work, a unit appended after the last
prioritization and a blocked item are refused at every station by one decision). Review cannot bypass
draft-plan, decision or dependency checks.

WHAT A DECISION CARRIES. The station, the unit, the store watermark, and the version and digest of
every input it consumed: the unit and its backlog item, governing plan, admission, project,
authority, claim, each dependency with its complete receipt collection, and the whole decision,
blocker and approval collections (a negative predicate reads a collection, never one record). A
later station passes the earlier decision back as its ticket and the Gate refuses by name
(stale_input:<label>) when any consumed input moved, while the project version stays fixed. Only
the claim's own lifecycle writes (claim record, unit and backlog state) are station OUTPUTS: they
are compared by their definition digest and claim ownership is re-decided fresh.

PROJECT LIFECYCLE (VELDO-0076). A unit's project is judged only from a record of kind project at
project:<name>; a record of any other kind at that id refuses project_not_active:not_a_project (the
project service also owns the project: id prefix, so no other command writes one). Every station
refuses a unit whose project record carries a lifecycle state other than ACTIVE
(project_not_active:<state>), so a paused or canceled project's units are neither offered, claimed,
prepared, launched nor published, and a ticket issued before the pause is also stale (its project
input moved). An ACTIVE project whose recorded owner is not a current person member holding
project_owner in a scope covering the project refuses project_not_active:owner_not_current: only
that owner may pause or cancel it, so while he cannot, its work halts at its next station until he is
current again (the fail-safe of VELDO-0138's demoted owner; handover to a new owner is Release 3).
The owner's membership record is a consumed input (project_owner).

COMPLETION. completion() is the one reader of the four facts (attempt finished, artifact accepted,
revision landed, objective satisfied) over stored completion receipts, judged by
completion_contract.fact_problems for the exact subject revision. Landed additionally needs the exact
landing receipt (completion_contract.landing_receipt_problems). A passing verdict, a proof manifest
or shipped status text never lands anything. completion_status() hands that answer to the status
maps the frontier and plan readers already consume.

ENABLEMENT. gate_for() is the one resolution every library entry calls. An explicit Gate is used. A
repository enrolled with the authority (VELDO-0029 binding) and no Gate wired STOPS with
eligibility_required, exactly as claim.py stops with authority_required: an enabled floor entry
cannot run without eligibility. An unenrolled tree keeps the pre-factory behavior unchanged.

PRODUCTION CONSTRUCTION. entry_gate() is what every command-line entry calls (bin/veldo work and
fleet, veldo_run, the executor, frontier, plan and status commands): in an enrolled repository it
BUILDS the Gate from the workspace's own signed binding (domain, repository, store and authority
generation), after verifying that binding against what this HOST trusts (HostTrust: its identity and
the allowed signers of enrollment). A binding that does not verify, a host that trusts nothing, or a
store that cannot be read is a named stop, never a Gate over coordinates nobody vouched for.

THE DISPATCH LIFECYCLE. StationCalls.launch() is the one scope a station's launch runs in: it opens
the dispatch (reserving its worker slot) only when the caller has passed every pre-launch decision
and is about to launch, and closes it the moment the launched call returns, however it returns. The
close retains every call's exposure (a call with no final usage report is settled as UNKNOWN, its
reserved charge and unknown units kept) and then retires the worker slot, so capacity is spent while
a launch runs and returned when it ends. Until VELDO-0040/0041's supervisor exists, the runner's own
observation that the launching call returned in this process is the lifecycle observation; the
supervisor owns retirement once it exists.

WHAT IT IS NOT. The Gate writes nothing: it reads inside one deferred read transaction. The only
writes on this path are the runner's own reservation commands (StationCalls.open_dispatch reserves a
dispatch's worker slot, each launch its call, and close_dispatch settles unreported calls as unknown
and retires the slot, through VELDO-0036's reservation service, which commits through control_store).
It holds no key, launches nothing itself (StationCalls hands launches to VELDO-0036's InvocationGuard,
which reserves before launch), and implements no recovery, fencing or clock qualification (Release 2). VELDO-0054's exact decision
consumption attaches to the same registrations. Standard library only.

ARCHITECTURE AT EVERY ENTRY (VELDO-0053, R50). Every station asks architecture_accepted. The answer
comes from the structural validator INSTALLED beside this module (never the copy a workspace carries),
executed once per Gate from one in-memory read of its bytes (ValidatorSnapshot) and asked through validate.py's
public entry_contract, over the workspace's .veldo/architecture.yaml. A Gate with no workspace always
refuses (missing_evidence:architecture/workspace). The authority's record
architecture:<repository>, when it is a valid veldo.architecture_record/v1 (VELDO-0134's schema, read
through control_architecture.record_problems; any other shape refuses missing_authority:architecture),
makes the contract required whatever the workspace's policy says, and the workspace file must be exactly those bytes; with no
record the repository's policy flag decides absence, as VELDO-0016's loader always has. A present
contract that is unreadable, malformed, of the wrong type or structurally invalid refuses by name
(invalid_input:architecture/<kind>), a required one that is absent refuses
(missing_evidence:architecture/required_absence), and bytes the authority did not accept refuse
(missing_authority:architecture/unaccepted_artifact), compared by the digest of the very bytes the
loader parsed. Each decision records the artifact it judged and the snapshot of the code that judged it
(every module it executed, keyed by module name, with its role label, installed path and the digest of
the bytes loaded).
"""
import builtins
import collections
import contextlib
import hashlib
import importlib.util
import json
import linecache
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import time
import uuid

SCHEMA = 'veldo.control_eligibility/v1'


def _organ(name):
    spec = importlib.util.spec_from_file_location('eligibility_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CC = _organ('completion_contract')
E = _organ('control_enrollment')
# VELDO-0076: the membership reading (scope_covers, authority_contract.active_member) a project's owner is judged by.
CM = _organ('control_membership')
SN = _organ('control_snapshot')
# VELDO-0054: exact decision-record dependency evaluation, the decisions_settled predicate's answer.
DD = _organ('control_decision_dependency')
# VELDO-0134: the architecture record's schema (veldo.architecture_record/v1), which the reader applies.
AR = _organ('control_architecture')
# VELDO-0078: the backlog's executable question, the priority_current predicate's answer, from its
# import-free module: the backlog service itself loads the entity contract and with it the engine's
# parser, which this process runs only inside the architecture snapshot.
BL = _organ('control_backlog_priority')

# The stations the floor's entries invoke, each with its station-specific predicates. The shipped
# contract's set is the floor of each; current admission is added to every station because R52
# excludes unadmitted work from autonomous dispatch and R69 invalidates admission on scope change.
FLOOR_STATIONS = ('selection', 'claim', 'direct_execution', 'build', 'review', 'publication', 'provider_request')
# VELDO-0053: required architecture is asked at every station too, before the station's own questions.
ARCHITECTURE_PREDICATE = 'architecture_accepted'
STATION_PREDICATES = {s: tuple(dict.fromkeys(('admission_current', ARCHITECTURE_PREDICATE) + tuple(CC.ENTRY_PREDICATES[s])))
                      for s in FLOOR_STATIONS}
# The refusal each refused architecture kind is named by (contract_loader.CONTRACT_KINDS, plus the
# accepted-digest check this module adds).
ARCHITECTURE_REFUSALS = {
    'required_absence': 'missing_evidence:architecture/required_absence',
    'unreadable': 'invalid_input:architecture/unreadable',
    'parse_failure': 'invalid_input:architecture/parse_failure',
    'invalid_structure': 'invalid_input:architecture/invalid_structure',
    'unaccepted_artifact': 'missing_authority:architecture/unaccepted_artifact',
}
# Predicates satisfied only by a store transaction at the call boundary, never by a read.
TRANSACTIONAL = {'charge_reserved': 'control_reservations.Reservations.reserve_call'}
# VELDO-0078: only admitted, PRIORITIZED work is eligible, at every station right after its admission: an
# admission record is written when the owner admits the item, before its priority, so admission alone
# never makes a unit eligible anywhere.
PRIORITY_PREDICATE = 'priority_current'
STATION_PREDICATES = {s: tuple(dict.fromkeys(('admission_current', PRIORITY_PREDICATE) + p))
                      for s, p in STATION_PREDICATES.items()}

# EVERY ENABLED FLOOR ENTRY, as (module, qualified function, station). The suite derives the same
# set from the actual call sites (a .decide/.require call naming a station) and requires equality.
REGISTRATIONS = (
    ('frontier.py', 'claimable._add', 'selection'),
    ('work.py', 'WorkLoop._claim_next', 'claim'),
    ('plan.py', 'cmd_run_check', 'direct_execution'),
    ('executor.py', 'Executor._decide', 'direct_execution'),
    ('executor.py', 'Executor._decide', 'build'),
    ('executor.py', 'Executor._decide', 'review'),
    ('executor.py', 'Executor._decide_calls', 'provider_request'),
    ('dispatch.py', 'Dispatcher._dispatch_build', 'build'),
    ('dispatch.py', 'Dispatcher._dispatch_review', 'review'),
    ('dispatch.py', 'Dispatcher._land', 'publication'),
    ('control_eligibility.py', 'CallHandle.invoke', 'provider_request'),
)
# EVERY COMPLETION CONSUMER, as (module, qualified function). Each reads completion through this
# module (completion / completion_status); the suite derives the set from call sites.
COMPLETION_CONSUMERS = (
    ('frontier.py', 'claimable'),
    ('frontier.py', 'withheld'),
    ('plan.py', '_status'),
    ('work_state.py', 'completion_view'),
    ('control_eligibility.py', 'completion_status'),
    ('control_eligibility.py', 'Gate.landed'),
    ('control_eligibility.py', 'Gate.landing'),
    ('control_eligibility.py', 'Gate.completion'),
    ('control_eligibility.py', 'Gate._dependencies'),
)
# The reader's call names a consumer site is recognized by.
READER_CALLS = ('completion_status', 'completion', 'landed', '_landed_from')

# Labels whose record the claim transition itself rewrites (VELDO-0031). They are compared by their
# definition, the record minus these lifecycle fields; ownership is decided fresh at every station.
LIFECYCLE_FIELDS = {'unit': ('state',), 'backlog': ('state',)}
OUTPUT_LABELS = ('claim',)

# VELDO-0076: the one lifecycle state of a project record (control_project.py) whose units any station
# admits. A record with no lifecycle state predates that service, which is its kind's only writer.
PROJECT_ACTIVE = 'ACTIVE'
PROJECT_KIND = 'project'
PROJECT_OWNER_ROLE = 'project_owner'

# The error taxonomy every refusal code maps to (observability). Unknown is never success.
TAXONOMY = {
    'invalid_input': 'invalid_input', 'missing_authority': 'missing_authority', 'draft_plan': 'missing_authority',
    'stale_scope': 'stale_subject', 'stale_input': 'stale_subject', 'stale_claim': 'stale_subject',
    'stale_authority': 'stale_subject', 'unresolved_dependency': 'missing_evidence',
    'unresolved_decision': 'missing_authority', 'blocked': 'missing_authority',
    'missing_evidence': 'missing_evidence', 'reviewer_not_independent': 'missing_authority',
    'clock_uncertain': 'unknown_outcome', 'unavailable_service': 'unavailable_service',
    'eligibility_required': 'missing_authority', 'reservation_required': 'missing_authority',
    'enrollment_unanswerable': 'unavailable_service', 'enrollment_refused': 'missing_authority',
    'host_trust_required': 'missing_authority', 'host_trust_unreadable': 'invalid_input',
    'host_trust_refused': 'missing_authority',
    'usage_cap': 'missing_authority', 'usage_refused': 'missing_authority', 'window_exhausted': 'missing_authority',
    'missing_ceiling': 'missing_authority', 'unknown_allowance': 'unknown_outcome', 'unknown_window': 'unknown_outcome',
    'unknown_window_usage': 'unknown_outcome',
    # VELDO-0054: the named blockers of a governing decision (control_decision_dependency).
    'missing_decision': 'missing_authority', 'ambiguous_decision': 'missing_authority',
    'unsupported_decision': 'missing_authority', 'unsigned_decision': 'missing_authority',
    'unbound_decision': 'stale_subject', 'decision_ruling': 'missing_authority',
    # VELDO-0076: the unit's project is paused, canceled or completed, is not a project record, or
    # its recorded owner is no longer current.
    'project_not_active': 'missing_authority',
}

OBSERVATION_LIMIT = 1000


def taxonomy(code):
    return TAXONOMY.get(code.split(':', 1)[0], 'unknown_outcome')


UNEXPECTED_MESSAGE_LIMIT = 160


def unexpected(error):
    """The named refusal for a fault nothing anticipated while deciding one unit (VELDO-0054): its
    outcome is unknown, so it refuses that unit by name and never raises into the caller's loop. It
    carries the fault's type and its message: on one line, ASCII only, every control character shown
    as an escape, no ';' (the separator refusal lists are joined with), bounded in length, and
    '<unprintable>' when the exception's own text raises."""
    code = 'unknown_outcome:evaluation_error/' + type(error).__name__
    try:
        text = str(error)
    except Exception:  # noqa: BLE001 - an exception whose own text raises is still named
        text = '<unprintable>'
    message = ' '.join(text.split()).replace(';', ',')
    message = message.encode('ascii', 'backslashreplace').decode('ascii')
    message = ''.join('\\x%02x' % ord(c) if ord(c) < 32 or ord(c) == 127 else c for c in message)
    message = message[:UNEXPECTED_MESSAGE_LIMIT]
    return code + '/' + message if message else code


class Refused(Exception):
    """A named refusal of one station decision; `decision` carries every refusal and input."""
    def __init__(self, code, detail='', decision=None):
        self.code, self.detail, self.decision = code, detail, decision
        super().__init__(code + (': ' + detail if detail else ''))


class Stopped(RuntimeError):
    """A named terminal stop: an enabled floor entry has no eligibility (or reservation) wired."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__('eligibility stopped: ' + reason)


# Every floor module loads this file by path under its own name. Keep one process-wide identity
# for both exceptions, as claim.py does for ClaimStopped, so any caller can catch them by class.
import sys as _sys
import types as _types
import weakref as _weakref
_errors = _sys.modules.setdefault('veldo_eligibility_errors', _types.ModuleType('veldo_eligibility_errors'))
for _name, _cls in (('Refused', Refused), ('Stopped', Stopped)):
    if not hasattr(_errors, _name):
        setattr(_errors, _name, _cls)
Refused, Stopped = _errors.Refused, _errors.Stopped


# The discovery walk lives in the shared Git boundary so every organ asks it the same way.
_GP = _organ('git_process')
_claims_a_repository = _GP.claims_a_repository
_entry_exists = _GP.entry_exists


def enrolled(repo_root):
    """Whether this workspace carries an authority enrollment binding (VELDO-0029).

    Only a directory in which Git's discovery finds no repository at all is "not enrolled". A Git
    that fails where a repository IS present (a malformed config, an unreadable common directory, a
    timeout, no git executable) is the named stop enrollment_unanswerable: the binding lives inside
    that repository, so its absence cannot be concluded, and a silent 'not enrolled' there would let
    every enabled entry run pre-factory with no eligibility at all."""
    try:
        return _entry_exists(E.binding_path(str(repo_root)))
    except E.EnrollmentRefused as error:
        if _claims_a_repository(repo_root):
            raise Stopped('enrollment_unanswerable') from error
        return False
    except (OSError, subprocess.SubprocessError) as error:
        raise Stopped('enrollment_unanswerable') from error


def gate_for(repo_root, gate):
    """THE ONE RESOLUTION every floor entry calls: the wired Gate; a named stop when the
    repository is enrolled and nothing is wired; None (pre-factory behavior) otherwise."""
    if gate is not None:
        return gate
    if enrolled(repo_root):
        raise Stopped('eligibility_required')
    return None


# ---------------------------------------------------------------------------------------------
# The production construction: a Gate built from the workspace's signed enrollment binding.
# ---------------------------------------------------------------------------------------------

# The OpenSSH signature namespace an enrollment binding is signed under (ssh-keygen -Y sign -n).
ENROLLMENT_NAMESPACE = 'veldo-enrollment'
HOST_TRUST_SCHEMA = 'veldo.host_trust/v1'


class HostTrust:
    """What THIS HOST trusts when it decides an enrollment binding: its own identity (the binding's
    host_identity must equal it) and an OpenSSH allowed-signers file naming the principals whose
    signature, under ENROLLMENT_NAMESPACE, makes a binding. These are VELDO-0029 verify_binding's
    `host_identity` and `verify`. Installed with the host, outside every repository: a record the
    checked workspace carries (its binding, its tracked .veldo/keys) cannot vouch for itself.

    ENFORCED, not assumed: the signers path must be absolute (host_trust_refused:signers_not_absolute;
    a relative one would resolve against wherever the process runs, usually the workspace), and the
    file it resolves to after every symlink must lie outside the checked workspace, its working tree
    and its git directory (host_trust_refused:signers_inside_workspace). The resolved file is the
    one read, so a symlink retargeted after the check cannot substitute another."""

    def __init__(self, host_identity, enrollment_signers, settlement_signers=None):
        if not isinstance(host_identity, str) or not host_identity.strip() \
                or not isinstance(enrollment_signers, str) or not enrollment_signers.strip():
            raise Stopped('host_trust_unreadable')
        if not os.path.isabs(enrollment_signers):
            raise Stopped('host_trust_refused:signers_not_absolute')
        if settlement_signers is not None:
            if not isinstance(settlement_signers, str) or not settlement_signers.strip():
                raise Stopped('host_trust_unreadable')
            if not os.path.isabs(settlement_signers):
                raise Stopped('host_trust_refused:settlement_signers_not_absolute')
        self.host_identity, self.enrollment_signers = host_identity, enrollment_signers
        self.settlement_signers = settlement_signers

    def settlement_trust(self, workspace):
        """VELDO-0054: the decision settlement signers this host trusts, as a
        control_decision_dependency.SettlementTrust, or None when the host names none (every
        settlement is then unsigned and every governing decision blocks). Held to the same rule as
        the enrollment signers: the file it resolves to must lie outside the checked workspace."""
        if self.settlement_signers is None:
            return None
        resolved = os.path.realpath(self.settlement_signers)
        if any(os.path.commonpath([resolved, area]) == area for area in _workspace_areas(workspace)):
            raise Stopped('host_trust_refused:settlement_signers_inside_workspace')
        try:
            return DD.SettlementTrust(Path(resolved).read_text())
        except (OSError, ValueError) as error:
            raise Stopped('host_trust_unreadable') from error

    def verifier(self, principal, workspace):
        """verify(message, signature) -> bool for a binding enrolled by `principal` in `workspace`,
        read from the signers file only when it resolves outside that workspace."""
        resolved = os.path.realpath(self.enrollment_signers)
        if any(os.path.commonpath([resolved, area]) == area for area in _workspace_areas(workspace)):
            raise Stopped('host_trust_refused:signers_inside_workspace')
        try:
            signers = Path(resolved).read_text()
        except OSError as error:
            raise Stopped('host_trust_unreadable') from error
        AC = _organ('authority_contract')

        def verify(message, signature):
            if not isinstance(principal, str) or not principal.strip() or not isinstance(signature, str):
                return False
            return AC.ssh_keygen_verify(message, signature, signers, principal, ENROLLMENT_NAMESPACE)[0]
        return verify


def _workspace_areas(workspace):
    """Every directory the checked workspace controls, each resolved: the path it was named by, its
    working tree, its git common directory and, for a clone whose common directory is its `.git`,
    that clone's working tree (a linked worktree's main checkout carries the same tracked files)."""
    try:
        top = E._git(workspace, 'rev-parse', '--show-toplevel')
        common = E.git_common_dir(workspace)
    except E.EnrollmentRefused as error:
        raise Stopped('enrollment_unanswerable') from error
    areas = {os.path.realpath(str(workspace)), os.path.realpath(top), common}
    if os.path.basename(common) == '.git':
        areas.add(os.path.dirname(common))
    return sorted(areas)


def host_trust_path():
    """Where this host's trust is installed: $XDG_CONFIG_HOME/veldo/host_trust.json, or
    ~/.config/veldo/host_trust.json when XDG_CONFIG_HOME is unset or not absolute."""
    base = os.environ.get('XDG_CONFIG_HOME') or ''
    if not os.path.isabs(base):
        base = os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(base, 'veldo', 'host_trust.json')


def load_host_trust(path=None):
    """The installed HostTrust, None when this host has installed none, a named stop when what is
    installed cannot be read as one."""
    path = path or host_trust_path()
    try:
        with open(path) as handle:
            text = handle.read()
    except FileNotFoundError:
        return None
    except OSError as error:
        raise Stopped('host_trust_unreadable') from error
    try:
        record = json.loads(text)
    except ValueError as error:
        raise Stopped('host_trust_unreadable') from error
    if not isinstance(record, dict) or record.get('schema') != HOST_TRUST_SCHEMA:
        raise Stopped('host_trust_unreadable')
    return HostTrust(record.get('host_identity'), record.get('enrollment_signers'), record.get('settlement_signers'))


def enrolled_gate(repo_root, trust, observe=None):
    """A Gate over the store the workspace's binding names, with the binding's domain, repository
    and authority generation. The binding is read ONCE and that same record is verified
    (control_enrollment.verify_binding: signature, repository identity, clone, host), so every
    coordinate the Gate uses is one that verified; any problem is a named stop."""
    workspace = str(repo_root)
    try:
        binding = E.read_binding(workspace)
    except E.EnrollmentRefused as error:
        raise Stopped('enrollment_refused:' + error.reason) from error
    if binding is None:
        raise Stopped('enrollment_refused:not_enrolled')
    principal = binding.get('enrolled_by') if isinstance(binding, dict) else None
    try:
        problems = E.verify_binding(workspace, binding, trust.verifier(principal, workspace), trust.host_identity)
    except E.EnrollmentRefused as error:
        raise Stopped('enrollment_unanswerable') from error
    if problems:
        raise Stopped('enrollment_refused:' + problems[0][0])
    settlements = trust.settlement_trust(workspace) if hasattr(trust, 'settlement_trust') else None
    store = _organ('control_store')
    try:
        conn = store.open_store(E.store_path_for(binding), mode='r')
    except (store.StoreRefused, sqlite3.Error, OSError) as error:
        raise Stopped('unavailable_service:store') from error
    return Gate(store, conn, domain_uuid=binding['domain_uuid'], repository_uuid=binding['repository_uuid'],
                authority_generation=binding['authority_generation'], observe=observe, workspace=workspace,
                settlement_trust=settlements)


def entry_gate(repo_root, gate=None, trust=None, observe=None):
    """THE PRODUCTION CONSTRUCTION every command-line entry calls: the wired Gate when one is given;
    None in an unenrolled tree (pre-factory behavior); in an enrolled repository, the Gate built from
    its signed binding under this host's trust (the installed one unless `trust` is given), or the
    named stop host_trust_required when this host trusts nothing."""
    if gate is not None:
        return gate
    if not enrolled(repo_root):
        return None
    if trust is None:
        trust = load_host_trust()
    if trust is None:
        raise Stopped('host_trust_required')
    return enrolled_gate(repo_root, trust, observe=observe)


def completion_status(gate, status):
    """A {spec: status} map in which 'shipped' means exactly revision_landed from the one completion
    reader. Status text says shipped only for a landed revision; everything else keeps its word, and
    a shipped string without the landing receipt is renamed so no reader counts it."""
    if gate is None:
        return status
    result = {}
    for sid, st in status.items():
        if gate.landed(sid):
            result[sid] = 'shipped'
        else:
            result[sid] = 'shipped_without_landing_receipt' if st == 'shipped' else st
    return result


def _definition(label, data):
    drop = LIFECYCLE_FIELDS.get(label, ())
    body = {k: v for k, v in (data or {}).items() if k not in drop} if isinstance(data, dict) else data
    return SN.digest(SN.canonical(body))


# The installed files whose code judges an architecture, by the role each plays.
VALIDATOR_ROLES = (('entry_point', 'validate.py'), ('entry', 'validate_checks.py'), ('loader', 'contract_loader.py'),
                   ('validator', 'arch.py'), ('parser', 'yamlish.py'))
# Labels only: the recorded identity is whatever the snapshot executes, each module keyed by its module name
# (unique among held files) with its role label as a field. A role label is never a key: an engine file named
# after a role (parser.py) would take the key of that role's module and drop it from the identity.
ROLE_LABELS = {name[:-3]: role for role, name in VALIDATOR_ROLES}


class _MemoryLoader:
    """Executes one held engine module, by name, from the bytes the snapshot read for that name."""

    def __init__(self, snapshot, held):
        self.snapshot, self.held = snapshot, held
        self.body = snapshot._bodies[held]

    def create_module(self, spec):
        return None

    def get_source(self, fullname):
        """The source that runs, decoded from the held bytes (inspect and tracebacks ask the loader)."""
        return importlib.util.decode_source(self.body)

    def exec_module(self, module):
        # The module's own `import importlib.util` resolves to the snapshot's, so every sibling it loads
        # is answered by name from the same held bytes, never read from disk.
        module.__dict__['__builtins__'] = self.snapshot.builtins
        # The code is compiled under a key only this snapshot uses, and linecache holds its lines under that
        # key with no modification time: tracebacks and inspect show the code that ran, no other loader's
        # traceback ever reads these lines, and a second snapshot never replaces them.
        key = self.snapshot.source_key(self.held)
        linecache.cache[key] = (len(self.body), None, importlib.util.decode_source(self.body).splitlines(True), key)
        self.snapshot._keys.append(key)
        # Recorded before the module runs. A module whose load raises stays in the identity only when the module
        # loading it catches the error; a raise out of the snapshot refuses the decision with validator {}.
        self.snapshot._executed[self.held] = 'sha256:' + hashlib.sha256(self.body).hexdigest()
        exec(compile(self.body, key, 'exec', dont_inherit=True), module.__dict__)


# The most bytes the snapshot reads from any one engine file (the largest is under 100 KiB). Every held file
# is read at snapshot construction, whether or not anything runs it, so without a limit one large file (a
# sparse 1 GiB zz.py) costs its whole size in time and memory before the first decision answers.
ENGINE_FILE_LIMIT = 1 << 20


def _read_engine_file(path):
    """The bytes of one engine file, read once. The file is opened without waiting and judged by the open
    descriptor: only a regular file (after links) is read; a FIFO, a directory or anything else under a
    '.py' name is the named stop ImportError, never a wait. At most ENGINE_FILE_LIMIT + 1 bytes are read,
    and a file longer than the limit is the named stop ImportError (the length read decides, not the size
    the file reports, so a file that grows or reports no size is bounded too)."""
    try:
        fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0))
    except OSError as error:
        raise ImportError('engine file %s cannot be opened: %s' % (path, error)) from error
    with os.fdopen(fd, 'rb') as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ImportError('engine file %s is not a regular file' % (path,))
        body = handle.read(ENGINE_FILE_LIMIT + 1)
    if len(body) > ENGINE_FILE_LIMIT:
        raise ImportError('engine file %s is longer than the %d byte limit' % (path, ENGINE_FILE_LIMIT))
    return body


def _forget_lines(keys):
    for key in keys:
        linecache.cache.pop(key, None)


class ValidatorSnapshot:
    """The installed structural validator, loaded ONCE from ONE read of the installed engine's bytes
    (VELDO-0053, R50), held by MODULE NAME. Each engine module is read exactly once by its installed name
    (the open follows links), its bytes digested and held under its name, never under a path. Every load
    request the validator makes (importlib.util's spec_from_file_location, the one way the engine loads its
    organs) is answered by the module name it asks for, the file name of its request, from those held
    bytes, compiled into a fresh module object whose __file__ is the installed path of that name. There is
    no path lookup, so aliases, links and resolved paths cannot make one name's bytes serve another; a
    name not held is the named stop ImportError. Nothing is written to or loaded from disk, so the digests
    recorded are of exactly the code that runs, and a later change on disk is neither run nor recorded by
    a decision of this snapshot. The structural validator (arch.py) is loaded once here and reused for
    every contract."""

    def __init__(self, installed=None):
        installed = Path(os.path.realpath(str(installed or Path(__file__).resolve().parent)))
        self._installed, self._id = installed, uuid.uuid4().hex
        # The empty module name (a file named '.py') is never held, so no request can be answered with it.
        self._bodies = {path.name[:-3]: _read_engine_file(path) for path in sorted(installed.glob('*.py')) if path.name[:-3]}
        self._keys, self._executed = [], {}
        _weakref.finalize(self, _forget_lines, self._keys)
        util = _types.ModuleType('importlib.util')
        util.__dict__.update({k: v for k, v in vars(importlib.util).items() if not k.startswith('__')})
        util.spec_from_file_location = self._spec
        package = _types.ModuleType('importlib')
        package.__dict__.update({k: v for k, v in vars(importlib).items() if not k.startswith('__')})
        package.util = util
        self._importlib = package
        self.builtins = dict(vars(builtins))
        self.builtins['__import__'] = self._import
        spec = self._named('eligibility_validator_snapshot', 'validate')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.validate, self.arch = module, module.entry_validator()

    @property
    def identity(self):
        """Every held module this snapshot has executed, in the order it ran, keyed by its module name: its role
        label (None when it has none), its installed path and the digest of the bytes it ran from."""
        return {held: {'module': held, 'role': ROLE_LABELS.get(held), 'path': str(self._installed / (held + '.py')),
                       'digest': digest}
                for held, digest in self._executed.items()}

    def source_key(self, held):
        """The file name this snapshot's code of `held` is compiled and cached under, unique to it."""
        return '<veldo validator snapshot %s: %s>' % (self._id, self._installed / (held + '.py'))

    def _import(self, name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and name in ('importlib', 'importlib.util'):
            return self._importlib.util if name == 'importlib.util' and fromlist else self._importlib
        return builtins.__import__(name, globals, locals, fromlist, level)

    def _named(self, name, held):
        """The spec of the held engine module `held`, executed from its held bytes; ImportError if not held."""
        if held not in self._bodies:
            raise ImportError('the validator snapshot holds no engine module named %r' % (held,))
        spec = importlib.util.spec_from_loader(name, _MemoryLoader(self, held), origin=str(self._installed / (held + '.py')))
        spec.has_location = True
        return spec

    def _spec(self, name, location=None, *args, **kwargs):
        """spec_from_file_location for the snapshot's modules: the request names an engine module by its
        file name, and that NAME is answered from the held bytes. The rest of the path is never looked up."""
        file_name = os.path.basename(str(location)) if location is not None else ''
        return self._named(name, file_name[:-3] if file_name.endswith('.py') else '')

    def contract(self, workspace, required):
        """(ContractLoad, digest of the bytes the loader parsed) through validate.py's public entry_contract."""
        return self.validate.entry_contract(workspace, required, arch=self.arch)


def _artifact_identity(path, parsed):
    """{path, type, digest} of the architecture artifact that was judged. The digest is the loader's,
    of the very bytes it parsed (None when nothing was read and parsed); the file is never read here."""
    kind = ('absent' if not os.path.lexists(path) else 'symlink' if os.path.islink(path)
            else 'directory' if os.path.isdir(path) else 'regular' if os.path.isfile(path) else 'other')
    return {'path': str(path), 'type': kind, 'digest': parsed}


class Gate:
    """One domain's shared eligibility over a real control store connection. Read-only."""

    def __init__(self, store, conn, *, domain_uuid, repository_uuid, authority_generation=1, observe=None,
                 workspace=None, settlement_trust=None, clock=time.time):
        self.store, self.conn = store, conn
        # VELDO-0076: the time a project owner's membership is judged current at.
        self.clock = clock
        # The workspace whose architecture every decision judges (VELDO-0053). A store-only Gate (no
        # workspace) cannot look at a file, so its architecture predicate always refuses
        # (missing_evidence:architecture/workspace): the default argument is never a pass.
        self.workspace = str(workspace) if workspace is not None else None
        self._validator = None
        # VELDO-0054: the settlement signers this Gate verifies against (None trusts no settlement).
        self.settlement_trust = settlement_trust
        self.decision_counts = {'accepted': 0, 'refused': 0}
        self.decision_last = {}
        # Settlement records nothing can associate with a governing record, each observed once.
        self.invalid_records = set()
        self.domain_uuid, self.repository_uuid = domain_uuid, repository_uuid
        self.authority_generation = authority_generation
        self.observe = observe or (lambda event: None)
        self.claims = _organ('control_claim')
        self.counts = {'accepted': 0, 'refused': 0}
        # Diagnostics only, bounded: the durable log is the observe callback's sink.
        self.observations = collections.deque(maxlen=OBSERVATION_LIMIT)
        self.last = {}

    def close(self):
        """Close the read connection (a Gate the production construction opened owns it)."""
        self.conn.close()

    @property
    def refusal_types(self):
        """The store's own refusals this Gate's reads raise: an accepted row whose digest does not match
        (control_snapshot.Refused) and a store refusal (control_store.StoreRefused). A reader that
        builds on the Gate (veldo status) catches exactly these and names them with refusal_code."""
        return (SN.Refused, self.store.StoreRefused)

    @staticmethod
    def refusal_code(error):
        """The one naming of a store refusal: a digest mismatch is missing authority, anything else
        invalid input, each followed by the store's own code."""
        return ('missing_authority:' if 'digest' in error.code else 'invalid_input:') + error.code

    # -- reads -----------------------------------------------------------------------------------

    def _entity(self, identity):
        return SN.entity(self.store, self.conn, identity)

    def _collection(self, kind, keep):
        members = []
        for (identity,) in self.conn.execute('SELECT id FROM entities WHERE kind=? ORDER BY id', (kind,)):
            item = self._entity(identity)
            if keep(item['value']['data']):
                members.append(item)
        return members

    def _receipts(self, unit):
        return self._collection('completion_receipt',
                                lambda d: isinstance(d.get('subject'), dict) and d['subject'].get('id') == unit)

    @staticmethod
    def _data(item):
        return (item.get('value') or {}).get('data') if item else None

    def _landed_from(self, receipts, subject):
        """The id of the first receipt that lands `subject` (the revision_landed fact for exactly that
        revision with a complete landing receipt for that unit), or None."""
        for item in receipts:
            r = self._data(item)
            if CC.fact_problems('revision_landed', r, subject):
                continue
            landing = r.get('publication_receipt')
            if isinstance(landing, dict) and not CC.landing_receipt_problems(landing) \
                    and landing.get('unit_id') == subject['id']:
                return item['id']
        return None

    def _subject(self, unit):
        data = self._data(self._entity(unit))
        if not isinstance(data, dict) or not isinstance(data.get('revision'), int):
            return None
        return {'id': unit, 'revision': data['revision']}

    def completion(self, unit):
        """THE COMPLETION READER: the four facts for the unit's current accepted revision, each only
        from its own stored receipt. Landed needs the exact landing receipt as well."""
        with self._reading():
            subject = self._subject(unit)
            receipts = self._receipts(unit)
        if subject is None:
            return {fact: False for fact in CC.FACT_ORDER}
        state = CC.completion_state([self._data(r) for r in receipts], subject)
        state['revision_landed'] = state['revision_landed'] and self._landed_from(receipts, subject) is not None
        return state

    def landed(self, unit):
        return self.completion(unit)['revision_landed']

    def landing(self, unit):
        """VELDO-0078: the landed fact's own evidence, the id of the receipt that lands the unit's current
        accepted revision, or None, read in one read transaction. It is None exactly when landed() is
        False; the backlog's DONE records it."""
        with self._reading():
            subject = self._subject(unit)
            receipts = self._receipts(unit)
        # The receipt _landed_from returns establishes the revision_landed fact itself, so this is landed().
        return None if subject is None else self._landed_from(receipts, subject)

    def unit_record(self, unit):
        """The unit's accepted execution_unit data, read in one read transaction, or None."""
        with self._reading():
            try:
                item = self._entity(unit)
            except (SN.Refused, self.store.StoreRefused):
                return None
        if not item or item['value']['kind'] != 'execution_unit':
            return None
        return self._data(item)

    def _reading(self):
        gate = self

        class _Read:
            def __enter__(self):
                self.owned = not gate.conn.in_transaction
                if self.owned:
                    gate.conn.execute('BEGIN')

            def __exit__(self, *exc):
                if self.owned and gate.conn.in_transaction:
                    gate.conn.execute('ROLLBACK')
                return False
        return _Read()

    def read(self, unit, references=()):
        """Every input a station decision over `unit` consumes, read in ONE read transaction.
        `references` are decision ids an inline open_decisions entry outside the store names."""
        with self._reading():
            inputs = {}
            u = self._entity(unit)
            inputs['unit'] = u
            data = self._data(u) or {}
            inputs['backlog'] = self._entity(data.get('backlog_item_uuid') or 'backlog:' + unit)
            inputs['plan'] = self._entity('plan:' + data['plan']) if data.get('plan') else None
            inputs['admission'] = self._entity('admission:' + unit)
            inputs['project'] = self._entity('project:' + str(data.get('project')))
            owner = self._project_owner(inputs['project'])
            if owner is not None:
                inputs['project_owner'] = self._entity(owner)
            inputs['authority'] = self._entity('authority:' + self.domain_uuid)
            inputs['claim'] = self._entity(self.claims.claim_id(self.repository_uuid, unit))
            for dep in data.get('depends_on') or []:
                inputs['dependency/' + dep] = self._entity(dep)
                inputs['receipts/' + dep] = self._receipts(dep)
            # VELDO-0054: every governing record that blocks the unit or its plan or that a reference
            # (the accepted plan's open_decisions, or one passed in) names, every settlement associated
            # with one of them, and the current accepted digest of each record's subject.
            refs = DD.references(self._data(inputs.get('plan')), unit) + list(references)
            if inputs.get('plan') is not None and any(not isinstance(r, str) for r in
                                                      DD.references(self._data(inputs['plan']), unit)):
                self._invalid_record(inputs['plan']['id'], 'open_decisions')
            inputs['decisions'] = self._decisions(unit, data.get('plan'), refs)
            governing = {m['id'] for m in inputs['decisions']}
            inputs['settlements'] = self._settlements(governing)
            inputs['decision_subjects'] = self._subjects(inputs['decisions'])
            inputs['blockers'] = self._collection('blocker', lambda d: d.get('unit') == unit)
            inputs['approvals'] = self._collection('approval', lambda d: d.get('unit') == unit)
            inputs['architecture'] = self._entity('architecture:' + self.repository_uuid)
            watermark = self.conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]
        return {k: v for k, v in inputs.items() if v is not None}, watermark

    def _decisions(self, unit, plan, refs):
        """Every governing record that bears on `unit` (control_decision_dependency.governs). A record
        whose `blocks` is malformed is recorded once as a named invalid_input observation, and it still
        governs every unit it names anywhere inside that value, where it is refused by name."""
        members = []
        for (identity,) in self.conn.execute('SELECT id FROM entities WHERE kind=? ORDER BY id', ('decision',)):
            item = self._entity(identity)
            data = self._data(item)
            if DD.blocks_malformed(data):
                self._invalid_record(identity, 'blocks')
            if isinstance(data, dict) and data.get('decision_id') is not None and not isinstance(data['decision_id'], str):
                self._invalid_record(identity, 'decision_id')
            if DD.governs(data, unit, plan, refs):
                members.append(item)
        return members

    def _settlements(self, governing):
        """Every settlement associated with one of the `governing` record ids. A settlement whose
        `decision` is not an id (a list, a mapping) concerns no unit: it is left out of every unit's
        read, and recorded once as a named invalid_input observation, never raised."""
        members = []
        for (identity,) in self.conn.execute('SELECT id FROM entities WHERE kind=? ORDER BY id', ('decision_settlement',)):
            item = self._entity(identity)
            data = self._data(item)
            target = data.get('decision') if isinstance(data, dict) else None
            if not isinstance(target, str):
                self._invalid_record(identity, 'decision')
            elif target in governing:
                members.append(item)
        return members

    def _invalid_record(self, identity, field):
        if identity in self.invalid_records:
            return
        self.invalid_records.add(identity)
        code = 'invalid_input:%s/%s' % (identity, field)
        event = {'schema': SCHEMA, 'operation': 'invalid_record', 'domain_uuid': self.domain_uuid,
                 'repository_uuid': self.repository_uuid, 'unit': None, 'entity': identity,
                 'decision_id': str(uuid.uuid4()), 'follows': None, 'watermark': None, 'accepted_inputs': {},
                 'outcome': 'refused', 'refusals': [code], 'taxonomy': [taxonomy(code)]}
        self.observations.append(event)
        self.observe(event)

    def _subjects(self, records):
        """One derived input: the current accepted digest of every governing record's subject, keyed
        by the subject's entity id. Its digest is exactly what the decision consumed, so a lifecycle
        write (a claim moving the unit's state) leaves it current and a changed subject does not."""
        current = {}
        for item in records:
            data = self._data(item)
            subject = data.get('subject') if isinstance(data, dict) else None
            eid = DD.subject_entity(subject)
            if eid is not None and eid not in current:
                current[eid] = DD.subject_digest(subject['kind'], self._data(self._entity(eid)))
        return {'id': 'decision_subjects', 'version': 0, 'digest': SN.digest(SN.canonical(current)),
                'value': {'kind': 'decision_subjects', 'data': current}}

    def _decision_codes(self, unit, inputs, references=()):
        refs = DD.references(self._data(inputs.get('plan')), unit) + list(references)
        records = [(m['id'], self._data(m)) for m in inputs.get('decisions') or []]
        settlements = [(m['id'], self._data(m)) for m in inputs.get('settlements') or []]
        subjects = self._data(inputs.get('decision_subjects')) or {}
        verify = self.settlement_trust.verify if self.settlement_trust is not None else None
        try:
            codes = DD.blockers(unit, refs, records, settlements, subjects, verify, self.domain_uuid)
        except DD.Unavailable:
            codes = ['unavailable_service:settlement_verifier']
        outcome = 'refused' if codes else 'accepted'
        self.decision_counts[outcome] += 1
        self.decision_last[unit] = outcome
        return codes

    def decision_blockers(self, unit, references=()):
        """VELDO-0054, for the plan and frontier readers: the named blockers the governing decisions of
        `unit` raise, [] when none blocks. Each inline reference must resolve to one accepted record
        whose current exact binding is settled; the inline text itself resolves nothing."""
        event = {'schema': SCHEMA, 'operation': 'decision_dependency', 'domain_uuid': self.domain_uuid,
                 'repository_uuid': self.repository_uuid, 'unit': unit, 'decision_id': str(uuid.uuid4()),
                 'follows': None, 'watermark': None, 'accepted_inputs': {}, 'references': list(references)}
        try:
            inputs, watermark = self.read(unit, references)
            codes = self._decision_codes(unit, inputs, references)
            identities = {label: self._identity(label, inputs[label])
                          for label in ('plan', 'decisions', 'settlements', 'decision_subjects') if label in inputs}
            event.update(watermark=watermark, accepted_inputs={
                label: identity.get('version', identity['digest']) for label, identity in identities.items()})
        except (SN.Refused, self.store.StoreRefused) as error:
            codes = [self.refusal_code(error)]
        except sqlite3.Error:
            codes = ['unavailable_service:store']
        except Stopped:
            raise  # a named stop is the caller's, never a unit hold
        except Exception as error:  # noqa: BLE001 - VELDO-0054: an unexpected fault is named, never raised
            codes = [unexpected(error)]
        event.update(outcome='refused' if codes else 'accepted', refusals=list(codes),
                     taxonomy=sorted({taxonomy(c) for c in codes}))
        self.observations.append(event)
        self.observe(event)
        return codes

    # -- predicates ------------------------------------------------------------------------------

    def _dependencies(self, data, inputs):
        codes = []
        for dep in data.get('depends_on') or []:
            dd = self._data(inputs.get('dependency/' + dep))
            if not isinstance(dd, dict) or not isinstance(dd.get('revision'), int):
                codes.append('unresolved_dependency:' + dep)
                continue
            if not self._landed_from(inputs.get('receipts/' + dep) or [], {'id': dep, 'revision': dd['revision']}):
                codes.append('unresolved_dependency:' + dep)
        return codes

    def _predicate(self, name, unit, inputs, context):
        data = self._data(inputs['unit']) or {}
        if name == 'admission_current':
            a = self._data(inputs.get('admission'))
            if not isinstance(a, dict) or a.get('state') != 'accepted' or a.get('unit') != unit:
                return ['missing_authority:admission']
            return [] if a.get('scope_digest') == data.get('scope_digest') and a.get('scope_digest') else ['stale_scope']
        if name == PRIORITY_PREDICATE:
            # VELDO-0078: the backlog's one executable question over the unit and item records this
            # decision consumed: the item PRIORITIZED or ACTIVE, the unit prioritized and not terminal.
            return BL.executable_record_problems(data, self._data(inputs.get('backlog')))
        if name == 'plan_not_draft':
            if not data.get('plan'):
                return []
            p = self._data(inputs.get('plan'))
            if not isinstance(p, dict):
                return ['missing_authority:plan']
            return [] if p.get('status') in ('ready', 'in_progress') else ['draft_plan']
        if name == 'decisions_settled':
            # VELDO-0054: only the current exact binding of an accepted signed settlement clears a
            # governing decision; a record's own status text resolves nothing.
            return self._decision_codes(unit, inputs)
        if name == 'dependencies_resolved':
            return self._dependencies(data, inputs)
        if name == 'no_blockers':
            return ['blocked:' + b['id'] for b in inputs['blockers'] if not self._data(b).get('cleared')]
        if name == 'claim_current':
            holder = (context or {}).get('holder')
            claim = self._data(inputs.get('claim')) or {}
            status = self.claims.ownership(claim, data, self._data(inputs.get('backlog')) or {})
            if status == 'unanswerable':
                return ['clock_uncertain']
            if status != 'owned' or not holder or claim.get('holder') != holder:
                return ['missing_authority:claim']
            wanted = (context or {}).get('generation')
            return ['stale_claim'] if wanted is not None and claim.get('generation') != wanted else []
        if name == 'reviewer_independent':
            reviewer, producer = (context or {}).get('reviewer'), data.get('producer')
            if not producer:
                return ['missing_evidence:producer']
            if not isinstance(reviewer, str) or not reviewer.strip() or reviewer.strip().lower() == str(producer).strip().lower():
                return ['reviewer_not_independent']
            return []
        if name == 'authority_current':
            a = self._data(inputs.get('authority'))
            if not isinstance(a, dict) or a.get('state') != 'active':
                return ['missing_authority:authority']
            return [] if a.get('generation') == self.authority_generation else ['stale_authority']
        if name == 'approvals_valid':
            granted = {self._data(a).get('name') for a in inputs['approvals']
                       if self._data(a).get('state') == 'granted' and self._data(a).get('revision') == data.get('revision')}
            return ['missing_authority:approval/' + n for n in data.get('approvals_required') or [] if n not in granted]
        if name in TRANSACTIONAL:
            return []
        # Richer governance this release cannot evaluate blocks rather than being presumed satisfied.
        return ['missing_authority:unsupported/' + name]

    def _unit_problems(self, unit, inputs):
        data = self._data(inputs['unit'])
        if not isinstance(data, dict) or inputs['unit']['value']['kind'] != 'execution_unit' \
                or data.get('repository_uuid') != self.repository_uuid:
            return ['missing_authority:unit']
        problems = []
        b = self._data(inputs.get('backlog'))
        if not isinstance(b, dict) or inputs['backlog']['value']['kind'] != 'backlog_item':
            problems.append('missing_authority:backlog')
        record = inputs.get('project') or {}
        project = self._data(record)
        if record.get('value') is not None and record['value'].get('kind') != PROJECT_KIND:
            # VELDO-0076: only a record of kind project decides a unit's project.
            problems.append('project_not_active:not_a_project')
        elif not isinstance(project, dict):
            problems.append('missing_authority:project')
        elif 'state' in project and project['state'] != PROJECT_ACTIVE:
            # VELDO-0076: a paused, canceled or completed project stops every station of its units.
            problems.append('project_not_active:%s' % project['state'])
        elif 'state' in project and not self._owner_current(data.get('project'), project, inputs.get('project_owner')):
            # VELDO-0076: nobody may stop a project whose owner lost his authority, so its work halts here.
            problems.append('project_not_active:owner_not_current')
        return problems

    def _project_owner(self, record):
        value = (record or {}).get('value') or {}
        data = value.get('data')
        if value.get('kind') != PROJECT_KIND or not isinstance(data, dict):
            return None
        owner = data.get('owner')
        return owner if isinstance(owner, str) and owner else None

    def _owner_current(self, name, project, member):
        """Whether the project's recorded owner is a current person member holding project_owner in a
        scope that covers the project, from his accepted membership record (id = principal)."""
        owner = project.get('owner')
        value = (member or {}).get('value') or {}
        if not isinstance(owner, str) or not owner or value.get('kind') != 'membership' \
                or not isinstance(value.get('data'), dict) or not isinstance(name, str):
            return False
        entry = dict(value['data'], principal=owner)
        roles = entry.get('roles')
        return (CM.AC.active_member(entry, self.clock())[0] and entry.get('principal_type') == 'person'
                and isinstance(roles, list) and PROJECT_OWNER_ROLE in roles
                and CM.scope_covers(entry.get('scope'), [name]))

    @staticmethod
    def _identity(label, value):
        if isinstance(value, list):
            members = [(m['id'], m['version'], m['digest']) for m in value]
            return {'members': members, 'digest': SN.digest(SN.canonical(members))}
        return {'id': value['id'], 'version': value['version'], 'digest': value['digest'],
                'definition': _definition(label, (value.get('value') or {}).get('data'))}

    def _stale(self, ticket, accepted):
        """Every consumed input of the ticket compared by version and digest with the current read."""
        codes = []
        before = (ticket or {}).get('inputs') or {}
        for label in sorted(set(before) | set(accepted)):
            if label in OUTPUT_LABELS:
                continue
            old, new = before.get(label), accepted.get(label)
            if label in LIFECYCLE_FIELDS and old and new:
                if old.get('definition') != new.get('definition'):
                    codes.append('stale_input:' + label)
            elif old != new:
                codes.append('stale_input:' + label)
        return codes

    # -- decisions -------------------------------------------------------------------------------

    def decide(self, station, unit, *, context=None, ticket=None):
        """{eligible, refusals, inputs, pending, ...}: the named decision of one station for one unit.
        A ticket (an earlier station's decision) makes every changed consumed input a refusal."""
        decision = {'schema': SCHEMA, 'decision_id': str(uuid.uuid4()), 'station': station, 'unit': unit,
                    'domain_uuid': self.domain_uuid, 'repository_uuid': self.repository_uuid,
                    'follows': (ticket or {}).get('decision_id'), 'inputs': {}, 'watermark': None,
                    'pending': [], 'refusals': []}
        try:
            if station not in STATION_PREDICATES or not isinstance(unit, str) or not unit:
                raise Refused('invalid_input', 'unknown station or unit')
            if ticket is not None and (ticket.get('unit') != unit or ticket.get('domain_uuid') != self.domain_uuid):
                raise Refused('invalid_input', 'ticket names another unit or domain')
            inputs, watermark = self.read(unit)
            decision['watermark'] = watermark
            decision['inputs'] = {label: self._identity(label, value) for label, value in inputs.items()}
            refusals = self._unit_problems(unit, inputs)
            if not refusals:
                for name in STATION_PREDICATES[station]:
                    if name == ARCHITECTURE_PREDICATE:
                        decision['architecture'] = self.architecture(inputs.get('architecture'))
                        refusals.extend(decision['architecture']['refusals'])
                        continue
                    refusals.extend(self._predicate(name, unit, inputs, context))
                    if name in TRANSACTIONAL:
                        decision['pending'].append(name)
            if ticket is not None:
                refusals = self._stale(ticket, decision['inputs']) + refusals
            decision['refusals'] = list(dict.fromkeys(refusals))
        except Refused as error:
            decision['refusals'] = [error.code]
        except (SN.Refused, self.store.StoreRefused) as error:
            decision['refusals'] = [self.refusal_code(error)]
        except sqlite3.Error:
            decision['refusals'] = ['unavailable_service:store']
        except Stopped:
            raise  # a named stop is the caller's, never a unit hold
        except Exception as error:  # noqa: BLE001 - VELDO-0054: an unexpected fault is named, never raised
            decision['refusals'] = [unexpected(error)]
        decision['eligible'] = not decision['refusals']
        self._record(decision)
        return decision

    def require(self, station, unit, *, context=None, ticket=None):
        decision = self.decide(station, unit, context=context, ticket=ticket)
        if not decision['eligible']:
            raise Refused(decision['refusals'][0], '; '.join(decision['refusals']), decision)
        return decision

    def _record(self, decision):
        outcome = 'accepted' if decision['eligible'] else 'refused'
        self.counts[outcome] += 1
        event = {'schema': SCHEMA, 'operation': decision['station'], 'domain_uuid': self.domain_uuid,
                 'repository_uuid': self.repository_uuid, 'unit': decision['unit'],
                 'decision_id': decision['decision_id'], 'follows': decision['follows'],
                 'watermark': decision['watermark'],
                 'accepted_inputs': {k: v.get('version', v.get('digest')) for k, v in decision['inputs'].items()},
                 'outcome': outcome, 'refusals': list(decision['refusals']),
                 'taxonomy': sorted({taxonomy(c) for c in decision['refusals']})}
        if decision.get('architecture'):
            found = decision['architecture']
            event['architecture'] = {'basis': found['basis'], 'kind': found['kind'],
                                     'artifact_digest': (found['artifact'] or {}).get('digest'),
                                     'validator': {module: f['digest'] for module, f in found['validator'].items()}}
            if found.get('error'):
                # The durable stop event names the error that stopped the validator (ImportError for a miss).
                event['architecture']['error'] = found['error']
        self.observations.append(event)
        self.last[decision['unit']] = outcome
        self.observe(event)

    # -- architecture (VELDO-0053) -----------------------------------------------------------------

    def _architecture_validator(self):
        """The installed validator beside this module, loaded once per Gate (ValidatorSnapshot)."""
        if self._validator is None:
            self._validator = ValidatorSnapshot()
        return self._validator

    def architecture(self, item):
        """The architecture answer of one decision: {basis, kind, state, required, accepted, artifact,
        validator, refusals}. `item` is the store's architecture:<repository> entity (version 0 when
        the authority has accepted none)."""
        record = self._data(item) if item else None
        accepted = None
        if item and item.get('version'):
            accepted = {'id': item['id'], 'version': item['version'],
                        'digest': record.get('digest') if isinstance(record, dict) else None}
        found = {'basis': 'accepted' if accepted else 'policy', 'kind': None, 'state': None, 'required': None,
                 'accepted': accepted, 'artifact': None, 'validator': {}, 'refusals': []}
        if accepted and AR.record_problems(item['id'], (item.get('value') or {}).get('kind'), record):
            # Exactly the schema-valid records are an acceptance (VELDO-0134); any other shape is none.
            found['refusals'] = ['missing_authority:architecture']
            return found
        if self.workspace is None:
            # No workspace, no file to judge: never a pass, whatever the store says (or does not say).
            found['basis'] = 'store_only'
            found['refusals'] = ['missing_evidence:architecture/workspace']
            return found
        try:
            snapshot = self._architecture_validator()
            load, parsed = snapshot.contract(self.workspace, True if accepted else None)
            found['validator'] = {module: dict(entry) for module, entry in snapshot.identity.items()}
        except Exception as error:  # noqa: BLE001 - a validator that cannot answer refuses, never passes
            found['refusals'] = ['unavailable_service:architecture_validator']
            found['error'] = type(error).__name__
            return found
        found.update(kind=load.kind, state=load.state, required=load.required,
                     artifact=_artifact_identity(load.path, parsed))
        if load.refused:
            found['refusals'] = [ARCHITECTURE_REFUSALS.get(load.kind, 'invalid_input:architecture/' + load.kind)]
            found['problems'] = list(load.problems)
        elif accepted and parsed != accepted['digest']:
            found['kind'] = 'unaccepted_artifact'
            found['refusals'] = [ARCHITECTURE_REFUSALS['unaccepted_artifact']]
        return found

    def status(self):
        """Metrics: accepted and refused decisions, and the units whose latest decision refused."""
        return dict(self.counts, pending=sorted(u for u, o in self.last.items() if o == 'refused'),
                    decisions=dict(self.decision_counts,
                                   blocked=sorted(u for u, o in self.decision_last.items() if o == 'refused'),
                                   invalid_records=sorted(self.invalid_records)))


# ---------------------------------------------------------------------------------------------
# Every build and review subscription CLI invocation: eligibility, then reservation, then launch.
# ---------------------------------------------------------------------------------------------

CALL_STATIONS = ('build', 'review')


def _reservation_refusal(error):
    """A reservation service refusal as a named Refused, or None when `error` carries no name (an
    unnamed failure is re-raised by the caller: its outcome is unknown, never a refusal)."""
    code = getattr(error, 'code', None)
    if not isinstance(code, str) or not code:
        return None
    return Refused(code if ':' in code or code in TAXONOMY else 'usage_refused:' + code)


class StationCalls:
    """The runner's side of every station dispatch (VELDO-0036's trusted runner seam). It opens the
    dispatch, reserving that dispatch's worker slot, and hands out one CallHandle per station
    dispatch. `guards` maps each registered adapter (control_reservation_runtime.ADAPTERS) to its
    InvocationGuard over ONE real reservation service; `account` is the subscription account this
    runner's calls are made under; `clock` is the runner's time source for reservation commands."""

    def __init__(self, gate, guards, *, account=None, clock=None):
        self.gate, self.guards = gate, dict(guards)
        self.account = account
        self.clock = clock or time.time
        self.observations = collections.deque(maxlen=OBSERVATION_LIMIT)

    def _reservations(self):
        services = {id(g.reservations): g.reservations for g in self.guards.values()}
        if len(services) != 1:
            raise Refused('unavailable_service:reservations', 'the guards do not share one reservation service')
        return next(iter(services.values()))

    def open_dispatch(self, unit, *, context=None):
        """THE DISPATCH IDENTITY: reserve one worker slot (control_reservations.reserve_worker) for
        this station dispatch of `unit`, under this runner's account and the unit's ACCEPTED project,
        and return its identity. Every CallHandle of that dispatch reserves its calls against it, so
        the work loop's own unit (which carries no identity, and must not choose one) can reach a
        subscription CLI. Callers open a dispatch through launch(), which closes it when the launch
        returns; until close_dispatch retires it the slot counts, which is the conservative direction."""
        event = {'operation': 'open_dispatch', 'unit': unit, 'holder': (context or {}).get('holder')}
        try:
            if not isinstance(self.account, str) or not self.account.strip():
                raise Refused('reservation_required:account', 'this runner names no subscription account')
            project = (self.gate.unit_record(unit) or {}).get('project')
            if not isinstance(project, str) or not project.strip():
                raise Refused('missing_authority:project', 'the unit has no accepted project')
            dispatch = 'dispatch/%s/%s' % (unit, uuid.uuid4().hex)
            try:
                self._reservations().reserve_worker('worker/' + dispatch, dispatch, self.account, project, unit,
                                                    now=self.clock())
            except Refused:
                raise
            except Exception as error:
                named = _reservation_refusal(error)
                if named is None:
                    raise
                raise named from error
        except Refused as error:
            self.observations.append(dict(event, outcome='refused', refusal=error.code))
            raise
        self.observations.append(dict(event, outcome='reserved', dispatch=dispatch))
        return dispatch

    def handle(self, station, unit, dispatch, *, context, ticket):
        if station not in CALL_STATIONS:
            raise Refused('invalid_input', 'subscription calls belong to build and review stations')
        return CallHandle(self, station, unit, dispatch, dict(context or {}), ticket)

    @contextlib.contextmanager
    def launch(self, station, unit, *, context, ticket):
        """THE SCOPE OF ONE STATION LAUNCH. Entered only after every pre-launch decision of the caller
        passed: it opens the dispatch (one worker slot) and yields the station's CallHandle. When the
        launched call returns, normally or by any exception, the dispatch is closed at once
        (close_dispatch). A reservation refusal at the open is raised before anything is held."""
        if station not in CALL_STATIONS:
            raise Refused('invalid_input', 'subscription calls belong to build and review stations')
        dispatch = self.open_dispatch(unit, context=context)
        handle = CallHandle(self, station, unit, dispatch, dict(context or {}), ticket)
        try:
            yield handle
        except BaseException as error:
            try:
                self.close_dispatch(dispatch, 'failed' if isinstance(error, Refused) else 'unknown')
            except Exception as closing:  # noqa: BLE001 - the launch's own error is the one raised
                self.observations.append({'operation': 'close_dispatch', 'dispatch': dispatch,
                                          'outcome': 'unknown_outcome', 'error': type(closing).__name__})
            raise
        self.close_dispatch(dispatch, 'completed')

    def close_dispatch(self, dispatch, outcome):
        """The launch this dispatch was opened for has returned: retain its calls' exposure and retire
        its worker slot. Every call of the dispatch with no final usage report is settled by one final
        report carrying NO usage, which leaves it UNKNOWN (VELDO-0036 AC3/AC4: its reserved invocation
        and wall time stay charged and its unknown units stay unknown, so later calls under a token or
        message ceiling still refuse by name). The slot is then retired with the runner's lifecycle
        observation: the launching call returned in this process, so the worker it was opened for has
        ended. VELDO-0040/0041's supervisor owns this observation once it exists. A named refusal
        leaves the slot held (the conservative direction) and is returned and recorded, never raised."""
        event = {'operation': 'close_dispatch', 'dispatch': dispatch, 'launch_outcome': outcome}
        service = self._reservations()
        mine = [r for r in service._records().values() if r['type'] == 'invocation'
                and r['context']['domain'] == service.domain and r['dispatch'] == dispatch]
        observation = {'terminated': True, 'cleaned': True, 'outcome': outcome, 'observer': 'runner',
                       'basis': 'launch_returned' if mine else 'no_call_launched', 'calls': len(mine)}
        try:
            for call in mine:
                if call['state'] == 'pending':
                    sequence = call['sequence'] + 1
                    service.report('close/%s/%d' % (call['invocation'], sequence), call['invocation'], sequence, {},
                                   final=True, now=self.clock())
            service.retire('retire/' + dispatch, dispatch, lambda _: dict(observation), now=self.clock())
        except Exception as error:
            named = _reservation_refusal(error)
            if named is None:
                raise
            self.observations.append(dict(event, outcome='refused', refusal=named.code))
            return dict(event, outcome='refused', refusal=named.code)
        self.observations.append(dict(event, outcome='retired', calls=len(mine)))
        return dict(event, outcome='retired', calls=len(mine))


class CallHandle:
    """The only path a station's builder or reviewer has to a subscription CLI. Every boundary,
    initial, retry and follow-on, is decided and reserved before its launch."""

    def __init__(self, calls, station, unit, dispatch, context, ticket):
        self.calls, self.station, self.unit, self.dispatch = calls, station, unit, dispatch
        self.context, self.ticket = context, ticket

    def invoke(self, adapter, boundary, invocation, wall_seconds, configuration, *, now, command_id=None):
        event = {'station': self.station, 'unit': self.unit, 'adapter': adapter, 'boundary': boundary,
                 'invocation': invocation}
        try:
            guard = self.calls.guards.get(adapter)
            if guard is None:
                raise Refused('unavailable_service:adapter', str(adapter))
            if not isinstance(self.dispatch, str) or not self.dispatch:
                raise Refused('reservation_required:dispatch', 'no dispatch was opened for this station')
            decision = self.calls.gate.require('provider_request', self.unit, context=self.context, ticket=self.ticket)
            event['decision_id'] = decision['decision_id']
            try:
                receipt = guard.invoke(command_id or 'call/' + invocation, self.dispatch, invocation, boundary,
                                       wall_seconds, configuration, now=now)
            except Refused:
                raise
            except Exception as error:
                named = _reservation_refusal(error)
                if named is None:
                    raise  # a launch failure after its reservation: outcome unknown, exposure retained
                raise named from error
        except Refused as error:
            self.calls.observations.append(dict(event, outcome='refused', refusal=error.code))
            raise
        self.calls.observations.append(dict(event, outcome='launched' if not receipt.get('replayed') else 'replayed',
                                            watermark=receipt.get('seq')))
        return receipt
