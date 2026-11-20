#!/usr/bin/env python3
"""Drive each native Mac falsifier red, then restore the unmutated module and observe green."""
import difflib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parent
ROOT = BUNDLE.parents[1]


def load_base_mutants():
    spec = importlib.util.spec_from_file_location('v124_native_falsifiers', BUNDLE / 'native_falsifiers.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    extra = (
        ('session-type', 'project_runner_macos_os.py',
         "                    LimitLoadToSessionType='Background',\n", '',
         'lifecycle', 'natural'),
        ('supervisor-deadline', 'project_runner_macos.py',
         "if now >= self.deadline and self.stage in (None, 'cooperative'):",
         "if False and self.stage in (None, 'cooperative'):",
         'lifecycle', 'deadline'),
    )
    return tuple(module.MUTANTS) + extra


def run_suite(target, suite):
    child = subprocess.run(
        [sys.executable, str(BUNDLE / 'native_checks.py'), suite, 'claude_code'],
        env=dict(os.environ, VELDO_0124_MODULES=str(target), PYTHONDONTWRITEBYTECODE='1'),
        capture_output=True, text=True, timeout=600,
    )
    payload = json.loads(child.stdout)
    rows = {r['row']: r for r in payload.get('rows', ())}
    return child.returncode, payload, rows


def main():
    if sys.platform != 'darwin':
        print(json.dumps(dict(status='not_run', reason='requires_real_macos')))
        return 2
    work = ROOT / 'runs'
    work.mkdir(exist_ok=True)
    mutants = load_base_mutants()
    records = []
    for name, filename, before, after, suite, row in mutants:
        original_path = ROOT / '.veldo' / filename
        source = original_path.read_text()
        assert source.count(before) == 1, name
        changed = source.replace(before, after)
        patch = ''.join(difflib.unified_diff(
            source.splitlines(True), changed.splitlines(True),
            fromfile='a/' + filename, tofile='b/' + filename, n=0,
        ))
        source_sha = hashlib.sha256(source.encode()).hexdigest()
        mutant_sha = hashlib.sha256(changed.encode()).hexdigest()
        row_key = 'native/claude_code/' + row
        with tempfile.TemporaryDirectory(prefix='rg-' + name + '-', dir=work) as temporary:
            target = Path(temporary)
            for path in (ROOT / '.veldo').glob('*.py'):
                shutil.copyfile(path, target / path.name)
            (target / filename).write_text(changed)
            red_rc, red_payload, red_rows = run_suite(target, suite)
            red_named = red_rows.get(row_key, {})
            red_ok = (red_rc == 1 and red_named.get('status') == 'failed')

            (target / filename).write_text(source)
            restored_sha = hashlib.sha256((target / filename).read_bytes()).hexdigest()
            assert restored_sha == source_sha, name
            green_rc, green_payload, green_rows = run_suite(target, suite)
            green_named = green_rows.get(row_key, {})
            green_ok = (
                green_rc == 0
                and green_payload.get('status') == 'passed'
                and green_named.get('status') == 'passed'
            )

        both_ok = red_ok and green_ok
        records.append(dict(
            name=name,
            file=filename,
            suite=suite,
            row=row_key,
            source_sha256=source_sha,
            mutant_sha256=mutant_sha,
            restored_sha256=restored_sha,
            red=dict(
                exit_code=red_rc,
                row_status=red_named.get('status'),
                error=red_named.get('error') or red_payload.get('error'),
                observed=red_named.get('observed'),
                rejected=red_ok,
            ),
            green_restored=dict(
                exit_code=green_rc,
                suite_status=green_payload.get('status'),
                row_status=green_named.get('status'),
                restored=green_ok,
            ),
            red_then_green=both_ok,
            patch=patch,
        ))
        state = 'RED_THEN_GREEN' if both_ok else 'FAILED'
        print(name, state, row_key, file=sys.stderr, flush=True)
    overall = 'passed' if all(r['red_then_green'] for r in records) else 'failed'
    print(json.dumps(dict(
        schema='veldo.macos_native_falsifiers_red_green/v1',
        kind='native',
        count=len(records),
        status=overall,
        falsifiers=records,
    ), indent=2))
    return 0 if overall == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
