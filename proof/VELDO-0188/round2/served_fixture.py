"""Provisioning fixture extracted from suite 110's setup, without its unrelated scenarios.
Real signed intake and settlement, provisioner, Git repositories and adoption signer.
Only GitHub and credential storage are local protocol stand-ins, fenced by identity_wire.
"""
import contextlib

@contextlib.contextmanager
def fixture(ROOT, PRODUCTION, install_modules=None):
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

    PREFIX = 'VELDO-0188 served '
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    helper = load('v143_fixture', ROOT / 'proof/VELDO-0152/fixture.py')
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
    with helper.fixture(ROOT, PRODUCTION, cycle_budget=100, compiled_sources=True, install_modules=install_modules) as f:
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
            FS = load('v143_setup', ROOT / '.veldo/control_factory_setup.py')
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
            projects_root = {name: base / ('projects-' + name) for name in ('personal',)}
            for path in projects_root.values():
                path.mkdir()
            TOKENS = {'personal': '-'.join(('personal', 'token', os.urandom(12).hex()))}
            LOGIN_OWNERS = {TOKENS['personal']: 'olga-p'}

            def identity(name, owner, label, token_name, default_visibility='private'):
                reference = 'keychain:%s/api' % token_name
                return dict(id=name, label=label, author_name='Olga ' + label, author_email='%s@example.invalid' % name,
                            remote_host='github.com', remote_owner=owner, api_token=reference,
                            push_credential=dict(kind='token', reference=reference),
                            projects_root=str(projects_root.get(name) or base / ('projects-' + name)),
                            default_visibility=default_visibility)
            identities = [identity('personal', 'olga-p', 'Personal', 'personal')]
            GI.configure_identities(conn, DOMAIN, identities, {})
            by_id = {r['id']: r for r in identities}
            routes = TR.TeamRoutes(f['service'], settlement, presenter)
            default = routes.save_default(f['team'](), OWNER, 0, next_id('default-team'), 'sha256:' + '1' * 64)
            keys = base / 'protected'
            keys.mkdir(mode=0o700, exist_ok=True)
            adoption_public = (' '.join((keys / 'adoption-signer.pub').read_text().split()[:2])
                               if (keys / 'adoption-signer.pub').exists() else FS.adoption_signer(str(keys)))
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
            wire = W['Wire'](base / 'wire', secrets={'personal/api': TOKENS['personal']})
            hub = {'repos': {}, 'calls': [], 'fault': None, 'reject_push': False, 'orgs': {},
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

            yield locals()
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
