"""VELDO-0267: each gate runs the mutation cases its candidate's changes select plus fixed canaries;
the full sweep runs nightly on the trunk, and a red nightly sweep blocks landing.

Every falsifier's registered mutation is applied HERE, to an in-memory copy of the module it names
(compiled under the real file name, so its own relative loads still resolve), and the row it targets
is required red on the copy and green on the real module. Fixture repositories, rules, coverage maps,
sweep records and approvals are temporary; nothing reads or writes the owner's state directory.
"""


def _v267_checks():
    import contextlib
    import fnmatch
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import types

    scripts = ROOT / 'scripts'
    # Literal anchors: the registered mutation driver (scripts/check_teeth_mutations.py) substitutes
    # the production copy here, so each registered falsifier also runs against its mutant.
    SELECTION = ROOT / "scripts" / "mutation_selection.py"
    SELECTION_RULE = ROOT / "scripts" / "mutation_selection.json"
    COORDINATOR = ROOT / "scripts" / "check_gate_mutations.py"
    NIGHTLY = ROOT / "scripts" / "mutation_nightly.py"
    POLICY = ROOT / ".veldo" / "policy_check.py"
    LANDER = ROOT / ".veldo" / "lander.py"

    def load(path, replace=()):
        """The module at path, or a copy with each (old, new) applied exactly once. An anchor that is
        not there exactly once leaves the module unchanged, named: its falsifier row then sees no
        difference and is red (the anchor moved, or the registered mutant already removed it)."""
        path = Path(path)
        source = path.read_text()
        for old, new in replace:
            if source.count(old) != 1:
                print('  VELDO-0267 mutation anchor not unique in %s: %r' % (path.name, old[:80]))
                continue
            source = source.replace(old, new)
        module = types.ModuleType('v267_' + path.stem)
        module.__file__ = str(path)
        sys.modules[module.__name__] = module
        exec(compile(source, str(path), 'exec'), module.__dict__)
        return module

    def row(name, condition):
        expect('VELDO-0267 ' + name, bool(condition))

    def falsifier(name, green, red):
        """A registered mutation: its row green on the real module, red on the mutated copy."""
        row('falsifier/' + name, green is True and red is False)

    selection = load(SELECTION)
    gate = load(COORDINATOR)
    gate.ROOT = ROOT

    def git(cwd, *arguments):
        return subprocess.run(['git', '-C', str(cwd), '-c', 'user.name=t', '-c', 'user.email=t@t',
                               '-c', 'commit.gpgsign=false', *arguments], check=True,
                              capture_output=True, text=True).stdout.strip()

    def case(name, module, suite, driver='check_teeth_mutations.py'):
        return {'finding': 267, 'name': name, 'suite': suite, 'module': module, 'old': 'o', 'new': 'n',
                'rows': ['r'], 'driver': driver, 'identity': driver + ':' + name}

    canary_cases = [case('k%d' % i, 'k%d.py' % i, 'k%d.py' % i,
                         'check_review_mutations.py' if i == 1 else 'check_teeth_mutations.py') for i in range(1, 7)]
    A = case('a', 'm1.py', 'sa.py')
    B = case('b', 'mb.py', 's2.py')
    C = case('c', 'mc.py', 'sc.py')
    D = case('d', 'md.py', 'sd.py')
    canaries = {c['identity'] for c in canary_cases}
    base_cases = [A, B, C] + canary_cases

    with tempfile.TemporaryDirectory(prefix='v267-') as temporary:
        top = Path(temporary)
        state = top / 'state'
        rule = json.loads((SELECTION_RULE).read_text())
        rule['canaries'] = sorted(canaries)
        rule['nightly']['state_directory'] = str(state)
        rule_path = top / 'rule.json'
        rule_path.write_text(json.dumps(rule))
        rule = selection.load_rule(rule_path)
        case_inputs = {'schema': 'veldo.case-inputs/v1', 'cases': {},
                       'toolchains': {'check_teeth_mutations.py': {'paths': ['/usr/bin/python3']},
                                      'check_review_mutations.py': {'paths': ['/usr/bin/python3']}}}
        now = time.time()

        def production(path):
            """The .veldo module the suite exercises: the real one, or (a registered mutant, loaded
            from a scratch path) the mutant beside a copy of the real siblings it loads by its own path."""
            path = Path(path)
            if path.parent == ROOT / '.veldo':
                return path
            tree = top / ('production-' + path.name) / '.veldo'
            if not tree.exists():
                shutil.copytree(ROOT / '.veldo', tree, ignore=shutil.ignore_patterns('__pycache__'))
                shutil.copyfile(path, tree / path.name)
            return tree / path.name

        def coverage_for(cases, finished=None, toolchains=None):
            files = {C['identity']: ['lib/shared.py', '.veldo/mc.py']}
            return selection.seal({
                'schema': selection.COVERAGE_SCHEMA, 'run_id': 'nightly-fixture', 'trunk_commit': '0' * 40,
                'finished_at': selection.utc(finished if finished is not None else now - 3600),
                'toolchains': toolchains or selection.toolchain_digests(case_inputs),
                'cases': {c['identity']: {'definition': selection.definition_digest(c),
                                          'files': files.get(c['identity'], [])} for c in cases}})

        coverage = coverage_for(base_cases)

        def choose(module, changed, cases=base_cases, cover=coverage, the_rule=rule, started=None):
            return module.select(cases, the_rule, base='b' * 40, candidate='c' * 40, changed=changed,
                                 coverage=cover, case_inputs=case_inputs, state=None,
                                 started=started if started is not None else now)

        # AC1: the selection over three registered cases.
        def m1_row(module):
            record = choose(module, ['.veldo/m1.py'])
            return module.chosen(record) == {A['identity']} | canaries and record['mode'] == 'selected'

        def shared_row(module):
            record = choose(module, ['lib/shared.py'])
            return (module.chosen(record) == {C['identity']} | canaries
                    and record['cases'][C['identity']]['reasons'] == ['covered_file'])

        def docs_row(module):
            record = choose(module, ['docs/readme.md'])
            return module.chosen(record) == canaries and record['counts']['selected'] == 6

        def new_case_row(module):
            record = choose(module, ['docs/readme.md'], cases=base_cases + [D])
            return (D['identity'] in module.chosen(record)
                    and record['cases'][D['identity']]['reasons'] == ['no_coverage_record'])

        def recompute_row(module):
            record = choose(module, ['.veldo/m1.py', 'scripts/suites/sa.py', 'lib/shared.py'])
            return (selection.recompute(record, base_cases, coverage, case_inputs)
                    and record['cases'][A['identity']]['reasons'] == ['mutated_module', 'suite_file'])

        row('select/m1-selects-a-and-canaries', m1_row(selection))
        row('select/shared-selects-c', shared_row(selection))
        row('select/docs-selects-only-canaries', docs_row(selection))
        row('select/new-case-always-selected', new_case_row(selection))
        row('select/recompute-agrees', recompute_row(selection))
        engine = choose(selection, ['engine/.veldo/m1.py', 'scripts/suites/s2.py'])
        row('select/engine-copy-and-suite-file',
            selection.chosen(engine) == {A['identity'], B['identity']} | canaries
            and engine['cases'][B['identity']]['reasons'] == ['suite_file'])
        changed_definition = dict(B, old='other')
        moved = choose(selection, ['docs/readme.md'], cases=[A, changed_definition, C] + canary_cases)
        row('select/changed-definition-selected', moved['cases'][B['identity']]['reasons'] == ['no_coverage_record'])
        declared = dict(case_inputs, cases={A['identity']: {'files': ['lib/declared.py']}})
        record = selection.select(base_cases, rule, base='b' * 40, candidate='c' * 40, changed=['lib/declared.py'],
                                  coverage=coverage, case_inputs=declared, started=now)
        row('select/declared-inputs-are-the-covered-set',
            record['cases'][A['identity']]['reasons'] == ['covered_file'])

        falsifier('ac1-1-rule-ignores-covered-files', shared_row(selection), shared_row(load(
            SELECTION,
            [("    if changed & covered:\n        reasons.append('covered_file')",
              "    if False:\n        reasons.append('covered_file')")])))
        falsifier('ac1-2-rule-ignores-unknown-case', new_case_row(selection), new_case_row(load(
            SELECTION,
            [("    if known is None or known.get('definition') != definition_digest(case) or (\n"
              "            declared is None and known.get('files') is None):",
              "    if known is not None and (known.get('definition') != definition_digest(case) or (\n"
              "            declared is None and known.get('files') is None)):")])))
        omitted = load(SELECTION,
                       [("entries[case['identity']] = {'selected': bool(reasons), 'reasons': reasons}",
                         "entries[case['identity']] = {'selected': bool(reasons), 'reasons': reasons[:1]}")])
        falsifier('ac1-3-record-omits-a-reason', recompute_row(selection), recompute_row(omitted))

        # AC1: the changed paths, from Git: both sides of a rename and every dirty path.
        repository = top / 'repo'
        repository.mkdir()
        git(repository, 'init', '-q', '-b', 'main')
        (repository / '.veldo').mkdir()
        (repository / '.veldo/m1.py').write_text('x = 1\n' * 20)
        (repository / 'docs').mkdir()
        (repository / 'docs/readme.md').write_text('read me\n')
        git(repository, 'add', '-A')
        git(repository, 'commit', '-q', '-m', 'base')
        base = git(repository, 'rev-parse', 'HEAD')
        git(repository, 'checkout', '-q', '-b', 'work')
        git(repository, 'mv', '.veldo/m1.py', '.veldo/m9.py')
        git(repository, 'commit', '-q', '-m', 'rename')
        (repository / 'docs/readme.md').write_text('dirty\n')
        (repository / 'docs/new.md').write_text('untracked\n')
        head = git(repository, 'rev-parse', 'HEAD')
        runner = selection.git_command(repository)
        changed = selection.changed_paths(runner, selection.merge_base(runner, 'main', head), head)
        row('changed/rename-both-sides-and-dirty',
            changed == ['.veldo/m1.py', '.veldo/m9.py', 'docs/new.md', 'docs/readme.md'])

        # AC1: the record is written before any case runs, and the stamp names its digest.
        common = gate.common_directory(repository)
        evidence = top / 'evidence' / 'mutation-selection.json'
        output = io.StringIO()
        previous = os.environ.get('VELDO_MUTATION_SELECTION')
        os.environ['VELDO_MUTATION_SELECTION'] = str(evidence)
        try:
            with contextlib.redirect_stdout(output):
                written = gate.gate_selection(selection, repository, common, None)(base_cases)
        finally:
            if previous is None:
                os.environ.pop('VELDO_MUTATION_SELECTION', None)
            else:
                os.environ['VELDO_MUTATION_SELECTION'] = previous
        stored = json.loads(evidence.read_text())
        row('record/written-with-line', stored == written and 'mutation selection: mode=' in output.getvalue()
            and 'trigger=selection_unavailable' in output.getvalue())
        cases_run, run_canaries = gate.stage_cases(base_cases, written)
        receipt = {'selection': dict(gate.selection_block(written, base_cases, cases_run, run_canaries),
                                     wall_seconds=1.5)}
        receipt_path = top / 'receipt.json'
        receipt_path.write_text(json.dumps(receipt))
        field = json.loads('{' + selection.stamp_field(receipt_path, evidence) + '}')['mutation']
        evidence.write_bytes(evidence.read_bytes().replace(b'"mode"', b'"mode" '))
        tampered = json.loads('{' + selection.stamp_field(receipt_path, evidence) + '}')['mutation']
        row('record/stamp-names-digest', field and field['digest'] == written['digest'] and field['mode'] == 'full'
            and field['run'] == len(base_cases) and tampered is None)

        # AC1: a landing's gate compares the candidate with the watermark the lander synced. A
        # landing-shaped workspace (a fresh repository: the trunk only as the watermark and the remote
        # ref, HEAD detached on the candidate, no refs/heads/main) is gated through the real lander and
        # control_verification by an installed verifier that runs the real verify.sh base block and the
        # real gate selection; the selection must be made against the watermark, not fall to the sweep.
        landing_ws = top / 'landing-workspace'
        landing_ws.mkdir()
        git(landing_ws, 'init', '-q', '-b', 'scratch')
        (landing_ws / 'scripts/suites').mkdir(parents=True)
        (landing_ws / 'scripts/mutation_case_inputs.json').write_text(json.dumps(case_inputs))
        (landing_ws / 'scripts/suites/manifest.json').write_text(json.dumps(
            {'suites': [{'file': 'k3.py', 'resources': {'systemd_user': 1}}]}))
        (landing_ws / 'docs').mkdir()
        (landing_ws / 'docs/readme.md').write_text('read me\n')
        git(landing_ws, 'add', '-A')
        git(landing_ws, 'commit', '-q', '-m', 'trunk')
        watermark = git(landing_ws, 'rev-parse', 'HEAD')
        git(landing_ws, 'update-ref', 'refs/veldo/candidate/watermark', watermark)
        git(landing_ws, 'update-ref', 'refs/remotes/origin/main', watermark)
        git(landing_ws, 'checkout', '-q', '--detach', watermark)
        git(landing_ws, 'branch', '-q', '-D', 'scratch')
        (landing_ws / 'docs/readme.md').write_text('the candidate\n')
        git(landing_ws, 'commit', '-q', '-am', 'candidate')
        landing_head = git(landing_ws, 'rev-parse', 'HEAD')
        land_state = top / 'land-state'
        land_state.mkdir()
        (land_state / 'coverage.json').write_text(json.dumps(coverage))
        land_rule_path = top / 'land-rule.json'
        land_rule_path.write_text(json.dumps(dict(rule, nightly=dict(rule['nightly'], state_directory=str(land_state)))))
        install = top / 'land-installation'
        (install / 'scripts').mkdir(parents=True)
        config = install / 'config.json'
        config.write_text(json.dumps({'root': str(ROOT), 'selection': str(SELECTION), 'rule': str(land_rule_path),
                                      'cases': base_cases,
                                      'leg': {'suites': ['k2'], 'entries': ['k2']}}))
        driver = install / 'driver.py'
        driver.write_text(
            'import importlib.util, json, os, sys\n'
            'from pathlib import Path\n'
            'config = json.loads(Path(sys.argv[1]).read_text())\n'
            'os.environ.pop("VELDO_MUTATION_SELECTION", None)\n'
            'def load(path, name):\n'
            '    spec = importlib.util.spec_from_file_location(name, path)\n'
            '    module = importlib.util.module_from_spec(spec)\n'
            '    spec.loader.exec_module(module)\n'
            '    return module\n'
            'root = Path(config["root"])\n'
            'selection = load(Path(config["selection"]), "v267_land_selection")\n'
            'plan = selection.plan\n'
            'selection.plan = lambda *a, **k: plan(*a, rule_path=Path(config["rule"]), **k)\n'
            'gate = load(root / "scripts/check_gate_mutations.py", "v267_land_gate")\n'
            'here = Path.cwd()\n'
            'record = gate.gate_selection(selection, here, gate.common_directory(here), config["leg"])(config["cases"])\n'
            'print("v267 landing record " + json.dumps({"mode": record["mode"], "base": record["base"],\n'
            '      "candidate": record["candidate"], "trigger": record["trigger"]}), flush=True)\n')
        verifier = (scripts / 'verify.sh').read_text()
        block_start = verifier.index('if [ -z "${VELDO_GATE_BASE_COMMIT:-}" ]; then')
        block_end = verifier.index('export VELDO_GATE_BASE_COMMIT\n') + len('export VELDO_GATE_BASE_COMMIT\n')
        (install / 'scripts/verify.sh').write_text(
            '#!/usr/bin/env bash\n# veldo-gate-interface: candidate-sink/v1\n'
            + verifier[block_start:block_end]
            + 'exec %s -I -S %s %s\n' % (sys.executable, driver, config))

        def landing_row(module):
            observations = Path(tempfile.mkdtemp(prefix='observations-', dir=top))
            try:
                ops = module.GitLandOps(landing_ws, 'unused', push=False, installation=install,
                                        observations=observations)
                ops.candidate = {'schema': module.CANDIDATE_SCHEMA, 'id': 'candidate-v267', 'state': 'built',
                                 'workspace': str(landing_ws), 'watermark': watermark, 'commit': landing_head}
                ops.gate()
                stdout = json.loads(Path(ops.candidate['gate']['observation']['path']).read_text())['stdout']
            except Exception as error:  # Any failure to drive it is a red row, named.
                print('  VELDO-0267 landing row could not run: %s: %s' % (type(error).__name__, error))
                return False
            found = [json.loads(text.split('v267 landing record ', 1)[1]) for text in stdout.splitlines()
                     if 'v267 landing record ' in text]
            return (len(found) == 1 and found[0]['mode'] == 'selected' and found[0]['trigger'] is None
                    and found[0]['base'] == watermark and found[0]['candidate'] == landing_head
                    and 'mutation selection: mode=selected' in stdout and 'selection_unavailable' not in stdout)

        lander = load(production(LANDER))
        row('landing/gate-selects-against-the-watermark', landing_row(lander))
        falsifier('ac1-4-lander-drops-the-base-hand-off', landing_row(lander), landing_row(load(
            production(LANDER), [('bind_refs=True, base=c["watermark"])', 'bind_refs=True)')])))

        # AC2: the canaries.
        def canary_line(module):
            record = choose(selection, ['docs/readme.md'])
            cases, chosen_canaries = module.stage_cases(base_cases, record)
            block = module.selection_block(record, base_cases, cases, chosen_canaries)
            line = module.verdict_line({'status': 'passed', 'registered': len(cases), 'executed': len(cases),
                                        'reused': 0, 'rejected': len(cases), 'worker_invocations': 3 * len(cases),
                                        'elapsed': 1.0, 'selection': block})
            return line.endswith('mode=selected selected=0 canaries=6') and len(cases) == 6

        row('canary/empty-selection-runs-canaries', canary_line(gate))
        skipping = load(COORDINATOR, [(
            "    chosen = {i for i, e in record['cases'].items() if e['selected']} | canaries\n",
            "    chosen = {i for i, e in record['cases'].items() if e['selected'] and e['reasons'] != ['canary']}\n"
            "    chosen |= canaries if chosen else set()\n"
            "    canaries = canaries & chosen\n")])
        falsifier('ac2-2-coordinator-skips-canaries-on-empty', canary_line(gate), canary_line(skipping))

        observed = [['VELDO r', True]]

        def observation(rows):
            return {'observations': rows, 'count': len(rows), 'row_names': [n for n, _ in rows],
                    'failed_rows': [n for n, ok in rows if not ok], 'failed_details': []}

        def result_for(c, baseline, mutant):
            return {'schema': gate.SCHEMA, 'case': c, 'fixture_version': gate.FIXTURE_VERSION,
                    'replacement_count': 1, 'old_digest': '1', 'new_digest': '2',
                    'baseline': observation(baseline), 'noop': observation(baseline),
                    'mutant': observation(mutant)}

        def canary_judged(module):
            canary = canary_cases[1]
            honest = result_for(canary, observed, [['VELDO r', False]])
            # A broken worker reports every row killed without running anything: baseline included.
            broken = result_for(canary, [['VELDO r', False]], [['VELDO r', False]])
            try:
                module.judge_canary(canary, honest)
            except module.Refused:
                return False
            try:
                module.judge_canary(canary, broken)
            except module.Refused as error:
                return error.code == 'canary_not_killed' and canary['identity'] in error.detail
            return False

        row('canary/broken-worker-reds-stage', canary_judged(gate))
        falsifier('ac2-1-worker-reports-every-mutant-killed', canary_judged(gate), canary_judged(load(
            COORDINATOR,
            [('        return validate_result(record, case)\n    except Refused as error:\n        raise Refused(CANARY',
              '        return record\n    except Refused as error:\n        raise Refused(CANARY')])))

        def declaration(path):
            try:
                selection.load_rule(path)
                return True, ''
            except selection.Invalid as error:
                return False, str(error)

        emptied = top / 'emptied.json'
        emptied.write_text(json.dumps(dict(json.loads((SELECTION_RULE).read_text()), canaries=[])))
        valid, _ = declaration(SELECTION_RULE)
        real_rule = selection.load_rule(SELECTION_RULE) if valid else None
        emptied_valid, why = declaration(emptied)
        row('canary/declaration-valid', valid and 6 <= len(real_rule['canaries']) <= 12)
        falsifier('ac2-3-canary-list-emptied', valid, emptied_valid)
        row('canary/emptied-names-the-bound-of-six', 'between six and twelve' in why and 'found 0' in why)
        teeth = load(scripts / 'check_teeth_mutations.py')
        review = load(scripts / 'check_review_mutations.py')
        inventory = [dict(c, driver=d, identity=d + ':' + c['name'])
                     for d, module in (('check_teeth_mutations.py', teeth), ('check_review_mutations.py', review))
                     for c in module.cases()]
        legs = load(scripts / 'gate_legs.py')
        leg = legs.mutation_leg()
        manifest = json.loads((scripts / 'suites/manifest.json').read_text())
        demands = {s['file']: s.get('resources') or {} for s in manifest['suites']}
        try:
            if real_rule is None:
                raise selection.Invalid('the declaration does not load')
            selection.check_canaries(real_rule, inventory, lambda c: gate.in_leg(leg, c),
                                     lambda c: demands.get(c['suite']))
            covered = True
        except selection.Invalid:
            covered = False
        row('canary/declaration-covers-drivers-legs-fixture', covered)

        # AC3: the full sweep and its named trigger.
        def full_for(path, the_rule=rule):
            record = choose(selection, [path, 'docs/readme.md'], the_rule=the_rule)
            return (record['mode'] == 'full' and record['trigger']['kind'] == 'trigger_path'
                    and record['trigger']['path'] == path and selection.chosen(record) == {c['identity'] for c in base_cases})

        groups = ['scripts/check_teeth_mutations.py', 'scripts/check_review_mutations.py',
                  'scripts/check_gate_mutations.py', 'engine/scripts/check_gate_mutations.py',
                  'scripts/mutation_selection.py', 'engine/scripts/mutation_selection.py',
                  'scripts/mutation_selection.json', 'scripts/mutation_case_inputs.json',
                  'scripts/mutation_observer.py', 'engine/scripts/mutation_reuse.py', 'scripts/mutation_nightly.py',
                  'scripts/case_trace.py', 'engine/scripts/case_inputs.py', 'scripts/gate_schedule.py',
                  'engine/scripts/gate_schedule.py', 'scripts/gate_host.py', 'engine/scripts/gate_host.py',
                  'scripts/gate_host.json', 'scripts/verify.sh', 'engine/scripts/verify.sh', 'scripts/gate_graph.json',
                  'scripts/gate_legs.py', 'engine/scripts/gate_legs.py', 'scripts/gate_unconfined.json',
                  'scripts/gate_candidate.py', 'engine/scripts/gate_candidate.py', 'scripts/suites/shared.py',
                  'scripts/suites/manifest.json']
        missed = [path for path in groups if not full_for(path)]
        row('trigger/every-group-forces-full', not missed)
        if missed:
            print('  VELDO-0267 trigger rows missed: ' + ', '.join(missed))
        dropped = dict(rule, triggers=[t for t in rule['triggers']
                                       if not fnmatch.fnmatchcase('scripts/mutation_selection.py', t)])
        falsifier('ac3-1-trigger-list-drops-mutation-selection', full_for('scripts/mutation_selection.py'),
                  full_for('scripts/mutation_selection.py', dropped))

        def reason(record, kind):
            return record['mode'] == 'full' and record['trigger']['kind'] == kind and len(selection.chosen(record)) == len(base_cases)

        missing = selection.select(base_cases, rule, base='b' * 40, candidate='c' * 40, changed=['docs/readme.md'],
                                   coverage=selection.Invalid('coverage map missing'), case_inputs=case_inputs,
                                   started=now)
        row('trigger/coverage-missing', reason(missing, 'coverage_missing'))
        unreadable = state / 'coverage.json'
        unreadable.parent.mkdir(parents=True, exist_ok=True)
        unreadable.write_text('{"schema": "veldo.mutation-coverage/v1"')
        try:
            selection.load_coverage(unreadable)
            refused = False
        except selection.Invalid as error:
            refused = 'unreadable' in str(error)
        row('trigger/coverage-unreadable', refused)
        unreadable.unlink()

        def stale_row(module):
            aged = coverage_for(base_cases, finished=now - 37 * 3600)
            record = module.select(base_cases, rule, base='b' * 40, candidate='c' * 40, changed=['docs/readme.md'],
                                   coverage=aged, case_inputs=case_inputs, started=now)
            fresh = module.select(base_cases, rule, base='b' * 40, candidate='c' * 40, changed=['docs/readme.md'],
                                  coverage=coverage_for(base_cases, finished=now - 35 * 3600),
                                  case_inputs=case_inputs, started=now)
            return reason(record, 'nightly_stale') and fresh['mode'] == 'selected'

        row('trigger/nightly-stale', stale_row(selection))
        falsifier('ac3-2-age-bound-skipped', stale_row(selection), stale_row(load(
            SELECTION, [('        if started - finished > limit:', '        if False:')])))
        altered = dict(selection.toolchain_digests(case_inputs))
        altered['check_review_mutations.py'] = '0' * 64
        toolchain = selection.select(base_cases, rule, base='b' * 40, candidate='c' * 40, changed=['docs/readme.md'],
                                     coverage=coverage_for(base_cases, toolchains=altered), case_inputs=case_inputs,
                                     started=now)
        row('trigger/toolchain-changed', reason(toolchain, 'toolchain_changed')
            and 'check_review_mutations.py' in toolchain['trigger']['detail'])
        unavailable = selection.select(base_cases, rule, base=None, candidate='c' * 40, error='no base')
        row('trigger/unavailable-runs-full', reason(unavailable, 'selection_unavailable'))

        # AC4: the nightly runner over a fixture trunk, a fake lock holder and a fake sweep.
        trunk = top / 'trunk'
        trunk.mkdir()
        git(trunk, 'init', '-q', '-b', 'main')
        (trunk / 'scripts').mkdir()
        (trunk / 'scripts/mutation_case_inputs.json').write_text(json.dumps(case_inputs))
        git(trunk, 'add', '-A')
        git(trunk, 'commit', '-q', '-m', 'trunk')
        trunk_commit = git(trunk, 'rev-parse', 'HEAD')
        calls = top / 'notified.txt'
        notifier = [sys.executable, '-c', 'import sys; open(sys.argv[1], "a").write(sys.argv[2] + "\\n")', str(calls)]
        survivor = case('survivor', 'mx.py', 'sx.py')
        lock = top / 'host.lock'

        def sweep_receipt(green):
            results = [{'case': c} for c in [A, survivor]]
            receipt = {'status': 'passed' if green else 'failed', 'registered': 2, 'executed': 2, 'reused': 0,
                       'rejected': 2 if green else 1, 'worker_invocations': 6, 'elapsed': 1.0, 'results': results,
                       'coverage_traces': {A['identity']: ['.veldo/m1.py'], survivor['identity']: ['lib/x.py']},
                       'invalid_results': []}
            if not green:
                receipt.update(error='mutation_survived', detail='r', invalid_results=[
                    {'case': survivor, 'error': 'mutation_survived', 'detail': 'VELDO r'}])
            return receipt

        def nightly(module, green, holder_seconds=0.0):
            """Run one sweep; (record, sweep start, holder release) in monotonic seconds."""
            seen = {}

            def sweep(checkout, receipt_path):
                seen['start'] = time.monotonic()
                seen['checkout'] = (checkout / 'scripts/mutation_case_inputs.json').is_file()
                return sweep_receipt(green)

            released = None
            holder = None
            if holder_seconds:
                ready = top / ('holding-%d' % len(os.listdir(top)))
                holder = subprocess.Popen([sys.executable, '-c', (
                    'import fcntl, os, sys, time\n'
                    'fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT)\n'
                    'fcntl.flock(fd, fcntl.LOCK_EX)\n'
                    'open(sys.argv[2], "w").close()\n'
                    'time.sleep(float(sys.argv[3]))\n'), str(lock), str(ready), str(holder_seconds)])
                late = wait_for(lambda: (ready.exists(), ready.exists()),
                                (30, 'a python start and one flock, generous on a loaded gate host'),
                                'the fake lock holder')
                if late:
                    raise AssertionError(late)
                released = time.monotonic() + holder_seconds
            runner = module.Runner(root=trunk, state=state, trunk='main', lock=str(lock), notifier=notifier, sweep=sweep)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                record = runner.run()
            if holder is not None:
                holder.wait(timeout=60)
            return record, seen, released, output.getvalue()

        nightly_module = load(NIGHTLY)

        def lock_row(module):
            record, seen, released, text = nightly(module, True, holder_seconds=1.5)
            return (seen['start'] >= released - 0.2 and record['lock_wait_seconds'] >= 1.0
                    and record['verdict'] == 'green' and seen['checkout'] and 'took the host lock' in text)

        row('nightly/waits-for-lock-then-sweeps', lock_row(nightly_module))
        falsifier('ac4-1-runner-skips-lock', lock_row(nightly_module), lock_row(load(
            NIGHTLY, [('    fcntl.flock(fd, fcntl.LOCK_EX)\n', '    pass\n')])))
        published = json.loads((state / 'coverage.json').read_text())
        row('nightly/green-publishes-coverage', published['trunk_commit'] == trunk_commit
            and selection.load_coverage(state / 'coverage.json')['cases'][A['identity']]['files'] == ['.veldo/m1.py'])

        def publish_row(module):
            before = (state / 'coverage.json').read_bytes()
            record, _, _, text = nightly(module, False)
            unchanged = (state / 'coverage.json').read_bytes() == before
            return record['verdict'] == 'red' and record['coverage'] is None and unchanged, record, text

        calls.write_text('')
        red_ok, red, red_text = publish_row(nightly_module)
        notes = calls.read_text().splitlines()
        row('nightly/red-record-names-case', red_ok and red['failures'][0]['case'] == survivor['identity']
            and red['trunk_commit'] == trunk_commit and 'mutations: failed registered=2' in red_text)
        row('nightly/one-notifier-call-naming-case', len(notes) == 1 and survivor['identity'] in notes[0]
            and trunk_commit[:12] in notes[0])
        publishing = load(NIGHTLY, [
            ('            if green:\n                try:\n                    published = coverage_map(',
             '            if True:\n                try:\n                    published = coverage_map(')])
        mutated_publish = publish_row(publishing)[0]
        falsifier('ac4-3-red-sweep-publishes-coverage', red_ok, mutated_publish)

        # The landing check, through the installed policy module's own reader and its own approval
        # rule (valid_approval_for): the subject is a repository whose push is base..work, its proof
        # names the producer, and an approval counts only bound to a commit of the push and approved
        # by someone who is not the producer.
        subject = top / 'subject'
        (subject / 'proof/VELDO-9999').mkdir(parents=True)
        git(subject, 'init', '-q', '-b', 'main')
        (subject / 'base.txt').write_text('base\n')
        git(subject, 'add', 'base.txt')
        git(subject, 'commit', '-q', '-m', 'base')
        subject_base = git(subject, 'rev-parse', 'HEAD')
        (subject / 'work.txt').write_text('work\n')
        git(subject, 'add', 'work.txt')
        git(subject, 'commit', '-q', '-m', 'work')
        subject_work = git(subject, 'rev-parse', 'HEAD')
        (subject / 'proof/VELDO-9999/manifest.json').write_text(json.dumps({'producer': 'agent-builder'}))
        (subject / 'proof/VELDO-9999/verdict.json').write_text(json.dumps(
            {'spec_id': 'VELDO-9999', 'commit': subject_work}))
        reader = load(SELECTION)
        reader.RULE = rule_path

        def policy_module(replace=()):
            module = load(production(POLICY), replace)
            module.ROOT = subject
            module.BASE = subject_base
            module._nightly_reader = lambda: reader
            return module

        policy = policy_module()

        def approve(run_id, cases, name, approver='owner', commit=None):
            scope = {'nightly_run': run_id, 'cases': cases}
            if commit is not None:
                scope['commit'] = commit
            (subject / 'proof/VELDO-9999' / name).write_text(json.dumps({
                'schema': 'veldo.approval/v1', 'decision': 'approved', 'approver': approver,
                'scope': scope, 'expires_at': '2999-01-01T00:00:00Z'}))

        def blocks_row(module):
            reader.landing_refusal = module.landing_refusal
            refused = policy.nightly_refusal()
            return bool(refused) and refused.startswith('nightly_red') and survivor['identity'] in refused

        real_landing = reader.landing_refusal
        row('landing/red-blocks', blocks_row(reader))
        greens_only = load(SELECTION, [
            ('without approval."""\n    records = sweeps(state)\n',
             "without approval.\"\"\"\n    records = [r for r in sweeps(state) if r['verdict'] == 'green']\n")])
        falsifier('ac4-2-landing-reads-only-green', blocks_row(reader), blocks_row(greens_only))
        reader.landing_refusal = real_landing
        approve('nightly-some-other-run', {survivor['identity']: 'known flake'}, 'approval-other.json',
                commit=subject_work)
        row('landing/other-run-id-does-not-clear', bool(policy.nightly_refusal()))
        latest = reader.sweeps(state)[-1]
        row('landing/latest-is-red', latest['verdict'] == 'red')
        reason_given = {survivor['identity']: 'accepted until the fix lands'}
        approve(latest['run_id'], reason_given, 'approval-unbound.json')
        row('landing/unbound-approval-does-not-clear', bool(policy.nightly_refusal()))
        (subject / 'proof/VELDO-9999/approval-unbound.json').unlink()

        def self_approval_row(module):
            """The producer's own approval, bound and naming the run and case, does not clear."""
            approve(latest['run_id'], reason_given, 'approval-self.json', approver='agent-builder',
                    commit=subject_work)
            try:
                return bool(module.nightly_refusal())
            finally:
                (subject / 'proof/VELDO-9999/approval-self.json').unlink()

        row('landing/self-approval-does-not-clear', self_approval_row(policy))
        falsifier('ac4-4-self-approval-accepted', self_approval_row(policy), self_approval_row(policy_module([
            ('            continue  # self-approval: the approver produced the work',
             '            pass  # self-approval: the approver produced the work')])))
        approve(latest['run_id'], reason_given, 'approval-owner.json', commit=subject_work)
        row('landing/approval-clears', policy.nightly_refusal() is None)
        (subject / 'proof/VELDO-9999/approval-owner.json').unlink()
        row('landing/red-again-without-approval', bool(policy.nightly_refusal()))
        nightly(nightly_module, True)
        row('landing/later-green-clears', policy.nightly_refusal() is None)


_v267_checks()
