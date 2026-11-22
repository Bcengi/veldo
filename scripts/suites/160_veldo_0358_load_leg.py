"""VELDO-0358 brief D: the load generator (AC12) and the load-proof leg (AC13).

load/level-by-construction drives the real scripts/gate_load.py beside a fixture leg: the load record
with every generator alive, load_not_applied when a spinner is killed midway, no generator process
left when the leg itself is killed, an event-synchronized green canary control, and the ordinary
sleep-synchronized canary result recorded inside the load.
leg/proves-and-blocks drives the real scripts/verify.sh, scripts/gate_legs.py and scripts/gate_load.py
as a fixture authority over a fixture candidate whose suites run through the real dispatcher.

Nothing here waits for time to pass. A fixture leg lasts by the CPU work it does, counted on its own
CPU clock; every wait is a read of a child's output or of a pidfd, with no bound of its own.
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
    start, record, code, lines, gone, left = under_load('alive', leg_command)
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

    start, record, code, lines, gone, left = under_load('canary', [python, '-I', '-S', str(load_source), '--canary'])
    canary_result = [line for line in lines if line.startswith('canary: ')]
    print('sleep-synchronized canary under generator load: %s (data)' % canary_result, flush=True)
    problems += [
        (code not in (0, 1) or canary_result != ['canary: ' + ('green' if code == 0 else 'red')])
        and 'the canary did not record a valid result: status %s, %s' % (code, canary_result),
        not (record and record['applied']) and 'the canary leg has no applied load record',
        not gone and 'canary: a generator process was left']
    row('load/level-by-construction', problems)

    # ------------------------------------------------------------------------ AC13: leg/proves-and-blocks
    legs = module('v358d_gate_legs', legs_source)
    # Brief D's finding 4: the leg's two bounds sit in gate_load.HANG (the census reads a bound named in the
    # file that uses it as its number). They are the contract's hang constants, the suite runtime's own.
    hang = module('v358d_gate_load_hang', load_source).HANG
    row('load/hang-constants-are-the-contract', [
        (hang.WAIT_HANG_SECONDS, hang.PROCESS_HANG_SECONDS) != (WAITS.WAIT_HANG_SECONDS, WAITS.PROCESS_HANG_SECONDS)
        and 'gate_load.HANG %r differs from waits.py %r' % ((hang.WAIT_HANG_SECONDS, hang.PROCESS_HANG_SECONDS),
                                                           (WAITS.WAIT_HANG_SECONDS, WAITS.PROCESS_HANG_SECONDS))])
    runs = top / 'runs'
    count = ('import os as _fx_os\n'
             'with open(_fx_os.environ["V358D_RUNS"], "a") as _fx_out:\n'
             '    _fx_out.write("%s %s\\n" % (_fx_os.path.basename(__suite_file__)[:-3], '
             '"leg" if SCOPE.partial else "unit"))\n')
    clean = count + 'expect("fx/clean", True)\n'
    # The canary as a suite. In the unit stage (the whole suite in one process, no load) it asserts
    # nothing about time; in a process of its own, which is how the leg runs it, it is the canary.
    canary_suite = count + (
        'import importlib.util as _fx_iu\n'
        'if SCOPE.partial:\n'
        '    _fx_spec = _fx_iu.spec_from_file_location("fx_gate_load", str(ROOT / "scripts/gate_load.py"))\n'
        '    _fx_load = _fx_iu.module_from_spec(_fx_spec)\n'
        '    _fx_spec.loader.exec_module(_fx_load)\n'
        '    expect("fx/canary-marker-after-its-sleep", _fx_load.canary())\n'
        'else:\n'
        '    expect("fx/canary-not-in-a-leg", True)\n')
    shared_text = (
        'import sys\nfrom pathlib import Path\n'
        'ROOT = Path(__file__).resolve().parent.parent.parent\n'
        'PASS = 0\nFAIL = 0\nSCOPE = None\n'
        'def expect(name, condition):\n'
        '    global PASS, FAIL\n'
        '    if condition:\n        PASS += 1\n'
        '    else:\n        FAIL += 1\n        print(f"  SELFTEST FAIL: {name}")\n'
        'def report():\n'
        '    print(SCOPE.aggregate_line(PASS, FAIL))\n'
        '    return SCOPE.exit_code(FAIL)\n')
    suites = {'fx_clean': clean, 'fx_canary_listed': canary_suite, 'fx_canary': canary_suite,
              'fx_changed': clean, 'fx_support': clean}
    stubs = {
        'scripts/gate_candidate.py': 'import subprocess, sys\na = sys.argv\n'
                                     'sys.exit(subprocess.run(a[a.index("--") + 1:]).returncode)\n',
        'scripts/check_gate_mutations.py': 'import os, sys\nopen(os.environ["V358D_MUTATION"], "a").write("started\\n")\n'
                                           'sys.exit(0)\n',
        'scripts/reuse_stamp.py': 'print(\'"force_fresh":false,"reused":{"mutation":0,"unit":0}\')\n',
        'scripts/check_lint.sh': 'exit 0\n', 'scripts/check_first_use.py': '', 'scripts/secret_inventory.py': '',
        'scripts/check_install_and_run.py': '', 'scripts/check_personal_setup.py': '',
        'scripts/check_wallclock.py': '',
        'scripts/check_generated.sh': 'exit 0\n', 'scripts/check_docs.sh': 'exit 0\n',
        'scripts/check_template_sync.sh': 'exit 0\n', 'scripts/check_space_boundary.py': '',
        '.veldo/validate.py': '', '.veldo/shape_gate.py': '', '.veldo/events.py': '',
    }

    def tree(root, changed):
        """One checkout of the fixture repository: the real dispatcher over the fixture suites."""
        for relative, text in stubs.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text)
        for source in (gate_source, legs_source, load_source, dispatcher_source,
                       ROOT / 'scripts/run_scope.py'):
            shutil.copyfile(str(source), str(root / 'scripts' / source.name))
        folder = root / 'scripts/suites'
        (folder / 'support').mkdir(parents=True)
        if (ROOT / 'scripts/suites/support').is_dir():  # the suite runtime's modules, where there are any
            shutil.copytree(str(ROOT / 'scripts/suites/support'), str(folder / 'support'), dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__'))
        (folder / 'shared.py').write_text(shared_text)
        (folder / 'support/fx_shared.py').write_text('SHARED = %r\n' % changed)
        for name, text in suites.items():
            (folder / (name + '.py')).write_text(text + ('# changed\n' if changed and name == 'fx_changed' else ''))
        (folder / 'manifest.json').write_text(json.dumps(
            {'schema': 'veldo.suites/v1', 'entry': 'selftest.py', 'shared': 'shared.py',
             'suites': [{'name': name, 'file': name + '.py', 'requires': [name], 'regions': 'fixture',
                         'requires_note': 'fixture'} for name in suites]}))
        (folder / 'requires.json').write_text(json.dumps(
            {'schema': 'veldo.suite_requires/v1', 'requires': {name: [name] for name in suites}}))
        return root

    # What each suite opened: the two canaries open the generator, and four suites open the shared
    # support file, which is therefore nobody's own fixture.
    opened = {name: ['scripts/suites/%s.py' % name] for name in suites}
    for name in ('fx_canary_listed', 'fx_canary'):
        opened[name].append('scripts/gate_load.py')
    for name in ('fx_clean', 'fx_canary', 'fx_changed', 'fx_support'):
        opened[name].append('scripts/suites/support/fx_shared.py')

    def gate(name, baselined):
        """One gate of the fixture authority over the fixture candidate, in candidate mode."""
        base = top / name
        authority, candidate = tree(base / 'authority', False), tree(base / 'candidate', True)
        (authority / 'scripts/suites/wallclock_baseline.json').write_text(json.dumps(
            {'schema': 'veldo.wallclock-baseline/v1', 'entries': [
                {'class': 'S1', 'count': 1, 'file': 'scripts/suites/%s.py' % suite, 'function': '<module>',
                 'rule': 'R1', 'text': 'fixture entry'} for suite in baselined]}))
        (authority / '.veldo/opened_files.json').write_text(json.dumps(opened))
        for folder in ('sink', 'home'):
            (base / folder).mkdir()
        run_env = dict(env, HOME=str(base / 'home'), V358D_RUNS=str(base / 'runs'),
                       V358D_MUTATION=str(base / 'mutation'))
        with open(base / 'log', 'w') as log:
            code = subprocess.run(['bash', str(authority / 'scripts/verify.sh'), '--candidate', str(candidate),
                                   '--sink', str(base / 'sink')], cwd=str(base), env=run_env, stdout=log,
                                  stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                  pass_fds=launcher_fds()).returncode
        ran = (base / 'runs').read_text().split('\n') if (base / 'runs').exists() else []
        stamp = None
        if (base / 'sink/last_verify').is_file():
            stamp = json.loads((base / 'sink/last_verify').read_text())
        return dict(code=code, out=(base / 'log').read_text(), stamp=stamp, mutation=(base / 'mutation').exists(),
                    leg={suite: ran.count(suite + ' leg') for suite in suites},
                    unit={suite: ran.count(suite + ' unit') for suite in suites})

    red = gate('red', ['fx_canary_listed'])
    out, load = red['out'], (red['stamp'] or {}).get('load') or {}
    problems = [
        red['unit'] != {suite: 1 for suite in suites} and 'the unit stage did not run each suite once: %s' % red['unit'],
        (red['leg']['fx_clean'] != 1 or '   load-proof: fx_clean: pass, 1 run' not in out)
        and 'the clean suite did not run once and green: %d' % red['leg']['fx_clean'],
        red['leg']['fx_canary_listed'] != 0 and 'the baselined canary ran %d times' % red['leg']['fx_canary_listed'],
        red['leg']['fx_canary'] != 1 and 'the canary without its entry ran %d times, not once' % red['leg']['fx_canary'],
        '   load-proof: fx_canary: FAIL' not in out and 'the canary without its entry is not red in the leg',
        'SELFTEST FAIL: fx/canary-marker-after-its-sleep' not in out and 'the red row is not named',
        (red['code'] != 1 or 'GATE: RED' not in out) and 'the gate is not red: status %s' % red['code'],
        red['mutation'] and 'the mutation stage was started after a red leg',
        '== mutation: NOT STARTED (the load-proof leg is red)' not in out and 'the gate does not say the mutation stage was not started',
        red['leg']['fx_changed'] != 20 and 'the changed suite ran %d times, not twenty' % red['leg']['fx_changed'],
        red['leg']['fx_support'] != 1 and 'the suite whose shared file changed ran %d times, not once' % red['leg']['fx_support'],
        (red['stamp'] or {}).get('status') != 'red' and 'the stamp is not red',
        (load.get('verdict') != 'FAIL' or load.get('red') != ['fx_canary'])
        and 'the stamp\'s load record does not name the red suite: %s' % load,
        not (load.get('load', {}).get('applied') and load['load']['spinners_alive'] == load['load']['spinners']
             == 3 * load['load']['cpus'] and load['load']['writer_bytes'] > 0)
        and 'the stamp carries no applied load record: %s' % load.get('load'),
        load.get('canary') != 'red' and 'the canary under the leg\'s load is recorded as %s' % load.get('canary')]
    if any(problems):
        problems.append('gate output: ' + ' | '.join(out.splitlines()[-40:]))
    # The control: with nothing red in the proven set, the same gate is green and starts the stage.
    green = gate('green', ['fx_canary_listed', 'fx_canary', 'fx_changed'])
    problems += [
        (green['code'] != 0 or 'GATE: GREEN' not in green['out'] or not green['mutation'])
        and 'control: a green leg did not leave the gate green with the mutation stage started: status %s, %s'
        % (green['code'], ' | '.join(green['out'].splitlines()[-25:])),
        green['leg'] != {'fx_clean': 1, 'fx_canary_listed': 0, 'fx_canary': 0, 'fx_changed': 0, 'fx_support': 1}
        and 'control: the leg ran %s' % green['leg'],
        ((green['stamp'] or {}).get('load') or {}).get('verdict') != 'pass' and 'control: the stamp has no passing load record']
    row('leg/proves-and-blocks', problems)

    # The rules behind the leg's choices, read from the leg itself.
    pairs = [(name, 'scripts/suites/%s.py' % name) for name in suites]
    state = legs.proven_set({'scripts/suites/fx_canary_listed.py', 'scripts/gate_load.py'},
                            {k: v for k, v in opened.items() if k != 'fx_support'}, pairs,
                            {'fx_changed': ['fx_clean', 'fx_canary', 'fx_changed']})
    own = dict(opened, fx_clean=['scripts/suites/fx_clean.py'])  # now three suites open the shared file
    row('leg/proven-and-changed-rules', [
        state != {'fx_clean': None, 'fx_canary_listed': 'baseline entry in scripts/gate_load.py',
                  'fx_canary': 'baseline entry in scripts/gate_load.py',
                  'fx_changed': 'proven, waiting for its prerequisite fx_canary',
                  'fx_support': 'no opened-files record'} and 'proven set: %s' % state,
        legs.changed_suites(top / 'red/candidate', top / 'red/authority', opened, pairs)
        != {'fx_changed': 'scripts/suites/fx_changed.py'} and 'a file four suites open made a suite changed',
        sorted(legs.changed_suites(top / 'red/candidate', top / 'red/authority', own, pairs))
        != ['fx_canary', 'fx_changed', 'fx_support'] and 'a changed file three suites open did not make them changed',
        legs.changed_suites(top / 'red/candidate', top / 'red/candidate', own, pairs) != {}
        and 'a checkout that is its own authority has changed suites',
        # The design's own example: a suite of 960 loaded seconds runs eight times at eight slots.
        [legs.repetitions(s, 8) for s in ([960.0], [None], [10.0, 20.0], [4000.0], [300.0])] != [8, 20, 20, 5, 20]
        and 'repetitions: %s' % [legs.repetitions(s, 8) for s in ([960.0], [None], [10.0, 20.0], [4000.0], [300.0])],
        legs.judge(['selftest (PARTIAL, 1 of 5 suites): 3 passed, 0 failed in 1.50s'], 2, False) != ('pass', [], 1.5)
        and 'a passing suite process is not judged pass',
        legs.judge(['  SELFTEST HUNG: a row', 'selftest (PARTIAL, 1 of 5 suites): 3 passed, 0 failed in 1.50s'], 2, False)[0] != 'FAIL'
        and 'a hung row is not red',
        legs.judge(['  SELFTEST NOT RUN: a row'], 1, False)[0] != 'FAIL' and 'a row not run is not red',
        legs.judge([], -9, False)[0] != 'FAIL' and 'a suite process with no summary is not red',
        legs.judge(['selftest (PARTIAL, 1 of 5 suites): 0 passed, 0 failed in 0.10s'], 2, False)[0] != 'FAIL'
        and 'a suite process that asserted nothing is not red',
        legs.judge([], None, True)[0] != 'hung' and 'a silent suite process is not hung'])

    # ------------------------------------------------- AC13 under the graph scheduler: leg/graph-blocks
    # With scripts/gate_graph.json present the stages run as nodes of scripts/gate_schedule.py. The leg is
    # the node load (every other node before it, the mutation node after it). The scheduler below is the
    # real one from a fixture authority whose gate_legs.py answers --load-proof by the row's choice and
    # whose mutation stage only leaves a mark that it started; the graph and the catalog are the fixture's.
    authority = top / 'graph/authority'
    (authority / 'scripts').mkdir(parents=True)
    shutil.copyfile(str(schedule_source), str(authority / 'scripts/gate_schedule.py'))
    shutil.copyfile(str(legs_source), str(authority / 'scripts/gate_legs_real.py'))
    for name in ('gate_candidate.py', 'agent_sandbox.py', 'agent_sandbox.json'):  # how a catalog stage runs
        shutil.copyfile(str(ROOT / 'scripts' / name), str(authority / 'scripts' / name))
    shutil.copytree(str(ROOT / '.veldo'), str(authority / '.veldo'),
                    ignore=shutil.ignore_patterns('__pycache__', 'events.jsonl', 'last_verify'))
    (authority / 'scripts/gate_legs.py').write_text(
        'import json, os, sys\n'
        'from pathlib import Path\n'
        'if __name__ == "__main__" and "--load-proof" in sys.argv:\n'
        '    record = sys.argv[sys.argv.index("--record") + 1]\n'
        '    red = os.environ.get("V358G_LEG") == "red"\n'
        '    Path(record).write_text(json.dumps({"schema": "veldo.load-proof/v1", "state": "ran",\n'
        '                                        "verdict": "FAIL" if red else "pass"}) + "\\n")\n'
        '    print("fixture leg:", "red" if red else "green", flush=True)\n'
        '    sys.exit(1 if red else 0)\n'
        '_real = Path(__file__).with_name("gate_legs_real.py")\n'
        'exec(compile(_real.read_text(), str(_real), "exec"))\n')
    marks = top / 'graph/marks'
    marks.mkdir()
    (authority / 'scripts/check_gate_mutations.py').write_text(
        'import json, os, sys\n'
        'from pathlib import Path\n'
        'Path(os.environ["V358G_MARKS"], "mutation-started").write_text("started\\n")\n'
        'receipt = sys.argv[sys.argv.index("--receipt") + 1]\n'
        'Path(receipt).write_text(json.dumps({"status": "passed"}))\n')
    gscheduler = module('v358g_gate_schedule', authority / 'scripts/gate_schedule.py')

    class FixtureMeter:
        def __init__(self, name):
            self.name = name

        def command(self, argv):
            return argv

        def sample(self):
            return {'cpu_seconds': 0.01, 'peak_anon_bytes': 1024, 'metrics_source': 'fixture'}

        def finish(self):
            return dict(self.sample(), live_descendants=False)

    gnodes = {'lint': [], 'load': ['lint'], 'mutation': ['load']}
    graph_path = authority / 'scripts/gate_graph.json'
    graph_path.write_text(json.dumps({'schema': 'veldo.gate-graph/v1', 'nodes': {
        n: {'depends_on': d, 'writes_candidate': False, 'manager': 'none', 'ports': []} for n, d in gnodes.items()},
        'reserve': {'cpu': 0, 'memory': 0}, 'mutation_floor': {'cpu': 1, 'memory': 1024}}))
    candidate = top / 'graph/candidate'
    candidate.mkdir()

    def graph_gate(tag, leg, lint_code):
        for mark in marks.iterdir():
            mark.unlink()
        out = top / 'graph' / tag
        catalog = {'lint': '%s -c "raise SystemExit(%d)"' % (python, lint_code),
                   'load': 'authority load-proof leg', 'mutation': 'authority mutation stage'}
        saved = {k: os.environ.get(k) for k in ('V358G_LEG', 'V358G_MARKS')}
        os.environ.update(V358G_LEG=leg, V358G_MARKS=str(marks))
        try:
            receipt = gscheduler.run(catalog, candidate, out, out / 'legs', out / 'mutation-receipt',
                                     graph_path=graph_path, capacity={'cpu': 4, 'memory': 1 << 30, 'manager': 4},
                                     measurement_store=top / 'graph/store', meter_factory=FixtureMeter,
                                     guard_factory=lambda root: (lambda: True))
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return receipt, (marks / 'mutation-started').exists(), out

    red, red_started, red_out = graph_gate('red', 'red', 0)
    green, green_started, _ = graph_gate('green', 'green', 0)
    before, before_started, _ = graph_gate('before', 'red', 1)
    real_graph = json.loads((ROOT / 'scripts' / 'gate_graph.json').read_text())['nodes']
    row('leg/graph-blocks', [
        red['stages'] != {'lint': 'pass', 'load': 'FAIL', 'mutation': 'not_started'}
        and 'a red leg under the scheduler: stages %s' % red['stages'],
        red_started and 'a red leg under the scheduler: the mutation stage started',
        not (red_out / 'load.record').is_file() and 'the leg left no record beside the scheduler\'s results',
        'not started: the load-proof leg is red' not in (red_out / 'mutation.log').read_text()
        and 'the held mutation node does not say why',
        green['stages'] != {'lint': 'pass', 'load': 'pass', 'mutation': 'pass'}
        and 'control: a green leg under the scheduler: stages %s' % green['stages'],
        not green_started and 'control: a green leg did not let the mutation stage start',
        before['stages'] != {'lint': 'FAIL', 'load': 'not_run', 'mutation': 'pass'}
        and 'a stage before the leg red: stages %s (the leg is not run, the mutation stage runs as on the '
            'serial path)' % before['stages'],
        not before_started and 'a stage before the leg red: the mutation stage did not start',
        real_graph.get('mutation', {}).get('depends_on') != ['load']
        and 'the real graph does not put the mutation node after the leg',
        set(real_graph.get('load', {}).get('depends_on', ())) != set(real_graph) - {'load', 'mutation'}
        and 'the real graph does not put the leg after every other node'])

    # ---------------------------------------------- C18: leg/record-taken-by-the-authority (lead decision)
    # The opened-files record is taken by the authority (scripts/gate_legs.py TakeOpened), never written by the
    # candidate. One real gate (scripts/verify.sh in candidate mode) of a fixture authority with the REAL
    # confinement (gate_candidate.py, agent_sandbox.py) and a fixture unconfined list, over a fixture candidate
    # whose suites run through the real dispatcher:
    #   - fx_reader opens a data file by a computed path: the open is in the record, under fx_reader;
    #   - fx_forger, in the unconfined leg, writes a forged record where the gate publishes its record and
    #     appends a forged claim (a file it never opened) to the ledger descriptor it finds in its process;
    #   - the authority's own last record (.veldo/opened_files.json) is a forged one too.
    # The record beside the stamp is the authority's, the forged claim is dropped and said so, and the leg
    # judges that record: fx_clean (proven by it) runs once, fx_reader (whose data file has a baseline entry)
    # does not run (the authority's baseline names fx_data.txt, gate_load.py and the forger's own file). Under the forged records the leg would do the opposite of both.
    # The confined suites write nothing outside the domain, so these suites count no runs; the leg's own
    # lines say which suites it ran.
    reader = ('_fx_name = "fx" + "_data"\n'
                      'exec(compile((ROOT / "scripts" / "suites" / (_fx_name + ".txt")).read_text(), "fx", "exec"))\n'
                      'expect("fx/reader", FX_DATA == 1)\n')
    forged = {'fx_clean': ['scripts/gate_load.py'], 'fx_reader': [], 'fx_forger': ['scripts/suites/fx_never.txt']}
    forger = (
        'import json as _fx_json, os as _fx_os\n'
        'for _fx_target in _fx_os.environ["V358T_FORGE"].split(":"):\n'
        '    with open(_fx_target, "w") as _fx_out:\n'
        '        _fx_out.write(%r)\n'
        'for _fx_fd in _fx_os.listdir("/proc/self/fd"):\n'
        '    try:\n'
        '        if _fx_os.path.basename(_fx_os.readlink("/proc/self/fd/" + _fx_fd)) == "ledger":\n'
        '            _fx_os.write(int(_fx_fd), b\'{"suite": "fx_forger", "paths": ["scripts/suites/fx_never.txt"]}\\n\')\n'
        '            print("FX FORGED A CLAIM", flush=True)\n'
        '    except OSError:\n'
        '        pass\n'
        'expect("fx/forger", True)\n') % json.dumps(forged)
    taken_suites = {'fx_clean': 'expect("fx/clean", True)\n', 'fx_support': 'expect("fx/support", True)\n',
                    'fx_reader': reader, 'fx_forger': forger}

    def taken_tree(root):
        tree(root, False)
        folder = root / 'scripts/suites'
        for name in suites:
            (folder / (name + '.py')).unlink()
        for name, text in taken_suites.items():
            (folder / (name + '.py')).write_text(text)
        (folder / 'fx_data.txt').write_text('FX_DATA = 1\n')
        (folder / 'fx_never.txt').write_text('never opened\n')
        (folder / 'manifest.json').write_text(json.dumps(
            {'schema': 'veldo.suites/v1', 'entry': 'selftest.py', 'shared': 'shared.py',
             'suites': [{'name': name, 'file': name + '.py', 'requires': [name], 'regions': 'fixture',
                         'requires_note': 'fixture'} for name in taken_suites]}))
        (folder / 'requires.json').write_text(json.dumps(
            {'schema': 'veldo.suite_requires/v1', 'requires': {name: [name] for name in taken_suites}}))
        return root

    base = top / 'taken'
    tauthority, tcandidate = taken_tree(base / 'authority'), taken_tree(base / 'candidate')
    shutil.copytree(str(ROOT / '.veldo'), str(tauthority / '.veldo'), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', 'events.jsonl', 'last_verify', 'opened_files.json'))
    for relative in ('.veldo/validate.py', '.veldo/shape_gate.py', '.veldo/events.py'):
        (tauthority / relative).write_text(stubs[relative])
    shutil.copyfile(str(candidate_source), str(tauthority / 'scripts/gate_candidate.py'))
    shutil.copyfile(str(sandbox_source), str(tauthority / 'scripts/agent_sandbox.py'))
    shutil.copyfile(str(ROOT / 'scripts/agent_sandbox.json'), str(tauthority / 'scripts/agent_sandbox.json'))
    (tauthority / 'scripts/gate_unconfined.json').write_text(json.dumps({
        'schema': 'veldo.gate-unconfined/v1', 'authority': 'fixture list of the opened-files row',
        'stages': {'unit': 'python3 scripts/selftest.py'},
        'suites': [{'suite': 'fx_forger', 'reason': 'fixture: the forger runs in the unconfined leg'}]}))
    (tauthority / 'scripts/suites/wallclock_baseline.json').write_text(json.dumps(
        {'schema': 'veldo.wallclock-baseline/v1', 'entries': [
            {'class': 'S1', 'count': 1, 'file': f, 'function': '<module>', 'rule': 'R1', 'text': 'fixture entry'}
            for f in ('scripts/suites/fx_forger.py', 'scripts/gate_load.py', 'scripts/suites/fx_data.txt')]}))
    (tauthority / '.veldo/opened_files.json').write_text(json.dumps(forged))
    for folder in ('sink', 'home'):
        (base / folder).mkdir()
    sink_record = base / 'sink/opened_files.json'
    run_env = dict(env, HOME=str(base / 'home'), V358D_MUTATION=str(base / 'mutation'), V358T_FORGE=str(sink_record))
    with open(base / 'log', 'w') as log:
        tcode = subprocess.run(['bash', str(tauthority / 'scripts/verify.sh'), '--candidate', str(tcandidate),
                                '--sink', str(base / 'sink')], cwd=str(base), env=run_env, stdout=log,
                               stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, pass_fds=launcher_fds()).returncode
    tout = (base / 'log').read_text()
    try:
        taken = json.loads(sink_record.read_text())
    except (OSError, ValueError) as error:
        taken = {'unreadable': str(error)}
    tstamp = json.loads((base / 'sink/last_verify').read_text()) if (base / 'sink/last_verify').is_file() else {}
    own = {name: ['scripts/suites/%s.py' % name] for name in taken_suites}
    own['fx_reader'] = sorted(own['fx_reader'] + ['scripts/suites/fx_data.txt'])
    problems = [
        (tcode != 0 or 'GATE: GREEN' not in tout) and 'the gate is not green: status %s' % tcode,
        {k: v for k, v in taken.items() if k != 'shared'} != own
        and 'the record beside the stamp is not the suites\' real opens: %s' % taken,
        'scripts/suites/shared.py' not in taken.get('shared', []) and 'the shared preamble\'s opens are not recorded',
        'FX FORGED A CLAIM' not in tout and 'the forger found no ledger descriptor to forge a claim on',
        'unit: opened-files record taken by the authority: 5 suites' not in tout
        and 'the unit stage does not say the authority took the record',
        '1 claim dropped (never opened)' not in tout and 'the forged claim of a file never opened is not dropped and said',
        '   load-proof: fx_clean: pass, 1 run' not in tout and 'fx_clean, proven by the taken record, did not run once',
        'load-proof: fx_reader' in tout and 'fx_reader, whose opened data file has a baseline entry, ran in the leg',
        (tstamp.get('load') or {}).get('verdict') != 'pass' and 'the stamp has no passing load record: %s' % tstamp.get('load')]
    # Under the scheduler: each unit node takes its leg's part into the scheduler's private directory, and the
    # load node is started only after the authority merged the parts over whatever is beside the stamp.
    parts = top / 'graph/opened-parts'
    parts.mkdir()
    take = gscheduler.command_for(tcandidate, 'unit', 'confined', 'python3 scripts/selftest.py', parts / 'legs',
                                  parts / 'receipt', True, opened_parts=parts)
    (parts / 'opened.confined.json').write_text(json.dumps({'fx_clean': ['scripts/suites/fx_clean.py']}))
    (parts / 'opened.unconfined.json').write_text(json.dumps({'fx_forger': ['scripts/suites/fx_forger.py']}))
    published = parts / 'published.json'
    published.write_text(json.dumps(forged))
    leg_argv = gscheduler.command_for(tcandidate, 'load', None, 'authority load-proof leg', parts / 'legs',
                                      parts / 'receipt', True, load_record=parts / 'load.record',
                                      load_opened=published, opened_parts=parts)
    problems += [
        take[take.index('--take-opened') + 1:take.index('--take-opened') + 2] != [str(parts / 'opened.confined.json')]
        if '--take-opened' in take else 'a unit node does not take its leg\'s record: %s' % take,
        json.loads(published.read_text()) != {'fx_clean': ['scripts/suites/fx_clean.py'],
                                              'fx_forger': ['scripts/suites/fx_forger.py']}
        and 'the load node\'s record is not the merged parts: %s' % published.read_text(),
        leg_argv[-2:] != ['--opened', str(published)] and 'the load node does not read the published record: %s' % leg_argv]
    if any(problems):
        problems.append('gate output: ' + ' | '.join(tout.splitlines()[-40:]))
    row('leg/record-taken-by-the-authority', problems)

    shutil.rmtree(str(top), ignore_errors=True)


_v358d_load_leg()
