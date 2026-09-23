"""Protected effect authority. Accepted contracts are service records, never worker declarations.

The scheduler/lander supplies versioned effect_contract and effect_permission entities through
its trusted store connection. This narrow consumption seam does not admit work or run reviews.
Handles convey no provider credential. All mutations use the existing signed store transaction.
"""
import importlib.util
import math
from pathlib import Path
import secrets
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('effect_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SIG = organ('control_signer')
R = organ('control_revocation')
S, CM, AC = SIG.S, SIG.CM, SIG.AC
Refused = SIG.K.Refused
NAMESPACE = 'veldo-effect-connection'
BINDINGS = ('domain_uuid', 'repository_uuid', 'unit', 'station', 'sandbox', 'dispatch_id', 'kind', 'target')
KINDS = ('provider', 'publication')


def entity(state, identity, kind):
    entry = state.get(identity)
    if not entry or entry['kind'] != kind:
        raise Refused('missing-authority')
    return entry


def authenticate(state, principal, challenge, request, signature):
    now = time.time()
    member = entity(state, principal, 'membership')['data']
    if member.get('revoked_at') is not None or (member.get('expires_at') is not None and now >= member['expires_at']):
        raise Refused('missing-authority')
    keys = [e['data'] for e in state.values() if e['kind'] == 'verification_key']
    key = AC.active_key(keys, principal, now)
    if not key:
        raise Refused('unauthenticated-worker')
    message = SIG.canonical({'challenge': challenge, 'request_digest': SIG.digest(request)})
    valid, _ = AC.ssh_keygen_verify(message, signature,
                                   AC.allowed_signers_line(principal, key['public_key'], NAMESPACE),
                                   principal, NAMESPACE)
    if not valid:
        raise Refused('unauthenticated-worker')


def authorize(conn, state, config, principal, request, consume=True):
    entry = entity(state, request['contract_id'], 'effect_contract')
    contract = entry['data']
    now = time.time()
    # The same connection observes the ledger under the acceptance write lock.
    if R.is_revoked(S, conn, principal, now):
        raise Refused('revoked')
    for identity, version in config.get('_auth_versions', {}).items():
        if state.get(identity, {}).get('version') != version:
            raise Refused('stale-authority')
    member = entity(state, principal, 'membership')['data']
    if member.get('revoked_at') is not None or (member.get('expires_at') is not None and now >= member['expires_at']):
        raise Refused('missing-authority')
    if contract.get('worker') != principal or contract.get('status') != 'accepted':
        raise Refused('missing-authority')
    if any(contract.get(f) != config[f] for f in ('domain_uuid', 'repository_uuid')):
        raise Refused('foreign-authority')
    if contract.get('kind') not in KINDS or any(not isinstance(contract.get(f), str) or not contract[f] for f in BINDINGS):
        raise Refused('invalid-contract')
    deadline = contract.get('deadline')
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or now >= deadline:
        raise Refused('expired-contract')
    if any(request.get(f) != contract[f] for f in BINDINGS):
        raise Refused('scope-mismatch')
    permission = entity(state, contract['permission_id'], 'effect_permission')
    data = permission['data']
    if (data.get('contract_digest') != entry['digest'] or data.get('authorized') is not True
            or data.get('obligations', []) or data.get('expires_at', 0) <= now):
        raise Refused('missing-authority')
    if contract['kind'] == 'provider':
        if data.get('subscription_allowed') is not True or (consume and data.get('remaining_calls', 0) < 1):
            raise Refused('usage-cap')
    else:
        payload = contract.get('payload', {})
        if any(not isinstance(payload.get(f), str) or len(payload[f]) not in (40, 64)
               or any(c not in '0123456789abcdef' for c in payload[f]) for f in ('commit', 'tree', 'old_tip')):
            raise Refused('missing-evidence')
        if (data.get('gate_tree') != contract.get('payload', {}).get('tree')
                or data.get('gate_passed') is not True or data.get('review_passed') is not True
                or not data.get('reviewer') or data.get('reviewer') == contract.get('worker')
                or not data.get('reviewer_group') or data.get('reviewer_group') == data.get('worker_group')
                or data.get('approval_current') is not True):
            raise Refused('missing-evidence')
    return entry, permission


def command(conn, operation, params, state, nonce, journal):
    cmd = {'command_id': secrets.token_hex(20), 'principal': 'effect-executor',
           'operation': operation, 'parameters': params,
           'expected_versions': {key: value['version'] for key, value in state.items()},
           'artifact_digests': [], 'nonce': nonce}
    for identity in params.get('new_ids', []):
        cmd['expected_versions'].setdefault(identity, 0)
    return S.execute(conn, cmd, journal[0], journal[1], 1)


def transact(conn, operation, params, state, nonce, journal, transition):
    S.COMMAND_REGISTRY[operation] = {'transition': transition, 'writes': ('entities', 'journal', 'commands', 'nonces')}
    return command(conn, operation, params, state, nonce, journal)


def issue(conn, config, principal, request, journal):
    state = S.materialized_state(conn)['entities']
    handle = secrets.token_urlsafe(32)
    hid = 'handle:' + SIG.digest(handle)
    def transition(params, before):
        entry, _ = authorize(conn, before, config, principal, request)
        contract = entry['data']
        data = {f: contract[f] for f in BINDINGS}
        data.update(contract_id=request['contract_id'], contract_digest=entry['digest'],
                    contract_version=entry['version'], worker=principal,
                    expires_at=min(contract['deadline'] + 900, time.time() + 900))
        return {hid: {'kind': 'effect_handle', 'data': data}}
    transact(conn, 'issue_effect_handle', {'new_ids': [hid]}, state, secrets.token_hex(20), journal, transition)
    return {'accepted': True, 'handle': handle, 'binding': S.materialized_state(conn)['entities'][hid]['data']}


def accept(conn, config, principal, request, journal):
    state = S.materialized_state(conn)['entities']
    entry, _ = authorize(conn, state, config, principal, request, consume=False)
    hid = 'handle:' + SIG.digest(request['handle'])
    handle = entity(state, hid, 'effect_handle')['data']
    if (handle['worker'] != principal or handle['contract_id'] != request['contract_id']
            or handle['contract_digest'] != entry['digest'] or time.time() >= handle['expires_at']):
        raise Refused('stale-handle')
    eid = 'effect:' + entry['data']['dispatch_id']
    previous = state.get(eid)
    if previous:
        if previous['data']['request_digest'] != SIG.digest(request):
            raise Refused('request-content-conflict')
        return previous['data'], False
    nonce = hid
    def transition(params, before):
        current, permission = authorize(conn, before, config, principal, request)
        saved = entity(before, hid, 'effect_handle')['data']
        if saved['contract_digest'] != current['digest'] or time.time() >= saved['expires_at']:
            raise Refused('stale-handle')
        contract = current['data']
        data = {f: contract[f] for f in BINDINGS}
        data.update(contract_id=request['contract_id'], contract_digest=current['digest'],
                    contract_version=current['version'], worker=principal, permission_version=permission['version'], payload=contract['payload'],
                    request_digest=SIG.digest(request), status='accepted', stop='effect-pending',
                    completed=False, evidence=None)
        changes = {eid: {'kind': 'protected_effect', 'data': data}}
        if contract['kind'] == 'provider':
            usage = dict(permission['data'], remaining_calls=permission['data']['remaining_calls'] - 1,
                         outstanding_dispatch=contract['dispatch_id'])
            changes[contract['permission_id']] = {'kind': 'effect_permission', 'data': usage}
        return changes
    transact(conn, 'accept_protected_effect', {'new_ids': [eid]}, state, nonce, journal, transition)
    return S.materialized_state(conn)['entities'][eid]['data'], True


def finish(conn, accepted, observation, journal):
    bound = ('dispatch_id', 'target', 'request_digest')
    matches = isinstance(observation, dict) and all(observation.get(f) == accepted[f] for f in bound)
    status = observation.get('status') if matches else 'unknown'
    if status not in ('accepted', 'completed', 'unknown'):
        status = 'unknown'
    completed = status == 'completed' and bool(observation.get('evidence'))
    if status == 'completed' and not completed:
        status = 'unknown'
    result = dict(accepted, status=status, completed=completed,
                  stop=None if completed else ('effect-pending' if status == 'accepted' else 'effect-outcome-unknown'),
                  evidence=SIG.digest(observation) if matches else None)
    eid = 'effect:' + accepted['dispatch_id']
    state = S.materialized_state(conn)['entities']
    transact(conn, 'observe_protected_effect', {}, state, secrets.token_hex(20), journal,
             lambda p, b: {eid: {'kind': 'protected_effect', 'data': result}})
    return result


def metrics(conn):
    entries = S.materialized_state(conn)['entities'].values()
    effects = [e['data'] for e in entries if e['kind'] == 'protected_effect']
    return {'accepted': len(effects), 'pending': sum(not e['completed'] for e in effects)}
