#!/usr/bin/env python3
"""The authority's side of the authenticated API: verify an edge assertion, execute its command (VELDO-0130).

WHAT THIS MODULE IS. What the authority runs for each API assertion the edge sends. It holds no
session and trusts nothing the API says about who is speaking beyond what the edge signed, and it
decides again, on its own store connection, everything the protected signer decided:

  - the value is one `veldo.api_assertion/v1` (control_api_assertion) for this authority and domain;
  - it is carried by the configured api edge, a current service member, and its signature verifies
    with that edge's enrolled key (ssh-keygen -Y, as VELDO-0126 verifies today);
  - it is live: issued no later than now and not past its 60-second expiry;
  - the principal it names holds the named api_credential, which is current, and is a current person
    member, so a credential revoked or a membership revoked while the assertion was in flight refuses;
  - the member's type is admitted at the operation's authority boundary (decision_settlement admits
    only a person).

Then it executes the operation's one existing domain command, derived from the verified assertion
(control_api_assertion.domain_request), never a second store write: a message goes into VELDO-0126's
common intake through its API adapter, with the edge's signature over that request; a decision answer
goes to VELDO-0068 settlement as an API answer, which applies the presentation rules the Telegram answer
meets, so one request version still gets one ruling; a credential revocation is
control_api_credentials.revoke_as_member, whose journal actor is the member. Every outcome is observed
with the operation, domain, principal, credential id, session handle, request id and the assertion
digest, never the assertion's text or a signature.

A workflow save (AC4) is VELDO-0132's Workflows.save, the only writer of workflow revisions, for the
verified principal with the base version the assertion carries: its own transaction judges the editor
(an active person member holding project_owner or technical_authority scoped to the repository) and
refuses a base that is not the current head as stale_version, so a stale or unauthorized edit is refused
by name and writes nothing.

READS (AC2). `inspect` is the read the API's session checks go through: named committed entities and the
journal watermark, as the VELDO-0047 service's inspect answers them. `read` serves one published read
model (control_api_models.read_model) from this connection for a principal who is a current person
member whose scope covers a project this domain serves (else unauthorized:no_project, the intake's own
refusal); `workflow` is VELDO-0132's Workflows.load of one revision. `events` is the live event feed:
every committed journal record after a sequence, read through the VELDO-0051 publication's own journal
reader, each with its identity (sequence, command, record digest, commit time), the kinds and ids it
changed and never their data, the credential and membership revocations it commits, and the events the
publication derives at that record, with the publication's watermark and freshness: "stale" with the
count of records not yet published whenever the published watermark is behind the head. An unreadable
store is unavailable_service, never an empty answer.

WHAT IT IS NOT. Not the transport: routing these packets through the VELDO-0047 service socket
(VELDO-0107) is the phase that wires the service. Standard library only.
"""
import importlib.util
import json
from pathlib import Path
import sqlite3
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('api_authority_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AS = organ('control_api_assertion')
CR = organ('control_api_credentials')
MO = organ('control_api_models')
WF = MO.WF
E = organ('control_channel_enrollment')
CM, AC = CR.CM, CR.AC
SCHEMA = 'veldo.api_authority_observation/v1'
HINT_SCHEMA = 'veldo.control_notification/v1'  # control_notify.SCHEMA, the VELDO-0046 hint
# The error classes of the specification's taxonomy, from each organ's own class names.
CLASSES = {'missing_authority': 'unauthorized', 'stale_subject': 'stale_version', 'invalid_input': 'invalid_input',
           'unsupported_configuration': 'invalid_input', 'missing_evidence': 'missing_evidence',
           'unavailable_service': 'unavailable_service', 'unauthenticated': 'unauthenticated',
           'unauthorized': 'unauthorized', 'stale_version': 'stale_version', 'unknown_outcome': 'unknown_outcome'}


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail))
        self.code, self.detail = code, detail


def taxonomy(code):
    """The specification's error class of a refusal: its own head, else the intake's or settlement's class."""
    head = str(code).split(':', 1)[0]
    if head in CLASSES:
        return CLASSES[head]
    for named in (AS.IN.taxonomy, AS.ST.taxonomy):
        found = named(code)
        if found != 'unknown_outcome':
            return CLASSES.get(found, 'unknown_outcome')
    return 'unknown_outcome'


def _class_of(code):
    """The taxonomy class of an organ's refusal: its own head, else VELDO-0132's class for it."""
    head = str(code).split(':', 1)[0]
    return CLASSES[head] if head in CLASSES else CLASSES.get(WF.taxonomy(code), 'unknown_outcome')


class ApiAuthority:
    """The API assertion judge on the authority's store connection `conn`.

    `store` and `membership` are the control_store and control_membership modules; `ids` this
    authority's domain_uuid, repository_uuid and store_uuid; `domain` the intake domain name; `edge`
    the api edge's service principal; `intake`, `settlement` and `credentials` the VELDO-0126 Intake,
    VELDO-0068 Settlement and control_api_credentials.Credentials on `conn`."""

    def __init__(self, store, membership, conn, *, ids, domain, edge, intake, settlement, credentials,
                 workflows=None, publication=None, notify=None, clock=time.time, observe=None):
        self.S, self.CM, self.conn = store, membership, conn
        self.ids = {f: ids.get(f) for f in AS.IDS}
        self.domain, self.edge = domain, edge
        self.intake, self.settlement, self.credentials, self.clock = intake, settlement, credentials, clock
        # VELDO-0132's Workflows on this connection, and VELDO-0051's Projection of this store.
        self.workflows, self.publication = workflows, publication
        # After each accepted command: notify(hint), the VELDO-0046 notification shape of the head record.
        self.notify = notify
        self.observe = observe or (lambda event: None)
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}

    # the read the API's session checks use

    def inspect(self, entity_ids):
        ids = entity_ids if isinstance(entity_ids, list) and len(entity_ids) <= 64 else []
        entities = {}
        for identity in ids:
            row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone() \
                if isinstance(identity, str) else None
            if row:
                entities[identity] = {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}
        head = self.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        return {'ok': True, 'reason': 'inspect', 'watermark': head, 'entities': entities}

    # the read models and the live feed (AC2)

    def _reader_problem(self, principal):
        member = AC.membership_entry(self.CM.authority_state(self.S, self.conn)['membership'], principal)
        if not AC.active_member(member, self.clock())[0] or member.get('principal_type') != 'person':
            return 'unauthenticated:member_not_current'
        if not any(self.CM.scope_covers(member.get('scope'), p) for p in self.intake.projects):
            return 'unauthorized:no_project'
        return None

    def _answer(self, principal, produce):
        try:
            problem = self._reader_problem(principal)
            if problem:
                return {'ok': False, 'reason': problem, 'taxonomy': taxonomy(problem)}
            return dict(produce(), ok=True)
        except (self.S.StoreRefused, sqlite3.Error, OSError):
            return {'ok': False, 'reason': 'unavailable_service:store', 'taxonomy': 'unavailable_service'}
        except Exception as error:  # noqa: BLE001 - an organ's named refusal (its own Refused class)
            if not isinstance(getattr(error, 'code', None), str):
                raise
            return {'ok': False, 'reason': error.code, 'taxonomy': _class_of(error.code)}

    def read(self, model, principal):
        """One published read model for `principal`, read on this connection now."""
        if model not in MO.MODELS:
            return {'ok': False, 'reason': 'missing_evidence:read_model', 'taxonomy': 'missing_evidence'}
        return self._answer(principal, lambda: MO.read_model(self.S, self.conn, model))

    def workflow(self, principal, workflow, version=None):
        """VELDO-0132's stored canvas document of one revision (the head when `version` is None)."""
        def produce():
            if self.workflows is None:
                raise WF.Refused('unavailable_service:workflows', 'no workflow service on this authority')
            document = self.workflows.load(workflow, version)
            served, paths = MO.redact(document)
            return dict(served, redacted=paths, watermark=MO.watermark(self.conn), freshness='live')
        return self._answer(principal, produce)

    def events(self, principal, after, limit=256):
        """The committed journal records after `after`, oldest first, at most `limit`, for `principal`."""
        return self._answer(principal, lambda: self._feed(after, limit))

    def feed(self, after, limit=256):
        """The same records for the API edge's own journal follow (ending sessions a record revokes); the
        streams it then feeds are each re-read through `events` for their own member."""
        try:
            return dict(self._feed(after, limit), ok=True)
        except (self.S.StoreRefused, sqlite3.Error, OSError):
            return {'ok': False, 'reason': 'unavailable_service:store', 'taxonomy': 'unavailable_service'}
        except Exception as error:  # noqa: BLE001 - the publication's named refusal
            if not isinstance(getattr(error, 'code', None), str):
                raise
            return {'ok': False, 'reason': error.code, 'taxonomy': _class_of(error.code)}

    def _feed(self, after, limit):
        if self.publication is None:
            raise WF.Refused('unavailable_service:publication', 'no VELDO-0051 publication on this authority')
        # The publication's own journal reader and stored watermark; its refusals keep their names.
        rows = self.publication._rows()
        mark = self.publication.watermark()
        head = rows[-1][0] if rows else 0
        published = mark['watermark'] if mark else 0
        derived, _judged = self.publication.derive(rows, after)
        by_seq = {}
        for event in derived:
            by_seq.setdefault(event.get('journal_seq'), []).append(event['id'])
        out = []
        for seq, command, digest, changes, committed in rows:
            if seq <= after:
                continue
            if len(out) >= limit:
                break
            revocations = {}
            for eid, change in changes.items():
                data = (change or {}).get('data') or {}
                if change.get('kind') in (CR.KIND, 'membership') and data.get('revoked_at') is not None:
                    revocations[eid] = {'kind': change['kind'], 'data': {'credential_id': data.get('credential_id'),
                                                                         'revoked_at': data['revoked_at']}}
            out.append({'seq': seq, 'command_id': command, 'record_digest': digest, 'committed_at': committed,
                        'entities': [{'id': eid, 'kind': (changes[eid] or {}).get('kind')} for eid in sorted(changes)],
                        'revocations': revocations, 'published': by_seq.get(seq, [])})
        return {'schema': 'veldo.api_events/v1', 'after': after, 'events': out,
                'watermark': {'seq': head, 'record_digest': rows[-1][2] if rows else None},
                'publication': {'watermark': published, 'head': head, 'pending_records': max(0, head - published),
                                'freshness': 'live' if published == head else 'stale'}}

    # the judgment

    def apply(self, packet):
        a = packet.get('assertion') if isinstance(packet, dict) else None
        a = a if isinstance(a, dict) else {}
        about = {'operation': a.get('operation'), 'principal': a.get('principal'), 'credential_id': a.get('credential_id'),
                 'session': a.get('session'), 'request_id': a.get('request_id'),
                 'assertion_digest': AS.digest(a) if a else None}
        try:
            result = self._apply(packet, a)
        except Refused as exc:
            return self._observe(about, False, exc.code, None)
        except (self.S.StoreRefused, sqlite3.Error):
            return self._observe(about, False, 'unavailable_service', None)
        refusal = result.get('reason') if result.get('outcome') in ('refused', 'unknown_outcome') else None
        answer = self._observe(about, refusal is None, refusal, result)
        if refusal is None and self.notify is not None:
            self.notify(self.hint())
        return answer

    def hint(self):
        """The VELDO-0046 notification hint of the journal head: identity only, never domain data."""
        row = self.conn.execute('SELECT seq, command_id, record_digest FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
        return dict(self.ids, schema=HINT_SCHEMA, command_id=row[1] if row else None,
                    record_digest=row[2] if row else None, watermark=row[0] if row else 0)

    def _apply(self, packet, a):
        if AS.shape_problems(a):
            raise Refused('invalid_input:assertion', 'not one API assertion')
        if a['domain'] != self.domain or any(a[f] != v for f, v in self.ids.items()):
            raise Refused('unauthorized:domain', 'the assertion names another domain, repository or store')
        now = self.clock()
        state = self.CM.authority_state(self.S, self.conn)
        kid = AC.edge_channel(AS.CHANNEL).get('edge_key_id')
        if a['edge'] != self.edge or a['edge_key_id'] != kid or a['channel'] != AS.CHANNEL:
            raise Refused('unauthenticated:edge', 'the assertion is not carried by the api edge')
        edge_key = E.edge_record(state, kid)
        member = AC.membership_entry(state['membership'], self.edge)
        if (edge_key is None or edge_key.get('channel') != AS.CHANNEL or edge_key.get('principal') != self.edge
                or not E.active(edge_key, now) or not AC.active_member(member, now)[0]
                or member.get('principal_type') != 'service'):
            raise Refused('unauthenticated:edge', 'the api edge is not a current enrolled service member')
        signature = packet.get('signature')
        verified, _ = AC.ssh_keygen_verify(self.S.canonical_bytes(a), signature if isinstance(signature, str) else '',
                                           AC.allowed_signers_line(self.edge, edge_key['public_key']), self.edge)
        if not verified:
            raise Refused('unauthenticated:signature', 'the assertion is not the api edge\'s')
        if AS.time_problem(a, now):
            raise Refused('unauthenticated:expired', 'the assertion is not live')
        _record, why = CR.current(state, a['credential_id'], now, principal=a['principal'])
        if why:
            raise Refused('unauthenticated:' + why, 'the principal holds no current credential')
        person = AC.membership_entry(state['membership'], a['principal'])
        boundary = AS.OPERATIONS[a['operation']]['boundary']
        if person.get('principal_type') not in AC.BOUNDARIES[boundary] or person.get('principal_type') != 'person':
            raise Refused('unauthorized:boundary', 'the member is not admitted at %s' % boundary)
        derived = AS.domain_request(a)
        if a['operation'] == 'send_message':
            return self.intake.receive('api_request', {'request': derived, 'signature': packet.get('domain_signature')})
        if a['operation'] == 'answer_decision':
            return self.settlement.api_answer({'answer': derived, 'signature': packet.get('domain_signature')})
        provenance = {'channel': AS.CHANNEL, 'edge': self.edge, 'request_id': a['request_id'],
                      'credential_id': a['credential_id'], 'assertion_digest': AS.digest(a)}
        if a['operation'] == 'save_workflow':
            return self._save_workflow(a)
        done = self.credentials.revoke_as_member(a['principal'], a['parameters']['credential_id'], provenance)
        if done['refusal']:
            return {'outcome': 'refused', 'reason': '%s:%s' % (CLASSES.get(done['error_class'], 'unknown_outcome'), done['refusal'])}
        return {'outcome': 'revoked'}

    def _save_workflow(self, a):
        """VELDO-0132's save for the verified principal: its transaction judges the editor and the base."""
        p = a['parameters']
        if self.workflows is None:
            return {'outcome': 'refused', 'reason': 'unavailable_service:workflows'}
        definition = p['definition'] if isinstance(p['definition'], dict) else {}
        if definition.get('id') != p['workflow']:
            return {'outcome': 'refused', 'reason': 'invalid_input:definition.id is not the workflow saved'}
        document = {'definition': p['definition']} if p['layout'] is None else {'definition': p['definition'],
                                                                                  'layout': p['layout']}
        try:
            saved = self.workflows.save(document, principal=a['principal'], base=p['base'])
        except Exception as error:  # noqa: BLE001 - VELDO-0132's named refusal (its own Refused class)
            if not isinstance(getattr(error, 'code', None), str):
                raise
            klass, head = _class_of(error.code), error.code.split(':', 1)[0]
            return {'outcome': 'refused', 'reason': error.code if CLASSES.get(head) == klass else '%s:%s' % (klass, error.code)}
        return dict(saved, outcome='saved')

    def commands(self):
        """Each operation and the store command it executes, for the route-to-command comparison."""
        return {'send_message': AS.IN.RECORD, 'answer_decision': AS.ST.API, 'revoke_credential': CR.REVOKE,
                'save_workflow': WF.SAVE}

    def _observe(self, about, ok, refusal, result):
        self.counts['accepted' if ok else 'refused'] += 1
        event = dict(self.ids, schema=SCHEMA, domain=self.domain, outcome='accepted' if ok else 'refused',
                     refusal=refusal, taxonomy=None if ok else taxonomy(refusal), **about)
        self.observations.append(event)
        self.observe(event)
        return {'ok': ok, 'reason': refusal, 'taxonomy': event['taxonomy'], 'operation': about['operation'],
                'request_id': about['request_id'], 'result': result}

    def metrics(self):
        refused = {}
        for e in self.observations:
            if e['refusal'] is not None:
                refused[e['refusal']] = refused.get(e['refusal'], 0) + 1
        return dict(self.counts, refused_by_reason=refused)
