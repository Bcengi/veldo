"""Run one suite file's rows without the selftest dispatcher's shared checks.

python3 -I proof/VELDO-0125/run_suite.py <checkout root> <suite name>
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
results = []


def expect(name, ok):
    results.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)


path = ROOT / 'scripts/suites' / (sys.argv[2] + '.py')
exec(compile(path.read_text(), path.name, 'exec'), {'ROOT': ROOT, 'expect': expect, '__name__': 'suite'})
print('passed %d failed %d' % (sum(r[1] for r in results), sum(not r[1] for r in results)))
sys.exit(0 if all(r[1] for r in results) else 1)
