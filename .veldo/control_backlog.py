"""Backlog lifecycle and priority-controlled execution (PLAN-0019 W63, VELDO-0078, R11, R12, R13).

WHAT THIS MODULE IS. The one writer of a repository's backlog items (entity `backlog:<hex>` of kind
`backlog_item`) and of the engineering units their approved decomposition creates (`execution_unit`
records named by their unit alias, with an `admission:<unit>` record once the owner admits them), and
the one answer every claim entry asks before it hands out work (executable_problems). A backlog item is
taken from a RAW feature of an accepted objective (VELDO-0077, which never admits or prioritizes a
feature and is never written here), and it moves along entity_contract's R11 vocabulary:

  take              A project member takes a RAW feature of an ACCEPTED or ACTIVE objective into the
                    backlog: the item is RAW (proposed), in the feature's one project, with the feature's
                    scope and a work class of the ordinary lane (WORK_CLASSES).
  prepare           The proposer shapes it: the decomposition (each unit's alias, checked by the existing
                    unit-id validator claim.unit_id_problem, its primary specification, scope, requirements
                    and eligible holders) at decomposition revision 1 with its digest. RAW -> PREPARED
                    (intake_validated). Each unit is created PLANNED: nothing can claim it.
  request_grooming  PREPARED -> AWAITING_GROOMING (grooming_requested): the item waits for its owner.
  admit             The owner's answer, settled by the VELDO-0068 settlement on the `admission`
                    touchpoint, is applied. The request's terms target this item at its CURRENT
                    decomposition revision and digest (decision_target), the request showed its owner
                    exactly admission_brief of that revision, and the request's owner and the settlement's
                    only principal are the project's owner. Approve: AWAITING_GROOMING -> ADMITTED
                    (admission_authority_receipt) and an accepted `admission:<unit>` record per unit;
                    reject: REJECTED, its units CANCELED; return_for_elaboration: back to PREPARED.
  prioritize        The owner's settled answer on the `priority` touchpoint for the current revision, with
                    the same binding. Approve: ADMITTED -> PRIORITIZED (priority_receipt), and exactly the
                    units of the approved decomposition move PLANNED -> READY
                    (primary_specification_revision_bound, backlog_item_prioritized) at admitted_revision.
                    On a PRIORITIZED or ACTIVE item it is the fresh prioritization of an appended unit: the
                    item keeps its state and only the units still PLANNED become READY. Reject and return
                    leave the item and its units where they are.
  append            A member appends a proposed unit to a PRIORITIZED or ACTIVE item: a new decomposition
                    revision and digest, the unit PLANNED. It needs its own settled prioritization of that
                    revision; the approved units continue meanwhile.
  block             A member records the interrupted phase and the reason: ACTIVE -> BLOCKED
                    (blocker_recorded), with a `blocker` record per open unit, so every Gate station
                    refuses the item's units (no_blockers) and the claim receiver refuses a BLOCKED item.
  resume            BLOCKED -> ACTIVE (resolution_validated) only when the owner's settled answer on the
                    `decision_disposition` touchpoint names exactly this block (block_target) and
                    approves: the interrupted phase is resumed, recorded, and the blocker records cleared.
  dispose_unit      The authorized alternative outcome of one unit: the owner's settled answer on
                    `decision_disposition` naming the unit at its revision (unit_target) with the
                    proposal {'outcome': 'not_required'}; approve moves the unit to CANCELED
                    (disposition_recorded) carrying that authorization.
  complete          ACTIVE -> DONE (required_units_completed_or_reconciled) only when every unit of the
                    decomposition has an accepted outcome (outcome_problems): the VELDO-0057
                    confirmed-landing receipt of its current revision (completion_contract's
                    revision_landed fact with a complete landing receipt for that unit), or its
                    authorized alternative outcome. A unit's declared output file, a canceled attempt
                    or a unit canceled without the owner's authorization is never an outcome.
  cancel            The project's current owner cancels an unfinished item with a reason; its open units
                    are CANCELED with it.

The first claim of a READY unit is VELDO-0031's (control_claim.transition): it moves the unit to CLAIMED
and the item PRIORITIZED -> ACTIVE in one transaction with the claim record, so the item's activation and
its first owner are one fact. This service never writes a claim.

EVERY CLAIM ENTRY ASKS ONE QUESTION. executable_problems(conn, unit) is [] only for a unit of an
admitted and prioritized item: the item PRIORITIZED or ACTIVE, the unit not PLANNED, and, for an item
this service records, its admission present and the unit inside the prioritized decomposition. The
frontier's offers (frontier.claimable) and the task source's direct claim (tasks.claim_task) ask it over
the Gate's read connection; the claim receiver refuses a PLANNED unit and an item that is neither
PRIORITIZED nor ACTIVE by itself. outcome_problems(conn, unit) is the one answer to whether a unit's
outcome is accepted; the task source concludes a task from it whenever a Gate is wired.

WHAT IS NOT OWNED. Backlog items and units are written here and by the claim transition (first-claim
activation, the claimed unit), so neither their kind nor an id prefix can be declared to one module
(control_store.declare_owners binds each command to one file). Rows forged into the store by another
command are outside this service's threat model, as the specification states.

Every command is a real signed command {'command': body, 'signature'} verified with the principal's
active key; every transition is asked of entity_contract.transition with the evidence established here,
and each appends one entry to the record's history, never changing an earlier one. In a project that is
not ACTIVE every operation but cancel refuses project_not_active:<state>.

STATED LIMITS. Trusted automatic defect admission and standing or emergency policy paths are not
executable here (no operation applies a signed policy admission; the class set is the ordinary lane).
A returned item is re-groomed with its recorded decomposition; reshaping it is Release 3. Recovery and
restart are Release 2. Observations carry identities, versions, outcomes and named refusals, never
reasons, rationales or signatures. Standard library only.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('backlog_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EC = _organ('entity_contract')
CC = _organ('completion_contract')
CL = _organ('claim')

SCHEMA = 'veldo.backlog_item/v1'
UNIT_SCHEMA = 'veldo.backlog_unit/v1'
ADMISSION_SCHEMA = 'veldo.backlog_admission/v1'
KIND, UNIT_KIND, ADMISSION_KIND, BLOCKER_KIND = 'backlog_item', 'execution_unit', 'admission', 'blocker'
ID_PREFIX, FEATURE_PREFIX = 'backlog:', 'objective-feature:'
OPERATION = 'backlog_operation'
WRITES = ('entities', 'journal', 'commands', 'nonces')
OPERATIONS = ('take', 'prepare', 'request_grooming', 'admit', 'prioritize', 'append', 'block', 'resume',
              'dispose_unit', 'complete', 'cancel')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
OWNER_ROLE = 'project_owner'
# The ordinary lane's classes with a person's admission (admission_contract.CLASS_POLICY); an ordinary
# defect (VELDO-0080) is a POLICY_DEFECT admitted by its owner like any other item.
WORK_CLASSES = ('PRODUCT_CHANGE', 'TECHNICAL_CHANGE', 'POLICY_DEFECT')
# The settlement touchpoints whose effects this service applies, and what each approval does.
ADMISSION, PRIORITY, DISPOSITION = 'admission', 'priority', 'decision_disposition'
ADMISSION_RULINGS = {'approve': 'ADMITTED', 'reject': 'REJECTED', 'return_for_elaboration': 'PREPARED'}
TARGET_KIND, BLOCK_TARGET_KIND, UNIT_TARGET_KIND = 'backlog_item', 'backlog_block', 'execution_unit'
ALTERNATIVE_OUTCOMES = ('not_required',)
REQUEST_KIND, SETTLEMENT_KIND, EFFECT_KIND = 'assignment', 'request_settlement', 'settlement_effect'
OBJECTIVE_KIND, PROJECT_KIND, RECEIPT_KIND = 'objective', 'project', 'completion_receipt'
EXECUTABLE_STATES = ('PRIORITIZED', 'ACTIVE')
TERMINAL = EC.LIFECYCLES[KIND]['terminal']
UNIT_TERMINAL = EC.LIFECYCLES[UNIT_KIND]['terminal']
UNIT_FIELDS = ('unit', 'specification', 'scope', 'requirements', 'eligible_holders')
TAXONOMY = {'invalid_input': 'invalid_input', 'missing_field': 'invalid_input', 'out_of_scope': 'invalid_input',
            'no_such_item': 'invalid_input', 'no_such_feature': 'invalid_input', 'unsupported_work_class': 'invalid_input',
            'unsupported_outcome': 'invalid_input', 'not_authorized': 'missing_authority', 'not_owner': 'missing_authority',
            'project_not_active': 'missing_authority', 'not_approved': 'missing_authority',
            'missing_authority': 'missing_authority', 'blocked': 'missing_authority',
            'already_exists': 'stale_subject', 'already_applied': 'stale_subject', 'stale_subject': 'stale_subject',
            'stale_version': 'stale_subject', 'invalid_transition': 'stale_subject',
            'nothing_to_prioritize': 'stale_subject', 'missing_evidence': 'missing_evidence',
            'missing_outcome': 'missing_evidence', 'unavailable_service': 'unavailable_service'}
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _sha(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def item_id(feature):
    return ID_PREFIX + hashlib.sha256(_canonical(['backlog', feature])).hexdigest()[:32]


def admission_id(unit):
    return 'admission:' + unit


def blocker_id(item, block, unit):
    return 'blocker:%s:%s:%s' % (item, block, unit)


def decomposition_digest(item, revision, units):
    return _sha({'item': item, 'revision': revision, 'units': units})


def unit_scope_digest(item, entry):
    return _sha({'item': item, 'unit': entry['unit'], 'specification': entry['specification'], 'scope': entry['scope']})


def decision_target(record):
    """The settlement terms target that asks the owner to admit or prioritize `record` as it stands now."""
    return {'kind': TARGET_KIND, 'ref': record['uuid'], 'revision': record['decomposition_revision'],
            'digest': record['decomposition_digest']}


def _units_text(record):
    return '; '.join('%s (%s)' % (u['unit'], u['specification']) for u in record['decomposition'] or [])


def admission_brief(record):
    """Exactly what the owner is shown when asked to admit the item at its current revision."""
    return ('Admit backlog item %s, decomposition revision %d, in project %s.\nTitle: %s\nClass: %s\n'
            'Scope: %s\nUnits: %s\nAdmitted work still needs its own priority before anything runs.'
            % (record['uuid'], record['decomposition_revision'], record['project'], record['title'],
               record['work_class'], '; '.join(record['scope']), _units_text(record)))


def priority_brief(record):
    """Exactly what the owner is shown when asked to prioritize the item at its current revision."""
    pending = [u['unit'] for u in record['decomposition'] or [] if u['unit'] not in _prioritized(record)]
    return ('Prioritize backlog item %s, decomposition revision %d, in project %s.\nTitle: %s\nUnits: %s\n'
            'Approving makes these units executable: %s.'
            % (record['uuid'], record['decomposition_revision'], record['project'], record['title'],
               _units_text(record), ', '.join(pending) or 'none'))


def block_target(record):
    """The target of the owner decision the item's current block is bound to."""
    block = (record.get('blocks') or [{}])[-1]
    return {'kind': BLOCK_TARGET_KIND, 'ref': record['uuid'], 'block': block.get('block_id'),
            'digest': _sha({'item': record['uuid'], 'block': block.get('block_id'), 'phase': block.get('phase'),
                            'reason': block.get('reason')})}


def unit_target(unit):
    """The target of the owner decision that authorizes an alternative outcome of `unit` (its record)."""
    return {'kind': UNIT_TARGET_KIND, 'ref': unit['uuid'], 'revision': unit['revision'],
            'digest': _sha({'unit': unit['uuid'], 'revision': unit['revision'], 'item': unit['backlog_item_uuid']})}


def _prioritized(record):
    return set((record.get('priority') or {}).get('units') or [])


def _row(conn, eid):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone() \
        if isinstance(eid, str) else None
    return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}


def read(conn, iid):
    """The backlog item record `iid` on any connection (another process's read-only one included)."""
    row = _row(conn, iid)
    return None if row is None or row['kind'] != KIND else dict(row['data'], version=row['version'])


def unit(conn, uid):
    row = _row(conn, uid)
    return None if row is None or row['kind'] != UNIT_KIND else dict(row['data'], version=row['version'])


# The questions every claim entry and every reader of done asks.

def executable_problems(conn, uid):
    """[] only when `uid` is executable engineering work now: a unit of an admitted, prioritized item. Otherwise
    the named reasons: missing_authority:unit, missing_authority:backlog, missing_authority:admission (the
    item is not admitted), missing_authority:priority (admitted but not prioritized, or the unit outside the
    prioritized decomposition), blocked:backlog, missing_authority:backlog/<terminal state>."""
    u = _row(conn, uid)
    if u is None or u['kind'] != UNIT_KIND or not isinstance(u['data'], dict):
        return ['missing_authority:unit']
    b = _row(conn, u['data'].get('backlog_item_uuid'))
    if b is None or b['kind'] != KIND or not isinstance(b['data'], dict):
        return ['missing_authority:backlog']
    item, state = b['data'], b['data'].get('state')
    if state == 'BLOCKED':
        return ['blocked:backlog']
    if state in TERMINAL:
        return ['missing_authority:backlog/' + str(state)]
    if state == 'ADMITTED':
        return ['missing_authority:priority']
    if state not in EXECUTABLE_STATES:
        return ['missing_authority:admission']
    if u['data'].get('state') == 'PLANNED':
        return ['missing_authority:priority']
    if u['data'].get('state') in UNIT_TERMINAL:
        return ['missing_authority:unit/' + str(u['data'].get('state'))]
    if item.get('schema') == SCHEMA:
        if not isinstance(item.get('admission'), dict):
            return ['missing_authority:admission']
        if uid not in _prioritized(item):
            return ['missing_authority:priority']
    return []


def landed_receipt(conn, uid, revision):
    """The id of a complete VELDO-0057 confirmed-landing receipt of `uid` at `revision`, or None: the
    revision_landed fact for exactly that subject with a landing receipt that joins every link, for that
    unit (the same predicates the completion reader applies)."""
    subject = {'id': uid, 'revision': revision}
    for eid, text in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id', (RECEIPT_KIND,)):
        receipt = json.loads(text)
        if not isinstance(receipt, dict) or CC.fact_problems('revision_landed', receipt, subject):
            continue
        landing = receipt.get('publication_receipt')
        if isinstance(landing, dict) and not CC.landing_receipt_problems(landing) and landing.get('unit_id') == uid:
            return eid
    return None


def outcome_problems(conn, uid):
    """[] only when `uid` has an accepted outcome: its confirmed-landing receipt at its current revision, or
    the owner's authorized alternative outcome. A declared output, an attempt's end or a cancellation nobody
    authorized is never one: missing_outcome:<unit>."""
    u = unit(conn, uid)
    if u is None:
        return ['missing_outcome:' + str(uid)]
    if isinstance(u.get('revision'), int) and landed_receipt(conn, uid, u['revision']):
        return []
    alternative = u.get('alternative_outcome')
    if u.get('state') == 'CANCELED' and isinstance(alternative, dict):
        effect = _row(conn, alternative.get('effect_id'))
        if (effect is not None and effect['kind'] == EFFECT_KIND and effect['data'].get('ruling') == 'approve'
                and (effect['data'].get('target') or {}).get('ref') == uid
                and effect['data'].get('touchpoint') == DISPOSITION):
            return []
    return ['missing_outcome:' + uid]


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


class Backlog:
    """One repository's backlog service on the configured real store connection.

    `store` and `membership` are the control_store and control_membership modules; `sign(bytes)` signs
    journal records as `journal_signer`. `workspace` is the checkout whose declared unit outputs the service
    reports on (never decides on)."""

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

    # Commands.

    def apply(self, packet):
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        observation = dict(self.ids, schema=SCHEMA, operation=command.get('operation'), item=None,
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
            raise Refused('invalid_input', 'invalid backlog command or authority coordinates')
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
        if op == 'take':
            feature = _row(self.conn, command.get('feature')) if _is_str(command.get('feature')) else None
            if (feature is None or feature['kind'] != KIND or not command['feature'].startswith(FEATURE_PREFIX)):
                raise Refused('no_such_feature', str(command.get('feature'))[:128])
            iid, project = item_id(command['feature']), feature['data'].get('project')
            pinned = [command['feature'], feature['data'].get('objective_uuid')]
        else:
            iid = command.get('item')
            current = read(self.conn, iid) if _is_str(iid) and iid.startswith(ID_PREFIX) else None
            if current is None:
                raise Refused('no_such_item', str(iid)[:128])
            if command.get('item_version') != current['version']:
                raise Refused('stale_version', 'command names another item version')
            project = current['project']
            pinned = []
        observation['item'] = iid
        if not _is_str(project) or not _NAME.match(project):
            raise Refused('invalid_input:project', 'the item names no project')
        record = _row(self.conn, 'project:' + project)
        owner = (record or {}).get('data', {}).get('owner') if (record or {}).get('kind') == PROJECT_KIND else None
        problems = self._member_problems(state, principal, project, now)
        if op == 'cancel':
            problems = problems or self._owner_problems(state, principal, project, now)
            if principal != owner:
                problems.append('not_owner:project')
        elif op in ('admit', 'prioritize', 'resume', 'dispose_unit'):
            problems = problems or ['not_owner:' + p for p in self._owner_problems(state, owner, project, now)]
        if problems:
            raise Refused(problems[0], '; '.join(problems))
        written = self._written(op, iid, command)
        if _is_str(command.get('request')):
            request = _row(self.conn, command['request']) or {}
            reference = (request.get('data') or {}).get('settlement') or {}
            pinned += [command['request']] + [reference[k] for k in ('settlement_id', 'effect_id')
                                              if isinstance(reference, dict) and _is_str(reference.get(k))]
        if op == 'complete':
            for entry in (read(self.conn, iid) or {}).get('decomposition') or []:
                pinned.append(entry['unit'])
                pinned += [eid for (eid,) in self.conn.execute(
                    'SELECT id FROM entities WHERE kind=? AND instr(data, ?) > 0', (RECEIPT_KIND, json.dumps(entry['unit'])))]
        pinned.append('project:' + project)
        versions = {eid: (_row(self.conn, eid) or {}).get('version', 0)
                    for eid in dict.fromkeys(written + [p for p in pinned if _is_str(p)] + [principal])}
        observation['accepted_versions'] = versions
        params = dict(command=command, item=iid, project=project, at=now)
        stored = dict(command_id=command['command_id'], principal=principal, operation=OPERATION, parameters=params,
                      expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        receipt = self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        return {'ok': True, 'reason': op, 'item_id': iid, 'item': read(self.conn, iid), 'receipt': receipt}

    def _written(self, op, iid, command):
        """Every record the operation may write, so each is pinned at the version the command was decided on."""
        written = [iid]
        current = read(self.conn, iid) or {}
        units = [u['unit'] for u in current.get('decomposition') or []]
        if op == 'prepare':
            units = [u.get('unit') for u in command.get('units') or [] if isinstance(u, dict)]
        if op == 'append' and isinstance(command.get('unit'), dict):
            units = units + [command['unit'].get('unit')]
        units = [u for u in units if _is_str(u) and not CL.unit_id_problem(u)]
        if op in ('prepare', 'append', 'admit', 'prioritize', 'cancel', 'dispose_unit'):
            written += units
        if op in ('prepare', 'admit', 'prioritize'):
            written += [admission_id(u) for u in units]
        if op in ('block', 'resume'):
            blocks = current.get('blocks') or []
            block = 'block-%d' % (len(blocks) + 1) if op == 'block' else (blocks[-1] if blocks else {}).get('block_id')
            written += [blocker_id(iid, block, u) for u in units]
        return written

    def _member_problems(self, state, principal, project, now):
        entry = self.AC.membership_entry(state['membership'], principal)
        active, why = self.AC.active_member(entry, now)
        if not active:
            return ['not_authorized:' + str(why)]
        if not self.membership.scope_covers(entry.get('scope'), [project]):
            return ['not_authorized:scope']
        return []

    def _owner_problems(self, state, principal, project, now):
        problems = self._member_problems(state, principal, project, now)
        entry = self.AC.membership_entry(state['membership'], principal) or {}
        if problems:
            return problems
        if entry.get('principal_type') != 'person':
            return ['not_authorized:not_a_person']
        return [] if OWNER_ROLE in (entry.get('roles') or []) else ['not_authorized:role']

    # The transaction.

    def _in_transaction(self, conn, params, before):
        """Inside the store's write transaction: every record the operation decides on is read here, so
        what it decided on is what it commits over."""
        command, iid, now = params['command'], params['item'], params['at']
        op, principal = command['operation'], command['principal']
        entry = {'by': principal, 'at': now, 'command_id': command['command_id'], 'operation': op}
        project = _row(conn, 'project:' + params['project'])
        if project is None or project['kind'] != PROJECT_KIND:
            raise Refused('project_not_active:missing', params['project'])
        if op != 'cancel' and project['data'].get('state') != 'ACTIVE':
            # VELDO-0076: a paused, canceled or completed project shapes, admits, runs and finishes nothing.
            raise Refused('project_not_active:%s' % project['data'].get('state'), params['project'])
        if op == 'take':
            return self._take(conn, command, iid, project, entry)
        current = _row(conn, iid)
        if current is None or current['kind'] != KIND:
            raise Refused('no_such_item', iid)
        data = json.loads(json.dumps(current['data']))
        return getattr(self, '_' + op)(conn, command, data, project, entry)

    def _take(self, conn, command, iid, project, entry):
        feature = _row(conn, command['feature'])
        found = feature['data'] if feature is not None and feature['kind'] == KIND else {}
        if found.get('state') != 'RAW' or found.get('repository_uuid') != self.ids['repository_uuid']:
            raise Refused('no_such_feature', 'a backlog item is taken from a RAW feature of this repository')
        objective = _row(conn, found.get('objective_uuid'))
        if (objective is None or objective['kind'] != OBJECTIVE_KIND
                or objective['data'].get('state') not in ('ACCEPTED', 'ACTIVE')
                or objective['data'].get('project') != found.get('project')):
            raise Refused('not_approved:objective', 'the feature\'s objective is not accepted')
        if _row(conn, iid) is not None:
            raise Refused('already_exists', iid)
        if command.get('work_class') not in WORK_CLASSES:
            raise Refused('unsupported_work_class:%s' % command.get('work_class'), 'the ordinary lane only')
        data = dict(schema=SCHEMA, uuid=iid, entity_type=KIND, domain_uuid=self.ids['domain_uuid'],
                    repository_uuid=self.ids['repository_uuid'], project=found['project'],
                    project_uuid='project:' + found['project'], objective_uuid=found['objective_uuid'],
                    feature_uuid=command['feature'], title=found.get('title'), scope=list(found.get('scope') or []),
                    work_class=command['work_class'], state='RAW', decomposition_revision=0, decomposition=None,
                    decomposition_digest=None, admission=None, priority=None, priorities=[], blocks=[], applied=[],
                    completion=None, cancellation=None,
                    provenance={'source': 'take', 'created_by': entry['by'], 'created_at': entry['at']},
                    history=[dict(entry, source=None, target='RAW')])
        return {iid: {'kind': KIND, 'data': data}}

    def _unit_entry(self, conn, data, raw, taken):
        """One validated decomposition entry, or a named refusal."""
        if not isinstance(raw, dict) or set(raw) - set(UNIT_FIELDS) - {'produces'} or not set(UNIT_FIELDS) <= set(raw):
            raise Refused('invalid_input:unit', 'a unit names %s' % ', '.join(UNIT_FIELDS))
        name = raw['unit']
        problem = CL.unit_id_problem(name)
        if problem:
            raise Refused('invalid_input:unit_id', problem)
        if name in taken or _row(conn, name) is not None or _row(conn, admission_id(name)) is not None:
            raise Refused('already_exists:' + name, 'a unit alias names one unit')
        if not _is_str(raw['specification']) or not _NAME.match(raw['specification']):
            raise Refused('invalid_input:specification', 'a unit binds its primary specification by id')
        for field in ('scope', 'requirements', 'eligible_holders'):
            if not isinstance(raw[field], list) or not all(_is_str(v) for v in raw[field]):
                raise Refused('invalid_input:' + field, 'a unit lists its %s' % field)
        if not raw['scope'] or not raw['eligible_holders']:
            raise Refused('invalid_input:unit', 'a unit has a scope and at least one eligible holder')
        outside = [s for s in raw['scope'] if s not in data['scope']]
        if outside:
            raise Refused('out_of_scope:' + outside[0], 'a unit stays inside its item\'s scope')
        if 'produces' in raw and not _is_str(raw['produces']):
            raise Refused('invalid_input:produces', 'a declared output is a path')
        return {k: (list(raw[k]) if isinstance(raw[k], list) else raw[k]) for k in raw}

    def _new_unit(self, data, u, revision, entry):
        return dict(schema=UNIT_SCHEMA, uuid=u['unit'], entity_type=UNIT_KIND, state='PLANNED',
                    domain_uuid=self.ids['domain_uuid'], repository_uuid=self.ids['repository_uuid'],
                    backlog_item_uuid=data['uuid'], project=data['project'], primary_specification=u['specification'],
                    scope=list(u['scope']), scope_digest=unit_scope_digest(data['uuid'], u),
                    requirements=list(u['requirements']), eligible_holders=list(u['eligible_holders']),
                    produces=u.get('produces'), revision=1, depends_on=[], admitted_revision=None,
                    decomposition_revision=revision, alternative_outcome=None,
                    history=[dict(entry, source=None, target='PLANNED')])

    def _prepare(self, conn, command, data, project, entry):
        if data['state'] != 'RAW':
            raise Refused('invalid_transition:%s->PREPARED' % data['state'], 'only a RAW item is prepared')
        if entry['by'] != data['provenance']['created_by']:
            raise Refused('not_authorized:proposer', 'the proposer shapes the item')
        raws = command.get('units')
        if not isinstance(raws, list) or not raws:
            raise Refused('invalid_input:units', 'a decomposition lists at least one unit')
        units = []
        for raw in raws:
            units.append(self._unit_entry(conn, data, raw, {u['unit'] for u in units}))
        self._edge(KIND, 'RAW', 'PREPARED', {'intake_validated': True})
        data.update(state='PREPARED', decomposition=units, decomposition_revision=1,
                    decomposition_digest=decomposition_digest(data['uuid'], 1, units))
        data['history'] = list(data['history']) + [dict(entry, source='RAW', target='PREPARED', revision=1,
                                                        units=[u['unit'] for u in units])]
        changes = {data['uuid']: {'kind': KIND, 'data': data}}
        for u in units:
            changes[u['unit']] = {'kind': UNIT_KIND, 'data': self._new_unit(data, u, 1, entry)}
        return changes

    def _request_grooming(self, conn, command, data, project, entry):
        self._edge(KIND, data['state'], 'AWAITING_GROOMING', {'grooming_requested': True})
        data['history'] = list(data['history']) + [dict(entry, source=data['state'], target='AWAITING_GROOMING',
                                                        revision=data['decomposition_revision'])]
        data['state'] = 'AWAITING_GROOMING'
        return {data['uuid']: {'kind': KIND, 'data': data}}

    def _settled(self, conn, command, touchpoint, target, brief, project, applied):
        """The owner's settled answer the command names: (ruling, reference, effect). Every refusal is named."""
        if command.get('request') in applied:
            raise Refused('already_applied', 'this settled answer was applied already')
        request = _row(conn, command.get('request'))
        req = request['data'] if request is not None and request['kind'] == REQUEST_KIND else {}
        reference = req.get('settlement') if isinstance(req.get('settlement'), dict) else {}
        settlement, effect = _row(conn, reference.get('settlement_id')), _row(conn, reference.get('effect_id'))
        if (req.get('state') != 'SATISFIED' or settlement is None or settlement['kind'] != SETTLEMENT_KIND
                or effect is None or effect['kind'] != EFFECT_KIND
                or effect['data'].get('settlement_id') != settlement['data'].get('settlement_id')
                or settlement['data'].get('request_id') != command.get('request')):
            raise Refused('missing_evidence:settlement', 'the request is not settled')
        found = effect['data'].get('target') or {}
        if settlement['data'].get('touchpoint') != touchpoint or found.get('kind') != target['kind'] \
                or found.get('ref') != target['ref']:
            raise Refused('invalid_input:request', 'the settled request does not ask this of this record')
        if found != target:
            raise Refused('stale_subject:binding', 'the answer was given to another revision or block')
        if brief is not None and req.get('brief') != brief:
            raise Refused('stale_subject:brief', 'the owner was shown something other than this revision')
        owner = project['data'].get('owner')
        if req.get('owner') != owner or settlement['data'].get('principals') != [owner]:
            raise Refused('not_owner', 'only the project\'s owner decides this')
        ruling = settlement['data'].get('ruling')
        record = {'request_id': command['request'], 'request_version': reference.get('request_version'),
                  'settlement_id': reference['settlement_id'], 'effect_id': reference['effect_id'],
                  'receipt_id': reference.get('receipt_id'), 'ruling': ruling, 'principals': [owner]}
        return ruling, record, effect['data']

    def _admit(self, conn, command, data, project, entry):
        if data['state'] != 'AWAITING_GROOMING':
            raise Refused('invalid_transition:%s->ADMITTED' % data['state'], 'an item is admitted from grooming')
        ruling, record, _effect = self._settled(conn, command, ADMISSION, decision_target(data), admission_brief(data),
                                                project, data['applied'])
        if ruling not in ADMISSION_RULINGS:
            raise Refused('not_approved:%s' % ruling, 'the owner did not rule on the admission')
        target = ADMISSION_RULINGS[ruling]
        evidence = {'admission_authority_receipt': True, 'returned_for_elaboration': True}
        self._edge(KIND, 'AWAITING_GROOMING', target, evidence)
        record.update(revision=data['decomposition_revision'], digest=data['decomposition_digest'])
        changes = {}
        if target == 'ADMITTED':
            data['admission'] = record
            for u in data['decomposition']:
                changes[admission_id(u['unit'])] = {'kind': ADMISSION_KIND, 'data': dict(
                    schema=ADMISSION_SCHEMA, unit=u['unit'], state='accepted', backlog_item_uuid=data['uuid'],
                    scope_digest=unit_scope_digest(data['uuid'], u), decomposition_revision=data['decomposition_revision'],
                    request_id=record['request_id'], settlement_id=record['settlement_id'])}
        if target == 'REJECTED':
            changes.update(self._cancel_units(conn, data, entry, 'admission_refused'))
        data['state'] = target
        data['applied'] = list(data['applied']) + [command['request']]
        data['history'] = list(data['history']) + [dict(entry, source='AWAITING_GROOMING', target=target,
                                                        revision=data['decomposition_revision'],
                                                        request_id=command['request'], ruling=ruling)]
        changes[data['uuid']] = {'kind': KIND, 'data': data}
        return changes

    def _prioritize(self, conn, command, data, project, entry):
        source = data['state']
        if source not in ('ADMITTED', 'PRIORITIZED', 'ACTIVE'):
            raise Refused('invalid_transition:%s->PRIORITIZED' % source, 'only admitted work is prioritized')
        pending = [u for u in data['decomposition'] if (_row(conn, u['unit']) or {}).get('data', {}).get('state') == 'PLANNED']
        if not pending:
            raise Refused('nothing_to_prioritize', 'every unit of this revision is prioritized already')
        ruling, record, effect = self._settled(conn, command, PRIORITY, decision_target(data), priority_brief(data),
                                               project, data['applied'])
        data['applied'] = list(data['applied']) + [command['request']]
        history = dict(entry, source=source, target=source, revision=data['decomposition_revision'],
                       request_id=command['request'], ruling=ruling)
        changes = {}
        if ruling == 'approve':
            if source == 'ADMITTED':
                self._edge(KIND, 'ADMITTED', 'PRIORITIZED', {'priority_receipt': True})
                data['state'] = history['target'] = 'PRIORITIZED'
            rank = (effect.get('proposal') or {}).get('rank') if isinstance(effect.get('proposal'), dict) else None
            record.update(revision=data['decomposition_revision'], digest=data['decomposition_digest'],
                          rank=rank if isinstance(rank, int) and not isinstance(rank, bool) else None,
                          units=[u['unit'] for u in data['decomposition']])
            data['priority'] = record
            data['priorities'] = list(data['priorities']) + [record]
            for u in pending:
                row = _row(conn, u['unit'])
                ud = json.loads(json.dumps(row['data']))
                self._edge(UNIT_KIND, 'PLANNED', 'READY', {'primary_specification_revision_bound': _is_str(
                    ud.get('primary_specification')), 'backlog_item_prioritized': True})
                ud.update(state='READY', admitted_revision=data['decomposition_revision'])
                ud['history'] = list(ud['history']) + [dict(entry, source='PLANNED', target='READY',
                                                            request_id=command['request'])]
                changes[u['unit']] = {'kind': UNIT_KIND, 'data': ud}
                if _row(conn, admission_id(u['unit'])) is None:
                    changes[admission_id(u['unit'])] = {'kind': ADMISSION_KIND, 'data': dict(
                        schema=ADMISSION_SCHEMA, unit=u['unit'], state='accepted', backlog_item_uuid=data['uuid'],
                        scope_digest=unit_scope_digest(data['uuid'], u),
                        decomposition_revision=data['decomposition_revision'], request_id=record['request_id'],
                        settlement_id=record['settlement_id'])}
            history['units'] = [u['unit'] for u in pending]
        data['history'] = list(data['history']) + [history]
        changes[data['uuid']] = {'kind': KIND, 'data': data}
        return changes

    def _append(self, conn, command, data, project, entry):
        if data['state'] not in EXECUTABLE_STATES:
            raise Refused('invalid_transition:%s->%s' % (data['state'], data['state']),
                          'a unit is appended to prioritized work')
        u = self._unit_entry(conn, data, command.get('unit'), {x['unit'] for x in data['decomposition']})
        revision = data['decomposition_revision'] + 1
        units = list(data['decomposition']) + [u]
        data.update(decomposition=units, decomposition_revision=revision,
                    decomposition_digest=decomposition_digest(data['uuid'], revision, units))
        data['history'] = list(data['history']) + [dict(entry, source=data['state'], target=data['state'],
                                                        revision=revision, appended=u['unit'])]
        return {data['uuid']: {'kind': KIND, 'data': data},
                u['unit']: {'kind': UNIT_KIND, 'data': self._new_unit(data, u, revision, entry)}}

    def _open_units(self, conn, data):
        return [u['unit'] for u in data['decomposition'] or []
                if (_row(conn, u['unit']) or {}).get('data', {}).get('state') not in UNIT_TERMINAL]

    def _block(self, conn, command, data, project, entry):
        if not _is_str(command.get('phase')) or not _is_str(command.get('reason')):
            raise Refused('missing_field:phase', 'a block records the interrupted phase and its reason')
        self._edge(KIND, data['state'], 'BLOCKED', {'blocker_recorded': True})
        block = {'block_id': 'block-%d' % (len(data['blocks']) + 1), 'phase': command['phase'],
                 'reason': command['reason'], 'by': entry['by'], 'at': entry['at'], 'resolution': None}
        data['blocks'] = list(data['blocks']) + [block]
        data['history'] = list(data['history']) + [dict(entry, source='ACTIVE', target='BLOCKED',
                                                        block=block['block_id'], phase=block['phase'])]
        data['state'] = 'BLOCKED'
        changes = {data['uuid']: {'kind': KIND, 'data': data}}
        for u in self._open_units(conn, data):
            changes[blocker_id(data['uuid'], block['block_id'], u)] = {'kind': BLOCKER_KIND, 'data': dict(
                unit=u, backlog_item_uuid=data['uuid'], block=block['block_id'], cleared=False)}
        return changes

    def _resume(self, conn, command, data, project, entry):
        if data['state'] != 'BLOCKED':
            raise Refused('invalid_transition:%s->ACTIVE' % data['state'], 'only a blocked item resumes')
        ruling, record, _effect = self._settled(conn, command, DISPOSITION, block_target(data), None, project,
                                                data['applied'])
        if ruling != 'approve':
            raise Refused('not_approved:%s' % ruling, 'the owner did not resolve the block')
        self._edge(KIND, 'BLOCKED', 'ACTIVE', {'resolution_validated': True})
        block = dict(data['blocks'][-1], resolution=record)
        data['blocks'] = list(data['blocks'][:-1]) + [block]
        data['applied'] = list(data['applied']) + [command['request']]
        data['state'] = 'ACTIVE'
        data['history'] = list(data['history']) + [dict(entry, source='BLOCKED', target='ACTIVE', block=block['block_id'],
                                                        resumed_phase=block['phase'], request_id=command['request'])]
        changes = {data['uuid']: {'kind': KIND, 'data': data}}
        for (eid, text) in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id', (BLOCKER_KIND,)):
            found = json.loads(text)
            if found.get('backlog_item_uuid') == data['uuid'] and found.get('block') == block['block_id']:
                changes[eid] = {'kind': BLOCKER_KIND, 'data': dict(found, cleared=True, resolution=record['request_id'])}
        return changes

    def _dispose_unit(self, conn, command, data, project, entry):
        uid = command.get('unit')
        if data['state'] in TERMINAL:
            raise Refused('invalid_transition:%s->%s' % (data['state'], data['state']), 'a finished item disposes of nothing')
        if uid not in [u['unit'] for u in data['decomposition'] or []]:
            raise Refused('invalid_input:unit', 'the unit is not in this item\'s decomposition')
        row = _row(conn, uid)
        ud = json.loads(json.dumps(row['data']))
        ud['uuid'] = uid
        ruling, record, effect = self._settled(conn, command, DISPOSITION, unit_target(ud), None, project, data['applied'])
        outcome = (effect.get('proposal') or {}).get('outcome') if isinstance(effect.get('proposal'), dict) else None
        if ruling != 'approve':
            raise Refused('not_approved:%s' % ruling, 'the owner did not authorize an alternative outcome')
        if outcome not in ALTERNATIVE_OUTCOMES:
            raise Refused('unsupported_outcome:%s' % outcome, 'the authorized alternative outcomes are named')
        self._edge(UNIT_KIND, ud['state'], 'CANCELED', {'disposition_recorded': True})
        record['outcome'] = outcome
        source, ud['state'], ud['alternative_outcome'] = ud['state'], 'CANCELED', record
        ud['history'] = list(ud['history']) + [dict(entry, source=source, target='CANCELED', outcome=outcome,
                                                    request_id=command['request'])]
        data['applied'] = list(data['applied']) + [command['request']]
        data['history'] = list(data['history']) + [dict(entry, source=data['state'], target=data['state'], unit=uid,
                                                        outcome=outcome, request_id=command['request'])]
        return {data['uuid']: {'kind': KIND, 'data': data}, uid: {'kind': UNIT_KIND, 'data': ud}}

    def _complete(self, conn, command, data, project, entry):
        if data['state'] != 'ACTIVE':
            raise Refused('invalid_transition:%s->DONE' % data['state'], 'only active work is done')
        missing, outcomes = [], {}
        for u in data['decomposition']:
            problems = outcome_problems(conn, u['unit'])
            if problems:
                missing.extend(problems)
                continue
            found = unit(conn, u['unit'])
            receipt = landed_receipt(conn, u['unit'], found.get('revision'))
            outcomes[u['unit']] = ({'receipt_id': receipt, 'revision': found.get('revision')} if receipt
                                   else {'alternative_outcome': found['alternative_outcome']})
        if missing:
            raise Refused(missing[0], '; '.join(missing))
        self._edge(KIND, 'ACTIVE', 'DONE', {'required_units_completed_or_reconciled': True})
        data['state'] = 'DONE'
        data['completion'] = {'by': entry['by'], 'at': entry['at'], 'outcomes': outcomes}
        data['history'] = list(data['history']) + [dict(entry, source='ACTIVE', target='DONE')]
        return {data['uuid']: {'kind': KIND, 'data': data}}

    def _cancel_units(self, conn, data, entry, why):
        changes = {}
        for uid in self._open_units(conn, data):
            ud = json.loads(json.dumps(_row(conn, uid)['data']))
            self._edge(UNIT_KIND, ud['state'], 'CANCELED', {'disposition_recorded': True})
            ud['history'] = list(ud['history']) + [dict(entry, source=ud['state'], target='CANCELED', why=why)]
            ud['state'] = 'CANCELED'
            changes[uid] = {'kind': UNIT_KIND, 'data': ud}
        return changes

    def _cancel(self, conn, command, data, project, entry):
        if entry['by'] != project['data'].get('owner'):
            raise Refused('not_owner:project', 'the project\'s owner cancels its backlog item')
        if not _is_str(command.get('reason')):
            raise Refused('missing_field:reason', 'a cancellation says why')
        source = data['state']
        self._edge(KIND, source, 'CANCELED', {'disposition_recorded': True})
        changes = self._cancel_units(conn, data, entry, 'item_canceled')
        data['state'] = 'CANCELED'
        data['cancellation'] = {'reason': command['reason'], 'by': entry['by'], 'at': entry['at']}
        data['history'] = list(data['history']) + [dict(entry, source=source, target='CANCELED')]
        changes[data['uuid']] = {'kind': KIND, 'data': data}
        return changes

    @staticmethod
    def _edge(kind, source, target, evidence):
        allowed, why = EC.transition(kind, source, target, evidence)
        if not allowed:
            raise Refused('invalid_transition:%s->%s' % (source, target), why)

    # Reads.

    def outputs(self, iid):
        """{unit: whether its declared output exists in the workspace}: reported, never an outcome."""
        out = {}
        for u in (read(self.conn, iid) or {}).get('decomposition') or []:
            produces = u.get('produces')
            out[u['unit']] = bool(self.workspace and _is_str(produces) and (Path(self.workspace) / produces).exists())
        return out

    def metrics(self):
        """Accepted and refused commands, items by state and the pending work: items awaiting grooming,
        admission or priority, units awaiting prioritization, and blocked items."""
        states, planned = {}, 0
        for (text,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,)):
            data = json.loads(text)
            if data.get('schema') == SCHEMA:
                states[str(data.get('state'))] = states.get(str(data.get('state')), 0) + 1
        for (text,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (UNIT_KIND,)):
            data = json.loads(text)
            planned += data.get('schema') == UNIT_SCHEMA and data.get('state') == 'PLANNED'
        return dict(self.counts, items=states,
                    pending={'awaiting_grooming': states.get('PREPARED', 0) + states.get('AWAITING_GROOMING', 0),
                             'awaiting_priority': states.get('ADMITTED', 0), 'units_awaiting_priority': planned,
                             'blocked': states.get('BLOCKED', 0)})
