#!/usr/bin/env python3
"""Regenerate a measured prefix digest; never claim baseline qualification."""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, required=True)
    parser.add_argument('--output', type=Path, help='optional full prefix inventory outside git')
    args = parser.parse_args()
    if args.count < 0:
        parser.error('count must be nonnegative')
    root = Path(__file__).resolve().parents[2]
    path = root / 'scripts/fixtures/grammar_cases.py'
    spec = importlib.util.spec_from_file_location('prefix_grammar', path)
    grammar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(grammar)
    digest = hashlib.sha256()
    generated = edits = 0
    output = args.output.open('w') if args.output else None
    try:
        for case in itertools.islice(grammar.cases(), args.count):
            generated += 1
            entries = [(None, case['text'])] + [(rule, grammar.edit(case, rule))
                       for rule in grammar.applicable(case['mask'], grammar.DATA)]
            for rule, text in entries:
                edits += rule is not None
                record = grammar.encoded([case['id'], case['production'], case['indent'],
                    case['newline'], case['comment'], rule, text]) + '\n'
                digest.update(record.encode())
                if output:
                    output.write(record)
    finally:
        if output:
            output.close()
    print(json.dumps({'domain': 'explicit-baseline-prefix', 'generated': generated,
                      'boundary_edits': edits, 'digest': digest.hexdigest(),
                      'baseline_qualification': 'unproven'}))


if __name__ == '__main__':
    main()
