#!/usr/bin/env python3
"""Ticket-only red then green checks. Invoke under the owner's blocking flock."""
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    teeth = load(ROOT/'scripts/check_teeth_mutations.py')
    cases = [c for c in teeth.cases() if c['finding']==219]
    assert {c['name'] for c in cases} == {'admission219-slowest-rate','admission219-fixed-sixteen',
                                         'admission219-optimistic-m'}
    paths = ['scripts/check_gate_mutations.py','scripts/reuse_worker.py','scripts/mutation_ownership.py']
    paths += ['engine/'+p for p in paths]
    paths += ['scripts/check_teeth_mutations.py','scripts/suites/115_veldo_0219_measured_admission.py',
              'scripts/suites/53_veldo_0123_mutations.py','scripts/suites/manifest.json','scripts/suites/requires.json',
              'proof/VELDO-0219/local_check.py','proof/VELDO-0219/kernel_check.py',
              'proof/VELDO-0219/qualification.py']
    evidence = dict(spec='VELDO-0219',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},runs=[],
        canonical_qualification='NOT RUN: owner rule 37191; see OPEN.md')
    target = Path(__file__).with_name('red-green.json')
    for case in cases:
        for mode in ('mutant','baseline','noop'):
            started = time.monotonic()
            with tempfile.TemporaryDirectory(prefix='v219-falsifier-') as directory:
                made = teeth.materialize(case,mode,directory,ROOT)
                if mode == 'mutant':
                    before = (ROOT/'scripts'/case['module']).read_text()
                    after = made['mutant'].read_text()
                    Path(__file__).with_name(case['name']+'.diff').write_text(''.join(difflib.unified_diff(
                        before.splitlines(keepends=True),after.splitlines(keepends=True),
                        fromfile='a/scripts/'+case['module'],tofile='b/scripts/'+case['module'])))
                result = teeth.worker(case,str(made['mutant']) if made['mutant'] else None)
            rows = {name.split()[-1]:ok for name,ok in result['observations'] if name.startswith('VELDO-0219 ')}
            evidence['runs'].append(dict(case=case['name'],mode=mode,target_rows=case['rows'],
                old_digest=made['old_digest'],new_digest=made['new_digest'],rows=rows,
                failed_rows=[n for n,ok in rows.items() if not ok],seconds=time.monotonic()-started))
            target.write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
            print(case['name'],mode,evidence['runs'][-1]['failed_rows'],flush=True)
            assert rows and len(rows)==14, result
            if mode == 'mutant':
                assert all(rows.get(r) is False for r in case['rows']), result
            else:
                assert all(rows.values()), result
    qualification = load(Path(__file__).with_name('qualification.py'))
    captures = []
    for elapsed, workers in ((5207,16),(3300,26)):
        capture = qualification.fixture()
        capture['mutation'].update(elapsed=elapsed,peak_workers=workers)
        result = qualification.check(capture)
        assert result['passed'] == (elapsed<=4000)
        captures.append(dict(synthetic=True,elapsed=elapsed,workers=workers,result=result))
    Path(__file__).with_name('capture-checker-red-green.json').write_text(json.dumps(
        dict(scope='checker unit test only; no canonical timing measured',runs=captures),indent=2)+'\n')
    suites = []
    for suite in ('115_veldo_0219_measured_admission','53_veldo_0123_mutations'):
        command = [sys.executable,'-B','scripts/selftest.py','--suite',suite]
        result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
        Path(__file__).with_name(suite+'.log').write_text(result.stdout+result.stderr)
        summary = [line for line in result.stdout.splitlines() if line.startswith('selftest (PARTIAL')]
        suites.append(dict(suite=suite,command=command,exit=result.returncode,summary=summary))
        Path(__file__).with_name('suite-results.json').write_text(json.dumps(suites,indent=2)+'\n')
        print(suite,result.returncode,summary,flush=True)
        assert result.returncode==2 and summary and '0 failed' in summary[0], result.stdout[-6000:]
    assert all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in evidence['source_sha256'].items())
    return 0


if __name__=='__main__':
    raise SystemExit(main())
