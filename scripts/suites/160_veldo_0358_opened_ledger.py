"""VELDO-0358: Authority-owned opening ledger (C18). Real dispatcher, confinement and load-proof fixture.

Each closure runs independently; mutation targets retain their original row labels.
"""


def _v358d_opened_ledger():
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
                       ROOT / 'scripts/run_scope.py', ROOT / 'scripts/gate_fixtures.py'):
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
    shutil.copyfile(str(schedule_source), str(tauthority / 'scripts/gate_schedule.py'))
    gscheduler = module('v358d_opened_schedule', tauthority / 'scripts/gate_schedule.py')
    shutil.copytree(str(ROOT / '.veldo'), str(tauthority / '.veldo'), dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', 'events.jsonl', 'last_verify', 'opened_files.json'))
    for relative in ('.veldo/validate.py', '.veldo/shape_gate.py', '.veldo/events.py'):
        (tauthority / relative).write_text(stubs[relative])
    shutil.copyfile(str(candidate_source), str(tauthority / 'scripts/gate_candidate.py'))
    shutil.copyfile(str(sandbox_source), str(tauthority / 'scripts/agent_sandbox.py'))
    shutil.copyfile(str(ROOT / 'scripts/gate_fixtures.py'), str(tauthority / 'scripts/gate_fixtures.py'))
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
    parts = top / 'opened-parts'
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


_v358d_opened_ledger()
