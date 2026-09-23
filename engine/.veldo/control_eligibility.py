"""Shared floor eligibility for every enabled station entry (PLAN-0019 W37, VELDO-0052, R52, R70).

WHAT THIS MODULE IS. The one eligibility service the floor's entries call: frontier selection, the
work loop's claim, plan run-check and the direct executor's build and review launches, the
dispatcher's build, review and publication, and every subscription CLI call a build or review makes. Each asks the same Gate for a
named decision over the accepted records in the real control store, with the predicates of ITS
station (completion_contract.ENTRY_PREDICATES, the shipped VELDO-0021 contract, plus current
admission everywhere under R52/R69). Review cannot bypass draft-plan, decision or dependency checks.

WHAT A DECISION CARRIES. The station, the unit, the store watermark, and the version and digest of
every input it consumed: the unit and its backlog item, governing plan, admission, project,
authority, claim, each dependency with its complete receipt collection, and the whole decision,
blocker and approval collections (a negative predicate reads a collection, never one record). A
later station passes the earlier decision back as its ticket and the Gate refuses by name
(stale_input:<label>) when any consumed input moved, while the project version stays fixed. Only
the claim's own lifecycle writes (claim record, unit and backlog state) are station OUTPUTS: they
are compared by their definition digest and claim ownership is re-decided fresh.

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
comes from the structural validator INSTALLED beside this module (validate.py and its loader, never
the copy a workspace carries) over the workspace's .veldo/architecture.yaml. The authority's record
architecture:<repository> (state accepted, digest of the accepted bytes) makes the contract required
whatever the workspace's policy says, and the workspace file must be exactly those bytes; with no
record the repository's policy flag decides absence, as VELDO-0016's loader always has. A present
contract that is unreadable, malformed, of the wrong type or structurally invalid refuses by name
(invalid_input:architecture/<kind>), a required one that is absent refuses
(missing_evidence:architecture/required_absence), and bytes the authority did not accept refuse
(missing_authority:architecture/unaccepted_artifact). Each decision records the artifact it judged and
the files of the code that judged it (path and digest).
"""
import collections
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
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
SN = _organ('control_snapshot')

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
    ('control_eligibility.py', 'Gate.completion'),
    ('control_eligibility.py', 'Gate._dependencies'),
)
# The reader's call names a consumer site is recognized by.
READER_CALLS = ('completion_status', 'completion', 'landed', '_landed_from')

# Labels whose record the claim transition itself rewrites (VELDO-0031). They are compared by their
# definition, the record minus these lifecycle fields; ownership is decided fresh at every station.
LIFECYCLE_FIELDS = {'unit': ('state',), 'backlog': ('state',)}
OUTPUT_LABELS = ('claim',)

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
}

OBSERVATION_LIMIT = 1000


def taxonomy(code):
    return TAXONOMY.get(code.split(':', 1)[0], 'unknown_outcome')


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
_errors = _sys.modules.setdefault('veldo_eligibility_errors', _types.ModuleType('veldo_eligibility_errors'))
for _name, _cls in (('Refused', Refused), ('Stopped', Stopped)):
    if not hasattr(_errors, _name):
        setattr(_errors, _name, _cls)
Refused, Stopped = _errors.Refused, _errors.Stopped


def _claims_a_repository(path):
    """Whether Git's own discovery from `path` would reach a repository: a `.git` entry, or a bare
    git directory, at `path` or at any ancestor on the same filesystem. git_process strips GIT_DIR and
    GIT_CEILING_DIRECTORIES, and discovery stops at a filesystem boundary, so this walk is exactly the
    set of places a failing Git could have been reading. Nothing is parsed from Git's own messages."""
    current = os.path.realpath(str(path))
    try:
        device = os.stat(current).st_dev
    except OSError:
        device = None
    while True:
        if os.path.lexists(os.path.join(current, '.git')) or all(
                os.path.exists(os.path.join(current, part)) for part in ('HEAD', 'objects', 'refs')):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        try:
            if device is not None and os.stat(parent).st_dev != device:
                return False
        except OSError:
            return True  # an ancestor that cannot be read cannot be ruled out
        current = parent


def enrolled(repo_root):
    """Whether this workspace carries an authority enrollment binding (VELDO-0029).

    Only a directory in which Git's discovery finds no repository at all is "not enrolled". A Git
    that fails where a repository IS present (a malformed config, an unreadable common directory, a
    timeout, no git executable) is the named stop enrollment_unanswerable: the binding lives inside
    that repository, so its absence cannot be concluded, and a silent 'not enrolled' there would let
    every enabled entry run pre-factory with no eligibility at all."""
    try:
        return os.path.lexists(E.binding_path(str(repo_root)))
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

    def __init__(self, host_identity, enrollment_signers):
        if not isinstance(host_identity, str) or not host_identity.strip() \
                or not isinstance(enrollment_signers, str) or not enrollment_signers.strip():
            raise Stopped('host_trust_unreadable')
        if not os.path.isabs(enrollment_signers):
            raise Stopped('host_trust_refused:signers_not_absolute')
        self.host_identity, self.enrollment_signers = host_identity, enrollment_signers

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
    return HostTrust(record.get('host_identity'), record.get('enrollment_signers'))


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
    store = _organ('control_store')
    try:
        conn = store.open_store(E.store_path_for(binding), mode='r')
    except (store.StoreRefused, sqlite3.Error, OSError) as error:
        raise Stopped('unavailable_service:store') from error
    return Gate(store, conn, domain_uuid=binding['domain_uuid'], repository_uuid=binding['repository_uuid'],
                authority_generation=binding['authority_generation'], observe=observe, workspace=workspace)


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


class ValidatorSnapshot:
    """The installed structural validator, loaded ONCE from ONE read of the installed engine's bytes
    (VELDO-0053, R50). The engine's modules are read once, written to a private directory only this
    process can reach, and executed from there, so the digests recorded are of the bytes that run: a
    later change on disk is neither run nor recorded by a decision of this snapshot. The structural
    validator (arch.py) is loaded once here and reused for every contract; the private copy is removed
    as soon as it is loaded."""

    def __init__(self, installed=None):
        installed = Path(installed or Path(__file__).resolve().parent)
        bodies = {path.name: path.read_bytes() for path in sorted(installed.glob('*.py'))}
        with tempfile.TemporaryDirectory(prefix='veldo-validator-') as private:
            engine = Path(private) / '.veldo'
            engine.mkdir()
            for name, body in bodies.items():
                (engine / name).write_bytes(body)
            spec = importlib.util.spec_from_file_location('eligibility_validator_snapshot', str(engine / 'validate.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.validate, self.arch = module, module.entry_validator()
        self.identity = {role: {'path': str(installed / name), 'digest': 'sha256:' + hashlib.sha256(bodies[name]).hexdigest()}
                         for role, name in VALIDATOR_ROLES}

    def contract(self, workspace, required):
        """The ContractLoad of the workspace's contract, through validate.py's public entry_contract."""
        return self.validate.entry_contract(workspace, required, arch=self.arch)


def _digest_file(path):
    with open(path, 'rb') as handle:
        return 'sha256:' + hashlib.sha256(handle.read()).hexdigest()


def _artifact_identity(path):
    """{path, type, digest} of the architecture artifact that was judged. Only a regular file is
    opened (a FIFO at the path is never read); a file the worker may not read has no digest."""
    kind = ('absent' if not os.path.lexists(path) else 'symlink' if os.path.islink(path)
            else 'directory' if os.path.isdir(path) else 'regular' if os.path.isfile(path) else 'other')
    digest = None
    if os.path.isfile(path):
        try:
            digest = _digest_file(path)
        except OSError:
            digest = None
    return {'path': str(path), 'type': kind, 'digest': digest}


class Gate:
    """One domain's shared eligibility over a real control store connection. Read-only."""

    def __init__(self, store, conn, *, domain_uuid, repository_uuid, authority_generation=1, observe=None,
                 workspace=None):
        self.store, self.conn = store, conn
        # The workspace whose architecture every decision judges (VELDO-0053). A store-only Gate (no
        # workspace) cannot look at a file, so its architecture predicate always refuses
        # (missing_evidence:architecture/workspace): the default argument is never a pass.
        self.workspace = str(workspace) if workspace is not None else None
        self._validator = None
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
        for item in receipts:
            r = self._data(item)
            if CC.fact_problems('revision_landed', r, subject):
                continue
            landing = r.get('publication_receipt')
            if isinstance(landing, dict) and not CC.landing_receipt_problems(landing) \
                    and landing.get('unit_id') == subject['id']:
                return True
        return False

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
        state['revision_landed'] = state['revision_landed'] and self._landed_from(receipts, subject)
        return state

    def landed(self, unit):
        return self.completion(unit)['revision_landed']

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

    def read(self, unit):
        """Every input a station decision over `unit` consumes, read in ONE read transaction."""
        with self._reading():
            inputs = {}
            u = self._entity(unit)
            inputs['unit'] = u
            data = self._data(u) or {}
            inputs['backlog'] = self._entity(data.get('backlog_item_uuid') or 'backlog:' + unit)
            inputs['plan'] = self._entity('plan:' + data['plan']) if data.get('plan') else None
            inputs['admission'] = self._entity('admission:' + unit)
            inputs['project'] = self._entity('project:' + str(data.get('project')))
            inputs['authority'] = self._entity('authority:' + self.domain_uuid)
            inputs['claim'] = self._entity(self.claims.claim_id(self.repository_uuid, unit))
            for dep in data.get('depends_on') or []:
                inputs['dependency/' + dep] = self._entity(dep)
                inputs['receipts/' + dep] = self._receipts(dep)
            inputs['decisions'] = self._collection('decision', lambda d: unit in (d.get('blocks') or []))
            inputs['blockers'] = self._collection('blocker', lambda d: d.get('unit') == unit)
            inputs['approvals'] = self._collection('approval', lambda d: d.get('unit') == unit)
            inputs['architecture'] = self._entity('architecture:' + self.repository_uuid)
            watermark = self.conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]
        return {k: v for k, v in inputs.items() if v is not None}, watermark

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
        if name == 'plan_not_draft':
            if not data.get('plan'):
                return []
            p = self._data(inputs.get('plan'))
            if not isinstance(p, dict):
                return ['missing_authority:plan']
            return [] if p.get('status') in ('ready', 'in_progress') else ['draft_plan']
        if name == 'decisions_settled':
            return ['unresolved_decision:' + d['id'] for d in inputs['decisions']
                    if unit in (self._data(d).get('blocks') or []) and self._data(d).get('state') != 'settled']
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
        if not isinstance(self._data(inputs.get('project')), dict):
            problems.append('missing_authority:project')
        return problems

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
            decision['refusals'] = [('missing_authority:' if 'digest' in error.code else 'invalid_input:') + error.code]
        except sqlite3.Error:
            decision['refusals'] = ['unavailable_service:store']
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
                                     'validator': {role: f['digest'] for role, f in found['validator'].items()}}
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
        if accepted and (not isinstance(record, dict) or record.get('state') != 'accepted'
                         or not isinstance(record.get('digest'), str) or not record['digest'].startswith('sha256:')):
            found['refusals'] = ['missing_authority:architecture']
            return found
        if self.workspace is None:
            # No workspace, no file to judge: never a pass, whatever the store says (or does not say).
            found['basis'] = 'store_only'
            found['refusals'] = ['missing_evidence:architecture/workspace']
            return found
        try:
            snapshot = self._architecture_validator()
            load = snapshot.contract(self.workspace, True if accepted else None)
            found['validator'] = {role: dict(entry) for role, entry in snapshot.identity.items()}
        except Exception as error:  # noqa: BLE001 - a validator that cannot answer refuses, never passes
            found['refusals'] = ['unavailable_service:architecture_validator']
            found['error'] = type(error).__name__
            return found
        found.update(kind=load.kind, state=load.state, required=load.required,
                     artifact=_artifact_identity(load.path))
        if load.refused:
            found['refusals'] = [ARCHITECTURE_REFUSALS.get(load.kind, 'invalid_input:architecture/' + load.kind)]
            found['problems'] = list(load.problems)
        elif accepted and found['artifact']['digest'] != accepted['digest']:
            found['kind'] = 'unaccepted_artifact'
            found['refusals'] = [ARCHITECTURE_REFUSALS['unaccepted_artifact']]
        return found

    def status(self):
        """Metrics: accepted and refused decisions, and the units whose latest decision refused."""
        return dict(self.counts, pending=sorted(u for u, o in self.last.items() if o == 'refused'))


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
