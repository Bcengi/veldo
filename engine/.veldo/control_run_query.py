"""VELDO-0359: the receiver's finite, read-only run questions. No store fallback.

One JSON line per connection, at most MAX_BYTES, with one deadline for the whole
exchange. The serving thread owns its connection and each request's transaction.
Only the receiver and its reaping Runner remove a dispatch's endpoint; never scan.
"""
import collections
import contextlib
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import selectors
import socket
import sqlite3
import stat
import threading
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('run_query_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_KEPT = {}


def _kept(name):
    """An organ a request needs, loaded once per process: a request never loads a module again."""
    if name not in _KEPT:
        _KEPT[name] = _organ(name)
    return _KEPT[name]


EL = _organ('control_eligibility')
SCHEMA = EL.SCHEMA
VARIABLE = 'VELDO_RUN_QUERY'
SECONDS = 5.0
MAX_BYTES = 262144
LOG_BYTES = 1 << 20  # the per-request log's size; the counts go on after it
COORDINATES = ('domain_uuid', 'repository_uuid', 'authority_generation')
DECISION = ('schema', 'decision_id', 'station', 'unit', 'domain_uuid', 'repository_uuid',
            'follows', 'inputs', 'watermark', 'pending', 'refusals', 'eligible', 'architecture')
EVENT = ('schema', 'operation', 'domain_uuid', 'repository_uuid', 'unit', 'entity', 'decision_id',
         'follows', 'watermark', 'accepted_inputs', 'references', 'outcome', 'refusals', 'taxonomy', 'architecture')
FLOOR = ('unit', 'record', 'version', 'state', 'station', 'lane', 'reason', 'detail',
         'build_dispatch', 'review_dispatches')
FACTS = ('attempt_finished', 'artifact_accepted', 'revision_landed', 'objective_satisfied')
REPLICATION = ('schema', 'last_durable_seq', 'last_acknowledged_seq', 'local_committed_seq',
               'pending_exports', 'oldest_pending_age_seconds', 'undispatched', 'backfill_required',
               'paused_publication', 'paused_reason', 'pending')
REQUESTS = {'hello': (), 'decide': ('station', 'unit', 'context', 'ticket'),
            'decision_blockers': ('unit', 'references'), 'completion': ('unit',),
            'floor_entry': ('unit', 'word', 'landed'), 'replication_status': ()}


class Refused(EL.Stopped):
    def __init__(self, code='unavailable_service:run_query'):
        self.code = code
        super().__init__(code)


class Unsupported(Refused, AttributeError):
    def __init__(self, name):
        super().__init__('run_query:unsupported:' + name)


def endpoint(dispatch_id, environment=None):
    env = os.environ if environment is None else environment
    runtime = env.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    return Path(runtime) / ('veldo-query-' + hashlib.sha256(dispatch_id.encode()).hexdigest()[:32]) / 'query.sock'


def remove(path, identity=None):
    """Only called for this dispatch after its owner is finished. Never recurse, never raise: the
    run's end is recorded whatever is found here. None when the directory is gone, else why it is
    left ('left:ENOTEMPTY' when something else was put in it), for the caller to record."""
    path = Path(path)
    try:
        if identity is not None:
            try:
                info = path.parent.lstat()
            except FileNotFoundError:
                return None
            if (info.st_dev, info.st_ino) != tuple(identity):
                return 'left:replaced'
        with contextlib.suppress(FileNotFoundError):
            path.unlink()
        with contextlib.suppress(FileNotFoundError):
            path.parent.rmdir()
    except OSError as error:
        return 'left:' + errno.errorcode.get(error.errno or 0, type(error).__name__)
    except Exception as error:  # noqa: BLE001 - cleanup never stops an end from being recorded
        return 'left:' + type(error).__name__
    return None


def log_path(records, dispatch_id):
    """Where a dispatch's requests are logged, one name and outcome per line: a file beside the run's
    other records, never the launch pipe, so a Runner that is not reading cannot hold an answer."""
    return os.path.join(str(records), hashlib.sha256(str(dispatch_id).encode()).hexdigest() + '.query.log')


def switch(store):
    path = Path(store).parent / 'store-guard.off'
    recovery = 'delete it to keep the guard on, or replace it with a regular file to turn it off'
    try:
        path = Path(store).resolve().parent / 'store-guard.off'
    except (OSError, RuntimeError):
        return {'state': 'invalid', 'path': str(path), 'reason': 'invalid_input:layout:switch', 'recovery': recovery}
    result = {'state': 'on', 'path': str(path)}
    try:
        info = path.lstat()
    except FileNotFoundError:
        return result
    except OSError:
        return dict(result, state='invalid', reason='invalid_input:layout:switch', recovery=recovery)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        return dict(result, state='invalid', reason='invalid_input:layout:switch', recovery=recovery)
    return dict(result, state='off', modified_at=info.st_mtime,
                recovery='delete it to turn the guard back on')


def _pick(value, names):
    return {k: value[k] for k in names if k in value}


def _identity(value):
    if 'members' in value:
        return {'members': [list(m[:3]) for m in value['members']], 'digest': value['digest']}
    return _pick(value, ('id', 'version', 'digest', 'definition'))


def _decision(value):
    out = _pick(value, DECISION)
    out['inputs'] = {k: _identity(v) for k, v in value['inputs'].items()}
    if 'architecture' in out:
        a = _pick(out['architecture'], ('basis', 'kind', 'state', 'required', 'accepted', 'artifact',
                                       'validator', 'refusals', 'problems', 'error'))
        if a.get('accepted') is not None:
            a['accepted'] = _pick(a['accepted'], ('id', 'version', 'digest'))
        if a.get('artifact') is not None:
            a['artifact'] = _pick(a['artifact'], ('path', 'type', 'digest'))
        a['validator'] = {k: _pick(v, ('module', 'role', 'path', 'digest')) for k, v in a['validator'].items()}
        out['architecture'] = a
    return out


def _event(value):
    out = _pick(value, EVENT)
    if value['operation'] != 'invalid_record':
        out.pop('entity', None)
    if value['operation'] != 'decision_dependency':
        out.pop('references', None)
    if 'architecture' in out:
        out['architecture'] = _pick(out['architecture'], ('basis', 'kind', 'artifact_digest', 'validator', 'error'))
    return out


def _strings(value, nullable=False):
    return isinstance(value, list) and all(isinstance(v, str) or (nullable and v is None) for v in value)


def _flat(value, fields):
    return isinstance(value, dict) and set(value) <= set(fields) and all(
        v is None or type(v) in (str, int, bool, float) for v in value.values())


def _valid_identity(value):
    if not isinstance(value, dict):
        return False
    if set(value) == {'members', 'digest'}:
        return isinstance(value['digest'], str) and isinstance(value['members'], list) and all(
            isinstance(m, list) and len(m) == 3 and isinstance(m[0], str) and type(m[1]) is int
            and isinstance(m[2], str) for m in value['members'])
    return set(value) in ({'id', 'digest'}, {'id', 'version', 'digest'}, {'id', 'version', 'digest', 'definition'}) and _flat(
        value, ('id', 'version', 'digest', 'definition'))


def _valid_architecture(value, event=False):
    if not isinstance(value, dict):
        return False
    fields = ('basis', 'kind', 'artifact_digest', 'validator', 'error') if event else (
        'basis', 'kind', 'state', 'required', 'accepted', 'artifact', 'validator', 'refusals', 'problems', 'error')
    required = set(fields) - ({'error'} if event else {'error', 'problems'})
    if not required <= set(value) <= set(fields):
        return False
    if not _flat({k: v for k, v in value.items() if k not in ('validator', 'accepted', 'artifact', 'refusals', 'problems')}, fields):
        return False
    validators = value['validator']
    if not isinstance(validators, dict) or not all(isinstance(k, str) and (
            isinstance(v, str) if event else isinstance(v, dict) and set(v) == {'module', 'role', 'path', 'digest'}
            and _flat(v, ('module', 'role', 'path', 'digest'))) for k, v in validators.items()):
        return False
    return event or ((value['accepted'] is None or (_flat(value['accepted'], ('id', 'version', 'digest'))
                         and set(value['accepted']) == {'id', 'version', 'digest'}))
                     and (value['artifact'] is None or (_flat(value['artifact'], ('path', 'type', 'digest'))
                         and set(value['artifact']) == {'path', 'type', 'digest'}))
                     and _strings(value['refusals']) and ('problems' not in value or _strings(value['problems'])))


def _valid_event(event):
    if not isinstance(event, dict):
        return False
    fields = set(EVENT) - {'architecture', 'entity', 'references'}
    if event.get('operation') == 'invalid_record':
        fields.add('entity')
    if event.get('operation') == 'decision_dependency':
        fields.add('references')
    return (fields <= set(event) <= fields | {'architecture'}
            and _flat({k: v for k, v in event.items() if k not in ('accepted_inputs', 'references', 'refusals', 'taxonomy', 'architecture')}, EVENT)
            and isinstance(event['accepted_inputs'], dict)
            and all(type(v) in (int, str) or v is None for v in event['accepted_inputs'].values())
            and _strings(event['refusals']) and _strings(event['taxonomy'])
            and ('references' not in event or _strings(event['references']))
            and ('architecture' not in event or _valid_architecture(event['architecture'], event=True)))


def _valid_answer(name, answer):
    if name == 'decision_blockers':
        return _strings(answer)
    if not isinstance(answer, dict):
        return False
    if name == 'hello':
        return set(answer) == set(COORDINATES) and isinstance(answer['domain_uuid'], str) and (
            answer['repository_uuid'] is None or isinstance(answer['repository_uuid'], str)) and type(answer['authority_generation']) is int
    if name == 'decide':
        return (set(DECISION) - {'architecture'} <= set(answer) <= set(DECISION)
                and _flat({k: v for k, v in answer.items() if k not in ('inputs', 'pending', 'refusals', 'architecture')}, DECISION)
                and isinstance(answer['inputs'], dict) and all(_valid_identity(v) for v in answer['inputs'].values())
                and _strings(answer['pending']) and _strings(answer['refusals']) and type(answer['eligible']) is bool
                and ('architecture' not in answer or _valid_architecture(answer['architecture'])))
    if name == 'completion':
        return set(answer) == set(FACTS) and all(type(v) is bool for v in answer.values())
    if name == 'floor_entry':
        return (set(answer) == set(FLOOR) and _flat({k: v for k, v in answer.items() if k not in ('detail', 'review_dispatches')}, FLOOR)
                and _strings(answer['detail']) and _strings(answer['review_dispatches'], nullable=True))
    if name == 'replication_status':
        return (set(answer) == set(REPLICATION) and _flat({k: v for k, v in answer.items() if k != 'pending'}, REPLICATION)
                and isinstance(answer['pending'], list) and all(isinstance(p, dict) and set(p) == {'seq', 'command_id', 'state'}
                and _flat(p, ('seq', 'command_id', 'state')) for p in answer['pending']))
    return False


def _receive(sock, deadline):
    data = bytearray()
    while b'\n' not in data:
        sock.settimeout(max(0.001, deadline - time.monotonic()))
        if time.monotonic() >= deadline:
            raise TimeoutError()
        chunk = sock.recv(min(65536, MAX_BYTES + 1 - len(data)))
        if not chunk:
            raise ValueError('incomplete frame')
        data.extend(chunk)
        if len(data) > MAX_BYTES:
            raise ValueError('large frame')
    if data.count(b'\n') != 1 or not data.endswith(b'\n'):
        raise ValueError('extra frame')
    return json.loads(data)


def _send(sock, value, deadline):
    data = (json.dumps(value, allow_nan=False, separators=(',', ':')) + '\n').encode()
    if len(data) > MAX_BYTES or time.monotonic() >= deadline:
        raise ValueError('response limit')
    sock.settimeout(max(0.001, deadline - time.monotonic()))
    sock.sendall(data)


def _scope(gate, request):
    unit = request.get('unit')
    if not isinstance(unit, str) or not unit:
        raise Refused('coordinate_not_served')
    item = gate._entity(unit)
    data = gate._data(item) or {}
    if gate.repository_uuid is None:
        # A conversation receiver serves no repository: no record is its to answer about, and one
        # without a repository field is not matched by the absence of one here.
        raise Refused('coordinate_not_served')
    coordination = request.get('station') == 'coordination'
    if item is not None and item['value'] is not None:
        kind = item['value']['kind']
        allowed = (kind == 'pm_cycle' and data.get('domain') == gate.domain_uuid
                   and data.get('repository') == gate.repository_uuid) if coordination else (
                       kind == 'execution_unit' and data.get('repository_uuid') == gate.repository_uuid)
        if not allowed:
            raise Refused('coordinate_not_served')
    for ref in request.get('references', []):
        if not isinstance(ref, str):
            raise Refused('coordinate_not_served')
        record = gate._entity(ref)
        if record is not None and record['value'] is not None:
            body = gate._data(record) or {}
            # A reference may not turn an unrelated record into a governing decision.
            if record['value']['kind'] != 'decision' or not EL.DD.governs(body, unit, data.get('plan')):
                raise Refused('coordinate_not_served')


def _answer(gate, request):
    if not isinstance(request, dict):
        raise Refused('coordinate_not_served')
    name = request.get('operation')
    if not isinstance(name, str) or name not in REQUESTS or set(request) != {'operation', *REQUESTS[name]}:
        raise Refused('coordinate_not_served')
    if name == 'hello':
        return {k: getattr(gate, k) for k in COORDINATES}
    if name == 'replication_status':
        out = _pick(_kept('control_replica').replication_status(gate.conn, gate.store, time.time()), REPLICATION)
        out['pending'] = [_pick(p, ('seq', 'command_id', 'state')) for p in out['pending']]
        return out
    if name == 'decide':
        if request['station'] not in (*EL.STATION_PREDICATES, 'coordination') or any(
                request[k] is not None and not isinstance(request[k], dict) for k in ('context', 'ticket')):
            raise Refused('coordinate_not_served')
    if name == 'decision_blockers' and not isinstance(request['references'], list):
        raise Refused('coordinate_not_served')
    if name == 'floor_entry' and (request['word'] is not None and not isinstance(request['word'], str) or type(request['landed']) is not bool):
        raise Refused('coordinate_not_served')
    _scope(gate, request)
    unit = request['unit']
    if name == 'decide':
        return _decision(gate.decide(request['station'], unit, context=request['context'], ticket=request['ticket']))
    if name == 'decision_blockers':
        return gate.decision_blockers(unit, request['references'])
    if name == 'completion':
        return _pick(gate.completion(unit), FACTS)
    if name == 'floor_entry':
        return _pick(gate.floor_entry(unit, request['word'], request['landed']), FLOOR)
    raise Refused('coordinate_not_served')


class Server:
    def __init__(self, config, dispatch_id, log=None, environment=None, created=None):
        self.config = config
        self.created = created
        self.path = endpoint(dispatch_id, environment)
        self.log = log  # a file's path; None keeps the counts only
        self.log_fd = None
        self.logged = 0
        self.identity = None
        self.left = None  # why close left the endpoint directory, when it did
        self.counts = collections.Counter()
        self.ready = threading.Event()
        self.stopped = threading.Event()
        self.error = None
        self.listener = None
        self.active = None
        self.thread = None
        self.made = False
        self.wake = None

    def start(self):
        try:
            self.path.parent.mkdir(mode=0o700)  # exclusive, no startup sweep
            self.made = True
            self.path.parent.chmod(0o700)
            info = self.path.parent.lstat()
            self.identity = (info.st_dev, info.st_ino)
            if self.created is not None:
                self.created(self.identity)
            if self.log is not None:
                # A launch is never refused for its log: without it the counts remain.
                with contextlib.suppress(OSError, ValueError, TypeError):
                    os.makedirs(os.path.dirname(str(self.log)), mode=0o700, exist_ok=True)
                    self.log_fd = os.open(str(self.log), os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_CLOEXEC
                                          | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
                    if not stat.S_ISREG(os.fstat(self.log_fd).st_mode):
                        os.close(self.log_fd)
                        self.log_fd = None
            self.listener = socket.socket(socket.AF_UNIX)
            self.listener.bind(str(self.path))
            self.path.chmod(0o600)
            self.listener.listen(16)
            self.wake = socket.socketpair()
            self.thread = threading.Thread(target=self._serve, daemon=True, name='run-query')
            self.thread.start()
            if not self.ready.wait(SECONDS) or self.error is not None:
                raise Refused()
            return self
        except Exception as error:
            self.close()
            raise Refused() from error

    def _gate(self):
        # The installed receiver configuration is the verified launch binding, as
        # in Receiver._recheck. Never take workspace, store or trust from a request.
        store = _kept('control_store')
        workspace = self.config.get('workspace')
        conversation = self.config.get('receiver_kind') == 'conversation'
        settlements = None
        if not conversation:
            trust_path = self.config.get('host_trust')
            if not trust_path:
                raise Refused()
            trust = EL.load_host_trust(trust_path)
            if trust is None:
                raise Refused()
            settlements = trust.settlement_trust(workspace)
        conn = store.open_store(self.config['store'], mode='r')
        try:
            return EL.Gate(store, conn, domain_uuid=self.config['domain'],
                           repository_uuid=None if conversation else self.config['repository'],
                           authority_generation=self.config.get('authority_generation', 1),
                           workspace=workspace, settlement_trust=settlements)
        except Exception:
            conn.close()
            raise

    def _serve(self):
        gate = None
        try:
            gate = self._gate()  # opened here, never borrowed from the receiver thread
            gate.conn.execute('PRAGMA busy_timeout=1000')
            with selectors.DefaultSelector() as selector:
                selector.register(self.listener, selectors.EVENT_READ)
                selector.register(self.wake[0], selectors.EVENT_READ)
                self.ready.set()
                while not self.stopped.is_set():
                    for key, _ in selector.select():
                        if key.fileobj is not self.listener or self.stopped.is_set():
                            return
                        client, _ = self.listener.accept()
                        self.active = client
                        with client:
                            self._request(gate, client)
                        self.active = None
        except Exception as error:
            self.error = type(error).__name__
            self.ready.set()
        finally:
            if gate is not None:
                gate.close()

    def _request(self, gate, client):
        deadline = time.monotonic() + SECONDS
        events = []
        name, outcome = 'malformed', 'unavailable_service:run_query'
        gate.observe = lambda event: events.append(_event(event))
        gate.conn.set_progress_handler(lambda: int(self.stopped.is_set() or time.monotonic() >= deadline), 1000)
        try:
            request = _receive(client, deadline)
            if isinstance(request, dict) and request.get('operation') in REQUESTS:
                name = request['operation']
            with gate._reading():
                answer = _answer(gate, request)
            if not _valid_answer(name, answer) or not all(_valid_event(e) for e in events):
                raise ValueError('response schema')
            response = {'answer': answer, 'events': events}
            outcome = 'ok'
        except Refused as error:
            outcome = error.code
            response = {'error': outcome}
        except Exception:
            response = {'error': outcome}
        finally:
            gate.conn.set_progress_handler(None, 0)
        try:
            _send(client, response, deadline)
        except (OSError, ValueError):
            outcome = 'unavailable_service:run_query'
        self.counts[name + ':' + outcome] += 1
        self._log(name, outcome)

    def _log(self, name, outcome):
        """The request's name and outcome, never its arguments or answer, on a regular file: this
        thread writes nothing to the launch pipe, so it never waits for the Runner to read."""
        if self.log_fd is None or self.logged >= LOG_BYTES:
            return
        line = ('%s %s\n' % (name, outcome)).encode()
        if self.logged + len(line) >= LOG_BYTES:
            line = b'log full: the counts continue\n'
            self.logged = LOG_BYTES
        self.logged += len(line)
        with contextlib.suppress(OSError):
            os.write(self.log_fd, line)

    def close(self):
        """Stop serving and remove this dispatch's endpoint. Never raises: what could not be removed
        is left, named in `left`, and the caller goes on to record the run's end."""
        self.stopped.set()
        with contextlib.suppress(Exception):
            if self.active is not None:
                with contextlib.suppress(OSError):
                    self.active.shutdown(socket.SHUT_RDWR)
            if self.wake is not None:
                with contextlib.suppress(OSError):
                    self.wake[1].send(b'x')
            if self.thread is not None:
                self.thread.join(SECONDS)
        for sock in (self.listener, *(self.wake or ())):
            if sock is not None:
                with contextlib.suppress(Exception):
                    sock.close()
        if self.log_fd is not None and (self.thread is None or not self.thread.is_alive()):
            with contextlib.suppress(OSError):
                os.close(self.log_fd)
            self.log_fd = None
        if self.made:
            self.left = remove(self.path, self.identity)
            self.made = False


def _exchange(path, request):
    try:
        deadline = time.monotonic() + SECONDS
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(SECONDS)
            client.connect(str(path))
            _send(client, request, deadline)
            response = _receive(client, deadline)
        if not isinstance(response, dict):
            raise ValueError('response')
        if set(response) == {'error'} and response['error'] in ('coordinate_not_served', 'unavailable_service:run_query'):
            raise Refused(response['error'])
        if set(response) != {'answer', 'events'} or not isinstance(response['events'], list):
            raise ValueError('envelope')
        return response
    except Refused:
        raise
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise Refused() from error


class RemoteGate:
    __slots__ = ('_path', '_coordinates', 'observe', '_closed')
    SCHEMA = SCHEMA
    refusal_types = (Refused,)

    def __init__(self, workspace, path, observe=None):
        self._path, self._closed = path, False
        self.observe = observe or (lambda event: None)
        hello = _exchange(path, {'operation': 'hello'})
        answer = hello['answer']
        if not _valid_answer('hello', answer) or hello['events']:
            raise Refused()
        binding = EL.E.read_binding(workspace)
        if not binding or binding.get('repository_uuid') != answer['repository_uuid']:
            raise Refused('run_query:other_repository')
        self._coordinates = tuple(answer[k] for k in COORDINATES)

    domain_uuid = property(lambda self: self._coordinates[0])
    repository_uuid = property(lambda self: self._coordinates[1])
    authority_generation = property(lambda self: self._coordinates[2])

    def __getattr__(self, name):
        raise Unsupported(name)

    @staticmethod
    def refusal_code(error):
        return error.code

    def decide(self, station, unit, *, context=None, ticket=None):
        return _remote_answer(self, {'operation': 'decide', 'station': station, 'unit': unit,
                                     'context': context, 'ticket': ticket})

    def decision_blockers(self, unit, references=()):
        return _remote_answer(self, {'operation': 'decision_blockers', 'unit': unit, 'references': list(references)})

    def completion(self, unit):
        return _remote_answer(self, {'operation': 'completion', 'unit': unit})

    def landed(self, unit):
        return self.completion(unit)['revision_landed']

    def floor_entry(self, unit, word, landed=False, reader=None):
        # `reader` is the frontier's local reading, for a Gate that holds the store; never sent.
        return _remote_answer(self, {'operation': 'floor_entry', 'unit': unit, 'word': word, 'landed': landed})

    def replication_status(self):
        return _remote_answer(self, {'operation': 'replication_status'})

    def close(self):
        self._closed = True  # exchanges own their socket; none is retained between requests


def _remote_answer(gate, request):
    if gate._closed:
        raise Refused()
    response = _exchange(gate._path, request)
    if not isinstance(response, dict) or set(response) != {'answer', 'events'} or not isinstance(response['events'], list):
        raise Refused()
    answer = response['answer']
    name = request['operation']
    if not _valid_answer(name, answer) or not all(_valid_event(e) for e in response['events']):
        raise Refused()
    if name not in ('decide', 'decision_blockers') and response['events']:
        raise Refused()
    for event in response['events']:
        gate.observe(event)
    return answer
