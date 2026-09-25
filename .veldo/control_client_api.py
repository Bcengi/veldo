#!/usr/bin/env python3
"""The API process's way to its authority: every command and read over the VELDO-0047 service socket
(VELDO-0107), and the hint socket the service wakes it on (VELDO-0130 phase 3).

WHAT THIS MODULE IS. The authenticated API (control_api.ControlApi) asks its `authority` to inspect,
apply, read, load a workflow, read events and follow the feed. In the API process that authority is
`ServiceAuthority`: each call is one control_client.send to the authority service of the API's enrolled
workspace, its command one API call (control_api_assertion.call_command), its request signed by the
protected signer's api purpose (control_api_signer.ApiSigner.request), never by a key this process holds.
The service judges the peer, the edge's request signature and the coordinate, and runs the call on its
own judge; nothing here opens the store. A refused or unreachable request raises Unavailable, which the
API names unavailable_service and never serves as an answer.

THE HINTS. `Hints` is the API's own local stream socket, in the API's 0700 state directory and 0600,
accepting only a peer the kernel says is this account (SO_PEERCRED). The service sends the VELDO-0046
hint of the head record after each commit, and each is handed to ControlApi.deliver, which reads the
records after its cursor through `feed`, ends the sessions a revocation ends and closes their streams.
`ServiceAuthority.connect` subscribes that socket. The service remembers its subscribers across a restart
and, once serving, sends each the head's hint; every hint names the service instance that sent it and
its number for this subscriber. When a hint, or the answer to any call, names another instance, or a
hint's number skips (hints were lost), the API subscribes again by itself and delivers the head's hint,
so it reconciles every record after its cursor (ControlApi.deliver pages the feed to the head) without
waiting for a request of its own. Deliveries run one at a time; a reconcile noticed inside one runs
when that delivery ends, once. A delivery that fails (the service refused unavailable, or a call raised)
leaves the catch-up owed: the hint socket's thread, which wakes every 0.25 s, runs it again with backoff
until it reaches the head. That is a retry of a delivery known to have failed, never polling for change.
`open_api` delivers the head the subscription answers, so the cursor is set from the start.

`open_api` is the production construction of the API process from its 0600 host configuration
(veldo.api_process/v1): the enrolled workspace and host trust the request is routed and verified with,
the protected signer's configuration, edge key id and connection key, the API's own configuration and
its loopback listener. Standard library only.
"""
import importlib.util
import json
import os
from pathlib import Path
import socket
import stat
import struct
import threading
import time


def _organ(name):
    spec = importlib.util.spec_from_file_location('client_api_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CC = _organ('control_client')
CE = _organ('control_enrollment')
EL = _organ('control_eligibility')
API = _organ('control_api')
SG = _organ('control_api_signer')
AS = API.AS

SCHEMA = 'veldo.api_process/v1'
FIELDS = ('schema', 'api', 'workspace', 'host_trust', 'signer', 'listen')
HINT_NAME = 'hints.sock'
HINT_LIMIT = 64 * 1024
EVENT_LIMIT = 256
# A catch-up that failed is tried again after RETRY_FIRST seconds, then twice as long each time it fails
# again, never longer than RETRY_MOST.
RETRY_FIRST, RETRY_MOST = 0.25, 8.0


class Unavailable(Exception):
    """The authority service refused or did not answer the API's request, by name."""

    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


class ServiceAuthority:
    """The API's authority, reached only through the authority service socket of `workspace`."""

    def __init__(self, workspace, verify, host_identity, sign, enrollment=CE, timeout=30.0):
        self.workspace, self.verify, self.host_identity = str(workspace), verify, host_identity
        self.sign, self.enrollment, self.timeout = sign, enrollment, timeout
        self.instance, self.seen, self.socket, self.api = None, None, None, None
        self.calls = {'accepted': 0, 'refused': 0}
        # One delivery at a time. The thread delivering is remembered, so a new service instance noticed by
        # a call made inside a delivery defers its reconcile to the end of that delivery (never re-entering
        # it), and the reconcile is applied once however many calls notice it.
        self._delivering = threading.Lock()
        self._deliverer, self._due = None, False
        # The last hint number the subscribed instance sent this API (a gap means hints were lost).
        self.sequence = None
        # A catch-up owed because a delivery failed (the service refused unavailable or a call raised):
        # (monotonic time it is next tried, the backoff after that), or None when nothing is owed.
        self.owed = None

    def _call(self, call, **arguments):
        try:
            answer = CC.send(self.workspace, AS.call_command(call, arguments), self.enrollment, self.verify, self.sign,
                             self.host_identity, timeout=self.timeout)
        except CC.RoutingRefused as exc:
            self.calls['refused'] += 1
            raise Unavailable('unavailable_service:authority:' + exc.reason, 'the authority service did not answer') from None
        except Exception as exc:  # noqa: BLE001 - a signer refusal signs nothing and sends nothing
            self.calls['refused'] += 1
            raise Unavailable('unavailable_service:authority:' + str(getattr(exc, 'code', type(exc).__name__)),
                              'the request was not signed') from None
        if not answer.get('accepted') or not isinstance(answer.get('result'), dict):
            self.calls['refused'] += 1
            raise Unavailable('unavailable_service:authority:' + str(answer.get('reason')), 'the service refused the request')
        self.calls['accepted'] += 1
        result = answer['result']
        instance = self.seen = result.pop('instance', None)
        if call != 'subscribe' and self.socket is not None and instance is not None and instance != self.instance:
            self._reconcile_due()
        return result

    # the ControlApi authority interface

    def inspect(self, entity_ids):
        result = self._call('inspect', entity_ids=list(entity_ids or []))
        if not result.get('ok'):
            raise Unavailable(str(result.get('reason')), 'the authority refused inspection')
        return result

    def apply(self, packet):
        return self._call('apply', packet=packet)

    def read(self, model, principal):
        return self._call('read', model=model, principal=principal)

    def workflow(self, principal, workflow, version=None):
        return self._call('workflow', principal=principal, workflow=workflow, version=version)

    def events(self, principal, after, limit=EVENT_LIMIT):
        return self._call('events', principal=principal, after=after, limit=limit)

    def feed(self, after, limit=EVENT_LIMIT):
        return self._call('feed', after=after, limit=limit)

    # the subscription

    def connect(self, socket_path, api):
        """Subscribe `socket_path` for the service's hints, delivered to `api`. Returns the head's hint."""
        self.socket, self.api = str(socket_path), api
        return self._subscribe()

    def _subscribe(self):
        result = self._call('subscribe', socket=self.socket)
        if not result.get('ok'):
            raise Unavailable(str(result.get('reason')), 'the service did not subscribe the API')
        self.instance = self.seen
        self.sequence = result.get('sequence') if type(result.get('sequence')) is int else None
        return {k: result.get(k) for k in ('schema', 'domain_uuid', 'repository_uuid', 'store_uuid', 'command_id',
                                           'record_digest', 'watermark')}

    def _reconcile_due(self):
        """A new service instance (it restarted and may have forgotten this subscriber) or a gap in its
        hints: subscribe again and deliver the head, so every record after the API's cursor is reconciled.
        On the delivering thread it is deferred to the end of the delivery in hand; on any other thread it
        runs now, after any delivery in hand."""
        self._due = True
        if self._deliverer != threading.get_ident():
            self.deliver(None)

    def deliver(self, hint):
        """One hint to the API's deliver, one at a time (the hint socket and a reconcile share it), then
        any reconcile that became due, once. A hint names the service instance that sent it and its number
        for this subscriber: another instance, or a number that skips, makes the reconcile due. `None`
        delivers only a due reconcile."""
        if self.api is None:
            return {'refusal': 'unavailable_service:not_connected'}
        with self._delivering:
            self._deliverer = threading.get_ident()
            try:
                answer = None
                if hint is not None:
                    sender, number = (hint.get('instance'), hint.get('sequence')) if isinstance(hint, dict) else (None, None)
                    if sender is not None and (sender != self.instance or type(number) is not int
                                               or self.sequence is None or number != self.sequence + 1):
                        self._due = True
                    elif sender is not None:
                        self.sequence = number
                    answer = self.api.deliver(hint)
                    if _unavailable(answer):
                        self._owe()
                while self._due:
                    self._due = False
                    head = self._subscribe()
                    if type(head.get('watermark')) is int and head['watermark'] > 0:
                        answer = self.api.deliver(head)
                        if _unavailable(answer):
                            self._owe()
                            break
                    self.owed = None
                return answer
            except Exception as exc:  # noqa: BLE001 - the catch-up stays owed; the caller's own call stands
                self._owe()
                return {'refusal': str(getattr(exc, 'code', None) or 'unknown_outcome:' + type(exc).__name__)}
            finally:
                self._deliverer = None

    def _owe(self):
        """A delivery failed, so the records after the cursor may hold a revocation nobody will hint
        again: the catch-up stays owed until `retry` runs it to the head, with backoff."""
        now, wait = time.monotonic(), RETRY_FIRST if self.owed is None else min(self.owed[1] * 2, RETRY_MOST)
        self.owed = (now + wait, wait)

    def retry(self):
        """Run the owed catch-up once its backoff has passed: subscribe again and deliver the head. The hint
        socket's thread calls this each time it wakes; it is a retry of a delivery known to have failed, and
        with nothing owed it calls nothing. Returns the delivery's answer, or None when nothing was run."""
        owed = self.owed
        if owed is None or time.monotonic() < owed[0]:
            return None
        self._due = True
        return self.deliver(None)


def _unavailable(answer):
    """Whether a delivery's answer is the service's unavailability (a failure worth retrying), not a judgment."""
    return isinstance(answer, dict) and str(answer.get('refusal') or '').startswith('unavailable_service')


def _peer_uid(conn):
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    except (OSError, AttributeError):
        return None
    return struct.unpack('3i', raw)[1]


class Hints:
    """The API's hint socket: `path` in a 0700 directory, 0600, one hint per connection from a peer the
    kernel says is this account, each handed to `deliver` in arrival order on one thread. The thread wakes
    at least every 0.25 s; each time it calls `retry`, which runs a catch-up only when one is owed."""

    def __init__(self, path, deliver, retry=None):
        self.path, self.deliver, self.retry = str(path), deliver, retry
        directory = os.path.dirname(self.path)
        os.makedirs(directory, mode=0o700, exist_ok=True)
        os.chmod(directory, 0o700)
        if os.path.lexists(self.path):
            if not stat.S_ISSOCK(os.lstat(self.path).st_mode):
                raise Unavailable('invalid_input:hints', 'the hint path is not a socket')
            os.unlink(self.path)
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(self.path)
        os.chmod(self.path, 0o600)
        self.server.listen(16)
        self.server.settimeout(0.25)
        self.outcomes, self._stop = [], threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                conn, _ = self.server.accept()
            except socket.timeout:
                conn = None
            except OSError:
                return
            if conn is not None:
                try:
                    self._one(conn)
                except Exception as exc:  # noqa: BLE001 - one bad hint never stops the listener
                    self.outcomes.append({'refusal': 'unknown_outcome:' + type(exc).__name__})
                finally:
                    conn.close()
            if self.retry is not None:
                try:
                    retried = self.retry()
                except Exception as exc:  # noqa: BLE001 - a failed retry is owed again, never fatal
                    retried = {'refusal': 'unknown_outcome:' + type(exc).__name__}
                if retried is not None:
                    self.outcomes.append(retried)
            del self.outcomes[:-256]

    def _one(self, conn):
        if _peer_uid(conn) != os.getuid():
            self.outcomes.append({'refusal': 'unauthorized:hint_peer'})
            return
        conn.settimeout(5)
        chunks, total = [], 0
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > HINT_LIMIT:
                self.outcomes.append({'refusal': 'invalid_input:hint_size'})
                return
            chunks.append(chunk)
        try:
            hint = json.loads(b''.join(chunks).decode('utf-8'))
        except (UnicodeDecodeError, ValueError):
            self.outcomes.append({'refusal': 'invalid_input:hint'})
            return
        self.outcomes.append(self.deliver(hint))

    def close(self):
        self._stop.set()
        self.server.close()
        self.thread.join(5)
        try:
            if stat.S_ISSOCK(os.lstat(self.path).st_mode):
                os.unlink(self.path)
        except OSError:
            pass


class Opened:
    """The constructed API process: the API, its service authority, its signer and its hint socket."""

    def __init__(self, api, authority, signer, hints, listen):
        self.api, self.authority, self.signer, self.hints, self.listen = api, authority, signer, hints, listen

    def close(self):
        self.hints.close()


def load_config(path):
    """The API process configuration: this account's own 0600 regular file with exactly its fields."""
    try:
        info = os.lstat(str(path))
    except OSError:
        raise Unavailable('missing_authority:api_process:absent', str(path)) from None
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise Unavailable('invalid_input:api_process:mode', str(path))
    try:
        config = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        raise Unavailable('invalid_input:api_process:unreadable', str(path)) from None
    if not isinstance(config, dict) or config.get('schema') != SCHEMA or set(config) != set(FIELDS):
        raise Unavailable('invalid_input:api_process:schema', 'exactly the %s fields' % SCHEMA)
    return config


def open_api(config_path, clock=time.time):
    """THE PRODUCTION CONSTRUCTION of the API process: the ControlApi whose authority is the service
    socket, subscribed for the service's hints. Starts no listener (serve does)."""
    config = load_config(config_path)
    workspace = os.path.realpath(config['workspace'])
    try:
        trust = EL.load_host_trust(config['host_trust'])
    except EL.Stopped as exc:
        raise Unavailable('missing_authority:host_trust:' + str(getattr(exc, 'reason', 'unreadable'))) from None
    binding = CE.read_binding(workspace) if trust is not None else None
    if trust is None or binding is None:
        raise Unavailable('missing_authority:enrollment', 'the API names an enrolled workspace of this host')
    verify = trust.verifier(binding.get('enrolled_by'), workspace)
    signer_config = config['signer'] if isinstance(config['signer'], dict) else {}
    signer = SG.ApiSigner(signer_config.get('config'), signer_config.get('edge_key_id'), signer_config.get('connection_key'))
    authority = ServiceAuthority(workspace, verify, trust.host_identity, signer.request)
    api = API.ControlApi(config['api'], authority, signer, clock=clock)
    hints = Hints(Path(config['api']['state_dir']) / HINT_NAME, authority.deliver, authority.retry)
    try:
        head = authority.connect(hints.path, api)
    except Exception:
        hints.close()
        raise
    # The head the subscription answered sets the cursor from the start (a failure is owed and retried).
    if type(head.get('watermark')) is int and head['watermark'] > 0:
        authority.deliver(head)
    return Opened(api, authority, signer, hints, config['listen'])


def serve(config_path):
    """Run the API process: the service-backed API on its loopback listener until interrupted."""
    opened = open_api(config_path)
    listen = opened.listen if isinstance(opened.listen, dict) else {}
    server = API.listen(opened.api, listen.get('host'), listen.get('port'))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        opened.close()


def main(argv):
    if len(argv) != 3 or argv[1] != 'serve':
        print('usage: control_client_api.py serve <api process configuration>')
        return 64
    serve(argv[2])
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
