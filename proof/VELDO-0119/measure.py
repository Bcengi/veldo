"""Regenerate complete observations outside the checkout; retain compact proof only."""
import argparse
import collections
import contextlib
import hashlib
import io
import lzma
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--output-dir', type=Path, required=True)
    args = cli.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    ns = {'ROOT': ROOT, 'json': json, 'expect': lambda name, ok: rows.append([name.split(':')[0], bool(ok)])}
    suite = ROOT / 'scripts/suites/55_veldo_0119_agreement.py'
    started = time.monotonic()
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(suite.read_bytes(), str(suite), 'exec'), ns)
    elapsed = time.monotonic() - started
    result, consumer = ns['_r_result'], ns['_r_consumer']
    body = ''.join(consumer.encoded(r) + '\n' for r in result['records']).encode()
    (args.output_dir / 'observations.jsonl').write_bytes(body)
    (args.output_dir / 'observations.jsonl.xz').write_bytes(lzma.compress(body))
    inventory = ns['_r_inventory']
    targets = ns['_r_cases'].coverage_targets()
    (args.output_dir / 'targets.json').write_text(json.dumps({k: sorted(v) for k, v in targets.items()}, indent=2)+'\n')
    historical = []
    for kind in ('control', 'coverage'):
        for line, source in enumerate((ROOT / ('proof/VELDO-0118/' + kind + '-disagreements.jsonl')).read_text().splitlines(), 1):
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
    assert json.loads((ROOT / target_ref).read_text()) == json.loads(json.dumps({k: sorted(v) for k, v in targets.items()}))
    report = consumer.summary(result)
    report['target_inventory_ref'] = target_ref
    report['target_inventory_sha256'] = hashlib.sha256((ROOT / target_ref).read_bytes()).hexdigest()
    report.update(rows=rows, elapsed_seconds=elapsed, normal_gate_invocations=2,
                  normal_gate_added_seconds=2*elapsed, raw_observations_sha256=hashlib.sha256(body).hexdigest(),
                  raw_observations_bytes=len(body), historical_records=218, historical_failures=historical,
                  controls=ns['_r_controls'])
    # Commit representative raw tags and DEL supplementary observations as well.
    samples = [r for r in result['records'] if r['source'] in ('a: true\n','a: 01\n','a: null\n','a: \x7f\n')]
    (args.output_dir / 'dialect-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    (args.output_dir / 'measurement.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'rows':rows, 'seconds':elapsed, 'normal_gate_added_seconds':2*elapsed,
                      'historical_failures':len(historical)}))
    if not all(ok for _, ok in rows) or historical:
        raise SystemExit(1)
    if 2*elapsed > 60:
        raise SystemExit('COST STOP: new suite alone exceeds 60 gate seconds')


if __name__ == '__main__':
    main()
