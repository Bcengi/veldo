"""VELDO-0176: the factory keeps each conversation's engine session and history, so a turn resumes it on any account
of its engine, after an account limit and after a restart.

Run: python3 scripts/selftest.py --suite 130_veldo_0176_conversation_history

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support), the production
conversation authority, VELDO-0174's conversation Line with real receiver subprocesses over fake pinned engines
(support/v174_journey.py, as suite 127 drives them through support/v231_fake_engines.py), the production decision
inbox for the owner's questions, and the production service run twice over one store for the restart. The fake
Claude Code keeps a transcript under its profile's projects directory for its working directory and resumes the
session `--resume` names only when that file is there; the fake Codex keeps a rollout file under its profile's
sessions directory and resumes the thread `exec resume` names only when that file is there. Account limits are a
fake engine's rejected rate-limit event; credentials are a fixture subscription token. No real engine, login, user
unit or network. Writes only temporary fixtures.
"""


def _v176_suite():
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import tempfile
    import time

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Literal anchors: the registered mutation driver substitutes each production copy here, and the fixture's
    # module copy (which the receivers and the restarted service run) takes each of them.
    PRODUCTION = {
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
    }
    ROWS = ('AC1/any-account', 'AC1/capture-kept', 'AC1/resume-qualified', 'AC1/resume-mismatch',
            'AC1/observability',
            'AC2/continues-after-a-limit', 'AC2/ask', 'AC2/wait', 'AC2/move', 'AC2/restart', 'AC2/running-at-restart',
            'AC3/same-engine', 'AC3/redaction', 'AC3/long-history', 'AC3/change-back', 'AC3/digest-refused',
            'AC3/observability')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    H = load('v176_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v176_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    F = load('v176_fakes', ROOT / 'scripts/suites/support/v231_fake_engines.py')
    base = Path(tempfile.mkdtemp(prefix='v176-', dir=fast_temp()))
    fixtures, factories = [], []
    BOUND = 2000

    # THE FAKE ENGINES: VELDO-0174's handshake and init, with the session each engine keeps in its profile. Claude
    # Code decides its session before init: the one `--resume` names when its transcript is under the profile's
    # projects directory for the working directory, else a new one. Codex reads the rollout `exec resume` names under
    # the profile's sessions directory. After its marker a run follows the scenario: hold while `hold-<conversation>`
    # exists; stop at its account's limit (`limit`: once, or on every account); print a tool result carrying the
    # resolved subscription token (`credential`); pad its reply (`pad`). Each run writes its transcript as it goes.
    INIT = "    init = {'type':'system','subtype':'init','apiKeySource':'none','tools':tools,\n"
    SESSION_CODE = r'''    import re as _re, uuid as _uuid
    RESUMED = args[args.index('--resume') + 1] if '--resume' in args else None
    _dir = Path(os.environ.get('CLAUDE_CONFIG_DIR', '/nonexistent')) / 'projects' / _re.sub(r'[^a-zA-Z0-9]', '-', os.getcwd())
    _fresh = (json.loads((MARKERS / 'scenario.json').read_text()) if (MARKERS / 'scenario.json').exists() else {}).get('fresh')
    SESSION = (RESUMED if RESUMED and not _fresh and (_dir / (RESUMED + '.jsonl')).exists()
               else 'session-' + _uuid.uuid4().hex[:12])
    TRANSCRIPT = _dir / (SESSION + '.jsonl')
'''
    OWN = "own = {'engine':ENGINE,'tools':tools,"
    BODY = r'''import uuid
scenario = json.loads((MARKERS / 'scenario.json').read_text()) if (MARKERS / 'scenario.json').exists() else {}
given = packet.get('payload') or {}
conversation = str(given.get('conversation'))
account = os.environ.get('VELDO_ACCOUNT')
if ENGINE == 'codex':
    home = Path(os.environ['CODEX_HOME'])
    RESUMED = args[args.index('resume') + 1] if 'resume' in args else None
    found = sorted(home.glob('sessions/**/rollout-*-%s.jsonl' % RESUMED)) if RESUMED else []
    if found:
        SESSION, TRANSCRIPT = RESUMED, found[-1]
    else:
        SESSION = 'thread-' + uuid.uuid4().hex[:12]
        TRANSCRIPT = home / 'sessions/2026/11/04' / ('rollout-2026-11-04T00-00-00-' + SESSION + '.jsonl')
prior = [json.loads(line) for line in TRANSCRIPT.read_text().splitlines()] if TRANSCRIPT.exists() else []
def keep(said):
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    with TRANSCRIPT.open('a') as handle: handle.write(json.dumps(said) + '\n')
own = {'engine':ENGINE,'cwd':os.getcwd(),'dispatch':os.environ.get('VELDO_DISPATCH_ID'),'argv':args,'packet':packet,
       'session':SESSION,'resumed':RESUMED,'prior':prior,'account':account,'transcript':str(TRANSCRIPT),
       'profile':os.environ.get('CLAUDE_CONFIG_DIR') if ENGINE != 'codex' else os.environ.get('CODEX_HOME')}
(MARKERS / (str(os.getpid()) + '.json')).write_text(json.dumps(own))
while (MARKERS / ('hold-' + conversation)).exists(): time.sleep(.02)
turn = given.get('turn')
keep({'turn': turn, 'part': 'started', 'account': account})
counter = [0]
def say(text):
    counter[0] += 1
    if ENGINE == 'codex':
        emit({'type':'item.completed','item':{'id':'say-%d' % counter[0],'type':'agent_message','text':text}})
    else:
        emit({'type':'assistant','session_id':SESSION,'message':{'id':'say-%s-%d' % (os.getpid(), counter[0]),
              'type':'message','role':'assistant','content':[{'type':'text','text':text}],
              'usage':{'input_tokens':1,'output_tokens':1}}})
if ENGINE == 'codex':
    emit({'type':'thread.started','thread_id':SESSION})
    emit({'type':'turn.started'})
limits = scenario.get('limit') or {}
if ENGINE != 'codex' and (limits.get(conversation) == 'all' or (limits.get(conversation) == 'once'
                          and not list(MARKERS.glob('limited-' + conversation + '-*')))):
    keep({'turn': turn, 'part': 'partial work before the limit', 'account': account})
    say('partial work')
    (MARKERS / ('limited-' + conversation + '-' + str(account))).write_text('1')
    emit({'type':'rate_limit_event','session_id':SESSION,'rate_limit_info':{'status':'rejected',
          'rateLimitType':'seven_day','resetsAt':int(time.time()) + 3600}})
    emit({'type':'result','subtype':'error_during_execution','is_error':True,'num_turns':1,'result':'stopped',
          'session_id':SESSION,'usage':{'input_tokens':1,'output_tokens':1}})
    sys.exit(1)
if ENGINE != 'codex' and conversation in (scenario.get('credential') or []):
    value = os.environ.get('CLAUDE_CODE_OAUTH_TOKEN', '')
    uid = 'toolu_cred_%d' % os.getpid()
    emit({'type':'assistant','session_id':SESSION,'message':{'id':'use-' + uid,'type':'message','role':'assistant',
          'content':[{'type':'tool_use','id':uid,'name':'Read','input':{'file_path':'credentials.txt'}}],
          'usage':{'input_tokens':1,'output_tokens':1}}})
    emit({'type':'user','session_id':SESSION,'message':{'role':'user','content':[{'type':'tool_result',
          'tool_use_id':uid,'content':'resolved credential ' + value}]}})
    keep({'turn': turn, 'tool_result': 'resolved credential ' + value})
done = [p.get('turn') for p in prior if p.get('part') == 'done']
reply = 'turn %s on %s remembers %s %s' % (turn, ENGINE, json.dumps(done),
                                           'p' * int((scenario.get('pad') or {}).get(conversation, 0)))
keep({'turn': turn, 'part': 'done'})
if ENGINE == 'codex':
    say(reply)
    emit({'type':'turn.completed','usage':{'input_tokens':12,'cached_input_tokens':0,'output_tokens':3}})
else:
    emit({'type':'rate_limit_event','session_id':SESSION,'rate_limit_info':{'status':'allowed',
          'rateLimitType':'five_hour','utilization':.25,'resetsAt':int(time.time())+3600}})
    say(reply)
    emit({'type':'result','subtype':'success','is_error':False,'num_turns':1,'result':reply,'session_id':SESSION,
          'usage':{'input_tokens':12,'output_tokens':3}})
'''

    def fake_source():
        source = J.FAKE
        if source.count(INIT) != 1 or source.count(OWN) != 1 or source.count("'session_id':'fixture-session'") != 1:
            raise RuntimeError('the VELDO-0174 fake engine moved')
        if source.count("'num_turns':0,") != 1:
            raise RuntimeError('the VELDO-0174 fake engine moved')
        source = source.replace(INIT, SESSION_CODE + INIT).replace("'session_id':'fixture-session'", "'session_id':SESSION")
        # The probe's zero-turn result names the run's session too, as the binary's does.
        source = source.replace("'num_turns':0,", "'num_turns':0,'session_id':SESSION,")
        return source[:source.index(OWN)] + BODY

    def install(tag, index, claude_accounts):
        f = F.fixture(ROOT, base, H, load, tag, index, PRODUCTION)
        fixtures.append(f)
        mods = f['root'] / 'modules'
        CV = load('v176_conversation_' + tag, mods / 'control_conversation.py')
        CS = load('v176_service_' + tag, mods / 'control_service.py')
        CS.CV = CV
        authority = f['authority']
        observations = []
        f['observations'] = observations
        f['conversations'] = CV.Conversations(authority.S, authority.conn, domain=authority.ids['domain_uuid'],
                                              principal='authority', signer='authority', sign=authority.journal_sign,
                                              state_root=f['root'] / 'state', observe=observations.append)
        saved, J.FAKE = J.FAKE, fake_source()
        try:
            receiver, markers, _ = J.engines(ROOT, f, CS)
        finally:
            J.FAKE = saved
        # The fixture bound of the Codex input (AC3), recorded where the pinned version's qualification keeps it.
        record_path = mods / 'runtime/codex-qualification.json'
        record = json.loads(record_path.read_text())
        record['history_bound'] = {'characters': BOUND, 'basis': 'the suite fixture'}
        record_path.write_text(json.dumps(record))
        # A second Claude Code role, to change role on the same engine (AC3).
        roles = dict(f['roles'])
        revision = dict(f['revisions']['assistant'], role='assistant_two')
        revision['digest'] = CV.CFG.digest({k: v for k, v in revision.items() if k != 'digest'})
        authority.fixture('configuration:assistant_two', 'agent_configuration', revision)
        roles['assistant_two'] = dict(roles['assistant'], capability_configuration={'role': 'assistant_two',
                                                                                    'revision': 1})
        authority.fixture('default-team:1', 'default_team_revision', {
            'revision': 1, 'team': {'roles': roles}, 'saved_by': 'owner', 'assertion_digest': 'sha256:fixture',
            'previous': None, 'digest': 'sha256:default-one'})
        accounts = load('v176_accounts_' + tag, mods / 'control_accounts.py').Accounts(
            authority.S, authority.conn, principal='owner', signer='authority', sign=authority.journal_sign)
        config = json.loads(receiver.read_text())
        tokens = {}
        for provider, number in [('claude_code', n) for n in range(1, claude_accounts + 1)] + [('codex', 1)]:
            account = 'account-%s-%d' % (provider, number)
            profile = f['root'] / ('profile-' + account)
            profile.mkdir(parents=True)
            accounts.register('account-register-' + account, account, provider, account, {f['host']: str(profile)},
                              concurrency=1, now=time.time())
            if provider == 'claude_code':
                # The account's subscription token: a resolved credential value of every run on it (VELDO-0141).
                value = 'v176-token-%s-%s' % (number, os.urandom(8).hex())
                path = f['root'] / ('token-' + account)
                path.write_text(value)
                path.chmod(0o600)
                tokens[account] = value
                config.setdefault('subscription_tokens', {})[account] = str(path)
        receiver.write_text(json.dumps(config))
        f.update(CV=CV, CS=CS, receiver=receiver, markers=markers, mods=mods, tokens=tokens, config=config)
        return f

    def observed(markers):
        found = {}
        for path in markers.glob('*.json'):
            if path.name.split('.')[0].isdigit() and path.name.count('.') == 1:
                value = json.loads(path.read_text())
                found[value.get('dispatch')] = value
        return found

    def runs_of(markers, identity):
        return [v for v in observed(markers).values() if ((v.get('packet') or {}).get('payload') or {})
                .get('conversation') == identity]

    def profile_sessions(f):
        """Every session file left in any account profile."""
        left = []
        for profile in f['root'].glob('profile-*'):
            left += [str(p) for p in profile.rglob('*.jsonl')]
        return left

    def start_loop(f):
        """J.loop's stand-in service and factory loop, with what Service carries for the decision flow (its store,
        journal key and inbox) before the loop starts, since its start recovers turns and may tell the owner."""
        from types import SimpleNamespace
        CS, authority, events = f['CS'], f['authority'], []
        service = SimpleNamespace(
            config={'receiver': {'conversations': str(f['receiver'])}, 'journal_key': str(authority.keyfile['authority'])},
            conn=authority.conn, domain=authority.ids['domain_uuid'], principal='authority', generation=1,
            sign=authority.journal_sign, conversations=lambda: f['conversations'], _log=events.append,
            repositories={}, store=authority.ids['store_uuid'],
            watermark=lambda: authority.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0],
            inbox=lambda coordinate: CS.I.Inbox(
                CS.S, CS.CM, CS.CLM, CS.ENT, authority.conn,
                {'domain_uuid': authority.ids['domain_uuid'], 'repository_uuid': coordinate,
                 'store_uuid': authority.ids['store_uuid']}, 'authority', authority.journal_sign, 1))
        wrapper = f['root'] / 'receiver-driver.py'
        wrapper.write_text('import runpy,sys\nsys.stderr=open(' + repr(str(f['root'] / 'receiver-errors.log'))
                           + ", 'a')\nrunpy.run_path(" + repr(str(f['mods'] / 'control_launch.py'))
                           + ",run_name='__main__')\n")
        CS.L.RECEIVER = str(wrapper)
        factory = CS.FactoryLoop(service, None)
        lock = CS.acquire(str(authority.db.parent / 'authority.lock'), {'principal': 'authority'})
        factory.lock = lock
        factories.append((factory, lock))
        factory.start()
        launched = []
        prepared = factory.conversation.runner.launch_prepared

        def keeping(contract):
            launch = prepared(contract)
            launched.append(launch)
            return launch
        factory.conversation.runner.launch_prepared = keeping
        return factory, events, launched

    def release_lock(lock_value):
        close = getattr(lock_value, 'close', None)
        if close:
            close()
        elif isinstance(lock_value, int):
            try:
                os.close(lock_value)
            except OSError:
                pass

    def answer(f, factory, identity, aid, ruling):
        """The owner's signed answer to a conversation question, through the production inbox (VELDO-0064)."""
        authority = f['authority']
        inbox = factory.service.inbox(f['CV'].conversation_id(identity))
        item = inbox.read(aid)
        body = {'domain_uuid': authority.ids['domain_uuid'], 'repository_uuid': f['CV'].conversation_id(identity),
                'store_uuid': authority.ids['store_uuid'], 'operation': 'answer', 'alias': item['data']['alias'],
                'principal': 'owner', 'command_id': 'v176-answer-' + aid[-12:] + ruling, 'nonce': 'v176-' + aid[-12:] + ruling,
                'request_version': item['data']['request_version'], 'ruling': ruling}
        return inbox.apply({'command': body, 'signature': authority.sign_as('owner', authority.S.canonical_bytes(body))})

    def turns(f, identity):
        return f['conversations'].turns(identity)

    def settled(f, identity, count):
        saved = turns(f, identity)
        return len(saved) >= count and saved[count - 1].get('state') == 'ended'

    def say(f, identity, text):
        return f['conversations'].message(identity, identity + '-' + text, 'sha256:' + identity + text, owner='owner')

    def run_turn(f, factory, identity, text, count, seconds=40):
        say(f, identity, text)
        J.pass_(factory)
        return F.drive(factory, lambda: settled(f, identity, count), seconds)

    def digest(path):
        return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()

    try:
        f = install('main', 76, 3)
        CV, markers, authority = f['CV'], f['markers'], f['authority']
        conversations = f['conversations']
        factory, events, launched = start_loop(f)
        scenario = {'credential': ['moving'], 'limit': {}, 'pad': {'long': 700}}
        (markers / 'scenario.json').write_text(json.dumps(scenario))

        # AC1: turn 1 on account A, turn 2 on account B.
        conversations.open('remember', owner='owner', role='assistant', intake_digest='sha256:remember')
        run_turn(f, factory, 'remember', 'one', 1)
        first = turns(f, 'remember')[0]
        one = runs_of(markers, 'remember')
        # Account A is busy with another conversation's held turn, so the pool picks another account for turn 2.
        conversations.open('blocker', owner='owner', role='assistant', intake_digest='sha256:blocker')
        (markers / 'hold-blocker').write_text('1')
        say(f, 'blocker', 'one')
        J.pass_(factory)
        J.eventually(lambda: runs_of(markers, 'blocker'), 20)
        run_turn(f, factory, 'remember', 'two', 2)
        (markers / 'hold-blocker').unlink()
        F.drive(factory, lambda: settled(f, 'blocker', 1), 30)
        second = turns(f, 'remember')[1]
        two = [r for r in runs_of(markers, 'remember') if r not in one]
        run_one = one[0] if one else {}
        run_two = two[0] if two else {}
        print('  VELDO-0176 AC1 accounts:', first.get('account'), second.get('account'), 'sessions:',
              run_one.get('session'), run_two.get('session'), 'outcomes:', first.get('outcome'), second.get('outcome'))
        check('AC1/any-account', 'turn 1 ran on account A and turn 2 on account B, both completed',
              first.get('account') == 'account-claude_code-1' and second.get('account') == 'account-claude_code-2'
              and first.get('outcome') == 'completed' and second.get('outcome') == 'completed')
        check('AC1/any-account', 'turn 2 resumed turn 1\'s session on B: the engine reported the same session id',
              run_one.get('session') and run_two.get('session') == run_one.get('session')
              and run_two.get('resumed') == run_one.get('session')
              and (second.get('session') or {}).get('session_id') == run_one.get('session'))
        check('AC1/any-account', 'the fake engine on B read the placed session: it remembers turn 1',
              [p.get('turn') for p in run_two.get('prior') or [] if p.get('part') == 'done'] == [1]
              and str(run_two.get('profile', '')).endswith('profile-account-claude_code-2'))
        check('AC1/any-account', 'the launch named the resume option with the held session id',
              '--resume' in (run_two.get('argv') or []) and
              (run_two.get('argv') or [])[(run_two.get('argv') or ['']).index('--resume') + 1:][:1] == [run_one.get('session')]
              if '--resume' in (run_two.get('argv') or []) else False)
        held = second.get('session') or {}
        capture = Path(held.get('capture') or '/nonexistent/v176')
        check('AC1/capture-kept', 'the capture is kept under the conversation\'s directory at mode 0600',
              capture.is_file() and oct(capture.stat().st_mode & 0o777) == '0o600'
              and str(capture).startswith(conversations.read('remember')['directory'] + '/sessions/claude_code/'))
        check('AC1/capture-kept', 'its digest is bound to the turn record',
              capture.is_file() and digest(capture) == held.get('digest')
              and [c.get('digest') for c in second.get('captures') or []] == [held.get('digest')])
        C = load('v176_claude_engine', f['mods'] / 'control_engine_claude.py')
        check('AC1/capture-kept', 'its relative place is the profile\'s projects directory for the workspace',
              held.get('relative') == 'projects/%s/%s.jsonl' % (
                  C.project_directory_name(CV.workspace_of(conversations.read('remember'))), run_one.get('session')))
        check('AC1/capture-kept', 'no session stays in any account profile after the turns [%s]' % profile_sessions(f),
              not profile_sessions(f))
        invocation = factory.conversation.invocation(second.get('dispatch_id') or '') or {}
        check('AC1/resume-qualified', 'the meter charged the resumed session\'s difference [%s]'
              % (invocation.get('session') or {}).get('charged'),
              (invocation.get('session') or {}).get('charged') == 'difference'
              and (invocation.get('session') or {}).get('id') == run_one.get('session'))
        shipped_claude = json.loads((ROOT / '.veldo/runtime/claude-qualification.json').read_text())
        shipped_codex = json.loads((ROOT / '.veldo/runtime/codex-qualification.json').read_text())
        claude_entry = next(iter(shipped_claude['versions'].values()))
        check('AC1/resume-qualified', 'the pinned versions\' qualification records name the resume options and bounds',
              (claude_entry.get('resume') or {}).get('option') == '--resume'
              and (shipped_codex.get('resume') or {}).get('argv') == ['resume', '{session}', '-']
              and isinstance((claude_entry.get('history_bound') or {}).get('characters'), int)
              and isinstance((shipped_codex.get('history_bound') or {}).get('characters'), int))
        X = load('v176_codex_engine', f['mods'] / 'control_engine_codex.py')
        check('AC1/resume-qualified', 'an engine version not qualified with the resume option is refused by name',
              X.resume_problem({'version': '0.0.1'}) == 'missing_evidence:engine_resume:0.0.1'
              and C.resume_problem({'version': '9.9.9', 'resume': None}) == 'missing_evidence:engine_resume:9.9.9'
              and X.resume_argv({'resume': shipped_codex['resume']}, 't-1') == ['resume', 't-1', '-'])

        # An engine that reports another session id than the one placed is stopped by name: the scenario makes the
        # fake Claude Code start a new session whatever `--resume` names.
        conversations.open('swapped', owner='owner', role='assistant', intake_digest='sha256:swapped')
        run_turn(f, factory, 'swapped', 'one', 1)
        original = (turns(f, 'swapped')[0].get('session') or {})
        (markers / 'scenario.json').write_text(json.dumps(dict(scenario, fresh=True)))
        run_turn(f, factory, 'swapped', 'two', 2)
        (markers / 'scenario.json').write_text(json.dumps(scenario))
        swapped_two = turns(f, 'swapped')[1]
        swapped_runs = [r for r in runs_of(markers, 'swapped')
                        if ((r.get('packet') or {}).get('payload') or {}).get('turn') == 2]
        print('  VELDO-0176 AC1 swapped:', swapped_two.get('outcome'), [r.get('session') for r in swapped_runs])
        reported_other = [m for launch in launched for m in launch.messages
                          if m.get('event') == 'conversation_session' and m.get('conversation') == 'swapped'
                          and m.get('turn') == 2]
        check('AC1/resume-mismatch', 'an engine that reports another session than the placed one is stopped by name',
              swapped_two.get('outcome') == 'binding_mismatch:conversation_resume' and not swapped_runs
              and reported_other and reported_other[0].get('resumed') == original.get('session_id')
              and reported_other[0].get('reported') not in (None, original.get('session_id'))
              and reported_other[0].get('refusal') == 'binding_mismatch:conversation_resume')
        check('AC1/resume-mismatch', 'its session is not bound: the held session stays turn 1\'s, and nothing stays in '
              'the profile', swapped_two.get('session') is None
              and CV.held_session(authority.conn, 'swapped', 'claude_code').get('session_id') == original.get('session_id')
              and not profile_sessions(f))
        check('AC1/resume-mismatch', 'turns stopped so are counted [%s]' % conversations.status().get('sessions'),
              (conversations.status().get('sessions') or {}).get('resume_mismatch') == 1)
        check('AC1/observability', 'each capture and placement is logged with conversation, turn, engine, session, '
              'account and digest, never content',
              any(o.get('operation') == 'session_capture' and o.get('conversation') == 'remember'
                  and o.get('sequence') == 2 and o.get('session_id') == run_one.get('session')
                  and o.get('account') == 'account-claude_code-2' and o.get('digest') == held.get('digest')
                  for o in f['observations'])
              and any(m.get('event') == 'conversation_session_placed' and m.get('account') == 'account-claude_code-2'
                      and m.get('session_id') == run_one.get('session') for launch in launched
                      for m in launch.messages)
              and not any('partial work' in json.dumps(o) or 'remembers' in json.dumps(o) for o in f['observations']))
        check('AC1/observability', 'each resumption reports the session id the engine reported',
              any(m.get('event') == 'conversation_session' and m.get('resumed') == run_one.get('session')
                  and m.get('reported') == run_one.get('session') for launch in launched for m in launch.messages))
        check('AC1/observability', 'captures and resumed turns are counted [%s]' % conversations.status().get('sessions'),
              (conversations.status().get('sessions') or {}).get('captures', 0) >= 4
              and (conversations.status().get('sessions') or {}).get('resumed', 0) >= 2)

        # AC3: a role on the same engine keeps resuming the held session.
        conversations.open('moving', owner='owner', role='assistant', intake_digest='sha256:moving')
        run_turn(f, factory, 'moving', 'one', 1)
        version = conversations.read('moving')['version']
        conversations.change_role('moving', version, 'assistant_two', owner='owner')
        run_turn(f, factory, 'moving', 'two', 2)
        moving = turns(f, 'moving')
        check('AC3/same-engine', 'after a role change on the same engine the next turn resumes the held session',
              [t.get('outcome') for t in moving] == ['completed', 'completed']
              and (moving[1].get('starts') or [{}])[-1].get('mode') == 'resumed'
              and (moving[1].get('session') or {}).get('session_id') == (moving[0].get('session') or {}).get('session_id'))
        token_value = f['tokens'][moving[0]['account']]
        capture_one = Path((moving[1].get('session') or {}).get('capture') or '/nonexistent/v176')
        check('AC3/redaction', 'the held Claude Code session itself carries the resolved credential value',
              capture_one.is_file() and token_value in capture_one.read_text())

        # Long history: a second conversation's history is three times the fixture bound.
        conversations.open('long', owner='owner', role='assistant', intake_digest='sha256:long')
        for number in range(1, 9):
            run_turn(f, factory, 'long', 'turn%d' % number, number)
        long_turns = turns(f, 'long')
        records = CV.history(authority.conn, f['CS'].L.ER.directory(f['config']), 'long', 9, f['CS'].L.ER.read)
        whole = CV.render(records, 10 ** 9)
        print('  VELDO-0176 AC3 long history characters:', whole['characters'], 'bound:', BOUND)
        check('AC3/long-history', 'the second conversation\'s history is three times the fixture bound',
              [t.get('outcome') for t in long_turns] == ['completed'] * 8 and whole['characters'] >= 3 * BOUND)

        # AC3: a held session whose digest differs from its turn record is refused by name, before anything is
        # spawned, and never replaced by a rendering.
        tampered = Path((turns(f, 'remember')[1].get('session') or {}).get('capture') or '/nonexistent/v176')
        tampered.write_text(tampered.read_text() + json.dumps({'turn': 99, 'part': 'done'}) + '\n')
        before = len(observed(markers))
        run_turn(f, factory, 'remember', 'three', 3)
        refused_turn = turns(f, 'remember')[2]
        refusals = [m for launch in launched for m in launch.messages
                    if m.get('event') == 'conversation_session_refused' and m.get('conversation') == 'remember']
        check('AC3/digest-refused', 'the turn is refused binding_mismatch:conversation_session and nothing ran [%s]'
              % refused_turn.get('outcome'),
              refused_turn.get('outcome') == 'binding_mismatch:conversation_session' and len(observed(markers)) == before
              and refusals and refusals[0].get('session_id') == (turns(f, 'remember')[1].get('session') or {}).get('session_id'))
        check('AC3/digest-refused', 'it was never replaced by a rendering and nothing was captured for it',
              not refused_turn.get('starts') and not refused_turn.get('captures')
              and not any(m.get('event') == 'conversation_history' and m.get('conversation') == 'remember'
                          for launch in launched for m in launch.messages))
        check('AC3/digest-refused', 'turns stopped so are counted [%s]' % conversations.status().get('sessions'),
              (conversations.status().get('sessions') or {}).get('session_mismatch') == 1)

        # AC2: account A limited in the middle of a turn.
        scenario['limit'] = {'limited': 'once'}
        (markers / 'scenario.json').write_text(json.dumps(scenario))
        conversations.open('limited', owner='owner', role='assistant', intake_digest='sha256:limited')
        run_turn(f, factory, 'limited', 'one', 1, 60)
        limited = turns(f, 'limited')[0]
        attempts = limited.get('attempts') or []
        limited_runs = runs_of(markers, 'limited')
        print('  VELDO-0176 AC2 limited attempts:', [(a.get('account'), a.get('dispatch_id')[-6:]) for a in attempts],
              'outcome:', limited.get('outcome'), 'limits:', limited.get('limits'))
        first_run = next((r for r in limited_runs if r.get('dispatch') == (attempts[0] if attempts else {}).get('dispatch_id')), {})
        rerun = next((r for r in limited_runs if r.get('dispatch') == (attempts[-1] if attempts else {}).get('dispatch_id')), {})
        check('AC2/continues-after-a-limit', 'the turn ran again under a new dispatch identity on another account and '
              'completed', len(attempts) == 2 and attempts[0]['dispatch_id'] != attempts[1]['dispatch_id']
              and attempts[0]['account'] != attempts[1]['account'] and limited.get('outcome') == 'completed'
              and (limited.get('limits') or [{}])[0].get('account') == attempts[0]['account'])
        check('AC2/continues-after-a-limit', 'the re-run resumed the captured session, not a fresh one',
              first_run.get('session') and rerun.get('session') == first_run.get('session')
              and rerun.get('resumed') == first_run.get('session')
              and 'partial work before the limit' in [p.get('part') for p in rerun.get('prior') or []])
        check('AC2/continues-after-a-limit', 'its input said the previous run stopped at an account limit',
              ((rerun.get('packet') or {}).get('payload') or {}).get('notice') == CV.LIMIT_NOTICE)
        check('AC2/continues-after-a-limit', 'the loop decided re-run over the record (VELDO-0160 AC3)',
              (limited.get('limits') or [{}])[0].get('decision') == 'rerun')

        # Every Claude Code account at its limit: the owner is asked, and nothing moves before his answer.
        scenario['limit'] = {'waiting': 'all', 'moving': 'all'}
        (markers / 'scenario.json').write_text(json.dumps(scenario))
        conversations.open('waiting', owner='owner', role='assistant', intake_digest='sha256:waiting')
        say(f, 'waiting', 'one')
        J.pass_(factory)
        F.drive(factory, lambda: turns(f, 'waiting')[0].get('state') == 'ended' or any(
            q.get('about') == f['CS'].MOVE_KIND for q in (turns(f, 'waiting')[0].get('questions') or [])), 60)
        waiting = turns(f, 'waiting')[0]
        question = next((q for q in waiting.get('questions') or [] if q.get('about') == f['CS'].MOVE_KIND), {})
        codex_before = [r for r in observed(markers).values() if r.get('engine') == 'codex']
        print('  VELDO-0176 AC2 all limited:', [a.get('account') for a in waiting.get('attempts') or []],
              'question:', question.get('ref'), 'state:', waiting.get('state'))
        inbox_item = factory.service.inbox(CV.conversation_id('waiting')).read(question.get('ref') or 'none')
        check('AC2/ask', 'with every Claude Code account at its limit the owner is asked through the decision flow',
              question and inbox_item and inbox_item['data']['choices'] == ['wait', 'move']
              and inbox_item['data']['owner'] == 'owner' and 'Every claude_code account is at its limit'
              in inbox_item['data']['brief'] and 'assistant_codex' in inbox_item['data']['brief'])
        F.drive(factory, lambda: False, 2)
        check('AC2/ask', 'nothing moves before his answer: no Codex turn ran and the role is unchanged',
              not codex_before and not [r for r in observed(markers).values() if r.get('engine') == 'codex']
              and conversations.read('waiting')['role'] == 'assistant' and turns(f, 'waiting')[0]['state'] == 'waiting')
        answered = answer(f, factory, 'waiting', question['ref'], 'wait') if question else {}
        J.pass_(factory)
        F.drive(factory, lambda: False, 1)
        waited = turns(f, 'waiting')[0]
        check('AC2/wait', 'his wait leaves the turn waiting for the reset, on its engine',
              answered.get('ok') and waited['state'] == 'waiting' and conversations.read('waiting')['role'] == 'assistant'
              and not [r for r in observed(markers).values() if r.get('engine') == 'codex']
              and [q.get('answer') for q in waited.get('questions') or [] if q.get('about') == f['CS'].MOVE_KIND] == ['wait'])
        check('AC2/wait', 'the turn waits for the reset its question named (the loop\'s reset wake)',
              question.get('until', '').isdigit() and int(question['until']) > time.time())

        # The other conversation: asked, then moved by his answer, and its first Codex turn starts from the history.
        say(f, 'moving', 'three')
        J.pass_(factory)
        F.drive(factory, lambda: turns(f, 'moving')[2].get('state') == 'ended' or any(
            q.get('about') == f['CS'].MOVE_KIND for q in (turns(f, 'moving')[2].get('questions') or [])), 60)
        asked = next((q for q in turns(f, 'moving')[2].get('questions') or [] if q.get('about') == f['CS'].MOVE_KIND), {})
        check('AC2/ask', 'the second conversation is asked too, and no Codex turn runs without a settled answer',
              asked and not [r for r in observed(markers).values() if r.get('engine') == 'codex']
              and conversations.read('moving')['role'] == 'assistant_two')
        moved = answer(f, factory, 'moving', asked['ref'], 'move') if asked else {}
        J.pass_(factory)
        F.drive(factory, lambda: settled(f, 'moving', 3), 40)
        third = turns(f, 'moving')[2]
        codex_runs = [r for r in runs_of(markers, 'moving') if r.get('engine') == 'codex']
        check('AC2/move', 'his move sends his role change and the turn runs on Codex under AC3',
              moved.get('ok') and conversations.read('moving')['role'] == 'assistant_codex'
              and third.get('outcome') == 'completed' and len(codex_runs) == 1
              and (third.get('starts') or [{}])[-1].get('mode') == 'rendered')
        history = ((codex_runs[0] if codex_runs else {}).get('packet') or {}).get('history') or ''
        check('AC3/redaction', 'the Codex turn\'s first input is the rendering of the earlier turns from their records',
              history.startswith(CV.LEFT_OUT % 0) and 'Turn 1' in history and 'Turn 2' in history
              and 'Tool call: Read' in history and 'Tool result: resolved credential [REDACTED' in history)
        check('AC3/redaction', 'the credential value is not in the Codex turn\'s first input',
              codex_runs and token_value not in json.dumps(codex_runs[0].get('packet'))
              and not any(t in json.dumps(codex_runs[0].get('packet')) for t in f['tokens'].values()))
        check('AC3/redaction', 'the Codex turn started a fresh session (nothing to resume on Codex)',
              codex_runs and codex_runs[0].get('resumed') is None and 'resume' not in (codex_runs[0].get('argv') or []))

        # The long conversation moves by the owner's role change: newest whole turns that fit the bound.
        version = conversations.read('long')['version']
        conversations.change_role('long', version, 'assistant_codex', owner='owner')
        run_turn(f, factory, 'long', 'turn9', 9)
        long_nine = turns(f, 'long')[8]
        long_codex = [r for r in runs_of(markers, 'long') if r.get('engine') == 'codex']
        text = ((long_codex[0] if long_codex else {}).get('packet') or {}).get('history') or ''
        started = (long_nine.get('starts') or [{}])[-1]
        kept = [int(line.split()[1]) for line in text.splitlines() if line.startswith('Turn ')]
        print('  VELDO-0176 AC3 long rendering: kept', kept, 'left out', started.get('left_out'), 'characters',
              len(text), 'outcome', long_nine.get('outcome'))
        check('AC3/long-history', 'the turn ran (completed) on Codex from a shortened rendering, never refused',
              long_nine.get('outcome') == 'completed' and len(long_codex) == 1 and started.get('mode') == 'rendered'
              and started.get('left_out', 0) > 0)
        check('AC3/long-history', 'the rendering fits the bound and opens with one line naming the turns left out',
              0 < len(text) <= BOUND and text.splitlines()[0] == CV.LEFT_OUT % started.get('left_out')
              and started.get('left_out') == 8 - len(kept))
        check('AC3/long-history', 'it carries the newest whole turns, each with its whole reply',
              kept and kept == list(range(9 - len(kept), 9))
              and all(('Reply: turn %d on claude_code remembers' % n) in text for n in kept)
              and text.count('p' * 700) == len(kept))
        check('AC3/long-history', 'the full history stays in the factory\'s record',
              len(CV.history(authority.conn, f['CS'].L.ER.directory(f['config']), 'long', 10, f['CS'].L.ER.read)) == 9)

        # A change back to the Claude Code role resumes its held session (kept through the Codex turn). Every Claude
        # Code account is still at its limit in this fixture, so the change back is checked on the held session the
        # next offer names.
        version = conversations.read('moving')['version']
        conversations.change_role('moving', version, 'assistant', owner='owner')
        claude_held = CV.held_session(authority.conn, 'moving', 'claude_code')
        codex_held = CV.held_session(authority.conn, 'moving', 'codex')
        check('AC3/change-back', 'the earlier engine\'s held session is kept, and the change back resumes it',
              claude_held and claude_held.get('session_id') == (moving[1].get('session') or {}).get('session_id')
              and Path(claude_held['capture']).is_file() and digest(claude_held['capture']) == claude_held['digest']
              and codex_held and codex_held.get('engine') == 'codex')

        # AC2: restarts.
        # A turn running when the loop's service restarts is outcome_unknown, the owner is told, and the last capture
        # stays and is resumed by his next message (a new factory loop over the same store: the restarted service's).
        r = install('running', 78, 1)
        rfactory, _revents, _rlaunched = start_loop(r)
        (r['markers'] / 'scenario.json').write_text(json.dumps({}))
        r['conversations'].open('interrupted', owner='owner', role='assistant', intake_digest='sha256:interrupted')
        run_turn(r, rfactory, 'interrupted', 'one', 1)
        last_capture = (turns(r, 'interrupted')[0].get('session') or {})
        (r['markers'] / 'hold-interrupted').write_text('1')
        say(r, 'interrupted', 'two')
        J.pass_(rfactory)
        J.eventually(lambda: len(runs_of(r['markers'], 'interrupted')) >= 2, 20)
        # The first service ends while its turn runs: its authority lock goes with it, its receiver is left running.
        release_lock(factories[-1][1])
        factories[-1] = (rfactory, None)
        restarted, _restart_events, _restart_launched = start_loop(r)
        (r['markers'] / 'hold-interrupted').unlink()
        interrupted = turns(r, 'interrupted')[1]
        notices = interrupted.get('notices') or []
        told = r['CS'].I.assignment_id(r['CV'].conversation_id('interrupted'), '')
        item = restarted.service.inbox(r['CV'].conversation_id('interrupted')).read(notices[0]['ref']) if notices else None
        print('  VELDO-0176 AC2 running at restart:', interrupted.get('state'), interrupted.get('outcome'), notices,
              (item or {}).get('data', {}).get('kind'))
        check('AC2/running-at-restart', 'a turn running at the restart is outcome_unknown and the owner is told',
              interrupted.get('outcome') == 'outcome_unknown' and notices and notices[0]['ref'].startswith(told)
              and item and item['data']['kind'] == 'acknowledgement' and 'restarted' in item['data']['brief'])
        run_turn(r, restarted, 'interrupted', 'three', 3)
        third_turn = turns(r, 'interrupted')[2]
        resumed_run = [x for x in runs_of(r['markers'], 'interrupted') if (x.get('packet') or {}).get('payload', {}).get('turn') == 3]
        check('AC2/running-at-restart', 'the last capture stays and his next message resumes from it',
              third_turn.get('outcome') == 'completed' and resumed_run
              and resumed_run[0].get('resumed') == last_capture.get('session_id')
              and 1 in [p.get('turn') for p in resumed_run[0].get('prior') or [] if p.get('part') == 'done'])

        # The production service, restarted between two turns over the same store.
        s = install('restart', 79, 1)
        (s['markers'] / 'scenario.json').write_text(json.dumps({}))
        before_restart, after_restart = J.restart(s, s['CS'], ROOT, receiver=s['receiver'], identity='restart-turns',
                                                  turns=True)
        saved = turns(s, 'restart-turns')
        restart_runs = sorted(runs_of(s['markers'], 'restart-turns'),
                              key=lambda x: (x.get('packet') or {}).get('payload', {}).get('turn') or 0)
        print('  VELDO-0176 AC2 restart:', [t.get('outcome') for t in saved],
              [(x.get('session'), x.get('resumed')) for x in restart_runs])
        check('AC2/restart', 'after a service restart between two turns the next message resumes the conversation',
              before_restart == after_restart and [t.get('outcome') for t in saved] == ['completed', 'completed']
              and len(restart_runs) == 2 and restart_runs[1].get('resumed') == restart_runs[0].get('session')
              and restart_runs[1].get('session') == restart_runs[0].get('session')
              and [p.get('turn') for p in restart_runs[1].get('prior') or [] if p.get('part') == 'done'] == [1])

        status = conversations.status().get('sessions') or {}
        print('  VELDO-0176 metrics:', status)
        check('AC3/observability', 'turns started from a rendering and from a shortened one are counted',
              status.get('rendered', 0) >= 2 and status.get('rendered_shortened', 0) >= 1)
        check('AC3/observability', 'engine questions are counted by answer',
              (status.get('questions') or {}).get('wait') == 1 and (status.get('questions') or {}).get('move') == 1)
        check('AC3/observability', 'each rendering is logged with its turn count, the turns left out and its digest',
              any(m.get('event') == 'conversation_history' and m.get('conversation') == 'long' and m.get('left_out')
                  and m.get('digest') == started.get('digest') for launch in launched for m in launch.messages))
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in ROWS:
            check(row, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        for factory_value, lock_value in factories:
            try:
                for launch in list(factory_value.conversation.runner.launches.values()):
                    launch.stop('requested')
            except Exception:  # noqa: BLE001
                pass
            release_lock(lock_value)
        for value in fixtures:
            value['authority'].conn.close()
        shutil.rmtree(base, ignore_errors=True)
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0176 detail:', row, '; '.join(failed))
        expect('VELDO-0176 ' + row, bool(rows[row]) and not failed)


_v176_suite()
