"""VELDO-0079: grooming and admission requests through enrolled decision surfaces, over a real signed store.

Run: python3 scripts/selftest.py --suite 76_veldo_0079_grooming

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy every
service loads; the production anchors below are the registered mutation driver's seams, so a mutation of
control_grooming.py, control_grooming_request.py or control_backlog.py reaches the grooming service and
the backlog. Real SQLite store with OpenSSH command, journal, edge and API signatures; people and services
are enrolled by the steward's signed VELDO-0025 commands; projects are activated by their owners' signed
VELDO-0076 commands and proj-a's team names pm its project manager by olga's settled VELDO-0089 answer.
Objectives come from the owner's own API messages through the real VELDO-0126 Intake.receive and are
accepted by VELDO-0150's accept_message, or are proposed by pm and accepted by olga's presented answer
through VELDO-0077; features, backlog items and their decompositions are the real VELDO-0077 and
VELDO-0078 services'. Every grooming request is a real VELDO-0064 request the grooming service opens,
frames and presents through the VELDO-0065 presenter over a loopback Bot API (real HTTP in the platform's
shapes, no network, no real token), whose sendMessage bodies are the Telegram bytes the rows read; every
answer is an assertion the API edge signs, settled by the real VELDO-0068 settlement. Executable-work
answers are read on a second, read-only connection.

Expected values are spelled from outside the grooming modules: the request schema's sixteen fields, the
lane of a product change, the default rank, the specification digests (hashlib over the files) and the
authority policy digest are computed here. Where the grooming service is absent (the pre-change tree, for
the red record) every grooming call is answered no_grooming_service and each row fails by its own
assertions.
"""


def _v79_suite():
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

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {'control_grooming.py': ROOT / ".veldo" / "control_grooming.py",
                  'control_grooming_request.py': ROOT / ".veldo" / "control_grooming_request.py",
                  'control_backlog.py': ROOT / ".veldo" / "control_backlog.py"}
    SCAFFOLD = ROOT / ".veldo" / "init_scaffold.py"
    PREFIX = 'VELDO-0079 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    # AC1's declared set: the request schema, spelled here and not read from the module.
    SCHEMA_FIELDS = ('class', 'lane', 'outcome', 'scope', 'exclusions', 'priority', 'ceiling', 'policy',
                     'specifications', 'protected_paths', 'release_authority', 'expiry', 'evidence', 'decomposition',
                     'alternatives', 'questions')
    PROPOSED = ('exclusions', 'priority', 'ceiling', 'expiry', 'alternatives', 'questions')
    NO_WRITER = ('class', 'lane', 'outcome', 'scope', 'policy', 'release_authority', 'evidence')
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
            m = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791400000 + st['tick'],
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
                return self._answer(200, {'ok': True, 'result': []})
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

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
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
            with region('install/assets'):
                scaffold = load('v79_scaffold', SCAFFOLD)
                rels = ('.veldo/control_grooming.py', '.veldo/control_grooming_request.py')
                present = {r: (ROOT / r).is_file() and (ROOT / 'engine' / r).is_file() for r in rels}
                for r in rels:
                    if present[r]:
                        scaffold._lay(ROOT / 'engine' / r, base / 'laid' / r, r, [], [])
                same = [r for r in ('.veldo/control_backlog.py', '.veldo/init_scaffold.py')
                        if (ROOT / 'engine' / r).read_bytes() == (ROOT / r).read_bytes()]
                check('install/assets', [
                    ('the grooming service and its request contract installed by the scaffold',
                     all(r in scaffold._FILES for r in rels)),
                    ('neither claimed as validator substrate', not any(r in scaffold.REQUIRED_SUBSTRATE for r in rels)),
                    ('both engine copies identical', all(present[r] and (ROOT / 'engine' / r).read_bytes()
                                                         == (ROOT / r).read_bytes() for r in rels)),
                    ('both laid by the installer', all(present[r] and (base / 'laid' / r).is_file()
                                                       and (base / 'laid' / r).read_bytes() == (ROOT / r).read_bytes()
                                                       for r in rels)),
                    ('control_backlog and init_scaffold engine copies identical', len(same) == 2)])

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
                                      capture_output=True, check=True, timeout=20).stdout.decode()

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
            enroll('olga', 'person', ['project_owner', 'admission_authority', 'priority_authority'], ['proj-a'])
            enroll('zed', 'person', ['project_owner', 'admission_authority'], ['proj-b'])
            enroll('asha', 'person', [], ['proj-a', 'proj-b'])
            enroll('pm', 'service', [], ['proj-a', 'proj-b'])
            enroll('mem', 'service', [], ['proj-a'])
            enroll('grooming', 'service', [], ['proj-a', 'proj-b'])
            enroll('api-edge', 'service', [], ['proj-a', 'proj-b'])
            for who in workers:
                enroll(who, 'agent_run', [], ['proj-a'])

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
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)

            def signed(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            for name, owner, policy in (('proj-a', 'olga', POLICY_A), ('proj-b', 'zed', POLICY_B)):
                projects.apply(signed(owner, dict(
                    ids, operation='activate', project=name, principal=owner, command_id=next_id('pc'),
                    nonce=next_id('pn'), owner=owner, charter={'purpose': 'Sell passes to travelers.'},
                    execution_repository=REPO, authority_policy=policy,
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

            def journal_length():
                return conn.execute('SELECT count(*) FROM journal').fetchone()[0]

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

            def assignments_naming(iid):
                """Every inbox request whose brief names the item."""
                return [(eid, d) for eid, d in of_kind('assignment') if iid in str(d.get('brief'))]

            def sent_naming(iid):
                return [m for m in api['sent'] if iid in m['text']]

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
                                                  deadline='2026-10-30T17:00:00Z', budget={'owner_minutes': 15}, brief=brief,
                                                  choices=list(CHOICES), subject=terms.get('subject') or {}))))
                rid = I.assignment_id(REPO, alias)
                presenter.frame(signed('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                                  risk_statement='Low: a wrong choice costs one grooming cycle.',
                                                  command_id=next_id('f'), nonce=next_id('fn'))))
                presenter.present(rid)
                return rid, presenter.current(rid) or {}

            def thin_target(record):
                """VELDO-0078's own admission target, the item at its decomposition revision, spelled here as
                516afd1's backlog built it (decision_target)."""
                return {'kind': 'backlog_item', 'ref': record.get('uuid'), 'revision': record.get('decomposition_revision'),
                        'digest': record.get('decomposition_digest')}

            def thin_brief(record):
                """VELDO-0078's thinner admission brief, spelled here as 516afd1's backlog rendered it
                (admission_brief): no policy, ceiling, specification digests, protected paths, release authority,
                expiry, evidence, alternatives or questions."""
                units = '; '.join('%s (%s)' % (u['unit'], u['specification']) for u in record.get('decomposition') or [])
                return ('Admit backlog item %s, decomposition revision %d, in project %s.\nTitle: %s\nClass: %s\n'
                        'Scope: %s\nUnits: %s\nAdmitted work still needs its own priority before anything runs.'
                        % (record.get('uuid'), record.get('decomposition_revision') or 0, record.get('project'),
                           record.get('title'), record.get('work_class'), '; '.join(record.get('scope') or []), units))

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
                        'principal': principal, 'text': text, 'project': None, 'clarifies': None}
                result = intake.receive('api_request', {'request': body,
                                                        'signature': sign_as('api-edge', S.canonical_bytes(body))})
                return result, body

            def own_objective(outcome, project='proj-a', owner='olga'):
                """An objective proposed by the owner from his own API message and accepted by that message."""
                m, body = by_api(owner, 'For %s: %s' % (project, outcome))
                made = osend(owner, 'propose', proposal=m.get('proposal_id'), outcome=outcome, scope=['checkout', 'payments'],
                             authority={'acceptor': owner, 'assessor': 'asha'}, evidence_requirements=copy.deepcopy(EVIDENCE))
                oid = made.get('objective_id')
                record = OB.read(conn, oid) or {}
                command = first_writer(IN.source_key('api_request', body['request_id']))
                osend('pm', 'accept_message', objective=oid, objective_version=record.get('version'),
                      revision=record.get('revision'), bound_digest=record.get('bound_digest'), intake_command=command)
                return oid, command

            def answered_objective(outcome):
                """An objective pm proposes and olga accepts by her answer to its presentation (VELDO-0077)."""
                m, _ = by_api('olga', 'For proj-a: %s' % outcome)
                made = osend('pm', 'propose', proposal=m.get('proposal_id'), outcome=outcome, scope=['checkout', 'payments'],
                             authority={'acceptor': 'olga', 'assessor': 'asha'}, evidence_requirements=copy.deepcopy(EVIDENCE))
                oid = made.get('objective_id')
                record = OB.read(conn, oid) or {}
                rid, receipt = present_terms(next_id('OBJ'), OB.acceptance_target(record), OB.acceptance_brief(record))
                answer(receipt)
                osend('pm', 'accept', objective=oid, objective_version=(OB.read(conn, oid) or {}).get('version'), request=rid)
                return oid, rid

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

            def work_item(oid, name, specs=('VELDO-9791',)):
                """A backlog item from a feature of `oid`, prepared and awaiting grooming: (item, [units])."""
                made = osend('pm', 'propose_feature', objective=oid, objective_version=(OB.read(conn, oid) or {}).get('version'),
                             feature='f-' + name, title='Feature %s' % name, scope=['checkout'])
                took = bsend('pm', 'take', feature=made.get('feature_id'), work_class='PRODUCT_CHANGE')
                iid = took.get('item_id')
                units = [unit_entry(s) for s in specs]
                bop('pm', 'prepare', iid, units=units)
                bop('pm', 'request_grooming', iid)
                return iid, [u['unit'] for u in units]

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

            # The objectives the rows' work is taken from.
            o_own, own_command = own_objective('A traveler buys a pass in two taps.')
            o_answer, o_answer_request = answered_objective('A traveler renews a pass in one tap.')
            o_zed, zed_command = own_objective('A cruise guest buys a pass on board.', project='proj-b', owner='zed')

            # AC2: his own message admits work at the default priority when the PM asks nothing.
            with region('route/own-message-default'):
                M, m_units = work_item(o_own, 'message', ('VELDO-9791', 'VELDO-9792'))
                sent_before, assignments_before = len(api['sent']), len(of_kind('assignment'))
                proposed_m = gpropose('pm', M)
                groomed_m = groom(M)
                record_m = request_record(M)
                after_m = item(M)
                admission_m = after_m.get('admission') or {}
                priority_m = after_m.get('priority') or {}
                check('route/own-message-default', [
                    ('his message proposed and accepted the objective',
                     (OB.read(conn, o_own) or {}).get('acceptance', {}).get('path') == 'own_message'),
                    ('pm, the project manager, proposed the grooming with no question and no priority',
                     proposed_m.get('ok') and record_m.get('author') == 'pm' and record_m.get('content', {}).get('questions') == []),
                    ('the item is admitted and prioritized by his message',
                     groomed_m.get('outcome') == 'admitted' and after_m.get('state') == 'PRIORITIZED'),
                    ('at the default priority', priority_m.get('rank') == DEFAULT_RANK),
                    ('the admission and priority name his message as their evidence',
                     admission_m.get('path') == 'own_message' and admission_m.get('intake_command') == own_command
                     and priority_m.get('intake_command') == own_command and admission_m.get('principals') == ['olga']),
                    ('they name the request revision they applied',
                     admission_m.get('request_revision') == record_m.get('revision')
                     and admission_m.get('request_digest') == record_m.get('digest')),
                    ('nothing was presented: no request opened and nothing sent',
                     len(api['sent']) == sent_before and len(of_kind('assignment')) == assignments_before
                     and not assignments_naming(M)),
                    ('every unit is executable', all(executable(u) == [] for u in m_units)
                     and all(data_of('admission:' + u).get('state') == 'accepted' for u in m_units))])

            # AC2 (declared falsifier): a question or another priority is asked, never admitted by his message.
            with region('route/ask-when-needed'):
                Q, q_units = work_item(o_own, 'question')
                gpropose('pm', Q, questions=[{'id': 'q1', 'text': 'Should the pass show a QR code?'}])
                groomed_q = groom(Q)
                R, r_units = work_item(o_own, 'rank')
                gpropose('pm', R, priority={'rank': 1})
                groomed_r = groom(R)
                A, a_units = work_item(o_answer, 'answered')
                gpropose('pm', A)
                groomed_a = groom(A)
                W, w_units = work_item(o_own, 'member')
                gpropose('mem', W)
                groomed_w = groom(W)
                cases = {'question': (Q, groomed_q, q_units), 'priority': (R, groomed_r, r_units),
                         'objective_by_answer': (A, groomed_a, a_units), 'author': (W, groomed_w, w_units)}
                direct = {why: admit_message(iid) for why, (iid, _g, _u) in cases.items()}
                check('route/ask-when-needed', [
                    ('each is presented, naming why', all(g.get('outcome') == 'presented' and why in (g.get('reasons') or [])
                                                          for why, (_i, g, _u) in cases.items())),
                    ('each has its admission and priority requests published on Telegram',
                     all(shown(i, 'admission').get('outcome') == 'published' and shown(i, 'priority').get('outcome') == 'published'
                         for i, _g, _u in cases.values())),
                    ('none is admitted: each awaits grooming', all(item(i).get('state') == 'AWAITING_GROOMING'
                                                                  for i, _g, _u in cases.values())),
                    ('asking the backlog to admit it by his message is refused by the reason',
                     all(direct[why].get('reason') == 'not_approved:' + why for why in cases)),
                    ('no unit of any of them is executable', all(executable(u) == ['missing_authority:admission']
                                                                 for _i, _g, units in cases.values() for u in units))])

            # AC1: the Telegram bytes carry the complete request.
            with region('material/telegram-brief'):
                spec_file('VELDO-9793', ['.veldo/policy.yaml', 'scripts/verify.sh'])
                T, t_units = work_item(o_own, 'material', ('VELDO-9791', 'VELDO-9793'))
                gpropose('pm', T, questions=[{'id': 'q-map', 'text': 'May the pass page show a map?'}],
                         priority={'rank': 2}, exclusions=['refunds'], alternatives=['a paper pass at the desk'])
                groom(T)
                record_t = request_record(T)
                item_t = item(T)
                project_a = data_of('project:proj-a')
                texts = {tp: words(' '.join(m['text'] for m in sent_naming(T) if ('Admit backlog item' if tp == 'admission'
                                                                                  else 'Prioritize backlog item') in m['text']))
                         for tp in ('admission', 'priority')}
                expected = {
                    'class': ['Class: PRODUCT_CHANGE'],
                    'lane': ['Lane: ordinary'],
                    'outcome': ['A traveler buys a pass in two taps.', o_own],
                    'scope': ['Scope: checkout'],
                    'exclusions': ['Exclusions: refunds'],
                    'priority': ['rank 2', 'the default is %d' % DEFAULT_RANK],
                    'ceiling': ['invocations=3', 'wall_seconds=300'],
                    'policy': [str(project_a.get('charter_digest')), sha(POLICY_A), 'charter revision 1'],
                    'specifications': ['VELDO-9791 ' + file_digest('VELDO-9791'), 'VELDO-9793 ' + file_digest('VELDO-9793')],
                    'protected_paths': ['.veldo/policy.yaml', 'scripts/verify.sh'],
                    'release_authority': ['at most land in repository ' + REPO],
                    'expiry': [EXPIRY],
                    'evidence': ['outcome (gate_observation)', own_command],
                    'decomposition': [str(item_t.get('decomposition_digest'))] + t_units,
                    'alternatives': ['a paper pass at the desk'],
                    'questions': ['q-map - May the pass page show a map?']}
                missing_parts = sorted('%s/%s' % (tp, f) for tp in texts for f, parts in expected.items()
                                       for p in parts if words(p) not in texts[tp])
                if missing_parts:
                    print('  %sdetail: fragments absent from the Telegram text: %s' % (PREFIX, missing_parts))
                terms_t = {tp: data_of((data_of(current_request(T, tp) or '').get('subject') or {}).get('ref'))
                           for tp in ('admission', 'priority')}
                # Presentations that leave out or change the material: the item's own thinner brief (VELDO-0078's),
                # and the request's digest shown beside other text. Each is answered by olga and applied by pm.
                thin_rid, thin_shown = present_terms('THIN-79', thin_target(item_t), thin_brief(item_t),
                                                     touchpoint='admission')
                thin_answer, _ = answer(thin_shown, 'accept')
                thin_admit = bop('pm', 'admit', T, request=thin_rid)
                other_rid, other_shown = present_terms('OTHER-79', terms_t['admission'].get('target') or {'kind': 'none',
                                                       'ref': 'none', 'digest': 'none'},
                                                       'Admit it; the details do not matter.', touchpoint='admission')
                other_answer, _ = answer(other_shown, 'accept')
                other_admit = bop('pm', 'admit', T, request=other_rid)
                check('material/telegram-brief', [
                    ('the declared set is the request schema, every field', set(expected) == set(SCHEMA_FIELDS)),
                    ('the request records exactly those fields', sorted(record_t.get('content') or {}) == sorted(SCHEMA_FIELDS)),
                    ('both decisions were sent to olga\'s chat', all(texts[tp] for tp in texts)
                     and all(m['chat_id'] == chats['olga'] for m in sent_naming(T))),
                    ('every field of the request is in the bytes Telegram received, for both decisions', not missing_parts),
                    ('admission and priority are separate requests on their own touchpoints',
                     terms_t['admission'].get('touchpoint') == 'admission' and terms_t['priority'].get('touchpoint') == 'priority'
                     and current_request(T, 'admission') != current_request(T, 'priority')),
                    ('both bind the request by its digest', all(terms_t[tp].get('target') == {
                        'kind': 'admission_request', 'ref': record_t.get('uuid'), 'digest': record_t.get('digest')}
                        for tp in terms_t)),
                    ('the priority request proposes the rank shown', terms_t['priority'].get('proposal') == {'rank': 2}),
                    ('an answer to the item\'s thinner brief does not admit groomed work',
                     thin_answer.get('outcome') == 'settled' and thin_admit.get('reason') == 'invalid_input:request'),
                    ('an answer to other text beside the request\'s digest does not admit it',
                     other_answer.get('outcome') == 'settled' and other_admit.get('reason') == 'stale_subject:brief'
                     and item(T).get('state') == 'AWAITING_GROOMING')])

            # AC1, the threat model's presentation that omits a bound field: an item grooming never made an
            # admission request for is not admitted through VELDO-0078's thinner brief, and nothing is written.
            with region('material/ungroomed-thin-brief'):
                G, g_units = work_item(o_own, 'ungroomed')
                item_g = item(G)
                g_rid, g_shown = present_terms('THIN-79-G', thin_target(item_g), thin_brief(item_g), touchpoint='admission')
                g_answer, _ = answer(g_shown, 'accept')
                journal_g, version_g = journal_length(), item_g.get('version')
                g_admit = bop('pm', 'admit', G, request=g_rid)
                after_g = item(G)
                check('material/ungroomed-thin-brief', [
                    ('grooming made no admission request for the item', G is not None and not request_record(G)),
                    ('olga\'s answer to the thin brief was shown and settled',
                     g_shown.get('outcome') == 'published' and g_answer.get('outcome') == 'settled'),
                    ('the backlog refuses it by name', g_admit.get('reason') == 'missing_evidence:admission_request'),
                    ('nothing is written: the journal and the item are unchanged',
                     journal_length() == journal_g and after_g.get('version') == version_g
                     and after_g.get('state') == 'AWAITING_GROOMING' and not after_g.get('applied')),
                    ('no unit is admitted or executable', bool(g_units) and all(
                        entity('admission:' + u) is None and executable(u) == ['missing_authority:admission']
                        for u in g_units))])

            # AC1: changing any bound field refuses the earlier presentation.
            with region('material/bound-fields'):
                B, b_units = work_item(o_own, 'bound')
                gpropose('pm', B, questions=[{'id': 'q1', 'text': 'Keep the old checkout?'}])
                groom(B)
                changes = {'exclusions': ['refunds'], 'priority': {'rank': 4}, 'ceiling': {'invocations': 2},
                           'expiry': '2030-02-28T17:00:00Z', 'alternatives': ['do nothing'],
                           'questions': [{'id': 'q2', 'text': 'Keep the old checkout for a week?'}]}
                state = {'questions': [{'id': 'q1', 'text': 'Keep the old checkout?'}]}
                observed = {}
                for field in PROPOSED:
                    earlier = shown(B, 'admission')
                    earlier_priority = shown(B, 'priority')
                    before = request_record(B)
                    state[field] = changes[field]
                    made = gpropose('pm', B, **state)
                    groom(B)
                    after = request_record(B)
                    now_shown = shown(B, 'admission')
                    stale, _ = answer(earlier, 'accept')
                    stale_priority, _ = answer(earlier_priority, 'accept')
                    observed[field] = {
                        'revised': made.get('ok') and after.get('revision') == before.get('revision', 0) + 1
                        and after.get('content', {}).get(field) == changes[field],
                        'digest_changed': after.get('digest') not in (None, before.get('digest')),
                        'superseded': now_shown.get('request_version') == (earlier.get('request_version') or 0) + 1
                        and (now_shown.get('supersedes') or {}).get('presentation_id') == earlier.get('presentation_id'),
                        'refused': stale.get('reason') == 'stale_presentation'
                        and stale_priority.get('reason') == 'stale_presentation'}
                # The specification files: the owner answers the current presentation, then a file changes.
                current = shown(B, 'admission')
                settled_b, _ = answer(current, 'accept')
                spec_file('VELDO-9791', ['.veldo/policy.yaml', 'bin/veldo'])
                applied_b = apply_rulings(B)
                spec_refusal = [r for r in applied_b if r.get('touchpoint') == 'admission']
                # The fields no writer changes after grooming, each named by the live binding when it differs.
                live = {}
                if GR is not None:
                    fields_b = request_record(B).get('content') or {}
                    for field in NO_WRITER:
                        altered = dict(copy.deepcopy(fields_b), **{field: 'altered'})
                        live[field] = attempt(lambda: GR.live_problems(altered, item(B), OB.read(conn, o_own) or {},
                                                                       data_of('project:proj-a')), default=['raised'])
                spec_file('VELDO-9791', ['.veldo/policy.yaml'])
                check('material/bound-fields', [
                    ('each proposed field is its own new revision with a new digest',
                     set(observed) == set(PROPOSED) and all(o['revised'] and o['digest_changed'] for o in observed.values())),
                    ('each change revised the pending requests: a new version whose presentation supersedes the one shown',
                     all(o['superseded'] for o in observed.values())),
                    ('an answer to the earlier presentation is refused after each change',
                     all(o['refused'] for o in observed.values())),
                    ('an answer settled before a specification file changed is not applied',
                     settled_b.get('outcome') == 'settled' and spec_refusal
                     and spec_refusal[0].get('reason') in ('stale_subject:specifications', 'stale_subject:protected_paths')
                     and item(B).get('state') == 'AWAITING_GROOMING'),
                    ('every field no writer changes is named by the live binding alone when it differs',
                     set(live) == set(NO_WRITER) and all(live[f] == ['stale_subject:' + f] for f in NO_WRITER)),
                    ('no unit ran', all(executable(u) == ['missing_authority:admission'] for u in b_units))])

            # AC1 (declared falsifier): a decomposition that grew after the owner answered is not prioritized by it.
            with region('material/changed-decomposition'):
                D, d_units = work_item(o_own, 'grow')
                gpropose('pm', D)
                groom(D)
                grown = unit_entry()
                bop('pm', 'append', D, unit=grown)
                proposed_d = gpropose('pm', D)
                groomed_d = groom(D)
                priority_d = shown(D, 'priority')
                settled_d, _ = answer(priority_d, 'accept')
                late = unit_entry()
                bop('pm', 'append', D, unit=late)
                stale_d = apply_rulings(D)
                stale_units = {u: data_of(u).get('state') for u in (grown['unit'], late['unit'])}
                stale_late = executable(late['unit'])
                gpropose('pm', D)
                groom(D)
                fresh_d, _ = answer(shown(D, 'priority'), 'accept')
                applied_d = apply_rulings(D)
                check('material/changed-decomposition', [
                    ('the appended unit is groomed for priority alone, presented because his message predates it',
                     proposed_d.get('ok') and request_record(D).get('touchpoints') == ['priority']
                     and 'fresh_priority' in (groomed_d.get('reasons') or [])),
                    ('the owner answered the priority of the decomposition he was shown', settled_d.get('outcome') == 'settled'),
                    ('after another unit was appended, that answer is refused as a changed decomposition',
                     [r.get('reason') for r in stale_d] == ['stale_subject:decomposition']),
                    ('neither appended unit became executable by it',
                     stale_units == {grown['unit']: 'PLANNED', late['unit']: 'PLANNED'}
                     and stale_late == ['missing_authority:priority']),
                    ('the regroomed decomposition, answered again, prioritizes both',
                     fresh_d.get('outcome') == 'settled' and [r.get('outcome') for r in applied_d] == ['applied']
                     and executable(grown['unit']) == [] and executable(late['unit']) == [])])

            # AC2: the owner's three choices, through his authenticated answers, with his own reasoning.
            with region('authority/owner-choices'):
                results = {}
                for choice, state_after in (('accept', 'PRIORITIZED'), ('reject', 'REJECTED'),
                                            ('return_for_elaboration', 'PREPARED')):
                    X, x_units = work_item(o_own, 'choice-' + choice)
                    gpropose('pm', X, questions=[{'id': 'q1', 'text': 'Is %s right?' % choice}])
                    groom(X)
                    why = 'My reason for %s: the scope is what I asked.' % choice
                    got, _ = answer(shown(X, 'admission'), choice, rationale=why)
                    if choice == 'accept':
                        answer(shown(X, 'priority'), 'accept', rationale='Rank it as proposed.')
                    applied = apply_rulings(X)
                    held = data_of(ST.settlement_id(current_request(X, 'admission') or '', 1))
                    priority_left = data_of(current_request(X, 'priority') or '').get('state')
                    results[choice] = {'state': item(X).get('state'), 'wanted': state_after, 'rationale': held.get('rationale'),
                                       'why': why, 'ruling': held.get('ruling'), 'priority_request': priority_left,
                                       'units': [executable(u) for u in x_units], 'applied': applied}
                check('authority/owner-choices', [
                    ('each choice moves the item where it says',
                     all(r['state'] == r['wanted'] for r in results.values())),
                    ('each settlement carries the owner\'s own reasoning and his ruling',
                     all(r['rationale'] == r['why'] for r in results.values())
                     and [results[c]['ruling'] for c in ('accept', 'reject', 'return_for_elaboration')]
                     == ['approve', 'reject', 'return_for_elaboration']),
                    ('accepting both runs the work', all(u == [] for u in results['accept']['units'])),
                    ('a reject or return cancels the priority request still waiting',
                     results['reject']['priority_request'] == 'CANCELED'
                     and results['return_for_elaboration']['priority_request'] == 'CANCELED'),
                    ('rejected or returned work does not run',
                     all(u and u != [] for c in ('reject', 'return_for_elaboration') for u in results[c]['units']))])

            # AC2: the project manager cannot admit or prioritize, however it asks.
            with region('authority/pm-self-admission'):
                X, x_units = work_item(o_own, 'self')
                gpropose('pm', X, questions=[{'id': 'q1', 'text': 'May I start?'}])
                groom(X)
                pm_answer, _ = answer(shown(X, 'admission'), 'accept', who='pm', rationale='I admit my own work.')
                pm_message = admit_message(X, who='pm')
                pm_admit = service.apply(signed('pm', dict(ids, operation='admit', principal='pm', command_id=next_id('pa'),
                                                           nonce=next_id('pan'), item=X, item_version=item(X).get('version'),
                                                           request=current_request(X, 'admission'))))
                pm_rank = bop('pm', 'reprioritize', M, priority={'rank': 1})
                silent, _ = answer(shown(X, 'admission'), 'accept', rationale=' ')
                check('authority/pm-self-admission', [
                    ('its signed answer through the API edge is refused as not the owner\'s',
                     pm_answer.get('reason') == 'not_owner'),
                    ('its request to admit by his message is refused by the question it asked',
                     pm_message.get('reason') == 'not_approved:question'),
                    ('its admit naming the unanswered request is refused for want of a settlement',
                     pm_admit.get('reason') == 'missing_evidence:settlement'),
                    ('it cannot reprioritize the owner\'s work, not being a person or the owner',
                     pm_rank.get('reason') == 'not_authorized:not_a_person'),
                    ('an answer without the owner\'s own reasoning is refused', silent.get('reason') == 'missing_rationale'),
                    ('nothing was admitted and nothing runs', item(X).get('state') == 'AWAITING_GROOMING'
                     and all(executable(u) == ['missing_authority:admission'] for u in x_units)
                     and (item(M).get('priority') or {}).get('rank') == DEFAULT_RANK)])

            # AC2: admission and priority are separate authority predicates, each current.
            with region('authority/separate-predicates'):
                Z1, z1_units = work_item(o_zed, 'zed-message')
                gpropose('zed', Z1)
                groomed_z1 = groom(Z1)
                Z2, z2_units = work_item(o_zed, 'zed-asked')
                gpropose('zed', Z2, questions=[{'id': 'q1', 'text': 'Board or port?'}])
                groom(Z2)
                zed_admits, _ = answer(shown(Z2, 'admission'), 'accept', who='zed', rationale='Admit it.')
                zed_ranks, _ = answer(shown(Z2, 'priority'), 'accept', who='zed', rationale='Rank it.')
                applied_z2 = apply_rulings(Z2)
                check('authority/separate-predicates', [
                    ('zed holds admission and not priority', True),
                    ('his own message cannot admit at a priority he may not set',
                     groomed_z1.get('reason') == 'not_owner:role:priority_authority' and item(Z1).get('state') == 'AWAITING_GROOMING'),
                    ('his admission answer settles and is applied', zed_admits.get('outcome') == 'settled'
                     and item(Z2).get('state') == 'ADMITTED'),
                    ('his priority answer does not settle: the priority authority is its own predicate',
                     zed_ranks.get('reason') == 'role_not_satisfied'),
                    ('admitted without priority, nothing runs',
                     all(executable(u) == ['missing_authority:priority'] for u in z2_units)
                     and all(executable(u) == ['missing_authority:admission'] for u in z1_units)),
                    ('the admission was applied once', [r.get('touchpoint') for r in applied_z2 if r.get('outcome') == 'applied']
                     == ['admission'])])

            # AC2: no execution while a question he must answer is unanswered.
            with region('authority/questions-unresolved'):
                X, x_units = work_item(o_own, 'unresolved')
                gpropose('pm', X, questions=[{'id': 'q1', 'text': 'Apple Pay too?'}, {'id': 'q2', 'text': 'Refunds?'}])
                groom(X)
                ranked, _ = answer(shown(X, 'priority'), 'accept', rationale='Rank it, but I have not decided on it.')
                early = apply_rulings(X)
                forced = service.apply(gsigned('prioritize', X, request=current_request(X, 'priority')))
                early_state = item(X).get('state')
                waiting_units = [executable(u) for u in x_units]
                admitted, _ = answer(shown(X, 'admission'), 'accept', rationale='Apple Pay yes, refunds later.')
                later = apply_rulings(X)
                check('authority/questions-unresolved', [
                    ('the priority answer settled first', ranked.get('outcome') == 'settled'),
                    ('it is not applied while the admission with its questions is unanswered',
                     [r.get('outcome') for r in early] == ['waiting'] and early_state == 'AWAITING_GROOMING'
                     and forced.get('reason') == 'invalid_transition:AWAITING_GROOMING->PRIORITIZED'),
                    ('no unit runs meanwhile', all(u == ['missing_authority:admission'] for u in waiting_units)),
                    ('his answer to the questions admits it, and then the priority applies',
                     admitted.get('outcome') == 'settled' and [r.get('touchpoint') for r in later] == ['admission', 'priority']
                     and item(X).get('state') == 'PRIORITIZED'),
                    ('the admission names the questions his answer resolved',
                     (item(X).get('admission') or {}).get('questions') == ['q1', 'q2']),
                    ('the units run now', all(executable(u) == [] for u in x_units))])

            # AC2: the owner's later reprioritization and withdrawal are applied.
            with region('authority/reprioritize-withdraw'):
                X, x_units = work_item(o_own, 'later')
                gpropose('pm', X)
                groom(X)
                raised_rank = bop('olga', 'reprioritize', X, priority={'rank': 1})
                same_rank = bop('olga', 'reprioritize', X, priority={'rank': 1})
                ranked_x = item(X)
                ranked_units = [data_of(u).get('state') for u in x_units]
                withdrawn = bop('olga', 'cancel', X, reason='Not needed this season.')
                check('authority/reprioritize-withdraw', [
                    ('his message admitted it at the default priority', (ranked_x.get('priorities') or [{}])[0].get('rank') == DEFAULT_RANK
                     and (ranked_x.get('priorities') or [{}])[0].get('path') == 'own_message'),
                    ('his signed reprioritization is applied, the work unchanged otherwise',
                     raised_rank.get('ok') and (ranked_x.get('priority') or {}).get('rank') == 1
                     and (ranked_x.get('priority') or {}).get('previous_rank') == DEFAULT_RANK
                     and ranked_x.get('state') == 'PRIORITIZED' and ranked_units == ['READY'] * len(x_units)),
                    ('the same rank again changes nothing', same_rank.get('reason') == 'already_applied'
                     and len(ranked_x.get('priorities') or []) == 2),
                    ('his withdrawal cancels the work and its units', withdrawn.get('ok') and item(X).get('state') == 'CANCELED'
                     and all(data_of(u).get('state') == 'CANCELED' for u in x_units)
                     and all(executable(u) == ['missing_authority:backlog/CANCELED'] for u in x_units))])

            # AC3 (declared falsifier): a settled ruling authorizes only the exact parameters it was given.
            with region('ruling/parameter-binding'):
                cases3 = {}
                for field, change in (('priority', {'priority': {'rank': 1}}), ('ceiling', {'ceiling': {'invocations': 1}})):
                    X, x_units = work_item(o_own, 'param-' + field)
                    gpropose('pm', X, questions=[{'id': 'q1', 'text': 'Now?'}])
                    groom(X)
                    held_answer, held_packet = answer(shown(X, 'admission'), 'accept')
                    gpropose('pm', X, questions=[{'id': 'q1', 'text': 'Now?'}], **change)
                    reused = apply_rulings(X)
                    replayed, _ = settlement.api_answer(held_packet), None
                    tampered = copy.deepcopy(held_packet)
                    tampered['answer']['choice'] = 'reject'
                    cases3[field] = {'settled': held_answer.get('outcome') == 'settled',
                                     'reused': [r.get('reason') for r in reused if r.get('touchpoint') == 'admission'],
                                     'replayed': replayed.get('reason'), 'tampered': settlement.api_answer(tampered).get('reason'),
                                     'state': item(X).get('state'), 'units': [executable(u) for u in x_units]}
                T1, _ = work_item(o_own, 'target-a')
                gpropose('pm', T1, questions=[{'id': 'q1', 'text': 'This one?'}])
                groom(T1)
                T2, _ = work_item(o_own, 'target-b')
                gpropose('pm', T2, questions=[{'id': 'q1', 'text': 'Or this one?'}])
                groom(T2)
                answer(shown(T1, 'admission'), 'accept')
                elsewhere = service.apply(gsigned('admit', T2, request=current_request(T1, 'admission')))
                packet = gsigned('admit', T1, request=current_request(T1, 'admission'))
                beneath = copy.deepcopy(packet)
                beneath['command']['item'] = T2
                beneath['command']['item_version'] = item(T2).get('version')
                forged = service.apply(beneath)
                check('ruling/parameter-binding', [
                    ('the owner\'s admission answers settled', all(c['settled'] for c in cases3.values())),
                    ('after the priority changed, the retained ruling is refused by its digest',
                     cases3['priority']['reused'] == ['stale_subject:binding'] and cases3['priority']['state'] == 'AWAITING_GROOMING'),
                    ('after the ceiling changed, the retained ruling is refused by its digest',
                     cases3['ceiling']['reused'] == ['stale_subject:binding'] and cases3['ceiling']['state'] == 'AWAITING_GROOMING'),
                    ('the retained signed answer submitted again is refused: its request version is settled',
                     all(c['replayed'] == 'request_closed' for c in cases3.values())),
                    ('a changed ruling beneath the edge\'s signature is refused', all(c['tampered'] == 'not_authorized'
                                                                                     for c in cases3.values())),
                    ('a ruling on one item does not admit another', elsewhere.get('reason') == 'invalid_input:request'
                     and item(T2).get('state') == 'AWAITING_GROOMING'),
                    ('another target beneath a signed command is refused', forged.get('reason') == 'not_authorized'),
                    ('nothing of it runs', all(u == ['missing_authority:admission'] for c in cases3.values() for u in c['units']))])

            # AC3: an unchanged ordinary duplicate settles once.
            with region('ruling/duplicate'):
                X, x_units = work_item(o_own, 'duplicate')
                gpropose('pm', X, questions=[{'id': 'q1', 'text': 'Twice?'}])
                groom(X)
                first, packet_answer = answer(shown(X, 'admission'), 'accept')
                again = settlement.api_answer(packet_answer)
                admission_request = current_request(X, 'admission')
                packet_admit = gsigned('admit', X, request=admission_request)
                applied_once = service.apply(packet_admit)
                length = journal_length()
                applied_twice = service.apply(packet_admit)
                settlements = [s for _e, s in of_kind('request_settlement') if s.get('request_id') == admission_request]
                history = [h for h in item(X).get('history') or [] if h.get('target') == 'ADMITTED']
                check('ruling/duplicate', [
                    ('the owner\'s answer settled once', first.get('outcome') == 'settled' and len(settlements) == 1),
                    ('the same signed answer again is refused and settles nothing more', again.get('reason') == 'request_closed'),
                    ('the admission was applied', applied_once.get('ok') and item(X).get('state') == 'ADMITTED'),
                    ('the same signed command again is refused as stale and writes nothing',
                     applied_twice.get('reason') == 'stale_version' and journal_length() == length and len(history) == 1),
                    ('the one admission is bound to the one settlement',
                     (item(X).get('admission') or {}).get('settlement_id') == (settlements[0] if settlements else {}).get('settlement_id'))])

            with region('observability'):
                metrics = grooming.metrics() if grooming is not None else {}
                observations = grooming.observations if grooming is not None else []
                refusals = [o for o in observations if o['outcome'] == 'refused']
                text = json.dumps(observations) + json.dumps(service.observations)
                check('observability', [
                    ('accepted and refused grooming operations are counted',
                     metrics.get('accepted', 0) > 0 and metrics.get('refused', 0) == len(refusals) > 0),
                    ('every refusal is named and classified, never as success',
                     all(o['refusal'] and o['taxonomy'] not in (None, 'unknown_outcome') for o in refusals)),
                    ('every grooming route is observed with its reasons',
                     any(o.get('operation') == 'groom' and o.get('path') == 'own_message' for o in observations)
                     and any(o.get('operation') == 'groom' and 'question' in (o.get('reasons') or []) for o in observations)),
                    ('the admission requests and the presented requests waiting for the owner are exposed',
                     metrics.get('requests', 0) > 0 and (metrics.get('pending') or {}).get('presented', 0) > 0),
                    ('observations carry no question, rationale or signature text',
                     'Should the pass show' not in text and 'I have read' not in text and 'SSH SIGNATURE' not in text)])
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for connection in connections:
                connection.close()
    if raised:
        print('  %sdetail: regions that raised: %s' % (PREFIX, raised))


_v79_started = __import__('time').monotonic()
_v79_suite()
print('VELDO-0079 suite seconds: %.3f' % (__import__('time').monotonic() - _v79_started))
