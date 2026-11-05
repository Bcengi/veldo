"""Workflow cycles: each LangGraph cycle executes one exact accepted revision, and every step it takes
acts only through ordinary proposals and eligibility checks (PLAN-0019 W95, VELDO-0132 AC2, AC4).
Standard library only; the graph runs in the isolated runtime, never in this process.

BINDING. Cycles.start() commits record_workflow_cycle, whose transition reads the workflow's head
INSIDE the store's transaction and pins that exact revision into the new cycle record: {id, version,
digest (the definition digest), revision, entity digest}, with the cycle's subject (an execution
unit) and its accepted VELDO-0035 snapshot {id, version, digest}. The transition refuses any later
record of the cycle whose binding, subject or snapshot differs (workflow_immutable:binding), so a
revision saved while the cycle runs changes nothing it executes. Every exchange of the cycle is built
from the bound revision's stored bytes, re-read and re-verified from the store each time.

THE RUNNER. runner_source() is the production runner (control_graph_langgraph.py) with the step
kinds (control_workflow_langgraph.py) and exactly one registration spliced before its entry point:
the bound definition's canonical text and version. Nothing else of the canvas document reaches it:
the layout never does. The actual LangGraph runtime executes it through the VELDO-0043 adapter,
activated first through VELDO-0045 (control_runtime.activation), and every answer must carry that
locked LangGraph's label.

ONE STEP PER EXCHANGE, EACH JUDGED. start runs the intake, which must report the bound digest. Then,
node by node, this service decides whether the next step may run and supplies only what the node's
kind reads, as plain versioned data read from the store (never text a caller writes):

  budget        a cycle that has taken budget.steps steps runs no more (budget_exceeded:steps), and
                a transition taken more often than its `max` ends it (budget_exceeded:loop/<id>)
  subject       the execution unit, current version, supplied to every step
  owner_wait    waits (runs nothing) until admission:<unit> is accepted or declined, then routes
  assignment    before waiting for a worker, the ORDINARY checks: the role configuration the bound
                definition names is current at its referenced version and digest, its principal is
                an active member of a type the assignment_acceptance boundary admits, scoped to the
                repository (authority_contract, control_membership), its tool references are
                current, and the eligibility Gate's selection decision for the unit is eligible.
                Any refusal ends the cycle by name. The worker result it then waits for must be an
                accepted proof bundle for the unit (kind proof_bundle); dispatching the worker is the
                floor's (VELDO-0039, VELDO-0049), under its own registered station decisions.
  result        the result handling node is supplied the accepted result the cycle received, re-read
                and required unchanged; its completion proposal must cite that result and nothing
                it was not supplied (missing_evidence:completion otherwise)

Every suspension must carry the bound {id, version, digest} (missing_evidence:binding) and a step
[node, port, next] that is a transition of the bound definition from the position that was run
(invalid_response:trace). An accepted proposal is RECORDED in the cycle as pending for its owning
authority; completion is only ever the completion reader's (control_eligibility.Gate.completion over
stored receipts). This module writes one entity kind, its own cycle records; no step writes domain
state.

OBSERVABILITY. Every operation is reported to `observe` with operation, domain, repository, actor,
cycle, subject, bound workflow, record identity, graph command, runtime label, outcome, named refusal
and its taxonomy class. status() counts accepted and refused operations and names the pending work:
each waiting cycle with the node and input it waits for.

CHECKS AND PARALLEL BRANCHES (VELDO-0247). A check node is supplied `fields`, the values of the
definition's declared fields read from the store (the subject's record, or the accepted result an
assignment on every path before it routed on). The runner reports the branch with its decision; this
service evaluates the same rule on the same values against the bound revision (control_workflow
.evaluate) and refuses any difference (unsupported_workflow:branch_mismatch) before anything follows,
so the runner never chooses the route; a field with no value or the wrong type fails the step
(invalid_input:field_unsupplied:<field>). The record's `decisions` and the `check` event hold the node,
branch, rule and every condition with its observed value (a private field's as its digest).
A fan-out suspends at PARALLEL with one branch per transition of its port; the record's `block` holds
each branch's position, input and arrival. Each exchange is one LangGraph superstep of branches: every
branch with what it needs runs, all in that superstep, and every branch's transition is judged as a
main-path step is; an assignment branch is dispatched (its ordinary checks, then waiting) without
waiting for another. The join runs only when every branch has reached it. The step budget counts
every node of every branch, and a superstep whose branches would take the cycle past budget.steps is
refused (budget_exceeded:steps) before any of them starts.

NOT HERE: checkpoint recovery and resuming a cycle after a crash (Release 2); a cycle whose exchange
fails is refused, never retried. The dispatcher's use of a pending assignment is the floor's.
"""
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import time

HERE = Path(__file__).resolve().parent
SCHEMA = 'veldo.workflow_cycle/v1'
CYCLE_KIND = 'workflow_cycle'
RECORD = 'record_workflow_cycle'
OWNER = 'VELDO-0132 workflow cycles'
WRITES = ('entities', 'journal', 'commands', 'nonces')
RUNNER = 'control_graph_langgraph.py'
STEPS = 'control_workflow_langgraph.py'
GUARD = "\nif __name__ == '__main__':\n"
INTAKE = 'veldo_intake'
STATES = ('running', 'waiting', 'proposed', 'refused', 'canceled')
FINAL = ('proposed', 'refused', 'canceled')
PINNED = ('schema', 'domain', 'repository', 'cycle', 'workflow', 'subject', 'binding', 'snapshot', 'started')
RUNNER_TYPES = ('service',)
RESULT_KIND = 'proof_bundle'
ANSWERS = ('accepted', 'declined')
STATION = 'selection'
PARALLEL = 'veldo_parallel'
MISMATCH = 'unsupported_workflow:branch_mismatch'


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, HERE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WF = _sibling('veldo_workflow_cycle_definitions', 'control_workflow.py')
Refused = WF.Refused
_ORGANS = {}
TAXONOMY = dict(WF.TAXONOMY, node_failed='unknown_outcome', unsupported_workflow='unsupported_configuration',
                invalid_response='missing_evidence', unknown_outcome='unknown_outcome', blocked='unauthorized',
                draft_plan='unauthorized', stale_scope='stale_version', stale_input='stale_version',
                unresolved_dependency='missing_evidence', unresolved_decision='unauthorized')


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _organ(name):
    if name not in _ORGANS:
        _ORGANS[name] = _sibling('veldo_%s_workflow_cycle' % name, name + '.py')
    return _ORGANS[name]


def record_id(domain, repository, cycle):
    return 'workflow-cycle:' + json.dumps([domain, repository, cycle], separators=(',', ':'))


def _entity_row(conn, identity):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    return None if row is None else {'id': identity, 'kind': row[0], 'version': row[1], 'digest': row[2],
                                     'data': json.loads(row[3])}


def _unit_identifier(value):
    """What the graph adapter accepts as a subject or supplied identity."""
    return (type(value) is str and 0 < len(value) <= 200 and '/' not in value and '\\' not in value
            and '..' not in value and all(32 <= ord(c) < 127 for c in value))


def _member(conn, principal, types, repository, now):
    """None when `principal` is an active member of one of `types` scoped to `repository`, else why."""
    AC, CM = _organ('authority_contract'), _organ('control_membership')
    row = _entity_row(conn, principal) if type(principal) is str and principal else None
    if row is None or row['kind'] != 'membership':
        return 'unknown_principal'
    entry = dict(row['data'], principal=principal)
    active, why = AC.active_member(entry, now)
    if not active:
        return why
    if entry.get('principal_type') not in types:
        return 'principal_type_not_admitted'
    return None if CM.scope_covers(entry.get('scope'), repository) else 'scope_not_covered'


def _record_transition(conn, params, before):
    """THE CYCLE RECORD: created with the head revision pinned; every later version keeps it."""
    domain, repository, cycle = params.get('domain'), params.get('repository'), params.get('cycle')
    if not all(type(v) is str and v for v in (domain, repository)) or not WF._identifier(cycle):
        raise Refused('invalid_input', 'domain, repository and cycle are named')
    now = params.get('now')
    if not isinstance(now, (int, float)) or _member(conn, params.get('principal'), RUNNER_TYPES, repository, now):
        raise Refused('missing_authority:principal', 'not an active service member for this repository')
    cid = record_id(domain, repository, cycle)
    prior = _entity_row(conn, cid)
    if params.get('action') == 'start':
        if prior is not None:
            raise Refused('invalid_input:cycle_exists', cid)
        workflow, subject, snapshot = params.get('workflow'), params.get('subject'), params.get('snapshot')
        version = WF.head_version(conn, domain, repository, workflow) if WF._identifier(workflow) else 0
        if not version:
            raise Refused('missing_workflow', str(workflow))
        store = _organ('control_store')
        row, data = WF.verified_revision(store, conn, domain, repository, workflow, version)
        unit = _entity_row(conn, subject) if _unit_identifier(subject) else None
        if unit is None or unit['kind'] != 'execution_unit' or unit['data'].get('repository_uuid') != repository:
            raise Refused('missing_evidence:subject', str(subject))
        SN = _organ('control_snapshot')
        reference = snapshot if type(snapshot) is dict else {}
        try:
            held = SN.entity(store, conn, reference.get('id')) if type(reference.get('id')) is str else None
            SN.load(store, conn, reference.get('id'), domain, repository)
        except SN.Refused as error:
            raise Refused('missing_evidence:snapshot', error.code) from error
        if held is None or (held['version'], held['digest']) != (reference.get('version'), reference.get('digest')):
            raise Refused('missing_evidence:snapshot', 'the snapshot reference is not the accepted record')
        record = {'schema': SCHEMA, 'domain': domain, 'repository': repository, 'cycle': cycle, 'workflow': workflow,
                  'subject': subject, 'snapshot': {k: reference[k] for k in ('id', 'version', 'digest')},
                  'binding': {'id': workflow, 'version': version, 'digest': data['definition_digest'],
                              'revision': row['id'], 'entity_digest': row['digest']},
                  'started': {'principal': params['principal'], 'at': now},
                  'state': 'running', 'position': None, 'steps': 0, 'trace': [], 'visits': {}, 'resume': None,
                  'waiting': None, 'assignment': None, 'received': None, 'result': None, 'answered': None,
                  'proposals': [], 'refusal': None, 'block': None, 'decisions': [], 'results': {},
                  'refusals': [], 'exchanges': 0}
        return {cid: {'kind': CYCLE_KIND, 'data': record}}
    record = params.get('record')
    if prior is None or prior['kind'] != CYCLE_KIND:
        raise Refused('missing_evidence:cycle', cid)
    old = prior['data']
    if old.get('state') in FINAL:
        raise Refused('invalid_input:cycle_final', cid)
    if type(record) is not dict or any(record.get(k) != old.get(k) for k in PINNED):
        raise Refused('workflow_immutable:binding', 'a cycle keeps the revision, subject and snapshot it started with')
    if (record.get('state') not in STATES or type(record.get('trace')) is not list
            or record['trace'][:len(old['trace'])] != old['trace'] or record.get('steps', -1) < old['steps']):
        raise Refused('invalid_input:cycle_record', cid)
    return {cid: {'kind': CYCLE_KIND, 'data': record}}


def installed_runtime(home=None, stage=None):
    """The activated LangGraph runtime (VELDO-0045), with `stage` replacing the account stage."""
    report = _organ('control_runtime').activation(home)
    if report['outcome'] != 'accepted':
        raise Refused('unavailable_service:runtime', '; '.join(report['problems'][:4]))
    runtime = _organ('control_graph').resolve_runtime(home)
    if runtime is None:
        raise Refused('unavailable_service:runtime', 'no runtime is installed')
    return dict(runtime, stage=str(stage)) if stage is not None else runtime


def runner_source(revision):
    """The production runner with the step kinds and exactly one revision registered before its entry
    point: the stored definition's canonical text and version, and nothing else of the document."""
    source = (HERE / RUNNER).read_text()
    if source.count(GUARD) != 1:
        raise Refused('unavailable_service:runner', 'the runner has no single entry point to register before')
    text = WF.canonical(revision['definition']).decode()
    block = '\n' + (HERE / STEPS).read_text() + '\nveldo_register_workflow(%r, %d)\n' % (text, revision['version'])
    return source.replace(GUARD, block + GUARD, 1)


class Cycles:
    """Workflow cycles of one domain and repository over a real control store connection. `workflows`
    is the revision service (control_workflow.Workflows) on the same connection; `gate` is the
    eligibility Gate, built by the caller over the workspace (control_eligibility.Gate(...,
    workspace=...)); `principal` is the active service member running cycles."""

    def __init__(self, store, conn, workflows, *, gate, principal, signer, sign, generation=1, runtime=None,
                 home=None, stage=None, timeout=120, observe=None, clock=None):
        self.store, self.conn, self.workflows, self.gate = store, conn, workflows, gate
        self.domain, self.repository = workflows.domain, workflows.repository
        if getattr(gate, 'domain_uuid', None) != self.domain or getattr(gate, 'repository_uuid', None) != self.repository:
            raise Refused('invalid_input', 'the Gate decides another domain or repository')
        self.principal, self.signer, self.sign, self.generation = principal, signer, sign, generation
        self._runtime, self.home, self.stage, self.timeout = runtime, home, stage, timeout
        self.observe = observe or (lambda event: None)
        self.clock = clock or time.time
        self.counts = {'accepted': 0, 'refused': 0}
        # VELDO-0247: checks by node and branch (otherwise on its own), fan-outs by width, branches running at
        # once, joins waiting and their wait time, and branch decisions refused as mismatches.
        self.metrics = {'checks': {}, 'otherwise': {}, 'fan_outs': {}, 'branches_running': {}, 'joins_waiting': {},
                        'join_wait_seconds': [], 'branch_mismatch': 0}
        # Diagnostics only, bounded: the durable log is the observe callback's sink.
        self.observations = collections.deque(maxlen=1000)
        store.declare_owners(conn, OWNER, kinds={CYCLE_KIND: (RECORD,)}, module=__file__)
        conn.command_registry[RECORD] = {'transaction_transition': _record_transition, 'writes': WRITES}

    # -- store ------------------------------------------------------------------------------------

    def record(self, cycle):
        row = _entity_row(self.conn, record_id(self.domain, self.repository, cycle))
        return dict(row['data']) if row and row['kind'] == CYCLE_KIND else None

    def _commit(self, cycle, params):
        cid = record_id(self.domain, self.repository, cycle)
        params = dict(params, domain=self.domain, repository=self.repository, cycle=cycle,
                      principal=self.principal, now=self.clock())
        command_id = 'workflow/cycle/' + hashlib.sha256(WF.canonical(params)).hexdigest()[:32]
        prior = _entity_row(self.conn, cid)
        command = {'command_id': command_id, 'principal': self.principal, 'operation': RECORD, 'parameters': params,
                   'expected_versions': {cid: prior['version'] if prior else 0}, 'artifact_digests': [],
                   'nonce': command_id + '/nonce'}
        try:
            result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except self.store.StoreRefused as error:
            raise Refused(error.code, error.detail) from error
        return result

    def _event(self, operation, record, **fields):
        binding = (record or {}).get('binding') or {}
        return dict({'schema': SCHEMA, 'operation': operation, 'domain': self.domain, 'repository': self.repository,
                     'actor': self.principal, 'cycle': (record or {}).get('cycle'), 'subject': (record or {}).get('subject'),
                     'workflow': {k: binding.get(k) for k in ('id', 'version', 'digest')} if binding else None,
                     'snapshot': (record or {}).get('snapshot'),
                     'record': record_id(self.domain, self.repository, (record or {}).get('cycle') or '-')}, **fields)

    def _report(self, event):
        outcome = 'refused' if event.get('refusal') else 'accepted'
        self.counts[outcome] += 1
        event = dict(event, outcome=outcome, taxonomy=taxonomy(event['refusal']) if event.get('refusal') else None)
        self.observations.append(event)
        self.observe(event)

    def _update(self, record, operation, **fields):
        result = self._commit(record['cycle'], {'action': 'update', 'record': record})
        self._report(self._event(operation, record, watermark=result['seq'], state=record['state'],
                                 steps=record['steps'], **fields))
        return record

    def _refuse(self, record, code, codes=None, **fields):
        record = dict(record, state='refused', refusal=code, refusals=list(codes or [code]), waiting=None)
        return self._update(record, 'refuse', refusal=code, refusals=record['refusals'], **fields)

    def _revision(self, record):
        """The bound revision, re-read from the store and verified: {definition, version, ...}."""
        binding = record['binding']
        row, data = WF.verified_revision(self.store, self.conn, self.domain, self.repository, binding['id'],
                                         binding['version'])
        if (row['id'], row['digest'], data['definition_digest']) != (binding['revision'], binding['entity_digest'],
                                                                     binding['digest']):
            raise Refused('missing_evidence:binding', 'the stored revision is not the one this cycle bound')
        return data

    # -- the graph --------------------------------------------------------------------------------

    def runtime(self):
        if self._runtime is None:
            self._runtime = installed_runtime(self.home, self.stage)
        return self._runtime

    def _exchange(self, record, revision, operation, **fields):
        """One exchange with the actual runtime, running this revision's own runner."""
        graph = _organ('control_graph')
        workflow = {k: record['binding'][k] for k in ('id', 'version', 'digest')}
        command = '%s.%d' % (record['cycle'], record['exchanges'] + 1)
        try:
            scratch = tempfile.TemporaryDirectory(prefix='veldo-workflow-runner-')
            runner = Path(scratch.name) / RUNNER
            runner.write_text(runner_source(revision))
        except OSError as error:
            raise Refused('unavailable_service:runner', error.strerror or type(error).__name__) from error
        with scratch:
            adapter = graph.Adapter(dict(self.runtime(), runner=str(runner)), self.domain, self.repository,
                                    self.timeout, evidence=graph.runtime_evidence())
            try:
                if operation == 'start':
                    answer = adapter.start(record['cycle'], command, record['snapshot'], workflow)
                elif operation == 'cancel':
                    answer = adapter.cancel(record['cycle'], command, workflow, record['resume'])
                else:
                    answer = adapter.advance(record['cycle'], command, record['snapshot'], workflow, record['resume'],
                                             fields['supplied'])
            except graph.Refused as error:
                code = 'unavailable_service:runtime' if error.code == 'runtime_unavailable' else error.code
                raise Refused(code, error.detail) from error
        record['exchanges'] += 1
        return answer, command

    @staticmethod
    def _notes(answer):
        try:
            notes = json.loads(answer['resume']['notes'])
        except (KeyError, TypeError, ValueError):
            return {}
        return notes if type(notes) is dict else {}

    def _supply(self, identity, row, value):
        return {'id': identity, 'version': row['version'], 'digest': row['digest'], 'value': value}

    # -- the ordinary checks ----------------------------------------------------------------------

    def role_problem(self, definition, node):
        """None when the assignment's role may take the unit's work now, else the named refusal."""
        AC = _organ('authority_contract')
        key = node['config']['role']
        ref = definition['references']['roles'][key]
        row = _entity_row(self.conn, ref['id'])
        if row is None or row['kind'] != WF.REFERENCE_KINDS['roles']:
            return 'missing_authority:role/' + key
        if (row['version'], row['digest']) != (ref['version'], ref['digest']):
            return 'stale_version:role/' + key
        for tool in node['config'].get('tools', []):
            tref = definition['references']['tools'][tool]
            trow = _entity_row(self.conn, tref['id'])
            if trow is None or (trow['kind'], trow['version'], trow['digest']) != (
                    WF.REFERENCE_KINDS['tools'], tref['version'], tref['digest']):
                return 'stale_version:tool/' + tool
        principal = row['data'].get('principal')
        if _member(self.conn, principal, AC.BOUNDARIES['assignment_acceptance'], self.repository, self.clock()):
            return 'missing_authority:role/' + key
        return None

    def _assignment(self, record, definition, node, position):
        """The ordinary checks before an assignment waits for a worker: role authority, then the Gate.
        Returns (assignment, None) or (None, (code, codes, fields))."""
        problem = self.role_problem(definition, node)
        if problem:
            return None, (problem, None, {'node': position})
        decision = self.gate.decide(STATION, record['subject'])
        if not decision['eligible']:
            return None, (decision['refusals'][0], decision['refusals'], {'node': position,
                                                                          'decision': decision['decision_id']})
        role = definition['references']['roles'][node['config']['role']]
        return {'node': position, 'role': node['config']['role'], 'configuration': dict(role), 'station': STATION,
                'decision': decision['decision_id'], 'watermark': decision['watermark']}, None

    def _assign(self, record, definition, node):
        # Through the class: a caller may drive this step with a stand-in holding only gate and role_problem.
        assignment, refusal = Cycles._assignment(self, record, definition, node, record['position'])
        if refusal:
            code, codes, fields = refusal
            return self._refuse(record, code, codes, **fields)
        record = dict(record, state='waiting', waiting={'node': record['position'], 'input': 'worker_result'},
                      assignment=assignment)
        return self._update(record, 'wait', node=record['position'], input='worker_result',
                            decision=assignment['decision'])

    def _result(self, identity):
        """An accepted result for the cycle's subject, or None."""
        row = _entity_row(self.conn, identity) if type(identity) is str else None
        return row

    def _accepted_result(self, record, row):
        data = row['data'] if row else {}
        return (row is not None and row['kind'] == RESULT_KIND and data.get('unit') == record['subject']
                and data.get('domain') == self.domain and data.get('repository') == self.repository)

    # -- the cycle --------------------------------------------------------------------------------

    def start(self, cycle, *, workflow, subject, snapshot):
        """Bind the workflow's current revision, then run the cycle until it waits, proposes or is
        refused. Returns the cycle record."""
        event = self._event('start', {'cycle': cycle, 'subject': subject}, requested=workflow)
        try:
            result = self._commit(cycle, {'action': 'start', 'workflow': workflow, 'subject': subject,
                                          'snapshot': snapshot})
        except Refused as error:
            self._report(dict(event, refusal=error.code))
            raise
        record = self.record(cycle)
        self._report(self._event('start', record, watermark=result['seq']))
        try:
            revision = self._revision(record)
            answer, command = self._exchange(record, revision, 'start')
        except Refused as error:
            return self._refuse(record, error.code)
        notes = self._notes(answer) if answer['outcome'] == 'suspended' else {}
        if answer['outcome'] != 'suspended' or answer['resume']['position'] != revision['definition']['entry']:
            return self._refuse(record, self._failure_code(answer, 'invalid_response:intake'), graph=command)
        if notes.get('workflow') != {k: record['binding'][k] for k in ('id', 'version', 'digest')}:
            return self._refuse(record, 'missing_evidence:binding', graph=command)
        record = dict(record, position=answer['resume']['position'], resume=answer['resume'])
        self._update(record, 'step', node=INTAKE, graph=command, runtime=answer['runtime'], executed=notes['workflow'])
        return self._run(record, revision)

    def advance(self, cycle, results=None):
        """Continue a waiting cycle once its input exists: for an assignment, `results` names the stored
        worker result {'worker_result': entity id}; an owner wait reads the admission record itself."""
        record = self.record(cycle)
        if record is None or record['state'] != 'waiting':
            error = Refused('invalid_input:not_waiting', str(cycle))
            self._report(dict(self._event('advance', record or {'cycle': cycle}), refusal=error.code))
            raise error
        try:
            revision = self._revision(record)
        except Refused as error:
            return self._refuse(record, error.code)
        if record['position'] == PARALLEL:
            # VELDO-0247: results for branches name the assignment node each is for: {node: entity id}.
            named = (results or {}).get('worker_result') or {}
            block = json.loads(json.dumps(record['block']))
            for node, identity in sorted(named.items() if type(named) is dict else ()):
                branch = next((b for b, st in block['branches'].items() if st['position'] == node
                               and st['waiting'] == 'worker_result'
                               and (st.get('assignment') or {}).get('node') == node), None)
                row = self._result(identity)
                if branch is None or not self._accepted_result(record, row):
                    return self._refuse(record, 'missing_evidence:result', node=node)
                block['branches'][branch]['received'] = {'id': identity, 'version': row['version'],
                                                         'digest': row['digest']}
            record = dict(record, block=block)
        elif record['waiting']['input'] == 'worker_result':
            identity = (results or {}).get('worker_result')
            row = self._result(identity)
            if not self._accepted_result(record, row):
                return self._refuse(record, 'missing_evidence:result', node=record['position'])
            record = dict(record, received={'id': identity, 'version': row['version'], 'digest': row['digest']})
        record = dict(record, state='running', waiting=None)
        return self._run(record, revision)

    def cancel(self, cycle):
        record = self.record(cycle)
        if record is None or record['state'] in FINAL:
            error = Refused('invalid_input:cycle_final', str(cycle))
            self._report(dict(self._event('cancel', record or {'cycle': cycle}), refusal=error.code))
            raise error
        graph = {}
        try:
            revision = self._revision(record)
            if record['resume'] is not None:
                answer, command = self._exchange(record, revision, 'cancel')
                if answer['outcome'] != 'canceled':
                    return self._refuse(record, self._failure_code(answer, 'invalid_response:cancel'), graph=command)
                graph = {'graph': command, 'runtime': answer['runtime']}
        except Refused as error:
            return self._refuse(record, error.code)
        return self._update(dict(record, state='canceled', waiting=None), 'cancel', **graph)

    @staticmethod
    def _failure_code(answer, default):
        failure = answer.get('failure') if answer.get('outcome') == 'failure' else None
        return failure['code'] + ':' + failure['detail'][:80] if failure else default

    def _inputs(self, record, node, kind):
        """The plain supplied results a node may read, from the store; None when it must wait."""
        unit = _entity_row(self.conn, record['subject'])
        if unit is None or unit['kind'] != 'execution_unit':
            raise Refused('missing_evidence:subject', record['subject'])
        supplied = [self._supply('subject', unit, {'unit': record['subject'], 'state': unit['data'].get('state')})]
        if kind['input'] == 'owner_answer':
            answer = _entity_row(self.conn, 'admission:' + record['subject'])
            data = answer['data'] if answer and answer['kind'] == 'admission' else {}
            if data.get('unit') != record['subject'] or data.get('state') not in ANSWERS:
                return None
            used = record.get('answered')
            if used is not None and answer['version'] <= used['version']:
                # Every visit to an owner wait needs an answer newer than the one this cycle last used.
                return None
            supplied.append(self._supply('owner_answer', answer, {'state': data['state']}))
        elif kind['input'] == 'worker_result':
            received = record.get('received')
            if not received or (record.get('assignment') or {}).get('node') != record['position']:
                return None
            row = self._result(received['id'])
            if not self._accepted_result(record, row) or (row['version'], row['digest']) != (received['version'],
                                                                                            received['digest']):
                raise Refused('missing_evidence:result', received['id'])
            supplied.append(self._supply('worker_result', row, {'kind': row['kind']}))
        elif kind['input'] == 'accepted_result':
            result = record.get('result')
            others = [(node, ref) for node, ref in sorted((record.get('results') or {}).items())
                      if ref != result]
            for name, result in ([('accepted_result', result)] if result else []) + [
                    ('accepted_result@' + node, ref) for node, ref in others]:
                row = self._result(result['id'])
                if not self._accepted_result(record, row) or (row['version'], row['digest']) != (
                        result['version'], result['digest']):
                    raise Refused('missing_evidence:result', result['id'])
                supplied.append(self._supply(name, row, {'kind': row['kind']}))
        return supplied

    def _fields(self, record, definition, name):
        """The supplied `fields` of a check: each declared field's value read from the store (absent when it has
        none): the subject's record, or the accepted result the named assignment routed on."""
        unit = _entity_row(self.conn, record['subject'])
        values = {}
        for field, declared in sorted((definition.get('fields') or {}).items()):
            source = declared['source']
            if 'subject' in source:
                data = unit['data'] if unit else {}
            else:
                result = (record.get('results') or {}).get(source['node'])
                row = self._result(result['id']) if result else None
                if row is None or (row['version'], row['digest']) != (result['version'], result['digest']):
                    continue
                data = row['data']
            if type(data) is dict and (source.get('subject') or source.get('result')) in data:
                values[field] = data[source.get('subject') or source.get('result')]
        return {'id': name, 'version': 1, 'digest': WF.digest(WF.canonical(values)), 'value': values}, values

    def _judge_check(self, record, definition, position, values, reported, port):
        """The cycle's own evaluation of a check against the bound revision: (decision, None) or (None, refusal)."""
        node = definition['nodes'][position]
        mine, problem = WF.evaluate(position, node['config'], definition.get('fields') or {}, values)
        if problem is not None or reported != mine or port != mine['branch']:
            self.metrics['branch_mismatch'] += 1
            return None, MISMATCH
        return mine, None

    def _decided(self, record, definition, mine, command, answer, **fields):
        """Record and report a check decision; count it by node and branch (otherwise on its own)."""
        kept = WF.redacted(mine, definition.get('fields') or {})
        if mine['branch'] == WF.OTHERWISE:
            self.metrics['otherwise'][mine['node']] = self.metrics['otherwise'].get(mine['node'], 0) + 1
        else:
            counts = self.metrics['checks'].setdefault(mine['node'], {})
            counts[mine['branch']] = counts.get(mine['branch'], 0) + 1
        self._report(self._event('check', record, node=mine['node'], branch=mine['branch'], rule=mine['rule'],
                                 conditions=kept['conditions'], graph=command, runtime=answer['runtime'], **fields))
        return kept

    def _run(self, record, revision):
        """Run the bound revision one judged step (one superstep of branches) at a time until it waits, proposes
        or is refused."""
        definition = revision['definition']
        routes = {}
        for t in definition['transitions']:
            routes.setdefault((t['from'], t['port']), []).append(t)
        while True:
            position = record['position']
            if record['steps'] >= definition['budget']['steps']:
                return self._refuse(record, 'budget_exceeded:steps', node=position)
            if position == PARALLEL:
                record = self._block_step(record, revision, routes)
                if record.get('state') != 'running':
                    return record
                continue
            node = definition['nodes'][position]
            kind = WF.STEP_KINDS[node['kind']]
            try:
                supplied = self._inputs(record, node, kind)
            except Refused as error:
                return self._refuse(record, error.code, node=position)
            if supplied is None:
                if kind['input'] == 'worker_result':
                    return self._assign(record, definition, node)
                waiting = dict(record, state='waiting', waiting={'node': position, 'input': kind['input']})
                return self._update(waiting, 'wait', node=position, input=kind['input'])
            values = None
            if node['kind'] == WF.CHECK:
                item, values = self._fields(record, definition, 'fields')
                supplied.append(item)
            try:
                answer, command = self._exchange(record, revision, 'advance', supplied=supplied)
            except Refused as error:
                return self._refuse(record, error.code, node=position)
            if kind['terminal']:
                return self._propose(record, answer, command, supplied)
            if answer['outcome'] != 'suspended':
                code = self._failure_code(answer, 'invalid_response:outcome')
                if values is not None:
                    _mine, problem = WF.evaluate(position, node['config'], definition.get('fields') or {}, values)
                    if problem is None or code != problem:
                        self.metrics['branch_mismatch'] += problem is None
                        code = MISMATCH if problem is None else problem
                return self._refuse(record, code, node=position, graph=command)
            notes = self._notes(answer)
            if notes.get('workflow') != {k: record['binding'][k] for k in ('id', 'version', 'digest')}:
                return self._refuse(record, 'missing_evidence:binding', node=position, graph=command)
            last = notes.get('last')
            port = last[1] if type(last) is list and len(last) == 3 and type(last[1]) is str else None
            found = routes.get((position, port)) or []
            if values is not None:
                mine, problem = self._judge_check(record, definition, position, values, notes.get('decision'), port)
                if problem:
                    return self._refuse(record, problem, node=position, graph=command)
            if len(found) > 1:
                record = self._fan_out(record, definition, answer, command, notes, found, kind, supplied)
                if record.get('state') != 'running':
                    return record
                continue
            taken = found[0] if found else None
            # The runner counts the intake as its first node: after definition step k it reports k + 1.
            if (taken is None or last[0] != position or last[2] != taken['to']
                    or answer['resume']['position'] != taken['to'] or answer['resume']['step'] != record['steps'] + 2):
                return self._refuse(record, 'invalid_response:trace', node=position, graph=command)
            visits = dict(record['visits'])
            visits[taken['id']] = visits.get(taken['id'], 0) + 1
            record = dict(record, steps=record['steps'] + 1, trace=record['trace'] + [list(last)], visits=visits,
                          position=taken['to'], resume=answer['resume'])
            if kind['input'] == 'owner_answer':
                # The answer this visit routed on is spent: the next owner wait asks the owner again.
                used = next(item for item in supplied if item['id'] == 'owner_answer')
                record = dict(record, answered={'version': used['version'], 'digest': used['digest']})
            if values is not None:
                record = dict(record, decisions=(record.get('decisions') or []) + [
                    self._decided(record, definition, mine, command, answer)])
            if kind['input'] == 'worker_result':
                # The result this assignment routed on is the one a result handling step may cite; a later
                # visit to an assignment waits for its own worker, after its own checks.
                record = dict(record, result=record['received'], received=None,
                              results=dict(record.get('results') or {}, **{position: record['received']}))
            if 'max' in taken and visits[taken['id']] > taken['max']:
                return self._refuse(record, 'budget_exceeded:loop/' + taken['id'], node=position, graph=command)
            self._update(record, 'step', node=position, port=last[1], graph=command, runtime=answer['runtime'],
                         executed=notes['workflow'])

    def _fan_out(self, record, definition, answer, command, notes, starts, kind, supplied):
        """A port with several transitions: the runner suspends at PARALLEL with one branch per transition, each at
        its first node, naming the join whose inputs are exactly those branches."""
        position, last = record['position'], notes.get('last')
        _problems, blocks = WF.block_problems(definition['nodes'], definition['transitions'])
        block = next((b for b in blocks if (b['fan_out'], b['port']) == (position, last[1])), None)
        expected = {t['id']: {'position': t['to'], 'last': None} for t in starts}
        if (block is None or last[0] != position or last[2] != PARALLEL or notes.get('branches') != expected
                or notes.get('join') != block['join'] or answer['resume']['position'] != PARALLEL
                or answer['resume']['step'] != record['steps'] + 2):
            return self._refuse(record, 'invalid_response:trace', node=position, graph=command)
        visits = dict(record['visits'])
        for t in starts:
            visits[t['id']] = visits.get(t['id'], 0) + 1
        result = {}
        if kind['input'] == 'owner_answer':
            spent = next(item for item in supplied if item['id'] == 'owner_answer')
            result['answered'] = {'version': spent['version'], 'digest': spent['digest']}
        if kind['input'] == 'worker_result':
            result = {'result': record['received'], 'received': None,
                      'results': dict(record.get('results') or {}, **{position: record['received']})}
        branches = {t['id']: {'position': t['to'], 'arrived': False, 'waiting': None, 'assignment': None,
                              'received': None, 'answered': None} for t in starts}
        record = dict(record, steps=record['steps'] + 1, trace=record['trace'] + [list(last)], visits=visits,
                      position=PARALLEL, resume=answer['resume'], **result,
                      block={'fan_out': position, 'port': last[1], 'join': block['join'], 'started': self.clock(),
                             'first_arrival': None, 'branches': branches})
        self.metrics['fan_outs'][len(starts)] = self.metrics['fan_outs'].get(len(starts), 0) + 1
        bounded = [t['id'] for t in starts if 'max' in t and visits[t['id']] > t['max']]
        if bounded:
            return self._refuse(record, 'budget_exceeded:loop/' + bounded[0], node=position, graph=command)
        self._update(record, 'step', node=position, port=last[1], graph=command, runtime=answer['runtime'],
                     executed=notes['workflow'])
        self._report(self._event('fan_out', record, node=position, width=len(starts), join=block['join'],
                                 branches={t['id']: t['to'] for t in starts}, graph=command))
        return record

    def _branch_inputs(self, record, definition, branch, state):
        """(items, waiting input or None, refusal or None) for one branch: what its node reads, keyed by node."""
        position = state['position']
        node = definition['nodes'][position]
        kind = WF.STEP_KINDS[node['kind']]
        if kind['input'] is None:
            if node['kind'] == WF.CHECK:
                item, _values = self._fields(dict(record, results=record.get('results') or {}), definition,
                                             'fields@' + position)
                return [item], None, None
            return [], None, None
        if kind['input'] == 'owner_answer':
            answer = _entity_row(self.conn, 'admission:' + record['subject'])
            data = answer['data'] if answer and answer['kind'] == 'admission' else {}
            used = state.get('answered') or record.get('answered')
            if (data.get('unit') != record['subject'] or data.get('state') not in ANSWERS
                    or (used is not None and answer['version'] <= used['version'])):
                return None, 'owner_answer', None
            return [self._supply('owner_answer@' + position, answer, {'state': data['state']})], None, None
        if kind['input'] == 'worker_result':
            received = state.get('received')
            if received and (state.get('assignment') or {}).get('node') == position:
                row = self._result(received['id'])
                if not self._accepted_result(record, row) or (row['version'], row['digest']) != (
                        received['version'], received['digest']):
                    return None, None, ('missing_evidence:result', None, {'node': position})
                return [self._supply('worker_result@' + position, row, {'kind': row['kind']})], None, None
            return None, 'worker_result', None
        return None, None, ('unsupported_workflow:' + node['kind'] + '_in_branch', None, {'node': position})

    def _block_step(self, record, revision, routes):
        """One superstep of a fan-out's branches, or the join once every branch has reached it."""
        definition = revision['definition']
        block = json.loads(json.dumps(record['block']))
        join, branches = block['join'], block['branches']
        binding = {k: record['binding'][k] for k in ('id', 'version', 'digest')}
        unit = _entity_row(self.conn, record['subject'])
        if unit is None or unit['kind'] != 'execution_unit':
            return self._refuse(record, 'missing_evidence:subject', node=PARALLEL)
        supplied = [self._supply('subject', unit, {'unit': record['subject'], 'state': unit['data'].get('state')})]
        if all(state['arrived'] for state in branches.values()):
            try:
                answer, command = self._exchange(record, revision, 'advance', supplied=supplied)
            except Refused as error:
                return self._refuse(record, error.code, node=join)
            notes = self._notes(answer) if answer['outcome'] == 'suspended' else {}
            last = notes.get('last')
            taken = (routes.get((join, 'done')) or [None])[0]
            if answer['outcome'] != 'suspended':
                return self._refuse(record, self._failure_code(answer, 'invalid_response:outcome'), node=join,
                                    graph=command)
            if notes.get('workflow') != binding:
                return self._refuse(record, 'missing_evidence:binding', node=join, graph=command)
            if (taken is None or last != [join, 'done', taken['to']] or notes.get('branches') is not None
                    or answer['resume']['position'] != taken['to'] or answer['resume']['step'] != record['steps'] + 2):
                return self._refuse(record, 'invalid_response:trace', node=join, graph=command)
            visits = dict(record['visits'])
            visits[taken['id']] = visits.get(taken['id'], 0) + 1
            waited = self.clock() - (block['first_arrival'] or block['started'])
            self.metrics['join_wait_seconds'].append(round(waited, 3))
            self.metrics['joins_waiting'].pop(record['cycle'], None)
            self.metrics['branches_running'].pop(record['cycle'], None)
            record = dict(record, steps=record['steps'] + 1, trace=record['trace'] + [list(last)], visits=visits,
                          position=taken['to'], resume=answer['resume'], block=None)
            if taken.get('max') is not None and visits[taken['id']] > taken['max']:
                return self._refuse(record, 'budget_exceeded:loop/' + taken['id'], node=join, graph=command)
            self._update(record, 'step', node=join, port='done', graph=command, runtime=answer['runtime'],
                         executed=notes['workflow'], join=join, fan_out=block['fan_out'], waited=round(waited, 3),
                         completed=self.clock())
            return record
        ready, dispatched = [], []
        for branch, state in sorted(branches.items()):
            if state['arrived']:
                continue
            items, waiting, refusal = self._branch_inputs(record, definition, branch, state)
            if refusal:
                code, codes, fields = refusal
                return self._refuse(record, code, codes, branch=branch, **fields)
            if items is not None:
                ready.append(branch)
                supplied += items
                state['waiting'] = None
                continue
            state['waiting'] = waiting
            if waiting == 'worker_result' and (state.get('assignment') or {}).get('node') != state['position']:
                dispatched.append(branch)
        # The whole superstep counts against the budget: one that would pass it is refused before any branch
        # starts, so a wide fan-out never runs past budget.steps.
        if ready and record['steps'] + len(ready) > definition['budget']['steps']:
            return self._refuse(record, 'budget_exceeded:steps', node=PARALLEL, branches=ready)
        for branch in dispatched:
            state = branches[branch]
            node = definition['nodes'][state['position']]
            assignment, refused = self._assignment(record, definition, node, state['position'])
            if refused:
                code, codes, fields = refused
                return self._refuse(record, code, codes, branch=branch, **fields)
            state['assignment'], state['received'] = assignment, None
        running = sum(1 for state in branches.values() if not state['arrived'])
        self.metrics['branches_running'][record['cycle']] = running
        record = dict(record, block=block)
        if not ready:
            pending = {b: {'node': st['position'], 'input': st['waiting']} for b, st in sorted(branches.items())
                       if not st['arrived']}
            record = dict(record, state='waiting', waiting={'node': PARALLEL, 'input': 'branches', 'branches': pending})
            return self._update(record, 'wait', node=PARALLEL, input='branches', branches=pending,
                                dispatched=dispatched, fan_out=block['fan_out'], join=join)
        try:
            answer, command = self._exchange(record, revision, 'advance', supplied=supplied)
        except Refused as error:
            return self._refuse(record, error.code, node=PARALLEL)
        if answer['outcome'] != 'suspended':
            return self._refuse(record, self._failure_code(answer, 'invalid_response:outcome'), node=PARALLEL,
                                graph=command)
        notes = self._notes(answer)
        if notes.get('workflow') != binding:
            return self._refuse(record, 'missing_evidence:binding', node=PARALLEL, graph=command)
        reported = notes.get('branches') if type(notes.get('branches')) is dict else {}
        if set(reported) != set(branches) or answer['resume']['position'] != PARALLEL or notes.get('join') != join:
            return self._refuse(record, 'invalid_response:trace', node=PARALLEL, graph=command)
        moved, steps, supersteps, decisions = [], [], set(), []
        visits = dict(record['visits'])
        for branch, state in sorted(branches.items()):
            entry = reported[branch] if type(reported[branch]) is dict else {}
            if state['arrived']:
                if entry != {'position': join, 'last': None}:
                    return self._refuse(record, 'invalid_response:trace', node=PARALLEL, branch=branch, graph=command)
                continue
            supersteps.add(entry.get('superstep'))
            last = entry.get('last')
            if branch not in ready:
                if entry.get('position') != state['position'] or last is not None:
                    return self._refuse(record, 'invalid_response:trace', node=PARALLEL, branch=branch, graph=command)
                continue
            position = state['position']
            node = definition['nodes'][position]
            port = last[1] if type(last) is list and len(last) == 3 and type(last[1]) is str else None
            found = routes.get((position, port)) or []
            if node['kind'] == WF.CHECK:
                _item, values = self._fields(record, definition, 'fields@' + position)
                mine, problem = self._judge_check(record, definition, position, values, entry.get('decision'), port)
                if problem:
                    return self._refuse(record, problem, node=position, branch=branch, graph=command)
                decisions.append((branch, mine))
            if len(found) != 1 or last != [position, port, found[0]['to']] or entry.get('position') != found[0]['to']:
                return self._refuse(record, 'invalid_response:trace', node=position, branch=branch, graph=command)
            taken = found[0]
            visits[taken['id']] = visits.get(taken['id'], 0) + 1
            if taken.get('max') is not None and visits[taken['id']] > taken['max']:
                return self._refuse(record, 'budget_exceeded:loop/' + taken['id'], node=position, branch=branch,
                                    graph=command)
            kind = WF.STEP_KINDS[node['kind']]
            if kind['input'] == 'owner_answer':
                used = next(item for item in supplied if item['id'] == 'owner_answer@' + position)
                state['answered'] = {'version': used['version'], 'digest': used['digest']}
            if kind['input'] == 'worker_result':
                record = dict(record, result=state['received'],
                              results=dict(record.get('results') or {}, **{position: state['received']}))
                state['received'], state['assignment'] = None, None
            state['position'], state['arrived'] = taken['to'], taken['to'] == join
            moved.append(branch)
            steps.append([branch, list(last), entry.get('superstep')])
        # Every branch that ran shares one superstep: branches run one after another are not parallel.
        if len(supersteps) != 1 or None in supersteps or answer['resume']['step'] != record['steps'] + 1 + len(moved):
            return self._refuse(record, 'invalid_response:trace', node=PARALLEL, graph=command)
        now = self.clock()
        if any(branches[b]['arrived'] for b in moved) and block['first_arrival'] is None:
            block['first_arrival'] = now
        kept = {}
        for branch, mine in decisions:
            kept[branch] = self._decided(record, definition, mine, command, answer, branch=branch,
                                         fan_out=block['fan_out'], join=join)
        record = dict(record, steps=record['steps'] + len(moved), visits=visits, resume=answer['resume'], block=block,
                      trace=record['trace'] + [last for _b, last, _s in steps],
                      decisions=(record.get('decisions') or []) + [kept[b] for b in sorted(kept)])
        if any(st['arrived'] for st in branches.values()) and not all(st['arrived'] for st in branches.values()):
            self.metrics['joins_waiting'][record['cycle']] = sorted(b for b, st in branches.items() if st['arrived'])
        record = self._update(record, 'superstep', node=PARALLEL, graph=command, runtime=answer['runtime'],
                              executed=notes['workflow'], moved=moved, fan_out=block['fan_out'], join=join)
        for branch, last, superstep in steps:
            self._report(self._event('branch_step', record, branch=branch, node=last[0], port=last[1], next=last[2],
                                     superstep=superstep, graph=command, runtime=answer['runtime'],
                                     fan_out=block['fan_out'], join=join))
            if branches[branch]['arrived']:
                self._report(self._event('arrive', record, branch=branch, join=join, at=now, fan_out=block['fan_out']))
        return record

    def _propose(self, record, answer, command, supplied):
        """The terminal step's proposal, judged by result validation; never completion itself."""
        position = record['position']
        if answer['outcome'] != 'proposal':
            return self._refuse(record, self._failure_code(answer, 'invalid_response:outcome'), node=position,
                                graph=command)
        proposals = answer['proposals']
        offered = {item['digest'] for item in supplied}
        received = (record.get('result') or {}).get('digest')
        valid = (len(proposals) == 1 and proposals[0]['type'] == 'completion'
                 and proposals[0]['subject'] == record['subject'])
        if not valid:
            return self._refuse(record, 'invalid_response:proposal', node=position, graph=command)
        evidence = set(proposals[0]['evidence'])
        if not received or received not in evidence or not evidence <= offered:
            return self._refuse(record, 'missing_evidence:completion', node=position, graph=command)
        record = dict(record, state='proposed', steps=record['steps'] + 1,
                      trace=record['trace'] + [[position, 'proposed', None]], proposals=proposals, resume=None)
        return self._update(record, 'propose', node=position, graph=command, runtime=answer['runtime'],
                            proposals=[p['proposal_id'] for p in proposals])

    # -- metrics ----------------------------------------------------------------------------------

    def status(self):
        """Accepted and refused operations, and the pending work: every waiting cycle, with the node
        and the input it waits for."""
        pending = []
        try:
            rows = self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (CYCLE_KIND,)).fetchall()
        except sqlite3.Error:
            rows = []
        for (raw,) in rows:
            data = json.loads(raw)
            if (data.get('domain'), data.get('repository')) == (self.domain, self.repository) and data['state'] == 'waiting':
                pending.append({'cycle': data['cycle'], 'subject': data['subject'], 'node': data['waiting']['node'],
                                'input': data['waiting']['input'], 'workflow': data['binding']['id'],
                                'version': data['binding']['version']})
        return dict(self.counts, pending=pending)
