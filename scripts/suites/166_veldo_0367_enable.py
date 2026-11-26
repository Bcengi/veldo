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
