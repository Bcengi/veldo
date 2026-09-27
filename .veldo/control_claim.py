"""Authority claim transitions and authenticated IPC-to-store receiver (VELDO-0031).

Only control_store writes. The accepted admission seam is an execution_unit entity
with state=READY, repository_uuid, backlog_item_uuid, requirements and eligible_holders;
its backlog_item is PRIORITIZED or ACTIVE (the existing entity lifecycle). Provisioning/admission belongs to other specs.
Release never rewinds activation. It retains the generation, so a later explicit
claim increments it. No stale or uncertain claim is automatically reclaimed.

Parking (VELDO-0064). A holder that stops for a person assignment gives its claim up through
`park`, the release transition that also records `parked_on`, the assignment the unit now waits
for. A parked unit is not claimable: `claim` refuses it as `parked` and inspection reports
`parked`. Only `resume`, naming the same assignment, takes it again, and it takes the same
eligibility, capability and activation checks as a claim. Neither `park` nor `resume` is an IPC
operation of the Receiver: the assignment inbox reaches them inside its own store transaction,
after that assignment's admission, so no holder resumes blocked work on its own word.

Clearing a park (VELDO-0133). When the person asked what becomes of parked work rules `backlog`,
the inbox's dispose command clears the park through `unpark`, naming the same assignment: the
claim stays released with no holder and loses `parked_on`, so the unit is claimable again by the
ordinary `claim` with its own eligibility, capability and activation checks. Like `park` and
`resume`, it is not an IPC operation of the Receiver.

Project lifecycle (VELDO-0076). Every claim of a unit is refused by name when the
shared eligibility Gate's own project check refuses it (project_not_active:PAUSED, :CANCELED,
:COMPLETED, :owner_not_current, :not_a_project, or missing_authority:project): a stopped project
takes no new assignment. The project and owner records that check read are pinned in the claim's
transaction. Renew, release and use of an existing claim are not new assignments; running work
follows the host stop policy.

The claim organ (VELDO-0169). Every claim record is decided by one function of this module,
`transition(conn, params, before)`, which every service calls inside its own store transaction
and which is itself a store transaction transition. For every transition that hands work
out (HANDOUTS: a claim, a resume, and the unpark of a disposition's backlog outcome) the organ asks
the shared eligibility Gate's project check (control_eligibility.Gate.project_problems) for the
unit, on the transaction's own connection while that transaction holds the write lock, and refuses
by the Gate's own name with nothing written when it finds any problem, before any other reason.
The store holds the same invariant in its commit path for every writer of a claim record
(control_store.handout_problem), whoever built the record; the organ's check refuses earlier, by
the same name. The callers ask the same check before they build the command, to name a refusal
early and to pin the records it read. Park, release, renew and use hand nothing out and are not
checked.

Receiver.apply plugs into control_client.Authority. Its inner command signature
identifies an active stored member independently of the transport credential.
Protected use records acceptance at this receiver; it is not a landing permit and
never substitutes for the lander's remaining publication predicates.
"""
import importlib.util
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('claims_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = organ('control_store')
CM = organ('control_membership')
AC = CM.AC
CL = organ('claim')
OPERATIONS = ('claim', 'renew', 'release', 'use', 'inspect')
# The record kind the claim organ decides (VELDO-0169).
KIND = 'claim'
# The transitions that hand work out (VELDO-0169): the organ asks the Gate's project check for each.
HANDOUTS = ('claim', 'resume', 'unpark')
# Rereads of one command whose pinned versions kept moving; past this the conflict is the answer.
ATTEMPTS = 16


def claim_id(repository, unit):
    return 'claim:' + repository + ':' + unit


def validate_alias(unit):
    problem = CL.unit_id_problem(unit)
    if problem:
        raise S.StoreRefused('invalid_input', problem)


ACTIVE_UNIT_STATES = ('CLAIMED', 'DISPATCHING', 'RUNNING', 'VERIFYING',
                      'REVIEWING', 'READY_TO_LAND', 'LANDING')


def ownership(data, unit, backlog, action='inspect'):
    """One consistency and liveness answer for reads and transactional operations."""
    if not data:
        return 'ownership_uncertain' if unit.get('state') in ACTIVE_UNIT_STATES else 'unowned'
    if data.get('state') == 'released':
        return 'parked' if data.get('parked_on') else 'unowned'
    if unit.get('state') not in ACTIVE_UNIT_STATES or backlog.get('state') != 'ACTIVE':
        return 'ownership_uncertain'
    if data.get('state') != 'owned' or not data.get('holder'):
        return 'ownership_uncertain'
    live = CL.liveness(data)
    if live == 'unanswerable':
        return 'unanswerable'
    if live == 'stale' and action in ('renew', 'release'):
        # Expiration denies use and takeover, but does not revoke the stored owner.
        # A malformed heartbeat remains uncertain rather than being treated as old.
        try:
            CL.datetime.strptime(data.get('heartbeat_at'), '%Y-%m-%dT%H:%M:%SZ')
        except (TypeError, ValueError):
            return 'ownership_uncertain'
        return 'owned'
    return 'owned' if live == 'live' else 'ownership_uncertain'


_ELIGIBILITY = []


def _project_gate(conn):
    """The shared eligibility Gate over `conn`, for its project check alone, which reads the unit, its
    project record and the owner's membership and no domain or repository coordinate. Kept on the
    connection it reads, so it lives exactly as long as that handle."""
    gate = getattr(conn, 'claim_project_gate', None)
    if gate is None or gate.conn is not conn:
        if not _ELIGIBILITY:
            _ELIGIBILITY.append(organ('control_eligibility'))
        gate = conn.claim_project_gate = _ELIGIBILITY[0].Gate(S, conn, domain_uuid=None, repository_uuid=None)
    return gate


def transition(conn, params, before):
    """The claim organ, as a store transaction transition: every claim record's one decision, for
    `params` over the command's `before`, inside the command transaction open on `conn`. A handout
    first asks the Gate's project check of its unit on that connection, and is refused by the Gate's
    own name when the check finds a problem."""
    if params['action'] in HANDOUTS:
        refusals, _read = _project_gate(conn).project_problems(params['unit_id'])
        if refusals:
            raise S.StoreRefused(refusals[0], 'the unit\'s project takes no new assignment')
    return _changes(params, before)


def _changes(params, before):
    unit, backlog, cid = params['unit_id'], params['backlog_item_uuid'], params['claim_id']
    u, b = before[unit]['data'], before[backlog]['data']
    current = before.get(cid, {}).get('data', {})
    status = ownership(current, u, b, params['action'])
    if status in ('unanswerable', 'ownership_uncertain'):
        raise S.StoreRefused(status, 'ownership cannot be established; stop without takeover')
    op, holder = params['action'], params['holder']
    if op == 'unpark':
        # The park is cleared only on the assignment the unit is parked on; the claim stays
        # released with no holder, and the next owner takes it through an ordinary claim.
        if status != 'parked' or current.get('parked_on') != params.get('parked_on'):
            raise S.StoreRefused('stale_subject', 'unpark names the assignment the unit is parked on')
        data = {k: v for k, v in current.items() if k != 'parked_on'}
        data.update(state='released', holder=None, unparked_from=params['parked_on'])
        return {cid: {'kind': 'claim', 'data': data}}
    if op in ('claim', 'resume'):
        if status == 'owned':
            raise S.StoreRefused('claimed', 'an owner already holds this unit')
        parked = current.get('parked_on') if status == 'parked' else None
        if op == 'claim' and parked:
            raise S.StoreRefused('parked', 'the unit waits for a person assignment; it resumes only through its admission')
        if op == 'resume' and (not parked or parked != params.get('parked_on')):
            raise S.StoreRefused('stale_subject', 'resume names the assignment the unit is parked on')
        if (u.get('state') != 'READY' and not (u.get('state') == 'CLAIMED' and current.get('state') == 'released')
                or b.get('state') not in ('PRIORITIZED', 'ACTIVE')):
            raise S.StoreRefused('not_admitted', 'unit must be READY and backlog PRIORITIZED or ACTIVE')
        if holder not in u.get('eligible_holders', []):
            raise S.StoreRefused('not_authorized', 'holder is not assigned to this unit')
        if not CL.capability_ok(params['capabilities'], u.get('requirements', [])):
            raise S.StoreRefused('capability', 'worker lacks an accepted requirement')
        data = dict(unit_id=unit, backlog_item_uuid=backlog, repository_uuid=params['repository_uuid'],
                    holder=holder, generation=current.get('generation', 0) + 1,
                    state='owned', heartbeat_at=CL._now())
        if op == 'resume':
            data['resumed_from'] = parked
        return {cid: {'kind': 'claim', 'data': data},
                unit: {'kind': 'execution_unit', 'data': dict(u, state='CLAIMED')},
                backlog: {'kind': 'backlog_item', 'data': dict(b, state='ACTIVE')}}
    if status != 'owned':
        raise S.StoreRefused('unowned', 'there is no current owner')
    if current.get('holder') != holder:
        raise S.StoreRefused('not_owner', 'operation requires the stored holder')
    if current.get('generation') != params['generation']:
        raise S.StoreRefused('stale_generation', 'operation requires the stored claim generation')
    if op in ('release', 'park'):
        data = dict(current, state='released', holder=None)
        if op == 'park':
            if not isinstance(params.get('parked_on'), str) or not params['parked_on']:
                raise S.StoreRefused('invalid_input', 'park names the assignment the unit waits for')
            data['parked_on'] = params['parked_on']
    elif op == 'renew':
        data = dict(current, heartbeat_at=CL._now())
    else:
        return {}  # protected use is journaled, without granting source-publication authority
    return {cid: {'kind': 'claim', 'data': data}}


class Receiver:
    """One repository's claim operations on the configured real store connection.

    Diagnostic rows include identity, accepted versions and outcome only. Metrics
    count this receiver's accepted/refused calls; pending() reads current ownership.
    """
    def __init__(self, conn, authority_ids, journal_signer, sign, authority_generation=1):
        self.conn, self.ids = conn, dict(authority_ids)
        self.journal_signer, self.sign = journal_signer, sign
        self.authority_generation = authority_generation
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        self.gate = None
        # VELDO-0169: the claim organ decides every claim record, on this receiver's own connection.
        conn.command_registry['claim_operation'] = {
            'transaction_transition': self._in_transaction, 'writes': ('entities', 'journal', 'commands', 'nonces')}

    def apply(self, packet):
        command = packet.get('command', {}) if isinstance(packet, dict) else {}
        if not isinstance(command, dict):
            command = {}
        observation = dict(self.ids, operation=command.get('operation'), unit_id=command.get('unit_id'),
                           command_id=command.get('command_id'), accepted_versions={})
        for _ in range(ATTEMPTS):
            try:
                result = self._apply(packet, command, observation)
            except S.StoreRefused as exc:
                result = {'ok': False, 'reason': exc.code}
                # stale_version here names the versions THIS receiver read and pinned, not any the
                # caller sent: another writer moved one between the read and the commit, and nothing
                # was written. That is contention on the receiver's own read, never an answer about
                # ownership, so it reads again and decides on the state that is current now (a renew
                # racing a unit transition was otherwise reported as a lost claim). Any other refusal,
                # or a stale_version whose pinned versions did not move, is the answer.
                if exc.code == 'stale_version' and self._pins_moved(observation['accepted_versions']):
                    continue
            break
        observation.update(outcome='accepted' if result['ok'] else 'refused', reason=result.get('reason'))
        self.counts[observation['outcome']] += 1
        if not result['ok']:
            reasons = self.counts.setdefault('refused_by_reason', {})
            reasons[result['reason']] = reasons.get(result['reason'], 0) + 1
        self.observations.append(observation)
        return result

    def _project_problems(self, unit):
        """VELDO-0076: the shared Gate's own project check of `unit` over this receiver's connection, and
        the versions it was decided from (control_eligibility.Gate.project_problems)."""
        if self.gate is None:
            EL = organ('control_eligibility')
            self.gate = EL.Gate(S, self.conn, domain_uuid=self.ids['domain_uuid'],
                                repository_uuid=self.ids['repository_uuid'],
                                authority_generation=self.authority_generation)
        return self.gate.project_problems(unit)

    def _in_transaction(self, conn, params, before):
        """claim_operation inside its store transaction, on this receiver's connection: the claim organ
        decides it there (and asks the Gate's project check of a claim itself)."""
        if conn is not self.conn or not conn.in_transaction:
            raise S.StoreRefused('wrong_connection', 'the claim is written in this receiver\'s store transaction')
        return transition(conn, params, before)

    def _pins_moved(self, pinned):
        entities = S.materialized_state(self.conn)['entities']
        return any(entities.get(eid, {}).get('version', 0) != version for eid, version in pinned.items())

    def _apply(self, packet, command, observation):
        if (not isinstance(packet, dict) or not isinstance(packet.get('command'), dict)
                or not isinstance(packet.get('signature'), str)
                or not packet['signature'].isascii()):
            raise S.StoreRefused('malformed_request', 'command must be a mapping and signature an ASCII string')
        validate_alias(command.get('unit_id'))
        required = {'operation', 'unit_id', 'principal', 'command_id', 'nonce', 'generation', 'capabilities', *self.ids}
        if (not required <= command.keys() or command['operation'] not in OPERATIONS
                or not all(isinstance(command[k], str) and command[k] for k in ('principal', 'command_id', 'nonce'))
                or not isinstance(command['capabilities'], list)
                or not all(isinstance(x, str) for x in command['capabilities'])
                or type(command['generation']) is not int or command['generation'] < 0
                or any(command[k] != v for k, v in self.ids.items())):
            raise S.StoreRefused('invalid_input', 'invalid claim command or authority coordinates')
        state = CM.authority_state(S, self.conn)
        now, principal = time.time(), command['principal']
        member = AC.membership_entry(state['membership'], principal)
        active, why = AC.active_member(member, now)
        key = AC.active_key(state['keyring'], principal, now)
        if (not active or not key or member['principal_type'] not in AC.BOUNDARIES['claim']
                or not CM.scope_covers(member.get('scope'), self.ids['repository_uuid'])):
            raise S.StoreRefused('not_authorized', why or 'claim membership or scope absent')
        verified, _ = AC.ssh_keygen_verify(S.canonical_bytes(command), packet.get('signature', ''),
                                          AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise S.StoreRefused('not_authorized', 'command signature did not verify')
        entities = state['entities']
        unit = command['unit_id']
        u = entities.get(unit, {})
        backlog = u.get('data', {}).get('backlog_item_uuid')
        b = entities.get(backlog, {})
        if (u.get('kind') != 'execution_unit' or b.get('kind') != 'backlog_item'
                or u['data'].get('repository_uuid') != self.ids['repository_uuid']
                or b['data'].get('repository_uuid') != self.ids['repository_uuid']):
            raise S.StoreRefused('missing_authority', 'accepted unit/backlog missing from this repository')
        cid = claim_id(self.ids['repository_uuid'], unit)
        current = entities.get(cid, {}).get('data', {})
        if command['operation'] == 'inspect':
            status = ownership(current, u['data'], b['data'])
            return {'ok': status in ('owned', 'unowned'), 'reason': status, 'claim': current}
        # Bind every authorization and activation input to the store transaction.
        touched = {unit, backlog, cid, principal, key['key_id'], CM.VERSIONS_ENTITY}
        versions = {eid: entities.get(eid, {}).get('version', 0) for eid in touched}
        if command['operation'] == 'claim':
            # VELDO-0076: a paused, canceled or completed project takes no new assignment. The check is the
            # one every station makes; the project and owner records it read are pinned with the rest, so
            # a pause committed before this claim refuses it by name, never after it.
            refusals, read = self._project_problems(unit)
            versions.update(read)
            observation.update(project=u['data'].get('project'), accepted_versions=dict(versions))
            if refusals:
                raise S.StoreRefused(refusals[0], 'the unit\'s project takes no new assignment')
            params = dict(action='claim', unit_id=unit, backlog_item_uuid=backlog, claim_id=cid,
                          holder=principal, generation=command['generation'], capabilities=command['capabilities'],
                          repository_uuid=self.ids['repository_uuid'])
        else:
            # Renew, release and use of a claim already held hand nothing out.
            params = dict(action=command['operation'], unit_id=unit, backlog_item_uuid=backlog, claim_id=cid,
                          holder=principal, generation=command['generation'], capabilities=command['capabilities'],
                          repository_uuid=self.ids['repository_uuid'])
        observation['accepted_versions'] = versions
        stored = dict(command_id=command['command_id'], principal=principal, operation='claim_operation',
                      parameters=params, expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        result = S.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        current = S.materialized_state(self.conn)['entities'].get(cid, {}).get('data', {})
        return {'ok': True, 'reason': command['operation'], 'claim': current, 'receipt': result}

    def pending(self):
        return {eid: e['data'] for eid, e in S.materialized_state(self.conn)['entities'].items()
                if e['kind'] == 'claim' and e['data'].get('state') != 'released'}
