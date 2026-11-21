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
OPERATIONS = OWNER_OPERATIONS + (DISPATCH, DEFER, END, FLAG)
# VELDO-0177: the workspace under the conversation's directory, the attached projects' clones under it, and the
# receiver's refusal of a turn launched anywhere else.
WORKSPACE = 'workspace'
PROJECTS = 'projects'
WORKSPACE_MISMATCH = 'binding_mismatch:conversation_workspace'


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


def flag_summary_id(dispatch_id):
    return 'run-flags:' + str(dispatch_id)


def flag_id(dispatch_id, number):
    return 'conversation-flag:%s:%d' % (dispatch_id, number)


def workspace_of(record):
    """VELDO-0177 AC1: a conversation's own workspace, `workspace` under its directory; None without a directory."""
    directory = (record or {}).get('directory')
    return os.path.join(directory, WORKSPACE) if _text(directory) and os.path.isabs(directory) else None


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


def transition(conn, params, before):
    operation, now = params.get('operation'), time.time()
    identity, principal = params.get('conversation'), params.get('principal')
    if operation == FLAG:
        return _flag(conn, params, before, now)
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
    if operation == DEFER:
        if turn.get('state') != 'dispatched' or turn.get('dispatch_id') != params.get('dispatch_id'):
            raise Refused('stale_subject:conversation_turn')
        prior = _row(conn, 'dispatch:' + str(turn.get('dispatch_id')))
        if not prior or prior.get('kind') != 'dispatch' or prior['data'].get('state') != 'refused':
            raise Refused('stale_subject:conversation_turn_active')
        turn.update(state='waiting', last_refusal=params.get('refusal'))
        return {tid: {'kind': TURN_KIND, 'data': turn}}
    if turn.get('state') != 'dispatched' or turn.get('dispatch_id') != params.get('dispatch_id'):
        raise Refused('stale_subject:conversation_turn')
    outcome = params.get('outcome')
    if not _text(outcome):
        raise Refused('invalid_input:conversation_outcome')
    turn.update(state='ended', outcome=outcome, ended_at=now)
    return {tid: {'kind': TURN_KIND, 'data': turn}}


class Conversations:
    def __init__(self, store, conn, *, domain, principal, signer, sign, state_root, generation=1, observe=None):
        self.store, self.conn, self.domain, self.principal = store, conn, domain, principal
        self.signer, self.sign, self.state_root, self.generation = signer, sign, os.path.abspath(str(state_root)), generation
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

    def open(self, identity, *, owner, role=DEFAULT_ROLE, intake_digest, command_id=None, now=None):
        safe = hashlib.sha256(identity.encode()).hexdigest()
        directory = os.path.join(self.state_root, 'conversations', safe)
        record, _receipt = self._run(OPEN, identity, {'role': role, 'intake_digest': intake_digest,
            'directory': directory, 'command_id': command_id}, principal=owner, now=now)
        # VELDO-0177 AC1: the conversation's own workspace under its directory, the engine's working directory.
        workspace = workspace_of(record)
        for path in (record['directory'], workspace):
            os.makedirs(path, mode=0o700, exist_ok=True)
            os.chmod(path, 0o700)
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

    def ended(self, identity, sequence, dispatch_id, outcome, *, now=None):
        self._run(END, identity, {'sequence': sequence, 'dispatch_id': dispatch_id, 'outcome': outcome}, now=now)
        return _turn(self.conn, identity, sequence)['data']

    def deferred(self, identity, sequence, dispatch_id, refusal, *, now=None):
        self._run(DEFER, identity, {'sequence': sequence, 'dispatch_id': dispatch_id,
                                   'refusal': refusal}, now=now)
        return _turn(self.conn, identity, sequence)['data']

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
        return {'open': sum(c.get('status') == 'open' for c in conversations),
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
