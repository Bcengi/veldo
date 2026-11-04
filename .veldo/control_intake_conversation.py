"""Conversations at intake (VELDO-0175), mixed into control_intake.Intake.

DECIDED DETERMINISTICALLY. A Telegram reply to any message the factory sent in a conversation (a reply part, a
status line, a command's answer: control_conversation `conversation-message` records) names that conversation, read
before the proposal and question records; an API message names one by its `conversation` field. Either one from
the conversation's owner continues it and nothing else; from anyone else it is refused by name
(missing_authority:conversation_owner), and one naming a closed conversation is refused
(stale_subject:conversation_closed), each with one line to the sender on the channel he wrote on and no turn.

AN API MESSAGE NAMING THE CONVERSATION is its next turn at once (VELDO-0174 AC2's send_conversation_message, run in
intake's own transaction with the source it came from). A TELEGRAM REPLY is the conversation's command when its text
starts with `/role <role>`, `/attach <project>` or `/close`: the owner's set_conversation_role, attach_project or
close_conversation on the conversation's current version with the name exactly as he typed it, answered with one line
naming what changed, never a turn. Any other reply is read by the factory project's PM (control_workflow_cycle_pm),
which reads only the owner's own message: one it reads as one of those commands is that command with the name it
read, and one it reads as none of them is the conversation's next turn. A command that replies to no conversation
message, or names no role of the default team or project in his scope, is refused by name
(invalid_input:conversation_command:<reason>) with one line and nothing changed.

THE PM ROUTES (VELDO-0152 AC3, five now): a new conversation runs VELDO-0174 AC1's open command with the message as
turn 1; an open conversation of the sender's, named by id, takes it as its next turn; either retires the inbox
proposal ROUTED, pointing at the conversation. A route naming a conversation that is not an open one of the
sender's is refused by name (invalid_input:route:conversation) and changes nothing.

Observations name the conversation, its turn or command and how the message was decided, never its text.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('intake_conversation_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CV = _organ('control_conversation')
CC = _organ('control_conversation_channel')
READING_SCHEMA = 'veldo.conversation_reading/v1'
COMMANDS = {'/role': 'role', '/attach': 'attach', '/close': 'close'}
READ_COMMANDS = ('role', 'attach', 'close', 'none')
AWAITING_READING, READ = 'AWAITING_READING', 'READ'
OPENING_WORDS = 12
NEW_CONVERSATION = 'a new conversation'
# The refusals a conversation message is answered with: one line on the channel it came on.
TOLD = ('missing_authority:conversation_owner', 'stale_subject:conversation_closed',
        'invalid_input:conversation_command', 'invalid_input:conversation:unknown')


def typed_command(text):
    """(kind, name) of a typed command: `/role <role>`, `/attach <project>` or `/close`, the name exactly as typed
    after the command word; None for any other text."""
    if not isinstance(text, str):
        return None
    words = text.strip().split(None, 1)
    kind = COMMANDS.get(words[0]) if words else None
    if kind is None:
        return None
    name = words[1].strip() if len(words) > 1 else None
    return kind, name


def conversation_key(proposal_id):
    """The identity of the conversation a new-conversation route opens for one inbox proposal."""
    return 'c-' + hashlib.sha256(str(proposal_id).encode()).hexdigest()[:20]


def opening(conn, identity):
    """The first message's opening words of a conversation, when its first turn came through intake; else None."""
    row = conn.execute('SELECT data FROM entities WHERE id=?', (CV.turn_id(identity, 1),)).fetchone()
    first = json.loads(row[0]) if row else {}
    source = conn.execute('SELECT kind, data FROM entities WHERE id=?', (str(first.get('intake_command')),)).fetchone()
    if not source or source[0] != 'intake_source':
        return None
    words = str(json.loads(source[1]).get('text') or '').split()
    return ' '.join(words[:OPENING_WORDS]) + (' ...' if len(words) > OPENING_WORDS else '')


def open_conversations(conn, principal):
    """VELDO-0175 AC2: the sender's open conversations with their first message's opening words, oldest first."""
    found = [json.loads(raw) for (raw,) in conn.execute('SELECT data FROM entities WHERE kind=?', (CV.KIND,))]
    found = [c for c in found if c.get('owner') == principal and c.get('status') == 'open']
    return [{'id': c['id'], 'opening': opening(conn, c['id'])}
            for c in sorted(found, key=lambda c: (c.get('opened_at') or 0, c['id']))]


def reading_inputs(conn, principal):
    """VELDO-0175 AC4: what the PM may read a reply as naming: the default team's roles and the projects the sender
    may attach (his own, in his scope)."""
    try:
        roles = sorted(((CV.default_team(conn).get('team') or {}).get('roles') or {}))
    except CV.Refused:
        roles = []
    member = CV._row(conn, principal) if isinstance(principal, str) else None
    scope = ((member or {}).get('data') or {}).get('scope') if (member or {}).get('kind') == 'membership' else None
    projects = sorted(p['name'] for p in (json.loads(raw) for (raw,) in conn.execute(
        'SELECT data FROM entities WHERE kind=?', ('project',)))
        if p.get('name') != 'factory' and p.get('owner') == principal and CV.CM.scope_covers(scope, [p.get('name')]))
    return {'roles': roles, 'projects': projects}


def refused_told(code):
    return any(str(code) == t or str(code).startswith(t + ':') for t in TOLD)


class Conversing:
    """The conversation half of the intake (VELDO-0175). Needs `self.conversations` (control_conversation
    Conversations of this service) for commands and new conversations."""

    def _conversations(self):
        """This service's Conversations, built when first needed; None when this intake has none."""
        held = getattr(self, 'conversations', None)
        if callable(held) and not hasattr(held, 'read'):
            try:
                held = held()
            except Exception:  # noqa: BLE001 - an intake without conversations refuses their commands by name
                held = None
            self.conversations = held
        return held

    # -- deciding ------------------------------------------------------------------------------------------------

    def _replied_conversation(self, bot, chat, message):
        """The conversation a Telegram reply continues: the one the replied message was sent in, else None."""
        row = self._entity(CV.sent_id(bot, chat, message))
        if row is None or row['kind'] != CV.SENT_KIND or row['data'].get('kind') == 'refusal':
            return None
        return row['data'].get('conversation')

    def conversation_decision(self, command):
        """How a message naming a conversation is decided: `turn` (an API message), `command` (a Telegram reply that
        starts with a typed command) or `reading` (any other Telegram reply, read by the factory PM)."""
        if command['source_kind'] != 'telegram_message':
            return 'turn'
        return 'command' if typed_command(command['text']) is not None else 'reading'

    def _conversation_plan(self, command, key, source, read, reads):
        """(changes, result) of a message naming a conversation, owned and open, or refused by name."""
        identity, principal = command['conversation'], command['principal']
        cid = CV.conversation_id(identity)
        row = read(cid)
        reads.append(cid)
        if row is None or row['kind'] != CV.KIND:
            raise self.route_refused('invalid_input:conversation:unknown', str(identity))
        if row['data'].get('owner') != principal:
            raise self.route_refused('missing_authority:conversation_owner', str(identity))
        decision = self.conversation_decision(command)
        # A typed command's own close must not refuse the record of it: the command itself refuses a closed one.
        if row['data'].get('status') != 'open' and decision != 'command':
            raise self.route_refused('stale_subject:conversation_closed', str(identity))
        decided_by = 'reply' if command['source_kind'] == 'telegram_message' else 'field'
        changes = {}
        if decision == 'turn':
            turn = self._turn_changes(identity, principal, key, source['content_digest'], read, changes)
            result = {'outcome': 'turn', 'conversation': identity, 'sequence': turn['sequence'],
                      'decided_by': decided_by}
        elif decision == 'reading':
            pid = self._proposal_id(key)
            changes[pid] = {'kind': 'intake_proposal', 'data': {
                'schema': 'veldo.intake_proposal/v1', 'proposal_id': pid, 'proposal': 'reading',
                'state': AWAITING_READING, 'domain': self.domain, 'project': 'factory', 'conversation': identity,
                'principal': principal, 'text': command['text'], 'sources': [key], 'clarifications': [],
                'question_id': None, 'resolves': None, 'resolved_to': None, 'hints': [], 'context': source['context'],
                'decision': {'decided_by': decided_by, 'conversation': identity}, 'route': None}}
            result = {'outcome': 'reading', 'proposal_id': pid, 'conversation': identity, 'decided_by': decided_by}
        else:
            kind, _name = typed_command(command['text'])
            result = {'outcome': 'command', 'conversation': identity, 'command': kind, 'decided_by': 'command'}
        return changes, result

    def _turn_changes(self, identity, principal, source_key, digest, read, changes, opened=None):
        """VELDO-0174 AC2's send_conversation_message, planned in this transaction: the conversation's next turn,
        whose intake command is the source the message came from (so its reply goes where he wrote)."""
        cid = CV.conversation_id(identity)
        before = {cid: opened if opened is not None else read(cid)}
        params = {'operation': CV.MESSAGE, 'conversation': identity, 'principal': principal,
                  'intake_command': source_key, 'intake_digest': digest}
        try:
            planned = CV.transition(self.conn, params, before)
        except CV.Refused as error:
            raise self.route_refused(error.code, error.detail) from None
        changes.update(planned)
        return next(item['data'] for item in planned.values() if item['kind'] == CV.TURN_KIND)

    # -- the typed commands (AC4) -------------------------------------------------------------------------------

    def _steer(self, identity, principal, kind, name, command_key):
        """Send the owner's command on the conversation's current version, with the name as given; (what changed as
        one line, detail). Refused by name: invalid_input:conversation_command:<reason>, or the command's own."""
        conversations = self._conversations()
        if conversations is None:
            raise self.route_refused('unsupported_configuration:conversations')
        current = conversations.read(identity)
        if current is None:
            raise self.route_refused('invalid_input:conversation_command:no_conversation')
        if kind in ('role', 'attach') and not (isinstance(name, str) and name.strip()):
            raise self.route_refused('invalid_input:conversation_command:no_name')
        version = current.get('version')
        command_id = 'conversation-command/' + hashlib.sha256(command_key.encode()).hexdigest()[:32]
        try:
            if kind == 'role':
                try:
                    CV.role_at(self.conn, name)
                except CV.Refused:
                    raise self.route_refused('invalid_input:conversation_command:unknown_role', name) from None
                record = conversations.change_role(identity, version, name, owner=principal, command_id=command_id)
                line = 'Conversation %s now runs as %s (it ran as %s).' % (identity, name, current.get('role'))
            elif kind == 'attach':
                try:
                    member = CV._member(self.conn, principal, self.clock(), owner=True)
                    CV.attach_authority(self.conn, member, current, name)
                except CV.Refused as error:
                    if error.code == 'missing_authority:conversation_owner':
                        raise self.route_refused(error.code) from None
                    raise self.route_refused('invalid_input:conversation_command:unknown_project', name) from None
                record = conversations.attach_project(identity, version, name, owner=principal, command_id=command_id)
                line = 'Project %s is attached to conversation %s.' % (name, identity)
            else:
                record = conversations.close(identity, version, owner=principal, command_id=command_id)
                line = 'Conversation %s is closed.' % identity
        except self.route_refused:
            raise
        except Exception as error:  # noqa: BLE001 - the service's own refusal (its module's class), by its name
            if not isinstance(getattr(error, 'code', None), str):
                raise
            raise self.route_refused(error.code, getattr(error, 'detail', '')) from None
        return line, {'command': kind, 'name': name, 'version': record.get('version'), 'role': record.get('role'),
                      'status': record.get('status'), 'project': record.get('project')}

    def _messages(self):
        if getattr(self, '_conversation_messages', None) is None:
            self._conversation_messages = CC.Messages(self.store, self.conn, self.journal_signer, self.sign,
                                                      self.generation, observe=self._message_event)
        return self._conversation_messages

    def _message_event(self, event):
        self.observe(dict(event, domain=self.domain))

    def _tell(self, where, text, *, kind, conversation=None, sequence=None, ref=None):
        """One line to the sender on Telegram, answering his message at `where`; recorded, never twice."""
        if self.asker is None or not where:
            return {'outcome': 'refused', 'reason': 'unavailable_service'}
        if kind != 'refusal' and sequence is None and conversation is not None:
            turns = [t['sequence'] for t in self._conversation_turns(conversation)]
            sequence = max(turns) if turns else None
        return self._messages().answer(self.asker, where, text, kind=kind, conversation=conversation,
                                       sequence=sequence, ref=ref)

    def _conversation_turns(self, identity):
        return [t for t in self._all(CV.TURN_KIND) if t.get('conversation') == identity]

    @staticmethod
    def _where(command):
        p = command.get('provenance') or {}
        if command.get('source_kind') != 'telegram_message':
            return None
        return {'bot_id': p.get('bot_id'), 'chat_id': p.get('chat_id'), 'message_id': p.get('message_id')}

    @staticmethod
    def refusal_line(code):
        return {'missing_authority:conversation_owner': 'Not done: that conversation is not yours '
                                                        '(missing_authority:conversation_owner).',
                'stale_subject:conversation_closed': 'Not done: that conversation is closed '
                                                     '(stale_subject:conversation_closed).'}.get(
            code, 'Not done: %s.' % code)

    # -- the PM's reading of the owner's words (AC4) ------------------------------------------------------------

    def read(self, document, *, dispatch, proposal_id, version=None):
        """Apply one dispatched PM reading of a conversation reply: none of the commands makes it the conversation's
        next turn; a command is sent as the owner's, answered with one line, and is never a turn."""
        about = dict(proposal_id=proposal_id, dispatch=dispatch)
        held = self.proposal(proposal_id)
        reading = None
        try:
            reading = self._reading_document(document, proposal_id)
            if not held or held.get('state') != AWAITING_READING:
                raise self.route_refused('stale_version')
            source = self._data(held['sources'][0], 'intake_source')
            where = self._where(source['command'])
            outcome, line, detail = 'turn', None, {}
            try:
                # Every reading, `none` included: a conversation no longer his open one (closed after the reply
                # was held, or gone) settles the held message READ by its named refusal, told once, no turn.
                self._owned_open(held['conversation'], held['principal'])
                if reading['command'] != 'none':
                    outcome = 'command'
                    line, detail = self._steer(held['conversation'], held['principal'], reading['command'],
                                               reading.get('name'), held['sources'][0])
            except self.route_refused as error:
                outcome, detail = 'refused', {'refusal': error.code}
                if refused_told(error.code):
                    self._tell(where, self.refusal_line(error.code), kind='refusal',
                               conversation=held['conversation'])
                if error.code in ('stale_version', 'unsupported_configuration:conversations'):
                    raise
            params = dict(reading=dict(proposal_id=proposal_id, dispatch=dispatch, document=reading, outcome=outcome,
                                       detail=detail, version=version))
            changes, reads = self._route_plan(params)
            expected = {eid: (self._entity(eid) or {}).get('version', 0) for eid in set(changes) | set(reads)}
            cid = 'intake-reading:' + hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
            self.store.execute(self.conn, dict(command_id=cid, principal=self.journal_signer, operation='intake_route',
                parameters=params, expected_versions=expected, artifact_digests=[], nonce=cid),
                self.journal_signer, self.sign, self.generation)
        except (self.route_refused, self.store.StoreRefused) as error:
            return dict(self._event('reading', 'refused', error.code, **about), ok=False)
        done = self.proposal(proposal_id)
        if outcome == 'command' and line:
            self._tell(where, line, kind='answer', conversation=held['conversation'], ref=reading['command'])
        self._event('conversation', outcome, None, decided_by='reading', conversation=held['conversation'],
                    sequence=(done.get('turn') or {}).get('sequence'), command=reading['command'],
                    command_refusal=detail.get('refusal'),
                    reply_to=(source['command']['provenance'] or {}).get('reply_to_message_id'), **about)
        return dict(ok=True, outcome=outcome if outcome != 'refused' else (
                        'command_refused' if reading['command'] != 'none' else 'refused'),
                    proposal_id=proposal_id, conversation=held['conversation'], detail=detail,
                    sequence=(done.get('turn') or {}).get('sequence'))

    def _reading_document(self, document, proposal_id):
        fail = self.route_refused
        if (not isinstance(document, dict) or document.get('schema') != READING_SCHEMA
                or document.get('proposal_id') != proposal_id or document.get('command') not in READ_COMMANDS
                or not isinstance(document.get('reason'), str) or not document['reason'].strip()
                or set(document) - {'schema', 'proposal_id', 'command', 'name', 'reason'}
                or (document['command'] in ('role', 'attach')
                    and not (isinstance(document.get('name'), str) and document['name'].strip()))
                or (document['command'] in ('close', 'none') and document.get('name') is not None)):
            raise fail('invalid_input:reading')
        return copy.deepcopy(document)

    def _owned_open(self, identity, principal):
        row = self._entity(CV.conversation_id(identity))
        if row is None or row['kind'] != CV.KIND:
            raise self.route_refused('invalid_input:conversation:unknown')
        if row['data'].get('owner') != principal:
            raise self.route_refused('missing_authority:conversation_owner')
        if row['data'].get('status') != 'open':
            raise self.route_refused('stale_subject:conversation_closed')
        return row

    def _reading_plan(self, params):
        """The reading's writes: the proposal READ, and for `none` the conversation's next turn."""
        fail = self.route_refused
        pid = params.get('proposal_id')
        held = self._entity(pid) if isinstance(pid, str) else None
        if not held or held['kind'] != 'intake_proposal':
            raise fail('invalid_input:reading')
        data = copy.deepcopy(held['data'])
        if data.get('state') != AWAITING_READING or params.get('version') not in (None, held['version']):
            raise fail('stale_version')
        reading = self._reading_document(params.get('document'), pid)
        reads, changes = [pid, data['sources'][0]], {}
        data.update(state=READ, reading=dict(reading, dispatch=params.get('dispatch'), outcome=params.get('outcome'),
                                             detail=params.get('detail') or {}))
        if params.get('outcome') == 'turn':
            row = self._owned_open(data['conversation'], data['principal'])
            source = self._data(data['sources'][0], 'intake_source')
            turn = self._turn_changes(data['conversation'], data['principal'], data['sources'][0],
                                      source['content_digest'], self._entity, changes, opened=row)
            data.update(resolved_to=CV.turn_id(data['conversation'], turn['sequence']),
                        turn={'conversation': data['conversation'], 'sequence': turn['sequence']})
            reads.append(CV.conversation_id(data['conversation']))
        changes[pid] = {'kind': 'intake_proposal', 'data': data}
        return changes, reads

    # -- the PM's conversation routes (AC2) ---------------------------------------------------------------------

    def _conversation_route(self, doc, data, pid, principal, changes, reads):
        """A new conversation (opened with the message as turn 1) or an open one of the sender's (its next turn)."""
        source_key = data['sources'][0]
        source = self._data(source_key, 'intake_source')
        reads.append(source_key)
        if doc['route'] == 'new_conversation':
            conversations = self._conversations()
            if conversations is None:
                raise self.route_refused('unsupported_configuration:conversations')
            identity = conversation_key(pid)
            cid = CV.conversation_id(identity)
            if self._entity(cid) is not None:
                raise self.route_refused('stale_version')
            params = {'operation': CV.OPEN, 'conversation': identity, 'principal': principal,
                      'role': CV.DEFAULT_ROLE, 'domain': conversations.domain, 'intake_digest': source['content_digest'],
                      'directory': conversations.directory(identity)}
            try:
                opened = CV.transition(self.conn, params, {})
            except CV.Refused as error:
                raise self.route_refused(error.code, error.detail) from None
            changes.update(opened)
            row = dict(opened[cid], version=0)
        else:
            identity = doc.get('conversation')
            cid = CV.conversation_id(identity) if isinstance(identity, str) else None
            row = self._entity(cid) if cid else None
            if (not row or row['kind'] != CV.KIND or row['data'].get('owner') != principal
                    or row['data'].get('status') != 'open'):
                raise self.route_refused('invalid_input:route:conversation')
        reads.append(cid)
        turn = self._turn_changes(identity, principal, source_key, source['content_digest'], self._entity, changes,
                                  opened=row)
        data.update(state='ROUTED', resolved_to=cid, conversation=identity,
                    turn={'conversation': identity, 'sequence': turn['sequence']})
        return identity

    def _made_conversation(self, held):
        """After a new-conversation route committed: its directory and workspace, made 0700."""
        record = (self._entity(CV.conversation_id(held.get('conversation'))) or {}).get('data') or {}
        if record and CV.workspace_of(record):
            CV.make_workspace(record)
            self._event('conversation', 'opened', None, decided_by='route', conversation=record['id'],
                        sequence=1, proposal_id=held.get('proposal_id'))

    def conversation_metrics(self):
        """Conversation messages by how they were decided, typed commands by kind and outcome, conversations opened
        by route, and replies to a closed or foreign conversation refused."""
        decided, commands, opened, refused = {}, {}, {}, {}
        for e in self.observations:
            if (e.get('operation') == 'conversation' and e.get('outcome') in ('turn', 'reading', 'command')
                    and e.get('decided_by') != 'reading'):
                key = e.get('decided_by') or 'unknown'
                decided[key] = decided.get(key, 0) + 1
            if e.get('operation') == 'conversation' and e.get('command') and e.get('outcome') in ('command', 'refused'):
                key = '%s/%s' % (e['command'], 'applied' if e['outcome'] == 'command'
                                 else e.get('refusal') or e.get('command_refusal'))
                commands[key] = commands.get(key, 0) + 1
            if e.get('operation') == 'conversation' and e.get('outcome') == 'opened':
                opened['new_conversation'] = opened.get('new_conversation', 0) + 1
            if e.get('operation') == 'route' and (e.get('route') or {}).get('route') == 'open_conversation' \
                    and not e.get('refusal'):
                opened['open_conversation'] = opened.get('open_conversation', 0) + 1
            why = e.get('refusal') or e.get('command_refusal')
            if e.get('operation') == 'conversation' and why in ('missing_authority:conversation_owner',
                                                                 'stale_subject:conversation_closed'):
                refused[why] = refused.get(why, 0) + 1
        return {'decided': decided, 'commands': commands, 'routes': opened, 'refused': refused}
