"""VELDO-0367 AC5: authority admission, durable revocation and real process custody."""


def _v367_weekly():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    from unittest.mock import patch

    sources = {'gate_weekly.py': ROOT / "scripts" / "gate_weekly.py",
               'gate_host.py': ROOT / "scripts" / "gate_host.py",
               'gate_reuse.py': ROOT / "scripts" / "gate_reuse.py",
               'gate_changes.py': ROOT / "scripts" / "gate_changes.py"}

    def load(path):
        spec = importlib.util.spec_from_file_location('weekly367_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def row(name, value):
        expect('VELDO-0367 weekly/' + name, value)

    def refused(call):
        try:
            call()
        except (ValueError, KeyError, TypeError, OSError):
            return True
        return False

    with tempfile.TemporaryDirectory(prefix='weekly367-') as directory:
        top = Path(directory)
        authority, repo = top / 'authority', top / 'repo'
        (authority / 'scripts').mkdir(parents=True)
        (authority / '.veldo').mkdir()
        repo.mkdir()
        for name, source in sources.items():
            shutil.copyfile(source, authority / 'scripts' / name)
        shutil.copyfile(ROOT / '.veldo/reuse_evidence.py', authority / '.veldo/reuse_evidence.py')
        W, H, R, C = (load(authority / 'scripts' / name) for name in
                       ('gate_weekly.py', 'gate_host.py', 'gate_reuse.py', 'gate_changes.py'))
        for relative in R.E.AUTHORITY_FILES:
            path = authority / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# fixture authority\n')
        store = R.Store(top / 'store', repo)
        weekly = W.Weekly(store, 'repository')
        commit = 'a' * 40
        with patch.object(C, 'SELECTION_ENABLED', False), patch.object(W, 'sibling', return_value=C):
            row('inactive', W.main([]) == 75)
        from types import SimpleNamespace
        commands = []
        adapter = SimpleNamespace(main=lambda argv: commands.append(argv) or 0)
        with patch.object(C, 'SELECTION_ENABLED', True), patch.object(W, 'sibling',
                side_effect=lambda name: C if name == 'gate_changes' else adapter):
            row('common-entry', W.main(['--candidate', '/fixture/candidate', '--sink', '/fixture/sink']) == 0 and
                commands == [['--weekly', '--root', '/fixture/candidate', '--sink', '/fixture/sink']])
        request = weekly.request(commit, 'pc2', 100)
        row('two-callers', weekly.request('b' * 40, 'other-host', 101) == request)
        program = '''import importlib.util,json,sys
from pathlib import Path
def load(name):
 s=importlib.util.spec_from_file_location(name,Path(sys.argv[1])/('scripts/'+name+'.py'))
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('gate_reuse');w=load('gate_weekly')
print(json.dumps(w.Weekly(r.Store(sys.argv[2],sys.argv[3]),'callers').request('a'*40,'pc2',100)),flush=True)
'''
        callers = [subprocess.Popen([sys.executable, '-c', program, str(authority), str(top / 'store'),
                                     str(repo)], stdout=subprocess.PIPE, text=True) for _ in range(2)]
        answers = [json.loads(child.communicate()[0]) for child in callers]
        row('concurrent-callers', answers[0] == answers[1] and all(child.returncode == 0 for child in callers))
        weekly.cancel(request['run_id'])
        row('cancel-free', store.weekly_read()['repositories']['repository']['last_full_started_at'] is None)
        request = weekly.request(commit, 'pc2', 102)
        custody = H.WeeklyCustody(top / 'lock', 'pc2', lambda: None)
        row('no-custody', weekly.start(request, 102, custody, {})['status'] == 'waiting')
        row('idle-admission', custody.acquire())
        stale = dict(request, run_id='stale')
        snapshot = store.weekly_read()
        row('stale-ticket', weekly.start(stale, 102, custody, {})['status'] == 'waiting')
        with store.weekly_transaction() as ledger:
            ledger.update(snapshot)
        custody.observe = lambda: 'unobservable occupancy'
        row('unobservable', weekly.start(request, 102, custody, {})['status'] == 'waiting')
        custody.observe = lambda: None
        old = {key: dict(result_digest=C.digest(key), stage=stage, depends_on=deps)
               for key, stage, deps in [('a', 'unit', []), ('b', 'unit', ['a']), ('c', 'docs', [])]}
        for key, value in old.items():
            store.put(value['result_digest'], dict(item=key))
        run = weekly.start(request, 102, custody, old)
        snapshot = store.weekly_read()
        row('consumes-once', run['status'] == 'running' and
            weekly.request(commit, 'pc2', 103)['reason'] == 'seven-day limit' and
            weekly.start(request, 103, custody, old)['status'] == 'waiting')
        with store.weekly_transaction() as ledger:
            ledger.update(copy.deepcopy(snapshot))
        row('rolling-week', weekly.request(commit, 'pc2', 102 + W.WEEK_SECONDS - 1).get('reason') == 'seven-day limit')
        with store.weekly_transaction() as ledger:
            ledger.update(copy.deepcopy(snapshot))
        ticket = weekly.red(run['run_id'], ['a'], {'a': 'fresh failure'})
        row('revocation', store.get(old['a']['result_digest']) is None and
            store.get(old['b']['result_digest']) is None and store.get(old['c']['result_digest']) is not None)
        row('ticket-idempotent', weekly.red(run['run_id'], ['a'], {}) == ticket)
        def unavailable(_):
            raise OSError('backlog offline')
        row('ticket-retry', refused(lambda: weekly.deliver_ticket(run['run_id'], unavailable)) and
            R.Store(top / 'store', repo).weekly_read()['repositories']['repository']['runs'][run['run_id']]['ticket']['status'] == 'pending')
        delivered = weekly.deliver_ticket(run['run_id'], lambda body: 'VELDO-fixture-' + body['key'])
        row('ticket-delivered', delivered['status'] == 'delivered' and
            weekly.deliver_ticket(run['run_id'], unavailable) == delivered)
        request2 = weekly.request(commit, 'pc2', 102 + W.WEEK_SECONDS)
        run2 = weekly.start(request2, 102 + W.WEEK_SECONDS, custody, old)
        weekly.recover(run2['run_id'])
        row('crash-revokes', store.get(old['c']['result_digest']) is None)
        row('crash-consumes-week', weekly.request(commit, 'pc2', 103 + W.WEEK_SECONDS)['status'] == 'waiting')
        custody.close()

        # The ledger remains an authority across restarts. Editing it never resets the limit.
        path = top / 'store/weekly.json'
        saved = path.read_bytes()
        damaged = json.loads(saved)
        damaged['payload']['revoked'] = []
        path.write_text(json.dumps(damaged))
        row('corrupt-authority', refused(lambda: weekly.request(commit, 'pc2', 9999999)) and
            store.get(old['a']['result_digest']) is None)
        path.write_bytes(saved)

        # Host observation covers every user, includes sleeping jobs and fails on hidden /proc.
        proc = top / 'proc'
        proc.mkdir()
        p = proc / '123'
        p.mkdir()
        (p / 'stat').write_text('123 (fixture) S 1 1 1 1 1 0 0')
        (p / 'exe').symlink_to('/usr/bin/fixture')
        (p / 'cgroup').write_text('0::/user.slice/job.scope\n')
        config = dict(enrolled=True, launchers_enrolled=True, allowed_system_services=[])
        row('busy-census', H.weekly_occupancy(config, proc_root=proc) == 'busy process 123')
        row('unenrolled', H.weekly_occupancy(dict(config, enrolled=False), proc_root=proc) == 'host is not enrolled')
        row('launchers-enrolled', H.weekly_occupancy(dict(config, launchers_enrolled=False), proc_root=proc) == 'launchers are not enrolled')
        services = [dict(executable='/usr/bin/fixture', cgroup='/user.slice/job.scope')]
        row('service-allowlist', H.weekly_occupancy(dict(config, allowed_system_services=services), proc_root=proc) is None)
        (p / 'cgroup').unlink()
        row('hidden-census', H.weekly_occupancy(config, proc_root=proc) is not None)

        # Controlled competitor owns a real shared lock, even with an optimistic first census.
        competitor = subprocess.Popen([sys.executable, '-c',
            'import fcntl,sys; f=open(sys.argv[1],"a+"); fcntl.flock(f,fcntl.LOCK_SH); '
            'print("held",flush=True); sys.stdin.readline()', str(top / 'competing.lock')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            assert competitor.stdout.readline().strip() == 'held'
            hold = H.WeeklyCustody(top / 'competing.lock', 'pc2', lambda: None)
            row('busy-waits', not hold.acquire())
            arrival = H.weekly_workload(top / 'competing.lock')
            row('reservation-blocks-arrivals', arrival is None)
            if arrival is not None:
                os.close(arrival)
            competitor.stdin.write('finish\n')
            competitor.stdin.flush()
            competitor.wait()
            row('idle-starts', hold.acquire())
            arrival = H.weekly_workload(top / 'competing.lock')
            row('exclusive-run', arrival is None)
            if arrival is not None:
                os.close(arrival)
            hold.observe = lambda: 'unrelated work appeared'
            row('intrusion-red', not hold.admitted('pc2'))
            hold.close()
            arrival = H.weekly_workload(top / 'competing.lock')
            row('released', arrival is not None)
            if arrival is not None:
                os.close(arrival)
        finally:
            if competitor.poll() is None:
                competitor.kill()
                competitor.wait()
            competitor.stdin.close()
            competitor.stdout.close()

        # A crash leaves keeper custody through descendant cleanup AND receipt persistence.
        # Pipes provide ordering; no sleeps, polling clock or duration assertions.
        driver = top / 'custody.py'
        driver.write_text('''import importlib.util,os,signal,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('host',sys.argv[1]); h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
c=h.WeeklyCustody(sys.argv[2],'pc2',lambda:None)
assert c.acquire()
def cleanup(groups):
    print('cleanup',flush=True)
    with open(sys.argv[3]) as pipe: pipe.read(1)
    h.weekly_stop_groups(groups)
def recover():
    print('persist',flush=True)
    with open(sys.argv[4]) as pipe: pipe.read(1)
    Path(sys.argv[5]).write_text('revoked')
c.guard(cleanup,recover)
child=c.launch([sys.executable,'-c',"import os,signal; os.fork(); print(os.getpid(),flush=True); signal.pause()"],stdout=subprocess.PIPE,text=True)
assert child.stdout.readline() and child.stdout.readline()
print('ready',child.pid,flush=True)
signal.pause()
'''.replace('import importlib.util,os,signal,sys', 'import importlib.util,os,signal,sys,subprocess'))
        first, second, receipt = top / 'cleanup.pipe', top / 'persist.pipe', top / 'receipt'
        os.mkfifo(first)
        os.mkfifo(second)
        worker = subprocess.Popen([sys.executable, str(driver), str(authority / 'scripts/gate_host.py'),
                                   str(top / 'crash.lock'), str(first), str(second), str(receipt)],
                                  stdout=subprocess.PIPE, text=True)
        ready = worker.stdout.readline().split()
        assert ready[0] == 'ready'
        group = int(ready[1])
        worker.kill()
        worker.wait()
        assert worker.stdout.readline().strip() == 'cleanup'
        blocked = H.weekly_workload(top / 'crash.lock')
        row('lock-custody', blocked is None and H.group_live(group))
        if blocked is not None:
            os.close(blocked)
        with first.open('w') as stream:
            stream.write('x')
        assert worker.stdout.readline().strip() == 'persist'
        blocked = H.weekly_workload(top / 'crash.lock')
        row('receipt-custody', blocked is None and not receipt.exists())
        if blocked is not None:
            os.close(blocked)
        with second.open('w') as stream:
            stream.write('x')
        worker.stdout.read()  # EOF comes only after the keeper releases its descriptors.
        worker.stdout.close()
        admitted = H.weekly_workload(top / 'crash.lock')
        row('crash-release', admitted is not None and receipt.read_text() == 'revoked' and not H.group_live(group))
        if admitted is not None:
            os.close(admitted)

        # Fresh publication is exercised with real authenticated dependency/result records.
        # Build a tiny repository and inventory; no production full gate is invoked.
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
        git('init', '-q')
        (repo / 'input').write_text('fixture')
        git('add', '.')
        git('-c', 'user.name=Dmitry Grinberg', '-c', 'user.email=dmitry@bcengi.com', 'commit', '-qm', 'fixture')
        head = git('rev-parse', 'HEAD')
        item = C.identity('suite', 'unit', 'confined', 'fixture')
        inventory = C.inventory([dict(item_id=item, state='required', definition_digest=C.digest('fixture'), reason=None)])
        dep = C.sealed(C.DEPENDENCY, item_id=item, observed_commit=head, paths=['input'], directories=[],
                       absent_paths=[], runtime_digest=C.digest('runtime'), complete=True, unknown_reason=None)
        result = C.sealed(C.RESULT, item_id=item, source_commit=head, status='passed', complete=True,
                          dependency_record_digest=dep['record_digest'])
        store.change_put(dep)
        store.change_put(result)
        entry = dict(item_id=item, status='executed', dependency_record_digest=dep['record_digest'],
                     result_digest=result['record_digest'], source_commit=head, source_gate_digest=None)
        receipt = C.sealed(C.RECEIPT, candidate_commit=head, baseline_commit=None, baseline_record_digest=None,
                           changed_paths_digest=C.digest([]), inventory_digest=inventory['record_digest'], items=[entry])
        clean = W.Weekly(store, 'refresh')
        holder = H.WeeklyCustody(top / 'fresh.lock', 'pc2', lambda: None)
        assert holder.acquire()
        pending = clean.request(head, 'pc2', 0)
        fresh = clean.start(pending, 0, holder, {})
        bad = C.sealed(C.RECEIPT, **{k: v for k, v in receipt.items() if k not in ('schema', 'record_digest', 'items')}, items=[])
        row('partial-not-green', refused(lambda: clean.green(fresh['run_id'], repo, inventory, bad)))
        plan = W.fresh_plan(repo, head, inventory)
        row('fresh-plan', plan['cache_reads'] is False and plan['fresh_build_outputs'] is True and
            plan['publish'] is True and plan['mutation_scope'] == 'suite' and
            plan['controls'] == 'once-per-suite' and [i['action'] for i in plan['items']] == ['execute'])
        (repo / 'input').write_text('changed')
        row('dirty-checkout', refused(lambda: W.fresh_plan(repo, head, inventory)))
        (repo / 'input').write_text('fixture')
        gate = clean.green(fresh['run_id'], repo, inventory, receipt)
        row('green-refresh', store.change_gate('refresh', head) is not None and
            gate['receipt']['items'][0]['source_commit'] == head and
            store.weekly_read()['repositories']['refresh']['runs'][fresh['run_id']]['status'] == 'green')
        holder.close()
        # A passing confined item remains unknown; its complete sibling can carry.
        unknown_id = C.identity('suite', 'unit', 'confined', 'unknown')
        mixed_inventory = C.inventory([*inventory['items'], dict(item_id=unknown_id,
            state='required', definition_digest=C.digest('confined'), reason=None)])
        unknown = C.sealed(C.DEPENDENCY, item_id=unknown_id, observed_commit=head,
            paths=['input'], directories=[], absent_paths=[], runtime_digest=C.digest('runtime'),
            complete=False, unknown_reason='confined runner: native observation unavailable')
        unknown_result = C.sealed(C.RESULT, item_id=unknown_id, source_commit=head,
            status='passed', complete=True, dependency_record_digest=unknown['record_digest'])
        assert store.change_put(unknown) and store.change_put(unknown_result)
        unknown_entry = dict(item_id=unknown_id, status='executed',
            dependency_record_digest=unknown['record_digest'], result_digest=unknown_result['record_digest'],
            source_commit=head, source_gate_digest=None)
        mixed_receipt = C.sealed(C.RECEIPT, candidate_commit=head, baseline_commit=None,
            baseline_record_digest=None, changed_paths_digest=C.digest(None),
            inventory_digest=mixed_inventory['record_digest'], items=[entry, unknown_entry])
        mixed = W.Weekly(store, 'mixed')
        holder = H.WeeklyCustody(top / 'mixed.lock', 'pc2', lambda: None)
        assert holder.acquire()
        pending = mixed.request(head, 'pc2', 0)
        started = mixed.start(pending, 0, holder, {})
        mixed_gate = None
        try:
            mixed_gate = mixed.green(started['run_id'], repo, mixed_inventory, mixed_receipt)
        except ValueError:
            pass
        row('unknown-seed-green', mixed_gate is not None and mixed_gate['status'] == 'green' and
            store.get(unknown['record_digest']) == unknown)
        if mixed_gate is None:
            # Keep the independent selector rows observable after a settlement defect.
            # The unknown-seed-green row above remains red.
            mixed_gate = C.publish_gate(repo, store, 'mixed', mixed_inventory, mixed_receipt)
        holder.close()
        (repo / 'unrelated').write_text('edit')
        git('add', '.')
        git('-c', 'user.name=Dmitry Grinberg', '-c', 'user.email=dmitry@bcengi.com',
            'commit', '-qm', 'unrelated')
        next_head = git('rev-parse', 'HEAD')
        selected = C.select(repo, store, 'mixed', next_head, mixed_inventory,
            {item: dep['runtime_digest'], unknown_id: unknown['runtime_digest']})
        choices = {i['item_id']: i for i in selected['items']}
        row('unknown-always-runs', choices[unknown_id]['status'] == 'run' and
            choices[unknown_id]['reason'] == 'unknown dependency')
        row('complete-sibling-carries', choices[item]['status'] == 'carried' and
            choices[item]['evidence']['source_gate_digest'] == mixed_gate['record_digest'])
        forged = dict(selected, items=[dict(i, status='carried', evidence=dict(unknown_entry,
            status='carried', source_gate_digest=mixed_gate['record_digest']))
            if i['item_id'] == unknown_id else i for i in selected['items']])
        row('unknown-carry-rejected', refused(lambda: C.publish_gate(repo, store, 'mixed',
            mixed_inventory, C.assemble(forged, {}))))
        refreshed_unknown = C.sealed(C.DEPENDENCY, **dict(
            {k: v for k, v in unknown.items() if k not in ('schema', 'record_digest')},
            observed_commit=next_head))
        refreshed_result = C.sealed(C.RESULT, item_id=unknown_id, source_commit=next_head,
            status='passed', complete=True, dependency_record_digest=refreshed_unknown['record_digest'])
        assert store.change_put(refreshed_unknown) and store.change_put(refreshed_result)
        refreshed_entry = dict(unknown_entry, source_commit=next_head,
            dependency_record_digest=refreshed_unknown['record_digest'], result_digest=refreshed_result['record_digest'])
        refreshed_plan = dict(selected, items=[dict(i, status='run', evidence=None)
            if i['item_id'] == unknown_id else i for i in selected['items']])
        later_gate = C.publish_gate(repo, store, 'mixed', mixed_inventory,
            C.assemble(refreshed_plan, {unknown_id: refreshed_entry}))
        (repo / 'unrelated').write_text('another edit')
        git('add', '.')
        git('-c', 'user.name=Dmitry Grinberg', '-c', 'user.email=dmitry@bcengi.com',
            'commit', '-qm', 'another unrelated edit')
        later = C.select(repo, store, 'mixed', git('rev-parse', 'HEAD'), mixed_inventory,
            {item: dep['runtime_digest'], unknown_id: unknown['runtime_digest']})
        row('unknown-runs-after-refresh', later_gate['status'] == 'green' and
            {i['item_id']: i['status'] for i in later['items']} ==
            {item: 'carried', unknown_id: 'run'} and
            store.get(refreshed_unknown['record_digest'])['unknown_reason'] == unknown['unknown_reason'])
        git('checkout', '-q', '--detach', head)
        # The dormant adapter stops only its own work and persists red on intrusion.
        intrusion = W.Weekly(store, 'intrusion')
        pending = intrusion.request(head, 'pc2', 0)
        holder = H.WeeklyCustody(top / 'intrusion.lock', 'pc2', lambda: None)
        def invaded(plan, monitor, launch):
            holder.observe = lambda: 'unrelated work appeared'
            monitor()
        row('adapter-intrusion', refused(lambda: intrusion.execute(pending, 0, holder, repo, inventory,
            old, invaded, H.weekly_stop_groups)) and
            store.weekly_read()['repositories']['intrusion']['runs'][pending['run_id']]['status'] == 'red')


_v367_weekly()
