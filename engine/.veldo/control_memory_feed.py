"""Every conversation turn fed to claude-mem's session history, from its redacted execution record (VELDO-0187).

claude-mem captures a session from Claude Code hooks, which VELDO-0155's baseline switches off for every run. So the
factory feeds the same store itself, through the requests those hooks send claude-mem's worker, and claude-mem stays
the one writer of its own store: nothing here opens its database.

THE QUALIFICATION RECORD (AC1). `runtime/claude-mem-qualification.json` beside this module lists each qualified
claude-mem version: the digest of each hook script (hooks/hooks.json and every file its commands name under the
plugin root, through the variable a command assigns the root to), every request those hooks send the worker (each
user prompt, which also starts the session, each tool observation, the summary request and the session's
completion) with its method, path and fields, the version request the hooks ask the worker, and the worker's
loopback address. `qualify(code)` reads them from the version's own hook code: a hook command names one bundle and
a subcommand of it (session-init, observation, summarize, session-complete); the bundle's handler table names each
subcommand's handler; the handler's one call of the request wrapper with a literal `/api/...` path is the request.
Anything not found exactly once is refused by name, never guessed. `python3 control_memory_feed.py qualify <plugin
directory>` writes the entry into the record. Setup (control_factory_setup_memory) reads the installed version
from VELDO-0182's claude-mem part and writes this host's feed setting under the state root (`setup`): qualified,
with the worker's address (the data directory's settings.json, else the version's own default), or refused by
name: a version the record does not list, or whose hook scripts differ from it
(missing_evidence:claude_mem_version:<v>), a worker address that is not a loopback address
(invalid_input:claude_mem:not_loopback). A refused setting records every turn not captured by that name, and
nothing is sent.

THE FEED (AC2, AC3). At each turn's end, whatever its outcome (control_conversation.Conversations.ended), the turn
as its redacted execution record keeps it (control_conversation.turn_from_record, never the held session) becomes
one feed: the owner's message as the prompt (the conversation's first prompt starts its session), each tool call
with its input and result as an observation, and the reply with the summary request, in the record's order, under
the conversation's one claude-mem session (its id derived from the conversation), so turns on any account or engine
join it. The feed is kept pending under the conversation's directory (`claude-mem/pending/<turn>.json`) and sent in
turn order; each request sent is kept in the conversation's feed log (`claude-mem/feed.jsonl`) with its digest and
the worker's answer. A conversation's close sends the session's completion after every pending turn.

Before anything is sent, each pass asks the worker its version (the qualified version request). A worker that does
not answer, or answers 5xx, 408 or 429, leaves the feed pending (unavailable_service:claude_mem_worker), never
dropped; the next turn's end or the next loop pass sends it, in order. A worker running another version than the
setting's gets nothing: the feeds stay pending and each pending turn is recorded not captured
(missing_evidence:claude_mem_version:<running version>) until setup runs again. Any other answer outside 2xx is the
worker's refusal of that feed: the turn is recorded not captured (invalid_input:claude_mem_worker:<status>), the
feed is moved to `claude-mem/refused/` and the next pending feed is sent. A feed this module itself refuses (an
address that is not loopback, a paid-API name) is moved there too, never deleted. The turn record shows each
capture state (`claude_mem`: pending, captured, not captured with its reason).

Only the qualified requests are sent, only to a loopback address, with no header but the content type, never
following a redirect, and never with a field VELDO-0183 AC2 refuses as a paid-API name. Observations name the
conversation, turn, session, request kinds and digests, answers' status and capture states; never turn content.
"""
import hashlib
import importlib.util
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request

SCHEMA = 'veldo.claude_mem_feed/v1'
RECORD_SCHEMA = 'veldo.claude_mem_qualification/v1'
SETTING_SCHEMA = 'veldo.claude_mem_feed_setting/v1'
QUALIFICATION = 'runtime/claude-mem-qualification.json'
SETTING = os.path.join('memory', 'claude-mem-feed.json')
DIRECTORY = 'claude-mem'
REFUSED_PLACE = 'refused'
# The closed conversation's completion feed: after every turn's, by name.
CLOSING = '99999999-close.json'
KINDS = ('prompt', 'observation', 'summary', 'complete')
# The hook event each request kind is sent from and the bundle subcommand its hook command names, as claude-mem's
# hooks.json registers its hooks.
EVENTS = {'UserPromptSubmit': ('prompt', 'session-init'), 'PostToolUse': ('observation', 'observation'),
          'Stop': ('summary', 'summarize'), 'SessionEnd': ('complete', 'session-complete')}
# The request claude-mem's hooks ask the worker its version with, and the field of its answer that carries it.
VERSION, VERSION_PATH, VERSION_ANSWER = 'version', '/api/version', 'version'
# What each field a hook sends carries, by the name the hook gives it; a field not named here is not qualified.
VALUES = {'contentSessionId': 'session', 'claudeSessionId': 'session', 'session_id': 'session', 'sessionId': 'session',
          'project': 'project', 'cwd': 'cwd', 'prompt': 'prompt', 'userPrompt': 'prompt',
          'tool_name': 'tool_name', 'toolName': 'tool_name', 'tool_input': 'tool_input', 'toolInput': 'tool_input',
          'tool_response': 'tool_response', 'toolResponse': 'tool_response', 'tool_output': 'tool_response',
          'last_assistant_message': 'reply', 'lastAssistantMessage': 'reply', 'prompt_number': 'turn',
          'promptNumber': 'turn'}
NOT_LOOPBACK = 'invalid_input:claude_mem:not_loopback'
UNAVAILABLE = 'unavailable_service:claude_mem_worker'
UNLISTED = 'missing_evidence:claude_mem_version:%s'
WORKER_REFUSED = 'invalid_input:claude_mem_worker:%d'
NO_REQUEST = 'missing_evidence:claude_mem_request:%s'
AMBIGUOUS = 'missing_evidence:claude_mem_request:%s:ambiguous'
# The answers a worker that cannot take a request now gives: the feed stays pending.
LATER = (408, 429)
NO_RECORD = 'missing_evidence:execution_record'
PROJECT = 'veldo-conversations'
TIMEOUT = 5


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _organ(name):
    spec = importlib.util.spec_from_file_location('memory_feed_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_PAID = []


def paid_names():
    """VELDO-0183 AC2's paid-API and login names (control_mcp_catalog.paid_api_names)."""
    if not _PAID:
        _PAID.append(_organ('control_mcp_catalog').paid_api_names())
    return _PAID[0]


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def record_path():
    return Path(__file__).parent / QUALIFICATION


def load_record(path=None):
    path = Path(path or record_path())
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        return {'schema': RECORD_SCHEMA, 'versions': {}}
    if record.get('schema') != RECORD_SCHEMA or not isinstance(record.get('versions'), dict):
        return {'schema': RECORD_SCHEMA, 'versions': {}}
    return record


def loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


# QUALIFICATION: read from the version's own hook code.

ASSIGNED = re.compile(r'(?<![\w$])([A-Za-z_][A-Za-z0-9_]*)="?\$\{?CLAUDE_PLUGIN_ROOT\}?"?')
SUBCOMMAND = re.compile(r'["\']?\s+hook\s+[A-Za-z0-9_\-]+\s+([A-Za-z0-9_\-]+)')
CALL = re.compile(r'(?<![\w$.])([A-Za-z_$][\w$]*)\(\s*(["\'])(/api/[A-Za-z0-9_/\-]+)\2\s*(,\s*\{)?')
METHOD = re.compile(r'method\s*[:]\s*[\'"]([A-Z]+)[\'"]')
BODY = re.compile(r'body\s*[:]\s*JSON\.stringify\(\{([^{}]*)\}\)')
HOST_DEFAULT = re.compile(r'CLAUDE_MEM_WORKER_HOST["\']?\s*(?:[:]|\|\|)\s*[\'"]([^\'"]+)[\'"]')
PORT_DEFAULT = re.compile(r'CLAUDE_MEM_WORKER_PORT["\']?\s*(?:[:]|\|\|)\s*[\'"]?([0-9]+)')
NAME = r'[A-Za-z_$][\w$]*'


def _inside(code, relative):
    """The file `relative` names under the plugin root, None when it is absent; refused when it leaves the root."""
    path = os.path.realpath(os.path.join(code, relative))
    if os.path.commonpath((path, os.path.realpath(code))) != os.path.realpath(code):
        raise Refused('missing_evidence:claude_mem_hooks', relative)
    return path if os.path.isfile(path) else None


def _scripts(command):
    """[(the file a hook command names under the plugin root, the bundle subcommand it is run with or None)]: the
    root is CLAUDE_PLUGIN_ROOT or a variable the command assigns it to (`_R="${CLAUDE_PLUGIN_ROOT}"`)."""
    names = ['CLAUDE_PLUGIN_ROOT'] + ASSIGNED.findall(command)
    named = re.compile(r'\$\{?(?:%s)\}?/([^\s"\'`;]+)' % '|'.join(re.escape(name) for name in names))
    found = []
    for match in named.finditer(command):
        ran = SUBCOMMAND.match(command, match.end())
        found.append((match.group(1), ran.group(1) if ran else None))
    return found


def _quoted(source, start):
    """The index just past the string or template literal that opens at `start`; None when it never closes."""
    quote, index = source[start], start + 1
    while index < len(source):
        char = source[index]
        if char == '\\':
            index += 2
        elif char == quote:
            return index + 1
        elif quote == '`' and source.startswith('${', index):
            index = _extent(source, index + 1)
            if index is None:
                return None
        else:
            index += 1
    return None


def _extent(source, start):
    """The index just past the brace that closes the one at `start`, string and template literals skipped; None
    when it never closes."""
    depth, index = 0, start
    while index < len(source):
        char = source[index]
        if char in '"\'`':
            index = _quoted(source, index)
            if index is None:
                return None
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return None


def _fields(body):
    names = []
    for part in body.split(','):
        name = part.split(':', 1)[0].strip().strip('\'"')
        if name:
            names.append(name)
    return names


def _key(subcommand):
    return re.compile(r'(?:^|,)\s*["\']?%s["\']?\s*[:]\s*(%s)\s*(?=,|$)' % (re.escape(subcommand), NAME))


def _handlers(source):
    """{subcommand: its handler's name} from the bundle's handler table: the one object literal that names every
    subcommand of EVENTS; None when there is none or more than one."""
    wanted = [subcommand for _kind, subcommand in EVENTS.values()]
    tables = []
    for match in re.finditer(r'["\']%s["\']\s*[:]' % re.escape(wanted[0]), source):
        low, high = source.rfind('{', 0, match.start()), source.find('}', match.end())
        if low < 0 or high < 0 or '}' in source[low:match.start()] or '{' in source[match.end():high]:
            continue
        inner = source[low + 1:high]
        named = {subcommand: _key(subcommand).findall(inner) for subcommand in wanted}
        if all(len(names) == 1 for names in named.values()):
            tables.append({subcommand: names[0] for subcommand, names in named.items()})
    return tables[0] if len(tables) == 1 else None


def _calls(text):
    """Every call of a request wrapper in `text` whose first argument is a literal `/api/...` path:
    [(wrapper, path, method, fields)]; the method is the wrapper's own default, GET, when none is given; the fields
    are None for a call with no body and False for a body that could not be read."""
    found = []
    for match in CALL.finditer(text):
        options, fields = '', None
        if match.group(4):
            end = _extent(text, match.end() - 1)
            options = text[match.end() - 1:end] if end is not None else None
        if options is None:
            fields = False
        else:
            body = BODY.search(options)
            fields = _fields(body.group(1)) if body else False if 'body' in options else None
        method = METHOD.search(options or '')
        found.append((match.group(1), match.group(3), method.group(1) if method else 'GET', fields))
    return found


def _request(source, handlers, kind, subcommand):
    """The one request the subcommand's handler sends: its one call of the request wrapper with a literal path,
    tied to the handler the bundle's table names; refused by name when any step of that tie is not unique."""
    name = handlers[subcommand]
    defined = [m for m in re.finditer(r'(?<![\w$.])%s\s*=\s*\{' % re.escape(name), source)]
    if len(defined) != 1:
        raise Refused(AMBIGUOUS % kind, '%s: %d definitions of its handler' % (subcommand, len(defined)))
    end = _extent(source, defined[0].end() - 1)
    if end is None:
        raise Refused(AMBIGUOUS % kind, subcommand + ': its handler does not close')
    text = source[defined[0].start():end]
    calls = _calls(text)
    if not calls:
        raise Refused(NO_REQUEST % kind, subcommand)
    if len(calls) != 1 or not isinstance(calls[0][3], list):
        raise Refused(AMBIGUOUS % kind, '%s: %d requests, or one whose body could not be read'
                      % (subcommand, len(calls)))
    wrapper, path, method, fields = calls[0]
    # What else the handler sends through the same wrapper, by a path it computes: read and recorded, never sent.
    computed = re.findall(r'(?<![\w$.])%s\(\s*`([^`]*)`' % re.escape(wrapper), text)
    return wrapper, {'method': method, 'path': path, 'fields': fields, 'subcommand': subcommand,
                     'handler': digest(text.encode()), 'not_sent': computed}


def qualify(code):
    """The qualification entry of the claude-mem plugin at `code`: its version, its hook scripts' digests, the
    request each hook sends its worker, the version request, and the worker's default address; refused by name
    when a request is missing or not uniquely tied to its hook, a field is unknown or a paid-API name, or the
    address is not loopback."""
    code = os.path.realpath(str(code))
    try:
        version = json.loads(Path(code, 'package.json').read_text())['version']
        hooks_path = _inside(code, os.path.join('hooks', 'hooks.json'))
        hooks = json.loads(Path(hooks_path).read_text())['hooks']
        events = {event: [str(hook.get('command') or '') for group in groups or [] for hook in group.get('hooks') or []]
                  for event, groups in hooks.items()}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise Refused('missing_evidence:claude_mem_hooks', code) from None
    digests, sources = {'hooks/hooks.json': digest(Path(hooks_path).read_bytes())}, {}
    for event in sorted(events):
        for command in events[event]:
            for relative, _subcommand in _scripts(command):
                path = _inside(code, relative)
                if path is None:
                    digests[relative] = None
                    continue
                raw = Path(path).read_bytes()
                digests[relative] = digest(raw)
                sources[relative] = raw.decode(errors='replace')
    requests, wrappers, bundles = {}, set(), set()
    for event, (kind, subcommand) in EVENTS.items():
        named = [relative for command in events.get(event) or [] for relative, ran in _scripts(command)
                 if ran == subcommand]
        if not named or named[0] not in sources:
            raise Refused(NO_REQUEST % kind, event)
        if len(named) != 1:
            raise Refused(AMBIGUOUS % kind, '%s: %d hooks' % (event, len(named)))
        source = sources[named[0]]
        handlers = _handlers(source)
        if handlers is None:
            raise Refused(AMBIGUOUS % kind, named[0] + ': its handler table')
        wrapper, request = _request(source, handlers, kind, subcommand)
        wrappers.add(wrapper)
        bundles.add(named[0])
        for name in request['fields']:
            if name in paid_names():
                raise Refused('invalid_input:claude_mem:paid_api:' + name, kind)
            if name not in VALUES:
                raise Refused('missing_evidence:claude_mem_field:' + name, kind)
        requests[kind] = dict(request, event=event, script=named[0],
                              values={name: VALUES[name] for name in request['fields']})
    # The version request: the one call of the same wrapper, in the same bundle, that asks the worker its version.
    asked = [(relative, call) for relative in sorted(bundles) for call in _calls(sources[relative])
             if call[1] == VERSION_PATH and call[0] in wrappers]
    if not asked:
        raise Refused(NO_REQUEST % VERSION, VERSION_PATH)
    if len(asked) != 1 or len(wrappers) != 1 or asked[0][1][3] is not None:
        raise Refused(AMBIGUOUS % VERSION, VERSION_PATH)
    requests[VERSION] = {'method': asked[0][1][2], 'path': VERSION_PATH, 'fields': [], 'values': {},
                         'script': asked[0][0], 'answer': VERSION_ANSWER}
    hosts = {value for relative in sorted(bundles) for value in HOST_DEFAULT.findall(sources[relative])}
    ports = {int(value) for relative in sorted(bundles) for value in PORT_DEFAULT.findall(sources[relative])}
    if len(hosts) != 1 or len(ports) != 1:
        raise Refused('missing_evidence:claude_mem_address', code)
    host, port = hosts.pop(), ports.pop()
    if not loopback(host):
        raise Refused(NOT_LOOPBACK, host)
    return {'version': version, 'hooks': digests, 'requests': requests,
            'address': {'host': host, 'port': port, 'host_setting': 'CLAUDE_MEM_WORKER_HOST',
                        'port_setting': 'CLAUDE_MEM_WORKER_PORT'}}


def record_qualified(code, path=None):
    """Qualify the plugin at `code` and write its entry into the record at `path` (this module's by default)."""
    path = Path(path or record_path())
    record = load_record(path) if path.exists() else {'schema': RECORD_SCHEMA, 'versions': {}}
    entry = qualify(code)
    record.setdefault('note', 'Each claude-mem version VELDO-0187 qualifies: read from that version\'s own hook code '
                              'by control_memory_feed.qualify.')
    record['versions'][entry.pop('version')] = entry
    path.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    return record


# SETUP: this host's feed setting, from VELDO-0182's claude-mem part.

def setting_path(root):
    return Path(root) / SETTING


def _write_private(path, value):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name('.%s.%d.tmp' % (path.name, os.getpid()))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(value, out, sort_keys=True)
    os.replace(temporary, path)


def setup(root, definition, record=None):
    """Read the installed claude-mem version from the memory definition's claude-mem part and write this host's
    feed setting under `root`; returns it. A version the qualification record does not list, or whose hook scripts
    differ from the record's digests, is refused by name, as is a worker address that is not loopback."""
    part = ((definition or {}).get('parts') or {}).get('claude_mem')
    if not part:
        return None
    record = record if record is not None else load_record()
    code, data = part['code'], part['data']
    try:
        version = str(json.loads(Path(code, 'package.json').read_text())['version'])
    except (OSError, ValueError, KeyError, TypeError):
        version = 'unknown'
    entry = record['versions'].get(version)
    setting = {'schema': SETTING_SCHEMA, 'version': version, 'code': code, 'data': data,
               'qualification_digest': digest(entry) if entry else None, 'state': 'qualified', 'refusal': None,
               'address': None, 'requests': None}
    if entry is None:
        setting.update(state='refused', refusal=UNLISTED % version)
    else:
        try:
            if qualify(code)['hooks'] != entry['hooks']:
                raise Refused(UNLISTED % version)
        except Refused as error:
            setting.update(state='refused', refusal=UNLISTED % version
                           if not error.code.startswith('invalid_input') else error.code)
    if setting['state'] == 'qualified':
        address = dict(entry['address'])
        try:
            settings = json.loads(Path(data, 'settings.json').read_text())
        except (OSError, ValueError):
            settings = {}
        host = str(settings.get(address['host_setting']) or address['host'])
        port = settings.get(address['port_setting']) or address['port']
        setting['address'] = {'host': host, 'port': int(port)}
        setting['requests'] = entry['requests']
        if not loopback(host):
            setting.update(state='refused', refusal=NOT_LOOPBACK)
    _write_private(setting_path(root), setting)
    return setting


def read_setting(root):
    try:
        setting = json.loads(setting_path(root).read_text())
    except (OSError, ValueError):
        return None
    return setting if setting.get('schema') == SETTING_SCHEMA else None


# THE FEED.

def session_of(identity):
    """The conversation's one claude-mem session."""
    return 'veldo-conversation-' + hashlib.sha256(str(identity).encode()).hexdigest()[:32]


def _text(value):
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def _body(setting, kind, values):
    spec = setting['requests'][kind]
    given = {name: values.get(value) for name, value in spec['values'].items()}
    return {'kind': kind, 'method': spec['method'], 'path': spec['path'], 'body': given, 'digest': digest(given)}


def build(setting, turn, *, session, cwd, sequence):
    """The requests of one turn, in the record's order, from `turn` (control_conversation.turn_from_record over the
    redacted execution record): the prompt (which starts the session when the worker has none), each tool call's
    observation, and the summary request with the reply."""
    common = {'session': session, 'project': PROJECT, 'cwd': cwd, 'turn': sequence}
    found = [_body(setting, 'prompt', dict(common, prompt=turn.get('message') or ''))]
    for call in turn.get('calls') or []:
        found.append(_body(setting, 'observation', dict(common, tool_name=call.get('name'),
                                                        tool_input=call.get('input'),
                                                        tool_response=_text(call.get('result')))))
    found.append(_body(setting, 'summary', dict(common, reply=turn.get('reply') or '')))
    return found


def completion(setting, *, session, cwd):
    """The request that completes the conversation's session, sent at its close."""
    return [_body(setting, 'complete', {'session': session, 'project': PROJECT, 'cwd': cwd})]


def version_request(setting):
    """The qualified request that asks the worker its version; None when the setting carries none."""
    spec = (setting.get('requests') or {}).get(VERSION)
    if not spec:
        return None
    return {'kind': VERSION, 'method': spec['method'], 'path': spec['path'], 'body': None, 'digest': digest(None),
            'answer': spec.get('answer') or VERSION_ANSWER}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is never followed: the answer is the worker's own, from the loopback address asked."""

    def redirect_request(self, *args, **kwargs):
        return None


def send(setting, request, opener=None):
    """One request to the worker at the setting's loopback address: (status, answer). Raises Refused for an address
    that is not loopback or a paid-API field, and OSError when the worker does not answer."""
    address = setting.get('address') or {}
    if not loopback(str(address.get('host'))):
        raise Refused(NOT_LOOPBACK, str(address.get('host')))
    named = [name for name in request.get('body') or {} if name in paid_names()]
    if named:
        raise Refused('invalid_input:claude_mem:paid_api:' + named[0])
    host = address['host'] if ':' not in address['host'] else '[%s]' % address['host']
    url = 'http://%s:%d%s' % (host, int(address['port']), request['path'])
    if request.get('body') is None:
        message = urllib.request.Request(url, method=request['method'])
    else:
        message = urllib.request.Request(url, data=json.dumps(request['body']).encode(), method=request['method'],
                                         headers={'Content-Type': 'application/json'})
    handler = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with (opener or handler.open)(message, timeout=TIMEOUT) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        raw, status = error.read(), error.code
    try:
        answer = json.loads(raw.decode() or 'null')
    except ValueError:
        answer = raw.decode(errors='replace')[:2000]
    return status, answer


class Feed:
    """One conversation directory's feeds: the pending feeds, the refused feeds, the feed log and the session."""

    def __init__(self, root, observe=None, opener=None):
        self.root = root
        self.observe = observe or (lambda event: None)
        self.opener = opener

    def setting(self):
        return read_setting(self.root)

    @staticmethod
    def place(directory):
        return Path(directory) / DIRECTORY

    def session(self, directory, identity):
        """The conversation's one claude-mem session, kept under its directory; its first prompt starts it."""
        path = self.place(directory) / 'session.json'
        if path.exists():
            return json.loads(path.read_text())['session']
        session = session_of(identity)
        _write_private(path, {'conversation': identity, 'session': session})
        return session

    def pending(self, directory):
        place = self.place(directory) / 'pending'
        return sorted(place.glob('*.json')) if place.is_dir() else []

    def log(self, directory, entry):
        path = self.place(directory) / 'feed.jsonl'
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as out:
            out.write(json.dumps(entry, sort_keys=True) + '\n')

    def refuse(self, directory, path, feed, reason):
        """Move a feed that will not be sent to the conversation's refused feeds, with the reason; never deleted."""
        place = self.place(directory) / REFUSED_PLACE
        _write_private(place / path.name, dict(feed, refused=reason, refused_at=time.time()))
        path.unlink()

    def turn(self, record, sequence, dispatch_id, turn, committed):
        """Keep one ended turn's feed pending; returns its capture state (pending, or not captured with a reason)."""
        setting = self.setting()
        identity, directory = record['id'], record['directory']
        base = {'schema': SCHEMA, 'operation': 'claude_mem_feed', 'conversation': identity, 'sequence': sequence,
                'dispatch_id': dispatch_id, 'execution_record': (committed or {}).get('digest'),
                'qualification': (setting or {}).get('qualification_digest')}
        if setting is None:
            return None
        if setting['state'] != 'qualified':
            state = {'state': 'not_captured', 'reason': setting['refusal']}
            self.observe(dict(base, capture=state['state'], reason=state['reason'], requests=[]))
            return state
        if turn is None:
            state = {'state': 'not_captured', 'reason': NO_RECORD}
            self.observe(dict(base, capture=state['state'], reason=state['reason'], requests=[]))
            return state
        session = self.session(directory, identity)
        cwd = os.path.join(directory, 'workspace')
        requests = build(setting, turn, session=session, cwd=cwd, sequence=sequence)
        feed = {'schema': SCHEMA, 'conversation': identity, 'sequence': sequence, 'dispatch_id': dispatch_id,
                'session': session, 'cwd': cwd, 'turn': turn, 'execution_record': base['execution_record'],
                'qualification': base['qualification'], 'requests': requests, 'sent': 0, 'late': False,
                'held': None, 'at': time.time()}
        _write_private(self.place(directory) / 'pending' / ('%08d.json' % sequence), feed)
        self.observe(dict(base, session=session, capture='pending', reason=None,
                          requests=[{'kind': r['kind'], 'digest': r['digest']} for r in requests]))
        return {'state': 'pending', 'reason': None, 'session': session}

    def close(self, record):
        """The closed conversation's last feed, kept pending after every turn's: its session's completion. Written
        once, and only for a conversation whose session a qualified feed started; returns whether it was."""
        setting = self.setting()
        identity, directory = record['id'], record.get('directory')
        path = self.place(directory) / 'session.json' if directory else None
        if setting is None or setting['state'] != 'qualified' or path is None or not path.exists():
            return False
        kept = json.loads(path.read_text())
        if kept.get('closed'):
            return False
        cwd = os.path.join(directory, 'workspace')
        requests = completion(setting, session=kept['session'], cwd=cwd)
        feed = {'schema': SCHEMA, 'conversation': identity, 'sequence': None, 'dispatch_id': None,
                'session': kept['session'], 'cwd': cwd, 'turn': None, 'execution_record': None,
                'qualification': setting['qualification_digest'], 'requests': requests, 'sent': 0, 'late': False,
                'held': None, 'at': time.time()}
        _write_private(self.place(directory) / 'pending' / CLOSING, feed)
        _write_private(path, dict(kept, closed=True))
        self.observe({'schema': SCHEMA, 'operation': 'claude_mem_feed', 'conversation': identity, 'sequence': None,
                      'session': kept['session'], 'qualification': setting['qualification_digest'],
                      'capture': 'pending', 'reason': None,
                      'requests': [{'kind': r['kind'], 'digest': r['digest']} for r in requests]})
        return True

    def _current(self, setting, path, feed):
        """The feed's requests under the setting in force: a feed kept under another qualification is built again
        from the turn it keeps, so nothing is sent by an interface that is no longer the qualified one."""
        if feed.get('qualification') == setting['qualification_digest']:
            return feed
        if feed.get('sequence') is None:
            requests = completion(setting, session=feed['session'], cwd=feed.get('cwd'))
        else:
            requests = build(setting, feed['turn'], session=feed['session'], cwd=feed.get('cwd'),
                             sequence=feed['sequence'])
        feed.update(requests=requests, qualification=setting['qualification_digest'],
                    sent=min(feed['sent'], len(requests)))
        _write_private(path, feed)
        return feed

    def flush(self, record):
        """Send the conversation's pending feeds in turn order, the worker's version asked first; stops at the first
        request the worker does not take now, and sends nothing to a worker of another version than the setting's.
        Returns [(sequence, capture state)] for each turn whose state changed."""
        setting = self.setting()
        identity, directory = record['id'], record['directory']
        changed = []
        if setting is None or setting['state'] != 'qualified':
            return changed
        asked = version_request(setting)
        if asked is None:
            return changed
        checked = False
        waiting = self.pending(directory)
        for path in waiting:
            feed = self._current(setting, path, json.loads(path.read_text()))
            turn = feed['sequence'] is not None
            base = {'schema': SCHEMA, 'operation': 'claude_mem_feed', 'conversation': identity,
                    'sequence': feed['sequence'], 'dispatch_id': feed['dispatch_id'], 'session': feed['session'],
                    'execution_record': feed['execution_record'], 'qualification': feed['qualification']}
            while feed['sent'] < len(feed['requests']):
                request = feed['requests'][feed['sent']] if checked else asked
                try:
                    status, answer = send(setting, request, self.opener)
                except Refused as error:
                    self.observe(dict(base, kind=request['kind'], digest=request['digest'], capture='not_captured',
                                      reason=error.code))
                    self.refuse(directory, path, feed, error.code)
                    if turn:
                        changed.append((feed['sequence'], {'state': 'not_captured', 'reason': error.code}))
                    break
                except OSError as error:
                    self.log(directory, {'conversation': identity, 'sequence': feed['sequence'],
                                         'session': feed['session'], 'kind': request['kind'],
                                         'path': request['path'], 'digest': request['digest'], 'request': request,
                                         'answer': None, 'error': UNAVAILABLE, 'detail': type(error).__name__,
                                         'at': time.time()})
                    self.observe(dict(base, kind=request['kind'], digest=request['digest'], capture='pending',
                                      reason=UNAVAILABLE))
                    self._later(path, feed, changed)
                    return changed
                ok = 200 <= status < 300
                self.log(directory, {'conversation': identity, 'sequence': feed['sequence'],
                                     'session': feed['session'], 'kind': request['kind'], 'path': request['path'],
                                     'digest': request['digest'], 'request': request, 'status': status,
                                     'answer': answer, 'at': time.time()})
                self.observe(dict(base, kind=request['kind'], digest=request['digest'], status=status,
                                  outcome='sent' if ok else 'refused'))
                if status >= 500 or status in LATER:
                    # The worker cannot take it now: pending, never dropped, and nothing later goes before it.
                    self._later(path, feed, changed)
                    return changed
                if not checked:
                    running = answer.get(asked['answer']) if ok and isinstance(answer, dict) else None
                    if running != setting['version']:
                        # Another version than the qualified one answers: nothing is sent until setup runs again.
                        reason = UNLISTED % (running if _named(running) else 'unknown')
                        for held_path in waiting:
                            held = feed if held_path == path else json.loads(held_path.read_text())
                            if held.get('held') == reason:
                                continue
                            held['held'] = reason
                            _write_private(held_path, held)
                            self.observe(dict(base, sequence=held['sequence'], dispatch_id=held['dispatch_id'],
                                              execution_record=held['execution_record'],
                                              capture='not_captured', reason=reason))
                            if held['sequence'] is not None:
                                changed.append((held['sequence'], {'state': 'not_captured', 'reason': reason}))
                        return changed
                    checked = True
                    continue
                if not ok:
                    # The worker answered and refused this feed: named, set aside, and the next feed goes on.
                    reason = WORKER_REFUSED % status
                    self.observe(dict(base, kind=request['kind'], digest=request['digest'], capture='not_captured',
                                      reason=reason))
                    self.refuse(directory, path, feed, reason)
                    if turn:
                        changed.append((feed['sequence'], {'state': 'not_captured', 'reason': reason}))
                    break
                feed['sent'] += 1
                _write_private(path, feed)
            else:
                kinds = {}
                for request in feed['requests']:
                    kinds[request['kind']] = kinds.get(request['kind'], 0) + 1
                path.unlink()
                state = {'state': 'captured', 'reason': None, 'session': feed['session'], 'requests': kinds,
                         'late': feed['late']}
                self.observe(dict(base, capture='captured' if turn else 'completed', requests=kinds,
                                  late=feed['late']))
                if turn:
                    changed.append((feed['sequence'], state))
        return changed

    @staticmethod
    def _later(path, feed, changed):
        """A feed the worker cannot take now stays pending; the first time, its turn's state says why."""
        if not feed['late']:
            feed['late'] = True
            _write_private(path, feed)
            if feed['sequence'] is not None:
                changed.append((feed['sequence'], {'state': 'pending', 'reason': UNAVAILABLE}))


def _named(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[A-Za-z0-9._+\-]{1,64}', value))


def metrics(turns):
    """Turns captured, pending and not captured by reason, requests sent by kind and feeds sent late, from the turn
    records' capture states."""
    found = {'captured': 0, 'pending': 0, 'not_captured': {}, 'requests': {}, 'late': 0}
    for turn in turns:
        state = turn.get('claude_mem') or {}
        if state.get('state') == 'captured':
            found['captured'] += 1
            found['late'] += int(bool(state.get('late')))
            for kind, count in (state.get('requests') or {}).items():
                found['requests'][kind] = found['requests'].get(kind, 0) + count
        elif state.get('state') == 'pending':
            found['pending'] += 1
        elif state.get('state') == 'not_captured':
            found['not_captured'][state.get('reason')] = found['not_captured'].get(state.get('reason'), 0) + 1
    return found


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog='control_memory_feed')
    subs = parser.add_subparsers(dest='action', required=True)
    given = subs.add_parser('qualify')
    given.add_argument('code')
    given.add_argument('--record')
    args = parser.parse_args(argv)
    try:
        record = record_qualified(args.code, args.record)
    except Refused as error:
        print(json.dumps({'outcome': 'refused', 'reason': error.code, 'detail': error.detail}))
        return 1
    print(json.dumps({'outcome': 'qualified', 'versions': sorted(record['versions'])}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
