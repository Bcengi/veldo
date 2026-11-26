"""Join historical worker time to the spec's mandatory thread exclusion.

Read source worktrees and receipts only. No validation workers are launched.
The shared controls make every associated case unknown even if a mutant
removes the watchdog. Additional exclusions cannot reduce this union.
"""
import ast
import collections
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path('/home/dmitry/projects/veldo-worktrees/change-scoped-i45')
LOG = Path('/home/dmitry/projects/myday/research/gate-stamps/cand-1122-55b511908-verify.log')
BASE = '55b511908'
original = runpy.run_path(str(ROOT/'proof/VELDO-0367/measure-confinement.py'))['measure'](LOG)
number = original['source_line']
for lineno,line in enumerate(LOG.open(),1):
    if lineno == number:
        receipt = json.loads(line[line.index('{'):])
        break
def historical(path):
    return subprocess.check_output(['git','show',BASE+':'+path])
worker = historical('scripts/reuse_worker.py')
assert b"owner = load(authority / 'scripts/mutation_observer.py')" in worker
assert b'owner.worker(case' in worker
observer = historical('scripts/mutation_observer.py')
assert b'faulthandler.dump_traceback_later(PROCESS_HANG_SECONDS, exit=True)' in observer
worker_function = next(n for n in ast.parse(observer).body if isinstance(n, ast.FunctionDef) and n.name == 'worker')
assert any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
           and isinstance(n.value.func, ast.Attribute)
           and isinstance(n.value.func.value, ast.Name)
           and n.value.func.value.id == 'faulthandler'
           and n.value.func.attr == 'dump_traceback_later'
           for n in worker_function.body), 'timer must be unconditional in worker body'
assert b'faulthandler.dump_traceback_later(PROCESS_HANG_SECONDS, exit=True)' in (ROOT/'scripts/mutation_observer.py').read_bytes()
dispatcher = historical('scripts/selftest.py')
watchdog = historical('scripts/suites/support/waits.py')
assert b'WAITS.arm_watchdog()' in dispatcher
assert b'threading.Thread(target=self._run' in watchdog
assert b'faulthandler.dump_traceback_later' in watchdog
assert b'self._thread.start()' in watchdog
assert b'WAITS.arm_watchdog()' in (ROOT/'scripts/selftest.py').read_bytes()
assert b'threading.Thread(target=self._run' in (ROOT/'scripts/suites/support/waits.py').read_bytes()
cases = {r['case']['identity']:r['case'] for r in receipt['results']}
workers = {w['name']:w for w in receipt['worker_outcomes']}
for case in cases.values():
    if workers[case['identity']]['leg'] != 'confined':
        continue
    group = case['suite']+':'+case['module']+':'+str(case.get('fixture') is True)
    if case.get('confined_only') is True:
        group += ':confined'
    for mode in ('baseline','noop'):
        assert workers[group+':'+mode]['leg'] == 'confined'

groups = collections.defaultdict(lambda:dict(cases=0,controls=0,mutant_seconds=0.,control_seconds=0.))
suites = collections.defaultdict(lambda:dict(cases=0,controls=0,worker_seconds=0.))
for w in receipt['worker_outcomes']:
    if w['leg'] != 'confined':
        continue
    mutant = w['mode']=='mutant'
    suite = cases[w['name']]['suite'] if mutant else w['name'].split(':')[0]
    row = suites[suite]
    row['cases' if mutant else 'controls'] += 1
    row['worker_seconds'] += w['elapsed']
    row = groups['confined_shared_runner_threads']
    row['cases' if mutant else 'controls'] += 1
    row['mutant_seconds' if mutant else 'control_seconds'] += w['elapsed']
groups['unconfined_tracing_exclusions'] = dict(original['groups']['nested_or_excluded'])
unknown = sum(v['mutant_seconds']+v['control_seconds'] for v in groups.values())
for row in groups.values():
    row['total_seconds'] = row['mutant_seconds']+row['control_seconds']
    row['share_all_worker_percent'] = 100*row['total_seconds']/original['total_worker_seconds']
    row['share_target_worker_percent'] = 100*row['total_seconds']/unknown
result = dict(source=str(LOG),source_line=number,receipt_commit=BASE,
    receipt_sha256=hashlib.sha256(line.encode()).hexdigest(),
    historical_worker_sha256=hashlib.sha256(worker).hexdigest(),
    historical_observer_sha256=hashlib.sha256(observer).hexdigest(),
    historical_dispatcher_sha256=hashlib.sha256(dispatcher).hexdigest(),
    historical_waits_sha256=hashlib.sha256(watchdog).hexdigest(),
    original_measurement=original,groups=dict(groups),confined_suites=len(suites),suites=dict(sorted(suites.items())),
    still_unknown_cases=sum(v['cases'] for v in groups.values()),still_unknown_seconds=unknown,
    still_unknown_target_percent=100.,newly_eligible_cases=0,newly_eligible_worker_seconds=0.,
    method='Static mandatory mutation_observer faulthandler watchdog path joined to actual historical worker legs; controls counted once by their own suite and leg. No extrapolation from sampled suites; no historical syscall traces.')
print(json.dumps(result,indent=2,sort_keys=True))
