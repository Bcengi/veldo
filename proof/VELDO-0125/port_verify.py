"""Run scoped suites with optional CPU contention; events coordinate load lifetime."""
import argparse
import hashlib
import json
import multiprocessing as mp
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def sanitize(text):
    text = text.replace(str(ROOT), '<checkout>')
    return re.sub(r'/(?:home|Users)/[^\s\'"`<>),;]+', '<operator-path>', text)


def load(ready, stop):
    ready.send(True)
    ready.close()
    value = b'load'
    while not stop.is_set():
        value = hashlib.sha256(value).digest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('suites', nargs='+')
    parser.add_argument('--load', type=int, default=0)
    parser.add_argument('--compact', action='store_true')
    parser.add_argument('--raw-dir', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    stop, workers = mp.Event(), []
    results = []
    try:
        for _ in range(args.load):
            reader, writer = mp.Pipe(duplex=False)
            worker = mp.Process(target=load, args=(writer, stop))
            worker.start()
            workers.append(worker)
            writer.close()
            assert reader.poll(120), 'load readiness hang detector'
            assert reader.recv()
            reader.close()
        for suite in args.suites:
            command = [sys.executable, 'scripts/selftest.py', '--suite', suite]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=1800)
            raw = result.stdout + result.stderr
            if args.raw_dir:
                args.raw_dir.mkdir(parents=True, exist_ok=True)
                (args.raw_dir / (suite + '.txt')).write_text(raw)
            lines = sanitize(raw).splitlines()
            summary = next((line for line in reversed(lines) if 'selftest (' in line), '')
            ok = result.returncode == 2 and bool(re.search(r'\b0 failed\b', summary))
            entry = dict(suite=suite, exit_code=result.returncode, passed=ok, summary=summary,
                         output_sha256=hashlib.sha256(raw.encode()).hexdigest(), load_workers=args.load)
            retained = lines if not args.compact else [line for line in lines if any(
                word in line for word in ('FAIL', 'Error', 'Traceback', 'selftest (', 'Permission denied'))]
            (args.output / (suite + '.txt')).write_text('command: python3 scripts/selftest.py --suite ' + suite +
                '\nexit_code: ' + str(result.returncode) + '\n' + '\n'.join(retained) + '\n')
            results.append(entry)
            (args.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
            print(suite, 'PASS' if ok else 'FAIL', summary, flush=True)
    finally:
        stop.set()
        for worker in workers:
            worker.join(timeout=120)
            if worker.is_alive():
                worker.kill()
                worker.join()
    return 0 if results and all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
