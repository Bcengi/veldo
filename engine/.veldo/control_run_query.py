"""VELDO-0359: the receiver's finite, read-only run questions. No store fallback.

One JSON line per connection, at most MAX_BYTES, with one deadline for the whole
exchange. The serving thread owns its connection and each request's transaction.
Only the receiver and its reaping Runner remove a dispatch's endpoint; never scan.
"""
import collections
import contextlib
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


EL = _organ('control_eligibility')
SCHEMA = EL.SCHEMA
VARIABLE = 'VELDO_RUN_QUERY'
SECONDS = 5.0
MAX_BYTES = 262144
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


def remove(path):
    """Only called for this dispatch after its owner is finished. Never recurse."""
    path = Path(path)
    with contextlib.suppress(FileNotFoundError):
        path.unlink()
    with contextlib.suppress(FileNotFoundError):
        path.parent.rmdir()


def switch(store):
    path = Path(store).resolve().parent / 'store-guard.off'
    result = {'state': 'on', 'path': str(path)}
    try:
        info = path.lstat()
    except FileNotFoundError:
        return result
    except OSError:
        return dict(result, state='invalid', reason='invalid_input:layout:switch')
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
        return dict(result, state='invalid', reason='invalid_input:layout:switch')
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
    coordination = request.get('station') == 'coordination'
    if item is not None:
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
        if record is not None:
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
        out = _pick(_organ('control_replica').replication_status(gate.conn, gate.store, time.time()), REPLICATION)
        out['pending'] = [_pick(p, ('seq', 'command_id', 'state')) for p in out['pending']]
        return out
    if name == 'decide':
        if request['station'] not in (*EL.STATION_PREDICATES, 'coordination') or any(
                request[k] is not None and not isinstance(request[k], dict) for k in ('context', 'ticket')):
            raise Refused('coordinate_not_served')
    if name == 'decision_blockers' and not isinstance(request['references'], list):
        raise Refused('coordinate_not_served')
    if name == 'floor_entry' and (not isinstance(request['word'], str) or type(request['landed']) is not bool):
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
    def __init__(self, config, dispatch_id, observe=None, environment=None):
        self.config = config
        self.path = endpoint(dispatch_id, environment)
        self.observe = observe or (lambda event: None)
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
            self.listener = socket.socket(socket.AF_UNIX)
            self.listener.bind(str(self.path))
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
        trust = EL.load_host_trust(self.config.get('host_trust'))
        if trust is None:
            raise Refused()
        workspace = self.config['workspace']
        binding = EL.E.read_binding(workspace)
        if not binding or os.path.realpath(EL.E.store_path_for(binding)) != os.path.realpath(self.config['store']):
            raise Refused()
        gate = EL.enrolled_gate(workspace, trust)
        if (gate.domain_uuid, gate.repository_uuid, gate.authority_generation) != (
                self.config['domain'], self.config['repository'], self.config.get('authority_generation', 1)):
            gate.close()
            raise Refused()
        return gate

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
        self.observe({'event': 'run_query', 'request': name, 'outcome': outcome})

    def close(self):
        self.stopped.set()
        if self.active is not None:
            with contextlib.suppress(OSError):
                self.active.shutdown(socket.SHUT_RDWR)
        if self.wake is not None:
            with contextlib.suppress(OSError):
                self.wake[1].send(b'x')
        if self.thread is not None:
            self.thread.join(SECONDS)
        if self.listener is not None:
            self.listener.close()
        if self.wake is not None:
            for sock in self.wake:
                sock.close()
        if self.made:
            remove(self.path)
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
        if not isinstance(answer, dict) or set(answer) != set(COORDINATES):
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

    def floor_entry(self, unit, word, landed=False):
        return _remote_answer(self, {'operation': 'floor_entry', 'unit': unit, 'word': word, 'landed': landed})

    def replication_status(self):
        return _remote_answer(self, {'operation': 'replication_status'})

    def close(self):
        self._closed = True  # exchanges own their socket; none is retained between requests


def _remote_answer(gate, request):
    if gate._closed:
        raise Refused()
    response = _exchange(gate._path, request)
    answer = response['answer']
    name = request['operation']
    fields = {'decide': DECISION, 'completion': FACTS, 'floor_entry': FLOOR, 'replication_status': REPLICATION}
    if name in fields:
        required = set(fields[name]) - ({'architecture'} if name == 'decide' else set())
        if not isinstance(answer, dict) or not required <= set(answer) <= set(fields[name]):
            raise Refused()
    elif not isinstance(answer, list) or not all(isinstance(v, str) for v in answer):
        raise Refused()
    for event in response['events']:
        if not isinstance(event, dict) or not set(event) <= set(EVENT):
            raise Refused()
        gate.observe(event)
    return answer
