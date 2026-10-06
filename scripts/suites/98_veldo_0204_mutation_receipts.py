"""VELDO-0204 coordinator regressions with controlled children, never a mutation drive."""


def _v204_mutation_receipts():
    import contextlib
    import json
    import os
    from pathlib import Path
    import tempfile
    import types
    from unittest.mock import patch

    source = (ROOT / 'scripts/check_gate_mutations.py').read_text()
    teeth = types.ModuleType('v204_teeth')
    teeth.__file__ = str(ROOT / 'scripts/check_teeth_mutations.py')
    exec(compile(Path(teeth.__file__).read_text(), teeth.__file__, 'exec'), teeth.__dict__)

    def module(text=source):
        obj = types.ModuleType('v204_coordinator')
        obj.__file__ = str(ROOT / 'scripts/check_gate_mutations.py')
        exec(compile(text, obj.__file__, 'exec'), obj.__dict__)
        return obj

    def exercise(gate, fault=None, concurrent=False, entry='gate', edit=None):
        # Only registry/input seams and the OS process boundary are replaced. The
        # production admission, completion, validation and receipt paths all run.
        cases = [dict(identity=name, name=name, finding=204, driver=gate.DRIVERS[0],
                      suite='controlled.py', module='controlled.py', rows=['target'],
                      old='before', new='after')
                 for name in (('first', 'second', 'third') if concurrent else ('first', 'second'))]
        cases[0].update(edit or {})
        pool = gate.SuiteResources({'resource_capacities': {'manager': 3 if concurrent else 1}, 'suites': [
            {'file': 'controlled.py', 'resources': {'manager': 1}}]})
        clock, children, cleaned, launched, handles = [1.0], {}, [], {}, []
        cleaned_while_held = []
        workers = []
        original_workers = gate.Workers
        class RecordingWorkers(original_workers):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                workers.append(self)
        class Child:
            def __init__(self, argv, **kwargs):
                self.job = json.loads(Path(argv[-1]).read_text())
                self.name = self.job['case']['identity']
                self.mode = self.job['mode']
                self.home = Path(argv[-1]).parent
                self.bad = self.name == 'second' and self.mode == 'mutant'
                handles.extend([kwargs['stdout'], kwargs['stderr']])
                if self.bad and fault == 'spawn':
                    raise OSError('planted exec refusal')
                # Slow launch and queued admission must not consume worker time.
                clock[0] += .01 if concurrent else 130
                self.pid = 1000000 + len(launched)
                self.returncode = None
                self.polls = 0
                launched[self.pid] = clock[0]
                children[self.pid] = self
                ok = self.mode != 'mutant'
                observation = dict(observations=[['TEST target', ok]], count=1,
                                   row_names=['TEST target'], failed_rows=[] if ok else ['TEST target'])
                output = dict(observation=observation, replacement_count=1,
                              old_digest='a', new_digest='b' if not ok else 'a')
                body = json.dumps(output).encode()
                if self.bad and fault == 'empty':
                    body = b''
                if self.bad and fault == 'nonobject':
                    body = b'[]'
                kwargs['stdout'].write(body)
                if self.bad and fault == 'exit':
                    kwargs['stderr'].write(b'planted child error')
            def poll(self):
                self.polls += 1
                if concurrent and self.name == 'third' and fault != 'completed-sibling':
                    return None
                if concurrent and self.name == 'third' and fault == 'completed-sibling':
                    self.returncode = 0
                if self.bad and fault in ('deadline', 'completed-sibling'):
                    clock[0] += 121
                    return None
                if self.polls > 1:
                    self.returncode = 7 if self.bad and fault == 'exit' else 0
                return self.returncode
            def wait(self, timeout=None):
                if self.returncode is None:
                    self.returncode = -9
                children.pop(self.pid, None)
                return self.returncode
        def cleanup(home, ledger):
            cleaned.append(str(home))
            cleaned_while_held.append(bool(pool.held))
            if fault == 'cleanup' and len(cleaned) == 4:
                raise RuntimeError('planted unit still active')
            return dict(units=[], directories=0)
        real_load = gate.load
        with tempfile.TemporaryDirectory(prefix='v204-receipts-') as directory:
            root = Path(directory)
            def snapshot(_root, _common, frozen, *_args):
                (frozen / '.veldo').mkdir(parents=True)
                (frozen / '.veldo/controlled.py').write_text('before\n')
            with contextlib.ExitStack() as stack:
                overrides = {
                    'Workers': RecordingWorkers,
                    'inventory': lambda root, expected_common: cases + ([dict(cases[0], identity='other-driver',
                        driver=gate.DRIVERS[1])] if entry == 'teeth' else []),
                    'read_inputs': lambda root, expected_common: {'scripts/check_gate_mutations.py': (0o644, source.encode())},
                    'git': lambda *a: 'head', 'snapshot': snapshot,
                    'inputs_unchanged': lambda *a: True, 'budget_for': lambda *a: 10000,
                    # The real reuse session runs: these controlled cases declare no inputs,
                    # so every one is a fresh miss and no cache is opened.
                    'load': lambda path: (real_load(path) if Path(path).name == 'case_reuse.py' else
                                          types.SimpleNamespace(cleanup=cleanup, mutate=teeth.mutate)),
                }
                for key, value in overrides.items():
                    stack.enter_context(patch.object(gate, key, value))
                stack.enter_context(patch.object(gate.SuiteResources, 'from_root', lambda *a: pool))
                stack.enter_context(patch.object(gate.subprocess, 'Popen', Child))
                stack.enter_context(patch.object(gate.os, 'killpg', lambda *a: None))
                stack.enter_context(patch.object(gate.time, 'monotonic', lambda: clock[0]))
                stack.enter_context(patch.object(gate.time, 'sleep', lambda _: clock.__setitem__(0, clock[0] + .1)))
                stack.enter_context(patch.object(gate.signal, 'setitimer', lambda *a: None))
                stack.enter_context(patch.object(teeth, '_coordinator', lambda: gate))
                # Every Git query is a double here; the trusted directory is still named.
                receipt = (teeth.run_stage(root, root / '.git', jobs=3, diff_dir=root / 'diffs')
                           if entry == 'teeth' else gate.run_stage(root, root / '.git'))
                if edit is not None:
                    # Nothing reaches the filesystem beside or above the diff directory.
                    written = sorted(str(p.relative_to(root)) for p in root.rglob('*.diff'))
                    receipt = dict(receipt, written=written)
                elif entry == 'teeth':
                    assert (root / 'diffs/first.diff').read_text() == (
                        '--- a/.veldo/controlled.py\n+++ b/.veldo/controlled.py\n'
                        '@@ -1 +1 @@\n-before\n+after\n')
        return receipt, pool, cleaned_while_held, children, handles, workers

    def check(gate, fault=None, entry='gate'):
        r, pool, held, children, handles, workers = exercise(gate, fault, entry=entry)
        assert not children and all(h.closed for h in handles)
        assert r['registered'] == 2 and r['surviving_workers'] == 0 and r['peak_workers'] == 1
        assert all(held) and held
        assert r['drivers'][gate.DRIVERS[0]]['worker_seconds'] > 0
        assert len(r['worker_outcomes']) == 4
        assert r['worker_invocations'] == (3 if fault == 'spawn' else 4)
        if fault is None:
            assert r['status'] == 'passed' and r['executed'] == r['rejected'] == 2
            assert not r['invalid_results'] and len(r['results']) == 2
        else:
            assert r['status'] == 'failed' and r['rejected'] == 1 and len(r['results']) == 1
            assert r['executed'] == (1 if fault == 'spawn' else 2)
            assert len(r['invalid_results']) == 1
            failure = r['invalid_results'][0]
            assert failure['name'] == 'second' and failure['mode'] == 'mutant'
            assert failure['returncode'] == ({'spawn': None, 'deadline': -9, 'exit': 7}.get(fault, 0))
            if fault == 'exit':
                assert 'planted child error' in failure['stderr_tail']
            if fault == 'empty':
                assert failure['stdout_bytes'] == 0 and 'empty' in failure['detail']
        assert bool(pool.held) == (fault == 'cleanup')
        assert bool(pool.used['manager']) == (fault == 'cleanup')
        return True

    for entry in ('gate', 'teeth'):
        for fault in (None, 'empty', 'nonobject', 'exit', 'spawn', 'deadline', 'cleanup'):
            expect('VELDO-0204 stall/' + entry + '-receipt-' + str(fault)
                   + ': partial results and every failure retained; cleanup precedes release '
                   'and launch precedes the deadline', check(module(), fault, entry))

    def siblings(gate, entry='gate'):
        r, pool, held, children, handles, workers = exercise(gate, 'exit', concurrent=True, entry=entry)
        assert r['status'] == 'failed' and r['executed'] == 3 and r['rejected'] == 1
        assert r['peak_workers'] == 3 and r['worker_invocations'] == 5
        assert len(r['worker_outcomes']) == 5 and len(r['invalid_results']) == 2
        assert {o['error'] for o in r['invalid_results']} == {'driver_error', 'worker_cancelled'}
        assert not children and not pool.held and all(h.closed for h in handles) and all(held)
        return True
    # The developer diff directory joins registry-supplied parts: each one passes safe_name first.
    for field, value in (('name', '../escaped'), ('dir', '../outside'), ('module', '../controlled.py')):
        receipt = exercise(module(), entry='teeth', edit={field: value})[0]
        expect('VELDO-0208 diff-dir/' + field + '-traversal-refused: ' + str(receipt.get('detail')),
               receipt['status'] == 'failed' and receipt['error'] == 'incomplete_inventory'
               and 'invalid' in receipt['detail'] and receipt['written'] == [])
    for entry in ('gate', 'teeth'):
        expect('VELDO-0204 stall/' + entry + '-siblings: a failed worker retains completed work and '
               'accounts for every cancelled sibling after reaping it', siblings(module(), entry))
    old = 'for name in list(self.active):'
    assert source.count(old) == 1
    try:
        siblings(module(source.replace(old, 'for name in []:')))
    except AssertionError:
        detected = True
    else:
        detected = False
    expect('VELDO-0204 stall/planted-unreaped-sibling: sibling cleanup cannot be omitted', detected)

    def completed_siblings(gate, entry):
        r, pool, held, children, handles, workers = exercise(
            gate, 'completed-sibling', concurrent=True, entry=entry)
        assert r['status'] == 'failed' and r['executed'] == 3 and r['rejected'] == 2
        assert len(r['results']) == 2 and len(r['invalid_results']) == 1
        assert r['invalid_results'][0]['error'] == 'mutation_budget_exceeded'
        assert 'worker deadline' in r['invalid_results'][0]['detail']
        assert not children and not pool.held and all(h.closed for h in handles)
        return True
    for entry in ('gate', 'teeth'):
        expect('VELDO-0204 stall/' + entry + '-completed-siblings: a timeout retains successful '
               'siblings even when they follow the failed child in polling order',
               completed_siblings(module(), entry))
        old = "if proc.poll() is None else None)"
        assert source.count(old) == 1
        try:
            completed_siblings(module(source.replace(old, 'if True else None)')), entry)
        except AssertionError:
            detected = True
        else:
            detected = False
        expect('VELDO-0204 stall/' + entry + '-planted-discarded-sibling: cleanup cannot classify '
               'an already completed child as cancelled', detected)

    # Each falsifier rewrites an in-memory module only. No driver is invoked and
    # no mutation registry, suite source or working tree input is changed.
    defects = [
        ('lost-partial', 'on_result(name, results[name])', 'None', 'empty'),
        ('lost-failure', "receipt['invalid_results'].extend(failed_workers)", 'pass', 'empty'),
        ('zero-seconds', "sum(o['elapsed'] for o in workers.outcomes if o['driver'] == driver)", '0.0', None),
        ('empty-not-executed', "o['mode'] == 'mutant' and o['returncode'] is not None", 'False', 'empty'),
        ('release-before-cleanup', "record['cleanup'] = ownership.cleanup(self.homes[name], self.ledgers[name])",
         "self.resources.release(name)\n            record['cleanup'] = ownership.cleanup(self.homes[name], self.ledgers[name])", None),
        ('queued-deadline', 'self.active[name] = (proc, out, err, time.monotonic())',
         'self.active[name] = (proc, out, err, 1.0)', None),
        ('release-failed-cleanup', "if record.get('error') != 'worker_cleanup_error':", 'if True:', 'cleanup'),
    ]
    for name, old, new, fault in defects:
        assert source.count(old) == 1, name
        for entry in ('gate', 'teeth'):
            detected = False
            try:
                check(module(source.replace(old, new)), fault, entry)
            except (AssertionError, KeyError):
                detected = True
            expect('VELDO-0204 stall/' + entry + '-planted-' + name
                   + ': the regression rejects the broken coordinator', detected)

    owner_source = (ROOT / 'scripts/mutation_ownership.py').read_text()
    def ownership_check(text):
        owner = types.ModuleType('v204_ownership')
        exec(compile(text, '<ownership>', 'exec'), owner.__dict__)
        with tempfile.TemporaryDirectory(prefix='v204-ownership-') as directory:
            # The coordinator's directory holds the ledger; the worker's home is beneath it.
            home = Path(directory) / 'home'
            home.mkdir()
            ledger = Path(directory) / 'ownership.jsonl'
            external = home / 'external'
            external.mkdir()
            units = Path(directory) / 'units'
            units.mkdir()
            service = units / 'veldo-authority-1234.service'
            service.write_text('fixture')
            unrelated = home / 'untouched'
            unrelated.mkdir()
            with contextlib.ExitStack() as stack:
                hooks = []
                stack.enter_context(patch.object(owner.sys, 'addaudithook', hooks.append))
                tracker = owner.Tracker(home, os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)).install()
                try:
                    hooks[0]('tempfile.mkdtemp', (str(external),))
                    json.dumps({'profile': {'kind': 'linux-systemd', 'slice': 'veldo1234.slice',
                                            'lock': str(external / 'lock')}})
                    json.dumps({'kind': 'linux-systemd', 'slice': 'veldo9999.slice',
                                'lock': '/not-owned/lock'})
                    hooks[0]('open', ('/run/user/%d/systemd/user/veldo-authority-1234.service' % os.getuid(),
                                      'w', os.O_CREAT | os.O_WRONLY))
                finally:
                    tracker.close()
            entries = [json.loads(line) for line in ledger.read_text().splitlines()]
            assert ['slice', 'veldo1234.slice'] in entries
            assert ['slice', 'veldo9999.slice'] not in entries
            assert any(k == 'service' for k, v in entries)
            # Redirect the recorded service file into this test's own tree. Never
            # create or stop a real manager unit during these controlled checks.
            ledger.write_text(''.join(json.dumps([k, str(service) if k == 'service' else v]) + '\n'
                                      for k, v in entries))
            calls = []
            def run(argv, **kwargs):
                calls.append(argv)
                return types.SimpleNamespace(returncode=0, stderr='',
                    stdout='ActiveState=inactive\nActiveState=inactive\n')
            try:
                owner.cleanup(home, ledger, runtime=units, run=lambda *a, **kw: types.SimpleNamespace(
                    returncode=1, stderr='manager unreachable', stdout='ActiveState=inactive\n'))
            except RuntimeError:
                pass
            else:
                raise AssertionError('partial manager response accepted')
            assert service.exists() and external.exists()
            result = owner.cleanup(home, ledger, run=run, runtime=units)
            assert result['units'] == ['veldo-authority-1234.service', 'veldo1234.slice']
            assert not service.exists() and not external.exists() and unrelated.exists()
            assert [c[2] for c in calls] == ['stop', 'show', 'reset-failed', 'daemon-reload']
            # The ledger survives cleanup for receipts, and reaping is idempotent.
            owner.cleanup(home, ledger, run=run, runtime=units)
        return True
    expect('VELDO-0204 stall/ownership: persist exact resources before use; reap only owned units and '
           'trees, retain them on incomplete manager evidence, and permit repeated cleanup', ownership_check(owner_source))

    def transparent_check(text):
        # The tracker runs inside every json encoding a suite makes in a mutation worker, so it
        # may not change what encodes: a value nested deeper than Python's recursion limit (the
        # C encoder takes it) must still encode, and a profile at the bottom is still recorded.
        owner = types.ModuleType('v204_transparent')
        exec(compile(text, '<ownership>', 'exec'), owner.__dict__)
        with tempfile.TemporaryDirectory(prefix='v204-transparent-') as directory:
            home = Path(directory)
            ledger = home / 'ownership.jsonl'
            deep = {'kind': 'linux-systemd', 'slice': 'veldo5000.slice', 'lock': str(home / 'lock')}
            for _ in range(5000):
                deep = [deep]
            with patch.object(owner.sys, 'addaudithook', lambda hook: None):
                tracker = owner.Tracker(home, os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)).install()
                try:
                    encoded = json.dumps(deep)
                except RecursionError:
                    return False
                finally:
                    tracker.close()
            entries = [json.loads(line) for line in ledger.read_text().splitlines()]
            return encoded == json.dumps(deep) and ['slice', 'veldo5000.slice'] in entries
    expect('VELDO-0204 stall/ownership-transparent: the tracker encodes and observes a value nested '
           '5000 deep, as the plain encoder does, so a suite behaves the same inside a mutation worker',
           transparent_check(owner_source))
    expect('VELDO-0204 stall/ownership-transparent-planted-recursive-walk: the check rejects the '
           'recursive observer that made VELDO-0054 an invalid baseline',
           not transparent_check(owner_source.replace(
               'visited, stack = set(), [value]',
               'visited, stack = set(), []\n        self._walk(value, set())').replace(
               '    def install(self):',
               '    def _walk(self, value, seen):\n'
               '        if isinstance(value, (list, tuple)):\n'
               '            for child in value:\n'
               '                self._walk(child, seen)\n\n'
               '    def install(self):')))

    # Cross a real process boundary: the audit hook must persist an allocation in the
    # worker's home before SIGKILL, through the inherited coordinator ledger descriptor,
    # without relying on Python finally/atexit.
    import subprocess
    import sys
    import time
    owner = types.ModuleType('v204_real_ownership')
    exec(compile(owner_source, '<ownership>', 'exec'), owner.__dict__)
    with tempfile.TemporaryDirectory(prefix='v204-killed-owner-') as directory:
        home = Path(directory) / 'home'
        home.mkdir()
        ledger = Path(directory) / 'ownership.jsonl'
        program = """
import importlib.util, json, pathlib, sys, tempfile, time
spec = importlib.util.spec_from_file_location('owner', sys.argv[1])
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
home = pathlib.Path(sys.argv[2])
tracker = owner.Tracker(home, int(sys.argv[3])).install()
tree = pathlib.Path(tempfile.mkdtemp(prefix='v204-killed-tree-', dir=home / 'nested'))
(tree / 'file').write_text('owned')
tree.chmod(0o500)
(home / 'ready').write_text(str(tree))
time.sleep(30)
"""
        (home / 'nested').mkdir()
        channel = os.open(ledger, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        with open(home / 'stdout', 'wb') as out, open(home / 'stderr', 'wb') as err:
            child = subprocess.Popen([sys.executable, '-B', '-c', program,
                                      str(ROOT / 'scripts/mutation_ownership.py'), str(home), str(channel)],
                                     stdout=out, stderr=err, pass_fds=(channel,))
            os.close(channel)
            try:
                deadline = time.monotonic() + 5
                while not (home / 'ready').exists() and child.poll() is None and time.monotonic() < deadline:
                    time.sleep(.01)
                assert (home / 'ready').exists(), (home / 'stderr').read_text()
                tree = Path((home / 'ready').read_text())
            finally:
                child.kill()
                child.wait(timeout=5)
                reaped = owner.cleanup(home, ledger)
        expect('VELDO-0204 stall/killed-owner: the coordinator-held audit ledger survives SIGKILL and '
               'reaps a read-only temporary tree in the worker home', child.returncode == -9
               and reaped['directories'] == 1 and not tree.exists())
    for name, old, new in (
        ('slice-unrecorded', "self.record('slice', value['slice'])", 'pass'),
        ('tree-leaked', 'remove_tree(path)', 'None'),
        ('partial-stop-accepted', 'len(states) != len(units)', 'not states'),
    ):
        # Restrict replacement to the call for tree-leaked, not the definition.
        old = '        ' + old if name == 'tree-leaked' else old
        new = '        ' + new if name == 'tree-leaked' else new
        assert owner_source.count(old) == 1, name
        try:
            ownership_check(owner_source.replace(old, new))
        except AssertionError:
            detected = True
        else:
            detected = False
        expect('VELDO-0204 stall/planted-' + name + ': the regression rejects missing ownership', detected)


_v204_mutation_receipts()
