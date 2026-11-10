"""Run the ticket's checks under host_heavy.sh and retain only small summaries."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(name, data):
    data['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    data['coordinator_sha256'] = hashlib.sha256((ROOT / 'scripts/check_gate_mutations.py').read_bytes()).hexdigest()
    text = json.dumps(data, indent=2, sort_keys=True) + '\n'
    assert len(text.encode()) < 1_000_000
    (HERE / (name + '.json')).write_text(text)
    print(text, flush=True)


def unit():
    results = []
    for suite in ('98_veldo_0204_mutation_receipts', '115_veldo_0219_measured_admission'):
        command = ['python3', 'scripts/selftest.py', '--suite', suite]
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        lines = run.stdout.splitlines()
        summary = [line for line in lines if line.startswith('selftest (PARTIAL')
                   or line.strip().startswith(suite + ' ') or 'SELFTEST FAIL:' in line]
        passed = run.returncode == 2 and any('0 failed' in line for line in summary)
        results.append(dict(command=command, exit=run.returncode, passed=passed,
                            summary=summary, stderr_tail=run.stderr[-3000:]))
    save('unit', dict(passed=all(r['passed'] for r in results), results=results))
    return all(r['passed'] for r in results)


def integration():
    # Run the new suite 101 function itself. Its other functions invoke fixture gates.
    path = ROOT / 'scripts/suites/101_veldo_0208_landing_reuse.py'
    tree = ast.parse(path.read_text(), str(path))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_v289_timeout_cleanup')
    source = ast.get_source_segment(path.read_text(), function)
    anchor = 'ROOT / "scripts" / "check_gate_mutations.py"'
    assert source.count(anchor) == 1
    teeth = load(ROOT / 'scripts/check_teeth_mutations.py')
    case = next(c for c in teeth.cases() if c['name'] == 'cleanup289-replaces-first-error')
    current = (ROOT / 'scripts/check_gate_mutations.py').read_text()
    base = subprocess.check_output(['git', 'show', '852f133b:scripts/check_gate_mutations.py'], cwd=ROOT, text=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='v289-proof-', dir=HERE) as temporary:
        for name, text, expected in [('852f133b', base, False),
                                     (case['name'], teeth.mutate(current, case), False),
                                     ('current', current, True)]:
            module = Path(temporary) / (name + '.py')
            module.write_text(text)
            rows = []
            namespace = dict(ROOT=ROOT, expect=lambda label, ok: rows.append([label, bool(ok)]))
            exec(compile(source.replace(anchor, 'Path(' + repr(str(module)) + ')'), str(path), 'exec'), namespace)
            observed = namespace['_v289_timeout_cleanup']()
            matched = rows == [['VELDO-0289 ownership/timeout-then-cleanup-failure', expected]]
            results.append(dict(mode=name, expected=expected, rows=rows, observed=observed, passed=matched))
    save('integration', dict(passed=all(r['passed'] for r in results), results=results))
    return all(r['passed'] for r in results)


def teeth():
    command = ['python3', 'scripts/check_teeth_mutations.py', '--finding', '289',
               '--summary', str(HERE / 'teeth.json')]
    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    print(run.stdout.splitlines()[-1] if run.stdout else '', flush=True)
    if run.returncode:
        print(run.stderr[-3000:], flush=True)
        print(run.stdout[-6000:], flush=True)
    return run.returncode == 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('check', choices=('unit', 'integration', 'teeth', 'all'))
    args = parser.parse_args()
    checks = (unit, integration, teeth) if args.check == 'all' else (globals()[args.check],)
    for check in checks:
        if not check():
            sys.exit(1)
