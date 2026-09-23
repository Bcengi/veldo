#!/usr/bin/env python3
"""Reproduce proof/VELDO-0043/mutations.json: each registered finding-43 mutation applied to a
temporary installation of every .veldo asset the
scaffolder installs (the suite's own construction), with the isolated-enforcement verdict observed per entry.

  python3 -B proof/VELDO-0043/drive.py > proof/VELDO-0043/mutations.json
"""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
spec = importlib.util.spec_from_file_location('scaffold', ROOT / '.veldo/init_scaffold.py')
scaffold = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scaffold)
results = []
for case in [c for c in teeth.cases() if c['finding'] == 43]:
    with tempfile.TemporaryDirectory(prefix='drive-43-') as temporary:
        repo = Path(temporary) / 'installed'
        (repo / '.veldo').mkdir(parents=True)
        for rel in [r for r in scaffold._FILES if r.startswith('.veldo/')]:
            shutil.copyfile(ROOT / 'engine' / rel, repo / rel)
        for name in ('control_graph.py', 'control_graph_isolation.py', 'authorization.py',
                     'two_key.py', 'request.py'):
            shutil.copyfile(ROOT / '.veldo' / name, repo / '.veldo' / name)
        target = repo / '.veldo' / case['module']
        body = target.read_text()
        assert body.count(case['old']) == 1
        target.write_text(body.replace(case['old'], case['new']))
        proc = subprocess.run([sys.executable, '-B', str(repo / '.veldo/control_graph_isolation.py'),
                               '--root', str(repo)], capture_output=True, text=True, timeout=120)
        verdict = json.loads(proc.stdout.rsplit('\n', 2)[0])
        results.append({'mutation': case['name'], 'module': case['module'], 'target_rows': case['rows'],
                        'isolation_exit': proc.returncode, 'passed': verdict['passed'],
                        'failed_entries': [{k: e.get(k) for k in ('entry', 'static_violations',
                                                                    'refused_imports', 'exception', 'exit')}
                                           for e in verdict['entries'] if e['status'] != 'pass']})
print(json.dumps(results, indent=1, sort_keys=True))
