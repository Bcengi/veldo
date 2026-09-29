"""Accepted role capability revisions and skill references (VELDO-0127).

The store owns every revision. Dispatches copy the accepted identity and digest, never
an account profile or a caller's replacement definition. Load modes are not defaults.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('agent_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MC = organ('control_mcp_catalog')
Refused = MC.Refused
KINDS = ('agent_configuration', 'agent_skill')
SAVE = 'save_agent_configuration'
MODES = ('always', 'when assigned')
CODEX_CAPABILITIES = {'shell', 'update_plan', 'apply_patch', 'view_image', 'multi_agent', 'sub_agents',
                      'web_search', 'tool_search', 'clock', 'request_user_input_async'}
FIELDS = {'role', 'engine', 'native_tools', 'mcp', 'skills', 'instructions', 'settings'}


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def identity(domain, repository, kind, name, revision=None):
    key = hashlib.sha256(('/'.join((domain, repository, kind, name))).encode()).hexdigest()
    return kind + ':' + key + (':head' if revision is None else ':' + str(revision))


def path_ok(value):
    return (isinstance(value, str) and bool(value) and not Path(value).is_absolute()
            and '..' not in Path(value).parts)


def names(items):
    return isinstance(items, list) and len(set(items)) == len(items) and all(MC.identifier(i) for i in items)


def validate(definition, kind=KINDS[0]):
    if not isinstance(definition, dict) or MC.credential_literal(definition):
        raise Refused('invalid_input:agent_configuration')
    if kind == KINDS[1]:
        if (set(definition) != {'skill', 'source', 'path'} or not MC.identifier(definition['skill'])
                or definition['source'] not in ('project', 'factory') or not path_ok(definition['path'])):
            raise Refused('invalid_input:agent_skill')
        return
    if (set(definition) != FIELDS or not MC.identifier(definition['role'])
            or definition['engine'] not in ('claude_code', 'codex')
            or not isinstance(definition['settings'], dict)):
        raise Refused('invalid_input:agent_configuration')
    for field, keys, key in (('native_tools', {'name', 'load'}, 'name'),
                             ('mcp', {'server', 'revision', 'tools', 'load'}, 'server'),
                             ('skills', {'skill', 'revision', 'load'}, 'skill'),
                             ('instructions', {'source', 'path', 'load'}, 'path')):
        items = definition[field]
        if not isinstance(items, list):
            raise Refused('invalid_input:agent_' + field)
        seen = set()
        for item in items:
            if not isinstance(item, dict) or set(item) != keys or item['load'] not in MODES:
                raise Refused('invalid_input:agent_' + field)
            name = (item.get('source'), item[key]) if field == 'instructions' else item[key]
            if name in seen:
                raise Refused('invalid_input:agent_' + field)
            seen.add(name)
            if field == 'instructions':
                valid = item['source'] in ('project', 'factory') and path_ok(item['path'])
            else:
                valid = MC.identifier(item[key])
            if field == 'native_tools' and definition['engine'] == 'codex':
                valid = valid and item[key] in CODEX_CAPABILITIES
            if 'revision' in keys:
                valid = valid and type(item['revision']) is int and item['revision'] > 0
            if 'tools' in keys:
                valid = valid and (item['tools'] == 'all' or names(item['tools']))
            if not valid:
                raise Refused('invalid_input:agent_' + field)
    if definition['engine'] == 'codex':
        codex_grants(definition)


def codex_grants(definition):
    """Refuse grants the qualified model cannot deliver, including deferred grants."""
    model = definition['settings'].get('model')
    if not model:
        return
    engine = organ('control_engine_codex')
    catalog = engine.load_qualification()['model_catalog']
    entry = next((m for m in catalog['models'] if m['slug'] == model), None)
    if entry is None:
        raise Refused('unsupported_configuration:codex_model:' + model)
    grants = {i['name'] for i in definition['native_tools']}
    for name, experimental in (('clock', 'clock'), ('request_user_input_async', 'send_user_message_async')):
        if name in grants and experimental not in entry['experimental_supported_tools']:
            raise Refused('unsupported_configuration:codex_tool:' + model + ':' + name)
    # In 0.154 Code Mode omits the search tool itself. With MCP, either mode
    # defers selected definitions, violating the role's exact launch set.
    if 'tool_search' in grants and (entry.get('tool_mode') == 'code_mode_only' or definition['mcp']):
        raise Refused('unsupported_configuration:codex_tool:' + model + ':tool_search')


def read(conn, domain, repository, role, revision=None, kind=KINDS[0]):
    if revision is None:
        head = MC.entity(conn, identity(domain, repository, kind, role))
        revision = head['data']['revision'] if head else 0
    row = MC.entity(conn, identity(domain, repository, kind, role, revision))
    if row is None or row['kind'] != kind:
        raise Refused('missing_evidence:agent_revision')
    data = row['data']
    if digest({k: v for k, v in data.items() if k != 'digest'}) != data.get('digest'):
        raise Refused('missing_evidence:agent_digest')
    return data


def transition(conn, params, before):
    try:
        MC.owner(conn, params['principal'], params['repository'], time.time())
    except MC.Refused:
        raise Refused('unauthorized:agent_owner') from None
    kind, definition = params['kind'], params['definition']
    validate(definition, kind)
    domain, repository, base = params['domain'], params['repository'], params['base']
    key = 'role' if kind == KINDS[0] else 'skill'
    name = definition[key]
    hid = identity(domain, repository, kind, name)
    head = MC.entity(conn, hid)
    if base != (head['data']['revision'] if head else 0):
        raise Refused('stale_version:agent_configuration')
    previous = read(conn, domain, repository, name, base, kind)['digest'] if base else None
    if kind == KINDS[0]:
        for item in definition['mcp']:
            row = MC.entity(conn, MC.revision_id(domain, item['server'], item['revision']))
            if row is None or row['kind'] != MC.KIND:
                raise Refused('missing_evidence:mcp_server')
        for item in definition['skills']:
            read(conn, domain, repository, item['skill'], item['revision'], KINDS[1])
    rid = identity(domain, repository, kind, name, base + 1)
    if MC.entity(conn, rid) is not None:
        raise Refused('stale_version:immutable_agent_configuration')
    data = dict(definition, revision=base + 1, previous=previous)
    data['digest'] = digest(data)
    return {rid: {'kind': kind, 'data': data},
            hid: {'kind': kind + '_head', 'data': {key: name, 'revision': base + 1}}}


class Configurations:
    def __init__(self, store, conn, *, domain, repository, signer, sign, generation=1, observe=None):
        self.S, self.conn, self.domain, self.repository = store, conn, domain, repository
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        store.declare_owners(conn, 'agent_configuration',
                             kinds={k: (SAVE,) for kind in KINDS for k in (kind, kind + '_head')}, module=__file__)
        conn.command_registry[SAVE] = {'transaction_transition': transition, 'writes': MC.WRITES}

    def save(self, definition, *, principal, base, command_id, kind=KINDS[0]):
        about = dict(operation=SAVE, actor=principal, domain=self.domain, repository=self.repository)
        try:
            if kind not in KINDS or type(base) is not int or base < 0:
                raise Refused('invalid_input:agent_configuration')
            validate(definition, kind)
            name = definition['role' if kind == KINDS[0] else 'skill']
            hid = identity(self.domain, self.repository, kind, name)
            rid = identity(self.domain, self.repository, kind, name, base + 1)
            command = dict(command_id=command_id, principal=principal, operation=SAVE,
                           parameters=dict(definition=definition, base=base, kind=kind, domain=self.domain,
                                           repository=self.repository, principal=principal),
                           expected_versions={hid: base, rid: 0}, artifact_digests=[], nonce=command_id)
            self.S.execute(self.conn, command, self.signer, self.sign, self.generation)
            result = read(self.conn, self.domain, self.repository, name, base + 1, kind)
        except (Refused, self.S.StoreRefused) as error:
            self.observe(dict(about, outcome='refused', refusal=error.code))
            raise Refused(error.code) from None
        self.observe(dict(about, outcome='saved', role=name, revision=result['revision'], digest=result['digest']))
        return result


def bind(conn, domain, repository, configuration):
    """Resolve a role selector once, at dispatch preparation. Existing unbound runs stay unbound."""
    configuration = json.loads(json.dumps(configuration))
    selector = configuration.get('role')
    if selector is None:
        return configuration
    if set(configuration) - {'role', 'revision'} or not MC.identifier(selector):
        raise Refused('invalid_input:agent_selector')
    accepted = read(conn, domain, repository, selector, configuration.get('revision'))
    revision = dict(accepted, native_tools=[i['name'] for i in accepted['native_tools'] if i['load'] == 'always'])
    return {'role_revision': revision,
            'mcp': [{k: i[k] for k in ('server', 'revision')} for i in accepted['mcp'] if i['load'] == 'always']}


def verify_binding(conn, domain, repository, revision):
    if not revision or 'digest' not in revision:
        return
    expected = bind(conn, domain, repository, {'role': revision['role'], 'revision': revision['revision']})
    if expected['role_revision'] != revision:
        raise Refused('stale_version:agent_binding')
