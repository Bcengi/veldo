"""Run one suite file's rows without the selftest dispatcher's shared checks.

python3 -I proof/VELDO-0125/run_suite.py <checkout root> <suite name>
"""
import sys
import ast
import importlib.util
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
# The suites name their hang bounds through WAITS (WAITS.WAIT_HANG_SECONDS), which the selftest dispatcher
# supplies. This driver supplies the same module, loaded the same way under the name `waits`, so a row's
# bounded wait reads the same bound here as in a gate run. The dispatcher's keeper and watchdog are not
# started: this process runs one suite's rows and its caller holds the hang detector.
spec = importlib.util.spec_from_file_location('waits', ROOT / 'scripts/suites/support/waits.py')
WAITS = importlib.util.module_from_spec(spec)
sys.modules['waits'] = WAITS
spec.loader.exec_module(WAITS)
exec(compile(tree, path.name, 'exec'), {'ROOT': ROOT, 'expect': expect, 'WAITS': WAITS, '__name__': 'suite'})
print('passed %d failed %d' % (sum(r[1] for r in results), sum(not r[1] for r in results)))
sys.exit(0 if results and all(r[1] for r in results) else 1)
