#!/usr/bin/env python3
"""The conversation screens' harness (VELDO-0179): VELDO-0131's factory harness (VELDO-0163's team harness over
VELDO-0145's real factory) with the owner's conversations on, every turn run by a fake engine.

WHAT IT ADDS, on the same store connection and authority thread:

- THE CONVERSATIONS. The production VELDO-0174 conversation authority (control_conversation.Conversations) on the
  store's connection, handed to the real control_api_authority as its `conversations` (the four conversation
  commands and the conversation read of VELDO-0178) and to the real VELDO-0126 intake (a message whose
  `conversation` field names one is its next turn, VELDO-0175). The factory's own service principal `authority`
  is enrolled as the reservation service that dispatches and ends turns, as the conversation Line runs.
- THE DEFAULT TEAM'S CONVERSATION ROLES. Capability configurations `assistant` (claude_code) and `assistant_codex`
  (codex) saved through the real VELDO-0127 writer, and the default team's second revision with both roles beside
  the first revision's, saved by the owner through the real default team route.
- A FIXTURE PROJECT `veldo`, owned by the owner and activated through the real project writer on its own execution
  repository (a one-commit Git repository bound in this domain with its identity), which a conversation attaches:
  the attach takes a real clone of it into the conversation's workspace.
- THE FAKE ENGINE. No real engine runs. A runner thread takes each waiting turn of an open conversation in order,
  as the conversation Line does: it writes the turn's dispatch record (a conversation turn's contract: subject kind
  conversation, its source the conversation and turn, no project), dispatches the turn through the conversation
  authority's own dispatch command, and feeds the lines a Claude Code run prints, one every `pace` seconds, through
  the real VELDO-0141 Recorder (the receiver's writer) with a resolved credential value, so the line carrying it is
  kept redacted: the run's init, a tool call (Bash `cat deploy.env`), the command's output, an error line on its
  error stream, then (once the conversation is not held) the reply and the run's result. It then commits the record,
  marks the dispatch exited with the committed count and digest, and ends the turn completed with the reply, through
  the conversation authority's own end command. Every write is followed by the authority's hint to the API, and
  every record batch by the record hint, exactly as the receiver's hints are.
- THE FAKE TELEGRAM EDGE. The owner writes on Telegram through the loopback Bot API stand-in (getUpdates in the
  platform's shape, nothing sent anywhere); the real VELDO-0066 Acquirer takes the update and the real intake
  receives it, and the factory PM's route document sends it to the named open conversation as its next turn (as
  suite 131 applies the PM's documents; the PM run itself is suite 132's).

THE CONTROL PORT adds:
  /conversation/replies   {replies: [text, ...]}         the replies the next turns end with, in order
  /conversation/hold      {conversation, on}              hold a conversation's running turn after its error line
  /conversation/pace      {seconds}                       the time between two printed lines
  /conversation/pause     {on}                            start no new turn while on (a turn stays waiting)
  /conversation/telegram  {conversation, text}            the owner writes on Telegram; the PM routes it there
  /conversation/role      {conversation, role}            the owner changes the role elsewhere (a newer version)
  /conversation/read      {conversation}                  the stored conversation and its turns
  /conversation/record    {conversation, sequence}        the turn's kept record lines and its commitment
  /conversation/list      {}                              every stored conversation

Run: python3 -B engine/ui/e2e/conversation_harness.py --dist engine/ui/dist
"""
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as H  # noqa: E402
import team_harness as T  # noqa: E402
import factory_harness as F  # noqa: E402

PROJECT = 'veldo'
ACCOUNT = 'owner-plan'
SECRET_KIND = 'subscription_token'


def engine_lines(conversation, sequence, secret, reply):
    """What the fake engine prints for one turn, in Claude Code's stream JSON shapes: (stream, payload) pairs, the
    hold point after the error line."""
    sid = 'session-' + secrets.token_hex(4)
    tool = 'toolu_' + secrets.token_hex(4)

    def assistant(*content):
        return {'type': 'assistant', 'parent_tool_use_id': None, 'session_id': sid,
                'message': {'id': 'msg_' + secrets.token_hex(6), 'role': 'assistant', 'content': list(content)}}
    before = [
        ('engine', {'type': 'system', 'subtype': 'init', 'cwd': '/conversations/workspace', 'session_id': sid,
                    'tools': ['Bash', 'Read'], 'model': 'fake-engine', 'permissionMode': 'default'}),
        ('engine', assistant({'type': 'tool_use', 'id': tool, 'name': 'Bash',
                              'input': {'command': 'cat deploy.env', 'description': 'Read the deploy settings'}})),
        ('engine', {'type': 'user', 'parent_tool_use_id': None, 'session_id': sid, 'message': {
            'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': tool,
                                         'content': 'DEPLOY_TOKEN=' + secret + '\nDEPLOY_STEP=migrate',
                                         'is_error': False}]}}),
        ('stderr', 'fake engine error: the deploy step of turn %d failed' % sequence),
    ]
    after = [
        ('engine', assistant({'type': 'text', 'text': reply})),
        ('engine', {'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 1, 'result': reply,
                    'stop_reason': 'end_turn', 'total_cost_usd': 0}),
    ]
    return before, after


class ConversationUi(F.FactoryUi):
    def _build(self):
        super()._build()
        organs, S, conn, ids = self.organs, self.S, self.conn, self.ids
        CV = H.load('e2e_conversation', organs / 'control_conversation.py')
        self.CV = CV
        self.EV = H.load('e2e_conversation_attribution', organs / 'control_channel_attribution.py')
        self.IN = H.load('e2e_conversation_intake', organs / 'control_intake.py')
        public = ' '.join(self.keyfile['authority'].with_name('authority.pub').read_text().split()[:2])
        self.admin('steward', 'enroll_principal', {'principal': 'authority', 'principal_type': 'service',
                                                   'roles': ['reservation_service'], 'public_key': public,
                                                   'independence_group': 'authority', 'scope': '*'},
                   enrollee='authority')
        self.conversation_observations = []
        self.conversations = CV.Conversations(S, conn, domain=ids['domain_uuid'], principal='authority', signer='authority',
                                              sign=self.journal_sign, state_root=self.base / 'state',
                                              observe=self.conversation_observations.append)
        self.authority.conversation_commands = self.conversations
        self.inbox_intake().conversations = self.conversations
        # The default team's conversation roles, each on its own capability configuration.
        for role, engine, tools in (('assistant', 'claude_code', [dict(name='Read', load='always')]),
                                    ('assistant_codex', 'codex', [])):
            self.configurations.save(dict(role=role, engine=engine, native_tools=tools,
                                          mcp=[], skills=[], instructions=[], settings={}),
                                     principal='owner', base=0, command_id=self.next_id(role))
        team = T.first_team({'role': 'general', 'revision': 1})
        for role, engine in (('assistant', 'claude_code'), ('assistant_codex', 'codex')):
            team['roles'][role] = T.role({'role': role, 'revision': 1}, ['w-elab'], 'assist', engines=(engine,),
                                         kind='specialist')
        cookie, token = self.session('owner')
        status, _h, answer = self.call('POST', '/api/v1/domains/%s/teams/default/save' % H.DOMAIN,
                                       dict(team=team, base=1), cookie, token)
        if status != 200:
            raise RuntimeError('default team conversation roles: %s' % answer)
        self.api.sessions.end_by_principal('owner')
        self._project()
        self.replies, self.held, self.pace, self.jobs, self.paused = [], set(), 0.4, {}, False
        self.secret = 'e2e-secret-' + secrets.token_hex(8)
        self.deliver()

    def _project(self):
        """The fixture project `veldo`, owned by the owner, activated through the real control_project writer on its
        own execution repository: a Git repository with one commit, its identity configured and bound in this domain
        (VELDO-0142), so an attach takes a real clone of it at its trunk commit (VELDO-0177 AC3)."""
        import subprocess
        repo = self.base / 'veldo-source'
        repo.mkdir()
        git = lambda *a: subprocess.run(['git', '-C', str(repo)] + list(a), check=True, capture_output=True, timeout=30)
        git('init', '-q', '-b', 'main')
        (repo / 'README.md').write_text('veldo fixture\n')
        git('add', 'README.md')
        git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture commit')
        repository = 'veldo-repository'
        GI = H.load('e2e_conversation_git_identity', self.organs / 'control_git_identity.py')
        GI.configure_identities(self.conn, self.ids['domain_uuid'], [dict(
            id='fixture', label='Fixture', author_name='Fixture Identity', author_email='fixture@example.invalid',
            remote_host='github.com', remote_owner='fixture', api_token='keychain:fixture/api',
            push_credential=dict(kind='token', reference='keychain:fixture/api'),
            projects_root='/nonexistent/veldo-fixture-projects', default_visibility='private')],
            {repository: dict(path=str(repo), identity='fixture')})
        self.S.bind_repositories(self.conn, self.ids['domain_uuid'], {repository: str(repo)})
        got = self.projects.apply(self.signed_command('owner', dict(
            self.ids, operation='activate', project=PROJECT, principal='owner', command_id=self.next_id('activate'),
            nonce=self.next_id('activate-nonce'), owner='owner', charter={'purpose': 'The method and its machinery.'},
            execution_repository=repository,
            authority_policy={'team_amendment': ['project_owner'], 'admission': ['admission_authority']},
            coordination_budget={'capacity': 5, 'invocations': 12, 'wall_seconds': 500})))
        if not got.get('ok'):
            raise RuntimeError('activate %s: %s' % (PROJECT, got.get('reason')))

    def inbox_intake(self):
        """The real intake the API authority hands messages to."""
        return self.authority.intake

    # the fake engine, run on the authority thread

    def step(self):
        """One pass of the fake engine: start each waiting turn of a conversation with no run, print the next line
        of each run that is due, and end each run that printed everything."""
        now = time.time()
        changed = False
        for turn in ([] if self.paused else self.conversations.waiting()):
            conversation = turn['conversation']
            if conversation not in self.jobs:
                self._start(conversation, turn['sequence'])
                changed = True
        for conversation, job in list(self.jobs.items()):
            if now < job['next_at']:
                continue
            if job['before']:
                self._print(job, job['before'].pop(0))
            elif conversation in self.held:
                continue
            elif job['after']:
                self._print(job, job['after'].pop(0))
            else:
                self._finish(conversation, job)
                changed = True
            job['next_at'] = now + self.pace
        if changed:
            self.deliver()

    def _start(self, conversation, sequence):
        unit = 'turn-%d' % sequence
        dispatch_id = 'dispatch/%s/%s' % (unit, secrets.token_hex(16))
        digest = 'sha256:' + hashlib.sha256(dispatch_id.encode()).hexdigest()
        reply = self.replies.pop(0) if self.replies else 'Turn %d: the deploy step failed at migrate; it is fixed now.' % sequence
        data = dict(schema='veldo.dispatch/v1', dispatch_id=dispatch_id, state='running', contract_digest=digest,
                    process={'platform': 'linux', 'host': 'veldo-linux-1', 'boot_id': 'boot-e2e',
                             'pid': 7000 + sequence, 'start': 17},
                    contract={'unit': unit, 'station': 'conversation', 'attempt': 1, 'subject_kind': 'conversation',
                              'source': {'conversation': conversation, 'turn': sequence},
                              'reservation': {'account': ACCOUNT},
                              'capability': {'adapter': 'claude_code',
                                             'configuration': {'role': 'assistant', 'revision': 1}}})
        self.fixture('dispatch:' + dispatch_id, 'dispatch', data)
        resolved = self.ER.Resolved()
        resolved.add(SECRET_KIND, self.secret)
        header = {'dispatch_id': dispatch_id, 'contract_digest': digest, 'unit': unit, 'station': 'conversation',
                  'project': None, 'account': ACCOUNT, 'host': 'veldo-linux-1', 'conversation': conversation,
                  'turn': sequence}
        recorder = self.ER.Recorder(self.records, header, resolved)
        self.conversations.dispatched(conversation, sequence, dispatch_id, 1, ACCOUNT, 'e2e-fake-engine')
        before, after = engine_lines(conversation, sequence, self.secret, reply)
        self.jobs[conversation] = {'sequence': sequence, 'dispatch': dispatch_id, 'recorder': recorder, 'data': data,
                                   'before': before, 'after': after, 'reply': reply, 'next_at': time.time() + self.pace}

    def _print(self, job, line):
        stream, payload = line
        text = payload if isinstance(payload, str) else json.dumps(payload, separators=(',', ':'))
        job['recorder'].feed(stream, text.encode('utf-8') + b'\n')
        job['recorder'].batch()
        self.api.deliver_record({'dispatch_id': job['dispatch'], 'seq': job['recorder'].sequence})

    def _finish(self, conversation, job):
        committed = job['recorder'].close()
        self.fixture('dispatch:' + job['dispatch'], 'dispatch', dict(job['data'], state='exited',
                                                                    execution_record=committed))
        self.api.deliver_record({'dispatch_id': job['dispatch'], 'seq': committed['lines']})
        self.conversations.ended(conversation, job['sequence'], job['dispatch'], 'completed', reply=job['reply'])
        del self.jobs[conversation]

    # the owner on Telegram, and elsewhere

    def telegram(self, conversation, text):
        """The owner writes on Telegram; the Acquirer takes the update, intake receives it, and the factory PM's route
        document names his open conversation, so it is that conversation's next turn."""
        sender = self.people['owner']
        chat = self.bots['chats'][sender['id']]
        with self.bots['lock']:
            self.bot['update_next'] += 1
            update_id = self.bot['update_next']
        self.bot['updates'].append({'update_id': update_id, 'message': H.message(self.bots, self.bot, sender, chat, text)})
        self.acquirer.acquire()
        intake = self.inbox_intake()
        received = intake.receive('telegram_message', self.EV.evidence_id(self.bot['user']['id'], update_id))
        routed = None
        if received.get('proposal_id'):
            pid = received['proposal_id']
            routed = intake.route(dict(schema=self.IN.RT.SCHEMA, proposal_id=pid, route='open_conversation',
                                       conversation=conversation, reason='Fixture PM: his open conversation.'),
                                  dispatch='fixture-pm-route', proposal_id=pid)
        self.deliver()
        return {'received': {k: received.get(k) for k in ('outcome', 'reason', 'proposal_id', 'conversation')},
                'routed': {k: (routed or {}).get(k) for k in ('outcome', 'reason', 'conversation', 'sequence')}}

    def change_role(self, conversation, role):
        record = self.conversations.read(conversation)
        changed = self.conversations.change_role(conversation, record['version'], role, owner='owner',
                                                 command_id=self.next_id('role-elsewhere'))
        self.deliver()
        return changed

    def stored(self, conversation):
        return {'conversation': self.conversations.read(conversation), 'turns': self.conversations.turns(conversation)}

    def turn_record(self, conversation, sequence):
        turn = next((t for t in self.conversations.turns(conversation) if t['sequence'] == sequence), None)
        if not turn or not turn.get('dispatch_id'):
            return {'lines': [], 'total': 0, 'committed': None, 'dispatch': None}
        row = self.entity('dispatch:' + turn['dispatch_id'])
        committed = ((row or {}).get('data') or {}).get('execution_record')
        kept = self.ER.read(self.records, turn['dispatch_id'], 0, 100000, committed)
        return {'lines': kept['lines'], 'total': kept['total'], 'committed': committed, 'dispatch': turn['dispatch_id']}

    def every(self):
        return [json.loads(r[0]) for r in self.conn.execute("SELECT data FROM entities WHERE kind=?",
                                                            (self.CV.KIND,))]


BASE_CONTROL = F.control_server


def control_server(factory, stop):
    server = BASE_CONTROL(factory, stop)
    handler = server.RequestHandlerClass
    route = handler.route

    def runner():
        while not stop.is_set():
            try:
                factory.on_thread(factory.step)
            except Exception as error:  # noqa: BLE001 - the fake engine's failure is printed, the test sees it stop
                print('fake engine: %s: %s' % (type(error).__name__, error), file=sys.stderr, flush=True)
            stop.wait(0.1)
    threading.Thread(target=runner, daemon=True).start()

    def extended(self, path, body):
        f = factory
        if path == '/conversation/replies':
            f.replies.extend(body.get('replies') or [])
            return {'replies': len(f.replies)}
        if path == '/conversation/hold':
            (f.held.add if body.get('on', True) else f.held.discard)(body['conversation'])
            return {'held': sorted(f.held)}
        if path == '/conversation/pause':
            f.paused = bool(body.get('on', True))
            return {'paused': f.paused}
        if path == '/conversation/pace':
            f.pace = float(body['seconds'])
            return {'pace': f.pace}
        if path == '/conversation/telegram':
            return f.on_thread(f.telegram, body['conversation'], body['text'])
        if path == '/conversation/role':
            return {'conversation': f.on_thread(f.change_role, body['conversation'], body['role'])}
        if path == '/conversation/read':
            return f.on_thread(f.stored, body['conversation'])
        if path == '/conversation/record':
            return f.on_thread(f.turn_record, body['conversation'], int(body['sequence']))
        if path == '/conversation/list':
            return {'conversations': f.on_thread(f.every)}
        if path == '/conversation/secret':
            return {'secret': f.secret}
        return route(self, path, body)
    handler.route = extended
    return server


def main():
    H.Factory = ConversationUi
    H.control_server = control_server
    H.main()


if __name__ == '__main__':
    os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
    main()
