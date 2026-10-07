"""Signed project/team fixture for VELDO-0152. Contains no suite or test driver.
Adapted from the existing team writer journey; all memberships, configuration,
project activation and team acceptance go through their production commands.
"""
import contextlib
import copy
import http.server
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sys
import tempfile
import threading
import time

@contextlib.contextmanager
def fixture(ROOT, PRODUCTION, cycle_budget=12, production_setup=False, factory_project=True):
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def message(st, sender, chat, text, reply_to=None):
        with st['lock']:
            st['next'] += 1
            st['tick'] += 1
            # The platform date is the clock when the message is sent, as Telegram stamps it. Intake
            # authorizes a sender as a member at that date (VELDO-0126), and this fixture enrolls its
            # members at time.time(), so a fixed date became "sent before enrollment" once the wall
            # clock passed it (1791300000, 2026-10-06 15:20 UTC). Rounded up so a message sent in the
            # enrollment's second is not dated before it; strictly increasing, as the fixed ticks were.
            st['date'] = max(math.ceil(time.time()), st.get('date', 0) + 1)
            m = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': st['date'],
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
                return self._answer(200, {'ok': True, 'result': [u for u in st.get('updates', []) if u['update_id'] >= body.get('offset', 0)]})
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

    # /dev/shm only when this process can really write there: os.access answers for permission
    # bits, not for the gate's confinement (VELDO-0208), which grants nothing beneath /dev.
    fast = None
    try:
        os.rmdir(tempfile.mkdtemp(prefix='fast-probe-', dir='/dev/shm'))
        fast = '/dev/shm'
    except OSError:
        pass
    connections, servers = [], []
    with tempfile.TemporaryDirectory(prefix='v89-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copytree(ROOT / '.veldo' / 'runtime', mods / 'runtime')
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

            setup_report = None
            if production_setup:
                helper = load('v88_setup_fixture', Path(__file__).with_name('setup_fixture.py'))
                setup_report = helper.setup(ROOT, base, mods, keyfile['steward'])
                ids = setup_report['authority_ids']
                DOMAIN, REPO = ids['domain_uuid'], ids['repository_uuid']
                keyfile['authority'] = Path(setup_report['state_root']) / 'keys' / 'journal'
                edge = load('v88_setup_edge', mods / 'control_channel_enrollment.py')
                keyfile['api-edge'] = Path(setup_report['state_root']) / 'keys' / edge.edge_key_id('api')
                public['api-edge'] = ' '.join(keyfile['api-edge'].with_suffix('.pub').read_text().split()[:2])
                public['authority'] = ' '.join(keyfile['authority'].with_suffix('.pub').read_text().split()[:2])
            # Signing uses the service edge; the production-setup branch never
            # enrolls the PM here. Setup owns that membership and possession proof.
            for who in ('pm', 'team-service'):
                keyfile[who], public[who] = keyfile['authority'], public['authority']

            def sign_as(who, data, namespace='veldo-command'):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=data,
                                      capture_output=True, check=True, timeout=20).stdout.decode()

            def journal_sign(data):
                return sign_as('authority', data, 'veldo-journal')

            serial = [0]

            def next_id(prefix):
                serial[0] += 1
                return '%s-%d' % (prefix, serial[0])

            if setup_report:
                db = Path(setup_report['store'])
            else:
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

            if not production_setup:
                admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                                      'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                                      'independence_group': 'steward', 'scope': '*'})
            enroll('olga', 'person', ['project_owner', 'admission_authority', 'priority_authority'], '*')
            enroll('zed', 'person', ['project_owner'], ['bcengi'])
            for who in services:
                if production_setup and who in ('pm', 'api-edge'):
                    continue
                enroll(who, 'service', ['reservation_service'], '*')
            for who in ('w-elab', 'w-build', 'w-build2', 'w-rev1', 'w-rev2', 'w-late'):
                enroll(who, 'agent_run', [], '*')
            enroll('w-rev3', 'agent_run', [], '*', group='w-build')
            enroll('outsider', 'agent_run', [], ['proj-b'])

            production_pm = CM.AC.membership_entry(CM.authority_state(S, conn)['membership'], 'pm')
            if production_setup and not production_pm:
                yield locals()
                return

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

            if not factory_project:
                yield locals()
                return

            projects.apply(signed('olga', dict(
                ids, operation='activate', project='factory', principal='olga', command_id=next_id('pc'), nonce=next_id('pn'),
                owner='olga', charter={'purpose': 'Sell passes to travelers.'}, execution_repository=REPO,
                authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
                coordination_budget={'capacity': 5, 'invocations': cycle_budget, 'wall_seconds': 500}, ticket_key_prefixes=['FAC'])))

            service = (CT.Teams(S, CM, conn, ids, 'authority', journal_sign, inbox=inbox, assignment=I,
                                requester='team-service', request_sign=lambda m: sign_as('team-service', m))
                       if CT is not None else None)

            def send(who, op, **fields):
                body = dict(ids, operation=op, project='factory', principal=who, command_id=next_id('tc'),
                            nonce=next_id('tn'), **fields)
                return service.apply(signed(who, body)) if service is not None else {'ok': False, 'reason': 'no_team_service'}

            def entity(eid):
                row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}

            def team_record():
                row = entity('team:factory')
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
            catalog_worker = base / 'catalog.py'
            catalog_worker.write_text('import json,sys,os\nfrom pathlib import Path\n'
                'q=json.load(sys.stdin)\n'
                'Path(sys.argv[1]).write_text(json.dumps(dict(request=q,pid=os.getpid())))\n'
                'print(json.dumps(dict(jsonrpc="2.0",id=q["id"],result={"content":[{"type":"text","text":"BCG-123: change one line"}]})))\n')
            catalog = CG.MC.Catalog(S, conn, domain=DOMAIN, repository=REPO, signer='authority', sign=journal_sign)
            catalog.save(dict(id='tickets', label='Fixture ticket catalog', transport='stdio', command=sys.executable,
                arguments=[str(catalog_worker), str(base / 'ticket-fetch.json')], url=None, environment={},
                headers={}, hosts=['linux'], read_only_tools=['jira.get']), principal='steward', base=0,
                command_id=next_id('catalog'))
            catalog_row = entity(CG.MC.revision_id(DOMAIN, 'tickets', 1))['data']
            (base / 'catalog.json').write_text(json.dumps(catalog_row))
            configurations.save(dict(role='team-fixture', engine='claude_code', native_tools=[],
                mcp=[dict(server='tickets', revision=1, tools=['jira.get'], load='when assigned')],
                skills=[], instructions=[], settings={}), principal='steward', base=0,
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
                    return {'kind': 'team', 'ref': 'team:factory', 'digest': 'sha256:none'}, 'Accept the team of factory.'
                return CT.amendment_target(record), CT.amendment_brief(record)

            def present(alias, target, brief, owner='olga'):
                """The requester's terms, the inbox request with its framing, and its presentation."""
                terms = settlement.terms(signed('pm', dict(ids, operation='terms', terms=alias, principal='pm',
                                                           command_id=next_id('terms'), nonce=next_id('tn'),
                                                           touchpoint='decision_disposition', target=target, proposal=None,
                                                           required_roles=[], quorum=None)))
                inbox.apply(signed('pm', dict(ids, operation='open', alias=alias, principal='pm', command_id=next_id('c'),
                                              nonce=next_id('n'), assignment=dict(
                                                  kind='decision', owner=owner, scope=['factory'],
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

            # Each behavioral row contains its successful real-writer control when needed.
            def accept(value):
                proposed = propose(value)
                if not proposed.get('ok'):
                    return proposed
                rid, settled = settle(next_id('TEAM'))
                result = amend(rid) if settled.get('outcome') == 'settled' else settled
                if not result.get('ok'):
                    print('  VELDO-0152 detail: acceptance result: %r' % result)
                return result

            accepted = accept(team())
            if not accepted.get('ok'):
                raise RuntimeError('fixture team: ' + str(accepted))
            yield locals()
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for connection in connections:
                connection.close()
