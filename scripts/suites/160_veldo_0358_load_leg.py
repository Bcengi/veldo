"""VELDO-0358: Generator lifecycle and load application (AC12). Real load, affinity, canary and cleanup.

Each closure runs independently; mutation targets retain their original row labels.
"""


def _v358d_load_leg():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import types

    # The subjects, each named once so the mutation driver can put a mutant copy in its place.
    load_source = ROOT / "scripts" / "gate_load.py"
    legs_source = ROOT / "scripts" / "gate_legs.py"
    gate_source = ROOT / "scripts" / "verify.sh"
    schedule_source = ROOT / "scripts" / "gate_schedule.py"
    dispatcher_source = ROOT / "scripts" / "selftest.py"
    candidate_source = ROOT / "scripts" / "gate_candidate.py"
    sandbox_source = ROOT / "scripts" / "agent_sandbox.py"

    def row(name, problems):
        problems = [p for p in problems if p]
        expect('VELDO-0358 ' + name + (': ' + '; '.join(problems) if problems else ''), not problems)

    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    env = {k: v for k, v in os.environ.items()
           if not k.startswith('VELDO_GATE_') and k not in ('VELDO_OPENED_LEDGER_FD', 'VELDO_SUITE_ORDER')}
    top = Path(tempfile.mkdtemp(prefix='v358d-'))
    python = sys.executable

    # ------------------------------------------------------------------ AC12: load/level-by-construction
    # The fixture leg: a fixed amount of CPU work in two halves, on the CPUs of the set. With three
    # spinners beside it, it gets a quarter of a CPU, so fifteen CPU-seconds last sixty seconds or more.
    fixture_leg = ('import json, os, sys, time\n'
                   'print("fixture leg: cpus " + json.dumps(sorted(os.sched_getaffinity(0))), flush=True)\n'
                   'def burn(amount):\n'
                   '    start = time.process_time()\n'
                   '    while time.process_time() - start < amount:\n'
                   '        pass\n'
                   'burn(7.5)\nprint("fixture leg: half", flush=True)\n'
                   'burn(7.5)\nprint("fixture leg: done", flush=True)\n')

    def under_load(name, command, at_half=None):
        """Run a command as a leg under the generator (two slots). Returns the start record, the load
        record (None when the leg never printed one), the exit status, the output, and whether every
        generator process was gone once the leg had ended."""
        scratch = top / name
        (scratch / 'a').mkdir(parents=True)
        (scratch / 'b').mkdir()
        leg = subprocess.Popen([python, '-I', '-S', str(load_source), '--slots', '2',
                                '--write-dir', str(scratch / 'a'), '--write-dir', str(scratch / 'b'),
                                '--', *command], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, env=env)
        start = record = None
        held, lines = [], []
        for line in leg.stdout:  # a line of the leg is the event; the read has no bound of its own
            lines.append(line.rstrip('\n'))
            if line.startswith('load: start '):
                start = json.loads(line[len('load: start '):])
                for pid in start['spinners'] + start['writers'] + [start['probe']]:
                    try:
                        held.append(os.pidfd_open(pid))
                    except OSError:
                        pass
            elif line.startswith('load: record '):
                record = json.loads(line[len('load: record '):])
            elif line.startswith('fixture leg: half') and at_half and start:
                at_half(leg, start)
        code = leg.wait()
        # Every generator's exit, each awaited on its pidfd: an event, with no bound.
        for pidfd in held:
            select.select([pidfd], [], [])
            os.close(pidfd)
        gone = start is not None and len(held) == len(start['spinners']) + len(start['writers']) + 1
        left = sorted(str(p.relative_to(scratch)) for p in scratch.rglob('*') if p.is_file())
        return start, record, code, lines, gone, left

    leg_command = [python, '-c', fixture_leg]

    # 1. Sixty seconds beside the fixture leg: the load record, every generator alive.
    # The ordinary canary shares this whole live fixture leg. A separate, very short canary
    # leg can end before every generator has recorded work; the existing CPU-work fixture
    # already supplies that evidence without a timing threshold or a second load level.
    live_leg_command = [python, '-c', fixture_leg +
                        'import subprocess\n'
                        'status = subprocess.run([sys.executable, "-I", "-S", sys.argv[1], "--canary"]).returncode\n'
                        'print("fixture canary exit: %s" % status, flush=True)\n', str(load_source)]
    start, record, code, lines, gone, left = under_load('alive', live_leg_command)
    problems = []
    if not (start and record):
        problems.append('no load record: %s' % lines[-3:])
    else:
        spinners, writers = record['spinners'], record['writers']
        problems += [
            code != 0 and 'the leg ended with status %s' % code,
            'fixture leg: done' not in lines and 'the fixture leg did not finish',
            'fixture leg: cpus ' + json.dumps(sorted(start['cpus'])) not in lines
            and 'the fixture leg is not bound to the spinners\' CPUs',
            sorted(s['cpu'] for s in spinners) != sorted(start['cpus'] * 3)
            and 'not three spinners on each CPU of the set: %s on %s' % ([s['cpu'] for s in spinners], start['cpus']),
            len(start['cpus']) != 2 and 'the set is not as many CPUs as the leg has slots: %s' % start['cpus'],
            len(writers) != 1 and 'not one writer per four CPUs: %d' % len(writers),
            not all(s['alive'] for s in spinners + writers) and 'a generator was not alive to the end',
            not all(s['cpu_seconds'] > 0 for s in spinners) and 'a spinner consumed no CPU',
            # Load-independent: on the leg's CPUs the spinners share the CPU with the leg (three to one per CPU),
            # so together they consume at least the leg's own fifteen CPU-seconds however busy the host is. A
            # spinner that is alive but blocked consumes only its start.
            sum(s['cpu_seconds'] for s in spinners) < 15.0
            and 'the spinners together consumed %.2f CPU-seconds, less than the leg\'s own 15 beside them'
            % sum(s['cpu_seconds'] for s in spinners),
            not all(w['bytes'] > 0 for w in writers) and 'a writer wrote no bytes',
            not (record['applied'] and record['error'] is None) and 'the load is not reported applied',
            'slowdown' not in record['probe'] and 'no probe reading: %s' % record['probe'],
            not gone and 'a generator process was left',
            left and 'a writer left files: %s' % left]

    canary_result = [line for line in lines if line.startswith('canary: ')]
    canary_exit = [line for line in lines if line.startswith('fixture canary exit: ')]
    print('sleep-synchronized canary under generator load: %s (data)' % canary_result, flush=True)
    problems += [
        (canary_result, canary_exit) not in [(['canary: green'], ['fixture canary exit: 0']),
                                           (['canary: red'], ['fixture canary exit: 1'])]
        and 'the canary did not record a valid result: %s, %s' % (canary_exit, canary_result)]

    # 2. The same with one spinner killed midway: load_not_applied, by name.
    def kill_spinner(leg, start):
        os.kill(start['spinners'][0], signal.SIGKILL)

    start, record, code, lines, gone, left = under_load('spinner-killed', leg_command, kill_spinner)
    if not (start and record):
        problems.append('spinner killed: no load record: %s' % lines[-3:])
    else:
        named = [p for p in record['problems'] if 'spinner %d ' % start['spinners'][0] in p]
        problems += [
            (record['applied'] or record['error'] != 'load_not_applied')
            and 'a leg with a spinner killed midway is not load_not_applied: %s' % record['error'],
            not named and 'the dead spinner is not named: %s' % record['problems'],
            code == 0 and 'a leg whose load was not applied ended with status 0',
            not any(line.startswith('load: load_not_applied') for line in lines) and 'load_not_applied is not printed',
            not gone and 'spinner killed: a generator process was left']

    # 3. The same ended by a kill of the leg: no generator process left.
    def kill_leg(leg, start):
        os.kill(leg.pid, signal.SIGKILL)

    start, record, code, lines, gone, left = under_load('leg-killed', leg_command, kill_leg)
    problems += [
        start is None and 'leg killed: the leg never started',
        record is not None and 'leg killed: a killed leg printed a record',
        code != -signal.SIGKILL and 'leg killed: the leg ended with status %s' % code,
        not gone and 'leg killed: a generator process was left',
        left and 'leg killed: a writer left files: %s' % left]

    # 4. Run the canary's own fork, work, marker read and reap. Only its sleep is replaced by
    # the child's completion event. The child is held on a pipe until that wait releases it;
    # if the wait is removed, the actual marker read must be false on EVERY schedule. Release
    # after that read too, so the missing-wait mutant can reap and fail by assertion, not hang.
    canary_load = module('v358d_canary_control', load_source)
    release_read, release_write = os.pipe()
    child_pids, released = [], []
    real_burn = canary_load.burn

    def held_burn(amount):
        os.read(release_read, 1)
        real_burn(amount)

    def canary_fork():
        pid = os.fork()
        if pid:
            child_pids.append(pid)
        return pid

    def release_canary():
        if not released:
            os.write(release_write, b'x')
            released.append(True)

    def wait_for_canary_child():
        release_canary()
        # WNOWAIT leaves the canary's own waitpid responsible for reaping its child.
        os.waitid(os.P_PID, child_pids[0], os.WEXITED | os.WNOWAIT)

    def event_sleep(_seconds):
        wait_for_canary_child()

    def read_marker(path):
        try:
            return os.path.exists(path)
        finally:
            release_canary()

    canary_load.burn = held_burn
    canary_load.time = types.SimpleNamespace(process_time=canary_load.time.process_time, sleep=event_sleep)
    canary_load.os = types.SimpleNamespace(**vars(os))
    canary_load.os.fork = canary_fork
    canary_load.os.path = types.SimpleNamespace(**vars(os.path))
    canary_load.os.path.exists = read_marker
    try:
        control_green = canary_load.canary()
    finally:
        release_canary()
        for pid in child_pids:
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:  # already reaped by the canary
                pass
        os.close(release_read)
        os.close(release_write)
    problems += [not control_green and 'the event-synchronized canary control is not green']
    print('canary control: %s (child completion event)' % ('green' if control_green else 'red'), flush=True)

    row('load/level-by-construction', problems)

    # Brief D's finding 4: the leg's two bounds sit in gate_load.HANG (the census reads a bound named in the
    # file that uses it as its number). They are the contract's hang constants, the suite runtime's own.
    hang = module('v358d_gate_load_hang', load_source).HANG
    row('load/hang-constants-are-the-contract', [
        (hang.WAIT_HANG_SECONDS, hang.PROCESS_HANG_SECONDS) != (WAITS.WAIT_HANG_SECONDS, WAITS.PROCESS_HANG_SECONDS)
        and 'gate_load.HANG %r differs from waits.py %r' % ((hang.WAIT_HANG_SECONDS, hang.PROCESS_HANG_SECONDS),
                                                           (WAITS.WAIT_HANG_SECONDS, WAITS.PROCESS_HANG_SECONDS))])
    shutil.rmtree(str(top), ignore_errors=True)


_v358d_load_leg()
