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
"""
import hashlib as _veldo_hashlib

VELDO_INTAKE = 'veldo_intake'
VELDO_STEP_KINDS = ('grooming', 'owner_wait', 'assignment', 'result_handling')
VELDO_OWNER_PORTS = {'accepted': 'admit', 'declined': 'decline'}


def _veldo_supplied(view):
    return {item.get('id'): item for item in view['supplied_results'] if type(item) is dict}


def _veldo_route(definition, name, port):
    for transition in definition['transitions']:
        if transition['from'] == name and transition['port'] == port:
            return transition['to']
    return None


def _veldo_node(definition, reference, name):
    kind = definition['nodes'][name]['kind']

    def step(view):
        supplied = _veldo_supplied(view)
        subject = (supplied.get('subject') or {}).get('value') or {}
        if kind == 'result_handling':
            evidence = sorted({item['digest'] for item in supplied.values()})
            return {'next': None, 'proposals': [{'type': 'completion', 'proposal_id': view['identity']['cycle_id'] + '.' + name,
                                                 'subject': subject.get('unit'), 'evidence': evidence}]}
        notes = {}
        if kind == 'grooming':
            port, notes = 'groomed', {'groomed': subject.get('unit')}
        elif kind == 'owner_wait':
            answer = ((supplied.get('owner_answer') or {}).get('value') or {}).get('state')
            port, notes = VELDO_OWNER_PORTS.get(answer), {'answer': answer}
        elif kind == 'assignment':
            port = 'done' if 'worker_result' in supplied else None
        else:
            port = None
        if port is None:
            return {'failure': {'code': 'invalid_input', 'detail': name + ' was supplied nothing to route by'}}
        following = _veldo_route(definition, name, port)
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
