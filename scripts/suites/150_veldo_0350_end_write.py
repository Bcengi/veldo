"""VELDO-0350: the write that records a dispatch's end, and the receiver's exit status.

Run: python3 scripts/selftest.py --suite 150_veldo_0350_end_write

Only shared ROOT, expect and fast_temp are consumed. One temporary tree holds the installed .veldo copy
with control_dispatch.py and control_launch.py laid over it; the suite loads the launch module from that
tree and uses the dispatch module and the store it loaded, and the receiver processes of the AC3 rows
execute that same copy, so a registered mutation of either module reaches both. The store is a real one.
The runner's stop bookkeeping is the runner's own: Runner.honor_stops, which asks the launch it holds and
writes stop_result through its own Dispatches.

THE CASE (the review of the item naming, finding F2). The receiver's end write reads the record's version
and then sends its command with that version. The runner's sweep writes the record of its stop ask on the
same record. When that record commits between the receiver's read and its command, the command is stale.
The review showed it with two delays put into the code (one after the versions are read, for the exit
only; one in the runner between the ask and its record). Here the same order is made without a clock:
the receiver's Dispatches is given a store whose execute, as the receiver's command arrives and before
the real store sees it, lets the runner's sweep run to its end. Everything else is the real store.

AC1 rows: ac1/exit-after-the-stop-record (the case: a running dispatch with an owner's stop request; the
runner's sweep records its ask between the receiver's read and its exit command; the exit is recorded,
the record ends exited with the termination given, the stop request keeps its result, and the unit and
station are released), ac1/unknown-and-refuse-after-the-stop-record (the same for the two other writes
that record an end: unknown from running, refuse from accepted), ac1/other-writes-refused-as-before (a
write that records no end, the run of an accepted dispatch, with the stop record landing the same way: it
is refused stale_version, sent once, and the record is as the stop record left it).

AC2 rows: ac2/never-two-ends (another writer's end, the unknown the runner writes for a receiver it has
ended, lands between the receiver's read and its exit command: the receiver sends one command and no
other, it is refused stale_version, and the record shows one end, the runner's; the same exit delivered
again after it committed writes nothing; a different exit after the end is refused by the transition),
ac2/retry-is-bounded (a record that moves before every command of the receiver: the write is sent
END_RETRIES times after its first, then refused stale_version; the record shows no end).

AC3 rows, each a real process running the launch module's own main(): ac3/failed-without-an-end (the end
write is refused, as it was in the case before this ticket: main reports failed and exits with
END_UNRECORDED, the record still running; a receiver that could not read its configuration does the
same), ac3/zero-with-an-end (a receiver that fails after its end was recorded reports failed and exits 0;
one that ends cleanly reports no failure and exits 0).

FIX 2 ROW (the review of 6e0b807b, finding 5): f2/unrecorded-before-running (a dispatch whose record is
accepted, not yet running: a receiver that exits END_UNRECORDED there is recorded unknown with the reason
launch_evidence_missing:end_unrecorded; one that ended with another status and one the runner killed are
recorded launch_evidence_missing as before; the real receiver started by invoke is recorded the first way).

paths/canon: the engine canon equals this repository's copies.

STAND-INS. The dispatch records are fixture records, written whole in the state the receiver's own run
(or accept) write leaves, with an owner's stop request waiting: prepare, accept and run need the
reservation and the claim, which are not this ticket's. The members are fixture records. The journal
signer is a function. The launch the runner holds answers that it asked. In the AC3 rows the Receiver
class is a stand-in that opens the store and holds the receiver's own Dispatches, as the real one does;
its launch does one of three things: sends the real exit over a store whose record moves before every
command (the end write refused), records the exit and then fails, or records the exit and reports it.
main(), end_recorded, the exit status and the dispatch module are the real ones.
"""


def _v350_end_write_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
    }
    ROWS = ('ac1/exit-after-the-stop-record', 'ac1/unknown-and-refuse-after-the-stop-record',
            'ac1/other-writes-refused-as-before',
            'ac2/never-two-ends', 'ac2/retry-is-bounded',
            'ac3/failed-without-an-end', 'ac3/zero-with-an-end',
            'f1/launch-records-the-status', 'f1/receiver-errors-in-the-log',
            'f2/unrecorded-before-running',
            'paths/canon')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def exercise(base):
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        L = load('v350_launch', mods / 'control_launch.py')
        D, S = L.D, L.S  # the dispatch module and the store the launch module itself loaded
        DOMAIN, REPOSITORY = 'domain-350', 'repository-350'
        db = base / 'authority' / 'control.sqlite3'
        db.parent.mkdir(mode=0o700)
        writer = S.open_store(str(db))
        serial = [0]

        def sign(message):
            return 'stub:' + S.digest_of(message.decode('utf-8'))

        def entity(identity):
            row = writer.execute('SELECT kind, version, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)

        for principal in ('runner', 'launch-receiver'):
            put(principal, 'membership', dict(principal_type='service', roles=['reservation_service'],
                                              scope=[REPOSITORY], revoked_at=None, expires_at=None))
        PROCESS = {'platform': 'linux', 'host': 'fixture-host', 'boot_id': 'boot-350', 'pid': 4350, 'start': '77'}
        TERMINATION = {'returncode': -15, 'signal': 15, 'output_digest': 'sha256:' + 'a' * 64, 'output_bytes': 0,
                       'deadline_stop': False}

        def planted(name, state='running'):
            """A dispatch record as the receiver's own run write leaves it (or its accept write, for
            `accepted`), holding its unit and station, with an owner's stop request waiting for its ask."""
            dispatch_id = 'dispatch/' + name
            contract = {'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'domain': DOMAIN, 'repository': REPOSITORY,
                        'unit': 'VELDO-93' + name[-2:], 'station': 'build', 'attempt': 1}
            history = [{'action': action, 'at': 1.0, 'principal': who, 'state': reached}
                       for action, who, reached in (('prepare', 'runner', 'prepared'),
                                                    ('accept', 'launch-receiver', 'accepted'),
                                                    ('run', 'launch-receiver', 'running'))
                       if state == 'running' or reached != 'running']
            put(D.record_id(dispatch_id), D.RECORD_KIND, {
                'schema': D.SCHEMA, 'dispatch_id': dispatch_id, 'state': state, 'contract': contract,
                'contract_digest': D.digest(contract), 'receiver': dict(PROCESS, pid=4349, principal='launch-receiver'),
                'process': PROCESS if state == 'running' else None, 'termination': None, 'refusal': None,
                'stop': None, 'reason': None, 'history': history,
                'stop_request': {'by': 'owner-person', 'at': 2.0, 'request': 'stop-' + name, 'reason': 'owner_stop',
                                 'channel': 'api', 'assertion_digest': None, 'result': None}})
            put(D.index_id(DOMAIN, REPOSITORY, contract['unit'], 'build'), D.INDEX_KIND, {
                'domain': DOMAIN, 'repository': REPOSITORY, 'unit': contract['unit'], 'station': 'build',
                'dispatch_id': dispatch_id, 'attempts': 1})
            return dispatch_id, contract

        def version(dispatch_id):
            return entity(D.record_id(dispatch_id))['version']

        def record(dispatch_id):
            return entity(D.record_id(dispatch_id))['data']

        def holder(contract):
            return entity(D.index_id(DOMAIN, REPOSITORY, contract['unit'], 'build'))['data'].get('dispatch_id')

        def ends(dispatch_id):
            return [(h['action'], h['principal']) for h in record(dispatch_id)['history']
                    if h['action'] in ('exit', 'refuse', 'unknown')]

        running = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner', signer='runner',
                               sign=sign)

        class Asked:
            """The launch the runner holds: its receiver was asked to stop."""
            @staticmethod
            def stop(reason):
                return True

        def sweep(dispatch_id):
            """The runner's own sweep of stop requests, holding the launch of `dispatch_id`."""
            made = object.__new__(L.Runner)
            made.dispatches, made.launches, made.observations, made.clock = running, {dispatch_id: Asked}, [], time.time
            return made.honor_stops()

        class Between:
            """The store the receiver's Dispatches is given. Its execute is the real store's; before each
            of the receiver's commands reaches it, and so after the receiver read the versions, `inside`
            runs: every time when `always`, else once. `sent` counts the receiver's commands."""
            def __init__(self, inside, always=False):
                self.inside, self.always, self.sent, self.did = inside, always, 0, []

            def __getattr__(self, name):
                return getattr(S, name)

            def execute(self, conn, command, *given):
                self.sent += 1
                if self.inside is not None and (self.always or self.sent == 1):
                    self.did.append(self.inside())
                return S.execute(conn, command, *given)

        def receiver(inside, always=False):
            store, events = Between(inside, always), []
            made = D.Dispatches(store, writer, domain=DOMAIN, repository=REPOSITORY, principal='launch-receiver',
                                signer='launch-receiver', sign=sign, observe=events.append)
            return made, store, events

        def attempt(call):
            try:
                return ('ok', call())
            except D.Refused as error:
                return ('refused', error.code)

        def outcomes(events):
            return [event.get('outcome') for event in events]

        # ---- AC1 ------------------------------------------------------------------------------------
        R = 'ac1/exit-after-the-stop-record'
        dispatch_id, contract = planted('race-01')
        read = version(dispatch_id)
        receiving, store, events = receiver(lambda: sweep(dispatch_id))
        answer = attempt(lambda: receiving.exit(dispatch_id, D.digest(contract), PROCESS, TERMINATION, now=time.time()))
        after = record(dispatch_id)
        check(R, 'the runner\'s sweep asked the receiver and recorded the ask between the receiver\'s read of the '
                 'record and its exit command: the record moved by that one write [%s]' % (store.did,),
              store.did == [[(dispatch_id, True)]]
              and [h['action'] for h in after['history']][3:4] == ['stop_result'])
        check(R, 'the exit is recorded: the write answers with the record, ended exited [%s %s]'
              % (answer[0], answer[1] if answer[0] == 'refused' else answer[1].get('state')),
              answer[0] == 'ok' and answer[1].get('state') == 'exited' and after['state'] == 'exited')
        check(R, 'with the termination given and the process the run recorded, one end in its history, the '
                 'receiver\'s, after the runner\'s stop record [%s]' % ([h['action'] for h in after['history']],),
              after['termination'] == TERMINATION and after['process'] == PROCESS
              and ends(dispatch_id) == [('exit', 'launch-receiver')]
              and [h['action'] for h in after['history']][3:] == ['stop_result', 'exit']
              and version(dispatch_id) == read + 2)
        check(R, 'the stop request keeps the result the runner wrote, and the unit and station are released [%s %s]'
              % ((after.get('stop_request') or {}).get('result'), holder(contract)),
              ((after.get('stop_request') or {}).get('result') or {}).get('asked') is True
              and holder(contract) is None)
        check(R, 'the receiver sent its command twice, the second with the versions read again, and observed one '
                 'retry and one acceptance [%s %s]' % (store.sent, outcomes(events)),
              store.sent == 2 and outcomes(events) == ['retried', 'accepted']
              and events[0].get('refusal') == 'stale_version'
              and events[1]['accepted_versions'][D.record_id(dispatch_id)] == read + 1
              and receiving.counts == {'accepted': 1, 'refused': 0})

        R = 'ac1/unknown-and-refuse-after-the-stop-record'
        dispatch_id, contract = planted('race-02')
        receiving, store, events = receiver(lambda: sweep(dispatch_id))
        answer = attempt(lambda: receiving.unknown(dispatch_id, D.digest(contract), 'containment_not_empty',
                                                   now=time.time(), expected_state='running'))
        after = record(dispatch_id)
        check(R, 'an unknown outcome written after the stop record landed the same way is recorded, once, and the '
                 'unit and station stay held [%s %s %s]' % (answer[0], after['state'], ends(dispatch_id)),
              answer[0] == 'ok' and after['state'] == 'unknown' and after['reason'] == 'containment_not_empty'
              and ends(dispatch_id) == [('unknown', 'launch-receiver')] and store.sent == 2
              and store.did == [[(dispatch_id, True)]] and holder(contract) == dispatch_id)
        dispatch_id, contract = planted('race-03', state='accepted')
        receiving, store, events = receiver(lambda: sweep(dispatch_id))
        answer = attempt(lambda: receiving.refuse(dispatch_id, D.digest(contract), 'spawn_failed:ENOENT',
                                                  now=time.time(), expected_state='accepted'))
        after = record(dispatch_id)
        check(R, 'a refusal written for an accepted dispatch after the stop record landed the same way is recorded, '
                 'once, and the unit and station are released [%s %s %s]' % (answer[0], after['state'], ends(dispatch_id)),
              answer[0] == 'ok' and after['state'] == 'refused' and after['refusal'] == 'spawn_failed:ENOENT'
              and ends(dispatch_id) == [('refuse', 'launch-receiver')] and store.sent == 2
              and store.did == [[(dispatch_id, True)]] and holder(contract) is None)

        R = 'ac1/other-writes-refused-as-before'
        dispatch_id, contract = planted('race-04', state='accepted')
        read = version(dispatch_id)
        receiving, store, events = receiver(lambda: sweep(dispatch_id))
        answer = attempt(lambda: receiving.run(dispatch_id, D.digest(contract), PROCESS, now=time.time()))
        after = record(dispatch_id)
        check(R, 'a write that records no end, the run of an accepted dispatch, is refused stale_version when the '
                 'stop record lands between its read and its command, and is sent once [%s %s %s]'
              % (answer, store.sent, outcomes(events)),
              answer == ('refused', 'stale_version') and store.sent == 1 and outcomes(events) == ['refused']
              and store.did == [[(dispatch_id, True)]])
        check(R, 'the record is as the stop record left it: accepted, no process, one version on [%s]'
              % (after['state'],),
              after['state'] == 'accepted' and after['process'] is None and version(dispatch_id) == read + 1
              and [h['action'] for h in after['history']][-1] == 'stop_result')

        # ---- AC2 ------------------------------------------------------------------------------------
        R = 'ac2/never-two-ends'
        dispatch_id, contract = planted('ended-05')
        read = version(dispatch_id)

        def runner_ends():
            # What Launch.wait writes for a receiver it has ended while the record says running.
            return running.unknown(dispatch_id, D.digest(contract), 'outcome_unknown', now=time.time(),
                                   expected_state='running').get('state')
        receiving, store, events = receiver(runner_ends)
        answer = attempt(lambda: receiving.exit(dispatch_id, D.digest(contract), PROCESS, TERMINATION, now=time.time()))
        after = record(dispatch_id)
        check(R, 'another writer\'s end landed between the receiver\'s read and its exit command: the runner '
                 'recorded the dispatch unknown [%s]' % (store.did,), store.did == ['unknown'])
        check(R, 'the receiver, reading the record again, finds an end and sends nothing more: one command, '
                 'refused stale_version, no retry observed [%s %s %s]' % (answer, store.sent, outcomes(events)),
              answer == ('refused', 'stale_version') and store.sent == 1 and outcomes(events) == ['refused']
              and receiving.counts == {'accepted': 0, 'refused': 1})
        check(R, 'the record shows one end, the runner\'s: unknown, no termination, one version on, the unit and '
                 'station held [%s %s]' % (after['state'], ends(dispatch_id)),
              after['state'] == 'unknown' and after['termination'] is None
              and ends(dispatch_id) == [('unknown', 'runner')] and version(dispatch_id) == read + 1
              and holder(contract) == dispatch_id)
        dispatch_id, contract = planted('ended-06')
        receiving, store, events = receiver(None)
        now = time.time()
        first = attempt(lambda: receiving.exit(dispatch_id, D.digest(contract), PROCESS, TERMINATION, now=now))
        at = version(dispatch_id)
        again = attempt(lambda: receiving.exit(dispatch_id, D.digest(contract), PROCESS, TERMINATION, now=now))
        other = attempt(lambda: receiving.exit(dispatch_id, D.digest(contract), PROCESS,
                                               dict(TERMINATION, returncode=0, signal=None), now=now + 1))
        check(R, 'the same exit delivered again after it committed writes nothing, and a different exit after the '
                 'end is refused by the transition: one end in the history, the version unchanged [%s %s %s %s]'
              % (first[0], again[0], other, ends(dispatch_id)),
              first[0] == 'ok' and again[0] == 'ok' and again[1].get('state') == 'exited'
              and other == ('refused', 'transition_refused:exited:exit')
              and ends(dispatch_id) == [('exit', 'launch-receiver')] and version(dispatch_id) == at
              and record(dispatch_id)['termination'] == TERMINATION)

        R = 'ac2/retry-is-bounded'
        dispatch_id, contract = planted('moving-07')
        read = version(dispatch_id)
        LIMIT = D.END_RETRIES + 4

        def moves():
            # The record moves before every command; after LIMIT commands it stops, so a write that
            # never gave up would end here and the row would say how many it sent.
            if store.sent > LIMIT:
                return None
            data = record(dispatch_id)
            put(D.record_id(dispatch_id), D.RECORD_KIND, dict(data, touched=store.sent))
            return store.sent
        receiving, store, events = receiver(moves, always=True)
        answer = attempt(lambda: receiving.exit(dispatch_id, D.digest(contract), PROCESS, TERMINATION, now=time.time()))
        after = record(dispatch_id)
        check(R, 'a record that moves before every command of the receiver: the exit is sent END_RETRIES times after '
                 'its first and then refused stale_version [%s %s of %s]' % (answer, store.sent, 1 + D.END_RETRIES),
              answer == ('refused', 'stale_version') and D.END_RETRIES >= 2 and store.sent == 1 + D.END_RETRIES
              and outcomes(events) == ['retried'] * D.END_RETRIES + ['refused']
              and [event.get('attempt') for event in events[:-1]] == list(range(1, D.END_RETRIES + 1)))
        check(R, 'the record shows no end and holds its unit and station: running, moved only by the other writer '
                 '[%s %s]' % (after['state'], version(dispatch_id) - read),
              after['state'] == 'running' and ends(dispatch_id) == [] and after['termination'] is None
              and version(dispatch_id) == read + 1 + D.END_RETRIES and holder(contract) == dispatch_id)

        # ---- AC3: the launch module's own main(), in a process of its own ----------------------------
        driver = base / 'drive_main.py'
        driver.write_text('''"""Run the launch module's own main() with a stand-in Receiver (the suite's STAND-INS)."""
import importlib.util, json, sys
mods, mode, config_path = sys.argv[1:4]
spec = importlib.util.spec_from_file_location('v350_receiver_launch', mods + '/control_launch.py')
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
D, S = L.D, L.S
PROCESS = %(process)r
TERMINATION = %(termination)r


def sign(message):
    return 'stub:' + S.digest_of(message.decode('utf-8'))


class Moving:
    """A store whose dispatch record moves before each of its first forty commands: each end write
    is stale."""
    def __init__(self, conn):
        self.conn, self.serial = conn, 0

    def __getattr__(self, name):
        return getattr(S, name)

    def execute(self, conn, command, *given):
        identity = D.record_id(command['parameters']['dispatch_id'])
        version, data = self.conn.execute('SELECT version, data FROM entities WHERE id=?', (identity,)).fetchone()
        self.serial += 1
        if self.serial > 40:  # a write that never gave up ends here, and the row says what it found
            return S.execute(conn, command, *given)
        name = 'moving-%%s-%%d' %% (identity, self.serial)  # one per dispatch: two receivers use this store
        S.execute(self.conn, dict(command_id=name, principal='owner', operation='upsert_entity',
                                  nonce=name, artifact_digests=[], expected_versions={identity: version},
                                  parameters=dict(entity_id=identity, kind=D.RECORD_KIND,
                                                  data=dict(json.loads(data), touched=self.serial))), 'owner', sign, 1)
        return S.execute(conn, command, *given)


class Receiver:
    def __init__(self, config, emit, control=None):
        self.conn, self.emit = S.open_store(config['store']), emit
        self.dispatches = D.Dispatches(Moving(self.conn) if mode == 'stale' else S, self.conn, domain=config['domain'],
                                       repository=config['repository'], principal=config['principal'],
                                       signer=config['principal'], sign=sign)

    def launch(self, contract):
        self.dispatches.exit(contract['dispatch_id'], D.digest(contract), PROCESS, TERMINATION, now=1000.0)
        if mode == 'late':
            raise OSError('the report of a recorded end failed')
        self.emit({'event': 'exited'})

    def close(self):
        self.conn.close()


if mode != 'real':
    L.Receiver = Receiver
sys.argv = [mods + '/control_launch.py', config_path]
L.main()
''' % {'process': PROCESS, 'termination': TERMINATION})
        config = base / 'receiver.json'
        config.write_text(json.dumps({'store': str(db), 'domain': DOMAIN, 'repository': REPOSITORY,
                                      'principal': 'launch-receiver'}))

        def main(mode, contract, config_path=config):
            done = subprocess.run([sys.executable, '-B', str(driver), str(mods), mode, str(config_path)],
                                  input=(json.dumps({'contract': contract}) + '\n').encode(), capture_output=True,
                                  timeout=120, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            said = []
            for line in done.stdout.decode().splitlines():
                with contextlib.suppress(ValueError):
                    said.append(json.loads(line))
            return done.returncode, said, done.stderr.decode()[-300:]

        R = 'ac3/failed-without-an-end'
        dispatch_id, contract = planted('main-08')
        read = version(dispatch_id)
        code, said, error = main('stale', contract)
        after = record(dispatch_id)
        check(R, 'the end write was refused, as in the case before this ticket: the record still says running and '
                 'shows no end, moved only by the other writer [%s %s %s]' % (after['state'], ends(dispatch_id), error),
              after['state'] == 'running' and ends(dispatch_id) == []
              and version(dispatch_id) == read + 1 + D.END_RETRIES and holder(contract) == dispatch_id)
        check(R, 'main reports failed, naming the refusal, and does not end as a clean receiver does: it exits with '
                 'END_UNRECORDED [%s %s]' % (code, said),
              said == [{'event': 'failed', 'error': 'Refused'}] and L.END_UNRECORDED not in (0, None)
              and code == L.END_UNRECORDED)
        code, said, error = main('real', contract, config_path=base / 'no-such-receiver.json')
        check(R, 'the real receiver, given a configuration it cannot read, records nothing, reports failed and exits '
                 'with END_UNRECORDED too [%s %s]' % (code, said),
              said == [{'event': 'failed', 'error': 'FileNotFoundError'}] and code == L.END_UNRECORDED
              and record(dispatch_id)['state'] == 'running')

        R = 'ac3/zero-with-an-end'
        dispatch_id, contract = planted('main-09')
        code, said, error = main('late', contract)
        check(R, 'a receiver that fails after its end was recorded reports failed and exits 0: the record says '
                 'exited [%s %s %s %s]' % (code, said, record(dispatch_id)['state'], error),
              code == 0 and said == [{'event': 'failed', 'error': 'OSError'}]
              and record(dispatch_id)['state'] == 'exited' and ends(dispatch_id) == [('exit', 'launch-receiver')])
        dispatch_id, contract = planted('main-10')
        code, said, error = main('clean', contract)
        check(R, 'a receiver that ends cleanly reports no failure and exits 0 [%s %s %s]' % (code, said, error),
              code == 0 and said == [{'event': 'exited'}] and record(dispatch_id)['state'] == 'exited')
        states = {state: L.end_recorded(type('Held', (), {'dispatches': type('Records', (), {
            'record': staticmethod(lambda dispatch_id, state=state: {'state': state})})})(),
            {'contract': {'dispatch_id': 'dispatch/any'}}) for state in D.STATES}
        check(R, 'an end is one of exited, refused and unknown; prepared, accepted and running are none, and neither '
                 'is a record that is missing or a request that names no dispatch [%s]' % (states,),
              states == {'prepared': False, 'accepted': False, 'running': False, 'exited': True, 'refused': True,
                         'unknown': True}
              and L.end_recorded(None, {'contract': contract}) is False
              and L.end_recorded(type('Held', (), {'dispatches': running})(), {'contract': {}}) is False
              and L.end_recorded(type('Held', (), {'dispatches': running})(),
                                 {'contract': {'dispatch_id': 'dispatch/none'}}) is False)

        # ---- The fix after the review (F1): whoever starts the receiver keeps its exit status ---------
        R = 'f1/launch-records-the-status'
        records = base / 'records'

        def launched(argv, contract, feed=True):
            """The runner's end of a receiver process that is running `contract`'s dispatch: the real
            Launch, its standard error opened as invoke opens it."""
            errors, place = L._receiver_errors(str(records), contract['dispatch_id'])
            child = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors,
                                     env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            os.close(errors)
            made = L.Launch(child, dict(contract, deadline=time.time() + 600), running, time.time, records=str(records))
            made.receiver_log, made.result, made.record = place, 'accepted', record(contract['dispatch_id'])
            if feed:
                child.stdin.write((json.dumps({'contract': contract}) + '\n').encode())
                child.stdin.flush()
            return made

        def shown(made, dispatch_id):
            after = record(dispatch_id)
            return (made.returncode, after['state'], after['reason'], ends(dispatch_id))

        dispatch_id, contract = planted('kept-11')
        made = launched([sys.executable, '-B', str(driver), str(mods), 'stale', str(config)], contract)
        made.wait(timeout=120)
        refused = shown(made, dispatch_id)
        check(R, 'a receiver whose end write was refused after its retries exits END_UNRECORDED, and the launch keeps '
                 'that status [%s %s]' % (refused[0], made.messages),
              refused[0] == L.END_UNRECORDED and made.messages == [{'event': 'failed', 'error': 'Refused'}])
        check(R, 'the runner records the dispatch unknown once, and the record itself says the receiver left no end: '
                 'its reason is an unknown outcome and names end_unrecorded [%s]' % (refused[1:],),
              refused[1:] == ('unknown', L.END_UNRECORDED_REASON, [('unknown', 'runner')])
              and L.END_UNRECORDED_REASON.split(':')[0] == 'outcome_unknown'
              and L.END_UNRECORDED_REASON != 'outcome_unknown'
              and D.taxonomy(L.END_UNRECORDED_REASON) == 'unknown_outcome' and holder(contract) == dispatch_id)
        log = Path(made.receiver_log).read_text() if made.receiver_log else None
        check(R, 'the receiver\'s own words are in its log beside the run\'s execution record: the refusal and the '
                 'status [%s]' % (log,),
              made.receiver_log == L.receiver_log(str(records), dispatch_id)
              and os.path.dirname(made.receiver_log) == os.path.dirname(L.ER.path(str(records), dispatch_id))
              and log is not None and 'receiver failed: Refused stale_version' in log
              and 'no end (exit %d)' % L.END_UNRECORDED in log)
        dispatch_id, contract = planted('dead-12')
        made = launched([sys.executable, '-c', 'import time; time.sleep(600)'], contract, feed=False)
        made.wait(timeout=0.3)
        killed = shown(made, dispatch_id)
        dispatch_id, contract = planted('gone-13')
        made = launched([sys.executable, '-c', 'import sys; sys.exit(1)'], contract, feed=False)
        made.wait(timeout=60)
        gone = shown(made, dispatch_id)
        check(R, 'a silent receiver the runner had to kill, and one that ended with another status, are recorded '
                 'unknown as before, outcome_unknown: told apart from the one that said it left no end [%s %s]'
              % (killed, gone),
              killed[0] is not None and killed[0] < 0 and killed[1:] == ('unknown', 'outcome_unknown', [('unknown', 'runner')])
              and gone == (1, 'unknown', 'outcome_unknown', [('unknown', 'runner')]))
        dispatch_id, contract = planted('slow-14')
        made = launched([sys.executable, '-c', 'import os, sys, time; os.close(1); time.sleep(0.6); sys.exit(%d)'
                         % L.END_UNRECORDED], contract, feed=False)
        made.wait(timeout=60)
        slow = shown(made, dispatch_id)
        check(R, 'a receiver whose output ended before it exited is given its exit: its status is its own, never '
                 'the kill\'s [%s]' % (slow,),
              slow == (L.END_UNRECORDED, 'unknown', L.END_UNRECORDED_REASON, [('unknown', 'runner')]))
        dispatch_id, contract = planted('done-15')
        made = launched([sys.executable, '-B', str(driver), str(mods), 'clean', str(config)], contract)
        made.wait(timeout=120)
        clean = shown(made, dispatch_id)
        check(R, 'control: a receiver that recorded its end is not written over: exited, no reason, one end, the '
                 'receiver\'s [%s]' % (clean,),
              clean[1:] == ('exited', None, [('exit', 'launch-receiver')]))

        R = 'f1/receiver-errors-in-the-log'
        dispatch_id, contract = planted('real-16')
        real_config = base / 'receiver-real.json'
        real_config.write_text(json.dumps({'store': str(db), 'domain': DOMAIN, 'repository': REPOSITORY,
                                           'principal': 'launch-receiver', 'records': str(records)}))
        made = L.invoke(str(real_config), dict(contract, deadline=time.time() + 600), running, accept_seconds=60,
                        environment=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        made.wait(timeout=60)
        real = shown(made, dispatch_id)
        log = Path(made.receiver_log).read_text() if made.receiver_log and os.path.exists(made.receiver_log) else None
        check(R, 'invoke starts the real receiver with its standard error on the log beside the run\'s execution '
                 'record, a file of the owner alone, not on /dev/null [%s %s]' % (made.receiver_log, log),
              made.receiver_log == L.receiver_log(str(records), dispatch_id) and log is not None
              and os.stat(made.receiver_log).st_mode & 0o777 == 0o600
              and os.stat(str(records)).st_mode & 0o777 == 0o700)
        check(R, 'the real receiver, which could not launch with this configuration, wrote there why it failed and '
                 'the status it exits with, and the launch holds that status and recorded it [%s %s]'
              % (real, made.messages),
              log is not None and log.startswith('receiver failed: ') and 'no end (exit %d)' % L.END_UNRECORDED in log
              and real == (L.END_UNRECORDED, 'unknown', L.END_UNRECORDED_REASON, [('unknown', 'runner')]))
        blocked = base / 'blocked'
        blocked.write_text('a file where the records directory would be')
        unopened = L._receiver_errors(str(blocked), dispatch_id)
        check(R, 'a log that cannot be opened refuses no launch: no descriptor and no path are given [%s]' % (unopened,),
              unopened == (None, None))

        # ---- Fix 2 (the review of 6e0b807b, finding 5): the same before the record reaches running ----
        R = 'f2/unrecorded-before-running'

        def started(name, argv=None, accept_seconds=60):
            """A dispatch whose record is accepted, not yet running, and the runner's Launch.start over its
            receiver: a process given by `argv`, or the real receiver started by invoke."""
            dispatch_id, contract = planted(name, state='accepted')
            if argv is None:
                made = L.invoke(str(real_config), dict(contract, deadline=time.time() + 600), running,
                                accept_seconds=accept_seconds, environment=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            else:
                made = launched(argv, contract, feed=False)
                made.result = made.record = None
                made.start(accept_seconds)
            return made, shown(made, dispatch_id), holder(contract) == dispatch_id

        made, early, held = started('early-17', [sys.executable, '-c', 'import os, sys; os.close(1); sys.exit(%d)'
                                                 % L.END_UNRECORDED])
        check(R, 'a receiver that exits END_UNRECORDED before its record reaches running is recorded unknown once, '
                 'by the runner, and the reason names end_unrecorded: launch evidence missing, and the receiver said '
                 'so itself [%s %s]' % (early, made.result),
              early == (L.END_UNRECORDED, 'unknown', L.EVIDENCE_UNRECORDED_REASON, [('unknown', 'runner')])
              and made.result == 'unknown' and held
              and L.EVIDENCE_UNRECORDED_REASON == 'launch_evidence_missing:end_unrecorded'
              and D.taxonomy(L.EVIDENCE_UNRECORDED_REASON) == D.taxonomy('launch_evidence_missing') == 'unknown_outcome')
        made, gone, _held = started('gone-18', [sys.executable, '-c', 'import sys; sys.exit(1)'])
        made, killed, _held = started('dead-19', [sys.executable, '-c', 'import time; time.sleep(600)'], accept_seconds=0.3)
        check(R, 'a receiver that ended there with another status, and a silent one the runner had to kill, are '
                 'recorded as before, launch_evidence_missing with nothing after it: told apart [%s %s]' % (gone, killed),
              gone == (1, 'unknown', 'launch_evidence_missing', [('unknown', 'runner')])
              and killed[0] is not None and killed[0] < 0
              and killed[1:] == ('unknown', 'launch_evidence_missing', [('unknown', 'runner')]))
        made, real, held = started('real-20')
        log = Path(made.receiver_log).read_text() if made.receiver_log and os.path.exists(made.receiver_log) else None
        check(R, 'the real receiver, started by invoke on an accepted dispatch it cannot run, exits END_UNRECORDED '
                 'and the launch records that reason; its log says no end [%s %s %s]' % (real, made.result, log),
              real == (L.END_UNRECORDED, 'unknown', L.EVIDENCE_UNRECORDED_REASON, [('unknown', 'runner')])
              and made.result == 'unknown' and held
              and log is not None and 'no end (exit %d)' % L.END_UNRECORDED in log)
        writer.close()

        R = 'paths/canon'
        for name in PRODUCTION:
            check(R, 'the engine canon engine/.veldo/%s equals this repository copy' % name,
                  (ROOT / 'engine' / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes())

    try:
        with tempfile.TemporaryDirectory(prefix='v350-', dir=fast_temp()) as directory:
            exercise(Path(os.path.realpath(directory)))
    except Exception as error:  # noqa: BLE001 - a raise reds every row that did not finish, never skips it
        import traceback
        where = ' | '.join(line.strip() for line in traceback.format_exc().splitlines()[-6:])[:600]
        for name in ROWS:
            if not rows[name] or name == ROWS[-1]:
                check(name, 'ran to its end (raised %s: %s) %s' % (type(error).__name__, str(error)[:300], where), False)
    for name, observed in rows.items():
        failed = next((label for label, ok in observed if not ok), '' if observed else 'no check ran')
        expect('VELDO-0350 ' + name + (': ' + failed if failed else ''), bool(observed) and not failed)


_v350_end_write_suite()
