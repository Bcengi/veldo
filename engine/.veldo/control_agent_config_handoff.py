"""Compile a bound role into engine inputs and compare the observed launch set."""
import copy
import http.server
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import tempfile
import threading
import time
import urllib.request

from importlib.util import spec_from_file_location, module_from_spec

_spec = spec_from_file_location('handoff_config', Path(__file__).with_name('control_agent_config.py'))
C = module_from_spec(_spec)
_spec.loader.exec_module(C)
Refused = C.Refused
_wire_spec = spec_from_file_location('handoff_codex', Path(__file__).with_name('control_engine_codex.py'))
X = module_from_spec(_wire_spec)
_wire_spec.loader.exec_module(X)
_git_spec = spec_from_file_location('handoff_git_process', Path(__file__).with_name('git_process.py'))
_git_process = module_from_spec(_git_spec)
_git_spec.loader.exec_module(_git_process)
OPTION = '-' * 2
CODEX_NATIVE = {'shell': 'shell_tool', 'apply_patch': 'apply_patch_freeform',
                'view_image': 'view_image', 'multi_agent': 'multi_agent'}


def selected(revision, field):
    return [i for i in revision[field] if i['load'] == 'always']


def content(item, roots):
    root = roots.get(item['source'])
    if root is None:
        raise Refused('missing_evidence:instruction_source')
    path = Path(root) / item['path']
    try:
        return path.read_text()
    except OSError:
        raise Refused('missing_evidence:instruction_file') from None


def materialize(conn, domain, repository, revision, roots):
    """Read only listed sources. Bodies go to private engine input, never ordinary views."""
    if not revision:
        return None
    if 'digest' not in revision:
        raise Refused('invalid_input:role_revision')
    C.verify_binding(conn, domain, repository, revision)
    settings = revision['settings']
    allowed = {'model'} if revision['engine'] == 'claude_code' else {'model', 'sandbox_mode', 'model_reasoning_effort'}
    if set(settings) - allowed or any(not isinstance(v, str) or not v for v in settings.values()):
        raise Refused('unsupported_configuration:engine_settings')
    if revision['engine'] == 'codex' and set(revision['native_tools']) - C.CODEX_CAPABILITIES:
        raise Refused('unsupported_configuration:native_tools')
    skills = []
    for item in selected(revision, 'skills'):
        source = C.read(conn, domain, repository, item['skill'], item['revision'], C.KINDS[1])
        skills.append({'name': item['skill'], 'body': content(source, roots),
                       'source_path': str(Path(roots[source['source']]) / source['path'])})
    return {'revision': revision, 'project': roots.get('project'), 'instructions': '\n\n'.join(content(i, roots) for i in selected(revision, 'instructions')),
            'skills': skills}


def _values(server, field):
    return {n: i['literal'] if 'literal' in i else i['handle'].reveal() for n, i in server[field].items()}


def tools_list(server):
    """The server's own authenticated MCP listing, before an engine can receive a prompt."""
    init = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                       'clientInfo': {'name': 'veldo', 'version': '1'}}}
    ready = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
    proc = None
    session = {}
    deadline = time.monotonic() + 15
    try:
        if server['transport'] == 'stdio':
            env = {n: os.environ[n] for n in ('PATH', 'HOME') if n in os.environ}
            env.update(_values(server, 'environment'))
            proc = subprocess.Popen([server['command']] + server['arguments'], stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
            selector = selectors.DefaultSelector()
            selector.register(proc.stdout, selectors.EVENT_READ)
            pending = bytearray()

            def exchange(message):
                proc.stdin.write((json.dumps(message) + '\n').encode())
                proc.stdin.flush()
                if 'id' not in message:
                    return {}
                while time.monotonic() < deadline:
                    if b'\n' not in pending:
                        if not selector.select(max(0, deadline - time.monotonic())):
                            break
                        chunk = os.read(proc.stdout.fileno(), 65536)
                        if not chunk:
                            break
                        pending.extend(chunk)
                    while b'\n' in pending:
                        raw, _, rest = pending.partition(b'\n')
                        pending[:] = rest
                        answer = json.loads(raw)
                        if answer.get('id') == message['id']:
                            return answer
                raise Refused('unavailable_service:mcp_server:' + server['id'])
        else:
            def exchange(message):
                headers = dict(_values(server, 'headers'), **{'Content-Type': 'application/json',
                               'Accept': 'application/json, text/event-stream'})
                headers.update(session)
                request = urllib.request.Request(server['url'], json.dumps(message).encode(), headers)
                with urllib.request.urlopen(request, timeout=15) as response:
                    if response.headers.get('Mcp-Session-Id'):
                        session['Mcp-Session-Id'] = response.headers['Mcp-Session-Id']
                    raw = response.read().decode()
                if not raw:
                    return {}
                return json.loads(_event_stream_data(raw))
        if 'result' not in exchange(init):
            raise Refused('unavailable_service:mcp_initialize:' + server['id'])
        exchange(ready)
        names, cursor = [], None
        while True:
            answer = exchange({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list',
                               'params': {'cursor': cursor} if cursor else {}}).get('result', {})
            if not isinstance(answer.get('tools'), list):
                raise Refused('missing_evidence:mcp_tools:' + server['id'])
            names.extend(t['name'] for t in answer['tools'])
            cursor = answer.get('nextCursor')
            if not cursor:
                return sorted(names)
            if time.monotonic() > deadline:
                raise Refused('unavailable_service:mcp_tools:' + server['id'])
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise Refused('unavailable_service:mcp_server:' + server['id']) from None
    finally:
        if proc is not None:
            proc.kill()
            proc.communicate()
            selector.close()


def _event_stream_data(raw):
    """The JSON body of a streamable HTTP answer: the body itself, or its first server-sent event's data field
    (the MCP streamable HTTP transport's `event:`/`data:` frames)."""
    if not re.match(r'(?:event|data):', raw):
        return raw
    found = re.search(r'(?m)^data:(.*)$', raw)
    if found is None:
        raise ValueError('no data field')
    return found.group(1).strip()


def inventory(capability, servers):
    revision = capability['revision']
    selections = selected(revision, 'mcp')
    if {s['id'] for s in servers} != {s['server'] for s in selections}:
        raise Refused('configuration_stop:mcp_servers')
    chosen = {}
    for item in selections:
        server = next(s for s in servers if s['id'] == item['server'])
        if server['revision'] != item['revision']:
            raise Refused('configuration_stop:mcp_revision')
        offered = tools_list(server)
        wanted = offered if item['tools'] == 'all' else sorted(item['tools'])
        if set(wanted) - set(offered):
            raise Refused('unavailable_service:mcp_tools:' + server['id'])
        chosen[server['id']] = {'tools': wanted, 'offered': offered}
    return chosen


def expected(capability, inventory):
    revision = capability['revision']
    skills = ['veldo-role:' + s['name'] for s in capability['skills']]
    return {'tools': sorted(revision['native_tools'] + ['mcp__%s__%s' % (s, t)
                                                      for s, entry in inventory.items() for t in entry['tools']]),
            'mcp_servers': sorted(inventory), 'skills': sorted(skills), 'slash_commands': sorted(skills),
            'plugins': ['veldo-role'] if skills else [], 'model': revision['settings'].get('model')}


def builtin_commands(commands):
    """Exclude a command name only when every entry of that name is built-in."""
    entries = {}
    for command in commands if isinstance(commands, list) else []:
        if isinstance(command, dict) and isinstance(command.get('name'), str):
            entries.setdefault(command['name'], []).append(command.get('builtin') is True)
    return tuple(sorted(name for name, flags in entries.items() if all(flags)))


def difference(event, wanted, builtin=()):
    """The named stop for an init event whose launch set differs from `wanted` in either direction, else None.
    `builtin` names the engine's own built-in commands (its initialize answer marks them): typed commands the
    model is not offered, left out of the slash commands only; every skill the model is offered is compared."""
    for field in ('tools', 'mcp_servers', 'slash_commands', 'skills', 'plugins'):
        value = event.get(field)
        if not isinstance(value, list):
            return 'configuration_stop:' + field
        if field == 'slash_commands':
            value = [v for v in value if v not in set(builtin)]
        if field in ('mcp_servers', 'plugins'):
            if not all(isinstance(v, dict) and isinstance(v.get('name'), str) for v in value):
                return 'configuration_stop:' + field
            if field == 'mcp_servers' and any(v.get('status') != 'connected' for v in value):
                return 'configuration_stop:mcp_servers'
            value = [v['name'] for v in value]
        if field == 'tools' and set(value) - set(wanted[field]):
            return 'configuration_stop:unexpected_tool'
        if sorted(value) != sorted(wanted[field]):
            return 'configuration_stop:' + field
    if wanted.get('model') is not None and event.get('model') != wanted['model']:
        return 'configuration_stop:model'
    return None


# What Claude Code 2.1.281 loads of its own beyond the qualified baseline, read from its init event with
# nothing listed: its built-in plugins (on in every run), and, once `--disable-slash-commands` gives way to a
# role's skills, its bundled skills (the disableBundledSkills setting removes them) and the built-in skills
# that setting leaves (skillOverrides "off" hides each from the model and from typing). A role-bound run turns
# every one off in its generated settings; one a later version adds reaches the init comparison and stops it.
CLAUDE_ENGINE_PLUGINS = ('agents-md@builtin', 'telemetry@builtin')
CLAUDE_ENGINE_SKILLS = ('design', 'doctor')
SETTINGS_FILE = 'settings.json'


def claude(extra, capability, inventory, config):
    revision = capability['revision']
    wanted = expected(capability, inventory)
    extra['expected'] = wanted
    if SETTINGS_FILE not in extra['files']:
        raise Refused('missing_evidence:engine_settings')
    settings = json.loads(extra['files'][SETTINGS_FILE])
    settings.update(enabledPlugins={name: False for name in CLAUDE_ENGINE_PLUGINS}, disableBundledSkills=True,
                    skillOverrides={name: 'off' for name in CLAUDE_ENGINE_SKILLS})
    extra['files'][SETTINGS_FILE] = (json.dumps(settings, sort_keys=True) + '\n').encode()
    extra['argv'] += [OPTION + 'debug-file', str(config / 'role-debug.log')]
    if capability['instructions']:
        extra['files']['role-instructions.md'] = capability['instructions'].encode()
        extra['argv'] += [OPTION + 'append-system-prompt-file', str(config / 'role-instructions.md')]
    # `--disable-slash-commands` also withdraws the Skill tool, so a role granting it, or listing a skill, runs
    # without it; the generated settings above keep the engine's own skills off either way.
    if capability['skills'] or 'Skill' in revision['native_tools']:
        extra['argv'].remove(OPTION + 'disable-slash-commands')
    if capability['skills']:
        extra['argv'] += [OPTION + 'plugin-dir', str(config / 'role-plugin')]
        extra['files']['role-plugin/.claude-plugin/plugin.json'] = json.dumps({'name': 'veldo-role'}).encode()
        for skill in capability['skills']:
            extra['files']['role-plugin/skills/' + skill['name'] + '/SKILL.md'] = skill['body'].encode()
    if revision['settings'].get('model'):
        extra['argv'] += [OPTION + 'model', revision['settings']['model']]
    # MCP tools stay server-prefixed. Deny unselected tools, including a listed server's other tools.
    denied = ['mcp__%s__%s' % (s, t) for s, e in inventory.items() for t in e['offered'] if t not in e['tools']]
    for index, arg in enumerate(extra['argv']):
        if arg.startswith(OPTION + 'disallowedTools=') and denied:
            extra['argv'][index] += (',' if not arg.endswith('=') else '') + ','.join(sorted(denied))
    return extra


def codex_model(bound, revision):
    """Use only the digest-bound bundled entry; never substitute a model."""
    model = revision['settings'].get('model')
    catalog = bound.get('model_catalog')
    entries = catalog.get('models', []) if isinstance(catalog, dict) else []
    entry = next((m for m in entries if m.get('slug') == model), None)
    if (not entry or bound.get('model_catalog_digest') != X.catalog_digest(catalog)
            or not all(k in entry for k in ('experimental_supported_tools', 'apply_patch_tool_type', 'supports_search_tool'))):
        if bound.get('model_tool_modes', {}).get(model) == 'code_mode_only':
            raise Refused('configuration_stop:codex_code_mode_model')
        raise Refused('configuration_stop:codex_model_catalog')
    selected = copy.deepcopy(entry)
    grants = set(revision['native_tools'])
    if not grants.intersection({'sub_agents', 'multi_agent'}):
        selected.pop('multi_agent_version', None)
    if 'apply_patch' not in grants:
        selected['apply_patch_tool_type'] = None
    experimental = {'send_user_message_async': 'request_user_input_async', 'clock': 'clock'}
    selected['experimental_supported_tools'] = [n for n in entry['experimental_supported_tools']
                                                if experimental.get(n, n) in grants]
    if 'tool_search' not in grants:
        selected['supports_search_tool'] = False
    return dict(copy.deepcopy(catalog), models=[selected])


def codex_features(listing, grants):
    """Classify every enabled binary default, including login-dependent tool sources.

    The complete features-list output belongs to the digest-bound qualification.
    An unknown enabled feature is potentially a tool source and refuses launch.
    """
    mapped = {
        'shell_tool': {'shell'}, 'unified_exec': {'shell'}, 'unified_exec_tty': {'shell'},
        'view_image': {'view_image'}, 'multi_agent': {'multi_agent', 'sub_agents'},
        'sleep_tool': {'clock'},
    }
    ungranted = {
        'apps', 'browser_use', 'browser_use_external', 'browser_use_full_cdp_access',
        'computer_use', 'goals', 'hooks', 'image_generation', 'in_app_browser',
        'in_app_local_automation', 'mentions_v2', 'plugins', 'remote_plugin',
        'skill_mcp_dependency_install', 'skill_search', 'tool_suggest', 'workspace_dependencies',
    }
    # These defaults change protocol, UI, transport or execution implementation;
    # they do not register another tool. Code Mode's runner is model-selected.
    non_tools = {
        'auth_elicitation', 'code_mode_host', 'collaboration_modes', 'compaction_image_budget',
        'content_item_kinds', 'enable_request_compression', 'fast_mode', 'guardian_approval',
        'in_app_chat', 'in_app_dictation', 'in_app_updates', 'item_ids', 'personality',
        'plugin_sharing', 'remote_compaction_v2', 'resize_all_images', 'shell_snapshot',
        'sqlite', 'steer', 'terminal_resize_reflow', 'tool_call_mcp_elicitation',
        'tool_search_always_defer_mcp_tools', 'tui_app_server', 'unbounded_connection_retries',
        'unified_exec_zsh_fork',
    }
    defaults = {}
    if not isinstance(listing, str) or not listing.strip():
        raise Refused('configuration_stop:codex_feature_listing')
    for line in listing.splitlines():
        match = re.fullmatch(r'([a-z0-9_.]+)\s+([a-z ]+?)\s+(true|false)\s*', line)
        if not match or match[1] in defaults:
            raise Refused('configuration_stop:codex_feature_listing')
        defaults[match[1]] = match[3] == 'true'
    configuration = {}
    for feature, enabled in defaults.items():
        if not enabled:
            continue
        if feature in mapped:
            configuration['features.' + feature] = bool(mapped[feature].intersection(grants))
        elif feature in ungranted:
            configuration['features.' + feature] = False
        elif feature not in non_tools:
            raise Refused('configuration_stop:codex_unknown_default_feature:' + feature)
    return configuration


def codex(configuration, capability, inventory, config, *, catalog=None, feature_listing=None):
    revision = capability['revision']
    configuration.update(revision['settings'])
    if feature_listing is None:
        feature_listing = X.load_qualification().get('feature_listing', '')
    configuration.update(codex_features(feature_listing, set(revision['native_tools'])))
    for name, feature in CODEX_NATIVE.items():
        configuration['features.' + feature] = name in revision['native_tools']
    configuration['tools.update_plan'] = {'enabled': 'update_plan' in revision['native_tools']}
    configuration['tools.experimental_request_user_input'] = {'enabled': False}
    configuration['features.goals'] = False
    agents = bool(set(revision['native_tools']) & {'multi_agent', 'sub_agents'})
    configuration['features.multi_agent'] = agents
    configuration['features.multi_agent_v2'] = {'enabled': agents}
    configuration['web_search'] = 'live' if 'web_search' in revision['native_tools'] else 'disabled'
    configuration['developer_instructions'] = capability['instructions']
    for server, entry in inventory.items():
        configuration['mcp_servers'][server]['enabled_tools'] = entry['tools']
        configuration['mcp_servers'][server]['required'] = True
    # The receiver stages only these generated skills in the clone's discovery directory.
    if catalog is None:
        catalog = codex_model(X.load_qualification(), revision)
    configuration['model_catalog_json'] = str(config / 'model-catalog.json')
    files = {'model-catalog.json': json.dumps(catalog, sort_keys=True).encode()}
    if capability['skills']:
        configuration['skills.include_instructions'] = True
        configuration['skills.config'] = [
            {'path': str(Path(capability['project']) / '.agents/skills' / skill['name'] / 'SKILL.md'), 'enabled': True}
            for skill in capability['skills']]
        for skill in capability['skills']:
            files['role-skills/' + skill['name'] + '/SKILL.md'] = skill['body'].encode()
    return files


def codex_request_tools(body):
    """Tool definitions from the pinned wire: Responses tools or additional_tools, or Chat tools."""
    arrays = []
    if isinstance(body.get('tools'), list):
        arrays.append(body['tools'])
    for item in body.get('input', []):
        if isinstance(item, dict) and item.get('type') == 'additional_tools' and isinstance(item.get('tools'), list):
            arrays.append(item['tools'])
    if not arrays:
        raise Refused('missing_evidence:codex_request_tools')
    return [tool for array in arrays for tool in array]


def codex_name(name):
    name = name.removeprefix('functions.')
    if name == 'web__run':
        return 'web_search'
    if name.startswith('mcp__'):
        name = name[:5] + name[5:].replace('.', '__', 1)
    return name


def codex_tool_names(tools, namespace=''):
    """Effective definitions: Code Mode runner plus its nested declarations, or direct tools."""
    names = []
    for tool in tools:
        if tool.get('type') == 'namespace':
            names.extend(codex_tool_names(tool['tools'], tool['name'] + '.'))
            continue
        definition = tool.get('function') if isinstance(tool.get('function'), dict) else tool
        name = codex_name(namespace + definition.get('name', tool.get('type', '')))
        names.append(name)
        if name == 'exec':
            names.extend(codex_name(n) for n in re.findall(r'^### `([^`]+)`\s*$',
                                                         definition.get('description', ''), re.M))
    return sorted(names)


def codex_expected_tools(wanted, body):
    names = [codex_name(n) for name in wanted['tools'] for n in X.NATIVE_TOOL_MAPPING.get(name, [name])]
    if wanted.get('mcp_servers'):
        names.extend(X.NATIVE_TOOL_MAPPING['mcp_server'])
    # Runner presence is determined by the accepted model, not by an untrusted tool list.
    if X.MODEL_TOOL_MODES.get(wanted.get('model')) == 'code_mode_only':
        names.extend(['exec', 'wait'])
    return sorted(set(names))


def codex_tool_difference(body, wanted):
    """Exact equality after expanding native grants and normalizing wire spellings."""
    expected_names = codex_expected_tools(wanted, body)
    try:
        actual = codex_tool_names(codex_request_tools(body))
    except Refused as error:
        return error.code
    if set(actual) - set(expected_names):
        return 'configuration_stop:codex_unexpected_tool'
    if set(actual) != set(expected_names):
        return 'configuration_stop:codex_missing_tool'
    return None


def codex_observe(bound, extra, environment, config):
    """Ask the pinned worker for its actual definitions before giving it the task.

    The generated overrides and MCP connections are the worker's. Only the model
    transport and provider login home are replaced. The loopback endpoint records
    definitions and rejects the request, so no model or tool turn can execute.
    Never retain the request's context, credentials, stdout or stderr.
    """
    observations = []

    class Endpoint(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                observations.append({'tools': codex_request_tools(body)})
            except (ValueError, KeyError, Refused):
                observations.append({})
            self.send_response(400)
            self.end_headers()

    with tempfile.TemporaryDirectory(prefix='tool-observation-', dir=config) as temp:
        home = Path(temp)
        profile = home / 'profile'
        profile.mkdir(mode=0o700)
        server = http.server.HTTPServer(('127.0.0.1', 0), Endpoint)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        provider = {'name': 'role-observation', 'base_url': 'http://127.0.0.1:%d/v1' % server.server_port,
                    'wire_api': 'responses', 'supports_standalone_web_search': True,
                    'request_max_retries': 0, 'stream_max_retries': 0}
        args = [bound['path'], 'exec', OPTION + 'json', OPTION + 'skip-git-repo-check'] + extra['argv']
        for key, value in {'model_provider': 'role_observation', 'model_providers.role_observation': provider,
                           'check_for_update_on_startup': False}.items():
            args += ['-c', key + '=' + X._toml(value)]
        env = dict(PATH=environment.get('PATH', '/usr/bin:/bin'), HOME=temp, CODEX_HOME=str(profile),
                   TMPDIR=temp, LANG='C.UTF-8')
        env.update(extra['secrets'])
        try:
            subprocess.run(args, input='Report no output and use no tools.', text=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, cwd=temp, timeout=45)
        except (OSError, subprocess.SubprocessError):
            raise Refused('configuration_stop:codex_observation') from None
        finally:
            server.shutdown()
            thread.join()
            server.server_close()
    if not observations:
        raise Refused('configuration_stop:codex_observation')
    return observations


def codex_check_launch(bound, extra, environment, config):
    observations = codex_observe(bound, extra, environment, config)
    for body in observations:
        stop = codex_tool_difference(body, extra['expected'])
        if stop:
            raise Refused(stop)
    return codex_tool_names(codex_request_tools(observations[0]))


def codex_listing(bound, extra, environment, config):
    """Codex's own view of the generated MCP table, before exec sees a prompt: `mcp list` for the server set
    and `mcp get` for each server's enabled tools (the 0.154 list prints none), with exec's own overrides.
    Neither subcommand takes exec's `--ignore-user-config`; both read CODEX_HOME's config.toml, so each runs
    with CODEX_HOME an empty directory of this run's own (`listing-home` in `config`) and reads exactly the
    table exec is handed, never the account profile's own servers. Neither needs the login."""
    args = extra['argv']
    overrides = []
    for i, arg in enumerate(args):
        if arg in ('-c', OPTION + 'enable', OPTION + 'disable'):
            overrides.extend(args[i:i + 2])
    home = Path(config) / 'listing-home'
    home.mkdir(mode=0o700)
    env = dict(environment, **extra['environment'], **extra['secrets'])
    env['CODEX_HOME'] = str(home)

    def ask(command):
        try:
            done = subprocess.run([bound['path'], 'mcp'] + command + [OPTION + 'json'] + overrides, env=env,
                                  cwd=str(home), capture_output=True, timeout=20, text=True, stdin=subprocess.DEVNULL)
            return json.loads(done.stdout) if done.returncode == 0 else None
        except (OSError, ValueError, subprocess.SubprocessError):
            return None
    listing = ask(['list'])
    wanted = extra['expected']['mcp_servers']
    if (not isinstance(listing, list) or not all(isinstance(i, dict) for i in listing)
            or sorted(i.get('name', '') for i in listing) != wanted):
        raise Refused('configuration_stop:mcp_servers')
    if any(i.get('enabled') is not True for i in listing):
        raise Refused('configuration_stop:mcp_servers')
    for item in listing:
        server = ask(['get', item['name']])
        tools = [t.split('__', 2)[2] for t in extra['expected']['tools'] if t.startswith('mcp__' + item['name'] + '__')]
        if (not isinstance(server, dict) or server.get('name') != item['name'] or server.get('enabled') is not True
                or not isinstance(server.get('enabled_tools'), list) or sorted(server['enabled_tools']) != sorted(tools)):
            raise Refused('configuration_stop:mcp_tools')
        item['enabled_tools'] = list(server['enabled_tools'])
    return listing


def stage_skills(capability, config):
    staged = []
    if capability and capability['revision']['engine'] == 'codex' and capability['skills']:
        root = Path(capability['project']) / '.agents/skills'
        root.mkdir(parents=True, exist_ok=True)
        for skill in capability['skills']:
            link = root / skill['name']
            if link.is_dir() and (link / 'SKILL.md').resolve() == Path(skill['source_path']).resolve():
                continue
            exclude = _git_process.run(['git', '-C', str(capability['project']), 'rev-parse',
                                      OPTION + 'git-path', 'info/exclude'], check=True, capture_output=True, text=True)
            path = Path(exclude.stdout.strip())
            if not path.is_absolute():
                path = Path(capability['project']) / path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a') as handle:
                handle.write('\n/.agents/skills/' + skill['name'] + '\n')
            link.symlink_to(config / 'role-skills' / skill['name'], target_is_directory=True)
            staged.append(link)
    return staged


def context_size(event, engine):
    if engine == 'claude_code':
        if event.get('parent_tool_use_id') is not None:
            return None
        message = event.get('message') if event.get('type') == 'assistant' else (event.get('event') or {}).get('message')
        usage = (message or {}).get('usage')
        if isinstance(usage, dict) and 'input_tokens' in usage:
            return sum(usage.get(k, 0) for k in ('input_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'))
    elif event.get('type') == 'turn.completed':
        return (event.get('usage') or {}).get('input_tokens')
    return None
