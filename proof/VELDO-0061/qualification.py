"""Select reviewed Codex evidence for the installed vendor binary, never qualify it implicitly.

VELDO_CODEX_BINARY selects a private vendor executable for scoped offline suites.
The active runtime record remains the production pin. Historical records permit
regression testing the previous install during a reviewed pin transition.
"""
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def select(binary=None):
    historical = json.loads((HERE.parent / 'VELDO-0062/cli-formats.json').read_text())['codex']
    binary = Path(binary or os.environ.get('VELDO_CODEX_BINARY') or historical['binary'])
    if not binary.is_absolute() or binary.resolve() != binary:
        raise ValueError('invalid_input:engine_link_or_path')
    package = next((p for p in binary.parents if (p / 'package.json').is_file()), None)
    manifest = json.loads((package / 'package.json').read_text()) if package else {}
    version = str(manifest.get('version', '')).split('-', 1)[0]
    # Only an explicitly retained reviewed record can select evidence. A package
    # manifest supplies identity, never authority or a newly generated digest.
    if not version or any(c not in '0123456789.' for c in version):
        raise ValueError('missing_evidence:engine_qualification')
    record_path = HERE / ('codex-qualification-' + version + '.json')
    if not record_path.is_file():
        raise ValueError('missing_evidence:engine_qualification:' + version)
    record = json.loads(record_path.read_text())
    if (manifest.get('name') != record['package'] or manifest.get('version') != record['package_version']
            or str(binary.relative_to(package)) != record['executable'] or version != record['version']):
        raise ValueError('invalid_input:engine_package')
    old = version == '0.154.0'
    events = historical if old else json.loads((HERE / ('codex-formats-' + version + '.json')).read_text())
    items_path = HERE / ('codex-exec.json' if old else 'codex-exec-' + version + '.json')
    items = json.loads(items_path.read_text())
    if not (events['version'] == items['version'] == record['version']
            and events['sha256'] == items['sha256'] == record['sha256']):
        raise ValueError('stale_subject:codex_evidence')
    with binary.open('rb') as handle:
        digest = 'sha256:' + hashlib.file_digest(handle, 'sha256').hexdigest()
    if digest != record['sha256']:
        raise ValueError('stale_subject:engine_digest')
    return dict(binary=str(binary), record=record, record_path=record_path,
                events=events, items=items, items_path=items_path)
