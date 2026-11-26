"""VELDO-0367 increment 3 review regressions and inactive runner adapters."""


def _v367_repairs():
    import contextlib
    import copy
    import importlib.util
    import io
    import json
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    # Literal production anchors are also used by the mutation worker.
    sources = {'gate_changes.py': ROOT / "scripts" / "gate_changes.py",
               'mutation_reuse.py': ROOT / "scripts" / "mutation_reuse.py",
               'mutation_observer.py': ROOT / "scripts" / "mutation_observer.py",
               'check_gate_mutations.py': ROOT / "scripts" / "check_gate_mutations.py",
               'run_scope.py': ROOT / "scripts" / "run_scope.py",
               'selftest.py': ROOT / "scripts" / "selftest.py",
               'check_first_use.py': ROOT / "scripts" / "check_first_use.py"}

    def load(path):
        spec = importlib.util.spec_from_file_location('repair367_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def row(name, condition):
        expect('VELDO-0367 repair/' + name, condition)

    def refuses(call):
        try:
            call()
        except (ValueError, RuntimeError, KeyError, TypeError):
            return True
        except Exception as error:
            if hasattr(error, 'code'):
                return True
            raise
        return False

    with tempfile.TemporaryDirectory(prefix='selection-repairs-') as temporary:
        top = Path(temporary)
        authority, repo = top / 'authority', top / 'repo'
        (authority / 'scripts/suites').mkdir(parents=True)
        (authority / '.veldo').mkdir()
        for name in (*sources, 'gate_reuse.py', 'case_inputs.py', 'gate_fixtures.py', 'case_trace.py'):
            shutil.copyfile(sources.get(name, ROOT / 'scripts' / name), authority / 'scripts' / name)
        shutil.copyfile(ROOT / '.veldo/reuse_evidence.py', authority / '.veldo/reuse_evidence.py')
        C, R, M, O, G, RS, FU = [load(authority / 'scripts' / n) for n in
            ('gate_changes.py', 'gate_reuse.py', 'mutation_reuse.py', 'mutation_observer.py',
             'check_gate_mutations.py', 'run_scope.py', 'check_first_use.py')]
        for relative in R.E.AUTHORITY_FILES:
            path = authority / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# fixture authority\n')
        runtime = C.digest('fixture runtime')
        def seal(record, **fields):
            return C.sealed(record['schema'], **dict({k: v for k, v in record.items()
                if k not in ('schema', 'record_digest')}, **fields))
        repo.mkdir()
        def git(*args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()
        git('init', '-q')
        git('config', 'user.name', 'Dmitry Grinberg')
        git('config', 'user.email', 'dmitry@example.invalid')
        (repo / 'input').write_text('before')
        git('add', '.')
        git('commit', '-qm', 'seed')
        a = git('rev-parse', 'HEAD')
        (repo / 'input').write_text('after')
        git('add', '.')
        git('commit', '-qm', 'dependency')
        b = git('rev-parse', 'HEAD')
        (repo / 'unrelated').write_text('new')
        git('add', '.')
        git('commit', '-qm', 'unrelated')
        c = git('rev-parse', 'HEAD')
        dep = C.sealed(C.DEPENDENCY, item_id='item', observed_commit=a, paths=['input'],
            directories=[], absent_paths=[], runtime_digest=runtime, complete=True, unknown_reason=None)
        checks = []
        for field in ('paths', 'absent_paths', 'directories'):
            for recorded, changed in [('a/b', 'a/b/child'), ('a/b/child', 'a/b')]:
                fields = dict(paths=[], absent_paths=[], directories=[])
                fields[field] = [recorded]
                checks.append(C.intersects(seal(dep, **fields), [changed]))
        row('prefix-both-ways', all(checks) and not C.intersects(seal(dep, paths=['a/b']), ['a/bc']))
        merged = O.combine_dependencies([dep, dep], 'item', a)
        repeated = O.combine_dependencies([merged, dep], 'item', b, prior=merged, rows=True)
        row('runtime-stable', merged['runtime_digest'] == runtime and repeated['runtime_digest'] == runtime)

        def inventory(names):
            return C.inventory([dict(item_id=n, definition_digest=C.digest(n), state='required', reason=None)
                                for n in names])
        def entry(store, dependency, result=None):
            if result is None:
                result = C.sealed(C.RESULT, item_id=dependency['item_id'], source_commit=dependency['observed_commit'],
                    status='passed', complete=True, dependency_record_digest=dependency['record_digest'])
            store.change_put(dependency)
            store.change_put(result)
            return dict(item_id=dependency['item_id'], status='executed',
                dependency_record_digest=dependency['record_digest'], result_digest=result['record_digest'],
                source_commit=dependency['observed_commit'], source_gate_digest=None)
        def gate(store, current, commit, entries, prior=None):
            receipt = C.sealed(C.RECEIPT, candidate_commit=commit,
                baseline_commit=prior['receipt']['candidate_commit'] if prior else None,
                baseline_record_digest=prior['record_digest'] if prior else None,
                changed_paths_digest=C.digest(C.changed_paths(repo, prior['receipt']['candidate_commit'], commit)
                                             if prior else None),
                inventory_digest=current['record_digest'], items=entries)
            return C.sealed(C.GATE, repository='fixture', inventory=current, receipt=receipt,
                            status='green', complete=True)
        store = R.Store(top / 'store', repo)
        current = inventory(['item'])
        original = entry(store, dep)
        seed = gate(store, current, a, [original])
        store.publish_change_gate(seed)
        carry = dict(original, status='carried', source_gate_digest=seed['record_digest'])
        stale = gate(store, current, b, [carry], seed)
        # Model a historical authenticated bad carry. Landing must recheck its original source.
        store.change_put(stale)
        store.put(store.change_gate_key('fixture', b),
                  dict(repository='fixture', commit=b, record_digest=stale['record_digest']))
        planned = C.select(repo, store, 'fixture', c, current, {'item': runtime})
        row('source-range-selection', planned['items'][0]['status'] == 'run')
        downstream = gate(store, current, c, [carry], stale)
        row('source-range-landing', refuses(lambda: C.green_record(repo, store, downstream, 'fixture')))

        # Same-commit full refresh must append, and corrupt/conflicting successors must not revive G1.
        for damage in ('conflict', 'corrupt'):
            cache = R.Store(top / damage, repo)
            e = entry(cache, dep)
            first = gate(cache, current, a, [e])
            cache.publish_change_gate(first)
            skey = C.successor_key('fixture', a, first['record_digest'])
            path = cache._path(skey)
            if damage == 'conflict':
                path.with_suffix('.json.conflict').write_text('conflicting publication')
            else:
                path.write_text('corrupt record')
            row('successor-' + damage, C.eligible_baseline(repo, cache, 'fixture', a) is None)
        cache = R.Store(top / 'refresh', repo)
        e = entry(cache, dep)
        first = gate(cache, current, a, [e])
        cache.publish_change_gate(first)
        refreshed_entry = entry(cache, seal(dep, paths=['input', 'setup']))
        refresh = gate(cache, current, a, [refreshed_entry])
        try:
            published = C.publish_gate(repo, cache, 'fixture', current, refresh['receipt'])
        except ValueError:
            published = None
        row('full-refresh', published == refresh and C.eligible_baseline(repo, cache, 'fixture', a) == refresh)

        case = dict(identity='driver:case', name='case', driver='driver', suite='fixture.py',
            module='one.py', rows=['target', 'second'], old='True', new='False', dir='.veldo')
        other = dict(case, identity='driver:other', name='other', module='two.py')
        configuration = dict(leg='confined', runtime_digest=runtime, fixture_configuration={})
        suite = M.suite_identity(case, configuration)
        def observation(rows, dependency=dep):
            return dict(count=len(rows), observations=rows, row_names=[n for n, _ in rows],
                failed_rows=[n for n, ok in rows if ok is False], dependency=dependency)
        honest = observation([['fixture target', True], ['fixture second', True]])
        baseline = json.loads((ROOT / 'scripts/suites/wallclock_baseline.json').read_text())
        baseline['entries'].append(dict(file='scripts/suites/fixture.py', count=1))
        (authority / 'scripts/suites/wallclock_baseline.json').write_text(json.dumps(baseline))
        controls = C.sealed(M.CONTROL_RECORD, suite=suite, cases=[case, other], source_commit=a,
                           dependency=dep, baseline=honest, noop=honest)
        store.change_put(controls)
        prior_result = dict(schema=G.SCHEMA, case=case, fixture_version=G.FIXTURE_VERSION,
            input_digest=C.digest(case), replacement_count=1, old_digest=C.digest('old'), new_digest=C.digest('new'),
            baseline=honest, noop=honest,
            mutant=observation([['fixture target', False], ['fixture second', True]]))
        G.validate_result(prior_result, case, store=store)
        prior = C.sealed(M.KILL_RECORD, source_commit=a, dependency=dep, result=prior_result)
        store.change_put(prior)
        validate = lambda result, definition: G.validate_result(result, definition, store=store)
        row('baselined-prior', M.prior_killing_rows(store, prior['record_digest'], case, validate) == ['fixture target'])
        mutant = observation([['fixture target', False]])
        scoped = dict(prior_result, schema=M.SCOPED_RESULT, execution_scope='rows', selected_rows=['fixture target'],
            observed_rows=['fixture target'], mutant=mutant, prior_kill_receipt_digest=prior['record_digest'],
            control_receipt_digest=controls['record_digest'],
            attempts=[dict(execution_scope='rows', selected_rows=['fixture target'], observation=mutant)])
        row('baselined-scope', not refuses(lambda: validate(copy.deepcopy(scoped), case)))
        invalid_failure = copy.deepcopy(scoped)
        invalid_failure['mutant']['failure_kinds'] = {'fixture target': 'timeout'}
        invalid_failure['attempts'][-1]['observation'] = invalid_failure['mutant']
        row('invalid-failure-kind', refuses(lambda: validate(invalid_failure, case)))
        item_id = C.identity('case', 'mutation', 'confined', case['suite'], case['driver'], case['name'])
        def mutation_entry(dependency, result):
            dependency = seal(dependency, item_id=item_id)
            envelope = C.sealed(M.KILL_RECORD, source_commit=a, dependency=dependency, result=result)
            store.change_put(envelope)
            outcome = C.sealed(C.RESULT_V2, item_id=item_id, source_commit=a, status='passed', complete=True,
                dependency_record_digest=dependency['record_digest'], execution_record_digest=envelope['record_digest'])
            return entry(store, dependency, outcome)
        row('baselined-landing', not refuses(lambda: C.item_evidence(store, mutation_entry(dep, scoped))))
        for retained in ('controls', 'prior'):
            for field in ('paths', 'directories', 'absent_paths', 'complete'):
                old = controls if retained == 'controls' else prior
                changed_dep = (seal(dep, complete=False, unknown_reason='lost') if field == 'complete'
                               else seal(dep, **{field: sorted(set(dep[field]) | {'hidden'})}))
                changed_record = seal(old, dependency=changed_dep)
                store.change_put(changed_record)
                altered = dict(scoped, **{('control_receipt_digest' if retained == 'controls'
                                          else 'prior_kill_receipt_digest'): changed_record['record_digest']})
                row('retain-' + retained + '-' + field,
                    refuses(lambda: C.item_evidence(store, mutation_entry(dep, altered))))

        source = 'expect("first target", calls.append("first"))\nexpect("second target", calls.append("second"))\n'
        calls = []
        try:
            exec(C.row_source(source, ['first target']), {'expect': lambda *args: None, 'calls': calls})
        except ValueError:
            pass
        row('exact-row', calls == ['first'])
        row('renamed-row', refuses(lambda: C.row_source(source, ['old target'])))
        leg = dict(suites=['fixture'], entries=['fixture:strace'], declaration=C.digest('leg'))
        row('row-leg-priority', not G.in_leg(leg, case, suite_leg='unconfined',
            selected_rows=['fixture target'], row_legs={'fixture target': 'confined'}))

        # Exercise production control construction and a later selected case with carried controls.
        frozen = top / 'frozen'
        (frozen / '.veldo').mkdir(parents=True)
        (frozen / 'scripts/suites').mkdir(parents=True)
        for name in ('one.py', 'two.py'):
            (frozen / '.veldo' / name).write_text('True\nSECOND\n')
        suite_file = frozen / 'scripts/suites/fixture.py'
        suite_source = ('one = ROOT / ".veldo" / "one.py"\ntwo = ROOT / ".veldo" / "two.py"\n'
                        'expect("fixture target", True)\nexpect("fixture second", True)\n')
        suite_file.write_text(suite_source)
        worker_calls = []
        active_commit = [a]
        def workers_run(jobs, directory, root):
            worker_calls.extend(job['mode'] for job in jobs.values())
            results = {}
            for name, job in jobs.items():
                reads = seal(dep, observed_commit=active_commit[0])
                observed = observation([['fixture target', False]] if job['mode'] == 'mutant' and
                    'selected_rows' in job else [['fixture target', job['mode'] != 'mutant'], ['fixture second', True]], reads)
                results[name] = dict(result=dict(observation=observed, replacement_count=1,
                    old_digest=C.digest('old'), new_digest=C.digest('new')))
            return results
        workers = SimpleNamespace(run=workers_run, active={}, meters={}, owned_snapshots={})
        configs = {member['identity']: configuration for member in (case, other)}
        original_load = G.load
        def modules(path):
            return {'mutation_reuse.py': M, 'mutation_observer.py': O}.get(Path(path).name) or original_load(path)
        def selected(members, **kwargs):
            return G.run_selected_cases(workers, [case], top, frozen, store=store, commit=active_commit[0],
                changed=['unrelated'], configurations=configs, registered_cases=members, **kwargs)
        with patch.object(C, 'SELECTION_ENABLED', True), patch.object(M, 'change_module', return_value=C), \
                patch.object(G, 'load', side_effect=modules):
            fresh = selected([case, other])
            fresh_result = store.get(fresh[case['identity']]['result_digest'])
            fresh_kill = store.get(fresh_result['execution_record_digest'])
            control_key = fresh_kill['result']['control_receipt_digest']
            worker_calls.clear()
            active_commit[0] = c
            try:
                carried_results = selected([case, other], prior_controls={C.digest(suite): control_key},
                    prior_kills={case['identity']: fresh_kill['record_digest']})
                carried_dep = store.get(carried_results[case['identity']]['dependency_record_digest'])
            except G.Refused:
                carried_dep = None
            row('carried-control-complete', worker_calls == ['mutant'] and carried_dep is not None and
                carried_dep['complete'] and carried_dep['observed_commit'] == c and
                carried_dep['runtime_digest'] == runtime)
            active_commit[0] = a
            bad_other = dict(other, also=[['missing secondary anchor', 'replacement']])
            row('secondary-wiring', refuses(lambda: selected([case, bad_other])))
            suite_file.write_text(suite_source.replace('two = ROOT / ".veldo" / "two.py"\n', ''))
            row('production-wiring', refuses(lambda: selected([case, other])))
            suite_file.write_text(suite_source)
        # Inspect the actual launch environment without launching a worker or installing a layer.
        environment = []
        def capture(*args, **kwargs):
            environment.append(kwargs['env'])
            raise OSError('fixture stopped before launch')
        resources = G.SuiteResources(dict(suites=[dict(file='fixture.py')]))
        real_workers = G.Workers(resources=resources, parallel=1)
        real_workers.leg = leg
        launch_dir = top / 'launch'; launch_dir.mkdir()
        with patch.object(G.subprocess, 'Popen', side_effect=capture), \
                patch.object(real_workers, 'launcher_fds', return_value=()):
            refuses(lambda: real_workers.run({'case': dict(case=case, mode='mutant',
                selected_rows=['fixture target'], row_legs={'fixture target': 'confined'})}, launch_dir, frozen))
        row('row-leg-environment', len(environment) == 1 and environment[0].get('VELDO_GATE_LEG') == 'confined'
            and environment[0].get('VELDO_GATE_UNCONFINED') == 'fixture:strace'
            and environment[0].get('VELDO_GATE_DECLARATION') == leg['declaration'])

        # Adapter fixtures use real selection and authenticated original provenance.
        names = ['selected', 'carried', 'unknown']
        manifest = dict(shared='shared.py', suites=[dict(name=n, file=n + '.py', requires=[n]) for n in names])
        requires = {n: [n] for n in names}
        cache = R.Store(top / 'adapters', repo)
        ids = {n: C.identity('suite', 'integration', 'confined', n) for n in names}
        inv = inventory(ids.values())
        entries = [entry(cache, seal(dep, item_id=ids[n], paths=['input'] if n == 'selected' else ['stable'],
            complete=n != 'unknown', unknown_reason='missing trace' if n == 'unknown' else None)) for n in names]
        initial = gate(cache, inv, a, entries)
        cache.publish_change_gate(initial)
        context = dict(root=repo, store=cache, repository='fixture', candidate_commit=c, inventory=inv,
                       runtimes=dict.fromkeys(ids.values(), runtime), stage='integration', leg='confined')
        # Use the adapter's actual sibling loader; only the switch is enabled in this fixture copy.
        changes_path = authority / 'scripts/gate_changes.py'
        changes_path.write_text(changes_path.read_text().replace('SELECTION_ENABLED = False', 'SELECTION_ENABLED = True'))
        (authority / 'scripts/suites/manifest.json').write_text(json.dumps(manifest))
        (authority / 'scripts/suites/requires.json').write_text(json.dumps({'requires': requires}))
        decision = RS.change_selection(repo, context, manifest=manifest, requires=requires)
        row('scope-selected', decision['running'] == ['selected', 'unknown'])
        row('scope-carried', decision['carried']['carried']['source_commit'] == a and
            decision['carried']['carried']['source_gate_digest'] == initial['record_digest'])
        row('scope-unknown', 'unknown' in decision['running'])
        (frozen / 'scripts/suites/fixture.py').unlink()
        for name in ('selftest.py', 'run_scope.py', 'gate_changes.py', 'gate_fixtures.py'):
            shutil.copyfile(authority / 'scripts' / name, frozen / 'scripts' / name)
        (frozen / 'scripts/suites/manifest.json').write_text(json.dumps(manifest))
        (frozen / 'scripts/suites/requires.json').write_text(json.dumps({'requires': requires}))
        (frozen / 'scripts/suites/shared.py').write_text(
            'PASS = FAIL = 0\n'
            'def expect(name, condition):\n'
            '    global PASS, FAIL\n'
            '    PASS += bool(condition); FAIL += not condition\n'
            '    print("body ran: " + name)\n')
        for name in names:
            (frozen / 'scripts/suites' / (name + '.py')).write_text(
                'expect("' + name + ' target", True)\n')
        (frozen / 'scripts/suites/selected.py').write_text(
            'expect("selected target", True)\nexpect("unselected row", 1 / 0)\n')
        context['selected_rows'] = {'selected': ['selected target']}
        decision = RS.change_selection(repo, context, manifest=manifest, requires=requires)
        import os
        import sys
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith('VELDO_GATE_') and not key.startswith('VELDO_SUITE_')}
        command = [sys.executable, '-I', '-B', '-c',
            "import runpy; runpy.run_path('scripts/selftest.py', run_name='__main__', "
            "init_globals={'CHANGE_SELECTION': " + repr(decision) + "})"]
        child = subprocess.run(command, cwd=frozen, env=environment, capture_output=True, text=True)
        row('selftest-selected', child.returncode == 2 and 'body ran: selected target' in child.stdout
            and 'body ran: unselected row' not in child.stdout)
        carries = [json.loads(line.split(': ', 1)[1]) for line in child.stdout.splitlines()
                   if line.startswith('selftest change carry: ')]
        row('selftest-carried', carries == [dict(suite='carried', **decision['carried']['carried'])]
            and 'body ran: carried target' not in child.stdout)
        row('selftest-unknown', 'body ran: unknown target' in child.stdout)
        captured = []
        def nested(argv, **kwargs):
            result = subprocess.run(argv, cwd=kwargs['cwd'], env=environment, capture_output=True, text=True)
            captured.append(result)
            return result
        with patch.object(FU, 'heavy_run', side_effect=nested), patch.object(FU, 'launcher_fds', return_value=()), \
                contextlib.redirect_stdout(io.StringIO()):
            try:
                measured = FU._run_suite(frozen, 'fixture', change_context=context)
            except FU.CannotAnswer:
                measured = None
        output = captured[0].stdout if captured else ''
        row('first-use-selected', measured == (2, 0, []) and 'body ran: selected target' in output
            and 'body ran: unselected row' not in output)
        row('first-use-carried', 'body ran: carried target' not in output and
            a in output and initial['record_digest'] in output)
        row('first-use-unknown', 'body ran: unknown target' in output)


_v367_repairs()
