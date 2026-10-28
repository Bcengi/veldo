"""VELDO-0216 ticket checks. Real scheduler, leg runner and candidate launcher.

Only the cgroup meter is a fixture: this suite never creates a manager scope or
acquires the real host lock. Mutation payloads are controlled authority fixtures,
never the full mutation coordinator. The original mutation input guard is used.
"""


def _v216_checks():
    import contextlib
    import copy
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shlex
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    from unittest.mock import patch

    def load(path):
        spec = importlib.util.spec_from_file_location('v216_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    source = ROOT / "scripts" / "gate_schedule.py"
    leg_source = ROOT / "scripts" / "gate_legs.py"
    original = load(source)
    original.HERE = ROOT / 'scripts'
    mutation = original.load_module('check_gate_mutations')
    reduction = original.load_module('reuse_stamp')

    def row(name, condition):
        expect('VELDO-0216 concurrent-stages/' + name, condition)

    class Meter:
        def __init__(self, name):
            self.name = name
        def command(self, argv):
            return argv
        def sample(self):
            return {'cpu_seconds': .01, 'peak_anon_bytes': 1024, 'metrics_source': 'fixture'}
        def finish(self):
            return dict(self.sample(), live_descendants=False)

    with tempfile.TemporaryDirectory(prefix='v216-') as tmp, contextlib.ExitStack() as stack:
        top = Path(tmp)
        home = top / 'home'
        home.mkdir()
        stack.enter_context(patch.dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE='1'))
        authority = top / 'authority'
        scripts = authority / 'scripts'
        scripts.mkdir(parents=True)
        for name in ('gate_candidate.py', 'agent_sandbox.py', 'agent_sandbox.json'):
            shutil.copyfile(ROOT / 'scripts' / name, scripts / name)
        shutil.copyfile(source, scripts / 'gate_schedule.py')
        shutil.copyfile(leg_source, scripts / 'gate_legs.py')
        shutil.copytree(ROOT / '.veldo', authority / '.veldo',
                        ignore=shutil.ignore_patterns('__pycache__', 'events.jsonl', 'last_verify'))
        scheduler = load(scripts / 'gate_schedule.py')
        legs = scheduler.load_module('gate_legs')
        # Use actual scratch Git inputs, including untracked files and file modes.
        candidate = top / 'candidate'
        candidate.mkdir()
        (candidate/'scripts').mkdir()
        (candidate/'scripts/gate_graph.json').write_text('{"schema":"candidate must not choose the graph"}')
        subprocess.run(['git', 'init', '-q', str(candidate)], check=True)
        (candidate / 'input').write_text('original\n')
        subprocess.run(['git', '-C', str(candidate), 'add', 'input'], check=True)
        subprocess.run(['git', '-C', str(candidate), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        common = candidate / '.git'
        (authority/'.veldo/authority_git_common').write_text(str(common))
        stack.enter_context(patch.dict(os.environ, VELDO_EXPECTED_GIT_COMMON=str(common)))

        def guard(root):
            files = mutation.read_inputs(root, common)
            head = mutation.git(root, common, 'rev-parse', 'HEAD')
            return lambda: mutation.inputs_unchanged(root, common, files, head)

        code = "import os,time,sys; time.sleep(.12); print('LEG='+os.getenv('VELDO_GATE_LEG','whole')); print('CHANNEL='+os.getenv('VELDO_GATE_LEDGER_FD','absent')); sys.exit(int(os.getenv('V216_FAIL','')==os.getenv('VELDO_GATE_LEG','whole')))"
        command = shlex.quote(sys.executable) + ' -c ' + shlex.quote(code)
        catalog = {s: command for s in ('lint', 'unit', 'integration', 'security', 'generated', 'docs', 'packaging', 'extra')}
        catalog['mutation'] = 'authority mutation stage'
        declaration = {'schema': 'veldo.gate-unconfined/v1', 'authority': 'controlled ticket fixture',
                       'stages': {'unit': command, 'integration': command, 'mutation': catalog['mutation']},
                       'suites': [{'suite': '01_fixture', 'reason': 'controlled fixture leg for scheduling'}]}
        listing = scripts / 'gate_unconfined.json'
        listing.write_text(json.dumps(declaration))
        nodes = {n: {'depends_on': [], 'writes_candidate': False, 'manager': 'none', 'ports': []}
                 for n in scheduler.required_nodes(catalog, declaration)}
        graph = {'schema': 'veldo.gate-graph/v1', 'nodes': nodes,
                 'reserve': {'cpu': 0, 'memory': 0}, 'mutation_floor': {'cpu': 0, 'memory': 0}}
        graph_path = scripts / 'gate_graph.json'
        graph_path.write_text(json.dumps(graph))
        # A controlled mutation authority with the same receipt and leg-record contract.
        (scripts / 'check_gate_mutations.py').write_text('''import argparse, importlib.util, json, os
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--root'); p.add_argument('--receipt'); p.add_argument('--legs-record'); a=p.parse_args()
s=importlib.util.spec_from_file_location('legs',Path(__file__).with_name('gate_legs.py')); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
leg=m.mutation_leg(); m.write_record(a.legs_record,'mutation',leg['declaration'],leg['entries'])
r={'status':'failed' if os.getenv('V216_FAIL')=='mutation' else 'passed','reused':0,'force_fresh':True,'registered':1,'executed':1,'rejected':0}
Path(a.receipt).write_text(json.dumps(r)); print(json.dumps(r)); raise SystemExit(r['status']=='failed')
''')
        loads = scheduler.load_module
        # Authority measurement boundary only. Claims below represent fixture measurements;
        # the production ledger, launcher, legs, record and scheduler remain unchanged.
        def fixture_load(name):
            module = loads(name)
            if name == 'gate_legs':
                module.read_resources = lambda *a: {'cpu_rate': 1, 'peak_anon_bytes': 1024}
            return module
        stack.enter_context(patch.object(scheduler, 'load_module', fixture_load))
        counter = 0
        def run(document=graph, fail='', serial=False, commands=None):
            nonlocal counter
            counter += 1
            out = top / ('run-' + str(counter))
            graph_path.write_text(json.dumps(document) if not isinstance(document, str) else document)
            log = io.StringIO()
            with patch.dict(os.environ, V216_FAIL=fail), contextlib.redirect_stdout(log):
                receipt = scheduler.run(commands or catalog, candidate, out, out / 'legs', out / 'mutation',
                    graph_path=graph_path, capacity={'cpu': 32, 'memory': 1048576, 'manager': 16},
                    measurement_store=top / 'store', meter_factory=Meter, guard_factory=guard, serial=serial,
                    node_inputs_factory=lambda root,dest: scheduler.NodeInputs(root,dest,mutation))
            return receipt, out, log.getvalue()

        passed, out, log = run()
        if set(passed['stages'].values()) != {'pass'}:
            print('fixture diagnostics', passed['stages'], log[-9000:])
        required = set(nodes)
        missing = copy.deepcopy(graph)
        del missing['nodes']['security']
        def refused(document):
            before = counter
            try:
                run(document)
            except scheduler.Refused:
                output = top / ('run-' + str(before + 1))
                return not list(output.glob('*.log'))
            return False
        row('graph-complete', set(passed['nodes']) == required and passed['checks_run'] == 9
            and set(passed['stages'].values()) == {'pass'} and refused(missing))
        bad = []
        cycle = copy.deepcopy(graph)
        cycle['nodes']['lint']['depends_on'] = ['security']
        cycle['nodes']['security']['depends_on'] = ['lint']
        unknown = copy.deepcopy(graph)
        unknown['nodes']['imaginary'] = copy.deepcopy(nodes['lint'])
        writer = copy.deepcopy(graph)
        writer['nodes']['lint']['writes_candidate'] = True
        for document in (cycle, missing, unknown, '{invalid', [], {'schema': 'bad'}, writer):
            bad.append(refused(document))
        row('graph-refusals', all(bad))
        # The graph can delay a node without imposing a barrier on independent nodes.
        dependent = copy.deepcopy(graph)
        dependent['nodes']['docs']['depends_on'] = ['unit.confined']
        ordered, _, _ = run(dependent)
        row('dependency-start', ordered['nodes']['docs']['start'] >= ordered['nodes']['unit.confined']['end']
            and ordered['nodes']['integration.confined']['start'] < ordered['nodes']['unit.confined']['end'])
        # Every source block appears exactly once in catalog order, even if finish order differs.
        row('ordered-logs', [line[3:] for line in log.splitlines() if line.startswith('== ')] == list(nodes)
            and all('CHANNEL=absent' in (out / (n + '.log')).read_text() for n in nodes if n != 'mutation'))

        def run_serial(fail=''):
            # Today's no-graph runner: one unsplit run_stage per catalog item.
            # No scheduler invocation, no split-leg argument, no prior-times override.
            nonlocal counter
            counter += 1
            output = top / ('serial-' + str(counter))
            output.mkdir()
            stages = {}
            with patch.dict(os.environ, V216_FAIL=fail):
                for stage, cmd in catalog.items():
                    argv = scheduler.command_for(candidate, stage, None, cmd,
                        output/'legs', output/'mutation', declaration)
                    completed = subprocess.run(argv, cwd=candidate, capture_output=True,
                        text=True, pass_fds=legs._launcher_fds())
                    (output/(stage+'.log')).write_text(completed.stdout+completed.stderr)
                    stages[stage] = 'pass' if completed.returncode == 0 else 'FAIL'
            return dict(stages=stages, checks_run=len(stages)), output, ''

        pairs = []
        exact_fields = []
        for failure in ('', 'confined', 'unconfined', 'mutation'):
            receipts = []
            for serial in (True, False):
                r, output, _ = run_serial(failure) if serial else run(fail=failure)
                m = json.loads((output / 'mutation').read_text())
                try:
                    fields = reduction.fields(m, True)
                except ValueError:
                    fields = {'force_fresh': True, 'reused': {'unit': 0, 'mutation': None}}
                try:
                    unconfined = legs.stamp(output / 'legs', ['unit', 'integration', 'mutation'])
                except legs.Invalid:
                    unconfined = None
                # Exercise the actual shell stamp and event printf, without running verify.sh.
                verify = (ROOT / 'scripts/verify.sh').read_text()
                start = verify.index('VELDO_HOST_FIELD="$VELDO_HOST_FIELD$VELDO_GRAPH_FIELD"')
                end = verify.index('if [ "$VELDO_OUT" = ".veldo" ]; then\n  veldo_write_stamp', start)
                fragment = verify[start:end] + '\nveldo_write_stamp "$V216_STAMP"\nprintf "%s\\n" "$EVENT_LINE"\n'
                env = dict(os.environ, VELDO_HOST_FIELD='', VELDO_GRAPH_FIELD='' if serial else ',"graph":'+json.dumps(r['graph']),
                           EVENT='gate.failed' if failure else 'gate.passed', COMMIT='a'*40, TS='fixture',
                           RAN=str(r['checks_run']), NA='15', STATUS='red' if failure else 'green', VERSION_JSON='null',
                           TREE_JSON='"clean"', REUSE_JSON=json.dumps(fields)[1:-1],
                           UNCONFINED_FIELD=',"unconfined":'+json.dumps(unconfined), V216_STAMP=str(output/'stamp'))
                emitted = subprocess.run(['bash', '-c', fragment], env=env, capture_output=True, text=True, check=True)
                receipts.append(dict(stages=r['stages'], checks=r['checks_run'], mutation=m,
                                     unconfined=unconfined, stamp=json.loads((output/'stamp').read_text()),
                                     event=json.loads(emitted.stdout)))
                expected = dict(fields, checks_run=9, unconfined=unconfined)
                if not serial:
                    expected['graph'] = r['graph']
                exact_fields.append(all(receipts[-1][kind].get(k) == v for kind in ('stamp','event')
                                        for k,v in expected.items()) and receipts[-1]['stamp']['checks_na']==15)
            # Graph identity is intentionally absent from the no-graph receipts.
            for kind in ('stamp', 'event'):
                receipts[1][kind].pop('graph', None)
            expected_failures = {'unit', 'integration'} if failure in ('confined', 'unconfined') else ({'mutation'} if failure else set())
            pairs.append(receipts[0] == receipts[1] and receipts[1]['unconfined'] is not None
                         and {s for s,v in receipts[1]['stages'].items() if v == 'FAIL'} == expected_failures)
        row('same-verdicts', all(pairs) and all(exact_fields))

        # A real unconfined candidate writer is RED by its node name and whole-tree comparison.
        write_command = 'if [ "$VELDO_GATE_LEG" = unconfined ]; then printf changed > input; else sleep .1; fi'
        saved = listing.read_text()
        d = copy.deepcopy(declaration)
        d['stages']['unit'] = write_command
        listing.write_text(json.dumps(d))
        modified = dict(catalog, unit=write_command)
        wrote, _, _ = run(commands=modified)
        row('tree-unchanged', not wrote['inputs_unchanged'] and wrote['nodes']['unit.unconfined']['verdict'] == 'FAIL'
            and 'candidate_tree_changed' in wrote['nodes']['unit.unconfined']['error']
            and all(n['verdict']=='pass' for name,n in wrote['nodes'].items() if name!='unit.unconfined')
            and (candidate/'input').read_text()=='original\n')
        (candidate/'input').write_text('original\n')
        listing.write_text(saved)

        # Algebra and every recorded instant, including manager workers and fixed ports.
        ledger = scheduler.Ledger({'cpu': 10, 'memory': 1000, 'manager': 3})
        claim = lambda cpu, memory, manager='none', ports=(): dict(cpu=cpu, memory=memory, manager=manager, ports=list(ports))
        with contextlib.redirect_stdout(io.StringIO()):
            checks = [ledger.acquire('worker1', claim(6, 100, 'shared')),
                      not ledger.acquire('cpu', claim(5, 100)),
                      not ledger.acquire('memory', claim(1, 950)),
                      not ledger.acquire('exclusive', claim(1, 100, 'exclusive')),
                      ledger.acquire('worker2', claim(1, 100, 'shared', [12345])),
                      not ledger.acquire('port', claim(1, 100, ports=[12345]))]
            for held in list(ledger.held):
                ledger.release(held)
            checks.extend([ledger.acquire('exclusive', claim(1, 100, 'exclusive')),
                           not ledger.acquire('worker3', claim(1, 100, 'shared'))])
            ledger.release('exclusive')
            for name, c in [('cpu',claim(5,100)),('memory',claim(1,950)),('port',claim(1,100,ports=[12345]))]:
                checks.append(ledger.acquire(name,c)); ledger.release(name)
            try:
                ledger.acquire('impossible', claim(11, 1))
            except scheduler.Refused as error:
                checks.append('invalid_resource_requirement' in str(error))
        row('ledger-sums', all(checks) and all(all(e['granted'][r] <= ledger.capacity[r] for r in ledger.capacity)
            for e in ledger.events) and {e['resource'] for e in ledger.events if e['action']=='refuse'} >= {'cpu','memory','manager','ports'})
        reserve = scheduler.Ledger({'cpu': 10, 'memory': 1000, 'manager': 3}, {'cpu': 6, 'memory': 600})
        with contextlib.redirect_stdout(io.StringIO()):
            reserved = not reserve.acquire('other', claim(5, 500)) and reserve.acquire('other',claim(4,400)) \
                and reserve.acquire('mutation',claim(6,600),mutation=True)
        reserve = scheduler.Ledger({'cpu':10,'memory':1000,'manager':3},{'cpu':6,'memory':600})
        with contextlib.redirect_stdout(io.StringIO()):
            held = [reserve.acquire('mutation',claim(2,200),mutation=True),
                    not reserve.acquire('borrow-floor',claim(5,500)),
                    reserve.acquire('other',claim(4,400)),
                    reserve.acquire('mutation/worker',claim(4,400),mutation=True)]
            for claimant in ('borrow-floor','mutation/worker','mutation'):
                if claimant in reserve.held:
                    reserve.release(claimant)
            held.append(reserve.acquire('after-mutation',claim(6,600)))
        row('mutation-floor', reserved and all(held))

        # Real inherited channel: a trusted coordinator claims two worker/shard needs.
        channel_code = '''import importlib.util,os
s=importlib.util.spec_from_file_location('schedule',os.environ['V216_SCHEDULER']); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
c=m.Client(); assert c.acquire('shard',2,3000,'shared',[22345]); assert not c.acquire('worker',31,3000); assert not c.acquire('exclusive',1,100,'exclusive'); c.release('shard'); assert c.acquire('worker',2,3000,'exclusive'); c.release('worker'); c.close()
'''
        saved_command = scheduler.command_for
        def channel_command(*args):
            return [sys.executable, '-c', channel_code]
        channel_catalog = {'lint': command}
        channel_graph = copy.deepcopy(graph)
        channel_graph['nodes'] = {'lint': nodes['lint']}
        with patch.object(scheduler, 'command_for', channel_command), patch.dict(os.environ, V216_SCHEDULER=str(scripts/'gate_schedule.py')):
            channel, _, _ = run(channel_graph, commands=channel_catalog)
        row('inherited-ledger', channel['stages']['lint'] == 'pass'
            and {e['claimant'] for e in channel['ledger'] if e['action']=='grant'} == {'lint','lint/shard','lint/worker'}
            and any(e['action']=='refuse' and e['claimant']=='lint/worker' for e in channel['ledger']))

        # Actual short processes qualify concurrency mechanics, never the 6000s host claim.
        timed_catalog = {'lint': 'sleep .4', 'docs': 'sleep .4', 'extra': 'sleep .4'}
        timed_graph = copy.deepcopy(graph)
        timed_graph['nodes'] = {n:nodes[n] for n in timed_catalog}
        def direct(root, stage, leg, command, *args):
            return ['bash','-c',command]
        with patch.object(scheduler,'command_for',direct):
            timing, _, _ = run(timed_graph, commands=timed_catalog)
        intervals = timing['nodes'].values()
        row('critical-path-fixture', max(n['start'] for n in intervals) < min(n['end'] for n in intervals)
            and timing['critical_path_seconds'] < sum(n['wall_seconds'] for n in intervals) * .65)

        # Measurement storage is authority-bound, expiring, and cannot call cgroup total memory anon.
        store = top / 'measurements'
        metrics = dict(cpu_seconds=4, peak_anon_bytes=4567, metrics_source='cgroup-v2-anon-sampled-50ms')
        legs.record_resources(store,'digest','unit.confined',2,metrics)
        measured = legs.read_resources(store,'digest','unit.confined')
        row('measured-claims', measured['cpu_rate'] == 2 and measured['peak_anon_bytes'] == 4567
            and legs.read_resources(store,'other','unit.confined') is None)
        race_store = top/'race-store'
        record_code = "import importlib.util,sys; from pathlib import Path; s=importlib.util.spec_from_file_location('legs',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.record_time(Path(sys.argv[2]),'race',sys.argv[3],123,'run')"
        writers = [subprocess.Popen([sys.executable,'-c',record_code,str(scripts/'gate_legs.py'),str(race_store),leg])
                   for leg in ('confined','unconfined')]
        codes = [p.wait() for p in writers]
        row('measurement-record-race', codes==[0,0] and set(legs.read_times(race_store,'race'))=={'confined','unconfined'}
            and len(list(race_store.iterdir()))==1)
        # Capacity uses exact fractional ancestor quota, scope memory and manifest slots.
        cgroup = top/'cgroups'
        own = Path('/proc/self/cgroup').read_text().split('::',1)[1].strip()
        base = cgroup/own.lstrip('/')
        base.mkdir(parents=True)
        (base/'cpu.max').write_text('150000 100000')
        (base/'memory.max').write_text('1000000')
        manifest = top/'manifest.json'
        manifest.write_text(json.dumps({'resource_capacities':{'systemd_user_manager':7}}))
        cap_graph = copy.deepcopy(graph)
        cap_graph['reserve'] = {'cpu':.25,'memory':100000}
        cap = scheduler.capacities(cap_graph,own,manifest,cgroup)
        row('scope-capacities', cap == {'cpu':min(len(os.sched_getaffinity(0)),1.5)-.25,'memory':900000,'manager':7})
        meter = scheduler.Meter.__new__(scheduler.Meter)
        meter.path, meter.peak = base, 0
        (base/'memory.stat').write_text('anon 1234\nfile 999999\n')
        (base/'cpu.stat').write_text('usage_usec 2500000\n')
        measured = meter.sample()
        (base/'memory.stat').write_text('anon 100\nfile 999999\n')
        row('anonymous-metrics', measured['cpu_seconds']==2.5 and measured['peak_anon_bytes']==1234
            and meter.sample()['peak_anon_bytes']==1234)
        # No borrowed or invented measurements: a cold authority serializes whole claims.
        with patch.object(scheduler,'load_module',loads), patch.object(scheduler,'command_for',direct):
            cold, _, _ = run(timed_graph,commands=timed_catalog)
        cold_nodes = list(cold['nodes'].values())
        row('cold-measurements', all(cold_nodes[i]['start'] >= cold_nodes[i-1]['end'] for i in range(1,len(cold_nodes))))
        # The batch checker rejects absent evidence and a 10719s serialized canonical
        # capture. The passing document here is synthetic and proves the checker only.
        qualification = load(ROOT/'proof/VELDO-0216/qualification.py')
        baseline = json.loads((ROOT/'proof/VELDO-0216/serial-baseline.json').read_text())
        fake_nodes = {n:dict(start=0,end=10,wall_seconds=10,cpu_seconds=5,peak_anon_bytes=1234,
                             verdict='pass',metrics_source='cgroup-v2-anon-sampled-50ms') for n in baseline['nodes']}
        synthetic = {'head':'a'*40,'elapsed':5300,'without_0219_0221':True,
            'host':{'cores':20,'memory_bytes':31*2**30,'scope_memory_max':16*2**30},
            'stamp':{'commit':'a'*40,'status':'green','force_fresh':True,'reused':{'unit':0,'mutation':0},'graph':'digest'},
            'event':{'commit':'a'*40,'type':'gate.passed','force_fresh':True,'reused':{'unit':0,'mutation':0},'graph':'digest'},
            'schedule':{'graph':'digest','inputs_unchanged':True,'wall_seconds':5290,'critical_path_seconds':5207,
                'critical_path_end':'mutation','nodes':fake_nodes,'peak_granted':{'cpu':10,'memory':100,'manager':1},
                'capacities':{'cpu':20,'memory':1000,'manager':16}}}
        serialized = copy.deepcopy(synthetic)
        serialized['elapsed'] = baseline['elapsed']
        serialized['schedule']['wall_seconds'] = baseline['elapsed']-6
        serialized['schedule']['critical_path_seconds'] = baseline['elapsed']-6
        row('canonical-receipt-check', qualification.check(synthetic,baseline)['passed']
            and not qualification.check(serialized,baseline)['passed'] and not qualification.check({},baseline)['passed'])

        with patch.object(legs,'_record_time_locked',side_effect=OSError('fixture refusal')), contextlib.redirect_stdout(io.StringIO()):
            row('timing-store-refusal', legs.record_time(top/'unwritable-store','digest','confined',1,'run') is False)
        # Execute the actual catalog shell fragment through the scheduler CLI. Never
        # execute verify.sh. Only kernel metering/capacities are fixture substitutes.
        shutil.copyfile(scripts/'gate_schedule.py', scripts/'gate_schedule_impl.py')
        wrapper = """import importlib.util,json,os
from pathlib import Path
def load(path):
 s=importlib.util.spec_from_file_location('fixture_'+path.stem,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
m=load(Path(__file__).with_name('gate_schedule_impl.py'))
m.capacities=lambda *a: dict(cpu=32,memory=1048576,manager=16)
class Meter:
 def __init__(self,*a): pass
 def command(self,argv): return argv
 def sample(self): return dict(cpu_seconds=.01,peak_anon_bytes=1024,metrics_source='fixture')
 def finish(self): return dict(self.sample(),live_descendants=False)
m.Meter=Meter
original=m.load_module
mutation=load(Path(os.environ['V216_SOURCE_ROOT'])/'scripts/check_gate_mutations.py')
def modules(name):
 if name=='check_gate_mutations': return mutation
 result=original(name)
 if name=='gate_legs': result.read_resources=lambda *a: dict(cpu_rate=1,peak_anon_bytes=1024)
 return result
m.load_module=modules
raise SystemExit(m.main())
"""
        (scripts/'gate_schedule.py').write_text(wrapper)
        graph_path.write_text(json.dumps(graph))
        verify = (ROOT/'scripts/verify.sh').read_text()
        functions = verify[verify.index('veldo_candidate() {'):verify.index('# CANDIDATE MODE')]
        order = __import__('re').search(r'ORDER="([^"]+)"',verify).group(1).replace('\\\n',' ')
        definitions = '\n'.join('CHECK_'+n+'='+shlex.quote('required:'+catalog[n] if n in catalog else 'na:fixture') for n in order.split())
        begin = verify.index('FAIL=0; RAN=0;')
        finish = verify.index('if [ "$VELDO_GRAPH_REFUSED" = 0 ]; then\necho "== secret scan',begin)
        fragment = 'set -u\n'+functions+'\nORDER='+shlex.quote(order)+'\n'+definitions+'\n'+verify[begin:finish]
        fragment += '\nprintf "COUNTS %s %s %s\\n" "$RAN" "$NA" "$FAIL"\n'
        shell_counts = []
        refusal_records = []
        for graph_enabled in (True,False,'invalid','capacity','exception'):
            shell_out = top/('shell-'+str(graph_enabled))
            shell_out.mkdir()
            victim = top/'receipt-link-target'
            victim.write_text('preserve this target')
            if graph_enabled is True:
                (shell_out/'gate-schedule.json').symlink_to(victim)
            if not graph_enabled:
                graph_path.unlink()
            elif graph_enabled=='invalid':
                graph_path.write_text('{bad graph')
            elif graph_enabled in ('capacity','exception'):
                graph_path.write_text(json.dumps(graph))
                (scripts/'gate_schedule.py').write_text(wrapper.replace(
                    'm.Meter=Meter',
                    "m.Meter=Meter\nm.capacities=lambda *a: dict(cpu=0,memory=1,manager=1)"
                    if graph_enabled=='capacity' else "m.Meter=Meter\nm.Meter=lambda *a: (_ for _ in ()).throw(OSError('meter refusal'))"))
            env = dict(os.environ, VELDO_AUTHORITY=str(authority), VELDO_OUT=str(shell_out),
                       VELDO_LEGS_RECORD=str(shell_out/'legs'), VELDO_REUSE_RECEIPT=str(shell_out/'mutation'),
                       VELDO_LEGS_EXPECTED='', V216_SOURCE_ROOT=str(ROOT), V216_FAIL='')
            refusing = graph_enabled in ('invalid','capacity','exception')
            emitted_fragment = fragment
            if refusing:
                (shell_out/'last_verify').write_text('{"status":"green"}')
                (shell_out/'events.jsonl').write_text('')
                emitted_fragment += verify[verify.index('COMMIT=$(git rev-parse'): ]
            env['VELDO_HOST_FIELD'] = ''
            result = subprocess.run(['bash','-c',emitted_fragment],cwd=candidate,env=env,capture_output=True,text=True,
                                    pass_fds=legs._launcher_fds())
            if refusing:
                stamp = json.loads((shell_out/'last_verify').read_text())
                events = [json.loads(line) for line in (shell_out/'events.jsonl').read_text().splitlines()]
                refusal_records.append(stamp.get('status')=='red' and stamp.get('checks_run')==0
                    and events and events[-1].get('type')=='gate.failed'
                    and events[-1].get('checks_run')==0)
                shell_counts.append(result.returncode==1 and 'GATE: RED' in result.stdout
                    and not (shell_out/'mutation').exists() and ' start ' not in result.stdout)
            else:
                safe_output = graph_enabled is not True or (not (shell_out/'gate-schedule.json').is_symlink()
                    and victim.read_text()=='preserve this target'
                    and json.loads((shell_out/'gate-schedule.json').read_text())['checks_run']==9)
                shell_counts.append(result.returncode==0 and 'COUNTS 9 15 0' in result.stdout and safe_output)
            if not shell_counts[-1]:
                print('catalog fixture diagnostics',graph_enabled,result.returncode,result.stdout[-3000:],result.stderr[-2000:])
        row('shell-catalog', all(shell_counts))
        row('graph-refusal-record', all(refusal_records))
        shutil.copyfile(scripts/'gate_schedule_impl.py',scripts/'gate_schedule.py')

        # Production graph and catalog are independently enumerated every run.
        verify = (ROOT/'scripts/verify.sh').read_text()
        actual = dict(__import__('re').findall(r'^CHECK_(\w+)="required:([^"]+)"',verify,__import__('re').M))
        actual_declaration = json.loads((ROOT/'scripts/gate_unconfined.json').read_text())
        actual_graph, _, _ = original.read_graph(actual,actual_declaration,ROOT/'scripts/gate_graph.json')
        row('authority-wiring', '.veldo/gate-schedule.json' in (ROOT/'.gitignore').read_text().splitlines()
            and set(actual_graph['nodes']) == set(original.required_nodes(actual,actual_declaration))
            and all('scripts/gate_schedule.py' in (ROOT/p).read_text() for p in
                    ('.veldo/reuse_evidence.py','engine/.veldo/reuse_evidence.py','.veldo/init_scaffold.py','engine/.veldo/init_scaffold.py'))
            and all('VELDO_GRAPH_FIELD' in (ROOT/p).read_text() for p in ('scripts/verify.sh','engine/scripts/verify.sh')))


_v216_checks()
