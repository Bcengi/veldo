"""Veldo's own step runner behind the plain-data graph adapter (VELDO-0043, VELDO-0262).

This file is the execution environment, not enforcement. It runs only as the child process that
control_graph.py launches with the resolved base interpreter (`python -I -S -B`), in an empty working
directory with a fixed environment, and it is never imported by enforcement code. Standard library
only: under -S not even site packages are importable in the child.

One exchange per process: read one veldo.graph/v1 request on stdin, write one response on stdout.
Nonpersistent (Release 1): no checkpoint, no database, no store handle or path. A cycle that needs
supplied results stops with outcome `suspended` and hands the caller a closed resume value
{position, step, notes as canonical JSON text}; `advance` enters the workflow at that position with
the accepted snapshot and supplied results. Every operation runs the step loop: `suspend` and `cancel`
run its control steps. The answer's runtime label (executed_by) is produced by the step loop after a
node ran; an answer where nothing ran says NO_RUNTIME. Veldo owns every identity.

A workflow is {'version': int, 'entry': node, 'nodes': {name: function}}. A node receives a plain view
{identity, snapshot, supplied_results, notes, step} and returns a mapping with only these keys: `next`
(a node name, or None to end), `suspend` (true: stop for supplied results and resume at `next`),
`proposals` (typed proposal mappings), `failure` ({code, detail}) and `notes` (working data). Any other
key is an untyped assertion and ends the cycle as the named failure node_failed: a workflow proposes,
it never asserts admission, priority or completion. Nothing leaves this process that is not exact
plain JSON data.

NO MUTABLE MODULE STATE. Each exchange's position, step count, notes, proposals and label live in one
Exchange object. WORKFLOWS holds what a splice registers before the entry point (the project pipeline,
the runtime qualification) and is never written by an exchange; a workflow revision is spliced as one
constant literal (control_workflow_steps.py) and built per exchange. Deterministic: no clock,
randomness, thread or environment read, branches in sorted name order, the same request bytes give the
same answer bytes. One exchange runs at most MAX_STEPS steps (supersteps), counted from the first.

PARALLEL BRANCHES (VELDO-0247). A node may suspend with `next` a mapping {branch: node}: a fan-out. The
cycle then suspends at PARALLEL with notes {branches: {branch: {position, last}}, join} (the node names
its join in its notes). An exchange entered at PARALLEL is one superstep of branches: every branch that
has not reached the join runs its one node, each against the same pre-superstep state and a private copy
of its view, writing only its own entry; the entries are merged after all have run, one step is counted
for each branch node that moved, and the cycle suspends at PARALLEL again. A branch node always
suspends: it moves to its next node, or stays (its input is not here yet). The join node runs only when
every branch has reached it; it then runs as an ordinary node.
"""
import copy
import json
import math
import sys

SCHEMA = 'veldo.graph/v1'
VERSION = '1.0'
IDENTITY = ('cycle_id', 'command_id', 'domain_uuid', 'repository_uuid')
NODE_KEYS = ('next', 'suspend', 'proposals', 'failure', 'notes')
MAX_STEPS = 64
WORKFLOWS = {}


class NotPlain(Exception):
    pass


class StepBound(Exception):
    pass


def plain_copy(value, where='value'):
    """Exact JSON types only; a tuple, an object or a subclass is not plain data."""
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
    """Working data crosses the boundary as canonical JSON text, never as a structure."""
    return json.dumps(plain_copy(notes, 'notes'), sort_keys=True, separators=(',', ':'), allow_nan=False)


NO_RUNTIME = {'name': 'none', 'version': ''}
CONTROL = {'suspend': 'veldo_suspend', 'cancel': 'veldo_cancel'}
PARALLEL = 'veldo_parallel'
COLLECT = 'veldo_collect'
MAX_BRANCHES = 8
FAILURES = ('invalid_input', 'missing_evidence', 'node_failed', 'unsupported_workflow')


def _reply(request, outcome, runtime, **fields):
    """`runtime` is what executed: the label the step loop produced, or NO_RUNTIME."""
    reply = {key: request[key] for key in ('schema', 'operation') + IDENTITY}
    reply.update(outcome=outcome, runtime=runtime)
    reply.update(fields)
    return reply


def _failure(request, code, detail, runtime=NO_RUNTIME):
    return _reply(request, 'failure', runtime, failure={'code': code, 'detail': detail[:500]})


def closed(reply):
    """The answer as exact plain data, with the notes turned into text."""
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


def _branch_set(notes, workflow):
    """The plain branch positions and join a PARALLEL resume carries, or None."""
    branches, join = notes.get('branches'), notes.get('join')
    if (type(branches) is not dict or not 2 <= len(branches) <= MAX_BRANCHES or join not in workflow['nodes']
            or not all(type(b) is dict and b.get('position') in workflow['nodes'] for b in branches.values())):
        return None
    return branches, join


class Exchange:
    """One exchange's whole state: position, step count, notes, proposals, outcome and label."""

    def __init__(self, request, workflow, resume):
        self.workflow = workflow
        self.identity = {key: request[key] for key in IDENTITY}
        self.operation = request['operation']
        self.snapshot = request.get('snapshot')
        self.supplied = request.get('supplied_results', [])
        self.position, self.step, self.notes = resume['position'], resume['step'], resume['notes']
        self.proposals, self.halt, self.failure, self.label, self.superstep = [], '', None, None, 0

    def ran(self):
        """The label, set by the step loop only after a node ran."""
        self.label = {'name': 'veldo-steps', 'version': VERSION}

    def end(self, halt, **fields):
        self.halt = halt
        for key, value in fields.items():
            setattr(self, key, value)
        return None

    def view(self):
        return {'identity': self.identity, 'snapshot': self.snapshot, 'supplied_results': self.supplied,
                'notes': dict(self.notes), 'step': self.step}

    def tick(self):
        self.superstep += 1
        if self.superstep > MAX_STEPS:
            raise StepBound()

    def run(self):
        target = CONTROL.get(self.operation, self.position)
        while target is not None:
            self.tick()
            if target == CONTROL['suspend']:
                target = self.end('suspend')
            elif target == CONTROL['cancel']:
                target = self.end('canceled')
            elif target == PARALLEL:
                target = self.parallel()
            else:
                target = self.node(target)
            self.ran()

    def node(self, name):
        """One ordinary node: its output routes the loop, suspends it or ends it."""
        out = self.workflow['nodes'][name](self.view())
        step = self.step + 1
        if type(out) is not dict:
            return self.end('failure', step=step, position=name, failure={
                'code': 'node_failed', 'detail': name + ' returned no node output mapping'})
        untyped = sorted(set(out) - set(NODE_KEYS))
        if untyped:
            return self.end('failure', step=step, position=name, failure={
                'code': 'node_failed', 'detail': name + ' returned an untyped assertion: ' + ', '.join(untyped)})
        if out.get('failure') is not None:
            return self.end('failure', step=step, position=name, failure=out['failure'])
        notes = dict(self.notes, **(out.get('notes') or {}))
        proposals = self.proposals + list(out.get('proposals') or [])
        self.step, self.position, self.notes, self.proposals = step, name, notes, proposals
        following = out.get('next')
        if type(following) is dict:
            # A fan-out: every branch starts at its first node in the next exchange's one superstep.
            if (not out.get('suspend') or proposals or not 2 <= len(following) <= MAX_BRANCHES
                    or not all(target in self.workflow['nodes'] for target in following.values())):
                return self.end('failure', failure={
                    'code': 'unsupported_workflow', 'detail': name + ' fans out to no bounded set of nodes'})
            branches = {b: {'position': t, 'last': None} for b, t in sorted(following.items())}
            return self.end('suspend', notes=dict(notes, branches=branches), position=PARALLEL)
        if following is not None and following not in self.workflow['nodes']:
            return self.end('failure', failure={
                'code': 'unsupported_workflow', 'detail': name + ' names no node ' + repr(following)})
        if out.get('suspend'):
            if following is None or proposals:
                return self.end('failure', failure={
                    'code': 'node_failed', 'detail': name + ' suspended without a resume node or with proposals'})
            return self.end('suspend', position=following)
        if following is None:
            return self.end('end')
        self.position = following
        return following

    def branch(self, name, branch, state):
        """One branch's node against the pre-superstep state, through a private copy of its view: it
        returns only its own entry."""
        view = dict(copy.deepcopy(state), branch=branch)
        out = self.workflow['nodes'][name](view)
        entry = {'superstep': self.superstep}
        if type(out) is not dict or sorted(set(out) - set(NODE_KEYS)):
            entry['failure'] = {'code': 'node_failed', 'detail': name + ' returned no node output mapping'}
        elif out.get('failure') is not None:
            entry['failure'] = out['failure']
        elif (not out.get('suspend') or out.get('proposals') or type(out.get('next')) is not str
              or out['next'] not in self.workflow['nodes']):
            entry['failure'] = {'code': 'node_failed', 'detail': name + ' did not suspend at one node in its branch'}
        else:
            notes = out.get('notes') or {}
            entry.update(position=out['next'], last=notes.get('last'),
                         **({'decision': notes['decision']} if 'decision' in notes else {}))
        return entry

    def parallel(self):
        """Every branch that has not reached the join runs its one node in one superstep, then the entries
        are merged; or, when every branch has reached it, the join runs."""
        found = _branch_set(self.notes, self.workflow)
        if found is None:
            return self.end('failure', failure={'code': 'invalid_input',
                                                'detail': 'the resume carries no plain branch set'})
        branches, join = found
        if all(b['position'] == join for b in branches.values()):
            self.position = join
            return join
        self.ran()
        self.tick()
        state = self.view()
        ran = {}
        for name, prior in sorted(branches.items()):
            if prior['position'] != join:
                ran[name] = self.branch(prior['position'], name, state)
        self.ran()
        self.tick()
        failed = sorted((b, e['failure']) for b, e in ran.items() if 'failure' in e)
        if failed:
            failure = failed[0][1]
            return self.end('failure', failure=dict(failure, detail=str(failure.get('detail', ''))))
        after, moved = {}, 0
        for name, prior in sorted(branches.items()):
            entry = ran.get(name)
            if entry is None:
                after[name] = {'position': prior['position'], 'last': None}
                continue
            after[name] = entry
            moved += entry.get('last') is not None
        return self.end('suspend', position=PARALLEL, step=self.step + moved,
                        notes=dict(self.notes, branches=after))


def run_cycle(request, workflow, resume):
    """Every operation runs the step loop: start and advance enter it at the cycle's position, suspend
    and cancel at its control steps."""
    exchange = Exchange(request, workflow, resume)
    try:
        exchange.run()
    except StepBound:
        return _failure(request, 'node_failed', 'the cycle exceeded its step bound')
    except Exception as error:  # a node's own exception is that node's failure, by name
        return _failure(request, 'node_failed', 'node raised ' + type(error).__name__)
    label = exchange.label
    if type(label) is not dict:
        return _failure(request, 'node_failed', 'no step executed')
    if exchange.halt == 'failure':
        failure = exchange.failure
        if type(failure) is not dict or failure.get('code') not in FAILURES:
            return _failure(request, 'node_failed', 'a node failed without a named code', label)
        return _reply(request, 'failure', label, failure={'code': failure['code'],
                                                          'detail': str(failure.get('detail', ''))[:500]})
    if exchange.halt == 'canceled':
        return _reply(request, 'canceled', label)
    if exchange.halt == 'suspend':
        return _reply(request, 'suspended', label, resume={'position': exchange.position,
                                                           'step': exchange.step, 'notes': exchange.notes})
    if exchange.halt == 'end' and exchange.proposals:
        return _reply(request, 'proposal', label, proposals=exchange.proposals)
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


def workflows():
    """The workflows this runner answers: what a splice registered before the entry point."""
    return WORKFLOWS


def serve(workflows, stdin=None, stdout=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    request = json.loads(stdin.buffer.read() if hasattr(stdin, 'buffer') else stdin.read())
    emit(request, answer(request, workflows), stdout)
    return 0


if __name__ == '__main__':
    sys.exit(serve(workflows()))
