#!/usr/bin/env python3
"""Authority worker bootstrap. Read the owned job before denying store and authority writes.

The parent creates the job and observes this child's output and exit. Candidate
receipts are never ingested by the coordinator. All candidate imports and execs
happen after the reviewed authority sandbox has installed its kernel boundary, except in the
mutation stage's unconfined leg (mode 'unconfined'), which the coordinator starts only for a case of
a suite the authority's scripts/gate_unconfined.json names (VELDO-0208, owner decision).
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


def main():
    authority = Path(__file__).resolve().parents[1]
    mode, root = sys.argv[1], Path(sys.argv[2])
    gate = load(authority / 'scripts/check_gate_mutations.py')
    if mode == 'inventory':  # Already confined by gate_candidate before this import.
        print(json.dumps(gate.inventory_local(root)))
        return
    # argv: worker|unconfined ROOT LEDGER_FD JOB. The ledger descriptor is the coordinator's
    # append-only channel; the file it names lies outside this worker's write grants.
    if mode not in ('worker', 'unconfined'):
        raise ValueError('unknown worker mode: ' + mode)
    ledger, jobpath = int(sys.argv[3]), Path(sys.argv[4])
    if not stat.S_ISREG(os.fstat(ledger).st_mode) or not fcntl.fcntl(ledger, fcntl.F_GETFL) & os.O_APPEND:
        raise ValueError('ownership channel must be an append-only regular file descriptor')
    job = json.loads(jobpath.read_text())
    boundary = load(authority / 'scripts/agent_sandbox.py')
    sandbox = load(authority / 'scripts/mutation_sandbox.py')
    owner = load(authority / 'scripts/mutation_observer.py')
    owner.ROOT = root
    ownership = load(authority / 'scripts/mutation_ownership.py')
    boundary.close_descriptors([], keep=(ledger,))
    # Ownership is persisted from the authority copy before any candidate code runs, so the
    # coordinator can reap this worker's allocations even after SIGKILL. Candidate code can
    # append to the same channel, so the coordinator validates every entry before acting.
    ownership.Tracker(jobpath.parent, ledger).install()
    if mode == 'unconfined':
        # The mutation stage's unconfined leg (VELDO-0208, owner decision Telegram 32403-32407): the
        # coordinator starts a case of a suite the authority's list names in this mode, and only
        # such a case. It runs as that suite does in the unit stage's unconfined leg, without the
        # boundary below: with the owner's authority, as every worker did before VELDO-0208.
        if 'runtime_paths' in job or 'snapshot_root' in job:
            raise ValueError('an unconfined worker runs no declared case')
        observe(gate, owner, job, root)
        return
    # Never load the candidate's sandbox or worker driver, even for fresh cases. The confinement is
    # mutation_sandbox.confine, the gate profile's domain and network rule (VELDO-0208, owner
    # decision Telegram 32421); this process returns from it only as the confined child.
    sandbox.confine(authority, root, Path(os.environ['TMPDIR']), job.get('runtime_paths'), keep=(ledger,))
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
