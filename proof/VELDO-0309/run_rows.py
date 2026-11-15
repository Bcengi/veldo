"""Record this ticket's rows as the suite gives them: one entry per row, in proof/VELDO-0309/rows.json.

The falsifiers are the registered cases of finding 309, run by the teeth tool
(python3 scripts/check_teeth_mutations.py --finding 309); falsifiers.json is written from its receipt:
python3 proof/VELDO-0309/run_rows.py RECEIPT, where RECEIPT is the file the tool's output was kept in.
No policy checker, confinement driver, engine or other suite is executed here.
"""
import contextlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/153_veldo_0309_gate_space.py'


def rows():
    result = []

    def expect(name, condition):
        result.append({'row': name, 'passed': bool(condition)})
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(SUITE.read_text(), str(SUITE), 'exec'), {'ROOT': ROOT, 'expect': expect, '__name__': 'proof'})
    return result


def falsifiers(receipt):
    text = Path(receipt).read_text()
    record = json.loads(next(line for line in text.splitlines() if line.startswith('{')))
    cases = []
    for entry in record['results']:
        case = entry['case']
        red = [name for name, good in entry['mutant']['observations'] if not good]
        cases.append({'name': case['name'], 'file': case['dir'] + '/' + case['module'], 'rows': case['rows'],
                      'red_rows': red,
                      'rejected': all(any(name.split()[-1] == row for name in red) for row in case['rows'])})
    return {'command': 'python3 scripts/check_teeth_mutations.py --finding 309', 'status': record['status'],
            'registered': record['registered'], 'executed': record['executed'], 'rejected': record['rejected'],
            'input_digest': record['input_digest'], 'cases': cases}


def main():
    if sys.argv[1:]:
        found = falsifiers(sys.argv[1])
        (PROOF / 'falsifiers.json').write_text(json.dumps(found, indent=2) + '\n')
        print('Falsifiers:', found['rejected'], 'of', found['registered'], 'rejected,', found['status'])
        return
    baseline = rows()
    (PROOF / 'rows.json').write_text(json.dumps(baseline, indent=2) + '\n')
    print('Rows:', sum(r['passed'] for r in baseline), 'passed,', sum(not r['passed'] for r in baseline), 'failed')
    if not baseline or any(not r['passed'] for r in baseline):
        raise SystemExit('rows refused')


if __name__ == '__main__':
    main()
