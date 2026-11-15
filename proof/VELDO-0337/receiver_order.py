"""Read-only reproduction of the VELDO-0337 footprint blocker.

Runs production Launch.wait and Runtime.review. The child, floor, signing,
and worker result are stand-ins. No process is started or signalled, no
store or filesystem item is removed, and no verdict is actually persisted.
"""

import importlib.util
import types
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        'probe0337', root / '.veldo/control_launch_work.py')
    work = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(work)
    trace, stored = [], []
    launch = object.__new__(work.L.Launch)
    launch.owned = True
    launch.child = types.SimpleNamespace(
        poll=lambda: 0, wait=lambda **kw: trace.append('receiver reaped'),
        stdin=None, returncode=0)
    launch.contract, launch.ends_by, launch.result = {'deadline': 0}, None, 'accepted'
    launch.record, launch.dispatch_id = {'state': 'exited'}, 'review-fixture'
    launch.dispatches = types.SimpleNamespace(record=lambda identity: launch.record)
    assignment = {'assignment': 'a1', 'reviewer': 'reviewer',
                  'source': {'commit': 'c1'}, 'proof': {'digest': 'p1'}}
    body = dict(schema='veldo.review_receipt/v1', assignment='a1', unit='VELDO-0337',
                reviewer='reviewer', source='c1', proof='p1', verdict='pass', findings=[])
    runtime = object.__new__(work.Runtime)
    runtime.role = lambda *args: {'identity': 'reviewer', 'signing_file': 'fixture-key'}
    runtime.reviewer = lambda unit: runtime.role()

    def record_review(*args, **kwargs):
        assert trace == ['receiver reaped', 'result returned', 'receipt signed']
        stored.append(body)
        trace.append('verdict recorded')
        return {'state': 'returned'}

    runtime.floor = types.SimpleNamespace(
        handoff_refusals=lambda unit: ['awaiting_reviews'],
        assign_review=lambda *args: assignment,
        record=lambda unit: {'builder': 'builder'}, record_review=record_review)

    def run(*args):
        launch.wait()
        assert not stored
        trace.append('result returned')
        return body, {'dispatch': 'review-fixture', 'artifact': {}}

    runtime._run = run

    def sign(*args):
        assert not stored
        trace.append('receipt signed')
        return 'fixture-signature'

    original = work.organ
    work.organ = lambda name: (types.SimpleNamespace(sign_bytes=sign)
                               if name == 'control_signer' else original(name))
    runtime.review({'id': 'VELDO-0337'})
    assert stored == [body]
    print('Direct runtime path: ' + ' -> '.join(trace))
    trace.clear()
    stored.clear()
    runtime.review({'id': 'VELDO-0337', 'assignment': assignment})
    assert not stored
    assert trace == ['receiver reaped', 'result returned', 'receipt signed']
    print('Assigned path: ' + ' -> '.join(trace) + ' -> returns without recording verdict')
    print('Ordering checks: 2 passed. These diagnose the blocker; they do not prove the ACs.')


if __name__ == '__main__':
    main()
