#!/usr/bin/env python3
"""Authority worker bootstrap: one mutation case as a plain child of the coordinator.

The parent creates the job and observes this child's output and exit. Candidate
receipts are never ingested by the coordinator. The worker runs in its own process group and,
under the gate, its own cgroup; no namespace and no Landlock domain is started (VELDO-0271), so a
case runs the same way whether the gate or a driver started it.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def join_worker_cgroup():
    # Authority opens this descriptor before spawn. Close it before any candidate
    # import, and remove it from the environment.
    descriptor = os.environ.pop('VELDO_MUTATION_CGROUP_FD', None)
    if descriptor is not None:
        fd = int(descriptor)
        try:
            os.write(fd, str(os.getpid()).encode())
        except OSError as error:
            raise RuntimeError('worker_launch_error: cannot enter worker cgroup') from error
        finally:
            os.close(fd)


def main():
    join_worker_cgroup()
    authority = Path(__file__).resolve().parents[1]
    mode, root = sys.argv[1], Path(sys.argv[2])
    if mode == 'inventory':  # Started through gate_candidate.py, like every candidate command.
        gate = load(authority / 'scripts/check_gate_mutations.py')
        print(json.dumps(gate.inventory_local(root)))
        return
    # argv: worker ROOT LEDGER_FD JOB. The ledger descriptor is the coordinator's append-only
    # channel to its ownership ledger.
    if mode != 'worker':
        raise ValueError('unknown worker mode: ' + mode)
    ledger, jobpath = int(sys.argv[3]), Path(sys.argv[4])
    lifecycle = os.environ.get('VELDO_MUTATION_LIFECYCLE_FD')
    if not stat.S_ISREG(os.fstat(ledger).st_mode) or not fcntl.fcntl(ledger, fcntl.F_GETFL) & os.O_APPEND:
        raise ValueError('ownership channel must be an append-only regular file descriptor')
    job = json.loads(jobpath.read_text())
    gate = load(authority / 'scripts/check_gate_mutations.py')
    owner = load(authority / 'scripts/mutation_observer.py')
    owner.ROOT = root
    ownership = load(authority / 'scripts/mutation_ownership.py')
    # Ownership is persisted from the authority copy before any candidate code runs, so the
    # coordinator can reap this worker's allocations even after SIGKILL. Candidate code can
    # append to the same channel, so the coordinator validates every entry before acting.
    os.environ.pop('VELDO_MUTATION_LIFECYCLE_FD', None)
    ownership.Tracker(jobpath.parent, ledger, int(lifecycle) if lifecycle is not None else None).install()
    observe(gate, owner, job, root)


def observe(gate, owner, job, root):
    case = job['case']
    prepared = owner.materialize(case, job['mode'], Path(os.environ['TMPDIR']), root=root)
    mutant = prepared['mutant']
    observation = owner.worker(case, str(mutant) if mutant else None)
    if case['driver'] == gate.DRIVERS[1]:
        matches = observation['targets'][case['rows'][0]]
        observation.update(case=case['name'], row=case['rows'][0],
                           matched=len(matches), passed=matches == [True])
    print(json.dumps(dict(observation=observation,
        **{key: prepared[key] for key in ('replacement_count', 'old_digest', 'new_digest')})))


if __name__ == '__main__':
    main()
