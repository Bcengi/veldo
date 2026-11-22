"""Closed installation tree validation and authority classification (VELDO-0253).

Only installation.py reads the repository. This module receives immutable blob
bytes, reads product schema data, and returns all problems without publishing any
configuration. Secret checks ask for names, never values.
"""
import fnmatch
import hashlib
import importlib.util
import json
from pathlib import Path
import re


def organ(name):
    spec = importlib.util.spec_from_file_location('installation_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WF = organ('control_workflow')
I = organ('installation')
IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
SECRET_FIELD = re.compile(r'^(token|password|passwd|credential|api_key|access_token|refresh_token|client_secret)$', re.I)
SECRET_VALUES = tuple(re.compile(pattern) for _, pattern in organ('secret_scan').FORMATS)


def schema():
    return json.loads(Path(__file__).with_name('installation_schema').joinpath('schema.json').read_text())


def digest(value):
    return WF.digest(WF.canonical(value))


def decode(body):
    text = body.decode('utf-8')
    # JSON is also the canonical format setup emits for .yaml files.
    if text.lstrip().startswith(('{', '[')):
        def pairs(items):
            out = {}
            for key, value in items:
                if key in out:
                    raise ValueError('duplicate_key')
                out[key] = value
            return out
        return json.loads(text, object_pairs_hook=pairs)
    return organ('yamlish').parse(text)


def check(value, rule, definitions, path, key, problems):
    if isinstance(rule, str):
        rule = definitions[rule]
    def bad(reason):
        problems.append('installation_invalid:%s:%s:%s' % (path, key, reason))
    if key.count('.') + key.count('[') > 64:
        bad('too_deep')
        return
    if 'one_of' in rule:
        for candidate in rule['one_of']:
            failed = []
            check(value, candidate, definitions, path, key, failed)
            if not failed:
                return
        bad('type')
        return
    if rule.get('validator') == 'role_configuration':
        try:
            organ('control_agent_config').validate(value)
        except Exception as error:
            bad(getattr(error, 'code', 'schema'))
        return
    if rule.get('validator') == 'team_configuration':
        for reason in organ('control_team').schema_problems(value):
            bad(reason)
        return
    kind = rule.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if kind in types and type(value) is not types[kind]:
        bad('expected_' + kind)
        return
    if 'enum' in rule and value not in rule['enum']:
        bad('enum')
    if kind == 'string':
        if not value or '\x00' in value:
            bad('empty_or_nul')
        if rule.get('identifier') and (not IDENT.fullmatch(value) or '..' in value):
            bad('identifier')
    if kind == 'integer' and not rule.get('minimum', 0) <= value <= rule.get('maximum', 2**63 - 1):
        bad('range')
    if kind == 'object':
        fields = rule.get('properties', {})
        for field in rule.get('required', []):
            if field not in value:
                problems.append('installation_invalid:%s:%s.%s:missing' % (path, key, field))
        for field, entry in value.items():
            at = key + '.' + str(field)
            if field in fields:
                check(entry, fields[field], definitions, path, at, problems)
            elif 'values' in rule:
                valid_key = isinstance(field, str) and re.fullmatch(rule.get('key_pattern', IDENT.pattern), field)
                if not valid_key or ('key_pattern' not in rule and '..' in field):
                    problems.append('installation_invalid:%s:%s:identifier' % (path, at))
                check(entry, rule['values'], definitions, path, at, problems)
            else:
                problems.append('installation_invalid:%s:%s:unknown_key' % (path, at))
    if kind == 'array':
        for index, entry in enumerate(value):
            check(entry, rule['items'], definitions, path, '%s[%d]' % (key, index), problems)


def secrets(value, path, exists, problems, key='$'):
    if isinstance(value, dict):
        if set(value) == {'secret'}:
            name = value['secret']
            if not isinstance(name, str) or not IDENT.fullmatch(name):
                problems.append('installation_invalid:%s:%s:secret_name' % (path, key))
            elif not exists(name):
                problems.append('installation_secret_missing:' + name)
            return
        for field, child in value.items():
            at = key + '.' + str(field)
            declaration = (path.endswith(('.openapi.json', '.tools.json'))
                           and key.rsplit('.', 1)[-1] in ('properties', 'schemas', 'securitySchemes'))
            if (not declaration and SECRET_FIELD.fullmatch(str(field))
                    and not (isinstance(child, dict) and set(child) == {'secret'})):
                problems.append('installation_secret_inline:%s:%s' % (path, at))
            else:
                secrets(child, path, exists, problems, at)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            secrets(child, path, exists, problems, '%s[%d]' % (key, index))
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_VALUES):
        problems.append('installation_secret_inline:%s:%s' % (path, key))


def validate(files, *, secret_exists, resolve=None):
    """(configuration, problems), validated as a whole; ignored/history bytes never become configuration."""
    declared, config, problems = schema(), {}, []
    for path, body in sorted(files.items()):
        entry = next((entry for entry in declared['paths'] if fnmatch.fnmatchcase(path, entry['pattern'])
                      and (path.count('/') == entry['pattern'].count('/')
                           or entry.get('ignored') or entry.get('history'))), None)
        if entry is None or ('/' in path and any(part in ('', '.', '..') for part in path.split('/'))):
            problems.append('installation_unknown_file:' + path)
            continue
        if entry.get('ignored') or entry.get('history') or entry.get('check_only'):
            continue
        try:
            value = decode(body)
        except (ValueError, UnicodeError, TypeError, RecursionError):
            problems.append('installation_invalid:%s:$:syntax' % path)
            continue
        before = len(problems)
        secrets(value, path, secret_exists, problems)
        rule = entry.get('kind')
        if rule in ('project', 'role', 'team', 'service', 'connector', 'schedule'):
            if not IDENT.fullmatch(Path(path).stem):
                problems.append('installation_invalid:%s:id:identifier' % path)
            if isinstance(value, dict) and 'id' in value and value['id'] != Path(path).stem:
                problems.append('installation_invalid:%s:id:path_mismatch' % path)
        if rule in declared['definitions']:
            check(value, rule, declared['definitions'], path, '$', problems)
        if rule == 'workflow':
            errors = WF.definition_problems(value, resolve)
            problems += ['installation_invalid:%s:definition:%s' % (path, error) for error in errors]
            if not errors and value['id'] != Path(path).stem:
                problems.append('installation_invalid:%s:id:path_mismatch' % path)
        if len(problems) == before:
            config[path] = value
    if I.SETTINGS_FILE not in files:
        problems.append('installation_invalid:%s:$:missing' % I.SETTINGS_FILE)
    settings = config.get(I.SETTINGS_FILE, {})
    if 'space' in settings:
        class Reader:
            def space(self):
                return settings['space']
        try:
            organ('control_space_config').read(installation=Reader())
        except Exception as error:
            problems.append(('installation_invalid:%s:space:' % I.SETTINGS_FILE) + getattr(error, 'code', 'schema'))
    records = {path: body for path, body in files.items() if path.startswith('records/') and path != 'records/digests.json'}
    if records or 'records/digests.json' in files:
        try:
            inventory = decode(files['records/digests.json'])
            actual = {path: 'sha256:' + hashlib.sha256(body).hexdigest() for path, body in records.items()}
            if inventory != actual:
                raise ValueError('digest_list')
        except (KeyError, ValueError, UnicodeError):
            problems.append('installation_invalid:records/digests.json:$:digest_list')
    for path, value in config.items():
        if path.startswith('projects/'):
            if value.get('account') not in settings.get('accounts', {}) and value.get('account') is not None:
                problems.append('installation_invalid:%s:account:unknown_reference' % path)
            for kind, binding in value.get('workflows', {}).items():
                if 'workflows/%s.json' % binding['workflow'] not in config and binding['workflow'] != 'code':
                    problems.append('installation_invalid:%s:workflows.%s:unknown_reference' % (path, kind))
        elif path.startswith('connectors/'):
            if set(value.get('allowed_tools', [])) - set(value.get('tools', [])):
                problems.append('installation_invalid:%s:allowed_tools:unknown_reference' % path)
            if value.get('transport', 'stdio') != 'stdio' or any('://' in arg for arg in value.get('args', [])):
                problems.append('installation_invalid:%s:transport:outside_service_required' % path)
        elif path.startswith('services/') and path.endswith('.yaml'):
            for field, suffix in (('openapi', '.openapi.json'), ('tools_snapshot', '.tools.json')):
                if field in value and ('services/' + value[field] not in files
                                      or value[field] != Path(path).stem + suffix):
                    problems.append('installation_invalid:%s:%s:unknown_reference' % (path, field))
        elif path.endswith('.layout.json'):
            definition = config.get(path[:-len('.layout.json')] + '.json')
            errors = WF.layout_problems(value, definition) if definition else ['missing_definition']
            problems += ['installation_invalid:%s:layout:%s' % (path, error) for error in errors]
        elif path.startswith('teams/'):
            for role in value.get('roles', []):
                if 'roles/%s.yaml' % role not in config:
                    problems.append('installation_invalid:%s:roles:unknown_reference' % path)
    return config, sorted(set(problems))


def widening(previous, current):
    """Every schema-marked widening, with stable kind/key identities and plain descriptions."""
    found = []
    def add(path, key, kind):
        found.append({'kind': kind, 'key': path + ':' + key,
                      'description': '%s changes authority at %s, %s' % (kind, path, key)})
    declared = schema()
    for path, new in sorted(current.items()):
        old = previous.get(path, {})
        if old == new:
            continue
        entry = next(e for e in declared['paths'] if fnmatch.fnmatchcase(path, e['pattern']))
        kind = entry.get('kind')
        for key, mode in declared.get('widening', {}).get(kind, {}).items():
            a, b = old.get(key), new.get(key)
            if a == b:
                continue
            if mode == 'added':
                if isinstance(b, dict):
                    changed = [name for name, item in b.items() if name not in (a or {}) or a[name] != item]
                else:
                    changed = [item for item in (b or []) if item not in (a or [])]
                if changed:
                    add(path, key, kind)
            elif mode == 'removed':
                if any(item not in (b or []) for item in (a or [])):
                    add(path, key, kind)
            elif mode == 'changed' and b is not None:
                add(path, key, kind)
            elif mode == 'owner_role' and b is not None:
                if (a or {}).get('role_id') != b.get('role_id'):
                    add(path, key + '.role_id', kind)
            elif mode in ('account_authority', 'channel_authority'):
                for name, value in (b or {}).items():
                    held = (a or {}).get(name)
                    if held is None:
                        add(path, key + '.' + name, kind)
                        continue
                    fields = ('binary', 'provider', 'path', 'token') if mode == 'account_authority' else ('kind', 'chat', 'token')
                    limit = 'concurrency' if mode == 'account_authority' else 'inbound_file_cap'
                    profiles = value.get('profiles', {})
                    if (any(value.get(field) is not None and value.get(field) != held.get(field) for field in fields)
                            or any(held.get('profiles', {}).get(host) != profile for host, profile in profiles.items())
                            or value.get(limit, 0) > held.get(limit, 0)):
                        add(path, key + '.' + name, kind)
            elif mode == 'role_grants' and b is not None:
                prior = a or {}
                grants = {item['name'] for item in prior.get('native_tools', [])}
                servers = {(item['server'], item['revision']): item['tools'] for item in prior.get('mcp', [])}
                skills = {(item['skill'], item['revision']) for item in prior.get('skills', [])}
                extra_mcp = False
                for item in b.get('mcp', []):
                    held = servers.get((item['server'], item['revision']))
                    tools = item['tools']
                    extra_mcp |= held is None or (held != 'all' and (tools == 'all' or bool(set(tools) - set(held))))
                if (prior.get('engine') != b.get('engine')
                        or any(item['name'] not in grants for item in b.get('native_tools', [])) or extra_mcp
                        or any((item['skill'], item['revision']) not in skills for item in b.get('skills', []))):
                    add(path, key, kind)
            elif mode == 'team_grants' and b is not None:
                prior = (a or {}).get('roles', {})
                for role, entry in b.get('roles', {}).items():
                    held = prior.get(role, {})
                    if (role not in prior or any(item not in held.get(field, [])
                            for field in ('workers', 'engines', 'proposal_permissions') for item in entry.get(field, []))
                            or entry.get('capability_configuration') != held.get('capability_configuration')):
                        add(path, key + '.roles.' + role, kind)
        if path not in previous and kind in ('project', 'service', 'schedule'):
            add(path, '$', 'new_' + kind)
        if kind in ('schedule', 'tools_snapshot', 'openapi'):
            add(path, '$', kind)
        if kind == 'workflow':
            for name, node in new.get('nodes', {}).items():
                step = WF.step_kind(node) or {}
                if (step.get('outward') or step.get('paid')) and old.get('nodes', {}).get(name) != node:
                    add(path, 'nodes.' + name, 'workflow_step')
            for category, refs in new.get('references', {}).items():
                for name, ref in refs.items():
                    if old.get('references', {}).get(category, {}).get(name) != ref:
                        add(path, 'references.' + category + '.' + name, 'workflow_reference')
    return sorted(found, key=lambda item: (item['key'], item['kind']))
