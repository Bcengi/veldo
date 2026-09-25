"""VELDO-0077: objective acceptance and signed outcome assessment over a real signed store.

Run: python3 scripts/selftest.py --suite 72_veldo_0077_objectives

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy every
service loads; the production anchor below is the registered mutation driver's seam, so a mutation of
control_objective.py reaches the service and the reader in another process. Real SQLite store with
OpenSSH command, journal and API signatures; the owner's messages reach the real VELDO-0126 Intake as
requests the API edge signed; every acceptance is a real VELDO-0064 request presented by the VELDO-0065
presenter over a loopback Bot API (real HTTP in the platform's shapes, no network, no real token),
answered through the authenticated API edge and settled by the real VELDO-0068 settlement; the project
is activated by its owner's signed VELDO-0076 command; evidence is gate observations of real check
processes kept by the VELDO-0050 proof service; specification statuses are read from spec files. A
reader in another process opens the store read-only. Where the objective service is absent (the
pre-change tree, for the red record) every command is answered no_objective_service and each row fails
by its own assertions.
"""


def _v77_suite():
    import contextlib
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

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {'control_objective.py': ROOT / ".veldo" / "control_objective.py"}
    SCAFFOLD = ROOT / ".veldo" / "init_scaffold.py"
    PREFIX = 'VELDO-0077 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    # AC2's declared set: each case and the one outcome it may have.
    AC2_SET = ('proven outcome', 'shipped specs but unproven outcome', 'missing evidence', 'wrong signer',
               'stale objective revision')

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
            m = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791200000 + st['tick'],
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
            if name != 'bot77':
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
    with tempfile.TemporaryDirectory(prefix='v77-', dir=fast) as directory:
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
                scaffold = load('v77_scaffold', SCAFFOLD)
                rel = '.veldo/control_objective.py'
                both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
                if both:
                    scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
                check('install/assets', [
                    (rel + ' installed by the scaffold', rel in scaffold._FILES),
                    (rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE),
                    (rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                    (rel + ' laid by the installer', both and (base / 'laid' / rel).is_file()
                     and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                    ('init_scaffold engine copy identical', (ROOT / 'engine/.veldo/init_scaffold.py').read_bytes()
                     == (ROOT / '.veldo/init_scaffold.py').read_bytes())])

            claims = load('v77_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v77_keys', mods / 'control_keys.py')
            I = load('v77_inbox', mods / 'control_assignment.py')
            P = load('v77_projection', mods / 'control_channel_projection.py')
            V = load('v77_presentation', mods / 'control_channel_presentation.py')
            EV = load('v77_attribution', mods / 'control_channel_attribution.py')
            E = load('v77_enrollment', mods / 'control_channel_enrollment.py')
            ST = load('v77_settlement', mods / 'control_request_settlement.py')
            IN = load('v77_intake', mods / 'control_intake.py')
            PJ = load('v77_project', mods / 'control_project.py')
            CP = load('v77_proof', mods / 'control_proof.py')
            contract = load('v77_contract', mods / 'entity_contract.py')
            OB = load('v77_objective', mods / 'control_objective.py') if (mods / 'control_objective.py').is_file() else None
            DOMAIN, REPO = 'domain-77', 'repository-77'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-77')

            keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
            for d in (keys, protected, edge_dir):
                d.mkdir(mode=0o700)
            people = ('steward', 'olga', 'zed', 'asha', 'pete')
            services = ('pm', 'api-edge', 'proof-service')
            keyfile = {who: keys / who for who in ('authority',) + people + services}
            keyfile['edge'] = protected / 'edge-telegram'
            keyfile['edge-auth'] = edge_dir / 'edge-auth'
            public = {}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v77-' + who, '-f', str(path)],
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
            enroll('olga', 'person', ['project_owner', 'admission_authority'], ['proj-a', 'proj-b'])
            enroll('zed', 'person', ['project_owner'], ['proj-a'])
            enroll('asha', 'person', [], ['proj-a'])
            enroll('pete', 'person', [], ['proj-a'])
            enroll('pm', 'service', [], ['proj-a', 'proj-b'])
            enroll('api-edge', 'service', [], ['proj-a', 'proj-b'])
            enroll('proof-service', 'service', [], [REPO])

            def fixture(eid, kind, data):
                row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: row[0] if row else 0}, artifact_digests=[],
                                            nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

            chats = {'olga': 5770001, 'zed': 5770002}
            # VELDO-0064 chat enrollments, spelled here: each person's own private chat with the bot.
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
                   'user': {'id': 8000000077, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_objective_bot'}}
            handler = type('V77Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]

            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot77'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot77'), conn, 'authority',
                                   journal_sign, 'telegram-edge', lambda m: sign_as('edge', m, 'veldo-command'))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=['proj-a', 'proj-b'], api_edge='api-edge',
                               journal_signer='authority', sign=journal_sign)
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)

            def signed(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            # The project, activated by its owner's own signed command.
            activation = projects.apply(signed('olga', dict(
                ids, operation='activate', project='proj-a', principal='olga', command_id=next_id('pc'), nonce=next_id('pn'),
                owner='olga', charter={'purpose': 'Sell passes to travelers.'}, execution_repository=REPO,
                authority_policy={'objective_acceptance': ['project_owner'], 'admission': ['admission_authority']},
                coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))

            # The workspace the service reports specification statuses from, and the kept evidence.
            work = base / 'work'
            (work / 'specs').mkdir(parents=True)

            def spec_file(sid, status):
                (work / 'specs' / ('%s-objective-fixture.md' % sid)).write_text('\n'.join([
                    '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Objective fixture', 'status: ' + status,
                    'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                    'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                    'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
            for sid in ('VELDO-9771', 'VELDO-9772', 'VELDO-9773'):
                spec_file(sid, 'shipped')
            proofs = CP.ProofService(S, conn, domain=DOMAIN, repository=REPO, repo=str(work), principal='proof-service',
                                     signer='authority', sign=journal_sign)
            checker = base / 'outcome_check.py'
            checker.write_text('import sys\nfrom pathlib import Path\n'
                               'text = Path(sys.argv[1]).read_text() if Path(sys.argv[1]).is_file() else ""\n'
                               'ok = sys.argv[2] in text\nprint("outcome %s: %s" % (sys.argv[2], "held" if ok else "not held"))\n'
                               'sys.exit(0 if ok else 1)\n')

            def observe(observed_file, wanted):
                """A real check process, observed and kept by the proof service: {id, digest}."""
                argv = [sys.executable, '-B', str(checker), str(observed_file), wanted]
                run = subprocess.run(argv, capture_output=True, text=True, timeout=30)
                body = {'schema': CP.OBSERVATION_SCHEMA, 'command': argv, 'commit': None, 'exit': run.returncode,
                        'stdout': run.stdout, 'stdout_digest': CP.digest(CP._bytes(run.stdout)),
                        'gate': {'path': 'outcome_check.py', 'digest': CP.digest(checker.read_bytes())}}
                kept = proofs.record_observation(body)
                return {'ref': kept['id'], 'digest': kept['digest'], 'exit': run.returncode}

            service = (OB.Objectives(S, CM, conn, ids, 'authority', journal_sign, workspace=str(work))
                       if OB is not None else None)
            missing = {'ok': False, 'reason': 'no_objective_service'}

            def send(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('oc'), nonce=next_id('on'), **fields)
                return service.apply(signed(who, body)) if service is not None else dict(missing)

            def entity(eid):
                row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}

            def objective(oid):
                row = entity(oid) if isinstance(oid, str) else None
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'objective' else {}

            def of_kind(kind):
                return [(eid, json.loads(t)) for eid, t in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id',
                                                                       (kind,))]

            def ask(text, request_id=None, principal='olga'):
                """One owner message through the authenticated API edge into the common intake."""
                body = {'schema': IN.API_SCHEMA, 'domain': DOMAIN, 'request_id': request_id or next_id('api-req'),
                        'edge': 'api-edge', 'principal': principal, 'text': text, 'project': None, 'clarifies': None}
                return intake.receive('api_request', {'request': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            EVIDENCE = [{'id': 'outcome', 'kind': 'gate_observation'}, {'id': 'regression', 'kind': 'gate_observation'}]

            def bound(outcome, scope=('checkout', 'payments')):
                return dict(outcome=outcome, scope=list(scope), authority={'acceptor': 'olga', 'assessor': 'asha'},
                            evidence_requirements=copy.deepcopy(EVIDENCE))

            def propose(proposal, outcome, **extra):
                return send('pm', 'propose', proposal=proposal, **dict(bound(outcome), **extra))

            def target_and_brief(oid):
                record = objective(oid)
                if OB is None or not record:
                    return {'kind': 'objective', 'ref': str(oid), 'digest': 'sha256:none'}, 'Accept objective %s.' % oid
                return OB.acceptance_target(record), OB.acceptance_brief(record)

            def present(alias, target, brief, owner='olga', touchpoint='decision_disposition'):
                """The requester's terms, the inbox request with its framing, and its presentation."""
                terms = settlement.terms(signed('pm', dict(ids, operation='terms', terms=alias, principal='pm',
                                                           command_id=next_id('terms'), nonce=next_id('tn'),
                                                           touchpoint=touchpoint, target=target, proposal=None,
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
                            rationale='I have read the outcome, scope and evidence.')
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def accept_through_settlement(oid, alias, owner='olga', choice='accept'):
                target, brief = target_and_brief(oid)
                rid, receipt = present(alias, target, brief, owner)
                settled = answer(receipt, choice, owner)
                applied = send('pm', 'accept', objective=oid, objective_version=objective(oid).get('version'), request=rid)
                return rid, settled, applied

            def pid_of(result):
                return result.get('proposal_id')

            # AC1: one project, the shared intake, the current owner's acceptance.
            with region('acceptance/intake-source', 'acceptance/stale-answer', 'acceptance/owner-only',
                        'acceptance/binds-fields', 'acceptance/later-feature', 'acceptance/bounded-elaboration'):
                m1 = ask('For proj-a: travelers can buy a pass in two taps.')
                m_inbox = ask('Travelers can buy a pass in two taps.')
                m_b = ask('For proj-b: a partner portal.')
                proposal1 = intake.proposal(pid_of(m1)) or {}
                inbox_refused = propose(pid_of(m_inbox), 'An inbox proposal names no project.')
                b_refused = propose(pid_of(m_b), 'A project that was never activated.')
                first = propose(pid_of(m1), 'A traveler buys a pass in two taps.')
                o1 = first.get('objective_id') or (OB.objective_id(pid_of(m1)) if OB else 'objective:absent')
                again = propose(pid_of(m1), 'A second objective from the same message.')
                forged = send('pm', 'propose', proposal=m1.get('source'),
                              **bound('A record that is not an intake proposal.'))
                wrong_acceptor = send('pm', 'propose', proposal=pid_of(ask('For proj-a: a second message.')),
                                      **dict(bound('Accepted by someone else.'), authority={'acceptor': 'zed', 'assessor': 'asha'}))
                def foreign(eid, kind):
                    try:
                        fixture(eid, kind, {'objective_uuid': o1, 'state': 'ADMITTED'})
                    except S.StoreRefused as error:
                        return error.code
                    return 'written'
                foreign_objective = foreign(OB.objective_id('forged') if OB else 'objective:forged', 'objective')
                foreign_feature = foreign(OB.feature_id(o1, 'forged') if OB else 'objective-feature:forged', 'backlog_item')
                check('acceptance/intake-source', [
                    ('no other command writes an objective or a feature id',
                     foreign_objective == 'entity_owned' and foreign_feature == 'entity_owned'),
                    ('the owner message is a proposed objective of proj-a through the intake',
                     m1.get('outcome') == 'proposed' and proposal1.get('proposal') == 'objective'
                     and proposal1.get('project') == 'proj-a'),
                    ('the project is active by its owner\'s command', activation.get('ok')),
                    ('the objective is created PROPOSED from that proposal, in its one project',
                     first.get('ok') and objective(o1).get('state') == 'PROPOSED' and objective(o1).get('proposal_id') == pid_of(m1)
                     and objective(o1).get('project_uuid') == 'project:proj-a'),
                    ('an inbox proposal with no project is refused', inbox_refused.get('reason') == 'no_such_proposal'),
                    ('a proposal for a project that is not active is refused',
                     str(b_refused.get('reason')).startswith('project_not_active')),
                    ('a second objective from the same proposal is refused', again.get('reason') == 'already_exists'),
                    ('a record that is not an intake proposal is refused', forged.get('reason') == 'no_such_proposal'),
                    ('an acceptor other than the project owner is refused', wrong_acceptor.get('reason') == 'not_owner:acceptor')])

                # A stale answer: presented at revision 1, a bound field altered, then answered.
                target_r1, brief_r1 = target_and_brief(o1)
                rid_r1, receipt_r1 = present('OBJ-1-r1', target_r1, brief_r1)
                amended = send('pm', 'amend', objective=o1, objective_version=objective(o1).get('version'),
                               changes={'outcome': 'A traveler buys a pass in two taps and sees it active in ten seconds.'})
                settled_r1 = answer(receipt_r1, 'accept')
                before_stale = objective(o1)
                stale = send('pm', 'accept', objective=o1, objective_version=before_stale.get('version'), request=rid_r1)
                # The current revision's target, but the owner was shown another brief.
                target_r2, _brief_r2 = target_and_brief(o1)
                rid_brief, receipt_brief = present('OBJ-1-brief', target_r2, 'Accept something harmless.')
                settled_brief = answer(receipt_brief, 'accept')
                before_brief = objective(o1)
                wrong_brief = send('pm', 'accept', objective=o1, objective_version=before_brief.get('version'),
                                   request=rid_brief)
                check('acceptance/stale-answer', [
                    ('an answer to the current revision shown another brief settled',
                     settled_brief.get('outcome') == 'settled'),
                    ('it is refused as a stale brief by name, the objective unchanged',
                     wrong_brief.get('reason') == 'stale_subject:brief' and objective(o1) == before_brief),
                    ('the amendment is a new revision with a new bound digest',
                     amended.get('ok') and objective(o1).get('revision') == 2 and target_r1.get('digest') != objective(o1).get('bound_digest')),
                    ('the owner\'s answer to revision 1 settled', settled_r1.get('outcome') == 'settled'),
                    ('the stale answer is refused by name', stale.get('reason') == 'stale_subject:revision'),
                    ('the objective is unchanged and still PROPOSED',
                     objective(o1) == before_stale and before_stale.get('state') == 'PROPOSED')])

                # Another project_owner member in scope who is not the project's owner.
                rid_z, settled_z, by_zed = accept_through_settlement(o1, 'OBJ-1-zed', owner='zed')
                check('acceptance/owner-only', [
                    ('the other member\'s answer settled', settled_z.get('outcome') == 'settled'),
                    ('it does not accept the objective', by_zed.get('reason') == 'not_owner'),
                    ('the objective is still PROPOSED at revision 2',
                     objective(o1).get('state') == 'PROPOSED' and objective(o1).get('revision') == 2)])

                under_proposed = send('pm', 'propose_feature', objective=o1, objective_version=objective(o1).get('version'),
                                      feature='early', title='Early', scope=['checkout'])
                rid1, settled1, accepted1 = accept_through_settlement(o1, 'OBJ-1-r2')
                record1 = objective(o1)
                effect1 = (entity(ST.effect_id(rid1, 1)) or {}).get('data') or {}
                shown = (inbox.read(rid1) or {}).get('data') or {}
                want = bound('A traveler buys a pass in two taps and sees it active in ten seconds.')
                check('acceptance/binds-fields', [
                    ('the owner\'s answer settled and accepted the objective',
                     settled1.get('outcome') == 'settled' and accepted1.get('ok') and record1.get('state') == 'ACCEPTED'),
                    ('the accepted revision is the one presented', record1.get('accepted_revision') == 2
                     and effect1.get('target') == {'kind': 'objective', 'ref': o1, 'revision': 2,
                                                   'digest': record1.get('bound_digest')}),
                    ('outcome, scope, authority and evidence requirements are bound exactly',
                     lambda: record1.get('bound') == want and OB.bound_digest(o1, 2, want) == record1.get('bound_digest')),
                    ('the owner was shown each bound field', all(str(v) in shown.get('brief', '') for v in (
                        want['outcome'], 'checkout; payments', 'Assessed by: asha', 'outcome (gate_observation)'))),
                    ('the acceptance names the settlement and the owner',
                     (record1.get('acceptance') or {}).get('settlement_id') == ST.settlement_id(rid1, 1)
                     and (record1.get('acceptance') or {}).get('principals') == ['olga'])])

                feature1 = send('pm', 'propose_feature', objective=o1, objective_version=objective(o1).get('version'),
                                feature='two-tap-checkout', title='Two-tap checkout', scope=['checkout'],
                                specifications=['VELDO-9771'])
                f1 = feature1.get('feature_id')
                f1_record = (entity(f1) or {}).get('data') or {}
                effects_on_f1 = [e for _i, e in of_kind('settlement_effect') if (e.get('target') or {}).get('ref') == f1]
                admissions_before = [e for _i, e in of_kind('admission')]
                rid_adm, receipt_adm = present('ADM-f1', {'kind': 'backlog_item', 'ref': str(f1), 'digest': 'sha256:' + '0' * 64},
                                               'Admit the two-tap checkout feature.', touchpoint='admission')
                admitted = answer(receipt_adm, 'accept')
                admit_effect = (entity(ST.effect_id(rid_adm, 1)) or {}).get('data') or {}
                check('acceptance/later-feature', [
                    ('the feature is proposed under the accepted objective and the objective is ACTIVE',
                     feature1.get('ok') and objective(o1).get('state') == 'ACTIVE' and f1 in objective(o1).get('features', [])),
                    ('the feature is RAW: neither admitted nor prioritized by the acceptance',
                     f1_record.get('state') == 'RAW' and f1_record.get('admission') is None and f1_record.get('priority') is None),
                    ('no admission record and no settled effect names the feature', not admissions_before and not effects_on_f1),
                    ('the acceptance effect targets the objective, not the feature', effect1.get('target', {}).get('ref') == o1),
                    ('admission is its own settled decision on the feature',
                     admitted.get('outcome') == 'settled' and admit_effect.get('type') == 'work_admitted'
                     and admit_effect.get('target', {}).get('ref') == f1),
                    ('the feature record stays RAW after that separate decision',
                     ((entity(f1) or {}).get('data') or {}).get('state') == 'RAW')])

                outside = send('pm', 'propose_feature', objective=o1, objective_version=objective(o1).get('version'),
                               feature='loyalty', title='Loyalty points', scope=['checkout', 'loyalty'])
                check('acceptance/bounded-elaboration', [
                    ('a feature outside the accepted scope is refused by name', outside.get('reason') == 'out_of_scope:loyalty'),
                    ('no feature record was written for it',
                     OB is not None and entity(OB.feature_id(o1, 'loyalty')) is None),
                    ('a feature under an objective that is not accepted is refused',
                     under_proposed.get('reason') == 'invalid_transition:PROPOSED->ACTIVE')])

            # AC2: only the bound assessor's assessment of the accepted revision, with complete evidence.
            with region('satisfaction/wrong-signer', 'satisfaction/missing-evidence', 'satisfaction/stale-revision',
                        'satisfaction/stale-evidence', 'satisfaction/unproven-outcome', 'satisfaction/proven',
                        'satisfaction/other-process'):
                good = work / 'outcome-o1.txt'
                good.write_text('checkout: two taps; active in ten seconds\n')
                ev_outcome = observe(good, 'two taps')
                ev_regress = observe(good, 'active in ten seconds')
                complete = {'outcome': {'ref': ev_outcome['ref'], 'digest': ev_outcome['digest']},
                            'regression': {'ref': ev_regress['ref'], 'digest': ev_regress['digest']}}

                def assess(who, oid, revision, evidence):
                    return send(who, 'assess', objective=oid, objective_version=objective(oid).get('version'),
                                revision=revision, evidence=evidence)
                version_before = objective(o1).get('version')
                by_pete = assess('pete', o1, 2, complete)
                by_pm = assess('pm', o1, 2, complete)
                check('satisfaction/wrong-signer', [
                    ('a person who is not the bound assessor is refused', by_pete.get('reason') == 'not_authorized:assessor'),
                    ('a service is refused', by_pm.get('reason') == 'not_authorized:not_a_person'),
                    ('the objective is unchanged', objective(o1).get('version') == version_before
                     and objective(o1).get('state') == 'ACTIVE')])
                partial = assess('asha', o1, 2, {'outcome': complete['outcome']})
                absent = assess('asha', o1, 2, dict(complete, regression={'ref': 'gate-observation:' + '0' * 64,
                                                                           'digest': ev_regress['digest']}))
                altered = assess('asha', o1, 2, dict(complete, regression={'ref': ev_regress['ref'], 'digest': 'sha256:' + '1' * 64}))
                check('satisfaction/missing-evidence', [
                    ('an assessment without a required item is refused', partial.get('reason') == 'missing_evidence:regression'),
                    ('an item naming no kept record is refused', absent.get('reason') == 'missing_evidence:regression'),
                    ('an item naming another digest is refused', altered.get('reason') == 'missing_evidence:regression'),
                    ('the objective is still ACTIVE', objective(o1).get('state') == 'ACTIVE')])
                stale_rev = assess('asha', o1, 1, complete)
                check('satisfaction/stale-revision', [
                    ('an assessment of revision 1, not the accepted revision 2, is refused',
                     stale_rev.get('reason') == 'stale_subject:revision'),
                    ('the objective is still ACTIVE', objective(o1).get('state') == 'ACTIVE')])

                # A specification-supported objective whose specifications are all shipped but whose
                # outcome did not hold when checked.
                m2 = ask('For proj-a: every pass renews itself before it expires.')
                o2 = propose(pid_of(m2), 'Every pass renews itself before it expires.').get('objective_id')
                _r2, _s2, accepted2 = accept_through_settlement(o2, 'OBJ-2')
                for name, spec in (('renewal-engine', 'VELDO-9772'), ('renewal-notice', 'VELDO-9773')):
                    send('pm', 'propose_feature', objective=o2, objective_version=objective(o2).get('version'), feature=name,
                         title=name, scope=['payments'], specifications=[spec])
                # Passing observations kept before this objective was accepted prove nothing about it.
                pre_acceptance = assess('asha', o2, 1, complete)
                check('satisfaction/stale-evidence', [
                    ('the evidence was kept and passed before the objective was accepted',
                     ev_outcome['exit'] == 0 and ev_regress['exit'] == 0 and accepted2.get('ok')),
                    ('an assessment over it is refused as stale evidence by name',
                     pre_acceptance.get('reason') == 'stale_subject:evidence'),
                    ('the objective is not satisfied', objective(o2).get('state') == 'ACTIVE'
                     and objective(o2).get('assessment') is None)])
                bad = work / 'outcome-o2.txt'
                bad.write_text('renewal: not yet observed\n')
                failing = observe(bad, 'renewed before expiry')
                passing = observe(bad, 'renewal')
                shipped = service.specifications(o2) if service is not None else {}
                unproven = assess('asha', o2, 1, {'outcome': {'ref': failing['ref'], 'digest': failing['digest']},
                                                   'regression': {'ref': passing['ref'], 'digest': passing['digest']}})
                check('satisfaction/unproven-outcome', [
                    ('the objective is accepted and every one of its specifications is shipped',
                     accepted2.get('ok') and objective(o2).get('state') == 'ACTIVE'
                     and shipped == {'VELDO-9772': 'shipped', 'VELDO-9773': 'shipped'}),
                    ('the outcome check ran and failed', failing['exit'] == 1),
                    ('the assessment is refused as an unproven outcome', unproven.get('reason') == 'unproven_outcome:outcome'),
                    ('the objective is not satisfied', objective(o2).get('state') == 'ACTIVE'
                     and objective(o2).get('assessment') is None)])

                proven = assess('asha', o1, 2, complete)
                receipt1 = objective(o1).get('assessment') or {}
                check('satisfaction/proven', [
                    ('the bound assessor\'s complete, current assessment satisfies the objective',
                     proven.get('ok') and objective(o1).get('state') == 'SATISFIED'),
                    ('the receipt is the objective_satisfied fact of the accepted revision',
                     receipt1.get('fact') == 'objective_satisfied' and receipt1.get('subject') == {'id': o1, 'revision': 2}
                     and receipt1.get('assessor') == 'asha'),
                    ('each evidence item is the kept record by its digest',
                     receipt1.get('evidence', {}).get('outcome', {}).get('digest') == (entity(ev_outcome['ref']) or {}).get('digest')),
                    ('a second assessment of a satisfied objective is refused',
                     str(assess('asha', o1, 2, complete).get('reason')).startswith('invalid_transition'))])
                assessment_body = S.canonical_bytes((receipt1.get('signed_assessment') or {}).get('command') or {})
                (base / 'assessment.bin').write_bytes(assessment_body)
                (base / 'assessment.sig').write_text((receipt1.get('signed_assessment') or {}).get('signature') or '')
                (base / 'allowed').write_text('asha namespaces="veldo-command" %s\n' % public['asha'])
                child = base / 'reader.py'
                child.write_text(_V77_CHILD)
                out = subprocess.run([sys.executable, '-B', str(child), str(mods), str(db), json.dumps([o1, o2]), str(base)],
                                     capture_output=True, text=True, timeout=60)
                seen = json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else {}
                check('satisfaction/other-process', [
                    ('the other process read the store read-only', seen.get('read_only') is True),
                    ('it sees the satisfied objective and its accepted revision',
                     seen.get('objectives', {}).get(o1, {}).get('state') == 'SATISFIED'
                     and seen.get('objectives', {}).get(o1, {}).get('subject') == {'id': o1, 'revision': 2}),
                    ('it sees the shipped-but-unproven objective still ACTIVE',
                     seen.get('objectives', {}).get(o2, {}).get('state') == 'ACTIVE'),
                    ('the assessor\'s signature verifies independently', seen.get('signature_verified') is True),
                    ('the declared AC2 set was driven', len(AC2_SET) == 5)])

            # AC3: cancellation disposes of unfinished work explicitly and keeps the history.
            with region('cancel/work-disposition', 'cancel/history-kept', 'cancel/reopen-linked', 'cancel/transfer-bounded'):
                m3 = ask('For proj-a: group passes for tour operators.')
                o3 = propose(pid_of(m3), 'A tour operator buys ten passes at once.').get('objective_id')
                rid3, _s3, _a3 = accept_through_settlement(o3, 'OBJ-3')
                m4 = ask('For proj-a: operator invoicing.')
                o4 = propose(pid_of(m4), 'An operator receives one invoice per group.').get('objective_id')
                _r4, _s4, _a4 = accept_through_settlement(o4, 'OBJ-4')
                fa = send('pm', 'propose_feature', objective=o3, objective_version=objective(o3).get('version'),
                          feature='bulk-cart', title='Bulk cart', scope=['checkout']).get('feature_id')
                fb = send('pm', 'propose_feature', objective=o3, objective_version=objective(o3).get('version'),
                          feature='group-invoice', title='Group invoice', scope=['payments']).get('feature_id')
                before3 = objective(o3)
                kept_rows = {eid: (entity(eid) or {}).get('digest') for eid in (
                    rid3, ST.settlement_id(rid3, 1), ST.effect_id(rid3, 1), ST.receipt_id(rid3, 1))}

                def cancel(who, dispositions, reason='Operators moved to a partner.'):
                    return send(who, 'cancel', objective=o3, objective_version=objective(o3).get('version'), reason=reason,
                                dispositions=dispositions)
                undisposed = cancel('olga', [])
                half = cancel('olga', [{'target': fa, 'disposition': 'stop', 'recorded_by': 'olga'}])
                by_other = cancel('olga', [{'target': fa, 'disposition': 'stop', 'recorded_by': 'zed'},
                                           {'target': fb, 'disposition': 'stop', 'recorded_by': 'zed'}])
                by_zed = cancel('zed', [{'target': fa, 'disposition': 'stop', 'recorded_by': 'zed'},
                                        {'target': fb, 'disposition': 'stop', 'recorded_by': 'zed'}])
                unchanged = objective(o3) == before3 and ((entity(fa) or {}).get('data') or {}).get('state') == 'RAW'
                canceled = cancel('olga', [{'target': fa, 'disposition': 'stop', 'recorded_by': 'olga'},
                                           {'target': fb, 'disposition': 'transfer', 'to': o4, 'recorded_by': 'olga'}])
                fa_after = (entity(fa) or {}).get('data') or {}
                fb_after = (entity(fb) or {}).get('data') or {}
                after3 = objective(o3)
                check('cancel/work-disposition', [
                    ('a cancel with no disposition of the unfinished features is refused',
                     undisposed.get('reason') == 'missing_disposition'),
                    ('a cancel disposing of only one of them is refused', half.get('reason') == 'missing_disposition'),
                    ('a disposition recorded by someone else is refused', by_other.get('reason') == 'not_authorized:disposition'),
                    ('another project_owner member cannot cancel', by_zed.get('reason') == 'not_owner:project'),
                    ('nothing changed while refused', unchanged),
                    ('the owner\'s explicit dispositions cancel the objective',
                     canceled.get('ok') and after3.get('state') == 'CANCELED'
                     and (after3.get('cancellation') or {}).get('dispositions', [{}])[0].get('recorded_by') == 'olga'),
                    ('the stopped feature is CANCELED with its disposition recorded',
                     fa_after.get('state') == 'CANCELED' and fa_after.get('history', [{}])[-1].get('disposition') == 'stop'),
                    ('the transferred feature now belongs to the other accepted objective',
                     fb_after.get('objective_uuid') == o4 and fb_after.get('state') == 'RAW' and fb in objective(o4).get('features', []))])
                check('cancel/history-kept', [
                    ('the earlier history entries are kept unchanged',
                     after3.get('history', [])[:len(before3.get('history', []))] == before3.get('history')
                     and len(after3.get('history', [])) == len(before3.get('history', [])) + 1),
                    ('the owner, acceptance and accepted revision are kept',
                     after3.get('bound', {}).get('authority') == before3.get('bound', {}).get('authority')
                     and after3.get('acceptance') == before3.get('acceptance') and after3.get('accepted_revision') == 1),
                    ('the settlement, effect, receipt and request records are unchanged',
                     all(v and (entity(eid) or {}).get('digest') == v for eid, v in kept_rows.items())),
                    ('the features list is kept', after3.get('features') == [fa, fb])])

                row3 = entity(o3)
                reopened = send('olga', 'reopen', objective=o3, objective_version=objective(o3).get('version'))
                amended3 = send('pm', 'amend', objective=o3, objective_version=objective(o3).get('version'),
                                changes={'outcome': 'Reopened by an amendment.'})
                m5 = ask('For proj-a: group passes again, through the partner.')
                from_active = propose(pid_of(m5), 'Continue from an objective that is not terminal.', continues=o4)
                continued = propose(pid_of(m5), 'A partner sells group passes.', continues=o3)
                o5 = continued.get('objective_id')
                check('cancel/reopen-linked', [
                    ('reopening the canceled objective is refused by the lifecycle',
                     reopened.get('reason') == 'invalid_transition:CANCELED->PROPOSED'),
                    ('amending it is refused', str(amended3.get('reason')).startswith('invalid_transition')),
                    ('a continuation must name a terminal objective', from_active.get('reason') == 'invalid_input:continues'),
                    ('a new objective linked to it continues the work',
                     continued.get('ok') and objective(o5).get('continues') == o3 and objective(o5).get('state') == 'PROPOSED'),
                    ('the canceled objective is byte-for-byte unchanged', row3 is not None and entity(o3) == row3)])

                # A transfer lands inside the receiving objective's accepted scope, under its accepted
                # revision, and each feature has exactly one disposition.
                mT = ask('For proj-a: seasonal passes.')
                oT = propose(pid_of(mT), 'A traveler buys a seasonal pass.').get('objective_id')
                accept_through_settlement(oT, 'OBJ-T')
                mR = ask('For proj-a: seasonal checkout.')
                oR = send('pm', 'propose', proposal=pid_of(mR),
                          **bound('A seasonal pass checks out in two taps.', scope=('checkout',))).get('objective_id')
                send('pm', 'amend', objective=oR, objective_version=objective(oR).get('version'),
                     changes={'outcome': 'A seasonal pass checks out in two taps, on every device.'})
                accept_through_settlement(oR, 'OBJ-R')
                fc = send('pm', 'propose_feature', objective=oT, objective_version=objective(oT).get('version'),
                          feature='season-cart', title='Season cart', scope=['checkout']).get('feature_id')
                fp = send('pm', 'propose_feature', objective=oT, objective_version=objective(oT).get('version'),
                          feature='season-billing', title='Season billing', scope=['payments']).get('feature_id')

                def snapshot():
                    return {eid: entity(eid) for eid in (oT, oR, fc, fp)}

                def cancel_t(dispositions):
                    return send('olga', 'cancel', objective=oT, objective_version=objective(oT).get('version'),
                                reason='Seasons moved to a partner.', dispositions=dispositions)
                start = snapshot()
                outside_transfer = cancel_t([{'target': fc, 'disposition': 'stop', 'recorded_by': 'olga'},
                                             {'target': fp, 'disposition': 'transfer', 'to': oR, 'recorded_by': 'olga'}])
                after_outside = snapshot()
                twice = cancel_t([{'target': fc, 'disposition': 'transfer', 'to': oR, 'recorded_by': 'olga'},
                                  {'target': fc, 'disposition': 'stop', 'recorded_by': 'olga'},
                                  {'target': fp, 'disposition': 'stop', 'recorded_by': 'olga'}])
                after_twice = snapshot()
                moved = cancel_t([{'target': fc, 'disposition': 'transfer', 'to': oR, 'recorded_by': 'olga'},
                                  {'target': fp, 'disposition': 'stop', 'recorded_by': 'olga'}])
                fc_after = (entity(fc) or {}).get('data') or {}
                listed = objective(oR).get('features') or []
                check('cancel/transfer-bounded', [
                    ('the source is accepted at revision 1 and the receiver, scoped to checkout, at revision 2',
                     objective(oT).get('accepted_revision') == 1 and objective(oR).get('accepted_revision') == 2
                     and objective(oR).get('bound', {}).get('scope') == ['checkout'] and bool(fc) and bool(fp)),
                    ('a transfer outside the receiver\'s accepted scope is refused by name',
                     outside_transfer.get('reason') == 'out_of_scope:payments'),
                    ('nothing was written for it', after_outside == start),
                    ('a disposition set naming one feature twice is refused',
                     twice.get('reason') == 'invalid_input:duplicate_disposition'),
                    ('nothing was written for that either', after_twice == start),
                    ('an in-scope transfer moves the feature under the receiver\'s accepted revision',
                     moved.get('ok') and fc_after.get('objective_uuid') == oR and fc_after.get('state') == 'RAW'
                     and fc_after.get('objective_revision') == 2 and fc in listed),
                    ('the receiver lists no canceled feature',
                     all(((entity(f) or {}).get('data') or {}).get('state') != 'CANCELED' for f in listed))])

                # Two transfers into one ACCEPTED receiver in one cancel: its state moves once, and its
                # history records ACCEPTED to ACTIVE for the first and ACTIVE to ACTIVE for the second.
                oW = propose(pid_of(ask('For proj-a: winter passes.')), 'A traveler buys a winter pass.').get('objective_id')
                accept_through_settlement(oW, 'OBJ-W')
                oV = propose(pid_of(ask('For proj-a: winter checkout.')), 'A winter pass checks out.').get('objective_id')
                accept_through_settlement(oV, 'OBJ-V')
                w1 = send('pm', 'propose_feature', objective=oW, objective_version=objective(oW).get('version'),
                          feature='winter-cart', title='Winter cart', scope=['checkout']).get('feature_id')
                w2 = send('pm', 'propose_feature', objective=oW, objective_version=objective(oW).get('version'),
                          feature='winter-cart-2', title='Winter cart two', scope=['checkout']).get('feature_id')
                v_before = objective(oV)
                both = send('olga', 'cancel', objective=oW, objective_version=objective(oW).get('version'),
                            reason='Winter moved to a partner.',
                            dispositions=[{'target': w1, 'disposition': 'transfer', 'to': oV, 'recorded_by': 'olga'},
                                          {'target': w2, 'disposition': 'transfer', 'to': oV, 'recorded_by': 'olga'}])
                v_after = objective(oV)
                v_new = [(h.get('source'), h.get('target'), h.get('feature'))
                         for h in (v_after.get('history') or [])[len(v_before.get('history') or []):]]
                check('cancel/transfer-bounded', [
                    ('two transfers into one accepted receiver move its state once',
                     both.get('ok') and v_before.get('state') == 'ACCEPTED' and v_after.get('state') == 'ACTIVE'
                     and v_after.get('version', 0) - v_before.get('version', 0) == 1),
                    ('and its history names the transition each transfer really made',
                     v_new == [('ACCEPTED', 'ACTIVE', w1), ('ACTIVE', 'ACTIVE', w2)])])

            with region('observability'):
                # The row's own objectives and feature, measured as a change, so objectives other rows
                # (or a probe) leave pending do not decide it.
                pending_before = (service.metrics() if service is not None else {}).get('pending') or {}
                mine = [propose(pid_of(ask('For proj-a: observed objective %d.' % n)), 'Observed outcome %d.' % n)
                        for n in (1, 2)]
                mine_feature = send('pm', 'propose_feature', objective=o4, objective_version=objective(o4).get('version'),
                                    feature='observed-feature', title='Observed feature', scope=['checkout'])
                metrics = service.metrics() if service is not None else {}
                pending_after = metrics.get('pending') or {}

                def grew(key):
                    return pending_after.get(key, 0) - pending_before.get(key, 0)
                proposed_mine = [x for x in mine if x.get('ok') and objective(x.get('objective_id')).get('state') == 'PROPOSED']
                refusals = [o for o in (service.observations if service is not None else []) if o['outcome'] == 'refused']
                text = json.dumps(service.observations if service is not None else [])
                check('observability', [
                    ('accepted and refused commands are counted',
                     metrics.get('accepted', 0) > 0 and metrics.get('refused', 0) == len(refusals) > 0),
                    ('every refusal is named and classified, never as success',
                     all(o['refusal'] and o['taxonomy'] not in (None, 'unknown_outcome') for o in refusals)),
                    ('the pending work is exposed: the row\'s own objectives and feature are counted',
                     len(proposed_mine) == 2 and grew('awaiting_acceptance') == len(proposed_mine)
                     and mine_feature.get('ok') and grew('features_awaiting_admission') == 1),
                    ('observations carry no outcome text or signature', 'two taps' not in text and 'SSH SIGNATURE' not in text)])

            # VELDO-0076: a paused, canceled or completed project amends, accepts, elaborates and
            # satisfies nothing; a paused one still lets its owner cancel an objective.
            with region('project/inactive-refusals'):
                def lifecycle(project, op, **fields):
                    return projects.apply(signed('olga', dict(
                        ids, operation=op, project=project, principal='olga', command_id=next_id('pc'), nonce=next_id('pn'),
                        project_version=(entity('project:' + project) or {}).get('version'), **fields)))
                mP = ask('For proj-a: passes for families.')
                oP = propose(pid_of(mP), 'A family buys four passes at once.').get('objective_id')
                targetP, briefP = target_and_brief(oP)
                ridP, receiptP = present('OBJ-P', targetP, briefP)
                settledP = answer(receiptP, 'accept')
                later = work / 'outcome-o4.txt'
                later.write_text('invoice: one per group\n')
                fresh = {'outcome': observe(later, 'one per group'), 'regression': observe(later, 'invoice')}
                fresh = {k: {'ref': v['ref'], 'digest': v['digest']} for k, v in fresh.items()}
                m_paused = ask('For proj-a: proposed while paused.')

                def attempts(tag):
                    return {
                        'amend': send('pm', 'amend', objective=oP, objective_version=objective(oP).get('version'),
                                      changes={'outcome': 'Amended while %s.' % tag}).get('reason'),
                        'accept': send('pm', 'accept', objective=oP, objective_version=objective(oP).get('version'),
                                       request=ridP).get('reason'),
                        'propose_feature': send('pm', 'propose_feature', objective=o4,
                                                objective_version=objective(o4).get('version'), feature='while-' + tag,
                                                title='While ' + tag, scope=['checkout']).get('reason'),
                        'assess': send('asha', 'assess', objective=o4, objective_version=objective(o4).get('version'),
                                       revision=objective(o4).get('accepted_revision'), evidence=fresh).get('reason')}
                paused = lifecycle('proj-a', 'pause', reason='Holding for the season.')
                held = {eid: entity(eid) for eid in (oP, o4)}
                while_paused = attempts('paused')
                propose_paused = propose(pid_of(m_paused), 'Proposed while paused.').get('reason')
                unchanged_paused = {eid: entity(eid) for eid in (oP, o4)} == held
                cancel_paused = send('olga', 'cancel', objective=oP, objective_version=objective(oP).get('version'),
                                     reason='Families moved to a partner.', dispositions=[])
                canceled = lifecycle('proj-a', 'cancel', reason='The line is closed.', disposition='stop everything')
                held = {eid: entity(eid) for eid in (o4, o5)}
                while_canceled = {
                    'amend': send('pm', 'amend', objective=o5, objective_version=objective(o5).get('version'),
                                  changes={'outcome': 'Amended after the cancel.'}).get('reason'),
                    'propose_feature': send('pm', 'propose_feature', objective=o4, objective_version=objective(o4).get('version'),
                                            feature='while-canceled', title='While canceled', scope=['checkout']).get('reason'),
                    'assess': send('asha', 'assess', objective=o4, objective_version=objective(o4).get('version'),
                                   revision=objective(o4).get('accepted_revision'), evidence=fresh).get('reason')}
                unchanged_canceled = {eid: entity(eid) for eid in (o4, o5)} == held
                activated_b = projects.apply(signed('olga', dict(
                    ids, operation='activate', project='proj-b', principal='olga', command_id=next_id('pc'), nonce=next_id('pn'),
                    owner='olga', charter={'purpose': 'Resell passes.'}, execution_repository=REPO,
                    authority_policy={'objective_acceptance': ['project_owner'], 'admission': ['admission_authority']},
                    coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))
                oB = send('pm', 'propose', proposal=pid_of(ask('For proj-b: a reseller portal.')),
                          **dict(bound('A reseller sells a pass.'), authority={'acceptor': 'olga', 'assessor': 'olga'})
                          ).get('objective_id')
                m_completed = ask('For proj-b: proposed after completion.')
                cancel_b = send('olga', 'cancel', objective=oB, objective_version=objective(oB).get('version'),
                                reason='Resellers wait.', dispositions=[])
                completed = lifecycle('proj-b', 'complete')
                held_b = entity(oB)
                while_completed = {
                    'amend': send('pm', 'amend', objective=oB, objective_version=objective(oB).get('version'),
                                  changes={'outcome': 'Amended after completion.'}).get('reason'),
                    'accept': send('pm', 'accept', objective=oB, objective_version=objective(oB).get('version'),
                                   request=ridP).get('reason')}
                propose_completed = send('pm', 'propose', proposal=pid_of(m_completed),
                                         **dict(bound('After completion.'), authority={'acceptor': 'olga', 'assessor': 'olga'})
                                         ).get('reason')
                check('project/inactive-refusals', [
                    ('the owner paused proj-a with an answer settled and fresh evidence kept',
                     paused.get('ok') and settledP.get('outcome') == 'settled' and objective(o4).get('state') != 'SATISFIED'),
                    ('while paused: amend, accept, propose_feature and assess are refused by name',
                     while_paused == {k: 'project_not_active:PAUSED' for k in while_paused}),
                    ('while paused: a new objective is refused by name', propose_paused == 'project_not_active:PAUSED'),
                    ('nothing was written while paused', unchanged_paused),
                    ('while paused: the owner still cancels an objective',
                     cancel_paused.get('ok') and objective(oP).get('state') == 'CANCELED'),
                    ('canceled proj-a: amend, propose_feature and assess are refused by name, nothing written',
                     canceled.get('ok') and unchanged_canceled
                     and while_canceled == {k: 'project_not_active:CANCELED' for k in while_canceled}),
                    ('completed proj-b: amend, accept and a new objective are refused by name, nothing written',
                     activated_b.get('ok') and cancel_b.get('ok') and completed.get('ok') and entity(oB) == held_b
                     and while_completed == {k: 'project_not_active:COMPLETED' for k in while_completed}
                     and propose_completed == 'project_not_active:COMPLETED')])
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for connection in connections:
                connection.close()
    if raised:
        print('  %sdetail: regions that raised: %s' % (PREFIX, raised))


# The other process: the installed store and objective modules over a read-only connection, and an
# independent ssh-keygen verification of the assessor's signed assessment.
_V77_CHILD = '''import importlib.util, json, sqlite3, subprocess, sys
from pathlib import Path
organs, db, wanted, base = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), Path(sys.argv[4])
def load(name):
    s = importlib.util.spec_from_file_location('child_' + name, str(Path(organs) / (name + '.py')))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = load('control_store'); OB = load('control_objective')
conn = S.open_store(db, mode='r')
try:
    conn.execute("CREATE TABLE probe (x)")
    read_only = False
except sqlite3.Error:
    read_only = True
out = {'read_only': read_only, 'objectives': {}}
for oid in wanted:
    record = OB.read(conn, oid) or {}
    out['objectives'][oid] = {'state': record.get('state'), 'subject': (record.get('assessment') or {}).get('subject'),
                              'features': [f.get('state') for f in OB.features(conn, oid)]}
done = subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(base / 'allowed'), '-I', 'asha', '-n', 'veldo-command',
                       '-s', str(base / 'assessment.sig')], input=(base / 'assessment.bin').read_bytes(), capture_output=True,
                      timeout=20)
out['signature_verified'] = done.returncode == 0
conn.close()
print(json.dumps(out))
'''

_v77_started = __import__('time').monotonic()
_v77_suite()
print('VELDO-0077 suite seconds: %.3f' % (__import__('time').monotonic() - _v77_started))
