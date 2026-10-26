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
service's take-on and its new-project pass run in this process (control_service.Service over the same store):
the provisioner's hand-off (VELDO-0161 TAKING IT ON) reaches it through control_client's Authority judging the
request as the socket's serving side does, and where local sockets may be made, the provisioner the service starts
as its own process hands its repository over a real socket served by the suite's loop (service/hand-off). No
private key byte, signature or token is printed or retained.
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
    import select
    import shutil
    import subprocess
    import sys
    import tempfile
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
        'control_telegram_report.py': ROOT / ".veldo" / "control_telegram_report.py",
        'control_channel_presentation.py': ROOT / ".veldo" / "control_channel_presentation.py",
        'control_request_settlement.py': ROOT / ".veldo" / "control_request_settlement.py",
        'control_git_identity.py': ROOT / ".veldo" / "control_git_identity.py",
    }
    PREFIX = 'VELDO-0143 '
    # VELDO-0143 R5-3: the fault a line names when it defers its cycles to the factory line.
    DEFERRED = 'pm_cycles:deferred_to_factory_line'
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

    @contextlib.contextmanager
    def stage_kept():
        """The fixture's graph stage guard (scripts/suites/support/graph_stage.py) raises at the fixture's end when an
        exchange resolved the account's graph stage: every region then counts as raised, so each ran/ row is red."""
        try:
            yield
        except AssertionError as error:
            if not getattr(error, 'graph_stage_escaped', False):
                raise
            print('  %sdetail: %s' % (PREFIX, error))
            raised.extend((first, repr(error)) for first in regions)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    if not PRODUCTION['control_project_proposal.py'].is_file():
        for label in ('factory/own-repository', 'intake/new-project-routed', 'proposal/fields', 'proposal/nothing-asked',
                      'proposal/one-answer', 'proposal/correction', 'proposal/refusals', 'provision/settlement-required',
                      'provision/created', 'provision/answered-and-corrected', 'provision/directory-not-empty',
                      'provision/adoption-path', 'provision/step-failures', 'provision/checks-before-creation',
                      'provision/interrupted', 'provision/observed', 'activation/order', 'activation/applied',
                      'activation/failed-activates-nothing', 'activation/admitted-without-question',
                      'activation/new-line', 'provision/handed-over', 'provision/signing-no-agent', 'service/provisions',
                      'service/hand-off', 'pm/new-project-run', 'proposal/correction-bound', 'proposal/name-taken',
                      'activation/name-taken', 'proposal/no-provisioner', 'proposal/presentation-interrupted',
                      'service/pm-settled-due', 'activation/line-from-pass',
                      'activation/factory-line-kept', 'activation/factory-line-restart', 'proposal/correction-negated',
                      'proposal/correction-phrasings', 'activation/factory-intake-current',
                      'activation/factory-paused-resumed', 'activation/new-projects-kept', 'activation/factory-canceled',
                      'proposal/correction-told', 'proposal/choices', 'proposal/own-message-doubt',
                      'proposal/adoption-visibility', 'proposal/identities-fold-alike', 'proposal/not-presentable',
                      'proposal/adoption-pick-folds', 'pm/graph-stage-own'):
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
            with wire.active():
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
    conform_formats = load('v143_conform_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    formats = json.loads((ROOT / 'proof/VELDO-0062/cli-formats.json').read_text())
    with stage_kept(), helper.fixture(ROOT, PRODUCTION, cycle_budget=100, compiled_sources=True) as f:
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
            projects_root = {name: base / ('projects-' + name) for name in ('personal', 'bcengi', 'nokey', 'outward')}
            for path in projects_root.values():
                path.mkdir()
            TOKENS = {'personal': '-'.join(('personal', 'token', os.urandom(12).hex())),
                      'bcengi': '-'.join(('bcengi', 'token', os.urandom(12).hex()))}
            LOGIN_OWNERS = {TOKENS['personal']: 'olga-p', TOKENS['bcengi']: 'olga-b'}

            def identity(name, owner, label, token_name, default_visibility='private'):
                reference = 'keychain:%s/api' % token_name
                return dict(id=name, label=label, author_name='Olga ' + label, author_email='%s@example.invalid' % name,
                            remote_host='github.com', remote_owner=owner, api_token=reference,
                            push_credential=dict(kind='token', reference=reference),
                            projects_root=str(projects_root.get(name) or base / ('projects-' + name)),
                            default_visibility=default_visibility)
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
                            str(keys / 'settlement')], check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL,
                            env=R._quiet_env())
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
                    return LOGIN_OWNERS.get(header[len('Bearer '):]) if header.startswith('Bearer ') else None

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
            # The provisioner configuration setup lays down in the state root: a proposal is made only where one is
            # installed (VELDO-0143 F6).
            provisioner_file = state_root / 'host' / 'provisioner.json'
            provisioner_file.write_text(json.dumps(effect_config))
            provisioner_file.chmod(0o600)

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

            decisions = PP.NewProjects(S, CM, conn, ids, 'authority', journal_sign, inbox=inbox, settlement=settlement,
                                       presenter=presenter, assignment=I, requester='pm',
                                       request_sign=lambda b: sign_as('pm', b), templates=str(ROOT / 'engine'),
                                       provisioner=str(provisioner_file))

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
                    ('it offers each configured identity with each visibility as a choice, and no plain accept '
                     '(no identity is shown) [%s]' % (request.get('data', {}).get('choices'),),
                     request.get('data', {}).get('choices') == ['accept %s %s' % (i, v) for i in ('bcengi', 'nokey', 'personal')
                                                                for v in ('private', 'public')]
                     + ['return_for_elaboration', 'reject']
                     and request.get('data', {}).get('choices') == PP.choices(shown)
                     and (presenter.current(drift_record.get('request')) or {}).get('rulings')
                     == ['approve'] * 6 + ['return_for_elaboration', 'reject']),
                    ('what he is shown is exactly the brief of that proposal, naming every value',
                     request.get('data', {}).get('brief') == PP.brief(shown)
                     and all(word in PP.brief(shown) for word in ('driftwood', 'bcengi', 'personal', 'https://github.com/',
                                                                   'default team revision', 'default_pipeline',
                                                                   'The harbor site\'s first page')))])

            with region('proposal/one-answer'):
                answered = answer(drift_record['request'], 'accept bcengi private',
                                  "Personally I'd make it public, not bcengi")
                after_answer = bot_messages()
                applied = decisions.apply_settled()
                drift_after = PP.read(conn, drift_decision) or {}
                drift_judged = PP.settled(S, CM, conn, drift_decision)
                again = decisions.apply_settled()
                check('proposal/one-answer', [
                    ('his one answer settles it', answered.get('outcome') in ('accepted', 'settled')
                     and drift_after.get('state') == 'settled' and drift_after.get('path') == 'answer'),
                    ('the choice he picked binds exactly its identity and visibility, whatever his reason says',
                     drift_judged['proposal']['identity'] == 'bcengi'
                     and drift_judged['proposal']['remote']['url'] == 'https://github.com/bcengi/driftwood.git'
                     and drift_judged['proposal']['remote']['visibility'] == 'private'
                     and drift_judged['proposal'] == PP.answered(drift_record['presented'], 'accept bcengi private')
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
                corrected = decisions.correct(reef_decision, document(pid3, 'reef-watch', None, None),
                                              dispatch='pm-np-reef-correction')
                reef_judged = PP.settled(S, CM, conn, reef_decision)
                check('proposal/correction', [
                    ('a message naming the identity but not by the owner\'s whole words is presented',
                     reef.get('outcome') == 'presented' and 'identity_not_in_message' in (reef.get('asked') or [])),
                    ('his correction hands his words to the factory PM, nothing is asked',
                     correcting.get('state') == 'correcting'
                     and (correcting.get('correction') or {}).get('rationale') == 'call it reef-watch and make it public'
                     and len(waiting) == 1 and waiting[0]['correction']['presented'] == correcting.get('presented')),
                    ('the PM\'s corrected proposal settles it with no second presentation: the new name, and the '
                     'identity and visibility he was shown, whatever his words said of them',
                     corrected.get('ok') and reef_judged['path'] == 'correction'
                     and reef_judged['proposal']['project'] == 'reef-watch'
                     and reef_judged['proposal']['identity'] == 'personal'
                     and reef_judged['proposal']['remote']['visibility'] == 'private'
                     and reef_judged['proposal']['repository'] == correcting['presented']['repository']
                     and bot_messages() == after_return and len([r for r in new_project_requests()]) == 2)])

            with region('proposal/choices'):
                # VELDO-0143 round 7 (owner decision, Telegram 36174 and 36175): the identity and the visibility are
                # offered choices he picks. accept approves what is shown; a pick binds exactly the identity and the
                # visibility it names; a choice not offered is refused by name, and nothing is recorded.
                def presented_for(name, identity_name, visibility=None):
                    result = send('api_request', 'start a new project called %s' % name)
                    pid, _ = routed(result)
                    made = decisions.propose(pid, document(pid, name, identity_name, visibility), dispatch=next_id('pm-np'))
                    held_ = PP.read(conn, made.get('decision')) or {}
                    return made.get('decision'), held_.get('request'), held_.get('presented') or {}
                d_sk, r_sk, shown_sk = presented_for('skerry', 'personal')
                offered_sk = (entity(r_sk) or {}).get('data', {}).get('choices')
                picked_sk = answer(r_sk, 'accept personal public', 'keep it private under bcengi')
                decisions.apply_settled()
                judged_sk = PP.settled(S, CM, conn, d_sk)
                d_gu, r_gu, shown_gu = presented_for('gully', 'bcengi', 'public')
                answer(r_gu, 'accept', 'not this account, make it private')
                decisions.apply_settled()
                judged_gu = PP.settled(S, CM, conn, d_gu)
                # Choices that are not offered, typed as he might: refused by name, nothing recorded, still presented.
                d_sh, r_sh, shown_sh = presented_for('shingle', 'personal')
                d_sb, r_sb, _shown_sb = presented_for('sandspit', None)
                unmatched = {}
                for rid_u, typed in ((r_sh, 'accept bc\u0435ngi private'), (r_sh, 'accept \uff42cengi private'),
                                     (r_sh, 'accept stranger private'), (r_sh, 'accept personal private'),
                                     (r_sh, 'use bcengi'), (r_sh, 'Personally'), (r_sb, 'accept')):
                    journal_u = journal()
                    unmatched[(rid_u == r_sb, typed)] = (answer(rid_u, typed, 'my reason'), journal() == journal_u)
                still = [(PP.read(conn, d) or {}).get('state') for d in (d_sh, d_sb)]
                answer(r_sh, 'accept bcengi private', 'fine')
                decisions.apply_settled()
                judged_sh = PP.settled(S, CM, conn, d_sh)
                # The one judge: a decision that binds another identity than his pick (the PM's document's) is refused.
                held_sh = PP.read(conn, d_sh)
                forged_sh = PP.resolve(held_sh['presented'], 'personal')
                decisions.write(d_sh, 'settled', step='answer', path='answer', proposal=forged_sh)
                try:
                    PP.settled(S, CM, conn, d_sh)
                    judge_sh = None
                except PP.Refused as error:
                    judge_sh = error.code
                # VELDO-0143 round 8 (R7-4): a request that offered him other choices than the proposal's settles
                # nothing, whatever he picked: its accept is answered and applied, and the one judge refuses it.
                real_choices = PP.choices
                PP.choices = lambda proposal: ['accept', 'reject']
                try:
                    d_ch, r_ch, _shown_ch = presented_for('chine', 'personal')
                finally:
                    PP.choices = real_choices
                offered_ch = (entity(r_ch) or {}).get('data', {}).get('choices')
                answer(r_ch, 'accept', 'fine')
                decisions.apply_settled()
                try:
                    PP.settled(S, CM, conn, d_ch)
                    judge_ch = None
                except PP.Refused as error:
                    judge_ch = error.code
                state_ch = (PP.read(conn, d_ch) or {}).get('state')
                # Ended here, so no later pass provisions what the judge refused.
                decisions._fail(d_ch, 'answer', 'invalid_input:fixture')
                check('proposal/choices', [
                    ('a proposal that shows an identity offers accept, every other identity and visibility as a pick, '
                     'return_for_elaboration and reject [%s]' % (offered_sk,),
                     offered_sk == ['accept', 'accept bcengi private', 'accept bcengi public', 'accept nokey private',
                                    'accept nokey public', 'accept personal public', 'return_for_elaboration', 'reject']
                     and all(word in PP.brief(shown_sk) for word in ('accept <identity> <private or public>',
                                                                      'bcengi: directory', 'nokey: directory',
                                                                      'personal: directory'))),
                    ('his pick binds exactly the identity and visibility it names, whatever his reason says',
                     picked_sk.get('outcome') in ('accepted', 'settled') and judged_sk['path'] == 'answer'
                     and judged_sk['proposal']['identity'] == 'personal'
                     and judged_sk['proposal']['remote']['visibility'] == 'public'
                     and judged_sk['proposal']['directory'] == str(projects_root['personal'] / 'skerry')),
                    ('accept keeps the values shown, whatever his reason says',
                     judged_gu['proposal']['identity'] == 'bcengi'
                     and judged_gu['proposal']['remote']['visibility'] == 'public'
                     and judged_gu['proposal']['remote']['owner'] == 'bcengi')] + [
                    ('%r%s is refused unmatched_choice by name and nothing is recorded [%s]'
                     % (typed, ' (no identity shown)' if no_identity else '', outcome.get('reason')),
                     outcome.get('outcome') == 'refused' and outcome.get('reason') == 'unmatched_choice' and unchanged)
                    for (no_identity, typed), (outcome, unchanged) in unmatched.items()] + [
                    ('each stays presented, and a choice offered still settles it',
                     still == ['presented', 'presented'] and judged_sh['proposal']['identity'] == 'bcengi'
                     and judged_sh['proposal']['remote']['visibility'] == 'private'),
                    ('the one judge refuses a decision whose identity is not his pick, by name [%s]' % judge_sh,
                     judge_sh == 'no_settled_decision:proposal'),
                    ('the one judge refuses a request that offered other choices than the proposal\'s, by name [%s %s]'
                     % (offered_ch, judge_ch),
                     offered_ch == ['accept', 'reject'] and state_ch == 'settled' and judge_ch == 'no_settled_decision:choices')])

            with region('proposal/correction-bound'):
                # A correction is bound to his words (VELDO-0143 F2): the PM reads them, it never chooses for him.
                def asked_for(name, identity_name, visibility=None):
                    result = send('api_request', 'start a new project called %s' % name)
                    pid, _ = routed(result)
                    made = decisions.propose(pid, document(pid, name, identity_name, visibility), dispatch=next_id('pm-np'))
                    return made.get('decision'), pid, (PP.read(conn, made.get('decision')) or {}).get('request')

                def returned(rid, words, ruling='return_for_elaboration'):
                    answer(rid, ruling, words)
                    return decisions.apply_settled()

                def state_of(decision):
                    held_ = PP.read(conn, decision) or {}
                    return held_.get('state'), held_.get('reason')
                cases_bound, before_bound = {}, (bot_messages(), len(hub['calls']), new_project_requests())
                # (a) he was asked the identity and returned it with words that name one: a correction never picks it.
                d_yes, p_yes, r_yes = asked_for('sandbar', None)
                returned(r_yes, 'call it sandbar-two, under bcengi')
                outcome_yes = decisions.correct(d_yes, document(p_yes, 'sandbar-two', 'bcengi', None), dispatch=next_id('pm-npc'))
                cases_bound['unpicked'] = (state_of(d_yes), outcome_yes)
                # (b) to (e): the PM's corrected document changes what his words did not.
                for case, name, words, corrected in (
                        ('identity', 'shoal', 'call it shoal-two', ('shoal-two', 'bcengi', None)),
                        ('visibility', 'spit', 'call it spit-two', ('spit-two', 'personal', 'public')),
                        ('mode', 'jetty', 'call it anchorage', ('anchorage', 'personal', None)),
                        ('project', 'pier', 'make it public', ('wharf', 'personal', 'public'))):
                    if case == 'mode':
                        anchorage = projects_root['personal'] / 'anchorage'
                        GP.run(['git', 'init', '-q', '-b', 'main', str(anchorage)], check=True, capture_output=True)
                        (anchorage / 'README').write_text('anchorage\n')
                        git(anchorage, 'add', '-A')
                        GP.run(['git', '-C', str(anchorage), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'mine'],
                               check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
                        refs_before = git(anchorage, 'for-each-ref')
                    decision_b, pid_b, rid_b = asked_for(name, 'personal')
                    returned(rid_b, words)
                    outcome_b = decisions.correct(decision_b, document(pid_b, *corrected), dispatch=next_id('pm-npc'))
                    cases_bound[case] = (state_of(decision_b), outcome_b)
                anchorage_refs = git(projects_root['personal'] / 'anchorage', 'for-each-ref')
                # (f) a correction that changes the name and the objective settles them; the identity and the
                # visibility stay as shown (the document may repeat them).
                d_ok, pid_ok, r_ok = asked_for('buoy', 'personal')
                returned(r_ok, 'call it buoy-b, and make the first objective a buoy map')
                ok_outcome = decisions.correct(d_ok, document(pid_ok, 'buoy-b', 'personal', None, objective='A buoy map'),
                                               dispatch='pm-npc-buoy')
                ok_judged = PP.settled(S, CM, conn, d_ok)
                # (g) the judge: a settled correction written without correct(), its identity not his.
                d_g, pid_g, r_g = asked_for('mooring', 'personal')
                returned(r_g, 'call it mooring-two')
                shown_g = PP.read(conn, d_g)
                doc_g = document(pid_g, 'mooring-two', 'bcengi')
                forged_g = PP.build(conn, DOMAIN, intake.proposal(pid_g), doc_g, repository=shown_g['presented']['repository'],
                                    owner=OWNER, chosen=('bcengi', 'private'))
                decisions.write(d_g, 'settled', step='correction', path='correction', proposal=forged_g,
                                project='mooring-two', correction=dict(shown_g['correction'], dispatch='forged', document=doc_g,
                                                                       digest=PP.digest(forged_g)))
                try:
                    PP.settled(S, CM, conn, d_g)
                    judge_g = None
                except PP.Refused as error:
                    judge_g = error.code
                journal_g, calls_g = journal(), len(hub['calls'])
                provision_g = provision(d_g)
                check('proposal/correction-bound', [
                    ('a correction of a proposal that showed no identity cannot pick one: it fails by name %s'
                     % (cases_bound['unpicked'][0],),
                     cases_bound['unpicked'][0] == ('failed', 'invalid_input:correction:identity')
                     and cases_bound['unpicked'][1].get('ok') is False)] + [
                    ('a corrected %s his words did not say fails the decision by name %s' % (case, cases_bound[case][0]),
                     cases_bound[case][0] == ('failed', 'invalid_input:correction:' + case)
                     and cases_bound[case][1].get('ok') is False)
                    for case in ('identity', 'visibility', 'mode', 'project')] + [
                    ('an adoption he was not shown lays nothing in that repository',
                     anchorage_refs == refs_before and not (projects_root['personal'] / 'jetty').exists()),
                    ('a correction of the name and the objective settles them, the identity and visibility as shown',
                     ok_outcome.get('ok') is True and ok_judged['proposal']['identity'] == 'personal'
                     and ok_judged['proposal']['project'] == 'buoy-b' and ok_judged['proposal']['objective'] == 'A buoy map'
                     and ok_judged['proposal']['remote']['visibility'] == 'private'),
                    ('the one judge refuses a settled correction whose identity is not his words, by name [%s]' % judge_g,
                     judge_g == 'no_settled_decision:correction:identity'),
                    ('so the provisioner refuses it at the settlement: nothing written, no directory, GitHub not asked',
                     provision_g.get('reason') == 'no_settled_decision:correction:identity'
                     and provision_g.get('step') == 'settlement' and journal() == journal_g
                     and len(hub['calls']) == calls_g and not (projects_root['bcengi'] / 'mooring-two').exists()),
                    ('none of it asks a second question or reaches GitHub',
                     len(new_project_requests()) == len(before_bound[2]) + 7 and len(hub['calls']) == before_bound[1])])

            with region('proposal/correction-negated'):
                # VELDO-0143 round 7: a correction never changes the identity or the visibility, whatever his words
                # say of them; only a pick does. A PM reading that changes either fails by name; a reading that keeps
                # them settles exactly what he was shown. The phrasings are the round 3 to 6 reviews' own.
                before_negated = (len(hub['calls']), len(new_project_requests()))
                negated_cases = {}
                # (case, name, identity shown, visibility shown, his words, the PM's reading (name, identity,
                # visibility), the field refused or None where it settles as shown)
                for case, name, asked_identity, asked_visibility, words, reading, refused in (
                        ('personally', 'rockbass', 'bcengi', 'public', "Personally I'd make it private",
                         (None, 'personal', 'private'), 'identity'),
                        ('personally-kept', 'rockcod', 'bcengi', 'public', "Personally I'd make it private",
                         (None, None, None), None),
                        ('publicly', 'kelpbed', 'bcengi', 'private', "Let's publicly launch later; for now use personal",
                         (None, 'personal', 'public'), 'identity'),
                        ('this-account', 'rockeel', 'bcengi', None, 'not this account', (None, 'personal', None),
                         'identity'),
                        ('this-account-kept', 'rockling', 'bcengi', None, 'not this account', (None, None, None), None),
                        ('lookalike', 'rockdove', 'personal', None, 'use bc\u0435ngi', (None, 'bcengi', None), 'identity'),
                        ('lookalike-kept', 'rockfoil', 'personal', None, 'use bc\u0435ngi', (None, 'personal', None), None),
                        ('make-private', 'kelpcrab', 'personal', 'public', 'make it private', (None, 'personal', 'private'),
                         'visibility'),
                        ('hidden', 'kelpie', 'personal', 'public', 'keep it hidden', (None, None, 'private'), 'visibility'),
                        ('hidden-kept', 'kelpgull', 'personal', 'public', 'keep it hidden', (None, None, None), None),
                        ('round3', 'saltmarsh', None, None, 'not under bcengi please, and keep it private, not public',
                         (None, 'bcengi', 'public'), 'identity'),
                        ('round4', 'rockrose', 'bcengi', None, "don't use bcengi and use personal",
                         (None, 'personal', None), 'identity'),
                        ('round5', 'kelpwrack', 'personal', 'public', 'not-public', (None, 'personal', 'private'),
                         'visibility'),
                        ('plain', 'rockweed', 'bcengi', None, 'use personal', (None, 'personal', None), 'identity'),
                        ('name-only', 'kelpfish', 'bcengi', 'public', 'call it kelpfish-two',
                         ('kelpfish-two', None, None), None)):
                    decision_n, pid_n, rid_n = asked_for(name, asked_identity, asked_visibility)
                    returned(rid_n, words)
                    outcome_n = decisions.correct(decision_n, document(pid_n, reading[0] or name, *reading[1:]),
                                                  dispatch=next_id('pm-npn'))
                    negated_cases[case] = (state_of(decision_n), outcome_n, decision_n, refused,
                                           (asked_identity, asked_visibility or 'private'))
                said_judged = {case: PP.settled(S, CM, conn, held[2]) for case, held in negated_cases.items()
                               if held[3] is None and held[1].get('ok') is True}
                check('proposal/correction-negated', [
                    ('%s: the reading that changes the %s fails the decision by name %s' % (case, held[3], held[0]),
                     held[0] == ('failed', 'invalid_input:correction:' + held[3]) and held[1].get('ok') is False)
                    for case, held in negated_cases.items() if held[3] is not None] + [
                    ('%s: the reading that keeps them settles exactly what he was shown %s' % (case, held[0]),
                     held[1].get('ok') is True and case in said_judged
                     and (said_judged[case]['proposal']['identity'],
                          said_judged[case]['proposal']['remote']['visibility']) == held[4])
                    for case, held in negated_cases.items() if held[3] is None] + [
                    ('none of it reaches GitHub or asks a second question',
                     len(hub['calls']) == before_negated[0]
                     and len(new_project_requests()) == before_negated[1] + len(negated_cases))])

            with region('proposal/correction-phrasings'):
                # VELDO-0143 round 7: the one judge over every phrasing the round 3 to 6 reviews named, for every
                # identity and visibility he could have been shown and every reading of the PM's (16 each): each
                # settles exactly the four readings that keep what he was shown, and no other.
                VIS_P = PP.VISIBILITIES
                combos_p = [(si, sv, ri, rv) for si in ('personal', 'bcengi') for sv in VIS_P
                            for ri in ('personal', 'bcengi') for rv in VIS_P]

                def shown_p(si, sv):
                    entries = [{'identity': i, 'mode': 'create', 'adoption': None, 'directory': '/p/' + i,
                                'remote': {'name': 'x', 'owner': i, 'url': 'u', 'visibility': sv}}
                               for i in ('bcengi', 'personal')]
                    return dict(next(e for e in entries if e['identity'] == si), project='x', offered=entries)

                def settles_p(words):
                    return sorted((si, sv, ri, rv) for si, sv, ri, rv in combos_p if not PP.correction_problems(
                        shown_p(si, sv), {'project': 'x', 'identity': ri, 'visibility': rv, 'mode': 'create'}, words))
                kept_p = sorted(c for c in combos_p if c[:2] == c[2:])
                phrasings_p = (
                    # round 3
                    'not under bcengi please, and keep it private, not public', 'not under bcengi, use personal',
                    'not bcengi',
                    # round 4
                    'Keep it private, not public.', 'Not under bcengi.', "don't host it publicly",
                    'neither personal nor bcengi', "don't use bcengi and personal", "don't use bcengi and use personal",
                    'dont use bcengi or personal', 'it cannot be public', 'dont make it public', 'nothing public please',
                    'neither public', 'except public', 'other than public', 'anything but public', 'public? no',
                    'it wont be public', 'cant be public', 'didnt want it public', 'avoid public', 'avoid bcengi',
                    'cannot be bcengi', 'bcengi? no', 'nothing bcengi-owned', 'no, bcengi', 'bcengi not personal',
                    # round 5
                    'not public!', 'not public, thanks', 'no bcengi', 'use personal (not bcengi)',
                    'not-public', 'not-bcengi please, personal', 'not\npublic', 'public!? no', 'public?! no way',
                    'public. No.', "don't make it public and keep it private", "keep it private and don't make it public",
                    'not_public', 'non-public', 'use personal', 'make it private', 'use personal and make it private',
                    'Make it public.', 'put it under Bcengi, call it x, and make it public', 'Use personal. Keep it private.',
                    # round 6 (R6-1 to R6-3 and section 2)
                    "Personally I'd make it private", "Let's publicly launch later; for now use personal",
                    "I'd discuss it privately, but go with bcengi", 'make it private, my email is someone@bcengi.com',
                    'like https://github.com/bcengi/shoal but make it private', 'my private account please',
                    'not this account', "that's the wrong owner", 'wrong account, use the other one', 'keep it hidden',
                    'under my own account', 'the other identity please', 'flip the visibility', 'use BCENGI',
                    'use bc\u0435ngi', 'use bc\u0441engi', 'use \uff42cengi', 'n\u043et public', 'no\u200bt public',
                    '\uff4e\uff4f\uff54 public', 'don\u02bct make it public', 'don\u2032t make it public',
                    'use bc\u00a0engi', 'make it public \u274c', 'make it public \U0001f6ab', 'public lol jk',
                    'make it public (kidding)', 'NOT PUBLIC', 'DO NOT make it public', 'never ever public', 'public, not!',
                    'public: nah-uh', 'pas de public', 'use personal' + ' filler' * 20000,
                    'make it public, no worries', "use personal, I'll remove the old one later",
                    "use personal, it's a nonprofit thing", 'use personal, the bcengi one is for work',
                    'use personal, please stop asking', 'I know, use personal', 'Personal, private.',
                    "use personal and make it private, that's all")
                wrong_p = {words[:60]: settles_p(words) for words in phrasings_p if settles_p(words) != kept_p}
                if wrong_p:
                    print('  %sdetail: correction phrasings judged wrongly: %s' % (PREFIX, wrong_p))
                check('proposal/correction-phrasings', [
                    ('every phrasing settles exactly the readings that keep what he was shown, over 16 readings each '
                     '(%d phrasings, %d wrong)' % (len(phrasings_p), len(wrong_p)), not wrong_p),
                    ('a correction that names another identity or visibility never binds it',
                     ('bcengi', 'public', 'personal', 'private') not in settles_p('use personal and make it private')
                     and ('bcengi', 'private', 'personal', 'private') not in settles_p("Personally I'd make it private")
                     and ('personal', 'private', 'bcengi', 'private') not in settles_p('use bc\u0435ngi'))])

            with region('proposal/own-message-doubt'):
                # VELDO-0143 round 7: his own message settles with nothing asked only where nothing in it could mean
                # another identity and the PM set no visibility; any doubt presents it, so he picks.
                # VELDO-0143 round 8 (R7-1): unasked, a repository is only ever private. An identity whose default is
                # public, or a message with a word of visibility, is presented, so he picks.
                GI.configure_identities(conn, DOMAIN, [identity('outward', 'olga-p', 'Outward', 'outward',
                                                                default_visibility='public')], {})
                doubts = {}
                for case, text, name, identity_name, visibility, why in (
                        ('negated', "don't put it under bcengi; start a new project called tarn", 'tarn', 'bcengi',
                         None, 'negated'),
                        ('two identities', 'start a new personal project called scree for bcengi', 'scree', 'personal',
                         None, 'identity_not_alone'),
                        ('lookalike', 'n\u043et under bcengi: start a new project called moraine', 'moraine',
                         'bcengi', None, 'not_plain_text'),
                        ('visibility set', 'start a new personal project called cirque', 'cirque', 'personal', 'public',
                         'visibility_not_private'),
                        ('hyphen-negated', 'start a new bcengi project called fell, not-public', 'fell', 'bcengi', None,
                         'negated'),
                        ('public default', 'start a new outward project called lagune', 'lagune', 'outward', None,
                         'visibility_not_private'),
                        ('public default, private said', 'start a new outward project called saltpan, keep it private',
                         'saltpan', 'outward', None, ('visibility_not_private', 'visibility_in_message')),
                        ('public default, hidden said', 'start shoreline under outward, hidden please', 'shoreline',
                         'outward', None, ('visibility_not_private', 'visibility_in_message')),
                        ('visibility word', 'start a new personal project called sound, make it public', 'sound',
                         'personal', None, 'visibility_in_message'),
                        # VELDO-0143 round 9 (R8-3): words of visibility no list holds; any word the rule has not
                        # read presents it.
                        ('share with everyone', 'start a new bcengi project called shoalwater and share it with '
                         'everyone', 'shoalwater', 'bcengi', None, 'words_not_read'),
                        ('publish', 'start a new bcengi project called kettle, publish it', 'kettle', 'bcengi', None,
                         'words_not_read'),
                        ('opensource', 'start a new bcengi project called esker and make it opensource', 'esker',
                         'bcengi', None, 'words_not_read'),
                        ('publically', 'start a new bcengi project called drumlin, publically', 'drumlin', 'bcengi',
                         None, 'words_not_read'),
                        ('everyone can see', 'start a new personal project called tor everyone can see', 'tor',
                         'personal', None, 'words_not_read')):
                    result = send('api_request', text)
                    pid, _ = routed(result)
                    made = decisions.propose(pid, document(pid, name, identity_name, visibility), dispatch=next_id('pm-np'))
                    doubts[case] = (made, why, (PP.read(conn, made.get('decision')) or {}))
                lagune = doubts['public default'][2]
                lagune_choices = (entity(lagune.get('request') or '') or {}).get('data', {}).get('choices') or []
                check('proposal/own-message-doubt', [
                    ('%s: presented for him to pick, not settled from his words %s' % (case, made.get('asked')),
                     made.get('outcome') == 'presented'
                     and all(w in (made.get('asked') or []) for w in (why if isinstance(why, tuple) else (why,)))
                     and held.get('state') == 'presented' and held.get('path') is None)
                    for case, (made, why, held) in doubts.items()] + [
                    ('an identity whose default is public is shown public and offered private as a pick, so a public '
                     'repository comes only from his answer [%s]' % (lagune_choices,),
                     PP.visibility_of(lagune.get('presented')) == 'public' and 'accept outward private' in lagune_choices
                     and 'accept' in lagune_choices)])

            with region('proposal/name-taken'):
                # A name is one project (VELDO-0143 F3): another live decision's name, compared as GitHub compares.
                calls_n, requests_n = len(hub['calls']), new_project_requests()
                taken_msg = send('api_request', 'start a new bcengi project called Driftwood')
                pid_n, _ = routed(taken_msg)
                taken = decisions.propose(pid_n, document(pid_n, 'Driftwood', 'bcengi'), dispatch='pm-np-taken')
                check('proposal/name-taken', [
                    ('a project named like another live decision\'s is refused before he is asked [%s]' % taken.get('reason'),
                     taken.get('ok') is False and taken.get('reason') == 'stale_subject:project_exists'),
                    ('the decision is failed by that name, so the message is not read again and his report tells him',
                     state_of(PP.decision_id(pid_n)) == ('failed', 'stale_subject:project_exists')
                     and pid_n not in {p['proposal_id'] for p in PP.pending(conn)}),
                    ('nothing is presented, built or created', new_project_requests() == requests_n
                     and len(hub['calls']) == calls_n and not (projects_root['bcengi'] / 'Driftwood').exists())])

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
                    ('the store binds it; with no service running, the hand-off is named and it waits for an instance',
                     S.bound_repository(conn, DOMAIN, tide_repo) == os.path.realpath(str(tide_dir))
                     and held.get('state') == 'provisioning' and tide_result.get('state') == 'provisioning'
                     and tide_result.get('reason') == 'not_taken_on:authority_unavailable')])

            with region('provision/answered-and-corrected'):
                with fenced(wire):
                    drift_result = provision(drift_decision)
                    reef_result = provision(reef_decision)
                    skerry_result = provision(d_sk)
                drift_repo, reef_repo = drift_judged['proposal']['repository'], reef_judged['proposal']['repository']
                check('provision/answered-and-corrected', [
                    ('his answered identity: the remote is created in that organization, under its owner',
                     drift_result.get('ok') and ('POST', '/orgs/bcengi/repos', 'olga-b',
                                                 {'name': 'driftwood', 'private': True, 'auto_init': False,
                                                  'has_wiki': False}) in hub['calls']
                     and (record(drift_repo) or {}).get('identity') == 'bcengi'
                     and (projects_root['bcengi'] / 'driftwood').is_dir()),
                    ('his corrected name, at the visibility he was shown: private',
                     reef_result.get('ok') and hub['repos'][('olga-p', 'reef-watch')]['body']['private'] is True
                     and (record(reef_repo) or {}).get('origin') == 'created'),
                    ('his picked visibility: public',
                     skerry_result.get('ok') and hub['repos'][('olga-p', 'skerry')]['body']['private'] is False
                     and (record(judged_sk['proposal']['repository']) or {}).get('identity') == 'personal')])

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
                    # VELDO-0143 round 8 (R7-2, R7-1): an adoption keeps its remote as it is, a visibility no one here
                    # knows, so even his own message naming it is presented and he answers it.
                    decision_h, _, proposed_h = own_decision('harbor')
                    answer((PP.read(conn, decision_h) or {}).get('request'), 'accept', 'adopt it as it is')
                    decisions.apply_settled()
                    harbor_judged = PP.settled(S, CM, conn, decision_h)
                    laid = harbor_judged['proposal']['adoption']['scaffold_commit']
                    harbor_result = provision(decision_h)
                harbor_record = record(harbor_judged['proposal']['repository']) or {}
                check('provision/adoption-path', [
                    ('his own message naming a directory that is already a Git repository is presented, the remote\'s '
                     'visibility kept as it is [%s]' % (proposed_h.get('asked'),),
                     proposed_h.get('outcome') == 'presented' and 'visibility_not_private' in (proposed_h.get('asked') or [])
                     and harbor_judged['path'] == 'answer'
                     and harbor_judged['proposal']['remote']['visibility'] == PP.AS_ON_REMOTE),
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

            with region('proposal/adoption-visibility'):
                # VELDO-0143 round 8 (R7-2): nothing on the adoption path applies a visibility, so an adopted entry is
                # offered none it cannot keep: its pick names the identity alone, the brief says the remote stays as
                # it is on GitHub, and a decision recording a visibility for an adoption is not one the judge settles.
                def existing(name):
                    """A directory under personal's projects root that is already a Git repository, its origin on
                    GitHub."""
                    path, bare = projects_root['personal'] / name, base / 'gh' / 'olga-p' / (name + '.git')
                    GP.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True, capture_output=True)
                    GP.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
                    (path / 'README').write_text(name + '\n')
                    git(path, 'add', '-A')
                    GP.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', name], check=True,
                           capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
                    git(path, 'push', '-q', str(bare), 'main:main')
                    git(path, 'remote', 'add', 'origin', wire.remote(name, bare, owner='olga-p'))
                existing('quay')
                existing('slipway')
                with fenced(wire):
                    msg_q = send('api_request', 'start a new project called quay')
                    pid_q, _ = routed(msg_q)
                    made_q = decisions.propose(pid_q, document(pid_q, 'quay', 'bcengi'), dispatch=next_id('pm-np'))
                    # A correction renaming an adoption he was shown would create a repository whose visibility he
                    # never picked: it fails by name, and nothing is created.
                    msg_w = send('api_request', 'start a new project called slipway')
                    pid_w, _ = routed(msg_w)
                    made_w = decisions.propose(pid_w, document(pid_w, 'slipway', 'personal'), dispatch=next_id('pm-np'))
                    answer((PP.read(conn, made_w.get('decision')) or {}).get('request'), 'return_for_elaboration',
                           'call it slipway-two')
                    decisions.apply_settled()
                    calls_w = len(hub['calls'])
                    renamed_w = decisions.correct(made_w.get('decision'), document(pid_w, 'slipway-two', None),
                                                  dispatch=next_id('pm-npc'))
                    state_w = state_of(made_w.get('decision'))
                d_q = made_q.get('decision')
                held_q = PP.read(conn, d_q) or {}
                shown_q = held_q.get('presented') or {}
                entry_q = PP.shown_entry(shown_q, 'personal') or {}
                offered_q = (entity(held_q.get('request') or '') or {}).get('data', {}).get('choices') or []
                typed_q = {t: answer(held_q.get('request'), t, 'keep it private')
                           for t in ('accept personal private', 'accept personal public', 'accept personal')}
                still_q = (PP.read(conn, d_q) or {}).get('state')
                answer(held_q.get('request'), 'accept personal adopt', 'adopt it')
                decisions.apply_settled()
                judged_q = PP.settled(S, CM, conn, d_q)
                try:
                    PP.resolve(shown_q, 'personal', 'private')
                    resolve_q = None
                except PP.Refused as error:
                    resolve_q = error.code
                forged_q = dict(judged_q['proposal'], remote=dict(judged_q['proposal']['remote'], visibility='private'))
                decisions.write(d_q, 'settled', step='answer', path='answer', proposal=forged_q)
                try:
                    PP.settled(S, CM, conn, d_q)
                    judge_q = None
                except PP.Refused as error:
                    judge_q = error.code
                # Ended here, so no later pass adopts what this row forged.
                decisions._fail(d_q, 'answer', 'invalid_input:fixture')
                check('proposal/adoption-visibility', [
                    ('the adopted entry records its remote\'s visibility as it is, never private or public',
                     entry_q.get('mode') == 'adopt' and PP.visibility_of(entry_q) == PP.AS_ON_REMOTE),
                    ('it is offered as its identity and adopt, with no visibility it cannot keep [%s]' % (offered_q,),
                     'accept personal adopt' in offered_q and 'accept personal private' not in offered_q
                     and 'accept personal public' not in offered_q and offered_q == PP.choices(shown_q)
                     and 'accept bcengi public' in offered_q),
                    ('the brief says the adopted repository stays as it is on GitHub',
                     'visibility as it is on GitHub' in PP.brief(shown_q) and '"accept <identity> adopt"' in PP.brief(shown_q)),
                    ('a visibility typed for the adopted identity, or its identity alone, is refused unmatched_choice '
                     'and it stays presented',
                     all(r.get('outcome') == 'refused' and r.get('reason') == 'unmatched_choice' for r in typed_q.values())
                     and still_q == 'presented'),
                    ('his pick adopts it as it is', judged_q['path'] == 'answer' and judged_q['proposal']['mode'] == 'adopt'
                     and judged_q['proposal']['identity'] == 'personal'
                     and PP.visibility_of(judged_q['proposal']) == PP.AS_ON_REMOTE),
                    ('no visibility can be resolved onto an adoption, and the judge refuses a decision recording one '
                     '[%s %s]' % (resolve_q, judge_q),
                     resolve_q == 'invalid_input:visibility' and judge_q == 'no_settled_decision:proposal'),
                    ('a resolved adoption recording private or public is not a proposal, whatever else matches [%s]'
                     % (PP.proposal_problems(forged_q),),
                     PP.proposal_problems(forged_q) == ['invalid_input:proposal:remote']
                     and PP.proposal_problems(dict(forged_q, remote=dict(forged_q['remote'], visibility='public')))
                     == ['invalid_input:proposal:remote'] and PP.proposal_problems(judged_q['proposal']) == []),
                    ('a correction renaming the adoption he was shown fails invalid_input:correction:mode, nothing '
                     'created [%s %s]' % (renamed_w.get('reason'), state_w),
                     (PP.read(conn, made_w.get('decision')) or {}).get('presented', {}).get('mode') == 'adopt'
                     and renamed_w.get('ok') is False and state_w == ('failed', 'invalid_input:correction:mode')
                     and len(hub['calls']) == calls_w and not (projects_root['personal'] / 'slipway-two').exists())])

            with region('proposal/adoption-pick-folds'):
                # VELDO-0143 round 9 (R8-1): a typed pick is folded ('-' and '_' are spaces), so an adoption's pick
                # `accept <id>` folded like the creation pick `accept <other id> <visibility>` of an id it extends
                # (bcengi-private beside bcengi). An adoption's pick ends in adopt, never a visibility, so no pick of
                # one identity folds like another's, and a configuration of those two ids stays one.
                projects_root['bcengi-private'] = base / 'projects-bcengi-private'
                projects_root['bcengi-private'].mkdir()
                for name in ('shoal', 'cobble'):
                    path, bare = projects_root['bcengi-private'] / name, base / 'gh' / 'olga-p' / (name + '.git')
                    GP.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True, capture_output=True)
                    GP.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
                    (path / 'README').write_text(name + '\n')
                    git(path, 'add', '-A')
                    GP.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', name], check=True,
                           capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
                    git(path, 'push', '-q', str(bare), 'main:main')
                    git(path, 'remote', 'add', 'origin', wire.remote(name, bare, owner='olga-p'))
                try:
                    GI.configure_identities(conn, DOMAIN, [identity('bcengi-private', 'olga-p', 'Bcengi private',
                                                                    'personal')], {})
                    configured_f = None
                except GI.Refused as error:
                    configured_f = error.code
                try:
                    with fenced(wire):
                        msg_f = send('api_request', 'start a new project called shoal')
                        pid_f, _ = routed(msg_f)
                        made_f = decisions.propose(pid_f, document(pid_f, 'shoal', 'bcengi'), dispatch=next_id('pm-np'))
                        msg_g = send('api_request', 'start a new project called cobble')
                        pid_g, _ = routed(msg_g)
                        made_g = decisions.propose(pid_g, document(pid_g, 'cobble', None), dispatch=next_id('pm-np'))
                finally:
                    conn.execute('DELETE FROM git_identities WHERE domain=? AND identity=?', (DOMAIN, 'bcengi-private'))
                held_f = PP.read(conn, made_f.get('decision')) or {}
                held_g = PP.read(conn, made_g.get('decision')) or {}
                offered_f = (entity(held_f.get('request') or '') or {}).get('data', {}).get('choices') or []
                offered_g = (entity(held_g.get('request') or '') or {}).get('data', {}).get('choices') or []
                typed_f = {t: answer(held_f.get('request'), t, 'bcengi, private')
                           for t in ('accept bcengi private', 'accept bcengi-private', 'accept bcengi_private')}
                still_f = (PP.read(conn, made_f.get('decision')) or {}).get('state')
                answer(held_f.get('request'), 'accept', 'as shown')
                decisions.apply_settled()
                judged_f = PP.settled(S, CM, conn, made_f.get('decision'))
                # Ended here, so no later pass creates what this row only answers.
                for made in (made_f, made_g):
                    if (PP.read(conn, made.get('decision')) or {}).get('state') in PP.LIVE:
                        decisions._fail(made.get('decision'), 'answer', 'invalid_input:fixture')
                fold = GI.presentation_fold()
                folded_f, folded_g = [fold(c) for c in offered_f], [fold(c) for c in offered_g]
                check('proposal/adoption-pick-folds', [
                    ('bcengi beside bcengi-private is a configuration [%s]' % configured_f, configured_f is None),
                    ('bcengi creating shoal is shown, bcengi-private adopting it is offered as its pick ending in adopt '
                     '[%s]' % (offered_f,),
                     made_f.get('outcome') == 'presented' and 'accept bcengi-private adopt' in offered_f
                     and 'accept bcengi public' in offered_f and 'accept' in offered_f
                     and len(set(folded_f)) == len(folded_f)),
                    ('"accept bcengi private", the pair accept approves, and bcengi-private without adopt are refused '
                     'unmatched_choice, it stays presented [%s]' % ({t: r.get('reason') for t, r in typed_f.items()},),
                     all(r.get('outcome') == 'refused' and r.get('reason') == 'unmatched_choice'
                         for r in typed_f.values()) and still_f == 'presented'),
                    ('accept creates shoal under bcengi, private, as shown',
                     judged_f['proposal']['identity'] == 'bcengi' and judged_f['proposal']['mode'] == 'create'
                     and PP.visibility_of(judged_f['proposal']) == 'private'),
                    ('with no identity shown the picks of both still fold apart, so it is presented, not refused '
                     'ambiguous_choice [%s %s]' % (made_g.get('reason'), offered_g),
                     made_g.get('outcome') == 'presented' and 'accept bcengi private' in offered_g
                     and 'accept bcengi-private adopt' in offered_g and len(set(folded_g)) == len(folded_g))])

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

            with region('provision/checks-before-creation'):
                # VELDO-0161's checks that change nothing, before anything is made: an adoption signer this host
                # does not enroll is refused before any directory exists or GitHub is asked.
                stranger_key = keys / 'stranger-signer'
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v143-stranger', '-f',
                                str(stranger_key)], check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL,
                                env=R._quiet_env())
                decision_u, _, _ = own_decision('unsigned')
                calls, pushes = len(hub['calls']), len(wire.invocations())
                with fenced(wire):
                    unsigned = EC.provision(dict(effect_config, adoption_signer={'key': str(stranger_key)}), decision_u)
                unsigned_record = record(PP.read(conn, decision_u)['proposal']['repository']) or {}
                # The repository's own configuration, judged before GitHub is asked: a key naming a command that the
                # author step leaves behind (injected) refuses the remote step before any network write.
                decision_c, _, _ = own_decision('commanded')
                saved = dict(EC.STEP_FUNCTIONS)

                def commanded(run):
                    done = saved['author'](run)
                    EC.CR.git(run['proposal']['directory'], 'config', 'core.fsmonitor', 'true')
                    return done
                EC.STEP_FUNCTIONS['author'] = commanded
                calls_c, pushes_c = len(hub['calls']), len(wire.invocations())
                try:
                    with fenced(wire):
                        commanded_result = provision(decision_c)
                finally:
                    EC.STEP_FUNCTIONS.clear()
                    EC.STEP_FUNCTIONS.update(saved)
                commanded_record = record(PP.read(conn, decision_c)['proposal']['repository']) or {}
                check('provision/checks-before-creation', [
                    ('an adoption signer this host does not enroll is refused at the signature, before the directory',
                     unsigned.get('reason') == 'signature_refused:not_enrolled' and unsigned_record.get('state') == 'failed'
                     and unsigned_record.get('failed_step') == 'signature'
                     and [h['step'] for h in unsigned_record.get('history') or []] == ['settled', 'signature']),
                    ('nothing is made for it: no directory, no GitHub call, no push',
                     not (projects_root['personal'] / 'unsigned').exists() and len(hub['calls']) == calls
                     and len(wire.invocations()) == pushes),
                    ('a repository configuration naming a command is refused at the remote step, by name',
                     commanded_result.get('reason') == 'invalid_input:repository_command:core.fsmonitor'
                     and commanded_record.get('state') == 'failed' and commanded_record.get('failed_step') == 'remote'
                     and [h['step'] for h in commanded_record.get('history') or []]
                     == ['settled', 'directory', 'init', 'scaffold', 'author', 'commit', 'remote']),
                    ('GitHub is not asked to create a remote for it, and nothing is pushed or signed',
                     len(hub['calls']) == calls_c and len(wire.invocations()) == pushes_c
                     and commanded_record.get('enrollment') is None
                     and binding_of(projects_root['personal'] / 'commanded') is None)])

            with region('provision/interrupted'):
                # VELDO-0161's INTERRUPTED rule, for a created repository: a run that ended (killed, the host
                # restarted) left its record provisioning with no binding; a live run holds the lock.
                decision_i, _, _ = own_decision('stranded')
                stranded = PP.read(conn, decision_i)['proposal']
                for step in ('settled', 'directory', 'init'):
                    R.write(S, conn, ('authority', journal_sign), stranded['repository'], 'provisioning', step=step,
                            origin='created', domain_uuid=DOMAIN, identity='personal', path=stranded['directory'],
                            request=decision_i, project='stranded', enrollment=None, reason=None, failed_step=None)
                calls = len(hub['calls'])
                interrupted = provision(decision_i)
                stranded_record = record(stranded['repository']) or {}
                decision_l, _, _ = own_decision('locked')
                locked = PP.read(conn, decision_l)['proposal']
                lock = EC.AD.hold(effect_config, locked['repository'])
                before = journal()
                try:
                    in_progress = provision(decision_l)
                    unchanged = journal() == before and record(locked['repository']) is None
                finally:
                    os.close(lock)
                # Once the live run is gone the decision is judged again: here its directory is taken meanwhile.
                (projects_root['personal'] / 'locked').mkdir()
                (projects_root['personal'] / 'locked' / 'notes.txt').write_text('mine\n')
                after_lock = provision(decision_l)
                check('provision/interrupted', [
                    ('a record the decision left provisioning with no binding is failed unknown_outcome:interrupted',
                     interrupted.get('reason') == 'unknown_outcome:interrupted' and stranded_record.get('state') == 'failed'
                     and stranded_record.get('failed_step') == 'init' and stranded_record.get('reason') == 'unknown_outcome:interrupted'),
                    ('at the step it names, running no step again', [h['step'] for h in stranded_record['history']]
                     == ['settled', 'directory', 'init', 'init'] and len(hub['calls']) == calls
                     and not (projects_root['personal'] / 'stranded').exists()),
                    ('a live run of the same repository is refused, touching nothing',
                     in_progress.get('reason') == 'stale_subject:provisioning_in_progress' and unchanged),
                    ('once it is gone the decision runs, and stops by name',
                     after_lock.get('reason') == 'directory_not_empty'
                     and (record(locked['repository']) or {}).get('failed_step') == 'directory')])

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

            # The owner's progress reports (VELDO-0128), through the reporter's one rendered send, as suite 93 runs it.
            TRP = load('v143_report', mods / 'control_telegram_report.py')
            report_gate = SimpleNamespace(conn=conn, channel='telegram_chat')
            report_edge = SimpleNamespace(activation=report_gate, send=presenter.edge.send)
            reporter = TRP.Reporter(SimpleNamespace(conn=conn, inbox=inbox, gate=report_gate, presenter=SimpleNamespace(
                conn=conn, P=f['P'], edge=report_edge, current=presenter.current)), owner=OWNER)

            def reported():
                """Each project_ready report not sent yet, sent now: [(entity, outcome, text)]."""
                out = []
                for fact in reporter.sources(since=0):
                    if fact['event'] == 'project_ready':
                        done = reporter.report(fact)
                        if done.get('outcome') != 'already_reported':
                            out.append((fact['source']['entity_id'], done.get('outcome'), fact['headline']))
                return out

            with region('activation/applied'):
                taken = service.take_on()
                before_messages = bot_messages()
                passed = service.new_project_pass()
                ready = reported()
                tide_project = PJ.read(S, conn, 'tidepool') or {}
                tide_team = (entity('team:tidepool') or {}).get('data') or {}
                tide_objective = OB.read(conn, OB.objective_id(pid1 + ':project')) or {}
                told = bot_messages()[len(before_messages):]
                tide_message = first.get('message_id')
                check('activation/applied', [
                    ('an instance takes on, at its start, the created repository no service was running to be handed',
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
                    ('he is told "tidepool is ready; the first objective is next" in his chat, by its report',
                     (tide_decision, 'sent', 'tidepool is ready; the first objective is next.') in ready
                     and any(c == chat and 'Veldo: tidepool is ready; the first objective is next.' in t
                             for c, _m, _r, t in told) and tide_message is not None),
                    ('the decisions are activated, and the pass itself sends him nothing',
                     len(told) == len([r for r in ready if r[1] == 'sent'])
                     and (PP.read(conn, tide_decision) or {}).get('state') == 'activated'
                     and any(e.get('operation') == 'activate' and e.get('outcome') == 'activated' for e in passed))])

            with region('activation/failed-activates-nothing'):
                failed_records = [PP.read(conn, done['record'].get('request')) or {} for done in failures.values()]
                check('activation/failed-activates-nothing', [
                    ('every decision whose repository failed is failed with its reason, and its report tells him',
                     all(r.get('state') == 'failed' and r.get('reason') for r in failed_records)
                     and any(e == failures['push']['record'].get('request') and outcome == 'sent'
                             and headline == 'refusedpush could not be set up.' for e, outcome, headline in ready)
                     and not any('refusedpush is ready' in t for _c, _m, _r, t in bot_messages())),
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

            def judged(svc):
                """control_client.send's shape, judged by control_client's Authority over `svc` as the socket's
                serving side judges it (VELDO-0161's suite does the same), with no socket."""
                authority = SV.CC.Authority(ids['store_uuid'], DOMAIN, str(f['db']), SV.E, svc.verify, HOST, svc.apply,
                                            watermark=svc.watermark, minimum_generation=1, context=True)

                def send_to(workspace, packet, enrollment, verify, sign, host_identity, timeout=30.0):
                    enrollment.resolve_store(workspace, verify, host_identity)
                    binding = enrollment.read_binding(workspace)
                    return authority.judge(SV.CC.build_request(workspace, binding, packet, sign), os.getuid())
                return send_to

            with region('activation/name-taken'):
                # A name is one project (VELDO-0143 F3), after activation: an existing project's name is refused
                # before he is asked, and an activation that finds the name taken meanwhile fails by name.
                calls_t = len(hub['calls'])
                again_msg = send('api_request', 'start a new personal project called tidepool')
                pid_t, _ = routed(again_msg)
                again_t = decisions.propose(pid_t, document(pid_t, 'tidepool', 'personal'), dispatch='pm-np-again')
                calls_after_t = len(hub['calls'])
                decision_m, _, _ = own_decision('mussel')
                mussel_repo = PP.read(conn, decision_m)['proposal']['repository']
                with fenced(wire):
                    mussel = provision(decision_m, send=judged(service))
                body_m = dict(ids, operation='activate', project='mussel', principal=OWNER, command_id=next_id('pm-m'),
                              nonce=next_id('pm-mn'), owner=OWNER, charter={'purpose': 'Another way in.'},
                              execution_repository=mussel_repo, authority_policy={'team_amendment': ['project_owner']},
                              coordination_budget={'capacity': 4, 'invocations': 400, 'wall_seconds': 604800})
                other = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda d, r: False).apply(
                    {'command': body_m, 'signature': sign_as(OWNER, S.canonical_bytes(body_m))})
                mussel_pass = service.new_project_pass()
                mussel_again = service.new_project_pass()
                told_m = reported()
                check('activation/name-taken', [
                    ('a new project named like an existing project is refused before he is asked [%s]' % again_t.get('reason'),
                     again_t.get('reason') == 'stale_subject:project_exists'
                     and (PP.read(conn, PP.decision_id(pid_t)) or {}).get('state') == 'failed'
                     and calls_after_t == calls_t),
                    ('a project of that name activated meanwhile fails the decision by name, once [%s, %s]'
                     % (mussel.get('state'), other.get('ok')),
                     mussel.get('state') == 'active' and other.get('ok') is True
                     and (PP.read(conn, decision_m) or {}).get('state') == 'failed'
                     and (PP.read(conn, decision_m) or {}).get('reason') == 'already_exists'
                     and any(e.get('decision') == decision_m and e.get('outcome') == 'failed' for e in mussel_pass)
                     and not any(e.get('decision') == decision_m for e in mussel_again)),
                    ('its report tells him it could not be set up, and why',
                     (decision_m, 'sent', 'mussel could not be set up.') in told_m
                     and (PP.decision_id(pid_t), 'sent', 'tidepool could not be set up.') in told_m
                     and any('already_exists' in t for _c, _m, _r, t in bot_messages()))])

            with region('proposal/no-provisioner'):
                # Nothing is asked that cannot be carried out (VELDO-0143 F6): an installation with no provisioner
                # configuration neither presents nor settles a proposal, and he is told why.
                bare = PP.NewProjects(S, CM, conn, ids, 'authority', journal_sign, inbox=inbox, settlement=settlement,
                                      presenter=presenter, assignment=I, requester='pm',
                                      request_sign=lambda b: sign_as('pm', b), templates=str(ROOT / 'engine'),
                                      provisioner=lambda: None)
                requests_p, calls_p = new_project_requests(), len(hub['calls'])
                named_p = send('api_request', 'start a new personal project called eddy')
                pid_p1, _ = routed(named_p)
                unnamed_p = send('api_request', 'start a new project called riffle')
                pid_p2, _ = routed(unnamed_p)
                eddy = bare.propose(pid_p1, document(pid_p1, 'eddy', 'personal'), dispatch='pm-np-eddy')
                riffle = bare.propose(pid_p2, document(pid_p2, 'riffle', None), dispatch='pm-np-riffle')
                told_p = reported()
                check('proposal/no-provisioner', [
                    ('neither the message that named both nor the one that asked settles or presents [%s, %s]'
                     % (eddy.get('reason'), riffle.get('reason')),
                     all(o.get('ok') is False and o.get('reason') == 'unavailable_service:provisioner' for o in (eddy, riffle))
                     and all((PP.read(conn, PP.decision_id(p)) or {}).get('state') == 'failed' for p in (pid_p1, pid_p2))
                     and new_project_requests() == requests_p),
                    ('nothing is built or created', len(hub['calls']) == calls_p
                     and not (projects_root['personal'] / 'eddy').exists()),
                    ('he is told each could not be set up, naming why',
                     (PP.decision_id(pid_p1), 'sent', 'eddy could not be set up.') in told_p
                     and (PP.decision_id(pid_p2), 'sent', 'riffle could not be set up.') in told_p
                     and any('eddy could not be set up' in t and 'unavailable_service:provisioner' in t
                             for _c, _m, _r, t in bot_messages())),
                    ('a decision settled where the running service has no configuration is failed by name, not left waiting',
                     (PP.read(conn, PP.decision_id(pid6)) or {}).get('state') == 'failed'
                     and (PP.read(conn, PP.decision_id(pid6)) or {}).get('reason') == 'unavailable_service:provisioner')])

            with region('proposal/correction-told'):
                # VELDO-0143 rounds 6 and 7: a correction refused because it would have set the identity or the
                # visibility tells him so in plain words: only a choice he picks sets them.
                reported()
                texts_r = [text for _c, _m, _r, text in bot_messages()]
                told_r = {field: [text for text in texts_r if '%s could not be set up' % name in text]
                          for field, name in (('identity', 'rockbass'), ('visibility', 'kelpcrab'))}
                if not all(len(v) == 1 for v in told_r.values()):
                    print('  %sdetail: correction told: %s' % (PREFIX, told_r))
                plain_r = {'identity': 'Your correction would have set the identity',
                           'visibility': 'Your correction would have set the visibility'}
                check('proposal/correction-told', [
                    ('the refused %s correction is told once, in plain words, with how to answer' % field,
                     len(told_r[field]) == 1 and plain_r[field] in told_r[field][0]
                     and 'change only by the choice you pick' in told_r[field][0]
                     and 'pick the choice that names the identity and visibility you want' in told_r[field][0])
                    for field in ('identity', 'visibility')])

            with region('proposal/identities-fold-alike'):
                # VELDO-0143 round 8 (R7-3): an identity is picked by typing its id, which the presentation module
                # folds, so ids that fold alike are not a configuration, in one call or added later.
                def configured_as(*names_):
                    try:
                        GI.validate([identity(n, 'olga-p', n, 'nokey') for n in names_])
                        return None
                    except GI.Refused as error:
                        return error.code
                folds = {pair: configured_as(*pair) for pair in (('work', 'Work'), ('my-org', 'my_org'), ('a.b', 'A.B'))}
                distinct = configured_as('work', 'works', 'my-org', 'my.org')
                try:
                    GI.configure_identities(conn, DOMAIN, [identity('Bcengi', 'bcengi', 'Bcengi', 'bcengi')], {})
                    added = None
                except GI.Refused as error:
                    added = error.code
                check('proposal/identities-fold-alike', [
                    ('%s and %s are refused invalid_input:ambiguous_git_identity [%s]' % (pair + (code,)),
                     code == 'invalid_input:ambiguous_git_identity') for pair, code in folds.items()] + [
                    ('ids that differ after the fold are a configuration [%s]' % distinct, distinct is None),
                    ('an id added later that folds like a configured one is refused, and nothing is added [%s]' % added,
                     added == 'invalid_input:ambiguous_git_identity'
                     and 'Bcengi' not in {r['id'] for r in GI.records(conn, DOMAIN)})])

            with region('proposal/not-presentable'):
                # VELDO-0143 round 8 (R7-3): a configuration made before ids were refused so (written here as it was
                # stored) makes two picks fold alike, so the presenter refuses ambiguous_choice. The decision fails by
                # that name, its request is canceled, and his report tells him, never presented to no one.
                legacy = identity('Bcengi', 'bcengi', 'Bcengi', 'bcengi')
                conn.execute('INSERT INTO git_identities VALUES (?,?,?)', (DOMAIN, 'Bcengi', json.dumps(legacy, sort_keys=True)))
                try:
                    msg_r = send('api_request', 'start a new project called riptide')
                    pid_r, _ = routed(msg_r)
                    before_r = bot_messages()
                    made_r = decisions.propose(pid_r, document(pid_r, 'riptide', None), dispatch=next_id('pm-np'))
                    sent_r = bot_messages()[len(before_r):]
                finally:
                    conn.execute('DELETE FROM git_identities WHERE domain=? AND identity=?', (DOMAIN, 'Bcengi'))
                held_r = PP.read(conn, made_r.get('decision')) or {}
                alias_r = (held_r.get('presentation') or {}).get('alias')
                request_r = ((entity(I.assignment_id(ids['repository_uuid'], alias_r)) if alias_r else None) or {}).get(
                    'data', {})
                reported()
                told_q = [text for _c, _m, _r, text in bot_messages() if 'riptide could not be set up' in text]
                check('proposal/not-presentable', [
                    ('the decision fails invalid_input:ambiguous_choice, not presented [%s %s]'
                     % (made_r.get('reason'), held_r.get('state')),
                     made_r.get('ok') is False and made_r.get('reason') == 'invalid_input:ambiguous_choice'
                     and held_r.get('state') == 'failed' and held_r.get('reason') == 'invalid_input:ambiguous_choice'),
                    ('nothing was presented and its request is canceled [%s]' % request_r.get('state'),
                     sent_r == [] and request_r.get('state') == 'CANCELED'),
                    ('his report tells him why, and what to do', len(told_q) == 1
                     and 'two of its choices would be typed alike' in told_q[0]
                     and 'Give each Git identity an id that differs' in told_q[0])])

            with region('proposal/presentation-interrupted'):
                # Presented once, even across a crash (VELDO-0143 F4): the decision is recorded before anything is
                # presented, and the running service's next pass finishes the presentation from the record.
                refused_msg = send('api_request', 'start a new project called kelp')
                pid_k1, _ = routed(refused_msg)
                crashed_msg = send('api_request', 'start a new project called wrack')
                pid_k2, _ = routed(crashed_msg)
                real_write, real_present = decisions.write, presenter.present

                def refusing_write(decision, state, **fields):
                    if state == 'presented':
                        raise S.StoreRefused('stale_version', 'injected: the store refuses the decision write')
                    return real_write(decision, state, **fields)

                def crashing_present(request):
                    raise RuntimeError('injected: the service is killed while presenting')
                before_k = bot_messages()
                decisions.write = refusing_write
                try:
                    kelp = decisions.propose(pid_k1, document(pid_k1, 'kelp', 'personal'), dispatch='pm-np-kelp')
                finally:
                    decisions.write = real_write
                kelp_sent = bot_messages()[len(before_k):]
                presenter.present = crashing_present
                try:
                    decisions.propose(pid_k2, document(pid_k2, 'wrack', 'personal'), dispatch='pm-np-wrack')
                    crashed = None
                except RuntimeError as error:
                    crashed = str(error)
                finally:
                    presenter.present = real_present
                interrupted_k = [(PP.read(conn, PP.decision_id(p)) or {}) for p in (pid_k1, pid_k2)]
                wrack_unsent = bot_messages()[len(before_k) + len(kelp_sent):]
                # VELDO-0143 round 9 (R8-2): a request the presenter refuses for good, the service killed just after
                # its cancel (tombolo) or just before it (groyne). The decision is failed before the cancel, so no
                # resume writes it presented over a canceled request, and the next pass cancels what was left open.
                legacy_k = identity('Bcengi', 'bcengi', 'Bcengi', 'bcengi')
                conn.execute('INSERT INTO git_identities VALUES (?,?,?)',
                             (DOMAIN, 'Bcengi', json.dumps(legacy_k, sort_keys=True)))
                real_apply, stops = inbox.apply, {}
                try:
                    for name, when in (('tombolo', 'after'), ('groyne', 'before')):
                        pid_s, _ = routed(send('api_request', 'start a new project called %s' % name))

                        def stopping_apply(packet, when=when):
                            if (packet.get('command') or {}).get('operation') == 'cancel':
                                if when == 'after':
                                    real_apply(packet)
                                raise RuntimeError('injected: the service is killed at the cancel')
                            return real_apply(packet)
                        inbox.apply = stopping_apply
                        try:
                            decisions.propose(pid_s, document(pid_s, name, None), dispatch='pm-np-' + name)
                            stopped = None
                        except RuntimeError as error:
                            stopped = str(error)
                        finally:
                            inbox.apply = real_apply
                        stops[name] = (pid_s, stopped)
                finally:
                    conn.execute('DELETE FROM git_identities WHERE domain=? AND identity=?', (DOMAIN, 'Bcengi'))

                def stop_state(pid_s):
                    held = PP.read(conn, PP.decision_id(pid_s)) or {}
                    alias = (held.get('presentation') or {}).get('alias')
                    request = (entity(I.assignment_id(ids['repository_uuid'], alias)) if alias else None) or {}
                    return held.get('state'), held.get('reason'), request.get('data', {}).get('state')
                stopped_k = {name: stop_state(pid_s) for name, (pid_s, _) in stops.items()}
                resumed = service.new_project_pass()
                stopped_after = {name: stop_state(pid_s) for name, (pid_s, _) in stops.items()}
                after_k = [(PP.read(conn, PP.decision_id(p)) or {}) for p in (pid_k1, pid_k2)]
                again_k = service.new_project_pass()
                sent_k = bot_messages()[len(before_k):]
                check('proposal/presentation-interrupted', [
                    ('a store refusal or a crash after the decision is recorded leaves it presenting, with its proposal [%s]'
                     % kelp.get('reason'),
                     kelp.get('ok') is False and crashed is not None
                     and [r.get('state') for r in interrupted_k] == ['presenting', 'presenting']
                     and all(r.get('presented', {}).get('project') in ('kelp', 'wrack') for r in interrupted_k)
                     and pid_k1 not in {p['proposal_id'] for p in PP.pending(conn)}),
                    ('the next pass presents each from its record, the same request, and it is presented',
                     [r.get('state') for r in after_k] == ['presented', 'presented']
                     and after_k[0].get('presented') == interrupted_k[0].get('presented')
                     and after_k[1].get('presented') == interrupted_k[1].get('presented')
                     and all(r.get('request') for r in after_k)
                     and sum(1 for e in resumed if e.get('operation') == 'resume' and e.get('outcome') == 'presented') == 2),
                    ('each question reaches him once: never twice, and the crashed one once it is resumed [%d, %d, %d]'
                     % (len(kelp_sent), len(wrack_unsent), len(sent_k)),
                     len(kelp_sent) == 1 and wrack_unsent == [] and len(sent_k) == 2
                     and not any(e.get('operation') == 'resume' for e in again_k)),
                    ('his answer to it is read: the decision settles',
                     answer(after_k[0]['request'], 'accept', 'yes').get('outcome') in ('accepted', 'settled')
                     and decisions.apply_settled() != []
                     and (PP.read(conn, PP.decision_id(pid_k1)) or {}).get('state') == 'settled'),
                    ('a request the presenter refuses for good, the service killed after its cancel: the decision is '
                     'already failed, and after the next pass it is still failed by name, never presented [%s %s]'
                     % (stopped_k.get('tombolo'), stopped_after.get('tombolo')),
                     all(stopped for _pid, stopped in stops.values())
                     and stopped_k.get('tombolo') == ('failed', 'invalid_input:ambiguous_choice', 'CANCELED')
                     and stopped_after.get('tombolo') == ('failed', 'invalid_input:ambiguous_choice', 'CANCELED')),
                    ('killed before its cancel: the decision is failed, and the next pass cancels the request left '
                     'open [%s %s]' % (stopped_k.get('groyne'), stopped_after.get('groyne')),
                     stopped_k.get('groyne', ())[:2] == ('failed', 'invalid_input:ambiguous_choice')
                     and stopped_k.get('groyne', ())[2] != 'CANCELED'
                     and stopped_after.get('groyne') == ('failed', 'invalid_input:ambiguous_choice', 'CANCELED')
                     and any(e.get('operation') == 'resume' and e.get('outcome') == 'canceled'
                             and e.get('decision') == PP.decision_id(stops['groyne'][0]) for e in resumed))])

            with region('provision/handed-over'):
                # VELDO-0161 TAKING IT ON, for a created repository: the provisioner hands its record to the running
                # service, which judges it again and answers synchronously; the answer is the record active.
                decision_e, _, _ = own_decision('inlet')
                inlet_repo = PP.read(conn, decision_e)['proposal']['repository']
                service.projects_due = False
                with fenced(wire):
                    inlet = provision(decision_e, send=judged(service))
                inlet_record = record(inlet_repo) or {}
                due = service.projects_due
                inlet_pass = service.new_project_pass()
                check('provision/handed-over', [
                    ('the provisioner\'s answer is the running service\'s: active, no refusal',
                     inlet.get('state') == 'active' and inlet.get('reason') is None and inlet.get('ok') is True),
                    ('the record was written active by that instance before the provisioner returned',
                     inlet_record.get('state') == 'active'
                     and (inlet_record.get('taken_on') or {}).get('instance_id') == service.instance['instance_id']
                     and [h['step'] for h in inlet_record.get('history') or []][-2:] == ['enrolled', 'take_on']),
                    ('the instance serves it from then on', inlet_repo in service.repositories),
                    ('the take-on it answered makes the new-project pass due, which activates the project',
                     due is True and (PJ.read(S, conn, 'inlet') or {}).get('state') == 'ACTIVE'
                     and any(e.get('operation') == 'activate' and e.get('decision') == decision_e
                             and e.get('outcome') == 'activated' for e in inlet_pass))])

            class AgentWatch:
                """provision/signing-no-agent's own SSH agent, outside the fence's (as VELDO-0161's
                adoption/signer-no-agent has one). While active, SSH_AUTH_SOCK and SSH_AGENT_PID name it and a
                stand-in ssh-keygen first on PATH records each invocation's agent variables, then runs the real one.
                Where local sockets may be made the agent is a recording socket (every connection is kept, with the
                process that made it); where they may not, it is a path where nothing listens or can, and the
                stand-in's record is the evidence. A signer that reaches for an agent fails the row by name."""

                def __init__(self):
                    import socket
                    import struct
                    self.socket, self.struct = socket, struct
                    self.shim = base / 'agent-shim'
                    self.shim.mkdir()
                    self.log = self.shim / 'invocations.jsonl'
                    self.log.write_text('')
                    real = shutil.which('ssh-keygen')
                    (self.shim / 'ssh-keygen').write_text(
                        '#!%s\nimport json, os, sys\n'
                        'def after(flag):\n'
                        '    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv[:-1] else None\n'
                        'with open(%r, "a") as f:\n'
                        '    f.write(json.dumps({"agent": [os.environ.get(k) for k in ("SSH_AUTH_SOCK", "SSH_AGENT_PID")'
                        ' if os.environ.get(k)], "argv": sys.argv[1:3], "key": after("-f"), "namespace": after("-n")})'
                        ' + "\\n")\n'
                        'os.execv(%r, [%r] + sys.argv[1:])\n' % (sys.executable, str(self.log), real, real))
                    (self.shim / 'ssh-keygen').chmod(0o700)
                    self.connections, self.stop = [], threading.Event()
                    self.directory = self.agent = self.thread = None
                    if UNIX:
                        # A short path (sun_path is bounded), as the fence's own agent has.
                        self.directory = tempfile.mkdtemp(prefix='v143a-')
                        self.path = os.path.join(self.directory, 'agent')
                        self.agent = socket.socket(socket.AF_UNIX)
                        self.agent.bind(self.path)
                        self.agent.listen(8)
                        self.thread = threading.Thread(target=self._serve, daemon=True)
                        self.thread.start()
                    else:
                        self.path = str(self.shim / 'agent.sock')

                def _serve(self):
                    while not self.stop.is_set():
                        try:
                            peer, _ = self.agent.accept()
                        except OSError:
                            return
                        if not self.stop.is_set():
                            try:
                                pid = self.struct.unpack('3i', peer.getsockopt(self.socket.SOL_SOCKET,
                                                                               self.socket.SO_PEERCRED, 12))[0]
                                asked = Path('/proc/%d/cmdline' % pid).read_bytes().replace(b'\0', b' ').decode(
                                    errors='replace').strip()[:300]
                            except OSError:
                                asked = 'unknown process'
                            self.connections.append(asked)
                        peer.close()

                @contextlib.contextmanager
                def active(self):
                    saved = {k: os.environ.get(k) for k in ('PATH', 'SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
                    os.environ.update(PATH=str(self.shim) + os.pathsep + (saved['PATH'] or os.defpath),
                                      SSH_AUTH_SOCK=self.path, SSH_AGENT_PID='1')
                    try:
                        yield self
                    finally:
                        for k, v in saved.items():
                            if v is None:
                                os.environ.pop(k, None)
                            else:
                                os.environ[k] = v

                def invocations(self):
                    return [json.loads(line) for line in self.log.read_text().splitlines() if line.strip()]

                def close(self):
                    if self.agent is None:
                        return
                    self.stop.set()
                    with contextlib.suppress(OSError):
                        waker = self.socket.socket(self.socket.AF_UNIX)
                        waker.connect(self.path)
                        waker.close()
                    self.agent.close()
                    self.thread.join(timeout=5)
                    with contextlib.suppress(OSError):
                        os.unlink(self.path)
                        os.rmdir(self.directory)
                    self.agent = None

            with region('provision/signing-no-agent'):
                # Every signature a new project's whole path makes, with an SSH agent named in the environment: his
                # message by the API edge, its intake, route and proposal journaled, the provisioner's journal and
                # adoption signatures, the running service's take-on and its new-project pass (the activation, the
                # first team and objective, journaled by the service and through the channel's inbox). None may
                # reach an agent: every ssh-keygen runs with SSH_AUTH_SOCK and SSH_AGENT_PID removed.
                watch = AgentWatch()
                try:
                    with watch.active():
                        decision_c, _, _ = own_decision('cove')
                    cove_repo = PP.read(conn, decision_c)['proposal']['repository']
                    with fenced(wire):
                        with watch.active():
                            cove = provision(decision_c, send=judged(service))
                            cove_pass = service.new_project_pass()
                finally:
                    watch.close()
                asked = watch.invocations()
                signing = [a for a in asked if a['argv'] == ['-Y', 'sign']]
                signed = {(Path(a['key'] or '').name, a['namespace']) for a in signing}
                check('provision/signing-no-agent', [
                    ('the new project ran its whole path there: created, handed over, active and activated',
                     cove.get('ok') is True and (record(cove_repo) or {}).get('state') == 'active'
                     and (PJ.read(S, conn, 'cove') or {}).get('state') == 'ACTIVE'
                     and any(e.get('decision') == decision_c and e.get('outcome') == 'activated' for e in cove_pass)),
                    ('each signer ran ssh-keygen -Y sign there: the API edge, the authority\'s journal and the adoption '
                     'signer %s' % sorted(signed),
                     {('api-edge', 'veldo-command'), (Path(str(f['keyfile']['authority'])).name, 'veldo-journal'),
                      (adoption_key.name, 'veldo-enrollment')} <= signed),
                    # A signature is what reaches for an agent; `-Y verify` (authority_contract's verifier) never does.
                    ('no ssh-keygen -Y sign was started with an SSH agent in its environment, though one was named %s'
                     % sorted({(Path(a['key'] or '').name, a['namespace']) for a in signing if a['agent']}),
                     bool(signing) and all(a['agent'] == [] for a in signing)),
                    ('nothing connected to this row\'s agent %s' % watch.connections[:3], watch.connections == [])])

            with region('service/provisions', 'service/hand-off'):
                provisioner = state_root / 'host' / 'provisioner.json'
                provisioner.write_text(json.dumps(effect_config))
                provisioner.chmod(0o600)
                decision_s, pid_s, _ = own_decision('lagoon')
                lagoon_repo = PP.read(conn, decision_s)['proposal']['repository']
                service.config['provisioner'] = str(provisioner)
                listener = authority = None
                if UNIX:
                    # The service's socket, beside the store, served by this loop as serve() serves it.
                    listener = SV.CC.bind(SV.CC.socket_path_for({'store_path': str(f['db'])}))
                    authority = SV.CC.Authority(ids['store_uuid'], DOMAIN, str(f['db']), SV.E, service.verify, HOST,
                                                service.apply, watermark=service.watermark, minimum_generation=1,
                                                context=True)
                passes, served, takes = [], 0, []
                try:
                    with fenced(wire):
                        started = service.new_project_pass()
                        one = service.projects_pass.running.get(decision_s)
                        # The serve loop's own shape: the socket and the provisioner's pipe, waited on; a pass only
                        # when an event made it due. Nothing is taken on by reading the records.
                        deadline = time.monotonic() + 120
                        while one is not None and not one.done and time.monotonic() < deadline:
                            pipes = service.provisioner_pipes()
                            ready = select.select(([listener] if listener is not None else []) + sorted(pipes), [], [],
                                                  5)[0]
                            if listener is not None and listener in ready:
                                SV.CC.serve_one(listener, authority)
                                served += 1
                            for fd in ready:
                                if fd in pipes:
                                    service.provisioner_readable(fd)
                            if service.projects_due:
                                passes += service.new_project_pass()
                        ended_state = (record(lagoon_repo) or {}).get('state')
                        active_before_start = (PJ.read(S, conn, 'lagoon') or {}).get('state') == 'ACTIVE'
                        if not UNIX:
                            # No socket could be made, so no running service could be handed the record: an
                            # instance takes it on at its start (VELDO-0161), and the pass that follows activates.
                            takes = service.take_on()
                            passes += service.new_project_pass()
                finally:
                    if listener is not None:
                        listener.close()
                # VELDO-0143 round 7 (the host's surviving newproject143-provisioner-end-unseen): on the socket branch
                # the take-on answered there made the pass due before the provisioner ended, so lagoon cannot show
                # that its end alone does. A second provisioner whose take-on is withheld (nothing serves the socket;
                # here, and where no socket can be made at all) ends with its record waiting, and only its end on the
                # output pipe can make the pass that names its answer due.
                with contextlib.suppress(OSError):
                    os.unlink(SV.CC.socket_path_for({'store_path': str(f['db'])}))
                decision_w, _pid_w, _ = own_decision('atoll')
                withheld = []
                with fenced(wire):
                    withheld_started = service.new_project_pass()
                    two = service.projects_pass.running.get(decision_w)
                    deadline = time.monotonic() + 120
                    while two is not None and not two.done and time.monotonic() < deadline:
                        pipes = service.provisioner_pipes()
                        for fd in select.select(sorted(pipes), [], [], 5)[0]:
                            service.provisioner_readable(fd)
                        if service.projects_due:
                            withheld += service.new_project_pass()
                ended_withheld = [e for e in withheld if e.get('operation') == 'provision'
                                  and e.get('decision') == decision_w and e.get('outcome') == 'ended']
                atoll_waiting = (record(PP.read(conn, decision_w)['proposal']['repository']) or {}).get('state')
                # The next instance takes it on at its start, as VELDO-0161 has it, and the pass activates it.
                service.take_on()
                service.new_project_pass()
                lagoon = PJ.read(S, conn, 'lagoon') or {}
                ended = [e for e in passes if e.get('operation') == 'provision' and e.get('decision') == decision_s
                         and e.get('outcome') == 'ended']
                if lagoon.get('state') != 'ACTIVE' or one is None or not one.done:
                    print('  %sdetail: service pass %s, provisioner %s' % (
                        PREFIX, json.dumps(started + passes, default=str)[:1500],
                        None if one is None else (one.process.returncode, one.output[-300:])))
                check('service/provisions', [
                    ('the running service starts the registered provisioner for a settled decision, as its own process',
                     any(e.get('operation') == 'provision' and e.get('outcome') == 'started' and e.get('decision') == decision_s
                         for e in started) and one is not None and one.done),
                    ('its end is seen on its output pipe, and the pass it makes due names its answer',
                     ended != [] if not UNIX else (ended != [] or active_before_start)),
                    ('a provisioner whose take-on is withheld: its end alone makes the pass due, which names its answer '
                     '[%s, %s]' % (atoll_waiting, [e.get('refusal') for e in ended_withheld]),
                     any(e.get('operation') == 'provision' and e.get('outcome') == 'started'
                         and e.get('decision') == decision_w for e in withheld_started)
                     and two is not None and two.done and atoll_waiting == 'provisioning'
                     and len(ended_withheld) == 1
                     and ended_withheld[0].get('refusal') == 'not_taken_on:authority_unavailable'),
                    ('a service with no provisioner configuration named finds the one setup lays in the state root',
                     SP.NewProjectPass(SimpleNamespace(config={'store_path': str(state_root / 'authority' / 'control.sqlite3')}),
                                       {}).provisioner_path() == str(state_root / 'host' / 'provisioner.json')),
                    ('with no socket the record waits, named, until an instance takes it on at its start'
                     if not UNIX else 'the record is handed over its socket',
                     (ended_state == 'provisioning' and ended != []
                      and ended[0].get('refusal') == 'not_taken_on:authority_unavailable'
                      and any(t.get('repository_uuid') == lagoon_repo and t.get('outcome') == 'accepted' for t in takes))
                     if not UNIX else served >= 1),
                    ('the repository is created, taken on and the project activated',
                     lagoon.get('state') == 'ACTIVE' and (PP.read(conn, decision_s) or {}).get('state') == 'activated')])
                if not UNIX:
                    check('service/hand-off', [('AF_UNIX sockets are refused on this host, so no provisioner can reach '
                                                'a running service over its socket', False)])
                else:
                    check('service/hand-off', [
                        ('the provisioner\'s take-on request is answered over the socket, synchronously',
                         served >= 1 and one.process.returncode == 0 and one.reason() is None),
                        ('the record is active, naming this instance, before the provisioner ended',
                         ended_state == 'active' and ((record(lagoon_repo) or {}).get('taken_on') or {}).get(
                             'instance_id') == service.instance['instance_id']),
                        ('the take-on it answered made the pass due: the project is active with no instance started',
                         active_before_start and takes == [])])

            with region('service/pm-settled-due'):
                # A decision the factory PM's run settles, applied in a factory loop pass, makes the new-project pass
                # due with no other event (VELDO-0143 F1): his own message, and his correction.
                PMd = load('v143_pm_due', mods / 'control_workflow_cycle_pm.py')
                applier = SimpleNamespace(services={'new_projects': service.new_projects()}, save=lambda r: r)

                def pm_applies(subject, value, dispatch):
                    """The factory loop's apply of the factory PM's run (ProjectCycles.apply), as its pass runs it."""
                    service.projects_due = False
                    cycle_record = {'new_project_subject': subject, 'dispatch': dispatch, 'cycle': dispatch,
                                    'project': 'factory'}
                    try:
                        PMd.ProjectCycles.apply(applier, cycle_record, value)
                    except PMd.Refused as error:
                        return error.code, service.projects_due
                    return cycle_record.get('state'), service.projects_due

                def serve_step():
                    """The serve loop's own check after the factory loop's pass: a pass only when one is due."""
                    return service.new_project_pass() if service.projects_due else []
                # The provisioners run inside the identity wire's fence, as service/provisions runs them.
                with fenced(wire):
                    brook_msg = send('api_request', 'start a new personal project called brook')
                    pid_b1, _ = routed(brook_msg)
                    brook_applied = pm_applies({'proposal_id': pid_b1, 'decision': None, 'correction': None},
                                               document(pid_b1, 'brook', 'personal'), 'pm-cycle-brook')
                    brook_step = serve_step()
                    rill_msg = send('api_request', 'start a new project called rill')
                    pid_b2, _ = routed(rill_msg)
                    rill_presented = pm_applies({'proposal_id': pid_b2, 'decision': None, 'correction': None},
                                                document(pid_b2, 'rill', 'personal'), 'pm-cycle-rill')
                    serve_step()
                    rill_decision = PP.decision_id(pid_b2)
                    answer((PP.read(conn, rill_decision) or {}).get('request'), 'return_for_elaboration', 'call it rill-two')
                    service.new_project_pass()
                    rill_applied = pm_applies({'proposal_id': pid_b2, 'decision': rill_decision, 'correction': None},
                                              document(pid_b2, 'rill-two', 'personal'), 'pm-cycle-rill-two')
                    rill_step = serve_step()
                    started_due = {e.get('decision') for e in brook_step + rill_step
                                   if e.get('operation') == 'provision' and e.get('outcome') == 'started'}
                    # Each provisioner runs to its end; an instance then takes the repositories on and the pass activates.
                    runs = [service.projects_pass.running.get(d) for d in (PP.decision_id(pid_b1), rill_decision)]
                    deadline = time.monotonic() + 120
                    while any(one is not None and not one.done for one in runs) and time.monotonic() < deadline:
                        pipes = service.provisioner_pipes()
                        for fd in select.select(sorted(pipes), [], [], 5)[0]:
                            service.provisioner_readable(fd)
                        serve_step()
                takes_due = service.take_on()
                activated_due = service.new_project_pass()
                if (PJ.read(S, conn, 'brook') or {}).get('state') != 'ACTIVE':
                    print('  %sdetail: pm-settled-due %s %s %s' % (PREFIX, [None if o is None else (o.done, o.reason())
                                                                          for o in runs],
                                                                 json.dumps(takes_due, default=str)[:600],
                                                                 json.dumps(activated_due, default=str)[:900]))
                check('service/pm-settled-due', [
                    ('his own message, settled by the factory PM\'s run in a loop pass, makes the pass due [%s]'
                     % (brook_applied,), brook_applied == ('proposed', True)
                     and (PP.read(conn, PP.decision_id(pid_b1)) or {}).get('path') == 'own_message'),
                    ('his correction, settled by the PM\'s run in a loop pass, makes the pass due [%s, %s]'
                     % (rill_presented, rill_applied), rill_presented[0] == 'proposed' and rill_applied == ('proposed', True)
                     and (PP.read(conn, rill_decision) or {}).get('path') == 'correction'),
                    ('with no other event the serve loop\'s pass starts the provisioner for each [%s]' % sorted(started_due),
                     started_due == {PP.decision_id(pid_b1), rill_decision}),
                    ('each repository is created and its project activated',
                     all(one is not None and one.done for one in runs)
                     and (PJ.read(S, conn, 'brook') or {}).get('state') == 'ACTIVE'
                     and (PJ.read(S, conn, 'rill-two') or {}).get('state') == 'ACTIVE')])

            # The service connection's registrations before any line's project cycles are built on it (the next row
            # is the first to build them): a restarted service's connection, for the R3-1 rows.
            cycles_free = dict(conn.command_registry)
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
    event = complete_event(event)
    with Path(sys.argv[2]).with_suffix('.events.jsonl').open('a') as stream:
        stream.write(json.dumps(event) + '\\n')
    print(json.dumps(event), flush=True)
if '--input-format' in sys.argv:
    opening = json.loads(sys.stdin.readline())
    assert opening['type'] == 'control_request'
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
                                             observations=str(base / 'pm-service.jsonl'),
                                             provisioner=str(provisioner_file)), conn)
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
                # Every identity configured when the PM runs is offered: the three above and the one bind_paths
                # configured for the factory source.
                offered_ids = sorted(r['id'] for r in GI.records(conn, DOMAIN))
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
                     and [i['id'] for i in payload.get('identities') or []] == offered_ids
                     and {'bcengi', 'nokey', 'personal'} <= set(offered_ids)),
                    ('the run\'s final document becomes the one proposal, presented once',
                     cycle.get('state') == 'proposed' and estuary_record.get('state') == 'presented'
                     and estuary_record.get('dispatch') == cycle.get('dispatch')
                     and (estuary_record.get('presented') or {}).get('objective') == 'The river trail map')])
            with region('activation/line-from-pass'):
                # VELDO-0143 F5: once the pass activates a new project with the factory loop attached, the loop
                # gains the repository's line from that pass. The first unit dispatched on that line is VELDO-0188
                # AC1's observation (owner, Telegram 36156); this row's former first-unit part is kept, unchanged,
                # in proof/VELDO-0143/round4/first-unit-for-0188.py.
                fjord_dir = projects_root['personal'] / 'fjord'
                # The factory loop runs as the scheduling service's principal (reservation_service), as the pm row's.
                unit_service = SV.Service(dict(service.config, principal='team-service',
                                               repositories={REPO: [str(base / 'workspace')]},
                                               observations=str(base / 'unit-service.jsonl'),
                                               receiver={'configs': {REPO: str(receiver_config)}}), conn)
                unit_service.channel = service.channel
                unit_loop = SV.FactoryLoop(unit_service, work)
                decision_u1, _, _ = own_decision('fjord')
                fjord_repo = PP.read(conn, decision_u1)['proposal']['repository']
                saved_loop, service.loop = service.loop, unit_loop
                try:
                    with fenced(wire):
                        fjord = provision(decision_u1, send=judged(service))
                    fjord_pass = service.new_project_pass()
                finally:
                    service.loop = saved_loop
                tline = unit_loop.lines.get(fjord_repo)
                check('activation/line-from-pass', [
                    ('the pass that activates the new project, with the factory loop attached, gives the loop its line',
                     fjord.get('state') == 'active' and (PJ.read(S, conn, 'fjord') or {}).get('state') == 'ACTIVE'
                     and any(e.get('decision') == decision_u1 and e.get('outcome') == 'activated'
                             and e.get('line') == fjord_repo for e in fjord_pass)),
                    ('that line works in the new repository, through its own receiver configuration, with the roles of '
                     'the loop\'s first line',
                     tline is not None and tline.workspace == os.path.realpath(str(fjord_dir))
                     and tline.gate.repository_uuid == fjord_repo and tline.roles == work['repositories'][REPO])])
            with region('activation/factory-line-kept', 'activation/factory-intake-current',
                        'activation/factory-line-restart'):
                # VELDO-0143 R3-1: the line the pass adds for a new project leaves the factory's own line whole. Until
                # VELDO-0188 runs several lines' project cycles on the service's one connection, the new line's cannot
                # be built there; that build registers nothing, is not tried again on every pass, and never takes the
                # connection's owners from the factory line, whatever the repository uuids' order (the loop visits
                # lines sorted by uuid), before or after a restart. A service started on this store: its connection
                # holds none of the cycles' owners.
                AL = load('v143_alias', mods / 'control_alias.py')
                CB = load('v143_backlog', mods / 'control_backlog.py')
                conn.command_registry.clear()
                conn.command_registry.update(cycles_free)
                # The factory line works in the factory's checkout, through the pm row's receiver configuration.
                kept_service = SV.Service(dict(service.config, principal='team-service',
                                               repositories={REPO: [str(source)]},
                                               observations=str(base / 'kept-service.jsonl'),
                                               receiver={'configs': {REPO: str(pm_receiver)}}), conn)
                kept_service.channel = service.channel
                kept_loop = SV.FactoryLoop(kept_service, work)
                kept_loop.wake('journal')
                first_pass = kept_loop.run() or {}
                factory = kept_loop.lines[REPO]
                before_cycles = getattr(factory, 'pm_cycles', None)
                decision_k, pid_k, _ = own_decision('kestrel')
                oid_k = OB.objective_id(pid_k + ':project')
                kestrel_repo = PP.read(conn, decision_k)['proposal']['repository']
                saved_loop, service.loop = service.loop, kept_loop
                try:
                    with fenced(wire):
                        kestrel = provision(decision_k, send=judged(service))
                    kestrel_pass = service.new_project_pass()
                finally:
                    service.loop = saved_loop
                passes = []
                for _ in range(2):
                    kept_loop.wake('journal')
                    passes.append(kept_loop.run() or {})
                kline = kept_loop.lines.get(kestrel_repo)
                registry = conn.command_registry

                def bound(operation):
                    entry = registry.get(operation) or {}
                    return getattr(entry.get('transaction_transition'), '__self__', None)

                def held_by(cycles):
                    return (cycles is not None and bound(CB.OPERATION) is cycles.services['backlog']
                            and bound('team_operation') is cycles.services['teams']
                            and bound('accept_snapshot') is cycles.readsets)

                def take(cycles, name):
                    # The PM proposes a feature in the factory's repository under the new project's accepted objective
                    # (VELDO-0077: a RAW feature of that repository), and the factory line's backlog takes it.
                    objectives = OB.Objectives(S, CM, conn, ids, 'authority', journal_sign)
                    current = OB.read(conn, oid_k) or {}
                    body = dict(ids, operation='propose_feature', principal='pm', command_id=next_id('r31-feature'),
                                nonce=next_id('r31-feature-n'), objective=oid_k, objective_version=current.get('version'),
                                feature=name, title='The ' + name + ' feature', scope=['kestrel'])
                    proposed = objectives.apply({'command': body, 'signature': sign_as('pm', S.canonical_bytes(body))})
                    if not proposed.get('ok'):
                        return dict(proposed, reason='feature:' + str(proposed.get('reason')))
                    body = dict(ids, operation='take', principal='pm', command_id=next_id('r31-take'),
                                nonce=next_id('r31-take-n'), feature=proposed.get('feature_id'),
                                work_class='PRODUCT_CHANGE')
                    try:
                        return cycles.services['backlog'].apply({'command': body,
                                                                 'signature': sign_as('pm', S.canonical_bytes(body))})
                    except Exception as error:  # noqa: BLE001 - another line's transition raises its own Refused
                        return {'ok': False, 'reason': getattr(error, 'code', type(error).__name__)}
                taken = take(factory.pm_cycles, 'kept') if getattr(factory, 'pm_cycles', None) else {}
                kept_faults = [fault for one in passes for fault in one.get('faults') or []
                               if fault.get('repository') == kestrel_repo]
                if not taken.get('ok') or len(kept_faults) != 1:
                    print('  %sdetail: factory line kept: take %s; new line faults %s; factory faults %s' % (
                        PREFIX, taken.get('reason'), kept_faults,
                        [x for one in [first_pass] + passes for x in one.get('faults') or [] if x.get('repository') == REPO]))
                check('activation/factory-line-kept', [
                    ('the factory line built its project cycles at the first pass, before any project was added',
                     before_cycles is not None and not any(x in cycles_free for x in AL.OPERATIONS)),
                    ('the pass activates the new project with the factory loop attached and the loop gains its line, '
                     'whose repository uuid sorts before the factory\'s', kestrel.get('state') == 'active'
                     and any(e.get('decision') == decision_k and e.get('outcome') == 'activated'
                             and e.get('line') == kestrel_repo for e in kestrel_pass)
                     and kline is not None and kestrel_repo < REPO),
                    ('after two loop passes the factory line keeps the same cycles and the registry\'s backlog, team and '
                     'snapshot transitions are its own', factory.pm_cycles is before_cycles and held_by(before_cycles)),
                    ('the factory line\'s backlog take of a RAW feature of its own repository is accepted, the item in '
                     'that repository', taken.get('ok') is True
                     and (taken.get('item') or {}).get('repository_uuid') == REPO),
                    ('the new line\'s cycles were refused once, by name, and not tried again on the second pass',
                     getattr(kline, 'pm_cycles', None) is None and getattr(kline, 'pm_refusal', None)
                     == 'invalid_registration' and len(kept_faults) == 1
                     and kept_faults[0]['reason'] == 'pm_cycles:invalid_registration')])
                # VELDO-0143 R4-3: after those passes the factory line's intake knows the new project. A message naming
                # it is recorded with it as a candidate, and the factory PM's route to it is accepted.
                fintake = (getattr(factory, 'pm_cycles', None) and factory.pm_cycles.services.get('intake'))
                current_body = dict(schema=IN.API_SCHEMA, domain=DOMAIN, request_id=next_id('message'), edge='api-edge',
                                    principal=OWNER, text='add a tide table page to kestrel', project=None,
                                    clarifies=None)
                current = fintake.receive('api_request', dict(
                    request=current_body, signature=sign_as('api-edge', S.canonical_bytes(current_body))))
                current_held = fintake.proposal(current.get('proposal_id')) or {}
                current_route = fintake.route(dict(schema=IN.RT.SCHEMA, proposal_id=current.get('proposal_id'),
                                                   route='existing_project', project='kestrel',
                                                   reason='The owner names kestrel.'),
                                              dispatch=next_id('pm-route'), proposal_id=current.get('proposal_id'))
                current_resolved = fintake.proposal(current_route.get('proposal_id')) or {}
                if not current_route.get('ok'):
                    print('  %sdetail: factory intake after the activation: %s; candidates %s; route %s' % (
                        PREFIX, current.get('outcome'), (current_held.get('context') or {}).get('candidates'),
                        current_route.get('reason') or current_route.get('refusal')))
                check('activation/factory-intake-current', [
                    ('the registry\'s intake record and route are the factory line\'s intake',
                     fintake is not None and bound(IN.RECORD) is fintake and bound(IN.RT.ROUTE) is fintake),
                    ('a message naming the new project is recorded with it as a candidate, and hinted',
                     current.get('outcome') == 'inbox'
                     and 'kestrel' in (current_held.get('context') or {}).get('candidates', [])
                     and 'kestrel' in (current_held.get('hints') or [])),
                    ('the factory PM\'s route to it is accepted, the request now the new project\'s',
                     current_route.get('ok') is True and current_resolved.get('project') == 'kestrel')])
                # A restart: a new service and loop on this store, where every repository it took on (the new one among
                # them, its uuid sorting first) has its line from the loop's constructor.
                conn.command_registry.clear()
                conn.command_registry.update(cycles_free)
                configs = dict(service.config['receiver']['configs'], **{REPO: str(pm_receiver)})
                restarted_service = SV.Service(dict(service.config, principal='team-service',
                                                    repositories=dict(service.repositories, **{REPO: [str(source)]}),
                                                    observations=str(base / 'restarted-service.jsonl'),
                                                    receiver={'configs': configs}), conn)
                restarted_service.channel = service.channel
                restarted = SV.FactoryLoop(restarted_service, work)
                order = sorted(restarted.lines)
                restart_passes = []
                for _ in range(2):
                    restarted.wake('journal')
                    restart_passes.append(restarted.run() or {})
                rfactory = restarted.lines[REPO]
                rcycles = getattr(rfactory, 'pm_cycles', None)
                rtaken = take(rcycles, 'restarted') if rcycles is not None else {}
                others = [line for repository, line in restarted.lines.items() if repository != REPO]
                rfaults = [x for one in restart_passes for x in one.get('faults') or []]
                if rcycles is None or not rtaken.get('ok'):
                    print('  %sdetail: factory line restart: order %s; take %s; faults %s' % (
                        PREFIX, order, rtaken.get('reason'), rfaults))
                check('activation/factory-line-restart', [
                    ('the restarted loop has the new repository\'s line, visited before the factory line',
                     kestrel_repo in restarted.lines and order.index(kestrel_repo) < order.index(REPO)
                     and restarted.factory_line == REPO),
                    ('the factory project\'s cycles run on the factory line at both passes, its owners on the connection',
                     rcycles is not None and all('pm_cycles' in one for one in restart_passes)
                     and not any(x.get('repository') == REPO for x in rfaults) and held_by(rcycles)),
                    ('its backlog take on its own repository is accepted', rtaken.get('ok') is True
                     and (rtaken.get('item') or {}).get('repository_uuid') == REPO),
                    ('no other line holds cycles, and each was refused at most once',
                     others and all(getattr(line, 'pm_cycles', None) is None for line in others)
                     and all(sum(1 for x in rfaults if x.get('repository') == line.repository
                                 and x.get('reason') != DEFERRED) <= 1 for line in others)),
                    ('a line visited before the factory line built its cycles named its deferral in that pass (R5-3)',
                     any(x == {'repository': kestrel_repo, 'reason': DEFERRED} for x in restart_passes[0].get('faults') or []))])

            with region('activation/factory-paused-resumed'):
                # VELDO-0143 R4-5: the factory project paused when the service starts, a taken-on repository's project
                # active. No other line takes the connection's owners while the factory line has no cycles, so once the
                # owner resumes the factory project its cycles run on the factory line.
                conn.command_registry.clear()
                conn.command_registry.update(cycles_free)
                owner_projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda d, r: False)

                def factory_change(op, **extra):
                    version = conn.execute("SELECT version FROM entities WHERE id='project:factory'").fetchone()[0]
                    body = dict(ids, operation=op, project='factory', principal=OWNER, command_id=next_id('r45-' + op),
                                nonce=next_id('r45-n'), project_version=version, **extra)
                    return owner_projects.apply({'command': body, 'signature': sign_as(OWNER, S.canonical_bytes(body))})
                paused_f = factory_change('pause', reason='the owner pauses the factory')
                # Every repository this store took on has its line from the loop's constructor, as at a restart.
                paused_configs = dict(service.config['receiver']['configs'], **{REPO: str(pm_receiver)})
                paused_service = SV.Service(dict(service.config, principal='team-service',
                                                 repositories=dict(service.repositories, **{REPO: [str(source)]}),
                                                 observations=str(base / 'paused-service.jsonl'),
                                                 receiver={'configs': paused_configs}), conn)
                paused_service.channel = service.channel
                paused_loop = SV.FactoryLoop(paused_service, work)
                paused_passes = []
                for _ in range(2):
                    paused_loop.wake('journal')
                    paused_passes.append(paused_loop.run() or {})
                held_while_paused = {repository: getattr(line, 'pm_cycles', None) is not None
                                     for repository, line in paused_loop.lines.items()}
                resumed_f = factory_change('resume')
                resumed_passes = []
                for _ in range(2):
                    paused_loop.wake('journal')
                    resumed_passes.append(paused_loop.run() or {})
                pfactory = paused_loop.lines[REPO]
                pcycles = getattr(pfactory, 'pm_cycles', None)
                ptaken = take(pcycles, 'resumed') if pcycles is not None else {}
                pothers = [line for repository, line in paused_loop.lines.items() if repository != REPO]
                pfaults = [x for one in paused_passes + resumed_passes for x in one.get('faults') or []]
                if pcycles is None or not ptaken.get('ok'):
                    print('  %sdetail: factory paused then resumed: pause %s, resume %s; held while paused %s; take %s; '
                          'faults %s' % (PREFIX, paused_f.get('reason'), resumed_f.get('reason'), held_while_paused,
                                         ptaken.get('reason'), pfaults))
                check('activation/factory-paused-resumed', [
                    ('the factory project was paused when the service started, with an active project on a line visited '
                     'before the factory line', paused_f.get('ok') is True and kestrel_repo in paused_loop.lines
                     and sorted(paused_loop.lines).index(kestrel_repo) < sorted(paused_loop.lines).index(REPO)
                     and (PJ.read(S, conn, 'kestrel') or {}).get('state') == 'ACTIVE'),
                    ('while it was paused no line built project cycles', not any(held_while_paused.values())),
                    ('each pass while it was paused names the new line\'s deferral to the factory line (R5-3)',
                     all({'repository': kestrel_repo, 'reason': DEFERRED} in (one.get('faults') or [])
                         for one in paused_passes)),
                    ('once he resumed it, its cycles run on the factory line with its owners on the connection',
                     resumed_f.get('ok') is True and pcycles is not None and all('pm_cycles' in one for one in resumed_passes)
                     and not any(x.get('repository') == REPO for x in pfaults) and held_by(pcycles)),
                    ('its backlog take on its own repository is accepted', ptaken.get('ok') is True
                     and (ptaken.get('item') or {}).get('repository_uuid') == REPO),
                    ('no other line holds cycles', pothers and all(getattr(line, 'pm_cycles', None) is None
                                                                  for line in pothers))])

            with region('activation/new-projects-kept'):
                # VELDO-0143 R4-6: a factory line build that fails leaves the service's new-project decisions
                # registered. A service whose new-project decisions are not yet built, on a connection that holds no
                # registration of them; its factory line's first build fails at grooming (its presenter seen on
                # another connection, once); the next pass builds it.
                registry_free = {k: v for k, v in cycles_free.items() if k != PP.OPERATION}
                conn.command_registry.clear()
                conn.command_registry.update(registry_free)

                class OnceElsewhere:
                    """The channel's presenter, seen on another connection while `elsewhere` holds."""
                    def __init__(self, real):
                        self.real, self.elsewhere = real, True

                    def __getattr__(self, name):
                        if name == 'conn' and self.elsewhere:
                            return None
                        return getattr(self.real, name)

                class Forward:
                    def __init__(self, real, **over):
                        self.real, self.over = real, over

                    def __getattr__(self, name):
                        return self.over[name] if name in self.over else getattr(self.real, name)
                once = OnceElsewhere(service.channel.ingress.presenter)
                np_service = SV.Service(dict(service.config, principal='team-service',
                                             repositories={REPO: [str(source)]},
                                             observations=str(base / 'np-service.jsonl'),
                                             receiver={'configs': {REPO: str(pm_receiver)}}), conn)
                np_service.channel = Forward(service.channel, ingress=Forward(service.channel.ingress, presenter=once))
                np_loop = SV.FactoryLoop(np_service, work)
                np_loop.wake('journal')
                np_first = np_loop.run() or {}
                np_built_first = getattr(np_loop.lines[REPO], 'pm_cycles', None)
                once.elsewhere = False
                np_loop.wake('journal')
                np_second = np_loop.run() or {}
                np_cycles = getattr(np_loop.lines[REPO], 'pm_cycles', None)
                np_decisions = np_service.new_projects()
                np_entry = conn.command_registry.get(PP.OPERATION) or {}
                if not np_entry:
                    print('  %sdetail: new-project decisions after a failed build: registered %s; first faults %s' % (
                        PREFIX, PP.OPERATION in conn.command_registry, np_first.get('faults')))
                check('activation/new-projects-kept', [
                    ('the factory line\'s first build failed and the next pass built it',
                     np_built_first is None and any(x.get('repository') == REPO for x in np_first.get('faults') or [])
                     and np_cycles is not None),
                    ('the service\'s new-project decisions, the ones the factory line\'s cycles hold, have their '
                     'operation registered on the connection', np_decisions is not None
                     and np_cycles.services.get('new_projects') is np_decisions
                     and np_entry.get('writes') == PP.WRITES and callable(np_entry.get('transition')))])

            with region('activation/factory-canceled'):
                # VELDO-0143 R5-3: a canceled factory project runs no cycles again, so another line does not wait on
                # the factory line for it: the active project's line builds its cycles, and nothing is deferred.
                conn.command_registry.clear()
                conn.command_registry.update(cycles_free)
                canceled_f = factory_change('cancel', reason='the owner closes the factory project',
                                            disposition='nothing left open')
                canceled_service = SV.Service(dict(service.config, principal='team-service',
                                                   repositories=dict(service.repositories, **{REPO: [str(source)]}),
                                                   observations=str(base / 'canceled-service.jsonl'),
                                                   receiver={'configs': paused_configs}), conn)
                canceled_service.channel = service.channel
                canceled_loop = SV.FactoryLoop(canceled_service, work)
                canceled_passes = []
                for _ in range(2):
                    canceled_loop.wake('journal')
                    canceled_passes.append(canceled_loop.run() or {})
                # The store holds several active projects by now, each on its line; the first line the loop visits
                # that wants cycles builds them (one set per connection until VELDO-0188), the others are refused.
                built_c = [(repository, line) for repository, line in sorted(canceled_loop.lines.items())
                           if getattr(line, 'pm_cycles', None) is not None]
                first_c = next((repository for repository, line in sorted(canceled_loop.lines.items())
                                if line.wants_cycles()), None)
                cfaults = [x for one in canceled_passes for x in one.get('faults') or []]
                if len(built_c) != 1:
                    print('  %sdetail: factory canceled: cancel %s; built %s; faults %s' % (
                        PREFIX, canceled_f.get('reason'), [r for r, _ in built_c], cfaults))
                check('activation/factory-canceled', [
                    ('the factory project is canceled and kestrel\'s project is active on its own line',
                     canceled_f.get('ok') is True and (PJ.read(S, conn, 'factory') or {}).get('state') == 'CANCELED'
                     and (PJ.read(S, conn, 'kestrel') or {}).get('state') == 'ACTIVE'
                     and kestrel_repo in canceled_loop.lines),
                    ('the factory line builds no cycles', getattr(canceled_loop.lines[REPO], 'pm_cycles', None) is None),
                    ('the first line visited that wants cycles, another active project\'s, builds them at the first pass, '
                     'its owners on the connection', first_c not in (None, REPO) and len(built_c) == 1
                     and built_c[0][0] == first_c and 'pm_cycles' in canceled_passes[0] and held_by(built_c[0][1].pm_cycles)),
                    ('no pass defers a line to the factory line', not any(x.get('reason') == DEFERRED for x in cfaults))])

            with region('pm/graph-stage-own'):
                # The seam's outcome, not its frame match: the PM exchanges above (pm/new-project-run's, and those of
                # the cycles the factory passes built in Line.build_cycles) resolved the account stage, and the
                # fixture's own stage holds the PM runner staged there (content-addressed: one file for them all).
                staged_pm = f['stage_seam'].pm_runners(f['graph_stage'], mods)
                check('pm/graph-stage-own', [
                    ('the PM exchanges staged their runner in the fixture\'s own graph stage [%d PM runner(s) in %s]'
                     % (staged_pm, f['graph_stage']), staged_pm >= 1)])

        finally:
            # Compare the events the PM fixture actually emitted, then drive that same generated
            # executable through the shared capture observer before its directory is removed.
            problems, printed = [], set()
            event_file = base / 'pm-packet.events.jsonl'
            if event_file.is_file():
                for raw in event_file.read_text().splitlines():
                    event = json.loads(raw)
                    name = conform_formats.event_name(event)
                    schema = formats['claude_code']['events'].get(name)
                    problems += conform_formats.conform(event, schema, name) if schema else [name + ':table:no-event']
                    printed.add(name)
            check('format/fake-lines', [('the PM run emitted conforming assistant and result events [%s; %s]'
                  % (sorted(printed), problems[:4]),
                  not problems and {'assistant', 'result/success'} <= printed)])

            def fake_engine(engine):
                return fake.read_text() if engine == 'claude' else ''

            def readback_args(engine, directory):
                result = directory / 'result.json'
                result.write_text(result_file.read_text())
                return [str(result), str(directory / 'packet.json')]

            L = load('v143_format_launch', mods / 'control_launch.py')
            fake_capture = conform_formats.conform_fake(locals(), '0143_new_project')
            for description in conform_formats.describe('0143_new_project', *fake_capture):
                print(description)
            expect('VELDO-0172 fake/capture:0143_new_project', bool(fake_capture[1]) and not fake_capture[0])
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])


_v143_started = __import__('time').monotonic()
__import__('runpy').run_path(str(ROOT / 'proof/VELDO-0143/check_compiled_sources.py'))['suite_rows'](expect)
_v143_suite()
print('VELDO-0143 suite seconds: %.3f' % (__import__('time').monotonic() - _v143_started))
