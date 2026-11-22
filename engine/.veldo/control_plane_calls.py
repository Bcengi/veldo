"""Service-owned outside calls: keystore custody, accepted settings and safe observations.

The process binding is memory only and PID bound: neither exec nor fork delivers
it to a run. It is established by the authority service and its trusted executor.
"""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
from types import ModuleType
from urllib.parse import urlsplit
import urllib.request


def organ(name):
    spec = importlib.util.spec_from_file_location('outside_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


state = sys.modules.setdefault('_veldo_control_plane', ModuleType('_veldo_control_plane'))
if not hasattr(state, 'pid'):
    state.pid, state.observe, state.commit = None, None, None
    state.calls, state.refusals = {}, {}


class Refused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def not_run(caller):
    if os.environ.get('VELDO_DISPATCH_ID') or os.environ.get('VELDO_DISPATCH_ACCEPTANCE'):
        raise Refused('unauthorized:control_plane_run:' + caller)


@contextlib.contextmanager
def service(commit, observe=None):
    """Bind the trusted service's lifetime, without an inheritable credential or flag."""
    not_run('service')
    previous = state.pid, state.commit, state.observe
    state.pid, state.commit, state.observe = os.getpid(), commit, observe
    try:
        yield
    finally:
        state.pid, state.commit, state.observe = previous


def require_service(caller):
    not_run(caller)
    if state.pid != os.getpid():
        raise Refused('unauthorized:control_plane_service:' + caller)


def emit(event):
    if state.observe:
        state.observe(event)
    else:
        print(json.dumps(event, sort_keys=True), file=sys.stderr)


def reference(caller, ref):
    """Refuse without printing a possible literal. Only a parsed reference has a name."""
    match = re.fullmatch(r'([a-z]+):([A-Za-z0-9_][A-Za-z0-9_./-]*)', ref) if isinstance(ref, str) else None
    scheme = match[1] if match else 'literal'
    if scheme != 'keychain':
        state.refusals[scheme] = state.refusals.get(scheme, 0) + 1
        emit(dict(caller=caller, scheme=scheme, name=match[2] if match else None, result='refused'))
        raise Refused('invalid_input:control_plane_credential:%s:%s' % (caller, scheme))
    return organ('secretref').wire(ref)


def credential(caller, ref, resolver=None):
    reference(caller, ref)
    not_run(caller)
    if resolver is not None:
        return resolver(ref)
    return organ('secretref').resolve_for_runtime(ref, organ('control_credential_keystore').SecretService()).reveal()


def settings(key):
    """Only the loader's last accepted settings; no product or state-root fallback."""
    installation = organ('installation').load()
    return installation.accepted_settings().get(key)


def metrics():
    return {'calls': dict(state.calls), 'credential_refusals': dict(state.refusals)}


@contextlib.contextmanager
def outside(caller, destination, operation, dispatch=None):
    require_service(caller)
    started, result = time.monotonic(), 'failed'
    try:
        yield
        result = 'ok'
    finally:
        key = caller + ':' + result
        state.calls[key] = state.calls.get(key, 0) + 1
        commit = state.commit() if callable(state.commit) else state.commit
        emit(dict(caller=caller, host=urlsplit(destination).hostname, operation=operation,
                  result=result, latency=time.monotonic() - started,
                  installation_commit=commit, dispatch_id=dispatch))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@contextlib.contextmanager
def http(caller, request, timeout=120):
    """No ambient proxy and no redirect of a credential; errors contain no URL or body."""
    with outside(caller, request.full_url, request.get_method()):
        try:
            with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(
                    request, timeout=timeout) as response:
                yield response
        except Exception:
            raise Refused('unavailable_service:control_plane_call:' + caller) from None


def accepted_commit():
    installation = organ('installation').load()
    remembered = organ('installation')._accepted_state.settings.get(str(Path(installation.folder).resolve()))
    return remembered[0] if remembered else None


def service_entry(function):
    """A trusted service entry, never a run. Its children must bind their own lifetime."""
    import functools
    @functools.wraps(function)
    def entered(*args, **kwargs):
        with service(accepted_commit):
            return function(*args, **kwargs)
    return entered
