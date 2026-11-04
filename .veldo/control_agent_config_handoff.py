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
    if repository is None:
        candidates = []
        for (raw,) in conn.execute('SELECT data FROM entities WHERE kind=?', (C.KINDS[0],)):
            value = json.loads(raw)
            if value.get('role') == revision.get('role') and value.get('revision') == revision.get('revision'):
                candidates.append(value)
        if len(candidates) != 1:
            raise Refused('missing_evidence:agent_revision')
        accepted = dict(candidates[0], native_tools=[item['name'] for item in candidates[0]['native_tools']
                                                    if item['load'] == 'always'])
        if accepted != revision:
            raise Refused('stale_version:agent_binding')
    else:
        C.verify_binding(conn, domain, repository, revision)
    settings = revision['settings']
    allowed = {'model'} if revision['engine'] == 'claude_code' else {'model', 'sandbox_mode', 'model_reasoning_effort'}
    if set(settings) - allowed or any(not isinstance(v, str) or not v for v in settings.values()):
        raise Refused('unsupported_configuration:engine_settings')
    if revision['engine'] == 'codex' and set(revision['native_tools']) - C.CODEX_CAPABILITIES:
        raise Refused('unsupported_configuration:native_tools')
    skills = []
    for item in selected(revision, 'skills'):
        if repository is None:
            sources = [json.loads(raw) for (raw,) in conn.execute(
                'SELECT data FROM entities WHERE kind=?', (C.KINDS[1],))
                if (value := json.loads(raw)).get('skill') == item['skill']
                and value.get('revision') == item['revision']]
            if len(sources) != 1:
                raise Refused('missing_evidence:agent_revision')
            source = sources[0]
        else:
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
            if field == 'plugins':
                # A built-in plugin the qualification grants (`accepted_plugins`) loads by the account, not by
                # Veldo's settings (2.1.317's cc-plugin-sec-default: Team and Enterprise organizations), so it
                # is accepted present or absent; every other plugin is compared.
                accepted = set(wanted.get('accepted_plugins') or ())
                value = [v for v in value if (v.get('source') if isinstance(v.get('source'), str)
                                              else v['name'] + '@builtin') not in accepted]
            value = [v['name'] for v in value]
        if field == 'tools' and set(value) - set(wanted[field]):
            return 'configuration_stop:unexpected_tool'
        if sorted(value) != sorted(wanted[field]):
            return 'configuration_stop:' + field
    if wanted.get('model') is not None and event.get('model') != wanted['model']:
        return 'configuration_stop:model'
    return None


# What Claude Code loads of its own beyond the qualified baseline, read from its init event with nothing
# listed (VELDO-0230: by .veldo/qualify.py into the version's record, `engine_plugins` and `engine_skills`):
# its built-in plugins (on in every run), and, once `--disable-slash-commands` gives way to a role's skills,
# the built-in skills the disableBundledSkills setting leaves (skillOverrides "off" hides each from the model
# and from typing; the setting removes the bundled ones). A role-bound run turns every one off in its
# generated settings; one a later version adds reaches the init comparison and stops it until requalified.
# VELDO-0230 AC3: qualify reads every built-in plugin the binary registers (not only those an empty, logged-out
# profile loads) and evaluates each; one granted is `accepted_plugins`, left on and accepted in the init event
# whether the account seats it or not; every other one is in `engine_plugins` and turned off.
SETTINGS_FILE = 'settings.json'


def claude(extra, capability, inventory, config, *, engine):
    """`engine` is the version's qualification entry, whose `engine_plugins` and `engine_skills` are turned off."""
    revision = capability['revision']
    wanted = expected(capability, inventory)
    extra['expected'] = wanted
    if SETTINGS_FILE not in extra['files']:
        raise Refused('missing_evidence:engine_settings')
    plugins, skills = engine.get('engine_plugins'), engine.get('engine_skills')
    accepted = engine.get('accepted_plugins', [])
    if not all(isinstance(names, list) and all(isinstance(n, str) for n in names)
               for names in (plugins, skills, accepted)) or set(plugins) & set(accepted):
        raise Refused('missing_evidence:engine_settings')
    if accepted:
        wanted['accepted_plugins'] = sorted(accepted)
    settings = json.loads(extra['files'][SETTINGS_FILE])
    settings.update(enabledPlugins={name: False for name in plugins}, disableBundledSkills=True,
                    skillOverrides={name: 'off' for name in skills})
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


# The classification of Codex features (VELDO-0127): the features that deliver a grant, the tool sources no
# role is granted, and the defaults that change protocol, UI, transport or execution implementation without
# registering another tool (Code Mode's runner is model-selected). Veldo's own policy, not the binary's list.
CODEX_FEATURE_GRANTS = {
    'shell_tool': {'shell'}, 'unified_exec': {'shell'}, 'unified_exec_tty': {'shell'},
    'view_image': {'view_image'}, 'multi_agent': {'multi_agent', 'sub_agents'},
    'sleep_tool': {'clock'},
}
CODEX_FEATURES_UNGRANTED = {
    'apps', 'browser_use', 'browser_use_external', 'browser_use_full_cdp_access',
    'computer_use', 'goals', 'hooks', 'image_generation', 'in_app_browser',
    'in_app_local_automation', 'mentions_v2', 'plugins', 'remote_plugin',
    'skill_mcp_dependency_install', 'skill_search', 'tool_suggest', 'workspace_dependencies',
}
CODEX_FEATURES_NON_TOOLS = {
    'auth_elicitation', 'code_mode_host', 'collaboration_modes', 'compaction_image_budget',
    'content_item_kinds', 'enable_request_compression', 'fast_mode', 'guardian_approval',
    'in_app_chat', 'in_app_dictation', 'in_app_updates', 'item_ids', 'personality',
    'plugin_sharing', 'remote_compaction_v2', 'resize_all_images', 'shell_snapshot',
    'sqlite', 'steer', 'terminal_resize_reflow', 'tool_call_mcp_elicitation',
    'tool_search_always_defer_mcp_tools', 'tui_app_server', 'unbounded_connection_retries',
    'unified_exec_zsh_fork',
}


def codex_defaults(listing):
    """{feature: on by default} of a `features list` output; a malformed listing is refused."""
    defaults = {}
    if not isinstance(listing, str) or not listing.strip():
        raise Refused('configuration_stop:codex_feature_listing')
    for line in listing.splitlines():
        match = re.fullmatch(r'([a-z0-9_.]+)\s+([a-z ]+?)\s+(true|false)\s*', line)
        if not match or match[1] in defaults:
            raise Refused('configuration_stop:codex_feature_listing')
        defaults[match[1]] = match[3] == 'true'
    return defaults


def codex_unclassified(listing):
    """VELDO-0230 AC3: the features on by default that the classification does not name, sorted. Each is
    turned off at launch (codex_features) and listed in the qualification record and the qualify output."""
    known = set(CODEX_FEATURE_GRANTS) | CODEX_FEATURES_UNGRANTED | CODEX_FEATURES_NON_TOOLS
    return sorted(f for f, on in codex_defaults(listing).items() if on and f not in known)


def codex_granted(record=None):
    """VELDO-0230 AC3 (Telegram 38878): the features the qualification record lists as new whose evaluation
    (runtime/capability-decisions.json, copied there by .veldo/qualify.py) grants them: left at their default."""
    try:
        record = X.load_qualification() if record is None else record
    except Refused:
        return frozenset()
    return frozenset(item['name'] for item in record.get('new_capabilities') or ()
                     if isinstance(item, dict) and item.get('kind') == 'features' and item.get('decision') == 'granted')


def codex_features(listing, grants, granted=frozenset()):
    """Control every listed feature, including login-dependent tool sources.

    The complete features-list output belongs to the digest-bound qualification. A feature the
    classification does not name is potentially a tool source: it is off, whatever its default
    (VELDO-0230 AC3: a newer binary never blocks the launch), unless its evaluation grants it
    (`granted`: on by default, it stays so; the wire comparison still binds every tool).
    """
    defaults = codex_defaults(listing)
    configuration = {}
    for feature, enabled in defaults.items():
        if feature in CODEX_FEATURES_NON_TOOLS:
            continue
        if feature in granted and feature not in CODEX_FEATURE_GRANTS and feature not in CODEX_FEATURES_UNGRANTED:
            continue
        key = 'features.' + feature
        if feature in CODEX_FEATURE_GRANTS:
            configuration[key] = bool(CODEX_FEATURE_GRANTS[feature].intersection(grants))
        else:
            configuration[key] = False
        if '.' in feature:
            # CLI dotted paths cannot quote a literal dot; use an inline table.
            configuration.setdefault('features', {})[feature] = configuration.pop(key)
    return configuration


def codex(configuration, capability, inventory, config, *, catalog=None, feature_listing=None):
    revision = capability['revision']
    configuration.update(revision['settings'])
    if feature_listing is None:
        feature_listing = X.load_qualification().get('feature_listing', '')
    configuration.update(codex_features(feature_listing, set(revision['native_tools']), codex_granted()))
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
    # Serialize one table in both the profile and CLI, after every grant override.
    # Literal feature dots remain quoted table keys, not TOML path separators.
    features = configuration.setdefault('features', {})
    for key in list(configuration):
        if key.startswith('features.'):
            features[key[len('features.'):]] = configuration.pop(key)
    return files


# The input items of a request that declare tool definitions to the model: `additional_tools` (a Code Mode
# model's declaration, and with the incremental_tools feature each later tool-list update, which follows the
# developer message "This is an incremental tools update. Previously declared tools remain available..."; Codex
# 0.166.0 on loopback, proof/VELDO-0230/fix3-incremental-capture.json) and `tool_search_output` (definitions a
# tool search loads into the session).
DECLARING_ITEMS = ('additional_tools', 'tool_search_output')


def codex_request_tools(body):
    """Tool definitions one request declares on the pinned wire: Responses tools, every declaring input item,
    or Chat tools."""
    arrays = []
    if isinstance(body.get('tools'), list):
        arrays.append(body['tools'])
    for item in body.get('input', []):
        if isinstance(item, dict) and item.get('type') in DECLARING_ITEMS and isinstance(item.get('tools'), list):
            arrays.append(item['tools'])
    if not arrays:
        raise Refused('missing_evidence:codex_request_tools')
    return [tool for array in arrays for tool in array]


def codex_declarations(body):
    """What of one request the comparison reads, and nothing else of its context: its Responses tools and
    its declaring input items (a later request with neither keeps its empty input)."""
    kept = {}
    if isinstance(body.get('tools'), list):
        kept['tools'] = body['tools']
    if isinstance(body.get('input'), list):
        kept['input'] = [i for i in body['input'] if isinstance(i, dict) and i.get('type') in DECLARING_ITEMS]
    if not kept:
        raise ValueError('no tools or input')
    return kept


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


def codex_expected_tools(wanted, body, modes=None):
    # VELDO-0230: a grant the qualified binary does not deliver under these switches is recorded as such and
    # left out, so the launch proceeds without it.
    undelivered = set(X.undelivered_grants())
    names = [codex_name(n) for name in wanted['tools'] if name not in undelivered
             for n in X.NATIVE_TOOL_MAPPING.get(name, [name])]
    if wanted.get('mcp_servers'):
        names.extend(X.NATIVE_TOOL_MAPPING['mcp_server'])
    # Runner presence is determined by the accepted model, not by an untrusted tool list: the qualified
    # binary's model tool modes (the bound record's, else the installed one's).
    modes = X.model_tool_modes() if modes is None else modes
    if modes.get(wanted.get('model')) == 'code_mode_only':
        names.extend(['exec', 'wait'])
    # VELDO-0230: the resource readers the binary offers with no server selected (none to list or read), as its
    # qualification records them for the model's tool mode; never a grant, and no other extra tool is accepted.
    if not wanted.get('mcp_servers'):
        names.extend(X.offered_without_server().get(modes.get(wanted.get('model')) or 'direct', []))
    return sorted(set(names))


def codex_run_tools(bodies):
    """VELDO-0230 fix round 3 (Telegram 38895-38896): the tools declared to the model at each request of a run,
    in order: what that request declares and every earlier one did. An incremental tools update declares only
    what changed ("previously declared tools remain available"), and a later request may carry only its new
    input items, so a request's own declarations are never the whole set; the tools a later request reaches
    are the union. A run with no request, or whose first request declares nothing, is refused by name; a later
    request that declares nothing keeps the earlier set."""
    declared, sets = set(), []
    for body in bodies:
        try:
            declared = declared | set(codex_tool_names(codex_request_tools(body)))
        except Refused:
            # Only a readable later request (one with its input) may declare nothing new.
            if not sets or not isinstance(body.get('input'), list):
                raise
        sets.append(sorted(declared))
    if not sets:
        raise Refused('missing_evidence:codex_request_tools')
    return sets


def codex_run_tool_difference(bodies, wanted):
    """Exact equality after expanding native grants and normalizing wire spellings, at every request of a run
    (VELDO-0127 AC4: a tool the role does not list is unexpected wherever it is first declared)."""
    expected_names = set(codex_expected_tools(wanted, {}))
    try:
        declared = codex_run_tools(bodies)
    except Refused as error:
        return error.code
    if any(set(names) - expected_names for names in declared):
        return 'configuration_stop:codex_unexpected_tool'
    if any(set(names) != expected_names for names in declared):
        return 'configuration_stop:codex_missing_tool'
    return None


def codex_tool_difference(body, wanted):
    """One request's comparison: the run comparison of a run of that request alone."""
    return codex_run_tool_difference([body], wanted)


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
                observations.append(codex_declarations(body))
            except (ValueError, KeyError, TypeError, AttributeError):
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
    stop = codex_run_tool_difference(observations, extra['expected'])
    if stop:
        raise Refused(stop)
    # Every definition the run declared, as the first request's spelling has always been reported.
    tools = []
    for body in observations:
        try:
            tools.extend(codex_request_tools(body))
        except Refused:
            pass
    return codex_tool_names(tools)


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
                                      OPTION + 'git-path', 'info/exclude'], check=False,
                                      capture_output=True, text=True)
            if exclude.returncode == 0 and exclude.stdout.strip():
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
