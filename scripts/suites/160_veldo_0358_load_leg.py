"""VELDO-0358 brief D: the load generator (AC12) and the load-proof leg (AC13).

load/level-by-construction drives the real scripts/gate_load.py beside a fixture leg: the load record
with every generator alive, load_not_applied when a spinner is killed midway, no generator process
left when the leg itself is killed, and the canary green alone and red inside the load.
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

    # The subjects, each named once so the mutation driver can put a mutant copy in its place.
    load_source = ROOT / "scripts" / "gate_load.py"
    legs_source = ROOT / "scripts" / "gate_legs.py"
    gate_source = ROOT / "scripts" / "verify.sh"

    def row(name, problems):
        problems = [p for p in problems if p]
        expect('VELDO-0358 ' + name + (': ' + '; '.join(problems) if problems else ''), not problems)

    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded

    env = {k: v for k, v in os.environ.items()
           if not k.startswith('VELDO_GATE_') and k not in ('VELDO_OPENED_FILES', 'VELDO_SUITE_ORDER')}
    top = Path(tempfile.mkdtemp(prefix='v358d-'))
    python = sys.executable

    # ------------------------------------------------------------------ AC12: load/level-by-construction
    # The fixture leg: a fixed amount of CPU work in two halves, on the CPUs of the set. With three
    # spinners beside it, it gets a quarter of a CPU, so fifteen CPU-seconds last sixty seconds or more.
    fixture_leg = ('import sys, time\n'
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
            sorted(s['cpu'] for s in spinners) != sorted(start['cpus'] * 3)
            and 'not three spinners on each CPU of the set: %s on %s' % ([s['cpu'] for s in spinners], start['cpus']),
            len(start['cpus']) != 2 and 'the set is not as many CPUs as the leg has slots: %s' % start['cpus'],
            len(writers) != 1 and 'not one writer per four CPUs: %d' % len(writers),
            not all(s['alive'] for s in spinners + writers) and 'a generator was not alive to the end',
            not all(s['cpu_seconds'] > 0 for s in spinners) and 'a spinner consumed no CPU',
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

    # 4. The canary: green alone, red in the fixture leg. Alone means on every CPU this process may
    # use, whatever set an enclosing leg bound it to: the canary is the test of the load, and its
    # control is the same test with no load on its CPUs.
    alone = subprocess.run(
        [python, '-c', 'import os, sys\nos.sched_setaffinity(0, range(os.cpu_count()))\n'
                       'os.execv(sys.executable, [sys.executable, "-I", "-S", sys.argv[1], "--canary"])',
         str(load_source)], stdin=subprocess.DEVNULL, capture_output=True, text=True, env=env)
    start, record, code, lines, gone, left = under_load('canary', [python, '-I', '-S', str(load_source), '--canary'])
    problems += [
        (alone.returncode != 0 or 'canary: green' not in alone.stdout)
        and 'the canary alone is not green: %s %r' % (alone.returncode, alone.stdout + alone.stderr),
        ('canary: red' not in lines or code != 1)
        and 'the canary in the fixture leg is not red: status %s, %s' % (code, [l for l in lines if 'canary' in l]),
        not (record and record['applied']) and 'the canary leg has no applied load record',
        not gone and 'canary: a generator process was left']
    row('load/level-by-construction', problems)

    # ------------------------------------------------------------------------ AC13: leg/proves-and-blocks
    legs = module('v358d_gate_legs', legs_source)
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
        for source in (gate_source, legs_source, load_source, ROOT / 'scripts/selftest.py',
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

    shutil.rmtree(str(top), ignore_errors=True)


_v358d_load_leg()
