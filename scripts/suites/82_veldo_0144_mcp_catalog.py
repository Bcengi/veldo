"""VELDO-0144: real passkey API, authority commands and SQLite, scratch secret-tool.

Only shared ROOT and expect are used. The production HTTP handler serves TLS on
loopback with a generated certificate. Requests are serviced serially on the
SQLite owner's thread. The authority's Service.apply and ServiceApi.call run in
process; the protected API signer runs its normal joined subprocess. No real
keyring or external host is contacted. Every row is reported exactly once.
"""


def _v144_suite():
    import base64
    import copy
    import fcntl
    import hashlib
    import http.client
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import socketserver
    import ssl
    import sys
    import subprocess
    import tempfile
    import threading
    import time
    from types import MethodType, SimpleNamespace

    PRODUCTION = {
        'control_mcp_catalog.py': ROOT / ".veldo" / "control_mcp_catalog.py",
        'control_credential.py': ROOT / ".veldo" / "control_credential.py",
        'control_credential_keystore.py': ROOT / ".veldo" / "control_credential_keystore.py",
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_service_api.py': ROOT / ".veldo" / "control_service_api.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    names = ('catalog/stdio', 'catalog/http', 'catalog/host-command', 'catalog/immutable-history',
             'catalog/stale-unauthorized', 'catalog/invalid', 'catalog/atlassian', 'credential/write',
             'credential/replace-delete', 'credential/read-back', 'credential/no-value-on-command-line',
             'credential/no-value-in-records', 'credential/keystore-refusals', 'credential/authority-binding',
             'catalog/observability', 'install/assets', 'catalog/known-shape-refused',
             'catalog/ordinary-config-saves', 'catalog/credential-position-refused', 'catalog/deleted-reference',
             'catalog/credential-domain', 'credential/libsecret-protocol', 'credential/replay-value',
             'credential/encoding', 'credential/deleted-state', 'catalog/refusal-no-value')
    rows = {name: [] for name in names}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def attempt(fn):
        try:
            return fn(), None
        except Exception as exc:
            return None, getattr(exc, 'code', type(exc).__name__)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def b64(data):
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

    def run(argv, **kw):
        return subprocess.run(argv, capture_output=True, check=True, timeout=20, **kw)

    original = {k: os.environ.get(k) for k in ('PATH', 'DBUS_SESSION_BUS_ADDRESS')}
    server, ing, fixture, lock = None, None, None, None
    with tempfile.TemporaryDirectory(prefix='v144-') as temporary:
        base = Path(temporary)
        # Capture actual fd 1 and fd 2, including os.write and inherited child descriptors.
        captures = [open(base / ('fd-' + str(fd)), 'w+b', buffering=0) for fd in (1, 2)]
        saved_fds = [os.dup(fd) for fd in (1, 2)]
        sys.stdout.flush()
        sys.stderr.flush()
        for fd, capture in zip((1, 2), captures):
            os.dup2(capture.fileno(), fd)
        process_outputs, lookup_outputs = [], []
        original_popen = subprocess.Popen

        class CapturedProcess(original_popen):
            def communicate(self, *args, **kwargs):
                stdout, stderr = super().communicate(*args, **kwargs)
                argv = self.args if isinstance(self.args, list) else []
                # Lookup stdout is the intended value channel, not a diagnostic.
                lookup = len(argv) > 1 and Path(str(argv[0])).name == 'secret-tool' and argv[1] == 'lookup'
                if lookup:
                    lookup_outputs.append(stdout)
                process_outputs.extend([stderr, None if lookup else stdout])
                return stdout, stderr

        subprocess.Popen = CapturedProcess
        try:
            mods = base / 'installed'
            mods.mkdir()
            for source in (ROOT / '.veldo').glob('*.py'):
                shutil.copyfile(source, mods / source.name)
            for name, source in PRODUCTION.items():
                target = mods / name
                target.unlink(missing_ok=True)
                if source.is_file():
                    shutil.copyfile(source, target)
            # This executable is the only Secret Service reachable by the suite.
            fake = base / 'fake-keystore'
            fake.mkdir()
            program = fake / 'secret-tool'
            program.write_text('''#!/usr/bin/env python3
import hashlib, json, os, pathlib, sys, time
home = pathlib.Path(__file__).parent
action = sys.argv[1]
data = sys.stdin.buffer.read()
args = sys.argv[2:]
label = '-' * 2 + 'label='
has_label = bool(args and args[0].startswith(label))
if has_label:
    args = args[1:]
attributes = dict(zip(args[::2], args[1::2]))
name = json.dumps(attributes, sort_keys=True)
mode = (home / 'mode').read_text() if (home / 'mode').exists() else ''
seen = []
for entry in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
    try:
        line = entry.read_bytes()
    except OSError:
        continue
    if data and data in line:
        seen.append(int(entry.parent.name))
record = {'action': action, 'argv': sys.argv[1:], 'bytes': len(data),
          'input_digest': hashlib.sha256(data).hexdigest(), 'exposed': seen}
with (home / 'calls').open('a') as out:
    out.write(json.dumps(record) + '\\n')
if len(args) % 2 or (action == 'store' and not has_label):
    sys.exit(2)
if mode:
    sys.stderr.write('collection locked' if mode == 'locked' else 'service unreachable')
    sys.exit(1)
identity = hashlib.sha256(name.encode()).hexdigest()
place = home / ('item-' + identity)
matches = []
for metadata in home.glob('attributes-*'):
    stored = json.loads(metadata.read_text())
    if all(stored.get(k) == v for k, v in attributes.items()):
        matches.append(home / ('item-' + metadata.name.removeprefix('attributes-')))
if action == 'store':
    place.write_bytes(data)
    (home / ('attributes-' + identity)).write_text(name)
    time.sleep(0.08)
elif action == 'lookup':
    if not matches:
        sys.exit(1)
    sys.stdout.buffer.write(matches[0].read_bytes() + (b'\\n' if sys.stdout.isatty() else b''))
elif action == 'clear':
    for place in matches:
        place.unlink(missing_ok=True)
        (home / ('attributes-' + place.name.removeprefix('item-'))).unlink(missing_ok=True)
else:
    sys.exit(2)
''')
            program.chmod(0o700)
            os.environ['PATH'] = str(fake) + os.pathsep + (original['PATH'] or '/usr/bin:/bin')
            os.environ['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path=' + str(base / 'absent-bus')
            tree = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
            H = load('v144_fixture', tree / 'scripts/suites/support/v73_authority.py')
            fixture = H.build(base / 'authority-fixture', mods, 5590144, 'http://127.0.0.1:9',
                              os.urandom(12).hex(), scope='activation-repository')
            A = fixture
            CS = load('v144_service', mods / 'control_service.py')
            API = load('v144_api', mods / 'control_api.py')
            SG = load('v144_signer', mods / 'control_api_signer.py')
            SA = CS.SA
            for who, path in (('api-gate', A.keyfile['edge'].with_name('edge-api')),
                              ('api-auth', A.keyfile['edge-auth'].with_name('api-auth'))):
                run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)], stdin=subprocess.DEVNULL)
                A.keyfile[who] = path
                A.public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
            enrollment = A.E.Enrollment(A.S, A.conn, A.ids, 'authority', A.journal_sign, projection=A.projection)
            command = dict(command_id=A.next_id('edge'), operation='enroll_channel_edge', target='channel:api',
                           parameters=dict(channel='api', edge_principal='api-gate', edge_key_id='edge-api',
                                           public_key=A.public['api-gate'], connection_public_key=A.public['api-auth'],
                                           scope=[A.ids['repository_uuid']]), artifact_digests=[], expected_versions={})
            env = A.envelope(command, 'steward')
            enrolled = enrollment.admit(env, command, A.sign_as('steward', A.AC.canonical_envelope_bytes(env)),
                                        A.sign_as('api-gate', A.AC.canonical_envelope_bytes(env), 'veldo-edge-possession'))
            config = dict(A.config, api_edge='api-gate')
            A.config_path.write_text(json.dumps(config))
            ing = CS.CH.IN.open_ingress(A.config_path)
            lock = os.open(A.db.parent / 'authority.lock', os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            state = base / 'service-state'
            state.mkdir()
            service_config = dict(domain_uuid=A.ids['domain_uuid'], store_uuid=A.ids['store_uuid'],
                                  repositories={A.ids['repository_uuid']: {}}, principal='authority',
                                  authority_generation=1, enrollment_signers=str(A.host / 'enrollment_signers'),
                                  journal_key=str(A.keyfile['authority']), observations=str(state / 'observations.jsonl'))
            service = CS.Service(service_config, ing.conn)
            host = 'localhost'
            origin = 'https://' + host
            api_config = dict(schema='veldo.api_service/v1', store_path=str(A.db), authority_ids=A.ids,
                              authority_generation=1, journal=config['journal'], api_edge='api-gate', domain='mcp-domain',
                              projects=[A.ids['repository_uuid']], rp_id=host, origin=origin,
                              workflows_repository=A.ids['repository_uuid'], publication_root=str(A.projection.parents[2]))
            config_file = base / 'api-service.json'
            config_file.write_text(json.dumps(api_config))
            config_file.chmod(0o600)
            service.api = SA.ServiceApi(config_file, SimpleNamespace(ingress=ing), lock, state)
            judge = service.api.authority
            coordinates = dict(repository_uuid=A.ids['repository_uuid'], workspace='scratch')
            # The API's authority seam invokes the actual service command dispatch, not a second writer.
            packets = []

            class Authority:
                def inspect(self, entity_ids):
                    return service.apply(SA.AS.call_command('inspect', dict(entity_ids=entity_ids)), coordinates)

                def apply(self, packet):
                    packets.append(packet)
                    return service.apply(SA.AS.call_command('apply', dict(packet=packet)), coordinates)

                def events(self, principal, after, limit):
                    return service.apply(SA.AS.call_command('events', dict(principal=principal, after=after, limit=limit)),
                                         coordinates)

            signer = SG.ApiSigner(A.signer_config, 'edge-api', A.keyfile['api-auth'])
            api = API.ControlApi(dict(origin=origin, rp_id=host, host=host, domain='mcp-domain', ids=A.ids,
                                      edge='api-gate', state_dir=str(base / 'api-state')), Authority(), signer)
            # Generated TLS material only. Production's loopback handler, serial scheduling for SQLite.
            pem, certificate = base / 'tls.pem', base / 'tls.crt'
            run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(pem),
                 '-out', str(certificate), '-days', '1', '-subj', '/CN=localhost',
                 '-addext', 'subjectAltName=DNS:localhost'])
            server = API.listen(api, '127.0.0.1', 0)
            server.process_request = MethodType(socketserver.BaseServer.process_request, server)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certificate, pem)
            server.socket = context.wrap_socket(server.socket, server_side=True)
            client_context = ssl.create_default_context(cafile=str(certificate))
            session = {}
            tls_versions, replies = [], []

            def call(method, path, body=None, authenticated=True, extra=None):
                headers = dict(Host=host, Origin=origin, **{'Content-Type': 'application/json', 'Connection': 'close'})
                if authenticated:
                    headers.update(session)
                headers.update(extra or {})
                result = []

                def request():
                    connection = http.client.HTTPSConnection('localhost', server.server_address[1],
                                                              context=client_context, timeout=20)
                    try:
                        connection.connect()
                        tls_versions.append(connection.sock.version())
                        connection.request(method, path, json.dumps(body) if body is not None else None, headers)
                        response = connection.getresponse()
                        result.append((response.status, dict(response.getheaders()), json.loads(response.read())))
                    except Exception as error:
                        result.append((599, {}, {'refusal': type(error).__name__}))
                    finally:
                        connection.close()
                thread = threading.Thread(target=request)
                thread.start()
                server.handle_request()
                thread.join(25)
                got = result[0] if result else (598, {}, {})
                replies.append(got)
                return got

            # Real registration, possession proof, steward enrollment, and passkey sign-in.
            browser = base / 'browser.pem'
            run(['openssl', 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256', '-out', str(browser)])
            der = run(['openssl', 'pkey', '-in', str(browser), '-pubout', '-outform', 'DER']).stdout
            browser_id = b64(os.urandom(32))

            def assertion(challenge, user):
                client = json.dumps(dict(type='webauthn.get', challenge=challenge, origin=origin, crossOrigin=False)).encode()
                auth = hashlib.sha256(host.encode()).digest() + bytes([5, 0, 0, 0, 0])
                signature = run(['openssl', 'dgst', '-sha256', '-sign', str(browser)],
                                input=auth + hashlib.sha256(client).digest()).stdout
                return dict(credential_id=browser_id, client_data_json=b64(client), authenticator_data=b64(auth),
                            signature=b64(signature), user_handle=user)

            begin = call('POST', '/api/v1/auth/registration/begin', {'label': 'Scratch passkey'}, False)[2]
            made = dict(registration_id=begin['registration_id'], credential_id=browser_id, public_key=b64(der), algorithm=-7,
                        client_data_json=b64(json.dumps(dict(type='webauthn.create', challenge=begin['challenge'],
                                                             origin=origin, crossOrigin=False)).encode()))
            offered = call('POST', '/api/v1/auth/registration/credential', made, False)[2]
            possession = assertion(offered['possession_challenge'], begin['user_handle'])
            possession.pop('credential_id')
            call('POST', '/api/v1/auth/registration/possession', dict(possession, registration_id=begin['registration_id']), False)
            pending = json.loads((base / 'api-state/pending' / (begin['registration_id'] + '.json')).read_text())
            command = SA.CR.enrollment_command(pending, 'owner', A.next_id('passkey'))
            env = A.envelope(command, 'steward')
            accepted = service.apply(dict(command=command, envelope=env,
                                          signature=A.sign_as('steward', A.AC.canonical_envelope_bytes(env))), coordinates)
            challenge = call('POST', '/api/v1/auth/challenge', {}, False)[2]
            logged = call('POST', '/api/v1/auth/sign-in', assertion(challenge['challenge'], begin['user_handle']), False)
            session.update(Cookie=logged[1].get('Set-Cookie', '').split(';')[0])
            session['X-Veldo-Token'] = logged[2].get('csrf_token', '')
            ready = accepted.get('ok') and logged[0] == 200 and enrolled.get('outcome') == 'accepted'
            prefix = '/api/v1/domains/mcp-domain/mcp/'
            cv = getattr(judge, 'mcp_credentials', None)
            catalog = getattr(judge, 'catalog', None)
            SR = load('v144_secretref', mods / 'secretref.py')
            first_value, second_value = os.urandom(33).hex(), os.urandom(35).hex() + '\n'
            candidates = [first_value, second_value]
            command_audit = []
            if cv is not None:
                execute = cv.S.execute

                def audited_execute(conn, command, *args, **kwargs):
                    if command.get('operation') in ('set_mcp_credential', 'delete_mcp_credential'):
                        body = cv.S.canonical_bytes(command)
                        command_audit.append('value' not in command['parameters']
                                             and all(v.encode() not in body for v in candidates))
                    return execute(conn, command, *args, **kwargs)
                cv.S.execute = audited_execute

            def calls():
                return [json.loads(line) for line in (fake / 'calls').read_text().splitlines()] if (fake / 'calls').exists() else []

            def head():
                return A.conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]

            def data_of(kind):
                return [json.loads(row[0]) for row in A.conn.execute('SELECT data FROM entities WHERE kind=?', (kind,))]

            def resolve(ref):
                if cv is None or not isinstance(ref, str):
                    return None, 'missing_adapter'
                return attempt(lambda: SR.resolve_for_runtime(ref, cv.keystore))

            def absent_values():
                sys.stdout.flush()
                sys.stderr.flush()
                # Includes database, WAL, journal, proof directory, observations, signer state and API state.
                paths = [p for p in base.rglob('*') if p.is_file() and not p.name.startswith('item-')]
                paths += [p for p in (tree / 'proof/VELDO-0144').glob('*') if p.is_file()]
                # Closing an extra descriptor of SQLite's file in its own process drops
                # its POSIX locks. Audit bytes from a joined child instead.
                scanner = """import json, pathlib, sys
paths, values = json.load(sys.stdin)
for name in paths:
    try:
        content = pathlib.Path(name).read_bytes()
    except FileNotFoundError:
        continue
    if any(v.encode() in content for v in values):
        sys.exit(1)
"""
                done = subprocess.run([sys.executable, '-c', scanner],
                                      input=json.dumps([[str(p) for p in paths], candidates]).encode(),
                                      capture_output=True, timeout=15)
                buffered = [stream.getvalue() for stream in (sys.stdout, sys.stderr) if hasattr(stream, 'getvalue')]
                outputs = [v.encode() if isinstance(v, str) else v for v in process_outputs + buffered if v]
                return (done.returncode == 0 and all(v.encode() not in out for v in candidates for out in outputs)
                        and all(out in [b''] + [v.encode() for v in candidates] for out in lookup_outputs))

            commandline_checks = []

            def commandlines_safe():
                inspected = 0
                for path in Path('/proc').glob('[0-9]*/cmdline'):
                    try:
                        commandline = path.read_bytes()
                    except OSError:
                        continue
                    inspected += 1
                    if any(value.encode() in commandline for value in candidates):
                        return False
                return inspected > 0

            scan_results = []
            scanning = threading.Event()
            scanning.set()

            def watch():
                while scanning.is_set():
                    ok, why = attempt(absent_values)
                    scan_results.append(ok is True and why is None)
                    time.sleep(0.01)
            watcher = threading.Thread(target=watch)
            watcher.start()
            try:
                write = call('POST', prefix + 'credentials/set', dict(id='atlassian', label='Atlassian', base=0, value=first_value))
            finally:
                scanning.clear()
                watcher.join(5)
            ref = write[2].get('reference')
            handle, failure = resolve(ref)
            stored = data_of('credential')
            valid_write = ready and write[0] == 200
            check('credential/write', 'TLS passkey write stores only the five metadata fields and resolves through keychain',
                  valid_write and handle is not None and handle.reveal() == first_value and failure is None
                  and stored == [dict(id='atlassian', label='Atlassian', reference=ref, set_at=stored[0]['set_at'], set_by='owner')]
                  and isinstance(stored[0]['set_at'], (float, int)) and set(tls_versions) <= {'TLSv1.2', 'TLSv1.3'})
            check('credential/write', 'the opaque runtime handle prints only its reference',
                  handle is not None and first_value not in repr(handle) and first_value not in str(handle))
            for stage in ('written', 'replaced', 'deleted'):
                if stage == 'replaced':
                    changed = call('POST', prefix + 'credentials/set', dict(id='atlassian', label='Atlassian updated',
                                                                         base=1, value=second_value))
                    later, failure = resolve(ref)
                    check('credential/replace-delete', 'replacement keeps the reference and resolves only the new value',
                          valid_write and changed[0] == 200 and changed[2].get('reference') == ref
                          and later is not None and later.reveal() == second_value)
                if stage == 'deleted':
                    gone = call('POST', prefix + 'credentials/delete', dict(id='atlassian', base=2))
                    later, failure = resolve(ref)
                    check('credential/replace-delete', 'deletion clears the keystore item and runtime resolution refuses',
                          valid_write and gone[0] == 200 and later is None and failure == 'SecretError'
                          and not list(fake.glob('item-*')))
                    check('credential/deleted-state', 'deleted record carries a tombstone',
                          any(d.get('id') == 'atlassian' and d.get('deleted') is True for d in data_of('credential')))
                commandline_checks.append(commandlines_safe())
                refused = call('GET', prefix + 'credentials?id=atlassian')
                check('credential/read-back', stage + ': read-back is refused by name',
                      valid_write and refused[0] == 403 and refused[2].get('refusal') == 'unauthorized:credential_read_back')
            # Store a fresh value for the ordinary Atlassian catalog record.
            last = call('POST', prefix + 'credentials/set', dict(id='atlassian', label='Atlassian', base=3, value=second_value))
            ref = last[2].get('reference') or 'keychain:absent'
            check('credential/deleted-state', 'set after delete is a write and removes the tombstone',
                  last[0] == 200 and last[2].get('outcome') == 'written'
                  and all('deleted' not in d for d in data_of('credential')))
            handle, failure = resolve(ref)
            attrs = ['application', 'veldo', 'credential', ref.split(':', 1)[1]]
            lookup = subprocess.run([str(program), 'lookup'] + attrs, input=b'', capture_output=True)
            wrong = subprocess.run([str(program), 'lookup', 'application', 'other'] + attrs[2:], input=b'', capture_output=True)
            subset = subprocess.run([str(program), 'lookup'] + attrs[2:], input=b'', capture_output=True)
            unlabeled = subprocess.run([str(program), 'store'] + attrs, input=b'', capture_output=True)
            check('credential/libsecret-protocol', 'lookup preserves a real newline, matches all attributes, and store requires label',
                  valid_write and handle is not None and handle.reveal() == second_value
                  and lookup.stdout == second_value.encode() and wrong.returncode == 1 and not wrong.stdout
                  and subset.stdout == second_value.encode() and unlabeled.returncode != 0
                  and all(c['argv'][2:4] == ['application', 'veldo'] for c in calls() if c['action'] == 'store' and c['bytes']))
            before_encoding = head()
            bad_encoding = call('POST', prefix + 'credentials/set',
                                dict(id='encoding', label='encoding', base=0, value=chr(0xd800)))
            check('credential/encoding', 'invalid Unicode refuses by name, writes nothing and records an API observation',
                  bad_encoding[0] == 400 and bad_encoding[2].get('refusal') == 'invalid_input:credential_encoding'
                  and head() == before_encoding
                  and 'invalid_input:credential_encoding' in json.dumps(api.observations))

            def definition(identity, transport, label):
                return dict(id=identity, label=label, transport=transport, command='/usr/bin/mcp' if transport == 'stdio' else None,
                            arguments=['serve', 'jira'] if transport == 'stdio' else [],
                            url='https://localhost/mcp' if transport == 'http' else None,
                            environment={'MODE': {'literal': 'read'}, 'ACCESS': {'reference': ref}},
                            headers={'Authorization': {'reference': ref}} if transport == 'http' else {},
                            hosts=['linux', 'mac'], read_only_tools=['jira.search', 'jira.get'])

            definitions, saves = {}, []
            for transport in ('stdio', 'http'):
                identity = 'local' if transport == 'stdio' else 'atlassian'
                versions = []
                for number in (1, 2):
                    doc = definition(identity, transport, transport + ' version ' + str(number))
                    if number == 2:
                        doc.update(hosts=['linux'], read_only_tools=['jira.get'])
                        doc['environment']['MODE'] = {'literal': 'owner-selected'}
                        if transport == 'stdio':
                            doc.update(command='/usr/local/bin/mcp', arguments=['jira'])
                        else:
                            doc['url'] = 'https://localhost/revised/mcp'
                    saved = call('POST', prefix + 'catalog/save', dict(definition=doc, base=number - 1))
                    saves.append(saved)
                    versions.append(dict(doc, revision=number))
                    check('catalog/' + transport, 'every field of revision ' + str(number) + ' round trips through API and SQLite',
                          saved[0] == 200 and saved[2].get('revision') == number
                          and call('GET', prefix + 'catalog?server=' + identity + '&revision=' + str(number))[2].get('server')
                          == dict(doc, revision=number) and dict(doc, revision=number) in data_of('mcp_server'))
                definitions[identity] = versions
            history = data_of('mcp_server')
            check('catalog/immutable-history', 'both revisions of both transports survive byte for byte after the later save',
                  len(history) == 4 and all(doc in history for versions in definitions.values() for doc in versions)
                  and all(call('GET', prefix + 'catalog?server=' + identity + '&revision=1')[2].get('server') == docs[0]
                          for identity, docs in definitions.items()))
            check('catalog/atlassian', 'Atlassian is an ordinary http definition with its reference resolvable in the keystore',
                  last[0] == 200 and definitions['atlassian'][1] in history and resolve(ref)[0] is not None
                  and set(definitions['atlassian'][1]) == {'id', 'revision', 'label', 'transport', 'command', 'arguments',
                                                         'url', 'environment', 'headers', 'hosts', 'read_only_tools'})

            def host_command(operation, params, who='owner', signature_as=None, command_id=None):
                cmd = dict(A.ids, command_id=command_id or A.next_id('host-mcp'), operation=operation, principal=who, parameters=params)
                return service.apply(A.signed_command(signature_as or who, cmd), coordinates)

            for transport in ('stdio', 'http'):
                for number in (1, 2):
                    doc = definition('host-' + transport, transport, 'host revision ' + str(number))
                    answer = host_command('save_mcp_server', dict(definition=doc, base=number - 1))
                    check('catalog/host-command', transport + ' host-signed authority command stores revision ' + str(number),
                          answer.get('ok') and dict(doc, revision=number) in data_of('mcp_server'))
            before = head()
            stale = call('POST', prefix + 'catalog/save', dict(definition=definition('local', 'stdio', 'stale'), base=0))
            unauthorized = host_command('save_mcp_server', dict(definition=definition('intruder', 'stdio', 'refuse'), base=0), 'pm')
            forged = host_command('save_mcp_server', dict(definition=definition('forged', 'stdio', 'refuse'), base=0),
                                  signature_as='pm')
            check('catalog/stale-unauthorized', 'stale, unauthorized and forged saves refuse by name and write nothing',
                  all(s[0] == 200 for s in saves) and stale[0] == 409 and stale[2].get('refusal', '').startswith('stale_version')
                  and unauthorized.get('reason') == 'unauthorized:mcp_owner'
                  and forged.get('reason') == 'unauthorized:mcp_signature' and head() == before)
            malformed = []
            for field, value in (('transport', 'connector'), ('command', None), ('hosts', []),
                                 ('headers', {'Authorization': {'literal': first_value}}),
                                 ('environment', {'ACCESS': {'reference': 'env:ambient'}}), ('extra', True)):
                doc = definition('bad', 'stdio', 'invalid')
                doc[field] = value
                result = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                malformed.append(result[0] == 400 and result[2].get('refusal', '').startswith('invalid_input:server'))
            check('catalog/invalid', 'invalid transports, fields and value/reference shapes store no definition',
                  saves[0][0] == 200 and all(malformed) and head() == before)

            # The probe used API_TOKEN for ordinary data. Use CONFIG so position and content are distinct.
            ordinary = [
                ('uuid cloudId', 'environment', ('5c04fb27-13f8-4d0f-ae1' 'b-be13e14a815a')),
                ('atlassian url', 'url', ('https://mcp.atlassian.' 'com/v1/sse')),
                ('long public api path', 'url', ('https://api.github.com' '/repos/bcengi-engineer' 'ing/veldo-dark-factory' '/contents')),
                ('filesystem server args', 'arguments', ['-y', ('@modelcontextprotocol/' 'server-filesystem'), ('/home/dmitry/projects/' 'veldo-worktrees')]),
                ('allowed dirs flag', 'arguments', ['-' * 2 + ('allowed-directories=/h' 'ome/dmitry/projects/my' 'day/research/codex-rev' 'iews')]),
                ('google sheet id', 'environment', ('1BxiMVs0XRA5nFMdKvBdBZ' 'jgmUUqptlbs74OgvE2upms')),
                ('google drive folder id', 'environment', ('1A2B3C4D5E6F7G8H9I0JKL' 'mnopQRstuvWX')),
                ('git sha repo pin', 'environment', ('6e1c725f63d18cf78e9a9c' '974aa108800abd656d')),
                ('github node id', 'environment', 'R_kgDOJ7x2lQ'),
                ('aws region/arn', 'environment', ('arn:aws:iam::123456789' '012:role/VeldoMcpReadO' 'nlyRole')),
                ('jira cloud id url', 'url', ('https://api.atlassian.' 'com/ex/jira/5c04fb27-1' '3f8-4d0f-ae1b-be13e14a' '815a/rest/api/3')),
                ('confluence space path', 'url', ('https://bcengi.atlassi' 'an.net/wiki/spaces/COE' '/pages/295862273/Ava-R' 'esearch')),
                ('npm scoped package with version', 'arguments', ['-y', ('@atlassian/mcp-atlassi' 'an-remote-server@1.4.2')]),
                ('docker image digest', 'arguments', ['run', ('ghcr.io/github/github-' 'mcp-server@sha256:0000' '0000000000000000000000' '0000000000000000000000' '0000000000000001')]),
                ('SSH public key fingerprint', 'environment', ('SHA256:uNiVztksCsDhcc0' 'u9e8BujQXVUpKZIDTMczCv' 'j3tD2s')),
                ('public ed25519 key', 'environment', ('ssh-ed25519 AAAAC3NzaC' '1lZDI1NTE5AAAAIOMqqnkV' 'zrm0SdG6UOoqKLsabgH5C9' 'okWi0dh2l9GKJl')),
                ('base64 json config', 'environment', ('eyJtb2RlIjogInJlYWQiLC' 'AicHJvamVjdCI6ICJDRU8i' 'fQ==')),
                ('webflow collection id', 'environment', ('6811521ddca74f46536b11' '3b')),
                ('long snake env value', 'environment', ('bcengi_production_read' 'only_reporting_warehou' 'se')),
                ('mixed case path segment', 'arguments', ['-' * 2 + ('config=/home/dmitry/.c' 'onfig/VeldoFactory/Mcp' 'Servers/AtlassianReadO' 'nly.json')]),
                ('worktree path', 'arguments', [('/home/dmitry/projects/' 'veldo-worktrees/build-' 'veldo-0144')]),
                ('mac application support', 'arguments', [('/Users/dmitry/Library/' 'Application Support/Ve' 'ldo')]),
                ('confluence REST URL', 'url', ('https://api.atlassian.' 'com/ex/confluence/5c04' 'fb27-13f8-4d0f-ae1b-be' '13e14a815a/wiki/rest/a' 'pi')),
            ]
            generated = os.urandom(12).hex()
            absolute = '/home/config/' + generated + '/sa.json'
            ordinary += [
                ('author flag', 'arguments', ['-' * 2 + 'author', generated]),
                ('token file flag', 'arguments', ['-' * 2 + 'token-file', absolute]),
                ('bare auth before flag', 'arguments', ['-' * 2 + 'no-auth', '-' * 2 + 'port', str(int.from_bytes(os.urandom(2)))]),
                ('absolute credential argument', 'arguments', ['-' * 2 + 'api-key', absolute]),
                ('home credential argument', 'arguments', ['-' * 2 + 'token=~/' + generated]),
            ]
            for name in ('GIT_AUTHOR_NAME', 'OAUTH_CALLBACK_PORT', 'GOOGLE_APPLICATION_CREDENTIALS_FILE',
                         'SORT_ORDER', 'AUTHOR', 'OAUTH'):
                ordinary.append((name, 'environment', {name: {'literal': generated}}))
            for value in (absolute, '~/' + generated + '/sa.json'):
                ordinary.append(('absolute credential environment', 'environment',
                                 {'GOOGLE_APPLICATION_CREDENTIALS': {'literal': value}}))
            for suffix in ('file', 'path', 'dir', 'name', 'port', 'url', 'host', 'id', 'callback'):
                name = 'token_' + suffix
                ordinary.append((name, 'environment', {name: {'literal': generated}}))
                ordinary.append((name, 'arguments', ['-' * 2 + name + '=' + generated]))
                ordinary.append((name, 'url', 'https://localhost/mcp?' + name + '=' + generated))
            for name in ('SIG', 'signature', 'code', 'author', 'oauth'):
                ordinary.append((name, 'url', 'https://localhost/mcp?' + name + '=' + generated))
            ordinary.append(('absolute credential query', 'url', 'https://localhost/mcp?token=' + absolute))
            for index, (label, field, value) in enumerate(ordinary):
                doc = definition('ordinary-' + str(index), 'http' if field == 'url' else 'stdio', label)
                doc[field] = {'CONFIG': {'literal': value}} if field == 'environment' and isinstance(value, str) else value
                saved = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                check('catalog/ordinary-config-saves', label + ' saves every field exactly',
                      saved[0] == 200 and saved[2].get('revision') == 1
                      and dict(doc, revision=1) in data_of('mcp_server')
                      and call('GET', prefix + 'catalog?server=' + doc['id'] + '&revision=1')[2].get('server')
                      == dict(doc, revision=1))

            position_names = ('apiToken', 'client_secret_value', 'Password', 'service_passwd', 'vendor_apikey',
                              'api_key', 'privateKey', 'accessKey', 'api.key', 'PASS', 'credentials', 'auth',
                              'service_KEY', 'service_PAT', 'pwd', 'bearer', 'cookie', 'credential', 'APIKey')
            doc = definition('credential-references', 'stdio', 'Named references')
            doc['environment'] = {name: {'reference': ref} for name in position_names}
            doc['arguments'] = ['-' * 2 + 'password']  # A bare flag without a following item holds no value.
            # Unrecognized literals elsewhere are the trusted owner's choice, even when they have high entropy.
            doc['environment']['CONFIG'] = {'literal': b64(os.urandom(48))}
            saved = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
            check('catalog/ordinary-config-saves', 'named references and an ordinary random literal save exactly',
                  saved[0] == 200 and dict(doc, revision=1) in data_of('mcp_server')
                  and call('GET', prefix + 'catalog?server=' + doc['id'] + '&revision=1')[2].get('server')
                  == dict(doc, revision=1))

            def refusal_has_no_value(field, value, reason):
                observations = getattr(catalog, 'observations', [])
                record = observations[-1] if observations else {}
                log = state / 'observations.jsonl'
                logged = [json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []
                return (any(all(event.get(key) == record.get(key) for key in
                                ('command_id', 'field', 'refusal', 'server', 'outcome')) for event in logged)
                        and record.get('field') == field and record.get('refusal') == reason
                        and record.get('outcome') == 'refused' and record.get('server') is None
                        and value not in json.dumps(observations)
                        and log.is_file() and value not in log.read_text())

            before = head()
            position_values = [os.urandom(size).hex() for size in (32, 33, 16, 3)]
            position_cases = []
            for index, name in enumerate(position_names):
                value = position_values[index % len(position_values)]
                position_cases.append(('environment', {name: {'literal': value}}))
                flag = '-' * 2 + name.replace('_', '-')
                position_cases.append(('arguments', [flag + '=' + value]))
                position_cases.append(('arguments', [flag, value]))
                position_cases.append(('url', 'https://localhost/mcp?' + name + '=' + value))
            for name in ('key', '%61pi%5Ftoken'):
                position_cases.append(('url', 'https://localhost/mcp?' + name + '=' + position_values[0]))
            position_cases += [('url', 'https://user:' + position_values[0] + '@localhost/mcp'),
                               ('url', 'https://user@localhost/mcp'),
                               ('url', 'https://localhost/mcp?key='),
                               ('arguments', ['-' * 2 + 'token=']),
                               ('headers', {'Authorization': {'literal': position_values[0]}}),
                               ('headers', {'x-api-key': {'literal': position_values[1]}})]
            store_attempts = []
            if catalog is not None:
                store_execute = catalog.S.execute

                def observe_catalog_execute(conn, command, *args, **kwargs):
                    store_attempts.append(command.get('operation'))
                    return store_execute(conn, command, *args, **kwargs)
                catalog.S.execute = observe_catalog_execute
            try:
                for index, (field, value) in enumerate(position_cases):
                    doc = definition('position-' + str(index), 'http' if field in ('url', 'headers') else 'stdio',
                                     'Credential position')
                    doc[field] = value
                    refused = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                    check('catalog/credential-position-refused', field + ' case ' + str(index) + ' refuses before the store',
                          refused[0] == 400 and refused[2].get('refusal') == 'invalid_input:server_credential_position'
                          and head() == before and not store_attempts
                          and not any(d['id'] == doc['id'] for d in data_of('mcp_server')))
                    check('catalog/refusal-no-value', field + ' position refusal records field and reason',
                          all(refusal_has_no_value(field, candidate, 'invalid_input:server_credential_position')
                              for candidate in position_values))
            finally:
                if catalog is not None:
                    catalog.S.execute = store_execute

            shaped = 'gh' + 'p_' + os.urandom(18).hex()
            for shape in ('environment', 'arguments', 'url', 'id', 'label', 'command', 'hosts', 'read_only_tools',
                          'environment-name', 'header-name', 'reference'):
                doc = definition('literal-' + shape, 'http' if shape in ('url', 'header-name') else 'stdio', 'refuse literal')
                if shape == 'environment':
                    doc[shape]['CONFIG'] = {'literal': shaped}
                elif shape in ('arguments', 'hosts', 'read_only_tools'):
                    doc[shape] = [shaped]
                elif shape == 'url':
                    doc[shape] += '?ordinary=' + shaped
                elif shape == 'environment-name':
                    doc['environment'][shaped] = {'literal': 'read'}
                elif shape == 'header-name':
                    doc['headers'][shaped] = {'reference': ref}
                elif shape == 'reference':
                    doc['environment']['CONFIG'] = {'reference': 'keychain:' + shaped}
                else:
                    doc[shape] = shaped
                refused = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                check('catalog/known-shape-refused', shape + ' is refused before any write',
                      refused[0] == 400 and refused[2].get('refusal') == 'invalid_input:server_credential_literal'
                      and head() == before and not any(d['id'] == doc['id'] for d in data_of('mcp_server')))
                field = {'environment-name': 'environment', 'header-name': 'headers',
                         'reference': 'environment'}.get(shape, shape)
                check('catalog/refusal-no-value', shape + ' refusal records only field and reason',
                      refusal_has_no_value(field, shaped, 'invalid_input:server_credential_literal'))
                if shape == 'id':
                    host_refused = host_command('save_mcp_server', dict(definition=doc, base=0))
                    check('catalog/refusal-no-value', 'host id refusal records only field and reason',
                          host_refused.get('reason') == 'invalid_input:server_credential_literal'
                          and head() == before
                          and refusal_has_no_value('id', shaped, 'invalid_input:server_credential_literal'))
            known_shapes = [
                '-' * 5 + 'BEGIN ' + 'PRIVATE KEY' + '-' * 5,
                'sk' + '_live_' + os.urandom(12).hex(),
                'gh' + 'p_' + os.urandom(18).hex(),
                'xox' + 'b-' + os.urandom(12).hex(),
                'AK' + 'IA' + os.urandom(8).hex().upper(),
                'AI' + 'za' + os.urandom(18).hex()[:35],
                'ey' + 'J' + os.urandom(8).hex() + '.' + os.urandom(8).hex() + '.',
                'pass' + 'word=' + chr(34) + os.urandom(12).hex() + chr(34),
            ]
            for index, shaped in enumerate(known_shapes):
                doc = definition('provider-' + str(index), 'stdio', 'Provider shape')
                doc['environment']['CONFIG'] = {'literal': shaped}
                refused = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                check('catalog/known-shape-refused', 'known shape ' + str(index) + ' refuses by name without storage',
                      refused[0] == 400 and refused[2].get('refusal') == 'invalid_input:server_credential_literal'
                      and head() == before and not any(d['id'] == doc['id'] for d in data_of('mcp_server')))
            for field, value in (('environment', {'GOOGLE_APPLICATION_CREDENTIALS': {'literal': '/home/' + shaped}}),
                                 ('arguments', ['-' * 2 + 'token-file', '~/' + shaped])):
                doc = definition('shaped-path', 'stdio', 'Known shape in path')
                doc[field] = value
                refused = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                check('catalog/known-shape-refused', field + ' path still refuses known shapes',
                      refused[0] == 400 and refused[2].get('refusal') == 'invalid_input:server_credential_literal'
                      and head() == before)
            foreign = 'keychain:veldo/' + hashlib.sha256(('another-domain/atlassian').encode()).hexdigest()
            for bad_ref in (foreign, 'keychain:someone-elses-item'):
                doc = definition('foreign', 'http', 'refuse foreign reference')
                doc['headers']['Authorization'] = {'reference': bad_ref}
                refused = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                check('catalog/credential-domain', 'reference must belong to a credential recorded in this domain',
                      refused[0] == 400 and refused[2].get('refusal') == 'invalid_input:server_credential_reference'
                      and head() == before)
            replay_id = A.next_id('replay-value')
            replay_params = dict(id='replay', label='Replay', base=0, value=first_value)
            initial = host_command('set_mcp_credential', replay_params, command_id=replay_id)
            replay_head, replay_calls = head(), len(calls())
            same = host_command('set_mcp_credential', replay_params, command_id=replay_id)
            different = host_command('set_mcp_credential', dict(replay_params, value=second_value), command_id=replay_id)
            check('credential/replay-value', 'identical retry is idempotent; changed value refuses before touching keystore',
                  initial.get('ok') and same.get('ok') and different.get('reason') == 'command_content_conflict'
                  and head() == replay_head and len(calls()) == replay_calls)

            host_command('delete_mcp_credential', dict(id='replay', base=1))
            deleted_head = head()
            deleted_ref = next((d['reference'] for d in data_of('credential') if d['id'] == 'replay'), 'keychain:absent')
            for field, name in (('environment', 'API_TOKEN'), ('headers', 'Authorization')):
                doc = definition('deleted-' + field, 'http', 'Deleted reference')
                doc[field][name] = {'reference': deleted_ref}
                refused = call('POST', prefix + 'catalog/save', dict(definition=doc, base=0))
                check('catalog/deleted-reference', field + ' cannot reference tombstoned metadata',
                      refused[0] == 400 and refused[2].get('refusal') == 'invalid_input:server_credential_reference'
                      and head() == deleted_head and not any(d['id'] == doc['id'] for d in data_of('mcp_server')))
            recreate_id = A.next_id('recreate')
            recreated = host_command('set_mcp_credential', dict(replay_params, base=2), command_id=recreate_id)
            recreated_again = host_command('set_mcp_credential', dict(replay_params, base=2), command_id=recreate_id)
            check('credential/deleted-state', 'replaying a recreation preserves its written outcome',
                  recreated.get('result', {}).get('outcome') == 'written'
                  and recreated_again.get('result', {}).get('outcome') == 'written')

            # A valid session does not grant the owner's role forever, and neither version nor binding is advisory.
            before = head()
            stale = call('POST', prefix + 'credentials/set', dict(id='atlassian', label='stale', base=0, value=first_value))
            unauthorized = host_command('set_mcp_credential', dict(id='other', label='other', base=0, value=first_value), 'pm')
            unsigned = call('POST', prefix + 'credentials/set', dict(id='other', label='other', base=0, value=first_value), False)
            missing_csrf = call('POST', prefix + 'credentials/set', dict(id='other', label='other', base=0, value=first_value),
                                extra={'X-Veldo-Token': ''})
            packet = next((copy.deepcopy(p) for p in packets if p.get('assertion', {}).get('operation') == 'set_mcp_credential'), None)
            if packet is not None:
                packet['value'] = second_value
                tampered = Authority().apply(packet)
            else:
                tampered = {}
            check('credential/authority-binding', 'current role, base, passkey, forgery guard and signed value binding are enforced',
                  valid_write and stale[0] == 409 and unauthorized.get('reason') == 'unauthorized:mcp_owner'
                  and unsigned[0] == 401 and missing_csrf[0] == 403
                  and tampered.get('reason') == 'invalid_input:credential_binding' and head() == before)
            original_roles = A.CM.authority_state(A.S, A.conn)['entities']['owner']['data']['roles']
            A.admin('steward', 'change_roles', dict(principal='owner', roles=[]))
            no_role_head = head()
            no_role_server = call('POST', prefix + 'catalog/save',
                                  dict(definition=definition('no-role', 'stdio', 'No role'), base=0))
            no_role_value = call('POST', prefix + 'credentials/set',
                                 dict(id='no-role', label='No role', base=0, value=first_value))
            for row, answer in (('catalog/stale-unauthorized', no_role_server),
                                ('credential/authority-binding', no_role_value)):
                check(row, 'a live passkey session whose owner role was removed cannot write',
                      valid_write and answer[0] == 403 and answer[2].get('refusal') == 'unauthorized:mcp_owner'
                      and head() == no_role_head)
            A.admin('steward', 'change_roles', dict(principal='owner', roles=original_roles))
            before = head()
            for state_name in ('locked', 'unreachable'):
                (fake / 'mode').write_text(state_name)
                refused = call('POST', prefix + 'credentials/set', dict(id='blocked', label='blocked', base=0, value=first_value))
                check('credential/keystore-refusals', state_name + ' refuses by name, commits no record and has no fallback',
                      valid_write and refused[0] == 503
                      and refused[2].get('refusal') == 'unavailable_service:keystore_' + state_name and head() == before)
            (fake / 'mode').unlink()
            program.rename(fake / 'unavailable-tool')
            refused = call('POST', prefix + 'credentials/set', dict(id='blocked', label='blocked', base=0, value=first_value))
            check('credential/keystore-refusals', 'missing executable refuses without touching any real keystore',
                  valid_write and refused[0] == 503 and refused[2].get('refusal') == 'unavailable_service:keystore_unreachable'
                  and head() == before)
            (fake / 'unavailable-tool').rename(program)
            observed = calls()
            writes = [c for c in observed if c['action'] == 'store']
            check('credential/no-value-on-command-line', 'the fake reads the exact value from stdin and checks every live process argv',
                  valid_write and len(writes) >= 3 and any(c['input_digest'] == hashlib.sha256(first_value.encode()).hexdigest()
                                                         for c in writes)
                  and len(commandline_checks) == 3 and all(commandline_checks) and commandlines_safe()
                  and all(not c['exposed'] for c in observed)
                  and all(all(v not in json.dumps(c['argv']) for v in candidates) for c in observed))
            events = call('GET', '/api/v1/domains/mcp-domain/events?after=0')
            all_observations = [api.observations, judge.observations, signer.results, replies, events,
                                getattr(cv, 'observations', []), getattr(catalog, 'observations', [])]
            check('credential/no-value-in-records', 'during and after writes no value appears in store, journal, feed, proof or logs ' + str(
                      [valid_write, events[0], bool(scan_results), all(scan_results), absent_values(),
                       all(v not in json.dumps(all_observations) for v in candidates)]),
                  valid_write and events[0] == 200 and scan_results and all(scan_results) and absent_values()
                  and all(v not in json.dumps(all_observations) for v in candidates)
                  and command_audit and all(command_audit)
                  and all('value' not in row for row in data_of('credential')))
            cmetrics = cv.metrics() if cv is not None else {}
            mmetrics = catalog.metrics() if catalog is not None else {}
            check('catalog/observability', 'save and credential observations join actor, revision, session and command; metrics count operations',
                  mmetrics.get('revisions') == 9 + len(ordinary) and cmetrics.get('written') == 6 and cmetrics.get('replaced') == 1
                  and cmetrics.get('deleted') == 2 and len(cmetrics.get('refused', {})) >= 3
                  and any(r.get('session') and r.get('command_id') and r.get('actor') == 'owner' and r.get('revision') == 2
                          for r in getattr(catalog, 'observations', []))
                  and any(r.get('session') and r.get('command_id') and r.get('set_by') == 'owner'
                          for r in getattr(cv, 'observations', [])))
            scaffold = load('v144_scaffold', mods / 'init_scaffold.py')
            installed = ('control_mcp_catalog.py', 'control_credential.py', 'control_credential_keystore.py', 'secretref.py')
            closure, failure = attempt(CS.closure)
            check('install/assets', 'new runtime assets are installed, derive into the authority closure, and match engine copies',
                  failure is None and all('.veldo/' + n in scaffold._FILES and n in (closure or [])
                                         for n in installed if n != 'secretref.py')
                  and all((ROOT / '.veldo' / n).is_file() and (ROOT / 'engine/.veldo' / n).is_file()
                          and (ROOT / '.veldo' / n).read_bytes() == (ROOT / 'engine/.veldo' / n).read_bytes() for n in installed)
                  and not api.route_problems())
        except Exception as exc:
            # A harness error is a failed assertion and named as raised, never accepted as a red proof.
            for name in names:
                check(name, 'the row ran to its end (it raised ' + type(exc).__name__ + ')', False)
        finally:
            subprocess.Popen = original_popen
            sys.stdout.flush()
            sys.stderr.flush()
            for fd, saved, capture in zip((1, 2), saved_fds, captures):
                os.dup2(saved, fd)
                os.close(saved)
                capture.close()
            if server is not None:
                server.server_close()
            if ing is not None:
                ing.conn.close()
            if fixture is not None:
                fixture.conn.close()
            if lock is not None:
                os.close(lock)
            for name, value in original.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
    for name, checks in rows.items():
        bad = [label for label, passed in checks if not passed]
        expect('VELDO-0144 ' + name, bool(checks) and not bad)
        if bad:
            print('VELDO-0144 detail: ' + name + ': ' + '; '.join(bad))


_v144_suite()
