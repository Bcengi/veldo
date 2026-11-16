"""Observe real cleanup calls while running the unchanged adoption suite.

Only reads fixture refs. Assertions, production calls and their results are unchanged.
Run from the repository root with nice -n 10 python3 proof/VELDO-0304/observe_adoption.py.
"""
import json
from pathlib import Path
import runpy
import subprocess
import sys


observations = []
active = {}


def git(path, *args, feed=None):
    done = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(path), *args],
                          input=feed, capture_output=True, text=True)
    return done.returncode, done.stdout.strip()


def observe(frame, event, result):
    if (frame.f_code.co_name != 'remove_scaffold_ref'
            or Path(frame.f_code.co_filename).name != 'control_repository_provisioner.py'):
        return
    if event == 'call':
        path, repository = frame.f_locals['path'], frame.f_locals['repository']
        ref = frame.f_globals['SCAFFOLD_REF'] + repository
        code, tip = git(path, 'show-ref', '--verify', '--hash', ref)
        if code:
            return
        code, holding = git(path, 'for-each-ref', '--format=%(objectname)', 'refs/heads/', 'refs/veldo/kept/')
        if code:
            raise AssertionError('cannot read fixture holding refs')
        code, beyond = git(path, 'rev-list', '--stdin', feed='\n'.join([tip, '--not', *holding.split()]) + '\n')
        if code:
            raise AssertionError('cannot read fixture reachability')
        if beyond:
            active[id(frame)] = dict(path=str(path), repository=repository, ref=ref, commit=tip)
    elif event == 'return' and id(frame) in active:
        item = active.pop(id(frame))
        code, refs = git(item['path'], 'for-each-ref', '--format=%(refname)',
                         '--contains=' + item['commit'], 'refs/veldo/kept/')
        gone_code, gone = git(item['path'], 'for-each-ref', '--format=%(refname)', item['ref'])
        item.update(cleanup_result=result, kept_refs=refs.splitlines(),
                    preserved=code == 0 and bool(refs), removed=gone_code == 0 and not gone)
        observations.append(item)


sys.argv = ['scripts/selftest.py', '--suite', '109_veldo_0161_adoption']
sys.setprofile(observe)
suite_exit = 0
try:
    runpy.run_path('scripts/selftest.py', run_name='__main__')
except SystemExit as ended:
    suite_exit = ended.code
finally:
    sys.setprofile(None)

passed = bool(observations) and not active and all(
    item['cleanup_result'] and item['preserved'] and item['removed'] for item in observations)
receipt = dict(status='passed' if passed else 'failed', suite_exit=suite_exit,
               unchanged_suite=True, unheld_cleanups=len(observations), observations=observations)
Path('proof/VELDO-0304/adoption-preservation.json').write_text(json.dumps(receipt, indent=2) + '\n')
print('adoption preservation: %s, %d unheld cleanups' % (receipt['status'], len(observations)))
raise SystemExit(0 if passed else 1)
