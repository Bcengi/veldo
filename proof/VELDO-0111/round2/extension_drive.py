"""Drive ticket rows and safely remove the CLONE_UNTRACED check in scratch."""
import difflib, gzip, hashlib, importlib.util, json, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'scripts/fixtures/lifecycle_census.py'
SUITE=ROOT/'scripts/suites/113_veldo_0111_census.py'
phase=sys.argv[1]
spec=importlib.util.spec_from_file_location('suite',SUITE)
suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)
source=SOURCE.read_text()
mutant=source.replace('            if flags & 0x800000:', '            if False: # swallow escape attempt')
assert mutant!=source
(HERE/'clone-untraced.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),mutant.splitlines(True),fromfile=str(SOURCE),tofile='mutant.py')))
report=dict(source_digest=hashlib.sha256(source.encode()).hexdigest(),suite_digest=hashlib.sha256(SUITE.read_bytes()).hexdigest(),runs={})
for label,contents in [('control',source),('escape-mutant',mutant)]:
    with tempfile.TemporaryDirectory(prefix='v111-extension-') as temporary:
        path=Path(temporary)/'lifecycle_census.py';path.write_text(contents)
        rows=[]
        evidence=suite.run_checks(ROOT,lambda name,ok:rows.append([name,bool(ok)]),path)
    with gzip.open(HERE/(phase+'-'+label+'.json.gz'),'wt') as output:
        json.dump(dict(rows=rows,evidence=evidence),output)
    report['runs'][label]=rows
    print(phase,label,rows,flush=True)
    assert dict(rows)['census/clone-untraced']==(label=='control')
    assert dict(rows)['census/accepted-and-implicit']==(phase=='green')
    if phase=='green' and label=='control':
        assert all(ok for _,ok in rows)
(HERE/('extensions-'+phase+'.json')).write_text(json.dumps(report,indent=2)+'\n')
