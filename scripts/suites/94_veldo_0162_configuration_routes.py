"""VELDO-0162: passkey API saves, exact owner decisions and named default revisions.
Real setup and command writers, generated keys and local fake CLI format readback.
"""

def _v162_suite():
    import copy
    import importlib.util
    import json
    from pathlib import Path
    PRODUCTION = {
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_service_api.py': ROOT / ".veldo" / "control_service_api.py",
        'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
        'control_team.py': ROOT / ".veldo" / "control_team.py",
        'control_team_routes.py': ROOT / ".veldo" / "control_team_routes.py",
    }
    SCAFFOLD = ROOT / ".veldo" / "init_scaffold.py"
    names = ('routes/redaction', 'routes/contract', 'install/assets', 'configuration/revisions', 'configuration/unauthorized-save',
        'configuration/refusals', 'team/roundtrip', 'team/stale-team', 'team/staffing', 'team/owner-save',
        'team/decider', 'team/unverified-assertion', 'team/owner-answer', 'team/telegram', 'team/decline',
        'team/other-request', 'default/history', 'default/refusals', 'default/named-revision', 'default/staffing', 'team/setup-requester', 'team/reproposal',
        'team/consumed', 'team/application-exception', 'format/fake-lines')
    rows = {name:[] for name in names}
    def check(row, label, condition):
        rows[row].append((label, bool(condition)))
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module
    here = Path(__suite_file__).resolve().parents[2]
    helper = load('v162_fixture', here / 'proof/VELDO-0162/fixture.py')
    import tempfile
    fake_formats = load('v162_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    conform_formats = load('v162_conform_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    fake_directory = tempfile.TemporaryDirectory(prefix='v162-formats-')
    base = Path(fake_directory.name)
    L = load('v162_format_launch', ROOT / '.veldo/control_launch.py')
    fake = fake_formats.embed('''import json,sys
from pathlib import Path
def emit(event):
    print(json.dumps(complete_event(event)), flush=True)
if sys.argv[1:3] == ['login', 'status']:
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
if Path(sys.argv[0]).name == 'claude':
    opening = json.loads(sys.stdin.readline())
    if opening['type'] != 'control_request':
        raise ValueError('expected initialize')
    emit({'type': 'control_response', 'response': {'subtype': 'success',
          'request_id': opening['request_id'], 'response': {'account': {
          'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    sys.stdin.readline()
    emit({'type': 'assistant', 'message': {'usage': {'input_tokens': 2, 'output_tokens': 3}}})
    emit({'type': 'result', 'subtype': 'success', 'is_error': False,
          'usage': {'input_tokens': 2, 'output_tokens': 4}})
else:
    sys.stdin.read()
    emit({'type': 'thread.started', 'thread_id': 'fixture-thread'})
    emit({'type': 'turn.started'})
    emit({'type': 'turn.completed', 'usage': {'input_tokens': 2, 'output_tokens': 4}})
''')
    try:
        with helper.fixture(ROOT, PRODUCTION, fake) as f:
            conn, S, service, api, call = (f[k] for k in ('conn','S','service','api','call'))
            authority = service.authority
            routes = getattr(authority, 'team_routes', None)
            CT = f['CT']; cfg = f['CG']; ids = f['ids']
            prefix = '/api/v1/domains/factory-domain/'
            owner_login = f['enroll']('olga'); member_login = f['enroll']('zed')
            f['activate']('bcengi'); f['activate']('newproject'); f['activate']('understaffed', budget=1)
            def post(path, body, who='olga'):
                return call('POST', prefix + path, body, who=who)
            def get(path):
                return call('GET', prefix + path)[2]
            def save_team(team, version, who='olga'):
                return post('teams/save', dict(project='bcengi', team=team, team_version=version), who)
            def team_read():
                return get('team?project=bcengi').get('team') or {}
            def count(kind):
                return conn.execute('SELECT COUNT(*) FROM entities WHERE kind=?',(kind,)).fetchone()[0]
            def answer(request, choice='accept'):
                receipt = f['presenter'].current(request) or {}
                return post('decisions/answer', dict(request_id=request, request_version=receipt.get('request_version'),
                    presentation_id=receipt.get('presentation_id'), presentation_digest=receipt.get('brief_digest'),
                    presentation_version=receipt.get('presentation_version'), choice=choice,
                    rationale='I read the team proposal and choose this ruling.'))
            registrations = {r.operation:r.name for r in f['API'].ROUTES if r.operation}
            commands = authority.commands()
            actions = {a.operation:a.route for a in f['API'].MO.ACTIONS if a.operation}
            expected = {'save_capability_configuration':('configurations.save','save_agent_configuration'),
                'propose_team':('teams.save','team_operation'), 'save_default_team':('teams.default_save','save_default_team_revision')}
            check('routes/contract', 'routes, assertions, UI contract and commands agree', all(
                registrations.get(op)==route and actions.get(op)==route and commands.get(op)==command
                and op in f['AS'].OPERATIONS for op,(route,command) in expected.items()))
            checks = []
            for path, body in [('configurations/save',dict(definition={},base=0)),
                               ('teams/save',dict(project='bcengi',team={},team_version=0)),
                               ('teams/default/save',dict(team={},base=0))]:
                checks.append(call('POST',prefix+path,body,session=False)[0] == 401)
                checks.append(post(path,dict(body,actor_id='olga'))[0] == 400)
            check('routes/contract', 'each save requires session and rejects body actor', all(checks))
            scaffold = load('v162_scaffold', SCAFFOLD)
            assets = []
            for name in PRODUCTION:
                rel = '.veldo/'+name
                engine = ROOT / 'engine' / rel
                assets.append(engine.is_file() and (ROOT/rel).is_file() and rel in scaffold._FILES
                              and engine.read_bytes() == (ROOT/rel).read_bytes())
                if engine.is_file():
                    scaffold._lay(engine, f['base']/'laid'/rel, rel, [], [])
                    assets.append((f['base']/'laid'/rel).read_bytes()==engine.read_bytes())
            check('install/assets', 'all installed engine assets and new route module match', all(assets))
            # Catalog and skill revisions are accepted through their actual owning writers.
            catalog = f['catalog']
            # The catalog save API uses the same flat definition shape as the owning writer.
            catalog.save(dict(id='atlassian', label='Fixture Atlassian', transport='stdio', command='/usr/bin/true',
                arguments=[],url=None,environment={},headers={},hosts=['linux'],read_only_tools=['jira.get']),
                principal='olga',base=0,command_id=f['next_id']('catalog'))
            f['configurations'].save(dict(skill='coding',source='factory',path='skills/coding.md'),
                principal='olga',base=0,command_id=f['next_id']('skill'),kind=cfg.KINDS[1])
            definition = dict(role='builder_jira',engine='claude_code',native_tools=[dict(name='Read',load='always'),
                dict(name='Edit',load='when assigned')],mcp=[dict(server='atlassian',revision=1,tools=['jira.get'],load='always'),
                dict(server='tickets',revision=1,tools='all',load='when assigned')],
                skills=[dict(skill='coding',revision=1,load='when assigned')],
                instructions=[dict(source='project',path='README.md',load='always'),
                              dict(source='factory',path='instructions/build.md',load='when assigned')],
                settings={'model':'sonnet','effort':'high'})
            first = post('configurations/save',dict(definition=definition,base=0))
            second_definition = copy.deepcopy(definition); second_definition['settings']['effort']='medium'
            second = post('configurations/save',dict(definition=second_definition,base=1))
            saved = [get('configurations/revision?role=builder_jira&revision='+str(n)).get('configuration') for n in (1,2)]
            exact = []
            for n,(sent,served) in enumerate(zip((definition,second_definition),saved),1):
                stored = f['entity'](cfg.identity(ids['domain_uuid'],ids['repository_uuid'],cfg.KINDS[0],'builder_jira',n))
                exact.append(served is not None and stored is not None and served==stored['data']
                    and all(served.get(k)==v for k,v in sent.items()))
            check('configuration/revisions','passkey sessions and exact immutable revision reads',
                owner_login[1][0]==200 and member_login[1][0]==200 and first[0]==second[0]==200 and all(exact))
            before = count(cfg.KINDS[0])
            unauthorized = post('configurations/save',dict(definition=dict(definition,role='forbidden'),base=0),'zed')
            check('configuration/unauthorized-save','command checks verified member with no saved revision',
                first[0]==200 and unauthorized[2].get('refusal')=='unauthorized:agent_owner' and count(cfg.KINDS[0])==before)
            stale = post('configurations/save',dict(definition=definition,base=1))
            invalid = post('configurations/save',dict(definition=dict(definition,engine='unknown'),base=2))
            check('configuration/refusals','stale and invalid configuration names with no writes', first[0]==200
                and stale[2].get('refusal','').startswith('stale_version')
                and invalid[2].get('refusal')=='invalid_input:agent_configuration' and count(cfg.KINDS[0])==before)
            plain = f['team']()
            requests = count('assignment')
            owner = save_team(plain,0); held = team_read()
            check('team/owner-save','owner save current immediately and no decision request', owner[0]==200
                and held.get('revision')==1 and held.get('team')==plain and held.get('proposal') is None
                and count('assignment')==requests)
            accepted = (held.get('revisions') or [{}])[-1]
            check('team/decider','journal and acceptance bind actual principal and signed assertion',
                owner[0]==200 and accepted.get('principals')==['olga']
                and accepted.get('assertion_digest')==CT._digest(f['assertions'][-1]['assertion'])
                and held.get('history',[{}])[-1].get('by')=='olga'
                and conn.execute('SELECT principal FROM journal WHERE command_id=?',
                    (owner[2].get('api_request_id'),)).fetchone()[0]=='olga')
            specialized = copy.deepcopy(plain)
            specialized['roles']['builder_jira'] = dict(f['role'](['w-build'],'implement'),kind='specialist',
                capability_configuration={'role':'builder_jira','revision':1})
            extended = save_team(specialized,held.get('version',0)); current=team_read()
            check('team/roundtrip','required then specialist exact through team read', owner[0]==extended[0]==200
                and current.get('revision')==2 and current.get('team')==specialized
                and all(set(role)==set(CT.ROLE_FIELDS) for role in specialized['roles'].values()))
            stale = save_team(plain,0)
            check('team/stale-team','stale team is refused without changing it', extended[0]==200
                and 'stale_subject:version' in stale[2].get('refusal','') and team_read()==current)
            # Both authority and Teams verify the edge signature on the owner path.
            if extended[0]==200:
                packet = copy.deepcopy(f['assertions'][-2] if f['assertions'][-1]['assertion']['operation']=='propose_team' else f['assertions'][-1])
                a = packet['assertion']; a['parameters']['team_version']=current['version']
                a['request_id']=f['next_id']('unverified'); a['parameters']['team']=plain
                derived = f['AS'].domain_request(a)
                # A well-formed SSH signature from the wrong generated key, not malformed text.
                packet['signature']=f['sign_as']('zed',S.canonical_bytes(a))
                packet['domain_signature']=f['sign_as']('zed',S.canonical_bytes(derived))
                rejected=authority.apply(packet)
                direct=routes.teams.apply(dict(command=derived,signature=packet['domain_signature']),api_assertion=packet)
                check('team/unverified-assertion','both verification boundaries refuse named signature',
                    rejected.get('reason')=='unauthenticated:signature' and direct.get('reason')=='unauthenticated:signature'
                    and team_read()==current)
            else:
                check('team/unverified-assertion','owner path exists',False)
            bads=[]
            for flaw in ('missing','unresolved','roster'):
                bad=copy.deepcopy(specialized)
                if flaw=='missing': del bad['roles']['builder_jira']['capability_configuration']
                if flaw=='unresolved': bad['roles']['builder_jira']['capability_configuration']['revision']=999
                if flaw=='roster': del bad['roles']['independent_review']
                refused=save_team(bad,current.get('version',0))
                rid=refused[2].get('owner_request'); req=f['inbox'].read(rid) if rid else None
                reason={'missing':'missing_capability_configuration','unresolved':'unresolved_capability_configuration',
                        'roster':'missing_staffing'}[flaw]
                bads.append('incomplete_roster:'+reason in refused[2].get('refusal','') and req is not None
                            and req['data']['owner']=='olga' and team_read()==current)
            check('team/staffing','named staffing refusals each carry owner request and write no team',all(bads))
            proposed=save_team(plain,current.get('version',0),'zed')
            pending=team_read(); rid=proposed[2].get('owner_request')
            repeated=save_team(plain,current.get('version',0),'zed')
            req=f['inbox'].read(rid) if rid else None
            state = f['CM'].authority_state(S, conn)
            qualification = f['AC'].membership_entry(state['membership'], 'qualification-requester')
            pm = f['AC'].membership_entry(state['membership'], 'pm')
            check('team/setup-requester', 'real setup enrolls narrow qualification and all-project PM; member request opens',
                f['setup_report'] is not None and f['channel'].requester[0]=='qualification-requester'
                and qualification['scope']==['channel-qualification'] and pm['scope']=='*'
                and proposed[0]==200 and req is not None and routes.teams.requester=='pm')
            target=CT.amendment_target(pending) if pending.get('proposal') else None
            terms=f['entity'](req['data']['subject']['ref']) if req else None
            check('team/owner-answer','member proposal waits for one exact request and repeat finds it',
                proposed[0]==repeated[0]==200 and pending.get('revision')==2 and pending.get('team')==specialized
                and req is not None and req['data']['owner']=='olga' and req['data']['brief']==CT.amendment_brief(pending)
                and terms is not None and terms['data']['target']==target and repeated[2].get('owner_request')==rid
                and team_read()==pending)
            if rid:
                answered=answer(rid); applied=team_read()
                check('team/owner-answer','API answer applies existing amend settlement',answered[0]==200
                    and applied.get('revision')==3 and applied.get('team')==plain and applied.get('proposal') is None
                    and applied['revisions'][-1].get('settlement_id') is not None
                    and (answered[2].get('team_application') or {}).get('ok') is True)
            proposal=save_team(specialized,team_read().get('version',0),'zed')
            rid=proposal[2].get('owner_request')
            if rid:
                acquired, settled=f['telegram'](f['presenter'].current(rid))
                check('team/telegram','Telegram answer applied by production service publication hook',
                    bool(acquired) and bool(settled) and team_read().get('revision')==4
                    and team_read().get('team')==specialized and team_read().get('proposal') is None)
            else: check('team/telegram','request exists',False)
            proposal=save_team(plain,team_read().get('version',0),'zed'); rid=proposal[2].get('owner_request')
            prior=team_read()
            if rid:
                declined=answer(rid,'reject')
                check('team/decline','settled rejection leaves previous revision current',declined[0]==200
                    and team_read().get('revision')==prior.get('revision') and team_read().get('team')==prior.get('team'))
                wrong_target=CT.amendment_target(prior); wrong_target['digest']=CT._digest('another proposal')
                other,receipt=f['present'](f['next_id']('other'),wrong_target,'A different proposal.')
                f['answer'](receipt,'accept'); result=routes.apply_settled(other)
                check('team/other-request','another settled target cannot amend pending team',
                    result is not None and not result.get('ok') and result.get('reason')=='stale_subject:revision'
                    and team_read().get('revision')==prior.get('revision'))
            else:
                check('team/decline','request exists',False); check('team/other-request','request exists',False)
            if rid:
                again = save_team(plain, team_read().get('version', 0), 'zed')
                fresh = again[2].get('owner_request')
                opened = f['inbox'].read(fresh) if fresh else None
                check('team/reproposal', 'same roster after decline opens a new exact request; pending repeat reuses it',
                    again[0]==200 and fresh is not None and fresh!=rid and opened is not None
                    and opened['data'].get('settlement') is None
                    and opened['data']['brief']==CT.amendment_brief(team_read())
                    and save_team(plain, prior['version'], 'zed')[2].get('owner_request')==fresh)
            else:
                check('team/reproposal', 'initial request exists', False)
            default1=post('teams/default/save',dict(team=specialized,base=0))
            old=get('team?project=default&revision=1').get('team')
            default2=post('teams/default/save',dict(team=plain,base=1))
            new=get('team?project=default').get('team')
            check('default/history','immutable saved revision and independently readable new head',
                default1[0]==default2[0]==200 and old is not None and old.get('team')==specialized
                and get('team?project=default&revision=1').get('team')==old and new is not None
                and new.get('revision')==2 and new.get('team')==plain and new.get('previous')==old.get('digest'))
            before=count('default_team_revision')
            refuses=[post('teams/default/save',dict(team=plain,base=0)),
                     post('teams/default/save',dict(team=plain,base=2),'zed'),
                     post('teams/default/save',dict(team={'bad':True},base=2))]
            check('default/refusals','stale base, non-factory owner and invalid schema store nothing',
                default1[0]==200 and all(r[0]>=400 for r in refuses)
                and refuses[0][2].get('refusal','').startswith('stale_version')
                and refuses[1][2].get('refusal')=='unauthorized:default_team_owner'
                and refuses[2][2].get('refusal')=='invalid_input:team' and count('default_team_revision')==before)
            if routes is not None and old:
                TR=load('v162_route_helpers', f['mods']/'control_team_routes.py')
                unrelated, unrelated_receipt = f['present'](f['next_id']('wrong-default-brief'),
                    TR.default_target('newproject', old), 'Approve something that shows no default revision.')
                f['answer'](unrelated_receipt, 'accept')
                refused = routes.apply_settled(unrelated)
                check('default/named-revision', 'an answer whose brief showed something else gives no team',
                    refused.get('reason')=='stale_subject:default_team_brief'
                    and get('team?project=newproject').get('team') is None)
                for project,row in [('newproject','default/named-revision'),('understaffed','default/staffing')]:
                    request,receipt=f['present'](f['next_id']('default-proposal'),TR.default_target(project,old),
                                                TR.default_brief(project,old))
                    f['answer'](receipt,'accept')
                    requests=count('assignment')
                    result=routes.apply_settled(request)
                    served=get('team?project='+project).get('team')
                    if project=='newproject':
                        check(row,'answer names old default even after newer default save, with no second question',
                            result.get('ok') and served is not None and served.get('revision')==1
                            and served.get('team')==specialized and count('assignment')==requests
                            and served['revisions'][0]['default_team']=={'revision':1,'digest':old['digest']})
                    else:
                        check(row,'project staffing checked at application and owner request returned',
                            not result.get('ok') and result.get('reason','').startswith('incomplete_roster:over_budget')
                            and result.get('owner_request') is not None and served is None)
            else:
                check('default/named-revision','default command exists',False)
                check('default/staffing','default command exists',False)
            if routes is not None:
                service.publish()
                before_observations = len(routes.observations)
                before_metrics = copy.deepcopy(routes.teams.metrics())
                for advance in range(3):
                    changed = post('configurations/save', dict(definition=definition, base=2+advance))
                    check('team/consumed', 'a real configuration save advances the journal', changed[0]==200)
                    service.publish()
                # A reconstructed consumer must also see the durable consumption record.
                restarted = type(routes)(routes.teams, routes.settlement, routes.presenter)
                replayed = restarted.apply_pending()
                check('team/consumed', 'refused and applied settlements are consumed across publication and reconstruction',
                    len(routes.observations)==before_observations and routes.teams.metrics()==before_metrics
                    and not replayed and not restarted.observations)
                fault_request, receipt = f['present'](f['next_id']('fault-default'),
                    TR.default_target('newproject', old), TR.default_brief('newproject', old))
                f['answer'](receipt, 'accept')
                original_inherit = routes.inherit
                attempts = []
                def fail_inherit(request):
                    attempts.append(request)
                    raise RuntimeError('fixture application fault')
                routes.inherit = fail_inherit
                # A real local hint socket proves an application fault cannot hide a journal hint.
                import socket
                hint_path = f['base'] / 'hints.sock'
                listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                listener.bind(str(hint_path)); listener.listen(); listener.settimeout(2)
                service.subscribe(str(hint_path))
                try:
                    try:
                        published = service.publish()
                    except Exception:
                        published = {'sent': 0}
                    hint = None
                    if published['sent']:
                        peer, _ = listener.accept()
                        with peer:
                            hint = json.loads(peer.recv(65536))
                    routes.inherit = original_inherit
                    observations = [o for o in routes.observations if o.get('request')==fault_request]
                    service.publish()
                    check('team/application-exception', 'fault recorded once, consumed and actual subscriber gets the hint',
                        attempts==[fault_request] and hint is not None and hint.get('watermark')==published.get('watermark')
                        and len(observations)==1 and observations[0].get('reason')=='unavailable_service:team_application'
                        and not restarted.apply_pending())
                finally:
                    routes.inherit = original_inherit
                    listener.close()
                # A failure before the per-request consumer is also recorded without hiding hints.
                original_pending = routes.apply_pending
                def fail_pending():
                    raise RuntimeError('fixture scan fault')
                routes.apply_pending = fail_pending
                listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                hint_path = f['base'] / 'scan-hints.sock'
                listener.bind(str(hint_path)); listener.listen(); listener.settimeout(2)
                service.subscribe(str(hint_path))
                try:
                    try:
                        published = service.publish()
                    except Exception:
                        published = {'sent': 0}
                    hint = None
                    if published['sent']:
                        peer, _ = listener.accept()
                        with peer:
                            hint = json.loads(peer.recv(65536))
                    logged = [json.loads(line) for line in service.mcp_log.read_text().splitlines()] if service.mcp_log.exists() else []
                    check('team/application-exception', 'consumer scan exception is logged and subscriber still receives the hint',
                        hint is not None and service.counts.get('team_application_errors')==1
                        and any(event.get('reason')=='unavailable_service:team_application' for event in logged))
                finally:
                    routes.apply_pending = original_pending
                    listener.close()
            # Ordinary reads use the existing API redactor even for free text in team roles.
            import secrets
            secret = 'gh' + 'p_' + secrets.token_hex(20)
            sensitive = copy.deepcopy(plain)
            sensitive['roles']['elaboration']['expertise'] = [secret]
            written = save_team(sensitive, team_read().get('version',0))
            response = get('team?project=bcengi')
            check('routes/redaction','generated credential in role text never returns through the read route',
                written[0]==200 and secret not in json.dumps(response) and bool(response.get('redacted')))
            proposed = save_team(sensitive, team_read().get('version', 0), 'zed')
            rid = proposed[2].get('owner_request')
            answered = answer(rid) if rid else (0, {}, {})
            check('routes/redaction', 'the returned team application also uses the API redactor',
                answered[0]==200 and (answered[2].get('team_application') or {}).get('ok') is True
                and secret not in json.dumps(answered[2]))
    except Exception as error:
        print('  VELDO-0162 detail: suite did not run to its end:',repr(error))
        import traceback
        traceback.print_exc()
        for name in names: check(name,'journey completed',False)
    finally:
        fake_capture = conform_formats.conform_fake(locals(), '0162_configuration_routes')
        check('format/fake-lines', 'setup fake CLI output matches captured binary formats',
              bool(fake_capture[1]) and not fake_capture[0])
        fake_directory.cleanup()
    for name in names:
        failed=[label for label,passed in rows[name] if not passed]
        if failed: print('  VELDO-0162 detail:',name,'; '.join(failed))
        expect('VELDO-0162 '+name,bool(rows[name]) and not failed)

    for line in conform_formats.describe('0162_configuration_routes', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0162_configuration_routes', bool(fake_capture[1]) and not fake_capture[0])

_v162_suite()
