"""Foreground suite 63 proof driver; owns and reaps exact child PIDs.

Usage: python3 proof/VELDO-0040/runtime_cap_check.py MODE LABEL [ROUNDS]
Modes: original-load, normal, gate, load, mutation.
Loaded rounds run two suite copies concurrently plus a pinned burner on every CPU.
Original production and suite come from f1e1abb9; only row diagnostics are added.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path.cwd()
SUITE = 'scripts/suites/63_veldo_0040_containment.py'
COMMAND = ['python3', 'scripts/selftest.py', '--suite', '63_veldo_0040_containment']


def original_diagnostics(original, current):
    """Retain the original predicates and wall-clock origin, adding named observations."""
    start = current.index("                wall_beats = times(capped")
    end = current.index('\n\n            # AC3:', start)
    detail = current[start:end]
    detail = detail.replace("wall_beats = times(capped, 'stubborn', 'beat')", 'wall_beats = beats')
    detail = detail.replace('gap = beats[-1] - active if beats and active else None',
                            'gap = beats[-1] - running_at if beats and running_at is not None else None')
    detail = detail.replace("                    'timestamps_ordered': 0 < active <= stopping <= inactive,\n"
                            "                    'first_beat_after_active': bool(beats) and active <= beats[0],\n"
                            "                    'last_beat_before_inactive': bool(beats) and beats[-1] <= inactive,\n",
                            "                    'running_at_present': running_at is not None,\n")
    detail = detail.replace("'beats_monotonic': beats, 'beats': wall_beats,", "'beats': wall_beats,")
    detail = detail.replace("                    'active': active, 'stopping': stopping, 'inactive': inactive,\n", '')
    detail = detail.replace("                    'last_beat_after_active': gap,\n", '')
    start = original.index("                observed['runtime_cap'] =")
    end = original.index('\n\n            # AC3:', start)
    original = original[:start] + detail + original[end:]
    old = "def check(label, condition):\n            emitted.add(label)\n            expect('VELDO-0040 ' + label, bool(condition))"
    new = "def check(label, condition, detail=None):\n            emitted.add(label)\n            suffix = ': ' + json.dumps(detail, sort_keys=True) if not condition and detail else ''\n            expect('VELDO-0040 ' + label + suffix, bool(condition))"
    assert old in original
    return original.replace(old, new)


def copy_tree(destination):
    (destination / '.veldo').mkdir(parents=True)
    for source in (ROOT / '.veldo').glob('*.py'):
        shutil.copyfile(source, destination / '.veldo' / source.name)
    shutil.copytree(ROOT / 'scripts', destination / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))


def main():
    mode, label = sys.argv[1:3]
    if mode not in ('original-load', 'normal', 'gate', 'load', 'mutation'):
        raise ValueError('Unknown mode: ' + mode)
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    out = Path('/tmp') / ('flake0040-' + label)
    out.mkdir(exist_ok=False)
    report = {'mode': mode, 'rounds': rounds, 'load': [], 'runs': [], 'output': str(out),
              'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}
    workers = []
    with tempfile.TemporaryDirectory(prefix='flake0040-proof-') as directory:
        temporary = Path(directory)
        observer = temporary / 'observer'
        observer.mkdir()
        (observer / 'sitecustomize.py').write_text('''import atexit, json, os, sys
from pathlib import Path
def capture():
    s = sys.modules.get('shared')
    if s is not None and hasattr(s, '_V40_OBSERVED'):
        Path(os.environ['V40_SNAPSHOT']).write_text(json.dumps({
            'passed': s.PASS, 'failed': s.FAIL, 'observed': s._V40_OBSERVED,
            'seconds': s._V40_SECONDS}, default=str))
atexit.register(capture)
''')
        cwd = ROOT
        if mode == 'original-load':
            cwd = temporary / 'original'
            cwd.mkdir()
            archive = temporary / 'original.tar'
            with archive.open('wb') as stream:
                subprocess.run(['git', 'archive', 'f1e1abb9', '.veldo', 'scripts'], stdout=stream, check=True)
            with tarfile.open(archive) as tar:
                tar.extractall(cwd, filter='data')
            suite = cwd / SUITE
            suite.write_text(original_diagnostics(suite.read_text(), (ROOT / SUITE).read_text()))
            report['original_commit'] = 'f1e1abb9'
        elif mode == 'mutation':
            cwd = temporary / 'mutated'
            copy_tree(cwd)
            target = cwd / '.veldo/control_containment.py'
            source = target.read_text()
            if mode == 'mutation':
                edits = [
                    ("                 ('RuntimeMaxSec', _usec(s['runtime_seconds'])), ('TimeoutStopSec', _usec(s['kill_grace_seconds'])),\n",
                     "                 ('TimeoutStopSec', _usec(s['kill_grace_seconds'])),  # defect: the runtime cap is ignored\n"),
                    ("            'runtime_seconds': {'RuntimeMaxUSec': round(s['runtime_seconds'] * 10 ** 6)},\n", '')]
            for old, new in edits:
                assert source.count(old) == 1, old
                source = source.replace(old, new)
            target.write_text(source)
        report['sha256'] = {name: hashlib.sha256((cwd / name).read_bytes()).hexdigest()
                            for name in [SUITE, '.veldo/control_containment.py', '.veldo/control_launch.py']}
        command = COMMAND if mode != 'gate' else ['bash', '-c', ' '.join(COMMAND)]
        loaded = mode in ('original-load', 'load')
        report['suite_copies_per_round'] = 2 if loaded else 1

        def run_one(round_number, slot):
            prefix = out / ('round-%02d-copy-%d' % (round_number, slot))
            snapshot = prefix.with_suffix('.json')
            env = dict(os.environ, PYTHONPATH=str(observer), V40_SNAPSHOT=str(snapshot), PYTHONDONTWRITEBYTECODE='1')
            with prefix.with_suffix('.log').open('w') as log:
                process = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
                prefix.with_suffix('.pid').write_text(str(process.pid) + '\n')
                try:
                    code = process.wait(timeout=240)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=30)
                    code = 'timeout'
            row = {'round': round_number, 'copy': slot, 'pid': process.pid, 'exit_code': code}
            if snapshot.exists():
                data = json.loads(snapshot.read_text())
                row.update({k: data[k] for k in ('passed', 'failed', 'seconds')})
                row['runtime_cap'] = data['observed'].get('runtime_cap')
                row['raised'] = data['observed'].get('raised')
            row['failed_details'] = [line.strip().split('SELFTEST FAIL: ', 1)[1]
                                     for line in prefix.with_suffix('.log').read_text().splitlines()
                                     if 'SELFTEST FAIL:' in line]
            return row

        try:
            if loaded:
                for cpu in sorted(os.sched_getaffinity(0)):
                    code = 'import os\nos.sched_setaffinity(0, {%d})\nwhile True:\n    pass\n' % cpu
                    worker = subprocess.Popen(['python3', '-S', '-c', code], stdin=subprocess.DEVNULL,
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    workers.append(worker)
                    report['load'].append({'cpu': cpu, 'pid': worker.pid})
                (out / 'load-pids.json').write_text(json.dumps(report['load'], indent=2) + '\n')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                for round_number in range(1, rounds + 1):
                    tasks = [pool.submit(run_one, round_number, slot)
                             for slot in range(1, report['suite_copies_per_round'] + 1)]
                    for task in tasks:
                        row = task.result()
                        report['runs'].append(row)
                        runtime = row.get('runtime_cap') or {}
                        print(json.dumps({'round': row['round'], 'copy': row['copy'], 'failed': row.get('failed'),
                                          'false_conjuncts': runtime.get('false_conjuncts'),
                                          'gap': runtime.get('last_beat_after_running'),
                                          'red_rows': [x.split(': ', 1)[0] for x in row['failed_details']]}), flush=True)
                    (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        finally:
            for worker, entry in zip(workers, report['load']):
                if worker.poll() is None:
                    stat = Path('/proc/%d/stat' % worker.pid).read_text().rsplit(')', 1)[1].split()
                    entry['cpu_ticks'] = int(stat[11]) + int(stat[12])
                    worker.terminate()
            for worker in workers:
                try:
                    worker.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait()
            report['load_reaped'] = all(p.returncode is not None for p in workers)
            (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
