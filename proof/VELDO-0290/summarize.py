#!/usr/bin/env python3
"""VELDO-0290: turn one heavy step's raw output into a small proof summary, then drop the raw files.

    python3 proof/VELDO-0290/summarize.py suite OUT ROOT COMMAND LOG RC [--red ROW ...] [--copied FILE ...]
    python3 proof/VELDO-0290/summarize.py raw OUT ROOT COMMAND RC PATH [PATH ...]

suite reads the log of one `python3 scripts/selftest.py --suite NAME` run made in ROOT. The log
names every failed row and the passed and failed counts. The verdict is pass when the VELDO-0290
rows that failed are exactly the --red rows (none for a green run) and no other row failed.
--copied names files of this checkout that were copied over ROOT's own before the run; their
digests are recorded.

raw records the name, size and sha256 of every file under each PATH for a step whose deciding
numbers are in another summary (the teeth run writes its own).

In both forms the summary's commit and tree are ROOT's, and the raw files are deleted once recorded.
"""
import argparse
import hashlib
import importlib.util
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parents[2]
PREFIX = 'VELDO-0290 admission/'


def validator():
    spec = importlib.util.spec_from_file_location('validate', HERE / '.veldo/validate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gather(paths):
    found = []
    for path in map(Path, paths):
        files = sorted(p for p in path.rglob('*') if p.is_file()) if path.is_dir() else [path] if path.is_file() else []
        found += [(str(p.relative_to(path.parent)), p.read_bytes()) for p in files]
    return found


def remove(paths):
    for path in map(Path, paths):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('kind', choices=('suite', 'raw'))
    parser.add_argument('out', type=Path)
    parser.add_argument('root', type=Path)
    parser.add_argument('command')
    parser.add_argument('rest', nargs='*')
    parser.add_argument('--red', nargs='*', default=[])
    parser.add_argument('--copied', nargs='*', default=[])
    arguments = parser.parse_args()
    write = validator().write_proof_summary
    if arguments.kind == 'raw':
        code, paths = int(arguments.rest[0]), arguments.rest[1:]
        raw = gather(paths)
        write(arguments.out, arguments.command, dict(exit_status=code, raw_files=len(raw)), discarded=raw,
              root=arguments.root, timing=True)
        remove(paths)
        print('%s: %d raw files recorded and dropped' % (arguments.out.name, len(raw)))
        return 0
    log, code = Path(arguments.rest[0]), int(arguments.rest[1])
    text = log.read_text(errors='replace')
    failed = [line.split('SELFTEST FAIL:', 1)[1].strip() for line in text.splitlines() if 'SELFTEST FAIL:' in line]
    total = re.search(r'^selftest \(.*?\): (\d+) passed, (\d+) failed', text, re.M)
    ours = sorted(row[len(PREFIX):] for row in failed if row.startswith(PREFIX))
    others = sorted(row for row in failed if not row.startswith(PREFIX))
    raised = [line.strip()[:300] for line in text.splitlines() if line.startswith('VELDO-0290 row raised')]
    expected = sorted(arguments.red)
    passed = bool(total) and ours == expected and not others and int(total.group(2)) == len(failed)
    deciding = dict(
        verdict='pass' if passed else 'FAIL', exit_status=code,
        rows_passed=int(total.group(1)) if total else None, rows_failed=int(total.group(2)) if total else None,
        expected_red=expected, observed_red=ours, other_failed_rows=others, rows_that_raised=raised,
        bound='the VELDO-0290 rows that failed are exactly the expected ones, and no other row failed',
        copied_over_root={name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in arguments.copied})
    write(arguments.out, arguments.command, deciding, discarded=[(log.name, log.read_bytes())],
          root=arguments.root, timing=True)
    log.unlink()
    print('%s: %s, red %s, others %d, %s passed' % (arguments.out.name, deciding['verdict'], ours, len(others),
                                                    deciding['rows_passed']))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
