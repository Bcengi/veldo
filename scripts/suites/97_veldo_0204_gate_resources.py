"""Owner-authorized gate repair: admission and fixture ownership, no mutation drive."""


def _v204_gate_resources():
    import ast
    import contextlib
    import importlib.util
    import json
    from pathlib import Path
    import tempfile
    import time
    import types
    from unittest.mock import patch

    spec = importlib.util.spec_from_file_location('v204_gate_resources', ROOT / 'scripts/check_gate_mutations.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    manager = 'systemd_user_manager'
    manifest = {'resource_capacities': {manager: 2, 'disk': 1}, 'suites': [
        {'file': 'ordinary.py'}, {'file': 'shared.py', 'resources': {manager: 1}},
        {'file': 'exclusive.py', 'resources': {manager: 'exclusive'}},
        {'file': 'both.py', 'resources': {manager: 1, 'disk': 1}}]}

    def job(suite, mode='baseline'):
        return {'case': {'driver': 'fixture', 'suite': suite + '.py'}, 'mode': mode}

    real = gate.SuiteResources.from_root(ROOT)
    protected = real.demand({'case': {'suite': '63_veldo_0040_containment.py'}})
    expect('VELDO-0204 gate/manager-declaration: containment reserves the whole manager, including '
           'against authority reloads and other real engine scopes',
           protected == {manager: real.capacity[manager]}
           and real.demand({'case': {'suite': '66_veldo_0047_authority.py'}}) == {manager: 1}
           and real.demand({'case': {'suite': '86_veldo_0127_agent_configuration.py'}}) == {manager: 1})

    pool = gate.SuiteResources(manifest)
    pool.acquire('first', job('shared'))
    waiting = [('exclusive', job('exclusive')), ('shared', job('shared')), ('ordinary', job('ordinary'))]
    chosen = pool.select(waiting)
    pool.release('first')
    exclusive = pool.select(waiting)
    pool.acquire('exclusive', waiting[0][1])
    during = pool.select(waiting[1:])
    pool.release('exclusive')
    expect('VELDO-0204 gate/resources-fair-admission: unrelated work bypasses a waiting exclusive job; '
           'later shared users cannot starve it and cannot overlap it', chosen == 2 and exclusive == 0 and during == 1)

    invalid = []
    for capacity in (0, -1, True, 1.5, '2'):
        try:
            gate.SuiteResources(manifest, {manager: capacity})
        except gate.Refused as error:
            invalid.append(error.code)
    for demand in (0, -1, True, 3, 1.5, 'bogus'):
        broken = json.loads(json.dumps(manifest))
        broken['suites'][1]['resources'][manager] = demand
        try:
            gate.SuiteResources(broken)
        except gate.Refused as error:
            invalid.append(error.code)
    for changed in ({'unregistered': 1},):
        try:
            gate.SuiteResources(manifest, changed)
        except gate.Refused as error:
            invalid.append(error.code)
    try:
        pool.demand(job('undeclared'))
    except gate.Refused as error:
        invalid.append(error.code)
    larger = gate.SuiteResources(manifest, {manager: 4})
    expect('VELDO-0204 gate/resources-invalid-refused: invalid, unknown and impossible requirements '
           'fail before launch; exclusive demand follows configured capacity',
           invalid == ['invalid_resource_requirement'] * 13
           and larger.demand(job('exclusive')) == {manager: 4})

    # Drive the production process scheduler with controlled child completion. No systemd,
    # clocks, sleeps, mutation executables or timing-based assertions in these regressions.
    def drive(jobs, *, failure=None):
        resources = gate.SuiteResources(manifest)
        workers = gate.Workers(time.monotonic() + 60, resources)
        live, launched, overlaps, handles = {}, [], [], []
        peak = [0]
        class Child:
            def __init__(self, argv, **kwargs):
                document = json.loads(Path(argv[-1]).read_text())
                self.suite = document['case']['suite']
                self.pid = 1000000 + len(launched)
                self.returncode = None
                self.polls = 0
                handles.extend((kwargs['stdout'], kwargs['stderr']))
                if failure == 'spawn':
                    raise OSError('controlled spawn failure')
                kwargs['stdout'].write(b'{}')
                live[self.pid] = self
                launched.append(document)
                overlaps.append([p.suite for p in live.values()])
                peak[0] = max(peak[0], len(live))
            def poll(self):
                self.polls += 1
                if self.polls >= 2:
                    self.returncode = 1 if failure == 'exit' else 0
                    live.pop(self.pid, None)
                return self.returncode
            def wait(self, timeout=None):
                live.pop(self.pid, None)
                self.returncode = 0
                return 0
        def timeout(*args):
            raise gate.Refused('mutation_budget_exceeded', 'controlled deadline')
        error, result = None, {}
        with tempfile.TemporaryDirectory(prefix='v204-admission-') as temporary:
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(gate, 'PARALLEL', 16))
                stack.enter_context(patch.object(gate.subprocess, 'Popen', Child))
                stack.enter_context(patch.object(gate.os, 'killpg', lambda *args: None))
                stack.enter_context(patch.object(gate.time, 'sleep', lambda *args: None))
                if failure == 'deadline':
                    stack.enter_context(patch.object(workers, 'check_worker', timeout))
                try:
                    result = workers.run(jobs, Path(temporary), ROOT)
                except (OSError, gate.Refused) as caught:
                    error = caught
        clean = (not live and not workers.active and not resources.held
                 and not any(resources.used.values()) and all(f.closed for f in handles))
        return result, launched, overlaps, peak[0], error, clean, resources.summary()

    jobs = {'shared-first': job('shared'), 'exclusive': job('exclusive', 'noop'),
            'shared-later': job('shared', 'mutant')}
    jobs.update({'ordinary-%d' % i: job('ordinary') for i in range(30)})
    result, launched, overlaps, peak, error, clean, summary = drive(jobs)
    valid = all(sum(s != 'ordinary.py' for s in active) == 1
                for active in overlaps if 'exclusive.py' in active)
    expect('VELDO-0204 gate/resources-workers: baseline, noop and mutants all reserve before spawn; '
           'the actual coordinator keeps 16 unrelated slots busy and releases every reservation',
           set(result) == set(jobs) and len(launched) == len(jobs) and peak == 16
           and valid and error is None and clean and summary['peak_slots'][manager] == 2)
    failures = [drive(jobs, failure=kind) for kind in ('spawn', 'exit', 'deadline')]
    expect('VELDO-0204 gate/resources-failure-cleanup: spawn errors, failed children and deadlines '
           'close output files, reap children and release resource slots',
           all(row[4] is not None and row[5] for row in failures))

    import concurrent.futures
    future_resources = gate.SuiteResources(manifest)
    admissions = []
    def submit(document):
        admissions.append((document, dict(future_resources.used)))
        future = concurrent.futures.Future()
        future.set_result(document['mode'])
        return future
    collected = future_resources.run_futures(jobs, submit, 16)
    expect('VELDO-0204 gate/resources-standalone: thread-pool admission enforces the same resource '
           'contract for honest and broken workers without blocking waiting pool threads',
           set(collected) == set(jobs) and len(admissions) == len(jobs)
           and all(used[manager] <= 2 for _, used in admissions)
           and any(doc['case']['suite'] == 'ordinary.py' and used[manager] == 2 for doc, used in admissions)
           and not future_resources.held and not any(future_resources.used.values()))

    # Execute the actual fixture owners extracted from their suites, with faults at the
    # allocation's first consumer and at normal completion. The pristine leak fails these
    # checks because its real mkdtemp call leaves entries in the private TMPDIR.
    class Fault(Exception):
        pass
    def fail(*args, **kwargs):
        raise Fault('controlled fixture failure')
    tree = ast.parse((ROOT / 'scripts/suites/13_warp_0623_codified_live.py').read_text())
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    outcomes = []
    with tempfile.TemporaryDirectory(prefix='v204-cleanup-') as directory:
        with patch.object(tempfile, 'tempdir', directory):
            for point in ('build', 'run', 'success', 'refusal'):
                class Refusal(Exception):
                    code = 'CONTROL'
                def run(*args, **kwargs):
                    if point == 'run':
                        fail()
                    if point == 'refusal':
                        raise Refusal()
                    return {'defect_names': []}
                mod = types.SimpleNamespace(build_fixture_tree=fail if point == 'build' else lambda *a: (None, None),
                                            run=run, EquivRefusal=Refusal)
                ns = {'tempfile': tempfile, '_W12_MUT_B': {}, '_W12_SENTINEL': 'sentinel',
                      '_w12_fresh': lambda *a: (mod, [1])}
                exec(compile(ast.Module(body=[functions['_w12_cell_B']], type_ignores=[]), '<fixture>', 'exec'), ns)
                try:
                    ns['_w12_cell_B']((None, 'clean'))
                except Fault:
                    pass
                outcomes.append(not list(Path(directory).iterdir()))
                # Keep the regression itself tidy even against the pre-fix implementation.
                for p in Path(directory).iterdir():
                    __import__('shutil').rmtree(p)
            for point in ('success', 'failure'):
                mod = types.SimpleNamespace(capture=fail if point == 'failure' else
                                            lambda *a: types.SimpleNamespace(reconcile=lambda: None), LabelRefusal=Fault)
                ns = {'tempfile': tempfile, 'Path': Path, '_W12_SELFEDIT': 'pass'}
                exec(compile(ast.Module(body=[functions['_w12_probe_selfedit']], type_ignores=[]), '<fixture>', 'exec'), ns)
                try:
                    ns['_w12_probe_selfedit'](mod)
                except (Fault, AttributeError):
                    pass
                outcomes.append(not list(Path(directory).iterdir()))
                for p in Path(directory).iterdir():
                    __import__('shutil').rmtree(p)
    expect('VELDO-0204 gate/temporary-fixtures: matrix cells and self-edit probes leave no directories '
           'after construction failure, execution failure, refusal or success', all(outcomes) and len(outcomes) == 6)

    # Tiny/eq/mono allocations used to leak at module scope as well. Run their actual
    # allocation and work statements, forcing an exception inside each owner block.
    owned = []
    for node in ast.walk(tree):
        if isinstance(node, ast.With) and 'veldo0712-' in ast.unparse(node.items[0].context_expr):
            owned.append(node)
    outcomes = []
    with tempfile.TemporaryDirectory(prefix='v204-top-cleanup-') as directory:
        with patch.object(tempfile, 'tempdir', directory):
            for node in owned:
                ns = {'tempfile': tempfile, 'Path': Path, '_W12_TINY': '', '_w12_v': 'clean',
                      '_w12_L': types.SimpleNamespace(capture=fail),
                      '_w12_E': types.SimpleNamespace(build_fixture_tree=fail),
                      '_w12_monos': {'clean': ''}, '_w12_S': types.SimpleNamespace(Slicer=fail),
                      '_W12_SELFEDIT': '', 'L': types.SimpleNamespace(capture=fail, LabelRefusal=ValueError),
                      'mod': types.SimpleNamespace(build_fixture_tree=fail), 'variant': 'clean'}
                # Function owners are covered above; this loop covers only module owners.
                if any(n in list(ast.walk(f)) for f in functions.values() for n in [node]):
                    continue
                try:
                    exec(compile(ast.Module(body=[node], type_ignores=[]), '<owner>', 'exec'), ns)
                except Fault:
                    pass
                outcomes.append(not list(Path(directory).iterdir()))
    expect('VELDO-0204 gate/module-fixtures-cleanup: all three module-level temporary owners '
           'remove their trees when construction or observation raises', len(outcomes) == 3 and all(outcomes))

    landing_results = []
    for filename in ('69_veldo_0058_gate_output.py', '70_veldo_0057_landing.py'):
        tree = ast.parse((ROOT / 'scripts/suites' / filename).read_text())
        land = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'land')
        for failure in (None, 'sync_main', 'reconcile', 'gate', 'record', 'finalize', 'between'):
            with tempfile.TemporaryDirectory(prefix='v204-candidates-') as directory:
                class Ops:
                    def __init__(self, *args, **kwargs):
                        self.workspace = Path(tempfile.mkdtemp(prefix='veldo-candidate-', dir=directory))
                    def discard(self):
                        __import__('shutil').rmtree(self.workspace)
                    def __getattr__(self, name):
                        def call(*args):
                            if name == failure:
                                fail()
                            return {'ok': True, 'workspace': str(self.workspace)}
                        return call
                ns = {'LD': types.SimpleNamespace(GitLandOps=Ops), 'inspect': __import__('inspect'),
                      'observations': directory, 'caller': directory, 'builds': {'A': {'branch': 'A'}},
                      'LANDER': None, 'DOMAIN': None, 'REPOSITORY': None, 'authority_policy': None,
                      'outcome_of': lambda fn: fn(), 'remote_tip': lambda: 'tip', 'snapshot': lambda *a: {},
                      'Path': Path, 'json': json}
                exec(compile(ast.Module(body=[land], type_ignores=[]), '<lander-fixture>', 'exec'), ns)
                try:
                    if filename.startswith('69'):
                        ns['land']('A', {}, between=fail if failure == 'between' else None)
                    else:
                        ns['land']('A', between=fail if failure == 'between' else None)
                except Fault:
                    pass
                landing_results.append(not list(Path(directory).iterdir()))
    expect('VELDO-0204 gate/candidate-cleanup: direct landing fixtures discard candidates on success '
           'and when each stage or the between-stage hook raises',
           len(landing_results) == 14 and all(landing_results))


_v204_gate_resources()
