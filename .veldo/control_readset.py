"""Transactional complete input registrations over the existing control store (VELDO-0035).

Authority startup calls attach() then enable() for each command it enables. Declarations name
entity inputs, collections (including empty blocker sets), and reference fields in collection
members. A reference beginning '$' resolves from command arguments. Every command additionally
consumes its accepted revision, that revision's document inventory, and status entities.
Only control_store.execute writes. Its BEGIN IMMEDIATE encloses both validation and transition.
Registrations are connection-local; direct store calls on that connection use the same guard.
What a command may WRITE is not: attach declares in the store (control_store.declare_owners) that
only accept_snapshot writes a control_snapshot, so no generic command on any connection to that
store forges an accepted snapshot, and the ownership another service declared binds a read-set
command exactly as it binds that command unregistered, whichever registered first. Each
declaration names this file as the code of accept_snapshot and accept_revision, so the store runs
either only when the registered transition is this file's code with the bytes it declared.
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
OWNER = 'VELDO-0035 accepted snapshots'
SNAPSHOT_KINDS = {'control_snapshot': ('accept_snapshot',)}
REVISION_OWNER = 'VELDO-0035 accepted revisions'
REVISION_KINDS = {'accepted_revision': ('accept_revision',), 'accepted_carriers': ('accept_revision',)}
# Each accepted commit's recorded carrier paths (see Revisions), written only by accept_revision.
CARRIERS_PREFIX = 'accepted-carriers/'
REVISION_PREFIXES = {CARRIERS_PREFIX: ('accept_revision',)}


def _descends(repo, older, newer):
    """Whether `newer` has `older` in its history (or is it)."""
    result = SN._git_process.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', older, newer],
                                 capture_output=True, timeout=15)
    if result.returncode not in (0, 1):
        raise SN.Refused('missing_authority', 'the accepted history is unreadable')
    return result.returncode == 0


def carriers_id(repository_uuid, commit):
    """The store entity holding what an accepted commit of a repository carries."""
    return '%s%s/%s' % (CARRIERS_PREFIX, repository_uuid, commit)


def carrier_paths(repo, commit):
    """Every path named in an exact commit's tree and in its whole history (every parent of every
    merge, renames as a deletion and an addition) that holds a digit, sorted and distinct: every
    path any kind's number could be read from, since a carrier always holds its number's digits.
    It is kind-independent because the first revision is accepted before any kind is enabled."""
    SN.commit_id(repo, commit)
    names = set()
    for command in (['ls-tree', '-r', '-z', '--name-only', commit],
                    ['log', '-m', '-z', '--no-renames', '--format=', '--name-only', commit]):
        result = SN._git_process.run(['git', '-C', str(repo), *command], capture_output=True, timeout=30)
        if result.returncode:
            raise SN.Refused('missing_authority', 'accepted tree is unreadable')
        names.update(name for name in result.stdout.decode('utf-8', 'surrogateescape').split('\0')
                     if any(character.isdigit() for character in name))
    return sorted(names)


def _holds(repo, commit):
    """Whether the Git repository at `repo` holds `commit` as a commit object now."""
    try:
        SN.commit_id(repo, commit)
    except SN.Refused:
        return False
    return True


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

        def transition(conn, parameters, before):
            try:
                self.require_transaction(conn)
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
            except (KeyError, TypeError, ValueError) as error:
                raise self.store.StoreRefused('invalid_input', 'malformed registered inputs') from error

        self.conn.command_registry[operation] = dict(original, transaction_transition=transition,
                                                     read_set=declaration)

    def require_transaction(self, conn):
        if conn is not self.conn:
            raise SN.Refused('wrong_connection', 'validation and write must use the same connection')
        if not conn.in_transaction or not conn.command_transaction:
            raise SN.Refused('missing_transaction', 'store BEGIN IMMEDIATE is required')

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
        SN.commit_id(self.repo, data['commit'])
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

    def accept(self, conn, parameters, before):
        try:
            self.require_transaction(conn)
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
            if command['operation'] != 'accept_snapshot' and command['operation'] not in self.registrations:
                raise self.store.StoreRefused('unregistered_inputs', command['operation'])
            result = self.store.execute(self.conn, command, **signing)
        except self.store.StoreRefused as error:
            self.counts['refused'] += 1
            self.observations.append(dict(event, outcome='refused', refusal=error.code, input=error.detail))
            raise
        self.counts['accepted'] += 1
        snapshot = SN.load(self.store, self.conn, event['snapshot_id'], self.domain_uuid, self.repository_uuid)
        inputs = snapshot['inputs']
        event['accepted_inputs'] = {
            name: {'digest': SN.digest(SN.canonical(value)),
                   'versions': {item['id']: item['version'] for item in
                                (value if isinstance(value, list) else [value])
                                if isinstance(item, dict) and 'version' in item}}
            for name, value in inputs.items()}
        self.observations.append(dict(event, outcome='accepted', watermark=result['seq'],
                                      input_watermark=snapshot['watermark']))
        return result

    def pending(self):
        """Accepted snapshots not yet referenced by a committed consuming command."""
        snapshots = {row[0] for row in self.conn.execute("SELECT id FROM entities WHERE kind='control_snapshot'")}
        # Journal before_versions includes every entity whose version the command declares.
        used = set()
        for (raw,) in self.conn.execute('SELECT before_versions FROM journal'):
            used.update(key for key, version in json.loads(raw).items() if version > 0 and key in snapshots)
        return sorted(snapshots - used)


class Revisions:
    """The accepting command for accepted_revision entities, the inputs every read set consumes and
    VELDO-0037 derives its first numbers from. An accepted revision names an exact commit of an
    enrolled repository, its documents {output_path: sha256} and statuses {output_path: entity_id},
    each checked inside the store's transaction exactly as inputs() checks them when consumed; a
    revision id already accepted moves only to a descendant of its commit. attach_revisions declares
    in the store that nothing but accept_revision writes an accepted_revision, on any connection.

    WHICH REPOSITORY. attach_revisions binds each repository uuid to its accepted repository in the
    store (control_store.bind_repositories): the first service to attach, this one or VELDO-0037's
    allocation authority, fixes it, and another repository for that uuid is refused
    repository_binding_conflict. The transition reads that binding back inside its transaction and
    refuses unenrolled_commit when the bound repository does not hold the commit at acceptance time
    (an unrelated repository's commit, or a clone's unpushed one), whatever path this object was
    constructed with, so no revision service reading another repository can record a commit the
    allocation authority cannot read.

    RECORDED CARRIERS. In the same transaction, the first acceptance of a commit records what it
    carries (carrier_paths, read from the bound repository) in an immutable accepted_carriers entity
    keyed by the repository and commit id. VELDO-0037's floor reads that record, never Git, so a
    branch deleted, pruned or force-pushed after acceptance changes no number the commit held."""

    def __init__(self, store, conn, domain_uuid, repositories):
        if not isinstance(repositories, dict) or not repositories:
            raise SN.Refused('invalid_registration', 'repositories map each repository uuid to its accepted repository')
        self.store, self.conn, self.domain_uuid = store, conn, domain_uuid
        self.paths = {repository: str(path) for repository, path in repositories.items()}

    def accept(self, revision_id, repository_uuid, commit, principal, documents=None, statuses=None, **signing):
        version = SN.entity(self.store, self.conn, revision_id)['version']
        carriers = carriers_id(repository_uuid, commit) if isinstance(repository_uuid, str) and isinstance(commit, str) else None
        expected = {revision_id: version}
        if carriers is not None:
            expected[carriers] = SN.entity(self.store, self.conn, carriers)['version']
        command_id = 'revision.accept:%s:%d:%s' % (revision_id, version, commit)
        return self.store.execute(self.conn, {
            'command_id': command_id, 'principal': principal, 'operation': 'accept_revision',
            'parameters': {'revision_id': revision_id, 'repository_uuid': repository_uuid, 'commit': commit,
                           'documents': dict(documents or {}), 'statuses': dict(statuses or {})},
            'expected_versions': expected, 'artifact_digests': [], 'nonce': command_id + '/nonce'}, **signing)

    def transition(self, conn, parameters, before):
        try:
            ReadSets.require_transaction(self, conn)   # the read sets' own guard: this connection, its BEGIN IMMEDIATE
            if set(parameters) != {'revision_id', 'repository_uuid', 'commit', 'documents', 'statuses'}:
                raise SN.Refused('invalid_input', 'an accepted revision is revision_id, repository_uuid, commit, documents, statuses')
            identity, repository, commit = parameters['revision_id'], parameters['repository_uuid'], parameters['commit']
            if repository not in self.paths:
                raise SN.Refused('wrong_repository', 'repository is not enrolled in this domain')
            repo = self.paths[repository]
            SN.commit_id(repo, commit)
            bound = self.store.bound_repository(conn, self.domain_uuid, repository)
            if bound is None or not _holds(bound, commit):
                raise SN.Refused('unenrolled_commit', '%s is not in the accepted repository %s of this store'
                                 % (commit, bound or '(none bound)'))
            documents, statuses = parameters['documents'], parameters['statuses']
            for path, identity_of_status in statuses.items():
                SN.safe_path(path)
                if SN.entity(self.store, conn, identity_of_status)['value'] is None:
                    raise SN.Refused('missing_authority', identity_of_status)
            # Every document read at the exact commit, and no two projection paths overlapping.
            SN.members({'documents': documents, 'statuses': {path: None for path in statuses},
                        'accepted_commit': commit}, repo)
            prior = before.get(identity)
            if prior is not None:
                data = prior['data']
                if (prior['kind'] != 'accepted_revision' or data.get('domain_uuid') != self.domain_uuid
                        or data.get('repository_uuid') != repository):
                    raise SN.Refused('invalid_input', '%s is not an accepted revision of this repository' % identity)
                # An accepted revision only moves forward: its history is what VELDO-0037's first
                # numbers are derived from, and a revision moved back would drop numbers it held.
                if not _descends(repo, data['commit'], commit):
                    raise SN.Refused('revision_regression', '%s is at %s; %s does not descend from it'
                                     % (identity, data['commit'], commit))
            changes = {identity: {'kind': 'accepted_revision', 'data': {
                'domain_uuid': self.domain_uuid, 'repository_uuid': repository, 'commit': commit,
                'documents': documents, 'statuses': statuses}}}
            # What the commit carries, recorded once from the bound repository; a record already
            # there is immutable and is only checked to be this commit's.
            carriers = carriers_id(repository, commit)
            recorded = before.get(carriers)
            if recorded is None:
                changes[carriers] = {'kind': 'accepted_carriers', 'data': {
                    'domain_uuid': self.domain_uuid, 'repository_uuid': repository, 'commit': commit,
                    'paths': carrier_paths(bound, commit)}}
            elif (recorded['kind'] != 'accepted_carriers' or recorded['data'].get('commit') != commit
                  or recorded['data'].get('repository_uuid') != repository):
                raise SN.Refused('invalid_input', '%s is not the carrier record of %s' % (carriers, commit))
            return changes
        except SN.Refused as error:
            raise self.store.StoreRefused(error.code, error.detail) from error
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise self.store.StoreRefused('invalid_input', 'malformed accepted revision') from error


def attach_revisions(store, conn, domain_uuid, repositories):
    """Register accept_revision on one store connection; returns the accepting service."""
    if 'accept_revision' in conn.command_registry:
        raise SN.Refused('invalid_registration', 'connection already accepts revisions')
    service = Revisions(store, conn, domain_uuid, repositories)
    store.declare_owners(conn, REVISION_OWNER, kinds=REVISION_KINDS, prefixes=REVISION_PREFIXES, module=__file__)
    store.bind_repositories(conn, domain_uuid, service.paths)
    conn.command_registry['accept_revision'] = {
        'transaction_transition': service.transition, 'writes': ('entities', 'journal', 'commands', 'nonces')}
    return service


def attach(store, conn, repo, domain_uuid, repository_uuid):
    if 'accept_snapshot' in conn.command_registry:
        raise SN.Refused('invalid_registration', 'connection already has a snapshot authority')
    reader = ReadSets(store, conn, repo, domain_uuid, repository_uuid)
    store.declare_owners(conn, OWNER, kinds=SNAPSHOT_KINDS, module=__file__)
    conn.command_registry['accept_snapshot'] = {
        'transaction_transition': reader.accept, 'writes': ('entities', 'journal', 'commands', 'nonces'),
        'read_set': 'enabled operation declaration plus accepted revision projections'}
    return reader
