"""VELDO-0151 specialist roles through real signed team and capability writers.
No model or credential fixture is used.
"""

def _v151_suite():
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
    PRODUCTION = {'control_team.py': ROOT / ".veldo" / "control_team.py"}
    SCAFFOLD = ROOT / ".veldo" / "init_scaffold.py"
    PREFIX = 'VELDO-0151 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    # The role fields the specification names (AC1), compared with the service's own schema.
    SPEC_FIELDS = ('workers', 'responsibilities', 'expertise', 'proposal_permissions', 'engines', 'budget', 'independence',
                   'capability_configuration', 'kind')

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
            if name != 'bot89':
                return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
            if method == 'getMe':
                return self._answer(200, {'ok': True, 'result': dict(st['user'], can_join_groups=True)})
            if method == 'getUpdates':
                return self._answer(200, {'ok': True, 'result': []})
            if method == 'sendMessage':
                chat = {'id': body.get('chat_id'), 'type': 'private'}
                reply = (body.get('reply_parameters') or {}).get('message_id')
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
    with tempfile.TemporaryDirectory(prefix='v89-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        try:
            claims = load('v89_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v89_keys', mods / 'control_keys.py')
            I = load('v89_inbox', mods / 'control_assignment.py')
            P = load('v89_projection', mods / 'control_channel_projection.py')
            V = load('v89_presentation', mods / 'control_channel_presentation.py')
            ST = load('v89_settlement', mods / 'control_request_settlement.py')
            PJ = load('v89_project', mods / 'control_project.py')
            DSP = load('v89_dispatch', mods / 'dispatch.py')
            contract = load('v89_contract', mods / 'entity_contract.py')
            CT = load('v89_team', mods / 'control_team.py') if (mods / 'control_team.py').is_file() else None
            DOMAIN, REPO = 'domain-89', 'repository-89'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-89')

            keys = base / 'keys'
            keys.mkdir(mode=0o700)
            people = ('steward', 'olga', 'zed')
            services = ('pm', 'api-edge', 'team-service')
            agents = ('w-elab', 'w-build', 'w-build2', 'w-rev1', 'w-rev2', 'w-rev3', 'w-late', 'outsider')
            keyfile = {who: keys / who for who in ('authority',) + people + services + agents}
            public = {}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v89-' + who, '-f', str(path)],
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

            def enroll(who, principal_type, roles, scope, group=None):
                admin('steward', 'enroll_principal', {'principal': who, 'principal_type': principal_type, 'roles': roles,
                                                      'public_key': public[who], 'independence_group': group or who,
                                                      'scope': scope}, enrollee=who)

            admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                                  'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                                  'independence_group': 'steward', 'scope': '*'})
            enroll('olga', 'person', ['project_owner', 'admission_authority'], ['proj-a'])
            enroll('zed', 'person', ['project_owner'], ['proj-a'])
            for who in services:
                enroll(who, 'service', [], ['proj-a', 'proj-b'] if who == 'team-service' else ['proj-a'])
            for who in ('w-elab', 'w-build', 'w-build2', 'w-rev1', 'w-rev2', 'w-late'):
                enroll(who, 'agent_run', [], ['proj-a'])
            enroll('w-rev3', 'agent_run', [], ['proj-a'], group='w-build')
            enroll('outsider', 'agent_run', [], ['proj-b'])

            def fixture(eid, kind, data):
                row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: row[0] if row else 0}, artifact_digests=[],
                                            nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

            for who, chat in (('olga', 5890001), ('zed', 5890002)):
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))

            api = {'tick': 0, 'next': 9000, 'messages': {}, 'lock': threading.Lock(),
                   'user': {'id': 8000000089, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_team_bot'}}
            handler = type('V89Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]

            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot89'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)

            def signed(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            projects.apply(signed('olga', dict(
                ids, operation='activate', project='proj-a', principal='olga', command_id=next_id('pc'), nonce=next_id('pn'),
                owner='olga', charter={'purpose': 'Sell passes to travelers.'}, execution_repository=REPO,
                authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
                coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))

            service = (CT.Teams(S, CM, conn, ids, 'authority', journal_sign, inbox=inbox, assignment=I,
                                requester='team-service', request_sign=lambda m: sign_as('team-service', m))
                       if CT is not None else None)

            def send(who, op, **fields):
                body = dict(ids, operation=op, project='proj-a', principal=who, command_id=next_id('tc'),
                            nonce=next_id('tn'), **fields)
                return service.apply(signed(who, body)) if service is not None else {'ok': False, 'reason': 'no_team_service'}

            def entity(eid):
                row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}

            def team_record():
                row = entity('team:proj-a')
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'team' else {}

            def version():
                return team_record().get('version', 0)

            def authority_rows():
                """Every membership, delegation and key row and the authority versions: (id, version, digest)."""
                return [tuple(r) for r in conn.execute(
                    "SELECT id, version, digest FROM entities WHERE kind IN ('membership', 'delegation', 'verification_key')"
                    " OR id=? ORDER BY id", (CM.VERSIONS_ENTITY,))]

            def requests_named(kind):
                return [(eid, json.loads(d)) for eid, d in conn.execute("SELECT id, data FROM entities WHERE kind='assignment'")
                        if (json.loads(d).get('subject') or {}).get('kind') == kind]

            CG = load('team_fixture_config', mods / 'control_agent_config.py')
            configurations = CG.Configurations(S, conn, domain=ids['domain_uuid'],
                repository=ids['repository_uuid'], signer='authority', sign=journal_sign)
            configurations.save(dict(role='team-fixture', engine='claude_code', native_tools=[],
                mcp=[], skills=[], instructions=[], settings={}), principal='steward', base=0,
                command_id=next_id('capability'))

            def role(workers, resp, perms=('feature',), engines=('claude_code',), budget=None, distinct=()):
                return dict(kind='required', capability_configuration={'role': 'team-fixture', 'revision': 1}, workers=list(workers), responsibilities=[resp, 'report'], expertise=['python', 'payments'],
                            proposal_permissions=list(perms), engines=list(engines),
                            budget=dict(budget or {'capacity': 1, 'invocations': 2, 'wall_seconds': 100}),
                            independence={'distinct_from': list(distinct)})

            def team(**roles):
                value = {'project_manager': role(['pm'], 'coordinate', ('objective', 'feature', 'team_amendment')),
                         'elaboration': role(['w-elab'], 'elaborate'),
                         'implementation': role(['w-build', 'w-build2'], 'implement', ('finding',)),
                         'independent_review': role(['w-rev1', 'w-rev2'], 'review', ('finding',), ('claude_code', 'codex'),
                                                    distinct=('implementation',))}
                for name, spec in roles.items():
                    if spec is None:
                        value.pop(name, None)
                    else:
                        value[name] = spec
                return {'roles': value}

            def propose(value, who='pm', team_version=None):
                return send(who, 'propose', team_version=version() if team_version is None else team_version, team=value)

            def target_and_brief():
                record = team_record()
                if CT is None or not record.get('proposal'):
                    return {'kind': 'team', 'ref': 'team:proj-a', 'digest': 'sha256:none'}, 'Accept the team of proj-a.'
                return CT.amendment_target(record), CT.amendment_brief(record)

            def present(alias, target, brief, owner='olga'):
                """The requester's terms, the inbox request with its framing, and its presentation."""
                terms = settlement.terms(signed('pm', dict(ids, operation='terms', terms=alias, principal='pm',
                                                           command_id=next_id('terms'), nonce=next_id('tn'),
                                                           touchpoint='decision_disposition', target=target, proposal=None,
                                                           required_roles=[], quorum=None)))
                inbox.apply(signed('pm', dict(ids, operation='open', alias=alias, principal='pm', command_id=next_id('c'),
                                              nonce=next_id('n'), assignment=dict(
                                                  kind='decision', owner=owner, scope=['proj-a'],
                                                  deadline='2026-10-30T17:00:00Z', budget={'owner_minutes': 15}, brief=brief,
                                                  choices=list(CHOICES), subject=terms.get('subject') or {}))))
                rid = I.assignment_id(REPO, alias)
                presenter.frame(signed('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                                  risk_statement='Low: a wrong roster costs one planning cycle.',
                                                  command_id=next_id('f'), nonce=next_id('fn'))))
                presenter.present(rid)
                return rid, presenter.current(rid) or {}

            def answer(receipt, choice, who='olga'):
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('ans'),
                            principal=who, request_id=receipt.get('request_id'), request_version=receipt.get('request_version'),
                            presentation_id=receipt.get('presentation_id'), presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice,
                            rationale='I have read the roster, its budgets and its separation.')
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def settle(alias, owner='olga', target=None, brief=None, choice='accept'):
                t, b = target_and_brief()
                rid, receipt = present(alias, target or t, brief or b, owner)
                return rid, answer(receipt, choice, owner)

            def amend(rid, who='pm', **over):
                record = team_record()
                proposal = record.get('proposal') or {}
                fields = dict(team_version=record.get('version', 0), revision=proposal.get('revision'),
                              digest=proposal.get('digest'), request=rid)
                fields.update(over)
                return send(who, 'amend', **fields)

            child_script = base / 'read_team.py'
            child_script.write_text('''import importlib.util, json, sys
from pathlib import Path
def load(name):
    s = importlib.util.spec_from_file_location(name, Path(sys.argv[1]) / (name + '.py'))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
st = load('control_store')
if not (Path(sys.argv[1]) / 'control_team.py').is_file():
    print(json.dumps({'refusal': 'no_team_module'})); sys.exit(0)
ct = load('control_team')
c = st.open_store(sys.argv[2], mode='r')
print(json.dumps({'team': ct.read(st, c, 'proj-a'), 'assignments': ct.assignments(c)}))
c.close()
''')

            def other_process():
                done = subprocess.run([sys.executable, '-B', str(child_script), str(mods), str(db)],
                                      capture_output=True, text=True, timeout=60)
                return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else {'error': done.stderr[-400:]}

            def refused(result, reason):
                return result.get('ok') is False and result.get('reason') == reason

            def staffing_refused(result, problem, before_authority):
                """Refused by name, with an owner request naming the problem, no team and no new principal."""
                rid = result.get('owner_request')
                request = (entity(rid) or {}).get('data') or {}
                return (result.get('ok') is False and str(result.get('reason')).startswith('incomplete_roster:')
                        and problem in (result.get('problems') or []) and request.get('owner') == 'olga'
                        and request.get('state') == 'OFFERED' and problem in str(request.get('brief'))
                        and (request.get('subject') or {}).get('kind') == 'team_staffing'
                        and not team_record() and authority_rows() == before_authority)

            # Each behavioral row contains its successful real-writer control when needed.
            def accept(value):
                proposed = propose(value)
                if not proposed.get('ok'):
                    return proposed
                rid, settled = settle(next_id('TEAM'))
                result = amend(rid) if settled.get('outcome') == 'settled' else settled
                if not result.get('ok'):
                    print('  VELDO-0151 detail: acceptance result: %r' % result)
                return result

            def specialist(name):
                result = role(['w-build2'], 'implement')
                result.update(kind='specialist', capability_configuration={'role': name, 'revision': 1})
                return result

            for name in ('designer', 'ios_builder', 'builder_jira'):
                configurations.save(dict(role=name, engine='claude_code', native_tools=[], mcp=[], skills=[],
                    instructions=[], settings={}), principal='steward', base=0, command_id=next_id('config'))
            roster = team(**{name: specialist(name) for name in ('designer', 'ios_builder', 'builder_jira')})
            authority_before = authority_rows()

            with region('roles/required-only'):
                accepted = accept(team())
                current = team_record()
                check('roles/required-only', [
                    ('accepted four required roles', accepted.get('ok') and current.get('team') == team()),
                    ('exact schema fields', tuple(CT.ROLE_FIELDS) == SPEC_FIELDS),
                    ('every reference resolves through 0127', all(CG.read(conn, DOMAIN, REPO,
                        r['capability_configuration']['role'], r['capability_configuration']['revision'])
                        for r in team()['roles'].values())),
                    ('no authority granted', authority_rows() == authority_before)])

            with region('roles/specialists'):
                accepted = accept(roster)
                current = team_record()
                check('roles/specialists', [
                    ('all specialist names accepted', accepted.get('ok') and current.get('team') == roster),
                    ('history keeps required-only revision', len(current.get('revisions', [])) == 2
                        and current['revisions'][0]['team'] == team()),
                    ('no authority granted', authority_rows() == authority_before),
                    ('specialist count', service.metrics().get('specialists', {}).get('proj-a') == 3)])

            def rejected_team(label, value, problem):
                with region(label):
                    before = team_record()
                    before_assignments = CT.assignments(conn)
                    first = propose(value)
                    second = propose(value)
                    rid = first.get('owner_request')
                    request = (entity(rid) or {}).get('data', {})
                    check(label, [
                        ('refuses by reason', first.get('ok') is False and problem in first.get('problems', [])),
                        ('one request to current owner', rid is not None and second.get('owner_request') == rid
                            and request.get('owner') == 'olga' and request.get('state') == 'OFFERED'),
                        ('request names problem', problem in request.get('brief', '')),
                        ('no team revision accepted', team_record() == before),
                        ('assigns nothing', CT.assignments(conn) == before_assignments),
                        ('no worker or authority invented', authority_rows() == authority_before)])

            value = copy.deepcopy(roster)
            value['roles']['designer']['workers'] = ['outsider']
            rejected_team('roles/specialist-outside-project', value, 'unknown_worker:designer/outsider')

            for name in ('implementation', 'designer'):
                value = copy.deepcopy(roster)
                value['roles'][name].pop('capability_configuration')
                rejected_team('roles/missing-reference/' + name, value, 'missing_capability_configuration:' + name)
                value = copy.deepcopy(roster)
                value['roles'][name]['capability_configuration']['revision'] = 987
                rejected_team('roles/unresolved-reference/' + name, value, 'unresolved_capability_configuration:' + name)
                for kind in ('unknown', 'specialist' if name == 'implementation' else 'required', None):
                    value = copy.deepcopy(roster)
                    value['roles'][name]['kind'] = kind
                    rejected_team('roles/kind/' + name + '/' + str(kind), value, 'invalid_kind:' + name)
            value = copy.deepcopy(roster)
            value['roles']['designer']['capability_configuration'] = {'role': 'designer'}
            rejected_team('roles/unversioned-reference', value, 'invalid_capability_configuration:designer')
            for required in ('project_manager', 'elaboration', 'implementation', 'independent_review'):
                value = copy.deepcopy(roster)
                value['roles'].pop(required)
                rejected_team('roles/required-still-required/' + required, value, 'missing_staffing:' + required)

            with region('roles/brief-and-authority'):
                proposed = propose(roster)
                brief = target_and_brief()[1]
                good_brief = all(name in brief for name in ('designer', 'ios_builder', 'builder_jira'))
                good_brief = good_brief and 'specialist' in brief and 'capability configuration' in brief
                bad = copy.deepcopy(roster)
                bad['roles']['designer']['proposal_permissions'] = ['admission_authority']
                rejected = propose(bad)
                tool = copy.deepcopy(roster)
                tool['roles']['designer']['tools'] = ['Bash']
                filtered = propose(tool)
                check('roles/brief-and-authority', [
                    ('owner sees specialist kind and revision', proposed.get('ok') and good_brief),
                    ('roster cannot grant admission', rejected.get('ok') is False
                        and 'roster_not_authority:designer/admission_authority' in rejected.get('problems', [])),
                    ('no second tool filter', filtered.get('ok') is False
                        and 'invalid_input:field:designer/tools' in filtered.get('problems', [])),
                    ('authority unchanged', authority_rows() == authority_before)])

            # The real intake, objective and backlog writers create the unit.
            IN = load('v151_intake', mods / 'control_intake.py')
            OB = load('v151_objective', mods / 'control_objective.py')
            CB = load('v151_backlog', mods / 'control_backlog.py')
            EV = load('v151_attribution', mods / 'control_channel_attribution.py')
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot89'),
                conn, 'authority', journal_sign, 'api-edge', lambda m: sign_as('api-edge', m))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=['proj-a'],
                              api_edge='api-edge', journal_signer='authority', sign=journal_sign)
            message_body = dict(schema=IN.API_SCHEMA, domain=DOMAIN, request_id=next_id('intake'),
                edge='api-edge', principal='olga', text='For proj-a: design the checkout.', project=None, clarifies=None)
            received = intake.receive('api_request', dict(request=message_body,
                signature=sign_as('api-edge', S.canonical_bytes(message_body))))
            objectives = OB.Objectives(S, CM, conn, ids, 'authority', journal_sign)

            def command(who, operation, **fields):
                return signed(who, dict(ids, operation=operation, principal=who,
                    command_id=next_id('work'), nonce=next_id('work-nonce'), **fields))

            proposed = objectives.apply(command('olga', 'propose', proposal=received.get('proposal_id'),
                outcome='A traveler buys a pass.', scope=['design'], authority={'acceptor': 'olga', 'assessor': 'zed'},
                evidence_requirements=[{'id': 'outcome', 'kind': 'gate_observation'}]))
            oid = proposed.get('objective_id')
            objective = OB.read(conn, oid) or {}
            source_key = IN.source_key('api_request', message_body['request_id'])
            intake_command = next((c for c, transition in conn.execute('SELECT command_id, transition FROM journal')
                                   if source_key in json.loads(transition)), None)
            objectives.apply(command('olga', 'accept_message', objective=oid,
                objective_version=objective.get('version'), revision=objective.get('revision'),
                bound_digest=objective.get('bound_digest'), intake_command=intake_command))
            feature = objectives.apply(command('olga', 'propose_feature', objective=oid,
                objective_version=(OB.read(conn, oid) or {}).get('version'), feature='design',
                title='Design checkout', scope=['design']))
            backlog = CB.Backlog(S, CM, conn, ids, 'authority', journal_sign)
            taken = backlog.apply(command('olga', 'take', feature=feature.get('feature_id'), work_class='PRODUCT_CHANGE'))
            uid = 'VELDO-9151'
            raw_unit = dict(unit=uid, specification=uid, scope=['design'], requirements=[],
                            eligible_holders=['w-build2'])
            prepared = backlog.apply(command('olga', 'prepare', item=taken.get('item_id'),
                item_version=(taken.get('item') or {}).get('version'), units=[raw_unit]))
            unit = (entity(uid) or {}).get('data', {})
            # No production writer supplies the team's risk input yet. Decorate the real unit,
            # retaining its complete provenance, with the risk that selects the review policy.
            fixture(uid, 'execution_unit', dict(unit, risk='critical'))
            subject = {k: unit.get(k) for k in ('revision', 'scope_digest')}
            subject['unit'] = uid

            def assign(name='designer', builder='w-build2', reviewers=('w-rev1', 'w-rev2'), **extra):
                fields = dict(team_version=version(), team_revision=team_record().get('revision'), unit=uid,
                    role=name, builder=builder, subject=subject,
                    reviewers=[dict(reviewer=r, subject=subject) for r in reviewers])
                fields.update(extra)
                return send('pm', 'assign', **fields)

            with region('assignment/policy'):
                missing = assign()
                policy = DSP.review_policy_record(ROOT / '.veldo/policy.yaml')
                fixture(DSP.review_policy_id(REPO), DSP.REVIEW_POLICY_KIND, policy)
                few = assign(reviewers=('w-rev1',))
                same = assign(builder='w-rev1')
                wrong = assign(subject=dict(subject, revision=0))
                valid = assign()
                check('assignment/policy', [
                    ('real backlog unit and specialist assignment', prepared.get('ok') and valid.get('ok')),
                    ('missing policy refuses', refused(missing, 'missing_authority:review_policy')),
                    ('review count enforced', refused(few, 'insufficient_reviews:1/2')),
                    ('independence enforced', str(same.get('reason')).startswith('reviewer_not_independent:')),
                    ('exact subject enforced', refused(wrong, 'wrong_subject:builder'))])

            with region('assignment/bindings'):
                old = team_record()
                changed = copy.deepcopy(roster)
                configuration = configurations.save(dict(role='designer', engine='claude_code', native_tools=[],
                    mcp=[], skills=[], instructions=[], settings={'model': 'fixture-model'}), principal='steward',
                    base=1, command_id=next_id('config'))
                before_update = assign()
                changed['roles']['designer']['capability_configuration']['revision'] = 2
                accepted = accept(changed)
                current = team_record()
                stale = assign(team_revision=old.get('revision'))
                bound = assign()
                value = bound.get('assignment', {})
                check('assignment/bindings', [
                    ('team amendment accepted', accepted.get('ok')),
                    ('existing reference does not float to head', before_update.get('assignment', {}).get(
                        'capability_configuration') == {'role': 'designer', 'revision': 1}),
                    ('role and worker bound', bound.get('ok') and value.get('role') == 'designer'
                        and value.get('builder') == 'w-build2'),
                    ('configuration revision bound', value.get('capability_configuration') ==
                        {'role': 'designer', 'revision': 2}),
                    ('current team bound', value.get('team') == {k: current.get(k) for k in ('revision', 'version', 'digest')}),
                    ('policy and exact subject bound', value.get('subject') == subject and
                        value.get('policy', {}).get('required_reviews') == 2),
                    ('stale team refuses', refused(stale, 'stale_subject:team_revision')),
                    ('stored reader sees exact binding', any(a.get('role') == 'designer' and
                        a.get('capability_configuration') == {'role': 'designer', 'revision': 2}
                        for a in other_process().get('assignments', [])))])

            with region('assignment/reviewer-capability-binding'):
                bound = assign()
                value = bound.get('assignment', {})
                expected = {'role': 'team-fixture', 'revision': 1}
                check('assignment/reviewer-capability-binding', [
                    ('specialist assignment accepted', bound.get('ok')),
                    ('reviewer reference differs from builder',
                        value.get('capability_configuration') == {'role': 'designer', 'revision': 2}),
                    ('reviewer configuration revision bound',
                        value.get('reviewer_capability_configuration') == expected),
                    ('stored reader sees exact reviewer binding', any(
                        {k: v for k, v in a.items() if k not in ('id', 'version')} == value
                        and a.get('reviewer_capability_configuration') == expected
                        for a in other_process().get('assignments', [])))])

            with region('assignment/unlisted-worker'):
                result = assign(builder='w-build')
                check('assignment/unlisted-worker', [
                    ('specialist role accepted', team_record().get('revision') == 3),
                    ('worker must belong to selected role', refused(result, 'not_staffed:designer/w-build'))])

            with region('assignment/staffing-request'):
                before = CT.assignments(conn)
                missing = assign(name='android_builder')
                repeated = assign(name='android_builder')
                rid = missing.get('owner_request')
                request = (entity(rid) or {}).get('data', {})
                check('assignment/staffing-request', [
                    ('missing specialist refuses', refused(missing, 'not_staffed:role:android_builder')),
                    ('one current-owner request', rid is not None and repeated.get('owner_request') == rid
                        and request.get('owner') == 'olga' and request.get('state') == 'OFFERED'),
                    ('names missing role', 'missing_role:android_builder' in request.get('brief', '')),
                    ('assigns nothing', CT.assignments(conn) == before),
                    ('invents no worker or authority', authority_rows() == authority_before)])
            with region('roles/observability'):
                metrics = service.metrics()
                observations = service.observations
                reference_id = CG.identity(DOMAIN, REPO, CG.KINDS[0], 'designer', 2)
                check('roles/observability', [
                    ('accepted revisions counted', metrics.get('revisions_accepted') == 3),
                    ('refused revisions counted', metrics.get('revisions_refused', 0) >= 12),
                    ('staffing request reasons counted once', metrics.get('staffing_requests_by_reason', {}).get(
                        'missing_role') == 1),
                    ('capability revision pinned on assignment', any(reference_id in o['accepted_versions']
                        for o in observations if o['operation'] == 'assign'))])
        finally:
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
            for c in connections:
                with contextlib.suppress(Exception):
                    c.close()


_v151_suite()
