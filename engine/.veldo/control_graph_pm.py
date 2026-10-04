"""Default project pipeline, spliced into the isolated LangGraph runner.
Only plain snapshots and result digests enter; no store or command owner exists here.
"""
import hashlib as _pm_hashlib
import sys as _pm_sys

_pm_active = False


def _pm_audit(event, args):
    if _pm_active and (event == 'open' or event.startswith(('os.', 'subprocess.', 'sqlite3.', 'socket.'))):
        raise PermissionError('graph_capability_denied:' + event)


_pm_sys.addaudithook(_pm_audit)


def _pm_bounded(function):
    def bounded(view):
        global _pm_active
        _pm_active = True
        try:
            return function(view)
        except PermissionError as error:
            return {'failure': {'code': 'node_failed', 'detail': str(error)}}
        finally:
            _pm_active = False
    return bounded

_PM_PIPELINE = ('intake', 'coordinate', 'elaborate', 'admit', 'assign', 'build',
                'prove_and_gate', 'review', 'land', 'report')


def _pm_step(name):
    def step(view):
        index = _PM_PIPELINE.index(name)
        trace = list(view['notes'].get('pm_trace', [])) + [name]
        if name == 'intake':
            return {'next': 'coordinate', 'suspend': True, 'notes': {'pm_trace': trace}}
        if name == 'coordinate' and not view['supplied_results']:
            return {'failure': {'code': 'missing_evidence', 'detail': 'coordinate needs a dispatched result'}}
        if name == 'report':
            return {'next': None, 'proposals': [{'type': 'completion',
                'proposal_id': view['identity']['cycle_id'] + '.report',
                'subject': view['supplied_results'][0]['value']['unit'],
                'evidence': [view['supplied_results'][0]['digest'],
                    'sha256:' + _pm_hashlib.sha256(json.dumps(trace, separators=(',', ':')).encode()).hexdigest()]}]}
        return {'next': _PM_PIPELINE[index + 1], 'notes': {'pm_trace': trace}}
    return _pm_bounded(step)


WORKFLOWS['default_pipeline'] = {'version': 1, 'entry': 'intake',
    'nodes': {name: _pm_step(name) for name in _PM_PIPELINE}}
