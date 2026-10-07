#!/usr/bin/env python3
"""Authority worker bootstrap. Read the owned job before denying store and authority writes.

The parent creates the job and observes this child's output and exit. Candidate
receipts are never ingested by the coordinator. All candidate imports and execs
happen after the reviewed authority sandbox has installed its kernel boundary.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import signal
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
    # argv: worker ROOT LEDGER_FD JOB. The ledger descriptor is the coordinator's append-only
    # channel; the file it names lies outside this worker's write grants.
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
    # Never load the candidate's sandbox or worker driver, even for fresh cases.
    grants = [(root, boundary.READ), (Path(os.environ['TMPDIR']), boundary.READ | boundary.WRITE)]
    grants += [(Path(p).resolve(), boundary.READ)
               for p in job.get('runtime_paths', sandbox.RUNTIME) if Path(p).exists()]
    grants += [(Path('/dev/null'), (1 << 1) | (1 << 2)), (Path('/dev/urandom'), 1 << 2)]
    # Suites serve and dial Unix sockets in their scratch and drive terminals. This process stays
    # outside the domain as their broker (never running candidate code); the child confines itself.
    sys.stdout.flush()
    sys.stderr.flush()
    pid, side = boundary.fork_brokered([Path(os.environ['TMPDIR'])], network=False)
    if pid:
        try:
            _, status = os.waitpid(pid, 0)
        finally:
            if side is not None:
                side.close()
        if os.WIFSIGNALED(status):
            signal.signal(os.WTERMSIG(status), signal.SIG_DFL)
            os.kill(os.getpid(), os.WTERMSIG(status))
        os._exit(os.waitstatus_to_exitcode(status))
    if boundary.landlock(grants, profile='worker', broker=side) != 'strict':
        os.environ[boundary.BROKERED] = '1'
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
