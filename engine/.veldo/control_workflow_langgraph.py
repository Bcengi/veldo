"""The registered workflow step kinds as the graph runner executes them (VELDO-0132).

NOTHING IMPORTS THIS FILE. control_workflow_cycle.runner_source() splices its text into a copy of
the production runner (control_graph_langgraph.py), after the runner's own definitions and before
its entry point, followed by ONE call registering the exact stored definition of one revision:
veldo_register_workflow(<the definition's canonical text>, <version>). That runner answers only that
revision, and the adapter stages it content-addressed like any runner. This is the execution
environment, not enforcement: it holds no store, path or credential, and control_workflow_cycle
re-judges every step it reports against the stored revision before anything follows from it.

ONE STEP PER EXCHANGE. `start` runs the intake node, which runs no step of the definition: it
reports the digest of the definition this runner was built from and suspends at the entry. Each
`advance` runs the ONE node at the cycle's position and suspends at the node its outcome port
leads to, so the domain side sees, and may refuse, every transition before the next node runs. A
terminal node ends the cycle with its typed proposal. Every suspension's graph notes carry the
executed definition's {id, version, digest} and the step taken, [node, port, next].

THE STEP KINDS read only the plain supplied results the cycle hands them, by id:
  subject          {unit, state}   the cycle's subject, supplied to every step
  owner_answer     {state}         the owner's admission record: accepted routes admit,
                                   declined routes decline
  worker_result    {kind}          the worker's result an assignment node waits for; it routes done
  accepted_result  {kind}          the accepted result a result handling node cites
grooming routes groomed; result_handling proposes completion of the subject citing the digest of
every result it was supplied. A node with nothing to route by fails by name (invalid_input).
Standard library only; `json` and `WORKFLOWS` are the runner's own.

VELDO-0247. A check node reads `fields` {name: value} and routes by the first of its branches whose
conditions all hold, else otherwise; a field it names with no value or the wrong type fails it
(invalid_input, field_unsupplied:<field>). It reports the decision {node, branch, rule, conditions}
in its notes; the cycle re-evaluates it and refuses any difference. Nothing is evaluated: a value is
compared as data. A port with several transitions fans out ({branch id: first node}, naming the join
whose inputs are those ids); inside a branch a node reads its inputs as '<input>@<node>' and, when
its input is not here yet, stays where it is. A join routes done and clears the branch set.
"""
import hashlib as _veldo_hashlib

VELDO_INTAKE = 'veldo_intake'
VELDO_STEP_KINDS = ('grooming', 'owner_wait', 'assignment', 'result_handling', 'check', 'join')
VELDO_OWNER_PORTS = {'accepted': 'admit', 'declined': 'decline'}
VELDO_PARALLEL = 'veldo_parallel'
# Whether a rule's conditions all hold.
VELDO_HOLDS = all


def _veldo_supplied(view):
    return {item.get('id'): item for item in view['supplied_results'] if type(item) is dict}


def _veldo_routes(definition, name, port):
    return [t for t in definition['transitions'] if t['from'] == name and t['port'] == port]


def _veldo_typed(field, value):
    kind = field['type']
    if kind == 'number':
        return type(value) is int
    if kind == 'yes_no':
        return type(value) is bool
    return type(value) is str and (kind != 'choice' or value in field['choices'])


def _veldo_compare(comparison, observed, value):
    return {'is': lambda: observed == value, 'is not': lambda: observed != value,
            'less than': lambda: observed < value, 'at most': lambda: observed <= value,
            'more than': lambda: observed > value, 'at least': lambda: observed >= value,
            'contains': lambda: value in observed, 'is one of': lambda: observed in value}[comparison]()


def _veldo_check(definition, name, values):
    """(decision, None) or (None, field_unsupplied:<field>): the first branch whose conditions all hold."""
    config, fields = definition['nodes'][name]['config'], definition.get('fields') or {}
    for branch in config['branches']:
        for condition in branch['conditions']:
            if condition['field'] not in values or not _veldo_typed(fields[condition['field']], values[condition['field']]):
                return None, 'field_unsupplied:' + condition['field']
    conditions = []
    for branch in config['branches']:
        found = []
        for condition in branch['conditions']:
            observed = values[condition['field']]
            held = bool(_veldo_compare(condition['comparison'], observed, condition['value']))
            found.append(held)
            conditions.append({'rule': branch['name'], 'field': condition['field'], 'comparison': condition['comparison'],
                               'value': condition['value'], 'observed': observed, 'holds': held})
        if VELDO_HOLDS(found):
            return {'node': name, 'branch': branch['name'], 'rule': branch['name'], 'conditions': conditions}, None
    return {'node': name, 'branch': 'otherwise', 'rule': 'otherwise', 'conditions': conditions}, None


def _veldo_join_of(definition, ids):
    for other, node in sorted(definition['nodes'].items()):
        if node['kind'] == 'join' and sorted(node['config']['inputs']) == sorted(ids):
            return other
    return None


def _veldo_node(definition, reference, name):
    kind = definition['nodes'][name]['kind']

    def step(view):
        supplied = _veldo_supplied(view)
        branch = view.get('branch')

        def given(key):
            return supplied.get(key + '@' + name) if branch else supplied.get(key)

        subject = (supplied.get('subject') or {}).get('value') or {}
        if kind == 'result_handling':
            evidence = sorted({item['digest'] for item in supplied.values()})
            return {'next': None, 'proposals': [{'type': 'completion', 'proposal_id': view['identity']['cycle_id'] + '.' + name,
                                                 'subject': subject.get('unit'), 'evidence': evidence}]}
        notes = {}
        if kind == 'grooming':
            port, notes = 'groomed', {'groomed': subject.get('unit')}
        elif kind == 'owner_wait':
            answer = ((given('owner_answer') or {}).get('value') or {}).get('state')
            port, notes = VELDO_OWNER_PORTS.get(answer), {'answer': answer}
        elif kind == 'assignment':
            port = 'done' if given('worker_result') is not None else None
        elif kind == 'check':
            decision, problem = _veldo_check(definition, name, (given('fields') or {}).get('value') or {})
            if problem is not None:
                return {'failure': {'code': 'invalid_input', 'detail': problem}}
            port, notes = decision['branch'], {'decision': decision}
        elif kind == 'join':
            port, notes = 'done', {'joined': sorted(definition['nodes'][name]['config']['inputs']),
                                   'branches': None, 'join': None}
        else:
            port = None
        if port is None and branch:
            # Inside a branch, a node whose input is not here yet stays where it is.
            return {'next': name, 'suspend': True, 'notes': {'last': None}}
        if port is None:
            return {'failure': {'code': 'invalid_input', 'detail': name + ' was supplied nothing to route by'}}
        routes = _veldo_routes(definition, name, port)
        if len(routes) > 1:
            fan = {t['id']: t['to'] for t in routes}
            return {'next': fan, 'suspend': True,
                    'notes': dict(notes, workflow=reference, last=[name, port, VELDO_PARALLEL],
                                  join=_veldo_join_of(definition, list(fan)))}
        following = routes[0]['to'] if routes else None
        return {'next': following, 'suspend': True,
                'notes': dict(notes, workflow=reference, last=[name, port, following])}
    return step


def veldo_register_workflow(text, version):
    """Register the one definition this runner answers, built from its exact canonical text."""
    definition = json.loads(text)
    reference = {'id': definition['id'], 'version': version,
                 'digest': 'sha256:' + _veldo_hashlib.sha256(text.encode()).hexdigest()}

    def intake(view):
        return {'next': definition['entry'], 'suspend': True, 'notes': {'workflow': reference, 'last': None}}

    nodes = {VELDO_INTAKE: intake}
    for name, node in definition['nodes'].items():
        if node['kind'] in VELDO_STEP_KINDS:
            nodes[name] = _veldo_node(definition, reference, name)
    WORKFLOWS[definition['id']] = {'version': version, 'entry': VELDO_INTAKE, 'nodes': nodes}
    return reference
