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
        expect('VELDO-0208 engine/scaffold-includes-boundary',
               set(E.AUTHORITY_FILES) <= set(scaffold._FILES))
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

            stdout = '== unit\n   unit: pass\nGATE: GREEN (' + commit + ')'
            sample = {'schema': 'veldo.gate_observation/v1', 'commit': commit, 'stdout': stdout,
                'stdout_digest': landing.digest(stdout.encode()), 'exit': 0, 'terminal': stdout.splitlines()[-1],
                'catalog': {'required': ['unit'], 'results': {'unit': 'pass'}},
                'candidate': {'commit': commit, 'tree': 'b'*40, 'binds_refs': False, 'state': {}},
                'post_run': {'equal': True, 'state': {}},
                'outputs': {'last_verify': stamp, 'gate_event': dict(stamp, type='gate.passed')}}
            expect('VELDO-0208 landing/fleet-accepts-gate-records', not landing.judge(sample))
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
            alterations = [dict(reuse_evidence={}), dict(commit='c' * 40),
                          dict(reused={'unit': 0, 'mutation': 2}), dict(force_fresh=True)]
            for n, change in enumerate(alterations):
                expect('VELDO-0208 landing/tampered-binding-' + str(n),
                       E.landing_problem(dict(stamp, **change)) is not None)
            path.write_bytes(E.canonical(E.sign(legacy, store.secret)))
            expect('VELDO-0208 landing/missing-record-provenance-refused', E.landing_problem(stamp) is not None)
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
            valid = dict(commit=actual, status='green', **reducer.fields(receipt, False, actual))
            for guard in ('scripts/veldo-guard.sh', 'engine/scripts/veldo-guard.sh',
                          'packs/claude/scripts/veldo-guard.sh'):
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




if leg_runs():
    _v208_confined_stages()
