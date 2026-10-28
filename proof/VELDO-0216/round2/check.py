"""Round two regressions. Single ticket checks, no canonical gate."""
import importlib.util
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
s = importlib.util.spec_from_file_location('schedule', ROOT/'scripts/gate_schedule.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
g = json.loads((ROOT/'scripts/gate_graph.json').read_text())
checks = {}
checks['recorded-startup-estimates'] = all('estimate' in n for n in g['nodes'].values()) and hasattr(m, 'node_claim')
checks['host-lock-declared'] = all(n.get('host_lock') == 'shared' for n in g['nodes'].values())
checks['serial-reference'] = 'def run_serial(' in (ROOT/'scripts/suites/114_veldo_0216_concurrent_stages.py').read_text()
checks['footprint-owner-item'] = '.gitignore' in (ROOT/'proof/VELDO-0216/OPEN.md').read_text()
if hasattr(m, 'node_claim'):
    import contextlib, io
    capacity = dict(cpu=20, memory=15*2**30, manager=16)
    claims = {n:m.node_claim(node, None, capacity)[0] for n,node in g['nodes'].items()}
    ledger = m.Ledger(capacity, g['mutation_floor'])
    with contextlib.redirect_stdout(io.StringIO()):
        checks['cold-independent-overlap'] = ledger.acquire('mutation', claims['mutation'], mutation=True) and ledger.acquire('unit.confined', claims['unit.confined'])
        checks['manager-exclusion-preserved'] = not ledger.acquire('unit.unconfined', claims['unit.unconfined'])
        checks['host-lock-exclusion'] = not ledger.acquire('lock-mutator', dict(cpu=0, memory=0, manager='none', ports=[], host_lock='exclusive'))
        ledger.release('unit.confined'); ledger.release('mutation')
        checks['host-lock-release'] = ledger.acquire('lock-mutator', dict(cpu=0, memory=0, manager='none', ports=[], host_lock='exclusive')) and not ledger.acquire('unit.confined', claims['unit.confined'])
    fresh, source = m.node_claim(g['nodes']['unit.confined'], dict(cpu_rate=2, peak_anon_bytes=12345), capacity)
    checks['fresh-measurement-precedence'] = fresh['cpu']==2 and fresh['memory']==12345 and 'anonymous-memory' in source
    unknown, source = m.node_claim(dict(manager='none', ports=[]), None, capacity)
    checks['unknown-remains-conservative'] = unknown['cpu']==20 and unknown['memory']==15*2**30
    try:
        m.startup_estimate(dict(g['nodes']['unit.confined']['estimate'], cpu_seconds=-1))
        checks['invalid-estimate-refused'] = False
    except m.Refused:
        checks['invalid-estimate-refused'] = True
print(json.dumps(checks, indent=2))
raise SystemExit(not all(checks.values()))
