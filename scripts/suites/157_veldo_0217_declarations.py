"""VELDO-0217: every confined mutation case gets a current, reviewed input declaration with complete keys.

Rows run on fixture repositories in scratch directories: the proposer's capture, staleness and
completeness (AC1), case_reuse's review conditions (AC2) and key (AC3), and the trace classifier and
the coordinator's publish path for non-file inputs (AC4). Nothing here traces a process, so every row
runs in the confined leg and inside mutation confinement; the traced rows of this ticket are in
100_veldo_0207_case_reuse (its strace rows). Mutated modules are loaded from the driver's anchors and
run as the repository's own file, so their siblings are the repository's.
"""


def _v217_declarations():
    import copy
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import types
    from unittest.mock import patch

    def as_module(source, name):
        """The module at `source` (the repository's, or a mutant's copy) run as the repository's own
        scripts/<name>.py, so the siblings it loads are the repository's."""
        module = types.ModuleType('v217_' + name)
        module.__file__ = str(ROOT / 'scripts' / (name + '.py'))
        exec(compile(Path(source).read_text(), module.__file__, 'exec'), module.__dict__)
        return module

    def load(name):
        spec = importlib.util.spec_from_file_location('v217_' + name, ROOT / 'scripts' / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    propose_source = ROOT / "scripts" / "propose_case_inputs.py"
    reuse_source = ROOT / "scripts" / "case_reuse.py"
    trace_source = ROOT / "scripts" / "case_trace.py"
    gate_source = ROOT / "scripts" / "check_gate_mutations.py"
    policy_source = ROOT / ".veldo" / "policy.yaml"
    P = as_module(propose_source, 'propose_case_inputs')
    C = as_module(reuse_source, 'case_reuse')
    T = as_module(trace_source, 'case_trace')
    gate = as_module(gate_source, 'check_gate_mutations')
    I, R = C.I, C.R

    def row(name, condition):
        expect('VELDO-0217 declarations/' + name, condition)

    if leg_runs():
        expect('VELDO-0217 declarations/spec',
               V.check_spec(ROOT / 'specs/VELDO-0217-every-confined-case-has-a-reviewed-input-declaration.md') == 0)

    def qualify(document, files, names=None):
        """Give reviewed fixture declarations the traced proposal AC2 requires and one review record
        binding each declaration's digest and trace digests."""
        record = {'schema': C.REVIEW_SCHEMA, 'batch': 'fixture', 'reviewer': 'independent fixture reviewer',
                  'commit': 'c' * 40, 'cases': {}}
        for name, entry in document['cases'].items():
            entry.setdefault('proposal', {'runs': [
                {'mode': mode, 'exit': 0, 'reads': 'same-reads', 'trace': 'trace-%d' % index,
                 'observation': 'seen', 'non_file': []} for index, mode in enumerate(C.TRACED_RUNS)],
                'gate_observation': 'seen', 'inputs': 'traced-inputs',
                'gate_receipt': {'status': 'passed', 'input_digest': 'traced-inputs', 'digest': 'r' * 64}})
            entry['review'] = 'proof/VELDO-0217/reviews/fixture.json'
            if names is None or name in names:
                record['cases'][name] = {'declaration': C.declaration_digest(entry),
                                         'traces': [r['trace'] for r in entry['proposal']['runs']]}
        files['proof/VELDO-0217/reviews/fixture.json'] = (0o644, R.canonical(record))
        bind(document, files)

    def bind(document, files):
        """The owner's approval binds the exact bytes of each declaration's review record (F4)."""
        for entry in document['cases'].values():
            if entry.get('review') in files:
                entry['review_sha256'] = hashlib.sha256(files[entry['review']][1]).hexdigest()
        files[I.DECLARATIONS] = (0o644, R.canonical(document))

    def machinery():
        return {p: ((ROOT / p).stat().st_mode & 0o777, (ROOT / p).read_bytes()) for p in (*I.MANDATORY, *I.DRIVERS)}

    def fixture_case(name, suite, module='subject.py', driver=None):
        driver = driver or gate.DRIVERS[0]
        return {'name': name, 'identity': driver + ':' + name, 'driver': driver, 'module': module,
                'suite': suite, 'old': 'value = 1', 'new': 'value = 0', 'rows': ['target']}

    def declared(files=(), **extra):
        return dict({'files': list(files), 'absent': [], 'directories': [], 'reviewed': True,
                     'non_file_inputs': 'none', 'rationale': 'Controlled file-only fixture.'}, **extra)

    with tempfile.TemporaryDirectory(prefix='v217-declarations-') as temporary:
        top = Path(temporary)

        # AC1: the seven declarations whose suite now loads scripts/suites/support/compiled_sources.py
        # while their declared files omit it. Each was proposed from its suite's old bytes; the suite now
        # loads the helper. The proposer finds each stale from its recorded digests, and its re-proposal,
        # captured through its own audit channel from a real run of the suite, includes the helper.
        if leg_runs():
            seven = ['effects-worker-scope', 'message-speaker-is-edge', 'account-codex-old-tables',
                     'limit-unreported', 'codex-baseline-user-config-loaded', 'worker129-build-unwired',
                     'receiver148-placement-wait-unbounded']
            root = top / 'stale'
            for relative in (*I.MANDATORY, *I.DRIVERS):
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, root / relative)
            helper = root / 'scripts/suites/support/compiled_sources.py'
            helper.parent.mkdir(parents=True, exist_ok=True)
            helper.write_text('COMPILED = {"fixture": 1}\n')
            old_declarations, suites = {}, {}
            for index, name in enumerate(seven):
                suite = root / 'scripts/suites' / ('s%d_fixture.py' % index)
                module = root / '.veldo' / ('m%d.py' % index)
                module.parent.mkdir(parents=True, exist_ok=True)
                module.write_text('value = %d\n' % index)
                suite.write_text("value = (ROOT / '.veldo' / 'm%d.py').read_text()\n" % index)
                files = sorted({str(suite.relative_to(root)), str(module.relative_to(root)), *I.MANDATORY, *I.DRIVERS})
                old_declarations[gate.DRIVERS[0] + ':' + name] = {
                    'files': files, 'absent': [], 'directories': [], 'reviewed': False,
                    'non_file_inputs': 'none', 'rationale': '',
                    'proposal': {'read_digests': {f: P.file_digest(root / f) for f in files}, 'runs': []}}
                # The pending stack's change: the suite now loads the helper.
                suite.write_text("import importlib.util\n"
                                 "spec = importlib.util.spec_from_file_location('helper', ROOT / 'scripts/suites/support/compiled_sources.py')\n"
                                 "helper = importlib.util.module_from_spec(spec)\n"
                                 "spec.loader.exec_module(helper)\n"
                                 "value = (ROOT / '.veldo' / 'm%d.py').read_text()\n" % index)
                suites[gate.DRIVERS[0] + ':' + name] = suite
            runner = ("import sys, types\nfrom pathlib import Path\n"
                      "source, real, audit, suite, root = sys.argv[1:6]\n"
                      "module = types.ModuleType('propose_case_inputs'); module.__file__ = real\n"
                      "exec(compile(Path(source).read_text(), real, 'exec'), module.__dict__)\n"
                      "handle = open(audit, 'w'); sys.addaudithook(module.audit_hook(handle))\n"
                      "exec(compile(Path(suite).read_text(), suite, 'exec'), {'ROOT': Path(root)})\n")
            reported, failures = {}, []
            for identity, old in old_declarations.items():
                reasons = P.stale(root, old)
                audit = top / ('audit-' + hashlib.sha256(identity.encode()).hexdigest()[:12])
                # As the proposer runs a case: no bytecode written, none read from a shared cache.
                run = subprocess.run([sys.executable, '-I', '-S', '-B', '-X', 'pycache_prefix=' + str(audit) + '-bytecode',
                                      '-c', runner, str(propose_source),
                                      str(ROOT / 'scripts/propose_case_inputs.py'), str(audit),
                                      str(suites[identity]), str(root)],
                                     stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
                if run.returncode:
                    failures.append(run.stderr[-500:])
                captured = P.capture(root, [], P.audit_events(audit))
                runs = [{'mode': mode, 'exit': run.returncode, 'reads': 'r', 'trace': 't', 'observation': 'o',
                         'non_file': []} for mode in C.TRACED_RUNS]
                again = P.proposal(root, identity, runs, [captured])
                reported[identity] = (reasons, again, P.stale(root, again),
                                      sorted(set(again['files']) - set(old['files'])))
            helper_name = 'scripts/suites/support/compiled_sources.py'
            suite_of = {identity: str(suite.relative_to(root)) for identity, suite in suites.items()}
            row('stale-found: %r %r' % (failures, {i: (r[0], r[3]) for i, r in reported.items()}),
                not failures and sorted(i.split(':', 1)[1] for i in reported) == sorted(seven)
                and all('input_changed:' + suite_of[i] in r[0] for i, r in reported.items())
                and all(helper_name in r[1]['files'] and r[3] == [helper_name] and r[2] == []
                        for r in reported.values()))
            # Each proposal records the digest of every file it read.
            again = next(iter(reported.values()))[1]
            row('proposal-records-read-digests',
                set(again['proposal']['read_digests']) == set(again['files'])
                and all(v == P.file_digest(root / n) for n, v in again['proposal']['read_digests'].items()))
            row('legacy-declaration-stale', P.stale(root, {'files': ['a'], 'proposal': {}}) == ['no_recorded_inputs']
                and P.stale(root, {'files': ['a']}) == ['no_recorded_inputs'])

            # The report is complete only against the coordinator's own enumeration, by identity.
            inventory = [fixture_case('a', 'a_test.py'), fixture_case('b', 'b_test.py'),
                         fixture_case('u', 'unconfined_test.py')]
            leg = {'declaration': 'sha256:' + '0' * 64, 'entries': ['unconfined_test'], 'suites': ['unconfined_test']}
            confined = P.confined_cases(gate, inventory, leg)
            row('report-complete',
                [c['identity'] for c in confined] == [inventory[0]['identity'], inventory[1]['identity']]
                and P.complete([inventory[0]['identity']], confined) == ([inventory[1]['identity']], [])
                and P.complete([inventory[0]['identity'], inventory[1]['identity'], 'x:y'], confined) == ([], ['x:y'])
                and P.complete([c['identity'] for c in confined], confined) == ([], []))
            try:
                P.refuse_inside_gate({'VELDO_GATE_LEDGER_FD': '3'})
            except SystemExit as error:
                inside = 'refused inside a gate' in str(error)
            else:
                inside = False
            row('refused-inside-a-gate', inside and P.refuse_inside_gate({}) is None)

            # Parallel through the coordinator's admission: a ledger of two CPUs admits two runs of one
            # CPU each at once and never three. Two runs meet at a barrier, so a serial pool never gets
            # past it; the barrier's deadline is only a hang detector.
            capacity = {'cpu': 2, 'memory': 2 ** 34, 'manager': 1}
            resources = gate.SuiteResources({'suites': [{'file': 'a_test.py'}]})
            pool = P.Pool(gate, parallel=8, resources=resources,
                          admission=gate.Admission(P.LocalLedger(capacity), capacity, {'cpu': 0, 'memory': 0}))
            meeting = threading.Barrier(2, timeout=300)
            jobs = [('run-%d' % n, {'case': inventory[0], 'mode': 'baseline',
                                    'claim': {'cpu': 1, 'memory': 2 ** 30, 'source': 'fixture', 'keys': []}})
                    for n in range(6)]
            try:
                done = pool.map(jobs, lambda job: meeting.wait() is not None)
            except Exception as error:
                done = {'error': str(error)}
            row('parallel-admission: %r peak=%s' % (sorted(done)[:2], pool.peak),
                sorted(done) == sorted(n for n, _ in jobs) and pool.peak == 2 and not pool.admission.held
                and len([e for e in pool.admission.events]) == 6)

        # AC2: case_reuse qualifies only when every mechanical condition holds, each failure named.
        if leg_runs():
            root = top / 'conditions'; root.mkdir()
            names = ['passes', 'unreviewed', 'no-review', 'review-mismatch', 'trace-failed', 'baselines-differ',
                     'one-baseline', 'non-file', 'observation-differs', 'no-gate-observation', 'gate-entry',
                     'toolchain-unreviewed', 'sensitivity-unproved', 'no-rationale',
                     'review-outside', 'review-unbound']
            cases = [fixture_case(n, 'test.py', driver=gate.DRIVERS[1] if n == 'toolchain-unreviewed' else None)
                     for n in names]
            files = machinery()
            files['.veldo/subject.py'] = (0o644, b'value = 1\n')
            files['scripts/suites/test.py'] = (0o644, b'expect("fixture target", True)\n')
            files['scripts/verify.sh'] = (0o755, b'#!/usr/bin/env bash\n')
            document = {'schema': 'veldo.case-inputs/v1',
                        'toolchains': {gate.DRIVERS[0]: {'paths': ['/usr'], 'reviewed': True},
                                       gate.DRIVERS[1]: {'paths': ['/usr'], 'reviewed': False}},
                        'cases': {c['identity']: declared() for c in cases}}
            by = {c['name']: document['cases'][c['identity']] for c in cases}
            qualify(document, files)
            by['unreviewed']['reviewed'] = False
            by['gate-entry']['files'] = ['scripts/verify.sh']
            by['trace-failed']['proposal']['runs'][2]['exit'] = 1
            by['baselines-differ']['proposal']['runs'][1]['reads'] = 'other-reads'
            by['one-baseline']['proposal']['runs'] = by['one-baseline']['proposal']['runs'][1:]
            by['non-file']['proposal']['runs'][3]['non_file'] = ['user_bus']
            by['observation-differs']['proposal']['gate_observation'] = 'another'
            by['no-gate-observation']['proposal']['gate_observation'] = None
            by['no-rationale']['rationale'] = ' '
            by['review-mismatch']['rationale'] = 'Changed after review.'
            qualify(document, files, names={c['identity'] for c in cases if c['name'] not in (
                'review-mismatch', 'no-review')})
            # The mismatched record names the declaration as it was before the edit.
            record = json.loads(files['proof/VELDO-0217/reviews/fixture.json'][1])
            stale_copy = dict(by['review-mismatch'], rationale='Controlled file-only fixture.')
            record['cases'][gate.DRIVERS[0] + ':review-mismatch'] = {
                'declaration': C.declaration_digest(stale_copy),
                'traces': [r['trace'] for r in stale_copy['proposal']['runs']]}
            files['proof/VELDO-0217/reviews/fixture.json'] = (0o644, R.canonical(record))
            # Review F4: a matching record outside the protected reviews/ tree (one a later, unapproved
            # commit could add), and a declaration whose bound digest is not its record's bytes.
            files['notes/anywhere.json'] = files['proof/VELDO-0217/reviews/fixture.json']
            by['review-outside']['review'] = 'notes/anywhere.json'
            bind(document, files)
            by['review-unbound']['review_sha256'] = hashlib.sha256(b'another record').hexdigest()
            files[I.DECLARATIONS] = (0o644, R.canonical(document))
            cache = top / 'conditions-cache'

            def session():
                with patch.object(C.M, 'runtime_identity', side_effect=lambda paths, env: {'paths': paths}):
                    return C.Session(root, files, cases, 'head', {'worker_environment': gate.fixed_env('<home>')},
                                     cache_directory=cache)
            first = session()
            # VELDO-0226's proof stands for every key but one's: written where case_reuse reads it.
            (cache / 'sensitivity').mkdir(parents=True)
            for c in cases:
                if c['name'] != 'sensitivity-unproved':
                    key = first.case_digests[c['identity']]
                    (cache / 'sensitivity' / (key + '.json')).write_text(json.dumps(
                        {'schema': C.SENSITIVITY_SCHEMA, 'key': key}))
            current = session()
            bound = ('review-outside', 'review-unbound')
            record_reasons = {n: current.reasons.get(gate.DRIVERS[0] + ':' + n) for n in bound}
            reasons = {c['name']: current.reasons.get(c['identity']) for c in cases if c['name'] not in bound}
            keyed = sorted(c['name'] for c in cases if current.keys.get(c['identity']) and c['name'] not in bound)
            row('review-record-bound: %r' % record_reasons,
                record_reasons == {n: 'review_mismatch' for n in bound}
                and not any(current.keys.get(gate.DRIVERS[0] + ':' + n) for n in bound))
            expected = {'passes': 'miss', 'unreviewed': 'unreviewed_declaration', 'no-review': 'review_mismatch',
                        'review-mismatch': 'review_mismatch', 'trace-failed': 'trace_failed',
                        'baselines-differ': 'baseline_reads_differ', 'one-baseline': 'trace_failed',
                        'non-file': 'user_bus', 'observation-differs': 'observation_differs',
                        'no-gate-observation': 'observation_differs', 'gate-entry': 'starts_a_gate',
                        'toolchain-unreviewed': 'toolchain_unreviewed',
                        'sensitivity-unproved': 'sensitivity_unproved', 'no-rationale': 'no_rationale'}
            row('review-conditions: %r keyed=%r' % ({k: v for k, v in reasons.items() if v != expected[k]}, keyed),
                reasons == expected and keyed == ['passes']
                and {n for n in current.snapshots if n.split(':', 1)[1] not in bound} == {gate.DRIVERS[0] + ':passes'})
            policy = (ROOT / '.veldo/policy.yaml').read_text()
            row('reviewed-flag-protected', '{path: "' + I.DECLARATIONS + '", floor: high}' in policy)

        # AC3: a qualified case's key covers every file input it reads, each class of input by itself.
        if leg_runs():
            root = top / 'keys'; root.mkdir()
            a = fixture_case('a', 'sa_test.py')
            b = fixture_case('b', 'sb_test.py', module='other.py')
            c2 = fixture_case('c', 'sc_test.py', module='third.py', driver=gate.DRIVERS[1])
            cases = [a, b, c2]
            files = machinery()
            files['.veldo/subject.py'] = (0o644, b'value = 1\n')
            files['.veldo/other.py'] = (0o644, b'value = 1\n')
            files['.veldo/third.py'] = (0o644, b'value = 1\n')
            files['scripts/suites/sa_test.py'] = (0o644, b"exec((ROOT / 'scripts/suites/support/fixture_helper.py').read_text())\n")
            files['scripts/suites/sb_test.py'] = (0o644, b'expect("fixture target", True)\n')
            files['scripts/suites/sc_test.py'] = (0o644, b'expect("fixture target", True)\n')
            files['scripts/suites/pre_test.py'] = (0o644, b'PRE = 1\n')
            files['scripts/suites/support/fixture_helper.py'] = (0o644, b'HELPER = 1\n')
            files['scripts/suites/support/unloaded_helper.py'] = (0o644, b'UNUSED = 1\n')
            files[I.REQUIRES] = (0o644, json.dumps({'requires': {'sa_test': ['pre_test', 'sa_test'],
                                                                 'sb_test': ['sb_test'], 'sc_test': ['sc_test']}}).encode())
            files['shared-a'] = (0o644, b'declared by a\n')
            files['dir-a/one'] = (0o644, b'in a declared directory\n')
            files['unrelated'] = (0o644, b'declared by nobody\n')
            toolchain = top / 'toolchain'
            for driver_dir in ('first', 'second'):
                (toolchain / driver_dir).mkdir(parents=True)
                (toolchain / driver_dir / 'libfixture.so').write_bytes(b'toolchain bytes')
            document = {'schema': 'veldo.case-inputs/v1',
                        'toolchains': {gate.DRIVERS[0]: {'paths': [str(toolchain / 'first')], 'reviewed': True},
                                       gate.DRIVERS[1]: {'paths': [str(toolchain / 'second')], 'reviewed': True}},
                        'cases': {a['identity']: declared(['shared-a'], directories=['dir-a']),
                                  b['identity']: declared(), c2['identity']: declared()}}
            qualify(document, files)
            environment = gate.fixed_env('<home>')

            def keys(source=None, definitions=None, configuration=None, authority=None):
                with patch.object(C.M, 'required_runtime', return_value=[]), \
                     patch.object(C, 'SYSTEM_ROOTS', (*C.SYSTEM_ROOTS, str(toolchain))), \
                     patch.object(C, 'sensitivity_proved', return_value=True), \
                     patch.object(C.R.E, 'authority_identity',
                                  return_value=authority or C.R.E.authority_identity()):
                    current = C.Session(root, source or files, definitions or cases, 'head',
                                        configuration or {'worker_environment': environment},
                                        cache_directory=top / 'keys-cache')
                return current
            base = keys()
            missed = lambda current: sorted(n['name'] for n in cases
                                            if current.keys[n['identity']] != base.keys[n['identity']])

            def edited(name, body=None, mode=None):
                changed = dict(files)
                old_mode, old_body = changed.get(name, (0o644, b''))
                changed[name] = (old_mode if mode is None else mode, old_body + b'#edit\n' if body is None else body)
                return keys(changed)
            outcomes = {}
            outcomes['declared-bytes'] = missed(edited('shared-a'))
            outcomes['declared-mode'] = missed(edited('shared-a', body=files['shared-a'][1], mode=0o755))
            outcomes['declared-name'] = missed(keys(dict(files, **{'dir-a/two': (0o644, b'a new name\n')})))
            outcomes['registry-entry'] = missed(keys(definitions=[dict(a, new='value = -1'), b, c2]))
            outcomes['mandatory'] = missed(edited('scripts/mutation_reuse.py'))
            outcomes['prerequisite'] = missed(edited('scripts/suites/pre_test.py'))
            outcomes['helper'] = missed(edited('scripts/suites/support/fixture_helper.py'))
            changed_document = copy.deepcopy(document)
            changed_document['cases'][a['identity']]['rationale'] = 'A rationale the reviewer reworded.'
            changed_files = dict(files)
            qualify(changed_document, changed_files)
            outcomes['declaration'] = missed(keys(changed_files))
            (toolchain / 'first' / 'libfixture.so').write_bytes(b'toolchain bytes, rebuilt')
            outcomes['toolchain'] = missed(keys())
            (toolchain / 'first' / 'libfixture.so').write_bytes(b'toolchain bytes')
            outcomes['environment'] = missed(keys(configuration={'worker_environment': dict(environment, LANG='C')}))
            outcomes['authority'] = missed(keys(authority={'fixture': 'another authority'}))
            outcomes['undeclared'] = missed(edited('unrelated'))
            outcomes['unloaded-helper'] = missed(edited('scripts/suites/support/unloaded_helper.py'))
            expected = {'declared-bytes': ['a'], 'declared-mode': ['a'], 'declared-name': ['a'],
                        'registry-entry': ['a'], 'mandatory': ['a', 'b', 'c'], 'prerequisite': ['a'],
                        'helper': ['a'], 'declaration': ['a'], 'toolchain': ['a', 'b'],
                        'environment': ['a', 'b', 'c'], 'authority': ['a', 'b', 'c'], 'undeclared': [],
                        'unloaded-helper': []}
            row('key-covers-inputs: %r' % {k: v for k, v in outcomes.items() if v != expected[k]},
                outcomes == expected and all(base.keys[c['identity']] for c in cases)
                and 'scripts/suites/support/fixture_helper.py' in base.snapshots[a['identity']]
                and 'scripts/suites/pre_test.py' in base.snapshots[a['identity']]
                and 'scripts/suites/support/fixture_helper.py' not in base.snapshots[b['identity']])

        # AC4: non-file inputs are refused from the trace, on the proposal's traces and again on the
        # baseline, no-op and mutant traces of every run that would publish.
        if leg_runs():
            uid = os.getuid()
            traces = top / 'traces'; traces.mkdir()
            served = ('100 socket(AF_INET, SOCK_STREAM|SOCK_CLOEXEC, IPPROTO_IP) = 3<TCP:[1001]>\n'
                      '100 bind(3<TCP:[1001]>, {sa_family=AF_INET, sin_port=htons(0), sin_addr=inet_addr("127.0.0.1")}, 16) = 0\n'
                      '100 listen(3<TCP:[127.0.0.1:41000]>, 128) = 0\n'
                      '100 connect(5<TCP:[1002]>, {sa_family=AF_INET, sin_port=htons(41000), sin_addr=inet_addr("127.0.0.1")}, 16) = 0\n'
                      '100 bind(6<UNIX-STREAM:[1003]>, {sa_family=AF_UNIX, sun_path=@"v217-own"}, 11) = 0\n'
                      '100 connect(7<UNIX-STREAM:[1004]>, {sa_family=AF_UNIX, sun_path=@"v217-own"}, 11) = 0\n'
                      '100 connect(8<UNIX-STREAM:[1005]>, {sa_family=AF_UNIX, sun_path="%s/own.sock"}, 30) = 0\n'
                      '100 connect(9<UNIX-STREAM:[1006]>, {sa_family=AF_UNIX, sun_path="/var/run/nscd/socket"}, 110) = -1 ENOENT (No such file or directory)\n'
                      % (top / 'private'))
            fixtures = {
                'remote': '100 connect(4<TCP:[2001]>, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("192.0.2.10")}, 16) = -1 EINPROGRESS (Operation now in progress)\n',
                'bus': '100 connect(4<UNIX-STREAM:[2002]>, {sa_family=AF_UNIX, sun_path="/run/user/%d/bus"}, 21) = 0\n' % uid,
                'runtime-socket': '100 connect(4<UNIX-STREAM:[2003]>, {sa_family=AF_UNIX, sun_path="/run/user/%d/v217-service.sock"}, 40) = 0\n' % uid,
                'host-loopback': '100 connect(4<TCP:[2004]>, {sa_family=AF_INET, sin_port=htons(5432), sin_addr=inet_addr("127.0.0.1")}, 16) = -1 ECONNREFUSED (Connection refused)\n',
                'loopback-only': '',
            }
            classes = {}
            for name, extra in fixtures.items():
                path = traces / name
                path.write_text(served + extra + '100 +++ exited with 0 +++\n')
                classes[name] = sorted(T.non_file_inputs(path, (top / 'private',)))
            expected = {'remote': ['network_peer'], 'bus': ['user_bus'], 'runtime-socket': ['host_socket'],
                        'host-loopback': ['unbound_loopback'], 'loopback-only': []}
            # The coordinator's publish path: each fixture class shows only in the mutant trace of a run
            # that would publish (the bus also in a baseline); the loopback-only case publishes.
            root = top / 'stage'; root.mkdir()
            names = list(fixtures)
            cases = [fixture_case(n, 'test.py') for n in names]
            files = machinery()
            files['.veldo/subject.py'] = (0o644, b'value = 1\n')
            files['scripts/suites/test.py'] = (0o644, b'expect("fixture target", True)\n')
            document = {'schema': 'veldo.case-inputs/v1',
                        'toolchains': {gate.DRIVERS[0]: {'paths': ['/usr'], 'reviewed': True}},
                        'cases': {c['identity']: declared() for c in cases}}
            qualify(document, files)
            clean = traces / 'clean'
            clean.write_text(served + '100 +++ exited with 0 +++\n')

            def observation(ok):
                return {'count': 1, 'observations': [['fixture target', ok]], 'row_names': ['fixture target'],
                        'failed_rows': [] if ok else ['fixture target']}

            class Workers:
                def __init__(self, *args, **kwargs):
                    self.invocations = 0; self.driver_spans = {}; self.resources = None
                    self.parallel = 1; self.active = {}; self.outcomes = []; self.peak = 0
                    self.retargeted = {}; self.peak_memory = 0
                    self.validated_groups, self.blocked_groups = set(), set()

                def check(self): pass

                def cleanup(self, on_result=None): return []

                def retarget(self, name, seconds): self.retargeted[name] = seconds

                def run(self, jobs, directory, frozen, on_result=None):
                    results = {}
                    for name, job in jobs.items():
                        self.invocations += 1
                        self.outcomes.append(dict(name=name, driver=job['case']['driver'], mode=job['mode'],
                                                  elapsed=.1, returncode=0))
                        shown = traces / job['case']['name'] if job['mode'] == 'mutant' else clean
                        if job['case']['name'] == 'bus' and job['mode'] == 'baseline':
                            shown = traces / 'bus'
                        results[name] = {'elapsed': .1, 'non_file': sorted(T.non_file_inputs(shown, (top / 'private',))),
                                         'result': {'observation': observation(job['mode'] != 'mutant'),
                                                    'replacement_count': 1, 'old_digest': 'old', 'new_digest': 'new'}}
                        if on_result is not None:
                            on_result(name, results[name])
                    return results
            real_session = C.Session

            def construct(*args, **kwargs):
                return real_session(*args, **kwargs, cache_directory=top / 'stage-cache')
            with patch.object(gate, 'inventory', return_value=cases), \
                 patch.object(gate, 'read_inputs', return_value=files), \
                 patch.object(gate, 'git', return_value='head'), \
                 patch.object(gate, 'snapshot'), patch.object(gate, 'inputs_unchanged', return_value=True), \
                 patch.object(gate, 'Workers', Workers), patch.object(gate, 'load', return_value=C), \
                 patch.object(gate, 'record_case_times'), \
                 patch.object(gate.SuiteResources, 'from_root',
                              return_value=gate.SuiteResources({'suites': [{'file': 'test.py'}]})), \
                 patch.object(C.M, 'runtime_identity', side_effect=lambda paths, env: {'paths': paths}), \
                 patch.object(C, 'sensitivity_proved', return_value=True), \
                 patch.object(C, 'Session', side_effect=construct):
                receipt = gate.run_stage(root, root / '.git')
            reasons = {r['identity'].split(':', 1)[1]: r['reason'] for r in receipt.get('case_receipts', [])}
            published = sorted(p.stem for p in (top / 'stage-cache').glob('*.json')) if (top / 'stage-cache').exists() else []
            keyed = {r['identity'].split(':', 1)[1]: r['key'] for r in receipt.get('case_receipts', [])}
            row('non-file-refused: %r %r %s %s' % (classes, reasons, receipt.get('status'), receipt.get('detail', '')),
                classes == expected and receipt.get('status') == 'passed'
                and reasons == {'remote': 'network_peer', 'bus': 'user_bus', 'runtime-socket': 'host_socket',
                                'host-loopback': 'unbound_loopback', 'loopback-only': 'miss'}
                and published == [keyed['loopback-only']]
                and all(keyed[n] is None for n in names if n != 'loopback-only'))
            row('absent-socket-keyed', T.absent_sockets(clean, (top / 'private',)) == ['/var/run/nscd/socket'])
            launcher = traces / 'launcher'
            launcher.write_text('100 execve("/usr/bin/systemd-run", ["systemd-run", "--user", "true"], 0x0 /* 3 vars */) = 0\n'
                                '100 +++ exited with 0 +++\n')
            row('outside-process', sorted(T.non_file_inputs(launcher)) == ['outside_process'])

        # Review F2: a thread an ended process left waiting in accept, on a socket the traced tree
        # listened on, lost no file evidence and reached nobody: no class, and the trace is whole. A
        # pending connect still counts as an attempt, an accept on a socket the tree never listened on
        # is an input, and an ended thread inside a file call is still lost evidence.
        if leg_runs():
            boundary = '100 landlock_restrict_self(5, 0) = 0\n'
            waiting = (boundary +
                       '100 bind(3<TCP:[3001]>, {sa_family=AF_INET, sin_port=htons(0), sin_addr=inet_addr("127.0.0.1")}, 16) = 0\n'
                       '100 listen(3<TCP:[127.0.0.1:42001]>, 128) = 0\n'
                       '100 bind(4<UNIX-STREAM:[3002]>, {sa_family=AF_UNIX, sun_path=@"v217-accept"}, 14) = 0\n'
                       '100 listen(4<UNIX-STREAM:[3002,@"v217-accept"]>, 128) = 0\n'
                       '101 accept4(3<TCP:[127.0.0.1:42001]>,  <unfinished ...>\n'
                       '102 accept4(4<UNIX-STREAM:[3002,@"v217-accept"]>,  <unfinished ...>\n'
                       '100 exit_group(0) = ?\n'
                       '101 <... accept4 resumed> <unfinished ...>) = ?\n'
                       '102 <... accept4 resumed> <unfinished ...>) = ?\n'
                       '101 +++ exited with 0 +++\n102 +++ exited with 0 +++\n100 +++ exited with 0 +++\n')
            others = {
                'pending-connect': boundary + '101 connect(4<TCP:[3003]>, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("192.0.2.10")}, 16 <unfinished ...>\n'
                                   '100 exit_group(0) = ?\n101 +++ exited with 0 +++\n100 +++ exited with 0 +++\n',
                'foreign-accept': boundary + '100 accept4(5<TCP:[127.0.0.1:6000]>, {sa_family=AF_INET, sin_port=htons(50000), sin_addr=inet_addr("127.0.0.1")}, [16], SOCK_CLOEXEC) = 6<TCP:[127.0.0.1:6000->127.0.0.1:50000]>\n'
                                  '100 +++ exited with 0 +++\n',
            }
            pending_file = (boundary + '101 openat(AT_FDCWD, "/etc/hosts", O_RDONLY|O_CLOEXEC <unfinished ...>\n'
                            '100 exit_group(0) = ?\n101 +++ exited with 0 +++\n100 +++ exited with 0 +++\n')
            outcome = {}
            for name, text in {'waiting': waiting, **others, 'pending-file': pending_file}.items():
                path = traces / ('accept-' + name)
                path.write_text(text)
                try:
                    list(T.accesses(path, after_confinement=True))
                    outcome[name] = sorted(T.non_file_inputs(path, (top / 'private',), after_confinement=True))
                except ValueError as error:
                    outcome[name] = type(error).__name__ + ': ' + str(error)
            row('accept-pending: %r' % outcome,
                outcome == {'waiting': [], 'pending-connect': ['network_peer'], 'foreign-accept': ['unbound_loopback'],
                            'pending-file': 'IncompleteTrace: incomplete file-read trace'})

        # Review F1, F3 and F6: the coordinator's own Workers.finish judges each publishing run's
        # planted trace (no stand-in computes the classes): a network peer shown only in the mutant trace, an
        # absent socket the key does not record, one it does, and a clean case; then, in a stage of its
        # own, an incomplete trace beside a clean case. Each process is a real one that already ended.
        if leg_runs():
            boundary = '100 landlock_restrict_self(5, 0) = 0\n'
            ending = '100 +++ exited with 0 +++\n'
            planted = {
                'peer-mutant': '100 connect(4<TCP:[4001]>, {sa_family=AF_INET, sin_port=htons(443), sin_addr=inet_addr("192.0.2.10")}, 16) = -1 EINPROGRESS (Operation now in progress)\n',
                'absent-undeclared': '100 connect(4<UNIX-STREAM:[4002]>, {sa_family=AF_UNIX, sun_path="/run/v217-not-declared.sock"}, 30) = -1 ENOENT (No such file or directory)\n',
                'absent-declared': '100 connect(4<UNIX-STREAM:[4003]>, {sa_family=AF_UNIX, sun_path="/run/v217-declared-absent.sock"}, 33) = -1 ENOENT (No such file or directory)\n',
                'clean': '',
                'incomplete': '101 openat(AT_FDCWD, "/etc/hosts", O_RDONLY|O_CLOEXEC <unfinished ...>\n100 exit_group(0) = ?\n101 +++ killed by SIGKILL +++\n',
                'clean-beside': '',
            }

            def observation(ok):
                return {'count': 1, 'observations': [['fixture target', ok]], 'row_names': ['fixture target'],
                        'failed_rows': [] if ok else ['fixture target']}

            class TracedWorkers(gate.Workers):
                """The real Workers, its finish included; only the launch is replaced by a process
                that already ended, its stdout and the trace a traced worker would have left."""
                def run(self, jobs, directory, frozen, on_result=None):
                    jobs = {name: dict(job) for name, job in jobs.items()}
                    self.jobs.update(jobs)
                    results = {}
                    for name, job in jobs.items():
                        self.budgets[name] = job.get('budget_seconds', gate.WORKER_BUDGET)
                        home = directory / str(self.invocations)
                        home.mkdir()
                        self.homes[name] = home
                        if job.get('declared_case'):
                            self.owned_snapshots[name] = directory / 'cases' / str(self.invocations)
                            job.update(self.case_reuse.prepare(job['case'], self.owned_snapshots[name]))
                        shown = planted[job['case']['name']] if job['mode'] == 'mutant' else ''
                        (directory / ('trace-' + home.name)).write_text(boundary + shown + ending)
                        out, err = (open(directory / (home.name + '-' + f), 'w+b') for f in ('stdout', 'stderr'))
                        out.write(json.dumps({'observation': observation(job['mode'] != 'mutant'), 'replacement_count': 1,
                                              'old_digest': 'old', 'new_digest': 'new'}).encode())
                        self.resources.acquire(name, job)
                        self.ledgers[name] = directory / ('ownership-' + home.name + '.jsonl')
                        process = subprocess.Popen(['/bin/true'], start_new_session=True)
                        process.wait(timeout=300)
                        self.active[name] = (process, out, err, time.monotonic())
                        self.invocations += 1
                        self.driver_spans.setdefault(job['case']['driver'], [time.monotonic(), time.monotonic()])
                        results[name] = self.finish(name)
                        if on_result is not None:
                            on_result(name, results[name])
                    return results
            real_load, real_session = gate.load, C.Session

            def loader(path):
                return {'case_trace.py': T, 'case_reuse.py': C}.get(Path(path).name) or real_load(path)

            def traced_stage(label, names):
                root = top / label; root.mkdir()
                cache = top / (label + '-cache')
                cases = [fixture_case(n, 'test.py') for n in names]
                files = machinery()
                files['.veldo/subject.py'] = (0o644, b'value = 1\n')
                files['scripts/suites/test.py'] = (0o644, b'expect("fixture target", True)\n')
                document = {'schema': 'veldo.case-inputs/v1',
                            'toolchains': {gate.DRIVERS[0]: {'paths': ['/usr'], 'reviewed': True,
                                                             'absent': ['/run/v217-declared-absent.sock']}},
                            'cases': {c['identity']: declared() for c in cases}}
                qualify(document, files)
                with patch.object(gate, 'inventory', return_value=cases), \
                     patch.object(gate, 'read_inputs', return_value=files), \
                     patch.object(gate, 'git', return_value='head'), \
                     patch.object(gate, 'snapshot'), patch.object(gate, 'inputs_unchanged', return_value=True), \
                     patch.object(gate, 'Workers', TracedWorkers), patch.object(gate, 'load', side_effect=loader), \
                     patch.object(gate, 'record_case_times'), \
                     patch.object(gate.SuiteResources, 'from_root',
                                  return_value=gate.SuiteResources({'suites': [{'file': 'test.py'}]})), \
                     patch.object(C.M, 'runtime_identity', side_effect=lambda paths, env: {'paths': paths}), \
                     patch.object(C, 'sensitivity_proved', return_value=True), \
                     patch.object(C, 'Session', side_effect=lambda *a, **k: real_session(*a, **k, cache_directory=cache)):
                    receipt = gate.run_stage(root, root / '.git')
                reasons = {r['identity'].split(':', 1)[1]: r['reason'] for r in receipt.get('case_receipts', [])}
                keyed = {r['identity'].split(':', 1)[1]: r['key'] for r in receipt.get('case_receipts', [])}
                published = {p.stem for p in cache.glob('*.json')} if cache.exists() else set()
                return receipt, reasons, {n: bool(keyed.get(n)) and keyed[n] in published for n in names}
            receipt, reasons, published = traced_stage('traced-stage', ['peer-mutant', 'absent-undeclared',
                                                                        'absent-declared', 'clean'])
            seen = '%r %r %s %s' % (reasons, published, receipt.get('status'), receipt.get('detail', ''))
            passed = receipt.get('status') == 'passed' and published.get('clean') is True
            row('worker-trace-refused: ' + seen,
                passed and reasons.get('peer-mutant') == 'network_peer' and published.get('peer-mutant') is False)
            row('undeclared-absent-socket: ' + seen,
                passed and reasons.get('absent-undeclared') == 'undeclared_absent_socket'
                and published.get('absent-undeclared') is False
                and reasons.get('absent-declared') == 'miss' and published.get('absent-declared') is True)
            receipt, reasons, published = traced_stage('incomplete-stage', ['incomplete', 'clean-beside'])
            row('incomplete-trace-demoted: %r %r %s %s' % (reasons, published, receipt.get('status'), receipt.get('detail', '')),
                receipt.get('status') == 'passed' and reasons == {'incomplete': 'incomplete_trace', 'clean-beside': 'miss'}
                and published == {'incomplete': False, 'clean-beside': True})

        # Review F5: the gate observation a proposal records is the last fresh one of the state it
        # traced: the proposer takes it only from a passed receipt over exactly its own inputs, and
        # case_reuse refuses a declaration whose receipt is of another state, failed, or missing.
        if leg_runs():
            receipts = top / 'receipts'; receipts.mkdir()
            fresh = {'source': 'fresh', 'case': {'identity': 'd:case'}, 'baseline': {'count': 1}}
            for name, status, inputs in (('current', 'passed', 'inputs-now'), ('earlier', 'passed', 'inputs-before'),
                                         ('failed', 'failed', 'inputs-now')):
                (receipts / name).write_text(json.dumps({'status': status, 'input_digest': inputs, 'results': [fresh]}))
            taken = {name: P.gate_observations(receipts / name, 'inputs-now') for name in ('current', 'earlier', 'failed')}
            proposer = {name: (sorted(found), (binding or {}).get('input_digest')) for name, (found, binding) in taken.items()}
            document = {'schema': 'veldo.case-inputs/v1', 'toolchains': {},
                        'cases': {'d:' + n: declared() for n in ('current', 'earlier', 'failed', 'none')}}
            files = {}
            qualify(document, files)
            for name, receipt in (('earlier', {'status': 'passed', 'input_digest': 'inputs-before'}),
                                  ('failed', {'status': 'failed', 'input_digest': 'traced-inputs'}), ('none', None)):
                document['cases']['d:' + name]['proposal']['gate_receipt'] = receipt
            qualify(document, files)
            judged = {n: C.failed_condition(files, 'd:' + n, document['cases']['d:' + n])
                      for n in ('current', 'earlier', 'failed', 'none')}
            row('gate-observation-current: %r %r' % (proposer, judged),
                proposer == {'current': (['d:case'], 'inputs-now'), 'earlier': ([], None), 'failed': ([], None)}
                and judged == {'current': None, 'earlier': 'observation_not_current',
                               'failed': 'observation_not_current', 'none': 'observation_not_current'})

        # Review F4: the review records a reviewed declaration names are a protected path, as the
        # declarations are: writing one needs the owner's commit-bound approval (.veldo/policy.yaml).
        if leg_runs():
            import fnmatch
            import re
            patterns = re.findall(r'\{path: "([^"]+)", *floor: high\}', policy_source.read_text())
            record = 'proof/VELDO-0217/reviews/batch-1.json'
            covered = [p for p in patterns if fnmatch.fnmatch(record, p) or fnmatch.fnmatch(record, p.rstrip('*') + '*')]
            row('review-records-protected: %r' % covered, covered == ['proof/VELDO-0217/reviews/*'])


_v217_declarations()
