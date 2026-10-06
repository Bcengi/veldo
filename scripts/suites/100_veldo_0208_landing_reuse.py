"""VELDO-0208: real inherited confinement and authenticated landing, no mutation stage."""


def _v208_landing_reuse():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    from unittest.mock import patch

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
                  'read_roots': ['/usr', '/lib', '/lib64', '/etc', str(top), str(ROOT)],
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
denied('network-ipv4', lambda: socket.socket(socket.AF_INET))
denied('network-ipv6', lambda: socket.socket(socket.AF_INET6))
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
        keyfd = os.open(storepath / 'authentication.key', os.O_RDWR)
        before = (storepath / 'authentication.key').read_bytes()
        try:
            result = subprocess.run(command + [sys.executable, '-I', '-S', str(probe), str(storepath),
                str(runner), str(ROOT / 'scripts/agent_sandbox.py'), str(keyfd)],
                pass_fds=(keyfd,), capture_output=True, text=True, timeout=20)
        finally:
            os.close(keyfd)
        expect('VELDO-0208 sandbox/launcher-starts: ' + result.stderr[-400:], result.returncode == 0)
        findings = json.loads(result.stdout) if result.returncode == 0 else {}
        for name in ('store-read', 'key-read', 'key-write', 'plant-record', 'replace-store',
                     'runner-write', 'runner-replace', 'authority-write', 'inherited-fd',
                     'symlink-key-read', 'symlink-key-write', 'hardlink-key', 'unix-service', 'user-bus', 'systemd-private',
                     'network-ipv4', 'network-ipv6', 'terminal-injection',
                     'child-read', 'child-plant', 'child-runner', 'own-worktree', 'private-home'):
            expect('VELDO-0208 sandbox/' + name, findings.get(name) is True)
        expect('VELDO-0208 sandbox/store-and-runner-intact',
               (storepath / 'authentication.key').read_bytes() == before
               and runner.read_text() == 'trusted runner' and not (storepath / 'planted.json').exists())
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
        result = subprocess.run([sys.executable, '-I', '-S', '-c', unavailable,
            str(ROOT / 'scripts/agent_sandbox.py'), '--config', str(config), '--worktree', str(worktree),
            '--', sys.executable, '-c', 'open(' + repr(str(marker)) + ', "w").close()'],
            capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/unavailable-refuses-before-exec', result.returncode == 2
               and 'Landlock unavailable' in result.stderr and not marker.exists())
        obsolete = unavailable.replace('return -1', 'return 5')
        result = subprocess.run([sys.executable, '-I', '-S', '-c', obsolete,
            str(ROOT / 'scripts/agent_sandbox.py'), '--config', str(config), '--worktree', str(worktree),
            '--', sys.executable, '-c', 'open(' + repr(str(marker)) + ', "w").close()'],
            capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/old-abi-refuses-before-exec', result.returncode == 2
               and 'needs Landlock ABI 6' in result.stderr and not marker.exists())
        bad_policy = dict(policy, write_roots=[str(top)])
        bad_config = top / 'bad-config.json'; bad_config.write_text(json.dumps(bad_policy))
        bad = command[:]; bad[bad.index(str(config))] = str(bad_config)
        result = subprocess.run(bad + ['/usr/bin/true'], capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/unsafe-config-refuses',
               result.returncode == 2 and 'unsafe writable path' in result.stderr)
        credential = top / 'credential-link'
        credential.symlink_to(storepath / 'authentication.key')
        bad_policy = dict(policy, seed_files={str(credential): '.codex/auth.json'})
        bad_config.write_text(json.dumps(bad_policy))
        result = subprocess.run(bad + ['/usr/bin/true'], capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/credential-alias-cannot-copy-key',
               result.returncode == 2 and 'seed exposes the reuse store' in result.stderr)

        # The orchestrator uses linked worktrees: commit through the actual launcher.
        main = top / 'git-main'
        linked = top / 'git-agent'
        def git_at(path, *args):
            return subprocess.check_output(['/usr/bin/git', '-C', str(path),
                '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args],
                stderr=subprocess.PIPE).decode().strip()
        main.mkdir()
        git_at(main, 'init', '-q', '-b', 'main')
        (main / 'file').write_text('original')
        git_at(main, 'add', 'file'); git_at(main, 'commit', '-qm', 'Initial fixture')
        original_head = git_at(main, 'rev-parse', 'HEAD')
        git_at(main, 'worktree', 'add', '-q', '-b', 'agent', str(linked))
        other = top / 'git-other'
        git_at(main, 'worktree', 'add', '-q', '-b', 'other', str(other))
        policy['git_common_dir'] = str(main / '.git')
        config.write_text(json.dumps(policy))
        linked_command = command[:]
        linked_command[linked_command.index(str(worktree))] = str(linked)
        script = """import errno, pathlib, subprocess, sys
pathlib.Path('file').write_text('agent edit')
subprocess.run(['git', 'add', 'file'], check=True)
subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                'commit', '-qm', 'Confined worktree commit'], check=True)
for name in sys.argv[1:]:
 try: pathlib.Path(name).write_text('forged')
 except OSError as error: assert error.errno in (errno.EACCES, errno.EPERM)
 else: raise AssertionError('wrote protected path: ' + name)
"""
        result = subprocess.run(linked_command + [sys.executable, '-I', '-S', '-c', script,
            str(storepath/'authentication.key'), str(runner), str(ROOT/'scripts/agent_sandbox.py'),
            str(ROOT/'scripts/check_gate_mutations.py'), str(ROOT/'.veldo/control_verification.py'),
            str(main/'.git/config'), str(main/'.git/HEAD'), str(main/'.git/hooks/planted'),
            str(main/'file'), str(main/'.git/worktrees/git-other/index')],
                                capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 sandbox/linked-worktree-commit: ' + result.stderr[-600:],
               result.returncode == 0 and git_at(linked, 'rev-parse', 'HEAD') != original_head
               and git_at(main, 'rev-parse', 'HEAD') == original_head)

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
        refused_agent = subprocess.run(linked_command + ['/usr/bin/true'],
                                      capture_output=True, text=True, timeout=20)
        expect('VELDO-0208 git/redirect-refused-before-git-or-agent',
               refused.returncode == refused_agent.returncode == 2
               and 'expected shared gitdir' in refused.stderr
               and 'expected shared gitdir' in refused_agent.stderr and not escaped.exists())
        (linked / '.git').write_text(original_marker)

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
        result = subprocess.run(command + [sys.executable, '-I', '-S', '-c', writer,
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
        expect('VELDO-0208 landing/canonical-copies-match', all(
            (ROOT / a).read_bytes() == (ROOT / b).read_bytes() for a, b in (
                ('engine/.veldo/reuse_evidence.py', '.veldo/reuse_evidence.py'),
                ('engine/.veldo/control_verification.py', '.veldo/control_verification.py'),
                ('engine/scripts/veldo-guard.sh', 'scripts/veldo-guard.sh'),
                ('engine/scripts/veldo-guard.sh', 'packs/claude/scripts/veldo-guard.sh'))))


_v208_landing_reuse()
