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
    P = as_module(propose_source, 'propose_case_inputs')
    C = as_module(reuse_source, 'case_reuse')
    T = as_module(trace_source, 'case_trace')
    gate = load('check_gate_mutations')
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
                'gate_observation': 'seen'})
            entry['review'] = 'proof/VELDO-0217/reviews/fixture.json'
            if names is None or name in names:
                record['cases'][name] = {'declaration': C.declaration_digest(entry),
                                         'traces': [r['trace'] for r in entry['proposal']['runs']]}
        files['proof/VELDO-0217/reviews/fixture.json'] = (0o644, R.canonical(record))
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
                     'toolchain-unreviewed', 'sensitivity-unproved', 'no-rationale']
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
            reasons = {c['name']: current.reasons.get(c['identity']) for c in cases}
            keyed = sorted(c['name'] for c in cases if current.keys.get(c['identity']))
            expected = {'passes': 'miss', 'unreviewed': 'unreviewed_declaration', 'no-review': 'review_mismatch',
                        'review-mismatch': 'review_mismatch', 'trace-failed': 'trace_failed',
                        'baselines-differ': 'baseline_reads_differ', 'one-baseline': 'trace_failed',
                        'non-file': 'user_bus', 'observation-differs': 'observation_differs',
                        'no-gate-observation': 'observation_differs', 'gate-entry': 'starts_a_gate',
                        'toolchain-unreviewed': 'toolchain_unreviewed',
                        'sensitivity-unproved': 'sensitivity_unproved', 'no-rationale': 'no_rationale'}
            row('review-conditions: %r keyed=%r' % ({k: v for k, v in reasons.items() if v != expected[k]}, keyed),
                reasons == expected and keyed == ['passes'] and set(current.snapshots) == {gate.DRIVERS[0] + ':passes'})
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


_v217_declarations()
