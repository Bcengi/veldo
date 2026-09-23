"""Transactional complete input registrations over the existing control store (VELDO-0035).

Authority startup calls attach() then enable() for each command it enables. Declarations name
entity inputs, collections (including empty blocker sets), and reference fields in collection
members. A reference beginning '$' resolves from command arguments. Every command additionally
consumes its accepted revision, that revision's document inventory, and status entities.
Only control_store.execute writes. Its BEGIN IMMEDIATE encloses both validation and transition.
The registration replaces the original transition so direct store calls cannot bypass the guard.
Authentication and business authorization remain the registering service's responsibility.
"""
import copy
import importlib.util
import json
from pathlib import Path


def _snapshots():
    spec = importlib.util.spec_from_file_location('readset_snapshot', Path(__file__).with_name('control_snapshot.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SN = _snapshots()


class ReadSets:
    def __init__(self, store, conn, repo, domain_uuid, repository_uuid):
        self.store, self.conn, self.repo = store, conn, Path(repo)
        self.domain_uuid, self.repository_uuid = domain_uuid, repository_uuid
        self.registrations = {}
        self.counts = {'accepted': 0, 'refused': 0}
        self.observations = []

    def _resolve(self, value, arguments):
        if not isinstance(value, str) or not value:
            raise SN.Refused('invalid_input', 'input identity is required')
        answer = arguments.get(value[1:]) if value.startswith('$') else value
        if not isinstance(answer, str) or not answer:
            raise SN.Refused('invalid_input', 'missing input binding')
        return answer

    def enable(self, operation, declaration):
        """Trusted service registration; all consumed inputs are explicit, never caller supplied.

        declaration = {revision: id-or-$argument, entities: {label: id-or-$argument},
          collections: {label: {kind: str, where: {field: id-or-$argument},
                                references: [entity-id-field, ...]}}}
        Additional operations must register before snapshot acceptance; changing a declaration
        invalidates old snapshots. This module installs no journey-specific business commands.
        """
        if (operation in self.registrations or operation == 'accept_snapshot'
                or operation not in self.store.COMMAND_REGISTRY
                or set(declaration) != {'revision', 'entities', 'collections'}):
            raise SN.Refused('invalid_registration', operation)
        declaration = copy.deepcopy(declaration)
        original = self.store.COMMAND_REGISTRY[operation]
        self.registrations[operation] = declaration

        def transition(parameters, before):
            try:
                if not self.conn.in_transaction:
                    raise SN.Refused('missing_transaction', operation)
                snapshot_id = parameters.get('snapshot_id')
                if not isinstance(snapshot_id, str):
                    raise SN.Refused('missing_snapshot', operation)
                if before.get(snapshot_id, {}).get('version') != 1:
                    raise SN.Refused('missing_snapshot', 'declare the stored snapshot version')
                snapshot = SN.load(self.store, self.conn, snapshot_id, self.domain_uuid, self.repository_uuid)
                if snapshot['operation'] != operation:
                    raise SN.Refused('snapshot_identity_mismatch', operation)
                current = self.inputs(operation, parameters)
                accepted = snapshot['inputs']
                for name in sorted(set(current) | set(accepted)):
                    if current.get(name) != accepted.get(name):
                        raise SN.Refused('stale_input', name)
                # Only the inputs the transition consumed are visible, including collection
                # members and their referenced entities. A missing required input stays absent.
                consumed = self.entities_from(current)
                result = original['transition'](parameters, consumed)
                return result
            except SN.Refused as error:
                raise self.store.StoreRefused(error.code, error.detail) from error

        self.store.COMMAND_REGISTRY[operation] = dict(original, transition=transition,
                                                     read_set=declaration)

    def entities_from(self, inputs):
        result = {}
        for item in inputs.values():
            values = item if isinstance(item, list) else [item]
            for value in values:
                if isinstance(value, dict) and value.get('value') is not None:
                    result[value['id']] = dict(value['value'], digest=value['digest'])
        return result

    def inputs(self, operation, arguments):
        if operation not in self.registrations:
            raise SN.Refused('unregistered_inputs', operation)
        declaration = self.registrations[operation]
        result = {'registration': SN.digest(SN.canonical(declaration))}
        for label, reference in declaration['entities'].items():
            result['entity/' + label] = SN.entity(self.store, self.conn, self._resolve(reference, arguments))
        for label, query in declaration['collections'].items():
            where = {key: self._resolve(value, arguments) for key, value in query['where'].items()}
            values = []
            for (identity,) in self.conn.execute('SELECT id FROM entities WHERE kind=? ORDER BY id', (query['kind'],)):
                value = SN.entity(self.store, self.conn, identity)
                data = value['value']['data']
                if all(data.get(key) == expected for key, expected in where.items()):
                    values.append(value)
                    for field in query.get('references', []):
                        target = self._resolve(data.get(field), {})
                        result['reference/' + label + '/' + identity + '/' + field] = SN.entity(self.store, self.conn, target)
            result['collection/' + label] = values
        revision = SN.entity(self.store, self.conn, self._resolve(declaration['revision'], arguments))
        if revision['value'] is None or revision['value']['kind'] != 'accepted_revision':
            raise SN.Refused('missing_authority', 'accepted revision')
        data = revision['value']['data']
        if data.get('domain_uuid') != self.domain_uuid or data.get('repository_uuid') != self.repository_uuid:
            raise SN.Refused('snapshot_identity_mismatch', 'accepted revision')
        result['revision'] = revision
        for path, expected in data['documents'].items():
            SN.artifact(self.repo, data['commit'], path, expected)
        for path, identity in data['statuses'].items():
            SN.safe_path(path)
            value = SN.entity(self.store, self.conn, identity)
            if value['value'] is None:
                raise SN.Refused('missing_authority', identity)
            result['status/' + path] = value
        return result

    def accept(self, parameters, before):
        try:
            identity = parameters['snapshot_id']
            if SN.entity(self.store, self.conn, identity)['value'] is not None:
                raise SN.Refused('snapshot_exists', identity)
            operation, arguments = parameters['operation'], parameters['arguments']
            inputs = self.inputs(operation, arguments)
            revision = inputs['revision']['value']['data']
            watermark = self.conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0] + 1
            snapshot = {'schema': SN.SCHEMA, 'snapshot_id': identity, 'operation': operation,
                        'domain_uuid': self.domain_uuid, 'repository_uuid': self.repository_uuid,
                        'accepted_commit': revision['commit'], 'watermark': watermark,
                        'inputs': inputs, 'documents': revision['documents'],
                        'statuses': {path: inputs['status/' + path]['value'] for path in revision['statuses']}}
            SN.members(snapshot, self.repo)  # validate the complete projection inventory before accepting
            return {identity: {'kind': 'control_snapshot', 'data': snapshot}}
        except SN.Refused as error:
            raise self.store.StoreRefused(error.code, error.detail) from error
        except (KeyError, TypeError, ValueError) as error:
            raise self.store.StoreRefused('invalid_input', 'malformed snapshot request') from error

    def execute(self, command, **signing):
        """Store result plus safe metadata observations; counters measure completed calls only."""
        event = {'operation': command['operation'], 'command_id': command['command_id'],
                 'domain_uuid': self.domain_uuid, 'repository_uuid': self.repository_uuid,
                 'snapshot_id': command['parameters'].get('snapshot_id')}
        try:
            result = self.store.execute(self.conn, command, **signing)
        except self.store.StoreRefused as error:
            self.counts['refused'] += 1
            self.observations.append(dict(event, outcome='refused', refusal=error.code, input=error.detail))
            raise
        self.counts['accepted'] += 1
        self.observations.append(dict(event, outcome='accepted', watermark=result['seq']))
        return result

    def pending(self):
        """Accepted snapshots not yet referenced by a committed consuming command."""
        snapshots = {row[0] for row in self.conn.execute("SELECT id FROM entities WHERE kind='control_snapshot'")}
        # Journal before_versions includes every entity whose version the command declares.
        used = set()
        for (raw,) in self.conn.execute('SELECT before_versions FROM journal'):
            used.update(key for key, version in json.loads(raw).items() if version > 0 and key in snapshots)
        return sorted(snapshots - used)


def attach(store, conn, repo, domain_uuid, repository_uuid):
    reader = ReadSets(store, conn, repo, domain_uuid, repository_uuid)
    store.COMMAND_REGISTRY['accept_snapshot'] = {
        'transition': reader.accept, 'writes': ('entities', 'journal', 'commands', 'nonces'),
        'read_set': 'enabled operation declaration plus accepted revision projections'}
    return reader
