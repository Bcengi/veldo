"""Reproduce the two process-boundary falsifiers using only specification suite 108.

Read registration data through the restricted AST audit, never import a mutation driver.
No network or service is needed. Full gate and consumer-suite kills remain unmeasured.
"""
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile


def main(output):
    root = Path(__file__).resolve().parents[2]
    audit = runpy.run_path(str(root / 'proof/VELDO-0153/audit_anchors.py'))
    cases, unresolved = audit['registrations']((root / 'scripts/check_teeth_mutations.py').read_text())
    if unresolved:
        raise AssertionError(unresolved)
    names = ('effects-transport-isolated-profile', 'effects-remote-host-unchecked')
    cases = {c['name']: c for c in cases if c['name'] in names}
    if set(cases) != set(names):
        raise AssertionError('missing process-boundary falsifier')
    runs = {}
    with tempfile.TemporaryDirectory(prefix='v153-process-', dir=os.environ['TMPDIR']) as directory:
        scratch = Path(directory)
        checkout = scratch / 'checkout'
        shutil.copytree(root, checkout, ignore=shutil.ignore_patterns('.git', '__pycache__', 'target'))
        temporary = scratch / 'tmp'
        temporary.mkdir()
        originals = {checkout / prefix / case['module']: (root / prefix / case['module']).read_text()
                     for case in cases.values() for prefix in ('.veldo', 'engine/.veldo')}
        for mode in (*names, 'restored'):
            for path, source in originals.items():
                if mode in cases and path.name == cases[mode]['module']:
                    case = cases[mode]
                    for old, new in [(case['old'], case['new']), *case['also']]:
                        if source.count(old) != 1:
                            raise AssertionError('nonunique registration anchor')
                        source = source.replace(old, new)
                path.write_text(source)
            command = [sys.executable, 'scripts/selftest.py', '--suite', '108_veldo_0153_executor_profile']
            log_path = scratch / (mode + '.log')
            with log_path.open('w') as log:
                result = subprocess.run(command, cwd=checkout, env=dict(os.environ, TMPDIR=str(temporary)),
                                        stdout=log, stderr=subprocess.STDOUT, timeout=120)
            lines = log_path.read_text().splitlines()
            failures = [line.strip() for line in lines if 'SELFTEST FAIL:' in line]
            summary = [line for line in lines if line.startswith('selftest (PARTIAL')]
            expected = [] if mode == 'restored' else ['SELFTEST FAIL: VELDO-0153 ' + row for row in cases[mode]['rows']]
            runs[mode] = dict(command=command, exit=result.returncode, failures=failures, summary=summary,
                              expected_failures=expected,
                              matched=set(failures) == set(expected) and bool(summary)
                              and result.returncode == (2 if mode == 'restored' else 1))
    ok = all(run['matched'] for run in runs.values())
    Path(output).write_text(json.dumps(dict(scope='suite 108 only; no gate or integration claim',
                                           verified=ok, runs=runs), indent=2) + '\n')
    print('process-boundary falsifiers: ' + str({name: run['matched'] for name, run in runs.items()}))
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
