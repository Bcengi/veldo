"""Journal-woken serial dispatcher. It computes no containment and runs no git.

Each child opens its own store connection. A lock survives a service restart while its old
child finishes, so a replacement service cannot run a second remover beside it. The output
pipe is drained by the service poll set. A failed worker leaves the record for the next
journal advance or start; it is never retried by a timer.
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
    def __init__(self, ledger, given=None, landing=None, observe=None):
        self.ledger, self.given, self.landing = ledger, dict(given or {}), landing
        self.observe = observe or (lambda answer: None)
        self.active, self.buffer = None, b''
        self.reconcile = None
        self.head, self.dispatched = 0, None

    def pipes(self):
        return {self.active[0]: self.active[1]} if self.active else {}

    def start(self, replay=None, reconcile=None):
        self.reconcile = reconcile
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
            # No inherited listener, lock, launch pipe or database handle outlives the service here.
            for name in os.listdir('/proc/self/fd'):
                descriptor = int(name)
                if descriptor > 2 and descriptor != write:
                    try:
                        os.close(descriptor)
                    except OSError:
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

    def readable(self, descriptor):
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
        finished = self.dispatched is None or self.ledger.event_record(self.dispatched)['state'] == 'consumed'
        if status == 0 and answer.get('ok') and finished:
            self.advance()
