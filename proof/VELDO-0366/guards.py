"""Direct guard falsifiers through fake nodes only; no mutation coordinator or native workers."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[2]
def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
gate = load(root/'scripts/check_gate_mutations.py')
helper = load(root/'scripts/suites/support/v366_nodes.py')
driver = load(root/'scripts/check_teeth_mutations.py')
observer = load(root/'scripts/mutation_observer.py')
results = []
for case in [c for c in driver.cases() if c['finding'] == 366]:
    source = (root/'scripts'/case['module']).read_bytes()
    record = dict(name=case['name'], row=case['rows'][0], observations={})
    for mode in ('baseline','noop','mutant'):
        body = observer.mutate(source, case) if mode=='mutant' else source + (b'\n# no-op guard control\n' if mode=='noop' else b'')
        with tempfile.TemporaryDirectory(prefix='v366-guard-') as directory:
            path = Path(directory)/case['module']
            path.write_bytes(body)
            module = load(path)
            module.ROOT = root
            shards = module if case['module']=='mutation_shards.py' else load(root/'scripts/mutation_shards.py')
            transport = module if case['module']=='mutation_transport.py' else load(root/'scripts/mutation_transport.py')
            rows = []
            with contextlib.redirect_stdout(io.StringIO()):
                helper.checks(module if case['module']=='check_gate_mutations.py' else gate, shards, transport, root, lambda name, passed: rows.append((name,bool(passed))),
                              worker=module if case['module']=='reuse_worker.py' else None)
            target = [ok for name,ok in rows if name.split()[-1] == case['rows'][0]]
            record['observations'][mode] = dict(target=target, failed=[n for n,ok in rows if not ok],
                                                source_sha256=hashlib.sha256(body).hexdigest())
    own = record['observations']
    record['passed'] = all(not own[m]['failed'] and own[m]['target']==[True] for m in ('baseline','noop')) and own['mutant']['target']==[False]
    results.append(record)
print(json.dumps(dict(passed=all(r['passed'] for r in results), count=len(results), guards=results),indent=2))
sys.exit(not all(r['passed'] for r in results))
