"""Accepted snapshot bytes and explicit-watermark materialization (VELDO-0035).

The authority supplies the store, connection and enrolled repository coordinates. Accepted
revision entities contain commit, documents {output_path: sha256}, and statuses
{output_path: entity_id}. This is a data seam, not admission or eligibility authority.
No working-tree fallback, current pointer, recovery protocol or background process.
"""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re


def _git_boundary():
    spec = importlib.util.spec_from_file_location('snapshot_git', Path(__file__).with_name('git_process.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _git_boundary()
SCHEMA = 'veldo.control_snapshot/v1'


class Refused(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(code + ': ' + detail)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def digest(body):
    return 'sha256:' + hashlib.sha256(body).hexdigest()


def safe_path(value):
    if (not isinstance(value, str) or not value or '\\' in value
            or str(PurePosixPath(value)) != value or PurePosixPath(value).is_absolute()
            or '..' in PurePosixPath(value).parts or value in ('.', 'manifest.json')):
        raise Refused('invalid_input', 'invalid projection path')
    return value


def artifact(repo, commit, path, expected):
    safe_path(path)
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
        raise Refused('invalid_input', 'accepted commit must be an exact object id')
    result = _git_process.run(['git', '-C', str(repo), 'cat-file', 'blob', commit + ':' + path],
                     capture_output=True, timeout=15)
    if result.returncode:
        raise Refused('missing_artifact', path)
    body = result.stdout
    if digest(body) != expected:
        raise Refused('artifact_digest_mismatch', path)
    return body


def entity(store, conn, identity):
    row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
    if row is None:
        return {'id': identity, 'version': 0, 'digest': digest(canonical(None)), 'value': None}
    value = {'kind': row[0], 'version': row[1], 'data': json.loads(row[3])}
    if store.digest_of(value) != row[2]:
        raise Refused('input_digest_mismatch', identity)
    return {'id': identity, 'version': row[1], 'digest': row[2], 'value': value}


def load(store, conn, identity, domain_uuid, repository_uuid):
    item = entity(store, conn, identity)
    if item['value'] is None or item['value']['kind'] != 'control_snapshot':
        raise Refused('missing_snapshot', identity)
    value = item['value']['data']
    if (value.get('schema') != SCHEMA or value.get('domain_uuid') != domain_uuid
            or value.get('repository_uuid') != repository_uuid or value.get('snapshot_id') != identity):
        raise Refused('snapshot_identity_mismatch', identity)
    return value


def members(snapshot, repo):
    """Read every accepted document and captured status; return exact bytes by output path."""
    paths = [safe_path(path) for path in (*snapshot['documents'], *snapshot['statuses'])]
    inventory = set(paths) | {'manifest.json'}
    if len(paths) != len(set(paths)) or any(
            str(parent) in inventory for path in paths for parent in PurePosixPath(path).parents):
        raise Refused('invalid_input', 'overlapping projection paths')
    result = {}
    for path, expected in snapshot['documents'].items():
        result[safe_path(path)] = artifact(repo, snapshot['accepted_commit'], path, expected)
    for path, value in snapshot['statuses'].items():
        if path in result:
            raise Refused('invalid_input', 'overlapping document and status projection')
        result[safe_path(path)] = canonical(value)
    return result


def manifest(snapshot, bodies):
    return {'schema': SCHEMA, 'snapshot_id': snapshot['snapshot_id'],
            'domain_uuid': snapshot['domain_uuid'], 'repository_uuid': snapshot['repository_uuid'],
            'accepted_commit': snapshot['accepted_commit'], 'watermark': snapshot['watermark'],
            'snapshot_digest': digest(canonical(snapshot)),
            'members': {path: digest(body) for path, body in bodies.items()}}


def materialize(snapshot, repo, destination):
    """Publish one complete revision at an explicit path; existing revisions are never updated.

    The manifest is the completion marker and is written last. Readers only consume a named
    complete revision. Crash recovery and atomic current-pointer switching are deferred.
    """
    bodies = members(snapshot, repo)
    destination = Path(destination)
    if destination.exists():
        raise Refused('projection_exists', str(destination))
    destination.mkdir(parents=True)
    for path, body in bodies.items():
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    record = manifest(snapshot, bodies)
    (destination / 'manifest.json').write_bytes(canonical(record))
    return record


def read_materialized(snapshot, repo, destination):
    """Compare a published revision to an accepted STORE snapshot, not to its own manifest alone."""
    expected = manifest(snapshot, members(snapshot, repo))
    destination = Path(destination)
    try:
        actual = json.loads((destination / 'manifest.json').read_bytes())
        if actual != expected:
            raise Refused('projection_mismatch', snapshot['snapshot_id'])
        bodies = {path: (destination / safe_path(path)).read_bytes() for path in expected['members']}
    except (OSError, ValueError) as error:
        raise Refused('missing_projection', snapshot['snapshot_id']) from error
    if {path: digest(body) for path, body in bodies.items()} != expected['members']:
        raise Refused('projection_mismatch', snapshot['snapshot_id'])
    return {'manifest': actual, 'members': bodies}
