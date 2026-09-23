"""Shared floor eligibility for every enabled station entry (PLAN-0019 W37, VELDO-0052, R52, R70).

WHAT THIS MODULE IS. The one eligibility service the floor's entries call: frontier selection, the
work loop's claim, plan run-check and the direct executor, the dispatcher's build, review and
publication, and every subscription CLI call a build or review makes. Each asks the same Gate for a
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

ENABLEMENT. gate_for() is the one resolution every entry calls. An explicit Gate is used. A
repository enrolled with the authority (VELDO-0029 binding) and no Gate wired STOPS with
eligibility_required, exactly as claim.py stops with authority_required: an enabled floor entry
cannot run without eligibility. An unenrolled tree keeps the pre-factory behavior unchanged.

WHAT IT IS NOT. It writes nothing: only control_store commits, and the Gate reads inside one
deferred read transaction. It holds no key, launches nothing itself (StationCalls hands launches to
VELDO-0036's InvocationGuard, which reserves before launch), and implements no recovery, fencing or
clock qualification (Release 2). VELDO-0053's architecture checks and VELDO-0054's exact decision
consumption attach to the same registrations. Standard library only.
"""
import collections
import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
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
STATION_PREDICATES = {s: tuple(dict.fromkeys(('admission_current',) + tuple(CC.ENTRY_PREDICATES[s])))
                      for s in FLOOR_STATIONS}
# Predicates satisfied only by a store transaction at the call boundary, never by a read.
TRANSACTIONAL = {'charge_reserved': 'control_reservations.Reservations.reserve_call'}

# EVERY ENABLED FLOOR ENTRY, as (module, qualified function, station). The suite derives the same
# set from the actual call sites (a .decide/.require call naming a station) and requires equality.
REGISTRATIONS = (
    ('frontier.py', 'claimable._add', 'selection'),
    ('work.py', 'WorkLoop._claim_next', 'claim'),
    ('plan.py', 'cmd_run_check', 'direct_execution'),
    ('executor.py', 'Executor.run', 'direct_execution'),
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
    'enrollment_unanswerable': 'unavailable_service',
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


class Gate:
    """One domain's shared eligibility over a real control store connection. Read-only."""

    def __init__(self, store, conn, *, domain_uuid, repository_uuid, authority_generation=1, observe=None):
        self.store, self.conn = store, conn
        self.domain_uuid, self.repository_uuid = domain_uuid, repository_uuid
        self.authority_generation = authority_generation
        self.observe = observe or (lambda event: None)
        self.claims = _organ('control_claim')
        self.counts = {'accepted': 0, 'refused': 0}
        # Diagnostics only, bounded: the durable log is the observe callback's sink.
        self.observations = collections.deque(maxlen=OBSERVATION_LIMIT)
        self.last = {}

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
        self.observations.append(event)
        self.last[decision['unit']] = outcome
        self.observe(event)

    def status(self):
        """Metrics: accepted and refused decisions, and the units whose latest decision refused."""
        return dict(self.counts, pending=sorted(u for u, o in self.last.items() if o == 'refused'))


# ---------------------------------------------------------------------------------------------
# Every build and review subscription CLI invocation: eligibility, then reservation, then launch.
# ---------------------------------------------------------------------------------------------

CALL_STATIONS = ('build', 'review')


class StationCalls:
    """Hands out one CallHandle per station dispatch. `guards` maps each registered adapter
    (control_reservation_runtime.ADAPTERS) to its InvocationGuard over real reservations."""

    def __init__(self, gate, guards):
        self.gate, self.guards = gate, dict(guards)
        self.observations = collections.deque(maxlen=OBSERVATION_LIMIT)

    def handle(self, station, unit, dispatch, *, context, ticket):
        if station not in CALL_STATIONS:
            raise Refused('invalid_input', 'subscription calls belong to build and review stations')
        return CallHandle(self, station, unit, dispatch, dict(context or {}), ticket)


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
            decision = self.calls.gate.require('provider_request', self.unit, context=self.context, ticket=self.ticket)
            event['decision_id'] = decision['decision_id']
            try:
                receipt = guard.invoke(command_id or 'call/' + invocation, self.dispatch, invocation, boundary,
                                       wall_seconds, configuration, now=now)
            except Refused:
                raise
            except Exception as error:
                code = getattr(error, 'code', None)
                if not isinstance(code, str) or not code:
                    raise  # a launch failure after its reservation: outcome unknown, exposure retained
                raise Refused(code if ':' in code or code in TAXONOMY else 'usage_refused:' + code) from error
        except Refused as error:
            self.calls.observations.append(dict(event, outcome='refused', refusal=error.code))
            raise
        self.calls.observations.append(dict(event, outcome='launched' if not receipt.get('replayed') else 'replayed',
                                            watermark=receipt.get('seq')))
        return receipt
