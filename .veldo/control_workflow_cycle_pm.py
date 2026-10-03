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
                 runner, adapters, services, generation=1, runtime=None, stage=None, observe=None):
        self.store, self.conn = store, conn
        self.domain, self.repository, self.workspace = domain, repository, str(workspace)
        self.principal, self.sign, self.command_sign = principal, sign, command_sign
        self.runner, self.adapters, self.services = runner, adapters, services
        self.generation, self.runtime, self.stage = generation, runtime, stage
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
                'objectives': {'kind': 'objective', 'where': {'project': '$name'}},
                'decisions': {'kind': 'assignment', 'where': {}},
                'dispatches': {'kind': 'dispatch_record', 'where': {}}}})

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
                        or kind == 'objective' and data.get('project') == project
                        or kind == 'assignment' and project in data.get('scope', []) and data.get('answer')
                        or kind == 'dispatch_record' and (data.get('contract') or {}).get('reservation', {}).get('project') == project
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
        engine = accepted['definition']['engine']
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
        for unit in value['decomposition']:
            for name in unit['staffing'].values():
                if name not in team['team']['roles']:
                    raise Refused('missing_authority:staffing_role')
        applied = []
        for proposal in value['proposals']:
            service_name, method = HANDLERS[proposal['type']]
            service = self.services.get(service_name)
            if service is None:
                raise Refused('unavailable_service:proposal_owner:' + service_name)
            command = copy.deepcopy(proposal['command'])
            command.update(principal=self.principal, command_id='pm-proposal/' + record['cycle'] + '/' + proposal['name'],
                           nonce='pm-proposal/' + record['cycle'] + '/' + proposal['name'])
            result = getattr(service, method)({'command': command,
                'signature': self.command_sign(self.store.canonical_bytes(command))})
            applied.append(dict(name=proposal['name'], type=proposal['type'], result=result))
            record['proposals'] = applied
            self.save(record)
            if not result.get('ok'):
                raise Refused('proposal_refused:' + proposal['name'], str(result.get('reason')))
        record['document'] = value
        record['elaboration'] = {'state': 'done', 'dispatch': record['dispatch']} if value['decomposition'] else None
        record['state'] = 'waiting_owner' if value['owner_questions'] else ('proposed' if applied else 'no_action')
        return record

    def finish(self, record, value=None):
        dispatched = self.runner.dispatches.record(record['dispatch'])
        try:
            if not organ('control_dispatch').completed(dispatched):
                raise Refused('missing_evidence:pm_result')
            if value is None:
                raise Refused('missing_evidence:proposal_document')
            self.apply(record, value)
            # Only a digest goes into the graph process. It cannot invoke owners.
            supplied = [{'id': 'result', 'version': 1, 'digest': SN.digest(SN.canonical(value)),
                         'value': {'unit': record['project']}}]
            answer = self.exchange(record, 'advance', supplied)
            if answer['outcome'] != 'proposal':
                raise Refused('invalid_response:report')
            record['trace'] = list(PIPELINE)
        except Exception as error:
            record.update(state='refused', refusal=getattr(error, 'code', 'unknown_outcome:' + type(error).__name__))
        self.counts['refused' if record['state'] == 'refused' else 'accepted'] += 1
        return self.save(record)

    def pass_once(self, results=None):
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
                    emitted.append(self.finish(active, (results or {}).get(active['dispatch'])))
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
