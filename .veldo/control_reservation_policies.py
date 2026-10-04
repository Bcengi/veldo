"""Reservation policies provisioned from the owner's configuration (VELDO-0204).

VELDO-0036 refuses a reservation missing_ceiling:<scope> unless the account, the project and the unit each
have a policy. This module derives every such policy from what the owner already controls and writes it
through the one writer, control_reservations.Reservations.configure, unchanged:

  project   its signed coordination budget (control_project, VELDO-0076), each VELDO-0036 kind it states;
            owner_minutes is no reservation kind and is left out.
  account   for every account record (control_accounts, VELDO-0062): capacity, invocations and wall_seconds,
            each the sum of that kind over every project record's coordination budget.
  unit      for every execution_unit record: the sum, kind by kind, of the budgets of the two roles that
            dispatch it, its build role (its team assignment's role, implementation when it has none) and
            independent_review, in its project's team at its current revision (control_team, VELDO-0089),
            or in the default team at its head revision when the project has none (VELDO-0162). A unit
            with no such source is refused missing_evidence:reservation_source:unit:<unit>, never given a
            default. A pm_cycle unit is no execution_unit: the PM cycle keeps writing its own policy.

A stored policy whose caps equal the derived caps is left alone and sends no command; its windows are not
compared, and configure keeps them. A policy with no source record is left as it is: nothing deletes one.
Each subject is reconciled on its own, so one refusal changes no other subject's outcome.

THE LOCK (VELDO-0171): only the holder of the store's lock writes. `Provisioning.run` refuses first, writing
nothing, unless control_api_authority.authority_problem finds the caller's descriptor holds authority.lock
beside the store its connection opened, and the Reservations it writes through is on that connection
(missing_authority:not_the_authority). Offline, the lock holder (setup) calls it on its own connection;
online, control_service's FactoryLoop calls it on the service's connection with the lock serve holds.
"""
import importlib.util
import json
from pathlib import Path
import time
from types import SimpleNamespace


def organ(name):
    spec = importlib.util.spec_from_file_location('reservation_policies_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUTH = organ('control_api_authority')
RES = organ('control_reservations')
TR = organ('control_team_routes')
CT = TR.CT
PJ = CT.PJ
ACC = RES.ACC
TA = CT.TA
SCHEMA = 'veldo.reservation_provisioning/v1'
ACCOUNT_KINDS = ('capacity', 'invocations', 'wall_seconds')
BUILD_ROLE, REVIEW_ROLE = 'implementation', 'independent_review'
NOT_THE_AUTHORITY = 'missing_authority:not_the_authority'


def writer(store, conn, *, domain, repository, principal, sign, generation=1, observe=lambda event: None):
    """The Reservations a line of control_service builds: this store's domain, a served repository, the service
    principal signing its own journal records, and the production authorization (service_authority)."""
    return RES.Reservations(store, conn, domain=domain, repository=repository, principal=principal,
                            authorize=RES.service_authority, signer=principal, sign=sign, generation=generation,
                            observe=observe)


def _kind(conn, kind):
    return [(eid, json.loads(data)) for eid, data in conn.execute(
        'SELECT id, data FROM entities WHERE kind=? ORDER BY id', (kind,))]


def _policy(conn, domain, scope, subject):
    """The stored policy of one subject, read by its policy entity id: (version, record) or (0, None)."""
    row = conn.execute('SELECT version, data FROM entities WHERE id=?',
                       (RES.entity('policy', [domain, scope, subject]),)).fetchone()
    return (row[0], json.loads(row[1])) if row else (0, None)


def _budget(record):
    budget = record.get('coordination_budget')
    return budget if isinstance(budget, dict) else {}


def _team(conn, project):
    """The team a unit of `project` takes its roles from, with where it came from, or (None, None)."""
    record = CT.read(None, conn, project)
    if record is not None and isinstance(record.get('team'), dict) and record.get('revision'):
        return record['team'], dict(team='team:' + project, revision=record['revision'])
    head = CT._row(conn, TR.HEAD)
    revision = (head or {}).get('data', {}).get('revision') if head and head['kind'] == 'default_team_head' else None
    if not revision:
        return None, None
    try:
        default = TR.TeamRoutes.read_default(SimpleNamespace(conn=conn), revision)
    except CT.Refused:
        return None, None
    return default['team'], dict(team=TR.default_id(revision), revision=revision)


def unit_source(conn, unit, record):
    """(caps, source) for one execution unit, or (None, source) when it has no source."""
    project = record.get('project')
    source = dict(project=project)
    if not isinstance(project, str) or PJ.read(None, conn, project) is None:
        return None, source
    team, found = _team(conn, project)
    if team is None:
        return None, source
    assignment = TA.assigned(conn, unit)
    build = (assignment or {}).get('role') or BUILD_ROLE
    source.update(found, roles=[build, REVIEW_ROLE])
    roles = team.get('roles') if isinstance(team.get('roles'), dict) else {}
    budgets = [(roles.get(role) or {}).get('budget') for role in (build, REVIEW_ROLE)]
    if not all(isinstance(budget, dict) and budget for budget in budgets):
        return None, source
    caps = {kind: budgets[0][kind] + budgets[1][kind] for kind in RES.KINDS
            if kind in budgets[0] and kind in budgets[1]}
    return caps, source


def derive(conn):
    """Every subject this store's records name: [(scope, subject, caps or None, source)]."""
    projects = _kind(conn, PJ.KIND)
    subjects = []
    for _eid, record in projects:
        budget = _budget(record)
        subjects.append(('project', record.get('name'), {k: budget[k] for k in RES.KINDS if k in budget},
                         dict(project=record.get('name'))))
    sums = {kind: sum(_budget(record).get(kind, 0) for _eid, record in projects) for kind in ACCOUNT_KINDS}
    names = sorted(str(record.get('name')) for _eid, record in projects)
    for _eid, record in _kind(conn, ACC.KIND):
        subjects.append(('account', record.get('id'), dict(sums), dict(projects=names)))
    for eid, record in _kind(conn, 'execution_unit'):
        caps, source = unit_source(conn, eid, record)
        subjects.append(('unit', eid, caps, source))
    return subjects


def _code(error):
    code = getattr(error, 'code', None)
    return code if isinstance(code, str) and code else 'unknown_outcome:' + type(error).__name__


class Provisioning:
    """One provisioning service: `run` reconciles every subject; `metrics` counts what the runs did."""

    def __init__(self, observe=None, clock=time.time):
        self.observe, self.clock = observe or (lambda event: None), clock
        self.counts = dict(passes={}, subjects={}, refusals={})

    def _count(self, group, key):
        self.counts[group][key] = self.counts[group].get(key, 0) + 1

    def metrics(self):
        return json.loads(json.dumps(self.counts))

    def run(self, conn, lock, reservations, *, caller):
        answer = dict(schema=SCHEMA, caller=caller, at=self.clock(), outcome='refused', refusal=None, taxonomy=None,
                      subjects=[])
        problem = AUTH.authority_problem(lock, conn)
        if problem is None and getattr(reservations, 'conn', None) is not conn:
            problem = NOT_THE_AUTHORITY
        if problem:
            answer.update(refusal=problem, taxonomy=problem.split(':', 1)[0])
        else:
            for scope, subject, caps, source in derive(conn):
                answer['subjects'].append(self._reconcile(conn, reservations, scope, subject, caps, source))
            answer['outcome'] = 'done'
        for entry in answer['subjects']:
            self._count('subjects', entry['scope'] + ':' + entry['outcome'])
            if entry['outcome'] == 'refused':
                self._count('refusals', entry['refusal'])
        if answer['refusal']:
            self._count('refusals', answer['refusal'])
        self._count('passes', caller.split(':', 1)[0] + ':' + answer['outcome'])
        self.observe(dict(answer, kind='reservation_provisioning', operation='provision'))
        return answer

    def _reconcile(self, conn, reservations, scope, subject, caps, source):
        entry = dict(scope=scope, subject=subject, source=source, caps=caps)
        if caps is None:
            refusal = 'missing_evidence:reservation_source:unit:' + subject
            return dict(entry, outcome='refused', refusal=refusal, taxonomy='missing_evidence')
        version, stored = _policy(conn, reservations.domain, scope, subject)
        if stored is not None and stored.get('caps') == caps:
            return dict(entry, outcome='unchanged', version=version)
        command_id = 'reservation-policy/%s/%s/%d' % (scope, subject, version)
        try:
            result = reservations.configure(command_id, scope, subject, dict(caps), now=self.clock())
        except Exception as error:  # noqa: BLE001 - the writer's own refusal, by its own name, for this subject
            refusal = _code(error)
            return dict(entry, outcome='refused', refusal=refusal, taxonomy=refusal.split(':', 1)[0],
                        command_id=command_id)
        return dict(entry, outcome='configured', command_id=command_id, seq=result.get('seq'),
                    version=_policy(conn, reservations.domain, scope, subject)[0])


def provision(conn, lock, reservations, *, caller, observe=None):
    return Provisioning(observe).run(conn, lock, reservations, caller=caller)
