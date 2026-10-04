"""VELDO-0152: actual intake, signed activation, factory pass, Runner and CLI-shaped PM output."""

def _v152_suite():
    import copy
    import importlib.util
    import json
    from pathlib import Path
    import sys
    import time
    from types import SimpleNamespace
    PRODUCTION = {
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
        'control_intake_routes.py': ROOT / ".veldo" / "control_intake_routes.py",
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_project.py': ROOT / ".veldo" / "control_project.py",
        'control_workflow_cycle_pm.py': ROOT / ".veldo" / "control_workflow_cycle_pm.py",
        'control_telegram_report.py': ROOT / ".veldo" / "control_telegram_report.py",
    }
    MUTATIONS = ROOT / "scripts" / "check_teeth_mutations.py"
    names = ('route/codex-result', 'intake/scoped-context', 'proof/intake-companions',
             'intake/ticket-key', 'intake/name-is-a-hint', 'intake/request-field',
             'intake/factory-inbox', 'intake/factory-refusals', 'project/prefixes',
             'route/new-project', 'route/existing-project', 'route/asked-only-when-unclear',
             'route/answers', 'route/read-and-report', 'route/runner-input',
             'route/scope-refusal', 'route/malformed', 'route/stale', 'route/factory-refusal',
             'format/fake-lines')
    rows = {n: [] for n in names}
    def check(name, label, condition):
        rows[name].append((label, bool(condition)))
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    fake_formats = load('v172_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    conform_formats = load('v172_compare_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    formats = json.loads((ROOT / 'proof/VELDO-0062/cli-formats.json').read_text())
    # Exercise the runner's isolated copies without executing any mutation suite.
    import tempfile
    driver = load('v152_mutation_catalog', MUTATIONS)
    # A mutated catalog lives in a temporary directory; its fixtures still belong to this repo.
    driver.ROOT = ROOT
    intake_cases = [case for case in driver.cases() if case['module'] == 'control_intake.py']
    check('proof/intake-companions', 'registered intake cases exist', bool(intake_cases))
    with tempfile.TemporaryDirectory(prefix='v152-companions-') as directory:
        layouts = set()
        for case in intake_cases:
            layout = (case.get('siblings', False), tuple(case.get('companions', ())))
            if layout in layouts:
                continue
            layouts.add(layout)
            try:
                made = driver.materialize(case, 'noop', Path(directory) / case['name'], root=ROOT)
                module = load('v152_isolated_' + case['name'], made['mutant'])
                check('proof/intake-companions', case['name'],
                      module.PJ.FACTORY_PROJECT == 'factory' and bool(module.RT.SCHEMA))
            except (ImportError, OSError) as error:
                check('proof/intake-companions', case['name'] + ': ' + str(error), False)
    if not PRODUCTION['control_intake_routes.py'].is_file():
        for name in names:
            expect('VELDO-0152 ' + name, False)
        return
    helper = load('v152_fixture', Path(__suite_file__).resolve().parents[2] / 'proof/VELDO-0152/fixture.py')
    # Keep the generated executables until their teardown read-back, after both stores close.
    fake_directory = tempfile.TemporaryDirectory(prefix='v152-formats-')
    fake_base = Path(fake_directory.name)
    printed = fake_base / 'printed.jsonl'
    def fake_engine(name):
        return (fake_base / name).read_text()
    try:
        with helper.fixture(ROOT, PRODUCTION, cycle_budget=100) as f:
            S, conn, base, mods = (f[k] for k in ('S', 'conn', 'base', 'mods'))
            domain, repository, ids = (f[k] for k in ('DOMAIN', 'REPO', 'ids'))
            IN = load('v152_intake', mods / 'control_intake.py')
            PM = load('v152_pm', mods / 'control_workflow_cycle_pm.py')
            EV = load('v152_attribution', mods / 'control_channel_attribution.py')
            acquirer = EV.Acquirer(S, f['CM'], f['P'], f['V'], f['presenter'],
                EV.TelegramAcquisitionEdge(f['P'], f['url'], 'bot89'), conn, 'authority', f['journal_sign'],
                'api-edge', lambda b: f['sign_as']('api-edge', b))
            intake = IN.Intake(S, f['CM'], f['AC'], acquirer, conn, domain=domain, projects=['factory'],
                api_edge='api-edge', journal_signer='authority', sign=f['journal_sign'], asker=f['presenter'].edge)
            def activate(name, prefixes):
                return f['projects'].apply(f['signed']('olga', dict(ids, operation='activate', project=name,
                    principal='olga', command_id=f['next_id']('project'), nonce=f['next_id']('nonce'), owner='olga',
                    charter={'purpose': 'Fixture work'}, execution_repository=repository,
                    authority_policy={'admission': ['admission_authority']},
                    coordination_budget={'capacity': 5, 'invocations': 100, 'wall_seconds': 500},
                    ticket_key_prefixes=prefixes)))
            def send(channel, text, who='olga', project=None, clarifies=None, reply=None):
                if channel == 'api_request':
                    body = dict(schema=IN.API_SCHEMA, domain=domain, request_id=f['next_id']('message'),
                        edge='api-edge', principal=who, text=text, project=project, clarifies=clarifies)
                    return intake.receive(channel, dict(request=body, signature=f['sign_as']('api-edge', S.canonical_bytes(body))))
                chat = 5890001 if who == 'olga' else 5890002
                msg = f['message'](f['api'], {'id': chat, 'is_bot': False, 'first_name': who},
                    {'id': chat, 'type': 'private'}, text, reply)
                f['api'].setdefault('updates', []).append(dict(update_id=msg['message_id'], message=msg))
                acquirer.acquire()
                return intake.receive(channel, EV.evidence_id(f['api']['user']['id'], msg['message_id']))
            def proposal(result):
                return intake.proposal(result.get('proposal_id')) or {}
            channels = IN.SOURCE_KINDS
            texts = ('start a new personal project called tidepool', 'make a new repo for the site',
                     "renew the project's certificate", 'fix the login bug')
            # Every owner project count and the scoped member, on both real source adapters.
            for count in range(3):
                if count:
                    name = 'bcengi' if count == 1 else 'other'
                    accepted = activate(name, ['BCG'] if count == 1 else ['OTH'])
                    check('project/prefixes', 'signed activation ' + name, accepted.get('ok'))
                    intake.projects += (name,)
                for channel in channels:
                    for text in texts:
                        result = send(channel, text)
                        p = proposal(result)
                        check('intake/factory-inbox', str((count, channel, text)), result.get('outcome') == 'inbox'
                              and p.get('project') == 'factory' and p.get('state') == 'AWAITING_ROUTE'
                              and p.get('text') == text and not p.get('question_id')
                              and (p.get('decision') or {}).get('decided_by') is None
                              and p.get('context', {}).get('candidates') == list(intake.projects[1:]))
            for channel in channels:
                for text in texts:
                    p = proposal(send(channel, text, who='zed'))
                    check('intake/factory-inbox', 'scoped member', p.get('state') == 'AWAITING_ROUTE'
                          and p.get('context', {}).get('candidates') == ['bcengi'])
                for text in ('please do BCG-123', 'BCG-123: add the new project settings page'):
                    p = proposal(send(channel, text))
                    check('intake/ticket-key', text, p.get('project') == 'bcengi' and p.get('state') == 'PROPOSED'
                          and p.get('decision', {}).get('decided_by') == 'ticket_key' and not p.get('question_id'))
                for text in ('in bcengi please add a new page to the project site', 'start a new project like bcengi'):
                    p = proposal(send(channel, text))
                    check('intake/name-is-a-hint', text, p.get('project') == 'factory' and p.get('hints') == ['bcengi'])
                for text in ('please do ZZZ-123', 'please do FAC-123'):
                    p = proposal(send(channel, text))
                    check('intake/ticket-key', text, p.get('state') == 'AWAITING_ROUTE')
            for channel in channels:
                for text in ('unresolved member work', 'please do BCG-123'):
                    p = proposal(send(channel, text, who='zed'))
                    expected = {name: f['entity'](name)['version']
                                for name in ('project:bcengi', 'project:factory')}
                    check('intake/scoped-context', channel + ': ' + text,
                          p.get('context', {}).get('project_versions') == expected
                          and p.get('decision', {}).get('project_versions') == expected
                          and p.get('decision', {}).get('candidates') == ['bcengi'])
            check('project/prefixes', 'record retains prefixes', f['entity']('project:bcengi')['data'].get('ticket_key_prefixes') == ['BCG'])
            for bad in ('BCG', ['lower'], ['BCG', 'BCG'], [3]):
                check('project/prefixes', repr(bad), activate(f['next_id']('bad'), bad).get('reason') == 'invalid_input:ticket_key_prefixes')
            activate('shared', ['BCG'])
            intake.projects += ('shared',)
            for channel in channels:
                p = proposal(send(channel, 'please do BCG-123'))
                check('intake/ticket-key', 'shared prefix', p.get('state') == 'AWAITING_ROUTE')
            p = proposal(send('api_request', 'start a new project like other', project='bcengi'))
            check('intake/request-field', 'field beats wording', p.get('project') == 'bcengi'
                  and p.get('decision', {}).get('decided_by') == 'request')
            check('intake/factory-refusals', 'explicit factory', send('api_request', 'work', project='factory').get('reason') == 'invalid_input:factory_project')
            saved = intake.projects
            intake.projects = ('bcengi',)
            for channel in channels:
                check('intake/factory-refusals', 'missing factory ' + channel, send(channel, 'work').get('reason') == 'unsupported_configuration:factory_project')
            intake.projects = ('factory',)
            for channel in channels:
                check('intake/factory-refusals', 'member has no project ' + channel, send(channel, 'work', who='zed').get('reason') == 'unauthorized:no_project')
            intake.projects = saved
            # Close the matrix inboxes with production commands before the cycle journeys.
            def doc(pid, route='new_project', **extra):
                return dict(schema=IN.RT.SCHEMA, proposal_id=pid, route=route, reason='Fixture PM reason.', **extra)
            for p in intake._all(IN.PROPOSAL_KIND):
                if p['state'] == 'AWAITING_ROUTE':
                    cleaned = intake.route(doc(p['proposal_id']), dispatch='fixture-prior-pm', proposal_id=p['proposal_id'])
                    if not cleaned.get('ok'): print('  VELDO-0152 detail: cleanup', cleaned)
            # The production factory pass starts coordination, on its ordinary Runner.
            GP = load('v152_git', mods / 'git_process.py')
            source = base / 'source'; source.mkdir(); (source / 'README').write_text('Fixture accepted source.\n')
            for args in (('init', '-q'), ('add', 'README'), ('commit', '-qm', 'Fixture source')):
                GP.run(['git', '-C', str(source), *args], check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
            commit = GP.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
            RS = load('v152_snapshots', mods / 'control_readset.py')
            RS.attach_revisions(S, conn, domain, {repository: str(source)}).accept('revision-152', repository, commit, 'pm',
                documents={'README': PM.SN.digest((source / 'README').read_bytes())}, signer='authority', sign=f['journal_sign'], authority_generation=1)
            SV = load('v152_service', mods / 'control_service.py')
            EN = load('v152_enrollment', mods / 'control_enrollment.py')
            signers = base / 'enrollment-signers'; signers.write_text('olga ' + f['public']['olga'] + '\n')
            EN.enroll(source, domain, ids['store_uuid'], str(f['db']), 'fixture-host', 1,
                lambda b: f['sign_as']('olga', b, SV.EL.ENROLLMENT_NAMESPACE), 'olga', '2026-10-03T00:00:00Z', repository_uuid=repository)
            service = SV.Service(dict(domain_uuid=domain, store_uuid=ids['store_uuid'], principal='team-service',
                authority_generation=1, repositories={repository: [str(source)]}, journal_key=str(f['keyfile']['authority']),
                host_identity='fixture-host', enrollment_signers=str(signers), observations=str(base / 'events.jsonl')), conn)
            service.channel = SimpleNamespace(ingress=SimpleNamespace(inbox=f['inbox'], presenter=f['presenter'],
                settlement=f['settlement'], acquirer=acquirer))
            result_file, packet_file = base / 'result.json', base / 'packet.json'
            # Both launches and the teardown observer drive these same generated executables.
            # complete_event supplies the live fields; the reasoning and shell-command items remain
            # alongside the final route document, with their text and command as the CLI emits them.
            fake_source = fake_formats.embed('''import json,sys
from pathlib import Path
engine = Path(sys.argv[0]).name
def emit(event):
    line = complete_event(event)
    with Path(PRINTED).open('a') as stream:
        stream.write(json.dumps({'engine': engine, 'line': line}) + chr(10))
    print(json.dumps(line), flush=True)
if sys.argv[1:3] == ['login', 'status']:
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
if engine == 'claude' and '--input-format' in sys.argv:
    opening = json.loads(sys.stdin.readline())
    if opening['type'] != 'control_request':
        raise ValueError('expected initialize')
    emit({'type': 'control_response', 'response': {'subtype': 'success',
          'request_id': opening['request_id'], 'response': {'account': {
          'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    packet = json.loads(json.loads(sys.stdin.readline())['message']['content'])
    result = 'Fixture PM read-back.'
elif sys.argv[1:2] == ['exec']:
    packet = json.load(sys.stdin)
    result = 'Fixture PM read-back.'
else:
    packet = json.load(sys.stdin)
    Path(sys.argv[2]).write_text(json.dumps(packet))
    result = Path(sys.argv[1]).read_text()
if engine == 'claude':
    emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': result}],
          'usage': {'input_tokens': 2, 'output_tokens': 3}}})
    emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': result,
          'usage': {'input_tokens': 2, 'output_tokens': 4}})
else:
    events = [{'type': 'thread.started', 'thread_id': 'route-thread'}, {'type': 'turn.started'},
              {'type': 'item.completed', 'item': {'id': 'item_0', 'type': 'reasoning',
               'text': 'Read the repository before routing.'}},
              {'type': 'item.completed', 'item': {'id': 'item_1', 'type': 'command_execution',
               'command': 'ls', 'aggregated_output': 'README' + chr(10), 'exit_code': 0, 'status': 'completed'}},
              {'type': 'item.completed', 'item': {'id': 'item_2', 'type': 'agent_message', 'text': result}},
              {'type': 'turn.completed', 'usage': {'input_tokens': 1200, 'output_tokens': 300}}]
    for event in events:
        emit(event)
''').replace('Path(PRINTED)', 'Path(%r)' % str(printed))
            fake, codex_fake = fake_base / 'claude', fake_base / 'codex'
            fake.write_text(fake_source)
            codex_fake.write_text(fake_source)
            config = base / 'receiver.json'
            config.write_text(json.dumps(dict(store=str(f['db']), journal_key=str(f['keyfile']['authority']), principal='pm',
                workspace=str(source), domain=domain, repository=repository, records=str(base / 'records'),
                adapters={'claude': {'identity': 'reported', 'argv': [sys.executable, '-B', str(mods / 'control_launch.py'),
                    'exec', sys.executable, '-B', str(fake), str(result_file), str(packet_file)]}})))
            receiver = json.loads(config.read_text())
            receiver['adapters']['codex'] = {'identity': 'reported', 'argv': [sys.executable, '-B',
                str(mods / 'control_launch.py'), 'exec', sys.executable, '-B', str(codex_fake),
                str(result_file), str(packet_file)]}
            config.write_text(json.dumps(receiver))
            factory = SV.FactoryLoop(service, {'repositories': {}})
            line = SV.Line(factory, repository, {'builder': {'identity': 'unassigned'}, 'reviewers': []}, config)
            line.runner.account = 'fixture-account'
            line.engines, line.hosts = {'claude': 'claude_code', 'codex': 'codex'}, {'claude': 'fixture-host', 'codex': 'fixture-host'}
            factory.lines[repository] = line
            for scope, subject in (('account', 'fixture-account'), ('project', 'factory')):
                line.reservations.configure('policy/' + subject, scope, subject, dict(capacity=5, invocations=100, wall_seconds=5000), now=time.time())
            def run(pid, value, before_finish=None):
                result_file.write_text(json.dumps(value))
                factory.wake('accepted_message'); factory.run()
                cycles = line.pm_cycles
                record = max(cycles.records('factory'), key=lambda r: r['watermark'])
                if record.get('dispatch') in line.runner.launches:
                    line.runner.wait(line.runner.launches[record['dispatch']], timeout=15)
                    if before_finish is not None:
                        before_finish()
                    factory.wake('run_end'); factory.run()
                latest = next(r for r in cycles.records('factory') if r['cycle'] == record['cycle'])
                if latest['state'] != 'proposed': print('  VELDO-0152 detail: cycle', latest.get('refusal'), latest.get('route_subject'), latest.get('proposals'))
                return latest
            report = load('v152_report', mods / 'control_telegram_report.py')
            report_gate = SimpleNamespace(conn=conn, channel='telegram_chat')
            # Loopback channel edge: sends are real HTTP, with the activation boundary trusted here.
            report_edge = SimpleNamespace(activation=report_gate, send=f['presenter'].edge.send)
            report_presenter = SimpleNamespace(conn=conn, P=f['P'], edge=report_edge, current=f['presenter'].current)
            reporter = report.Reporter(SimpleNamespace(conn=conn, inbox=f['inbox'], presenter=report_presenter,
                                                       gate=report_gate), owner='olga')
            for channel in channels:
                for route in IN.RT.ROUTES:
                    result = send(channel, 'start a new project like bcengi')
                    pid = result['proposal_id']
                    value = doc(pid, route, **({'project': 'bcengi'} if route == 'existing_project' else {}))
                    record = run(pid, value)
                    p = intake.proposal(pid)
                    check('route/' + ('asked-only-when-unclear' if route == 'unclear' else route.replace('_', '-')),
                          channel, p.get('state') == {'new_project': 'NEW_PROJECT', 'existing_project': 'ROUTED', 'unclear': 'AWAITING_PROJECT'}[route]
                          and record.get('state') == 'proposed')
                    check('route/asked-only-when-unclear', route, bool(p.get('question_id')) == (route == 'unclear'))
                    packet = json.loads(packet_file.read_text()) if packet_file.exists() else {}
                    route_events = [e for e in line.pm_cycles.services['intake'].observations if e['operation'] == 'route' and e.get('proposal_id') == pid]
                    check('route/read-and-report', 'route observation and count', route_events
                          and route_events[-1].get('route', {}).get('reason') == value['reason']
                          and line.pm_cycles.services['intake'].metrics()['routes'][route] >= 1)
                    check('route/runner-input', channel + route, packet.get('station') == 'coordination'
                          and packet.get('payload', {}).get('hints') == ['bcengi']
                          and packet.get('payload', {}).get('proposal_id') == pid
                          and (p.get('route') or {}).get('dispatch') == record.get('dispatch'))
                    if route == 'existing_project':
                        target = intake.proposal(p.get('resolved_to')) or {}
                        check('route/existing-project', 'objective target', target.get('project') == 'bcengi' and target.get('state') == 'PROPOSED')
                    if route == 'unclear':
                        q = intake.question(p.get('question_id')) or {}
                        check('route/asked-only-when-unclear', 'offered projects', q.get('candidates') == ['bcengi', 'other', 'shared', 'a new project']
                              and (q.get('delivery') or {}).get('channel') == ('api' if channel == 'api_request' else 'telegram_chat'))
                        answer = send(channel, 'other' if channel == 'api_request' else 'OTH-12', clarifies=pid,
                                      reply=(q.get('delivery') or {}).get('message_id'))
                        check('route/answers', 'offered name or ticket key', proposal(answer).get('project') == 'other'
                              and intake.proposal(pid).get('state') == 'ROUTED')
                    api_authority = load('v152_api_authority', mods / 'control_api_authority.py')
                    with (Path(f['db']).parent / api_authority.LOCK_NAME).open('a+') as authority_lock:
                        api = api_authority.ApiAuthority(S, f['CM'], conn, ids=ids, domain=domain, edge='api-edge',
                            intake=intake, settlement=f['settlement'], credentials=None, authority_lock=authority_lock.fileno())
                        answer = api.read('objectives', 'olga')
                        check('route/read-and-report', 'authorized API authority read', answer.get('ok'))
                        read = answer
                    served = next((x for x in read['items']['intake_proposal'] if x['id'] == pid), {})
                    facts = [fact for fact in reporter.sources(since=0) if fact['event'] == 'intake_routed'
                             and fact['source']['entity_id'] == pid and 'Fixture PM reason.' in fact['fact']]
                    delivered = reporter.report(facts[0]) if facts else {}
                    check('route/read-and-report', route,
                          served.get('data', {}).get('route') == intake.proposal(pid).get('route')
                          and facts and facts[0]['run'] == record.get('dispatch') and delivered.get('outcome') == 'sent')
            # Each refusal comes back from the dispatched fake and leaves the proposal unchanged.
            bads = [('scope-refusal', 'unauthorized:project', 'zed', {'route': 'existing_project', 'project': 'other'}),
                    ('factory-refusal', 'invalid_input:factory_project', 'olga', {'route': 'existing_project', 'project': 'factory'})]
            malformed = ({'_omit': 'route'}, {'_omit': 'reason'}, {'_two': True}, {'route': None}, {'routes': ['new_project', 'unclear']}, {'route': 'unknown'}, {'reason': ''}, {'reason': None}, {'project': 'bcengi'},
                         {'unexpected': True}, {'proposal_id': 'another'}, {'route': 'existing_project', 'project': 'absent'},
                         {'route': ['new_project', 'unclear']})
            bads += [('malformed', 'invalid_input:route', who, bad) for who in ('olga', 'zed') for bad in malformed]
            for name, reason, who, bad in bads:
                pid = send('api_request', 'unresolved work', who=who)['proposal_id']
                before = copy.deepcopy(intake.proposal(pid))
                value = dict(doc(pid), **bad)
                if '_omit' in value:
                    value.pop(value.pop('_omit'), None)
                if '_two' in value:
                    value = [doc(pid), doc(pid)]
                record = run(pid, value)
                results = record.get('proposals') or []
                check('route/' + name, repr(bad), intake.proposal(pid) == before and record.get('state') == 'refused'
                      and results and results[0]['result'].get('reason') == reason and len(results) == 1)
                intake.route(doc(pid), dispatch='fixture-cleanup', proposal_id=pid)
            pid = send('api_request', 'first unresolved work')['proposal_id']
            unchanged = []
            def intervene():
                intake.route(doc(pid), dispatch='intervening-pm', proposal_id=pid)
                unchanged.append(copy.deepcopy(intake.proposal(pid)))
            record = run(pid, doc(pid), before_finish=intervene)
            check('route/stale', 'route changed while the dispatched PM ran', unchanged
                  and intake.proposal(pid) == unchanged[0] and record.get('state') == 'refused'
                  and record.get('proposals', [{}])[0].get('result', {}).get('reason') == 'stale_version')
            pid = send('api_request', 'undecided follow-up')['proposal_id']
            run(pid, doc(pid, 'unclear'))
            answer = send('api_request', 'a new project called tidepool', clarifies=pid)
            held = intake.proposal(pid)
            check('route/answers', 'other answer saved for next PM run', answer.get('outcome') == 'clarification'
                  and held['state'] == 'AWAITING_ROUTE' and held['clarifications'][-1]['text'] == 'a new project called tidepool')
            run(pid, doc(pid))
            # Accept a Codex PM configuration through the ordinary configuration/team writers.
            configured = f['configurations'].save(dict(role='codex-pm', engine='codex', native_tools=[],
                mcp=[], skills=[], instructions=[], settings={}), principal='steward', base=0,
                command_id=f['next_id']('capability'))
            pm_role = f['role'](['pm'], 'coordinate', ('objective', 'feature', 'team_amendment'), engines=('codex',))
            pm_role['capability_configuration'] = {'role': 'codex-pm', 'revision': 1}
            accepted = f['accept'](f['team'](project_manager=pm_role))
            check('route/codex-result', 'Codex PM configuration and team accepted', configured.get('engine') == 'codex' and accepted.get('ok'))
            pid = send('api_request', 'start another project')['proposal_id']
            record = run(pid, doc(pid))
            routed = intake.proposal(pid)
            dispatched = line.runner.dispatches.record(record['dispatch'])
            check('route/codex-result', 'one route document survives reasoning and command events',
                  record.get('state') == 'proposed' and routed.get('state') == 'NEW_PROJECT'
                  and (routed.get('route') or {}).get('reason') == 'Fixture PM reason.'
                  and (routed.get('route') or {}).get('dispatch') == record['dispatch']
                  and dispatched['contract']['capability']['adapter'] == 'codex')
        # This store truly has no factory project record, rather than merely excluding it from configuration.
        with helper.fixture(ROOT, PRODUCTION, factory_project=False) as f:
            S, conn, mods = f['S'], f['conn'], f['mods']
            IN = load('v152_missing_intake', mods / 'control_intake.py')
            EV = load('v152_missing_attribution', mods / 'control_channel_attribution.py')
            acquirer = EV.Acquirer(S, f['CM'], f['P'], f['V'], f['presenter'],
                EV.TelegramAcquisitionEdge(f['P'], f['url'], 'bot89'), conn, 'authority', f['journal_sign'],
                'api-edge', lambda b: f['sign_as']('api-edge', b))
            intake = IN.Intake(S, f['CM'], f['AC'], acquirer, conn, domain=domain, projects=['factory', 'bcengi'],
                api_edge='api-edge', journal_signer='authority', sign=f['journal_sign'], asker=f['presenter'].edge)
            for channel in channels:
                result = send(channel, 'fix the login bug')
                check('intake/factory-refusals', 'no factory record ' + channel,
                      intake._entity('project:factory') is None
                      and result.get('reason') == 'unsupported_configuration:factory_project'
                      and not intake._all(IN.PROPOSAL_KIND))
    except Exception as error:
        print('  VELDO-0152 detail: suite did not run to its end:', repr(error))
        import traceback
        traceback.print_exc()
        for name in names:
            rows[name].append(('journey completed', False))
    finally:
        base = fake_base
        L = load('v152_format_launch', ROOT / '.veldo/control_launch.py')
        fake_capture = conform_formats.conform_fake(locals(), '0152_intake_routes')
        problems, observed = [], set()
        if printed.is_file():
            for raw in printed.read_text().splitlines():
                record = json.loads(raw)
                engine, event = record['engine'], record['line']
                name = conform_formats.event_name(event)
                table = formats['claude_code' if engine == 'claude' else 'codex']
                schema = table['events'].get(name)
                problems += conform_formats.conform(event, schema, name) if schema else [name + ':table:no-event']
                observed.add((engine, name))
        check('format/fake-lines', 'every emitted line conforms to the binary table: ' + repr(problems[:4]),
              not problems and {('claude', 'assistant'), ('claude', 'result/success'),
              ('codex', 'thread.started'), ('codex', 'turn.started'), ('codex', 'item.completed'),
              ('codex', 'turn.completed')} <= observed)
        fake_directory.cleanup()
    for name in names:
        failed = [label for label, passed in rows[name] if not passed]
        if failed:
            print('  VELDO-0152 detail:', name, '; '.join(failed))
        expect('VELDO-0152 ' + name, bool(rows[name]) and not failed)
    for line in conform_formats.describe('0152_intake_routes', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0152_intake_routes', bool(fake_capture[1]) and not fake_capture[0])

_v152_suite()
