"""Foreground suite 63 proof driver; owns and reaps exact child PIDs.

Usage: python3 proof/VELDO-0040/runtime_cap_check.py MODE LABEL [ROUNDS]
Modes: original-load, normal, gate, load, mutation.
Loaded rounds run one selected suite at a time plus a pinned burner on every CPU.
Original production and suite come from f1e1abb9; only row diagnostics are added.
"""
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
            patch = ROOT / 'proof/VELDO-0040/original-row-diagnostics.diff'
            subprocess.run(['git', 'apply', str(patch)], cwd=cwd, capture_output=True, check=True)
            report['diagnostic_patch'] = patch.name
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
        report['suite_copies_per_round'] = 1

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
                row['deterministic'] = {k: data['observed'].get(k) for k in (
                    'manager_cap_after_adapter_exit', 'conclude_settles', 'conclude_reset_budget', 'conclude_unknown')}
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
            for round_number in range(1, rounds + 1):
                row = run_one(round_number, 1)
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
