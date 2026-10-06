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

    def module(text=source):
        obj = types.ModuleType('v204_coordinator')
        obj.__file__ = str(ROOT / 'scripts/check_gate_mutations.py')
        exec(compile(text, obj.__file__, 'exec'), obj.__dict__)
        return obj

    def exercise(gate, fault=None):
        # Only registry/input seams and the OS process boundary are replaced. The
        # production admission, completion, validation and receipt paths all run.
        cases = [dict(identity=name, name=name, finding=204, driver=gate.DRIVERS[0],
                      suite='controlled.py', module='controlled.py', rows=['target'])
                 for name in ('first', 'second')]
        pool = gate.SuiteResources({'resource_capacities': {'manager': 1}, 'suites': [
            {'file': 'controlled.py', 'resources': {'manager': 'exclusive'}}]})
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
                clock[0] += 130
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
                if self.bad and fault == 'deadline':
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
        def cleanup(home):
            cleaned.append(str(home))
            cleaned_while_held.append(bool(pool.held))
            if fault == 'cleanup' and len(cleaned) == 4:
                raise RuntimeError('planted unit still active')
            return dict(units=[], directories=0)
        with tempfile.TemporaryDirectory(prefix='v204-receipts-') as directory:
            root = Path(directory)
            with contextlib.ExitStack() as stack:
                overrides = {
                    'Workers': RecordingWorkers, 'inventory': lambda root: cases,
                    'read_inputs': lambda root: {'scripts/check_gate_mutations.py': (0o644, source.encode())},
                    'git': lambda *a: 'head', 'snapshot': lambda *a: None,
                    'inputs_unchanged': lambda *a: True, 'budget_for': lambda *a: 10000,
                    'load': lambda *a: types.SimpleNamespace(cleanup=cleanup),
                }
                for key, value in overrides.items():
                    stack.enter_context(patch.object(gate, key, value))
                stack.enter_context(patch.object(gate.SuiteResources, 'from_root', lambda *a: pool))
                stack.enter_context(patch.object(gate.subprocess, 'Popen', Child))
                stack.enter_context(patch.object(gate.os, 'killpg', lambda *a: None))
                stack.enter_context(patch.object(gate.time, 'monotonic', lambda: clock[0]))
                stack.enter_context(patch.object(gate.time, 'sleep', lambda _: clock.__setitem__(0, clock[0] + .1)))
                stack.enter_context(patch.object(gate.signal, 'setitimer', lambda *a: None))
                receipt = gate.run_stage(root)
        return receipt, pool, cleaned_while_held, children, handles, workers

    def check(gate, fault=None):
        r, pool, held, children, handles, workers = exercise(gate, fault)
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

    for fault in (None, 'empty', 'nonobject', 'exit', 'spawn', 'deadline', 'cleanup'):
        expect('VELDO-0204 stall/receipt-' + str(fault) + ': partial results and every failure retained; '
               'cleanup precedes release and launch precedes the deadline', check(module(), fault))

    # Each falsifier rewrites an in-memory module only. No driver is invoked and
    # no mutation registry, suite source or working tree input is changed.
    defects = [
        ('lost-partial', 'on_result(name, results[name])', 'None', 'empty'),
        ('lost-failure', "receipt['invalid_results'].extend(failed_workers)", 'pass', 'empty'),
        ('zero-seconds', "sum(o['elapsed'] for o in workers.outcomes if o['driver'] == driver)", '0.0', None),
        ('empty-not-executed', "o['mode'] == 'mutant' and o['returncode'] is not None", 'False', 'empty'),
        ('release-before-cleanup', "record['cleanup'] = ownership.cleanup(self.homes[name])",
         "self.resources.release(name)\n            record['cleanup'] = ownership.cleanup(self.homes[name])", None),
        ('queued-deadline', 'self.active[name] = (proc, out, err, time.monotonic())',
         'self.active[name] = (proc, out, err, 1.0)', None),
        ('release-failed-cleanup', "if record.get('error') != 'worker_cleanup_error':", 'if True:', 'cleanup'),
    ]
    for name, old, new, fault in defects:
        assert source.count(old) == 1, name
        detected = False
        try:
            check(module(source.replace(old, new)), fault)
        except (AssertionError, KeyError):
            detected = True
        expect('VELDO-0204 stall/planted-' + name + ': the regression rejects the broken coordinator', detected)

    owner_source = (ROOT / 'scripts/mutation_ownership.py').read_text()
    def ownership_check(text):
        owner = types.ModuleType('v204_ownership')
        exec(compile(text, '<ownership>', 'exec'), owner.__dict__)
        with tempfile.TemporaryDirectory(prefix='v204-ownership-') as directory:
            home = Path(directory)
            external = home / 'external'
            external.mkdir()
            service = home / 'veldo-authority-1234.service'
            service.write_text('fixture')
            unrelated = home / 'untouched'
            unrelated.mkdir()
            with contextlib.ExitStack() as stack:
                hooks = []
                stack.enter_context(patch.object(owner.sys, 'addaudithook', hooks.append))
                tracker = owner.Tracker(home).install()
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
            entries = [json.loads(line) for line in tracker.path.read_text().splitlines()]
            assert ['slice', 'veldo1234.slice'] in entries
            assert ['slice', 'veldo9999.slice'] not in entries
            assert any(k == 'service' for k, v in entries)
            # Redirect the recorded service file into this test's own tree. Never
            # create or stop a real manager unit during these controlled checks.
            tracker.path.write_text(''.join(json.dumps([k, str(service) if k == 'service' else v]) + '\n'
                                            for k, v in entries))
            calls = []
            def run(argv, **kwargs):
                calls.append(argv)
                return types.SimpleNamespace(returncode=0, stderr='',
                    stdout='ActiveState=inactive\nActiveState=inactive\n')
            try:
                owner.cleanup(home, run=lambda *a, **kw: types.SimpleNamespace(
                    returncode=1, stderr='manager unreachable', stdout='ActiveState=inactive\n'))
            except RuntimeError:
                pass
            else:
                raise AssertionError('partial manager response accepted')
            assert service.exists() and external.exists()
            result = owner.cleanup(home, run=run)
            assert result['units'] == ['veldo-authority-1234.service', 'veldo1234.slice']
            assert not service.exists() and not external.exists() and unrelated.exists()
            assert [c[2] for c in calls] == ['stop', 'show', 'reset-failed', 'daemon-reload']
            # The ledger survives cleanup for receipts, and reaping is idempotent.
            owner.cleanup(home, run=run)
        return True
    expect('VELDO-0204 stall/ownership: persist exact resources before use; reap only owned units and '
           'trees, retain them on incomplete manager evidence, and permit repeated cleanup', ownership_check(owner_source))
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
