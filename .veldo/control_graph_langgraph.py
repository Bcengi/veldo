"""The LangGraph runner behind the plain-data graph adapter (VELDO-0043).

This file is the execution environment, not enforcement. It runs only as the child process that
control_graph.py launches with the locked runtime's own interpreter (`python -I -B`), in an empty
working directory with a fixed environment, and it is never imported by enforcement code.

One exchange per process: read one veldo.graph/v1 request on stdin, write one response on
stdout. The graph is nonpersistent (Release 1): no checkpointer, no database, no store handle or
path. A cycle that needs supplied results stops with outcome `suspended` and hands the caller a
closed resume value {position, step, notes as canonical JSON text}; `advance` rebuilds the graph
and enters it at that position with the accepted snapshot and supplied results. Every operation
executes the compiled graph: `suspend` and `cancel` enter its control nodes. The answer's runtime
label is produced by the nodes that ran (executed_by, only callable inside a running graph);
an answer where nothing ran says NO_RUNTIME. Veldo owns every identity.

A workflow is {'version': int, 'entry': node, 'nodes': {name: function}}. A node receives a
plain view {identity, snapshot, supplied_results, notes, step} and returns a mapping with only
these keys: `next` (a node name, or None to end), `suspend` (true: stop for supplied results and
resume at `next`), `proposals` (typed proposal mappings), `failure` ({code, detail}) and `notes`
(graph working data). Any other key is an untyped assertion and ends the cycle as the named
failure node_failed: a graph proposes, it never asserts admission, priority or completion.
Nothing leaves this process that is not exact plain JSON data; LangGraph objects never cross.

Workflow definitions are supplied by VELDO-0132; this module registers none, so production
`main` answers every workflow with the named failure unsupported_workflow.

PARALLEL BRANCHES (VELDO-0247). A node may suspend with `next` a mapping {branch: node}: a fan-out. The
cycle then suspends at PARALLEL with notes {branches: {branch: {position, last}}, join} (the node names
its join in its notes). An exchange entered at PARALLEL is one superstep of branches: the PARALLEL node
starts every branch that has not reached the join through LangGraph's Send, so they all run in the same
superstep, each in its own branch state merged by a reducer so no branch overwrites another; COLLECT
then gathers them, counts one step for each branch node that moved, and suspends at PARALLEL again. A
branch node always suspends: it moves to its next node, or stays (its input is not here yet). The join
node runs only when every branch has reached it; it then runs as an ordinary node.
"""
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


def notes_text(notes):
    """Graph working data crosses the boundary as canonical JSON text, never as a structure."""
    return json.dumps(plain_copy(notes, 'notes'), sort_keys=True, separators=(',', ':'), allow_nan=False)


NO_RUNTIME = {'name': 'none', 'version': ''}
CONTROL = {'suspend': 'veldo_suspend', 'cancel': 'veldo_cancel'}
PARALLEL = 'veldo_parallel'
COLLECT = 'veldo_collect'
MAX_BRANCHES = 8


def _reply(request, outcome, runtime, **fields):
    """`runtime` is what executed: the label a LangGraph node produced, or NO_RUNTIME."""
    reply = {key: request[key] for key in ('schema', 'operation') + IDENTITY}
    reply.update(outcome=outcome, runtime=runtime)
    reply.update(fields)
    return reply


def _failure(request, code, detail, runtime=NO_RUNTIME):
    return _reply(request, 'failure', runtime, failure={'code': code, 'detail': detail[:500]})


def closed(reply):
    """The answer as exact plain data, with the graph's notes turned into text."""
    body = plain_copy(reply)
    if 'resume' in body:
        body['resume'] = dict(body['resume'], notes=notes_text(body['resume']['notes']))
    return body


def emit(request, reply, stdout):
    try:
        body = json.dumps(closed(reply), allow_nan=False)
    except NotPlain as error:
        body = json.dumps(_failure(request, 'node_failed', str(error), reply.get('runtime', NO_RUNTIME)),
                          allow_nan=False)
    stdout.write(body)


def _resume(request, workflow):
    resume = request.get('resume')
    if (type(resume) is not dict or set(resume) != {'position', 'step', 'notes'}
            or (resume['position'] not in workflow['nodes'] and resume['position'] != PARALLEL)
            or type(resume['step']) is not int
            or type(resume['notes']) is not str):
        return None
    try:
        notes = json.loads(resume['notes'])
    except ValueError:
        return None
    if type(notes) is not dict:
        return None
    return dict(resume, notes=notes)


def executed_by():
    """The runtime label, produced only from inside a running LangGraph graph: get_config()
    raises outside one, and the version is the running langgraph package's own."""
    from langgraph.config import get_config
    from langgraph.version import __version__
    get_config()
    return {'name': 'langgraph', 'version': __version__}


def _merge_branches(old, new):
    """The reducer of branch state: each branch writes only its own key, so none overwrites another."""
    return dict(old or {}, **(new or {}))


def _latest(old, new):
    return new


def _branch_set(notes, workflow):
    """The plain branch positions and join a PARALLEL resume carries, or None."""
    branches, join = notes.get('branches'), notes.get('join')
    if (type(branches) is not dict or not 2 <= len(branches) <= MAX_BRANCHES or join not in workflow['nodes']
            or not all(type(b) is dict and b.get('position') in workflow['nodes'] for b in branches.values())):
        return None
    return branches, join


def _build(workflow):
    from typing import Annotated, TypedDict
    from langgraph.config import get_config
    from langgraph.graph import END, START, StateGraph
    from langgraph.types import Command, Send

    class State(TypedDict, total=False):
        identity: dict
        operation: str
        snapshot: dict
        supplied_results: list
        position: str
        step: int
        notes: dict
        proposals: list
        halt: str
        failure: dict
        executed_by: Annotated[dict, _latest]
        branch: str
        branches: Annotated[dict, _merge_branches]

    def branch_node(name, function, state):
        """One branch's node, in the superstep every started branch shares: it writes only its own branch."""
        branch = state['branch']
        view = {'identity': state['identity'], 'snapshot': state['snapshot'],
                'supplied_results': state['supplied_results'], 'notes': dict(state['notes']),
                'step': state['step'], 'branch': branch}
        out = function(view)
        entry = {'superstep': get_config()['metadata'].get('langgraph_step')}
        if type(out) is not dict or sorted(set(out) - set(NODE_KEYS)):
            entry['failure'] = {'code': 'node_failed', 'detail': name + ' returned no node output mapping'}
        elif out.get('failure') is not None:
            entry['failure'] = out['failure']
        elif (not out.get('suspend') or out.get('proposals') or type(out.get('next')) is not str
              or out['next'] not in workflow['nodes']):
            entry['failure'] = {'code': 'node_failed', 'detail': name + ' did not suspend at one node in its branch'}
        else:
            notes = out.get('notes') or {}
            entry.update(position=out['next'], last=notes.get('last'),
                         **({'decision': notes['decision']} if 'decision' in notes else {}))
        return Command(goto=COLLECT, update={'branches': {branch: entry}, 'executed_by': executed_by()})

    def wrap(name, function):
        def node(state):
            if state.get('branch'):
                return branch_node(name, function, state)
            view = {'identity': state['identity'], 'snapshot': state['snapshot'],
                    'supplied_results': state['supplied_results'], 'notes': dict(state['notes']),
                    'step': state['step']}
            out = function(view)
            base = {'step': state['step'] + 1, 'position': name, 'executed_by': executed_by()}
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
            if type(following) is dict:
                # A fan-out: every branch starts at its first node in the next exchange's one superstep.
                if (not out.get('suspend') or update['proposals'] or not 2 <= len(following) <= MAX_BRANCHES
                        or not all(target in workflow['nodes'] for target in following.values())):
                    return Command(goto=END, update=dict(update, halt='failure', failure={
                        'code': 'unsupported_workflow', 'detail': name + ' fans out to no bounded set of nodes'}))
                notes = dict(update['notes'], branches={b: {'position': t, 'last': None}
                                                        for b, t in sorted(following.items())})
                return Command(goto=END, update=dict(update, notes=notes, halt='suspend', position=PARALLEL))
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

    def parallel(state):
        """Start every branch that has not reached the join, all in one superstep; or, when every branch has
        reached it, the join."""
        found = _branch_set(state['notes'], workflow)
        if found is None:
            return Command(goto=END, update={'halt': 'failure', 'executed_by': executed_by(), 'failure': {
                'code': 'invalid_input', 'detail': 'the resume carries no plain branch set'}})
        branches, join = found
        if all(b['position'] == join for b in branches.values()):
            return Command(goto=join, update={'position': join, 'executed_by': executed_by()})
        view = {key: state[key] for key in ('identity', 'snapshot', 'supplied_results', 'notes', 'step')}
        return Command(goto=[Send(b['position'], dict(view, branch=name)) for name, b in sorted(branches.items())
                             if b['position'] != join], update={'executed_by': executed_by()})

    def collect(state):
        """Gather the superstep's branches: a failure ends the cycle, else every branch's position and the step
        it moved, one step for each branch node that moved, and the cycle suspends at PARALLEL again."""
        ran, (branches, join) = state.get('branches') or {}, _branch_set(state['notes'], workflow)
        failed = sorted((b, e['failure']) for b, e in ran.items() if 'failure' in e)
        if failed:
            branch, failure = failed[0]
            return Command(goto=END, update={'halt': 'failure', 'executed_by': executed_by(), 'failure': dict(
                failure, detail=str(failure.get('detail', '')))})
        after, moved = {}, 0
        for name, prior in sorted(branches.items()):
            entry = ran.get(name)
            if entry is None:
                after[name] = {'position': prior['position'], 'last': None}
                continue
            after[name] = entry
            moved += entry.get('last') is not None
        return Command(goto=END, update={'halt': 'suspend', 'position': PARALLEL, 'step': state['step'] + moved,
                                         'notes': dict(state['notes'], branches=after), 'executed_by': executed_by()})

    def hold(state):
        # suspend: the cycle stays at its position; the graph ran and says so.
        return Command(goto=END, update={'halt': 'suspend', 'executed_by': executed_by()})

    def cancel(state):
        return Command(goto=END, update={'halt': 'canceled', 'executed_by': executed_by()})

    graph = StateGraph(State)
    for name, function in workflow['nodes'].items():
        graph.add_node(name, wrap(name, function))
    graph.add_node(CONTROL['suspend'], hold)
    graph.add_node(CONTROL['cancel'], cancel)
    graph.add_node(PARALLEL, parallel)
    graph.add_node(COLLECT, collect)
    graph.add_conditional_edges(START, lambda state: CONTROL.get(state['operation'], state['position']),
                                list(workflow['nodes']) + list(CONTROL.values()) + [PARALLEL])
    return graph.compile()


def run_cycle(request, workflow, resume):
    """Every operation executes the compiled graph: start and advance enter it at the cycle's
    position, suspend and cancel enter its control nodes."""
    try:
        from langgraph.errors import GraphRecursionError
    except ImportError:
        return _failure(request, 'node_failed', 'the LangGraph runtime cannot be imported')
    state = {'identity': {key: request[key] for key in IDENTITY}, 'operation': request['operation'],
             'snapshot': request.get('snapshot'), 'supplied_results': request.get('supplied_results', []),
             'proposals': [], 'halt': '', 'position': resume['position'], 'step': resume['step'],
             'notes': resume['notes'], 'branches': {}}
    try:
        final = _build(workflow).invoke(state, {'recursion_limit': MAX_STEPS})
    except GraphRecursionError:
        return _failure(request, 'node_failed', 'the cycle exceeded its step bound')
    except Exception as error:  # a node's own exception is that node's failure, by name
        return _failure(request, 'node_failed', 'node raised ' + type(error).__name__)
    label = final.get('executed_by')
    if type(label) is not dict:
        return _failure(request, 'node_failed', 'no LangGraph node executed')
    if final.get('halt') == 'failure':
        failure = final.get('failure')
        if type(failure) is not dict or failure.get('code') not in (
                'invalid_input', 'missing_evidence', 'node_failed', 'unsupported_workflow'):
            return _failure(request, 'node_failed', 'a node failed without a named code', label)
        return _reply(request, 'failure', label, failure={'code': failure['code'],
                                                          'detail': str(failure.get('detail', ''))[:500]})
    if final.get('halt') == 'canceled':
        return _reply(request, 'canceled', label)
    if final.get('halt') == 'suspend':
        return _reply(request, 'suspended', label, resume={'position': final['position'],
                                                           'step': final['step'], 'notes': final['notes']})
    if final.get('halt') == 'end' and final.get('proposals'):
        return _reply(request, 'proposal', label, proposals=final['proposals'])
    return _failure(request, 'missing_evidence', 'the cycle ended without a proposal', label)


def answer(request, workflows):
    workflow = workflows.get(request['workflow']['id'])
    if (workflow is None or workflow['version'] != request['workflow']['version']
            or set(workflow['nodes']) & (set(CONTROL.values()) | {PARALLEL, COLLECT})):
        return _failure(request, 'unsupported_workflow', 'no registered workflow ' +
                        request['workflow']['id'] + ' version ' + str(request['workflow']['version']))
    if request['operation'] == 'start':
        return run_cycle(request, workflow, {'position': workflow['entry'], 'step': 0, 'notes': {}})
    resume = _resume(request, workflow)
    if resume is None:
        return _failure(request, 'invalid_input', 'resume is not this workflow\'s plain position')
    return run_cycle(request, workflow, resume)


def serve(workflows, stdin=None, stdout=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    request = json.loads(stdin.buffer.read() if hasattr(stdin, 'buffer') else stdin.read())
    emit(request, answer(request, workflows), stdout)
    return 0


if __name__ == '__main__':
    sys.exit(serve(WORKFLOWS))
