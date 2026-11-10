"""VELDO-0208: the authenticated landing contract, the Git guard, worker ownership and the gate's
stages run through the candidate runner. Since VELDO-0271 no stage or worker is confined, so the
rows that tested the launcher, its domain and the two legs are gone."""


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
        policy = {'schema': 'veldo.agent-sandbox/v1', 'store': str(storepath)}
        config.write_text(json.dumps(policy))
        import shutil
        # The authority starts the worker from its own copy, never the candidate's.
        worker_source = (ROOT / 'scripts/check_gate_mutations.py').read_text()
        expect('VELDO-0208 candidate/authority-launches-worker',
               "str(ROOT / 'scripts/reuse_worker.py')" in worker_source
               and "str(worker_root / 'scripts/check_gate_mutations.py')" not in worker_source)
        # A shared repository with two linked worktrees, for the Git guard rows below.
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
        expect('VELDO-0208 git/redirect-refused-before-git-or-agent',
               refused.returncode == 2
               and 'expected shared gitdir' in refused.stderr and not escaped.exists())
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
        fake_trace = top / 'forged.trace'
        fake_trace.write_text('1 openat(AT_FDCWD, "/stolen-key", O_RDONLY) = -1 EACCES\n')
        try:
            tracer.check(fake_trace, worker_root, [], scratch=worker_home)
        except ValueError:
            trace_refused = True
        else:
            trace_refused = False
        expect('VELDO-0208 candidate/trace-still-rejects-undeclared-probes', trace_refused)
        # A worker thread torn down by its group's exit never resumes its last call. The tracer
        # prints that thread's end, and only an exit (or a call strace could not name) may be left
        # pending by a thread whose end is printed; anything else is a lost read.
        shared_read = ('1 openat(AT_FDCWD, "' + str(worker_root / 'scripts/suites/shared.py')
                       + '", O_RDONLY|O_CLOEXEC) = 3</shared.py>\n')
        def ended_trace(pending, end):
            fake_trace.write_text(shared_read
                                  + '2 ' + pending + ' <unfinished ...>\n' + '1 exit_group(0) = ?\n'
                                  + ('2 +++ exited with 0 +++\n' if end else '') + '1 +++ exited with 0 +++\n')
            try:
                tracer.check(fake_trace, worker_root, ['scripts/suites/shared.py'], scratch=worker_home)
                return list(tracer.accesses(fake_trace))
            except ValueError as error:
                return str(error)
        expect('VELDO-0208 candidate/trace-ended-thread-pending-exit-accepted', all(
            ended_trace(pending, True) == [(worker_root / 'scripts/suites/shared.py', 'content', True)]
            for pending in ('exit_group(0', 'exit(0', '???(')))
        expect('VELDO-0208 candidate/trace-pending-exit-without-thread-end-refused', all(
            ended_trace(pending, False) == 'incomplete file-read trace'
            for pending in ('exit_group(0', 'exit(0', '???(')))
        expect('VELDO-0208 candidate/trace-ended-thread-pending-read-refused',
               ended_trace('openat(AT_FDCWD, "/stolen-key", O_RDONLY', True) == 'incomplete file-read trace')

        # The coordinator reaps what a worker owns. Its ledger is the coordinator's file, beside the
        # worker's home; a candidate suite appends to it through the inherited descriptor, so each
        # planted line is a claim the coordinator checks. Real authority workers run these suites
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
        # A fresh worker runs isolated but with the system site-packages its suites run with.
        # Under -S, 0119's PyYAML oracle stood down and reader-strip-quoted-hash survived.
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
        scaffold = load('engine/.veldo/init_scaffold.py')
        # VELDO-0216's graph (scripts/gate_graph.json) is optional in the authority and never
        # shipped: with none, verify.sh runs its stages one after another, and an adopter never
        # receives one.
        expect('VELDO-0208 engine/scaffold-includes-boundary',
               set(E.AUTHORITY_FILES) - set(E.OPTIONAL_AUTHORITY_FILES) <= set(scaffold._FILES)
               and 'scripts/gate_candidate.py' in scaffold._FILES
               and E.OPTIONAL_AUTHORITY_FILES == ('scripts/gate_graph.json',)
               and not set(E.OPTIONAL_AUTHORITY_FILES) & set(scaffold._FILES)
               and not set(E.OPTIONAL_AUTHORITY_FILES) & set(scaffold.REQUIRED_SUBSTRATE)
               and not [f for f in E.OPTIONAL_AUTHORITY_FILES if (ROOT / 'engine' / f).exists()])
        catalog = load('.veldo/control_proof.py').catalog((ROOT / 'scripts/verify.sh').read_text())
        expect('VELDO-0208 gate/catalog-includes-authority-stage',
               {'extra', 'mutation'} <= set(catalog['required']))
        with patch.dict(os.environ, {}, clear=True):
            engine_evidence = load('engine/.veldo/reuse_evidence.py')
            default_path, default_document = engine_evidence.configuration()
        # No configuration file ships: the default names only the uid's own store.
        expect('VELDO-0208 engine/default-config-shipped',
               default_path is None and default_document['store'].endswith('/.cache/veldo/gate-reuse-v2')
               and os.path.isabs(default_document['store']))

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

            # This repository's authority carries its gate graph; the engine's, which adopters
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
                ('engine/scripts/agent_sandbox.py', 'scripts/agent_sandbox.py'),
                ('engine/.veldo/reuse_evidence.py', '.veldo/reuse_evidence.py'),
                ('engine/.veldo/control_verification.py', '.veldo/control_verification.py'),
                ('engine/scripts/veldo-guard.sh', 'scripts/veldo-guard.sh'),
                ('engine/scripts/veldo-guard.sh', 'packs/claude/scripts/veldo-guard.sh'))))


def _v208_traced_workers():
    """The authority's baseline, noop and mutant workers under its tracer (strace), each observed.
    The candidate's own driver never runs."""
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
        observed, traced_reads = {}, {}
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
                # The trace is the record of what the worker read: the suite and its subject are in it.
                read = {str(path) for path, kind, success in tracer.accesses(trace, cwd=worker_root) if success}
                traced_reads[mode] = {str(worker_root / n) for n in ('scripts/suites/fixture.py', '.veldo/subject.py')} <= read
        expect('VELDO-0208 candidate/authority-observes-kill', len(observed) == 3
               and traced_reads == {'baseline': True, 'noop': True, 'mutant': True}
               and observed['baseline']['observation']['failed_rows'] == []
               and observed['noop']['observation']['failed_rows'] == []
               and observed['mutant']['observation']['failed_rows'] == ['fixture target'])


_v208_landing_reuse()
_v208_traced_workers()


def _v208_gate_stages():
    """The gate's own stages, run through the gate's candidate runner (scripts/gate_candidate.py, as
    verify.sh runs them), not beside it: the generator stage compares without writing, a gate the
    stage runs for another tree, an installed pack's gate, a mutation worker serving a socket and a
    terminal, and a failed receipt's clean red."""
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile

    runner = [sys.executable, '-I', '-S', str(ROOT / 'scripts/gate_candidate.py')]

    def staged(root, command, env=None, timeout=120):
        """One gate stage command over `root`, exactly as verify.sh's veldo_candidate runs it:
        stdin /dev/null, output captured."""
        return subprocess.run(runner + ['--root', str(root), '--', *command], capture_output=True,
                              text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                              env=dict(os.environ if env is None else env))

    with tempfile.TemporaryDirectory(prefix='v208-stages-') as temporary:
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
        clean = staged(tree, ['bash', str(ROOT / 'scripts/check_generated.sh')], stage_env)
        index.write_text(fresh + 'stale\n')
        stale = staged(tree, ['bash', str(ROOT / 'scripts/check_generated.sh')], stage_env)
        expect('VELDO-0208 confined-stage/generated-compares-without-writing: ' + (clean.stdout + clean.stderr)[-300:],
               clean.returncode == 0 and 'generated: pass (specs/index.md)' in clean.stdout
               and stale.returncode == 1 and 'specs/index.md was stale' in stale.stdout
               and 'Nothing was rewritten' in stale.stdout and 'errored or refused' not in stale.stdout
               and 'Permission denied' not in stale.stdout + stale.stderr
               and index.read_text() == fresh + 'stale\n')

        # ---- unit: a gate the stage runs for another tree (the init scaffold's) ------------------
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
        nested_gate = staged(scaffold, [sys.executable, str(scaffold / 'run.py')], timeout=300)
        expect('VELDO-0208 confined-stage/nested-scaffold-gate-green: ' + nested_gate.stdout[-300:],
               nested_gate.returncode == 0 and 'GATE: GREEN' in nested_gate.stdout
               and 'refused to start' not in nested_gate.stdout)

        # ---- packaging: an installed pack's gate names its own repository ------------------------
        # verify.sh exports the authority's common directory; the stage is run with it exported.
        common = subprocess.run([sys.executable, '-I', '-S', str(ROOT / '.veldo/candidate_git.py'),
                                 '--authority-common'], capture_output=True, text=True).stdout.strip()
        packaged = staged(ROOT, [sys.executable, 'scripts/check_install_and_run.py', '--pack', 'claude'],
                            dict(os.environ, VELDO_EXPECTED_GIT_COMMON=common), timeout=300)
        expect('VELDO-0208 confined-stage/installed-pack-gate-green: ' + (packaged.stdout + packaged.stderr)[-300:],
               packaged.returncode == 0 and 'adopter gate GREEN' in packaged.stdout
               and 'candidate Git boundary refused' not in packaged.stdout)

        # ---- mutation: a worker serves sockets and terminals -------------------------------------
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
        expect('VELDO-0208 confined-stage/worker-serves-socket-and-terminal: ' + repr((observed, stderr)),
               observed == {'baseline': [], 'mutant': ['fixture target']})

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




def _v208_one_leg():
    """What the leg rows checked that does not depend on a leg (VELDO-0271): the authority's Git
    common directory never reaches a candidate command, the dispatcher never imports a candidate
    file that shadows a standard-library or dispatcher module, and an authority without the optional
    graph still has an identity. Driven through the real candidate runner and the real dispatcher
    over a fixture candidate."""
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

    shared_source = (ROOT / 'scripts/suites/shared.py').read_text()
    real_helpers = ''.join(ast.get_source_segment(shared_source, node) + '\n\n'
                           for node in ast.parse(shared_source).body
                           if isinstance(node, ast.FunctionDef) and node.name == 'suite_file')
    fixture_shared = ('import os\nimport sys\nfrom pathlib import Path\n'
        'ROOT = Path(__file__).resolve().parents[2]\nsys.path.insert(0, str(ROOT / "scripts"))\n'
        'PASS = FAIL = 0\nSCOPE = None\n' + real_helpers +
        'def expect(name, condition):\n    global PASS, FAIL\n    PASS += bool(condition); FAIL += not condition\n'
        'def report():\n    print(SCOPE.aggregate_line(PASS, FAIL)); return SCOPE.exit_code(FAIL)\n'
        'def probe(label):\n'
        '    print("V208-COMMON %s %s" % (label, os.environ.get("VELDO_EXPECTED_GIT_COMMON", "absent")),'
        ' flush=True)\n    expect(label, True)\n')
    bodies = {'01_first': 'probe("01_first")\n', '02_second': 'probe("02_second")\n'}
    with tempfile.TemporaryDirectory(prefix='v208-one-leg-') as temporary:
        top = Path(temporary)
        candidate = top / 'candidate'
        (candidate / 'scripts/suites').mkdir(parents=True)
        for name in ('selftest.py', 'run_scope.py'):
            shutil.copyfile(ROOT / 'scripts' / name, candidate / 'scripts' / name)
        (candidate / 'scripts/suites/shared.py').write_text(fixture_shared)
        for name, body in bodies.items():
            (candidate / 'scripts/suites' / (name + '.py')).write_text(body)
        (candidate / 'scripts/suites/manifest.json').write_text(json.dumps({
            'schema': 'veldo.suites/v1', 'entry': 'selftest.py', 'shared': 'shared.py',
            'suites': [{'name': n, 'file': n + '.py'} for n in bodies]}))

        def stage(root, extra=None):
            """The unit stage's command over `root`, as verify.sh's veldo_candidate runs it."""
            return subprocess.run([sys.executable, '-I', '-S', str(ROOT / 'scripts/gate_candidate.py'),
                                   '--root', str(root), '--', 'bash', '-c', 'python3 scripts/selftest.py'],
                                  capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL,
                                  env=dict(os.environ, **(extra or {})))

        # The authority's own Git common directory, which verify.sh exports for its own scripts,
        # reaches no candidate command. Handed on, a suite's gate for a fixture repository checked
        # that repository against the authority's directory and refused it: 0050 and 0148 failed
        # inside the real gate and passed in every run without it.
        held = stage(candidate, {'VELDO_EXPECTED_GIT_COMMON': str(top / 'authority-common')})
        seen = dict(line.split()[1:3] for line in held.stdout.splitlines() if line.startswith('V208-COMMON '))
        expect('VELDO-0208 unconfined-leg/authority-git-common-reaches-neither-leg: ' + repr(seen)
               + ' ' + (held.stdout + held.stderr)[-300:],
               held.returncode == 0 and 'selftest: 2 passed, 0 failed' in held.stdout
               and seen == {'01_first': 'absent', '02_second': 'absent'})

        # No file in scripts/ or scripts/suites/ shadows a standard-library module the dispatcher
        # imports, nor one of the modules it imports by name. A candidate scripts/json.py and
        # suites/tempfile.py, and a scripts/shared.py and suites/run_scope.py standing in for
        # suites/shared.py and scripts/run_scope.py, each announcing its import, run through the real
        # runner and dispatcher, with shared.py's own imports, and none is imported; the control
        # shows each plant is live for an ordinary script in the same directory. The plants in
        # suites/ are enumerated, so the dispatcher reaches shared.py rather than refusing them as
        # SUITE_NOT_ENUMERATED.
        shadow = top / 'shadow'
        shutil.copytree(candidate, shadow)
        real_imports = ''.join(ast.get_source_segment(shared_source, node) + '\n'
                               for node in ast.parse(shared_source).body
                               if isinstance(node, (ast.Import, ast.ImportFrom)))
        (shadow / 'scripts/suites/shared.py').write_text(real_imports + fixture_shared)
        plants = ('scripts/json.py', 'scripts/suites/tempfile.py', 'scripts/shared.py', 'scripts/suites/run_scope.py')
        for planted in plants:
            module = Path(planted).stem
            (shadow / planted).write_text('if __name__ == %r:\n    print("V208-SHADOWED %s", flush=True)\n'
                                          % (module, module))
            (shadow / planted).with_name('control_%s.py' % module).write_text('import %s\n' % module)
        shadow_manifest = json.loads((shadow / 'scripts/suites/manifest.json').read_text())
        for module in ('tempfile', 'run_scope'):
            shadow_manifest['suites'].append({'name': module, 'file': module + '.py'})
            shadow_manifest['suites'].append({'name': 'control_' + module, 'file': 'control_%s.py' % module})
        (shadow / 'scripts/suites/manifest.json').write_text(json.dumps(shadow_manifest))
        ran = stage(shadow)
        controls = [subprocess.run([sys.executable, str(shadow / relative)], cwd=str(shadow), capture_output=True,
                                   text=True, timeout=60, stdin=subprocess.DEVNULL).stdout
                    for relative in (str(Path(planted).with_name('control_' + Path(planted).name))
                                     for planted in plants)]
        shadow_out = ran.stdout + ran.stderr
        expect('VELDO-0208 unconfined-leg/dispatcher-never-imports-a-candidate-stdlib-shadow: '
               + repr((ran.returncode, shadow_out[-400:], controls)),
               {'import json', 'import subprocess', 'import tempfile'} <= set(real_imports.splitlines())
               and ran.returncode == 0 and 'V208-SHADOWED' not in shadow_out
               and 'selftest: 2 passed, 0 failed' in shadow_out
               and controls == ['V208-SHADOWED %s\n' % Path(planted).stem for planted in plants])

        # The graph is optional in the authority (with none, verify.sh runs its stages one after
        # another, and an adopter never receives one), so an authority without it still has an
        # identity: the graph is recorded as absent, a stable value no digest equals, while any
        # other missing authority file is still an error.
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
        (bare / 'scripts/gate_graph.json').write_bytes((ROOT / 'scripts/gate_graph.json').read_bytes())
        with_graph = bare_identity()
        (bare / 'scripts/gate_graph.json').write_text('not a graph')
        with_invalid_graph = bare_identity()
        (bare / 'scripts/gate_graph.json').unlink()
        absent_again = bare_identity()
        (bare / 'scripts/gate_candidate.py').rename(bare / 'gate_candidate.moved')
        without_runner = bare_identity()
        (bare / 'gate_candidate.moved').rename(bare / 'scripts/gate_candidate.py')
        expect('VELDO-0208 unconfined-leg/authority-without-the-list-has-an-identity-and-is-confined: '
               + repr((absent_twice, with_graph, with_invalid_graph, absent_again, without_runner)),
               E_bare.OPTIONAL_AUTHORITY_FILES == ('scripts/gate_graph.json',)
               and absent_twice[0] == absent_twice[1] == absent_again and re.match(r'^[0-9a-f]{64}$', absent_twice[0])
               and len({absent_twice[0], with_graph, with_invalid_graph}) == 3
               and without_runner == 'FileNotFoundError')


_v208_gate_stages()
_v208_one_leg()


def _v208_first_use_nested_copy():
    """The parked integration check's nested copy (scripts/parked/estimation/check_first_use.py) is a
    tree a gate can run over, and a failing row there is named: a linked worktree's copied `.git`
    was once refused as a redirect, and the stage passed on equal counts without a name on the page."""
    import contextlib
    import importlib.util
    import io
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile

    def load(name, path):
        saved = list(sys.path)
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        finally:
            sys.path[:] = saved  # check_first_use.py drops scripts/ from the path it loads in

    def git(where, *args):
        return subprocess.run(['git', '-C', str(where), *args], check=True, capture_output=True, text=True,
                              env=dict(os.environ, GIT_AUTHOR_NAME='fixture', GIT_AUTHOR_EMAIL='fixture@example.test',
                                       GIT_COMMITTER_NAME='fixture', GIT_COMMITTER_EMAIL='fixture@example.test',
                                       GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')).stdout.strip()

    F = load('v208_first_use', ROOT / 'scripts/parked/estimation/check_first_use.py')  # parked, VELDO-0278
    G = load('v208_first_use_git', ROOT / '.veldo/candidate_git.py')
    with tempfile.TemporaryDirectory(prefix='v208-first-use-') as temporary:
        top = Path(temporary)

        # A run with failures names every failing row, the baseline run included.
        named = top / 'named'
        (named / 'scripts').mkdir(parents=True)
        (named / 'scripts/selftest.py').write_text(
            'print("  SELFTEST FAIL: V208 row-one: detail")\nprint("  SELFTEST FAIL: V208 row-two")\n'
            'print("selftest: 3 passed, 2 failed")\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            counted = F._run_suite(named, 'baseline')
        printed = out.getvalue()
        expect('VELDO-0208 first-use/failing-rows-named: ' + printed[-300:],
               counted == (3, 2, ['V208 row-one: detail', 'V208 row-two'])
               and '   baseline failing: V208 row-one: detail\n' in printed
               and '   baseline failing: V208 row-two\n' in printed)

        # A copy of a linked worktree is a repository of its own: the Git guard accepts it with its
        # own .git as the common directory, and it has the worktree's branch, commit and staged and
        # unstaged state. The copy as copytree leaves it is refused, which is what the rows saw.
        main, linked = top / 'main', top / 'linked'
        (main / 'scripts').mkdir(parents=True)
        (main / 'scripts/selftest.py').write_text('print("selftest: 1 passed, 0 failed")\n')
        (main / 'kept').write_text('one\n')
        git(main, 'init', '-q', '-b', 'main')
        git(main, 'add', '-A')
        git(main, 'commit', '-q', '-m', 'one')
        git(main, 'worktree', 'add', '-q', '-b', 'topic', str(linked))
        (linked / 'kept').write_text('two\n')
        (linked / 'staged').write_text('staged\n')
        git(linked, 'add', 'staged')
        state = [git(linked, *a) for a in (('rev-parse', '--abbrev-ref', 'HEAD'), ('rev-parse', 'HEAD'),
                                           ('status', '--porcelain'), ('rev-parse', 'main'))]
        with contextlib.redirect_stdout(io.StringIO()):
            copied = F._copy(linked, top / 'copied', 'pristine')
        try:
            G.validate(copied, copied / '.git')
            accepted = True
        except ValueError as error:
            accepted = repr(error)
        naive = top / 'naive'
        shutil.copytree(linked, naive, symlinks=True)
        try:
            G.validate(naive, main / '.git')
            naive_refused = False
        except ValueError as error:
            naive_refused = 'redirects outside' in str(error)
        copied_state = [git(copied, *a) for a in (('rev-parse', '--abbrev-ref', 'HEAD'), ('rev-parse', 'HEAD'),
                                                  ('status', '--porcelain'), ('rev-parse', 'main'))]
        expect('VELDO-0208 first-use/linked-worktree-copy-is-own-repository: '
               + repr((accepted, naive_refused, state, copied_state)),
               accepted is True and naive_refused and (copied / '.git').is_dir()
               and not (copied / '.git/worktrees').exists() and copied_state == state
               and state[0] == 'topic' and 'A  staged' in state[2] and 'M kept' in state[2])


_v208_first_use_nested_copy()


def _v208_case_input_proposal():
    """Proposing case inputs for a suite whose cases serve on 127.0.0.1 TCP (58_veldo_0028_effects)
    works: propose_case_inputs.py traces its baseline, noop and mutant workers, and each trace
    shows the worker reading the suite."""
    import importlib.util
    from pathlib import Path

    def load(relative):
        spec = importlib.util.spec_from_file_location('v208_proposal_' + Path(relative).stem, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    proposer = load('scripts/propose_case_inputs.py')
    gate = proposer.load_gate()
    T = proposer.T
    suite = ROOT / 'scripts/suites/58_veldo_0028_effects.py'
    name = 'check_teeth_mutations.py:effects-worker-scope'
    case = {c['identity']: c for c in gate.inventory(ROOT, gate.common_directory(ROOT))}[name]
    reads = []
    traced = T.accesses

    def accesses(trace, **kwargs):
        # Whether the traced worker read the suite: each successful open of it in the trace.
        hits = []
        for line in T.syscall_lines(trace):
            match = T.CALL.search(line)
            if not match:
                continue
            call, arguments, result = match.groups()
            if call.startswith('open') and '"' + str(suite) + '"' in arguments and not result.startswith('-1'):
                hits.append(True)
        reads.append(hits)
        return traced(trace, **kwargs)

    proposer.T.accesses = accesses
    try:
        result, _ = proposer.trace_case(gate, case)
    except (OSError, ValueError) as error:
        # A deadline or an incomplete trace is this row's red, with its reason, never a crash of
        # the suite (landing-b gate e6aed167).
        expect('VELDO-0208 profiles/case-input-proposal-tcp-suite-confined: %s: %s'
               % (type(error).__name__, error), False)
        return
    finally:
        proposer.T.accesses = traced
    modes = {m['mode']: m for m in result['modes']}
    failed = {mode: m.get('observation', {}).get('observation', {}).get('failed_rows') for mode, m in modes.items()}
    expect('VELDO-0208 profiles/case-input-proposal-tcp-suite-confined: ' + repr((failed, reads))
           + ' ' + ' '.join(m.get('error', '')[-300:] for m in modes.values()),
           sorted(modes) == ['baseline', 'mutant', 'noop'] and all(m['exit'] == 0 for m in modes.values())
           and failed['baseline'] == [] and failed['noop'] == [] and failed['mutant']
           and len(reads) == 3 and all(hits and all(hits) for hits in reads)
           and 'scripts/suites/58_veldo_0028_effects.py' in result['files'])


_v208_case_input_proposal()
