"""Specification alias allocation and accepted document identity (VELDO-0037, PLAN-0019 W22, R73).

WHAT THIS IS. The authority's allocation commands, registered on ONE store connection the way
control_readset registers snapshot consumers. control_store.execute alone writes; every transition
below runs inside its BEGIN IMMEDIATE on that same connection, so what a transition reads and what
it writes are one transaction.

  enable_artifact_kind  a per-repository artifact kind: alias prefix, number width, path template
                        and first number. The kind entity IS the kind's alias counter.
  allocate_document     one new alias from the stored counter, its reservation, the source
                        mapping, the accepted document head, its immutable version 1 and a pending
                        publication obligation, all in one signed journal record.
  edit_document         a new immutable version of an accepted document, only when the caller's
                        expected version AND expected content digest are both current.
  record_publication    one declared version's publication obligation becomes published, carrying
                        the digest of the bytes the publisher actually made visible.

IDENTITY. An alias never comes from a checkout: only allocate_document advances the counter, and it
refuses a command whose number is not the counter's current value. Each alias is reserved as its own
entity (alias/<repository>/<alias>), so the store's primary key plus the expected-version-0 rule is
the uniqueness constraint, and a reservation is never released, so nothing recycles an alias. The
source mapping is keyed by (repository, source system, source id, source revision, intended artifact
role). The same key with the same bytes returns the original allocation; the same key with other
bytes is the named conflict source_content_conflict, never an overwrite. A role is '<kind>' or
'<kind>/<label>', so one source can produce several specifications and other artifacts. Every alias
passes claim.unit_id_problem before any artifact entity is written; this module has no second
spelling of that rule.

ACCEPTED BYTES. Document content is UTF-8 text committed in the store beside its sha256 digest.
Version entities are immutable, so the prior bytes stay readable after every edit. Publication to a
checkout happens after commit and lives in control_document.py.

NOT HERE, on purpose (Release 2): concurrency qualification matrices, recovery of interrupted
publication, fencing, remote acknowledgement. Authenticating the requester and authorizing the
business action belong to the calling service; this module records the principal it is handed.
Standard library only.
"""
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SN = _sibling('alias_snapshot', 'control_snapshot.py')
CLAIM = _sibling('alias_claim', 'claim.py')
_git_process = SN._git_process
SCHEMA = 'veldo.control_alias/v1'
OPERATIONS = ('enable_artifact_kind', 'allocate_document', 'edit_document', 'record_publication')
ATTEMPTS = 16
# Everything these commands write; no other command on the allocation connection may write it.
OWNED_KINDS = frozenset(('artifact_kind', 'alias_reservation', 'alias_source', 'accepted_document',
                         'document_version', 'publication_obligation'))
OWNED_PREFIXES = ('artifact-kind/', 'alias/', 'alias-source/', 'document/', 'publication/')
# The error taxonomy every refusal is reported under. A code missing here is unknown_outcome,
# never success.
CATEGORIES = {
    'invalid_input': 'invalid_input', 'invalid_unit_id': 'invalid_input',
    'malformed_command': 'invalid_input', 'invalid_registration': 'invalid_input',
    'wrong_repository': 'invalid_input', 'transition_refused': 'invalid_input',
    'missing_authority': 'missing_authority', 'allocation_owned': 'missing_authority',
    'unregistered_inputs': 'invalid_input',
    'stale_version': 'stale_subject', 'stale_document': 'stale_subject',
    'source_content_conflict': 'stale_subject', 'command_content_conflict': 'stale_subject',
    'publication_conflict': 'stale_subject', 'publication_order': 'stale_subject',
    'below_accepted_history': 'stale_subject',
    'nonce_consumed': 'stale_subject',
    'allocation_contention': 'unavailable_service', 'read_only_handle': 'unavailable_service',
    'unsupported_filesystem': 'unavailable_service', 'durability_not_enabled': 'unavailable_service',
    'incomplete_transaction': 'unavailable_service', 'wrong_connection': 'unavailable_service',
    'missing_transaction': 'unavailable_service',
    'accepted_digest_mismatch': 'missing_evidence', 'publication_mismatch': 'missing_evidence',
    'missing_publication': 'missing_evidence', 'document_mismatch': 'missing_evidence',
    'input_digest_mismatch': 'missing_evidence',
}
_KIND = re.compile(r'[a-z][a-z0-9_]{0,31}')
_WORD = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+){0,15}')
_PLACEHOLDER = re.compile(r'(\{alias\}|\{number\}|\{slug\})')


def category(code):
    return CATEGORIES.get(code, 'unknown_outcome')


def kind_id(repository, kind):
    return 'artifact-kind/%s/%s' % (repository, kind)


def alias_id(repository, alias):
    return 'alias/%s/%s' % (repository, alias)


def head_id(repository, alias):
    return 'document/%s/%s' % (repository, alias)


def version_id(repository, alias, version):
    return 'document/%s/%s@%d' % (repository, alias, version)


def publication_id(repository, alias, version):
    return 'publication/%s/%s@%d' % (repository, alias, version)


def source_key(repository, source, role):
    return SN.digest(SN.canonical({'repository_uuid': repository, 'system': source['system'],
                                   'id': source['id'], 'revision': source['revision'], 'role': role}))


def source_id(repository, key):
    return 'alias-source/%s/%s' % (repository, key.split(':', 1)[1])


def alias_for(kind, number):
    return kind['prefix'] + '-' + str(number).zfill(kind['width'])


def path_for(kind, number, slug):
    """The declared output path of one allocation; the template decides, never the caller."""
    template = kind['path_template']
    if '{slug}' in template and (not isinstance(slug, str) or not _WORD.fullmatch(slug)):
        raise SN.Refused('invalid_input', 'a slug is lowercase words joined by single hyphens')
    path = (template.replace('{alias}', alias_for(kind, number))
            .replace('{number}', str(number).zfill(kind['width'])).replace('{slug}', slug or ''))
    return SN.safe_path(path)


def _pattern(kind):
    regex = ''
    for part in _PLACEHOLDER.split(kind['path_template']):
        if part == '{alias}':
            regex += re.escape(kind['prefix']) + '-([0-9]+)'
        elif part == '{number}':
            regex += '([0-9]+)'
        elif part == '{slug}':
            regex += '[a-z0-9]+(?:-[a-z0-9]+)*'
        else:
            regex += re.escape(part)
    return re.compile(regex)


def maximum(paths, kind):
    """The highest number among repository-relative paths the kind's template produces."""
    pattern = _pattern(kind)
    found = [int(match.group(1)) for match in (pattern.fullmatch(str(p)) for p in paths) if match]
    return max(found, default=0)


def root_commits(repo, revision='HEAD'):
    """A repository's identity: every root commit reachable from a revision, sorted. A different
    repository cannot share them and a clone cannot shed them (control_enrollment's rule)."""
    result = _git_process.run(['git', '-C', str(repo), 'rev-list', '--max-parents=0', revision, '--'],
                              capture_output=True, timeout=15)
    if result.returncode:
        return None
    return sorted(line for line in result.stdout.decode().split() if line) or None


def checkout_identity(root):
    """The root commits of the Git checkout whose top level is exactly `root`, or None."""
    result = _git_process.run(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], capture_output=True, timeout=15)
    if result.returncode or os.path.realpath(result.stdout.decode().strip()) != os.path.realpath(root):
        return None
    return root_commits(root)


def _static_directory(template):
    """The deepest directory every path of a template lies under: its leading placeholder-free
    components, or '' for the whole tree."""
    parts = []
    for part in PurePosixPath(template).parts[:-1]:
        if '{' in part:
            break
        parts.append(part)
    return '/'.join(parts)


def accepted_maximum(repo, commit, kind):
    """The kind's highest number among the paths its template matches in an EXACT accepted commit,
    counting the commit's tree AND its history, so a number whose file was later deleted or renamed
    stays taken (C9). Only the enabling transition calls it; allocation never reads any tree."""
    SN.commit_id(repo, commit)
    directory = _static_directory(kind['path_template'])
    scope = ['--', directory] if directory else []
    names = []
    for command in (['ls-tree', '-r', '-z', '--name-only', commit],
                    ['log', '-m', '-z', '--no-renames', '--format=', '--name-only', commit]):
        result = _git_process.run(['git', '-C', str(repo), *command, *scope], capture_output=True, timeout=30)
        if result.returncode:
            raise SN.Refused('missing_authority', 'accepted tree is unreadable')
        names += result.stdout.decode('utf-8', 'surrogateescape').split('\0')
    return maximum(names, kind)


_DIGITS = frozenset('0123456789')
_SLUG = frozenset('abcdefghijklmnopqrstuvwxyz0123456789-')
_SLASH = (frozenset('/'), False)


def _literal(text):
    return [(frozenset(character), False) for character in text]


def _items(kind):
    """Every path a kind can declare, as a sequence of (characters, repeats) items. It
    over-approximates: a slug's hyphen placement and a number's leading zeros are not modelled, so
    a collision found here may be one the counter never reaches, never the reverse."""
    items = []
    for part in _PLACEHOLDER.split(kind['path_template']):
        if part == '{alias}':
            items += _literal(kind['prefix'] + '-')
        if part in ('{alias}', '{number}'):
            items += [(_DIGITS, False)] * kind['width'] + [(_DIGITS, True)]
        elif part == '{slug}':
            items += [(_SLUG, False), (_SLUG, True)]
        elif part:
            items += _literal(part)
    return items


def _meet(first, second, directories=True):
    """Whether some path of `first` equals some path of `second`, or (with directories) names a
    directory holding one of the other's paths. A walk of the two item sequences in step."""
    ends = (len(first), len(second))
    seen, pending = {(0, 0)}, [(0, 0)]
    while pending:
        i, j = pending.pop()
        if (i, j) == ends:
            return True
        if directories and ((i == ends[0] and j < ends[1] and second[j] == _SLASH)
                            or (j == ends[1] and i < ends[0] and first[i] == _SLASH)):
            return True
        moves = []
        if i < ends[0] and first[i][1]:
            moves.append((i + 1, j))
        if j < ends[1] and second[j][1]:
            moves.append((i, j + 1))
        if i < ends[0] and j < ends[1] and first[i][0] & second[j][0]:
            moves.append((i if first[i][1] else i + 1, j if second[j][1] else j + 1))
        for move in moves:
            if move not in seen:
                seen.add(move)
                pending.append(move)
    return False


def _template_problem(kind):
    template = kind['path_template']
    if not isinstance(template, str):
        return 'path_template is text'
    counts = {name: template.count(name) for name in ('{alias}', '{number}', '{slug}')}
    if counts['{alias}'] + counts['{number}'] != 1 or counts['{slug}'] > 1:
        return 'path_template names exactly one of {alias} or {number}, and {slug} at most once'
    if '{' in _PLACEHOLDER.sub('', template) or '}' in _PLACEHOLDER.sub('', template):
        return 'path_template has an unknown placeholder'
    try:
        path_for(kind, kind['next'], 'sample')
    except SN.Refused as error:
        return error.detail
    return None


def _text(content):
    if not isinstance(content, bytes):
        raise SN.Refused('invalid_input', 'document content is bytes')
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError as error:
        raise SN.Refused('invalid_input', 'documents are UTF-8 text') from error


def parse_source(source, role):
    if (not isinstance(source, dict) or set(source) != {'system', 'id', 'revision'}
            or not all(isinstance(v, str) and v.strip() for v in source.values())):
        raise SN.Refused('invalid_input', 'source is {system, id, revision}, each non-blank text')
    if not isinstance(role, str) or not role:
        raise SN.Refused('invalid_input', 'intended artifact role is required')
    kind, _, label = role.partition('/')
    if not _KIND.fullmatch(kind) or ('/' in role and not _WORD.fullmatch(label)):
        raise SN.Refused('invalid_input', "role is '<kind>' or '<kind>/<label>'")
    return dict(source), role, kind


class Allocations:
    """One domain's allocation authority over the repositories enrolled in that domain."""

    def __init__(self, store, conn, domain_uuid, repositories):
        """repositories maps each enrolled repository UUID to its accepted Git repository, the one
        accepted revisions name commits of; the path is configuration, never a request field."""
        if not isinstance(repositories, dict) or not repositories:
            raise SN.Refused('invalid_registration', 'repositories map each repository uuid to its accepted repository')
        self.store, self.conn, self.domain_uuid = store, conn, domain_uuid
        self.paths = {repository: str(path) for repository, path in repositories.items()}
        self.repositories = frozenset(self.paths)
        # Each repository's identity, which binds a checkout to it; two enrolled repositories that
        # shared one could not tell their checkouts apart.
        self.identities = {repository: root_commits(path) for repository, path in self.paths.items()}
        known = [identity for identity in self.identities.values() if identity is not None]
        if len(known) != len(self.identities) or len({tuple(identity) for identity in known}) != len(known):
            raise SN.Refused('invalid_registration', 'every enrolled repository needs its own readable root commits')
        self.counts = {'accepted': 0, 'reused': 0, 'refused': 0}
        self.observations = []

    # -- reads (outside any transaction; transitions reread under the store's lock) ------------
    def current(self, identity):
        item = SN.entity(self.store, self.conn, identity)
        return item['version'], (item['value'] or {}).get('data')

    def pending(self):
        """Publication obligations accepted but not yet published: this concern's pending work."""
        found = []
        for (raw,) in self.conn.execute("SELECT data FROM entities WHERE kind='publication_obligation'"):
            data = json.loads(raw)
            if data['state'] == 'pending':
                found.append((data['repository_uuid'], data['alias'], data['version']))
        return sorted(found)

    # -- the observed operation wrapper --------------------------------------------------------
    def observe(self, operation, request, work):
        event = {'operation': operation, 'domain_uuid': self.domain_uuid,
                 'repository_uuid': request.get('repository_uuid') if isinstance(request, dict) else None,
                 'request_id': request.get('request_id') if isinstance(request, dict) else None}
        try:
            try:
                result = work(event)
            except SN.Refused as error:
                raise self.store.StoreRefused(error.code, error.detail) from error
            except (KeyError, TypeError, AttributeError) as error:
                raise self.store.StoreRefused('invalid_input', 'malformed %s request' % operation) from error
        except self.store.StoreRefused as error:
            self.counts['refused'] += 1
            self.observations.append(dict(event, outcome='refused', refusal=error.code,
                                          category=category(error.code)))
            raise
        except Exception as error:
            self.observations.append(dict(event, outcome='unknown', refusal=type(error).__name__,
                                          category='unknown_outcome'))
            raise
        outcome = 'reused' if result.get('reused') else 'accepted'
        self.counts[outcome] += 1
        self.observations.append(dict(event, outcome=outcome, alias=result.get('alias'),
                                      version=result.get('version'), command_id=result.get('command_id'),
                                      seq=result.get('seq'), record_digest=result.get('record_digest'),
                                      after_versions=result.get('after_versions', {})))
        return result

    def _repository(self, request):
        repository = request['repository_uuid']
        if repository not in self.repositories:
            raise SN.Refused('wrong_repository', 'repository is not enrolled in this domain')
        return repository

    def _execute(self, command, signing, **identity):
        result = self.store.execute(self.conn, command, **signing)
        return dict(result, inputs=dict(command['expected_versions']), **identity)

    @staticmethod
    def _command(command_id, principal, operation, parameters, expected):
        return {'command_id': command_id, 'principal': principal, 'operation': operation,
                'parameters': parameters, 'expected_versions': expected, 'artifact_digests':
                [parameters['digest']] if 'digest' in parameters else [], 'nonce': command_id + '/nonce'}

    def _reuse(self, mapping, digest, event):
        if mapping['digest'] != digest:
            raise SN.Refused('source_content_conflict', 'this source tuple was accepted with other bytes; '
                             'changed content needs a new source revision')
        event.update(source_key=mapping['source_key'], alias=mapping['alias'])
        return {'reused': True, 'alias': mapping['alias'], 'version': mapping['version'],
                'digest': mapping['digest'], 'path': mapping['path'], 'source_key': mapping['source_key']}

    # -- operations ----------------------------------------------------------------------------
    def enable_kind(self, request, **signing):
        def work(event):
            repository = self._repository(request)
            event.update(kind=request['kind'])
            revision = request['revision_id']
            if not isinstance(revision, str) or not revision:
                raise SN.Refused('invalid_input', 'a kind names the accepted revision its first number comes from')
            parameters = {'repository_uuid': repository, 'kind': request['kind'], 'prefix': request['prefix'],
                          'width': request['width'], 'path_template': request['path_template'],
                          'revision_id': revision, 'first': request.get('first')}
            command = self._command('alias.enable:' + request['request_id'], request['principal'],
                                    'enable_artifact_kind', parameters,
                                    {kind_id(repository, request['kind']): 0, revision: self.current(revision)[0]})
            return self._execute(command, signing)
        return self.observe('enable_artifact_kind', request, work)

    def author_allocation(self, request):
        """The command allocate() would execute now, or a reuse result. Separated so a caller's
        stale read of the counter is demonstrably refused by the store rather than trusted."""
        repository = self._repository(request)
        source, role, kind_name = parse_source(request['source'], request['role'])
        text = _text(request['content'])
        digest = SN.digest(request['content'])
        key = source_key(repository, source, role)
        _, mapping = self.current(source_id(repository, key))
        if mapping is not None:
            return None, mapping, digest
        kind_version, kind = self.current(kind_id(repository, kind_name))
        if kind is None:
            raise SN.Refused('missing_authority', 'artifact kind %s is not enabled' % kind_name)
        number = kind['next']
        alias = alias_for(kind, number)
        problem = CLAIM.unit_id_problem(alias)
        if problem is not None:
            raise SN.Refused('invalid_unit_id', problem)
        path = path_for(kind, number, request.get('slug'))
        parameters = {'repository_uuid': repository, 'role': role, 'source': source, 'number': number,
                      'slug': request.get('slug'), 'content': text, 'digest': digest}
        expected = {kind_id(repository, kind_name): kind_version, alias_id(repository, alias): 0,
                    source_id(repository, key): 0, head_id(repository, alias): 0,
                    version_id(repository, alias, 1): 0, publication_id(repository, alias, 1): 0}
        command = self._command('alias.allocate:%s:%d' % (request['request_id'], kind_version),
                                request['principal'], 'allocate_document', parameters, expected)
        return command, {'alias': alias, 'path': path, 'source_key': key,
                         'kind': kind_id(repository, kind_name), 'kind_version': kind_version}, digest

    def allocate(self, request, **signing):
        def work(event):
            event.update(workspace=request['workspace'])
            for _ in range(ATTEMPTS):
                command, plan, digest = self.author_allocation(request)
                if command is None:
                    return self._reuse(plan, digest, event)
                event.update(source_key=plan['source_key'], alias=plan['alias'])
                try:
                    return self._execute(command, signing, alias=plan['alias'], version=1,
                                         digest=digest, path=plan['path'], source_key=plan['source_key'])
                except self.store.StoreRefused as error:
                    # Only a counter that moved since this read is contention worth rereading;
                    # anything else, including a reserved alias, is the answer.
                    if error.code != 'stale_version' or self.current(plan['kind'])[0] == plan['kind_version']:
                        raise
            raise SN.Refused('allocation_contention', 'the counter kept moving; nothing was written')
        return self.observe('allocate_document', request, work)

    def edit(self, request, **signing):
        def work(event):
            repository = self._repository(request)
            alias = request['alias']
            problem = CLAIM.unit_id_problem(alias)
            if problem is not None:
                raise SN.Refused('invalid_unit_id', problem)
            event.update(alias=alias, workspace=request['workspace'])
            _, reservation = self.current(alias_id(repository, alias))
            if reservation is None:
                raise SN.Refused('missing_authority', 'alias %s is not allocated here' % alias)
            source, role, kind_name = parse_source(request['source'], request['role'])
            if kind_name != reservation['kind']:
                raise SN.Refused('invalid_input', 'the role names another artifact kind')
            text = _text(request['content'])
            digest = SN.digest(request['content'])
            key = source_key(repository, source, role)
            event.update(source_key=key)
            _, mapping = self.current(source_id(repository, key))
            if mapping is not None:
                if mapping['alias'] != alias:
                    raise SN.Refused('source_content_conflict', 'this source tuple produced another alias')
                return self._reuse(mapping, digest, event)
            head_version, _ = self.current(head_id(repository, alias))
            expected = request['expected_version']
            if type(expected) is not int or expected < 1 or not isinstance(request['expected_digest'], str):
                raise SN.Refused('invalid_input', 'an edit names its expected version and content digest')
            parameters = {'repository_uuid': repository, 'alias': alias, 'role': role, 'source': source,
                          'expected_version': expected, 'expected_digest': request['expected_digest'],
                          'content': text, 'digest': digest}
            command = self._command('alias.edit:' + request['request_id'], request['principal'], 'edit_document',
                                    parameters, {head_id(repository, alias): expected, source_id(repository, key): 0,
                                                 version_id(repository, alias, expected + 1): 0,
                                                 publication_id(repository, alias, expected + 1): 0})
            return self._execute(command, signing, alias=alias, version=expected + 1, digest=digest,
                                 path=reservation['path'], source_key=key, observed_head=head_version)
        return self.observe('edit_document', request, work)

    def record_publication(self, repository, alias, version, observed, principal, **signing):
        """Called by the publisher after the bytes are visible; not an independently observed call."""
        expected = {publication_id(repository, alias, version): 1}
        if version > 1:
            expected[publication_id(repository, alias, version - 1)] = 2
        parameters = {'repository_uuid': repository, 'alias': alias, 'version': version, 'observed_digest': observed}
        command = self._command('alias.publish:%s:%s@%d' % (repository, alias, version), principal,
                                'record_publication', parameters, expected)
        return self._execute(command, signing, alias=alias, version=version, digest=observed)

    # -- transitions (inside control_store.execute's BEGIN IMMEDIATE) ---------------------------
    def _refuse(self, code, detail):
        raise self.store.StoreRefused(code, detail)

    def _guard(self, conn, parameters):
        if conn is not self.conn:
            self._refuse('wrong_connection', 'validation and write must use the same connection')
        if not conn.in_transaction or not conn.command_transaction:
            self._refuse('missing_transaction', 'store BEGIN IMMEDIATE is required')
        if parameters.get('repository_uuid') not in self.repositories:
            self._refuse('wrong_repository', 'repository is not enrolled in this domain')
        return parameters['repository_uuid']

    def _transition(self, body):
        def transition(conn, parameters, before):
            try:
                return body(conn, parameters, before)
            except SN.Refused as error:
                raise self.store.StoreRefused(error.code, error.detail) from error
            except (KeyError, TypeError, AttributeError, ValueError) as error:
                raise self.store.StoreRefused('invalid_input', 'malformed allocation parameters') from error
        return transition

    def _t_enable(self, conn, p, before):
        repository = self._guard(conn, p)
        if not isinstance(p['kind'], str) or not _KIND.fullmatch(p['kind']):
            self._refuse('invalid_input', 'a kind is a lowercase word')
        first = p['first']
        if (not isinstance(p['prefix'], str) or not p['prefix'] or type(p['width']) is not int
                or not 1 <= p['width'] <= 9 or (first is not None and (type(first) is not int or first < 1))):
            self._refuse('invalid_input', 'prefix is text, width 1-9 and a first number, when named, positive')
        data = {'schema': SCHEMA, 'repository_uuid': repository, 'kind': p['kind'], 'prefix': p['prefix'],
                'width': p['width'], 'path_template': p['path_template'], 'next': 1 if first is None else first}
        problem = CLAIM.unit_id_problem(alias_for(data, data['next']))
        if problem is not None:
            self._refuse('invalid_unit_id', problem)
        problem = _template_problem(data)
        if problem is not None:
            self._refuse('invalid_input', problem)
        # One repository's kinds share one checkout: no two may declare one path, or a path that
        # is a directory of another kind's path.
        for (raw,) in conn.execute("SELECT data FROM entities WHERE kind='artifact_kind'"):
            other = json.loads(raw)
            if other['repository_uuid'] != repository:
                continue
            if other['prefix'] == data['prefix']:
                self._refuse('invalid_registration', 'prefix %s already allocates kind %s' % (data['prefix'], other['kind']))
            if _meet(_items(data), _items(other)):
                self._refuse('invalid_registration', 'kinds %s and %s can declare one path' % (data['kind'], other['kind']))
        # The first number comes from an accepted revision's commit, read here inside the
        # transaction; a caller may name a later first number, never an earlier one.
        revision = before.get(p['revision_id'])
        if revision is None or revision['kind'] != 'accepted_revision':
            self._refuse('missing_authority', 'no accepted revision %r' % (p['revision_id'],))
        accepted = revision['data']
        if accepted.get('domain_uuid') != self.domain_uuid or accepted.get('repository_uuid') != repository:
            self._refuse('wrong_repository', 'the accepted revision belongs to another repository')
        floor = accepted_maximum(self.paths[repository], accepted['commit'], data) + 1
        roots = root_commits(self.paths[repository], accepted['commit'])
        if roots != self.identities[repository]:
            self._refuse('wrong_repository', 'the accepted commit is not in the enrolled repository')
        if first is None:
            data['next'] = floor
        elif first < floor:
            self._refuse('below_accepted_history', 'accepted commit %s already holds %s numbers below %d'
                         % (accepted['commit'], data['kind'], floor))
        data.update(accepted_revision=p['revision_id'], accepted_commit=accepted['commit'], root_commits=roots)
        return {kind_id(repository, data['kind']): {'kind': 'artifact_kind', 'data': data}}

    def _t_allocate(self, conn, p, before):
        repository = self._guard(conn, p)
        source, role, kind_name = parse_source(p['source'], p['role'])
        counter = kind_id(repository, kind_name)
        if counter not in before:
            self._refuse('missing_authority', 'artifact kind %s is not enabled' % kind_name)
        kind = before[counter]['data']
        number = p['number']
        if number != kind['next']:
            self._refuse('stale_version', 'the counter is at %r; this command allocates %r' % (kind['next'], number))
        alias = alias_for(kind, number)
        problem = CLAIM.unit_id_problem(alias)
        if problem is not None:
            self._refuse('invalid_unit_id', problem)
        path = path_for(kind, number, p['slug'])
        digest = SN.digest(p['content'].encode('utf-8'))
        if digest != p['digest']:
            self._refuse('invalid_input', 'content digest does not match the content')
        key = source_key(repository, source, role)
        record = {'schema': SCHEMA, 'repository_uuid': repository, 'alias': alias, 'kind': kind_name,
                  'role': role, 'path': path, 'source': source, 'source_key': key}
        return {
            counter: {'kind': 'artifact_kind', 'data': dict(kind, next=number + 1)},
            alias_id(repository, alias): {'kind': 'alias_reservation', 'data': dict(record, number=number)},
            source_id(repository, key): {'kind': 'alias_source', 'data': dict(record, version=1, digest=digest)},
            head_id(repository, alias): {'kind': 'accepted_document', 'data': dict(record, version=1, digest=digest)},
            version_id(repository, alias, 1): {'kind': 'document_version', 'data': dict(
                record, version=1, digest=digest, prior_digest=None, content=p['content'])},
            publication_id(repository, alias, 1): {'kind': 'publication_obligation', 'data': {
                'repository_uuid': repository, 'alias': alias, 'path': path, 'version': 1, 'digest': digest,
                'state': 'pending', 'observed_digest': None}},
        }

    def _t_edit(self, conn, p, before):
        repository = self._guard(conn, p)
        alias = p['alias']
        problem = CLAIM.unit_id_problem(alias)
        if problem is not None:
            self._refuse('invalid_unit_id', problem)
        head = head_id(repository, alias)
        if head not in before:
            self._refuse('missing_authority', 'alias %s has no accepted document' % alias)
        current = before[head]['data']
        if current['digest'] != p['expected_digest']:
            self._refuse('stale_document', 'accepted %s version %d is %s; the edit expected %s'
                         % (alias, current['version'], current['digest'], p['expected_digest']))
        version = before[head]['version'] + 1
        if version != p['expected_version'] + 1 or current['version'] + 1 != version:
            self._refuse('stale_version', 'accepted %s is at version %d' % (alias, current['version']))
        source, role, kind_name = parse_source(p['source'], p['role'])
        if kind_name != current['kind']:
            self._refuse('invalid_input', 'the role names another artifact kind')
        digest = SN.digest(p['content'].encode('utf-8'))
        if digest != p['digest']:
            self._refuse('invalid_input', 'content digest does not match the content')
        key = source_key(repository, source, role)
        record = dict(current, role=role, source=source, source_key=key, version=version, digest=digest)
        return {
            head: {'kind': 'accepted_document', 'data': record},
            source_id(repository, key): {'kind': 'alias_source', 'data': record},
            version_id(repository, alias, version): {'kind': 'document_version', 'data': dict(
                record, prior_digest=current['digest'], content=p['content'])},
            publication_id(repository, alias, version): {'kind': 'publication_obligation', 'data': {
                'repository_uuid': repository, 'alias': alias, 'path': current['path'], 'version': version,
                'digest': digest, 'state': 'pending', 'observed_digest': None}},
        }

    def _t_publish(self, conn, p, before):
        repository = self._guard(conn, p)
        obligation = publication_id(repository, p['alias'], p['version'])
        if obligation not in before:
            self._refuse('missing_authority', 'no publication obligation for %s@%r' % (p['alias'], p['version']))
        data = before[obligation]['data']
        if data['state'] != 'pending':
            self._refuse('stale_version', 'already published')
        if p['observed_digest'] != data['digest']:
            self._refuse('publication_mismatch', 'published bytes are %s; accepted %s' % (p['observed_digest'], data['digest']))
        if p['version'] > 1:
            prior = before.get(publication_id(repository, p['alias'], p['version'] - 1))
            if prior is None or prior['data']['state'] != 'published':
                self._refuse('publication_order', 'the prior version is not published')
        return {obligation: {'kind': 'publication_obligation',
                             'data': dict(data, state='published', observed_digest=p['observed_digest'])}}


def _owned(identity, kind):
    return (isinstance(identity, str) and identity.startswith(OWNED_PREFIXES)) or kind in OWNED_KINDS


def _guard_generic(store, operation, registration):
    """The registration with one more rule: whatever this command would write, no alias or
    document entity, recognized by its id or by its kind before or after. The original transition
    still decides everything else, and a snapshot command it could not guard stays refused."""
    inner, plain = registration.get('transaction_transition'), registration.get('transition')

    def transition(conn, parameters, before):
        if inner is None and 'snapshot_id' in parameters:
            raise store.StoreRefused('unregistered_inputs', 'snapshot command requires a connection-local guard')
        changes = inner(conn, parameters, before) if inner is not None else plain(parameters, before)
        for identity, change in changes.items():
            if _owned(identity, change['kind']) or _owned(identity, before.get(identity, {}).get('kind')):
                raise store.StoreRefused('allocation_owned', '%s cannot write %s: only the allocation commands do'
                                         % (operation, identity))
        return changes
    return dict(registration, transaction_transition=transition)


def attach(store, conn, domain_uuid, repositories):
    """Register the allocation commands on one store connection; returns the service. Every other
    command registered on the connection at this moment, the store's generic ones included, is
    guarded so that it cannot write the entities these commands own (a counter moved backwards or
    a version rewritten by upsert_entity would bypass every rule below)."""
    if any(operation in conn.command_registry for operation in OPERATIONS):
        raise SN.Refused('invalid_registration', 'connection already has an allocation authority')
    service = Allocations(store, conn, domain_uuid, repositories)
    for operation, registration in dict(store.COMMAND_REGISTRY, **conn.command_registry).items():
        conn.command_registry[operation] = _guard_generic(store, operation, registration)
    for operation, body in zip(OPERATIONS, (service._t_enable, service._t_allocate, service._t_edit, service._t_publish)):
        conn.command_registry[operation] = {'transaction_transition': service._transition(body),
                                            'writes': ('entities', 'journal', 'commands', 'nonces')}
    return service
