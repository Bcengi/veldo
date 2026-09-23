"""Measure the policy product before writing suite rows; retain readable observations."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    grammar = load('grammar', ROOT / 'scripts/fixtures/grammar_cases.py')
    oracle = load('oracle', ROOT / 'scripts/fixtures/yaml_oracle.py')
    consumer = load('consumer', ROOT / 'scripts/fixtures/policy_agreement.py')
    readers = {name: load(name, ROOT / prefix / 'fix_validation_record.py')
               for name, prefix in (('repository', '.veldo'), ('engine', 'engine/.veldo'))}
    started = time.monotonic()
    cases = list(consumer.cases(grammar))
    generated = time.monotonic() - started
    expected = consumer.expected_ids(grammar)
    result = consumer.run(cases, expected, readers, oracle, oracle.capability(), retain='--records' in sys.argv)
    counts = grammar.coverage_count()
    summary = consumer.summary(result)
    summary.update(grammar_counts=counts, generation_seconds=generated,
                   full_cross_product=(sum(counts.values()) * 4 * len(consumer.BOOLEAN_WORDS) * len(consumer.COMMITS)),
                   construction='coverage: each witness and boundary at each site, every scalar in both fields, schema partitions',
                   coverage_by_family=dict(__import__('collections').Counter(c['id'][0] for c in cases)))
    summary['implementation_digests'] = {name: hashlib.sha256((ROOT / prefix / 'fix_validation_record.py').read_bytes()).hexdigest()
        for name, prefix in (('repository', '.veldo'), ('engine', 'engine/.veldo'))}
    summary['fixture_version'] = grammar.DATA['revision']
    summary['fixture_digest'] = hashlib.sha256(b''.join((ROOT / 'scripts/fixtures' / p).read_bytes()
        for p in ('grammar_cases.py', 'yaml_oracle.py', 'policy_agreement.py', 'yamlish_grammar.json'))).hexdigest()
    summary['input_digest'] = hashlib.sha256(consumer.encoded([(c['id'], c['text']) for c in cases]).encode()).hexdigest()
    summary['owner_policy'] = dict(sha256=hashlib.sha256((ROOT / '.veldo/policy.yaml').read_bytes()).hexdigest(),
        settings=consumer.schema(readers['repository']._yamlish.read(ROOT / '.veldo/policy.yaml')))
    output = Path(sys.argv[1])
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    if '--records' in sys.argv:
        with output.with_suffix('.jsonl').open('w') as stream:
            for record in result['records']:
                stream.write(json.dumps(record, sort_keys=True) + '\n')
        summary['observations_sha256'] = hashlib.sha256(output.with_suffix('.jsonl').read_bytes()).hexdigest()
        output.write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, sort_keys=True))


if __name__ == '__main__':
    main()
