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
    owner = load(authority / 'scripts/check_teeth_mutations.py')
    owner.ROOT = root
    boundary.close_descriptors([])
    # Never load the candidate's sandbox or worker driver, even for fresh cases.
    sandbox.restrict(root, Path(os.environ['TMPDIR']), job.get('runtime_paths', sandbox.RUNTIME),
                     legacy=False)
    boundary.ipc_filter(__import__('ctypes').CDLL(None, use_errno=True))
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
