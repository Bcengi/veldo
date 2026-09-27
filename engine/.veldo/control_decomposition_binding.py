"""VELDO-0085 publication binding, shared by backlog and eligibility.

Only the decomposition writer emits the JSON-valued front matter below. Reading that
format needs no engine parser outside the Gate's validator snapshot. Historical specs
without an authority document retain their existing admission path.
"""
import hashlib
import json
from pathlib import Path


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
    fields = {}
    for line in document['content'].splitlines()[1:]:
        if line == '-' * 3:
            break
        key, sep, value = line.partition(': ')
        if sep and key in ('id', 'decomposition', 'depends_on'):
            try:
                fields[key] = json.loads(value)
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
