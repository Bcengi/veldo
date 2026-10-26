"""VELDO-0143 round 2: one suite run on a copy of a commit (git archive, never the working tree), with what this
sandbox lacks stood in for, each only when asked, and optional textual replacements (a falsifier) applied to the
copy first. Prints and writes a JSON record: the commit, what was stood in for, the replacements, the suite's
table count, its SELFTEST FAIL rows and its detail lines.

    python3 proof/VELDO-0143/round2/sandbox_run.py <commit> <suite> <output.json> [--stage] [--agent]
                                                   [--replace <path> <old> <new>]...

--stage   the graph runtime's stage directory is the account's (~/.local/state/veldo/graph-stage), which this
          sandbox may not write; the copy's .veldo/control_graph.py names a stage under the run's temporary
          directory instead, so the installed LangGraph runtime itself runs (pm/new-project-run).
--agent   this sandbox refuses AF_UNIX, so the identity wire's fence runs without its recording SSH agent. A
          stand-in ssh-keygen first on PATH records, as the host's agent does, every `ssh-keygen -Y sign` started
          with the fence's agent named in SSH_AUTH_SOCK (a HermeticViolation 'the SSH agent was contacted by:
          ...' in that wire's log), then runs the real ssh-keygen. On the host the real agent records it.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
args = sys.argv[1:]
commit, suite, out = args[:3]
flags, replacements, i = set(), [], 3
while i < len(args):
    if args[i] == '--replace':
        replacements.append(tuple(args[i + 1:i + 4]))
        i += 4
    else:
        flags.add(args[i])
        i += 1
STAGE_OLD = "'stage': str(lock.account_home() / STAGE_RELATIVE if home is None else Path(home) / STAGE_RELATIVE)}"
AGENT = '''#!%(python)s
import json, os, sys
from pathlib import Path
sock = os.environ.get('SSH_AUTH_SOCK') or ''
if sys.argv[1:3] == ['-Y', 'sign'] and sock.endswith('/no-agent/agent'):
    with open(Path(sock).parent.parent / 'hermetic-violations.jsonl', 'a') as log:
        log.write(json.dumps({'kind': 'keyring', 'detail': 'the SSH agent was contacted by: ssh-keygen '
                              + ' '.join(sys.argv[1:])[:280]}) + '\\n')
os.execv(%(real)r, [%(real)r] + sys.argv[1:])
'''

with tempfile.TemporaryDirectory(prefix='v143r2-') as directory:
    tree = Path(directory) / 'tree'
    tree.mkdir()
    archive = subprocess.run(['git', '-C', str(ROOT), 'archive', commit], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
    env = dict(os.environ)
    for path, old, new in replacements:
        text = (tree / path).read_text()
        if text.count(old) != 1:
            raise SystemExit('replacement not found exactly once in %s' % path)
        (tree / path).write_text(text.replace(old, new))
    if '--stage' in flags:
        stage = Path(directory) / 'graph-stage'
        stage.mkdir(mode=0o700)
        graph = tree / '.veldo' / 'control_graph.py'
        graph.write_text(graph.read_text().replace(STAGE_OLD, "'stage': %r}" % str(stage)))
    if '--agent' in flags:
        shim = Path(directory) / 'agent'
        shim.mkdir()
        (shim / 'ssh-keygen').write_text(AGENT % {'python': sys.executable, 'real': shutil.which('ssh-keygen')})
        (shim / 'ssh-keygen').chmod(0o700)
        env['PATH'] = str(shim) + os.pathsep + env['PATH']
    done = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', suite], cwd=tree, env=env,
                          capture_output=True, text=True, timeout=3600)
    text = (done.stdout + done.stderr).replace(directory, '<tmp>').replace(tempfile.gettempdir(), '<tmp>')
table = re.search(r'^\s+%s\s+(\d+) passed' % re.escape(suite), text, re.M)
lines = [line.strip() for line in text.splitlines()]
record = {'commit': subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', commit], capture_output=True,
                                   text=True).stdout.strip(),
          'suite': suite, 'stood_in': sorted(flags), 'replacements': [list(r) for r in replacements],
          'passed': int(table.group(1)) if table else None,
          'failed_rows': [line[len('SELFTEST FAIL: '):] for line in lines if line.startswith('SELFTEST FAIL: ')],
          'details': [line[:600] for line in lines if ' detail: ' in line], 'exit': done.returncode}
Path(out).write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
print(json.dumps({k: record[k] for k in ('commit', 'stood_in', 'passed', 'failed_rows')}))
