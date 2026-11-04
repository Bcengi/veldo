"""VELDO-0230 fix round 3: run named mutants of scripts/check_teeth_mutations.py in a scratch git worktree.

    python3 proof/VELDO-0230/fix3_mutants.py <scratch worktree at the commit under test> <name,name,...>

For each case: the suite's baseline and a no-op copy, then the mutant written over its module in the scratch
tree (materialize's exact replacement), the case's suite run there by `python3 scripts/selftest.py --suite`, the
failed rows read from its output, and the module's bytes restored. The repository under test is never edited.
"""
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile

tree = Path(sys.argv[1]).resolve()
names = sys.argv[2].split(',')
spec = importlib.util.spec_from_file_location('ctm', tree / 'scripts/check_teeth_mutations.py')
ctm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctm)
cases = {c['name']: c for c in ctm.cases()}


def failed(suite):
    done = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', suite[:-3]], cwd=tree,
                          capture_output=True, text=True, timeout=900)
    return sorted(set(re.findall(r'SELFTEST FAIL: VELDO-\d+ (\S+)', done.stdout + done.stderr)))


baselines = {}
with tempfile.TemporaryDirectory(prefix='v0230-fix3-mut-') as directory:
    for name in names:
        case = cases[name]
        prepared = ctm.materialize(case, 'mutant', Path(directory) / name, root=tree)
        source = Path(prepared['source'])
        original = source.read_bytes()
        if case['suite'] not in baselines:
            baselines[case['suite']] = failed(case['suite'])
            noop = ctm.materialize(case, 'noop', Path(directory) / (name + '-noop'), root=tree)
            source.write_bytes(Path(noop['mutant']).read_bytes())
            try:
                print('%s baseline failed=%s noop failed=%s' % (case['suite'], baselines[case['suite']], failed(case['suite'])))
            finally:
                source.write_bytes(original)
        source.write_bytes(Path(prepared['mutant']).read_bytes())
        try:
            rows = failed(case['suite'])
        finally:
            source.write_bytes(original)
        killed = all(r in rows and r not in baselines[case['suite']] for r in case['rows'])
        print('%-40s %s rows=%s failed=%s' % (name, 'KILLED' if killed else 'SURVIVED', case['rows'], rows), flush=True)
