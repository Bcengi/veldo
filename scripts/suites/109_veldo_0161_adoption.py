"""VELDO-0161: a repository the owner names is adopted under one identity on his settled answer and taken on
by the running factory without a restart.

Run: python3 scripts/selftest.py --suite 109_veldo_0161_adoption

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy every module loads, with
the production copies named in PRODUCTION (the copies a registered mutation replaces). Real SQLite store with
OpenSSH command, journal, enrollment, possession and edge signatures; members enrolled by the steward's signed
VELDO-0025 commands; adoption requests recorded as VELDO-0068 terms, opened in the VELDO-0064 inbox, presented
by the VELDO-0065 presenter over a loopback Bot API (no network, no real token) and settled by the owner's
answer through the authenticated API edge. Real Git repositories with local bare remotes reached through
VELDO-0153's identity profile by the hermetic identity wire (scripts/suites/support/identity_wire.py: GitHub
URLs mapped to the bare paths, the fixture identity's credential answered by a stand-in keystore, every
non-local transport refused). The adoption signer's key and the host's enrollment signers are made by
control_factory_setup's own adoption_signer and host_files. The VELDO-0047 authority service is installed by
control_service.install from this .veldo copy and run as the installed unit's ExecStart, a real separate
process serving its real socket; where this host's systemd user manager cannot qualify the worker profile
(the sandbox), installation runs with the containment qualification answered qualified, said so in the
output, since the service under test never launches a worker. The rows after the service's own judge its
parts in this process: control_service.Service over the installed configuration and this store, with
control_client's Authority judging each request as the socket's serving side does, so they run where no local
socket can be made. Every ssh-keygen this suite runs is kept from any SSH agent (the fence's recording agent
names one that reaches it). No private key byte, signature or token is printed or retained.
"""


def _v161_suite():
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
    import signal
    import socket
    import sqlite3
    import struct
    import subprocess
    import sys
    import tempfile
    import threading
    import time

    # Literal anchors: the registered mutation driver substitutes one production copy here.
    PRODUCTION = {
        'control_repository.py': ROOT / ".veldo" / "control_repository.py",
        'control_repository_provisioner.py': ROOT / ".veldo" / "control_repository_provisioner.py",
        'control_effect_executor_adoption.py': ROOT / ".veldo" / "control_effect_executor_adoption.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
    }
    PREFIX = 'VELDO-0161 '
    CHOICES = ('accept', 'return_for_elaboration', 'reject')

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
        with st['lock']:
            bot['next'] += 1
            st['tick'] += 1
            m = {'message_id': bot['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791000000 + st['tick'],
                 'text': text}
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
                return self._answer(200, {'ok': True, 'result': []})
            if method == 'sendMessage':
                chat = st['chats'].get(body.get('chat_id'), {'id': body.get('chat_id'), 'type': 'private'})
                return self._answer(200, {'ok': True, 'result': message(st, bot, bot['user'], chat, body['text'])})
            return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

        def _answer(self, code, value):
            payload = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    W = runpy.run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))

    def unix_sockets():
        """Whether this process may create a local (AF_UNIX) socket: the authority service's socket and the
        identity wire's recording SSH agent are both one. Some confinements refuse it outright."""
        import socket
        try:
            socket.socket(socket.AF_UNIX).close()
            return True
        except OSError:
            return False
    UNIX = unix_sockets()
    NO_SERVICE = 'AF_UNIX sockets are refused on this host, so no authority service can serve here'

    @contextlib.contextmanager
    def fenced(wire):
        """The identity wire's hermetic fence. Where local sockets are refused, the fence's recording SSH agent
        cannot be created; the fence is then raised without it and SSH_AUTH_SOCK names a path where nothing
        listens or can, so no agent is reachable at all (these fixtures push with a token, never over ssh).
        Every other wall (the transport guard, the credential guard, the audit hook) is the wire's own."""
        if UNIX:
            with wire.active():
                yield wire
            return
        print('  %sthe fence runs without its recording agent: %s' % (PREFIX, NO_SERVICE))
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
    watch = put_back = None
    connections, servers, services = [], [], []
    with tempfile.TemporaryDirectory(prefix='v161-', dir=fast_temp()) as directory:
        base = Path(directory)
        mods = base / 'i' / '.veldo'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__', '*.jsonl'))
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        try:
            claims = load('v161_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v161_keys', mods / 'control_keys.py')
            I = load('v161_inbox', mods / 'control_assignment.py')
            P = load('v161_projection', mods / 'control_channel_projection.py')
            V = load('v161_presentation', mods / 'control_channel_presentation.py')
            E = load('v161_edge_enrollment', mods / 'control_channel_enrollment.py')
            ST = load('v161_settlement', mods / 'control_request_settlement.py')
            CE = load('v161_enrollment', mods / 'control_enrollment.py')
            EL = load('v161_eligibility', mods / 'control_eligibility.py')
            CC = load('v161_client', mods / 'control_client.py')
            GP = load('v161_git', mods / 'git_process.py')
            GI = load('v161_identity', mods / 'control_git_identity.py')
            SC = load('v161_scaffold', mods / 'init_scaffold.py')
            contract = load('v161_contract', mods / 'entity_contract.py')
            R = load('v161_repository', mods / 'control_repository.py')
            PR = load('v161_provisioner', mods / 'control_repository_provisioner.py')
            AD = load('v161_adoption', mods / 'control_effect_executor_adoption.py')
            CS = load('v161_service', mods / 'control_service.py')
            FS = load('v161_setup', mods / 'control_factory_setup.py')

            DOMAIN, STORE, HOST = 'domain-161', 'store-161', 'host-161'
            FACTORY = 'repository-161-factory'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=FACTORY, store_uuid=STORE)
            keys, protected, edge_dir, skeys = base / 'k', base / 'p', base / 'e', base / 'sk'
            for d in (keys, protected, edge_dir, skeys):
                d.mkdir(mode=0o700)
            keyfile = {who: keys / who for who in ('authority', 'steward', 'owner', 'pm', 'api-edge', 'settlement')}
            keyfile['edge'] = protected / 'edge-telegram'
            keyfile['edge-auth'] = edge_dir / 'edge-auth'
            public = {}

            def quiet():
                """The environment every ssh-keygen of this suite runs in: never through an agent (the fence's
                recording agent names any process that reaches one)."""
                return {k: v for k, v in os.environ.items() if k not in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID')}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v161-' + who, '-f', str(path)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL, env=quiet())
                public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
            # The adoption signer, generated as factory setup generates it, in the protected key directory.
            adoption_public = FS.adoption_signer(str(skeys)) if hasattr(FS, 'adoption_signer') else None
            adoption_key = skeys / 'adoption-signer'

            def sign_as(who, data, namespace='veldo-command'):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=data,
                                      capture_output=True, check=True, timeout=20, env=quiet()).stdout.decode()

            serial = [0]

            def next_id(prefix):
                serial[0] += 1
                return '%s-%d' % (prefix, serial[0])

            def journal_sign(data):
                return sign_as('authority', data, 'veldo-journal')

            (base / 's').mkdir()
            db = base / 's' / 'control.sqlite3'
            conn = S.open_store(str(db))
            connections.append(conn)
            CM.attach(S)
            K.attach(S)
            repository_dir = base / 'r0'
            repository_dir.mkdir()
            projection = repository_dir / '.veldo' / 'keys' / 'allowed_signers'

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

            admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                                  'roles': ['membership_steward', 'project_owner'],
                                                  'public_key': public['steward'], 'independence_group': 'steward',
                                                  'scope': '*'})
            for who, kind, roles in (('owner', 'person', ['project_owner']), ('pm', 'service', []),
                                     ('api-edge', 'service', [])):
                admin('steward', 'enroll_principal', {'principal': who, 'principal_type': kind, 'roles': roles,
                                                      'public_key': public[who], 'independence_group': who,
                                                      'scope': '*'}, enrollee=who)

            def fixture(eid, kind, data):
                current = S.materialized_state(conn)['entities']
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: current.get(eid, {}).get('version', 0)},
                                            artifact_digests=[], nonce=next_id('fixture-nonce')), 'authority',
                                 journal_sign, 1)

            chat = 5590161
            fixture('channel-enrollment:telegram_chat:owner', 'channel_enrollment',
                    dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='owner', chat_id=chat,
                         revoked_at=None))
            enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
            edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                           'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': '*'}
            edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                            'target': 'channel:telegram_chat', 'parameters': edge_params, 'artifact_digests': [],
                            'expected_versions': {}}
            edge_env = envelope(edge_command, 'steward')
            enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                             sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))

            api = {'tick': 0, 'bots': {}, 'chats': {}, 'lock': threading.Lock()}
            handler = type('V161Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]
            api['bots']['bot161'] = {'user': {'id': 8000000161, 'is_bot': True, 'first_name': 'Veldo',
                                              'username': 'veldo_adoption_bot'},
                                     'next': 9000, 'messages': {}, 'updates': []}
            bot = api['bots']['bot161']
            api['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': 'Owner'}
            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot161'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')

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

            def record(repository):
                found = entity('repository:' + repository)
                return dict(found['data'], version=found['version']) if found else None

            def signature_rows():
                return [json.loads(d) for (d,) in conn.execute("SELECT data FROM entities WHERE kind='adoption_signature'")]

            def open_request(alias, proposal, kind='repository_adoption', ref=None, brief=None):
                """The PM's terms naming the adoption, the inbox request, its framing and its presentation:
                (request id, presented receipt). The brief is the service's rendering of the proposal."""
                if brief is None:
                    brief = R.adoption_brief(proposal)
                target = {'kind': kind, 'ref': ref or 'repository:' + proposal['repository'],
                          'digest': spelled_digest(proposal)}
                body = dict(ids, operation='terms', terms=alias, principal='pm', command_id=next_id('terms'),
                            nonce=next_id('terms-nonce'), touchpoint='decision_disposition', target=target,
                            proposal=proposal, required_roles=[], quorum=None)
                subject = settlement.terms(signed_command('pm', body)).get('subject')
                inbox.apply(signed_command('pm', dict(ids, operation='open', alias=alias, principal='pm',
                                                      command_id=next_id('c'), nonce=next_id('n'), assignment=dict(
                                                          kind='decision', owner='owner', scope=['adoption'],
                                                          deadline='2026-11-01T17:00:00Z', budget={'owner_minutes': 15},
                                                          brief=brief, choices=list(CHOICES), subject=subject))))
                rid = I.assignment_id(FACTORY, alias)
                presenter.frame(signed_command('pm', dict(ids, operation='frame', alias=alias, principal='pm',
                                                          request_version=1,
                                                          risk_statement='Low: an adoption is removed by hand.',
                                                          command_id=next_id('f'), nonce=next_id('fn'))))
                presenter.present(rid)
                return rid, presenter.current(rid) or {}

            def answer(receipt, choice, principal='owner'):
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('api'),
                            principal=principal, request_id=receipt.get('request_id'),
                            request_version=receipt.get('request_version'), presentation_id=receipt.get('presentation_id'),
                            presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice,
                            rationale='adopt it')
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def shown(receipt):
                return '\n'.join((bot['messages'].get((chat, m)) or {}).get('text', '')
                                 for m in receipt.get('message_ids') or [])

            # The one Git identity of these repositories, configured as setup configures it (VELDO-0142).
            GIO = runpy.run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))
            identity = GIO['options']()['git_identities'][0]
            GI.configure_identities(conn, DOMAIN, [identity], {})

            def git(path, *args, check=True):
                done = GP.run(['git', '-C', str(path), *args], capture_output=True, text=True, timeout=60)
                if check and done.returncode:
                    raise RuntimeError('git %s: %s' % (args[0], done.stderr.strip()[:300]))
                return done.stdout.strip()

            def make_repository(label, scaffold=False):
                """A real repository on branch main with one commit (and the scaffold committed when asked),
                and its bare remote holding main."""
                path = base / 'g' / label
                bare = base / 'b' / (label + '.git')
                path.mkdir(parents=True)
                bare.parent.mkdir(exist_ok=True)
                GP.run(['git', 'init', '-q', '-b', 'main', str(path)], check=True, capture_output=True)
                GP.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True, capture_output=True)
                (path / 'README').write_text('%s\n' % label)
                if scaffold:
                    SC.scaffold(str(path), templates=str(ROOT / 'engine'))
                git(path, 'add', '-A')
                GP.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', label], check=True,
                       capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
                git(path, 'push', '-q', str(bare), 'main:main')
                return os.path.realpath(str(path)), str(bare)

            def tip(path, ref='refs/heads/main'):
                done = GP.run(['git', '-C', str(path), 'rev-parse', '--verify', '--quiet', ref], capture_output=True,
                              text=True)
                return done.stdout.strip() if done.returncode == 0 else None

            def refs(path, prefix='refs/veldo/'):
                return git(path, 'for-each-ref', '--format=%(refname)', prefix).splitlines()

            # The host's trust as factory setup writes it: the owner and the adoption signer as enrollment signers.
            state_root = base / 'st'
            state_root.mkdir(mode=0o700)
            trust_file = base / 'ht' / 'host_trust.json'
            plan = {'root': str(state_root), 'owner': 'owner', 'owner_public': public['owner'],
                    'host_trust': str(trust_file), 'host_identity': HOST}
            if hasattr(FS, 'adoption_signer'):
                texts = FS.host_files(plan, public['settlement'], adoption_public)
            else:
                texts = FS.host_files(plan, public['settlement'])
            (state_root / 'host').mkdir(mode=0o700)
            trust_file.parent.mkdir(mode=0o700)
            for path, text in texts.items():
                Path(path).write_text(text)
                os.chmod(path, 0o600)
            trust = EL.load_host_trust(str(trust_file))
            signers_text = Path(trust.enrollment_signers).read_text()

            def binding_verify(message, signature):
                """A binding verifies when its enrolled_by principal signed it under the host's enrollment signers."""
                try:
                    principal = json.loads(message).get('enrolled_by')
                except ValueError:
                    return False
                return AC.ssh_keygen_verify(message, signature, signers_text, principal, 'veldo-enrollment')[0]

            # The factory repository the installed service serves, enrolled by the owner (VELDO-0029).
            factory_path, _ = make_repository('factory')
            CE.enroll(factory_path, DOMAIN, STORE, str(db), HOST, 1,
                      lambda data: sign_as('owner', data, 'veldo-enrollment'), 'owner', time.time(),
                      repository_uuid=FACTORY)
            # A repository enrolled to the same store by the owner that no settlement adopted.
            stray_path, _ = make_repository('stray')
            CE.enroll(stray_path, DOMAIN, STORE, str(db), HOST, 1,
                      lambda data: sign_as('owner', data, 'veldo-enrollment'), 'owner', time.time(),
                      repository_uuid='repository-161-stray')

            # The installed authority service.
            workers = [str(base / 'w')]
            profile = {'kind': 'linux-systemd', 'slice': 'v161.slice', 'lock': str(base / 'workers.lock'),
                       'concurrency': 2, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
                       'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}

            class Fake:
                def run(self, args):
                    return 0, '', ''
            real_qualify = CS.C.qualify
            qualification = real_qualify(profile)
            stand_in = not qualification.get('qualified')
            if stand_in:
                print('  %sthe worker profile does not qualify here (%s): installing with the containment '
                      'qualification answered qualified; the service under test launches no worker'
                      % (PREFIX, qualification.get('refusal')))
                CS.C.qualify = lambda value, environment=None: dict(real_qualify(value, environment), qualified=True,
                                                                    refusal=None, problems=[])
            try:
                installed = CS.install([factory_path], host_trust=str(trust_file), key_directory=str(skeys),
                                       install_root=str(base / 'in'), unit_dir=str(base / 'u'), profile=profile,
                                       writable=workers, runner=Fake())
            finally:
                CS.C.qualify = real_qualify
            config_path = installed['config']
            service_config = json.loads(Path(config_path).read_text())
            home = Path(installed['home'])

            def start_service():
                values = {}
                for line in Path(installed['unit_path']).read_text().splitlines():
                    if line.startswith('ExecStart='):
                        values['argv'] = line[len('ExecStart='):].split()
                env = {k: v for k, v in os.environ.items() if k not in ('NOTIFY_SOCKET',)}
                proc = subprocess.Popen(values['argv'], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.PIPE, env=env)
                services.append(proc)
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline and not os.path.exists(service_config['socket']):
                    if proc.poll() is not None:
                        raise RuntimeError('the service exited: %s' % proc.stderr.read().decode()[-500:])
                    time.sleep(0.05)
                return proc

            def stop_service(proc):
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=30)

            def send(workspace, packet, who='steward'):
                try:
                    return CC.send(str(workspace), packet, CE, binding_verify,
                                   lambda data: sign_as(who, data, AC.SIGNATURE_NAMESPACE), HOST, timeout=20)
                except CC.RoutingRefused as error:
                    return {'accepted': False, 'routing': error.reason}

            def inspect(workspace):
                return send(workspace, {'operation': 'inspect', 'entity_ids': []})

            def note(workspace, repository):
                body = dict(command_id=next_id('note'), principal='steward', operation='upsert_entity',
                            nonce=next_id('note-nonce'), artifact_digests=[],
                            expected_versions={'note:' + repository: 0},
                            parameters=dict(entity_id='note:' + repository, kind='note', data={'from': repository}),
                            domain_uuid=DOMAIN, store_uuid=STORE, repository_uuid=repository)
                return send(workspace, {'command': body, 'signature': sign_as('steward', S.canonical_bytes(body))})

            def result_of(answer):
                return (answer or {}).get('result') or {}

            def wait_state(repository, states=('active', 'failed'), seconds=30):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    current = (record(repository) or {}).get('state')
                    if current in states:
                        return current
                    time.sleep(0.05)
                return (record(repository) or {}).get('state')

            def fixed_state():
                """Everything an installation lays down: the fixed executable, the unit and service.json."""
                found = {}
                for path in sorted((home / 'bin').rglob('*')):
                    if path.is_file():
                        found[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
                found['unit'] = hashlib.sha256(Path(installed['unit_path']).read_bytes()).hexdigest()
                found['service.json'] = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
                return found

            def process_start(pid):
                text = Path('/proc/%d/stat' % pid).read_text()
                return int(text[text.rindex(')') + 2:].split()[19])

            observations = base / 'adoption.jsonl'
            effect_config = {'schema': 'veldo.adoption_effect/v1', 'store': str(db), 'domain_uuid': DOMAIN,
                             'store_uuid': STORE, 'authority_generation': 1, 'host_trust': str(trust_file),
                             'journal': {'principal': 'authority', 'key': installed['journal_key']},
                             'adoption_signer': {'key': str(adoption_key)}, 'templates': str(ROOT / 'engine'),
                             'observations': str(observations)}

            signer_ids = dict(domain_uuid=DOMAIN, store_uuid=STORE, store_path=str(db), host_identity=HOST,
                              authority_generation=1)

            class Signer:
                """The adoption signer, counting every time the effect asks it for a signature."""
                def __init__(self):
                    self.inner = R.AdoptionSigner(str(adoption_key), S, CM, conn, signer_ids,
                                                  ('authority', journal_sign))
                    self.asked = []
                    self.observations = self.inner.observations

                def signer(self, request):
                    def sign(message):
                        self.asked.append(request)
                        return self.inner.sign(message, request)
                    return sign

            def adopt(request, signer=None, send=None, config=None):
                return AD.adopt(config or effect_config, request, signer=signer, send=send)

            def unsent(*args, **kwargs):
                """A stand-in for the take-on request that reaches no service: the record stays provisioning."""
                return {'accepted': False, 'reason': 'not_sent_by_this_row'}

            class AgentWatch:
                """adoption/signer-no-agent's own SSH agent, outside the fence's. While active, SSH_AUTH_SOCK and
                SSH_AGENT_PID name it and a stand-in ssh-keygen first on PATH records each invocation's agent
                variables, then runs the real one. Where local sockets may be made the agent is a recording socket
                (every connection is kept, with the process that made it); where they may not, it is a path where
                nothing listens or can, and the stand-in's record is the evidence. Nothing connecting is the row's
                to judge, so a signer that reaches for an agent fails that row by name rather than the suite."""

                def __init__(self):
                    self.shim = base / 'agent-shim'
                    self.shim.mkdir(exist_ok=True)
                    self.log = self.shim / 'invocations.jsonl'
                    self.log.write_text('')
                    real = shutil.which('ssh-keygen')
                    (self.shim / 'ssh-keygen').write_text(
                        '#!%s\nimport json, os, sys\n'
                        'with open(%r, "a") as f:\n'
                        '    f.write(json.dumps({"agent": [os.environ.get(k) for k in ("SSH_AUTH_SOCK", "SSH_AGENT_PID")'
                        ' if os.environ.get(k)], "argv": sys.argv[1:3]}) + "\\n")\n'
                        'os.execv(%r, [%r] + sys.argv[1:])\n' % (sys.executable, str(self.log), real, real))
                    (self.shim / 'ssh-keygen').chmod(0o700)
                    self.connections, self.signed, self.stop = [], 0, threading.Event()
                    self.directory = self.agent = self.thread = None
                    if UNIX:
                        # A short path (sun_path is bounded), as the fence's own agent has.
                        self.directory = tempfile.mkdtemp(prefix='v161a-')
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
                                pid = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[0]
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

                def watch_signers(self, modules):
                    """Every AdoptionSigner.sign of `modules` (the suite's and the effect's copies) runs active, so
                    no adoption signature anywhere in this suite names the fence's agent to its ssh-keygen; returns
                    the function that puts them back."""
                    restore = []
                    for cls in {id(m.AdoptionSigner): m.AdoptionSigner for m in modules}.values():
                        original = cls.sign

                        def sign(signer, message, request, _original=original):
                            with self.active():
                                self.signed += 1
                                return _original(signer, message, request)
                        cls.sign = sign
                        restore.append((cls, original))

                    def put_back():
                        for cls, original in restore:
                            cls.sign = original
                    return put_back

                def invocations(self):
                    return [json.loads(line) for line in self.log.read_text().splitlines() if line.strip()]

                def close(self):
                    if self.agent is None:
                        return
                    self.stop.set()
                    with contextlib.suppress(OSError):
                        waker = socket.socket(socket.AF_UNIX)
                        waker.connect(self.path)
                        waker.close()
                    self.agent.close()
                    self.thread.join(timeout=5)
                    with contextlib.suppress(OSError):
                        os.unlink(self.path)
                        os.rmdir(self.directory)
                    self.agent = None

            def prepared(label, repository, remote, path):
                proposal, _event = PR.prepare(conn, DOMAIN, path=path, identity='fixture', remote=remote, name=label,
                                              owner='owner', repository=repository, templates=str(ROOT / 'engine'))
                return proposal

            def settle(alias, proposal, choice='accept', **kwargs):
                rid, receipt = open_request(alias, proposal, **kwargs)
                answered = answer(receipt, choice) if choice else None
                return rid, receipt, answered

            wire = W['Wire'](base / 'wire')
            watch = AgentWatch()
            agent_row = [('the signer-scope region reached its agent checks', False)]
            put_back = watch.watch_signers((R, AD.R, PR.R))
            with fenced(wire):
                repos = {}
                for label, scaffold in (('alpha', True), ('beta', False), ('wrong', True), ('scope', False),
                                        ('other', False), ('legacy', False), ('delta', True), ('lease', False),
                                        ('landed', False), ('monitored', False), ('filtered', False),
                                        ('crafted', False), ('unconfigured', True), ('fault', True),
                                        ('tk-answered', True), ('gamma', True), ('tk-store', True),
                                        ('tk-retry-x', True), ('tk-retry-y', True), ('tk-signer', True),
                                        ('tk-signature', True), ('agent', True)):
                    path, bare = make_repository(label, scaffold)
                    remote = wire.remote(label, bare, owner='stranger' if label == 'wrong' else W['OWNER'])
                    # The remote the repository itself is configured with (prepare checks it is the one named).
                    if label != 'unconfigured':
                        git(path, 'remote', 'add', 'origin', remote)
                    repos[label] = {'path': path, 'bare': bare, 'remote': remote, 'uuid': 'repository-161-' + label,
                                    'base': tip(path)}

                # The installed service, running and serving the factory repository, before any adoption.
                proc = start_service() if UNIX else None
                pid = proc.pid if proc else None
                started = process_start(pid) if proc else None
                before_inspect = inspect(factory_path) if proc else {}
                instance = result_of(before_inspect).get('instance') or {}
                fixed_before = fixed_state()
                stray_before = note(stray_path, 'repository-161-stray') if proc else {}
                alive = [proc is not None and proc.poll() is None]

                # AC1: the remote owner, checked before anything is laid and again before anything is pushed.
                with region('adoption/remote-owner-refused'):
                    wrong = repos['wrong']
                    try:
                        prepared('wrong', wrong['uuid'], wrong['remote'], wrong['path'])
                        prepare_refusal = None
                    except PR.Refused as error:
                        prepare_refusal = error.code
                    laid = refs(wrong['path'])
                    proposal = R.adoption_proposal(repository=wrong['uuid'], name='wrong', owner='owner',
                                                   identity='fixture', path=wrong['path'], remote=wrong['remote'],
                                                   default_branch='main', base_commit=wrong['base'], scaffold_commit=None)
                    rid, _receipt, _ = settle('A-wrong', proposal)
                    wrong_result = adopt(rid)
                    wrong_record = record(wrong['uuid']) or {}
                    check('adoption/remote-owner-refused', [
                        ('the repository carries the scaffold and is configured with that remote, so only the owner '
                         'check stands between it and its adoption under another owner',
                         PR.missing_scaffold(wrong['path'], wrong['base']) == []
                         and PR.configured_remote(wrong['path'], 'main') == wrong['remote']),
                        ('the provisioner refuses a remote under another owner before laying anything',
                         prepare_refusal == 'binding_mismatch:remote_owner' and laid == []),
                        ('the settled adoption of it refuses binding_mismatch:remote_owner',
                         wrong_result.get('ok') is False and wrong_result.get('reason') == 'binding_mismatch:remote_owner'),
                        ('its record is failed and names the reason',
                         wrong_record.get('state') == 'failed' and wrong_record.get('reason') == 'binding_mismatch:remote_owner'),
                        ('nothing is signed, enrolled, bound or pushed',
                         CE.read_binding(wrong['path']) is None
                         and not any(s.get('repository') == wrong['uuid'] for s in signature_rows())
                         and S.bound_repository(conn, DOMAIN, wrong['uuid']) is None
                         and tip(wrong['bare']) == wrong['base']),
                        ('its record names no other owner\'s remote as adopted',
                         (wrong_record.get('remote') or {}).get('owner') is None)])

                # AC1: the effect checks the settlement before it asks the adoption signer for anything.
                with region('adoption/settlement-before-signature'):
                    other = repos['other']
                    proposal = prepared('other', other['uuid'], other['remote'], other['path'])
                    unanswered, _r, _ = settle('A-unanswered', proposal, choice=None)
                    rejected, _r, _ = settle('A-rejected', dict(proposal, name='other-rejected'), choice='reject')
                    shown_other, _r, _ = settle('A-brief', dict(proposal, name='other-brief'),
                                                brief='Adopt a repository.')
                    activation, _r, _ = settle('A-activation', dict(proposal, name='other-activation'),
                                               kind='project_activation', ref='project:other')
                    before = journal()
                    cases = {}
                    for case, rid in (('unanswered', unanswered), ('rejected', rejected), ('brief', shown_other),
                                      ('not an adoption', activation)):
                        asked = Signer()
                        cases[case] = (adopt(rid, signer=asked), asked.asked)
                    after = journal()
                    check('adoption/settlement-before-signature', [
                        ('%s refuses no_settled_decision by name' % case,
                         outcome.get('ok') is False and str(outcome.get('reason')).startswith('no_settled_decision:'))
                        for case, (outcome, _asked) in cases.items()] + [
                        ('the adoption signer is never asked', all(asked == [] for _o, asked in cases.values())),
                        ('nothing is written to the store', after == before and record(other['uuid']) is None),
                        ('nothing is enrolled, bound, committed or pushed',
                         CE.read_binding(other['path']) is None and S.bound_repository(conn, DOMAIN, other['uuid']) is None
                         and tip(other['path']) == other['base'] and tip(other['bare']) == other['base']),
                        ('each refusal is distinct', len({o.get('reason') for o, _a in cases.values()}) == 4)])

                # AC1: the adoption signer judges, itself, that a settled decision names the repository it signs.
                with region('adoption/signer-scope'):
                    scope = repos['scope']
                    scope_proposal = prepared('scope', scope['uuid'], scope['remote'], scope['path'])
                    scope_settled, _r, _ = settle('A-scope', scope_proposal)
                    other_rid, _r, _ = settle('A-other-unadopted', dict(proposal, name='other-pending'), choice=None)
                    signer = R.AdoptionSigner(str(adoption_key), S, CM, conn, signer_ids, ('authority', journal_sign))
                    # A signer pinned below the store's own authority generation.
                    behind = R.AdoptionSigner(str(adoption_key), S, CM, conn, dict(signer_ids, authority_generation=0),
                                              ('authority', journal_sign))

                    def binding_bytes(path, repository, enrolled_by='adoption-signer', **fields):
                        return CE.binding_signed_bytes(dict({
                            'schema': CE.BINDING_SCHEMA, 'repository_uuid': repository,
                            'repository_root_commit': CE.root_commits(path), 'clone_uuid': 'clone-' + repository,
                            'domain_uuid': DOMAIN, 'store_uuid': STORE, 'store_path': os.path.realpath(str(db)),
                            'host_identity': HOST, 'authority_generation': 1, 'enrolled_at': 1.0,
                            'enrolled_by': enrolled_by}, **fields))

                    def attempt(data, rid, by=None):
                        try:
                            return ('signed', (by or signer).sign(data, rid))
                        except R.Refused as error:
                            return ('refused', error.code)
                        except Exception as error:  # noqa: BLE001 - anything else is not a named refusal
                            return ('raised', type(error).__name__)
                    before, signed_before = journal(), signature_rows()
                    scoped = {
                        'no settled decision names it': attempt(binding_bytes(other['path'], other['uuid']), other_rid),
                        'the decision names another repository': attempt(binding_bytes(other['path'], other['uuid']),
                                                                        scope_settled),
                        'enrolled by someone else': attempt(binding_bytes(scope['path'], scope['uuid'], 'owner'),
                                                            scope_settled),
                        'not a binding': attempt(S.canonical_bytes({'operation': 'note', 'repository': scope['uuid']}),
                                                 scope_settled),
                        'a request that is no decision': attempt(binding_bytes(scope['path'], scope['uuid']), 'nothing')}
                    # Each coordinate the signer pins, wrong by itself, refused by its own name.
                    pinned = {
                        'another store': ('signature_refused:scope:store', attempt(
                            binding_bytes(scope['path'], scope['uuid'], store_uuid='store-elsewhere'), scope_settled)),
                        'another repository\'s root commits': ('signature_refused:scope:repository_identity', attempt(
                            binding_bytes(scope['path'], scope['uuid'], repository_root_commit=[other['base']]),
                            scope_settled)),
                        'another host': ('signature_refused:scope:host', attempt(
                            binding_bytes(scope['path'], scope['uuid'], host_identity='host-elsewhere'), scope_settled)),
                        'another generation': ('signature_refused:scope:generation', attempt(
                            binding_bytes(scope['path'], scope['uuid'], authority_generation=2), scope_settled)),
                        'a generation below the store\'s': ('signature_refused:scope:generation', attempt(
                            binding_bytes(scope['path'], scope['uuid'], authority_generation=0), scope_settled,
                            by=behind))}
                    after, signed_after = journal(), signature_rows()
                    control = attempt(binding_bytes(scope['path'], scope['uuid']), scope_settled)
                    control_rows = [s for s in signature_rows() if s.get('repository') == scope['uuid']]
                    again = attempt(binding_bytes(scope['path'], scope['uuid']), scope_settled)
                    check('adoption/signer-scope', [
                        ('%s: refused signature_refused by name' % case,
                         outcome[0] == 'refused' and outcome[1].startswith('signature_refused:'))
                        for case, outcome in scoped.items()] + [
                        ('%s: refused %s and nothing else' % (case, code), outcome == ('refused', code))
                        for case, (code, outcome) in pinned.items()] + [
                        ('no refusal signs or journals anything', after == before and signed_after == signed_before),
                        ('control: the binding of the repository its settled decision names is signed',
                         control[0] == 'signed'
                         and binding_verify(binding_bytes(scope['path'], scope['uuid']), control[1])),
                        ('the control signature is journaled with the decision it answered',
                         len(control_rows) == 1 and control_rows[0].get('request') == scope_settled
                         and control_rows[0].get('binding_digest') == 'sha256:' + hashlib.sha256(
                             binding_bytes(scope['path'], scope['uuid'])).hexdigest()),
                        ('a decision is signed for once', again == ('refused', 'signature_refused:already_signed'))])
                    # Every ssh-keygen the signer and the effect run, with an SSH agent named in the environment.
                    agent_repo = repos['agent']
                    agent_rid, _r, _ = settle('A-agent', prepared('agent', agent_repo['uuid'], agent_repo['remote'],
                                                                  agent_repo['path']))
                    with watch.active():
                        derived = R.public_key(str(adoption_key))
                        listed = R.enrolled(signers_text, str(adoption_key))
                        agent_signed = attempt(binding_bytes(agent_repo['path'], agent_repo['uuid']), agent_rid)
                        journal_signed = AD._ssh_signer(installed['journal_key'], 'veldo-journal')(b'v161')
                    asked = watch.invocations()
                    # Judged at the suite's end, with every adoption signature the other rows asked for.
                    agent_row = [
                        ('the signer derives its key, finds its line and signs, the effect signs with the journal key',
                         derived == adoption_public and listed is True and agent_signed[0] == 'signed'
                         and 'SSH SIGNATURE' in journal_signed),
                        ('each ran ssh-keygen', ['-y', '-f'] in [a['argv'] for a in asked]
                         and sum(a['argv'] == ['-Y', 'sign'] for a in asked) >= 2),
                        ('no ssh-keygen was started with an SSH agent in its environment, though one was named',
                         bool(asked) and all(a['agent'] == [] for a in asked))]

                # AC1: a repository carrying the scaffold is adopted with nothing committed; AC2: taken on running.
                with region('adoption/scaffold-present'):
                    alpha = repos['alpha']
                    alpha_proposal = prepared('alpha', alpha['uuid'], alpha['remote'], alpha['path'])
                    alpha_rid, alpha_receipt, _ = settle('A-alpha', alpha_proposal)
                    alpha_result = adopt(alpha_rid)
                    alpha_record = record(alpha['uuid']) or {}
                    check('adoption/scaffold-present', [
                        ('the proposal names no scaffold commit and nothing is laid',
                         alpha_proposal.get('scaffold_commit') is None and refs(alpha['path']) == []),
                        ('the settled adoption is accepted and the record names its signed binding',
                         alpha_result.get('ok') is True and alpha_record.get('state') in ('provisioning', 'active')
                         and alpha_record.get('enrollment') == CE.binding_digest(CE.read_binding(alpha['path']) or {})),
                        ('nothing is committed or pushed',
                         tip(alpha['path']) == alpha['base'] and tip(alpha['bare']) == alpha['base']),
                        ('the record names the identity, remote, decision and no scaffold commit',
                         alpha_record.get('identity') == 'fixture' and alpha_record.get('origin') == 'adopted'
                         and (alpha_record.get('remote') or {}).get('owner') == W['OWNER']
                         and alpha_record.get('request') == alpha_rid and alpha_record.get('scaffold_commit') is None)])

                # AC1: the missing scaffold, one recorded commit the answered proposal names, pushed on his answer.
                with region('adoption/scaffold-commit'):
                    beta = repos['beta']
                    # Hooks of the adopted repository, which no step of the adoption may run.
                    hooked = base / 'hook-ran'
                    for hook in ('post-merge', 'reference-transaction', 'post-checkout', 'pre-push'):
                        target = Path(beta['path']) / '.git' / 'hooks' / hook
                        target.write_text('#!/bin/sh\necho %s >> %s\n' % (hook, hooked))
                        target.chmod(0o700)
                    beta_proposal = prepared('beta', beta['uuid'], beta['remote'], beta['path'])
                    laid_commit = beta_proposal.get('scaffold_commit')
                    laid_ref = tip(beta['path'], 'refs/veldo/adoption/' + beta['uuid'])
                    parents = git(beta['path'], 'rev-list', '--parents', '-n', '1', laid_commit).split()
                    statuses = set(git(beta['path'], 'diff-tree', '--no-commit-id', '-r', '--name-status', beta['base'],
                                       laid_commit).split()[0::2])
                    author = git(beta['path'], 'log', '-1', '--format=%an <%ae>|%cn <%ce>', laid_commit)
                    unmoved = (tip(beta['path']) == beta['base'] and tip(beta['bare']) == beta['base'])
                    beta_rid, beta_receipt, _ = settle('A-beta', beta_proposal)
                    pushes_before = len(wire.invocations())
                    beta_result = adopt(beta_rid)
                    beta_record = record(beta['uuid']) or {}
                    new = git(beta['path'], 'rev-list', '%s..main' % beta['base']).split()
                    pushes = [i for i in wire.invocations()[pushes_before:]
                              if 'push' in i and 'credential.interactive=false' in i and beta['remote'] in i]
                    check('adoption/scaffold-commit', [
                        ('the provisioner laid one commit on the base, adding files only, authored by the identity',
                         isinstance(laid_commit, str) and laid_ref == laid_commit and parents[1:] == [beta['base']]
                         and statuses == {'A'} and author == '%s <%s>|%s <%s>' % (identity['author_name'],
                                                                                   identity['author_email'],
                                                                                   identity['author_name'],
                                                                                   identity['author_email'])),
                        ('the commit is complete scaffold', PR.missing_scaffold(beta['path'], laid_commit) == []),
                        ('before his answer no branch moved and nothing was pushed', unmoved),
                        ('the brief he was shown and answered names that commit',
                         laid_commit in ((entity(beta_rid) or {}).get('data') or {}).get('brief', '')),
                        ('the settled adoption is accepted and the record names its signed binding',
                         beta_result.get('ok') is True and beta_record.get('state') in ('provisioning', 'active')
                         and beta_record.get('enrollment') == CE.binding_digest(CE.read_binding(beta['path']) or {})),
                        ('the branch holds exactly that one commit on the base', new == [laid_commit]),
                        ('the remote holds exactly that commit', tip(beta['bare']) == laid_commit),
                        ('it was pushed through the identity profile', len(pushes) >= 1),
                        ('no hook of the repository ran', not hooked.exists()),
                        ('the ref the commit was recorded under is removed once it was pushed', refs(beta['path']) == []),
                        ('the record names the commit the proposal named',
                         beta_record.get('scaffold_commit') == laid_commit == beta_result.get('scaffold_commit'))])

                with region('adoption/signatures-journaled', 'adoption/signer-enrolled'):
                    rows = {s.get('repository'): s for s in signature_rows()}
                    journaled = []
                    for label in ('alpha', 'beta'):
                        repo = repos[label]
                        binding = CE.read_binding(repo['path']) or {}
                        row = rows.get(repo['uuid']) or {}
                        rec = record(repo['uuid']) or {}
                        journaled.append((label, binding, row, rec))
                    check('adoption/signatures-journaled', [
                        ('%s: its binding is the adoption signer\'s and verifies under this host\'s trust' % label,
                         binding.get('enrolled_by') == 'adoption-signer' and binding.get('repository_uuid') == repos[label]['uuid']
                         and CE.verify_binding(repos[label]['path'], binding,
                                               trust.verifier('adoption-signer', repos[label]['path']), HOST, DOMAIN,
                                               STORE, 1) == [])
                        for label, binding, row, rec in journaled] + [
                        ('%s: the signature is journaled with the decision, the settlement and the binding digest' % label,
                         row.get('request') == rec.get('request') and row.get('settlement') == rec.get('settlement')
                         and row.get('binding_digest') == CE.binding_digest(binding) == rec.get('enrollment'))
                        for label, binding, row, rec in journaled] + [
                        ('every signature the signer made is journaled: the two adoptions, the scope control and the '
                         'no-agent control', sorted(rows) == sorted([repos[label]['uuid'] for label in
                                                                    ('alpha', 'beta', 'scope', 'agent')]))])
                    legacy = repos['legacy']
                    legacy_trust = base / 'ht' / 'legacy_trust.json'
                    legacy_signers = base / 'ht' / 'legacy_signers'
                    legacy_signers.write_text(FS.host_files(plan, public['settlement'])[str(state_root / 'host' / 'enrollment_signers')])
                    legacy_trust.write_text(json.dumps(dict(json.loads(trust_file.read_text()),
                                                            enrollment_signers=str(legacy_signers))))
                    legacy_proposal = prepared('legacy', legacy['uuid'], legacy['remote'], legacy['path'])
                    legacy_rid, _r, _ = settle('A-legacy', legacy_proposal)
                    # A factory set up before the adoption signer existed: no line for it and no key.
                    legacy_result = adopt(legacy_rid, config=dict(
                        effect_config, host_trust=str(legacy_trust),
                        adoption_signer={'key': str(base / 'no-adoption-key' / 'adoption-signer')}))
                    installed_signers = Path(service_config['enrollment_signers']).read_text()
                    check('adoption/signer-enrolled', [
                        ('setup\'s enrollment signers name the adoption signer\'s key for enrollment',
                         adoption_public is not None and R.enrolled(signers_text, str(adoption_key))
                         and 'adoption-signer namespaces="veldo-enrollment" %s' % adoption_public in signers_text),
                        ('the installed service trusts the same signers', installed_signers == signers_text),
                        ('a host whose enrollment signers lack it, and that has no key for it, refuses '
                         'signature_refused:not_enrolled', legacy_proposal.get('scaffold_commit') is not None
                         and legacy_result.get('reason') == 'signature_refused:not_enrolled'
                         and (record(legacy['uuid']) or {}).get('state') == 'failed'
                         and CE.read_binding(legacy['path']) is None),
                        ('it refuses before the branch moves or the scaffold is pushed, and removes the ref it was '
                         'recorded under', tip(legacy['path']) == legacy['base'] and tip(legacy['bare']) == legacy['base']
                         and refs(legacy['path']) == [])])

                # A push the remote refuses, named, with nothing signed or bound.
                with region('adoption/push-refused'):
                    lease = repos['lease']
                    lease_proposal = prepared('lease', lease['uuid'], lease['remote'], lease['path'])
                    lease_rid, _r, _ = settle('A-lease', lease_proposal)
                    elsewhere = base / 'g' / 'elsewhere'
                    git(base / 'g', 'clone', '-q', lease['bare'], str(elsewhere))
                    (elsewhere / 'MOVED').write_text('moved\n')
                    git(elsewhere, 'add', 'MOVED')
                    GP.run(['git', '-C', str(elsewhere), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'moved'],
                           check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
                    git(elsewhere, 'push', '-q', lease['bare'], 'HEAD:main')
                    moved = tip(lease['bare'])
                    lease_result = adopt(lease_rid)
                    lease_record = record(lease['uuid']) or {}
                    check('adoption/push-refused', [
                        ('a push the remote refuses (its branch moved past the base) is push_refused:remote',
                         lease_result.get('ok') is False and lease_result.get('reason') == 'push_refused:remote'),
                        ('its record is failed and names the reason',
                         lease_record.get('state') == 'failed' and lease_record.get('reason') == 'push_refused:remote'),
                        ('the remote keeps the other push and nothing is signed, enrolled or bound',
                         tip(lease['bare']) == moved and CE.read_binding(lease['path']) is None
                         and S.bound_repository(conn, DOMAIN, lease['uuid']) is None
                         and not any(x.get('repository') == lease['uuid'] for x in signature_rows())),
                        ('the ref the refused commit was recorded under is removed', refs(lease['path']) == [])])

                with region('adoption/observed'):
                    events = [json.loads(line) for line in observations.read_text().splitlines()]
                    adopted = {e.get('repository'): e for e in events if e.get('outcome') in ('adopted', 'enrolled')}
                    signed = [e for e in events if e.get('operation') == 'adoption_signature' and e.get('outcome') == 'signed']
                    reasons = {e.get('reason') for e in events if e.get('refusal')}
                    metrics = R.metrics(conn, events)
                    text = observations.read_text() + json.dumps([r[0] for r in conn.execute('SELECT data FROM entities')])
                    beta_event = adopted.get(repos['beta']['uuid']) or {}
                    check('adoption/observed', [
                        ('each adoption names its repository, identity, settled decision, scaffold commit and binding',
                         beta_event.get('identity') == 'fixture' and beta_event.get('request') == beta_rid
                         and beta_event.get('settlement') == (record(repos['beta']['uuid']) or {}).get('settlement')
                         and beta_event.get('scaffold_commit') == laid_commit
                         and beta_event.get('binding_digest') == (record(repos['beta']['uuid']) or {}).get('enrollment')),
                        ('each adoption signature is observed with the decision it answered',
                         {(e.get('repository'), e.get('request')) for e in signed}
                         == {(repos['alpha']['uuid'], alpha_rid), (repos['beta']['uuid'], beta_rid)}),
                        ('refusals are named by class: remote owner, push, no settled decision, signature',
                         {'remote_owner_mismatch', 'push_refused', 'no_settled_decision', 'signature_refused'} <= reasons),
                        ('metrics count refusals by reason and adoption signatures issued',
                         metrics.get('signatures') == 4
                         and metrics.get('failed_by_reason') == {'remote_owner_mismatch': 1, 'push_refused': 1,
                                                                 'signature_refused': 1}
                         and (metrics.get('refused_by_reason') or {}).get('no_settled_decision') == 4),
                        ('no token, key or signature is observed',
                         W['TOKEN'] not in text and 'SSH SIGNATURE' not in observations.read_text()
                         and 'PRIVATE KEY' not in text)])

                # AC2: the running service took them on, in the same process, with nothing reinstalled.
                if proc is None:
                    for label in ('adoption/taken-on-running', 'adoption/same-process', 'adoption/packet-accepted',
                                  'adoption/not-taken-on-named'):
                        check(label, [(NO_SERVICE, False)])
                else:
                    with region('adoption/taken-on-running', 'adoption/same-process', 'adoption/packet-accepted'):
                        alive.append(proc.poll() is None)
                        after_inspect = inspect(factory_path)
                        served = result_of(after_inspect)
                        alpha_record, beta_record = record(repos['alpha']['uuid']) or {}, record(repos['beta']['uuid']) or {}
                        configs = {}
                        for label in ('alpha', 'beta'):
                            taken = (record(repos[label]['uuid']) or {}).get('taken_on') or {}
                            path = taken.get('receiver_config')
                            configs[label] = (path, json.loads(Path(path).read_text()) if path and Path(path).is_file() else {},
                                              (os.stat(path).st_mode & 0o777) if path and Path(path).is_file() else None)
                        service_log = [json.loads(line) for line in
                                       Path(service_config['observations']).read_text().splitlines()]
                        take_ons = {e.get('repository_uuid'): e for e in service_log
                                    if e.get('kind') == 'adoption' and e.get('outcome') == 'accepted'}
                        check('adoption/taken-on-running', [
                            ('before adoption the service served only the factory repository',
                             result_of(before_inspect).get('repositories') == [FACTORY]),
                            ('the store binds each adopted repository at its path',
                             S.bound_repository(conn, DOMAIN, repos['alpha']['uuid']) == repos['alpha']['path']
                             and S.bound_repository(conn, DOMAIN, repos['beta']['uuid']) == repos['beta']['path']),
                            ('the running service serves them now',
                             served.get('repositories') == sorted([FACTORY, repos['alpha']['uuid'], repos['beta']['uuid']])),
                            ('each has its receiver configuration beside the installed ones, 0600, naming it',
                             all(path and os.path.dirname(path) == os.path.dirname(config_path) and mode == 0o600
                                 and data.get('repository') == repos[label]['uuid']
                                 and data.get('workspace') == repos[label]['path'] and data.get('store') == str(db)
                                 for label, (path, data, mode) in configs.items())),
                            ('each record is active', alpha_record.get('state') == 'active'
                             and beta_record.get('state') == 'active'),
                            ('the service observes taking each on, naming the decision and the instance',
                             all((take_ons.get(repos[label]['uuid']) or {}).get('request') == (record(repos[label]['uuid']) or {}).get('request')
                                 and (take_ons.get(repos[label]['uuid']) or {}).get('instance_id') == instance.get('instance_id')
                                 for label in ('alpha', 'beta'))),
                            ('each adoption was answered by the running service before the effect returned: active, '
                             'no refusal', all(r.get('state') == 'active' and r.get('reason') is None
                                               for r in (alpha_result, beta_result)))])
                        taken = [(record(repos[label]['uuid']) or {}).get('taken_on') or {} for label in ('alpha', 'beta')]
                        check('adoption/same-process', [
                            ('the service process ran throughout', all(alive) and proc.poll() is None),
                            ('it is the same process: pid and kernel start time unchanged',
                             proc.pid == pid and process_start(pid) == started),
                            ('the instance serving now is the one that served before (instance_id and serving time)',
                             bool(instance.get('instance_id')) and served.get('instance') == instance),
                            ('each record names that same instance as the one that took it on',
                             all(t.get('instance_id') == instance.get('instance_id') and t.get('pid') == pid
                                 and t.get('process_start') == started
                                 and t.get('serving_since') == instance.get('serving_since') for t in taken)),
                            ('nothing was reinstalled: the fixed executable, the unit and service.json are unchanged',
                             fixed_state() == fixed_before)])
                        alpha_inspect = inspect(repos['alpha']['path'])
                        alpha_note = note(repos['alpha']['path'], repos['alpha']['uuid'])
                        stray_after = note(stray_path, 'repository-161-stray')
                        check('adoption/packet-accepted', [
                            ('from its workspace, the repository\'s packet is accepted by the same running instance',
                             alpha_inspect.get('accepted') is True and result_of(alpha_inspect).get('ok') is True
                             and result_of(alpha_inspect).get('instance') == instance),
                            ('a store command naming the adopted repository commits',
                             alpha_note.get('accepted') is True and result_of(alpha_note).get('ok') is True
                             and (entity('note:' + repos['alpha']['uuid']) or {}).get('data') == {'from': repos['alpha']['uuid']}),
                            ('a repository enrolled to this store that no settlement adopted is refused, before and after',
                             result_of(stray_before).get('reason') == 'missing_authority:repository_not_served'
                             and result_of(stray_after).get('reason') == 'missing_authority:repository_not_served'
                             and entity('note:repository-161-stray') is None)])

                    # A repository the running service did not take on, named; the next instance takes it on.
                    with region('adoption/not-taken-on-named'):
                        stop_service(proc)
                        delta = repos['delta']
                        delta_proposal = prepared('delta', delta['uuid'], delta['remote'], delta['path'])
                        delta_rid, _r, _ = settle('A-delta', delta_proposal)
                        delta_result = adopt(delta_rid)
                        delta_waiting = (record(delta['uuid']) or {}).get('state')
                        restarted = start_service()
                        delta_state = wait_state(delta['uuid'])
                        delta_taken = (record(delta['uuid']) or {}).get('taken_on') or {}
                        alpha_again = inspect(repos['alpha']['path'])
                        events = [json.loads(line) for line in observations.read_text().splitlines()]
                        metrics = R.metrics(conn, events)
                        check('adoption/not-taken-on-named', [
                            ('with no service running the adoption reports not_taken_on:authority_unavailable and stays '
                             'provisioning', delta_result.get('reason') == 'not_taken_on:authority_unavailable'
                             and delta_waiting == 'provisioning'
                             and any(e.get('reason') == 'not_taken_on' and e.get('repository') == delta['uuid']
                                     for e in events)),
                            ('the next instance takes it on at its start, named as itself',
                             delta_state == 'active' and delta_taken.get('pid') == restarted.pid
                             and delta_taken.get('instance_id') not in (None, instance.get('instance_id'))),
                            ('a repository adopted before the restart is served again',
                             alpha_again.get('accepted') is True and result_of(alpha_again).get('ok') is True),
                            ('metrics count the repositories adopted and taken on by the running service',
                             metrics.get('adopted') == 3 and metrics.get('taken_on') == 3)])
                        stop_service(restarted)

                # ---------------------------------------------------------------------------------------------
                # The effect's own refusals, before anything is moved or pushed, and its named outcomes.
                # ---------------------------------------------------------------------------------------------
                fixture_identity = ('Fixture', 'fixture@example.invalid')
                record_identity = PR.identity_record(conn, DOMAIN, 'fixture')

                def plumbing(path, *args, stdin=None):
                    done = GP.run(['git', '-C', str(path), *args], capture_output=True, text=True, timeout=60,
                                  input=stdin, identity=fixture_identity)
                    if done.returncode:
                        raise RuntimeError('git %s: %s' % (args[0], done.stderr.strip()[:300]))
                    return done.stdout.strip()

                def nothing_adopted(repo, uuid=None):
                    uuid = uuid or repo['uuid']
                    return (CE.read_binding(repo['path']) is None and S.bound_repository(conn, DOMAIN, uuid) is None
                            and not any(x.get('repository') == uuid for x in signature_rows()))

                def hand_proposal(repo, uuid, scaffold_commit=None, remote=None):
                    return R.adoption_proposal(repository=uuid, name=uuid.rsplit('-', 1)[-1], owner='owner',
                                               identity='fixture', path=repo['path'], remote=remote or repo['remote'],
                                               default_branch='main', base_commit=repo['base'],
                                               scaffold_commit=scaffold_commit)

                with region('adoption/unknown-outcome'):
                    fault = repos['fault']
                    fault_rid, _r, _ = settle('A-fault', prepared('fault', fault['uuid'], fault['remote'], fault['path']))
                    real_configured = AD.P.check_configured_remote

                    def faulty(*args, **kwargs):
                        raise RuntimeError('an unexpected fault in a step')
                    AD.P.check_configured_remote = faulty
                    try:
                        try:
                            fault_result = adopt(fault_rid)
                        except Exception as error:  # noqa: BLE001 - a raise is what the row refuses
                            fault_result = {'raised': type(error).__name__}
                    finally:
                        AD.P.check_configured_remote = real_configured
                    fault_record = record(fault['uuid']) or {}
                    check('adoption/unknown-outcome', [
                        ('an unexpected fault is reported, never raised', 'raised' not in fault_result
                         and fault_result.get('ok') is False),
                        ('it is named unknown_outcome:<type>', fault_result.get('reason') == 'unknown_outcome:RuntimeError'),
                        ('the record is failed and names it, never left provisioning',
                         fault_record.get('state') == 'failed' and fault_record.get('reason') == 'unknown_outcome:RuntimeError'),
                        ('nothing is signed, enrolled or bound', nothing_adopted(fault))])

                with region('adoption/push-unconfirmed'):
                    landed = repos['landed']
                    # The remote accepts the push and then moves its branch back: the push landed and the branch
                    # does not read back as the commit.
                    receive = Path(landed['bare']) / 'hooks' / 'post-receive'
                    receive.write_text('#!/bin/sh\nexec git update-ref refs/heads/main %s\n' % landed['base'])
                    receive.chmod(0o700)
                    landed_proposal = prepared('landed', landed['uuid'], landed['remote'], landed['path'])
                    landed_rid, _r, _ = settle('A-landed', landed_proposal)
                    try:
                        landed_result = adopt(landed_rid)
                    finally:
                        receive.unlink()
                    landed_record = record(landed['uuid']) or {}
                    received = GP.run(['git', '-C', landed['bare'], 'cat-file', '-e',
                                       '%s^{commit}' % landed_proposal.get('scaffold_commit')], capture_output=True)
                    check('adoption/push-unconfirmed', [
                        ('the remote received the commit and its branch does not hold it',
                         received.returncode == 0 and tip(landed['bare']) == landed['base']),
                        ('the adoption reports push_unconfirmed:remote, not a refused push',
                         landed_result.get('ok') is False and landed_result.get('reason') == 'push_unconfirmed:remote'),
                        ('its record is failed and names it, a class of its own',
                         landed_record.get('state') == 'failed' and landed_record.get('reason') == 'push_unconfirmed:remote'
                         and R.reason('push_unconfirmed:remote') == 'push_unconfirmed'),
                        ('nothing is signed, enrolled or bound', nothing_adopted(landed))])

                with region('adoption/repository-commands'):
                    monitored, filtered = repos['monitored'], repos['filtered']
                    marker = base / 'repository-command-ran'
                    command = base / 'repository-command'
                    command.write_text('#!/bin/sh\necho ran >> %s\ncat\n' % marker)
                    command.chmod(0o700)
                    # Laid when the owner was asked; the command is planted in the repository afterwards.
                    monitored_commit = PR.lay_scaffold(monitored['path'], monitored['base'], record_identity,
                                                       str(ROOT / 'engine'), 'refs/veldo/adoption/' + monitored['uuid'])
                    git(monitored['path'], 'config', 'core.fsmonitor', str(command))
                    git(filtered['path'], 'config', 'filter.v161.smudge', str(command))
                    PR.git(monitored['path'], 'status', '--porcelain')
                    status_ran = marker.exists()

                    def prepare_code(repo, uuid, remote=None):
                        try:
                            prepared(uuid.rsplit('-', 1)[-1], uuid, remote or repo['remote'], repo['path'])
                            return None
                        except PR.Refused as error:
                            return error.code
                    monitored_prepare = prepare_code(monitored, 'repository-161-monitored2')
                    filtered_prepare = prepare_code(filtered, filtered['uuid'])
                    monitored_refs = refs(monitored['path'])
                    monitored_rid, _r, _ = settle('A-monitored', hand_proposal(monitored, monitored['uuid'],
                                                                                monitored_commit))
                    monitored_result = adopt(monitored_rid)
                    check('adoption/repository-commands', [
                        ('a local step runs no fsmonitor of the repository (git status with one configured)',
                         not status_ran),
                        ('prepare refuses a repository whose configuration names an fsmonitor, laying nothing',
                         monitored_prepare == 'invalid_input:repository_command:core.fsmonitor'
                         and monitored_refs == ['refs/veldo/adoption/' + monitored['uuid']]),
                        ('prepare refuses one whose configuration names a filter command, laying nothing',
                         filtered_prepare == 'invalid_input:repository_command:filter.v161.smudge'
                         and refs(filtered['path']) == []),
                        ('the settled adoption of a repository that came to name one refuses it before the branch moves',
                         monitored_result.get('reason') == 'invalid_input:repository_command:core.fsmonitor'
                         and (record(monitored['uuid']) or {}).get('state') == 'failed'
                         and tip(monitored['path']) == monitored['base'] and tip(monitored['bare']) == monitored['base']
                         and nothing_adopted(monitored) and refs(monitored['path']) == []),
                        ('no command of the repository ran', not marker.exists())])

                with region('adoption/scaffold-problems'):
                    crafted = repos['crafted']
                    cpath, cbase = crafted['path'], crafted['base']
                    good = PR.lay_scaffold(cpath, cbase, record_identity, str(ROOT / 'engine'), 'refs/veldo/elsewhere/crafted')
                    tree = git(cpath, 'rev-parse', good + '^{tree}')
                    side = plumbing(cpath, 'commit-tree', cbase + '^{tree}', '-p', cbase, '-m', 'side')
                    on_side = plumbing(cpath, 'commit-tree', tree, '-p', side, '-m', 'the scaffold on another parent')
                    blob = plumbing(cpath, 'hash-object', '-w', '--stdin', stdin='changed\n')
                    entries = git(cpath, 'ls-tree', tree).splitlines()
                    changed = plumbing(cpath, 'mktree', stdin=''.join(
                        ('100644 blob %s\tREADME\n' % blob) if entry.split('\t', 1)[1] == 'README' else entry + '\n'
                        for entry in entries))
                    modifying = plumbing(cpath, 'commit-tree', changed, '-p', cbase, '-m', 'a scaffold that modifies')
                    crafted_cases = {
                        'a commit not recorded for the repository': ('a', good, None, 'stale_subject:scaffold_commit_not_named'),
                        'a commit on another parent than the base': ('b', on_side, on_side, 'stale_subject:scaffold_parent'),
                        'a commit that modifies a file': ('c', modifying, modifying, 'stale_subject:scaffold_changes_files')}
                    crafted_outcomes = {}
                    for case, (suffix, commit, recorded, expected) in crafted_cases.items():
                        uuid = 'repository-161-crafted-' + suffix
                        if recorded:
                            git(cpath, 'update-ref', 'refs/veldo/adoption/' + uuid, recorded)
                        rid, _r, _ = settle('A-crafted-' + suffix, hand_proposal(crafted, uuid, commit))
                        crafted_outcomes[case] = (adopt(rid), record(uuid) or {}, expected, uuid)
                    check('adoption/scaffold-problems', [
                        ('%s: refused %s, its record failed naming it' % (case, expected),
                         outcome.get('reason') == expected and rec.get('state') == 'failed' and rec.get('reason') == expected)
                        for case, (outcome, rec, expected, uuid) in crafted_outcomes.items()] + [
                        ('the branch never moved and nothing was pushed', tip(cpath) == cbase and tip(crafted['bare']) == cbase),
                        ('nothing is signed, enrolled or bound', all(nothing_adopted(crafted, uuid)
                                                                     for _o, _r, _e, uuid in crafted_outcomes.values()))])

                with region('adoption/prepare-checks'):
                    unconfigured = repos['unconfigured']
                    not_configured = prepare_code(unconfigured, unconfigured['uuid'])
                    another_remote = prepare_code(crafted, 'repository-161-crafted-d', remote=repos['landed']['remote'])
                    not_ids = {text: prepare_code(crafted, text) for text in ('crafted/e', '..', 'crafted.lock', 'a..b')}
                    unconfigured_rid, _r, _ = settle('A-unconfigured', hand_proposal(unconfigured, unconfigured['uuid']))
                    unconfigured_result = adopt(unconfigured_rid)
                    check('adoption/prepare-checks', [
                        ('a remote the repository is not configured with is refused, laying nothing',
                         not_configured == 'invalid_input:remote_not_configured' and refs(unconfigured['path']) == []),
                        ('so is a remote other than the one it is configured with',
                         another_remote == 'invalid_input:remote_not_configured'),
                        ('a repository id that is not one ref component is refused, laying nothing',
                         all(code == 'invalid_input:proposal:repository' for code in not_ids.values())
                         and not any(ref.startswith('refs/veldo/adoption/crafted') or '..' in ref
                                     for ref in refs(cpath))),
                        ('the settled adoption of it refuses the remote again, before anything is signed',
                         unconfigured_result.get('reason') == 'invalid_input:remote_not_configured'
                         and (record(unconfigured['uuid']) or {}).get('state') == 'failed'
                         and nothing_adopted(unconfigured))])

                # ---------------------------------------------------------------------------------------------
                # The service's judgment in this process: a Service over the installed configuration and this
                # store, and control_client's Authority judging each request as the socket's serving side does.
                # ---------------------------------------------------------------------------------------------
                inproc_config = copy.deepcopy(service_config)
                inproc_config['observations'] = str(base / 'inproc-observations.jsonl')

                def in_process():
                    return CS.Service(copy.deepcopy(inproc_config), conn)

                def judged(svc):
                    authority = CC.Authority(service_config['store_uuid'], DOMAIN, service_config['store_path'], CS.E,
                                             svc.verify, HOST, svc.apply, watermark=svc.watermark, minimum_generation=1,
                                             context=True)

                    def send_to(workspace, packet, enrollment, verify, sign, host_identity, timeout=30.0):
                        enrollment.resolve_store(workspace, verify, host_identity)
                        binding = enrollment.read_binding(workspace)
                        return authority.judge(CC.build_request(workspace, binding, packet, sign), os.getuid())
                    return send_to

                def receiver_path(repository):
                    return os.path.join(os.path.dirname(config_path),
                                        'receiver-%s.json' % hashlib.sha256(repository.encode()).hexdigest()[:16])

                def take_on_packet(repo, request):
                    return {'operation': 'take_on', 'repository_uuid': repo['uuid'], 'request': request}

                with region('adoption/take-on-answered', 'adoption/receiver-configuration-used'):
                    svc = in_process()
                    answered = repos['tk-answered']
                    answered_rid, _r, _ = settle('A-tk-answered', prepared('tk-answered', answered['uuid'],
                                                                         answered['remote'], answered['path']))
                    answered_result = adopt(answered_rid, send=judged(svc))
                    answered_record = record(answered['uuid']) or {}
                    answered_verify = trust.verifier('adoption-signer', answered['path'])
                    by_member = judged(svc)(answered['path'], take_on_packet(answered, answered_rid), CS.E,
                                            answered_verify, lambda d: sign_as('steward', d, 'veldo-adoption-take-on'), HOST)
                    by_adoption_key = judged(svc)(answered['path'], take_on_packet(answered, answered_rid), CS.E,
                                                  answered_verify, AD._ssh_signer(str(adoption_key), 'veldo-adoption-take-on'),
                                                  HOST)
                    stray_take_on = judged(svc)(stray_path, {'operation': 'take_on', 'repository_uuid': 'repository-161-stray',
                                                             'request': answered_rid}, CS.E, binding_verify,
                                                AD._ssh_signer(installed['journal_key'], 'veldo-adoption-take-on'), HOST)
                    check('adoption/take-on-answered', [
                        ('the effect hands the record to the service and gets its answer: active, no refusal',
                         answered_result.get('state') == 'active' and answered_result.get('reason') is None),
                        ('the record is active, naming the instance that answered',
                         answered_record.get('state') == 'active'
                         and (answered_record.get('taken_on') or {}).get('instance_id') == svc.instance['instance_id']),
                        ('that instance serves it from then on', answered['uuid'] in svc.repositories),
                        ('a take-on request signed by a member rather than the journal key is refused',
                         by_member.get('accepted') is False and by_member.get('reason') == 'command_signature_invalid'),
                        ('so is one signed by the adoption signer\'s key',
                         by_adoption_key.get('accepted') is False
                         and by_adoption_key.get('reason') == 'command_signature_invalid'),
                        ('a take-on from a repository no record names takes nothing on',
                         result_of(stray_take_on).get('ok') is False
                         and result_of(stray_take_on).get('reason') == 'not_taken_on:no_record'
                         and 'repository-161-stray' not in svc.repositories)])
                    # The launch receiver, enrolled as the installation's receiver principal, run over the receiver
                    # configuration the service wrote for the adopted repository.
                    keyfile['launch-receiver'] = keys / 'launch-receiver'
                    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v161-launch-receiver', '-f',
                                    str(keyfile['launch-receiver'])], check=True, capture_output=True, timeout=20,
                                   stdin=subprocess.DEVNULL, env=quiet())
                    admin('steward', 'enroll_principal', {
                        'principal': 'launch-receiver', 'principal_type': 'service', 'roles': [],
                        'public_key': ' '.join(Path(str(keyfile['launch-receiver']) + '.pub').read_text().split()[:2]),
                        'independence_group': 'launch-receiver', 'scope': '*'}, enrollee='launch-receiver')
                    written = (answered_record.get('taken_on') or {}).get('receiver_config')
                    dispatch_id = 'dispatch-v161-receiver'
                    contract = {'dispatch_id': dispatch_id, 'unit': 'VELDO-9161', 'station': 'build',
                                'repository': answered['uuid'], 'domain': DOMAIN, 'capability': {'adapter': 'v161'}}
                    fixture('dispatch:' + dispatch_id, 'dispatch', {
                        'schema': 'veldo.dispatch/v1', 'dispatch_id': dispatch_id, 'state': 'prepared',
                        'contract': contract, 'contract_digest': 'sha256:' + '0' * 64, 'receiver': None,
                        'process': None, 'termination': None, 'refusal': None, 'stop': None, 'reason': None,
                        'history': []})
                    launched = subprocess.run([sys.executable, service_config['receiver']['executable'], str(written)],
                                              input=json.dumps({'contract': contract}) + '\n', capture_output=True,
                                              text=True, timeout=120, env=quiet())
                    emitted_events = [json.loads(line) for line in launched.stdout.splitlines() if line.strip()]
                    refused = (entity('dispatch:' + dispatch_id) or {}).get('data') or {}
                    last = conn.execute('SELECT principal, command_id FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
                    check('adoption/receiver-configuration-used', [
                        ('the service wrote it for the adopted repository', bool(written) and Path(written).is_file()
                         and json.loads(Path(written).read_text()).get('repository') == answered['uuid']),
                        ('the receiver run over it judges a packet as the adopted repository\'s',
                         len(emitted_events) == 1 and emitted_events[0].get('event') == 'refused'
                         and emitted_events[0].get('refusal') == 'binding_mismatch:contract_digest'
                         and emitted_events[0].get('repository') == answered['uuid']
                         and emitted_events[0].get('configuration') == os.path.realpath(str(written))),
                        ('and records its refusal in this store, as the installation\'s receiver principal',
                         refused.get('state') == 'refused' and refused.get('refusal') == 'binding_mismatch:contract_digest'
                         and last is not None and last[0] == 'launch-receiver'
                         and last[1].startswith('dispatch/refuse/' + dispatch_id))])

                with region('adoption/take-on-write-first'):
                    gamma = repos['gamma']
                    gamma_rid, _r, _ = settle('A-gamma', prepared('gamma', gamma['uuid'], gamma['remote'], gamma['path']))
                    gamma_result = adopt(gamma_rid, send=unsent)
                    svc = in_process()
                    real_write = CS.REPO.write
                    write_outcomes = {}
                    for label, fault in (('sqlite3.Error', sqlite3.OperationalError('database is locked')),
                                         ('StoreRefused', CS.S.StoreRefused('stale_version', 'the record moved'))):
                        def failing(store, conn_, journal_, repository, state, _fault=fault, **kwargs):
                            if state == 'active':
                                raise _fault
                            return real_write(store, conn_, journal_, repository, state, **kwargs)
                        CS.REPO.write = failing
                        try:
                            svc.adoption_faults.clear()
                            observation = svc.take_on_record(record(gamma['uuid']))
                        finally:
                            CS.REPO.write = real_write
                        write_outcomes[label] = (observation.get('refusal'), gamma['uuid'] in svc.repositories,
                                                 gamma['uuid'] in svc.config['receiver']['configs'],
                                                 os.path.lexists(receiver_path(gamma['uuid'])),
                                                 (record(gamma['uuid']) or {}).get('state'))
                    check('adoption/take-on-write-first', [
                        ('the adoption left it provisioning for a service', gamma_result.get('state') == 'provisioning'),
                        ('a store fault writing it active serves nothing and keeps no receiver configuration',
                         write_outcomes['sqlite3.Error'] == ('not_taken_on:unknown_outcome:OperationalError', False, False,
                                                             False, 'provisioning')),
                        ('a refused write of it active serves nothing either, and it is failed by name',
                         write_outcomes['StoreRefused'] == ('not_taken_on:stale_version', False, False, False, 'failed'))])

                with region('adoption/take-on-refusals'):
                    svc = in_process()

                    def provisioning_record(repo, uuid, request, settlement, enrollment):
                        R.write(S, conn, ('authority', journal_sign), uuid, 'provisioning', step='settled',
                                domain_uuid=DOMAIN, name=uuid, identity='fixture', path=repo['path'],
                                remote={'url': repo['remote'], 'owner': W['OWNER'], 'default_branch': 'main'},
                                request=request, settlement=settlement, scaffold_commit=None, base_commit=repo['base'],
                                enrollment=enrollment, reason=None)
                    # The decision: the record names a request no owner settled.
                    signature_repo = repos['tk-signature']
                    provisioning_record(signature_repo, 'repository-161-tk-decision', unanswered, None, 'sha256:' + '1' * 64)
                    # The signature: a settled decision names it, no adoption signature was journaled.
                    signature_rid, _r, _ = settle('A-tk-signature', prepared('tk-signature', signature_repo['uuid'],
                                                                           signature_repo['remote'], signature_repo['path']))
                    provisioning_record(signature_repo, signature_repo['uuid'], signature_rid,
                                        R.settled(S, CM, conn, signature_rid)['settlement_id'], 'sha256:' + '2' * 64)
                    # The binding's signer: a settled decision and a journaled signature, the binding the owner's.
                    signer_repo = repos['tk-signer']
                    signer_rid, _r, _ = settle('A-tk-signer', prepared('tk-signer', signer_repo['uuid'], signer_repo['remote'],
                                                                     signer_repo['path']))
                    owner_binding = CE.enroll(signer_repo['path'], DOMAIN, STORE, str(db), HOST, 1,
                                              lambda data: sign_as('owner', data, 'veldo-enrollment'), 'owner', time.time(),
                                              repository_uuid=signer_repo['uuid'])
                    signer_settlement = R.settled(S, CM, conn, signer_rid)['settlement_id']
                    fixture('adoption-signature:' + signer_settlement, 'adoption_signature', {
                        'repository': signer_repo['uuid'], 'request': signer_rid, 'settlement': signer_settlement,
                        'binding_digest': CE.binding_digest(owner_binding), 'signer': 'adoption-signer',
                        'domain_uuid': DOMAIN, 'at': 1.0})
                    provisioning_record(signer_repo, signer_repo['uuid'], signer_rid, signer_settlement,
                                        CE.binding_digest(owner_binding))
                    # The store binding: adopted in full, except that the store does not bind it.
                    store_repo = repos['tk-store']
                    store_rid, _r, _ = settle('A-tk-store', prepared('tk-store', store_repo['uuid'], store_repo['remote'],
                                                                   store_repo['path']))
                    real_bind = AD.S.bind_repositories
                    AD.S.bind_repositories = lambda *args, **kwargs: None
                    try:
                        store_result = adopt(store_rid, send=unsent)
                    finally:
                        AD.S.bind_repositories = real_bind
                    take_on_cases = {
                        'a record no settled decision answers': ('repository-161-tk-decision',
                                                                 'not_taken_on:no_settled_decision:not_settled'),
                        'no adoption signature journaled': (signature_repo['uuid'], 'not_taken_on:no_adoption_signature'),
                        'a binding the adoption signer did not sign': (signer_repo['uuid'],
                                                                       'not_taken_on:binding:not_the_adopted_binding'),
                        'a repository the store does not bind': (store_repo['uuid'], 'not_taken_on:store_binding')}
                    take_on_outcomes = {case: (svc.take_on_record(record(uuid)).get('refusal'), uuid in svc.repositories,
                                               (record(uuid) or {}).get('state'), expected)
                                        for case, (uuid, expected) in take_on_cases.items()}
                    check('adoption/take-on-refusals', [
                        ('the store-binding case was adopted in full but for the store binding',
                         store_result.get('state') == 'provisioning' and CE.read_binding(store_repo['path']) is not None
                         and S.bound_repository(conn, DOMAIN, store_repo['uuid']) is None)] + [
                        ('%s: refused %s, not served, failed' % (case, expected),
                         (code, served, state) == (expected, False, 'failed'))
                        for case, (code, served, state, expected) in take_on_outcomes.items()])

                with region('adoption/take-on-retry'):
                    retry_x, retry_y = repos['tk-retry-x'], repos['tk-retry-y']
                    for label in ('tk-retry-x', 'tk-retry-y'):
                        repo = repos[label]
                        rid, _r, _ = settle('A-' + label, prepared(label, repo['uuid'], repo['remote'], repo['path']))
                        adopt(rid, send=unsent)
                    svc = in_process()
                    real_settled = CS.REPO.settled
                    x_request = (record(retry_x['uuid']) or {}).get('request')

                    def flaky(store, membership, conn_, request, now=None):
                        if request == x_request:
                            raise RuntimeError('a transient fault')
                        return real_settled(store, membership, conn_, request, now)
                    CS.REPO.settled = flaky
                    try:
                        first = {o.get('repository_uuid'): o for o in svc.take_on()}
                    finally:
                        CS.REPO.settled = real_settled
                    due = svc.adoption_due()
                    faulted_at = time.monotonic()
                    second = {o.get('repository_uuid'): o for o in svc.take_on()}
                    svc.adoption_faults[retry_x['uuid']] = time.monotonic() - 1
                    third = {o.get('repository_uuid'): o for o in svc.take_on()}
                    check('adoption/take-on-retry', [
                        ('a fault taking one record on is named and leaves it provisioning',
                         (first.get(retry_x['uuid']) or {}).get('refusal') == 'not_taken_on:unknown_outcome:RuntimeError'
                         and retry_x['uuid'] not in second and (record(retry_x['uuid']) or {}).get('state') in ('provisioning', 'active')),
                        ('another record taken on meanwhile', (first.get(retry_y['uuid']) or {}).get('outcome') == 'accepted'),
                        ('the faulted record is not judged again before its own retry time, whatever was taken on since',
                         retry_x['uuid'] not in second and due is not None
                         and due - faulted_at > CS.ADOPTION_RETRY_SECONDS - 1),
                        ('once its time came it is judged again and taken on',
                         (third.get(retry_x['uuid']) or {}).get('outcome') == 'accepted'
                         and (record(retry_x['uuid']) or {}).get('state') == 'active' and svc.adoption_due() is None)])

                with region('adoption/active-served-again'):
                    template_path = sorted(service_config['receiver']['configs'].values())[0]
                    template = json.loads(Path(template_path).read_text())
                    # A setup re-run rewrote the installed receiver configuration.
                    Path(template_path).write_text(json.dumps(dict(template, adapters=dict(
                        template.get('adapters') or {}, v161={'argv': ['true']})), indent=1, sort_keys=True) + '\n')
                    rewritten = Path(template_path).read_text()
                    # The owner no longer holds project_owner: a later change of membership.
                    admin('steward', 'change_roles', {'principal': 'owner', 'roles': []})
                    try:
                        R.settled(S, CM, conn, answered_rid)
                        now_settled = 'settled'
                    except R.Refused as error:
                        now_settled = error.code
                    later = in_process()
                    again = [o for o in later.take_on() if o.get('repository_uuid') == answered['uuid']]
                    answered_receiver = (record(answered['uuid']) or {}).get('taken_on', {}).get('receiver_config')
                    expected_receiver = json.dumps(dict(json.loads(rewritten), repository=answered['uuid'],
                                                        workspace=answered['path']), indent=1, sort_keys=True) + '\n'
                    check('adoption/active-served-again', [
                        ('the owner no longer holds project_owner, so his decision would not be judged settled now',
                         now_settled == 'no_settled_decision:not_owner'),
                        ('a new instance serves the active repository again, on its signature, binding and store binding',
                         len(again) == 1 and again[0].get('outcome') == 'accepted' and again[0].get('resumed') is True
                         and answered['uuid'] in later.repositories),
                        ('the receiver configuration it wrote is written again from the installed one as it is now',
                         bool(answered_receiver) and Path(answered_receiver).read_text() == expected_receiver
                         and (os.stat(answered_receiver).st_mode & 0o777) == 0o600),
                        ('the installed receiver configuration is not written by it', Path(template_path).read_text() == rewritten)])

                # Every adoption signature of every row above, judged once they are all made and before the fence's
                # own end: its stand-in records each one, and nothing may have connected to its agent.
                put_back()
                watch.close()
                every, signatures = watch.invocations(), signature_rows()
                check('adoption/signer-no-agent', agent_row + [
                    ('every adoption signature the suite asked for ran with this row\'s agent named [%d asked, %d '
                     'journaled]' % (watch.signed, len(signatures)), watch.signed >= max(2, len(signatures))),
                    ('no ssh-keygen any row started there had an SSH agent in its environment',
                     bool(every) and all(a['agent'] == [] for a in every)),
                    ('nothing connected to this row\'s agent %s' % watch.connections[:3], watch.connections == [])])
        finally:
            if watch is not None:
                put_back()
                watch.close()
            for proc in services:
                if proc.poll() is None:
                    with contextlib.suppress(Exception):
                        proc.kill()
                        proc.wait(timeout=10)
            for server in servers:
                with contextlib.suppress(Exception):
                    server.shutdown()
                    server.server_close()
            for conn in connections:
                with contextlib.suppress(Exception):
                    conn.close()
    for first in regions:
        check('ran/' + first, [('ran to its end', first not in {label for label, _ in raised})])


_v161_started = __import__('time').monotonic()
_v161_suite()
print('VELDO-0161 suite seconds: %.3f' % (__import__('time').monotonic() - _v161_started))
