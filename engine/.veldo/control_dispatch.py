"""Durable dispatch records: the complete contract before any worker, launch results under the
original dispatch, and every later observation bound to its own dispatch (PLAN-0019 W24,
VELDO-0039, R31, R33).

WHAT THIS MODULE IS. The dispatch authority's side of a launch: one registered store command,
`dispatch_transition`, committed through control_store's signed journal on the caller's own
connection (registered on that handle, never in the process-wide catalog), and the Dispatches
service that builds its commands. A dispatch record (kind `dispatch`, id `dispatch:<dispatch id>`)
holds the complete CONTRACT the runner prepared before anything was invoked: the source (commit and
tree), the input (the station decision's consumed inputs, its context and the task payload), the
capability (the adapter and the exact configured MCP servers and tools, passed on unchanged), the
reservation (VELDO-0036's worker slot of this same dispatch identity, by version and digest), the
claim (VELDO-0031 holder and generation), the deadline and the authority generation, with the
contract's digest.

THE DISPATCH IDENTITY is the one VELDO-0036's worker slot and VELDO-0028's effect contracts already
use: the `dispatch_id` string (control_eligibility.StationCalls.open_dispatch makes it as
`dispatch/<unit>/<hex>`). The record is keyed by it, the worker slot it binds must be the slot
reserved under it (control_reservations.entity('worker', [domain, dispatch_id])), and every later
observation addresses it. No transition here makes a second identity for the same attempt.

ONE ACTIVE DISPATCH PER UNIT AND STATION. An index entity (kind `dispatch_active`) per domain,
repository, unit and station names the dispatch holding it. Preparation reads and rewrites it in
the transaction that creates the record, with its version expected, so a second preparation is
refused by name (active_dispatch) or, when two race, as a stale version. Only a CONCLUSIVE end
frees it: exited (the receiver reaped the worker) or refused (nothing ran). An UNKNOWN outcome keeps
it: an ambiguous launch is a stopped original dispatch, never permission to prepare another (R33).

THE SCHEMA. STATES and TRANSITIONS are the ordinary lifecycle, and the suite derives its matrix from
them. `prepare` creates `prepared`; the receiver's acceptance (`accept`, its durable launch record,
committed before it spawns anything) makes `accepted`; `run` records the spawned process's OS
identity (`running`); `exit` records the reaped worker's termination (`exited`); `refuse` ends a
dispatch that conclusively did not launch (`refused`); `unknown` stops one whose launch or outcome
cannot be established (`unknown`, with a stop owed). Nothing else moves a record.

BINDING. Every observation after preparation names its dispatch AND carries that dispatch's
contract digest; `exit` also carries the process identity `run` recorded. An observation whose
binding differs from the record it addresses is refused (binding_mismatch:<field>) and changes
nothing, so one worker's result cannot move another dispatch. A termination records the exit
status and the digest and size of what the worker printed. Nothing the worker printed is copied or
interpreted, and no transition here writes a completion receipt: a worker's exit is not a completion
(VELDO-0021's receipts and VELDO-0052's reader own completion).

AUTHORITY. Every transition runs inside the store transaction and first requires the command's
principal to be an active `service` member (authority_contract.BOUNDARIES['dispatch_acceptance'])
whose scope covers this repository, so a worker principal writes no dispatch record. The claim and
reservation a contract binds are re-read in the same transaction at preparation and at acceptance.

OBSERVABILITY. Each command is reported to `observe` with operation, domain, repository, unit,
station, dispatch, request, accepted versions, outcome, named refusal and its taxonomy (invalid
input, missing authority, stale subject, unavailable service, missing evidence, unknown outcome;
unknown is never success). status() counts accepted and refused commands and lists pending and
stopped dispatches.

WHAT IT IS NOT. It launches nothing (control_launch holds the runner and the receiver) and
implements no recovery, replication, retry authorization or re-dispatch after an unknown outcome
(Release 2). Standard library only.
"""
import copy
import importlib.util
import json
import math
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('dispatch_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _organ('control_store')
CM = _organ('control_membership')
AC = CM.AC
CLM = _organ('control_claim')
RES = _organ('control_reservations')

SCHEMA = 'veldo.dispatch/v1'
OPERATION = 'dispatch_transition'
RECORD_KIND = 'dispatch'
INDEX_KIND = 'dispatch_active'
# The stations that launch a worker (control_eligibility.CALL_STATIONS), and those whose contract
# binds the builder's claim (VELDO-0021: build requires claim_current, review does not).
STATIONS = ('build', 'review')
CLAIMED_STATIONS = ('build',)

STATES = ('prepared', 'accepted', 'running', 'exited', 'refused', 'unknown')
# action: (the states it may move a record from, the state it moves it to). `prepare` moves from no
# record at all. This table IS the ordinary lifecycle; nothing outside it moves a record.
TRANSITIONS = {
    'prepare': ((), 'prepared'),
    'accept': (('prepared',), 'accepted'),
    'run': (('accepted',), 'running'),
    'exit': (('running',), 'exited'),
    'refuse': (('prepared', 'accepted'), 'refused'),
    'unknown': (('accepted', 'running'), 'unknown'),
}
# States that hold their unit and station. An unknown outcome holds it: never a new dispatch.
HOLDING = ('prepared', 'accepted', 'running', 'unknown')
STOP = 'dispatch-outcome-unknown'

CONTRACT_FIELDS = ('schema', 'dispatch_id', 'domain', 'repository', 'unit', 'station', 'attempt', 'source',
                   'input', 'capability', 'reservation', 'claim', 'deadline', 'authority_generation')
IDENTITY_FIELDS = ('platform', 'host', 'boot_id', 'pid', 'start')
TERMINATION_FIELDS = ('returncode', 'signal', 'output_digest', 'output_bytes', 'deadline_stop')

TAXONOMY = {
    'invalid_input': 'invalid_input', 'incomplete_contract': 'invalid_input', 'binding_mismatch': 'invalid_input',
    'duplicate_dispatch': 'invalid_input', 'missing_dispatch': 'invalid_input', 'unregistered_adapter': 'invalid_input',
    'command_content_conflict': 'invalid_input', 'malformed_command': 'invalid_input',
    'missing_authority': 'missing_authority', 'missing_reservation': 'missing_authority',
    'reservation_retired': 'missing_authority', 'not_authorized': 'missing_authority', 'draft_plan': 'missing_authority',
    'unresolved_decision': 'missing_authority', 'blocked': 'missing_authority',
    'reservation_mismatch': 'stale_subject', 'stale_claim': 'stale_subject', 'active_dispatch': 'stale_subject',
    'transition_refused': 'stale_subject', 'deadline_passed': 'stale_subject', 'stale_attempt': 'stale_subject',
    'stale_version': 'stale_subject', 'stale_input': 'stale_subject', 'stale_scope': 'stale_subject',
    'not_prepared': 'stale_subject', 'stale_authority': 'stale_subject',
    'unresolved_dependency': 'missing_evidence', 'missing_evidence': 'missing_evidence',
    'unavailable_service': 'unavailable_service', 'receiver_unavailable': 'unavailable_service',
    'spawn_failed': 'unavailable_service',
    'clock_uncertain': 'unknown_outcome', 'dispatch_outcome_unknown': 'unknown_outcome',
    'launch_evidence_missing': 'unknown_outcome', 'outcome_unknown': 'unknown_outcome',
    'process_identity_unreadable': 'unknown_outcome',
}


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


class Refused(Exception):
    """A named refusal of one dispatch transition; nothing was written."""

    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def record_id(dispatch_id):
    return 'dispatch:' + dispatch_id


def index_id(domain, repository, unit, station):
    return 'dispatch-active:' + json.dumps([domain, repository, unit, station], separators=(',', ':'))


def digest(value):
    return S.digest_of(value)


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _count(value, minimum=1):
    return type(value) is int and value >= minimum


def _hex(value):
    return isinstance(value, str) and len(value) in (40, 64) and set(value) <= set('0123456789abcdef')


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def contract_problems(contract):
    """The fields of a dispatch contract that are missing or malformed, by name. A contract is
    complete only when every binding is present and each digest it carries recomputes."""
    if not isinstance(contract, dict):
        return ['contract']
    missing = [f for f in CONTRACT_FIELDS if f not in contract]
    if missing:
        return missing
    problems = ['unexpected:' + f for f in sorted(set(contract) - set(CONTRACT_FIELDS))]
    if contract['schema'] != SCHEMA:
        problems.append('schema')
    problems += [f for f in ('dispatch_id', 'domain', 'repository', 'unit') if not _text(contract[f])]
    if contract['station'] not in STATIONS:
        problems.append('station')
    if not _count(contract['attempt']):
        problems.append('attempt')
    source = contract['source']
    if not isinstance(source, dict) or not _hex(source.get('commit')) or not _hex(source.get('tree')):
        problems.append('source')
    given = contract['input']
    decision = given.get('decision') if isinstance(given, dict) else None
    if (not isinstance(decision, dict) or not _text(decision.get('decision_id'))
            or decision.get('station') != contract['station'] or decision.get('unit') != contract['unit']
            or not isinstance(decision.get('inputs'), dict) or not decision['inputs']
            or not isinstance(given.get('context'), dict) or not isinstance(given.get('payload'), dict)
            or given.get('payload_digest') != digest(given.get('payload'))):
        problems.append('input')
    capability = contract['capability']
    if (not isinstance(capability, dict) or not _text(capability.get('adapter'))
            or not isinstance(capability.get('configuration'), dict)
            or capability.get('configuration_digest') != digest(capability.get('configuration'))):
        problems.append('capability')
    reservation = contract['reservation']
    if (not isinstance(reservation, dict) or not _text(contract['dispatch_id']) or not _text(contract['domain'])
            or reservation.get('entity') != RES.entity('worker', [contract['domain'], contract['dispatch_id']])
            or not _count(reservation.get('version')) or not _text(reservation.get('digest'))
            or not _text(reservation.get('account')) or not _text(reservation.get('project'))):
        problems.append('reservation')
    claim = contract['claim']
    if claim is None:
        if contract['station'] in CLAIMED_STATIONS:
            problems.append('claim')
    elif (not isinstance(claim, dict) or not _text(contract['repository']) or not _text(contract['unit'])
            or claim.get('entity') != CLM.claim_id(contract['repository'], contract['unit'])
            or not _text(claim.get('holder')) or not _count(claim.get('generation'))):
        problems.append('claim')
    if not _number(contract['deadline']):
        problems.append('deadline')
    if not _count(contract['authority_generation']):
        problems.append('authority_generation')
    return problems


def _identity_problems(value, extra=()):
    if not isinstance(value, dict) or set(value) != set(IDENTITY_FIELDS + tuple(extra)):
        return True
    return (not all(_text(value[f]) for f in ('platform', 'host', 'boot_id', 'start') + tuple(extra))
            or not _count(value['pid']))


def _termination_problems(value):
    if not isinstance(value, dict) or set(value) != set(TERMINATION_FIELDS):
        return True
    return (not (value['returncode'] is None or type(value['returncode']) is int)
            or not (value['signal'] is None or type(value['signal']) is int)
            or not (isinstance(value['output_digest'], str) and value['output_digest'].startswith('sha256:'))
            or not _count(value['output_bytes'], 0) or type(value['deadline_stop']) is not bool)


def _entity(conn, identity):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    if row is None:
        return None
    return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}


def _authorize(conn, principal, repository, now):
    """Current authorization at the dispatch boundary, read inside the command's transaction."""
    row = _entity(conn, principal) if _text(principal) else None
    entry = dict(row['data'], principal=principal) if row and row['kind'] == 'membership' else None
    active, why = AC.active_member(entry, now)
    if (not active or entry.get('principal_type') not in AC.BOUNDARIES['dispatch_acceptance']
            or not CM.scope_covers(entry.get('scope'), repository)):
        raise Refused('missing_authority', why or 'not an active service member for this repository')


def _reservation_bound(conn, contract):
    """The worker slot the contract binds: reserved under this dispatch identity, held, unchanged."""
    binding = contract['reservation']
    slot = _entity(conn, binding['entity'])
    if not slot or slot['kind'] != 'subscription_reservation' or slot['data'].get('type') != 'worker':
        raise Refused('missing_reservation', binding['entity'])
    data = slot['data']
    context = data.get('context') or {}
    if (data.get('dispatch') != contract['dispatch_id'] or context.get('domain') != contract['domain']
            or context.get('repository') != contract['repository'] or context.get('unit') != contract['unit']
            or context.get('account') != binding['account'] or context.get('project') != binding['project']):
        raise Refused('reservation_mismatch:context', binding['entity'])
    if data.get('retired'):
        raise Refused('reservation_retired', binding['entity'])
    if slot['version'] != binding['version'] or slot['digest'] != binding['digest']:
        raise Refused('reservation_mismatch:version', binding['entity'])


def _claim_bound(conn, contract):
    """The claim the contract binds: still owned by its holder at its generation (VELDO-0031)."""
    binding = contract['claim']
    if binding is None:
        return
    unit = _entity(conn, contract['unit']) or {}
    backlog_id = (unit.get('data') or {}).get('backlog_item_uuid')
    backlog = (_entity(conn, backlog_id) if _text(backlog_id) else None) or {}
    claim = _entity(conn, binding['entity']) or {}
    data = claim.get('data') or {}
    status = CLM.ownership(data, unit.get('data') or {}, backlog.get('data') or {})
    if status == 'unanswerable':
        raise Refused('clock_uncertain', binding['entity'])
    if status != 'owned' or data.get('holder') != binding['holder']:
        raise Refused('missing_authority:claim', binding['entity'])
    if data.get('generation') != binding['generation']:
        raise Refused('stale_claim', binding['entity'])


def transition(conn, params, before):
    """THE ONE TRANSITION every dispatch command commits, inside its store transaction."""
    action, now = params.get('action'), params.get('now')
    if action not in TRANSITIONS or not _number(now) or not _text(params.get('dispatch_id')):
        raise Refused('invalid_input', 'unknown action, time or dispatch')
    _authorize(conn, params.get('principal'), params.get('repository'), now)
    rid = record_id(params['dispatch_id'])
    current = before.get(rid)
    history = {'action': action, 'at': now, 'principal': params['principal']}
    if action == 'prepare':
        if current:
            raise Refused('duplicate_dispatch', rid)
        contract = params.get('contract')
        problems = contract_problems(contract)
        if problems:
            raise Refused('incomplete_contract:' + ','.join(problems))
        if (contract['dispatch_id'] != params['dispatch_id'] or contract['domain'] != params['domain']
                or contract['repository'] != params['repository']):
            raise Refused('binding_mismatch:coordinates')
        iid = index_id(contract['domain'], contract['repository'], contract['unit'], contract['station'])
        index = (before.get(iid) or {}).get('data') or {}
        holder = index.get('dispatch_id')
        if holder:
            held = _entity(conn, record_id(holder))
            state = (held or {}).get('data', {}).get('state')
            if state in HOLDING:
                # An unknown outcome is named as such: a stopped original dispatch, not a free slot.
                raise Refused(('dispatch_outcome_unknown:' if state == 'unknown' else 'active_dispatch:') + holder,
                              'one active dispatch per unit and station')
        if contract['attempt'] != index.get('attempts', 0) + 1:
            raise Refused('stale_attempt', 'attempt %r follows %r' % (contract['attempt'], index.get('attempts', 0)))
        if now >= contract['deadline']:
            raise Refused('deadline_passed')
        _reservation_bound(conn, contract)
        _claim_bound(conn, contract)
        record = {'schema': SCHEMA, 'dispatch_id': params['dispatch_id'], 'state': 'prepared',
                  'contract': contract, 'contract_digest': digest(contract), 'receiver': None, 'process': None,
                  'termination': None, 'refusal': None, 'stop': None, 'reason': None,
                  'history': [dict(history, state='prepared')]}
        slot = {'domain': contract['domain'], 'repository': contract['repository'], 'unit': contract['unit'],
                'station': contract['station'], 'dispatch_id': params['dispatch_id'], 'attempts': contract['attempt']}
        return {rid: {'kind': RECORD_KIND, 'data': record}, iid: {'kind': INDEX_KIND, 'data': slot}}
    if not current or current['kind'] != RECORD_KIND:
        raise Refused('missing_dispatch', rid)
    record = copy.deepcopy(current['data'])
    allowed, target = TRANSITIONS[action]
    if record['state'] not in allowed or params.get('expected_state') not in (None, record['state']):
        # An observation that names the state it ends is refused once the record has moved on.
        raise Refused('transition_refused:%s:%s' % (record['state'], action))
    if params.get('contract_digest') != record['contract_digest']:
        raise Refused('binding_mismatch:contract_digest', 'this observation belongs to another dispatch')
    contract = record['contract']
    if action == 'accept':
        if now >= contract['deadline']:
            raise Refused('deadline_passed')
        _reservation_bound(conn, contract)
        _claim_bound(conn, contract)
        if _identity_problems(params.get('receiver'), ('principal',)) or params['receiver']['principal'] != params['principal']:
            raise Refused('invalid_input', 'the receiver names its own process identity and principal')
        record['receiver'] = params['receiver']
    elif action == 'run':
        if _identity_problems(params.get('process')):
            raise Refused('invalid_input', 'a running observation carries the OS process identity')
        record['process'] = params['process']
    elif action == 'exit':
        if params.get('process') != record['process']:
            raise Refused('binding_mismatch:process', 'this termination belongs to another process')
        if _termination_problems(params.get('termination')):
            raise Refused('invalid_input', 'a termination carries exit status and output digest only')
        record['termination'] = params['termination']
    elif action == 'refuse':
        if not _text(params.get('refusal')):
            raise Refused('invalid_input', 'a refusal is named')
        record['refusal'] = params['refusal']
    elif action == 'unknown':
        if not _text(params.get('reason')):
            raise Refused('invalid_input', 'an unknown outcome names why')
        record['stop'], record['reason'] = STOP, params['reason']
    record['state'] = target
    record['history'].append(dict(history, state=target))
    changes = {rid: {'kind': RECORD_KIND, 'data': record}}
    if target not in HOLDING:
        # A conclusive end frees its unit and station for the next attempt.
        iid = index_id(contract['domain'], contract['repository'], contract['unit'], contract['station'])
        index = (before.get(iid) or {}).get('data') or {}
        if index.get('dispatch_id') == record['dispatch_id']:
            changes[iid] = {'kind': INDEX_KIND, 'data': dict(index, dispatch_id=None, released_by=target)}
    return changes


class Dispatches:
    """One domain and repository's dispatch records over a real control store connection. The
    principal is the service writing (the runner prepares; the launch receiver accepts, runs and
    exits); `sign(bytes) -> text` signs its journal records as `signer`."""

    def __init__(self, store, conn, *, domain, repository, principal, signer, sign, generation=1, observe=None):
        if not all(_text(v) for v in (domain, repository, principal, signer)):
            raise Refused('invalid_input', 'domain, repository, principal and signer are named')
        self.store, self.conn = store, conn
        self.domain, self.repository, self.principal = domain, repository, principal
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        self.counts = {'accepted': 0, 'refused': 0}
        conn.command_registry[OPERATION] = {'transaction_transition': transition,
                                            'writes': ('entities', 'journal', 'commands', 'nonces')}

    # Reads.

    def record(self, dispatch_id):
        """The stored record of one dispatch, or None."""
        entry = _entity(self.conn, record_id(dispatch_id)) if _text(dispatch_id) else None
        return entry['data'] if entry and entry['kind'] == RECORD_KIND else None

    def version(self, dispatch_id):
        entry = _entity(self.conn, record_id(dispatch_id))
        return entry['version'] if entry else 0

    def active(self, unit, station):
        """The record holding `unit` at `station`, or None when nothing holds it."""
        entry = _entity(self.conn, index_id(self.domain, self.repository, unit, station))
        holder = (entry or {}).get('data', {}).get('dispatch_id')
        record = self.record(holder) if holder else None
        return record if record and record['state'] in HOLDING else None

    def receipt(self, dispatch_id, action):
        """The journal record digest of the committed `action` of this dispatch, or None: the
        store's own evidence that the transition committed (the acceptance a worker launches under)."""
        prefix = 'dispatch/%s/%s/' % (action, dispatch_id)
        row = self.conn.execute('SELECT record_digest FROM journal WHERE substr(command_id, 1, ?) = ? ORDER BY seq LIMIT 1',
                                (len(prefix), prefix)).fetchone()
        return row[0] if row else None

    def attempts(self, unit, station):
        entry = _entity(self.conn, index_id(self.domain, self.repository, unit, station))
        return (entry or {}).get('data', {}).get('attempts', 0)

    def status(self):
        """Metrics: accepted and refused commands, and the dispatches pending or stopped."""
        states = {}
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (RECORD_KIND,)):
            record = json.loads(data)
            contract = record.get('contract') or {}
            if contract.get('domain') == self.domain and contract.get('repository') == self.repository:
                states[record['dispatch_id']] = record['state']
        return dict(self.counts, pending=sorted(d for d, s in states.items() if s in ('prepared', 'accepted', 'running')),
                    stopped=sorted(d for d, s in states.items() if s == 'unknown'),
                    states={s: sum(v == s for v in states.values()) for s in STATES})

    # Commands.

    def _run(self, action, dispatch_id, fields, now, contract=None):
        if not _text(dispatch_id):
            raise Refused('invalid_input', 'a dispatch is named')
        current = contract or (self.record(dispatch_id) or {}).get('contract') or {}
        ids = [record_id(dispatch_id)]
        if all(_text(current.get(f)) for f in ('unit', 'station')):
            ids.append(index_id(self.domain, self.repository, current['unit'], current['station']))
        params = dict(fields, action=action, dispatch_id=dispatch_id, now=now, principal=self.principal,
                      domain=self.domain, repository=self.repository)
        # Idempotent by content: a delivery retry of the same observation replays its first result,
        # and a different observation is a new command the transition itself judges.
        command_id = 'dispatch/%s/%s/%s' % (action, dispatch_id, digest(params)[len('sha256:'):][:24])
        expected = {}
        for identity in ids:
            row = self.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            expected[identity] = row[0] if row else 0
        # A delivery retry of the same observation reuses the versions its first commit expected.
        prior = self.conn.execute('SELECT before_versions FROM journal WHERE command_id=?', (command_id,)).fetchone()
        if prior:
            expected = json.loads(prior[0])
        command = dict(command_id=command_id, principal=self.principal, operation=OPERATION, parameters=params,
                       expected_versions=expected, artifact_digests=[], nonce='dispatch/' + command_id)
        event = {'schema': SCHEMA, 'operation': action, 'domain': self.domain, 'repository': self.repository,
                 'unit': current.get('unit'), 'station': current.get('station'), 'dispatch_id': dispatch_id,
                 'request': command_id, 'accepted_versions': dict(expected)}
        try:
            result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            self.counts['refused'] += 1
            self.observe(dict(event, outcome='refused', refusal=error.code, taxonomy=taxonomy(error.code)))
            if isinstance(error, Refused):
                raise
            raise Refused(error.code, error.detail) from error
        self.counts['accepted'] += 1
        self.observe(dict(event, outcome='accepted', watermark=result['seq'], state=TRANSITIONS[action][1]))
        return self.record(dispatch_id)

    def prepare(self, contract, *, now):
        """Record the COMPLETE contract, the dispatch's first write and its unit/station's hold."""
        if not isinstance(contract, dict):
            raise Refused('incomplete_contract:contract')
        return self._run('prepare', contract.get('dispatch_id'), {'contract': contract}, now, contract=contract)

    def accept(self, dispatch_id, contract_digest, receiver, *, now):
        """The receiver's durable acceptance of this dispatch identity, before any spawn."""
        return self._run('accept', dispatch_id, {'contract_digest': contract_digest, 'receiver': receiver}, now)

    def run(self, dispatch_id, contract_digest, process, *, now):
        """The spawned worker's OS identity: the launch was accepted and the worker is running."""
        return self._run('run', dispatch_id, {'contract_digest': contract_digest, 'process': process}, now)

    def exit(self, dispatch_id, contract_digest, process, termination, *, now):
        """The reaped worker's termination, bound to the process `run` recorded."""
        return self._run('exit', dispatch_id, {'contract_digest': contract_digest, 'process': process,
                                               'termination': termination}, now)

    def refuse(self, dispatch_id, contract_digest, refusal, *, now, expected_state=None):
        """A launch that conclusively did not happen, by name, ending `expected_state` when named."""
        fields = {'contract_digest': contract_digest, 'refusal': refusal}
        if expected_state is not None:
            fields['expected_state'] = expected_state
        return self._run('refuse', dispatch_id, fields, now)

    def unknown(self, dispatch_id, contract_digest, reason, *, now, expected_state=None):
        """A launch or outcome that cannot be established: the dispatch stops with a stop owed."""
        fields = {'contract_digest': contract_digest, 'reason': reason}
        if expected_state is not None:
            fields['expected_state'] = expected_state
        return self._run('unknown', dispatch_id, fields, now)
