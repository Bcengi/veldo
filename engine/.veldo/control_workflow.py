"""Versioned workflow definitions: plain data, validated here, stored as immutable revisions
(PLAN-0019 W95, VELDO-0132 AC1 and AC3). Standard library only.

WHAT A WORKFLOW IS. A definition (schema veldo.workflow/v1) is plain JSON data and nothing else:

  schema       'veldo.workflow/v1'
  id           the workflow's identity, an identifier (lowercase letters, digits, '-' and '_')
  entry        the node a cycle starts at
  terminal     the nodes a cycle ends at: exactly the nodes whose step kind is terminal
  nodes        {node id: {kind, config}}: kind is a REGISTERED step kind (STEP_KINDS), config is
               that kind's closed configuration; no node carries code, shell, SQL or a script
  transitions  [{id, from, port, to, max?}]: one transition for each port of each non-terminal
               node, from a node to a node, `max` bounding how often one cycle may take it
  references   {roles: {key: ref}, tools: {key: ref}}: each ref is {id, version, digest} of an
               accepted role or tool configuration entity in the store (REFERENCE_KINDS)
  budget       {steps}: the most node executions one cycle may make, at most STEP_CEILING

The revision number is not part of the definition: the store assigns it. definition_problems()
names every problem: dangling edges, unknown step kinds and ports, missing, unused or unresolved
configuration references, unreachable nodes, a terminal set that is not the terminal kinds, and an
unbounded cycle (a ring of transitions none of which carries `max`). A loop is allowed exactly when
it is bounded.

THE CANVAS DOCUMENT is {definition, layout}. The layout ({nodes: {id: {x, y}}, transitions: {id:
{points}}, viewport: {x, y, zoom}}) is canvas metadata only: it is stored beside the definition and
digested separately, and nothing that executes ever reads it. The execution identity of a revision
is (id, version, definition_digest), where definition_digest is the sha256 of the definition's
canonical bytes (sorted keys, compact separators, ASCII).

REVISIONS. Workflows.save() commits one store command, save_workflow_revision, through the caller's
connection and signer. It is the ONLY writer of workflow revisions and heads (control_store
.declare_owners names this file), and its transition reads everything it judges inside the store's
transaction: the editor's membership (an active person member holding project_owner or
technical_authority, scoped to the repository), the head, and every referenced configuration. A save
names the version it edits (`base`, 0 for a new workflow); a base that is not the current head is
refused stale_version, so an edit never lands on a revision it did not see. Each save writes a NEW
revision entity, workflow-revision:[domain, repository, workflow, version], that is never written
again (workflow_immutable), and moves the head to it; every earlier revision keeps its bytes.
Workflows.load() reads a revision back from the store, checks its entity digest and its definition
digest, and returns the document. Saving and loading dispatch nothing, call no provider and run no
shell: this module never loads the graph adapter, the runner or any dispatcher.

OBSERVABILITY. Every save and load is reported to `observe` with operation, domain, repository,
actor, workflow, base and resulting version, record identity, digests, outcome, named refusal and
its class in the error taxonomy (unauthenticated, unauthorized, stale version, unsupported
configuration, unavailable service, missing evidence, unknown outcome; unknown is never success).
No secret is read or reported.

NOT HERE (Release 2): recovery, migration of revisions to a new schema, concurrent-editor merging.
The authenticated API (VELDO-0130) and the canvas (VELDO-0131) call save() and load(); they are
built by those specifications.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sqlite3
import time

SCHEMA = 'veldo.workflow/v1'
REVISION_SCHEMA = 'veldo.workflow_revision/v1'
REVISION_KIND = 'workflow_revision'
HEAD_KIND = 'workflow_head'
SAVE = 'save_workflow_revision'
OWNER = 'VELDO-0132 workflow revisions'
WRITES = ('entities', 'journal', 'commands', 'nonces')

DEFINITION_FIELDS = ('schema', 'id', 'entry', 'terminal', 'nodes', 'transitions', 'references', 'budget')
NODE_FIELDS = ('kind', 'config')
TRANSITION_FIELDS = ('id', 'from', 'port', 'to')
TRANSITION_OPTIONAL = ('max',)
REFERENCE_FIELDS = ('id', 'version', 'digest')
# The accepted configuration kinds a reference may name (their schema and writer are VELDO-0127's).
REFERENCE_KINDS = {'roles': 'role_configuration', 'tools': 'tool_configuration'}
BUDGET_FIELDS = ('steps',)
# The graph runner bounds one invocation at 64 steps (control_graph_langgraph.MAX_STEPS).
STEP_CEILING = 64
# THE REGISTERED STEP KINDS. ports: the named outcomes a node of the kind routes by; config: its closed
# configuration ({field: (reference type or None, required)}); input: what the cycle must supply before
# the node runs (None: nothing beyond the subject); terminal: the node ends the cycle with a proposal.
STEP_KINDS = {
    'grooming': {'ports': ('groomed',), 'config': {}, 'input': None, 'terminal': False},
    'owner_wait': {'ports': ('admit', 'decline'), 'config': {}, 'input': 'owner_answer', 'terminal': False},
    'assignment': {'ports': ('done',), 'config': {'role': ('roles', True), 'tools': ('tools', False)},
                   'input': 'worker_result', 'terminal': False},
    'result_handling': {'ports': (), 'config': {}, 'input': 'accepted_result', 'terminal': True},
}
# VELDO-0241: THE UNIT'S STATION KINDS, the steps a unit's process (control_workflow_unit) is made of. `station`
# marks a kind the Line runs for a unit; `outward` a step that sends something out of the factory (land here;
# deliver, publish and deploy register the same way), which the save check (approval_problems) lets a definition
# reach only through an owner_approval node naming it; `changes_subject` False marks a kind proven not to change
# what was approved (a kind without it, registered here or later, counts as changing the subject).
# An owner_approval node names its outward node in `approves`; it settles through the owner's ordinary decision
# bound to the exact subject (VELDO-0068, VELDO-0057), and only its `granted` port passes on to that node.
APPROVAL = 'owner_approval'
GRANTED = 'granted'
LAND_PORTS = ('landed', 'trunk_moved', 'conflict', 'awaiting_approval', 'unknown', 'failed')
STEP_KINDS.update({
    'build': {'ports': ('done',), 'config': {}, 'input': None, 'terminal': False, 'station': True,
              'changes_subject': True},
    'review': {'ports': ('done',), 'config': {}, 'input': None, 'terminal': False, 'station': True,
               'changes_subject': False},
    'gate': {'ports': ('passed',), 'config': {}, 'input': None, 'terminal': False, 'station': True,
             'changes_subject': False},
    APPROVAL: {'ports': (GRANTED, 'stopped'), 'config': {'approves': (None, True)}, 'input': None, 'terminal': False,
               'station': True, 'changes_subject': False},
    'land': {'ports': LAND_PORTS, 'config': {}, 'input': None, 'terminal': False, 'station': True, 'outward': True,
             'changes_subject': False},
    'end': {'ports': (), 'config': {}, 'input': None, 'terminal': True, 'station': True, 'changes_subject': False},
})
# VELDO-0247: CHECK AND JOIN, AND PARALLEL BRANCHES. A definition may declare `fields` ({name: {type, source,
# choices?, private?}}): a type (FIELD_TYPES; a choice lists its `choices`), a source ({subject: key}, the key of the
# subject's record, or {node, result}, the named result of an assignment node that lies on every path from the entry
# to each check reading it) and `private` (its observed value is logged only as a digest). A check node's config is
# exactly {branches: [{name, conditions: [{field, comparison, value}]}], otherwise: true}: its ports are its branch
# names plus `otherwise`, each with exactly one transition, tried in order, the first branch whose conditions all hold
# taken, otherwise when none does. A comparison is one of COMPARISONS, allowed only for the field's type; a value is
# a literal of the field's type (a list of them for `is one of`), plain text matching TEXT. Nothing is ever
# evaluated, interpolated or run: a value is compared as data (evaluate). Any other port that leads to several
# transitions makes its node a fan-out of at most FAN_OUT_CEILING branches, each branch named by the id of the
# transition that starts it; every branch reaches the one join node whose config is {inputs: [those ids]}, no path
# leaves a branch except through that join, and a fan-out inside a branch is refused (block_problems).
CHECK = 'check'
JOIN = 'join'
OTHERWISE = 'otherwise'
DEFINITION_OPTIONAL = ('fields',)
FAN_OUT_CEILING = 8
FIELD_FIELDS = ('type', 'source')
FIELD_OPTIONAL = ('choices', 'private')
COMPARISONS = ('is', 'is not', 'less than', 'at most', 'more than', 'at least', 'contains', 'is one of')
FIELD_TYPES = {
    'text': ('is', 'is not', 'contains', 'is one of'),
    'number': ('is', 'is not', 'less than', 'at most', 'more than', 'at least', 'is one of'),
    'yes_no': ('is', 'is not'),
    'choice': ('is', 'is not', 'is one of'),
}
TEXT = re.compile(r'[A-Za-z0-9 .,_/:@-]{0,200}\Z')
CODE_LIKE = frozenset('{}`$\'"[]();|<>=')
CHECK_FIELDS = ('branches', 'otherwise')
BRANCH_FIELDS = ('name', 'conditions')
CONDITION_FIELDS = ('field', 'comparison', 'value')
STEP_KINDS.update({
    CHECK: {'ports': (), 'config': None, 'input': None, 'terminal': False, 'changes_subject': False},
    JOIN: {'ports': ('done',), 'config': None, 'input': None, 'terminal': False, 'changes_subject': False},
})
LAYOUT_FIELDS = ('nodes', 'transitions', 'viewport')
IDENTIFIER = re.compile(r'[a-z][a-z0-9_-]{0,62}\Z')
# Node names the runner and this service keep for themselves.
RESERVED_PREFIX = 'veldo_'
DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')
EDITOR_TYPES = ('person',)
EDITOR_ROLES = ('project_owner', 'technical_authority')

TAXONOMY = {
    'unauthenticated': 'unauthenticated', 'missing_authority': 'unauthorized', 'budget_exceeded': 'unauthorized',
    'stale_version': 'stale_version', 'workflow_immutable': 'stale_version', 'entity_owned': 'unauthorized',
    'unsupported_configuration': 'unsupported_configuration', 'invalid_input': 'unsupported_configuration',
    'unavailable_service': 'unavailable_service', 'runtime_unavailable': 'unavailable_service',
    'missing_evidence': 'missing_evidence', 'missing_workflow': 'missing_evidence',
}


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


class Refused(Exception):
    """A named refusal; nothing was written. `codes` names every problem found."""

    def __init__(self, code, detail='', codes=None):
        self.code, self.detail = code, detail
        self.codes = list(codes or [code])
        super().__init__(code + (': ' + detail if detail else ''))


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_ORGANS = {}


def _organ(name):
    if name not in _ORGANS:
        _ORGANS[name] = _sibling('veldo_%s_workflow' % name, name + '.py')
    return _ORGANS[name]


def canonical(value):
    """THE canonical bytes of plain data: sorted keys, compact separators, ASCII, no NaN."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(body):
    return 'sha256:' + hashlib.sha256(body).hexdigest()


def definition_digest(definition):
    return digest(canonical(definition))


def revision_id(domain, repository, workflow, version):
    return 'workflow-revision:' + json.dumps([domain, repository, workflow, version], separators=(',', ':'))


def head_id(domain, repository, workflow):
    return 'workflow-head:' + json.dumps([domain, repository, workflow], separators=(',', ':'))


def _identifier(value):
    return type(value) is str and bool(IDENTIFIER.match(value))


def step_kind(node):
    """The registered step kind of a node, or None (an unknown or non-text kind)."""
    kind = node.get('kind') if type(node) is dict else None
    return STEP_KINDS.get(kind) if type(kind) is str else None


def node_ports(node):
    """The ports of a node: a check's branch names plus otherwise, else its kind's ports."""
    kind = step_kind(node)
    if kind is None:
        return ()
    if node.get('kind') != CHECK:
        return kind['ports']
    branches = (node.get('config') or {}).get('branches') if type(node.get('config')) is dict else None
    names = [b.get('name') for b in branches if type(b) is dict] if type(branches) is list else []
    return tuple(name for name in names if type(name) is str) + (OTHERWISE,)


def _count(value, low=1, high=None):
    return type(value) is int and value >= low and (high is None or value <= high)


def _literal(field, value):
    """'ok', 'code_like' or 'type' for one literal of the field's type."""
    kind = field['type']
    if kind == 'number':
        return 'ok' if type(value) is int else 'type'
    if kind == 'yes_no':
        return 'ok' if type(value) is bool else 'type'
    if type(value) is not str:
        return 'type'
    if CODE_LIKE & set(value):
        return 'code_like'
    if not TEXT.match(value):
        return 'type'
    if kind == 'choice' and value not in field['choices']:
        return 'type'
    return 'ok'


def _field_problems(fields, nodes):
    """(problems, declared fields) of the definition's `fields` section."""
    problems, declared = [], {}
    if type(fields) is not dict:
        return ['invalid_input:fields is not a mapping'], declared
    for name, field in sorted(fields.items()):
        where = 'fields.' + str(name)
        if not _identifier(name):
            problems.append('invalid_input:%s is not an identifier' % where)
            continue
        shape = _closed(field, FIELD_FIELDS, FIELD_OPTIONAL, where)
        if shape:
            problems += shape
            continue
        if field['type'] not in FIELD_TYPES:
            problems.append('invalid_input:%s.type is not one of %s' % (where, ', '.join(FIELD_TYPES)))
            continue
        choices = field.get('choices')
        if (field['type'] == 'choice') != ('choices' in field) or (choices is not None and (
                type(choices) is not list or not choices or len(set(map(str, choices))) != len(choices)
                or not all(type(c) is str and c and TEXT.match(c) and not CODE_LIKE & set(c) for c in choices))):
            problems.append('invalid_input:%s.choices' % where)
            continue
        if 'private' in field and type(field['private']) is not bool:
            problems.append('invalid_input:%s.private is not yes or no' % where)
            continue
        source = field['source']
        if type(source) is dict and set(source) == {'subject'} and _identifier(source['subject']):
            pass
        elif (type(source) is dict and set(source) == {'node', 'result'} and _identifier(source['result'])
              and type(source['node']) is str and (step_kind(nodes.get(source['node'])) or {}).get('input')
              == 'worker_result'):
            pass
        else:
            problems.append('invalid_input:%s.source is not {subject} or {node, result} of an assignment' % where)
            continue
        declared[name] = field
    return problems, declared


def _check_problems(name, config, fields):
    """Problems of one check node's closed configuration."""
    bad = 'unsupported_configuration:invalid_config:%s:' % name
    if type(config) is not dict:
        return [bad + 'config']
    problems = []
    if config.get('otherwise') is not True:
        problems.append('unsupported_configuration:check_without_otherwise:%s' % name)
    unknown = sorted(set(config) - set(CHECK_FIELDS))
    problems += [bad + key for key in unknown]
    branches = config.get('branches')
    if type(branches) is not list or not branches:
        return problems + [bad + 'branches']
    seen = set()
    for index, branch in enumerate(branches):
        if type(branch) is not dict or set(branch) != set(BRANCH_FIELDS):
            problems.append(bad + 'branches[%d]' % index)
            continue
        rule = branch['name']
        if not _identifier(rule) or rule == OTHERWISE or rule in seen:
            problems.append(bad + 'branches[%d].name' % index)
            continue
        seen.add(rule)
        conditions = branch['conditions']
        if type(conditions) is not list or not conditions:
            problems.append(bad + '%s.conditions' % rule)
            continue
        for condition in conditions:
            if type(condition) is not dict or set(condition) != set(CONDITION_FIELDS):
                problems.append(bad + '%s.condition' % rule)
                continue
            field = fields.get(condition['field']) if type(condition['field']) is str else None
            if field is None:
                problems.append('unsupported_configuration:undeclared_field:%s:%s' % (name, condition['field']))
                continue
            comparison = condition['comparison']
            if comparison not in FIELD_TYPES[field['type']]:
                problems.append('unsupported_configuration:unknown_comparison:%s:%s' % (name, comparison))
                continue
            value = condition['value']
            if comparison == 'is one of':
                verdicts = [_literal(field, item) for item in value] if type(value) is list and value else ['type']
            else:
                verdicts = [_literal(field, value)]
            if 'code_like' in verdicts:
                problems.append('unsupported_configuration:code_like_value:%s:%s' % (name, rule))
            elif 'type' in verdicts:
                problems.append('unsupported_configuration:value_type:%s:%s' % (name, rule))
    return problems


def _observed_type(field, value):
    """Whether an observed value is of the field's type."""
    kind = field['type']
    if kind == 'number':
        return type(value) is int
    if kind == 'yes_no':
        return type(value) is bool
    if type(value) is not str:
        return False
    return kind != 'choice' or value in field['choices']


def _holds(comparison, observed, value):
    if comparison == 'is':
        return observed == value
    if comparison == 'is not':
        return observed != value
    if comparison == 'less than':
        return observed < value
    if comparison == 'at most':
        return observed <= value
    if comparison == 'more than':
        return observed > value
    if comparison == 'at least':
        return observed >= value
    if comparison == 'contains':
        return value in observed
    return observed in value


def evaluate(name, config, fields, values):
    """THE CHECK, as data: (decision, None) or (None, 'invalid_input:field_unsupplied:<field>'). Every field the
    rules name must have a supplied value of its type, else the step fails and takes no branch. The decision is
    {node, branch, rule, conditions}: each condition of the taken rule and of every earlier rule with its observed
    value and whether it held. Nothing is evaluated, interpolated or run."""
    for branch in config['branches']:
        for condition in branch['conditions']:
            field = condition['field']
            if field not in values or not _observed_type(fields[field], values[field]):
                return None, 'invalid_input:field_unsupplied:%s' % field
    conditions = []
    for branch in config['branches']:
        results = []
        for condition in branch['conditions']:
            observed = values[condition['field']]
            held = bool(_holds(condition['comparison'], observed, condition['value']))
            results.append(held)
            conditions.append({'rule': branch['name'], 'field': condition['field'],
                               'comparison': condition['comparison'], 'value': condition['value'],
                               'observed': observed, 'holds': held})
        if all(results):
            return {'node': name, 'branch': branch['name'], 'rule': branch['name'], 'conditions': conditions}, None
    return {'node': name, 'branch': OTHERWISE, 'rule': OTHERWISE, 'conditions': conditions}, None


def redacted(decision, fields):
    """A decision as the record and the log hold it: a private field's observed value only as its digest."""
    out = dict(decision, conditions=[])
    for condition in decision['conditions']:
        if (fields.get(condition['field']) or {}).get('private'):
            condition = dict({k: v for k, v in condition.items() if k != 'observed'},
                             observed_digest=digest(canonical(condition['observed'])))
        out['conditions'].append(condition)
    return out


def plain_problems(value, where, floats=False):
    """Exact JSON types only, walked without recursion: a subclass, a tuple, a set, a non-string key,
    a non-finite number, or (unless `floats`) any float is a problem."""
    problems, stack = [], [(value, where, 1)]
    while stack:
        item, at, depth = stack.pop()
        kind = type(item)
        if depth > 32:
            problems.append('invalid_input:%s nests deeper than 32' % at)
        elif item is None or kind in (bool, int, str):
            continue
        elif kind is float:
            if not floats or not math.isfinite(item):
                problems.append('invalid_input:%s is not an allowed number' % at)
        elif kind is list:
            stack.extend((child, at + '[]', depth + 1) for child in item)
        elif kind is dict:
            for key, child in item.items():
                if type(key) is not str:
                    problems.append('invalid_input:%s has a non-string key' % at)
                else:
                    stack.append((child, at + '.' + key, depth + 1))
        else:
            problems.append('invalid_input:%s is %s, not plain data' % (at, kind.__name__))
    return problems


def _closed(value, required, optional=(), where='value'):
    """Problems for a mapping whose keys must be `required` plus any of `optional`, and no others."""
    if type(value) is not dict:
        return ['invalid_input:%s is not a mapping' % where]
    missing = [key for key in required if key not in value]
    unknown = sorted(set(value) - set(required) - set(optional))
    return (['invalid_input:%s lacks %s' % (where, key) for key in missing]
            + ['invalid_input:%s has unknown field %s' % (where, key) for key in unknown])


def _reference_problems(references):
    problems, declared = [], {}
    problems += _closed(references, (), tuple(REFERENCE_KINDS), 'references')
    if problems:
        return problems, declared
    for kind in REFERENCE_KINDS:
        table = references.get(kind, {})
        if type(table) is not dict:
            problems.append('invalid_input:references.%s is not a mapping' % kind)
            continue
        for key, ref in table.items():
            where = 'references.%s.%s' % (kind, key)
            if not _identifier(key):
                problems.append('invalid_input:%s is not an identifier' % where)
                continue
            shape = _closed(ref, REFERENCE_FIELDS, (), where)
            if shape:
                problems += shape
                continue
            if type(ref['id']) is not str or not ref['id'] or not _count(ref['version']) \
                    or type(ref['digest']) is not str or not DIGEST.match(ref['digest']):
                problems.append('invalid_input:%s is not {id, version, digest}' % where)
                continue
            declared[(kind, key)] = ref
    return problems, declared


def _node_problems(nodes, declared, fields=None):
    problems, used = [], set()
    for name, node in sorted(nodes.items()):
        where = 'nodes.' + str(name)
        if not _identifier(name) or name.startswith(RESERVED_PREFIX):
            problems.append('unsupported_configuration:reserved_or_invalid_node_id:%s' % name)
            continue
        shape = _closed(node, NODE_FIELDS, (), where)
        if shape:
            problems += shape
            continue
        kind = step_kind(node)
        if kind is None:
            problems.append('unsupported_configuration:unknown_step_kind:%s:%s' % (name, node['kind']))
            continue
        config = node['config']
        if node['kind'] == CHECK:
            problems += _check_problems(name, config, fields or {})
            continue
        if node['kind'] == JOIN:
            inputs = config.get('inputs') if type(config) is dict and set(config) == {'inputs'} else None
            if (type(inputs) is not list or len(inputs) < 2 or not all(_identifier(i) for i in inputs)
                    or len(set(inputs)) != len(inputs)):
                problems.append('unsupported_configuration:invalid_config:%s:inputs' % name)
            continue
        required = tuple(field for field, (_, needed) in kind['config'].items() if needed)
        shape = _closed(config, required, tuple(kind['config']), where + '.config')
        if shape:
            problems += ['unsupported_configuration:invalid_config:%s:%s' % (name, p.split(':', 1)[1]) for p in shape]
            continue
        for field, (reference, _) in kind['config'].items():
            if field not in config:
                continue
            if reference is None:
                # A plain field naming a node of this definition (owner_approval's `approves`).
                if not _identifier(config[field]) or config[field] not in nodes \
                        or not (step_kind(nodes[config[field]]) or {}).get('outward'):
                    problems.append('unsupported_configuration:invalid_config:%s:%s' % (name, field))
                continue
            keys = config[field] if field == 'tools' else [config[field]]
            if type(keys) is not list or not all(type(key) is str for key in keys) or len(set(keys)) != len(keys):
                problems.append('unsupported_configuration:invalid_config:%s:%s' % (name, field))
                continue
            for key in keys:
                if (reference, key) not in declared:
                    problems.append('unsupported_configuration:missing_reference:%s:%s/%s' % (name, reference, key))
                used.add((reference, key))
    return problems, used


def _transition_problems(nodes, transitions):
    problems, edges, seen_ids, seen_ports = [], [], set(), set()
    if type(transitions) is not list:
        return ['invalid_input:transitions is not a list'], edges
    for index, item in enumerate(transitions):
        where = 'transitions[%d]' % index
        shape = _closed(item, TRANSITION_FIELDS, TRANSITION_OPTIONAL, where)
        if shape:
            problems += shape
            continue
        tid, source, port, target = item['id'], item['from'], item['port'], item['to']
        if not _identifier(tid) or not all(type(v) is str for v in (source, port, target)):
            problems.append('invalid_input:%s is not {id, from, port, to} as identifiers' % where)
            continue
        if tid in seen_ids:
            problems.append('unsupported_configuration:duplicate_transition:%s' % tid)
            continue
        seen_ids.add(tid)
        if source not in nodes or target not in nodes:
            problems.append('unsupported_configuration:dangling_edge:%s:%s->%s' % (tid, source, target))
            continue
        kind = step_kind(nodes[source])
        if kind is None:
            continue
        if port not in node_ports(nodes[source]):
            problems.append('unsupported_configuration:unknown_port:%s:%s.%s' % (tid, source, port))
            continue
        # VELDO-0247: a port may lead to several transitions (a fan-out), never twice to one node; a check's
        # ports lead to exactly one each.
        if (source, port) in seen_ports and (nodes[source].get('kind') == CHECK or any(
                (e['from'], e['port'], e['to']) == (source, port, target) for e in edges)):
            problems.append('unsupported_configuration:duplicate_transition:%s:%s.%s' % (tid, source, port))
            continue
        seen_ports.add((source, port))
        if 'max' in item and not _count(item['max'], 1, STEP_CEILING):
            problems.append('unsupported_configuration:invalid_bound:%s' % tid)
            continue
        edges.append(item)
    for name, node in sorted(nodes.items()):
        for port in node_ports(node):
            if (name, port) not in seen_ports:
                problems.append('unsupported_configuration:missing_transition:%s.%s' % (name, port))
    wide = sorted({e['from'] for e in edges if sum(1 for o in edges if (o['from'], o['port']) == (e['from'], e['port']))
                   > FAN_OUT_CEILING})
    problems += ['unsupported_configuration:fan_out_too_wide:%s' % name for name in wide]
    return problems, edges


def fan_outs(edges):
    """{(node, port): [transitions]} of every port that leads to several transitions."""
    ports = {}
    for edge in edges:
        ports.setdefault((edge['from'], edge['port']), []).append(edge)
    return {key: found for key, found in ports.items() if len(found) > 1}


def block_problems(nodes, edges):
    """(problems, blocks) of every fan-out: each block is {fan_out, port, join, branches: {branch id: first node},
    regions: {branch id: set of nodes}}. Every branch reaches the one join naming exactly the fan-out's branch ids,
    no path leaves a branch except through that join, nothing enters a branch or the join from outside the block,
    and no fan-out or join lies inside a branch (branch_escapes_join, join_inputs)."""
    problems, blocks = [], []
    leaving = {}
    for edge in edges:
        leaving.setdefault(edge['from'], []).append(edge)
    joins = {name: node['config']['inputs'] for name, node in nodes.items()
             if node.get('kind') == JOIN and type(node.get('config')) is dict
             and type(node['config'].get('inputs')) is list}
    named = set()
    for (source, port), starts in sorted(fan_outs(edges).items()):
        ids = sorted(edge['id'] for edge in starts)
        join = [name for name, inputs in sorted(joins.items()) if sorted(inputs) == ids]
        if len(join) != 1:
            problems.append('unsupported_configuration:join_inputs:%s' % source)
            continue
        join = join[0]
        named.add(join)
        block = {'fan_out': source, 'port': port, 'join': join, 'branches': {e['id']: e['to'] for e in starts},
                 'regions': {}}
        for edge in starts:
            region, todo, arrives = set(), [edge['to']], False
            while todo:
                here = todo.pop()
                if here == join:
                    arrives = True
                    continue
                if here in region:
                    continue
                region.add(here)
                todo.extend(e['to'] for e in leaving.get(here, ()))
            block['regions'][edge['id']] = region
            if not arrives:
                problems.append('unsupported_configuration:branch_escapes_join:%s' % edge['to'])
        blocks.append(block)
    terminal = {name for name, node in nodes.items() if (step_kind(node) or {}).get('terminal')}
    for block in blocks:
        inside = set().union(*block['regions'].values())
        fanning = {key[0] for key in fan_outs(edges)}
        for branch, region in sorted(block['regions'].items()):
            others = set().union(*(r for b, r in block['regions'].items() if b != branch))
            for name in sorted(region):
                # Leaving: a terminal, the fan-out, another branch, a nested fan-out or join; entering from outside.
                entered = [e for e in edges if e['to'] == name and e['from'] not in region
                           and not (e['from'] == block['fan_out'] and e['id'] == branch)]
                if (name in terminal or name == block['fan_out'] or name in others or name in fanning
                        or name in joins or entered):
                    problems.append('unsupported_configuration:branch_escapes_join:%s' % name)
        if any(e['to'] == block['join'] and e['from'] not in inside for e in edges):
            problems.append('unsupported_configuration:join_inputs:%s' % block['join'])
    problems += ['unsupported_configuration:join_inputs:%s' % name for name in sorted(set(joins) - named)]
    return sorted(set(problems), key=problems.index), blocks


def _ring(nodes, edges):
    """A ring of transitions none of which is bounded, as a list of node names, or None."""
    graph = {name: [] for name in nodes}
    for edge in edges:
        if 'max' not in edge:
            graph.setdefault(edge['from'], []).append(edge['to'])
            graph.setdefault(edge['to'], [])
    state, path = {}, []
    for start in sorted(graph):
        if state.get(start):
            continue
        stack = [(start, iter(graph[start]))]
        state[start], path = 1, [start]
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                state[node] = 2
                stack.pop()
                path.pop()
            elif state.get(child) == 1:
                return path[path.index(child):] + [child]
            elif not state.get(child):
                state[child] = 1
                path.append(child)
                stack.append((child, iter(graph[child])))
    return None


def approval_problems(nodes, edges, entry):
    """VELDO-0241 AC2, over every path from the entry, cycles and back edges included: the edge taken out of the
    last owner_approval node before an outward node must be the `granted` port of an approval naming that node,
    and no step whose kind is not registered subject-preserving (`changes_subject: False`) lies between that edge
    and the outward node. Any other port of an approval (stopped, or any outcome a later kind adds) and any port of
    an approval naming another node leaves nothing approved. Complete by construction: a reachability over the
    finite product of node and state, the state being None (nothing approved), ('approved', A) or ('changed', A)
    (A granted, then a subject-changing step). Problems: invalid_input:missing_owner_approval:<outward node> when
    the node is reached with nothing approved, invalid_input:approval_not_last:<approval node> when it is reached
    after a subject-changing step that follows that approval's grant."""
    problems = []
    kinds = {name: step_kind(node) or {} for name, node in nodes.items()}
    leaving = {}
    for edge in edges:
        leaving.setdefault(edge['from'], []).append(edge)
    for target in sorted(name for name in nodes if kinds[name].get('outward')):
        missing, stale = False, set()
        seen, todo = {(entry, None)}, [(entry, None)]
        while todo:
            here, state = todo.pop()
            if here == target:
                if state is None:
                    missing = True
                elif state[0] == 'changed':
                    stale.add(state[1])
            node = nodes[here]
            for edge in leaving.get(here, ()):
                if node.get('kind') == APPROVAL:
                    names = (node.get('config') or {}).get('approves') == target
                    after = ('approved', here) if names and edge['port'] == GRANTED else None
                elif state is not None and kinds[here].get('changes_subject', True) is not False:
                    after = ('changed', state[1])
                else:
                    after = state
                if (edge['to'], after) not in seen:
                    seen.add((edge['to'], after))
                    todo.append((edge['to'], after))
        if missing:
            problems.append('invalid_input:missing_owner_approval:%s' % target)
        problems += ['invalid_input:approval_not_last:%s' % name for name in sorted(stale)]
    return problems


def ran_before(nodes, edges, entry, blocks):
    """{node: the nodes that have run on every path from the entry to it}. A fan-out and its join are one block:
    every branch runs before the join, so the join has after it whatever each of its branches had."""
    universe, incoming = set(nodes), {}
    for edge in edges:
        incoming.setdefault(edge['to'], []).append(edge)
    ran = {name: set(universe) for name in nodes}
    ran[entry] = set()
    joined = {block['join']: block for block in blocks}
    changed = True
    while changed:
        changed = False
        for name in sorted(nodes):
            arriving = incoming.get(name, [])
            if name == entry or not arriving:
                continue
            block = joined.get(name)
            if block is not None:
                parts = []
                for region in block['regions'].values():
                    ins = [e for e in arriving if e['from'] in region]
                    if ins:
                        parts.append(set.intersection(*[ran[e['from']] | {e['from']} for e in ins]))
                found = set().union(*parts) if parts else set(universe)
            else:
                found = set.intersection(*[ran[e['from']] | {e['from']} for e in arriving])
            if found != ran[name]:
                ran[name], changed = found, True
    return ran


def _source_problems(nodes, edges, entry, blocks, fields):
    """A field a check reads from a node's result must come from a node on every path to that check."""
    problems, ran = [], ran_before(nodes, edges, entry, blocks)
    for name, node in sorted(nodes.items()):
        if node.get('kind') != CHECK:
            continue
        named = []
        for branch in node['config']['branches']:
            named += [c['field'] for c in branch['conditions'] if c['field'] not in named]
        for field in named:
            source = fields[field]['source']
            if 'node' in source and source['node'] not in ran[name]:
                problems.append('unsupported_configuration:undeclared_field:%s:%s' % (name, field))
    return problems


def branch_approval_problems(nodes, blocks):
    """VELDO-0247 AC4: no owner_approval and no outward step inside a parallel branch; the approval sits before the
    fan-out or after the join. Named as VELDO-0241's problems, naming why."""
    problems = []
    for block in blocks:
        for name in sorted(set().union(*block['regions'].values())):
            kind = step_kind(nodes[name]) or {}
            if nodes[name].get('kind') == APPROVAL:
                problems.append('invalid_input:approval_not_last:approval_in_branch:%s' % name)
            if kind.get('outward'):
                problems.append('invalid_input:missing_owner_approval:outward_in_branch:%s' % name)
    return problems


def definition_problems(definition, resolve=None):
    """Every problem with a workflow definition, by name; [] when it is valid. `resolve(kind, ref)`
    (optional) answers whether a declared configuration reference names an accepted record."""
    problems = plain_problems(definition, 'definition')
    if problems:
        return problems
    problems = _closed(definition, DEFINITION_FIELDS, DEFINITION_OPTIONAL, 'definition')
    if problems:
        return problems
    if definition['schema'] != SCHEMA:
        problems.append('unsupported_configuration:schema:%r' % definition['schema'])
    if not _identifier(definition['id']):
        problems.append('invalid_input:definition.id is not an identifier')
    nodes = definition['nodes']
    if type(nodes) is not dict or not nodes:
        return problems + ['invalid_input:definition.nodes is not a non-empty mapping']
    reference_problems, declared = _reference_problems(definition['references'])
    problems += reference_problems
    field_problems, fields = _field_problems(definition.get('fields', {}), nodes)
    problems += field_problems
    node_problems, used = _node_problems(nodes, declared, fields)
    problems += node_problems
    problems += ['unsupported_configuration:unused_reference:%s/%s' % key for key in sorted(set(declared) - used)]
    if resolve is not None:
        for (kind, key), ref in sorted(declared.items()):
            if not resolve(kind, ref):
                problems.append('unsupported_configuration:missing_reference:%s/%s' % (kind, key))
    transition_problems, edges = _transition_problems(nodes, definition['transitions'])
    problems += transition_problems
    entry, terminal = definition['entry'], definition['terminal']
    if type(entry) is not str or entry not in nodes:
        problems.append('unsupported_configuration:unknown_entry:%s' % entry)
    terminals = sorted(name for name, node in nodes.items() if (step_kind(node) or {}).get('terminal'))
    if (type(terminal) is not list or not all(type(name) is str for name in terminal)
            or sorted(terminal) != terminals or not terminals or len(set(terminal)) != len(terminal)):
        problems.append('unsupported_configuration:terminal_mismatch:%s' % ','.join(terminals))
    if type(entry) is str and entry in nodes:
        reached, todo = {entry}, [entry]
        while todo:
            here = todo.pop()
            for edge in edges:
                if edge['from'] == here and edge['to'] not in reached:
                    reached.add(edge['to'])
                    todo.append(edge['to'])
        problems += ['unsupported_configuration:unreachable_node:%s' % name for name in sorted(set(nodes) - reached)]
        # VELDO-0247: the block structure of every fan-out, then the approval walk over every path, every check
        # branch (otherwise included) being a port it follows; a fan-out's branches are each walked to the join,
        # which is the block rule (a subject-changing step in any branch precedes whatever follows the join).
        structure, blocks = block_problems(nodes, edges)
        problems += structure
        if not node_problems and not field_problems and not structure:
            problems += _source_problems(nodes, edges, entry, blocks, fields)
        problems += branch_approval_problems(nodes, blocks)
        problems += approval_problems(nodes, edges, entry)
    ring = _ring(nodes, edges)
    if ring is not None:
        problems.append('unsupported_configuration:unbounded_cycle:%s' % '->'.join(ring))
    budget = definition['budget']
    shape = _closed(budget, BUDGET_FIELDS, (), 'budget')
    if shape or not _count(budget['steps'], 1, STEP_CEILING):
        problems.append('unsupported_configuration:invalid_budget')
    return problems


def layout_problems(layout, definition):
    """Problems with canvas metadata: only positions of the definition's own nodes and transitions,
    finite numbers, a positive zoom. It never carries execution semantics."""
    problems = plain_problems(layout, 'layout', floats=True)
    if problems:
        return problems
    problems = _closed(layout, (), LAYOUT_FIELDS, 'layout')
    if problems:
        return problems
    nodes = definition['nodes']
    transitions = {t['id'] for t in definition['transitions']}

    def number(value):
        return type(value) in (int, float) and math.isfinite(value)

    def point(value):
        return type(value) is list and len(value) == 2 and all(number(v) for v in value)

    places, edges = layout.get('nodes', {}), layout.get('transitions', {})
    if type(places) is not dict or type(edges) is not dict:
        return ['invalid_input:layout.nodes and layout.transitions are mappings']
    for name, place in sorted(places.items()):
        if name not in nodes:
            problems.append('invalid_input:layout.nodes.%s names no node' % name)
        elif _closed(place, ('x', 'y'), (), 'place') or not (number(place['x']) and number(place['y'])):
            problems.append('invalid_input:layout.nodes.%s is not {x, y}' % name)
    for tid, shape in sorted(edges.items()):
        if tid not in transitions:
            problems.append('invalid_input:layout.transitions.%s names no transition' % tid)
        elif (_closed(shape, ('points',), (), 'shape') or type(shape['points']) is not list
              or not all(point(p) for p in shape['points'])):
            problems.append('invalid_input:layout.transitions.%s is not {points}' % tid)
    if 'viewport' in layout:
        view = layout['viewport']
        if (_closed(view, ('x', 'y', 'zoom'), (), 'viewport') or not all(number(view[k]) for k in ('x', 'y', 'zoom'))
                or view['zoom'] <= 0):
            problems.append('invalid_input:layout.viewport is not {x, y, zoom > 0}')
    return problems


# The transition, inside the store's own transaction.

def _entity_row(conn, identity):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}


def _resolver(conn):
    """resolve(kind, ref): the reference names, at exactly its version and entity digest, a current
    accepted configuration entity of the kind REFERENCE_KINDS gives it."""
    def resolve(kind, ref):
        row = _entity_row(conn, ref['id'])
        return (row is not None and row['kind'] == REFERENCE_KINDS[kind] and row['version'] == ref['version']
                and row['digest'] == ref['digest'])
    return resolve


def editor_problem(conn, principal, repository, now):
    """None when `principal` may edit this repository's workflows: an active person member holding
    project_owner or technical_authority, scoped to the repository. Else the named refusal."""
    AC, CM = _organ('authority_contract'), _organ('control_membership')
    row = _entity_row(conn, principal) if type(principal) is str and principal else None
    if row is None or row['kind'] != 'membership':
        return 'unauthenticated:editor'
    entry = dict(row['data'], principal=principal)
    active, _why = AC.active_member(entry, now) if isinstance(now, (int, float)) else (False, 'clock')
    if (not active or entry.get('principal_type') not in EDITOR_TYPES
            or not set(entry.get('roles') or []) & set(EDITOR_ROLES)
            or not CM.scope_covers(entry.get('scope'), repository)):
        return 'missing_authority:editor'
    return None


def _save_transition(conn, params, before):
    """THE SAVE: an authorized editor's new immutable revision of a validated definition."""
    domain, repository, workflow = params.get('domain'), params.get('repository'), params.get('workflow')
    if not all(type(v) is str and v for v in (domain, repository)) or not _identifier(workflow):
        raise Refused('invalid_input', 'domain, repository and workflow are named')
    problem = editor_problem(conn, params.get('principal'), repository, params.get('now'))
    if problem:
        raise Refused(problem, str(params.get('principal')))
    # Read on the transaction's own connection, never from what the command declared.
    hid = head_id(domain, repository, workflow)
    head = _entity_row(conn, hid)
    if head is not None and head['kind'] != HEAD_KIND:
        raise Refused('invalid_input', hid + ' is not a workflow head')
    current = head['data']['version'] if head else 0
    if params.get('base') != current:
        raise Refused('stale_version', 'the edit starts from version %r; the head is %d' % (params.get('base'), current))
    version = current + 1
    rid = revision_id(domain, repository, workflow, version)
    if _entity_row(conn, rid) is not None:
        raise Refused('workflow_immutable', rid)
    definition, layout = params.get('definition'), params.get('layout')
    problems = definition_problems(definition, _resolver(conn))
    if not problems and definition['id'] != workflow:
        problems = ['invalid_input:definition.id is not the workflow saved']
    if not problems:
        problems = layout_problems(layout, definition)
    if problems:
        raise Refused(problems[0], '; '.join(problems), problems)
    record = {'schema': REVISION_SCHEMA, 'domain': domain, 'repository': repository, 'workflow': workflow,
              'version': version, 'definition': definition, 'definition_digest': definition_digest(definition),
              'layout': layout, 'layout_digest': digest(canonical(layout)),
              'previous': {'version': current, 'revision': head['data']['revision'], 'digest': head['data']['digest']}
              if head else None,
              'saved': {'principal': params['principal'], 'at': params['now']}}
    return {rid: {'kind': REVISION_KIND, 'data': record},
            hid: {'kind': HEAD_KIND, 'data': {'workflow': workflow, 'domain': domain, 'repository': repository,
                                              'version': version, 'revision': rid,
                                              'definition_digest': record['definition_digest'],
                                              'digest': definition_digest(record)}}}


def verified_revision(store, conn, domain, repository, workflow, version):
    """A stored revision re-read and checked: the entity digest, its identity and its definition digest.
    Returns (entity row, record) or raises Refused."""
    rid = revision_id(domain, repository, workflow, version)
    row = _entity_row(conn, rid)
    if row is None or row['kind'] != REVISION_KIND:
        raise Refused('missing_workflow', rid)
    data = row['data']
    if store.digest_of({'kind': row['kind'], 'data': data, 'version': row['version']}) != row['digest']:
        raise Refused('missing_evidence:revision_digest', rid)
    if ((data.get('schema'), data.get('domain'), data.get('repository'), data.get('workflow'), data.get('version'))
            != (REVISION_SCHEMA, domain, repository, workflow, version)
            or definition_digest(data.get('definition')) != data.get('definition_digest')
            or digest(canonical(data.get('layout'))) != data.get('layout_digest')):
        raise Refused('missing_evidence:revision_identity', rid)
    return dict(row, id=rid), data


def head_version(conn, domain, repository, workflow):
    row = _entity_row(conn, head_id(domain, repository, workflow))
    return row['data']['version'] if row and row['kind'] == HEAD_KIND else 0


class Workflows:
    """One domain and repository's workflow revisions over a real control store connection. `sign(bytes)
    -> text` signs journal records as `signer`; the editor of each save is the principal the caller's
    authenticated session names (VELDO-0130), judged against the store's membership."""

    def __init__(self, store, conn, *, domain, repository, signer, sign, generation=1, observe=None, clock=None):
        if not all(type(v) is str and v for v in (domain, repository, signer)):
            raise Refused('invalid_input', 'domain, repository and signer are named')
        self.store, self.conn = store, conn
        self.domain, self.repository = domain, repository
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        self.clock = clock or time.time
        self.counts = {'accepted': 0, 'refused': 0}
        # VELDO-0241: refused saves by each problem they named.
        self.refusals = {}
        store.declare_owners(conn, OWNER, kinds={REVISION_KIND: (SAVE,), HEAD_KIND: (SAVE,)}, module=__file__)
        conn.command_registry[SAVE] = {'transaction_transition': _save_transition, 'writes': WRITES}

    def _event(self, operation, workflow, **fields):
        return dict({'schema': REVISION_SCHEMA, 'operation': operation, 'domain': self.domain,
                     'repository': self.repository, 'workflow': workflow}, **fields)

    def _refused(self, event, error):
        self.counts['refused'] += 1
        codes = list(getattr(error, 'codes', None) or [error.code])
        for code in codes:
            self.refusals[code] = self.refusals.get(code, 0) + 1
        self.observe(dict(event, outcome='refused', refusal=error.code, refusals=codes, taxonomy=taxonomy(error.code)))

    def save(self, document, *, principal, base):
        """Commit the canvas document {definition, layout} as the next revision after `base`; returns
        {workflow, version, revision, definition_digest, layout_digest, seq} or raises Refused."""
        document = document if type(document) is dict else {}
        definition, layout = document.get('definition'), document.get('layout', {})
        workflow = definition.get('id') if type(definition) is dict else None
        event = self._event('save', workflow, actor=principal, base=base)
        shape = _closed(document, ('definition',), ('layout',), 'document') if document else ['invalid_input:document']
        if shape or not _identifier(workflow) or not _count(base, 0):
            error = Refused((shape or ['invalid_input'])[0], 'a document {definition, layout} and a base version', shape)
            self._refused(event, error)
            raise error
        hid = head_id(self.domain, self.repository, workflow)
        current = head_version(self.conn, self.domain, self.repository, workflow)
        version = current + 1
        rid = revision_id(self.domain, self.repository, workflow, version)
        params = {'domain': self.domain, 'repository': self.repository, 'workflow': workflow, 'base': base,
                  'definition': definition, 'layout': layout, 'principal': principal, 'now': self.clock()}
        expected = {hid: (_entity_row(self.conn, hid) or {}).get('version', 0), rid: 0}
        try:
            problems = plain_problems(document, 'document', floats=True)
            if problems:
                raise Refused(problems[0], '; '.join(problems), problems)
            command_id = 'workflow/save/' + digest(canonical(params))[len('sha256:'):][:32]
            command = {'command_id': command_id, 'principal': principal if type(principal) is str and principal else '-',
                       'operation': SAVE, 'parameters': params, 'expected_versions': expected, 'artifact_digests': [],
                       'nonce': command_id + '/nonce'}
            result = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused, ValueError, TypeError) as error:
            if not isinstance(error, (Refused, self.store.StoreRefused)):
                error = Refused('invalid_input', 'the document is not plain data: ' + type(error).__name__)
            elif isinstance(error, self.store.StoreRefused):
                error = Refused(error.code, error.detail)
            self._refused(event, error)
            raise error
        row = _entity_row(self.conn, rid)
        answer = {'workflow': workflow, 'version': version, 'revision': rid, 'entity_digest': row['digest'],
                  'definition_digest': row['data']['definition_digest'], 'layout_digest': row['data']['layout_digest'],
                  'seq': result['seq']}
        self.counts['accepted'] += 1
        self.observe(dict(event, outcome='accepted', version=version, record=rid, watermark=result['seq'],
                          definition_digest=answer['definition_digest'], layout_digest=answer['layout_digest']))
        return answer

    def load(self, workflow, version=None):
        """The stored canvas document of one revision (the head when `version` is None): {workflow,
        version, revision, definition, layout, definition_digest, layout_digest, entity_digest,
        previous, saved}. Reads the store only; runs nothing."""
        event = self._event('load', workflow, requested=version)
        try:
            if not _identifier(workflow):
                raise Refused('invalid_input', 'a workflow identifier')
            if version is None:
                version = head_version(self.conn, self.domain, self.repository, workflow)
            if not _count(version):
                raise Refused('missing_workflow', workflow)
            row, data = verified_revision(self.store, self.conn, self.domain, self.repository, workflow, version)
        except (Refused, sqlite3.Error) as error:
            if not isinstance(error, Refused):
                error = Refused('unavailable_service:store', type(error).__name__)
            self._refused(event, error)
            raise error
        self.counts['accepted'] += 1
        self.observe(dict(event, outcome='accepted', version=version, record=row['id'],
                          definition_digest=data['definition_digest']))
        return {'workflow': workflow, 'version': version, 'revision': row['id'], 'entity_digest': row['digest'],
                'definition': data['definition'], 'layout': data['layout'],
                'definition_digest': data['definition_digest'], 'layout_digest': data['layout_digest'],
                'previous': data['previous'], 'saved': data['saved']}

    def history(self, workflow):
        """Every stored version of a workflow, oldest first, each {version, revision, definition_digest}."""
        current = head_version(self.conn, self.domain, self.repository, workflow) if _identifier(workflow) else 0
        out = []
        for version in range(1, current + 1):
            row, data = verified_revision(self.store, self.conn, self.domain, self.repository, workflow, version)
            out.append({'version': version, 'revision': row['id'], 'definition_digest': data['definition_digest'],
                        'entity_digest': row['digest']})
        return out
