"""Allowlist scrub of the two recorded engine streams and only the two named tap answers.

Reads the source only when explicitly invoked with its directory. No source values are logged.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def policy():
    return json.loads((HERE / 'allowlist.json').read_text())


def scrub(value, path=(), rules=None):
    rules = policy() if rules is None else rules
    field = path[-1] if path else ''
    if isinstance(value, dict):
        return {key: scrub(item, path + (key,), rules) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item, path + ('[]',), rules) for item in value]
    if isinstance(value, str):
        return value if value in rules['strings'].get(field, []) else '<string>'
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, (int, float)):
        return value if field in rules['token_counts'] else (0.0 if isinstance(value, float) else 0)
    raise ValueError('unsupported value type')


def selected(source):
    streams = {}
    for engine in ('claude', 'codex'):
        rows = [json.loads(line) for line in (source / ('real-' + engine) / 'capture/stream.jsonl').read_text().splitlines()]
        streams[engine] = [json.loads(row['line']) for row in rows]
    taps = {}
    for engine, kind in (('claude', 'guard.answer'), ('codex', 'codex.login_status')):
        rows = [json.loads(line) for line in (source / ('real-' + engine) / 'capture/tap.jsonl').read_text().splitlines()]
        matches = [row for row in rows if row.get('kind') == kind]
        if len(matches) != 1:
            raise ValueError('expected exactly one selected tap answer')
        row = matches[0]
        if engine == 'claude':
            taps['claude_initialize'] = {'type': 'control_response', 'response': row['answer']}
        else:
            # Preserve the actual text's type while recording its stream separately. No argv or tap envelope.
            taps['codex_login_status'] = {name: {'present': bool(row[name]), 'text': row[name]}
                                          for name in ('stdout', 'stderr')}
    return {'streams': streams, 'taps': taps}


def digest(path):
    return 'sha256:' + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    raw = selected(args.source)
    result = scrub(raw)
    (HERE / 'capture.json').write_text(json.dumps(result, indent=1, sort_keys=True) + '\n')
    print('wrote scrubbed streams and two selected tap answers')


if __name__ == '__main__':
    main()
