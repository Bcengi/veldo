#!/usr/bin/env python3
"""Export immutable historical inputs once; the suite never runs this script.

Run from any directory with python3 proof/VELDO-0189/older/generate.py.
The recorded census endpoints make later regeneration reproducible.
"""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('fixture_git', ROOT / '.veldo/git_process.py')
git = importlib.util.module_from_spec(spec)
spec.loader.exec_module(git)


def read(*args, text=True, **kwargs):
    return git.run(['git', '-C', str(ROOT), *args], capture_output=True,
                   text=text, check=True, **kwargs).stdout


def main():
    previous = HERE / 'digests.json'
    endpoints = json.loads(previous.read_text())['census_heads'] if previous.exists() else {
        name: read('rev-parse', name).strip() for name in ('HEAD', 'main')}
    manifest = {'schema': 'veldo.older-engines/v1', 'census_heads': endpoints, 'files': {}}

    def write(name, data, **metadata):
        (HERE / name).write_bytes(data)
        manifest['files'][name] = dict(sha256=hashlib.sha256(data).hexdigest(), **metadata)

    for short in ('8bc34e94', '971186ac'):
        commit = read('rev-parse', short + '^{commit}').strip()
        archive = read('archive', '--format=tar', commit, '.veldo', text=False)
        write(short + '.tar.gz', gzip.compress(archive, mtime=0), commit=commit,
              archive_sha256=hashlib.sha256(archive).hexdigest())

    anchor = read('rev-parse', '8bc34e94^{commit}').strip()
    chain = read('rev-list', '--first-parent', endpoints['HEAD']).split()
    assert anchor in chain
    chain = chain[:chain.index(anchor) + 1]
    main_chain = read('rev-list', '--first-parent', endpoints['main']).split()
    main_chain = main_chain[:main_chain.index(anchor) + 1] if anchor in main_chain else []
    commits = chain + [c for c in main_chain if c not in chain]
    batch = read('cat-file', '--batch-check', input=''.join(
        c + ':.veldo/control_service.py\n' for c in commits)).splitlines()
    blobs = {}
    for commit, line in zip(commits, batch):
        blob, kind, size = line.split()
        assert kind == 'blob'
        if blob not in blobs:
            blobs[blob] = {'commits': [], 'source': read('cat-file', 'blob', blob)}
        blobs[blob]['commits'].append(commit)
    census = dict(anchor=anchor, chain=chain, main=main_chain, blobs=blobs)
    write('census.json.gz', gzip.compress((json.dumps(census, sort_keys=True, indent=1) + '\n').encode(), mtime=0))
    previous.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')
    print('Exported two exact .veldo archives and %d commits / %d installers' % (len(commits), len(blobs)))


if __name__ == '__main__':
    main()
