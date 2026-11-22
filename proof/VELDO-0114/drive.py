#!/usr/bin/env python3
"""Drive VELDO-0114's registered teeth cases (finding 114) outside the gate's confinement.

The census needs ptrace, which the confined mutation worker refuses, so this runs the registry's
own materialize() and worker() directly: a baseline of each original suite, then per case a no-op
copy and the mutant, each in a fresh interpreter. A case counts only when the baseline target is
[True], the no-op rows equal the baseline and the mutant's target rows are exactly [False] in an
otherwise completed run. A crash, missing row or timeout is an invalid drive, never a detection.
Writes results.json and one applied diff per case beside this file.

  python3 -B proof/VELDO-0114/drive.py
"""
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
import check_teeth_mutations as T  # noqa: E402

HANG = 1800  # a hang detector for a whole suite run, never a pass condition


def run(case, mutant=None):
    argv = [sys.executable, '-B', str(ROOT / 'scripts/check_teeth_mutations.py'), '--worker', case['name']]
    if mutant:
        argv += ['--mutant', str(mutant)]
    done = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT, timeout=HANG)
    try:
        return json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return dict(error=done.returncode, stderr=done.stderr[-2000:])


def targets(record, case):
    return {label: [ok for name, ok in record.get('observations', []) if name.split()[-1] == label]
            for label in case['rows']}


def main():
    cases = [c for c in T.cases() if c['finding'] == 114]
    results = []
    with tempfile.TemporaryDirectory(prefix='v114-drive-') as scratch:
        baselines = {}
        for case in cases:
            if case['suite'] not in baselines:
                baselines[case['suite']] = run(case)
            baseline = baselines[case['suite']]
            m = T.materialize(case, 'baseline', None)
            before = m['source'].read_text()
            (OUT / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                before.splitlines(True), T.mutate(before, case).splitlines(True),
                str(m['source'].relative_to(ROOT)), str(m['source'].relative_to(ROOT)) + ' (mutant)')))
            noop = T.materialize(case, 'noop', Path(scratch) / (case['name'] + '-noop'))
            noop_rows = run(case, noop['mutant'])
            broken = T.materialize(case, 'mutant', Path(scratch) / (case['name'] + '-mutant'))
            mutant_rows = run(case, broken['mutant'])
            honest = baseline.get('observations')
            verdict = (honest is not None and all(ok for _, ok in honest)
                       and noop_rows.get('observations') == honest
                       and all(v == [True] for v in targets(baseline, case).values())
                       and all(v == [False] for v in targets(mutant_rows, case).values())
                       and mutant_rows.get('count') == baseline.get('count'))
            results.append(dict(case=case['name'], suite=case['suite'], module=case['module'], rows=case['rows'],
                                old_digest=broken['old_digest'], new_digest=broken['new_digest'],
                                baseline_targets=targets(baseline, case),
                                noop_equals_baseline=noop_rows.get('observations') == honest,
                                mutant_targets=targets(mutant_rows, case),
                                mutant_failed_rows=mutant_rows.get('failed_rows'),
                                mutant_error=mutant_rows.get('error'), detected=verdict))
    record = dict(schema='veldo.v114-drive/v1',
                  baseline_rows={k: b.get('observations') for k, b in baselines.items()},
                  baseline_error={k: b.get('error') for k, b in baselines.items()}, cases=results,
                  all_detected=all(r['detected'] for r in results) and len(results) == 5)
    (OUT / 'results.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    for r in results:
        print(r['case'], 'detected' if r['detected'] else 'NOT DETECTED', r['mutant_targets'])
    print('all detected' if record['all_detected'] else 'DRIVE FAILED')
    return 0 if record['all_detected'] else 1


if __name__ == '__main__':
    sys.exit(main())
