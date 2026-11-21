"""Durable conversations and ordered turns beside project work (VELDO-0174).

A conversation is authority data, not a project.  It has no repository, backlog,
charter or trunk.  Owner commands create and close its versioned record and append
turns.  The installed service changes a waiting turn to dispatched only after a
VELDO-0039 conversation dispatch has been prepared.  The receiver then rechecks the
same record before accepting the launch.

VELDO-0177: each conversation has its own workspace, `workspace` under its directory, made by the open command;
it is the engine's working directory for every turn, and the receiver refuses a turn whose contract names any other
(binding_mismatch:conversation_workspace) before anything is spawned.  An attach of a project the owner's scope
covers takes a fresh isolated clone of the project's repository at its trunk commit, with its whole history, under
the workspace's `projects/<project>` directory (control_clone.conversation_clone): no remote, no Git identity, no
publication credential.  Attaching again takes a new clone beside the old one.

VELDO-0176: the factory keeps each conversation's engine session itself.  After each turn the receiver captures the
session state the engine wrote in the account profile (Claude Code's transcript of the session the result event
names, under the profile's projects directory for the workspace; Codex's rollout file of the thread under the
profile's sessions directory), keeps it under the conversation's `sessions` directory at mode 0600, removes it from
the profile and reports it; the turn record binds its digest (`session`).  The next turn on the same engine resumes
the newest held session of that engine on whichever account the pool picks: the receiver checks the capture against
its turn record (binding_mismatch:conversation_session, never replaced by a rendering), places it at the same
relative place in that account's profile and launches with the engine's qualified resume option; an engine that
reports another session is stopped by name (binding_mismatch:conversation_resume).  A turn stopped at its account's
limit returns to waiting with its capture (`limited`), and is dispatched again under a new dispatch identity.  The
first turn on an engine that holds no session starts from `render`: the earlier turns as their redacted execution
records keep them, the newest whole turns that fit the engine's qualified input bound, after one line naming how
many were left out.

VELDO-0175: a completed turn keeps its reply on its record (`reply`): its engine's final result text, read from the
redacted execution record its exit committed (`final_reply`).  Every message the factory sends in a conversation (a
reply part, a status line, a command's answer) is recorded by `record_conversation_message` with its bot, chat and
message id, bound to the conversation and turn (`conversation-message:<bot>:<chat>:<message>`), so a Telegram reply to
any of them continues the conversation (control_intake); a reply part or status line is also listed on its turn
(`sent`), and a line answering one of the owner's messages is kept under that message
(`conversation-answer:<bot>:<chat>:<message>`), so a redelivered message is never answered twice.

VELDO-0180: the owner's typed command making the conversation a project's work points it at that project
(`record_conversation_project`, planned in intake's routing transaction, the owner's own): `projects` lists each
project, route, conversion proposal and command; the conversation stays open.  `records` is where the conversation
receiver keeps its turns' execution records (its state root's, unless the service names another), which the
conversion's rendering reads.

Conversation worker reservations use the shared subscription-account records and
the same account-pool selection order.  Their context names the conversation as the
unit and deliberately carries no project or repository.  They are visible to the
ordinary pool's active-run count and use the shared reservation ledger's policies.
"""
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('conversation_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _organ('control_store')
CM = _organ('control_membership')
AC = CM.AC
POOL = _organ('control_account_pool')
RES = _organ('control_reservations')
CFG = _organ('control_agent_config')

SCHEMA = 'veldo.conversation/v1'
TURN_SCHEMA = 'veldo.conversation_turn/v1'
OPERATION = 'conversation_command'
KIND = 'conversation'
TURN_KIND = 'conversation_turn'
OPEN = 'open_conversation'
CLOSE = 'close_conversation'
ROLE = 'change_conversation_role'
ATTACH = 'attach_conversation_project'
MESSAGE = 'send_conversation_message'
DISPATCH = 'dispatch_conversation_turn'
END = 'end_conversation_turn'
DEFER = 'wait_conversation_turn'
# VELDO-0176 AC2: a question the factory asked about a turn, or a notice it gave the owner, kept on the turn record.
NOTE = 'note_conversation_turn'
# VELDO-0180: the conversation points at the project its owner's typed command made it the work of.
POINT = 'record_conversation_project'
OWNER_OPERATIONS = (OPEN, CLOSE, ROLE, ATTACH, MESSAGE)
STATUSES = ('open', 'closed')
TURN_STATES = ('waiting', 'dispatched', 'ended')
DEFAULT_ROLE = 'assistant'
HEAD = 'default-team:head'
DEFAULT_PREFIX = 'default-team:'
WORKER_KIND = 'subscription_reservation'
# VELDO-0231: a running agent's flag to the lead, and its run's flag summary.
FLAG = 'flag_conversation'
FLAG_KIND = 'conversation_flag'
FLAG_SUMMARY_KIND = 'run_flag_summary'
FLAG_SCHEMA = 'veldo.conversation_flag/v1'
FLAG_TEXT = 2000
FLAG_WINDOW = 60
FLAG_LIMIT = 20
RATE_LIMITED = 'rate_limited:run_flag'
UNDELIVERED = 'undelivered:no_conversation'
# VELDO-0175: every message the factory sent in a conversation, and the line that answered one of the owner's.
SENT = 'record_conversation_message'
SENT_KIND = 'conversation_message'
ANSWER_KIND = 'conversation_answer'
SENT_SCHEMA = 'veldo.conversation_message/v1'
SENT_KINDS = ('reply', 'status', 'answer', 'refusal')
OPERATIONS = OWNER_OPERATIONS + (DISPATCH, DEFER, END, FLAG, NOTE, SENT, POINT)
# VELDO-0177: the workspace under the conversation's directory, the attached projects' clones under it, and the
# receiver's refusal of a turn launched anywhere else.
WORKSPACE = 'workspace'
PROJECTS = 'projects'
WORKSPACE_MISMATCH = 'binding_mismatch:conversation_workspace'
# VELDO-0176: the held sessions under the conversation's directory, the refusals by name, the turn a limit stopped.
SESSIONS = 'sessions'
SESSION_MISMATCH = 'binding_mismatch:conversation_session'
RESUME_MISMATCH = 'binding_mismatch:conversation_resume'
LIMITED = 'account_limit'
SESSION_FIELDS = ('engine', 'session_id', 'relative', 'capture', 'digest', 'account', 'dispatch_id')
LIMIT_NOTICE = ('The previous run of this turn stopped at an account limit; continue from where it stopped.')
LEFT_OUT = 'Earlier turns left out of this history: %d.'
# VELDO-0176 AC2: the owner's assistant role on the other engine (VELDO-0177 AC2), for the wait-or-move question.
OTHER_ROLE = {'claude_code': 'assistant_codex', 'codex': 'assistant'}


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def conversation_id(identity):
    return 'conversation:' + str(identity)


def turn_id(identity, sequence):
    return 'conversation-turn:%s:%d' % (identity, sequence)


def sent_id(bot, chat, message):
    """VELDO-0175 AC1: the record of one message the factory sent in a conversation."""
    return 'conversation-message:%s:%s:%s' % (bot, chat, message)


def answer_id(bot, chat, message):
    """VELDO-0175: the record of the one line that answered the owner's message `message`."""
    return 'conversation-answer:%s:%s:%s' % (bot, chat, message)


def flag_summary_id(dispatch_id):
    return 'run-flags:' + str(dispatch_id)


def flag_id(dispatch_id, number):
    return 'conversation-flag:%s:%d' % (dispatch_id, number)


def workspace_of(record):
    """VELDO-0177 AC1: a conversation's own workspace, `workspace` under its directory; None without a directory."""
    directory = (record or {}).get('directory')
    return os.path.join(directory, WORKSPACE) if _text(directory) and os.path.isabs(directory) else None


def make_workspace(record):
    """VELDO-0177 AC1: the conversation's directory and its workspace, made 0700 once its open command committed."""
    workspace = workspace_of(record)
    for path in (record['directory'], workspace):
        os.makedirs(path, mode=0o700, exist_ok=True)
        os.chmod(path, 0o700)
    return workspace


def clone_path(record, project, number):
    """VELDO-0177 AC3: where the `number`th attach of `project` puts its clone: under the workspace's
    projects/<project> directory, one directory per attach, so attaching again takes a new clone beside the old."""
    return os.path.join(workspace_of(record), PROJECTS, project, str(number))


def project_source(conn, domain, project):
    """VELDO-0177 AC3: (repository uuid, bound path) of a project's execution repository, (None, None) for a project
    that names none; refused by name when it names one this store has no readable binding for."""
    row = _row(conn, 'project:' + project) if _text(project) else None
    repository = ((row or {}).get('data') or {}).get('execution_repository') if row and row['kind'] == 'project' else None
    if not _text(repository):
        return None, None
    path = S.bound_repository(conn, domain, repository)
    if not path or not os.path.isdir(path):
        raise Refused('missing_evidence:project_repository', str(project))
    return repository, path


def conversation_directory(state_root, identity):
    """A conversation's directory under the factory state root, named by its identity's digest."""
    return os.path.join(os.path.abspath(str(state_root)), 'conversations', hashlib.sha256(identity.encode()).hexdigest())


def lead_conversation(conn, conversation=None, project=None):
    """VELDO-0231 AC1: the conversation a run's flag goes to: the run's own conversation for a conversation turn,
    else the open conversation attached to the run's project, the most recently opened when several are; None."""
    if _text(conversation):
        row = _conversation(conn, conversation)
        return conversation if row is not None else None
    if not _text(project):
        return None
    attached = [json.loads(raw) for (raw,) in conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,))]
    attached = [c for c in attached if c.get('status') == 'open' and c.get('project') == project]
    if not attached:
        return None
    return max(attached, key=lambda c: (c.get('opened_at') or 0, str(c.get('id'))))['id']


def _flag(conn, params, before, now):
    """flag_conversation (VELDO-0231 AC1, AC4): one flag read from a running agent's stream, written by the
    service principal. The per-run window is the summary's: a run's first flag at once, after it at most one per
    FLAG_WINDOW seconds and FLAG_LIMIT per run; a flag beyond that is counted, not written."""
    _member(conn, params.get('principal'), now, service=True)
    dispatch_id, number, at = params.get('dispatch_id'), params.get('number'), params.get('at')
    if (not _text(dispatch_id) or type(number) is not int or number < 1 or not _number(at)
            or not _text(params.get('engine')) or not _text(params.get('means'))
            or not isinstance(params.get('text'), str)):
        raise Refused('invalid_input:conversation_flag')
    sid = flag_summary_id(dispatch_id)
    summary = copy.deepcopy((before.get(sid) or {}).get('data') or {
        'schema': FLAG_SCHEMA, 'dispatch_id': dispatch_id, 'read': 0, 'delivered': 0, 'undelivered': 0,
        'held_back': 0, 'held_since_last': 0, 'last_at': None})
    summary['read'] += 1
    if summary['read'] != number:
        raise Refused('stale_subject:conversation_flag')
    written = summary['delivered'] + summary['undelivered']
    if written and (written >= FLAG_LIMIT or at - summary['last_at'] < FLAG_WINDOW):
        summary['held_back'] += 1
        summary['held_since_last'] += 1
        summary['outcome'] = RATE_LIMITED
        return {sid: {'kind': FLAG_SUMMARY_KIND, 'data': summary}}
    target = lead_conversation(conn, params.get('conversation'), params.get('project'))
    text = params['text'][:FLAG_TEXT]
    record = {'schema': FLAG_SCHEMA, 'dispatch_id': dispatch_id, 'number': number, 'conversation': target,
              'project': params.get('project'), 'engine': params['engine'], 'means': params['means'],
              'text': text, 'length': len(params['text']), 'synchronous': bool(params.get('synchronous')),
              'account': params.get('account'), 'sequence': params.get('sequence'),
              'read_at': params.get('read_at'), 'at': at,
              'held_back_since_last': summary['held_since_last'],
              'refusal': None if target is not None else UNDELIVERED}
    summary['delivered' if target is not None else 'undelivered'] += 1
    summary.update(held_since_last=0, last_at=at, outcome='delivered' if target is not None else UNDELIVERED)
    return {sid: {'kind': FLAG_SUMMARY_KIND, 'data': summary},
            flag_id(dispatch_id, number): {'kind': FLAG_KIND, 'data': record}}


def _row(conn, identity):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}


def _member(conn, principal, now, *, owner=False, service=False):
    row = _row(conn, principal) if _text(principal) else None
    entry = dict((row or {}).get('data') or {}, principal=principal)
    active, why = AC.active_member(entry if row and row['kind'] == 'membership' else None, now)
    if not active:
        raise Refused('missing_authority:conversation_owner' if owner else 'missing_authority:conversation_service',
                      why or 'inactive member')
    if owner and (entry.get('principal_type') != 'person' or 'project_owner' not in (entry.get('roles') or [])):
        raise Refused('missing_authority:conversation_owner')
    if service and (entry.get('principal_type') != 'service'
                    or 'reservation_service' not in (entry.get('roles') or [])):
        raise Refused('missing_authority:conversation_service')
    return entry


def _conversation(conn, identity):
    row = _row(conn, conversation_id(identity))
    return row if row and row['kind'] == KIND else None


def _turn(conn, identity, sequence):
    row = _row(conn, turn_id(identity, sequence))
    return row if row and row['kind'] == TURN_KIND else None


def default_team(conn):
    head = _row(conn, HEAD)
    revision = ((head or {}).get('data') or {}).get('revision')
    row = _row(conn, DEFAULT_PREFIX + str(revision)) if type(revision) is int else None
    if not row or row['kind'] != 'default_team_revision':
        raise Refused('missing_evidence:default_team')
    return row['data']


def role_at(conn, name):
    """The named role of the current accepted default team and its immutable capability revision."""
    saved = default_team(conn)
    role = (((saved.get('team') or {}).get('roles') or {}).get(name))
    if not isinstance(role, dict):
        raise Refused('invalid_input:conversation_role:' + str(name))
    reference = role.get('capability_configuration')
    if (not isinstance(reference, dict) or set(reference) != {'role', 'revision'}
            or reference.get('role') != name or type(reference.get('revision')) is not int):
        raise Refused('missing_evidence:conversation_role:' + str(name))
    candidates = []
    for (data,) in conn.execute('SELECT data FROM entities WHERE kind=?', (CFG.KINDS[0],)):
        value = json.loads(data)
        if value.get('role') == name and value.get('revision') == reference['revision']:
            candidates.append(value)
    if len(candidates) != 1:
        raise Refused('missing_evidence:conversation_role:' + str(name))
    revision = candidates[0]
    if CFG.digest({k: v for k, v in revision.items() if k != 'digest'}) != revision.get('digest'):
        raise Refused('missing_evidence:agent_digest')
    return copy.deepcopy(role), copy.deepcopy(revision), saved['revision']


def attach_authority(conn, member, record, project):
    """VELDO-0177 AC3: the project an attach names, refused by name unless it is the conversation owner's own and in
    the owner's scope; the same checks the transition applies, run before anything of its repository is read."""
    target = _row(conn, 'project:' + project) if _text(project) else None
    if not target or target['kind'] != 'project':
        raise Refused('invalid_input:conversation_project')
    if target['data'].get('owner') != record.get('owner'):
        raise Refused('missing_authority:project')
    if not CM.scope_covers(member.get('scope'), [project]):
        raise Refused('missing_authority:project')
    return target


def _int(value):
    return type(value) is int


def _sent(conn, params, before, now):
    """record_conversation_message (VELDO-0175): one message the factory sent, as the platform confirmed it: a reply
    part or status line of a turn, the answer to one of the owner's commands, or a refusal line. Every one but a
    refusal is bound to its conversation and turn for a reply to continue it; a reply part or status line is listed on
    its turn; a line answering one of his messages is kept under that message. Written by the journal signer."""
    kind, identity, sequence = params.get('kind'), params.get('conversation'), params.get('sequence')
    bot, chat, message = params.get('bot_id'), params.get('chat_id'), params.get('message_id')
    if (kind not in SENT_KINDS or not all(_int(v) for v in (bot, chat, message, params.get('date')))
            or (params.get('answers') is not None and not _int(params['answers']))
            or (params.get('reply_to') is not None and not _int(params['reply_to']))):
        raise Refused('invalid_input:conversation_message')
    record = {'schema': SENT_SCHEMA, 'kind': kind, 'conversation': identity, 'sequence': sequence,
              'part': params.get('part'), 'parts': params.get('parts'), 'ref': params.get('ref'), 'bot_id': bot,
              'chat_id': chat, 'message_id': message, 'date': params['date'], 'reply_to': params.get('reply_to'),
              'answers': params.get('answers'), 'at': now}
    changes = {}
    if kind != 'refusal':
        if not _text(identity) or not before.get(conversation_id(identity)):
            raise Refused('invalid_input:conversation:unknown')
        mid = sent_id(bot, chat, message)
        if before.get(mid) or _row(conn, mid):
            raise Refused('stale_subject:conversation_message')
        changes[mid] = {'kind': SENT_KIND, 'data': record}
    if kind in ('reply', 'status'):
        tid = turn_id(identity, sequence) if _int(sequence) else None
        current = before.get(tid) if tid else None
        if not current or current.get('kind') != TURN_KIND:
            raise Refused('invalid_input:conversation_turn:unknown')
        turn = copy.deepcopy(current['data'])
        turn.setdefault('sent', []).append({k: record[k] for k in ('kind', 'ref', 'part', 'parts', 'chat_id',
                                                                   'message_id', 'date')})
        changes[tid] = {'kind': TURN_KIND, 'data': turn}
    if record['answers'] is not None:
        aid = answer_id(bot, chat, record['answers'])
        if before.get(aid) or _row(conn, aid):
            raise Refused('stale_subject:conversation_answer')
        changes[aid] = {'kind': ANSWER_KIND, 'data': record}
    return changes


def transition(conn, params, before):
    operation, now = params.get('operation'), time.time()
    identity, principal = params.get('conversation'), params.get('principal')
    if operation == FLAG:
        return _flag(conn, params, before, now)
    if operation == SENT:
        return _sent(conn, params, before, now)
    if operation not in OPERATIONS or not _text(identity):
        raise Refused('invalid_input:conversation')
    cid = conversation_id(identity)
    current = before.get(cid)
    record = copy.deepcopy((current or {}).get('data') or {})
    if operation == OPEN:
        _member(conn, principal, now, owner=True)
        if current is not None:
            raise Refused('stale_subject:conversation_exists')
        role = params.get('role') or DEFAULT_ROLE
        role_at(conn, role)
        directory = params.get('directory')
        if not _text(directory) or not os.path.isabs(directory):
            raise Refused('invalid_input:conversation_directory')
        data = {'schema': SCHEMA, 'id': identity, 'domain': params.get('domain'), 'owner': principal,
                'role': role, 'status': 'open', 'version': 1, 'intake_digest': params.get('intake_digest'),
                'directory': directory, 'opened_at': now, 'closed_at': None}
        if not _text(data['domain']) or not _text(data['intake_digest']):
            raise Refused('invalid_input:conversation')
        return {cid: {'kind': KIND, 'data': data}}
    if not current or current.get('kind') != KIND:
        raise Refused('invalid_input:conversation:unknown')
    if operation == POINT:
        _member(conn, principal, now, owner=True)
        if record.get('owner') != principal:
            raise Refused('missing_authority:conversation_owner')
        if record.get('status') != 'open':
            raise Refused('stale_subject:conversation_closed')
        if not all(_text(params.get(k)) for k in ('project', 'route', 'proposal', 'command')):
            raise Refused('invalid_input:conversation_project')
        record.setdefault('projects', []).append({k: params[k] for k in ('project', 'route', 'proposal', 'command')}
                                                 | {'at': now})
        record['version'] += 1
        return {cid: {'kind': KIND, 'data': record}}
    if operation in OWNER_OPERATIONS:
        member = _member(conn, principal, now, owner=True)
        if record.get('owner') != principal:
            raise Refused('missing_authority:conversation_owner')
    else:
        _member(conn, principal, now, service=True)
    if operation in (CLOSE, ROLE, ATTACH):
        if type(params.get('version')) is not int or params['version'] != record.get('version'):
            raise Refused('stale_version')
        if record.get('status') != 'open':
            raise Refused('stale_subject:conversation_closed')
        if operation == CLOSE:
            record.update(status='closed', closed_at=now)
        elif operation == ROLE:
            role = params.get('role')
            if not _text(role):
                raise Refused('invalid_input:conversation_role')
            role_at(conn, role)
            record['role'] = role
        else:
            project = params.get('project')
            target = attach_authority(conn, member, record, project)
            record['project'] = project
            # VELDO-0177 AC3: the clone this attach takes, at the trunk commit read for it, beside every earlier one.
            repository = target['data'].get('execution_repository')
            if _text(repository):
                commit, path = params.get('commit'), params.get('clone')
                earlier = [a for a in record.get('attachments') or [] if a.get('project') == project]
                expected = clone_path(record, project, len(earlier) + 1) if workspace_of(record) else None
                if (not isinstance(commit, str) or len(commit) not in (40, 64)
                        or any(c not in '0123456789abcdef' for c in commit) or path != expected):
                    raise Refused('invalid_input:conversation_attach')
                record.setdefault('attachments', []).append(
                    {'project': project, 'repository': repository, 'commit': commit, 'clone': path, 'at': now})
        record['version'] += 1
        return {cid: {'kind': KIND, 'data': record}}
    if operation == MESSAGE:
        if record.get('status') != 'open':
            raise Refused('stale_subject:conversation_closed')
        intake = params.get('intake_command')
        digest = params.get('intake_digest')
        if not _text(intake) or not _text(digest):
            raise Refused('invalid_input:conversation_message')
        sequences = [value.get('sequence', 0) for (raw,) in conn.execute(
            'SELECT data FROM entities WHERE kind=?', (TURN_KIND,))
            if (value := json.loads(raw)).get('conversation') == identity]
        sequence = max(sequences, default=0) + 1
        tid = turn_id(identity, sequence)
        if tid in before or _row(conn, tid):
            raise Refused('stale_subject:conversation_turn')
        journal_seq = conn.execute('SELECT COALESCE(MAX(seq), 0) + 1 FROM journal').fetchone()[0]
        turn = {'schema': TURN_SCHEMA, 'conversation': identity, 'sequence': sequence,
                'intake_command': intake, 'intake_digest': digest, 'state': 'waiting', 'created_at': now,
                'arrival': journal_seq, 'dispatch_id': None, 'role_revision': None, 'account': None,
                'receiver': None, 'outcome': None, 'ended_at': None}
        return {tid: {'kind': TURN_KIND, 'data': turn}}
    sequence = params.get('sequence')
    if type(sequence) is not int or sequence < 1:
        raise Refused('invalid_input:conversation_turn')
    tid = turn_id(identity, sequence)
    current_turn = before.get(tid)
    turn = copy.deepcopy((current_turn or {}).get('data') or {})
    if not current_turn or current_turn.get('kind') != TURN_KIND:
        raise Refused('invalid_input:conversation_turn:unknown')
    if operation == DISPATCH:
        if record.get('status') != 'open':
            raise Refused('stale_subject:conversation_closed')
        retry = turn.get('state') == 'dispatched'
        if retry:
            prior = _row(conn, 'dispatch:' + str(turn.get('dispatch_id')))
            if not prior or prior.get('kind') != 'dispatch' or prior['data'].get('state') != 'refused':
                raise Refused('stale_subject:conversation_turn_active')
        elif turn.get('state') != 'waiting':
            raise Refused('stale_subject:conversation_turn_active')
        if not retry:
            active = conn.execute("SELECT data FROM entities WHERE kind=?", (TURN_KIND,)).fetchall()
            if any((value := json.loads(r[0])).get('conversation') == identity
                   and value.get('state') == 'dispatched' for r in active):
                raise Refused('stale_subject:conversation_turn_active')
        dispatch_id = params.get('dispatch_id')
        role_revision = params.get('role_revision')
        if not _text(dispatch_id) or type(role_revision) is not int or role_revision < 1:
            raise Refused('invalid_input:conversation_dispatch')
        turn.setdefault('attempts', []).append({'dispatch_id': dispatch_id, 'account': params.get('account'),
                                                'at': now})
        turn.update(state='dispatched', dispatch_id=dispatch_id, role_revision=role_revision,
                    account=params.get('account'), receiver=params.get('receiver'), dispatched_at=now)
        return {tid: {'kind': TURN_KIND, 'data': turn}}
    if operation == NOTE:
        note = params.get('note')
        if not isinstance(note, dict) or note.get('kind') not in ('question', 'notice') or not _text(note.get('ref')):
            raise Refused('invalid_input:conversation_note')
        key = 'questions' if note['kind'] == 'question' else 'notices'
        kept = turn.setdefault(key, [])
        same = next((item for item in kept if item.get('ref') == note['ref']), None)
        if same is None:
            kept.append(dict(note, at=now))
        else:
            same.update(note)
        return {tid: {'kind': TURN_KIND, 'data': turn}}
    # VELDO-0176: the capture this dispatch produced, bound to the turn by its digest, and how the turn started.
    session = _session_param(record, params.get('session'))
    started = params.get('start')
    if started is not None and not isinstance(started, dict):
        raise Refused('invalid_input:conversation_start')
    if operation == DEFER:
        if turn.get('state') != 'dispatched' or turn.get('dispatch_id') != params.get('dispatch_id'):
            raise Refused('stale_subject:conversation_turn')
        prior = _row(conn, 'dispatch:' + str(turn.get('dispatch_id')))
        limited = params.get('refusal') == LIMITED
        # VELDO-0176 AC2: a run that exited at its account's limit returns its turn to waiting, to run again under a
        # new dispatch identity; any other deferral follows a dispatch its receiver refused.
        allowed = ('exited',) if limited else ('refused',)
        if not prior or prior.get('kind') != 'dispatch' or prior['data'].get('state') not in allowed:
            raise Refused('stale_subject:conversation_turn_active')
        turn.update(state='waiting', last_refusal=params.get('refusal'))
        if limited:
            limit = params.get('limit') if isinstance(params.get('limit'), dict) else {}
            turn['limited'] = {'dispatch_id': turn['dispatch_id'], 'account': turn.get('account'),
                               'window': limit.get('window'), 'reset_at': limit.get('reset_at'),
                               'decision': params.get('decision'), 'question': params.get('question'), 'at': now}
            turn.setdefault('limits', []).append(dict(turn['limited']))
        _bind_session(turn, session, started)
        return {tid: {'kind': TURN_KIND, 'data': turn}}
    stopped_waiting = (turn.get('state') == 'waiting' and isinstance(turn.get('limited'), dict)
                       and turn['limited'].get('dispatch_id') == params.get('dispatch_id'))
    if not stopped_waiting and (turn.get('state') != 'dispatched'
                                or turn.get('dispatch_id') != params.get('dispatch_id')):
        raise Refused('stale_subject:conversation_turn')
    outcome = params.get('outcome')
    if not _text(outcome):
        raise Refused('invalid_input:conversation_outcome')
    turn.update(state='ended', outcome=outcome, ended_at=now)
    # VELDO-0175 AC3: the turn's reply, its engine's final result text, kept on the record as the engine wrote it.
    if 'reply' in params:
        reply = params['reply']
        if reply is not None and not isinstance(reply, str):
            raise Refused('invalid_input:conversation_reply')
        turn['reply'] = reply
        turn['reply_digest'] = None if reply is None else 'sha256:' + hashlib.sha256(reply.encode()).hexdigest()
    _bind_session(turn, session, started)
    return {tid: {'kind': TURN_KIND, 'data': turn}}


def sessions_of(record):
    """VELDO-0176 AC1: where a conversation's held sessions are kept, `sessions` under its directory."""
    directory = (record or {}).get('directory')
    return os.path.join(directory, SESSIONS) if _text(directory) and os.path.isabs(directory) else None


def _session_param(record, value):
    """The capture a turn's dispatch reports, checked by shape: its engine, the session id the engine reported, the
    place relative to the account profile, the capture under this conversation's sessions directory and its digest."""
    if value is None:
        return None
    root = sessions_of(record)
    if (not isinstance(value, dict) or not all(_text(value.get(k)) for k in SESSION_FIELDS) or root is None
            or os.path.isabs(value['relative']) or '..' in Path(value['relative']).parts
            or os.path.dirname(os.path.normpath(value['capture'])) != os.path.join(root, value['engine'])
            or not value['digest'].startswith('sha256:') or len(value['digest']) != 71):
        raise Refused('invalid_input:conversation_session')
    return {k: value[k] for k in SESSION_FIELDS}


def _bind_session(turn, session, started):
    """The turn keeps the newest capture of its dispatches (the one its next turn resumes) and every earlier one."""
    if session is not None:
        turn['session'] = dict(session)
        turn.setdefault('captures', []).append(dict(session))
    if started is not None:
        turn.setdefault('starts', []).append(copy.deepcopy(started))


class Conversations:
    def __init__(self, store, conn, *, domain, principal, signer, sign, state_root, generation=1, observe=None,
                 records=None):
        self.store, self.conn, self.domain, self.principal = store, conn, domain, principal
        self.signer, self.sign, self.state_root, self.generation = signer, sign, os.path.abspath(str(state_root)), generation
        # VELDO-0180: the turns' execution records (the conversation receiver's), for a conversion's rendering.
        self.records = os.path.abspath(str(records)) if records else os.path.join(self.state_root, 'records')
        self.observe = observe or (lambda event: None)
        conn.command_registry[OPERATION] = {'transaction_transition': transition,
                                            'writes': ('entities', 'journal', 'commands', 'nonces')}

    def read(self, identity):
        row = _conversation(self.conn, identity)
        return copy.deepcopy(row['data']) if row else None

    def turns(self, identity):
        found = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (TURN_KIND,)):
            value = json.loads(data)
            if value.get('conversation') == identity:
                found.append(value)
        return sorted(found, key=lambda value: value['sequence'])

    def waiting(self):
        found = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (TURN_KIND,)):
            value = json.loads(data)
            conversation = self.read(value.get('conversation'))
            if value.get('state') == 'waiting' and conversation and conversation.get('status') == 'open':
                found.append(value)
        return sorted(found, key=lambda value: (value.get('arrival', 0), value['conversation'], value['sequence']))

    def _run(self, operation, identity, fields, *, principal=None, now=None):
        principal = principal or self.principal
        cid = conversation_id(identity)
        ids = [cid]
        if operation == MESSAGE:
            ids.append(turn_id(identity, len(self.turns(identity)) + 1))
        if type(fields.get('sequence')) is int:
            ids.append(turn_id(identity, fields['sequence']))
        expected = {}
        for item in ids:
            row = _row(self.conn, item)
            expected[item] = row['version'] if row else 0
        params = dict(fields, operation=operation, conversation=identity, domain=self.domain,
                      principal=principal)
        command_id = fields.get('command_id') or ('conversation/%s/%s/%s' % (
            operation, identity, S.digest_of(params).split(':', 1)[-1][:24]))
        command = {'command_id': command_id, 'principal': principal, 'operation': OPERATION,
                   'parameters': params, 'expected_versions': expected, 'artifact_digests': [],
                   'nonce': 'conversation/' + command_id}
        prior = self.conn.execute('SELECT before_versions FROM journal WHERE command_id=?', (command_id,)).fetchone()
        if prior:
            command['expected_versions'] = json.loads(prior[0])
        event = {'schema': SCHEMA, 'operation': operation, 'conversation': identity, 'principal': principal,
                 'read_version': expected.get(cid), 'command_id': command_id}
        try:
            receipt = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            code = error.code
            self.observe(dict(event, outcome='refused', refusal=code))
            if isinstance(error, Refused):
                raise
            raise Refused(code, getattr(error, 'detail', '')) from None
        committed = self.conn.execute('SELECT transition FROM journal WHERE command_id=?', (command_id,)).fetchone()
        changes = json.loads(committed[0]) if committed else {}
        record = (changes.get(cid) or {}).get('data') or self.read(identity)
        detail = {key: fields.get(key) for key in ('sequence', 'dispatch_id', 'role_revision', 'account', 'receiver')
                  if fields.get(key) is not None}
        changed_turn = next((item['data'] for item in changes.values() if item.get('kind') == TURN_KIND), None)
        if changed_turn:
            detail.update({key: changed_turn.get(key) for key in
                           ('sequence', 'dispatch_id', 'role_revision', 'account', 'receiver', 'state')})
            detail['turn_outcome'] = changed_turn.get('outcome')
        self.observe(dict(event, outcome='accepted', written_version=(record or {}).get('version'),
                          watermark=receipt['seq'], **detail))
        return record, receipt

    def directory(self, identity):
        """Where a conversation opened by this service keeps its directory."""
        return conversation_directory(self.state_root, identity)

    def open(self, identity, *, owner, role=DEFAULT_ROLE, intake_digest, command_id=None, now=None):
        directory = self.directory(identity)
        record, _receipt = self._run(OPEN, identity, {'role': role, 'intake_digest': intake_digest,
            'directory': directory, 'command_id': command_id}, principal=owner, now=now)
        # VELDO-0177 AC1: the conversation's own workspace under its directory, the engine's working directory.
        workspace = make_workspace(record)
        self.observe({'schema': SCHEMA, 'operation': 'conversation_workspace', 'conversation': identity,
                      'workspace': workspace, 'outcome': 'made'})
        return record

    def close(self, identity, version, *, owner, command_id=None, now=None):
        record, _receipt = self._run(CLOSE, identity, {'version': version, 'command_id': command_id},
                                     principal=owner, now=now)
        return record

    def message(self, identity, intake_command, intake_digest, *, owner, command_id=None, now=None):
        before = len(self.turns(identity))
        _record, receipt = self._run(MESSAGE, identity, {'intake_command': intake_command,
            'intake_digest': intake_digest, 'command_id': command_id}, principal=owner, now=now)
        turns = self.turns(identity)
        if before < len(turns):
            return turns[before]
        transition_row = self.conn.execute('SELECT transition FROM journal WHERE command_id=?',
                                           (receipt['command_id'],)).fetchone()
        transition = json.loads(transition_row[0]) if transition_row else {}
        replayed = [entry['data'] for entry in transition.values() if entry.get('kind') == TURN_KIND]
        if len(replayed) != 1:
            raise Refused('unknown_outcome:conversation_replay')
        return replayed[0]

    def change_role(self, identity, version, role, *, owner, command_id=None, now=None):
        record, _receipt = self._run(ROLE, identity, {'version': version, 'role': role,
                                     'command_id': command_id}, principal=owner, now=now)
        return record

    def attach_project(self, identity, version, project, *, owner, command_id=None, now=None):
        """attach_project (VELDO-0177 AC3): the owner's command on the current version; for a project with an
        execution repository, its trunk commit is read first, the record names that commit and the new clone's
        path, and the clone is taken there once the command commits (a replay takes none).  Nothing of the
        repository is read unless the owner, version, open and project checks pass first; otherwise the command
        runs without it and the transition refuses it by the same name."""
        fields = {'version': version, 'project': project, 'command_id': command_id}
        current = self.read(identity)
        source, authorized = None, False
        if current is not None and _text(project) and type(version) is int and version == current.get('version'):
            try:
                member = _member(self.conn, owner, time.time(), owner=True)
                if current.get('owner') != owner or current.get('status') != 'open':
                    raise Refused('missing_authority:conversation_owner')
                attach_authority(self.conn, member, current, project)
                authorized = True
            except Refused:
                pass
        if authorized:
            try:
                repository, path = project_source(self.conn, self.domain, project)
            except Refused as error:
                self.observe({'schema': SCHEMA, 'operation': ATTACH, 'conversation': identity, 'project': project,
                              'outcome': 'refused', 'refusal': error.code})
                raise
            if path is not None and workspace_of(current):
                CL = _organ('control_clone')
                try:
                    fields['commit'] = CL.trunk_commit(path)
                except CL.Refused as error:
                    raise Refused(error.code, error.detail) from None
                earlier = [a for a in current.get('attachments') or [] if a.get('project') == project]
                fields['clone'] = clone_path(current, project, len(earlier) + 1)
                source = path
        record, receipt = self._run(ATTACH, identity, fields, principal=owner, now=now)
        attached = [a for a in record.get('attachments') or [] if a.get('project') == project]
        if source is not None and not receipt.get('replayed') and attached and attached[-1]['clone'] == fields['clone']:
            CL = _organ('control_clone')
            try:
                CL.conversation_clone(source, fields['commit'], fields['clone'])
            except CL.Refused as error:
                self.observe({'schema': SCHEMA, 'operation': 'project_attach', 'conversation': identity,
                              'project': project, 'commit': fields['commit'], 'clone': fields['clone'],
                              'outcome': 'refused', 'refusal': error.code})
                raise Refused(error.code, error.detail) from None
            self.observe({'schema': SCHEMA, 'operation': 'project_attach', 'conversation': identity,
                          'project': project, 'commit': fields['commit'], 'clone': fields['clone'],
                          'outcome': 'cloned'})
        return record

    def dispatched(self, identity, sequence, dispatch_id, role_revision, account, receiver, *, now=None):
        self._run(DISPATCH, identity, {'sequence': sequence, 'dispatch_id': dispatch_id,
                  'role_revision': role_revision, 'account': account, 'receiver': receiver}, now=now)
        return _turn(self.conn, identity, sequence)['data']

    def ended(self, identity, sequence, dispatch_id, outcome, *, session=None, start=None, reply=False, now=None):
        """End a turn. VELDO-0175 AC3: a completed turn keeps its engine's final result text as its reply, read from
        the execution record its exit committed (or `reply` when the caller read it); any other end keeps none."""
        fields = {'sequence': sequence, 'dispatch_id': dispatch_id, 'outcome': outcome}
        fields.update({k: v for k, v in (('session', session), ('start', start)) if v is not None})
        if reply is False:
            reply = self.reply_of(identity, sequence, dispatch_id) if outcome == 'completed' else None
        fields['reply'] = reply
        self._run(END, identity, fields, now=now)
        self._session_event(identity, sequence, dispatch_id, session, start)
        return _turn(self.conn, identity, sequence)['data']

    def deferred(self, identity, sequence, dispatch_id, refusal, *, session=None, start=None, limit=None,
                 decision=None, question=None, now=None):
        fields = {'sequence': sequence, 'dispatch_id': dispatch_id, 'refusal': refusal}
        fields.update({k: v for k, v in (('session', session), ('start', start), ('limit', limit),
                                         ('decision', decision), ('question', question)) if v is not None})
        self._run(DEFER, identity, fields, now=now)
        self._session_event(identity, sequence, dispatch_id, session, start)
        return _turn(self.conn, identity, sequence)['data']

    def reply_of(self, identity, sequence, dispatch_id):
        """VELDO-0175 AC3: the final result text of the dispatch's run, read from its redacted execution record as its
        exit committed it, through the receiver configuration the turn was dispatched to; None when there is none."""
        turn = _turn(self.conn, identity, sequence)
        dispatch = _row(self.conn, 'dispatch:' + str(dispatch_id))
        committed = ((dispatch or {}).get('data') or {}).get('execution_record')
        receiver = ((turn or {}).get('data') or {}).get('receiver')
        if committed is None or not _text(receiver):
            return None
        ER = _organ('control_execution_record')
        lines, after = [], 0
        try:
            records = ER.directory(json.loads(Path(receiver).read_text()))
            while True:
                page = ER.read(records, dispatch_id, after, 4096, committed=committed)
                lines += page['lines']
                after += len(page['lines'])
                if not page['lines'] or after >= page['total']:
                    break
        except Exception as error:  # noqa: BLE001 - an unreadable record keeps no reply, by name
            self.observe({'schema': SCHEMA, 'operation': 'turn_reply', 'conversation': identity, 'sequence': sequence,
                          'dispatch_id': dispatch_id, 'outcome': 'refused',
                          'refusal': getattr(error, 'code', type(error).__name__)})
            return None
        return final_reply(lines)

    def _session_event(self, identity, sequence, dispatch_id, session, start):
        """VELDO-0176 observability: the capture a turn's dispatch produced, as bound to its record (ids and digest,
        never session content), and how the dispatch started."""
        if session is not None:
            self.observe({'schema': SCHEMA, 'operation': 'session_capture', 'conversation': identity,
                          'sequence': sequence, 'dispatch_id': dispatch_id, 'engine': session['engine'],
                          'session_id': session['session_id'], 'account': session['account'],
                          'digest': session['digest'], 'outcome': 'bound'})
        if start is not None:
            self.observe(dict({'schema': SCHEMA, 'operation': 'turn_start', 'conversation': identity,
                               'sequence': sequence, 'dispatch_id': dispatch_id}, **start))

    def note(self, identity, sequence, note, *, now=None):
        """VELDO-0176 AC2: a question about a turn (its ref, choices and, once settled, the answer) or a notice the
        owner was given, kept on the turn record."""
        self._run(NOTE, identity, {'sequence': sequence, 'note': note}, now=now)
        self.observe(dict({'schema': SCHEMA, 'operation': 'turn_' + note.get('kind', 'note'), 'conversation': identity,
                           'sequence': sequence}, **{k: note.get(k) for k in ('ref', 'answer', 'reason')}))
        return _turn(self.conn, identity, sequence)['data']

    def held(self, identity, engine):
        return held_session(self.conn, identity, engine)

    def flag(self, dispatch_id, *, engine, means, text, at, read_at=None, sequence=None, account=None,
             synchronous=False, conversation=None, project=None):
        """VELDO-0231: write one flag a running agent raised (flag_conversation, the service principal). Returns
        {outcome, conversation, flag (the record, None when held back), summary}; the observation names the
        conversation, the run's flag count and its held back count, never the text."""
        sid = flag_summary_id(dispatch_id)
        row = _row(self.conn, sid)
        number = ((row or {}).get('data') or {}).get('read', 0) + 1
        fid = flag_id(dispatch_id, number)
        params = {'operation': FLAG, 'conversation': conversation, 'project': project, 'dispatch_id': dispatch_id,
                  'number': number, 'engine': engine, 'means': means, 'text': text, 'at': at, 'read_at': read_at,
                  'sequence': sequence, 'account': account, 'synchronous': bool(synchronous),
                  'domain': self.domain, 'principal': self.principal}
        command_id = 'conversation/%s/%s/%d' % (FLAG, dispatch_id, number)
        command = {'command_id': command_id, 'principal': self.principal, 'operation': OPERATION,
                   'parameters': params, 'artifact_digests': [], 'nonce': 'conversation/' + command_id,
                   'expected_versions': {sid: row['version'] if row else 0, fid: 0}}
        event = {'schema': FLAG_SCHEMA, 'operation': FLAG, 'dispatch_id': dispatch_id, 'engine': engine,
                 'means': means, 'length': len(text) if isinstance(text, str) else None, 'sequence': sequence,
                 'account': account, 'command_id': command_id}
        try:
            receipt = self.store.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, self.store.StoreRefused) as error:
            self.observe(dict(event, outcome='refused', refusal=error.code))
            if isinstance(error, Refused):
                raise
            raise Refused(error.code, getattr(error, 'detail', '')) from None
        summary = _row(self.conn, sid)['data']
        written = _row(self.conn, fid)
        record = written['data'] if written and written['kind'] == FLAG_KIND else None
        outcome = summary.get('outcome')
        self.observe(dict(event, outcome=outcome, conversation=(record or {}).get('conversation'),
                          flags=summary['read'], held_back=summary['held_back'], watermark=receipt['seq'],
                          latency=(at - read_at) if record is not None and _number(read_at) else None))
        return {'outcome': outcome, 'conversation': (record or {}).get('conversation'), 'flag': record,
                'summary': summary}

    def flags(self, conversation=None, dispatch_id=None):
        """The flag records, of one conversation or one run (the undelivered ones have no conversation), in order."""
        found = [json.loads(raw) for (raw,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (FLAG_KIND,))]
        found = [f for f in found if (conversation is None or f.get('conversation') == conversation)
                 and (dispatch_id is None or f.get('dispatch_id') == dispatch_id)]
        return sorted(found, key=lambda f: (f.get('at') or 0, f['dispatch_id'], f['number']))

    def flag_summary(self, dispatch_id):
        row = _row(self.conn, flag_summary_id(dispatch_id))
        return copy.deepcopy(row['data']) if row else None

    def flag_counts(self):
        """VELDO-0231 metrics: flags read, delivered, held back and undelivered, per engine and means, and each
        delivered flag's latency from the receiver reading it to its commit."""
        counts = {}
        for (raw,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (FLAG_KIND,)):
            flag = json.loads(raw)
            key = '%s/%s' % (flag.get('engine'), flag.get('means'))
            entry = counts.setdefault(key, {'delivered': 0, 'undelivered': 0, 'latencies': []})
            if flag.get('conversation') is None:
                entry['undelivered'] += 1
            else:
                entry['delivered'] += 1
                if _number(flag.get('read_at')):
                    entry['latencies'].append(round(flag['at'] - flag['read_at'], 6))
        summaries = [json.loads(raw) for (raw,) in self.conn.execute(
            'SELECT data FROM entities WHERE kind=?', (FLAG_SUMMARY_KIND,))]
        return {'read': sum(s.get('read', 0) for s in summaries),
                'held_back': sum(s.get('held_back', 0) for s in summaries), 'by_means': counts}

    def status(self):
        conversations = []
        for (data,) in self.conn.execute('SELECT data FROM entities WHERE kind=?', (KIND,)):
            conversations.append(json.loads(data))
        turns = [json.loads(data) for (data,) in self.conn.execute(
            'SELECT data FROM entities WHERE kind=?', (TURN_KIND,))]
        outcomes = {}
        for turn in turns:
            if turn.get('outcome'):
                outcomes[turn['outcome']] = outcomes.get(turn['outcome'], 0) + 1
        # VELDO-0177 metrics: turns by the role revision they launched with, turns refused for a workspace mismatch,
        # and project attaches.
        by_revision = {}
        for turn in turns:
            if type(turn.get('role_revision')) is int:
                key = str(turn['role_revision'])
                by_revision[key] = by_revision.get(key, 0) + 1
        # VELDO-0176 metrics: turns resumed from a held session, started from a rendering and from a shortened one,
        # captures, engine questions by answer, and turns stopped by a held session whose digest differs.
        starts = [start for turn in turns for start in turn.get('starts') or []]
        answers = {}
        for turn in turns:
            for asked in turn.get('questions') or []:
                key = asked.get('answer') or 'unanswered'
                answers[key] = answers.get(key, 0) + 1
        sessions = {'resumed': sum(s.get('mode') == 'resumed' for s in starts),
                    'rendered': sum(s.get('mode') == 'rendered' for s in starts),
                    'rendered_shortened': sum(s.get('mode') == 'rendered' and bool(s.get('left_out')) for s in starts),
                    'captures': sum(len(turn.get('captures') or []) for turn in turns),
                    'questions': answers, 'session_mismatch': outcomes.get(SESSION_MISMATCH, 0),
                    'resume_mismatch': outcomes.get(RESUME_MISMATCH, 0)}
        return {'sessions': sessions, 'open': sum(c.get('status') == 'open' for c in conversations),
                'waiting': sum(t.get('state') == 'waiting' for t in turns), 'outcomes': outcomes,
                'turns_by_role_revision': by_revision, 'workspace_refusals': outcomes.get(WORKSPACE_MISMATCH, 0),
                'project_attaches': sum(len(c.get('attachments') or []) for c in conversations)}


def receiver_check(conn, contract):
    """None when this prepared conversation turn may still launch, else its named refusal."""
    if contract.get('subject_kind') != KIND or contract.get('station') != 'turn':
        return 'binding_mismatch:conversation_receiver'
    subject = contract.get('unit')
    record = _conversation(conn, subject)
    if record is None:
        return 'invalid_input:conversation:unknown'
    if record['data'].get('status') != 'open':
        return 'stale_subject:conversation_closed'
    turn = _turn(conn, subject, (contract.get('source') or {}).get('turn'))
    if (turn is None or turn['data'].get('state') != 'dispatched'
            or turn['data'].get('dispatch_id') != contract.get('dispatch_id')):
        return 'stale_subject:conversation_turn_active'
    # VELDO-0177 AC1: the working directory the contract names is this conversation's own workspace, or nothing runs.
    own = workspace_of(record['data'])
    if own is None or (contract.get('source') or {}).get('workspace') != own:
        return WORKSPACE_MISMATCH
    return None


# ---- VELDO-0176: held sessions and the history rendering -------------------------------------------------------------

def held_session(conn, identity, engine):
    """The newest capture of `engine` a turn of this conversation holds, with that turn's sequence; None for none.
    A role on the same engine resumes it; the other engine's held session is kept, so a change back resumes it."""
    found = []
    for (data,) in conn.execute('SELECT data FROM entities WHERE kind=?', (TURN_KIND,)):
        turn = json.loads(data)
        session = turn.get('session')
        if turn.get('conversation') == identity and isinstance(session, dict) and session.get('engine') == engine:
            found.append((turn['sequence'], session))
    if not found:
        return None
    sequence, session = max(found, key=lambda item: item[0])
    return dict(session, turn=sequence)


def file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


def checked_capture(conn, identity, held):
    """VELDO-0176 AC1, AC3: the held session named by the dispatch (`held`: its turn, session id and digest), read
    back from the turn record and its capture file; refused by name (binding_mismatch:conversation_session) when the
    turn record names another session or digest, or the capture is missing, a link, or its digest differs."""
    turn = _turn(conn, identity, (held or {}).get('turn'))
    session = ((turn or {}).get('data') or {}).get('session') or {}
    if (not session or any(session.get(k) != held.get(k) for k in ('engine', 'session_id', 'digest', 'relative'))
            or session.get('capture') != held.get('capture')):
        raise Refused(SESSION_MISMATCH, 'the held session is not the one the turn record binds')
    try:
        info = os.lstat(session['capture'])
        if not (info.st_mode & 0o170000 == 0o100000) or file_digest(session['capture']) != session['digest']:
            raise Refused(SESSION_MISMATCH, 'the held session differs from its turn record')
    except OSError:
        raise Refused(SESSION_MISMATCH, 'the held session is missing') from None
    return session


def _write_private(path, data):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    temporary = path + '.tmp-' + os.urandom(6).hex()
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(data)
    os.replace(temporary, path)


def place(session, profile):
    """VELDO-0176 AC1: the checked capture at the same relative place in the chosen account's profile, mode 0600;
    returns the placed path. The capture was read and checked by digest, and what is placed is those bytes."""
    with open(session['capture'], 'rb') as handle:
        data = handle.read()
    if 'sha256:' + hashlib.sha256(data).hexdigest() != session['digest']:
        raise Refused(SESSION_MISMATCH, 'the held session changed while it was placed')
    target = os.path.join(profile, session['relative'])
    if os.path.commonpath([os.path.realpath(profile), os.path.realpath(os.path.dirname(target))]) != \
            os.path.realpath(profile):
        raise Refused(SESSION_MISMATCH, 'the held session would leave the account profile')
    _write_private(target, data)
    return target


def capture(record, engine, profile, found, session_id, dispatch_id, account):
    """VELDO-0176 AC1: the session file the engine wrote in the account profile (`found`, the engine module's
    session_file) kept under the conversation's sessions directory at mode 0600 and removed from the profile.
    Returns the session as the turn record binds it."""
    root = sessions_of(record)
    with open(found, 'rb') as handle:
        data = handle.read()
    name = hashlib.sha256(str(dispatch_id).encode()).hexdigest()[:32] + '.jsonl'
    target = os.path.join(root, engine, name)
    os.makedirs(root, mode=0o700, exist_ok=True)
    os.chmod(root, 0o700)
    _write_private(target, data)
    os.unlink(found)
    return {'engine': engine, 'session_id': session_id, 'relative': os.path.relpath(found, profile),
            'capture': target, 'digest': 'sha256:' + hashlib.sha256(data).hexdigest(), 'account': account,
            'dispatch_id': dispatch_id}


def _text_of(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(_text_of(item.get('text') if isinstance(item, dict) and 'text' in item else item)
                         for item in value)
    return json.dumps(value, sort_keys=True)


def turn_from_record(lines):
    """One earlier turn as its execution record keeps it after redaction (VELDO-0141 AC4): the owner's message from
    the receiver's input line, each tool call with its input and result, and the reply; read from the record's
    redacted payloads only, never from a held session."""
    message, calls, replies, results = None, [], [], {}
    for line in lines:
        try:
            event = json.loads(line.get('payload') or 'null')
        except ValueError:
            event = None
        if not isinstance(event, dict):
            continue
        if line.get('stream') == 'wrapper' and isinstance(event.get('turn_input'), dict):
            message = message if message is not None else event['turn_input'].get('message')
            continue
        if line.get('stream') != 'engine':
            continue
        kind = event.get('type')
        content = (event.get('message') or {}).get('content') if isinstance(event.get('message'), dict) else None
        if kind == 'assistant' and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    calls.append({'id': block.get('id'), 'name': block.get('name'), 'input': block.get('input'),
                                  'result': None})
                elif isinstance(block, dict) and block.get('type') == 'text' and _text(block.get('text')):
                    replies.append(block['text'])
        elif kind == 'user' and isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_result':
                    results[block.get('tool_use_id')] = _text_of(block.get('content'))
        elif kind == 'result' and _text(event.get('result')):
            replies.append(event['result'])
        elif kind == 'item.completed' and isinstance(event.get('item'), dict):
            item = event['item']
            if item.get('type') == 'agent_message' and _text(item.get('text')):
                replies.append(item['text'])
            elif item.get('type') not in ('reasoning', 'agent_message'):
                name = item.get('tool') or item.get('type')
                given = item.get('command') if 'command' in item else item.get('arguments', item.get('changes'))
                result = item.get('aggregated_output') if 'aggregated_output' in item else item.get('result')
                calls.append({'id': item.get('id'), 'name': name, 'input': given, 'result': _text_of(result)})
    for call in calls:
        if call['id'] in results:
            call['result'] = results[call['id']]
    return {'message': message, 'calls': calls, 'reply': replies[-1] if replies else None}


def final_reply(lines):
    """VELDO-0175 AC3: a run's final result text from its execution record (VELDO-0060 and VELDO-0061 terminal
    records): Claude Code's successful `result` event, else Codex's last completed agent message before its turn
    completed; None when the run wrote neither."""
    result, message = None, None
    for line in lines:
        if line.get('stream') != 'engine':
            continue
        try:
            event = json.loads(line.get('payload') or 'null')
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get('type') == 'result' and not event.get('is_error') and isinstance(event.get('result'), str):
            result = event['result']
        elif event.get('type') == 'item.completed' and isinstance(event.get('item'), dict):
            item = event['item']
            if item.get('type') == 'agent_message' and isinstance(item.get('text'), str):
                message = item['text']
    reply = result if result is not None else message
    return reply if _text(reply) else None


def _turn_text(sequence, turn):
    parts = ['Turn %d' % sequence, 'Owner: %s' % (turn.get('message') if turn.get('message') is not None
                                                   else '(not in the record)')]
    for call in turn.get('calls') or []:
        parts.append('Tool call: %s %s' % (call.get('name'), json.dumps(call.get('input'), sort_keys=True)))
        parts.append('Tool result: %s' % (call.get('result') if call.get('result') is not None else '(none)'))
    parts.append('Reply: %s' % (turn.get('reply') if turn.get('reply') is not None else '(none)'))
    return '\n'.join(parts) + '\n'


def render(turns, bound):
    """VELDO-0176 AC3: the history a fresh session on the other engine starts from: `turns` ((sequence, turn) in
    order, each as turn_from_record reads it) as the newest whole turns that fit `bound` characters, after one line
    naming how many earlier turns were left out. A turn is never cut; a history beyond the bound is shortened, never
    refused. Returns {text, turns, left_out, digest, characters}."""
    texts = [(sequence, _turn_text(sequence, turn)) for sequence, turn in turns]
    kept = []
    for sequence, text in reversed(texts):
        header = LEFT_OUT % (len(texts) - len(kept) - 1) + '\n'
        if len(header) + sum(len(t) for _s, t in kept) + len(text) > bound:
            break
        kept.insert(0, (sequence, text))
    left_out = len(texts) - len(kept)
    text = LEFT_OUT % left_out + '\n' + ''.join(t for _s, t in kept)
    return {'text': text, 'turns': [sequence for sequence, _t in kept], 'left_out': left_out,
            'digest': 'sha256:' + hashlib.sha256(text.encode()).hexdigest(), 'characters': len(text)}


def history(conn, records, identity, before, read):
    """VELDO-0176 AC3: each earlier turn of the conversation (sequence below `before`), in order, read from the
    execution records of its dispatches as their exits committed them (`read`, control_execution_record.read)."""
    found = []
    turns = sorted((json.loads(d) for (d,) in conn.execute('SELECT data FROM entities WHERE kind=?', (TURN_KIND,))),
                   key=lambda t: t.get('sequence', 0))
    for turn in turns:
        if turn.get('conversation') != identity or turn.get('sequence', 0) >= before:
            continue
        lines = []
        for attempt in turn.get('attempts') or []:
            row = _row(conn, 'dispatch:' + str(attempt.get('dispatch_id')))
            committed = ((row or {}).get('data') or {}).get('execution_record')
            if not row or committed is None:
                continue
            after = 0
            while True:
                try:
                    page = read(records, attempt['dispatch_id'], after, 4096, committed=committed)
                except Exception:  # noqa: BLE001 - a record that cannot be read leaves that attempt out, by name
                    break
                lines += page['lines']
                after += len(page['lines'])
                if not page['lines'] or after >= page['total']:
                    break
        found.append((turn['sequence'], turn_from_record(lines)))
    return found
