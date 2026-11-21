"""Accepted host configuration and all-capability dispatch selection (VELDO-0125).

Only the trusted authority calls prepare. Requirements come from the admitted
unit decision, never a remote claim. Profiles are operator accepted configuration
in the authority config, with evidence bound to their full immutable definition.
Availability is separate so disabling a host cannot rewrite an existing contract.
"""
import copy
import importlib.util
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


D = organ('control_dispatch')
Refused = D.Refused


def definition(profile):
    return {k: v for k, v in profile.items() if k not in ('available', 'qualification')}


def qualified(profile):
    evidence = profile.get('qualification') or {}
    return (profile.get('platform') in ('linux', 'darwin')
            and type(profile.get('revision')) is int and profile['revision'] > 0
            and all(isinstance(profile.get(k), str) and profile[k] for k in ('host', 'principal'))
            and isinstance(profile.get('capabilities'), list)
            and all(isinstance(v, str) and v for v in profile['capabilities'])
            and (profile['platform'] == 'darwin' or not {'macos', 'ios-build'}.intersection(profile['capabilities']))
            and evidence.get('kind') == 'native' and bool(evidence.get('reference'))
            and evidence.get('profile_digest') == D.digest(definition(profile)))


def requirements(contract):
    required = contract['input']['context'].get('required_host_capabilities',
        contract['input']['decision']['inputs'].get('required_host_capabilities', []))
    if not isinstance(required, list) or not all(isinstance(c, str) and c for c in required):
        raise Refused('invalid_input:host_capabilities')
    return sorted(set(required))


def eligible(profile, contract):
    capability = contract['capability']
    return (qualified(profile) and profile.get('available') is True
            and set(requirements(contract)).issubset(profile['capabilities'])
            and profile.get('engines', {}).get(capability['adapter']) == capability['configuration_digest'])


def select(profiles, contract):
    hosts = [p['host'] for p in profiles]
    if len(hosts) != len(set(hosts)):
        raise Refused('unsupported_configuration:duplicate_host')
    for profile in profiles:
        if eligible(profile, contract):
            return dict(host=profile['host'], principal=profile['principal'], platform=profile['platform'],
                        profile_digest=D.digest(definition(profile)), runtime_profile=profile.get('runtime_profile'), required=requirements(contract))
    raise Refused('blocked:no_qualified_host')


def check(profiles, contract):
    route = contract['input']['context'].get('host_route')
    if not isinstance(route, dict):
        raise Refused('missing_evidence:host_route')
    matches = [p for p in profiles if p['host'] == route['host']]
    if (len(matches) != 1 or not eligible(matches[0], contract)
            or route != dict(host=matches[0]['host'], principal=matches[0]['principal'],
                             platform=matches[0]['platform'], profile_digest=D.digest(definition(matches[0])),
                             runtime_profile=matches[0].get('runtime_profile'),
                             required=requirements(contract))):
        raise Refused('blocked:host_unavailable_or_changed')
    return route


def decision_transition(params, before):
    return {params['id']: dict(kind='host_routing', data=params['decision'])}


def record_decision(dispatches, result):
    """Owner-visible routing state survives a blocked queue pass."""
    store, conn = dispatches.store, dispatches.conn
    operation = 'host_routing_decision'
    conn.command_registry[operation] = dict(transition=decision_transition,
                                            writes=('entities', 'journal', 'commands', 'nonces'))
    store.declare_owners(conn, 'VELDO-0125-routing', kinds={'host_routing': (operation,)},
                         prefixes={'routing:': (operation,)}, module=__file__)
    identity = 'routing:' + result['dispatch_id']
    row = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
    version = row[0] if row else 0
    command_id = 'routing/' + result['dispatch_id'] + '/' + str(version + 1)
    store.execute(conn, dict(command_id=command_id, principal=dispatches.principal, operation=operation,
        nonce=command_id, artifact_digests=[], expected_versions={identity: version},
        parameters=dict(id=identity, decision=dict(result, domain=dispatches.domain, repository=dispatches.repository))),
        dispatches.signer, dispatches.sign, dispatches.generation)


def check_prepared(dispatches, profiles, contract):
    try:
        return check(profiles, contract)
    except Refused as error:
        if error.code.startswith('blocked:'):
            record_decision(dispatches, dict(state='blocked', reason=error.code,
                unit=contract['unit'], dispatch_id=contract['dispatch_id'], required=requirements(contract)))
        raise


def prepare(dispatches, contract, profiles, *, now):
    """Before Runner launch: returns a visible blocked decision or a stored contract.
    No reservation is released and no fallback is launched when the host is absent.
    The caller retains blocked work in its queue and surfaces the returned reason.
    """
    contract = copy.deepcopy(contract)
    if dispatches.record(contract['dispatch_id']) is not None:
        raise Refused('duplicate_dispatch')
    try:
        route = select(profiles, contract)
    except Refused as error:
        if error.code != 'blocked:no_qualified_host':
            raise
        result = dict(state='blocked', reason=error.code, unit=contract['unit'],
                      dispatch_id=contract['dispatch_id'], required=requirements(contract))
        record_decision(dispatches, result)
        return result
    contract['input']['context']['host_route'] = route
    dispatches.prepare(contract, now=now)
    result = dict(state='prepared', unit=contract['unit'], dispatch_id=contract['dispatch_id'],
                  required=requirements(contract), host=route['host'], contract_digest=D.digest(contract))
    record_decision(dispatches, result)
    return dict(result, contract=contract)
