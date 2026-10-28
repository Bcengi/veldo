"""Run only this ticket's falsifiers, each followed by its restored green check.

Invoke under the owner's flock. Mutations are compiled from scratch source strings;
production files are never mutated. A crashed or incomplete run is an invalid drive.
"""
import difflib
import importlib.util
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / 'scripts/fixtures/relay_exchange.py'
spec = importlib.util.spec_from_file_location('relay_exchange121', path)
fixture_bytes = path.read_bytes()
fixture = importlib.util.module_from_spec(spec)
exec(compile(fixture_bytes, str(path), 'exec'), fixture.__dict__)


def main():
    source = (ROOT / '.veldo/control_relay.py').read_text()
    assert source == (ROOT / 'engine/.veldo/control_relay.py').read_text()
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'proof/VELDO-0121/results'
    output.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    for relative, data in (('.veldo/control_relay.py', source.encode()),
                           ('scripts/fixtures/relay_exchange.py', fixture_bytes)):
        assert subprocess.check_output(['git', 'show', head + ':' + relative], cwd=ROOT) == data, relative
    summary = dict(input_commit=head, fixture_version=fixture.VERSION, results=[])
    for criterion, row in fixture.ROWS.items():
        changed = fixture.mutate(source, criterion)
        (output / (criterion + '.diff')).write_text(''.join(difflib.unified_diff(
            source.splitlines(True), changed.splitlines(True),
            fromfile='a/.veldo/control_relay.py', tofile='b/.veldo/control_relay.py')))
        for color, code in (('red', changed), ('green', source)):
            result = fixture.qualify(code, criterion)
            unchanged = (path.read_bytes() == fixture_bytes
                         and (ROOT / '.veldo/control_relay.py').read_text() == source
                         and (ROOT / 'engine/.veldo/control_relay.py').read_text() == source)
            result['valid'] = result['valid'] and unchanged
            result['inputs_unchanged'] = unchanged
            result['input_commit'] = head
            receipt = criterion + '-' + color + '.json.gz'
            (output / receipt).write_bytes(gzip.compress(json.dumps(result).encode(), mtime=0))
            expected = color == 'green'
            valid = result['valid'] and not result['incomplete'] and row in result['rows']
            observed = result['rows'].get(row)
            witnesses = []
            if color == 'red':
                for index, record in enumerate(result['records']):
                    case = record['case']
                    witnessed = {
                        'AC1': (case.get('phase') == 'recv' and case.get('offset', 0) > 0
                                and case.get('outcome') == 'ECONNRESET'
                                and record['stdout']['length'] > 0 and record['exit'] == 3),
                        'AC2': (case.get('response') == 0 and case.get('request') == 0
                                and record['exit'] == 3),
                        'AC3': (case.get('trickle') and record['exit'] == 0),
                        'AC4': (case.get('phase') == 'recv' and record.get('connection_attempts', 0) > 1
                                and len(record['complete_requests']) > 1),
                    }[criterion]
                    if witnessed:
                        witnesses.append(index)
                valid = valid and bool(witnesses)
            summary['results'].append(dict(criterion=criterion, color=color, valid=valid,
                                           row=row, observed=observed, expected=expected,
                                           receipt=receipt, falsifier_witness_records=witnesses,
                                           first_witness=result['records'][witnesses[0]] if witnesses else None))
            print(criterion, color, 'valid=' + str(valid), 'row=' + str(observed), flush=True)
            if not valid or observed != expected:
                (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
                return 1
    summary['complete'] = True
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
