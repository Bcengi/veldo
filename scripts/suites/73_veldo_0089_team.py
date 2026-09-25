"""VELDO-0089: versioned team configuration over a real signed store.

Run: python3 scripts/selftest.py --suite 73_veldo_0089_team

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy every
service loads; the production anchor below is the registered mutation driver's seam, so a mutation of
control_team.py reaches the service and the reader in another process. Real SQLite store with OpenSSH
command, journal and API signatures; principals are enrolled by the steward's signed VELDO-0025
commands; the project is activated by its owner's signed VELDO-0076 command; every team amendment is a
real VELDO-0064 request presented by the VELDO-0065 presenter over a loopback Bot API (no network, no
real token), answered through the authenticated API edge and settled by the real VELDO-0068
settlement; assignments read the VELDO-0049 review policy record built by dispatch.review_policy_record
from the repository's own .veldo/policy.yaml. A reader in another process opens the store read-only.
Where the team service is absent (the pre-change tree, for the red record) every command is answered
no_team_service and each row fails by its own assertions.
"""


def _v89_suite():
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
    PREFIX = 'VELDO-0089 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    # The role fields the specification names (AC1), compared with the service's own schema.
    SPEC_FIELDS = ('workers', 'responsibilities', 'expertise', 'proposal_permissions', 'engines', 'budget', 'independence')

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
            with region('install/assets'):
                scaffold = load('v89_scaffold', SCAFFOLD)
                rel = '.veldo/control_team.py'
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
            agents = ('w-elab', 'w-build', 'w-build2', 'w-rev1', 'w-rev2', 'w-rev3', 'outsider')
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
                enroll(who, 'service', [], ['proj-a'])
            for who in ('w-elab', 'w-build', 'w-build2', 'w-rev1', 'w-rev2'):
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

            def role(workers, resp, perms=('feature',), engines=('claude_code',), budget=None, distinct=()):
                return dict(workers=list(workers), responsibilities=[resp, 'report'], expertise=['python', 'payments'],
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

            authority_before = authority_rows()

            # AC1: the schema, completeness against the project's requirements, and owner requests.
            with region('team/schema-closed', 'team/incomplete-roster', 'team/conflicting-staffing',
                        'team/project-requirements', 'team/complete-proposal'):
                tooled = team(implementation=dict(role(['w-build'], 'implement'), tools=['Bash'], mcp_servers=['jira']))
                with_tools = propose(tooled)
                unknown_role = propose({'roles': dict(team()['roles'], release_manager=role(['w-elab'], 'release'))})
                check('team/schema-closed', [
                    ('the specification\'s role fields are exactly the schema\'s', CT is not None and tuple(CT.ROLE_FIELDS) == SPEC_FIELDS),
                    ('no tool or capability field in the schema', CT is not None and not any(
                        w in f for f in CT.ROLE_FIELDS for w in ('tool', 'mcp', 'capabilit', 'server'))),
                    ('a role with tools and MCP servers is refused by name', with_tools.get('ok') is False
                     and 'invalid_input:field:implementation/tools' in (with_tools.get('problems') or [])
                     and 'invalid_input:field:implementation/mcp_servers' in (with_tools.get('problems') or [])),
                    ('an undeclared role is refused by name', unknown_role.get('ok') is False
                     and 'invalid_input:role:release_manager' in (unknown_role.get('problems') or [])),
                    ('and nothing is recorded', not team_record())])

                no_review = propose(team(independent_review=None))
                check('team/incomplete-roster', [
                    ('a team without independent review is refused and asks the owner',
                     staffing_refused(no_review, 'missing_staffing:independent_review', authority_before)),
                    ('the refusal is incomplete_roster naming the missing role',
                     no_review.get('reason') == 'incomplete_roster:missing_staffing:independent_review'),
                    ('an empty review role is refused the same way', staffing_refused(
                        propose(team(independent_review=role([], 'review', distinct=('implementation',)))),
                        'missing_staffing:independent_review', authority_before))])

                two_pm = propose(team(project_manager=role(['pm', 'w-elab'], 'coordinate')))
                overlap = propose(team(independent_review=role(['w-rev1', 'w-build'], 'review', distinct=('implementation',))))
                grouped = propose(team(independent_review=role(['w-rev1', 'w-rev3'], 'review', distinct=('implementation',))))
                ghost = propose(team(elaboration=role(['w-ghost'], 'elaborate')))
                foreign = propose(team(elaboration=role(['outsider'], 'elaborate')))
                check('team/conflicting-staffing', [
                    ('two project managers', staffing_refused(two_pm, 'conflicting_staffing:project_manager', authority_before)),
                    ('a builder who also reviews', staffing_refused(overlap, 'conflicting_staffing:independent_review/w-build',
                                                                    authority_before)),
                    ('a reviewer in a builder\'s independence group', staffing_refused(
                        grouped, 'conflicting_staffing:independent_review/w-rev3', authority_before)),
                    ('a worker nobody enrolled is never invented', staffing_refused(
                        ghost, 'unknown_worker:elaboration/w-ghost', authority_before) and entity('w-ghost') is None),
                    ('a member outside the project is not staffed', staffing_refused(
                        foreign, 'unknown_worker:elaboration/outsider', authority_before))])

                over = propose(team(implementation=role(['w-build'], 'implement',
                                                        budget={'capacity': 1, 'invocations': 2, 'wall_seconds': 900})))
                engine = propose(team(elaboration=role(['w-elab'], 'elaborate', engines=('claude_code', 'gpt'))))
                duty = propose(team(implementation=dict(role(['w-build'], 'implement'), responsibilities=['report'])))
                separation = propose(team(independent_review=role(['w-rev1', 'w-rev2'], 'review')))
                check('team/project-requirements', [
                    ('a role budget above the project\'s coordination budget', staffing_refused(
                        over, 'over_budget:implementation/wall_seconds', authority_before)),
                    ('an engine that is no registered adapter', staffing_refused(
                        engine, 'engine_ineligible:elaboration/gpt', authority_before)),
                    ('a role without its responsibility', staffing_refused(
                        duty, 'missing_responsibility:implementation', authority_before)),
                    ('independent review not declared separate from implementation', staffing_refused(
                        separation, 'missing_independence:independent_review/implementation', authority_before)),
                    ('the engines are the registered subscription adapters', CT is not None
                     and set(CT.ENGINES) == {'claude_code', 'codex'})])

                pending = [(eid, d) for eid, d in requests_named('team_staffing') if d.get('state') == 'OFFERED']
                good = propose(team())
                record = team_record()
                proposal = record.get('proposal') or {}
                seen = other_process()
                check('team/complete-proposal', [
                    ('a complete team is recorded as the pending proposal', good.get('ok') is True
                     and proposal.get('revision') == 1 and proposal.get('base_revision') == 0),
                    ('bound to exactly its content', CT is not None and proposal.get('team') == team()
                     and proposal.get('digest') == CT.revision_digest('proj-a', 1, 0, team())),
                    ('and nothing is accepted yet', record.get('revision') == 0 and record.get('revisions') == []),
                    ('every earlier staffing problem is an open owner request', len(pending) >= 10),
                    ('another process reads the same proposal', ((seen.get('team') or {}).get('proposal') or {}).get('digest')
                     == proposal.get('digest') and proposal.get('digest') is not None)])

            # AC2: owner amendments through the settlement path; the roster grants nothing.
            with region('team/owner-amendment', 'team/stale-amendment', 'team/altered-amendment',
                        'team/self-promotion', 'team/roster-not-authority'):
                rid1, settled1 = settle('TEAM-1')
                applied1 = amend(rid1)
                first = team_record()
                seen1 = other_process()
                # A second revision, amending the first.
                second_team = team(elaboration=role(['w-elab', 'w-build2'], 'elaborate'))
                proposed2 = propose(second_team)
                rid2, settled2 = settle('TEAM-2')
                applied2 = amend(rid2)
                second = team_record()
                check('team/owner-amendment', [
                    ('the owner\'s answer settled', settled1.get('outcome') == 'settled' and settled2.get('outcome') == 'settled'),
                    ('and amended the team to revision 1', applied1.get('ok') is True and first.get('revision') == 1
                     and first.get('team') == team() and first.get('proposal') is None),
                    ('the revision names the settlement and the owner', (first.get('revisions') or [{}])[0].get('settlement_id')
                     == ST.settlement_id(rid1, 1) and (first.get('revisions') or [{}])[0].get('principals') == ['olga']),
                    ('a second revision amends the first', proposed2.get('ok') is True and applied2.get('ok') is True
                     and second.get('revision') == 2 and second.get('team') == second_team
                     and [r.get('revision') for r in second.get('revisions') or []] == [1, 2]),
                    ('the stored first revision is unchanged', (second.get('revisions') or [{}])[0] == (first.get('revisions') or [None])[0]),
                    ('another process reads the accepted revision', (seen1.get('team') or {}).get('revision') == 1
                     and (seen1.get('team') or {}).get('digest') == first.get('digest'))])

                # Stale: a command bound to an older team version; an answer to a superseded proposal.
                propose(team(elaboration=role(['w-elab'], 'elaborate', ('feature', 'objective'))))
                rid3, settled3 = settle('TEAM-3')
                stale_version = amend(rid3, team_version=version() - 1)
                superseding = propose(team(elaboration=role(['w-elab'], 'elaborate', ('objective',))))
                superseded = amend(rid3)
                after_stale = team_record()
                check('team/stale-amendment', [
                    ('the answer settled', settled3.get('outcome') == 'settled'),
                    ('a command bound to an older team version is refused', refused(stale_version, 'stale_subject:version')),
                    ('an answer to a superseded proposal is refused', superseding.get('ok') is True
                     and refused(superseded, 'stale_subject:revision')),
                    ('and the team stays at revision 2', after_stale.get('revision') == 2
                     and len(after_stale.get('revisions') or []) == 2)])

                # Altered: the command changed after signing; content changed after the owner's answer;
                # a request that showed the owner another brief.
                rid4, settled4 = settle('TEAM-4')
                body = dict(ids, operation='amend', project='proj-a', principal='pm', command_id=next_id('tc'),
                            nonce=next_id('tn'), team_version=version(),
                            revision=(team_record().get('proposal') or {}).get('revision'),
                            digest=(team_record().get('proposal') or {}).get('digest'), request=rid4)
                packet = signed('pm', body)
                packet['command'] = dict(body, request=rid3)
                forged = service.apply(packet) if service is not None else {'ok': False, 'reason': 'no_team_service'}
                quiet = copy.deepcopy(team_record().get('proposal', {}).get('team') or team())
                quiet['roles']['independent_review']['expertise'] = ['nothing']
                propose(quiet)
                changed = amend(rid4)
                target5, _brief5 = target_and_brief()
                rid5, settled5 = settle('TEAM-5', target=target5, brief='Accept a small change to the team of proj-a.')
                other_brief = amend(rid5)
                after_altered = team_record()
                check('team/altered-amendment', [
                    ('a command altered after signing is refused', refused(forged, 'not_authorized')),
                    ('content changed after the owner\'s answer is refused', settled4.get('outcome') == 'settled'
                     and refused(changed, 'stale_subject:revision')),
                    ('an answer to another brief is refused', settled5.get('outcome') == 'settled'
                     and refused(other_brief, 'stale_subject:brief')),
                    ('and the team stays at revision 2', after_altered.get('revision') == 2)])

                # Self-promotion: the manager proposes himself as a reviewer and tries every way round the owner.
                promoted = team(independent_review=role(['w-rev1', 'w-rev2', 'pm'], 'review', distinct=('implementation',)))
                proposed_p = propose(promoted)
                unsettled = amend(I.assignment_id(REPO, 'TEAM-NONE'))
                rid6, receipt6 = present('TEAM-6', *target_and_brief())
                own = answer(receipt6, 'accept', 'pm')
                own_applied = amend(rid6)
                rid7, settled7 = settle('TEAM-7', owner='zed')
                by_other = amend(rid7)
                outside = send('outsider', 'propose', team_version=version(), team=promoted)
                after_promotion = team_record()
                check('team/self-promotion', [
                    ('the promotion is only a proposal', proposed_p.get('ok') is True),
                    ('it does not apply without a settled answer', refused(unsettled, 'missing_evidence:settlement')),
                    ('the manager\'s own answer settles nothing', own.get('outcome') != 'settled'
                     and refused(own_applied, 'missing_evidence:settlement')),
                    ('another project owner\'s answer is not the owner\'s', settled7.get('outcome') == 'settled'
                     and refused(by_other, 'not_owner')),
                    ('a member outside the project proposes nothing', refused(outside, 'not_authorized:scope')),
                    ('the manager is still no reviewer', after_promotion.get('revision') == 2
                     and 'pm' not in (((after_promotion.get('team') or {}).get('roles') or {}).get('independent_review') or {}).get('workers', ['pm']))])

                authority_after = authority_rows()
                pm_entry = (entity('pm') or {}).get('data') or {}
                _need, admit_problems = settlement.eligibility('admission', {'required_roles': [], 'quorum': None}, 'pm',
                                                               requested_by='team-service', scopes=['proj-a'])
                granting = propose(team(project_manager=role(['pm'], 'coordinate', ('objective', 'admission_authority'))))
                touchpoint = propose(team(project_manager=role(['pm'], 'coordinate', ('admission',))))
                check('team/roster-not-authority', [
                    ('amendments were accepted', second.get('revision') == 2),
                    ('no membership, delegation, key or authority version changed', authority_after == authority_before),
                    ('the configured manager holds no role', pm_entry.get('roles') == []),
                    ('and cannot settle an admission', bool(admit_problems)),
                    ('a proposal permission naming an authority is refused', refused(
                        granting, 'roster_not_authority:project_manager/admission_authority')),
                    ('a proposal permission naming a settlement touchpoint is refused', refused(
                        touchpoint, 'roster_not_authority:project_manager/admission'))])

            # AC3: assignments bind the current team revision and the engineering-review policy.
            with region('team/policy-required', 'team/valid-assignment', 'team/review-count', 'team/independence',
                        'team/exact-subject', 'team/stale-team'):
                for uid, risk in (('unit-c', 'critical'), ('unit-s', 'standard'), ('unit-x', 'experimental')):
                    fixture(uid, 'execution_unit', dict(state='READY', repository_uuid=REPO, project='proj-a', risk=risk,
                                                        revision=3, scope_digest='sha256:scope-' + uid, requirements=[]))

                def subject(uid, revision=3):
                    return {'unit': uid, 'revision': revision, 'scope_digest': 'sha256:scope-' + uid}

                def assign(uid, builder, reviewers, who='pm', team_revision=None, subjects=None, builder_subject=None):
                    subjects = subjects or {}
                    return send(who, 'assign', team_version=version(), unit=uid,
                                team_revision=team_record().get('revision') if team_revision is None else team_revision,
                                builder=builder, subject=builder_subject or subject(uid),
                                reviewers=[{'reviewer': r, 'subject': subjects.get(r) or subject(uid)} for r in reviewers])

                no_policy_none = assign('unit-s', 'w-build', [])
                no_policy_one = assign('unit-s', 'w-build', ['w-rev1'])
                policy_record = DSP.review_policy_record(ROOT / '.veldo' / 'policy.yaml')
                fixture(DSP.review_policy_id(REPO), DSP.REVIEW_POLICY_KIND, policy_record)
                no_tier = assign('unit-x', 'w-build', ['w-rev1', 'w-rev2'])
                check('team/policy-required', [
                    ('the service reads VELDO-0049\'s own policy record', CT is not None
                     and CT.review_policy_id(REPO) == DSP.review_policy_id(REPO)
                     and CT.REVIEW_POLICY_KIND == DSP.REVIEW_POLICY_KIND),
                    ('no policy and no reviewer is refused', refused(no_policy_none, 'missing_authority:review_policy')),
                    ('no policy and one reviewer is refused', refused(no_policy_one, 'missing_authority:review_policy')),
                    ('a risk the policy has no count for is refused', refused(no_tier, 'missing_authority:review_policy')),
                    ('and no assignment exists', not (other_process().get('assignments') or []) and CT is not None)])

                valid_c = assign('unit-c', 'w-build', ['w-rev1', 'w-rev2'])
                valid_s = assign('unit-s', 'w-build2', ['w-rev2'])
                record_c = valid_c.get('assignment') or {}
                seen3 = other_process()
                current = team_record()
                check('team/valid-assignment', [
                    ('the policy counts are the repository\'s', policy_record['tiers'].get('critical') == 2
                     and policy_record['tiers'].get('standard') == 1),
                    ('an independent critical assignment succeeds', valid_c.get('ok') is True
                     and record_c.get('builder') == 'w-build' and record_c.get('reviewers') == ['w-rev1', 'w-rev2']),
                    ('bound to the current team revision', record_c.get('team') == {
                        'revision': current.get('revision'), 'digest': current.get('digest'), 'version': current.get('version')}),
                    ('bound to the policy and its count', (record_c.get('policy') or {}).get('required_reviews') == 2
                     and (record_c.get('policy') or {}).get('version') == (entity(DSP.review_policy_id(REPO)) or {}).get('version')),
                    ('bound to the exact subject', record_c.get('subject') == subject('unit-c')),
                    ('a standard unit needs one review', valid_s.get('ok') is True),
                    ('another process reads both', sorted(a.get('unit') for a in seen3.get('assignments') or [])
                     == ['unit-c', 'unit-s'])])

                one_review = assign('unit-c', 'w-build', ['w-rev1'])
                check('team/review-count', [
                    ('a critical unit with one review is refused', refused(one_review, 'insufficient_reviews:1/2')),
                    ('a standard unit with none is refused', refused(assign('unit-s', 'w-build', []), 'insufficient_reviews:0/1'))])

                self_review = assign('unit-s', 'w-build', ['w-build'])
                twice = assign('unit-s', 'w-build', ['w-rev1', 'w-rev1'])
                check('team/independence', [
                    ('the builder reviewing his own unit is refused', refused(self_review, 'reviewer_not_independent:w-build')),
                    ('one reviewer in two positions is refused', refused(twice, 'reviewer_not_independent:w-rev1')),
                    ('a reviewer who is no independent reviewer is refused', refused(
                        assign('unit-s', 'w-build', ['w-elab']), 'not_staffed:independent_review/w-elab'))])

                other_unit = assign('unit-c', 'w-build', ['w-rev1', 'w-rev2'], subjects={'w-rev2': subject('unit-s')})
                old_revision = assign('unit-s', 'w-build', ['w-rev1'], subjects={'w-rev1': subject('unit-s', 2)})
                builder_elsewhere = assign('unit-s', 'w-build', ['w-rev1'], builder_subject=subject('unit-c'))
                check('team/exact-subject', [
                    ('a reviewer bound to another unit is refused', refused(other_unit, 'wrong_subject:w-rev2')),
                    ('a reviewer bound to an older revision is refused', refused(old_revision, 'wrong_subject:w-rev1')),
                    ('a builder bound to another unit is refused', refused(builder_elsewhere, 'wrong_subject:builder'))])

                stale_team = assign('unit-s', 'w-build', ['w-rev1'], team_revision=1)
                not_manager = assign('unit-s', 'w-build', ['w-rev1'], who='w-elab')
                by_owner = assign('unit-s', 'w-build', ['w-rev1'], who='olga')
                check('team/stale-team', [
                    ('an assignment under an older team revision is refused', refused(stale_team, 'stale_subject:team_revision')),
                    ('a worker who is not the manager assigns nothing', refused(not_manager, 'not_authorized:not_manager')),
                    ('the project\'s owner may assign', by_owner.get('ok') is True)])

            with region('team/observability'):
                observations = service.observations if service is not None else []
                metrics = service.metrics() if service is not None else {}
                text = json.dumps(observations)
                check('team/observability', [
                    ('every command is observed with its outcome', len(observations) == metrics.get('accepted', 0)
                     + metrics.get('refused', 0) and len(observations) > 20),
                    ('refusals are named and classified', all(o['refusal'] and o['taxonomy'] != 'unknown_outcome'
                                                              for o in observations if o['outcome'] == 'refused')),
                    ('accepted commands carry the versions they read', all(o['accepted_versions'] for o in observations
                                                                           if o['outcome'] == 'accepted')),
                    ('pending work is counted', metrics.get('pending_proposals') == 1
                     and metrics.get('pending_staffing_requests', 0) >= 10 and metrics.get('assignments') == 3),
                    ('no team content or signature is observed', 'payments' not in text and 'SSH SIGNATURE' not in text)])
        finally:
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
            for c in connections:
                with contextlib.suppress(Exception):
                    c.close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])


_v89_started = __import__('time').monotonic()
_v89_suite()
print('VELDO-0089 suite seconds: %.3f' % (__import__('time').monotonic() - _v89_started))
