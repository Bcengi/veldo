"""Drive each named row green, then red under one isolated source mutation."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from port_verify import ROOT, sanitize


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    # VELDO_0125_FALSIFIER_CASES names another cases file (the driver's own check of invalid mutants).
    cases = json.loads(Path(os.environ.get('VELDO_0125_FALSIFIER_CASES',
                                           Path(__file__).with_name('port-falsifiers.json'))).read_text())
    results, greens = [], {}
    for name, case in cases.items():
        if len(sys.argv) > 2 and name not in sys.argv[2:]:
            continue
        command = [sys.executable, '-I', 'proof/VELDO-0125/run_suite.py', str(ROOT), case['suite'], case['row']]
        key = (case['suite'], case['row'])
        if key not in greens:
            green = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
            greens[key] = (green.returncode, green.stdout + green.stderr)
        green_code, green_log = greens[key]
        source = (ROOT / case.get('source', '.veldo/' + case['file'])).read_text()
        assert source.count(case['before']) == 1, name
        changed = source.replace(case['before'], case['after'])
        (output / (name + '.diff')).write_text(''.join(difflib.unified_diff(
            source.splitlines(True), changed.splitlines(True), fromfile=case['file'], tofile=case['file'], n=2)))
        try:
            # A mutant that does not compile fails at load, never at its row: it is invalid, not a rejection.
            compile(changed, case['file'], 'exec')
        except SyntaxError as error:
            (output / (name + '.txt')).write_text('INVALID MUTANT: ' + type(error).__name__ + ': ' + str(error) + '\n')
            results.append(dict(case=name, suite=case['suite'], row=case['row'], rejected=False, invalid_mutant=True,
                                green_exit=green_code, mutant_exit=None,
                                source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                                mutant_sha256=hashlib.sha256(changed.encode()).hexdigest()))
            (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
            print(name, 'INVALID_MUTANT', flush=True)
            continue
        with tempfile.TemporaryDirectory(prefix='v125-port-mutant-') as temporary:
            target = Path(temporary)
            for path in (ROOT / '.veldo').glob('*.py'):
                shutil.copyfile(path, target / path.name)
            (target / case['file']).write_text(changed)
            env = dict(os.environ, VELDO_0124_MODULES=str(target), VELDO_0125_MODULES=str(target),
                       PYTHONDONTWRITEBYTECODE='1')
            if case.get('override'):
                env[case['override']] = str(target / case['file'])
            try:
                red = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, env=env, timeout=300)
                red_code, red_log = red.returncode, red.stdout + red.stderr
            except subprocess.TimeoutExpired as error:
                red_code, red_log = 124, 'Hang detector expired; not a named rejection.\n'
        marker = 'FAIL ' + case['ticket'] + ' ' + case['row']
        rejected = green_code == 0 and red_code == 1 and marker in red_log
        (output / (name + '.txt')).write_text('GREEN exit=' + str(green_code) + '\n' + sanitize(green_log) +
            '\nMUTANT exit=' + str(red_code) + '\n' + sanitize(red_log))
        results.append(dict(case=name, suite=case['suite'], row=case['row'], rejected=rejected,
                            green_exit=green_code, mutant_exit=red_code,
                            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                            mutant_sha256=hashlib.sha256(changed.encode()).hexdigest()))
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name, 'REJECTED' if rejected else 'NOT_REJECTED', flush=True)
    return 0 if results and all(r['rejected'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
