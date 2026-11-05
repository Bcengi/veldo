"""A unit's process is a versioned workflow revision (VELDO-0241). Standard library only.

WHAT THIS IS. The Line (control_service) used to hardcode a unit's stations: build, then review, and after a land
the land station's after-land rule. Here the process is a VELDO-0132 workflow definition made of the unit's
station kinds (control_workflow.STEP_KINDS: build, review, gate, owner_approval, land, end), and the Line runs the
one revision the unit is bound to, node by node, every node still going through the role, the Gate and the result
checks of the station it names.

THE DEFAULT. Today's code process ships as the definition `code` (workflows/code.json beside this module, the file
the scaffold lays and the canvas shows): build, review, gate, the owner's landing approval, land, with VELDO-0148's
re-land (land.trunk_moved -> land), re-build on conflict (land.conflict -> build) and re-approval
(land.awaiting_approval -> approval) as bounded transitions. An installed service carries only Python modules, so
CODE below is the same definition as data in this module; the VELDO-0241 suite holds the two byte-identical in
canonical form. A project with no binding runs `code` as the shipped revision, version SHIPPED (0).

THE BINDING. A project record (control_project, operation bind_workflow, the project owner's signed command) holds
`workflows`: {kind of work: {workflow, version, digest}}. A unit names its kind of work in its execution unit record
(`kind_of_work`); a unit that names none, or names one the project does not bind, takes the `default` binding, and a
project with no binding takes the shipped `code`. A binding names an accepted revision of a unit workflow: one the
store holds, whose digests verify and whose nodes are all station kinds (bound_revision), else missing_workflow.

THE PIN. A unit records {id, version, digest} (and the node) in the payload of the first station the Line offers it,
and every later station reads that record (pinned), not the project's binding and not the workflow's head: saving a
new revision or rebinding while a unit runs leaves it on its recorded revision; the next new unit takes the new one.
A unit whose stations predate this record runs the shipped `code`, which is what it ran.

WHAT IS NOT HERE. The save check that no definition reaches an outward step without the owner's approval is
control_workflow.approval_problems (every save runs it); this module only loads, resolves and walks.
"""
import importlib.util
import json
from pathlib import Path


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WF = _sibling('veldo_workflow_unit_workflow', 'control_workflow.py')
Refused = WF.Refused

DEFAULT = 'code'
DEFAULT_KIND = 'default'
SHIPPED = 0
KIND_FIELD = 'kind_of_work'
PIN_FIELDS = ('id', 'version', 'digest')
MISSING = 'missing_workflow'

# The shipped `code` definition, as data (see THE DEFAULT): identical to workflows/code.json.
CODE = {
    'schema': 'veldo.workflow/v1', 'id': 'code', 'entry': 'build', 'terminal': ['done'],
    'nodes': {
        'build': {'kind': 'build', 'config': {}},
        'review': {'kind': 'review', 'config': {}},
        'gate': {'kind': 'gate', 'config': {}},
        'approval': {'kind': 'owner_approval', 'config': {'approves': 'land'}},
        'land': {'kind': 'land', 'config': {}},
        'done': {'kind': 'end', 'config': {}},
    },
    'transitions': [
        {'id': 'built', 'from': 'build', 'port': 'done', 'to': 'review'},
        {'id': 'reviewed', 'from': 'review', 'port': 'done', 'to': 'gate'},
        {'id': 'gated', 'from': 'gate', 'port': 'passed', 'to': 'approval'},
        {'id': 'approved', 'from': 'approval', 'port': 'granted', 'to': 'land'},
        {'id': 'stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'},
        {'id': 'landed', 'from': 'land', 'port': 'landed', 'to': 'done'},
        {'id': 're-land', 'from': 'land', 'port': 'trunk_moved', 'to': 'land', 'max': 16},
        {'id': 're-build', 'from': 'land', 'port': 'conflict', 'to': 'build', 'max': 16},
        {'id': 're-approval', 'from': 'land', 'port': 'awaiting_approval', 'to': 'approval', 'max': 16},
        {'id': 'unknown', 'from': 'land', 'port': 'unknown', 'to': 'done'},
        {'id': 'failed', 'from': 'land', 'port': 'failed', 'to': 'done'},
    ],
    'references': {},
    'budget': {'steps': 64},
}


def shipped(name=DEFAULT):
    """The shipped definition `name`: the workflows directory's file beside this module when it is there (the
    engine and a scaffolded repository), else the module's own copy (an installed service)."""
    path = Path(__file__).with_name('workflows') / (name + '.json')
    if path.is_file():
        return json.loads(path.read_text())
    if name == DEFAULT:
        return json.loads(json.dumps(CODE))
    raise Refused(MISSING, name)


def pin(definition, version):
    """The identity a unit records: {id, version, digest} of the definition at `version`."""
    return {'id': definition['id'], 'version': version, 'digest': WF.definition_digest(definition)}


def unit_problems(definition):
    """Every problem of `definition` as a unit's process: the save problems, and any node that is not a station
    kind (a VELDO-0132 cycle definition is not a unit process)."""
    problems = WF.definition_problems(definition)
    if problems:
        return problems
    return ['unsupported_configuration:not_a_station:%s' % name for name, node in sorted(definition['nodes'].items())
            if not (WF.step_kind(node) or {}).get('station')]


def bound_revision(store, conn, domain, repository, workflow, version):
    """(pin, definition) of an accepted unit workflow revision in the store, or Refused missing_workflow."""
    if not WF._identifier(workflow) or type(version) is not int or version < 1:
        raise Refused(MISSING, '%r@%r' % (workflow, version))
    try:
        _row, data = WF.verified_revision(store, conn, domain, repository, workflow, version)
    except Refused as error:
        raise Refused(MISSING, error.code) from None
    definition = data['definition']
    if unit_problems(definition):
        raise Refused(MISSING + ':not_a_unit_workflow', workflow)
    return pin(definition, version), definition


def binding(project, kind_of_work=None):
    """The project's binding for the kind of work (falling back to `default`), or None."""
    bindings = (project or {}).get('workflows') or {}
    kind = kind_of_work if isinstance(kind_of_work, str) and kind_of_work in bindings else DEFAULT_KIND
    return bindings.get(kind)


def resolve(store, conn, domain, repository, project, kind_of_work=None):
    """(pin, definition) a new unit of this project and kind of work takes: its binding's revision, or the
    shipped `code`."""
    bound = binding(project, kind_of_work)
    if bound is None:
        definition = shipped()
        return pin(definition, SHIPPED), definition
    found, definition = bound_revision(store, conn, domain, repository, bound.get('workflow'), bound.get('version'))
    if found['digest'] != bound.get('digest'):
        raise Refused(MISSING + ':stale_binding', bound.get('workflow'))
    return found, definition


def recorded(payload):
    """The pin a station's payload records, or None."""
    found = (payload or {}).get('workflow') if isinstance(payload, dict) else None
    if not isinstance(found, dict) or not all(field in found for field in PIN_FIELDS):
        return None
    return {field: found[field] for field in PIN_FIELDS}


def pinned(store, conn, domain, repository, found):
    """The definition of the revision a unit recorded, read again and checked against the recorded digest."""
    if found['version'] == SHIPPED:
        definition = shipped(found['id'])
        if WF.definition_digest(definition) != found['digest']:
            raise Refused(MISSING + ':shipped_changed', found['id'])
        return definition
    current, definition = bound_revision(store, conn, domain, repository, found['id'], found['version'])
    if current['digest'] != found['digest']:
        raise Refused(MISSING + ':digest', found['id'])
    return definition


def transition(definition, node, port):
    """The transition leaving `node` by `port`, or None."""
    return next((t for t in definition['transitions'] if t['from'] == node and t['port'] == port), None)


def nodes_of(definition, kind):
    return sorted(name for name, node in definition['nodes'].items() if node['kind'] == kind)


def walk(definition, start, act):
    """Run `act(node, kind)` from `start`: it answers ('port', port) to move on by that port's transition, or
    ('stop', value) to end the walk with value. A walk longer than the definition's step budget stops
    ('budget_exceeded:steps', None); a port with no transition stops ('missing_transition', None)."""
    node, steps = start, 0
    while steps < definition['budget']['steps']:
        steps += 1
        answer, value = act(node, definition['nodes'][node]['kind'])
        if answer == 'stop':
            return None, value
        taken = transition(definition, node, value)
        if taken is None:
            return 'missing_transition:%s.%s' % (node, value), None
        node = taken['to']
    return 'budget_exceeded:steps', None


def metrics(processes):
    """Units by bound revision and node: {"id@version": {node: count}}."""
    counts = {}
    for found in processes.values():
        key = '%s@%s' % (found.get('id'), found.get('version'))
        counts.setdefault(key, {})
        counts[key][found.get('node')] = counts[key].get(found.get('node'), 0) + 1
    return counts
