"""Replay only VELDO-0142, sequentially, including its exact registered falsifiers.

This is not the gate or the repository mutation driver. Restore each source in finally.
Run from this checkout with python3 proof/VELDO-0142/drive.py.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent
LOGS = ROOT / '.veldo/tmp/0142'
SUITE = '103_veldo_0142_git_identities'


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def run(name, observations):
    log = LOGS / (name + '.log')
    environment = dict(os.environ, VELDO_0142_OBSERVATIONS=str(observations), PYTHONDONTWRITEBYTECODE='1')
    with log.open('w') as stream:
        result = subprocess.run(['python3', 'scripts/selftest.py', '--suite', SUITE], cwd=ROOT,
                                env=environment, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
    lines = log.read_text().splitlines()
    return dict(exit=result.returncode, summary=[line for line in lines if line.startswith('selftest (PARTIAL')],
                failing_rows=[line.strip() for line in lines if 'SELFTEST FAIL:' in line],
                diagnostics=[line for line in lines if 'VELDO-0142 diagnostic' in line],
                log_sha256=digest(log.read_bytes()))


def main():
    LOGS.mkdir(parents=True, exist_ok=True)
    baseline = run('honest', PROOF / 'observations.json')
    assert baseline['exit'] == 2 and not baseline['failing_rows'], baseline
    records = []
    for case in json.loads((PROOF / 'falsifiers.json').read_text()):
        target = ROOT / '.veldo' / case['module']
        source = target.read_bytes()
        original = source.decode()
        assert original.count(case['old']) == 1, case['name']
        mutated = original.replace(case['old'], case['new'])
        diff = ''.join(difflib.unified_diff(original.splitlines(True), mutated.splitlines(True),
                                          fromfile='a/.veldo/' + case['module'], tofile='b/.veldo/' + case['module']))
        (PROOF / (case['name'] + '.diff')).write_text(diff)
        try:
            target.write_text(mutated)
            result = run(case['name'], LOGS / (case['name'] + '.json'))
        finally:
            target.write_bytes(source)
        expected = ['SELFTEST FAIL: VELDO-0142 ' + row for row in case['rows']]
        record = dict(name=case['name'], module=case['module'], source_sha256=digest(source),
                      mutant_sha256=digest(mutated.encode()), diff=case['name'] + '.diff', expected_rows=expected,
                      rejected=result['exit'] == 1 and all(row in result['failing_rows'] for row in expected), **result)
        records.append(record)
        print(case['name'], 'rejected' if record['rejected'] else 'NOT REJECTED', flush=True)
        assert record['rejected'], record
    packet = dict(schema='veldo.identity_scoped_checks/v1',
                  commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  suite=SUITE, suite_sha256=digest((ROOT / 'scripts/suites' / (SUITE + '.py')).read_bytes()),
                  baseline=baseline, mutations=records, full_gate_run=False, other_suites_run=False)
    (PROOF / 'verification.json').write_text(json.dumps(packet, indent=2) + '\n')
    print('Honest suite passes; all registered falsifiers fail their required assertion rows.', flush=True)


if __name__ == '__main__':
    main()
