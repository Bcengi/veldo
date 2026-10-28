import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import datetime
sys.dont_write_bytecode = True
root = Path.cwd()
spec = importlib.util.spec_from_file_location('gate', root / 'scripts/check_gate_mutations.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
cases = gate.inventory_local(root)
files = gate.read_inputs(root, gate.common_directory(root))
leg = gate.load(root / 'scripts/gate_legs.py').mutation_leg()
reuse = gate.load(root / 'scripts/case_reuse.py').Session(root, files, cases,
    gate.git(root, gate.common_directory(root), 'rev-parse', 'HEAD'),
    {'fixture_version': gate.FIXTURE_VERSION, 'capacities': None,
     'worker_environment': gate.fixed_env('<private-worker-home>')}, force_fresh=True)
prepared = {c['identity']: {'declared_case': True} for c in cases
            if c['identity'] in reuse.snapshots and not gate.in_leg(leg, c)}
keys = {c['identity']: gate.case_time_key(c, files, leg) for c in cases}
deadlines = {identity: gate.case_deadline(key) for identity, key in keys.items()}
def group(case):
    return case['identity'] if case['identity'] in prepared else gate.control_group(case)
controls = gate.control_jobs(cases, group, prepared, deadlines)
mutants = {c['identity']: dict(case=c, budget_seconds=deadlines[c['identity']]) for c in cases}
resources = gate.SuiteResources.from_root(root)
phases = [list(controls.values()), list(mutants.values())]
report = dict(calculated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), inventory=len(cases), workers=16, mode='all fresh, read-only planning; no workers launched',
              store=str(gate.CASE_TIMES), measured_above_floor=sum(v > 120 for v in deadlines.values()),
              existing_key_files=sum((gate.CASE_TIMES / (key + '.json')).is_file() for key in keys.values()),
              capacities=resources.capacity, old_count_cap=gate.budget_for(len(cases), 16),
              serial_cap=120 + sum(j['budget_seconds'] for jobs in phases for j in jobs),
              bound=gate.budget_for(len(cases), 16, phases, resources),
              implementation_sha256=hashlib.sha256((root / 'scripts/check_gate_mutations.py').read_bytes()).hexdigest(),
              measured_cases=[dict(identity=identity, key=keys[identity], deadline=seconds)
                              for identity, seconds in deadlines.items() if seconds > 120],
              phases=[])
for name, jobs in zip(('controls', 'mutants'), phases):
    chain_details = {}
    for resource, capacity in resources.capacity.items():
        slot_time, drain_tails, prefix = 0, 0, 0
        for job in jobs:
            slots = resources.demand(job).get(resource, 0)
            if slots:
                slot_time += slots * job['budget_seconds'] / capacity
                if slots > 1:
                    drain_tails += prefix
                prefix = max(prefix, job['budget_seconds'])
        chain_details[resource] = dict(normalized_slot_time=slot_time, drain_tails=drain_tails)
    report['phases'].append(dict(name=name, jobs=len(jobs), resource_chains=chain_details,
        work=sum(j['budget_seconds'] for j in jobs),
        tail=max(j['budget_seconds'] for j in jobs),
        bound=gate.budget_for(0, 16, [jobs], resources) - gate.BUDGET))
print(json.dumps(report, indent=2))
