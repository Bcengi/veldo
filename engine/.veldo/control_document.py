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
from pathlib import Path


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


def _fsync_directory(directory):
    handle = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


class Publisher:
    """Materializes accepted versions under one checkout root for an Allocations service."""

    def __init__(self, service, root):
        self.service, self.root = service, Path(root)

    def _materialize(self, target, body, digest, exclusive):
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.parent / ('.%s.%s.publishing' % (target.name, os.urandom(8).hex()))
        handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(handle, 'wb') as output:
                output.write(body)
                output.flush()
                os.fsync(output.fileno())
            observed = SN.digest(temporary.read_bytes())
            if observed != digest:
                raise SN.Refused('publication_mismatch', 'written bytes differ from the accepted digest')
            if exclusive:
                os.link(temporary, target)
            else:
                os.replace(temporary, target)
        except FileExistsError as error:
            raise SN.Refused('publication_conflict', '%s already exists' % target.name) from error
        finally:
            if temporary.exists():
                temporary.unlink()
        _fsync_directory(target.parent)
        return observed

    def publish(self, repository, alias, version, principal, **signing):
        service = self.service

        def work(event):
            event.update(alias=alias, version=version)
            if repository not in service.repositories:
                raise SN.Refused('wrong_repository', 'repository is not enrolled in this domain')
            data, obligation, body = accepted(service.store, service.conn, repository, alias, version)
            target = self.root / SN.safe_path(data['path'])
            if target.is_symlink() or (target.exists() and not target.is_file()):
                raise SN.Refused('publication_conflict', 'declared path is not a regular file')
            current = target.read_bytes() if target.exists() else None
            if obligation['state'] == 'published':
                if current is None or SN.digest(current) != data['digest']:
                    raise SN.Refused('document_mismatch', 'published %s@%d is no longer visible' % (alias, version))
                return {'reused': True, 'alias': alias, 'version': version, 'digest': data['digest']}
            if current is not None and SN.digest(current) == data['digest']:
                observed = SN.digest(current)   # visible already; only the record was missing
            elif version == 1:
                if current is not None:
                    raise SN.Refused('publication_conflict', 'declared path holds bytes nobody accepted')
                observed = self._materialize(target, body, data['digest'], exclusive=True)
            else:
                _, prior = service.current(AL.publication_id(repository, alias, version - 1))
                if prior is None or prior['state'] != 'published':
                    raise SN.Refused('publication_order', 'version %d is not published yet' % (version - 1))
                if current is None or SN.digest(current) != data['prior_digest']:
                    raise SN.Refused('publication_conflict', 'declared path is not the prior accepted version')
                observed = self._materialize(target, body, data['digest'], exclusive=False)
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
    try:
        body = (Path(root) / SN.safe_path(data['path'])).read_bytes()
    except OSError as error:
        raise SN.Refused('missing_publication', '%s is not readable' % data['path']) from error
    observed = SN.digest(body)
    if observed != data['digest'] or obligation['observed_digest'] != data['digest']:
        raise SN.Refused('document_mismatch', '%s@%d published bytes differ from the accepted record' % (alias, version))
    return {'alias': alias, 'version': version, 'digest': observed, 'source': data['source'],
            'role': data['role'], 'path': data['path'], 'body': body}
