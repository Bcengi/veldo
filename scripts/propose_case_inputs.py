#!/usr/bin/env python3
"""Propose case input declarations from traced runs, outside any gate. Never grants review approval.

VELDO-0217. Every case of the confined leg gets a current proposal:

  --all      traces every confined case of the coordinator's inventory;
  --stale    traces only the confined cases with no declaration or a stale one;
  --case ID  traces the named cases (repeatable);
  --check    traces nothing: reports each declaration's staleness and the counts.

A case is traced four times, each run under strace and the proposer's audit hook: two independent
baselines, the no-op and the mutant. Runs are admitted in parallel through the coordinator's
admission (check_gate_mutations.Admission, VELDO-0219) over a gate_schedule.Ledger sized to this
host, each claiming the case's measured resources; nothing here runs inside a gate, and a process
that carries a gate's ledger channel or leg is refused before anything runs.

Each proposal records the digest of every repository file it read, the read-set, trace and
observation digests of each run, and the non-file input classes its traces show (case_trace,
AC4). A declaration is stale when a file it was proposed from changed or it records none; a
re-proposal is reported with the files its trace reads that the old declaration omitted.

All workers have an owned process group, removed with their temporary tree. A traced run is bounded
only against a hang, by the gate's WORKER_CEILING (VELDO-0285) without trace or output progress.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import case_inputs as I
import case_trace as T
import mutation_reuse as M

REPORT_SCHEMA = 'veldo.case-proposals/v1'
RUNS = ('baseline', 'baseline', 'noop', 'mutant')
SYSTEM = ('/usr', '/lib', '/lib64', '/etc')
GATE_VARIABLES = ('VELDO_GATE_LEDGER_FD', 'VELDO_GATE_LEG', 'VELDO_GATE_UNCONFINED', 'VELDO_GATE_DECLARATION')


def load_gate():
    spec = importlib.util.spec_from_file_location('gate', ROOT / 'scripts/check_gate_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def refuse_inside_gate(environ=None):
    """The proposer never runs inside a gate (VELDO-0217): a gate's ledger channel or leg in the
    environment is a refusal by name, before anything is traced."""
    present = [name for name in GATE_VARIABLES if name in (os.environ if environ is None else environ)]
    if present:
        raise SystemExit('propose_case_inputs: refused inside a gate (%s set); run it outside any gate'
                         % ', '.join(present))


def audit_hook(audit):
    """The proposer's audit channel: every Python open and directory listing, one JSON line each.
    It covers dynamic Python imports; the independent syscall trace covers children."""
    def hook(event, args):
        if event in ('open', 'os.listdir', 'os.scandir') and args and isinstance(args[0], str):
            audit.write(json.dumps([event, os.path.abspath(args[0])]) + '\n')
            audit.flush()
    return hook


def probe(jobfile, auditfile):
    with open(auditfile, 'w') as audit:
        sys.addaudithook(audit_hook(audit))
        gate = load_gate()
        # The worker is confined exactly as a coordinator's (mutation_sandbox.confine); the audit
        # file is the one descriptor it keeps.
        print(json.dumps(gate.worker(json.loads(Path(jobfile).read_text()), keep=(audit.fileno(),))))


def audit_events(path):
    path = Path(path)
    if not path.exists():
        return []
    return [tuple(json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def executables(trace):
    found = []
    for line in T.syscall_lines(trace):
        if 'execve(' in line:
            match = T.QUOTED.search(line)
            if match:
                found.append(Path(ast.literal_eval(match[0])))
    return found


def capture(root, accesses, events, programs=()):
    """What one run read, from its syscall accesses [(path, kind, success)], its audit events
    [(event, path)] and the programs it executed: repository files (a listed directory is its whole
    subtree), absent repository probes, listed directories, and system runtime files and probes."""
    root = Path(root)
    reads = {(p, kind == 'listing') for p, kind, success in accesses}
    reads.update((p, False) for p in programs if p.is_absolute())
    runtime_absent = {str(p) for p, kind, success in accesses
                      if not success and not p.exists() and not p.is_relative_to(root)
                      and any(p.is_relative_to(base) for base in (*SYSTEM, '/proc', '/sys'))}
    for event, name in events:
        path = Path(name)
        # A directory read is proposed as its complete repository subtree.
        if event in ('os.listdir', 'os.scandir') and path.is_dir() and path.is_relative_to(root):
            reads.update((p, False) for p in path.rglob('*') if p.is_file())
        else:
            reads.add((path, event != 'open'))
    files, absent, directories, runtime = set(), set(), set(), set()
    for path, is_directory in reads:
        if path.is_relative_to(root):
            name = str(path.relative_to(root))
            if '.git' in path.parts or '__pycache__' in path.parts:
                continue
            if is_directory and path.is_dir():
                directories.add(name)
                files.update(str(p.relative_to(root)) for p in path.rglob('*')
                             if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts)
            if path.is_file():
                files.add(name)
            elif not is_directory and not path.exists():
                absent.add(name)
        elif path.is_file() and any(path.is_relative_to(p) for p in SYSTEM):
            runtime.add(str(path))
    return {'files': sorted(files), 'absent': sorted(absent - files), 'directories': sorted(directories),
            'runtime': sorted(runtime), 'runtime_absent': sorted(runtime_absent)}


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def observation_digest(observation):
    return digest({k: v for k, v in observation.items() if k != 'failed_details'})


def run_traced(argv, env, cwd, directory, ceiling):
    """Run argv under strace in its own process group; (exit, seconds, stdout, stderr, trace)."""
    trace = Path(directory) / 'trace'
    start = time.monotonic()
    with open(Path(directory) / 'stdout', 'w+b') as stdout, open(Path(directory) / 'stderr', 'w+b') as stderr:
        proc = subprocess.Popen(T.command(trace, argv), env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            progress = (0, 0, 0)
            while True:
                try:
                    code = proc.wait(timeout=ceiling)
                    break
                except subprocess.TimeoutExpired:
                    observed = (trace.stat().st_size if trace.exists() else 0,
                                os.fstat(stdout.fileno()).st_size, os.fstat(stderr.fileno()).st_size)
                    if observed == progress:
                        code = 124
                        break
                    progress = observed
                    print('case trace: still progressing (%d trace bytes); continuing' % observed[0], flush=True)
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        stdout.seek(0)
        stderr.seek(0)
        out, err = stdout.read(), stderr.read()
    if code == 124:
        # The tracer died with its tracees, so the trace ends mid-call: no evidence, and no read
        # set may be proposed from it. Say why, rather than what the parser then finds.
        raise TimeoutError('traced run made no progress for %gs; its trace is incomplete' % ceiling)
    return code, round(time.monotonic() - start, 3), out, err, trace


def trace_case(gate, case, mode=None, keep=None):
    """One traced run of a case in one mode: (row, what it read, the worker's own output). The row
    holds the run's exit, the digests of its trace, read set and observation, and the non-file input
    classes its trace shows (case_trace.non_file_inputs).

    Without a mode, the earlier single-case form (VELDO-0207): baseline, noop and mutant one after
    another, as ({files, absent, directories, runtime_absent, modes}, runtime)."""
    if mode is None:
        modes, captured = [], []
        for each in ('baseline', 'noop', 'mutant'):
            row, reads, output = trace_case(gate, case, each, keep)
            modes.append({'mode': each, 'exit': row['exit'], 'seconds': row['seconds'],
                          **({'observation': output} if output is not None else {'error': row.get('error', '')})})
            captured.append(reads)
        files = set().union(*(c['files'] for c in captured))
        return ({'files': sorted(files),
                 'absent': sorted(set().union(*(c['absent'] for c in captured)) - files),
                 'directories': sorted(set().union(*(c['directories'] for c in captured))),
                 'runtime_absent': sorted(set().union(*(c['runtime_absent'] for c in captured))),
                 'modes': modes}, set().union(*(set(c['runtime']) for c in captured)))
    with tempfile.TemporaryDirectory(prefix='veldo-case-proposal-') as temporary:
        directory = Path(temporary)
        job, audit = directory / 'job.json', directory / 'audit'
        job.write_text(json.dumps({'case': case, 'mode': mode}))
        argv = [sys.executable, '-B', '-X', 'pycache_prefix=' + str(directory / 'bytecode'),
                str(Path(__file__).resolve()), '--probe', str(job), str(audit)]
        code, seconds, out, err, trace = run_traced(argv, gate.fixed_env(directory), ROOT, directory,
                                                    gate.WORKER_CEILING)
        row = {'mode': mode, 'exit': code, 'seconds': seconds,
               'trace': hashlib.sha256(trace.read_bytes()).hexdigest()}
        output = None
        try:
            output = json.loads(out)
            observation = output['observation']
            row['observation'] = observation_digest(observation)
            row['failed_rows'] = observation.get('failed_rows', [])
        except (ValueError, KeyError, TypeError):
            output = None
            row['error'] = home_as_tilde(err.decode(errors='replace')[-1500:])
        captured = capture(ROOT, list(T.accesses(trace, cwd=ROOT)), audit_events(audit), executables(trace))
        row['non_file'] = sorted(T.non_file_inputs(trace, (directory,)))
        # A socket path that did not exist is keyed by its absence, as a failed runtime probe is.
        captured['runtime_absent'] = sorted(set(captured['runtime_absent']) | set(T.absent_sockets(trace, (directory,))))
        row['reads'] = digest({k: captured[k] for k in ('files', 'absent', 'directories')})
        if keep is not None:
            Path(keep).mkdir(parents=True, exist_ok=True)
            (Path(keep) / (digest(case['identity']) + '-' + mode + '-' + row['trace'][:12] + '.trace')
             ).write_bytes(trace.read_bytes())
    return row, captured, output


class LocalLedger:
    """gate_schedule.Ledger behind the protocol of gate_schedule.Client, so the coordinator's own
    Admission admits each traced run against this host's capacity (VELDO-0219) outside a gate."""
    def __init__(self, capacity):
        schedule = load_module('gate_schedule')
        self.ledger = schedule.Ledger(capacity)
        self.last_reply = {}

    def acquire(self, name, cpu, memory, manager='none', ports=(), host_lock='none'):
        granted = self.ledger.acquire(name, dict(cpu=cpu, memory=memory, manager=manager,
                                                 ports=list(ports), host_lock=host_lock))
        self.last_reply = {'granted': granted, 'resource': self.ledger.blocking_resource,
                           'totals': self.ledger.totals()}
        return granted

    def release(self, name):
        self.ledger.release(name)

    def close(self):
        pass


def host_capacity(resources):
    """This host's admission capacity: its usable CPUs and the memory it can give, the smaller of
    MemAvailable and any cgroup memory.max above this process."""
    try:
        cpus = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        cpus = os.cpu_count() or 2
    memory = None
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):
                memory = int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    try:
        group = Path('/proc/self/cgroup').read_text().strip().split('::', 1)[1]
        path = Path('/sys/fs/cgroup' + group)
        while str(path).startswith('/sys/fs/cgroup'):
            limit = path / 'memory.max'
            if limit.exists() and limit.read_text().strip() != 'max':
                memory = min(memory or 1 << 62, int(limit.read_text()))
            if path == path.parent:
                break
            path = path.parent
    except (OSError, ValueError, IndexError):
        pass
    return {'cpu': cpus, 'memory': memory or 2 ** 32,
            'manager': max(1, resources.capacity.get('systemd_user_manager', 1))}


class Pool:
    """Traced runs in parallel, each admitted by the coordinator's Admission with the case's measured
    claim. A thread waits for a grant on the release of another run, never on a clock."""
    def __init__(self, gate, parallel=None, admission=None, resources=None):
        self.gate = gate
        self.resources = resources or gate.SuiteResources.from_root(ROOT)
        if admission is None:
            capacity = host_capacity(self.resources)
            admission = gate.Admission(LocalLedger(capacity), capacity, {'cpu': 0, 'memory': 0})
        self.admission = admission
        self.parallel = parallel or gate.worker_count()
        self.changed = threading.Condition()
        self.running = 0
        self.worker_seconds = 0.0
        self.peak = 0

    def admit(self, name, job):
        with self.changed:
            while True:
                if (self.running < self.parallel and self.resources.select([(name, job)]) is not None
                        and self.admission.acquire(name, job, self.resources)):
                    self.resources.acquire(name, job)
                    self.running += 1
                    self.peak = max(self.peak, self.running)
                    return
                if not self.running:
                    raise RuntimeError('%s: its claim exceeds this host capacity %s'
                                       % (name, self.admission.capacity))
                self.changed.wait()

    def release(self, name, seconds):
        with self.changed:
            self.admission.release(name)
            self.resources.release(name)
            self.running -= 1
            self.worker_seconds += seconds
            self.changed.notify_all()

    def map(self, jobs, run):
        """run(job) for every (name, job), each admitted first; results by name, errors raised."""
        results, errors = {}, []

        def one(name, job):
            try:
                self.admit(name, job)
            except Exception as error:
                errors.append(error)
                return
            started = time.monotonic()
            try:
                results[name] = run(job)
            except Exception as error:
                errors.append(error)
            finally:
                self.release(name, time.monotonic() - started)
        threads = [threading.Thread(target=one, args=item) for item in jobs]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        if errors:
            raise errors[0]
        return results


def proposal(root, identity, runs, captured, gate_observation=None, gate_receipt=None, inputs=None):
    """The declaration a set of traced runs proposes, with the digest of every file they read."""
    files = sorted(set().union(*(c['files'] for c in captured)))
    proposed = {
        'files': sorted(set(files) | set(I.MANDATORY) | set(I.DRIVERS)),
        'absent': sorted(set().union(*(c['absent'] for c in captured)) - set(files)),
        'directories': sorted(set().union(*(c['directories'] for c in captured))),
        'reviewed': False,
        'non_file_inputs': 'none' if not any(r['non_file'] for r in runs)
                           else sorted(set().union(*(r['non_file'] for r in runs))),
        'rationale': '',
        'trace_scope': '-'.join(RUNS),
        'proposal': {'read_digests': {name: file_digest(Path(root) / name)
                                      for name in sorted(set(files) | set(I.MANDATORY) | set(I.DRIVERS))
                                      if (Path(root) / name).is_file()},
                     'runs': [{k: r.get(k) for k in ('mode', 'exit', 'reads', 'trace', 'observation', 'non_file')}
                              for r in runs],
                     'gate_observation': gate_observation,
                     # The receipt the observation came from, and the inputs this proposal traced:
                     # case_reuse takes the observation as the last fresh one only when they agree.
                     'gate_receipt': gate_receipt, 'inputs': inputs}}
    return proposed


def stale(root, declaration):
    """Why a declaration is stale, mechanically; [] when current. A declaration is current only when
    it records the digest of every file it was proposed from and each still has those bytes."""
    recorded = (declaration.get('proposal') or {}).get('read_digests')
    if not recorded:
        return ['no_recorded_inputs']
    reasons = []
    for name in sorted(set(declaration['files']) - set(recorded)):
        reasons.append('unrecorded_input:' + name)
    for name, value in sorted(recorded.items()):
        path = Path(root) / name
        if not path.is_file():
            reasons.append('input_missing:' + name)
        elif file_digest(path) != value:
            reasons.append('input_changed:' + name)
    return reasons


def confined_cases(gate, inventory, leg):
    """The coordinator's own enumeration of the confined leg: every case not in the unconfined leg.
    A case of a suite listed only for some rows cannot run as a case at all, so it is not confined."""
    result = []
    for case in inventory:
        try:
            if not gate.in_leg(leg, case):
                result.append(case)
        except gate.Refused:
            continue
    return result


def complete(report_identities, confined):
    """The proposal report against the coordinator's enumeration, by identity: (missing, extra)."""
    expected = {c['identity'] for c in confined}
    reported = set(report_identities)
    return sorted(expected - reported), sorted(reported - expected)


def gate_observations(receipt, inputs):
    """({identity: baseline observation digest}, receipt binding) from a gate's mutation receipt (its
    fresh results). The last fresh gate observation of what a proposal traced is a passed receipt over
    exactly the proposal's inputs (`inputs`: the gate's input digest of this tree, its files and head);
    a receipt of any other state, earlier or later, is refused: ({}, None)."""
    raw = Path(receipt).read_bytes()
    document = json.loads(raw)
    binding = {'input_digest': document.get('input_digest'), 'status': document.get('status'),
               'digest': hashlib.sha256(raw).hexdigest()}
    if binding['status'] != 'passed' or binding['input_digest'] != inputs:
        return {}, None
    found = {}
    for result in document.get('results', []):
        if result.get('source') == 'fresh' and isinstance(result.get('baseline'), dict):
            found[result['case']['identity']] = observation_digest(result['baseline'])
    return found, binding


def propose(gate, case, pool, gate_observation=None, keep=None, gate_receipt=None, inputs=None):
    jobs = [(case['identity'] + '#' + str(index) + ':' + mode, {'case': case, 'mode': mode,
             'claim': pool.claims[case['identity']]}) for index, mode in enumerate(RUNS)]
    results = pool.map(jobs, lambda job: trace_case(gate, job['case'], job['mode'], keep))
    ordered = [results[name] for name, _job in jobs]
    runs, captured = [r for r, _c, _o in ordered], [c for _r, c, _o in ordered]
    return proposal(ROOT, case['identity'], runs, captured, gate_observation,
                    gate_receipt if gate_observation else None, inputs), runs, captured


def home_as_tilde(text):
    """Evidence text with the user's home directory written as ~ (VELDO-0259). The personal-setup gate
    stage refuses a home path on any line a candidate adds, proof/ included, so the writer that records
    into proof/ does this when it writes, and no builder has to remember to."""
    import re
    homes = {os.path.expanduser('~')}
    try:
        import pwd
        homes.add(pwd.getpwuid(os.getuid()).pw_dir)
    except (ImportError, KeyError):
        pass
    for home in sorted({h.rstrip('/') for h in homes if h and h.rstrip('/')}, key=len, reverse=True):
        text = re.sub(re.escape(home) + r'(?![A-Za-z0-9_.\-])', lambda _: '~', text)
    return text


def authority_staleness(document, directory):
    """Only marks for the current declaration ask the proposer to re-trace it."""
    C = load_module('case_reuse')
    result = {}
    for entry in M.stale_entries(directory):
        declaration = document['cases'].get(entry['identity'])
        if declaration is not None and C.declaration_digest(declaration) == entry['declaration']:
            result.setdefault(entry['identity'], []).append('declaration_stale:' + entry['reason'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--probe', nargs=2)
    select = parser.add_mutually_exclusive_group()
    select.add_argument('--case', action='append')
    select.add_argument('--all', action='store_true')
    select.add_argument('--stale', action='store_true')
    select.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / I.DECLARATIONS)
    parser.add_argument('--report', type=Path, default=ROOT / 'proof/VELDO-0217/proposals.json')
    parser.add_argument('--gate-receipt', type=Path, help='a gate mutation receipt: its fresh baseline '
                        'observations are recorded beside the traced ones (AC2)')
    parser.add_argument('--jobs', type=int, help='at most this many traced runs at once')
    parser.add_argument('--keep-traces', type=Path, help='keep each run trace here (outside the repository)')
    args = parser.parse_args()
    if args.probe:
        probe(*args.probe)
        return 0
    if not (args.case or args.all or args.stale or args.check):
        parser.error('choose --case, --all, --stale or --check; no implicit registry drive')
    refuse_inside_gate()
    began = time.monotonic()
    gate = load_gate()
    leg = load_module('gate_legs').mutation_leg()
    inventory = gate.inventory(ROOT, gate.common_directory(ROOT))
    confined = confined_cases(gate, inventory, leg)
    registry = {c['identity']: c for c in confined}
    document = (json.loads(args.output.read_text()) if args.output.exists()
                else {'schema': 'veldo.case-inputs/v1', 'cases': {}, 'toolchains': {}})
    marked = authority_staleness(document, os.environ.get('VELDO_GATE_CACHE') or M.R.E.configuration()[1]['store'])
    staleness = {name: stale(ROOT, document['cases'][name]) + marked.get(name, [])
                 for name in registry if name in document['cases']}
    for name, reasons in sorted(staleness.items()):
        if reasons:
            print('stale', name, ' '.join(reasons[:4]) + (' ...' if len(reasons) > 4 else ''), flush=True)
    if args.check:
        names = []
    elif args.case:
        unknown = sorted(set(args.case) - set(registry))
        if unknown:
            parser.error('not a confined case of the inventory: ' + ', '.join(unknown))
        names = args.case
    elif args.stale:
        names = [n for n in registry if n not in document['cases'] or staleness.get(n)]
    else:
        names = list(registry)
    pool = Pool(gate, args.jobs)
    files = gate.read_inputs(ROOT, gate.common_directory(ROOT))
    inputs = gate.digest({'files': gate.file_identity(files),
                          'head': gate.git(ROOT, gate.common_directory(ROOT), 'rev-parse', 'HEAD')})
    observed, receipt_binding = gate_observations(args.gate_receipt, inputs) if args.gate_receipt else ({}, None)
    if args.gate_receipt and receipt_binding is None:
        print('gate receipt refused: not a passed receipt over this tree; no gate observation recorded', flush=True)
    store = gate.CaseClaims()
    pool.claims = {n: store.claim(registry[n], gate.case_time_key(registry[n], files, leg)) for n in names}
    report = {'schema': REPORT_SCHEMA, 'commit': gate.git(ROOT, gate.common_directory(ROOT), 'rev-parse', 'HEAD'),
              'inventory': {'registered': len(inventory), 'confined': len(confined)},
              'cases': [], 'stale': {n: r for n, r in sorted(staleness.items()) if r}}
    lock = threading.Lock()
    previous = {n: document['cases'].get(n) for n in names}

    def one(name):
        case = registry[name]
        declared, runs, captured = propose(gate, case, pool, observed.get(name), args.keep_traces,
                                           receipt_binding, inputs)
        runtime = set().union(*(c['runtime'] for c in captured))
        absent_runtime = set().union(*(c['runtime_absent'] for c in captured))
        before = previous.get(name)
        entry = {'identity': name, 'files': len(declared['files']),
                 'read_digests': declared['proposal']['read_digests'],
                 'runs': [{k: r.get(k) for k in ('mode', 'exit', 'seconds', 'reads', 'trace', 'observation',
                                                 'non_file', 'error')} for r in runs],
                 'non_file': sorted(set().union(*(r['non_file'] for r in runs))),
                 'stale_before': staleness.get(name, ['no_declaration']) if before else ['no_declaration'],
                 'undeclared_before': sorted(set(declared['files']) - set(before['files'])) if before else None}
        with lock:
            current = document['toolchains'].setdefault(case['driver'], {'paths': [], 'reviewed': False})
            current['absent'] = sorted(set(current.get('absent', [])) | absent_runtime)
            paths = set(current['paths']) | runtime | {str(p) for p in M.required_runtime(gate.fixed_env('<scratch>'))}
            current['paths'] = sorted(p for p in paths if not any(
                p != parent and Path(p).is_relative_to(parent) for parent in paths))
            document['cases'][name] = declared
            report['cases'].append(entry)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + '\n')
        print('proposed', name, 'exits', ','.join(str(r['exit']) for r in runs), 'reads', len(declared['files']),
              'non-file', ','.join(entry['non_file']) or 'none', flush=True)
        return entry

    # Cases in parallel too, as many at once as runs may be: each case's four runs then wait for
    # admission like every other run, so the pool stays full without a thread per case.
    pending, failures = list(reversed(names)), []

    def guarded():
        while True:
            with lock:
                if not pending:
                    return
                name = pending.pop()
            try:
                one(name)
            except Exception as error:
                with lock:
                    failures.append((name, str(error)))
                print('failed', name, error, flush=True)
    case_threads = [threading.Thread(target=guarded) for _ in range(min(len(names), pool.parallel))]
    for thread in case_threads:
        thread.start()
    for thread in case_threads:
        thread.join()
    report['cases'].sort(key=lambda e: e['identity'])
    report['failures'] = failures
    if args.all:
        missing, extra = complete([e['identity'] for e in report['cases']], confined)
        report['completeness'] = {'missing': missing, 'extra': extra, 'compared_with': 'coordinator inventory'}
    declarations = {n: d for n, d in document['cases'].items() if n in registry}
    classes = {}
    for entry in report['cases']:
        for name in entry['non_file']:
            classes[name] = classes.get(name, 0) + 1
    report['summary'] = {
        'declared': len(declarations),
        'current': sum(1 for d in declarations.values() if not stale(ROOT, d)),
        'stale': sum(1 for d in declarations.values() if stale(ROOT, d)),
        'reviewed': sum(1 for d in declarations.values() if d.get('reviewed') is True),
        'proposed': len(report['cases']), 'failed': len(failures),
        'wall_seconds': round(time.monotonic() - began, 3),
        'worker_seconds': round(pool.worker_seconds, 3), 'peak_runs': pool.peak,
        'non_file_classes': classes}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(home_as_tilde(json.dumps(report, indent=2, sort_keys=True) + '\n'))
    print(json.dumps(report['summary'], sort_keys=True), flush=True)
    return 1 if failures or report.get('completeness', {}).get('missing') else 0


if __name__ == '__main__':
    sys.exit(main())
