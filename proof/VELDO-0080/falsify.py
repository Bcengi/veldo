"""Drive this ticket's falsifiers in private source copies. Run under the host flock."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES = [
    ('AC1', 'label-admits', 'control_backlog_priority.py',
     "    held = (unit if isinstance(unit, dict) else {}).get('state')",
     "    if (item or {}).get('work_class') == 'POLICY_DEFECT':\n        return []\n    held = (unit if isinstance(unit, dict) else {}).get('state')",
     'defects/ordinary-admission'),
    ('AC2', 'missing-review-completes', 'dispatch.py',
     '    passing = sorted({r["reviewer"] for r in record["reviews"] if r["attempt"] == attempt and r["passes"]})',
     '    passing = sorted({r["reviewer"] for r in record["reviews"] if r["attempt"] == attempt and r["passes"]}) or ["w-rev"]',
     'defects/ordinary-completion'),
    ('AC3', 'model-claim-admits', 'control_grooming_request.py',
     "    reasons = []\n    if ((fields.get('evidence') or {}).get('defect') or {}).get('scope_changes'):",
     "    reasons = []\n    if ((fields.get('evidence') or {}).get('defect') or {}).get('reproduction'):\n        return OWN_MESSAGE, []\n    if ((fields.get('evidence') or {}).get('defect') or {}).get('scope_changes'):",
     'defects/no-automatic-admission'),
    ('AC1', 'severity-lost', 'control_defect.py',
     "    return {'severity': severity, 'reproduction': reproduction, 'scope_changes': list(changes),",
     "    return {'severity': 'low', 'reproduction': reproduction, 'scope_changes': list(changes),",
     'defects/ordinary-admission'),
    ('AC1', 'report-unbound', 'control_grooming_request.py',
     "                     'acceptance': accepted, **({'defect': DF.evidence(item)} if DF.evidence(item) is not None else {})},",
     "                     'acceptance': accepted},",
     'defects/ordinary-admission'),
    ('AC3', 'scope-change-admits', 'control_grooming_request.py',
     "    if ((fields.get('evidence') or {}).get('defect') or {}).get('scope_changes'):",
     "    if False:",
     'defects/no-automatic-admission'),
]
results = []
with tempfile.TemporaryDirectory(prefix='v80-mutants-') as scratch:
    for ac, name, filename, old, new, row in CASES:
        source = (ROOT / '.veldo' / filename).read_text()
        if source.count(old) != 1:
            raise AssertionError('mutation anchor count: ' + name)
        changed = source.replace(old, new, 1)
        target = Path(scratch) / filename
        target.write_text(changed)
        (HERE / (name + '.diff')).write_text(''.join(difflib.unified_diff(source.splitlines(True), changed.splitlines(True),
            fromfile='.veldo/' + filename, tofile='mutant/' + filename)))
        env = dict(os.environ, VELDO_0080_MUTANTS=json.dumps({filename: str(target)}))
        env.pop('VELDO_0080_EVIDENCE', None)
        result = subprocess.run([sys.executable, str(HERE / 'run.py')], cwd=ROOT, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (HERE / (name + '.red.log')).write_text(result.stdout)
        killed = result.returncode == 1 and 'FAIL VELDO-0080 ' + row in result.stdout and 'Traceback' not in result.stdout
        results.append(dict(ac=ac, mutation=name, target='.veldo/' + filename, row=row, exit=result.returncode,
                            killed=killed, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                            mutant_sha256=hashlib.sha256(changed.encode()).hexdigest()))
        print(name + ': ' + ('RED as required' if killed else 'NOT KILLED'), flush=True)
        if not killed:
            print(result.stdout, flush=True)
    # The same checks must be green after all private mutations have gone away.
    env = dict(os.environ, VELDO_0080_EVIDENCE=str(HERE / 'observations.json'))
    env.pop('VELDO_0080_MUTANTS', None)
    green = subprocess.run([sys.executable, str(HERE / 'run.py')], cwd=ROOT, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (HERE / 'green.log').write_text(green.stdout)
    print(green.stdout, end='', flush=True)
receipt = {'schema': 'veldo.ticket-falsifiers/v1', 'ticket': 'VELDO-0080', 'mutations': results,
           'green_exit': green.returncode}
(HERE / 'mutations.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
sys.exit(not (all(r['killed'] for r in results) and green.returncode == 0))
