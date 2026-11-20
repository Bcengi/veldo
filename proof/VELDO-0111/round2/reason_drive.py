"""Replay retained live qualification evidence against each named-gap mutant."""
import copy, difflib, gzip, hashlib, importlib.util, json, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
SOURCE=ROOT/'scripts/fixtures/lifecycle_census.py'
source=SOURCE.read_text()
evidence=json.load(gzip.open(HERE/'qualification-green.json.gz','rt'))['evidence']['inventory']
expected={'protocol_inventory_bounds','operation_address_fixture','operation_configuration',
          'io_uring_socket_effects','socket_destruction','shared_socket_memory'}
report=dict(source_digest=hashlib.sha256(source.encode()).hexdigest(),cases={})
for capability in sorted(expected):
    needle='    def gap(capability, reason, evidence):\n'
    mutant=source.replace(needle,needle+f'        if capability == {capability!r}:\n            return\n')
    assert mutant!=source
    (HERE/(capability+'.diff')).write_text(''.join(difflib.unified_diff(
        source.splitlines(True),mutant.splitlines(True),fromfile=str(SOURCE),tofile='mutant.py')))
    results=[]
    for phase,code in [('red',mutant),('green',source)]:
        with tempfile.TemporaryDirectory(prefix='v111-reason-') as temporary:
            path=Path(temporary)/'census.py';path.write_text(code)
            spec=importlib.util.spec_from_file_location('census',path)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            r=copy.deepcopy(evidence);r['failures']=[]
            module.qualify(r,r['qualification']['inventory'])
        actual={f['capability'] for f in r['qualification']['reasons']}
        passed=actual==expected and actual=={f['capability'] for f in r['failures']}
        assert passed==(phase=='green'),(capability,phase,actual)
        results.append(dict(phase=phase,passed=passed,actual=sorted(actual)))
    report['cases'][capability]=results
    print(capability,results,flush=True)
(HERE/'reason-mutations.json').write_text(json.dumps(report,indent=2)+'\n')
