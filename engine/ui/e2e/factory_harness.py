#!/usr/bin/env python3
"""The factory UI's harness (VELDO-0131): VELDO-0163's team harness (itself VELDO-0145's real factory) with
every read model the factory screens show populated, the journal feed served, and the workflow service on.

WHAT IT ADDS, on the same store connection and authority thread:

- THE JOURNAL FEED. The real VELDO-0051 Projection (control_event_projection.Projection) over the store's file,
  handed to the real control_api_authority as its `publication`, so `events.read` and `events.stream` serve the
  committed records the live screens follow. Every write this harness makes outside the authority's own
  commands is followed by the authority's post-commit hint to the API (`deliver`), exactly as an accepted
  command's notify is, so an open events stream receives it.
- THE WORKFLOW SERVICE. The real VELDO-0132 Workflows (control_workflow.Workflows) handed to the authority as
  its `workflows`, with one workflow saved through it by the owner (`delivery`), so `reads.workflow` and
  `workflows.save` execute the real service.
- THE OWNER'S WORK COMMANDS (VELDO-0131, owner Telegram 38184). The real control_backlog Backlog,
  control_dispatch Dispatches and control_accounts Accounts on the authority's connection, handed to the real
  control_api_authority, so `backlog.reprioritize`, `workers.stop` and `workers.cap` execute the real commands.
  The account is registered through Accounts (its writer owns the kind). No runner holds a receiver here, so a
  stop request stays recorded with its ask pending, as in the authority service.
- THE READ MODELS' RECORDS, in their writers' stored shapes (the shapes control_objective, control_backlog,
  control_proof, control_landing and control_reservations write; see the docstrings there): objectives of
  project-a and factory, backlog items with priorities and a blocker, the execution units under them, a proof
  bundle with its gate observation, a completion receipt for one landed unit, and the account policy, worker
  and invocation reservations of the usage screen. They are written as store entities (upsert_entity, the
  harness's existing `fixture`) because those writers need real git repositories, intake proposals and worker
  processes that a browser test does not have; the API reads them through its real read models, digests and
  member scope. These records are fixtures and certify the screens only, never the writers.

THE CONTROL PORT adds:
  /factory/upsert   {id, kind, data}   write one entity and deliver the hint (a live update the screens see)
  /factory/entity   {id}               the stored entity (kind, version, data) or null
  /factory/kind     {kind}             every stored entity of a kind (id, version, data)
  /factory/deliver  {}                 deliver the journal head's hint to the API
  /factory/workflow {workflow}         the head revision the workflow service stores

Run: python3 -B engine/ui/e2e/factory_harness.py --dist engine/ui/dist
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402
import team_harness as T  # noqa: E402

REPOSITORY = 'e2e-repository'
WORKFLOW = 'delivery'


def sha(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def seed_workflow():
    definition = {
        'schema': 'veldo.workflow/v1', 'id': WORKFLOW, 'entry': 'groom', 'terminal': ['finish'],
        'nodes': {'groom': {'kind': 'grooming', 'config': {}},
                  'wait': {'kind': 'owner_wait', 'config': {}},
                  'finish': {'kind': 'result_handling', 'config': {}}},
        'transitions': [{'id': 't1', 'from': 'groom', 'port': 'groomed', 'to': 'wait'},
                        {'id': 't2', 'from': 'wait', 'port': 'admit', 'to': 'finish'},
                        {'id': 't3', 'from': 'wait', 'port': 'decline', 'to': 'finish'}],
        'references': {}, 'budget': {'steps': 8}}
    layout = {'nodes': {'groom': {'x': 40, 'y': 60}, 'wait': {'x': 280, 'y': 60}, 'finish': {'x': 520, 'y': 60}},
              'viewport': {'x': 0, 'y': 0, 'zoom': 1}}
    return {'definition': definition, 'layout': layout}


class FactoryUi(T.TeamFactory):
    def _build(self):
        super()._build()
        organs, S, conn, ids = self.organs, self.S, self.conn, self.ids
        WF = H.load('e2e_factory_workflow', organs / 'control_workflow.py')
        EP = H.load('e2e_factory_projection', organs / 'control_event_projection.py')
        root = self.base / 'repository'
        (root / '.veldo').mkdir(parents=True, exist_ok=True)
        self.authority.publication = EP.Projection(S, str(self.base / 'authority' / 'control.sqlite3'),
                                                   domain=ids['domain_uuid'], repository=ids['repository_uuid'],
                                                   root=str(root))
        self.workflows = WF.Workflows(S, conn, domain=ids['domain_uuid'], repository=ids['repository_uuid'],
                                      signer='authority', sign=self.journal_sign)
        self.authority.workflows = self.workflows
        self.workflows.save(seed_workflow(), principal='owner', base=0)
        # VELDO-0131: the writers of the owner's backlog priority, worker stop and account cap.
        AUTH = H.load('e2e_factory_authority', organs / 'control_api_authority.py')
        self.authority.backlog = AUTH.BL.Backlog(S, self.CM, conn, ids, 'authority', self.journal_sign)
        self.authority.dispatches = AUTH.DP.Dispatches(S, conn, domain=ids['domain_uuid'], repository=ids['repository_uuid'],
                                                       principal='pm', signer='authority', sign=self.journal_sign)
        self.accounts = AUTH.AA.Accounts(S, conn, principal='owner', signer='authority', sign=self.journal_sign)
        self.authority.accounts = self.accounts
        # A second revision of the team's capability configuration, selecting the Atlassian server (VELDO-0127's
        # real writer), so the configuration and catalog screens have a history and a selected server to show.
        self.configurations.save(dict(role='general', engine='claude_code',
                                      native_tools=[dict(name='Read', load='always'), dict(name='Bash', load='when assigned')],
                                      mcp=[dict(server='atlassian', revision=1, tools=['jira_search'], load='always')],
                                      skills=[], instructions=[], settings={}),
                                 principal='owner', base=1, command_id=self.next_id('general2'))
        # VELDO-0131 fix round 2: a configuration no team names, a credential record and a server no configuration
        # selects that references it (the configuration and catalog screens list every stored one), the Git
        # identities and their repository bindings (VELDO-0142's setup tables, through its own writer).
        self.configurations.save(dict(role='reviewer', engine='claude_code', native_tools=[dict(name='Grep', load='always')],
                                      mcp=[], skills=[], instructions=[], settings={}),
                                 principal='owner', base=0, command_id=self.next_id('reviewer'))
        credential = self.authority.mcp_credentials.apply(
            'set_mcp_credential', dict(id='github-token', base=0, label='GitHub token for the factory',
                                       value='e2e-' + 'x' * 24), principal='owner', command_id=self.next_id('credential'))
        self.catalog.save(dict(id='github', label='GitHub', transport='stdio', command='github-mcp', arguments=['stdio'],
                               url=None, environment={'GITHUB_TOKEN': {'reference': credential['reference']}},
                               headers={}, hosts=['linux', 'mac'], read_only_tools=['get_issue']),
                          principal='owner', base=0, command_id=self.next_id('github'))
        GI = H.load('e2e_factory_git_identity', organs / 'control_git_identity.py')
        work = dict(id='work', label='Work', author_name='Factory Owner', author_email='owner@example.com',
                    remote_host='github.com', remote_owner='acme', api_token='keychain:veldo/e2e-api-token',
                    push_credential={'kind': 'token', 'reference': 'keychain:veldo/e2e-push-token'},
                    projects_root='/srv/veldo/projects', default_visibility='private')
        GI.configure_identities(conn, ids['domain_uuid'], [work, dict(work, id='personal', label='Personal',
                                author_email='me@example.com', remote_owner='me', default_visibility='public')],
                                {REPOSITORY: {'path': '/srv/veldo/projects/importer', 'identity': 'work'}})
        self._factory_seed()

    def _factory_seed(self):
        now = time.time()
        ids = self.ids
        objectives = {
            'objective:a1': ('project-a', 'ACTIVE', 'Parse every customer file the old importer accepted, with no silent drops.',
                             ['importer', 'parser'], 2),
            'objective:a2': ('project-a', 'PROPOSED', 'Report import failures to the owner within one minute.',
                             ['reporting'], 0),
            'objective:f1': ('factory', 'SATISFIED', 'Run the factory UI on phone and desktop.', ['ui'], 1),
        }
        for oid, (project, state, outcome, scope, features) in objectives.items():
            self.fixture(oid, 'objective', dict(
                schema='veldo.objective/v1', uuid=oid, entity_type='objective', domain_uuid=ids['domain_uuid'],
                repository_uuid=ids['repository_uuid'], project=project, project_uuid='project:' + project,
                proposal_id='proposal:' + oid, state=state, revision=1,
                bound={'outcome': outcome, 'scope': scope, 'authority': {'acceptor': 'owner', 'assessor': 'owner'},
                       'evidence_requirements': [{'id': 'gate', 'kind': 'gate_observation'}]},
                accepted_revision=1 if state != 'PROPOSED' else None, features=['feature-%d' % n for n in range(features)],
                assessment={'outcome': 'satisfied', 'evidence': ['gate-observation:131']} if state == 'SATISFIED' else None,
                history=[]))
        items = [
            ('backlog:131-parser', 'objective:a1', 'Empty lines parse to an empty list', 'ACTIVE', 1, []),
            ('backlog:131-encoding', 'objective:a1', 'Detect the file encoding before parsing', 'PRIORITIZED', 2, []),
            ('backlog:131-report', 'objective:a1', 'Name the failing line in the import report', 'BLOCKED', 3,
             [{'block_id': 'block-1', 'phase': 'execution', 'reason': 'waiting on the owner\'s answer about report format',
               'by': 'pm', 'at': now - 3600, 'resolution': None}]),
            ('backlog:131-alerts', 'objective:a2', 'Alert the owner on an import failure', 'ADMITTED', None, []),
        ]
        for bid, objective, title, state, rank, blocks in items:
            self.fixture(bid, 'backlog_item', dict(
                schema='veldo.backlog_item/v1', uuid=bid, entity_type='backlog_item', domain_uuid=ids['domain_uuid'],
                repository_uuid=ids['repository_uuid'], project='project-a', project_uuid='project:project-a',
                objective_uuid=objective, feature_uuid='objective-feature:' + bid.split(':')[1], title=title,
                scope=['importer'], work_class='PRODUCT_CHANGE', state=state, decomposition_revision=1,
                decomposition_digest=sha(bid), decomposition=[],
                priority=({'path': 'owner_command', 'rank': rank, 'previous_rank': None, 'ruling': 'approve',
                           'principals': ['owner'], 'revision': 1, 'units': []} if rank else None),
                priorities=[], blocks=blocks, applied=[], completion=None, cancellation=None, history=[]))
        units = [
            ('unit-131-parse', 'backlog:131-parser', 'COMPLETED'),
            ('unit-131-tests', 'backlog:131-parser', 'RUNNING'),
            ('unit-131-detect', 'backlog:131-encoding', 'READY'),
            ('unit-131-report', 'backlog:131-report', 'AWAITING_AUTHORITY'),
            ('unit-131-built', 'backlog:131-parser', 'COMPLETED'),
        ]
        for uid, item, state in units:
            self.fixture(uid, 'execution_unit', dict(
                schema='veldo.backlog_unit/v1', uuid=uid, entity_type='execution_unit', state=state,
                domain_uuid=ids['domain_uuid'], repository_uuid=ids['repository_uuid'], backlog_item_uuid=item,
                project='project-a', primary_specification='VELDO-9' + uid[-4:], revision=1, depends_on=[], history=[]))
        # The gate's observation and the proof bundle of unit-131-parse, and its landing's completion receipt.
        # unit-131-built is COMPLETED in its own record with no receipt: the landing is not confirmed.
        stdout = 'suite 113: 7 rows green\nsuite 119: 10 rows green\nGATE: GREEN (6f1c2ab)\n'
        observation = dict(schema='veldo.gate_observation/v1', command=['bash', 'scripts/verify.sh'], commit='6f1c2ab' * 5 + 'ab',
                           gate={'path': 'scripts/verify.sh', 'digest': sha('gate')}, exit=0, stdout=stdout,
                           stdout_digest='sha256:' + hashlib.sha256(stdout.encode()).hexdigest(), stderr='',
                           stderr_digest='sha256:' + hashlib.sha256(b'').hexdigest(), terminal='GATE: GREEN (6f1c2ab)',
                           green=True, started_at=now - 7200, finished_at=now - 7100, capture='e2e',
                           domain=ids['domain_uuid'], repository=REPOSITORY)
        self.fixture('gate-observation:131-parse', 'gate_observation', observation)
        red = 'suite 113: 7 rows green\nsuite 119: 9 of 10 rows green; team/widths red\nGATE: RED (5e0b19a)\n'
        self.fixture('gate-observation:131-parse-red', 'gate_observation', dict(
            observation, commit='5e0b19a' * 5 + 'ab', exit=1, stdout=red, green=False, terminal='GATE: RED (5e0b19a)',
            stdout_digest='sha256:' + hashlib.sha256(red.encode()).hexdigest(), started_at=now - 9000, finished_at=now - 8900))
        self.fixture('proof-bundle:131-parse', 'proof_bundle', dict(
            schema='veldo.proof_bundle/v1', unit='unit-131-parse', source={'commit': '6f1c2ab' * 5 + 'ab'},
            base='1a2b3c4' * 5 + 'cd', implementation={'commit': '6f1c2ab' * 5 + 'ab'},
            spec={'path': 'specs/VELDO-9131-parser.md', 'revision': 2, 'criteria': ['AC1', 'AC2'],
                  'required_evidence': ['unit', 'integration']},
            manifest={'location': 'proof/VELDO-9131/manifest.json', 'path': 'proof/VELDO-9131/manifest.json',
                      'digest': sha('manifest'), 'body': {'AC1': 'tests/test_parser.py', 'AC2': 'proof/VELDO-9131/red.log'}},
            artifacts=[{'criterion': 'AC1', 'type': 'unit', 'path': 'tests/test_parser.py', 'digest': sha('t')},
                       {'criterion': 'AC2', 'type': 'integration', 'path': 'proof/VELDO-9131/red.log', 'digest': sha('r')}],
            checks=[{'name': 'gate', 'status': 'passed', 'command': 'bash scripts/verify.sh', 'observed': True,
                     'gate_exit': 0, 'observation': 'gate-observation:131-parse'},
                    {'name': 'review', 'status': 'passed', 'command': 'independent review', 'observed': True,
                     'gate_exit': 0, 'observation': 'gate-observation:131-parse'}],
            producer='w-build', builder='w-build', domain=ids['domain_uuid'], repository=REPOSITORY,
            observation={'id': 'gate-observation:131-parse', 'digest': sha(observation)},
            accepted={'at': now - 7000, 'principal': 'pm'}))
        self.land('unit-131-parse')
        # The repository records (control_repository's stored shape): this factory's repository, adopted and active,
        # and one whose creation failed with its named reason.
        self.fixture('repository:' + REPOSITORY, 'repository', dict(
            schema='veldo.repository/v1', repository=REPOSITORY, name='importer', identity='work',
            path='/srv/veldo/projects/importer',
            remote={'url': 'git@github.com:acme/importer.git', 'owner': 'acme', 'default_branch': 'main'},
            origin='adopted', state='active', updated_at=now - 600,
            history=[{'step': 'settled', 'state': 'provisioning', 'at': now - 900},
                     {'step': 'enrolled', 'state': 'active', 'at': now - 600}]))
        self.fixture('repository:e2e-billing', 'repository', dict(
            schema='veldo.repository/v1', repository='e2e-billing', name='billing', identity='work',
            path='/srv/veldo/projects/billing', remote={'url': None, 'owner': 'acme', 'default_branch': 'main'},
            origin='created', state='failed', reason='remote_exists', updated_at=now - 300,
            history=[{'step': 'settled', 'state': 'provisioning', 'at': now - 400},
                     {'step': 'remote', 'state': 'failed', 'at': now - 300, 'reason': 'remote_exists'}]))
        # The account the reservations charge (control_accounts' stored shape), so usage names its provider.
        self.accounts.register(self.next_id('account'), 'owner-plan', 'claude_code', "Owner's plan",
                               {'veldo-linux-1': '/srv/veldo/profiles/owner-plan'}, now=now - 86400)
        # The usage screen: one account's policy with its windows, two workers, and their invocations, one
        # settled with its tokens and one whose tokens are unknown.
        account = 'owner-plan'
        self.fixture('reservation:policy:131-account', 'subscription_reservation', dict(
            type='policy', scope='account', subject=account,
            caps={'capacity': 2, 'invocations': 400, 'wall_seconds': 36000, 'messages': 900},
            windows={'5h': {'window_id': '5h', 'unit': 'messages', 'remaining': 120, 'reset_at': now + 2 * 3600,
                            'watermark': 3, 'outstanding': [], 'store_watermark': 1},
                     'weekly': {'window_id': 'weekly', 'unit': 'messages', 'remaining': 0, 'reset_at': now + 30 * 3600,
                                'watermark': 2, 'outstanding': [], 'store_watermark': 1}}))
        self.fixture('reservation:policy:131-project', 'subscription_reservation', dict(
            type='policy', scope='project', subject='project-a', caps={'capacity': 2, 'invocations': 200, 'wall_seconds': 18000}))
        for n, (dispatch, unit) in enumerate((('dispatch/131/a', 'unit-131-parse'), ('dispatch/131/b', 'unit-131-tests'))):
            context = {'domain': ids['domain_uuid'], 'repository': ids['repository_uuid'], 'account': account,
                       'project': 'project-a', 'unit': unit}
            self.fixture('reservation:worker:131-%d' % n, 'subscription_reservation', dict(
                type='worker', dispatch=dispatch, context=context, retired=n == 0, reserved_seq=1))
            for k in range(3):
                head = self.conn.execute('SELECT COALESCE(MAX(seq),0)+1 FROM journal').fetchone()[0]
                known = n == 0
                self.fixture('reservation:invocation:131-%d-%d' % (n, k), 'subscription_reservation', dict(
                    type='invocation', dispatch=dispatch, invocation='inv-%d-%d' % (n, k), boundary='turn',
                    wall_seconds=60 + 30 * k, context=context,
                    charge={'invocations': 1, 'wall_seconds': 60 + 30 * k, **({'tokens': 1800 + 400 * k, 'messages': 1} if known else {})},
                    reserved={'invocations': 1, 'wall_seconds': 60 + 30 * k},
                    observed={'tokens': 1800 + 400 * k, 'messages': 1} if known else {},
                    unknown=[] if known else ['tokens', 'messages'], state='settled' if known else 'unknown',
                    sequence=1, reports={}, outcome='completed', accepted_seq=head))
        self.deliver()

    def land(self, unit):
        """The landing's completion receipt for `unit` (control_landing's stored shape)."""
        dispatch = 'dispatch/%s/landing' % unit
        receipt = 'receipt:revision_landed:%s:%s' % (unit, hashlib.sha256(dispatch.encode()).hexdigest()[:16])
        self.fixture(receipt, 'completion_receipt', dict(
            fact='revision_landed', subject={'id': unit, 'revision': 1},
            publication_receipt={'implementation_commit': '6f1c2ab' * 5 + 'ab', 'proof_digest': sha(unit),
                                 'unit_id': unit, 'dispatch_id': dispatch, 'candidate_commit': '6f1c2ab' * 5 + 'ab'},
            remote_confirmation={'remote': 'origin', 'tip': '6f1c2ab' * 5 + 'ab'}, replicated=True, spec_shipped_event=None))
        return receipt

    def deliver(self):
        if self.api_box:
            return self.api.deliver(self.on_thread(self.authority.hint))
        return None

    def upsert(self, eid, kind, data):
        self.on_thread(self.fixture, eid, kind, data)
        return self.deliver()

    def entity(self, eid):
        row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
        return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

    def entities(self, kind):
        return [{'id': r[0], 'version': r[1], 'data': json.loads(r[2])}
                for r in self.conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', (kind,))]


BASE_CONTROL = T.control_server


def control_server(factory, stop):
    server = BASE_CONTROL(factory, stop)
    handler = server.RequestHandlerClass
    route = handler.route

    def extended(self, path, body):
        f = factory
        if path == '/factory/upsert':
            return {'delivered': f.upsert(body['id'], body['kind'], body['data'])}
        if path == '/factory/land':
            receipt = f.on_thread(f.land, body['unit'])
            return {'receipt': receipt, 'delivered': f.deliver()}
        if path == '/factory/entity':
            return {'entity': f.on_thread(f.entity, body['id'])}
        if path == '/factory/kind':
            return {'entities': f.on_thread(f.entities, body['kind'])}
        if path == '/factory/deliver':
            return {'delivered': f.deliver()}
        if path == '/factory/workflow':
            return {'workflow': f.on_thread(f.workflows.load, body.get('workflow', WORKFLOW), body.get('version'))}
        return route(self, path, body)
    handler.route = extended
    return server


def main():
    H.Factory = FactoryUi
    H.control_server = control_server
    H.main()


if __name__ == '__main__':
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    main()
