"""VELDO-0231: a running agent flags the lead without stopping, and the flag reaches the lead's conversation at once.

Run: python3 scripts/selftest.py --suite 127_veldo_0231_run_flags

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support), the production
conversation authority, VELDO-0174's conversation Line and its real receiver subprocesses over fake pinned engines
(scripts/suites/support/v231_fake_engines.py, built on VELDO-0174's), and the service loop's poll over the launch
pipes (the factory loop's pipes and readable). Fake engines only: no real Claude Code or Codex runs, no login, no
network beyond loopback. The qualify command's flag probe runs over fake Codex binaries on loopback.
"""


def _v231_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import time

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Literal anchors: the registered mutation driver substitutes each production copy here, and the fixture's
    # module copy (which the receivers run) takes each of them.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_conversation.py': ROOT / ".veldo" / "control_conversation.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
        'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
        'qualify.py': ROOT / ".veldo" / "qualify.py",
    }
    ROWS = ('AC1/at-once', 'AC1/run-goes-on', 'AC1/lead-conversation', 'AC1/observability',
            'AC2/codex-launch', 'AC2/decisions', 'AC2/switch', 'AC2/probe', 'AC2/marked-line',
            'AC3/save-refused', 'AC3/instructions', 'AC3/probe-answer', 'AC3/answered', 'AC3/blocking',
            'AC4/flood', 'AC4/per-run-cap', 'AC4/nothing-outward')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def refusal(call):
        try:
            call()
        except Exception as error:  # noqa: BLE001
            return getattr(error, 'code', type(error).__name__)
        return None

    H = load('v231_authority', ROOT / 'scripts/suites/support/v73_authority.py')
    J = load('v231_journey', ROOT / 'scripts/suites/support/v174_journey.py')
    F = load('v231_fakes', ROOT / 'scripts/suites/support/v231_fake_engines.py')
    MEANS = F.MEANS
    base = Path(tempfile.mkdtemp(prefix='v231-', dir=fast_temp()))
    fixtures = []
    lock = factory = None

    def stop_all(loop):
        """Every run still going is asked to stop, and its end is read, so none outlives the suite."""
        running = list(loop.conversation.runner.launches.values())
        for launch in running:
            launch.stop('requested')
        F.drive(loop, lambda: all(launch.ended for launch in running), 20)
    try:
        # The fixture's modules: the production copies the suite names (mutation-substituted) beside the rest.
        f = F.fixture(ROOT, base, H, load, 'flags', 0, PRODUCTION)
        fixtures.append(f)
        mods = f['root'] / 'modules'
        CV = load('v231_conversation', mods / 'control_conversation.py')
        CS = load('v231_service', mods / 'control_service.py')
        CS.CV = CV
        L = CS.L
        X = load('v231_engine_codex', mods / 'control_engine_codex.py')
        C = load('v231_engine_claude', mods / 'control_engine_claude.py')
        CFG = load('v231_agent_config', mods / 'control_agent_config.py')
        HO = load('v231_handoff', mods / 'control_agent_config_handoff.py')
        Q = load('v231_qualify', mods / 'qualify.py')
        authority = f['authority']
        conversations = CV.Conversations(authority.S, authority.conn, domain=authority.ids['domain_uuid'],
                                         principal='authority', signer='authority', sign=authority.journal_sign,
                                         state_root=f['root'] / 'state')
        f['conversations'] = conversations
        receiver, markers, _ = F.install(ROOT, f, CS, J, load('v231_accounts', mods / 'control_accounts.py'))
        (markers / 'release').touch()
        factory, lock, events = J.loop(f, CS, receiver)
        dispatches = factory.conversation.dispatches

        # Each commit of a flag, on the wall clock, with the state its dispatch was in at that moment.
        commits = []
        original_flag = conversations.flag

        def timed(dispatch_id, **fields):
            result = original_flag(dispatch_id, **fields)
            commits.append({'wall': time.time(), 'dispatch_id': dispatch_id, 'result': result,
                            'state': (dispatches.record(dispatch_id) or {}).get('state')})
            return result
        conversations.flag = timed

        def turn(identity, role, scenario, seconds=40):
            (markers / 'scenario.json').write_text(json.dumps(scenario))
            conversations.open(identity, owner='owner', role=role, intake_digest='sha256:' + identity)
            conversations.message(identity, identity + '-1', 'sha256:' + identity + '-1', owner='owner')
            started = len(commits)
            J.pass_(factory)
            ended = F.drive(factory, lambda: (conversations.turns(identity) or [{}])[-1].get('state') == 'ended',
                            seconds)
            saved = conversations.turns(identity)[-1]
            return saved, ended, commits[started:]

        stamp = re.compile(r'stamp=([0-9.]+)')

        # AC1: ten flags from a running Claude Code agent (SendUserMessage), the service's rate window on the
        # suite's clock (61 seconds per reading) so that each is deliverable; the run goes on for 5 seconds after.
        clock = {'now': time.time()}

        def stepping():
            clock['now'] += 61
            return clock['now']
        factory.clock = stepping
        flagged, ended, made = turn('flags-claude', 'assistant', {'mode': 'flags', 'count': 10, 'interval': .3,
                                                                 'after': 5})
        latencies = [c['wall'] - float(stamp.search(c['result']['flag']['text']).group(1))
                     for c in made if c['result']['flag'] and stamp.search(c['result']['flag']['text'])]
        delivered = conversations.flags('flags-claude')
        (base / 'ac1-latencies.json').write_text(json.dumps(latencies))
        print('  VELDO-0231 AC1 latencies (s):', ', '.join('%.3f' % v for v in latencies))
        check('AC1/at-once', 'the turn ended', ended)
        check('AC1/at-once', 'ten flags committed, %d' % len(made), len(made) == 10 and len(latencies) == 10)
        check('AC1/at-once', 'each within 2 seconds of the engine writing it: max %.3f' % max(latencies or [99]),
              len(latencies) == 10 and max(latencies) < 2)
        states = sorted({c['state'] for c in made})
        check('AC1/at-once', 'each committed while the dispatch is still running: %s' % states,
              bool(made) and all(c['state'] == 'running' for c in made))
        check('AC1/at-once', "each in the run's own conversation", len(delivered) == 10 and all(
            d['conversation'] == 'flags-claude' for d in delivered))
        check('AC1/run-goes-on', 'each names the run id, the engine and the text', all(
            d['dispatch_id'] == flagged['dispatch_id'] and d['engine'] == 'claude_code'
            and d['means'] == 'SendUserMessage' and d['text'].startswith('flag ') for d in delivered))
        plain, ended_plain, none = turn('flags-none', 'assistant', {'mode': 'none', 'after': 5})
        check('AC1/run-goes-on', 'the outcome with flags (%s) is the one with none (%s)'
              % (flagged.get('outcome'), plain.get('outcome')),
              ended and ended_plain and flagged.get('outcome') == plain.get('outcome') == 'completed' and not none)

        # The lead's conversation of a project run, and a flag with none to receive it.
        project = 'activation-repository'
        authority.fixture('project:' + project, 'project', {'name': project, 'owner': 'owner'})
        for identity in ('lead-older', 'lead-newer'):
            opened = conversations.open(identity, owner='owner', intake_digest='sha256:' + identity)
            conversations.attach_project(identity, opened['version'], project, owner='owner')
            time.sleep(.01)
        led = conversations.flag('project-run-1', engine='codex', means='marked_line', text='x' * 2500,
                                 at=time.time(), read_at=time.time(), project=project)
        orphan = conversations.flag('project-run-2', engine='codex', means='marked_line', text='nobody',
                                    at=time.time(), project='no-such-project')
        counts = conversations.flag_counts()
        check('AC1/lead-conversation', 'a project run flags the most recently opened open conversation attached to '
              'its project', led['conversation'] == 'lead-newer' and led['outcome'] == 'delivered')
        check('AC1/lead-conversation', 'its text is kept to its first 2000 characters',
              len(led['flag']['text']) == 2000 and led['flag']['length'] == 2500)
        check('AC1/lead-conversation', 'with no conversation it is kept, counted and named undelivered:no_conversation',
              orphan['outcome'] == CV.UNDELIVERED == 'undelivered:no_conversation'
              and orphan['flag']['conversation'] is None and orphan['flag']['refusal'] == CV.UNDELIVERED
              and counts['by_means']['codex/marked_line']['undelivered'] == 1)

        # AC1 observability: the service's records of each flag, without its text; the flag's joins.
        logged = [e for e in events if e.get('kind') == 'flag' and e.get('operation') == 'flag']
        check('AC1/observability', 'each delivered flag logged with dispatch, engine, means, length, conversation, '
              'flag and held back counts, never its text', len(logged) >= 10 and all(
                  'text' not in e and {'dispatch_id', 'engine', 'means', 'length', 'conversation', 'flags',
                                       'held_back', 'outcome'} <= set(e) for e in logged))
        check('AC1/observability', 'each flag record joins its account and the execution record sequence it was read '
              'from', all(isinstance(d.get('sequence'), int) and d.get('account') and d.get('read_at')
                          for d in delivered))
        check('AC1/observability', 'delivered flags are counted per engine and means with their latency',
              len(counts['by_means'].get('claude_code/SendUserMessage', {}).get('latencies', [])) == 10)

        # AC2: a Codex role that lists request_user_input_async launches (the wire set equals the role's with both
        # tools the switch delivers) and its flags arrive by the recorded form.
        factory.clock = stepping
        codex_turn, codex_ended, codex_made = turn('flags-codex', 'assistant_codex',
                                                   {'mode': 'flags', 'count': 3, 'interval': .2, 'after': 1})
        refused = [r for r in (factory.last or {}).get('refused', [])] + [
            m for m in events if m.get('kind') == 'loop' for m in m.get('refused', [])]
        check('AC2/codex-launch', 'the Codex run with the asynchronous grant completes (outcome %s; %s)'
              % (codex_turn.get('outcome'), [r.get('refusals') for r in refused][-2:]),
              codex_ended and codex_turn.get('outcome') == 'completed')
        check('AC2/codex-launch', 'its flags are read in the recorded form and delivered',
              len(codex_made) == 3 and all(c['result']['flag'] and c['result']['flag']['means']
                                           == 'request_user_input_async' for c in codex_made))

        decisions = json.loads((ROOT / '.veldo/runtime/capability-decisions.json').read_text())
        claude_record = json.loads((ROOT / '.veldo/runtime/claude-qualification.json').read_text())
        entry = next(iter(claude_record['versions'].values()))
        formats = json.loads((ROOT / 'proof/VELDO-0062/cli-formats.json').read_text())
        shipped = json.loads((ROOT / '.veldo/runtime/codex-qualification.json').read_text())
        grant = decisions['codex']['grants']['request_user_input_async']
        check('AC2/decisions', 'request_user_input_async is granted with its reason',
              grant['decision'] == 'granted' and 'VELDO-0231' in grant['reason'])
        check('AC2/decisions', 'SendUserMessage is granted and on the in-run list (extractor, classification, reader)',
              decisions['claude_code']['tools']['SendUserMessage']['decision'] == 'granted'
              and 'SendUserMessage' in formats['claude_code']['tool_forms']['in_run']['tools']
              and entry['tool_classification']['SendUserMessage']['class'] == 'in_run'
              and 'SendUserMessage' in entry['stream_forms']['in_run_tools'])
        push = decisions['claude_code']['tools']['PushNotification']
        check('AC2/decisions', 'PushNotification stays off under VELDO-0160 AC3 with its reason, outward',
              push['decision'] == 'off' and push['rule'] == 'VELDO-0160 AC3' and 'phone' in push['reason']
              and entry['tool_classification']['PushNotification']['class'] == 'outward'
              and 'PushNotification' not in formats['claude_code']['tool_forms']['in_run']['tools'])
        check('AC2/decisions', "the grant's tool mapping names both tools the switch delivers (module and record)",
              X.NATIVE_TOOL_MAPPING['request_user_input_async'] == ['request_user_input_async', 'request_user_input']
              and shipped['native_tool_mapping']['request_user_input_async'] == X.NATIVE_TOOL_MAPPING[
                  'request_user_input_async'])

        source = json.loads((ROOT / 'proof/VELDO-0127/codex-live.json').read_text())['runs'][0]

        def configured(tools):
            revision = dict(source['revision'], native_tools=tools, mcp=[],
                            settings={'model': 'fixture-codex-model'}, engine='codex')
            cfg = X.generated()
            cfg['mcp_servers'] = {}
            HO.codex(cfg, {'revision': revision, 'skills': [], 'instructions': 'Role text.'}, {}, base,
                     catalog={'models': []}, feature_listing='shell_tool stable true\n', probe=True)
            return cfg
        on, off = configured(['update_plan', 'request_user_input_async']), configured(['update_plan'])
        check('AC2/switch', 'the handoff turns tools.experimental_request_user_input on only for a role that lists it',
              on['tools.experimental_request_user_input'] == {'enabled': True}
              and off['tools.experimental_request_user_input'] == {'enabled': False})
        wanted = {'tools': ['request_user_input_async', 'update_plan'], 'mcp_servers': [], 'model': None}
        check('AC2/switch', 'the wire set of both delivered tools equals the role\'s',
              HO.codex_tool_difference({'tools': [{'type': 'function', 'name': n} for n in (
                  'update_plan', 'request_user_input_async', 'request_user_input')]}, wanted) is None)

        # AC2, AC3: the qualify command's loopback probe over fake Codex binaries.
        LB = load('v231_loopback', ROOT / 'proof/VELDO-0127/loopback.py')
        Q.PROBE_SECONDS = 4
        catalog = {'models': [{'slug': 'probe-model', 'experimental_supported_tools': ['send_user_message_async'],
                               'apply_patch_tool_type': None, 'supports_search_tool': False}]}
        qualified = {'model_catalog': catalog, 'model_catalog_digest': X.catalog_digest(catalog),
                     'model_tool_modes': X.catalog_modes(catalog)}
        probes = {}
        for name, stream, answer in (('stream', True, True), ('hidden', False, True), ('block', True, False)):
            binary = F.probe_binary(base / ('probe-' + name), stream, answer, sys.executable)
            probes[name] = Q.flag_probe(binary, qualified, HO, LB, source, base)
        (base / 'probes.json').write_text(json.dumps(probes, indent=1))
        stream = probes['stream']
        check('AC2/probe', 'a binary whose asynchronous call reaches the stream: that form, and the grant holds',
              stream['means'] == 'request_user_input_async'
              and stream['forms']['request_user_input_async'] == {
                  'type': 'item.completed', 'item_type': 'mcp_tool_call', 'name': ['item', 'tool'],
                  'text': [['item', 'arguments', 'message']]}
              and X.flag_grant({'flag_means': stream}) is None)
        hidden = probes['hidden']
        check('AC2/probe', 'a binary on which it does not reach the stream gets the marked line with that reason',
              hidden['means'] == 'marked_line' and 'does not reach' in hidden['reason']
              and X.flag_grant({'flag_means': hidden}) is not None)
        check('AC2/probe', 'the probed form is the one the receiver reads', X.flags(
            {'type': 'item.completed', 'item': {'id': 'a', 'type': 'mcp_tool_call', 'tool': 'request_user_input_async',
                                                'arguments': {'message': 'blocked on the gate lock'}}},
            stream) == [{'means': 'request_user_input_async', 'text': 'blocked on the gate lock',
                         'synchronous': False}])
        check('AC3/probe-answer', 'the binary answered the synchronous question at once with no answers: recorded',
              stream['question']['immediate'] is True and stream['question']['answers'] is False
              and stream['question']['within_seconds'] == X.IMMEDIATE_SECONDS and 'seconds' not in stream['question']
              and stream['question']['answer'] is not None)
        blocked = probes['block']
        check('AC3/probe-answer', 'a binary that does not answer at once: the grant does not hold',
              blocked['question']['immediate'] is False and X.flag_grant({'flag_means': blocked}) is not None)
        answering = dict(stream, question=dict(stream['question'], answers=True))
        check('AC3/probe-answer', 'a binary that answers with answers: the grant does not hold',
              X.flag_grant({'flag_means': answering}) is not None)

        # AC2: the marked line only from the agent's own message text.
        mark = 'VELDO-FLAG: the brief did not expect this'
        check('AC2/marked-line', 'Claude Code: read from an assistant text block',
              C.flags({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'note\n' + mark}]}})
              == [{'means': 'marked_line', 'text': 'the brief did not expect this', 'synchronous': False}])
        check('AC2/marked-line', 'Claude Code: never from a tool result, a file read or the prompt',
              C.flags({'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': mark}]}}) == []
              and C.flags({'type': 'assistant', 'message': {'content': [
                  {'type': 'tool_use', 'name': 'Read', 'input': {'file_path': mark}}]}}) == []
              and C.flags({'type': 'system', 'subtype': 'init', 'prompt': mark}) == [])
        check('AC2/marked-line', 'Codex: read from an agent_message item, never a command output or a tool result',
              X.flags({'type': 'item.completed', 'item': {'id': 'm', 'type': 'agent_message', 'text': mark}}, MEANS)
              == [{'means': 'marked_line', 'text': 'the brief did not expect this', 'synchronous': False}]
              and X.flags({'type': 'item.completed', 'item': {'id': 'c', 'type': 'command_execution',
                                                             'aggregated_output': mark}}, MEANS) == []
              and X.flags({'type': 'item.completed', 'item': {'id': 't', 'type': 'mcp_tool_call', 'tool': 'search',
                                                             'result': mark}}, MEANS) == [])
        check('AC2/marked-line', 'a line must begin with the mark',
              C.flags({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'see ' + mark}]}}) == [])

        # AC3: no role may list a tool that waits for an answer.
        def definition(engine, tool):
            return {'role': 'asker', 'engine': engine, 'native_tools': [{'name': tool, 'load': 'always'}], 'mcp': [],
                    'skills': [], 'instructions': [], 'settings': {}}
        check('AC3/save-refused', 'AskUserQuestion and request_user_input are refused by name',
              refusal(lambda: CFG.validate(definition('claude_code', 'AskUserQuestion')))
              == refusal(lambda: CFG.validate(definition('codex', 'request_user_input')))
              == 'invalid_input:agent_native_tools:wait_question')
        check('AC3/save-refused', 'the flag tools are not',
              refusal(lambda: CFG.validate(definition('claude_code', 'SendUserMessage'))) is None
              and refusal(lambda: CFG.validate(definition('codex', 'request_user_input_async'))) is None)
        check('AC3/instructions', 'a role that holds a flag means gets the one fixed text after its own',
              on['developer_instructions'] == 'Role text.\n\n' + HO.FLAG_INSTRUCTIONS
              and 'Nobody answers questions in this run' in HO.FLAG_INSTRUCTIONS
              and 'flag it and go on' in HO.FLAG_INSTRUCTIONS)
        check('AC3/instructions', 'a role without one keeps its own', off['developer_instructions'] == 'Role text.')

        # AC3: a synchronous question answered at once by the binary, and one never answered.
        factory.clock = stepping
        answered, answered_end, asked = turn('question-answered', 'assistant_codex', {'mode': 'question', 'after': 1})
        launch_events = [e for e in events if e.get('kind') == 'flag' and e.get('operation') == 'question']
        check('AC3/answered', 'the run ends normally (%s)' % answered.get('outcome'),
              answered_end and answered.get('outcome') == 'completed')
        check('AC3/answered', 'its question is delivered as a flag with its text',
              any(c['result']['flag'] and c['result']['flag']['synchronous']
                  and c['result']['flag']['text'] == 'Which lock should I wait for?' for c in asked))
        check('AC3/answered', 'the service records the question as answered',
              any(e.get('dispatch_id') == answered.get('dispatch_id') and e.get('outcome') == 'answered'
                  for e in launch_events))
        began = time.monotonic()
        blocking, blocking_end, block_asked = turn('question-block', 'assistant_codex', {'mode': 'block'}, seconds=15)
        took = time.monotonic() - began
        launch_events = [e for e in events if e.get('kind') == 'flag' and e.get('operation') == 'question']
        check('AC3/blocking', 'the blocking run is not running when the deadline passes (%.1fs, %s)'
              % (took, blocking.get('outcome')), blocking_end and blocking.get('state') == 'ended')
        check('AC3/blocking', 'it was stopped by name, configuration_stop:wait_question',
              any(e.get('dispatch_id') == blocking.get('dispatch_id')
                  and e.get('outcome') == 'configuration_stop:wait_question' for e in launch_events))
        check('AC3/blocking', 'its question flag was delivered', any(
            c['result']['flag'] and c['result']['flag']['synchronous'] for c in block_asked))
        if not blocking_end:
            # A run the window did not stop holds the account: stopped here so the rows after it still run.
            stop_all(factory)

        # AC4: a run that flags in a loop: 500 flags in 5 seconds, on the service's own clock.
        factory.clock = time.time
        flood, flood_end, flooded = turn('flood', 'assistant_codex', {'mode': 'flood', 'count': 500, 'seconds': 5},
                                         seconds=90)
        summary = conversations.flag_summary(flood.get('dispatch_id'))
        records = conversations.flags('flood')
        check('AC4/flood', 'the flood run ended (%s)' % flood.get('outcome'), flood_end)
        check('AC4/flood', 'exactly one of 500 is delivered: %d' % len(records), len(records) == 1)
        check('AC4/flood', 'the summary counts 499 held back (rate_limited:run_flag): %s'
              % {k: (summary or {}).get(k) for k in ('read', 'held_back', 'delivered')},
              summary is not None and summary['read'] == 500 and summary['held_back'] == 499
              and sum(1 for c in flooded if c['result']['outcome'] == 'rate_limited:run_flag') == 499)
        # The counts are in the store: a restarted service (a new connection) reads them and goes on with them.
        if summary is None:
            check('AC4/flood', 'the flood run has a flag summary to restart with', False)
        else:
            reopened = authority.S.open_store(str(authority.db))
            reopened.command_registry = dict(getattr(authority.conn, 'command_registry', {}))
            later = CV.Conversations(authority.S, reopened, domain=authority.ids['domain_uuid'],
                                     principal='authority', signer='authority', sign=authority.journal_sign,
                                     state_root=f['root'] / 'state')
            after = later.flag(flood['dispatch_id'], engine='codex', means='request_user_input_async',
                               text='one more', at=summary['last_at'] + 61, read_at=time.time(), conversation='flood')
            check('AC4/flood', 'after a restart, a flag 61 seconds later (suite clock) is delivered naming 499',
                  after['outcome'] == 'delivered' and after['flag']['held_back_since_last'] == 499
                  and later.flag_summary(flood['dispatch_id'])['held_back'] == 499)
            reopened.close()

        # AC4: at most 20 per run.
        moment = time.time()
        capped = [conversations.flag('capped-run', engine='claude_code', means='SendUserMessage', text='n',
                                     at=moment + 61 * n, conversation='flags-claude')['outcome'] for n in range(25)]
        check('AC4/per-run-cap', 'a run delivers at most 20 flags, one per 60 seconds: %d'
              % capped.count('delivered'), capped.count('delivered') == 20
              and capped[20:] == ['rate_limited:run_flag'] * 5)
        quick = [conversations.flag('quick-run', engine='claude_code', means='SendUserMessage', text='n',
                                    at=moment + seconds, conversation='flags-claude')['outcome']
                 for seconds in (0, 59, 60)]
        check('AC4/per-run-cap', 'the first at once, the next only 60 seconds after it',
              quick == ['delivered', 'rate_limited:run_flag', 'delivered'])

        # AC4: nothing outward. Socket creation and process start raise, in the receiver's reading and in the
        # service's delivery: a flag is still read and delivered. The one process the service's store starts for
        # every record it commits, its journal signature (ssh-keygen -Y sign, control_signer), is let through and
        # named; proof/VELDO-0231/OPEN.md states why the strict form needs a path outside the footprint.
        def refuse(*args, **kwargs):
            raise OSError('VELDO-0231: no socket or process for a flag')
        real_popen, signer_runs = subprocess.Popen, []

        class SignerOnly(real_popen):
            def __init__(self, args, *rest, **kwargs):
                if list(args[:3]) != ['ssh-keygen', '-Y', 'sign']:
                    raise OSError('VELDO-0231: no process for a flag: %s' % (args,))
                signer_runs.append(list(args[:3]))
                super().__init__(args, *rest, **kwargs)
        patched = [(socket, 'socket'), (socket, 'create_connection'), (subprocess, 'Popen'), (os, 'fork'),
                   (os, 'posix_spawn'), (os, 'execv'), (os, 'execve'), (os, 'system')]
        saved = [(owner, name, getattr(owner, name)) for owner, name in patched if hasattr(owner, name)]
        emitted, raised = [], []
        try:
            for owner, name, _ in saved:
                setattr(owner, name, refuse)
            reader = L.Flags(emitted.append, 'outward-run', X, 'account-codex-1', MEANS, 2)
            reader.feed((json.dumps({'type': 'item.completed', 'item': {
                'id': 'o', 'type': 'agent_message', 'text': 'VELDO-FLAG: offline'}}) + '\n').encode())
            raised.append(refusal(lambda: socket.socket()) is not None
                          and refusal(lambda: subprocess.Popen(['true'])) is not None)
            subprocess.Popen = SignerOnly

            class Held:
                dispatch_id, flags, contract = 'outward-run', emitted, {'reservation': {}}
            factory.deliver(factory.conversation, Held())
            raised.append(refusal(lambda: subprocess.Popen(['true'])) is not None)
        finally:
            for owner, name, value in saved:
                setattr(owner, name, value)
        outward = conversations.flags(dispatch_id='outward-run')
        check('AC4/nothing-outward', 'with socket creation and process start raising, the receiver reads the flag',
              len(emitted) == 1 and emitted[0]['event'] == 'flag' and emitted[0]['text'] == 'offline'
              and raised[:1] == [True])
        why = [e.get('refusal') for e in events if e.get('dispatch_id') == 'outward-run']
        check('AC4/nothing-outward', 'and the service delivers it as a record in this host\'s store, its only '
              'process the store\'s journal signer %s %s' % (why, signer_runs),
              len(outward) == 1 and outward[0]['text'] == 'offline' and raised[1:] == [True]
              and all(run == ['ssh-keygen', '-Y', 'sign'] for run in signer_runs))
        tools = entry['tool_classification']
        check('AC4/nothing-outward', 'no tool that leaves the host is granted for it',
              all(tools[name]['class'] == 'outward' for name in ('PushNotification', 'SendUserFile', 'RemoteTrigger')
                  if name in tools)
              and not {'PushNotification', 'SendUserFile', 'RemoteTrigger'} & set(
                  formats['claude_code']['tool_forms']['in_run']['tools'])
              and not {'PushNotification', 'SendUserFile', 'RemoteTrigger'} & set(CFG.CODEX_CAPABILITIES))
    except Exception as error:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        for row in ROWS:
            check(row, 'journey completes: %s: %s' % (type(error).__name__, str(error)[:300]), False)
    finally:
        if factory is not None:
            stop_all(factory)
        if lock is not None:
            close = getattr(lock, 'close', None)
            if close:
                close()
        for value in fixtures:
            value['authority'].conn.close()
        shutil.rmtree(base, ignore_errors=True)
    for row in ROWS:
        failed = [label for label, ok in rows[row] if not ok] or ([] if rows[row] else ['journey did not reach row'])
        if failed:
            print('  VELDO-0231 detail:', row, '; '.join(failed))
        expect('VELDO-0231 ' + row, bool(rows[row]) and not failed)


_v231_suite()
