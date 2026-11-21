"""Run one suite file's rows without the selftest dispatcher's shared checks.

python3 -I proof/VELDO-0125/run_suite.py <checkout root> <suite name>
"""
import sys
import ast
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
results = []


def expect(name, ok):
    results.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name, flush=True)


path = ROOT / 'scripts/suites' / (sys.argv[2] + '.py')
tree = ast.parse(path.read_text(), filename=path.name)
if len(sys.argv) > 3:
    selected = sys.argv[3]
    for node in ast.walk(tree):
        if (isinstance(node, ast.For) and isinstance(node.target, ast.Tuple)
                and len(node.target.elts) == 2 and isinstance(node.target.elts[1], ast.Name)
                and node.target.elts[1].id == 'test'):
            name = node.target.elts[0].id
            node.body.insert(0, ast.parse(f'if {name} != {selected!r}: continue').body[0])
    ast.fix_missing_locations(tree)
exec(compile(tree, path.name, 'exec'), {'ROOT': ROOT, 'expect': expect, '__name__': 'suite'})
print('passed %d failed %d' % (sum(r[1] for r in results), sum(not r[1] for r in results)))
sys.exit(0 if results and all(r[1] for r in results) else 1)
