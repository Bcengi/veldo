"""VELDO-0085 real publication, backlog admission and dependency eligibility.

Generated fixture keys only. SQLite, Git, OpenSSH and loopback HTTP; no live service.
Every row drives the production writer and reports once. A tree without the publication
service reports each behavior assertion false, without substituting authority records.
"""

def _v85_suite():
    import contextlib
    import ast
    import copy
    import http.server
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import types

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {name: path for name, path in (
        ('control_alias.py', ROOT / ".veldo" / "control_alias.py"),
        ('control_backlog.py', ROOT / ".veldo" / "control_backlog.py"),
        ('control_eligibility.py', ROOT / ".veldo" / "control_eligibility.py"),
        ('control_decomposition.py', ROOT / ".veldo" / "control_decomposition.py"),
        ('control_decomposition_binding.py', ROOT / ".veldo" / "control_decomposition_binding.py"),
        ('init_scaffold.py', ROOT / ".veldo" / "init_scaffold.py"))}
    PREFIX = 'VELDO-0085 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    # AC1's declared set: the four kinds of work, and the claim entries each is driven through.
    AC1_SET = ('intake-only', 'prepared', 'admitted-without-priority', 'prioritized')
    ENTRIES = ('offer', 'receiver', 'task-ledger', 'task-authority')
    # AC3's declared set of DONE attempts.
    # The grooming proposal's expiry (VELDO-0079), beyond every run of this suite.
    EXPIRY = '2030-01-31T17:00:00Z'
    AC3_SET = ('path-only output', 'canceled attempt', 'missing required receipt', 'incomplete landing receipt',
               'complete receipts or an authorized alternative')

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

    def attempt(fn):
        """An entry's answer, or ('error', <type>) when the entry cannot even be asked (the red tree)."""
        try:
            return fn()
        except Exception as error:  # noqa: BLE001 - an entry that cannot answer is a failed part
            return ('error', type(error).__name__)

    def message(st, sender, chat, text, reply_to=None):
        with st['lock']:
            st['next'] += 1
            st['tick'] += 1
            m = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791300000 + st['tick'],
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
            if name != 'bot78':
                return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
            if method == 'getMe':
                return self._answer(200, {'ok': True, 'result': dict(st['user'], can_join_groups=True)})
            if method == 'getUpdates':
                return self._answer(200, {'ok': True, 'result': []})
            if method == 'sendMessage':
                chat = {'id': body.get('chat_id'), 'type': 'private'}
                reply = (body.get('reply_parameters') or {}).get('message_id')
                st['sent'].append(body.get('chat_id'))
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
    with tempfile.TemporaryDirectory(prefix='v78-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        try:
            claims = load('v78_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v78_keys', mods / 'control_keys.py')
            I = load('v78_inbox', mods / 'control_assignment.py')
            P = load('v78_projection', mods / 'control_channel_projection.py')
            V = load('v78_presentation', mods / 'control_channel_presentation.py')
            EV = load('v78_attribution', mods / 'control_channel_attribution.py')
            E = load('v78_enrollment', mods / 'control_channel_enrollment.py')
            ST = load('v78_settlement', mods / 'control_request_settlement.py')
            IN = load('v78_intake', mods / 'control_intake.py')
            PJ = load('v78_project', mods / 'control_project.py')
            OB = load('v78_objective', mods / 'control_objective.py')
            FR = load('v78_frontier', mods / 'frontier.py')
            TS = load('v78_tasks', mods / 'tasks.py')
            CLF = load('v78_claim', mods / 'claim.py')
            VAL = load('v78_validate', mods / 'validate.py')
            contract = load('v78_contract', mods / 'entity_contract.py')
            CB = load('v78_backlog', mods / 'control_backlog.py') if (mods / 'control_backlog.py').is_file() else None
            CYC = load('v78_cycle', mods / 'control_workflow_cycle.py')
            GM = load('v78_grooming', mods / 'control_grooming.py') if (mods / 'control_grooming.py').is_file() else None
            DOMAIN, REPO = 'domain-78', 'repository-78'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-78')

            keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
            for d in (keys, protected, edge_dir):
                d.mkdir(mode=0o700)
            people = ('steward', 'olga', 'zed')
            services = ('pm', 'grooming', 'api-edge', 'builder', 'builder-b', 'closer')
            keyfile = {who: keys / who for who in ('authority',) + people + services}
            keyfile['edge'] = protected / 'edge-telegram'
            keyfile['edge-auth'] = edge_dir / 'edge-auth'
            public = {}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v78-' + who, '-f', str(path)],
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
                                                  'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                                  'independence_group': 'steward', 'scope': '*'})
            deciders = ['project_owner', 'admission_authority', 'priority_authority']
            enroll('olga', 'person', deciders, ['proj-a'])
            enroll('zed', 'person', deciders, ['proj-a'])
            enroll('pm', 'service', [], ['proj-a'])
            # VELDO-0079's grooming service, which opens and presents the admission and priority requests.
            enroll('grooming', 'service', [], ['proj-a'])
            enroll('api-edge', 'service', [], ['proj-a'])
            enroll('builder', 'service', [], [REPO])
            enroll('builder-b', 'service', [], [REPO])
            # A worker that stops for a person about its claimed unit (VELDO-0133): the project and the repository.
            enroll('closer', 'service', [], ['proj-a', REPO])

            def fixture(eid, kind, data):
                row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: row[0] if row else 0}, artifact_digests=[],
                                            nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

            chats = {'olga': 5780001, 'zed': 5780002}
            for who, chat in chats.items():
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))
            enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
            edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                           'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': ['proj-a']}
            edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                            'target': 'channel:telegram_chat', 'parameters': edge_params, 'artifact_digests': [],
                            'expected_versions': {}}
            edge_env = envelope(edge_command, 'steward')
            enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                             sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))

            api = {'tick': 0, 'next': 9000, 'messages': {}, 'sent': [], 'lock': threading.Lock(),
                   'user': {'id': 8000000078, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_backlog_bot'}}
            handler = type('V78Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]

            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot78'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot78'), conn, 'authority',
                                   journal_sign, 'telegram-edge', lambda m: sign_as('edge', m, 'veldo-command'))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=['proj-a'], api_edge='api-edge',
                               journal_signer='authority', sign=journal_sign)
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)
            receiver = claims.Receiver(conn, ids, 'authority', journal_sign)

            def signed(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            activation = projects.apply(signed('olga', dict(
                ids, operation='activate', project='proj-a', principal='olga', command_id=next_id('pc'), nonce=next_id('pn'),
                owner='olga', charter={'purpose': 'Sell passes to travelers.'}, execution_repository=REPO,
                authority_policy={'objective_acceptance': ['project_owner'], 'admission': ['admission_authority']},
                coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))

            # The workspace: ready standalone specs the frontier reads, the task set, declared outputs.
            work = base / 'work'
            (work / 'specs').mkdir(parents=True)
            (work / '.veldo' / 'tasks').mkdir(parents=True)
            (work / 'out').mkdir()
            ledger = base / 'ledger'
            ledger.mkdir()
            # Every unit's primary specification has its file: grooming binds each one's digest (VELDO-0079).
            SPECS = ('VELDO-9781', 'VELDO-9782', 'VELDO-9783', 'VELDO-9784', 'VELDO-9785', 'VELDO-9786', 'VELDO-9787',
                     'VELDO-9788', 'VELDO-9789', 'VELDO-9791', 'VELDO-9792')
            for sid in SPECS:
                (work / 'specs' / ('%s-backlog-fixture.md' % sid)).write_text('\n'.join([
                    '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Backlog fixture unit', 'status: ready',
                    'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                    'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                    'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
            TASKS = ('TASK-78-1', 'TASK-78-2', 'TASK-78-3', 'TASK-78-4', 'TASK-78-grow')
            lines = ['schema: veldo.tasks/v1', 'id: TASKSET-78', 'version: 1', 'tasks:']
            for tid in TASKS:
                lines += ['  - id: ' + tid, '    kind: review', '    target: specs/' + tid + '.md',
                          '    produces: out/' + tid + '.md']
            (work / '.veldo' / 'tasks' / 'backlog.yaml').write_text('\n'.join(lines) + '\n')
            tdir = work / '.veldo' / 'tasks'

            reader = S.open_store(str(db), mode='r')
            connections.append(reader)
            events = []
            gate = FR.EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPO, workspace=str(work),
                              observe=events.append)

            service = (CB.Backlog(S, CM, conn, ids, 'authority', journal_sign, workspace=str(work))
                       if CB is not None else None)
            missing = {'ok': False, 'reason': 'no_backlog_service'}
            grooming = (GM.Grooming(S, CM, conn, ids, 'authority', journal_sign, backlog=CB, service=service, assignment=I,
                                    inbox=inbox, presenter=presenter, settlement=settlement,
                                    requester=('grooming', lambda m: sign_as('grooming', m)), workspace=str(work))
                        if GM is not None and service is not None else None)

            def entity(eid):
                row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}

            def data_of(eid):
                return (entity(eid) or {}).get('data') or {}

            def item(iid):
                row = entity(iid) if isinstance(iid, str) else None
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'backlog_item' else {}

            def of_kind(kind):
                return [(eid, json.loads(t)) for eid, t in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id',
                                                                       (kind,))]

            def bsend(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('bc'), nonce=next_id('bn'), **fields)
                return service.apply(signed(who, body)) if service is not None else dict(missing)

            def bop(who, op, iid, **fields):
                return bsend(who, op, item=iid, item_version=item(iid).get('version'), **fields)

            def present(alias, target, brief, owner='olga', touchpoint='decision_disposition', proposal=None):
                """The requester's terms, the inbox request with its framing, and its presentation."""
                terms = settlement.terms(signed('pm', dict(ids, operation='terms', terms=alias, principal='pm',
                                                           command_id=next_id('terms'), nonce=next_id('tn'),
                                                           touchpoint=touchpoint, target=target, proposal=proposal,
                                                           required_roles=[], quorum=None)))
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

            def answer(receipt, choice, who='olga'):
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('ans'),
                            principal=who, request_id=receipt.get('request_id'), request_version=receipt.get('request_version'),
                            presentation_id=receipt.get('presentation_id'), presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice,
                            rationale='I have read the item, its units and their scope.')
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def request_record(iid):
                """The item's VELDO-0079 admission request, read by grooming's own reader, or {}."""
                return (GM.read(conn, GM.GR.request_id(iid)) or {}) if GM is not None else {}

            def gpropose(iid, rank=1):
                """pm proposes the item's grooming at `rank` (VELDO-0079): a new admission request revision when
                the material changed, nothing written when it did not."""
                if grooming is None:
                    return dict(missing, reason='no_grooming_service')
                body = dict(ids, operation='propose', principal='pm', command_id=next_id('gc'), nonce=next_id('gn'),
                            item=iid, item_version=item(iid).get('version'),
                            proposal={'priority': {'rank': rank}, 'ceiling': {'invocations': 3}, 'expiry': EXPIRY})
                return grooming.apply(signed('pm', body))

            def groom(iid, rank=1):
                """Grooming asks the owner what the item's current revision needs: proposed, then each decision
                presented as its own request on Telegram."""
                gpropose(iid, rank)
                return grooming.groom(iid) if grooming is not None else dict(missing, reason='no_grooming_service')

            def asked(iid, touchpoint):
                """(request id, its current presentation) of grooming's latest request for `touchpoint`."""
                record = request_record(iid)
                found = grooming.requests(record, touchpoint) if grooming is not None and record else []
                rid = found[-1][1] if found else None
                return rid, (presenter.current(rid) or {}) if rid else {}

            asked_as = {}

            def admit(iid, alias, choice='accept'):
                """Grooming asks for the item's admission and priority; the owner answers the admission, which pm
                applies: (request, settled, applied)."""
                groom(iid)
                rid, receipt = asked(iid, 'admission')
                asked_as[alias] = rid
                return rid, answer(receipt, choice), bop('pm', 'admit', iid, request=rid)

            def prioritize(iid, alias, choice='accept'):
                """The owner answers grooming's priority request (rank 1), which pm applies. Units appended to
                prioritized work are groomed afresh for their priority first."""
                if item(iid).get('state') in ('PRIORITIZED', 'ACTIVE'):
                    groom(iid)
                rid, receipt = asked(iid, 'priority')
                asked_as[alias] = rid
                return rid, answer(receipt, choice), bop('pm', 'prioritize', iid, request=rid)

            def unit_entry(name, produces=None):
                entry = dict(unit=name, specification=name if name.startswith('VELDO-') else 'VELDO-9785',
                             scope=['checkout'], requirements=[], eligible_holders=['builder', 'builder-b'])
                if produces:
                    entry['produces'] = produces
                return entry

            # The accepted objective the backlog items are taken from, and its RAW features.
            body = {'schema': IN.API_SCHEMA, 'domain': DOMAIN, 'request_id': 'api-78-2', 'edge': 'api-edge',
                    'principal': 'olga', 'text': 'For proj-a: travelers can buy a pass in two taps.', 'project': None,
                    'clarifies': None}
            m1 = intake.receive('api_request', {'request': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def osend(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('oc'), nonce=next_id('on'), **fields)
                return objectives.apply(signed(who, body))

            objectives = OB.Objectives(S, CM, conn, ids, 'authority', journal_sign, workspace=str(work))
            proposed = osend('pm', 'propose', proposal=m1.get('proposal_id'), outcome='A traveler buys a pass in two taps.',
                             scope=['checkout', 'payments'], authority={'acceptor': 'olga', 'assessor': 'zed'},
                             evidence_requirements=[{'id': 'outcome', 'kind': 'gate_observation'}])
            o1 = proposed.get('objective_id')
            record = OB.read(conn, o1) or {}
            rid_o, receipt_o = present('OBJ-78', OB.acceptance_target(record), OB.acceptance_brief(record))
            answer(receipt_o, 'accept')
            accepted = osend('pm', 'accept', objective=o1, objective_version=(OB.read(conn, o1) or {}).get('version'),
                             request=rid_o)
            features = {}
            for name in ('intake', 'prepared', 'admitted', 'prioritized', 'main', 'rejected', 'returned', 'closed', 'running'):
                made = osend('pm', 'propose_feature', objective=o1, objective_version=(OB.read(conn, o1) or {}).get('version'),
                             feature='f-' + name, title='Feature %s' % name, scope=['checkout'])
                features[name] = made.get('feature_id')

            def take(name, who='pm', work_class='PRODUCT_CHANGE'):
                result = bsend(who, 'take', feature=features[name], work_class=work_class)
                return result, result.get('item_id') or (CB.item_id(features[name]) if CB is not None else 'backlog:' + name)

            labels = ('fields/invalid-id-no-artifact', 'binding/one-owner', 'priority/fresh-growth',
                      'aliases/authority-counter', 'publication/other-process', 'publication/stale-input',
                      'dependencies/eligibility', 'install/assets', 'refusals/service-class',
                      'dependencies/current-specification', 'dependencies/prepare-mismatch', 'publication/concurrent-current')
            if not (mods / 'control_decomposition.py').is_file():
                for label in labels:
                    check(label, [('publication service exists', False)])
                return
            DP = load('v85_decomposition', mods / 'control_decomposition.py')
            AL = load('v85_alias', mods / 'control_alias.py')
            DOC = load('v85_document', mods / 'control_document.py')
            RS = load('v85_readset', mods / 'control_readset.py')
            EN = load('v85_enrollment', mods / 'control_enrollment.py')
            git = AL._git_process

            def g(*args):
                return git.check_output(['git', '-C', str(work), *args],
                                        identity=('Fixture', 'fixture@example.test')).decode().strip()

            g('init', '-q')
            historical = work / 'specs' / 'WARP-0012-existing.md'
            historical.write_text('# Historical identity\n')
            g('add', '.')
            g('commit', '-qm', 'Fixture specifications')
            before_files = {p.name: p.read_bytes() for p in (work / 'specs').iterdir()}
            allocations = AL.attach(S, conn, DOMAIN, {REPO: str(work)})
            signing = dict(signer='authority', sign=journal_sign, authority_generation=1)
            revisions = RS.attach_revisions(S, conn, DOMAIN, {REPO: str(work)})
            revisions.accept('revision/v85', REPO, g('rev-parse', 'HEAD'), 'pm', **signing)
            EN.enroll(work, DOMAIN, ids['store_uuid'], str(db), 'fixture-host', 1,
                      journal_sign, 'olga', '2026-09-27T00:00:00Z', repository_uuid=REPO)
            allowed = base / 'allowed-enrollment'
            allowed.write_text('authority ' + public['authority'] + '\n')

            def verify(body, signature):
                sig = base / 'enrollment.sig'
                sig.write_text(signature)
                return subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'authority',
                                       '-n', 'veldo-journal', '-s', str(sig)], input=body,
                                      capture_output=True, timeout=10).returncode == 0

            publisher = DOC.Publisher(allocations, work, verify=verify, host_identity='fixture-host')
            allocations.enable_kind(dict(request_id='kind-v85', principal='olga', repository_uuid=REPO,
                                         kind='specification', prefix='VELDO', width=4,
                                         path_template='specs/{alias}-{slug}.md', revision_id='revision/v85'), **signing)
            decomposition = DP.Decomposition(service, allocations, publisher)

            def raw(name, deps=(), revision='1', role='specification/main'):
                return dict(unit=name, scope=['checkout'], requirements=[], eligible_holders=['builder'],
                            source={'system': 'pm', 'id': name, 'revision': revision}, role=role,
                            front=dict(title='Buy a pass', status='ready', risk='standard', owner='olga',
                                       human_approval='not_required', lane='standalone', protected_paths=[],
                                       acceptance_criteria=[{'id': 'AC1', 'text': 'A traveler buys a pass.'}],
                                       required_evidence=['unit'], rollback='Revert the change.'),
                            body='\n## Intent\n\nComplete accepted bytes, including trailing spaces.  \n',
                            dependencies=list(deps))

            def publish(iid, entry):
                command = dict(ids, operation='publish_decomposition', principal='pm', command_id=next_id('pub'),
                               item=iid, item_version=item(iid).get('version'), unit=entry)
                return decomposition.publish(signed('pm', command))

            def counter():
                return allocations.current(AL.kind_id(REPO, 'specification'))[1]['next']

            def judged(uid):
                return gate.decide('claim', uid)

            with region('fields/invalid-id-no-artifact'):
                _, invalid_item = take('intake')
                first = counter()
                snapshot = S.table_snapshot(conn)
                files = sorted(p.name for p in (work / 'specs').iterdir())
                invalid = []
                for uid in ('../bad', 'unit/bad', 'bad unit', ''):
                    invalid.append(publish(invalid_item, raw(uid)))
                for field in ('unit', 'scope', 'requirements', 'eligible_holders', 'source', 'role', 'front', 'body', 'dependencies'):
                    entry = raw('UNIT-85-fields')
                    entry.pop(field)
                    invalid.append(publish(invalid_item, entry))
                check('fields/invalid-id-no-artifact', [
                    ('all required fields and invalid IDs refuse', all(not r.get('ok') for r in invalid)),
                    ('invalid IDs are named', all(r.get('reason') == 'invalid_input:unit_id' for r in invalid[:4])),
                    ('no reservation or document written', S.table_snapshot(conn) == snapshot and counter() == first),
                    ('no materialized artifact', sorted(p.name for p in (work / 'specs').iterdir()) == files)])

            with region('aliases/authority-counter'):
                _, aliases_item = take('prepared')
                start = counter()
                base_entry = raw('UNIT-85-alias')
                a = publish(aliases_item, base_entry)
                again = publish(aliases_item, base_entry)
                revised = publish(aliases_item, raw('UNIT-85-alias', revision='2'))
                role = publish(aliases_item, raw('UNIT-85-alias', role='specification/other'))
                other = publish(aliases_item, raw('UNIT-85-other'))
                answers = [a, revised, role, other]
                mapping = []
                for result in answers:
                    entry = result.get('unit') or {}
                    bound = entry.get('document') or {}
                    key = AL.source_key(REPO, bound.get('source', {}), bound.get('role')) if bound else None
                    mapping.append(allocations.current(AL.source_id(REPO, key))[1] if key else {})
                check('aliases/authority-counter', [
                    ('identical source reuses', again.get('reused') and again.get('unit') == a.get('unit')),
                    ('distinct tuples get the next authority aliases',
                     [r.get('unit', {}).get('specification') for r in answers] == ['VELDO-%04d' % (start+i) for i in range(4)]),
                    ('counter advanced without checkout history commits', counter() == start + 4),
                    ('each source maps exactly', all(m and m['alias'] == r['unit']['specification'] and
                                                    m['source'] == r['unit']['document']['source'] and
                                                    m['role'] == r['unit']['document']['role'] for m, r in zip(mapping, answers))),
                    ('historical VELDO and WARP identities unchanged',
                     all((work / 'specs' / name).read_bytes() == body for name, body in before_files.items()))])

            with region('binding/one-owner', 'priority/fresh-growth', 'dependencies/eligibility', 'publication/other-process'):
                _, main_item = take('main')
                first = publish(main_item, raw('UNIT-85-first'))
                second = publish(main_item, raw('UNIT-85-second', ['UNIT-85-first']))
                if not first.get('ok') or not second.get('ok'):
                    for label in ('binding/one-owner', 'priority/fresh-growth', 'dependencies/eligibility', 'publication/other-process'):
                        check(label, [('prerequisite publications accepted', False)])
                else:
                    entries = [r.get('unit', {}) for r in (first, second)]
                    _, foreign_item = take('rejected')
                    combined = bop('pm', 'prepare', foreign_item, units=[entries[0]])
                    combined_publication = publish([main_item, foreign_item], raw('UNIT-85-combined'))
                    # An accepted primary revision belongs to exactly its declared unit.
                    dup = dict(entries[0], unit='UNIT-85-duplicate')
                    duplicate = bop('pm', 'prepare', main_item, units=[entries[0], dup])
                    prepared = bop('pm', 'prepare', main_item, units=entries)
                    bop('pm', 'request_grooming', main_item)
                    admission = admit(main_item, 'admit-85')[2]
                    priority = prioritize(main_item, 'priority-85')[2]
                    check('binding/one-owner', [
                        ('accepted preparation and owner admission', prepared.get('ok') and admission.get('ok')),
                        ('authority cannot combine across items', not combined.get('ok') and item(foreign_item).get('state') == 'RAW'
                         and combined_publication.get('reason') == 'invalid_input:backlog_item'),
                        ('duplicate primary revisions refused', not duplicate.get('ok')),
                        ('one primary revision and item per unit', all(data_of(e['unit']).get('backlog_item_uuid') == main_item
                            and data_of(e['unit']).get('specification_document') == e.get('document')
                            and data_of(e['unit']).get('primary_specification') == {'alias': e['specification'], 'revision': 1}
                            for e in entries))])
                    gate_second = judged('UNIT-85-second')
                    check('dependencies/eligibility', [
                        ('priority accepted', priority.get('ok')),
                        ('generated dependency reached the unit', data_of('UNIT-85-second').get('depends_on') == ['UNIT-85-first']),
                        ('eligibility consumes and refuses unresolved dependency',
                         'unresolved_dependency:UNIT-85-first' in gate_second.get('refusals', [])),
                        ('specification declares its generated dependency', CB.GR.Y.front_matter(allocations.current(AL.version_id(REPO,
                             entries[1]['specification'], 1))[1]['content']).get('depends_on')
                             == [entries[0]['specification']]),
                        ('independent unit eligible', judged('UNIT-85-first').get('eligible'))])
                    third = publish(main_item, raw('UNIT-85-third'))
                    appended = bop('pm', 'append', main_item, unit=third.get('unit', {}))
                    before = judged('UNIT-85-third')
                    still = judged('UNIT-85-first')
                    fresh = prioritize(main_item, 'priority-85-fresh')[2]
                    check('priority/fresh-growth', [
                        ('append remains planned until fresh priority', appended.get('ok') and
                         'missing_authority:priority' in before.get('refusals', [])),
                        ('already approved sibling continues', still.get('eligible')),
                        ('renewed priority makes new unit executable', fresh.get('ok') and judged('UNIT-85-third').get('eligible'))])
                    child = _V85_CHILD
                    proc = subprocess.run([sys.executable, '-B', '-c', child, str(mods), str(db), REPO, str(work),
                                           json.dumps([e['unit'] for e in entries])], capture_output=True, text=True, timeout=30)
                    seen = json.loads(proc.stdout) if proc.returncode == 0 else {}
                    check('publication/other-process', [
                        ('reader process completed', proc.returncode == 0),
                        ('exact versions, digests, ownership and complete bytes', all(
                            seen.get(e['unit'], {}).get('binding') == e.get('document') and
                            seen[e['unit']]['owner'] == main_item and not seen[e['unit']]['errors'] and
                            bytes.fromhex(seen[e['unit']]['body']) == allocations.current(
                                AL.version_id(REPO, e['specification'], 1))[1]['content'].encode()
                            for e in entries)),
                        ('dependency edge visible in another process', seen.get('UNIT-85-second', {}).get('dependencies') == ['UNIT-85-first'])])

            with region('refusals/service-class'):
                before_count = decomposition.counts['refused']
                before_reasons = dict(getattr(decomposition, 'refused_by_reason', {}))
                before_observations = len(decomposition.observations)
                bad_spec = raw('UNIT-85-bad-spec')
                bad_spec['front']['id'] = '../invalid'
                cases = [(dict(raw('UNIT-85-scope'), scope=['payments']), 'out_of_scope:payments'),
                         (raw('UNIT-85-first'), 'already_exists:UNIT-85-first'),
                         (dict(raw('UNIT-85-empty'), eligible_holders=[]), 'invalid_input:unit'),
                         (bad_spec, 'invalid_input:specification')]
                results = [attempt(lambda entry=entry: publish(main_item, entry)) for entry, _ in cases]
                observations = decomposition.observations[before_observations:]
                check('refusals/service-class', [
                    ('each service refusal returns by name', all(isinstance(r, dict) and r == {'ok': False, 'reason': reason}
                        for r, (_, reason) in zip(results, cases))),
                    ('every refusal observed', [o.get('refusal') for o in observations] == [r for _, r in cases]
                     and all(o.get('outcome') == 'refused' for o in observations)),
                    ('total refused increments', decomposition.counts['refused'] == before_count + len(cases)),
                    ('reason counts increment', all(getattr(decomposition, 'refused_by_reason', {}).get(reason, 0)
                        == before_reasons.get(reason, 0) + 1 for _, reason in cases))])

            with region('dependencies/current-specification', 'dependencies/prepare-mismatch'):
                _, twin_item = take('closed')
                old = publish(twin_item, raw('UNIT-85-twin'))
                new = publish(twin_item, raw('UNIT-85-twin', revision='2'))
                dependent = publish(twin_item, raw('UNIT-85-twin-dependent', ['UNIT-85-twin']))
                old_alias = old.get('unit', {}).get('specification')
                new_alias = new.get('unit', {}).get('specification')
                dep_alias = dependent.get('unit', {}).get('specification')
                dep_doc = allocations.current(AL.version_id(REPO, dep_alias, 1))[1] or {}
                check('dependencies/current-specification', [
                    ('all twin publications accepted', all(r.get('ok') for r in (old, new, dependent))),
                    ('old head names superseding alias', (allocations.current(AL.head_id(REPO, old_alias))[1] or {}).get('superseded_by') == new_alias),
                    ('dependent names only current specification', (CB.GR.Y.front_matter(dep_doc.get('content', '')) or {}).get('depends_on') == [new_alias])])
                latest = publish(twin_item, raw('UNIT-85-twin', revision='3'))
                stale_prepare = attempt(lambda: bop('pm', 'prepare', twin_item,
                    units=[latest.get('unit', {}), dependent.get('unit', {})]))
                check('dependencies/prepare-mismatch', [
                    ('new dependency revision accepted', latest.get('ok')),
                    ('prepare refuses stale dependency by name', isinstance(stale_prepare, dict) and
                     stale_prepare.get('reason') == 'binding_mismatch:dependency_specification'),
                    ('refused prepare creates no units', data_of('UNIT-85-twin') == {} and data_of('UNIT-85-twin-dependent') == {})])

            with region('publication/concurrent-current'):
                _, concurrent_item = take('running')
                packets = []
                for revision in ('a', 'b'):
                    packets.append(signed('pm', dict(ids, operation='publish_decomposition', principal='pm',
                        command_id=next_id('concurrent'), item=concurrent_item,
                        item_version=item(concurrent_item)['version'], unit=raw('UNIT-85-concurrent', revision=revision))))
                barrier = threading.Barrier(2)
                verify_lock = threading.Lock()
                results = [None, None]

                def concurrent_publish(index):
                    connection = None
                    try:
                        connection = S.open_store(str(db))
                        backlog = CB.Backlog(S, CM, connection, ids, 'authority', journal_sign, workspace=str(work))
                        allocator = AL.attach(S, connection, DOMAIN, {REPO: str(work)})
                        with verify_lock:
                            materializer = DOC.Publisher(allocator, work, verify=verify, host_identity='fixture-host')
                        author = allocator.author_allocation
                        first_attempt = [True]

                        def synchronized(*args, **kwargs):
                            plan = author(*args, **kwargs)
                            if first_attempt[0]:
                                first_attempt[0] = False
                                barrier.wait(timeout=20)
                            return plan

                        allocator.author_allocation = synchronized
                        results[index] = DP.Decomposition(backlog, allocator, materializer).publish(packets[index])
                    except Exception as error:
                        results[index] = ('error', type(error).__name__)
                        barrier.abort()
                    finally:
                        if connection is not None:
                            connection.close()

                workers = [threading.Thread(target=concurrent_publish, args=(i,)) for i in range(2)]
                for worker in workers:
                    worker.start()
                for worker in workers:
                    worker.join(timeout=30)
                heads = []
                for identity, version, text in conn.execute("SELECT id, version, data FROM entities WHERE kind='accepted_document'"):
                    head = json.loads(text)
                    if head.get('repository_uuid') != REPO:
                        continue
                    document = allocations.current(AL.version_id(REPO, head['alias'], head['version']))[1] or {}
                    meta = (CB.GR.Y.front_matter(document.get('content', '')) or {}).get('decomposition', {})
                    if meta.get('unit') == 'UNIT-85-concurrent':
                        heads.append((identity, version, head))
                current = [head for _, _, head in heads if not head.get('superseded_by')]
                check('publication/concurrent-current', [
                    ('both callers return named outcomes', all(isinstance(r, dict) and
                        (r.get('ok') or r.get('reason') == 'stale_subject:specification_superseded') for r in results)),
                    ('both source revisions published', len(heads) == 2 and all(
                        (allocations.current(AL.publication_id(REPO, h['alias'], 1))[1] or {}).get('state') == 'published'
                        for _, _, h in heads)),
                    ('exactly one current specification', len(current) == 1),
                    ('earlier commit superseded by later', len(current) == 1 and all(
                        h == current[0] or h.get('superseded_by') == current[0]['alias'] for _, _, h in heads)),
                    ('workers reaped', not any(worker.is_alive() for worker in workers))])

            with region('publication/stale-input'):
                if not first.get('ok'):
                    check('publication/stale-input', [('prerequisite publication accepted', False)])
                else:
                    bound = first.get('unit', {}).get('document', {})
                    path = work / bound.get('path', 'absent')
                    accepted_bytes = path.read_bytes()
                    path.write_bytes(accepted_bytes + b'Changed after priority.\n')
                    stale = judged('UNIT-85-first')
                    path.write_bytes(accepted_bytes)
                    _, stale_item = take('admitted')
                    proposed = publish(stale_item, raw('UNIT-85-stale'))
                    if not proposed.get('ok'):
                        check('publication/stale-input', [('stale fixture publication accepted', False)])
                    else:
                        entry = proposed.get('unit', {})
                        bp = work / entry.get('document', {}).get('path', 'absent')
                        original = bp.read_bytes()
                        bp.write_bytes(original + b'Unaccepted local edit.\n')
                        refused = bop('pm', 'prepare', stale_item, units=[entry])
                        bp.write_bytes(original)
                        pending = allocations.edit(dict(request_id='pending-v85', principal='pm', repository_uuid=REPO,
                            workspace=str(work), alias=entry['specification'], expected_version=1,
                            expected_digest=entry['document']['digest'], source={'system':'pm','id':'pending','revision':'2'},
                            role='specification/main', content=original + b'Accepted but unpublished.\n'), **signing)
                        unpublished = bop('pm', 'prepare', stale_item, units=[entry])
                        _, admission_item = take('returned')
                        admission_doc = publish(admission_item, raw('UNIT-85-admission'))
                        admission_entry = admission_doc.get('unit', {})
                        bop('pm', 'prepare', admission_item, units=[admission_entry])
                        bop('pm', 'request_grooming', admission_item)
                        ap = work / admission_entry['document']['path']
                        original_admission = ap.read_bytes()
                        ap.write_bytes(original_admission + b'Local bytes before grooming.\n')
                        groom(admission_item)
                        rid, shown_receipt = asked(admission_item, 'admission')
                        answer(shown_receipt, 'accept')
                        stale_admission = bop('pm', 'admit', admission_item, request=rid)
                        ap.write_bytes(original_admission)
                        check('publication/stale-input', [
                            ('stale executable bytes refused', 'stale_subject:specification_bytes' in stale.get('refusals', [])),
                            ('local edit cannot be prepared', not refused.get('ok') and refused.get('reason') == 'stale_subject:specification_bytes'),
                            ('unpublished newest version cannot be prepared', pending.get('version') == 2 and
                             unpublished.get('reason') == 'missing_evidence:specification_publication'),
                            ('grooming local bytes cannot confer publication authority',
                             stale_admission.get('reason') == 'stale_subject:specification_bytes' and
                             data_of('admission:UNIT-85-admission') == {}),
                            ('no admission or execution input created', data_of('UNIT-85-stale') == {})])

            with region('install/assets'):
                scaffold = load('v85_scaffold', mods / 'init_scaffold.py')
                names = ('control_decomposition.py', 'control_decomposition_binding.py')
                for name in names:
                    scaffold._lay(ROOT / 'engine' / '.veldo' / name, base / 'laid' / name, '.veldo/' + name, [], [])
                check('install/assets', [('registered and exact installed assets', all('.veldo/' + n in scaffold._FILES and
                    (base / 'laid' / n).read_bytes() == (ROOT / '.veldo' / n).read_bytes() for n in names)),
                    ('engine and installed modules identical', all((ROOT / 'engine' / '.veldo' / n).read_bytes() ==
                        (ROOT / '.veldo' / n).read_bytes() for n in PRODUCTION))])
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for connection in connections:
                connection.close()
    if raised:
        print('  %sdetail: regions that raised: %s' % (PREFIX, raised))


_V85_CHILD = r'''import importlib.util, json, sys
from pathlib import Path
def load(name):
    s=importlib.util.spec_from_file_location(name, Path(sys.argv[1])/(name+'.py'))
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S=load('control_store'); B=load('control_decomposition_binding')
c=S.open_store(sys.argv[2], mode='r'); out={}
for uid in json.loads(sys.argv[5]):
    u=B.row(c,uid); expected=u['specification_document']
    bound, errors=B.binding(c,sys.argv[3],expected['alias'],sys.argv[4])
    out[uid]={'binding':bound,'errors':errors,'owner':u['backlog_item_uuid'],'dependencies':u['depends_on'],
              'body':(Path(sys.argv[4])/expected['path']).read_bytes().hex()}
print(json.dumps(out)); c.close()

'''

_v85_suite()
