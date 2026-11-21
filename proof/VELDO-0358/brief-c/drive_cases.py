"""Serial mutation proof using registered definitions and the authority observer.

This is a developer proof drive, not the required full mutation stage. Each row
runs baseline, no-op and mutant over disposable copies and records its actual
failed target labels. Logs and artifacts go to the caller's scratch directory.
"""
import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]


def load(name):
    path = ROOT / 'scripts' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    registry = load('check_teeth_mutations')
    observer = load('mutation_observer')
    gate = load('check_gate_mutations')
    cases = [c for c in registry.cases() if c['finding'] in (214, 215, 285, 358)
             and (not args.case or c['name'] in args.case)]
    failures = 0
    for c in cases:
        c = dict(c, driver='check_teeth_mutations.py', identity='check_teeth_mutations.py:' + c['name'])
        observations = {}
        with tempfile.TemporaryDirectory(prefix='brief-c-case-') as scratch:
            scratch = Path(scratch)
            for mode in ('baseline', 'noop', 'mutant'):
                prepared = observer.materialize(c, mode, scratch / mode)
                job = scratch / 'job.json'
                job.write_text(json.dumps([c, str(prepared['mutant']) if prepared['mutant'] else None]))
                command = ('import importlib.util,json,sys; '
                           's=importlib.util.spec_from_file_location("observer",sys.argv[1]); '
                           'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                           'c,p=json.load(open(sys.argv[2])); print(json.dumps(m.worker(c,p)))')
                result = observer.run_heavy([sys.executable, '-B', '-c', command,
                    str(ROOT / 'scripts/mutation_observer.py'), str(job)], cwd=ROOT,
                    env=__import__('os').environ)
                if result.returncode:
                    raise RuntimeError(c['name'] + '/' + mode + ': ' + result.stderr[-3000:])
                observations[mode] = json.loads(result.stdout)
            record = dict(schema=gate.SCHEMA, fixture_version=gate.FIXTURE_VERSION, case=c,
                          **observations, **{k: prepared[k] for k in
                              ('old_digest', 'new_digest', 'replacement_count')})
            try:
                gate.validate_result(record, c)
                status = 'rejected'
            except gate.Refused as error:
                status = error.code
                failures += 1
            before = prepared['source'].read_text()
            after = observer.mutate(before, c)
            (args.out / (c['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                before.splitlines(True), after.splitlines(True), fromfile=c['module'], tofile=c['module'], n=0)))
            print(json.dumps(dict(case=c['name'], status=status,
                controls=[observations[k]['failed_rows'] for k in ('baseline', 'noop')],
                failed=observations['mutant']['failed_rows'], kills=record.get('kills', []))), flush=True)
    return int(bool(failures))


if __name__ == '__main__':
    sys.exit(main())
