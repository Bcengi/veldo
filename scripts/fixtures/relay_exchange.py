"""VELDO-0121 exchange model and fault controls around real AF_UNIX transport.

No host lock operations live here. The caller serializes mutation runs. All sockets,
threads and children belong to the current scratch directory and are closed/joined.
See proof/VELDO-0121/MODEL.md for the finite schedule domain and its limits.
"""
import ast
import base64
import concurrent.futures
import errno
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import zlib

VERSION = 'relay-exchange-v1'
LIMIT = 1 << 20
ROWS = {
    'AC1': 'relay/transport-errors-have-zero-stdout',
    'AC2': 'relay/eof-and-size-decisions-match-model',
    'AC3': 'relay/exchange-deadline-is-total',
    'AC4': 'relay/failure-does-not-replay',
}
OUTCOMES = {
    'connect': ('ENOENT', 'ECONNREFUSED', 'EACCES', 'ECONNRESET', 'ETIMEDOUT', 'timeout'),
    'send': ('EPIPE', 'ECONNRESET', 'ENOTCONN', 'ETIMEDOUT', 'timeout', 'zero'),
    'shutdown': ('EPIPE', 'ECONNRESET', 'ENOTCONN', 'ETIMEDOUT', 'timeout'),
    'recv': ('ECONNRESET', 'ENOTCONN', 'ETIMEDOUT', 'timeout'),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def wire(n):
    return (b'\x00\xff\x80ABC' * ((n + 5) // 6))[:n]


def encoded(data):
    """Lossless exact bytes, compact even for the 1 MiB boundary cases."""
    return dict(length=len(data), sha256=digest(data),
                zlib_base64=base64.b64encode(zlib.compress(data)).decode())


def partitions(n):
    if not n:
        return [()]
    return [(head,) + tail for head in range(1, n + 1) for tail in partitions(n - head)]


def offsets(parts):
    result, at = [], 0
    for size in parts:
        result.append(at)
        at += size
    return result


def chunks(n, width):
    return tuple(min(width, n - at) for at in range(0, n, width))


def shapes():
    # Every composition for each 0..3-byte request AND response, crossed.
    for n in range(4):
        for m in range(4):
            for sends in partitions(n):
                for receives in partitions(m):
                    yield n, m, sends, receives
    # Boundary classes: either side of 64 KiB and 1 MiB, plus every 64 KiB
    # boundary up to the limit. One-byte leading chunks vary alignment.
    for n in (65535, 65536, 65537, LIMIT - 1, LIMIT):
        for parts in (chunks(n, 65536), (1,) + chunks(n - 1, 65536)):
            yield n, 3, parts, (1, 2)
            yield 3, n, (1, 2), parts


def fault_schedules():
    for n, m, sends, receives in shapes():
        for phase, positions in (('connect', [0]), ('send', offsets(sends)),
                                 ('shutdown', [n]), ('recv', offsets(receives) + [m])):
            for offset in positions:
                for outcome in OUTCOMES[phase]:
                    yield dict(kind='fault', request=n, response=m, sends=sends,
                               receives=receives, phase=phase, offset=offset, outcome=outcome)


def terminal_schedules():
    for n, m, sends, receives in shapes():
        yield dict(kind='terminal', request=n, response=m, sends=sends, receives=receives)
    for n in (LIMIT - 1, LIMIT, LIMIT + 1):
        for width in (65536, 65535):
            yield dict(kind='terminal', request=n, response=3, sends=chunks(n, width),
                       receives=(1, 2), stdin_width=width)
            yield dict(kind='terminal', request=3, response=n, sends=(1, 2),
                       receives=chunks(n, width), stdin_width=width)


class Input(io.BytesIO):
    def __init__(self, data, width):
        super().__init__(data)
        self.width = width

    def read(self, n=-1):
        return super().read(min(n, self.width) if n >= 0 else self.width)


class Exchange:
    """A phase barrier on each real transport call, not a replacement forward().

    In deterministic schedules the peer pumps bytes synchronously at each barrier.
    This removes scheduler races while connect/send/shutdown/recv remain kernel calls.
    Only the selected failing result, partial-call width and clock are controlled.
    """
    def __init__(self, home, case):
        self.case, self.address = case, str(home / 'endpoint')
        self.listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.listener.bind(self.address)
        self.listener.listen(4)
        self.listener.settimeout(1)
        self.connections, self.complete, self.events, self.clients = [], [], [], []
        self.attempts, self.now, self.fired = 0, 0.0, False
        if case.get('native') == 'before_connect':
            self.listener.close()

    def factory(self, *args):
        client = Transport(self, socket.socket(*args))
        self.clients.append(client)
        return client

    def close(self):
        for client in self.clients:
            client.close()
            if client.peer is not None:
                client.peer.close()
        self.listener.close()

    def enter(self, client, phase, offset):
        event = dict(phase=phase, offset=offset, outcome='ok', time=self.now)
        self.events.append(event)
        c = self.case
        if not self.fired and 'outcome' in c and c.get('phase') == phase and c.get('offset') == offset:
            self.fired = True
            outcome = c['outcome']
            event['outcome'] = outcome
            if outcome == 'stall':
                self.now += client.budget
                raise TimeoutError('injected stalled operation')
            if outcome == 'late':
                # A syscall returned as the deadline expired. Its result must
                # still be refused even if the kernel reports successful EOF.
                self.now += 30.01
                return False
            if outcome == 'timeout':
                raise TimeoutError('injected operation timeout')
            if outcome == 'zero':
                return True
            raise OSError(getattr(errno, outcome), 'injected ' + outcome)
        if c.get('trickle') and phase == 'recv' and offset < c['response']:
            delay = 29.0
            if client.budget < delay:
                self.now += client.budget
                event['outcome'] = 'timeout'
                raise TimeoutError('trickle exhausted remaining budget')
            self.now += delay
        return False


class Transport:
    def __init__(self, exchange, raw):
        self.x, self.raw, self.peer = exchange, raw, None
        self.sent, self.received, self.budget = 0, 0, 30.0
        self.request, self.closed, self.peer_closed = bytearray(), False, False
        self.counted_request = False

    def settimeout(self, value):
        self.budget = value
        self.raw.settimeout(min(value, 1))

    def native_close(self, phase, offset):
        c = self.x.case
        if not self.peer_closed and c.get('native') and c.get('phase') == phase and c['offset'] == offset:
            if self.peer is not None:
                self.peer.close()
            self.peer_closed = True

    def kernel(self, operation, *args):
        event = self.x.events[-1]
        try:
            value = getattr(self.raw, operation)(*args)
        except OSError as exc:
            event['kernel_outcome'] = type(exc).__name__
            event['kernel_errno'] = exc.errno
            event['kernel_diagnostic'] = str(exc)
            raise
        event['kernel_outcome'] = 'orderly_eof' if operation == 'recv' and value == b'' else 'ok'
        event['kernel_return'] = len(value) if isinstance(value, bytes) else value
        return value

    def connect(self, address):
        self.x.attempts += 1
        self.x.enter(self, 'connect', 0)
        self.kernel('connect', address)
        self.peer, _ = self.x.listener.accept()
        self.peer.settimeout(1)
        self.x.connections.append(self)

    def send(self, data):
        if self.x.enter(self, 'send', self.sent):
            return 0
        self.native_close('send', self.sent)
        parts = self.x.case['sends']
        stop = next((v for v in offsets(parts) + [sum(parts)] if v > self.sent), self.sent + len(data))
        count = self.kernel('send', data[:stop - self.sent])
        if not self.peer_closed and not self.x.case.get('unread'):
            got = bytearray()
            while len(got) < count:
                got.extend(self.peer.recv(count - len(got)))
            self.request.extend(got)
        self.sent += count
        if not self.peer_closed:
            self.observe_request()
        return count

    def observe_request(self):
        if self.x.case.get('unread') and self.sent:
            # Observe the identity while keeping bytes unread for native reset.
            self.request = bytearray(self.peer.recv(65536, socket.MSG_PEEK))
        if not self.counted_request and len(self.request) == self.x.case['request']:
            self.x.complete.append(digest(bytes(self.request)))
            self.counted_request = True

    def shutdown(self, how):
        self.x.enter(self, 'shutdown', self.sent)
        self.native_close('shutdown', self.sent)
        self.kernel('shutdown', how)
        if not self.peer_closed:
            if not self.x.case.get('unread'):
                assert self.peer.recv(1) == b''
            self.observe_request()

    def recv(self, size):
        self.x.enter(self, 'recv', self.received)
        self.native_close('recv', self.received)
        c = self.x.case
        if not self.peer_closed:
            end = next((v for v in offsets(c['receives']) + [c['response']] if v > self.received), None)
            if end is None:
                self.peer.close()
                self.peer_closed = True
            else:
                self.peer.sendall(wire(c['response'])[self.received:min(end, self.received + size)])
                size = min(size, end - self.received)
        answer = self.kernel('recv', size)
        self.received += len(answer)
        return answer

    def close(self):
        self.raw.close()
        self.closed = True


def load(source):
    module = types.ModuleType('relay121')
    exec(compile(source, 'control_relay.py', 'exec'), module.__dict__)
    return module


def execute(source, case):
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='v121-') as directory:
        exchange = Exchange(Path(directory), case)
        module = load(source)
        out, err = io.BytesIO(), io.StringIO()
        module.socket = types.SimpleNamespace(socket=exchange.factory, AF_UNIX=socket.AF_UNIX,
                                              SOCK_STREAM=socket.SOCK_STREAM, SHUT_WR=socket.SHUT_WR)
        module.time = types.SimpleNamespace(monotonic=lambda: exchange.now)
        module.sys = types.SimpleNamespace(stdout=types.SimpleNamespace(buffer=out))
        unexpected = None
        try:
            code = module.main(['relay', exchange.address],
                               Input(wire(case['request']), case.get('stdin_width', 65536)), out, err)
        except Exception as exc:
            code, unexpected = None, repr(exc)
        finally:
            closed_by_relay = all(c.closed for c in exchange.clients)
            exchange.close()
        value = dict(case=case, input_sha256=digest(wire(case['request'])),
                     implementation_sha256=digest(source.encode()), fixture_version=VERSION,
                     events=exchange.events, injected_reached=exchange.fired,
                     exit=code, stdout=encoded(out.getvalue()), stderr=err.getvalue(),
                     endpoint_named=exchange.address in err.getvalue(),
                     connection_attempts=exchange.attempts, accepted_connections=len(exchange.connections),
                     complete_requests=exchange.complete, transport_seconds=exchange.now,
                     elapsed_seconds=time.monotonic() - started, closed_by_relay=closed_by_relay,
                     unexpected=unexpected)
        # Retain the precise kernel error observed, not an assumed close result.
        if case.get('native'):
            value['kernel_diagnostic'] = err.getvalue()
        return value


def classification(record):
    if record['exit'] == 0:
        return 'orderly_eof'
    if record['exit'] == 4:
        return 'request_too_large' if 'request' in record['stderr'] else 'response_too_large'
    if record['exit'] == 3:
        timed = {'timeout', 'ETIMEDOUT', 'stall', 'late'}
        if (any(e.get('outcome') in timed for e in record.get('events', []))
                or any(word in record['stderr'] for word in ('timed out', 'deadline', 'budget'))):
            return 'endpoint_timeout'
        return 'endpoint_error'
    return 'unexpected'


def refused(record):
    return record['exit'] == 3 and record['stdout']['length'] == 0 and record['endpoint_named']


def no_replay(record):
    return (record['connection_attempts'] <= 1 and record['accepted_connections'] <= 1
            and len(record['complete_requests']) <= 1
            and all(identity == record['input_sha256'] for identity in record['complete_requests']))


def native_schedules():
    yield dict(kind='native', native='before_connect', request=3, response=3,
               sends=(1, 2), receives=(1, 2))
    for mode in ('close', 'reset'):
        for phase, offset in (('send', 0), ('send', 1), ('shutdown', 3), ('recv', 0), ('recv', 1)):
            yield dict(kind='native', native=mode, request=3, response=3,
                       sends=(1, 2), receives=(1, 2), phase=phase, offset=offset,
                       unread=mode == 'reset')


def deadline_schedules():
    for phase, offset in (('connect', 0), ('send', 0), ('send', 1),
                          ('shutdown', 3), ('recv', 0), ('recv', 1), ('recv', 3)):
        for outcome in ('stall', 'late'):
            yield dict(kind='deadline', request=3, response=3, sends=(1, 2), receives=(1, 2),
                       phase=phase, offset=offset, outcome=outcome)
    yield dict(kind='deadline', request=3, response=3, sends=(1, 2), receives=(1, 1, 1), trickle=True)


def realtime(source, trickle):
    """Unmodified relay CLI, real monotonic clock, stdin supplied, stdout drained.

    The endpoint ends by 30.25 seconds even for the renewing-deadline mutant,
    allowing that mutant to finish normally and falsify the actual named row.
    """
    with tempfile.TemporaryDirectory(prefix='v121-clock-') as directory:
        home = Path(directory)
        relay = home / 'relay.py'
        relay.write_text(source)
        address = str(home / 'endpoint')
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(address)
        listener.listen(4)
        listener.settimeout(.1)
        stop, requests, faults = threading.Event(), [], []
        accepted = []

        def endpoint():
            try:
                while not stop.is_set():
                    try:
                        peer, _ = listener.accept()
                        break
                    except socket.timeout:
                        continue
                else:
                    return
                accepted.append(1)
                with peer:
                    peer.settimeout(.1)
                    request = bytearray()
                    while not stop.is_set():
                        try:
                            part = peer.recv(65536)
                        except socket.timeout:
                            continue
                        if not part:
                            break
                        request.extend(part)
                    requests.append(digest(bytes(request)))
                    born = time.monotonic()
                    for at in ((29.0, 30.25) if trickle else (30.25,)):
                        if stop.wait(max(0, born + at - time.monotonic())):
                            return
                        if trickle:
                            peer.sendall(b'\xff')
            except OSError as exc:
                faults.append(repr(exc))

        worker = threading.Thread(target=endpoint)
        worker.start()
        started = time.monotonic()
        proc = subprocess.Popen([sys.executable, str(relay), address], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        unexpected = None
        try:
            out, err = proc.communicate(b'\x00\xff\x80', timeout=32)
        except subprocess.TimeoutExpired:
            unexpected = 'fixture watchdog expired: invalid drive'
            proc.kill()
            out, err = proc.communicate()
        finally:
            stop.set()
            worker.join(1)
            listener.close()
        elapsed = time.monotonic() - started
        return dict(case=dict(kind='realtime', trickle=trickle), exit=proc.returncode,
                    stdout=encoded(out), stderr=err.decode(), endpoint_named=address in err.decode(),
                    elapsed_seconds=elapsed, transport_seconds=elapsed,
                    closed_by_relay=proc.poll() is not None and not worker.is_alive(),
                    surviving_helpers=int(worker.is_alive()) + int(proc.poll() is None),
                    accepted_connections=len(accepted), complete_requests=requests,
                    input_sha256=digest(b'\x00\xff\x80'), implementation_sha256=digest(source.encode()),
                    fixture_version=VERSION, endpoint_faults=faults, unexpected=unexpected)


def reconcile(source):
    tree = ast.parse(source)
    forward = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'forward')
    calls = [n.func.attr for n in ast.walk(forward) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
             and n.func.value.id == 'conn']
    expected = {'settimeout', 'connect', 'send', 'shutdown', 'recv', 'close'}
    return dict(calls=calls, expected=sorted(expected), matches=set(calls) == expected)


def qualify(source, criterion=None):
    """Each criterion is its own completed automated check; no missing cells pass."""
    selected = [criterion] if criterion else list(ROWS)
    records, checks, expected_counts, coverage = [], {}, {}, {}
    reconciliation = reconcile(source)
    faults = []
    if set(selected) & {'AC1', 'AC4'}:
        schedules = list(fault_schedules())
        expected_counts['fault'] = len(schedules)
        faults = [execute(source, case) for case in schedules]
        native = [execute(source, case) for case in native_schedules()]
        expected_counts['native'] = len(list(native_schedules()))
        records.extend(faults + native)
        coverage['phase_outcomes'] = sorted({e['phase'] + '/' + e['outcome']
                                           for r in faults for e in r['events'] if e['outcome'] != 'ok'})
        required = sorted(phase + '/' + outcome for phase, outcomes in OUTCOMES.items() for outcome in outcomes)
        complete = (len(faults) == len(schedules) and all(r['injected_reached'] for r in faults)
                    and coverage['phase_outcomes'] == required)
        if 'AC1' in selected:
            # A native orderly close can succeed with exactly the received prefix.
            # A reset/error must meet the endpoint refusal contract, whichever
            # operation the kernel selected for delivering it.
            native_ok = all(refused(r) if r['exit'] == 3 else
                            r['exit'] == 0 and r['stderr'] == '' and
                            r['stdout'] == encoded(wire(3)[:r['case'].get('offset', 0)
                                                          if r['case'].get('phase') == 'recv' else 0])
                            for r in native)
            checks['AC1'] = (complete and reconciliation['matches'] and all(refused(r) for r in faults)
                             and native_ok and any(e.get('kernel_errno') == errno.ECONNRESET
                                                  for r in native for e in r['events']))
        if 'AC4' in selected:
            checks['AC4'] = complete and all(no_replay(r) for r in faults + native)
    if 'AC2' in selected:
        schedules = list(terminal_schedules())
        expected_counts['terminal'] = len(schedules)
        terminal = [execute(source, case) for case in schedules]
        records.extend(terminal)
        def terminal_ok(r):
            c = r['case']
            if c['request'] > LIMIT or c['response'] > LIMIT:
                direction = 'request' if c['request'] > LIMIT else 'response'
                return (r['exit'] == 4 and r['stdout']['length'] == 0 and direction in r['stderr']
                        and (c['request'] <= LIMIT or r['connection_attempts'] == 0))
            return (r['exit'] == 0 and r['stdout'] == encoded(wire(c['response'])) and r['stderr'] == ''
                    and r['complete_requests'] == [r['input_sha256']])
        checks['AC2'] = len(terminal) == len(schedules) and all(terminal_ok(r) for r in terminal)
    if 'AC3' in selected:
        schedules = list(deadline_schedules())
        deadline = [execute(source, case) for case in schedules]
        # Two joined children qualify the real 30 second budget concurrently.
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            native_clock = list(pool.map(lambda trickle: realtime(source, trickle), (False, True)))
        expected_counts.update(deadline=len(schedules), realtime=2)
        records.extend(deadline + native_clock)
        checks['AC3'] = (all(refused(r) and r['transport_seconds'] <= 31 and r['closed_by_relay']
                            for r in deadline + native_clock)
                         and all(r['injected_reached'] for r in deadline if not r['case'].get('trickle')))
    for record in records:
        record['classification'] = classification(record)
        record['schedule_sha256'] = digest(json.dumps(record['case'], sort_keys=True).encode())
    valid = all(r['unexpected'] is None for r in records)
    counts = {kind: sum(r['case']['kind'] == kind for r in records) for kind in expected_counts}
    incomplete = [kind for kind in expected_counts if expected_counts[kind] != counts[kind]]
    incomplete.extend(r['schedule_sha256'] for r in records
                      if r['case']['kind'] in ('fault', 'deadline') and 'phase' in r['case']
                      and not r['injected_reached'])
    return dict(fixture_version=VERSION, fixture_sha256=digest(Path(__file__).read_bytes()),
                implementation_sha256=digest(source.encode()), reconciliation=reconciliation,
                expected=expected_counts, executed=counts, incomplete=incomplete,
                valid=valid, coverage=coverage, rows={ROWS[k]: bool(v and valid and not incomplete)
                                                    for k, v in checks.items()}, records=records)


MUTATIONS = {
    'AC1': ('            chunks.append(chunk)',
            '            chunks.append(chunk)\n            sys.stdout.buffer.write(chunk)\n            sys.stdout.buffer.flush()'),
    'AC2': ('            if not chunk:\n                break',
            '            if not chunk:\n                raise OSError("clean EOF misclassified")'),
    'AC3': ('            chunks.append(chunk)',
            '            chunks.append(chunk)\n            deadline = time.monotonic() + timeout'),
    'AC4': ('            chunk = conn.recv(65536)',
            '            try:\n                chunk = conn.recv(65536)\n            except OSError:\n'
            '                conn.close()\n                conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)\n'
            '                conn.settimeout(remaining())\n                conn.connect(address)\n'
            '                replayed = 0\n                while replayed < len(payload):\n'
            '                    replayed += conn.send(memoryview(payload)[replayed:])\n'
            '                conn.shutdown(socket.SHUT_WR)\n                chunk = conn.recv(65536)'),
}


def mutate(source, criterion):
    old, new = MUTATIONS[criterion]
    if source.count(old) != 1:
        raise ValueError('mutation anchor must match exactly once: ' + criterion)
    return source.replace(old, new)
