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
import math
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DRIVERS = ('check_teeth_mutations.py', 'check_review_mutations.py')
SCHEMA = 'veldo.mutation-result/v1'
FIXTURE_VERSION = 1
# Legacy measurement API names are retained for callers. These values estimate
# admission cost only; no worker or stage is held to the resulting numbers.
BUDGET = 120
PER_CASE_SECONDS = 2.0        # measured at REFERENCE_WORKERS workers
REFERENCE_WORKERS = 8
WORKER_BUDGET = 120          # admission estimate only; never a deadline
WORKER_CEILING = 1800
WORKER_MULTIPLIER = 3.0
WAIT_HANG_SECONDS = 600
PROCESS_HANG_SECONDS = 3600
CASE_TIMES = Path.home() / '.cache' / 'veldo' / 'mutation-case-seconds'

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
                cpus = int(quota) / int(period)
                best = cpus if best is None else min(best, cpus)
        except (OSError, ValueError):
            pass
        parent = os.path.dirname(path)
        if path == top or parent == path:      # the mount, or the filesystem root: stop
            return best
        path = parent


def worker_count(cpus=None, cgroup_root='/sys/fs/cgroup', membership='/proc/self/cgroup'):
    """Safety ceiling only: twice usable CPUs, with a floor of two.

    Actual concurrency is admitted by the gate ledger's measured resource claims.
    """
    if cpus is None:
        try:
            cpus = len(os.sched_getaffinity(0))
        except (AttributeError, OSError):
            cpus = os.cpu_count() or 2
        quota = _quota_cpus(cgroup_root, membership)
        if quota:
            cpus = min(cpus, quota)
    return max(2, int(2 * cpus))


PARALLEL = 1 if '--worker' in sys.argv else min(16, worker_count())
OUTPUTS = {'.veldo/last_verify', '.veldo/events.jsonl', '.veldo/gate-schedule.json',
           '.veldo/opened_files.json'}


def budget_for(count, workers=REFERENCE_WORKERS, phases=(), resources=None, floor=None):
    """Estimate sequential scheduling phases, including resource admission barriers.

    Full workers charge W/m; full resources charge slot-time/capacity. A blocked
    multi-slot request can also wait for earlier users to drain, at most their
    largest estimate. The last active jobs contribute one final tail.
    """
    phases = [list(jobs) for jobs in phases]
    if floor is not None:
        workers = guaranteed_workers([j for phase in phases for j in phase], floor, workers)
    scheduled = 0
    for jobs in phases:
        jobs = list(jobs)
        deadlines = [job.get('budget_seconds', WORKER_BUDGET) for job in jobs]
        work, tail = sum(deadlines), max(deadlines, default=0)
        chains = 0
        if resources is not None:
            demands = [resources.demand(job) for job in jobs]
            for resource, capacity in resources.capacity.items():
                prefix = 0
                for seconds, demand in zip(deadlines, demands):
                    slots = demand.get(resource, 0)
                    if slots:
                        chains += slots * seconds / capacity
                        if slots > 1:
                            chains += prefix
                        prefix = max(prefix, seconds)
        if floor is not None:
            for resource in ('cpu', 'memory'):
                chains += sum(j['claim'][resource] * d for j, d in zip(jobs, deadlines)) / floor[resource]
        scheduled += min(work, work / max(1, workers) + tail + chains)
    return max(BUDGET + scheduled, PER_CASE_SECONDS * count * REFERENCE_WORKERS / max(1, min(workers, REFERENCE_WORKERS)))


class Refused(Exception):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(f'{code}: {detail}')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def case_time_key(case, files, leg):
    """Duration identity, independent of HEAD, proofs and unrelated registry cases.

    This is not an input-closure proof for result reuse. Bind the case's own executable
    definition and its direct sources, plus the authority execution machinery and leg.
    """
    target = str(Path('scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo'))
                 / case['module'])
    paths = {target, 'scripts/suites/' + case['suite'], 'scripts/suites/shared.py',
             'scripts/check_gate_mutations.py', 'scripts/mutation_observer.py',
             'scripts/reuse_worker.py', 'scripts/mutation_sandbox.py', 'scripts/agent_sandbox.py',
             'scripts/mutation_ownership.py'}
    sources = {path: file_identity({path: files[path]})[path] if path in files else None
               for path in sorted(paths)}
    return digest({'authority': str(ROOT), 'case': case, 'sources': sources,
                   'leg': 'unconfined' if in_leg(leg, case) else 'confined',
                   'declaration': leg})[:32]


def case_samples(key, times, now):
    """Live candidate peaks; legacy single samples retain their original file age."""
    try:
        path = Path(times) / (key + '.json')
        item = json.loads(path.read_text())
        if item['authority'] != str(ROOT) or item['key'] != key:
            return []
        samples = item.get('samples', [[path.stat().st_mtime, item['seconds']]])
        return [(at, seconds) for at, seconds in samples
                if type(at) in (int, float) and math.isfinite(at)
                and now - 30 * 86400 <= at <= now
                and type(seconds) in (int, float) and math.isfinite(seconds) and seconds > 0]
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return []


def case_deadline(key, times=CASE_TIMES):
    """Historical API: return an admission estimate, never a worker deadline."""
    seconds = max((seconds for _, seconds in case_samples(key, times, time.time())), default=0)
    if not seconds:
        return WORKER_BUDGET
    return scaled_deadline(seconds)


def scaled_deadline(seconds):
    """WORKER_MULTIPLIER times a measured time, within the floor and the ceiling."""
    # Clamp before multiplying, including finite floats near overflow.
    return min(WORKER_CEILING, max(WORKER_BUDGET,
               WORKER_MULTIPLIER * min(seconds, WORKER_CEILING)))


def case_deadlines(keys, times=CASE_TIMES):
    """Historical API: admission estimates, or None until this stage measures a baseline.

    Neither these values nor the same-stage refresh can end or reject a worker.
    """
    now = time.time()
    return {identity: case_deadline(key, times) if case_samples(key, times, now) else None
            for identity, key in keys.items()}


def record_case_times(root, samples, times=CASE_TIMES, *, authority=False):
    """Only authority coordination after a passing fresh stage calls this writer.

    Only the authority CLI opts in to the owner store, including when checking a landing
    candidate in another root. Library/fixture calls stand down. An explicitly supplied
    scratch store is for tests; no command line or environment variable selects it.
    """
    if Path(times) == CASE_TIMES and not authority:
        return False
    for key, seconds in samples.items():
        if not math.isfinite(seconds) or seconds <= 0:
            continue
        try:
            Path(times).mkdir(mode=0o700, parents=True, exist_ok=True)
            target = Path(times) / (key + '.json')
            now = time.time()
            samples = [(at, value) for at, value in case_samples(key, times, now) if value > seconds]
            samples.append((now, seconds))
            peak = max(value for _, value in samples)
            try:
                previous = json.loads(target.read_text())
            except (OSError, ValueError):
                previous = {}
            if not isinstance(previous, dict):
                previous = {}
            resources = {k: previous[k] for k in ('identity', 'suite') if k in previous}
            resources['resource_runs'] = resource_samples(previous, now)
            fd, pending = tempfile.mkstemp(prefix='.pending-', dir=str(times))
            with os.fdopen(fd, 'w') as handle:
                json.dump({'authority': str(ROOT), 'key': key, 'seconds': peak, 'samples': samples,
                           'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **resources}, handle,
                          sort_keys=True)
            os.replace(pending, target)
            # Same file naming and ownership metadata as VELDO-0214's store.
            load(ROOT / 'scripts/gate_legs.py').prune_times(times, keep=target)
        except OSError as error:
            print('   mutation: could not record case time in %s (%s)' % (times, error),
                  file=sys.stderr, flush=True)
    return True


def record_case_resources(cases, keys, outcomes, group_for, times=CASE_TIMES, *, authority=False):
    """Called only after the complete fresh stage validates and inputs stay stable."""
    if not authority and Path(times) == CASE_TIMES:
        return False
    by_name = {o['name']: o for o in outcomes}
    for case in cases:
        key = keys[case['identity']]
        names = [case['identity'], group_for(case) + ':baseline', group_for(case) + ':noop']
        runs = []
        now = time.time()
        for name in names:
            outcome = by_name[name]
            if 'error' in outcome or not outcome.get('measurement'):
                break
            runs.append(dict(outcome['measurement'], elapsed=outcome['elapsed'],
                             mode=outcome['mode'], at=now))
        if len(runs) != 3 or len(resource_samples({'resource_runs': runs}, now)) != 3:
            continue
        target = Path(times) / (key + '.json')
        try:
            item = json.loads(target.read_text())
            if item.get('authority') != str(ROOT) or item.get('key') != key:
                continue
            item.update(identity=case['identity'], suite=case['suite'],
                        resource_runs=resource_samples(item, now) + runs)
            fd, pending = tempfile.mkstemp(prefix='.pending-', dir=str(times))
            with os.fdopen(fd, 'w') as handle:
                json.dump(item, handle, sort_keys=True)
            os.replace(pending, target)
            timing = load(ROOT / 'scripts/gate_legs.py')
            timing.prune_times(times, keep=target)
        except (OSError, ValueError, TypeError) as error:
            print('   mutation: could not record case resources (%s)' % error, file=sys.stderr, flush=True)
    return True


def resource_samples(item, now):
    """Resource runs have the same lifetime as duration peaks, but keep every run."""
    if not isinstance(item, dict):
        return []
    runs = item.get('resource_runs', [])
    if not isinstance(runs, list):
        return []
    return [r for r in runs if isinstance(r, dict)
            and all(type(r.get(k)) in (int, float) and math.isfinite(r[k]) and r[k] > 0
                    for k in ('at', 'cpu_seconds', 'elapsed', 'peak_anon_bytes'))
            and ('peak_memory_bytes' not in r or (type(r['peak_memory_bytes']) in (int, float)
                 and math.isfinite(r['peak_memory_bytes']) and r['peak_memory_bytes'] >= 0))
            and now - 30 * 86400 <= r['at'] <= now]


def resource_claim(runs):
    return dict(cpu=max(r['cpu_seconds'] / r['elapsed'] for r in runs),
                memory=max(max(r['peak_anon_bytes'], r.get('peak_memory_bytes', 0)) for r in runs))


class CaseClaims:
    """Read the authority store once. Previous keys are hints, never deadline reuse."""
    def __init__(self, times=CASE_TIMES):
        self.records = {}
        now = time.time()
        for path in Path(times).glob('*.json'):
            try:
                item = json.loads(path.read_text())
                runs = resource_samples(item, now)
                if (not runs or item.get('authority') != str(ROOT) or item.get('key') != path.stem
                        or not isinstance(item.get('identity'), str) or not isinstance(item.get('suite'), str)):
                    continue
                self.records[path.stem] = dict(item, resource_runs=runs)
            except (OSError, ValueError, TypeError, OverflowError):
                continue

    def claim(self, case, key):
        item = self.records.get(key)
        if item is not None and (item['identity'] != case['identity'] or item['suite'] != case['suite']):
            item = None
        source, keys = 'this_key', [key]
        if item is None:
            previous = [i for i in self.records.values() if i['identity'] == case['identity']]
            if previous:
                item = max(previous, key=lambda i: max(r['at'] for r in i['resource_runs']))
                source, keys = 'previous_key', [item['key']]
        if item is not None:
            claim = resource_claim(item['resource_runs'])
        else:
            # One latest record per identity, so key churn cannot weight a median.
            latest = {}
            for record in self.records.values():
                identity = record['identity']
                if identity not in latest or max(r['at'] for r in record['resource_runs']) > max(
                        r['at'] for r in latest[identity]['resource_runs']):
                    latest[identity] = record
            members = [i for i in latest.values() if i['suite'] == case['suite']]
            source = 'suite_median'
            if not members:
                members, source = list(latest.values()), 'all_median'
            if members:
                claims = [resource_claim(i['resource_runs']) for i in members]
                claim = {r: statistics.median(c[r] for c in claims) for r in ('cpu', 'memory')}
                keys = sorted(i['key'] for i in members)
            else:
                claim, source, keys = dict(cpu=1.0, memory=2**30), 'default', []
        return dict(claim, source=source, keys=keys)


def guaranteed_workers(jobs, floor, ceiling):
    largest = {r: max((j['claim'][r] for j in jobs), default=1) for r in ('cpu', 'memory')}
    guaranteed = min(floor[r] / largest[r] for r in largest)
    return min(ceiling, max(2, math.floor(guaranteed)))


class Admission:
    """Local manifest admission precedes the authority ledger's final grant."""
    def __init__(self, client, capacity, floor, meter_factory=None):
        self.client, self.capacity, self.floor = client, capacity, floor
        self.meter_factory = meter_factory
        self.held, self.events, self.waiting = {}, [], {}
        self.peak = dict(cpu=0, memory=0)
        self.blocked = {}

    @classmethod
    def authority(cls):
        scheduler = load(ROOT / 'scripts/gate_schedule.py')
        if scheduler.CHANNEL not in os.environ:
            raise Refused('worker_launch_error', 'measured admission requires the gate ledger channel')
        client = scheduler.Client()
        try:
            state = client.handoff()
        except (ValueError, OSError) as error:
            client.close()
            raise Refused('invalid_resource_requirement', str(error)) from error
        scope = os.environ.get('VELDO_GATE_SCOPE', '')
        ownership = load(ROOT / 'scripts/mutation_ownership.py')
        return cls(client, state['capacities'], state['floor'],
                   lambda name: ownership.WorkerMeter(scope, name))

    def validate(self, job):
        claim = job['claim']
        if any(type(claim.get(r)) not in (int, float) or not math.isfinite(claim[r])
               or claim[r] <= 0 or claim[r] > self.capacity[r] for r in ('cpu', 'memory')):
            raise Refused('invalid_resource_requirement', 'worker claim exceeds gate capacity or is invalid')

    def acquire(self, name, job, resources):
        self.validate(job)
        claim = job['claim']
        slots = resources.demand(job).get('systemd_user_manager', 0)
        # The existing channel represents one shared slot or an exclusive hold.
        if slots not in (0, 1, resources.capacity.get('systemd_user_manager')):
            raise Refused('invalid_resource_requirement', 'ledger cannot express multiple shared manager slots')
        manager = ('exclusive' if slots and slots == resources.capacity['systemd_user_manager']
                   else 'shared' if slots else 'none')
        began = self.waiting.setdefault(name, time.monotonic())
        try:
            granted = self.client.acquire(name, claim['cpu'], claim['memory'], manager)
        except ValueError as error:
            raise Refused('invalid_resource_requirement', str(error)) from error
        reply = getattr(self.client, 'last_reply', {})
        if not granted:
            self.blocked.setdefault(name, set()).add(reply.get('resource', 'unknown'))
            return False
        self.held[name] = claim
        totals = {r: sum(c[r] for c in self.held.values()) for r in ('cpu', 'memory')}
        self.events.append(dict(name=name, claim=claim, waited_seconds=time.monotonic() - began,
                                resource=sorted(self.blocked.pop(name, set())),
                                granted=reply.get('totals', totals), capacities=self.capacity))
        self.waiting.pop(name)
        for r in self.peak:
            self.peak[r] = max(self.peak[r], totals[r])
        return True

    def release(self, name):
        if name in self.held:
            self.client.release(name)
            del self.held[name]

    def close(self):
        self.client.close()


def control_jobs(cases, group_for, prepared, deadlines, claims=None):
    """Shared controls must accommodate every case whose observations they supply."""
    controls = {}
    for case in cases:
        for mode in ('baseline', 'noop'):
            name = group_for(case) + ':' + mode
            job = controls.setdefault(name, {'case': case, 'mode': mode,
                                             **prepared.get(case['identity'], {})})
            job['budget_seconds'] = max(job.get('budget_seconds', 0), deadlines[case['identity']])
            if claims is not None:
                member = claims[case['identity']]
                prior = job.get('claim', member)
                job['claim'] = dict(cpu=max(prior['cpu'], member['cpu']),
                                    memory=max(prior['memory'], member['memory']),
                                    source='group_largest',
                                    keys=sorted(set(prior['keys']) | set(member['keys'])))
    return controls


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Loaded when a stage runs, from the ROOT then in force: a mutant of this file is executed from a
# scratch directory and its authority points ROOT back at the real helpers only after import.
# The bound loader is not the module's load name, which fixtures stub for the helpers they double.
AUDIT = None
_load_audit = load


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
    # Run inside a tree the agent launcher made (a suite of the gate's), the launcher this starts is
    # nested and is handed the tree's marker (VELDO-0210 AC6).
    result = subprocess.run(confined_command(root, [sys.executable, '-I', '-S',
        str(ROOT / 'scripts/reuse_worker.py'), 'inventory', str(root)]),
        capture_output=True, text=True, timeout=WAIT_HANG_SECONDS, env=env,
        pass_fds=load(ROOT / 'scripts/agent_sandbox.py').launcher_fds())
    if result.returncode:
        raise Refused('candidate_execution_denied', result.stderr[-2000:])
    return json.loads(result.stdout)


def fixed_env(home, binpath='/usr/bin:/bin'):
    return {'PATH': binpath, 'HOME': str(home), 'TMPDIR': str(home),
            'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
            'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1',
            'PYTHONHASHSEED': '0', 'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}


def fresh_env(home, binpath='/usr/bin:/bin'):
    """The fixed worker environment plus its enclosing private fixture allocation.

    Fresh workers start a nested tree and allocate a child beneath this root. Declared
    workers use fixed_env alone: their keyed runtime boundary grants no fixture tree.
    """
    environment = fixed_env(home, binpath)
    environment.update({key: os.environ[key] for key in
                        ('VELDO_FIXTURE_ROOT', 'VELDO_FIXTURE_PARENT') if key in os.environ})
    return environment


def command(args, env, with_stderr=False):
    """Even setup subprocesses belong to an owned, bounded process group."""
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, start_new_session=True)
    try:
        out, err = proc.communicate(timeout=WAIT_HANG_SECONDS)
        if proc.returncode:
            raise subprocess.CalledProcessError(proc.returncode, args, out, err)
        return (out, err) if with_stderr else out
    except subprocess.TimeoutExpired as error:
        raise Refused('hung', 'setup subprocess made no progress') from error
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()


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
                       not isinstance(r[0], str) or (type(r[1]) is not bool and r[1] not in ('hung', 'not_run')) for r in rows):
        raise ValueError('invalid observations')
    if value['count'] != len(rows) or value['row_names'] != [n for n, _ in rows]:
        raise ValueError('inconsistent row inventory')
    if value['failed_rows'] != [n for n, ok in rows if ok is False]:
        raise ValueError('inconsistent false rows')
    return rows


def baselined(case, observation, baseline=None):
    """An absent first census is unknown, never proof of a converted suite."""
    if baseline is None:
        path = ROOT / 'scripts/suites/wallclock_baseline.json'
        if not path.exists():
            return True
        baseline = json.loads(path.read_text())
    entries = baseline['entries'] if isinstance(baseline, dict) else baseline
    if not isinstance(entries, list) or any(not isinstance(e, dict) or
            not isinstance(e.get('file'), str) or type(e.get('count')) is not int
            or e['count'] <= 0 for e in entries):
        raise ValueError('invalid wallclock baseline')
    paths = {'scripts/suites/' + case['suite'], *observation.get('opened_files', [])}
    return any(entry['file'] in paths and entry['count'] > 0 for entry in entries)


def validate_result(record, case, *, baseline=None, store=None):
    try:
        scoped = record['schema'] == 'veldo.mutation-result/v2'
        if (record['schema'] not in (SCHEMA, 'veldo.mutation-result/v2') or record['case'] != case
                or record['fixture_version'] != FIXTURE_VERSION):
            raise ValueError('identity mismatch')
        honest, noop, broken = (observations(record[k]) for k in ('baseline', 'noop', 'mutant'))
        if (not all(ok is True for _, ok in honest) or noop != honest
                or any(record[k].get('watchdog_fired') or record[k].get('hung_rows')
                       or record[k].get('not_run_rows') for k in ('baseline', 'noop'))):
            failures = {mode: {'failed_rows': record[mode].get('failed_rows', []),
                               'failed_details': record[mode].get('failed_details', []),
                               'hung_rows': record[mode].get('hung_rows', [])}
                        for mode in ('baseline', 'noop')}
            raise Refused('control_failed', case['identity'] + ': completed controls: '
                          + json.dumps(failures, sort_keys=True))
        mutant = record['mutant']
        stalled = {n.split()[-1] for n in mutant.get('hung_rows', []) + mutant.get('not_run_rows', [])}
        stalled.update(n.split()[-1] for n, state in broken if state in ('hung', 'not_run'))
        if mutant.get('watchdog_fired') or stalled.intersection(case['rows']):
            raise Refused('hung_not_killed', case['identity'] + ': target hung or not run')
        targets = case['rows']
        if scoped:
            validate_scope(record, case, store, baseline=baseline)
            if record['execution_scope'] == 'rows':
                targets = [n.split()[-1] for n in record['selected_rows']]
                honest = [row for row in honest if row[0] in record['selected_rows']]
        if not (collections.Counter(n for n, _ in honest) <=
                collections.Counter(n for n, _ in broken)):
            raise Refused('missing_target', case['identity'] + ': baseline rows removed')
        killed = []
        for label in targets:
            before = [ok for name, ok in honest if name.split()[-1] == label]
            after = [(name, ok) for name, ok in broken if name.split()[-1] == label]
            if before != [True] or len(after) != 1:
                raise Refused('missing_target', label)
            name, state = after[0]
            if state is False:
                kind = mutant.get('failure_kinds', {}).get(name, 'assertion')
                if kind not in ('assertion', 'terminal'):
                    raise ValueError('invalid failure evidence')
                killed.append(dict(row=name, kill_by=kind))
        if not killed:
            raise Refused('mutation_survived', case['identity'])
        if record['replacement_count'] != 1 or record['old_digest'] == record['new_digest']:
            raise ValueError('invalid mutation diff')
        opened = sorted({path for mode in ('baseline', 'noop', 'mutant')
                         for path in record[mode].get('opened_files', [])})
        if baselined(case, dict(mutant, opened_files=opened), baseline):
            killed = [dict(row=item['row'], kill_by='unproven') for item in killed]
        record['kills'] = killed
        record['kill_by'] = ('unproven' if any(k['kill_by'] == 'unproven' for k in killed)
                             else killed[0]['kill_by'])
        return record
    except (KeyError, TypeError, ValueError) as error:
        raise Refused('driver_error', str(error)) from error


def validate_scope(record, case, store, *, baseline=None):
    M = load(ROOT / 'scripts/mutation_reuse.py')
    C = M.change_module()
    scope, selected = record['execution_scope'], record['selected_rows']
    C.require(scope in ('rows', 'suite'), 'execution scope')
    C.require(store is not None, 'authenticated controls required')
    controls = store.get(record['control_receipt_digest'])
    C.check_seal(controls, M.CONTROL_RECORD,
                 ('suite', 'cases', 'source_commit', 'dependency', 'baseline', 'noop'))
    M.authenticated_controls(store, record['control_receipt_digest'], controls['suite'], controls['cases'])
    C.require(case in controls['cases'] and record['baseline'] == controls['baseline'] and
              record['noop'] == controls['noop'], 'control references')
    C.require(record['observed_rows'] == record['mutant']['row_names'], 'observed rows')
    attempts = record['attempts']
    C.require(isinstance(attempts, list) and 1 <= len(attempts) <= 2 and
              attempts[-1] == dict(execution_scope=scope, selected_rows=selected,
                                   observation=record['mutant']), 'attempt evidence')
    if scope == 'rows':
        C.require(isinstance(selected, list) and selected and len(set(selected)) == len(selected) and
                  collections.Counter(selected) == collections.Counter(record['observed_rows']), 'selected row inventory')
        C.require(all(n.split()[-1] in case['rows'] for n in selected), 'selected target identity')
    else:
        C.require(selected == [], 'suite row selection')
    prior_key = record['prior_kill_receipt_digest']
    if scope == 'rows' or len(attempts) == 2:
        prior = C.referenced(store, prior_key, M.KILL_RECORD, ('source_commit', 'dependency', 'result'))
        C.validate_dependency(prior['dependency'])
        previous = prior['result']
        C.require(previous['case'] == case and prior['source_commit'] == prior['dependency']['observed_commit'],
                  'prior case source')
        # Its authenticated result must itself prove a kill, including passing controls.
        validate_result(previous, case, store=store, baseline=baseline)
        wanted = [k['row'] for k in previous['kills'] if k['kill_by'] in ('assertion', 'terminal', 'unproven')]
        C.require(wanted and attempts[0]['selected_rows'] == wanted, 'prior kill provenance')
        if len(attempts) == 2 and not attempts[0].get('unavailable'):
            first = observations(attempts[0]['observation'])
            C.require(collections.Counter(n for n, _ in first) == collections.Counter(wanted) and
                      all(ok is True for _, ok in first), 'fallback from incomplete attempt')
    else:
        C.require(prior_key is None, 'unexpected prior receipt')


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
    def __init__(self, deadline=None, resources=None, parallel=None, admission=None,
                 *, hang_seconds=PROCESS_HANG_SECONDS, clock=None):
        self.resources = resources
        self.admission = admission
        self.meters = {}
        self.deadline = None  # compatibility: no stage deadline
        self.hang_seconds = hang_seconds
        self.clock = clock or time.monotonic
        self.supplied_clock = clock is not None
        self.progress = {}
        self.positions = {}
        self.events = None
        self.parallel = (worker_count() if admission else min(16, PARALLEL)) if parallel is None else max(1, parallel)
        self.active = {}
        self.owned_snapshots = {}
        self.invocations = 0
        self.driver_spans = {}
        self.outcomes = []
        self.peak = 0
        self.peak_memory = 0
        self.jobs = {}
        self.homes = {}
        self.ledgers = {}
        # The authority's unconfined leg (gate_legs.mutation_leg) or None: every worker confined.
        self.leg = None
        self.legs = {}
        self.authority_dependencies = {}
        self.authority_runtimes = {}
        self.observation_context = {}
        self.budgets = {}

    boundary = None

    def launcher_fds(self):
        if self.boundary is None:
            self.boundary = load(ROOT / 'scripts/agent_sandbox.py')
        return self.boundary.launcher_fds()

    def check(self):
        # Admission estimates cannot expire a stage.
        pass

    def watch_worker(self, name):
        if self.events is None:
            self.events = load(ROOT / 'scripts/mutation_observer.py').Events()
        proc, out, err, started = self.active[name]
        lifecycle = getattr(self.meters.get(name), 'lifecycle', None)
        self.events.add(name, proc, (out, err), (lifecycle.fileno(),) if lifecycle is not None else ())

    def read_progress(self, name):
        _, out, err, _ = self.active[name]
        for stream in (out, err):
            key = (name, stream.fileno())
            offset = self.positions.get(key, 0)
            data = os.pread(stream.fileno(), os.fstat(stream.fileno()).st_size - offset, offset)
            self.positions[key] = offset + len(data)
            if b'\n' in data:
                self.progress[name] = (self.clock(), data.rsplit(b'\n', 2)[-2].decode(errors='replace')[-400:])

    def check_worker(self, name, started):
        last, event = self.progress.get(name, (started, 'worker started'))
        if self.clock() - last >= self.hang_seconds:
            mode = self.jobs.get(name, {}).get('mode')
            code = 'control_failed' if mode in ('baseline', 'noop') else 'hung_not_killed'
            raise Refused(code, name + ': hung since ' + event)

    def wait_for_progress(self):
        if self.active:
            remaining = min(max(0, self.hang_seconds - (self.clock() -
                self.progress.get(n, (started, 'started'))[0]))
                for n, (_, _, _, started) in self.active.items())
            self.events.wait(max(WAIT_HANG_SECONDS, remaining)
                             if self.supplied_clock and remaining else remaining)
        elif self.admission:
            raise Refused('admission_stalled', 'no active worker can release the requested resources')

    def retarget(self, name, seconds):
        """Refresh an admission estimate, including completed work, without rejudging it."""
        self.jobs[name]['budget_seconds'] = seconds
        if name in self.budgets:
            self.budgets[name] = seconds
        for outcome in self.outcomes:
            if outcome['name'] == name:
                outcome['estimate_seconds'] = seconds

    def release_snapshot(self, name):
        path = self.owned_snapshots.pop(name, None)
        if path is not None and path.exists():
            shutil.rmtree(path)

    def finish(self, name, error=None):
        proc, out, err, started = self.active[name]
        measurement = None
        if name in self.meters:
            try:
                measurement = self.meters[name].sample(self.homes[name], self.ledgers[name])
            except Exception as meter_error:
                error = Refused('worker_measurement_error', name + ': ' + str(meter_error))
        if error is not None and getattr(error, 'code', '') in ('hung_not_killed', 'control_failed'):
            # Python's fatal-signal handler writes every thread before it exits.
            try:
                os.killpg(proc.pid, signal.SIGABRT)
            except ProcessLookupError:
                pass
            proc.wait()
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        meter_path = getattr(self.meters.get(name), 'path', None)
        if meter_path is not None:
            (meter_path / 'cgroup.kill').write_text('1')
            load(ROOT / 'scripts/mutation_observer.py').wait_empty(meter_path)
        out.seek(0)
        err.seek(0)
        stdout, stderr = out.read(), err.read()
        out.close()
        err.close()
        elapsed = time.monotonic() - started
        job = self.jobs[name]
        home = self.homes[name]
        record = dict(name=name, driver=job['case']['driver'], mode=job['mode'],
                      leg=self.legs.get(name, 'confined'), estimate_seconds=self.budgets[name],
                      hang_seconds=self.hang_seconds,
                      elapsed=elapsed, returncode=proc.returncode, pid=proc.pid,
                      output_directory=str(home),
                      stdout_bytes=len(stdout), stderr_bytes=len(stderr))
        if measurement is not None:
            record['measurement'] = measurement
        result = None
        non_file, withheld = {}, set()
        stale = None
        if error is None and 'snapshot_root' in job:
            # Trace is outside the worker's writable home. Check before trusting output.
            tracer = load(ROOT / 'scripts/case_trace.py')
            try:
                trace = home.parent / ('trace-' + home.name)
                tracer.check(
                    trace, job['snapshot_root'], job['declared_files'],
                    job.get('declared_absent', []), runtime=job['runtime_paths'], scratch=home,
                    directories=job.get('declared_directories', []),
                    runtime_absent=job.get('runtime_absent', []), after_confinement=True)
                # VELDO-0217 AC4: a non-file input this run shows keeps its case from publishing.
                private = (home, job['snapshot_root'])
                non_file = tracer.non_file_inputs(trace, private, after_confinement=True)
                # An absent socket is an input too: a probe of one the key does not record as absent
                # would go unnoticed if that socket appeared later, so the case publishes nothing.
                undeclared = sorted(set(tracer.absent_sockets(trace, private, after_confinement=True))
                                    - set(job.get('runtime_absent', [])))
                if undeclared:
                    withheld.add('undeclared_absent_socket')
                    record['undeclared_absent_sockets'] = undeclared
            except tracer.UndeclaredInput as undeclared_input:
                stale = str(undeclared_input)
                # Never raises: an unavailable store leaves the finding unpersisted, not the stage red.
                self.case_reuse.mark_stale(job['case'], str(undeclared_input))
                record['declaration_stale'] = stale
            except tracer.IncompleteTrace as incomplete:
                # A thread ended inside a call (a case that SIGKILLs its own child): the confined
                # run's result stands as a fresh result, but its inputs are not proven, so it is
                # never published; the stage goes on (VELDO-0217 F6).
                withheld.add('incomplete_trace')
                record['trace_incomplete'] = str(incomplete)
            except ValueError as trace_error:
                error = trace_error
        if non_file:
            record['non_file_inputs'] = sorted(non_file)
        if error is None and stale is None:
            if proc.returncode:
                hung = b'SELFTEST HUNG' in stdout or b'SELFTEST HUNG' in stderr or b'Timeout (' in stderr
                code = ('worker_launch_error' if b'worker_launch_error:' in stderr else
                        'control_failed' if job['mode'] in ('baseline', 'noop') else
                        'hung_not_killed' if hung else 'driver_error')
                error = Refused(code,
                                name + ': worker exit ' + str(proc.returncode))
            else:
                try:
                    result = json.loads(stdout)
                    if not isinstance(result, dict):
                        raise ValueError('worker result must be an object')
                except ValueError:
                    error = Refused('driver_error', name + ': invalid or empty worker JSON')
        if error is None and result is not None:
            owner = load(ROOT / 'scripts/mutation_observer.py')
            claim = result.get('observation', {}).get('dependency')
            if claim is not None:
                try:
                    if claim['complete']:
                        raise ValueError('Python dependency claim asserts complete native coverage')
                    trace = home.parent / ('trace-' + home.name)
                    if trace.is_file():
                        reads = owner.DependencyReads(*self.observation_context[name], private_scratch=(home,))
                        reads.trace(trace, launched_argv=proc.args)
                        if claim['observed_commit'] == '0' * 40:
                            reads.unknown('observed commit unavailable')
                        native = reads.record(claim['item_id'], claim['observed_commit'])
                        self.authority_dependencies[claim['record_digest']] = native
                        self.authority_runtimes[native['runtime_digest']] = reads.runtime
                except (OSError, ValueError, KeyError, TypeError) as observation_error:
                    print('dependency observation not stored: %s' % observation_error, file=sys.stderr)
        if error is not None:
            record.update(error=getattr(error, 'code', 'driver_error'), detail=getattr(error, 'detail', str(error)),
                          stdout_tail=stdout.decode(errors='replace')[-2000:],
                          stderr_tail=stderr.decode(errors='replace')[-2000:])
        if error is not None and (getattr(error, 'code', '') == 'hung_not_killed'
                                  or b'Timeout (' in stderr or b'Fatal Python error' in stderr
                                  or b'SELFTEST HUNG' in stdout):
            record['stack_dump'] = stderr.decode(errors='replace')
        try:
            ownership = load(ROOT / 'scripts/mutation_ownership.py')
            # A metered worker's own directories outside its home are reaped by the rule its meter
            # admitted them under: born after the meter started (mutation_ownership.created_since).
            metered = getattr(self.meters.get(name), 'started', None)
            record['cleanup'] = ownership.cleanup(self.homes[name], self.ledgers[name],
                                                  **({'born_after': metered} if metered is not None else {}))
            # Materialized production trees are not ownership-ledger entries. Reap
            # this worker's scratch after reading its evidence, before admitting
            # another worker; retaining every copy until stage end fills the disk.
            # stdout, stderr, traces and the ledger live beside home and survive.
            ownership.remove_tree(home)
            # Keep the ownership receipt unchanged; scratch is coordinator-owned.
            record['scratch_removed'] = True
        except Exception as cleanup_error:
            error = Refused('worker_cleanup_error', name + ': ' + str(cleanup_error))
            record.update(error=error.code, detail=error.detail)
        finally:
            if name in self.meters:
                try:
                    self.meters[name].close()
                    del self.meters[name]
                except Exception as cleanup_error:
                    error = Refused('worker_cleanup_error', name + ': ' + str(cleanup_error))
                    record.update(error=error.code, detail=error.detail)
        record['elapsed'] = time.monotonic() - started
        self.outcomes.append(record)
        self.driver_spans[job['case']['driver']][1] = time.monotonic()
        del self.active[name]
        if self.events is not None:
            self.events.remove(name)
        self.progress.pop(name, None)
        self.positions = {key: value for key, value in self.positions.items() if key[0] != name}
        self.release_snapshot(name)
        if record.get('error') != 'worker_cleanup_error':
            self.resources.release(name)
            if self.admission:
                self.admission.release(name)
        if error is not None:
            raise error
        if stale is not None:
            return {'result': None, 'elapsed': elapsed, 'declaration_stale': stale}
        return {'result': result, 'elapsed': elapsed, 'non_file': sorted(non_file), 'withheld': sorted(withheld)}

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
        pending = sorted(jobs.items(), key=lambda item: -item[1].get('budget_seconds', 0))
        # Validate every job before launching any, including ones behind blocked jobs.
        for _name, job in pending:
            self.resources.demand(job)
            if self.admission:
                self.admission.validate(job)
        results = {}
        try:
            while pending or self.active:
                self.check()
                stale = getattr(getattr(self, 'case_reuse', None), 'stale', {})
                for name, job in [p for p in pending if p[1].get('declared_case')
                                  and p[1]['case']['identity'] in stale]:
                    # A sibling of a case found stale is not launched: without its snapshot it
                    # would run untraced, and the stale case's own rerun replaces its result.
                    pending.remove((name, job))
                    superseded = {'result': None, 'elapsed': 0.0, 'declaration_stale':
                                  'superseded: ' + stale[job['case']['identity']]['reason']}
                    results[name] = superseded
                    if on_result is not None:
                        on_result(name, superseded)
                while pending and len(self.active) < self.parallel:
                    index = self.resources.select(pending)
                    if index is None:
                        break
                    name, job = pending[index]
                    if self.admission and not self.admission.acquire(name, job, self.resources):
                        break
                    pending.pop(index)
                    self.budgets[name] = job.get('budget_seconds', WORKER_BUDGET)
                    home = directory / str(self.invocations)
                    home.mkdir()
                    self.homes[name] = home
                    bindir = home / 'bin'
                    bindir.mkdir()
                    (bindir / 'python3').symlink_to(sys.executable)
                    if job.get('declared_case'):
                        self.owned_snapshots[name] = directory / 'cases' / str(self.invocations)
                        job.update(self.case_reuse.prepare(job['case'], self.owned_snapshots[name]))
                    job['observed_commit'] = getattr(self, 'observed_commit', None)
                    jobpath = home / 'job.json'
                    jobpath.write_bytes(canonical(job))
                    out, err = (open(directory / (str(self.invocations) + '-' + f), 'w+b')
                                for f in ('stdout', 'stderr'))
                    self.resources.acquire(name, job)
                    # The ownership ledger is this coordinator's file, beside the home and outside
                    # every worker grant; the worker only inherits an append descriptor to it.
                    self.ledgers[name] = directory / ('ownership-' + str(self.invocations) + '.jsonl')
                    ledger = None
                    meter_fd = lifecycle_fd = None
                    try:
                        if self.admission and self.admission.meter_factory:
                            meter = self.admission.meter_factory(str(self.invocations))
                            self.meters[name] = meter
                            meter_fd = meter.open_join()
                            if (hasattr(meter, 'open_lifecycle')
                                    and self.resources.demand(job).get('systemd_user_manager', 0)):
                                lifecycle_fd = meter.open_lifecycle()
                        ledger = os.open(self.ledgers[name], os.O_WRONLY | os.O_CREAT | os.O_EXCL
                                         | os.O_APPEND | os.O_CLOEXEC, 0o600)
                        worker_root = Path(job.get('snapshot_root', root))
                        # A case of a suite the authority's list names runs in the unconfined leg,
                        # as its suite does in the unit stage (VELDO-0208, owner decision): the
                        # worker installs no boundary. It is never a declared case, so never traced.
                        leg = 'unconfined' if in_leg(self.leg, job['case'], selected_rows=job.get('selected_rows'),
                                                    row_legs=job.get('row_legs'), suite_leg=job.get('suite_leg')) else 'confined'
                        if leg == 'unconfined' and 'snapshot_root' in job:
                            raise Refused('driver_error', name + ': an unconfined case cannot be declared')
                        self.legs[name] = leg
                        # -I keeps user site and PYTHON* variables out. A fresh worker keeps the
                        # system site-packages its suites ran with before confinement: without it
                        # an optional oracle (PyYAML for 0119) stands down and its row passes a
                        # mutant. A declared case runs only its keyed runtime set, so it adds -S.
                        argv = [sys.executable, '-I', *(('-S',) if 'snapshot_root' in job else ()), '-B',
                                '-X', 'faulthandler', '-u', '-X', 'pycache_prefix=' + str(home / 'bytecode'),
                                str(ROOT / 'scripts/reuse_worker.py'),
                                'worker' if leg == 'confined' else 'unconfined',
                                str(worker_root), str(ledger), str(jobpath)]
                        tracer = load(ROOT / 'scripts/case_trace.py')
                        if 'snapshot_root' in job or (leg == 'unconfined' and Path('/usr/bin/strace').is_file()
                                and tracer.compatible(ROOT, [job['case']['suite']])):
                            argv = tracer.command(directory / ('trace-' + str(self.invocations)), argv)
                        # A worker reads its job from its file, never from the coordinator's
                        # stdin, which may be a socket the worker's boundary would refuse.
                        # Inside a tree the agent launcher made, a worker is handed its marker, so a
                        # fresh worker's own tree nests in it (VELDO-0210 AC6, AC7).
                        worker_env = fixed_env if 'snapshot_root' in job else fresh_env
                        environment = worker_env(home, str(bindir) + ':/usr/bin:/bin')
                        if (job['case'].get('confined_only') is True or job.get('suite_leg') or job.get('row_legs')) and self.leg:
                            # The whole worker stays confined; only the authority's existing
                            # row split omits census rows assigned to its other leg.
                            environment.update(VELDO_GATE_LEG=leg,
                                               VELDO_GATE_UNCONFINED=','.join(self.leg['entries']),
                                               VELDO_GATE_DECLARATION=self.leg['declaration'])
                        if meter_fd is not None:
                            environment['VELDO_MUTATION_CGROUP_FD'] = str(meter_fd)
                        if lifecycle_fd is not None:
                            environment['VELDO_MUTATION_LIFECYCLE_FD'] = str(lifecycle_fd)
                        self.observation_context[name] = (worker_root, environment)
                        proc = subprocess.Popen(argv, cwd=worker_root,
                                                env=environment,
                                                stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                                pass_fds=(ledger, *((meter_fd,) if meter_fd is not None else ()),
                                                          *((lifecycle_fd,) if lifecycle_fd is not None else ()), *self.launcher_fds()),
                                                start_new_session=True)
                        if lifecycle_fd is not None:
                            meter.launched()
                    except BaseException as error:
                        out.close()
                        err.close()
                        self.resources.release(name)
                        if name in self.meters:
                            self.meters.pop(name).close()
                        if self.admission:
                            self.admission.release(name)
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
                        if meter_fd is not None:
                            os.close(meter_fd)
                    self.active[name] = (proc, out, err, self.clock())
                    self.progress[name] = (self.clock(), 'worker started')
                    self.watch_worker(name)
                    self.invocations += 1
                    self.peak = max(self.peak, len(self.active))
                    self.driver_spans.setdefault(job['case']['driver'], [time.monotonic(), time.monotonic()])
                active_before_reap = len(self.active)
                for name, (proc, out, err, started) in list(self.active.items()):
                    if name in self.meters:
                        self.meters[name].sample(self.homes[name], self.ledgers[name])
                        self.peak_memory = max(self.peak_memory, sum(m.peak for m in self.meters.values()))
                    self.read_progress(name)
                    if proc.poll() is None:
                        try:
                            self.check_worker(name, started)
                        except Refused as error:
                            self.finish(name, error)
                        continue
                    results[name] = self.finish(name)
                    if on_result is not None:
                        on_result(name, results[name])
                # A completion released claims after the admission attempt above.
                # Retry pending work before deciding that nobody can free capacity.
                if pending and len(self.active) < active_before_reap:
                    continue
                if self.active or pending:
                    self.wait_for_progress()
            self.check()
            return results
        finally:
            try:
                self.cleanup(on_result)
                if self.events is not None:
                    self.events.close()
                    self.events = None
            finally:
                # The stage leaves this run only when done or aborting, so no ledger grant outlives
                # it: a failed mkdir or job materialization, a cancelled worker and one whose cleanup
                # failed (its outcome keeps the error; its local resources stay held) all release.
                if self.admission:
                    for name in list(self.admission.held):
                        self.admission.release(name)


def worker(job, keep=()):
    # The same confinement as a coordinator's worker (reuse_worker.py): the gate profile's domain
    # and network rule. Only the confined child returns; the parent exits with its status. The
    # repository's Git common directory stays readable, as it is when it lies inside ROOT, so a
    # linked worktree's suites find their repository as the main checkout's do.
    load(ROOT / 'scripts/mutation_sandbox.py').confine(ROOT, ROOT, Path(os.environ['TMPDIR']),
                                                       job.get('runtime_paths'), keep=keep,
                                                       reads=(common_directory(ROOT),))
    case = job['case']
    driver = load(ROOT / 'scripts' / case['driver'])
    owner = load(ROOT / 'scripts/check_teeth_mutations.py')
    prepared = owner.materialize(case, job['mode'], Path(os.environ['TMPDIR']), root=ROOT)
    mutant = prepared['mutant']
    argument = case if case['driver'] == DRIVERS[0] else case['name']
    return dict(observation=driver.worker(argument, str(mutant) if mutant else None),
                **{key: prepared[key] for key in ('replacement_count', 'old_digest', 'new_digest')})


# Without explicit confinement, a case of a rows-scoped suite is refused: the stage RED.
ROWS_SCOPED_CASE = 'rows_scoped_unconfined_case'


def in_leg(leg, case, *, selected_rows=None, row_legs=None, suite_leg=None):
    """Keep the authority's suite/row grant and an explicit confinement narrowing.

    Scoped jobs install the declared leg's row split in Workers. Legacy jobs
    cannot broaden a row grant into whole-suite unconfined execution.
    """
    if suite_leg not in (None, 'confined', 'unconfined'):
        raise Refused('invalid_suite_leg', str(suite_leg))
    if case.get('confined_only') is True or suite_leg == 'confined':
        return False
    suite = case['suite']
    if leg is None or not suite.endswith('.py') or suite[:-3] not in leg['suites']:
        if suite_leg == 'unconfined':
            raise Refused('invalid_suite_leg', 'suite is not in the authority unconfined list')
        return False
    if suite[:-3] in {e.split(':', 1)[0] for e in leg['entries'] if ':' in e}:
        if selected_rows is not None and row_legs is not None:
            assignments = {row_legs.get(row) for row in selected_rows}
            if assignments == {'confined'}:
                return False
            if assignments == {'unconfined'}:
                return True
        elif suite_leg == 'unconfined':
            return True  # Workers installs the authority's row split in its environment.
        raise Refused(ROWS_SCOPED_CASE, '%s is a case of %s, which the unconfined list names only for '
                      'some rows, and a case runs its whole suite; refusing rather than running every '
                      'row of it unconfined' % (case.get('identity') or case.get('name'), suite[:-3]))
    return True


def control_group(case, configuration=None):
    if configuration is not None:
        return digest(load(ROOT / 'scripts/mutation_reuse.py').suite_identity(case, configuration))
    # A deliberately confined case cannot borrow a whole-suite unconfined control.
    return (case['suite'] + ':' + case['module'] + ':' + str(case.get('fixture') is True)
            + (':confined' if case.get('confined_only') is True else ''))


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




def publish_case_dependencies(root, head, cases, results, workers, *, store=None):
    """Publish observations only after the authority has reaped worker allocations."""
    if workers.active or workers.meters or workers.owned_snapshots:
        raise Refused('worker_cleanup_error', 'dependency publication before cleanup')
    if any(outcome.get('error') == 'worker_cleanup_error' for outcome in workers.outcomes):
        raise Refused('worker_cleanup_error', 'dependency publication after failed cleanup')
    owner = load(ROOT / 'scripts/mutation_observer.py')
    changes = owner.dependency_module('gate_changes')
    store = store or load(ROOT / 'scripts/gate_reuse.py')._suite_store(root, os.environ)
    if store is None:
        print('dependency observation not stored: dependency Store unavailable', file=sys.stderr)
        return
    for case in cases:
        record = results[case['identity']]
        leg = 'unconfined' if in_leg(workers.leg, case) else 'confined'
        item = changes['identity']('case', 'mutation', leg, case['suite'], case['driver'], case['name'])
        dependencies = []
        for mode in ('baseline', 'noop', 'mutant'):
            dependency = record[mode].get('dependency')
            if dependency is None:
                missing = owner.DependencyReads(root)
                missing.unknown('missing ' + mode + ' observation')
                dependency = missing.record(item, head)
            if dependency['complete']:
                raise ValueError('Python dependency claim asserts complete native coverage')
            native = getattr(workers, 'authority_dependencies', {}).get(dependency['record_digest'])
            dependency = owner.native_dependency(native, dependency)
            dependencies.append(dependency)
        dependency = owner.combine_dependencies(dependencies, item, head)
        try:
            owner.publish_dependencies(store, dependency, record)
        except OSError as observation_error:
            print('dependency observation not stored: %s' % observation_error, file=sys.stderr)


def run_stage(root, expected_common, capacities=None, findings=None, names=None, log_dir=None,
              drivers=None, parallel=None, diff_dir=None, force_fresh=False, leg=None, measure=False,
              admission=None, admit=False, change_context=None):
    """expected_common is the trusted Git common directory of root, named by the caller that owns
    root: the authority's own for the gate, a fixture's own for the fixture's creator. leg is the
    authority's unconfined leg (gate_legs.mutation_leg), None for every case confined. Only
    the authority CLI sets measure=True; library/fixture drives do not write owner timings."""
    if change_context is not None:
        if findings or names or drivers or force_fresh:
            raise Refused('invalid_change_scope', 'diagnostic selectors cannot supply a complete change plan')
        return run_change_stage(root, expected_common, change_context, capacities=capacities,
                                parallel=parallel, leg=leg, admission=admission, admit=admit)
    started = time.monotonic()
    workers = Workers(None, parallel=parallel, admission=admission)
    workers.leg = leg
    receipt = {'schema': 'veldo.mutation-stage/v1', 'results': [],
               'registered': 0, 'executed': 0, 'reused': 0,
               'rejected': 0, 'drivers': {}, 'surviving_workers': 0, 'invalid_results': []}
    cases, reuse = [], None
    audits, audit_keys = {}, {}
    audit_module = AUDIT or _load_audit(ROOT / 'scripts/mutation_reuse.py')
    receipt['audit'] = dict(population=[], entries=[], audited=0, matched=0, mismatched=0,
                            worker_seconds=0.0, suites={})
    try:
        if admit:
            admission = workers.admission = Admission.authority()
            if parallel is None:
                workers.parallel = worker_count()
        full_inventory = inventory(root, expected_common)
        cases = [c for c in full_inventory if (not findings or c['finding'] in findings)
                 and (not drivers or c['driver'] in drivers)
                 and (not names or c['name'] in names)]
        if not cases or (names and set(names) - {c['name'] for c in cases}):
            raise Refused('incomplete_inventory', 'empty or unknown subset')
        receipt['scope'] = 'selected' if findings or names or drivers else 'full'
        receipt['registered'] = len(cases)
        budget = budget_for(len(full_inventory), workers.parallel)
        receipt['estimate_seconds'] = budget
        for driver in DRIVERS:
            own = [c for c in cases if c['driver'] == driver]
            receipt['drivers'][driver] = {'inventory_digest': digest(own), 'registered': len(own),
                                           'worker_seconds': 0.0, 'executed': 0, 'reused': 0}
        files = read_inputs(root, expected_common)
        time_keys = {c['identity']: case_time_key(c, files, leg) for c in cases}
        deadlines = case_deadlines(time_keys)
        unmeasured = {identity for identity, seconds in deadlines.items() if seconds is None}
        # Updated in place once this stage measures an unmeasured case's baseline.
        receipt['case_estimates'] = deadlines
        receipt['unmeasured_cases'] = sorted(unmeasured)
        # An unmeasured case starts with the conservative legacy admission estimate.
        # Its baseline subsequently refreshes that estimate; it never sets a deadline.
        planned = {identity: WORKER_CEILING if seconds is None else seconds
                   for identity, seconds in deadlines.items()}
        claims = None
        if admission:
            store = CaseClaims()
            claims = {c['identity']: store.claim(c, time_keys[c['identity']]) for c in cases}
            receipt['case_claims'] = claims
            receipt['mutation_floor'] = admission.floor
        head = git(root, expected_common, 'rev-parse', 'HEAD')
        workers.observed_commit = load(ROOT / 'scripts/mutation_observer.py').clean_commit(root)
        receipt['input_digest'] = digest({'files': file_identity(files), 'head': head})
        receipt['implementation_digest'] = hashlib.sha256(
            files['scripts/check_gate_mutations.py'][1]).hexdigest()
        reuse_module = load(ROOT / 'scripts/case_reuse.py')
        reuse = reuse_module.Session(root, files, cases, head,
            {'fixture_version': FIXTURE_VERSION, 'capacities': capacities,
             'worker_environment': fixed_env('<private-worker-home>')}, force_fresh=force_fresh)
        receipt['force_fresh'] = reuse.forced
        # An unconfined case is neither traced nor confined, so nothing bounds what it read: it is
        # never reuse-qualified, runs fresh every time, and is never published.
        outside = [c for c in cases if in_leg(leg, c)]
        for case in outside:
            reuse.keys[case['identity']] = None
            reuse.reasons[case['identity']] = 'unconfined_leg'
            getattr(reuse, 'snapshots', {}).pop(case['identity'], None)
        if leg is not None:
            receipt['unconfined'] = {'declaration': leg['declaration'], 'entries': leg['entries'],
                                     'cases': sorted(c['identity'] for c in outside),
                                     'suites': dict(collections.Counter(c['suite'][:-3] for c in outside))}
        receipt['reuse_qualified'] = sum(key is not None for key in reuse.keys.values())
        results = {}
        fresh = []
        for case in cases:
            record = reuse.lookup(case, validate_result)
            if record is None:
                fresh.append(case)
            else:
                results[case['identity']] = record
        # All lookups finish before the authority draws fresh entropy.
        selected = audit_module.audit_sample(results)
        audit = receipt['audit']
        audit['population'] = [dict(identity=identity, key=reuse.keys[identity],
                                    suite=record['case']['suite'], rate=audit_module.R.E.audit_rate(record))
                               for identity, record in results.items()]
        for case in cases:
            identity = case['identity']
            if identity in selected:
                audits[identity] = results.pop(identity)
                audit_keys[identity] = reuse.keys[identity]
                reuse.hits.pop(identity, None)
                fresh.append(case)
            elif identity in results:
                receipt['results'].append(reuse.evidence(case, results[identity], True))
        for member in audit['population']:
            suite = audit['suites'].setdefault(member['suite'], dict(hits=0, reused=0, audited=0))
            suite['hits'] += 1
            suite['reused'] += member['identity'] not in selected
            suite['audited'] += member['identity'] in selected
        for suite_name, suite in audit['suites'].items():
            strata = {}
            for member in audit['population']:
                if member['suite'] == suite_name:
                    counts = strata.setdefault(member['rate'], [0, 0])
                    counts[0] += 1
                    counts[1] += member['identity'] in selected
            minimum = min(chosen / total for total, chosen in strata.values())
            suite['minimum_inclusion_probability'] = minimum
            fraction = suite['audited'] / suite['hits']
            suite['sample_fraction'] = fraction
            suite['detection_probability'] = {str(k): 1 - (1 - minimum) ** k for k in (1, 20, 60)}
        minimum = min((s['minimum_inclusion_probability'] for s in audit['suites'].values()), default=0)
        audit['minimum_inclusion_probability'] = minimum
        audit['detection_probability'] = {str(k): 1 - (1 - minimum) ** k for k in (1, 20, 60)}
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
                return case['identity'] if (prepared_cases.get(case['identity'])
                                            or case['identity'] in audits
                                            or case['identity'] in getattr(reuse, 'stale', {})) else control_group(case)
            controls = control_jobs(fresh, group_for, prepared_cases, planned, claims)
            mutant_jobs = {c['identity']: {'case': c, 'mode': 'mutant',
                           'budget_seconds': planned[c['identity']],
                           **({'claim': claims[c['identity']]} if claims is not None else {}),
                           **prepared_cases.get(c['identity'], {})} for c in fresh}
            workers.resources = SuiteResources.from_root(frozen, capacities)
            budget = budget_for(len(full_inventory), workers.parallel,
                                [controls.values(), mutant_jobs.values()], workers.resources,
                                floor=admission.floor if admission else None)
            receipt['estimate_seconds'] = budget
            if admission:
                receipt['guaranteed_workers'] = guaranteed_workers(
                    [*controls.values(), *mutant_jobs.values()], admission.floor, workers.parallel)
            if log_dir is not None:
                log_dir = Path(log_dir).resolve()
                log_dir.mkdir(parents=True, exist_ok=False)
                directory = log_dir
            members = collections.defaultdict(list)
            for case in fresh:
                members[group_for(case)].append(case)

            def measured_baseline(name, completed):
                # Refresh the admission estimate from this stage's baseline. A shared
                # control represents its largest member; completed work is never rejudged.
                group, _, mode = name.rpartition(':')
                own = [c for c in members[group] if c['identity'] in unmeasured]
                if mode != 'baseline' or not own or completed.get('declaration_stale'):
                    return
                seconds = scaled_deadline(completed['elapsed'])
                for case in own:
                    deadlines[case['identity']] = seconds
                    mutant_jobs[case['identity']]['budget_seconds'] = seconds
                workers.retarget(group + ':noop', max(deadlines[c['identity']] for c in members[group]))

            control_results = workers.run(controls, directory, frozen, on_result=measured_baseline)
            rerun = {job['case']['identity'] for name, job in controls.items()
                     if control_results[name].get('declaration_stale')}
            for identity in rerun:
                mutant_jobs.pop(identity, None)
            if unmeasured.intersection(c['identity'] for c in fresh):
                # Refresh the remaining-work estimate, for reporting only.
                budget = min(budget, time.monotonic() - started + budget_for(
                    len(full_inventory), workers.parallel, [mutant_jobs.values()], workers.resources,
                    floor=admission.floor if admission else None))
                receipt['estimate_seconds'] = budget
            by_identity = {c['identity']: c for c in fresh}

            def collect(identity, completed):
                # Each mutant is judged as its worker completes, so a later failure or
                # timeout cannot discard results that were already produced.
                case = by_identity[identity]
                group = group_for(case)
                if completed.get('declaration_stale'):
                    rerun.add(identity)
                    return
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
                    if identity in audits:
                        differences = audit_module.R.E.audit_differences(audits[identity], record, case)
                        mismatch = any(d['verdict'] for d in differences.values())
                        entry = dict(identity=identity, key=audit_keys[identity],
                                     result_digest=reuse.authenticated_digests[identity],
                                     fresh_record=record, fresh_digest=audit_module.R.E.digest(record),
                                     differences=differences, matched=not mismatch)
                        receipt['audit']['entries'].append(entry)
                        print('   reuse audit: %s %s fields=%s' %
                              (identity, 'reuse_audit_mismatch' if mismatch else 'matched',
                               ','.join(differences) or 'none'), flush=True)
                        if mismatch:
                            reuse.store.invalidate(audit_keys[identity])
                            reuse.mark_stale(case, 'reuse_audit_mismatch: ' + ','.join(differences))
                        # An invalid fresh run retains its own failure classification.
                        try:
                            validate_result(record, case)
                        finally:
                            # Validation attaches verdict-bearing kill metadata. Bind the final
                            # fresh record, including on a refused control, before signing it.
                            entry['fresh_digest'] = audit_module.R.E.digest(record)
                        if mismatch:
                            raise Refused('reuse_audit_mismatch', identity + ': ' + ','.join(differences))
                    else:
                        validate_result(record, case)
                except (Refused, KeyError, TypeError) as error:
                    receipt['invalid_results'].append(dict(case=case, error=getattr(error, 'code', 'driver_error'),
                                                           detail=str(error)))
                    return
                # VELDO-0217 AC4: the baseline, no-op and mutant traces of a run that would publish
                # are checked again; a non-file input in any of them keeps the case fresh, unpublished,
                # and so do an undeclared absent socket and an incomplete trace.
                runs = [completed, *(control_results[group + ':' + mode] for mode in ('baseline', 'noop'))]
                shown = sorted(set().union(*(run.get('non_file', ()) for run in runs)))
                shown += sorted(set().union(*(run.get('withheld', ()) for run in runs)))
                if shown and hasattr(reuse, 'withhold'):
                    reuse.withhold(case, shown[0])
                results[identity] = record
                receipt['results'].append(dict(reuse.evidence(case, record, False),
                                               elapsed=completed['elapsed'],
                                               **(dict(audited=True, reuse_key=audit_keys[identity])
                                                  if identity in audits else {})))

            workers.run(mutant_jobs, directory, frozen, on_result=collect)
            if rerun:
                # Every stale attempt loses all three observations. Its own controls and mutant
                # run in the full frozen input tree, with ordinary fresh worker confinement.
                again = [c for c in fresh if c['identity'] in rerun]
                rerun_controls = control_jobs(again, group_for, {}, planned, claims)
                rerun_mutants = {c['identity']: {'case': c, 'mode': 'mutant',
                    'budget_seconds': planned[c['identity']],
                    **({'claim': claims[c['identity']]} if claims is not None else {})} for c in again}
                # A stale snapshot is not a timing sample for its full-tree replacement.
                budget = max(budget, time.monotonic() - started + budget_for(
                    len(again), workers.parallel, [rerun_controls.values(), rerun_mutants.values()],
                    workers.resources, floor=admission.floor if admission else None))
                receipt['estimate_seconds'] = budget
                control_results.update(workers.run(rerun_controls, directory, frozen))
                workers.run(rerun_mutants, directory, frozen, on_result=collect)
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
        if fresh:
            try:
                publish_case_dependencies(root, head, fresh, results, workers)
            except (OSError, ValueError, KeyError, TypeError) as observation_error:
                print('dependency observation not stored: %s' % observation_error, file=sys.stderr)
        for case in fresh:
            reuse.publish(case, results[case['identity']], validate_result)
        if reuse.store and reuse.store.integrity_errors:
            raise Refused('reuse_integrity_conflict', 'conflicting cache record: ' +
                          ', '.join(reuse.store.integrity_errors))
        workers.check()
        # Timed by the coordinator, never taken from worker JSON. No failed stage or reused
        # case refreshes a sample; controls shared by several cases contribute to each one.
        elapsed = {o['name']: o['elapsed'] for o in workers.outcomes}
        samples = {time_keys[c['identity']]: max(elapsed[c['identity']],
                   elapsed[group_for(c) + ':baseline'], elapsed[group_for(c) + ':noop'])
                   for c in fresh}
        record_case_times(root, samples, authority=measure)
        if admission:
            record_case_resources(fresh, time_keys, workers.outcomes, group_for, authority=measure)
        receipt['status'] = 'passed'
    except Exception as error:  # All incomplete drives are named errors, never detections.
        receipt['status'] = 'failed'
        receipt['error'] = getattr(error, 'code',
                                   'hung' if isinstance(error, subprocess.TimeoutExpired)
                                   else 'driver_error')
        receipt['detail'] = str(error)
    finally:
        workers.cleanup()
        receipt['declaration_stale'] = list(getattr(reuse, 'stale', {}).values())
        receipt['stale_count'] = len(receipt['declaration_stale'])
        receipt['gate_run'] = getattr(reuse, 'gate_run', None)
        receipt['stale_unpersisted'] = sum(1 for e in receipt['declaration_stale'] if not e.get('persisted'))
        receipt['reuse_unavailable'] = dict(getattr(reuse, 'unavailable', {}))
        try:
            receipt['authority_stale_count'] = (len(reuse_module.M.stale_entries(reuse.store.directory))
                if hasattr(reuse, 'stale') and reuse.store and reuse.store.secret is not None else 0)
        except OSError:
            receipt['authority_stale_count'] = None
        audit = receipt['audit']
        audit['audited'] = len(audit['entries'])
        audit['matched'] = sum(e['matched'] for e in audit['entries'])
        audit['mismatched'] = audit['audited'] - audit['matched']
        audit_names = {name for identity in audits for name in
                       (identity, identity + ':baseline', identity + ':noop')}
        audit['worker_seconds'] = sum(o['elapsed'] for o in workers.outcomes if o['name'] in audit_names)
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
                'validated': identity in completed,
                **(dict(audited=True, reuse_key=audit_keys[identity]) if identity in audits else {}),
                **({k: results[identity][k] for k in ('kill_by', 'kills')} if identity in completed else {})})
        for driver, summary in receipt['drivers'].items():
            span = workers.driver_spans.get(driver, (0, 0))
            summary['wall_seconds'] = span[1] - span[0]
            summary['worker_seconds'] = sum(o['elapsed'] for o in workers.outcomes if o['driver'] == driver)
        if workers.resources is not None:
            receipt['resources'] = workers.resources.summary()
        receipt['reuse_integrity_errors'] = (list(reuse.store.integrity_errors)
                                             if reuse is not None and reuse.store else [])
        if admission:
            receipt['admissions'] = admission.events
            receipt['peak_granted'] = admission.peak
            receipt['ledger_capacities'] = admission.capacity
            receipt['peak_anon_bytes'] = workers.peak_memory
            receipt['mean_busy_cores'] = sum(o.get('measurement', {}).get('cpu_seconds', 0)
                for o in workers.outcomes) / max(.000001, time.monotonic() - started)
            admission.close()
        receipt['peak_workers'] = workers.peak
        receipt['surviving_workers'] = len(workers.active)
        receipt['parallel_workers'] = workers.parallel
        receipt['worker_invocations'] = workers.invocations
        receipt['elapsed'] = time.monotonic() - started
    return receipt


def print_leg(leg, receipt, path):
    """Name the leg on the stage lines as gate_legs.py does for the unit stage: the list, its
    digest, and what ran unconfined."""
    ran = receipt.get('unconfined', {})
    outside = set(ran.get('cases', []))
    rejected = sum(r['case']['identity'] in outside for r in receipt.get('results', []))
    print('   mutation: confined leg - every case except those of the %d suite%s the list names (a case '
          'runs its whole suite; confined_only cases retain confinement, other rows-scoped cases are refused)'
          % (len(leg['suites']), '' if len(leg['suites']) == 1 else 's'), flush=True)
    print('   mutation: UNCONFINED LEG - runs outside the confinement by owner decision (VELDO-0208, %s %s), '
          '%d entr%s: %s' % (os.path.basename(str(path)), leg['declaration'], len(leg['entries']),
                              'y' if len(leg['entries']) == 1 else 'ies', ', '.join(leg['entries'])), flush=True)
    print('   mutation: unconfined leg ran %d case%s, %d rejected: %s'
          % (len(outside), '' if len(outside) == 1 else 's', rejected,
             ', '.join('%s (%d)' % item for item in sorted(ran.get('suites', {}).items())) or 'none'),
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', type=Path)
    parser.add_argument('--change-run')
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--resource-capacity', action='append', default=[], metavar='NAME=N')
    parser.add_argument('--finding', type=int, action='append')
    parser.add_argument('--case', action='append', dest='names')
    parser.add_argument('--worker-log-dir', type=Path)
    parser.add_argument('--legs-record', type=Path, help="verify.sh's record of the gate's unconfined legs")
    args = parser.parse_args()
    if args.change_run:
        return load(ROOT / 'scripts/gate_execution.py').node(
            args.change_run, 'mutation', args.root, args.directory)
    if args.worker:
        # Developer entry only: no coordinator launches it, so it keeps no ownership ledger.
        # Gate workers start from reuse_worker.py, which reports to the coordinator's ledger.
        print(json.dumps(worker(json.loads(args.worker.read_text()))))
        return 0
    # THE UNCONFINED LEG (VELDO-0208, owner decision Telegram 32403-32407, 2026-10-07): the cases of
    # the suites the authority's scripts/gate_unconfined.json names run without the worker
    # confinement when the list declares this stage. The list is read beside this file, never from
    # --root; a caller's leg variables decide nothing (no worker environment carries them). An
    # invalid list runs nothing.
    legs = load(ROOT / 'scripts/gate_legs.py')
    try:
        leg = legs.mutation_leg()
    except legs.Invalid as error:
        print('   mutation: the unconfined list %s is invalid (%s); nothing ran, in either leg'
              % (legs.DECLARATION, error), flush=True)
        return 1
    # The gate names the authority checkout's own common directory; a candidate root is a linked
    # worktree of it, and its marker is checked against that directory before any Git runs.
    receipt = run_stage(args.root, common_directory(ROOT), capacities=resource_capacities(args.resource_capacity),
                        findings=args.finding, names=args.names,
                        admit=load(ROOT / 'scripts/gate_schedule.py').CHANNEL in os.environ,
                        log_dir=args.worker_log_dir, leg=leg, measure=True)
    if os.environ.get('VELDO_GATE_GRAPH_DIGEST'):
        receipt['graph'] = os.environ['VELDO_GATE_GRAPH_DIGEST']
    if args.receipt:
        args.receipt.write_bytes(canonical(receipt))
    print(json.dumps(receipt, sort_keys=True), flush=True)
    if leg is not None:
        print_leg(leg, receipt, legs.DECLARATION)
        if args.legs_record:
            legs.write_record(args.legs_record, 'mutation', leg['declaration'], leg['entries'])
    print('mutations: {status} registered={registered} executed={executed} '
          'reused={reused} rejected={rejected} workers={worker_invocations} elapsed={elapsed:.3f}s'.format(**receipt), flush=True)
    return 0 if receipt['status'] == 'passed' else 1




def run_selected_cases(workers, cases, directory, frozen, *, store, commit, changed,
                       configurations, registered_cases, prior_kills=None, prior_controls=None, claims=None, verify_runtime=False):
    """Increment 3 coordinator seam. Increment 5 supplies the authenticated selection.

    Uses the existing confined workers, reservations and cleanup, with controls
    completed and validated before any case of their suite starts.
    """
    M = load(ROOT / 'scripts/mutation_reuse.py')
    C = M.change_module()
    C.require(C.SELECTION_ENABLED, 'change selection is inactive until increment 5')
    O = load(ROOT / 'scripts/mutation_observer.py')
    prior_kills, prior_controls = prior_kills or {}, prior_controls or {}
    requested = {c['identity'] for c in cases}
    C.require(requested <= {c['identity'] for c in registered_cases}, 'selected case inventory')
    groups = {}
    for case in registered_cases:
        suite = M.suite_identity(case, configurations[case['identity']])
        groups.setdefault(C.digest(suite), (suite, []))[1].append(case)
    controls = M.SuiteControls(store, changed, commit, runtime_validator=(
        lambda key: C.runtime_current(store, key, fixed_env('/nonexistent'), ROOT)) if verify_runtime else None)
    results = {}
    for group, (suite, members) in groups.items():
        if not any(c['identity'] in requested for c in members):
            continue
        def execute_controls(members):
            jobs = control_jobs(members, lambda case: group, {},
                                {case['identity']: WORKER_BUDGET for case in members}, claims)
            for job in jobs.values():
                job['suite_leg'] = suite['leg']
            observations = workers.run(jobs, directory, frozen)
            baseline, noop = (observations[group + ':' + mode]['result']['observation']
                              for mode in ('baseline', 'noop'))
            for observation in (baseline, noop):
                claim = observation['dependency']
                observation['dependency'] = O.native_dependency(
                    getattr(workers, 'authority_dependencies', {}).get(claim['record_digest']), claim)
            # Controls also read each target's original bytes and validate its anchor,
            # even when the representative worker targets another module.
            for member in members:
                base = frozen / ('scripts/fixtures' if member.get('fixture') else member.get('dir', '.veldo'))
                source = (base / member['module']).read_bytes()
                C.require(source.count(member['old'].encode()) == 1, 'control target wiring')
                O.mutate(source, member)
                if not member.get('fixture'):
                    suite_source = (frozen / 'scripts/suites' / member['suite']).read_text()
                    anchor = 'ROOT / "' + member.get('dir', '.veldo') + '" / "' + member['module'] + '"'
                    C.require(anchor in suite_source, 'control suite production-copy wiring')
            dependency = O.combine_dependencies([baseline['dependency'], noop['dependency']], group, commit)
            dependency = C.sealed(C.DEPENDENCY, **{k: v for k, v in dependency.items()
                if k not in ('schema', 'record_digest', 'paths')},
                paths=sorted(set(dependency['paths']) | {
                    ('scripts/fixtures' if c.get('fixture') else c.get('dir', '.veldo')) + '/' + c['module']
                    for c in members}))
            runtime_keys = sorted({baseline['dependency']['runtime_digest'], noop['dependency']['runtime_digest']})
            if len(runtime_keys) > 1:
                C.publish_runtime(store, runtime_keys)
            return baseline, noop, dependency

        shared = controls.get(suite, members, execute_controls, prior_controls.get(group))
        for case in members:
            if case['identity'] not in requested:
                continue
            def execute(selected):
                if selected is not None:
                    try:
                        C.row_source((frozen / 'scripts/suites' / case['suite']).read_text(), selected)
                    except ValueError:
                        return None
                job = dict(case=case, mode='mutant', budget_seconds=WORKER_BUDGET, suite_leg=suite['leg'])
                if claims is not None:
                    job['claim'] = claims[case['identity']]
                if selected is not None:
                    job['selected_rows'] = selected
                completed = workers.run({case['identity']: job}, directory, frozen)[case['identity']]['result']
                claim = completed['observation']['dependency']
                completed['observation']['dependency'] = O.native_dependency(
                    getattr(workers, 'authority_dependencies', {}).get(claim['record_digest']), claim)
                return dict(case=case, fixture_version=FIXTURE_VERSION, input_digest=C.digest(case),
                            mutant=completed['observation'],
                            **{k: completed[k] for k in ('replacement_count', 'old_digest', 'new_digest')})

            result = M.selected_mutation(case, shared, execute,
                lambda record, definition: validate_result(record, definition, store=store),
                store=store, prior=prior_kills.get(case['identity']))
            previous = store.get(prior_kills[case['identity']]) if case['identity'] in prior_kills else None
            control_dependency = C.sealed(C.DEPENDENCY, **dict(
                {k: v for k, v in shared['dependency'].items() if k not in ('schema', 'record_digest')},
                observed_commit=commit))
            dependencies = [control_dependency, *(a['observation']['dependency']
                            for a in result['attempts'] if 'observation' in a)]
            dependency = O.combine_dependencies(dependencies, C.identity('case', 'mutation', suite['leg'],
                case['suite'], case['driver'], case['name']), commit,
                prior=previous['dependency'] if previous else None, rows=result['execution_scope'] == 'rows')
            C.require(not workers.active and not workers.meters and not workers.owned_snapshots,
                      'publication before cleanup')
            envelope = C.sealed(M.KILL_RECORD, source_commit=commit, dependency=dependency, result=result)
            for runtime in getattr(workers, 'authority_runtimes', {}).values():
                C.publish_runtime(store, runtime)
            runtime_keys = sorted({d['runtime_digest'] for d in dependencies})
            if len(runtime_keys) > 1:
                C.publish_runtime(store, runtime_keys)
            C.require(store.change_put(dependency) and store.change_put(envelope), 'kill publication')
            result_record = C.sealed(C.RESULT_V2, item_id=dependency['item_id'], source_commit=commit,
                status='passed', complete=True, dependency_record_digest=dependency['record_digest'],
                execution_record_digest=envelope['record_digest'])
            C.require(store.change_put(result_record), 'mutation result publication')
            results[case['identity']] = dict(item_id=dependency['item_id'], status='executed',
                dependency_record_digest=dependency['record_digest'], result_digest=result_record['record_digest'],
                source_commit=commit, source_gate_digest=None)
    return results


def run_change_stage(root, expected_common, context, *, capacities=None, parallel=None, leg=None,
                     admission=None, admit=False):
    """Authority-only mutation child of the common plan; no CLI enables it yet."""
    reuse = load(ROOT / 'scripts/case_reuse.py')
    C, store = reuse.M.change_module(), context['store']
    C.require(C.SELECTION_ENABLED, 'change selection is inactive until increment 5')
    if 'plan' in context:
        plan = context['plan']
    else:
        plan = reuse.Session.for_changes(root, store, context['repository'],
            context['candidate_commit'], context['inventory'], context['runtimes']).plan
    cases = inventory(root, expected_common)
    configurations = context['configurations']
    C.require(set(configurations) == {c['identity'] for c in cases}, 'case configuration inventory')
    selected = {i['item_id']: i for i in plan['items']}
    identities = {c['identity']: C.identity('case', 'mutation',
        reuse.M.suite_identity(c, configurations[c['identity']])['leg'], c['suite'], c['driver'], c['name']) for c in cases}
    C.require(set(identities.values()) <= set(selected), 'mutation selection inventory')
    fresh = [c for c in cases if selected[identities[c['identity']]]['status'] == 'run']
    carried = [selected[identities[c['identity']]]['evidence'] for c in cases if c not in fresh]
    C.require(all(item and item['status'] == 'carried' for item in carried), 'mutation carry inventory')
    files = read_inputs(root, expected_common)
    head = git(root, expected_common, 'rev-parse', 'HEAD')
    C.require(head == context['candidate_commit'], 'candidate changed')
    workers = Workers(None, parallel=parallel, admission=admission)
    workers.leg = leg
    try:
        if admit:
            workers.admission = Admission.authority()
            if parallel is None:
                workers.parallel = worker_count()
        claims = ({c['identity']: CaseClaims().claim(c, C.digest([c, configurations[c['identity']]]))
                   for c in cases} if workers.admission else None)
        prior_kills, prior_controls = {}, {}
        if not context.get('full') and plan['baseline_record_digest'] is not None:
            baseline = C.historical_gate(store, plan['baseline_record_digest'], context['repository'])
            old = {i['item_id']: i for i in baseline['receipt']['items']}
            for case in cases:
                try:
                    previous = store.get(old[identities[case['identity']]]['result_digest'])
                    kill = store.get(previous['execution_record_digest'])
                    C.require(kill['result']['case'] == case, 'prior case definition')
                    prior_kills[case['identity']] = previous['execution_record_digest']
                    group = C.digest(reuse.M.suite_identity(case, configurations[case['identity']]))
                    prior_controls[group] = kill['result']['control_receipt_digest']
                except (KeyError, TypeError, ValueError):
                    continue  # an unusable prior means a full case and fresh controls
        executed = {}
        if fresh:
            with tempfile.TemporaryDirectory(prefix='veldo-selected-mutations-') as temporary:
                directory = Path(temporary)
                frozen = directory / 'input'
                frozen_common = snapshot(root, expected_common, frozen, files, head)
                C.require(inventory(frozen, frozen_common) == cases, 'registry changed while snapshotting')
                workers.resources = SuiteResources.from_root(frozen, capacities)
                executed = run_selected_cases(workers, fresh, directory, frozen, store=store, commit=head,
                    changed=plan['changed_paths'], configurations=configurations, registered_cases=cases,
                    prior_kills=prior_kills, prior_controls=prior_controls, claims=claims,
                    verify_runtime=context.get('verify_runtime', False))
        C.require(inputs_unchanged(root, expected_common, files, head), 'inputs changed during stage')
        items = [*carried, *executed.values()]
        for item in items:
            C.item_evidence(store, item)
        fallbacks = sum(len(store.get(store.get(i['result_digest'])['execution_record_digest'])['result']['attempts']) == 2
                        for i in executed.values())
        return dict(schema='veldo.mutation-stage/v2', status='passed', items=items,
                    registered=len(cases), executed=len(executed), carried=len(carried),
                    worker_invocations=workers.invocations, peak_workers=workers.peak, fallback_count=fallbacks,
                    worker_seconds=sum(o['elapsed'] for o in workers.outcomes), worker_outcomes=workers.outcomes)
    finally:
        errors = workers.cleanup()
        if workers.admission:
            workers.admission.close()
        if errors:
            raise Refused('worker_cleanup_error', str(errors))


if __name__ == '__main__':
    sys.exit(main())
