"""VELDO-0161 round 5: the rows that fail without each fix. Suite 109 as it is at <suite-commit>, run in a copy of
that commit with the adoption modules put back as they were at <unfixed-commit> (before N1 and N2), and once
with them as they are at <suite-commit>. The checkout is never edited; each copy is `git archive` output in a
fresh temporary directory.

    python3 proof/VELDO-0161/round5/run_unfixed.py <checkout> <output.json> <suite-commit> <unfixed-commit>
"""
import json, re, subprocess, sys, tarfile, tempfile, io
from pathlib import Path

root, out, suite_commit, unfixed_commit = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
MODULES = ['%s/control_repository_provisioner.py', '%s/control_effect_executor_adoption.py']


def git(*args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=True).stdout


def run(modules_at):
    with tempfile.TemporaryDirectory(prefix='veldo-161-r5-') as d:
        tarfile.open(fileobj=io.BytesIO(git('archive', suite_commit))).extractall(d, filter='data')
        for prefix in ('engine/.veldo', '.veldo'):
            for module in MODULES:
                Path(d, module % prefix).write_bytes(git('show', '%s:%s' % (modules_at, module % prefix)))
        done = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '109_veldo_0161_adoption'],
                              cwd=d, capture_output=True, text=True, timeout=1800)
    text = done.stdout + done.stderr
    return {'modules_at': modules_at, 'exit': done.returncode,
            'failed_rows': re.findall(r'SELFTEST FAIL: (VELDO-0161 \S+)', text),
            'details': [line.strip() for line in text.splitlines()
                        if 'detail:' in line and ('transport-config' in line or 'repository-commands' in line)],
            'summary': [line.strip() for line in text.splitlines() if line.startswith('selftest')]}


result = {'suite_commit': suite_commit, 'unfixed': run(unfixed_commit), 'fixed': run(suite_commit)}
out.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
for key in ('unfixed', 'fixed'):
    print(key, result[key]['summary'], result[key]['failed_rows'])
