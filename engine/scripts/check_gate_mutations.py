#!/usr/bin/env python3
"""Repository-only mutation gate. Every registered case has validated, input-bound evidence.

Workers see a frozen copy of the working tree Git does not ignore, never gate receipts.
The source tree is read twice to reject races. Git history is cloned at the measured HEAD.
All children inherit a fixed environment, no user Python site, and disabled bytecode.
"""
import argparse
import collections
import concurrent.futures
import difflib
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
# The combined cap scales with the registered inventory: each case costs roughly 0.8 s on the
# qualification host (116 cases measured at 91.8 s on 2026-09-23), so a fixed cap would turn red for
# growth alone. BUDGET is the floor; budget_for() is the cap actually enforced.
BUDGET = 120
PER_CASE_SECONDS = 2.0        # measured at REFERENCE_WORKERS workers
REFERENCE_WORKERS = 8
WORKER_BUDGET = 120

def _quota_cpus(root='/sys/fs/cgroup', membership='/proc/self/cgroup'):
    """The CPUs a cgroup v2 quota allows this process: the smallest cpu.max quota on the process's
    OWN cgroup or any parent up to the mount (a quota set on a host scope or slice sits there, not
    at the mount root), or None when none applies. cgroup v1 is not read (stated limit)."""
    try:
        with open(membership, errors='surrogateescape') as handle:
            own = next((line.split('::', 1)[1].strip() for line in handle if line.startswith('0::')), None)
    except OSError:
        own = None
    if own is None:
        return None
    top = os.path.normpath(root)
    best, path = None, os.path.normpath(os.path.join(top, own.lstrip('/')))
    if path != top and not path.startswith(top.rstrip(os.sep) + os.sep):
        return None
    while True:
        try:
            with open(os.path.join(path, 'cpu.max')) as handle:
                quota, period = handle.read().split()[:2]
            if quota != 'max' and int(period) > 0:
                cpus = max(1, -(-int(quota) // int(period)))
                best = cpus if best is None else min(best, cpus)
        except (OSError, ValueError):
            pass
        parent = os.path.dirname(path)
        if path == top or parent == path:      # the mount, or the filesystem root: stop
            return best
        path = parent


def worker_count(cpus=None, cgroup_root='/sys/fs/cgroup', membership='/proc/self/cgroup'):
    """Workers the stage runs at once: the CPUs this process may use (its affinity set, bounded by
    a cgroup CPU quota), never fewer than 2 or more than 16. A fixed 8 left most of a 20-core host
    idle while the stage grew with every item, and would oversubscribe a small one. Verdicts do not
    depend on the count; the combined budget scales with it (budget_for)."""
    if cpus is None:
        try:
            cpus = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            cpus = os.cpu_count() or 2
        quota = _quota_cpus(cgroup_root, membership)
        if quota:
            cpus = min(cpus, quota)
    return max(2, min(16, int(cpus)))


PARALLEL = 1 if '--worker' in sys.argv else worker_count()
OUTPUTS = {'.veldo/last_verify', '.veldo/events.jsonl'}


def budget_for(count, workers=REFERENCE_WORKERS):
    """The combined cap for a registered inventory of `count` cases run by `workers` workers at
    once, never below BUDGET. The per-case figure was measured at REFERENCE_WORKERS. Fewer workers
    get proportionally more time; MORE workers get no less than the reference figure, because the
    measured speedup past REFERENCE_WORKERS is well below linear (8 -> 16 was about 1.5x), so the
    extra workers buy margin instead of a tighter cap."""
    return max(BUDGET, PER_CASE_SECONDS * count * REFERENCE_WORKERS / max(1, min(workers, REFERENCE_WORKERS)))


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


def inventory_local(root):
    result = []
    for driver in DRIVERS:
        path = root / 'scripts' / driver
        if not path.is_file():
            raise Refused('incomplete_inventory', driver)
        driver_module = load(path)
        definitions = driver_module.cases()
        if not definitions:
            raise Refused('incomplete_inventory', driver + ': empty registry')
        for case in definitions:
            if hasattr(driver_module, 'reuse_definition'):
                driver_module.reuse_definition(case, definitions)
            case = dict(case, driver=driver, identity=driver + ':' + case['name'])
            if not case['rows'] or case['old'] == case['new']:
                raise Refused('incomplete_inventory', case['identity'])
            result.append(case)
    if len({c['identity'] for c in result}) != len(result):
        raise Refused('incomplete_inventory', 'duplicate case')
    return result


def confined_command(root, command):
    return [sys.executable, '-I', '-S', str(ROOT / 'scripts/gate_candidate.py'),
            '--root', str(root), '--', *command]


def common_directory(root):
    """The Git common directory of a repository the caller itself owns (the authority checkout, or
    a repository the caller just created), resolved from its marker by the guarded helper without
    running Git. Whoever owns a repository names this; nothing defaults it."""
    return load(ROOT / '.veldo/candidate_git.py').common_directory(root)


def inventory(root, expected_common):
    # Registry imports are candidate execution too. Only data crosses this pipe.
    env = dict(os.environ, VELDO_EXPECTED_GIT_COMMON=str(expected_common))
    result = subprocess.run(confined_command(root, [sys.executable, '-I', '-S',
        str(ROOT / 'scripts/reuse_worker.py'), 'inventory', str(root)]),
        capture_output=True, text=True, timeout=WORKER_BUDGET, env=env)
    if result.returncode:
        raise Refused('candidate_execution_denied', result.stderr[-2000:])
    return json.loads(result.stdout)


def fixed_env(home, binpath='/usr/bin:/bin'):
    return {'PATH': binpath, 'HOME': str(home), 'TMPDIR': str(home),
            'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
            'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            'PYTHONHASHSEED': '0', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}


def command(args, env, with_stderr=False):
    """Even setup subprocesses belong to an owned, bounded process group."""
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=WORKER_BUDGET)
        if proc.returncode:
            raise subprocess.CalledProcessError(proc.returncode, args, out, err)
        return (out, err) if with_stderr else out
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
def git_bytes(root, expected_common, *args, with_stderr=False):
    return command([sys.executable, '-I', '-S', str(ROOT / '.veldo/candidate_git.py'),
                    '--root', str(root), '--expected-common', str(expected_common), '--', *args],
                   fixed_env('/nonexistent'), with_stderr=with_stderr)


def git(root, expected_common, *args):
    return git_bytes(root, expected_common, *args).decode().strip()


def read_inputs(root, expected_common):
    """THE INPUT CLOSURE: every file of the working tree Git does not ignore, tracked or untracked,
    minus deleted files, bytecode caches and the gate's own outputs. Ignore rules are what Git applies
    to this repository with no global configuration: .gitignore, info/exclude and a core.excludesFile
    set in the repository's own config (the last two are local to this clone); a user's global ignore
    file does not apply. An ignored file (local configuration such as
    .veldo/trackers.json, caches) is machine-local and is NOT an input: the gate judges the
    repository, not the host. The snapshot the workers run in holds exactly this closure: a hand
    list of directories left out the front door bin/veldo, and a row that runs it passed in the
    checkout and failed in every baseline in the snapshot. Names are read as raw bytes (NUL
    separated, decoded with the file system encoding), so no name is trimmed or undecodable."""
    listed, warned = git_bytes(root, expected_common, 'ls-files', '-z', '--cached', '--others', '--exclude-standard',
                               with_stderr=True)
    if warned.strip():
        # Git lists what it could read and only WARNS about a directory it could not open, so such
        # a warning means files are missing from the listing. Any OTHER output (a deprecation
        # notice, a hint) is refused too, since nobody has shown the listing is whole, but under
        # its own name so the cause is not misread.
        lines = warned.decode(errors='replace').strip().splitlines()
        missing = [line for line in lines if 'could not open directory' in line]
        kind = 'incomplete input listing' if missing else 'unexpected git output while listing inputs'
        raise Refused('driver_error', kind + ': ' + (missing or lines)[0])
    files = {}
    top = os.path.realpath(root)
    for rel in sorted(set(os.fsdecode(name) for name in listed.split(b'\0') if name)):
        path = root / rel
        if rel.endswith('/'):
            # Git lists an untracked nested repository as a directory and never its files.
            raise Refused('driver_error', 'nested repository in the input closure: ' + rel)
        if rel in OUTPUTS or '__pycache__' in Path(rel).parts:
            continue
        try:
            linked = path.is_symlink() or (os.path.lexists(path)
                                           and os.path.realpath(path) != os.path.join(top, rel))
        except OSError as error:
            raise Refused('driver_error', 'unreadable input: ' + rel) from error
        if linked:
            # A link as the file, or as ANY directory above it, would copy a file the checkout
            # only points at.
            raise Refused('driver_error', 'symlink input: ' + rel)
        if path.is_file():
            try:
                files[rel] = (path.stat().st_mode & 0o777, path.read_bytes())
            except OSError as error:
                raise Refused('driver_error', 'unreadable input: ' + rel) from error
    return files


def inputs_unchanged(root, expected_common, files, head):
    """THE RACE CHECK: read the inputs AGAIN and compare with the first read, by content, mode and
    name, and the commit, so a change during the stage can never pass as the tree that was run."""
    return (file_identity(read_inputs(root, expected_common)) == file_identity(files)
            and git(root, expected_common, 'rev-parse', 'HEAD') == head)


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


class SuiteResources:
    """Admission belongs to the coordinator, not a semaphore blocking a worker.

    Positive slot demands share a resource; 'exclusive' reserves its whole configured
    capacity. A waiting exclusive job bars later users of that resource, so it cannot
    starve, while unrelated jobs can pass it and fill every available worker slot.
    Reservations cover the process lifetime, including baseline/noop and teardown.
    """
    def __init__(self, manifest, overrides=None):
        self.capacity = dict(manifest.get('resource_capacities', {}))
        for name, slots in (overrides or {}).items():
            if name not in self.capacity:
                raise Refused('invalid_resource_requirement', 'unknown capacity: ' + name)
            self.capacity[name] = slots
        if any(not isinstance(name, str) or not name or type(slots) is not int or slots <= 0
               for name, slots in self.capacity.items()):
            raise Refused('invalid_resource_requirement', 'capacities must be positive integers')
        self.requirements = {}
        for suite in manifest['suites']:
            name = suite['file']
            if name in self.requirements:
                raise Refused('invalid_resource_requirement', 'duplicate suite: ' + name)
            demand = suite.get('resources', {})
            if not isinstance(demand, dict):
                raise Refused('invalid_resource_requirement', name + ': resources must be an object')
            resolved = {}
            for resource, slots in demand.items():
                if resource not in self.capacity:
                    raise Refused('invalid_resource_requirement', name + ': unknown resource ' + resource)
                if slots == 'exclusive':
                    slots = self.capacity[resource]
                if type(slots) is not int or slots <= 0 or slots > self.capacity[resource]:
                    raise Refused('invalid_resource_requirement', name + ': impossible demand ' + resource)
                resolved[resource] = slots
            self.requirements[name] = resolved
        self.used = dict.fromkeys(self.capacity, 0)
        self.peak = dict(self.used)
        self.held = {}

    @classmethod
    def from_root(cls, root, overrides=None):
        return cls(json.loads((root / 'scripts/suites/manifest.json').read_text()), overrides)

    def demand(self, job):
        suite = job['case']['suite']
        if suite not in self.requirements:
            raise Refused('invalid_resource_requirement', 'undeclared suite: ' + suite)
        return self.requirements[suite]

    def select(self, pending):
        barred = set()
        for index, (_name, job) in enumerate(pending):
            demand = self.demand(job)
            if (not barred.intersection(demand) and
                    all(self.used[r] + n <= self.capacity[r] for r, n in demand.items())):
                return index
            barred.update(demand)
        return None

    def acquire(self, name, job):
        demand = self.demand(job)
        if name in self.held or any(self.used[r] + n > self.capacity[r] for r, n in demand.items()):
            raise Refused('invalid_resource_requirement', 'overcommitted reservation: ' + name)
        self.held[name] = demand
        for resource, slots in demand.items():
            self.used[resource] += slots
            self.peak[resource] = max(self.peak[resource], self.used[resource])

    def release(self, name):
        for resource, slots in self.held.pop(name).items():
            self.used[resource] -= slots

    def clear(self):
        for name in list(self.held):
            self.release(name)

    def run_futures(self, jobs, submit, limit):
        """The standalone driver uses the same reservations outside its thread pool."""
        pending, active, results = list(jobs.items()), {}, {}
        for _name, job in pending:
            self.demand(job)
        try:
            while pending or active:
                while pending and len(active) < limit:
                    index = self.select(pending)
                    if index is None:
                        break
                    name, job = pending.pop(index)
                    self.acquire(name, job)
                    try:
                        active[submit(job)] = name
                    except BaseException:
                        self.release(name)
                        raise
                if not active:
                    raise Refused('invalid_resource_requirement', 'no runnable pending job')
                done, _ = concurrent.futures.wait(active, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    name = active.pop(future)
                    self.release(name)
                    results[name] = future.result()
            return results
        finally:
            # A failing future cannot release reservations still used by other threads.
            concurrent.futures.wait(active)
            self.clear()

    def summary(self):
        return {'capacities': self.capacity, 'peak_slots': self.peak, 'remaining_slots': self.used}


def resource_capacities(arguments):
    capacities = {}
    for argument in arguments:
        try:
            name, value = argument.split('=', 1)
            slots = int(value)
            if not name or slots <= 0 or name in capacities:
                raise ValueError()
        except ValueError as error:
            raise argparse.ArgumentTypeError('resource capacity must be unique NAME=POSITIVE_INTEGER') from error
        capacities[name] = slots
    return capacities


class Workers:
    def __init__(self, deadline, resources=None, parallel=None):
        self.resources = resources
        self.deadline = deadline
        self.parallel = PARALLEL if parallel is None else max(1, parallel)
        self.active = {}
        self.owned_snapshots = {}
        self.invocations = 0
        self.driver_spans = {}
        self.outcomes = []
        self.peak = 0
        self.jobs = {}
        self.homes = {}
        self.ledgers = {}

    def check(self):
        if time.monotonic() >= self.deadline:
            raise Refused('mutation_budget_exceeded', 'combined deadline')

    def check_worker(self, name, started):
        if time.monotonic() - started >= WORKER_BUDGET:
            raise Refused('mutation_budget_exceeded', name + ': worker deadline')

    def release_snapshot(self, name):
        path = self.owned_snapshots.pop(name, None)
        if path is not None and path.exists():
            shutil.rmtree(path)

    def finish(self, name, error=None):
        proc, out, err, started = self.active[name]
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(), err.read()
        out.close()
        err.close()
        elapsed = time.monotonic() - started
        job = self.jobs[name]
        home = self.homes[name]
        record = dict(name=name, driver=job['case']['driver'], mode=job['mode'],
                      elapsed=elapsed, returncode=proc.returncode, pid=proc.pid,
                      output_directory=str(home),
                      stdout_bytes=len(stdout), stderr_bytes=len(stderr))
        result = None
        if error is None and 'snapshot_root' in job:
            # Trace is outside the worker's writable home. Check before trusting output.
            try:
                load(ROOT / 'scripts/case_trace.py').check(
                    home.parent / ('trace-' + home.name), job['snapshot_root'], job['declared_files'],
                    job.get('declared_absent', []), runtime=job['runtime_paths'], scratch=home,
                    directories=job.get('declared_directories', []),
                    runtime_absent=job.get('runtime_absent', []), after_confinement=True)
            except ValueError as trace_error:
                error = trace_error
        if error is None:
            if proc.returncode:
                error = Refused('driver_error', name + ': worker exit ' + str(proc.returncode))
            else:
                try:
                    result = json.loads(stdout)
                    if not isinstance(result, dict):
                        raise ValueError('worker result must be an object')
                except ValueError:
                    error = Refused('driver_error', name + ': invalid or empty worker JSON')
        if error is not None:
            record.update(error=getattr(error, 'code', 'driver_error'), detail=getattr(error, 'detail', str(error)),
                          stdout_tail=stdout.decode(errors='replace')[-2000:],
                          stderr_tail=stderr.decode(errors='replace')[-2000:])
        try:
            ownership = load(ROOT / 'scripts/mutation_ownership.py')
            record['cleanup'] = ownership.cleanup(self.homes[name], self.ledgers[name])
        except Exception as cleanup_error:
            error = Refused('worker_cleanup_error', name + ': ' + str(cleanup_error))
            record.update(error=error.code, detail=error.detail)
        record['elapsed'] = time.monotonic() - started
        self.outcomes.append(record)
        self.driver_spans[job['case']['driver']][1] = time.monotonic()
        del self.active[name]
        self.release_snapshot(name)
        if record.get('error') != 'worker_cleanup_error':
            self.resources.release(name)
        if error is not None:
            raise error
        return {'result': result, 'elapsed': elapsed}

    def cleanup(self, on_result=None):
        # Reap and account for every sibling, even after the first failure.
        errors = []
        for name in list(self.active):
            try:
                proc = self.active[name][0]
                error = (Refused('worker_cancelled', 'stage stopped before worker completed')
                         if proc.poll() is None else None)
                completed = self.finish(name, error)
                if on_result is not None:
                    on_result(name, completed)
            except (Refused, ValueError) as error:
                errors.append(error)
        # Snapshots prepared for workers that never launched are owned here too.
        for name in list(self.owned_snapshots):
            self.release_snapshot(name)
        return errors

    def run(self, jobs, directory, root, on_result=None):
        if self.resources is None:
            self.resources = SuiteResources.from_root(root)
        jobs = {name: dict(job) for name, job in jobs.items()}
        self.jobs.update(jobs)
        pending = list(jobs.items())
        # Validate every job before launching any, including ones behind blocked jobs.
        for _name, job in pending:
            self.resources.demand(job)
        results = {}
        try:
            while pending or self.active:
                self.check()
                while pending and len(self.active) < self.parallel:
                    index = self.resources.select(pending)
                    if index is None:
                        break
                    name, job = pending.pop(index)
                    home = directory / str(self.invocations)
                    home.mkdir()
                    self.homes[name] = home
                    bindir = home / 'bin'
                    bindir.mkdir()
                    (bindir / 'python3').symlink_to(sys.executable)
                    if job.get('declared_case'):
                        self.owned_snapshots[name] = directory / 'cases' / str(self.invocations)
                        job.update(self.case_reuse.prepare(job['case'], self.owned_snapshots[name]))
                    jobpath = home / 'job.json'
                    jobpath.write_bytes(canonical(job))
                    out, err = (open(directory / (str(self.invocations) + '-' + f), 'w+b')
                                for f in ('stdout', 'stderr'))
                    self.resources.acquire(name, job)
                    # The ownership ledger is this coordinator's file, beside the home and outside
                    # every worker grant; the worker only inherits an append descriptor to it.
                    self.ledgers[name] = directory / ('ownership-' + str(self.invocations) + '.jsonl')
                    ledger = None
                    try:
                        ledger = os.open(self.ledgers[name], os.O_WRONLY | os.O_CREAT | os.O_EXCL
                                         | os.O_APPEND | os.O_CLOEXEC, 0o600)
                        worker_root = Path(job.get('snapshot_root', root))
                        # -I keeps user site and PYTHON* variables out. A fresh worker keeps the
                        # system site-packages its suites ran with before confinement: without it
                        # an optional oracle (PyYAML for 0119) stands down and its row passes a
                        # mutant. A declared case runs only its keyed runtime set, so it adds -S.
                        argv = [sys.executable, '-I', *(('-S',) if 'snapshot_root' in job else ()), '-B',
                                '-X', 'pycache_prefix=' + str(home / 'bytecode'),
                                str(ROOT / 'scripts/reuse_worker.py'),
                                'worker', str(worker_root), str(ledger), str(jobpath)]
                        if 'snapshot_root' in job:
                            tracer = load(ROOT / 'scripts/case_trace.py')
                            argv = tracer.command(directory / ('trace-' + str(self.invocations)), argv)
                        # A worker reads its job from its file, never from the coordinator's
                        # stdin, which may be a socket the worker's boundary would refuse.
                        proc = subprocess.Popen(argv, cwd=worker_root,
                                                env=fixed_env(home, str(bindir) + ':/usr/bin:/bin'),
                                                stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                                pass_fds=(ledger,), start_new_session=True)
                    except BaseException as error:
                        out.close()
                        err.close()
                        self.resources.release(name)
                        self.outcomes.append(dict(name=name, driver=job['case']['driver'], mode=job['mode'],
                                                  elapsed=0.0, returncode=None, error='worker_launch_error',
                                                  detail=str(error), stdout_bytes=0, stderr_bytes=0,
                                                  pid=None, output_directory=str(home)))
                        if isinstance(error, Exception):
                            raise Refused('worker_launch_error', name + ': ' + str(error)) from error
                        raise
                    finally:
                        if ledger is not None:
                            os.close(ledger)
                    self.active[name] = (proc, out, err, time.monotonic())
                    self.invocations += 1
                    self.peak = max(self.peak, len(self.active))
                    self.driver_spans.setdefault(job['case']['driver'], [time.monotonic(), time.monotonic()])
                for name, (proc, out, err, started) in list(self.active.items()):
                    if proc.poll() is None:
                        try:
                            self.check_worker(name, started)
                        except Refused as error:
                            self.finish(name, error)
                        continue
                    results[name] = self.finish(name)
                    if on_result is not None:
                        on_result(name, results[name])
                if self.active:
                    time.sleep(0.02)
            self.check()
            return results
        finally:
            self.cleanup(on_result)


def worker(job):
    sandbox = load(ROOT / 'scripts/mutation_sandbox.py')
    if 'runtime_paths' in job:
        sandbox.restrict(ROOT, Path(os.environ['TMPDIR']), job['runtime_paths'], legacy=False)
    else:
        sandbox.restrict(ROOT, Path(os.environ['TMPDIR']))
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


def snapshot(root, expected_common, destination, files, head):
    command([sys.executable, '-I', '-S', str(ROOT / '.veldo/candidate_git.py'), '--root', str(root),
             '--expected-common', str(expected_common), '--clone-to', str(destination)],
            fixed_env('/nonexistent'))
    # The clone is this stage's own repository: it names the common directory it just created.
    common = common_directory(destination)
    git(destination, common, 'checkout', '-q', '--detach', head)
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
    return common




def run_stage(root, expected_common, capacities=None, findings=None, names=None, log_dir=None,
              drivers=None, parallel=None, diff_dir=None, force_fresh=False):
    """expected_common is the trusted Git common directory of root, named by the caller that owns
    root: the authority's own for the gate, a fixture's own for the fixture's creator."""
    started = time.monotonic()
    deadline = started + BUDGET
    workers = Workers(deadline, parallel=parallel)
    receipt = {'schema': 'veldo.mutation-stage/v1', 'results': [],
               'registered': 0, 'executed': 0, 'reused': 0,
               'rejected': 0, 'drivers': {}, 'surviving_workers': 0, 'invalid_results': []}
    cases, reuse = [], None
    previous = signal.getsignal(signal.SIGALRM)

    def timeout(signum, frame):
        raise Refused('mutation_budget_exceeded', 'combined deadline')

    signal.signal(signal.SIGALRM, timeout)
    # Enumeration itself runs under the floor; the full cap is armed once the count is known.
    signal.setitimer(signal.ITIMER_REAL, BUDGET)
    try:
        full_inventory = inventory(root, expected_common)
        cases = [c for c in full_inventory if (not findings or c['finding'] in findings)
                 and (not drivers or c['driver'] in drivers)
                 and (not names or c['name'] in names)]
        if not cases or (names and set(names) - {c['name'] for c in cases}):
            raise Refused('incomplete_inventory', 'empty or unknown subset')
        receipt['scope'] = 'selected' if findings or names or drivers else 'full'
        receipt['registered'] = len(cases)
        budget = budget_for(len(full_inventory), workers.parallel)
        receipt['budget_seconds'] = budget
        workers.deadline = started + budget
        signal.setitimer(signal.ITIMER_REAL, max(workers.deadline - time.monotonic(), 0.001))
        for driver in DRIVERS:
            own = [c for c in cases if c['driver'] == driver]
            receipt['drivers'][driver] = {'inventory_digest': digest(own), 'registered': len(own),
                                           'worker_seconds': 0.0, 'executed': 0, 'reused': 0}
        files = read_inputs(root, expected_common)
        head = git(root, expected_common, 'rev-parse', 'HEAD')
        receipt['input_digest'] = digest({'files': file_identity(files), 'head': head})
        receipt['implementation_digest'] = hashlib.sha256(
            files['scripts/check_gate_mutations.py'][1]).hexdigest()
        reuse_module = load(ROOT / 'scripts/case_reuse.py')
        reuse = reuse_module.Session(root, files, cases, head,
            {'fixture_version': FIXTURE_VERSION, 'capacities': capacities,
             'worker_environment': fixed_env('<private-worker-home>')}, force_fresh=force_fresh)
        receipt['force_fresh'] = reuse.forced
        receipt['reuse_qualified'] = sum(key is not None for key in reuse.keys.values())
        results = {}
        fresh = []
        for case in cases:
            record = reuse.lookup(case, validate_result)
            if record is None:
                fresh.append(case)
            else:
                results[case['identity']] = record
                receipt['results'].append(reuse.evidence(case, record, True))
        with tempfile.TemporaryDirectory(prefix='veldo-mutations-') as temporary:
            directory = Path(temporary)
            frozen = directory / 'input'
            frozen_common = snapshot(root, expected_common, frozen, files, head)
            # Registries executed again from the frozen bytes: an enumeration race is red.
            if inventory(frozen, frozen_common) != full_inventory:
                raise Refused('incomplete_inventory', 'registry changed while snapshotting')
            if diff_dir is not None:
                destination = Path(diff_dir)
                destination.mkdir(parents=True, exist_ok=True)
                # The authority's own materializer: candidate driver code never runs here.
                owner = load(ROOT / 'scripts/mutation_observer.py')
                safe = reuse_module.I.safe_name
                for case in cases:
                    # Every path part comes from the candidate's registry: none may leave its root.
                    try:
                        base = 'scripts/fixtures' if case.get('fixture') else safe(case.get('dir', '.veldo'))
                        relative = str(Path(base) / safe(case['module']))
                        if Path(safe(case['name'])).name != case['name']:
                            raise ValueError('invalid case name: ' + case['name'])
                    except ValueError as error:
                        raise Refused('incomplete_inventory', str(error)) from error
                    before = (frozen / relative).read_text()
                    after = owner.mutate(before, case)
                    (destination / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                        before.splitlines(keepends=True), after.splitlines(keepends=True), n=0,
                        fromfile='a/' + relative, tofile='b/' + relative)))
            workers.case_reuse = reuse
            prepared_cases = {c['identity']: {'declared_case': True} for c in fresh
                              if c['identity'] in getattr(reuse, 'snapshots', {})}
            def group_for(case):
                return case['identity'] if prepared_cases.get(case['identity']) else control_group(case)
            controls = {}
            for case in fresh:
                group = group_for(case)
                for mode in ('baseline', 'noop'):
                    controls.setdefault(group + ':' + mode, {'case': case, 'mode': mode,
                                     **prepared_cases.get(case['identity'], {})})
            workers.resources = SuiteResources.from_root(frozen, capacities)
            if log_dir is not None:
                log_dir = Path(log_dir).resolve()
                log_dir.mkdir(parents=True, exist_ok=False)
                directory = log_dir
            control_results = workers.run(controls, directory, frozen)
            by_identity = {c['identity']: c for c in fresh}

            def collect(identity, completed):
                # Each mutant is judged as its worker completes, so a later failure or
                # timeout cannot discard results that were already produced.
                case = by_identity[identity]
                group = group_for(case)
                prepared = completed['result']
                try:
                    record = {'schema': SCHEMA, 'case': case,
                              'fixture_version': FIXTURE_VERSION,
                              'input_digest': (reuse.input_digest(case) if hasattr(reuse, 'input_digest')
                                               else reuse.base_digest),
                              **{key: prepared[key] for key in ('replacement_count', 'old_digest', 'new_digest')},
                              'baseline': control_results[group + ':baseline']['result']['observation'],
                              'noop': control_results[group + ':noop']['result']['observation'],
                              'mutant': prepared['observation']}
                    validate_result(record, case)
                except (Refused, KeyError, TypeError) as error:
                    receipt['invalid_results'].append(dict(case=case, error=getattr(error, 'code', 'driver_error'),
                                                           detail=str(error)))
                    return
                results[identity] = record
                receipt['results'].append(dict(reuse.evidence(case, record, False),
                                               elapsed=completed['elapsed']))

            workers.run({c['identity']: {'case': c, 'mode': 'mutant',
                                         **prepared_cases.get(c['identity'], {})}
                         for c in fresh}, directory, frozen, on_result=collect)
            if receipt['invalid_results']:
                first = receipt['invalid_results'][0]
                raise Refused(first['error'], first['detail'])
            # Reject changes to the checked inputs during execution.
            if not inputs_unchanged(root, expected_common, files, head):
                raise Refused('driver_error', 'inputs changed during stage')
            if not reuse.unchanged():
                raise Refused('driver_error', 'runtime inputs changed during stage')
            workers.check()
            if set(results) != {c['identity'] for c in cases}:
                raise Refused('incomplete_inventory', 'registered/result identities differ')
            for case in cases:
                validate_result(results[case['identity']], case)
        workers.check()
        for case in fresh:
            reuse.publish(case, results[case['identity']], validate_result)
        if reuse.store and reuse.store.integrity_errors:
            raise Refused('reuse_integrity_conflict', 'conflicting cache record: ' +
                          ', '.join(reuse.store.integrity_errors))
        workers.check()
        receipt['status'] = 'passed'
    except Exception as error:  # All incomplete drives are named errors, never detections.
        receipt['status'] = 'failed'
        receipt['error'] = getattr(error, 'code', 'driver_error')
        receipt['detail'] = str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        try:
            workers.cleanup()
        finally:
            # Restore the caller's handler even when cleanup itself fails.
            signal.signal(signal.SIGALRM, previous)
        receipt['worker_outcomes'] = workers.outcomes
        failed_workers = [o for o in workers.outcomes if 'error' in o]
        receipt['invalid_results'].extend(failed_workers)
        # A launched mutant with no usable output is still an execution, never a
        # rejection. Launch errors are attempts only (returncode is None). A reused
        # case launches no worker, so it is never counted as executed.
        launched = {o['name'] for o in workers.outcomes
                    if o['mode'] == 'mutant' and o['returncode'] is not None}
        completed = {r['case']['identity'] for r in receipt['results']}
        receipt['case_receipts'] = []
        for case in cases:
            identity = case.get('identity')
            if identity is None:
                continue
            hit = reuse is not None and identity in reuse.hits
            attempted = identity in launched
            receipt['executed'] += int(attempted)
            receipt['reused'] += int(hit)
            receipt['rejected'] += int(identity in completed)
            summary = receipt['drivers'].get(case['driver'])
            if summary is not None:
                summary['executed'] += int(attempted)
                summary['reused'] += int(hit)
            receipt['case_receipts'].append({
                'identity': identity, 'key': reuse.keys[identity] if reuse else None,
                'source': 'reused' if hit else ('fresh' if attempted else 'pending'),
                'reason': reuse.reasons[identity] if reuse else 'setup_failed',
                'validated': identity in completed})
        for driver, summary in receipt['drivers'].items():
            span = workers.driver_spans.get(driver, (0, 0))
            summary['wall_seconds'] = span[1] - span[0]
            summary['worker_seconds'] = sum(o['elapsed'] for o in workers.outcomes if o['driver'] == driver)
        if workers.resources is not None:
            receipt['resources'] = workers.resources.summary()
        receipt['reuse_integrity_errors'] = (list(reuse.store.integrity_errors)
                                             if reuse is not None and reuse.store else [])
        receipt['peak_workers'] = workers.peak
        receipt['surviving_workers'] = len(workers.active)
        receipt['parallel_workers'] = workers.parallel
        receipt['worker_invocations'] = workers.invocations
        receipt['elapsed'] = time.monotonic() - started
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--resource-capacity', action='append', default=[], metavar='NAME=N')
    parser.add_argument('--finding', type=int, action='append')
    parser.add_argument('--case', action='append', dest='names')
    parser.add_argument('--worker-log-dir', type=Path)
    args = parser.parse_args()
    if args.worker:
        # Developer entry only: no coordinator launches it, so it keeps no ownership ledger.
        # Gate workers start from reuse_worker.py, which reports to the coordinator's ledger.
        print(json.dumps(worker(json.loads(args.worker.read_text()))))
        return 0
    # The gate names the authority checkout's own common directory; a candidate root is a linked
    # worktree of it, and its marker is checked against that directory before any Git runs.
    receipt = run_stage(args.root, common_directory(ROOT), capacities=resource_capacities(args.resource_capacity),
                        findings=args.finding, names=args.names, log_dir=args.worker_log_dir)
    if args.receipt:
        args.receipt.write_bytes(canonical(receipt))
    print(json.dumps(receipt, sort_keys=True), flush=True)
    print('mutations: {status} registered={registered} executed={executed} '
          'reused={reused} rejected={rejected} workers={worker_invocations} elapsed={elapsed:.3f}s'.format(**receipt), flush=True)
    return 0 if receipt['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
