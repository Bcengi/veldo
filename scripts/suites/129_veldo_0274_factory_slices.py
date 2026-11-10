"""VELDO-0274: the VELDO-0127 factory removes every systemd slice it creates, on success, failure and interruption.

The last suite of the unit stage, so its end-of-run row sees every factory user of this run before it. In the
gate it runs after suite 86 and in the same process."""
def _v274_factory_slices():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import signal
    import subprocess
    import sys
    import tempfile
    import time

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]
    # The factory under test, by the path the mutation stage's worker replaces with a mutant copy; the children
    # load the same file.
    FACTORY_FILE = ROOT / "proof/VELDO-0127" / "factory.py"
    spec = importlib.util.spec_from_file_location('v274_factory', FACTORY_FILE)
    factory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(factory)
    ROWS = ('slices/return', 'slices/raise', 'slices/sigterm', 'slices/sweep-dead', 'slices/sweep-live',
            'slices/end-of-run')
    rows = {name: [] for name in ROWS}

    def check(row, condition, detail=''):
        rows[row].append(bool(condition))
        if not condition:
            print('  VELDO-0274 ' + row + ' detail: ' + detail)

    runtime = '/run/user/' + str(os.getuid())
    environment = dict(os.environ, XDG_RUNTIME_DIR=runtime, DBUS_SESSION_BUS_ADDRESS='unix:path=' + runtime + '/bus')
    # A child process that starts the factory, launches one fake engine into its slice, reports what the user
    # manager shows, and then returns, raises, waits to be signalled, or (enter) only enters and leaves.
    child = '''import importlib.util, json, os, subprocess, sys, time
from pathlib import Path
tree, root, mode, base = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
factory = load('v274_child_factory', Path(sys.argv[5]))
wire = load('v274_child_wire', tree / 'proof/VELDO-0127/wire_fixture.py')
fault = base / 'fault'
fault.write_text('')
catalog = base / 'catalog-fixture.json'
catalog.write_bytes((tree / 'proof/VELDO-0127/catalog-fixture.json').read_bytes())
(base / 'features-fixture.json').write_bytes((tree / 'proof/VELDO-0127/features-fixture.json').read_bytes())
with factory.factory(root, base / 'factory', {}, lambda _: wire.engine_source(catalog, fault)) as f:
    report = {'slice': f.slice_name}
    if mode != 'enter':
        engine = 'veldo0274-engine-%d.service' % os.getpid()
        subprocess.run(['systemd-run', '--user', '--quiet', '--collect', '--slice=' + f.slice_name, '--unit=' + engine,
                        '--', sys.executable, '-c', 'import time; time.sleep(600)'],
                       env=f.inherited, check=True, capture_output=True, timeout=20)
        active = subprocess.run(['systemctl', '--user', 'is-active', engine], env=f.inherited,
                                capture_output=True, text=True, timeout=20).stdout.strip()
        report.update(engine=engine, active=active, loaded=f.slice_name in (factory.loaded_slices(f.inherited) or []))
    print(json.dumps(report), flush=True)
    if mode == 'raise':
        raise RuntimeError('the body raised')
    if mode == 'wait':
        time.sleep(300)
'''

    def run_child(mode, scratch, wait=True):
        work = scratch / mode
        (work / 'factory').mkdir(parents=True)
        command = [sys.executable, '-I', str(scratch / 'child.py'), str(TREE), str(ROOT), mode, str(work),
                   str(FACTORY_FILE)]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   stdin=subprocess.DEVNULL, env=environment)
        children.append(process.pid)
        if not wait:
            return process
        out, err = process.communicate(timeout=300)
        return process.returncode, out, err

    def report(out):
        for line in out.splitlines():
            if line.startswith('{"slice"'):
                return json.loads(line)
        return {}

    def unit_loaded(name):
        result = subprocess.run(['systemctl', '--user', 'list-units', '--all', '--plain', '--no-legend', name],
                                env=environment, capture_output=True, text=True, timeout=20)
        return any(line.split()[:1] == [name] for line in result.stdout.splitlines())

    def gone(seen, row):
        """The child's slice and its fake engine are no longer loaded in the user manager."""
        name = seen.get('slice') or ''
        check(row, seen.get('loaded') is True and seen.get('active') == 'active',
              'the fake engine never ran in the slice: %r' % (seen,))
        deadline = time.monotonic() + 10
        while (unit_loaded(name) or unit_loaded(seen.get('engine') or '')) and time.monotonic() < deadline:
            time.sleep(0.1)
        check(row, bool(name) and not unit_loaded(name), '%s is still loaded after the factory closed' % name)
        check(row, seen.get('engine') and not unit_loaded(seen['engine']),
              '%s is still loaded after the factory closed' % seen.get('engine'))

    children, planted, sleepers = [], [], []
    manager = factory.loaded_slices(environment)
    try:
        if manager is None:
            print('  VELDO-0274: no systemd user manager answers here; the slice rows stand down, '
                  'only the end-of-run row runs')
        else:
            with tempfile.TemporaryDirectory(prefix='v274-', dir=runtime) as temp:
                scratch = Path(temp)
                (scratch / 'child.py').write_text(child)
                # AC1 (a) and (b): the body returns, the body raises.
                code, out, err = run_child('return', scratch)
                check('slices/return', code == 0, 'child exited %s: %s' % (code, err[-400:]))
                gone(report(out), 'slices/return')
                code, out, err = run_child('raise', scratch)
                check('slices/raise', code != 0 and 'the body raised' in err, 'child exited %s: %s' % (code, err[-400:]))
                gone(report(out), 'slices/raise')
                # AC2: SIGTERM while the factory is open stops the slice and then ends the child by default action.
                process = run_child('wait', scratch, wait=False)
                line = ''
                while not line.startswith('{"slice"'):
                    line = process.stdout.readline()
                    if not line:
                        break
                process.send_signal(signal.SIGTERM)
                try:
                    process.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                check('slices/sigterm', process.returncode == -signal.SIGTERM,
                      'child exited %s, not by SIGTERM' % process.returncode)
                gone(report(line), 'slices/sigterm')
                # AC2: the entry sweep stops a dead pid's slice and never a live process's.
                dead = subprocess.Popen([sys.executable, '-c', 'pass'])
                dead.wait()
                sleeper = subprocess.Popen(['sleep', '600'])
                sleepers.append(sleeper)
                dead_slice = 'veldo0127-%d.slice' % dead.pid
                live_slice = 'veldo0127-%d.slice' % sleeper.pid
                for name in (dead_slice, live_slice):
                    planted.append(name)
                    factory.unit('start', name, environment)
                planted_ok = unit_loaded(dead_slice) and unit_loaded(live_slice) and not factory.live(dead.pid)
                check('slices/sweep-dead', planted_ok, 'the planted slices are not both loaded')
                check('slices/sweep-live', planted_ok, 'the planted slices are not both loaded')
                code, out, err = run_child('enter', scratch)
                check('slices/sweep-dead', code == 0, 'child exited %s: %s' % (code, err[-400:]))
                check('slices/sweep-dead', not unit_loaded(dead_slice), dead_slice + ' is still loaded')
                check('slices/sweep-dead', dead_slice in out, 'the factory printed no line naming ' + dead_slice)
                check('slices/sweep-live', unit_loaded(live_slice), live_slice + ' of a live process was stopped')
                check('slices/sweep-live', live_slice not in out, 'the factory named ' + live_slice)
    except Exception as error:
        for row in ROWS[:-1]:
            check(row, False, 'raised %s: %s' % (type(error).__name__, str(error)[:200]))
    finally:
        # The suite's own fixtures only: the planted slices, and any slice a broken factory left for a child.
        for name in planted + ['veldo0127-%d.slice' % pid for pid in children]:
            factory.unit('stop', name, environment)
        for sleeper in sleepers:
            sleeper.kill()
            sleeper.wait()
    # AC3's registered mutation (check_teeth_mutations.py, slices274-factory-user-without-exit-stack): the mutation
    # stage's worker replaces this path with a copy of suite 86, the factory user that runs before this suite in the
    # gate, in this process. Only then does this suite run that copy here, before the end-of-run
    # row, as the gate runs 86 before 129; the no-op copy is the control. Unreplaced, suite 86 runs on its own in
    # the manifest and is not run again here. Its rows stay its own: they are counted here but never reported as
    # this suite's rows, so the control's rows equal the baseline's.
    FACTORY_USER = ROOT / "scripts/suites" / "86_veldo_0127_agent_configuration.py"
    if Path(FACTORY_USER).resolve() != (ROOT / 'scripts/suites/86_veldo_0127_agent_configuration.py').resolve():
        user_rows = []
        exec(compile(Path(FACTORY_USER).read_text(), str(FACTORY_USER), 'exec'),
             dict(globals(), expect=lambda name, condition: user_rows.append((name, bool(condition)))))
        print('  VELDO-0274 suite 86 copy: %d rows, false: %s' % (
            len(user_rows), ', '.join(name for name, ok in user_rows if not ok) or 'none'))
    # AC3: after the unit stage's last suite, no veldo0127 slice whose pid belongs to this run remains loaded. In
    # the gate this suite runs in the same selftest process as the factory users and after them. A pid belongs to this run when it is this process, a live descendant of it, or a process that is
    # gone and whose slice became active after this process started. A live process outside this process's tree
    # is another run's, and its slice is never judged.
    def parent(pid):
        try:
            return int(Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, IndexError, ValueError):
            return 0

    def descendant(pid):
        seen = set()
        while pid > 1 and pid not in seen:
            if pid == os.getpid():
                return True
            seen.add(pid)
            pid = parent(pid)
        return False

    def activated_us(name):
        result = subprocess.run(['systemctl', '--user', 'show', '-p', 'ActiveEnterTimestampMonotonic', '--value',
                                 name], env=environment, capture_output=True, text=True, timeout=20)
        return int(result.stdout.strip() or 0) if result.stdout.strip().isdigit() else 0

    # This process's start on CLOCK_MONOTONIC's scale, the scale of ActiveEnterTimestampMonotonic.
    ticks = int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])
    age = float(Path('/proc/uptime').read_text().split()[0]) - ticks / os.sysconf('SC_CLK_TCK')
    started_us = (time.clock_gettime(time.CLOCK_MONOTONIC) - age) * 1e6

    def ours(name):
        pid = int(factory.SLICE.fullmatch(name).group(1))
        if factory.live(pid):
            return descendant(pid)
        return activated_us(name) >= started_us

    leaked = [name for name in (factory.loaded_slices(environment) or []) if ours(name)]
    check('slices/end-of-run', not leaked, 'leaked: ' + ', '.join(leaked))
    # Judged first, then stopped, so a leak reds this row once and does not outlive the run.
    for name in leaked:
        factory.unit('stop', name, environment)
    for row, observed in rows.items():
        if manager is None and row != 'slices/end-of-run':
            continue
        expect('VELDO-0274 ' + row, bool(observed) and all(observed))

_v274_factory_slices()
