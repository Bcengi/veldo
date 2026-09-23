"""Explicit enrolled-clone claim caller; no database or clone ledger writes.

Pass Client as claim.py's root (or Lander's claims_root). Generation is retained
from the successful claim, never refreshed from a read to make a stale holder
current. renew/release/use also accept an explicit generation for dispatched work.
The service runner supplies signing and verification callables and the host ID.
"""
import importlib.util
from pathlib import Path
import uuid


def organ(name):
    spec = importlib.util.spec_from_file_location('claim_client_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


IPC = organ('control_client')
E = organ('control_enrollment')
CL = organ('claim')


class Client:
    authority_claim_client = True

    def __init__(self, workspace, principal, sign, verify, host_identity, timeout=5):
        self.workspace, self.principal = str(workspace), principal
        self.sign, self.verify, self.host_identity = sign, verify, host_identity
        self.timeout, self.generations = timeout, {}

    def request(self, operation, unit, generation=0, capabilities=()):
        problem = CL.unit_id_problem(unit)
        if problem:
            raise CL.UnitIdError(problem)
        binding = E.read_binding(self.workspace)
        command = dict(operation=operation, unit_id=unit, principal=self.principal,
                       command_id=str(uuid.uuid4()), nonce=str(uuid.uuid4()), generation=generation,
                       capabilities=list(capabilities))
        command.update({k: binding[k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid')})
        # Same canonical encoding as the store, without importing the store into a client.
        import json
        message = json.dumps(command, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
        packet = {'command': command, 'signature': self.sign(message)}
        try:
            response = IPC.send(self.workspace, packet, E, self.verify, self.sign,
                                self.host_identity, timeout=self.timeout)
        except IPC.RoutingRefused as exc:
            raise CL.ClaimStopped(exc.reason) from exc
        if not response['accepted']:
            raise CL.ClaimStopped(response['reason'])
        result = response['result']
        if result.get('reason') in ('unanswerable', 'ownership_uncertain', 'missing_authority'):
            raise CL.ClaimStopped(result['reason'])
        return result

    def claim(self, unit, worker, worker_caps=None, requirements=None):
        if worker != self.principal:
            return False, 'not_owner'
        result = self.request('claim', unit, capabilities=worker_caps or ())
        if result['ok']:
            self.generations[unit] = result['claim']['generation']
        return result['ok'], 'granted' if result['ok'] else result['reason']

    def _owned(self, operation, unit, worker, generation=None):
        if worker != self.principal:
            return False
        result = self.request(operation, unit, self.generations.get(unit, 0) if generation is None else generation)
        return result['ok']

    def heartbeat(self, unit, worker):
        return self._owned('renew', unit, worker)

    def release(self, unit, worker):
        return self._owned('release', unit, worker)

    def use(self, unit, generation=None):
        """Receiver-side protected-use check, consumed immediately by the effect caller."""
        return self._owned('use', unit, self.principal, generation)

    def holder(self, unit):
        result = self.request('inspect', unit)
        if not result['ok']:
            raise CL.ClaimStopped(result['reason'])
        return result['claim'].get('holder')
