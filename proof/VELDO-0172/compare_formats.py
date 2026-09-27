"""Value-free shape comparison, and a census of actual fake engine writers in every suite."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import selectors
import sys


def event_name(line):
    name = line.get('type')
    return name + '/' + line['subtype'] if name in ('system', 'result') else name


def paths(value, path=''):
    """Union of field paths; a model-name keyed record has one key, as the contract requires."""
    found = {path}
    if isinstance(value, dict):
        for key, item in value.items():
            found |= paths(item, path + '.' + ('*' if path == '.modelUsage' else key))
    elif isinstance(value, list):
        for item in value:
            found |= paths(item, path + '[]')
    return found


def conform(value, schema, path='', scrubbed=False):
    """Name fields and disagreement categories, never values. Open binary payloads stay open."""
    kind = schema.get('type')
    if value is None:
        return [] if schema.get('nullable') or kind == 'any' else [path + ':table:null']
    if kind == 'object':
        if not isinstance(value, dict):
            return [path + ':table:type']
        fields = schema.get('fields', {})
        problems = [path + '.' + k + ':table:unknown' for k in value if k not in fields]
        for key, field in fields.items():
            if key in value:
                problems += conform(value[key], field, path + '.' + key, scrubbed)
            elif not field.get('optional'):
                problems.append(path + '.' + key + ':table:required')
        return problems
    if kind == 'record' and isinstance(value, dict):
        return [problem for item in value.values() for problem in conform(item, schema['values'], path + '.*', scrubbed)]
    if kind == 'array' and isinstance(value, list):
        return [problem for item in value for problem in conform(item, schema.get('items', {}), path + '[]', scrubbed)]
    if kind == 'union':
        return [] if any(not conform(value, option, path, scrubbed) for option in schema['anyOf']) else [path + ':table:union']
    if kind == 'any':
        return conform(value, schema['observed'], path, scrubbed) if scrubbed and 'observed' in schema else []
    if kind in ('literal', 'enum') and scrubbed and value == '<string>':
        return []
    checks = {'literal': value == schema.get('value'),
              'enum': value in (schema.get('values') or [value]),
              'number': type(value) in (int, float), 'string': isinstance(value, str),
              'boolean': type(value) is bool, 'object': isinstance(value, dict),
              'array': isinstance(value, list), 'record': isinstance(value, dict)}
    return [] if checks.get(kind, True) else [path + ':table:type-or-constant']


def binary_only(value):
    """Remove exactly the fields and optionality explicitly attributed to the capture."""
    value = copy.deepcopy(value)
    def strip(node):
        if not isinstance(node, dict):
            return
        if 'optional_source' in node:
            for name in ('optional', 'optional_source', 'omitted_lines'):
                node.pop(name, None)
        node.pop('observed', None)
        fields = node.get('fields', {})
        for name in list(fields):
            if 'capture_lines' in fields[name]:
                del fields[name]
        for item in node.values():
            if isinstance(item, dict):
                strip(item)
            elif isinstance(item, list):
                for member in item:
                    strip(member)
    for section in ('claude_code', 'codex'):
        events = value[section]['events']
        for name in list(events):
            if 'capture_lines' in events[name]:
                del events[name]
            else:
                strip(events[name])
    for name in list(value['codex']['items']):
        if 'capture_lines' in value['codex']['items'][name]:
            del value['codex']['items'][name]
    value.pop('capture', None)
    return value


def census(directory):
    """Discover embedded executable sources by protocol syntax, not suite names or a fixed file list."""
    found = []
    for path in sorted(Path(directory).glob('*.py')):
        tree = ast.parse(path.read_text())
        candidates = [node for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)
                      and ('sys.stdout' in node.value or 'print(' in node.value)
                      and ('login' in node.value and 'status' in node.value or 'control_response' in node.value
                           or 'turn.completed' in node.value)]
        if candidates:
            found.append(path)
    return found


def observe_fake(local, suite, table, capture):
    """Run the suite's actual generated executable and line constructors, then compare its bytes.

    The surrounding suite already drives real qualification, launch, accounting and artifacts. This
    read-back uses fresh generated profiles, never an ambient login, and leaves its files to that
    suite's normal teardown. Deliberate malformed-output cases remain that suite's negative controls.
    """
    base = local['base'] / 'format-readback'
    base.mkdir()
    profile = base / 'profile'
    profile.mkdir()
    markers = base / 'markers'
    markers.mkdir()
    executable = base / 'fake'
    source = local.get('fake', '')
    if 'fake_engine' in local:
        source = local['fake_engine']('claude')
    executable.write_text(source)
    env = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin', 'HOME': str(base),
           'CLAUDE_CONFIG_DIR': str(profile), 'CODEX_HOME': str(profile), 'XDG_RUNTIME_DIR': str(base),
           'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8',
           'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '1', 'VELDO_DISPATCH_ID': 'format/readback'}
    (profile / 'auth.json').write_text(json.dumps({'auth_mode': 'chatgpt'}))
    # These generated files are the baseline fake's subscription-kind fixtures, not credential stores.
    if 'LOGIN' in local:
        (profile / local['LOGIN']).write_text(json.dumps({'subscriber': True}))
    problems, printed = [], []
    suffix = [str(base / 'empty.db'), str(markers), 'fixture-domain'] if 'store, markers, domain = sys.argv' in source else []
    if 'markers = sys.argv[-1]' in source:
        suffix = [str(markers)]
    has_claude = "'control_request'" in source
    has_codex = "'login', 'status'" in source
    for engine in (['claude'] if has_claude else []) + (['codex'] if has_codex else []):
        script = []
        if engine == 'claude' and 'c_msg' in local:
            script = [local['c_init'](), local['c_msg']('fixture-message', 2, 3),
                      local['c_rate']('allowed', 2000000000), local['c_result'](2, 4, 1)]
        elif engine == 'codex' and 'x_done' in local:
            script = [local['x_thread'](), local['x_started'](), local['x_done'](2, 4)]
        elif engine == 'codex' and 'x_normal' in local:
            script = local['x_normal']('fixture-thread', 2, 4)
        elif engine == 'codex' and callable(local.get('normal')):
            script = [{'line': line} for line in local['normal']('fixture-thread', 2, 4)]
        packet = json.dumps({'payload': {'script': script}})
        args = [sys.executable, str(executable)]
        if engine == 'claude':
            args += ['--input-format', 'stream-json', '--setting-sources', '', '--strict-mcp-config', '--disable-slash-commands']
        else:
            args += ['exec', '--json', '-c', 'cli_auth_credentials_store="file"']
        # Drive the installed protocol writer for both engines, including its held-prompt handshake.
        adapter = local['L'].ENGINES['claude_code' if engine == 'claude' else engine]
        guard = adapter.Guard()
        opening, close = guard.opening(packet.encode())
        prefix = b''
        with subprocess.Popen(args + suffix, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, cwd=base, env=env) as child:
            if close:
                stdout, stderr = child.communicate(opening, timeout=15)
            else:
                child.stdin.write(opening)
                child.stdin.flush()
                with selectors.DefaultSelector() as selector:
                    selector.register(child.stdout, selectors.EVENT_READ)
                    if not selector.select(15):
                        child.kill()
                        child.communicate()
                        problems.append(engine + ':fake:handshake-timeout')
                        continue
                prefix = child.stdout.readline()
                guard.feed(prefix)
                release = guard.release()
                if release is None:
                    problems.append(engine + ':fake:handshake-refused')
                stdout, stderr = child.communicate(release or b'', timeout=15)
            run = subprocess.CompletedProcess(args, child.returncode, (prefix + stdout).decode(), stderr.decode())
        if run.returncode:
            problems.append(engine + ':fake:exit')
        terminal = adapter.Terminal()
        terminal.feed(run.stdout.encode())
        terminal.close()
        if not terminal.document({'returncode': run.returncode, 'signal': None}, None).get('complete'):
            problems.append(engine + ':production:terminal-incomplete')
        lines = []
        for raw in run.stdout.splitlines():
            try:
                lines.append(json.loads(raw))
            except ValueError:
                problems.append(engine + ':fake:invalid-json')
        if not lines:
            problems.append(engine + ':fake:no-lines')
        section = 'claude_code' if engine == 'claude' else 'codex'
        reference = {event_name(line): line for line in capture['streams'][engine]}
        for index, line in enumerate(lines):
            name = event_name(line)
            schema = table[section]['events'].get(name)
            if schema is None:
                problems.append(name + ':table:no-event')
                continue
            problems += conform(line, schema, name)
            # Other item variants (reasoning, tool calls) are outside the captured agent-message variant.
            other_item = name == 'item.completed' and line.get('item', {}).get('type') != 'agent_message'
            if name in reference and not other_item:
                actual, expected = paths(line), paths(reference[name])
                problems += [name + field + ':fake:missing' for field in sorted(expected - actual)]
                problems += [name + field + ':fake:added' for field in sorted(actual - expected)]
            printed.append({'suite': suite.name, 'row': 'fake/capture', 'engine': engine, 'line': index + 1, 'event': name})
        if engine == 'claude':
            answers = [line for line in lines if line.get('type') == 'control_response']
            if not answers or answers[0]['response']['response']['account'].get('subscriptionType') != 'Claude Team':
                problems.append('control_response:fake:subscription-label')
            messages = [line for line in lines if line.get('type') == 'assistant']
            results = [line for line in lines if line.get('type') == 'result']
            if not messages or not results or messages[0]['message']['usage']['output_tokens'] != 3 or results[-1]['usage']['output_tokens'] != 4:
                problems.append('assistant:fake:streamed-output-count')
        else:
            login = subprocess.run([sys.executable, str(executable), 'login', 'status', '-c', 'cli_auth_credentials_store="file"'],
                                   env=env, cwd=base, input='', capture_output=True, text=True, timeout=15)
            for stream in ('stdout', 'stderr'):
                if bool(getattr(login, stream)) != capture['taps']['codex_login_status'][stream]['present']:
                    problems.append('login_status:' + stream + ':fake:wrong-stream')
            if login.returncode or login.stderr.strip() != 'Logged in using ChatGPT':
                problems.append('login_status:fake:subscription-status')
    return problems, printed
