#!/usr/bin/env python3
"""The land station: every land of a unit is its own land dispatch, and a land refused because another
factory moved the trunk is followed by a new one (PLAN-0019 W108, VELDO-0148).

WHAT THIS MODULE IS. The factory loop's land station (control_service's Line, VELDO-0154) and anyone else
who lands a unit through the factory land it here. LandStation.land runs ONE land dispatch of one unit:

  1. it opens the dispatch's record (kind `land_dispatch`, id `land:<dispatch id>`) in the store, under a
     new dispatch identity (`dispatch/<unit>/land-<attempt>-<hex>`), naming the land dispatch it follows
     when it is a re-land, the evidence commit it lands, and the claim holder and generation;
  2. it runs the serialized land (lander.py) exactly as a factory land runs: a disposable candidate built
     on a watermark fetched now from the trunk (VELDO-0056), the unit's implementation and evidence merged
     onto it, the gate of the trusted installation run on it (VELDO-0058), the authority's CandidatePolicy,
     and the exact-tip compare-and-swap through the protected effect executor with the confirmed-landing
     receipt (control_landing, VELDO-0057). Nothing is ever forced: the swap is leased on the watermark;
  3. it ends the record with its outcome, the new watermark, the candidate, its gate observation, its
     publication effect and receipt, and the named refusal:

       landed             the compare-and-swap landed and its receipt is committed;
       trunk_moved        the publication was refused because another push moved the trunk: at the listing
                          (`stale-subject`) or between the listing and the push (`trunk-moved`); the
                          watermark, the tip found and the classification are recorded;
       conflict           the re-merge onto the watermark conflicted (a real conflict, or an append-only
                          union that is not safe); nothing was published;
       awaiting_approval  every refusal of the publication's subject is a prior grant with a mismatched binding;
                          the exact subject a fresh grant would be bound to is recorded; nothing moved;
       unknown            the outcome cannot be established (an unknown publication): a named stop;
       failed             any other refusal.

WHAT FOLLOWS A LAND (the loop's next-station rule, control_service Line.after_land). A land that ended
trunk_moved is followed by exactly one new land dispatch (a re-land): a new watermark from the new trunk,
the same re-merge, the gate again on the new candidate and a new compare-and-swap. A clean re-merge keeps
the review, which is bound to the unchanged evidence commit. A conflict sends the unit back to its builder
as a new build dispatch told to merge the new trunk, and that build is reviewed again. awaiting_approval
asks the project's owner once for a fresh grant bound to the re-merged tree (the old grant, bound to
another tree, never publishes it); his grant is recorded by `grant` and the next land dispatch publishes.
A mixed refusal stays failed without a subject or an owner question.
landed and unknown are followed by nothing. The original dispatch is never attempted again: its
publication's recorded answer is final (VELDO-0057 AC3), and every re-land is a new identity.

THE RECORDS. `transition` is the one store transition of a land dispatch, `open` and `end`, committed on the
caller's connection: its principal must be an active service member for the repository; one land of a unit
runs at a time (the unit's index, kind `land_dispatch_unit`, names its latest land dispatch, its state and
its attempts); a dispatch that follows another must follow the unit's latest one, and only one that ended
trunk_moved or awaiting_approval. So each refused land is followed by at most one re-land.

WHAT IT IS NOT. No bound or backoff for a trunk that keeps moving (hardening), no recovery of a land whose
process died mid-run (its record stays running, a stop), no recovery of an unknown publication (Release 2).
Standard library only. The store connection, coordinates, the land configuration (the work configuration's
`land` entry, config_problem) and the journal signer are arguments; nothing is routed from the current
directory.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time


def _sibling(name):
    spec = importlib.util.spec_from_file_location('veldo_land_station_' + name,
                                                  Path(__file__).resolve().with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CM = _sibling('control_membership')
AC = CM.AC
LD = _sibling('lander')
LG = _sibling('control_landing')

SCHEMA = 'veldo.land_dispatch/v1'
KIND = 'land_dispatch'
UNIT_KIND = 'land_dispatch_unit'
OPERATION = 'land_dispatch_transition'
WRITES = ('entities', 'journal', 'commands', 'nonces')
STATION = 'land'
RUNNING, LANDED, TRUNK_MOVED, CONFLICT, AWAITING, UNKNOWN, FAILED = (
    'running', 'landed', 'trunk_moved', 'conflict', 'awaiting_approval', 'unknown', 'failed')
ENDS = (LANDED, TRUNK_MOVED, CONFLICT, AWAITING, UNKNOWN, FAILED)
# The ends a new land dispatch of the unit follows: the re-land, and the land after a fresh grant.
FOLLOWED = (TRUNK_MOVED, AWAITING)
# The candidate's refusals that are a conflict the build must resolve (lander.GitLandOps._merge).
CONFLICTS = ('conflict:', 'union_unsafe:')
# The floor record the CandidatePolicy and the Landing read (dispatch.FLOOR_KIND and dispatch.floor_id).
FLOOR_KIND = 'floor_unit'
# The work configuration's `land` entry: required text fields, the lander's commit identity, optional paths.
REQUIRED = ('repository', 'trunk', 'remote', 'effects', 'target', 'principal', 'connection_key', 'events_root',
            'claims')
OPTIONAL = ('installation', 'observations', 'workspace_root')
TAXONOMY = ('invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service', 'missing_evidence',
            'unknown_outcome')


class Refused(Exception):
    """A named refusal: `code` (its class is taxonomy(code)) and a detail without secrets."""

    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def taxonomy(code):
    head = str(code).split(':', 1)[0]
    return head if head in TAXONOMY else LD.taxonomy(code)


def _text(value):
    return isinstance(value, str) and value.strip() != ''


def _digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                                 ensure_ascii=True).encode()).hexdigest()


def record_id(dispatch_id):
    return 'land:' + dispatch_id


def unit_index_id(domain, repository, unit):
    return 'land-unit:' + json.dumps([domain, repository, unit], separators=(',', ':'))


def floor_id(repository, unit):
    return 'floor:' + json.dumps([repository, unit], separators=(',', ':'))


def config_problem(land):
    """Why a work configuration's `land` entry cannot run a land, or None: exactly the REQUIRED text fields,
    the lander's commit identity [name, email] and any OPTIONAL paths."""
    if not isinstance(land, dict) or not set(REQUIRED) | {'identity'} <= set(land) \
            or not set(land) <= set(REQUIRED) | set(OPTIONAL) | {'identity'}:
        return 'fields'
    if not all(_text(land[k]) for k in REQUIRED) or not all(_text(land[k]) for k in OPTIONAL if k in land):
        return 'text'
    identity = land['identity']
    if not isinstance(identity, list) or len(identity) != 2 or not all(_text(v) for v in identity):
        return 'identity'
    return None


def _entity(conn, identity):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None


def _authorize(conn, principal, repository, now):
    """The writer is an active service member for this repository, read inside the transaction."""
    row = _entity(conn, principal) if _text(principal) else None
    entry = dict(row['data'], principal=principal) if row and row['kind'] == 'membership' else None
    active, why = AC.active_member(entry, now)
    if (not active or entry.get('principal_type') not in AC.BOUNDARIES['dispatch_acceptance']
            or not CM.scope_covers(entry.get('scope'), repository)):
        raise Refused('missing_authority:land_dispatch', why or 'not an active service member for this repository')


def transition(conn, params, before):
    """THE ONE TRANSITION of a land dispatch, `open` or `end`, inside its store transaction."""
    action, now = params.get('action'), params.get('now')
    domain, repository, unit, dispatch = (params.get(k) for k in ('domain', 'repository', 'unit', 'dispatch_id'))
    if (action not in ('open', 'end') or isinstance(now, bool) or not isinstance(now, (int, float))
            or not math.isfinite(now) or not all(_text(v) for v in (domain, repository, unit, dispatch))):
        raise Refused('invalid_input:land_dispatch', 'an action, a time, the coordinates, the unit and the dispatch')
    _authorize(conn, params.get('principal'), repository, now)
    rid, xid = record_id(dispatch), unit_index_id(domain, repository, unit)
    record = (before.get(rid) or {}).get('data')
    index = dict((before.get(xid) or {}).get('data') or {})
    if action == 'open':
        target = _entity(conn, unit)
        if (not target or target['kind'] != 'execution_unit'
                or (target['data'] or {}).get('repository_uuid') != repository):
            raise Refused('missing_authority:unit', unit)
        if record is not None:
            raise Refused('stale_subject:land_dispatch/exists', dispatch)
        if index.get('state') == RUNNING:
            raise Refused('stale_subject:land_dispatch/running', str(index.get('latest')))
        follows = params.get('follows')
        if follows is not None and (follows != index.get('latest') or index.get('state') not in FOLLOWED):
            raise Refused('stale_subject:land_dispatch/follows', '%s is not the unit\'s latest land to follow' % follows)
        attempt = int(index.get('attempts') or 0) + 1
        opened = params.get('record') or {}
        if not _text(opened.get('evidence')):
            raise Refused('invalid_input:land_dispatch/evidence')
        record = dict(opened, schema=SCHEMA, dispatch_id=dispatch, domain=domain, repository=repository, unit=unit,
                      station=STATION, attempt=attempt, follows=follows, state=RUNNING, opened_at=now)
        index = {'unit': unit, 'latest': dispatch, 'state': RUNNING, 'attempts': attempt}
    else:
        if record is None or record.get('state') != RUNNING:
            raise Refused('stale_subject:land_dispatch/ended', dispatch)
        outcome = params.get('outcome')
        if outcome not in ENDS:
            raise Refused('invalid_input:land_dispatch/outcome', str(outcome))
        ended = {k: v for k, v in (params.get('end') or {}).items() if k not in (
            'schema', 'dispatch_id', 'domain', 'repository', 'unit', 'station', 'attempt', 'follows', 'state')}
        record = dict(record, **ended, state=outcome, ended_at=now)
        if index.get('latest') == dispatch:
            index['state'] = outcome
    return {rid: {'kind': KIND, 'data': record}, xid: {'kind': UNIT_KIND, 'data': index}}


class FloorRecords:
    """The floor authority's read (VELDO-0049) the CandidatePolicy and the Landing ask: record(unit), the
    stored floor record of one unit of this repository, on this connection."""

    def __init__(self, conn, repository):
        self.conn, self.repository = conn, repository

    def record(self, unit):
        row = _entity(self.conn, floor_id(self.repository, unit)) if _text(unit) else None
        return row['data'] if row and row['kind'] == FLOOR_KIND else None


class LandStation:
    """The land dispatches of one repository over a real store connection.

    store, conn        control_store and a writer connection to it; principal, signer and sign the service
                       that writes (an active service member for the repository), generation its authority
                       generation.
    land               the work configuration's `land` entry (config_problem): the repository holding the
                       builds, the trunk and the remote name there, the VELDO-0028 executor's configuration
                       and receiver, the lander's effect principal and its connection key, the VELDO-0051
                       projection's root, the land lock's ledger, the candidate commits' identity, and
                       optionally the trusted installation, the observation and workspace roots.
    settlement_trust   the Gate's settlement signers (CandidatePolicy); call the executor adapter
                       (control_effect_executor.call by default); observe receives one event per land step."""

    def __init__(self, store, conn, *, domain, repository, land, principal, signer, sign, generation=1,
                 settlement_trust=None, call=None, observe=None, clock=None):
        problem = config_problem(land)
        if problem:
            raise Refused('invalid_input:land:' + problem)
        if not all(_text(v) for v in (domain, repository, principal, signer)):
            raise Refused('invalid_input:coordinates', 'the domain, repository, principal and signer are named')
        self.store, self.conn = store, conn
        self.domain, self.repository, self.land_config = domain, repository, dict(land)
        self.principal, self.signer, self.sign, self.generation = principal, signer, sign, generation
        self.settlement_trust, self.call = settlement_trust, call
        self.observe = observe or (lambda event: None)
        self.clock = clock or time.time
        self.floor = FloorRecords(conn, repository)
        self.counts = {'opened': 0, 'refused': 0}
        conn.command_registry[OPERATION] = {'transaction_transition': transition, 'writes': WRITES}

    # Reads.

    def record(self, dispatch_id):
        row = _entity(self.conn, record_id(dispatch_id)) if _text(dispatch_id) else None
        return row['data'] if row and row['kind'] == KIND else None

    def records(self, unit=None):
        """This repository's land dispatch records (of `unit`, when named), in attempt order."""
        found = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,)):
            record = json.loads(data)
            if (record.get('domain'), record.get('repository')) == (self.domain, self.repository) and (
                    unit is None or record.get('unit') == unit):
                found.append(record)
        return sorted(found, key=lambda r: (r.get('unit'), r.get('attempt') or 0))

    def latest(self, unit):
        """The unit's latest land dispatch record, as its index names it, or None."""
        index = _entity(self.conn, unit_index_id(self.domain, self.repository, unit))
        latest = ((index or {}).get('data') or {}).get('latest') if (index or {}).get('kind') == UNIT_KIND else None
        return self.record(latest) if latest else None

    # Commands.

    def _run(self, action, unit, dispatch, fields):
        now = self.clock()
        params = dict(fields, action=action, now=now, principal=self.signer, domain=self.domain,
                      repository=self.repository, unit=unit, dispatch_id=dispatch)
        ids = (record_id(dispatch), unit_index_id(self.domain, self.repository, unit))
        expected = {}
        for identity in ids:
            row = self.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            expected[identity] = row[0] if row else 0
        command_id = 'land-dispatch/%s/%s/%s' % (action, dispatch, _digest(params)[len('sha256:'):][:24])
        command = dict(command_id=command_id, principal=self.signer, operation=OPERATION, parameters=params,
                       expected_versions=expected, artifact_digests=[], nonce=command_id + '/nonce')
        try:
            self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            self.counts['refused'] += 1
            code = error.code if isinstance(error, Refused) else '%s:land_dispatch/%s' % (
                self.store_class(error.code), error.code)
            self._emit(action, unit, dispatch, outcome='refused', refusal=code, taxonomy=taxonomy(code))
            raise Refused(code, getattr(error, 'detail', '')) from None
        return self.record(dispatch)

    @staticmethod
    def store_class(code):
        return {'stale_version': 'stale_subject', 'transition_refused': 'invalid_input'}.get(code, 'unknown_outcome')

    def _ops(self, evidence):
        """The factory land's GitLandOps over this repository's configuration, with the authority's
        CandidatePolicy and the exact-tip Landing wired, exactly as every factory land runs."""
        land = self.land_config
        policy = LD.CandidatePolicy(self.store, self.conn, domain=self.domain, repository=self.repository,
                                    floor=self.floor, settlement_trust=self.settlement_trust)
        landing = LG.Landing(self.store, self.conn, domain=self.domain, repository=self.repository,
                             effects=land['effects'], target=land['target'], principal=land['principal'],
                             connection_key=land['connection_key'], floor=self.floor, events_root=land['events_root'],
                             signer=self.signer, sign=self.sign, generation=self.generation, call=self.call,
                             observe=self.observe)
        return LD.GitLandOps(land['repository'], evidence, trunk=land['trunk'], remote=land['remote'], push=True,
                             policy=policy, identity=tuple(land['identity']), workspace_root=land.get('workspace_root'),
                             observe=self.observe, domain=self.domain, repository=self.repository,
                             installation=land.get('installation'), observations=land.get('observations'),
                             landing=landing)

    def land(self, unit, *, evidence, holder=None, generation=None, follows=None):
        """Run one land dispatch of `unit`, landing the build whose evidence commit is `evidence`; `follows`
        names the land dispatch this one re-lands. Returns the ended record. Refused, with nothing run,
        when the station cannot be built for it or its record cannot be opened (another land of the unit is
        running, or `follows` is not the unit's latest land that a new one may follow)."""
        try:
            ops = self._ops(evidence)
        except (LG.Refused, OSError, ValueError) as error:
            raise Refused(getattr(error, 'code', 'unavailable_service:land/' + type(error).__name__),
                          getattr(error, 'detail', '')) from None
        index = _entity(self.conn, unit_index_id(self.domain, self.repository, unit))
        attempt = int(((index or {}).get('data') or {}).get('attempts') or 0) + 1
        dispatch = 'dispatch/%s/land-%d-%s' % (unit, attempt, os.urandom(4).hex())
        opened = self._run('open', unit, dispatch, {'follows': follows, 'record': {
            'evidence': evidence, 'holder': holder, 'generation': generation}})
        self.counts['opened'] += 1
        self._emit('open', unit, dispatch, outcome='accepted', follows=follows, attempt=opened.get('attempt'),
                   evidence=evidence)
        subject = {'spec': unit, 'dispatch': dispatch, 'holder': holder, 'generation': generation}
        try:
            result = LD.veldo_land(ops, subject, worker_id='land-' + hashlib.sha256(dispatch.encode()).hexdigest()[:12],
                                   claims_root=self.land_config['claims'])
        except Exception as error:  # noqa: BLE001 - a land that cannot answer is an unknown outcome, never success
            result = {'ok': False, 'stage': 'raised', 'detail': {'refusal': 'unknown_outcome:land/' + type(error).__name__}}
        outcome, end = self.classify(result, ops.record(), dispatch)
        self.counts[outcome] = self.counts.get(outcome, 0) + 1
        ended = self._run('end', unit, dispatch, {'outcome': outcome, 'end': end})
        self._emit('end', unit, dispatch, outcome=outcome, follows=follows, watermark=end.get('watermark'),
                   candidate=end.get('candidate'), refusal=end.get('refusal'), taxonomy=taxonomy(end.get('refusal'))
                   if end.get('refusal') else None, observed=end.get('observed'))
        return ended

    @staticmethod
    def classify(result, candidate, dispatch):
        """(outcome, fields) of a land's answer: its stage, the watermark, the candidate, the gate observation,
        the publication effect and receipt, and the named refusal."""
        result = result if isinstance(result, dict) else {}
        detail = result.get('detail') if isinstance(result.get('detail'), dict) else {}
        landing = detail.get('landing') if isinstance(detail.get('landing'), dict) else {}
        c = candidate if isinstance(candidate, dict) else {}
        # The candidate record keeps the publication's answer however the land ended (GitLandOps._publish).
        published = c.get('landing') if isinstance(c.get('landing'), dict) else {}
        refusals = [r for r in (landing.get('refusals') or detail.get('refusals') or []) if _text(r)]
        refusal = landing.get('refusal') or detail.get('refusal') or (refusals[0] if refusals else None)
        stage = result.get('stage')
        fields = {'stage': stage, 'watermark': c.get('watermark'), 'implementation': c.get('implementation'),
                  'candidate': {'id': c.get('id'), 'commit': c.get('commit'), 'tree': c.get('tree')},
                  'observation': ((c.get('gate') or {}).get('observation') or {}).get('digest'),
                  'effect': 'effect:' + dispatch if published else None, 'receipt': published.get('receipt'),
                  'refusal': None, 'refusals': [], 'observed': landing.get('observed'),
                  'subject': landing.get('subject'), 'conflicts': detail.get('conflicts')}
        if result.get('ok') is True and published.get('outcome') == 'landed' and _text(published.get('receipt')):
            return LANDED, fields
        fields.update(refusal=refusal or 'unknown_outcome:land/' + str(stage), refusals=(refusals or [refusal])[:8])
        if stage == 'reconcile' and str(refusal).startswith(CONFLICTS):
            return CONFLICT, fields
        if (stage == 'finalize' and landing.get('outcome') == 'failed'
                and (landing.get('observed') or {}).get('classification') in LG.TRUNK_MOVED):
            return TRUNK_MOVED, fields
        if (stage == 'finalize' and landing.get('outcome') == 'refused' and isinstance(landing.get('subject'), dict)
                and refusals and all(code.startswith(LG.APPROVAL_CODES) for code in refusals)):
            return AWAITING, fields
        if landing.get('outcome') == 'unknown' or taxonomy(fields['refusal']) == 'unknown_outcome':
            return UNKNOWN, fields
        return FAILED, fields

    def grant(self, unit, record, *, owner, basis):
        """The owner's fresh grant for the re-merged tree: only the mismatched names in the subject,
        bound to exactly that subject (tree, source, proof and dependency versions) at
        the unit's revision it was asked for, with `basis` (his answer). Returns the approval ids."""
        subject = (record or {}).get('subject')
        if ((record or {}).get('state') != AWAITING or not isinstance(subject, dict)
                or not subject.get('approvals') or record.get('unit') != unit):
            raise Refused('invalid_input:grant', 'no land of this unit awaits a grant')
        bound = {f: subject.get(f) for f in LG.SUBJECT_FIELDS}
        approvals = [(aid, json.loads(data)) for aid, data in
                     self.conn.execute("SELECT id, data FROM entities WHERE kind='approval'")]
        applied = [aid for aid, data in approvals if data.get('land_dispatch') == record['dispatch_id']]
        if applied:
            return applied
        # Re-read every prior grant before writing any replacement. An answer cannot revive a
        # revoked grant or repair a different binding than the older tree named by the question.
        for name in subject['approvals']:
            prior = [data for _, data in approvals if data.get('unit') == unit and data.get('name') == name
                     and data.get('revision') == subject.get('revision') and data.get('state') == 'granted']
            if not any(isinstance(data.get('subject'), dict)
                       and [f for f in LG.SUBJECT_FIELDS if data['subject'].get(f) != bound[f]] == ['tree']
                       for data in prior):
                raise Refused('missing_authority:approval/' + name, 'prior grant no longer covers the older tree')
        written = []
        for name in subject.get('approvals') or []:
            aid = 'approval:%s:%s:%s' % (unit, name, _digest(bound)[len('sha256:'):][:16])
            data = {'unit': unit, 'name': name, 'revision': subject.get('revision'), 'state': 'granted',
                    'subject': bound, 'granted_by': owner, 'basis': basis, 'land_dispatch': record['dispatch_id']}
            current = _entity(self.conn, aid)
            if current is None or current['data'] != data:
                command_id = 'land-grant/%s' % _digest([aid, data])[len('sha256:'):][:32]
                self.store.execute(self.conn, {
                    'command_id': command_id, 'principal': self.signer, 'operation': 'upsert_entity',
                    'parameters': {'entity_id': aid, 'kind': 'approval', 'data': data},
                    'expected_versions': {aid: current['version'] if current else 0}, 'artifact_digests': [],
                    'nonce': command_id + '/nonce'}, self.signer, self.sign, self.generation)
            written.append(aid)
        self._emit('grant', unit, record['dispatch_id'], outcome='accepted', approvals=written, owner=owner)
        return written

    # Observability.

    def _emit(self, operation, unit, dispatch, **fields):
        self.observe(dict({'schema': SCHEMA, 'operation': 'land_dispatch_' + operation, 'domain': self.domain,
                           'repository': self.repository, 'unit': unit, 'dispatch_id': dispatch}, **fields))

    def status(self):
        """Metrics: opened and refused commands, the lands running, the outcomes of this repository's land
        dispatches, and the re-land dispatches (those that follow another) per unit."""
        records = self.records()
        return dict(self.counts, running=sorted(r['dispatch_id'] for r in records if r.get('state') == RUNNING),
                    outcomes={s: sum(r.get('state') == s for r in records) for s in ENDS},
                    relands={u: sum(1 for r in records if r.get('unit') == u and r.get('follows'))
                             for u in sorted({r.get('unit') for r in records})})
