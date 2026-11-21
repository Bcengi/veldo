"""Measure real cold/warm workers with fixture admission, never production qualifications.

The scratch store authenticates real worker observations. Only admission and runtime fingerprinting
are fixture seams: these registry cases have no production sensitivity qualification. The real
coordinator still snapshots Git inputs, confines workers, validates results and draws its own audit.
Output goes to stdout; this program never writes a receipt into the candidate tree during a stage.
"""
import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch


def main():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location('audit_measure', root / 'scripts/check_gate_mutations.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    reuse = gate.load(root / 'scripts/case_reuse.py')
    original_session, original_load = reuse.Session, gate.load
    with tempfile.TemporaryDirectory(prefix='veldo-0218-measure-') as temporary:
        cache = Path(temporary) / 'store'
        def qualified(root, files, cases, head, configuration, force_fresh=False):
            session = original_session.__new__(original_session)
            session.root, session.files = root, files
            session.forced = force_fresh
            session.base_digest = reuse.R.digest(gate.file_identity(files))
            session.case_digests = {c['identity']: reuse.R.digest(dict(inputs=session.base_digest, case=c))
                                    for c in cases}
            session.keys = {name: None if force_fresh else key for name, key in session.case_digests.items()}
            session.reasons = dict.fromkeys(session.keys, 'force_fresh' if force_fresh else 'miss')
            session.hits, session.stale, session.snapshots = {}, {}, {}
            session.runtime_checks, session.runtime_absent = {}, {}
            session.reviewed = dict.fromkeys(session.keys, {'rationale': 'measurement fixture only'})
            session.gate_run = reuse.os.urandom(16).hex()
            session.store = reuse.R.Store(cache, root)
            session.store_directory = lambda: cache
            return session
        with patch.object(reuse, 'Session', side_effect=qualified), patch.object(gate, 'load',
                side_effect=lambda path: reuse if path.name == 'case_reuse.py' else original_load(path)):
            for phase in ('cold', 'warm'):
                receipt = gate.run_stage(root, gate.common_directory(root), findings=[218])
                audit = receipt['audit']
                print(json.dumps(dict(phase=phase, qualification='fixture-only',
                    status=receipt['status'], error=receipt.get('error'), detail=receipt.get('detail'),
                    executed=receipt['executed'], reused=receipt['reused'], audit=audit,
                    elapsed=receipt['elapsed'], worker_invocations=receipt['worker_invocations'],
                    worker_seconds=sum(o['elapsed'] for o in receipt['worker_outcomes'])), sort_keys=True), flush=True)
                if receipt['status'] != 'passed':
                    return 1
                if phase == 'warm' and (audit['audited'] != 3 or audit['matched'] != 3 or receipt['reused']):
                    return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
