"""VELDO-0174: durable conversations, ordered turns, shared-pool priority and receiver binding.

Run: python3 scripts/selftest.py --suite 107_veldo_0174_conversations

Only ROOT, expect and fast_temp are consumed.  The suite uses real signed SQLite authority stores,
OpenSSH identities, default-team and capability records, the production conversation authority,
VELDO-0039 dispatch records, Runner preparation and account-pool selection.  Installer layout is
rendered over a real enrolled Git workspace with the host-profile qualification seam fixed to a
portable positive record; no service, login, socket, user unit or real engine is started.
"""


def _v174_suite():
    import importlib.util
    import inspect
    import json
    import os
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import tempfile
    import time

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    CV = load('v174_conversation', ROOT / ".veldo" / "control_conversation.py")
    L = load('v174_launch', ROOT / ".veldo" / "control_launch.py")
    CS = load('v174_service', ROOT / ".veldo" / "control_service.py")
    E = load('v174_enrollment', ROOT / ".veldo" / "control_enrollment.py")
    H = load('v174_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    rows = {}

    def check(row, label, condition):
        rows.setdefault(row, []).append((label, bool(condition)))

    def refusal(call):
        try:
            call()
        except Exception as error:
            return getattr(error, 'code', type(error).__name__)
        return None

    base = Path(tempfile.mkdtemp(prefix='v174-', dir=fast_temp()))
    fixtures = []

    def fixture(tag, providers=('claude_code',), account_count=1):
        root = base / tag
        root.mkdir(parents=True)
        authority = H.build(root / 'authority', ROOT / '.veldo', 17400 + len(fixtures),
                            'http://127.0.0.1:1', 'fixture', scope='activation-repository')
        authority.admin('steward', 'enroll_principal', {
            'principal': 'authority', 'principal_type': 'service', 'roles': ['reservation_service'],
            'public_key': authority.public['authority'], 'independence_group': 'authority', 'scope': '*'
        }, enrollee='authority')
        authority.fixture('launch-receiver', 'membership', {
            'principal_type': 'service', 'roles': ['reservation_service'], 'scope': '*',
            'revoked_at': None, 'expires_at': None})
        revisions = {}
        roles = {}
        for index, provider in enumerate(dict.fromkeys(providers), 1):
            role_name = 'assistant' if index == 1 else 'assistant_' + provider
            definition = {'role': role_name, 'engine': provider, 'native_tools': [], 'mcp': [], 'skills': [],
                          'instructions': [], 'settings': {}}
            saved = dict(definition, revision=1, previous=None)
            saved['digest'] = CV.CFG.digest(saved)
            authority.fixture('configuration:' + role_name, 'agent_configuration', saved)
            revisions[role_name] = saved
            roles[role_name] = {
                'kind': 'specialist', 'capability_configuration': {'role': role_name, 'revision': 1},
                'workers': [role_name + '-worker'], 'responsibilities': ['assist'], 'expertise': ['general'],
                'proposal_permissions': [], 'engines': [provider],
                'budget': {'capacity': 4, 'invocations': 20, 'wall_seconds': 300,
                           'tokens': 100000, 'messages': 100},
                'independence': {'distinct_from': []}}
        default = {'revision': 1, 'team': {'roles': roles}, 'saved_by': 'owner',
                   'assertion_digest': 'sha256:fixture', 'previous': None, 'digest': 'sha256:default-one'}
        authority.fixture('default-team:1', 'default_team_revision', default)
        authority.fixture('default-team:head', 'default_team_head', {'revision': 1})
        host = socket.gethostname()
        for index in range(account_count):
            provider = providers[index % len(providers)]
            account = 'account-%s-%d' % (provider, index + 1)
            profile = root / ('profile-' + account)
            profile.mkdir(parents=True)
            authority.fixture('account:' + account, 'account', {
                'id': account, 'provider': provider, 'label': account, 'profiles': {host: str(profile)},
                'concurrency': 1, 'status': 'active', 'windows': {}})
        conversations = CV.Conversations(
            authority.S, authority.conn, domain=authority.ids['domain_uuid'], principal='authority',
            signer='authority', sign=authority.journal_sign, state_root=root / 'state')
        found = {'root': root, 'authority': authority, 'conversations': conversations,
                 'revisions': revisions, 'roles': roles, 'host': host}
        fixtures.append(found)
        return found

    def runner(f, adapters):
        authority = f['authority']
        reservations = L.D.RES.Reservations(
            authority.S, authority.conn, domain=authority.ids['domain_uuid'], repository=None,
            principal='authority', authorize=L.D.RES.service_authority,
            signer='authority', sign=authority.journal_sign, subject_kind='conversation')
        dispatches = L.D.Dispatches(
            authority.S, authority.conn, domain=authority.ids['domain_uuid'], repository=None,
            principal='authority', signer='authority', sign=authority.journal_sign,
            subject_kind='conversation')
        pool = L.D.RES.POOL.Pool({name: {'engine': engine, 'host': f['host']} for name, engine in adapters.items()})
        return L.Runner(None, reservations, dispatches, lambda _contract: None, account=pool), dispatches

    def prepare(run, f, identity, turn, role='assistant', adapter='claude_code'):
        conversation = f['conversations'].read(identity)
        revision = CV.role_at(f['authority'].conn, role)[1]
        subjects = ([('account', account['id']) for account in L.D.RES.POOL.accounts(f['authority'].conn)]
                    + [('project', identity), ('unit', identity)])
        for scope, subject in subjects:
            entity = L.D.RES.entity('policy', [f['authority'].ids['domain_uuid'], scope, subject])
            if f['authority'].conn.execute('SELECT 1 FROM entities WHERE id=?', (entity,)).fetchone() is None:
                run.reservations.configure('v174-policy/%s/%s' % (scope, subject), scope, subject,
                    {'capacity': 10, 'invocations': 100, 'wall_seconds': 1000,
                     'tokens': 1000000, 'messages': 1000}, now=time.time())
        return run.prepare_conversation(
            identity, turn['sequence'], intake_digest=turn['intake_digest'], adapter=adapter,
            configuration={'role': role, 'revision': revision['revision']}, role_revision=revision,
            payload={'owner': conversation['owner'], 'intake_command': turn['intake_command']},
            deadline=time.time() + 30)

    try:
        # AC1: durable standalone versioned record and owner-only close.
        f1 = fixture('ac1')
        c1, a1 = f1['conversations'], f1['authority']
        opened = c1.open('conversation-one', owner='owner', intake_digest='sha256:open-one')
        reopened = CV.Conversations(a1.S, a1.conn, domain=a1.ids['domain_uuid'], principal='authority',
                                    signer='authority', sign=a1.journal_sign,
                                    state_root=f1['root'] / 'state').read('conversation-one')
        check('AC1/restart-open', 'a new service object reads the same open version 1 record from the store',
              reopened == opened and opened['status'] == 'open' and opened['version'] == 1)
        before = c1.read('conversation-one')
        stale = refusal(lambda: c1.close('conversation-one', 0, owner='owner'))
        other = refusal(lambda: c1.close('conversation-one', 1, owner='steward'))
        unchanged = c1.read('conversation-one') == before
        closed = c1.close('conversation-one', 1, owner='owner')
        check('AC1/version-owner', 'stale and non-owner closes are named and change nothing; the owner closes version 1',
              stale == 'stale_version' and other == 'missing_authority:conversation_owner' and unchanged
              and closed['status'] == 'closed' and closed['version'] == 2)
        check('AC1/not-project', 'the record has no repository, backlog, charter or trunk and no project entity',
              not ({'repository', 'backlog', 'charter', 'trunk'} & set(opened))
              and a1.conn.execute('SELECT 1 FROM entities WHERE id=?', ('project:conversation-one',)).fetchone() is None)

        # AC2: three owner messages queue, only one dispatch is active, and a later turn binds the new role revision.
        f2 = fixture('ac2', account_count=2)
        c2 = f2['conversations']
        c2.open('ordered', owner='owner', intake_digest='sha256:ordered-open')
        turns = [c2.message('ordered', 'message-%d' % number, 'sha256:message-%d' % number, owner='owner')
                 for number in (1, 2, 3)]
        run2, dispatches2 = runner(f2, {'claude_code': 'claude_code'})
        first = prepare(run2, f2, 'ordered', turns[0])
        c2.dispatched('ordered', 1, first['dispatch_id'], 1, first['reservation']['account'], 'conversations')
        active_refusal = refusal(lambda: prepare(run2, f2, 'ordered', turns[1]))
        check('AC2/one-active-ordered', 'sequences are gapless and turn 2 stays waiting while turn 1 holds the station',
              [t['sequence'] for t in c2.turns('ordered')] == [1, 2, 3]
              and [t['state'] for t in c2.turns('ordered')] == ['dispatched', 'waiting', 'waiting']
              and active_refusal.startswith('active_dispatch:'))
        conversation_run = inspect.getsource(CS.ConversationLine.run)
        check('AC2/one-offer-per-pass', 'the Line marks a conversation offered before considering its next waiting turn',
              "if turn['conversation'] in offered:" in conversation_run
              and "offered.add(turn['conversation'])" in conversation_run)
        dispatches2.refuse(first['dispatch_id'], dispatches2.record(first['dispatch_id'])['contract_digest'],
                           'fixture_end', now=time.time())
        run2._retire(first['dispatch_id'], 'cancelled', 'never_spawned')
        c2.ended('ordered', 1, first['dispatch_id'], 'fixture_end')
        second = prepare(run2, f2, 'ordered', turns[1])
        c2.dispatched('ordered', 2, second['dispatch_id'], 1, second['reservation']['account'], 'conversations')
        dispatches2.refuse(second['dispatch_id'], dispatches2.record(second['dispatch_id'])['contract_digest'],
                           'fixture_end', now=time.time())
        run2._retire(second['dispatch_id'], 'cancelled', 'never_spawned')
        c2.ended('ordered', 2, second['dispatch_id'], 'fixture_end')
        definition = dict(f2['revisions']['assistant'], revision=2,
                          previous=f2['revisions']['assistant']['digest'])
        definition['digest'] = CV.CFG.digest({k: v for k, v in definition.items() if k != 'digest'})
        f2['authority'].fixture('configuration:assistant:2', 'agent_configuration', definition)
        role2 = json.loads(json.dumps(f2['roles']['assistant']))
        role2['capability_configuration']['revision'] = 2
        f2['authority'].fixture('default-team:2', 'default_team_revision', {
            'revision': 2, 'team': {'roles': {'assistant': role2}}, 'saved_by': 'owner',
            'assertion_digest': 'sha256:two', 'previous': 'sha256:default-one', 'digest': 'sha256:default-two'})
        f2['authority'].fixture('default-team:head', 'default_team_head', {'revision': 2})
        third = prepare(run2, f2, 'ordered', turns[2])
        c2.dispatched('ordered', 3, third['dispatch_id'], 2, third['reservation']['account'], 'conversations')
        check('AC2/current-role-revision', 'the next turn binds accepted role revision 2 after the owner changes it',
              third['capability']['configuration']['role_revision']['revision'] == 2
              and c2.turns('ordered')[2]['role_revision'] == 2)

        # Review regressions: command redelivery and reservation admission are real transactions.
        original = c2.message('ordered', 'replay-message', 'sha256:replay', owner='owner', command_id='replay')
        c2.message('ordered', 'later-message', 'sha256:later', owner='owner')
        replayed = c2.message('ordered', 'replay-message', 'sha256:replay', owner='owner', command_id='replay')
        check('AC2/redelivery', 'the original command returns its original turn after a later message',
              replayed == original and len(c2.turns('ordered')) == 5)
        fcap = fixture('caps')
        fcap['conversations'].open('capped', owner='owner', intake_digest='sha256:capped')
        capped = fcap['conversations'].message('capped', 'capped-message', 'sha256:capped', owner='owner')
        rcap, _ = runner(fcap, {'claude_code': 'claude_code'})
        rcap.reservations.configure('cap-domain', 'domain', fcap['authority'].ids['domain_uuid'],
                                   {'capacity': 0, 'invocations': 100, 'wall_seconds': 1000}, now=time.time())
        denied = refusal(lambda: prepare(rcap, fcap, 'capped', capped))
        check('AC2/domain-cap', 'a domain at capacity starts no turn and reserves no worker',
              denied is not None and not any(v.get('type') == 'worker' for v in rcap.reservations._records().values()))
        invalid = json.loads(json.dumps(third)); invalid['subject_kind'] = 'project'
        invalid['repository'] = 'fixture'
        check('AC4/turn-kind', 'a project contract cannot use the turn station',
              'station' in L.D.contract_problems(invalid))
        check('AC1/unknown-conversation', 'unknown conversations have a named refusal',
              refusal(lambda: c1.message('absent', 'absent-message', 'sha256:absent', owner='owner'))
              == 'invalid_input:conversation:unknown')

        # AC3: three conversations occupy three accounts, and a waiting turn consumes the only slot first.
        f3 = fixture('ac3', account_count=3)
        run3, _dispatches3 = runner(f3, {'claude_code': 'claude_code'})
        contracts = []
        for number in (1, 2, 3):
            identity = 'parallel-%d' % number
            f3['conversations'].open(identity, owner='owner', intake_digest='sha256:open-%d' % number)
            turn = f3['conversations'].message(identity, 'parallel-message-%d' % number,
                                               'sha256:parallel-%d' % number, owner='owner')
            contract = prepare(run3, f3, identity, turn)
            f3['conversations'].dispatched(identity, 1, contract['dispatch_id'], 1,
                                           contract['reservation']['account'], 'conversations')
            contracts.append(contract)
        check('AC3/parallel-conversations', 'three conversations reserve three distinct shared account slots',
              len({c['reservation']['account'] for c in contracts}) == 3)
        f31 = fixture('ac3-priority', account_count=1)
        run31, _dispatches31 = runner(f31, {'claude_code': 'claude_code'})
        f31['conversations'].open('priority', owner='owner', intake_digest='sha256:priority-open')
        priority_turn = f31['conversations'].message('priority', 'priority-message', 'sha256:priority', owner='owner')
        priority = prepare(run31, f31, 'priority', priority_turn)
        records = run31.reservations.conn.execute(
            'SELECT id, data FROM entities WHERE kind=?', (CV.WORKER_KIND,)).fetchall()
        choice_while_turn = CV.POOL.choose(f31['authority'].conn,
            {key: json.loads(data) for key, data in records},
            {'engine': 'claude_code', 'host': f31['host']}, time.time(), lambda _account: None)
        run31.cancel_prepared(priority, 'fixture_end')
        records = run31.reservations.conn.execute(
            'SELECT id, data FROM entities WHERE kind=?', (CV.WORKER_KIND,)).fetchall()
        choice_after = CV.POOL.choose(f31['authority'].conn,
            {key: json.loads(data) for key, data in records},
            {'engine': 'claude_code', 'host': f31['host']}, time.time(), lambda _account: None)
        check('AC3/turn-first-slot', 'the turn takes the one free slot and project work can take it after the turn ends',
              choice_while_turn['account'] is None and choice_after['account'] == priority['reservation']['account'])
        loop_run = inspect.getsource(CS.FactoryLoop.run)
        check('AC3/turn-before-project', 'the loop calls its conversation Line before iterating repository Lines',
              loop_run.index('self.conversation.run') < loop_run.index('for repository, line in sorted(self.lines.items())'))

        # AC4: installer layout always writes the repository-free receiver and both kinds reject the other contract.
        f4 = fixture('ac4')
        workspace = f4['authority'].config['workspace']
        Path(workspace, 'README').write_text('conversation receiver fixture\n')
        subprocess.run(['git', '-C', workspace, 'add', 'README'], check=True, capture_output=True)
        subprocess.run(['git', '-C', workspace, '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', 'commit', '-q', '-m', 'fixture'],
                       check=True, capture_output=True)
        E.enroll(workspace, f4['authority'].ids['domain_uuid'], f4['authority'].ids['store_uuid'],
                 str(f4['authority'].db), 'v73-host', 1,
                 lambda data: f4['authority'].sign_as('steward', data, 'veldo-enrollment'), 'steward',
                 '2026-10-10T00:00:00Z', repository_uuid=f4['authority'].ids['repository_uuid'])
        original_qualify = CS.C.qualify
        CS.C.qualify = lambda _profile: {'qualified': True, 'refusal': None}
        try:
            key_directory = f4['authority'].keyfile['authority'].parent
            layout = CS.layout([workspace], host_trust=str(f4['authority'].config['host_trust']),
                               key_directory=str(key_directory), install_root=str(f4['root'] / 'installed'),
                               unit_dir=str(f4['root'] / 'units'), profile={'portable': True},
                               adapters={'claude_code': {'engine': 'claude_code', 'argv': ['/bin/true']}},
                               writable=[], state_root=str(f4['root'] / 'factory-state'))
        finally:
            CS.C.qualify = original_qualify
        conversation_path = layout['config']['receiver']['conversations']
        receiver = layout['receivers'].get(conversation_path) or {}
        check('AC4/install-conversation-receiver', 'installation without work writes and names one conversation receiver',
              layout['config']['work'] is None and receiver.get('receiver_kind') == 'conversation'
              and receiver.get('state_root') == str(f4['root'] / 'factory-state')
              and 'repository' not in receiver and 'workspace' not in receiver)
        project_contract = {'station': 'build'}
        conversation_contract = {'subject_kind': 'conversation', 'station': 'turn'}
        check('AC4/receiver-kind-refusal', 'each receiver kind refuses the other contract before spawn',
              L.receiver_kind_problem(receiver, project_contract) == 'binding_mismatch:conversation_receiver'
              and L.receiver_kind_problem({'receiver_kind': 'project'}, conversation_contract)
              == 'binding_mismatch:conversation_receiver')
        check('AC4/no-work-line', 'the no-work installation is loop-configured by its conversation receiver',
              bool(layout['config']['receiver']['conversations']) and not layout['config']['work']
              and 'if conversation_receiver else None' in inspect.getsource(CS.FactoryLoop.__init__))
    except Exception as error:
        import traceback
        traceback.print_exc()
        for row in ('AC1/restart-open', 'AC1/version-owner', 'AC1/not-project',
                    'AC2/one-active-ordered', 'AC2/one-offer-per-pass', 'AC2/current-role-revision',
                    'AC3/parallel-conversations', 'AC3/turn-first-slot', 'AC3/turn-before-project',
                    'AC4/install-conversation-receiver', 'AC4/receiver-kind-refusal', 'AC4/no-work-line'):
            check(row, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        for fixture_value in fixtures:
            fixture_value['authority'].conn.close()
        shutil.rmtree(base, ignore_errors=True)
    for row in sorted(rows):
        failed = [label for label, ok in rows[row] if not ok]
        if failed:
            print('  VELDO-0174 detail:', row, '; '.join(failed))
        expect('VELDO-0174 ' + row, bool(rows[row]) and not failed)


_v174_suite()
