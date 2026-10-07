"""VELDO-0207 isolated case keys and real single-worker sandbox boundaries."""


def _v207_cases():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import time
    from unittest.mock import patch

    def load(name):
        spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    C, gate = load('case_reuse'), load('check_gate_mutations')
    I, R = C.I, C.R
    if leg_runs():
        expect('VELDO-0207 case/spec', V.check_spec(ROOT / 'specs/VELDO-0207-declared-case-reuse.md') == 0)
    with tempfile.TemporaryDirectory(prefix='case-reuse-tests-') as temporary:
        top = Path(temporary)
        root = top / 'repository'; root.mkdir()
        case = {'name': 'one', 'identity': gate.DRIVERS[0] + ':one', 'driver': gate.DRIVERS[0],
                'module': 'subject.py', 'suite': 'test.py', 'old': 'value = 1', 'new': 'value = 0',
                'rows': ['target']}
        other = dict(case, name='two', identity=gate.DRIVERS[0]+':two', module='other.py', suite='other_test.py')
        cases = [case, other]
        files = {p: ((ROOT / p).stat().st_mode & 0o777, (ROOT / p).read_bytes())
                 for p in (*I.MANDATORY, *I.DRIVERS)}
        files['.veldo/subject.py'] = (0o644, b'value = 1\n')
        files['.veldo/other.py'] = (0o644, b'value = 1\n')
        files['shared-helper'] = (0o644, b'helper-v1')
        files['unrelated'] = (0o644, b'not in any closure')
        files['scripts/suites/shared.py'] = (0o644, b'''from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
def expect(name, condition):
    pass
''')
        files['scripts/suites/test.py'] = (0o644, b'''namespace = {}
exec((ROOT / ".veldo" / "subject.py").read_text(), namespace)
expect('fixture target', namespace['value'] == 1)
''')
        files['scripts/suites/other_test.py'] = (0o644, files['scripts/suites/test.py'][1].replace(b'subject.py', b'other.py'))
        declaration = {'schema': 'veldo.case-inputs/v1',
                       'toolchains': {gate.DRIVERS[0]: {'paths': ['/usr', '/lib', '/lib64', '/etc'], 'absent': ['/proc/sys/crypto/fips_enabled'], 'reviewed': True}},
                       'cases': {c['identity']: {'files': ['shared-helper'], 'absent': ['optional'],
                                                'directories': ['scripts'],
                                                'reviewed': True, 'non_file_inputs': 'none',
                                                'rationale': 'Controlled file-only test fixture.'} for c in cases}}
        files[I.DECLARATIONS] = (0o644, R.canonical(declaration))
        runtime_version = [1]
        # Runtime key changes are controlled; real subprocess tests below use real Landlock.
        runtime = lambda paths, env: {'version': runtime_version[0], 'paths': paths, 'environment': env}
        def session(source=None, definitions=None, head='first', force=False):
            with patch.object(C.M, 'runtime_identity', side_effect=runtime):
                return C.Session(root, source or files, definitions or cases, head,
                                 {'worker_environment': gate.fixed_env('<private-worker-home>')},
                                 force_fresh=force, cache_directory=top / 'cache')
        def observation(ok):
            return {'count': 1, 'observations': [['fixture target', ok]],
                    'row_names': ['fixture target'], 'failed_rows': [] if ok else ['fixture target']}
        def killed(c, current):
            return {'schema': gate.SCHEMA, 'case': c, 'fixture_version': gate.FIXTURE_VERSION,
                    'replacement_count': 1, 'old_digest': 'old', 'new_digest': 'new',
                    'baseline': observation(True), 'noop': observation(True), 'mutant': observation(False),
                    'input_digest': current.input_digest(c), 'elapsed': 0.1}
        if leg_runs():
            original = session()
            keys = original.keys
            changed = dict(files); changed['.veldo/subject.py'] = (0o644, b'value = 2\n')
            changed_keys = session(changed).keys
            expect('VELDO-0207 case/keys-declared-edit',
                   changed_keys[case['identity']] != keys[case['identity']]
                   and changed_keys[other['identity']] == keys[other['identity']])
            changed = dict(files); changed['shared-helper'] = (0o644, b'helper-v2')
            expect('VELDO-0207 case/keys-shared-edit', all(session(changed).keys[n] != k for n,k in keys.items()))
            changed = dict(files); changed['unrelated'] = (0o644, b'unrelated commit')
            expect('VELDO-0207 case/keys-unrelated-commit', session(changed, head='second').keys == keys)
            # Registry changes disappear only through the production AST projection.
            changed = dict(files)
            name = I.DRIVERS[0]
            changed[name] = (files[name][0], files[name][1].replace(b"add(204, 'v204-scaffold-absent'", b"add(204, 'unrelated-entry'"))
            expect('VELDO-0207 case/keys-own-registry-entry', session(changed).keys == keys)
            altered = [dict(case, new='value = -1'), other]
            expect('VELDO-0207 case/keys-registry-edit',
                   session(definitions=altered).keys[case['identity']] != keys[case['identity']]
                   and session(definitions=altered).keys[other['identity']] == keys[other['identity']])
            third = dict(case, name='third', driver=gate.DRIVERS[1], identity=gate.DRIVERS[1]+':third')
            d = copy.deepcopy(declaration)
            for entry in d['cases'].values(): entry['directories'] = []
            d['cases'][third['identity']] = copy.deepcopy(d['cases'][case['identity']])
            d['toolchains'][gate.DRIVERS[1]] = copy.deepcopy(d['toolchains'][gate.DRIVERS[0]])
            three_files = dict(files); three_files[I.DECLARATIONS] = (0o644, R.canonical(d))
            before = session(three_files, cases+[third]).keys
            d['toolchains'][gate.DRIVERS[0]]['identity_revision'] = 2
            three_files[I.DECLARATIONS] = (0o644, R.canonical(d))
            after = session(three_files, cases+[third]).keys
            expect('VELDO-0207 case/per-driver-toolchain',
                   all(after[c['identity']] != before[c['identity']] for c in cases)
                   and after[third['identity']] == before[third['identity']])
            runtime_version[0] = 2
            expect('VELDO-0207 case/keys-toolchain', all(session().keys[n] != k for n,k in keys.items()))
            runtime_version[0] = 1
            changed = dict(files); changed['optional'] = (0o644, b'now present')
            try:
                session(changed)
            except ValueError as error:
                absent_refused = 'expected absent' in str(error)
            else:
                absent_refused = False
            expect('VELDO-0207 case/absent-input-addition-refused', absent_refused)
            record = killed(case, original)
            expect('VELDO-0207 case/store-cold-warm', original.lookup(case, gate.validate_result) is None
                   and original.publish(case, record, gate.validate_result)
                   and session(head='unrelated-commit').lookup(case, gate.validate_result) == record)
            changed = dict(files); changed['.veldo/subject.py'] = (0o644, b'value = 3\n')
            newer = session(changed)
            expect('VELDO-0207 case/store-planted-stale',
                   not newer.publish(case, record, gate.validate_result)
                   and newer.store.put(newer.keys[case['identity']], record)
                   and newer.lookup(case, gate.validate_result) is None)
            path = top / 'cache' / (keys[case['identity']] + '.json')
            document = json.loads(path.read_bytes()); document['payload']['result']['elapsed'] = 999
            path.write_bytes(R.canonical(document))
            expect('VELDO-0207 case/store-tamper', session().lookup(case, gate.validate_result) is None)
            fresh = session(force=True)
            expect('VELDO-0207 case/force-fresh', fresh.store is None and not any(fresh.keys.values())
                   and not fresh.publish(case, record, gate.validate_result)
                   and case['identity'] in fresh.snapshots)

        # The traced rows: workers under strace, which the gate domain refuses. A gate whose authority
        # lists them (scripts/gate_unconfined.json) runs them in its unconfined leg; every other row
        # of this suite stays in the confined leg.
        if leg_runs('strace'):
            def run_worker(source, suffix, expected_failure=False, force=False):
                current = session(source, force=force)
                parent = top / suffix; parent.mkdir()
                job = dict(case=case, mode='baseline', **current.prepare(case, parent / 'cases'))
                frozen = Path(job['snapshot_root'])
                expect('VELDO-0207 case/snapshot-only-declared-' + suffix,
                       not (frozen / 'unrelated').exists() and not (frozen / '.git').exists())
                resources = gate.SuiteResources({'suites': [{'file': 'test.py'}]})
                workers = gate.Workers(time.monotonic()+20, resources)
                workers.case_reuse = current
                job['declared_case'] = True
                with patch.object(gate, 'PARALLEL', 1):
                    try:
                        result = workers.run({'one': job}, parent, frozen)
                    except ValueError as error:
                        if not expected_failure or 'undeclared input read' not in str(error): print('case trace error:', suffix, str(error))
                        return (expected_failure and 'undeclared input read' in str(error)
                                and not workers.owned_snapshots
                                and not (parent / 'cases' / '0').exists())
                    except Exception as error:
                        print('case worker error:', str(error)[-800:])
                        return False
                if expected_failure:
                    return False
                honest = result['one']['result']['observation']
                pair = {}
                with patch.object(gate, 'PARALLEL', 1):
                    for mode in ('noop', 'mutant'):
                        pair[mode] = workers.run({mode: dict(job, mode=mode)}, parent, frozen)[mode]['result']
                actual = dict(killed(case, current), baseline=honest, noop=pair['noop']['observation'],
                              mutant=pair['mutant']['observation'],
                              old_digest=pair['mutant']['old_digest'], new_digest=pair['mutant']['new_digest'])
                current.store = R.Store(parent / 'cache', root)
                # The store keeps the observations without their free-text failure details.
                stored = dict(actual, **{mode: {k: v for k, v in actual[mode].items() if k != 'failed_details'}
                                         for mode in ('baseline', 'noop', 'mutant')})
                return ('failed_details' in actual['mutant']
                        and current.publish(case, actual, gate.validate_result)
                        and current.lookup(case, gate.validate_result) == stored
                        and not workers.owned_snapshots
                        and all(not (parent/'cases'/str(n)).exists() for n in range(workers.invocations)))
            expect('VELDO-0207 case/sandbox-valid-worker', run_worker(files, 'valid'))
            for kind, read in [('python', "(ROOT / 'undeclared').read_text()"),
                               ('child', "__import__('subprocess').run(['/usr/bin/cat', str(ROOT / 'undeclared')], capture_output=True)"),
                               ('exists', "(ROOT / 'undeclared').exists()"),
                               ('is-file', "(ROOT / 'undeclared').is_file()"),
                               ('stat', "__import__('os').stat(ROOT / 'undeclared')"),
                               ('lstat', "__import__('os').lstat(ROOT / 'undeclared')"),
                               ('access', "__import__('os').access(ROOT / 'undeclared', 4)"),
                               ('readlink', "__import__('os').readlink(ROOT / 'undeclared')"),
                               ('listdir', "__import__('os').listdir(ROOT / '.veldo')"),
                               ('scandir', "list(__import__('os').scandir(ROOT / '.veldo'))"),
                               ('glob', "list(ROOT.glob('.veldo/*'))"),
                               ('parent-traversal', "(ROOT / 'undeclared' / '..' / 'scripts' / 'case_trace.py').exists()"),
                               ('scratch-alias', "alias = __import__('pathlib').Path(__import__('os').environ['TMPDIR']) / 'alias'; alias.symlink_to(ROOT); (alias / 'undeclared').exists(); alias.unlink()"),
                               ('child-stat', "__import__('subprocess').run([__import__('sys').executable, '-B', '-S', '-c', 'import os; os.stat(' + repr(str(ROOT / 'undeclared')) + ')'], capture_output=True)")]:
                changed = dict(files)
                extra = '\ntry:\n    ' + read + '\nexcept OSError:\n    pass\n'
                changed['scripts/suites/test.py'] = (0o644, files['scripts/suites/test.py'][1] + extra.encode())
                expect('VELDO-0207 case/sandbox-caught-undeclared-' + kind,
                       run_worker(changed, kind, expected_failure=True))
                expect('VELDO-0207 case/forced-caught-undeclared-' + kind,
                       run_worker(changed, 'forced-' + kind, expected_failure=True, force=True))

        if leg_runs():
            # A declared directory includes every descendant in its key and snapshot.
            expanded = dict(files); expanded['scripts/new-child'] = (0o644, b'new input')
            expect('VELDO-0207 case/listed-directory-new-child-invalidates',
                   session(expanded).keys != keys
                   and 'scripts/new-child' in session(expanded).snapshots[case['identity']])
            # The worker confinement (mutation_sandbox.confine) has the gate profile's network rule:
            # the user bus and the systemd private socket stay refused, sockets opened before it
            # do not enter the domain, and TCP reaches the network stack (VELDO-0208, owner decision
            # Telegram 32421).
            services = """import errno, importlib.util, json, os, socket, sys
spec = importlib.util.spec_from_file_location('sandbox', sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
inherited = [socket.socket(socket.AF_UNIX), socket.socket()]
numbers = [s.fileno() for s in inherited]
m.confine(sys.argv[3], sys.argv[2], sys.argv[2])
results = {}
for number in numbers:
 try: os.fstat(number)
 except OSError as error: results['inherited-' + str(number)] = errno.errorcode.get(error.errno)
 else: results['inherited-' + str(number)] = 'open'
for name, address in [('bus', '/run/user/' + str(os.getuid()) + '/bus'),
                      ('systemd', '/run/user/' + str(os.getuid()) + '/systemd/private')]:
 try:
  sock = socket.socket(socket.AF_UNIX)
  sock.connect(address)
 except OSError as error: results[name] = errno.errorcode.get(error.errno)
 else: results[name] = 'connected'
try: socket.create_connection(('127.0.0.1', 9), timeout=5)
except OSError as error: results['tcp'] = errno.errorcode.get(error.errno)
else: results['tcp'] = 'connected'
print(json.dumps(results))
"""
            result = subprocess.run([sys.executable, '-I', '-S', '-c', services,
                                     str(ROOT/'scripts/mutation_sandbox.py'), str(top), str(ROOT)],
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
            try:
                outcome = json.loads(result.stdout)
            except ValueError:
                outcome = {}
            expect('VELDO-0207 case/mutant-bus-systemd-inherited-denied: ' + repr(outcome) + result.stderr[-300:],
                   result.returncode == 0 and outcome.get('bus') in ('EPERM', 'EACCES')
                   and outcome.get('systemd') in ('EPERM', 'EACCES')
                   and [v for k, v in outcome.items() if k.startswith('inherited-')] == ['EBADF'] * 2
                   and outcome.get('tcp') in ('ECONNREFUSED', 'connected'))

            # Without the seccomp filter the domain does not start: no fallback, nothing ran.
            broken_filter = services.replace(
                "m.confine(sys.argv[3], sys.argv[2], sys.argv[2])",
                "real = __import__('ctypes').CDLL\n"
                "class Kernel:\n"
                " def __init__(self, *a, **k): self.libc = real(*a, **k)\n"
                " def __getattr__(self, name): return getattr(self.libc, name)\n"
                " def syscall(self, number, *args):\n"
                "  if getattr(number, 'value', number) == 317: return -1\n"
                "  return self.libc.syscall(number, *args)\n"
                "__import__('ctypes').CDLL = Kernel\n"
                "m.confine(sys.argv[3], sys.argv[2], sys.argv[2])\n"
                "print('confined')")
            result = subprocess.run([sys.executable, '-I', '-S', '-c', broken_filter,
                                     str(ROOT/'scripts/mutation_sandbox.py'), str(top), str(ROOT)],
                                    stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
            expect('VELDO-0207 case/unavailable-ipc-filter-fails-closed: ' + result.stderr[-300:],
                   result.returncode != 0 and 'IPC filter unavailable' in result.stderr
                   and not result.stdout)

        if leg_runs():
            # A read before sandbox installation is still refused by the independent tracer.
            T = load('case_trace')
            for call in ('stat', 'lstat', 'statx', 'newfstatat', 'access', 'faccessat',
                         'faccessat2', 'readlink', 'readlinkat'):
                trace = top / ('metadata-' + call)
                prefix = 'AT_FDCWD<' + str(root) + '>, ' if call in (
                    'statx', 'newfstatat', 'faccessat', 'faccessat2', 'readlinkat') else ''
                trace.write_text('123 ' + call + '(' + prefix + '"' + str(root/'undeclared') +
                                 '", 0) = -1 ENOENT (No such file)\n')
                try: T.check(trace, root, [])
                except ValueError as error: refused = 'undeclared input' in str(error)
                else: refused = False
                expect('VELDO-0207 case/metadata-syscall-' + call, refused)
            trace.write_text('123 getdents64(3<' + str(root) + '>, [], 100) = 0\n')
            try: T.check(trace, root, ['subject.py'])
            except ValueError as error: refused = 'undeclared input' in str(error)
            else: refused = False
            expect('VELDO-0207 case/getdents-parent-not-declared', refused)

        if leg_runs('strace'):
            T = load('case_trace')
            startup_input = top / 'startup-config'; startup_input.write_text('unkeyed input')
            scratch = top / 'startup-home'; scratch.mkdir()
            trace = top / 'startup.trace'
            result = subprocess.run(T.command(trace, [sys.executable, '-B', '-S', '-c',
                                    'open(' + repr(str(startup_input)) + ').read()']),
                                    cwd=root, env=gate.fixed_env(scratch), capture_output=True, timeout=15)
            try:
                T.check(trace, root, [], runtime=('/usr','/lib','/lib64','/etc'), scratch=scratch)
            except ValueError as error:
                startup_refused = 'undeclared runtime read' in str(error)
            else:
                startup_refused = False
            expect('VELDO-0207 case/startup-runtime-boundary', result.returncode == 0 and startup_refused)

        if leg_runs():
            # Controlled coordinator proves v2 digests, grouped controls and exact receipts.
            active = [dict(files)]
            class Workers:
                def __init__(self, *args, **kwargs):
                    self.invocations = 0; self.driver_spans = {}; self.resources = None
                    self.parallel = 1; self.active = {}; self.outcomes = []; self.peak = 0
                def check(self): pass
                def cleanup(self, on_result=None): return []
                def run(self, jobs, directory, frozen, on_result=None):
                    results = {}
                    for name, job in jobs.items():
                        self.invocations += 1
                        self.outcomes.append(dict(name=name, driver=job['case']['driver'], mode=job['mode'],
                                                  elapsed=.1, returncode=0))
                        results[name] = {'elapsed': .1, 'result': {'observation': observation(job['mode'] != 'mutant'),
                            'replacement_count': 1, 'old_digest': 'old', 'new_digest': 'new'}}
                        if on_result is not None:
                            on_result(name, results[name])
                    return results
            # Clean a poisoned fixture record, never repair external production cache data.
            path.unlink()
            def run_stage(miss=False):
                real_session = C.Session
                def construct(*args, **kwargs):
                    return real_session(*args, **kwargs, cache_directory=top/'stage-cache')
                with patch.object(gate, 'inventory', return_value=cases), \
                     patch.object(gate, 'read_inputs', side_effect=lambda root, common: active[0]), \
                     patch.object(gate, 'git', return_value='head'), \
                     patch.object(gate, 'snapshot'), patch.object(gate, 'inputs_unchanged', return_value=True), \
                     patch.object(gate, 'Workers', Workers), patch.object(gate, 'load', return_value=C), \
                     (patch.object(C.Session, 'lookup', return_value=None) if miss else patch.object(gate, 'PARALLEL', 1)), \
                     patch.object(gate.SuiteResources, 'from_root', return_value=gate.SuiteResources({'suites':[{'file':'test.py'}, {'file':'other_test.py'}]})), \
                     patch.object(C.M, 'runtime_identity', side_effect=runtime), \
                     patch.object(C, 'Session', side_effect=construct):
                    return gate.run_stage(root, root / '.git')
            cold, warm = run_stage(), run_stage()
            repeated = run_stage(miss=True)
            expect('VELDO-0207 case/deterministic-concurrent-publication',
                   repeated['status'] == 'passed' and not repeated.get('reuse_integrity_errors')
                   and all('elapsed' not in R.Store(top/'stage-cache', root).get(r['reuse_key'])
                           for r in repeated['results']))
            conflict_store = R.Store(top/'stage-cache', root)
            conflict_key = repeated['results'][0]['reuse_key']
            conflict_path = top/'stage-cache'/(conflict_key + '.json')
            conflict_path.unlink()
            conflict_store.put(conflict_key, {'planted': 'different content'})
            conflict = run_stage(miss=True)
            expect('VELDO-0207 case/content-conflict-turns-stage-red',
                   conflict['status'] == 'failed' and conflict['error'] == 'reuse_integrity_conflict'
                   and 'conflicting cache record' in conflict['detail'])
            repeated_conflict = run_stage(miss=True)
            expect('VELDO-0207 case/poisoned-key-stays-red',
                   repeated_conflict['status'] == 'failed'
                   and repeated_conflict['error'] == 'reuse_integrity_conflict')
            conflict_path.unlink()
            (top/'stage-cache'/(conflict_key + '.json.conflict')).unlink()

            run_stage(miss=True)
            active[0]['.veldo/subject.py'] = (0o644, b'value = 2\n')
            mixed = run_stage()
            expect('VELDO-0207 case/receipts',
                   cold['status'] == warm['status'] == mixed['status'] == 'passed'
                   and (cold['executed'], cold['reused']) == (2,0)
                   and (warm['executed'], warm['reused']) == (0,2)
                   and (mixed['executed'], mixed['reused']) == (1,1))


_v207_cases()
