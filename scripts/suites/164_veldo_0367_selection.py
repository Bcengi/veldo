"""VELDO-0367 AC3/AC4: dormant selection, provenance and scoped mutation evidence."""


def _v367_selection():
    import copy
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    from unittest.mock import patch

    sources = {'gate_changes.py': ROOT / "scripts" / "gate_changes.py",
               'case_reuse.py': ROOT / "scripts" / "case_reuse.py",
               'mutation_reuse.py': ROOT / "scripts" / "mutation_reuse.py",
               'check_gate_mutations.py': ROOT / "scripts" / "check_gate_mutations.py",
               'reuse_stamp.py': ROOT / "scripts" / "reuse_stamp.py",
               'mutation_observer.py': ROOT / "scripts" / "mutation_observer.py",
               'reuse_worker.py': ROOT / "scripts" / "reuse_worker.py"}
    evidence_source = ROOT / ".veldo" / "reuse_evidence.py"
    teeth_source = ROOT / "scripts" / "check_teeth_mutations.py"

    def load(path):
        spec = importlib.util.spec_from_file_location('selection367_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def row(name, condition):
        expect('VELDO-0367 selection/' + name, condition)

    def refused(call):
        try:
            call()
        except Exception as error:
            if isinstance(error, (ValueError, TypeError, KeyError, RuntimeError)) or hasattr(error, 'code'):
                return True
            raise
        return False

    def reseal(value, **fields):
        return C.sealed(value['schema'], **dict({k: v for k, v in value.items()
                         if k not in ('schema', 'record_digest')}, **fields))

    with tempfile.TemporaryDirectory(prefix='selection367-') as temporary:
        top = Path(temporary)
        authority, repo = top / 'authority', top / 'repo'
        (authority / 'scripts').mkdir(parents=True)
        (authority / '.veldo').mkdir()
        for name in ('gate_reuse.py', 'case_inputs.py', 'gate_fixtures.py', *sources):
            shutil.copyfile(sources.get(name, ROOT / 'scripts' / name), authority / 'scripts' / name)
        switch = authority / 'scripts/gate_changes.py'
        switch.write_text(switch.read_text().replace('SELECTION_ENABLED = True', 'SELECTION_ENABLED = False'))
        shutil.copyfile(evidence_source, authority / '.veldo/reuse_evidence.py')
        C, R, M, G, S, K = (load(authority / 'scripts' / name) for name in
                            ('gate_changes.py', 'gate_reuse.py', 'mutation_reuse.py',
                             'check_gate_mutations.py', 'reuse_stamp.py', 'case_reuse.py'))
        E = R.E
        G.ROOT = authority
        for relative in E.AUTHORITY_FILES:
            path = authority / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# fixture authority\n')
        repo.mkdir()
        def git(*args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()
        git('init', '-q')
        git('config', 'user.name', 'Dmitry Grinberg')
        git('config', 'user.email', 'dmitry@example.invalid')
        (repo / 'scripts').mkdir()
        (repo / 'scripts/gate_changes.py').write_text('# before\n')
        (repo / 'scripts/verify.sh').write_text('# before\n')
        (repo / 'input').write_text('before')
        git('add', '.')
        git('commit', '-qm', 'seed')
        a = git('rev-parse', 'HEAD')
        (repo / 'unrelated').write_text('new')
        git('add', '.')
        git('commit', '-qm', 'unrelated')
        b = git('rev-parse', 'HEAD')
        (repo / 'input').write_text('after')
        git('add', '.')
        git('commit', '-qm', 'dependency')
        c = git('rev-parse', 'HEAD')
        git('checkout', '-qb', 'authority-edit', b)
        (repo / 'scripts/gate_changes.py').write_text('# after\n')
        git('add', '.')
        git('commit', '-qm', 'authority dependency')
        machinery = git('rev-parse', 'HEAD')
        git('checkout', '-qb', 'verify-edit', b)
        (repo / 'scripts/verify.sh').write_text('# after\n')
        git('add', '.')
        git('commit', '-qm', 'unrelated gate edit')
        gate_edit = git('rev-parse', 'HEAD')
        runtime = C.digest('runtime')
        items = C.inventory([dict(item_id=n, definition_digest=C.digest(n), state='required', reason=None)
                             for n in ('dependent', 'other', 'unknown')])
        store = R.Store(top / 'store', repo)
        entries = []
        deps = {}
        for name in ('dependent', 'other', 'unknown'):
            dep = C.sealed(C.DEPENDENCY, item_id=name, observed_commit=a,
                paths=['input'] if name == 'dependent' else ['scripts/gate_changes.py'], directories=[], absent_paths=[],
                runtime_digest=runtime, complete=name != 'unknown',
                unknown_reason='missing trace' if name == 'unknown' else None)
            result = C.sealed(C.RESULT, item_id=name, source_commit=a, status='passed', complete=True,
                              dependency_record_digest=dep['record_digest'])
            store.change_put(dep)
            store.change_put(result)
            deps[name] = dep
            entries.append(dict(item_id=name, status='executed', dependency_record_digest=dep['record_digest'],
                                result_digest=result['record_digest'], source_commit=a, source_gate_digest=None))
        receipt = C.sealed(C.RECEIPT, candidate_commit=a, baseline_commit=None, baseline_record_digest=None,
                           changed_paths_digest=C.digest(None), inventory_digest=items['record_digest'], items=entries)
        seed = C.sealed(C.GATE, repository='fixture', inventory=items, receipt=receipt, status='green', complete=True)
        row('seed', store.publish_change_gate(seed))
        runtimes = dict.fromkeys(('dependent', 'other', 'unknown'), runtime)
        def plan(commit=b):
            return C.select(repo, store, 'fixture', commit, items, runtimes)
        def states(value):
            return {i['item_id']: i['status'] for i in value['items']}
        row('unrelated', states(plan()) == dict(dependent='carried', other='carried', unknown='run'))
        row('dependency-edit', states(plan(c)) == dict(dependent='run', other='carried', unknown='run'))
        row('machinery-dependent', states(plan(machinery)) == dict(dependent='carried', other='run', unknown='run'))
        row('no-blanket-invalidation', states(plan(gate_edit)) == dict(dependent='carried', other='carried', unknown='run'))
        changed_runtime = C.select(repo, store, 'fixture', b, items, dict(runtimes, dependent=C.digest('new runtime')))
        row('runtime-local', states(changed_runtime) == dict(dependent='run', other='carried', unknown='run'))
        row('unknown-runs', states(plan())['unknown'] == 'run')
        row('inactive', C.SELECTION_ENABLED is False and refused(lambda: C.dispatch(plan(), lambda _: None)))
        row('production-inactive', refused(lambda: G.run_stage(repo, repo / '.git', change_context=dict(
            store=store, repository='fixture', candidate_commit=b, inventory=items, runtimes=runtimes))))
        row('directory-and-absent', C.intersects(reseal(deps['other'], directories=['new'], absent_paths=['missing']),
                                               ['new/child']) and
            C.intersects(reseal(deps['other'], absent_paths=['missing']), ['missing']))
        carried = plan()['items'][0]['evidence']
        row('provenance', carried is not None and carried['source_commit'] == a and carried['source_gate_digest'] == seed['record_digest'])
        new_unknown = reseal(deps['unknown'], observed_commit=b)
        store.change_put(new_unknown)
        result = C.sealed(C.RESULT, item_id='unknown', source_commit=b, status='passed', complete=True,
                          dependency_record_digest=new_unknown['record_digest'])
        store.change_put(result)
        execution = dict(entries[2], source_commit=b, dependency_record_digest=new_unknown['record_digest'],
                         result_digest=result['record_digest'])
        expected_plan = dict(candidate_commit=b, baseline_commit=a, baseline_record_digest=seed['record_digest'],
            changed_paths=['unrelated'], inventory=items, items=[
                dict(item_id=e['item_id'], status='carried', reason='fixture',
                     evidence=dict(e, status='carried', source_gate_digest=seed['record_digest'])) for e in entries[:2]] +
                [dict(item_id='unknown', status='run', reason='unknown dependency', evidence=None)])
        dispatched = []
        def execute_item(name):
            dispatched.append(name)
            return execution
        with patch.object(C, 'SELECTION_ENABLED', True):
            try:
                C.dispatch(expected_plan, execute_item)
                dispatch_ok = True
            except ValueError:
                dispatch_ok = False
        row('dispatch-carried', dispatch_ok and dispatched == ['unknown'])
        assembled = C.assemble(expected_plan, {'unknown': execution})
        gate = C.sealed(C.GATE, repository='fixture', inventory=items, receipt=assembled, status='green', complete=True)
        row('carry-green', C.green_record(repo, store, gate, 'fixture') == gate)
        forged = copy.deepcopy(gate['receipt']['items'])
        forged[0]['source_commit'] = b
        wrong = reseal(gate, receipt=reseal(assembled, items=forged))
        row('forged-source', refused(lambda: C.green_record(repo, store, wrong, 'fixture')))
        dep_c = reseal(new_unknown, observed_commit=c)
        store.change_put(dep_c)
        result_c = reseal(result, source_commit=c, dependency_record_digest=dep_c['record_digest'])
        store.change_put(result_c)
        stale_items = [*assembled['items'][:2], dict(execution, source_commit=c,
                       dependency_record_digest=dep_c['record_digest'], result_digest=result_c['record_digest'])]
        stale = reseal(gate, receipt=reseal(assembled, candidate_commit=c, items=stale_items,
                      changed_paths_digest=C.digest(C.changed_paths(repo, a, c))))
        row('stale-carry', refused(lambda: C.green_record(repo, store, stale, 'fixture')))
        duplicate = reseal(gate, receipt=reseal(assembled, items=assembled['items'] + assembled['items'][:1]))
        row('duplicate', refused(lambda: C.green_record(repo, store, duplicate, 'fixture')))
        published = C.publish_gate(repo, store, 'fixture', items, assembled)
        row('publish-carry', C.eligible_baseline(repo, store, 'fixture', b) == published)
        again = C.assemble(dict(expected_plan, baseline_commit=b,
            baseline_record_digest=published['record_digest'], changed_paths=[]), {'unknown': execution})
        refreshed = C.publish_gate(repo, store, 'fixture', items, again)
        row('same-commit-refresh', C.eligible_baseline(repo, store, 'fixture', b) == refreshed and
            again['items'][0]['source_commit'] == a and again['items'][0]['source_gate_digest'] == seed['record_digest'])
        document = dict(commit=b, **S.change_fields(repo, store, gate, 'fixture'))
        row('landing', E.change_landing(document, repo, store) == gate)
        payload = E.authenticated(document['change_evidence'], store.secret)
        forged_document = dict(document, change_evidence=E.sign(dict(payload, commit=c), store.secret))
        row('landing-candidate', refused(lambda: E.change_landing(forged_document, repo, store)))
        store.change_put(wrong)
        row('stamp-forged', refused(lambda: S.change_fields(repo, store, wrong, 'fixture')))
        with patch.object(E, 'authority_identity', return_value='changed authority'):
            row('authority-dependency', store.get(seed['record_digest']) == seed)
        original = store._path(entries[1]['result_digest']).read_bytes()
        forged_mac = json.loads(original)
        forged_mac['payload']['result']['source_commit'] = c
        store._path(entries[1]['result_digest']).write_bytes(E.canonical(forged_mac))
        row('forged-mac', states(plan())['other'] == 'run')
        store._path(entries[1]['result_digest']).unlink()
        row('isolated-missing', states(plan()) == dict(dependent='carried', other='run', unknown='run'))
        store._path(entries[1]['result_digest']).write_bytes(original)
        store.invalidate(entries[1]['result_digest'])
        row('revocation', states(plan())['other'] == 'run')
        session = K.ChangeSession(repo, store, 'fixture', b, items, runtimes)
        row('session', states(session.plan) == dict(dependent='carried', other='run', unknown='run'))

        case = dict(identity='driver:case', name='case', driver='driver', suite='fixture.py',
                    module='one.py', rows=['target', 'second'], old='True', new='False')
        other = dict(case, identity='driver:other', name='other', module='two.py')
        configuration = dict(leg='confined', runtime_digest=runtime, fixture_configuration={})
        suite = M.suite_identity(case, configuration)
        row('suite-group', suite == M.suite_identity(other, configuration) and
            suite != M.suite_identity(case, dict(configuration, leg='unconfined')) and
            suite != M.suite_identity(case, dict(configuration, fixture_configuration={'fixture': 'other'})) and
            G.control_group(case, configuration) == G.control_group(other, configuration))
        def observation(rows):
            return dict(count=len(rows), observations=rows, row_names=[n for n, _ in rows],
                        failed_rows=[n for n, ok in rows if ok is False])
        honest = observation([['fixture target', True], ['fixture second', True]])
        control_dep = reseal(deps['dependent'], item_id='controls')
        calls = []
        control_commit = [a]
        def execute_controls(cases):
            calls.append([x['identity'] for x in cases])
            return honest, honest, reseal(control_dep, observed_commit=control_commit[0])
        controls = M.SuiteControls(store, [], a)
        pair = controls.get(suite, [case, other], execute_controls)
        controls.get(suite, [case, other], execute_controls)
        row('controls-once', len(calls) == 1)
        control_commit[0] = b
        carried_pair = M.SuiteControls(store, ['unrelated'], b).get(suite, [case, other], execute_controls,
                                                                pair['record_digest'])
        row('controls-carry', len(calls) == 1 and carried_pair == pair)
        control_commit[0] = a
        M.SuiteControls(store, ['input'], a).get(suite, [case, other], execute_controls, pair['record_digest'])
        row('controls-dependency', len(calls) == 2)
        forged_control = reseal(pair, source_commit=b)
        store.change_put(forged_control)
        M.SuiteControls(store, [], a).get(suite, [case, other], execute_controls, forged_control['record_digest'])
        row('control-forgery', len(calls) == 3)
        invalid_pair = dict(pair, baseline=observation([['fixture target', False], ['fixture second', True]]))
        ran = []
        row('failed-control', refused(lambda: M.selected_mutation(case, invalid_pair, lambda _: ran.append(1) or dict(mutant=honest),
            lambda *_: None, store=store)) and not ran)
        def record(broken):
            return dict(schema=G.SCHEMA, case=case, fixture_version=G.FIXTURE_VERSION, input_digest=C.digest(case),
                        replacement_count=1, old_digest=C.digest('old'), new_digest=C.digest('new'),
                        baseline=honest, noop=honest, mutant=observation(broken))
        (authority / 'scripts/suites').mkdir(exist_ok=True)
        census = json.loads((ROOT / 'scripts/suites/wallclock_baseline.json').read_text())
        census['entries'].append(dict(file='scripts/suites/fixture.py', count=1))
        (authority / 'scripts/suites/wallclock_baseline.json').write_text(json.dumps(census))
        def validate(result, definition):
            return G.validate_result(result, definition, store=store)
        prior = record([['fixture target', False], ['fixture second', True]])
        validate(prior, case)
        kill = C.sealed(M.KILL_RECORD, source_commit=a, dependency=deps['dependent'], result=prior)
        store.change_put(kill)
        def run(selected, survive=False):
            ran.append(selected)
            return record([['fixture target', bool(survive)]] if selected else
                          [['fixture target', False], ['fixture second', True]])
        ran.clear()
        result = M.selected_mutation(case, pair, run, validate, store=store, prior=kill['record_digest'])
        row('prior-first', ran == [['fixture target']] and result['execution_scope'] == 'rows')
        ran.clear()
        try:
            fallback = M.selected_mutation(case, pair, lambda selected: run(selected, survive=bool(selected)),
                                           validate, store=store, prior=kill['record_digest'])
        except G.Refused:
            fallback = None
        row('fallback', fallback is not None and ran == [['fixture target'], None] and fallback['execution_scope'] == 'suite'
            and len(fallback['attempts']) == 2)
        ran.clear()
        M.selected_mutation(case, pair, run, validate, store=store, prior=C.digest('missing'))
        row('missing-prior', ran == [None])
        unavailable = M.selected_mutation(case, pair, lambda selected: None if selected else run(None),
            validate, store=store, prior=kill['record_digest'])
        row('unusable-prior-fallback', unavailable['execution_scope'] == 'suite' and
            unavailable['attempts'][0].get('unavailable') is True)
        item_id = C.identity('case', 'mutation', 'confined', case['suite'], case['driver'], case['name'])
        mutation_dep = reseal(deps['dependent'], item_id=item_id)
        envelope = C.sealed(M.KILL_RECORD, source_commit=a, dependency=mutation_dep, result=result)
        store.change_put(mutation_dep)
        store.change_put(envelope)
        outcome = C.sealed(C.RESULT_V2, item_id=item_id, source_commit=a, status='passed', complete=True,
            dependency_record_digest=mutation_dep['record_digest'], execution_record_digest=envelope['record_digest'])
        store.change_put(outcome)
        entry = dict(item_id=item_id, status='executed', dependency_record_digest=mutation_dep['record_digest'],
                     result_digest=outcome['record_digest'], source_commit=a, source_gate_digest=None)
        row('landing-row-kill', C.item_evidence(store, entry) == mutation_dep)
        damaged = copy.deepcopy(result)
        damaged['observed_rows'] = []
        broken_envelope = reseal(envelope, result=damaged)
        store.change_put(broken_envelope)
        broken_outcome = reseal(outcome, execution_record_digest=broken_envelope['record_digest'])
        store.change_put(broken_outcome)
        row('landing-missing-rows', refused(lambda: C.item_evidence(store,
            dict(entry, result_digest=broken_outcome['record_digest']))))

        survivor = copy.deepcopy(result)
        survivor['mutant'] = observation([['fixture target', True]])
        survivor['attempts'][-1]['observation'] = survivor['mutant']
        try:
            validate(survivor, case)
            rejection = None
        except G.Refused as error:
            rejection = error.code
        row('target-rejection', rejection == 'mutation_survived')
        hung = copy.deepcopy(result)
        hung['mutant']['hung_rows'] = ['fixture target']
        try:
            validate(hung, case)
            rejection = None
        except G.Refused as error:
            rejection = error.code
        row('hung-not-kill', rejection == 'hung_not_killed')
        extra = copy.deepcopy(result)
        extra['mutant'] = observation([['fixture target', False], ['fixture second', True]])
        extra['observed_rows'] = extra['mutant']['row_names']
        extra['attempts'][-1]['observation'] = extra['mutant']
        row('incomplete-row', refused(lambda: validate(extra, case)))
        rows_leg = dict(suites=['fixture'], entries=['fixture:strace'])
        row('confinement', G.in_leg(rows_leg, case, selected_rows=['fixture target'],
                                   row_legs={'fixture target': 'confined'}) is False and
            G.in_leg(rows_leg, case, selected_rows=['fixture target'],
                     row_legs={'fixture target': 'unconfined'}) is True and
            refused(lambda: G.in_leg(rows_leg, case, selected_rows=['fixture target'], row_legs={})) and
            refused(lambda: G.in_leg(None, case, suite_leg='unconfined')))
        side = []
        source = 'expect("fixture target", side.append("target") or True)\nexpect("fixture second", side.append("second") or True)\n'
        exec(C.row_source(source, ['fixture target']), {'expect': lambda *_: None, 'side': side})
        row('row-bodies', side == ['target'])
        row('unusable-rows', refused(lambda: C.row_source(source, ['fixture gone'])))
        # The direct teeth driver must execute the same selected bodies, including setup.
        driver = load(teeth_source)
        fake = top / 'driver'
        (fake / 'scripts/suites').mkdir(parents=True)
        shutil.copyfile(authority / 'scripts/gate_changes.py', fake / 'scripts/gate_changes.py')
        (fake / 'scripts/suites/shared.py').write_text('def expect(name, condition):\n    pass\n')
        (fake / 'scripts/suites/fixture.py').write_text(
            'expect("fixture target", True)\nexpect("fixture second", 1 / 0)\n')
        driver.ROOT = fake
        with patch.object(driver, '_coordinator', return_value=G):
            try:
                result = driver.worker(case, selected_rows=['fixture target'])
            except ZeroDivisionError:
                result = None
        row('teeth-rows', result is not None and result['observations'] == [['fixture target', True]] and
            set(result['targets']) == {'target'})
        child = ('import importlib.util,json; from pathlib import Path; '
                 's=importlib.util.spec_from_file_location("selected_observer",%r); '
                 'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.ROOT=Path(%r); '
                 'print(json.dumps(m.worker(%r,isolate_runtime=False,selected_rows=["fixture target"])))'
                 % (str(authority / 'scripts/mutation_observer.py'), str(fake), case))
        import sys
        observed = subprocess.run([sys.executable, '-c', child], capture_output=True, text=True)
        captured = json.loads(observed.stdout) if observed.returncode == 0 else {}
        row('observer-rows', captured.get('observations') == [['fixture target', True]] and
            set(captured.get('targets', {})) == {'target'})
        import contextlib
        import io
        import os
        from types import SimpleNamespace
        W = load(authority / 'scripts/reuse_worker.py')
        forwarded = []
        def observing(*args, **kwargs):
            forwarded.append(kwargs)
            return honest
        owner = SimpleNamespace(materialize=lambda *args, **kwargs: dict(mutant=None, replacement_count=1,
            old_digest='old', new_digest='new'), worker=observing)
        with patch.dict(os.environ, TMPDIR=str(top)), contextlib.redirect_stdout(io.StringIO()):
            W.observe(G, owner, dict(case=case, mode='mutant', selected_rows=['fixture target']), fake)
        row('worker-rows', forwarded == [dict(isolate_runtime=True, selected_rows=['fixture target'])])



_v367_selection()
