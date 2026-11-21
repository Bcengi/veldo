"""VELDO-0224: real coordinator, session, trace validation and cleanup, controlled worker launches.

The fixture candidate is separate from the authority. A child executes its suite in the declared
snapshot or full frozen tree; a supplied syscall trace exercises Workers.finish without ptrace
(which is unavailable in the confined mutation leg). Git/input discovery, runtime fingerprints
and deadline metadata are fixture values; frozen contents, authentication and result checks are real.
"""


def _v224_stale():
    import copy
    import json
    from pathlib import Path
    import subprocess
    import sys
    import tempfile
    import time
    import types
    from unittest.mock import patch

    def module(source, name):
        result = types.ModuleType('v224_' + name)
        result.__file__ = str(ROOT / 'scripts' / (name + '.py'))
        exec(compile(source.read_text(), result.__file__, 'exec'), result.__dict__)
        return result

    C = module(ROOT / "scripts" / "case_reuse.py", 'case_reuse')
    gate = module(ROOT / "scripts" / "check_gate_mutations.py", 'check_gate_mutations')
    P = module(ROOT / "scripts" / "propose_case_inputs.py", 'propose_case_inputs')
    if not leg_runs():
        return
    M, I, R = C.M, C.I, C.R
    materializer = gate.load(ROOT / 'scripts/mutation_observer.py')
    suite_body = ("ns = {}; exec(SUBJECT.read_text(), ns)\n"
                  "expect('fixture target', ns['value'] == 1 and not BROKEN)\n")

    def row(name, condition, detail=''):
        expect('VELDO-0224 stale-declarations/' + name + ': ' + detail, condition)

    def obs(ok):
        return dict(count=1, observations=[['fixture target', ok]], row_names=['fixture target'],
                    failed_rows=[] if ok else ['fixture target'])

    def record(case, session):
        return dict(schema=gate.SCHEMA, case=case, fixture_version=gate.FIXTURE_VERSION,
                    input_digest=session.input_digest(case), replacement_count=1,
                    old_digest='old', new_digest='new', baseline=obs(True), noop=obs(True), mutant=obs(False))

    def qualify(document, files):
        review = dict(schema=C.REVIEW_SCHEMA, reviewer='fixture reviewer', commit='f' * 40, cases={})
        for name, entry in document['cases'].items():
            entry['proposal'] = dict(runs=[dict(mode=mode, exit=0, reads='same', trace='trace',
                observation='seen', non_file=[]) for mode in C.TRACED_RUNS], gate_observation='seen',
                inputs='inputs', gate_receipt=dict(status='passed', input_digest='inputs'))
            entry['review'] = 'proof/VELDO-0217/reviews/fixture.json'
            review['cases'][name] = dict(declaration=C.declaration_digest(entry), traces=['trace'] * 4)
        files['proof/VELDO-0217/reviews/fixture.json'] = (0o644, R.canonical(review))
        files[I.DECLARATIONS] = (0o644, R.canonical(document))

    with tempfile.TemporaryDirectory(prefix='v224-') as temporary:
        top = Path(temporary)
        names = ['import-baseline', 'import-noop', 'import-mutant', 'deleted', 'closure', 'clean']
        cases = [dict(name=n, identity=gate.DRIVERS[0] + ':' + n, driver=gate.DRIVERS[0],
                      module='subject.py', suite='test.py', old='value = 1', new='value = 0',
                      rows=['target']) for n in names]
        files = {p: ((ROOT / p).stat().st_mode & 0o777, (ROOT / p).read_bytes())
                 for p in (*I.MANDATORY, *I.DRIVERS)}
        files.update({'.veldo/subject.py': (0o644, b'value = 1\n'),
                      'optional-declared': (0o644, b'old input'),
                      'helper.py': (0o644, b'VALUE = True\n'),
                      'scripts/suites/test.py': (0o644, suite_body.encode())})
        document = dict(schema='veldo.case-inputs/v1', toolchains={gate.DRIVERS[0]:
                        dict(paths=['/usr'], reviewed=True)}, cases={c['identity']:
                        dict(files=['optional-declared'] if c['name'] == 'deleted' else [],
                             absent=['appeared'] if c['name'] == 'closure' else [], directories=[],
                             reviewed=True, non_file_inputs='none', rationale='Fixture file-only inputs.')
                        for c in cases})
        qualify(document, files)
        original_session, original_load = C.Session, gate.load
        launched, released = [], []
        failure = [False]

        class FixtureWorkers(gate.Workers):
            def release_snapshot(self, name):
                path = self.owned_snapshots.get(name)
                super().release_snapshot(name)
                if path is not None:
                    released.append(not path.exists())

            def run(self, jobs, directory, frozen, on_result=None):
                jobs = {name: dict(job) for name, job in jobs.items()}
                self.jobs.update(jobs)
                results = {}
                for name, job in jobs.items():
                    home = directory / str(self.invocations)
                    home.mkdir()
                    self.homes[name] = home
                    self.budgets[name] = 300
                    if job.get('declared_case'):
                        self.owned_snapshots[name] = directory / 'cases' / str(self.invocations)
                        job.update(self.case_reuse.prepare(job['case'], self.owned_snapshots[name]))
                    root = Path(job.get('snapshot_root', frozen))
                    declared = 'snapshot_root' in job
                    launched.append((job['case']['name'], job['mode'], declared))
                    # Child imports the fixture helper only in the newly changed suite's selected
                    # mode. The snapshot omits it. Real stdout/exit are judged by Workers.finish.
                    prepared = materializer.materialize(job['case'], job['mode'], home, root=root)
                    subject = prepared['mutant'] or prepared['source']
                    child = ("import json, sys\nfrom pathlib import Path\n"
                             "root, mode, name, broken, subject = Path(sys.argv[1]), *sys.argv[2:]\n"
                             "rows = []\n"
                             "ns = dict(ROOT=root, MODE=mode, CASE=name, SUBJECT=Path(subject), "
                             "BROKEN=broken == 'True', expect=lambda n, ok: rows.append([n, ok]))\n"
                             "exec((root / 'scripts/suites/test.py').read_text(), ns)\n"
                             "ob = dict(count=len(rows), observations=rows, "
                             "row_names=[n for n, ok in rows], failed_rows=[n for n, ok in rows if not ok])\n"
                             "print(json.dumps(dict(observation=ob, replacement_count=1, "
                             "old_digest='old', new_digest='new')))\n")
                    trace = '100 landlock_restrict_self(5, 0) = 0\n'
                    if job['case']['name'] == 'import-' + job['mode']:
                        trace += '100 openat(AT_FDCWD, ' + json.dumps(str(root / 'helper.py')) + ', O_RDONLY) = -1 ENOENT\n'
                    (directory / ('trace-' + home.name)).write_text(trace + '100 +++ exited with 0 +++\n')
                    out, err = (open(directory / (home.name + '-' + f), 'w+b') for f in ('stdout', 'stderr'))
                    self.resources.acquire(name, job)
                    self.ledgers[name] = directory / ('ownership-' + home.name + '.jsonl')
                    process = subprocess.Popen([sys.executable, '-I', '-B', '-c', child, str(root),
                        job['mode'], job['case']['name'], str(failure[0] and not declared), str(subject)],
                        stdout=out, stderr=err, start_new_session=True)
                    process.wait(timeout=300)
                    self.active[name] = (process, out, err, time.monotonic())
                    self.invocations += 1
                    self.driver_spans.setdefault(job['case']['driver'], [time.monotonic(), time.monotonic()])
                    results[name] = self.finish(name)
                    if on_result is not None:
                        on_result(name, results[name])
                return results

        def drive(label, fail=False, force=False):
            candidate, cache = top / label, top / (label + '-store')
            configuration = dict(fixture_version=gate.FIXTURE_VERSION, capacities=None,
                                 worker_environment=gate.fixed_env('<private-worker-home>'))
            # An earlier valid record for every case, authenticated by the real store.
            with patch.object(C.M, 'runtime_identity', side_effect=lambda paths, env: dict(paths=paths)), \
                 patch.object(C, 'sensitivity_proved', return_value=True):
                old = original_session(candidate, files, cases, 'head', configuration, cache_directory=cache)
                seeded = [old.publish(c, record(c, old), gate.validate_result) for c in cases]
            current = dict(files)
            current.pop('optional-declared')
            current['appeared'] = (0o644, b'now exists')
            # The suite gains an import; its bytes change the key, but its declaration omits the helper.
            current['scripts/suites/test.py'] = (0o644, ("if CASE == 'import-' + MODE:\n"
                "    import importlib.util\n"
                "    spec = importlib.util.spec_from_file_location('helper', ROOT / 'helper.py')\n"
                "    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n" + suite_body).encode())
            I.freeze(candidate, current)
            # Keep fixture writable, so a mutant's candidate write is observed, not denied by modes.
            for p in candidate.rglob('*'):
                if p.is_file():
                    p.chmod(0o644)
            before = R.tree_identity(candidate)
            existing = {p.name: p.read_bytes() for p in cache.glob('*.json')}
            launched.clear(); released.clear(); failure[0] = fail

            def snapshot(root, common, destination, inputs, head):
                I.freeze(destination, inputs)
                return destination / '.git'

            def loader(path):
                return C if Path(path).name == 'case_reuse.py' else original_load(path)

            with patch.object(gate, 'inventory', return_value=cases), \
                 patch.object(gate, 'read_inputs', return_value=current), \
                 patch.object(gate, 'git', return_value='head'), \
                 patch.object(gate, 'snapshot', side_effect=snapshot), \
                 patch.object(gate, 'inputs_unchanged', side_effect=lambda *a: R.tree_identity(candidate) == before), \
                 patch.object(gate, 'Workers', FixtureWorkers), patch.object(gate, 'load', side_effect=loader), \
                 patch.object(gate, 'case_deadlines', side_effect=lambda keys: dict.fromkeys(keys, 300)), \
                 patch.object(gate, 'record_case_times'), \
                 patch.object(gate.SuiteResources, 'from_root', side_effect=lambda *a:
                              gate.SuiteResources({'suites': [{'file': 'test.py'}]})), \
                 patch.object(C.M, 'runtime_identity', side_effect=lambda paths, env: dict(paths=paths)), \
                 patch.object(C, 'sensitivity_proved', return_value=True), \
                 patch.object(C, 'Session', side_effect=lambda *a, **k: original_session(*a, **k, cache_directory=cache)):
                receipt = gate.run_stage(candidate, candidate / '.git', force_fresh=force)
            entries = M.stale_entries(cache)
            new_records = [R.Store(cache, candidate).get(p.stem) for p in cache.glob('*.json')
                           if p.name not in existing]
            selected = P.authority_staleness(document, cache)
            # A subsequent gate cannot hit earlier records, including an otherwise unchanged key.
            with patch.object(C.M, 'runtime_identity', side_effect=lambda paths, env: dict(paths=paths)), \
                 patch.object(C, 'sensitivity_proved', return_value=True):
                later = original_session(candidate, current, cases, 'another-gate', configuration, cache_directory=cache)
                no_hits = all(later.lookup(c, gate.validate_result) is None for c in cases[:-1])
                clean_hit = later.lookup(cases[-1], gate.validate_result) is not None
            return dict(receipt=receipt, seeded=all(seeded), launched=list(launched), entries=entries,
                        new_records=new_records, no_hits=no_hits, clean_hit=clean_hit, selected=selected,
                        unchanged=R.tree_identity(candidate) == before, released=all(released),
                        old_unchanged=all((cache / n).read_bytes() == b for n, b in existing.items()))

        good, bad, forced = drive('candidate'), drive('failing-candidate', fail=True), drive('forced-candidate', force=True)
        receipts = good['receipt']['case_receipts']
        stale_names = {c['identity'] for c in cases[:-1]}
        detail = repr([(d['receipt']['status'], d['receipt'].get('detail'), d['receipt'].get('stale_count'))
                       for d in (good, bad, forced)])
        all_fresh = all((c['name'], mode, False) in good['launched'] for c in cases[:-1]
                        for mode in ('baseline', 'noop', 'mutant'))
        row('runs-fresh', good['receipt']['status'] == forced['receipt']['status'] == 'passed'
            and good['receipt']['stale_count'] == 5 and all_fresh and good['released']
            and all(r['source'] == 'fresh' and r['validated'] and r['reason'] == 'declaration_stale'
                    for r in receipts if r['identity'] in stale_names)
            and bad['receipt']['status'] == 'failed' and bad['receipt']['error'] == 'invalid_baseline', detail)
        row('never-published', good['seeded'] and good['old_unchanged'] and good['no_hits'] and good['clean_hit']
            and good['receipt']['reused'] == 0
            and all(r and r['case']['identity'] not in stale_names for r in good['new_records'])
            and all(r['key'] is None for r in receipts if r['identity'] in stale_names), detail)
        row('authority-store', good['unchanged'] and {e['identity'] for e in good['entries']} == stale_names
            and set(good['selected']) == stale_names
            and all(e['declaration'] == C.declaration_digest(document['cases'][e['identity']])
                    and e['gate_run'] == good['receipt']['gate_run'] and e['reason'] for e in good['entries'])
            and good['receipt']['authority_stale_count'] == 5, detail)
        row('stale-reasons', any('helper.py' in e['reason'] for e in good['entries'])
            and any('optional-declared' in e['reason'] for e in good['entries'])
            and any('appeared' in e['reason'] for e in good['entries']), repr(good['entries']))
        # An audit mismatch uses the same authority API and influences only the matching declaration.
        audit = R.Store(top / 'audit-store', top / 'audit-candidate')
        entry = document['cases'][cases[0]['identity']]
        M.mark_stale(audit, identity=cases[0]['identity'], declaration=C.declaration_digest(entry),
                     gate_run='audit-run', reason='audit mismatch')
        changed = copy.deepcopy(document)
        changed['cases'][cases[0]['identity']]['rationale'] = 'New reviewed declaration.'
        row('audit-consumer', set(P.authority_staleness(document, audit.directory)) == {cases[0]['identity']}
            and P.authority_staleness(changed, audit.directory) == {})
        refused = False
        try:
            M.mark_stale(R.Store(top / 'bad-candidate/store', top / 'bad-candidate'), identity='case',
                         declaration='digest', gate_run='run', reason='stale')
        except ValueError:
            refused = True
        row('candidate-store-refused', refused and not (top / 'bad-candidate').exists())


_v224_stale()
