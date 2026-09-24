#!/usr/bin/env python3
"""Regenerate engine/runtime/langgraph-records.json from the registry (VELDO-0045 AC1).

    python3 -B proof/VELDO-0045/records.py SCRATCH_DIR

Reads, for every package in .veldo/control_graph_lock.py, TODAY's PyPI JSON for its exact release
(https://pypi.org/pypi/<name>/<version>/json) and for the project (https://pypi.org/pypi/<name>/json, the latest
release), and the PEP 740 provenance of its locked wheel from the PyPI integrity API
(https://pypi.org/integrity/<name>/<version>/<wheel>/provenance; a 404 is recorded as no published
attestation). It downloads the one locked wheel from the URL the registry serves, refuses it unless
its sha256 equals both the lock and the registry, verifies every member of the wheel against the
wheel's own RECORD, and records the wheel's content digest: sha256 over the sorted "path,hash" rows of
that RECORD, leaving out the RECORD row itself and the .data/scripts/ rows pip rewrites when it
installs them. Origin and approval are carried from the reviewed VELDO-0043 closure
(proof/VELDO-0043/dependency-closure.json); the SPDX expression is the registry's license expression
when it declares one, otherwise its license field in SPDX form (the three non-SPDX spellings are
mapped below). Writes the canonical file and this repository's installed copy byte-identically.
Needs the network; never run by a suite or the gate.
"""
import base64
import csv
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPDX = {'Apache License, Version 2.0': 'Apache-2.0', 'Modified BSD License': 'BSD-3-Clause',
        'Apache 2.0': 'Apache-2.0'}
ROOT_APPROVAL = 'chosen software: actual LangGraph is required by owner Telegram 28848 and R34'


def fetch(url, scratch, name):
    cached, marker = scratch / name, scratch / (name + '.status')
    if cached.is_file() and marker.is_file():
        return int(marker.read_text()), cached.read_bytes()
    try:
        with urllib.request.urlopen(url, timeout=60) as reply:
            status, body = reply.status, reply.read()
    except urllib.error.HTTPError as error:
        status, body = error.code, error.read()
    if status in (200, 404):
        cached.write_bytes(body)
        marker.write_text(str(status))
    return status, body


def b64(data):
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b'=').decode()


def content(wheel):
    archive = zipfile.ZipFile(wheel)
    records = [n for n in archive.namelist() if n.endswith('.dist-info/RECORD')]
    assert len(records) == 1, (wheel, records)
    rows = [r for r in csv.reader(io.StringIO(archive.read(records[0]).decode())) if r]
    kept = []
    for path, digest, _size in rows:
        if path == records[0]:
            continue
        assert b64(archive.read(path)) == digest, (wheel, path, 'member does not match the wheel RECORD')
        if '.data/scripts/' in path:
            continue
        kept.append('%s,%s' % (path, digest))
    listed = {r[0] for r in rows}
    members = {n for n in archive.namelist() if not n.endswith('/')}  # directory entries carry no content
    assert members <= listed | {records[0]}, (wheel, 'a member the RECORD does not list')
    return {'files': len(kept), 'sha256': hashlib.sha256('\n'.join(sorted(kept)).encode()).hexdigest()}


def main(scratch):
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('lock', ROOT / '.veldo/control_graph_lock.py')
    lock = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lock)
    reviewed = {c['name']: c for c in json.loads((ROOT / 'proof/VELDO-0043/dependency-closure.json').read_text())['closure']}
    packages = []
    for name, version, wheel, sha256 in lock.PACKAGES:
        status, body = fetch('https://pypi.org/pypi/%s/%s/json' % (name, version), scratch, '%s-%s.json' % (name, version))
        assert status == 200, (name, status)
        release = json.loads(body)
        info = release['info']
        _, latest_body = fetch('https://pypi.org/pypi/%s/json' % name, scratch, '%s-latest.json' % name)
        latest = json.loads(latest_body)['info']['version']
        status, provenance = fetch('https://pypi.org/integrity/%s/%s/%s/provenance' % (name, version, wheel),
                                   scratch, '%s-%s.provenance.json' % (name, version))
        attestation = None
        if status == 200:
            bundles = json.loads(provenance)['attestation_bundles']
            publisher = bundles[0]['publisher']
            attestation = {key: publisher.get(key) for key in ('kind', 'repository', 'workflow', 'environment')}
        served = [u for u in release['urls'] if u['filename'] == wheel]
        assert len(served) == 1, (name, wheel)
        served = served[0]
        local = scratch / wheel
        if not local.is_file():
            with urllib.request.urlopen(served['url'], timeout=120) as reply:
                local.write_bytes(reply.read())
        actual = hashlib.sha256(local.read_bytes()).hexdigest()
        assert actual == sha256 == served['digests']['sha256'], (name, actual, sha256)
        expression, text = info.get('license_expression') or None, info.get('license') or None
        spdx = expression or SPDX.get(text, text)
        urls = {key.lower(): value for key, value in (info.get('project_urls') or {}).items()}
        source = next((urls[k] for k in ('source', 'source code', 'repository', 'code', 'github', 'homepage')
                       if urls.get(k)), info.get('home_page'))
        row = reviewed[name]
        record = {
            'name': name, 'version': version, 'wheel': wheel, 'sha256': served['digests']['sha256'],
            'url': served['url'], 'uploaded': served['upload_time_iso_8601'],
            'requires_python': served.get('requires_python'),
            'license': {'registry_license': text, 'registry_license_expression': expression, 'spdx': spdx,
                        'basis': 'license_expression' if expression else 'license'},
            'source': source, 'attestation': attestation, 'latest': latest,
            'origin': row['origin'],
            'approval': ROOT_APPROVAL if name == 'langgraph' else row['status'],
            'content': content(local),
        }
        if latest != version:
            record['capped_by'] = row.get('why_not_latest')
        packages.append(record)
    records = {
        'schema': 'veldo.runtime-records/v1',
        'lock': '.veldo/control_graph_lock.py', 'lock_digest': lock.digest(), 'root': lock.ROOT_REQUIREMENT,
        'python': lock.PYTHON, 'platform': lock.PLATFORM, 'read': datetime.date.today().isoformat(),
        'how': ('PyPI JSON for each exact release and project, the PyPI integrity API for PEP 740 provenance, '
                'and the locked wheel downloaded from the registry URL, verified against the lock and the '
                'registry sha256 and against its own RECORD. Regenerate with proof/VELDO-0045/records.py.'),
        'packages': packages,
    }
    text = json.dumps(records, indent=1, sort_keys=True) + '\n'
    for target in (ROOT / 'engine/runtime/langgraph-records.json', ROOT / '.veldo/runtime/langgraph-records.json'):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    print(json.dumps({'packages': len(packages), 'lock_digest': lock.digest(),
                      'attested': sum(1 for p in packages if p['attestation']),
                      'not_latest': {p['name']: p['latest'] for p in packages if p['latest'] != p['version']}}))


if __name__ == '__main__':
    main(sys.argv[1])
