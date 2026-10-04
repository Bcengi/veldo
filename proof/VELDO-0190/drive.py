#!/usr/bin/env python3
"""Run only the current 0190 suite against archived pre-change production.
Overlay the suite and its harness, never production. Mutation execution belongs
to the reviewer. Every suite invocation uses the named selftest dispatcher.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '95_veldo_0190_owner_revisions'
PREFIX = 'VELDO-0190 '
MODULES = ('control_agent_config.py', 'control_owner_revisions.py', 'control_membership.py', 'control_service.py', 'init_scaffold.py')

spec = importlib.util.spec_from_file_location('v190_drive_git_process', ROOT / '.veldo/git_process.py')
_git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_git_process)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def red(commit):
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                               capture_output=True, text=True, check=True).stdout.strip()
    suite_path = Path('scripts/suites') / (SUITE + '.py')
    source = (ROOT / suite_path).read_text()
    names = next(ast.literal_eval(n.value) for n in ast.walk(ast.parse(source))
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'names' for t in n.targets))
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='v190-red-') as directory:
        tree = Path(directory) / 'tree'
        tree.mkdir()
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        modules = {'.veldo/' + m: dict(at_commit=sha(tree / '.veldo' / m), now=sha(ROOT / '.veldo' / m)) for m in MODULES}
        overlays = [suite_path, Path('proof/VELDO-0190/fixture.py'), Path('proof/VELDO-0190/journey.py')]
        for path in overlays:
            (tree / path).parent.mkdir(parents=True, exist_ok=True)
            (tree / path).write_bytes((ROOT / path).read_bytes())
        manifest_path = tree / 'scripts/suites/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        current = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
        manifest['suites'] = [s for s in manifest['suites'] if s['name'] != SUITE]
        manifest['suites'].append(next(s for s in current['suites'] if s['name'] == SUITE))
        manifest_path.write_text(json.dumps(manifest))
        requires_path = tree / 'scripts/suites/requires.json'
        requires = json.loads(requires_path.read_text())
        requires['requires'][SUITE] = [SUITE]
        requires_path.write_text(json.dumps(requires))
        command = ['python3', 'scripts/selftest.py', '--suite', SUITE]
        log_path = Path(directory) / 'suite.log'
        with log_path.open('w') as log:
            proc = subprocess.run(command, cwd=tree, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        output = log_path.read_text()
        # No production file is overlaid; record and check every affected module.
        assert all(sha(tree / path) == hashes['at_commit'] for path, hashes in modules.items())
    failed = [line.strip().removeprefix('SELFTEST FAIL: ') for line in output.splitlines()
              if line.strip().startswith('SELFTEST FAIL: ' + PREFIX)]
    details = [line.strip() for line in output.splitlines() if line.startswith(PREFIX) and 'detail:' in line]
    by_assertion = 'ran to its end' not in output and 'Traceback (most recent call last)' not in output
    compatibility = 'service/non-owner-malformed'
    compatible = output.splitlines().count(PREFIX + compatibility + ' compatibility: passed') == 1
    if (proc.returncode != 1 or not by_assertion or not compatible
            or failed != [PREFIX + name for name in names if name != compatibility]):
        raise SystemExit('Red proof requires owner rows red by assertion and base compatibility green: ' + output[-2000:])
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0190', suite=str(suite_path), commit=resolved,
                  tree='git archive %s; production unchanged; current suite, helpers and suite registration overlaid' % resolved,
                  command=command, modules=modules, suite_sha256=sha(ROOT / suite_path),
                  harness_sha256={str(p): sha(ROOT / p) for p in overlays[1:]},
                  by_assertion=by_assertion, rows=[[PREFIX + name, name == compatibility] for name in names],
                  failed_rows=failed, compatibility_rows=[PREFIX + compatibility],
                  details=details, seconds=round(time.monotonic() - started, 3), exit_code=proc.returncode,
                  log_sha256=hashlib.sha256(output.encode()).hexdigest())
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps(dict(commit=resolved, failed_rows=len(failed), by_assertion=by_assertion, written=name)))


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--red':
        raise SystemExit('Use the red mode. Mutation execution belongs to the reviewer.')
    red(sys.argv[2])
