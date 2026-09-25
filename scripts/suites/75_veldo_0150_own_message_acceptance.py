"""VELDO-0150: an objective proposed from the project owner's own message is accepted by that message.

Run: python3 scripts/selftest.py --suite 75_veldo_0150_own_message_acceptance

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy every
service loads; the production anchor below is the registered mutation driver's seam, so a mutation of
control_objective.py reaches the service. Real SQLite store with OpenSSH command, journal, edge and API
signatures; the people are enrolled by the steward's signed VELDO-0025 commands and the Telegram edge
by his VELDO-0067 enrollment. Telegram messages reach the real VELDO-0126 Intake the way VELDO-0066
acquires them: a loopback Bot API (getMe, getUpdates, sendMessage over real HTTP in the platform's
shapes, no network, no real token), the production TelegramAcquisitionEdge and Acquirer, then
Intake.take_telegram. API messages reach it through Intake.receive('api_request', ...) as requests the
API edge signs with its real key, as VELDO-0126 drives its API leg. Projects are activated by their
owners' signed VELDO-0076 commands. An objective from anyone but the project's owner is presented as
a real VELDO-0064 request by the VELDO-0065 presenter over the loopback Bot API, answered through the
API edge and settled by the real VELDO-0068 settlement, then applied by VELDO-0077's `accept`.

Expected values are spelled from outside the objective service: the intake command is the journal
record that first wrote the intake source, read here with the suite's own SQL; the attribution is the
message the loopback platform itself sent; the bound digest is recomputed here with hashlib. Where the
own-message acceptance is absent (the pre-change tree, for the red record) the command is refused and
each row fails by its own assertions.
"""


def _v150_suite():
    import contextlib
    import copy
    import hashlib
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
    PRODUCTION = {'control_objective.py': ROOT / ".veldo" / "control_objective.py"}
    PREFIX = 'VELDO-0150 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    emitted, raised = set(), []

    def check(label, parts):
        """One row: every named part must hold. A part that raises while judging is a failed part."""
        emitted.add(label)
        failed = []
        for name, condition in parts:
            try:
                ok = bool(condition() if callable(condition) else condition)
            except Exception as error:  # noqa: BLE001 - a malformed answer is a failed part, never a raise
                ok, name = False, '%s (%s)' % (name, type(error).__name__)
            if not ok:
                failed.append(name)
        if failed:
            print('  %sdetail: %s: %s' % (PREFIX, label, '; '.join(failed)))
        expect(PREFIX + label, not failed)

    @contextlib.contextmanager
    def region(*labels):
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            print('  %sdetail: %s did not run to its end: %r' % (PREFIX, labels[0], error))
            for label in labels:
                if label not in emitted:
                    check(label, [('region raised', False)])

    def message(st, sender, chat, text, reply_to=None):
        with st['lock']:
            st['next'] += 1
            st['tick'] += 1
            m = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': st['epoch'] + st['tick'],
                 'text': text}
            if reply_to is not None and (chat['id'], reply_to) in st['messages']:
                held = st['messages'][(chat['id'], reply_to)]
                m['reply_to_message'] = copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
            st['messages'][(chat['id'], m['message_id'])] = m
            return m

    class BotApi(http.server.BaseHTTPRequestHandler):
        """Loopback getMe, getUpdates and sendMessage in the Bot API shapes, for one bot."""
        state = None

        def log_message(self, *args):
            pass

        def do_POST(self):
            st = self.state
            raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
            body = json.loads(raw) if raw else {}
            _, _, rest = self.path.partition('/bot')
            name, _, method = rest.partition('/')
            if name != 'bot150':
                return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
            if method == 'getMe':
                return self._answer(200, {'ok': True, 'result': dict(st['user'], can_join_groups=True)})
            if method == 'getUpdates':
                offset = body.get('offset') or 0
                with st['lock']:
                    pending = [u for u in st['updates'] if u['update_id'] >= offset]
                return self._answer(200, {'ok': True, 'result': pending[:body.get('limit') or 100]})
            if method == 'sendMessage':
                chat = {'id': body.get('chat_id'), 'type': 'private'}
                reply = (body.get('reply_parameters') or {}).get('message_id')
                st['sent'].append((body.get('chat_id'), body.get('text')))
                return self._answer(200, {'ok': True, 'result': message(st, st['user'], chat, body['text'], reply)})
            return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

        def _answer(self, code, value):
            payload = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    connections, servers = [], []
    with tempfile.TemporaryDirectory(prefix='v150-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        try:
            claims = load('v150_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v150_keys', mods / 'control_keys.py')
            I = load('v150_inbox', mods / 'control_assignment.py')
            P = load('v150_projection', mods / 'control_channel_projection.py')
            V = load('v150_presentation', mods / 'control_channel_presentation.py')
            EV = load('v150_attribution', mods / 'control_channel_attribution.py')
            E = load('v150_enrollment', mods / 'control_channel_enrollment.py')
            ST = load('v150_settlement', mods / 'control_request_settlement.py')
            IN = load('v150_intake', mods / 'control_intake.py')
            PJ = load('v150_project', mods / 'control_project.py')
            OB = load('v150_objective', mods / 'control_objective.py')
            TM = load('v150_team', mods / 'control_team.py')
            contract = load('v150_contract', mods / 'entity_contract.py')
            DOMAIN, REPO = 'domain-150', 'repository-150'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-150')

            keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
            for d in (keys, protected, edge_dir):
                d.mkdir(mode=0o700)
            people = ('steward', 'olga', 'zed', 'asha', 'mallory')
            services = ('pm', 'api-edge')
            workers = ('w-elab', 'w-build', 'w-rev')
            keyfile = {who: keys / who for who in ('authority',) + people + services + workers}
            keyfile['edge'] = protected / 'edge-telegram'
            keyfile['edge-auth'] = edge_dir / 'edge-auth'
            public = {}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v150-' + who, '-f', str(path)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])

            def sign_as(who, data, namespace='veldo-command'):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=data,
                                      capture_output=True, check=True, timeout=20).stdout.decode()

            def journal_sign(data):
                return sign_as('authority', data, 'veldo-journal')

            serial = [0]

            def next_id(prefix):
                serial[0] += 1
                return '%s-%d' % (prefix, serial[0])

            (base / 'authority').mkdir()
            conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
            connections.append(conn)
            CM.attach(S)
            K.attach(S)
            signer_repo = base / 'signer-repository'
            signer_repo.mkdir()
            projection = signer_repo / '.veldo' / 'keys' / 'allowed_signers'

            def envelope(command, principal):
                now = CM.authority_state(S, conn)
                return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                            request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                            membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))

            def admin(principal, operation, params, enrollee=None):
                command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority',
                           'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
                env = envelope(command, principal)
                signature = sign_as(principal, AC.canonical_envelope_bytes(env))
                cosigned = (sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal'])))
                            if enrollee else None)
                result = CM.admit(S, conn, env, command, signature, ids, time.time(), enrollee_signature=cosigned,
                                  journal_signer=('authority', journal_sign))
                K.publish(S, conn, projection)
                return result

            def enroll(who, principal_type, roles, scope):
                admin('steward', 'enroll_principal', {'principal': who, 'principal_type': principal_type, 'roles': roles,
                                                      'public_key': public[who], 'independence_group': who,
                                                      'scope': scope}, enrollee=who)

            admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                                  'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                                  'independence_group': 'steward', 'scope': '*'})
            # olga owns proj-a and is a member of proj-c; zed owns proj-c and is a member of proj-a.
            enroll('olga', 'person', ['project_owner'], ['proj-a', 'proj-c'])
            enroll('zed', 'person', ['project_owner'], ['proj-a', 'proj-c'])
            enroll('asha', 'person', [], ['proj-a'])
            # mallory has an active key and acts only in proj-c.
            enroll('mallory', 'person', [], ['proj-c'])
            enroll('pm', 'service', [], ['proj-a', 'proj-c'])
            for who in workers:
                enroll(who, 'agent_run', [], ['proj-a'])
            enroll('api-edge', 'service', [], ['proj-a', 'proj-c'])

            def fixture(eid, kind, data):
                row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: row[0] if row else 0}, artifact_digests=[],
                                            nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

            chats = {'olga': 1500001, 'zed': 1500002}
            users = {who: {'id': chat, 'is_bot': False, 'first_name': who.capitalize(), 'language_code': 'en'}
                     for who, chat in chats.items()}
            # VELDO-0064 chat enrollments, spelled here: each person's own private chat with the bot.
            for who, chat in chats.items():
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))
            enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
            edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                           'public_key': public['edge'], 'connection_public_key': public['edge-auth'],
                           'scope': ['proj-a', 'proj-c']}
            edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                            'target': 'channel:telegram_chat', 'parameters': edge_params, 'artifact_digests': [],
                            'expected_versions': {}}
            edge_env = envelope(edge_command, 'steward')
            enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                             sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))

            BOT = 8000000150
            api = {'tick': 0, 'next': 15000, 'messages': {}, 'sent': [], 'updates': [], 'update_next': 150000000,
                   'lock': threading.Lock(), 'epoch': int(time.time()),
                   'user': {'id': BOT, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_own_message_bot'}}
            handler = type('V150Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]

            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot150'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot150'), conn, 'authority',
                                   journal_sign, 'telegram-edge', lambda m: sign_as('edge', m, 'veldo-command'))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=['proj-a', 'proj-c'], api_edge='api-edge',
                               journal_signer='authority', sign=journal_sign)
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)
            service = OB.Objectives(S, CM, conn, ids, 'authority', journal_sign)

            def signed(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            def activate(project, owner):
                return projects.apply(signed(owner, dict(
                    ids, operation='activate', project=project, principal=owner, command_id=next_id('pc'),
                    nonce=next_id('pn'), owner=owner, charter={'purpose': 'Sell passes to travelers.'},
                    execution_repository=REPO,
                    authority_policy={'objective_acceptance': ['project_owner'], 'admission': ['project_owner']},
                    coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))

            activated = [activate('proj-a', 'olga'), activate('proj-c', 'zed')]

            def send(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('oc'), nonce=next_id('on'), **fields)
                return service.apply(signed(who, body))

            def entity(eid):
                row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}

            def objective(oid):
                row = entity(oid) if isinstance(oid, str) else None
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'objective' else {}

            def journal_length():
                return conn.execute('SELECT count(*) FROM journal').fetchone()[0]

            def naming(oid):
                """Every record other than the objective itself whose data names it."""
                return [(eid, kind) for eid, kind, text in conn.execute('SELECT id, kind, data FROM entities')
                        if eid != oid and isinstance(oid, str) and oid in text]

            def first_writer(eid):
                """The suite's own reading of the journal: the command that first wrote `eid`."""
                for command_id, text in conn.execute('SELECT command_id, transition FROM journal ORDER BY seq'):
                    if eid in json.loads(text):
                        return command_id
                return None

            def digest_of(value):
                return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                             ensure_ascii=True).encode()).hexdigest()

            # The two sources, as the owner and his members use them.
            def by_api(principal, text, request_id=None):
                body = {'schema': 'veldo.intake_api_request/v1', 'domain': DOMAIN, 'request_id': request_id or next_id('req'),
                        'edge': 'api-edge', 'principal': principal, 'text': text, 'project': None, 'clarifies': None}
                result = intake.receive('api_request', {'request': body,
                                                        'signature': sign_as('api-edge', S.canonical_bytes(body))})
                return result, body

            def by_telegram(who, text):
                chat = {'id': chats[who], 'type': 'private', 'first_name': users[who]['first_name']}
                held = message(api, users[who], chat, text)
                with api['lock']:
                    api['update_next'] += 1
                    update = {'update_id': api['update_next'], 'message': held}
                    api['updates'].append(update)
                acquirer.acquire()
                evidence = 'channel-evidence:telegram_chat:%d:%d' % (BOT, update['update_id'])
                results = [r for r in intake.take_telegram() if r.get('evidence_id') == evidence]
                return (results[0] if results else {}), held, update

            def telegram_key(held):
                return IN.source_key('telegram_message', '%d:%d:%d' % (BOT, held['chat']['id'], held['message_id']))

            EVIDENCE = [{'id': 'outcome', 'kind': 'gate_observation'}]

            def bound(outcome, acceptor='olga', assessor='asha', scope=('checkout', 'payments')):
                return dict(outcome=outcome, scope=list(scope), authority={'acceptor': acceptor, 'assessor': assessor},
                            evidence_requirements=copy.deepcopy(EVIDENCE))

            def propose(result, fields):
                done = send('pm', 'propose', proposal=result.get('proposal_id'), **fields)
                return done, done.get('objective_id') or 'objective:absent'

            def accept_message(oid, intake_command, revision=None, bound_digest=None):
                record = objective(oid)
                return send('pm', 'accept_message', objective=oid, objective_version=record.get('version'),
                            revision=record.get('revision') if revision is None else revision,
                            bound_digest=record.get('bound_digest') if bound_digest is None else bound_digest,
                            intake_command=intake_command)

            def present(alias, oid, owner='olga'):
                """The requester's terms at the objective's current revision, the inbox request with the
                brief of that revision, and its presentation over the loopback Bot API."""
                record = objective(oid)
                return present_terms(alias, OB.acceptance_target(record), OB.acceptance_brief(record), owner)

            def present_terms(alias, target, brief, owner='olga'):
                terms = settlement.terms(signed('pm', dict(ids, operation='terms', terms=alias, principal='pm',
                                                           command_id=next_id('terms'), nonce=next_id('tn'),
                                                           touchpoint='decision_disposition', target=target,
                                                           proposal=None, required_roles=[], quorum=None)))
                inbox.apply(signed('pm', dict(ids, operation='open', alias=alias, principal='pm', command_id=next_id('c'),
                                              nonce=next_id('n'), assignment=dict(
                                                  kind='decision', owner=owner, scope=['proj-a'],
                                                  deadline='2026-10-30T17:00:00Z', budget={'owner_minutes': 15}, brief=brief,
                                                  choices=list(CHOICES), subject=terms.get('subject') or {}))))
                rid = I.assignment_id(REPO, alias)
                presenter.frame(signed('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                                  risk_statement='Low: a wrong choice costs one grooming cycle.',
                                                  command_id=next_id('f'), nonce=next_id('fn'))))
                presenter.present(rid)
                return rid, presenter.current(rid) or {}

            def answer(receipt, choice='accept', who='olga'):
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('ans'),
                            principal=who, request_id=receipt.get('request_id'), request_version=receipt.get('request_version'),
                            presentation_id=receipt.get('presentation_id'), presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice,
                            rationale='I have read the outcome, scope and evidence.')
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def accept_by_answer(oid, rid):
                return send('pm', 'accept', objective=oid, objective_version=objective(oid).get('version'), request=rid)

            # VELDO-0089: proj-a's team names pm its project manager, accepted by olga's settled answer.
            teams = TM.Teams(S, CM, conn, ids, 'authority', journal_sign, inbox=inbox, assignment=I, requester='pm',
                             request_sign=lambda m: sign_as('pm', m))

            def role(names, responsibility, perms=('feature',), distinct=()):
                return dict(workers=list(names), responsibilities=[responsibility, 'report'], expertise=['payments'],
                            proposal_permissions=list(perms), engines=['claude_code'],
                            budget={'capacity': 1, 'invocations': 2, 'wall_seconds': 100},
                            independence={'distinct_from': list(distinct)})

            def team_record():
                row = entity('team:proj-a')
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'team' else {}

            def team_send(op, **fields):
                body = dict(ids, operation=op, project='proj-a', principal='pm', command_id=next_id('tc'),
                            nonce=next_id('tn'), team_version=team_record().get('version', 0), **fields)
                return teams.apply(signed('pm', body))

            def establish_team():
                proposed = team_send('propose', team={'roles': {
                    'project_manager': role(['pm'], 'coordinate', ('objective', 'feature')),
                    'elaboration': role(['w-elab'], 'elaborate'),
                    'implementation': role(['w-build'], 'implement', ('finding',)),
                    'independent_review': role(['w-rev'], 'review', ('finding',), ('implementation',))}})
                record = team_record()
                if not record.get('proposal'):
                    return proposed, {}
                rid, receipt = present_terms('TEAM-proj-a', TM.amendment_target(record), TM.amendment_brief(record))
                settled = answer(receipt)
                proposal = team_record().get('proposal') or {}
                return settled, team_send('amend', revision=proposal.get('revision'), digest=proposal.get('digest'),
                                          request=rid)

            # AC1: the owner's own Telegram message and API request accept their objectives.
            with region('own-message/telegram', 'own-message/api', 'own-message/non-owner-presented',
                        'own-message/admits-nothing', 'evidence/bound-intake-command', 'evidence/same-bound-fields'):
                team_settled, team_amended = establish_team()
                tg, tg_held, tg_update = by_telegram('olga', 'For proj-a: please do BCG-123, travelers buy a pass in two taps.')
                tg_key = telegram_key(tg_held)
                want_tg = bound('A traveler buys a pass in two taps.')
                tg_proposed, o_tg = propose(tg, want_tg)
                assignments_before, sent_before = len([1 for _ in conn.execute(
                    "SELECT id FROM entities WHERE kind='assignment'")]), list(api['sent'])
                tg_command = first_writer(tg_key)
                tg_accepted = accept_message(o_tg, tg_command)
                tg_record = objective(o_tg)
                tg_observed = [o for o in service.observations if o.get('operation') == 'accept_message'
                               and o.get('objective') == o_tg]
                check('own-message/telegram', [
                    ('both projects are active by their owners\' commands', all(a.get('ok') for a in activated)),
                    ('pm, the proposer, is the project manager of proj-a\'s current team, by olga\'s settled answer',
                     team_settled.get('outcome') == 'settled' and team_amended.get('ok')
                     and team_record().get('revision') == 1
                     and ((team_record().get('team') or {}).get('roles') or {}).get('project_manager', {}).get('workers')
                     == ['pm']),
                    ('the owner\'s Telegram message is a proposed objective of proj-a through the intake',
                     tg.get('outcome') == 'proposed' and (intake.proposal(tg.get('proposal_id')) or {}).get('project') == 'proj-a'),
                    ('the objective is proposed from it', tg_proposed.get('ok') and tg_record.get('proposal_id') == tg.get('proposal_id')),
                    ('his message accepts it', tg_accepted.get('ok') and tg_record.get('state') == 'ACCEPTED'
                     and tg_record.get('accepted_revision') == 1),
                    ('with nothing presented: no request, no record naming the objective, nothing sent',
                     len([1 for _ in conn.execute("SELECT id FROM entities WHERE kind='assignment'")]) == assignments_before
                     and naming(o_tg) == [] and api['sent'] == sent_before),
                    ('the acceptance is recorded as his own message\'s, naming the intake command',
                     (tg_record.get('acceptance') or {}).get('path') == 'own_message'
                     and (tg_record.get('acceptance') or {}).get('intake_command') == tg_command),
                    ('the observation records the path and the intake command',
                     tg_observed and tg_observed[-1].get('outcome') == 'accepted'
                     and (tg_observed[-1].get('acceptance') or {}).get('path') == 'own_message'
                     and (tg_observed[-1].get('acceptance') or {}).get('intake_command') == tg_command)])

                ap, ap_body = by_api('olga', 'For proj-a: travelers see their pass active in ten seconds.')
                ap_key = IN.source_key('api_request', ap_body['request_id'])
                want_ap = bound('A traveler sees the pass active in ten seconds.')
                ap_proposed, o_ap = propose(ap, want_ap)
                ap_command = first_writer(ap_key)
                ap_accepted = accept_message(o_ap, ap_command)
                ap_record = objective(o_ap)
                check('own-message/api', [
                    ('the owner\'s API request is a proposed objective of proj-a through Intake.receive',
                     ap.get('outcome') == 'proposed' and (intake.proposal(ap.get('proposal_id')) or {}).get('project') == 'proj-a'),
                    ('the objective is proposed from it', ap_proposed.get('ok') and ap_record.get('proposal_id') == ap.get('proposal_id')),
                    ('his request accepts it with nothing presented', ap_accepted.get('ok') and ap_record.get('state') == 'ACCEPTED'
                     and naming(o_ap) == []),
                    ('the acceptance is recorded as his own message\'s, naming the intake command',
                     (ap_record.get('acceptance') or {}).get('path') == 'own_message'
                     and (ap_record.get('acceptance') or {}).get('intake_command') == ap_command),
                    ('the metrics count two acceptances by his own message',
                     (service.metrics().get('acceptances') or {}).get('by_own_message') == 2)])

                # Objectives from a member who is not the project's owner, by Telegram and by API.
                zt, zt_held, _zt_update = by_telegram('zed', 'For proj-a: a loyalty badge on the pass.')
                zt_proposed, o_zt = propose(zt, bound('A traveler sees a loyalty badge.'))
                zt_before = entity(o_zt)
                zt_length = journal_length()
                zt_by_message = accept_message(o_zt, first_writer(telegram_key(zt_held)))
                zt_unchanged = entity(o_zt) == zt_before and journal_length() == zt_length
                aa, aa_body = by_api('asha', 'For proj-a: receipts by email.')
                aa_proposed, o_aa = propose(aa, bound('A traveler gets a receipt by email.'))
                aa_before = entity(o_aa)
                aa_by_message = accept_message(o_aa, first_writer(IN.source_key('api_request', aa_body['request_id'])))
                aa_unchanged = entity(o_aa) == aa_before
                # Presented through VELDO-0077; a stale answer after a bound field changes is refused.
                rid_r1, receipt_r1 = present('OBJ-zed-r1', o_zt)
                amended = send('pm', 'amend', objective=o_zt, objective_version=objective(o_zt).get('version'),
                               changes={'outcome': 'A traveler sees a loyalty badge within a day.'})
                settled_r1 = answer(receipt_r1)
                before_stale = entity(o_zt)
                stale = accept_by_answer(o_zt, rid_r1)
                stale_unchanged = entity(o_zt) == before_stale
                rid_zt, receipt_zt = present('OBJ-zed-r2', o_zt)
                settled_zt = answer(receipt_zt)
                zt_accepted = accept_by_answer(o_zt, rid_zt)
                rid_aa, receipt_aa = present('OBJ-asha', o_aa)
                settled_aa = answer(receipt_aa)
                aa_accepted = accept_by_answer(o_aa, rid_aa)
                check('own-message/non-owner-presented', [
                    ('a member\'s Telegram message and API request are proposed objectives of proj-a',
                     zt.get('outcome') == 'proposed' and aa.get('outcome') == 'proposed'
                     and zt_proposed.get('ok') and aa_proposed.get('ok')),
                    ('his message does not accept the Telegram one: refused not_owner:source, nothing written',
                     zt_by_message.get('reason') == 'not_owner:source' and zt_unchanged),
                    ('nor the API one: refused not_owner:source, nothing written',
                     aa_by_message.get('reason') == 'not_owner:source' and aa_unchanged),
                    ('both stay PROPOSED until presented', zt_before and zt_before['data'].get('state') == 'PROPOSED'
                     and aa_before and aa_before['data'].get('state') == 'PROPOSED'),
                    ('an answer to revision 1 after the amendment is refused as stale, unchanged',
                     amended.get('ok') and settled_r1.get('outcome') == 'settled'
                     and stale.get('reason') == 'stale_subject:revision' and stale_unchanged),
                    ('the owner\'s answer to the current presentation accepts each',
                     settled_zt.get('outcome') == 'settled' and zt_accepted.get('ok')
                     and objective(o_zt).get('state') == 'ACCEPTED' and objective(o_zt).get('accepted_revision') == 2
                     and settled_aa.get('outcome') == 'settled' and aa_accepted.get('ok')
                     and objective(o_aa).get('state') == 'ACCEPTED'),
                    ('each acceptance names its settlement, not a message',
                     (objective(o_zt).get('acceptance') or {}).get('settlement_id') == ST.settlement_id(rid_zt, 1)
                     and (objective(o_zt).get('acceptance') or {}).get('path') != 'own_message'
                     and (objective(o_aa).get('acceptance') or {}).get('settlement_id') == ST.settlement_id(rid_aa, 1)),
                    ('the metrics count the refused own-message acceptances and the answers',
                     (service.metrics().get('acceptances') or {}).get('own_message_refused') == 2
                     and (service.metrics().get('acceptances') or {}).get('by_answer') == 2)])

                feature = send('pm', 'propose_feature', objective=o_tg, objective_version=objective(o_tg).get('version'),
                               feature='two-tap-checkout', title='Two-tap checkout', scope=['checkout'])
                fid = feature.get('feature_id')
                f_record = (entity(fid) or {}).get('data') or {} if isinstance(fid, str) else {}
                effects = [json.loads(t) for (t,) in conn.execute("SELECT data FROM entities WHERE kind='settlement_effect'")]
                check('own-message/admits-nothing', [
                    ('a feature is proposed under the objective his message accepted',
                     feature.get('ok') and objective(o_tg).get('state') == 'ACTIVE'),
                    ('the feature is RAW: neither admitted nor prioritized',
                     f_record.get('state') == 'RAW' and f_record.get('admission') is None and f_record.get('priority') is None),
                    ('no admission, priority or settled effect names it',
                     not [1 for _ in conn.execute("SELECT id FROM entities WHERE kind IN ('admission', 'priority')")]
                     and not [e for e in effects if (e.get('target') or {}).get('ref') == fid]),
                    ('nothing but the objective names the feature', {k for _e, k in naming(fid)} == {'objective'}
                     if isinstance(fid, str) else False)])

                # AC2: the acceptance binds the intake command and the canonical attribution.
                tg_accept = tg_record.get('acceptance') or {}
                ap_accept = ap_record.get('acceptance') or {}
                tg_source = intake.source('telegram_message', '%d:%d:%d' % (BOT, chats['olga'], tg_held['message_id'])) or {}
                other, other_held, _other_update = by_telegram('olga', 'For proj-a: a second objective, gift passes.')
                other_key = telegram_key(other_held)
                o_named, other_oid = propose(other, bound('A traveler gifts a pass.'))
                named_before, named_length = entity(other_oid), journal_length()
                named_other = accept_message(other_oid, tg_command)
                named_none = accept_message(other_oid, 'intake:' + '0' * 32)
                named_unchanged = entity(other_oid) == named_before and journal_length() == named_length
                named_own = accept_message(other_oid, first_writer(other_key))
                check('evidence/bound-intake-command', [
                    ('the Telegram acceptance names the intake command that first wrote the message\'s source',
                     tg_command and tg_command.startswith('intake:') and tg_accept.get('intake_command') == tg_command
                     and tg_accept.get('intake_source') == tg_key and tg_accept.get('source_kind') == 'telegram_message'),
                    ('the intake command is the intake\'s own for that source and content',
                     tg_command == 'intake:' + IN._hex(tg_key, tg_source.get('content_digest'))),
                    ('with the message\'s canonical attribution: message id, sender and platform time',
                     (tg_accept.get('attribution') or {}).get('message_id') == tg_held['message_id']
                     and (tg_accept.get('attribution') or {}).get('sender_id') == tg_held['from']['id'] == chats['olga']
                     and (tg_accept.get('attribution') or {}).get('date') == tg_held['date']
                     and (tg_accept.get('attribution') or {}).get('update_id') == tg_update['update_id']
                     and (tg_accept.get('attribution') or {}).get('evidence_id')
                     == 'channel-evidence:telegram_chat:%d:%d' % (BOT, tg_update['update_id'])),
                    ('the API acceptance names its request, principal and signed digest',
                     ap_accept.get('intake_command') == ap_command and ap_accept.get('source_id') == ap_body['request_id']
                     and (ap_accept.get('attribution') or {}).get('principal') == 'olga'
                     and (ap_accept.get('attribution') or {}).get('request_digest') == IN.digest(ap_body)),
                    ('evidence naming another message\'s intake command is refused by name, nothing written',
                     o_named.get('ok') and named_other.get('reason') == 'invalid_input:intake_command' and named_unchanged),
                    ('evidence naming no intake command is refused by name', named_none.get('reason') == 'invalid_input:intake_command'),
                    ('the message\'s own intake command accepts it', named_own.get('ok')
                     and objective(other_oid).get('state') == 'ACCEPTED')])

                def bound_parts(record, want, revision):
                    acceptance = record.get('acceptance') or {}
                    independent = digest_of(dict(want, objective=record.get('uuid'), revision=revision))
                    return (record.get('bound') == want and record.get('bound_digest') == independent
                            and record.get('accepted_revision') == revision and acceptance.get('revision') == revision
                            and acceptance.get('bound_digest') == independent and acceptance.get('principals') == ['olga']
                            and acceptance.get('ruling') == 'approve')
                zt_want = bound('A traveler sees a loyalty badge within a day.')
                check('evidence/same-bound-fields', [
                    ('the Telegram acceptance binds outcome, scope, authority and evidence requirements exactly',
                     bound_parts(tg_record, want_tg, 1)),
                    ('so does the API acceptance', bound_parts(ap_record, want_ap, 1)),
                    ('as the accepted answer binds them', bound_parts(objective(o_zt), zt_want, 2)),
                    ('both paths bind the same fields', {'revision', 'bound_digest', 'principals', 'ruling'}
                     <= set(tg_accept) & set(objective(o_zt).get('acceptance') or {}))])

            with region('evidence/project-not-his', 'evidence/repeat', 'evidence/stale-revision'):
                # His message in proj-c, whose owner is zed: the objective's acceptor is zed.
                pc, pc_held, _pc_update = by_telegram('olga', 'For proj-c: a partner portal.')
                pc_proposed, o_pc = propose(pc, bound('A partner sells a pass.', acceptor='zed', assessor='zed'))
                pc_before, pc_length = entity(o_pc), journal_length()
                pc_message = accept_message(o_pc, first_writer(telegram_key(pc_held)))
                check('evidence/project-not-his', [
                    ('his message is a proposed objective of proj-c, owned by zed',
                     pc.get('outcome') == 'proposed' and (intake.proposal(pc.get('proposal_id')) or {}).get('project') == 'proj-c'
                     and pc_proposed.get('ok') and objective(o_pc).get('project') == 'proj-c'),
                    ('his message does not accept it as its owner\'s: not_owner:source',
                     pc_message.get('reason') == 'not_owner:source'),
                    ('nothing was written', entity(o_pc) == pc_before and journal_length() == pc_length
                     and objective(o_pc).get('state') == 'PROPOSED')])

                length = journal_length()
                tg_entity = entity(o_tg)
                again_intake = intake.receive('telegram_message', 'channel-evidence:telegram_chat:%d:%d'
                                              % (BOT, tg_update['update_id']))
                again_api = intake.receive('api_request', {'request': ap_body, 'signature': sign_as(
                    'api-edge', S.canonical_bytes(ap_body))})
                again_propose = send('pm', 'propose', proposal=tg.get('proposal_id'), **want_tg)
                again_tg = send('pm', 'accept_message', objective=o_tg, objective_version=tg_record.get('version'),
                                revision=1, bound_digest=tg_record.get('bound_digest'), intake_command=tg_command)
                again_ap = accept_message(o_ap, ap_command)
                check('evidence/repeat', [
                    ('the same Telegram message again is the same proposal, repeated',
                     again_intake.get('repeated') and again_intake.get('proposal_id') == tg.get('proposal_id')),
                    ('the same API request again is the same proposal, repeated',
                     again_api.get('repeated') and again_api.get('proposal_id') == ap.get('proposal_id')),
                    ('no second objective from it', again_propose.get('reason') == 'already_exists'),
                    ('its acceptance again returns the same acceptance',
                     again_tg.get('ok') and (again_tg.get('objective') or {}).get('acceptance') == tg_accept
                     and again_ap.get('ok') and (again_ap.get('objective') or {}).get('acceptance') == ap_accept),
                    ('with no second record: the objective and the journal unchanged',
                     entity(o_tg) == tg_entity and journal_length() == length
                     and [h.get('target') for h in objective(o_tg).get('history', [])].count('ACCEPTED') == 1)])

                sr, _sr_body = by_api('olga', 'For proj-a: travelers renew in one tap.', request_id='req-stale')
                sr_proposed, o_sr = propose(sr, bound('A traveler renews in one tap.'))
                r1_digest = objective(o_sr).get('bound_digest')
                sr_command = first_writer(IN.source_key('api_request', 'req-stale'))
                sr_amended = send('pm', 'amend', objective=o_sr, objective_version=objective(o_sr).get('version'),
                                  changes={'scope': ['checkout', 'renewals']})
                sr_before, sr_length = entity(o_sr), journal_length()
                sr_stale = accept_message(o_sr, sr_command, revision=1, bound_digest=r1_digest)
                sr_stale_digest = accept_message(o_sr, sr_command, bound_digest=r1_digest)
                sr_unchanged = entity(o_sr) == sr_before and journal_length() == sr_length
                sr_current = accept_message(o_sr, sr_command)
                check('evidence/stale-revision', [
                    ('his objective is amended to revision 2 before its acceptance',
                     sr_proposed.get('ok') and sr_amended.get('ok') and (sr_before or {}).get('data', {}).get('revision') == 2),
                    ('an acceptance naming revision 1 is refused by name', sr_stale.get('reason') == 'stale_subject:revision'),
                    ('so is one naming revision 1\'s bound digest', sr_stale_digest.get('reason') == 'stale_subject:revision'),
                    ('nothing was written', sr_unchanged),
                    ('the acceptance of the current revision binds revision 2',
                     sr_current.get('ok') and objective(o_sr).get('accepted_revision') == 2
                     and (objective(o_sr).get('acceptance') or {}).get('bound_digest') == objective(o_sr).get('bound_digest')
                     != r1_digest)])

            with region('authorship/member-authored-presented', 'authorship/owner-authored',
                        'evidence/repeat-after-checks', 'evidence/paused-project'):
                # olga's message; asha, a plain member of proj-a, writes the objective's bound fields.
                h, h_held, _h_update = by_telegram('olga', 'For proj-a: travelers get a refund in one tap.')
                h_command = first_writer(telegram_key(h_held))
                h_proposed = send('asha', 'propose', proposal=h.get('proposal_id'),
                                  **bound('Asha chose this outcome.', assessor='asha', scope=('payments',)))
                o_h = h_proposed.get('objective_id') or 'objective:absent'
                h_amended = send('asha', 'amend', objective=o_h, objective_version=objective(o_h).get('version'),
                                 changes={'outcome': 'Asha amended it: a refund in one tap.'})
                h_pm = send('pm', 'propose', proposal=h.get('proposal_id'), **bound('The PM outcome.'))
                h_before, h_length, h_sent = entity(o_h), journal_length(), len(api['sent'])
                h_record = objective(o_h)
                h_by_asha = send('asha', 'accept_message', objective=o_h, objective_version=h_record.get('version'),
                                 revision=h_record.get('revision'), bound_digest=h_record.get('bound_digest'),
                                 intake_command=h_command)
                h_by_pm = accept_message(o_h, h_command)
                h_unchanged = entity(o_h) == h_before and journal_length() == h_length and len(api['sent']) == h_sent
                # zed owns proj-c and is a member of proj-a: he is not proj-a's owner or its project manager.
                zo, zo_held, _zo_update = by_telegram('olga', 'For proj-a: travelers pick a seat.')
                zo_proposed = send('zed', 'propose', proposal=zo.get('proposal_id'), **bound('A traveler picks a seat.'))
                o_zo = zo_proposed.get('objective_id') or 'objective:absent'
                zo_by_message = accept_message(o_zo, first_writer(telegram_key(zo_held)))
                # Presented to olga instead, as VELDO-0077 does, and accepted by her answer.
                rid_h, receipt_h = present('OBJ-asha-authored', o_h)
                shown = [t or '' for c, t in api['sent'][h_sent:] if c == chats['olga']]
                settled_h = answer(receipt_h)
                h_accepted = accept_by_answer(o_h, rid_h)
                check('authorship/member-authored-presented', [
                    ('asha, a member without the project manager role, proposes and amends the objective of olga\'s message',
                     h.get('outcome') == 'proposed' and h_proposed.get('ok') and h_amended.get('ok')
                     and (h_record.get('provenance') or {}).get('created_by') == 'asha' and h_record.get('revision') == 2),
                    ('the PM\'s later proposal from that message is refused already_exists, as VELDO-0077 does',
                     h_pm.get('reason') == 'already_exists'),
                    ('her acceptance naming olga\'s intake command is refused not_authorized:author',
                     h_command and h_by_asha.get('reason') == 'not_authorized:author'),
                    ('so is the PM\'s delivering the same message', h_by_pm.get('reason') == 'not_authorized:author'),
                    ('nothing was written or sent, and it stays PROPOSED',
                     h_unchanged and (h_before or {}).get('data', {}).get('state') == 'PROPOSED'),
                    ('another project\'s owner writing it in proj-a is refused the same way',
                     zo_proposed.get('ok') and zo_by_message.get('reason') == 'not_authorized:author'
                     and objective(o_zo).get('state') == 'PROPOSED'),
                    ('olga is shown asha\'s wording', any('Asha amended it: a refund in one tap.' in t for t in shown)),
                    ('and her answer accepts it through accept, naming the settlement, not a message',
                     settled_h.get('outcome') == 'settled' and h_accepted.get('ok')
                     and objective(o_h).get('state') == 'ACCEPTED'
                     and (objective(o_h).get('acceptance') or {}).get('settlement_id') == ST.settlement_id(rid_h, 1)
                     and (objective(o_h).get('acceptance') or {}).get('path') != 'own_message')])

                ow, ow_held, _ow_update = by_telegram('olga', 'For proj-a: travelers share a pass with family.')
                ow_proposed = send('olga', 'propose', proposal=ow.get('proposal_id'),
                                   **bound('A traveler shares a pass with family.'))
                o_ow = ow_proposed.get('objective_id') or 'objective:absent'
                ow_amended = send('olga', 'amend', objective=o_ow, objective_version=objective(o_ow).get('version'),
                                  changes={'scope': ['family']})
                ow_command = first_writer(telegram_key(ow_held))
                ow_accepted = accept_message(o_ow, ow_command)
                check('authorship/owner-authored', [
                    ('olga proposes and amends the objective of her own message herself',
                     ow_proposed.get('ok') and ow_amended.get('ok')
                     and (objective(o_ow).get('provenance') or {}).get('created_by') == 'olga'),
                    ('her message accepts it with nothing presented',
                     ow_accepted.get('ok') and objective(o_ow).get('state') == 'ACCEPTED' and naming(o_ow) == []
                     and (objective(o_ow).get('acceptance') or {}).get('intake_command') == ow_command
                     and objective(o_ow).get('accepted_revision') == 2)])

                # A principal with an active key who acts only in proj-c repeats olga's accepted message.
                mal_length, mal_entity = journal_length(), entity(o_tg)
                mal_record = objective(o_tg)
                mal = send('mallory', 'accept_message', objective=o_tg, objective_version=mal_record.get('version'),
                           revision=mal_record.get('revision'), bound_digest=mal_record.get('bound_digest'),
                           intake_command=tg_command)
                pm_again = accept_message(o_tg, tg_command)
                check('evidence/repeat-after-checks', [
                    ('a repeat by a principal outside proj-a\'s scope is refused not_authorized:scope, not repeated',
                     mal.get('ok') is False and mal.get('reason') == 'not_authorized:scope' and not mal.get('repeated')),
                    ('it is not handed the acceptance', 'objective' not in mal),
                    ('nothing was written', entity(o_tg) == mal_entity and journal_length() == mal_length),
                    ('a member in scope still gets the same acceptance', pm_again.get('ok') and pm_again.get('repeated')
                     and (pm_again.get('objective') or {}).get('acceptance') == mal_record.get('acceptance'))])

                pp, pp_held, _pp_update = by_telegram('olga', 'For proj-a: travelers pause auto-refill.')
                pp_proposed, o_pp = propose(pp, bound('A traveler pauses auto-refill.'))
                pp_command = first_writer(telegram_key(pp_held))
                paused = projects.apply(signed('olga', dict(
                    ids, operation='pause', project='proj-a', principal='olga', command_id=next_id('pc'),
                    nonce=next_id('pn'), reason='A pricing review.', project_version=entity('project:proj-a')['version'])))
                pp_before, pp_length = entity(o_pp), journal_length()
                pp_paused = accept_message(o_pp, pp_command)
                pp_repeat = accept_message(o_tg, tg_command)
                pp_unchanged = entity(o_pp) == pp_before and journal_length() == pp_length
                resumed = projects.apply(signed('olga', dict(
                    ids, operation='resume', project='proj-a', principal='olga', command_id=next_id('pc'),
                    nonce=next_id('pn'), project_version=entity('project:proj-a')['version'])))
                pp_active = accept_message(o_pp, pp_command)
                check('evidence/paused-project', [
                    ('olga pauses proj-a after the PM proposed the objective of her message',
                     pp_proposed.get('ok') and paused.get('ok')
                     and (entity('project:proj-a') or {}).get('data', {}).get('state') == 'ACTIVE' and resumed.get('ok')),
                    ('her message\'s acceptance while paused is refused project_not_active:PAUSED',
                     pp_paused.get('reason') == 'project_not_active:PAUSED'),
                    ('nothing was written and it stays PROPOSED',
                     pp_unchanged and (pp_before or {}).get('data', {}).get('state') == 'PROPOSED'),
                    ('a repeat of an accepted message while paused is refused the same way, not repeated',
                     pp_repeat.get('reason') == 'project_not_active:PAUSED' and not pp_repeat.get('repeated')),
                    ('once resumed her message accepts it', pp_active.get('ok') and objective(o_pp).get('state') == 'ACCEPTED')])
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for connection in connections:
                connection.close()
    if raised:
        print('  %sdetail: regions that raised: %s' % (PREFIX, raised))


_v150_started = __import__('time').monotonic()
_v150_suite()
print('VELDO-0150 suite seconds: %.3f' % (__import__('time').monotonic() - _v150_started))
