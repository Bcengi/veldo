"""VELDO-0215: coordinator deadlines and authority measurements, with scratch stores only.
VELDO-0285: an unmeasured case's baseline is bounded by the ceiling, and its noop and mutant by
WORKER_MULTIPLIER times that baseline as measured in the same stage."""


def _v215_case_deadlines():
    import contextlib
    import importlib.util
    import json
    import os
    import runpy
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import time
    import types
    from unittest.mock import patch

    compiler = runpy.run_path(str(ROOT / 'scripts/suites/support/compiled_sources.py'))
    with tempfile.TemporaryDirectory(prefix='v215-') as temporary, contextlib.ExitStack() as fixture:
        scratch = Path(temporary)
        # Nested coordinator fixtures stay beneath this worker's private scratch root.
        fixture.enter_context(patch.object(tempfile, 'tempdir', str(scratch)))
        fixture.enter_context(compiler['compiled_sources'](ROOT / 'scripts'))
        path = ROOT / "scripts" / "check_gate_mutations.py"
        if path.parent != ROOT / 'scripts':
            fixture.enter_context(compiler['compiled_sources'](path.parent))
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
            expect(('VELDO-0358 ' + name if '/' in name else 'VELDO-0215 case-deadlines/' + name), condition)

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
        jobs = [dict(case=case, budget_seconds=120) for _ in range(32)]
        plain = gate.SuiteResources({'suites': [{'file': 'sample.py'}]})
        budgets = [gate.budget_for(32, 16, [jobs], plain) == 480,
                   gate.budget_for(32, 1, [jobs], plain) == 3960,
                   gate.budget_for(32, 16, [jobs[:16], jobs[16:]], plain) == 600,
                   gate.budget_for(10000, 16, [jobs], plain) == 20000,
                   gate.budget_for(0, 16, [], plain) == 120]
        # Drive the real selector/reservations with completion events. Include exclusive,
        # multi-slot, multi-resource, shortened jobs and capacity overrides.
        for capacity in (1, 2, 4, 16):
            manifest = dict(resource_capacities={'r': 16, 's': 2}, suites=[
                dict(file='unit', resources={'r': 1}),
                dict(file='wide', resources={'r': min(2, capacity), 's': 1}),
                dict(file='exclusive', resources={'r': 'exclusive'}),
                dict(file='plain')])
            sequence = ['unit'] * 20 + ['exclusive', 'plain', 'wide'] * 3 + ['unit'] * 12
            batch = [dict(case=dict(case, suite=suite), budget_seconds=120 + i % 3 * 60)
                     for i, suite in enumerate(sequence)]
            for parallel in (1, 4, 16):
                for shortened in (False, True):
                    pool = gate.SuiteResources(manifest, {'r': capacity})
                    cap = gate.budget_for(2, parallel, [batch], pool)
                    pending, active, clock = list(enumerate(batch)), {}, 0
                    while pending or active:
                        while pending and len(active) < parallel:
                            index = pool.select(pending)
                            if index is None:
                                break
                            name, job = pending.pop(index)
                            pool.acquire(name, job)
                            active[name] = clock + job['budget_seconds'] / (3 if shortened and name % 2 else 1)
                        clock = min(active.values())
                        for name in [n for n, done in active.items() if done == clock]:
                            del active[name]
                            pool.release(name)
                    budgets.append(clock + gate.BUDGET <= cap <= gate.BUDGET + sum(
                        j['budget_seconds'] for j in batch))
        row('combined-budget', all(budgets))

        peaks = scratch / 'peaks'
        now = time.time()
        def record_at(day, seconds):
            with patch.object(gate.time, 'time', lambda: now + day * 86400):
                gate.record_case_times(ROOT, {key: seconds}, peaks)
                return gate.case_deadline(key, peaks)
        maximums = [record_at(0, 160) == 480, record_at(1, 80) == 480,
                    record_at(2, 200) == 600, record_at(3, 90) == 600,
                    record_at(31, 100) == 600, record_at(33, 80) == 300]
        with patch.object(gate.time, 'time', lambda: now + 64 * 86400):
            maximums.append(gate.case_deadline(key, peaks) == 120)
        maximums.append(record_at(64, 70) == 210)
        kept = json.loads((peaks / (key + '.json')).read_text())
        maximums.append(kept['seconds'] == 70 and len(kept['samples']) == 1)
        # Legacy data also expires, even when a new write would refresh its file mtime.
        legacy = peaks / (key + '.json')
        legacy.write_text(json.dumps(dict(authority=str(ROOT), key=key, seconds=300)))
        os.utime(legacy, (now, now))
        maximums.extend([record_at(1, 80) == 900, record_at(31, 90) == 270])
        row('rolling-maximum', all(maximums))

        def exercise(duration=150, fault=None, reuse_hit=False, measure=True, measured=True, parallel=1):
            runroot = scratch / ('run-' + str(len(list(scratch.glob('run-*')))))
            runroot.mkdir()
            times = runroot / 'times'
            # This is the authority's own root for this in-process fixture; its cache is scratch.
            sample(80)
            if not measured:
                (store / (key + '.json')).unlink()
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
                    self.output = kwargs['stderr']
                    kwargs['stdout'].write(json.dumps(dict(observation=obs, replacement_count=1,
                        old_digest='a', new_digest='b' if mode == 'mutant' else 'a')).encode())
                def poll(self):
                    clock[0] += 30
                    if fault != 'hang-' + self.job['mode']:
                        self.output.write(b'SELFTEST PROGRESS fixture\n')
                        self.output.flush()
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
            real_deadlines, real_record = gate.case_deadlines, gate.record_case_times
            with contextlib.ExitStack() as stack:
                overrides = dict(inventory=lambda *a: [case], read_inputs=lambda *a: files,
                    git=lambda *a: 'head', snapshot=lambda *a: None, inputs_unchanged=lambda *a: True,
                    load=loader, case_deadlines=lambda keys: real_deadlines(keys, store),
                    record_case_times=lambda root, samples, authority=False: real_record(
                        root, samples, times, authority=authority), CASE_TIMES=times)
                for name, value in overrides.items():
                    stack.enter_context(patch.object(gate, name, value))
                stack.enter_context(patch.object(gate.Workers, 'launcher_fds', lambda self: ()))
                stack.enter_context(patch.object(gate.SuiteResources, 'from_root', lambda *a: pool))
                stack.enter_context(patch.object(gate.subprocess, 'Popen', Child))
                stack.enter_context(patch.object(gate.os, 'killpg', lambda pid, sig: kills.append(pid)))
                stack.enter_context(patch.object(gate.time, 'monotonic', lambda: clock[0]))
                stack.enter_context(patch.object(gate.Workers, 'watch_worker', lambda *a: None))
                stack.enter_context(patch.object(gate.Workers, 'wait_for_progress', lambda *a: None))
                stack.enter_context(patch.object(gate.signal, 'setitimer', lambda *a: alarms.append(a)))
                receipt = gate.run_stage(runroot, runroot / '.git', parallel=parallel, measure=measure)
            return receipt, children, kills, cleaned, times, alarms

        with patch.object(gate, 'inventory', side_effect=subprocess.TimeoutExpired('inventory', 120)):
            expired = gate.run_stage(scratch, scratch / '.git')
        row('setup-timeout', expired.get('error') == 'hung')

        obs = lambda ok: dict(count=1, observations=[['TEST target', ok]], row_names=['TEST target'],
                              failed_rows=[] if ok else ['TEST target'])
        valid_record = dict(schema=gate.SCHEMA, fixture_version=gate.FIXTURE_VERSION, case=case,
                            baseline=obs(True), noop=obs(True), mutant=obs(False),
                            replacement_count=1, old_digest='a', new_digest='b')
        passed, children, kills, cleaned, times, alarms = exercise()
        row('measured-worker', passed['status'] == 'passed' and len(children) == 3
            and all(o['estimate_seconds'] == 240 and o['hang_seconds'] == gate.PROCESS_HANG_SECONDS
                    for o in passed['worker_outcomes']) and not alarms)
        row('slow-pass', passed['status'] == 'passed' and passed['executed'] == 1
            and all(o['elapsed'] == 150 for o in passed['worker_outcomes']))
        hang_results = [exercise(fault='hang-' + mode) for mode in ('baseline', 'noop', 'mutant')]
        row('hang-timeout', all(r['error'] == ('hung_not_killed' if mode == 'mutant' else 'control_failed')
            and any('hung since' in o.get('detail', '') for o in r['worker_outcomes'])
            and len(ch) == len(cl) and r['surviving_workers'] == 0 and not list(t.glob('*.json'))
            for mode, (r, ch, k, cl, t, _) in zip(('baseline', 'noop', 'mutant'), hang_results)))

        def outcome(receipt, mode):
            return next((o for o in receipt['worker_outcomes'] if o['mode'] == mode), {'elapsed': 0})
        slow, _, _, _, slow_times, slow_alarms = exercise(measured=False)
        base = outcome(slow, 'baseline')
        derived = gate.WORKER_MULTIPLIER * base['elapsed']
        slow_file = slow_times / (key + '.json')
        slow_record = json.loads(slow_file.read_text()) if slow_file.exists() else {}
        row('unmeasured-slow-baseline', slow['status'] == 'passed' and slow.get('unmeasured_cases') == [case['identity']]
            and base['estimate_seconds'] == gate.WORKER_CEILING and base['elapsed'] > gate.WORKER_BUDGET
            and derived == 450 and slow.get('case_estimates') == {case['identity']: derived}
            and outcome(slow, 'noop').get('estimate_seconds') == outcome(slow, 'mutant').get('estimate_seconds') == derived
            and slow_record.get('seconds') == 150 and not slow_alarms)
        settled = gate.Workers(0)
        settled.jobs['g:noop'] = {'budget_seconds': gate.WORKER_CEILING}
        settled.outcomes.append(dict(name='g:noop', elapsed=500.0, estimate_seconds=gate.WORKER_CEILING))
        settled.retarget('g:noop', 450)
        row('unmeasured-mutant-deadline', settled.outcomes[0]['estimate_seconds'] == 450
            and 'error' not in settled.outcomes[0])
        hung, hung_children, hung_kills, _, hung_times, _ = exercise(measured=False, fault='hang-baseline')
        row('unmeasured-hang', hung.get('error') == 'control_failed' and len(hung_children) == 1
            and outcome(hung, 'baseline').get('error') == 'control_failed'
            and outcome(hung, 'baseline')['elapsed'] >= gate.PROCESS_HANG_SECONDS
            and hung_kills and hung['surviving_workers'] == 0 and not list(hung_times.glob('*.json')))
        long_stage = exercise(duration=7500)[0]
        measured_clock = [0]
        measured = gate.Workers(clock=lambda: measured_clock[0])
        measured.jobs['slow'] = {'mode': 'mutant'}
        measured.budgets['slow'] = 2
        measured_clock[0] = 30
        measured.progress['slow'] = (30, 'row completed')
        try:
            measured.check_worker('slow', 0)
            slow_ok = True
        except gate.Refused:
            slow_ok = False
        row('verdict/slow-is-not-red', slow_ok and long_stage['status'] == 'passed'
            and long_stage['elapsed'] > 21600 and long_stage['rejected'] == 1
            and 'mutation_budget_exceeded' not in json.dumps(long_stage))

        bad, _, _, _, bad_times, _ = exercise(fault='false-baseline')
        row('baseline-details', bad['error'] == 'control_failed'
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
        # main() loads gate_legs.py for the leg and (VELDO-0219) gate_schedule.py for its ledger CHANNEL; only
        # the leg is doubled, every other module main loads is the real one.
        real_load = gate.load
        legs_double = types.SimpleNamespace(mutation_leg=lambda: None)
        def cli_stage(root, common, **kwargs):
            calls.append((root, kwargs))
            return dict(status='passed', registered=0, executed=0, reused=0, rejected=0,
                        worker_invocations=0, elapsed=0)
        with patch.object(gate.sys, 'argv', ['check_gate_mutations.py', '--root', str(scratch / 'candidate')]), \
                patch.object(gate, 'run_stage', cli_stage), \
                patch.object(gate, 'common_directory', lambda root: root / '.git'), \
                patch.object(gate, 'load', lambda path: legs_double if Path(path).name == 'gate_legs.py' else real_load(path)), \
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
        # VELDO-0304 supersedes age-based store deletion (owner rule, Telegram 41209).
        # A gone authority is the only removal trigger. Old live and pending files
        # retain their bytes and timestamps, as do foreign names.
        retained = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in prune.iterdir()
                    if p.name != 'a' * 32 + '.json'}
        gate.record_case_times(ROOT, {key: 80}, prune)
        row('store-pruned', {p.name for p in prune.iterdir()} == {key + '.json', *retained}
            and all((prune / name).read_bytes() == content
                    and (prune / name).stat().st_mtime_ns == modified
                    for name, (content, modified) in retained.items()))

        # Real OS child and process-group kill/reap; only elapsed time is supplied.
        # Replace only the launch command; production Workers.run/finish/check_worker execute.
        home = scratch / 'real'
        home.mkdir()
        blocked_script = home / 'blocking_child.py'
        # __index__ runs inside os.read: after readiness, its call frame is already
        # on the stack, even if the scheduler pauses the child before the kernel read.
        blocked_script.write_text('import os\nimport resource\n'
            'resource.setrlimit(resource.RLIMIT_CORE, (0,0))\nr,w=os.pipe()\n'
            'class ReadyFD:\n    def __index__(self):\n'
            '        print("blocking read",flush=True)\n        return r\n'
            'os.read(ReadyFD(),1)\n')
        real_popen, real_load = subprocess.Popen, gate.load
        pool = gate.SuiteResources({'suites': [{'file': 'sample.py'}], 'resource_capacities': {}})
        hang_clock = [0]
        workers = gate.Workers(resources=pool, parallel=1, hang_seconds=3, clock=lambda: hang_clock[0])
        read_progress = workers.read_progress
        def advance_after_ready(name):
            read_progress(name)
            if workers.progress[name][1] == 'blocking read':
                hang_clock[0] += 3
        def launch(argv, **kwargs):
            return real_popen([sys.executable, '-X', 'faulthandler', str(blocked_script)], **kwargs)
        def loader(p):
            if Path(p).name == 'mutation_ownership.py':
                return types.SimpleNamespace(cleanup=lambda *a: {})
            return real_load(p)
        error = None
        with patch.object(gate.subprocess, 'Popen', launch), patch.object(gate, 'load', loader), \
                patch.object(gate.Workers, 'launcher_fds', lambda self: ()), \
                patch.object(workers, 'read_progress', advance_after_ready):
            try:
                workers.run({'hang': dict(case=case, mode='baseline', budget_seconds=.2)}, home, ROOT)
            except gate.Refused as exc:
                error = exc.code
        row('real-hang-reaped', error == 'control_failed' and workers.invocations == 1
            and not workers.active and workers.outcomes[0]['returncode'] == -6
            and workers.outcomes[0]['hang_seconds'] == 3
            and 'Current thread' in workers.outcomes[0].get('stderr_tail', '')
            and 'blocking_child.py", line 9' in workers.outcomes[0].get('stack_dump', ''))

        observer = gate.load(ROOT / "scripts" / "mutation_observer.py")
        clock = [0]
        progress = observer.Progress(3, lambda: clock[0])
        kept = []
        for second in range(1, 11):
            clock[0] = second
            kept.append(not progress.expired())
            progress.touch('line %d' % second)
        clock[0] += 3
        ack_r, ack_w = os.pipe()
        heavy_clock, heavy_lines = [0], []
        def line_seen(line):
            heavy_lines.append(line)
            heavy_clock[0] += 1
            os.write(ack_w, b'R')
        try:
            heavy = observer.run_heavy([sys.executable, '-u', '-c',
                'import os,sys; fd=int(sys.argv[1]); '
                '[(print(i,flush=True),os.read(fd,1)) for i in range(10)]', str(ack_r)],
                cwd=scratch, env=os.environ, pass_fds=(ack_r,), seconds=3,
                clock=lambda: heavy_clock[0], on_line=line_seen)
        except TimeoutError:
            heavy = types.SimpleNamespace(returncode=1)
        finally:
            os.close(ack_r)
            os.close(ack_w)
        # Actual readiness, using a descriptor beyond select's fixed fd_set.
        import fcntl
        low, writer = os.pipe()
        high = fcntl.fcntl(low, fcntl.F_DUPFD_CLOEXEC, 2048)
        try:
            os.write(writer, b'R')
            try:
                high_ready = observer.wait_readable([high], observer.WAIT_HANG_SECONDS) == {high}
            except ValueError:
                high_ready = False
        finally:
            for fd in (low, writer, high):
                os.close(fd)
        row('watchdog/progress-not-total', high_ready and all(kept) and progress.expired()
            and heavy.returncode == 0 and heavy_lines == [str(i).encode() for i in range(10)]
            and heavy_clock[0] == 10
            and long_stage['status'] == 'passed' and long_stage['elapsed'] > 21600
            and error == 'control_failed' and 'Current thread' in workers.outcomes[0].get('stderr_tail', '')
            and 'blocking_child.py", line 9' in workers.outcomes[0].get('stack_dump', ''))

        outcomes = []
        for kind in ('assertion', 'terminal', 'hung', 'not_run', 'control', 'unproven'):
            record = json.loads(json.dumps(valid_record))
            if kind in ('hung', 'not_run'):
                record['mutant']['observations'][0][1] = kind
                record['mutant']['failed_rows'] = []
            if kind == 'terminal':
                record['mutant']['failure_kinds'] = {'TEST target': 'terminal'}
            if kind == 'control':
                record['baseline']['observations'][0][1] = 'hung'
            record['mutant']['opened_files'] = ['proof/fixture.py']
            baseline_path = scratch / ('baseline-' + kind + '.json')
            baseline_path.write_text(json.dumps({'entries':
                [{'file': 'proof/fixture.py', 'rule': 'R1', 'text': 'legacy_pause()',
                  'function': 'fixture', 'count': 1, 'class': 'S1'}] if kind == 'unproven' else []}))
            try:
                answer = gate.validate_result(record, case, baseline=json.loads(baseline_path.read_text()))
                outcomes.append(('rejected', answer['kill_by'], answer['kills'][0]['row']))
            except gate.Refused as error:
                outcomes.append(error.code)
        row('verdict/kill-by-evidence', outcomes == [
            ('rejected', 'assertion', 'TEST target'), ('rejected', 'terminal', 'TEST target'),
            'hung_not_killed', 'hung_not_killed', 'control_failed',
            ('rejected', 'unproven', 'TEST target')])

        host = gate.load(ROOT / "scripts" / "gate_host.py")
        lock = scratch / 'host.lock'
        lock.touch()
        stat = lock.stat()
        identity = '%02x:%02x:%d' % (os.major(stat.st_dev), os.minor(stat.st_dev), stat.st_ino)
        procroot = scratch / 'proc'
        fdinfo = procroot / '42/fdinfo'
        fdinfo.mkdir(parents=True)
        entry = '1: FLOCK ADVISORY WRITE 42 %s 0 EOF' % identity
        (fdinfo / '3').write_text('lock: ' + entry + '\n')
        (fdinfo / '4').write_text('lock: ' + entry + '\n')
        holders = []
        for table in (entry + '\n' + entry + '\n', ''):
            (procroot / 'locks').write_text(table)
            holders.append(host.holders(lock, procroot))
        row('host/holders-from-descriptor', holders == [[42], [42]])

        timers = gate.load(ROOT / "engine/.veldo" / "timers.py")
        empty = timers.report() == []
        timers.register('worker', 2, 'fixture_worker', 'deadline')
        timers.register('stop', 5, 'fixture_stop', 'contract')
        timers.set_profile('stop')
        timers.register('late', 7, 'fixture_late', 'deadline')
        effective = {r['name']: r['value'] for r in timers.report()}
        timers.set_profile()
        all_hang = all(r['value'] == 600 for r in timers.report())
        timers.reset_profile()
        row('timers/table-profile', empty and effective == {'worker': 600, 'stop': 5, 'late': 600}
            and all_hang and {r['name']: r['value'] for r in timers.report()} == {'worker': 2, 'stop': 5, 'late': 7})


_v215_case_deadlines()
