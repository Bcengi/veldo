"""Production factory activation used by suites whose intake routing 0152 amends."""
import importlib.util
from pathlib import Path
import uuid


def factory(intake, ids, owner, sign_as):
    spec = importlib.util.spec_from_file_location('neighbor_project', Path(intake._plan.__func__.__globals__['__file__']).with_name('control_project.py'))
    project = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(project)
    service = project.Projects(intake.store, intake.CM, intake.conn, ids, intake.journal_signer, intake.sign, stop=lambda dispatch, reason: False)
    command = dict(ids, operation='activate', project='factory', principal=owner,
        command_id='factory-' + uuid.uuid4().hex, nonce=uuid.uuid4().hex, owner=owner,
        charter={'purpose': 'Route new input'}, execution_repository=ids['repository_uuid'],
        authority_policy={'admission': ['project_owner']},
        coordination_budget={'capacity': 1, 'invocations': 10, 'wall_seconds': 60})
    result = service.apply(dict(command=command, signature=sign_as(owner, intake.store.canonical_bytes(command))))
    if not result.get('ok'):
        raise AssertionError('factory activation refused: ' + str(result))
    intake.projects = tuple(intake.projects) + ('factory',)
    return result


def unclear(intake, result):
    pid = result['proposal_id']
    return intake.route(dict(schema='veldo.intake_route/v1', proposal_id=pid, route='unclear',
                             reason='The project is unclear.'), dispatch='fixture-pm-152', proposal_id=pid)
