"""VELDO-0367 increment 1: real Git trees and the private authenticated Store."""


def _v367_baseline():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile

    sources = {'gate_changes.py': ROOT / "scripts" / "gate_changes.py",
               'gate_reuse.py': ROOT / "scripts" / "gate_reuse.py"}

    def load(path):
        spec = importlib.util.spec_from_file_location('v367_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def row(name, condition):
        expect('VELDO-0367 baseline/' + name, condition)

    def refused(call):
        try:
            call()
        except (ValueError, TypeError, KeyError):
            return True
        return False

    with tempfile.TemporaryDirectory(prefix='v367-') as directory:
        top = Path(directory)
        authority, repo = top / 'authority', top / 'repo'
        (authority / 'scripts').mkdir(parents=True)
        (authority / '.veldo').mkdir()
        for name, source in sources.items():
            shutil.copyfile(source, authority / 'scripts' / name)
        shutil.copyfile(ROOT / '.veldo/reuse_evidence.py', authority / '.veldo/reuse_evidence.py')
        C = load(authority / 'scripts/gate_changes.py')
        R = load(authority / 'scripts/gate_reuse.py')
        for relative in R.E.AUTHORITY_FILES:
            path = authority / relative
            if not path.exists() and relative not in R.E.OPTIONAL_AUTHORITY_FILES:
                path.write_text('# fixture authority input\n')
        repo.mkdir()

        def git(*args):
            return subprocess.run(['git', '-C', str(repo), *args], check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()

        git('init', '-q')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        git('config', 'core.filemode', 'true')

        commits = []

        def commit(*parents):
            git('add', '-A')
            args = ['commit-tree', git('write-tree'), '-m', 'fixture ' + str(len(commits))]
            for parent in parents:
                args.extend(('-p', parent))
            sha = git(*args)
            commits.append(sha)
            return sha

        (repo / 'keep').write_text('keep')
        (repo / 'delete').write_text('delete')
        (repo / 'rename').write_text('rename')
        (repo / 'mode').write_text('mode')
        (repo / 'link').symlink_to('keep')
        a = commit()
        (repo / 'added').write_text('added')
        (repo / 'delete').unlink()
        (repo / 'rename').rename(repo / 'renamed')
        (repo / 'mode').chmod(0o755)
        (repo / 'link').unlink()
        (repo / 'link').symlink_to('added')
        b = commit(a)
        c = commit(b)
        side = commit(a)
        joined = commit(c, side)
        unrelated = commit()

        catalog = {'unit': 'required:unit command', 'integration': 'required:integration command',
                   'mutation': 'required:mutation command', 'docs': 'na:no docs',
                   'format': 'waived:2099-01-01:owner decision'}
        expanded = {s: ['confined', 'unconfined'] for s in ('unit', 'integration', 'mutation')}
        manifest = {'suites': [{'name': 'alpha', 'file': 'alpha.py'}, {'name': 'beta', 'file': 'beta.py'}]}
        requires = {'requires': {'alpha': ['alpha'], 'beta': ['alpha', 'beta']}}
        drivers = {'check_teeth_mutations.py': [dict(name='same', suite='alpha', leg='confined')],
                   'check_review_mutations.py': [dict(name='same', suite='beta', leg='unconfined')]}
        inv = C.build_inventory(catalog, expanded, manifest, requires, drivers, [{'name': 'extra-check'}])
        expected = {C.identity('stage', stage) for stage in catalog}
        expected |= {C.identity('leg', stage, leg) for stage in expanded for leg in expanded[stage]}
        expected |= {C.identity('suite', stage, leg, suite) for stage in ('unit', 'integration')
                     for leg in expanded[stage] for suite in ('alpha', 'beta')}
        expected |= {C.identity('case', 'mutation', case['leg'], case['suite'], driver, case['name'])
                     for driver, cases in drivers.items() for case in cases}
        expected.add(C.identity('uncataloged', 'extra-check'))
        row('complete-inventory', {i['item_id'] for i in inv['items']} == expected and len(inv['items']) == len(expected))
        row('catalog-reasons', {i['state']: i['reason'] for i in inv['items'] if i['reason']} ==
            {'not-applicable': 'no docs', 'waived': '2099-01-01:owner decision'})
        row('duplicate-inventory', refused(lambda: C.inventory(inv['items'] + inv['items'][:1])))
        row('missing-closure', refused(lambda: C.build_inventory(catalog, expanded, manifest,
            {'requires': {'alpha': ['alpha']}}, drivers)))
        row('missing-leg', refused(lambda: C.build_inventory(catalog, {'unit': ['confined']}, manifest, requires, drivers)))
        row('missing-driver', refused(lambda: C.build_inventory(catalog, expanded, manifest, requires,
            {'check_teeth_mutations.py': []})))
        revised = copy.deepcopy(inv['items'])
        removed = revised.pop()
        revised[0]['definition_digest'] = C.digest('new definition')
        revised.append(dict(item_id='new identity', definition_digest=C.digest('new'), state='required', reason=None))
        reconciliation = C.reconcile(C.inventory(revised), inv)
        row('reconcile', len(reconciliation) == len(inv['items']) + 1 and
            {r['reason'] for r in reconciliation} == {'new', 'definition-changed', 'unchanged', 'removed'} and
            next(r for r in reconciliation if r['item_id'] == removed['item_id'])['state'] == 'removed')
        row('unchanged-inventory', all(r['reason'] == 'unchanged' for r in C.reconcile(inv, inv)))
        row('absent-inventory', all(r['reason'] == 'new' for r in C.reconcile(inv)))

        small = C.inventory([dict(item_id='unit/alpha', definition_digest=C.digest('alpha'), state='required', reason=None)])
        store = R.Store(top / 'store', repo)
        row('store-private', store.secret is not None and R.Store(repo / 'bad-store', repo).secret is None)

        def seal_again(value, **updates):
            fields = {k: v for k, v in value.items() if k not in ('schema', 'record_digest')}
            fields.update(updates)
            return C.sealed(value['schema'], **fields)

        def make_gate(sha, target=store):
            dep = C.sealed(C.DEPENDENCY, item_id='unit/alpha', observed_commit=sha,
                           paths=['keep', 'link'], directories=['.'], absent_paths=['missing'],
                           runtime_digest=C.digest('runtime'), complete=True, unknown_reason=None)
            result = C.sealed(C.RESULT, item_id='unit/alpha', source_commit=sha, status='passed', complete=True,
                              dependency_record_digest=dep['record_digest'])
            target.change_put(dep)
            target.change_put(result)
            receipt = C.sealed(C.RECEIPT, candidate_commit=sha, baseline_commit=None, baseline_record_digest=None,
                               changed_paths_digest=C.digest([]), inventory_digest=small['record_digest'],
                               items=[dict(item_id='unit/alpha', status='executed', dependency_record_digest=dep['record_digest'],
                                           result_digest=result['record_digest'], source_commit=sha, source_gate_digest=None)])
            gate = C.sealed(C.GATE, repository='fixture-repository', inventory=small, receipt=receipt, status='green', complete=True)
            return gate, dep, result

        ga, dep, result = make_gate(a)
        row('publish-green', store.publish_change_gate(ga))
        row('unchanged', C.baseline(repo, a, store, 'fixture-repository') ==
            dict(candidate_commit=a, baseline_commit=a, baseline_record_digest=ga['record_digest'], changed_paths=[]))
        row('tree-changes', C.changed_paths(repo, a, b) == ['added', 'delete', 'link', 'mode', 'rename', 'renamed'])
        row('identical-tree', C.changed_paths(repo, b, c) == [])
        # A red record is authenticated, indexed and complete-looking: eligibility,
        # rather than merely absence of a green publication, must reject it.
        gb, _, _ = make_gate(b)
        red = seal_again(gb, status='red')
        store.change_put(red)
        store.put(store.change_gate_key('fixture-repository', b),
                  dict(repository='fixture-repository', commit=b, record_digest=red['record_digest']))
        found = C.baseline(repo, c, store, 'fixture-repository')
        row('intervening-red', found['baseline_commit'] == a and found['baseline_record_digest'] == ga['record_digest'])
        gs, _, _ = make_gate(side)
        store.publish_change_gate(gs)
        row('first-parent', C.baseline(repo, joined, store, 'fixture-repository')['baseline_commit'] == a)
        row('divergent', C.baseline(repo, unrelated, store, 'fixture-repository')['baseline_commit'] is None)
        row('wrong-repository', C.baseline(repo, c, store, 'other')['baseline_commit'] is None)
        empty = R.Store(top / 'empty', repo)
        row('absent-records', C.baseline(repo, c, empty, 'fixture-repository') ==
            dict(candidate_commit=c, baseline_commit=None, baseline_record_digest=None, changed_paths=None))
        gc, _, _ = make_gate(c)
        row('nearest-green', store.publish_change_gate(gc) and
            C.baseline(repo, joined, store, 'fixture-repository')['baseline_commit'] == c)
        row('mutable-reference', refused(lambda: C.first_parents(repo, 'HEAD')))

        row('dependency-valid', C.validate_dependency(dep) == dep)
        row('unknown-explicit', C.validate_dependency(seal_again(dep, complete=False, unknown_reason='lost events'))['complete'] is False)
        row('unknown-not-empty', refused(lambda: C.validate_dependency(seal_again(dep, complete=False))))
        row('paths-relative', all(refused(lambda p=p: C.validate_dependency(seal_again(dep, paths=[p])))
                                  for p in ('/tmp/file', '../file', 'a/../b', 'a//b', './a', 'a\x00b')))
        row('dependency-digest', refused(lambda: C.validate_dependency(dict(dep, paths=['other']))))
        row('dependency-version', refused(lambda: C.validate_dependency(seal_again(dict(dep, schema='old')))))
        for name, entries in (
            ('receipt-missing', []), ('receipt-duplicate', ga['receipt']['items'] * 2),
            ('receipt-wrong-source', [dict(ga['receipt']['items'][0], source_commit=b)]),
            ('receipt-removed-current', [dict(ga['receipt']['items'][0], status='removed')]),
        ):
            row(name, refused(lambda: C.validate_receipt(seal_again(ga['receipt'], items=entries), small)))
        row('receipt-valid', C.validate_receipt(ga['receipt'], small) == ga['receipt'])
        row('receipt-baseline-pin', refused(lambda: C.validate_receipt(seal_again(ga['receipt'], baseline_commit=a), small)))
        row('receipt-inventory-pin', refused(lambda: C.validate_receipt(seal_again(ga['receipt'], inventory_digest=C.digest('wrong')), small)))

        # Isolate every missing/corrupt/revoked reference so each test has its own
        # authenticated green control and cannot pass due to another damaged input.
        for name in ('red', 'incomplete', 'missing-result', 'wrong-result', 'missing-dependency',
                     'wrong-dependency', 'revoked', 'corrupt', 'unsigned', 'wrong-index'):
            target = R.Store(top / ('store-' + name), repo)
            gate, dependency, outcome = make_gate(a, target)
            if name == 'red':
                gate = seal_again(gate, status='red')
            elif name == 'incomplete':
                gate = seal_again(gate, complete=False)
            elif name == 'wrong-result':
                target.invalidate(outcome['record_digest'])
            elif name == 'wrong-dependency':
                target.invalidate(dependency['record_digest'])
            target.change_put(gate)
            index_key = target.change_gate_key('fixture-repository', a)
            target.put(index_key, dict(repository='other' if name == 'wrong-index' else 'fixture-repository',
                                       commit=a, record_digest=gate['record_digest']))
            if name in ('missing-result', 'missing-dependency'):
                key = outcome['record_digest'] if name == 'missing-result' else dependency['record_digest']
                target._path(key).unlink()
            elif name == 'revoked':
                target.invalidate(gate['record_digest'])
            elif name in ('corrupt', 'unsigned'):
                path = target._path(gate['record_digest'])
                document = json.loads(path.read_text())
                if name == 'corrupt':
                    document['payload']['result']['status'] = 'red'
                else:
                    document['mac'] = '0' * 64
                path.write_bytes(R.canonical(document))
            row(name + '-miss', target.change_gate('fixture-repository', a) is None)
        # A valid MAC cannot turn a wrong source or identity into usable evidence.
        for name, field, replacement in (
            ('result-source', 'source_commit', b), ('result-item', 'item_id', 'other'),
            ('result-status', 'status', 'failed'), ('result-completeness', 'complete', False),
        ):
            target = R.Store(top / name, repo)
            gate, dependency, outcome = make_gate(a, target)
            outcome = seal_again(outcome, **{field: replacement})
            target.change_put(outcome)
            receipt = seal_again(gate['receipt'], items=[dict(gate['receipt']['items'][0], result_digest=outcome['record_digest'])])
            gate = seal_again(gate, receipt=receipt)
            row(name, not target.publish_change_gate(gate))
        row('red-not-published', not store.publish_change_gate(red))
        row('legacy-record', empty.put(empty.change_gate_key('fixture-repository', a), {'status': 'passed'})
            and empty.change_gate('fixture-repository', a) is None)


_v367_baseline()
