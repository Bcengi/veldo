#!/usr/bin/env python3
"""Reproduce all control-domain observations and retain every disagreement.

This is a diagnostic, not baseline qualification or evidence of full agreement.
Only the consumer loads the production reader; the oracle never does.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    fixture = ROOT / 'scripts/fixtures'
    grammar = load('control_grammar', fixture / 'grammar_cases.py')
    oracle = load('control_oracle', fixture / 'yaml_oracle.py')
    reader = load('control_reader', ROOT / '.veldo/yamlish.py')
    data, cap = grammar.control_domain(), oracle.capability()
    summary = {'domain': 'mutation-control', 'expected': grammar.expected(data),
               'generated': 0, 'boundary_edits': 0, 'compared': 0, 'disagreements': 0,
               'valid_yaml': 0, 'invalid_yaml': 0, 'oracle_state': cap['state'],
               'oracle_version': cap.get('version'), 'reader_sha256': hashlib.sha256(
                   (ROOT / '.veldo/yamlish.py').read_bytes()).hexdigest(),
               'fixture_sha256': hashlib.sha256(b''.join((fixture / p).read_bytes() for p in
                   ('yamlish_grammar.json', 'grammar_cases.py', 'yaml_oracle.py'))).hexdigest()}
    observations, inputs = hashlib.sha256(), hashlib.sha256()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'control-disagreements.jsonl').open('w') as findings:
        for case in grammar.cases(data):
            summary['generated'] += 1
            neighbors = [(None, case['text'])] + [
                (rule, grammar.edit(case, rule)) for rule in grammar.applicable(case['mask'], data)]
            for rule, text in neighbors:
                summary['boundary_edits'] += rule is not None
                inputs.update((grammar.encoded([case['id'], rule, text]) + '\n').encode())
                raw = oracle.observe(text, cap)
                observations.update((grammar.encoded([case['id'], rule, raw]) + '\n').encode())
                if raw['state'] != 'observed':
                    continue
                summary['compared'] += 1
                summary[raw['syntax']] += 1
                expected = {'state': 'refused'} if rule else oracle.answer(raw)
                try:
                    actual = {'state': 'value', 'value': reader.parse(text)}
                except ValueError as error:
                    actual = {'state': 'refused', 'error': str(error)}
                if (actual['state'] != expected['state'] or
                        actual['state'] == 'value' and actual['value'] != expected.get('value')):
                    summary['disagreements'] += 1
                    finding = {'derivation': case['id'], 'production': case['production'],
                               'edit': rule, 'source': text, 'input_bytes_hex': text.encode().hex(),
                               'reader': actual, 'oracle': raw, 'dialect_answer': expected}
                    findings.write(grammar.encoded(finding) + '\n')
    summary.update(input_digest=inputs.hexdigest(), observation_digest=observations.hexdigest())
    summary['unobserved'] = summary['generated'] + summary['boundary_edits'] - summary['compared']
    (args.output_dir / 'control-comparison.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
