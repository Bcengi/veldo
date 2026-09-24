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


def _count(value, low=1, high=None):
    return type(value) is int and value >= low and (high is None or value <= high)


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


def _node_problems(nodes, declared):
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
        required = tuple(field for field, (_, needed) in kind['config'].items() if needed)
        shape = _closed(config, required, tuple(kind['config']), where + '.config')
        if shape:
            problems += ['unsupported_configuration:invalid_config:%s:%s' % (name, p.split(':', 1)[1]) for p in shape]
            continue
        for field, (reference, _) in kind['config'].items():
            if field not in config:
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
        if port not in kind['ports']:
            problems.append('unsupported_configuration:unknown_port:%s:%s.%s' % (tid, source, port))
            continue
        if (source, port) in seen_ports:
            problems.append('unsupported_configuration:duplicate_transition:%s:%s.%s' % (tid, source, port))
            continue
        seen_ports.add((source, port))
        if 'max' in item and not _count(item['max'], 1, STEP_CEILING):
            problems.append('unsupported_configuration:invalid_bound:%s' % tid)
            continue
        edges.append(item)
    for name, node in sorted(nodes.items()):
        for port in (step_kind(node) or {}).get('ports', ()):
            if (name, port) not in seen_ports:
                problems.append('unsupported_configuration:missing_transition:%s.%s' % (name, port))
    return problems, edges


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


def definition_problems(definition, resolve=None):
    """Every problem with a workflow definition, by name; [] when it is valid. `resolve(kind, ref)`
    (optional) answers whether a declared configuration reference names an accepted record."""
    problems = plain_problems(definition, 'definition')
    if problems:
        return problems
    problems = _closed(definition, DEFINITION_FIELDS, (), 'definition')
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
    node_problems, used = _node_problems(nodes, declared)
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
        store.declare_owners(conn, OWNER, kinds={REVISION_KIND: (SAVE,), HEAD_KIND: (SAVE,)}, module=__file__)
        conn.command_registry[SAVE] = {'transaction_transition': _save_transition, 'writes': WRITES}

    def _event(self, operation, workflow, **fields):
        return dict({'schema': REVISION_SCHEMA, 'operation': operation, 'domain': self.domain,
                     'repository': self.repository, 'workflow': workflow}, **fields)

    def _refused(self, event, error):
        self.counts['refused'] += 1
        codes = list(getattr(error, 'codes', None) or [error.code])
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
