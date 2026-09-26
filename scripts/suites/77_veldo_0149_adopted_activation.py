"""VELDO-0149: a project activates on any repository this domain adopted, by the owner's signed command
or by his settled answer, over a real signed store.

Run: python3 scripts/selftest.py --suite 77_veldo_0149_adopted_activation

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy every
service loads, with the production control_project.py (PRODUCTION below, the copy a registered mutation
replaces). Real SQLite store with OpenSSH command, journal, enrollment, possession and edge signatures;
members and keys enrolled by the steward's signed VELDO-0025 commands; real Git repositories enrolled
through their VELDO-0029 bindings (control_enrollment.enroll, resolved by resolve_store) and bound to the
store for their domain (control_store.bind_repositories); activation requests recorded as VELDO-0068
terms, opened in the VELDO-0064 inbox, framed and presented by the VELDO-0065 presenter over a loopback
Bot API (real HTTP in the platform's shapes; no network, no real token), answered through the
authenticated API edge or by a Telegram reply the VELDO-0066 Acquirer attributes and the actual
protected signer process signs, and settled by the VELDO-0068 settlement service. Where the settled
path is absent (the pre-change tree, for the red record) it is answered no_settled_activation and each
row fails by its own assertions, never by an exception. No private key byte, signature or rationale is
printed or retained.
"""


def _v149_suite():
    import contextlib
    import copy
    import hashlib
    import http.server
    import importlib.util
    import inspect
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import threading
    import time

    # Literal anchors: the registered mutation driver substitutes this production copy here.
    PRODUCTION = {
        'control_project.py': ROOT / ".veldo" / "control_project.py",
    }
    PREFIX = 'VELDO-0149 '
    # The fields VELDO-0076 AC1 says activation binds; VELDO-0149 AC2 says an answer binds the same.
    SPEC_FIELDS = ('owner', 'charter', 'execution_repository', 'authority_policy', 'coordination_budget')
    CHOICES = ('accept', 'return_for_elaboration', 'reject')
    NAMES = ['tide', 'reef', 'kelp', 'cove', 'dune', 'moor', 'heath', 'fern', 'vale', 'glen', 'rill']

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    emitted, raised, regions = set(), [], []

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
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            print('  %sdetail: %s did not run to its end: %r' % (PREFIX, labels[0], error))
            for label in labels:
                if label not in emitted:
                    check(label, [('region raised', False)])

    def message(st, bot, sender, chat, text, reply_to=None):
        """One message as the platform keeps and delivers it."""
        with st['lock']:
            bot['next'] += 1
            st['tick'] += 1
            m = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791000000 + st['tick'],
                 'text': text}
            if reply_to is not None:
                held = bot['messages'][(chat['id'], reply_to)]
                m['reply_to_message'] = copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
            bot['messages'][(chat['id'], m['message_id'])] = m
            return m

    class BotApi(http.server.BaseHTTPRequestHandler):
        """Loopback endpoint with the Bot API getMe, getUpdates and sendMessage shapes."""
        state = None

        def log_message(self, *args):
            pass

        def do_POST(self):
            st = self.state
            raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
            body = json.loads(raw) if raw else {}
            _, _, rest = self.path.partition('/bot')
            name, _, method = rest.partition('/')
            bot = st['bots'].get(name)
            if bot is None:
                return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
            if method == 'getMe':
                return self._answer(200, {'ok': True, 'result': dict(bot['user'], can_join_groups=True)})
            if method == 'getUpdates':
                offset = body.get('offset') or 0
                if offset:
                    bot['updates'] = [u for u in bot['updates'] if u['update_id'] >= offset]
                return self._answer(200, {'ok': True, 'result': bot['updates'][:body.get('limit') or 100]})
            if method == 'sendMessage':
                chat = st['chats'].get(body.get('chat_id'), {'id': body.get('chat_id'), 'type': 'private'})
                reply = (body.get('reply_parameters') or {}).get('message_id')
                if reply is not None and (chat['id'], reply) not in bot['messages']:
                    reply = None
                return self._answer(200, {'ok': True, 'result': message(st, bot, bot['user'], chat, body['text'], reply)})
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
    with tempfile.TemporaryDirectory(prefix='v149-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        try:
            claims = load('v149_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v149_keys', mods / 'control_keys.py')
            I = load('v149_inbox', mods / 'control_assignment.py')
            P = load('v149_projection', mods / 'control_channel_projection.py')
            V = load('v149_presentation', mods / 'control_channel_presentation.py')
            EV = load('v149_attribution', mods / 'control_channel_attribution.py')
            E = load('v149_edge_enrollment', mods / 'control_channel_enrollment.py')
            A = load('v149_answers', mods / 'control_signer_answers.py')
            ST = load('v149_settlement', mods / 'control_request_settlement.py')
            EN = load('v149_enrollment', mods / 'control_enrollment.py')
            GP = load('v149_git', mods / 'git_process.py')
            contract = load('v149_contract', mods / 'entity_contract.py')
            PJ = load('v149_project', mods / 'control_project.py')

            DOMAIN, OTHER, REPO, STORE, HOST = 'domain-149', 'domain-149-other', 'repository-149', 'store-149', 'host-149'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid=STORE)
            keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
            for d in (keys, protected, edge_dir):
                d.mkdir(mode=0o700)
            keyfile = {who: keys / who for who in ('authority', 'steward', 'owner', 'owner2', 'pm', 'api-edge')}
            keyfile['edge'] = protected / 'edge-telegram'
            keyfile['edge-auth'] = edge_dir / 'edge-auth'
            public = {}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v149-' + who, '-f', str(path)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])

            def sign_as(who, data, namespace='veldo-command'):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=data,
                                      capture_output=True, check=True, timeout=20).stdout.decode()

            serial = [0]

            def next_id(prefix):
                serial[0] += 1
                return '%s-%d' % (prefix, serial[0])

            def verifies(principal, namespace, data, signature):
                """An independent ssh-keygen verification, in a fresh directory of its own."""
                place = base / next_id('verify')
                place.mkdir()
                (place / 'allowed').write_text('%s namespaces="%s" %s\n' % (principal, namespace, public[principal]))
                (place / 'signature').write_text(signature if isinstance(signature, str) else '')
                done = subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(place / 'allowed'), '-I', principal,
                                       '-n', namespace, '-s', str(place / 'signature')], input=data,
                                      capture_output=True, timeout=20)
                return done.returncode == 0

            def journal_sign(data):
                return sign_as('authority', data, 'veldo-journal')

            (base / 'authority').mkdir()
            db = base / 'authority' / 'control.sqlite3'
            conn = S.open_store(str(db))
            connections.append(conn)
            CM.attach(S)
            K.attach(S)
            repository = base / 'repository'
            repository.mkdir()
            projection = repository / '.veldo' / 'keys' / 'allowed_signers'
            config_path = base / 'authority' / 'signer.json'
            config_path.write_text(json.dumps({'store': str(db), 'repository': str(repository),
                                               'allowed_signers': str(projection), 'key_directory': str(protected),
                                               'authority_ids': ids}))

            def envelope(command, principal):
                now = CM.authority_state(S, conn)
                return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                            request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                            membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))

            def admin(principal, operation, params, enrollee=None):
                """One membership organ command, signed by `principal` (and co-signed by an enrollee)."""
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

            admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                                  'roles': ['membership_steward', 'project_owner'],
                                                  'public_key': public['steward'], 'independence_group': 'steward',
                                                  'scope': '*'})
            for who, kind, roles in (('owner', 'person', ['project_owner', 'admission_authority']),
                                     ('owner2', 'person', ['project_owner']),
                                     ('pm', 'service', []), ('api-edge', 'service', [])):
                admin('steward', 'enroll_principal', {'principal': who, 'principal_type': kind, 'roles': roles,
                                                      'public_key': public[who], 'independence_group': who,
                                                      'scope': list(NAMES)}, enrollee=who)

            def fixture(eid, kind, data):
                current = S.materialized_state(conn)['entities']
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: current.get(eid, {}).get('version', 0)},
                                            artifact_digests=[], nonce=next_id('fixture-nonce')), 'authority',
                                 journal_sign, 1)

            chats = {'owner': 5590001, 'owner2': 5590002}
            for who, chat in chats.items():
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))
            enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
            edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                           'public_key': public['edge'], 'connection_public_key': public['edge-auth'],
                           'scope': list(NAMES)}
            edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                            'target': 'channel:telegram_chat', 'parameters': edge_params, 'artifact_digests': [],
                            'expected_versions': {}}
            edge_env = envelope(edge_command, 'steward')
            enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                             sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))
            admin('owner', 'grant_delegation', {'id': 'delegation-owner', 'principal': 'owner', 'channel': 'telegram_chat',
                                                'assertion_kinds': ['decision_answer', 'review_disposition'],
                                                'authority_scope': list(NAMES), 'request_version': None,
                                                'presentation_version': None, 'expires_at': time.time() + 1800,
                                                'edge_key_id': 'edge-telegram'})

            api = {'tick': 0, 'bots': {}, 'chats': {}, 'lock': threading.Lock()}
            handler = type('V149Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]
            api['bots']['bot149'] = {'user': {'id': 8000000149, 'is_bot': True, 'first_name': 'Veldo',
                                              'username': 'veldo_projects_bot'},
                                     'next': 9000, 'update_next': 720000000, 'messages': {}, 'updates': []}
            bot = api['bots']['bot149']
            people = {who: {'id': chat, 'is_bot': False, 'first_name': who.capitalize()} for who, chat in chats.items()}
            for person in people.values():
                api['chats'][person['id']] = {'id': person['id'], 'type': 'private', 'first_name': person['first_name']}

            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot149'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')
            adapter = A.EdgeSigner(S, CM, conn, config_path, 'edge-telegram', keyfile['edge-auth'])
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot149'), conn,
                                   'authority', journal_sign, 'telegram-edge', adapter)

            # The project service, given the settlement service where its constructor takes one (the
            # pre-change tree's does not, and has no settled path).
            extra = {'settlement': settlement} if 'settlement' in inspect.signature(PJ.Projects).parameters else {}
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False,
                                   **extra)
            missing = {'ok': False, 'reason': 'no_settled_activation', 'stops': [], 'obligations': []}

            def canonical(value):
                return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')

            def spelled_digest(value):
                return 'sha256:' + hashlib.sha256(canonical(value)).hexdigest()

            def signed_command(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            def journal():
                return [tuple(r) for r in conn.execute('SELECT seq, record_digest FROM journal ORDER BY seq')]

            def entity(eid):
                row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

            def project(name):
                found = entity('project:' + name)
                return dict(found['data'], version=found['version'], kind=found['kind']) if found else None

            def fields(name, repository, **over):
                f = dict(owner='owner', charter={'purpose': 'Deliver the %s journey.' % name, 'exclusions': ['billing']},
                         execution_repository=repository,
                         authority_policy={'grooming': ['project_owner'], 'admission': ['admission_authority']},
                         coordination_budget={'capacity': 4, 'invocations': 40, 'wall_seconds': 3600, 'owner_minutes': 120})
                f.update(over)
                return f

            def activate(name, repository, who='owner', **over):
                body = dict(ids, operation='activate', project=name, principal=who, command_id=next_id('pc'),
                            nonce=next_id('pn'), **fields(name, repository, **over))
                return projects.apply(signed_command(who, body))

            def activate_settled(rid):
                return projects.activate_settled(rid) if hasattr(projects, 'activate_settled') else dict(missing)

            # Real Git repositories, each enrolled through its signed VELDO-0029 binding naming this store.
            def repo(label):
                path = base / 'repos' / label
                path.mkdir(parents=True)
                GP.run(['git', 'init', '-q', str(path)], check=True, capture_output=True)
                (path / 'README').write_text('%s\n' % label)
                GP.run(['git', '-C', str(path), 'add', 'README'], check=True, capture_output=True)
                GP.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', label], check=True,
                       capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
                return path

            def enroll_sign(data):
                return sign_as('owner', data, 'veldo-enrollment')

            def enroll_verify(data, signature):
                return verifies('owner', 'veldo-enrollment', data, signature)

            workspaces, resolved = {}, {}

            def adopt(label, domain, bind):
                """Enroll a real clone of repository-<label> in `domain` and, when asked, bind it to the store
                for that domain from the repository its verified binding names."""
                path = repo(label)
                EN.enroll(str(path), domain, STORE, str(db), HOST, 1, enroll_sign, 'owner', time.time(),
                          repository_uuid='repository-' + label)
                resolved[label] = EN.resolve_store(str(path), enroll_verify, HOST, domain_uuid=domain, store_uuid=STORE)
                binding = EN.read_binding(str(path))
                if bind:
                    S.bind_repositories(conn, domain, {binding['repository_uuid']: str(path)})
                workspaces[label] = os.path.realpath(str(path))
                return binding['repository_uuid']

            for label in ('alpha', 'beta', 'epsilon', 'zeta', 'eta', 'theta'):
                adopt(label, DOMAIN, bind=True)
            adopt('gamma', DOMAIN, bind=False)
            adopt('delta', OTHER, bind=True)

            # AC1: any repository adopted in this domain, and nothing else.
            with region('adopted/two-repositories', 'adopted/unadopted-refused', 'adopted/observed'):
                tide = activate('tide', 'repository-alpha')
                reef = activate('reef', 'repository-beta')
                t, r = project('tide') or {}, project('reef') or {}
                check('adopted/two-repositories', [
                    ('both clones resolve through their signed bindings to this store',
                     resolved.get('alpha') == os.path.realpath(str(db)) and resolved.get('beta') == os.path.realpath(str(db))),
                    ('the store binds each for this domain to its own clone',
                     S.bound_repository(conn, DOMAIN, 'repository-alpha') == workspaces['alpha']
                     and S.bound_repository(conn, DOMAIN, 'repository-beta') == workspaces['beta']),
                    ('the owner\'s signed activation on the first is accepted', tide.get('ok') is True),
                    ('the owner\'s signed activation on the second is accepted', reef.get('ok') is True),
                    ('each is one ACTIVE project of the owner bound to its repository',
                     t.get('state') == 'ACTIVE' and t.get('owner') == 'owner' and t.get('execution_repository') == 'repository-alpha'
                     and r.get('state') == 'ACTIVE' and r.get('owner') == 'owner'
                     and r.get('execution_repository') == 'repository-beta'),
                    ('every field is bound as signed', all(t.get(f) == fields('tide', 'repository-alpha')[f] for f in SPEC_FIELDS)
                     and all(r.get(f) == fields('reef', 'repository-beta')[f] for f in SPEC_FIELDS)),
                    ('exactly one record of each', conn.execute(
                        "SELECT COUNT(*) FROM entities WHERE kind='project' AND id IN ('project:tide', 'project:reef')").fetchone()[0] == 2)])

                before = journal()
                unadopted = {'enrolled-unbound': activate('kelp', 'repository-gamma'),
                             'bound-in-another-domain': activate('kelp', 'repository-delta'),
                             'never-enrolled': activate('kelp', 'repository-nowhere')}
                after = journal()
                control = activate('kelp', 'repository-epsilon')
                check('adopted/unadopted-refused', [
                    ('the enrolled clone the store never bound resolves, and is unbound',
                     resolved.get('gamma') == os.path.realpath(str(db)) and S.bound_repository(conn, DOMAIN, 'repository-gamma') is None),
                    ('the clone bound in another domain is bound there only',
                     S.bound_repository(conn, OTHER, 'repository-delta') == workspaces['delta']
                     and S.bound_repository(conn, DOMAIN, 'repository-delta') is None)] + [
                    ('%s refuses invalid_input:execution_repository' % case,
                     result.get('ok') is False and result.get('reason') == 'invalid_input:execution_repository')
                    for case, result in unadopted.items()] + [
                    ('none of them writes anything', after == before),
                    ('control: the same activation on a repository the store binds for this domain is accepted',
                     control.get('ok') is True and (project('kelp') or {}).get('execution_repository') == 'repository-epsilon')])

                activations = [o for o in projects.observations if o.get('operation') == 'activate']
                seen = {(o.get('project'), o.get('execution_repository'), o.get('outcome')): o for o in activations}
                accepted = seen.get(('project:tide', 'repository-alpha', 'accepted')) or {}
                refused = seen.get(('project:kelp', 'repository-gamma', 'refused')) or {}
                metrics = projects.metrics()
                tally = (metrics.get('activations') or {}).get('signed_command') or {}
                check('adopted/observed', [
                    ('the accepted activation names its project, repository, the binding that adopted it and its path',
                     accepted.get('path') == 'signed_command' and accepted.get('adoption') == {
                         'domain_uuid': DOMAIN, 'repository_uuid': 'repository-alpha', 'path': workspaces['alpha'],
                         'by': 'store_binding'}),
                    ('the refused one names its path, its refusal and its class, and no binding',
                     refused.get('path') == 'signed_command' and refused.get('refusal') == 'invalid_input:execution_repository'
                     and refused.get('taxonomy') == 'invalid_input' and refused.get('adoption') is None),
                    ('the signed-command activations are counted accepted and refused, by refusal',
                     tally.get('accepted') == 3 and tally.get('refused') == 3
                     and tally.get('refusals') == {'invalid_input:execution_repository': 3}),
                    ('no charter text or signature is observed', 'Deliver the' not in json.dumps(activations)
                     and 'SSH SIGNATURE' not in json.dumps(activations))])

            # AC2: the owner's settled answer to an activation request.
            def open_activation(alias, proposal, owner='owner'):
                """The requester's terms naming the activation, the inbox request, its framing and its
                presentation: (request id, presented receipt)."""
                target = {'kind': 'project_activation', 'ref': 'project:' + proposal['project'],
                          'digest': spelled_digest(proposal)}
                body = dict(ids, operation='terms', terms=alias, principal='pm', command_id=next_id('terms'),
                            nonce=next_id('terms-nonce'), touchpoint='decision_disposition', target=target,
                            proposal=proposal, required_roles=[], quorum=None)
                subject = settlement.terms(signed_command('pm', body)).get('subject')
                inbox.apply(signed_command('pm', dict(ids, operation='open', alias=alias, principal='pm',
                                                      command_id=next_id('c'), nonce=next_id('n'), assignment=dict(
                                                          kind='decision', owner=owner, scope=[proposal['project']],
                                                          deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                                          brief='Start project %s.' % proposal['project'],
                                                          choices=list(CHOICES), subject=subject))))
                rid = I.assignment_id(REPO, alias)
                frame(alias, 1)
                presenter.present(rid)
                return rid, presenter.current(rid) or {}

            def frame(alias, version):
                presenter.frame(signed_command('pm', dict(ids, operation='frame', alias=alias, principal='pm',
                                                          request_version=version,
                                                          risk_statement='Low: a wrong start costs one cancel.',
                                                          command_id=next_id('f'), nonce=next_id('fn'))))

            def revise(alias):
                rid = I.assignment_id(REPO, alias)
                inbox.apply(signed_command('pm', dict(ids, operation='revise', alias=alias, principal='pm',
                                                      command_id=next_id('c'), nonce=next_id('n'), request_version=1,
                                                      changes={'brief': 'Start project %s, revised.' % alias})))
                frame(alias, 2)
                presenter.present(rid)
                return presenter.current(rid) or {}

            def api_answer(receipt, choice, rationale, principal='owner'):
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('api'),
                            principal=principal, request_id=receipt.get('request_id'),
                            request_version=receipt.get('request_version'), presentation_id=receipt.get('presentation_id'),
                            presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice, rationale=rationale)
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def reply(receipt, text, who='owner'):
                sender = people[who]
                chat = api['chats'][sender['id']]
                with api['lock']:
                    bot['update_next'] += 1
                    update_id = bot['update_next']
                update = {'update_id': update_id,
                          'message': message(api, bot, sender, chat, text, (receipt.get('message_ids') or [None])[-1])}
                bot['updates'].append(update)
                return update

            def acquire():
                return {x['update_id']: (x.get('outcome'), x.get('reason')) for x in acquirer.acquire()
                        if x.get('update_id') is not None}

            def refused(result, reason, before, name):
                return (result.get('ok') is False and result.get('reason') == reason and journal() == before
                        and project(name) is None)

            with region('answer/activates', 'answer/binds-every-field', 'answer/unsettled', 'answer/owner-only',
                        'answer/stale', 'answer/observed'):
                cove_fields = fields('cove', 'repository-zeta')
                cove_rid, cove_receipt = open_activation('A-cove', dict(cove_fields, project='cove'))
                cove_answer = api_answer(cove_receipt, 'accept', 'start it on zeta')
                before = journal()
                cove = activate_settled(cove_rid)
                c, signed = project('cove') or {}, project('tide') or {}
                again_before = journal()
                again = activate_settled(cove_rid)
                sdata = (entity('request-settlement:%s:1' % cove_rid) or {}).get('data') or {}
                shared = ('state', 'charter_revision', 'domain_uuid', 'repository_uuid', 'stopping', 'kind', 'schema')
                check('answer/activates', [
                    ('the activation request is presented and the owner\'s API answer settles it',
                     cove_receipt.get('outcome') == 'published' and cove_answer.get('outcome') == 'settled'
                     and sdata.get('principals') == ['owner'] and sdata.get('ruling') == 'approve'),
                    ('the settlement applies one activation', cove.get('ok') is True and journal()[:len(before)] == before
                     and len(again_before) == len(before) + 1),
                    ('it creates one ACTIVE project of the owner on the store-bound repository',
                     c.get('state') == 'ACTIVE' and c.get('owner') == 'owner' and c.get('execution_repository') == 'repository-zeta'),
                    ('it binds owner, charter, execution repository, authority policy and finite budget as proposed',
                     all(c.get(f) == cove_fields[f] for f in SPEC_FIELDS)),
                    ('its record is the signed command\'s record: the same fields, digest and state',
                     set(c) == set(signed) and all(c.get(k) == signed.get(k) for k in shared)
                     and c.get('charter_digest') == spelled_digest(cove_fields['charter'])
                     and [(h.get('source'), h.get('target'), h.get('by')) for h in c.get('history') or []]
                     == [('DRAFT', 'ACTIVE', 'owner')]),
                    ('its provenance names the settlement it came from',
                     (c.get('provenance') or {}).get('source') == 'settled_answer'
                     and (c.get('provenance') or {}).get('settlement_id') == sdata.get('settlement_id')
                     and (c.get('provenance') or {}).get('receipt_id') == sdata.get('receipt_id')),
                    ('applying the same settlement again refuses already_exists and writes nothing',
                     again.get('ok') is False and again.get('reason') == 'already_exists' and journal() == again_before)])

                omitted = {}
                for f in SPEC_FIELDS:
                    proposal = dict(fields('moor', 'repository-theta'), project='moor')
                    proposal.pop(f)
                    rid, receipt = open_activation('A-moor-' + f.replace('_', '-'), proposal)
                    settled_ = api_answer(receipt, 'accept', 'start it')
                    before = journal()
                    omitted[f] = (settled_.get('outcome') == 'settled'
                                  and refused(activate_settled(rid), 'missing_field:' + f, before, 'moor'))
                check('answer/binds-every-field', [
                    ('the request omitting %s is settled, and refuses missing_field:%s with nothing written' % (f, f),
                     omitted[f]) for f in SPEC_FIELDS])

                glen_rid, _glen_receipt = open_activation('A-glen', dict(fields('glen', 'repository-theta'), project='glen'))
                before = journal()
                none = activate_settled(glen_rid)
                none_ok = refused(none, 'unsettled:no_answer', before, 'glen')
                dune_fields = fields('dune', 'repository-eta')
                dune_rid, dune_receipt = open_activation('A-dune', dict(dune_fields, project='dune'))
                dune_update = reply(dune_receipt, 'accept: start dune on eta')
                dune_acquired = acquire()
                before = journal()
                pending = activate_settled(dune_rid)
                pending_ok = refused(pending, 'unsettled:not_settled', before, 'dune')
                dune_settled = settlement.settle(dune_rid)
                dune = activate_settled(dune_rid)
                rill_rid, rill_receipt = open_activation('A-rill', dict(fields('rill', 'repository-theta'), project='rill'))
                rejected = api_answer(rill_receipt, 'reject', 'not now')
                before = journal()
                no = activate_settled(rill_rid)
                check('answer/unsettled', [
                    ('a presented request nobody answered refuses unsettled:no_answer, nothing written', none_ok),
                    ('the owner\'s Telegram reply is accepted as his answer',
                     dune_acquired.get(dune_update['update_id']) == ('answered', None)),
                    ('answered but not yet settled refuses unsettled:not_settled, nothing written', pending_ok),
                    ('control: once the settlement settles his reply, the same request activates',
                     dune_settled.get('outcome') == 'settled' and dune.get('ok') is True
                     and (project('dune') or {}).get('execution_repository') == 'repository-eta'),
                    ('a settled rejection refuses not_approved:reject, nothing written',
                     rejected.get('outcome') == 'settled' and refused(no, 'not_approved:reject', before, 'rill'))])

                heath_rid, heath_receipt = open_activation('A-heath', dict(fields('heath', 'repository-theta'), project='heath'),
                                                           owner='owner2')
                other = api_answer(heath_receipt, 'accept', 'start it for him', principal='owner2')
                other_data = (entity('request-settlement:%s:1' % heath_rid) or {}).get('data') or {}
                before = journal()
                by_other = activate_settled(heath_rid)
                by_other_ok = refused(by_other, 'not_owner', before, 'heath')
                fern_rid, fern_receipt = open_activation('A-fern', dict(fields('fern', 'repository-theta', owner='owner2'),
                                                                        project='fern'))
                for_other = api_answer(fern_receipt, 'accept', 'start it with owner2 owning it')
                before = journal()
                binds_other = activate_settled(fern_rid)
                check('answer/owner-only', [
                    ('a settlement answered by another current owner-role member exists',
                     other.get('outcome') == 'settled' and other_data.get('principals') == ['owner2']),
                    ('it refuses not_owner: he is not the owner the activation binds, and nothing is written', by_other_ok),
                    ('an answer by one member for a project another would own refuses not_owner, nothing written',
                     for_other.get('outcome') == 'settled' and refused(binds_other, 'not_owner', before, 'fern'))])

                vale_rid, vale_first = open_activation('A-vale', dict(fields('vale', 'repository-theta'), project='vale'))
                vale_update = reply(vale_first, 'accept: start vale')
                vale_acquired = acquire()
                vale_second = revise('A-vale')
                run = [x for x in settlement.run() if x.get('request_id') == vale_rid]
                before = journal()
                stale = activate_settled(vale_rid)
                check('answer/stale', [
                    ('the owner answered the first presentation', vale_acquired.get(vale_update['update_id']) == ('answered', None)),
                    ('the request was revised and presented again, superseding what he answered',
                     vale_second.get('presentation_version') == 2 and vale_second.get('presentation_id') != vale_first.get('presentation_id')),
                    ('nothing settles the revised version', run == []
                     and entity('request-settlement:%s:2' % vale_rid) is None),
                    ('it refuses stale_answer, nothing written', refused(stale, 'stale_answer', before, 'vale'))])

                answered = [o for o in projects.observations if o.get('path') == 'settled_answer']
                accepted = next((o for o in answered if o.get('project') == 'project:cove' and o.get('outcome') == 'accepted'), {})
                classes = {o.get('refusal'): o.get('taxonomy') for o in answered if o.get('outcome') == 'refused'}
                tally = ((projects.metrics().get('activations') or {}).get('settled_answer')) or {}
                text = json.dumps(answered)
                check('answer/observed', [
                    ('the accepted activation names its request, settlement, receipt, presentation, repository and binding',
                     accepted.get('request_id') == cove_rid and accepted.get('settlement_id') == sdata.get('settlement_id')
                     and accepted.get('receipt_id') == sdata.get('receipt_id')
                     and accepted.get('presentation_id') == cove_receipt.get('presentation_id')
                     and accepted.get('execution_repository') == 'repository-zeta'
                     and accepted.get('adoption') == {'domain_uuid': DOMAIN, 'repository_uuid': 'repository-zeta',
                                                      'path': workspaces['zeta'], 'by': 'store_binding'}),
                    ('a missing field, an unsettled answer, another member\'s answer and a stale answer are distinct classes',
                     classes.get('missing_field:owner') == 'invalid_input' and classes.get('unsettled:no_answer') == 'missing_evidence'
                     and classes.get('not_owner') == 'missing_authority' and classes.get('stale_answer') == 'stale_subject'),
                    ('the settled-answer activations are counted accepted and refused, by refusal',
                     tally.get('accepted') == 2 and tally.get('refused') == 12
                     and (tally.get('refusals') or {}).get('not_owner') == 2
                     and (tally.get('refusals') or {}).get('already_exists') == 1),
                    ('no rationale, charter text or signature is observed',
                     'start it' not in text and 'Deliver the' not in text and 'SSH SIGNATURE' not in text)])
        finally:
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
            for conn in connections:
                with contextlib.suppress(Exception):
                    conn.close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])


_v149_started = __import__('time').monotonic()
_v149_suite()
print('VELDO-0149 suite seconds: %.3f' % (__import__('time').monotonic() - _v149_started))
