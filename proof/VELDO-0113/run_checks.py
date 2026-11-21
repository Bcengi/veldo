"""Retain exact teeth edits, full receipts and restored controls without editing source.

Run through the externally supplied load wrapper. This is ticket evidence, not
an invocation of the canonical gate or independent review.
"""
import argparse
import difflib
import gzip
import hashlib
import importlib.util
import json
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
    assert read_receipts(DESTINATION / (name + '.json.gz')) == result
    summary = dict(name=name, rows=result['rows'], metrics=result['metrics'],
                   qualification=result['qualification'], faults_ok=result['faults_ok'],
                   receipt_sha256=hashlib.sha256(data).hexdigest())
    (DESTINATION / (name + '.txt')).write_text(json.dumps(summary, indent=2) + '\n')
    print(name, {k: v['status'] for k, v in result['rows'].items()}, flush=True)
    return summary


def read_receipts(path):
    archive = json.loads(gzip.decompress(Path(path).read_bytes()))
    def unpack(value):
        if isinstance(value, dict):
            if set(value) == {'$shared'}:
                return archive['shared'][value['$shared']]
            return {k: unpack(v) for k, v in value.items()}
        return [unpack(v) for v in value] if isinstance(value, list) else value
    result = unpack(archive['result'])
    data = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
    assert hashlib.sha256(data).hexdigest() == archive['receipt_sha256']
    return result


def run(name, case=None, mode='baseline'):
    with tempfile.TemporaryDirectory(prefix='v113-proof-') as temporary:
        root = Path(temporary)
        helper = load(ROOT / 'scripts/fixtures/no_autostart.py', 'no_autostart_copy')
        helper.copy_production(ROOT, root)
        shutil.copytree(ROOT / 'scripts/fixtures', root / 'scripts/fixtures',
                        ignore=shutil.ignore_patterns('__pycache__'))
        if case:
            relative = Path('scripts/fixtures' if case.get('fixture') else '.veldo') / case['module']
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
        assert result['expected'] == sorted(result['completed'])
        assert len(result['expected']) == len(set(result['completed']))
        if mode == 'mutant':
            for row in case['rows']:
                assert result['rows'][row]['status'] == 'FAIL', (case['name'], row)
            if case['name'] == 'autostart113-reaped-fallback':
                assert any(c.get('effects', {}).get('forbidden_births') for c in result['cases'])
                assert all(p['terminal'] for c in result['cases']
                           for p in c.get('effects', {}).get('forbidden_births', []))
            if case['name'] == 'autostart113-transient-abstract-listener':
                assert any(c.get('effects', {}).get('services') for c in result['cases'])
        else:
            assert all(row['status'] != 'FAIL' for row in result['rows'].values()), summary
            assert result['faults_ok'] and all(result['protocol_controls'].values())
        return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case')
    parser.add_argument('--control', choices=('baseline', 'restored'))
    parser.add_argument('--label')
    args = parser.parse_args()
    teeth = load(ROOT / 'scripts/check_teeth_mutations.py', 'teeth_proof')
    definitions = [c for c in teeth.cases() if c['finding'] == 113]
    if args.control:
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
