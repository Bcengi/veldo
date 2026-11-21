"""Retain exact teeth edits, full receipts and restored controls without editing source.

Run through the externally supplied load wrapper. This is ticket evidence, not
an invocation of the canonical gate or independent review.
"""
import argparse
import base64
import difflib
import gzip
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = Path(__file__).resolve().parent


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def retain(name, result):
    data = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
    # Store the actual receipts unchanged. A personal path is a failed proof
    # build, never something silently edited out of a digest-bound receipt.
    assert b'/home/' not in data and b'/Users/' not in data
    shared = {}
    def pack(value, key=None):
        if key in ('combinations', 'unsupported_combinations', 'not_qualified_families'):
            identity = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
            shared[identity] = value
            return {'$shared': identity}
        if isinstance(value, dict):
            return {k: pack(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [pack(v) for v in value]
        return value
    packed = pack(result)
    archive = dict(schema='veldo.0113-lossless-receipts/v1', result=packed, shared=shared,
                   receipt_sha256=hashlib.sha256(data).hexdigest())
    (DESTINATION / (name + '.json.gz')).write_bytes(gzip.compress(
        json.dumps(archive, sort_keys=True, separators=(',', ':')).encode(), mtime=0))
    assert json.dumps(read_receipts(DESTINATION / (name + '.json.gz')),
                      sort_keys=True, separators=(',', ':')).encode() == data
    rows = {name: {k: v for k, v in row.items() if k != 'observation_receipts'}
            for name, row in result['rows'].items()}
    summary = dict(name=name, rows=rows, metrics=result['metrics'],
                   qualification=result['qualification'], faults_ok=result['faults_ok'],
                   receipt_sha256=hashlib.sha256(data).hexdigest())
    (DESTINATION / (name + '.txt')).write_text(json.dumps(summary, indent=2) + '\n')
    print(name, {k: v['status'] for k, v in result['rows'].items()}, flush=True)
    return summary


def read_archive(path):
    archive = json.loads(gzip.decompress(Path(path).read_bytes()))
    if archive.get('schema') == 'veldo.0113-compressed/v1':
        archive = json.loads(lzma.decompress(base64.b64decode(archive['payload'])))
    return archive


def compressed_archive(archive):
    raw = json.dumps(archive, sort_keys=True, separators=(',', ':')).encode()
    envelope = dict(schema='veldo.0113-compressed/v1', encoding='lzma+base64',
                    payload=base64.b64encode(lzma.compress(raw, preset=9 | lzma.PRESET_EXTREME)).decode())
    return gzip.compress(json.dumps(envelope, sort_keys=True).encode(), mtime=0)


def read_receipts(path):
    archive = read_archive(path)
    shared = archive.get('shared')
    if shared is None:
        shared = json.loads(gzip.decompress((Path(path).parent / archive['shared_file']).read_bytes()))
    def unpack(value):
        if isinstance(value, dict):
            if set(value) == {'$shared'}:
                return shared[value['$shared']]
            return {k: unpack(v) for k, v in value.items()}
        return [unpack(v) for v in value] if isinstance(value, list) else value
    result = unpack(archive['result'])
    data = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
    assert hashlib.sha256(data).hexdigest() == archive['receipt_sha256']
    return result


def compact_receipts():
    """After all runs, intern repeated source/capability tables across archives."""
    shared, archives = {}, {}
    def pack(value, key=None):
        if key in ('combinations', 'unsupported_combinations', 'not_qualified_families', 'scanned_files'):
            identity = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
            shared[identity] = value
            return {'$shared': identity}
        if isinstance(value, dict):
            return {k: pack(v, k) for k, v in value.items()}
        return [pack(v) for v in value] if isinstance(value, list) else value
    for path in DESTINATION.glob('*.json.gz'):
        archive = read_archive(path)
        if not isinstance(archive, dict) or not str(archive.get('schema', '')).startswith('veldo.0113-lossless-receipts/'):
            continue
        result = read_receipts(path)
        archives[path] = dict(schema='veldo.0113-lossless-receipts/v2', result=pack(result),
                              shared_file='shared-tables.json.gz', receipt_sha256=archive['receipt_sha256'])
    (DESTINATION / 'shared-tables.json.gz').write_bytes(gzip.compress(
        json.dumps(shared, sort_keys=True, separators=(',', ':')).encode(), mtime=0))
    for path, archive in archives.items():
        path.write_bytes(compressed_archive(archive))
        read_receipts(path)  # Verify every original receipt digest again after compaction.
    return sum(p.stat().st_size for p in DESTINATION.rglob('*') if p.is_file())


def run(name, case=None, mode='baseline'):
    with tempfile.TemporaryDirectory(prefix='v113-proof-') as temporary:
        root = Path(temporary)
        helper = load(ROOT / 'scripts/fixtures/no_autostart.py', 'no_autostart_copy')
        helper.copy_production(ROOT, root)
        shutil.copytree(ROOT / 'scripts/fixtures', root / 'scripts/fixtures',
                        ignore=shutil.ignore_patterns('__pycache__'))
        if case:
            relative = Path('scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo')) / case['module']
            target = root / relative
            before = target.read_text()
            assert before.count(case['old']) == 1
            after = before.replace(case['old'], case['new'])
            (DESTINATION / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                before.splitlines(True), after.splitlines(True), fromfile='a/' + str(relative),
                tofile='b/' + str(relative))))
            target.write_text(after if mode == 'mutant' else before)
        module = load(root / 'scripts/fixtures/no_autostart.py', 'consumer_proof')
        result = module.qualify(root)
        summary = retain(name, result)
        check_result(result, case if mode == 'mutant' else None)
        return summary


def check_result(result, case=None):
    """Assess complete saved JSON as well as a newly captured result."""
    assert result['expected'] == sorted(result['completed'])
    assert len(result['expected']) == len(set(result['completed']))
    assert all(c['outcome'].get('invoked') and c['outcome'].get('refused')
               for c in result['cases'] if 'receipt' in c), 'required client refusal did not complete'
    assert result['faults_driven'], 'observer fault matrix was not exercised'
    if case:
        for row in case['rows']:
            assert result['rows'][row]['status'] == 'FAIL', (case['name'], row)
        if case['name'] == 'autostart113-reaped-fallback':
            assert any(c.get('effects', {}).get('forbidden_births') for c in result['cases'])
            assert all(p['terminal'] for c in result['cases']
                       for p in c.get('effects', {}).get('forbidden_births', []))
        if case['name'] == 'autostart113-transient-abstract-listener':
            assert any(c.get('effects', {}).get('services') for c in result['cases'])
    else:
        assert all(row['status'] != 'FAIL' for row in result['rows'].values()), result['rows']
        assert result['faults_ok'] and all(result['protocol_controls'].values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case')
    parser.add_argument('--control', choices=('baseline', 'restored'))
    parser.add_argument('--label')
    parser.add_argument('--reassess', help='assess saved JSON; does not rerun the observer')
    args = parser.parse_args()
    teeth = load(ROOT / 'scripts/check_teeth_mutations.py', 'teeth_proof')
    definitions = [c for c in teeth.cases() if c['finding'] == 113]
    if args.reassess:
        case = next((c for c in definitions if c['name'] == args.reassess), None)
        assert case or args.reassess in ('baseline', 'restored', 'restored-full-matrix')
        print('SAVED RECEIPT ASSESSMENT; no new observer invocation', flush=True)
        result = read_receipts(DESTINATION / (args.reassess + '.json.gz'))
        check_result(result, case)
    elif args.control:
        run(args.label or args.control)
    elif args.case:
        case = next(c for c in definitions if c['name'] == args.case)
        run(case['name'], case, 'mutant')
    else:
        run('baseline')
        for case in definitions:
            run(case['name'], case, 'mutant')
        run('restored')


if __name__ == '__main__':
    main()
