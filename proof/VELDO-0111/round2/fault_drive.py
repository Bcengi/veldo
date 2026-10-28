"""Single ticket suite, retained swallowed-fault falsifiers."""
import difflib
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'scripts/fixtures/lifecycle_census.py'
SUITE = ROOT / 'scripts/suites/113_veldo_0111_census.py'
CASES = {
    'corrupt': ('            op = 255', '            op = raw[0]'),
    'abi': ('            arch = 0\n', '            arch = struct.unpack_from("<I", raw, 4)[0]\n'),
    'loss': ('                    if req.get("fault") == "loss":', '                    if False: # swallowed loss'),
}

def main():
    phase = sys.argv[1]
    spec = importlib.util.spec_from_file_location('suite', SUITE)
    suite = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(suite)
    source = SOURCE.read_text()
    report = {'phase': phase, 'source_digest': hashlib.sha256(source.encode()).hexdigest(),
              'suite_digest': hashlib.sha256(SUITE.read_bytes()).hexdigest(), 'cases': {}}
    for fault, (old, new) in CASES.items():
        assert source.count(old) == 1
        mutant = source.replace(old, new)
        (HERE / ('swallow-' + fault + '.diff')).write_text(''.join(difflib.unified_diff(
            source.splitlines(True), mutant.splitlines(True), fromfile=str(SOURCE), tofile='mutant.py')))
        with tempfile.TemporaryDirectory(prefix='v111-fault-') as temporary:
            path = Path(temporary) / 'lifecycle_census.py'
            path.write_text(mutant)
            rows = []
            evidence = suite.run_checks(ROOT, lambda name, ok: rows.append([name, bool(ok)]), path)
        with gzip.open(HERE / (phase + '-swallow-' + fault + '.json.gz'), 'wt') as output:
            json.dump(dict(rows=rows, evidence=evidence), output)
        assert len(rows) == len(set(name for name, _ in rows))
        detected = dict(rows)['census/incomplete-is-not-empty'] is False
        report['cases'][fault] = dict(detected=detected, rows=rows)
        print(phase, fault, 'detected', detected, flush=True)
        assert detected == (phase == 'green')
    if phase == 'green':
        rows = []
        evidence = suite.run_checks(ROOT, lambda name, ok: rows.append([name, bool(ok)]))
        with gzip.open(HERE / 'fault-green-control.json.gz', 'wt') as output:
            json.dump(dict(rows=rows, evidence=evidence), output)
        assert all(ok for _, ok in rows), rows
        report['control'] = rows
    (HERE / ('fault-' + phase + '.json')).write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    main()
