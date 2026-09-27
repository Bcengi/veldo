"""Write-only credential commands; only metadata ever enters the control store.

The value is held in the transaction callable, never command parameters, a digest
input to the store, a result or an observation. The keystore operation runs after
current authority and version checks inside the serialized store transaction.
"""
import hashlib
import importlib.util
from pathlib import Path
import time


def organ(name):
    spec = importlib.util.spec_from_file_location('credential_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MC = organ('control_mcp_catalog')
KS = organ('control_credential_keystore')
KIND = 'credential'
SET, DELETE = 'set_mcp_credential', 'delete_mcp_credential'
OPERATIONS = (SET, DELETE)
Refused = MC.Refused


def entity_id(domain, identity):
    return 'credential:' + hashlib.sha256((domain + '/' + identity).encode()).hexdigest()


def reference(domain, identity):
    return 'keychain:veldo/' + entity_id(domain, identity).split(':')[1]


class Credentials:
    def __init__(self, store, conn, *, domain, repository, signer, sign, generation=1, observe=None, keystore=None):
        self.S, self.conn, self.domain, self.repository = store, conn, domain, repository
        self.signer, self.sign, self.generation = signer, sign, generation
        self.observe = observe or (lambda event: None)
        self.observations = []
        self.keystore = keystore or KS.SecretService()
        store.declare_owners(conn, 'mcp_credentials', kinds={KIND: OPERATIONS}, module=__file__)

    def apply(self, operation, params, *, principal, command_id, session=None):
        identity = params.get('id')
        about = dict(operation=operation, credential=identity, set_by=principal, command_id=command_id, session=session)
        try:
            required = {'id', 'base', 'label', 'value'} if operation == SET else {'id', 'base'}
            if (operation not in OPERATIONS or set(params) != required or not MC.identifier(identity)
                    or type(params['base']) is not int or params['base'] < 0 or not MC.text(command_id)):
                raise Refused('invalid_input:credential')
            value = params.get('value')
            if operation == SET and (not MC.text(params['label']) or not isinstance(value, str) or not value
                                     or '\x00' in value):
                raise Refused('invalid_input:credential')
            eid = entity_id(self.domain, identity)
            ref = reference(self.domain, identity)
            stored = {k: v for k, v in params.items() if k != 'value'}
            stored.update(principal=principal, repository=self.repository, reference=ref, session=session)

            def transition(conn, safe, before):
                MC.owner(conn, principal, self.repository, time.time())
                old = before.get(eid)
                if operation == DELETE and old is None:
                    raise Refused('missing_evidence:credential')
                if operation == SET:
                    self.keystore.set(ref.split(':', 1)[1], value)
                    data = dict(id=identity, label=safe['label'], reference=ref, set_at=time.time(), set_by=principal)
                else:
                    self.keystore.delete(ref.split(':', 1)[1])
                    # Preserve the reference and its history; no value remains resolvable.
                    data = dict(old['data'], set_at=time.time(), set_by=principal)
                return {eid: {'kind': KIND, 'data': data}}

            self.conn.command_registry[operation] = {'transaction_transition': transition, 'writes': MC.WRITES}
            command = dict(command_id=command_id, principal=principal, operation=operation, parameters=stored,
                           expected_versions={eid: params['base']}, artifact_digests=[], nonce=command_id)
            saved = self.S.execute(self.conn, command, self.signer, self.sign, self.generation)
        except (Refused, KS.Refused, self.S.StoreRefused) as error:
            self.record(dict(about, outcome='refused', refusal=error.code))
            raise Refused(error.code) from None
        finally:
            self.conn.command_registry.pop(operation, None)
        outcome = 'deleted' if operation == DELETE else 'replaced' if params['base'] else 'written'
        self.record(dict(about, outcome=outcome, seq=saved['seq']))
        return dict(outcome=outcome, id=identity, reference=ref, version=params['base'] + 1, seq=saved['seq'])

    def record(self, event):
        self.observations.append(event)
        self.observe(event)

    def metrics(self):
        counts = {name: sum(r['outcome'] == name for r in self.observations)
                  for name in ('written', 'replaced', 'deleted')}
        counts['refused'] = {}
        for row in self.observations:
            if row.get('refusal'):
                reason = row['refusal']
                counts['refused'][reason] = counts['refused'].get(reason, 0) + 1
        return counts
