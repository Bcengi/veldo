"""Trusted-store read fixture: real SQLite journal, generated signing key, real publication readers.

Seed records mirror the owning writers' fields. This suite judges readers, not authorization
of these seed writes. No service is started and no external engine or account is used.
"""
import contextlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_transition(params, before):
    return params['changes']


@contextlib.contextmanager
def fixture(root, production):
    with tempfile.TemporaryDirectory(prefix='v164-') as directory:
        base = Path(directory)
        organs = base / 'installed'
        organs.mkdir()
        for path in (root / '.veldo').glob('*.py'):
            shutil.copyfile(path, organs / path.name)
        for name, source in production.items():
            shutil.copyfile(source, organs / name)
        A = load('v164_authority', organs / 'control_api_authority.py')
        S = load('v164_store', organs / 'control_store.py')
        CM = A.CM
        API = load('v164_api', organs / 'control_api.py')
        TR = load('v164_team_routes', organs / 'control_team_routes.py')
        EP = load('v164_publication', organs / 'control_event_projection.py')
        key = base / 'journal-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True)
        def sign(message):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-journal'],
                                  input=message, capture_output=True, check=True).stdout.decode()
        db = base / 'control.sqlite3'
        conn = S.open_store(str(db))
        lock = os.open(base / 'authority.lock', os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        conn.command_registry['seed_read_fixture'] = dict(transition=seed_transition,
            writes=('entities', 'journal', 'commands', 'nonces'))
        counter = 0
        def commit(changes):
            nonlocal counter
            counter += 1
            expected = {}
            for identity in changes:
                row = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
                expected[identity] = row[0] if row else 0
            return S.execute(conn, dict(command_id='seed-' + str(counter), principal='fixture',
                operation='seed_read_fixture', parameters=dict(changes=changes), expected_versions=expected,
                artifact_digests=[], nonce='seed-' + str(counter)), 'fixture', sign, 1)
        def put(identity, kind, **data):
            return commit({identity:dict(kind=kind, data=data)})
        for principal, scope in (('owner','*'), ('reader',['A']), ('outside',['C']), ('other',['B']), ('factory-reader',['factory'])):
            put(principal, 'membership', principal_type='person', roles=['project_owner'], scope=scope,
                revoked_at=None, expires_at=None)
        for kind in ('role_configuration', 'tool_configuration'):
            put(kind, kind, label=kind, token='do not disclose')
        # Use the actual default team's kind and identity, not a project team stand-in.
        put(TR.default_id(1), TR.KIND, revision=1, team={'roles':{}}, saved_by='owner', previous=None)
        workflows = {p:A.WF.Workflows(S,conn,domain='domain',repository=p,signer='fixture',sign=sign)
                     for p in ('A','B')}
        put(TR.HEAD, 'default_team_head', revision=1)
        expected = {'A':{}, 'B':{}}
        for project in expected:
            def row(kind, data, identity=None):
                identity = identity or kind + ':' + project
                put(identity, kind, **data)
                expected[project][kind] = identity
                return identity
            unit = 'unit-' + project
            request = 'request-' + project
            proposal = 'proposal-' + project
            row('project', dict(name=project, execution_repository=project), 'project:' + project)
            row('objective', dict(project=project))
            context = dict(candidates=['A','B'], projects=[
                dict(id=p, name=p, ticket_key_prefixes=['AAA' if p=='A' else 'BBB']) for p in ('A','B')],
                project_versions={'project:A':1, 'project:B':1, 'project:factory':1})
            row('intake_proposal', dict(project=project, proposal='objective', state='PROPOSED',
                context=context, decision=dict(context, hints=['A','B'], shared_ticket_keys=['A','B']),
                hints=['A','B']), proposal)
            row('intake_question', dict(proposal_id=proposal))
            row('backlog_item', dict(project=project))
            for kind in ('accepted_document','document_version','accepted_revision'):
                row(kind, dict(repository_uuid=project, content='Document of ' + project))
            row('execution_unit', dict(project=project), unit)
            row('dispatch', dict(contract={'reservation':{'project':project}, 'unit':unit},
                process={'platform':'linux','host':'host-' + project}, state='running'))
            row('dispatch_active', dict(unit=unit))
            row('workflow_cycle', dict(subject=unit))
            row('assignment', dict(scope=[project], subject={'ref':'settlement_terms:' + project}), request)
            row('settlement_terms', dict(target={'ref':unit}))
            for kind in ('request_settlement','channel_presentation'):
                row(kind, dict(request_id=request))
            row('decision_settlement', dict(settlement={'request_id':request}))
            row('decision', dict(subject={'kind':'spec','id':unit}))
            row('proof_bundle', dict(unit=unit))
            row('gate_observation', dict(repository=project))
            row('completion_receipt', dict(subject={'id':unit}))
            row('subscription_reservation', dict(type='worker', context={'project':project}))
            row('team', dict(project=project, revision=1, team={'roles':{}}), 'team:' + project)
            WF = A.WF
            definition = dict(schema='veldo.workflow/v1', id='build', entry='done', terminal=['done'],
                nodes={'done':{'kind':'result_handling','config':{}}}, transitions=[],
                references={'roles':{},'tools':{}}, budget={'steps':1})
            workflows[project].save(dict(definition=definition,layout={}),principal='owner',base=0)
            expected[project][WF.REVISION_KIND] = WF.revision_id('domain',project,'build',1)
            expected[project][WF.HEAD_KIND] = WF.head_id('domain',project,'build')
        put('project:factory','project',name='factory',execution_repository='factory')
        inbox_ids = []
        for state in ('AWAITING_ROUTE','AWAITING_PROJECT','NEW_PROJECT','ROUTED'):
            pid = 'unrouted' if state == 'AWAITING_ROUTE' else 'inbox-' + state
            inbox_ids.append(pid)
            put(pid, 'intake_proposal', project='factory', proposal='inbox', state=state,
                text='Unrouted private request', context=context,
                resolved_to='proposal-B' if state=='ROUTED' else None)
            qid = 'question-' + state
            inbox_ids.append(qid)
            put(qid, 'intake_question', proposal_id=pid, candidates=['A','B','a new project'],
                project='B' if state=='ROUTED' else None,
                prompt='Which project is this for? A, B, a new project')
        put('account-policy','subscription_reservation',type='policy',scope='account',subject='account')
        publication = EP.Projection(S, db, domain='domain',repository='A',root=base)
        authority = A.ApiAuthority(S,CM,conn,ids=dict(domain_uuid='domain',repository_uuid='A',store_uuid='store'),
            domain='domain',edge='edge',intake=SimpleNamespace(projects=['A','B','factory']),settlement=None,credentials=None,
            publication=publication,workflows=workflows['A'],authority_lock=lock)
        try:
            yield SimpleNamespace(**locals())
        finally:
            conn.close()
            os.close(lock)
