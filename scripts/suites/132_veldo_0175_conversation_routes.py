"""VELDO-0175 AC2 and AC4: the factory PM's five routes, two of them to conversations, and the owner's typed and
plain-words commands on a conversation from Telegram (and AC1's closed refusal for a reply the PM reads after its
conversation closed).

Run: python3 scripts/selftest.py --suite 132_veldo_0175_conversation_routes

Only shared ROOT and expect (and __suite_file__) are consumed. Loads the signed VELDO-0152 fixture
(proof/VELDO-0152/fixture.py: a real SQLite store, signed memberships, the factory project and its team, the
VELDO-0064 inbox and VELDO-0065 presenter over a loopback Bot API) and runs the factory PM as suite 93 does: the
production factory loop's pass dispatches the PM's coordination run on its ordinary Runner to a fake Claude Code
whose final message is the route or reading document this suite supplies, and the production PM cycle applies it
through intake. Telegram messages reach intake through the production VELDO-0066 Acquirer; API messages are signed
by the API edge's real key. A conversation's sent messages are its reply parts as the production delivery
(control_conversation_channel.Replies) sends and records them, for a turn this suite ends with a reply (suite 131
runs turns on fake engines). Attaching a project clones its local fixture repository. No real Telegram service,
token, engine or network beyond loopback. Writes only temporary fixtures.
"""


def _v175_routes_suite():
    import contextlib
    import importlib.util
    import json
    from pathlib import Path
    import sys
    import tempfile
    import time
    from types import SimpleNamespace

    PRODUCTION = {
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
        'control_intake_conversation.py': ROOT / ".veldo" / "control_intake_conversation.py",
        'control_intake_routes.py': ROOT / ".veldo" / "control_intake_routes.py",
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
        'control_conversation_channel.py': ROOT / ".veldo" / "control_conversation_channel.py",
        'control_workflow_cycle_pm.py': ROOT / ".veldo" / "control_workflow_cycle_pm.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
    }
    ROWS = ('AC2/new-conversation', 'AC2/open-conversation', 'AC2/project-routes', 'AC2/unclear-offers',
            'AC2/route-input', 'AC2/conversation-refused', 'AC2/observability',
            'AC4/slash-role', 'AC4/slash-attach', 'AC4/attach-initial-branch', 'AC4/slash-close', 'AC4/plain-words', 'AC4/plain-none-is-a-turn',
            'AC4/reads-only-his-words', 'AC4/other-member', 'AC4/no-reply', 'AC4/unknown-name', 'AC4/observability',
            'AC1/closed-before-reading')
    rows = {name: [] for name in ROWS}

    def check(name, label, condition):
        rows[name].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    if not all(Path(p).is_file() for p in PRODUCTION.values()):
        for name in ROWS:
            expect('VELDO-0175 ' + name, False)
        return
    fake_formats = load('v175p_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    helper = load('v175p_fixture', Path(__suite_file__).resolve().parents[2] / 'proof/VELDO-0152/fixture.py')
    fake_directory = tempfile.TemporaryDirectory(prefix='v175p-fake-')
    fake_base = Path(fake_directory.name)
    try:
        with helper.fixture(ROOT, PRODUCTION, cycle_budget=200) as f:
            S, conn, base, mods = (f[k] for k in ('S', 'conn', 'base', 'mods'))
            domain, repository, ids = (f[k] for k in ('DOMAIN', 'REPO', 'ids'))
            IN = load('v175p_intake', mods / 'control_intake.py')
            PM = load('v175p_pm', mods / 'control_workflow_cycle_pm.py')
            CV = load('v175p_conversation', mods / 'control_conversation.py')
            CC = load('v175p_channel', mods / 'control_conversation_channel.py')
            EV = load('v175p_attribution', mods / 'control_channel_attribution.py')
            SV = load('v175p_service', mods / 'control_service.py')
            SV.CV = CV
            acquirer = EV.Acquirer(S, f['CM'], f['P'], f['V'], f['presenter'],
                EV.TelegramAcquisitionEdge(f['P'], f['url'], 'bot89'), conn, 'authority', f['journal_sign'],
                'api-edge', lambda b: f['sign_as']('api-edge', b))
            events = []
            conversations = CV.Conversations(S, conn, domain=domain, principal='team-service', signer='authority',
                                             sign=f['journal_sign'], state_root=base / 'state', observe=events.append)
            intake = IN.Intake(S, f['CM'], f['AC'], acquirer, conn, domain=domain,
                               projects=lambda: IN.store_projects(conn), api_edge='api-edge',
                               journal_signer='authority', sign=f['journal_sign'], asker=f['presenter'].edge,
                               conversations=conversations)
            replies = CC.Replies(S, conn, 'authority', f['journal_sign'], f['presenter'].edge)
            bot_id = f['api']['user']['id']
            olga_chat, zed_chat = 5890001, 5890002

            def activate(name, prefixes):
                return f['projects'].apply(f['signed']('olga', dict(ids, operation='activate', project=name,
                    principal='olga', command_id=f['next_id']('project'), nonce=f['next_id']('nonce'), owner='olga',
                    charter={'purpose': 'Fixture work'}, execution_repository=repository,
                    authority_policy={'admission': ['admission_authority']},
                    coordination_budget={'capacity': 5, 'invocations': 100, 'wall_seconds': 500},
                    ticket_key_prefixes=prefixes)))

            def telegram(text, who='olga', reply=None):
                chat = olga_chat if who == 'olga' else zed_chat
                msg = f['message'](f['api'], {'id': chat, 'is_bot': False, 'first_name': who},
                                   {'id': chat, 'type': 'private'}, text, reply)
                f['api'].setdefault('updates', []).append(dict(update_id=msg['message_id'], message=msg))
                acquirer.acquire()
                return intake.receive('telegram_message', EV.evidence_id(bot_id, msg['message_id'])), msg

            def post(text, who='olga', conversation=None):
                body = dict(schema=IN.API_SCHEMA, domain=domain, request_id=f['next_id']('message'), edge='api-edge',
                            principal=who, text=text, project=None, clarifies=None)
                if conversation is not None:
                    body['conversation'] = conversation
                return intake.receive('api_request', dict(request=body, signature=f['sign_as'](
                    'api-edge', S.canonical_bytes(body))))

            def bot_lines(chat, after=0):
                """What the bot sent to `chat` after message id `after`: (message id, text, reply to)."""
                return sorted((mid, m['text'], (m.get('reply_to_message') or {}).get('message_id'))
                              for (c, mid), m in f['api']['messages'].items()
                              if c == chat and mid > after and m['from'].get('is_bot'))

            def last_id():
                return max([mid for (_c, mid) in f['api']['messages']] or [0])

            activate('bcengi', ['BCG'])
            # The conversation roles of the default team, each on its own accepted capability configuration.
            for name, engine in (('assistant', 'claude_code'), ('assistant_codex', 'codex')):
                f['configurations'].save(dict(role=name, engine=engine, native_tools=[], mcp=[], skills=[],
                                              instructions=[], settings={}), principal='steward', base=0,
                                         command_id=f['next_id']('capability'))

            def assistant(name, engine):
                spec = f['role'](['w-late'], 'assist', (), engines=(engine,))
                spec.update(kind='specialist', capability_configuration={'role': name, 'revision': 1})
                return spec

            # THE FACTORY PM's RUN, as suite 93 runs it: the factory pass, the PM's coordination dispatch on the
            # line's Runner, a fake Claude Code whose final message is the document this suite supplies.
            GP = load('v175p_git', mods / 'git_process.py')
            # The project's branch has the name a fresh repository starts on (master here): the attach clone, a fresh
            # repository, must still take it (VELDO-0177's clone, fixed in VELDO-0175).
            fresh = base / 'fresh-init'
            GP.run(['git', 'init', '-q', str(fresh)], check=True, capture_output=True)
            initial = GP.run(['git', '-C', str(fresh), 'symbolic-ref', '--short', 'HEAD'], check=True,
                             capture_output=True, text=True).stdout.strip()
            source = base / 'source'
            source.mkdir()
            (source / 'README').write_text('Fixture accepted source.\n')
            for args in (('init', '-q', '-b', initial), ('add', 'README'), ('commit', '-qm', 'Fixture source')):
                GP.run(['git', '-C', str(source), *args], check=True, capture_output=True,
                       identity=('Fixture', 'fixture@example.invalid'))
            commit = GP.run(['git', '-C', str(source), 'rev-parse', 'HEAD'], check=True, capture_output=True,
                            text=True).stdout.strip()
            RS = load('v175p_snapshots', mods / 'control_readset.py')
            __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind_paths'](
                mods, conn, domain, {repository: str(source)})
            RS.attach_revisions(S, conn, domain, {repository: str(source)}).accept(
                'revision-175', repository, commit, 'pm', documents={'README': PM.SN.digest((source / 'README').read_bytes())},
                signer='authority', sign=f['journal_sign'], authority_generation=1)
            EN = load('v175p_enrollment', mods / 'control_enrollment.py')
            signers = base / 'enrollment-signers'
            signers.write_text('olga ' + f['public']['olga'] + '\n')
            EN.enroll(source, domain, ids['store_uuid'], str(f['db']), 'fixture-host', 1,
                      lambda b: f['sign_as']('olga', b, SV.EL.ENROLLMENT_NAMESPACE), 'olga', '2026-10-03T00:00:00Z',
                      repository_uuid=repository)
            service = SV.Service(dict(domain_uuid=domain, store_uuid=ids['store_uuid'], principal='team-service',
                authority_generation=1, repositories={repository: [str(source)]},
                journal_key=str(f['keyfile']['authority']), host_identity='fixture-host',
                enrollment_signers=str(signers), observations=str(base / 'events.jsonl')), conn)
            service.channel = SimpleNamespace(ingress=SimpleNamespace(inbox=f['inbox'], presenter=f['presenter'],
                settlement=f['settlement'], acquirer=acquirer))
            # The service's conversations: the PM cycle's intake sends the commands and opens conversations here.
            service.conversations = lambda: conversations
            result_file, packet_file = base / 'result.json', base / 'packet.json'
            printed = fake_base / 'printed.jsonl'
            fake_source = fake_formats.embed('''import json,sys
from pathlib import Path
def emit(event):
    line = complete_event(event)
    print(json.dumps(line), flush=True)
if sys.argv[1:3] == ['login', 'status']:
    sys.exit(0)
if '--input-format' in sys.argv:
    opening = json.loads(sys.stdin.readline())
    emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': opening['request_id'],
          'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    packet = json.loads(json.loads(sys.stdin.readline())['message']['content'])
    result = 'Fixture PM read-back.'
else:
    packet = json.load(sys.stdin)
    Path(sys.argv[2]).write_text(json.dumps(packet))
    result = Path(sys.argv[1]).read_text()
emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': result}],
      'usage': {'input_tokens': 2, 'output_tokens': 3}}})
emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': result,
      'usage': {'input_tokens': 2, 'output_tokens': 4}})
''')
            fake = fake_base / 'claude'
            fake.write_text(fake_source)
            trust_signers = base / 'receiver-enrollment-signers'
            trust_signers.write_text('')
            host_trust = base / 'receiver-host-trust.json'
            host_trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='fixture-host',
                                                  enrollment_signers=str(trust_signers))))
            host_trust.chmod(0o600)
            config = base / 'receiver.json'
            config.write_text(json.dumps(dict(store=str(f['db']), journal_key=str(f['keyfile']['authority']),
                principal='pm', workspace=str(source), host_trust=str(host_trust), domain=domain,
                repository=repository, records=str(base / 'records'),
                adapters={'claude': {'identity': 'reported', 'argv': [sys.executable, '-B', str(mods / 'control_launch.py'),
                    'exec', sys.executable, '-B', str(fake), str(result_file), str(packet_file)]}})))
            runtime = PM.CY.installed_runtime()
            installed = base / 'receiver-installed.json'
            installed_data = json.loads(config.read_text())
            installed_data['adapters']['claude']['engine'] = 'claude_code'
            installed.write_text(json.dumps(installed_data))
            service.config['receiver'] = {'configs': {repository: str(installed)}}
            saved = SV.TR.TeamRoutes(f['service'], f['settlement'], f['presenter']).save_default(
                f['team'](assistant=assistant('assistant', 'claude_code'),
                          assistant_codex=assistant('assistant_codex', 'codex')),
                'olga', 0, f['next_id']('default-team'), 'sha256:' + '0' * 64)
            factory = SV.FactoryLoop(service, {'repositories': {}})
            line = factory.lines[repository]
            line.runner.receiver = lambda contract: SV.L.invoke(config, contract, line.dispatches)
            line.runner.account = 'fixture-account'
            line.engines, line.hosts = {'claude': 'claude_code'}, {'claude': 'fixture-host'}
            line.pm_cycles = PM.from_line(line)
            line.pm_cycles.runtime = runtime
            pm_intake = line.pm_cycles.services['intake']
            for scope, subject in (('account', 'fixture-account'), ('project', 'factory')):
                line.reservations.configure('policy/' + subject, scope, subject,
                                            dict(capacity=5, invocations=500, wall_seconds=50000), now=time.time())
            print('  VELDO-0175 default team:', saved.get('outcome'))

            def run(value):
                result_file.write_text(json.dumps(value))
                factory.wake('accepted_message')
                factory.run()
                cycles = line.pm_cycles
                record = max(cycles.records('factory'), key=lambda r: r['watermark'])
                if record.get('dispatch') in line.runner.launches:
                    line.runner.wait(line.runner.launches[record['dispatch']], timeout=30)
                    factory.wake('run_end')
                    factory.run()
                latest = next(r for r in cycles.records('factory') if r['cycle'] == record['cycle'])
                if latest['state'] != 'proposed':
                    print('  VELDO-0175 detail: cycle', latest.get('refusal'), latest.get('proposals'))
                return latest

            def route(pid, name, **extra):
                return dict(schema=IN.RT.SCHEMA, proposal_id=pid, route=name, reason='Fixture PM reason.', **extra)

            def reading(pid, command, name=None):
                return dict(schema='veldo.conversation_reading/v1', proposal_id=pid, command=command, name=name,
                            reason='Fixture PM reading of his words.')

            def packet():
                return (json.loads(packet_file.read_text()) if packet_file.exists() else {}).get('payload') or {}

            def turns(identity):
                return conversations.turns(identity)

            def end_with_reply(identity, text):
                """End the conversation's waiting turns, in order, each with a reply, and deliver them (the reply
                parts of a Telegram turn are messages he can answer); returns the delivered message ids."""
                for turn in [t for t in turns(identity) if t['state'] == 'waiting']:
                    dispatch = 'fixture-dispatch-%s-%d' % (identity, turn['sequence'])
                    conversations.dispatched(identity, turn['sequence'], dispatch, 1, 'fixture-account', None)
                    conversations.ended(identity, turn['sequence'], dispatch, 'completed', reply=text)
                return [r['message_id'] for r in replies.deliver() if r.get('outcome') == 'sent']

            # AC2: the PM routes an owner's message to a new conversation.
            first, first_msg = telegram('why did yesterday\'s Google Ads spend jump so much compared to the week?')
            pid = first.get('proposal_id')
            record = run(route(pid, 'new_conversation'))
            held = intake.proposal(pid) or {}
            identity = held.get('conversation')
            opened = conversations.read(identity) if identity else None
            one = turns(identity) if identity else []
            print('  VELDO-0175 AC2 new:', first.get('outcome'), record.get('state'), held.get('state'), identity)
            check('AC2/new-conversation', 'the PM run\'s new-conversation route opens a conversation with the message '
                  'as turn 1 [%s]' % held.get('state'),
                  record.get('state') == 'proposed' and opened and opened['owner'] == 'olga'
                  and opened['status'] == 'open' and opened['role'] == 'assistant' and len(one) == 1
                  and one[0]['intake_command'] == first.get('source') and one[0]['state'] == 'waiting')
            check('AC2/new-conversation', 'the inbox proposal is retired ROUTED, pointing at the conversation',
                  held.get('state') == 'ROUTED' and held.get('resolved_to') == CV.conversation_id(identity or '')
                  and (held.get('route') or {}).get('dispatch') == record.get('dispatch'))
            check('AC2/new-conversation', 'its workspace is made',
                  bool(opened) and Path(CV.workspace_of(opened)).is_dir())

            # AC2: a second message, routed by the PM to that open conversation of his, is its next turn.
            second = post('and compare it with the same day last month')
            record = run(route(second['proposal_id'], 'open_conversation', conversation=identity))
            routed = intake.proposal(second['proposal_id']) or {}
            payload = packet()
            check('AC2/open-conversation', 'an open-conversation route makes the message that conversation\'s next turn',
                  record.get('state') == 'proposed' and routed.get('state') == 'ROUTED'
                  and routed.get('resolved_to') == CV.conversation_id(identity or '') and len(turns(identity)) == 2
                  and turns(identity)[1]['intake_command'] == second.get('source'))
            check('AC2/route-input', 'the PM run\'s input lists his open conversations with their first message\'s '
                  'opening words, beside his projects [%s]' % payload.get('conversations'),
                  payload.get('operation') == 'route'
                  and payload.get('conversations') == [{'id': identity, 'opening':
                      "why did yesterday's Google Ads spend jump so much compared to the ..."}]
                  and [p['id'] for p in payload.get('projects') or []] == ['bcengi']
                  and 'new_conversation' in payload.get('instruction', '')
                  and 'open_conversation' in payload.get('instruction', ''))

            # AC2: the three project routes still do what they did.
            states = {}
            for name in ('new_project', 'existing_project', 'unclear'):
                message = post('start a new project like bcengi')
                extra = {'project': 'bcengi'} if name == 'existing_project' else {}
                run(route(message['proposal_id'], name, **extra))
                states[name] = (intake.proposal(message['proposal_id']) or {})
            check('AC2/project-routes', 'new project, existing project and unclear routes from AWAITING_ROUTE [%s]'
                  % {k: v.get('state') for k, v in states.items()},
                  states['new_project'].get('state') == 'NEW_PROJECT'
                  and states['existing_project'].get('state') == 'ROUTED'
                  and states['unclear'].get('state') == 'AWAITING_PROJECT')
            question = intake.question(states['unclear'].get('question_id')) or {}
            check('AC2/unclear-offers', 'the unclear question also offers a new conversation and his open '
                  'conversations [%s]' % question.get('prompt'),
                  question.get('candidates') == ['bcengi', 'a new project']
                  and (question.get('conversations') or [])[:1] == ['a new conversation']
                  and any(identity in c and 'Google Ads' in c for c in question.get('conversations') or [])
                  and 'a new conversation' in question.get('prompt', '') and identity in question.get('prompt', ''))

            # AC2: a route naming a conversation that is not an open one of the sender's is refused and changes nothing.
            zed_open = conversations.open('zed-talk', owner='zed', role='assistant', intake_digest='sha256:zed')
            conversations.open('closed-talk', owner='olga', role='assistant', intake_digest='sha256:closed')
            conversations.close('closed-talk', 1, owner='olga')
            refused = []
            for target in ('zed-talk', 'closed-talk', 'no-such-talk'):
                message = post('add this to that conversation')
                before = intake.proposal(message['proposal_id'])
                before_turns = {c: len(turns(c)) for c in ('zed-talk', 'closed-talk', identity)}
                record = run(route(message['proposal_id'], 'open_conversation', conversation=target))
                result = (record.get('proposals') or [{}])[0].get('result') or {}
                refused.append((target, result.get('reason'), intake.proposal(message['proposal_id']) == before,
                                {c: len(turns(c)) for c in before_turns} == before_turns))
                intake.route(route(message['proposal_id'], 'new_project'), dispatch='fixture-cleanup',
                             proposal_id=message['proposal_id'])
            check('AC2/conversation-refused', 'another member\'s, a closed and an unknown conversation are refused '
                  'invalid_input:route:conversation with nothing changed [%s]' % refused,
                  zed_open and all(r[1] == 'invalid_input:route:conversation' and r[2] and r[3] for r in refused))

            if not (identity and conversations.read(identity)):
                # The new-conversation route did not open one (a falsifier's run): the commands' conversation is
                # opened directly and his message routed to it, so the AC4 rows judge only the commands.
                fallback, _msg = telegram('a question for the commands')
                conversations.open('commands-talk', owner='olga', role='assistant', intake_digest='sha256:commands')
                intake.route(route(fallback['proposal_id'], 'open_conversation', conversation='commands-talk'),
                             dispatch='fixture-fallback', proposal_id=fallback['proposal_id'])
                identity = 'commands-talk'
            # A conversation message to reply to: turn 1's reply, delivered as the production delivery sends it.
            sent = end_with_reply(identity, 'Spend rose because two campaigns doubled their bids.')
            check('AC4/slash-role', 'the conversation has a sent reply part to reply to', len(sent) == 1)

            # AC4: /role, typed in reply to any of its messages, is the owner's role change and never a turn.
            version = conversations.read(identity)['version']
            count = len(turns(identity))
            mark = last_id()
            slash, slash_msg = telegram('/role assistant_codex', reply=sent[0] if sent else None)
            lines = bot_lines(olga_chat, mark)
            after = conversations.read(identity)
            print('  VELDO-0175 AC4 slash role:', slash.get('outcome'), slash.get('reason'), after.get('role'), lines)
            check('AC4/slash-role', 'the typed /role changes the role on the current version with the name as typed, '
                  'and makes no turn [%s %s]' % (slash.get('outcome'), slash.get('reason')),
                  slash.get('outcome') == 'command' and after['role'] == 'assistant_codex'
                  and after['version'] == version + 1 and len(turns(identity)) == count
                  and not any((intake._data(t['intake_command'], IN.SOURCE_KIND) or {}).get('text') == '/role assistant_codex'
                              for t in turns(identity)))
            check('AC4/slash-role', 'he is answered with one line naming what changed, as a reply to his command',
                  len(lines) == 1 and lines[0][2] == slash_msg['message_id'] and 'assistant_codex' in lines[0][1])
            again, _ = telegram('one more question', reply=lines[0][0] if lines else None)
            check('AC4/slash-role', 'the answer is a conversation message: a reply to it continues the conversation',
                  again.get('outcome') == 'reading' and again.get('conversation') == identity)
            run(reading(again.get('proposal_id'), 'none'))

            # AC4: /attach one of his projects: an isolated clone of its repository in the conversation's workspace.
            mark = last_id()
            attach, attach_msg = telegram('/attach bcengi', reply=sent[0] if sent else None)
            after = conversations.read(identity)
            clone = ((after.get('attachments') or [{}])[-1]).get('clone')
            lines = bot_lines(olga_chat, mark)
            check('AC4/slash-attach', 'the typed /attach attaches his project with its clone and answers one line '
                  '[%s %s]' % (attach.get('outcome'), attach.get('reason')),
                  attach.get('outcome') == 'command' and after.get('project') == 'bcengi' and clone
                  and Path(clone, 'README').is_file() and len(lines) == 1 and 'bcengi' in lines[0][1]
                  and lines[0][2] == attach_msg['message_id'])
            cloned = GP.run(['git', '-C', str(clone), 'symbolic-ref', '--short', 'HEAD'], capture_output=True,
                            text=True).stdout.strip() if clone else None
            at = GP.run(['git', '-C', str(clone), 'rev-parse', 'HEAD'], capture_output=True,
                        text=True).stdout.strip() if clone else None
            print('  VELDO-0175 attach clone:', initial, cloned, at == commit)
            check('AC4/attach-initial-branch', 'a project whose branch is named %r, the name a fresh repository '
                  'starts on, clones cleanly on that branch at its commit [%s %s]' % (initial, cloned, attach.get('reason')),
                  initial == 'master' and cloned == initial and at == commit
                  and GP.run(['git', '-C', str(clone), 'status', '--porcelain'], capture_output=True,
                             text=True).stdout == '')

            # AC4: anyone else's command is refused by name with one line and nothing changed. Telegram lets him
            # reply only in his own chat, so the message he replies to is a conversation note sent there.
            note = f['presenter'].edge.send(zed_chat, 'A note from conversation %s.' % identity)
            CC.Messages(S, conn, 'authority', f['journal_sign']).record('answer', note, bot=bot_id,
                                                                        conversation=identity, sequence=1)
            mark, before = last_id(), conversations.read(identity)
            foreign, foreign_msg = telegram('/close', who='zed', reply=note['message_id'])
            lines = bot_lines(zed_chat, mark)
            check('AC4/other-member', 'another member\'s /close is refused missing_authority:conversation_owner with '
                  'one line and nothing changed [%s]' % foreign.get('reason'),
                  foreign.get('reason') == 'missing_authority:conversation_owner'
                  and conversations.read(identity) == before and len(lines) == 1
                  and lines[0][2] == foreign_msg['message_id'])
            words, _ = telegram('we are done here', who='zed', reply=note['message_id'])
            check('AC4/other-member', 'his plain words are refused the same way, with nothing for the PM to read',
                  words.get('reason') == 'missing_authority:conversation_owner'
                  and conversations.read(identity) == before
                  and not any(p.get('state') == 'AWAITING_READING' for p in intake._all(IN.PROPOSAL_KIND)))

            # AC4: a command that replies to no conversation message, or names no role or project of his.
            mark, before = last_id(), conversations.read(identity)
            bare, bare_msg = telegram('/role assistant')
            lines = bot_lines(olga_chat, mark)
            check('AC4/no-reply', 'a typed command replying to no conversation message is refused by name with one '
                  'line, nothing changed and no inbox proposal [%s]' % bare.get('reason'),
                  bare.get('reason') == 'invalid_input:conversation_command:no_conversation'
                  and conversations.read(identity) == before and len(lines) == 1
                  and lines[0][2] == bare_msg['message_id'] and not bare.get('proposal_id'))
            unknown = []
            for text in ('/role nobody', '/attach otherproject', '/role'):
                mark = last_id()
                result, _msg = telegram(text, reply=sent[0] if sent else None)
                unknown.append((text, result.get('reason'), len(bot_lines(olga_chat, mark))))
            check('AC4/unknown-name', 'an unknown role, a project not his and a missing name are refused by name '
                  'with one line each and nothing changed [%s]' % unknown,
                  [u[1] for u in unknown] == ['invalid_input:conversation_command:unknown_role',
                                              'invalid_input:conversation_command:unknown_project',
                                              'invalid_input:conversation_command:no_name']
                  and all(u[2] == 1 for u in unknown) and conversations.read(identity) == before)

            # AC4: plain words, read by the factory PM from his own message only.
            mark, count = last_id(), len(turns(identity))
            plain, plain_msg = telegram('switch this back to Claude please', reply=sent[0] if sent else None)
            record = run(reading(plain.get('proposal_id'), 'role', 'assistant'))
            payload = packet()
            after = conversations.read(identity)
            lines = bot_lines(olga_chat, mark)
            print('  VELDO-0175 AC4 plain role:', plain.get('outcome'), record.get('state'), after.get('role'), lines)
            check('AC4/plain-words', 'his words the PM reads as a role change change the role, answered with one line, '
                  'no turn [%s %s]' % (plain.get('outcome'), record.get('state')),
                  plain.get('outcome') == 'reading' and record.get('state') == 'proposed'
                  and after['role'] == 'assistant' and len(turns(identity)) == count and len(lines) == 1
                  and lines[0][2] == plain_msg['message_id']
                  and (intake.proposal(plain.get('proposal_id')) or {}).get('state') == 'READ')
            check('AC4/reads-only-his-words', 'the PM\'s input is his own message, never a turn\'s output [%s]'
                  % sorted(payload),
                  payload.get('operation') == 'read_command' and payload.get('text') == 'switch this back to Claude please'
                  and set(payload) == {'operation', 'proposal_id', 'text', 'roles', 'projects', 'output_schema',
                                       'instruction'}
                  and 'assistant_codex' in payload.get('roles', []) and payload.get('projects') == ['bcengi']
                  and 'two campaigns' not in json.dumps(payload))
            plain_turn, _ = telegram('what were the two campaigns?', reply=sent[0] if sent else None)
            record = run(reading(plain_turn.get('proposal_id'), 'none'))
            check('AC4/plain-none-is-a-turn', 'a reply the PM reads as none of them is the conversation\'s next turn',
                  record.get('state') == 'proposed' and len(turns(identity)) == count + 1
                  and (intake._data(turns(identity)[-1]['intake_command'], IN.SOURCE_KIND) or {}).get('text')
                  == 'what were the two campaigns?')
            mark = last_id()
            done, done_msg = telegram('we are done here', reply=sent[0] if sent else None)
            record = run(reading(done.get('proposal_id'), 'close'))
            lines = bot_lines(olga_chat, mark)
            check('AC4/plain-words', '"we are done here", read as a close, closes it with one line',
                  record.get('state') == 'proposed' and conversations.read(identity)['status'] == 'closed'
                  and len(lines) == 1 and lines[0][2] == done_msg['message_id'])

            # AC4: /close typed, on a second conversation, and a command on a closed one.
            other, other_msg = telegram('a second question for a new talk')
            run(route(other['proposal_id'], 'new_conversation'))
            second_id = (intake.proposal(other['proposal_id']) or {}).get('conversation')
            second_sent = end_with_reply(second_id, 'Here is the second answer.') if second_id else []
            mark = last_id()
            close, close_msg = telegram('/close', reply=second_sent[0] if second_sent else None)
            lines = bot_lines(olga_chat, mark)
            check('AC4/slash-close', 'the typed /close closes the conversation, one line, no turn [%s]'
                  % close.get('reason'),
                  close.get('outcome') == 'command' and second_id
                  and conversations.read(second_id)['status'] == 'closed' and len(turns(second_id)) == 1
                  and len(lines) == 1 and lines[0][2] == close_msg['message_id'])
            closed_again, _ = telegram('/role assistant_codex', reply=second_sent[0] if second_sent else None)
            check('AC4/slash-close', 'a command on a closed conversation is refused by name',
                  closed_again.get('reason') == 'stale_subject:conversation_closed'
                  and conversations.read(second_id)['role'] == 'assistant')

            # Observability.
            observed = intake.observations + pm_intake.observations
            metrics = intake.metrics().get('conversations') or {}
            pm_metrics = pm_intake.metrics().get('conversations') or {}
            print('  VELDO-0175 metrics:', metrics, pm_metrics)
            check('AC2/observability', 'each route to a conversation is logged with its conversation and turn, and '
                  'conversations opened by route are counted',
                  any(e.get('operation') == 'conversation' and e.get('decided_by') == 'route'
                      and e.get('conversation') == identity and e.get('sequence') == 1 for e in observed)
                  and (pm_metrics.get('routes') or {}).get('new_conversation', 0) >= 2
                  and (pm_metrics.get('routes') or {}).get('open_conversation', 0) >= 1
                  and pm_intake.metrics()['routes'].get('new_conversation', 0) >= 2)
            check('AC4/observability', 'typed commands are counted by kind and outcome, and each is logged with its '
                  'conversation and command, never its text',
                  (metrics.get('commands') or {}).get('role/applied') == 1
                  and (metrics.get('commands') or {}).get('attach/applied') == 1
                  and (metrics.get('commands') or {}).get('close/applied') == 1
                  and (metrics.get('commands') or {}).get('role/invalid_input:conversation_command:unknown_role') == 1
                  and (pm_metrics.get('commands') or {}).get('role/applied') == 1
                  and (pm_metrics.get('commands') or {}).get('close/applied') == 1
                  and (metrics.get('decided') or {}).get('command', 0) >= 3
                  and not any('switch this back' in json.dumps(e) for e in observed
                              if e.get('operation') == 'conversation'))

            # AC1 with AC4 (fix round 2): "thanks" is held for the PM's reading, then his "/close" closes the
            # conversation before the PM reads it. The reading settles the held message READ with the one
            # stale_subject:conversation_closed line, and the PM's next run routes a later, unrelated message.
            third, _msg = telegram('a third question, for a short talk')
            run(route(third['proposal_id'], 'new_conversation'))
            third_id = (intake.proposal(third['proposal_id']) or {}).get('conversation')
            third_sent = end_with_reply(third_id, 'Here is the third answer.') if third_id else []
            thanks, thanks_msg = telegram('thanks', reply=third_sent[0] if third_sent else None)
            shut, _msg = telegram('/close', reply=third_sent[0] if third_sent else None)
            count = len(turns(third_id)) if third_id else 0
            mark = last_id()
            record = run(reading(thanks.get('proposal_id'), 'none'))
            lines = bot_lines(olga_chat, mark)
            held = intake.proposal(thanks.get('proposal_id')) or {}
            print('  VELDO-0175 closed before reading:', thanks.get('outcome'), shut.get('outcome'), record.get('state'),
                  record.get('refusal'), held.get('state'), lines)
            check('AC1/closed-before-reading', 'a held reply whose conversation closed before the reading is retired '
                  'READ with one stale_subject:conversation_closed line and no turn [%s %s]'
                  % (record.get('state'), held.get('state')),
                  thanks.get('outcome') == 'reading' and shut.get('outcome') == 'command'
                  and conversations.read(third_id)['status'] == 'closed' and held.get('state') == 'READ'
                  and len(turns(third_id)) == count and len(lines) == 1
                  and lines[0][2] == thanks_msg['message_id'] and 'stale_subject:conversation_closed' in lines[0][1])
            mark = last_id()
            later, _msg = telegram('an unrelated question about invoices')
            record = run(route(later.get('proposal_id'), 'new_conversation'))
            routed = intake.proposal(later.get('proposal_id')) or {}
            check('AC1/closed-before-reading', 'a later unrelated message is routed by the PM\'s next run [%s]'
                  % routed.get('state'),
                  record.get('state') == 'proposed' and routed.get('state') == 'ROUTED'
                  and not any(p.get('state') == 'AWAITING_READING' for p in intake._all(IN.PROPOSAL_KIND)))
            check('AC1/closed-before-reading', 'the line is sent once: no second line to that message',
                  not any(r == thanks_msg['message_id'] for _m, _t, r in bot_lines(olga_chat, mark)))
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for name in ROWS:
            check(name, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        fake_directory.cleanup()
    for name in ROWS:
        failed = [label for label, ok in rows[name] if not ok] or ([] if rows[name] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0175 detail:', name, '; '.join(failed))
        expect('VELDO-0175 ' + name, bool(rows[name]) and not failed)


_v175_routes_suite()
