"""Publishing accepted documents into a checkout, and reading them back (VELDO-0037, R73).

WHAT THIS IS. The filesystem half of R73. control_alias commits an accepted document version and
its pending publication obligation; afterwards this publisher materializes EXACTLY those accepted
bytes at the version's declared path and then records the publication through the store, carrying
the digest of the bytes it made visible. SQLite and a worktree never pretend to share one atomic
write: the store commit is the acceptance, the file is a projection of it, and the obligation stays
pending until the projection exists.

  version 1   exclusive creation: a hard link of a fully written, fsynced, verified temporary
              file, so an existing path (anyone's bytes) refuses publication_conflict.
  version N   atomic replacement (rename) of the declared path, only when the file there is still
              the prior accepted version's bytes and that version is recorded published;
              otherwise publication_conflict or publication_order, and nothing is overwritten.

READERS consume only published versions. read_published() takes the newest version whose
obligation is recorded published, reads the complete file, and compares its digest, the recorded
publication digest, the source mapping, alias and version with the accepted store records. Edited,
truncated or missing output refuses by name; the reader never substitutes checkout bytes.

NOT HERE (Release 2): recovery of a publication interrupted between rename and record, exclusion of
a second publisher process, and remote Git confirmation. Standard library only.
"""
import importlib.util
import os
from pathlib import Path, PurePosixPath
import stat


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, Path(__file__).with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AL = _sibling('document_alias', 'control_alias.py')
SN = AL.SN


def accepted(store, conn, repository, alias, version):
    """One accepted version, its obligation and its exact bytes, verified against the store digest."""
    problem = AL.CLAIM.unit_id_problem(alias)
    if problem is not None:
        raise SN.Refused('invalid_unit_id', problem)
    record = SN.entity(store, conn, AL.version_id(repository, alias, version))['value']
    obligation = SN.entity(store, conn, AL.publication_id(repository, alias, version))['value']
    if record is None or obligation is None:
        raise SN.Refused('missing_authority', 'no accepted %s version %r' % (alias, version))
    data = record['data']
    body = data['content'].encode('utf-8')
    if SN.digest(body) != data['digest'] or obligation['data']['digest'] != data['digest']:
        raise SN.Refused('accepted_digest_mismatch', '%s@%r' % (alias, version))
    return data, obligation['data'], body


# Every declared path is reached from the checkout root one component at a time through directory
# descriptors opened without following symlinks, so no symlink anywhere on the path is honoured and
# the file reached is necessarily inside the root: safe_path already refused '..' and absolute paths.
_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
_FILE = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)


def _unsafe(path, error):
    return SN.Refused('unsafe_path', '%s is reached through a symlink or a non-directory (%s)'
                      % (path, error.strerror or type(error).__name__))


def _open_parent(root, path, create):
    """A descriptor for the declared path's parent directory and the file's own name, walked from
    the checkout root with no symlink followed. Missing directories are created only when asked."""
    parts = PurePosixPath(SN.safe_path(path)).parts
    handle = os.open(root, _DIRECTORY)
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, _DIRECTORY, dir_fd=handle)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o755, dir_fd=handle)
                except FileExistsError:
                    pass
                child = os.open(part, _DIRECTORY, dir_fd=handle)
            os.close(handle)
            handle = child
    except FileNotFoundError:
        os.close(handle)
        raise
    except OSError as error:
        os.close(handle)
        raise _unsafe(path, error) from error
    return handle, parts[-1]


def _read_at(parent, name, path):
    """The complete bytes of one regular file in an open directory, never through a symlink;
    None when there is no file of that name."""
    try:
        handle = os.open(name, _FILE, dir_fd=parent)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise _unsafe(path, error) from error
    with os.fdopen(handle, 'rb') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise SN.Refused('publication_conflict', '%s is not a regular file' % path)
        return source.read()


def read_exact(root, path):
    """The bytes at a declared path under a checkout root, or None when nothing is there."""
    try:
        parent, name = _open_parent(root, path, create=False)
    except FileNotFoundError:
        return None
    try:
        return _read_at(parent, name, path)
    finally:
        os.close(parent)


class Publisher:
    """Materializes accepted versions under one checkout root for an Allocations service."""

    def __init__(self, service, root):
        """Bound to the one enrolled repository whose identity (root commits) the checkout at
        `root` carries; a directory that is no checkout of an enrolled repository binds nothing."""
        self.service, self.root = service, Path(os.path.realpath(root))
        identity = AL.checkout_identity(self.root)
        matches = [repository for repository, roots in service.identities.items() if identity and roots == identity]
        if len(matches) != 1:
            raise SN.Refused('wrong_repository', '%s is not a checkout of an enrolled repository' % self.root)
        self.repository = matches[0]

    def visible_digest(self, path):
        """The digest of the bytes a reader of this checkout sees at a declared path, or None."""
        body = read_exact(self.root, path)
        return None if body is None else SN.digest(body)

    def _materialize(self, path, body, digest, exclusive):
        parent, name = _open_parent(self.root, path, create=True)
        temporary = '.%s.%s.publishing' % (name, os.urandom(8).hex())
        try:
            handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=parent)
            try:
                with os.fdopen(handle, 'wb') as output:
                    output.write(body)
                    output.flush()
                    os.fsync(output.fileno())
                observed = SN.digest(_read_at(parent, temporary, path))
                if observed != digest:
                    raise SN.Refused('publication_mismatch', 'written bytes differ from the accepted digest')
                if exclusive:
                    os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
                else:
                    os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
            except FileExistsError as error:
                raise SN.Refused('publication_conflict', '%s already exists' % name) from error
            finally:
                try:
                    os.unlink(temporary, dir_fd=parent)
                except FileNotFoundError:
                    pass
            os.fsync(parent)
            # What a reader now sees at the declared name, re-read through the same safe walk.
            visible = _read_at(parent, name, path)
        finally:
            os.close(parent)
        if visible is None or SN.digest(visible) != digest:
            raise SN.Refused('publication_mismatch', 'the declared path does not show the accepted bytes')
        return SN.digest(visible)

    def publish(self, repository, alias, version, principal, **signing):
        service = self.service

        def work(event):
            event.update(alias=alias, version=version)
            if repository != self.repository:
                raise SN.Refused('wrong_repository', 'this checkout is repository %s, not %r' % (self.repository, repository))
            data, obligation, body = accepted(service.store, service.conn, repository, alias, version)
            current = read_exact(self.root, data['path'])
            if obligation['state'] == 'published':
                if current is None or SN.digest(current) != data['digest']:
                    raise SN.Refused('document_mismatch', 'published %s@%d is no longer visible' % (alias, version))
                return {'reused': True, 'alias': alias, 'version': version, 'digest': data['digest']}
            if current is not None and SN.digest(current) == data['digest']:
                observed = SN.digest(current)   # visible already; only the record was missing
            elif version == 1:
                if current is not None:
                    raise SN.Refused('publication_conflict', 'declared path holds bytes nobody accepted')
                observed = self._materialize(data['path'], body, data['digest'], exclusive=True)
            else:
                _, prior = service.current(AL.publication_id(repository, alias, version - 1))
                if prior is None or prior['state'] != 'published':
                    raise SN.Refused('publication_order', 'version %d is not published yet' % (version - 1))
                if current is None or SN.digest(current) != data['prior_digest']:
                    raise SN.Refused('publication_conflict', 'declared path is not the prior accepted version')
                observed = self._materialize(data['path'], body, data['digest'], exclusive=False)
            return service.record_publication(repository, alias, version, observed, principal, **signing)

        def guarded(event):
            # This module's refusals are reported through the service's store vocabulary.
            try:
                return work(event)
            except SN.Refused as error:
                raise service.store.StoreRefused(error.code, error.detail) from error

        return service.observe('publish_document', {'repository_uuid': repository,
                                                    'request_id': 'publish:%s@%s' % (alias, version)}, guarded)


def read_published(store, conn, repository, alias, root):
    """The reader-visible complete document for the newest PUBLISHED version, checked against the
    accepted records; any disagreement refuses by name."""
    problem = AL.CLAIM.unit_id_problem(alias)
    if problem is not None:
        raise SN.Refused('invalid_unit_id', problem)
    head = SN.entity(store, conn, AL.head_id(repository, alias))
    if head['value'] is None:
        raise SN.Refused('missing_authority', 'alias %s has no accepted document' % alias)
    version = head['version']
    while version > 0:
        publication = SN.entity(store, conn, AL.publication_id(repository, alias, version))['value']
        if publication is not None and publication['data']['state'] == 'published':
            break
        version -= 1
    if version == 0:
        raise SN.Refused('missing_publication', 'no published version of %s' % alias)
    data, obligation, _ = accepted(store, conn, repository, alias, version)
    mapping = SN.entity(store, conn, AL.source_id(repository, data['source_key']))['value']
    if (mapping is None or mapping['data']['alias'] != alias or mapping['data']['version'] != version
            or mapping['data']['digest'] != data['digest'] or mapping['data']['source'] != data['source']):
        raise SN.Refused('document_mismatch', 'source mapping disagrees with %s@%d' % (alias, version))
    kind = SN.entity(store, conn, AL.kind_id(repository, data['kind']))['value']
    recorded = (kind or {}).get('data', {}).get('root_commits')
    if not recorded or AL.checkout_identity(os.path.realpath(root)) != recorded:
        raise SN.Refused('wrong_repository', '%s is not a checkout of repository %s' % (root, repository))
    try:
        body = read_exact(os.path.realpath(root), data['path'])
    except OSError as error:
        raise SN.Refused('missing_publication', '%s is not readable' % data['path']) from error
    if body is None:
        raise SN.Refused('missing_publication', '%s is not there' % data['path'])
    observed = SN.digest(body)
    if observed != data['digest'] or obligation['observed_digest'] != data['digest']:
        raise SN.Refused('document_mismatch', '%s@%d published bytes differ from the accepted record' % (alias, version))
    return {'alias': alias, 'version': version, 'digest': observed, 'source': data['source'],
            'role': data['role'], 'path': data['path'], 'body': body}
