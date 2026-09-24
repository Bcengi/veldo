"""VELDO-0053: architecture failure handling at every eligibility entry, over real files and a real store.

Only shared ROOT and expect are consumed. One temporary Git repository is both the workspace the
entries read and the installed .veldo they run from (as in VELDO-0052's suite), so a registered
mutation of a production module reaches every entry that loads it. A second tree is a clone that
carries its own .veldo with a success-stub structural validator and a deleted, weakened or unaccepted
architecture; the installed Gate judges it. Real SQLite store, real files in every contract state
(permission denial by chmod under the running worker, a directory and a FIFO at the path), the
installed validator run as a real process, real VELDO-0036 reservation transactions and an observed
receiver. Launch counters stand in for the delegated build and review agents.
"""


def _v53_suite():
    import contextlib
    import hashlib
    import hmac
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
        'validate_checks.py': ROOT / ".veldo" / "validate_checks.py",
        'contract_loader.py': ROOT / ".veldo" / "contract_loader.py",
        'arch.py': ROOT / ".veldo" / "arch.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def sha(data):
        return 'sha256:' + hashlib.sha256(data).hexdigest()

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v53-', dir=fast) as directory:
        top = Path(directory)
        base = top / 'repo'
        mods = base / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        GP = load('v53_git', mods / 'git_process.py')
        EL = load('v53_eligibility', mods / 'control_eligibility.py')
        S = load('v53_store', mods / 'control_store.py')
        RES = load('v53_reservations', mods / 'control_reservations.py')
        RT = load('v53_runtime', mods / 'control_reservation_runtime.py')
        V = load('v53_validate', mods / 'validate.py')
        CLM = EL._organ('control_claim')
        DOMAIN, REPOSITORY, SID = 'domain-53', 'repository-53', 'VELDO-9301'
        db = top / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        key = os.urandom(32)

        def sign(message):
            return hmac.new(key, message, hashlib.sha256).hexdigest()

        serial = [0]
        # VELDO-0134: the store lets only its architecture operation write architecture:<repository>, so
        # the record reaches the Gate through that operation, registered here on the suite's own
        # connection with the suite's own transition (VELDO-0134's suite drives the real signed accept
        # command). Each record is a complete veldo.architecture_record/v1 carrying the state and digest
        # a row names; a row that names no digest leaves the field out, so the record-states rows face
        # schema-invalid records. An earlier store with no such operation takes the generic write.
        ARCHITECTURE_WRITE = getattr(S, 'ARCHITECTURE_OPERATION', 'upsert_entity')
        writer.command_registry[ARCHITECTURE_WRITE] = {
            'transition': lambda params, before: {params['entity_id']: {'kind': params['kind'], 'data': params['data']}},
            'writes': ('entities', 'journal', 'commands', 'nonces')}

        def architecture_record(identity, data):
            record = dict(schema='veldo.architecture_record/v1', repository_uuid=identity[len('architecture:'):],
                          state='accepted', contract_version=1,
                          source=dict(commit='0' * 40, path='.veldo/architecture.yaml'), accepted_by='owner',
                          command_id='c%d' % serial[0], superseded=[])
            record.update(data)
            return record

        def put(identity, kind, data):
            serial[0] += 1
            row = writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            operation = ARCHITECTURE_WRITE if identity.startswith('architecture:') else 'upsert_entity'
            if identity.startswith('architecture:'):
                data = architecture_record(identity, data)
            S.execute(writer, dict(command_id='c%d' % serial[0], principal='owner', operation=operation,
                                   nonce='n%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: row[0] if row else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)),
                      'authority', sign, 1)

        # Accepted authority records for ONE unit that every station accepts: the architecture is the
        # only thing each scenario below changes.
        put('project:p1', 'project', dict(name='floor'))
        put('authority:' + DOMAIN, 'authority', dict(state='active', generation=1))
        put('plan:PLAN-9301', 'plan', dict(status='ready', revision=1))
        put(SID, 'execution_unit', dict(state='CLAIMED', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + SID,
                                        requirements=[], eligible_holders=['worker-a'], plan='PLAN-9301', project='p1',
                                        depends_on=[], scope_digest='sha256:scope', revision=1, producer='builder-a',
                                        approvals_required=['owner']))
        put('backlog:' + SID, 'backlog_item', dict(state='ACTIVE', repository_uuid=REPOSITORY))
        put('admission:' + SID, 'admission', dict(unit=SID, state='accepted', scope_digest='sha256:scope'))
        put('approval:%s:owner' % SID, 'approval', dict(unit=SID, name='owner', state='granted', revision=1))
        put(CLM.claim_id(REPOSITORY, SID), 'claim', dict(unit_id=SID, holder='worker-a', generation=1,
                                                         state='owned', heartbeat_at=CLM.CL._now()))

        # The checkout: one ready planned spec with a placement in the fixture architecture's one area.
        VALID = ('schema: veldo.arch/v1\nid: ARCH-9301\ntitle: Fixture architecture\nstatus: draft\nversion: 1\n'
                 'areas:\n  - id: floor\n    title: Floor\n    includes: ["src/**", "specs/**"]\n')
        WEAKENED = VALID.replace('version: 1\n', 'version: 2\n') + '  - id: anything\n    title: Anything\n    includes: ["**"]\n'
        WRONG_FIELDS = ('schema: veldo.arch/v1\nid: ARCH-9301\ntitle: Fixture architecture\nstatus: draft\n'
                        'version: one\nareas: none\n')

        def spec_text(sid):
            return '\n'.join(['---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Architecture fixture ' + sid,
                              'status: ready', 'risk: low', 'owner: dmitry', 'lane: planned', 'plan: PLAN-9301',
                              'work: W1', 'plan_revision: 1', 'depends_on: []', 'placement: [floor]',
                              'footprint: ["src/**"]', '---', '', 'Fixture.', ''])

        for tree in (base, top / 'clone'):
            (tree / 'specs').mkdir(parents=True)
            (tree / 'plans').mkdir()
            (tree / 'specs' / (SID + '-fixture.md')).write_text(spec_text(SID))
            (tree / 'plans' / 'PLAN-9301-fixture.md').write_text('\n'.join(
                ['---', 'schema: veldo.plan/v1', 'id: PLAN-9301', 'title: Architecture fixture plan', 'status: ready',
                 'revision: 1', 'work:', '  - item: W1', '    spec: ' + SID, '    order: 1', '---', '', 'Plan.', '']))
        spec_path = base / 'specs' / (SID + '-fixture.md')
        plan_path = str(base / 'plans' / 'PLAN-9301-fixture.md')
        originals = {p: p.read_bytes() for p in list((base / 'specs').glob('*.md')) + list((top / 'clone' / 'specs').glob('*.md'))}

        def restore():
            for p, body in originals.items():
                p.write_bytes(body)

        contract, policy = mods / 'architecture.yaml', mods / 'policy.yaml'
        GP.run(['git', '-C', str(base), 'init', '-q'], check=True, capture_output=True)
        GP.run(['git', '-C', str(base), 'add', '-A'], check=True, capture_output=True)
        GP.run(['git', '-C', str(base), 'commit', '-q', '-m', 'architecture fixture'], check=True, capture_output=True,
               identity=('Fixture', 'fixture@example.invalid'))

        def trunk():
            refs = GP.run(['git', '-C', str(base), 'for-each-ref', '--format=%(refname) %(objectname)'], check=True,
                          capture_output=True, text=True).stdout
            head = GP.run(['git', '-C', str(base), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout
            return head + refs

        def clear(target):
            if os.path.lexists(str(target)):
                if os.path.isdir(str(target)) and not os.path.islink(str(target)):
                    shutil.rmtree(str(target))
                else:
                    os.unlink(str(target))

        # Every contract state a real file can be in, with the policy flag in force. `expect` is the
        # outcome the installed loader and policy owe it, written out here, not read back from them.
        STATES = {
            'valid': ('optional', 'valid', True),
            'optional_absent': ('optional', 'optional_absence', True),
            'required_absent': ('required', 'required_absence', False),
            'unreadable': ('optional', 'unreadable', False),
            'malformed_not_mapping': ('optional', 'parse_failure', False),
            'malformed_outside_subset': ('optional', 'parse_failure', False),
            'wrong_type_directory': ('optional', 'unreadable', False),
            'wrong_type_fifo': ('optional', 'unreadable', False),
            'wrong_type_fields': ('optional', 'invalid_structure', False),
        }
        denied = {}

        def arrange(state, tree=base, text=None):
            target, flag = tree / '.veldo' / 'architecture.yaml', tree / '.veldo' / 'policy.yaml'
            clear(target)
            flag.write_text('architecture_contract: %s\n' % STATES[state][0])
            if text is not None:
                target.write_text(text)
            elif state in ('valid', 'unreadable'):
                target.write_text(VALID)
            elif state == 'malformed_not_mapping':
                target.write_text('- floor\n- fleet\n')
            elif state == 'malformed_outside_subset':
                target.write_text('schema: veldo.arch/v1\nareas: [unclosed\n')
            elif state == 'wrong_type_directory':
                target.mkdir()
            elif state == 'wrong_type_fifo':
                os.mkfifo(str(target))
            elif state == 'wrong_type_fields':
                target.write_text(WRONG_FIELDS)
            if state == 'unreadable':
                # ACTUAL permission denial under the identity running this suite, never a mocked error.
                os.chmod(str(target), 0)
                try:
                    with open(str(target), 'rb'):
                        denied[state] = False
                except PermissionError:
                    denied[state] = True
            return target

        def bytes_at(target):
            return target.read_bytes() if os.path.isfile(str(target)) and os.access(str(target), os.R_OK) else None

        reader = S.open_store(str(db), mode='r')
        observed = {}
        CTX = {'holder': 'worker-a', 'reviewer': 'reviewer-b'}
        CODES = {'required_absence': 'missing_evidence:architecture/required_absence',
                 'unreadable': 'invalid_input:architecture/unreadable',
                 'parse_failure': 'invalid_input:architecture/parse_failure',
                 'invalid_structure': 'invalid_input:architecture/invalid_structure',
                 'unaccepted_artifact': 'missing_authority:architecture/unaccepted_artifact'}

        def stations(gate):
            return {st: gate.decide(st, SID, context=CTX) for st in EL.FLOOR_STATIONS}

        def outcome(decisions, code):
            """True when every station said exactly `code` (None: every station accepted)."""
            wanted = [] if code is None else [code]
            return all(d['refusals'] == wanted and d['eligible'] == (code is None) for d in decisions.values())

        emitted, raised, regions = set(), [], []

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0053 ' + label, condition)

        @contextlib.contextmanager
        def region(*labels):
            regions.append(labels[0])
            try:
                yield
            except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
                raised.append((labels[0], repr(error)))
                for label in labels:
                    if label not in emitted:
                        check(label, False)

        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        # The code every judgement must come from: the installed engine's files, by module name, resolved path
        # and digest. The five validator roles are always among what a snapshot runs; whatever else it runs is
        # recorded too.
        LABELS = {'validate': 'entry_point', 'validate_checks': 'entry', 'contract_loader': 'loader',
                  'arch': 'validator', 'yamlish': 'parser'}
        installed = {p_.name[:-3]: os.path.realpath(str(p_)) for p_ in mods.glob('*.py')}
        installed_digests = {module: sha(Path(path).read_bytes()) for module, path in installed.items()}

        def pristine(recorded, table=None):
            # Every validator role's module is recorded and every recorded digest is the one in `table`.
            table = installed_digests if table is None else table
            return set(LABELS) <= set(recorded) and all(table.get(k) == d for k, d in recorded.items())

        def by_module(validator):
            # A decision's recorded identity as {module: digest}, read from each entry's own module field (its
            # key when it names none), so what is compared is which module ran, whatever the record is keyed by.
            return {(v.get('module') or k): v.get('digest') for k, v in (validator or {}).items()}

        # Separately installed engines for the snapshot rows: a copy of the installed engine (or a per-file link
        # farm into `links_into`), and a Gate of it judging every station.
        real_read = Path.read_bytes

        @contextlib.contextmanager
        def reading(writer, *modules):
            # A writer around the snapshot's one read of each engine file: the eligibility module's own reader
            # of engine files where it has one, and Path.read_bytes (which an older snapshot read with).
            saved = [(m_, m_.__dict__.get('_read_engine_file')) for m_ in modules]
            for m_, own in saved:
                if own is not None:
                    m_._read_engine_file = lambda path_: writer(Path(path_))
            Path.read_bytes = writer
            try:
                yield
            finally:
                Path.read_bytes = real_read
                for m_, own in saved:
                    if own is not None:
                        m_._read_engine_file = own

        def engine_copy(where, links_into=None, leave_out=()):
            where.mkdir(parents=True)
            for source in sorted(mods.glob('*.py')):
                if source.name in leave_out:
                    continue
                if links_into is not None and source.name != 'control_eligibility.py':
                    shutil.copyfile(source, links_into / source.name)
                    (where / source.name).symlink_to(links_into / source.name)
                else:
                    shutil.copyfile(source, where / source.name)
            return where

        def judge(engine, tag, writer=None, events=None):
            # One separately installed engine's Gate at every station; `writer` wraps its one read of each file.
            engine_el = load('v53_%s_eligibility' % tag, engine / 'control_eligibility.py')
            judging = engine_el.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base),
                                     observe=(events.append if events is not None else None))
            with (reading(writer, engine_el) if writer is not None else contextlib.nullcontext()):
                decided = stations(judging)
            arch_file = None
            try:
                arch_file = judging._architecture_validator().arch.__file__
            except Exception:  # noqa: BLE001 - a snapshot that could not load has no module to name
                pass
            recorded = [by_module((d.get('architecture') or {}).get('validator')).get('arch') for d in decided.values()]
            return decided, recorded, arch_file

        with region('architecture/store-only-refuses'):
            # A Gate built with no workspace (the constructor's default) cannot look at any file, so it
            # never passes the architecture: here the authority has no record, and the repository's policy
            # requires a contract that is malformed, which only a workspace Gate could see.
            arrange('malformed_not_mapping')
            policy.write_text('architecture_contract: required\n')
            store_only = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY)
            blind = stations(store_only)
            seen = stations(gate)
            clear(contract)
            observed['store_only'] = {'store_only': sorted({r for d in blind.values() for r in d['refusals']}),
                                      'workspace': sorted({r for d in seen.values() for r in d['refusals']})}
            check('architecture/store-only-refuses',
                   outcome(blind, 'missing_evidence:architecture/workspace') and outcome(seen, CODES['parse_failure'])
                   and all((d.get('architecture') or {}).get('basis') == 'store_only' for d in blind.values()))

        # --- AC1: valid, absent and invalid contracts at every loader/ready entry -------------------------
        with region('architecture/state-kinds', 'architecture/ready-refusal'):
            kinds, processes, ready, policy_rows = {}, {}, {}, {}
            for state, (flag, kind, proceeds) in STATES.items():
                target = arrange(state)
                kinds[state] = V.load_contract_state(str(base)).kind
                # The installed structural validator as a real process, for every present state.
                if os.path.lexists(str(target)):
                    run = subprocess.run([sys.executable, '-B', str(mods / 'validate.py'), 'arch', str(target)],
                                         capture_output=True, text=True, timeout=60)
                    processes[state] = run.returncode
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    ready[state] = V.check_ready(str(spec_path), repo_root=str(base))
                policy_rows[state] = stations(gate)
                clear(target)
            observed['state_kinds'] = kinds
            observed['validator_process_exit'] = processes
            observed['permission_denied'] = denied
            check('architecture/state-kinds',
                   kinds == {s: k for s, (_, k, _) in STATES.items()} and denied == {'unreadable': True}
                   and processes == {s: (0 if s == 'valid' else 1) for s in STATES if s not in ('optional_absent', 'required_absent')})

            # The same states under the authority's accepted record: the record's digest names the bytes at
            # the path (the valid contract's when nothing readable is there), so absence is required.
            accepted_rows = {}
            for state in STATES:
                target = arrange(state)
                body = bytes_at(target)
                put('architecture:' + REPOSITORY, 'architecture_contract',
                    dict(state='accepted', digest=sha(body if body is not None else VALID.encode())))
                accepted_rows[state] = stations(gate)
                clear(target)
            ready_ok = True
            for state, (_, kind, proceeds) in STATES.items():
                ready_ok &= (ready[state] == 0) == proceeds
                ready_ok &= outcome(policy_rows[state], None if proceeds else CODES[kind])
                wanted = None if state == 'valid' else CODES['required_absence' if kind == 'optional_absence' else kind]
                ready_ok &= outcome(accepted_rows[state], wanted)
            observed['ready_errors'] = ready
            observed['station_refusals'] = {
                basis: {state: sorted({r for d in rows.values() for r in d['refusals']}) for state, rows in table.items()}
                for basis, table in (('policy', policy_rows), ('accepted', accepted_rows))}
            check('architecture/ready-refusal', ready_ok)

        # --- AC2: invalid or required-missing accepted architecture blocks every enabled entry ------------
        FR = load('v53_frontier', mods / 'frontier.py')
        WK = load('v53_work', mods / 'work.py')
        PL = load('v53_plan', mods / 'plan.py')
        EX = load('v53_executor', mods / 'executor.py')
        DSP = load('v53_dispatch', mods / 'dispatch.py')
        claims = top / 'claims'
        receiver = []
        observer = S.open_store(str(db), mode='r')

        def launcher(adapter):
            def launch(invocation, configuration):
                committed = observer.execute('SELECT 1 FROM entities WHERE id=?',
                                             (RES.entity('invocation', [DOMAIN, invocation]),)).fetchone() is not None
                receiver.append((adapter, invocation, committed))
            return launch

        def authorize(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            return bool(row) and json.loads(row[0]).get('roles') == ['reservation_service']

        put('runner', 'membership', dict(roles=['reservation_service']))
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=authorize, signer='authority', sign=sign)
        guards = {a: RT.InvocationGuard(reservations, a, launcher(a), lambda *_: None) for a in RT.ADAPTERS}
        CONFIG = {'mcp_servers': ['configured'], 'tools': ['configured-tool']}
        clock = [100.0]

        def tick():
            clock[0] += 1
            return clock[0]

        CEILING = dict(capacity=100, invocations=200, wall_seconds=100000)
        for scope, subject in zip(RES.SCOPES, ('acct-floor', 'p1', SID)):
            reservations.configure('ceiling-%s-%s' % (scope, subject), scope, subject, CEILING, now=tick())
        reservations.reserve_worker('slot-direct-call', 'dispatch-direct-call', 'acct-floor', 'p1', SID, now=tick())

        class Hooks(EX.LoopSteps):
            reviewer_identity = 'reviewer-b'

            def __init__(self, during_build=None):
                self.builds, self.reviews, self.root = [], [], str(base)
                self.during_build = during_build

            def resolve(self, sid):
                return {'id': sid, 'status': FR.current_status(sid, str(base)), 'plan': 'PLAN-9301', 'work': 'W1'}

            def run_check(self, spec):
                return True, 'checked'

            def build(self, spec, calls=None):
                self.builds.append(spec['id'])
                if calls is not None:
                    calls.invoke('claude_code', 'initial', 'build-%d-%s' % (tick(), spec['id']), 10, CONFIG, now=tick())
                if self.during_build:
                    self.during_build()
                return {'ok': True, 'commit': 'c', 'evidence': {}}

            def gate(self):
                return {'green': True, 'detail': 'green'}

            def assemble_proof(self, spec, build):
                return {'criteria': []}

            def validate_proof(self, proof):
                return True, 0

            def emit(self, *args, **kwargs):
                return None

            def review(self, spec, proof, calls=None):
                self.reviews.append(spec['id'])
                if calls is not None:
                    calls.invoke('codex', 'initial', 'exec-review-%d' % tick(), 10, CONFIG, now=tick())
                return {'verdict': 'pass'}

            def merge_ready(self, spec, proof, verdict):
                return True, None

            def approve(self, spec, info):
                return {'decision': 'approved'}

        class Reviewer(DSP.Reviewer):
            identity = 'reviewer-b'

            def __init__(self):
                self.reviews = []

            def review(self, spec, unit, calls=None):
                self.reviews.append(spec['id'])
                if calls is not None:
                    calls.invoke('codex', 'initial', 'review-%d' % tick(), 10, CONFIG, now=tick())
                return {'verdict': 'pass', 'findings': []}

        class Lander:
            def __init__(self):
                self.lands = []

            def land(self, unit):
                self.lands.append(unit['spec'])
                return {'ok': True}

        class Counter(WK.Dispatcher):
            def __init__(self):
                self.units = []

            def dispatch(self, unit):
                self.units.append(unit['spec'])
                return {'ok': False}

        def observe_effect(fn):
            try:
                return ('ok', fn())
            except Exception as error:  # noqa: BLE001 - recorded, then asserted
                name = getattr(error, 'reason', None) or getattr(error, 'code', None) or str(error)
                return ('raised', '%s:%s' % (type(error).__name__, name))

        calls = EL.StationCalls(gate, guards, account='acct-floor', clock=tick)
        HOLDER = {'holder': 'worker-a'}

        def entry_drivers(condition):
            """One driver per shared registration: (what it launched, the refusal text it reported)."""
            restore()

            def frontier():
                offers = FR.claimable(repo_root=str(base), claims_root=str(claims), eligibility=gate)
                return [u['spec'] for u in offers], ''

            def work():
                counter = Counter()
                WK.WorkLoop('worker-a', [], counter, repo_root=str(base), claims_root=str(claims), eligibility=gate).run()
                return list(counter.units), ''

            def plan():
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = PL.cmd_run_check(plan_path, SID, eligibility=gate)
                return ([SID] if rc == 0 else []), out.getvalue()

            def executor(station):
                def run():
                    hooks = Hooks()
                    got = EX.Executor(hooks, eligibility=gate, calls=calls, station=station, context=HOLDER).run(
                        SID, stop_after='proof')
                    return list(hooks.builds), got.get('reason') or ''
                return run

            def executor_review():
                # The review launch follows a build, so the build starts against the accepted valid
                # contract and the architecture turns invalid (or goes missing while required) during it:
                # the review station is the first to face it. Its build is counted by the caller.
                put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('valid')))
                flips = {'invalid': lambda: contract.write_text(WRONG_FIELDS), 'missing': lambda: clear(contract)}
                hooks = Hooks(during_build=flips.get(condition))
                got = EX.Executor(hooks, eligibility=gate, calls=calls, context=HOLDER).run(SID)
                put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset(condition)))
                review_builds[condition] = list(hooks.builds)
                return list(hooks.reviews), got.get('reason') or ''

            def executor_calls():
                # The provider_request boundary a direct execution asks before it enters its builder.
                return executor('direct_execution')()

            def dispatch_build():
                hooks = Hooks()
                disp = DSP.Dispatcher(repo_root=str(base), hooks=hooks, eligibility=gate, calls=calls, worker_id='worker-a')
                got = disp.dispatch(dict(kind='build', spec=SID, holder='worker-a'))
                restore()
                return list(hooks.builds), got.get('reason') or ''

            def dispatch_review():
                reviewer, lander = Reviewer(), Lander()
                disp = DSP.Dispatcher(repo_root=str(base), reviewer=reviewer, lander=lander, eligibility=gate,
                                      calls=calls, worker_id='worker-a')
                got = disp.dispatch(dict(kind='review', spec=SID, holder='worker-a'))
                restore()
                return list(reviewer.reviews), got.get('reason') or ''

            def publication():
                lander = Lander()
                disp = DSP.Dispatcher(repo_root=str(base), lander=lander, eligibility=gate, calls=calls, worker_id='worker-a')
                got = disp._land(dict(kind='review', spec=SID, holder='worker-a'))
                return list(lander.lands), got.get('reason') or ''

            def invoke():
                before = len(receiver)
                handle = calls.handle('build', SID, 'dispatch-direct-call', context=HOLDER, ticket=None)
                got = observe_effect(lambda: handle.invoke('claude_code', 'initial', 'direct-%d' % tick(), 10, CONFIG,
                                                           now=tick()))
                return [SID for _, i, _ in receiver[before:] if i.startswith('direct-')], '' if got[0] == 'ok' else got[1]

            return {
                ('frontier.py', 'claimable._add', 'selection'): frontier,
                ('work.py', 'WorkLoop._claim_next', 'claim'): work,
                ('plan.py', 'cmd_run_check', 'direct_execution'): plan,
                ('executor.py', 'Executor._decide', 'direct_execution'): executor('direct_execution'),
                ('executor.py', 'Executor._decide', 'build'): executor('build'),
                ('executor.py', 'Executor._decide', 'review'): executor_review,
                ('executor.py', 'Executor._decide_calls', 'provider_request'): executor_calls,
                ('dispatch.py', 'Dispatcher._dispatch_build', 'build'): dispatch_build,
                ('dispatch.py', 'Dispatcher._dispatch_review', 'review'): dispatch_review,
                ('dispatch.py', 'Dispatcher._land', 'publication'): publication,
                ('control_eligibility.py', 'CallHandle.invoke', 'provider_request'): invoke,
            }

        def reset(condition):
            """Invalid: the accepted bytes are present and structurally invalid. Missing: the accepted
            contract is absent while the workspace's own policy says optional. Valid: the control."""
            text = {'invalid': WRONG_FIELDS, 'missing': VALID, 'valid': VALID}[condition]
            arrange('optional_absent')
            if condition != 'missing':
                contract.write_text(text)
            return sha(text.encode())

        EXEC_REVIEW = ('executor.py', 'Executor._decide', 'review')
        review_builds = {}

        def snapshot():
            return dict(trunk=trunk(), ledger=len(ledger), receiver=len(receiver),
                        opened=sum(o.get('operation') == 'open_dispatch' for o in calls.observations),
                        claims=writer.execute("SELECT id, version FROM entities WHERE kind='claim' ORDER BY id").fetchall())

        with region('architecture/registrations', 'architecture/entries-blocked', 'architecture/forbidden-review-launch'):
            drivers = entry_drivers('valid')
            registered = set(EL.REGISTRATIONS)
            check('architecture/registrations',
                   set(drivers) == registered
                   and all(EL.ARCHITECTURE_PREDICATE in EL.STATION_PREDICATES[s] for _, _, s in registered))
            ledger, real_claim = [], WK.CL.claim

            def spy_claim(sid, *args, **kwargs):
                ledger.append(sid)
                return real_claim(sid, *args, **kwargs)

            WK.CL.claim = spy_claim
            ran = {}
            try:
                for condition in ('valid', 'invalid', 'missing'):
                    put('architecture:' + REPOSITORY, 'architecture_contract',
                        dict(state='accepted', digest=reset(condition)))
                    drivers = entry_drivers(condition)
                    before = snapshot()
                    # The executor's review registration runs last and apart: it needs its build first.
                    effects = {reg: observe_effect(fn) for reg, fn in drivers.items() if reg != EXEC_REVIEW}
                    after = snapshot()
                    effects[EXEC_REVIEW] = observe_effect(drivers[EXEC_REVIEW])
                    ran[condition] = (effects, before, after, trunk())
            finally:
                WK.CL.claim = real_claim
                restore()
                reset('valid')
            want = {'invalid': CODES['invalid_structure'], 'missing': CODES['required_absence']}
            valid_effects = ran['valid'][0]
            blocked_ok = all(r[0] == 'ok' and r[1][0] == [SID] for r in valid_effects.values())
            blocked_ok &= review_builds.get('valid') == [SID]
            for condition, code in want.items():
                effects, before, after, final = ran[condition]
                blocked_ok &= all(r[0] == 'ok' and r[1][0] == [] for r in effects.values())
                # Every refusal an entry reports names the architecture, except the frontier and the work
                # loop, which offer and claim nothing and have nothing to report.
                blocked_ok &= all(code in r[1][1] for reg, r in effects.items() if reg[0] not in ('frontier.py', 'work.py'))
                # Zero claims, zero launches, zero worker slots and the same trunk, across every entry.
                blocked_ok &= before == after and final == before['trunk']
                # The executor's review registration: its build ran against the valid contract, nothing else.
                blocked_ok &= review_builds.get(condition) == [SID]
            observed['entries'] = {condition: {'%s %s %s' % reg: (list(r[1]) if r[0] == 'ok' else list(r))
                                               for reg, r in sorted(effects.items())}
                                   for condition, (effects, _, _, _) in ran.items()}
            observed['entries_unchanged'] = {c: ran[c][1] == ran[c][2] and ran[c][3] == ran[c][1]['trunk'] for c in want}
            observed['executor_review_builds'] = review_builds
            check('architecture/entries-blocked', blocked_ok)
            # Direct review, the dispatcher's and the executor's: no reviewer is ever launched.
            review_regs = sorted(r for r in registered if r[2] == 'review')
            review_ok = len(review_regs) == 2 and all(ran['valid'][0][reg][1][0] == [SID] for reg in review_regs)
            for condition, code in want.items():
                review_ok &= all(ran[condition][0][reg][0] == 'ok' and ran[condition][0][reg][1][0] == []
                                 and code in ran[condition][0][reg][1][1] for reg in review_regs)
            check('architecture/forbidden-review-launch', review_ok)

        # --- AC3: the installed validator and the accepted artifact, whatever the clone carries -----------
        with region('architecture/substitution'):
            clone = top / 'clone'
            (clone / '.veldo').mkdir()
            for source in sorted(mods.glob('*.py')):
                shutil.copyfile(source, clone / '.veldo' / source.name)
            marker = clone / '.veldo' / 'STUB_RAN'
            # The clone's structural validator is a success stub that says so when it is loaded.
            (clone / '.veldo' / 'arch.py').write_text(
                'from pathlib import Path as _StubPath\n'
                "_StubPath(%r).write_text('the clone validator ran\\n')\n" % str(marker)
                + (mods / 'arch.py').read_text()
                + '\n\ndef validate_contract(data, root, contract_path, fail):\n    return 0\n')
            gate_c = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(clone))
            calls_c = EL.StationCalls(gate_c, guards, account='acct-floor', clock=tick)
            cases = {
                # (what the clone carries, the digest the authority accepted, the refusal owed)
                'deleted': (None, sha(VALID.encode()), CODES['required_absence']),
                'weakened': (WEAKENED, sha(VALID.encode()), CODES['unaccepted_artifact']),
                'accepted_invalid': (WRONG_FIELDS, sha(WRONG_FIELDS.encode()), CODES['invalid_structure']),
                'accepted_valid': (VALID, sha(VALID.encode()), None),
            }
            substitution_ok, identities = True, {}
            for name, (text, digest, code) in cases.items():
                arrange('optional_absent', tree=clone, text=text)
                put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=digest))
                decisions = stations(gate_c)
                reviewer, lander = Reviewer(), Lander()
                disp = DSP.Dispatcher(repo_root=str(clone), reviewer=reviewer, lander=lander, eligibility=gate_c,
                                      calls=calls_c, worker_id='worker-a')
                got = observe_effect(lambda: disp.dispatch(dict(kind='review', spec=SID, holder='worker-a')))
                restore()
                found = decisions['review'].get('architecture') or {}
                validator = found.get('validator') or {}
                artifact = found.get('artifact') or {}
                present = text.encode() if text is not None else None
                substitution_ok &= outcome(decisions, code)
                substitution_ok &= reviewer.reviews == ([] if code else [SID]) and got[0] == 'ok'
                substitution_ok &= all(v.get('path') == installed.get(v.get('module') or r) for r, v in validator.items())
                substitution_ok &= pristine(by_module(validator))
                substitution_ok &= artifact.get('path') == str(clone / '.veldo' / 'architecture.yaml')
                substitution_ok &= artifact.get('digest') == (sha(present) if present is not None else None)
                substitution_ok &= found.get('basis') == 'accepted' and (found.get('accepted') or {}).get('digest') == digest
                identities[name] = {'refusals': decisions['review']['refusals'], 'reviews': list(reviewer.reviews),
                                    'artifact': dict(artifact, path='clone:.veldo/architecture.yaml'),
                                    'validator': {m: {'path': 'installed:.veldo/' + Path(v['path']).name,
                                                      'digest': v['digest']} for m, v in validator.items()}}
            substitution_ok &= not marker.exists()
            observed['substitution'] = identities
            observed['clone_validator_ran'] = marker.exists()
            check('architecture/substitution', substitution_ok)

        with region('architecture/record-states'):
            # The record itself: one not in the accepted state, or naming no digest, is not an acceptance;
            # a store-only Gate cannot look at the file an accepted record names.
            reset('valid')
            states = {}
            for record in (dict(state='withdrawn', digest=sha(VALID.encode())), dict(state='accepted'),
                           dict(state='accepted', digest='md5:nothing')):
                put('architecture:' + REPOSITORY, 'architecture_contract', record)
                states[json.dumps(record, sort_keys=True)] = outcome(stations(gate), 'missing_authority:architecture')
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=sha(VALID.encode())))
            states['store_only'] = outcome(stations(EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY)),
                                           'missing_evidence:architecture/workspace')
            states['accepted'] = outcome(stations(gate), None)
            observed['record_states'] = states
            check('architecture/record-states', all(states.values()) and len(states) == 5)

        with region('architecture/public-seam'):
            # The Gate judges only through validate.py's PUBLIC entry_contract: an installed copy whose
            # validate.py wraps that name with a counter sees every judgement of a Gate loaded from it.
            spied = top / 'spied' / '.veldo'
            spied.mkdir(parents=True)
            for source in sorted(mods.glob('*.py')):
                shutil.copyfile(source, spied / source.name)
            log = top / 'spied-entry.log'
            with open(str(spied / 'validate.py'), 'a') as handle:
                handle.write('\n\n_veldo_real_entry = globals().get("entry_contract") or _VC.entry_contract\n\n\n'
                             'def entry_contract(*args, **kwargs):\n'
                             '    with open(%r, "a") as _log:\n'
                             '        _log.write("entry\\n")\n'
                             '    return _veldo_real_entry(*args, **kwargs)\n' % str(log))
            EL_spied = load('v53_spied_eligibility', spied / 'control_eligibility.py')
            reset('valid')
            spied_gate = EL_spied.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
            through = stations(spied_gate)
            calls_seen = log.read_text().count('entry') if log.exists() else 0
            observed['public_seam'] = {'judgements': len(through), 'through_public_entry': calls_seen,
                                       'refusals': sorted({r for d in through.values() for r in d['refusals']})}
            check('architecture/public-seam', outcome(through, None) and calls_seen == len(through) == len(EL.FLOOR_STATIONS))

        with region('architecture/identity-is-what-ran'):
            # R50 identity: the validator is loaded ONCE, from one read of its bytes, and every decision
            # records THAT snapshot. The installed loader and structural validator are then replaced on
            # disk (the loader by other bytes, the validator by one that passes everything): the same Gate keeps judging with the code it loaded
            # (arch.py included, never re-executed per call) and keeps recording the digests of the bytes
            # that ran; a Gate built after the change runs the new code and records the new digests.
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('invalid')))
            loaded = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
            first = stations(loaded)
            originals_code = {name: (mods / name).read_bytes() for name in ('contract_loader.py', 'arch.py')}
            try:
                # A loader that behaves the same with different bytes, and a validator that passes all.
                (mods / 'contract_loader.py').write_bytes(originals_code['contract_loader.py'] + b'\n# replaced on disk\n')
                (mods / 'arch.py').write_bytes(originals_code['arch.py']
                                               + b'\n\ndef validate_contract(data, root, contract_path, fail):\n    return 0\n')
                changed = {module: sha((mods / Path(path).name).read_bytes()) for module, path in installed.items()}
                second = stations(loaded)
                fresh = stations(EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base)))
            finally:
                for name, body in originals_code.items():
                    (mods / name).write_bytes(body)
            recorded = [by_module((d.get('architecture') or {}).get('validator'))
                        for d in list(first.values()) + list(second.values())]
            fresh_recorded = [by_module((d.get('architecture') or {}).get('validator')) for d in fresh.values()]
            observed['identity_is_what_ran'] = {
                'before_change': sorted({c for d in first.values() for c in d['refusals']}),
                'same_gate_after_change': sorted({c for d in second.values() for c in d['refusals']}),
                'fresh_gate_after_change': sorted({c for d in fresh.values() for c in d['refusals']}),
                'recorded_is_loaded': all(pristine(r) for r in recorded),
                'fresh_records_new': all(pristine(r, changed) for r in fresh_recorded)}
            check('architecture/identity-is-what-ran',
                   outcome(first, CODES['invalid_structure']) and outcome(second, CODES['invalid_structure'])
                   and all(pristine(r) for r in recorded)
                   and changed != installed_digests and outcome(fresh, None) and all(pristine(r, changed) for r in fresh_recorded))
            reset('valid')

        with region('architecture/snapshot-in-memory'):
            # The snapshot executes the validator from the bytes it holds in memory, so nothing on disk can
            # stand between the bytes digested and the code that runs. A same-account writer acts at the
            # one moment a copy on disk would be exposed: just before any engine module is loaded from a
            # path outside the installed engine, it replaces the arch.py beside that path with a validator
            # that passes everything. Every path the validator's modules are loaded from is also recorded.
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('invalid')))
            scratch = top / 'tmp'
            scratch.mkdir()
            stub = (mods / 'arch.py').read_bytes() + b'\n\ndef validate_contract(data, root, contract_path, fail):\n    return 0\n'
            real_spec, loads, swaps, real_tempdir = importlib.util.spec_from_file_location, [], [], tempfile.tempdir

            # A per-file link farm (a package manager that links files, not the directory): an installed engine
            # whose arch.py is a symlink to a file kept elsewhere.
            farm, keep = top / 'linkfarm' / '.veldo', top / 'linkstore'
            farm.mkdir(parents=True)
            keep.mkdir()
            for source in sorted(mods.glob('*.py')):
                shutil.copyfile(source, farm / source.name)
            farm_arch = (farm / 'arch.py').read_bytes()
            (keep / 'arch.py').write_bytes(farm_arch)
            (farm / 'arch.py').unlink()
            (farm / 'arch.py').symlink_to(keep / 'arch.py')
            engines = {os.path.realpath(str(d_)) for d_ in (mods, farm, keep)}

            def watched_spec(name, location=None, *args, **kwargs):
                where = os.path.realpath(str(location)) if location is not None else ''
                if where.startswith(str(scratch) + os.sep) or os.path.dirname(where) in engines:
                    loads.append(where)
                    beside = os.path.join(os.path.dirname(where), 'arch.py')
                    if where.startswith(str(scratch) + os.sep) and os.path.exists(beside):
                        Path(beside).write_bytes(stub)  # the concurrent writer, just before the load
                        swaps.append(beside)
                return real_spec(name, location, *args, **kwargs)

            # The Gate itself is built first (it loads its own organs); its validator snapshot is built at its
            # first architecture decision, inside the watched window.
            fresh_gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
            importlib.util.spec_from_file_location, tempfile.tempdir = watched_spec, str(scratch)
            try:
                raced = stations(fresh_gate)
            finally:
                importlib.util.spec_from_file_location, tempfile.tempdir = real_spec, real_tempdir
            left_on_disk = sorted(p_.name for p_ in scratch.iterdir())
            # The writer acts right after the snapshot's one read of an engine file: it replaces what that
            # read came from with a validator that passes everything. Only the bytes already read may run.
            farm_EL = load('v53_farm_eligibility', farm / 'control_eligibility.py')
            farm_gate = farm_EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
            farm_stub = farm_arch + b'\n\ndef validate_contract(data, root, contract_path, fail):\n    return 0\n'
            real_read, rewritten = Path.read_bytes, []

            installed_arch = (mods / 'arch.py').read_bytes()
            after_read = {os.path.realpath(str(keep / 'arch.py')): farm_stub, os.path.realpath(str(mods / 'arch.py')): stub}

            def read_then_write(self_):
                data = real_read(self_)
                target = os.path.realpath(str(self_))
                if self_.name == 'arch.py' and target in after_read:
                    Path(target).write_bytes(after_read[target])  # the concurrent writer, after the one read
                    rewritten.append(target)
                return data

            # The same writer in the window between the one read and the compile, over the regular engine.
            read_gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
            importlib.util.spec_from_file_location = watched_spec
            hooked = reading(read_then_write, farm_EL, EL)
            hooked.__enter__()
            try:
                farm_raced = stations(farm_gate)
                read_raced = stations(read_gate)
            finally:
                hooked.__exit__(None, None, None)
                importlib.util.spec_from_file_location = real_spec
                (keep / 'arch.py').write_bytes(farm_arch)
                (mods / 'arch.py').write_bytes(installed_arch)
            read_recorded = [by_module((d.get('architecture') or {}).get('validator')) for d in read_raced.values()]
            farm_digests = [by_module((d.get('architecture') or {}).get('validator')).get('arch') for d in farm_raced.values()]
            reset('valid')
            recorded = [by_module((d.get('architecture') or {}).get('validator')) for d in raced.values()]
            observed['snapshot_in_memory'] = {
                'refusals': sorted({r for d in raced.values() for r in d['refusals']}),
                'engine_loads_from_disk': len(loads), 'swapped': len(swaps), 'left_on_disk': left_on_disk,
                'recorded_is_installed': all(pristine(r) for r in recorded),
                'writes_after_the_one_read': len(rewritten),
                'link_farm': {'refusals': sorted({r for d in farm_raced.values() for r in d['refusals']}),
                              'recorded_arch_is_bytes_read': all(g_ == sha(farm_arch) for g_ in farm_digests)},
                'rewritten_after_read': {'refusals': sorted({r for d in read_raced.values() for r in d['refusals']}),
                                         'recorded_is_bytes_read': all(pristine(r) for r in read_recorded)}}
            check('architecture/snapshot-in-memory',
                   outcome(raced, CODES['invalid_structure']) and loads == [] and swaps == [] and left_on_disk == []
                   and all(pristine(r) for r in recorded)
                   and outcome(farm_raced, CODES['invalid_structure']) and len(rewritten) == 2
                   and all(g_ == sha(farm_arch) for g_ in farm_digests)
                   and outcome(read_raced, CODES['invalid_structure']) and all(pristine(r) for r in read_recorded))

        with region('architecture/snapshot-by-name'):
            # The snapshot holds each engine module by NAME, read once by its installed name, and answers every
            # load request by that name, never by a path: aliases, links and resolved paths cannot make one
            # name's bytes serve another. Four fixtures, each a separate installed engine judging an accepted,
            # structurally invalid contract (which only the real structural validator refuses).
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('invalid')))
            by_name = {}
            pass_all = b'\n\ndef validate_contract(data, root, contract_path, fail):\n    return 0\n'

            original = (mods / 'arch.py').read_bytes()
            # 1. Collision: right after arch.py's one read the writer makes it pass everything, and before a
            #    later-sorted engine file (budget.py) is read it becomes a link to arch.py.
            collide = engine_copy(top / 'collide' / '.veldo')
            steps = []

            def collide_writer(self_):
                if self_.name == 'budget.py' and os.path.realpath(str(self_.parent)) == str(collide) and steps == ['arch']:
                    os.unlink(str(self_))
                    os.symlink(str(collide / 'arch.py'), str(self_))
                    steps.append('budget')
                data = real_read(self_)
                if self_.name == 'arch.py' and os.path.realpath(str(self_.parent)) == str(collide) and not steps:
                    (collide / 'arch.py').write_bytes(original + pass_all)
                    steps.append('arch')
                return data

            decided, recorded, _ = judge(collide, 'collide', collide_writer)
            by_name['collision'] = (outcome(decided, CODES['invalid_structure']) and steps == ['arch', 'budget']
                                    and all(r == sha(original) for r in recorded))
            # 2. The same collision in a per-file link farm whose Gate file is regular: after arch.py's read
            #    the kept arch.py passes everything and the installed link is moved elsewhere; before
            #    budget.py's read its link is moved onto the kept arch.py.
            kept = top / 'farm2' / 'keep' / '.veldo'
            kept.mkdir(parents=True)
            farm2 = engine_copy(top / 'farm2' / 'i' / '.veldo', links_into=kept)
            moved = []

            def farm_writer(self_):
                if self_.name == 'budget.py' and str(self_.parent) == str(farm2) and moved == ['arch']:
                    os.unlink(str(self_))
                    os.symlink(str(kept / 'arch.py'), str(self_))
                    moved.append('budget')
                data = real_read(self_)
                if self_.name == 'arch.py' and str(self_.parent) == str(farm2) and not moved:
                    (kept / 'arch.py').write_bytes(original + pass_all)
                    (top / 'farm2' / 'elsewhere.py').write_bytes(original)
                    os.unlink(str(self_))
                    os.symlink(str(top / 'farm2' / 'elsewhere.py'), str(self_))
                    moved.append('arch')
                return data

            decided, recorded, _ = judge(farm2, 'farm2', farm_writer)
            by_name['farm_collision'] = (outcome(decided, CODES['invalid_structure']) and moved == ['arch', 'budget']
                                         and all(r == sha(original) for r in recorded))
            # 3. An alias link in the engine (zz_alias.py -> arch.py) renames nothing: arch is arch.
            alias = engine_copy(top / 'alias' / '.veldo')
            (alias / 'zz_alias.py').symlink_to(alias / 'arch.py')
            decided, recorded, arch_file = judge(alias, 'alias')
            by_name['alias'] = (outcome(decided, CODES['invalid_structure']) and all(r == sha(original) for r in recorded)
                                and arch_file == str(alias / 'arch.py'))
            # 4. A name the snapshot does not hold is the named stop ImportError, in the decision and in the
            #    durable stop event: an engine without verdict_corpus.py, which validate_checks loads.
            missing, events = engine_copy(top / 'missing' / '.veldo', leave_out=('verdict_corpus.py',)), []
            decided, _, _ = judge(missing, 'missing', events=events)
            by_name['miss_is_import_error'] = (
                outcome(decided, 'unavailable_service:architecture_validator')
                and all((d.get('architecture') or {}).get('error') == 'ImportError' for d in decided.values())
                and len(events) == len(decided)
                and all((e.get('architecture') or {}).get('error') == 'ImportError' for e in events))
            reset('valid')
            observed['snapshot_by_name'] = by_name
            check('architecture/snapshot-by-name', all(by_name.values()) and len(by_name) == 4)

        with region('architecture/identity-covers-what-ran'):
            # The recorded identity is built from what the snapshot actually executes: every held module it
            # runs, by name, with the digest of its bytes, not a fixed list of five. An engine whose tracker.py
            # (or verdict_corpus.py) gained a line runs that module, so the decision records the new bytes; and
            # a tracker.py that answers arch.py's open() of the contract with a valid one passes the invalid
            # contract, which the decision must then record, not the pristine digests.
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('invalid')))

            def recorded_of(decided):
                return [by_module((d.get('architecture') or {}).get('validator')) for d in decided.values()]

            covers = {}
            for module in ('tracker', 'verdict_corpus'):
                engine = engine_copy(top / ('covers-' + module) / '.veldo')
                with open(str(engine / (module + '.py')), 'a') as handle:
                    handle.write('\n# appended by the identity fixture\n')
                decided, _, _ = judge(engine, 'covers_' + module)
                wanted = sha((engine / (module + '.py')).read_bytes())
                covers[module] = (outcome(decided, CODES['invalid_structure'])
                                  and all(r.get(module) == wanted and r.get(module) != installed_digests.get(module)
                                          for r in recorded_of(decided)))
            hooked = engine_copy(top / 'covers-hook' / '.veldo')
            with open(str(hooked / 'tracker.py'), 'a') as handle:
                handle.write('\n\nimport io as _fixture_io\n_fixture_open = __builtins__["open"]\n'
                             '__builtins__["open"] = lambda p, *a, **k: _fixture_io.BytesIO(%r) '
                             'if str(p).endswith("architecture.yaml") else _fixture_open(p, *a, **k)\n' % VALID.encode())
            decided, _, _ = judge(hooked, 'covers_hook')
            hook_digest = sha((hooked / 'tracker.py').read_bytes())
            covers['hooked_tracker_recorded'] = all(r.get('tracker') == hook_digest for r in recorded_of(decided))
            reset('valid')
            observed['identity_covers_what_ran'] = covers
            check('architecture/identity-covers-what-ran', all(covers.values()) and len(covers) == 3)

        with region('architecture/identity-keyed-by-module'):
            # The identity is keyed by module name, never by role: an engine file NAMED after a role label takes no
            # other module's place. The installed yamlish.py (role parser) gains two lines that load parser.py, a
            # byte copy of the original yamlish.py; both run, so the decision and its durable event record both,
            # the changed yamlish under its own name with its role, and parser.py under its own name with none.
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('invalid')))
            keyed = engine_copy(top / 'keyed' / '.veldo')
            shutil.copyfile(str(keyed / 'yamlish.py'), str(keyed / 'parser.py'))
            with open(str(keyed / 'yamlish.py'), 'a') as handle:
                handle.write('\n\nimport importlib.util as _fixture_util\n'
                             '_fixture_spec = _fixture_util.spec_from_file_location("fixture_parser_copy", "parser.py")\n'
                             '_fixture_spec.loader.exec_module(_fixture_util.module_from_spec(_fixture_spec))\n')
            changed_yamlish, copy_digest = sha((keyed / 'yamlish.py').read_bytes()), sha((keyed / 'parser.py').read_bytes())
            keyed_events = []
            decided, _, _ = judge(keyed, 'keyed', events=keyed_events)
            wanted = {'yamlish': changed_yamlish, 'parser': copy_digest}
            records = [(d.get('architecture') or {}).get('validator') or {} for d in decided.values()]
            keyed_ok = {
                'both_recorded': all({m: by_module(r).get(m) for m in wanted} == wanted for r in records),
                'keyed_by_module': all(k == v.get('module') for r in records for k, v in r.items()),
                'roles_kept': all((r.get('yamlish') or {}).get('role') == 'parser' and 'role' in (r.get('parser') or {})
                                  and r['parser']['role'] is None for r in records),
                'events_record_both': len(keyed_events) == len(decided) and all(
                    {m: ((e.get('architecture') or {}).get('validator') or {}).get(m) for m in wanted} == wanted
                    for e in keyed_events)}
            keyed_ok['decisions'] = bool(records) and outcome(decided, CODES['invalid_structure'])
            reset('valid')
            observed['identity_keyed_by_module'] = dict(keyed_ok, recorded=[sorted(by_module(r)) for r in records[:1]])
            check('architecture/identity-keyed-by-module', all(keyed_ok.values()) and len(keyed_ok) == 5)

        with region('architecture/snapshot-held-names'):
            # Only a non-empty module name is ever held, and only a regular file is ever read. An engine with a
            # file named '.py' (whose module name is empty) holds no empty name, so a request whose file name
            # is not a held module (no '.py', the bare '.py', no location at all) is the named stop and that
            # file's code never runs; an engine with a FIFO under a '.py' name is a named stop, never a wait.
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('invalid')))
            held_names = {}
            dotted = engine_copy(top / 'dotpy' / '.veldo')
            dot_marker = top / 'dotpy-ran'
            (dotted / '.py').write_text('open(%r, "w").write("ran")\n' % str(dot_marker))
            dot_el = load('v53_dotpy_eligibility', dotted / 'control_eligibility.py')
            dot_snapshot = dot_el.ValidatorSnapshot(str(dotted))
            answered = {}
            for label, request in (('arch.pyc', 'arch.pyc'), ('engine/arch', str(dotted / 'arch')),
                                   ('engine/.py', str(dotted / '.py')), ('.py', '.py'), ('no location', None)):
                try:
                    spec = dot_snapshot._spec('fixture_request', request) if request is not None else dot_snapshot._spec('fixture_request')
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    answered[label] = 'answered'
                except Exception as error:  # noqa: BLE001 - recorded by type, asserted below
                    answered[label] = type(error).__name__
            decided, _, _ = judge(dotted, 'dotpy_gate')
            # Each sub-condition by name, beside the value it saw, so a false row says which part went false.
            empty_parts = {'requests_all_import_error': set(answered.values()) == {'ImportError'},
                           'dot_py_never_ran': not dot_marker.exists(),
                           'decisions_invalid_structure': outcome(decided, CODES['invalid_structure'])}
            empty_seen = {'refusals': sorted({r for d in decided.values() for r in d['refusals']})}
            held_names['empty_name'] = all(empty_parts.values()) and len(empty_parts) == 3
            piped = engine_copy(top / 'fifo' / '.veldo')
            os.mkfifo(str(piped / 'zz.py'))
            # A reader blocked on the FIFO would wait for a writer forever; this helper opens it for writing,
            # which releases such a reader with an empty read, so a snapshot that reads it cannot hang the suite.
            # It touches the FIFO only after FIFO_GRACE seconds with the judgement still running. The snapshot's
            # own open is non-blocking and is held open while it is judged by descriptor, so a write-end open
            # landing in that window succeeds without any reader having waited; polling from the start counted
            # that as a release whenever load stretched the window. After the grace, a release means a reader
            # was still there after the judgement had every chance to finish: a wait.
            import threading
            import time
            FIFO_GRACE = 20.0
            stop_helper, unblocked = threading.Event(), []

            def release_readers():
                if stop_helper.wait(FIFO_GRACE):
                    return
                while not stop_helper.is_set():
                    try:
                        os.close(os.open(str(piped / 'zz.py'), os.O_WRONLY | os.O_NONBLOCK))
                        unblocked.append(1)
                    except OSError:
                        pass
                    stop_helper.wait(0.02)

            helper = threading.Thread(target=release_readers, daemon=True)
            helper.start()
            fifo_events = []
            fifo_started = time.monotonic()
            try:
                decided, _, _ = judge(piped, 'fifo_gate', events=fifo_events)
            finally:
                fifo_seconds = time.monotonic() - fifo_started
                stop_helper.set()
                helper.join(5)
            fifo_parts = {'decisions_unavailable_validator': outcome(decided, 'unavailable_service:architecture_validator'),
                          'no_reader_released': not unblocked,
                          'errors_import_error': all((d.get('architecture') or {}).get('error') == 'ImportError'
                                                     for d in decided.values())}
            fifo_seen = {'refusals': sorted({r for d in decided.values() for r in d['refusals']}),
                         'errors': sorted({str((d.get('architecture') or {}).get('error')) for d in decided.values()}),
                         'helper_alive_after_join': helper.is_alive(), 'judge_seconds': round(fifo_seconds, 3),
                         'grace_seconds': FIFO_GRACE}
            held_names['fifo_is_named_stop'] = all(fifo_parts.values()) and len(fifo_parts) == 3
            reset('valid')
            observed['snapshot_held_names'] = {
                'requests': answered, 'cases': held_names, 'fifo_readers_released': len(unblocked),
                'empty_name': dict(parts=empty_parts, seen=empty_seen), 'fifo': dict(parts=fifo_parts, seen=fifo_seen),
                'false': sorted(case + '/' + part for case, parts in (('empty_name', empty_parts), ('fifo', fifo_parts))
                                for part, value in parts.items() if not value)}
            check('architecture/snapshot-held-names', all(held_names.values()) and len(held_names) == 2)

        with region('architecture/snapshot-file-bounded'):
            # A held file is read up to the snapshot's stated size limit and no further: one over it is the named
            # stop ImportError, in the decision and in the durable stop event, whether or not anything runs it.
            # A sparse 64 MiB zz.py (no disk, no gigabyte) is judged with Python's allocations traced: a read of
            # the whole file allocates its 64 MiB, a bounded read allocates the limit. A file of exactly the
            # limit is held, and the engine judges as usual (the accepted contract is structurally invalid).
            import tracemalloc
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=reset('invalid')))
            bounded, largest = {}, max(p_.stat().st_size for p_ in mods.glob('*.py'))
            stated = getattr(EL, 'ENGINE_FILE_LIMIT', None)
            limit = stated if isinstance(stated, int) else 1 << 20
            bounded['limit_stated'] = isinstance(stated, int) and largest < stated <= 16 << 20
            SPARSE = 64 << 20

            def sparse_engine(tag, size):
                engine = engine_copy(top / ('bounded-' + tag) / '.veldo')
                with open(str(engine / 'zz.py'), 'wb') as handle:
                    handle.truncate(size)
                return engine

            huge, huge_events = sparse_engine('huge', SPARSE), []
            tracing = tracemalloc.is_tracing()
            if not tracing:
                tracemalloc.start()
            tracemalloc.reset_peak()
            try:
                decided, _, _ = judge(huge, 'bounded_huge', events=huge_events)
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                if not tracing:
                    tracemalloc.stop()
            bounded['over_limit_is_named_stop'] = (
                outcome(decided, 'unavailable_service:architecture_validator')
                and all((d.get('architecture') or {}).get('error') == 'ImportError' for d in decided.values())
                and len(huge_events) == len(decided)
                and all((e.get('architecture') or {}).get('error') == 'ImportError' for e in huge_events))
            bounded['read_is_bounded'] = peak < SPARSE // 2
            decided, _, _ = judge(sparse_engine('over', limit + 1), 'bounded_over')
            bounded['one_over_limit_refused'] = outcome(decided, 'unavailable_service:architecture_validator')
            decided, _, _ = judge(sparse_engine('at', limit), 'bounded_at')
            bounded['at_limit_held'] = outcome(decided, CODES['invalid_structure'])
            reset('valid')
            observed['snapshot_file_bounded'] = dict(bounded, limit=stated, largest_engine_file=largest,
                                                     traced_peak_mib=round(peak / (1 << 20), 1))
            check('architecture/snapshot-file-bounded', all(bounded.values()) and len(bounded) == 5)

        with region('architecture/snapshot-module-files'):
            # Each held module's __file__ is the installed path of its name, never the file a link resolves to,
            # in a per-file link farm too; and linecache holds a module's lines BEFORE it runs, so an error
            # raised while a module loads shows the line that raised.
            import traceback
            files = {}
            farm_keep = top / 'files' / 'keep' / '.veldo'
            farm_keep.mkdir(parents=True)
            files_farm = engine_copy(top / 'files' / 'i' / '.veldo', links_into=farm_keep)
            files_el = load('v53_files_eligibility', files_farm / 'control_eligibility.py')
            expected_dir = os.path.realpath(str(files_farm))
            try:
                farm_snapshot = files_el.ValidatorSnapshot(str(files_farm))
                files['file_is_installed_path'] = (
                    farm_snapshot.validate.__file__ == os.path.join(expected_dir, 'validate.py')
                    and farm_snapshot.arch.__file__ == os.path.join(expected_dir, 'arch.py')
                    and all(entry['path'] == os.path.join(expected_dir, entry['module'] + '.py')
                            for entry in farm_snapshot.identity.values()))
            except Exception as error:  # noqa: BLE001 - a snapshot that cannot load names no file
                files['file_is_installed_path'] = False
                observed['snapshot_module_files_error'] = type(error).__name__
            failing = engine_copy(top / 'files-raise' / '.veldo')
            raising_line = "raise RuntimeError('raised while tracker loads')"
            with open(str(failing / 'tracker.py'), 'a') as handle:
                handle.write('\n' + raising_line + '\n')
            failing_el = load('v53_failing_eligibility', failing / 'control_eligibility.py')
            shown = None
            try:
                failing_el.ValidatorSnapshot(str(failing))
            except RuntimeError:
                frames = traceback.extract_tb(sys.exc_info()[2])
                shown = frames[-1].line if frames else None
            files['load_error_shows_its_line'] = shown == raising_line
            observed['snapshot_module_files'] = files
            check('architecture/snapshot-module-files', all(files.values()) and len(files) == 2)

        with region('architecture/snapshot-source'):
            # Tracebacks and inspect show the code that ran, and ONLY the snapshot's code: its lines are kept
            # under a key no other loader uses. After the installed arch.py is edited on disk: the snapshot's
            # traceback prints the line that raised as it was loaded, inspect finds the function it names and
            # the loader hands back the held source; a module loaded ordinarily from the edited file prints the
            # edited file's line (no snapshot line leaks into it); and a second snapshot, of the edited file,
            # neither shows the first snapshot's lines nor changes what the first shows.
            import inspect
            import linecache
            import traceback
            reset('valid')
            source_gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
            stations(source_gate)
            held = source_gate._architecture_validator().arch
            ran_text = (mods / 'arch.py').read_text()
            ran_lines = ran_text.splitlines()

            def raised_line(module):
                try:
                    module.read_contract(None, None)  # Path(None) raises inside read_contract
                except TypeError:
                    code_file = module.read_contract.__code__.co_filename
                    frames = [f for f in traceback.extract_tb(sys.exc_info()[2]) if f.filename == code_file]
                    return (frames[-1].lineno, frames[-1].line) if frames else (None, None)
                return (None, None)

            def same(line_no_line, lines):
                line_no, line = line_no_line
                return bool(line_no) and line_no <= len(lines) and line == lines[line_no - 1].strip()

            installed_arch = (mods / 'arch.py').read_bytes()
            edited = b'# a later edit on disk\n' * 3 + installed_arch
            try:
                (mods / 'arch.py').write_bytes(edited)
                linecache.checkcache()
                first_seen = raised_line(held)
                try:
                    first = inspect.getsource(held.read_contract).splitlines()[0]
                except (OSError, TypeError) as error:
                    first = repr(error)
                try:
                    given = held.__loader__.get_source(held.__name__) if hasattr(held.__loader__, 'get_source') else None
                except (OSError, ImportError) as error:
                    given = repr(error)
                edited_lines = edited.decode().splitlines()
                ordinary = load('v53_ordinary_arch', mods / 'arch.py')
                ordinary_seen = raised_line(ordinary)
                second_gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
                stations(second_gate)
                second_seen = raised_line(second_gate._architecture_validator().arch)
                first_again = raised_line(held)
            finally:
                (mods / 'arch.py').write_bytes(installed_arch)
                linecache.checkcache()
            observed['snapshot_source'] = {
                'traceback_line_is_the_line_that_ran': same(first_seen, ran_lines),
                'getsource_first_line': first, 'get_source_is_held': given == ran_text,
                'ordinary_loader_sees_its_own_file': same(ordinary_seen, edited_lines),
                'second_snapshot_sees_its_own_bytes': same(second_seen, edited_lines),
                'first_snapshot_unchanged_by_second': same(first_again, ran_lines),
                'snapshot_key_is_not_the_installed_path': held.read_contract.__code__.co_filename != held.__file__}
            check('architecture/snapshot-source',
                   same(first_seen, ran_lines) and first.startswith('def read_contract') and given == ran_text
                   and same(ordinary_seen, edited_lines) and same(second_seen, edited_lines) and same(first_again, ran_lines))

        with region('architecture/not-text-refused'):
            # A contract that is not valid UTF-8 is a named parse failure with the digest of the bytes read,
            # never an unanswered validator. The accepted record names those very bytes, so only the
            # decoding can refuse them.
            not_text = VALID.encode() + b'# \xff\xfe\n'
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=sha(not_text)))
            arrange('optional_absent')
            contract.write_bytes(not_text)
            judged = stations(gate)
            reset('valid')
            observed['not_text'] = sorted({r for d in judged.values() for r in d['refusals']})
            check('architecture/not-text-refused',
                   outcome(judged, CODES['parse_failure'])
                   and all(((d.get('architecture') or {}).get('artifact') or {}).get('digest') == sha(not_text)
                           for d in judged.values()))

        with region('architecture/validated-is-digested'):
            # The digest compared with the accepted record is the digest of the very bytes the loader parsed
            # and validated, never a second read: a writer lands while the contract is being validated.
            # Validated unaccepted bytes are refused (and recorded) as what was validated even though the
            # file now holds the accepted bytes; validated accepted bytes pass although the file changed.
            put('architecture:' + REPOSITORY, 'architecture_contract', dict(state='accepted', digest=sha(VALID.encode())))
            raced = {}
            for name, (validated, lands) in {'unaccepted_validated': (WEAKENED, VALID),
                                             'accepted_validated': (VALID, WEAKENED)}.items():
                arrange('optional_absent', text=validated)
                racing = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
                validator = racing._architecture_validator().arch
                real_validate, versions = validator.validate_contract, []

                def validate_then_write(data, root, path, fail, real_validate=real_validate, lands=lands, versions=versions):
                    versions.append(data.get('version'))
                    contract.write_text(lands)  # the concurrent writer, after the loader read the bytes
                    return real_validate(data, root, path, fail)

                validator.validate_contract = validate_then_write
                decided = {}
                for st in EL.FLOOR_STATIONS:
                    contract.write_text(validated)  # each decision reads `validated`; the writer lands during it
                    decided[st] = racing.decide(st, SID, context=CTX)
                raced[name] = (decided, list(versions))
            reset('valid')
            race_ok = outcome(raced['unaccepted_validated'][0], CODES['unaccepted_artifact'])
            race_ok &= outcome(raced['accepted_validated'][0], None)
            race_ok &= set(raced['unaccepted_validated'][1]) == {2} and set(raced['accepted_validated'][1]) == {1}
            for name, validated in (('unaccepted_validated', WEAKENED), ('accepted_validated', VALID)):
                race_ok &= all(((d.get('architecture') or {}).get('artifact') or {}).get('digest') == sha(validated.encode())
                               for d in raced[name][0].values())
            observed['validated_is_digested'] = {name: {'refusals': sorted({r for d in ds.values() for r in d['refusals']}),
                                                        'validated_versions': sorted(set(v))}
                                                 for name, (ds, v) in raced.items()}
            check('architecture/validated-is-digested', race_ok)

        with region('architecture/observations'):
            # Every eligibility decision (one event per station, EL.FLOOR_STATIONS) records the architecture it
            # judged, and its refusals keep their taxonomy. The Gate's other events, VELDO-0054's decision
            # dependency and invalid record observations, judge no architecture.
            decisions = [e for e in gate.observations if e.get('operation') in EL.FLOOR_STATIONS]
            judged = [e for e in decisions if e.get('architecture')]
            obs_ok = len(judged) == len(decisions) > 0
            obs_ok &= all(set(e['architecture']) - {'error'} == {'basis', 'kind', 'artifact_digest', 'validator'} for e in judged)
            refused_arch = [e for e in gate.observations if any('architecture' in r for r in e['refusals'])]
            obs_ok &= len(refused_arch) > 0 and all(
                set(e['taxonomy']) <= {'invalid_input', 'missing_evidence', 'missing_authority'} for e in refused_arch)
            obs_ok &= all(pristine(e['architecture']['validator']) for e in judged
                          if e['architecture']['basis'] != 'store_only' and e['architecture']['validator'])
            status = gate.status()
            obs_ok &= status['accepted'] > 0 and status['refused'] > 0
            observed['gate_status'] = status
            observed['decision_sample'] = [e for e in gate.observations if e['refusals']][:2]
            check('architecture/observations', obs_ok)

        for first in regions:
            check('ran/' + first, first not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V53_OBSERVED'] = observed
        reader.close()
        observer.close()
        writer.close()


_v53_started = __import__('time').monotonic()
_v53_suite()
_V53_SECONDS = __import__('time').monotonic() - _v53_started
