"""VELDO-0231: fake engines that flag the lead, a conversation fixture over the real authority, and the service
loop's poll over launch pipes, for suite 127. Fake engines only: no real Claude Code or Codex ever runs.

The fake Claude Code and Codex are VELDO-0174's (scripts/suites/support/v174_journey.py), with two changes: the
Codex declares the two flag tools when the handoff turns tools.experimental_request_user_input on, and after its
release a run follows the scenario in its markers directory (`scenario.json`): flags at an interval, each stamped
with the time immediately before it is written, then printing for `after` seconds and ending normally; a
synchronous question answered at once or never; or a flood of flags. PROBE is a fake Codex binary for the qualify
command's loopback flag probe: it speaks the Responses wire to the loopback model and prints exec JSON events.

THE LOAD RULE (owner, Telegram 42829, 2026-11-20: no gate depends on machine speed). Every wait of the suites that
load this module waits for the condition it needs: a launch pipe the poll set finds readable (`drive`), a ledger or
store row the predicate reads, a hint on a socket, a process's exit. HANG_SECONDS is never a verdict: it only ends a
wait that would otherwise hang, and `drive` and `eventually` refuse a shorter one, so a pause that is then asserted
on ("nothing moved in 2 seconds") cannot come back. Where a row must show that the loop did NOT act, `quiesce`
forces the loop's next pass and reads every run it starts to its end: the event that proves the loop has processed
past the point, whatever the machine's speed.
"""
import hashlib
import json
from pathlib import Path
import select
import shutil
import socket
import time

HANG_SECONDS = 120
# The forms the fake Codex writes its flag calls in, as the qualify probe records them (`flag_means`).
FORMS = {
    'request_user_input_async': {'type': 'item.completed', 'item_type': 'mcp_tool_call', 'name': ['item', 'tool'],
                                 'text': [['item', 'arguments', 'message']]},
    'request_user_input': {'type': 'item.started', 'item_type': 'mcp_tool_call', 'name': ['item', 'tool'],
                           'text': [['item', 'arguments', 'questions', 0, 'question']]},
}
MEANS = {'means': 'request_user_input_async', 'forms': FORMS,
         'question': {'answer': '{"answers": {}}', 'seconds': 0.01, 'immediate': True, 'answers': False,
                      'returncode': 0},
         'reason': 'the asynchronous call reaches the exec JSON stream in the recorded form'}

TOOLS_OLD = "    tools = ['update_plan'] if cfg.get('tools.update_plan', {}).get('enabled') else []\n"
TOOLS_NEW = """    tools = ['update_plan'] if cfg.get('tools.update_plan', {}).get('enabled') else []
    if cfg.get('tools.experimental_request_user_input', {}).get('enabled'):
        tools += ['request_user_input_async', 'request_user_input']
"""
RELEASE = "while not (MARKERS / 'release').exists(): time.sleep(.02)\n"
SCENARIO = r'''
scenario = json.loads((MARKERS / 'scenario.json').read_text()) if (MARKERS / 'scenario.json').exists() else {}
mode = scenario.get('mode', 'none')
counter = [0]
def say(text):
    counter[0] += 1
    if ENGINE == 'codex':
        emit({'type':'item.completed','item':{'id':'say-%d' % counter[0],'type':'agent_message','text':text}})
    else:
        emit({'type':'assistant','message':{'id':'say-%d' % counter[0],'type':'message','role':'assistant',
              'content':[{'type':'text','text':text}],'usage':{'input_tokens':1,'output_tokens':1}}})
def flag(text):
    counter[0] += 1
    if ENGINE == 'codex' and scenario.get('means') == 'marked':
        emit({'type':'item.completed','item':{'id':'flag-%d' % counter[0],'type':'agent_message',
              'text':'still working\nVELDO-FLAG: ' + text}})
    elif ENGINE == 'codex':
        emit({'type':'item.completed','item':{'id':'flag-%d' % counter[0],'type':'mcp_tool_call','server':'codex',
              'tool':'request_user_input_async','arguments':{'message':text},'status':'completed'}})
    else:
        emit({'type':'assistant','message':{'id':'flag-%d' % counter[0],'type':'message','role':'assistant',
              'content':[{'type':'tool_use','id':'use-%d' % counter[0],'name':'SendUserMessage',
                          'input':{'message':text}}],'usage':{'input_tokens':1,'output_tokens':1}}})
def keep(seconds):
    until = time.time() + seconds
    while time.time() < until:
        say('working')
        time.sleep(.25)
if ENGINE == 'codex':
    emit({'type':'thread.started','thread_id':'fixture-thread'})
    emit({'type':'turn.started'})
acks = None
if scenario.get('ack'):
    # VELDO-0231 AC1 (ordering): the suite writes one byte on this FIFO for each flag: 'c' as it commits it, or 'n'
    # when the dispatch cycle that took it ended without a commit (a defect). The engine writes nothing more until it
    # reads that byte, so each commit is ordered before the engine's next line and before its end, whatever the
    # machine's speed, and a defect is read at once. HANG only ends a wait for a byte that never comes.
    import select
    acks = os.open(str(MARKERS / scenario['ack']), os.O_RDWR)
def acknowledged():
    global acks
    if acks is None:
        return
    if not select.select([acks], [], [], scenario.get('hang', 120))[0]:
        say('flag not committed: going on unacknowledged')
        acks = None
        return
    if os.read(acks, 1) == b'n':
        say('flag not committed in the cycle that read it: going on')
if mode == 'flags':
    for n in range(scenario.get('count', 10)):
        time.sleep(scenario.get('interval', .3))
        flag('flag %d stamp=%.6f' % (n, time.time()))
        acknowledged()
    keep(scenario.get('after', 5))
elif mode == 'none':
    keep(scenario.get('after', 5))
elif mode == 'flood':
    started = time.time()
    count = scenario.get('count', 500)
    for n in range(count):
        flag('flood %d stamp=%.6f' % (n, time.time()))
        time.sleep(max(0, started + scenario.get('seconds', 5) * (n + 1) / count - time.time()))
elif mode in ('question', 'block'):
    say('working')
    question = {'questions':[{'question':'Which lock should I wait for?','header':'Lock'}]}
    started = {'type':'item.started','item':{'id':'question-1','type':'mcp_tool_call','server':'codex',
               'tool':'request_user_input','arguments':question,'status':'in_progress'}}
    if mode == 'block':
        emit(started)
        while True: time.sleep(1)
    # The binary's immediate empty answer and the agent's next line, in the same write as the question: the receiver
    # reads the engine writing on after its question in that one read (an event), so the 2 second question window
    # the suite sets can never close on it however slow the machine is.
    import contextlib, io
    together = io.StringIO()
    with contextlib.redirect_stdout(together):
        emit(started)
        emit({'type':'item.completed','item':{'id':'question-1','type':'mcp_tool_call','server':'codex',
              'tool':'request_user_input','arguments':question,'result':{'answers':{}},'status':'completed'}})
        say('No answer: continuing on my own judgment.')
    sys.stdout.write(together.getvalue())
    sys.stdout.flush()
    keep(scenario.get('after', 1))
'''

# The qualify probe's fake Codex: one turn against the loopback model, the call it is answered with printed in
# exec JSON (`STREAM`: whether the call reaches the stream), the synchronous question answered at once with no
# answers or never (`ANSWER`).
PROBE = r'''#!PYTHON -B
import json, sys, time, tomllib, urllib.request
args = sys.argv[1:]
STREAM, ANSWER, HANG = PROBE_STREAM, PROBE_ANSWER, PROBE_HANG
if args[:2] == ['features', 'list'] or args[:2] == ['debug', 'models']:
    sys.exit(0)
cfg = {}
for n, a in enumerate(args):
    if a == '-c':
        key, _, value = args[n + 1].partition('=')
        node = cfg
        *path, last = key.split('.')
        for part in path:
            node = node.setdefault(part, {})
        node[last] = tomllib.loads('x=' + value)['x']
prompt = sys.stdin.read()
base = cfg['model_providers']['loopback']['base_url']
tools = []
if cfg.get('tools', {}).get('experimental_request_user_input', {}).get('enabled'):
    tools = [{'type':'function','name':'request_user_input_async','parameters':{'type':'object',
              'properties':{'message':{'type':'string'}},'required':['message']}},
             {'type':'function','name':'request_user_input','parameters':{'type':'object','properties':{
              'questions':{'type':'array','items':{'type':'object','properties':{'question':{'type':'string'},
              'header':{'type':'string'}},'required':['question','header']}}},'required':['questions']}}]
def ask(items):
    body = {'model':'probe','tools':tools,'input':items,'stream':True}
    request = urllib.request.Request(base + '/responses', json.dumps(body).encode(),
                                     {'Content-Type':'application/json'})
    done = []
    with urllib.request.urlopen(request, timeout=HANG) as response:
        for raw in response.read().decode().splitlines():
            if raw.startswith('data: '):
                event = json.loads(raw[6:])
                if event.get('type') == 'response.output_item.done':
                    done.append(event['item'])
    return done
def emit(value):
    print(json.dumps(value), flush=True)
emit({'type':'thread.started','thread_id':'probe'})
emit({'type':'turn.started'})
items = [{'type':'message','role':'user','content':[{'type':'input_text','text':prompt}]}]
output = ask(items)
call = next((i for i in output if i.get('type') == 'function_call'), None)
if call is not None:
    arguments = json.loads(call['arguments'])
    if STREAM:
        emit({'type':'item.started' if call['name'] == 'request_user_input' else 'item.completed',
              'item':{'id':'call','type':'mcp_tool_call','server':'codex','tool':call['name'],'arguments':arguments}})
    if call['name'] == 'request_user_input' and not ANSWER:
        # Never answers: it ends without the call's output, an event the probe reads at once (no answer, so not
        # immediate), instead of blocking until the probe's own hang bound.
        sys.exit(0)
    answer = json.dumps({'answers': {}}) if call['name'] == 'request_user_input' else 'delivered'
    ask(items + [call, {'type':'function_call_output','call_id':call['call_id'],'output':answer}])
emit({'type':'item.completed','item':{'id':'answer','type':'agent_message','text':'ready'}})
emit({'type':'turn.completed','usage':{'input_tokens':1,'cached_input_tokens':0,'output_tokens':1}})
'''


def fake_source(J):
    """VELDO-0174's fake engines with the flag tools and the scenario."""
    source = J.FAKE
    if source.count(TOOLS_OLD) != 1 or source.count(RELEASE) != 1:
        raise RuntimeError('the VELDO-0174 fake engine moved')
    source = source.replace(TOOLS_OLD, TOOLS_NEW).replace(RELEASE, RELEASE + SCENARIO)
    return source


def fixture(ROOT, base, H, load, tag, index, production, providers=('claude_code', 'codex')):
    """A real signed authority (VELDO-0073's support) over a copy of the modules (with the production copies the
    suite names, which the mutation driver substitutes), with the default team's roles for each engine; as suite
    123's fixture."""
    root = base / tag
    root.mkdir(parents=True)
    mods = root / 'modules'
    shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
    for name, path in production.items():
        shutil.copyfile(path, mods / name)
    CFG = load('v231_fixture_config_' + tag, mods / 'control_agent_config.py')
    authority = H.build(root / 'authority', mods, 23100 + index, 'http://127.0.0.1:1', 'fixture',
                        scope='activation-repository')
    authority.admin('steward', 'enroll_principal', {
        'principal': 'authority', 'principal_type': 'service', 'roles': ['reservation_service'],
        'public_key': authority.public['authority'], 'independence_group': 'authority', 'scope': '*'},
        enrollee='authority')
    authority.fixture('launch-receiver', 'membership', {
        'principal_type': 'service', 'roles': ['reservation_service'], 'scope': '*',
        'revoked_at': None, 'expires_at': None})
    revisions, roles = {}, {}
    for number, provider in enumerate(providers, 1):
        role_name = 'assistant' if number == 1 else 'assistant_' + provider
        saved = {'role': role_name, 'engine': provider, 'native_tools': [], 'mcp': [], 'skills': [],
                 'instructions': [], 'settings': {}, 'revision': 1, 'previous': None}
        saved['digest'] = CFG.digest(saved)
        authority.fixture('configuration:' + role_name, 'agent_configuration', saved)
        revisions[role_name] = saved
        roles[role_name] = {
            'kind': 'specialist', 'capability_configuration': {'role': role_name, 'revision': 1},
            'workers': [role_name + '-worker'], 'responsibilities': ['assist'], 'expertise': ['general'],
            'proposal_permissions': [], 'engines': [provider],
            'budget': {'capacity': 4, 'invocations': 50, 'wall_seconds': 120, 'tokens': 1000000, 'messages': 1000},
            'independence': {'distinct_from': []}}
    authority.fixture('default-team:1', 'default_team_revision', {
        'revision': 1, 'team': {'roles': roles}, 'saved_by': 'owner', 'assertion_digest': 'sha256:fixture',
        'previous': None, 'digest': 'sha256:default-one'})
    authority.fixture('default-team:head', 'default_team_head', {'revision': 1})
    host = socket.gethostname()
    return {'root': root, 'authority': authority, 'revisions': revisions, 'roles': roles, 'host': host}


def install(ROOT, f, CS, J, accounts_module):
    """The fake engines pinned and qualified over the fixture's modules, the roles' flag tools, the accounts and
    the receiver with a 2 second question window. Returns (receiver path, markers, modules)."""
    saved, J.FAKE = J.FAKE, fake_source(J)
    try:
        path, markers, mods = J.engines(ROOT, f, CS)
    finally:
        J.FAKE = saved
    # The Codex record: a catalog model that supports the asynchronous call, and the fake's flag forms.
    record_path = mods / 'runtime/codex-qualification.json'
    record = json.loads(record_path.read_text())
    X = J.load('v231_codex_' + f['root'].name, mods / 'control_engine_codex.py')
    catalog = {'models': [{'slug': 'fixture-codex-model', 'experimental_supported_tools': ['send_user_message_async'],
                           'apply_patch_tool_type': None, 'supports_search_tool': False}]}
    record.update(model_catalog=catalog, model_catalog_digest=X.catalog_digest(catalog),
                  model_tool_modes=X.catalog_modes(catalog), flag_means=MEANS)
    record_path.write_text(json.dumps(record))
    authority = f['authority']
    for name, revision in f['revisions'].items():
        flag = {'claude_code': 'SendUserMessage', 'codex': 'request_user_input_async'}[revision['engine']]
        revision['native_tools'].append({'name': flag, 'load': 'always'})
        revision['digest'] = CS.CV.CFG.digest({k: v for k, v in revision.items() if k != 'digest'})
        authority.fixture('configuration:' + name, 'agent_configuration', revision)
    accounts = accounts_module.Accounts(authority.S, authority.conn, principal='owner', signer='authority',
                                        sign=authority.journal_sign)
    for provider in ('claude_code', 'codex'):
        account = 'account-%s-1' % provider
        profile = f['root'] / ('profile-' + account)
        profile.mkdir(parents=True)
        accounts.register('account-register-' + account, account, provider, account, {f['host']: str(profile)},
                          concurrency=1, now=time.time())
    config = json.loads(path.read_text())
    config['question_window_seconds'] = 2
    path.write_text(json.dumps(config))
    return path, markers, mods


def drive(factory, until, seconds=HANG_SECONDS):
    """THE SERVICE LOOP's part this suite needs (control_service serve): every launch pipe in a poll set, a
    readable one handed to the factory loop, a pass run when something woke it; until `until()` holds. `seconds` is
    a hang detector only (at least HANG_SECONDS); a shorter one is refused, so no row rests on a pause."""
    if seconds < HANG_SECONDS:
        raise ValueError('drive: %r seconds is a pause, not a hang detector (the load rule)' % (seconds,))
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if until():
            return True
        pipes = factory.pipes()
        if pipes:
            poller = select.poll()
            for fd in pipes:
                poller.register(fd, select.POLLIN)
            for fd, _ in poller.poll(100):
                if fd in pipes:
                    factory.readable(pipes[fd])
        else:
            time.sleep(.05)
        if factory.wakes:
            factory.run()
    return until()


def eventually(predicate, seconds=HANG_SECONDS):
    """Until `predicate()` holds (a marker a fake engine writes as it starts, a store row); `seconds` is a hang
    detector only, at least HANG_SECONDS."""
    if seconds < HANG_SECONDS:
        raise ValueError('eventually: %r seconds is a pause, not a hang detector (the load rule)' % (seconds,))
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        value = predicate()
        if value:
            return value
        time.sleep(.03)
    return predicate()


def quiet(factory):
    """No run in flight (no launch pipe) and nothing waking the loop."""
    return not factory.pipes() and not factory.wakes


def quiesce(factory):
    """The event that proves the loop has processed past this point, in place of a pause before asserting that
    nothing moved: the loop's next pass is forced, and every run it starts is read to its end (its pipe's end of
    file), until no run is in flight and nothing wakes the loop. A defect that would act on the next pass has acted
    by the time this returns, however slow the machine. True when the loop went quiet (False only on a hang)."""
    factory.wake('journal')  # the fullest pass: as a journal advance (an answer, a message) wakes it
    factory.run()
    return drive(factory, lambda: quiet(factory))


def probe_binary(directory, stream, answer, python):
    """A fake Codex vendor package for the flag probe; its executable."""
    package = Path(directory)
    executable = package / 'vendor/x86_64-unknown-linux-musl/bin/codex'
    executable.parent.mkdir(parents=True)
    (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.0.1-linux-x64'}))
    executable.write_text(PROBE.replace('PYTHON', python).replace('PROBE_STREAM', repr(stream))
                          .replace('PROBE_ANSWER', repr(answer)).replace('PROBE_HANG', repr(HANG_SECONDS)))
    executable.chmod(0o755)
    return executable


def digest(path):
    return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()
