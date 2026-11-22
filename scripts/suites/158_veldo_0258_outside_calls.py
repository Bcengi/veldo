"""VELDO-0258: real HTTP authentication, accepted Git trees and a fixture landing.

No timing assertions: response completion and subprocess completion synchronize
the rows. Every subprocess deadline is a 120-second hang detector.
"""


def _v258_suite():
    import base64
    import contextlib
    import http.server
    import importlib.util
    import io
    import json
    import multiprocessing
    import os
    from pathlib import Path
    import secrets
    import shutil
    import subprocess
    import sys
    import tempfile
    import threading
    from types import SimpleNamespace
    from unittest.mock import patch

    PRODUCTION = {
        'control_plane_calls.py': ROOT / ".veldo" / "control_plane_calls.py",
        'control_plane_scan.py': ROOT / ".veldo" / "control_plane_scan.py",
        'tracker.py': ROOT / ".veldo" / "tracker.py",
        'tracker_intake.py': ROOT / ".veldo" / "tracker_intake.py",
        'control_installation_schema.py': ROOT / ".veldo" / "control_installation_schema.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def check(row, ok):
        expect('VELDO-0258 ' + row, bool(ok))

    def refusal(call):
        try:
            call()
        except Exception as error:
            return getattr(error, 'code', str(error))
        return None

    with tempfile.TemporaryDirectory(prefix='v258-') as temporary:
        root = Path(temporary)
        mods = root / 'modules'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__', '*.db', '*.sqlite3'))
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        CP = load('v258_calls', mods / 'control_plane_calls.py')
        TR = load('v258_tracker', mods / 'tracker.py')
        RN = load('v258_runner', mods / 'tracker_mirror_runner.py')
        JI = load('v258_init', mods / 'tracker_jira_init.py')
        DB = load('v258_doorbell', mods / 'request_doorbell.py')
        IN = load('v258_ingress', mods / 'control_channel_ingress.py')
        CR = load('v258_creation', mods / 'control_repository_creation.py')
        SC = load('v258_scan', mods / 'control_plane_scan.py')
        C = load('v258_config', mods / 'control_installation_config.py')
        values = {caller: 'canary-' + secrets.token_hex(24) for caller in
                  ('tracker', 'tracker_init', 'doorbell', 'provisioner', 'owner_channel', 'landing_push')}
        keystore = root / 'keystore.json'
        keystore.write_text(json.dumps(values))
        binaries = root / 'bin'
        binaries.mkdir()
        tool = binaries / 'secret-tool'
        tool.write_text('#!' + sys.executable + '\nimport json,sys\nfrom pathlib import Path\n'
                        + 'values=json.loads(Path(' + repr(str(keystore)) + ').read_text())\n'
                        + "sys.stdout.write(values[sys.argv[-1]])\n")
        tool.chmod(0o700)
        observed, authenticated = [], []

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.do_GET()

            def do_GET(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                header = self.headers.get('Authorization', '')
                for caller, value in values.items():
                    basic = base64.b64encode(('owner@example.com:' + value).encode()).decode()
                    if header in ('Bearer ' + value, 'Basic ' + basic) or ('/bot' + value + '/') in self.path:
                        authenticated.append(caller)
                failed = self.path == '/failure'
                if self.path == '/commit-changes':
                    self.server.commit_change()
                reply = (values['tracker'].encode() if failed else json.dumps({'ok': True,
                         'result': {'message_id': 1, 'date': 1, 'chat': {'id': 123}, 'text': 'Notice'},
                         'body_bytes': len(body)}).encode())
                self.send_response(401 if failed else 200)
                self.send_header('Content-Length', str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        origin = 'http://127.0.0.1:%d' % server.server_address[1]
        try:
            with patch.dict(os.environ, PATH=str(binaries) + os.pathsep + os.environ.get('PATH', ''),
                            VELDO_INSTALLATION=str(root / 'installation')):
                def entry(ref):
                    return {'trackers': {'fixture': {'kind': 'jira-cloud', 'base_url': origin,
                            'email': 'owner@example.com', 'token_ref': ref}}}

                constructors = {
                    'tracker': lambda ref: RN.build_live_adapter(entry(ref)),
                    'tracker_init': lambda ref: JI.build_live_provisioner(entry(ref)),
                    'doorbell': lambda ref: DB.TelegramSink(123, ref),
                    'provisioner': lambda ref: CR.GitHub(origin, CR.token({'api_token': ref}), timeout=120),
                    'owner_channel': lambda ref: IN.organ('control_channel_projection').TelegramEdge(
                        origin, IN.service_token({'bot_api': {'token_ref': ref}}), timeout=120),
                }
                def authenticate(caller, instance):
                    if caller in ('tracker', 'tracker_init'):
                        with instance.trace('VELDO-0258'):
                            instance._request('GET', '/fixture')
                    elif caller == 'doorbell':
                        instance.ORIGIN = origin
                        instance.send('Notice', None)
                    elif caller == 'provisioner':
                        instance.call('GET', '/fixture')
                    else:
                        instance.send(123, 'Notice')

                with CP.service('a' * 40, observed.append):
                    for caller, construct in constructors.items():
                        instance = construct('keychain:' + caller)
                        authenticate(caller, instance)
                        if caller in ('tracker', 'tracker_init'):
                            check('observability/unit/' + caller, observed[-1].get('unit_id') == 'VELDO-0258')
                        check('ac1/authenticates/' + caller, caller in authenticated)
                        for scheme, ref in [('env', 'env:CANARY258'), ('file', 'file:CANARY258'),
                                            ('literal', values[caller]), ('literal', 'literal:' + values[caller])]:
                            before = len(authenticated)
                            with patch.dict(os.environ, CANARY258=values[caller]):
                                # With the old resolver restored, this really authenticates
                                # using the environment canary, as AC1's falsifier states.
                                code = refusal(lambda: authenticate(caller, construct(ref)))
                            label = 'literal-tagged' if ref.startswith('literal:') else scheme
                            check('ac1/refuses/' + caller + '/' + label,
                                  code == 'invalid_input:control_plane_credential:' + caller + ':' + scheme
                                  and len(authenticated) == before)
                    check('ac1/no-canary-in-observations', all(value not in json.dumps(observed)
                          for value in values.values()))
                    check('observability/calls', all({'host', 'caller', 'operation', 'result', 'latency',
                          'installation_commit', 'dispatch_id'} <= set(row)
                          and row['installation_commit'] == 'a' * 40
                          for row in observed if 'operation' in row))
                    code = refusal(lambda: RN.build_live_adapter(entry('keychain:tracker'))._request('GET', '/failure'))
                    check('observability/failed-body-private', code == 'unavailable_service:control_plane_call:tracker'
                          and values['tracker'] not in json.dumps(observed))
                    check('observability/counts', CP.metrics()['calls'].get('tracker:failed', 0) >= 1
                          and all(CP.metrics()['credential_refusals'].get(scheme, 0) >= len(constructors)
                                  for scheme in ('env', 'file', 'literal')))
                    changing_commit = ['a' * 40]
                    server.commit_change = lambda: changing_commit.__setitem__(0, 'b' * 40)
                    with CP.service(lambda: changing_commit[0], observed.append):
                        RN.build_live_adapter(entry('keychain:tracker'))._request('GET', '/commit-changes')
                    check('observability/commit-pinned', changing_commit[0] == 'b' * 40
                          and observed[-1]['installation_commit'] == 'a' * 40)
                # Exec cannot inherit the memory binding; a run marker refuses even an existing service binding.
                for caller, construct in constructors.items():
                    check('ac3/service-required/' + caller, refusal(lambda: construct('keychain:' + caller))
                          == 'unauthorized:control_plane_service:' + caller)
                    with patch.dict(os.environ, VELDO_DISPATCH_ID='dispatch/fixture'):
                        check('ac3/run-refused/' + caller, refusal(lambda: construct('keychain:' + caller))
                              == 'unauthorized:control_plane_run:' + caller)
                # A child inherits memory on fork, but not the parent's process authority.
                context = multiprocessing.get_context('fork')
                parent_pipe, child_pipe = context.Pipe(duplex=False)
                def child_attempt():
                    parent_pipe.close()
                    child_pipe.send(refusal(lambda: CP.credential('tracker', 'keychain:tracker')))
                    child_pipe.close()
                with CP.service('a' * 40, observed.append):
                    child = context.Process(target=child_attempt)
                    child.start()
                    child_pipe.close()
                    child.join(timeout=120)
                    ended = not child.is_alive()
                    if not ended:
                        child.terminate()
                        child.join(timeout=120)
                    code = parent_pipe.recv() if ended and parent_pipe.poll() else None
                    parent_pipe.close()
                    check('ac3/fork-does-not-inherit', ended and child.exitcode == 0
                          and code == 'unauthorized:control_plane_service:tracker')

                # Real Git transport into a disposable bare remote. The fixture substitutes only
                # the approved GitHub URL's wire, after resolving the real keystore reference.
                P = load('v258_provisioner', mods / 'control_repository_provisioner.py')
                transport = P._git_process.identity_transport()
                work, remote = root / 'work', root / 'remote.git'
                def git(*args):
                    return subprocess.run(['git', *map(str, args)], check=True, capture_output=True,
                                          text=True, timeout=120).stdout.strip()
                git('init', '-q', '--initial-branch=main', work)
                git('init', '-q', '--bare', remote)
                gate_called = root / 'gate-called'
                gate_hook = work / '.git/hooks/pre-push'
                gate_hook.write_text('#!' + sys.executable + '\nfrom pathlib import Path\nPath('
                                     + repr(str(gate_called)) + ').touch()\nraise SystemExit(1)\n')
                gate_hook.chmod(0o700)
                git('-C', work, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.com',
                    'commit', '-q', '--allow-empty', '-m', 'Fixture landing')
                tip = git('-C', work, 'rev-parse', 'HEAD')
                record = {'push_credential': {'kind': 'token', 'reference': 'keychain:landing_push'}}
                def fixture_options(identity, destination):
                    check('ac3/landing-keystore', transport.credential(identity) == values['landing_push'])
                    return ['-c', 'protocol.file.allow=always']
                with patch.object(P, 'STEP_SECONDS', 120), \
                        patch.object(P._git_process, 'identity_transport', return_value=transport), \
                        patch.object(transport, 'options', side_effect=fixture_options), \
                        CP.service('a' * 40, observed.append, dispatch='fixture-landing'):
                    landed = P.push(dict(path=str(work), default_branch='main', remote=str(remote),
                                         base_commit='', scaffold_commit=tip), record)
                check('ac3/landing-outside-gate', landed == tip
                      and git('--git-dir', remote, 'rev-parse', 'refs/heads/main') == tip and not gate_called.exists())
                check('observability/landing-dispatch', any(row.get('caller') == 'landing_push'
                      and row.get('dispatch_id') == 'fixture-landing' for row in observed))

                # Real loader, Git object tree and signed SQLite record; malformed routing refuses whole.
                S = load('v258_store', mods / 'control_store.py')
                SIG = load('v258_signer', mods / 'control_signer.py')
                private = root / 'journal'
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private)],
                               check=True, capture_output=True, timeout=120)
                sign = lambda body: SIG.sign_bytes(private, body, 'veldo-journal')
                conn = S.open_store(root / 'store.sqlite3')
                try:
                    repo = C.I.Repository.create(root / 'installation')
                    identity = {'name': 'Fixture Owner', 'email': 'owner@example.com'}
                    routing = {'schema': 'veldo.tracker/v1', 'routing': {'mechanism': 'label', 'label_prefix': 'repo:'},
                               'repos': [{'id': 'example', 'tracker': 'fixture', 'project': 'EX'}],
                               'trackers': entry('keychain:tracker')['trackers']}
                    settings = {'schema': 'veldo.installation/v1', 'git': {'branch': 'main'},
                                'tracker_routing': routing,
                                'doorbell': {'chat_id': 123, 'origin': origin, 'token_ref': 'keychain:doorbell'}}
                    first = repo.commit({'installation.yaml': json.dumps(settings).encode()}, None, identity, 'Routing')
                    repo.publish(first, None)
                    loader = C.Loader(S, conn, repo, domain='fixture', workflow_repository='fixture',
                                      signer='setup', sign=sign, secret_exists=lambda name: name in values,
                                      observe=observed.append)
                    accepted = loader.reconcile(bootstrap=True)
                    (mods / 'trackers.json').write_text('{}')
                    (root / 'installation' / 'installation.yaml').write_text('{}')
                    check('ac2/accepted-site', accepted['outcome'] == 'accepted'
                          and TR.load_tracker_config(repo_root=str(root), path=str(mods / 'trackers.json')) == routing)
                    with CP.service(lambda: loader.accepted_commit, observed.append):
                        check('ac2/accepted-route-authenticates', refusal(lambda: RN.build_live_adapter(
                            TR.load_tracker_config())._request('GET', '/accepted-site')) is None)
                        DB.TelegramSink.from_installation().send('Accepted target', None)
                        # Real command signatures and runtime routing. Only the authority's
                        # membership projection is a fixture; the command judge and preview run.
                        TS = load('v258_tracker_service', mods / 'control_tracker_service.py')
                        membership = TS.organ('control_membership')
                        authority = dict(membership=[dict(principal='owner', principal_type='person',
                                                          roles=['project_owner'], scope=['fixture'])],
                                         keyring=[dict(principal='owner', public_key=Path(str(private) + '.pub').read_text().strip())])
                        command = dict(operation='tracker_call', domain_uuid='fixture', store_uuid='fixture',
                                       repository_uuid='fixture', principal='owner', command_id='preview', expires_at=1300,
                                       parameters=dict(action='mirror', tracker='fixture', dry_run=True))
                        packet = dict(command=command, signature=SIG.sign_bytes(private, S.canonical_bytes(command), 'veldo-command'))
                        service = SimpleNamespace(conn=conn, domain='fixture', store='fixture', repositories={'fixture': [str(work)]})
                        organ = TS.organ
                        with patch.object(TS, 'organ', side_effect=lambda name: membership if name == 'control_membership' else organ(name)), \
                                patch.object(membership, 'authority_state', return_value=authority), \
                                patch.object(TS.time, 'time', return_value=1000):
                            answer = TS.execute(service, packet, 'fixture')
                            print('VELDO-0258 signed command:', answer)
                            check('ac3/signed-service-command', answer['ok'])
                            packet['command'] = dict(command, parameters=dict(action='init', tracker='fixture', dry_run=False))
                            check('ac3/tampered-command-refused', TS.execute(service, packet, 'fixture') ==
                                  {'ok': False, 'reason': 'unauthorized:tracker_call'})
                    check('observability/effect-provenance', CP.effect_commit({'store': str(root / 'store.sqlite3')}) == first)
                    effect_configuration = {'store': str(root / 'store.sqlite3')}
                    with CP.service(first, CP.effect_observer(effect_configuration), dispatch='fixture-effect'):
                        effect_code = refusal(lambda: RN.build_live_adapter(TR.load_tracker_config())._request('GET', '/durable-effect'))
                        refusal(lambda: CP.credential('tracker', 'literal:' + values['tracker']))
                    effect_text = CP.effect_log(effect_configuration).read_text()
                    effect_rows = [json.loads(line) for line in effect_text.splitlines()]
                    check('observability/effect-log', effect_code is None and len(effect_rows) == 2
                          and effect_rows[0]['installation_commit'] == first
                          and effect_rows[0]['dispatch_id'] == 'fixture-effect'
                          and all(value not in effect_text for value in values.values()))
                    check('observability/effect-counters', CP.effect_metrics(effect_configuration) ==
                          {'calls': {'tracker:ok': 1}, 'credential_refusals': {'literal': 1}})
                    bad = json.loads(json.dumps(settings))
                    bad['tracker_routing']['trackers']['fixture']['base_url'] = 'malformed site'
                    second = repo.commit({'installation.yaml': json.dumps(bad).encode()}, first, identity, 'Bad routing')
                    repo.publish(second, first)
                    rejected = loader.reconcile()
                    check('ac2/malformed-whole', rejected['outcome'] == 'refused'
                          and any(p.startswith('installation_invalid:') for p in rejected['problems'])
                          and loader.accepted_commit == first and TR.load_tracker_config() == routing)
                    before = len(authenticated)
                    with CP.service(lambda: loader.accepted_commit, observed.append):
                        code = refusal(lambda: RN.build_live_adapter(TR.load_tracker_config())._request('GET', '/previous-still-live'))
                    check('ac2/previous-still-live', code is None and len(authenticated) == before + 1
                          and observed[-1]['installation_commit'] == first)
                finally:
                    conn.close()
                check('ac1/no-canary-in-store', all(value.encode() not in (root / 'store.sqlite3').read_bytes()
                      for value in values.values()))
                check('ac2/template-no-site', not json.loads((ROOT / 'engine/.veldo/trackers.json').read_text())['trackers'])
                problems = SC.findings(ROOT / 'engine')
                print('VELDO-0258 register findings:', problems)
                check('ac3/register', problems == [])
                planted = mods / 'unregistered.py'
                planted.write_text('from urllib.request import urlopen as send\ndef planted():\n    send("https://example.com")\n')
                check('ac3/planted-call', 'control_plane_call_unregistered:unregistered.py' in SC.findings(mods))
                tree = root / 'engine-scan'
                shutil.copytree(mods, tree / '.veldo')
                (tree / 'scripts').mkdir()
                shutil.copyfile(planted, tree / 'scripts/unregistered.py')
                check('ac3/planted-script', 'control_plane_call_unregistered:scripts/unregistered.py' in SC.findings(tree))
                check('ac1/no-canary-in-records', all(value not in json.dumps(observed) for value in values.values()))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=120)
            check('fixture/server-joined', not thread.is_alive())


_v258_suite()
