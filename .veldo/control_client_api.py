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
`ServiceAuthority.connect` subscribes that socket; when an answer names another service instance (the
authority restarted and forgot its subscribers), it subscribes again and delivers the head's hint, so
the API reconciles every record after its cursor.

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
        self._delivering = threading.Lock()

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
            self._resubscribe()
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
        return {k: result.get(k) for k in ('schema', 'domain_uuid', 'repository_uuid', 'store_uuid', 'command_id',
                                           'record_digest', 'watermark')}

    def _resubscribe(self):
        """A new service instance: subscribe again, then deliver the head so every record after the
        API's cursor is reconciled."""
        hint = self._subscribe()
        if type(hint.get('watermark')) is int and hint['watermark'] > 0:
            self.deliver(hint)

    def deliver(self, hint):
        """One hint to the API's deliver, one at a time (the hint socket and a reconnect share it)."""
        if self.api is None:
            return {'refusal': 'unavailable_service:not_connected'}
        with self._delivering:
            return self.api.deliver(hint)


def _peer_uid(conn):
    try:
        raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    except (OSError, AttributeError):
        return None
    return struct.unpack('3i', raw)[1]


class Hints:
    """The API's hint socket: `path` in a 0700 directory, 0600, one hint per connection from a peer the
    kernel says is this account, each handed to `deliver` in arrival order on one thread."""

    def __init__(self, path, deliver):
        self.path, self.deliver = str(path), deliver
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
                continue
            except OSError:
                return
            try:
                self._one(conn)
            except Exception as exc:  # noqa: BLE001 - one bad hint never stops the listener
                self.outcomes.append({'refusal': 'unknown_outcome:' + type(exc).__name__})
            finally:
                conn.close()
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
    hints = Hints(Path(config['api']['state_dir']) / HINT_NAME, authority.deliver)
    try:
        authority.connect(hints.path, api)
    except Exception:
        hints.close()
        raise
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
