"""MARKED STAND-IN for the red record (proof/VELDO-0132/red.py). NOT production code.

At 5a5dfcd there is no control_workflow module and no workflow service. What a caller had was the
store's generic command: a definition kept as one ordinary entity, written in place with
upsert_entity by whoever names a principal, with nothing validated, no revision kept and no layout
separated; reading it back returns whatever was last written. This file gives the names suite 65
calls exactly that behaviour, and reports nothing.
"""
import hashlib
import json

SCHEMA = 'veldo.workflow/v1'
REVISION_SCHEMA = 'pre-change: no workflow revisions'


class Refused(Exception):
    def __init__(self, code, detail='', codes=None):
        self.code, self.detail, self.codes = code, detail, list(codes or [code])
        super().__init__(code)


def taxonomy(code):
    return 'unknown_outcome'


def definition_problems(definition, resolve=None):
    return []


def _id(workflow):
    return 'workflow:' + str(workflow)


def head_version(conn, domain, repository, workflow):
    row = conn.execute('SELECT version FROM entities WHERE id=?', (_id(workflow),)).fetchone()
    return row[0] if row else 0


def head_id(domain, repository, workflow):
    return _id(workflow)


class Workflows:
    def __init__(self, store, conn, *, domain, repository, signer, sign, generation=1, observe=None, clock=None):
        self.store, self.conn, self.domain, self.repository = store, conn, domain, repository
        self.signer, self.sign, self.generation = signer, sign, generation
        self.counts = {'accepted': 0, 'refused': 0}
        self.serial = 0

    def save(self, document, *, principal, base):
        definition = (document or {}).get('definition') or {}
        workflow = definition.get('id')
        identity = _id(workflow)
        current = head_version(self.conn, self.domain, self.repository, workflow)
        self.serial += 1
        command_id = 'workflow-write-%s-%d-%s' % (workflow, self.serial, hashlib.sha256(
            json.dumps(document, sort_keys=True, default=str).encode()).hexdigest()[:12])
        result = self.store.execute(self.conn, {
            'command_id': command_id, 'principal': principal or '-', 'operation': 'upsert_entity',
            'parameters': {'entity_id': identity, 'kind': 'workflow', 'data': dict(document)},
            'expected_versions': {identity: current}, 'artifact_digests': [], 'nonce': command_id},
            self.signer, self.sign, self.generation)
        return {'workflow': workflow, 'version': current + 1, 'revision': identity, 'seq': result['seq']}

    def load(self, workflow, version=None):
        row = self.conn.execute('SELECT version, data FROM entities WHERE id=?', (_id(workflow),)).fetchone()
        if row is None:
            raise Refused('absent')
        data = json.loads(row[1])
        return {'workflow': workflow, 'version': row[0], 'revision': _id(workflow),
                'definition': data.get('definition'), 'layout': data.get('layout', {})}

    def history(self, workflow):
        version = head_version(self.conn, self.domain, self.repository, workflow)
        return [{'version': version}] if version else []
