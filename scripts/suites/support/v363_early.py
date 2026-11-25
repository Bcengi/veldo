"""Event-driven coordinator doubles: no subprocess, manager, native cgroup or load."""
import contextlib
import json
import os
from pathlib import Path
import tempfile
import types
from unittest.mock import patch


def cases_for(gate, sizes=(2, 1, 1)):
    return [dict(identity='g%d-c%d' % (g, n), name='g%d-c%d' % (g, n),
                 driver=gate.DRIVERS[0], finding=363, suite='g%d.py' % g,
                 module='target.py', rows=['target'], old='before', new='after')
            for g, size in enumerate(sizes) for n in range(size)]


def drive(gate, *, cases=None, durations=None, history=None, fault=None, collect='0', parallel=3):
    cases = cases or cases_for(gate)
    durations = durations or {}
    audited = bool(fault and fault.startswith('audit-'))
    fault = fault.removeprefix('audit-') if fault else fault
    invalidated = []
    clock, children, launched, settled, reaped, closed = [0.0], {}, [], [], [], []
    original_workers = gate.Workers
    holders = []
    class Workers(original_workers):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            holders.append(self)
            self.planted_stale = False
        def finish(self, name, error=None):
            completed = super().finish(name, error)
            if fault == 'stale' and name == cases[0]['identity'] and not self.planted_stale:
                self.planted_stale = True
                self.case_reuse.stale[name] = dict(reason='fixture undeclared input')
                completed.update(result=None, declaration_stale='fixture undeclared input')
            return completed
        def run(self, jobs, *args, **kwargs):
            if fault == 'missing-verdict':
                jobs = {n: j for n, j in jobs.items() if n != 'g2-c0'}
            if fault == 'missing-dependency':
                jobs['g2-c0']['requires'] = 'absent'
            return super().run(jobs, *args, **kwargs)
    class Session:
        def __init__(self, *args, **kwargs):
            self.keys = {c['identity']: None for c in cases}
            self.reasons = {c['identity']: 'fixture' for c in cases}
            self.hits, self.snapshots, self.store, self.forced = {}, {}, None, True
            self.stale = {}
            if fault == 'stale':
                self.snapshots[cases[0]['identity']] = True
            self.base_digest = 'fixture'
            if audited:
                case = cases[0]
                def obs(ok):
                    return dict(count=1, observations=[['TEST target', ok]], row_names=['TEST target'],
                                failed_rows=[] if ok else ['TEST target'])
                record = dict(schema=gate.SCHEMA, fixture_version=gate.FIXTURE_VERSION, case=case,
                              input_digest='fixture', baseline=obs(True), noop=obs(True), mutant=obs(False),
                              replacement_count=1, old_digest='a', new_digest='b')
                self.hits[case['identity']] = record
                self.keys[case['identity']] = 'fixture-key'
                self.authenticated_digests = {case['identity']: gate.digest(record)}
                self.store = types.SimpleNamespace(integrity_errors=[], secret=None,
                                                    invalidate=invalidated.append)
        def prepare(self, *args):
            return {}
        def lookup(self, case, *args):
            return self.hits.get(case['identity'])
        def mark_stale(self, case, reason):
            self.stale[case['identity']] = dict(identity=case['identity'], reason=reason)
        def evidence(self, case, record, reused):
            return dict(record, reused=reused)
        def unchanged(self):
            return True
        def publish(self, *args):
            pass
    class Child:
        def __init__(self, argv, **kwargs):
            job = json.loads(Path(argv[-1]).read_text())
            self.case, self.mode = job['case'], job['mode']
            identity = self.case['identity']
            group_name = identity if fault == 'stale' and identity == cases[0]['identity'] else gate.control_group(self.case)
            self.name = identity if self.mode == 'mutant' else group_name + ':' + self.mode
            self.pid, self.returncode = 9000000 + len(launched), None
            group = self.case['suite']
            duration = durations.get(self.name, {'g0.py': 1, 'g1.py': 10}.get(group, 20))
            self.due = clock[0] + duration
            children[self.pid] = self
            launched.append([self.name, self.mode, clock[0]])
            ok = self.mode != 'mutant'
            if identity == cases[0]['identity']:
                if fault == 'survivor' and self.mode == 'mutant':
                    ok = True
                if fault == 'baseline' and self.mode == 'baseline':
                    ok = False
                if fault == 'noop' and self.mode == 'noop':
                    ok = False
            rows = [['TEST target', ok]]
            if fault == 'missing-target' and identity == cases[0]['identity']:
                rows = [['TEST other', ok]]
            if fault == 'mismatch' and identity == cases[0]['identity'] and self.mode == 'noop':
                rows.append(['TEST extra', True])
            obs = dict(observations=rows, count=len(rows), row_names=[n for n, _ in rows],
                       failed_rows=[n for n, v in rows if not v])
            if identity == cases[0]['identity'] and self.mode == 'baseline':
                if fault == 'watchdog':
                    obs['watchdog_fired'] = True
                if fault == 'malformed':
                    obs['count'] = 999
            kwargs['stdout'].write(json.dumps(dict(observation=obs, replacement_count=1,
                old_digest='a', new_digest='b')).encode())
        def poll(self):
            if clock[0] >= self.due:
                self.returncode = (1 if fault == 'worker-error' and self.mode == 'baseline'
                                   and self.case['identity'] == cases[0]['identity'] else 0)
            return self.returncode
        def wait(self, timeout=None):
            if self.returncode is None:
                self.returncode = -9
            settled.append([self.name, self.mode, clock[0], self.returncode])
            children.pop(self.pid, None)
            return self.returncode
    with tempfile.TemporaryDirectory(prefix='v363-') as temporary:
        root = Path(temporary)
        class Meter:
            peak = 1024
            def __init__(self, name):
                self.path = root / ('cgroup-' + name)
                self.path.mkdir()
            def open_join(self):
                return os.open('/dev/null', os.O_WRONLY)
            def sample(self, *args):
                return dict(cpu_seconds=1, peak_anon_bytes=1024)
            def close(self):
                assert (self.path / 'cgroup.kill').read_text() == '1'
                closed.append(str(self.path))
        client = types.SimpleNamespace(acquire=lambda *a: True, release=lambda *a: None, close=lambda: None)
        admission = gate.Admission(client, dict(cpu=32, memory=32*2**30, manager=16),
                                   dict(cpu=4, memory=4*2**30), Meter)
        real_load = gate.load
        owner = real_load(gate.ROOT / 'scripts/mutation_ownership.py')
        def load(path):
            if Path(path).name == 'case_reuse.py':
                return types.SimpleNamespace(Session=Session)
            if Path(path).name == 'mutation_ownership.py':
                return types.SimpleNamespace(cleanup=lambda *a: {}, remove_tree=owner.remove_tree)
            if Path(path).name == 'mutation_observer.py':
                return types.SimpleNamespace(wait_empty=lambda p: reaped.append(str(p)))
            return real_load(path)
        def advance(*args):
            future = [c.due for c in children.values() if c.due > clock[0]]
            assert future, 'waiting without a worker completion event'
            clock[0] = min(future)
        patches = dict(Workers=Workers, inventory=lambda *a: cases,
            read_inputs=lambda *a: {'scripts/check_gate_mutations.py': (0o644, b'fixture')},
            git=lambda *a: 'head', snapshot=lambda *a: None, inputs_unchanged=lambda *a: True,
            load=load, CASE_TIMES=root / 'hints',
            case_deadlines=lambda keys: {k: 240 for k in keys},
            order_history=lambda *a: history or {}, record_case_times=lambda *a, **kw: None,
            record_case_resources=lambda *a, **kw: None)
        with contextlib.ExitStack() as stack:
            for key, value in patches.items():
                stack.enter_context(patch.object(gate, key, value))
            stack.enter_context(patch.dict(os.environ, {'VELDO_GATE_COLLECT_ALL': collect}))
            stack.enter_context(patch.object(gate.SuiteResources, 'from_root', lambda *a:
                gate.SuiteResources(dict(suites=[dict(file=s) for s in sorted({c['suite'] for c in cases})]))))
            stack.enter_context(patch.object(gate.Workers, 'launcher_fds', lambda *a: ()))
            stack.enter_context(patch.object(gate.Workers, 'watch_worker', lambda *a: None))
            stack.enter_context(patch.object(gate.Workers, 'wait_for_progress', advance))
            stack.enter_context(patch.object(gate.subprocess, 'Popen', Child))
            stack.enter_context(patch.object(gate.os, 'killpg', lambda *a: None))
            stack.enter_context(patch.object(gate.time, 'monotonic', lambda: clock[0]))
            receipt = gate.run_stage(root, root / '.git', parallel=parallel, admission=admission,
                                     log_dir=root / 'logs')
        assert not children and not admission.held and not holders[0].active
        assert len(closed) == len(reaped) == receipt['worker_invocations']
        assert all(Path(o['output_directory']).parent.joinpath(
            Path(o['output_directory']).name + '-stdout').exists() for o in receipt['worker_outcomes'])
        receipt['fixture_invalidated'] = invalidated
        return receipt, launched, settled


def checks(gate, expect):
    def row(name, predicate):
        expect('VELDO-0363 early/' + name, predicate)
    r, launches, finishes = drive(gate)
    first = next((t for _, m, t in launches if m == 'mutant'), None)
    row('release', r['status'] == 'passed' and r['rejected'] == 4 and first == 1
        and first < max(t for _, m, t, _ in finishes if m != 'mutant'))
    safe = True
    cases = cases_for(gate)
    for name, mode, at in launches:
        if mode == 'mutant':
            group = gate.control_group(next(c for c in cases if c['identity'] == name))
            safe &= all(any(n == group + ':' + m and t <= at and rc == 0
                            for n, _, t, rc in finishes) for m in ('baseline', 'noop'))
    row('dependencies', safe)
    slow_noop = {gate.control_group(cases[0]) + ':noop': 5}
    r, launches, _ = drive(gate, durations=slow_noop)
    row('both-controls', r['status'] == 'passed'
        and min((t for n, m, t in launches if n == 'g0-c0' and m == 'mutant'), default=-1) == 5)
    r, launches, finishes = drive(gate, fault='stale', durations={'g0-c0:noop': 5})
    own_launches = [m for n, m, _ in launches if n.startswith('g0-c0')]
    row('stale-rerun', r['status'] == 'passed' and r['rejected'] == 4
        and own_launches == ['baseline', 'noop', 'mutant', 'baseline', 'noop', 'mutant']
        and max(t for n, _, t in launches if n == 'g0-c0')
            >= max(t for n, _, t, _ in finishes if n == 'g0-c0:noop'))
    for fault in ('missing-verdict', 'missing-dependency'):
        r, _, _ = drive(gate, fault=fault)
        row(fault, r['status'] == 'failed' and r['error'] == 'incomplete_inventory'
            and r['rejected'] == 3 and len(r['case_receipts']) == 4)
    r, launches, _ = drive(gate, fault='audit-mismatch')
    entries = r['audit']['entries']
    row('audit-control', r['status'] == 'failed' and r['error'] == 'control_failed'
        and len(entries) == 1 and entries[0].get('incomplete') is True and not entries[0]['matched']
        and 'noop' in entries[0]['differences'] and 'mutant' not in entries[0]['fresh_record']
        and r['fixture_invalidated'] == ['fixture-key'] and r['stale_count'] == 1
        and not any(n == 'g0-c0' and m == 'mutant' for n, m, t in launches))
    for fault in ('baseline', 'noop', 'mismatch', 'watchdog', 'malformed', 'survivor', 'missing-target'):
        r, launches, _ = drive(gate, fault=fault, durations=slow_noop if fault == 'baseline' else None)
        expected = 'mutation_survived' if fault == 'survivor' else (
                   'driver_error' if fault == 'malformed' else (
                   'missing_target' if fault == 'missing-target' else 'control_failed'))
        row('abort-' + fault, r['status'] == 'failed' and r['error'] == expected
            and r['elapsed'] == (2 if fault == 'survivor' else 1)
            and len(r['case_receipts']) == 4 and r['invalid_results']
            and any(o.get('error') == 'worker_cancelled' for o in r['worker_outcomes'])
            and not any(n == 'g2-c0' for n, m, t in launches if m == 'mutant')
            and (fault == 'survivor' or not any(m == 'mutant' for n, m, t in launches)))
        r, launches, _ = drive(gate, fault=fault, collect='1')
        row('collect-' + fault, r['status'] == 'failed' and r['error'] == expected
            and r['rejected'] == (3 if fault == 'survivor' else 2)
            and len(r['case_receipts']) == 4
            and (fault == 'survivor' or not any(n.startswith('g0-') and m == 'mutant' for n, m, t in launches)))
    r, _, _ = drive(gate, fault='survivor', collect='true')
    row('explicit-collect', r['collect_all'] is False and r['rejected'] < 3)
    history = {'g2-c0': dict(failed=True, seconds=1), 'g1-c0': dict(failed=False, seconds=900),
               'g0-c0': dict(failed=False, seconds=10)}
    r, launches, _ = drive(gate, history=history, parallel=1)
    mutants = [n for n, m, _ in launches if m == 'mutant']
    row('ordering', r['status'] == 'passed' and mutants[:2] == ['g2-c0', 'g1-c0']
        and launches[0][0].startswith('g2.py:'))
    with tempfile.TemporaryDirectory(prefix='v363-history-') as temporary:
        path = Path(temporary) / 'hints.json'
        row('missing-history', gate.order_history(path) == {})
        corrupt = []
        for bad in ('[]', 'null', '{', '{"x": {"failed": 1, "seconds": 2}}',
                    '{"x": {"failed": true, "seconds": -1}}',
                    '{"x": {"failed": true, "seconds": NaN}}', '{"x": null}',
                    '{"x": {"failed": true, "seconds": Infinity}}',
                    '{"x": {"failed": true, "seconds": "1"}}',
                    '{"x": {"failed": true, "seconds": true}}'):
            path.write_text(bad)
            corrupt.append(gate.order_history(path) == {})
        path.write_text(json.dumps({'valid': dict(failed=False, seconds=1), 'invalid': None}))
        corrupt.append(gate.order_history(path) == {'valid': dict(failed=False, seconds=1)})
        row('corrupt-history', all(corrupt))
        path.unlink()
        r, _, _ = drive(gate, fault='survivor')
        gate.record_order_history(r, cases, gate.control_group, path=path)
        row('authority-only', not path.exists())
        gate.record_order_history(r, cases, gate.control_group, authority=True, path=path)
        hints = gate.order_history(path)
        row('red-history', hints['g0-c0']['failed'] and hints['g0-c0']['seconds'] > 0
            and not hints['g2-c0']['failed'])
        path.unlink()
        r, _, _ = drive(gate, fault='worker-error')
        gate.record_order_history(r, cases, gate.control_group, authority=True, path=path)
        row('worker-error-history', gate.order_history(path)['g0-c0']['failed']
            and not gate.order_history(path)['g1-c0']['failed'])
        r, _, _ = drive(gate)
        gate.record_order_history(r, cases, gate.control_group, authority=True, path=path)
        row('clear-failure', not gate.order_history(path)['g0-c0']['failed'])
        path.write_text(json.dumps({'g2-c0': dict(failed=True, seconds=100)}))
        r, _, _ = drive(gate, fault='baseline')
        gate.record_order_history(r, cases, gate.control_group, authority=True, path=path)
        row('pending-history', gate.order_history(path)['g2-c0'] == dict(failed=True, seconds=100))
        try:
            gate.record_order_history(r, cases, None, authority=True, path=path)
            setup_ok = gate.order_history(path)['g2-c0']['failed']
        except TypeError:
            setup_ok = False
        row('setup-history', setup_ok)
        try:
            gate.record_order_history(r, cases, gate.control_group, authority=True, path=path / 'bad')
            unavailable = 'order_history_error' in r
        except OSError:
            unavailable = False
        row('history-unavailable', unavailable)
