"""VELDO-0207 isolated case keys, the case trace and the stage's receipts. Since VELDO-0271 the
stage runs every case fresh and no worker is confined, so the rows that ran a declared case in a
confined worker are gone."""


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
        # Runtime key changes are controlled.
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

        # A declared directory includes every descendant in its key and snapshot.
        expanded = dict(files); expanded['scripts/new-child'] = (0o644, b'new input')
        expect('VELDO-0207 case/listed-directory-new-child-invalidates',
               session(expanded).keys != keys
               and 'scripts/new-child' in session(expanded).snapshots[case['identity']])
        # The independent tracer refuses a metadata probe of an undeclared input.
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

        # Controlled coordinator proves v2 digests, grouped controls and exact receipts.
        active = [dict(files)]
        class Workers:
            def __init__(self, *args, **kwargs):
                self.invocations = 0; self.driver_spans = {}; self.resources = None
                self.parallel = 1; self.active = {}; self.outcomes = []; self.peak = 0
                self.retargeted = {}
                # VELDO-0267: the coordinator reads the worker's coverage map after every stage
                # (None unless the nightly sweep traces baselines, which this one does not).
                self.coverage = None
            def check(self): pass
            def cleanup(self, on_result=None): return []
            # VELDO-0285: the coordinator retargets an unmeasured case's noop once its
            # baseline is measured in this stage; the worker protocol includes that call.
            def retarget(self, name, seconds): self.retargeted[name] = seconds
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
        def run_stage():
            real_session = C.Session
            def construct(*args, **kwargs):
                return real_session(*args, **kwargs, cache_directory=top/'stage-cache')
            with patch.object(gate, 'inventory', return_value=cases), \
                 patch.object(gate, 'read_inputs', side_effect=lambda root, common: active[0]), \
                 patch.object(gate, 'git', return_value='head'), \
                 patch.object(gate, 'snapshot'), patch.object(gate, 'inputs_unchanged', return_value=True), \
                 patch.object(gate, 'Workers', Workers), patch.object(gate, 'load', return_value=C), \
                 patch.object(gate, 'PARALLEL', 1), \
                 patch.object(gate.SuiteResources, 'from_root', return_value=gate.SuiteResources({'suites':[{'file':'test.py'}, {'file':'other_test.py'}]})), \
                 patch.object(C.M, 'runtime_identity', side_effect=runtime), \
                 patch.object(C, 'Session', side_effect=construct):
                return gate.run_stage(root, root / '.git')
        # Reuse is off (VELDO-0271): the same inputs twice, then one changed input, and every run
        # executes both cases, reuses none, publishes nothing and runs no declared snapshot.
        cold, warm = run_stage(), run_stage()
        active[0]['.veldo/subject.py'] = (0o644, b'value = 2\n')
        mixed = run_stage()
        stored = sorted(p.name for p in (top/'stage-cache').glob('*.json*')) if (top/'stage-cache').is_dir() else []
        expect('VELDO-0207 case/receipts: %r' % [(r.get('status'), r.get('executed'), r.get('reused')) for r in (cold, warm, mixed)],
               cold['status'] == warm['status'] == mixed['status'] == 'passed'
               and all((r['executed'], r['reused'], r['reuse_qualified']) == (2, 0, 0) for r in (cold, warm, mixed))
               and all({c['source'] for c in r['case_receipts']} == {'fresh'}
                       and {c['reason'] for c in r['case_receipts']} == {'reuse_off'} for r in (cold, warm, mixed))
               and stored == [])


_v207_cases()
