"""Read registry definitions only: no test loading and no mutation execution."""
import ast
import collections
import difflib
import hashlib
import json
from pathlib import Path
root=Path.cwd()
path=root/'scripts/check_teeth_mutations.py'
tree=ast.parse(path.read_text())
wanted={'SIGNED','FIELDS','RENDERER_LOADERS','RENDERER_COMPANIONS'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cases','edits') or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in wanted for t in n.targets)]
ns={'ROOT':root,'Path':Path,'json':json}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
cases=ns['cases']();bad=[]
for case in cases:
    path=root/case.get('dir','.veldo')/case['module']
    if case.get('fixture') or not path.exists():
        candidates=list(root.glob('**/'+case['module']))
        path=candidates[0] if candidates else None
    if path is None:
        continue
    source=path.read_text()
    for old,new in ns['edits'](case):
        if source.count(old)!=1:
            bad.append((case['name'],str(path.relative_to(root)),source.count(old)))
duplicates=[name for name,count in collections.Counter(c['name'] for c in cases).items() if count>1]
print(json.dumps(dict(registered=len(cases),bad=bad,duplicates=duplicates)))
print('%d bad anchors'%len(bad))
if bad or duplicates:
    raise SystemExit(1)
