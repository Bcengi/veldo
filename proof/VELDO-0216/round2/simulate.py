"""Discrete event replay of recorded durations through the production ledger.

No gate processes run. Startup costs, new suites and contention are unmeasured;
this is a projection, never canonical qualification.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import types
ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
revision = sys.argv[1] if len(sys.argv) > 1 else None

def source(path):
    return subprocess.check_output(['git', 'show', revision+':'+path], cwd=ROOT).decode() if revision else (ROOT/path).read_text()

scheduler = types.ModuleType('projection')
scheduler.__file__ = str(ROOT/'scripts/gate_schedule.py')
exec(compile(source('scripts/gate_schedule.py'), scheduler.__file__, 'exec'), scheduler.__dict__)
graph = json.loads(source('scripts/gate_graph.json'))
baseline = json.loads((ROOT/'proof/VELDO-0216/serial-baseline.json').read_text())
capacity = dict(cpu=20, memory=15*2**30, manager=16)
ledger = scheduler.Ledger(capacity, graph['mutation_floor'])
claims = {}
for name, node in graph['nodes'].items():
    # The pre-round-two production branch literally reserves full CPU and memory
    # on missing measurements. The new branch uses its real node_claim function.
    claims[name] = scheduler.node_claim(node, None, capacity)[0] if hasattr(scheduler, 'node_claim') else dict(
        cpu=capacity['cpu'], memory=capacity['memory'], manager=node['manager'], ports=node['ports'])
pending = sorted(graph['nodes'], key=lambda n: n != 'mutation')
active, completed, intervals = {}, set(), {}
now = 0
with contextlib.redirect_stdout(io.StringIO()):
    while pending or active:
        for name in list(pending):
            if not set(graph['nodes'][name]['depends_on']) <= completed:
                continue
            if ledger.acquire(name, claims[name], mutation=name == 'mutation'):
                b = baseline['nodes'][name]
                duration = b['wall_seconds'] if b['wall_seconds'] is not None else b['wall_interval_seconds'][1]
                active[name] = now + duration
                intervals[name] = dict(start=now, end=now+duration, seconds=duration)
                pending.remove(name)
        if not active:
            raise AssertionError('no claim fits')
        now = min(active.values())
        for name in list(active):
            if active[name] == now:
                ledger.release(name)
                completed.add(name)
                del active[name]
for event in ledger.events:
    event.pop('at')  # Runtime clock is irrelevant to the virtual schedule.
result = dict(basis='recorded 2026-10-25 durations, short stages at interval upper bounds, production admission',
    source_revision=revision or 'working tree', scheduler_sha256=hashlib.sha256(source('scripts/gate_schedule.py').encode()).hexdigest(),
    graph_sha256=hashlib.sha256(source('scripts/gate_graph.json').encode()).hexdigest(),
    graph_seconds=now, target_seconds=6000, target_met=now <= 6000,
    manager_lower_bound=sum(baseline['nodes'][n]['wall_seconds'] for n in ('mutation','unit.unconfined','integration.unconfined')),
    qualification='NOT RUN; projection excludes contention and shell overhead',
    intervals=intervals, claims=claims, capacities=capacity, peak_granted=ledger.peak, ledger=ledger.events)
print(json.dumps(result, indent=2))
