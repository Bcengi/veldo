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


def transition(params, before):
    unit, backlog, cid = params['unit_id'], params['backlog_item_uuid'], params['claim_id']
    u, b = before[unit]['data'], before[backlog]['data']
    current = before.get(cid, {}).get('data', {})
    status = ownership(current, u, b, params['action'])
    if status in ('unanswerable', 'ownership_uncertain'):
        raise S.StoreRefused(status, 'ownership cannot be established; stop without takeover')
    op, holder = params['action'], params['holder']
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
        S.COMMAND_REGISTRY['claim_operation'] = {
            'transition': transition, 'writes': ('entities', 'journal', 'commands', 'nonces')}

    def apply(self, packet):
        command = packet.get('command', {}) if isinstance(packet, dict) else {}
        if not isinstance(command, dict):
            command = {}
        observation = dict(self.ids, operation=command.get('operation'), unit_id=command.get('unit_id'),
                           command_id=command.get('command_id'), accepted_versions={})
        try:
            result = self._apply(packet, command, observation)
        except S.StoreRefused as exc:
            result = {'ok': False, 'reason': exc.code}
        observation.update(outcome='accepted' if result['ok'] else 'refused', reason=result.get('reason'))
        self.counts[observation['outcome']] += 1
        self.observations.append(observation)
        return result

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
        observation['accepted_versions'] = versions
        params = dict(action=command['operation'], unit_id=unit, backlog_item_uuid=backlog, claim_id=cid,
                      holder=principal, generation=command['generation'], capabilities=command['capabilities'],
                      repository_uuid=self.ids['repository_uuid'])
        stored = dict(command_id=command['command_id'], principal=principal, operation='claim_operation',
                      parameters=params, expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        result = S.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        current = S.materialized_state(self.conn)['entities'].get(cid, {}).get('data', {})
        return {'ok': True, 'reason': command['operation'], 'claim': current, 'receipt': result}

    def pending(self):
        return {eid: e['data'] for eid, e in S.materialized_state(self.conn)['entities'].items()
                if e['kind'] == 'claim' and e['data'].get('state') != 'released'}
