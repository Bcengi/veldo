"""Run only the three VELDO-0080 acceptance checks, without the selftest prelude."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[2]
failed = []
seen = []

def expect(label, passed):
    seen.append(label)
    print(('PASS ' if passed else 'FAIL ') + label, flush=True)
    if not passed:
        failed.append(label)

suite = root / 'scripts/suites/113_veldo_0080_defects.py'
exec(compile(suite.read_text(), str(suite), 'exec'), {'ROOT': root, 'expect': expect})
assert set(seen) == {'VELDO-0080 defects/' + name for name in
                     ('ordinary-admission', 'ordinary-completion', 'no-automatic-admission')}
sys.exit(bool(failed))
