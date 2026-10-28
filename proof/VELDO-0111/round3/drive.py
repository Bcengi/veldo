"""Run this ticket's focused regressions or its full suite, retaining receipts."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'scripts/fixtures/lifecycle_census.py'
SUITE = ROOT / 'scripts/suites/113_veldo_0111_census.py'

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run(label, source=SOURCE, groups=None):
    suite = load('suite111', SUITE)
    rows = []
    emit = lambda name, ok: rows.append([name, bool(ok)])
    if groups is None:
        evidence = suite.run_checks(ROOT, emit, source)
    else:
        evidence = suite.run_round3_checks(load('census111', source), emit, groups)
    report = dict(rows=rows, source_digest=hashlib.sha256(source.read_bytes()).hexdigest(),
                  suite_digest=hashlib.sha256(SUITE.read_bytes()).hexdigest())
    with gzip.open(HERE / (label + '.json.gz'), 'wt') as output:
        json.dump(dict(report, evidence=evidence), output)
    (HERE / (label + '.json')).write_text(json.dumps(report, indent=2) + '\n')
    print(label, rows, flush=True)
    return dict(rows)

if __name__ == '__main__':
    label = sys.argv[1]
    rows = run(label, groups=sys.argv[2:] or None)
    assert bool(rows) and all(rows.values()) == ('red' not in label)
