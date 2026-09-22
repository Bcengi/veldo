#!/usr/bin/env python3
"""Regenerate coverage counts, raw observations and follow-up disagreements."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/fixtures'))
import grammar_cases as grammar
import yaml_oracle as oracle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location('coverage_reader', ROOT / '.veldo/yamlish.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    started = time.monotonic()
    with (args.output_dir / 'inputs.jsonl').open('w') as output:
        report = grammar.coverage_inventory(output=output)
    report['oracle_version'] = (cap := oracle.capability()).get('version')
    report['oracle_state'] = cap['state']
    report.update(compared=0, disagreements=0, accepted_invalid_yaml=0, oracle_errors=0)
    digest = hashlib.sha256()
    with (args.output_dir / 'observations.jsonl').open('w') as output, (args.output_dir / 'coverage-disagreements.jsonl').open('w') as findings:
        for case in grammar.coverage_cases():
            raw = oracle.observe(case['text'], cap)
            record = dict(identity=case['id'], raw=raw, answer=oracle.answer(raw))
            line = grammar.encoded(record) + '\n'
            output.write(line)
            digest.update(line.encode())
            report['oracle_errors'] += raw['state'] == 'oracle_error'
            if raw['state'] != 'observed':
                continue
            report['compared'] += 1
            report['accepted_invalid_yaml'] += not case['edit'] and raw['syntax'] == 'invalid_yaml'
            expected = {'state': 'refused'} if case['edit'] else oracle.answer(raw)
            try:
                actual = {'state': 'value', 'value': reader.parse(case['text'])}
            except ValueError as error:
                actual = {'state': 'refused', 'error': str(error)}
            if actual['state'] != expected['state'] or (actual['state'] == 'value' and grammar.encoded(actual['value']) != grammar.encoded(expected.get('value'))):
                report['disagreements'] += 1
                findings.write(grammar.encoded(dict(derivation=case['id'], production=case['production'],
                    source=case['text'], input_bytes_hex=case['text'].encode().hex(), edit=case['edit'],
                    reader=actual, oracle=raw, dialect_answer=expected)) + '\n')
    report.update(total_seconds=time.monotonic() - started, observation_digest=digest.hexdigest(),
                  unobserved=sum(report['inputs'].values()) - report['compared'])
    report['fixture_sha256'] = hashlib.sha256(b''.join((ROOT / 'scripts/fixtures' / p).read_bytes()
        for p in ('yamlish_grammar.json', 'grammar_cases.py', 'yaml_oracle.py'))).hexdigest()
    report['reader_sha256'] = hashlib.sha256((ROOT / '.veldo/yamlish.py').read_bytes()).hexdigest()
    report['gate_invocations_green_path'] = 2
    report['measured_added_work_seconds'] = 2 * report['total_seconds']
    (args.output_dir / 'coverage-measurement.json').write_text(json.dumps(report, indent=2) + '\n')
    targets = {k: sorted(v) for k, v in grammar.coverage_targets().items()}
    (args.output_dir / 'coverage-targets.json').write_text(json.dumps(targets, separators=(',', ':')) + '\n')
    print(json.dumps(report, sort_keys=True))
    if report['measured_added_work_seconds'] > 60:
        raise SystemExit('cost stop: measured coverage work exceeds 60 seconds')


if __name__ == '__main__':
    main()
