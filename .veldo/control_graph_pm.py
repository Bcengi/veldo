"""Default project pipeline, spliced into the isolated LangGraph runner.
Only plain snapshots and result digests enter; no store or command owner exists here.
"""
_PM_PIPELINE = ('intake', 'coordinate', 'elaborate', 'admit', 'assign', 'build',
                'prove_and_gate', 'review', 'land', 'report')


def _pm_step(name):
    def step(view):
        index = _PM_PIPELINE.index(name)
        if name == 'intake':
            return {'next': 'coordinate', 'suspend': True}
        if name == 'coordinate' and not view['supplied_results']:
            return {'failure': {'code': 'missing_evidence', 'detail': 'coordinate needs a dispatched result'}}
        if name == 'report':
            return {'next': None, 'proposals': [{'type': 'completion',
                'proposal_id': view['identity']['cycle_id'] + '.report',
                'subject': view['supplied_results'][0]['value']['unit'],
                'evidence': [view['supplied_results'][0]['digest']]}]}
        return {'next': _PM_PIPELINE[index + 1]}
    return step


WORKFLOWS['default_pipeline'] = {'version': 1, 'entry': 'intake',
    'nodes': {name: _pm_step(name) for name in _PM_PIPELINE}}
