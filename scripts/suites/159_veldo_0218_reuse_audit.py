"""VELDO-0218: real coordinator/reducer/store; controlled worker results and qualified keys.

Admission, Git snapshots and worker execution are fixture seams. Sampling, comparison,
revocation, stale marks, counters, authentication and landing validation are production paths.
"""


def _v218_audit():
    import copy
    import contextlib
    import io
    import tempfile
    import types
    from pathlib import Path
    from unittest.mock import patch

    def module(source, relative):
        value = types.ModuleType('v218_' + source.stem)
        value.__file__ = str(ROOT / relative)
        exec(compile(source.read_text(), value.__file__, 'exec'), value.__dict__)
        return value

    G = module(ROOT / "scripts" / "check_gate_mutations.py", 'scripts/check_gate_mutations.py')
    M = module(ROOT / "scripts" / "mutation_reuse.py", 'scripts/mutation_reuse.py')
    E = module(ROOT / ".veldo" / "reuse_evidence.py", '.veldo/reuse_evidence.py')
    S = module(ROOT / "scripts" / "reuse_stamp.py", 'scripts/reuse_stamp.py')
    C = G.load(ROOT / 'scripts/case_reuse.py')
    C.M = M
    C.R = M.R
    M.R.E = E
    G.AUDIT = M
    S.E = E
    original_session = C.Session
    original_load = G.load

    def row(name, good, detail=''):
        expect('VELDO-0218 reuse-audit/' + name + ': ' + detail, good)

    def observation(rows):
        return dict(observations=rows, count=len(rows), row_names=[n for n, _ in rows],
                    failed_rows=[n for n, ok in rows if not ok])

    def record(case):
        return dict(schema=G.SCHEMA, fixture_version=G.FIXTURE_VERSION, case=case,
                    input_digest=M.R.digest(case), replacement_count=1, old_digest='old', new_digest='new',
                    baseline=observation([['fixture target', True], ['fixture other', True]]),
                    noop=observation([['fixture target', True], ['fixture other', True]]),
                    mutant=observation([['fixture target', False], ['fixture other', True]]))

    def cases_for(n):
        return [dict(identity=G.DRIVERS[i % 2] + ':audit-' + str(i), name='audit-' + str(i),
                     driver=G.DRIVERS[i % 2], suite='suite-' + str(i % 3) + '.py', module='subject.py',
                     old='value = 1', new='value = 0', rows=['target']) for i in range(n)]

    with tempfile.TemporaryDirectory(prefix='v218-') as temporary:
        top = Path(temporary)
        sequence = [0]
        class Workers(G.Workers):
            def run(self, jobs, directory, frozen, on_result=None):
                self.jobs.update(jobs)
                results = {}
                for name, job in jobs.items():
                    self.invocations += 1
                    case, mode = job['case'], job['mode']
                    fresh = copy.deepcopy(record(case))
                    if change[0]:
                        change[0](fresh)
                    value = dict(observation=fresh[mode], **{k: fresh[k] for k in
                                 ('replacement_count', 'old_digest', 'new_digest')})
                    completed = dict(result=value, elapsed=1.25)
                    self.outcomes.append(dict(name=name, driver=case['driver'], mode=mode,
                                              elapsed=1.25, returncode=0))
                    results[name] = completed
                    if on_result:
                        on_result(name, completed)
                return results

        change = [None]
        def drive(n, warm=None, force=False, alter=None, admitted=False):
            sequence[0] += 1
            candidate = top / ('candidate-' + str(sequence[0]))
            candidate.mkdir()
            declaration = candidate / 'declarations.json'
            declaration.write_text('candidate declaration remains untouched')
            before = declaration.read_bytes()
            cache = top / ('store-' + str(sequence[0]))
            store = M.R.Store(cache, candidate)
            cases = cases_for(n)
            records = {c['identity']: record(c) for c in cases}
            if admitted:
                for r in records.values():
                    r['reuse_admission'] = 'VELDO-0222'
            for c in cases[:n if warm is None else warm]:
                assert store.put(M.R.digest(c), records[c['identity']])
            sessions = []
            def session(root, files, selected, head, configuration, force_fresh=False):
                value = original_session.__new__(original_session)
                value.root, value.files = root, files
                value.forced = force_fresh
                value.base_digest = 'fixture'
                value.case_digests = {c['identity']: M.R.digest(c) for c in selected}
                value.keys = {name: None if force_fresh else key for name, key in value.case_digests.items()}
                value.reasons = dict.fromkeys(value.keys, 'force_fresh' if force_fresh else 'miss')
                value.hits, value.stale, value.snapshots = {}, {}, {}
                value.runtime_checks, value.runtime_absent = {}, {}
                value.reviewed = dict.fromkeys(value.keys, {'rationale': 'controlled admission'})
                value.gate_run = 'fixture-run-' + str(sequence[0])
                value.store = store
                value.store_directory = lambda: cache
                sessions.append(value)
                return value
            files = {'scripts/check_gate_mutations.py': (0o644, b'fixture authority')}
            change[0] = alter
            with patch.object(C, 'Session', side_effect=session), \
                 patch.object(G, 'load', side_effect=lambda p: C if p.name == 'case_reuse.py' else original_load(p)), \
                 patch.object(G, 'inventory', return_value=cases), patch.object(G, 'read_inputs', return_value=files), \
                 patch.object(G, 'git', return_value='a' * 40), patch.object(G, 'snapshot'), \
                 patch.object(G, 'inputs_unchanged', return_value=True), patch.object(G, 'Workers', Workers), \
                 patch.object(G, 'case_deadlines', side_effect=lambda keys: dict.fromkeys(keys, 300)), \
                 patch.object(G, 'record_case_times'), patch.object(G.SuiteResources, 'from_root',
                    side_effect=lambda *a: G.SuiteResources({'suites': [{'file': c['suite']} for c in
                        {c['suite']: c for c in cases}.values()]})), contextlib.redirect_stdout(io.StringIO()):
                receipt = G.run_stage(candidate, candidate / '.git', force_fresh=force)
            return receipt, store, sessions[0], declaration.read_bytes() == before

        # Identity hashing is fixture metadata; the authenticated envelopes and file permissions are real.
        with patch.object(E, 'authority_identity', return_value='a' * 64):
            summaries, good = [], True
            for n in (0, 1, 7, 8, 100, 2000):
                # A zero-hit stage still has fresh cases to run (an empty inventory is correctly refused).
                receipt, _, _, _ = drive(max(n, 1), warm=n)
                audit = receipt['audit']
                ids = [e['identity'] for e in audit['entries']]
                good &= (receipt['status'] == 'passed' and len(ids) >= max(min(n, 8), (n + 19) // 20)
                         and len(ids) == len(set(ids)) and len(audit['population']) == n
                         and receipt['reused'] == n - len(ids)
                         and all(s['audited'] >= (s['hits'] + 19) // 20 for s in audit['suites'].values()))
                summaries.append((n, receipt['executed'], receipt['reused'], audit['audited'], audit['suites']))
            ten, _, _, _ = drive(100, admitted=True)
            good &= (ten['status'] == 'passed' and ten['audit']['audited'] >= 10
                     and all(s['audited'] >= (s['hits'] + 9) // 10 for s in ten['audit']['suites'].values()))
            row('sample-size', good, repr(summaries))

            values = {c['identity']: record(c) for c in cases_for(2000)}
            first, second = M.audit_sample(values), M.audit_sample(values)
            # Fixed entropy is the positive control: deterministic draws repeat. Production requests
            # OS bytes after lookup; patching only that entropy also proves it is actually consumed.
            with patch.object(M.os, 'urandom', return_value=b'x' * 32) as entropy:
                fixed1, fixed2 = M.audit_sample(values), M.audit_sample(values)
            row('unpredictable', first != second and fixed1 == fixed2 and entropy.call_count == 2)

            changes = {
                'baseline': lambda r: r.update(baseline=observation([['changed target', True], ['fixture other', True]])),
                'noop': lambda r: r.update(noop=observation([['changed target', True], ['fixture other', True]])),
                'mutant_targets': lambda r: r.update(mutant=observation([['changed target', False], ['fixture other', True], ['fixture target', False]])),
                'replacement_count': lambda r: r.update(replacement_count=2),
                'old_digest': lambda r: r.update(old_digest='changed'),
                'new_digest': lambda r: r.update(new_digest='changed'),
            }
            compared = []
            for field, edit in changes.items():
                receipt, store, session, unchanged = drive(1, alter=edit)
                entry = receipt['audit']['entries'][0]
                marks = M.stale_entries(store.directory)
                compared.append((field, receipt.get('error'), sorted(entry['differences'])))
                good = (receipt['status'] == 'failed' and field in entry['differences']
                        and entry['differences'].get(field, {}).get('verdict') and not entry['matched']
                        and store.get(entry['key']) is None
                        and not (store.directory / (entry['key'] + '.json')).exists()
                        and len(marks) == 1 and marks[0]['identity'] == entry['identity']
                        and marks[0]['gate_run'] == session.gate_run and unchanged)
                row('field/' + field, good, repr(compared[-1]))
            same, _, _, _ = drive(1)
            other, _, _, _ = drive(1, alter=lambda r: r.update(mutant=observation(
                [['fixture target', False], ['fixture other', False], ['extra unrelated', True]])))
            valid_diff, _, _, _ = drive(1, alter=lambda r: r.update(
                baseline=observation([['fixture target', True], ['fixture other', True], ['extra row', True]]),
                noop=observation([['fixture target', True], ['fixture other', True], ['extra row', True]]),
                mutant=observation([['fixture target', False], ['fixture other', True], ['extra row', True]])))
            row('compare', all(name in fields for name, _, fields in compared)
                and all(code in ('control_failed', 'missing_target', 'driver_error', 'reuse_audit_mismatch')
                        for _, code, _ in compared)
                and valid_diff['status'] == 'failed' and valid_diff['error'] == 'reuse_audit_mismatch'
                and same['status'] == other['status'] == 'passed'
                and same['audit']['entries'][0]['differences'] == {}
                and other['audit']['entries'][0]['differences']['mutant_other']['verdict'] is False,
                repr(compared))

            outcomes = []
            for label, n, hits, forced in [('cold', 12, 0, False), ('warm', 12, 12, False),
                                          ('mixed', 20, 12, False), ('force', 12, 12, True),
                                          ('all-audited', 1, 1, False)]:
                receipt, store, _, _ = drive(n, warm=hits, force=forced)
                with patch.object(E, 'configuration', return_value=(None, {'store': str(store.directory)})):
                    fields = S.fields(receipt, forced, 'b' * 40)
                    stamp = dict(fields, commit='b' * 40)
                    accepted = E.landing_problem(stamp) is None
                    absent_refused = True
                    if hits and not forced:
                        missing = copy.deepcopy(receipt)
                        del missing['audit']
                        try:
                            S.fields(missing, forced, 'b' * 40)
                        except (ValueError, TypeError, KeyError):
                            pass
                        else:
                            absent_refused = False
                        removed = copy.deepcopy(receipt)
                        removed['audit']['entries'] = []
                        try:
                            S.fields(removed, forced, 'b' * 40)
                        except (ValueError, TypeError, KeyError):
                            pass
                        else:
                            absent_refused = False
                        # Re-sign to test landing's contract, independently of envelope authentication.
                        payload = copy.deepcopy(stamp['reuse_evidence']['payload'])
                        payload['audit']['entries'] = []
                        absent_refused &= E.landing_problem(dict(stamp, reuse_evidence=E.sign(payload, store.secret))) is not None
                    ids = [r['case']['identity'] for r in receipt['results']]
                    selected = [r for r in receipt['results'] if r.get('audited')]
                    honest = (len(ids) == len(set(ids)) == n and receipt['executed'] + receipt['reused'] == n
                              and len(selected) == receipt['audit']['audited']
                              and all(r['source'] == 'fresh' and r['reuse_key'] for r in selected)
                              and (not forced or receipt['reused'] == receipt['audit']['audited'] == 0))
                    outcomes.append((label, accepted, absent_refused, honest, receipt['executed'], receipt['reused']))
            row('receipts', all(all(item[1:4]) for item in outcomes), repr(outcomes))
            row('worker-seconds', same['audit']['worker_seconds'] == 3.75
                and same['audit']['matched'] == 1 and same['audit']['mismatched'] == 0)


_v218_audit()
