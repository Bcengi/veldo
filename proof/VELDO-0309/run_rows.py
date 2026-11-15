"""Run this ticket's rows and apply each registered falsifier once in private copies.

This is a small targeted proof runner, not the gate or the mutation coordinator.
No policy checker, confinement driver, engine, or other suite is executed.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/153_veldo_0309_gate_space.py'


def rows(source, only='all'):
    result = []
    def expect(name, condition):
        result.append({'row': name.split(':', 1)[0], 'passed': bool(condition),
                       'detail': name.partition(':')[2].strip()[:600] if not condition else ''})
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(source, str(SUITE), 'exec'), {'ROOT': ROOT, 'expect': expect, '__name__': 'proof',
                                                '_V309_ONLY': only})
    return result


def main():
    baseline = rows(SUITE.read_text())
    (PROOF / 'rows.json').write_text(json.dumps(baseline, indent=2) + '\n')
    print('Baseline:', sum(r['passed'] for r in baseline), 'passed,', sum(not r['passed'] for r in baseline),
          'failed', flush=True)
    if not baseline or any(not r['passed'] for r in baseline):
        raise SystemExit('baseline refused')
    spec = importlib.util.spec_from_file_location('definitions', ROOT / 'scripts/check_teeth_mutations.py')
    definitions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(definitions)
    results = []
    if sys.argv[1:] == ['remaining']:
        results = [r for r in json.loads((PROOF / 'falsifiers.json').read_text()) if r['rejected']]
    for case in (c for c in definitions.cases() if c['finding'] == 309):
        if any(r['name'] == case['name'] for r in results):
            continue
        with tempfile.TemporaryDirectory(prefix='veldo-0309-falsifier-') as directory:
            path = ROOT / case['dir'] / case['module']
            text = path.read_text()
            for old, new in [(case['old'], case['new'])] + list(case.get('also', [])):
                if text.count(old) != 1:
                    raise RuntimeError('anchor moved: ' + case['name'])
                text = text.replace(old, new)
            mutant = Path(directory) / case['module']
            mutant.write_text(text)
            anchor = 'ROOT / "' + case['dir'] + '" / "' + case['module'] + '"'
            source = SUITE.read_text()
            if source.count(anchor) != 1:
                raise RuntimeError('suite anchor moved: ' + case['name'])
            source = source.replace(anchor, 'Path(' + repr(str(mutant)) + ')')
            only = case['rows'][0].split('/')[0].upper()
            observed = rows(source, only if only.startswith('AC') else 'safe')
            red = [r['row'] for r in observed if not r['passed']]
            rejected = all('VELDO-0309 ' + row in red for row in case['rows']) and 'VELDO-0309 suite/completed' not in red
            results.append({'name': case['name'], 'applied': 1, 'rejected': rejected, 'red_rows': red})
            print(case['name'] + ': ' + ('rejected' if rejected else 'FAILED'), flush=True)
            (PROOF / 'falsifiers.json').write_text(json.dumps(results, indent=2) + '\n')
            if not rejected:
                print(json.dumps(observed, indent=2), flush=True)
                raise SystemExit('falsifier did not turn its row red')
    print('Falsifiers:', len(results), 'applied once, all rejected', flush=True)


if __name__ == '__main__':
    main()
