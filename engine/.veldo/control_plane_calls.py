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
    state.dispatch = None


class Refused(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def not_run(caller):
    if os.environ.get('VELDO_DISPATCH_ID') or os.environ.get('VELDO_DISPATCH_ACCEPTANCE'):
        raise Refused('unauthorized:control_plane_run:' + caller)


@contextlib.contextmanager
def service(commit, observe=None, dispatch=None):
    """Bind the trusted service's lifetime, without an inheritable credential or flag."""
    not_run('service')
    previous = state.pid, state.commit, state.observe, state.dispatch
    state.pid, state.commit, state.observe, state.dispatch = os.getpid(), commit, observe, dispatch
    try:
        yield
    finally:
        state.pid, state.commit, state.observe, state.dispatch = previous


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
    match = re.fullmatch(r'([a-z]+):([A-Za-z0-9_./-]+)', ref) if isinstance(ref, str) else None
    prefix = re.match(r'([a-z]+):', ref) if isinstance(ref, str) else None
    scheme = prefix[1] if prefix else 'literal'
    if scheme != 'keychain':
        state.refusals[scheme] = state.refusals.get(scheme, 0) + 1
        emit(dict(caller=caller, scheme=scheme, name=match[2] if match else None, result='refused'))
        raise Refused('invalid_input:control_plane_credential:%s:%s' % (caller, scheme))
    try:
        return organ('secretref').wire(ref)
    except ValueError:
        raise Refused('invalid_input:control_plane_credential:' + caller + ':keychain') from None


def credential(caller, ref, resolver=None):
    reference(caller, ref)
    not_run(caller)
    if resolver is not None:
        return resolver(ref)
    require_service(caller)
    return organ('secretref').resolve_for_runtime(ref, organ('control_credential_keystore').SecretService()).reveal()


def settings(key):
    """Only the loader's last accepted settings; no product or state-root fallback."""
    installation = organ('installation').load()
    return installation.accepted_settings().get(key)


def metrics():
    return {'calls': dict(state.calls), 'credential_refusals': dict(state.refusals)}


@contextlib.contextmanager
def outside(caller, destination, operation, dispatch=None, unit=None):
    require_service(caller)
    started, result, outcome = time.monotonic(), 'failed', {}
    try:
        yield outcome
        result = outcome.get('result', 'ok')
    finally:
        key = caller + ':' + result
        state.calls[key] = state.calls.get(key, 0) + 1
        commit = state.commit() if callable(state.commit) else state.commit
        emit(dict(caller=caller, host=urlsplit(destination).hostname, operation=operation,
                  result=result, latency=time.monotonic() - started,
                  installation_commit=commit, dispatch_id=dispatch or state.dispatch, unit_id=unit))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@contextlib.contextmanager
def http(caller, request, timeout=120, unit=None):
    """No ambient proxy and no redirect of a credential; errors contain no URL or body."""
    with outside(caller, request.full_url, request.get_method(), unit=unit):
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
        configuration = args[0] if args and isinstance(args[0], dict) else None
        commit = (lambda: effect_commit(configuration)) if configuration else accepted_commit
        with service(commit):
            return function(*args, **kwargs)
    return entered


def effect_commit(configuration):
    """A trusted effect child reads provenance from the accepted store record, not its environment."""
    import sqlite3
    path = configuration.get('store')
    if not path:
        return None
    try:
        with contextlib.closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as conn:
            return organ('installation').configuration_commit(conn)
    except sqlite3.Error:
        # The effect's own normal preflight reports an absent or unreadable store.
        return None
