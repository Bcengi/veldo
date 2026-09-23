"""Release 1 signal delivery over an installed module and real signed SQLite journal.

Three criterion rows, driven by registered production mutations. Barriers expose both
sides of idle entry; joins and cleanup signals bound a defective copy's lifetime.
Handlers observe journal records only: these are consumer seams, not implementations
of settlement, assignment, eligibility, intake or the PM owned by other specifications.
"""
import importlib.util as _n46_import
import json as _n46_json
import shutil as _n46_shutil
import subprocess as _n46_subprocess
import tempfile as _n46_tempfile
import threading as _n46_threading
import time as _n46_time
from pathlib import Path as _n46_Path


def _n46_load(name, path):
    spec = _n46_import.spec_from_file_location(name, path)
    module = _n46_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _n46_checks(directory):
    # Exercise the installer file writer and declared asset inventory. Mutation gate
    # snapshots intentionally omit docs and engine/scripts, so install only this seam.
    scaffold = _n46_load('notify_scaffold', ROOT / '.veldo' / 'init_scaffold.py')
    target = directory / 'installed'
    created, skipped = [], []
    for rel in ('.veldo/control_notify.py', '.veldo/control_store.py'):
        if rel not in scaffold._FILES:
            return False, False, False
        scaffold._lay(ROOT / 'engine' / rel, target / rel, rel, created, skipped)
    installed = target / '.veldo' / 'control_notify.py'
    source = ROOT / ".veldo" / "control_notify.py"
    installed.write_bytes(source.read_bytes())
    delivery = _n46_load('notify_installed', installed)
    store = _n46_load('notify_store', target / '.veldo' / 'control_store.py')
    coords = dict(domain_uuid='domain-test', repository_uuid='repository-test', store_uuid='store-test')
    key = directory / 'journal-key'
    _n46_subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'notification-test',
                         '-f', str(key)], check=True, capture_output=True)
    allowed = directory / 'allowed_signers'
    allowed.write_text('journal ' + key.with_suffix('.pub').read_text())
    signed = []

    def sign(payload):
        proc = _n46_subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-journal'],
                                  input=payload, capture_output=True, check=True)
        signed.append((payload, proc.stdout))
        return proc.stdout.decode()

    seq = 0

    def command(kind):
        nonlocal seq
        seq += 1
        return dict(command_id='command-' + str(seq), principal='journal', operation='upsert_entity',
                    parameters=dict(entity_id='unit-' + str(seq), kind=kind, data={'version': 1}),
                    expected_versions={'unit-' + str(seq): 0}, artifact_digests=[], nonce='nonce-' + str(seq))

    observed = []
    premature = []
    inside_sign = False
    expected_enabled = ('settlement', 'assignment', 'dependency', 'completion', 'budget', 'intake', 'pm')
    expected_kinds = expected_enabled[:-1]
    expected_pairs = {(kind, kind) for kind in expected_kinds} | {(kind, 'pm') for kind in expected_kinds}
    path = directory / 'control.sqlite3'
    writer = store.open_store(str(path))

    def handler(name):
        def apply(event):
            if inside_sign:
                premature.append(name)
            # A second independent connection proves the callback can see the committed identity.
            conn = store.open_store(str(path), mode='r')
            row = conn.execute('SELECT command_id, record_digest FROM journal WHERE seq=?',
                               (event.get('watermark', event.get('seq')),)).fetchone()
            conn.close()
            observed.append((name, event, row))
        return apply

    service = delivery.Delivery(store, str(path), coords, expected_enabled,
                                {name: handler(name) for name in expected_enabled})
    ac1 = set(service.inventory()) == expected_pairs
    ac1 = ac1 and '.veldo/control_notify.py' in scaffold._FILES
    ac1 = ac1 and (ROOT / 'engine/.veldo/control_notify.py').read_bytes() == (ROOT / '.veldo/control_notify.py').read_bytes()
    for kind in expected_kinds:
        cmd = command(kind)

        def guarded_sign(payload):
            nonlocal inside_sign
            inside_sign = True
            record = _n46_json.loads(payload)
            hint = service.hint(record)
            # The producer knows its would-be event before COMMIT. It is not evidence yet.
            hint['event'] = dict(record, watermark=record['seq'], **coords)
            service.notify(hint)
            result = service.run_once(timeout=0)
            premature.append(result['outcome'] != 'missing_evidence')
            result = sign(payload)
            inside_sign = False
            return result

        start = len(observed)
        result = service.execute(writer, cmd, 'journal', guarded_sign, 1)
        pending = service.metrics()['pending']
        receipt = service.run_once(timeout=0)
        seen = observed[start:]
        ac1 = ac1 and pending == 1 and receipt is not None and receipt['outcome'] == 'delivered'
        ac1 = ac1 and {name for name, _, _ in seen} == {kind, 'pm'}
        ac1 = ac1 and all(row == (result['command_id'], result['record_digest']) for _, _, row in seen)
        ac1 = ac1 and all(event['watermark'] == result['seq'] for _, event, _ in seen)
        service.execute(writer, cmd, 'journal', sign, 1)
        ac1 = ac1 and service.metrics()['pending'] == 0  # identical store retry is not a new commit
    ac1 = ac1 and premature == [False] * len(expected_kinds)
    # A refused transaction must not leave delivery work behind.
    invalid = command('settlement')
    invalid['expected_versions'] = {'missing-unit': 0}
    try:
        service.execute(writer, invalid, 'journal', sign, 1)
        ac1 = False
    except store.StoreRefused:
        ac1 = ac1 and service.metrics()['pending'] == 0
    for payload, signature in signed:
        signature_file = directory / 'record.sig'
        signature_file.write_bytes(signature)
        verified = _n46_subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(allowed), '-I', 'journal',
                                        '-n', 'veldo-journal', '-s', str(signature_file)],
                                       input=payload, capture_output=True)
        ac1 = ac1 and verified.returncode == 0
    try:
        delivery.Delivery(store, str(path), coords, expected_enabled, {'settlement': handler('settlement')})
        ac1 = False
    except delivery.Refused as exc:
        ac1 = ac1 and exc.reason == 'invalid_registration'
    minimal = delivery.Delivery(store, str(path), coords, expected_enabled[:5],
                                {name: handler(name) for name in expected_enabled[:5]})
    ac1 = ac1 and set(minimal.inventory()) == {(kind, kind) for kind in expected_enabled[:5]}
    minimal.close()

    # Existing committed identities, invented identities, altered watermarks and foreign coordinates
    # go through the same transport queue for every enabled consumer, including the optional two.
    ac3 = True
    for kind in expected_kinds:
        result = service.execute(writer, command(kind), 'journal', sign, 1)
        service.run_once(timeout=0)
        hint = service.hint(result)
        for field, value, reason in [('command_id', 'invented-event', 'stale_subject'),
                                     ('record_digest', 'invented-digest', 'stale_subject'),
                                     ('watermark', 99999, 'missing_evidence'),
                                     ('domain_uuid', 'foreign-domain', 'missing_authority'),
                                     ('repository_uuid', 'foreign-repository', 'missing_authority'),
                                     ('store_uuid', 'foreign-store', 'missing_authority')]:
            before = len(observed)
            service.notify(dict(hint, **{field: value}, event={'arbitrary': 'untrusted-payload'}))
            refusal = service.run_once(timeout=0)
            ac3 = ac3 and len(observed) == before and refusal['outcome'] == reason
        # A genuine hint with forged data must still deliver exactly what the journal stored.
        before = len(observed)
        service.notify(dict(hint, transition={'fake': {'kind': 'completion'}}, principal='invented'))
        receipt = service.run_once(timeout=0)
        ac3 = ac3 and receipt['consumers'] == [kind, 'pm']
        ac3 = ac3 and all(event['principal'] == 'journal' and 'fake' not in event['transition']
                          for _, event, _ in observed[before:])
        ac3 = ac3 and receipt['accepted_input_versions'] == result['after_versions']
    # Reservation commits are budget events too, even without an entity transition.
    reservation = command('budget')
    reservation.update(operation='reserve', parameters=dict(reservation_id='hold', ceiling='unit', delta=1),
                       expected_versions={})
    service.execute(writer, reservation, 'journal', sign, 1)
    receipt = service.run_once(timeout=0)
    ac3 = ac3 and receipt is not None and receipt['consumers'] == ['budget', 'pm']
    # Handler mutation cannot alter the next consumer's authoritative input.
    service.handlers['settlement'] = lambda event: event['transition'].clear()
    before = len(observed)
    service.execute(writer, command('settlement'), 'journal', sign, 1)
    service.run_once(timeout=0)
    ac3 = ac3 and bool(observed[before:]) and bool(observed[-1][1]['transition'])
    service.handlers['settlement'] = handler('settlement')
    ac3 = ac3 and 'untrusted-payload' not in _n46_json.dumps(service.observations)
    ac3 = ac3 and service.metrics()['pending'] == 0 and service.metrics()['refused'] >= 36

    # Real event-loop barriers, not sleeps hoping to hit the race. The first barrier is
    # immediately before taking the idle lock; the other is Condition.wait's lock release.
    ac2 = True
    for order in ('before-lock', 'after-wait'):
        entered, proceed, waiting = (_n46_threading.Event() for _ in range(3))
        completed = _n46_threading.Event()
        wait_with_pending, errors, outcomes = [], [], []
        reading = []

        class Reader:
            sqlite3, StoreRefused = store.sqlite3, store.StoreRefused

            def open_store(self, *args, **kwargs):
                reading.append(True)
                return store.open_store(*args, **kwargs)

            execute = staticmethod(store.execute)

        loop = delivery.Delivery(Reader(), str(path), coords, ['completion'], {'completion': handler('completion')})

        class Boundary(_n46_threading.Condition):
            def __enter__(self):
                if order == 'before-lock' and _n46_threading.current_thread().name == 'notification-loop' and not entered.is_set():
                    entered.set()
                    proceed.wait(3)
                return super().__enter__()

            def wait(self, timeout=None):
                wait_with_pending.append(bool(loop._queue))
                waiting.set()
                return super().wait(timeout)

        loop._condition = Boundary()

        def consume():
            try:
                outcomes.append(loop.run_once(timeout=1))
            except Exception as exc:
                errors.append(type(exc).__name__)
            finally:
                completed.set()

        thread = _n46_threading.Thread(target=consume, name='notification-loop')
        thread.start()
        barrier = entered if order == 'before-lock' else waiting
        reached = barrier.wait(3)
        ac2 = ac2 and reached and not reading
        if order == 'after-wait':
            ac2 = ac2 and not completed.wait(0.02) and not reading
        result = loop.execute(writer, command('completion'), 'journal', sign, 1)
        proceed.set()
        delivered = completed.wait(2)
        loop.close()
        thread.join(3)
        ac2 = ac2 and delivered and not thread.is_alive() and not errors and not any(wait_with_pending)
        ac2 = ac2 and len(outcomes) == 1 and outcomes[0] is not None and outcomes[0]['outcome'] == 'delivered'
        ac2 = ac2 and len(reading) == 1 and loop.metrics()['pending'] == 0
    # Ordinary absence and handler uncertainty are named; neither is a success.
    unavailable = delivery.Delivery(store, str(directory / 'missing.sqlite3'), coords,
                                    ['completion'], {'completion': handler('completion')})
    unavailable.notify(service.hint(result))
    ac3 = ac3 and unavailable.run_once(timeout=0)['outcome'] == 'service_unavailable'
    unavailable.close()
    def uncertain(event):
        raise RuntimeError('private diagnostic must not enter observations')
    service.handlers['completion'] = uncertain
    service.execute(writer, command('completion'), 'journal', sign, 1)
    stopped = service.run_once(timeout=0)
    ac3 = ac3 and stopped is not None and stopped['outcome'] == 'unknown_outcome' and not stopped['accepted']
    ac3 = ac3 and 'private diagnostic' not in _n46_json.dumps(service.observations)
    service.close()
    writer.close()
    return ac1, ac2, ac3


_n46_started = _n46_time.monotonic()
with _n46_tempfile.TemporaryDirectory(prefix='v46-') as _n46_dir:
    _n46_results = _n46_checks(_n46_Path(_n46_dir))
for _n46_name, _n46_result in zip(('committed-event', 'event-in-the-gap', 'fabricated-event'), _n46_results):
    expect('VELDO-0046 notify/' + _n46_name, _n46_result)
print('VELDO-0046 suite seconds: %.3f' % (_n46_time.monotonic() - _n46_started))
