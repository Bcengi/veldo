"""Journal-woken serial dispatcher. It computes no containment and runs no git.

Each child opens its own store connection. A lock survives a service restart while its old
child finishes, so a replacement service cannot run a second remover beside it. The output
pipe is drained by the service poll set. A failed worker leaves the record for the next
journal advance or start; it is never retried by a timer.

The child closes what the service holds and it must not keep: the descriptors and connections
`held` names (the service's lock, listeners, pipes and store, and the store connections of its
channel and its API), this dispatcher's own pipe and its process descriptors. It closes nothing else: a descriptor the service did not open (one a
supervisor or a test harness handed down) is not the child's to close.

A session ended record whose client is still alive is not dropped. The worker leaves its
scratch deferred (rule 3) and names it in the record's result; this dispatcher then holds a
process descriptor of that client in the service poll set. The kernel makes it readable when
the client ends, and that writes one more session ended record for the same session, which is
consumed like any other. Nothing reads a clock and nothing polls. The kernel reports the end
before the client's parent has collected it; the worker judges the client as exited from then
(state Z in its stat, with the recorded start time), so the scratch does not wait for the parent.
"""
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import stat


def _organ(name):
    spec = importlib.util.spec_from_file_location('space_consumer_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WORKER = _organ('control_space_worker')


class Consumer:
    def __init__(self, ledger, given=None, landing=None, observe=None, held=None):
        self.ledger, self.given, self.landing = ledger, dict(given or {}), landing
        self.observe = observe or (lambda answer: None)
        self.held = held or (lambda: ())
        self.active, self.buffer = None, b''
        self.reconcile = None
        self.head, self.dispatched = 0, None
        self.watched = {}

    def pipes(self):
        found = {descriptor: watch['process']['pid'] for descriptor, watch in self.watched.items()}
        if self.active:
            found[self.active[0]] = self.active[1]
        return found

    def start(self, replay=None, reconcile=None):
        self.reconcile = reconcile
        self._rearm()
        if replay is not None:
            self._spawn(replay)
        else:
            self.advance()

    def advance(self):
        if self.active or self.ledger.conn.in_transaction:
            return
        pending = [identity for identity, record in self.ledger.events() if record['state'] == 'received']
        if pending:
            self._spawn()
        elif self.reconcile is not None:
            reconcile, self.reconcile = self.reconcile, None
            self._spawn(reconcile)

    def _spawn(self, task=None):
        if self.active:
            return
        ledger = self.ledger
        self.head = ledger.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        self.dispatched = next((identity for identity, record in ledger.events()
                                if record['state'] == 'received'), None) if task is None else None
        path = ledger.conn.execute('PRAGMA database_list').fetchone()[2]
        if not path:
            raise ValueError('the space worker needs a durable store')
        read, write = os.pipe()
        pid = os.fork()
        if pid:
            os.close(write)
            os.set_blocking(read, False)
            self.active, self.buffer = (read, pid), b''
            return
        answer = {'ok': False}
        try:
            registry = dict(ledger.conn.command_registry)
            ledger.conn.close()
            # No listener, lock, launch pipe or database handle of the service outlives it here. Only
            # what the service holds is closed, never every inherited descriptor.
            for one in [read] + list(self.watched) + list(self.held()):
                try:
                    if type(one) is int:
                        if one > 2 and one != write:
                            os.close(one)
                    elif one is not None:
                        one.close()
                except Exception:  # noqa: BLE001 - one that is closed already is closed
                    pass
            root = ledger.state_root
            if os.path.realpath(root) != root:
                raise ValueError('the state root traverses a link')
            lock = os.open(os.path.join(root, 'space-worker.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            info = os.fstat(lock)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise ValueError('unsafe space worker lock')
            fcntl.flock(lock, fcntl.LOCK_EX)
            ledger.conn = ledger.store.open_store(path)
            ledger.conn.command_registry.update(registry)
            if task is not None:
                task()
                answer = {'ok': True}
            else:
                # Read again under the lock: an older service's child may have just consumed it.
                pending = [identity for identity, record in ledger.events() if record['state'] == 'received']
                answer = WORKER.consume(ledger, pending[0], self.given, self.landing) if pending else {'ok': True}
            ledger.conn.close()
        except BaseException as error:
            answer = {'ok': False, 'reason': type(error).__name__, 'detail': str(error)[:500]}
        try:
            os.write(write, json.dumps(answer).encode()[:4096])
        except OSError:
            pass
        os._exit(0 if answer.get('ok') else 1)

    def _rearm(self):
        """At start: every scratch a session ended record left deferred behind a live client."""
        if self.ledger.conn.in_transaction:
            return
        for identity, item in sorted(self.ledger.items().items()):
            deferral = item.get('deferral') or {}
            origin = (deferral.get('emitter') or {}).get('event_record')
            if (item['kind'] != 'scratch' or item['state'] != 'deferred'
                    or deferral.get('refused_by') != 'owner_live' or not origin):
                continue
            record = self.ledger.event_record(origin)
            if record is not None and record['type'] == 'session_ended':
                self._watch(origin, record, identity)

    def _watch(self, origin, record, item):
        """Hold the client of a session ended record by a process descriptor until it ends."""
        subject = record['subject']
        process = {'pid': subject['pid'], 'started': subject['started']}
        if any(watch['process'] == process for watch in self.watched.values()):
            return
        proc = self.given.get('proc') or '/proc'
        watch = {'origin': origin, 'subject': dict(subject), 'process': process, 'item': item}
        try:
            descriptor = os.pidfd_open(process['pid'])
        except ProcessLookupError:
            descriptor = None
        except (OSError, AttributeError) as error:
            self.observe({'ok': False, 'reason': 'space_client_unwatched', 'event': origin, 'item': item,
                          'detail': str(error)[:500]})
            return
        # The descriptor is held first: the number cannot be handed to another process after this look.
        seen = WORKER.PROBE.process(process['pid'], proc)
        if descriptor is not None and seen is not None and seen['live'] and seen['start'] == process['started']:
            self.watched[descriptor] = watch
            return
        if descriptor is not None:
            os.close(descriptor)
        if WORKER._ended(process, proc):
            self._exited(watch)
        else:
            self.observe({'ok': False, 'reason': 'space_client_unwatched', 'event': origin, 'item': item,
                          'detail': 'the recorded process cannot be read'})

    def _exited(self, watch):
        """The client's exit is an event record of its own, consumed once like a hook's."""
        answer = self.ledger.event('session_ended', watch['subject'],
                                   {'hook': 'client-exit', 'host': self.ledger.host, 'after': watch['origin']})
        self.observe(dict(answer, client_exit=watch['origin'], item=watch['item']))

    def readable(self, descriptor):
        if descriptor in self.watched:
            watch = self.watched.pop(descriptor)
            os.close(descriptor)
            self._exited(watch)
            self.advance()
            return
        if not self.active or descriptor != self.active[0]:
            return
        try:
            chunk = os.read(descriptor, 4096)
        except BlockingIOError:
            return
        if chunk:
            self.buffer += chunk
            return
        _read, pid = self.active
        os.close(descriptor)
        _pid, status = os.waitpid(pid, 0)
        self.active = None
        try:
            answer = json.loads(self.buffer)
        except ValueError:
            answer = {'ok': False, 'reason': 'space_worker_lost'}
        self.observe(dict(answer, worker=pid, status=status))
        record = self.ledger.event_record(self.dispatched) if self.dispatched is not None else None
        finished = record is None or record['state'] == 'consumed'
        if record is not None and finished and record['type'] == 'session_ended':
            for one in (record['result'] or {}).get('held') or ():
                if one.get('why') == 'client_alive':
                    self._watch(self.dispatched, record, one.get('item'))
        if status == 0 and answer.get('ok') and finished:
            self.advance()
