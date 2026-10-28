"""Reusable inventory and public-entry adapters for VELDO-0112 consumers.

The caller supplies the enrolled authority fixture. No store, authority lifecycle,
SSH authentication or refusal behavior is simulated here. Call arguments are
supplied by that fixture; adapters always invoke a registered public callable.
"""
import ast
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path

VERSION = 'veldo.registered_clients/v1'


def registry(root):
    path = Path(root) / '.veldo' / 'control_client_registry.py'
    spec = importlib.util.spec_from_file_location('fixture_client_registry', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.load_clients()
    return module


@dataclass(frozen=True)
class Adapter:
    identity: str
    entrypoint: str

    def invoke(self, runtime, authority, transport):
        args, kwargs = authority.arguments(self.entrypoint, transport)
        return runtime.invoke(self.entrypoint, *args, **kwargs)


# Adapter declarations are joined to the production registry, never used to
# enumerate cases. A plugin must supply its own adapter or the join refuses.
def adapters():
    paths = {
        'claim:claim': 'local_ipc', 'claim:heartbeat': 'local_ipc', 'claim:release': 'local_ipc',
        'control_claim_client:Client.request': 'local_ipc',
        'control_claim_client:Client.claim': 'local_ipc',
        'control_claim_client:Client.heartbeat': 'local_ipc',
        'control_claim_client:Client.release': 'local_ipc',
        'control_claim_client:Client.use': 'local_ipc',
        'control_client:send': 'local_ipc',
        'control_relay:forward': 'relay', 'control_relay:main': 'relay',
        'control_dispatch:Dispatches.prepare': 'in_process',
        'control_dispatch:Dispatches.accept': 'in_process',
        'control_dispatch:Dispatches.run': 'in_process',
        'control_dispatch:Dispatches.exit': 'in_process',
        'control_dispatch:Dispatches.refuse': 'in_process',
        'control_dispatch:Dispatches.unknown': 'in_process',
        'dispatch:Dispatcher.dispatch': 'in_process', 'dispatch:veldo_dispatch': 'in_process',
    }
    return {(entry, mode): Adapter(entry + '-v1', entry) for entry, mode in paths.items()}


@dataclass(frozen=True)
class Case:
    client: str
    transport: str
    adapter: Adapter
    registration_digest: str
    implementation_digest: str

    @property
    def identity(self):
        return self.adapter.entrypoint + '/' + self.transport

    def invoke(self, runtime, authority):
        if runtime.digest() != self.registration_digest:
            raise runtime.RegistryError('inventory_changed', self.identity)
        return self.adapter.invoke(runtime, authority, self.transport)


def cases(runtime, extra_adapters=None):
    records = runtime.registrations()
    if not records:
        raise runtime.RegistryError('vacuous_client_set')
    product = {(r['identity'], t) for r in records for t in r['transports']}
    drivers = adapters()
    drivers.update(extra_adapters or {})
    if product != set(drivers):
        missing = sorted(product - set(drivers))
        extra = sorted(set(drivers) - product)
        raise runtime.RegistryError('missing_fixture_adapter', repr(dict(missing=missing, extra=extra)))
    stamp = runtime.digest(records)
    result = []
    for identity, transport in sorted(product):
        adapter = drivers[identity, transport]
        choices = [r for r in records if r['identity'] == identity and transport in r['transports']]
        chosen = next((r for r in choices if r['identity'] == adapter.entrypoint), None)
        if chosen is None:
            raise runtime.RegistryError('unregistered_entrypoint', adapter.entrypoint)
        result.append(Case(chosen['client'], transport, adapter, stamp, chosen['implementation_digest']))
    return tuple(result)


def receipt(runtime, inventory, executed, *, consumer):
    """Reject filtered, duplicate, stale or invented executions, before issuing evidence."""
    records = runtime.registrations()
    expected = {r['identity'] + '/' + t for r in records for t in r['transports']}
    exported = [case.identity for case in inventory]
    stamp = runtime.digest(records)
    if not expected:
        raise runtime.RegistryError('vacuous_client_set')
    if (set(exported) != expected or len(exported) != len(expected)
            or set(executed) != expected or len(executed) != len(expected)):
        raise runtime.RegistryError('incomplete_inventory', repr(dict(
            registered=sorted(expected), exported=exported, executed=list(executed))))
    if any(case.registration_digest != stamp for case in inventory):
        raise runtime.RegistryError('inventory_changed')
    return dict(schema=VERSION, consumer=consumer, registration_digest=stamp,
                fixture_digest=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                registered=sorted(expected), exercised=sorted(executed), missing=[],
                cases=[dict(identity=c.identity, entrypoint=c.adapter.entrypoint,
                            adapter=c.adapter.identity, transport=c.transport,
                            implementation_digest=c.implementation_digest) for c in inventory])


def exercise(runtime, authority, *, consumer, extra_adapters=None):
    inventory = cases(runtime, extra_adapters)
    executed, results = [], {}
    for case in inventory:
        result = case.invoke(runtime, authority)
        if not authority.accepted(case, result):
            raise runtime.RegistryError('positive_control_refused', case.identity)
        executed.append(case.identity)
        results[case.identity] = result
    evidence = receipt(runtime, inventory, executed, consumer=consumer)
    evidence['input_identity'] = authority.identity()
    return evidence, results


# Independently discover callers of mutation sinks in the named client surfaces.
# Internal authority writers are not clone clients. New plugins are audited from
# the files they register; their public registered callable must retain its guard.
SURFACES = {
    'claim': ('', {'_publish', 'os.remove', 'client.claim', 'client.heartbeat', 'client.release'}),
    'control_client': ('', {'conn.sendall'}),
    'control_claim_client': ('Client', {'IPC.send'}),
    'control_relay': ('', {'conn.sendall'}),
    'control_dispatch': ('Dispatches', {'self.store.execute'}),
    'dispatch': ('Dispatcher', {'self._dispatch_build', 'self._dispatch_review'}),
}
# These calls explicitly request inspection; the transport's send is intentionally
# registered, since its payload can also be a mutation.
READS = {('control_client', 'inspect'), ('control_claim_client', 'holder')}
AUTHORITY_SERVERS = {('control_client', 'serve_one'), ('control_client', 'serve_forever')}


def boundary_problems(runtime):
    problems = []
    records = runtime.registrations()
    if not records:
        return ['vacuous_client_set']
    if not {'claim', 'command', 'dispatch-admission'} <= {r['client'] for r in records}:
        problems.append('missing_required_client')
    for name, (scope, sinks) in SURFACES.items():
        module = runtime.load(name)
        tree = ast.parse(Path(module.__file__).read_text())
        owner = getattr(module, scope) if scope else module
        nodes = tree.body if not scope else next(n.body for n in tree.body
                                                 if isinstance(n, ast.ClassDef) and n.name == scope)
        functions = {n.name: n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        calls = {key: {ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)}
                 for key, node in functions.items()}
        mutating = set()
        while True:
            expanded = {key for key, values in calls.items()
                        if values & (sinks | mutating | {'self.' + n for n in mutating})}
            if expanded <= mutating:
                break
            mutating |= expanded
        for key in sorted(mutating):
            if not key.startswith('_') and (name, key) not in READS | AUTHORITY_SERVERS:
                if not runtime.registered(getattr(owner, key)):
                    problems.append('unregistered_entrypoint:' + name + ':' + key)
    # The module-level dispatcher is an alias front door, outside its class scope.
    if not runtime.registered(runtime.load('dispatch').veldo_dispatch):
        problems.append('unregistered_entrypoint:dispatch:veldo_dispatch')
    for record in records:
        handles = runtime._state.entries[record['identity']]['handles']
        if not handles or any(not runtime.registered(h) for h in handles):
            problems.append('unregistered_entrypoint:' + record['identity'])
    return problems
