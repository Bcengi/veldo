"""Host-only read-back and exhaustive literal grep; prints counts, never source values."""
import argparse
import json
from pathlib import Path
import subprocess
import scrub


def typed_paths(value, path=()):
    found = [(path, type(value).__name__)]
    if isinstance(value, dict):
        for key, item in value.items():
            found += typed_paths(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found += typed_paths(item, path + (index,))
    return found


def strings(value):
    if isinstance(value, str):
        yield value
        try:
            decoded = json.loads(value)
        except ValueError:
            return
        if not isinstance(decoded, str):
            yield from strings(decoded)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    source = scrub.selected(args.source)
    capture_path = scrub.HERE / 'capture.json'
    capture = json.loads(capture_path.read_text())
    same = set(typed_paths(source)) == set(typed_paths(capture)) and scrub.scrub(source) == capture
    constants = {v for values in scrub.policy()['strings'].values() for v in values}
    constants.update(scrub.policy()['grep_schema_constants'])
    values = set()
    for path in args.source.rglob('*'):
        if not path.is_file() or path.suffix not in ('.json', '.jsonl'):
            continue
        text = path.read_text()
        records = [json.loads(line) for line in text.splitlines()] if path.suffix == '.jsonl' else [json.loads(text)]
        for record in records:
            values.update(v for v in strings(record) if len(v) > 3 and v not in constants)
    # grep's fixed-string input is supplied privately, never as command-line arguments or output.
    # Multi-line values are searched as whole strings in Python to avoid treating their individual lines as values.
    single = sorted(v for v in values if '\n' not in v)
    checked = subprocess.run(['grep', '-F', '-q', '-f', '-', str(capture_path)],
                             input='\n'.join(single) + '\n', text=True, capture_output=True)
    none = checked.returncode == 1 and not any(v in capture_path.read_text() for v in values if '\n' in v)
    report = {'schema': 'veldo.capture-readback/v1', 'spec_id': 'VELDO-0172',
              'capture_sha256': scrub.digest(capture_path), 'typed_paths': len(typed_paths(source)),
              'keys_and_types_equal': same, 'non_allowlisted_strings_checked': len(values),
              'literal_grep_no_matches': none, 'selected_taps': 2}
    print(json.dumps(report, indent=1, sort_keys=True))
    if same and none:
        (scrub.HERE / 'readback.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    return 0 if same and none else 1


if __name__ == '__main__':
    raise SystemExit(main())
