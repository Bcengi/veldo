#!/usr/bin/env python3
"""Authority worker bootstrap. Read the owned job before denying store and authority writes.

The parent creates the job and observes this child's output and exit. Candidate
receipts are never ingested by the coordinator. All candidate imports and execs
happen after the reviewed authority sandbox has installed its kernel boundary.
"""
import importlib.util
import json
import os
from pathlib import Path
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
    job = json.loads(Path(sys.argv[3]).read_text())
    boundary = load(authority / 'scripts/agent_sandbox.py')
    sandbox = load(authority / 'scripts/mutation_sandbox.py')
    owner = load(authority / 'scripts/mutation_observer.py')
    owner.ROOT = root
    ownership = load(authority / 'scripts/mutation_ownership.py')
    boundary.close_descriptors([])
    # Ownership is persisted from the authority copy before any candidate code runs, so the
    # coordinator can reap this worker's allocations even after SIGKILL. The ledger opens after
    # descriptors are closed and lives in the worker's own writable home.
    ownership.Tracker(Path(sys.argv[3]).parent).install()
    # Never load the candidate's sandbox or worker driver, even for fresh cases.
    grants = [(root, boundary.READ), (Path(os.environ['TMPDIR']), boundary.READ | boundary.WRITE)]
    grants += [(Path(p).resolve(), boundary.READ)
               for p in job.get('runtime_paths', sandbox.RUNTIME) if Path(p).exists()]
    grants += [(Path('/dev/null'), (1 << 1) | (1 << 2)), (Path('/dev/urandom'), 1 << 2)]
    boundary.landlock(grants, profile='worker')
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
