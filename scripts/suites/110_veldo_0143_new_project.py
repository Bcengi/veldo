"""VELDO-0143: a repository the owner asks for in chat is created or adopted and bound to a new project on his one
answer.

Run: python3 scripts/selftest.py --suite 110_veldo_0143_new_project

Only shared ROOT and expect are consumed. The signed project and team fixture of VELDO-0152
(proof/VELDO-0152/fixture.py: a real SQLite store, members enrolled by the steward's signed VELDO-0025 commands,
the VELDO-0064 inbox, the VELDO-0065 presenter over a loopback Bot API, the VELDO-0068 settlement, the factory
project activated by its owner and its team accepted) holds one temporary .veldo copy every module loads, with
the production copies named in PRODUCTION (the copies a registered mutation replaces). The owner's messages
come through the real intake (VELDO-0126/0152) by Telegram and by an API request the API edge signs; the
factory PM's route and its new-project document are the documents the suite supplies, as VELDO-0152 drives
them (the run that returns them through the factory loop, the Runner and a fake engine is its own row). The
repositories are real Git repositories; GitHub is a loopback REST stand-in that creates bare repositories, which
the hermetic identity wire (scripts/suites/support/identity_wire.py) maps the GitHub URLs to, so every push goes
through VELDO-0153's identity profile and nothing leaves this host. The adoption signer and the host's
enrollment signers are made by control_factory_setup's own adoption_signer and host_files. The authority
service's take-on and its new-project pass run in this process (control_service.Service over the same store),
so no socket is needed. No private key byte, signature or token is printed or retained.
"""


def _v143_suite():
    import contextlib
    import copy
    import hashlib
    import http.server
    import importlib.util
    import json
    import os
    from pathlib import Path
    import runpy
    import shutil
    import subprocess
    import sys
    import threading
    import time
    from types import SimpleNamespace

    # Literal anchors: the registered mutation driver substitutes one production copy here.
    PRODUCTION = {
        'control_project_proposal.py': ROOT / ".veldo" / "control_project_proposal.py",
        'control_repository_creation.py': ROOT / ".veldo" / "control_repository_creation.py",
        'control_effect_executor_creation.py': ROOT / ".veldo" / "control_effect_executor_creation.py",
        'control_effect_executor_adoption.py': ROOT / ".veldo" / "control_effect_executor_adoption.py",
        'control_repository.py': ROOT / ".veldo" / "control_repository.py",
        'control_project.py': ROOT / ".veldo" / "control_project.py",
        'control_objective.py': ROOT / ".veldo" / "control_objective.py",
        'control_intake_routes.py': ROOT / ".veldo" / "control_intake_routes.py",
        'control_grooming_request.py': ROOT / ".veldo" / "control_grooming_request.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_service_projects.py': ROOT / ".veldo" / "control_service_projects.py",
        'control_workflow_cycle_pm.py': ROOT / ".veldo" / "control_workflow_cycle_pm.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
    }
    PREFIX = 'VELDO-0143 '
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

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    if not PRODUCTION['control_project_proposal.py'].is_file():
        for label in ('factory/own-repository', 'intake/new-project-routed', 'proposal/fields', 'proposal/nothing-asked',
                      'proposal/one-answer', 'proposal/correction', 'proposal/refusals', 'provision/settlement-required',
                      'provision/created', 'provision/answered-and-corrected', 'provision/directory-not-empty',
                      'provision/adoption-path', 'provision/step-failures', 'provision/observed',
                      'activation/order', 'activation/applied', 'activation/failed-activates-nothing',
                      'activation/admitted-without-question', 'activation/new-line', 'service/provisions',
                      'pm/new-project-run'):
            expect(PREFIX + label, False)
        return

    helper = load('v143_fixture', Path(__suite_file__).resolve().parents[2] / 'proof/VELDO-0152/fixture.py')
    W = runpy.run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))

    def unix_sockets():
        """Whether this process may create a local (AF_UNIX) socket: the identity wire's recording SSH agent is
        one. Some confinements refuse it outright."""
        import socket
        try:
            socket.socket(socket.AF_UNIX).close()
            return True
        except OSError:
            return False
    UNIX = unix_sockets()

    @contextlib.contextmanager
    def fenced(wire):
        """The identity wire's hermetic fence (as VELDO-0161's suite raises it). Where local sockets are refused,
        the fence's recording SSH agent cannot be created; the fence is then raised without it and SSH_AUTH_SOCK
        names a path where nothing listens, so no agent is reachable at all (these fixtures push with a token,
        never over ssh). Every other wall is the wire's own."""
        if UNIX:
            with fenced(wire):
                yield wire
            return
        state = W['_audit_state']()
        saved = {k: os.environ.get(k) for k in ('PATH', 'SSH_AUTH_SOCK')}
        os.environ['PATH'] = str(wire.directory) + os.pathsep + (saved['PATH'] or os.defpath)
        os.environ['SSH_AUTH_SOCK'] = str(wire.directory / 'no-agent' / 'agent')
        state.stack.append(wire)
        clean = False
        try:
            yield wire
            clean = True
        finally:
            state.stack.remove(wire)
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            found = wire.violations()
            if found and clean:
                raise W['HermeticViolation']('VELDO HERMETIC FENCE: %d violation(s): %s' % (len(found), json.dumps(found)[:2000]))
    if not UNIX:
        print('  %sthe fence runs without its recording agent: AF_UNIX sockets are refused on this host' % PREFIX)
    servers = []
    with helper.fixture(ROOT, PRODUCTION, cycle_budget=100) as f:
        S, CM, AC, conn, base, mods = (f[k] for k in ('S', 'CM', 'AC', 'conn', 'base', 'mods'))
        DOMAIN, REPO, ids = f['DOMAIN'], f['REPO'], f['ids']
        sign_as, journal_sign, next_id = f['sign_as'], f['journal_sign'], f['next_id']
        inbox, presenter, settlement, I = f['inbox'], f['presenter'], f['settlement'], f['I']
        try:
            IN = load('v143_intake', mods / 'control_intake.py')
            EV = load('v143_attribution', mods / 'control_channel_attribution.py')
            PP = load('v143_proposal', mods / 'control_project_proposal.py')
            R = load('v143_repository', mods / 'control_repository.py')
            CR = load('v143_creation', mods / 'control_repository_creation.py')
            EC = load('v143_creation_effect', mods / 'control_effect_executor_creation.py')
            GI = load('v143_identity', mods / 'control_git_identity.py')
            GP = load('v143_git', mods / 'git_process.py')
            CE = load('v143_enrollment', mods / 'control_enrollment.py')
            EL = load('v143_eligibility', mods / 'control_eligibility.py')
            SC = load('v143_scaffold', mods / 'init_scaffold.py')
            FS = load('v143_setup', mods / 'control_factory_setup.py')
            SP = load('v143_service_projects', mods / 'control_service_projects.py')
            SV = load('v143_service', mods / 'control_service.py')
            PJ = load('v143_project', mods / 'control_project.py')
            OB = load('v143_objective', mods / 'control_objective.py')
            GR = load('v143_grooming_request', mods / 'control_grooming_request.py')
            TR = load('v143_team_routes', mods / 'control_team_routes.py')

            HOST, OWNER = 'host-143', 'olga'
            chat = 5890001

            def entity(eid):
                row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

            def journal():
                return [tuple(r) for r in conn.execute('SELECT seq, record_digest FROM journal ORDER BY seq')]

            def record(repository):
                return R.read(conn, repository)

            def git(path, *args, check=True):
                done = GP.run(['git', '-C', str(path), *args], capture_output=True, text=True, timeout=60)
                if check and done.returncode:
                    raise RuntimeError('git %s: %s' % (args[0], done.stderr.strip()[:300]))
                return done.stdout.strip()

            def tip(path, ref='refs/heads/main'):
                done = GP.run(['git', '-C', str(path), 'rev-parse', '--verify', '--quiet', ref], capture_output=True,
                              text=True)
                return done.stdout.strip() if done.returncode == 0 else None

            def bot_messages():
                """Every message the bot sent, in order: (chat, message id, reply to, text)."""
                user = f['api']['user']['id']
                return [(c, m, (v.get('reply_to_message') or {}).get('message_id'), v.get('text'))
                        for (c, m), v in sorted(f['api']['messages'].items(), key=lambda kv: kv[0][1])
                        if (v.get('from') or {}).get('id') == user]

            def new_project_requests():
                return [eid for eid, data in conn.execute("SELECT id, data FROM entities WHERE kind='settlement_terms'")
                        if (json.loads(data).get('target') or {}).get('kind') == PP.TARGET]

            # ---- the factory's identities, its default team and its adoption signer --------------------------------
            projects_root = {name: base / ('projects-' + name) for name in ('personal', 'bcengi', 'nokey')}
            for path in projects_root.values():
                path.mkdir()
            TOKENS = {'personal': '-'.join(('personal', 'token', os.urandom(12).hex())),
                      'bcengi': '-'.join(('bcengi', 'token', os.urandom(12).hex()))}
            LOGIN = {TOKENS['personal']: 'olga-p', TOKENS['bcengi']: 'olga-b'}

            def identity(name, owner, label, token_name):
                reference = 'keychain:%s/api' % token_name
                return dict(id=name, label=label, author_name='Olga ' + label, author_email='%s@example.invalid' % name,
                            remote_host='github.com', remote_owner=owner, api_token=reference,
                            push_credential=dict(kind='token', reference=reference),
                            projects_root=str(projects_root[name]), default_visibility='private')
            identities = [identity('personal', 'olga-p', 'Personal', 'personal'),
                          identity('bcengi', 'bcengi', 'Bcengi', 'bcengi'),
                          identity('nokey', 'olga-p', 'Nokey', 'nokey')]
            GI.configure_identities(conn, DOMAIN, identities, {})
            by_id = {r['id']: r for r in identities}
            routes = TR.TeamRoutes(f['service'], settlement, presenter)
            default = routes.save_default(f['team'](), OWNER, 0, next_id('default-team'), 'sha256:' + '1' * 64)
            keys = base / 'protected'
            keys.mkdir(mode=0o700)
            adoption_public = FS.adoption_signer(str(keys))
            adoption_key = keys / 'adoption-signer'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v143-settlement', '-f',
                            str(keys / 'settlement')], check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            settlement_public = ' '.join((keys / 'settlement.pub').read_text().split()[:2])
            state_root = base / 'state'
            (state_root / 'host').mkdir(parents=True, mode=0o700)
            trust_file = base / 'trust' / 'host_trust.json'
            trust_file.parent.mkdir(mode=0o700)
            plan = {'root': str(state_root), 'owner': OWNER, 'owner_public': f['public'][OWNER],
                    'host_trust': str(trust_file), 'host_identity': HOST}
            for path, text in FS.host_files(plan, settlement_public, adoption_public).items():
                Path(path).write_text(text)
                os.chmod(path, 0o600)
            trust = EL.load_host_trust(str(trust_file))

            # ---- GitHub: a loopback REST stand-in whose repositories are bare ones the identity wire maps ----------
            wire = W['Wire'](base / 'wire', secrets={'personal/api': TOKENS['personal'], 'bcengi/api': TOKENS['bcengi']})
            hub = {'repos': {}, 'calls': [], 'fault': None, 'reject_push': False, 'orgs': {'bcengi': {'olga-b'}},
                   'lock': threading.Lock()}

            class GitHubApi(http.server.BaseHTTPRequestHandler):
                def log_message(self, *args):
                    pass

                def _answer(self, code, value):
                    payload = json.dumps(value).encode()
                    self.send_response(code)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)

                def _who(self):
                    header = self.headers.get('Authorization') or ''
                    return LOGIN.get(header[len('Bearer '):]) if header.startswith('Bearer ') else None

                def do_GET(self):
                    who = self._who()
                    hub['calls'].append(('GET', self.path, who))
                    if who is None:
                        return self._answer(401, {'message': 'Bad credentials'})
                    if self.path == '/user':
                        return self._answer(200, {'login': who})
                    parts = self.path.strip('/').split('/')
                    if len(parts) == 3 and parts[0] == 'repos':
                        found = hub['repos'].get((parts[1], parts[2]))
                        return self._answer(200, found['answer']) if found else self._answer(404, {'message': 'Not Found'})
                    return self._answer(404, {'message': 'Not Found'})

                def do_POST(self):
                    who = self._who()
                    body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
                    hub['calls'].append(('POST', self.path, who, dict(body)))
                    if who is None:
                        return self._answer(401, {'message': 'Bad credentials'})
                    parts = self.path.strip('/').split('/')
                    if parts == ['user', 'repos']:
                        owner = who
                    elif len(parts) == 3 and parts[0] == 'orgs' and parts[2] == 'repos':
                        if who not in hub['orgs'].get(parts[1], set()):
                            return self._answer(403, {'message': 'Must be an organization member'})
                        owner = parts[1]
                    else:
                        return self._answer(404, {'message': 'Not Found'})
                    if hub['fault'] == 'refuse':
                        return self._answer(403, {'message': 'Resource not accessible by integration'})
                    if (owner, body['name']) in hub['repos']:
                        return self._answer(422, {'message': 'name already exists on this account'})
                    with hub['lock']:
                        bare = base / 'gh' / owner / (body['name'] + '.git')
                        bare.parent.mkdir(parents=True, exist_ok=True)
                        GP.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
                        if hub['reject_push']:
                            # The remote already holds a branch, so the push leased on its absence is refused.
                            seed = base / 'gh-seed' / owner / body['name']
                            seed.mkdir(parents=True)
                            GP.run(['git', 'init', '-q', '-b', 'main', str(seed)], check=True, capture_output=True)
                            GP.run(['git', '-C', str(seed), '-c', 'commit.gpgsign=false', 'commit', '-q', '--allow-empty',
                                    '-m', 'seeded'], check=True, capture_output=True,
                                   identity=('Fixture', 'fixture@example.invalid'))
                            GP.run(['git', '-C', str(seed), 'push', '-q', str(bare), 'main:main'], check=True,
                                   capture_output=True)
                        wire.remote(body['name'], bare, owner=owner)
                        shown = 'someone-else' if hub['fault'] == 'wrong_owner' else owner
                        answer = {'id': len(hub['repos']) + 1, 'name': body['name'], 'private': body['private'],
                                  'owner': {'login': shown}, 'clone_url': W['url'](body['name'], owner)}
                        hub['repos'][(owner, body['name'])] = {'bare': bare, 'answer': answer, 'body': dict(body)}
                    return self._answer(201, answer)

            github = http.server.ThreadingHTTPServer(('127.0.0.1', 0), GitHubApi)
            servers.append(github)
            threading.Thread(target=github.serve_forever, daemon=True).start()
            github_api = 'http://127.0.0.1:%d' % github.server_address[1]

            observations = base / 'provisioner.jsonl'
            effect_config = {'schema': EC.SCHEMA, 'store': str(f['db']), 'domain_uuid': DOMAIN,
                             'store_uuid': ids['store_uuid'], 'authority_generation': 1, 'host_trust': str(trust_file),
                             'journal': {'principal': 'authority', 'key': str(f['keyfile']['authority'])},
                             'adoption_signer': {'key': str(adoption_key)}, 'templates': str(ROOT / 'engine'),
                             'observations': str(observations), 'github_api': github_api}

            # ---- intake: the owner's messages, by Telegram and by an API request --------------------------------
            acquirer = EV.Acquirer(S, CM, f['P'], f['V'], presenter, EV.TelegramAcquisitionEdge(f['P'], f['url'], 'bot89'),
                                   conn, 'authority', journal_sign, 'api-edge', lambda b: sign_as('api-edge', b))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=['factory'], api_edge='api-edge',
                               journal_signer='authority', sign=journal_sign, asker=presenter.edge)

            def send(channel, text, who=OWNER):
                if channel == 'api_request':
                    body = dict(schema=IN.API_SCHEMA, domain=DOMAIN, request_id=next_id('message'), edge='api-edge',
                                principal=who, text=text, project=None, clarifies=None)
                    return intake.receive(channel, dict(request=body, signature=sign_as('api-edge', S.canonical_bytes(body))))
                sender = 5890001 if who == OWNER else 5890002
                msg = f['message'](f['api'], {'id': sender, 'is_bot': False, 'first_name': who},
                                   {'id': sender, 'type': 'private'}, text, None)
                f['api'].setdefault('updates', []).append(dict(update_id=msg['message_id'], message=msg))
                acquirer.acquire()
                return dict(intake.receive(channel, EV.evidence_id(f['api']['user']['id'], msg['message_id'])),
                            message_id=msg['message_id'])

            def routed(result):
                """The factory PM's route of an inbox proposal as a new project (VELDO-0152 AC3), applied by intake."""
                pid = result.get('proposal_id')
                done = intake.route(dict(schema=IN.RT.SCHEMA, proposal_id=pid, route='new_project',
                                         reason='The owner asks for a project that does not exist yet.'),
                                    dispatch=next_id('pm-route'), proposal_id=pid)
                return pid, done

            def document(pid, project, identity=None, visibility=None, objective='A first page for the project'):
                return dict(schema=PP.DOCUMENT, proposal_id=pid, project=project, identity=identity,
                            visibility=visibility, objective=objective,
                            reason='The owner asked for a new project; the PM read his words.')

            def tell(text, record_):
                return SP.tell_owner(conn, presenter.edge, record_, text)
            decisions = PP.NewProjects(S, CM, conn, ids, 'authority', journal_sign, inbox=inbox, settlement=settlement,
                                       presenter=presenter, assignment=I, requester='pm',
                                       request_sign=lambda b: sign_as('pm', b), templates=str(ROOT / 'engine'), tell=tell)

            def answer(rid, choice, rationale):
                receipt = presenter.current(rid) or {}
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('api'),
                            principal=OWNER, request_id=receipt.get('request_id'),
                            request_version=receipt.get('request_version'), presentation_id=receipt.get('presentation_id'),
                            presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice, rationale=rationale)
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def own_decision(name, identity_name='personal', channel='api_request', **doc):
                """A message naming the project and the identity, routed, proposed: settled by the message itself."""
                result = send(channel, 'start a new %s project called %s' % (identity_name, name))
                pid, _done = routed(result)
                proposed = decisions.propose(pid, document(pid, name, identity_name, **doc), dispatch=next_id('pm-np'))
                return proposed.get('decision'), pid, proposed

            def binding_of(path):
                """The VELDO-0029 binding a directory carries, None for one that carries none or is no repository."""
                try:
                    return CE.read_binding(str(path))
                except CE.EnrollmentRefused:
                    return None

            def provision(decision, **kwargs):
                return EC.provision(effect_config, decision, **kwargs)

            # =====================================================================================================
            # AC1: the factory project's own repository; one proposal; nothing asked when he named both
            # =====================================================================================================
            with region('factory/own-repository'):
                small = dict(plan, root=str(state_root), store=str(f['db']), owner_key=str(f['keyfile'][OWNER]))
                made = FS.factory_repository(small, ids, S, conn, identities, 'personal', time.time)
                committed = FS.record_team(made, f['team']())
                again = FS.record_team(made, f['team']())
                files = git(made['path'], 'ls-tree', '-r', '--name-only', 'HEAD').splitlines()
                binding = CE.read_binding(made['path']) or {}
                fresh = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda d, r: False)
                body = dict(ids, operation='activate', project='factory-check', principal=OWNER, command_id=next_id('fc'),
                            nonce=next_id('fcn'), owner=OWNER, charter={'purpose': 'The factory\'s own work.'},
                            execution_repository=made['repository_uuid'],
                            authority_policy={'team_amendment': ['project_owner']},
                            coordination_budget={'capacity': 4, 'invocations': 400, 'wall_seconds': 604800})
                activated = fresh.apply({'command': body, 'signature': sign_as(OWNER, S.canonical_bytes(body))})
                team_json = json.loads((Path(made['path']) / 'team.json').read_text())
                check('factory/own-repository', [
                    ('setup makes the factory project\'s repository under the state root',
                     made['path'] == os.path.realpath(str(state_root / 'factory')) and (state_root / 'factory' / '.git').is_dir()),
                    ('it holds only the team configuration, committed once under the workspace identity',
                     files == ['team.json'] and again == committed
                     and git(made['path'], 'log', '-1', '--format=%an <%ae>') == 'Olga Personal <personal@example.invalid>'),
                    ('its team configuration is the default team, with a PM role',
                     team_json == f['team']() and 'project_manager' in team_json['roles']),
                    ('it is enrolled by the owner and bound by the store under the workspace identity',
                     binding.get('enrolled_by') == OWNER and binding.get('repository_uuid') == made['repository_uuid']
                     and S.bound_repository(conn, DOMAIN, made['repository_uuid']) == made['path']
                     and GI.resolve(conn, DOMAIN, made['repository_uuid'])['id'] == 'personal'),
                    ('a project activated on it is bound to it alone (VELDO-0149)',
                     activated.get('ok') is True
                     and (activated.get('project') or {}).get('execution_repository') == made['repository_uuid']),
                    ('setup lays the provisioner configuration down with GitHub\'s own REST origin',
                     json.loads(FS.provisioner_text(dict(small, keys=str(keys)), ids)).get('github_api') == 'https://api.github.com'
                     and set(json.loads(FS.provisioner_text(dict(small, keys=str(keys)), ids))) == set(EC.FIELDS))])

            with region('intake/new-project-routed'):
                first = send('telegram_message', 'start a new personal project called tidepool')
                second = send('api_request', 'start a new project called driftwood for the harbor site')
                pid1, route1 = routed(first)
                pid2, route2 = routed(second)
                check('intake/new-project-routed', [
                    ('each message is a factory inbox proposal with no question',
                     first.get('outcome') == 'inbox' and second.get('outcome') == 'inbox'
                     and not (intake.proposal(pid1) or {}).get('question_id')),
                    ('the factory PM\'s new-project route keeps each in the factory project as NEW_PROJECT',
                     route1.get('ok') and route2.get('ok') and (intake.proposal(pid1) or {}).get('state') == 'NEW_PROJECT'
                     and (intake.proposal(pid2) or {}).get('state') == 'NEW_PROJECT'),
                    ('both wait for the factory PM\'s proposal',
                     {p['proposal_id'] for p in PP.pending(conn)} >= {pid1, pid2})])

            with region('proposal/nothing-asked'):
                before_messages, before_requests = bot_messages(), new_project_requests()
                tide = decisions.propose(pid1, document(pid1, 'tidepool', 'personal', objective='A tide chart page'),
                                         dispatch='pm-np-tidepool')
                tide_decision = tide.get('decision')
                tide_record = PP.read(conn, tide_decision) or {}
                tide_judged = PP.settled(S, CM, conn, tide_decision)
                check('proposal/nothing-asked', [
                    ('his message named the project and the identity: it is the answer',
                     tide.get('ok') and tide.get('outcome') == 'settled' and tide_record.get('state') == 'settled'
                     and tide_record.get('path') == 'own_message' and tide_judged['path'] == 'own_message'),
                    ('nothing is presented and no request is opened',
                     tide_record.get('request') is None and new_project_requests() == before_requests
                     and bot_messages() == before_messages),
                    ('the settled proposal names the identity, its directory and its remote',
                     tide_judged['proposal']['identity'] == 'personal'
                     and tide_judged['proposal']['directory'] == str(projects_root['personal'] / 'tidepool')
                     and tide_judged['proposal']['remote'] == {'name': 'tidepool', 'owner': 'olga-p', 'visibility': 'private',
                                                               'url': 'https://github.com/olga-p/tidepool.git'})])

            with region('proposal/fields'):
                before_messages = bot_messages()
                drift = decisions.propose(pid2, document(pid2, 'driftwood', None, objective='The harbor site\'s first page'),
                                          dispatch='pm-np-driftwood')
                drift_decision = drift.get('decision')
                drift_record = PP.read(conn, drift_decision) or {}
                shown = drift_record.get('presented') or {}
                request = entity(drift_record.get('request') or '') or {}
                presented_messages = bot_messages()[len(before_messages):]
                check('proposal/fields', [
                    ('a message that named no identity is presented once, to the factory owner',
                     drift.get('outcome') == 'presented' and drift_record.get('state') == 'presented'
                     and request.get('data', {}).get('owner') == OWNER and len(presented_messages) >= 1
                     and all(m[0] == chat for m in presented_messages)),
                    ('it names the project, the first objective, the default team\'s current revision, the default '
                     'pipeline and the coordination budget',
                     shown.get('project') == 'driftwood' and shown.get('objective') == 'The harbor site\'s first page'
                     and shown.get('team') == {'revision': default['revision'], 'digest': default['digest']}
                     and shown.get('pipeline') == PP.default_pipeline()
                     and shown.get('coordination_budget') == PP.COORDINATION_BUDGET),
                    ('the identity is asked in the same request: each identity offered with its directory and remote',
                     shown.get('identity') is None
                     and [e['identity'] for e in shown.get('offered') or []] == ['bcengi', 'nokey', 'personal']
                     and all(e['directory'] == str(projects_root[e['identity']] / 'driftwood')
                             and e['remote']['owner'] == by_id[e['identity']]['remote_owner']
                             and e['remote']['visibility'] == 'private' for e in shown.get('offered') or [])),
                    ('what he is shown is exactly the brief of that proposal, naming every value',
                     request.get('data', {}).get('brief') == PP.brief(shown)
                     and all(word in PP.brief(shown) for word in ('driftwood', 'bcengi', 'personal', 'https://github.com/',
                                                                   'default team revision', 'default_pipeline',
                                                                   'The harbor site\'s first page')))])

            with region('proposal/one-answer'):
                answered = answer(drift_record['request'], 'accept', 'yes, under bcengi')
                after_answer = bot_messages()
                applied = decisions.apply_settled()
                drift_after = PP.read(conn, drift_decision) or {}
                drift_judged = PP.settled(S, CM, conn, drift_decision)
                again = decisions.apply_settled()
                check('proposal/one-answer', [
                    ('his one answer settles it', answered.get('outcome') in ('accepted', 'settled')
                     and drift_after.get('state') == 'settled' and drift_after.get('path') == 'answer'),
                    ('the identity he named in it resolves the proposal to what was offered for it',
                     drift_judged['proposal']['identity'] == 'bcengi'
                     and drift_judged['proposal']['remote']['url'] == 'https://github.com/bcengi/driftwood.git'
                     and drift_judged['request'] == drift_record['request']),
                    ('no further question is sent', bot_messages() == after_answer and again == []
                     and any(e.get('outcome') == 'settled' for e in applied))])

            with region('proposal/correction'):
                third = send('api_request', 'start a new project called reefwatch')
                pid3, _ = routed(third)
                reef = decisions.propose(pid3, document(pid3, 'reefwatch', 'personal'), dispatch='pm-np-reef')
                reef_decision = reef.get('decision')
                rid3 = (PP.read(conn, reef_decision) or {}).get('request')
                answer(rid3, 'return_for_elaboration', 'call it reef-watch and make it public')
                after_return = bot_messages()
                decisions.apply_settled()
                correcting = PP.read(conn, reef_decision) or {}
                waiting = [p for p in PP.pending(conn) if p.get('decision') == reef_decision]
                corrected = decisions.correct(reef_decision, document(pid3, 'reef-watch', 'personal', 'public'),
                                              dispatch='pm-np-reef-correction')
                reef_judged = PP.settled(S, CM, conn, reef_decision)
                check('proposal/correction', [
                    ('a message naming the identity but not by the owner\'s whole words is presented',
                     reef.get('outcome') == 'presented' and 'identity_not_in_message' in (reef.get('asked') or [])),
                    ('his correction hands his words to the factory PM, nothing is asked',
                     correcting.get('state') == 'correcting'
                     and (correcting.get('correction') or {}).get('rationale') == 'call it reef-watch and make it public'
                     and len(waiting) == 1 and waiting[0]['correction']['presented'] == correcting.get('presented')),
                    ('the PM\'s corrected proposal settles it with no second presentation',
                     corrected.get('ok') and reef_judged['path'] == 'correction'
                     and reef_judged['proposal']['project'] == 'reef-watch'
                     and reef_judged['proposal']['remote']['visibility'] == 'public'
                     and reef_judged['proposal']['repository'] == correcting['presented']['repository']
                     and bot_messages() == after_return and len([r for r in new_project_requests()]) == 2)])

            with region('proposal/refusals'):
                fourth = send('api_request', 'start a new project called unanswered')
                pid4, _ = routed(fourth)
                bad = {
                    'not a document': decisions.propose(pid4, {'schema': 'other'}, dispatch='x'),
                    'the factory project': decisions.propose(pid4, document(pid4, 'factory', 'personal'), dispatch='x'),
                    'an unknown identity': decisions.propose(pid4, document(pid4, 'unanswered', 'nobody'), dispatch='x'),
                    'another proposal': decisions.propose(pid4, document(pid1, 'unanswered', 'personal'), dispatch='x'),
                    'a decided proposal': decisions.propose(pid1, document(pid1, 'tidepool', 'personal'), dispatch='x'),
                    'a message not routed as a new project': decisions.propose('intake_proposal:none',
                                                                               document('intake_proposal:none', 'x'),
                                                                               dispatch='x')}
                check('proposal/refusals', [
                    ('%s: refused by name' % case, outcome.get('ok') is False and ':' in str(outcome.get('reason')))
                    for case, outcome in bad.items()] + [
                    ('none writes a decision', PP.read(conn, PP.decision_id(pid4)) is None)])

            # =====================================================================================================
            # AC2: created only on a settled answer, step by step, stopping by name at the first failure
            # =====================================================================================================
            unanswered = decisions.propose(pid4, document(pid4, 'unanswered', None), dispatch='pm-np-unanswered')
            fifth = send('api_request', 'start a new project called rejected')
            pid5, _ = routed(fifth)
            rejected = decisions.propose(pid5, document(pid5, 'rejected', None), dispatch='pm-np-rejected')
            answer((PP.read(conn, rejected['decision']) or {}).get('request'), 'reject', 'no')
            decisions.apply_settled()
            sixth = send('api_request', 'start a new project called forged under someone')
            pid6, _ = routed(sixth)
            forged_proposal = PP.build(conn, DOMAIN, intake.proposal(pid6), document(pid6, 'forged', 'personal'),
                                       repository='forged-repository', owner=OWNER)
            decisions.write(PP.decision_id(pid6), 'settled', step='own_message', proposal_id=pid6, path='own_message',
                            document=document(pid6, 'forged', 'personal'), dispatch='forged', presented=None,
                            request=None, proposal=forged_proposal, correction=None, project='forged',
                            repository='forged-repository', reason=None)

            with region('provision/settlement-required'):
                before, calls = journal(), len(hub['calls'])
                cases = {'presented, unanswered': unanswered.get('decision'), 'rejected': rejected.get('decision'),
                         'no decision': 'new-project:intake_proposal:none',
                         'his message did not name the identity': PP.decision_id(pid6)}
                outcomes = {case: provision(decision) for case, decision in cases.items()}
                check('provision/settlement-required', [
                    ('%s: refused no_settled_decision by name' % case,
                     outcome.get('ok') is False and str(outcome.get('reason')).startswith('no_settled_decision:')
                     and outcome.get('step') == 'settlement')
                    for case, outcome in outcomes.items()] + [
                    ('nothing is written, no directory is made, GitHub is not called',
                     journal() == before and len(hub['calls']) == calls
                     and not (projects_root['personal'] / 'forged').exists()
                     and not any((projects_root[i] / 'unanswered').exists() for i in projects_root)),
                    ('each refusal is distinct [%s]' % sorted(o.get('reason') for o in outcomes.values()),
                     len({o.get('reason') for o in outcomes.values()}) == 4)])

            with region('provision/created'):
                pushes_before = len(wire.invocations())
                with fenced(wire):
                    tide_result = provision(tide_decision)
                tide_repo = tide_judged['proposal']['repository']
                tide_dir = projects_root['personal'] / 'tidepool'
                held = record(tide_repo) or {}
                bare = hub['repos'][('olga-p', 'tidepool')]['bare'] if ('olga-p', 'tidepool') in hub['repos'] else None
                steps = [h['step'] for h in held.get('history') or []]
                pushed = [i for i in wire.invocations()[pushes_before:]
                          if 'push' in i and 'credential.interactive=false' in i]
                check('provision/created', [
                    ('each step runs in order and is recorded',
                     steps == ['settled', 'directory', 'init', 'scaffold', 'author', 'commit', 'remote', 'push', 'enrolled']),
                    ('the repository is created under the identity\'s projects root with the scaffold and its author',
                     tide_dir.is_dir() and SC.missing_substrate(str(tide_dir)) == []
                     and git(tide_dir, 'config', 'user.name') == 'Olga Personal'
                     and git(tide_dir, 'log', '-1', '--format=%an <%ae>|%cn <%ce>', 'main')
                     == 'Olga Personal <personal@example.invalid>|Olga Personal <personal@example.invalid>'),
                    ('the remote is created under the identity\'s owner, private, through GitHub\'s REST interface',
                     ('POST', '/user/repos', 'olga-p', {'name': 'tidepool', 'private': True, 'auto_init': False,
                                                        'has_wiki': False}) in hub['calls']),
                    ('the initial commit is pushed through the identity profile',
                     bare is not None and tip(bare) == held.get('base_commit') == tip(tide_dir) and len(pushed) == 1
                     and 'https://github.com/olga-p/tidepool.git' in pushed[0]),
                    ('the record is created, names the identity, decision, remote and its signed binding',
                     tide_result.get('ok') is True and held.get('origin') == 'created' and held.get('identity') == 'personal'
                     and held.get('request') == tide_decision and (held.get('remote') or {}).get('owner') == 'olga-p'
                     and held.get('enrollment') == CE.binding_digest(CE.read_binding(str(tide_dir)) or {})
                     and (CE.read_binding(str(tide_dir)) or {}).get('enrolled_by') == R.SIGNER_PRINCIPAL),
                    ('the adoption signer signed it for this decision alone, journaled',
                     [s.get('request') for s in R.signatures(conn) if s.get('repository') == tide_repo] == [tide_decision]),
                    ('the store binds it, and it waits for the running service',
                     S.bound_repository(conn, DOMAIN, tide_repo) == os.path.realpath(str(tide_dir))
                     and held.get('state') == 'provisioning')])

            with region('provision/answered-and-corrected'):
                with fenced(wire):
                    drift_result = provision(drift_decision)
                    reef_result = provision(reef_decision)
                drift_repo, reef_repo = drift_judged['proposal']['repository'], reef_judged['proposal']['repository']
                check('provision/answered-and-corrected', [
                    ('his answered identity: the remote is created in that organization, under its owner',
                     drift_result.get('ok') and ('POST', '/orgs/bcengi/repos', 'olga-b',
                                                 {'name': 'driftwood', 'private': True, 'auto_init': False,
                                                  'has_wiki': False}) in hub['calls']
                     and (record(drift_repo) or {}).get('identity') == 'bcengi'
                     and (projects_root['bcengi'] / 'driftwood').is_dir()),
                    ('his corrected visibility: public',
                     reef_result.get('ok') and hub['repos'][('olga-p', 'reef-watch')]['body']['private'] is False
                     and (record(reef_repo) or {}).get('origin') == 'created')])

            with region('provision/directory-not-empty'):
                occupied = projects_root['personal'] / 'occupied'
                occupied.mkdir()
                (occupied / 'notes.txt').write_text('mine\n')
                decision_o, _, _ = own_decision('occupied')
                calls = len(hub['calls'])
                outcome = provision(decision_o)
                held = record(PP.read(conn, decision_o)['proposal']['repository']) or {}
                check('provision/directory-not-empty', [
                    ('a directory that exists and is not empty is refused by name',
                     outcome.get('reason') == 'directory_not_empty' and held.get('state') == 'failed'
                     and held.get('failed_step') == 'directory' and R.reason(held.get('reason')) == 'directory_not_empty'),
                    ('nothing in it is touched and no later step runs',
                     sorted(os.listdir(occupied)) == ['notes.txt'] and len(hub['calls']) == calls
                     and [h['step'] for h in held['history']] == ['settled', 'directory'])])

            with region('provision/adoption-path'):
                harbor = projects_root['personal'] / 'harbor'
                harbor_bare = base / 'gh' / 'olga-p' / 'harbor.git'
                harbor_bare.parent.mkdir(parents=True, exist_ok=True)
                GP.run(['git', 'init', '-q', '-b', 'main', str(harbor)], check=True, capture_output=True)
                GP.run(['git', 'init', '-q', '--bare', '-b', 'main', str(harbor_bare)], check=True, capture_output=True)
                (harbor / 'README').write_text('harbor\n')
                git(harbor, 'add', '-A')
                GP.run(['git', '-C', str(harbor), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'harbor'], check=True,
                       capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
                git(harbor, 'push', '-q', str(harbor_bare), 'main:main')
                harbor_url = wire.remote('harbor', harbor_bare, owner='olga-p')
                git(harbor, 'remote', 'add', 'origin', harbor_url)
                base_commit = tip(harbor)
                with fenced(wire):
                    decision_h, _, proposed_h = own_decision('harbor')
                    harbor_judged = PP.settled(S, CM, conn, decision_h)
                    laid = harbor_judged['proposal']['adoption']['scaffold_commit']
                    harbor_result = provision(decision_h)
                harbor_record = record(harbor_judged['proposal']['repository']) or {}
                check('provision/adoption-path', [
                    ('a directory that is already a Git repository is proposed for adoption, its scaffold commit laid',
                     harbor_judged['proposal']['mode'] == 'adopt' and isinstance(laid, str)
                     and harbor_judged['proposal']['adoption']['base_commit'] == base_commit),
                    ('on his settlement the provisioner takes the adoption path (VELDO-0161)',
                     harbor_result.get('path') == 'adoption' and harbor_record.get('origin') == 'adopted'
                     and harbor_record.get('request') == decision_h and harbor_record.get('scaffold_commit') == laid),
                    ('the named scaffold commit is pushed and the binding signed, no remote is created',
                     tip(harbor_bare) == laid and harbor_result.get('ok') is True
                     and ('olga-p', 'harbor') not in hub['repos']
                     and (CE.read_binding(str(harbor)) or {}).get('enrolled_by') == R.SIGNER_PRINCIPAL)])

            with region('provision/step-failures'):
                incomplete = base / 'incomplete-templates'
                incomplete.mkdir()
                failures = {}

                def failing(step, name, identity_name='personal', prepare=None, config=None, inject=None):
                    decision, _pid, _p = own_decision(name, identity_name)
                    if prepare is not None:
                        prepare()
                    saved = dict(EC.STEP_FUNCTIONS)
                    if inject:
                        def refused(run):
                            raise EC.CR.Refused('invalid_input:%s_fixture' % inject)
                        EC.STEP_FUNCTIONS[inject] = refused
                    calls_before, pushes_before = len(hub['calls']), len(wire.invocations())
                    try:
                        with fenced(wire):
                            outcome = EC.provision(dict(effect_config, **(config or {})), decision)
                    finally:
                        EC.STEP_FUNCTIONS.clear()
                        EC.STEP_FUNCTIONS.update(saved)
                        hub.update(fault=None, reject_push=False)
                    held = record(PP.read(conn, decision)['proposal']['repository']) or {}
                    failures[step] = dict(outcome=outcome, record=held, calls=len(hub['calls']) - calls_before,
                                          pushes=len(wire.invocations()) - pushes_before,
                                          directory=projects_root[identity_name] / name)
                    return failures[step]
                unwritable = projects_root['personal'] / 'readonly'
                failing('init', 'readonly', prepare=lambda: (unwritable.mkdir(), unwritable.chmod(0o500)))
                failing('scaffold', 'noscaffold', config={'templates': str(incomplete)})
                failing('author', 'noauthor', inject='author')
                failing('commit', 'nocommit', inject='commit')
                failing('remote:token', 'notoken', identity_name='nokey')
                hub['repos'][('olga-p', 'taken')] = {'bare': None, 'answer': {'name': 'taken'}, 'body': {}}
                failing('remote:exists', 'taken')
                failing('remote:owner', 'wrongowner', prepare=lambda: hub.update(fault='wrong_owner'))
                failing('remote:refused', 'refusedrepo', prepare=lambda: hub.update(fault='refuse'))
                failing('push', 'refusedpush', prepare=lambda: hub.update(reject_push=True))
                unwritable.chmod(0o700)
                order = ['settled', 'directory', 'init', 'scaffold', 'author', 'commit', 'remote', 'push']
                expected = {'init': 'invalid_input:init', 'scaffold': 'invalid_input:scaffold',
                            'author': 'invalid_input:author_fixture', 'commit': 'invalid_input:commit_fixture',
                            'remote:token': 'token_unavailable', 'remote:exists': 'remote_exists',
                            'remote:owner': 'remote_owner_mismatch', 'remote:refused': 'creation_refused',
                            'push': 'push_refused'}
                parts = []
                for case, done in failures.items():
                    step = case.split(':')[0]
                    held = done['record']
                    reason = str(held.get('reason'))
                    parts.append(('%s: the record is failed, naming the step and the reason' % case,
                                  held.get('state') == 'failed' and held.get('failed_step') == step
                                  and done['outcome'].get('step') == step
                                  and (R.reason(reason) == expected[case] or reason.startswith(expected[case]))))
                    parts.append(('%s: no later step ran' % case,
                                  [h['step'] for h in held.get('history') or []] == order[:order.index(step) + 1]
                                  and (done['pushes'] == 0 or step == 'push')
                                  and (done['calls'] == 0 or step in ('remote', 'push'))
                                  and held.get('enrollment') is None and binding_of(done['directory']) is None))
                    parts.append(('%s: never reported ready' % case, done['outcome'].get('ok') is False))
                forged_remote = dict(tide_judged['proposal'], remote=dict(tide_judged['proposal']['remote'],
                                                                         url='https://github.com/stranger/tidepool.git'))
                calls = len(hub['calls'])
                try:
                    CR.remote(forged_remote, by_id['personal'], origin=github_api)
                    owner_check = None
                except CR.Refused as error:
                    owner_check = error.code
                parts.append(('a remote under another owner is refused by VELDO-0153\'s check before any network write',
                              owner_check == 'binding_mismatch:remote_owner' and len(hub['calls']) == calls))
                check('provision/step-failures', parts)

            with region('provision/observed'):
                events = [json.loads(line) for line in observations.read_text().splitlines()]
                steps_seen = {e.get('step') for e in events if e.get('operation') == 'provision_step'}
                text = observations.read_text() + json.dumps(R.records(conn))
                metrics = R.metrics(conn, events)
                check('provision/observed', [
                    ('each step is observed with the repository, identity, decision, step and outcome',
                     steps_seen == {'directory', 'init', 'scaffold', 'author', 'commit', 'remote', 'push'}
                     and all(e.get('repository') and e.get('identity') and e.get('request') and e.get('outcome')
                             for e in events if e.get('operation') == 'provision_step')),
                    ('each refusal is observed with its step and its named reason',
                     all(any(e.get('outcome') == 'refused' and e.get('step') == case.split(':')[0]
                             for e in events) for case in failures)),
                    ('each adoption signature is observed with the decision it answered',
                     any(e.get('operation') == 'adoption_signature' and e.get('request') == tide_decision
                         and e.get('outcome') == 'signed' for e in events)),
                    ('no token is ever recorded', all(t not in text for t in TOKENS.values())),
                    ('metrics count repositories created, failed by reason and signatures',
                     metrics.get('failed', 0) >= len(failures) + 1 and metrics.get('signatures', 0) >= 4
                     and set(metrics.get('failed_by_reason') or {}) >= {'directory_not_empty', 'remote_exists',
                                                                       'token_unavailable', 'creation_refused',
                                                                       'push_refused'})])

            # =====================================================================================================
            # AC3: the same settlement activates the project once its repository is active
            # =====================================================================================================
            receiver_config = base / 'receivers' / 'receiver-installed.json'
            receiver_config.parent.mkdir()
            receiver_config.write_text(json.dumps({'store': str(f['db']), 'workspace': str(base / 'workspace'),
                                                   'repository': REPO, 'domain': DOMAIN, 'principal': 'pm',
                                                   'records': str(base / 'records'), 'adapters': {}}))
            receiver_config.chmod(0o600)
            service = SV.Service(dict(domain_uuid=DOMAIN, store_uuid=ids['store_uuid'], principal='authority',
                                      authority_generation=1, repositories={REPO: [str(base / 'workspace')]},
                                      journal_key=str(f['keyfile']['authority']), host_identity=HOST,
                                      enrollment_signers=trust.enrollment_signers, store_path=str(f['db']),
                                      observations=str(base / 'service.jsonl'),
                                      receiver={'configs': {REPO: str(receiver_config)}}), conn)
            service.channel = SimpleNamespace(ingress=SimpleNamespace(inbox=inbox, presenter=presenter,
                                                                      settlement=settlement, acquirer=acquirer))

            with region('activation/order'):
                activations = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda d, r: False)
                before = journal()
                while_provisioning = activations.activate_decided(tide_decision)
                while_failed = activations.activate_decided(failures['push']['record'].get('request'))
                check('activation/order', [
                    ('a project whose repository is still provisioning is not activated',
                     while_provisioning.get('reason') == 'not_ready:repository:provisioning'
                     and PJ.read(S, conn, 'tidepool') is None),
                    ('one whose repository failed is not activated',
                     while_failed.get('reason') == 'not_ready:repository:failed' and PJ.read(S, conn, 'refusedpush') is None),
                    ('nothing is written', journal() == before)])

            with region('activation/applied'):
                taken = service.take_on()
                before_messages = bot_messages()
                passed = service.new_project_pass()
                tide_project = PJ.read(S, conn, 'tidepool') or {}
                tide_team = (entity('team:tidepool') or {}).get('data') or {}
                tide_objective = OB.read(conn, OB.objective_id(pid1 + ':project')) or {}
                told = bot_messages()[len(before_messages):]
                tide_message = first.get('message_id')
                check('activation/applied', [
                    ('the running service takes the created repository on, in this process',
                     (record(tide_repo) or {}).get('state') == 'active'
                     and any(e.get('repository_uuid') == tide_repo and e.get('outcome') == 'accepted' for e in taken)),
                    ('the settlement is applied as the project\'s activation on that repository',
                     tide_project.get('state') == 'ACTIVE' and tide_project.get('execution_repository') == tide_repo
                     and (tide_project.get('provenance') or {}).get('source') == 'new_project'
                     and (tide_project.get('provenance') or {}).get('decision') == tide_decision
                     and tide_project.get('owner') == OWNER and tide_project.get('coordination_budget') == PP.COORDINATION_BUDGET),
                    ('its first team revision is the default team revision the proposal named',
                     tide_team.get('revision') == 1 and tide_team.get('team') == f['team']()
                     and (tide_team.get('revisions') or [{}])[0].get('default_team') == {'revision': default['revision'],
                                                                                         'digest': default['digest']}
                     and (tide_team.get('revisions') or [{}])[0].get('decision') == tide_decision),
                    ('its first objective is accepted by his first message, with no question',
                     tide_objective.get('state') == 'ACCEPTED'
                     and tide_objective.get('bound', {}).get('outcome') == 'A tide chart page'
                     and (tide_objective.get('acceptance') or {}).get('path') == 'new_project'
                     and (tide_objective.get('acceptance') or {}).get('via') == 'own_message'
                     and (tide_objective.get('acceptance') or {}).get('intake_command') == tide_judged['source']['intake_command']),
                    ('the answered project\'s objective is accepted by his answer',
                     (OB.read(conn, OB.objective_id(pid2 + ':project')) or {}).get('acceptance', {}).get('via') == 'answer'
                     and (OB.read(conn, OB.objective_id(pid2 + ':project')) or {}).get('acceptance', {}).get(
                         'settlement_id') == drift_judged['settlement_id']),
                    ('he is told "tidepool is ready; the first objective is next", in reply to his message',
                     (chat, None, tide_message, 'tidepool is ready; the first objective is next.') in
                     [(c, None, r, t) for c, _m, r, t in told]),
                    ('the decisions are activated and nothing else is sent to him',
                     all(t.endswith('is ready; the first objective is next.') or 'could not be set up' in t
                         for _c, _m, _r, t in told)
                     and (PP.read(conn, tide_decision) or {}).get('state') == 'activated'
                     and any(e.get('operation') == 'activate' and e.get('outcome') == 'activated' for e in passed))])

            with region('activation/failed-activates-nothing'):
                failed_records = [PP.read(conn, done['record'].get('request')) or {} for done in failures.values()]
                check('activation/failed-activates-nothing', [
                    ('every decision whose repository failed is failed with its reason, and he is told',
                     all(r.get('state') == 'failed' and r.get('reason') for r in failed_records)
                     and any('refusedpush could not be set up' in t for _c, _m, _r, t in bot_messages())),
                    ('none of them is activated', all(PJ.read(S, conn, case_name) is None for case_name in
                                                     ('readonly', 'noscaffold', 'noauthor', 'nocommit', 'notoken', 'taken',
                                                      'wrongowner', 'refusedrepo', 'refusedpush', 'occupied')))])

            with region('activation/admitted-without-question'):
                managers = OB.project_managers(S, conn, 'tidepool')
                fields = {'priority': dict(GR.DEFAULT_PRIORITY), 'questions': []}
                by_decision = GR.route(fields, [GR.ADMISSION, GR.PRIORITY], tide_objective, OWNER, managers, 'pm', [], [])
                answered_objective = dict(tide_objective, acceptance={'path': 'answer', 'request_id': 'r'})
                by_answer = GR.route(fields, [GR.ADMISSION, GR.PRIORITY], answered_objective, OWNER, managers, 'pm', [], [])
                check('activation/admitted-without-question', [
                    ('work under the decided first objective is admitted at the default priority with no question',
                     by_decision == (GR.OWN_MESSAGE, []) and managers == ['pm']),
                    ('one message admits once: the decision\'s message identifies it',
                     GR.message_of(tide_objective) != ()),
                    ('an objective accepted by an ordinary answer is still presented', by_answer[0] == 'present'
                     and 'objective_by_answer' in by_answer[1])])

            with region('activation/new-line'):
                CFG = load('v143_config', mods / 'control_agent_config.py')
                copied = CFG.read(conn, DOMAIN, tide_repo, 'team-fixture', 1)
                base_revision = entity(SP.INITIAL_REVISION + tide_repo) or {}
                role = {'identity': 'w-build', 'adapter': 'claude', 'configuration': {'role': 'team-fixture', 'revision': 1},
                        'seconds': 100, 'payload': {'task': 'build the unit'}}
                work = {'repositories': {REPO: {'builder': role, 'reviewers': [dict(role, identity='w-rev1',
                                                                                    payload={'task': 'review the unit'})]}}}
                loop = SV.FactoryLoop(service, work)
                line = loop.lines.get(tide_repo)
                added = loop.add_line(tide_repo, service.config['receiver']['configs'][tide_repo])
                author = GI.author(GI.resolve(conn, DOMAIN, tide_repo))
                check('activation/new-line', [
                    ('the new repository is served with a receiver configuration of its own',
                     tide_repo in service.repositories
                     and json.loads(Path(service.config['receiver']['configs'][tide_repo]).read_text())['workspace']
                     == os.path.realpath(str(tide_dir))),
                    ('its first accepted revision is the commit it was created at',
                     (base_revision.get('data') or {}).get('commit') == (record(tide_repo) or {}).get('base_commit')),
                    ('the team\'s capability configurations read the same in it',
                     {k: copied[k] for k in ('role', 'engine')} == {'role': 'team-fixture', 'engine': 'claude_code'}),
                    ('the factory loop has its line, whose Runner dispatches in it, with the first line\'s roles',
                     added == tide_repo and line is not None and line.workspace == os.path.realpath(str(tide_dir))
                     and line.gate.repository_uuid == tide_repo and line.roles == work['repositories'][REPO]
                     and loop.factory_line == REPO),
                    ('its units are authored by the identity alone', author == ('Olga Personal', 'personal@example.invalid'))])

            with region('service/provisions'):
                provisioner = base / 'provisioner.json'
                provisioner.write_text(json.dumps(effect_config))
                provisioner.chmod(0o600)
                decision_s, pid_s, _ = own_decision('lagoon')
                service.config['provisioner'] = str(provisioner)
                with fenced(wire):
                    started = service.new_project_pass()
                    process = (service.projects_pass.running.get(decision_s) or (None,))[0]
                    # The serve loop's own iteration: take on what was adopted while the provisioner runs.
                    deadline = time.monotonic() + 120
                    while process is not None and process.poll() is None and time.monotonic() < deadline:
                        service.take_on()
                        time.sleep(0.05)
                    service.take_on()
                    service.new_project_pass()
                lagoon = PJ.read(S, conn, 'lagoon') or {}
                if lagoon.get('state') != 'ACTIVE' or process is None or process.returncode != 0:
                    print('  %sdetail: service pass %s, provisioner exit %s' % (
                        PREFIX, json.dumps(started, default=str)[:1500], None if process is None else process.returncode))
                check('service/provisions', [
                    ('the running service starts the registered provisioner for a settled decision',
                     any(e.get('operation') == 'provision' and e.get('outcome') == 'started' and e.get('decision') == decision_s
                         for e in started) and process is not None and process.returncode == 0),
                    ('the repository is created, taken on and the project activated',
                     lagoon.get('state') == 'ACTIVE' and (PP.read(conn, decision_s) or {}).get('state') == 'activated')])

            with region('pm/new-project-run'):
                # The factory PM's run through the factory loop's Runner, on the launch receiver and a fake engine
                # printing the installed CLI's output shape (VELDO-0172's, as VELDO-0152 drives the route run). The
                # cycle's graph needs the installed runtime: where it is absent the row is red by name, the host's.
                PM = load('v143_pm', mods / 'control_workflow_cycle_pm.py')
                RS = load('v143_readset', mods / 'control_readset.py')
                fake_formats = load('v143_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
                source = base / 'pm-source'
                source.mkdir()
                (source / 'README').write_text('Factory source.\n')
                for args in (('init', '-q'), ('add', 'README'), ('commit', '-qm', 'Factory source')):
                    GP.run(['git', '-C', str(source), *args], check=True, capture_output=True,
                           identity=('Fixture', 'fixture@example.invalid'))
                commit = tip(source, 'HEAD')
                runpy.run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind_paths'](
                    mods, conn, DOMAIN, {REPO: str(source)})
                CE.enroll(str(source), DOMAIN, ids['store_uuid'], str(f['db']), HOST, 1,
                          lambda b: sign_as(OWNER, b, EL.ENROLLMENT_NAMESPACE), OWNER, time.time(), repository_uuid=REPO)
                RS.attach_revisions(S, conn, DOMAIN, {REPO: str(source)}).accept(
                    'revision-143', REPO, commit, 'pm', documents={'README': PM.SN.digest((source / 'README').read_bytes())},
                    signer='authority', sign=journal_sign, authority_generation=1)
                result_file, packet_file = base / 'pm-result.json', base / 'pm-packet.json'
                fake = base / 'pm-fake' / 'claude'
                fake.parent.mkdir()
                fake.write_text(fake_formats.embed('''import json,sys
from pathlib import Path
def emit(event):
    print(json.dumps(complete_event(event)), flush=True)
if '--input-format' in sys.argv:
    opening = json.loads(sys.stdin.readline())
    emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': opening['request_id'],
          'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    packet = json.loads(json.loads(sys.stdin.readline())['message']['content'])
else:
    packet = json.load(sys.stdin)
Path(sys.argv[2]).write_text(json.dumps(packet))
result = Path(sys.argv[1]).read_text()
emit({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': result}],
      'usage': {'input_tokens': 2, 'output_tokens': 3}}})
emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': result,
      'usage': {'input_tokens': 2, 'output_tokens': 4}})
'''))
                pm_signers = base / 'pm-enrollment-signers'
                pm_signers.write_text('')
                pm_trust = base / 'pm-host-trust.json'
                pm_trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity=HOST,
                                                    enrollment_signers=str(pm_signers))))
                pm_trust.chmod(0o600)
                pm_receiver = base / 'pm-receiver.json'
                pm_receiver.write_text(json.dumps(dict(
                    store=str(f['db']), journal_key=str(f['keyfile']['authority']), principal='pm', workspace=str(source),
                    host_trust=str(pm_trust), domain=DOMAIN, repository=REPO, records=str(base / 'pm-records'),
                    adapters={'claude': {'identity': 'reported', 'argv': [
                        sys.executable, '-B', str(mods / 'control_launch.py'), 'exec', sys.executable, '-B', str(fake),
                        str(result_file), str(packet_file)]}})))
                # The scheduling service's principal holds reservation_service, as VELDO-0152's suite runs it.
                pm_service = SV.Service(dict(domain_uuid=DOMAIN, store_uuid=ids['store_uuid'], principal='team-service',
                                             authority_generation=1, repositories={REPO: [str(source)]},
                                             journal_key=str(f['keyfile']['authority']), host_identity=HOST,
                                             enrollment_signers=trust.enrollment_signers, store_path=str(f['db']),
                                             observations=str(base / 'pm-service.jsonl')), conn)
                pm_service.channel = service.channel
                pm_loop = SV.FactoryLoop(pm_service, {'repositories': {}})
                line = SV.Line(pm_loop, REPO, {'builder': {'identity': 'unassigned'}, 'reviewers': []}, str(pm_receiver))
                line.runner.account = 'fixture-account'
                line.engines, line.hosts = {'claude': 'claude_code'}, {'claude': HOST}
                pm_loop.lines[REPO] = line
                pm_loop.configured = [REPO]
                line.pm_cycles = PM.from_line(line)
                for scope, subject in (('account', 'fixture-account'), ('project', 'factory')):
                    line.reservations.configure('policy/' + subject, scope, subject,
                                                dict(capacity=5, invocations=100, wall_seconds=5000), now=time.time())
                estuary = send('api_request', 'start a new project called estuary for the river trail')
                pid_e, _ = routed(estuary)
                result_file.write_text(json.dumps(document(pid_e, 'estuary', None, objective='The river trail map')))
                pm_loop.wake('accepted_message')
                pm_loop.run()
                cycle = max(line.pm_cycles.records('factory'), key=lambda r: r['watermark'])
                if cycle.get('dispatch') in line.runner.launches:
                    line.runner.wait(line.runner.launches[cycle['dispatch']], timeout=60)
                    pm_loop.wake('run_end')
                    pm_loop.run()
                cycle = next(r for r in line.pm_cycles.records('factory') if r['cycle'] == cycle['cycle'])
                packet = json.loads(packet_file.read_text()) if packet_file.exists() else {}
                payload = packet.get('payload') or packet
                estuary_record = PP.read(conn, PP.decision_id(pid_e)) or {}
                if cycle.get('state') != 'proposed':
                    print('  %sdetail: pm cycle %s %s' % (PREFIX, cycle.get('state'), cycle.get('refusal')))
                check('pm/new-project-run', [
                    ('the factory loop starts the factory project\'s cycle for the NEW_PROJECT message',
                     cycle.get('new_project_subject', {}).get('proposal_id') == pid_e and cycle.get('dispatch')),
                    ('the PM run is dispatched through the Runner with the new-project instruction, his words and the '
                     'identities to choose from',
                     payload.get('operation') == 'new_project' and payload.get('proposal_id') == pid_e
                     and payload.get('text') == 'start a new project called estuary for the river trail'
                     and payload.get('output_schema') == PP.DOCUMENT
                     and [i['id'] for i in payload.get('identities') or []] == ['bcengi', 'nokey', 'personal']),
                    ('the run\'s final document becomes the one proposal, presented once',
                     cycle.get('state') == 'proposed' and estuary_record.get('state') == 'presented'
                     and estuary_record.get('dispatch') == cycle.get('dispatch')
                     and (estuary_record.get('presented') or {}).get('objective') == 'The river trail map')])
        finally:
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])


_v143_started = __import__('time').monotonic()
_v143_suite()
print('VELDO-0143 suite seconds: %.3f' % (__import__('time').monotonic() - _v143_started))
