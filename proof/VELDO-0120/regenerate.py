"""Regenerate omitted proof bytes outside the checkout and enforce their digests.

Measurements execute pinned source. Mutation receipts expand a lossless readable
summary: historical timings are preserved, not claimed as a fresh execution.
"""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent


def expand_mutations(summary):
    receipt = copy.deepcopy(summary['receipt'])
    receipt['results'] = []
    for entry in summary['cases']:
        record = copy.deepcopy(entry)
        for mode in ('baseline', 'noop', 'mutant'):
            observation = record[mode]
            if isinstance(observation, str):
                observation = copy.deepcopy(summary['controls'][observation])
            names = summary['row_inventories'][observation.pop('row_inventory')]
            failed = observation['failed_rows']
            if len(names) != len(set(names)) or not set(failed) <= set(names):
                raise ValueError('invalid or ambiguous row inventory')
            observation['row_names'] = list(names)
            observation['observations'] = [[name, name not in failed] for name in names]
            if observation['count'] != len(names):
                raise ValueError('observation count does not match inventory')
            record[mode] = observation
        receipt['results'].append(record)
    return (json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode()


def regenerate(artifact, output, expected):
    output.mkdir(parents=True, exist_ok=True)
    destination = output / artifact
    if artifact == 'measurement.jsonl':
        with tempfile.TemporaryDirectory(prefix='veldo-0120-source-', dir='/tmp') as temporary:
            root = Path(temporary)
            archive = subprocess.check_output([
                'git', 'archive', expected['source_commit'],
                'proof/VELDO-0120/measure.py', 'scripts/fixtures',
                '.veldo', 'engine/.veldo'], cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(archive)) as files:
                files.extractall(root, filter='data')
            subprocess.run([sys.executable, '-B', str(root / 'proof/VELDO-0120/measure.py'),
                            str(output / 'measurement.json'), '--records'], check=True,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    else:
        destination.write_bytes(expand_mutations(json.loads((PROOF / artifact).read_text())))
    return destination


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('artifact', choices=('measurement.jsonl', 'gate-mutations.json'))
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output-dir', type=Path)
    mode.add_argument('--verify', action='store_true')
    cli.add_argument('--expected-sha256', help='override for a wrong-digest negative control')
    args = cli.parse_args()
    expected = json.loads((PROOF / 'digests.json').read_text())[args.artifact]

    def run(output):
        path = regenerate(args.artifact, output, expected)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        wanted = args.expected_sha256 or expected['sha256']
        if actual != wanted:
            raise SystemExit(f'{args.artifact}: SHA-256 mismatch: {actual} != {wanted}')
        if path.stat().st_size != expected['bytes']:
            raise SystemExit(f'{args.artifact}: byte count mismatch')
        print(f'{args.artifact}: SHA-256 MATCH {actual}')

    if args.verify:
        with tempfile.TemporaryDirectory(prefix='veldo-0120-verify-', dir='/tmp') as temporary:
            run(Path(temporary))
    else:
        output = args.output_dir.resolve()
        if output.is_relative_to(ROOT):
            cli.error('--output-dir must be outside the repository')
        # Resolve the generated filenames too, rejecting symlinks into the checkout.
        for name in (args.artifact, 'measurement.json'):
            if (output / name).resolve().is_relative_to(ROOT):
                cli.error('output file must be outside the repository')
        run(output)


if __name__ == '__main__':
    main()
