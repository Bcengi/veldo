#!/usr/bin/env python3
"""Repository-only mutation gate. Every registered case executes fresh on every invocation.

Workers see a frozen copy of scripts, .veldo and the proof corpus, never gate receipts.
The source tree is read twice to reject races. Git history is cloned at the measured HEAD.
All children inherit a fixed environment, no user Python site, and disabled bytecode.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DRIVERS = ('check_teeth_mutations.py', 'check_review_mutations.py')
SCHEMA = 'veldo.mutation-result/v1'
FIXTURE_VERSION = 1
BUDGET = 120
WORKER_BUDGET = 120
PARALLEL = 8
OUTPUTS = {'.veldo/last_verify', '.veldo/events.jsonl'}


class Refused(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(f'{code}: {detail}')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inventory(root):
    result = []
    for driver in DRIVERS:
        path = root / 'scripts' / driver
        if not path.is_file():
            raise Refused('incomplete_inventory', driver)
        definitions = load(path).cases()
        if not definitions:
            raise Refused('incomplete_inventory', driver + ': empty registry')
        for case in definitions:
            case = dict(case, driver=driver, identity=driver + ':' + case['name'])
            if not case['rows'] or case['old'] == case['new']:
                raise Refused('incomplete_inventory', case['identity'])
            result.append(case)
    if len({c['identity'] for c in result}) != len(result):
        raise Refused('incomplete_inventory', 'duplicate case')
    return result


def fixed_env(home, binpath='/usr/bin:/bin'):
    return {'PATH': binpath, 'HOME': str(home), 'TMPDIR': str(home),
            'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
            'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            'PYTHONHASHSEED': '0', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}


def command(args, env):
    """Even setup subprocesses belong to an owned, bounded process group."""
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=WORKER_BUDGET)
        if proc.returncode:
            raise subprocess.CalledProcessError(proc.returncode, args, out, err)
        return out
    except subprocess.TimeoutExpired as error:
        raise Refused('mutation_budget_exceeded', 'setup subprocess') from error
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)


# Git's shared environment boundary runs inside our owned group. The outer process
# keeps setup descendants killable even if the shared subprocess.run call hangs.
GIT_BRIDGE = """import importlib.util, subprocess, sys
spec = importlib.util.spec_from_file_location('git_process', sys.argv[1])
_git_process = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_git_process)
result = _git_process.run(['git', *sys.argv[2:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
sys.exit(result.returncode)
"""


def git(root, *args):
    return command([sys.executable, '-B', '-s', '-c', GIT_BRIDGE,
                    str(ROOT / '.veldo/git_process.py'), '-C', str(root), *args],
                   fixed_env('/nonexistent')).decode().strip()


def read_inputs(root):
    """Coarse input closure, including scripts/fixtures and untracked additions/deletions."""
    files = {}
    for directory in ('.veldo', 'scripts', 'proof'):
        for path in sorted((root / directory).rglob('*')):
            rel = path.relative_to(root).as_posix()
            if rel in OUTPUTS or '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                raise Refused('driver_error', 'symlink input: ' + rel)
            if path.is_file():
                files[rel] = (path.stat().st_mode & 0o777, path.read_bytes())
    return files


def file_identity(files):
    return {name: [mode, hashlib.sha256(body).hexdigest()]
            for name, (mode, body) in files.items()}


def observations(value):
    rows = value['observations']
    if not rows or any(not isinstance(r, list) or len(r) != 2 or
                       not isinstance(r[0], str) or type(r[1]) is not bool for r in rows):
        raise ValueError('invalid observations')
    if value['count'] != len(rows) or value['row_names'] != [n for n, _ in rows]:
        raise ValueError('inconsistent row inventory')
    if value['failed_rows'] != [n for n, ok in rows if not ok]:
        raise ValueError('inconsistent false rows')
    return rows


def validate_result(record, case):
    try:
        if (record['schema'] != SCHEMA or record['case'] != case
                or record['fixture_version'] != FIXTURE_VERSION):
            raise ValueError('identity mismatch')
        honest, noop, broken = (observations(record[k]) for k in ('baseline', 'noop', 'mutant'))
        if not all(ok for _, ok in honest) or noop != honest:
            raise Refused('invalid_baseline', case['identity'])
        if not (collections.Counter(n for n, _ in honest) <=
                collections.Counter(n for n, _ in broken)):
            raise Refused('missing_target', case['identity'] + ': baseline rows removed')
        for label in case['rows']:
            before = [ok for name, ok in honest if name.split()[-1] == label]
            after = [ok for name, ok in broken if name.split()[-1] == label]
            if before != [True] or len(after) != 1:
                raise Refused('missing_target', label)
            if after != [False]:
                raise Refused('mutation_survived', label)
        if record['replacement_count'] != 1 or record['old_digest'] == record['new_digest']:
            raise ValueError('invalid mutation diff')
        return record
    except (KeyError, TypeError, ValueError) as error:
        raise Refused('driver_error', str(error)) from error


class Workers:
    def __init__(self, deadline):
        self.deadline = deadline
        self.active = {}
        self.invocations = 0
        self.driver_spans = {}

    def check(self):
        if time.monotonic() >= self.deadline:
            raise Refused('mutation_budget_exceeded', 'combined deadline')

    def check_worker(self, name, started):
        if time.monotonic() - started >= WORKER_BUDGET:
            raise Refused('mutation_budget_exceeded', name + ': worker deadline')

    def cleanup(self):
        for proc, _, _, _ in self.active.values():
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for proc, out, err, _ in self.active.values():
            proc.wait(timeout=5)
            out.close()
            err.close()
        self.active.clear()

    def run(self, jobs, directory, root):
        pending = list(jobs.items())
        results = {}
        try:
            while pending or self.active:
                self.check()
                while pending and len(self.active) < PARALLEL:
                    name, job = pending.pop(0)
                    home = directory / str(self.invocations)
                    home.mkdir()
                    bindir = home / 'bin'
                    bindir.mkdir()
                    (bindir / 'python3').symlink_to(sys.executable)
                    jobpath = home / 'job.json'
                    jobpath.write_bytes(canonical(job))
                    out, err = (open(home / f, 'w+b') for f in ('stdout', 'stderr'))
                    proc = subprocess.Popen([sys.executable, '-B', '-s',
                                             str(root / 'scripts/check_gate_mutations.py'),
                                             '--worker', str(jobpath)], cwd=root,
                                            env=fixed_env(home, str(bindir) + ':/usr/bin:/bin'),
                                            stdout=out, stderr=err, start_new_session=True)
                    self.active[name] = (proc, out, err, time.monotonic())
                    self.invocations += 1
                    self.driver_spans.setdefault(job['case']['driver'], [time.monotonic(), time.monotonic()])
                for name, (proc, out, err, started) in list(self.active.items()):
                    self.check_worker(name, started)
                    if proc.poll() is None:
                        continue
                    # A completed parent cannot leave grandchildren holding resources.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    out.seek(0)
                    err.seek(0)
                    stdout, stderr = out.read(), err.read()
                    out.close()
                    err.close()
                    del self.active[name]
                    self.driver_spans[jobs[name]['case']['driver']][1] = time.monotonic()
                    if proc.returncode != 0:
                        raise Refused('driver_error', name + ': ' + stderr.decode(errors='replace')[-2000:])
                    try:
                        results[name] = {'result': json.loads(stdout), 'elapsed': time.monotonic() - started}
                    except ValueError as error:
                        raise Refused('driver_error', name + ': invalid worker JSON') from error
                if self.active:
                    time.sleep(0.02)
            self.check()
            return results
        finally:
            self.cleanup()


def worker(job):
    case = job['case']
    driver = load(ROOT / 'scripts' / case['driver'])
    owner = load(ROOT / 'scripts/check_teeth_mutations.py')
    prepared = owner.materialize(case, job['mode'], Path(os.environ['TMPDIR']), root=ROOT)
    mutant = prepared['mutant']
    argument = case if case['driver'] == DRIVERS[0] else case['name']
    return dict(observation=driver.worker(argument, str(mutant) if mutant else None),
                **{key: prepared[key] for key in ('replacement_count', 'old_digest', 'new_digest')})


def control_group(case):
    return (case['suite'] + ':' + case['module'] + ':' + str(case.get('fixture') is True))


def snapshot(root, destination, files, head):
    git(root, 'clone', '-q', '--no-checkout', '--no-hardlinks', str(root), str(destination))
    git(destination, 'checkout', '-q', '--detach', head)
    # Git exists only for corpus/history queries; excluded outputs cannot be read by workers.
    for child in destination.iterdir():
        if child.name == '.git':
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    for rel, (mode, body) in files.items():
        path = destination / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        path.chmod(mode)


def run_stage(root=ROOT):
    started = time.monotonic()
    deadline = started + BUDGET
    workers = Workers(deadline)
    receipt = {'schema': 'veldo.mutation-stage/v1', 'results': [],
               'registered': 0, 'executed': 0,
               'rejected': 0, 'drivers': {}, 'surviving_workers': 0, 'invalid_results': []}
    previous = signal.getsignal(signal.SIGALRM)

    def timeout(signum, frame):
        raise Refused('mutation_budget_exceeded', 'combined deadline')

    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, BUDGET)
    try:
        cases = inventory(root)
        receipt['registered'] = len(cases)
        for driver in DRIVERS:
            own = [c for c in cases if c['driver'] == driver]
            receipt['drivers'][driver] = {'inventory_digest': digest(own), 'registered': len(own),
                                           'worker_seconds': 0.0}
        files = read_inputs(root)
        head = git(root, 'rev-parse', 'HEAD')
        receipt['input_digest'] = digest({'files': file_identity(files), 'head': head})
        receipt['implementation_digest'] = hashlib.sha256(
            files['scripts/check_gate_mutations.py'][1]).hexdigest()
        results = {}
        with tempfile.TemporaryDirectory(prefix='veldo-mutations-') as temporary:
            directory = Path(temporary)
            frozen = directory / 'input'
            snapshot(root, frozen, files, head)
            # Registries executed again from the frozen bytes: an enumeration race is red.
            if inventory(frozen) != cases:
                raise Refused('incomplete_inventory', 'registry changed while snapshotting')
            controls = {}
            for case in cases:
                group = control_group(case)
                for mode in ('baseline', 'noop'):
                    controls.setdefault(group + ':' + mode, {'case': case, 'mode': mode})
            control_results = workers.run(controls, directory, frozen)
            mutant_results = workers.run({c['identity']: {'case': c, 'mode': 'mutant'}
                                          for c in cases}, directory, frozen)
            for case in cases:
                identity = case['identity']
                group = control_group(case)
                prepared = mutant_results[identity]['result']
                record = {'schema': SCHEMA, 'case': case,
                          'fixture_version': FIXTURE_VERSION,
                          **{key: prepared[key] for key in ('replacement_count', 'old_digest', 'new_digest')},
                          'baseline': control_results[group + ':baseline']['result']['observation'],
                          'noop': control_results[group + ':noop']['result']['observation'],
                          'mutant': prepared['observation'],
                          'elapsed': mutant_results[identity]['elapsed']}
                try:
                    validate_result(record, case)
                except Refused as error:
                    receipt['invalid_results'].append(dict(record, error=error.code, detail=error.detail))
                    continue
                results[identity] = record
            if receipt['invalid_results']:
                first = receipt['invalid_results'][0]
                raise Refused(first['error'], first['detail'])
            # Reject changes to the checked inputs during execution.
            if (file_identity(read_inputs(root)) != file_identity(files)
                    or git(root, 'rev-parse', 'HEAD') != head):
                raise Refused('driver_error', 'inputs changed during stage')
            workers.check()
            if set(results) != {c['identity'] for c in cases}:
                raise Refused('incomplete_inventory', 'registered/result identities differ')
            for case in cases:
                identity = case['identity']
                record = results[identity]
                validate_result(record, case)
                receipt['executed'] += 1
                receipt['rejected'] += 1
                receipt['drivers'][case['driver']]['worker_seconds'] += record['elapsed']
                receipt['results'].append(record)
        workers.check()
        receipt['status'] = 'passed'
    except Exception as error:  # All incomplete drives are named errors, never detections.
        receipt['status'] = 'failed'
        receipt['error'] = getattr(error, 'code', 'driver_error')
        receipt['detail'] = str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        workers.cleanup()
        signal.signal(signal.SIGALRM, previous)
        for driver, summary in receipt['drivers'].items():
            span = workers.driver_spans.get(driver, (0, 0))
            summary['wall_seconds'] = span[1] - span[0]
        receipt['worker_invocations'] = workers.invocations
        receipt['elapsed'] = time.monotonic() - started
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(json.loads(args.worker.read_text()))))
        return 0
    receipt = run_stage()
    print(json.dumps(receipt, sort_keys=True), flush=True)
    print('mutations: {status} registered={registered} executed={executed} '
          'rejected={rejected} workers={worker_invocations} elapsed={elapsed:.3f}s'.format(**receipt), flush=True)
    return 0 if receipt['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
