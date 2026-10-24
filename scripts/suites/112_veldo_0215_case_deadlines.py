"""VELDO-0215: coordinator deadlines and authority measurements, with scratch stores only."""


def _v215_case_deadlines():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import time
    import types
    from unittest.mock import patch

    path = ROOT / "scripts" / "check_gate_mutations.py"
    spec = importlib.util.spec_from_file_location('gate215', path)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    # A mutant is loaded from a scratch path; its authority still has the real helpers.
    gate.ROOT = ROOT
    case = dict(identity='check_teeth_mutations.py:sample', name='sample', finding=215,
                driver=gate.DRIVERS[0], suite='sample.py', module='sample.py',
                rows=['target'], old='before', new='after')
    files = {name: (0o644, b'before') for name in (
        '.veldo/sample.py', 'scripts/suites/sample.py', 'scripts/suites/shared.py',
        'scripts/check_gate_mutations.py', 'scripts/mutation_observer.py',
        'scripts/reuse_worker.py', 'scripts/mutation_sandbox.py', 'scripts/agent_sandbox.py',
        'scripts/mutation_ownership.py')}

    def row(name, condition):
        expect('VELDO-0215 case-deadlines/' + name, condition)

    with tempfile.TemporaryDirectory(prefix='v215-') as temporary:
        scratch = Path(temporary)
        key = gate.case_time_key(case, files, None)
        store = scratch / 'times'
        store.mkdir()
        def sample(seconds, sample_key=key):
            (store / (sample_key + '.json')).write_text(json.dumps(
                dict(authority=str(ROOT), key=sample_key, seconds=seconds)))
        bounds = [gate.case_deadline(key, store) == 120]
        for seconds, wanted in ((80, 240), (1, 120), (10000, 1800), (1e308, 1800),
                                (-1, 120), (True, 120), ('80', 120), (10 ** 400, 120),
                                (float('nan'), 120), (float('inf'), 120)):
            sample(seconds)
            bounds.append(gate.case_deadline(key, store) == wanted)
        (store / (key + '.json')).write_text('[]')
        bounds.append(gate.case_deadline(key, store) == 120)
        row('bounds', all(bounds))

        keys = [gate.case_time_key(dict(case, new='different'), files, None)]
        for name in files:
            changed = dict(files, **{name: (0o644, b'changed')})
            keys.append(gate.case_time_key(case, changed, None))
        keys.append(gate.case_time_key(case, files, dict(suites=['sample'], entries=['sample'],
                                                        declaration='other')))
        sample(80)
        row('key-binding', all(k != key and gate.case_deadline(k, store) == 120 for k in keys)
            and gate.case_time_key(case, dict(files, **{'proof/note': (0o644, b'new')}), None) == key)

        other = dict(case, identity='second', name='second')
        controls = gate.control_jobs([case, other], gate.control_group, {},
                                     {case['identity']: 120, 'second': 480})
        row('shared-controls', len(controls) == 2
            and all(j['budget_seconds'] == 480 for j in controls.values()))
        row('combined-budget', gate.budget_for(2, 16, [480, 480, 120, 480]) >= 1680
            and gate.budget_for(2, 1, [480, 480, 120, 480]) >= 1680)

        def exercise(duration=150, fault=None, reuse_hit=False, measure=True):
            runroot = scratch / ('run-' + str(len(list(scratch.glob('run-*')))))
            runroot.mkdir()
            times = runroot / 'times'
            # This is the authority's own root for this in-process fixture; its cache is scratch.
            sample(80)
            clock, kills, cleaned, children, alarms = [1.0], [], [], [], []
            pool = gate.SuiteResources({'suites': [{'file': 'sample.py'}], 'resource_capacities': {}})
            class Session:
                def __init__(self, *args, **kwargs):
                    self.keys = {case['identity']: None}
                    self.reasons = {case['identity']: 'fixture'}
                    self.hits = set([case['identity']]) if reuse_hit else set()
                    self.forced, self.store, self.base_digest = False, None, 'fixture'
                def lookup(self, item, validate):
                    return valid_record if reuse_hit else None
                def evidence(self, item, record, hit):
                    return {'case': item}
                def unchanged(self):
                    return fault != 'race'
                def publish(self, *args):
                    pass
            class Child:
                def __init__(self, argv, **kwargs):
                    self.job = json.loads(Path(argv[-1]).read_text())
                    self.pid, self.returncode, self.born = 1000000 + len(children), None, clock[0]
                    children.append(self)
                    mode = self.job['mode']
                    ok = mode != 'mutant' and fault != 'false-baseline'
                    obs = dict(count=1, observations=[['TEST target', ok]], row_names=['TEST target'],
                               failed_rows=[] if ok else ['TEST target'],
                               failed_details=[] if ok else [['TEST target', 'inner operation expired']])
                    kwargs['stdout'].write(json.dumps(dict(observation=obs, replacement_count=1,
                        old_digest='a', new_digest='b' if mode == 'mutant' else 'a')).encode())
                def poll(self):
                    clock[0] += 30
                    if fault != 'hang-' + self.job['mode'] and clock[0] - self.born >= duration:
                        self.returncode = 0
                    return self.returncode
                def wait(self, timeout=None):
                    if self.returncode is None:
                        self.returncode = -9
                    return self.returncode
            real_load = gate.load
            def loader(p):
                if Path(p).name == 'case_reuse.py':
                    return types.SimpleNamespace(Session=Session)
                if Path(p).name == 'mutation_ownership.py':
                    return types.SimpleNamespace(cleanup=lambda home, ledger: cleaned.append(str(home)))
                return real_load(p)
            real_deadline, real_record = gate.case_deadline, gate.record_case_times
            with contextlib.ExitStack() as stack:
                overrides = dict(inventory=lambda *a: [case], read_inputs=lambda *a: files,
                    git=lambda *a: 'head', snapshot=lambda *a: None, inputs_unchanged=lambda *a: True,
                    load=loader, case_deadline=lambda k: real_deadline(k, store),
                    record_case_times=lambda root, samples, authority=False: real_record(
                        root, samples, times, authority=authority), CASE_TIMES=times)
                for name, value in overrides.items():
                    stack.enter_context(patch.object(gate, name, value))
                stack.enter_context(patch.object(gate.Workers, 'launcher_fds', lambda self: ()))
                stack.enter_context(patch.object(gate.SuiteResources, 'from_root', lambda *a: pool))
                stack.enter_context(patch.object(gate.subprocess, 'Popen', Child))
                stack.enter_context(patch.object(gate.os, 'killpg', lambda pid, sig: kills.append(pid)))
                stack.enter_context(patch.object(gate.time, 'monotonic', lambda: clock[0]))
                stack.enter_context(patch.object(gate.time, 'sleep', lambda _: None))
                stack.enter_context(patch.object(gate.signal, 'setitimer', lambda *a: alarms.append(a)))
                receipt = gate.run_stage(runroot, runroot / '.git', parallel=1, measure=measure)
            return receipt, children, kills, cleaned, times, alarms

        with patch.object(gate, 'inventory', side_effect=subprocess.TimeoutExpired('inventory', 120)):
            expired = gate.run_stage(scratch, scratch / '.git')
        row('setup-timeout', expired.get('error') == 'mutation_budget_exceeded')

        obs = lambda ok: dict(count=1, observations=[['TEST target', ok]], row_names=['TEST target'],
                              failed_rows=[] if ok else ['TEST target'])
        valid_record = dict(schema=gate.SCHEMA, fixture_version=gate.FIXTURE_VERSION, case=case,
                            baseline=obs(True), noop=obs(True), mutant=obs(False),
                            replacement_count=1, old_digest='a', new_digest='b')
        passed, children, kills, cleaned, times, alarms = exercise()
        row('measured-worker', passed['status'] == 'passed' and len(children) == 3
            and all(o['budget_seconds'] == 240 for o in passed['worker_outcomes'])
            and passed['budget_seconds'] >= 840
            and any(a[1] >= 840 for a in alarms))
        row('slow-pass', passed['status'] == 'passed' and passed['executed'] == 1
            and all(120 < o['elapsed'] < 240 for o in passed['worker_outcomes']))
        hang_results = [exercise(fault='hang-' + mode) for mode in ('baseline', 'noop', 'mutant')]
        row('hang-timeout', all(r['error'] == 'mutation_budget_exceeded'
            and any(o.get('error') == 'mutation_budget_exceeded' and 240 <= o['elapsed'] <= 270
                    for o in r['worker_outcomes'])
            and len(ch) == count and len(k) == len(cl) == count
            and r['surviving_workers'] == 0 and not list(t.glob('*.json'))
            for count, (r, ch, k, cl, t, _) in enumerate(hang_results, 1)))
        bad, _, _, _, bad_times, _ = exercise(fault='false-baseline')
        row('baseline-details', bad['error'] == 'invalid_baseline'
            and 'inner operation expired' in bad['detail'] and 'TEST target' in bad['detail'])
        raced = exercise(fault='race')
        reused = exercise(reuse_hit=True)
        library = exercise(measure=False)
        record = json.loads((times / (key + '.json')).read_text()) if (times / (key + '.json')).exists() else {}
        owner = scratch / 'owner'
        with patch.object(gate, 'CASE_TIMES', owner):
            refused = gate.record_case_times(scratch / 'candidate', {key: 80}, owner)
            wrote = gate.record_case_times(scratch / 'candidate', {key: 80}, owner, authority=True)
        row('authority-recording', record.get('seconds') == 150 and refused is False and wrote is True
            and not list(bad_times.glob('*.json')) and not list(raced[4].glob('*.json'))
            and reused[0]['status'] == 'passed' and reused[0]['reused'] == 1
            and not list(reused[4].glob('*.json')) and not list(library[4].glob('*.json')))

        # An installed authority verifies another root. Only its CLI opts into recording;
        # neither a caller environment variable nor --root grants a fixture library call this.
        calls = []
        def cli_stage(root, common, **kwargs):
            calls.append((root, kwargs))
            return dict(status='passed', registered=0, executed=0, reused=0, rejected=0,
                        worker_invocations=0, elapsed=0)
        with patch.object(gate.sys, 'argv', ['check_gate_mutations.py', '--root', str(scratch / 'candidate')]), \
                patch.object(gate, 'run_stage', cli_stage), \
                patch.object(gate, 'common_directory', lambda root: root / '.git'), \
                patch.object(gate, 'load', lambda path: types.SimpleNamespace(mutation_leg=lambda: None)), \
                contextlib.redirect_stdout(__import__('io').StringIO()):
            code = gate.main()
        row('candidate-authority', code == 0 and calls[0][0] == scratch / 'candidate'
            and calls[0][1].get('measure') is True and wrote is True)

        prune = scratch / 'prune'
        prune.mkdir()
        old = time.time() - 31 * 86400
        for name, authority, stale in (('a' * 32 + '.json', scratch / 'gone', False),
                ('b' * 32 + '.json', ROOT, True), ('c' * 32 + '.json', ROOT, False),
                ('.pending-old', ROOT, True), ('foreign', ROOT, True)):
            p = prune / name
            p.write_text(json.dumps({'authority': str(authority)}))
            if stale:
                os.utime(p, (old, old))
        gate.record_case_times(ROOT, {key: 80}, prune)
        row('store-pruned', {p.name for p in prune.iterdir()} == {key + '.json', 'c' * 32 + '.json', 'foreign'})

        # Real OS child, actual process-group kill and reap; no fake clock on this row.
        # Replace only the launch command; production Workers.run/finish/check_worker execute.
        home = scratch / 'real'
        home.mkdir()
        real_popen, real_load = subprocess.Popen, gate.load
        pool = gate.SuiteResources({'suites': [{'file': 'sample.py'}], 'resource_capacities': {}})
        workers = gate.Workers(time.monotonic() + 20, pool, parallel=1)
        def launch(argv, **kwargs):
            return real_popen([sys.executable, '-c', 'import time; time.sleep(60)'], **kwargs)
        def loader(p):
            if Path(p).name == 'mutation_ownership.py':
                return types.SimpleNamespace(cleanup=lambda *a: {})
            return real_load(p)
        error = None
        with patch.object(gate.subprocess, 'Popen', launch), patch.object(gate, 'load', loader), \
                patch.object(gate.Workers, 'launcher_fds', lambda self: ()):
            try:
                workers.run({'hang': dict(case=case, mode='baseline', budget_seconds=.2)}, home, ROOT)
            except gate.Refused as exc:
                error = exc.code
        row('real-hang-reaped', error == 'mutation_budget_exceeded' and workers.invocations == 1
            and not workers.active and workers.outcomes[0]['returncode'] == -9
            and workers.outcomes[0]['budget_seconds'] == .2)


_v215_case_deadlines()
