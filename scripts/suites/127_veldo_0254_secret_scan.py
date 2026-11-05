"""VELDO-0254: credentials never enter runs, a secret scan reports leaked ones masked, the confined runner is opt-in.

Run: python3 scripts/selftest.py --suite 127_veldo_0254_secret_scan

Only shared ROOT, expect and fast_temp are consumed. Copies the checkout's .veldo into scratch with the production
copies (PRODUCTION) laid over it and loads the scan module and the launcher from there. AC1: the static row lists
every place the launch modules build a run's configuration, environment or command and names any that resolves a
keystore reference or reads a credential (the checkout, and a scratch copy with one planted); the canary row scans
a fixture run's files, environment and command line for canary credentials. AC2: the one scan entry over a fixture
workspace at run end, a landing candidate's changed files, a project tree on the owner's command and at setup,
masked findings, the engine login fixture, reports only. AC3: the one launcher decision, a default run reaching a
fixture database on host loopback (TCP and its Unix socket) and a fixture service on a local address, a risky run
started in the confined runner (scripts/agent_sandbox.py), and a host without the runner's helper. Starts only
loopback fixture servers and child processes; writes only temporary files.
"""


def _v254_suite():
    import ast
    import base64
    import hashlib
    import http.server
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import threading

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'secret_scan.py': ROOT / ".veldo" / "secret_scan.py",
        'secret_scan_patterns.json': ROOT / ".veldo" / "secret_scan_patterns.json",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_launch_work.py': ROOT / ".veldo" / "control_launch_work.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
    }
    SANDBOX = ROOT / 'scripts' / 'agent_sandbox.py'
    SANDBOX_CONFIG = ROOT / 'scripts' / 'agent_sandbox.json'
    # The one launch path VELDO-0158 opened into a run, which VELDO-0257 removes (proof/VELDO-0254/OPEN.md). The
    # static row accepts no other site, and this one only while it is still there.
    PENDING_0257 = {'credential_delivery_site:control_launch.py:Receiver._spawn'}
    ROWS = ('ac1/static-sites', 'ac1/static-planted', 'ac1/canary-run', 'ac2/run-end', 'ac2/landing',
            'ac2/command', 'ac2/setup', 'ac2/masked', 'ac2/login', 'ac2/reports-only', 'ac2/one-entry',
            'ac3/default-reaches', 'ac3/risky-confined', 'ac3/no-runner-host', 'ac3/one-decision')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def canary():
        # Random, upper case and digits: no six characters of it occur in a log by chance.
        return 'CANARY' + base64.b32encode(os.urandom(25)).decode().rstrip('=')

    def leaks(text, value, width=6):
        return [value[at:at + width] for at in range(len(value) - width + 1) if value[at:at + width] in text]

    def tree(directory, files):
        for name, text in files.items():
            path = Path(directory) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

    def digests(directory):
        return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(Path(directory).rglob('*')) if p.is_file()}

    def functions(path):
        """{qualified name: node} of every module-level function and method of `path`."""
        found = {}
        for node in ast.parse(Path(path).read_text()).body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[node.name] = node
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        found[node.name + '.' + item.name] = item
        return found

    def calls(node):
        names = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call):
                func = sub.func
                if isinstance(func, ast.Attribute):
                    names.add(func.attr)
                elif isinstance(func, ast.Name):
                    names.add(func.id)
        return names

    temp = tempfile.mkdtemp(prefix='v254-', dir=fast_temp())
    servers = []
    try:
        base = Path(temp)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if source.is_file():
                shutil.copyfile(source, mods / name)
        SS = load('v254_secret_scan', mods / 'secret_scan.py')
        L = load('v254_launch', mods / 'control_launch.py')

        # AC1, the static row over the checkout's launch modules.
        report = SS.delivery_sites(mods)
        sites = set(report['sites'])
        check('ac1/static-sites', 'the row lists the places a run is built (spawn, containment, wrapper, engine '
              'protocol builders) [%s]' % sorted(sites)[:8],
              {'control_launch.py:Receiver._spawn', 'control_launch.py:Receiver._contained', 'control_launch.py:wrap',
               'control_engine_claude.py:command', 'control_engine_claude.py:environment',
               'control_engine_claude.py:baseline', 'control_engine_codex.py:command',
               'control_engine_codex.py:environment', 'control_engine_codex.py:baseline'} <= sites)
        check('ac1/static-sites', 'no launch site resolves a keystore reference or reads a credential, but the '
              'VELDO-0158 one VELDO-0257 removes [%s]' % sorted(set(report['findings']) - PENDING_0257),
              set(report['findings']) <= PENDING_0257)
        check('ac1/static-sites', 'each finding is a named credential_delivery_site',
              all(f.startswith('credential_delivery_site:') for f in report['findings']))

        planted = base / 'planted'
        shutil.copytree(mods, planted)
        source = (planted / 'control_launch.py').read_text()
        anchor = "    runtime = environment.pop(ENGINE_RUNTIME, None)\n"
        source = source.replace(anchor, anchor + "    environment['FIXTURE_TOKEN'] = _organ('secretref').resolve_for_runtime("
                                "'keychain:fixture', _organ('control_credential_keystore').SecretService()).reveal()\n", 1)
        (planted / 'control_launch.py').write_text(source)
        planted_report = SS.delivery_sites(planted)
        check('ac1/static-planted', 'a keystore reference resolved into a run\'s environment is named by its site [%s]'
              % planted_report['findings'],
              'credential_delivery_site:control_launch.py:engine_environment' in planted_report['findings'])
        check('ac1/static-planted', 'the plant changed only that site',
              set(planted_report['findings']) - set(report['findings'])
              == {'credential_delivery_site:control_launch.py:engine_environment'})

        # AC1, the canary row over one fixture run: its workspace and scratch files, its environment, its command.
        services = {'fixture-mail': canary(), 'fixture-tracker': canary()}
        run = base / 'run'
        tree(run / 'workspace', {'README.md': 'a fixture project\n', 'src/app.py': 'print(1)\n'})
        tree(run / 'scratch', {'notes.txt': 'scratch\n'})
        environment = {'PATH': '/usr/bin:/bin', 'HOME': str(run / 'scratch')}
        argv = ['engine', '--print', 'build it']

        def run_files(environment, argv):
            files = list(SS.tree_files(run / 'workspace')) + [('scratch/' + n, b) for n, b in SS.tree_files(run / 'scratch')]
            files.append(('environment', ''.join('%s=%s\n' % kv for kv in sorted(environment.items())).encode()))
            files.append(('command', '\n'.join(argv).encode()))
            return files
        clean = SS.scan('run_end', 'fixture', run_files(environment, argv), held=services.values())
        check('ac1/canary-run', 'a run built without credentials holds no canary in its files, environment or '
              'command [%s]' % [f['file'] for f in clean['findings']], clean['findings'] == [])
        leaked = dict(environment, FIXTURE_MAIL_TOKEN=services['fixture-mail'])
        dirty = SS.scan('run_end', 'fixture', run_files(leaked, argv + [services['fixture-tracker']]),
                        held=services.values())
        check('ac1/canary-run', 'a canary resolved into the environment or the command is found there [%s]'
              % [(f['file'], f['kind']) for f in dirty['findings']],
              sorted(f['file'] for f in dirty['findings']) == ['command', 'environment'])

        # AC2: run end, through the launcher's run-end scan.
        held = canary()
        workspace = base / 'clone' / 'work'
        tree(workspace, {'config/service.json': '{\n  "url": "https://example.invalid",\n  "token": "%s"\n}\n' % held,
                         '.env': 'MODE=test\nSERVICE_TOKEN=%s\n' % held,
                         'scripts/deploy.sh': '#!/bin/sh\ncurl -H "Authorization: Bearer %s" "$URL"\n' % held,
                         'src/main.py': 'print("nothing here")\n'})
        logs = base / 'logs'
        logs.mkdir()
        notices = []

        def sink(text):
            notices.append(text)
            return 'notice-%d' % len(notices)
        config = {'store': str(base / 'authority' / 'control.sqlite3'), 'secret_scan_log': str(logs / 'scan.jsonl')}
        before = digests(workspace)
        ended = L.scan_run_end(config, 'dispatch-254', 'fixture', [workspace], held=[held], notify=sink)
        found = sorted((f['file'], f['line']) for f in ended['findings'])
        check('ac2/run-end', 'each occurrence in a config file, an environment file and a script is reported once '
              '[%s]' % found, found == [('.env', 2), ('config/service.json', 3), ('scripts/deploy.sh', 2)])
        check('ac2/run-end', 'each finding is secret_found:<kind> with the run-end trigger, the project and the '
              'dispatch', all(f['code'] == 'secret_found:' + f['kind'] and ended['trigger'] == 'run_end'
                              and ended['project'] == 'fixture' and ended['dispatch'] == 'dispatch-254'
                              for f in ended['findings']) and ended['findings'])
        lines = [json.loads(line) for line in (logs / 'scan.jsonl').read_text().splitlines()]
        check('ac2/run-end', 'one log line per finding and one summary line with the files read and the findings',
              len([x for x in lines if x.get('event') == 'secret_found']) == 3
              and [x for x in lines if x.get('event') == 'secret_scan'][-1].get('findings') == 3
              and [x for x in lines if x.get('event') == 'secret_scan'][-1].get('files') == 4)
        check('ac2/run-end', 'the owner notice names each finding, masked, and says to move it behind the gate',
              len(notices) == 1 and notices[0].count('secret_found:') == 3 and 'behind the outside gate' in notices[0]
              and all(x.get('notice') == 'notice-1' for x in lines if x.get('event') == 'secret_found'))
        check('ac2/reports-only', 'the scan edits no file of the workspace', digests(workspace) == before)

        # AC2: a landing candidate's changed files, before it lands.
        repo = base / 'repo'
        git = ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false',
               '-C', str(repo)]
        subprocess.run(['git', 'init', '-q', str(repo)], check=True, capture_output=True)
        tree(repo, {'README.md': 'base\n', 'old.txt': 'token %s\n' % held})
        subprocess.run(git + ['add', '-A'], check=True, capture_output=True)
        subprocess.run(git + ['commit', '-q', '-m', 'base'], check=True, capture_output=True)
        base_commit = subprocess.run(git + ['rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
        tree(repo, {'app/settings.py': 'API = "https://example.invalid"\nKEY = "%s"\n' % held, 'README.md': 'changed\n'})
        subprocess.run(git + ['add', '-A'], check=True, capture_output=True)
        subprocess.run(git + ['commit', '-q', '-m', 'candidate'], check=True, capture_output=True)
        head = subprocess.run(git + ['rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
        landing = SS.scan('landing_candidate', 'fixture', SS.candidate_files(repo, base_commit, head), held=[held],
                          log=logs / 'landing.jsonl')
        check('ac2/landing', 'a candidate that adds a canary is reported, and only its changed files are read [%s]'
              % [(f['file'], f['line']) for f in landing['findings']],
              [(f['file'], f['line']) for f in landing['findings']] == [('app/settings.py', 2)] and landing['files'] == 2)
        work = (mods / 'control_launch_work.py')
        collect = functions(work).get('Work._collect') or functions(work).get('_collect')
        collect = collect or next((node for name, node in functions(work).items() if name.endswith('._collect')), None)
        check('ac2/landing', 'the build collection scans the candidate before it can land',
              collect is not None and 'scan_candidate' in calls(collect))
        check('ac2/landing', 'the landing scan reads the candidate\'s changed files through the one entry',
              hasattr(L, 'scan_candidate'))

        # AC2: a project tree on the owner's command, a credential of a known format.
        project = base / 'project'
        known = 'ghp_' + ''.join('ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'[b % 54] for b in os.urandom(36))
        tree(project, {'deploy/ci.yml': 'steps:\n  - run: push\n    env:\n      TOKEN: %s\n' % known, 'README.md': 'hi\n'})
        command = subprocess.run([sys.executable, '-B', str(mods / 'secret_scan.py'), 'scan', '--project', 'fixture',
                                  '--root', str(project), '--log', str(logs / 'command.jsonl')],
                                 capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        check('ac2/command', 'the owner\'s command reports the known-format credential by kind, file and line [%s %s]'
              % (command.returncode, command.stdout.strip()[-200:]),
              command.returncode == 0 and 'secret_found:github_token' in command.stdout
              and 'deploy/ci.yml:4' in command.stdout)
        command_log = (logs / 'command.jsonl').read_text() if (logs / 'command.jsonl').is_file() else ''
        check('ac2/command', 'the command\'s scan is logged with its trigger',
              '"trigger": "command"' in command_log and '"github_token"' in command_log)

        # AC2: setup scans the workspace project tree through the same entry.
        setup_source = functions(mods / 'control_factory_setup.py')
        setup_scan = setup_source.get('scan_projects')
        check('ac2/setup', 'setup has one project-tree scan and both setup paths call it',
              setup_scan is not None and 'scan_projects' in calls(setup_source['scan_projects_reporting'])
              and 'scan_projects_reporting' in calls(setup_source['setup'])
              and 'scan_projects_reporting' in calls(setup_source['rerun']))
        if setup_scan is not None:
            FS = load('v254_setup', mods / 'control_factory_setup.py')
            state = base / 'state'
            state.mkdir()
            at_setup = FS.scan_projects({'root': str(state), 'workspace': str(project)}, held=[held])
            check('ac2/setup', 'setup reports the project tree\'s credential with the setup trigger [%s]'
                  % [(f['file'], f['kind']) for f in at_setup['findings']],
                  at_setup['trigger'] == 'setup'
                  and [(f['file'], f['kind']) for f in at_setup['findings']] == [('deploy/ci.yml', 'github_token')])

        # AC2: masking. No report, log line, notice or command output holds any six characters of a value.
        text = json.dumps([ended, landing, dirty]) + ''.join(notices) + command.stdout + command.stderr
        text += ''.join(p.read_text() for p in logs.glob('*.jsonl'))
        check('ac2/masked', 'no report, log line or notice holds any part of a canary [%s]' % leaks(text, held)[:3],
              not leaks(text, held) and not any(leaks(text, value) for value in services.values()))
        check('ac2/masked', 'nor of the known-format credential [%s]' % leaks(text, known[4:])[:3],
              not leaks(text, known[4:]))
        masked = ended['findings'][0]['masked'] if ended['findings'] else {}
        check('ac2/masked', 'the masked form is the kind, the length and a short digest',
              masked.get('kind') == ended['findings'][0]['kind'] and masked.get('length') == len(held)
              and masked.get('digest') == hashlib.sha256(held.encode()).hexdigest()[:12])

        # AC2: the engine's own model login in its usual place is not a finding; the same value elsewhere is.
        login = base / 'login'
        login_value = 'sk-ant-oat01-' + base64.b32encode(os.urandom(30)).decode().rstrip('=')
        tree(login, {'.claude/.credentials.json': '{"claudeAiOauth": {"accessToken": "%s"}}\n' % login_value,
                     '.codex/auth.json': '{"tokens": {"access_token": "%s"}}\n' % login_value})
        quiet = SS.scan('run_end', 'fixture', SS.tree_files(login))
        check('ac2/login', 'the engine login fixture is not reported [%s]' % [f['file'] for f in quiet['findings']],
              quiet['findings'] == [])
        tree(login, {'notes/pasted.txt': 'key %s\n' % login_value})
        pasted = SS.scan('run_end', 'fixture', SS.tree_files(login))
        check('ac2/login', 'the same value pasted elsewhere is reported [%s]' % [f['file'] for f in pasted['findings']],
              [f['file'] for f in pasted['findings']] == ['notes/pasted.txt'])

        # AC2: reports only. A finding stops nothing: the run-end scan returns, and the scan module edits, stops and
        # refuses nothing (it has no write, kill or refusal call).
        scan_calls = calls(ast.parse((mods / 'secret_scan.py').read_text()))
        check('ac2/reports-only', 'the scan module calls no file edit, process stop or refusal [%s]'
              % sorted(scan_calls & {'unlink', 'remove', 'rmtree', 'kill', 'killpg', 'write_text', 'write_bytes',
                                     'replace', 'rename', 'truncate'}),
              not (scan_calls & {'unlink', 'remove', 'rmtree', 'kill', 'killpg', 'write_text', 'write_bytes',
                                 'replace', 'rename', 'truncate'}))

        # AC2: one scan entry. The three triggers call it; no other module reports a found credential.
        launch_functions = functions(mods / 'control_launch.py')
        check('ac2/one-entry', 'the receiver\'s run end calls the run-end scan before the run directory goes',
              '_scan_workspace' in calls(launch_functions['Receiver._finish'])
              and 'scan_run_end' in calls(launch_functions['Receiver._scan_workspace'])
              and 'scan' in calls(launch_functions['scan_run_end'])
              and 'scan' in calls(launch_functions['scan_candidate']))
        reporters = sorted(p.name for p in mods.glob('*.py')
                           if p.name != 'secret_scan.py' and "'secret_found" in p.read_text())
        check('ac2/one-entry', 'no other module names secret_found [%s]' % reporters, not reporters)
        check('ac2/one-entry', 'the triggers are exactly run end, landing candidate, setup and command',
              tuple(SS.TRIGGERS) == ('run_end', 'landing_candidate', 'setup', 'command'))

        # AC3: fixture services. A database answering on host loopback, by TCP and by its Unix socket, and a service
        # on a local address (the host's own address when it has one, loopback otherwise).
        def answering(sock):
            def serve():
                while True:
                    try:
                        conn, _ = sock.accept()
                    except OSError:
                        return
                    with conn:
                        conn.sendall(b'PONG\n')
            threading.Thread(target=serve, daemon=True).start()
            servers.append(sock)
        tcp = socket.socket()
        tcp.bind(('127.0.0.1', 0))
        tcp.listen()
        answering(tcp)
        unix = socket.socket(socket.AF_UNIX)
        unix_path = str(base / 'db.sock')
        unix.bind(unix_path)
        unix.listen()
        answering(unix)
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(('192.0.2.1', 9))
            address = probe.getsockname()[0]
        except OSError:
            address = '127.0.0.1'
        finally:
            probe.close()

        class Page(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'public page')

            def log_message(self, *args):
                pass
        web = http.server.ThreadingHTTPServer((address, 0), Page)
        threading.Thread(target=web.serve_forever, daemon=True).start()
        servers.append(web)
        runs = base / 'runs'
        runs.mkdir()
        reach = runs / 'reach.py'
        reach.write_text('''import json, socket, sys, urllib.request
out = {}
try:
    with socket.create_connection(('127.0.0.1', int(sys.argv[1])), timeout=5) as s:
        out['tcp'] = s.recv(16).decode().strip()
except OSError as error:
    out['tcp'] = 'unreachable: %s' % error
try:
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(5)
    s.connect(sys.argv[2])
    out['unix'] = s.recv(16).decode().strip()
    s.close()
except OSError as error:
    out['unix'] = 'unreachable: %s' % error
try:
    out['web'] = urllib.request.urlopen(sys.argv[3], timeout=5).read().decode()
except Exception as error:
    out['web'] = 'unreachable: %s' % error
try:
    out['label'] = open('/proc/self/attr/current').read().strip()
except OSError:
    out['label'] = ''
print(json.dumps(out))
''')
        url = 'http://%s:%d/' % (address, web.server_address[1])
        probe_argv = ['python3', str(reach), str(tcp.getsockname()[1]), unix_path, url]

        def contract(context=None, project='fixture'):
            return {'reservation': {'project': project}, 'repository': project,
                    'input': {'context': dict(context or {})}}

        def started(argv):
            done = subprocess.run(argv, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
                                  cwd=str(runs))
            try:
                return json.loads(done.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                return {'exit': done.returncode, 'error': done.stderr.strip()[-300:]}

        runner_config = {'confined_runner': {'program': str(SANDBOX), 'config': str(SANDBOX_CONFIG)}}
        default = L.runner_decision(runner_config, contract())
        check('ac3/default-reaches', 'an unmarked launch takes the default runner [%s]' % default,
              default == {'runner': 'default', 'why': None})
        default_argv = L.runner_argv(runner_config, default, probe_argv, str(runs))
        check('ac3/default-reaches', 'the default runner starts the command as today, unwrapped',
              default_argv == probe_argv)
        seen = started(default_argv)
        check('ac3/default-reaches', 'a default run reaches the fixture database on host loopback by TCP and its '
              'socket, and the fixture service [%s]' % seen,
              seen.get('tcp') == 'PONG' and seen.get('unix') == 'PONG' and seen.get('web') == 'public page')

        # AC3: a run marked risky, by the installation, the project or the dispatch, starts in the confined runner.
        marks = [('installation', dict(runner_config, risky={'installation': True}), contract()),
                 ('project', dict(runner_config, risky={'projects': ['fixture']}), contract()),
                 ('dispatch', runner_config, contract({'risky': True}))]
        decided = [(why, L.runner_decision(config_, contract_)) for why, config_, contract_ in marks]
        check('ac3/risky-confined', 'each mark takes the confined runner and names why [%s]' % decided,
              all(decision == {'runner': 'confined', 'why': why} for why, decision in decided))
        check('ac3/risky-confined', 'another project\'s mark leaves this launch on the default runner',
              L.runner_decision(dict(runner_config, risky={'projects': ['other']}), contract())['runner'] == 'default')
        check('ac3/risky-confined', 'this host provides the confined runner [%s]' % L.confined_runner_problem(runner_config),
              L.confined_runner_problem(runner_config) is None)
        confined = L.runner_argv(runner_config, decided[2][1], probe_argv, str(runs))
        inside = started(confined)
        check('ac3/risky-confined', 'the risky run starts in the confined runner [%s]' % inside,
              'veldo-userns-child' in str(inside.get('label')) and confined[-len(probe_argv):] == probe_argv
              and confined != probe_argv)

        # AC3: a host without the confined runner's setup. A default run starts; a risky run is refused by name.
        missing = base / 'nohelper'
        missing.mkdir()
        shutil.copyfile(SANDBOX_CONFIG, missing / 'agent_sandbox.json')
        text = SANDBOX.read_text()
        text = text.replace("NAMESPACE_HELPER = Path('/usr/local/lib/veldo/veldo-userns')",
                            "NAMESPACE_HELPER = Path(%r)" % str(missing / 'absent' / 'veldo-userns'), 1)
        (missing / 'agent_sandbox.py').write_text(text)
        bare = {'confined_runner': {'program': str(missing / 'agent_sandbox.py'),
                                    'config': str(missing / 'agent_sandbox.json')}}
        problem = L.confined_runner_problem(bare)
        check('ac3/no-runner-host', 'the missing helper is a named problem [%s]' % problem,
              isinstance(problem, str) and problem.startswith('confined_runner_unavailable:'))
        check('ac3/no-runner-host', 'an installation with no confined runner configured has one too',
              str(L.confined_runner_problem({})).startswith('confined_runner_unavailable:'))
        seen_bare = started(L.runner_argv(bare, L.runner_decision(bare, contract()), probe_argv, str(runs)))
        check('ac3/no-runner-host', 'a default run there starts and reaches its services [%s]' % seen_bare,
              seen_bare.get('tcp') == 'PONG' and seen_bare.get('unix') == 'PONG')
        refusal = L.runner_refusal(bare, L.runner_decision(bare, contract({'risky': True})))
        check('ac3/no-runner-host', 'a risky run there is refused by name [%s]' % refusal,
              refusal == problem)
        check('ac3/no-runner-host', 'a default run there is never refused for a confinement reason',
              L.runner_refusal(bare, L.runner_decision(bare, contract())) is None)

        # AC3: one launcher decision for every launch kind (engine run, conversation turn, workflow step: every one
        # is accepted by Receiver.launch), and the spawn applies it.
        users = sorted(name for name, node in launch_functions.items() if 'runner_decision' in calls(node))
        check('ac3/one-decision', 'Receiver.launch is the one caller of the decision [%s]' % users,
              users == ['Receiver.launch'])
        check('ac3/one-decision', 'the spawn starts what the decision chose',
              'runner_argv' in calls(launch_functions['Receiver._spawn']))
        marked = sorted(name for name, node in launch_functions.items()
                        if any(isinstance(s, ast.Constant) and s.value == 'risky' for s in ast.walk(node)))
        check('ac3/one-decision', 'only the decision reads the risky mark [%s]' % marked,
              marked == ['runner_decision'])
    except Exception as error:
        for row in ROWS:
            check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:300], False)
    finally:
        for server in servers:
            try:
                (server.shutdown() if hasattr(server, 'shutdown') and not isinstance(server, socket.socket)
                 else server.close())
            except OSError:
                pass
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0254 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v254_suite()
