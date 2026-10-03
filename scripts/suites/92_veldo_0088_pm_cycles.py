"""VELDO-0088: real signed project inputs, LangGraph and Runner coordination.
The fixture worker is a plain protocol process, not a Claude Code or Codex fake.
It makes no model call and supplies only predetermined proposal documents.
"""


def _v88_suite():
    import copy
    import importlib.util
    import json
    from pathlib import Path
    import subprocess
    import sys
    import time

    PRODUCTION = {
        'control_workflow_cycle_pm.py': ROOT / ".veldo" / "control_workflow_cycle_pm.py",
        'control_graph_pm.py': ROOT / ".veldo" / "control_graph_pm.py",
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_team.py': ROOT / ".veldo" / "control_team.py",
        'authority_contract.py': ROOT / ".veldo" / "authority_contract.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    names = ('cycle/runner', 'cycle/snapshot', 'cycle/no-action', 'cycle/failure',
             'proposal/unauthorized', 'proposal/stop-on-refusal', 'cycle/serialized',
             'cycle/pending-follow-up', 'cycle/budget', 'unit/one-run-staging', 'unit/factory-builder-ticket', 'unit/independent-review',
             'proposal/graph-process', 'cycle/combined-inputs', 'cycle/receipts', 'cycle/waiting-release')
    rows = {name: [] for name in names}

    def check(name, label, condition):
        rows[name].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    present = all(PRODUCTION[n].is_file() for n in ('control_workflow_cycle_pm.py', 'control_graph_pm.py'))
    if not present:
        for name in names:
            expect('VELDO-0088 ' + name, False)
        return
    helper = load('v88_fixture', Path(__suite_file__).resolve().parents[2] / 'proof/VELDO-0088/fixture.py')
    try:
        with helper.fixture(ROOT, PRODUCTION) as f:
            S, conn, base, mods = (f[k] for k in ('S', 'conn', 'base', 'mods'))
            domain, repository, ids = (f[k] for k in ('DOMAIN', 'REPO', 'ids'))
            PM = load('v88_pm', mods / 'control_workflow_cycle_pm.py')
            L = load('v88_launch', mods / 'control_launch.py')
            EL = load('v88_gate', mods / 'control_eligibility.py')
            RS = load('v88_snapshots', mods / 'control_readset.py')
            G = load('v88_graph', mods / 'control_graph.py')
            GP = load('v88_git', mods / 'git_process.py')
            sign = f['journal_sign']
            source = base / 'source'
            source.mkdir()
            (source / 'README').write_text('Accepted project source.\n')
            for args in (('init', '-q'), ('add', 'README'), ('commit', '-qm', 'Accepted source')):
                GP.run(['git', '-C', str(source), *args], check=True, capture_output=True,
                       identity=('Fixture', 'fixture@example.invalid'))
            commit = GP.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], check=True,
                            capture_output=True, text=True).stdout.strip()
            revisions = RS.attach_revisions(S, conn, domain, {repository: str(source)})
            revisions.accept('revision-88', repository, commit, 'pm',
                documents={'README': PM.SN.digest((source / 'README').read_bytes())}, signer='authority', sign=sign,
                authority_generation=1)
            common = dict(domain=domain, repository=repository, principal='pm', signer='authority', sign=sign)
            dispatches = L.D.Dispatches(S, conn, **common)
            reservations = L.D.RES.Reservations(S, conn, authorize=L.D.RES.service_authority, **common)
            for scope, subject in (('account', 'fixture-account'), ('project', 'proj-a')):
                reservations.configure('policy/' + subject, scope, subject,
                    dict(capacity=5, invocations=20, wall_seconds=1000), now=time.time())
            gate = EL.Gate(S, conn, domain_uuid=domain, repository_uuid=repository, workspace=source)
            result_file = base / 'answer.json'
            empty = dict(schema=PM.DOCUMENT, owner_questions=[], decomposition=[], proposals=[])
            result_file.write_text(json.dumps(empty))
            worker = base / 'worker.py'
            worker.write_text('import json,sys\nfrom pathlib import Path\np=json.load(sys.stdin)\n'
                'Path(sys.argv[2]).write_text(json.dumps(p))\nimport time\n'
                'if Path(sys.argv[3]).exists(): time.sleep(1)\n'
                'if p["station"] == "coordination": print(Path(sys.argv[1]).read_text())\n'
                'else:\n'
                ' import subprocess,os\n'
                ' until=time.monotonic()+10\n'
                ' while Path(sys.argv[4]).with_name("engineering-hold").exists() and time.monotonic()<until: time.sleep(.02)\n'
                ' if p["station"] == "build":\n'
                '  selection=p["configuration"]["role_revision"]["mcp"][0]\n'
                '  catalog=json.loads(Path(sys.argv[4]).read_text())\n'
                '  assert selection["server"] == catalog["id"] and selection["revision"] == catalog["revision"]\n'
                '  assert "BCG-123" in p["payload"]["requirements"]\n'
                '  q={"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"jira.get","arguments":{"key":"BCG-123"}}}\n'
                '  fetched=subprocess.run([catalog["command"],*catalog["arguments"]],input=json.dumps(q),text=True,capture_output=True,check=True)\n'
                '  print(fetched.stdout.strip())\n'
                ' print(json.dumps({"station":p["station"],"dispatch":p["dispatch_id"],"pid":os.getpid()}))\n')
            packet_file = base / 'packet.json'
            config = base / 'receiver.json'
            config.write_text(json.dumps(dict(store=str(f['db']), journal_key=str(f['keyfile']['authority']),
                principal='pm', workspace=str(source), domain=domain, repository=repository, records=str(base / 'records'),
                adapters={'protocol': {'identity': 'reported', 'argv': [sys.executable, '-B',
                    str(mods / 'control_launch.py'), 'exec', sys.executable, '-B', str(worker), str(result_file),
                    str(packet_file), str(base / 'hold'), str(base / 'catalog.json')]}})))
            runner = L.Runner(gate, reservations, dispatches,
                              lambda contract: L.invoke(config, contract, dispatches), account='fixture-account')
            runtime = G.resolve_runtime()
            if runtime:
                runtime['stage'] = str(base / 'graph-stage')
            cycles = PM.ProjectCycles(S, conn, domain=domain, repository=repository, workspace=source,
                principal='pm', sign=sign, command_sign=lambda b: f['sign_as']('pm', b), runner=runner,
                adapters={'protocol': 'claude_code'}, services={'inbox': f['inbox'], 'teams': f['service']},
                runtime=runtime, stage=str(base / 'graph-stage'), execution_records=base / 'records')
            first = cycles.start('proj-a', cycles.inputs('proj-a'))
            dispatch = dispatches.record(first.get('dispatch')) if first.get('dispatch') else None
            check('cycle/runner', 'coordination launch accepted', first['state'] == 'waiting_run')
            if dispatch:
                binding = dispatch['contract']
                check('cycle/runner', 'ordinary Runner contract and team configuration',
                      binding['station'] == 'coordination' and binding['capability']['configuration']['role_revision']['role']
                      == 'team-fixture' and binding['reservation'] == first['reservation'])
                launch = runner.launches[first['dispatch']]
                ended = runner.wait(launch, timeout=15)
                print('  VELDO-0088 detail: first dispatch state: ' + str(ended.get('state')))
                first = cycles.finish(first)
            else:
                print('  VELDO-0088 detail: first cycle: ' + str(first.get('refusal')))
            print('  VELDO-0088 detail: result:', first['state'], first.get('refusal'))
            check('cycle/no-action', 'empty result produces bound receipt and actual graph trace',
                  first['state'] == 'no_action' and first['trace'] == list(PM.PIPELINE)
                  and PM.row(conn, 'pm-cycle:' + first['cycle'])['data'] == first)
            snap = PM.SN.load(S, conn, first['snapshot']['id'], domain, repository)
            (source / 'README').write_text('Unaccepted edited source.\n')
            check('cycle/snapshot', 'snapshot keeps accepted source, watermark and input versions',
                first['accepted_commit'] == commit and first['watermark'] == snap['watermark']
                and first['input_versions'] == snap['inputs']
                and PM.SN.members(snap, source)['README'] == b'Accepted project source.\n')
            before = conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
            for kind, operation in (('shell', 'sh'), ('sql', 'update'), ('backlog', 'prioritize'), ('assignment', 'complete')):
                bad = dict(empty, proposals=[dict(name='bad', type=kind, command={'operation': operation})])
                try:
                    PM.document(bad)
                    rejected = False
                except PM.Refused:
                    rejected = True
                check('proposal/unauthorized', operation + ' is not a node operation', rejected)
            check('proposal/unauthorized', 'rejected documents write nothing',
                  conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == before)

            def run(value):
                result_file.write_text(json.dumps(value))
                record = cycles.start('proj-a', cycles.inputs('proj-a'))
                if record.get('dispatch') in runner.launches:
                    runner.wait(runner.launches[record['dispatch']], timeout=15)
                    record = cycles.finish(record)
                return record

            question = dict(ids, operation='open', alias='question-88', assignment=dict(kind='decision', owner='olga',
                scope=['proj-a'], deadline='2026-10-30T17:00:00Z', budget={'owner_minutes': 1},
                brief='Choose a scope.', choices=['yes', 'no'], subject={'kind': 'pm', 'ref': 'proj-a',
                    'digest': PM.SN.digest(b'question')}))
            refused = dict(question, operation='open', assignment={})
            failed = run(dict(empty, proposals=[dict(name='first', type='question', command=refused),
                                                dict(name='second', type='question', command=question)]))
            print('  VELDO-0088 detail: refused proposals:', failed.get('refusal'), failed['proposals'])
            check('proposal/stop-on-refusal', 'first owning command refuses and later request is absent',
                  failed.get('refusal') == 'proposal_refused:first' and len(failed['proposals']) == 1
                  and f['inbox'].read(f['I'].assignment_id(repository, 'question-88')) is None)
            check('cycle/failure', 'failed cycle retains source and named refusal',
                  failed['state'] == 'refused' and failed['snapshot'] and failed['watermark'] > 0)
            result_file.write_text(json.dumps(empty))
            request_id, receipt = f['present']('pending-88', {'kind': 'pm', 'ref': 'proj-a',
                'digest': PM.SN.digest(b'pending')}, 'Answer this coordination question.')
            (base / 'hold').write_text('hold')
            held = cycles.start('proj-a', cycles.inputs('proj-a'))
            try:
                cycles.start('proj-a', cycles.inputs('proj-a'))
                serial = False
            except Exception as error:
                serial = getattr(error, 'code', '') == 'active_cycle:project'
            check('cycle/serialized', 'store refuses a second active project cycle', serial)
            answered = f['answer'](receipt, 'accept')
            pending_pass = cycles.pass_once()
            check('cycle/pending-follow-up', 'owner answer retained while one cycle holds the project',
                  answered.get('outcome') == 'settled' and 'proj-a' in cycles.pending
                  and len([r for r in cycles.records('proj-a') if r['state'] not in PM.FINAL]) == 1)
            if held.get('dispatch') in runner.launches:
                runner.wait(runner.launches[held['dispatch']], timeout=15)
            (base / 'hold').unlink()
            follow = cycles.pass_once()
            active = [r for r in cycles.records('proj-a') if r['state'] not in PM.FINAL]
            check('cycle/pending-follow-up', 'one follow-up binds a newer accepted snapshot',
                  len(active) == 1 and active[0]['snapshot'] != held['snapshot']
                  and active[0]['watermark'] > held['watermark'])
            for one in active:
                if one.get('dispatch') in runner.launches:
                    runner.wait(runner.launches[one['dispatch']], timeout=15)
            cycles.pass_once()
            count = len(cycles.records('proj-a'))
            check('cycle/pending-follow-up', 'consumed inputs do not self-trigger',
                  not cycles.pass_once() and len(cycles.records('proj-a')) == count and not cycles.pending)
            IN = load('v88_intake', mods / 'control_intake.py')
            OB = load('v88_objective', mods / 'control_objective.py')
            CB = load('v88_backlog', mods / 'control_backlog.py')
            EV = load('v88_attribution', mods / 'control_channel_attribution.py')
            acquirer = EV.Acquirer(S, f['CM'], f['P'], f['V'], f['presenter'],
                EV.TelegramAcquisitionEdge(f['P'], f['url'], 'bot89'), conn, 'authority', sign,
                'api-edge', lambda b: f['sign_as']('api-edge', b))
            intake = IN.Intake(S, f['CM'], f['AC'], acquirer, conn, domain=domain, projects=['proj-a'],
                api_edge='api-edge', journal_signer='authority', sign=sign)
            message = dict(schema=IN.API_SCHEMA, domain=domain, request_id=f['next_id']('intake'),
                edge='api-edge', principal='olga', text='please do BCG-123', project='proj-a', clarifies=None)
            received = intake.receive('api_request', dict(request=message,
                signature=f['sign_as']('api-edge', S.canonical_bytes(message))))
            objectives = OB.Objectives(S, f['CM'], conn, ids, 'authority', sign)

            def command(who, operation, **fields):
                return f['signed'](who, dict(ids, operation=operation, principal=who,
                    command_id=f['next_id']('work'), nonce=f['next_id']('work-nonce'), **fields))

            proposed = objectives.apply(command('olga', 'propose', proposal=received.get('proposal_id'),
                outcome='Do the requested ticket.', scope=['design'], authority={'acceptor': 'olga', 'assessor': 'zed'},
                evidence_requirements=[{'id': 'outcome', 'kind': 'gate_observation'}]))
            oid = proposed.get('objective_id')
            objective = OB.read(conn, oid) or {}
            source_key = IN.source_key('api_request', message['request_id'])
            intake_command = next((c for c, transition in conn.execute('SELECT command_id, transition FROM journal')
                                   if source_key in json.loads(transition)), None)
            objectives.apply(command('olga', 'accept_message', objective=oid,
                objective_version=objective.get('version'), revision=objective.get('revision'),
                bound_digest=objective.get('bound_digest'), intake_command=intake_command))
            feature = objectives.apply(command('pm', 'propose_feature', objective=oid,
                objective_version=(OB.read(conn, oid) or {}).get('version'), feature='ticket',
                title='Implement BCG-123', scope=['design']))
            backlog = CB.Backlog(S, f['CM'], conn, ids, 'authority', sign, workspace=source)
            taken = backlog.apply(command('pm', 'take', feature=feature.get('feature_id'), work_class='PRODUCT_CHANGE'))
            iid = taken.get('item_id')
            AL = load('v88_alias', mods / 'control_alias.py')
            DOC = load('v88_document', mods / 'control_document.py')
            EN = load('v88_enrollment', mods / 'control_enrollment.py')
            DP = load('v88_decomposition', mods / 'control_decomposition.py')
            GR = load('v88_grooming', mods / 'control_grooming.py')
            allocations = AL.attach(S, conn, domain, {repository: str(source)})
            EN.enroll(source, domain, ids['store_uuid'], str(f['db']), 'fixture-host', 1,
                      sign, 'olga', '2026-10-02T00:00:00Z', repository_uuid=repository)
            allowed = base / 'enrollment-signers'
            allowed.write_text('authority ' + f['public']['authority'] + '\n')

            def verify(body, signature):
                path = base / 'enrollment.sig'
                path.write_text(signature)
                return subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'authority',
                    '-n', 'veldo-journal', '-s', str(path)], input=body, capture_output=True).returncode == 0

            publisher = DOC.Publisher(allocations, source, verify, 'fixture-host')
            allocations.enable_kind(dict(request_id='kind-88', principal='olga', repository_uuid=repository,
                kind='specification', prefix='VELDO', width=4, path_template='specs/{alias}-{slug}.md',
                revision_id='revision-88'), signer='authority', sign=sign, authority_generation=1)
            decomposition = DP.Decomposition(backlog, allocations, publisher)
            grooming = GR.Grooming(S, f['CM'], conn, ids, 'authority', sign, backlog=CB, service=backlog,
                assignment=f['I'], inbox=f['inbox'], presenter=f['presenter'], settlement=f['settlement'],
                requester=('pm', lambda b: f['sign_as']('pm', b)), workspace=source)
            cycles.services.update(backlog=backlog, decomposition=decomposition, grooming=grooming)
            policy = f['DSP'].review_policy_record(ROOT / '.veldo/policy.yaml')
            f['fixture'](f['DSP'].review_policy_id(repository), f['DSP'].REVIEW_POLICY_KIND, policy)
            uid = 'VELDO-8801'
            requirements = 'Implement the requested ticket. Owner: please do BCG-123'
            raw = dict(unit=uid, scope=['design'], requirements=[requirements], eligible_holders=['w-build'],
                source={'system': 'pm', 'id': oid, 'revision': '1'}, role='specification/main',
                front=dict(title='Implement BCG-123', status='ready', risk='standard', owner='olga',
                    human_approval='not_required', lane='standalone', protected_paths=[]),
                body='## Intent\n\n' + requirements + '\n', dependencies=[])
            doc = dict(empty, decomposition=[dict(unit=uid, requirements=requirements, owner_message=message['text'],
                references=['BCG-123'], staffing={name: name for name in PM.CT.REQUIRED_ROLES})], proposals=[
                dict(name='publish', type='decomposition', command=dict(ids, operation='publish_decomposition',
                    item=iid, item_version=1, unit=raw)),
                dict(name='prepare', type='backlog', command=dict(ids, operation='prepare', item=iid, item_version=1,
                    units=[{'result': 'publish', 'path': ['unit']}])),
                dict(name='request', type='backlog', command=dict(ids, operation='request_grooming', item=iid, item_version=2)),
                dict(name='groom', type='grooming', command=dict(ids, operation='propose', item=iid, item_version=3,
                    proposal={'ceiling': {'invocations': 1}, 'expiry': '2026-10-30T17:00:00Z'})),
                dict(name='assign', type='assignment', command=dict(ids, operation='assign', project='proj-a',
                    team_version=f['version'](), team_revision=f['team_record']()['revision'], unit=uid,
                    role='implementation', builder='w-build', reviewers=['w-rev1']))])
            reservations.configure('engineering-ceiling', 'unit', uid, dict(capacity=2, invocations=4, wall_seconds=500), now=time.time())
            (base / 'engineering-hold').write_text('hold')
            before_dispatches = conn.execute("SELECT COUNT(*) FROM entities WHERE kind='dispatch'").fetchone()[0]
            from types import SimpleNamespace
            SV = load('v88_factory', mods / 'control_service.py')
            service = SimpleNamespace(conn=conn, domain=domain, store=ids['store_uuid'], principal='pm',
                generation=1, config={}, _log=lambda report: None)
            factory = SV.FactoryLoop(service, {'repositories': {}})
            line = SV.Line.__new__(SV.Line)
            line.loop, line.service, line.repository = factory, service, repository
            line.workspace, line.records = str(source), base / 'records'
            line.runner, line.gate, line.dispatches, line.reservations = runner, gate, dispatches, reservations
            line.registration = SV.S.COMMAND_REGISTRY.get('subscription_reservation',
                                                        S.COMMAND_REGISTRY['subscription_reservation'])
            line.engines, line.hosts = {'protocol': 'claude_code'}, {'protocol': 'fixture-host'}
            line.roles = {'builder': {'identity': 'unassigned'}, 'reviewers': []}
            line.pm_cycles = cycles
            factory.lines[repository] = line
            result_file.write_text(json.dumps(doc))
            factory.wake('accepted_objective')
            started = factory.run()
            active = [r for r in cycles.records('proj-a') if r['state'] not in PM.FINAL]
            check('unit/factory-builder-ticket', 'factory starts one PM dispatch',
                  len(active) == 1 and not started['faults'])
            if active:
                runner.wait(runner.launches[active[0]['dispatch']], timeout=15)
            factory.wake('run_end')
            staged_pass = factory.run()
            staged = next(r for r in cycles.records('proj-a') if r['cycle'] == active[0]['cycle'])
            print('  VELDO-0088 detail: factory staging:', staged_pass['refused'], staged_pass['faults'])
            print('  VELDO-0088 detail: staging:', staged['state'], staged.get('refusal'),
                  [(r['name'], r['result'].get('reason')) for r in staged['proposals']])
            check('unit/one-run-staging', 'one coordination run publishes requirements and stages all four roles',
                staged['state'] == 'proposed' and set(staged.get('unit_roles', {})) == set(PM.CT.REQUIRED_ROLES)
                and staged.get('elaboration') == {'state': 'done', 'dispatch': staged['dispatch']}
                and len([r for r in line.latest().values() if r['contract']['station'] == 'coordination']) == before_dispatches + 1
                and f['entity'](uid)['data']['state'] == 'READY')
            extra = load('v88_observations', Path(__suite_file__).resolve().parents[2] / 'proof/VELDO-0088/observations.py')
            extra.observe(locals())
            budget = f['entity']('project:proj-a')['data']['coordination_budget']['invocations']
            for unused in range(budget - len(cycles.records('proj-a'))):
                run(empty)
            try:
                cycles.start('proj-a', cycles.inputs('proj-a'))
                bounded = False
            except PM.Refused as error:
                bounded = error.code == 'budget_exceeded:coordination'
            check('cycle/budget', 'the project cycle budget stops further dispatch',
                  bounded and len(cycles.records('proj-a')) == budget)
    except Exception as error:
        print('  VELDO-0088 detail: fixture did not run to its end: ' + repr(error))
        for name in names:
            rows[name].append(('fixture raised', False))
    for name in names:
        bad = [label for label, ok in rows[name] if not ok]
        if bad:
            print('  VELDO-0088 detail: ' + name + ': ' + '; '.join(bad))
        expect('VELDO-0088 ' + name, bool(rows[name]) and not bad)


_v88_suite()
