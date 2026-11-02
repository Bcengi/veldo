"""Signed intake and grooming setup adapted from suite 76. No dependency tests run."""
import contextlib

@contextlib.contextmanager
def fixture(ROOT, PRODUCTION):
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

    PREFIX = 'VELDO-0079 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    DEFAULT_RANK = 3
    EXPIRY = '2030-01-31T17:00:00Z'
    CEILING = {'invocations': 3, 'wall_seconds': 300}
    POLICY_A = {'objective_acceptance': ['project_owner'], 'admission': ['admission_authority'],
                'priority': ['priority_authority']}
    POLICY_B = {'objective_acceptance': ['project_owner'], 'admission': ['admission_authority']}

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def attempt(fn, default=None):
        try:
            return fn()
        except Exception as error:  # noqa: BLE001 - a call that cannot answer is a failed part
            return default if default is not None else {'ok': False, 'reason': 'raised:' + type(error).__name__}

    def sha(value):
        return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                     ensure_ascii=True).encode()).hexdigest()

    def words(text):
        return ' '.join(str(text).split())

    def message(st, sender, chat, text, reply_to=None):
        with st['lock']:
            st['next'] += 1
            st['tick'] += 1
            m = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': int(time.time()) + st['tick'],
                 'text': text}
            if reply_to is not None and (chat['id'], reply_to) in st['messages']:
                held = st['messages'][(chat['id'], reply_to)]
                m['reply_to_message'] = copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
            st['messages'][(chat['id'], m['message_id'])] = m
            return m

    class BotApi(http.server.BaseHTTPRequestHandler):
        """Loopback getMe, getUpdates and sendMessage in the Bot API shapes, for one bot; it keeps every
        sendMessage body it was given, which are the bytes Telegram would show."""
        state = None

        def log_message(self, *args):
            pass

        def do_POST(self):
            st = self.state
            raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
            body = json.loads(raw) if raw else {}
            _, _, rest = self.path.partition('/bot')
            name, _, method = rest.partition('/')
            if name != 'bot79':
                return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
            if method == 'getMe':
                return self._answer(200, {'ok': True, 'result': dict(st['user'], can_join_groups=True)})
            if method == 'getUpdates':
                return self._answer(200, {'ok': True, 'result': [u for u in st.get('updates', []) if u['update_id'] >= body.get('offset', 0)]})
            if method == 'sendMessage':
                chat = {'id': body.get('chat_id'), 'type': 'private'}
                reply = (body.get('reply_parameters') or {}).get('message_id')
                held = message(st, st['user'], chat, body['text'], reply)
                st['sent'].append({'chat_id': body.get('chat_id'), 'text': body['text'],
                                   'message_id': held['message_id'], 'reply_to': reply})
                return self._answer(200, {'ok': True, 'result': held})
            return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

        def _answer(self, code, value):
            payload = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    fast = None
    connections, servers = [], []
    with tempfile.TemporaryDirectory(prefix='v79-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        try:
            claims = load('v79_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v79_keys', mods / 'control_keys.py')
            I = load('v79_inbox', mods / 'control_assignment.py')
            P = load('v79_projection', mods / 'control_channel_projection.py')
            V = load('v79_presentation', mods / 'control_channel_presentation.py')
            EV = load('v79_attribution', mods / 'control_channel_attribution.py')
            E = load('v79_enrollment', mods / 'control_channel_enrollment.py')
            ST = load('v79_settlement', mods / 'control_request_settlement.py')
            IN = load('v79_intake', mods / 'control_intake.py')
            PJ = load('v79_project', mods / 'control_project.py')
            OB = load('v79_objective', mods / 'control_objective.py')
            TM = load('v79_team', mods / 'control_team.py')
            contract = load('v79_contract', mods / 'entity_contract.py')
            CB = load('v79_backlog', mods / 'control_backlog.py')
            GM = load('v79_grooming', mods / 'control_grooming.py') if (mods / 'control_grooming.py').is_file() else None
            GR = (load('v79_grooming_request', mods / 'control_grooming_request.py')
                  if (mods / 'control_grooming_request.py').is_file() else None)
            DOMAIN, REPO = 'domain-79', 'repository-79'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-79')

            keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
            for d in (keys, protected, edge_dir):
                d.mkdir(mode=0o700)
            people = ('steward', 'olga', 'zed', 'asha')
            services = ('pm', 'mem', 'grooming', 'api-edge')
            workers = ('w-elab', 'w-build', 'w-rev')
            keyfile = {who: keys / who for who in ('authority',) + people + services + workers}
            keyfile['edge'] = protected / 'edge-telegram'
            keyfile['edge-auth'] = edge_dir / 'edge-auth'
            public = {}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v79-' + who, '-f', str(path)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])

            def sign_as(who, data, namespace='veldo-command'):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=data,
                                      capture_output=True, check=True, timeout=20,
                                      env={k: v for k, v in os.environ.items() if k != 'SSH_AUTH_SOCK'}).stdout.decode()

            def journal_sign(data):
                return sign_as('authority', data, 'veldo-journal')

            serial = [0]

            def next_id(prefix):
                serial[0] += 1
                return '%s-%d' % (prefix, serial[0])

            (base / 'authority').mkdir()
            db = base / 'authority' / 'control.sqlite3'
            conn = S.open_store(str(db))
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
                                                  'roles': ['membership_steward', 'project_owner'],
                                                  'public_key': public['steward'], 'independence_group': 'steward',
                                                  'scope': '*'})
            # olga owns proj-a with both decision roles; zed owns proj-b and holds admission, never priority.
            enroll('olga', 'person', ['project_owner', 'admission_authority', 'priority_authority'], ['proj-a', 'factory'])
            enroll('zed', 'person', ['project_owner', 'admission_authority'], ['proj-b'])
            enroll('asha', 'person', [], ['proj-a', 'proj-b'])
            enroll('pm', 'service', [], ['proj-a', 'proj-b', REPO])
            enroll('mem', 'service', [], ['proj-a'])
            enroll('grooming', 'service', [], ['proj-a', 'proj-b'])
            enroll('api-edge', 'service', [], ['proj-a', 'proj-b'])
            for who in workers:
                enroll(who, 'agent_run', [], ['proj-a', REPO])

            def fixture(eid, kind, data):
                row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: row[0] if row else 0}, artifact_digests=[],
                                            nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

            chats = {'olga': 5790001, 'zed': 5790002}
            for who, chat in chats.items():
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))
            enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
            edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                           'public_key': public['edge'], 'connection_public_key': public['edge-auth'],
                           'scope': ['proj-a', 'proj-b']}
            edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                            'target': 'channel:telegram_chat', 'parameters': edge_params, 'artifact_digests': [],
                            'expected_versions': {}}
            edge_env = envelope(edge_command, 'steward')
            enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                             sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))

            api = {'tick': 0, 'next': 9000, 'messages': {}, 'sent': [], 'lock': threading.Lock(),
                   'user': {'id': 8000000079, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_grooming_bot'}}
            handler = type('V79Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]

            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot79'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot79'), conn, 'authority',
                                   journal_sign, 'telegram-edge', lambda m: sign_as('edge', m, 'veldo-command'))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=['proj-a', 'proj-b'],
                               api_edge='api-edge', journal_signer='authority', sign=journal_sign)
            neighbor152 = __import__('runpy').run_path(str(ROOT / 'proof/VELDO-0152/neighbors.py'))
            neighbor152['factory'](intake, ids, 'olga', sign_as)
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)

            def signed(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            for name, owner, policy in (('proj-a', 'olga', POLICY_A), ('proj-b', 'zed', POLICY_B)):
                projects.apply(signed(owner, dict(
                    ids, operation='activate', project=name, principal=owner, command_id=next_id('pc'),
                    nonce=next_id('pn'), owner=owner, charter={'purpose': 'Sell passes to travelers.'},
                    execution_repository=REPO, authority_policy=policy, ticket_key_prefixes=['BUG'] if name == 'proj-a' else [],
                    coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))

            # The workspace: the specifications the units bind, one of them protecting a path.
            work = base / 'work'
            (work / 'specs').mkdir(parents=True)

            def spec_file(sid, protected_paths):
                path = work / 'specs' / ('%s-grooming-fixture.md' % sid)
                path.write_text('\n'.join([
                    '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Grooming fixture unit', 'status: ready',
                    'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                    'protected_paths: [%s]' % ', '.join(protected_paths), 'acceptance_criteria:', '  - id: AC1',
                    '    text: The unit check passes.', 'required_evidence: [unit]', 'rollback: git revert', '---', '',
                    '## Intent', '', 'Fixture.', '']))
                return path

            spec_file('VELDO-9791', ['.veldo/policy.yaml'])
            spec_file('VELDO-9792', [])

            def file_digest(sid):
                return 'sha256:' + hashlib.sha256((work / 'specs' / ('%s-grooming-fixture.md' % sid)).read_bytes()).hexdigest()

            reader = S.open_store(str(db), mode='r')
            connections.append(reader)
            service = CB.Backlog(S, CM, conn, ids, 'authority', journal_sign, workspace=str(work))
            grooming = (GM.Grooming(S, CM, conn, ids, 'authority', journal_sign, backlog=CB, service=service, assignment=I,
                                    inbox=inbox, presenter=presenter, settlement=settlement,
                                    requester=('grooming', lambda m: sign_as('grooming', m)), workspace=str(work))
                        if GM is not None else None)
            missing = {'ok': False, 'reason': 'no_grooming_service'}

            def entity(eid):
                row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

            def data_of(eid):
                return (entity(eid) or {}).get('data') or {}

            def item(iid):
                row = entity(iid) if isinstance(iid, str) else None
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'backlog_item' else {}

            def of_kind(kind):
                return [(eid, json.loads(t)) for eid, t in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id',
                                                                       (kind,))]

            def first_writer(eid):
                """The suite's own reading of the journal: the command that first wrote `eid`."""
                for command_id, text in conn.execute('SELECT command_id, transition FROM journal ORDER BY seq'):
                    if eid in json.loads(text):
                        return command_id
                return None

            def executable(uid):
                return CB.executable_problems(reader, uid)

            def request_record_id(iid):
                return 'admission-request:' + hashlib.sha256(json.dumps(['admission-request', iid], sort_keys=True,
                                                                        separators=(',', ':')).encode()).hexdigest()[:32]

            def request_record(iid):
                row = entity(request_record_id(iid))
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'admission_request' else {}

            # The team: pm is proj-a's project manager by olga's settled answer (VELDO-0089).
            teams = TM.Teams(S, CM, conn, ids, 'authority', journal_sign, inbox=inbox, assignment=I, requester='pm',
                             request_sign=lambda m: sign_as('pm', m))

            def answer(receipt, choice='accept', who='olga', rationale='I have read the whole request.'):
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('ans'),
                            principal=who, request_id=receipt.get('request_id'), request_version=receipt.get('request_version'),
                            presentation_id=receipt.get('presentation_id'), presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice, rationale=rationale)
                packet = {'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))}
                return settlement.api_answer(packet), packet

            def present_terms(alias, target, brief, owner='olga', touchpoint='decision_disposition'):
                terms = settlement.terms(signed('pm', dict(ids, operation='terms', terms=alias, principal='pm',
                                                           command_id=next_id('terms'), nonce=next_id('tn'),
                                                           touchpoint=touchpoint, target=target,
                                                           proposal=None, required_roles=[], quorum=None)))
                inbox.apply(signed('pm', dict(ids, operation='open', alias=alias, principal='pm', command_id=next_id('c'),
                                              nonce=next_id('n'), assignment=dict(
                                                  kind='decision', owner=owner, scope=['proj-a'],
                                                  deadline=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + 3600)), budget={'owner_minutes': 15}, brief=brief,
                                                  choices=list(CHOICES), subject=terms.get('subject') or {}))))
                rid = I.assignment_id(REPO, alias)
                presenter.frame(signed('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                                  risk_statement='Low: a wrong choice costs one grooming cycle.',
                                                  command_id=next_id('f'), nonce=next_id('fn'))))
                presenter.present(rid)
                return rid, presenter.current(rid) or {}

            CG = load('team_fixture_config', mods / 'control_agent_config.py')
            configurations = CG.Configurations(S, conn, domain=ids['domain_uuid'],
                repository=ids['repository_uuid'], signer='authority', sign=journal_sign)
            configurations.save(dict(role='team-fixture', engine='claude_code', native_tools=[],
                mcp=[], skills=[], instructions=[], settings={}), principal='steward', base=0,
                command_id=next_id('capability'))

            def role(names, responsibility, perms=('feature',), distinct=()):
                return dict(kind='required', capability_configuration={'role': 'team-fixture', 'revision': 1}, workers=list(names), responsibilities=[responsibility, 'report'], expertise=['payments'],
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

            team_send('propose', team={'roles': {
                'project_manager': role(['pm'], 'coordinate', ('objective', 'feature')),
                'elaboration': role(['w-elab'], 'elaborate'),
                'implementation': role(['w-build'], 'implement', ('finding',)),
                'independent_review': role(['w-rev'], 'review', ('finding',), ('implementation',))}})
            team_rid, team_receipt = present_terms('TEAM-proj-a', TM.amendment_target(team_record()),
                                                   TM.amendment_brief(team_record()))
            answer(team_receipt)
            team_proposal = team_record().get('proposal') or {}
            team_send('amend', revision=team_proposal.get('revision'), digest=team_proposal.get('digest'), request=team_rid)

            def osend(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('oc'), nonce=next_id('on'), **fields)
                return objectives.apply(signed(who, body))

            objectives = OB.Objectives(S, CM, conn, ids, 'authority', journal_sign, workspace=str(work))
            EVIDENCE = [{'id': 'outcome', 'kind': 'gate_observation'}]

            def by_api(principal, text):
                body = {'schema': IN.API_SCHEMA, 'domain': DOMAIN, 'request_id': next_id('req'), 'edge': 'api-edge',
                        'principal': principal, 'text': text, 'project': next((p for p in ('proj-a', 'proj-b', 'proj-c') if text.startswith('For ' + p + ':')), None), 'clarifies': None}
                result = intake.receive('api_request', {'request': body,
                                                        'signature': sign_as('api-edge', S.canonical_bytes(body))})
                return result, body

            def bsend(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('bc'), nonce=next_id('bn'), **fields)
                return service.apply(signed(who, body))

            def bop(who, op, iid, **fields):
                return bsend(who, op, item=iid, item_version=item(iid).get('version'), **fields)

            units_made = [0]

            def unit_entry(spec='VELDO-9791'):
                units_made[0] += 1
                return dict(unit='TASK-79-%d' % units_made[0], specification=spec, scope=['checkout'], requirements=[],
                            eligible_holders=['w-build'])

            def proposal(**changes):
                value = {'ceiling': dict(CEILING), 'expiry': EXPIRY}
                value.update(changes)
                return value

            def gpropose(who, iid, **changes):
                if grooming is None:
                    return dict(missing)
                body = dict(ids, operation='propose', principal=who, command_id=next_id('gc'), nonce=next_id('gn'),
                            item=iid, item_version=item(iid).get('version'), proposal=proposal(**changes))
                return grooming.apply(signed(who, body))

            def groom(iid):
                return attempt(lambda: grooming.groom(iid)) if grooming is not None else dict(missing)

            def apply_rulings(iid):
                return attempt(lambda: grooming.apply_rulings(iid), default=[]) if grooming is not None else []

            def requests_of(iid, touchpoint):
                """[(alias, request id, data)] grooming opened for the item's touchpoint, via its own reader."""
                if grooming is None or not request_record(iid):
                    return []
                return attempt(lambda: grooming.requests(request_record(iid), touchpoint), default=[])

            def current_request(iid, touchpoint):
                found = requests_of(iid, touchpoint)
                return found[-1][1] if found else None

            def shown(iid, touchpoint):
                rid = current_request(iid, touchpoint)
                return (presenter.current(rid) or {}) if rid else {}

            def gsigned(op, iid, **fields):
                """A backlog command the grooming service's own key signs, kept by the caller."""
                return signed('grooming', dict(ids, operation=op, principal='grooming', command_id=next_id('gb'),
                                               nonce=next_id('gbn'), item=iid, item_version=item(iid).get('version'),
                                               **fields))

            def admit_message(iid, who='grooming'):
                record = request_record(iid)
                body = dict(ids, operation='admit_message', principal=who, command_id=next_id('am'), nonce=next_id('amn'),
                            item=iid, item_version=item(iid).get('version'), request_revision=record.get('revision'),
                            request_digest=record.get('digest'))
                return service.apply(signed(who, body))

            yield locals()
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for connection in connections:
                connection.close()
