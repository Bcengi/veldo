"""Production mutation client inventory, shared by file-location imports.

Registration wraps the public callable itself. Removing a registration disables
existing handles as well as identity dispatch. This is an admission inventory,
not a sandbox against arbitrary Python execution in the authority process.
"""
import functools
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
import types

ROOT = Path(__file__).resolve().parent
_KEY = '_veldo_clients_' + hashlib.sha256(str(ROOT).encode()).hexdigest()
_state = sys.modules.setdefault(_KEY, types.ModuleType(_KEY))
if not hasattr(_state, 'entries'):
    _state.entries = {}
    _state.lock = threading.RLock()
    _state.modules = {}
    class RegistryError(RuntimeError):
        def __init__(self, code, detail=''):
            self.code, self.detail = code, detail
            super().__init__(code + (': ' + detail if detail else ''))
    _state.error = RegistryError
RegistryError = _state.error

# The normal client modules, not a list of fixture cases. Plugins register through
# entrypoint too; enumeration never discards identities not in these modules.
MODULES = ('claim', 'control_client', 'control_claim_client', 'control_relay',
           'control_dispatch', 'dispatch')


def entrypoint(client, transports):
    """Register a stable client and public entry identity; return its guarded callable."""
    def decorate(function):
        path = Path(function.__code__.co_filename).resolve()
        identity = path.stem + ':' + function.__qualname__
        modes = tuple(sorted(set(transports)))
        if not client or not modes or any(not isinstance(t, str) or not t for t in modes):
            raise RegistryError('invalid_registration', identity)
        origin = (str(path), function.__qualname__)
        with _state.lock:
            previous = _state.entries.get(identity)
            if previous and (previous['origin'] != origin or previous['client'] != client
                             or previous['transports'] != modes):
                raise RegistryError('duplicate_client', identity)
            @functools.wraps(function)
            def guarded(*args, **kwargs):
                with _state.lock:
                    current = _state.entries.get(identity)
                    if current is None or guarded not in current['handles']:
                        raise RegistryError('unregistered_entrypoint', identity)
                return function(*args, **kwargs)
            guarded.client_entrypoint = identity
            record = previous or dict(identity=identity, client=client, transports=modes,
                                      origin=origin, handles=[], callable=guarded)
            record['handles'].append(guarded)
            _state.entries[identity] = record
        return guarded
    return decorate


def load(name):
    """Normal module loading, once for each source installation."""
    with _state.lock:
        if name not in _state.modules:
            spec = importlib.util.spec_from_file_location(_KEY + '_' + name, ROOT / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _state.modules[name] = module
        return _state.modules[name]


def registrations():
    with _state.lock:
        return tuple(dict(identity=r['identity'], client=r['client'], transports=r['transports'],
                          implementation_digest=hashlib.sha256(Path(r['origin'][0]).read_bytes()).hexdigest())
                     for _, r in sorted(_state.entries.items()))


def digest(records=None):
    records = registrations() if records is None else records
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def invoke(identity, *args, **kwargs):
    with _state.lock:
        record = _state.entries.get(identity)
        if record is None:
            raise RegistryError('unregistered_entrypoint', identity)
        function = record['callable']
    return function(*args, **kwargs)


def registered(function):
    function = getattr(function, '__func__', function)
    with _state.lock:
        record = _state.entries.get(getattr(function, 'client_entrypoint', None))
        return bool(record and function in record['handles'])


def load_clients():
    for name in MODULES:
        load(name)
    return registrations()
