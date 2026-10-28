"""Ticket-only mutation drive. Invoke under the owner's blocking flock command.

Each mutant lives in a private scratch directory. Its subprocess supervisor loads
that exact mutated file. The original worktree file is never replaced. A failed
named boolean in a completed run is a detected falsifier; exceptions are errors.
"""

import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'scripts/fixtures/lifecycle_census.py'
SUITE = ROOT / 'scripts/suites/113_veldo_0111_census.py'

CASES = [
    ('AC1', 'census/process-lifetimes',
     '            r["state"] = "drained"\n',
     '''            r["state"] = "drained"
            returned = next(b['sequence'] for b in r['barriers'] if b['name'] == 'call_returned')
            dropped = {p['identity'] for p in r['processes'] if not p['root'] and p['terminal'] < returned}
            r['processes'] = [p for p in r['processes'] if p['identity'] not in dropped]
            r['events'] = [e for e in r['events'] if e.get('identity') not in dropped]
'''),
    ('AC2', 'census/listener-lifetimes',
     '    def expose(self, pid, obj, operation, address):\n',
     '''    def expose(self, pid, obj, operation, address):
        if obj['family'] == socket.AF_INET6:
            return
'''),
    ('AC3', 'census/observer-is-outside',
     '            r["state"] = "drained"\n',
     '''            r["state"] = "drained"
            dropped = {p['identity'] for p in r['processes'] if not p['root'] and p.get('comm') == r['observer']['comm']}
            r['processes'] = [p for p in r['processes'] if p['identity'] not in dropped]
            r['events'] = [e for e in r['events'] if e.get('identity') not in dropped]
'''),
    ('AC4', 'census/incomplete-is-not-empty',
     '        failure(r, "collector_death", f"collector terminal status {status}")\n',
     '''        r.update(status='COMPLETE', capture_status='COMPLETE', state='drained', failures=[],
                 events=[], processes=[], sockets=[])
        r['qualification'].update(status='COMPLETE', gaps=[])
'''),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('suite111', SUITE)
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    original = SOURCE.read_text()
    report = dict(source_digest=sha(SOURCE), suite_digest=sha(SUITE), cases=[],
                  qualification='INCOMPLETE', scope='VELDO-0111 only')
    for ac, target, old, new in CASES:
        assert original.count(old) == 1, (ac, 'ambiguous replacement')
        changed = original.replace(old, new)
        patch = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                        fromfile='a/scripts/fixtures/lifecycle_census.py',
                        tofile='b/scripts/fixtures/lifecycle_census.py'))
        (HERE / (ac + '.diff')).write_text(patch)
        results = []
        for phase, contents in (('red', changed), ('green', original)):
            started = time.monotonic()
            with tempfile.TemporaryDirectory(prefix='v111-' + ac + '-' + phase + '-') as temporary:
                module = Path(temporary) / 'lifecycle_census.py'
                module.write_text(contents)
                rows = []
                evidence = suite.run_checks(ROOT, lambda name, ok: rows.append([name, bool(ok)]), module)
            result = dict(phase=phase, rows=rows, evidence=evidence,
                          seconds=time.monotonic() - started,
                          implementation_digest=hashlib.sha256(contents.encode()).hexdigest())
            (HERE / (ac + '-' + phase + '.json')).write_text(json.dumps(result, indent=2) + '\n')
            names = [name for name, _ in rows]
            assert len(names) == len(set(names)) == 5 and target in names, (ac, phase, 'missing row')
            observed = dict(rows)[target]
            assert observed == (phase == 'green'), (ac, phase, rows)
            if phase == 'green':
                assert all(ok for _, ok in rows), (ac, phase, rows)
            results.append(dict(phase=phase, row=target, passed=observed, completed=True,
                                seconds=result['seconds'], log=ac + '-' + phase + '.json'))
            print(ac, phase, target, observed, flush=True)
        report['cases'].append(dict(criterion=ac, diff=ac + '.diff', results=results))
        assert SOURCE.read_text() == original, 'worktree changed during drive'
        (HERE / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print('All four falsifiers detected, followed by green controls. Qualification remains INCOMPLETE.', flush=True)


if __name__ == '__main__':
    main()
