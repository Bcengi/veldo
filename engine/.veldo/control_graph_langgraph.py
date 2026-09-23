"""The LangGraph runner behind the plain-data graph adapter (VELDO-0043).

This file is the execution environment, not enforcement. It runs only as the child process that
control_graph.py launches with the locked runtime's own interpreter (`python -I -B`), in an empty
working directory with a fixed environment, and it is never imported by enforcement code.

One exchange per process: read one veldo.graph/v1 request on stdin, write one response on
stdout. The graph is nonpersistent (Release 1): no checkpointer, no database, no store handle or
path. A cycle that needs supplied results stops with outcome `suspended` and hands the caller a
plain resume value {position, step, notes}; `advance` rebuilds the graph and enters it at that
position with the accepted snapshot and supplied results. Veldo owns every identity.

A workflow is {'version': int, 'entry': node, 'nodes': {name: function}}. A node receives a
plain view {identity, snapshot, supplied_results, notes, step} and returns a mapping with only
these keys: `next` (a node name, or None to end), `suspend` (true: stop for supplied results and
resume at `next`), `proposals` (typed proposal mappings), `failure` ({code, detail}) and `notes`
(graph working data). Any other key is an untyped assertion and ends the cycle as the named
failure node_failed: a graph proposes, it never asserts admission, priority or completion.
Nothing leaves this process that is not exact plain JSON data; LangGraph objects never cross.

Workflow definitions are supplied by VELDO-0132; this module registers none, so production
`main` answers every workflow with the named failure unsupported_workflow.
"""
import importlib.metadata
import json
import math
import sys

SCHEMA = 'veldo.graph/v1'
IDENTITY = ('cycle_id', 'command_id', 'domain_uuid', 'repository_uuid')
NODE_KEYS = ('next', 'suspend', 'proposals', 'failure', 'notes')
MAX_STEPS = 64
WORKFLOWS = {}


class NotPlain(Exception):
    pass


def plain_copy(value, where='value'):
    """Exact JSON types only; a LangGraph object, tuple or subclass is not plain data."""
    kind = type(value)
    if value is None or kind in (bool, int, str):
        return value
    if kind is float and math.isfinite(value):
        return value
    if kind is list:
        return [plain_copy(item, where + '[]') for item in value]
    if kind is dict and all(type(key) is str for key in value):
        return {key: plain_copy(item, where + '.' + key) for key, item in value.items()}
    raise NotPlain(where + ': ' + kind.__module__ + '.' + kind.__qualname__ + ' is not plain data')


def _reply(request, outcome, **fields):
    reply = {key: request[key] for key in ('schema', 'operation') + IDENTITY}
    reply.update(outcome=outcome, runtime={'name': 'langgraph',
                                           'version': importlib.metadata.version('langgraph')})
    reply.update(fields)
    return reply


def _failure(request, code, detail):
    return _reply(request, 'failure', failure={'code': code, 'detail': detail[:500]})


def emit(request, reply, stdout):
    try:
        body = json.dumps(plain_copy(reply), allow_nan=False)
    except NotPlain as error:
        body = json.dumps(_failure(request, 'node_failed', str(error)), allow_nan=False)
    stdout.write(body)


def _resume(request, workflow):
    resume = request.get('resume')
    if (type(resume) is not dict or set(resume) != {'position', 'step', 'notes'}
            or resume['position'] not in workflow['nodes'] or type(resume['step']) is not int
            or type(resume['notes']) is not dict):
        return None
    return resume


def _build(workflow):
    from typing import TypedDict
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command

    class State(TypedDict, total=False):
        identity: dict
        snapshot: dict
        supplied_results: list
        position: str
        step: int
        notes: dict
        proposals: list
        halt: str
        failure: dict

    def wrap(name, function):
        def node(state):
            view = {'identity': state['identity'], 'snapshot': state['snapshot'],
                    'supplied_results': state['supplied_results'], 'notes': dict(state['notes']),
                    'step': state['step']}
            out = function(view)
            base = {'step': state['step'] + 1, 'position': name}
            if type(out) is not dict:
                return Command(goto=END, update=dict(base, halt='failure', failure={
                    'code': 'node_failed', 'detail': name + ' returned no node output mapping'}))
            untyped = sorted(set(out) - set(NODE_KEYS))
            if untyped:
                return Command(goto=END, update=dict(base, halt='failure', failure={
                    'code': 'node_failed',
                    'detail': name + ' returned an untyped assertion: ' + ', '.join(untyped)}))
            if out.get('failure') is not None:
                return Command(goto=END, update=dict(base, halt='failure', failure=out['failure']))
            update = dict(base, notes=dict(state['notes'], **(out.get('notes') or {})),
                          proposals=state['proposals'] + list(out.get('proposals') or []))
            following = out.get('next')
            if following is not None and following not in workflow['nodes']:
                return Command(goto=END, update=dict(update, halt='failure', failure={
                    'code': 'unsupported_workflow', 'detail': name + ' names no node ' + repr(following)}))
            if out.get('suspend'):
                if following is None or update['proposals']:
                    return Command(goto=END, update=dict(update, halt='failure', failure={
                        'code': 'node_failed',
                        'detail': name + ' suspended without a resume node or with proposals'}))
                return Command(goto=END, update=dict(update, halt='suspend', position=following))
            if following is None:
                return Command(goto=END, update=dict(update, halt='end'))
            return Command(goto=following, update=dict(update, position=following))
        return node

    graph = StateGraph(State)
    for name, function in workflow['nodes'].items():
        graph.add_node(name, wrap(name, function))
    graph.add_conditional_edges(START, lambda state: state['position'], list(workflow['nodes']))
    return graph.compile()


def run_cycle(request, workflow, resume):
    from langgraph.errors import GraphRecursionError
    state = {'identity': {key: request[key] for key in IDENTITY}, 'snapshot': request['snapshot'],
             'supplied_results': request.get('supplied_results', []), 'proposals': [], 'halt': '',
             'position': resume['position'], 'step': resume['step'], 'notes': resume['notes']}
    try:
        final = _build(workflow).invoke(state, {'recursion_limit': MAX_STEPS})
    except GraphRecursionError:
        return _failure(request, 'node_failed', 'the cycle exceeded its step bound')
    except Exception as error:  # a node's own exception is that node's failure, by name
        return _failure(request, 'node_failed', 'node raised ' + type(error).__name__)
    if final.get('halt') == 'failure':
        failure = final.get('failure')
        if type(failure) is not dict or failure.get('code') not in (
                'invalid_input', 'missing_evidence', 'node_failed', 'unsupported_workflow'):
            return _failure(request, 'node_failed', 'a node failed without a named code')
        return _reply(request, 'failure', failure={'code': failure['code'],
                                                   'detail': str(failure.get('detail', ''))[:500]})
    if final.get('halt') == 'suspend':
        return _reply(request, 'suspended', resume={'position': final['position'],
                                                    'step': final['step'], 'notes': final['notes']})
    if final.get('halt') == 'end' and final.get('proposals'):
        return _reply(request, 'proposal', proposals=final['proposals'])
    return _failure(request, 'missing_evidence', 'the cycle ended without a proposal')


def answer(request, workflows):
    workflow = workflows.get(request['workflow']['id'])
    if workflow is None or workflow['version'] != request['workflow']['version']:
        return _failure(request, 'unsupported_workflow', 'no registered workflow ' +
                        request['workflow']['id'] + ' version ' + str(request['workflow']['version']))
    operation = request['operation']
    if operation == 'start':
        return run_cycle(request, workflow, {'position': workflow['entry'], 'step': 0, 'notes': {}})
    resume = _resume(request, workflow)
    if resume is None:
        return _failure(request, 'invalid_input', 'resume is not this workflow\'s plain position')
    if operation == 'advance':
        return run_cycle(request, workflow, resume)
    if operation == 'suspend':
        return _reply(request, 'suspended', resume=resume)
    return _reply(request, 'canceled')


def serve(workflows, stdin=None, stdout=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    request = json.loads(stdin.buffer.read() if hasattr(stdin, 'buffer') else stdin.read())
    emit(request, answer(request, workflows), stdout)
    return 0


if __name__ == '__main__':
    sys.exit(serve(WORKFLOWS))
