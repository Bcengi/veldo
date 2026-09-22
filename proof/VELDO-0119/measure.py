"""Regenerate complete observations outside the checkout; retain compact proof only."""
import argparse
import collections
import contextlib
import hashlib
import io
import json
from pathlib import Path
import time
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def measure(root, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    ns = {'ROOT': root, 'json': json, 'expect': lambda name, ok: rows.append([name.split(':')[0], bool(ok)])}
    suite = root / 'scripts/suites/55_veldo_0119_agreement.py'
    started = time.monotonic()
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(suite.read_bytes(), str(suite), 'exec'), ns)
    elapsed = time.monotonic() - started
    result, consumer = ns['_r_result'], ns['_r_consumer']
    body = ''.join(consumer.encoded(r) + '\n' for r in result['records']).encode()
    (output_dir / 'observations.jsonl').write_bytes(body)
    inventory = ns['_r_inventory']
    targets = ns['_r_cases'].coverage_targets()
    (output_dir / 'targets.json').write_text(json.dumps({k: sorted(v) for k, v in targets.items()}, indent=2)+'\n')
    historical = []
    for kind in ('control', 'coverage'):
        for line, source in enumerate((root / ('proof/VELDO-0118/' + kind + '-disagreements.jsonl')).read_text().splitlines(), 1):
            case = json.loads(source)
            expected = ns['_r_oracle'].answer(ns['_r_oracle'].observe(case['source'], ns['_r_cap']))
            for name, reader in ns['_r_readers'].items():
                try:
                    actual = {'state': 'value', 'value': reader.parse(case['source'])}
                except ValueError as exc:
                    actual = {'state': 'refused', 'error': str(exc)}
                if consumer.encoded(actual) != consumer.encoded(expected):
                    historical.append({'record': kind + ':' + str(line), 'reader': name,
                                       'expected': expected, 'actual': actual})
    target_ref = 'proof/VELDO-0118/coverage-targets.json'
    assert json.loads((root / target_ref).read_text()) == json.loads(json.dumps({k: sorted(v) for k, v in targets.items()}))
    report = consumer.summary(result)
    report['target_inventory_ref'] = target_ref
    report['target_inventory_sha256'] = hashlib.sha256((root / target_ref).read_bytes()).hexdigest()
    report.update(rows=rows, elapsed_seconds=elapsed, normal_gate_invocations=2,
                  normal_gate_added_seconds=2*elapsed, raw_observations_sha256=hashlib.sha256(body).hexdigest(),
                  raw_observations_bytes=len(body), historical_records=218, historical_failures=historical,
                  controls=ns['_r_controls'])
    # Commit representative raw tags and DEL supplementary observations as well.
    samples = [r for r in result['records'] if r['source'] in ('a: true\n','a: 01\n','a: null\n','a: \x7f\n')]
    (output_dir / 'dialect-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    (output_dir / 'measurement.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'rows':rows, 'seconds':elapsed, 'normal_gate_added_seconds':2*elapsed,
                      'historical_failures':len(historical)}))
    if not all(ok for _, ok in rows) or historical:
        raise SystemExit(1)
    if 2*elapsed > 60:
        raise SystemExit('COST STOP: new suite alone exceeds 60 gate seconds')


def main():
    cli = argparse.ArgumentParser()
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output-dir', type=Path)
    mode.add_argument('--verify', action='store_true',
                      help='regenerate pinned observations in /tmp and check the committed SHA-256')
    args = cli.parse_args()
    if not args.verify:
        if args.output_dir.resolve().is_relative_to(ROOT):
            cli.error('--output-dir must be outside the repository')
        measure(ROOT, args.output_dir)
        return
    expected = json.loads((ROOT / 'proof/VELDO-0119/digests.json').read_text())['observations.jsonl']
    with tempfile.TemporaryDirectory(prefix='veldo-0119-observations-', dir='/tmp') as tmp:
        root = Path(tmp) / 'source'
        root.mkdir()
        archive = subprocess.check_output([
            'git', 'archive', expected['source_commit'], 'scripts/fixtures',
            'scripts/suites/55_veldo_0119_agreement.py', '.veldo/yamlish.py',
            'engine/.veldo/yamlish.py', 'proof/VELDO-0118'], cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(archive)) as files:
            files.extractall(root, filter='data')
        output = Path(tmp) / 'output'
        measure(root, output)
        actual = hashlib.sha256((output / 'observations.jsonl').read_bytes()).hexdigest()
        if actual != expected['sha256']:
            raise SystemExit(f"observations.jsonl: SHA-256 mismatch: {actual} != {expected['sha256']}")
        print(f'observations.jsonl: SHA-256 MATCH {actual}')


if __name__ == '__main__':
    main()
