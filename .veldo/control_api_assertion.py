#!/usr/bin/env python3
"""The typed API assertion the authenticated API's edge signs for a session's member (VELDO-0130).

WHAT THIS MODULE IS. One shape, shared by the API (which builds it from the session alone), the
protected signer's "api" purpose (control_api_signer, which signs nothing else) and the authority
(control_api_authority, which verifies and executes it): `veldo.api_assertion/v1`. It names this
authority (domain name, domain, repository and store), the channel and edge, a single-use request id,
the session's principal and credential id, a session handle that is not the cookie, the operation, its
target and exact parameters, the expected versions, the issue time and an expiry 60 seconds later.

EACH OPERATION HAS ONE DOMAIN COMMAND, derived here (`domain_request`) and never written by a caller: a
message is VELDO-0126's API intake request unchanged, carrying the assertion's principal; a decision
answer is VELDO-0068's API answer on channel api; a credential revocation executes
revoke_api_credential and a workflow save executes VELDO-0132's Workflows.save (the store command
save_workflow_revision) for the assertion's principal, and neither has a separate signed request.
The signer signs the assertion and its derived request, and the authority derives the request again
from the verified assertion, so the command executed is exactly the one the assertion names.

THE CALLS (phase 3). The API reaches the authority only through the VELDO-0047 authority service socket
over VELDO-0107, one request per call, and each request's command is one API call built here
(`call_command`): {"operation": "api_call", "call": <name>, "arguments": {...}} with exactly the
arguments CALLS names. `apply` carries one signed assertion packet; `inspect`, `read`, `workflow`,
`events` and `feed` are the reads; `subscribe` names the API's own hint socket, to which the service
sends the VELDO-0046 hint after each commit. The protected signer signs such a request, and nothing
else, in REQUEST_NAMESPACE with the api edge key; the service verifies an API call against that key
alone, so no other key can speak as the API and the API's request signature stands in for no command.

WHAT IT IS NOT. Not a session, a transport or a store. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('api_assertion_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IN = _organ('control_intake')
ST = _organ('control_request_settlement')
SCHEMA = 'veldo.api_assertion/v1'
CHANNEL = 'api'
LIFETIME = 60
SKEW = 5
IDS = ('domain_uuid', 'repository_uuid', 'store_uuid')
FIELDS = ('schema', 'domain') + IDS + ('channel', 'edge', 'edge_key_id', 'request_id', 'principal', 'credential_id',
                                       'session', 'operation', 'target', 'parameters', 'expected_versions',
                                       'issued_at', 'expires_at')
# Every operation: its exact parameters and the authority boundary its member is judged at.
OPERATIONS = {
    'send_message': {'parameters': ('text', 'project', 'clarifies'), 'boundary': 'proposal_commit'},
    'answer_decision': {'parameters': ('request_id', 'request_version', 'presentation_id', 'presentation_digest',
                                       'presentation_version', 'choice', 'rationale'),
                        'boundary': 'decision_settlement'},
    'revoke_credential': {'parameters': ('credential_id',), 'boundary': 'command_acceptance'},
    'save_workflow': {'parameters': ('workflow', 'base', 'definition', 'layout'), 'boundary': 'command_acceptance'},
}

CALL = 'api_call'
REQUEST_NAMESPACE = 'veldo-api-request'
CALLS = {'apply': ('packet',), 'inspect': ('entity_ids',), 'read': ('model', 'principal'),
         'workflow': ('principal', 'workflow', 'version'), 'events': ('principal', 'after', 'limit'),
         'feed': ('after', 'limit'), 'subscribe': ('socket',)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def digest(value):
    return 'sha256:' + hashlib.sha256(canonical(value)).hexdigest()


def _text(value, limit=256):
    return isinstance(value, str) and 0 < len(value) <= limit and value.isprintable()


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def shape_problems(a):
    """Why a value is not one API assertion, by name; [] when it is."""
    if not isinstance(a, dict) or set(a) != set(FIELDS):
        return ['an API assertion has exactly its fields']
    problems = []
    if a['schema'] != SCHEMA or a['channel'] != CHANNEL:
        problems.append('the assertion is a %s on channel %s' % (SCHEMA, CHANNEL))
    if not all(_text(a[f]) for f in ('domain', 'edge', 'edge_key_id', 'request_id', 'principal', 'session', 'target') + IDS):
        problems.append('identities are named')
    if not _text(a['credential_id'], 2048):
        problems.append('the credential id is named')
    spec = OPERATIONS.get(a['operation'])
    if spec is None:
        problems.append('the operation is one of %s' % ', '.join(sorted(OPERATIONS)))
    elif not isinstance(a['parameters'], dict) or set(a['parameters']) != set(spec['parameters']):
        problems.append('the parameters are exactly %s' % ', '.join(spec['parameters']))
    if not isinstance(a['expected_versions'], dict):
        problems.append('the expected versions are a mapping')
    if not (_number(a['issued_at']) and _number(a['expires_at']) and a['expires_at'] == a['issued_at'] + LIFETIME):
        problems.append('the assertion expires %d seconds after it is issued' % LIFETIME)
    return problems


def time_problem(a, now):
    """Why an assertion is not live at `now`, or None."""
    if a['issued_at'] > now + SKEW:
        return 'issued in the future'
    if a['expires_at'] <= now:
        return 'expired'
    return None


def domain_request(a):
    """The one signed domain request an assertion's operation carries, or None for revoke_credential and
    save_workflow, which execute from the verified assertion itself."""
    p = a['parameters']
    if a['operation'] == 'send_message':
        return {'schema': IN.API_SCHEMA, 'domain': a['domain'], 'request_id': a['request_id'], 'edge': a['edge'],
                'principal': a['principal'], 'text': p['text'], 'project': p['project'], 'clarifies': p['clarifies']}
    if a['operation'] == 'answer_decision':
        return dict({f: a[f] for f in IDS}, schema=ST.API_SCHEMA, edge=a['edge'], answer_id=a['request_id'],
                    principal=a['principal'], request_id=p['request_id'], request_version=p['request_version'],
                    presentation_id=p['presentation_id'], presentation_digest=p['presentation_digest'],
                    presentation_version=p['presentation_version'], choice=p['choice'], rationale=p['rationale'])
    return None


def call_command(call, arguments):
    """The command of one API request to the authority service."""
    return {'operation': CALL, 'call': call, 'arguments': dict(arguments)}


def is_call(command):
    """Whether a request's command claims to be an API call (then only the api edge may have signed it)."""
    return isinstance(command, dict) and command.get('operation') == CALL


def call_problems(command):
    """Why a request's command is not one API call, by name; [] when it is."""
    if not isinstance(command, dict) or set(command) != {'operation', 'call', 'arguments'} or command['operation'] != CALL:
        return ['an API call is exactly operation, call and arguments']
    fields = CALLS.get(command['call'])
    if fields is None:
        return ['the call is one of %s' % ', '.join(sorted(CALLS))]
    if not isinstance(command['arguments'], dict) or set(command['arguments']) != set(fields):
        return ['the arguments of %s are exactly %s' % (command['call'], ', '.join(fields))]
    return []
