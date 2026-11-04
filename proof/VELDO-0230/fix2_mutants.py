"""Run named VELDO-0160 mutants through proof/VELDO-0160/drive.py's runner (no proof files written)."""
import importlib.util, json, sys, tempfile
from pathlib import Path
root = Path(sys.argv[1]).resolve()
names = sys.argv[2].split(',')
def load(n, p):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
D = load('d160', root / 'proof/VELDO-0160/drive.py')
ctm = D._driver()
cases = {c['name']: c for c in ctm.cases() if c['finding'] == 160}
base = D.run()
print('baseline failed=%s rows=%d' % (base['failed_rows'], len(base['rows'])))
with tempfile.TemporaryDirectory(prefix='v0230-fix2-mut-') as directory:
    noop_case = cases[names[0]]
    noop = ctm.materialize(noop_case, 'noop', Path(directory) / 'noop')
    n = D.run({noop_case['module']: str(noop['mutant'])})
    print('noop control_engine_claude.py failed=%s' % n['failed_rows'])
    for name in names:
        case = cases[name]
        prepared = ctm.materialize(case, 'mutant', Path(directory) / name)
        o = D.run({case['module']: str(prepared['mutant'])})
        killed = all(D.PREFIX + r in o['failed_rows'] for r in case['rows'])
        print('%-40s %s rows=%s failed=%s' % (name, 'KILLED' if killed else 'SURVIVED', case['rows'],
                                               [r[len(D.PREFIX):] for r in o['failed_rows']]))
