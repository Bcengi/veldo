"""VELDO-0254 AC3: a run marked risky starts in the confined runner, on a host that provides it.

Run: python3 scripts/selftest.py --suite 128_veldo_0254_confined_runner

Only shared ROOT, expect and fast_temp are consumed. Loads the launcher from a scratch copy of the checkout's .veldo
with its production copy (PRODUCTION) laid over it, takes the runner decision for a launch its dispatch marks risky,
and starts the argv the launcher gives it: the confined runner of VELDO-0208 (scripts/agent_sandbox.py with
scripts/agent_sandbox.json and the installed namespace helper) around a probe that reports its AppArmor label and
whether it reaches a fixture database's Unix socket. The confined runner nests no namespace inside the gate's own
confinement (the helper's root ownership is not visible there), so this suite is the one of VELDO-0254 that needs the
unconfined leg (proof/VELDO-0254/OPEN.md). Writes only temporary files.
"""


def _v254_confined_suite():
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import threading

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
    }
    SANDBOX = ROOT / 'scripts' / 'agent_sandbox.py'
    SANDBOX_CONFIG = ROOT / 'scripts' / 'agent_sandbox.json'
    ROWS = ('ac3/risky-starts-confined',)
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    temp = tempfile.mkdtemp(prefix='v254c-', dir=fast_temp())
    unix = None
    try:
        base = Path(temp)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        L = load('v254c_launch', mods / 'control_launch.py')
        unix = socket.socket(socket.AF_UNIX)
        unix_path = str(base / 'db.sock')
        unix.bind(unix_path)
        unix.listen()

        def serve():
            while True:
                try:
                    conn, _ = unix.accept()
                except OSError:
                    return
                with conn:
                    conn.sendall(b'PONG\n')
        threading.Thread(target=serve, daemon=True).start()
        runs = base / 'runs'
        runs.mkdir()
        probe = runs / 'probe.py'
        probe.write_text('''import json, socket, sys
out = {}
try:
    out['label'] = open('/proc/self/attr/current').read().strip()
except OSError:
    out['label'] = ''
try:
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(5)
    s.connect(sys.argv[1])
    out['unix'] = s.recv(16).decode().strip()
except OSError as error:
    out['unix'] = 'unreachable: %s' % error
print(json.dumps(out))
''')
        argv = ['python3', str(probe), unix_path]
        config = {'confined_runner': {'program': str(SANDBOX), 'config': str(SANDBOX_CONFIG)}}
        contract = {'reservation': {'project': 'fixture'}, 'repository': 'fixture', 'input': {'context': {'risky': True}}}
        decision = L.runner_decision(config, contract)
        check('ac3/risky-starts-confined', 'the dispatch mark takes the confined runner [%s]' % decision,
              decision == {'runner': 'confined', 'why': 'dispatch'})
        problem = L.confined_runner_problem(config)
        check('ac3/risky-starts-confined', 'this host provides the confined runner [%s]' % problem, problem is None)
        check('ac3/risky-starts-confined', 'so the risky launch is not refused', L.runner_refusal(config, decision) is None)
        done = subprocess.run(L.runner_argv(config, decision, argv, str(runs)), capture_output=True, text=True,
                              timeout=120, stdin=subprocess.DEVNULL, cwd=str(runs))
        try:
            seen = json.loads(done.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            seen = {'exit': done.returncode, 'error': done.stderr.strip()[-300:]}
        check('ac3/risky-starts-confined', 'the risky run starts in the confined runner [%s]' % seen,
              'veldo-userns-child' in str(seen.get('label')))
        check('ac3/risky-starts-confined', 'and is confined there: the host database socket a default run reaches is '
              'out of its reach [%s]' % seen.get('unix'), str(seen.get('unix', '')).startswith('unreachable'))
        default = subprocess.run(L.runner_argv(config, L.runner_decision(config, dict(contract, input={'context': {}})),
                                               argv, str(runs)), capture_output=True, text=True, timeout=120,
                                 stdin=subprocess.DEVNULL, cwd=str(runs))
        check('ac3/risky-starts-confined', 'while the same command unmarked reaches it [%s]' % default.stdout.strip(),
              '"unix": "PONG"' in default.stdout)
    except Exception as error:
        for row in ROWS:
            check(row, 'raised ' + type(error).__name__ + ': ' + str(error)[:300], False)
    finally:
        if unix is not None:
            unix.close()
        shutil.rmtree(temp, ignore_errors=True)

    for row, values in rows.items():
        failed = [label for label, ok in values if not ok]
        expect('VELDO-0254 ' + row + (': ' + failed[0] if failed else ''), bool(values) and not failed)


_v254_confined_suite()
