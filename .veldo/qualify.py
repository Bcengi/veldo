"""VELDO-0230: upgrading an agent CLI is one command.

    python3 .veldo/qualify.py [--codex <vendor binary>] [--claude <version or path>] [--root <repository>]

With no argument it qualifies what is installed: the vendor binary inside the npm package the `codex` on
PATH runs, and the versioned executable the `claude` on PATH resolves to. `--claude 2.1.281` names the
installer's copy ~/.local/share/claude/versions/2.1.281; a path names any copy.

THE ENGINES RECORD (runtime/engines.json, beside this module, byte-identical in every runtime copy) names the
qualified Codex and Claude Code: version, binary path and digest. It is the one place a version lives: every
extractor's default binary, every suite's fake package and pinned copy, the census and setup read it.

ONE COMMAND. In order it writes the engines record, runs every extractor in write mode against the two
binaries (EXTRACTORS: the tables the engine modules and the suites compare against), regenerates the
VELDO-0127 fixtures from the Codex binary (FIXTURES), and writes the Codex and the Claude Code qualification
records to every runtime copy (RUNTIMES): the Codex record by control_engine_codex.qualification, its model
tool modes read from the bundled catalog; the Claude Code record by `claude_record`, from the extracted
tables, with the stream reader's tables (`stream_forms`, read by control_engine_claude: its known messages,
tool-free frames, fields naming a tool, nested-work and in-run tables, `stream_forms` below). On the binaries
already qualified it rewrites every file with the bytes it holds.

A NEWER BINARY NEVER BLOCKS (AC3). A Codex feature the classification (control_agent_config_handoff
CODEX_FEATURES) does not name is off at launch unless its evaluation grants it, and listed by name in the record (`unclassified_default_on`)
and in this command's output; a Claude Code tool not on the in-run list is outward (the extractor's
classification). EVALUATED AND USED IF USEFUL (Telegram 38878): every new item a binary brings (a Codex feature
on by default the classification does not name or a feature, option, reader or grant the replaced binary did not
have; a Claude Code tool, credential or environment name, option, stream message, tool-free frame, field naming a
tool, or `_host` routing switch the replaced binary or record did not have) is listed in
the record (`new_capabilities`) and in the output with its decision from runtime/capability-decisions.json:
granted with its reason, off with the written rule it breaks, or not applicable; one with no decision there is
unevaluated and not granted. A granted Codex feature stays on at launch; nothing new ever blocks one.
Standard library only.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ENGINES = HERE / 'runtime' / 'engines.json'
SCHEMA = 'veldo.engines/v1'
CLAUDE_VERSIONS = Path('~/.local/share/claude/versions')
VERSION = re.compile(r'[0-9]+(?:\.[0-9]+){1,3}')
CODEX_PACKAGE = '@openai/codex'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engines(path=None):
    """The engines record: {schema, claude_code: {version, binary, sha256}, codex: {version, package_version,
    binary, sha256}}. `path` defaults to the record beside this module."""
    record = json.loads(Path(path or ENGINES).read_text())
    if record.get('schema') != SCHEMA or not all(isinstance(record.get(e), dict) for e in ('claude_code', 'codex')):
        raise ValueError('not an engines record: %s' % (path or ENGINES))
    return record


def expand(path):
    """A record path with its leading `~` as this account's home directory (its passwd entry, never $HOME,
    which an engine's environment points at a temporary profile)."""
    path = str(path)
    if path == '~' or path.startswith('~/'):
        import pwd
        return Path(pwd.getpwuid(os.getuid()).pw_dir + path[1:])
    return Path(path)


def binary(engine, record=None):
    """The qualified binary of `engine` ('claude_code' or 'codex') as an absolute path, `~` expanded."""
    record = engines() if record is None else record
    return expand(record[engine]['binary'])


def home_form(path):
    """A path under the home directory written as ~/..., so the record reads the same for every account."""
    import pwd
    path, home = Path(path), Path(pwd.getpwuid(os.getuid()).pw_dir)
    try:
        return '~/' + str(path.relative_to(home))
    except ValueError:
        return str(path)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


def codex_package(executable):
    """(root, manifest) of the npm package holding the vendor binary: its nearest package.json."""
    for parent in Path(executable).parents:
        manifest = parent / 'package.json'
        if manifest.is_file():
            return parent, json.loads(manifest.read_text())
    raise SystemExit('qualify: %s lies in no npm package' % executable)


def codex_version(executable):
    """(version, package_version) of a Codex vendor binary, from its own package manifest."""
    _, manifest = codex_package(executable)
    package_version = str(manifest.get('version') or '')
    return package_version.split('-', 1)[0], package_version


def claude_version(executable):
    """The version of a Claude Code executable: its installer file name, else what `--version` prints."""
    name = Path(executable).name
    if VERSION.fullmatch(name):
        return name
    done = subprocess.run([str(executable), '--version'], capture_output=True, text=True, timeout=60,
                          env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/'), 'LANG': 'C.UTF-8'})
    found = VERSION.search(done.stdout)
    if not found:
        raise SystemExit('qualify: %s prints no version' % executable)
    return found.group(0)


def installed_codex():
    """The vendor binary inside the package the `codex` on PATH runs (its platform package's vendor tree)."""
    link = shutil.which('codex')
    if not link:
        raise SystemExit('qualify: no codex on PATH; name the vendor binary with --codex')
    root = Path(os.path.realpath(link)).parent.parent
    found = sorted(root.glob('node_modules/@openai/codex-*/vendor/*/bin/codex')) or sorted(
        root.parent.glob('codex-*/vendor/*/bin/codex'))
    if not found:
        raise SystemExit('qualify: no vendor binary under %s; name it with --codex' % root)
    return found[0]


def installed_claude(named=None):
    """The Claude Code executable: a version names the installer's copy, a path names itself, nothing names
    the copy the `claude` on PATH resolves to."""
    if named:
        if VERSION.fullmatch(named):
            return expand(str(CLAUDE_VERSIONS / named))
        return Path(named).resolve()
    link = shutil.which('claude')
    if not link:
        raise SystemExit('qualify: no claude on PATH; name a version or a path with --claude')
    return Path(os.path.realpath(link))


def engines_record(codex, claude):
    version, package_version = codex_version(codex)
    return {
        'schema': SCHEMA,
        'spec_id': 'VELDO-0230',
        'note': 'The qualified agent CLIs, written by python3 .veldo/qualify.py and read by every extractor, '
                'suite, census row and setup step that needs a version, a binary path or a digest.',
        'claude_code': {'version': claude_version(claude), 'binary': home_form(claude), 'sha256': digest(claude)},
        'codex': {'version': version, 'package_version': package_version, 'binary': home_form(codex),
                  'sha256': digest(codex)},
    }


# THE WRITERS.

ROOT = HERE.parent
# The runtime copies every record is written to: this module's own, the engine canon's, and a composed pack's.
RUNTIMES = ('.veldo/runtime', 'engine/runtime', 'packs/*/runtime')
# Every extractor in write mode, in dependency order (VELDO-0061's and VELDO-0173's read VELDO-0062's table),
# each with the engines it reads and the tables it writes beside itself.
EXTRACTORS = (('proof/VELDO-0062/extract_formats.py', ('claude', 'codex'), ('cli-formats.json',)),
              ('proof/VELDO-0061/extract_items.py', ('codex',), ('codex-exec.json',)),
              ('proof/VELDO-0060/extract_cli.py', ('claude',), ('cli-options.json',)),
              ('proof/VELDO-0141/extract_stream.py', ('claude', 'codex'), ('stream-formats.json',)),
              ('proof/VELDO-0155/extract_baseline.py', ('claude',), ('claude-baseline.json',)),
              ('proof/VELDO-0156/extract_baseline.py', ('codex',), ('codex-baseline.json',)),
              # The binary's own offline prompt rendering and its loopback model request (suite 81 reads both).
              ('proof/VELDO-0156/render_offline.py', ('codex',), ('codex-rendered.json',)),
              ('proof/VELDO-0156/capture_mentions.py', ('codex',), ('codex-mentions.json',)),
              ('proof/VELDO-0165/extract_environment.py', ('claude', 'codex'),
               ('claude-environment.json', 'codex-environment.json')),
              ('proof/VELDO-0173/extract_tools.py', ('claude',), ('claude-tools.json',)),
              ('proof/VELDO-0185/extract_login_status.py', ('claude',), ('login-status.json',)))
FIXTURES = 'proof/VELDO-0127'
CLAUDE_NOTE = "The Claude Code configuration VELDO-0060 qualifies on Linux. Every value is read from the installed binary: its digest and stream formats from proof/VELDO-0062/cli-formats.json, its command line from proof/VELDO-0060/cli-options.json. A version not listed here, or a pinned copy whose digest differs, is refused before anything is spawned; upgrading is a deliberate requalification that adds a version. VELDO-0155: the version is qualified with the everything-off baseline read from the same binary (proof/VELDO-0155/claude-baseline.json); a record without it refuses every launch of the version. VELDO-0155 AC3: the version is also qualified with stream JSON input (--input-format stream-json, which the binary accepts only with stream JSON output in print mode), so the prompt waits for the login check; a record without it refuses every launch of the version. VELDO-0141: the baseline also carries the stream options --include-partial-messages and --forward-subagent-text (read from the same bytes, proof/VELDO-0155/claude-baseline.json), so partial messages and a subagent's text reach the stream the execution record keeps; a record without them refuses every launch of the version. VELDO-0173: the version is also qualified with the binary's full tool registry (tool_registry, every tool it registers) and the classification of every registry tool as in_run or outward with its reason (tool_classification), both read from the same bytes (proof/VELDO-0173/claude-tools.json); a record missing either, or leaving a registry tool unclassified, refuses every launch of the version. VELDO-0185: the version is also qualified with its own login status command (login_status: auth status --json, whose answer names loggedIn and authMethod, claude.ai for the subscription, proof/VELDO-0185/login-status.json), which setup and the launch receiver run for each account before work; a record without it reads every such account as not qualified."
# The Claude Code configuration Veldo runs every qualified version with (VELDO-0060, VELDO-0155 AC3): its
# policy, not the binary's tables; the binary's own values are read in claude_record.
CLAUDE_POLICY = {
    'authentication': {'init_api_key_source': 'none', 'mode': 'subscription', 'profile_variable': 'CLAUDE_CONFIG_DIR'},
    'environment': {'DISABLE_AUTOUPDATER': '1'},
    'flags': ['--print', '--output-format', 'stream-json', '--verbose', '--input-format', 'stream-json'],
    'host_kind': 'linux',
    'input': 'stream JSON input (VELDO-0155 AC3): the initialize control request first, then the dispatch packet '
             'as the user message only once the answer names a subscription login',
    'live_usage': None,
    'usage_units': ['invocations', 'wall_seconds', 'tokens', 'messages'],
}


def text(record):
    return json.dumps(record, indent=1, sort_keys=True) + '\n'


def runtimes(root):
    found = []
    for pattern in RUNTIMES:
        found += [path for path in sorted(Path(root).glob(pattern)) if path.is_dir()]
    return found


def write(root, name, content, written):
    for directory in runtimes(root):
        (directory / name).write_text(content)
        written.append(str((directory / name).relative_to(root)))


def claude_builtins(executable, baseline):
    """VELDO-0127's reading of what Claude Code loads of its own beyond the baseline: the init event of one
    probe (the empty user message that queries nothing, answered before any model request, so no login is
    needed), run in a fresh empty profile with the baseline's environment and settings, the bundled skills
    removed and skills listed. ({plugins}, {skills}): its built-in plugins and the skills left."""
    import tempfile
    with tempfile.TemporaryDirectory(prefix='veldo-qualify-claude-') as temp:
        root = Path(temp)
        for name in ('home', 'profile', 'work'):
            (root / name).mkdir()
        settings = dict(baseline['settings'], disableBundledSkills=True)
        options = [o for o in baseline['options'] if o != '--disable-slash-commands']
        argv = ([str(executable)] + CLAUDE_POLICY['flags'] + options[:2]
                + [baseline['settings_option'], json.dumps(settings), baseline['mcp_option'],
                   json.dumps(baseline['mcp_config'])] + options[2:])
        env = dict(baseline['environment'], PATH='/usr/bin:/bin', HOME=str(root / 'home'), TMPDIR=temp,
                   CLAUDE_CONFIG_DIR=str(root / 'profile'), **CLAUDE_POLICY['environment'])
        probe = {'type': 'user', 'message': {'role': 'user', 'content': []}, 'parent_tool_use_id': None,
                 'shouldQuery': False}
        done = subprocess.run(argv, input=json.dumps(probe) + '\n', capture_output=True, text=True, timeout=120,
                              cwd=root / 'work', env=env)
    for line in done.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get('type') == 'system' and event.get('subtype') == 'init':
            return (sorted(p['source'] for p in event.get('plugins') or []), sorted(event.get('skills') or []))
    raise SystemExit('qualify: %s printed no init event to the probe' % executable)


def claude_record(root, executable):
    """The Claude Code qualification record of one binary (VELDO-0230's writer), from the tables the
    extractors just wrote and this module's policy: one version, the one the engines record names."""
    C = load('qualify_claude', HERE / 'control_engine_claude.py')
    proof = Path(root) / 'proof'
    version = claude_version(executable)
    table = json.loads((proof / 'VELDO-0062/cli-formats.json').read_text())['claude_code']
    formats, usage = table['events'], table['usage_limit']
    tools = json.loads((proof / 'VELDO-0173/claude-tools.json').read_text())
    login = json.loads((proof / 'VELDO-0185/login-status.json').read_text())['record']
    plugins, skills = claude_builtins(executable, C.BASELINE)
    entry = dict(json.loads(json.dumps(CLAUDE_POLICY)), baseline=C.BASELINE, engine_plugins=plugins,
                 engine_skills=skills, limit_names=usage['names'], login_status=login,
                 pinned='<state root>/engines/claude_code/' + version,
                 rate_limit_windows=formats['rate_limit_event']['fields']['rate_limit_info']['fields']['rateLimitType']['values'],
                 session_environment=C.session_environment(executable), sha256=digest(executable),
                 source=home_form(executable),
                 terminal_protocol={'error_subtypes': formats['result/error']['fields']['subtype']['values'],
                                    'output': 'stream-json', 'success_subtype': 'success', 'terminal_event': 'result'},
                 tool_classification=tools['tool_classification'], tool_registry=tools['tool_registry'])
    return {'engine': 'claude_code', 'note': CLAUDE_NOTE, 'schema': C.QUALIFICATION_SCHEMA, 'spec_id': 'VELDO-0060',
            'versions': {version: entry}}


def fixture_text(record):
    """VELDO-0127's fixture form: sorted keys, one-space indent, a doubled hyphen written as escapes."""
    return text(record).replace('-' * 2, '\\u002d' * 2)


def normalized(record):
    """A loopback capture with what changes from run to run (temporary directories, thread, session and
    installation ids, the day it ran) replaced by placeholders, so the same binary writes the same bytes."""
    import tempfile
    raw = json.dumps(record)
    if tempfile.gettempdir() != '/tmp':
        raw = raw.replace(tempfile.gettempdir().rstrip('/') + '/', '/tmp/')
    raw = re.sub(r'/tmp/((?:v127|veldo)-[a-z-]*?-)[A-Za-z0-9_]{8}', r'/tmp/\1<temp>', raw)
    raw = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<id>', raw)
    raw = re.sub(r'(_at_unix_ms\\?\\?\\?"\s*:\s*)[0-9]+', r'\g<1>0', raw)
    # The engine's environment context names the day it ran; the fixture keeps a placeholder so a rerun matches.
    raw = re.sub(r'<current_date>[0-9]{4}-[0-9]{2}-[0-9]{2}</current_date>', '<current_date><date></current_date>', raw)
    return json.loads(raw)


def fixture_models(catalog):
    """The catalog's first Code Mode model and its first direct one, the two VELDO-0127's captures run."""
    modes = [(m['slug'], m.get('tool_mode')) for m in catalog['models']]
    return (next(s for s, mode in modes if mode == 'code_mode_only'), next(s for s, mode in modes if mode is None))


# VELDO-0231: the token the flag probe's model call carries, and how long one probe run may take.
FLAG_TOKEN = 'veldo-flag-probe-0231'
PROBE_SECONDS = 45


def token_path(value, token, path=()):
    """The path to the first string in `value` holding `token` (`$json` entering a JSON-encoded string), or None."""
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = enumerate(value)
    elif isinstance(value, str) and token in value:
        if value.strip() == token:
            return list(path)
        try:
            inner = json.loads(value)
        except ValueError:
            return list(path)
        found = token_path(inner, token, ())
        return list(path) + ['$json'] + found if found is not None else list(path)
    else:
        return None
    for key, item in items:
        found = token_path(item, token, path + (key,))
        if found is not None:
            return found
    return None


def name_path(value, name, path=()):
    """The path to the first string in `value` equal to `name`, or None."""
    if isinstance(value, str):
        return list(path) if value == name else None
    items = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()
    for key, item in items:
        found = name_path(item, name, path + (key,))
        if found is not None:
            return found
    return None


def stream_form(stdout, token, tool):
    """The form of the first exec JSON event that carries `token` and names `tool`: {type, item_type, name: path,
    text: [path]}, or None."""
    for line in (stdout or '').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        path = token_path(event, token) if isinstance(event, dict) else None
        named = name_path(event, tool) if path is not None else None
        if path is not None and named is not None:
            item = event.get('item')
            return {'type': event.get('type'), 'item_type': item.get('type') if isinstance(item, dict) else None,
                    'name': named, 'text': [path]}
    return None


def flag_probe(executable, qualified, H, LB, source, temp):
    """VELDO-0231 AC2, AC3: on loopback, with the input closed after the prompt as Veldo launches it, the model calls
    request_user_input_async and, in a second run, request_user_input, each carrying FLAG_TOKEN. Records the form
    in which each call reaches the exec JSON stream, and for the synchronous one the binary's own answer (the call's
    output in its next request), how long it took as the bound it answered within (`within_seconds`, never the
    measured time, so the same binary writes the same record), whether it was immediate and whether it gave answers.
    The means is the asynchronous call only where its form was found; else the marked line, with that reason."""
    import copy
    X = H.X
    models = qualified['model_catalog']['models']
    supporting = [m for m in models if 'send_user_message_async' in (m.get('experimental_supported_tools') or ())]
    model = next((m['slug'] for m in supporting if m.get('tool_mode') is None),
                 supporting[0]['slug'] if supporting else None)
    if model is None:
        return dict(X.UNPROBED, reason='no model of the bundled catalog supports the asynchronous call')
    revision = copy.deepcopy(source['revision'])
    revision['settings']['model'], revision['mcp'], revision['native_tools'] = model, [], ['request_user_input_async']
    capability = {'revision': revision, 'skills': [], 'instructions': ''}
    forms, question = {}, None
    for tool in (X.FLAG_TOOL, X.QUESTION_TOOL):
        cfg = X.generated()
        cfg['mcp_servers'] = {}
        catalog = H.codex_model(qualified, revision)
        H.codex(cfg, capability, {}, temp, catalog=catalog, probe=True)
        result = LB.capture(executable, cfg, catalog=catalog, call=(tool, FLAG_TOKEN), timeout=PROBE_SECONDS)
        forms[tool] = stream_form(result.get('stdout'), FLAG_TOKEN, tool)
        if tool == X.QUESTION_TOOL:
            requests = result.get('requests') or []
            answered = requests[0].get('answered_at') if requests else None
            output, seconds = None, None
            for request in requests[1:]:
                outputs = [i for i in request['body'].get('input') or () if isinstance(i, dict)
                           and i.get('type') == 'function_call_output' and i.get('call_id') == 'call_loopback']
                if outputs:
                    output = outputs[0].get('output')
                    seconds = round(request['arrived'] - answered, 3) if answered is not None else None
                    break
            text_output = output if isinstance(output, str) else json.dumps(output)
            try:
                parsed = json.loads(text_output) if output is not None else None
            except ValueError:
                parsed = None
            answers = bool(parsed.get('answers')) if isinstance(parsed, dict) else output is None or bool(text_output)
            immediate = seconds is not None and seconds <= X.IMMEDIATE_SECONDS
            question = {'answer': output, 'within_seconds': X.IMMEDIATE_SECONDS if immediate else None,
                        'answers': answers, 'immediate': immediate, 'returncode': result.get('returncode')}
    if forms[X.FLAG_TOOL] is None:
        return {'means': X.MARKED_LINE, 'forms': forms, 'question': question,
                'reason': 'the asynchronous call does not reach the exec JSON stream on this binary'}
    return {'means': X.FLAG_TOOL, 'forms': forms, 'question': question,
            'reason': 'the asynchronous call reaches the exec JSON stream in the recorded form'}


def fixtures(root, executable, written):
    """The VELDO-0127 fixtures the role suites read: the bundled catalog, the features listing and the real
    binary's loopback request with and without a selected MCP server for each of the two models."""
    import copy
    import tempfile
    here = Path(root) / FIXTURES
    H = load('qualify_handoff', Path(root) / '.veldo/control_agent_config_handoff.py')
    LB = load('qualify_loopback', here / 'loopback.py')
    E = load('qualify_evidence', here / 'evidence.py')
    qualified = H.X.load_qualification()
    outputs = {'catalog-fixture.json': fixture_text(qualified['model_catalog'])}
    # The catalog's models the mutation registry names its rows by (a plain table it reads by key): the first
    # Code Mode model, the first that supports the clock, the first direct model, and the first direct model
    # that supports neither experimental tool.
    models = qualified['model_catalog']['models']
    code = next(m['slug'] for m in models if m.get('tool_mode') == 'code_mode_only')
    outputs['fixture-models.json'] = text({
        'code': code, 'direct': next(m['slug'] for m in models if m.get('tool_mode') is None),
        'clock': next((m['slug'] for m in models if 'clock' in (m.get('experimental_supported_tools') or ())), code),
        'plain': next(m['slug'] for m in models if m.get('tool_mode') is None and not set(
            m.get('experimental_supported_tools') or ()) & {'clock', 'send_user_message_async'})})
    outputs['features-fixture.json'] = text(normalized(LB.capture(executable, {}, features=True)))
    source = json.loads((here / 'codex-live.json').read_text())['runs'][0]
    captured = []
    with tempfile.TemporaryDirectory(prefix='v127-resource-probe-') as temp:
        for model in fixture_models(qualified['model_catalog']):
            for selected in (True, False):
                revision = copy.deepcopy(source['revision'])
                revision['settings']['model'] = model
                if not selected:
                    revision['mcp'] = []
                capability = {'revision': revision, 'skills': [],
                              'instructions': source['configuration']['developer_instructions']}
                inventory = {'jira': {'tools': ['jira_search']}} if selected else {}
                cfg = H.X.generated()
                cfg['mcp_servers'] = {'jira': {'enabled_tools': ['jira_search']}} if selected else {}
                catalog = H.codex_model(qualified, revision)
                H.codex(cfg, capability, inventory, Path(temp), catalog=catalog)
                captured.append((model, selected, capability, inventory, catalog,
                                 LB.capture(executable, cfg, catalog=catalog)))
        # VELDO-0231: the forms in which the flag calls reach the exec JSON stream, and the binary's own answer to a
        # synchronous question, written before the grant probe below (the handoff reads them).
        means = flag_probe(executable, qualified, H, LB, source, Path(temp))
        if qualified.get('flag_means') != means:
            qualified['flag_means'] = means
            write(root, 'codex-qualification.json', text(qualified), [])
        # VELDO-0230: each experimental grant the catalog lists, on the first model listing it, with nothing else
        # granted: a grant whose tools do not reach the request under Veldo's switches is undelivered.
        undelivered = []
        for grant, experimental in (('clock', 'clock'), ('request_user_input_async', 'send_user_message_async')):
            model = next((m['slug'] for m in qualified['model_catalog']['models']
                          if experimental in (m.get('experimental_supported_tools') or ())), None)
            if model is None:
                continue
            revision = copy.deepcopy(source['revision'])
            revision['settings']['model'], revision['mcp'], revision['native_tools'] = model, [], [grant]
            capability = {'revision': revision, 'skills': [], 'instructions': ''}
            cfg = H.X.generated()
            cfg['mcp_servers'] = {}
            catalog = H.codex_model(qualified, revision)
            H.codex(cfg, capability, {}, Path(temp), catalog=catalog, probe=True)
            result = LB.capture(executable, cfg, catalog=catalog)
            sent = set().union(*[H.codex_tool_names(H.codex_request_tools(r['body'])) for r in result['requests']])
            if not {H.codex_name(n) for n in qualified['native_tool_mapping'].get(grant, [grant])} <= sent:
                undelivered.append(grant)
    # VELDO-0230: the resource readers the binary offers with no server selected, by the model's tool mode, read
    # from its own request; recorded in the Codex record (offered, never granted) before the comparison below.
    readers = set(qualified['native_tool_mapping']['mcp_server'])
    offered = {}
    for model, selected, _, _, _, result in captured:
        if not selected:
            for request in result['requests']:
                found = readers & set(H.codex_tool_names(H.codex_request_tools(request['body'])))
                if found:
                    mode = qualified['model_tool_modes'].get(model) or 'direct'
                    offered[mode] = sorted(set(offered.get(mode, [])) | found)
    if (qualified['mcp_resource_rule'].get('offered_without_server') != offered
            or qualified.get('undelivered_grants') != sorted(undelivered)):
        qualified['mcp_resource_rule']['offered_without_server'] = offered
        qualified['undelivered_grants'] = sorted(undelivered)
        write(root, 'codex-qualification.json', text(qualified), [])
    cases = []
    for model, selected, capability, inventory, catalog, result in captured:
        wanted = H.expected(capability, inventory)
        observations = E.wire_observations([r['body'] for r in result['requests']], wanted, H)
        result.update(expected=wanted, observations=observations, model_catalog=catalog,
                      production=E.production(Path(root)), selected_server=selected,
                      owner_decision='Telegram 29400/29401, 2026-09-28; 38878, 2026-11-03')
        name = 'resources-' + model + ('-selected' if selected else '-none') + '.json'
        outputs[name] = text(normalized(result))
        cases.append({'model': model, 'selected_server': selected, 'record': name,
                      'returncode': result['returncode'], 'observations': normalized(observations),
                      'exact_equality': result['returncode'] == 0 and bool(observations) and all(
                          o['stop'] is None and o['actual'] == o['expected'] for o in observations)})
    outputs['resource-qualification.json'] = json.dumps({
        'owner_decision': 'Telegram 29400/29401, 2026-09-28; 38878, 2026-11-03', 'binary_sha256': qualified['sha256'],
        'cases': cases, 'offered_without_server': offered,
        'rule': 'Exactly three resource readers with a selected MCP server; without one, none granted and exactly '
                'those the binary offers a model of its tool mode accepted (nothing to list or read).',
        'network': '127.0.0.1 stand-in; empty temporary HOME and CODEX_HOME; Landlock TCP restriction'},
        indent=1) + '\n'
    for name, content in outputs.items():
        (here / name).write_text(content)
        written.append(FIXTURES + '/' + name)


DECISIONS = '.veldo/runtime/capability-decisions.json'
UNEVALUATED = {'decision': 'unevaluated', 'reason': 'no evaluation in runtime/capability-decisions.json: not granted '
               'until one is written (the evaluation is part of this upgrade)'}


def decided(decisions, engine, kind, names, default=None):
    """VELDO-0230 AC3: [{kind, name, decision, reason, rule?}] for each new item, its evaluation from the decisions
    record, else `default` (an item a written rule already decides), else unevaluated (not granted)."""
    table = (decisions.get(engine) or {}).get(kind) or {}
    return [dict(kind=kind, name=name, **(table.get(name) or default or UNEVALUATED)) for name in sorted(names)]


def previous_tables(root):
    """What the replaced qualification read, before the extractors overwrite it: {name: set}."""
    def read(path, pick):
        try:
            return set(pick(json.loads((Path(root) / path).read_text())))
        except (OSError, ValueError, KeyError, TypeError):
            return None
    credentials = lambda engine: lambda t: [n for table in t[engine]['credential_tables'] for n in table['names']]
    return {'codex_features': read('.veldo/runtime/codex-qualification.json',
                                   lambda r: [line.split()[0] for line in r['feature_listing'].splitlines() if line.strip()]),
            'codex_options': read('proof/VELDO-0156/codex-baseline.json', lambda t: t['options']),
            'codex_environment': read('proof/VELDO-0062/cli-formats.json', credentials('codex')),
            'claude_tools': read('.veldo/runtime/claude-qualification.json',
                                 lambda r: next(iter(r['versions'].values()))['tool_registry']),
            'claude_options': read('proof/VELDO-0060/cli-options.json', lambda t: t['claude_code']['options']),
            'claude_environment': read('proof/VELDO-0062/cli-formats.json', credentials('claude_code'))}


def previous_new(root, engine):
    """The (kind, name) pairs the replaced record listed as new, with the digest it was qualified at."""
    try:
        name = {'codex': 'codex', 'claude_code': 'claude'}[engine] + '-qualification.json'
        record = json.loads((Path(root) / '.veldo/runtime' / name).read_text())
        entry = record if engine == 'codex' else next(iter(record['versions'].values()))
        return entry['sha256'], {(i['kind'], i['name']) for i in entry.get('new_capabilities') or ()}
    except (OSError, ValueError, KeyError, StopIteration, TypeError):
        return None, set()


def newer(current, before, carried, kind, same):
    """The names of `kind` that are new: against the replaced binary's table, or, re-qualifying the same binary,
    the names the record already listed (so the same binary writes the same bytes)."""
    if same:
        return {name for k, name in carried if k == kind}
    return set(current) - before if before is not None else set()


def previous_forms(root):
    """The stream forms the replaced Claude Code record gave its reader (`stream_forms`), or None."""
    try:
        record = json.loads((Path(root) / '.veldo/runtime/claude-qualification.json').read_text())
        forms = next(iter(record['versions'].values()))['stream_forms']
        return forms if isinstance(forms, dict) else None
    except (OSError, ValueError, KeyError, StopIteration, TypeError):
        return None


def _tag(pair):
    return '/'.join(part for part in pair if part is not None)


def stream_forms(root, previous, carried, same, decisions):
    """VELDO-0230 AC2/AC3: the Claude Code stream reader's tables (control_engine_claude reads `stream_forms` from
    the record) from the binary's own (proof/VELDO-0062/cli-formats.json tool_forms), and the new items among them.
    The messages, the tool-free frames and the fields naming a tool the replaced record already gave the reader keep
    their reading; one it did not give is new and read by its decision in runtime/capability-decisions.json: a
    granted message is known, a granted frame tool-free, a granted field read as its decision says (free by
    default); one not granted (off or unevaluated) is left out of the known messages and the tool-free frames,
    and a field's value is an unknown call (`ask`). The nested-work and in-run tables are the binary's own; a
    switch that routes `_host` to another machine (in_run host routed) is listed with its decision.
    (forms, [new item])."""
    binary = json.loads((Path(root) / 'proof/VELDO-0062/cli-formats.json').read_text())['claude_code']['tool_forms']
    previous = previous or {}
    known = {'messages': {_tag(m) for m in previous.get('messages') or ()},
             'frames': {_tag(f) for f in previous.get('tool_free_frames') or ()},
             'tool_fields': {'%s %s' % (tag, path): how for tag, paths in (previous.get('tool_fields') or {}).items()
                             for path, how in paths.items() if how != 'ask'}}
    current = {'messages': {_tag(m): m for m in binary['messages']},
               'frames': {_tag(f[:2]): f[:2] for f in binary['frames'] if f[2]},
               'tool_fields': {'%s %s' % (tag, path): (tag, path) for source in ('tool_fields', 'emitted_tool_fields')
                               for tag, paths in (binary.get(source) or {}).items() for path in paths}}
    table = (decisions.get('claude_code') or {})
    items, granted, fresh = [], {}, {}
    for kind in ('messages', 'frames', 'tool_fields'):
        fresh[kind] = newer(current[kind], set(known[kind]), carried, kind, same)
        items += decided(decisions, 'claude_code', kind, fresh[kind])
        granted[kind] = {name for name in current[kind] if name not in fresh[kind] and name in known[kind]} | {
            name for name in fresh[kind] if ((table.get(kind) or {}).get(name) or {}).get('decision') == 'granted'}
    fields = {}
    for name, (tag, path) in sorted(current['tool_fields'].items()):
        if name not in granted['tool_fields']:
            how = 'ask'
        elif name in fresh['tool_fields']:
            how = table['tool_fields'][name].get('read', 'free')
        else:
            how = known['tool_fields'][name]
        fields.setdefault(tag, {})[path] = how
    host = dict(binary['in_run']['host'])
    routed = host.pop('routed')
    if isinstance(routed, str):
        before = previous.get('routed')
        items += decided(decisions, 'claude_code', 'routing',
                         newer({routed}, {before} if before is not None else set(), carried, 'routing', same))
    order = lambda pair: (pair[0], pair[1] or '')
    forms = {'messages': sorted((current['messages'][n] for n in granted['messages']), key=order),
             'tool_free_frames': sorted((current['frames'][n] for n in granted['frames']), key=order),
             'tool_fields': fields,
             'nested': {k: v for k, v in binary['nested_work'].items() if k not in ('tools', 'source')},
             'in_run_tools': binary['in_run']['tools'], 'in_run_host': host, 'routed': routed}
    return forms, items


def new_tools(entry, known):
    """VELDO-0230 AC3: the registry tools of a qualified Claude Code entry that the replaced record's
    classification did not hold, each with the class the new classification gives it."""
    return [(name, entry['tool_classification'][name]['class'])
            for name in sorted(set(entry['tool_registry']) - set(known))] if known else []


def main(argv=None):
    parser = argparse.ArgumentParser(description='Qualify the installed or named Codex and Claude Code.')
    parser.add_argument('--codex', help='the Codex vendor binary (default: the one the codex on PATH runs)')
    parser.add_argument('--claude', help='a Claude Code version or path (default: the claude on PATH)')
    parser.add_argument('--root', default=str(ROOT), help='the repository to write (default: this one)')
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    codex = Path(args.codex).resolve() if args.codex else installed_codex()
    claude = installed_claude(args.claude)
    for path in (codex, claude):
        if not path.is_file():
            raise SystemExit('qualify: no such binary: %s' % path)
    written = []
    try:
        previous = engines(root / '.veldo/runtime/engines.json')
    except (OSError, ValueError):
        previous = None
    try:
        known_tools = set(next(iter(json.loads((root / '.veldo/runtime/claude-qualification.json').read_text())
                                    ['versions'].values()))['tool_classification'])
    except (OSError, ValueError, KeyError, StopIteration):
        known_tools = set()
    before = previous_tables(root)
    forms_before = previous_forms(root)
    codex_before, claude_before = previous_new(root, 'codex'), previous_new(root, 'claude_code')
    try:
        decisions = json.loads((root / DECISIONS).read_text())
    except (OSError, ValueError):
        decisions = {}
    record = engines_record(codex, claude)
    write(root, 'engines.json', text(record), written)
    for script, reads, tables in EXTRACTORS:
        argv = [sys.executable, '-B', str(root / script)]
        argv += ['--claude', str(claude)] if 'claude' in reads else []
        argv += ['--codex', str(codex)] if 'codex' in reads else []
        done = subprocess.run(argv, cwd=root, capture_output=True, text=True)
        if done.returncode:
            sys.stderr.write(done.stdout + done.stderr)
            raise SystemExit('qualify: %s failed on these binaries (exit %d)' % (script, done.returncode))
        written += [str(Path(script).parent / table) for table in tables]
    X = load('qualify_codex', root / '.veldo/control_engine_codex.py')
    codex_record = X.qualification(str(codex), catalog=True)
    # VELDO-0230 AC3: every new item the binary brings, with its evaluation (the features before the loopback
    # captures, since a granted feature stays on at launch; the readers and grants those captures find, after).
    same = codex_before[0] == codex_record['sha256']
    listing = {line.split()[0]: line.split()[-1] == 'true' for line in codex_record['feature_listing'].splitlines()
               if line.strip()}
    unclassified = set(codex_record['unclassified_default_on'] or ())
    fresh = newer(listing, before['codex_features'], codex_before[1], 'features', same) - unclassified
    options = json.loads((root / 'proof/VELDO-0156/codex-baseline.json').read_text())['options']
    codex_new = decided(decisions, 'codex', 'features', unclassified) + decided(
        decisions, 'codex', 'features', fresh, {'decision': 'not_applicable', 'reason': (
            'off by default, or classified by VELDO-0127; Veldo writes every listed feature it does not grant off')})
    codex_new += decided(decisions, 'codex', 'options', newer(options, before['codex_options'], codex_before[1],
                                                              'options', same), {
        'decision': 'not_applicable', 'reason': 'Veldo passes only its qualified flags and baseline options'})
    codex_record['new_capabilities'] = codex_new
    write(root, 'codex-qualification.json', text(codex_record), written)
    claude_qualification = claude_record(root, claude)
    entry = claude_qualification['versions'][record['claude_code']['version']]
    same = claude_before[0] == entry['sha256']
    cli = json.loads((root / 'proof/VELDO-0060/cli-options.json').read_text())['claude_code']['options']
    tables = json.loads((root / 'proof/VELDO-0062/cli-formats.json').read_text())['claude_code']['credential_tables']
    names = {}
    for table in tables:
        for name in table['names']:
            names.setdefault(name, ((table.get('exceptions') or {}).get(name) or {}).get('decision', table['decision']))
    entry['new_capabilities'] = (
        decided(decisions, 'claude_code', 'tools', newer(entry['tool_registry'], before['claude_tools'],
                                                         claude_before[1], 'tools', same))
        + decided(decisions, 'claude_code', 'environment', newer(names, before['claude_environment'],
                                                                 claude_before[1], 'environment', same))
        + decided(decisions, 'claude_code', 'options', newer(cli, before['claude_options'], claude_before[1],
                                                             'options', same), {
            'decision': 'not_applicable', 'reason': 'Veldo passes only its qualified flags and baseline options'}))
    entry['stream_forms'], found = stream_forms(root, forms_before, claude_before[1], same, decisions)
    entry['new_capabilities'] += found
    write(root, 'claude-qualification.json', text(claude_qualification), written)
    fixtures(root, codex, written)
    codex_record = json.loads((root / '.veldo/runtime/codex-qualification.json').read_text())
    found = decided(decisions, 'codex', 'tools_without_server', set().union(
        *codex_record['mcp_resource_rule']['offered_without_server'].values())) + decided(
        decisions, 'codex', 'grants', codex_record['undelivered_grants'])
    if found:
        codex_record['new_capabilities'] += found
        write(root, 'codex-qualification.json', text(codex_record), [])
    print('qualified codex %s (%s) %s' % (record['codex']['version'], record['codex']['binary'], record['codex']['sha256']))
    print('qualified claude_code %s (%s) %s' % (record['claude_code']['version'], record['claude_code']['binary'],
                                               record['claude_code']['sha256']))
    if previous:
        print('replaced codex %s, claude_code %s' % (previous['codex']['version'], previous['claude_code']['version']))
    print('codex features on by default the classification does not name: %s'
          % (', '.join(codex_record['unclassified_default_on']) or 'none'))
    print('claude_code tools the replaced classification did not hold: %s'
          % (', '.join('%s (%s)' % pair for pair in new_tools(entry, known_tools)) or 'none'))
    # VELDO-0230 AC3: every new item and its decision (runtime/capability-decisions.json); also in each record.
    for engine, items in (('codex', codex_record['new_capabilities']), ('claude_code', entry['new_capabilities'])):
        for item in items:
            print('new %s %s %s: %s%s (%s)' % (engine, item['kind'], item['name'], item['decision'],
                                              ' by ' + item['rule'] if item.get('rule') else '', item['reason']))
        print('new %s items: %d, %s' % (engine, len(items), ', '.join(
            '%d %s' % (n, d) for d, n in sorted(__import__('collections').Counter(i['decision'] for i in items).items()))
            or 'none'))
    print('claude_code built-in plugins and skills turned off in a role-bound run: %s; %s'
          % (', '.join(entry['engine_plugins']) or 'none', ', '.join(entry['engine_skills']) or 'none'))
    for line in written:
        print('wrote ' + line)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
