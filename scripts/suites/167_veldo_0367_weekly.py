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
               'gate_reuse.py': ROOT / "scripts" / "gate_reuse.py"}

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
        shutil.copyfile(ROOT / 'scripts/gate_changes.py', authority / 'scripts/gate_changes.py')
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
        row('inactive', W.WEEKLY_ENABLED is False)
        request = weekly.request(commit, 'pc2', 100)
        row('two-callers', weekly.request('b' * 40, 'other-host', 101) == request)
        weekly.cancel(request['run_id'])
        row('cancel-free', store.weekly_read()['repositories']['repository']['last_full_started_at'] is None)
        request = weekly.request(commit, 'pc2', 102)
        custody = H.WeeklyCustody(top / 'lock', 'pc2', lambda: None)
        row('no-custody', weekly.start(request, 102, custody, {})['status'] == 'waiting')
        row('idle-admission', custody.acquire())
        stale = dict(request, run_id='stale')
        row('stale-ticket', weekly.start(stale, 102, custody, {})['status'] == 'waiting')
        custody.observe = lambda: 'unobservable occupancy'
        row('unobservable', weekly.start(request, 102, custody, {})['status'] == 'waiting')
        custody.observe = lambda: None
        old = {key: dict(result_digest=C.digest(key), stage=stage, depends_on=deps)
               for key, stage, deps in [('a', 'unit', []), ('b', 'unit', ['a']), ('c', 'docs', [])]}
        for key, value in old.items():
            store.put(value['result_digest'], dict(item=key))
        run = weekly.start(request, 102, custody, old)
        row('consumes-once', run['status'] == 'running' and
            weekly.request(commit, 'pc2', 103)['reason'] == 'seven-day limit' and
            weekly.start(request, 103, custody, old)['status'] == 'waiting')
        row('rolling-week', weekly.request(commit, 'pc2', 102 + W.WEEK_SECONDS - 1)['status'] == 'waiting')
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
        row('unenrolled', H.weekly_occupancy(dict(config, enrolled=False), proc_root=proc) is not None)
        row('launchers-enrolled', H.weekly_occupancy(dict(config, launchers_enrolled=False), proc_root=proc) is not None)
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
child=c.launch([sys.executable,'-c',"import os,signal; os.fork(); print('descendant',flush=True); signal.pause()"],stdout=subprocess.DEVNULL)
print('ready',flush=True)
signal.pause()
'''.replace('import importlib.util,os,signal,sys', 'import importlib.util,os,signal,sys,subprocess'))
        first, second, receipt = top / 'cleanup.pipe', top / 'persist.pipe', top / 'receipt'
        os.mkfifo(first)
        os.mkfifo(second)
        worker = subprocess.Popen([sys.executable, str(driver), str(authority / 'scripts/gate_host.py'),
                                   str(top / 'crash.lock'), str(first), str(second), str(receipt)],
                                  stdout=subprocess.PIPE, text=True)
        assert worker.stdout.readline().strip() == 'ready'
        worker.kill()
        worker.wait()
        assert worker.stdout.readline().strip() == 'cleanup'
        blocked = H.weekly_workload(top / 'crash.lock')
        row('lock-custody', blocked is None)
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
        row('crash-release', admitted is not None and receipt.read_text() == 'revoked')
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
        gate = clean.green(fresh['run_id'], repo, inventory, receipt)
        row('green-refresh', gate['receipt']['items'][0]['source_commit'] == head and
            store.weekly_read()['repositories']['refresh']['runs'][fresh['run_id']]['status'] == 'green')
        holder.close()


_v367_weekly()
