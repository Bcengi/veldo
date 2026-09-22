"""Snapshot all tracked YAML and Markdown through both actual reader copies.

The inventory deliberately includes non-consumer Markdown (absent metadata),
engine templates and other YAML as a conservative superset of runtime callers.
Original input bytes and readers are loaded from Git; parsed trees are deduplicated.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import types
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COPIES = ('.veldo/yamlish.py', 'engine/.veldo/yamlish.py')


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def load(path, raw=None):
    mod = types.ModuleType('audit_reader')
    exec(compile((ROOT / path).read_bytes() if raw is None else raw, path, 'exec'), mod.__dict__)
    return mod


def read(mod, path, source):
    try:
        value = (mod.front_matter(source, path) if path.endswith('.md') else mod.parse(source, path))
        return {'state': 'value', 'value': value}
    except ValueError as exc:
        return {'state': 'refused', 'error': str(exc)}


def baseline():
    expected = json.loads((ROOT / 'proof/VELDO-0119/digests.json').read_text())['corpus-before.json']
    commit = expected['source_commit']

    def blob(path):
        return subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)

    readers = {p: blob(p) for p in COPIES}
    modules = {p: load(p, raw) for p, raw in readers.items()}
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', '-z', commit], cwd=ROOT).decode().split('\0')
    paths = [p for p in names if p.endswith(('.md', '.yaml', '.yml'))]
    result = {'base': commit[:7],
              'reader_digests': {p: hashlib.sha256(raw).hexdigest() for p, raw in readers.items()},
              'documents': {}, 'objects': {}}
    for p in paths:
        raw = blob(p)
        source = raw.decode('utf-8-sig')
        values = {name: read(mod, p, source) for name, mod in modules.items()}
        # Prose after a complete fence is never read; retain only parser input.
        if p.endswith('.md'):
            try:
                match = next(iter(modules.values())).front_matter_match(source)
                source = source[:match.end()] if match else ''
            except ValueError:
                pass  # Retain malformed input in full.
        payload = {'source': source, 'answers': values}
        digest = hashlib.sha256(encode(payload)).hexdigest()
        result['objects'][digest] = payload
        result['documents'][p] = {'sha256': hashlib.sha256(raw).hexdigest(), 'object': digest}
    return result


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--baseline', action='store_true')
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', action='store_true',
                      help='regenerate the pinned baseline in /tmp and check the committed SHA-256')
    args = cli.parse_args()
    if args.output and args.output.resolve().is_relative_to(ROOT):
        cli.error('--output must be outside the repository')
    frozen = baseline()
    expected = json.loads((ROOT / 'proof/VELDO-0119/digests.json').read_text())['corpus-before.json']
    with tempfile.TemporaryDirectory(prefix='veldo-0119-corpus-', dir='/tmp') as tmp:
        regenerated = Path(tmp) / 'corpus-before.json'
        regenerated.write_bytes(encode(frozen))
        actual = hashlib.sha256(regenerated.read_bytes()).hexdigest()
        if actual != expected['sha256']:
            raise SystemExit(f"corpus-before.json: SHA-256 mismatch: {actual} != {expected['sha256']}")
        print(f'corpus-before.json: SHA-256 MATCH {actual}')
        if args.verify:
            return
        if args.baseline:
            args.output.write_bytes(regenerated.read_bytes())
            print(json.dumps({'documents': len(frozen['documents']), 'bytes': args.output.stat().st_size}))
            return
    modules = {p: load(p) for p in COPIES}
    changes = []
    for p, entry in frozen['documents'].items():
        before = frozen['objects'][entry['object']]
        for name, mod in modules.items():
            after = read(mod, p, before['source'])
            if encode(before['answers'][name]) != encode(after):
                changes.append({'path': p, 'reader': name, 'source': before['source'],
                                'before': before['answers'][name], 'after': after})
    result = {'baseline': frozen['base'], 'documents': len(frozen['documents']),
              'reader_digests': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in COPIES},
              'policy_unchanged': not any(c['path'] == '.veldo/policy.yaml' for c in changes), 'changes': changes}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: len(v) if k == 'changes' else v for k, v in result.items()}))
    if not result['policy_unchanged']:
        raise SystemExit('STOP: owner policy meaning changed; do not commit reader fix')


if __name__ == '__main__':
    main()
