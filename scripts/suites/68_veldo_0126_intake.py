"""VELDO-0126: one intake for Telegram messages and authenticated API requests, which only ever proposes.

Only shared ROOT and expect are consumed. One temporary tree holds an installed .veldo copy; the
production anchor below is the registered mutation driver's seam, so a mutation of the intake module
reaches every reader. The store is the real SQLite authority with OpenSSH journal signatures. Telegram
messages reach the intake the way VELDO-0066 acquires them: a loopback Bot API endpoint over real HTTP
(getMe, getUpdates, sendMessage in the platform's documented shapes, as suite 63 serves them), the
production TelegramAcquisitionEdge and Acquirer, and the VELDO-0065 presentation edge for the question
sent back. No real Telegram service or token is used. The API leg drives the intake interface the
authenticated API (VELDO-0130, not built yet) will call, with requests the API edge principal signs
with its real OpenSSH key from the store's keyring; VELDO-0130 drives its own leg over its server. A
second loopback endpoint stands for the Jira host a message links to and records every request.
When the intake module is absent (the pre-change tree, for the red record) a stand-in that takes
nothing is used, so every row fails by its own assertions rather than by an exception.
"""


def _v126_suite():
    import contextlib
    import copy
    import http.server
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import threading
    import time

    # Literal anchor: the registered mutation driver substitutes the production copy here.
    PRODUCTION = {'control_intake.py': ROOT / ".veldo" / "control_intake.py"}
    PREFIX = 'VELDO-0126 '

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    observed, emitted, raised, regions = {}, set(), [], []

    def check(label, parts):
        """One row: every named part must hold. A part that raises while judging is a failed part."""
        emitted.add(label)
        failed = []
        for name, condition in parts:
            try:
                ok = bool(condition() if callable(condition) else condition)
            except Exception as error:  # noqa: BLE001 - a malformed answer is a failed part, never a raise
                ok = False
                name = '%s (%s)' % (name, type(error).__name__)
            if not ok:
                failed.append(name)
        if failed:
            print('  %sdetail: %s: %s' % (PREFIX, label, '; '.join(failed)))
        observed.setdefault('failed_parts', {})[label] = failed
        expect(PREFIX + label, not failed)

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            print('  %sdetail: %s did not run to its end: %r' % (PREFIX, labels[0], error))
            for label in labels:
                if label not in emitted:
                    check(label, [('region raised', False)])

    class BotApi(http.server.BaseHTTPRequestHandler):
        """getMe, getUpdates and sendMessage for one bot, per the Bot API's documented shapes."""
        state = None

        def log_message(self, *args):
            pass

        def do_POST(self):
            st = self.state
            raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
            body = json.loads(raw) if raw else {}
            _, _, rest = self.path.partition('/bot')
            token, _, method = rest.partition('/')
            if token != st['token']:
                return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
            st['calls'].append((method, body))
            if method == 'getMe':
                return self._answer(200, {'ok': True, 'result': dict(st['bot'], can_join_groups=True,
                                                                     can_read_all_group_messages=False,
                                                                     supports_inline_queries=False)})
            if method == 'getUpdates':
                offset = body.get('offset') or 0
                if offset:
                    st['updates'] = [u for u in st['updates'] if u['update_id'] >= offset]
                return self._answer(200, {'ok': True, 'result': st['updates'][:body.get('limit') or 100]})
            if method == 'sendMessage':
                chat = st['chats'].get(body.get('chat_id'))
                if chat is None:
                    return self._answer(400, {'ok': False, 'error_code': 400, 'description': 'Bad Request: chat not found'})
                reply = (body.get('reply_parameters') or {}).get('message_id')
                message = st['message'](st['bot'], chat, body['text'], reply)
                return self._answer(200, {'ok': True, 'result': message})
            return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

        def _answer(self, code, value):
            payload = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    class TicketHost(http.server.BaseHTTPRequestHandler):
        """Stands for the Jira host a message links to: records every request, answers nothing useful."""
        hits = None

        def log_message(self, *args):
            pass

        def _any(self):
            self.hits.append((self.command, self.path))
            self.send_response(404)
            self.send_header('Content-Length', '0')
            self.end_headers()

        do_GET = do_POST = do_HEAD = _any

    class Absent:
        """The pre-change tree has no intake: nothing takes a message, so every request is refused."""
        observations = []

        def receive(self, source_kind, payload):
            return {'outcome': 'refused', 'reason': 'unsupported_source'}

        def take_telegram(self):
            return []

        def proposal(self, pid):
            return None

        question = proposal

        def source(self, kind, source_id):
            return None

        def metrics(self):
            return {}

    servers = []
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v126-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        present = PRODUCTION['control_intake.py'].is_file()
        if present:
            shutil.copyfile(PRODUCTION['control_intake.py'], mods / 'control_intake.py')
        conn = None
        try:
            with region('install/assets'):
                rel = '.veldo/control_intake.py'
                scaffold = load('v126_scaffold', ROOT / '.veldo' / 'init_scaffold.py')
                here = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
                laid = base / 'laid' / rel
                if here:
                    scaffold._lay(ROOT / 'engine' / rel, laid, rel, [], [])
                check('install/assets', [
                    ('installed by the scaffold', rel in scaffold._FILES),
                    ('not validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE),
                    ('engine copy identical', here and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                    ('laid by the installer', here and laid.is_file() and laid.read_bytes() == (ROOT / rel).read_bytes())])

            claims = load('v126_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            contract = load('v126_contract', mods / 'entity_contract.py')
            INBOX = load('v126_inbox', mods / 'control_assignment.py')
            P = load('v126_projection', mods / 'control_channel_projection.py')
            V = load('v126_presentation', mods / 'control_channel_presentation.py')
            A = load('v126_attribution', mods / 'control_channel_attribution.py')
            IN = load('v126_intake', mods / 'control_intake.py') if present else None

            keys = base / 'keys'
            keys.mkdir(mode=0o700)
            public = {}
            names = ('authority', 'pm', 'owner', 'multi', 'colleague', 'retired', 'telegram-edge', 'api-edge', 'late')
            for who in names:
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v126-' + who, '-f', str(keys / who)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                public[who] = (keys / (who + '.pub')).read_text().strip()

            def sign_as(who, message, namespace=AC.SIGNATURE_NAMESPACE):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                                      capture_output=True, check=True, timeout=20).stdout.decode()

            def journal_sign(message):
                return sign_as('authority', message, 'veldo-journal')

            DOMAIN, PROJECTS = 'intake-domain', ('project-a', 'project-b')
            ids = dict(domain_uuid=DOMAIN, repository_uuid='project-a', store_uuid='intake-store')
            conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
            serial = [0]

            def fixture(eid, kind, data):
                serial[0] += 1
                current = S.materialized_state(conn)['entities']
                S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority', operation='upsert_entity',
                                     parameters=dict(entity_id=eid, kind=kind, data=data),
                                     expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                     nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

            members = {'owner': ('person', ['project-a'], None), 'multi': ('person', ['project-a', 'project-b'], None),
                       'colleague': ('person', ['project-a'], None), 'retired': ('person', ['project-a'], 1.0),
                       'pm': ('service', ['project-a'], None), 'telegram-edge': ('service', ['project-a'], None),
                       'api-edge': ('service', ['*'], None)}
            for who, (kind, scope, revoked) in members.items():
                fixture(who, 'membership', dict(principal_type=kind, roles=['project_owner'] if kind == 'person' else [],
                                                scope=scope, revoked_at=revoked, expires_at=None))
                if who != 'telegram-edge':
                    fixture('key-' + who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
            fixture(AC.CHANNELS['telegram_chat']['edge_key_id'], 'verification_key',
                    dict(principal='telegram-edge', public_key=public['telegram-edge'], effective_at=0))
            chats = {'owner': 6260001, 'multi': 6260002, 'colleague': 6260003}
            for who, chat in chats.items():
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))
            fixture_kinds = {k for (k,) in conn.execute('SELECT DISTINCT kind FROM entities')}

            def user(uid, first, last=None):
                found = {'id': uid, 'is_bot': False, 'first_name': first, 'language_code': 'en'}
                if last:
                    found['last_name'] = last
                return found

            owner_user = user(chats['owner'], 'Owner', 'Example')
            multi_user = user(chats['multi'], 'Multi')
            colleague_user = user(chats['colleague'], 'Colleague')
            stranger_user = user(6260099, 'Owner', 'Example')  # an unenrolled account copying the owner's name
            late_user = user(6260004, 'Late')  # writes before being a member, is enrolled afterwards
            api = {'token': 'intake-bot', 'bot': {'id': 8126000001, 'is_bot': True, 'first_name': 'Veldo',
                                                   'username': 'veldo_intake_bot'},
                   'calls': [], 'updates': [], 'messages': {}, 'next': 7000, 'update_next': 400000000, 'tick': 0,
                   'chats': {}}
            for person in (owner_user, multi_user, colleague_user, stranger_user, late_user):
                api['chats'][person['id']] = {'id': person['id'], 'type': 'private', 'first_name': person['first_name']}

            def message(sender, chat, text, reply_to=None, **extra):
                api['next'] += 1
                api['tick'] += 1
                held = {'message_id': api['next'], 'from': dict(sender), 'chat': dict(chat),
                        'date': 1790100000 + api['tick'], 'text': text}
                if reply_to is not None and (chat['id'], reply_to) in api['messages']:
                    replied = api['messages'][(chat['id'], reply_to)]
                    held['reply_to_message'] = copy.deepcopy({k: v for k, v in replied.items() if k != 'reply_to_message'})
                held.update(extra)
                api['messages'][(chat['id'], held['message_id'])] = held
                return held

            api['message'] = message

            def say(sender, text, reply_to=None, **extra):
                held = message(sender, api['chats'][sender['id']], text, reply_to, **extra)
                api['update_next'] += 1
                api['updates'].append({'update_id': api['update_next'], 'message': held})
                return held

            def edit(held, text):
                changed = dict(copy.deepcopy(held), text=text, edit_date=held['date'] + 5)
                api['update_next'] += 1
                api['updates'].append({'update_id': api['update_next'], 'edited_message': changed})

            handler = type('V126BotApi', (BotApi,), {'state': api})
            bot_server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            ticket_hits = []
            ticket_server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), type('V126Ticket', (TicketHost,),
                                                                                  {'hits': ticket_hits}))
            for server in (bot_server, ticket_server):
                servers.append(server)
                threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % bot_server.server_address[1]
            ticket_url = 'http://127.0.0.1:%d/browse/OPS-142' % ticket_server.server_address[1]

            inbox = INBOX.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, api['token']), conn, 'authority',
                                    journal_sign, assignment=INBOX)
            acquirer = A.Acquirer(S, CM, P, V, presenter, A.TelegramAcquisitionEdge(P, url, api['token']), conn,
                                  'authority', journal_sign, 'telegram-edge', lambda m: sign_as('telegram-edge', m))
            events = []
            if IN is not None:
                intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=PROJECTS, api_edge='api-edge',
                                   journal_signer='authority', sign=journal_sign,
                                   asker=V.TelegramPresentationEdge(P, url, api['token']), observe=events.append)
            else:
                intake = Absent()
            INTAKE_KINDS = {'intake_source', 'intake_proposal', 'intake_question'}
            counter = [0]

            def request(principal, text, request_id=None, project=None, clarifies=None, edge='api-edge', domain=DOMAIN):
                counter[0] += 1
                return {'schema': 'veldo.intake_api_request/v1', 'domain': domain,
                        'request_id': request_id or 'req-%d' % counter[0], 'edge': edge, 'principal': principal,
                        'text': text, 'project': project, 'clarifies': clarifies}

            def packet(body, signer='api-edge'):
                return {'request': body, 'signature': sign_as(signer, S.canonical_bytes(body))}

            def via_api(principal, text, **fields):
                return intake.receive('api_request', packet(request(principal, text, **fields)))

            taken = {}

            def pump():
                """One acquisition by the production Acquirer, then intake of what it kept; each result is
                indexed by the platform message it came from."""
                acquirer.acquire()
                results = intake.take_telegram()
                for r in results:
                    kept = acquirer.evidence(r.get('evidence_id') or '')
                    if kept is not None:
                        taken[kept['fields']['message_id']] = r
                return results

            def telegram(sender, text, reply_to=None, **extra):
                held = say(sender, text, reply_to, **extra)
                results = pump()
                return taken.get(held['message_id']) or {'outcome': 'missing', 'all': results}, held

            def proposal_of(result):
                return intake.proposal((result or {}).get('proposal_id'))

            def seq():
                """How many journal records intake commands wrote (acquisition writes its own)."""
                return conn.execute("SELECT COUNT(*) FROM journal WHERE command_id LIKE 'intake%'").fetchone()[0]

            def intake_rows():
                return conn.execute('SELECT COUNT(*) FROM entities WHERE kind IN (?,?,?)',
                                    tuple(sorted(INTAKE_KINDS))).fetchone()[0]

            def same_shape(p, q):
                keys = ('proposal', 'state', 'project', 'principal', 'text', 'domain')
                return p is not None and q is not None and all(p.get(k) == q.get(k) for k in keys)

            # AC1: one Telegram message and one API request with equal text through the one service.
            with region('intake/common-command'):
                t1 = 'Add a weekly spend summary to the owner dashboard.'
                r_t, m_t = telegram(owner_user, t1)
                r_a = via_api('owner', t1, request_id='req-common')
                p_t, p_a = proposal_of(r_t), proposal_of(r_a)
                c_t, c_a = r_t.get('command') or {}, r_a.get('command') or {}
                s_t = intake.source('telegram_message', '%d:%d:%d' % (api['bot']['id'], chats['owner'], m_t['message_id']))
                s_a = intake.source('api_request', 'req-common')
                submits = [e for e in events if e.get('operation') == 'submit' and e.get('outcome') == 'proposed']
                observed['common'] = {'telegram': r_t.get('outcome'), 'api': r_a.get('outcome')}
                check('intake/common-command', [
                    ('two allowed source kinds', getattr(IN, 'SOURCE_KINDS', None) == ('telegram_message', 'api_request')),
                    ('telegram proposed', r_t.get('outcome') == 'proposed'),
                    ('api proposed', r_a.get('outcome') == 'proposed'),
                    ('one normalized command shape', c_t and set(c_t) == set(c_a) and c_t.get('schema') == c_a.get('schema')),
                    ('same text, principal and context', all(c.get('text') == t1 and c.get('principal') == 'owner'
                                                            and c.get('project') is None for c in (c_t, c_a))),
                    ('source identities', c_t.get('source_id') == '%d:%d:%d' % (api['bot']['id'], chats['owner'],
                                                                                m_t['message_id'])
                     and c_a.get('source_id') == 'req-common'),
                    ('telegram provenance', (c_t.get('provenance') or {}).get('message_id') == m_t['message_id']
                     and acquirer.evidence((c_t.get('provenance') or {}).get('evidence_id') or '') is not None),
                    ('api provenance', (c_a.get('provenance') or {}).get('request_id') == 'req-common'),
                    ('equal proposals', same_shape(p_t, p_a) and p_t.get('proposal') == 'objective'
                     and p_t.get('state') == 'PROPOSED' and p_t.get('project') == 'project-a'),
                    ('distinct proposals per source', p_t and p_a and p_t['proposal_id'] != p_a['proposal_id']),
                    ('sources retained', s_t and s_a and s_t.get('text') == t1 and s_a.get('text') == t1
                     and s_t.get('principal') == s_a.get('principal') == 'owner'
                     and (s_t.get('context') or {}).get('candidates') == ['project-a']
                     and s_t.get('proposal_id') == r_t.get('proposal_id') and s_a.get('proposal_id') == r_a.get('proposal_id')),
                    ('both through the one store command', {e.get('source_kind') for e in submits}
                     == {'telegram_message', 'api_request'} and [sorted({v.get('kind') for v in json.loads(t).values()})
                                                                 for (t,) in conn.execute(
                         "SELECT transition FROM journal WHERE command_id LIKE 'intake%' ORDER BY seq")]
                     == [['intake_proposal', 'intake_source']] * 2),
                ])

            # AC1: an owner with two projects is asked, never assigned one.
            with region('intake/unresolved-project-asks'):
                t2 = 'Improve the onboarding flow for new travelers.'
                sends = len([c for c in api['calls'] if c[0] == 'sendMessage'])
                r_mt, m_mt = telegram(multi_user, t2)
                r_ma = via_api('multi', t2, request_id='req-multi')
                p_mt, p_ma = proposal_of(r_mt), proposal_of(r_ma)
                q_mt, q_ma = intake.question((p_mt or {}).get('question_id')), intake.question((p_ma or {}).get('question_id'))
                sent = [c for c in api['calls'] if c[0] == 'sendMessage'][sends:]
                delivered = (q_mt or {}).get('delivery') or {}
                observed['unresolved'] = {'telegram': r_mt.get('outcome'), 'api': r_ma.get('outcome'), 'sent': len(sent)}
                check('intake/unresolved-project-asks', [
                    ('telegram inbox', r_mt.get('outcome') == 'inbox'),
                    ('api inbox', r_ma.get('outcome') == 'inbox'),
                    ('no project invented', all(p and p.get('project') is None and p.get('state') == 'AWAITING_PROJECT'
                                                and p.get('proposal') == 'inbox' and p.get('text') == t2 for p in (p_mt, p_ma))),
                    ('questions open with every candidate', all(q and q.get('state') == 'open'
                                                                and q.get('candidates') == ['project-a', 'project-b']
                                                                and q.get('principal') == 'multi' for q in (q_mt, q_ma))),
                    ('telegram question sent as a reply', len(sent) == 1 and sent[0][1].get('chat_id') == chats['multi']
                     and (sent[0][1].get('reply_parameters') or {}).get('message_id') == m_mt['message_id']
                     and sent[0][1].get('text') == (q_mt or {}).get('prompt')),
                    ('telegram delivery recorded', delivered.get('channel') == 'telegram_chat'
                     and delivered.get('chat_id') == chats['multi'] and type(delivered.get('message_id')) is int),
                    ('api question answered in the response', (r_ma.get('question') or {}).get('candidates')
                     == ['project-a', 'project-b'] and ((q_ma or {}).get('delivery') or {}).get('request_id') == 'req-multi'),
                    ('no objective for the unresolved owner', not [p for p in (json.loads(t) for (t,) in conn.execute(
                        "SELECT data FROM entities WHERE kind='intake_proposal'"))
                        if p.get('principal') == 'multi' and p.get('state') != 'AWAITING_PROJECT']),
                ])

            # AC2: prose, a ticket link and incomplete intent, through both sources, kept as written.
            with region('intake/plain-objective'):
                texts = {'prose': '  Plan the fall launch for the travel app.\nKeep the scope small.  ',
                         'ticket link': 'Please look at %s and tell me what it needs.' % ticket_url,
                         'incomplete': 'the thing from yesterday, not sure yet'}
                results = {}
                for name, text in texts.items():
                    results[(name, 'telegram')] = telegram(owner_user, text)[0]
                    results[(name, 'api')] = via_api('owner', text)
                kinds_now = {k for (k,) in conn.execute('SELECT DISTINCT kind FROM entities')}
                observed['plain'] = {'%s/%s' % k: v.get('outcome') for k, v in results.items()}
                parts = []
                for (name, leg), result in results.items():
                    text, prop = texts[name], proposal_of(result)
                    src = intake.source(((result.get('command') or {}).get('source_kind') or ''),
                                        (result.get('command') or {}).get('source_id') or '')
                    parts += [('%s via %s proposed' % (name, leg), result.get('outcome') == 'proposed'),
                              ('%s via %s text exact' % (name, leg), prop and prop.get('text') == text
                               and src and src.get('text') == text and (result.get('command') or {}).get('text') == text)]
                check('intake/plain-objective', parts + [
                    ('no ticket id needed', not any(ch.isdigit() for ch in texts['prose'] + texts['incomplete'])),
                    ('the ticket host was never contacted', ticket_hits == []),
                    ('nothing watches the ticket', kinds_now <= fixture_kinds | INTAKE_KINDS | {
                        'channel_evidence', 'channel_acquisition_cursor', 'authority_versions'}),
                ])

            # AC2: follow-ups clarify, and resolve an inbox proposal only by naming a candidate.
            with region('intake/follow-up-clarification'):
                q_message = ((q_mt or {}).get('delivery') or {}).get('message_id')
                r_ft, m_ft = telegram(multi_user, 'project-b please', reply_to=q_message)
                r_fa = via_api('multi', 'This one is for project-a.', clarifies=(r_ma or {}).get('proposal_id'))
                # After the project is answered, a follow-up to the original message (Telegram) or naming the
                # inbox proposal (API) belongs to the live objective, not to the retired inbox record.
                r_lt, _ = telegram(multi_user, 'Also add a checklist', reply_to=m_mt['message_id'])
                r_la = via_api('multi', 'Also add a checklist', clarifies=(r_ma or {}).get('proposal_id'))
                r_ct, _ = telegram(owner_user, 'Also include refunds.', reply_to=m_t['message_id'])
                r_ca = via_api('owner', 'and keep it weekly', clarifies=(r_a or {}).get('proposal_id'))
                r_open = via_api('multi', 'Tidy up the release notes.', request_id='req-open')
                r_vague = via_api('multi', 'not sure yet', clarifies=(r_open or {}).get('proposal_id'))
                f_t, f_a = proposal_of(r_ft), proposal_of(r_fa)
                p_mt2, p_ma2, p_t2, p_a2 = (intake.proposal((p or {}).get('proposal_id')) for p in (p_mt, p_ma, p_t, p_a))
                open_p = proposal_of(r_open)
                observed['follow_up'] = {k: v.get('outcome') for k, v in (('tg', r_ft), ('api', r_fa), ('tg-clar', r_ct),
                                                                          ('api-clar', r_ca), ('vague', r_vague),
                                                                          ('tg-after', r_lt), ('api-after', r_la))}

                def said(p):
                    return [c.get('text') for c in (p or {}).get('clarifications', [])]
                check('intake/follow-up-clarification', [
                    ('telegram reply to the question resolves', r_ft.get('outcome') == 'resolved' and f_t
                     and f_t.get('project') == 'project-b' and f_t.get('text') == t2 and f_t.get('state') == 'PROPOSED'
                     and f_t.get('resolves') == (p_mt or {}).get('proposal_id')),
                    ('api follow-up resolves', r_fa.get('outcome') == 'resolved' and f_a and f_a.get('project') == 'project-a'
                     and f_a.get('text') == t2 and f_a.get('resolves') == (p_ma or {}).get('proposal_id')),
                    ('follow-up text kept', f_t and {'source': (r_ft.get('source')), 'text': 'project-b please'}
                     in f_t.get('clarifications', []) and f_a and 'This one is for project-a.'
                     in [c.get('text') for c in f_a.get('clarifications', [])]),
                    ('inbox proposals resolved', all(p and p.get('state') == 'RESOLVED' and p.get('text') == t2
                                                     for p in (p_mt2, p_ma2))
                     and (intake.question((p_mt or {}).get('question_id')) or {}).get('state') == 'answered'),
                    ('clarifications on objectives kept', r_ct.get('outcome') == 'clarification'
                     and r_ca.get('outcome') == 'clarification' and p_t2 and p_t2.get('text') == t1
                     and [c.get('text') for c in p_t2.get('clarifications', [])] == ['Also include refunds.']
                     and p_a2 and [c.get('text') for c in p_a2.get('clarifications', [])] == ['and keep it weekly']),
                    ('a vague follow-up keeps the question open', r_vague.get('outcome') == 'clarification'
                     and (intake.question((open_p or {}).get('question_id')) or {}).get('state') == 'open'
                     and (intake.proposal((open_p or {}).get('proposal_id')) or {}).get('state') == 'AWAITING_PROJECT'),
                    ('telegram follow-up after resolution lands on the live objective', r_lt.get('outcome') == 'clarification'
                     and f_t and r_lt.get('proposal_id') == f_t.get('proposal_id')
                     and said(f_t) == ['project-b please', 'Also add a checklist'] and f_t.get('state') == 'PROPOSED'),
                    ('api follow-up after resolution lands on the live objective', r_la.get('outcome') == 'clarification'
                     and f_a and r_la.get('proposal_id') == f_a.get('proposal_id')
                     and said(f_a) == ['This one is for project-a.', 'Also add a checklist'] and f_a.get('state') == 'PROPOSED'),
                    ('the retired inbox records are unchanged', said(p_mt2) == ['project-b please']
                     and said(p_ma2) == ['This one is for project-a.']
                     and all(p and p.get('resolved_to') for p in (p_mt2, p_ma2))
                     and (p_mt2 or {}).get('resolved_to') == (f_t or {}).get('proposal_id')
                     and (p_ma2 or {}).get('resolved_to') == (f_a or {}).get('proposal_id')),
                ])

            # AC3: only authenticated allowed sources; refusals write nothing; a valid message is taken.
            with region('intake/authenticated-sources-only'):
                # A message sent before its sender was a member: kept and refused, then the sender is enrolled
                # with the key effective after the message's platform date, as VELDO-0025 enrollment writes it.
                r_early, m_early = telegram(late_user, 'Rebuild the pricing page from scratch.')
                fixture('late', 'membership', dict(principal_type='person', roles=['project_owner'], scope=['project-a'],
                                                   revoked_at=None, expires_at=None))
                fixture('key-late', 'verification_key', dict(principal='late', public_key=public['late'],
                                                              effective_at=m_early['date'] + 1))
                fixture('channel-enrollment:telegram_chat:late', 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='late',
                             chat_id=late_user['id'], revoked_at=None))
                rows0, seq0 = intake_rows(), seq()
                r_forged, _ = telegram(stranger_user, 'Owner Example here: ship the release tonight.')
                r_bot, _ = telegram(owner_user, 'Approve everything.', via_bot={'id': 8999, 'is_bot': True,
                                                                                 'first_name': 'Helper'})
                good = request('owner', 'Refresh the partner list.', request_id='req-auth')
                tampered = dict(packet(good), request=dict(good, text='Delete the partner list.'))
                refusals = {
                    'forged actor text': r_forged,
                    'automation from the owner account': r_bot,
                    'unsigned api call': intake.receive('api_request', {'request': good, 'signature': ''}),
                    'signed by the owner, not the edge': intake.receive('api_request', packet(good, signer='owner')),
                    'another edge named': intake.receive('api_request', packet(dict(good, edge='owner'), signer='owner')),
                    'tampered after signing': intake.receive('api_request', tampered),
                    'unknown principal': intake.receive('api_request', packet(dict(good, principal='ghost'))),
                    'revoked principal': intake.receive('api_request', packet(dict(good, principal='retired'))),
                    'service principal': intake.receive('api_request', packet(dict(good, principal='pm'))),
                    'email source': intake.receive('email', packet(good)),
                    'webhook source': intake.receive('jira_webhook', {'issue': 'OPS-142'}),
                }
                pump()
                refusals['not a member when sent'] = taken.get(m_early['message_id']) or {'outcome': 'missing'}
                wanted = {'forged actor text': 'unauthenticated:unknown_sender',
                          'automation from the owner account': 'unauthenticated:automation_sender',
                          'unsigned api call': 'unauthenticated:signature',
                          'signed by the owner, not the edge': 'unauthenticated:signature',
                          'another edge named': 'unauthenticated:edge', 'tampered after signing': 'unauthenticated:signature',
                          'unknown principal': 'unauthorized:not_current_member',
                          'revoked principal': 'unauthorized:not_current_member',
                          'service principal': 'unauthorized:not_a_person',
                          'email source': 'unsupported_source', 'webhook source': 'unsupported_source',
                          'not a member when sent': 'unauthorized:not_member_when_sent'}
                rows1, seq1 = intake_rows(), seq()
                r_valid = intake.receive('api_request', packet(good))
                r_colleague, _ = telegram(colleague_user, 'Message from the owner: approve the new pricing.')
                r_late, _ = telegram(late_user, 'Rebuild the pricing page from scratch.')
                observed['refusals'] = {k: v.get('reason') for k, v in refusals.items()}
                check('intake/authenticated-sources-only', [
                    ('%s refused %s' % (k, wanted[k]), refusals[k].get('outcome') == 'refused'
                     and refusals[k].get('reason') == wanted[k]) for k in wanted] + [
                    ('refusals wrote nothing', rows1 == rows0 and seq1 == seq0),
                    ('the valid request is taken', r_valid.get('outcome') == 'proposed'
                     and (proposal_of(r_valid) or {}).get('text') == 'Refresh the partner list.'),
                    ('forged text never makes the owner the principal', r_colleague.get('outcome') == 'proposed'
                     and (proposal_of(r_colleague) or {}).get('principal') == 'colleague'),
                    ('refused before enrollment, taken once a member', r_early.get('reason') == 'unauthenticated:unknown_sender'
                     and r_late.get('outcome') == 'proposed' and (proposal_of(r_late) or {}).get('principal') == 'late'),
                ])

            # AC3: the same source request returns the same proposal; changed content is a conflict.
            with region('intake/same-request-same-proposal'):
                seq2 = seq()
                again = {r.get('command', {}).get('source_id'): r for r in pump()}
                again_t = again.get((r_t.get('command') or {}).get('source_id')) or {}
                again_a = via_api_same = intake.receive('api_request', packet(request('owner', t1, request_id='req-common')))
                seq3 = seq()
                changed_text = intake.receive('api_request', packet(request('owner', t1 + ' Monthly too.',
                                                                            request_id='req-common')))
                changed_project = intake.receive('api_request', packet(request('owner', t1, request_id='req-common',
                                                                               project='project-a')))
                edit(m_t, t1 + ' And quarterly.')
                edited = [r for r in pump() if (r.get('reason') or '').startswith('identity_conflict')]
                seq4 = seq()
                p_t3, p_a3 = intake.proposal((p_t or {}).get('proposal_id')), intake.proposal((p_a or {}).get('proposal_id'))
                s_a3 = intake.source('api_request', 'req-common')
                observed['identity'] = {'again_t': again_t.get('outcome'), 'again_a': again_a.get('outcome'),
                                        'changed': changed_text.get('reason'), 'edited': [r.get('reason') for r in edited]}
                check('intake/same-request-same-proposal', [
                    ('telegram repeat returns the same proposal', again_t.get('repeated') is True
                     and again_t.get('proposal_id') == r_t.get('proposal_id')),
                    ('api repeat returns the same proposal', via_api_same.get('repeated') is True
                     and via_api_same.get('proposal_id') == r_a.get('proposal_id')),
                    ('repeats wrote nothing', seq3 == seq2),
                    ('changed text refused', changed_text.get('reason') == 'identity_conflict'),
                    ('changed project refused', changed_project.get('reason') == 'identity_conflict'),
                    ('an edit refused', len(edited) == 1 and edited[0].get('reason') == 'identity_conflict:edited_message'),
                    ('conflicts wrote nothing', seq4 == seq3),
                    ('the records are unchanged', p_t3 and p_t3.get('text') == t1 and p_a3 and p_a3.get('text') == t1
                     and s_a3 and s_a3.get('text') == t1 and (s_a3.get('command') or {}).get('project') is None),
                ])

            # AC3: intake admits and prioritizes nothing.
            with region('intake/no-admission'):
                kinds = {k for (k,) in conn.execute('SELECT DISTINCT kind FROM entities')}
                proposals = [json.loads(t) for (t,) in conn.execute("SELECT data FROM entities WHERE kind='intake_proposal'")]
                touched = set()
                for (t,) in conn.execute("SELECT transition FROM journal WHERE command_id LIKE 'intake%'"):
                    touched |= {v.get('kind') for v in json.loads(t).values()}
                fields = {'schema', 'proposal_id', 'proposal', 'state', 'domain', 'project', 'principal', 'text', 'sources',
                          'clarifications', 'question_id', 'resolves', 'resolved_to'}
                observed['admission'] = {'kinds': sorted(kinds), 'touched': sorted(touched), 'proposals': len(proposals)}
                check('intake/no-admission', [
                    ('proposals were made', len(proposals) >= 10),
                    ('no unit, backlog item, admission, priority or claim', not kinds & {
                        'execution_unit', 'unit', 'backlog_item', 'admission', 'priority', 'claim', 'assignment'}),
                    ('intake writes only intake records', touched == INTAKE_KINDS),
                    ('only proposal states', {p.get('state') for p in proposals} <= {'PROPOSED', 'AWAITING_PROJECT', 'RESOLVED'}),
                    ('no priority or admission field', all(set(p) == fields for p in proposals)),
                    ('no reservation or effect', conn.execute('SELECT COUNT(*) FROM reservations').fetchone()[0] == 0
                     and conn.execute('SELECT COUNT(*) FROM effects').fetchone()[0] == 0),
                ])

            with region('intake/observations'):
                classes = {'unauthenticated', 'unauthorized', 'stale_version', 'unsupported_configuration',
                           'unavailable_service', 'missing_evidence', 'unknown_outcome'}
                metrics = intake.metrics()
                proposals = [json.loads(t) for (t,) in conn.execute("SELECT data FROM entities WHERE kind='intake_proposal'")]
                text = json.dumps(events, default=str)
                submits = [e for e in events if e.get('operation') == 'submit' and e.get('refusal') is None]
                check('intake/observations', [
                    ('events', len(events) > 20),
                    ('every event names operation, domain and outcome', all(e.get('operation') and e.get('domain') == DOMAIN
                                                                           and e.get('outcome') for e in events)),
                    ('refusals carry a class', all(e.get('taxonomy') in classes for e in events if e.get('refusal'))),
                    ('accepted submits carry identity, versions and trace', submits and all(
                        e.get('principal') and e.get('source') and e.get('accepted_versions') and e.get('trace')
                        and e.get('proposal_id') for e in submits if not e.get('repeated'))),
                    ('counts are the events', metrics.get('accepted') == sum(1 for e in events if e.get('refusal') is None)
                     and metrics.get('refused') == sum(1 for e in events if e.get('refusal'))),
                    ('pending is the store', metrics.get('pending') == {
                        'proposed': sum(1 for p in proposals if p['state'] == 'PROPOSED'),
                        'awaiting_project': sum(1 for p in proposals if p['state'] == 'AWAITING_PROJECT'),
                        'open_questions': 1}),
                    ('no token or key text', api['token'] not in text and 'PRIVATE KEY' not in text),
                ])
        finally:
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
            if conn is not None:
                with contextlib.suppress(Exception):
                    conn.close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])
    observed['raised'] = raised
    globals()['_V126_OBSERVED'] = observed


_v126_started = __import__('time').monotonic()
_v126_suite()
_V126_SECONDS = __import__('time').monotonic() - _v126_started
