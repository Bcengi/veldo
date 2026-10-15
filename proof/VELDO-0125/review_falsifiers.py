#!/usr/bin/env python3
"""Review regressions: mutate an isolated module copy and run only the named 0125 suite."""
import argparse
import difflib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    'remote-cleanup': ('control_launch.py', 'AC3/remote-cleanup-held',
        '        if remote and (not never_contacted or dispatch_id in self.remote_retirements):',
        '        if False:'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case', choices=CASES)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    # Evidence is append-only: a new directory for each invocation.
    args.output.mkdir(parents=True, exist_ok=False)
    name, row, before, after = CASES[args.case]
    source = (ROOT / '.veldo' / name).read_text()
    assert source.count(before) == 1
    mutant = source.replace(before, after)
    (args.output / 'mutation.diff').write_text(''.join(difflib.unified_diff(
        source.splitlines(True), mutant.splitlines(True), fromfile=name, tofile=name)))
    with tempfile.TemporaryDirectory(prefix='v125-review-') as directory:
        modules = Path(directory) / '.veldo'
        shutil.copytree(ROOT / '.veldo', modules, ignore=shutil.ignore_patterns('__pycache__', 'tmp-*'))
        (modules / name).write_text(mutant)
        log = args.output / 'suite.log'
        with log.open('x') as out:
            result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '106_veldo_0125_routing'],
                cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, timeout=180,
                env=dict(os.environ, VELDO_0125_MODULES=str(modules), VELDO_0124_MODULES=str(modules)))
    caught = result.returncode == 1 and 'SELFTEST FAIL: VELDO-0125 ' + row in log.read_text()
    print(args.case + ': ' + ('rejected by ' + row if caught else 'SURVIVED'))
    return 0 if caught else 1


if __name__ == '__main__':
    sys.exit(main())
