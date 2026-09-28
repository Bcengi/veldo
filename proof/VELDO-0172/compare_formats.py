"""Value-free shape comparison, each suite's own fake-engine conformance check, and the static census of fake writers."""
import ast
import copy
import json
from pathlib import Path
import re
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


ROW = 'VELDO-0172 fake/capture:'
CONFORM = 'conform_fake'


def short_name(path):
    """A suite's row suffix: its file stem without the ordering prefix and `veldo_` (79_veldo_0061_x -> 0061_x)."""
    stem = Path(path).stem
    return stem.split('_veldo_', 1)[1] if '_veldo_' in stem else stem


def builds_fake(tree):
    """A suite builds a fake engine when an executable literal of it prints a Claude Code or Codex line."""
    return any(isinstance(node, ast.Constant) and isinstance(node.value, str)
               and ('sys.stdout' in node.value or 'print(' in node.value)
               and ('login' in node.value and 'status' in node.value or 'control_response' in node.value
                    or 'turn.completed' in node.value)
               for node in ast.walk(tree))


def census(directory, copies=None):
    """Discover embedded executable sources by protocol syntax, not suite names or a fixed file list.

    `copies` maps a suite's file name to the file read in its place (a registered mutant copy).
    """
    copies = copies or {}
    found = []
    for path in sorted(Path(directory).glob('*.py')):
        if builds_fake(ast.parse(Path(copies.get(path.name, path)).read_text())):
            found.append(path)
    return found


def _trees(tree):
    """The suite's own tree and every embedded executable literal that parses as a program.

    A literal is a template until the suite fills it: an `@@NAME@@` placeholder is read as a name and a
    doubled `%` as the one the suite's own `%` formatting leaves, so the program it installs is read.
    """
    yield tree
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and ('print(' in node.value or 'sys.stdout' in node.value):
            for text in (node.value, re.sub(r'@@[A-Z_]+@@', 'PLACEHOLDER', node.value).replace('%%', '%')):
                try:
                    yield ast.parse(text)
                    break
                except SyntaxError:
                    continue


def _display(node):
    """A dict display's constant string keys and their value nodes."""
    return {key.value: value for key, value in zip(node.keys, node.values)
            if isinstance(key, ast.Constant) and isinstance(key.value, str)}


def _constant(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def credited_events(tree, capture):
    """The captured events, per engine, a suite is credited with printing: (engine, event) pairs.

    Only a dict display naming a captured event of that engine counts, so no other dict with a `type` key
    (an input message, a schema kind, a server type) is credited, and an `item.completed` counts only
    with the captured agent-message item displayed in it. The suite's own fake/capture row then requires its
    conform trace to print every event credited here, so a credit the suite's fake does not earn reds it.
    """
    captured = {(engine, event_name(line)) for engine, lines in capture['streams'].items() for line in lines}
    credited = set()
    for part in _trees(tree):
        for node in ast.walk(part):
            if not isinstance(node, ast.Dict):
                continue
            keys = _display(node)
            name = _constant(keys.get('type'))
            if name is None:
                continue
            if name in ('system', 'result'):
                sub = _constant(keys.get('subtype'))
                if sub is None:
                    continue
                name += '/' + sub
            if name == 'item.completed':
                item = keys.get('item')
                if not (isinstance(item, ast.Dict) and _constant(_display(item).get('type')) == 'agent_message'):
                    continue
            credited |= {(engine, event) for engine, event in captured if event == name}
    return credited


def suite_tree(suite_name, directory=None):
    """The syntax tree of the committed suite whose short name this is, from the directory the census reads."""
    directory = Path(directory or Path(__file__).resolve().parents[2] / 'scripts' / 'suites')
    found = [path for path in sorted(directory.glob('*.py')) if short_name(path) == suite_name]
    if len(found) != 1:
        raise LookupError('suite %s names %d suite files' % (suite_name, len(found)))
    return ast.parse(found[0].read_text())


def wiring(tree, name):
    """How a fake-building suite reports its own conformance: named problems, empty when complete.

    It must call the shared conform function with its own locals and short name inside a `finally`
    (the teardown, so it runs whatever the tests did), report `VELDO-0172 fake/capture:<short name>`
    through expect, and keep a `format/` row of its own for the lines it scripts.
    """
    short = short_name(name)
    in_teardown = any(
        isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr == CONFORM
        and len(call.args) == 2 and isinstance(call.args[0], ast.Call)
        and isinstance(call.args[0].func, ast.Name) and call.args[0].func.id == 'locals'
        and isinstance(call.args[1], ast.Constant) and call.args[1].value == short
        for node in ast.walk(tree) if isinstance(node, ast.Try)
        for statement in node.finalbody for call in ast.walk(statement))
    reported = any(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'expect'
        and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == ROW + short
        for node in ast.walk(tree))
    format_row = any(isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith('format/')
                     for node in ast.walk(tree))
    return ([] if in_teardown else [name + ':census:no-conform-in-teardown']) + \
        ([] if reported else [name + ':census:no-fake-capture-row']) + \
        ([] if format_row else [name + ':census:no-format-row'])


def static_census(directory, capture, templates, copies=None):
    """The census row's facts, read from each suite's syntax tree without running it.

    Returns (suites, problems, events): every fake-building suite, what is missing from its wiring or
    from the union of credited events, and each suite's credited `engine:event` names. Each credit is
    earned at run time: the suite's own fake/capture row reds unless its conform trace prints it.
    """
    copies = copies or {}
    suites, problems, events = [], [], {}
    for path in sorted(Path(directory).glob('*.py')):
        tree = ast.parse(Path(copies.get(path.name, path)).read_text())
        if not builds_fake(tree):
            continue
        suites.append(path.name)
        problems += wiring(tree, path.name)
        events[path.name] = sorted(engine + ':' + event for engine, event in credited_events(tree, capture))
    if not suites:
        problems.append('census:empty')
    printed = set().union(*map(set, events.values())) if events else set()
    for engine, lines in capture['streams'].items():
        for line in lines:
            name = event_name(line)
            if engine + ':' + name not in printed:
                problems.append(engine + ':' + name + ':census:capture-event-not-printed')
            template = templates.get(engine, {}).get(name)
            if template is None:
                problems.append(engine + ':' + name + ':census:no-template')
            elif paths(template) != paths(line):
                problems.append(engine + ':' + name + ':census:template-shape')
    return suites, problems, events


def conform_fake(local, suite_name, table=None, capture=None):
    """One suite's own fake/capture observation, called at its teardown with its locals.

    Loads the committed table and capture beside this module unless given, drives the suite's generated
    executables once and returns (issues, trace). Never raises: a failure is the suite's named issue.
    """
    root = Path(__file__).resolve().parents[2]
    try:
        table = table or json.loads((root / 'proof/VELDO-0062/cli-formats.json').read_text())
        capture = capture or json.loads((root / 'proof/VELDO-0172/capture.json').read_text())
        problems, trace = observe_fake(local, suite_name, table, capture)
        # Every captured event the census credits to this suite is one its fake printed here, compared.
        compared = {(t['engine'], t['event']) for t in trace if t.get('compared')}
        problems += ['%s:%s:fake:credited-not-printed' % pair
                     for pair in sorted(credited_events(suite_tree(suite_name, root / 'scripts' / 'suites'), capture) - compared)]
        return problems, trace
    except Exception as error:  # noqa: BLE001 - reported on the suite's own row, never raised past teardown
        return ['observer:did-not-complete:' + type(error).__name__ + ':' + str(error)[:200]], []


def describe(suite_name, issues, trace):
    """The suite's report lines: each issue, then the count and events it compared (never a value)."""
    lines = ['  %s%s detail: %s' % (ROW, suite_name, issue) for issue in issues]
    lines.append('%s%s: %d fake lines compared, events %s'
                 % (ROW, suite_name, len(trace), sorted({t['engine'] + ':' + t['event'] for t in trace})))
    return lines


def observe_fake(local, suite_name, table, capture):
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
    problems, printed = [], []

    def source_of(engine):
        # A suite names each engine's generated executable through fake_engine(name), else one `fake` source
        # serves both. Anything that is not source text is a named problem of this suite, never a raise.
        maker = local.get('fake_engine')
        try:
            value = maker(engine) if callable(maker) else local.get('fake', '')
        except Exception as error:  # noqa: BLE001 - reported as the suite's own problem
            return None, engine + ':fake:source-unreadable:' + type(error).__name__
        if not isinstance(value, str):
            return None, engine + ':fake:source-unreadable:' + type(value).__name__
        return value, None
    sources = {}
    for engine in ('claude', 'codex'):
        sources[engine], problem = source_of(engine)
        if problem:
            problems.append(problem)
    env = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin', 'HOME': str(base),
           'CLAUDE_CONFIG_DIR': str(profile), 'CODEX_HOME': str(profile), 'XDG_RUNTIME_DIR': str(base),
           'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8',
           'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '1', 'VELDO_DISPATCH_ID': 'format/readback'}
    (profile / 'auth.json').write_text(json.dumps({'auth_mode': 'chatgpt'}))
    # These generated files are the baseline fake's subscription-kind fixtures, not credential stores.
    if 'LOGIN' in local:
        (profile / local['LOGIN']).write_text(json.dumps({'subscriber': True}))
    protocol = {'claude': "'control_request'", 'codex': "'login', 'status'"}
    for engine in [name for name in ('claude', 'codex') if sources[name] is not None and protocol[name] in sources[name]]:
        source = sources[engine]
        # Named as the engine's own binary, so an executable that tells its engine by its path reads it.
        executable = base / engine / engine
        executable.parent.mkdir()
        executable.write_text(source)
        suffix = [str(base / 'empty.db'), str(markers), 'fixture-domain'] if 'store, markers, domain = sys.argv' in source else []
        if 'markers = sys.argv[-1]' in source:
            suffix = [str(markers)]
        script = []
        if engine == 'claude' and 'c_msg' in local:
            # A fake that prints its own init line has no scripted one.
            script = ([local['c_init']()] if 'c_init' in local else []) + [
                local['c_msg']('fixture-message', 2, 3), local['c_rate']('allowed', 2000000000), local['c_result'](2, 4, 1)]
        elif engine == 'codex' and 'x_done' in local:
            # A suite with an agent-message constructor prints that captured item in its normal turn.
            script = [local['x_thread'](), local['x_started']()] + (
                [local['x_message']()] if callable(local.get('x_message')) else []) + [local['x_done'](2, 4)]
        elif engine == 'codex' and 'x_normal' in local:
            script = local['x_normal']('fixture-thread', 2, 4)
        elif engine == 'codex' and callable(local.get('normal')):
            script = [{'line': line} for line in local['normal']('fixture-thread', 2, 4)]
        # A fake that reads more of its packet than the script is given the suite's own normal packet.
        packet = local['readback_packet'](engine, script) if callable(local.get('readback_packet')) else None
        packet = json.dumps(packet or {'payload': {'script': script}})
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
            compared = name in reference and not other_item
            if compared:
                actual, expected = paths(line), paths(reference[name])
                problems += [name + field + ':fake:missing' for field in sorted(expected - actual)]
                problems += [name + field + ':fake:added' for field in sorted(actual - expected)]
            printed.append({'suite': suite_name, 'row': ROW + suite_name, 'engine': engine, 'line': index + 1, 'event': name,
                            'compared': compared})
        # AC2's suite-level facts, where this suite prints the event.
        for line in lines:
            if line.get('type') == 'rate_limit_event' and 'unifiedWindows' not in (line.get('rate_limit_info') or {}):
                problems.append('rate_limit_event:fake:no-unifiedWindows')
            if line.get('type') == 'turn.completed' and len(line.get('usage') or {}) != 5:
                problems.append('turn.completed:fake:usage-fields:%d' % len(line.get('usage') or {}))
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
