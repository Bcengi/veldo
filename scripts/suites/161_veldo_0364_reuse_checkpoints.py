"""Authority checkpoint boundaries; controlled workers, real validation and signing store."""


def _v364_checkpoints():
    import copy
    import contextlib
    import io
    import json
    from pathlib import Path
    import tempfile
    import types
    from unittest.mock import patch

    def load(path):
        module = types.ModuleType('v364_' + path.stem)
        # Mutation materialization changes the source path, not the fixture authority root.
        module.__file__ = str(ROOT / 'scripts' / path.name)
        exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
        return module

    G = load(ROOT / "scripts" / "check_gate_mutations.py")
    C = G.load(ROOT / 'scripts/case_reuse.py')
    original_session = C.Session

    def row(name, condition):
        expect('VELDO-0364 checkpoint/' + name, condition)

    def observation(ok):
        return dict(observations=[['fixture target', ok]], count=1,
                    row_names=['fixture target'], failed_rows=[] if ok else ['fixture target'])

    cases = [dict(name=name, identity=G.DRIVERS[0] + ':' + name, driver=G.DRIVERS[0],
                  suite=name + '.py', module='subject.py', old='yes', new='no', rows=['target'])
             for name in ('good', 'bad', 'pending')]

    def record(case):
        return dict(schema=G.SCHEMA, fixture_version=G.FIXTURE_VERSION, case=case,
                    input_digest=C.R.digest(case), replacement_count=1, old_digest='old', new_digest='new',
                    baseline=observation(True), noop=observation(True), mutant=observation(False))

    class Spy:
        store = None
        def __init__(self):
            self.writes = []
        def unchanged(self):
            return True
        def publish(self, case, value, validate):
            self.writes.append(case['identity'])
            return True

    good = cases[0]
    completed = {good['identity']: (good, record(good))}
    for name in ('red', 'input-race', 'runtime-race', 'cleanup', 'active', 'cleanup-outcome',
                 'audit', 'invalid'):
        reuse = Spy()
        workers = types.SimpleNamespace(active={}, outcomes=[])
        receipt = dict(status='failed', error='later_case_failed', audit={'entries': []})
        errors, source = [], copy.deepcopy(completed)
        if name == 'runtime-race':
            reuse.unchanged = lambda: False
        if name == 'cleanup':
            errors = [RuntimeError('cannot reap')]
        if name == 'active':
            workers.active['remaining'] = object()
        if name == 'cleanup-outcome':
            workers.outcomes.append({'error': 'worker_cleanup_error'})
        if name == 'audit':
            receipt['audit']['entries'].append({'matched': False})
        if name == 'invalid':
            source[good['identity']][1]['mutant'] = observation(True)
        try:
            G.checkpoint_completed(reuse, source, workers, errors, receipt, lambda: name != 'input-race')
        except G.Refused:
            pass
        row(name, reuse.writes == ([good['identity']] if name == 'red' else [])
            and receipt['status'] == 'failed' and receipt['error'] == 'later_case_failed')

    # Drive the actual stage reducer through success, invalid verdict and fatal later worker.
    # Only inventory/snapshot and process execution are stood in. No nested gate is started.
    with tempfile.TemporaryDirectory(prefix='v364-') as temporary:
        top = Path(temporary)
        for scenario in ('red', 'fatal', 'force', 'green', 'input-race', 'runtime-race', 'cleanup',
                         'input-restored', 'runtime-restored', 'cleanup-raises'):
            root = top / scenario
            root.mkdir()
            cache = top / (scenario + '-store')
            store = C.R.Store(cache, root)
            sessions, lifecycle = [], []
            original_load = G.load

            class Workers(G.Workers):
                def run(self, jobs, directory, frozen, on_result=None):
                    results = {}
                    for name, job in jobs.items():
                        case, mode = job['case'], job['mode']
                        if scenario == 'fatal' and mode == 'mutant' and case['name'] == 'bad':
                            raise G.Refused('driver_error', 'later worker failed')
                        value = record(case)
                        if scenario in ('red', 'force') and mode == 'mutant' and case['name'] == 'bad':
                            value['mutant'] = observation(True)
                        self.invocations += 1
                        self.outcomes.append(dict(name=name, driver=case['driver'], mode=mode,
                            elapsed=1.0, returncode=0, cleanup={'units': [], 'directories': 1},
                            scratch_removed=True))
                        result = dict(result=dict(observation=value[mode], **{k: value[k] for k in
                                      ('replacement_count', 'old_digest', 'new_digest')}), elapsed=1.0)
                        results[name] = result
                        if on_result:
                            on_result(name, result)
                    return results

                def cleanup(self, on_result=None):
                    lifecycle.append('cleanup')
                    if scenario == 'cleanup-raises':
                        raise RuntimeError('cleanup raised')
                    return [RuntimeError('cleanup failed')] if scenario == 'cleanup' else []

            def session(*args, force_fresh=False, **kwargs):
                s = original_session.__new__(original_session)
                s.root, s.store, s.forced = root, store, force_fresh
                s.base_digest = 'fixture'
                s.case_digests = {c['identity']: C.R.digest(c) for c in cases}
                s.keys = {k: None if force_fresh else v for k, v in s.case_digests.items()}
                s.reasons = dict.fromkeys(s.keys, 'force_fresh' if force_fresh else 'miss')
                s.hits, s.stale, s.snapshots, s.authenticated_digests = {}, {}, {}, {}
                s.runtime_checks, s.runtime_absent = {}, {}
                s.gate_run = 'controlled-fixture'
                runtime_checks = iter((False, True))
                s.unchanged = (lambda: next(runtime_checks)) if scenario == 'runtime-restored' else (
                    lambda: scenario != 'runtime-race')
                original_publish = s.publish
                def publish(*args):
                    assert 'cleanup' in lifecycle
                    lifecycle.append('publish')
                    return original_publish(*args)
                s.publish = publish
                sessions.append(s)
                return s

            with patch.object(C, 'Session', side_effect=session), \
                 patch.object(G, 'load', side_effect=lambda p: C if p.name == 'case_reuse.py' else original_load(p)), \
                 patch.object(G, 'Workers', Workers), patch.object(G, 'inventory', return_value=cases), \
                 patch.object(G, 'read_inputs', return_value={'scripts/check_gate_mutations.py': (0o644, b'fixture')}), \
                 patch.object(G, 'git', return_value='fixture'), patch.object(G, 'snapshot'), \
                 patch.object(G, 'inputs_unchanged', side_effect=([False, True] if scenario == 'input-restored'
                     else lambda *args: scenario != 'input-race')), \
                 patch.object(G, 'case_deadlines', side_effect=lambda keys: dict.fromkeys(keys, 1)), \
                 patch.object(G, 'record_case_times'), \
                 patch.object(G.SuiteResources, 'from_root', side_effect=lambda *a: G.SuiteResources(
                     {'suites': [{'file': c['suite']} for c in cases]})), \
                 contextlib.redirect_stdout(io.StringIO()):
                receipt = G.run_stage(root, root / '.git', force_fresh=scenario == 'force')
            expected = [cases[0]] if scenario == 'fatal' else (
                [cases[0], cases[2]] if scenario == 'red' else cases if scenario == 'green' else [])
            published = receipt['checkpoint']['published']
            row('stage-' + scenario, published == [c['identity'] for c in expected]
                and receipt['status'] == ('passed' if scenario == 'green' else 'failed')
                and receipt['registered'] == len(receipt['case_receipts']) == 3
                and receipt['executed'] == (1 if scenario == 'fatal' else 3)
                and receipt['reused'] == 0 and receipt['surviving_workers'] == 0
                and all(store.get(C.R.digest(c)) is not None for c in expected))
            if scenario == 'fatal':
                row('pending-coverage', receipt['case_receipts'][-1]['source'] == 'pending'
                    and receipt['case_receipts'][-1]['validated'] is False
                    and receipt['error'] == 'driver_error' and receipt['detail'] == 'driver_error: later worker failed')
            if scenario == 'green':
                saved = store.get(C.R.digest(good))
                row('authenticated', saved is not None and saved['case'] == good)
                path = cache / (C.R.digest(good) + '.json')
                path.write_text('{}')
                row('corrupt-miss', store.get(C.R.digest(good)) is None)
        # This is a refusal proof, not a planted production sensitivity approval.
        row('sensitivity-unproved', not C.sensitivity_proved(top, 'unproved'))
        (top / 'sensitivity').mkdir()
        (top / 'sensitivity' / 'wrong.json').write_text(json.dumps(
            {'schema': C.SENSITIVITY_SCHEMA, 'key': 'different'}))
        row('sensitivity-wrong-key', not C.sensitivity_proved(top, 'wrong'))


_v364_checkpoints()
