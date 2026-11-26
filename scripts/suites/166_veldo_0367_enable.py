"""VELDO-0367: cold selection and landing through authenticated baseline chains."""


def _v367_enable():
    import copy
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    from unittest.mock import patch

    sources = {'reuse_stamp.py': ROOT / "scripts" / "reuse_stamp.py",
               'gate_changes.py': ROOT / "scripts" / "gate_changes.py",
               'gate_execution.py': ROOT / "scripts" / "gate_execution.py",
               'gate_schedule.py': ROOT / "scripts" / "gate_schedule.py",
               'gate_legs.py': ROOT / "scripts" / "gate_legs.py",
               'reuse_evidence.py': ROOT / ".veldo" / "reuse_evidence.py",
               'control_verification.py': ROOT / ".veldo" / "control_verification.py"}

    def load(path):
        spec = importlib.util.spec_from_file_location('enable367_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def row(name, condition):
        expect('VELDO-0367 enable/' + name, condition)

    def refused(call):
        try:
            call()
        except (ValueError, TypeError, KeyError, OSError):
            return True
        return False

    with tempfile.TemporaryDirectory(prefix='enable367-') as directory:
        top = Path(directory)
        authority, repo = top / 'authority', top / 'repo'
        for folder in ('scripts', '.veldo'):
            (authority / folder).mkdir(parents=True)
            for path in (ROOT / folder).glob('*.py'):
                shutil.copyfile(sources.get(path.name, path), authority / folder / path.name)
        (authority / 'scripts/suites').mkdir()
        (authority / 'scripts/suites/wallclock_baseline.json').write_text('{"entries": []}')
        C, R, S = (load(authority / 'scripts' / name) for name in
                   ('gate_changes.py', 'gate_reuse.py', 'reuse_stamp.py'))
        E = R.E
        V = load(authority / '.veldo/control_verification.py')
        for relative in E.AUTHORITY_FILES:
            path = authority / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# fixture authority\n')
        repo.mkdir()

        def git(*args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

        def commit(message):
            git('add', '.')
            git('commit', '-qm', message)
            return git('rev-parse', 'HEAD')

        def seal(value, **fields):
            return C.sealed(value['schema'], **dict({k: v for k, v in value.items()
                if k not in ('schema', 'record_digest')}, **fields))

        git('init', '-q')
        git('config', 'user.name', 'Dmitry Grinberg')
        git('config', 'user.email', 'dmitry@example.invalid')
        (repo / 'input').write_text('old')
        first = commit('first')
        (repo / 'unrelated').write_text('one')
        second = commit('second')
        (repo / 'unrelated').write_text('two')
        third = commit('third')
        runtime = C.digest('fixture runtime')
        item_id = C.identity('suite', 'unit', 'confined', 'fixture')
        inventory = C.inventory([dict(item_id=item_id, definition_digest=C.digest('definition'),
                                     state='required', reason=None)])
        store = R.Store(top / 'store', repo)
        plan = C.select(repo, store, 'fixture', first, inventory, {item_id: runtime})
        row('no-seed-runs', plan['baseline_commit'] is None and
            [i['status'] for i in plan['items']] == ['run'])
        row('no-seed-cannot-skip', refused(lambda: C.assemble(plan, {})))
        dependency = C.sealed(C.DEPENDENCY, item_id=item_id, observed_commit=first,
            paths=['input'], directories=[], absent_paths=[], runtime_digest=runtime,
            complete=True, unknown_reason=None)
        result = C.sealed(C.RESULT, item_id=item_id, source_commit=first, status='passed',
            complete=True, dependency_record_digest=dependency['record_digest'])
        store.change_put(dependency)
        store.change_put(result)
        execution = dict(item_id=item_id, status='executed', dependency_record_digest=dependency['record_digest'],
            result_digest=result['record_digest'], source_commit=first, source_gate_digest=None)
        seed = C.publish_gate(repo, store, 'fixture', inventory, C.assemble(plan, {item_id: execution}))
        plan = C.select(repo, store, 'fixture', second, inventory, {item_id: runtime})
        carried = C.publish_gate(repo, store, 'fixture', inventory, C.assemble(plan, {}))
        plan = C.select(repo, store, 'fixture', third, inventory, {item_id: runtime})
        final = C.publish_gate(repo, store, 'fixture', inventory, C.assemble(plan, {}))
        document = dict(commit=third, force_fresh=False, reused={'unit': 1, 'mutation': 0},
                        **S.change_fields(repo, store, final, 'fixture'))
        row('original-source', final['receipt']['items'][0]['source_commit'] == first and
            final['receipt']['items'][0]['source_gate_digest'] == seed['record_digest'])
        row('landing-chain', E.change_landing(document, repo, store) == final)
        with patch.object(E, 'configuration', return_value=(None, {'store': str(top / 'store')})):
            row('landing-consumer', E.landing_problem(document, root=repo) is None)
            row('landing-needs-history', E.landing_problem(document) is not None)
            row('landing-counts', E.landing_problem(dict(document, reused={'unit': 0, 'mutation': 0}), root=repo) is not None)
            row('landing-count-types', E.landing_problem(dict(document, reused={'unit': True, 'mutation': 0}), root=repo) is not None)
            row('landing-force', E.landing_problem(dict(document, force_fresh=True), root=repo) is not None)
            row('landing-absent-history', E.landing_problem(document, root=top / 'absent') is not None)
            row('landing-missing-evidence', E.landing_problem(dict(commit=third,
                validation_mode='change-scoped', force_fresh=False, reused={'unit': 0, 'mutation': 0}),
                root=repo) is not None)

        # VELDO-0367 F1: every intermediate baseline of a carry is reopened, not one hop plus the origin.
        (repo / 'unrelated').write_text('three')
        fourth = commit('fourth')
        git('reset', '-q', '--hard', third)
        before_loss = C.select(repo, store, 'fixture', fourth, inventory, {item_id: runtime})
        middle = store._path(carried['record_digest'])
        aside = middle.with_name('aside-' + middle.name)
        middle.rename(aside)
        try:
            lost = C.select(repo, store, 'fixture', fourth, inventory, {item_id: runtime})
            row('chain-intermediate-select', [i['status'] for i in before_loss['items']] == ['carried'] and
                lost['baseline_record_digest'] == final['record_digest'] and
                [i['status'] for i in lost['items']] == ['run'])
            row('chain-intermediate-publish', refused(lambda: C.publish_gate(repo, store, 'fixture', inventory,
                C.assemble(before_loss, {}))))
        finally:
            aside.rename(middle)

        # VELDO-0367 F2: content-keyed runtime records stay readable after an authority edit;
        # any other record still needs the current authority.
        observed_runtime = {'environment': {'LANG': 'C.UTF-8'}, '/etc/fixture': ['file', 'a' * 64, 33188]}
        runtime_key = C.digest(['observed-runtime', C.publish_runtime(store, observed_runtime)])
        foreign_key = C.digest(['observed-runtime', C.digest('another record')])
        store.put(foreign_key, ['not', 'its', 'digest'])
        edited = authority / 'scripts/gate_weekly.py'
        saved_weekly = edited.read_text()
        edited.write_text(saved_weekly + '# authority edit\n')
        try:
            row('runtime-after-authority', store.get(runtime_key) == observed_runtime)
            row('foreign-after-authority', store.get(foreign_key) is None)
        finally:
            edited.write_text(saved_weekly)

        # Production catalog and graph adapters, exercised with a tiny authority.
        X = load(authority / 'scripts/gate_execution.py')
        L = X.module('gate_legs')
        Q = X.module('gate_schedule')
        prior_plans = json.loads((ROOT / 'proof/VELDO-0367/stage-plan-before.json').read_text())['plans']
        import re
        for relative, before in prior_plans.items():
            source = (ROOT / relative).read_text()
            declarations = re.findall(r'^CHECK_(\w+)="([^"\n]*)"$', source, re.M)
            order = re.search(r'^ORDER="(.*?)"', source, re.M | re.S)[1].replace('\\\n', ' ').split()
            assignments = ['CHECK_' + name + '=' + __import__('shlex').quote(value) for name, value in declarations]
            block = source.split('# VELDO-0367: the sole authority switch', 1)[1].split('# End VELDO-0367 entry.', 1)[0]
            block = '# VELDO-0367: the sole authority switch' + block + '\n'
            changes_path = authority / 'scripts/gate_changes.py'
            saved_changes = changes_path.read_text()
            changes_path.write_text(saved_changes.replace('SELECTION_ENABLED = True', 'SELECTION_ENABLED = False'))
            shell = ('VELDO_AUTHORITY=' + __import__('shlex').quote(str(authority)) + '\nVELDO_SINK=""\n' + block +
                     '\n'.join(assignments) + '\n' + '\n'.join(
                         'printf "%s\\t%s\\n" ' + name + ' "$CHECK_' + name + '"' for name in order))
            completed = subprocess.run(['bash', '-c', shell], capture_output=True, text=True)
            changes_path.write_text(saved_changes)
            actual = [line.split('\t', 1) for line in completed.stdout.splitlines()]
            row('off-stage-plan-' + ('engine' if relative.startswith('engine') else 'home'),
                completed.returncode == 0 and actual == before)

        command = Q.command_for(repo, 'mutation', None, 'authority mutation stage', top / 'legs', top / 'receipt',
                                {}, opened_parts=top, change_run='a' * 64)
        row('graph-mutation-entry', Path(command[3]).name == 'check_gate_mutations.py' and '--change-run' in command)
        command = Q.command_for(repo, 'unit', 'confined', 'python3 scripts/selftest.py', top / 'legs', top / 'receipt',
                                {}, opened_parts=top, change_run='a' * 64)
        row('graph-suite-entry', Path(command[3]).name == 'gate_legs.py' and '--change-run' in command and
                                command[-2:] == ['--leg', 'confined'])
        row('suite-public-plan', 'CHANGE_SELECTION' in L.selected_command('unit', 'python3 scripts/selftest.py',
            dict(running=['fixture'], carried={}, rows={})))
        row('integration-public-plan', 'CHANGE_CONTEXT' in L.selected_command('integration', 'python3 scripts/check_first_use.py',
            dict(running=['fixture'], carried={}, rows={})))
        row('suite-command-binding', refused(lambda: L.selected_command('unit', 'true', dict(running=[], carried={}, rows={}))))

        # Model both registries and all suite legs, including a non-applicable slot.
        fixture_manifest = {'shared': 'shared.py', 'suites': [dict(name='fixture', file='fixture.py')]}
        fixture_requires = {'requires': {'fixture': ['fixture']}}
        (repo / 'scripts/suites').mkdir(parents=True)
        (repo / 'scripts/suites/manifest.json').write_text(json.dumps(fixture_manifest))
        (repo / 'scripts/suites/requires.json').write_text(json.dumps(fixture_requires))
        definitions = [dict(name='one', suite='fixture.py', driver=driver, identity=driver + ':one')
                       for driver in ('check_teeth_mutations.py', 'check_review_mutations.py')]
        declarations = dict(unit='required:python3 scripts/selftest.py',
            integration='required:python3 scripts/check_first_use.py', mutation='required:authority mutation stage',
            lint='required:true', format='na:fixture', docs='waived:2999-01-01:fixture')
        changes_path = authority / 'scripts/gate_changes.py'
        saved_changes = changes_path.read_text()
        changes_path.write_text(saved_changes.replace('SELECTION_ENABLED = False', 'SELECTION_ENABLED = True'))
        with patch.object(X, 'source_state', return_value=(repo / '.git', {}, third)), \
                patch.object(L, 'mutation_leg', return_value=None), \
                patch.object(L, 'DECLARATION', top / 'no-unconfined'):
            context = X.prepare(repo, store, cases=definitions, declarations=declarations, runtime=runtime)
        changes_path.write_text(saved_changes)
        required_ids = {i['item_id'] for i in context['inventory']['items'] if i['state'] == 'required'}
        row('common-no-seed-all', {i['item_id'] for i in context['plan']['items'] if i['status'] == 'run'} == required_ids
            and len(required_ids) > len(declarations) and context['plan']['baseline_commit'] is None)
        row('common-no-seed-not-empty', refused(lambda: C.assemble(context['plan'], {})))
        row('both-mutation-drivers', {__import__('json').loads(key)[4] for key in required_ids
            if __import__('json').loads(key)[0] == 'case'} == {case['driver'] for case in definitions})
        key = X.save_context(store, context)
        row('common-authenticated-plan', X.read_context(store, key)['nonce'] == context['nonce'])
        row('common-unsigned-plan', refused(lambda: X.read_context(store, 'f' * 64)))
        tampered = dict(X.read_context(store, key), nonce='tampered')
        with patch.object(store, 'get', return_value=tampered):
            row('common-plan-seal', refused(lambda: X.read_context(store, key)))
        full = X.full_plan(dict(context['plan'], baseline_commit=first, baseline_record_digest=seed['record_digest'],
                               items=[dict(i, status='carried', evidence=execution) if i['status'] == 'run' else i
                                      for i in context['plan']['items']]))
        row('full-clears-carry', full['baseline_record_digest'] is None and full['changed_paths'] is None and
            all(i['status'] == 'run' and i['evidence'] is None for i in full['items'] if i['item_id'] in required_ids))
        suite_key = C.identity('suite', 'unit', 'confined', 'fixture')
        parent_keys = [C.identity('stage', 'unit'), C.identity('leg', 'unit', 'confined')]
        promotion = dict(context['plan'], items=[dict(i, status='carried', evidence=execution)
            if i['item_id'] in parent_keys else i for i in context['plan']['items']])
        X.reconcile_children(promotion)
        row('selected-child-promotes-parent', all(i['status'] == 'run' for i in promotion['items'] if i['item_id'] in parent_keys))
        # A stage success cannot manufacture a missing suite receipt.
        with patch.object(X, 'store_for', return_value=store), patch.object(X, 'source_state',
                return_value=(repo / '.git', {}, third)), patch.object(X.module('gate_changes'), 'SELECTION_ENABLED', True), \
                patch.object(X.module('check_gate_mutations'), 'file_identity', return_value=context['files_digest']), \
                patch.object(L, 'TakeOpened') as take, patch.object(L, 'run_stage', return_value=0):
            take.return_value.finish.return_value = 0
            take.return_value.observation_error = None
            take.return_value.observations = []
            # run_scope loads the fixture's enabled authority, independently of X.
            changes_path.write_text(saved_changes.replace('SELECTION_ENABLED = False', 'SELECTION_ENABLED = True'))
            row('common-missing-suite', refused(lambda: X.node(key, 'unit', repo, top)))
            changes_path.write_text(saved_changes)
        shutil.rmtree(repo / 'scripts')

        # Shared migration reads, directory discovery, and absent file creation
        # select both the suite and its cases, while unrelated edits carry source.
        for label, changed, expected in (('migration', ['db/migrations/002.sql'], True),
                ('listed-directory', ['plugins/new.py'], True), ('missing-created', ['optional/config'], True),
                ('unrelated-input', ['notes'], False)):
            dep = seal(dependency, paths=['db/migrations'], directories=['plugins'], absent_paths=['optional/config'])
            row('common-' + label, C.intersects(dep, changed) is expected)
        external = top / 'runtime-file'
        external.write_text('one')
        runtime_value = {'environment': {}, str(external): ['file', __import__('hashlib').sha256(b'one').hexdigest(), external.stat().st_mode]}
        runtime_key = C.publish_runtime(store, runtime_value)
        row('runtime-consumer-unchanged', C.runtime_current(store, runtime_key, {}, authority))
        external.write_text('two')
        row('runtime-consumer-changed', not C.runtime_current(store, runtime_key, {}, authority))

        # An authenticated intermediate gate can be malformed without changing
        # the final source digest. Reject the chain, not merely a bad MAC.
        empty_inventory = C.inventory([dict(item_id='other', definition_digest=C.digest('other'),
            state='not-applicable', reason='fixture')])
        absent = dict(item_id='other', status='not-applicable', dependency_record_digest=None,
                      result_digest=None, source_commit=None, source_gate_digest=None)
        empty_receipt = seal(seed['receipt'], inventory_digest=empty_inventory['record_digest'], items=[absent])
        missing = seal(seed, inventory=empty_inventory, receipt=empty_receipt)
        store.change_put(missing)
        broken_middle = seal(carried, receipt=seal(carried['receipt'], baseline_record_digest=missing['record_digest']))
        store.change_put(broken_middle)
        broken = seal(final, receipt=seal(final['receipt'], baseline_record_digest=broken_middle['record_digest']))
        store.change_put(broken)
        payload = E.authenticated(document['change_evidence'], store.secret)
        broken_document = dict(document, change_evidence=E.sign(dict(payload,
            gate_digest=broken['record_digest']), store.secret))
        row('chain-missing-item', refused(lambda: E.change_landing(broken_document, repo, store)))
        row('reducer-chain', refused(lambda: S.change_fields(repo, store, broken, 'fixture')))

        git('checkout', '-qb', 'side', first)
        (repo / 'side').write_text('side')
        side = commit('side')
        side_receipt = seal(seed['receipt'], candidate_commit=side, items=[dict(execution, source_commit=side)])
        # A well-shaped historical gate on a different branch cannot anchor carry.
        side_gate = seal(seed, receipt=side_receipt)
        store.change_put(side_gate)
        wrong_branch = seal(carried, receipt=seal(carried['receipt'], baseline_commit=side,
            baseline_record_digest=side_gate['record_digest']))
        store.change_put(wrong_branch)
        broken = seal(final, receipt=seal(final['receipt'], baseline_record_digest=wrong_branch['record_digest']))
        store.change_put(broken)
        broken_document = dict(document, change_evidence=E.sign(dict(payload,
            gate_digest=broken['record_digest']), store.secret))
        row('chain-first-parent', refused(lambda: E.change_landing(broken_document, repo, store)))

        # Invoke the real landing judge with a complete captured observation.
        output = '== unit\n   unit: pass\nGATE: GREEN (%s)\n' % third
        observation = dict(schema=V._proof().OBSERVATION_SCHEMA, commit=third,
            stdout=output, stdout_digest=V.digest(output.encode()), exit=0,
            terminal='GATE: GREEN (%s)' % third,
            catalog={'required': ['unit'], 'results': {'unit': 'pass'}},
            candidate={'root': str(repo), 'commit': third, 'tree': 'a' * 40, 'binds_refs': False, 'state': 'state'},
            post_run={'equal': True, 'state': 'state'}, outputs={
                'last_verify': dict(document, status='green'),
                'gate_event': dict(document, type='gate.passed')})
        original_sibling = V._sibling
        with patch.object(E, 'configuration', return_value=(None, {'store': str(top / 'store')})), \
                patch.object(V, '_sibling', side_effect=lambda alias, name:
                             E if name == 'reuse_evidence.py' else original_sibling(alias, name)):
            row('judge-valid', V.judge(observation) == [])
            bad = copy.deepcopy(observation)
            bad['outputs']['gate_event']['change_evidence'] = broken_document['change_evidence']
            problems = V.judge(bad)
            row('judge-chain', 'missing_evidence:gate/authenticated_reuse_required' in problems)
            row('judge-same-evidence', 'binding_mismatch:gate/change_evidence' in problems)


_v367_enable()
