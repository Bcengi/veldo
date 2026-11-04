"""VELDO-0175 AC1 and AC3: a reply to any message the factory sent in a conversation, or an API message naming it,
continues that conversation; every turn's reply reaches the owner where he wrote, in parts he can reply to.

Run: python3 scripts/selftest.py --suite 131_veldo_0175_conversation_replies

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support) with the owner's
and a second member's Telegram chats, a loopback Bot API stand-in (getUpdates and sendMessage in the platform's
shapes), the production VELDO-0066 Acquirer and VELDO-0065 presentation edge, the production VELDO-0126 intake with
its conversations (control_intake_conversation), API requests the API edge signs with its real key, VELDO-0174's
conversation Line with real receiver subprocesses over fake pinned engines (support/v174_journey.py, the fake's
reply from this suite's scenario), and the production delivery (control_conversation_channel.Replies, the channel's
`replies`). The factory PM's route and reading are applied with the documents a PM run returns
(control_intake.route and read, as the PM cycle applies them); suite 132 runs the PM itself. No real Telegram
service, token, engine, login or network beyond loopback. Writes only temporary fixtures.
"""


def _v175_replies_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import tempfile
    import time
    from types import SimpleNamespace

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Literal anchors: the registered mutation driver substitutes each production copy here, and the fixture's
    # module copy (which intake, the receivers and the delivery run) takes each of them.
    PRODUCTION = {
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
        'control_intake_conversation.py': ROOT / ".veldo" / "control_intake_conversation.py",
        'control_intake_routes.py': ROOT / ".veldo" / "control_intake_routes.py",
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
        'control_conversation_channel.py': ROOT / ".veldo" / "control_conversation_channel.py",
        'control_service_channel.py': ROOT / ".veldo" / "control_service_channel.py",
    }
    ROWS = ('AC1/reply-continues', 'AC1/api-field', 'AC1/foreign-refused', 'AC1/closed-refused', 'AC1/no-route',
            'AC1/observability',
            'AC3/reply-kept', 'AC3/parts-sent', 'AC3/reply-to-the-last-part', 'AC3/status-line',
            'AC3/api-not-sent', 'AC3/channel-pass', 'AC3/observability')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    present = all(Path(p).is_file() for p in PRODUCTION.values())
    if not present:
        for row in ROWS:
            expect('VELDO-0175 ' + row, False)
        return
    H = load('v175r_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v175r_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    F = load('v175r_fakes', ROOT / 'scripts/suites/support/v231_fake_engines.py')
    base = Path(tempfile.mkdtemp(prefix='v175r-', dir=fast_temp()))
    stops, factories = [], []

    # THE FAKE ENGINE: VELDO-0174's handshake and init, then the reply this suite's scenario names for the turn
    # (`words` words, so a long one needs three Telegram messages; a zero-width space in it), or a failed run.
    OWN = "own = {'engine':ENGINE,'tools':tools,"
    BODY = r'''own = {'engine':ENGINE,'cwd':os.getcwd(),'dispatch':os.environ.get('VELDO_DISPATCH_ID'),'argv':args,'packet':packet}
(MARKERS / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
scenario = json.loads((MARKERS / 'scenario.json').read_text()) if (MARKERS / 'scenario.json').exists() else {}
given = packet.get('payload') or {}
conversation, turn = str(given.get('conversation')), given.get('turn')
plan = (scenario.get(conversation) or {}).get(str(turn)) or {}
if ENGINE == 'codex':
    emit({'type':'thread.started','thread_id':'fixture-thread'})
    emit({'type':'turn.started'})
if plan.get('fail'):
    emit({'type':'result','subtype':'error_during_execution','is_error':True,'num_turns':1,'result':'',
          'usage':{'input_tokens':1,'output_tokens':1}})
    sys.exit(3)
words = int(plan.get('words', 4))
reply = ('Turn %s of %s:\u200b ' % (turn, conversation)) + ' '.join('word%05d' % n for n in range(words))
(MARKERS / ('reply-%s-%s.txt' % (conversation, turn))).write_text(reply)
if ENGINE == 'codex':
    emit({'type':'item.completed','item':{'id':'working','type':'agent_message','text':'working on it'}})
    emit({'type':'item.completed','item':{'id':'answer','type':'agent_message','text':reply}})
    emit({'type':'turn.completed','usage':{'input_tokens':12,'cached_input_tokens':0,'output_tokens':3}})
else:
    emit({'type':'rate_limit_event','rate_limit_info':{'status':'allowed','rateLimitType':'five_hour',
          'utilization':.25,'resetsAt':int(time.time())+3600}})
    emit({'type':'assistant','message':{'id':'message-one','type':'message','role':'assistant',
          'content':[{'type':'text','text':'working on it'}],'usage':{'input_tokens':12,'output_tokens':3}}})
    emit({'type':'result','subtype':'success','is_error':False,'num_turns':1,'result':reply,
          'usage':{'input_tokens':12,'output_tokens':3}})
'''

    def fake_source():
        source = J.FAKE
        if source.count(OWN) != 1:
            raise RuntimeError('the VELDO-0174 fake engine moved')
        return source[:source.index(OWN)] + BODY

    try:
        f = F.fixture(ROOT, base, H, load, 'replies', 75, PRODUCTION)
        mods, authority = f['root'] / 'modules', f['authority']
        S, CM, AC = authority.S, authority.CM, authority.AC
        CV = load('v175r_conversation', mods / 'control_conversation.py')
        CS = load('v175r_service', mods / 'control_service.py')
        CS.CV = CV
        IN = load('v175r_intake', mods / 'control_intake.py')
        CC = load('v175r_channel', mods / 'control_conversation_channel.py')
        SC = load('v175r_service_channel', mods / 'control_service_channel.py')
        P = load('v175r_projection', mods / 'control_channel_projection.py')
        V = load('v175r_presentation', mods / 'control_channel_presentation.py')
        EV = load('v175r_attribution', mods / 'control_channel_attribution.py')
        I = load('v175r_inbox', mods / 'control_assignment.py')
        contract = load('v175r_contract', mods / 'entity_contract.py')
        observations = []
        conversations = CV.Conversations(S, authority.conn, domain=authority.ids['domain_uuid'], principal='authority',
                                         signer='authority', sign=authority.journal_sign,
                                         state_root=f['root'] / 'state', observe=observations.append)
        f['conversations'] = conversations
        saved, J.FAKE = J.FAKE, fake_source()
        try:
            receiver, markers, _ = J.engines(ROOT, f, CS)
        finally:
            J.FAKE = saved
        accounts = load('v175r_accounts', mods / 'control_accounts.py').Accounts(
            S, authority.conn, principal='owner', signer='authority', sign=authority.journal_sign)
        for provider in ('claude_code', 'codex'):
            account = 'account-%s-1' % provider
            profile = f['root'] / ('profile-' + account)
            profile.mkdir(parents=True)
            accounts.register('account-register-' + account, account, provider, account, {f['host']: str(profile)},
                              concurrency=1, now=time.time())

        # The loopback Bot API, the owner's chat (the authority's enrollment) and a second member's.
        bot = {'id': 8000000175, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_v175_bot'}
        url, api, stop = H.stand_in({'bot175': bot})
        stops.append(stop)
        owner_chat = 23100 + 75
        owner = {'id': owner_chat, 'is_bot': False, 'first_name': 'Owner'}
        other = {'id': 23999, 'is_bot': False, 'first_name': 'Steward'}
        authority.fixture('channel-enrollment:telegram_chat:steward', 'channel_enrollment',
                          dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='steward',
                               chat_id=other['id'], revoked_at=None))
        authority.fixture('project:factory', 'project', {'name': 'factory', 'owner': 'owner', 'state': 'ACTIVE',
                                                         'ticket_key_prefixes': []})
        inbox = I.Inbox(S, CM, authority.claims, contract, authority.conn, authority.ids, 'authority',
                        authority.journal_sign)
        presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot175'), authority.conn,
                                'authority', authority.journal_sign, assignment=I)
        acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot175'), authority.conn,
                               'authority', authority.journal_sign, 'api-edge',
                               lambda b: authority.sign_as('api-edge', b))
        intake = IN.Intake(S, CM, AC, acquirer, authority.conn, domain=authority.ids['domain_uuid'],
                           projects=['factory'], api_edge='api-edge', journal_signer='authority',
                           sign=authority.journal_sign, asker=presenter.edge, conversations=conversations)
        replies = CC.Replies(S, authority.conn, 'authority', authority.journal_sign, presenter.edge,
                             observe=observations.append)
        bot_messages = api['bots']['bot175']['messages']

        def telegram(sender, text, reply_to=None):
            update = H.deliver(api, 'bot175', sender, text, reply_to)
            acquirer.acquire()
            return intake.receive('telegram_message', EV.evidence_id(bot['id'], update['update_id'])), update

        serial = [0]

        def post(text, who='owner', conversation=None):
            serial[0] += 1
            body = dict(schema=IN.API_SCHEMA, domain=authority.ids['domain_uuid'], request_id='v175-api-%d' % serial[0],
                        edge='api-edge', principal=who, text=text, project=None, clarifies=None)
            if conversation is not None:
                body['conversation'] = conversation
            return intake.receive('api_request', {'request': body,
                                                  'signature': authority.sign_as('api-edge', S.canonical_bytes(body))})

        def sent_to(chat):
            """Every message the bot sent to `chat`, in order: (message id, text, reply to)."""
            return sorted([(m['message_id'], m['text'], (m.get('reply_to_message') or {}).get('message_id'))
                           for (c, _mid), m in bot_messages.items() if c == chat and m['from'].get('is_bot')])

        # The service loop's stand-in (as suite 130): the production FactoryLoop over the conversation receiver.
        service = SimpleNamespace(
            config={'receiver': {'conversations': str(receiver)}, 'journal_key': str(authority.keyfile['authority'])},
            conn=authority.conn, domain=authority.ids['domain_uuid'], principal='authority', generation=1,
            sign=authority.journal_sign, conversations=lambda: conversations, _log=lambda event: None,
            repositories={}, store=authority.ids['store_uuid'],
            watermark=lambda: authority.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0])
        wrapper = f['root'] / 'receiver-driver.py'
        wrapper.write_text('import runpy,sys\nsys.stderr=open(' + repr(str(f['root'] / 'receiver-errors.log'))
                           + ", 'a')\nrunpy.run_path(" + repr(str(mods / 'control_launch.py')) + ",run_name='__main__')\n")
        CS.L.RECEIVER = str(wrapper)
        factory = CS.FactoryLoop(service, None)
        lock = CS.acquire(str(authority.db.parent / 'authority.lock'), {'principal': 'authority'})
        factory.lock = lock
        factories.append((factory, lock))
        factory.start()

        def nth(identity, number):
            """Turn `number` of the conversation, or {} when it has none (a falsifier's run goes on to its rows)."""
            found = conversations.turns(identity) if identity else []
            return found[number - 1] if len(found) >= number else {}

        def settle(identity, count, seconds=60):
            if not identity or len(conversations.turns(identity)) < count:
                return False
            J.pass_(factory)
            done = F.drive(factory, lambda: len(conversations.turns(identity)) >= count
                           and conversations.turns(identity)[count - 1].get('state') == 'ended', seconds)
            return done

        def proposals(state=None):
            return [p for p in intake._all(IN.PROPOSAL_KIND) if state is None or p.get('state') == state]

        def none_reading(pid):
            return intake.read(dict(schema='veldo.conversation_reading/v1', proposal_id=pid, command='none', name=None,
                                    reason='Fixture PM: a follow-up question, no command.'),
                               dispatch='fixture-pm-reading', proposal_id=pid)

        (markers / 'scenario.json').write_text(json.dumps({}))
        # The owner writes on Telegram; the factory PM routes it to a new conversation (the route document).
        first, first_update = telegram(owner, "why did yesterday's Google Ads spend jump?")
        pid = first.get('proposal_id')
        routed = intake.route(dict(schema=IN.RT.SCHEMA, proposal_id=pid, route='new_conversation',
                                   reason='Fixture PM: a question to talk over.'), dispatch='fixture-pm-route',
                              proposal_id=pid) if pid else {}
        talk = routed.get('conversation')
        (markers / 'scenario.json').write_text(json.dumps({talk: {'1': {'words': 1000}, '2': {'words': 6},
                                                                  '3': {'words': 6}, '4': {'words': 6},
                                                                  '5': {'fail': True}}}))
        settled_one = settle(talk, 1) if talk else False
        delivered_one = replies.deliver()
        turn_one = (conversations.turns(talk) or [{}])[0] if talk else {}
        engine_reply = (markers / ('reply-%s-1.txt' % talk)).read_text() if talk and (markers / ('reply-%s-1.txt' % talk)).exists() else None
        parts_one = sent_to(owner_chat)
        print('  VELDO-0175 turn 1:', settled_one, turn_one.get('outcome'), len(parts_one),
              [(d.get('part'), d.get('outcome')) for d in delivered_one])

        # AC3: the reply on the turn record as the engine wrote it, and its parts on Telegram.
        check('AC3/reply-kept', 'the turn record keeps the engine\'s final result text exactly',
              engine_reply is not None and turn_one.get('reply') == engine_reply and turn_one.get('outcome') == 'completed'
              and turn_one.get('reply_digest') == CC.digest(engine_reply))
        check('AC3/reply-kept', 'the final result is the result event, not the earlier assistant text',
              turn_one.get('reply') != 'working on it')
        shown = [text for _mid, text, _to in parts_one]
        # A part a soft cut opened shows the space it begins with escaped, since the platform trims it.
        joined = ''.join(' ' + t[len('<U+0020>'):] if n and t.startswith('<U+0020>') else t for n, t in enumerate(shown))
        check('AC3/parts-sent', 'a reply longer than two Telegram messages is sent as three parts in order [%d]'
              % len(parts_one), len(parts_one) == 3 and all(V.utf16_units(t) <= V.MESSAGE_LIMIT for t in shown))
        check('AC3/parts-sent', 'the first part is a reply to his message, the others are not',
              len(parts_one) == 3 and parts_one[0][2] == first_update['message']['message_id']
              and parts_one[1][2] is None and parts_one[2][2] is None)
        check('AC3/parts-sent', 'the parts show the reply whole, with VELDO-0168\'s escapes (the zero-width space shown)',
              engine_reply is not None and joined == engine_reply.replace('\u200b', '<U+200B>')
              and '<U+200B>' in shown[0])
        recorded = [json.loads(raw) for (raw,) in authority.conn.execute(
            'SELECT data FROM entities WHERE kind=?', (CV.SENT_KIND,))]
        recorded_one = sorted((r['part'], r['message_id']) for r in recorded if r.get('conversation') == talk
                              and r.get('sequence') == 1 and r.get('kind') == 'reply')
        check('AC3/parts-sent', 'every part is recorded with its bot, chat and message id, bound to the turn',
              recorded_one == [(n + 1, mid) for n, (mid, _t, _to) in enumerate(parts_one)]
              and all(r['bot_id'] == bot['id'] and r['chat_id'] == owner_chat for r in recorded if r.get('sequence') == 1)
              and [s.get('message_id') for s in nth(talk, 1).get('sent') or []]
              == [mid for mid, _t, _to in parts_one])
        check('AC3/parts-sent', 'a second pass sends nothing again', replies.deliver() == [] and
              len(sent_to(owner_chat)) == 3)

        # AC1: he replies to the second of the three parts with a follow-up; it continues the conversation.
        before_inbox = len(proposals('AWAITING_ROUTE'))
        follow, follow_update = telegram(owner, 'and what about the day before?', reply_to=parts_one[1][0]
                                         if len(parts_one) > 1 else None)
        reading_pid = follow.get('proposal_id')
        read = none_reading(reading_pid) if follow.get('outcome') == 'reading' else {}
        turns = conversations.turns(talk) if talk else []
        second = turns[1] if len(turns) > 1 else {}
        source = intake._data(second.get('intake_command'), IN.SOURCE_KIND) or {}
        print('  VELDO-0175 AC1 reply:', follow.get('outcome'), follow.get('reason'), read.get('outcome'),
              [t.get('sequence') for t in turns])
        check('AC1/reply-continues', 'a reply to the second of three parts continues that conversation as its next '
              'turn [%s %s]' % (follow.get('outcome'), (intake.proposal(reading_pid) or {}).get('state')),
              follow.get('outcome') == 'reading' and follow.get('conversation') == talk and read.get('outcome') == 'turn'
              and second.get('sequence') == 2 and source.get('text') == 'and what about the day before?'
              and second.get('state') == 'waiting')
        check('AC1/no-route', 'no inbox proposal and no question for it',
              len(proposals('AWAITING_ROUTE')) == before_inbox
              and not any(q.get('proposal_id') == reading_pid for q in intake._all(IN.QUESTION_KIND))
              and (intake.proposal(reading_pid) or {}).get('proposal') == 'reading')
        settle(talk, 2)
        replies.deliver()
        after_two = sent_to(owner_chat)
        check('AC1/reply-continues', 'turn 2 ran and its reply came back as a reply to his follow-up',
              nth(talk, 2).get('outcome') == 'completed' and len(after_two) == 4
              and after_two[3][2] == follow_update['message']['message_id'])

        # AC1: an API message naming the conversation is its next turn at once.
        posted = post('one more thing from the UI', conversation=talk)
        turns = conversations.turns(talk)
        third = turns[2] if len(turns) > 2 else {}
        check('AC1/api-field', 'a message with the conversation field becomes its next turn at intake [%s]'
              % posted.get('outcome'), posted.get('outcome') == 'turn' and posted.get('sequence') == 3
              and third.get('intake_command') == IN.source_key('api_request', 'v175-api-%d' % serial[0])
              and third.get('state') == 'waiting')
        settle(talk, 3)
        delivered_three = replies.deliver()
        check('AC3/api-not-sent', 'an API turn\'s reply is kept on its record and nothing is sent to Telegram',
              (nth(talk, 3).get('reply') or '').startswith('Turn 3 of') and delivered_three == []
              and len(sent_to(owner_chat)) == 4)

        # AC3: a reply to the last part of turn 1 continues the conversation too.
        last, _ = telegram(owner, 'thanks, go on', reply_to=parts_one[2][0] if len(parts_one) > 2 else None)
        last_read = none_reading(last.get('proposal_id')) if last.get('outcome') == 'reading' else {}
        turns = conversations.turns(talk)
        print('  VELDO-0175 AC3 last part:', last.get('outcome'), (intake.proposal(last.get('proposal_id')) or {}).get('state'))
        check('AC3/reply-to-the-last-part', 'a reply to the last part continues the conversation as its next turn '
              '[%s %s]' % (last.get('outcome'), (intake.proposal(last.get('proposal_id')) or {}).get('state')),
              last.get('outcome') == 'reading' and last.get('conversation') == talk
              and last_read.get('outcome') == 'turn' and len(turns) == 4 and turns[3].get('sequence') == 4)
        settle(talk, 4)
        replies.deliver()

        # AC3: a turn that ends with no result text sends one status line, and a reply to it continues too.
        post('this one fails', conversation=talk)
        settle(talk, 5)
        failed_turn = nth(talk, 5)
        before_status = len(sent_to(owner_chat))
        status = replies.deliver()
        print('  VELDO-0175 AC3 status:', failed_turn.get('outcome'), status)
        # An API turn sends nothing: the status row uses a Telegram turn that fails.
        ask, ask_update = telegram(owner, 'try the failing thing', reply_to=parts_one[0][0] if parts_one else None)
        none_reading(ask.get('proposal_id')) if ask.get('outcome') == 'reading' else None
        (markers / 'scenario.json').write_text(json.dumps({talk: {'6': {'fail': True}, '7': {'words': 5}}}))
        settle(talk, 6)
        sixth = nth(talk, 6)
        status = replies.deliver()
        lines = sent_to(owner_chat)[before_status:]
        sixth = nth(talk, 6)
        check('AC3/status-line', 'a turn that ends with no result text sends one status line naming the outcome '
              'and what happens next [%s %s]' % (sixth.get('outcome'), [t for _m, t, _r in lines]),
              sixth.get('state') == 'ended' and sixth.get('outcome') != 'completed' and sixth.get('reply') is None
              and len(lines) == 1 and lines[0][2] == ask_update['message']['message_id']
              and str(sixth.get('outcome')) in lines[0][1] and 'Turn 6' in lines[0][1]
              and [s['kind'] for s in sixth.get('sent') or []] == ['status'])
        again, _ = telegram(owner, 'ok, try again', reply_to=lines[0][0] if lines else None)
        check('AC3/status-line', 'a reply to the status line continues the conversation',
              again.get('outcome') == 'reading' and again.get('conversation') == talk)
        none_reading(again.get('proposal_id')) if again.get('outcome') == 'reading' else None
        check('AC3/status-line', 'a later pass sends no second status line', replies.deliver() == [])

        # AC1: anyone else's reply, and a reply to a closed conversation, is refused by name with one line.
        before_turns = len(conversations.turns(talk))
        # Telegram lets a member reply only in his own chat, so the conversation message he replies to is one the
        # factory sent there: a note bound to the owner's conversation, recorded as every conversation message is.
        note = presenter.edge.send(other['id'], 'A note from conversation %s.' % talk)
        CC.Messages(S, authority.conn, 'authority', authority.journal_sign).record(
            'answer', note, bot=bot['id'], conversation=talk, sequence=1)
        foreign, foreign_update = telegram(other, 'let me add to that', reply_to=note['message_id'])
        to_other = sent_to(other['id'])[1:]
        check('AC1/foreign-refused', 'another member\'s reply is refused missing_authority:conversation_owner with one '
              'line to him and no turn [%s]' % foreign.get('reason'),
              foreign.get('reason') == 'missing_authority:conversation_owner'
              and len(conversations.turns(talk)) == before_turns and len(to_other) == 1
              and to_other[0][2] == foreign_update['message']['message_id']
              and 'missing_authority:conversation_owner' in to_other[0][1])
        foreign_api = post('let me add to that', who='steward', conversation=talk)
        check('AC1/foreign-refused', 'an API message naming his conversation from another member is refused by name',
              foreign_api.get('reason') == 'missing_authority:conversation_owner'
              and len(conversations.turns(talk)) == before_turns)
        intake.take_telegram()
        check('AC1/foreign-refused', 'a redelivered refused message is not answered twice and makes no turn',
              len(sent_to(other['id'])) == 2 and len(conversations.turns(talk)) == before_turns)
        conversations.close(talk, conversations.read(talk)['version'], owner='owner')
        closed, closed_update = telegram(owner, 'one last question', reply_to=parts_one[0][0] if parts_one else None)
        closed_lines = [m for m in sent_to(owner_chat) if m[2] == closed_update['message']['message_id']]
        check('AC1/closed-refused', 'a reply to a closed conversation is refused stale_subject:conversation_closed with '
              'one line and no turn [%s]' % closed.get('reason'),
              closed.get('reason') == 'stale_subject:conversation_closed' and len(closed_lines) == 1
              and 'stale_subject:conversation_closed' in closed_lines[0][1]
              and len(conversations.turns(talk)) == before_turns)
        closed_api = post('one last question', conversation=talk)
        check('AC1/closed-refused', 'an API message naming a closed conversation is refused by name',
              closed_api.get('reason') == 'stale_subject:conversation_closed'
              and len(conversations.turns(talk)) == before_turns)

        # AC3: the channel pass delivers through the same production method (Channel.replies).
        conversations.open('channel', owner='owner', role='assistant', intake_digest='sha256:channel')
        start, start_update = telegram(owner, 'a channel pass question')
        intake.route(dict(schema=IN.RT.SCHEMA, proposal_id=start['proposal_id'], route='open_conversation',
                          conversation='channel', reason='Fixture PM: his open conversation.'),
                     dispatch='fixture-pm-route', proposal_id=start['proposal_id'])
        settle('channel', 1)
        channel = SimpleNamespace(ingress=SimpleNamespace(conn=authority.conn, presenter=presenter), replier=None,
                                  clock=time.time)
        passed = SC.Channel.replies(channel)
        check('AC3/channel-pass', 'the channel\'s pass sends a Telegram turn\'s reply as a reply to his message',
              [p.get('outcome') for p in passed] == ['sent']
              and sent_to(owner_chat)[-1][2] == start_update['message']['message_id']
              and SC.Channel.replies(channel) == [])

        # Observability: how each message was decided and each part sent, with ids, never text.
        events = intake.observations
        decided = [e for e in events if e.get('operation') == 'conversation']
        check('AC1/observability', 'each conversation message is logged with how it was decided, its conversation and '
              'turn sequence or the replied message, never its text',
              any(e.get('decided_by') == 'reply' and e.get('conversation') == talk
                  and e.get('reply_to') == parts_one[1][0] for e in decided if len(parts_one) > 1)
              and any(e.get('decided_by') == 'field' and e.get('sequence') == 3 for e in decided)
              and any(e.get('decided_by') == 'route' and e.get('conversation') == talk for e in decided)
              and not any('what about the day before' in json.dumps(e) for e in decided))
        metrics = intake.metrics().get('conversations') or {}
        print('  VELDO-0175 metrics:', metrics, replies.metrics())
        check('AC1/observability', 'conversation messages are counted by how they were decided, and refusals of a '
              'closed or foreign conversation are counted',
              (metrics.get('decided') or {}).get('reply', 0) >= 3 and (metrics.get('decided') or {}).get('field', 0) >= 2
              and (metrics.get('refused') or {}).get('missing_authority:conversation_owner', 0) >= 2
              and (metrics.get('refused') or {}).get('stale_subject:conversation_closed', 0) >= 2)
        sent_events = [o for o in observations if o.get('operation') == 'conversation_reply' and o.get('outcome') == 'sent']
        check('AC3/observability', 'each reply part sent is logged with its chat, message id and turn, never its text',
              len([o for o in sent_events if o.get('conversation') == talk and o.get('sequence') == 1]) == 3
              and all(o.get('turn') == CV.turn_id(talk, o['sequence']) and type(o.get('message_id')) is int
                      and o.get('chat_id') == owner_chat for o in sent_events)
              and not any('word00001' in json.dumps(o) for o in observations))
        check('AC3/observability', 'reply parts sent are counted',
              replies.metrics().get('parts_sent', 0) >= 5 and replies.metrics().get('status_sent', 0) >= 1)
        continued = [e for e in decided if e.get('reply_to') is not None]
        check('AC1/observability', 'each continuing message is joined to the sent message it replied to',
              {e['reply_to'] for e in continued} >= {parts_one[1][0], parts_one[2][0]} if len(parts_one) > 2 else False)
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in ROWS:
            check(row, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        for factory_value, lock_value in factories:
            try:
                for launch in list(factory_value.conversation.runner.launches.values()):
                    launch.stop('requested')
            except Exception:  # noqa: BLE001
                pass
            close = getattr(lock_value, 'close', None)
            if close:
                close()
            elif isinstance(lock_value, int):
                try:
                    os.close(lock_value)
                except OSError:
                    pass
        for stop in stops:
            stop()
        try:
            f['authority'].conn.close()
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(base, ignore_errors=True)
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0175 detail:', row, '; '.join(failed))
        expect('VELDO-0175 ' + row, bool(rows[row]) and not failed)


_v175_replies_suite()
