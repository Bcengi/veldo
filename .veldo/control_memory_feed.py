"""Every conversation turn fed to claude-mem's session history, from its redacted execution record (VELDO-0187).

claude-mem captures a session from Claude Code hooks, which VELDO-0155's baseline switches off for every run. So the
factory feeds the same store itself, through the requests those hooks send claude-mem's worker, and claude-mem stays
the one writer of its own store: nothing here opens its database.

THE QUALIFICATION RECORD (AC1). `runtime/claude-mem-qualification.json` beside this module lists each qualified
claude-mem version: the digest of each hook script (hooks/hooks.json and every file its commands name under the
plugin root), every request those hooks send the worker (the session's start, each user prompt, each tool
observation and the end-of-session summary request) with its method, path and fields, and the worker's loopback
address. `qualify(code)` reads them from the version's own hook code; `python3 control_memory_feed.py qualify
<plugin directory>` writes them into the record. Setup (control_factory_setup_memory) reads the installed version
from VELDO-0182's claude-mem part and writes this host's feed setting under the state root (`setup`): qualified, with
the worker's address (the data directory's settings.json, else the version's own default), or refused by name: a
version the record does not list, or whose hook scripts differ from it (missing_evidence:claude_mem_version:<v>), a
worker address that is not a loopback address (invalid_input:claude_mem:not_loopback). A refused setting records
every turn not captured by that name, and nothing is sent.

THE FEED (AC2, AC3). At each turn's end, whatever its outcome (control_conversation.Conversations.ended), the turn
as its redacted execution record keeps it (control_conversation.turn_from_record, never the held session) becomes
one feed: the session's start when the conversation has none yet, the owner's message as the prompt, each tool call
with its input and result as an observation, and the reply with the summary request, in the record's order, under
the conversation's one claude-mem session (its id derived from the conversation), so turns on any account or engine
join it. The feed is kept pending under the conversation's directory (`claude-mem/pending/<turn>.json`) and sent in
turn order; each request sent is kept in the conversation's feed log (`claude-mem/feed.jsonl`) with its digest and
the worker's answer. A worker that does not answer leaves the feed pending (unavailable_service:claude_mem_worker),
never dropped; the next turn's end or the next loop pass sends it, in order. The turn record shows each capture
state (`claude_mem`: pending, captured, not captured with its reason).

Only the qualified requests are sent, only to a loopback address, with no header but the content type, and never
with a field VELDO-0183 AC2 refuses as a paid-API name. Observations name the conversation, turn, session, request
kinds and digests, answers' status and capture states; never turn content.
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
KINDS = ('start', 'prompt', 'observation', 'summary')
# The hook event each request kind is sent from, as claude-mem's hooks.json registers its hooks.
EVENTS = {'SessionStart': 'start', 'UserPromptSubmit': 'prompt', 'PostToolUse': 'observation', 'Stop': 'summary'}
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

FETCH = re.compile(r'fetch\(\s*`[^`]*?(/api/[A-Za-z0-9_/\-]+)`\s*,\s*\{\s*method[:]\s*[\'"]([A-Z]+)[\'"]')
BODY = re.compile(r'JSON\.stringify\(\{([^{}]*)\}\)')
HOST_DEFAULT = re.compile(r'(CLAUDE_MEM_WORKER_HOST)\s*\|\|\s*[\'"]([^\'"]+)[\'"]')
PORT_DEFAULT = re.compile(r'(CLAUDE_MEM_WORKER_PORT)\s*\|\|\s*[\'"]?([0-9]+)')
SCRIPT = re.compile(r'\$\{?CLAUDE_PLUGIN_ROOT\}?/([^\s"\'`]+)')


def _inside(code, relative):
    path = os.path.realpath(os.path.join(code, relative))
    if os.path.commonpath((path, os.path.realpath(code))) != os.path.realpath(code) or not os.path.isfile(path):
        raise Refused('missing_evidence:claude_mem_hooks', relative)
    return path


def _fields(body):
    names = []
    for part in body.split(','):
        name = part.split(':', 1)[0].strip().strip('\'"')
        if name:
            names.append(name)
    return names


def qualify(code):
    """The qualification entry of the claude-mem plugin at `code`: its version, its hook scripts' digests, the
    request each hook sends its worker, and the worker's default address; refused by name when a request kind is
    missing, a field is unknown or a paid-API name, or the address is not loopback."""
    code = os.path.realpath(str(code))
    try:
        version = json.loads(Path(code, 'package.json').read_text())['version']
        hooks_path = _inside(code, os.path.join('hooks', 'hooks.json'))
        hooks = json.loads(Path(hooks_path).read_text())['hooks']
    except (OSError, ValueError, KeyError, TypeError):
        raise Refused('missing_evidence:claude_mem_hooks', code) from None
    digests = {'hooks/hooks.json': digest(Path(hooks_path).read_bytes())}
    requests, host, port = {}, None, None
    for event, kind in EVENTS.items():
        found = []
        for group in hooks.get(event) or []:
            for hook in group.get('hooks') or []:
                for relative in SCRIPT.findall(hook.get('command') or ''):
                    source = Path(_inside(code, relative)).read_text()
                    digests[relative] = digest(source.encode())
                    for match in FETCH.finditer(source):
                        body = BODY.search(source, match.end())
                        found.append({'method': match.group(2), 'path': match.group(1),
                                      'fields': _fields(body.group(1)) if body else []})
                    host = host or next((m.group(2) for m in HOST_DEFAULT.finditer(source)), None)
                    port = port or next((int(m.group(2)) for m in PORT_DEFAULT.finditer(source)), None)
        if len(found) != 1:
            raise Refused('missing_evidence:claude_mem_request:' + kind, event)
        request = found[0]
        for name in request['fields']:
            if name in paid_names():
                raise Refused('invalid_input:claude_mem:paid_api:' + name, kind)
            if name not in VALUES:
                raise Refused('missing_evidence:claude_mem_field:' + name, kind)
        requests[kind] = dict(request, values={name: VALUES[name] for name in request['fields']})
    if host is None or port is None:
        raise Refused('missing_evidence:claude_mem_address', code)
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


def build(setting, turn, *, session, cwd, sequence, start):
    """The requests of one turn, in the record's order, from `turn` (control_conversation.turn_from_record over the
    redacted execution record): the session's start when `start`, the prompt, each tool call's observation, and the
    summary request with the reply."""
    def body(kind, values):
        spec = setting['requests'][kind]
        given = {name: values.get(value) for name, value in spec['values'].items()}
        return {'kind': kind, 'method': spec['method'], 'path': spec['path'], 'body': given, 'digest': digest(given)}
    common = {'session': session, 'project': PROJECT, 'cwd': cwd, 'turn': sequence}
    found = []
    if start:
        found.append(body('start', dict(common, prompt=turn.get('message'))))
    found.append(body('prompt', dict(common, prompt=turn.get('message') or '')))
    for call in turn.get('calls') or []:
        found.append(body('observation', dict(common, tool_name=call.get('name'), tool_input=call.get('input'),
                                              tool_response=_text(call.get('result')))))
    found.append(body('summary', dict(common, reply=turn.get('reply') or '')))
    return found


def send(setting, request, opener=None):
    """One request to the worker at the setting's loopback address: (status, answer). Raises Refused for an address
    that is not loopback or a paid-API field, and OSError when the worker does not answer."""
    address = setting.get('address') or {}
    if not loopback(str(address.get('host'))):
        raise Refused(NOT_LOOPBACK, str(address.get('host')))
    named = [name for name in request['body'] if name in paid_names()]
    if named:
        raise Refused('invalid_input:claude_mem:paid_api:' + named[0])
    host = address['host'] if ':' not in address['host'] else '[%s]' % address['host']
    url = 'http://%s:%d%s' % (host, int(address['port']), request['path'])
    data = json.dumps(request['body']).encode()
    message = urllib.request.Request(url, data=data, method=request['method'],
                                     headers={'Content-Type': 'application/json'})
    handler = urllib.request.build_opener(urllib.request.ProxyHandler({}))
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
    """One conversation directory's feeds: the pending feeds, the feed log and the session."""

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
        """(session id, whether this feed starts it): the conversation's first feed starts its session."""
        path = self.place(directory) / 'session.json'
        if path.exists():
            return json.loads(path.read_text())['session'], False
        session = session_of(identity)
        _write_private(path, {'conversation': identity, 'session': session})
        return session, True

    def pending(self, directory):
        place = self.place(directory) / 'pending'
        return sorted(place.glob('*.json')) if place.is_dir() else []

    def log(self, directory, entry):
        path = self.place(directory) / 'feed.jsonl'
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as out:
            out.write(json.dumps(entry, sort_keys=True) + '\n')

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
        session, start = self.session(directory, identity)
        requests = build(setting, turn, session=session, cwd=os.path.join(directory, 'workspace'), sequence=sequence,
                         start=start)
        feed = {'schema': SCHEMA, 'conversation': identity, 'sequence': sequence, 'dispatch_id': dispatch_id,
                'session': session, 'execution_record': base['execution_record'],
                'qualification': base['qualification'], 'requests': requests, 'sent': 0, 'late': False,
                'at': time.time()}
        _write_private(self.place(directory) / 'pending' / ('%08d.json' % sequence), feed)
        self.observe(dict(base, session=session, capture='pending', reason=None,
                          requests=[{'kind': r['kind'], 'digest': r['digest']} for r in requests]))
        return {'state': 'pending', 'reason': None, 'session': session}

    def flush(self, record):
        """Send the conversation's pending feeds in turn order, stopping at the first the worker does not take.
        Returns [(sequence, capture state)] for each feed whose state changed."""
        setting = self.setting()
        identity, directory = record['id'], record['directory']
        changed = []
        if setting is None or setting['state'] != 'qualified':
            return changed
        for path in self.pending(directory):
            feed = json.loads(path.read_text())
            base = {'schema': SCHEMA, 'operation': 'claude_mem_feed', 'conversation': identity,
                    'sequence': feed['sequence'], 'dispatch_id': feed['dispatch_id'], 'session': feed['session'],
                    'execution_record': feed['execution_record'], 'qualification': feed['qualification']}
            while feed['sent'] < len(feed['requests']):
                request = feed['requests'][feed['sent']]
                try:
                    status, answer = send(setting, request, self.opener)
                except Refused as error:
                    self.observe(dict(base, kind=request['kind'], digest=request['digest'], capture='not_captured',
                                      reason=error.code))
                    path.unlink()
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
                    if not feed['late']:
                        feed['late'] = True
                        _write_private(path, feed)
                        changed.append((feed['sequence'], {'state': 'pending', 'reason': UNAVAILABLE}))
                    return changed
                ok = 200 <= status < 300
                self.log(directory, {'conversation': identity, 'sequence': feed['sequence'],
                                     'session': feed['session'], 'kind': request['kind'], 'path': request['path'],
                                     'digest': request['digest'], 'request': request, 'status': status,
                                     'answer': answer, 'at': time.time()})
                self.observe(dict(base, kind=request['kind'], digest=request['digest'], status=status,
                                  outcome='sent' if ok else 'refused'))
                if not ok:
                    if not feed['late']:
                        feed['late'] = True
                        _write_private(path, feed)
                        changed.append((feed['sequence'], {'state': 'pending', 'reason': UNAVAILABLE}))
                    return changed
                feed['sent'] += 1
                _write_private(path, feed)
            else:
                kinds = {}
                for request in feed['requests']:
                    kinds[request['kind']] = kinds.get(request['kind'], 0) + 1
                path.unlink()
                state = {'state': 'captured', 'reason': None, 'session': feed['session'], 'requests': kinds,
                         'late': feed['late']}
                self.observe(dict(base, capture='captured', requests=kinds, late=feed['late']))
                changed.append((feed['sequence'], state))
                continue
            continue
        return changed


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
