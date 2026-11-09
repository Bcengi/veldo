"""VELDO-0275 AC3: every launch starts with a stream probe, read by the run's own stream reader.

Run: python3 scripts/selftest.py --suite 131_veldo_0275_stream_probe

Only shared ROOT and expect are consumed. One temporary tree holds an installed .veldo copy with this change's
production modules (PRODUCTION) laid over it, so a registered mutation of any of them reaches every row. The
fake engines are small Python programs run as real processes:

- Claude Code: a fake that speaks stream JSON input. It answers the initialize request with a subscription login,
  answers the zero-turn probe (a user message with shouldQuery false) as its mode says, and records whether a
  prompt (a user message with text) ever reached it. The suite drives it exactly as the receiver does: the
  Guard's opening first, then each input the Guard releases, every output line fed to the Guard.
- Codex: a fake vendor binary inside an @openai/codex package that answers the probe the receiver runs before
  acceptance (exec with --ephemeral) as its mode says. The suite calls the receiver's own probe step
  (control_launch Receiver._stream_probe) with the engine module, so the launch wiring is what is exercised.

Rows:
- probe/unknown-frame: an approved fake engine prints one frame of an unknown type in its probe: Claude Code's
  launch is stopped stream_probe_failed with that frame kept and the prompt never written; Codex's launch is
  refused stream_probe_failed with that frame in the event; a Claude Code probe that draws no result frame in
  time, and a Codex probe with no terminal frame, are refused the same way.
- probe/accepted: an approved fake engine whose probe answers in today's format: Claude Code's prompt is written
  once after the probe's result (a role-free launch, not only a role-bound one), and Codex's launch proceeds with
  one event naming the engine, binary, version and the parsed probe.
- format/probe-lines: every line the Claude Code fake printed in today's format is an event of the binary's own
  table (proof/VELDO-0062's), and VELDO-0172's read-back conforms the fake to the live capture at teardown.
"""


def _v275_probe_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
    }
    ROWS = ('probe/unknown-frame', 'probe/accepted', 'format/probe-lines')
    UNKNOWN, ACCEPTED, FORMAT = ROWS
    rows = {name: [] for name in ROWS}
    started = time.monotonic()
    VENDOR = 'vendor/x86_64-unknown-linux-musl/bin/codex'

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fake_spec = importlib.util.spec_from_file_location('v275p_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    fake_formats = importlib.util.module_from_spec(fake_spec)
    fake_spec.loader.exec_module(fake_formats)
    # VELDO-0172: this suite checks its own fake engine against the live capture at its teardown.
    conform_spec = importlib.util.spec_from_file_location('v275p_compare_formats',
                                                          ROOT / 'proof/VELDO-0172/compare_formats.py')
    conform_formats = importlib.util.module_from_spec(conform_spec)
    conform_spec.loader.exec_module(conform_formats)
    live_step = fake_formats.live_step

    # The Claude Code fake: stream JSON input, the login answer, the probe as its mode says, then the prompt's
    # scripted lines (VELDO-0172's constructors), each line completed to the binary's own shape.
    CLAUDE_FAKE = fake_formats.embed('''#!%s -B
import json, os, sys
mode, marker = sys.argv[1], sys.argv[2]
def emit(event):
    sys.stdout.write(json.dumps(complete_event(event)) + chr(10))
    sys.stdout.flush()
for line in sys.stdin:
    message = json.loads(line)
    if message.get('type') == 'control_request':
        emit({'type': 'control_response', 'response': {'subtype': 'success', 'request_id': message['request_id'],
              'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    elif message.get('type') == 'user' and message.get('shouldQuery') is False:
        if mode == 'unknown':
            sys.stdout.write(json.dumps({'type': 'veldo_fixture_frame', 'note': 'a frame no stream table lists'}) + chr(10))
            sys.stdout.flush()
        if mode != 'silent':
            emit({'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'session_id': 'fixture-session'})
            emit({'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 0, 'result': '',
                  'session_id': 'fixture-session', 'stop_reason': None})
    elif message.get('type') == 'user':
        open(marker, 'w').write(json.dumps(message))
        content = (message.get('message') or {}).get('content')
        packet = json.loads(content) if isinstance(content, str) and content.strip().startswith('{') else {}
        for step in (packet.get('payload') or {}).get('script') or []:
            emit(step['line'])
        break
''' % sys.executable)
    fake = CLAUDE_FAKE
    SESSION = 'session-275-' + os.urandom(4).hex()

    def c_usage(inp, out):
        return {'input_tokens': inp, 'output_tokens': out, 'cache_creation_input_tokens': 0,
                'cache_read_input_tokens': 0,
                'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0},
                'service_tier': 'standard'}

    @live_step
    def c_msg(mid, inp, out):
        return {'line': {'type': 'assistant', 'parent_tool_use_id': None, 'uuid': 'uuid-' + os.urandom(6).hex(),
                         'session_id': SESSION,
                         'message': {'id': mid, 'type': 'message', 'role': 'assistant', 'model': 'fixture-model',
                                     'content': [], 'stop_reason': None, 'stop_sequence': None,
                                     'usage': c_usage(inp, out)}}}

    @live_step
    def c_rate(status, reset, kind='five_hour'):
        return {'line': {'type': 'rate_limit_event', 'uuid': 'uuid-' + os.urandom(6).hex(), 'session_id': SESSION,
                         'rate_limit_info': {'status': status, 'rateLimitType': kind, 'resetsAt': int(reset)}}}

    @live_step
    def c_result(inp, out, turns=1, text='done'):
        return {'line': {'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4,
                         'is_error': False, 'num_turns': turns, 'result': text, 'stop_reason': 'end_turn',
                         'total_cost_usd': 0, 'usage': c_usage(inp, out),
                         'modelUsage': {'fixture-model': {'inputTokens': inp, 'outputTokens': out,
                                                          'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0,
                                                          'webSearchRequests': 0, 'costUSD': 0,
                                                          'contextWindow': 200000, 'maxOutputTokens': 32000}},
                         'permission_denials': [], 'uuid': 'uuid-' + os.urandom(6).hex(), 'session_id': SESSION}}

    def readback_args(engine, base):
        # VELDO-0172's read-back runs the fake in today's format, its prompt marker in the read-back directory.
        return ['today', str(base / 'readback-prompt')]

    # The Codex fake answers only the receiver's probe (exec with --ephemeral); its lines are written as JSON text.
    CODEX_FAKE = '''#!%s -B
import os, sys
mode = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mode')).read().strip()
if '--ephemeral' not in sys.argv:
    sys.exit(97)
sys.stdin.read()
lines = ['{"type": "thread.started", "thread_id": "fixture-thread"}', '{"type": "turn.started"}']
if mode == 'unknown':
    lines.append('{"type": "veldo.fixture_frame"}')
if mode != 'silent':
    lines.append('{"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": "ready"}}')
    lines.append('{"type": "turn.completed", "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1}}')
for line in lines:
    sys.stdout.write(line + chr(10))
''' % sys.executable

    def claude_launch(C, base, mode):
        """Drive the fake as the receiver does: (guard, prompt written, lines read)."""
        fake = base / 'claude-fake.py'
        fake.write_text(CLAUDE_FAKE)
        fake.chmod(0o755)
        marker = base / ('prompt-' + mode)
        guard = C.Guard()
        worker = subprocess.Popen([str(fake), mode, str(marker)], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        lines = []
        try:
            packet = {'payload': {'script': [c_msg('msg-275', 2, 3), c_rate('allowed', 2000000000), c_result(2, 4)]}}
            opening, _close = guard.opening(json.dumps(packet).encode())
            worker.stdin.write(opening)
            worker.stdin.flush()
            pending, end = b'', time.monotonic() + 10
            while time.monotonic() < end and guard.stop is None and not guard.released:
                ready, _, _ = select.select([worker.stdout], [], [], 0.2)
                if ready:
                    chunk = os.read(worker.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    lines += [line for line in chunk.split(b'\n') if line.strip()]
                    guard.feed(chunk)
                if guard.stop is None:
                    data = guard.release()
                    if data is not None:
                        worker.stdin.write(data)
                        worker.stdin.flush()
                # A probe that draws no result: its deadline, as the receiver's clock would reach it.
                if mode == 'silent' and guard.probed and guard.probe_result is None:
                    guard.expired(time.monotonic() + C.PROBE_SECONDS + 1)
            if guard.released:
                worker.stdin.close()
                worker.wait(timeout=10)
        finally:
            worker.kill()
            worker.wait(timeout=10)
        return guard, marker.is_file(), lines

    def codex_package(base, mode):
        root = base / ('codex-' + mode)
        root.mkdir()
        (root / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '1.0.0-linux-x64'}))
        vendor = root / VENDOR
        vendor.parent.mkdir(parents=True)
        vendor.write_text(CODEX_FAKE)
        vendor.chmod(0o755)
        (vendor.parent / 'mode').write_text(mode)
        return vendor

    class Receiver:
        """The receiver's state its probe step reads: the events it emits."""

        def __init__(self):
            self.events = []

        def emit(self, event):
            self.events.append(event)

    def exercise(base):
        mods = base / 'src' / '.veldo'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        C = load('v275p_claude', mods / 'control_engine_claude.py')
        X = load('v275p_codex', mods / 'control_engine_codex.py')
        L = load('v275p_launch', mods / 'control_launch.py')

        # Claude Code.
        guard, prompted, lines = claude_launch(C, base, 'unknown')
        failure = guard.probe_failure or {}
        check(UNKNOWN, 'Claude Code: a probe printing an unknown frame stops the launch as stream_probe_failed '
              '[%s]' % guard.stop, guard.stop == 'stream_probe_failed')
        check(UNKNOWN, 'Claude Code: the failure keeps that frame and the frames the probe read [%s]' % failure,
              failure.get('reason') == 'unknown_frame' and 'veldo_fixture_frame' in (failure.get('frame') or '')
              and any('veldo_fixture_frame' in f for f in failure.get('frames') or []))
        check(UNKNOWN, 'Claude Code: the prompt is never written [%s]' % prompted, not prompted and not guard.released)
        guard, prompted, _ = claude_launch(C, base, 'silent')
        check(UNKNOWN, 'Claude Code: a probe drawing no result frame in time is refused as stream_probe_failed '
              '[%s %s]' % (guard.stop, guard.probe_failure),
              guard.stop == 'stream_probe_failed' and (guard.probe_failure or {}).get('reason') == 'missing_result'
              and not prompted)
        check(UNKNOWN, 'Claude Code: the receiver stops such a launch as a configuration stop',
              L._stop_cause('stream_probe_failed') == 'configuration_stop')
        guard, prompted, lines = claude_launch(C, base, 'today')
        table = json.loads((ROOT / 'proof/VELDO-0062/cli-formats.json').read_text())['claude_code']['events']
        bad = []
        for raw in lines:
            event = json.loads(raw)
            name = conform_formats.event_name(event)
            schema = table.get(name)
            if schema is None or conform_formats.conform(event, schema, name):
                bad.append(name)
        check(FORMAT, 'every line the Claude Code fake printed in today\'s format is an event of the binary\'s own table '
              '[%s]' % bad[:4], lines and not bad)
        check(ACCEPTED, 'Claude Code: a role-free launch whose probe answers in today\'s format writes the prompt once '
              'after the probe\'s result [%s %s %s]' % (guard.stop, guard.probe_result, prompted),
              guard.stop is None and guard.expected is None and guard.probed and prompted
              and (guard.probe_result or {}).get('num_turns') == 0)

        # Codex: the receiver's own probe step, before acceptance.
        environment = {'PATH': '/usr/bin:/bin', 'HOME': str(base), 'LANG': 'C.UTF-8'}
        for mode, row in (('unknown', UNKNOWN), ('silent', UNKNOWN), ('today', ACCEPTED)):
            vendor = codex_package(base, mode)
            bound = {'engine': 'codex', 'path': str(vendor), 'version': '1.0.0', 'flags': list(X.FLAGS)}
            receiver = Receiver()
            refusal = L.Receiver._stream_probe(receiver, X, bound, environment, None)
            event = next((e for e in receiver.events if e.get('event') == 'stream_probe'), {})
            if mode == 'unknown':
                check(row, 'Codex: a probe printing an unknown frame refuses the launch as stream_probe_failed with '
                      'that frame [%s %s]' % (refusal, event.get('probe')),
                      refusal == 'stream_probe_failed' and event.get('result') == 'failed'
                      and (event.get('probe') or {}).get('reason') == 'unknown_event'
                      and 'veldo.fixture_frame' in ((event.get('probe') or {}).get('frame') or ''))
            elif mode == 'silent':
                check(row, 'Codex: a probe with no terminal frame refuses the launch as stream_probe_failed [%s %s]'
                      % (refusal, event.get('probe')),
                      refusal == 'stream_probe_failed' and (event.get('probe') or {}).get('reason') == 'missing_result')
            else:
                check(row, 'Codex: a probe in today\'s format lets the launch proceed, with one line naming the engine, '
                      'binary, version and the parsed probe [%s %s]' % (refusal, receiver.events),
                      refusal is None and len(receiver.events) == 1 and event.get('result') == 'parsed'
                      and event.get('engine') == 'codex' and event.get('binary') == str(vendor)
                      and event.get('version') == '1.0.0')
        return L

    fake_capture = (['not run'], [])
    directory = tempfile.mkdtemp(prefix='v275p-')
    base = Path(directory)
    try:
        L = exercise(base)
    except Exception as error:  # noqa: BLE001
        for name in ROWS:
            check(name, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    finally:
        fake_capture = conform_formats.conform_fake(locals(), '0275_stream_probe')
        shutil.rmtree(directory, ignore_errors=True)
    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0275_DETAILS'):
                print('  VELDO-0275 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0275 ' + name + (': ' + failed if failed else ''), ok)
    for line in conform_formats.describe('0275_stream_probe', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0275_stream_probe', bool(fake_capture[1]) and not fake_capture[0])
    print('VELDO-0275 probe suite seconds: %.3f' % (time.monotonic() - started))


_v275_probe_suite()
