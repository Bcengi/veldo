"""VELDO-0278: Tokens of Effort leaves the gate and the mutation sets, and the integration stage
that only guarded its first use leaves with it.

Run: python3 scripts/selftest.py --suite 129_veldo_0278_parked_estimation

Only shared ROOT and expect are consumed. AC1: the unit suite holds none of the eight estimation
fragments, and `python3 scripts/selftest.py --parked estimation` runs all eight green and can never
produce a gate pass. AC2: no registered mutation case mutates an estimation module or runs a parked
suite. AC3: the integration stage is na with its reason, no graph node remains for it, and a
fixture gate over this repository's own verify.sh is green with no integration stage line.
"""


def _v278_checks():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile

    def row(name, condition, detail=''):
        expect('VELDO-0278 ' + name + (': ' + detail if detail and not condition else ''), condition)

    def load(name, path):
        saved = list(sys.path)
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            with contextlib.redirect_stdout(io.StringIO()):
                spec.loader.exec_module(module)
            return module
        finally:
            sys.path[:] = saved

    EIGHT = ['15_warp_1402_estimate_record', '15_warp_1404_historical_analogy',
             '15_warp_1405_reconciliation', '15_warp_1406_normalization', '15_warp_1407_judgment_load',
             '15_warp_1408_budget_rollup', '15_warp_1409_cost_to_change_per_area', '16_warp_1403_sizing_pass']
    PARKED_TOO = EIGHT + ['111_veldo_0214_first_use_budget']
    MODULES = ['toe_analogy', 'toe_budget', 'toe_corpus', 'toe_normalize', 'toe_reconcile', 'estimate',
               'sizing_pass', 'judgment_load', 'cost_to_change']
    REASON = 'estimation layer parked until a spend source exists, VELDO-0278'
    suites = ROOT / 'scripts' / 'suites'
    parked = ROOT / 'scripts' / 'parked' / 'estimation'
    env = {k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')}

    # ---- AC1: the unit stage's suite list holds none of them; the parked set holds them all -------
    manifest = json.loads((suites / 'manifest.json').read_text())
    unit_names = [s['name'] for s in manifest['suites']]
    requires = json.loads((suites / 'requires.json').read_text())['requires']
    named_in_closures = sorted({n for closure in requires.values() for n in closure} & set(PARKED_TOO))
    parked_manifest = json.loads((parked / 'manifest.json').read_text())
    parked_names = [s['name'] for s in parked_manifest['suites']]
    row('parked/unit-list-excludes-estimation',
        not set(PARKED_TOO) & set(unit_names) and not set(PARKED_TOO) & set(requires)
        and not named_in_closures
        and not [n for n in PARKED_TOO if (suites / (n + '.py')).exists()]
        and set(PARKED_TOO) <= set(parked_names)
        and all((parked / s['file']).is_file() and s.get('requires') == [s['name']]
                for s in parked_manifest['suites']),
        repr((sorted(set(PARKED_TOO) & set(unit_names)), named_in_closures, parked_names)))

    run = subprocess.run([sys.executable, 'scripts/selftest.py', '--parked', 'estimation'], cwd=str(ROOT),
                         env=env, capture_output=True, text=True, timeout=3600, stdin=subprocess.DEVNULL)
    out = run.stdout + run.stderr
    per_suite = {m.group(1): (int(m.group(2)), int(m.group(3)))
                 for m in re.finditer(r'^  (\S+)\s+(\d+) passed\s+(\d+) failed', out, re.M)}
    row('parked/command-runs-the-eight-green',
        all(n in per_suite and per_suite[n][0] > 0 and per_suite[n][1] == 0 for n in EIGHT),
        repr((run.returncode, {n: per_suite.get(n) for n in EIGHT},
              [l for l in out.splitlines() if 'SELFTEST FAIL' in l][:5], out[-600:])))
    # A parked run is never a gate pass: it never exits 0, never prints the aggregate line the gate
    # parses, and its scope refuses the verify stamp.
    row('parked/no-gate-pass',
        run.returncode in (1, 2) and not re.search(r'^selftest: \d+ passed, \d+ failed$', out, re.M)
        and 'selftest parked estimation: verify stamp: refused (PARTIAL_RUN_CANNOT_VERIFY)' in out
        and 'verify stamp: ALLOWED' not in out
        and re.search(r'^selftest parked estimation: \d+ passed, \d+ failed in [0-9.]+s \(not a gate result\)$',
                      out, re.M) is not None,
        repr((run.returncode, out[-600:])))

    # ---- AC2: no registered case names an estimation module or a parked suite ----------------------
    teeth = load('v278_teeth', ROOT / 'scripts' / 'check_teeth_mutations.py')
    registered = teeth.cases()
    inputs = json.loads((ROOT / 'scripts' / 'mutation_case_inputs.json').read_text())

    def estimation_case(module, suite):
        return Path(module).stem in MODULES or Path(suite).stem in PARKED_TOO

    named = sorted(c['name'] for c in registered if estimation_case(c['module'], c['suite']))
    declared = []
    for key in inputs['cases']:
        driver, _, name = key.partition(':')
        for case in registered if driver == 'check_teeth_mutations.py' else ():
            if case['name'] == name and estimation_case(case['module'], case['suite']):
                declared.append(key)
    moved_inputs = sorted({f for d in inputs['cases'].values() for f in d['files']
                           if Path(f).stem in PARKED_TOO or f == 'scripts/check_first_use.py'})
    row('mutation/no-estimation-case', registered and not named and not declared and not moved_inputs,
        repr((named, declared, moved_inputs)))

    # ---- AC3: the integration stage is na, its graph node is gone, and its script is parked --------
    verify = (ROOT / 'scripts' / 'verify.sh').read_text()
    catalog = dict(re.findall(r'^CHECK_(\w+)="required:([^"]+)"', verify, re.M))
    declaration = json.loads((ROOT / 'scripts' / 'gate_unconfined.json').read_text())
    schedule = load('v278_schedule', ROOT / 'scripts' / 'gate_schedule.py')
    try:
        graph = schedule.read_graph(catalog, declaration, ROOT / 'scripts' / 'gate_graph.json')[0]
        nodes, refused = set(graph['nodes']), None
    except schedule.Refused as error:
        nodes, refused = set(), str(error)
    row('integration/graph-nodes-are-required-catalog-items',
        refused is None and nodes == set(schedule.required_nodes(catalog, declaration))
        and not [n for n in nodes if n.split('.')[0] == 'integration'],
        repr((refused, sorted(nodes))))
    policy = (ROOT / '.veldo' / 'policy.yaml').read_text()
    row('integration/stage-is-na-and-parked',
        'CHECK_integration="na:%s"' % REASON in verify and 'integration' not in catalog
        and 'integration' not in declaration['stages']
        and not (ROOT / 'scripts' / 'check_first_use.py').exists() and (parked / 'check_first_use.py').is_file()
        and '  - {path: "scripts/parked/estimation/check_first_use.py", floor: high}' in policy.splitlines()
        and '"scripts/check_first_use.py"' not in policy)

    # A fixture gate: this repository's verify.sh over stub stages, no graph, list or host file (so
    # serial, confined whole, unlocked). It is green, its catalog prints integration as na with the
    # reason, no integration stage or node line appears, and the stamp counts it as not applicable.
    stubs = {
        'scripts/gate_candidate.py': 'import subprocess, sys\na = sys.argv\n'
                                     'sys.exit(subprocess.run(a[a.index("--") + 1:]).returncode)\n',
        'scripts/check_gate_mutations.py': 'import sys\nsys.exit(0)\n',
        'scripts/reuse_stamp.py': 'print(\'"force_fresh":false,"reused":{"mutation":0,"unit":0}\')\n',
        'scripts/check_lint.sh': 'exit 0\n', 'scripts/selftest.py': '', 'scripts/secret_inventory.py': '',
        'scripts/check_install_and_run.py': '', 'scripts/check_generated.sh': 'exit 0\n',
        'scripts/check_docs.sh': 'exit 0\n', 'scripts/check_template_sync.sh': 'exit 0\n',
        '.veldo/validate.py': '', '.veldo/shape_gate.py': '', '.veldo/events.py': '',
    }
    with tempfile.TemporaryDirectory(prefix='v278-gate-') as temporary:
        root = Path(temporary) / 'authority'
        for relative, text in stubs.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(text)
        shutil.copyfile(ROOT / 'scripts' / 'verify.sh', root / 'scripts' / 'verify.sh')
        log = root.parent / 'gate.log'
        with open(log, 'w') as handle:
            code = subprocess.run(['bash', str(root / 'scripts' / 'verify.sh')], cwd=str(root), env=env,
                                  stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                  timeout=600, pass_fds=launcher_fds()).returncode
        gate = log.read_text()
        stamp_path = root / '.veldo' / 'last_verify'
        stamp = json.loads(stamp_path.read_text()) if stamp_path.is_file() else None
        na_items = len(re.findall(r'^CHECK_\w+="na:', verify, re.M))
        row('integration/fixture-gate-green-with-na-line',
            code == 0 and gate.rstrip().endswith('GATE: GREEN (no-git)')
            and '== integration: na (%s)' % REASON in gate.splitlines()
            and '== integration' not in [l.rstrip() for l in gate.splitlines()]
            and not re.search(r'^\s*(node )?integration[.:]', gate, re.M)
            and stamp is not None and stamp['status'] == 'green' and stamp['checks_na'] == na_items
            and stamp['checks_run'] == len(catalog),
            repr((code, stamp, gate[-800:])))


_v278_checks()
