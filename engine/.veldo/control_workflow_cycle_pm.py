"""Project coordination cycles over accepted snapshots (VELDO-0088).

The authority owns scheduling and receipts. LangGraph owns only the bounded step
trace. Reasoning is a coordination dispatch on the ordinary Runner. Returned
commands are applied in order by their registered owners; the first refusal stops
the document. A cycle never writes the entities owned by those commands.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import uuid


def organ(name):
    spec = importlib.util.spec_from_file_location('pm_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SN = organ('control_snapshot')
RS = organ('control_readset')
CT = organ('control_team')
CFG = organ('control_agent_config')
CY = organ('control_workflow_cycle')
SCHEMA = 'veldo.pm_cycle/v1'
DOCUMENT = 'veldo.pm_proposals/v1'
KIND = 'pm_cycle'
RECORD = 'record_pm_cycle'
PIPELINE = ('intake', 'coordinate', 'elaborate', 'admit', 'assign', 'build',
            'prove_and_gate', 'review', 'land', 'report')
WORKFLOW = {'id': 'default_pipeline', 'version': 1,
            'digest': SN.digest(SN.canonical(list(PIPELINE)))}
HANDLERS = {'question': ('inbox', 'apply'), 'decomposition': ('decomposition', 'publish'),
            'backlog': ('backlog', 'apply'), 'grooming': ('grooming', 'apply'),
            'assignment': ('teams', 'apply')}
OPERATIONS = {'question': ('open',), 'decomposition': ('publish_decomposition',),
              'backlog': ('take', 'prepare', 'request_grooming'),
              'grooming': ('propose',), 'assignment': ('assign',)}
FINAL = ('proposed', 'no_action', 'refused', 'waiting_owner')
Refused = CY.Refused


def row(conn, identity):
    got = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    return None if got is None else dict(id=identity, kind=got[0], version=got[1], digest=got[2], data=json.loads(got[3]))


def ref(record):
    return {k: record[k] for k in ('id', 'version', 'digest')}


def assigned(conn, unit):
    records = CT.assignments(conn, unit)
    return max(records, key=lambda r: (r['at'], r['id'])) if records else None


def assignment_inputs(gate, unit, data):
    """Bind the assignment and its current authority to the ordinary station ticket."""
    assignment = assigned(gate.conn, unit)
    if not assignment:
        return {}
    identities = {'team_assignment': assignment['id'], 'assigned_team': 'team:' + data['project']}
    identities.update({'assigned_member/' + who: who
                       for who in [assignment['builder'], *assignment['reviewers']]})
    return {name: gate._entity(identity) for name, identity in identities.items()}


def assignment_problems(gate, unit, inputs, context):
    assignment = gate._data(inputs.get('team_assignment')) or {}
    data = gate._data(inputs['unit'])
    team = gate._data(inputs.get('assigned_team')) or {}
    if (assignment.get('subject') != dict(unit=unit, revision=data.get('revision'),
                                         scope_digest=data.get('scope_digest'))
            or assignment.get('project') != data.get('project')
            or assignment.get('team', {}).get('revision') != team.get('revision')):
        return ['stale_subject:team_assignment']
    if (context or {}).get('holder') != assignment.get('builder'):
        return ['missing_authority:assigned_builder']
    reviewer = (context or {}).get('reviewer')
    if reviewer and (reviewer not in assignment['reviewers'] or reviewer == assignment['builder']):
        return ['reviewer_not_independent']
    membership = organ('control_membership')
    for who in [assignment['builder'], *assignment['reviewers']]:
        member = gate._data(inputs.get('assigned_member/' + who))
        if (not member or not membership.AC.active_member(dict(member, principal=who), time.time())[0]
                or not membership.scope_covers(member.get('scope'), [data['project']])):
            return ['missing_authority:assigned_member']
    return []


def engineering_role(line, assignment, station):
    """Use the accepted team's capability and budget at the engineering boundary."""
    review = station == 'review'
    who = assignment['reviewers'][0] if review else assignment['builder']
    configuration = assignment['reviewer_capability_configuration' if review else 'capability_configuration']
    accepted = CFG.read(line.service.conn, line.service.domain, line.repository,
                        configuration['role'], configuration['revision'])
    adapter = next((a for a, engine in sorted(line.engines.items()) if engine == accepted['engine']), None)
    if adapter is None:
        raise Refused('unavailable_service:engineering_adapter')
    team = CT.read(None, line.service.conn, assignment['project'])
    role = team['team']['roles']['independent_review' if review else assignment['role']]
    unit = row(line.service.conn, assignment['unit'])['data']
    bound = unit['specification_document']
    specification = row(line.service.conn, 'document/%s/%s@%s' %
                        (line.repository, bound['alias'], bound['version']))
    return dict(identity=who, adapter=adapter, configuration=configuration,
                seconds=role['budget']['wall_seconds'], payload={
                    'requirements': specification['data']['content'],
                    'instruction': 'Fetch referenced tickets using the catalog servers in your role configuration.'})


def document(value):
    """Closed proposal vocabulary. No node can submit arbitrary operations."""
    if (type(value) is not dict or set(value) != {'schema', 'owner_questions', 'decomposition', 'proposals'}
            or value['schema'] != DOCUMENT or type(value['owner_questions']) is not list
            or not all(type(q) is str and q.strip() for q in value['owner_questions'])
            or type(value['decomposition']) is not list or len(value['decomposition']) > 1
            or type(value['proposals']) is not list):
        raise Refused('invalid_input:proposal_document')
    for unit in value['decomposition']:
        if (type(unit) is not dict or set(unit) != {'unit', 'requirements', 'owner_message', 'references', 'staffing'}
                or not all(type(unit[k]) is str and unit[k] for k in ('unit', 'requirements', 'owner_message'))
                or type(unit['references']) is not list or not all(type(r) is str for r in unit['references'])
                or type(unit['staffing']) is not dict or set(unit['staffing']) != set(CT.REQUIRED_ROLES)
                or not all(type(r) is str and r for r in unit['staffing'].values())):
            raise Refused('invalid_input:one_unit')
    names = set()
    for proposal in value['proposals']:
        if (type(proposal) is not dict or set(proposal) != {'name', 'type', 'command'}
                or type(proposal['name']) is not str or not proposal['name'] or proposal['name'] in names
                or proposal['type'] not in HANDLERS or type(proposal['command']) is not dict
                or proposal['command'].get('operation') not in OPERATIONS[proposal['type']]):
            raise Refused('invalid_input:proposal')
        names.add(proposal['name'])
    return copy.deepcopy(value)


def result_references(value, applied):
    """Only earlier owner results can supply a subsequently allocated identity."""
    if isinstance(value, dict) and set(value) == {'result', 'path'}:
        held = next((r['result'] for r in applied if r['name'] == value['result']), None)
        if held is None or not isinstance(value['path'], list):
            raise Refused('invalid_input:proposal_reference')
        for key in value['path']:
            if not isinstance(held, dict) or key not in held:
                raise Refused('invalid_input:proposal_reference')
            held = held[key]
        return copy.deepcopy(held)
    if isinstance(value, dict):
        return {key: result_references(item, applied) for key, item in value.items()}
    if isinstance(value, list):
        return [result_references(item, applied) for item in value]
    return value


def coordination_decision(gate, unit, context, ticket):
    """Project-bound eligibility at Runner preparation and receiver acceptance."""
    decision = dict(schema=gate.SCHEMA if hasattr(gate, 'SCHEMA') else 'veldo.control_eligibility/v1',
        decision_id=str(uuid.uuid4()), station='coordination', unit=unit, domain_uuid=gate.domain_uuid,
        repository_uuid=gate.repository_uuid, follows=(ticket or {}).get('decision_id'), inputs={}, watermark=0, pending=[], refusals=[])
    with gate._reading():
        cycle = row(gate.conn, unit)
        if not cycle or cycle['kind'] != KIND:
            decision['refusals'].append('missing_authority:pm_cycle')
        else:
            data = cycle['data']
            project = gate._entity('project:' + data['project'])
            owner = gate._project_owner(project)
            decision['refusals'] += gate._project_problems(data['project'], project,
                gate._entity(owner) if owner else None)
            team = row(gate.conn, 'team:' + data['project'])
            snap = row(gate.conn, data['snapshot']['id'])
            if (data['domain'], data['repository']) != (gate.domain_uuid, gate.repository_uuid):
                decision['refusals'].append('missing_authority:pm_coordinates')
            if data['state'] not in ('running', 'waiting_run'):
                decision['refusals'].append('stale_subject:cycle_final')
            if not team or ref(team) != data['team']:
                decision['refusals'].append('stale_subject:team')
            if not snap or ref(snap) != data['snapshot']:
                decision['refusals'].append('missing_evidence:snapshot')
            manager = row(gate.conn, data['manager'])
            entry = dict(manager['data'], principal=data['manager']) if manager else None
            if (not entry or not organ('control_membership').AC.active_member(entry, time.time())[0]
                    or not organ('control_membership').scope_covers(entry.get('scope'), [data['project']])
                    or (context or {}).get('holder') != data['manager']):
                decision['refusals'].append('missing_authority:manager')
            for name, held in (('team', team), ('snapshot', snap), ('manager', manager)):
                if held:
                    decision['inputs'][name] = ref(held)
            # The mutable receipt records observations, not new authorization.
            decision['inputs']['cycle'] = {'id': unit, 'digest': SN.digest(SN.canonical({
                k: data[k] for k in ('project', 'snapshot', 'team', 'configuration', 'manager', 'accepted_commit')}))}
            decision['inputs']['project'] = gate._identity('project', project)
            decision['watermark'] = gate.conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]
    if ticket and ticket.get('inputs') != decision['inputs']:
        decision['refusals'].append('stale_input:coordination')
    decision['eligible'] = not decision['refusals']
    gate._record(decision)
    return decision


def transition(conn, params, before):
    identity, record = params['id'], params['record']
    old = row(conn, identity)
    if old:
        for key in ('schema', 'project', 'repository', 'domain', 'snapshot', 'workflow', 'cycle', 'input_key'):
            if record.get(key) != old['data'].get(key):
                raise Refused('stale_subject:cycle_binding')
    else:
        active = [json.loads(r[0]) for r in conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,))]
        if any(r['project'] == record['project'] and r['repository'] == record['repository']
               and r['state'] not in FINAL for r in active):
            raise Refused('active_cycle:project')
    return {identity: {'kind': KIND, 'data': record}}


class ProjectCycles:
    """One repository, one authority scheduler, the existing Runner and command owners.

    `services` are the actual owning services, never callbacks running node code.
    `command_sign` signs ordinary commands as the enrolled scheduling principal.
    No scheduling thread, retry timer or persistent graph checkpoint is created.
    """
    def __init__(self, store, conn, *, domain, repository, workspace, principal, sign, command_sign,
                 runner, adapters, services, generation=1, runtime=None, stage=None, observe=None, execution_records=None):
        self.store, self.conn = store, conn
        self.domain, self.repository, self.workspace = domain, repository, str(workspace)
        self.principal, self.sign, self.command_sign = principal, sign, command_sign
        self.runner, self.adapters, self.services = runner, adapters, services
        self.generation, self.runtime, self.stage = generation, runtime, stage
        self.execution_records = execution_records
        self.observe = observe or (lambda event: None)
        self.pending, self.seen = {}, {}
        self.counts = {'accepted': 0, 'refused': 0}
        store.declare_owners(conn, 'VELDO-0088 project cycles', kinds={KIND: (RECORD,)}, module=__file__)
        conn.command_registry[RECORD] = {'transaction_transition': transition,
                                        'writes': ('entities', 'journal', 'commands', 'nonces')}
        self.readsets = RS.attach(store, conn, workspace, domain, repository)
        # Snapshot acceptance consumes all accepted project inputs. The consumer
        # registration exists only to define the read set, never to write a unit.
        store.COMMAND_REGISTRY.setdefault('pm_snapshot_inputs', {'transition': lambda p, b: {}, 'writes': ()})
        self.readsets.enable('pm_snapshot_inputs', {'revision': '$revision',
            'entities': {'project': '$project', 'team': '$team'}, 'collections': {
                'objectives': {'kind': 'objective', 'where': {'project': '$name'}, 'references': ['proposal_id']},
                'decisions': {'kind': 'assignment', 'where': {}},
                'dispatches': {'kind': 'dispatch', 'where': {}}}})

    def records(self, project=None):
        records = [json.loads(r[0]) for r in self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (KIND,))]
        return [r for r in records if r['repository'] == self.repository and (project is None or r['project'] == project)]

    def save(self, record):
        identity = 'pm-cycle:' + record['cycle']
        old = row(self.conn, identity)
        command = 'pm-receipt/' + uuid.uuid4().hex
        result = self.store.execute(self.conn, dict(command_id=command, principal=self.principal, operation=RECORD,
            parameters={'id': identity, 'record': record}, expected_versions={identity: old['version'] if old else 0},
            artifact_digests=[], nonce=command), self.principal, self.sign, self.generation)
        self.observe(dict(operation='pm_cycle', project=record['project'], cycle=record['cycle'],
            domain=self.domain, repository=self.repository, snapshot=record['snapshot'], state=record['state'],
            refusal=record.get('refusal'), watermark=result['seq']))
        return record

    def inputs(self, project):
        """Relevant accepted input, excluding the cycle's own receipts and dispatch."""
        values = []
        for identity, kind, version, digest, raw in self.conn.execute(
                'SELECT id, kind, version, digest, data FROM entities ORDER BY id'):
            data = json.loads(raw)
            relevant = (identity in ('project:' + project, 'team:' + project)
                        or kind == 'accepted_revision' and data.get('repository_uuid') == self.repository
                        or kind == 'objective' and data.get('project') == project
                        or kind == 'assignment' and project in data.get('scope', []) and data.get('answer')
                        or kind == 'dispatch' and (data.get('contract') or {}).get('reservation', {}).get('project') == project
                        and (data.get('contract') or {}).get('station') != 'coordination'
                        and data.get('state') in ('exited', 'unknown'))
            if relevant:
                values.append([identity, version, digest])
        return SN.digest(SN.canonical(values))

    def snapshot(self, project):
        revisions = [r[0] for r in self.conn.execute("SELECT id FROM entities WHERE kind='accepted_revision' ORDER BY id")
                     if row(self.conn, r[0])['data'].get('repository_uuid') == self.repository]
        if not revisions:
            raise Refused('missing_evidence:accepted_revision')
        identity = 'pm-snapshot-' + uuid.uuid4().hex
        command = 'pm-snapshot/' + uuid.uuid4().hex
        self.readsets.execute(dict(command_id=command, principal=self.principal, operation='accept_snapshot',
            parameters={'snapshot_id': identity, 'operation': 'pm_snapshot_inputs', 'arguments': {
                'revision': revisions[-1], 'project': 'project:' + project, 'team': 'team:' + project, 'name': project}},
            expected_versions={identity: 0}, artifact_digests=[], nonce=command),
            signer=self.principal, sign=self.sign, authority_generation=self.generation)
        return row(self.conn, identity)

    def exchange(self, record, operation, supplied=()):
        graph = organ('control_graph')
        runtime = self.runtime or CY.installed_runtime(stage=self.stage)
        source = (Path(__file__).with_name('control_graph_langgraph.py')).read_text()
        extension = Path(__file__).with_name('control_graph_pm.py').read_text()
        guard = "\nif __name__ == '__main__':\n"
        with tempfile.TemporaryDirectory(prefix='pm-graph-') as temporary:
            runner = Path(temporary) / 'runner.py'
            runner.write_text(source.replace(guard, '\n' + extension + '\n' + guard))
            adapter = graph.Adapter(dict(runtime, runner=str(runner)), self.domain, self.repository,
                                    evidence=graph.runtime_evidence())
            command = record['cycle'] + '.' + str(len(record['trace']))
            if operation == 'start':
                answer = adapter.start(record['cycle'], command, record['snapshot'], record['workflow'])
            else:
                answer = adapter.advance(record['cycle'], command, record['snapshot'], record['workflow'],
                                         record['resume'], list(supplied))
        if answer['outcome'] == 'failure':
            raise Refused(answer['failure']['code'], answer['failure']['detail'])
        return answer

    def start(self, project, input_key):
        p = row(self.conn, 'project:' + project)
        team = CT.read(self.store, self.conn, project)
        if not p or p['data'].get('state') != 'ACTIVE' or not team:
            raise Refused('missing_authority:active_project_team')
        budget = p['data']['coordination_budget']['invocations']
        if len(self.records(project)) >= budget:
            raise Refused('budget_exceeded:coordination')
        role = team['team']['roles']['project_manager']
        configuration = role['capability_configuration']
        accepted = CFG.read(self.conn, self.domain, self.repository, configuration['role'], configuration['revision'])
        engine = accepted['engine']
        adapter = next((name for name, value in sorted(self.adapters.items()) if value == engine), None)
        if adapter is None:
            raise Refused('unavailable_service:pm_adapter')
        snap = self.snapshot(project)
        record = dict(schema=SCHEMA, cycle='pm-' + uuid.uuid4().hex, project=project, domain=self.domain,
            repository=self.repository, workflow=dict(WORKFLOW), snapshot=ref(snap), input_key=input_key,
            accepted_commit=snap['data']['accepted_commit'], watermark=snap['data']['watermark'],
            input_versions=copy.deepcopy(snap['data']['inputs']), team=ref(row(self.conn, 'team:' + project)),
            state='running', trace=[], resume=None, dispatch=None, reservation=None, proposals=[], refusal=None,
            configuration=copy.deepcopy(configuration), manager=role['workers'][0])
        self.save(record)
        try:
            answer = self.exchange(record, 'start')
            record['resume'] = answer.get('resume')
            if answer['outcome'] != 'suspended' or record['resume']['position'] != 'coordinate':
                raise Refused('invalid_response:coordinate')
            record['trace'] = ['intake']
            payload = {'operation': 'coordinate', 'snapshot': snap['data'], 'workflow': record['workflow'],
                       'output_schema': DOCUMENT, 'required_roles': list(CT.REQUIRED_ROLES),
                       'instruction': 'Return one typed proposal document. For one unit write its requirements '
                                      'in this run, preserving the owner message and every reference verbatim. '
                                      'The builder fetches references using its configured catalog servers.'}
            self.runner.reservations.configure('pm-ceiling/' + record['cycle'], 'unit',
                'pm-cycle:' + record['cycle'], dict(role['budget']), now=time.time())
            launch = self.runner.submit('pm-cycle:' + record['cycle'], 'coordination', holder=record['manager'],
                source=self.workspace, revision=record['accepted_commit'], payload=payload, adapter=adapter,
                configuration={'role': configuration['role'], 'revision': configuration['revision']},
                deadline=time.time() + role['budget']['wall_seconds'], context={'project': project})
            record.update(dispatch=launch.dispatch_id, reservation=launch.contract['reservation'], state='waiting_run')
            if launch.result != 'accepted':
                raise Refused('unavailable_service:pm_dispatch')
        except Exception as error:
            record.update(state='refused', refusal=getattr(error, 'code', 'unknown_outcome:' + type(error).__name__))
        return self.save(record)

    def apply(self, record, value):
        value = document(value)
        team = CT.read(self.store, self.conn, record['project'])
        if ref(row(self.conn, 'team:' + record['project'])) != record['team']:
            raise Refused('stale_subject:team')
        snapshot = SN.load(self.store, self.conn, record['snapshot']['id'], self.domain, self.repository)
        sources = [v['value']['data'].get('text') for k, v in snapshot['inputs'].items()
                   if k.startswith('reference/objectives/') and v.get('value')]
        for unit in value['decomposition']:
            if unit['owner_message'] not in sources:
                raise Refused('stale_subject:owner_message')
            for name in unit['staffing'].values():
                if name not in team['team']['roles']:
                    raise Refused('missing_authority:staffing_role')
        applied = []
        for proposal in value['proposals']:
            service_name, method = HANDLERS[proposal['type']]
            service = self.services.get(service_name)
            if service is None:
                raise Refused('unavailable_service:proposal_owner:' + service_name)
            command = result_references(proposal['command'], applied)
            if proposal['type'] == 'assignment':
                held = row(self.conn, command.get('unit'))
                if not held or held['kind'] != 'execution_unit':
                    raise Refused('missing_evidence:assignment_unit')
                subject = dict(unit=held['id'], revision=held['data']['revision'],
                               scope_digest=held['data']['scope_digest'])
                command['subject'] = subject
                command['reviewers'] = [dict(reviewer=who, subject=subject) for who in command['reviewers']]
            if command.get('project', record['project']) != record['project']:
                raise Refused('invalid_input:proposal_project')
            command.update(principal=self.principal, command_id='pm-proposal/' + record['cycle'] + '/' + proposal['name'],
                           nonce='pm-proposal/' + record['cycle'] + '/' + proposal['name'])
            result = getattr(service, method)({'command': command,
                'signature': self.command_sign(self.store.canonical_bytes(command))})
            applied.append(dict(name=proposal['name'], type=proposal['type'], result=result))
            record['proposals'] = applied
            self.save(record)
            if not result.get('ok'):
                raise Refused('proposal_refused:' + proposal['name'], str(result.get('reason')))
            if proposal['type'] == 'grooming':
                outcome = service.groom(command['item'])
                applied.append(dict(name=proposal['name'] + '/groom', type='grooming', result=outcome))
                self.save(record)
                if not outcome.get('ok'):
                    raise Refused('proposal_refused:' + proposal['name'] + '/groom', str(outcome.get('reason')))
        for unit in value['decomposition']:
            self.staged(record, unit, team)
        record['document'] = value
        record['elaboration'] = {'state': 'done', 'dispatch': record['dispatch']} if value['decomposition'] else None
        record['state'] = 'waiting_owner' if value['owner_questions'] else ('proposed' if applied else 'no_action')
        return record

    def staged(self, record, unit, team):
        held = row(self.conn, unit['unit'])
        assignments = CT.assignments(self.conn, unit['unit'])
        if not held or held['data'].get('state') != 'READY' or not assignments:
            raise Refused('missing_evidence:staged_unit')
        bound = held['data'].get('specification_document')
        accepted = row(self.conn, 'document/%s/%s@%s' % (self.repository, bound['alias'], bound['version'])) if bound else None
        body = accepted['data']['content'] if accepted else ''
        if any(text not in body for text in [unit['requirements'], unit['owner_message'], *unit['references']]):
            raise Refused('missing_evidence:requirements')
        assignment = assignments[-1]
        if assignment['team']['revision'] != team['revision'] or assignment['builder'] in assignment['reviewers']:
            raise Refused('missing_evidence:staffing')
        record['unit_roles'] = {name: {'role': selected,
            'configuration': team['team']['roles'][selected]['capability_configuration']}
            for name, selected in unit['staffing'].items()}
        record['unit_assignment'] = assignment

    def returned_document(self, dispatched):
        if not self.execution_records or not dispatched.get('execution_record'):
            raise Refused('missing_evidence:proposal_document')
        reader = organ('control_execution_record')
        values, after = [], 0
        while True:
            page = reader.read(self.execution_records, dispatched['dispatch_id'], after, 4096,
                               committed=dispatched['execution_record'])
            for line in page['lines']:
                if line['stream'] != 'engine' or line.get('redacted'):
                    continue
                try:
                    value = json.loads(line['payload'])
                    if value.get('type') == 'result' and isinstance(value.get('result'), str):
                        value = json.loads(value['result'])
                    elif value.get('type') == 'item.completed' and value.get('item', {}).get('type') == 'agent_message':
                        value = json.loads(value['item']['text'])
                    if value.get('schema') == DOCUMENT:
                        values.append(value)
                except (ValueError, TypeError, AttributeError):
                    continue
            after += len(page['lines'])
            if after >= page['total'] or not page['lines']:
                break
        if len(values) != 1:
            raise Refused('missing_evidence:one_proposal_document')
        return values[0]

    def finish(self, record):
        dispatched = self.runner.dispatches.record(record['dispatch'])
        try:
            if not organ('control_dispatch').completed(dispatched):
                raise Refused('missing_evidence:pm_result')
            value = self.returned_document(dispatched)
            document(value)
            # Only a digest goes into the graph process. It cannot invoke owners.
            supplied = [{'id': 'result', 'version': 1, 'digest': SN.digest(SN.canonical(value)),
                         'value': {'unit': record['project']}}]
            answer = self.exchange(record, 'advance', supplied)
            if (answer['outcome'] != 'proposal' or len(answer['proposals']) != 1
                    or answer['proposals'][0]['evidence'] != [supplied[0]['digest'], WORKFLOW['digest']]):
                raise Refused('invalid_response:report')
            self.apply(record, value)
            record['trace'] = list(PIPELINE)
        except Exception as error:
            record.update(state='refused', refusal=getattr(error, 'code', 'unknown_outcome:' + type(error).__name__))
        self.counts['refused' if record['state'] == 'refused' else 'accepted'] += 1
        return self.save(record)

    def pass_once(self):
        """Called by the factory pass. One active cycle and one coalesced follow-up."""
        emitted = []
        projects = [json.loads(r[0]) for r in self.conn.execute("SELECT data FROM entities WHERE kind='project'")]
        for project in projects:
            name = project['name']
            if project.get('state') != 'ACTIVE' or project.get('execution_repository') != self.repository:
                continue
            current = self.inputs(name)
            active = next((r for r in self.records(name) if r['state'] not in FINAL), None)
            if active:
                if current != active['input_key']:
                    self.pending[name] = current
                dispatched = self.runner.dispatches.record(active.get('dispatch')) if active.get('dispatch') else None
                if dispatched and dispatched['state'] not in ('prepared', 'running', 'accepted'):
                    emitted.append(self.finish(active))
                    self.seen[name] = active['input_key']
                    if name in self.pending:
                        emitted.append(self.start(name, self.pending.pop(name)))
                continue
            if self.seen.get(name) != current:
                self.seen[name] = current
                try:
                    emitted.append(self.start(name, current))
                except Exception as error:
                    self.observe(dict(operation='pm_start', project=name,
                                      refusal=getattr(error, 'code', 'unknown_outcome:' + type(error).__name__)))
        return emitted


def from_line(line):
    """The authority service's factory line supplies its Runner and owning services."""
    service = line.service
    modules = line.run.__func__.__globals__
    store, membership, assignment = modules['S'], modules['CM'], modules['I']
    ids = dict(domain_uuid=service.domain, repository_uuid=line.repository, store_uuid=service.store)
    signature = lambda body: modules['SIG'].sign_bytes(service.config['journal_key'], body,
                                                       modules['AC'].SIGNATURE_NAMESPACE)
    inbox = service.inbox(line.repository)
    backlog_module = organ('control_backlog')
    backlog = backlog_module.Backlog(store, membership, service.conn, ids, service.principal, service.sign,
                                    workspace=line.workspace, authority_generation=service.generation)
    teams = CT.Teams(store, membership, service.conn, ids, service.principal, service.sign,
                     inbox=inbox, assignment=assignment, requester=service.principal, request_sign=signature,
                     authority_generation=service.generation)
    services = {'inbox': inbox, 'backlog': backlog, 'teams': teams}
    allocations = organ('control_alias').attach(store, service.conn, service.domain, {line.repository: line.workspace})
    publisher = organ('control_document').Publisher(allocations, line.workspace, service.verify,
                                                    service.config['host_identity'])
    services['decomposition'] = organ('control_decomposition').Decomposition(backlog, allocations, publisher)
    channel = getattr(service, 'channel', None)
    if channel is not None:
        ingress = channel.ingress
        services['grooming'] = organ('control_grooming').Grooming(store, membership, service.conn, ids,
            service.principal, service.sign, backlog=backlog_module, service=backlog, assignment=assignment,
            inbox=ingress.inbox, presenter=ingress.presenter, settlement=ingress.settlement,
            requester=(service.principal, signature), workspace=line.workspace,
            authority_generation=service.generation)
    return ProjectCycles(store, service.conn, domain=service.domain, repository=line.repository,
        workspace=line.workspace, principal=service.principal, sign=service.sign, command_sign=signature,
        runner=line.runner, adapters=line.engines, services=services, generation=service.generation,
        execution_records=line.records, observe=service._log)
