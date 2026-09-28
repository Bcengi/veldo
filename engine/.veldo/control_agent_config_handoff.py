"""Compile a bound role into engine inputs and compare the observed launch set."""
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
import urllib.request

from importlib.util import spec_from_file_location, module_from_spec

_spec = spec_from_file_location('handoff_config', Path(__file__).with_name('control_agent_config.py'))
C = module_from_spec(_spec)
_spec.loader.exec_module(C)
Refused = C.Refused
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
    if revision['engine'] == 'codex' and (set(revision['native_tools']) - set(CODEX_NATIVE) - {'update_plan', 'web_search'}
                                        or 'update_plan' not in revision['native_tools']):
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


def codex(configuration, capability, inventory, config):
    revision = capability['revision']
    configuration.update(revision['settings'])
    for name, feature in CODEX_NATIVE.items():
        configuration['features.' + feature] = name in revision['native_tools']
    configuration['web_search'] = 'live' if 'web_search' in revision['native_tools'] else 'disabled'
    configuration['developer_instructions'] = capability['instructions']
    for server, entry in inventory.items():
        configuration['mcp_servers'][server]['enabled_tools'] = entry['tools']
        configuration['mcp_servers'][server]['required'] = True
    # The receiver stages only these generated skills in the clone's discovery directory.
    files = {}
    if capability['skills']:
        configuration['skills.include_instructions'] = True
        configuration['skills.config'] = [
            {'path': str(Path(capability['project']) / '.agents/skills' / skill['name'] / 'SKILL.md'), 'enabled': True}
            for skill in capability['skills']]
        for skill in capability['skills']:
            files['role-skills/' + skill['name'] + '/SKILL.md'] = skill['body'].encode()
    return files


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
