"""VELDO-0085 publication binding, shared by backlog and eligibility.

Accepted specification bytes are read with the repository's one document parser.
Historical specs without an authority document retain their existing admission path.
"""
import hashlib
import importlib.util
import json
from pathlib import Path


def _front_matter(content):
    # Loading Gate must not execute a workspace parser. Only a bound accepted
    # document needs this reader; architecture keeps its own validator snapshot.
    spec = importlib.util.spec_from_file_location('decomposition_yamlish', Path(__file__).with_name('yamlish.py'))
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    return reader.front_matter(content)


def row(conn, identity):
    found = conn.execute('SELECT data FROM entities WHERE id=?', (identity,)).fetchone()
    return json.loads(found[0]) if found else None


def head_id(repository, alias):
    return 'document/%s/%s' % (repository, alias)


def binding(conn, repository, alias, workspace):
    """The current complete published specification and its decomposition metadata.

    Returns (binding, problems). An authority head, even if unpublished, opts this
    alias into authority publication; a missing head is the historical file path.
    """
    hid = head_id(repository, alias)
    head = row(conn, hid)
    if head is None:
        return None, []
    version = head['version']
    document = row(conn, hid + '@%d' % version)
    obligation = row(conn, 'publication/%s/%s@%d' % (repository, alias, version))
    if not document or not obligation or obligation.get('state') != 'published':
        return None, ['missing_evidence:specification_publication']
    digest = document['digest']
    body = document['content'].encode('utf-8')
    try:
        visible = (Path(workspace) / document['path']).read_bytes() if workspace else None
    except OSError:
        visible = None
    if (visible != body or 'sha256:' + hashlib.sha256(body).hexdigest() != digest
            or obligation.get('observed_digest') != digest):
        return None, ['stale_subject:specification_bytes']
    try:
        fields = _front_matter(document['content']) or {}
    except ValueError:
        return None, ['invalid_input:specification_binding']
    meta = fields.get('decomposition')
    if fields.get('id') != alias or not isinstance(meta, dict):
        return None, ['invalid_input:specification_binding']
    if fields.get('depends_on') != meta.get('specification_dependencies'):
        return None, ['invalid_input:specification_dependencies']
    return dict(alias=alias, version=version, digest=digest, path=document['path'],
                source=document['source'], role=document['role'], **meta), []


def problems(conn, repository, unit, workspace):
    """A bound unit cannot execute or be admitted on edited or unpublished bytes."""
    expected = unit.get('specification_document')
    if expected is None:
        return []
    found, errors = binding(conn, repository, expected['alias'], workspace)
    if errors:
        return errors
    if found != expected:
        return ['stale_subject:specification_revision']
    if (found['backlog_item'] != unit.get('backlog_item_uuid') or found['unit'] != unit.get('uuid')
            or found['dependencies'] != unit.get('depends_on')):
        return ['invalid_input:unit_ownership']
    return []
