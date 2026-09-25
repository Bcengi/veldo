"""Objective acceptance, bounded elaboration, evidence assessment and cancellation (PLAN-0019 W62,
VELDO-0077, R06).

WHAT THIS MODULE IS. The one writer of a repository's objective records in the control store, and of
the features proposed under them. An objective is entity `objective:<hex>` of kind `objective`, named
by the VELDO-0126 intake proposal it was elaborated from, and it belongs to exactly one project
(`project_uuid` is `project:<name>`, the chain the eligibility Gate, the inbox and the project service
already read). A feature proposed under it is a `backlog_item` at `objective-feature:<hex>` whose
`objective_uuid` names the objective. The service declares the `objective` kind and both id prefixes as
its own (control_store's declare_owners), so no other command writes an objective or a record at one of
these ids.

Every change is a real signed command {'command': body, 'signature'}: the body carries the operation,
the principal, a command id, a nonce and the store's coordinates, and it is verified with the
principal's active key. The lifecycle is entity_contract's R06 vocabulary: every transition is asked of
entity_contract.transition with the evidence this service established, so an undeclared edge, a terminal
source or a missing predicate is refused by name.

  propose          From an intake proposal of kind objective (state PROPOSED, one project) whose
                   project is ACTIVE, a member in the project's scope elaborates the BOUND fields: the
                   observable outcome, the scope, the authority (the acceptor, who is the project's
                   owner, and the assessor, an active person in the project's scope) and the evidence
                   requirements (each an id and the kind of kept record that proves it). The record is
                   PROPOSED at revision 1 with the digest of exactly those fields. `continues` may name a
                   terminal objective of the same project: that is the only way work continues after a
                   terminal objective, and the terminal record is never changed.
  amend            The proposer changes bound fields of a PROPOSED objective: a new revision and a new
                   bound digest. An answer given to an earlier revision no longer accepts it.
  accept           The owner's answer, settled by the VELDO-0068 settlement on the
                   decision_disposition touchpoint, is applied. The request's terms target this
                   objective at its CURRENT revision and bound digest (acceptance_target), the request
                   showed its owner exactly acceptance_brief of that revision, the request's owner and the
                   settlement's only principal are the bound acceptor, who is the project's owner and
                   current. Approve moves PROPOSED -> ACCEPTED and records accepted_revision; reject moves
                   it to REJECTED. Anything else refuses and writes nothing.
  propose_feature  Bounded elaboration: under an ACCEPTED or ACTIVE objective a member proposes a
                   feature whose scope lies inside the objective's accepted scope. The feature is RAW: it
                   carries no admission and no priority, and nothing here writes either; admission and
                   priority are their own settled decisions. The first feature links the contribution
                   (ACCEPTED -> ACTIVE).
  assess           Satisfaction is only the bound assessor's signed assessment of the ACCEPTED revision:
                   every evidence requirement names a kept record of its kind by id and entity digest,
                   read inside the transaction, and a gate observation proves only with exit 0. The
                   receipt is completion_contract's objective_satisfied fact (ACTIVE -> SATISFIED).
                   Shipped specifications are reported (specifications) and never decide it.
  cancel           The project's current owner cancels with a reason and an explicit disposition of
                   every unfinished feature (release_floor_contract.objective_cancellation_problems):
                   `stop` cancels the feature, `transfer` moves it to another accepted objective of the
                   project. Every disposition is recorded by the canceling owner. The objective's
                   acceptance, features and history stay; CANCELED is terminal.
  reopen           Asked of the lifecycle as an edge back to PROPOSED, which R06 does not declare: a
                   terminal objective is never reopened, and continuation is a new objective that
                   `continues` it.

Each transition appends one entry to the record's `history` and never changes an earlier one.

STATED LIMITS. One project per objective and one acceptor, the project's owner (objectives spanning
projects and additional owners are Release 3). Units of a stopped feature are not reached here: a
feature this service writes is never admitted by it, so no unit exists under it unless a later admission
put one there. Recovery and restart are Release 2. Observations carry identities, versions, outcomes and
named refusals, never outcome text, reasons, rationales or signatures. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('objective_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EC = _organ('entity_contract')
CC = _organ('completion_contract')
RF = _organ('release_floor_contract')
Y = _organ('yamlish')

SCHEMA = 'veldo.objective/v1'
FEATURE_SCHEMA = 'veldo.objective_feature/v1'
KIND, FEATURE_KIND = 'objective', 'backlog_item'
ID_PREFIX, FEATURE_PREFIX = 'objective:', 'objective-feature:'
OPERATION = 'objective_operation'
OWNER = 'VELDO-0077 objectives'
WRITES = ('entities', 'journal', 'commands', 'nonces')
OPERATIONS = ('propose', 'amend', 'accept', 'propose_feature', 'assess', 'cancel', 'reopen')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
OWNER_ROLE = 'project_owner'
# What acceptance binds, in the order a missing one is named.
BOUND_FIELDS = ('outcome', 'scope', 'authority', 'evidence_requirements')
AUTHORITY_FIELDS = ('acceptor', 'assessor')
# The settlement the owner's acceptance comes through (VELDO-0068) and the target kind it names.
ACCEPTANCE_TOUCHPOINT, TARGET_KIND = 'decision_disposition', 'objective'
RULINGS = {'approve': 'ACCEPTED', 'reject': 'REJECTED'}
# The kept records an evidence requirement may name, and what makes one prove it.
EVIDENCE_KINDS = ('gate_observation',)
SUPPORTED_DISPOSITIONS = ('stop', 'transfer')
PROPOSAL_KIND, PROJECT_KIND = 'intake_proposal', 'project'
REQUEST_KIND, SETTLEMENT_KIND, EFFECT_KIND = 'assignment', 'request_settlement', 'settlement_effect'
TAXONOMY = {'invalid_input': 'invalid_input', 'missing_field': 'invalid_input', 'out_of_scope': 'invalid_input',
            'no_such_objective': 'invalid_input', 'no_such_proposal': 'invalid_input',
            'unsupported_disposition': 'invalid_input', 'not_authorized': 'missing_authority',
            'not_owner': 'missing_authority', 'project_not_active': 'missing_authority',
            'not_accepted': 'missing_authority', 'already_exists': 'stale_subject', 'stale_subject': 'stale_subject',
            'stale_version': 'stale_subject', 'invalid_transition': 'stale_subject',
            'missing_evidence': 'missing_evidence', 'unproven_outcome': 'missing_evidence',
            'missing_disposition': 'missing_evidence', 'unavailable_service': 'unavailable_service'}
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _hex(*parts):
    return hashlib.sha256(_canonical(list(parts))).hexdigest()[:32]


def objective_id(proposal):
    return ID_PREFIX + _hex('objective', proposal)


def feature_id(objective, name):
    return FEATURE_PREFIX + _hex('feature', objective, name)


def bound_digest(objective, revision, bound):
    return 'sha256:' + hashlib.sha256(_canonical(dict({k: bound.get(k) for k in BOUND_FIELDS},
                                                      objective=objective, revision=revision))).hexdigest()


def acceptance_target(record):
    """The settlement terms target that asks the owner to accept `record` at its current revision."""
    return {'kind': TARGET_KIND, 'ref': record['uuid'], 'revision': record['revision'], 'digest': record['bound_digest']}


def acceptance_brief(record):
    """Exactly what the owner is shown: the bound fields of the revision the answer accepts."""
    bound = record['bound']
    evidence = '; '.join('%s (%s)' % (e['id'], e['kind']) for e in bound['evidence_requirements'])
    return ('Accept objective %s, revision %d, in project %s.\nOutcome: %s\nScope: %s\n'
            'Accepted by: %s. Assessed by: %s.\nEvidence required: %s\n'
            'Features proposed under it still need their own admission and priority.'
            % (record['uuid'], record['revision'], record['project'], bound['outcome'], '; '.join(bound['scope']),
               bound['authority']['acceptor'], bound['authority']['assessor'], evidence))


def bound_problems(bound):
    """Why the bound fields are not an objective this service accepts, by name."""
    missing = [f for f in BOUND_FIELDS if f not in bound]
    if missing:
        return ['missing_field:' + f for f in missing]
    problems = []
    if not _is_str(bound['outcome']):
        problems.append('invalid_input:outcome')
    scope = bound['scope']
    if not isinstance(scope, list) or not scope or not all(_is_str(s) for s in scope) or len(set(scope)) != len(scope):
        problems.append('invalid_input:scope')
    authority = bound['authority']
    if not isinstance(authority, dict) or set(authority) != set(AUTHORITY_FIELDS) or not all(
            _is_str(authority[k]) for k in AUTHORITY_FIELDS):
        problems.append('invalid_input:authority')
    evidence = bound['evidence_requirements']
    if (not isinstance(evidence, list) or not evidence
            or not all(isinstance(e, dict) and set(e) == {'id', 'kind'} and _is_str(e['id']) and e['kind'] in EVIDENCE_KINDS
                       for e in evidence) or len({e['id'] for e in evidence}) != len(evidence)):
        problems.append('invalid_input:evidence_requirements')
    return problems


def _row(conn, eid):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone() \
        if isinstance(eid, str) else None
    return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}


def read(conn, oid):
    """The accepted objective record `oid` on any connection (another process's read-only one included)."""
    row = _row(conn, oid)
    return None if row is None or row['kind'] != KIND else dict(row['data'], version=row['version'])


def features(conn, oid):
    """Every feature under `oid`, by id order: the backlog items whose objective_uuid names it."""
    found = []
    for eid, version, text in conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id',
                                           (FEATURE_KIND,)):
        data = json.loads(text)
        if isinstance(data, dict) and data.get('objective_uuid') == oid:
            found.append(dict(data, uuid=eid, version=version))
    return found


def specification_status(workspace, spec):
    """The status a specification file under `workspace`/specs carries, or None. Reported, never decisive."""
    if workspace is None or not _is_str(spec) or not _NAME.match(spec):
        return None
    for path in sorted((Path(workspace) / 'specs').glob(spec + '-*.md')) + [Path(workspace) / 'specs' / (spec + '.md')]:
        if path.is_file():
            match = Y.front_matter_match(path.read_text())
            front = Y.parse(match.group(1)) if match else None
            if isinstance(front, dict) and front.get('id') == spec:
                return front.get('status')
    return None


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


class Objectives:
    """One repository's objective service on the configured real store connection.

    `store` and `membership` are the control_store and control_membership modules; `sign(bytes)` signs
    journal records as `journal_signer`. `workspace` is the checkout whose specification files the
    service reports on (never decides on)."""

    def __init__(self, store, membership, conn, coordinates, journal_signer, sign, *, workspace=None,
                 authority_generation=1, clock=time.time):
        if set(coordinates) != set(COORDINATES) or not all(_is_str(v) for v in coordinates.values()):
            raise Refused('invalid_input', 'coordinates are domain, repository and store identities')
        self.store, self.membership, self.AC = store, membership, membership.AC
        self.conn, self.ids = conn, dict(coordinates)
        self.journal_signer, self.sign, self.workspace = journal_signer, sign, workspace
        self.authority_generation, self.clock = authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction, 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={KIND: (OPERATION,)},
                             prefixes={ID_PREFIX: (OPERATION,), FEATURE_PREFIX: (OPERATION,)}, module=__file__)

    # Commands.

    def apply(self, packet):
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        observation = dict(self.ids, schema=SCHEMA, operation=command.get('operation'), objective=None,
                           command_id=command.get('command_id'), accepted_versions={})
        try:
            result = self._apply(packet, command, observation)
        except Refused as exc:
            result = {'ok': False, 'reason': exc.code}
        except self.store.StoreRefused as exc:
            result = {'ok': False, 'reason': exc.code}
        except sqlite3.Error:
            result = {'ok': False, 'reason': 'unavailable_service'}
        observation.update(outcome='accepted' if result['ok'] else 'refused',
                           refusal=None if result['ok'] else result['reason'],
                           taxonomy=None if result['ok'] else taxonomy(result['reason']))
        self.counts[observation['outcome']] += 1
        self.observations.append(observation)
        return result

    def _apply(self, packet, command, observation):
        if (not isinstance(packet, dict) or not isinstance(packet.get('command'), dict)
                or not isinstance(packet.get('signature'), str) or not packet['signature'].isascii()):
            raise Refused('invalid_input', 'command must be a mapping and signature ASCII text')
        required = {'operation', 'principal', 'command_id', 'nonce', *COORDINATES}
        if (not required <= command.keys() or command['operation'] not in OPERATIONS
                or not all(_is_str(command[k]) for k in ('principal', 'command_id', 'nonce'))
                or any(command[k] != v for k, v in self.ids.items())):
            raise Refused('invalid_input', 'invalid objective command or authority coordinates')
        op, principal = command['operation'], command['principal']
        state = self.membership.authority_state(self.store, self.conn)
        now = self.clock()
        key = self.AC.active_key(state['keyring'], principal, now)
        if not key:
            raise Refused('not_authorized', 'no active verification key')
        verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), packet['signature'],
                                                self.AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise Refused('not_authorized', 'command signature did not verify')
        if op == 'propose':
            proposal = _row(self.conn, command.get('proposal')) if _is_str(command.get('proposal')) else None
            if proposal is None or proposal['kind'] != PROPOSAL_KIND:
                raise Refused('no_such_proposal', str(command.get('proposal'))[:128])
            oid, project = objective_id(command['proposal']), proposal['data'].get('project')
            pinned = [command['proposal']] + ([command['continues']] if _is_str(command.get('continues')) else [])
        else:
            oid = command.get('objective')
            current = read(self.conn, oid) if _is_str(oid) and oid.startswith(ID_PREFIX) else None
            if current is None:
                raise Refused('no_such_objective', str(oid)[:128])
            if command.get('objective_version') != current['version']:
                raise Refused('stale_version', 'command names another objective version')
            project = current['project']
            pinned = []
        observation['objective'] = oid
        if not _is_str(project) or not _NAME.match(project):
            raise Refused('invalid_input:project', 'the objective names no project')
        record = _row(self.conn, 'project:' + project)
        owner = (record or {}).get('data', {}).get('owner') if (record or {}).get('kind') == PROJECT_KIND else None
        if op == 'propose' and (owner is None or record['data'].get('state') != 'ACTIVE'):
            raise Refused('project_not_active:%s' % ((record or {}).get('data') or {}).get('state', 'missing'), project)
        problems = self._member_problems(state, principal, project, now)
        if op == 'cancel':
            problems = problems or self._owner_problems(state, principal, project, now)
            if principal != owner:
                problems.append('not_owner:project')
        elif op == 'assess':
            problems = problems or self._person_problems(state, principal, project, now)
        elif op == 'accept':
            problems = problems or ['not_owner:' + p for p in self._owner_problems(state, owner, project, now)]
        elif op == 'propose':
            assessor = (command.get('authority') or {}).get('assessor') if isinstance(command.get('authority'), dict) else None
            problems = problems or ['invalid_input:assessor:' + p for p in self._person_problems(state, assessor, project, now)]
        if problems:
            raise Refused(problems[0], '; '.join(problems))
        written = [oid]
        if op == 'propose_feature' and _is_str(command.get('feature')):
            written.append(feature_id(oid, command['feature']))
        if op == 'cancel':
            written += [f['uuid'] for f in features(self.conn, oid)]
            written += sorted({d.get('to') for d in command.get('dispositions') or []
                               if isinstance(d, dict) and _is_str(d.get('to')) and d.get('to') != oid})
        if op == 'accept' and _is_str(command.get('request')):
            request = _row(self.conn, command['request']) or {}
            reference = (request.get('data') or {}).get('settlement') or {}
            pinned += [command['request']] + [reference[k] for k in ('settlement_id', 'effect_id')
                                              if isinstance(reference, dict) and _is_str(reference.get(k))]
        if op == 'assess' and isinstance(command.get('evidence'), dict):
            pinned += sorted({e['ref'] for e in command['evidence'].values() if isinstance(e, dict) and _is_str(e.get('ref'))})
        pinned.append('project:' + project)
        versions = {eid: (_row(self.conn, eid) or {}).get('version', 0) for eid in written + pinned + [principal]}
        observation['accepted_versions'] = versions
        params = dict(command=command, signature=packet['signature'] if op == 'assess' else None, objective=oid,
                      project=project, at=now)
        stored = dict(command_id=command['command_id'], principal=principal, operation=OPERATION, parameters=params,
                      expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        receipt = self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        return {'ok': True, 'reason': op, 'objective_id': oid, 'objective': read(self.conn, oid), 'receipt': receipt,
                'feature_id': written[1] if op == 'propose_feature' else None}

    def _member_problems(self, state, principal, project, now):
        entry = self.AC.membership_entry(state['membership'], principal)
        active, why = self.AC.active_member(entry, now)
        if not active:
            return ['not_authorized:' + str(why)]
        if not self.membership.scope_covers(entry.get('scope'), [project]):
            return ['not_authorized:scope']
        return []

    def _person_problems(self, state, principal, project, now):
        problems = self._member_problems(state, principal, project, now)
        entry = self.AC.membership_entry(state['membership'], principal) or {}
        return problems or ([] if entry.get('principal_type') == 'person' else ['not_authorized:not_a_person'])

    def _owner_problems(self, state, principal, project, now):
        problems = self._person_problems(state, principal, project, now)
        entry = self.AC.membership_entry(state['membership'], principal) or {}
        return problems or ([] if OWNER_ROLE in (entry.get('roles') or []) else ['not_authorized:role'])

    # The transaction.

    def _in_transaction(self, conn, params, before):
        """Inside the store's write transaction: every record the operation decides on is read here, so
        what it decided on is what it commits over."""
        command, oid, now = params['command'], params['objective'], params['at']
        op, principal = command['operation'], command['principal']
        entry = {'by': principal, 'at': now, 'command_id': command['command_id'], 'operation': op}
        project = _row(conn, 'project:' + params['project'])
        if project is None or project['kind'] != PROJECT_KIND:
            raise Refused('project_not_active:missing', params['project'])
        if op == 'propose':
            return self._propose(conn, command, oid, project, entry)
        current = _row(conn, oid)
        if current is None or current['kind'] != KIND:
            raise Refused('no_such_objective', oid)
        data = json.loads(json.dumps(current['data']))
        source = data['state']
        if op == 'reopen':
            self._edge(KIND, source, 'PROPOSED', {})
            data['state'] = 'PROPOSED'
            data['history'] = list(data['history']) + [dict(entry, source=source, target='PROPOSED')]
            return {oid: {'kind': KIND, 'data': data}}
        changes = getattr(self, '_' + op)(conn, command, params, data, project, entry)
        return changes

    def _propose(self, conn, command, oid, project, entry):
        proposal = _row(conn, command['proposal'])
        found = proposal['data'] if proposal is not None and proposal['kind'] == PROPOSAL_KIND else {}
        if found.get('proposal') != 'objective' or found.get('state') != 'PROPOSED' or found.get('domain') != self.ids['domain_uuid']:
            raise Refused('no_such_proposal', 'not a proposed objective of this domain')
        if project['data'].get('state') != 'ACTIVE':
            raise Refused('project_not_active:%s' % project['data'].get('state'), found.get('project'))
        if _row(conn, oid) is not None:
            raise Refused('already_exists', oid)
        bound = {f: command[f] for f in BOUND_FIELDS if f in command}
        problems = bound_problems(bound)
        if problems:
            raise Refused(problems[0], '; '.join(problems))
        if bound['authority']['acceptor'] != project['data'].get('owner'):
            raise Refused('not_owner:acceptor', 'the acceptor is the project\'s owner')
        continues = command.get('continues')
        if continues is not None:
            prior = _row(conn, continues) if _is_str(continues) else None
            if (prior is None or prior['kind'] != KIND or prior['data'].get('project') != found['project']
                    or prior['data'].get('state') not in EC.LIFECYCLES[KIND]['terminal']):
                raise Refused('invalid_input:continues', 'a continuation names a terminal objective of the project')
        data = dict(schema=SCHEMA, uuid=oid, entity_type=KIND, domain_uuid=self.ids['domain_uuid'],
                    repository_uuid=self.ids['repository_uuid'], project=found['project'],
                    project_uuid='project:' + found['project'], proposal_id=command['proposal'],
                    proposal_text_digest='sha256:' + hashlib.sha256(_canonical(found.get('text'))).hexdigest(),
                    state='PROPOSED', revision=1, bound=bound, bound_digest=bound_digest(oid, 1, bound),
                    accepted_revision=None, acceptance=None, features=[], assessment=None, cancellation=None,
                    continues=continues, provenance={'source': 'propose', 'created_by': entry['by'], 'created_at': entry['at']},
                    history=[dict(entry, source=None, target='PROPOSED', revision=1)])
        return {oid: {'kind': KIND, 'data': data}}

    def _amend(self, conn, command, params, data, project, entry):
        if data['state'] != 'PROPOSED':
            raise Refused('invalid_transition:%s->PROPOSED' % data['state'], 'only a proposed objective is amended')
        if entry['by'] != data['provenance']['created_by']:
            raise Refused('not_authorized:proposer', 'the proposer amends the objective')
        changes = command.get('changes')
        if not isinstance(changes, dict) or not changes or set(changes) - set(BOUND_FIELDS):
            raise Refused('invalid_input:changes', 'an amendment changes bound fields')
        bound = dict(data['bound'], **changes)
        problems = bound_problems(bound)
        if problems:
            raise Refused(problems[0], '; '.join(problems))
        if bound['authority']['acceptor'] != project['data'].get('owner'):
            raise Refused('not_owner:acceptor', 'the acceptor is the project\'s owner')
        data.update(bound=bound, revision=data['revision'] + 1)
        data['bound_digest'] = bound_digest(data['uuid'], data['revision'], bound)
        data['history'] = list(data['history']) + [dict(entry, source='PROPOSED', target='PROPOSED',
                                                        revision=data['revision'], changed=sorted(changes))]
        return {data['uuid']: {'kind': KIND, 'data': data}}

    def _accept(self, conn, command, params, data, project, entry):
        oid = data['uuid']
        if data['state'] != 'PROPOSED':
            raise Refused('invalid_transition:%s->ACCEPTED' % data['state'], 'only a proposed objective is accepted')
        request = _row(conn, command.get('request'))
        req = request['data'] if request is not None and request['kind'] == REQUEST_KIND else {}
        reference = req.get('settlement') if isinstance(req.get('settlement'), dict) else {}
        settlement, effect = _row(conn, reference.get('settlement_id')), _row(conn, reference.get('effect_id'))
        if (req.get('state') != 'SATISFIED' or settlement is None or settlement['kind'] != SETTLEMENT_KIND
                or effect is None or effect['kind'] != EFFECT_KIND
                or effect['data'].get('settlement_id') != settlement['data'].get('settlement_id')
                or settlement['data'].get('request_id') != command.get('request')):
            raise Refused('missing_evidence:settlement', 'the request is not settled')
        target = effect['data'].get('target') or {}
        if (settlement['data'].get('touchpoint') != ACCEPTANCE_TOUCHPOINT or target.get('kind') != TARGET_KIND
                or target.get('ref') != oid):
            raise Refused('invalid_input:request', 'the settled request does not ask to accept this objective')
        if target != acceptance_target(data):
            raise Refused('stale_subject:revision', 'the answer accepted another revision of the objective')
        if req.get('brief') != acceptance_brief(data):
            raise Refused('stale_subject:brief', 'the owner was shown something other than this revision')
        acceptor = data['bound']['authority']['acceptor']
        if (acceptor != project['data'].get('owner') or req.get('owner') != acceptor
                or settlement['data'].get('principals') != [acceptor]):
            raise Refused('not_owner', 'only the project\'s owner accepts its objective')
        ruling = settlement['data'].get('ruling')
        if ruling not in RULINGS:
            raise Refused('not_accepted:%s' % ruling, 'the owner did not accept or reject the objective')
        target_state = RULINGS[ruling]
        self._edge(KIND, 'PROPOSED', target_state, {'acceptance_authority_signed': True})
        data['state'] = target_state
        data['accepted_revision'] = data['revision'] if target_state == 'ACCEPTED' else None
        data['acceptance'] = {'request_id': command['request'], 'request_version': reference.get('request_version'),
                              'settlement_id': reference['settlement_id'], 'effect_id': reference['effect_id'],
                              'receipt_id': reference.get('receipt_id'), 'ruling': ruling, 'principals': [acceptor],
                              'revision': data['revision'], 'bound_digest': data['bound_digest']}
        data['history'] = list(data['history']) + [dict(entry, source='PROPOSED', target=target_state,
                                                        revision=data['revision'], request_id=command['request'])]
        return {oid: {'kind': KIND, 'data': data}}

    def _propose_feature(self, conn, command, params, data, project, entry):
        oid, name = data['uuid'], command.get('feature')
        if data['state'] not in ('ACCEPTED', 'ACTIVE'):
            raise Refused('invalid_transition:%s->ACTIVE' % data['state'], 'features are proposed under an accepted objective')
        if not _is_str(name) or not _NAME.match(name) or not _is_str(command.get('title')):
            raise Refused('invalid_input:feature', 'a feature has a name and a title')
        fid = feature_id(oid, name)
        if _row(conn, fid) is not None:
            raise Refused('already_exists', fid)
        scope, specs = command.get('scope'), command.get('specifications', [])
        if not isinstance(scope, list) or not scope or not all(_is_str(s) for s in scope):
            raise Refused('invalid_input:scope', 'a feature names its scope')
        outside = [s for s in scope if s not in data['bound']['scope']]
        if outside:
            raise Refused('out_of_scope:' + outside[0], 'bounded elaboration stays inside the accepted scope')
        if not isinstance(specs, list) or not all(_is_str(s) and _NAME.match(s) for s in specs):
            raise Refused('invalid_input:specifications', 'specifications are listed by id')
        feature = dict(schema=FEATURE_SCHEMA, uuid=fid, entity_type=FEATURE_KIND, name=name, title=command['title'],
                       domain_uuid=self.ids['domain_uuid'], repository_uuid=self.ids['repository_uuid'],
                       objective_uuid=oid, objective_revision=data['accepted_revision'], project=data['project'],
                       state='RAW', scope=list(scope), specifications=list(specs), admission=None, priority=None,
                       provenance={'source': 'propose_feature', 'created_by': entry['by'], 'created_at': entry['at']},
                       history=[dict(entry, source=None, target='RAW')])
        source = data['state']
        if source == 'ACCEPTED':
            self._edge(KIND, 'ACCEPTED', 'ACTIVE', {'contribution_linked': True})
            data['state'] = 'ACTIVE'
        data['features'] = list(data['features']) + [fid]
        data['history'] = list(data['history']) + [dict(entry, source=source, target=data['state'], feature=fid)]
        return {oid: {'kind': KIND, 'data': data}, fid: {'kind': FEATURE_KIND, 'data': feature}}

    def _assess(self, conn, command, params, data, project, entry):
        oid = data['uuid']
        if data['state'] != 'ACTIVE':
            raise Refused('invalid_transition:%s->SATISFIED' % data['state'], 'only an active objective is satisfied')
        if entry['by'] != data['bound']['authority']['assessor']:
            raise Refused('not_authorized:assessor', 'only the bound assessor assesses the objective')
        if command.get('revision') != data['accepted_revision']:
            raise Refused('stale_subject:revision', 'the assessment is of another revision than the accepted one')
        evidence = command.get('evidence') if isinstance(command.get('evidence'), dict) else {}
        kept = {}
        for requirement in data['bound']['evidence_requirements']:
            named = evidence.get(requirement['id']) if isinstance(evidence.get(requirement['id']), dict) else {}
            row = _row(conn, named.get('ref')) if _is_str(named.get('ref')) else None
            if row is None or row['kind'] != requirement['kind'] or row['digest'] != named.get('digest'):
                raise Refused('missing_evidence:' + requirement['id'], 'no kept record of the required kind and digest')
            if row['data'].get('exit') != 0:
                raise Refused('unproven_outcome:' + requirement['id'], 'the kept observation did not pass')
            kept[requirement['id']] = {'ref': named['ref'], 'digest': row['digest'], 'kind': row['kind']}
        receipt = {'fact': 'objective_satisfied', 'subject': {'id': oid, 'revision': data['accepted_revision']},
                   'signed_assessment': {'command': command, 'signature': params['signature']},
                   'accepted_objective_revision': data['accepted_revision'], 'assessor': entry['by'],
                   'evidence': kept, 'assessed_at': entry['at']}
        problems = CC.fact_problems('objective_satisfied', receipt, {'id': oid, 'revision': data['accepted_revision']})
        if problems:
            raise Refused('missing_evidence:assessment', '; '.join(problems))
        self._edge(KIND, 'ACTIVE', 'SATISFIED', {'signed_assessment_against_accepted_revision': True})
        data.update(state='SATISFIED', assessment=receipt)
        data['history'] = list(data['history']) + [dict(entry, source='ACTIVE', target='SATISFIED',
                                                        revision=data['accepted_revision'])]
        return {oid: {'kind': KIND, 'data': data}}

    def _cancel(self, conn, command, params, data, project, entry):
        oid, source = data['uuid'], data['state']
        if entry['by'] != project['data'].get('owner'):
            raise Refused('not_owner:project', 'the project\'s owner cancels its objective')
        if not _is_str(command.get('reason')):
            raise Refused('missing_field:reason', 'a cancellation says why')
        dispositions = command.get('dispositions')
        if not isinstance(dispositions, list) or not all(isinstance(d, dict) for d in dispositions):
            raise Refused('invalid_input:dispositions', 'dispositions are a list of records')
        items = features(conn, oid)
        open_ = {i['uuid']: i for i in items if i.get('state') not in EC.LIFECYCLES[FEATURE_KIND]['terminal']}
        problems = RF.objective_cancellation_problems({'uuid': oid}, items, dispositions)
        if problems:
            raise Refused('missing_disposition', '; '.join(problems))
        changes = {}
        for d in dispositions:
            if d.get('target') not in open_:
                raise Refused('invalid_input:disposition', 'a disposition names an unfinished feature of the objective')
            if d.get('recorded_by') != entry['by']:
                raise Refused('not_authorized:disposition', 'the canceling owner records every disposition')
            if d.get('disposition') not in SUPPORTED_DISPOSITIONS:
                raise Refused('unsupported_disposition:%s' % d.get('disposition'), 'stop or transfer in this release')
            item = dict(open_[d['target']])
            item.pop('version', None)
            record = dict(entry, disposition=d['disposition'], reason=command['reason'], source=item['state'])
            if d['disposition'] == 'stop':
                self._edge(FEATURE_KIND, item['state'], 'CANCELED', {'disposition_recorded': True})
                item['state'] = 'CANCELED'
            else:
                to = _row(conn, d.get('to'))
                if (to is None or to['kind'] != KIND or d.get('to') == oid or to['data'].get('project') != data['project']
                        or to['data'].get('state') not in ('ACCEPTED', 'ACTIVE')):
                    raise Refused('invalid_input:transfer', 'a transfer names another accepted objective of the project')
                receiving = changes.get(d['to'], {}).get('data') or json.loads(json.dumps(to['data']))
                if receiving['state'] == 'ACCEPTED':
                    self._edge(KIND, 'ACCEPTED', 'ACTIVE', {'contribution_linked': True})
                    receiving['state'] = 'ACTIVE'
                receiving['features'] = list(receiving['features']) + [item['uuid']]
                receiving['history'] = list(receiving['history']) + [dict(entry, source=to['data']['state'],
                                                                          target=receiving['state'], feature=item['uuid'],
                                                                          transferred_from=oid)]
                changes[d['to']] = {'kind': KIND, 'data': receiving}
                item['objective_uuid'], record['to'] = d['to'], d['to']
            record['target'] = item['state']
            item['history'] = list(item.get('history') or []) + [record]
            changes[item['uuid']] = {'kind': FEATURE_KIND, 'data': item}
        self._edge(KIND, source, 'CANCELED', {'disposition_recorded': True})
        data['state'] = 'CANCELED'
        data['cancellation'] = {'reason': command['reason'], 'by': entry['by'], 'at': entry['at'],
                                'dispositions': [dict(d) for d in dispositions]}
        data['history'] = list(data['history']) + [dict(entry, source=source, target='CANCELED')]
        changes[oid] = {'kind': KIND, 'data': data}
        return changes

    @staticmethod
    def _edge(kind, source, target, evidence):
        allowed, why = EC.transition(kind, source, target, evidence)
        if not allowed:
            raise Refused('invalid_transition:%s->%s' % (source, target), why)

    # Reads.

    def specifications(self, oid):
        """{spec: status} over the specifications the objective's features name, read from the workspace.
        Shipped specifications are information about the work, never evidence that the outcome holds."""
        out = {}
        for feature in features(self.conn, oid):
            for spec in feature.get('specifications') or []:
                out[spec] = specification_status(self.workspace, spec)
        return out

    def metrics(self):
        """Accepted and refused commands, objectives by state, and the pending work: objectives awaiting
        acceptance or assessment and features awaiting their own admission."""
        states, raw = {}, 0
        for (text,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,)):
            data = json.loads(text)
            states[str(data.get('state'))] = states.get(str(data.get('state')), 0) + 1
        for (eid,) in self.conn.execute('SELECT id FROM entities WHERE kind=? AND substr(id, 1, ?) = ?',
                                        (FEATURE_KIND, len(FEATURE_PREFIX), FEATURE_PREFIX)):
            raw += (_row(self.conn, eid) or {}).get('data', {}).get('state') == 'RAW'
        return dict(self.counts, objectives=states,
                    pending={'awaiting_acceptance': states.get('PROPOSED', 0),
                             'awaiting_assessment': states.get('ACCEPTED', 0) + states.get('ACTIVE', 0),
                             'features_awaiting_admission': raw})
