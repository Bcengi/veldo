"""VELDO-0174: durable conversations, ordered turns, shared-pool priority and receiver binding.

Run: python3 scripts/selftest.py --suite 123_veldo_0174_conversations

Only ROOT, expect and fast_temp are consumed.  The suite uses real signed SQLite authority stores,
OpenSSH identities, default-team and capability records, the production conversation authority,
VELDO-0039 dispatch records, Runner preparation and account-pool selection.  Installer layout is
rendered over a real enrolled Git workspace. Real service restart and receiver subprocesses run over
fixture accounts and pinned fake engines. No real login or user unit is used. A denied service socket
is a host-required failure, never a passing restart row.
"""


def _v174_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import sys
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
    # Signed commands must use the same production copy selected by the mutation driver,
    # including its Refused type and its durable command registration.
    CS.CV = CV
    MUTATIONS = ROOT / "scripts" / "check_teeth_mutations.py"
    E = load('v174_enrollment', ROOT / ".veldo" / "control_enrollment.py")
    H = load('v174_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v174_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    rows = {name: [] for name in (
        'proof/mutation-dependencies',
        'proof/signed-command-module',
        'AC1/durable-store',
        'AC1/mutation-targets',
        'AC1/not-project',
        'AC1/project-commands',
        'AC1/project-owner',
        'AC1/project-scope',
        'AC1/restart-open',
        'AC1/unknown-conversation',
        'AC1/version-owner',
        'AC1/versioned-mutations',
        'AC2/account-retry',
        'AC2/active-refusal-once',
        'AC2/charged-windows',
        'AC2/closed-dispatch',
        'AC2/current-role-revision',
        'AC2/domain-cap',
        'AC2/durable-recovery',
        'AC2/one-active-ordered',
        'AC2/one-offer-per-pass',
        'AC2/own-directory',
        'AC2/real-ordered-turns',
        'AC2/receiver-loss',
        'AC2/redelivery',
        'AC2/role-skills',
        'AC2/role-tools',
        'AC2/restart-turns',
        'AC3/parallel-conversations',
        'AC3/three-running',
        'AC3/turn-before-project',
        'AC3/turn-first-slot',
        'AC4/install-conversation-receiver',
        'AC4/no-work-line',
        'AC4/real-kind-refusal',
        'AC4/receiver-kind-refusal',
        'AC4/turn-kind',
        'AC4/unit-to-conversation',
    )}

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
        organs = ROOT / '.veldo'
        if tag.startswith('live'):
            organs = root / 'modules'
            shutil.copytree(ROOT / '.veldo', organs, ignore=shutil.ignore_patterns('__pycache__'))
        authority = H.build(root / 'authority', organs, 17400 + len(fixtures),
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
        account_module = load('v174_accounts_'+tag,organs / 'control_accounts.py')
        accounts = account_module.Accounts(authority.S,authority.conn,principal='owner',signer='authority',sign=authority.journal_sign)
        for index in range(account_count):
            provider = providers[index % len(providers)]
            account = 'account-%s-%d' % (provider, index + 1)
            profile = root / ('profile-' + account)
            profile.mkdir(parents=True)
            accounts.register('account-register-'+account,account,provider,account,{host:str(profile)},
                              concurrency=1,now=time.time())
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

    def priority_journey(factory, live, cv, markers, CS, L):
        repository, line = J.project_line(live, factory, CS, E)
        factory.lines[repository] = line
        cv.open('priority-live',owner='owner',intake_digest='sha256:priority-live')
        cv.message('priority-live','priority-live-1','sha256:priority-live-1',owner='owner')
        try:
            offered = J.pass_(factory)
            first = (bool(offered['conversation_offered']) and not line.runner.launches
                     and any(e.get('unit') == 'build-unit' for e in offered['waiting']))
            next_pass = J.drain(factory, markers)
            builds = [e for e in next_pass['offered'] if e.get('unit') == 'build-unit']
            started = bool(builds) and builds[0]['result'] == 'accepted'
            if started:
                build = line.runner.launches[builds[0]['dispatch_id']]
                J.eventually(lambda: build.pump(), 10)
                line.runner.wait(build, timeout=3)
                line.activate()
                contract = line.runner.prepare('build-unit', 'build', holder='project-builder',
                    source=line.workspace, revision='HEAD', payload={}, adapter='claude_code',
                    configuration={}, deadline=time.time()+30)
                kind_events = []
                receiver = L.Receiver(factory.conversation.receiver, kind_events.append)
                try:
                    receiver.launch(contract)
                finally:
                    receiver.close()
                check('AC4/unit-to-conversation', 'actual conversation receiver refuses the real project build contract',
                      kind_events[-1].get('refusal') == 'binding_mismatch:conversation_receiver')
                line.runner.cancel_prepared(contract, 'fixture_kind_check')
            if not first or not started:
                print('  VELDO-0174 priority:', [{k:r[k] for k in ('offered','waiting','refused','faults')}
                                               for r in (offered, next_pass)])
            return first and started
        finally:
            for launch in list(line.runner.launches.values()):
                J.eventually(lambda: launch.pump(), 10)
                line.runner.wait(launch, timeout=3)
            # The stand-in stops serving the project's repository, so VELDO-0188's follow_store builds no line
            # for it at later passes.
            factory.service.repositories.pop(repository, None)
            factory.lines.clear()

    try:
        # Import real no-op layouts from the registry without running the mutation driver.
        # Group identical layouts, but include the module: service and conversation have
        # different transitive imports. A missing sibling is a failed row, not a crash.
        bytecode_disabled = sys.dont_write_bytecode
        try:
            driver = load('v174_mutation_catalog', MUTATIONS)
        finally:
            sys.dont_write_bytecode = bytecode_disabled
        # A catalog mutant is isolated; its referenced qualification fixtures stay here.
        driver.ROOT = ROOT
        cases = [case for case in driver.cases() if case['finding'] == 174
                 and case['module'] in ('control_conversation.py', 'control_service.py')]
        check('proof/mutation-dependencies', 'both production modules have registered falsifiers',
              {case['module'] for case in cases} == {'control_conversation.py', 'control_service.py'})
        layouts = set()
        for case in cases:
            layout = (case['module'], case.get('siblings', False), tuple(case.get('companions', ())))
            if layout in layouts:
                continue
            layouts.add(layout)
            try:
                made = driver.materialize(case, 'noop', base / 'noops' / case['name'], root=ROOT)
                module = load('v174_noop_' + case['name'], made['mutant'])
                check('proof/mutation-dependencies', case['name'] + ' imports its unchanged isolated copy',
                      Path(module.__file__).resolve() == made['mutant'].resolve()
                      and made['mutant'].read_bytes() == made['source'].read_bytes())
            except Exception as error:
                check('proof/mutation-dependencies', case['name'] + ': ' + str(error), False)

        # AC1: durable standalone versioned record and owner-only close.
        f1 = fixture('ac1')
        c1, a1 = f1['conversations'], f1['authority']
        persisted, reread = J.restart(f1, CS, ROOT, identity='store-persistence', serve=False)
        check('AC1/durable-store', 'separate authority processes read the same open record from SQLite without a service socket',
              persisted is not None and persisted == reread and reread['status'] == 'open')
        try:
            opened, reopened = J.restart(f1, CS, ROOT, identity='conversation-one')
            check('AC1/restart-open', 'real service stop and start preserve the open record',
                  opened is not None and reopened == opened and reopened['version'] == 1 and reopened['status'] == 'open')
        except Exception as error:
            check('AC1/restart-open', 'real service restart: '+str(error)[-350:], False)
            opened = c1.read('conversation-one')
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

        PJ = load('v174_project', ROOT / '.veldo/control_project.py')
        project_service = PJ.Projects(a1.S,a1.CM,a1.conn,a1.ids,'authority',a1.journal_sign,stop=lambda *a:None)
        refused_projects=[]
        for operation in PJ.OPERATIONS:
            command=dict(a1.ids,operation=operation,project='conversation-one',principal='owner',
                         command_id='not-project-'+operation,nonce='not-project-'+operation)
            refused_projects.append(project_service.apply({'command':command,'signature':'fixture'})['reason'])
        check('AC1/project-commands','all project commands refuse a conversation identity',
              refused_projects==['invalid_input:conversation']*len(PJ.OPERATIONS))

        # AC1's record mutations travel through signed owner commands, including replay.
        fv = fixture('versions', providers=('claude_code', 'codex'))
        av = fv['authority']
        owner_roles = CV._row(av.conn, 'owner')['data']['roles']
        def owner_scope(scope):
            av.admin('steward', 'change_roles', {'principal': 'owner', 'roles': owner_roles,
                                                'scope': scope})
            return CV._row(av.conn, 'owner')['data']['scope'] == scope
        assert owner_scope(['activation-repository', 'attachment', 'another-owner'])
        service = CS.Service(J.service_config(fv, CS), av.conn)
        check('proof/signed-command-module', 'signed service commands bind the selected conversation authority and refusal type',
              CS.CV is CV and type(service.conversations()) is CV.Conversations)
        def owner_command(operation, parameters, who='owner', command_id=None):
            command = dict(av.ids, operation=operation, parameters=parameters, principal=who,
                           command_id=command_id or av.next_id('conversation'), nonce=av.next_id('nonce'))
            packet = {'command': command, 'signature': av.sign_as(who, av.S.canonical_bytes(command))}
            return service.conversation_command(packet, command, av.ids['repository_uuid'], {})
        opened = owner_command(CV.OPEN, {'conversation': 'versioned'})['conversation']
        av.fixture('project:attachment', 'project', {'name': 'attachment', 'owner': 'owner'})
        rejected = []
        for operation, field, value in [(CV.ROLE, 'role', 'assistant_codex'),
                                         (CV.ATTACH, 'project', 'attachment')]:
            params = {'conversation': 'versioned', 'version': 0, field: value}
            rejected.append(owner_command(operation, params)['reason'] == 'stale_version')
            params['version'] = 1
            rejected.append(owner_command(operation, params, 'steward')['reason']
                            == 'missing_authority:conversation_owner')
        rejected.append(service.conversations().read('versioned') == opened)
        changed = owner_command(CV.ROLE, {'conversation': 'versioned', 'version': 1,
                                         'role': 'assistant_codex'}, command_id='change-role')['conversation']
        attached = owner_command(CV.ATTACH, {'conversation': 'versioned', 'version': 2,
                                            'project': 'attachment'})['conversation']
        replay = owner_command(CV.ROLE, {'conversation': 'versioned', 'version': 1,
                                        'role': 'assistant_codex'}, command_id='change-role')['conversation']
        check('AC1/versioned-mutations', 'signed role and project changes reject stale versions and non-owners; replay preserves the original result',
              all(rejected) and changed['version'] == 2 and changed['role'] == 'assistant_codex'
              and attached['version'] == 3 and attached['project'] == 'attachment' and replay == changed
              and not ({'repository', 'workspace', 'backlog', 'charter', 'trunk'} & set(attached)))
        invalid = [owner_command(CV.ROLE, {'conversation': 'versioned', 'version': 3, 'role': 'absent'})['reason'],
                   owner_command(CV.ATTACH, {'conversation': 'versioned', 'version': 3, 'project': 'absent'})['reason'],
                   owner_command(CV.CLOSE, {'conversation': 'versioned', 'version': 1})['reason']]
        closed = owner_command(CV.CLOSE, {'conversation': 'versioned', 'version': 3})['conversation']
        refused_closed = owner_command(CV.ROLE, {'conversation': 'versioned', 'version': 4,
                                               'role': 'assistant'})['reason']
        check('AC1/mutation-targets', 'unknown roles and projects leave the version unchanged; closed conversations refuse edits',
              invalid == ['invalid_input:conversation_role:absent', 'invalid_input:conversation_project', 'stale_version']
              and closed['version'] == 4 and refused_closed == 'stale_subject:conversation_closed')

        # A signed project_owner still cannot attach another owner's project (VELDO-0177 AC3).
        owner_command(CV.OPEN, {'conversation': 'scoped'})
        own = owner_command(CV.ATTACH, {'conversation': 'scoped', 'version': 1,
                                      'project': 'attachment'})['conversation']
        av.fixture('project:another-owner', 'project', {'name': 'another-owner', 'owner': 'steward'})
        before = CV._row(av.conn, CV.conversation_id('scoped'))
        foreign = owner_command(CV.ATTACH, {'conversation': 'scoped', 'version': own['version'],
                                          'project': 'another-owner'})
        check('AC1/project-owner', 'signed project owner cannot replace its attachment with another owner\'s project; durable record and version stay unchanged',
              foreign == {'ok': False, 'reason': 'missing_authority:project'}
              and own['project'] == 'attachment' and own['version'] == 2
              and CV._row(av.conn, CV.conversation_id('scoped')) == before)

        # Ownership survives a scope change; attachment authority must not.
        owner_command(CV.OPEN, {'conversation': 'unattached'})
        for scope in (['activation-repository'], []):
            updated = owner_scope(scope)
            for identity in ('unattached', 'scoped'):
                before = CV._row(av.conn, CV.conversation_id(identity))
                denied = owner_command(CV.ATTACH, {'conversation': identity,
                    'version': before['data']['version'], 'project': 'attachment'})
                check('AC1/project-scope', 'signed scope removal refuses attachment without changing the durable row: '+identity,
                      updated and denied == {'ok': False, 'reason': 'missing_authority:project'}
                      and CV._row(av.conn, CV.conversation_id(identity)) == before
                      and CV._row(av.conn, 'project:attachment')['data']['owner'] == 'owner')
        for scope in (['attachment'], 'attachment', '*', ['*']):
            updated = owner_scope(scope)
            before = service.conversations().read('unattached')
            allowed = owner_command(CV.ATTACH, {'conversation': 'unattached',
                'version': before['version'], 'project': 'attachment'})
            saved = service.conversations().read('unattached')
            check('AC1/project-scope', 'restored named or universal scope permits a fresh signed attachment',
                  updated and allowed.get('ok') is True and allowed.get('conversation') == saved
                  and saved['project'] == 'attachment' and saved['version'] == before['version'] + 1)

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

        # A real receiver checks status before binding any engine or spawning anything.
        c2.close('ordered',1,owner='owner')
        observed=[]
        receiver_config={'store':str(f2['authority'].db),'domain':f2['authority'].ids['domain_uuid'],
                         'principal':'launch-receiver','journal_key':str(f2['authority'].keyfile['authority']),
                         'receiver_kind':'conversation','adapters':{'claude_code':{'argv':['/bin/false']}}}
        actual_receiver=L.Receiver(receiver_config,observed.append)
        try:
            actual_receiver.launch(third)
        finally:
            actual_receiver.close()
        check('AC2/closed-dispatch','receiver refuses a turn closed after preparation before spawning',
              observed[0].get('refusal')=='stale_subject:conversation_closed')
        run2._retire(third['dispatch_id'],'cancelled','never_spawned')

        # Temporary refusals retry the shared pool before ending or deferring the turn.
        from types import SimpleNamespace
        retry_fixture=fixture('retry',account_count=2)
        retry_cv=retry_fixture['conversations']; retry_authority=retry_fixture['authority']
        retry_cv.open('retry-turn',owner='owner',intake_digest='sha256:retry')
        retry_turn=retry_cv.message('retry-turn','retry-message','sha256:retry-message',owner='owner')
        retry_path=retry_fixture['root']/'receiver.json'
        retry_path.write_text(json.dumps(dict(receiver_config,store=str(retry_authority.db),
            domain=retry_authority.ids['domain_uuid'],host=retry_fixture['host'],
            adapters={'claude_code':{'engine':'claude_code','argv':['/bin/false']}})))
        service=SimpleNamespace(conn=retry_authority.conn,domain=retry_authority.ids['domain_uuid'],
            principal='authority',generation=1,sign=retry_authority.journal_sign,conversations=lambda:retry_cv)
        line=CS.ConversationLine(SimpleNamespace(service=service),str(retry_path))
        initial=prepare(line.runner,retry_fixture,'retry-turn',retry_turn)
        line.runner.cancel_prepared(initial,'fixture_setup')
        accounts_tried=[]
        def temporarily_refused(contract):
            account=contract['reservation']['account']; accounts_tried.append(account)
            line.dispatches.refuse(contract['dispatch_id'],L.D.digest(contract),
                'host_trust_required:fixture' if len(accounts_tried)==1 else 'fixture_finished',now=time.time())
            launch=L.Launch(None,contract,line.dispatches,time.time); launch._settle(lost=False)
            return launch
        line.runner.receiver=temporarily_refused
        report={key:[] for key in ('offered','conversation_offered','refused','waiting','faults')}
        line.offer(retry_turn,report)
        check('AC2/account-retry','a temporary host refusal tries a different account in the same turn',
              len(accounts_tried)==2 and len(set(accounts_tried))==2
              and len(retry_cv.turns('retry-turn')[0]['attempts'])==2)

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
        actual_receiver=L.Receiver(dict(receiver_config,store=str(f3['authority'].db),
            domain=f3['authority'].ids['domain_uuid'],journal_key=str(f3['authority'].keyfile['authority']),
            receiver_kind='project',repository=f3['authority'].ids['repository_uuid']),observed.append)
        try:
            actual_receiver.launch(contracts[0])
        finally:
            actual_receiver.close()
        check('AC4/real-kind-refusal','actual repository receiver refuses a conversation contract',
              observed[-1].get('refusal')=='binding_mismatch:conversation_receiver'
              and observed[-1].get('metrics',{}).get('turn_kind_refusals')==1)

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
        repository_receiver = next(value for value in layout['receivers'].values()
                                   if value.get('receiver_kind') == 'project')
        check('AC4/install-conversation-receiver', 'installation without work writes and names one conversation receiver',
              layout['config']['work'] is None and receiver.get('receiver_kind') == 'conversation'
              and receiver.get('state_root') == str(f4['root'] / 'factory-state')
              and all(receiver.get(field) == repository_receiver.get(field) for field in
                      ('store', 'journal_key', 'principal', 'domain', 'authority_generation',
                       'host_trust', 'profile', 'adapters', 'state_root'))
              and 'repository' not in receiver and 'workspace' not in receiver)
        project_contract = {'station': 'build'}
        conversation_contract = {'subject_kind': 'conversation', 'station': 'turn'}
        check('AC4/receiver-kind-refusal', 'each receiver kind refuses the other contract before spawn',
              L.receiver_kind_problem(receiver, project_contract) == 'binding_mismatch:conversation_receiver'
              and L.receiver_kind_problem({'receiver_kind': 'project'}, conversation_contract)
              == 'binding_mismatch:conversation_receiver')
        # AC2/AC4: the real Line invokes both real receiver processes with pinned fake engines.
        live = fixture('live', providers=('claude_code','codex'), account_count=2)
        receiver_path, markers, mods = J.engines(ROOT, live, CS)
        factory, lock, logs = J.loop(live, CS, receiver_path)
        try:
            cv = live['conversations']
            for identity, role in [('claude-live','assistant'),('codex-live','assistant_codex')]:
                cv.open(identity,owner='owner',role=role,intake_digest='sha256:'+identity)
                cv.message(identity,identity+'-1','sha256:'+identity+'-1',owner='owner')
            report = J.pass_(factory)
            if any(e['result']!='accepted' for e in report['conversation_offered']):
                print('  VELDO-0174 launch refusals:',[(i,t['outcome']) for i in ('claude-live','codex-live') for t in cv.turns(i)])
            check('AC4/no-work-line','no work configuration still launches both engine turns',
                  len(report['conversation_offered']) == 2 and
                  all(e['result']=='accepted' for e in report['conversation_offered']))
            for number in (2,3):
                cv.message('claude-live','live-message-'+str(number),'sha256:'+str(number),owner='owner')
            busy = J.pass_(factory); again = J.pass_(factory)
            check('AC2/one-offer-per-pass','only one active turn, later messages remain waiting',
                  [t['state'] for t in cv.turns('claude-live')]==['dispatched','waiting','waiting']
                  and not busy['conversation_offered'] and not again['conversation_offered']
                  and len(busy['refused'])==1)
            check('AC2/active-refusal-once','waiting-turn refusal is emitted once across repeated passes',
                  sum('active_dispatch' in e.get('refusals',[]) for r in (busy,again) for e in r['refused'])==1)
            J.eventually(lambda:len(list(markers.glob('*.json')))>=2)
            observed=[json.loads(p.read_text()) for p in markers.glob('*.json')]
            check('AC2/role-tools','both fake executables observe exactly the accepted native tools and MCP sets',
                  {v['engine']:v['tools'] for v in observed}=={'claude_code':['Read'],'codex':['update_plan']}
                  and all(v['mcp']==[] for v in observed))
            check('AC2/role-skills', 'both engines read the accepted skill body from their actual launch inputs',
                  len(observed) == 2 and all(v['skills'] == {'conversation-help':
                      (live['root']/'state/conversation-skill.md').read_text()} for v in observed))
            check('AC2/own-directory','each engine runs in its own durable conversation directory',
                  {v['cwd'] for v in observed}=={cv.read(i)['directory'] for i in ('claude-live','codex-live')})
            J.drain(factory,markers)
            J.drain(factory,markers)
            J.drain(factory,markers)
            check('AC2/real-ordered-turns','all three turns complete in message order',
                  [t['state'] for t in cv.turns('claude-live')]==['ended']*3
                  and all(t['outcome']=='completed' for t in cv.turns('claude-live')))
            ledger=factory.conversation.reservations._records()
            invocations=[v for v in ledger.values() if v.get('type')=='invocation']
            check('AC2/charged-windows','metered tokens are charged and reported account windows persist',
                  len(invocations)==4 and all(v['observed'].get('tokens')==15 for v in invocations)
                  and any(a.get('windows') for a in L.D.RES.POOL.accounts(live['authority'].conn)))
            check('AC3/turn-before-project','loop observes conversation offers before a pending project build',
                  priority_journey(factory, live, cv, markers, CS, L))
            # Killing the receiver exercises the ordinary unknown-outcome account release.
            (markers/'release').unlink(missing_ok=True)
            cv.open('lost-live',owner='owner',intake_digest='sha256:lost')
            cv.message('lost-live','lost-1','sha256:lost-1',owner='owner')
            loss=J.pass_(factory)
            current=cv.turns('lost-live')[0]
            launched=factory.conversation.runner.launches.get(current.get('dispatch_id'))
            if launched is not None:
                launched.child.kill(); launched.child.wait(timeout=5)
                factory.saw_end(factory.conversation,launched)
                J.pass_(factory,'run_end')
            worker=factory.conversation.reservations.worker(current.get('dispatch_id')) or {}
            check('AC2/receiver-loss','lost receiver records unknown outcome and frees its account slot',
                  bool(worker.get('account_released')) and cv.turns('lost-live')[0]['outcome']=='outcome_unknown')
            # Durable recovery also works with an empty, newly constructed Runner.
            cv.open('recover-live',owner='owner',intake_digest='sha256:recover')
            pending=cv.message('recover-live','recover-1','sha256:recover-1',owner='owner')
            J.pass_(factory)
            pending=cv.turns('recover-live')[0]
            receiver_launch=factory.conversation.runner.launches.get(pending.get('dispatch_id'))
            if receiver_launch:
                receiver_launch.child.kill(); receiver_launch.child.wait(timeout=5)
                from types import SimpleNamespace
                recovered=CS.ConversationLine(SimpleNamespace(service=factory.service),str(receiver_path))
                recovered.recover()
                check('AC2/durable-recovery','new Line reconciles persisted in-flight turns without its old Runner',
                      cv.turns('recover-live')[0]['state']=='ended'
                      and cv.turns('recover-live')[0]['outcome']=='outcome_unknown'
                      and bool(recovered.reservations.worker(pending['dispatch_id']).get('account_released')))
                factory.conversation.runner.launches.pop(pending['dispatch_id'],None)
            else:
                check('AC2/durable-recovery','fixture receiver started',False)

        finally:
            errors=live['root']/'receiver-errors.log'
            if errors.exists() and errors.stat().st_size: print('  VELDO-0174 receiver error:',errors.read_text()[-2500:])
            os.close(lock)
            for launch in list(factory.conversation.runner.launches.values()):
                launch.stop('fixture_cleanup')
                factory.conversation.runner.wait(launch,timeout=3)

        parallel = fixture('live-parallel', account_count=3)
        path, marks, _mods = J.engines(ROOT, parallel, CS)
        fleet, held_lock, _events = J.loop(parallel, CS, path)
        try:
            for number in (1, 2, 3):
                identity = 'simultaneous-' + str(number)
                parallel['conversations'].open(identity, owner='owner', intake_digest='sha256:'+identity)
                parallel['conversations'].message(identity, identity, 'sha256:'+identity, owner='owner')
            report = J.pass_(fleet)
            J.eventually(lambda: len(list(marks.glob('*.json'))) == 3)
            launches = list(fleet.conversation.runner.launches.values())
            if len(list(marks.glob('*.json'))) != 3:
                print('  VELDO-0174 parallel:', {k: report[k] for k in ('offered','refused','faults')})
                errors=parallel['root']/'receiver-errors.log'
                if errors.exists(): print('  VELDO-0174 parallel errors:', errors.read_text()[-1500:])
            check('AC3/three-running', 'three fake engines run concurrently on three shared accounts',
                  len(launches) == 3 and len(list(marks.glob('*.json'))) == 3
                  and all(launch.child.poll() is None and launch.result == 'accepted' for launch in launches)
                  and len({entry['account'] for entry in report['conversation_offered']}) == 3)
            J.drain(fleet, marks)
        finally:
            for launch in list(fleet.conversation.runner.launches.values()):
                launch.stop('fixture_cleanup')
                fleet.conversation.runner.wait(launch, timeout=3)
            os.close(held_lock)

        restarted = fixture('live-restart')
        path, marks, _mods = J.engines(ROOT, restarted, CS)
        (marks/'release').touch()
        try:
            before, after = J.restart(restarted, CS, ROOT, receiver=path, identity='restart-turns', turns=True)
            saved = restarted['conversations'].turns('restart-turns')
            check('AC2/restart-turns', 'the production service completes a turn before and after restarting over the same store',
                  before == after and len(saved) == 2 and all(t['outcome'] == 'completed' for t in saved))
        except Exception as error:
            check('AC2/restart-turns', 'real service restart: '+str(error)[-350:], False)
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
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0174 detail:', row, '; '.join(failed))
        expect('VELDO-0174 ' + row, bool(rows[row]) and not failed)


_v174_suite()
