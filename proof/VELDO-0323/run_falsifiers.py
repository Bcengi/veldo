"""Apply every ticket-local falsifier, sequentially, without the gate or teeth stage.

The registry supplies definitions only. Each temporary production copy runs suite 153 with
its two declared inputs, ROOT and expect. Exceptions and missing target rows are errors.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    spec = importlib.util.spec_from_file_location('definitions', ROOT / 'scripts/check_teeth_mutations.py')
    definitions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(definitions)
    cases = [case for case in definitions.cases() if case['finding'] == 323]
    summaries = []
    for case in cases:
        before = (ROOT / '.veldo' / case['module']).read_text()
        if before.count(case['old']) != 1:
            raise ValueError('mutation anchor moved: ' + case['name'])
        after = before.replace(case['old'], case['new'])
        observed, output, started = {}, io.StringIO(), time.monotonic()
        with tempfile.TemporaryDirectory(prefix='veldo-0323-falsifier-') as folder:
            mutant = Path(folder) / case['module']
            mutant.write_text(after)
            suite = ROOT / 'scripts/suites' / case['suite']
            source = suite.read_text()
            anchor = 'ROOT / ".veldo" / "' + case['module'] + '"'
            if source.count(anchor) != 1:
                raise ValueError('suite anchor moved: ' + case['name'])
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(str(mutant)) + ')')
            try:
                with contextlib.redirect_stdout(output):
                    exec(compile(source, str(suite), 'exec'), {'ROOT': ROOT,
                         'expect': lambda name, ok: observed.update({name: bool(ok)})})
                targets = {name: observed.get('VELDO-0323 ' + name) for name in case['rows']}
                status = 'rejected' if targets and all(value is False for value in targets.values()) else 'error'
                error = None
            except Exception as failure:
                targets, status, error = {}, 'error', repr(failure)
        summaries.append(dict(name=case['name'], status=status, targets=targets, error=error,
            before=hashlib.sha256(before.encode()).hexdigest(), after=hashlib.sha256(after.encode()).hexdigest(),
            seconds=round(time.monotonic() - started, 3),
            failed_rows=[name for name, ok in observed.items() if not ok], detail=output.getvalue()[-4000:]))
        print(case['name'] + ': ' + status, flush=True)
    (HERE / 'falsifiers.json').write_text(json.dumps(summaries, indent=1) + '\n')
    return 0 if summaries and len(summaries) == len(cases) and all(row['status'] == 'rejected' for row in summaries) else 1


if __name__ == '__main__':
    raise SystemExit(main())
