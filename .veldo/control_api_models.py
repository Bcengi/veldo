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

Kind = collections.namedtuple('Kind', 'kind module constant spec')
ReadModel = collections.namedtuple('ReadModel', 'name route criterion_subject kinds')
Action = collections.namedtuple('Action', 'name route operation module command spec')
Gap = collections.namedtuple('Gap', 'criterion subject spec what')

# THE READ MODELS. Each kind names the module and constant that own it, so the suite can compare the
# registration with the owning module's own name for it.
READ_MODELS = (
    ReadModel('objectives', 'reads.objectives', 'projects/objectives', (
        Kind('intake_proposal', 'control_intake', 'PROPOSAL_KIND', 'VELDO-0126'),
        Kind('intake_question', 'control_intake', 'QUESTION_KIND', 'VELDO-0126'))),
    ReadModel('work', 'reads.work', 'backlog/specs/units', (
        Kind('accepted_document', 'control_alias', 'OWNED_KINDS', 'VELDO-0037'),
        Kind('document_version', 'control_alias', 'OWNED_KINDS', 'VELDO-0037'),
        Kind('accepted_revision', 'control_readset', 'REVISION_KINDS', 'VELDO-0035'),
        Kind('execution_unit', 'entity_contract', 'ENTITY_TYPES', 'VELDO-0031'))),
    ReadModel('workers', 'reads.workers', 'machines/workers', (
        Kind('dispatch', 'control_dispatch', 'RECORD_KIND', 'VELDO-0039'),
        Kind('dispatch_active', 'control_dispatch', 'INDEX_KIND', 'VELDO-0039'))),
    ReadModel('runs', 'reads.runs', 'run steps/tool calls', (
        Kind('workflow_cycle', 'control_workflow_cycle', 'CYCLE_KIND', 'VELDO-0132'),)),
    ReadModel('decisions', 'reads.decisions', 'decisions', (
        Kind('assignment', 'control_assignment', 'ENTITY_KIND', 'VELDO-0064'),
        Kind('settlement_terms', 'control_request_settlement', 'TERMS_KIND', 'VELDO-0068'),
        Kind('request_settlement', 'control_request_settlement', 'SETTLEMENT_KIND', 'VELDO-0068'),
        Kind('decision_settlement', 'control_request_settlement', 'DECISION_SETTLEMENT_KIND', 'VELDO-0069'),
        Kind('decision', 'control_request_settlement', 'GOVERNING_RECORD_KIND', 'VELDO-0069'),
        Kind('channel_presentation', 'control_channel_presentation', 'RECEIPT_KIND', 'VELDO-0065'))),
    ReadModel('proof', 'reads.proof', 'gate/review/proof', (
        Kind('proof_bundle', 'control_proof', 'BUNDLE_KIND', 'VELDO-0050'),
        Kind('gate_observation', 'control_proof', 'OBSERVATION_KIND', 'VELDO-0058'),
        Kind('completion_receipt', 'control_event_projection', 'RECEIPT_KIND', 'VELDO-0021'))),
    ReadModel('spend', 'reads.spend', 'spend', (
        Kind('subscription_reservation', 'control_reservations', None, 'VELDO-0036'),)),
    ReadModel('configuration', 'reads.configuration', 'configuration/workflows', (
        Kind('workflow_head', 'control_workflow', 'HEAD_KIND', 'VELDO-0132'),
        Kind('workflow_revision', 'control_workflow', 'REVISION_KIND', 'VELDO-0132'),
        Kind('role_configuration', 'control_workflow', 'REFERENCE_KINDS', 'VELDO-0127'),
        Kind('tool_configuration', 'control_workflow', 'REFERENCE_KINDS', 'VELDO-0127'))),
)
MODELS = {m.name: m for m in READ_MODELS}

# THE UI ACTION CONTRACT. An action with a route executes the named existing command; an action without
# one is a gap owned by the named specification.
ACTIONS = (
    Action('send_message', 'messages.send', 'send_message', 'control_intake', 'RECORD', 'VELDO-0126'),
    Action('answer_decision', 'decisions.answer', 'answer_decision', 'control_request_settlement', 'API', 'VELDO-0068'),
    Action('revoke_credential', 'auth.revoke_credential', 'revoke_credential', 'control_api_credentials', 'REVOKE',
           'VELDO-0130'),
    Action('workflow_save', 'workflows.save', 'save_workflow', 'control_workflow', 'SAVE', 'VELDO-0132'),
    Action('owner_admission', None, None, None, None, 'VELDO-0079'),
    Action('owner_priority', None, None, None, None, 'VELDO-0078'),
    Action('project_pause', None, None, None, None, 'VELDO-0076'),
    Action('project_cancel', None, None, None, None, 'VELDO-0076'),
    Action('worker_stop', None, None, None, None, 'VELDO-0041'),
    Action('team_configuration_edit', None, None, None, None, 'VELDO-0089'),
    Action('agent_configuration_edit', None, None, None, None, 'VELDO-0127'),
)

GAPS = (
    Gap('AC2', 'projects', 'VELDO-0076', 'no project record (owner, charter, lifecycle) is written by the engine yet'),
    Gap('AC2', 'accepted objectives', 'VELDO-0077', 'objectives are served as the intake proposals of VELDO-0126; '
        'no accepted objective record exists yet'),
    Gap('AC2', 'backlog items and their nesting', 'VELDO-0078', 'no backlog item is written by the engine yet, so '
        'specs and units are served flat'),
    Gap('AC2', 'machine registry', 'VELDO-0125', 'machines are derived from the host and platform each dispatch '
        'recorded; no machine or host capability record exists yet'),
    Gap('AC2', 'tool calls', None, 'no specification records a worker\'s tool calls in the store; VELDO-0131 AC2 '
        'consumes them; run steps are the workflow cycles\' traces'),
    Gap('AC2', 'team configuration', 'VELDO-0089', 'no team configuration record is written by the engine yet'),
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


def _item(store, conn, row):
    """(served item, redacted paths), or (None, the problem) for an entity that does not verify."""
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
    served, paths = redact(data, '$.' + identity)
    return {'id': identity, 'kind': kind, 'version': version, 'digest': digest, 'data': served}, paths


def read_model(store, conn, name):
    """One read model from the authority's connection, in one read transaction at one watermark."""
    model = MODELS[name]
    kinds = [k.kind for k in model.kinds]
    items, problems, redacted = {k: [] for k in kinds}, [], []
    opened = not conn.in_transaction
    if opened:
        conn.execute('BEGIN')
    try:
        mark = watermark(conn)
        for row in conn.execute('SELECT id, kind, version, digest, data FROM entities WHERE kind IN (%s) '
                                'ORDER BY kind, id' % ','.join('?' * len(kinds)), kinds).fetchall():
            item, extra = _item(store, conn, row)
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


def _gap_of(gap, name):
    return {'projects': 'objectives', 'accepted objectives': 'objectives', 'backlog items and their nesting': 'work',
            'machine registry': 'workers', 'tool calls': 'runs', 'team configuration': 'configuration'}.get(gap.subject) == name


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


def contract():
    """The published contract the UI reads: read models with their kinds, actions and gaps."""
    return {'schema': 'veldo.api_contract/v1',
            'read_models': [{'name': m.name, 'route': m.route, 'subject': m.criterion_subject,
                             'kinds': [k.kind for k in m.kinds]} for m in READ_MODELS],
            'actions': [a._asdict() for a in ACTIONS], 'gaps': [g._asdict() for g in GAPS]}
