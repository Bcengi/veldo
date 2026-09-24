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

NOT HERE: checkpoint recovery and resuming a cycle after a crash (Release 2); a cycle whose exchange
fails is refused, never retried. The dispatcher's use of a pending assignment is the floor's.
"""
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
    prior = before.get(cid)
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
                  'waiting': None, 'assignment': None, 'received': None, 'proposals': [], 'refusal': None,
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
        self.observations = []
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
        with tempfile.TemporaryDirectory(prefix='veldo-workflow-runner-') as scratch:
            runner = Path(scratch) / RUNNER
            runner.write_text(runner_source(revision))
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

    def _assign(self, record, definition, node):
        """The ordinary checks before an assignment waits for a worker: role authority, then the Gate."""
        problem = self.role_problem(definition, node)
        if problem:
            return self._refuse(record, problem, node=record['position'])
        decision = self.gate.decide(STATION, record['subject'])
        if not decision['eligible']:
            return self._refuse(record, decision['refusals'][0], decision['refusals'], node=record['position'],
                                decision=decision['decision_id'])
        role = definition['references']['roles'][node['config']['role']]
        record = dict(record, state='waiting', waiting={'node': record['position'], 'input': 'worker_result'},
                      assignment={'node': record['position'], 'role': node['config']['role'],
                                  'configuration': dict(role), 'station': STATION,
                                  'decision': decision['decision_id'], 'watermark': decision['watermark']})
        return self._update(record, 'wait', node=record['position'], input='worker_result',
                            decision=decision['decision_id'])

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
        self._update(record, 'step', node=INTAKE, graph=command, runtime=answer['runtime'])
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
        if record['waiting']['input'] == 'worker_result':
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
        try:
            revision = self._revision(record)
            if record['resume'] is not None:
                answer, command = self._exchange(record, revision, 'cancel')
                if answer['outcome'] != 'canceled':
                    return self._refuse(record, self._failure_code(answer, 'invalid_response:cancel'), graph=command)
        except Refused as error:
            return self._refuse(record, error.code)
        return self._update(dict(record, state='canceled', waiting=None), 'cancel')

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
            received = record.get('received')
            if received:
                row = self._result(received['id'])
                if not self._accepted_result(record, row) or (row['version'], row['digest']) != (
                        received['version'], received['digest']):
                    raise Refused('missing_evidence:result', received['id'])
                supplied.append(self._supply('accepted_result', row, {'kind': row['kind']}))
        return supplied

    def _run(self, record, revision):
        """Run the bound revision one judged step at a time until it waits, proposes or is refused."""
        definition = revision['definition']
        transitions = {(t['from'], t['port']): t for t in definition['transitions']}
        while True:
            position = record['position']
            node = definition['nodes'][position]
            kind = WF.STEP_KINDS[node['kind']]
            if record['steps'] >= definition['budget']['steps']:
                return self._refuse(record, 'budget_exceeded:steps', node=position)
            try:
                supplied = self._inputs(record, node, kind)
            except Refused as error:
                return self._refuse(record, error.code, node=position)
            if supplied is None:
                if kind['input'] == 'worker_result':
                    return self._assign(record, definition, node)
                waiting = dict(record, state='waiting', waiting={'node': position, 'input': kind['input']})
                return self._update(waiting, 'wait', node=position, input=kind['input'])
            try:
                answer, command = self._exchange(record, revision, 'advance', supplied=supplied)
            except Refused as error:
                return self._refuse(record, error.code, node=position)
            if kind['terminal']:
                return self._propose(record, answer, command, supplied)
            if answer['outcome'] != 'suspended':
                return self._refuse(record, self._failure_code(answer, 'invalid_response:outcome'), node=position,
                                    graph=command)
            notes = self._notes(answer)
            if notes.get('workflow') != {k: record['binding'][k] for k in ('id', 'version', 'digest')}:
                return self._refuse(record, 'missing_evidence:binding', node=position, graph=command)
            last = notes.get('last')
            taken = (transitions.get((position, last[1])) if type(last) is list and len(last) == 3
                     and type(last[1]) is str else None)
            # The runner counts the intake as its first node: after definition step k it reports k + 1.
            if (taken is None or last[0] != position or last[2] != taken['to']
                    or answer['resume']['position'] != taken['to'] or answer['resume']['step'] != record['steps'] + 2):
                return self._refuse(record, 'invalid_response:trace', node=position, graph=command)
            visits = dict(record['visits'])
            visits[taken['id']] = visits.get(taken['id'], 0) + 1
            record = dict(record, steps=record['steps'] + 1, trace=record['trace'] + [list(last)], visits=visits,
                          position=taken['to'], resume=answer['resume'])
            if 'max' in taken and visits[taken['id']] > taken['max']:
                return self._refuse(record, 'budget_exceeded:loop/' + taken['id'], node=position, graph=command)
            self._update(record, 'step', node=position, port=last[1], graph=command, runtime=answer['runtime'])

    def _propose(self, record, answer, command, supplied):
        """The terminal step's proposal, judged by result validation; never completion itself."""
        position = record['position']
        if answer['outcome'] != 'proposal':
            return self._refuse(record, self._failure_code(answer, 'invalid_response:outcome'), node=position,
                                graph=command)
        proposals = answer['proposals']
        offered = {item['digest'] for item in supplied}
        received = (record.get('received') or {}).get('digest')
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
