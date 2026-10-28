"""VELDO-0112: client boundary, live adapters and fresh consumer inventories.

Only this ticket's three rows run. The supplied authority uses real enrollment,
OpenSSH signatures, AF_UNIX, claim receiver, store and dispatch transitions.
The relay leg calls the production byte carrier; it does not qualify sshd.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time

ROWS = ('clients/registry-is-the-boundary', 'clients/every-registration-is-drivable',
        'clients/registry-growth-expands-cases')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuthorityFixture:
    def __init__(self, root, runtime, scratch):
        self.root, self.runtime, self.scratch = root, runtime, scratch
        self.cc = runtime.load_client_module('control_client')
        self.cl = runtime.load_client_module('control_claim_client')
        self.d = runtime.load_client_module('control_dispatch')
        self.en = self.cl.E
        self.cm = load(root / '.veldo/control_claim.py', 'clients_claim_authority')
        self.s = self.cm.S
        self.sig = load(root / '.veldo/control_signer.py', 'clients_signer')
        self.db = scratch / 'authority/control.sqlite3'
        self.conn = self.s.open_store(str(self.db))
        self.serial = 0
        self.key = scratch / 'key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.key)],
                       check=True, capture_output=True)
        self.public = self.key.with_suffix('.pub').read_text().strip()
        self.workspace = scratch / 'workspace'
        self.workspace.mkdir()
        self.gp = load(root / '.veldo/git_process.py', 'clients_git')
        self.gp.run(['git', 'init', '-q', str(self.workspace)], check=True, capture_output=True)
        self.gp.run(['git', '-C', str(self.workspace), '-c', 'commit.gpgsign=false',
                     'commit', '-q', '-' * 2 + 'allow-empty', '-m', 'fixture'],
                    identity=('Fixture', 'fixture@example.invalid'), check=True, capture_output=True)
        self.ids = dict(domain_uuid='clients-domain', repository_uuid='clients-repository', store_uuid='clients-store')
        self.en.enroll(str(self.workspace), self.ids['domain_uuid'], self.ids['store_uuid'], str(self.db),
                       'clients-host', 1, self.sign, 'owner', time.time(), repository_uuid=self.ids['repository_uuid'])
        self.put('owner', 'membership', dict(principal_type='person', roles=['project_owner'], scope='*'))
        self.put('worker', 'membership', dict(principal_type='agent_run', roles=[], scope='*'))
        self.put('service', 'membership', dict(principal_type='service', roles=['reservation_service'], scope='*'))
        self.put('key-worker', 'verification_key', dict(principal='worker', public_key=self.public, effective_at=0))
        self.put('project:clients', 'project', dict(name='clients', state='ACTIVE', owner='owner'))
        self.put('backlog', 'backlog_item', dict(state='PRIORITIZED', repository_uuid=self.ids['repository_uuid']))
        self.put('unit', 'execution_unit', dict(state='READY', project='clients', backlog_item_uuid='backlog',
                 repository_uuid=self.ids['repository_uuid'], requirements=[], eligible_holders=['worker']))
        self.client = self.cl.Client(self.workspace, 'worker', self.sign, self.verify, 'clients-host')
        self.dispatches = self.d.Dispatches(self.s, self.conn, domain=self.ids['domain_uuid'],
                  repository=self.ids['repository_uuid'], principal='service', signer='service', sign=self.sign)
        self.reservations = self.d.RES.Reservations(self.s, self.conn, domain=self.ids['domain_uuid'],
                  repository=self.ids['repository_uuid'], principal='service', signer='service', sign=self.sign,
                  authorize=lambda conn, command: command['principal'] == 'service')
        for scope, subject in [('account', 'account'), ('project', 'clients'), ('unit', 'unit')]:
            self.reservations.configure('policy-' + scope, scope, subject,
                                        dict(capacity=10, invocations=10, wall_seconds=100), now=time.time())
        binding = self.en.read_binding(str(self.workspace))
        self.address = self.cc.socket_path_for(binding)
        self.socket = self.cc.bind(self.address)
        self.socket.settimeout(.05)
        self.stop = threading.Event()
        self.errors = []
        self.server = threading.Thread(target=self.serve)
        self.server.start()

    def sign(self, data):
        return self.sig.sign_bytes(self.key, data, self.cm.AC.SIGNATURE_NAMESPACE)

    def verify(self, data, signature):
        return self.cm.AC.ssh_keygen_verify(data, signature,
                   self.cm.AC.allowed_signers_line('worker', self.public), 'worker')[0]

    def command(self, identity):
        self.serial += 1
        return dict(command_id='fixture-' + str(self.serial), nonce='fixture-' + str(self.serial),
                    principal='owner', operation='upsert_entity', artifact_digests=[],
                    expected_versions={identity: 0}, parameters=dict(entity_id=identity, kind='fixture', data={'ok': True}))

    def put(self, identity, kind, data):
        command = self.command(identity)
        command['parameters'].update(kind=kind, data=data)
        return self.s.execute(self.conn, command, 'owner', self.sign, 1)

    def serve(self):
        conn = self.s.open_store(str(self.db))
        receiver = self.cm.Receiver(conn, self.ids, 'owner', self.sign)
        def apply(packet):
            if 'command' in packet:
                return receiver.apply(packet)
            return self.s.execute(conn, packet, 'owner', self.sign, 1)
        authority = self.cc.Authority(self.ids['store_uuid'], self.ids['domain_uuid'], str(self.db),
                                      self.en, self.verify, 'clients-host', apply)
        try:
            while not self.stop.is_set():
                try:
                    self.cc.serve_one(self.socket, authority, timeout=.05)
                except TimeoutError:
                    pass
        except Exception as error:
            self.errors.append(repr(error))
        finally:
            conn.close()

    def arguments(self, entrypoint, transport):
        self.entrypoint = entrypoint
        args = self._arguments(entrypoint, transport)
        self.before_seq = self.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        return args

    def _arguments(self, entrypoint, transport):
        if entrypoint.endswith(':qualify.<locals>.extension'):
            return (self,), {}
        if entrypoint.startswith(('claim:', 'control_claim_client:')):
            action = entrypoint.rsplit(':', 1)[1].split('.')[-1]
            # Every operation gets the prerequisite it actually consumes.
            held = self.client.holder('unit')
            if action == 'claim':
                if held is not None:
                    assert self.client.release('unit', 'worker')
            elif held is None:
                assert self.client.claim('unit', 'worker') == (True, 'granted')
            if entrypoint == 'control_claim_client:Client.request':
                return (self.client, 'renew', 'unit', self.client.generations['unit']), {}
            if entrypoint.startswith('claim:'):
                return ('unit', 'worker'), dict(root=self.client)
            if action == 'use':
                return (self.client, 'unit'), {}
            return (self.client, 'unit', 'worker'), {}
        if entrypoint == 'control_client:send':
            return (self.workspace, self.command('command-' + str(self.serial)), self.en, self.verify,
                    self.sign, 'clients-host'), {}
        if entrypoint.startswith('control_relay:'):
            import io
            packet = self.cc.build_request(self.workspace, self.en.read_binding(str(self.workspace)),
                                           self.command('relay-' + str(self.serial)), self.sign)
            payload = json.dumps(packet).encode()
            if entrypoint.endswith(':main'):
                self.relay_output = io.BytesIO()
                return (['relay', self.address],), dict(stdin=io.BytesIO(payload), stdout=self.relay_output, stderr=io.StringIO())
            return (self.address, payload), {}
        if entrypoint.startswith('control_dispatch:'):
            action = entrypoint.rsplit('.', 1)[1]
            contract = self.contract()
            if action == 'prepare':
                return (self.dispatches, contract), dict(now=time.time())
            self.dispatches.prepare(contract, now=time.time())
            dispatch, digest = contract['dispatch_id'], self.d.digest(contract)
            process = dict(platform='linux', host='fixture', boot_id='fixture-boot', pid=1, start='1')
            if action == 'accept':
                return (self.dispatches, dispatch, digest, dict(process, principal='service')), dict(now=time.time())
            if action in ('run', 'exit', 'unknown'):
                self.dispatches.accept(dispatch, digest, dict(process, principal='service'), now=time.time())
            if action == 'run':
                return (self.dispatches, dispatch, digest, process), dict(now=time.time())
            if action == 'exit':
                self.dispatches.run(dispatch, digest, process, now=time.time())
                end = dict(returncode=0, signal=None, output_digest='sha256:' + '0'*64, output_bytes=0, deadline_stop=False)
                return (self.dispatches, dispatch, digest, process, end), dict(now=time.time())
            return (self.dispatches, dispatch, digest, 'fixture-observation'), dict(now=time.time())
        if entrypoint.startswith('dispatch:'):
            return self.orchestrator_arguments(entrypoint)
        raise ValueError('unprepared entrypoint: ' + entrypoint)

    def contract(self):
        dispatch = 'dispatch-' + str(self.serial)
        self.serial += 1
        unit = dispatch + '-unit'
        self.reservations.configure('policy-' + unit, 'unit', unit,
                                    dict(capacity=10, invocations=10, wall_seconds=100), now=time.time())
        self.reservations.reserve_worker('reserve-' + dispatch, dispatch, 'account', 'clients', unit, now=time.time())
        slot_id = self.d.RES.entity('worker', [self.ids['domain_uuid'], dispatch])
        slot = self.s.materialized_state(self.conn)['entities'][slot_id]
        contract = dict(schema=self.d.SCHEMA, dispatch_id=dispatch, domain=self.ids['domain_uuid'],
            repository=self.ids['repository_uuid'], unit=unit, station='review', attempt=1,
            source={k: self.gp.check_output(['git', '-C', str(self.workspace), 'rev-parse', 'HEAD^{'+k+'}'],
                                           text=True).strip() for k in ('commit', 'tree')},
            input=dict(decision=dict(decision_id='fixture-review', station='review', unit=unit,
                                     inputs={'unit': {'version': 1}}), context={}, payload={}, payload_digest=self.d.digest({})),
            capability=dict(adapter='fixture', configuration={}, configuration_digest=self.d.digest({})),
            reservation=dict(entity=slot_id, version=slot['version'], digest=slot['digest'], account='account', project='clients'),
            claim=None, deadline=time.time()+60, authority_generation=1)
        self.dispatch_id = dispatch
        return contract

    def orchestrator_arguments(self, entrypoint):
        # These are the dispatcher's documented external control-logic seams,
        # not worker, eligibility or proof-service qualification. Admission itself
        # is independently exercised above through the real dispatch store writer.
        import contextlib
        from types import SimpleNamespace
        dsp = self.runtime.load_client_module('dispatch')
        fixture = self
        class Hooks(dsp.EX.LoopSteps):
            root = fixture.workspace
            def resolve(self, sid):
                return dict(id=sid, status='ready')
            def build(self, spec, calls=None):
                return dict(ok=True, commit='a'*40)
            def gate(self):
                return dict(green=True, detail='external fixture gate observation')
            def assemble_proof(self, spec, build):
                return dict(fixture=True)
            def validate_proof(self, proof):
                return True, []
            def emit(self, *args, **kwargs):
                pass
        sid = 'fixture-dispatch-' + str(self.serial)
        self.serial += 1
        def accept_build(unit, **fields):
            self.put(unit, 'fixture_floor', dict(state='review', **fields))
        floor = SimpleNamespace(record=lambda unit: None, accept_build=accept_build,
                                publish=lambda unit: {'unit': unit, 'state': 'review'})
        gate = SimpleNamespace(decide=lambda *args, **kwargs: dict(eligible=True, refusals=[]))
        calls = SimpleNamespace(launch=lambda *args, **kwargs: contextlib.nullcontext())
        kwargs = dict(repo_root=self.workspace, hooks=Hooks(), eligibility=gate, calls=calls, authority=floor)
        unit = dict(kind='build', spec=sid, holder='worker', generation=1)
        if entrypoint == 'dispatch:veldo_dispatch':
            return (unit,), kwargs
        return (dsp.Dispatcher(**kwargs), unit), {}

    def accepted(self, case, result):
        after = self.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        if after <= self.before_seq:
            return False
        if case.client == 'extension':
            return bool(result)
        if case.client == 'claim':
            if isinstance(result, tuple):
                return result == (True, 'granted')
            return result.get('ok') is True if isinstance(result, dict) else result is True
        if case.client == 'command':
            if case.adapter.entrypoint == 'control_relay:main':
                if result != 0:
                    return False
                result = self.relay_output.getvalue()
            if case.transport == 'relay':
                result = json.loads(result)
            return result.get('accepted') is True and bool(result.get('result'))
        if case.adapter.entrypoint.startswith('dispatch:'):
            return result.get('ok') is True and result.get('status') == 'review'
        return bool(result) and self.dispatches.record(self.dispatch_id) is not None

    def identity(self):
        binding = self.en.read_binding(str(self.workspace))
        return {k: binding[k] for k in ('domain_uuid', 'store_uuid', 'repository_uuid', 'clone_uuid', 'binding_digest')}

    def close(self):
        self.stop.set()
        self.server.join()
        self.socket.close()
        self.conn.close()
        if self.errors:
            raise RuntimeError(self.errors)


def qualify(root):
    fixture = load(root / 'scripts/fixtures/registered_clients.py', 'clients_fixture')
    runtime = fixture.registry(root)
    rows, detail = {}, {}
    problems = fixture.boundary_problems(runtime)
    for name in (*runtime.MODULES, 'control_client_registry', 'init_scaffold'):
        if (root / '.veldo' / (name + '.py')).read_bytes() != (root / 'engine/.veldo' / (name + '.py')).read_bytes():
            problems.append('engine_copy_differs:' + name)
    try:
        installer = load(root / '.veldo/init_scaffold.py', 'clients_installer')
        service = load(root / '.veldo/control_service.py', 'clients_service_closure')
        if '.veldo/control_client_registry.py' not in installer._FILES:
            problems.append('registry_not_scaffolded')
        if 'control_client_registry.py' not in service.closure():
            problems.append('registry_not_installed')
    except Exception as error:
        problems.append('installation:' + repr(error))
    # Both direct and identity dispatch reject a handle after removal. A new
    # registration with the same callable identity but another client is rejected.
    record = runtime._state.entries.pop('claim:claim', None)
    checks = []
    boundary_scratch = tempfile.TemporaryDirectory(prefix='v112-boundary-')
    try:
        for call in (lambda: runtime.load_client_module('claim').claim('unit', 'worker', root=boundary_scratch.name),
                     lambda: runtime.invoke('claim:claim', 'unit', 'worker')):
            try:
                call()
                checks.append(False)
            except runtime.RegistryError as error:
                checks.append(error.code == 'unregistered_entrypoint')
            except Exception:
                checks.append(False)
    finally:
        if record:
            runtime._state.entries['claim:claim'] = record
    boundary_scratch.cleanup()
    if record:
        try:
            runtime.entrypoint('different-client', ('local_ipc',))(record['callable'].__wrapped__)
            checks.append(False)
        except runtime.RegistryError as error:
            checks.append(error.code == 'duplicate_client')
    rows[ROWS[0]] = not problems and all(checks)
    detail['boundary'] = dict(problems=problems, controls=checks, registrations=runtime.registrations())
    try:
        with tempfile.TemporaryDirectory(prefix='v112-') as temporary:
            authority = AuthorityFixture(root, runtime, Path(temporary))
            try:
                evidence, results = fixture.exercise(runtime, authority, consumer='live-positive-control')
                detail['live'] = evidence
                rows[ROWS[1]] = True
            finally:
                authority.close()
    except Exception as error:
        rows[ROWS[1]] = False
        detail['live'] = dict(error=repr(error))
    original = dict(runtime._state.entries)
    base_inventory = fixture.cases(runtime) if rows[ROWS[1]] else ()
    try:
        @runtime.entrypoint('extension', ('local_ipc',))
        def extension(authority):
            return authority.put('plugin-operation', 'fixture', {'accepted': True})
        adapter = fixture.Adapter('extension-v1', extension.client_entrypoint)
        extra = {(extension.client_entrypoint, 'local_ipc'): adapter}
        inventories = [fixture.cases(runtime, extra) for _ in range(2)]
        controls = [any(c.client == 'extension' for c in inv) for inv in inventories]
        receipts = []
        for consumer in ('lifecycle-consumer', 'refusal-consumer'):
            with tempfile.TemporaryDirectory(prefix='v112-consumer-') as temporary:
                authority = AuthorityFixture(root, runtime, Path(temporary))
                try:
                    observed, results = fixture.exercise(runtime, authority, consumer=consumer, extra_adapters=extra)
                    receipts.append(observed)
                finally:
                    authority.close()
        controls.append(receipts[0]['registration_digest'] == receipts[1]['registration_digest'])
        # An inventory obtained before plugin loading is no longer current.
        try:
            fixture.receipt(runtime, base_inventory, [c.identity for c in base_inventory], consumer='stale')
            controls.append(False)
        except runtime.RegistryError as error:
            controls.append(error.code == 'incomplete_inventory')
        # A caller cannot silently submit a handwritten smaller execution list.
        try:
            fixture.receipt(runtime, inventories[0], [c.identity for c in inventories[0]][:-1], consumer='filtered')
            controls.append(False)
        except runtime.RegistryError as error:
            controls.append(error.code == 'incomplete_inventory')
        # New production registration without an adapter must refuse.
        try:
            fixture.cases(runtime)
            controls.append(False)
        except runtime.RegistryError as error:
            controls.append(error.code == 'missing_fixture_adapter')
        runtime._state.entries.clear()
        for invoke in (lambda: fixture.cases(runtime, extra),
                       lambda: fixture.receipt(runtime, (), (), consumer='empty')):
            try:
                invoke()
                controls.append(False)
            except runtime.RegistryError as error:
                controls.append(error.code == 'vacuous_client_set')
        rows[ROWS[2]] = all(controls)
        detail['growth'] = dict(controls=controls, receipts=receipts)
    except Exception as error:
        rows[ROWS[2]] = False
        detail['growth'] = dict(error=repr(error))
    finally:
        runtime._state.entries.clear()
        runtime._state.entries.update(original)
    return dict(rows=rows, detail=detail)


if 'expect' in globals():
    _clients_result = qualify(Path(ROOT))
    for _clients_row, _clients_passed in _clients_result['rows'].items():
        expect('VELDO-0112 ' + _clients_row, _clients_passed)
elif __name__ == '__main__':
    import sys
    result = qualify(Path(__file__).resolve().parents[2])
    print(json.dumps(result, indent=2))
    sys.exit(0 if all(result['rows'].values()) else 1)
