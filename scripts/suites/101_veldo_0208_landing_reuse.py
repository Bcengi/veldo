"""VELDO-0208: real inherited confinement and authenticated landing, no mutation stage."""


def _v208_worker_fixture(top, escaped):
    """A controlled candidate tree for authority workers: one fixture suite over one subject, and a
    candidate driver that touches `escaped` and claims a kill if it ever runs (it must not)."""
    import os
    import sys
    worker_root = top / 'worker-input'; worker_home = top / 'worker-home'
    (worker_root / 'scripts/suites').mkdir(parents=True)
    (worker_root / '.veldo').mkdir(); worker_home.mkdir()
    (worker_root / 'scripts/suites/shared.py').write_text(
        'from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\n'
        'def expect(name, condition): pass\n')
    worker_suite = worker_root / 'scripts/suites/fixture.py'
    worker_suite.write_text('value = (ROOT / ".veldo" / "subject.py").read_text()\n'
                           'expect("fixture target", value == "good")\n')
    (worker_root / '.veldo/subject.py').write_text('good')
    # An executable candidate driver would claim all mutants killed. It must never run.
    (worker_root / 'scripts/check_gate_mutations.py').write_text(
        'from pathlib import Path\nPath(' + repr(str(escaped)) + ').touch()\n'
        'print("forged killed record")\n')
    controlled_case = dict(identity='check_teeth_mutations.py:controlled', name='controlled',
        driver='check_teeth_mutations.py', suite='fixture.py', rows=['target'],
        module='subject.py', old='good', new='bad')
    def worker_argv(job):
        # The coordinator's ownership channel: an append descriptor to a file outside the home.
        channel = os.open(job.with_suffix('.ownership'), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        return [sys.executable, '-I', '-S', str(ROOT / 'scripts/reuse_worker.py'),
                'worker', str(worker_root), str(channel), str(job)], channel
    return worker_root, worker_home, worker_suite, controlled_case, worker_argv


def _v208_landing_reuse():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import socket
    from unittest.mock import patch

    def confined_run(*args, **kwargs):
        """Start the launcher or a worker directly, as the authority does: with /dev/null for stdin
        unless a row names another. The boundary refuses a socket on a standard descriptor, so a row
        must not depend on what stdin the suite itself was started with."""
        kwargs.setdefault('stdin', subprocess.DEVNULL)
        return subprocess.run(*args, **kwargs)

    def load(relative):
        spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    E = load('.veldo/reuse_evidence.py')
    R = load('scripts/gate_reuse.py')
    C = load('scripts/case_reuse.py')
    landing = load('engine/.veldo/control_verification.py')
    gate = load('scripts/check_gate_mutations.py')
    sys.path.insert(0, str(ROOT / 'scripts'))
    try:
        reducer = load('scripts/reuse_stamp.py')
    finally:
        sys.path.pop(0)
    with patch.dict(os.environ, {}, clear=True):
        expect('VELDO-0208 landing/explicit-default-mode',
               landing.gate_env().get('VELDO_GATE_FORCE_FRESH') == '0')
    with patch.dict(os.environ, {'VELDO_GATE_FORCE_FRESH': '1'}):
        expect('VELDO-0208 landing/explicit-force-mode',
               landing.gate_env()['VELDO_GATE_FORCE_FRESH'] == '1')
    expect('VELDO-0208 spec/ready-contract',
           V.check_spec(ROOT / 'specs/VELDO-0208-single-user-landing-reuse.md') == 0)
    with tempfile.TemporaryDirectory(prefix='landing-reuse-') as temporary:
        top = Path(temporary)
        worktree, storepath, runner = top / 'worktree', top / 'store', top / 'runner.sh'
        worktree.mkdir()
        runner.write_text('trusted runner')
        store = R.Store(storepath, worktree)
        config = top / 'config.json'
        policy = {'schema': 'veldo.agent-sandbox/v1', 'store': str(storepath),
                  'read_roots': json.loads((ROOT / 'scripts/agent_sandbox.json').read_text())['read_roots'],
                  'write_roots': ['{worktree}', '{scratch}'], 'deny_write': [str(runner)],
                  'seed_files': {}}
        config.write_text(json.dumps(policy))
        command = [sys.executable, '-I', '-S', str(ROOT / 'scripts/agent_sandbox.py'),
                   '--config', str(config), '--worktree', str(worktree), '--']
        probe = worktree / 'probe.py'
        # Each sub-process runs sequentially, and checks actual kernel denials.
        probe.write_text('''import errno, fcntl, json, os, pathlib, socket, subprocess, sys
store, runner, authority, inherited = map(pathlib.Path, sys.argv[1:])
results = {}
def denied(name, operation):
 try:
  operation()
 except OSError as error:
  results[name] = error.errno in (errno.EACCES, errno.EPERM, errno.EBADF, errno.EXDEV)
 else:
  results[name] = False
denied('store-read', lambda: list(store.iterdir()))
denied('key-read', lambda: (store / 'authentication.key').read_bytes())
denied('key-write', lambda: (store / 'authentication.key').write_text('forged'))
denied('plant-record', lambda: (store / 'planted.json').write_text('forged'))
denied('replace-store', lambda: store.rename(store.with_name('stolen')))
denied('runner-write', lambda: runner.write_text('forged'))
denied('runner-replace', lambda: runner.unlink())
denied('authority-write', lambda: authority.write_text('forged'))
denied('inherited-fd', lambda: os.write(int(str(inherited)), b'forged'))
pathlib.Path('key-link').symlink_to(store / 'authentication.key')
denied('symlink-key-read', lambda: pathlib.Path('key-link').read_bytes())
denied('symlink-key-write', lambda: pathlib.Path('key-link').write_text('forged'))
denied('hardlink-key', lambda: os.link(store / 'authentication.key', 'key-hardlink'))
denied('unix-service', lambda: socket.socket(socket.AF_UNIX))
def connect_service(path):
 with socket.socket(socket.AF_UNIX) as client: client.connect(path)
denied('user-bus', lambda: connect_service('/run/user/' + str(os.getuid()) + '/bus'))
denied('systemd-private', lambda: connect_service('/run/user/' + str(os.getuid()) + '/systemd/private'))
with socket.create_connection(('127.0.0.1', int(os.environ['VELDO_TEST_PORT'])), timeout=2):
 results['network-ipv4'] = True
with socket.socket(socket.AF_INET6): results['network-ipv6'] = True
for name in ('ssh', 'v1-store', 'v1-key', 'codex-auth', 'claude-credentials'):
 denied('private-' + name, lambda name=name: pathlib.Path(os.environ['VELDO_TEST_PRIVATE'], name).read_bytes())
denied('terminal-injection', lambda: fcntl.ioctl(0, 0x5412, b'x'))
for name, code in [
 ('child-read', 'from pathlib import Path; Path(' + repr(str(store / 'authentication.key')) + ').read_bytes()'),
 ('child-plant', 'from pathlib import Path; Path(' + repr(str(store / 'child.json')) + ').write_text("forged")'),
 ('child-runner', 'from pathlib import Path; Path(' + repr(str(runner)) + ').write_text("forged")')]:
 child = subprocess.run([sys.executable, '-I', '-S', '-c', code], capture_output=True)
 results[name] = child.returncode != 0 and b'PermissionError' in child.stderr
pathlib.Path('edited').write_text('allowed')
pathlib.Path(os.environ['HOME'], 'private-state').write_text('allowed')
results['own-worktree'] = pathlib.Path('edited').read_text() == 'allowed'
results['private-home'] = pathlib.Path(os.environ['HOME'], 'private-state').read_text() == 'allowed'
print(json.dumps(results))
''')
        # A newly planted candidate suite imports its own reuse code and attempts
        # publication through the exact authority entry used by the gate catalog.
        import shutil
        (worktree / 'scripts').mkdir()
        (worktree / '.veldo').mkdir()
        for relative in ('scripts/case_reuse.py', 'scripts/mutation_reuse.py',
                         'scripts/gate_reuse.py', 'scripts/case_inputs.py', '.veldo/reuse_evidence.py'):
            shutil.copyfile(ROOT / relative, worktree / relative)
        planted = worktree / 'scripts/planted_suite.py'
        planted.write_text("import case_reuse, pathlib\n"
            "store = case_reuse.R.Store(" + repr(str(storepath)) + ", pathlib.Path.cwd())\n"
            "assert store.put('f' * 64, {'mutant': 'killed'}), 'store publication denied'\n")
        planted_result = subprocess.run([sys.executable, '-I', '-S',
            str(ROOT / 'scripts/gate_candidate.py'), '--root', str(worktree), '--',
            sys.executable, str(planted)], env=dict(os.environ, VELDO_AGENT_CONFIG=str(config)),
            capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 candidate/planted-suite-publication-red',
               planted_result.returncode != 0 and 'store publication denied' in planted_result.stderr
               and 'store-denied domain' in planted_result.stderr
               and not (storepath / ('f' * 64 + '.json')).exists())
        # Replacing the worker entry cannot run before the authority installs confinement.
        worker_source = (ROOT / 'scripts/check_gate_mutations.py').read_text()
        expect('VELDO-0208 candidate/authority-launches-worker',
               "str(ROOT / 'scripts/reuse_worker.py')" in worker_source
               and "str(worker_root / 'scripts/check_gate_mutations.py')" not in worker_source)
        listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(4)
        private_home = top / 'private-home'; private_home.mkdir()
        for name in ('ssh', 'v1-store', 'v1-key', 'codex-auth', 'claude-credentials'):
            (private_home / name).write_text('private fixture')
        network_env = dict(os.environ, VELDO_TEST_PORT=str(listener.getsockname()[1]),
                           VELDO_TEST_PRIVATE=str(private_home))
        keyfd = os.open(storepath / 'authentication.key', os.O_RDWR)
        before = (storepath / 'authentication.key').read_bytes()
        # The probe's stdin is a real terminal, so terminal-injection always tries TIOCSTI on one.
        terminal, terminal_peer = os.openpty()
        try:
            result = confined_run(command + [sys.executable, '-I', '-S', str(probe), str(storepath),
                str(runner), str(ROOT / 'scripts/agent_sandbox.py'), str(keyfd)],
                pass_fds=(keyfd,), stdin=terminal_peer, capture_output=True, text=True, timeout=20,
                env=network_env)
        finally:
            os.close(keyfd)
            os.close(terminal)
            os.close(terminal_peer)
        expect('VELDO-0208 sandbox/launcher-starts: ' + result.stderr[-400:], result.returncode == 0)
        findings = json.loads(result.stdout) if result.returncode == 0 else {}
        for name in ('store-read', 'key-read', 'key-write', 'plant-record', 'replace-store',
                     'runner-write', 'runner-replace', 'authority-write', 'inherited-fd',
                     'symlink-key-read', 'symlink-key-write', 'hardlink-key', 'unix-service', 'user-bus', 'systemd-private',
                     'network-ipv4', 'network-ipv6', 'private-ssh', 'private-v1-store', 'private-v1-key',
                     'private-codex-auth', 'private-claude-credentials', 'terminal-injection',
                     'child-read', 'child-plant', 'child-runner', 'own-worktree', 'private-home'):
            expect('VELDO-0208 sandbox/' + name, findings.get(name) is True)
        expect('VELDO-0208 sandbox/store-and-runner-intact',
               (storepath / 'authentication.key').read_bytes() == before
               and runner.read_text() == 'trusted runner' and not (storepath / 'planted.json').exists())
        worker_network = """import ctypes, importlib.util, pathlib, socket, sys
spec = importlib.util.spec_from_file_location('boundary', sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.landlock([(pathlib.Path(p).resolve(), m.READ) for p in ('/usr','/lib','/lib64','/etc')], profile='worker')
for family, address in [(socket.AF_INET, ('127.0.0.1', int(sys.argv[2]))),
                        (socket.AF_UNIX, '/run/user/' + str(__import__('os').getuid()) + '/bus')]:
 try:
  with socket.socket(family) as client: client.connect(address)
 except PermissionError: pass
 else: raise AssertionError('worker connected to service')
"""
        worker_result = subprocess.run([sys.executable, '-I', '-S', '-c', worker_network,
            str(ROOT / 'scripts/agent_sandbox.py'), str(listener.getsockname()[1])],
            capture_output=True, text=True, timeout=20)
        listener.close()
        expect('VELDO-0208 profiles/worker-denies-tcp-and-user-bus: ' + worker_result.stderr[-300:],
               worker_result.returncode == 0)
        defaults = json.loads((ROOT / 'scripts/agent_sandbox.json').read_text())
        expect('VELDO-0208 sandbox/default-no-broad-home-or-tmp',
               '~' not in defaults['read_roots'] and '/tmp' not in defaults['read_roots'])
        # Kernel failure is injected at the syscall boundary, before exec. No root needed.
        unavailable = '''import importlib.util, sys
spec = importlib.util.spec_from_file_location('sandbox', sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class Kernel:
 def syscall(self, *args): return -1
m.ctypes.CDLL = lambda *args, **kwargs: Kernel()
sys.argv = [sys.argv[1], *sys.argv[2:]]
sys.exit(m.main())
'''
        marker = worktree / 'must-not-start'
        result = confined_run([sys.executable, '-I', '-S', '-c', unavailable,
            str(ROOT / 'scripts/agent_sandbox.py'), '--config', str(config), '--worktree', str(worktree),
            '--', sys.executable, '-c', 'open(' + repr(str(marker)) + ', "w").close()'],
            capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/unavailable-refuses-before-exec', result.returncode == 2
               and 'Landlock unavailable' in result.stderr and not marker.exists())
        obsolete = unavailable.replace('return -1', 'return 5')
        result = confined_run([sys.executable, '-I', '-S', '-c', obsolete,
            str(ROOT / 'scripts/agent_sandbox.py'), '--config', str(config), '--worktree', str(worktree),
            '--', sys.executable, '-c', 'open(' + repr(str(marker)) + ', "w").close()'],
            capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/old-abi-refuses-before-exec', result.returncode == 2
               and 'needs Landlock ABI 6' in result.stderr and not marker.exists())
        bad_policy = dict(policy, write_roots=[str(top)])
        bad_config = top / 'bad-config.json'; bad_config.write_text(json.dumps(bad_policy))
        bad = command[:]; bad[bad.index(str(config))] = str(bad_config)
        result = confined_run(bad + ['/usr/bin/true'], capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/unsafe-config-refuses',
               result.returncode == 2 and 'unsafe writable path' in result.stderr)
        credential = top / 'credential-link'
        credential.symlink_to(storepath / 'authentication.key')
        bad_policy = dict(policy, seed_files={str(credential): '.codex/auth.json'})
        bad_config.write_text(json.dumps(bad_policy))
        scratch_parent = top / 'scratch-owner'; scratch_parent.mkdir()
        result = confined_run(bad + ['/usr/bin/true'], capture_output=True, text=True, timeout=20,
                                env=dict(os.environ, TMPDIR=str(scratch_parent)))
        expect('VELDO-0208 sandbox/refusal-cleans-scratch', not list(scratch_parent.iterdir()))
        expect('VELDO-0208 sandbox/credential-alias-cannot-copy-key',
               result.returncode == 2 and 'seed exposes the reuse store' in result.stderr)

        # Agents never write the shared repository: each works in a linked worktree of its own bare
        # repository (objects private, the shared store a read-only alternate), may move only
        # refs/heads/agent/<id>/..., and its work enters the shared repository only through a fetch
        # that re-hashes every object. Commit through the actual launcher.
        main = top / 'git-main'
        linked = top / 'git-agent'
        def git_at(path, *args):
            return subprocess.check_output(['/usr/bin/git', '-C', str(path),
                '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args],
                stderr=subprocess.PIPE).decode().strip()
        def plant_remap(gitdir, victim, forged):
            """Plant a pack in `gitdir` whose index names the existing object `victim` but whose
            bytes are `forged`: the store then answers `victim` with other content."""
            def git_dir(*args, data=None):
                return subprocess.run(['/usr/bin/git', '--git-dir=' + str(gitdir), *args], input=data,
                                      capture_output=True, check=True).stdout
            replacement = git_dir('hash-object', '-w', '--stdin', data=forged).decode().strip()
            with tempfile.TemporaryDirectory(prefix='remap-') as scratch:
                name = git_dir('pack-objects', '-q', str(Path(scratch) / 'pack'),
                               data=(replacement + '\n').encode()).decode().strip()
                index = bytearray((Path(scratch) / ('pack-' + name + '.idx')).read_bytes())
                assert index[:8] == b'\xfftOc\x00\x00\x00\x02' and int.from_bytes(index[1028:1032], 'big') == 1
                first = bytes.fromhex(victim)
                for byte in range(256):
                    index[8 + 4 * byte:12 + 4 * byte] = int(byte >= first[0]).to_bytes(4, 'big')
                index[1032:1032 + len(first)] = first
                (Path(scratch) / ('pack-' + name + '.idx')).chmod(0o644)
                (Path(scratch) / ('pack-' + name + '.idx')).write_bytes(bytes(index))
                for part in Path(scratch).iterdir():
                    shutil.copyfile(part, gitdir / 'objects/pack' / part.name)
            loose = gitdir / 'objects' / replacement[:2] / replacement[2:]
            loose.unlink(missing_ok=True)
            return git_dir('cat-file', 'blob', victim) == forged
        main.mkdir()
        git_at(main, 'init', '-q', '-b', 'main')
        (main / 'file').write_text('original')
        git_at(main, 'add', 'file'); git_at(main, 'commit', '-qm', 'Initial fixture')
        original_head = git_at(main, 'rev-parse', 'HEAD')
        git_at(main, 'worktree', 'add', '-q', '-b', 'linked', str(linked))
        other = top / 'git-other'
        git_at(main, 'worktree', 'add', '-q', '-b', 'other', str(other))
        policy['git_common_dir'] = str(main / '.git')
        config.write_text(json.dumps(policy))
        sandbox = load('scripts/agent_sandbox.py')
        private, agent_tree = top / 'agent-a1.git', top / 'agent-a1'
        sandbox.prepare(main / '.git', private, agent_tree, 'a1', 'task', 'main')
        agent_env = dict(os.environ, VELDO_EXPECTED_GIT_COMMON=str(private))
        agent_command = command[:]
        agent_command[agent_command.index(str(worktree))] = str(agent_tree)
        def shared_state():
            return (sorted(str(p.relative_to(main / '.git')) for p in (main / '.git/objects').rglob('*')),
                    git_at(main, 'for-each-ref', '--format=%(refname) %(objectname)'),
                    (main / '.git/packed-refs').read_bytes() if (main / '.git/packed-refs').exists() else None)
        shared_before = shared_state()
        script = """import errno, json, os, pathlib, subprocess, sys
pathlib.Path('file').write_text('agent edit')
subprocess.run(['git', 'add', 'file'], check=True)
subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '-qm', 'Confined worktree commit'], check=True)
results = {}
for name in sys.argv[2:]:
 try: pathlib.Path(name).write_text('forged')
 except OSError as error: results[name] = error.errno in (errno.EACCES, errno.EPERM)
 else: results[name] = False
head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
moved = subprocess.run(['git', 'update-ref', 'refs/heads/main', head], capture_output=True, text=True)
results['update-ref-main'] = moved.returncode != 0
other = subprocess.run(['git', 'branch', 'agent/a2/foreign', head], capture_output=True, text=True)
results['other-agent-namespace'] = other.returncode != 0
shared = subprocess.run(['git', 'hash-object', '-w', '--stdin'], input='planted', capture_output=True,
                        text=True, env=dict(os.environ, GIT_OBJECT_DIRECTORY=sys.argv[1]))
results['shared-object-write'] = shared.returncode != 0
own = subprocess.run(['git', 'branch', 'agent/a1/second', head], capture_output=True, text=True)
results['own-namespace-branch'] = own.returncode == 0
print(json.dumps(results))
"""
        protected_writes = [str(storepath/'authentication.key'), str(runner), str(ROOT/'scripts/agent_sandbox.py'),
            str(ROOT/'scripts/check_gate_mutations.py'), str(ROOT/'.veldo/control_verification.py'),
            str(main/'.git/config'), str(main/'.git/HEAD'), str(main/'.git/hooks/planted'),
            str(main/'file'), str(main/'.git/worktrees/git-other/index'), str(main/'.git/refs/heads/main'),
            str(main/'.git/refs/heads/planted'), str(main/'.git/objects/planted'),
            str(main/'.git/objects/pack/pack-planted.idx'), str(private/'refs/heads/main'),
            str(private/'refs/heads/agent/planted'), str(private/'config'), str(private/'packed-refs'),
            str(private/'HEAD'), str(private/'hooks/pre-commit')]
        result = confined_run(agent_command + [sys.executable, '-I', '-S', '-c', script,
            str(main / '.git/objects'), *protected_writes], capture_output=True, text=True, timeout=30, env=agent_env)
        attempts = json.loads(result.stdout) if result.returncode == 0 else {}
        agent_head = git_at(agent_tree, 'rev-parse', 'HEAD')
        expect('VELDO-0208 sandbox/agent-repository-commit: ' + result.stderr[-600:],
               result.returncode == 0 and agent_head != original_head
               and git_at(main, 'rev-parse', 'refs/heads/main') == original_head
               and git_at(agent_tree, 'symbolic-ref', 'HEAD') == 'refs/heads/agent/a1/task'
               and attempts.get('own-namespace-branch') is True)
        expect('VELDO-0208 git/agent-main-ref-write-refused: ' + json.dumps(attempts),
               attempts.get('update-ref-main') is True
               and not (private / 'refs/heads/main').exists()
               and attempts.get('other-agent-namespace') is True)
        expect('VELDO-0208 git/agent-protected-and-shared-writes-refused: ' + json.dumps(attempts),
               all(attempts.get(name) is True for name in protected_writes)
               and attempts.get('shared-object-write') is True and shared_state() == shared_before)
        # Integration is a fetch with transfer.fsckObjects into the agent's namespace only.
        sandbox.integrate(main / '.git', private, 'a1')
        expect('VELDO-0208 git/integrate-fetches-agent-namespace',
               git_at(main, 'rev-parse', 'refs/heads/agent/a1/task') == agent_head
               and git_at(main, 'rev-parse', 'refs/heads/main') == original_head
               and git_at(main, 'cat-file', '-p', agent_head + ':file') == 'agent edit')
        # A forged object in the private store (an id remapped to other bytes) never enters the
        # shared store: the fetch re-hashes it, so integration fails and no shared ref moves.
        (agent_tree / 'file').write_text('second edit')
        git_at(agent_tree, 'commit', '-qam', 'Second agent commit')
        second_head = git_at(agent_tree, 'rev-parse', 'HEAD')
        blob = git_at(agent_tree, 'rev-parse', 'HEAD:file')
        remapped = plant_remap(private, blob, b'forged bytes\n')
        (private / 'objects' / blob[:2] / blob[2:]).unlink()
        try:
            sandbox.integrate(main / '.git', private, 'a1')
        except RuntimeError:
            fetch_refused = True
        else:
            fetch_refused = False
        expect('VELDO-0208 git/integrate-rehashes-remapped-object',
               remapped and fetch_refused and git_at(main, 'rev-parse', 'refs/heads/agent/a1/task') == agent_head
               and subprocess.run(['/usr/bin/git', '-C', str(main), 'cat-file', '-e', blob],
                                  capture_output=True).returncode != 0
               and subprocess.run(['/usr/bin/git', '-C', str(main), 'cat-file', '-e', second_head],
                                  capture_output=True).returncode != 0)
        # The launcher refuses an agent worktree whose writes would reach the shared repository or
        # leave the agent namespace, before the command runs.
        # The probe writes into the worktree it starts in, which a started agent always may.
        start_probe = [sys.executable, '-c', 'open("agent-started", "w").close()']
        linked_command = command[:]
        linked_command[linked_command.index(str(worktree))] = str(linked)
        git_at(private, 'worktree', 'add', '-q', '-b', 'feature', str(top / 'agent-feature'), original_head)
        feature_command = command[:]
        feature_command[feature_command.index(str(worktree))] = str(top / 'agent-feature')
        for name, tree, argv, env, message in (
                ('shared-worktree', linked, linked_command,
                 dict(os.environ, VELDO_EXPECTED_GIT_COMMON=str(main / '.git')), 'must not share the authority object store'),
                ('unnamed-repository', linked, linked_command, dict(os.environ), 'private agent repository'),
                ('branch-outside-namespace', top / 'agent-feature', feature_command, agent_env,
                 'refs/heads/agent/<id>/<name>')):
            refused = confined_run(argv + start_probe, capture_output=True, text=True, timeout=20, env=env)
            expect('VELDO-0208 git/agent-start-refused-' + name + ': ' + refused.stderr[-300:],
                   refused.returncode == 2 and message in refused.stderr and not (tree / 'agent-started').exists())
        # The trusted verifier installation re-hashes every object from the trusted commit down: a
        # planted pack that remaps verify.sh's existing id to other bytes is never installed.
        trusted = top / 'trusted-repo'
        (trusted / 'scripts').mkdir(parents=True); (trusted / '.veldo').mkdir()
        (trusted / 'scripts/verify.sh').write_text('#!/bin/sh\necho trusted\n')
        (trusted / '.veldo/policy_check.py').write_text('TRUSTED = True\n')
        git_at(trusted, 'init', '-q', '-b', 'main'); git_at(trusted, 'add', '.')
        git_at(trusted, 'commit', '-qm', 'Trusted verifier')
        trusted_commit = git_at(trusted, 'rev-parse', 'HEAD')
        verifier_blob = git_at(trusted, 'rev-parse', 'HEAD:scripts/verify.sh')
        forged_verifier = b'#!/bin/sh\necho forged\n'
        verifier_remapped = plant_remap(trusted / '.git', verifier_blob, forged_verifier)
        def install(module, name):
            try:
                module.installation_at(trusted, trusted_commit, top / name)
            except module.Refused as error:
                return error.code
            return (top / name / 'scripts/verify.sh').read_bytes()
        landing_source = (ROOT / 'engine/.veldo/control_verification.py').read_text()
        check = 'if hashlib.new(algorithm, kind + b" %d\\0" % size + body).hexdigest() != oid:'
        unchecked = type(landing)('unchecked_control_verification')
        unchecked.__file__ = landing.__file__
        exec(compile(landing_source.replace(check, 'if False:'), landing.__file__, 'exec'), unchecked.__dict__)
        expect('VELDO-0208 install/planted-remap-not-installed',
               verifier_remapped and install(landing, 'installed') == 'invalid_input:installation/object-hash'
               and not (top / 'installed/scripts/verify.sh').exists()
               and landing_source.count(check) == 1
               and install(unchecked, 'unchecked') == forged_verifier)
        # Both plausible redirect metadata and hostile ambient Git config are planted.
        guard = load('.veldo/candidate_git.py')
        planted_hook = linked / 'git-escape.sh'
        escaped = top / 'git-escaped'
        planted_hook.write_text('#!/bin/sh\ntouch ' + str(escaped) + '\n')
        planted_hook.chmod(0o755)
        git_at(main, 'config', 'core.fsmonitor', str(planted_hook))
        hooks = linked / 'evil-hooks'; hooks.mkdir()
        shutil.copyfile(planted_hook, hooks / 'pre-commit'); (hooks / 'pre-commit').chmod(0o755)
        git_at(main, 'config', 'core.hooksPath', str(hooks))
        poisoned = dict(os.environ, GIT_CONFIG_COUNT='2',
            GIT_CONFIG_KEY_0='core.fsmonitor', GIT_CONFIG_VALUE_0=str(planted_hook),
            GIT_CONFIG_KEY_1='core.hooksPath', GIT_CONFIG_VALUE_1=str(hooks),
            GIT_CONFIG_PARAMETERS="'core.fsmonitor=" + str(planted_hook) + "'")
        check = guard.run(linked, ['status', '--porcelain'], main / '.git',
                          env=poisoned, capture_output=True)
        committed = guard.run(linked, ['-c', 'user.name=Fixture', '-c',
            'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'Guard fixture'],
            main / '.git', env=poisoned, capture_output=True)
        expect('VELDO-0208 git/config-hooks-and-fsmonitor-disabled',
               check.returncode == committed.returncode == 0 and not escaped.exists())
        git_at(main, 'config', '--unset', 'core.fsmonitor')
        git_at(main, 'config', '--unset', 'core.hooksPath')
        original_marker = (linked / '.git').read_text()
        fake_common = linked / 'fake-common'; fake = fake_common / 'worktrees/fake'
        fake.mkdir(parents=True)
        (fake / 'gitdir').write_text(str(linked / '.git'))
        (fake / 'commondir').write_text('../..')
        (fake / 'HEAD').write_text('ref: refs/heads/agent\n')
        (fake / 'config').write_text('[core]\nfsmonitor = ' + str(planted_hook) + '\n')
        (linked / '.git').write_text('gitdir: ' + str(fake) + '\n')
        refused = subprocess.run([sys.executable, '-I', '-S', str(ROOT / '.veldo/candidate_git.py'),
            '--root', str(linked), '--expected-common', str(main / '.git'), '--', 'status'],
            capture_output=True, text=True, timeout=20)
        refused_agent = confined_run(linked_command + ['/usr/bin/true'], capture_output=True, text=True,
                                      timeout=20, env=dict(os.environ, VELDO_EXPECTED_GIT_COMMON=str(main / '.git')))
        expect('VELDO-0208 git/redirect-refused-before-git-or-agent',
               refused.returncode == refused_agent.returncode == 2
               and 'expected shared gitdir' in refused.stderr
               and 'expected shared gitdir' in refused_agent.stderr and not escaped.exists())
        (linked / '.git').unlink()
        (linked / '.git').mkdir()
        try:
            guard.validate(linked, main / '.git')
        except ValueError:
            directory_refused = True
        else:
            directory_refused = False
        expect('VELDO-0208 git/embedded-directory-cannot-replace-linked-marker', directory_refused)
        (linked / '.git').rmdir()
        (linked / '.git').write_text(original_marker)

        # Small controlled workers only: never run the mutation stage or its drivers. The traced
        # baseline, noop and mutant workers are _v208_traced_workers below, the strace rows.
        worker_root, worker_home, worker_suite, controlled_case, worker_argv = _v208_worker_fixture(top, escaped)
        tracer = load('scripts/case_trace.py')
        scratch = worker_home / 'mutant'; scratch.mkdir()
        job = top / 'mutant-job.json'
        worker_suite.write_text('from pathlib import Path\nPath(' +
            repr(str(storepath / 'authentication.key')) + ').read_bytes()\n')
        job.write_text(json.dumps(dict(case=controlled_case, mode='baseline')))
        argv, channel = worker_argv(job)
        try:
            denied_worker = confined_run(argv, cwd=worker_root, env=gate.fixed_env(scratch), pass_fds=(channel,),
                                          capture_output=True, text=True, timeout=20)
        finally:
            os.close(channel)
        expect('VELDO-0208 candidate/worker-key-access-errors-never-kills: ' + denied_worker.stderr[-300:],
               denied_worker.returncode != 0 and 'PermissionError' in denied_worker.stderr)
        fake_trace = top / 'forged.trace'
        fake_trace.write_text('1 openat(AT_FDCWD, "/stolen-key", O_RDONLY) = 3</stolen-key>\n')
        try:
            list(tracer.accesses(fake_trace, after_confinement=True))
        except ValueError:
            trace_refused = True
        else:
            trace_refused = False
        expect('VELDO-0208 candidate/trace-missing-boundary-refused', trace_refused)
        fake_trace.write_text('1 landlock_restrict_self(3, 0) = 0\n'
                             '1 openat(AT_FDCWD, "/stolen-key", O_RDONLY) = -1 EACCES\n')
        try:
            tracer.check(fake_trace, worker_root, [], scratch=worker_home, after_confinement=True)
        except ValueError:
            trace_refused = True
        else:
            trace_refused = False
        expect('VELDO-0208 candidate/trace-still-rejects-undeclared-probes', trace_refused)

        # The unconfined coordinator reaps what a worker owns. Its ledger is the coordinator's file,
        # outside every worker grant; a confined candidate suite reaches it only through the inherited
        # append descriptor, so each planted line is a claim. Real authority workers run these suites
        # under the real coordinator (Workers.run); systemctl is recorded, never invoked.
        import time
        ledger_root = top / 'ledger-input'
        (ledger_root / 'scripts/suites').mkdir(parents=True); (ledger_root / '.veldo').mkdir()
        shutil.copyfile(worker_root / 'scripts/suites/shared.py', ledger_root / 'scripts/suites/shared.py')
        (ledger_root / '.veldo/subject.py').write_text('good')
        victims = top / 'ledger-victims'; victims.mkdir()
        (victims / 'keep').write_text('outside')
        victim_service = victims / 'victim.service'; victim_service.write_text('[Unit]\n')
        class Pool:
            def demand(self, job): pass
            def select(self, pending): return 0
            def acquire(self, name, job): pass
            def release(self, name): pass
        def drive_ledger(body):
            (ledger_root / 'scripts/suites/fixture.py').write_text(
                'import json, os, sys, tempfile\n' + body + 'expect("fixture target", True)\n')
            calls = []
            def systemctl(argv, **kwargs):
                calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, '', '')
            with tempfile.TemporaryDirectory(prefix='ledger-coordinator-') as coordinator:
                workers = gate.Workers(time.monotonic() + 60, resources=Pool(), parallel=1)
                with patch.object(subprocess, 'run', systemctl):
                    try:
                        workers.run({'ledger': dict(case=controlled_case, mode='baseline')},
                                    Path(coordinator), ledger_root)
                    except gate.Refused as error:
                        code = error.code
                    else:
                        code = None
            outside_intact = ((victims / 'keep').read_text() == 'outside'
                              and victim_service.read_text() == '[Unit]\n')
            return code, calls, (workers.outcomes or [{}])[-1], outside_intact
        def forge(kind, value):
            return 'os.write(int(sys.argv[3]), (json.dumps([%r, %r]) + "\\n").encode())\n' % (kind, value)
        code, calls, outcome, intact = drive_ledger('tempfile.mkdtemp()\n')
        expect('VELDO-0208 ownership/own-temporary-tree-reaped: ' + str(outcome.get('detail')),
               code is None and outcome.get('cleanup') == {'units': [], 'directories': 1} and calls == [])
        for kind, value in (('directory', str(victims)), ('service', str(victim_service)),
                            ('slice', 'user.slice')):
            code, calls, outcome, intact = drive_ledger(forge(kind, value))
            expect('VELDO-0208 ownership/forged-' + kind + '-red-and-untouched: ' + str(outcome.get('detail')),
                   code == 'worker_cleanup_error' and 'outside this worker' in outcome.get('detail', '')
                   and calls == [] and intact)
        # Python audits mkdtemp before its mkdir, so a probe the domain refuses still reaches the
        # ledger. shared.fast_temp's /dev/shm probe did, and every suite using it went red in the
        # gate's mutation stage (worker_cleanup_error) while passing alone.
        code, calls, outcome, intact = drive_ledger(
            'for parent in ("/dev/shm", %r):\n'
            '    try:\n'
            '        os.rmdir(tempfile.mkdtemp(prefix="fast-probe-", dir=parent))\n'
            '    except OSError:\n'
            '        pass\n' % str(victims))
        expect('VELDO-0208 ownership/refused-outside-probe-not-red: ' + str(outcome.get('detail')),
               code is None and calls == [] and intact
               and sorted(p.name for p in victims.iterdir()) == ['keep', 'victim.service'])
        code, calls, outcome, intact = drive_ledger(forge('directory', str(victims / 'absent')))
        expect('VELDO-0208 ownership/forged-absent-directory-untouched: ' + str(outcome.get('detail')),
               code is None and calls == [] and intact and not (victims / 'absent').exists())
        # A fresh worker runs isolated but with the system site-packages its suites ran with before
        # confinement. Under -S, 0119's PyYAML oracle stood down and reader-strip-quoted-hash survived.
        code, calls, outcome, intact = drive_ledger(
            'if sys.flags.no_site or not sys.flags.isolated:\n'
            '    raise SystemExit("worker flags: no_site=%d isolated=%d" % (sys.flags.no_site, sys.flags.isolated))\n')
        expect('VELDO-0208 worker/fresh-keeps-system-site: ' + str(outcome.get('detail')),
               code is None and calls == [])
        code, calls, outcome, intact = drive_ledger(
            'open(os.path.join(os.environ["TMPDIR"], "ownership.jsonl"), "w").write('
            'json.dumps(["directory", %r]) + "\\n")\n' % str(victims))
        expect('VELDO-0208 ownership/home-ledger-never-read: ' + str(outcome.get('detail')),
               code is None and calls == [] and intact)
        git_at(worker_root, 'init', '-q')
        definition = {k: v for k, v in controlled_case.items() if k not in ('driver', 'identity')}
        for driver in gate.DRIVERS:
            (worker_root / 'scripts' / driver).write_text('def cases(): return ' + repr([definition]) + '\n')
        with patch.dict(os.environ, {'VELDO_AGENT_CONFIG': str(config)}):
            inventory = gate.inventory(worker_root, expected_common=worker_root / '.git')
        expect('VELDO-0208 candidate/frozen-registry-confined', len(inventory) == 2)
        (worker_root / 'scripts' / gate.DRIVERS[0]).write_text(
            'from pathlib import Path\nPath(' + repr(str(storepath / 'authentication.key')) + ').read_bytes()\n')
        with patch.dict(os.environ, {'VELDO_AGENT_CONFIG': str(config)}):
            try:
                gate.inventory(worker_root, expected_common=worker_root / '.git')
            except gate.Refused as error:
                refused_registry = error.code == 'candidate_execution_denied' and 'PermissionError' in error.detail
            else:
                refused_registry = False
        expect('VELDO-0208 candidate/planted-registry-red', refused_registry)
        scaffold = load('engine/.veldo/init_scaffold.py')
        # The unconfined list is this repository's own owner decision: it is optional in the
        # authority and never shipped, and no engine copy exists to ship.
        expect('VELDO-0208 engine/scaffold-includes-boundary',
               set(E.AUTHORITY_FILES) - set(E.OPTIONAL_AUTHORITY_FILES) <= set(scaffold._FILES)
               and 'scripts/gate_legs.py' in scaffold._FILES)
        expect('VELDO-0208 engine/adopters-receive-no-unconfined-list',
               E.OPTIONAL_AUTHORITY_FILES == ('scripts/gate_unconfined.json',)
               and not set(E.OPTIONAL_AUTHORITY_FILES) & set(scaffold._FILES)
               and not set(E.OPTIONAL_AUTHORITY_FILES) & set(scaffold.REQUIRED_SUBSTRATE)
               and not (ROOT / 'engine/scripts/gate_unconfined.json').exists())
        catalog = load('.veldo/control_proof.py').catalog((ROOT / 'scripts/verify.sh').read_text())
        expect('VELDO-0208 gate/catalog-includes-authority-stage',
               {'extra', 'mutation'} <= set(catalog['required']))
        with patch.dict(os.environ, {}, clear=True):
            engine_evidence = load('engine/.veldo/reuse_evidence.py')
            default_path, _ = engine_evidence.configuration()
        expect('VELDO-0208 engine/default-config-shipped',
               default_path == ROOT / 'engine/scripts/agent_sandbox.json')

        case = dict(identity='check_teeth_mutations.py:fixture', name='fixture',
                    driver='check_teeth_mutations.py', rows=['target'], suite='fixture.py',
                    module='subject.py', old='good', new='bad')
        files = {name: ((ROOT / name).stat().st_mode & 0o777, (ROOT / name).read_bytes())
                 for name in (*C.I.MANDATORY, *C.I.DRIVERS)}
        files['scripts/suites/fixture.py'] = (0o644, b'# Controlled observations; no suite process.\n')
        files['.veldo/subject.py'] = (0o644, b'good\n')
        files[C.I.DECLARATIONS] = (0o644, E.canonical({'schema': 'veldo.case-inputs/v1',
            'toolchains': {case['driver']: {'paths': ['/usr'], 'reviewed': True}},
            'cases': {case['identity']: {'files': [], 'reviewed': True, 'non_file_inputs': 'none',
                                       'rationale': 'Controlled file-only unit fixture.'}}}))
        def session(source):
            with patch.object(C.M, 'runtime_identity', return_value={'fixture': 'runtime-v1'}):
                return C.Session(worktree, source, [case], 'a' * 40, {}, environment={},
                                 cache_directory=storepath)
        current = session(files)
        observation = lambda ok: {'observations': [['fixture target', ok]], 'count': 1,
                                  'row_names': ['fixture target'], 'failed_rows': [] if ok else ['fixture target']}
        key = current.keys[case['identity']]
        record = {'schema': gate.SCHEMA, 'case': case, 'fixture_version': gate.FIXTURE_VERSION,
                  'input_digest': key, 'replacement_count': 1, 'old_digest': 'a', 'new_digest': 'b',
                  'baseline': observation(True), 'noop': observation(True),
                  'mutant': observation(False), 'elapsed': 0.1}
        # Reproduce the review attack with the exact controlled Session key, not
        # just an arbitrary record name. Runtime is fixed fixture data on both sides.
        for relative in E.AUTHORITY_FILES:
            destination = worktree / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        attack_input = worktree / 'attack-input.json'
        attack_input.write_text(json.dumps(dict(
            files={name: [mode, body.hex()] for name, (mode, body) in files.items()},
            case=case, key=key, record=record, store=str(storepath))))
        planted.write_text("import case_reuse as C, json\nfrom pathlib import Path\n"
            "data = json.loads(Path('attack-input.json').read_text())\n"
            "files = {n: (m, bytes.fromhex(b)) for n, (m,b) in data['files'].items()}\n"
            "C.M.runtime_identity = lambda *args: {'fixture': 'runtime-v1'}\n"
            "s = C.Session(Path.cwd(), files, [data['case']], 'a' * 40, {}, environment={}, "
            "cache_directory=data['store'])\n"
            "key = s.keys[data['case']['identity']]\n"
            "assert key == data['key'], 'case key differs'\n"
            "assert s.store.put(key, data['record']), 'real-key publication denied'\n")
        attack = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'scripts/gate_candidate.py'),
            '--root', str(worktree), '--', sys.executable, str(planted)],
            env=dict(os.environ, VELDO_AGENT_CONFIG=str(config)), capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 candidate/real-session-key-planting-red',
               attack.returncode != 0 and 'real-key publication denied' in attack.stderr
               and 'store-denied domain' in attack.stderr and not (storepath / (key + '.json')).exists())
        expect('VELDO-0208 provenance/gate-writes-authenticated-record',
               current.publish(case, record, gate.validate_result) and store.get(key) == record
               and session(files).lookup(case, gate.validate_result) == record)
        changed = dict(files); changed['.veldo/subject.py'] = (0o644, b'changed input\n')
        moved = session(changed)
        expect('VELDO-0208 landing/changed-declared-input-misses',
               moved.keys[case['identity']] != key and moved.lookup(case, gate.validate_result) is None)
        with patch.object(C.M, 'runtime_identity', return_value={'fixture': 'runtime-v1'}):
            forced = C.Session(worktree, files, [case], 'a' * 40, {},
                environment={'VELDO_GATE_FORCE_FRESH': '1'}, cache_directory=storepath)
        expect('VELDO-0208 landing/force-fresh-bypasses-store', forced.store is None
               and forced.lookup(case, gate.validate_result) is None
               and not forced.publish(case, record, gate.validate_result))
        path = storepath / (key + '.json'); raw = path.read_bytes()
        payload = json.loads(raw)['payload']
        expect('VELDO-0208 provenance/signed-outside-domain', payload['provenance'] == E.PROVENANCE)
        wrong_authority = dict(payload, authority='0' * 64)
        path.write_bytes(E.canonical(E.sign(wrong_authority, store.secret)))
        expect('VELDO-0208 provenance/signed-other-authority-refused', store.get(key) is None)
        path.write_bytes(raw)
        with patch.object(C.R.E, 'authority_identity', return_value='0' * 64):
            other_authority = session(files)
        expect('VELDO-0208 provenance/authority-is-in-case-key',
               other_authority.keys[case['identity']] != key)
        legacy = dict(payload); legacy.pop('provenance')
        path.write_bytes(E.canonical(E.sign(legacy, store.secret)))
        expect('VELDO-0208 provenance/signed-missing-provenance-refused', store.get(key) is None)
        path.write_bytes(raw)
        env = dict(os.environ, VELDO_AGENT_CONFIG=str(config))
        writer = '''import importlib.util, os, pathlib, sys
spec = importlib.util.spec_from_file_location('reuse', sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
os.environ.pop('VELDO_AGENT_SANDBOX', None)
s = m.Store(sys.argv[2], pathlib.Path.cwd())
assert s.secret is None and not s.put('a' * 64, {'planted': True})
'''
        result = confined_run(command + [sys.executable, '-I', '-S', '-c', writer,
            str(ROOT / 'scripts/gate_reuse.py'), str(storepath)],
            capture_output=True, text=True, env=env, timeout=20)
        expect('VELDO-0208 provenance/confined-gate-cannot-sign: ' + result.stderr[-300:],
               result.returncode == 0)

        commit = 'a' * 40
        receipt = dict(status='passed', force_fresh=False, reused=1, executed=0, registered=1,
                       results=[dict(record, reuse_key=key, source='reused', reuse_reason='hit')])
        with patch.dict(os.environ, {'VELDO_AGENT_CONFIG': str(config)}):
            fields = reducer.fields(receipt, False, commit)
            stamp = dict(commit=commit, status='green', **fields)
            expect('VELDO-0208 landing/authenticated-declared-record-accepted', E.landing_problem(stamp) is None)
            forged_authority = dict(fields['reuse_evidence']['payload'], authority='0' * 64)
            expect('VELDO-0208 landing/signed-other-authority-refused', E.landing_problem(
                dict(stamp, reuse_evidence=E.sign(forged_authority, store.secret))) is not None)

            # This repository's authority carries its unconfined list; the engine's, which adopters
            # install, carries none, so the two identities differ. The engine-side checks (the
            # fleet's judge, the engine and pack guards) get evidence signed under the engine's
            # identity, as an adopter's own gate signs it.
            engine_identity = load('engine/.veldo/reuse_evidence.py').authority_identity()
            def signed_under(identity, at):
                path.write_bytes(E.canonical(E.sign(dict(payload, authority=identity), store.secret)))
                with patch.object(reducer.E, 'authority_identity', return_value=identity):
                    return dict(commit=at, status='green', **reducer.fields(receipt, False, at))
            engine_stamp = signed_under(engine_identity, commit)
            stdout = '== unit\n   unit: pass\nGATE: GREEN (' + commit + ')'
            sample = {'schema': 'veldo.gate_observation/v1', 'commit': commit, 'stdout': stdout,
                'stdout_digest': landing.digest(stdout.encode()), 'exit': 0, 'terminal': stdout.splitlines()[-1],
                'catalog': {'required': ['unit'], 'results': {'unit': 'pass'}},
                'candidate': {'commit': commit, 'tree': 'b'*40, 'binds_refs': False, 'state': {}},
                'post_run': {'equal': True, 'state': {}},
                'outputs': {'last_verify': engine_stamp, 'gate_event': dict(engine_stamp, type='gate.passed')}}
            expect('VELDO-0208 landing/fleet-accepts-gate-records',
                   engine_identity != E.authority_identity() and not landing.judge(sample))
            for document in ('last_verify', 'gate_event'):
                altered = copy.deepcopy(sample)
                altered['outputs'][document]['reuse_evidence'] = {}
                expect('VELDO-0208 landing/fleet-checks-' + document,
                       'missing_evidence:gate/authenticated_reuse_required' in landing.judge(altered))
            for missing in (('reused',), ('force_fresh',), ('reused', 'force_fresh')):
                for document in ('last_verify', 'gate_event'):
                    altered = copy.deepcopy(sample)
                    for field in missing:
                        altered['outputs'][document].pop(field)
                    expect('VELDO-0208 landing/missing-fields-' + document + str(missing),
                           bool(landing.judge(altered)))
            path.write_bytes(raw)
            alterations = [dict(reuse_evidence={}), dict(commit='c' * 40),
                          dict(reused={'unit': 0, 'mutation': 2}), dict(force_fresh=True)]
            for n, change in enumerate(alterations):
                expect('VELDO-0208 landing/tampered-binding-' + str(n),
                       E.landing_problem(dict(stamp, **change)) is not None)
            path.write_bytes(E.canonical(E.sign(legacy, store.secret)))
            expect('VELDO-0208 landing/missing-record-provenance-refused', E.landing_problem(stamp) is not None)
            path.write_bytes(E.canonical(E.sign(dict(legacy, authority=engine_identity), store.secret)))
            expect('VELDO-0208 landing/fleet-refuses-missing-provenance',
                   'missing_evidence:gate/authenticated_reuse_required' in landing.judge(sample))
            path.write_bytes(raw)
            wrong = dict(record, input_digest='d' * 64)
            bad_payload = dict(payload, result=wrong)
            path.write_bytes(E.canonical(E.sign(bad_payload, store.secret)))
            expect('VELDO-0208 landing/wrong-declared-key-refused', E.landing_problem(stamp) is not None)
            path.write_bytes(raw)
            for changes in (dict(reused=2), dict(executed=1), dict(registered=2), dict(force_fresh=True)):
                try:
                    reducer.fields(dict(receipt, **changes), False, commit)
                except ValueError:
                    refused = True
                else:
                    refused = False
                expect('VELDO-0208 landing/reducer-refuses-' + next(iter(changes)), refused)
            fresh = dict(status='passed', force_fresh=True, reused=0)
            expect('VELDO-0208 landing/force-fresh-and-zero-counts',
                   E.landing_problem(dict(commit=commit, **reducer.fields(fresh, True, commit))) is None)
            expect('VELDO-0208 landing/zero-reuse-needs-no-force-flag',
                   E.landing_problem(dict(commit=commit, force_fresh=False, reused={'mutation': 0})) is None)
            fresh_record = dict(record, case=dict(case, identity='second'))
            mixed = dict(receipt, registered=2, executed=1,
                         results=receipt['results'] + [dict(fresh_record, source='fresh')])
            expect('VELDO-0208 landing/mixed-counts-remain-honest',
                   reducer.fields(mixed, False, commit)['reused'] == {'unit': 0, 'mutation': 1})

            # Drive the real shell guard; the next refusal (no proof) proves this guard passed.
            fixture = top / 'guard-repo'; fixture.mkdir(); (fixture / '.veldo').mkdir()
            def git(*args):
                return subprocess.check_output(['git', '-C', str(fixture), *args], stderr=subprocess.PIPE).decode().strip()
            git('init', '-q')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                'commit', '--allow-empty', '-qm', 'Fixture')
            actual = git('rev-parse', 'HEAD')
            for guard in ('scripts/veldo-guard.sh', 'engine/scripts/veldo-guard.sh',
                          'packs/claude/scripts/veldo-guard.sh'):
                valid = signed_under(E.authority_identity() if guard == 'scripts/veldo-guard.sh'
                                     else engine_identity, actual)
                for name, candidate, refused in [('valid', valid, False),
                        ('no-provenance', dict(valid, reuse_evidence={}), True),
                        ('missing-both', {'commit': actual, 'status': 'green'}, True),
                        ('missing-force', {k:v for k,v in valid.items() if k != 'force_fresh'}, True),
                        ('missing-reused', {k:v for k,v in valid.items() if k != 'reused'}, True)]:
                    (fixture / '.veldo/last_verify').write_text(json.dumps(candidate))
                    result = subprocess.run(['bash', str(ROOT / guard)],
                        input=json.dumps({'tool_input': {'command': 'git merge topic'}}), text=True,
                        capture_output=True, timeout=20, env=dict(env, CLAUDE_PROJECT_DIR=str(fixture)))
                    expect('VELDO-0208 landing/real-guard-' + guard + '-' + name,
                           ('Landing requires authenticated' in result.stderr) is refused and result.returncode == 2)
            path.write_bytes(raw)
        # Exercise only the stamp writer function, never a gate/catalog command.
        template = (ROOT / 'engine/scripts/verify.sh').read_text()
        stamp_function = template[template.index('veldo_write_stamp() {'):].split('\n}', 1)[0] + '\n}'
        for force in ('false', 'true'):
            stamp_path = top / 'engine-stamp.json'
            program = ('COMMIT=' + 'a' * 40 + '\nSTATUS=green\nTS=fixture\nRAN=1\nNA=0\n'
                'VERSION_JSON=null\nTREE_JSON=null\nVELDO_FORCE_JSON=' + force + '\n'
                + stamp_function + '\nveldo_write_stamp "$1"\n')
            written = subprocess.run(['bash', '-c', program, 'fixture', str(stamp_path)],
                                     capture_output=True, text=True, timeout=20)
            expect('VELDO-0208 engine/stamp-declares-zero-reuse-' + force,
                   written.returncode == 0 and E.landing_problem(json.loads(stamp_path.read_text())) is None)
        expect('VELDO-0208 landing/canonical-copies-match', all(
            (ROOT / a).read_bytes() == (ROOT / b).read_bytes() for a, b in (
                ('engine/scripts/agent_sandbox.json', 'scripts/agent_sandbox.json'),
                ('engine/scripts/agent_sandbox.py', 'scripts/agent_sandbox.py'),
                ('engine/.veldo/reuse_evidence.py', '.veldo/reuse_evidence.py'),
                ('engine/.veldo/control_verification.py', '.veldo/control_verification.py'),
                ('engine/scripts/veldo-guard.sh', 'scripts/veldo-guard.sh'),
                ('engine/scripts/veldo-guard.sh', 'packs/claude/scripts/veldo-guard.sh'))))


def _v208_traced_workers():
    """The authority's baseline, noop and mutant workers under its tracer (strace), each observed
    and its trace checked against the declared closure. These are the suite's strace rows: the gate
    domain refuses ptrace, so a gate whose authority lists them (scripts/gate_unconfined.json) runs
    them in its unconfined leg, and every other row of this suite stays in the confined leg."""
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile

    def load(relative):
        spec = importlib.util.spec_from_file_location(Path(relative).stem, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    gate = load('scripts/check_gate_mutations.py')
    tracer = load('scripts/case_trace.py')
    with tempfile.TemporaryDirectory(prefix='landing-traced-') as temporary:
        top = Path(temporary)
        escaped = top / 'driver-escaped'
        worker_root, worker_home, _, controlled_case, worker_argv = _v208_worker_fixture(top, escaped)
        observed = {}
        for mode in ('baseline', 'noop', 'mutant'):
            scratch = worker_home / mode; scratch.mkdir()
            job = top / (mode + '-job.json')
            job.write_text(json.dumps(dict(case=controlled_case, mode=mode)))
            trace = top / (mode + '.trace')
            argv, channel = worker_argv(job)
            try:
                process = subprocess.run(tracer.command(trace, argv), cwd=worker_root, pass_fds=(channel,),
                    env=gate.fixed_env(scratch), capture_output=True, text=True, timeout=20,
                    stdin=subprocess.DEVNULL)
            finally:
                os.close(channel)
            expect('VELDO-0208 candidate/authority-worker-' + mode + ': ' + process.stderr[-400:],
                   process.returncode == 0 and not escaped.exists())
            if process.returncode == 0:
                observed[mode] = json.loads(process.stdout)
                tracer.check(trace, worker_root, ['scripts/suites/shared.py', 'scripts/suites/fixture.py',
                    '.veldo/subject.py'], runtime=('/usr', '/lib', '/lib64', '/etc'), scratch=scratch,
                    after_confinement=True)
        expect('VELDO-0208 candidate/authority-observes-kill', len(observed) == 3
               and observed['baseline']['observation']['failed_rows'] == []
               and observed['noop']['observation']['failed_rows'] == []
               and observed['mutant']['observation']['failed_rows'] == ['fixture target'])


if leg_runs():
    _v208_landing_reuse()
if leg_runs('strace'):
    _v208_traced_workers()


def _v208_confined_stages():
    """The gate's own stages, run UNDER the gate's confinement (scripts/gate_candidate.py, the
    launcher verify.sh uses), not beside it. Every suite passed alone while the first confined
    gate went red on all of these, so each row reproduces one way that happened:
    generators writing the read-only tree, the unit stage's Unix sockets and terminals, a nested
    gate's launcher listing /proc, an installed pack's gate inheriting this repository's Git
    common directory, a mutation worker serving a socket, and a failed receipt's traceback."""
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile

    launcher = [sys.executable, '-I', '-S', str(ROOT / 'scripts/gate_candidate.py')]
    # Run alone, a row starts the gate's launcher. Run by the gate's own unit stage, this suite is
    # already inside that confinement, and a launcher started here would be a nested one, which
    # never gets Unix sockets (asserted below): there the row runs its command as it stands.
    inside = os.environ.get('VELDO_SANDBOX_BROKERED') == '1'
    # Outside every domain's writable roots (the gate never writes the authority tree), so an
    # address there is outside the confinement whether or not this suite already runs in it.
    outside = ROOT / ('.v208-outside-%d' % os.getpid())

    def confined(root, command, env=None, timeout=120):
        """One gate stage command in the gate's own domain over `root`, exactly as verify.sh's
        veldo_candidate runs it: stdin /dev/null, output captured."""
        return subprocess.run(launcher + ['--root', str(root), '--', *command], capture_output=True,
                              text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                              env=dict(os.environ if env is None else env))

    with tempfile.TemporaryDirectory(prefix='v208-confined-') as temporary:
        top = Path(temporary)

        # ---- generated: regenerate privately, compare, never write the tree ----------------------
        tree = top / 'generated-tree'
        (tree / 'scripts').mkdir(parents=True)
        shutil.copytree(ROOT / '.veldo', tree / '.veldo', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(ROOT / 'scripts/update_index.py', tree / 'scripts/update_index.py')
        (tree / 'specs').mkdir()
        (tree / 'specs/VELDO-9208-fixture.md').write_text(
            '---\nid: VELDO-9208\ntitle: Confined generated fixture\nstatus: draft\nrisk: low\n'
            'owner: suite\n---\n\nFixture.\n')
        subprocess.run([sys.executable, str(tree / 'scripts/update_index.py')], check=True,
                       capture_output=True, timeout=60)
        index = tree / 'specs/index.md'
        fresh = index.read_text()
        stage_env = dict(os.environ, GENERATED_CHECK_ROOT=str(tree), GENERATED_CHECK_ONLY='spec-index')
        clean = confined(tree, ['bash', str(ROOT / 'scripts/check_generated.sh')], stage_env)
        index.write_text(fresh + 'stale\n')
        stale = confined(tree, ['bash', str(ROOT / 'scripts/check_generated.sh')], stage_env)
        expect('VELDO-0208 confined-stage/generated-compares-without-writing: ' + (clean.stdout + clean.stderr)[-300:],
               clean.returncode == 0 and 'generated: pass (specs/index.md)' in clean.stdout
               and stale.returncode == 1 and 'specs/index.md was stale' in stale.stdout
               and 'Nothing was rewritten' in stale.stdout and 'errored or refused' not in stale.stdout
               and 'Permission denied' not in stale.stdout + stale.stderr
               and index.read_text() == fresh + 'stale\n')

        # ---- unit: the suites' Unix sockets and terminals, brokered; services refused -----------
        probe = top / 'probe-root'
        probe.mkdir()
        (probe / 'probe.py').write_text(r"""import errno, json, os, pty, socket, tempfile, threading
r = {}
def holds(name, operation):
    # Each row on its own: one that raises is recorded false, never takes the others with it.
    try:
        r[name] = bool(operation())
    except Exception as error:
        r[name] = repr(error)
def refused(name, operation):
    try:
        operation()
    except OSError as error:
        r[name] = error.errno in (errno.EACCES, errno.EPERM, errno.EXDEV)
    except Exception as error:
        r[name] = repr(error)
    else:
        r[name] = False
d = tempfile.mkdtemp()
path = os.path.join(d, 'listener')
def serve_and_dial():
    srv = socket.socket(socket.AF_UNIX)
    srv.bind(path)
    srv.listen()
    r['bound-name-is-the-path'] = srv.getsockname() == path
    def serve():
        c, _ = srv.accept(); c.sendall(c.recv(8).upper()); c.close()
    threading.Thread(target=serve, daemon=True).start()
    c = socket.socket(socket.AF_UNIX); c.connect(path); c.sendall(b'ping')
    return c.recv(8) == b'PING'
holds('stream-round-trip', serve_and_dial)
def datagram():
    q = os.path.join(d, 'datagram')
    dg = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM); dg.bind(q)
    socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM).sendto(b'x', q)
    return dg.recv(4) == b'x'
holds('datagram-to-own-socket', datagram)
def descriptors():
    x, y = socket.socketpair()
    socket.send_fds(x, [b'f'], [1])
    return len(socket.recv_fds(y, 4, 2)[1]) == 1
holds('descriptor-passing', descriptors)
def terminal():
    master, terminal = os.openpty()
    os.write(master, b'typed\n')
    return os.isatty(terminal) and os.read(terminal, 16).startswith(b'typed')
holds('own-terminal', terminal)
def terminal_child():
    pid, fd = pty.fork()
    if pid == 0:
        os.write(1, b'child-on-terminal\n'); os._exit(0)
    out = b''
    try:
        while True:
            chunk = os.read(fd, 64)
            if not chunk: break
            out += chunk
    except OSError:
        pass
    os.waitpid(pid, 0)
    return b'child-on-terminal' in out
holds('terminal-child', terminal_child)
holds('proc-mounts-readable', lambda: open('/proc/mounts').read(8))
bus = '/run/user/%d/bus' % os.getuid()
refused('user-bus-refused', lambda: socket.socket(socket.AF_UNIX).connect(bus))
def via_link():
    os.symlink(bus, os.path.join(d, 'bus-link'))
    socket.socket(socket.AF_UNIX).connect(os.path.join(d, 'bus-link'))
refused('symlink-to-bus-refused', via_link)
refused('abstract-connect-refused', lambda: socket.socket(socket.AF_UNIX).connect('\0veldo-probe'))
refused('abstract-bind-refused', lambda: socket.socket(socket.AF_UNIX).bind('\0veldo-probe'))
refused('bind-outside-scratch-refused', lambda: socket.socket(socket.AF_UNIX).bind(os.environ['VELDO_PROBE_OUTSIDE']))
refused('addressed-sendto-service-refused',
        lambda: socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)[0].sendto(b'x', bus))
refused('addressed-sendmsg-service-refused',
        lambda: socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)[0].sendmsg([b'x'], [], 0, '/run/systemd/journal/socket'))
def outside_environ():
    # The nearest ancestor outside this domain is the launcher's trusted parent: its environ must
    # be refused (Landlock's ptrace scope), while ancestors inside the domain stay readable.
    pid = os.getppid()
    while pid > 1:
        try:
            open('/proc/%d/environ' % pid, 'rb').read()
        except PermissionError:
            return True
        pid = int(open('/proc/%d/stat' % pid).read().rsplit(')', 1)[1].split()[1])
    return False
holds('outside-environ-refused', outside_environ)
print(json.dumps(r))
""")
        probe_env = dict(os.environ, VELDO_PROBE_OUTSIDE=str(outside))
        names = ('bound-name-is-the-path', 'stream-round-trip', 'datagram-to-own-socket', 'descriptor-passing',
                 'own-terminal', 'terminal-child', 'proc-mounts-readable', 'user-bus-refused',
                 'symlink-to-bus-refused', 'abstract-connect-refused', 'abstract-bind-refused',
                 'bind-outside-scratch-refused', 'addressed-sendto-service-refused',
                 'addressed-sendmsg-service-refused', 'outside-environ-refused')
        command = [sys.executable, str(probe / 'probe.py')]
        result = (subprocess.run(command, capture_output=True, text=True, timeout=120, env=probe_env,
                                 stdin=subprocess.DEVNULL) if inside else confined(probe, command, probe_env))
        try:
            found = json.loads(result.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            found = {}
        for name in names:
            expect('VELDO-0208 confined-stage/unit-' + name + ': ' + repr(found.get(name))
                   + ' ' + result.stderr[-300:], found.get(name) is True)
        expect('VELDO-0208 confined-stage/unit-nothing-bound-outside', not outside.exists())
        # A launcher started inside a brokered domain (a gate a suite runs) cannot hold a listener
        # of its own; the outer broker answers for the outer domain's roots, not the nested one's,
        # so the nested domain gets no Unix sockets rather than its parent's reach.
        (probe / 'strict.py').write_text('import socket\ntry:\n    socket.socket(socket.AF_UNIX)\n'
                                         'except PermissionError:\n    print("refused")\n')
        nested = [sys.executable, str(probe / 'strict.py')]
        nested = launcher + ['--root', str(probe), '--', *nested] if not inside else nested
        nested_result = confined(probe, nested)
        expect('VELDO-0208 confined-stage/nested-launcher-strict: ' + nested_result.stderr[-300:],
               nested_result.returncode == 0 and nested_result.stdout.strip() == 'refused')
        if outside.exists():
            outside.unlink()

        # The bind helper itself creates socket files only beneath the domain's roots, so a path
        # whose components are swapped for links after the broker resolved it still cannot land
        # elsewhere: asked directly for an outside path, it refuses.
        spec = importlib.util.spec_from_file_location('v208_boundary', ROOT / 'scripts/agent_sandbox.py')
        boundary = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(boundary)
        import socket as _v208_socket
        roots = top / 'broker-root'
        roots.mkdir()
        broker = boundary.Broker([roots], network=False)
        try:
            outcomes = []
            for target in (roots / 'inside', outside):
                sock = _v208_socket.socket(_v208_socket.AF_UNIX)
                try:
                    broker._bind_path(sock.fileno(), b'\x01\x00' + os.fsencode(target) + b'\0')
                    outcomes.append('bound')
                except PermissionError:
                    outcomes.append('refused')
                finally:
                    sock.close()
        finally:
            broker.close()
        expect('VELDO-0208 confined-stage/bind-helper-confined-to-roots: ' + repr(outcomes),
               outcomes == ['bound', 'refused'] and (roots / 'inside').is_socket() and not outside.exists())
        if outside.exists():
            outside.unlink()

        # ---- unit: a gate the confined stage runs for another tree (the init scaffold's) ----------
        scaffold = top / 'scaffold-root'
        scaffold.mkdir()
        (scaffold / 'run.py').write_text(
            'import importlib.util, subprocess, sys, tempfile\nfrom pathlib import Path\n'
            'spec = importlib.util.spec_from_file_location("isc", ' + repr(str(ROOT / '.veldo/init_scaffold.py')) + ')\n'
            'm = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n'
            'with tempfile.TemporaryDirectory() as d:\n'
            '    m.scaffold(d)\n'
            '    r = subprocess.run(["bash", str(Path(d) / "scripts/verify.sh")], capture_output=True, text=True)\n'
            '    print(r.stdout[-400:] + r.stderr[-400:]); sys.exit(r.returncode)\n')
        nested_gate = confined(scaffold, [sys.executable, str(scaffold / 'run.py')], timeout=300)
        expect('VELDO-0208 confined-stage/nested-scaffold-gate-green: ' + nested_gate.stdout[-300:],
               nested_gate.returncode == 0 and 'GATE: GREEN' in nested_gate.stdout
               and 'refused to start' not in nested_gate.stdout)

        # ---- packaging: an installed pack's gate names its own repository ------------------------
        # verify.sh exports the authority's common directory; the stage is run with it exported.
        common = subprocess.run([sys.executable, '-I', '-S', str(ROOT / '.veldo/candidate_git.py'),
                                 '--authority-common'], capture_output=True, text=True).stdout.strip()
        packaged = confined(ROOT, [sys.executable, 'scripts/check_install_and_run.py', '--pack', 'claude'],
                            dict(os.environ, VELDO_EXPECTED_GIT_COMMON=common), timeout=300)
        expect('VELDO-0208 confined-stage/installed-pack-gate-green: ' + (packaged.stdout + packaged.stderr)[-300:],
               packaged.returncode == 0 and 'adopter gate GREEN' in packaged.stdout
               and 'candidate Git boundary refused' not in packaged.stdout)

        # ---- mutation: a worker under the worker boundary serves sockets and terminals -----------
        gate = importlib.util.module_from_spec(importlib.util.spec_from_file_location(
            'v208_gate', ROOT / 'scripts/check_gate_mutations.py'))
        gate.__spec__.loader.exec_module(gate)
        worker_root = top / 'worker-input'
        (worker_root / 'scripts/suites').mkdir(parents=True)
        (worker_root / '.veldo').mkdir()
        (worker_root / 'scripts/suites/shared.py').write_text(
            'from pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\n'
            'def expect(name, condition): pass\n')
        (worker_root / 'scripts/suites/fixture.py').write_text(
            'import os, socket, tempfile, threading\n'
            'path = os.path.join(tempfile.mkdtemp(), "s")\n'
            'srv = socket.socket(socket.AF_UNIX); srv.bind(path); srv.listen()\n'
            'def serve():\n    c, _ = srv.accept(); c.sendall(c.recv(8).upper()); c.close()\n'
            'threading.Thread(target=serve, daemon=True).start()\n'
            'c = socket.socket(socket.AF_UNIX); c.connect(path); c.sendall(b"ping")\n'
            'served = c.recv(8) == b"PING"\n'
            'master, terminal = os.openpty()\n'
            'value = (ROOT / ".veldo" / "subject.py").read_text()\n'
            'expect("fixture target", served and os.isatty(terminal) and value == "good")\n')
        (worker_root / '.veldo/subject.py').write_text('good')
        case = dict(identity='check_teeth_mutations.py:socket-worker', name='socket-worker',
                    driver='check_teeth_mutations.py', suite='fixture.py', rows=['target'],
                    module='subject.py', old='good', new='bad')
        observed, stderr = {}, {}
        for mode in ('baseline', 'mutant'):
            scratch = top / ('worker-home-' + mode)
            scratch.mkdir()
            job = top / (mode + '-job.json')
            job.write_text(json.dumps(dict(case=case, mode=mode)))
            channel = os.open(top / (mode + '.ownership'), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                run = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'scripts/reuse_worker.py'), 'worker',
                                      str(worker_root), str(channel), str(job)], cwd=worker_root,
                                     pass_fds=(channel,), env=gate.fixed_env(scratch),
                                     capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
            finally:
                os.close(channel)
            try:
                observed[mode] = json.loads(run.stdout)['observation']['failed_rows']
            except (ValueError, KeyError):
                observed[mode] = None
            stderr[mode] = run.stderr[-300:]
        if not inside:
            expect('VELDO-0208 confined-stage/worker-serves-socket-and-terminal: ' + repr((observed, stderr)),
                   observed == {'baseline': [], 'mutant': ['fixture target']})
        else:
            # Inside the gate a worker is a nested domain: strict, so the fixture's socket is refused.
            expect('VELDO-0208 confined-stage/worker-nested-strict: ' + repr((observed, stderr)),
                   observed == {'baseline': None, 'mutant': None}
                   and all('Operation not permitted' in text for text in stderr.values()))

        # ---- the stamp: a failed stage is a clean RED in the requested mode, never a traceback ---
        receipt = top / 'failed-receipt.json'
        receipt.write_text(json.dumps({'status': 'failed', 'error': 'driver_error', 'reused': 0,
                                       'force_fresh': True}))
        empty = top / 'empty-receipt.json'
        empty.write_text('')
        for name, source in (('failed', receipt), ('empty', empty)):
            reduced = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'scripts/reuse_stamp.py'),
                                      str(source), '1', 'a' * 40], capture_output=True, text=True, timeout=30)
            expect('VELDO-0208 confined-stage/stamp-' + name + '-receipt-clean-red: ' + reduced.stderr[-200:],
                   reduced.returncode == 1 and 'Traceback' not in reduced.stderr
                   and 'the gate is RED' in reduced.stderr
                   and json.loads('{' + reduced.stdout.strip() + '}') == {
                       'force_fresh': True, 'reused': {'mutation': None, 'unit': 0}})




def _v208_unconfined_leg():
    """The unconfined leg (owner decision, Telegram 32403-32407, 2026-10-07): the suites the
    authority's scripts/gate_unconfined.json lists run outside the confinement in a named leg, every
    other suite stays confined even if it asks, and the list is a protected file. Driven through the
    real leg runner, the real launcher and the real dispatcher over a fixture candidate whose suites
    probe a directory outside the candidate: the confined leg cannot write there, the unconfined
    leg can. Run by the gate's own confined leg, the fixture's unconfined leg is still inside the
    outer domain, which grants that directory, so the observation holds in both places."""
    import ast
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile

    spec = importlib.util.spec_from_file_location('gate_legs_under_test', ROOT / 'scripts/gate_legs.py')
    L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
    sys.path.insert(0, str(ROOT / 'scripts'))
    try:
        import run_scope as RSL
    finally:
        sys.path.pop(0)

    # ---- the declared list: valid, each entry with its reason, and the stages verify.sh runs -----
    document, digest = L.load()
    listed = {e['suite']: e.get('rows') for e in document['suites']}
    gate_text = (ROOT / 'scripts/verify.sh').read_text()
    declared_commands = {name: re.search(r'^CHECK_%s="required:(.*)"$' % name, gate_text, re.M).group(1)
                         for name in ('unit', 'integration')}
    control_plane = ['62_0039', '63_0040', '63_0049', '64_0050', '66_0042', '67_0041', '67_0135', '71_0076',
                     '71_0130', '71_0138', '73_0139', '78_0060', '79_0061', '80_0155', '81_0156', '82_0129',
                     '82_0141', '83_0154', '85_0158', '85_0171', '86_0127', '86_0148', '86_0189', '87_0170',
                     '91_0167', '92_0088', '93_0152', '94_0162', '95_0203', '96_0204']
    manifest = [s['name'] for s in json.loads((ROOT / 'scripts/suites/manifest.json').read_text())['suites']]
    whole = sorted(n for n, rows in listed.items() if rows is None)
    expected_whole = sorted([n for n in manifest for short in control_plane + ['65_0067']
                             if n.startswith(short.replace('_', '_veldo_', 1) + '_')])
    expect('VELDO-0208 unconfined-leg/declared-list: ' + repr(sorted(set(whole) ^ set(expected_whole))),
           document['stages'] == declared_commands and len(expected_whole) == 31 and whole == expected_whole
           and {n: r for n, r in listed.items() if r} == {'100_veldo_0207_case_reuse': 'strace',
                                                         '101_veldo_0208_landing_reuse': 'strace'}
           and all(n in manifest for n in listed)
           and all(len(e['reason']) > 30 for e in document['suites']))
    # A suite that builds on a suite listed whole, loading its file directly or through a proof
    # module it loads, needs what that suite needs, so it is listed too. 95_0203 loads 85_0171's
    # host fixture through its own proof module; the classification missed it, and the first full
    # gate with the leg failed its 35 rows in the confined leg. (This comment names no proof path,
    # so this suite's own text does not read as loading one.)
    sharers = {}
    for name in manifest:
        if listed.get(name, '') is None:
            continue
        text = (ROOT / 'scripts/suites' / (name + '.py')).read_text()
        loaded = [text] + [(ROOT / rel).read_text() for rel in sorted(set(re.findall(r'proof/VELDO-\d{4}/[\w.]+\.py', text)))
                           if (ROOT / rel).is_file()]
        shared = sorted(w for w in whole if any('suites/%s.py' % w in body for body in loaded))
        if shared:
            sharers[name] = shared
    expect('VELDO-0208 unconfined-leg/fixture-sharers-are-listed: ' + repr(sharers), not sharers)

    # ---- the list is protected, read from the authority, and recorded in the stamp --------------
    front = V.front_matter((ROOT / 'specs/VELDO-0208-single-user-landing-reuse.md').read_text(), 'VELDO-0208')
    expect('VELDO-0208 unconfined-leg/list-is-protected',
           {'scripts/gate_unconfined.json', 'scripts/gate_legs.py'} <= set(P.protected_patterns())
           and {'scripts/gate_unconfined.json', 'scripts/gate_legs.py'} <= set(front['protected_paths']))
    # The candidate's dispatcher applies the list, so it is protected with it; the listed suites are
    # not, because review of the candidate, not a protected path, is the safeguard for their code.
    dispatcher_files = {'scripts/selftest.py', 'scripts/run_scope.py', 'scripts/suites/shared.py',
                        'scripts/check_first_use.py'}
    listed_files = ['scripts/suites/%s.py' % name for name in listed]
    expect('VELDO-0208 unconfined-leg/dispatcher-is-protected',
           dispatcher_files <= set(P.protected_patterns()) and dispatcher_files <= set(front['protected_paths'])
           and all((ROOT / f).is_file() for f in dispatcher_files) and len(listed_files) == 33
           and not [f for f in listed_files for pattern in P.protected_patterns()
                    if __import__('fnmatch').fnmatch(f, pattern)])

    # ---- which rows each leg owns ----------------------------------------------------------------
    env = {'VELDO_GATE_UNCONFINED': 'whole,rowed:strace', 'VELDO_GATE_DECLARATION': 'sha256:' + '0' * 64}
    table = {(leg, suite, rows): RSL.leg_runs(suite, rows, dict(env, VELDO_GATE_LEG=leg))
             for leg in ('confined', 'unconfined') for suite in ('whole', 'rowed', 'asks')
             for rows in (None, 'strace')}
    try:
        RSL.gate_leg({'VELDO_GATE_LEG': 'outside'})
    except RSL.LegRefused:
        bad_leg = True
    else:
        bad_leg = False
    try:
        RSL.gate_leg(dict(env, VELDO_GATE_LEG='confined', VELDO_GATE_UNCONFINED='../x'))
    except RSL.LegRefused:
        bad_entry = True
    else:
        bad_entry = False
    expect('VELDO-0208 unconfined-leg/rows-each-leg-owns',
           table == {('confined', 'whole', None): True, ('confined', 'whole', 'strace'): True,
                     ('confined', 'rowed', None): True, ('confined', 'rowed', 'strace'): False,
                     ('confined', 'asks', None): True, ('confined', 'asks', 'strace'): True,
                     ('unconfined', 'whole', None): True, ('unconfined', 'whole', 'strace'): True,
                     ('unconfined', 'rowed', None): False, ('unconfined', 'rowed', 'strace'): True,
                     ('unconfined', 'asks', None): False, ('unconfined', 'asks', 'strace'): False}
           and RSL.leg_runs('asks', 'strace', {}) and bad_leg and bad_entry)

    # Only the complete set gate_legs.py sets is a leg: a leg with an empty list, a list without its
    # digest, a stray variable on its own and a digest that is not one are each refused, never read.
    def refused(environ):
        try:
            RSL.gate_leg(environ)
        except RSL.LegRefused:
            return True
        return False
    complete = dict(env, VELDO_GATE_LEG='unconfined')
    expect('VELDO-0208 unconfined-leg/only-the-runners-complete-set-is-a-leg',
           RSL.gate_leg(complete) == ('unconfined', {'whole': None, 'rowed': 'strace'})
           and refused(dict(complete, VELDO_GATE_UNCONFINED=''))
           and refused({k: v for k, v in complete.items() if k != 'VELDO_GATE_DECLARATION'})
           and refused({'VELDO_GATE_LEG': 'unconfined', 'VELDO_GATE_UNCONFINED': ''})
           and refused({'VELDO_GATE_UNCONFINED': 'whole'}) and refused({'VELDO_GATE_LEG': ''})
           and refused(dict(complete, VELDO_GATE_DECLARATION='sha256:short'))
           and refused(dict(complete, VELDO_GATE_UNCONFINED='whole,,rowed:strace'))
           and refused(dict(complete, VELDO_GATE_UNCONFINED='whole:')))

    # ---- a fixture candidate run through the real leg runner -------------------------------------
    shared_source = (ROOT / 'scripts/suites/shared.py').read_text()
    real_helpers = ''.join(ast.get_source_segment(shared_source, node) + '\n\n'
                           for node in ast.parse(shared_source).body
                           if isinstance(node, ast.FunctionDef) and node.name in ('suite_file', 'leg_runs'))
    fixture_shared = ('import os\nimport sys\nfrom pathlib import Path\n'
        'ROOT = Path(__file__).resolve().parents[2]\nsys.path.insert(0, str(ROOT / "scripts"))\n'
        'PASS = FAIL = 0\nSCOPE = None\n' + real_helpers +
        'def expect(name, condition):\n    global PASS, FAIL\n    PASS += bool(condition); FAIL += not condition\n'
        'def report():\n    print(SCOPE.aggregate_line(PASS, FAIL)); return SCOPE.exit_code(FAIL)\n'
        'def probe(label):\n    leg = os.environ.get("VELDO_GATE_LEG", "none")\n'
        '    try:\n        (Path(os.environ["V208_PROBE_OUTSIDE"]) / (label + "." + leg)).write_text("x")\n'
        '        outcome = "wrote"\n    except OSError:\n        outcome = "refused"\n'
        '    print("V208-PROBE %s.%s %s" % (label, leg, outcome), flush=True)\n'
        '    print("V208-COMMON %s.%s %s" % (label, leg, os.environ.get("VELDO_EXPECTED_GIT_COMMON", "absent")),'
        ' flush=True)\n    expect(label, True)\n')
    bodies = {'01_listed': 'probe("01_listed")\n',
              '02_asks': 'if leg_runs("strace"):\n    probe("02_asks.strace")\nif leg_runs():\n    probe("02_asks")\n',
              '03_rows': 'if leg_runs():\n    probe("03_rows")\nif leg_runs("strace"):\n    probe("03_rows.strace")\n'}
    driver = ('import importlib.util, sys\n'
              's = importlib.util.spec_from_file_location("gate_legs", sys.argv[1])\n'
              'm = importlib.util.module_from_spec(s); s.loader.exec_module(m)\n'
              'sys.exit(m.run_stage(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], path=sys.argv[6]))\n')
    with tempfile.TemporaryDirectory(prefix='v208-legs-') as temporary:
        top = Path(temporary)
        candidate, outside = top / 'candidate', top / 'outside'
        (candidate / 'scripts/suites').mkdir(parents=True); outside.mkdir()
        for name in ('selftest.py', 'run_scope.py'):
            shutil.copyfile(ROOT / 'scripts' / name, candidate / 'scripts' / name)
        (candidate / 'scripts/suites/shared.py').write_text(fixture_shared)
        for name, body in bodies.items():
            (candidate / 'scripts/suites' / (name + '.py')).write_text(body)
        (candidate / 'scripts/suites/manifest.json').write_text(json.dumps({
            'schema': 'veldo.suites/v1', 'entry': 'selftest.py', 'shared': 'shared.py',
            'suites': [{'name': n, 'file': n + '.py'} for n in bodies]}))
        authority_list = top / 'gate_unconfined.json'
        authority_list.write_text(json.dumps(dict(document, stages={'unit': 'python3 scripts/selftest.py'},
            suites=[{'suite': '01_listed', 'reason': 'fixture: needs what the domain refuses'},
                    {'suite': '03_rows', 'rows': 'strace', 'reason': 'fixture: rows that trace a worker'}])))
        # The candidate's own copy of the list is the authority's plus 02_asks; only the authority's counts.
        asking = json.loads(authority_list.read_text())
        asking['suites'].append({'suite': '02_asks', 'reason': 'the candidate asks to leave the domain'})
        (candidate / 'scripts/gate_unconfined.json').write_text(json.dumps(asking))

        def stage(name, command, listing=authority_list, extra=None, root=candidate):
            for marker in outside.iterdir():
                marker.unlink()
            record = top / ('record-' + name)
            record.unlink(missing_ok=True)
            result = subprocess.run([sys.executable, '-I', '-S', '-c', driver, str(ROOT / 'scripts/gate_legs.py'),
                                     str(root), name, command, str(record), str(listing)],
                                    capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                                    env=dict(os.environ, V208_PROBE_OUTSIDE=str(outside), **(extra or {})))
            # The candidate tree is read-only in the gate domain, so each probe reports on stdout.
            markers = dict(line.split()[1:3] for line in result.stdout.splitlines()
                           if line.startswith('V208-PROBE '))
            return result, markers, record

        result, markers, record = stage('unit', 'python3 scripts/selftest.py')
        output = result.stdout + result.stderr
        expect('VELDO-0208 unconfined-leg/listed-suite-runs-unconfined-and-named: ' + output[-600:],
               result.returncode == 0
               and 'unit: UNCONFINED LEG - runs outside the confinement by owner decision' in output
               and '2 entries: 01_listed, 03_rows:strace' in output
               and 'unit: confined leg: pass' in output and 'unit: unconfined leg: pass' in output
               and 'selftest leg unconfined:' in output and 'selftest leg confined:' in output
               and markers.get('01_listed.unconfined') == 'wrote' and '01_listed.confined' not in markers)
        expect('VELDO-0208 unconfined-leg/unlisted-suite-stays-confined-even-if-it-asks: ' + repr(markers),
               markers.get('02_asks.confined') == 'refused' and markers.get('02_asks.strace.confined') == 'refused'
               and not [m for m in markers if m.startswith('02_asks') and m.endswith('.unconfined')]
               and not (outside / '02_asks.confined').exists())
        expect('VELDO-0208 unconfined-leg/listed-rows-only-leave: ' + repr(markers),
               markers.get('03_rows.confined') == 'refused' and markers.get('03_rows.strace.unconfined') == 'wrote'
               and '03_rows.strace.confined' not in markers and '03_rows.unconfined' not in markers)
        # The authority's own Git common directory, which verify.sh exports for its launchers, reaches
        # candidate code in neither leg. The unconfined leg once handed it on, so a listed suite's gate
        # for a fixture repository checked that repository against the authority's directory and
        # refused it: 0050 and 0148 failed inside the real gate and passed in every run without it.
        held, _, _ = stage('unit', 'python3 scripts/selftest.py',
                           extra={'VELDO_EXPECTED_GIT_COMMON': str(top / 'authority-common')})
        seen = dict(line.split()[1:3] for line in held.stdout.splitlines() if line.startswith('V208-COMMON '))
        expect('VELDO-0208 unconfined-leg/authority-git-common-reaches-neither-leg: ' + repr(seen),
               held.returncode == 0
               and {'01_listed.unconfined', '03_rows.strace.unconfined', '02_asks.confined',
                    '03_rows.confined'} <= set(seen)
               and set(seen.values()) == {'absent'})
        stamped = L.stamp(record)
        # verify.sh's own stamp and event lines, executed over this record, an empty one and a
        # corrupt one: the leg is in both records when it was expected and ran, absent when none was
        # expected, RED when unread.
        stamp_block = gate_text[gate_text.index('UNCONFINED_FIELD=""'):]
        stamp_block = stamp_block[:stamp_block.index('veldo_write_stamp() {')] + \
            stamp_block[stamp_block.index('veldo_write_stamp() {'):].split('\n}', 1)[0] + '\n}\n'
        def written(legs_record, expected='unit', before='', authority=ROOT):
            program = ('VELDO_AUTHORITY=' + str(authority) + '\nVELDO_LEGS_RECORD=' + str(legs_record) + '\n'
                       'VELDO_LEGS_EXPECTED=' + expected + '\n'
                       'FAIL=0\nSTATUS=green\nEVENT=gate.passed\nCOMMIT=' + 'a' * 40 + '\nTS=fixture\nRAN=1\nNA=0\n'
                       'VERSION_JSON=null\nTREE_JSON=null\nREUSE_JSON=\'"force_fresh":false,"reused":{"mutation":0,"unit":0}\'\n'
                       + before + stamp_block + 'veldo_write_stamp "$1"\nprintf "%s\\n" "$EVENT_LINE" > "$2"\n')
            outputs = top / 'written-stamp', top / 'written-event'
            for o in outputs:
                o.unlink(missing_ok=True)
            ran = subprocess.run(['bash', '-c', program, 'fixture', *map(str, outputs)],
                                 capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                                 env=dict({k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')},
                                          V208_PROBE_OUTSIDE=str(outside)))
            return ran.returncode, [json.loads(o.read_text()) for o in outputs]
        empty = top / 'empty-record'; empty.write_text('')
        corrupt = top / 'corrupt-record'; corrupt.write_text('{"stage": "unit"\n')
        with_leg, without_leg, unread = written(record), written(empty, expected=''), written(corrupt)
        expect('VELDO-0208 unconfined-leg/stamp-and-event-carry-the-leg: ' + repr((with_leg, without_leg, unread)),
               all(code == 0 for code, _ in (with_leg, without_leg, unread))
               and all(document['unconfined'] == stamped for document in with_leg[1])
               and all(document['status' if 'status' in document else 'type'] in ('green', 'gate.passed')
                       for document in with_leg[1])
               and all('unconfined' not in document for document in without_leg[1])
               and all(document['unconfined'] is None for document in unread[1])
               and unread[1][0]['status'] == 'red' and unread[1][1]['type'] == 'gate.failed')
        refused_stamp = subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'scripts/gate_legs.py'), '--stamp',
                                        str(corrupt)], capture_output=True, text=True, timeout=30)
        expect('VELDO-0208 unconfined-leg/stamp-names-the-leg: ' + repr(stamped),
               stamped == {'declaration': 'sha256:' + __import__('hashlib').sha256(
                               authority_list.read_bytes()).hexdigest(),
                           'legs': {'unit': ['01_listed', '03_rows:strace']}}
               and L.stamp(empty) == {} and L.stamp(top / 'never-written') == {}
               and refused_stamp.returncode == 1 and refused_stamp.stdout.strip() == 'null'
               and 'the gate is RED' in refused_stamp.stderr)

        # An expected leg whose record is gone, empty or short of a stage is RED with the field null,
        # never absent: candidate code in the unconfined leg can reach the record.
        missing = [written(top / 'deleted-record'), written(empty), written(record, expected='unit,integration')]
        expect('VELDO-0208 unconfined-leg/expected-leg-without-its-record-is-red-and-null: ' + repr(missing),
               all(code == 0 and all('unconfined' in d and d['unconfined'] is None for d in documents)
                   and documents[0]['status'] == 'red' and documents[1]['type'] == 'gate.failed'
                   for code, documents in missing))

        # A stage the list does not declare, or a command other than the declared one, is confined
        # whole, and a caller's leg variables never reach it.
        asked = {'VELDO_GATE_LEG': 'unconfined', 'VELDO_GATE_UNCONFINED': '02_asks',
                 'VELDO_GATE_DECLARATION': 'sha256:' + '0' * 64}
        other, other_markers, other_record = stage('integration', 'python3 scripts/selftest.py', extra=asked)
        changed, changed_markers, changed_record = stage('unit', 'python3 scripts/selftest.py ', extra=asked)
        expect('VELDO-0208 unconfined-leg/undeclared-stage-is-confined-whole: ' + repr((other_markers, changed_markers)),
               other.returncode == 0 and changed.returncode == 0
               and 'UNCONFINED' not in other.stdout + changed.stdout
               and other_markers == changed_markers == {'01_listed.none': 'refused', '02_asks.none': 'refused',
                   '02_asks.strace.none': 'refused', '03_rows.none': 'refused', '03_rows.strace.none': 'refused'}
               and not other_record.exists() and not changed_record.exists())

        # An invalid list runs nothing at all, in either leg.
        broken = top / 'broken.json'
        broken.write_text(json.dumps(dict(json.loads(authority_list.read_text()),
                                          suites=[{'suite': '01_listed', 'reason': ''}])))
        invalid, invalid_markers, invalid_record = stage('unit', 'python3 scripts/selftest.py', listing=broken)
        expect('VELDO-0208 unconfined-leg/invalid-list-runs-nothing: ' + invalid.stdout[-300:],
               invalid.returncode == 1 and 'is invalid (01_listed has no reason)' in invalid.stdout
               and invalid_markers == {} and not invalid_record.exists())

        # A leg that tests nothing is refused, never a pass: the reviewer's empty-list run, a leg
        # whose list names no suite of the manifest, and a leg whose listed suite asserts no row.
        def dispatcher(extra):
            return subprocess.run([sys.executable, str(candidate / 'scripts/selftest.py')], cwd=str(candidate),
                                  capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
                                  env=dict({k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')},
                                           V208_PROBE_OUTSIDE=str(outside), **extra))
        leg_of = {'VELDO_GATE_LEG': 'unconfined', 'VELDO_GATE_DECLARATION': 'sha256:' + '0' * 64}
        empty_list = dispatcher({'VELDO_GATE_LEG': 'unconfined', 'VELDO_GATE_UNCONFINED': ''})
        no_suite = dispatcher(dict(leg_of, VELDO_GATE_UNCONFINED='99_absent'))
        no_row = dispatcher(dict(leg_of, VELDO_GATE_UNCONFINED='03_rows:other'))
        ran = dispatcher(dict(leg_of, VELDO_GATE_UNCONFINED='01_listed'))
        expect('VELDO-0208 unconfined-leg/leg-that-tests-nothing-is-refused: '
               + repr([(r.returncode, r.stdout[-200:]) for r in (empty_list, no_suite, no_row, ran)]),
               all(r.returncode == 2 and ' passed, ' not in r.stdout for r in (empty_list, no_suite, no_row))
               and 'set without VELDO_GATE_DECLARATION' in empty_list.stdout
               and 'LEG_RAN_NOTHING: no suite of this manifest' in no_suite.stdout
               and 'LEG_RAN_NOTHING: the 1 suite(s) of this leg asserted no row' in no_row.stdout
               and ran.returncode == 0 and 'selftest: 1 passed, 0 failed' in ran.stdout)

        # The gate's fallback with no list in the authority runs the stage confined whole and drops a
        # caller's leg variables, even a complete set that would otherwise be honoured.
        fallback = top / 'authority-without-list'
        (fallback / 'scripts').mkdir(parents=True)
        (fallback / 'scripts/gate_candidate.py').symlink_to(ROOT / 'scripts/gate_candidate.py')
        functions = ''.join(re.search(r'^%s\(\) \{\n.*?^\}\n' % name, gate_text, re.S | re.M).group(0)
                            for name in ('veldo_candidate', 'veldo_stage'))
        for marker in outside.iterdir():
            marker.unlink()
        leaked = subprocess.run(['bash', '-c', 'VELDO_AUTHORITY=%s\nVELDO_LEGS_RECORD=%s\n%s'
                                 'cd %s && veldo_stage unit "python3 scripts/selftest.py"'
                                 % (fallback, top / 'fallback-record', functions, candidate)],
                                capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                                env=dict(os.environ, V208_PROBE_OUTSIDE=str(outside), **asked))
        leaked_markers = dict(line.split()[1:3] for line in leaked.stdout.splitlines()
                              if line.startswith('V208-PROBE '))
        expect('VELDO-0208 unconfined-leg/fallback-drops-the-callers-leg-variables: '
               + repr((leaked.returncode, leaked_markers, leaked.stdout[-300:])),
               leaked.returncode == 0 and 'selftest leg' not in leaked.stdout
               and leaked_markers == {'01_listed.none': 'refused', '02_asks.none': 'refused',
                   '02_asks.strace.none': 'refused', '03_rows.none': 'refused', '03_rows.strace.none': 'refused'}
               and not (top / 'fallback-record').exists())

        # The engine's gate, which adopters install, drops a caller's leg variables the same way: it
        # runs no unconfined leg, so a candidate's dispatcher never reads one from the caller.
        engine_text = (ROOT / 'engine/scripts/verify.sh').read_text()
        engine_candidate = re.search(r'^veldo_candidate\(\) \{\n.*?^\}\n', engine_text, re.S | re.M).group(0)
        for marker in outside.iterdir():
            marker.unlink()
        engine_leaked = subprocess.run(['bash', '-c', 'VELDO_AUTHORITY=%s\n%s'
                                        'cd %s && veldo_candidate bash -c "python3 scripts/selftest.py"'
                                        % (fallback, engine_candidate, candidate)],
                                       capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                                       env=dict(os.environ, V208_PROBE_OUTSIDE=str(outside), **asked))
        engine_markers = dict(line.split()[1:3] for line in engine_leaked.stdout.splitlines()
                              if line.startswith('V208-PROBE '))
        expect('VELDO-0208 unconfined-leg/engine-gate-drops-the-callers-leg-variables: '
               + repr((engine_leaked.returncode, engine_markers, engine_leaked.stdout[-300:])),
               'veldo_stage' not in engine_text and 'gate_legs' not in engine_text
               and engine_leaked.returncode == 0 and 'selftest leg' not in engine_leaked.stdout
               and engine_markers == {'01_listed.none': 'refused', '02_asks.none': 'refused',
                   '02_asks.strace.none': 'refused', '03_rows.none': 'refused', '03_rows.strace.none': 'refused'})

        # The same through verify.sh's own veldo_stage: it learns from the authority's list that the
        # unit stage expects a leg before the stage runs, so deleting the record after the leg ran
        # (what candidate code in the unconfined leg can do) is RED and null; a stage the list does
        # not declare expects nothing and the field stays absent.
        authority = top / 'authority-with-list'
        (authority / 'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/gate_legs.py', authority / 'scripts/gate_legs.py')
        shutil.copyfile(authority_list, authority / 'scripts/gate_unconfined.json')
        (authority / 'scripts/gate_candidate.py').symlink_to(ROOT / 'scripts/gate_candidate.py')
        def through_stage(stage, command, delete):
            live = top / 'live-record'
            live.write_text('')
            return written(live, expected='', authority=authority, before=functions
                           + 'cd %s && veldo_stage %s "%s"\n' % (candidate, stage, command)
                           + ('rm -f "$VELDO_LEGS_RECORD"\n' if delete else ''))
        kept = through_stage('unit', 'python3 scripts/selftest.py', False)
        deleted = through_stage('unit', 'python3 scripts/selftest.py', True)
        undeclared = through_stage('lint', 'true', False)
        expect('VELDO-0208 unconfined-leg/deleted-record-after-an-expected-leg-is-red-and-null: '
               + repr((kept, deleted, undeclared)),
               all(d.get('unconfined') == {'declaration': 'sha256:' + __import__('hashlib').sha256(
                       authority_list.read_bytes()).hexdigest(), 'legs': {'unit': ['01_listed', '03_rows:strace']}}
                   for d in kept[1]) and kept[1][0]['status'] == 'green'
               and all('unconfined' in d and d['unconfined'] is None for d in deleted[1])
               and deleted[1][0]['status'] == 'red' and deleted[1][1]['type'] == 'gate.failed'
               and all('unconfined' not in d for d in undeclared[1]) and undeclared[1][0]['status'] == 'green')

        # The list is read from the authority, observed rather than read off verify.sh: verify.sh's own
        # veldo_stage over a candidate whose copy of the list adds 02_asks runs 02_asks confined, and
        # the record names the authority's list and entries, never the candidate's.
        for marker in outside.iterdir():
            marker.unlink()
        own_record = top / 'own-list-record'
        own = subprocess.run(['bash', '-c', 'VELDO_AUTHORITY=%s\nVELDO_LEGS_RECORD=%s\nVELDO_LEGS_EXPECTED=\n%s'
                              'cd %s && veldo_stage unit "python3 scripts/selftest.py" && echo "expected=$VELDO_LEGS_EXPECTED"'
                              % (authority, own_record, functions, candidate)],
                             capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                             env=dict({k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')},
                                      V208_PROBE_OUTSIDE=str(outside)))
        own_markers = dict(line.split()[1:3] for line in own.stdout.splitlines() if line.startswith('V208-PROBE '))
        expect('VELDO-0208 unconfined-leg/list-read-from-the-authority: ' + repr((own.returncode, own_markers)),
               L.DECLARATION == ROOT / 'scripts/gate_unconfined.json'
               and '[ -e "$VELDO_AUTHORITY/scripts/gate_unconfined.json" ]' in gate_text
               and 'else veldo_stage "$name" "$cmd"; fi' in gate_text
               and '02_asks' in (candidate / 'scripts/gate_unconfined.json').read_text()
               and own.returncode == 0 and 'expected=unit' in own.stdout
               and own_markers.get('01_listed.unconfined') == 'wrote'
               and own_markers.get('02_asks.confined') == 'refused'
               and not [m for m in own_markers if m.startswith('02_asks') and m.endswith('.unconfined')]
               and '02_asks' not in own.stdout.split('UNCONFINED LEG', 1)[-1].split('\n', 1)[0]
               and L.stamp(own_record) == {'declaration': 'sha256:' + __import__('hashlib').sha256(
                   authority_list.read_bytes()).hexdigest(), 'legs': {'unit': ['01_listed', '03_rows:strace']}})

        # No file in scripts/ or scripts/suites/ shadows a standard-library module the dispatcher
        # imports. A candidate scripts/json.py and suites/tempfile.py that announce their import run
        # through both legs of the real runner and dispatcher, with shared.py's own imports, and
        # through check_first_use.py, and neither is imported; the control shows each plant is live
        # for an ordinary script in the same directory. suites/tempfile.py is enumerated, so the
        # dispatcher reaches shared.py rather than refusing it as SUITE_NOT_ENUMERATED.
        shadow = top / 'shadow'
        shutil.copytree(candidate, shadow)
        shutil.copyfile(ROOT / 'scripts/check_first_use.py', shadow / 'scripts/check_first_use.py')
        real_imports = ''.join(ast.get_source_segment(shared_source, node) + '\n'
                               for node in ast.parse(shared_source).body
                               if isinstance(node, (ast.Import, ast.ImportFrom)))
        (shadow / 'scripts/suites/shared.py').write_text(real_imports + fixture_shared)
        for planted in ('scripts/json.py', 'scripts/suites/tempfile.py'):
            module = Path(planted).stem
            (shadow / planted).write_text('if __name__ == %r:\n    print("V208-SHADOWED %s", flush=True)\n'
                                          % (module, module))
            (shadow / planted).with_name('control_%s.py' % module).write_text('import %s\n' % module)
        shadow_manifest = json.loads((shadow / 'scripts/suites/manifest.json').read_text())
        shadow_manifest['suites'].append({'name': 'tempfile', 'file': 'tempfile.py'})
        shadow_manifest['suites'].append({'name': 'control_tempfile', 'file': 'control_tempfile.py'})
        (shadow / 'scripts/suites/manifest.json').write_text(json.dumps(shadow_manifest))
        legs, _, _ = stage('unit', 'python3 scripts/selftest.py', root=shadow)
        first_use = subprocess.run([sys.executable, 'scripts/check_first_use.py', '--refuse-this'], cwd=str(shadow),
                                   capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        controls = [subprocess.run([sys.executable, str(shadow / relative)], cwd=str(shadow), capture_output=True,
                                   text=True, timeout=60, stdin=subprocess.DEVNULL).stdout
                    for relative in ('scripts/control_json.py', 'scripts/suites/control_tempfile.py')]
        shadow_out = legs.stdout + legs.stderr
        expect('VELDO-0208 unconfined-leg/dispatcher-never-imports-a-candidate-stdlib-shadow: '
               + repr((legs.returncode, shadow_out[-400:], first_use.returncode, first_use.stdout[-200:], controls)),
               {'import json', 'import subprocess', 'import tempfile'} <= set(real_imports.splitlines())
               and legs.returncode == 0 and 'V208-SHADOWED' not in shadow_out
               and 'selftest leg confined:' in shadow_out and 'selftest leg unconfined:' in shadow_out
               and 'unit: confined leg: pass' in shadow_out and 'unit: unconfined leg: pass' in shadow_out
               and first_use.returncode == 2 and 'UNRECOGNISED_FLAG' in first_use.stdout
               and 'V208-SHADOWED' not in first_use.stdout + first_use.stderr
               and controls == ['V208-SHADOWED json\n', 'V208-SHADOWED tempfile\n'])

        # The list is optional in the authority (with none, every stage is confined: the first
        # landing's authority predates it, and an adopter never receives one), so an authority
        # without it still has an identity: the list is recorded as absent, a stable value no digest
        # equals, while any other missing authority file is still an error. The same authority runs
        # verify.sh's veldo_stage confined whole.
        bare = top / 'authority-bare'
        evidence = importlib.util.spec_from_file_location('v208_bare_evidence', ROOT / '.veldo/reuse_evidence.py')
        E_bare = importlib.util.module_from_spec(evidence); evidence.loader.exec_module(E_bare)
        for relative in E_bare.AUTHORITY_FILES:
            if relative not in E_bare.OPTIONAL_AUTHORITY_FILES:
                (bare / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, bare / relative)
        def bare_identity():
            loaded = importlib.util.spec_from_file_location('v208_bare_identity', bare / '.veldo/reuse_evidence.py')
            module = importlib.util.module_from_spec(loaded); loaded.loader.exec_module(module)
            try:
                return module.authority_identity()
            except OSError as error:
                return type(error).__name__
        absent_twice = bare_identity(), bare_identity()
        (bare / 'scripts/gate_unconfined.json').write_bytes((ROOT / 'scripts/gate_unconfined.json').read_bytes())
        with_list = bare_identity()
        (bare / 'scripts/gate_unconfined.json').write_text('not a list')
        with_invalid = bare_identity()
        (bare / 'scripts/gate_unconfined.json').unlink()
        (bare / 'scripts/gate_legs.py').rename(bare / 'gate_legs.moved')
        without_runner = bare_identity()
        (bare / 'gate_legs.moved').rename(bare / 'scripts/gate_legs.py')
        for marker in outside.iterdir():
            marker.unlink()
        bare_record = top / 'bare-record'
        bare_run = subprocess.run(['bash', '-c', 'VELDO_AUTHORITY=%s\nVELDO_LEGS_RECORD=%s\nVELDO_LEGS_EXPECTED=\n%s'
                                   'cd %s && veldo_stage unit "python3 scripts/selftest.py" && echo "expected=$VELDO_LEGS_EXPECTED"'
                                   % (bare, bare_record, functions, candidate)],
                                  capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                                  env=dict({k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')},
                                           V208_PROBE_OUTSIDE=str(outside)))
        bare_markers = dict(line.split()[1:3] for line in bare_run.stdout.splitlines()
                            if line.startswith('V208-PROBE '))
        expect('VELDO-0208 unconfined-leg/authority-without-the-list-has-an-identity-and-is-confined: '
               + repr((absent_twice, with_list, with_invalid, without_runner, bare_run.returncode, bare_markers)),
               E_bare.OPTIONAL_AUTHORITY_FILES == ('scripts/gate_unconfined.json',)
               and absent_twice[0] == absent_twice[1] and re.match(r'^[0-9a-f]{64}$', absent_twice[0])
               and len({absent_twice[0], with_list, with_invalid}) == 3
               and without_runner == 'FileNotFoundError'
               and bare_run.returncode == 0 and 'expected=\n' in bare_run.stdout
               and 'UNCONFINED' not in bare_run.stdout and 'selftest leg' not in bare_run.stdout
               and bare_markers == {'01_listed.none': 'refused', '02_asks.none': 'refused',
                   '02_asks.strace.none': 'refused', '03_rows.none': 'refused', '03_rows.strace.none': 'refused'}
               and not bare_record.exists())


if leg_runs():
    _v208_confined_stages()
    _v208_unconfined_leg()


def _v208_installed_tools():
    """A fresh mutation worker reads the installed tools the gate profile grants (optional_read_roots
    of the authority's sandbox configuration), read only, resolved against the account's home rather
    than the worker's private HOME, and never a root that holds or lies beneath a denied path or the
    reuse store. Without them 0045 and 0132 lost the langgraph runtime and 0165 and 0173 the Codex
    and Claude Code binaries, and every case of those suites was an invalid baseline."""
    import importlib.util
    import json
    import os
    from pathlib import Path
    import pwd
    import tempfile
    from unittest.mock import patch

    spec = importlib.util.spec_from_file_location('v208_tools_boundary', ROOT / 'scripts/agent_sandbox.py')
    B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
    with tempfile.TemporaryDirectory(prefix='v208-tools-') as temporary:
        top = Path(temporary)
        for name in ('tool', 'denied/inner', 'store-parent/store'):
            (top / name).mkdir(parents=True)
        (top / 'plain-file').write_text('x')
        config = {'store': str(top / 'store-parent/store'), 'deny_read': [str(top / 'denied')],
                  'optional_read_roots': [str(top / 'tool'), str(top / 'absent'), str(top / 'denied/inner'),
                                          str(top / 'store-parent'), str(top / 'plain-file')]}
        granted = B.installed_tools(config)
        real = json.loads((ROOT / 'scripts/agent_sandbox.json').read_text())
        real['store'] = str(Path(pwd.getpwuid(os.getuid()).pw_dir) / real['store'][2:])
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        with patch.dict(os.environ, {'HOME': str(top)}):
            from_scratch_home = B.installed_tools(real)
        expected_real = [(home / v[2:]).resolve() for v in real['optional_read_roots'] if (home / v[2:]).is_dir()]
    worker_source = (ROOT / 'scripts/reuse_worker.py').read_text()
    expect('VELDO-0208 worker/installed-tools-read-only: ' + repr((granted, from_scratch_home)),
           granted == [(top / 'tool').resolve()]
           and from_scratch_home == expected_real
           and {'~/.nvm/versions/node', '~/.local/share/claude', '~/.local/share/veldo/langgraph'}
               <= set(real['optional_read_roots'])
           and "if 'runtime_paths' not in job:" in worker_source
           and "grants += [(p, boundary.READ) for p in boundary.installed_tools(config)]" in worker_source)


if leg_runs():
    _v208_installed_tools()
