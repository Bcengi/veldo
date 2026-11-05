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

THE EXECUTION RECORD (VELDO-0141). `record` serves one run's execution record (control_execution_record) for a
principal who is a current person member whose scope covers THAT run's project, the project its dispatch's
contract reserved (else unauthorized:out_of_scope): the kept lines after a cursor, at most a page, each with
its sequence, receive time, stream, redaction kinds and payload as kept (the receiver redacted every line
before keeping it; nothing unredacted exists to serve), with the run's identity (dispatch, unit, station,
project, account, host, state, process) and, once the dispatch has ended, its end and the line count, byte
count and digest its exit committed, which the file must match or the read is refused by name. An unknown
run is missing_evidence:unknown_run, a cursor past the end invalid_input:cursor_past_end, a record bound to
another dispatch or not matching its commitment unknown_outcome:record_binding or :record_digest; none is
served as an empty record. The records are read from `records`, the receivers' records directory.

VELDO-0178: a conversation turn's run has no project; its record is decided by its conversation and served to the
conversation's owner alone (else missing_authority:conversation_owner), whatever his scope, and a run with neither a
project nor a conversation is served to nobody (unauthorized:out_of_scope). The served run names the conversation and
the turn its contract binds, and a record whose header names another conversation or turn is refused
(unknown_outcome:record_binding). Each read of a turn's record is observed with its dispatch, conversation and turn.

THE OWNER'S CONVERSATIONS (VELDO-0178 AC1). `conversations` reads, for a current person member, his own
conversations (id, status, role, version, turn count and last activity) or one of them with every turn (sequence,
state, his message as its intake source kept it, reply, outcome, dispatch id and account). A conversation of anyone
else is refused missing_authority:conversation_owner, whatever the reader's scope, and is never listed; an unknown
one is invalid_input:conversation:unknown. Four operations send VELDO-0174's typed commands as the verified member
through control_conversation.Conversations (`conversations`): open_conversation (a new id from the request id, the
assertion's digest as its intake digest), close_conversation, change_conversation_role and
attach_conversation_project, each on the version the owner saw (else stale_version), each command's id the API
request id, so a route call joins its command. Every conversation record is on the event feed for its owner alone
(control_api_models_scope).

A workflow save (AC4) is VELDO-0132's Workflows.save, the only writer of workflow revisions, for the
verified principal with the base version the assertion carries: its own transaction judges the editor
(an active person member holding project_owner or technical_authority scoped to the repository) and
refuses a base that is not the current head as stale_version, so a stale or unauthorized edit is refused
by name and writes nothing.

THE OWNER'S WORK COMMANDS (VELDO-0131, owner Telegram 38184). Three more operations execute existing writers
for the verified principal, each refusing by name and writing nothing on a refusal:
  - reprioritize_backlog: control_backlog.Backlog's own reprioritize command, derived from the assertion
    (control_api_assertion.domain_request) and signed by the edge (the packet's domain signature); the Backlog
    verifies the edge, the assertion and the command again (its `api_assertion`), then judges the member as for
    his own signature: the project's owner holding priority_authority, the item at the version he saw.
  - stop_worker: control_dispatch.Dispatches.request_stop, the person's stop request of one dispatch at the
    version he saw, recorded on the dispatch. When this authority holds the runner's receivers (`stop`, a
    control_launch.stop_requester) it asks the receiver at once and records the ask's result (stop_result);
    otherwise the runner that holds them does on its next sweep (control_launch.Runner.honor_stops).
  - set_account_cap: control_accounts.Accounts.cap, a versioned change of the account's run concurrency.
A missing writer is unavailable_service by name.

THE OWNER'S PACING (VELDO-0236). pause_account, resume_account and set_account_ceiling execute control_accounts'
pause, resume and ceiling for the verified principal (route `ui`, the assertion digest its provenance), the same signed
operations Telegram's typed commands reach through intake; control_accounts refuses anyone but the factory owner. The
answer names the account, the window and the end in words in the authority's time zone (`time_zone`).

READS (AC2). `inspect` is the read the API's session checks go through: named committed entities and the
journal watermark, as the VELDO-0047 service's inspect answers them. `read` serves one published read
model (control_api_models.read_model) from this connection for a principal who is a current person
member whose scope covers a project this domain serves (else unauthorized:no_project, the intake's own
refusal); `workflow` is VELDO-0132's Workflows.load of one revision. `events` is the live event feed:
every committed journal record after a sequence, read through the VELDO-0051 publication's own journal
reader, each with its identity (sequence, command, record digest, commit time), the kinds and ids it
changed and never their data, the credential and membership revocations it commits, and the events the
publication has published at that record (its own log, never past its stored watermark), with the
publication's watermark and freshness: "stale" with the count of records not yet published whenever the
published watermark is behind the head. The records come from the publication's public bounded journal
reader (VELDO-0051's control_event_projection.journal), one query of at most `limit` records. An unreadable
store is unavailable_service, never an empty answer.

VELDO-0164 scopes model rows, workflow revisions and member events using the rules beside each
registered kind. Shared configurations and default teams remain visible. Unresolved projects require
universal scope. A member page carries the last scanned journal sequence as its cursor, including
when every record was withheld; the head watermark and publication freshness remain unchanged.
The edge's feed and universal-scope answers retain their existing representation.

ONLY THE AUTHORITY RUNS IT (phase 3). The authority service (control_service_api) constructs this judge
on its own store connection with `authority_lock`, the descriptor on which it holds the exclusive flock
of the stable lock file beside the store (VELDO-0047's one instance). Every command and every read first
asks `authority_problem`: the descriptor must be that file and this process must hold its lock. So the
API process, which reaches the authority only over the service socket (control_client_api), cannot run a
command or a read in-process while the service runs: it holds no such lock and cannot take it, and it is
refused missing_authority:not_the_authority with nothing read or written.

WHAT IT IS NOT. Not the transport: the service socket and its client are control_service_api and
control_client_api. Standard library only.
"""
import hashlib
import hmac
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


LOCK = organ('control_authority_lock')
AS = organ('control_api_assertion')
CR = organ('control_api_credentials')
MO = organ('control_api_models')
WF = MO.WF
MC = organ('control_mcp_catalog')
CV = organ('control_credential')
E = organ('control_channel_enrollment')
ER = organ('control_execution_record')
# VELDO-0131: the writers of the owner's work commands (their taxonomies and record identities).
BL = organ('control_backlog')
DP = organ('control_dispatch')
AA = organ('control_accounts')
WORK_OPERATIONS = ('reprioritize_backlog', 'stop_worker', 'set_account_cap')
# VELDO-0236: the owner's pacing of an account, each control_accounts' own signed operation.
PACING_OPERATIONS = {'pause_account': 'pause', 'resume_account': 'resume', 'set_account_ceiling': 'ceiling'}
# VELDO-0178: the conversation commands the API sends (control_conversation's OPEN, CLOSE, ROLE and ATTACH).
CONVERSATION_OPERATIONS = ('open_conversation', 'close_conversation', 'change_conversation_role',
                           'attach_conversation_project')
CONVERSATIONS_SCHEMA = 'veldo.api_conversations/v1'
OWNER_REFUSAL = 'missing_authority:conversation_owner'
RECORD_SCHEMA = 'veldo.api_execution_record/v1'
RECORD_LIMIT = 512
# A dispatch's states once its run has ended (control_dispatch.STATES): its record grows no more.
ENDED = ('exited', 'refused', 'unknown')
CM, AC = CR.CM, CR.AC
SCHEMA = 'veldo.api_authority_observation/v1'
HINT_SCHEMA = 'veldo.control_notification/v1'  # control_notify.SCHEMA, the VELDO-0046 hint
LOCK_NAME = LOCK.LOCK_NAME
# The error classes of the specification's taxonomy, from each organ's own class names.
CLASSES = {'missing_authority': 'unauthorized', 'stale_subject': 'stale_version', 'invalid_input': 'invalid_input',
           'unsupported_configuration': 'invalid_input', 'missing_evidence': 'missing_evidence',
           'unavailable_service': 'unavailable_service', 'unauthenticated': 'unauthenticated',
           'incomplete_roster': 'invalid_input', 'not_authorized': 'unauthorized', 'not_owner': 'unauthorized',
           'not_accepted': 'unauthorized', 'unauthorized': 'unauthorized', 'stale_version': 'stale_version', 'unknown_outcome': 'unknown_outcome'}


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


def _named(code, organ_taxonomy):
    """A writer's refusal under the specification's class (VELDO-0131): its own name when its head is a class here,
    else prefixed with the class the writer's own taxonomy gives it, so a refusal is never an unknown outcome."""
    code = str(code)
    head = code.split(':', 1)[0]
    if head in CLASSES:
        return code
    klass = CLASSES.get(organ_taxonomy(code), 'unknown_outcome')
    return '%s:%s' % (klass, code)


def _class_of(code):
    """The taxonomy class of an organ's refusal: its own head, else VELDO-0132's class for it."""
    head = str(code).split(':', 1)[0]
    return CLASSES[head] if head in CLASSES else CLASSES.get(WF.taxonomy(code), 'unknown_outcome')


SCOPE = MO.SCOPE
_CONVERSATION = []


def _conversation_module():
    """control_conversation, loaded once when first needed (VELDO-0178)."""
    if not _CONVERSATION:
        _CONVERSATION.append(organ('control_conversation'))
    return _CONVERSATION[0]


def _turns(conn, CVM, identity):
    found = [json.loads(raw) for (raw,) in conn.execute('SELECT data FROM entities WHERE kind=?', (CVM.TURN_KIND,))]
    return sorted((t for t in found if t.get('conversation') == identity), key=lambda t: t.get('sequence') or 0)


def _last_activity(record, turns):
    """The latest moment the conversation or one of its turns changed."""
    moments = [record.get('opened_at'), record.get('closed_at')]
    for turn in turns:
        moments += [turn.get('created_at'), turn.get('dispatched_at'), turn.get('ended_at')]
    moments = [m for m in moments if isinstance(m, (int, float)) and not isinstance(m, bool)]
    return max(moments) if moments else None


def _message_text(conn, source):
    """The owner's words of a turn, as its intake source keeps them, or None."""
    row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(source),)).fetchone() if source else None
    return json.loads(row[1]).get('text') if row and row[0] == 'intake_source' else None


# Preserve the API authority's public check; all writers use the same implementation.
authority_problem = LOCK.authority_problem


class ApiAuthority:
    """The API assertion judge on the authority's store connection `conn`.

    `store` and `membership` are the control_store and control_membership modules; `ids` this
    authority's domain_uuid, repository_uuid and store_uuid; `domain` the intake domain name; `edge`
    the api edge's service principal; `intake`, `settlement` and `credentials` the VELDO-0126 Intake,
    VELDO-0068 Settlement and control_api_credentials.Credentials on `conn`; `authority_lock` the
    descriptor holding the authority's lock (authority_problem)."""

    def __init__(self, store, membership, conn, *, ids, domain, edge, intake, settlement, credentials,
                 workflows=None, publication=None, notify=None, clock=time.time, observe=None, authority_lock=None,
                 catalog=None, mcp_credentials=None, records=None, configurations=None, team_routes=None,
                 backlog=None, dispatches=None, accounts=None, stop=None, conversations=None, time_zone='UTC'):
        self.S, self.CM, self.conn = store, membership, conn
        # VELDO-0236: the owner's time zone the pacing answers name their ends in.
        self.time_zone = time_zone
        # VELDO-0178: control_conversation.Conversations on `conn`, which sends the owner's conversation commands.
        self.conversation_commands = conversations
        # VELDO-0131: control_backlog.Backlog, control_dispatch.Dispatches and control_accounts.Accounts on `conn`,
        # and `stop(dispatch_id, reason)`, the runner's in-process ask (control_launch.stop_requester), when held.
        self.backlog, self.dispatches, self.accounts, self.stop = backlog, dispatches, accounts, stop
        # VELDO-0141: the launch receivers' records directory (control_execution_record.directory).
        self.records = records
        self.configurations, self.team_routes = configurations, team_routes
        self.authority_lock = authority_lock
        self.ids = {f: ids.get(f) for f in AS.IDS}
        self.domain, self.edge = domain, edge
        self.intake, self.settlement, self.credentials, self.clock = intake, settlement, credentials, clock
        # VELDO-0132's Workflows on this connection, and VELDO-0051's Projection of this store.
        self.workflows, self.publication = workflows, publication
        self.catalog, self.mcp_credentials = catalog, mcp_credentials
        # After each accepted command: notify(hint), the VELDO-0046 notification shape of the head record.
        self.notify = notify
        self.observe = observe or (lambda event: None)
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}

    # the read the API's session checks use

    def _authority(self):
        """Refused unless this process is the authority of this store (authority_problem)."""
        problem = authority_problem(self.authority_lock, self.conn)
        if problem:
            raise Refused(problem, 'only the authority service runs the API\'s commands and reads')

    def inspect(self, entity_ids):
        self._authority()
        ids = entity_ids if isinstance(entity_ids, list) and len(entity_ids) <= 64 else []
        opened = not self.conn.in_transaction
        if opened:
            self.conn.execute('BEGIN')
        try:
            entities = {}
            for identity in ids:
                row = self.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone() \
                    if isinstance(identity, str) else None
                if row:
                    entities[identity] = {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}
            head = self.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
            return {'ok': True, 'reason': 'inspect', 'watermark': head, 'entities': entities}
        finally:
            if opened:
                self.conn.execute('ROLLBACK')

    # the read models and the live feed (AC2)

    def _reader_problem(self, principal):
        member = AC.membership_entry(self.CM.authority_state(self.S, self.conn)['membership'], principal)
        if not AC.active_member(member, self.clock())[0] or member.get('principal_type') != 'person':
            return 'unauthenticated:member_not_current'
        if not any(self.CM.scope_covers(member.get('scope'), p) for p in self.intake.projects):
            return 'unauthorized:no_project'
        return None

    def _answer(self, principal, produce):
        opened = False
        try:
            self._authority()
            opened = not self.conn.in_transaction
            if opened:
                self.conn.execute('BEGIN')
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
        finally:
            if opened:
                self.conn.execute('ROLLBACK')

    def _read_scope(self, principal):
        member = AC.membership_entry(self.CM.authority_state(self.S, self.conn)['membership'], principal)
        return MO.reader_scope(self.conn, self.CM, member.get('scope'), principal=principal)

    def _observe_read(self, principal, model, scope, answer, **extra):
        event = dict(schema=SCHEMA, operation='read', principal=principal, model=model,
                     scope=scope.scope, watermark=answer['watermark'], withheld=dict(scope.withheld),
                     withheld_records=dict(scope.records), **extra)
        self.observations.append(event)
        self.observe(event)
        key = 'feed_pages' if model == 'events' else 'reads'
        self.counts[key] = self.counts.get(key, 0) + 1
        for category, counts in (('entities', scope.withheld), ('records', scope.records)):
            for reason, count in counts.items():
                key = 'withheld_' + category + ':' + reason
                self.counts[key] = self.counts.get(key, 0) + count

    def read(self, model, principal):
        """One published read model, or one metadata read of control_api_models.METADATA_READS (VELDO-0131), for
        `principal`, read on this connection now."""
        if model not in MO.MODELS and model not in MO.METADATA:
            return {'ok': False, 'reason': 'missing_evidence:read_model', 'taxonomy': 'missing_evidence'}
        def produce():
            scope = self._read_scope(principal)
            answer = MO.read_model(self.S, self.conn, model, scope=scope)
            if model == 'repositories':
                # VELDO-0131: the Git identities (setup tables, not entities), metadata only, in this read.
                answer['identities'] = MO.identities(self.conn, self.ids['domain_uuid'], answer['items']['repository'],
                                                     scope)
            self._observe_read(principal, model, scope, answer)
            return answer
        return self._answer(principal, produce)

    def workflow(self, principal, workflow, version=None):
        """VELDO-0132's stored canvas document of one revision (the head when `version` is None)."""
        def produce():
            if self.workflows is None:
                raise WF.Refused('unavailable_service:workflows', 'no workflow service on this authority')
            scope = self._read_scope(principal)
            if not scope.visible('', WF.REVISION_KIND, {'repository': self.workflows.repository}):
                answer = dict(workflow=None, redacted=[], watermark=MO.watermark(self.conn), freshness='live')
                self._observe_read(principal, 'workflow', scope, answer)
                return answer
            document = self.workflows.load(workflow, version)
            served, paths = MO.redact(document)
            answer = dict(served, redacted=paths, watermark=MO.watermark(self.conn), freshness='live')
            self._observe_read(principal, 'workflow', scope, answer)
            return answer
        return self._answer(principal, produce)

    def events(self, principal, after, limit=256):
        """The committed journal records after `after`, oldest first, at most `limit`, for `principal`."""
        def produce():
            scope = self._read_scope(principal)
            answer = self._feed(after, limit, scope=scope, principal=principal)
            self._observe_read(principal, 'events', scope, answer, after=after)
            return answer
        return self._answer(principal, produce)

    def _record_scope(self, principal, member, contract):
        """Why `principal` may not read the record of the run `contract` binds, or None (VELDO-0141, VELDO-0164,
        VELDO-0178): a conversation turn's record by its conversation's owner, a project run's by the member's scope
        over its project, and a run with neither by nobody."""
        source = contract.get('source') if isinstance(contract.get('source'), dict) else {}
        if contract.get('subject_kind') == 'conversation':
            owner = SCOPE.conversation_owner(self.conn, source.get('conversation'))
            return None if owner is not None and owner == principal else OWNER_REFUSAL
        project = (contract.get('reservation') or {}).get('project')
        if project is None:
            return 'unauthorized:out_of_scope'
        return None if self.CM.scope_covers(member.get('scope'), project) else 'unauthorized:out_of_scope'

    def record(self, principal, dispatch_id, after, limit=RECORD_LIMIT):
        """One run's execution record after `after`, at most `limit` lines, for `principal` (VELDO-0141)."""
        turn = {}

        def produce():
            self._authority()
            if not isinstance(dispatch_id, str) or not dispatch_id or type(after) is not int or after < 0:
                raise ER.Refused('invalid_input:record', 'a dispatch and a cursor')
            row = self.conn.execute('SELECT kind, data FROM entities WHERE id=?', ('dispatch:' + dispatch_id,)).fetchone()
            dispatch = json.loads(row[1]) if row and row[0] == 'dispatch' else None
            contract = (dispatch or {}).get('contract') or {}
            reservation = contract.get('reservation') or {}
            member = AC.membership_entry(self.CM.authority_state(self.S, self.conn)['membership'], principal)
            if dispatch is None:
                # An unknown run reads as out of scope to a member whose scope is not universal, as before.
                if not self.CM.scope_covers(member.get('scope'), '*'):
                    raise ER.Refused('unauthorized:out_of_scope', 'the run\'s project is outside the member\'s scope')
                raise ER.Refused('missing_evidence:unknown_run', 'no such run')
            source = contract.get('source') if isinstance(contract.get('source'), dict) else {}
            if contract.get('subject_kind') == 'conversation':
                turn.update(conversation=source.get('conversation'), turn=source.get('turn'))
            refusal = self._record_scope(principal, member, contract)
            if refusal:
                raise ER.Refused(refusal, 'the run is outside the member\'s scope')
            if self.records is None:
                raise ER.Refused('unavailable_service:records', 'no records directory on this authority')
            ended = dispatch.get('state') in ENDED
            committed = dispatch.get('execution_record') if ended else None
            kept = ER.read(self.records, dispatch_id, after, max(1, min(int(limit), RECORD_LIMIT)), committed)
            header = kept['header']
            if header.get('contract_digest') != dispatch.get('contract_digest'):
                raise ER.Refused('unknown_outcome:record_binding', 'the record is bound to another run')
            # VELDO-0178: a header naming a conversation or turn names the ones the run's contract binds.
            if turn and any(key in header and header[key] != turn[key] for key in ('conversation', 'turn')):
                raise ER.Refused('unknown_outcome:record_binding', 'the record is bound to another turn')
            lines = kept['lines']
            run = {'unit': contract.get('unit'), 'station': contract.get('station'),
                   'project': reservation.get('project'), 'account': reservation.get('account'),
                   'host': header.get('host'), 'state': dispatch.get('state'), 'process': dispatch.get('process')}
            if turn:
                run.update(turn)
            return {'schema': RECORD_SCHEMA, 'dispatch_id': dispatch_id, 'after': after, 'run': run,
                    'lines': lines, 'cursor': lines[-1]['seq'] if lines else after, 'total': kept['total'],
                    'ended': ended, 'committed': committed}
        answer = self._answer(principal, produce)
        if turn:
            # VELDO-0178: each read of a turn's record, joined to its conversation; never a line of it.
            refusal = None if answer.get('ok') else answer.get('reason')
            event = dict(schema=SCHEMA, operation='turn_record', principal=principal, dispatch=dispatch_id,
                         conversation=turn['conversation'], turn=turn['turn'], after=after,
                         outcome='served' if refusal is None else 'refused', refusal=refusal,
                         lines=len(answer.get('lines') or ()))
            self.observations.append(event)
            self.observe(event)
            key = 'turn_records' if refusal is None else 'turn_records_refused:' + str(refusal)
            self.counts[key] = self.counts.get(key, 0) + 1
        return answer

    def conversations(self, principal, conversation=None):
        """VELDO-0178 AC1: the reader's own conversations, or one of his with every turn, read now."""
        def produce():
            CVM = _conversation_module()
            mark = MO.watermark(self.conn)
            if conversation is None:
                found = []
                for (raw,) in self.conn.execute('SELECT data FROM entities WHERE kind=? ORDER BY id', (CVM.KIND,)):
                    record = json.loads(raw)
                    if record.get('owner') != principal:
                        continue
                    turns = _turns(self.conn, CVM, record.get('id'))
                    found.append({'id': record.get('id'), 'status': record.get('status'), 'role': record.get('role'),
                                  'version': record.get('version'), 'turns': len(turns),
                                  'last_activity': _last_activity(record, turns)})
                found.sort(key=lambda c: (-(c['last_activity'] or 0), c['id'] or ''))
                answer = {'schema': CONVERSATIONS_SCHEMA, 'conversations': found, 'watermark': mark, 'freshness': 'live'}
                self._observe_conversations(principal, None, 'listed', None, len(found))
                return answer
            if not isinstance(conversation, str) or not conversation:
                raise CVM.Refused('invalid_input:conversation', 'a conversation id')
            row = self.conn.execute('SELECT kind, data FROM entities WHERE id=?',
                                    (CVM.conversation_id(conversation),)).fetchone()
            if not row or row[0] != CVM.KIND:
                self._observe_conversations(principal, conversation, 'refused', 'invalid_input:conversation:unknown')
                raise CVM.Refused('invalid_input:conversation:unknown', 'no such conversation')
            record = json.loads(row[1])
            if record.get('owner') != principal:
                self._observe_conversations(principal, conversation, 'refused', OWNER_REFUSAL)
                raise CVM.Refused(OWNER_REFUSAL, 'the conversation is another member\'s')
            turns = _turns(self.conn, CVM, conversation)
            served = [{'sequence': t.get('sequence'), 'state': t.get('state'),
                       'message': _message_text(self.conn, t.get('intake_command')), 'reply': t.get('reply'),
                       'outcome': t.get('outcome'), 'dispatch_id': t.get('dispatch_id'), 'account': t.get('account'),
                       'created_at': t.get('created_at'), 'ended_at': t.get('ended_at')} for t in turns]
            view = {k: record.get(k) for k in ('id', 'status', 'role', 'version', 'opened_at', 'closed_at', 'project')}
            view.update(turns=len(turns), last_activity=_last_activity(record, turns),
                        attachments=[{k: a.get(k) for k in ('project', 'commit', 'at')}
                                     for a in record.get('attachments') or []])
            self._observe_conversations(principal, conversation, 'served', None, len(served))
            return {'schema': CONVERSATIONS_SCHEMA, 'conversation': view, 'turns': served, 'watermark': mark,
                    'freshness': 'live'}
        return self._answer(principal, produce)

    def _observe_conversations(self, principal, conversation, outcome, refusal, count=0):
        event = dict(schema=SCHEMA, operation='conversations', principal=principal, conversation=conversation,
                     outcome=outcome, refusal=refusal, count=count)
        self.observations.append(event)
        self.observe(event)
        key = 'conversation_reads:' + outcome + ('' if refusal is None else ':' + refusal)
        self.counts[key] = self.counts.get(key, 0) + 1

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

    def _feed(self, after, limit, scope=None, principal=None):
        self._authority()
        if self.publication is None:
            raise WF.Refused('unavailable_service:publication', 'no VELDO-0051 publication on this authority')
        # The publication's own public bounded readers: at most `limit` journal records after `after` with
        # the head, and the events it has published up to its stored watermark. Its refusals keep their names.
        rows, top = self.publication.journal(after, limit)
        head = top['seq']
        listed, published = self.publication.published(after, rows[-1][0] if rows else after)
        by_seq = {}
        for event in listed:
            by_seq.setdefault(event.get('journal_seq'), []).append(event)
        out = []
        for seq, command, digest, changes, committed in rows:
            visible = changes
            # VELDO-0178: a conversation's records are withheld from everyone but its owner, whatever the scope.
            if scope is not None and (not scope.universal or any(
                    scope.owned((change or {}).get('kind'), (change or {}).get('data') or {}) is not None
                    for change in changes.values())):
                visible = {}
                reasons = []
                for eid, change in changes.items():
                    data, kind = (change or {}).get('data') or {}, (change or {}).get('kind')
                    own = data.get('revoked_at') is not None and (
                        (kind == 'membership' and eid == principal)
                        or (kind == CR.KIND and data.get('principal') == principal))
                    reason = None if own else scope.reason(eid, kind, data)
                    if reason is None:
                        visible[eid] = change
                    else:
                        scope.withheld[reason] += 1
                        reasons.append(reason)
                if not visible:
                    scope.records['out_of_scope' if 'out_of_scope' in reasons else
                                  SCOPE.OWNER if SCOPE.OWNER in reasons else 'no_project'] += 1
                    continue
            revocations = {}
            for eid, change in visible.items():
                data = (change or {}).get('data') or {}
                if change.get('kind') in (CR.KIND, 'membership') and data.get('revoked_at') is not None:
                    revocations[eid] = {'kind': change['kind'], 'data': {'credential_id': data.get('credential_id'),
                                                                         'revoked_at': data['revoked_at']}}
            out.append({'seq': seq, 'command_id': command, 'record_digest': digest, 'committed_at': committed,
                        'entities': [{'id': eid, 'kind': (visible[eid] or {}).get('kind')} for eid in sorted(visible)],
                        'revocations': revocations, 'published': [e['id'] for e in by_seq.get(seq, [])
                            if scope is None or scope.universal or e.get('receipt') in visible]})
        cursor = {'cursor': rows[-1][0] if rows else after} if scope is not None and not scope.universal else {}
        return dict({'schema': 'veldo.api_events/v1', 'after': after, 'events': out,
                'watermark': {'seq': head, 'record_digest': top['record_digest']},
                'publication': {'watermark': published, 'head': head, 'pending_records': max(0, head - published),
                                'freshness': 'live' if published == head else 'stale'}}, **cursor)

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
        self._authority()
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
        if a['operation'] in ('send_message', 'make_conversation_project'):
            # VELDO-0180: the conversion command is an intake request too, the edge's signature over it.
            return self.intake.receive('api_request', {'request': derived, 'signature': packet.get('domain_signature')})
        if a['operation'] == 'answer_decision':
            # VELDO-0145 AC3: a member whose scope does not cover the request's projects (for example a scope
            # narrowed after the decision was shown) is refused by that name before settlement is asked, so the
            # answer reads as out of scope rather than as a stale or foreign presentation. Only an assignment is
            # answerable: settlement reads the request from the inbox, which holds no other kind, so an answer naming
            # any other record is refused there (missing_evidence) and nothing settles (suite 113, ui/out-of-scope).
            row = self.conn.execute('SELECT kind, data FROM entities WHERE id=?',
                                    (str(a['parameters'].get('request_id')),)).fetchone()
            if row and row[0] == 'assignment':
                scope = json.loads(row[1]).get('scope')
                if scope is not None and not self.CM.scope_covers(person.get('scope'), scope):
                    raise Refused('unauthorized:out_of_scope', 'the request\'s project is outside the member\'s scope')
            result = self.settlement.api_answer({'answer': derived, 'signature': packet.get('domain_signature')})
            if self.team_routes is not None and result.get('outcome') == 'settled':
                result['team_application'] = self.team_routes.apply_settled(derived['request_id'])
            return result
        if a['operation'] in ('save_capability_configuration', 'propose_team', 'save_default_team'):
            return self._configuration(a, packet)
        provenance = {'channel': AS.CHANNEL, 'edge': self.edge, 'request_id': a['request_id'],
                      'credential_id': a['credential_id'], 'assertion_digest': AS.digest(a)}
        if a['operation'] in (MC.SAVE,) + CV.OPERATIONS:
            return self._mcp(a, packet)
        if a['operation'] == 'save_workflow':
            return self._save_workflow(a)
        if a['operation'] in WORK_OPERATIONS:
            return self._work(a, packet, provenance)
        if a['operation'] in PACING_OPERATIONS:
            return self._pacing(a, provenance)
        if a['operation'] in CONVERSATION_OPERATIONS:
            return self._conversation(a)
        done = self.credentials.revoke_as_member(a['principal'], a['parameters']['credential_id'], provenance)
        if done['refusal']:
            return {'outcome': 'refused', 'reason': '%s:%s' % (CLASSES.get(done['error_class'], 'unknown_outcome'), done['refusal'])}
        return {'outcome': 'revoked'}

    def _configuration(self, a, packet):
        p = a['parameters']
        try:
            if a['operation'] == 'save_capability_configuration':
                if self.configurations is None:
                    raise Refused('unavailable_service:configurations')
                saved = self.configurations.save(p['definition'], principal=a['principal'], base=p['base'],
                                                  command_id=a['request_id'])
                return dict(outcome='saved', revision=saved['revision'], role=saved['role'], digest=saved['digest'])
            if self.team_routes is None:
                raise Refused('unavailable_service:teams')
            return self.team_routes.save(a, packet)
        except Exception as error:
            if not isinstance(getattr(error, 'code', None), str):
                raise
            return dict(outcome='refused', reason=error.code, owner_request=getattr(error, 'owner_request', None))

    def _mcp(self, a, packet):
        p = dict(a['parameters'])
        try:
            if a['operation'] == MC.SAVE:
                if self.catalog is None:
                    raise MC.Refused('unavailable_service:mcp_catalog')
                return self.catalog.save(p['definition'], principal=a['principal'], base=p['base'],
                                         command_id=a['request_id'], session=a['session'])
            if self.mcp_credentials is None:
                raise MC.Refused('unavailable_service:mcp_credentials')
            if a['operation'] == CV.SET:
                value = packet.get('value')
                bound = p.pop('value_digest')
                if (not isinstance(value, str) or not isinstance(bound, str)
                        or not hmac.compare_digest(hashlib.sha256(value.encode()).hexdigest(), bound)):
                    raise MC.Refused('invalid_input:credential_binding')
                p['value'] = value
            return self.mcp_credentials.apply(a['operation'], p, principal=a['principal'],
                                              command_id=a['request_id'], session=a['session'])
        except UnicodeEncodeError:
            return {'outcome': 'refused', 'reason': 'invalid_input:credential_encoding'}
        except (MC.Refused, CV.Refused) as error:
            return {'outcome': 'refused', 'reason': error.code}

    def _work(self, a, packet, provenance):
        """VELDO-0131: the owner's backlog priority, worker stop and account cap, each by its own writer."""
        p, now = a['parameters'], self.clock()
        try:
            if a['operation'] == 'reprioritize_backlog':
                if self.backlog is None:
                    return {'outcome': 'refused', 'reason': 'unavailable_service:backlog'}
                done = self.backlog.apply({'command': AS.domain_request(a), 'signature': packet.get('domain_signature')},
                                          api_assertion=packet)
                if not done.get('ok'):
                    return {'outcome': 'refused', 'reason': _named(done.get('reason'), BL.taxonomy)}
                item = done.get('item') or {}
                return {'outcome': 'reprioritized', 'id': done.get('item_id'), 'version': item.get('version'),
                        'rank': (item.get('priority') or {}).get('rank')}
            if a['operation'] == 'stop_worker':
                if self.dispatches is None:
                    return {'outcome': 'refused', 'reason': 'unavailable_service:dispatches'}
                record = self.dispatches.request_stop(p['dispatch'], p['dispatch_version'], a['principal'], now=now,
                                                      request=a['request_id'], channel=AS.CHANNEL,
                                                      assertion_digest=provenance['assertion_digest'])
                asked = None
                if self.stop is not None:
                    try:
                        asked = bool(self.stop(p['dispatch'], 'owner_stop'))
                    except Exception:  # noqa: BLE001 - an unreachable receiver is recorded as not asked
                        asked = False
                    record = self.dispatches.stop_result(p['dispatch'], asked, now=self.clock())
                return {'outcome': 'stop_requested', 'dispatch': p['dispatch'],
                        'version': self.dispatches.version(p['dispatch']), 'state': (record or {}).get('state'),
                        'stop': {'asked': asked, 'requested_at': ((record or {}).get('stop_request') or {}).get('at')}}
            if self.accounts is None:
                return {'outcome': 'refused', 'reason': 'unavailable_service:accounts'}
            self.accounts.cap(a['request_id'], p['account'], p['concurrency'], base=p['account_version'],
                              principal=a['principal'], now=now, assertion_digest=provenance['assertion_digest'])
            row = self.conn.execute('SELECT version, data FROM entities WHERE id=?',
                                    (AA.entity_id(p['account']),)).fetchone()
            return {'outcome': 'capped', 'account': p['account'], 'version': row[0] if row else None,
                    'concurrency': json.loads(row[1]).get('concurrency') if row else None}
        except Exception as error:  # noqa: BLE001 - each writer's named refusal (its own Refused class)
            code = getattr(error, 'code', None)
            if not isinstance(code, str):
                raise
            classify = DP.taxonomy if a['operation'] == 'stop_worker' else (lambda c: 'missing_authority' if str(c).startswith(
                'missing_authority') else 'invalid_input' if str(c).startswith('invalid_input') else 'unknown_outcome')
            return {'outcome': 'refused', 'reason': _named(code, classify)}

    def _pacing(self, a, provenance):
        """VELDO-0236: the owner's pause, resume or ceiling of one account, control_accounts' own signed operation for
        the verified principal; its command id is the API request id."""
        if self.accounts is None:
            return {'outcome': 'refused', 'reason': 'unavailable_service:accounts'}
        p, kind = a['parameters'], PACING_OPERATIONS[a['operation']]
        common = dict(principal=a['principal'], now=self.clock(), route='ui', provenance=provenance['assertion_digest'])
        try:
            if kind == 'pause':
                event = self.accounts.pause(a['request_id'], p['account'], p['window'], **common)
            elif kind == 'ceiling':
                event = self.accounts.ceiling(a['request_id'], p['account'], p['window'], p['value'], **common)
            else:
                event = self.accounts.resume(a['request_id'], p['account'], **common)
        except Exception as error:  # noqa: BLE001 - control_accounts' named refusal (its own Refused class)
            code = getattr(error, 'code', None)
            if not isinstance(code, str):
                raise
            return {'outcome': 'refused', 'reason': _named(code, lambda c: 'missing_authority' if str(c).startswith(
                'missing_authority') else 'invalid_input' if str(c).startswith('invalid_input') else 'unknown_outcome')}
        return {'outcome': {'pause': 'paused', 'ceiling': 'capped', 'resume': 'resumed'}[kind],
                'account': p['account'], 'window': event.get('window'), 'until': event.get('until'),
                'value': event.get('value'), 'utilization': event.get('utilization'), 'ended': event.get('ended'),
                'words': AA.words(event, self.time_zone)}

    def _conversation(self, a):
        """VELDO-0178: the owner's conversation command, by control_conversation.Conversations, as the verified member
        on the version he saw; its command id is the API request id."""
        p, principal, request = a['parameters'], a['principal'], a['request_id']
        if self.conversation_commands is None:
            return {'outcome': 'refused', 'reason': 'unavailable_service:conversations'}
        CVM = _conversation_module()
        try:
            if a['operation'] == 'open_conversation':
                identity = 'c-' + hashlib.sha256(('api/' + request).encode()).hexdigest()[:20]
                record = self.conversation_commands.open(identity, owner=principal, role=p.get('role') or CVM.DEFAULT_ROLE,
                                                 intake_digest=AS.digest(a), command_id=request)
                outcome = 'opened'
            elif a['operation'] == 'close_conversation':
                record = self.conversation_commands.close(p['conversation'], p['version'], owner=principal, command_id=request)
                outcome = 'closed'
            elif a['operation'] == 'change_conversation_role':
                record = self.conversation_commands.change_role(p['conversation'], p['version'], p['role'], owner=principal,
                                                        command_id=request)
                outcome = 'role_changed'
            else:
                record = self.conversation_commands.attach_project(p['conversation'], p['version'], p['project'],
                                                           owner=principal, command_id=request)
                outcome = 'attached'
        except Exception as error:  # noqa: BLE001 - the conversation authority's named refusal (its own class)
            code = getattr(error, 'code', None)
            if not isinstance(code, str):
                raise
            return {'outcome': 'refused', 'reason': _named(code, lambda c: 'unknown_outcome')}
        record = record or {}
        return {'outcome': outcome, 'conversation': record.get('id'), 'version': record.get('version'),
                'status': record.get('status'), 'role': record.get('role'), 'project': record.get('project')}

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
        return {'send_message': AS.IN.RECORD, 'make_conversation_project': AS.IN.RECORD,
                'answer_decision': AS.ST.API, 'revoke_credential': CR.REVOKE,
                'save_workflow': WF.SAVE, MC.SAVE: MC.SAVE, CV.SET: CV.SET, CV.DELETE: CV.DELETE,
                'save_capability_configuration': 'save_agent_configuration', 'propose_team': 'team_operation',
                'save_default_team': 'save_default_team_revision', 'reprioritize_backlog': BL.OPERATION,
                'stop_worker': DP.OPERATION, 'set_account_cap': AA.OPERATION,
                **{operation: AA.OPERATION for operation in PACING_OPERATIONS},
                **{operation: 'conversation_command' for operation in CONVERSATION_OPERATIONS}}

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
