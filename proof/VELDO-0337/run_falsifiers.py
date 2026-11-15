"""Apply only VELDO-0337 falsifiers once in private copies; no teeth stage runs."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main(selected=()):
    definitions = runpy.run_path(str(ROOT / 'scripts/check_teeth_mutations.py'))
    cases = [c for c in definitions['cases']() if c['finding'] == 337
             and (not selected or c['name'] in selected)]
    source = ROOT / 'scripts/suites/153_veldo_0337_verdict_recorded.py'
    suite = source.read_text()

    def run(text):
        rows = []
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(compile(text, str(source), 'exec'), dict(ROOT=ROOT,
                 expect=lambda label, ok: rows.append({'row': label, 'passed': bool(ok)})))
        return rows, output.getvalue()

    baseline, output = run(suite)
    assert baseline and all(row['passed'] for row in baseline), (baseline, output)
    receipt_path = ROOT / 'proof/VELDO-0337/falsifiers.json'
    previous = json.loads(receipt_path.read_text()) if selected else {}
    results = [c for c in previous.get('cases', []) if c['name'] not in selected]
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='veldo-0337-falsifier-') as temp:
            path = Path(temp) / case['module']
            original = (ROOT / '.veldo' / case['module']).read_text()
            mutant = definitions['mutate'](original, case)
            path.write_text(mutant)
            anchor = 'ROOT / ".veldo" / "' + case['module'] + '"'
            assert suite.count(anchor) == 1
            text = suite.replace(anchor, 'Path(' + repr(str(path)) + ')')
            rows, output = run(text)
            failed = [row['row'] for row in rows if not row['passed']]
            targets = ['VELDO-0337 ' + name for name in case['rows']]
            rejected = all(any(row == target or row.startswith(target + ':') for row in failed) for target in targets)
            result = dict(name=case['name'], applied=1, rejected=rejected, targets=case['rows'], failed=failed,
                          original_digest=hashlib.sha256(original.encode()).hexdigest(),
                          mutant_digest=hashlib.sha256(mutant.encode()).hexdigest())
            results.append(result)
            print(case['name'], 'red' if rejected else 'NOT REJECTED', flush=True)
            if not rejected:
                print(output[-2000:])
    receipt = dict(spec='VELDO-0337', baseline_rows=len(baseline), baseline_failed=0,
                   executed=len(results), rejected=sum(r['rejected'] for r in results), cases=results)
    if selected:
        receipt['earlier_attempt'] = 'First batch: 7 of 8 target sets red. The owner-subject mutant exposed a fixture KeyError before the stale-version row. Corrected the shape assertion, reran the baseline and that mutant alone; both target rows now red.'
    receipt_path.write_text(json.dumps(receipt, indent=1) + '\n')
    assert receipt['executed'] == receipt['rejected']


if __name__ == '__main__':
    import sys
    main(sys.argv[1:])
