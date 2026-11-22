"""Canvas writes are installation commits, published by branch compare and swap."""
import importlib.util
from pathlib import Path


def organ(name):
    spec = importlib.util.spec_from_file_location('installation_commit_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WF = organ('control_workflow')
I = organ('installation')
Refused = WF.Refused


def save(loader, document, *, principal, base, command_id, base_commit, approval=None):
    definition, layout = document['definition'], document.get('layout', {})
    workflow = definition['id']
    event = {'operation': 'canvas_save', 'workflow': workflow, 'base': base, 'principal': principal,
             'command_id': command_id, 'commit': None}
    try:
        problem = WF.editor_problem(loader.conn, principal, loader.workflow_repository, loader.clock())
        if problem:
            raise Refused(problem)
        if not isinstance(command_id, str) or not command_id:
            raise Refused('invalid_input:command_id')
        if not isinstance(base_commit, str):
            raise Refused('invalid_input:base_commit')
        pending_commit = (approval or {}).get('command', {}).get('configuration_commit')
        retry = pending_commit is not None and loader.status().get('commit') == pending_commit
        if base_commit != loader.accepted_commit or loader.repo.head() != (pending_commit if retry else base_commit):
            raise Refused('stale_version')
        if WF.head_version(loader.conn, loader.domain, loader.workflow_repository, workflow) != base:
            raise Refused('stale_version')
        problems = WF.definition_problems(definition, WF._resolver(loader.conn))
        if not problems:
            problems = WF.layout_problems(layout, definition)
        if problems:
            raise Refused(problems[0], codes=problems)
        identity = loader.live[I.SETTINGS_FILE].get('git_identities', {}).get(principal)
        if identity is None:
            raise Refused('installation_missing:git_identities.' + principal)
        snapshot = loader.repo.snapshot(base_commit)
        files = dict(snapshot['files'])
        files['workflows/%s.json' % workflow] = WF.canonical(definition)
        files['workflows/%s.layout.json' % workflow] = WF.canonical(layout)
        _, problems = loader.validate(files)
        if problems:
            raise Refused(problems[0], codes=problems)
        head = WF._entity_row(loader.conn, WF.head_id(loader.domain, loader.workflow_repository, workflow))
        version = base + int(not head or head['data'].get('definition_digest') != WF.definition_digest(definition))
        message = 'workflow %s base %d version %d command %s' % (workflow, base, version, command_id)
        if retry:
            proposed = loader.repo.snapshot(pending_commit)
            if proposed['files'] != files:
                raise Refused('invalid_input:approval_commit')
            commit = pending_commit
        else:
            commit = loader.repo.commit(files, base_commit, identity, message)
        event.update(commit=commit, author=identity)
        if not retry:
            loader.repo.publish(commit, base_commit)
        result = loader.reconcile(made=True)
        if approval is not None:
            if loader.decisions is None or principal != loader.decisions.owner:
                raise Refused('installation_waiting_approval:' + commit)
            loader.decisions.signed_save(approval, commit)
            result = loader.reconcile(made=True)
        if result['outcome'] == 'refused':
            raise Refused(result['problems'][0], codes=result['problems'])
        answer = {'workflow': workflow, 'version': WF.head_version(loader.conn, loader.domain,
                  loader.workflow_repository, workflow), 'commit': commit, 'api_request_id': command_id,
                  'outcome': result['outcome'], 'configuration_commit': loader.accepted_commit}
        if result['outcome'] == 'waiting':
            answer['reason'] = 'installation_waiting_approval:' + commit
        else:
            answer['revision'] = WF.revision_id(loader.domain, loader.workflow_repository, workflow, answer['version'])
        if result.get('push_refusal'):
            answer['push_refusal'] = result['push_refusal']
        loader.saves['accepted'] += int(result['outcome'] == 'accepted')
        loader.observe(dict(event, outcome=result['outcome']))
        return answer
    except (Refused, loader.repo.error_type) as error:
        loader.saves['refused'] += 1
        loader.save_refusals[error.code] = loader.save_refusals.get(error.code, 0) + 1
        loader.observe(dict(event, outcome='refused', reason=error.code))
        raise Refused(error.code, codes=getattr(error, 'codes', None)) from None
