"""Exact selected-case verdict comparison with completed records from a prior host gate."""
import json
from pathlib import Path
import sys


def verdict(record):
    return dict(case=record['case'], old_digest=record['old_digest'], new_digest=record['new_digest'],
                replacement_count=record['replacement_count'],
                observations={mode: record[mode]['observations'] for mode in ('baseline', 'noop', 'mutant')},
                kill_by=record['kill_by'], kills=record['kills'])


def compare(expected, receipt):
    names = {v['case']['name'] for v in expected}
    actual = [verdict(r) for r in receipt['results']]
    checks = dict(
        complete=receipt['status'] == 'passed' and receipt['scope'] == 'selected'
            and receipt['registered'] == receipt['executed'] == receipt['rejected'] == len(expected)
            and len(names) == len(expected) == len(actual),
        fresh=receipt['reused'] == 0 and receipt['force_fresh'] is True,
        clean=not receipt['invalid_results'] and receipt['surviving_workers'] == 0
            and not receipt['qualification_ledger']['held']
            and all(not w.get('error') and w.get('scratch_removed') is True
                    and not any(w.get('cleanup', {}).values()) for w in receipt['worker_outcomes']),
        validated=len(receipt['case_receipts']) == len(expected)
            and all(r['validated'] for r in receipt['case_receipts']),
        verdicts=sorted(actual, key=lambda r: r['case']['identity'])
            == sorted(expected, key=lambda r: r['case']['identity']))
    return dict(passed=all(checks.values()), checks=checks,
                cases=len(expected), elapsed=receipt['elapsed'], workers=receipt['worker_invocations'],
                peak_workers=receipt['peak_workers'], ledger=receipt['qualification_ledger'],
                input_digest=receipt['input_digest'], implementation_digest=receipt['implementation_digest'])


if __name__ == '__main__':
    answer = compare(json.loads(Path(sys.argv[1]).read_text()), json.loads(Path(sys.argv[2]).read_text()))
    print(json.dumps(answer, indent=2, sort_keys=True))
    sys.exit(0 if answer['passed'] else 1)
