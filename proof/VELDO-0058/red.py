#!/usr/bin/env python3
"""Run the CURRENT suite 69 over the pre-change gate and print every VELDO-0058 row.

    python3 -B proof/VELDO-0058/red.py 932d9b0 > proof/VELDO-0058/red-932d9b0.json
    python3 -B proof/VELDO-0058/red.py 35be8ff control_verification.py policy_check.py \
        > proof/VELDO-0058/red-35be8ff.json
    python3 -B proof/VELDO-0058/red.py b370581 lander.py control_verification.py policy_check.py \
        > proof/VELDO-0058/red-b370581.json

Module names after the commit choose which production anchors take that commit's bytes (verify.sh,
lander.py and executor.py when none are named). The second record is the policy-source finding: at
35be8ff the installed policy_check.py read the protected list from the candidate's own policy.yaml.
The third is the range-base finding: at b370581 the installed policy computed its push range from the
candidate workspace's own origin refs, and the candidate's state did not cover its refs.

At 932d9b0 scripts/verify.sh has no candidate mode (it verifies the checkout it lives in and writes
.veldo/last_verify and .veldo/events.jsonl there), GitLandOps.gate runs the candidate's own
scripts/verify.sh inside the candidate and finalize its own policy_check.py, and LiveLoop.gate runs the
workspace's own gate. The suite's production anchors for verify.sh, lander.py and executor.py are
pointed at that commit's bytes; control_verification.py, which no module of that commit loads, stays
installed and unused. Every other installed module is compared with that commit's copy and reported.
A row that fails reports its observation, never a crash: each region reds its rows on a raise, and a
`ran/` row says whether it did.
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
ALL_PATHS = {'verify.sh': 'scripts/verify.sh', 'lander.py': '.veldo/lander.py', 'executor.py': '.veldo/executor.py',
             'control_verification.py': '.veldo/control_verification.py',
             'policy_check.py': '.veldo/policy_check.py'}
DEFAULT = ('verify.sh', 'lander.py', 'executor.py')


def git(*args):
    return _git_process.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit, names=DEFAULT):
    PATHS = {name: ALL_PATHS[name] for name in names}
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - set(PATHS)
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    with tempfile.TemporaryDirectory(prefix='v58-red-') as directory:
        substitute = {}
        for name, rel in PATHS.items():
            path = Path(directory) / name
            path.write_bytes(git('show', '%s:%s' % (commit, rel)))
            substitute[name] = path
        rows, observed, _elapsed = run_suite(substitute)
    print(json.dumps({
        'production_at': commit, 'substituted': {name: '%s:%s' % (commit, rel) for name, rel in PATHS.items()},
        'installed_only_now': sorted(current - at_commit),
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in rows if not ok], 'passed': [n for n, ok in rows if ok],
        'raised': observed.get('raised'), 'observed': observed,
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '932d9b0', tuple(sys.argv[2:]) or DEFAULT)
