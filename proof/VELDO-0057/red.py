#!/usr/bin/env python3
"""Run the CURRENT suite 70 over the pre-change lander and print every VELDO-0057 row.

    python3 -B proof/VELDO-0057/red.py b53e7b1 > proof/VELDO-0057/red-b53e7b1.json

At b53e7b1 (the branch point, VELDO-0058 merged) lander.py has no landing: finalize pushes the candidate
itself, fast-forward only, and nothing writes a confirmed-landing receipt or runs the projection after
a landing; control_landing.py does not exist. The suite's production anchors take that commit's bytes:
lander.py is that commit's file, and control_landing.py is pointed at a path that does not exist, so the
suite installs none (as that commit installs none). Every other installed module is compared with that
commit's copy and reported. A row that fails reports its observation, never a crash: each region reds
its rows on a raise, and a `ran/` row says whether it did.
"""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, run_suite  # noqa: E402

_spec = importlib.util.spec_from_file_location('red_git', ROOT / '.veldo' / 'git_process.py')
_git_process = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_git_process)
PATHS = {'lander.py': '.veldo/lander.py', 'control_landing.py': '.veldo/control_landing.py'}


def git(*args, check=True):
    return _git_process.run(['git', '-C', str(ROOT), *args], check=check, capture_output=True)


def main(commit):
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').stdout.decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - set(PATHS)
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)).stdout)
    with tempfile.TemporaryDirectory(prefix='v57-red-') as directory:
        substitute, substituted = {}, {}
        for name, rel in PATHS.items():
            path = Path(directory) / name
            shown = git('show', '%s:%s' % (commit, rel), check=False)
            if shown.returncode == 0:
                path.write_bytes(shown.stdout)
                substituted[name] = '%s:%s' % (commit, rel)
            else:
                substituted[name] = 'absent at %s' % commit
            substitute[name] = path
        rows, observed, _elapsed = run_suite(substitute)
    print(json.dumps({
        'production_at': commit, 'substituted': substituted,
        'installed_only_now': sorted(current - at_commit),
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in rows if not ok], 'passed': [n for n, ok in rows if ok],
        'raised': observed.get('raised'), 'observed': observed,
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'b53e7b1')
