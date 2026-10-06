"""VELDO-0205: controlled coordinator workers only; never launch a mutation process."""


def _v205_reuse():
    import copy
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import sys
    import tempfile
    import types
    from unittest.mock import patch

    def load(name):
        path = ROOT / 'scripts' / (name + '.py')
        spec = importlib.util.spec_from_file_location('test_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    expect('VELDO-0205 reuse/spec-contracts: both ready specifications validate',
           V.check_spec(ROOT / 'specs/VELDO-0205-mutation-result-reuse.md') == 0
           and V.check_spec(ROOT / 'specs/VELDO-0206-suite-result-reuse.md') == 0)
    gate = load('check_gate_mutations')
    reuse = load('mutation_reuse')
    R = reuse.R
    driver_definitions = []
    for name in gate.DRIVERS:
        owner = load(name.removesuffix('.py'))
        definition = {'name': 'controlled', 'old': 'a', 'new': 'b'}
        driver_definitions.append(owner.reuse_definition(definition, [definition]) == definition)
        try:
            owner.reuse_definition(dict(definition, new='weakened'), [definition])
        except ValueError:
            driver_definitions.append(True)
        else:
            driver_definitions.append(False)
    expect('VELDO-0205 reuse/driver-identity: both registry owners reject altered case definitions',
           all(driver_definitions))
    cases = [dict(name=str(i), identity=driver + ':' + str(i), driver=driver,
                  suite='controlled.py', module='subject.py', rows=['target'], old='good', new='bad')
             for i, driver in enumerate(gate.DRIVERS)]

    def observation(ok):
        return {'observations': [['fixture target', ok]], 'count': 1,
                'row_names': ['fixture target'], 'failed_rows': [] if ok else ['fixture target']}

    def killed(case):
        return {'schema': gate.SCHEMA, 'case': case, 'fixture_version': gate.FIXTURE_VERSION,
                'replacement_count': 1, 'old_digest': 'a', 'new_digest': 'b',
                'baseline': observation(True), 'noop': observation(True),
                'mutant': observation(False), 'elapsed': 0.1}

    with tempfile.TemporaryDirectory(prefix='build-gate-reuse-tests-') as temporary:
        base = Path(temporary)
        root = base / 'repository'
        root.mkdir()
        runtime = base / 'runtime'
        runtime.mkdir()
        tool = runtime / 'tool'
        tool.write_text('tool v1')
        # Exact interpreter bytes plus a deliberately tiny external fixture closure.
        # This is test data, not a claim about any production suite's runtime closure.
        runtime_paths = [str(Path(sys.executable).resolve()), str(runtime)]
        files = {'scripts/check_gate_mutations.py': (0o644, b'gate'),
                 'scripts/check_teeth_mutations.py': (0o644, b'teeth'),
                 'scripts/check_review_mutations.py': (0o644, b'review'),
                 'scripts/verify.sh': (0o755, b'gate wiring'),
                 '.veldo/subject.py': (0o644, b'good'),
                 'scripts/suites/controlled.py': (0o644, b'test'),
                 'scripts/fixtures/data': (0o644, b'fixture'),
                 'engine/runtime.py': (0o644, b'engine')}

        def qualified(source, definitions=cases):
            source = dict(source)
            source[reuse.PROFILE] = (0o644, R.canonical({
                'schema': 'veldo.mutation-closures/v1', 'profiles': {
                    c['identity']: {'tree_digest': reuse.qualification_digest(source),
                                    'case_digest': R.digest(c), 'non_file_inputs': 'none',
                                    'rationale': 'Controlled unit fixture; no real worker executes.',
                                    'runtime_paths': runtime_paths} for c in definitions}}))
            return source

        reuse.required_runtime = lambda environment: [Path(sys.executable).resolve(), runtime]
        files = qualified(files)
        cache = base / 'cache'

        # Exercise the existing fixture constructor without running its mutation stage.
        import ast
        import subprocess
        fixture_source = (ROOT / 'scripts/suites/53_veldo_0123_mutations.py').read_text()
        fixture_function = next(node for node in ast.parse(fixture_source).body
                                if isinstance(node, ast.FunctionDef) and node.name == 'fixture')
        namespace = {'_m123_os': os, '_m123_sp': subprocess, 'FIXTURE_DRIVER': '# controlled'}
        exec(compile(ast.Module(body=[fixture_function], type_ignores=[]), 'fixture_constructor', 'exec'), namespace)
        fixture_root = base / 'compatibility-fixture'
        namespace['fixture'](fixture_root, ROOT / 'scripts/check_gate_mutations.py')
        expect('VELDO-0205 reuse/legacy-fixture-dependencies: old fresh-stage fixtures carry new helpers',
               all((fixture_root / 'scripts' / name).is_file()
                   for name in ('gate_reuse.py', 'mutation_reuse.py', 'mutation_sandbox.py',
                                'case_inputs.py', 'case_reuse.py', 'case_trace.py', 'reuse_stamp.py')))

        def session(source=files, definitions=cases, **kwargs):
            return reuse.Session(root, source, definitions, kwargs.pop('head', 'head'),
                                 kwargs.pop('configuration', {'fixture_version': 1}),
                                 environment=kwargs.pop('environment', {'TOOL_SETTING': '1'}),
                                 cache_directory=kwargs.pop('cache_directory', cache), **kwargs)

        def key_checks():
            first = session()
            original = first.keys[cases[0]['identity']]
            ok = original is not None and original == session().keys[cases[0]['identity']]
            changes = []
            for name in files:
                if name == reuse.PROFILE:
                    continue
                for new in ((files[name][0], files[name][1] + b'changed'),
                            (0o700, files[name][1])):
                    changed = dict(files, **{name: new})
                    # A changed source first loses qualification. Requalifying still changes its key.
                    ok &= session(changed).keys[cases[0]['identity']] is None
                    changes.append(session(qualified(changed)).keys[cases[0]['identity']])
            added = dict(files, extra=(0o644, b'new'))
            deleted = dict(files)
            del deleted['engine/runtime.py']
            changes.extend([session(qualified(added)).keys[cases[0]['identity']],
                            session(qualified(deleted)).keys[cases[0]['identity']],
                            session(head='different').keys[cases[0]['identity']],
                            session(configuration={'fixture_version': 2}).keys[cases[0]['identity']],
                            session(environment={'TOOL_SETTING': '2'}).keys[cases[0]['identity']]])
            altered_case = copy.deepcopy(cases)
            altered_case[0]['new'] = 'different mutant'
            changes.append(session(qualified(files, altered_case), altered_case).keys[cases[0]['identity']])
            with patch.object(sys, 'version', 'different interpreter version'):
                changes.append(session().keys[cases[0]['identity']])
            tool.write_text('tool v2')
            changes.append(session().keys[cases[0]['identity']])
            ok &= not first.unchanged()
            tool.write_text('tool v1')
            (runtime / 'added').write_text('new dependency')
            changes.append(session().keys[cases[0]['identity']])
            (runtime / 'added').unlink()
            (runtime / 'link').symlink_to(tool)
            changes.append(session().keys[cases[0]['identity']])
            (runtime / 'link').unlink()
            missing = dict(files)
            del missing[reuse.PROFILE]
            ok &= all(value is None for value in session(missing).keys.values())
            return bool(ok and all(value is not None and value != original for value in changes))

        malformed = dict(files)
        data = json.loads(files[reuse.PROFILE][1])
        data['profiles'][cases[0]['identity']]['rationale'] = 12
        malformed[reuse.PROFILE] = (0o644, R.canonical(data))
        expect('VELDO-0205 reuse/malformed-closure-misses: incomplete qualification cannot authorize reuse',
               session(malformed).keys[cases[0]['identity']] is None)
        expect('VELDO-0205 reuse/exact-closure: every input dimension misses; unchanged closure hits', key_checks())
        # A planted defect is executed, not merely described. Pinning and keying share this primitive.
        real_identity = reuse.input_identity
        def without_contents(source):
            return {name: [mode, 'content omitted'] for name, (mode, _) in source.items()}
        with patch.object(reuse, 'input_identity', without_contents):
            expect('VELDO-0205 reuse/exact-closure-negative: omitting contents is detected', not key_checks())
        assert reuse.input_identity is real_identity

        def authenticated_checks(directory):
            current = session(cache_directory=directory)
            case = cases[0]
            record = dict(killed(case), input_digest=R.digest(current.base))
            key = current.keys[case['identity']]
            ok = current.lookup(case, gate.validate_result) is None
            ok &= current.publish(case, record, gate.validate_result)
            ok &= session(cache_directory=directory).lookup(case, gate.validate_result) == record
            path = directory / (key + '.json')
            raw = path.read_bytes()
            document = json.loads(raw)
            document['payload']['result']['elapsed'] = 999
            # Even a perfectly well-formed record with a recomputed plain digest is unauthenticated.
            path.write_bytes(R.canonical(document))
            ok &= current.lookup(case, gate.validate_result) is None
            document['mac'] = hashlib.sha256(R.canonical(document['payload'])).hexdigest()
            path.write_bytes(R.canonical(document))
            ok &= current.lookup(case, gate.validate_result) is None
            path.write_bytes(b'{')
            ok &= current.lookup(case, gate.validate_result) is None
            path.write_bytes(raw)
            invalid = []
            for field, value in [('baseline', observation(False)), ('mutant', observation(True)),
                                 ('noop', observation(False)), ('replacement_count', 0),
                                 ('fixture_version', 999), ('case', cases[1])]:
                broken = dict(record, **{field: value})
                invalid.append(not current.publish(case, broken, gate.validate_result))
                # A signed but semantically invalid record is still not reusable.
                path.unlink()
                current.store.put(key, broken)
                invalid.append(current.lookup(case, gate.validate_result) is None)
            path.unlink()
            current.store.put(key, {'status': 'timeout'})
            invalid.append(current.lookup(case, gate.validate_result) is None)
            other_key = R.digest('different key')
            other = directory / (other_key + '.json')
            other.write_bytes(raw)
            other.chmod(0o600)
            ok &= current.store.get(other_key) is None
            return bool(ok and all(invalid))

        expect('VELDO-0205 reuse/authenticated-kills: corrupt, tampered, invalid and non-killed records miss',
               authenticated_checks(base / 'auth-cache'))
        with patch.object(R.hmac, 'compare_digest', lambda *args: True):
            expect('VELDO-0205 reuse/authenticated-kills-negative: bypassing authentication is detected',
                   not authenticated_checks(base / 'bad-auth-cache'))
        inside = R.Store(root / 'forbidden-cache', root)
        expect('VELDO-0205 reuse/external-atomic-store: repository cache refused and private atomic records used',
               inside.secret is None and not (root / 'forbidden-cache').exists()
               and not list(base.rglob('.pending-*')))
        with patch.object(R.os, 'link', side_effect=OSError('disk unavailable')):
            unavailable = R.Store(base / 'unavailable-cache', root)
            expect('VELDO-0205 reuse/store-errors-miss: unavailable store never supplies a result',
                   unavailable.secret is None and unavailable.get('a' * 64) is None)

        current = session(cache_directory=base / 'deadline-cache')
        record = dict(killed(cases[0]), input_digest=current.base_digest)
        current.publish(cases[0], record, gate.validate_result)
        def expired(*args):
            raise gate.Refused('mutation_budget_exceeded', 'controlled deadline')
        deadlines = []
        for operation in (lambda: current.lookup(cases[0], expired),
                          lambda: current.publish(cases[0], record, expired)):
            try:
                operation()
            except gate.Refused as error:
                deadlines.append(error.code)
        expect('VELDO-0205 reuse/deadline-stays-red: cache fallback cannot swallow the stage alarm',
               deadlines == ['mutation_budget_exceeded'] * 2)

        stage_cache = base / 'stage-cache'
        calls = []
        real_session = reuse.Session
        active_files = [files]
        survivor = [False]
        race = [False]
        failure = [False]
        captured = []
        def stage_session(*args, **kwargs):
            value = real_session(*args, **kwargs, environment={}, cache_directory=stage_cache)
            captured.append(value)
            return value

        class ControlledWorkers:
            def __init__(self, deadline):
                self.deadline = deadline
                self.resources = None
                self.driver_spans = {}
                self.invocations = 0
                self.attempted = set()
            def check(self):
                pass
            def cleanup(self):
                pass
            def run(self, jobs, directory, frozen):
                results = {}
                for name, job in jobs.items():
                    self.attempted.add(name)
                    self.invocations += 1
                    calls.append((name, job['mode']))
                    if failure[0] and job['mode'] == 'mutant':
                        raise gate.Refused('driver_error', 'controlled worker crash')
                    results[name] = {'result': dict(observation=observation(
                        job['mode'] != 'mutant' or survivor[0]), replacement_count=1,
                        old_digest='a', new_digest='b'), 'elapsed': 0.1}
                return results

        with patch.object(gate, 'inventory', return_value=[{'driver': 'synthetic'}]), \
             patch.object(gate, 'read_inputs', side_effect=gate.Refused('driver_error', 'controlled setup stop')):
            setup_failed = gate.run_stage(root)
        expect('VELDO-0205 reuse/setup-error-receipt: incomplete setup returns a failed receipt',
               setup_failed['status'] == 'failed' and setup_failed['executed'] == setup_failed['reused'] == 0)

        class Resources:
            def summary(self):
                return {}

        def run(force=False):
            with patch.object(gate, 'Workers', ControlledWorkers), \
                 patch.object(gate, 'inventory', return_value=cases), \
                 patch.object(gate, 'read_inputs', side_effect=lambda root: active_files[0]), \
                 patch.object(gate, 'git', return_value='head'), \
                 patch.object(gate, 'snapshot'), \
                 patch.object(gate, 'inputs_unchanged', side_effect=lambda *args: not race[0]), \
                 patch.object(gate, 'load', return_value=reuse), \
                 patch.object(gate.SuiteResources, 'from_root', return_value=Resources()), \
                 patch.object(reuse, 'Session', side_effect=stage_session):
                return gate.run_stage(root, force_fresh=force)

        cold = run()
        warm = run()
        expect('VELDO-0205 reuse/receipt-counts: cold executes both drivers; warm validates both cached kills',
               cold['status'] == warm['status'] == 'passed'
               and (cold['executed'], cold['reused'], cold['rejected']) == (2, 0, 2)
               and (warm['executed'], warm['reused'], warm['rejected']) == (0, 2, 2)
               and warm['worker_invocations'] == 0
               and all(d['executed'] == 0 and d['reused'] == 1 for d in warm['drivers'].values())
               and all(r['key'] and r['source'] == 'reused' for r in warm['case_receipts']))
        # Corrupt one entry. Exactly that case executes again, its peer remains a hit.
        broken_key = captured[-1].keys[cases[0]['identity']]
        (stage_cache / (broken_key + '.json')).write_bytes(b'corrupt')
        mixed = run()
        expect('VELDO-0205 reuse/mixed-counts: corruption causes one fresh case and retains the other hit',
               mixed['status'] == 'passed' and (mixed['executed'], mixed['reused']) == (1, 1)
               and mixed['drivers'][gate.DRIVERS[0]]['executed'] == 1
               and mixed['drivers'][gate.DRIVERS[1]]['reused'] == 1)
        survivor[0] = True
        red = run()
        expect('VELDO-0205 reuse/stale-cannot-pass: a corrupt record cannot hide a surviving fresh mutant',
               red['status'] == 'failed' and red['error'] == 'mutation_survived'
               and (red['executed'], red['reused'], red['rejected']) == (1, 1, 1))
        survivor[0] = False
        fresh = run(True)
        direct = session(force_fresh=True)
        with patch.dict(os.environ, {'VELDO_GATE_FORCE_FRESH': '1'}):
            env_forced = real_session(root, files, cases, 'head', {}, cache_directory=stage_cache)
        expect('VELDO-0205 reuse/fresh-policy: force fresh bypasses cache reads and writes',
               fresh['status'] == 'passed' and (fresh['executed'], fresh['reused']) == (2, 0)
               and fresh['force_fresh'] and direct.store is None and env_forced.store is None
               and all(key is None for key in direct.keys.values()))
        race[0] = True
        raced = run()
        race[0] = False
        failure[0] = True
        crashed = run(True)
        failure[0] = False
        expect('VELDO-0205 reuse/failures-are-not-cached: race and worker crash stay red with honest attempts',
               raced['status'] == crashed['status'] == 'failed'
               and crashed['executed'] == 1 and crashed['reused'] == 0)
        changed = dict(files)
        changed['.veldo/subject.py'] = (0o644, b'defect')
        active_files[0] = changed
        survivor[0] = True
        stale = run()
        expect('VELDO-0205 reuse/changed-input-cannot-pass: stale cache cannot conceal an edited defective subject',
               stale['status'] == 'failed' and stale['executed'] == 2 and stale['reused'] == 0)
        active_files[0] = files
        survivor[0] = False

        # Run the real coordinator code with planted counting and force-fresh defects.
        source = (ROOT / 'scripts/check_gate_mutations.py').read_text()
        for label, old, new, criterion in [
            ('count', "receipt['executed'] += int(attempted)", "receipt['executed'] += int(attempted or hit)",
             lambda value: value['executed'] == 0 and value['reused'] == 2),
            ('force', 'force_fresh=force_fresh)', 'force_fresh=False)',
             lambda value: value['executed'] == 2 and value['reused'] == 0)]:
            assert source.count(old) == 1
            mutant = types.ModuleType('controlled_coordinator_' + label)
            mutant.__file__ = str(ROOT / 'scripts/check_gate_mutations.py')
            exec(compile(source.replace(old, new), mutant.__file__, 'exec'), mutant.__dict__)
            # Remove the corrupt record and repopulate it through the production path.
            (stage_cache / (broken_key + '.json')).unlink(missing_ok=True)
            run()
            original_gate = gate
            gate = mutant
            try:
                value = run(label == 'force')
            finally:
                gate = original_gate
            expect('VELDO-0205 reuse/' + label + '-negative: planted coordinator regression is detected',
                   value['status'] == 'passed' and not criterion(value))
        text = (ROOT / 'scripts/verify.sh').read_text()
        expect('VELDO-0205 reuse/gate-wiring: both drivers remain required through the coordinator',
               'python3 -B scripts/check_gate_mutations.py' in text
               and 'VELDO_GATE_FORCE_FRESH=1' in text
               and gate.DRIVERS == ('check_teeth_mutations.py', 'check_review_mutations.py'))


_v205_reuse()


# Explicit single key-pass measurement. No worker, snapshot, suite fan-out or mutation runs.
if os.environ.get('VELDO_REUSE_MEASURE') == '1':
    import time as _v205_time
    _v205_started = _v205_time.monotonic()
    _v205_spec = importlib.util.spec_from_file_location('reuse_measure_gate', ROOT / 'scripts/check_gate_mutations.py')
    _v205_gate = importlib.util.module_from_spec(_v205_spec)
    _v205_spec.loader.exec_module(_v205_gate)
    _v205_files = _v205_gate.read_inputs(ROOT)
    _v205_cases = _v205_gate.inventory(ROOT)
    _v205_reuse = _v205_gate.load(ROOT / 'scripts/mutation_reuse.py')
    _v205_session = _v205_reuse.Session(ROOT, _v205_files, _v205_cases,
        _v205_gate.git(ROOT, 'rev-parse', 'HEAD'), {'fixture_version': _v205_gate.FIXTURE_VERSION})
    print('reuse-key-measurement: ' + json.dumps({
        'seconds': _v205_time.monotonic() - _v205_started,
        'files': len(_v205_files), 'bytes': sum(len(body) for _, body in _v205_files.values()),
        'cases': len(_v205_cases), 'qualified': sum(key is not None for key in _v205_session.keys.values()),
        'input_digest': _v205_session.base_digest, 'python': sys.version,
        'note': 'One full production admission/key pass; unqualified cases have null keys. No workers.'}, sort_keys=True))


def _v205_review_repairs():
    import importlib.util
    import subprocess
    import tempfile
    import sys
    import json
    from pathlib import Path
    def load(name):
        spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    reuse = load('mutation_reuse')
    truth = [reuse.truthy(v) for v in ('1', 'TRUE', 'yes', 'On', '0', 'False', 'no', 'off')]
    try:
        reuse.truthy('sometimes')
    except ValueError:
        unknown = True
    else:
        unknown = False
    expect('VELDO-0205 repair/force-values', truth == [True]*4 + [False]*4 and unknown)
    try:
        reuse.runtime_identity([sys.executable], {})
    except ValueError:
        incomplete = True
    else:
        incomplete = False
    expect('VELDO-0205 repair/stdlib-and-tools-required', incomplete)
    with tempfile.TemporaryDirectory(prefix='reuse-boundary-') as tmp:
        top = Path(tmp)
        root, scratch = top / 'root', top / 'scratch'
        root.mkdir(); scratch.mkdir()
        store = reuse.R.Store(top / 'private', root)
        key = reuse.R.digest('collision')
        assert store.put(key, {'first': True})
        expect('VELDO-0205 repair/collision-is-integrity-miss',
               not store.put(key, {'second': True}) and store.get(key) is None and store.integrity_errors)
        sandbox = ROOT / 'scripts/mutation_sandbox.py'
        script = '''import importlib.util, pathlib, subprocess, sys
spec = importlib.util.spec_from_file_location('sandbox', sys.argv[1])
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
s.restrict(sys.argv[2], sys.argv[3])
p = pathlib.Path(sys.argv[4])
try:
 p.read_bytes()
except PermissionError:
 pass
else:
 raise AssertionError('worker read key')
child = subprocess.run(['/usr/bin/cat', str(p)], capture_output=True)
assert child.returncode != 0 and b'Permission denied' in child.stderr
try:
 p.write_bytes(b'changed')
except PermissionError:
 pass
else:
 raise AssertionError('worker wrote key')
pathlib.Path(sys.argv[3], 'allowed').write_text('ok')
'''
        result = subprocess.run([sys.executable, '-B', '-c', script, str(sandbox), str(root),
                                 str(scratch), str(top / 'private/authentication.key')],
                                capture_output=True, text=True, timeout=15)
        expect('VELDO-0205 repair/worker-and-child-cannot-access-store: ' + result.stderr[-300:],
               result.returncode == 0 and (scratch / 'allowed').read_text() == 'ok')
    import copy
    spec = importlib.util.spec_from_file_location('landing', ROOT / 'engine/.veldo/control_verification.py')
    landing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(landing)
    commit = 'a' * 40
    stdout = '== unit\n   unit: pass\nGATE: GREEN (' + commit + ')'
    stamp = {'commit': commit, 'status': 'green', 'force_fresh': True,
             'reused': {'unit': 0, 'mutation': 0}}
    observation = {'schema': 'veldo.gate_observation/v1', 'commit': commit, 'stdout': stdout,
                   'stdout_digest': landing.digest(stdout.encode()), 'exit': 0,
                   'terminal': stdout.splitlines()[-1],
                   'catalog': {'required': ['unit'], 'results': {'unit': 'pass'}},
                   'candidate': {'commit': commit, 'tree': 'b'*40, 'binds_refs': False, 'state': {}},
                   'post_run': {'equal': True, 'state': {}},
                   'outputs': {'last_verify': stamp,
                               'gate_event': dict(stamp, type='gate.passed')}}
    good = not landing.judge(observation)
    for document in ('last_verify', 'gate_event'):
        for counts, forced in [({'mutation': 1}, True), ({'mutation': 0}, False),
                               ({'mutation': '0'}, True), ({}, True)]:
            bad = copy.deepcopy(observation)
            bad['outputs'][document].update(reused=counts, force_fresh=forced)
            good &= 'missing_evidence:gate/fresh_required' in landing.judge(bad)
    expect('VELDO-0205 repair/landing-refuses-reuse', good)
    with tempfile.TemporaryDirectory(prefix='reuse-guard-') as tmp:
        root = Path(tmp)
        (root / '.veldo').mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE).decode().strip()
        git('init', '-q'); git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                              'commit', '--allow-empty', '-qm', 'Fixture')
        stamp['commit'] = git('rev-parse', 'HEAD')
        decisions = []
        for reused in (1, 0):
            stamp['reused']['mutation'] = reused
            (root / '.veldo/last_verify').write_text(json.dumps(stamp))
            env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root), PYTHONOPTIMIZE='1')
            env.pop('VELDO_EMERGENCY', None)
            result = subprocess.run(['bash', str(ROOT / 'scripts/veldo-guard.sh')],
                input=json.dumps({'tool_input': {'command': 'git merge topic'}}),
                text=True, capture_output=True, env=env, timeout=15)
            decisions.append('Landing requires force_fresh' in result.stderr)
        expect('VELDO-0205 repair/real-guard-rejects-reused-stamp', decisions == [True, False])
    import sys
    sys.path.insert(0, str(ROOT / 'scripts'))
    reducer = load('reuse_stamp')
    expect('VELDO-0205 repair/stamp-receipt-counts',
           reducer.fields({'status': 'passed', 'force_fresh': False, 'reused': 7}, False)
           == {'force_fresh': False, 'reused': {'unit': 0, 'mutation': 7}})


_v205_review_repairs()
