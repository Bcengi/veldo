"""A signed remote worker client. No store, authority keys or mutation fallback.

workspace is the explicit enrolled Linux workspace coordinate. The remote clone
is a separate execution path. ssh_argv is fixed operator configuration naming the
existing 0108 relay, never constructed from an untrusted request.
"""
import importlib.util
import json
import os
import random
from pathlib import Path
import subprocess
import time
import uuid


def organ(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CC = organ('control_client')
COMMAND_NAMESPACE = 'veldo-worker-command'
OPERATIONS = ('worker_claim', 'worker_launch', 'worker_result', 'worker_release', 'worker_status')


def durable_json(path, value):
    """Replace a trusted host record, syncing both its contents and directory entry."""
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w') as stream:
        os.chmod(temporary, 0o600)
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def remote_request(workspace, binding, command, sign):
    """CC.build_request for a coordinate on another host. The enrolled Linux workspace is sent
    exactly as configured: build_request canonicalizes it against this machine's filesystem, and on
    a Mac /tmp is /private/tmp, so the authority would be asked for a workspace it never enrolled."""
    if not isinstance(workspace, str) or not workspace.startswith('/'):
        raise Refused('invalid_input:workspace')
    request = dict(schema=CC.REQUEST_SCHEMA, workspace=workspace, domain_uuid=binding['domain_uuid'],
                   store_uuid=binding['store_uuid'], command=command)
    request.update({k: binding[k] for k in CC.IDENTITY_FIELDS})
    request['signature'] = sign(CC.signed_bytes(request))
    return request


class Client:
    def __init__(self, workspace, binding, principal, sign, ssh_argv, *, timeout=30, signing_key=None):
        self.workspace, self.binding, self.principal = workspace, binding, principal
        self.sign, self.argv, self.timeout = sign, list(ssh_argv), timeout
        self.signing_key = str(Path(signing_key).resolve()) if signing_key else None
        self.watermark = None
        self.sent = []
        self.outbox = None
        self.retry_seconds = 1
        self.retry_max_seconds = 300
        self.retry_attempts = 8

    def send(self, operation, parameters):
        if operation not in OPERATIONS:
            raise Refused('invalid_input:worker_operation')
        command = dict(command_id=str(uuid.uuid4()), principal=self.principal, operation=operation,
                       parameters=parameters, **{k: self.binding[k] for k in
                       ('domain_uuid', 'store_uuid', 'repository_uuid')})
        packet = dict(command=command, signature=self.sign(json.dumps(command, sort_keys=True,
                       separators=(',', ':'), ensure_ascii=True, default=str).encode(), COMMAND_NAMESPACE))
        request = remote_request(self.workspace, self.binding, packet, self.sign)
        if operation == 'worker_result' and self.outbox is not None:
            durable_json(self.outbox, request)
            return self.retry_result()
        if operation == 'worker_status':
            return self.retry(request)
        return self.deliver(request)

    def retry_result(self):
        """Bounded exponential retry; exhaustion leaves the same command for restart."""
        request = json.loads(Path(self.outbox).read_text())
        response = self.retry(request)
        durable_json(str(self.outbox) + '.ack', response)
        return response

    def retry(self, request):
        for attempt in range(self.retry_attempts):
            try:
                response = self.deliver(request)
            except Refused as error:
                if not error.code.startswith('AUTHORITY_UNAVAILABLE:'):
                    raise
                if attempt + 1 == self.retry_attempts:
                    raise
                delay = min(self.retry_max_seconds, self.retry_seconds * 2 ** attempt)
                time.sleep(random.uniform(delay / 2, delay))
                continue
            return response

    def deliver(self, request):
        wire = json.dumps(request).encode()
        self.sent.append(request)
        try:
            result = subprocess.run(self.argv, input=wire, capture_output=True, timeout=self.timeout)
            if result.returncode:
                raise OSError('relay_unavailable')
            answer = json.loads(result.stdout)
        except (OSError, subprocess.TimeoutExpired, ValueError) as error:
            raise Refused('AUTHORITY_UNAVAILABLE:%s:watermark=%s:%s' % (
                CC.service_id(self.binding), self.watermark, CC.start_guidance(self.binding))) from error
        if answer.get('store_uuid') != self.binding['store_uuid']:
            raise Refused('binding_mismatch:authority')
        if not answer.get('accepted'):
            raise Refused(answer.get('reason', 'unknown_outcome'))
        self.watermark = answer.get('watermark')
        response = answer.get('result') or {}
        if not response.get('ok'):
            raise Refused(response.get('reason', 'unknown_outcome'))
        return response

    def claim(self, dispatch):
        return self.send('worker_claim', dict(dispatch_id=dispatch))

    def launch(self, binding, phase, **fields):
        return self.send('worker_launch', dict(binding, phase=phase, **fields))

    def result(self, binding, observation, *, usage=None, references=None):
        return self.send('worker_result', dict(binding, observation=observation,
                                               usage=usage, references=references or {}))

    def release(self, binding, *, reason, cleanup):
        return self.send('worker_release', dict(binding, reason=reason, cleanup=cleanup))

    def status(self, dispatch):
        return self.send('worker_status', dict(dispatch_id=dispatch))
