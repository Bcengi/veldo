"""Snapshot all tracked YAML and Markdown through both actual reader copies.

The inventory deliberately includes non-consumer Markdown (absent metadata),
engine templates and other YAML as a conservative superset of runtime callers.
Frozen input bytes and full parsed trees are deduplicated and lzma compressed.
"""
import argparse
import base64
import lzma
import hashlib
import json
from pathlib import Path
import subprocess
import types

ROOT = Path(__file__).resolve().parents[2]
COPIES = ('.veldo/yamlish.py', 'engine/.veldo/yamlish.py')


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


def load(path):
    mod = types.ModuleType('audit_reader')
    exec(compile((ROOT / path).read_bytes(), path, 'exec'), mod.__dict__)
    return mod


def read(mod, path, source):
    try:
        value = (mod.front_matter(source, path) if path.endswith('.md') else mod.parse(source, path))
        return {'state': 'value', 'value': value}
    except ValueError as exc:
        return {'state': 'refused', 'error': str(exc)}


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--baseline', action='store_true')
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    frozen = ROOT / 'proof/VELDO-0119/corpus-before.json.xz.b64'
    modules = {p: load(p) for p in COPIES}
    if args.baseline:
        names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', '-z', 'b34d17d'], cwd=ROOT).decode().split('\0')
        paths = [p for p in names if p.endswith(('.md', '.yaml', '.yml'))]
        result = {'base': 'b34d17d',
                  'reader_digests': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in COPIES},
                  'documents': {}, 'objects': {}}
        for p in paths:
            raw = (ROOT / p).read_bytes()
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
        args.output.write_bytes(base64.encodebytes(lzma.compress(encode(result))))
        print(json.dumps({'documents': len(paths), 'compressed_bytes': args.output.stat().st_size}))
        return
    baseline = json.loads(lzma.decompress(base64.decodebytes(frozen.read_bytes())))
    changes = []
    for p, entry in baseline['documents'].items():
        before = baseline['objects'][entry['object']]
        for name, mod in modules.items():
            after = read(mod, p, before['source'])
            if encode(before['answers'][name]) != encode(after):
                changes.append({'path': p, 'reader': name, 'source': before['source'],
                                'before': before['answers'][name], 'after': after})
    result = {'baseline': baseline['base'], 'documents': len(baseline['documents']),
              'reader_digests': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in COPIES},
              'policy_unchanged': not any(c['path'] == '.veldo/policy.yaml' for c in changes), 'changes': changes}
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: len(v) if k == 'changes' else v for k, v in result.items()}))
    if not result['policy_unchanged']:
        raise SystemExit('STOP: owner policy meaning changed; do not commit reader fix')


if __name__ == '__main__':
    main()
