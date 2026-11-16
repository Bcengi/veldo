#!/usr/bin/env python3
"""The authenticated API's published read models and UI action contract (VELDO-0130 AC2 and AC4).

WHAT THIS MODULE IS. Three published tables and the authority-side reader they drive, all plain data:

  READ_MODELS  every read model the API serves: its name, its route, and the store entity kinds it
               reads, each named with the module and constant that own the kind and the specification
               that writes it. A read is the authority's inspection of its own committed store, the one
               store every owning module writes; no second store, cache or projection is kept here.
  ACTIONS      the UI action contract: every owner action the UI offers, the API route and authority
               operation that carry it, and the existing typed domain command it executes. An action
               whose domain command does not exist yet in the engine names its owning specification as
               a gap and has no route, so the UI can never offer an action that writes nothing real.
  GAPS         every read model or action the criteria name that has no reader or command in the
               engine yet, with the specification that owns it.

THE READ (`read_model`), on the authority's own store connection: every entity of the model's kinds,
each with its identity, kind, concurrency version and entity digest, re-checked here against the store's
own digest formula, so an entity whose bytes do not match its digest is reported as missing evidence and
never served as state. Workflow revisions are also checked by VELDO-0132's verified_revision (identity
and definition digest). Every answer carries its freshness: the journal watermark it was read at (the
head sequence and that record's digest and commit time) and `freshness` "live", because it was read
from the authority's committed state in this request. What comes from the VELDO-0051 publication (the
published events) is labeled with the publication's own watermark and is "stale", with the count of
committed records not yet published, whenever that watermark is behind the journal head. Nothing is
ever labeled live that was not read at the head.

REDACTION (`redact`). Every served value is walked: a field whose name is a credential or signature
field, or a mapping of environment or headers, is replaced by the marker, and so is any text the
engine's secret scanner finds by its own full detection (secret_scan.scan_text: its known credential
shapes and its entropy detector, which catches a key no pattern covers yet). The paths redacted are
returned with the value.

THE SPACE READS (VELDO-0319, design 6.6 and 10). SPACE_MODEL names the space ledger's kinds the console's
Space screen is served from, each with its project rule, and SPACE_VIEWS the four reads made of them:

  space.usage    bytes and item counts by scope, then ticket, then kind, over every item that is still
                 there (SPACE_LIVE: declared, present, due, deferred, removing and kept), so a deferred item
                 counts until it is removed. Each plain repository and no project is a row of its own.
  space.pending  every due and every deferred item with its reason in words (deferral_words), the event it
                 was refused at, the events that retry it and its decision request; the requests, each with
                 the members it lists by index.
  space.removed  every removed item, newest first by the journal record that last wrote it, with its event,
                 its size and the pool's free space before and after.
  space.pools    every pool with its floor and what is held on it (admitted and advised holds, each need less
                 what the run's own items already use: control_space_admission.held), and under it the
                 waiting and the advised holds with need, free, held and floor as the ledger recorded them.

They are computed here, from one read_model of SPACE_MODEL at one watermark, and are plain data: no figure
is measured in a read, so the read touches no filesystem. An item that is not a project's (a plain
repository's, or no project's) is served only to a member whose scope is universal.

WHAT IT IS NOT. Not the transport, not a writer, not a cache. Standard library only.
"""
import collections
import importlib.util
import json
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('api_models_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SCAN = _organ('secret_scan')
WF = _organ('control_workflow')
SCHEMA = 'veldo.api_read/v1'
MARKER = '[redacted]'
# Field names whose values are credentials, key material or signatures, wherever they appear.
CREDENTIAL_FIELDS = frozenset({
    'signature', 'domain_signature', 'enrollee_signature', 'authentication', 'envelope', 'proof', 'public_key',
    'connection_public_key', 'private_key', 'token', 'csrf_token', 'cookie', 'secret', 'password', 'passphrase',
    'api_key', 'access_token', 'refresh_token', 'bot_token', 'authorization'})
CREDENTIAL_SUFFIXES = ('_signature', '_token', '_secret', '_password', '_private_key')
# Mappings whose every value is configuration a process reads at run time (an MCP server's
# environment, a request's headers): served by name only.
OPAQUE_MAPPINGS = frozenset({'env', 'environment', 'headers'})

Kind = collections.namedtuple('Kind', 'kind module constant spec project_rule')
ReadModel = collections.namedtuple('ReadModel', 'name route criterion_subject kinds')
Action = collections.namedtuple('Action', 'name route operation module command spec')
Gap = collections.namedtuple('Gap', 'criterion subject spec what')

# THE READ MODELS. Each kind names the module and constant that own it, so the suite can compare the
# registration with the owning module's own name for it. Projects (VELDO-0076), objectives (VELDO-0077),
# backlog items with their nesting (objective_uuid, and the feature an item was taken from; VELDO-0078) and
# teams (VELDO-0089) are served from their writers' own records. Each registration declares how
# its project is resolved. Only explicit shared kinds are available to every current member.
READ_MODELS = (
    ReadModel('objectives', 'reads.objectives', 'projects/objectives', (
        Kind('project', 'control_project', 'KIND', 'VELDO-0076', ('field', 'name')),
        Kind('objective', 'control_objective', 'KIND', 'VELDO-0077', ('field', 'project')),
        Kind('intake_proposal', 'control_intake', 'PROPOSAL_KIND', 'VELDO-0126', ('intake',)),
        Kind('intake_question', 'control_intake', 'QUESTION_KIND', 'VELDO-0126', ('reference', 'proposal_id')))),
    ReadModel('work', 'reads.work', 'backlog/specs/units', (
        Kind('backlog_item', 'control_backlog', 'KIND', 'VELDO-0078', ('field', 'project')),
        Kind('accepted_document', 'control_alias', 'OWNED_KINDS', 'VELDO-0037', ('repository', 'repository_uuid')),
        Kind('document_version', 'control_alias', 'OWNED_KINDS', 'VELDO-0037', ('repository', 'repository_uuid')),
        Kind('accepted_revision', 'control_readset', 'REVISION_KINDS', 'VELDO-0035', ('repository', 'repository_uuid')),
        Kind('execution_unit', 'entity_contract', 'ENTITY_TYPES', 'VELDO-0031', ('field', 'project')))),
    ReadModel('workers', 'reads.workers', 'machines/workers', (
        Kind('dispatch', 'control_dispatch', 'RECORD_KIND', 'VELDO-0039', ('field', 'contract.reservation.project')),
        Kind('dispatch_active', 'control_dispatch', 'INDEX_KIND', 'VELDO-0039', ('reference', 'unit')))),
    ReadModel('runs', 'reads.runs', 'run steps/tool calls', (
        Kind('workflow_cycle', 'control_workflow_cycle', 'CYCLE_KIND', 'VELDO-0132', ('reference', 'subject')),)),
    ReadModel('decisions', 'reads.decisions', 'decisions', (
        Kind('assignment', 'control_assignment', 'ENTITY_KIND', 'VELDO-0064', ('field', 'scope')),
        Kind('settlement_terms', 'control_request_settlement', 'TERMS_KIND', 'VELDO-0068', ('request',)),
        Kind('request_settlement', 'control_request_settlement', 'SETTLEMENT_KIND', 'VELDO-0068', ('reference', 'request_id')),
        Kind('decision_settlement', 'control_request_settlement', 'DECISION_SETTLEMENT_KIND', 'VELDO-0069', ('reference', 'settlement.request_id')),
        Kind('decision', 'control_request_settlement', 'GOVERNING_RECORD_KIND', 'VELDO-0069', ('reference', 'subject.id')),
        Kind('channel_presentation', 'control_channel_presentation', 'RECEIPT_KIND', 'VELDO-0065', ('reference', 'request_id')))),
    ReadModel('proof', 'reads.proof', 'gate/review/proof', (
        Kind('proof_bundle', 'control_proof', 'BUNDLE_KIND', 'VELDO-0050', ('reference', 'unit')),
        Kind('gate_observation', 'control_proof', 'OBSERVATION_KIND', 'VELDO-0058', ('repository', 'repository')),
        Kind('completion_receipt', 'control_event_projection', 'RECEIPT_KIND', 'VELDO-0021', ('reference', 'subject.id')))),
    ReadModel('spend', 'reads.spend', 'spend', (
        Kind('subscription_reservation', 'control_reservations', None, 'VELDO-0036', ('reservation',)),
        # VELDO-0131 (review-2026-11-01 F4): the accounts the reservations charge, so the spend view can name each
        # account's provider. An account is factory scope (control_accounts), so it is shared like a configuration.
        Kind('account', 'control_accounts', 'KIND', 'VELDO-0062', ('shared',)))),
    ReadModel('configuration', 'reads.configuration', 'configuration/workflows', (
        Kind('workflow_head', 'control_workflow', 'HEAD_KIND', 'VELDO-0132', ('field', 'repository')),
        Kind('workflow_revision', 'control_workflow', 'REVISION_KIND', 'VELDO-0132', ('field', 'repository')),
        Kind('default_team_revision', 'control_team_routes', 'KIND', 'VELDO-0162', ('shared',)),
        Kind('team', 'control_team', 'KIND', 'VELDO-0089', ('field', 'project')),
        Kind('role_configuration', 'control_workflow', 'REFERENCE_KINDS', 'VELDO-0127', ('shared',)),
        Kind('tool_configuration', 'control_workflow', 'REFERENCE_KINDS', 'VELDO-0127', ('shared',)),
        # VELDO-0131 (review-2026-11-01 F3): the kinds VELDO-0127's writer actually stores, so every stored role
        # configuration and skill is served, not only those a team names.
        Kind('agent_configuration', 'control_agent_config', 'KINDS', 'VELDO-0127', ('shared',)),
        Kind('agent_skill', 'control_agent_config', 'KINDS', 'VELDO-0127', ('shared',)))),
)
MODELS = {m.name: m for m in READ_MODELS}

# VELDO-0131 (review-2026-11-01 F1 and F4): two metadata-only reads the factory screens need, served by their own
# configuration-family routes (control_api.ROUTES) through the same authority read, member check and scope as the
# read models. They are not criterion subjects of VELDO-0130's AC2, so they are kept apart from READ_MODELS.
#   catalog       the MCP catalog's heads and revisions (VELDO-0144) and the credential records (metadata only:
#                 the record holds no value, and CREDENTIAL_METADATA is every field served of one)
#   repositories  the repository records (VELDO-0161, VELDO-0143) and the Git identities (VELDO-0142), which are
#                 setup tables, not entities: each identity is served as IDENTITY_METADATA only, never its
#                 credential references
METADATA_READS = (
    ReadModel('catalog', 'mcp.list', 'MCP catalog and credential metadata', (
        Kind('mcp_server_head', 'control_mcp_catalog', 'HEAD_KIND', 'VELDO-0144', ('shared',)),
        Kind('mcp_server', 'control_mcp_catalog', 'KIND', 'VELDO-0144', ('shared',)),
        Kind('credential', 'control_credential', 'KIND', 'VELDO-0144', ('shared',)))),
    ReadModel('repositories', 'repositories.read', 'repositories and Git identities', (
        Kind('repository', 'control_repository', 'KIND', 'VELDO-0161', ('repository', 'repository')),)),
)
METADATA = {m.name: m for m in METADATA_READS}
CREDENTIAL_METADATA = ('id', 'label', 'reference', 'set_at', 'set_by', 'deleted')
IDENTITY_METADATA = ('id', 'label', 'author_name', 'author_email', 'remote_host', 'remote_owner', 'projects_root',
                     'default_visibility')
SCOPE = _organ('control_api_models_scope')

# VELDO-0319 (design 6.6): the space ledger's kinds the Space screen is served from. An item, a hold and a
# review group name their scope (control_space.checked_scope: a project, a plain repository or no project),
# and a pool is the installation's. The four views below are made of one read of this model.
SPACE_MODEL = ReadModel('space', None, 'space ledger', (
    Kind('space_item', 'control_space', 'ITEM_KIND', 'VELDO-0297', ('field', 'owner.scope.id')),
    Kind('space_pool', 'control_space', 'POOL_KIND', 'VELDO-0297', ('shared',)),
    Kind('space_hold', 'control_space', 'HOLD_KIND', 'VELDO-0297', ('field', 'scope.id')),
    Kind('space_review_group', 'control_space', 'GROUP_KIND', 'VELDO-0340', ('field', 'scope.id'))))
SPACE_VIEWS = collections.OrderedDict((
    ('space.pools', 'pools'), ('space.usage', 'usage'), ('space.pending', 'pending'), ('space.removed', 'removed')))
SPACE_SCHEMA = 'veldo.api_space/v1'
# An item's states in which its thing is still there (control_space.LIVE), and those the owner is shown
# as pending removal.
SPACE_LIVE = ('declared', 'present', 'due', 'deferred', 'removing', 'kept')
SPACE_PENDING = ('due', 'deferred')
# The states in which a worktree takes the owner's Abandon (control_space.SIGNALLED), and its event.
SPACE_ABANDONED_FROM = ('present', 'kept', 'deferred')
SPACE_ABANDON_EVENT = 'worktree_abandoned'
# The holds whose promise is counted (control_space_admission.COUNTED), and those the screen lists.
SPACE_COUNTED = ('admitted', 'advised')
SPACE_LISTED = ('waiting', 'advised')


def reader_scope(conn, membership, scope):
    return SCOPE.ReaderScope(conn, membership, scope, {k.kind: k.project_rule
                                                       for m in READ_MODELS + METADATA_READS + (SPACE_MODEL,)
                                                       for k in m.kinds})

# THE UI ACTION CONTRACT. An action with a route executes the named existing command; an action without
# one is a gap owned by the named specification.
ACTIONS = (
    Action('mcp_server_save', 'mcp.save', 'save_mcp_server', 'control_mcp_catalog', 'SAVE', 'VELDO-0144'),
    Action('mcp_credential_set', 'mcp.credential_set', 'set_mcp_credential', 'control_credential', 'SET', 'VELDO-0144'),
    Action('mcp_credential_delete', 'mcp.credential_delete', 'delete_mcp_credential', 'control_credential', 'DELETE', 'VELDO-0144'),
    Action('send_message', 'messages.send', 'send_message', 'control_intake', 'RECORD', 'VELDO-0126'),
    Action('answer_decision', 'decisions.answer', 'answer_decision', 'control_request_settlement', 'API', 'VELDO-0068'),
    Action('revoke_credential', 'auth.revoke_credential', 'revoke_credential', 'control_api_credentials', 'REVOKE',
           'VELDO-0130'),
    Action('workflow_save', 'workflows.save', 'save_workflow', 'control_workflow', 'SAVE', 'VELDO-0132'),
    Action('owner_admission', None, None, None, None, 'VELDO-0079'),
    # VELDO-0131 (owner, Telegram 38184): the owner's backlog priority, worker stop and account cap, each the
    # existing writer's command reached through the API (control_api_authority._work).
    Action('owner_priority', 'backlog.reprioritize', 'reprioritize_backlog', 'control_backlog', 'OPERATION', 'VELDO-0078'),
    Action('project_pause', None, None, None, None, 'VELDO-0076'),
    Action('project_cancel', None, None, None, None, 'VELDO-0076'),
    Action('worker_stop', 'workers.stop', 'stop_worker', 'control_dispatch', 'OPERATION', 'VELDO-0041'),
    Action('worker_cap', 'workers.cap', 'set_account_cap', 'control_accounts', 'OPERATION', 'VELDO-0062'),
    Action('team_configuration_edit', 'teams.save', 'propose_team', 'control_team', 'OPERATION', 'VELDO-0162'),
    Action('agent_configuration_edit', 'configurations.save', 'save_capability_configuration',
           'control_agent_config', 'SAVE', 'VELDO-0162'),
    Action('default_team_edit', 'teams.default_save', 'save_default_team', 'control_team_routes', 'SAVE', 'VELDO-0162'),
    # VELDO-0312 (design 6.6): the owner's Abandon of one worktree, the space ledger's signal for that item.
    Action('space_reconcile', 'space.reconcile', 'reconcile_space', 'control_space', 'RECONCILE', 'VELDO-0315'),
    Action('worktree_abandon', 'space.abandon', 'abandon_worktree', 'control_space', 'SIGNAL', 'VELDO-0312'),
)

GAPS = (
    Gap('AC2', 'machine registry', 'VELDO-0125', 'machines are derived from the host and platform each dispatch '
        'recorded; no machine or host capability record exists yet'),
    Gap('AC2', 'tool calls', None, 'no specification records a worker\'s tool calls in the store; VELDO-0131 AC2 '
        'consumes them; run steps are the workflow cycles\' traces'),
) + tuple(Gap('AC4', a.name, a.spec, 'no typed authority command exists for it in the engine yet')
          for a in ACTIONS if a.route is None)


def redact(value, path='$'):
    """(the value with every credential replaced by the marker, the redacted paths)."""
    paths = []

    def walk(item, where, key=None):
        if key is not None and (key in CREDENTIAL_FIELDS or key.endswith(CREDENTIAL_SUFFIXES)) and item is not None:
            paths.append(where)
            return MARKER
        if isinstance(item, dict):
            if key in OPAQUE_MAPPINGS:
                paths.extend('%s.%s' % (where, k) for k in sorted(item))
                return {k: MARKER for k in item}
            return {k: walk(v, '%s.%s' % (where, k), k if isinstance(k, str) else None) for k, v in item.items()}
        if isinstance(item, list):
            return [walk(v, '%s[%d]' % (where, i)) for i, v in enumerate(item)]
        if isinstance(item, str) and SCAN.scan_text(item):
            paths.append(where)
            return MARKER
        return item

    return walk(value, path), paths


def watermark(conn):
    """The journal head this read is at: {seq, record_digest, committed_at}; seq 0 on an empty journal."""
    row = conn.execute('SELECT j.seq, j.record_digest, p.committed_at FROM journal j LEFT JOIN publication p '
                       'ON p.seq = j.seq ORDER BY j.seq DESC LIMIT 1').fetchone()
    return {'seq': row[0], 'record_digest': row[1], 'committed_at': row[2]} if row else \
        {'seq': 0, 'record_digest': None, 'committed_at': None}


def _item(store, conn, row, scope=None, plain=False):
    """(served item, redacted paths), or (None, the problem) for an entity that does not verify. With
    `plain` the data is not redacted here: the space views are computed from the records and redacted as
    views (space_view), since a redacted alias or path could no longer be joined or counted."""
    identity, kind, version, digest, text = row
    data = json.loads(text)
    if store.digest_of({'kind': kind, 'data': data, 'version': version}) != digest:
        return None, {'id': identity, 'kind': kind, 'refusal': 'missing_evidence:entity_digest'}
    if kind == WF.REVISION_KIND:
        try:
            checked, _record = WF.verified_revision(store, conn, data.get('domain'), data.get('repository'),
                                                    data.get('workflow'), data.get('version'))
        except WF.Refused as error:
            return None, {'id': identity, 'kind': kind, 'refusal': error.code}
        if checked['id'] != identity:
            return None, {'id': identity, 'kind': kind, 'refusal': 'missing_evidence:revision_identity'}
    if kind == 'credential':
        data = {k: data[k] for k in CREDENTIAL_METADATA if k in data}
    served_data = scope.project_data(kind, data) if scope is not None else data
    served, paths = (served_data, []) if plain else redact(served_data, '$.' + identity)
    # A route's dispatch is a public authority identity, even when its random suffix
    # resembles entropy in a credential. Retain only a dispatch that the store owns.
    route = data.get('route') if kind == 'intake_proposal' else None
    if isinstance(route, dict) and isinstance(route.get('dispatch'), str):
        dispatch = conn.execute("SELECT kind FROM entities WHERE id=?", ('dispatch:' + route['dispatch'],)).fetchone()
        if dispatch and dispatch[0] == 'dispatch' and isinstance(served.get('route'), dict):
            served['route']['dispatch'] = route['dispatch']
            paths = [p for p in paths if p != '$.' + identity + '.route.dispatch']
    return {'id': identity, 'kind': kind, 'version': version, 'digest': digest, 'data': served}, paths


def read_model(store, conn, name, scope=None, plain=False):
    """One read model (or metadata read) from the authority's connection, in one read transaction at one
    watermark. The repositories read's Git identities are added by the authority (`identities`). `plain` is
    for the space model alone, whose records are never served themselves (space_view redacts what is)."""
    if plain and name != SPACE_MODEL.name:
        raise ValueError('only the space model is read unredacted, for its views')
    model = MODELS.get(name) or METADATA.get(name) or {SPACE_MODEL.name: SPACE_MODEL}[name]
    kinds = [k.kind for k in model.kinds]
    items, problems, redacted = {k: [] for k in kinds}, [], []
    opened = not conn.in_transaction
    if opened:
        conn.execute('BEGIN')
    try:
        mark = watermark(conn)
        for row in conn.execute('SELECT id, kind, version, digest, data FROM entities WHERE kind IN (%s) '
                                'ORDER BY kind, id' % ','.join('?' * len(kinds)), kinds).fetchall():
            if scope is not None and not scope.visible(row[0], row[1], json.loads(row[4])):
                continue
            item, extra = _item(store, conn, row, scope=scope, plain=plain)
            if item is None:
                problems.append(extra)
                continue
            items[item['kind']].append(item)
            redacted.extend(extra)
    finally:
        if opened:
            conn.execute('COMMIT')
    answer = {'schema': SCHEMA, 'model': name, 'kinds': kinds, 'items': items, 'problems': problems,
              'redacted': redacted, 'watermark': mark, 'freshness': 'live',
              'gaps': [g._asdict() for g in GAPS if g.criterion == 'AC2' and _gap_of(g, name)]}
    if name == 'workers':
        answer['machines'] = machines(items['dispatch'])
    return answer


def identities(conn, domain, repositories, scope=None):
    """The Git identities of `domain` (control_git_identity's setup table), each as IDENTITY_METADATA only, with
    the repositories bound to it. A reader whose scope is not universal sees only the identities of the
    repositories it sees."""
    if not isinstance(domain, str):
        return []
    GI = _organ('control_git_identity')
    bound = {}
    if GI.exists(conn, 'git_identity_repositories'):
        for repository, identity in conn.execute('SELECT repository, identity FROM git_identity_repositories '
                                                 'WHERE domain=? ORDER BY repository', (domain,)):
            bound.setdefault(identity, []).append(repository)
    seen = {item['data'].get('identity') for item in repositories}
    visible = {item['id'] for item in repositories} | {item['data'].get('repository') for item in repositories}
    narrowed = scope is not None and not scope.universal
    served = []
    for record in GI.records(conn, domain):
        if narrowed and record.get('id') not in seen:
            continue
        # A narrowed reader sees only the bound repositories its own read serves, never the names of others.
        names = [r for r in bound.get(record.get('id'), []) if not narrowed or r in visible]
        value, _paths = redact(dict({k: record.get(k) for k in IDENTITY_METADATA}, repositories=names))
        served.append(value)
    return served


def _gap_of(gap, name):
    return {'machine registry': 'workers', 'tool calls': 'runs'}.get(gap.subject) == name


def machines(dispatches):
    """The machines the recorded dispatches ran on, from each dispatch's recorded process identity."""
    found = {}
    for item in dispatches:
        process = item['data'].get('process') if isinstance(item['data'].get('process'), dict) else None
        if process is None:
            continue
        key = (process.get('platform'), process.get('host'))
        entry = found.setdefault(key, {'platform': key[0], 'host': key[1], 'workers': [], 'running': []})
        entry['workers'].append(item['id'])
        if item['data'].get('state') == 'running':
            entry['running'].append(item['id'])
    return [found[k] for k in sorted(found, key=lambda k: (str(k[0]), str(k[1])))]


# ---------------------------------------------------------------------------------------------
# VELDO-0319: the space views. Plain functions of the served items of SPACE_MODEL.

def _mapping(value):
    return value if isinstance(value, dict) else {}


def _count(value):
    return value if type(value) is int and value >= 0 else 0


def _plural(count, one, many):
    return '%d %s' % (count, one if count == 1 else many)


def space_scope_key(scope):
    """(type, id) of a recorded scope; anything unreadable is no project."""
    scope = _mapping(scope)
    kind = scope.get('type') if scope.get('type') in ('project', 'plain_repository') else 'no_project'
    return kind, scope.get('id') if kind != 'no_project' and isinstance(scope.get('id'), str) else None


def space_locator(kind, locator):
    """An item's locator as one line: the path, the repository and ref of a branch, or the engine and
    name of a Docker object."""
    locator = _mapping(locator)
    if isinstance(locator.get('path'), str):
        return locator['path']
    if kind == 'branch':
        return '%s %s' % (locator.get('repository') or 'unknown repository', locator.get('ref') or 'unknown ref')
    if 'engine' in locator:
        return '%s on %s' % (locator.get('name') or locator.get('id') or 'unnamed', locator.get('engine'))
    return ''


def _owner_view(owner):
    owner = _mapping(owner)
    kind, identity = space_scope_key(owner.get('scope'))
    run = _mapping(owner.get('run'))
    return {'scope': {'type': kind, 'id': identity}, 'ticket': owner.get('ticket'),
            'run': run.get('id'), 'station': run.get('station'), 'gate': owner.get('gate'),
            'lane': owner.get('lane'), 'session': owner.get('session')}


def _unique_work_words(found):
    if found.get('no_space_worktree'):
        return 'kept after a run that ended with no space left'
    if 'unread' in found and 'cases' not in found and 'not_across' not in found:
        return 'its work could not be read'
    parts = []
    more = _mapping(found.get('more'))
    files = sum(len(found.get(name) or ()) + _count(more.get(name)) for name in ('modified', 'staged', 'untracked'))
    if files:
        parts.append('uncommitted changes in ' + _plural(files, 'file', 'files'))
    if found.get('operation'):
        parts.append('a git operation in progress (%s)' % found['operation'])
    if found.get('unlanded'):
        parts.append('commits that are not landed')
    if found.get('not_across'):
        refs = len(found['not_across']) + (_count(found.get('more')) if type(found.get('more')) is int else 0)
        parts.append('%s with commits the shared repository does not hold' % _plural(refs, 'ref', 'refs'))
    if found.get('stashes'):
        stashes = found['stashes']
        parts.append(_plural(len(stashes), 'stash', 'stashes') if isinstance(stashes, list) else 'stashed changes')
    return '; '.join(parts) or 'work that is in no other place'


def _in_use_words(deferral, found):
    refused_by = deferral.get('refused_by')
    if refused_by == 'registry' or 'held_by' in deferral:
        held = deferral.get('held_by')
        return ('waits for %s inside it' % _plural(len(held), 'item', 'items') if isinstance(held, (list, dict)) and held
                else 'waits for what is inside it')
    if refused_by == 'children' or 'items' in found:
        return 'holds %s that are still there' % _plural(len(found.get('items') or ()), 'item', 'items')
    process = _mapping(found.get('process'))
    if process.get('pid') is not None:
        return 'in use by process %s' % process['pid']
    if 'run' in found or 'gate' in found:
        run = _mapping(found.get('run'))
        if run.get('id'):
            return 'its run %s is not known to have ended' % run['id']
        return ('its gate %s is not known to have ended' % found['gate'] if found.get('gate')
                else 'its owner is not known to have ended')
    parts = []
    pids = [entry.get('pid') for entry in found.get('processes') or () if isinstance(entry, dict) and 'pid' in entry]
    if len(pids) == 1:
        parts.append('in use by process %s' % pids[0])
    elif pids:
        shown = ', '.join(str(pid) for pid in pids[:4]) + (' and more' if len(pids) > 4 else '')
        parts.append('in use by %d processes (%s)' % (len(pids), shown))
    containers = found.get('containers') or ()
    if containers:
        parts.append('mounted by ' + _plural(len(containers), 'container', 'containers'))
    git = _mapping(found.get('git'))
    if git.get('files') or git.get('worktree_locked'):
        parts.append('locked by git')
    if _mapping(found.get('scratch')).get('in_use'):
        parts.append('its scratch is borrowed by a running launcher')
    if not parts:
        return 'whether it is in use could not be read'
    return '; '.join(parts)


def deferral_words(deferral):
    """Why an item was not removed, in words the owner reads (design 10): the deferral the first refusing
    rule named (control_space_signal.DEFERRAL and the removers' own three), from what that rule found."""
    deferral = _mapping(deferral)
    rule, found = deferral.get('rule'), _mapping(deferral.get('found'))
    if rule == 'in_use':
        return _in_use_words(deferral, found)
    if rule == 'unique_work':
        return _unique_work_words(found)
    if rule == 'protected':
        return ('on the protect list (%s)' % found['entry'] if isinstance(found.get('entry'), str)
                else 'whether it is protected could not be read')
    if rule == 'not_in_ledger':
        return 'what is at its place is not what the ledger recorded'
    if rule == 'keep_failed':
        return 'its work could not be saved first, so it was not removed'
    if rule == 'remove_refused':
        return 'the remover refused it'
    return 'deferred by the rule %s' % rule if isinstance(rule, str) and rule else 'no reason is recorded'


def _sum(rows):
    return {'bytes': sum(row['bytes'] for row in rows), 'items': sum(row['items'] for row in rows),
            'unmeasured': sum(row['unmeasured'] for row in rows)}


def space_usage(items):
    """Bytes and item counts by scope, then ticket, then kind (design 6.6 and 10), over every item that is
    still there. An item never measured counts as an item and adds no bytes; `unmeasured` says how many.
    `worktrees` lists each worktree the owner's Abandon can be sent for (design 6.6: worktree abandoned,
    for one worktree), with the version a command names and whether it holds the owner's Keep."""
    cells, worktrees = {}, []
    for item in items:
        data = item['data']
        if data.get('state') not in SPACE_LIVE:
            continue
        owner, size = _mapping(data.get('owner')), _mapping(data.get('size'))
        if (data.get('kind') == 'worktree' and data.get('state') in SPACE_ABANDONED_FROM
                and SPACE_ABANDON_EVENT in (_mapping(data.get('ends_on')).get('events') or ())):
            worktrees.append({'id': item['id'], 'version': item['version'], 'state': data['state'],
                              'owner': _owner_view(owner), 'locator': space_locator('worktree', data.get('locator')),
                              'branch': data.get('branch'),
                              'bytes': size.get('bytes') if type(size.get('bytes')) is int else None,
                              'owner_keep': bool(data.get('owner_keep'))})
        key = (space_scope_key(owner.get('scope')), owner.get('ticket') if isinstance(owner.get('ticket'), str) else None,
               str(data.get('kind')))
        cell = cells.setdefault(key, {'bytes': 0, 'items': 0, 'unmeasured': 0, 'measured_at': set()})
        cell['items'] += 1
        if type(size.get('bytes')) is int:
            cell['bytes'] += size['bytes']
            if isinstance(size.get('event'), str):
                cell['measured_at'].add(size['event'])
        else:
            cell['unmeasured'] += 1
    order = {'project': 0, 'plain_repository': 1, 'no_project': 2}
    scopes = []
    for scope in sorted({key[0] for key in cells}, key=lambda one: (order[one[0]], one[1] or '')):
        tickets = []
        for ticket in sorted({key[1] for key in cells if key[0] == scope}, key=lambda one: (one is None, one or '')):
            kinds = [dict(kind=key[2], bytes=cell['bytes'], items=cell['items'], unmeasured=cell['unmeasured'],
                          measured_at=sorted(cell['measured_at']))
                     for key, cell in sorted(cells.items(), key=lambda pair: pair[0][2])
                     if key[0] == scope and key[1] == ticket]
            tickets.append(dict(_sum(kinds), ticket=ticket, kinds=kinds))
        scopes.append(dict(_sum(tickets), scope={'type': scope[0], 'id': scope[1]}, tickets=tickets))
    worktrees.sort(key=lambda row: (order[row['owner']['scope']['type']], row['owner']['scope']['id'] or '',
                                    row['owner']['ticket'] or '', row['locator'], row['id']))
    return {'scopes': scopes, 'total': _sum(scopes), 'worktrees': worktrees}


def space_pending(items, groups):
    """Every due and every deferred item (design 6.6 and 10) with its reason in words, the event it was
    refused at, the events that retry it and its decision request, and the requests: a single worktree's
    own, and a review group's one request with the members it lists, each by its index."""
    rows, requests = [], {}
    records = {group['id']: group['data'] for group in groups}
    for item in items:
        data = item['data']
        if data.get('state') not in SPACE_PENDING:
            continue
        deferral = _mapping(data.get('deferral')) if data.get('state') == 'deferred' else {}
        disposition = _mapping(data.get('disposition'))
        open_request = disposition.get('state') == 'requested' and isinstance(disposition.get('alias'), str)
        size = _mapping(data.get('size'))
        row = {'id': item['id'], 'version': item['version'], 'state': data.get('state'), 'kind': data.get('kind'),
               'owner': _owner_view(data.get('owner')), 'locator': space_locator(data.get('kind'), data.get('locator')),
               'pool': data.get('pool'), 'bytes': size.get('bytes') if type(size.get('bytes')) is int else None,
               'measured_at': size.get('event'), 'due_event': _mapping(data.get('due')).get('event'),
               'rule': deferral.get('rule'), 'reason': deferral_words(deferral) if deferral else None,
               'refused_at': deferral.get('event'), 'attempts': deferral.get('attempts'),
               'retry': [event for event in deferral.get('retry') or () if isinstance(event, str)],
               'request': disposition['alias'] if open_request else None,
               'group': disposition.get('group') if open_request else None,
               'index': disposition.get('index') if open_request else None}
        rows.append(row)
        if not open_request:
            continue
        group = _mapping(records.get(row['group'])) if row['group'] else {}
        current = _mapping(group.get('request'))
        # A member whose own request is not the group's current one waits for the request the Ledger
        # raises next: it is listed under the alias its own record names.
        proposal = _mapping(current.get('proposal')) if current.get('alias') == row['request'] else {}
        request = requests.setdefault(row['request'], {
            'alias': row['request'], 'group': row['group'],
            'day': group.get('day') if row['group'] else None, 'sequence': group.get('sequence') if row['group'] else None,
            'picks': [index for index in proposal.get('picks') or () if type(index) is int], 'members': []})
        request['members'].append({'item': item['id'], 'index': row['index']})
    for request in requests.values():
        request['members'].sort(key=lambda member: (member['index'] is None, member['index'] or 0, member['item']))
    rows.sort(key=lambda row: (row['state'] != 'deferred', row['owner']['scope']['type'], row['owner']['scope']['id'] or '',
                               row['owner']['ticket'] or '', row['locator'], row['id']))
    return {'items': rows, 'requests': [requests[alias] for alias in sorted(requests)]}


def space_removed(items, written):
    """Every removed item, newest first (design 6.6 and 10): what, whose, which event, how much and the
    pool's free space before and after. `written` is {item: (journal sequence, commit time)} of the record
    that last wrote each (space_written); an engine pool's host figure is served apart."""
    rows = []
    for item in items:
        data = item['data']
        if data.get('state') != 'removed':
            continue
        removal, size = _mapping(data.get('removal')), _mapping(data.get('size'))
        seq, at = written.get(item['id'], (None, None))
        kept = _mapping(data.get('kept'))
        measured = removal.get('bytes') if type(removal.get('bytes')) is int else size.get('bytes')
        rows.append({'id': item['id'], 'version': item['version'], 'kind': data.get('kind'),
                     'owner': _owner_view(data.get('owner')),
                     'locator': space_locator(data.get('kind'), data.get('locator')),
                     'pool': removal.get('pool') or data.get('pool'), 'event': removal.get('event'),
                     'emitter': removal.get('emitter'), 'method': removal.get('method'),
                     'bytes': measured if type(measured) is int else None,
                     'freed': removal.get('freed') if type(removal.get('freed')) is int else None,
                     'free_before': removal.get('pool_free_before'), 'free_after': removal.get('pool_free_after'),
                     'host': removal.get('host') if isinstance(removal.get('host'), dict) else None,
                     'kept_refs': len(_mapping(kept.get('refs'))), 'snapshots': len(kept.get('snapshots') or ()),
                     'seq': seq, 'at': at})
    rows.sort(key=lambda row: (-(row['seq'] or 0), row['id']))
    return {'items': rows}


def space_written(conn, identities):
    """{item: (journal sequence, commit time)} of the journal record that last wrote each of `identities`:
    one bounded pass over the journal, newest first, that stops when every one is found."""
    wanted, found = set(identities), {}
    if not wanted:
        return found
    rows = conn.execute("SELECT j.seq, j.after_versions, p.committed_at FROM journal j LEFT JOIN publication p "
                        "ON p.seq = j.seq WHERE instr(j.after_versions, 'space:item:') > 0 ORDER BY j.seq DESC")
    for seq, after, committed in rows:
        try:
            touched = json.loads(after)
        except ValueError:
            continue
        for identity in wanted.intersection(touched if isinstance(touched, dict) else ()):
            found[identity] = (seq, committed)
        wanted.difference_update(found)
        if not wanted:
            break
    return found


def space_pools(pools, holds, carried=None):
    """Every pool with its floor and what is held on it, and under it the waiting and the advised holds
    with need, free, held and floor as numbers (design 6.6, 6.7 and 10). `carried` is {hold: the run that
    carries it} for the holds a dispatch record names (the authority reads them)."""
    carried = carried or {}
    out = []
    for pool in sorted(pools, key=lambda one: one['id']):
        data, name = pool['data'], pool['data'].get('name')
        held, listed = 0, {state: [] for state in SPACE_LISTED}
        for hold in holds:
            record = hold['data']
            needs, used = _mapping(record.get('needs')), _mapping(record.get('used'))
            if record.get('state') in SPACE_COUNTED and name in needs:
                held += max(0, _count(needs.get(name)) - _count(used.get(name)))
            reason = _mapping(record.get('reason'))
            if record.get('state') in SPACE_LISTED and reason.get('pool') == name:
                kind, identity = space_scope_key(record.get('scope'))
                listed[record['state']].append(dict(
                    {field: reason.get(field) for field in ('need', 'free', 'held', 'floor')},
                    id=hold['id'], version=hold['version'], state=record['state'], pool=name,
                    scope={'type': kind, 'id': identity}, source=_mapping(record.get('source')).get(name),
                    run=carried.get(hold['id'])))
        out.append({'id': pool['id'], 'version': pool['version'], 'name': name, 'host': data.get('host'),
                    'type': data.get('type'), 'engine': data.get('engine'), 'backing': data.get('backing'),
                    'floor': data.get('floor'), 'returns_space': data.get('returns_space'), 'held': held,
                    'waiting': sorted(listed['waiting'], key=lambda one: one['id']),
                    'advised': sorted(listed['advised'], key=lambda one: one['id'])})
    return {'pools': out}


def space_view(conn, view, answer, universal, carried=None):
    """One space view from `answer`, the plain read of SPACE_MODEL at one watermark. A member whose scope is
    not universal is served the items, holds and groups of projects only: a plain repository and no
    project have no project a scope could cover. Every value is redacted like a read model's; the
    identities, which name what a command is sent for, are kept."""
    def served_to(scope):
        return universal or space_scope_key(scope)[0] == 'project'
    items = [item for item in answer['items']['space_item']
             if served_to(_mapping(item['data'].get('owner')).get('scope'))]
    holds = [hold for hold in answer['items']['space_hold'] if served_to(hold['data'].get('scope'))]
    groups = [group for group in answer['items']['space_review_group'] if served_to(group['data'].get('scope'))]
    if view == 'usage':
        body = space_usage(items)
    elif view == 'pending':
        body = space_pending(items, groups)
    elif view == 'removed':
        body = space_removed(items, space_written(conn, [item['id'] for item in items
                                                         if item['data'].get('state') == 'removed']))
    elif view == 'pools':
        body = space_pools(answer['items']['space_pool'], holds, carried)
    else:
        raise KeyError(view)
    kept = _identities(body)
    served, paths = redact(body, '$.' + view)
    _restore(served, kept)
    # A locator is a path, and the scanner reads a whole path as one long token. It is judged part by
    # part instead: a part the scanner finds is replaced, the rest of the path is served.
    located = [(path, _locator_served(text)) for path, text in _identities(body, fields=('locator',))]
    _restore(served, located)
    kept = kept + [(path, text) for path, text in located if MARKER not in text]
    named = {'$.' + view + ''.join('[%d]' % part if type(part) is int else '.' + part for part in path)
             for path, _original in kept}
    return dict(served, schema=SPACE_SCHEMA, view=view, problems=answer['problems'],
                redacted=sorted(set(paths) - named), watermark=answer['watermark'], freshness=answer['freshness'])


_IDENTITY_FIELDS = ('id', 'item', 'request', 'alias', 'group', 'run', 'dispatch')


def _identities(value, path=(), fields=_IDENTITY_FIELDS):
    """Every identity field of a view with its place, so the redaction can be undone for them alone: a store
    identity may look like a credential to the scanner, and a command names its subject by it."""
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in fields and isinstance(item, str):
                found.append((path + (key,), item))
            else:
                found.extend(_identities(item, path + (key,), fields))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_identities(item, path + (index,), fields))
    return found


def _locator_served(text):
    """A locator with each of its parts judged by the secret scanner alone: the parts between separators
    of a path, and the words of any other locator. A part the scanner finds is the marker."""
    def parts(piece, separators):
        if not separators:
            return MARKER if piece and SCAN.scan_text(piece) else piece
        return separators[0].join(parts(one, separators[1:]) for one in piece.split(separators[0]))
    return parts(text, ('/', ' '))


def _restore(value, kept):
    for path, original in kept:
        target = value
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = original


def contract():
    """The published contract the UI reads: read models with their kinds, actions and gaps."""
    return {'schema': 'veldo.api_contract/v1',
            'read_models': [{'name': m.name, 'route': m.route, 'subject': m.criterion_subject,
                             'kinds': [k.kind for k in m.kinds]} for m in READ_MODELS],
            'actions': [a._asdict() for a in ACTIONS], 'gaps': [g._asdict() for g in GAPS]}
