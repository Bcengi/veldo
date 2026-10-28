"""VELDO-0219: real coordinator and ledger, controlled time and cgroup counters.

Scratch stores only. Native kernel qualification is a separate ticket check;
this file also runs inside mutation confinement without the user manager.
"""


def _v219_checks():
    import contextlib
    import copy
    import importlib.util
    import io
    import json
    import math
    import os
    from pathlib import Path
    import tempfile
    import time
    import types
    from unittest.mock import patch

    def load(path):
        spec = importlib.util.spec_from_file_location('v219_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    source = ROOT / "scripts" / "check_gate_mutations.py"
    gate = load(source)
    gate.ROOT = ROOT
    scheduler = load(ROOT / 'scripts/gate_schedule.py')
    ownership = load(ROOT / "scripts" / "mutation_ownership.py")
    bootstrap = load(ROOT / 'scripts/reuse_worker.py')

    def row(name, condition):
        expect('VELDO-0219 admission/' + name, condition)

    case = dict(identity='fixture:cpu', name='cpu', driver=gate.DRIVERS[0],
                suite='cpu.py', module='cpu.py', rows=['target'], old='old', new='new', finding=219)
    manifest = dict(resource_capacities={'systemd_user_manager': 16, 'new_project_fixture': 2},
                    suites=[dict(file='cpu.py'), dict(file='memory.py'),
                            dict(file='manager.py', resources={'systemd_user_manager': 1}),
                            dict(file='exclusive.py', resources={'systemd_user_manager': 'exclusive'}),
                            dict(file='project.py', resources={'new_project_fixture': 1})])
    with tempfile.TemporaryDirectory(prefix='v219-') as temporary:
        top = Path(temporary)
        store = top / 'store'
        now = time.time()
        key = '1' * 32
        runs = []
        def outcome(name, mode, elapsed, cpu, memory):
            return dict(name=name, mode=mode, elapsed=elapsed,
                        measurement=dict(cpu_seconds=cpu, peak_anon_bytes=memory))
        def record(key, c, seconds, cpu, memory, age=0):
            group = gate.control_group(c)
            outcomes = [outcome(c['identity'], 'mutant', seconds, cpu, memory),
                        outcome(group + ':baseline', 'baseline', seconds, cpu, memory),
                        outcome(group + ':noop', 'noop', seconds, cpu, memory)]
            with patch.object(gate.time, 'time', lambda: now + age):
                gate.record_case_times(ROOT, {key: seconds}, store)
                gate.record_case_resources([c], {c['identity']: key}, outcomes, gate.control_group, store)
            return outcomes

        record(key, case, 10, 8, 64 * 2**20)
        record(key, case, 20, 8, 96 * 2**20)
        claim = gate.CaseClaims(store).claim(case, key)
        item = json.loads((store / (key + '.json')).read_text())
        measured = [claim['cpu'] == .8, claim['memory'] == 96 * 2**20,
                    len(item['resource_runs']) == 6, gate.case_deadline(key, store) == 120]
        bad = record('2' * 32, dict(case, identity='failure'), 10, 8, 1024)
        before = (store / ('2' * 32 + '.json')).read_bytes()
        bad[0]['error'] = 'invalid_baseline'
        gate.record_case_resources([dict(case, identity='failure')], {'failure': '2' * 32}, bad,
                                   gate.control_group, store)
        measured.append((store / ('2' * 32 + '.json')).read_bytes() == before)
        with patch.object(gate, 'CASE_TIMES', store):
            measured.append(gate.record_case_resources([case], {case['identity']: key}, [],
                                                       gate.control_group, store) is False)
        with patch.object(gate.time, 'time', lambda: now + 31 * 86400):
            measured.append(gate.CaseClaims(store).claim(case, key)['source'] == 'default')
        row('measured-per-case', all(measured))

        # Same on-disk counters as cgroup v2. A nested unit is counted once and
        # a separate unit contributes its CPU and anonymous memory before removal.
        cg = top / 'cgroups'
        (cg / 'scope').mkdir(parents=True)
        meter = ownership.WorkerMeter('/scope', 'fixture', cg)
        def counters(path, cpu, anon):
            path.mkdir(parents=True, exist_ok=True)
            (path / 'cpu.stat').write_text('usage_usec %d\n' % (cpu * 1e6))
            (path / 'memory.stat').write_text('anon %d\nfile 999999999\n' % anon)
        counters(meter.path, 8, 64 * 2**20)
        external = cg / 'other/veldo-authority-ab.service'
        counters(external, 2, 32 * 2**20)
        meter.paths['unit'] = external
        meter.paths['nested'] = meter.path / 'nested'
        counters(meter.path / 'nested', 8, 64 * 2**20)
        value = meter.sample()
        row('cgroup-counters', value['cpu_seconds'] == 10 and value['peak_anon_bytes'] == 96 * 2**20
            and len(value['cgroups']) == 2)
        marker = top / 'join'
        fd = os.open(marker, os.O_WRONLY | os.O_CREAT, 0o600)
        with patch.dict(os.environ, VELDO_MUTATION_CGROUP_FD=str(fd)):
            bootstrap.join_worker_cgroup()
            joined = 'VELDO_MUTATION_CGROUP_FD' not in os.environ
        try:
            os.fstat(fd)
            closed = False
        except OSError:
            closed = True
        row('bootstrap-joins-before-import', joined and closed and marker.read_text() == str(os.getpid()))

        record('3' * 32, dict(case, identity='memory1', suite='memory.py'), 10, 20, 2**29)
        record('4' * 32, dict(case, identity='memory2', suite='memory.py'), 10, 40, 2**31)
        prior = gate.CaseClaims(store).claim(case, 'changed-key')
        suite = gate.CaseClaims(store).claim(dict(case, identity='unseen'), 'new')
        glob = gate.CaseClaims(store).claim(dict(case, identity='unseen', suite='unseen.py'), 'new')
        empty = gate.CaseClaims(top / 'empty').claim(case, 'new')
        row('fallback-order', prior['source'] == 'previous_key' and prior['keys'] == [key]
            and suite['source'] == 'suite_median' and suite['cpu'] == .8
            and glob['source'] == 'all_median' and glob['cpu'] == 1.4
            and glob['memory'] == (96*2**20+2**29)/2
            and empty == dict(cpu=1., memory=2**30, source='default', keys=[]))

        class Client:
            def __init__(self, ledger):
                self.ledger = ledger
            def acquire(self, name, cpu, memory, manager='none', ports=()):
                return self.ledger.acquire(name, dict(cpu=cpu, memory=memory, manager=manager,
                                                     ports=list(ports)), mutation=True)
            def release(self, name):
                self.ledger.release(name)
            def close(self):
                pass

        invocation = 0
        def exercise(jobs, cores=40, gib=31, limit=None, floor=None, fault=None, background=False, resources_manifest=None):
            nonlocal invocation
            invocation += 1
            home = top / ('run-%d' % invocation)
            home.mkdir()
            clock = [1.]
            capacity = dict(cpu=cores, memory=gib * 2**30, manager=16)
            floor = floor or dict(cpu=cores, memory=gib * 2**30)
            ledger = scheduler.Ledger(capacity, floor)
            ledger.event = lambda action, name, resource, claim=None: ledger.events.append(
                dict(action=action, claimant=name, resource=resource, granted=ledger.totals()))
            # Keep the mutation root until every worker ends, as the graph does.
            ledger.acquire('root', dict(cpu=0, memory=0, manager='none', ports=[]), mutation=True)
            if background:
                ledger.acquire('other-node', dict(cpu=cores-floor['cpu'], memory=(gib*2**30)-floor['memory'],
                                                  manager='none', ports=[]))
            admission = gate.Admission(Client(ledger), capacity, floor)
            pool = gate.SuiteResources(resources_manifest or manifest)
            workers = gate.Workers(100000, pool, parallel=gate.worker_count(cores) if limit is None else limit,
                                   admission=admission)
            children = []
            class Child:
                def __init__(self, argv, **kwargs):
                    self.job = json.loads(Path(argv[-1]).read_text())
                    self.pid, self.returncode, self.born = 1000000 + len(children), None, clock[0]
                    children.append(self)
                    ok = self.job['mode'] != 'mutant'
                    obs = dict(count=1, observations=[['TEST target', ok]], row_names=['TEST target'],
                               failed_rows=[] if ok else ['TEST target'])
                    kwargs['stdout'].write(json.dumps(dict(observation=obs, replacement_count=1,
                        old_digest='a', new_digest='b' if not ok else 'a')).encode())
                def poll(self):
                    if clock[0] - self.born >= .2:
                        self.returncode = 0
                    return self.returncode
                def wait(self, timeout=None):
                    self.returncode = 0 if self.returncode is not None else -9
                    return self.returncode
            loader = gate.load
            def load_fixture(path):
                if Path(path).name == 'mutation_ownership.py':
                    return types.SimpleNamespace(cleanup=lambda *a: {})
                return loader(path)
            error = None
            if fault == 'meter':
                def fail(name):
                    raise PermissionError('no delegation')
                admission.meter_factory = fail
            with patch.object(gate.subprocess, 'Popen', Child), patch.object(gate, 'load', load_fixture), \
                    patch.object(gate.os, 'killpg', lambda *a: None), \
                    patch.object(gate.Workers, 'launcher_fds', lambda self: ()), \
                    patch.object(gate.time, 'monotonic', lambda: clock[0]), \
                    patch.object(gate.time, 'sleep', lambda dt: clock.__setitem__(0, clock[0] + dt)):
                try:
                    done = workers.run(jobs, home, ROOT)
                except gate.Refused as exc:
                    error, done = exc.code, {}
            return workers, ledger, done, error, admission

        base = dict(cpu=.5, memory=2**28, source='previous_key', keys=['old'])
        jobs = {'j%d' % n: dict(case=case, mode='baseline', budget_seconds=240, claim=base) for n in range(100)}
        fits = []
        for cores in (4, 20, 40):
            for gib in (4, 16, 31):
                workers, ledger, done, error, admission = exercise(jobs, cores, gib)
                wanted = min(gate.worker_count(cores), math.floor(cores/.5), gib*4, len(jobs))
                fits.append(error is None and len(done) == len(jobs) and workers.peak == wanted
                    and all(e['granted']['cpu'] <= cores and e['granted']['memory'] <= gib*2**30
                            for e in ledger.events))
                if cores == 40 and gib == 31:
                    fits.append(workers.peak == 80)
        row('fits-ledger', all(fits))
        invalid = {'bad': dict(jobs['j0'], claim=dict(base, memory=32*2**30))}
        _, ledger, done, error, _ = exercise(invalid)
        row('oversized-refused', error == 'invalid_resource_requirement' and not done
            and set(ledger.held) == {'root'})
        workers, ledger, done, error, _ = exercise({'bad': jobs['j0']}, fault='meter')
        row('cgroup-launch-refused', error == 'worker_launch_error' and not workers.active
            and set(ledger.held) == {'root'} and not workers.resources.held)

        restricted = {}
        for n in range(28):
            suite_name = 'manager.py' if n < 20 else 'project.py'
            restricted[str(n)] = dict(jobs['j0'], case=dict(case, suite=suite_name))
        restricted['exclusive'] = dict(jobs['j0'], case=dict(case, suite='exclusive.py'))
        workers, ledger, done, error, _ = exercise(restricted)
        row('manifest-and-manager', error is None and len(done) == len(restricted)
            and workers.resources.peak == {'systemd_user_manager': 16, 'new_project_fixture': 2}
            and all(e['granted']['manager'] <= 16 for e in ledger.events))

        # Enumerate the real registry without executing its unrelated suites. Seed
        # previous keys in a scratch store for every identity, never transplant times.
        inventory = gate.inventory_local(ROOT)
        inventory_manifest = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
        inventory_store = top / 'inventory'
        inventory_store.mkdir()
        for n, c in enumerate(inventory):
            oldkey = '%032x' % n
            (inventory_store / (oldkey + '.json')).write_text(json.dumps(dict(authority=str(ROOT),
                key=oldkey, identity=c['identity'], suite=c['suite'],
                resource_runs=[dict(at=now, cpu_seconds=6, elapsed=10, peak_anon_bytes=2**29)])))
        known = gate.CaseClaims(inventory_store)
        full_jobs = {c['identity']: dict(case=c, mode='baseline', budget_seconds=120,
                     claim=known.claim(c, 'changed-'+str(n))) for n, c in enumerate(inventory)}
        previous_run = exercise(full_jobs, 20, 15, resources_manifest=inventory_manifest)
        defaults = {n: dict(j, claim=empty) for n, j in full_jobs.items()}
        empty_run = exercise(defaults, 20, 15, resources_manifest=inventory_manifest)
        historical = exercise(dict(list(full_jobs.items())[:2689]), 20, 15, resources_manifest=inventory_manifest)
        row('unmeasured-inventory', len(inventory) >= 2689 and previous_run[3] is None
            and previous_run[0].peak >= 16 and previous_run[0].peak == 30
            and empty_run[3] is None and empty_run[0].peak == 15 and historical[0].peak == 30
            and all(j['claim']['source'] == 'previous_key' for j in full_jobs.values())
            and all(j['claim']['cpu'] == 1 and j['claim']['memory'] == 2**30 for j in defaults.values()))

        # Verdict fields pass through the actual Workers.run/finish path at each
        # ceiling; budget expectations below are independently calculated.
        jobs = {str(n): dict(case=case, mode='mutant', budget_seconds=240+n%3*60, claim=base)
                for n in range(40)}
        floor = dict(cpu=2, memory=2**30)
        receipts = [exercise(jobs, 20, 16, limit=n, floor=floor, background=True)
                    for n in (2, 8, 16, None)]
        same = [r[3] is None and all(o['budget_seconds'] == jobs[o['name']]['budget_seconds']
                                    for o in r[0].outcomes) for r in receipts]
        observations = [{n: v['result'] for n, v in r[2].items()} for r in receipts]
        same.append(all(o == observations[0] for o in observations))
        for ceiling in (2, 8, 16, 40):
            m = min(ceiling, 4)
            work = sum(j['budget_seconds'] for j in jobs.values())
            tail = max(j['budget_seconds'] for j in jobs.values())
            charges = work * (.5/2 + (2**28)/(2**30))
            wanted = max(2*len(jobs)*8/min(m,8), 120+min(work, work/m+tail+charges))
            got = gate.budget_for(len(jobs), ceiling, [jobs.values()], gate.SuiteResources(manifest), floor)
            same.append(got == wanted)
        controls = gate.control_jobs([case, dict(case, identity='wide')], gate.control_group, {},
                    {case['identity']: 240, 'wide': 360},
                    {case['identity']: base, 'wide': dict(base, cpu=2, memory=2**30)})
        same.append(all(j['budget_seconds'] == 360 and j['claim']['cpu'] == 2
                        and j['claim']['memory'] == 2**30 for j in controls.values()))
        row('same-verdicts', all(same))
        row('reserved-floor', all(e['granted']['cpu'] <= 20 and e['granted']['memory'] <= 16*2**30
            for r in receipts for e in r[1].events) and receipts[-1][0].peak == 4)

        # Real stage receipts, both phases, passing and failing cases, with only
        # inventory/snapshot/child boundaries replaced. The stage computes and
        # enforces its cap, validates verdicts and writes the scratch store.
        stage_cases = [dict(case, identity='case%d' % n, name='case%d' % n) for n in range(12)]
        stage_files = {'scripts/check_gate_mutations.py': (0o644, b'fixture')}
        def stage_run(ceiling, fail=False):
            nonlocal invocation
            invocation += 1
            times = top / ('stage-store-%d' % invocation)
            clock = [1.]
            claim_store = types.SimpleNamespace(claim=lambda *a: base)
            floor = dict(cpu=2, memory=2**30)
            ledger = scheduler.Ledger(dict(cpu=20, memory=16*2**30, manager=16), floor)
            ledger.event = lambda *a: None
            ledger.acquire('root', dict(cpu=0,memory=0,manager='none',ports=[]), mutation=True)
            class Meter:
                peak = 2**28
                def open_join(self):
                    return os.open('/dev/null', os.O_WRONLY)
                def sample(self, *a):
                    return dict(cpu_seconds=4, peak_anon_bytes=self.peak)
                def close(self):
                    pass
            admission = gate.Admission(Client(ledger), ledger.capacity, floor, lambda n: Meter())
            class Session:
                def __init__(self, root, files, cases, head, options, force_fresh=False):
                    self.keys = {c['identity']: None for c in cases}
                    self.reasons = {c['identity']: 'fresh' for c in cases}
                    self.hits, self.snapshots, self.store, self.forced = set(), {}, None, True
                    self.base_digest = 'fixture'
                def lookup(self, *a):
                    return None
                def unchanged(self):
                    return True
                def evidence(self, c, r, reused):
                    return dict(r, reused=reused)
                def publish(self, *a):
                    pass
            class Child:
                serial = 0
                def __init__(self, argv, **kwargs):
                    self.job = json.loads(Path(argv[-1]).read_text())
                    self.pid, self.returncode, self.born = 2000000 + Child.serial, None, clock[0]
                    Child.serial += 1
                    ok = self.job['mode'] != 'mutant' and not fail
                    obs = dict(count=1,observations=[['TEST target',ok]],row_names=['TEST target'],
                               failed_rows=[] if ok else ['TEST target'])
                    kwargs['stdout'].write(json.dumps(dict(observation=obs,replacement_count=1,
                        old_digest='a',new_digest='b' if self.job['mode']=='mutant' else 'a')).encode())
                def poll(self):
                    if clock[0]-self.born >= 10:
                        self.returncode = 0
                    return self.returncode
                def wait(self, timeout=None):
                    self.returncode = 0
                    return 0
            real_load, real_record, real_resources = gate.load, gate.record_case_times, gate.record_case_resources
            def loader(path):
                if Path(path).name == 'case_reuse.py':
                    return types.SimpleNamespace(Session=Session)
                if Path(path).name == 'mutation_ownership.py':
                    return types.SimpleNamespace(cleanup=lambda *a: {})
                return real_load(path)
            patches = dict(inventory=lambda *a: stage_cases,read_inputs=lambda *a: stage_files,
                git=lambda *a: 'head',snapshot=lambda *a: None,inputs_unchanged=lambda *a: True,
                load=loader,CaseClaims=lambda: claim_store,case_deadline=lambda key: 240,
                record_case_times=lambda root,samples,authority=False: real_record(root,samples,times,authority=authority),
                record_case_resources=lambda cases,keys,outcomes,group,authority=False:
                    real_resources(cases,keys,outcomes,group,times,authority=authority))
            with contextlib.ExitStack() as stack:
                for name, value in patches.items():
                    stack.enter_context(patch.object(gate,name,value))
                stack.enter_context(patch.object(gate.SuiteResources,'from_root',lambda *a:gate.SuiteResources(manifest)))
                stack.enter_context(patch.object(gate.Workers,'launcher_fds',lambda self:()))
                stack.enter_context(patch.object(gate.subprocess,'Popen',Child))
                stack.enter_context(patch.object(gate.os,'killpg',lambda *a:None))
                stack.enter_context(patch.object(gate.time,'monotonic',lambda:clock[0]))
                stack.enter_context(patch.object(gate.time,'sleep',lambda dt:clock.__setitem__(0,clock[0]+5)))
                stack.enter_context(patch.object(gate.signal,'setitimer',lambda *a:None))
                result = gate.run_stage(top,top/'.git',parallel=ceiling,admission=admission,measure=True)
            return result,times
        stage_runs = [stage_run(n) for n in (2,8,16,None)]
        stage_failed,failed_store = stage_run(8,True)
        fields = ('status','registered','executed','reused','rejected','surviving_workers','invalid_results')
        receipt_checks = [r['status']=='passed' and all(o['budget_seconds']==240 for o in r['worker_outcomes'])
                          and len(list(t.glob('*.json')))==12 for r,t in stage_runs]
        receipt_checks.append(all({k:r[k] for k in fields} == {k:stage_runs[0][0][k] for k in fields}
                                  for r,t in stage_runs))
        for (result, times), m in zip(stage_runs,(2,4,4,4)):
            # Two shared controls then twelve mutants, each with 240s deadline.
            wanted = 120 + sum(min(n*240,n*240/m+240+n*240*.5) for n in (2,12))
            receipt_checks.append(result['budget_seconds']==wanted and result['guaranteed_workers']==m)
        receipt_checks.append(stage_failed['error']=='invalid_baseline' and not list(failed_store.glob('*.json')))
        row('stage-receipts-and-recording', all(receipt_checks))

        regressions = load(ROOT / 'proof/VELDO-0219/round2/check.py')
        row('aggregate-handoff', regressions.handoff(gate))
        row('unmetered-fixed-cap', regressions.fixed_cap(gate))
        row('cpu-per-run', regressions.per_run(gate))
        row('blocking-resource', regressions.blocking_resource(gate))
        row('unit-lifecycle', regressions.unit_lifecycle(ownership))
        row('final-memory-bound', gate.resource_claim([dict(cpu_seconds=1, elapsed=2,
            peak_anon_bytes=1024, peak_memory_bytes=32*2**20)])['memory'] == 32*2**20)

        qualification = load(ROOT / 'proof/VELDO-0219/qualification.py')
        capture = qualification.fixture()
        passed = qualification.check(capture)
        slow = copy.deepcopy(capture)
        slow['mutation']['elapsed'] = 5207
        slow['mutation']['peak_workers'] = 16
        missing = copy.deepcopy(capture)
        missing['mutation']['worker_outcomes'] = []
        row('qualification-capture', passed['passed'] and not qualification.check(slow)['passed']
            and not qualification.check(missing)['passed'] and not qualification.check({})['passed'])


_v219_checks()
