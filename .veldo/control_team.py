"""Versioned team configuration (PLAN-0019 W74, VELDO-0089).

WHAT THIS MODULE IS. The one writer of a project's team record and of the builder and reviewer
assignments made under it, in the control store. A team is plain versioned data: entity `team:<name>`
of kind `team` for project `project:<name>` (VELDO-0076). It names exactly one project manager and
the required elaboration, implementation and independent review roles (REQUIRED_ROLES), each with
exactly the fields of ROLE_FIELDS: its workers, responsibilities, expertise, proposal permissions,
engine eligibility, budget and independence. The schema is closed: any other field, a tool list, an
MCP server list or any second capability filter among them, is refused by name. A role's tools and
MCP servers come only from VELDO-0127's versioned capability configuration, never from here. The
service declares both kinds and both id prefixes as its own (control_store's declare_owners), so no
other command writes a team or a team assignment.

Every change is a real signed command {'command': body, 'signature'} verified against the signer's
active key: the body carries the operation, the project, the principal, a command id, a nonce and
the store's coordinates. The project must be ACTIVE (project_not_active:<state> otherwise).

  propose  A member in the project's scope proposes the next revision, bound to the team record's
           current version (stale_subject:version otherwise). The team is judged against the schema
           (invalid_input:<what>) and against the project's requirements (staffing_problems): every
           required role staffed, one project manager, every worker an enrolled active member in the
           project's scope, the role's required responsibility present, every engine a registered
           subscription adapter (VELDO-0036), every budget finite and inside the project's
           coordination budget, and independent review separate from implementation by principal and
           independence group. Missing or conflicting staffing writes no team: it opens an owner
           request in the VELDO-0064 inbox, addressed to the project's owner and naming every problem,
           and refuses incomplete_roster:<first problem>. A worker is never invented. A complete
           proposal is recorded as the pending proposal: its revision, the revision it amends and the
           digest of exactly its content.
  amend    The owner's answer, settled by the VELDO-0068 settlement on the decision_disposition
           touchpoint, is applied. The settled terms target this team at the pending proposal's
           revision and digest (amendment_target), the request showed exactly amendment_brief of it,
           the request is addressed to the project's recorded owner, who is current, and he is the
           settlement's only principal. The command is bound to the team record's version. A stale
           version, an answer to another proposal or another revision, an altered command, a request
           the owner did not settle and a manager's own answer all refuse and write nothing. The
           accepted revision is appended to `revisions`, which no command ever rewrites.
  assign   The project manager of the current team (or the project's owner) assigns one builder and
           the reviewers of one execution unit of the project, bound to the current team revision
           and to the applicable VELDO-0049 engineering-review policy (review-policy:<repository>,
           each risk tier's count of distinct independent reviews). A missing policy, or no count for
           the unit's risk, refuses missing_authority:review_policy: nothing defaults to no review.
           The builder is an implementation worker, each reviewer an independent review worker; fewer
           distinct reviewers than the count refuses insufficient_reviews:<n>/<need>; a reviewer who
           is the builder, shares the builder's independence group or repeats another reviewer refuses
           reviewer_not_independent:<reviewer>; and every position is bound to the exact subject (the
           unit, its revision and its scope digest), a mismatch refusing wrong_subject:<position>.

THE ROSTER IS NOT AUTHORITY. Nothing here writes a membership, a role, a delegation or a key, and a
proposal permission is a kind of proposal the role may make (PROPOSAL_KINDS), never a right to admit,
prioritize, settle or approve: naming an R37 role or a settlement touchpoint as one refuses
roster_not_authority:<role>/<name>. Admission and every other authority stay where VELDO-0025 and
VELDO-0068 keep them.

STATED LIMITS. Concurrent amendment races, mid-cycle reassignment and recovery are Release 2;
additional owners and delegation are Release 3; adversarial decision review (VELDO-0070) is not
invoked. Observations carry identities, versions, outcomes and named refusals, never team content or
signatures. Standard library only.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sqlite3
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('team_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AC = _organ('authority_contract')
PJ = _organ('control_project')
RT = _organ('control_reservation_runtime')
ST = _organ('control_request_settlement')

SCHEMA = 'veldo.team/v1'
ASSIGNMENT_SCHEMA = 'veldo.team_assignment/v1'
KIND, ASSIGNMENT_KIND = 'team', 'team_assignment'
ID_PREFIX, ASSIGNMENT_PREFIX = 'team:', 'team-assignment:'
OPERATION = 'team_operation'
OWNER = 'VELDO-0089 team configuration'
WRITES = ('entities', 'journal', 'commands', 'nonces')
OPERATIONS = ('propose', 'amend', 'assign')
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
PM_ROLE = 'project_manager'
REQUIRED_ROLES = (PM_ROLE, 'elaboration', 'implementation', 'independent_review')
ROLE_FIELDS = ('workers', 'responsibilities', 'expertise', 'proposal_permissions', 'engines', 'budget', 'independence')
# The responsibility each required role must carry.
REQUIRED_RESPONSIBILITY = {PM_ROLE: 'coordinate', 'elaboration': 'elaborate', 'implementation': 'implement',
                           'independent_review': 'review'}
# The roles each role must be separate from (by principal and by independence group).
REQUIRED_SEPARATION = {'independent_review': ('implementation',)}
# What a role may PROPOSE. None of these is an authority: the owner or the authority decides each one.
PROPOSAL_KINDS = ('objective', 'feature', 'backlog_item', 'decision_request', 'finding', 'team_amendment')
# The engines a role may be eligible for: the registered subscription adapters (VELDO-0036).
ENGINES = tuple(sorted(RT.ADAPTERS))
WORKER_TYPES = ('agent_run', 'service')
OWNER_ROLE = PJ.OWNER_ROLE
# VELDO-0049's engineering-review policy record, as dispatch.py keeps it (review_policy_id).
REVIEW_POLICY_KIND, REVIEW_POLICY_PREFIX = 'review_policy', 'review-policy:'
# The settlement the owner's amendment comes through (VELDO-0068) and the target kind it names.
AMENDMENT_TOUCHPOINT, TARGET_KIND = 'decision_disposition', KIND
RULINGS = ('approve',)
REQUEST_KIND, SETTLEMENT_KIND, EFFECT_KIND = 'assignment', ST.SETTLEMENT_KIND, ST.EFFECT_KIND
# Every name that is an authority, never a proposal: the R37 roles (VELDO-0025) and the settlement
# touchpoints (VELDO-0068).
AUTHORITY_NAMES = frozenset(AC.ROLES) | frozenset(ST.JOURNEY)
STAFFING_SUBJECT = 'team_staffing'
STAFFING_CHOICES = ['staff_the_team', 'decline']
REQUEST_WINDOW = 7 * 86400
TAXONOMY = {'invalid_input': 'invalid_input', 'no_such_project': 'invalid_input', 'no_such_team': 'invalid_input',
            'roster_not_authority': 'invalid_input', 'incomplete_roster': 'invalid_input',
            'not_authorized': 'missing_authority', 'not_owner': 'missing_authority',
            'project_not_active': 'missing_authority', 'missing_authority': 'missing_authority',
            'not_staffed': 'missing_authority', 'reviewer_not_independent': 'missing_authority',
            'not_accepted': 'missing_authority', 'stale_subject': 'stale_subject', 'stale_version': 'stale_subject',
            'wrong_subject': 'stale_subject', 'missing_evidence': 'missing_evidence',
            'insufficient_reviews': 'missing_evidence', 'unavailable_service': 'unavailable_service'}
_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$')


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def team_id(name):
    return ID_PREFIX + name


def review_policy_id(repository):
    return REVIEW_POLICY_PREFIX + repository


def _is_str(v):
    return isinstance(v, str) and v.strip() != ''


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def assignment_id(unit, command_id):
    return ASSIGNMENT_PREFIX + hashlib.sha256(_canonical(['team_assignment', unit, command_id])).hexdigest()[:32]


def revision_digest(project, revision, base_revision, team):
    return _digest({'project': project, 'revision': revision, 'base_revision': base_revision, 'team': team})


def _text_list(value):
    return (isinstance(value, list) and bool(value) and all(_is_str(v) for v in value)
            and len(set(value)) == len(value))


def schema_problems(team):
    """Why `team` is not a team this schema describes, by name: the closed field set, each field's
    shape, and no proposal permission that names an authority."""
    if not isinstance(team, dict) or set(team) != {'roles'} or not isinstance(team.get('roles'), dict):
        return ['invalid_input:team']
    problems = []
    for role in sorted(team['roles'], key=str):
        spec = team['roles'][role]
        if role not in REQUIRED_ROLES:
            problems.append('invalid_input:role:%s' % role)
            continue
        if not isinstance(spec, dict):
            problems.append('invalid_input:role:%s' % role)
            continue
        problems += ['invalid_input:field:%s/%s' % (role, f) for f in sorted(spec, key=str) if f not in ROLE_FIELDS]
        problems += ['invalid_input:missing:%s/%s' % (role, f) for f in ROLE_FIELDS if f not in spec]
        workers = spec.get('workers')
        if 'workers' in spec and not (isinstance(workers, list) and all(_is_str(w) for w in workers)
                                      and len(set(workers)) == len(workers)):
            problems.append('invalid_input:workers:%s' % role)
        for f in ('responsibilities', 'expertise', 'engines'):
            if f in spec and not _text_list(spec[f]):
                problems.append('invalid_input:%s:%s' % (f, role))
        permissions = spec.get('proposal_permissions')
        if 'proposal_permissions' in spec:
            if not isinstance(permissions, list) or not all(_is_str(p) for p in permissions):
                problems.append('invalid_input:proposal_permissions:%s' % role)
            else:
                for p in permissions:
                    if p in AUTHORITY_NAMES:
                        problems.append('roster_not_authority:%s/%s' % (role, p))
                    elif p not in PROPOSAL_KINDS:
                        problems.append('invalid_input:proposal_permission:%s/%s' % (role, p))
        if 'budget' in spec and PJ.budget_problems(spec['budget']):
            problems.append('invalid_input:budget:%s' % role)
        independence = spec.get('independence')
        if 'independence' in spec and not (isinstance(independence, dict) and set(independence) == {'distinct_from'}
                                           and isinstance(independence['distinct_from'], list)
                                           and all(r in REQUIRED_ROLES and r != role
                                                   for r in independence['distinct_from'])):
            problems.append('invalid_input:independence:%s' % role)
    return problems


def staffing_problems(team, membership, project, now, active_member, scope_covers):
    """Why a well-formed `team` does not staff project `project` (a record read by control_project),
    by name: a missing or conflicting staffing, an unknown worker, a missing responsibility, an
    ineligible engine, a budget outside the project's coordination budget, a missing separation."""
    problems = []
    roles = team['roles']
    name = project.get('name')
    limits = project.get('coordination_budget') if isinstance(project.get('coordination_budget'), dict) else {}
    entries = {}
    for m in membership:
        if isinstance(m, dict):
            entries[m.get('principal')] = m
    for role in REQUIRED_ROLES:
        spec = roles.get(role)
        if not spec or not spec.get('workers'):
            problems.append('missing_staffing:%s' % role)
            continue
        if role == PM_ROLE and len(spec['workers']) != 1:
            problems.append('conflicting_staffing:%s' % role)
        for worker in spec['workers']:
            entry = entries.get(worker)
            if (not active_member(entry, now)[0] or entry.get('principal_type') not in WORKER_TYPES
                    or not scope_covers(entry.get('scope'), [name])):
                problems.append('unknown_worker:%s/%s' % (role, worker))
        if REQUIRED_RESPONSIBILITY[role] not in spec['responsibilities']:
            problems.append('missing_responsibility:%s' % role)
        problems += ['engine_ineligible:%s/%s' % (role, e) for e in spec['engines'] if e not in ENGINES]
        for unit in sorted(spec['budget']):
            cap = limits.get(unit)
            if not isinstance(cap, (int, float)) or isinstance(cap, bool) or spec['budget'][unit] > cap:
                problems.append('over_budget:%s/%s' % (role, unit))
    for role, others in REQUIRED_SEPARATION.items():
        spec = roles.get(role) or {}
        declared = (spec.get('independence') or {}).get('distinct_from') or []
        for other in others:
            if other not in declared:
                problems.append('missing_independence:%s/%s' % (role, other))
            mine, theirs = spec.get('workers') or [], (roles.get(other) or {}).get('workers') or []
            groups = {(entries.get(w) or {}).get('independence_group') or w for w in theirs}
            for worker in mine:
                if worker in theirs or ((entries.get(worker) or {}).get('independence_group') or worker) in groups:
                    problems.append('conflicting_staffing:%s/%s' % (role, worker))
    return problems


def amendment_target(record):
    """The settlement terms target that asks the owner to accept `record`'s pending proposal."""
    proposal = record['proposal']
    return {'kind': TARGET_KIND, 'ref': team_id(record['project']), 'revision': proposal['revision'],
            'base_revision': proposal['base_revision'], 'digest': proposal['digest']}


def amendment_brief(record):
    """Exactly what the owner is shown: every role of the pending proposal and what it binds."""
    proposal = record['proposal']
    lines = ['Accept team revision %d of project %s (amends revision %d).'
             % (proposal['revision'], record['project'], proposal['base_revision'])]
    for role in REQUIRED_ROLES:
        spec = proposal['team']['roles'][role]
        lines.append('%s: %s; engines %s; budget %s; may propose %s; separate from %s.' % (
            role, ', '.join(spec['workers']), ', '.join(spec['engines']),
            ', '.join('%s %s' % (u, spec['budget'][u]) for u in sorted(spec['budget'])),
            ', '.join(spec['proposal_permissions']) or 'nothing',
            ', '.join(spec['independence']['distinct_from']) or 'no role'))
    lines.append('The roster grants no authority. Tools and MCP servers come from the capability configuration.')
    return '\n'.join(lines)


def staffing_brief(project, problems):
    return ('The team proposed for project %s cannot be staffed as written, so no team was recorded and no '
            'worker was added. Staff it or decline it.\nProblems: %s' % (project, '; '.join(problems)))


def read(store, conn, name):
    """The team record of project `name` on any connection (another process's read-only one
    included), or None."""
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (team_id(name),)).fetchone()
    if row is None or row[0] != KIND:
        return None
    return dict(json.loads(row[2]), version=row[1])


def assignments(conn, unit=None):
    """Every team assignment (of `unit` when named), on any connection."""
    rows = conn.execute('SELECT id, version, data FROM entities WHERE kind=? ORDER BY id', (ASSIGNMENT_KIND,))
    found = [dict(json.loads(data), id=eid, version=version) for eid, version, data in rows]
    return [a for a in found if unit is None or a.get('unit') == unit]


def _row(conn, identity):
    if not _is_str(identity):
        return None
    row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}


class Refused(Exception):
    def __init__(self, code, detail='', problems=(), owner_request=None):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail, self.problems, self.owner_request = code, detail, list(problems), owner_request


class Teams:
    """One repository's team service on the configured real store connection.

    `store` and `membership` are the control_store and control_membership modules; `sign(bytes)`
    signs journal records as `journal_signer`. `inbox` is the VELDO-0064 Inbox (and `assignment` its
    module) the owner requests are opened in, as `requester` (an enrolled service) whose commands
    `request_sign(bytes)` signs."""

    def __init__(self, store, membership, conn, coordinates, journal_signer, sign, *, inbox, assignment, requester,
                 request_sign, authority_generation=1, clock=time.time):
        if set(coordinates) != set(COORDINATES) or not all(_is_str(v) for v in coordinates.values()):
            raise Refused('invalid_input', 'coordinates are domain, repository and store identities')
        if inbox is None or not _is_str(requester) or not callable(request_sign):
            raise Refused('invalid_input', 'the owner-request inbox and its requester are required')
        self.store, self.membership, self.AC = store, membership, membership.AC
        self.conn, self.ids = conn, dict(coordinates)
        self.journal_signer, self.sign, self.authority_generation, self.clock = journal_signer, sign, authority_generation, clock
        self.inbox, self.assignment, self.requester, self.request_sign = inbox, assignment, requester, request_sign
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}
        conn.command_registry[OPERATION] = {'transaction_transition': self._in_transaction, 'writes': WRITES}
        store.declare_owners(conn, OWNER, kinds={KIND: (OPERATION,), ASSIGNMENT_KIND: (OPERATION,)},
                             prefixes={ID_PREFIX: (OPERATION,), ASSIGNMENT_PREFIX: (OPERATION,)}, module=__file__)

    # Commands.

    def apply(self, packet):
        command = packet.get('command') if isinstance(packet, dict) else None
        command = command if isinstance(command, dict) else {}
        observation = dict(self.ids, schema=SCHEMA, operation=command.get('operation'), project=None, unit=None,
                           command_id=command.get('command_id'), accepted_versions={})
        try:
            result = self._apply(packet, command, observation)
        except Refused as exc:
            result = {'ok': False, 'reason': exc.code, 'problems': exc.problems, 'owner_request': exc.owner_request}
        except self.store.StoreRefused as exc:
            result = {'ok': False, 'reason': exc.code, 'problems': [], 'owner_request': None}
        except sqlite3.Error:
            result = {'ok': False, 'reason': 'unavailable_service', 'problems': [], 'owner_request': None}
        observation.update(outcome='accepted' if result['ok'] else 'refused',
                           refusal=None if result['ok'] else result['reason'],
                           taxonomy=None if result['ok'] else taxonomy(result['reason']),
                           owner_request=result.get('owner_request'))
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
            raise Refused('invalid_input', 'invalid team command or authority coordinates')
        op, principal, name = command['operation'], command['principal'], command['project']
        tid = team_id(name)
        observation['project'] = PJ.project_id(name)
        state = self.membership.authority_state(self.store, self.conn)
        now = self.clock()
        key = self.AC.active_key(state['keyring'], principal, now)
        if not key:
            raise Refused('not_authorized', 'no active verification key')
        verified, _ = self.AC.ssh_keygen_verify(self.store.canonical_bytes(command), packet['signature'],
                                                self.AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise Refused('not_authorized', 'command signature did not verify')
        entry = self.AC.membership_entry(state['membership'], principal)
        active, why = self.AC.active_member(entry, now)
        if not active:
            raise Refused('not_authorized:' + str(why))
        if (entry.get('principal_type') not in self.AC.BOUNDARIES['proposal_commit']
                or not self.membership.scope_covers(entry.get('scope'), [name])):
            raise Refused('not_authorized:scope', 'the principal does not act in this project')
        entities = state['entities']
        project = entities.get(PJ.project_id(name))
        if project is None or project.get('kind') != PJ.KIND or not isinstance(project.get('data'), dict):
            raise Refused('no_such_project', name)
        if project['data'].get('state') != 'ACTIVE':
            raise Refused('project_not_active:%s' % project['data'].get('state'))
        current = entities.get(tid)
        record = dict(current['data'], version=current['version']) if current and current.get('kind') == KIND else None
        if command.get('team_version') != (record or {}).get('version', 0):
            raise Refused('stale_subject:version', 'the command names another team version')
        pinned = [tid, PJ.project_id(name), principal, key['key_id'], self.membership.VERSIONS_ENTITY]
        params = dict(action=op, team_id=tid, project=name, principal=principal, command_id=command['command_id'],
                      at=now)
        if op == 'propose':
            self._propose(command, state, project['data'], record, params, pinned, now)
        elif op == 'amend':
            self._amend(command, state, project['data'], record, params, pinned, now)
        else:
            observation['unit'] = command.get('unit')
            self._assign(command, state, project['data'], record, params, pinned, now, principal)
        versions = {eid: entities.get(eid, {}).get('version', 0) for eid in dict.fromkeys(pinned)}
        observation['accepted_versions'] = versions
        stored = dict(command_id=command['command_id'], principal=principal, operation=OPERATION, parameters=params,
                      expected_versions=versions, artifact_digests=[], nonce=command['nonce'])
        receipt = self.store.execute(self.conn, stored, self.journal_signer, self.sign, self.authority_generation)
        result = {'ok': True, 'reason': op, 'team_id': tid, 'team': read(self.store, self.conn, name),
                  'receipt': receipt, 'problems': [], 'owner_request': None}
        if op == 'assign':
            result['assignment'] = (_row(self.conn, params['assignment_id']) or {}).get('data')
        return result

    def _staffed(self, team, state, project, now):
        """The team's staffing problems over the current membership, and the rows they read."""
        problems = staffing_problems(team, state['membership'], project, now, self.AC.active_member,
                                     self.membership.scope_covers)
        workers = sorted({w for spec in team['roles'].values() for w in spec.get('workers') or []})
        return problems, workers

    def _propose(self, command, state, project, record, params, pinned, now):
        team = command.get('team')
        problems = schema_problems(team)
        if problems:
            raise Refused(problems[0], '; '.join(problems), problems)
        staffing, workers = self._staffed(team, state, project, now)
        if staffing:
            raise Refused('incomplete_roster:' + staffing[0], '; '.join(staffing), staffing,
                          self._owner_request(project, team, staffing, now))
        revision = (record or {}).get('revision', 0) + 1
        base = (record or {}).get('revision', 0)
        params['proposal'] = {'revision': revision, 'base_revision': base, 'team': copy.deepcopy(team),
                              'digest': revision_digest(project['name'], revision, base, team),
                              'proposed_by': params['principal'], 'command_id': params['command_id'], 'at': now}
        pinned += workers

    def _owner_problems(self, state, owner, name, now):
        entry = self.AC.membership_entry(state['membership'], owner)
        active, why = self.AC.active_member(entry, now)
        if not active:
            return ['not_owner:' + str(why)]
        if entry.get('principal_type') != 'person' or OWNER_ROLE not in (entry.get('roles') or []):
            return ['not_owner:role']
        if not self.membership.scope_covers(entry.get('scope'), [name]):
            return ['not_owner:scope']
        return []

    def _amend(self, command, state, project, record, params, pinned, now):
        if record is None or not isinstance(record.get('proposal'), dict):
            raise Refused('no_such_team', 'no proposal is pending')
        proposal = record['proposal']
        if command.get('revision') != proposal['revision'] or command.get('digest') != proposal['digest']:
            raise Refused('stale_subject:proposal', 'the command names another proposal than the pending one')
        request = _row(self.conn, command.get('request'))
        req = request['data'] if request is not None and request['kind'] == REQUEST_KIND else {}
        reference = req.get('settlement') if isinstance(req.get('settlement'), dict) else {}
        settlement, effect = _row(self.conn, reference.get('settlement_id')), _row(self.conn, reference.get('effect_id'))
        if (req.get('state') != 'SATISFIED' or settlement is None or settlement['kind'] != SETTLEMENT_KIND
                or effect is None or effect['kind'] != EFFECT_KIND
                or effect['data'].get('settlement_id') != settlement['data'].get('settlement_id')
                or settlement['data'].get('request_id') != command.get('request')):
            raise Refused('missing_evidence:settlement', 'the request is not settled')
        target = effect['data'].get('target') or {}
        if (settlement['data'].get('touchpoint') != AMENDMENT_TOUCHPOINT or target.get('kind') != TARGET_KIND
                or target.get('ref') != params['team_id']):
            raise Refused('invalid_input:request', 'the settled request does not ask to amend this team')
        if target != amendment_target(record):
            raise Refused('stale_subject:revision', 'the answer settled another proposal of the team')
        if req.get('brief') != amendment_brief(record):
            raise Refused('stale_subject:brief', 'the owner was shown something other than this proposal')
        owner = project.get('owner')
        problems = self._owner_problems(state, owner, project['name'], now)
        if problems:
            raise Refused(problems[0], '; '.join(problems))
        if req.get('owner') != owner or settlement['data'].get('principals') != [owner]:
            raise Refused('not_owner', 'only the project\'s owner amends its team')
        ruling = settlement['data'].get('ruling')
        if ruling not in RULINGS:
            raise Refused('not_accepted:%s' % ruling, 'the owner did not accept the proposal')
        staffing, workers = self._staffed(proposal['team'], state, project, now)
        if staffing:
            raise Refused('incomplete_roster:' + staffing[0], '; '.join(staffing), staffing,
                          self._owner_request(project, proposal['team'], staffing, now))
        params['acceptance'] = {'request_id': command['request'], 'request_version': reference.get('request_version'),
                                'settlement_id': reference['settlement_id'], 'effect_id': reference['effect_id'],
                                'ruling': ruling, 'principals': [owner]}
        pinned += [command['request'], reference['settlement_id'], reference['effect_id'], owner] + workers

    def _assign(self, command, state, project, record, params, pinned, now, principal):
        if record is None or not record.get('revision'):
            raise Refused('no_such_team', 'the project has no accepted team')
        team = record['team']
        pm = team['roles'][PM_ROLE]['workers']
        if principal not in pm and principal != project.get('owner'):
            raise Refused('not_authorized:not_manager', 'the team\'s project manager or the owner assigns work')
        if command.get('team_revision') != record['revision']:
            raise Refused('stale_subject:team_revision', 'the assignment names another team revision')
        unit_id = command.get('unit')
        unit = state['entities'].get(unit_id) if _is_str(unit_id) else None
        if unit is None or unit.get('kind') != 'execution_unit' or (unit.get('data') or {}).get('project') != project['name']:
            raise Refused('invalid_input:unit', 'the unit is not an execution unit of this project')
        data = unit['data']
        subject = {'unit': unit_id, 'revision': data.get('revision'), 'scope_digest': data.get('scope_digest')}
        policy_row = state['entities'].get(review_policy_id(self.ids['repository_uuid']))
        tiers = ((policy_row.get('data') or {}).get('tiers') or {}) if (policy_row or {}).get('kind') == REVIEW_POLICY_KIND else {}
        need = tiers.get(data.get('risk')) if _is_str(data.get('risk')) else None
        if not isinstance(need, int) or isinstance(need, bool) or need < 1:
            raise Refused('missing_authority:review_policy', 'no accepted review count for risk %r' % data.get('risk'))
        builder = command.get('builder')
        reviewers = command.get('reviewers')
        if not _is_str(builder) or not isinstance(reviewers, list) or not all(
                isinstance(r, dict) and set(r) == {'reviewer', 'subject'} and _is_str(r['reviewer']) for r in reviewers):
            raise Refused('invalid_input:positions', 'one builder and a list of reviewer positions')
        entries = {m.get('principal'): m for m in state['membership'] if isinstance(m, dict)}
        problems, staffed = [], []
        if builder not in team['roles']['implementation']['workers']:
            staffed.append('not_staffed:implementation/%s' % builder)
        group = (entries.get(builder) or {}).get('independence_group') or builder
        seen = set()
        for position in reviewers:
            who = position['reviewer']
            if who not in team['roles']['independent_review']['workers']:
                staffed.append('not_staffed:independent_review/%s' % who)
            mine = (entries.get(who) or {}).get('independence_group') or who
            if who == builder or mine == group or who in seen:
                problems.append('reviewer_not_independent:%s' % who)
            seen.add(who)
        problems += staffed
        for position in [{'reviewer': 'builder', 'subject': command.get('subject')}] + reviewers:
            if position['subject'] != subject:
                problems.append('wrong_subject:%s' % position['reviewer'])
        for who in [builder] + sorted(seen):
            entry = entries.get(who)
            if not self.AC.active_member(entry, now)[0] or not self.membership.scope_covers(
                    (entry or {}).get('scope'), [project['name']]):
                problems.append('not_staffed:member/%s' % who)
        if len(seen) < need:
            problems.append('insufficient_reviews:%d/%d' % (len(seen), need))
        if problems:
            raise Refused(problems[0], '; '.join(problems), problems)
        aid = assignment_id(unit_id, params['command_id'])
        params['assignment_id'] = aid
        params['assignment'] = {
            'schema': ASSIGNMENT_SCHEMA, 'project': project['name'], 'unit': unit_id, 'subject': subject,
            'team': {'revision': record['revision'], 'digest': record['digest'], 'version': record['version']},
            'policy': {'id': review_policy_id(self.ids['repository_uuid']), 'version': policy_row['version'],
                       'risk': data['risk'], 'required_reviews': need},
            'builder': builder, 'reviewers': [p['reviewer'] for p in reviewers], 'assigned_by': principal,
            'at': now}
        pinned += [aid, unit_id, review_policy_id(self.ids['repository_uuid']), builder] + sorted(seen)

    def _owner_request(self, project, team, problems, now):
        """Open (or find) the owner request that names the staffing problems; its id, or None."""
        name = project['name']
        subject_digest = _digest({'team': team, 'problems': problems})
        alias = 'team-staffing-' + subject_digest.split(':', 1)[1][:24]
        aid = self.assignment.assignment_id(self.ids['repository_uuid'], alias)
        body = dict(self.ids, operation='open', alias=alias, principal=self.requester,
                    command_id='team-request-' + subject_digest.split(':', 1)[1][:32],
                    nonce='team-request-nonce-' + subject_digest.split(':', 1)[1][:32], assignment=dict(
                        kind='decision', owner=project.get('owner'), scope=[name],
                        deadline=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now + REQUEST_WINDOW)),
                        budget={'owner_minutes': 10}, brief=staffing_brief(name, problems),
                        choices=list(STAFFING_CHOICES),
                        subject={'kind': STAFFING_SUBJECT, 'ref': team_id(name), 'digest': subject_digest}))
        try:
            self.inbox.apply({'command': body, 'signature': self.request_sign(self.store.canonical_bytes(body))})
        except Exception:  # noqa: BLE001 - the refusal stands; a request that did not open is reported as None
            return None
        # Opened now, or opened by an earlier proposal of exactly this team with exactly these problems.
        row = _row(self.conn, aid)
        if row and row['kind'] == REQUEST_KIND and (row['data'].get('subject') or {}).get('digest') == subject_digest:
            return aid
        return None

    # The transaction.

    def _in_transaction(self, conn, params, before):
        """Inside the store's write transaction: the team row is read here, so what the command decided
        on is what it commits over (every other input's version is pinned by the command)."""
        tid, op, now = params['team_id'], params['action'], params['at']
        current = before.get(tid)
        entry = {'by': params['principal'], 'at': now, 'command_id': params['command_id'], 'operation': op}
        if op == 'assign':
            aid = params['assignment_id']
            if aid in before:
                raise Refused('stale_subject', 'the assignment exists')
            return {aid: {'kind': ASSIGNMENT_KIND, 'data': dict(params['assignment'])}}
        if current is None:
            data = dict(schema=SCHEMA, project=params['project'], domain_uuid=self.ids['domain_uuid'],
                        repository_uuid=self.ids['repository_uuid'], revision=0, team=None, digest=None,
                        revisions=[], proposal=None, history=[])
        elif current.get('kind') != KIND:
            raise Refused('no_such_team', tid)
        else:
            data = json.loads(json.dumps(current['data']))
        if op == 'propose':
            data['proposal'] = params['proposal']
            data['history'] = list(data['history']) + [dict(entry, revision=params['proposal']['revision'],
                                                            digest=params['proposal']['digest'])]
            return {tid: {'kind': KIND, 'data': data}}
        proposal = data.get('proposal') or {}
        accepted = {'revision': proposal['revision'], 'base_revision': proposal['base_revision'],
                    'digest': proposal['digest'], 'team': proposal['team'], 'proposed_by': proposal['proposed_by'],
                    'accepted_at': now, **params['acceptance']}
        data['revisions'] = list(data['revisions']) + [accepted]
        data.update(revision=proposal['revision'], team=proposal['team'], digest=proposal['digest'], proposal=None)
        data['history'] = list(data['history']) + [dict(entry, revision=proposal['revision'], digest=proposal['digest'],
                                                        request_id=params['acceptance']['request_id'])]
        return {tid: {'kind': KIND, 'data': data}}

    # Reads.

    def metrics(self):
        """Accepted and refused commands, and the pending work: proposals awaiting the owner's
        answer and staffing requests still open in the inbox."""
        teams = [json.loads(d) for (d,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,))]
        pending_requests = 0
        for (d,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (REQUEST_KIND,)):
            data = json.loads(d)
            if (data.get('subject') or {}).get('kind') == STAFFING_SUBJECT and data.get('state') in (
                    'OFFERED', 'ACCEPTED', 'IN_PROGRESS'):
                pending_requests += 1
        return dict(self.counts, teams=len(teams), pending_proposals=sum(1 for t in teams if t.get('proposal')),
                    pending_staffing_requests=pending_requests,
                    assignments=self.conn.execute('SELECT COUNT(*) FROM entities WHERE kind=?',
                                                  (ASSIGNMENT_KIND,)).fetchone()[0])
