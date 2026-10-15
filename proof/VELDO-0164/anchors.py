"""Read mutation registrations and retain diffs without running any mutation or suite."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'scripts/check_teeth_mutations.py'
tree = ast.parse(path.read_text())
# Evaluate the declarative registry only, never its dispatcher or mutation machinery.
kept = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
        or isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets)
        or isinstance(node, ast.FunctionDef) and node.name == 'cases']
namespace = {'__file__': str(path)}
exec(compile(ast.Module(body=kept, type_ignores=[]), str(path), 'exec'), namespace)
cases = namespace['cases']()
touched = {'control_api_models.py','control_api_models_scope.py','control_api_authority.py','control_api.py','init_scaffold.py'}
errors, records = [], []
for case in cases:
    if (case['finding'] != 164 and case.get('module') not in touched) or case.get('fixture'):
        continue
    source = ROOT / case.get('dir','.veldo') / case['module']
    before = source.read_text()
    after = before
    for old,new in [(case['old'],case['new'])] + case.get('also',[]):
        if after.count(old) != 1:
            errors.append(dict(name=case['name'],module=case['module'],count=after.count(old)))
            break
        after = after.replace(old,new)
    if case['finding'] == 164:
        diff = case['name'] + '.diff'
        (Path(__file__).parent / diff).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
            fromfile=case.get('dir','.veldo')+'/'+case['module'],tofile=case.get('dir','.veldo')+'/'+case['module'],n=0)))
        records.append(dict(name=case['name'],rows=case['rows'],module=case['module'],diff=diff,
            source_sha256=hashlib.sha256(before.encode()).hexdigest(),status='registered; execution reserved for reviewer'))
result = dict(schema='veldo.scoped_read_falsifiers/v1',finding=164,mutations=records,anchor_errors=errors)
(Path(__file__).parent / 'falsifiers.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'registered':len(records),'anchor_errors':errors},indent=2))
