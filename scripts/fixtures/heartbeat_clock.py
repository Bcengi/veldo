"""Suite-only supplied clocks for the real heartbeat sender and receiver.

Installation instruments private copies, never the product. Production computes
all deadlines, sends every heartbeat, renews claims and signals real processes.
A clock advance wakes poll through a FIFO; scheduling never advances test time.
The poll boundary and receiver snapshot are observations, not substitute decisions.
"""
import json
import os
from pathlib import Path
import select
import selectors
import types
try:
    from fixture_waits import WAIT_HANG_SECONDS
except ImportError:
    import runpy
    WAIT_HANG_SECONDS = runpy.run_path(str(Path(__file__).parents[1] / 'suites/support/waits.py'))['WAIT_HANG_SECONDS']


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.%d.tmp' % os.getpid())
    temporary.write_text(json.dumps(value))
    temporary.replace(path)


def read(path):
    return json.loads(Path(path).read_text())


def deadline(state):
    """The requested wake, preserving Stop.due below poll's millisecond rounding."""
    assert state['timeout'] is not None, state
    due = state['now'] + state['timeout'] / 1000
    stop_due = (state.get('observation') or {}).get('due')
    if stop_due is not None and due - 0.001 <= stop_due <= due:
        return stop_due
    return due


class Clock:
    def __init__(self, directory):
        self.directory = Path(directory)

    def monotonic(self):
        return read(self.directory / 'now')

    def snapshot(self, **values):
        write(self.directory / 'receiver', values)

    def select(self, role):
        clock = self

        class EventSelector(selectors.PollSelector):
            _EVENT_READ = select.POLLIN | select.POLLPRI | select.POLLERR

        class Poll:
            def __init__(self):
                self.poller = EventSelector()
                self.tick = os.open(clock.directory / role, os.O_RDWR | os.O_NONBLOCK)
                self.poller.register(self.tick, selectors.EVENT_READ)
                self.gate = EventSelector()
                self.gate.register(self.tick, selectors.EVENT_READ)
                self.held = False
                self.turn = 0

            def register(self, fd, events):
                return self.poller.register(fd, selectors.EVENT_READ)

            def unregister(self, *args):
                return self.poller.unregister(*args)

            def poll(self, timeout=None):
                self.turn += 1
                observation = clock.directory / 'receiver'
                state = {'now': clock.monotonic(), 'timeout': timeout, 'turn': self.turn,
                         'observation': read(observation) if role == 'receiver-tick' and observation.exists() else None}
                write(clock.directory / (role + '-waiting'), state)
                # Only a hang detector is a real timeout. The supplied clock's
                # deadline is awakened by the fixture's explicit tick.
                while True:
                    if self.held:
                        write(clock.directory / (role + '-held'), state)
                    waiting = self.gate if self.held else self.poller
                    events = waiting.select(WAIT_HANG_SECONDS)
                    if not events:
                        raise TimeoutError('heartbeat fixture event wait hung')
                    result = []
                    for key, mask in events:
                        fd = key.fd
                        if fd == self.tick:
                            self.held = os.read(fd, 65536).endswith(b'h')
                        else:
                            result.append((fd, mask))
                    # Deliver already observed native events before acknowledging
                    # a hold at the next product poll and its updated deadline.
                    if result or not self.held:
                        return result

        return types.SimpleNamespace(poll=Poll, POLLIN=select.POLLIN,
                                     POLLPRI=select.POLLPRI, POLLERR=select.POLLERR)


def replace(source, old, new):
    if source.count(old) != 1:
        raise ValueError('heartbeat fixture boundary moved: ' + old)
    return source.replace(old, new)


def install(mods):
    """Bind existing time arguments through module-local proxies in private copies."""
    import shutil
    shutil.copyfile(__file__, mods / 'heartbeat_clock.py')
    shutil.copyfile(Path(__file__).parents[1] / 'suites/support/waits.py', mods / 'fixture_waits.py')
    path = mods / 'control_heartbeat.py'
    source = path.read_text()
    source = replace(source, '        poller = select.poll()\n        poller.register(engine',
                     "        from heartbeat_clock import Clock\n"
                     "        time = Clock(os.environ['V41_CLOCK'])\n"
                     "        select = time.select('sender')\n"
                     '        poller = select.poll()\n        poller.register(engine')
    path.write_text(source)
    path = mods / 'control_containment.py'
    source = path.read_text()
    source = replace(source, '    def terminate(self):\n',
                     '    def terminate(self):\n'
                     "        if self.environment.get('V41_CLOCK'):\n"
                     "            __import__('heartbeat_clock').write(Path(self.environment['V41_CLOCK']) / 'group-terminated', True)\n")
    path.write_text(source)
    path = mods / 'control_launch.py'
    source = path.read_text()
    source = replace(source, '        group = C.Group(self.profile, self.qualification, dispatch_id, environment)',
                     "        environment = dict(environment, V41_CLOCK=str(Path(self.config['fixture_clocks']) / dispatch_id.rsplit('/', 1)[-1]))\n"
                     '        group = C.Group(self.profile, self.qualification, dispatch_id, environment)')
    source = replace(source, 'worker.heartbeat = HB.Watch(channel, interval, window, time.monotonic())',
                     "worker.heartbeat = HB.Watch(channel, interval, window, __import__('heartbeat_clock').Clock(environment['V41_CLOCK']).monotonic())")
    source = replace(source, '        self.space_output = _organ(\'control_space_admission\').Output()',
                     "        from heartbeat_clock import Clock\n"
                     "        fixture_clock = Clock(Path(self.config['fixture_clocks']) / contract['dispatch_id'].rsplit('/', 1)[-1])\n"
                     "        time = types.SimpleNamespace(time=__import__('time').time, monotonic=fixture_clock.monotonic)\n"
                     "        select = fixture_clock.select('receiver-tick')\n"
                     "        self.space_output = _organ('control_space_admission').Output()")
    # Read-only snapshots after the real receiver's decisions, including mutants
    # that omitted a decision. They let absence be judged without a timeout.
    source = replace(source, "                while getattr(self, 'checks', None):",
                     "                fixture_clock.snapshot(now=now, heartbeat=watch.summary() if watch else {}, cause=cause,\n"
                     "                                       steps=stop.steps if stop else [], due=stop.due if stop else None, code=code)\n"
                     "                while getattr(self, 'checks', None):")
    # types is already a product import only on some revisions; keep this local.
    source = source.replace('        from heartbeat_clock import Clock\n',
                            '        import types\n        from heartbeat_clock import Clock\n')
    path.write_text(source)
