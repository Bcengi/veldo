"""Project ownership, charter and lifecycle (PLAN-0019 W61, VELDO-0076, R04, R05).

WHAT THIS MODULE IS. The one writer of a repository's project records in the control store. A
project is the continuing coordination boundary its objectives, backlog items and execution units
belong to: entity `project:<name>` of kind `project`, the identity every existing reader already
resolves (the eligibility Gate reads `project:<unit.project>`, the inbox walks unit, backlog item,
objective and `project_uuid`). The service declares that kind, and the `project:` id prefix, as its
own (control_store's declare_owners), so no other command on any connection writes a project record
or any other record at a project's id (the Gate judges a unit's project only from a record of kind
project, so a record of another kind there would stop the project's units and block its activation).

Every change is a real signed command from the enrolled owner: {'command': body, 'signature'} where
the body carries the operation, the project name, the principal, a command id, a nonce and the
store's coordinates, signed under the command namespace with the principal's active verification
key. The principal must be an active person holding `project_owner` in a membership scope that covers
the project, and for every operation after activation the owner the record names.

THE LIFECYCLE is entity_contract's R05 vocabulary and nothing else: every transition is asked of
entity_contract.transition with the evidence this service established, so an undeclared edge, a
terminal source or a missing predicate is refused by name.

  activate  creates the record ACTIVE through the declared DRAFT -> ACTIVE edge (the record never sits
            in DRAFT: Release 1 has no draft authoring). It binds ACTIVATION_FIELDS: the owner (the
            signer), the charter (signed with the command; its digest and charter_revision 1 are
            kept), the execution repository (this store's one repository), the authority policy
            (each touchpoint's roles, every role held by a current person member in the project's
            scope: authority_policy_applies) and a finite coordination budget (every required
            unit present, every cap a finite positive number: bounded_coordination_budget). An
            omitted field refuses missing_field:<field>; an existing project refuses already_exists.
  pause     ACTIVE -> PAUSED. From the moment it commits the Gate refuses every station of the
            project's units (project_not_active:PAUSED), so the frontier offers nothing from it, a
            claim, a preparation and a receiver's recheck all refuse, and no dispatch starts. The
            record names the project's dispatches that were accepted or running at commit, and the
            service then asks the host's ordinary stop of each (the runner's Launch.stop, R44's
            cooperative stop and the containment group's escalation, through `stop`), which is the
            stop_policy_invoked predicate. Nothing else is written: history and receipts stay.
  resume    PAUSED -> ACTIVE, with the activation predicates judged again over the record now.
  cancel    DRAFT, ACTIVE or PAUSED -> CANCELED with a recorded disposition of its unfinished work;
            the same stop as a pause. CANCELED is terminal.
  complete  ACTIVE or PAUSED -> COMPLETED only when, read inside the completing transaction, every
            objective of the project is terminal and no assignment, governing decision, dispatch,
            release execution or reservation of it is open (OBLIGATIONS). An open one refuses
            open_obligation:<kind>, naming every open (kind, id), and writes nothing.

Each transition appends one entry to the record's `history` and never changes an earlier one.

WHAT BELONGS TO A PROJECT. Its units: execution units whose `project` is the name, or whose chain
(backlog item, objective, project_uuid) ends at the project. Objectives: `project_uuid` is the
project's id. Assignments: an inbox assignment whose scope names the project or whose unit is one
of its units. Decisions: a governing decision still blocking one of its units, as the eligibility
Gate's decision_blockers answers over this same connection and the configured settlement trust
(none trusted means none settled). Dispatches: a record whose contract reserves for the project or
runs one of its units, in a holding state. Reservations: a worker slot of the project not retired,
or a call of it still pending or unknown.

STATED LIMITS. A project record written before this service (no `state`) is not judged by the
Gate's lifecycle rule; nothing writes one once the service has declared the kind. An ACTIVE
project whose recorded owner loses project_owner or the project's scope, or is revoked or expires,
can be paused, canceled or completed by nobody, so the Gate halts its units at their next station
(project_not_active:owner_not_current) until he is current again. Ownership transfer (handover to a
new owner), additional owners and delegation are Release 3; concurrent activation and restart are
Release 2. Observations carry identities, versions, outcomes and named refusals, never charter text,
reasons, dispositions or signatures. Standard library only.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sqlite3
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('project_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EC = _organ('entity_contract')
EL = _organ('control_eligibility')

SCHEMA = 'veldo.project/v1'
KIND = 'project'
ID_PREFIX = 'project:'
OPERATION = 'project_operation'
OWNER = 'VELDO-0076 project lifecycle'
WRITES = ('entities', 'journal', 'commands', 'nonces')
OPERATIONS = ('activate', 'pause', 'resume', 'cancel', 'complete')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
OWNER_ROLE = 'project_owner'
# What activation binds (R04, R05), in the order a missing one is named.
ACTIVATION_FIELDS = ('owner', 'charter', 'execution_repository', 'authority_policy', 'coordination_budget')
# The DRAFT -> ACTIVE predicates, each established by one check below.
ACTIVATION_PREDICATES = ('signed_charter', 'resolvable_owner', 'authority_policy_applies', 'bounded_coordination_budget')
# The coordination budget's units: the reservation service's (VELDO-0036) and the owner's minutes.
BUDGET_UNITS = ('capacity', 'invocations', 'wall_seconds', 'tokens', 'messages', 'owner_minutes')
REQUIRED_BUDGET = ('capacity', 'invocations', 'wall_seconds')
# The dispatch states a live receiver holds (control_dispatch): the ones the host's stop is asked of.
STOPPABLE = ('accepted', 'running')
HOLDING_DISPATCH = ('prepared', 'accepted', 'running', 'unknown')
# The completion obligations, each with the R05 predicate it establishes.
OBLIGATIONS = (('objective', 'objectives_terminal'), ('assignment', 'assignments_reconciled'),
               ('decision', 'decisions_reconciled'), ('dispatch', 'dispatches_reconciled'),
               ('release_execution', 'release_executions_reconciled'), ('reservation', 'reservations_reconciled'))
TAXONOMY = {'invalid_input': 'invalid_input', 'missing_field': 'invalid_input', 'unbounded_budget': 'invalid_input',
            'no_such_project': 'invalid_input', 'not_authorized': 'missing_authority', 'not_owner': 'missing_authority',
            'inapplicable_policy': 'missing_authority', 'already_exists': 'stale_subject',
            'stale_subject': 'stale_subject', 'stale_version': 'stale_subject', 'invalid_transition': 'stale_subject',
            'open_obligation': 'missing_evidence', 'unavailable_service': 'unavailable_service'}
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def project_id(name):
    return ID_PREFIX + name


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                 ensure_ascii=True).encode()).hexdigest()


def charter_problems(charter):
    if not isinstance(charter, dict) or not _is_str(charter.get('purpose')):
        return ['invalid_input:charter']
    return []


def budget_problems(budget):
    """Why a coordination budget is not finite: every required unit present, no unknown unit, and
    every cap a finite number above zero (a bool, None, text, infinity or a negative is unbounded)."""
    if not isinstance(budget, dict) or not budget:
        return ['unbounded_budget:budget']
    problems = ['unbounded_budget:' + unit for unit in REQUIRED_BUDGET if unit not in budget]
    for unit in sorted(budget, key=str):
        cap = budget[unit]
        if unit not in BUDGET_UNITS:
            problems.append('unbounded_budget:%s' % unit)
        elif (not isinstance(cap, (int, float)) or isinstance(cap, bool) or not math.isfinite(cap) or cap <= 0):
            problems.append('unbounded_budget:' + unit)
    return problems


def read(store, conn, name):
    """The accepted project record of `name` on any connection (another process's read-only one
    included), or None."""
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (project_id(name),)).fetchone()
    if row is None or row[0] != KIND:
        return None
    return dict(json.loads(row[2]), version=row[1])


def runner_stop(runner):
    """The host's ordinary stop of a running dispatch, as the VELDO-0039 runner holds it: the Launch
    it submitted asks its receiver to stop (R44's cooperative stop, then the group's escalation).
    False when this runner holds no receiver of that dispatch."""
    def stop(dispatch_id, reason):
        launch = runner.launches.get(dispatch_id)
        return bool(launch is not None and launch.stop(reason))
    return stop


class Refused(Exception):
    def __init__(self, code, detail='', obligations=()):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail, self.obligations = code, detail, list(obligations)


class Projects:
    """One repository's project service on the configured real store connection.

    `store` and `membership` are the control_store and control_membership modules; `sign(bytes)`
    signs journal records as `journal_signer`. `stop(dispatch_id, reason) -> bool` is the host's
    ordinary stop of running work (runner_stop(runner) in production). `settlement_trust` is the
    VELDO-0054 settlement verifier the completion's decision read uses (None settles nothing)."""

    def __init__(self, store, membership, conn, coordinates, journal_signer, sign, *, stop,
                 settlement_trust=None, authority_generation=1, clock=time.time):
        if set(coordinates) != set(COORDINATES) or not all(_is_str(v) for v in coordinates.values()):
            raise Refused('invalid_input', 'coordinates are domain, repository and store identities')
        if not callable(stop):
            raise Refused('invalid_input', 'the host stop policy is required')
        self.store, self.membership, self.AC = store, membership, membership.AC
        self.conn, self.ids = conn, dict(coordinates)
        self.journal_signer, self.sign, self.stop = journal_signer, sign, stop
        self.settlement_trust, self.authority_generation, self.clock = settlement_trust, authority_generation, clock
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction, 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={KIND: (OPERATION,)}, prefixes={ID_PREFIX: (OPERATION,)},
                             module=__file__)

    # Commands.

    def apply(self, packet):
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        observation = dict(self.ids, schema=SCHEMA, operation=command.get('operation'), project=None,
                           command_id=command.get('command_id'), accepted_versions={})
        try:
            result = self._apply(packet, command, observation)
        except Refused as exc:
            result = {'ok': False, 'reason': exc.code, 'obligations': exc.obligations}
        except self.store.StoreRefused as exc:
            result = {'ok': False, 'reason': exc.code, 'obligations': []}
        except sqlite3.Error:
            result = {'ok': False, 'reason': 'unavailable_service', 'obligations': []}
        observation.update(outcome='accepted' if result['ok'] else 'refused',
                           refusal=None if result['ok'] else result['reason'],
                           taxonomy=None if result['ok'] else taxonomy(result['reason']),
                           obligations=[dict(o) for o in result.get('obligations') or []])
        self.counts[observation['outcome']] += 1
        self.observations.append(observation)
        return result

    def _apply(self, packet, command, observation):
        if (not isinstance(packet, dict) or not isinstance(packet.get('command'), dict)
                or not isinstance(packet.get('signature'), str) or not packet['signature'].isascii()):
            raise Refused('invalid_input', 'command must be a mapping and signature ASCII text')
        required = {'operation', 'project', 'principal', 'command_id', 'nonce', *COORDINATES}
        if (not required <= command.keys() or command['operation'] not in OPERATIONS
                or not all(_is_str(command[k]) for k in ('principal', 'command_id', 'nonce', 'project'))
                or not _NAME.match(command['project']) or any(command[k] != v for k, v in self.ids.items())):
            raise Refused('invalid_input', 'invalid project command or authority coordinates')
        op, principal, name = command['operation'], command['principal'], command['project']
        pid = project_id(name)
        observation['project'] = pid
        state = self.membership.authority_state(self.store, self.conn)
        now = self.clock()
        key = self.AC.active_key(state['keyring'], principal, now)
        if not key:
            raise Refused('not_authorized', 'no active verification key')
        verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), packet['signature'],
                                                self.AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise Refused('not_authorized', 'command signature did not verify')
        owner_problems = self._owner_problems(state, principal, name, now)
        if owner_problems:
            raise Refused(owner_problems[0], '; '.join(owner_problems))
        entities = state['entities']
        current = entities.get(pid)
        params = dict(action=op, project_id=pid, name=name, principal=principal, command_id=command['command_id'],
                      at=now)
        if op == 'activate':
            if current is not None:
                raise Refused('already_exists', pid)
            missing = [f for f in ACTIVATION_FIELDS if f not in command]
            if missing:
                raise Refused('missing_field:' + missing[0], ', '.join(missing))
            if command['owner'] != principal:
                raise Refused('not_owner', 'the owner activates the project, and is its signer')
            if command['execution_repository'] != self.ids['repository_uuid']:
                raise Refused('invalid_input:execution_repository', 'one execution repository: this store\'s')
            fields = {f: command[f] for f in ACTIVATION_FIELDS}
            self._activation_evidence(fields, state, name, now)
            params['fields'] = fields
        else:
            if current is None or current.get('kind') != KIND or not isinstance(current.get('data'), dict):
                raise Refused('no_such_project', pid)
            data = current['data']
            if command.get('project_version') != current['version']:
                raise Refused('stale_subject', 'command names another project version')
            if data.get('owner') != principal:
                raise Refused('not_owner', 'only the project\'s owner changes its lifecycle')
            if op in ('pause', 'cancel'):
                if not _is_str(command.get('reason')):
                    raise Refused('missing_field:reason', 'a pause or cancel says why')
                params['reason'] = command['reason']
            if op == 'cancel':
                if not _is_str(command.get('disposition')):
                    raise Refused('missing_field:disposition', 'a cancel records the disposition of its work')
                params['disposition'] = command['disposition']
            if op == 'resume':
                self._activation_evidence(data, state, name, now)
        versions = {eid: entities.get(eid, {}).get('version', 0) for eid in (pid, principal, key['key_id'])}
        observation['accepted_versions'] = versions
        stored = dict(command_id=command['command_id'], principal=principal, operation=OPERATION, parameters=params,
                      expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        receipt = self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        record = read(self.store, self.conn, name)
        result = {'ok': True, 'reason': op, 'project_id': pid, 'project': record, 'receipt': receipt,
                  'stops': [], 'obligations': []}
        if op in ('pause', 'cancel') and not receipt.get('replayed'):
            # The ordinary host stop of every running dispatch the committed record names.
            reason = 'project_%s:%s' % ('paused' if op == 'pause' else 'canceled', name)
            for dispatch_id in (record or {}).get('stopping') or []:
                try:
                    asked = bool(self.stop(dispatch_id, reason))
                except Exception:  # noqa: BLE001 - an unreachable receiver is reported, the pause stands
                    asked = False
                result['stops'].append({'dispatch': dispatch_id, 'asked': asked})
        observation['stops'] = [dict(s) for s in result['stops']]
        return result

    def _owner_problems(self, state, principal, name, now):
        entry = self.AC.membership_entry(state['membership'], principal)
        active, why = self.AC.active_member(entry, now)
        if not active:
            return ['not_authorized:' + str(why)]
        if entry.get('principal_type') != 'person':
            return ['not_authorized:not_a_person']
        if OWNER_ROLE not in (entry.get('roles') or []):
            return ['not_authorized:role']
        if not self.membership.scope_covers(entry.get('scope'), [name]):
            return ['not_authorized:scope']
        return []

    def _policy_problems(self, policy, state, name, now):
        if not isinstance(policy, dict) or not policy:
            return ['invalid_input:authority_policy']
        problems = []
        for touchpoint in sorted(policy, key=str):
            roles = policy[touchpoint]
            if (not isinstance(touchpoint, str) or not _NAME.match(touchpoint) or not isinstance(roles, list) or not roles
                    or not all(r in self.AC.ROLES for r in roles)):
                problems.append('invalid_input:authority_policy')
                continue
            for role in roles:
                holders = [m for m in state['membership'] if self.AC.active_member(m, now)[0]
                           and m.get('principal_type') == 'person' and role in (m.get('roles') or [])
                           and self.membership.scope_covers(m.get('scope'), [name])]
                if not holders:
                    problems.append('inapplicable_policy:%s/%s' % (touchpoint, role))
        return problems

    def _activation_evidence(self, fields, state, name, now):
        """The DRAFT -> ACTIVE (and PAUSED -> ACTIVE) predicates over `fields`, refused by name."""
        checks = {
            'signed_charter': charter_problems(fields.get('charter')),
            'resolvable_owner': self._owner_problems(state, fields.get('owner'), name, now),
            'authority_policy_applies': self._policy_problems(fields.get('authority_policy'), state, name, now),
            'bounded_coordination_budget': budget_problems(fields.get('coordination_budget')),
        }
        codes = [code for predicate in ACTIVATION_PREDICATES for code in checks[predicate]]
        if codes:
            raise Refused(codes[0], '; '.join(codes))
        return {predicate: not checks[predicate] for predicate in ACTIVATION_PREDICATES}

    # The transaction.

    def _in_transaction(self, conn, params, before):
        """Inside the store's write transaction: the project row, the lifecycle edge and (for complete)
        every obligation are read here, so what the command decided on is what it commits over."""
        pid, op, now = params['project_id'], params['action'], params['at']
        current = before.get(pid)
        entry = {'by': params['principal'], 'at': now, 'command_id': params['command_id']}
        if op == 'activate':
            if current is not None:
                raise Refused('already_exists', pid)
            fields = params['fields']
            evidence = {p: True for p in ACTIVATION_PREDICATES}
            self._edge('DRAFT', 'ACTIVE', evidence)
            data = dict(schema=SCHEMA, name=params['name'], state='ACTIVE', domain_uuid=self.ids['domain_uuid'],
                        repository_uuid=self.ids['repository_uuid'], charter_digest=_digest(fields['charter']),
                        charter_revision=1, provenance={'source': 'activate', 'created_by': params['principal'],
                                                        'created_at': now},
                        history=[dict(entry, source='DRAFT', target='ACTIVE')], stopping=[], **fields)
            return {pid: {'kind': KIND, 'data': data}}
        if current is None or current.get('kind') != KIND:
            raise Refused('no_such_project', pid)
        data = json.loads(json.dumps(current['data']))
        source = data.get('state')
        target = {'pause': 'PAUSED', 'resume': 'ACTIVE', 'cancel': 'CANCELED', 'complete': 'COMPLETED'}[op]
        if op == 'resume':
            evidence = {p: True for p in ACTIVATION_PREDICATES}
        elif op in ('pause', 'cancel'):
            data['stopping'] = self._running(conn, data['name'])
            evidence = {'stop_policy_invoked': True, 'disposition_recorded': _is_str(params.get('disposition'))}
        else:
            open_ = self.obligations(data['name'], conn)
            if open_:
                raise Refused('open_obligation:' + open_[0]['kind'],
                              ', '.join('%s:%s' % (o['kind'], o['id']) for o in open_), open_)
            evidence = {predicate: True for _kind, predicate in OBLIGATIONS}
        self._edge(source, target, evidence)
        data['state'] = target
        data['history'] = list(data.get('history') or []) + [dict(entry, source=source, target=target, **{
            k: params[k] for k in ('reason', 'disposition') if k in params})]
        return {pid: {'kind': KIND, 'data': data}}

    @staticmethod
    def _edge(source, target, evidence):
        allowed, why = EC.transition(KIND, source, target, evidence)
        if not allowed:
            raise Refused('invalid_transition:%s->%s' % (source, target), why)

    # Reads.

    @staticmethod
    def _kind(conn, kind):
        return [(eid, json.loads(data)) for eid, data in
                conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id', (kind,))]

    def _units(self, conn, name):
        """The project's execution units: its name on the unit, or its id at the end of the unit's chain."""
        pid = project_id(name)
        rows = {eid: (kind, json.loads(data)) for eid, kind, data in
                conn.execute("SELECT id, kind, data FROM entities WHERE kind IN ('backlog_item', 'objective')")}
        units = []
        for eid, data in self._kind(conn, 'execution_unit'):
            if not isinstance(data, dict):
                continue
            if data.get('project') == name:
                units.append(eid)
                continue
            backlog = rows.get(data.get('backlog_item_uuid')) if isinstance(data.get('backlog_item_uuid'), str) else None
            objective = (rows.get(backlog[1].get('objective_uuid')) if backlog and backlog[0] == 'backlog_item'
                         and isinstance(backlog[1], dict) and isinstance(backlog[1].get('objective_uuid'), str) else None)
            if objective and objective[0] == 'objective' and isinstance(objective[1], dict) \
                    and objective[1].get('project_uuid') == pid:
                units.append(eid)
        return units

    def _running(self, conn, name):
        units = set(self._units(conn, name))
        return [data['dispatch_id'] if _is_str(data.get('dispatch_id')) else eid
                for eid, data in self._kind(conn, 'dispatch')
                if isinstance(data, dict) and data.get('state') in STOPPABLE and self._dispatch_of(data, name, units)]

    @staticmethod
    def _dispatch_of(data, name, units):
        contract = data.get('contract') if isinstance(data.get('contract'), dict) else {}
        reservation = contract.get('reservation') if isinstance(contract.get('reservation'), dict) else {}
        return reservation.get('project') == name or contract.get('unit') in units

    def obligations(self, name, conn=None):
        """Every open obligation of the project, [{kind, id}] in OBLIGATIONS order: the pending work
        its completion waits on. Read on `conn` (inside the completing transaction) or this service's."""
        conn = conn or self.conn
        pid = project_id(name)
        units = self._units(conn, name)
        found = []
        terminal = {k: set(EC.LIFECYCLES[k]['terminal']) for k in ('objective', 'assignment', 'release_execution')}
        for eid, data in self._kind(conn, 'objective'):
            if isinstance(data, dict) and data.get('project_uuid') == pid and data.get('state') not in terminal['objective']:
                found.append({'kind': 'objective', 'id': eid})
        for eid, data in self._kind(conn, 'assignment'):
            if not isinstance(data, dict) or data.get('state') in terminal['assignment']:
                continue
            scope = data.get('scope')
            if (isinstance(scope, list) and name in scope) or data.get('unit_id') in units:
                found.append({'kind': 'assignment', 'id': eid})
        gate = EL.Gate(self.store, conn, domain_uuid=self.ids['domain_uuid'], repository_uuid=self.ids['repository_uuid'],
                       settlement_trust=self.settlement_trust)
        for unit in units:
            for code in gate.decision_blockers(unit):
                found.append({'kind': 'decision', 'id': '%s:%s' % (unit, code)})
        for eid, data in self._kind(conn, 'dispatch'):
            if isinstance(data, dict) and data.get('state') in HOLDING_DISPATCH and self._dispatch_of(data, name, set(units)):
                found.append({'kind': 'dispatch', 'id': eid})
        for eid, data in self._kind(conn, 'release_execution'):
            if (isinstance(data, dict) and (data.get('project') == name or data.get('project_uuid') == pid)
                    and data.get('state') not in terminal['release_execution']):
                found.append({'kind': 'release_execution', 'id': eid})
        for eid, data in self._kind(conn, 'subscription_reservation'):
            context = data.get('context') if isinstance(data, dict) and isinstance(data.get('context'), dict) else {}
            if context.get('project') != name or context.get('domain') != self.ids['domain_uuid']:
                continue
            if (data.get('type') == 'worker' and not data.get('retired')) or (
                    data.get('type') == 'invocation' and data.get('state') in ('pending', 'unknown')):
                found.append({'kind': 'reservation', 'id': eid})
        return found

    def metrics(self):
        """Accepted and refused commands, and the projects by lifecycle state (the pending work)."""
        states = {}
        for _eid, data in self._kind(self.conn, KIND):
            if isinstance(data, dict):
                states[str(data.get('state'))] = states.get(str(data.get('state')), 0) + 1
        return dict(self.counts, projects=states)
