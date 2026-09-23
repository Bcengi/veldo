"""VELDO-0052: shared floor eligibility at every enabled entry, over a real control store.

Only shared ROOT and expect are consumed. One temporary tree is both the repository the entries
read and the installed .veldo they run from, so a registered mutation of any production module
reaches every entry that loads it. Real SQLite store, keyed journal signatures, a fresh reader
process over real receipts, and real VELDO-0036 reservation transactions with an observed receiver.
Launch counters stand in for the delegated build and review agents (the same seams dispatch.py
exposes); they qualify no live engine.
"""


def _v52_suite():
    import ast
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
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
        'dispatch.py': ROOT / ".veldo" / "dispatch.py",
        'work.py': ROOT / ".veldo" / "work.py",
        'work_state.py': ROOT / ".veldo" / "work_state.py",
        'frontier.py': ROOT / ".veldo" / "frontier.py",
        'plan.py': ROOT / ".veldo" / "plan.py",
        'executor.py': ROOT / ".veldo" / "executor.py",
    }
    FLOOR = ('frontier.py', 'work.py', 'plan.py', 'executor.py', 'dispatch.py', 'work_state.py',
             'control_eligibility.py')

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v52-', dir=fast) as directory:
        base = Path(directory) / 'repo'
        mods = base / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        GP = load('v52_git', mods / 'git_process.py')
        GP.run(['git', '-C', str(base), 'init', '-q'], check=True, capture_output=True)
        EL = load('v52_eligibility', mods / 'control_eligibility.py')
        S = load('v52_store', mods / 'control_store.py')
        RES = load('v52_reservations', mods / 'control_reservations.py')
        RT = load('v52_runtime', mods / 'control_reservation_runtime.py')
        CLM = EL._organ('control_claim')
        DOMAIN, REPOSITORY = 'domain-52', 'repository-52'
        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        key = os.urandom(32)

        def sign(message):
            return hmac.new(key, message, hashlib.sha256).hexdigest()

        serial = [0]

        def put(identity, kind, data):
            serial[0] += 1
            row = writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            S.execute(writer, dict(command_id='c%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='n%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: row[0] if row else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)),
                      'authority', sign, 1)

        def version(identity):
            row = writer.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            return row[0] if row else 0

        def receipt(fact, unit, revision, n=0, **extra):
            body = {'fact': fact, 'subject': {'id': unit, 'revision': revision}}
            body.update({
                'attempt_finished': dict(trusted_exit=True, accounting_observation='obs/' + unit, containment_empty=True),
                'artifact_accepted': dict(station='review', artifact_digests=['sha256:' + unit], acceptor='dmitry'),
                'revision_landed': dict(publication_receipt=landing(unit), remote_confirmation='refs/heads/main',
                                        replicated=True, spec_shipped_event='event/' + unit),
                'objective_satisfied': dict(signed_assessment='assessment/' + unit, accepted_objective_revision=1,
                                            assessor='dmitry'),
            }[fact])
            body.update(extra)
            put('receipt:%s:%s:%d:%d' % (fact, unit, revision, n), 'completion_receipt', body)

        def landing(unit):
            return {f: f + '/' + unit for f in (
                'implementation_commit', 'proof_digest', 'reviewed_source_digest', 'old_remote_tip',
                'candidate_commit', 'tested_tree', 'gate_invocation', 'remote_confirmation', 'replication_receipt',
                'dispatch_id')} | {'gate_output_location': 'outside/' + unit, 'unit_id': unit}

        def landed(unit, revision=1):
            for fact in ('attempt_finished', 'artifact_accepted', 'revision_landed'):
                receipt(fact, unit, revision)

        def unit(sid, plan='PLAN-9001', depends=('VELDO-9100',), scope='sha256:scope', admitted=True,
                 admission_scope=None, revision=1):
            put(sid, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + sid,
                                            requirements=[], eligible_holders=['worker-a'], plan=plan, project='p1',
                                            depends_on=list(depends), scope_digest=scope, revision=revision,
                                            producer='builder-a', approvals_required=['owner']))
            put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            if admitted:
                put('admission:' + sid, 'admission', dict(unit=sid, state='accepted',
                                                           scope_digest=admission_scope or scope))
            put('approval:%s:owner' % sid, 'approval', dict(unit=sid, name='owner', state='granted', revision=revision))

        def claim(sid):
            u = json.loads(writer.execute('SELECT data FROM entities WHERE id=?', (sid,)).fetchone()[0])
            put(sid, 'execution_unit', dict(u, state='CLAIMED'))
            put('backlog:' + sid, 'backlog_item', dict(state='ACTIVE', repository_uuid=REPOSITORY))
            put(CLM.claim_id(REPOSITORY, sid), 'claim', dict(unit_id=sid, holder='worker-a', generation=1,
                                                             state='owned', heartbeat_at=CLM.CL._now()))

        # Accepted authority records: the scenario each unit exercises is its ONLY defect.
        put('project:p1', 'project', dict(name='floor'))
        put('authority:' + DOMAIN, 'authority', dict(state='active', generation=1))
        put('plan:PLAN-9001', 'plan', dict(status='ready', revision=1))
        put('plan:PLAN-9002', 'plan', dict(status='draft', revision=1))
        put('VELDO-9100', 'execution_unit', dict(state='DONE', repository_uuid=REPOSITORY, revision=1))
        landed('VELDO-9100')
        put('VELDO-9199', 'execution_unit', dict(state='BUILT', repository_uuid=REPOSITORY, revision=1))
        receipt('attempt_finished', 'VELDO-9199', 1)
        # unit: (the predicate its one defect violates, the named refusal it must produce)
        SCENARIOS = {
            'VELDO-9101': ('admission_current', {'missing_authority:admission'}),
            'VELDO-9102': ('plan_not_draft', {'draft_plan'}),
            'VELDO-9103': ('dependencies_resolved', {'unresolved_dependency:VELDO-9199'}),
            'VELDO-9104': ('decisions_settled', {'unresolved_decision:decision:9104'}),
            'VELDO-9105': ('admission_current', {'stale_scope'}),
            'VELDO-9106': (None, set()),
        }

        def expected_at(station, sid):
            predicate, codes = SCENARIOS[sid]
            return codes if predicate in EL.STATION_PREDICATES[station] else set()
        unit('VELDO-9101', admitted=False)
        unit('VELDO-9102', plan='PLAN-9002')
        unit('VELDO-9103', depends=('VELDO-9100', 'VELDO-9199'))
        unit('VELDO-9104')
        put('decision:9104', 'decision', dict(blocks=['VELDO-9104'], state='open'))
        put('decision:settled', 'decision', dict(blocks=['VELDO-9106'], state='settled'))
        unit('VELDO-9105', scope='sha256:new', admission_scope='sha256:old')
        unit('VELDO-9106')

        # The checkout says every scenario is ready, planned and unblocked, so the files alone would
        # launch all six: every refusal below is attributable to the store-backed station decision.
        (base / 'specs').mkdir()
        (base / 'plans').mkdir()

        def spec(sid, status='ready', depends=(), lane='planned', work=None):
            fm = ['---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Floor fixture ' + sid, 'status: ' + status,
                  'risk: low', 'owner: dmitry', 'lane: ' + lane]
            if lane == 'planned':
                fm += ['plan: PLAN-9001', 'work: ' + work, 'plan_revision: 1']
            fm += ['depends_on: [%s]' % ', '.join(depends), '---', '', 'Fixture.', '']
            (base / 'specs' / (sid + '-fixture.md')).write_text('\n'.join(fm))

        work_items = []
        for n, sid in enumerate(sorted(SCENARIOS), 1):
            spec(sid, work='W%d' % n)
            work_items += ['  - item: W%d' % n, '    spec: ' + sid, '    order: %d' % n]
        (base / 'plans' / 'PLAN-9001-fixture.md').write_text('\n'.join(
            ['---', 'schema: veldo.plan/v1', 'id: PLAN-9001', 'title: Floor fixture plan', 'status: ready',
             'revision: 1', 'work:'] + work_items + ['---', '', 'Fixture plan.', '']))
        originals = {p: p.read_bytes() for p in (base / 'specs').glob('*.md')}

        def restore():
            for p, body in originals.items():
                p.write_bytes(body)

        reader = S.open_store(str(db), mode='r')
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY)
        FR = load('v52_frontier', mods / 'frontier.py')
        WK = load('v52_work', mods / 'work.py')
        PL = load('v52_plan', mods / 'plan.py')
        EX = load('v52_executor', mods / 'executor.py')
        DSP = load('v52_dispatch', mods / 'dispatch.py')
        WS = load('v52_work_state', mods / 'work_state.py')
        claims = base / 'claims'
        plan_path = str(base / 'plans' / 'PLAN-9001-fixture.md')

        # The observed receiver: every subscription CLI launch, with whether its reservation was
        # already committed in the store when the launch began.
        receiver = []
        observer = S.open_store(str(db), mode='r')

        def launcher(adapter):
            def launch(invocation, configuration):
                committed = observer.execute('SELECT 1 FROM entities WHERE id=?',
                                             (RES.entity('invocation', [DOMAIN, invocation]),)).fetchone() is not None
                receiver.append((adapter, invocation, committed, configuration.get('tools')))
            return launch

        def authorize(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            return bool(row) and json.loads(row[0]).get('roles') == ['reservation_service']

        put('runner', 'membership', dict(roles=['reservation_service']))
        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=authorize, signer='authority', sign=sign)
        stops = []
        guards = {a: RT.InvocationGuard(reservations, a, launcher(a), stops.append) for a in RT.ADAPTERS}
        calls = EL.StationCalls(gate, guards)
        CONFIG = {'mcp_servers': ['configured'], 'tools': ['configured-tool']}
        clock = [100.0]

        def tick():
            clock[0] += 1
            return clock[0]

        def policies(account, project, sid, caps):
            for scope, subject in zip(RES.SCOPES, (account, project, sid)):
                cap = dict(capacity=50, invocations=100, wall_seconds=10000)
                cap.update(caps.get(scope, {}))
                reservations.configure('policy-%s-%s-%s' % (sid, scope, subject), scope, subject, cap, now=tick())

        def dispatch_slot(sid, account='acct-floor', project='proj-floor', caps=None):
            policies(account, project, sid, caps or {})
            reservations.reserve_worker('slot-' + sid, 'd-' + sid, account, project, sid, now=tick())

        class Hooks(EX.LoopSteps):
            def __init__(self):
                self.builds, self.root = [], str(base)

            def resolve(self, sid):
                return {'id': sid, 'status': FR.current_status(sid, str(base)), 'plan': 'PLAN-9001', 'work': 'W1'}

            def run_check(self, spec):
                return True, 'checked'

            def build(self, spec, calls=None):
                self.builds.append(spec['id'])
                if calls is not None:
                    calls.invoke('claude_code', 'initial', 'build-' + spec['id'], 10, CONFIG, now=tick())
                return {'ok': True, 'commit': 'c', 'evidence': {}}

            def gate(self):
                return {'green': True, 'detail': 'green'}

            def assemble_proof(self, spec, build):
                return {'criteria': []}

            def validate_proof(self, proof):
                return True, 0

            def emit(self, *args, **kwargs):
                return None

        class Reviewer(DSP.Reviewer):
            identity = 'reviewer-b'

            def __init__(self):
                self.reviews = []

            def review(self, spec, unit, calls=None):
                self.reviews.append(spec['id'])
                if calls is not None:
                    calls.invoke('codex', 'initial', 'review-' + spec['id'], 10, CONFIG, now=tick())
                    calls.invoke('codex', 'follow_on', 'review-more-' + spec['id'], 10, CONFIG, now=tick())
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
                # Not ok: the loop releases the unit and never re-claims it, so the run drains.
                self.units.append(unit['spec'])
                return {'ok': False}

        def attempt(fn):
            # A refusal raised by a later station (a provider call inside a launched builder or
            # reviewer) is recorded as that outcome; the launch counters still see the launch.
            try:
                return fn()
            except EL.Refused as error:
                return {'refusals': ['raised:' + error.code] + list((error.decision or {}).get('refusals', []))}

        def refusals_of(station, sid, **kw):
            return set(gate.decide(station, sid, **kw)['refusals'])

        # Each region reds its own rows if it raises, so a mutation that crashes a region is a
        # red row there and never a suite that stops asserting (the driver refuses a dead run).
        emitted, raised = set(), []
        # What the entries actually did, kept for the proof bundle's observations (no secrets).
        observed = {'launches': {}, 'stale_refusals': {}}

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0052 ' + label, condition)

        regions = []

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

        # --- AC1: every enabled floor entry invokes the shared station decision -------------------
        # Registrations are derived from the actual call sites of the installed modules.
        def qualified_calls(path, names, station_arg):
            found = set()
            tree = ast.parse(Path(path).read_text())

            def walk(node, prefix):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        walk(child, prefix + [child.name])
                    else:
                        if isinstance(child, ast.Call) and prefix:
                            f = child.func
                            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, 'id', None)
                            if name in names:
                                if not station_arg:
                                    found.add((Path(path).name, '.'.join(prefix)))
                                elif child.args and isinstance(child.args[0], ast.Constant) \
                                        and child.args[0].value in EL.FLOOR_STATIONS:
                                    found.add((Path(path).name, '.'.join(prefix), child.args[0].value))
                        walk(child, prefix)
            walk(tree, [])
            return found

        with region('eligibility/registrations-from-call-sites'):
            derived = set()
            consumers = set()
            for name in FLOOR:
                derived |= qualified_calls(mods / name, ('decide', 'require'), True)
                consumers |= qualified_calls(mods / name, EL.READER_CALLS, False)
            stations_ok = all(set(EL.STATION_PREDICATES[s]) >= set(EL.CC.ENTRY_PREDICATES[s]) for s in EL.FLOOR_STATIONS)
            check('eligibility/registrations-from-call-sites',
                   derived == set(EL.REGISTRATIONS) and stations_ok
                   and {s for _, _, s in derived} >= {'selection', 'claim', 'direct_execution', 'build', 'review',
                                                       'publication', 'provider_request'})

        with region('eligibility/entry-frontier', 'eligibility/entry-work'):
            named_ok = True
            for sid in SCENARIOS:
                for station in ('selection', 'claim', 'direct_execution'):
                    named_ok &= refusals_of(station, sid) == expected_at(station, sid)
            launches = {}
            # Selection: the frontier offers exactly the valid unit, each offer carrying its ticket.
            legacy = {u['spec'] for u in FR.claimable(repo_root=str(base), claims_root=str(claims))}
            offered = FR.claimable(repo_root=str(base), claims_root=str(claims), eligibility=gate)
            launches['frontier'] = {u['spec'] for u in offered}
            tickets = {u['spec']: u['eligibility'] for u in offered}
            check('eligibility/entry-frontier',
                   legacy == set(SCENARIOS) and launches['frontier'] == {'VELDO-9106'}
                   and tickets['VELDO-9106']['station'] == 'selection' and tickets['VELDO-9106']['eligible'])

            counter = Counter()
            WK.WorkLoop('worker-a', [], counter, repo_root=str(base), claims_root=str(claims), eligibility=gate).run()
            observed['launches']['frontier_offers'] = sorted(launches['frontier'])
            observed['launches']['work_dispatches'] = list(counter.units)
            check('eligibility/entry-work', counter.units == ['VELDO-9106'])

        with region('eligibility/entry-work-rechecks'):
            # The claim station itself: an input that moves after selection refuses BEFORE the claim is
            # taken, and one that moves between that decision and the claim is caught by the recheck
            # after it, which releases the claim. A spy on the ledger records what was really claimed.
            for sid in ('VELDO-9109', 'VELDO-9111'):
                unit(sid)
                n = 7 if sid == 'VELDO-9109' else 8
                spec(sid, work='W%d' % n)

            class Interposer:
                triggers = {('selection', 'VELDO-9109'), ('claim', 'VELDO-9111')}

                def __getattr__(self, name):
                    return getattr(gate, name)

                def decide(self, station, sid, **kw):
                    decision = gate.decide(station, sid, **kw)
                    if (station, sid) in self.triggers:
                        # Every time: each re-selection mints a fresh ticket, and each one must go stale.
                        put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope'))
                    return decision

            ledger = {'claimed': [], 'released': []}
            real_claim, real_release = WK.CL.claim, WK.CL.release

            def spy_claim(sid, *args, **kwargs):
                ledger['claimed'].append(sid)
                return real_claim(sid, *args, **kwargs)

            def spy_release(sid, *args, **kwargs):
                ledger['released'].append(sid)
                return real_release(sid, *args, **kwargs)

            WK.CL.claim, WK.CL.release = spy_claim, spy_release
            work_items_extra = ['  - item: W7', '    spec: VELDO-9109', '    order: 7',
                                '  - item: W8', '    spec: VELDO-9111', '    order: 8']
            plan_file = base / 'plans' / 'PLAN-9001-fixture.md'
            plan_text = plan_file.read_text()
            plan_file.write_text(plan_text.replace('---\n\nFixture plan.', '\n'.join(work_items_extra) + '\n---\n\nFixture plan.'))
            counter = Counter()
            try:
                WK.WorkLoop('worker-a', [], counter, repo_root=str(base), claims_root=str(claims) + '-2',
                            eligibility=Interposer()).run()
            finally:
                WK.CL.claim, WK.CL.release = real_claim, real_release
                plan_file.write_text(plan_text)
                for sid in ('VELDO-9109', 'VELDO-9111'):
                    (base / 'specs' / (sid + '-fixture.md')).unlink()
            check('eligibility/entry-work-rechecks',
                   counter.units == ['VELDO-9106'] and 'VELDO-9109' not in ledger['claimed']
                   and ledger['claimed'].count('VELDO-9111') == 1 and 'VELDO-9111' in ledger['released'])

        with region('eligibility/entry-plan'):
            run_checks = {}
            for sid in SCENARIOS:
                with contextlib.redirect_stdout(io.StringIO()):
                    run_checks[sid] = PL.cmd_run_check(plan_path, sid, eligibility=gate)
            check('eligibility/entry-plan',
                   {s for s, rc in run_checks.items() if rc == 0} == {'VELDO-9106'})

        with region('eligibility/entry-executor'):
            hooks = Hooks()
            halted = {sid: EX.Executor(hooks, eligibility=gate).run(sid, stop_after='proof') for sid in SCENARIOS}
            check('eligibility/entry-executor',
                   hooks.builds == ['VELDO-9106'] and halted['VELDO-9106']['state'] == 'built'
                   and all(halted[s]['halted_at'] == EX.ELIGIBILITY_STEP for s in SCENARIOS if s != 'VELDO-9106'))

        with region('eligibility/named-refusals'):
            # Build, review and publication run for a claimed unit; the claim's own lifecycle writes are
            # station outputs and leave every earlier ticket current.
            for sid in SCENARIOS:
                claim(sid)
                dispatch_slot(sid)
            for sid in SCENARIOS:
                for station in ('build', 'publication'):
                    named_ok &= refusals_of(station, sid, context={'holder': 'worker-a'}) == expected_at(station, sid)
                named_ok &= refusals_of('review', sid, context={'holder': 'worker-a', 'reviewer': 'reviewer-b'}) \
                    == expected_at('review', sid)
            # Every launching station asks every scenario's question: no scenario reaches an effect.
            named_ok &= all(expected_at(st, sid) for st in ('direct_execution', 'build', 'review', 'publication')
                            for sid in SCENARIOS if sid != 'VELDO-9106')
            named_ok &= gate.decide('build', 'VELDO-9106', context={'holder': 'worker-a'},
                                    ticket=tickets['VELDO-9106'])['eligible']
            named_ok &= refusals_of('review', 'VELDO-9106', context={'holder': 'worker-a', 'reviewer': 'builder-a'}) \
                == {'reviewer_not_independent'}
            named_ok &= refusals_of('build', 'VELDO-9106', context={'holder': 'worker-z'}) == {'missing_authority:claim'}
            # Canonical clock uncertainty stays a named refusal, never contention or permission.
            unit('VELDO-9160')
            claim('VELDO-9160')
            held = json.loads(writer.execute('SELECT data FROM entities WHERE id=?',
                                             (CLM.claim_id(REPOSITORY, 'VELDO-9160'),)).fetchone()[0])
            ahead = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + 3600))
            put(CLM.claim_id(REPOSITORY, 'VELDO-9160'), 'claim', dict(held, heartbeat_at=ahead))
            named_ok &= refusals_of('build', 'VELDO-9160', context={'holder': 'worker-a'}) == {'clock_uncertain'}
            observed['station_refusals'] = {
                st: {sid: sorted(gate.decide(st, sid, context={'holder': 'worker-a', 'reviewer': 'reviewer-b'})['refusals'])
                     for sid in SCENARIOS} for st in EL.FLOOR_STATIONS}
            observed['launches']['plan_run_check_clear'] = sorted(s for s, rc in run_checks.items() if rc == 0)
            observed['launches']['executor_builds'] = list(hooks.builds)
            check('eligibility/named-refusals', named_ok)

        with region('eligibility/entry-dispatch-build'):
            hooks, before = Hooks(), len(receiver)
            disp = DSP.Dispatcher(repo_root=str(base), hooks=hooks, eligibility=gate, calls=calls, worker_id='worker-a')
            built = {sid: disp.dispatch(dict(kind='build', spec=sid, holder='worker-a', dispatch='d-' + sid))
                     for sid in SCENARIOS}
            restore()
            # The build station's own question: a worker that does not hold the claim builds nothing,
            # although direct execution (which asks no claim question) would let it through.
            unclaimed = attempt(lambda: disp.dispatch(dict(kind='build', spec='VELDO-9106', holder='worker-z',
                                                           dispatch='d-VELDO-9106')))
            restore()
            build_calls = receiver[before:]
            observed['launches']['dispatch_builds'] = list(hooks.builds)
            check('eligibility/entry-dispatch-build',
                   hooks.builds == ['VELDO-9106'] and built['VELDO-9106']['ok']
                   and all(built[s]['halted_at'] == 'eligibility' for s in SCENARIOS if s != 'VELDO-9106')
                   and unclaimed['refusals'] == ['missing_authority:claim']
                   and [(a, i, c) for a, i, c, _ in build_calls] == [('claude_code', 'build-VELDO-9106', True)])

        with region('eligibility/entry-dispatch-review'):
            reviewer, lander, before = Reviewer(), Lander(), len(receiver)
            disp = DSP.Dispatcher(repo_root=str(base), reviewer=reviewer, lander=lander, eligibility=gate,
                                  calls=calls, worker_id='worker-a')
            reviewed = {sid: disp.dispatch(dict(kind='review', spec=sid, holder='worker-a', dispatch='d-' + sid))
                        for sid in SCENARIOS}
            restore()
            observed['launches']['dispatch_reviews'] = list(reviewer.reviews)
            check('eligibility/entry-dispatch-review',
                   reviewer.reviews == ['VELDO-9106'] and reviewed['VELDO-9106']['landed']
                   and [i for _, i, c, _ in receiver[before:] if c] == ['review-VELDO-9106', 'review-more-VELDO-9106']
                   and all(reviewed[s]['state'] == 'refused' for s in SCENARIOS if s != 'VELDO-9106'))

        with region('eligibility/entry-publication'):
            lander = Lander()
            disp = DSP.Dispatcher(repo_root=str(base), lander=lander, eligibility=gate, calls=calls, worker_id='worker-a')
            for sid in SCENARIOS:
                disp._land(dict(kind='review', spec=sid, holder='worker-a'))
            observed['launches']['publication_lands'] = list(lander.lands)
            check('eligibility/entry-publication', lander.lands == ['VELDO-9106'])

        with region('eligibility/enrolled-entry-stops'):
            # An enrolled repository with no eligibility wired stops by name at every entry; nothing runs.
            binding = Path(EL.E.binding_path(str(base)))
            binding.parent.mkdir(parents=True, exist_ok=True)
            binding.write_text('{}')
            stops_seen, hooks = [], Hooks()

            def stopped(fn):
                try:
                    fn()
                except EL.Stopped as error:
                    stops_seen.append(error.reason)
                    return True
                return False

            with contextlib.redirect_stdout(io.StringIO()):
                enrolled_ok = all(stopped(fn) for fn in (
                    lambda: FR.claimable(repo_root=str(base), claims_root=str(claims)),
                    lambda: WK.WorkLoop('worker-a', [], Counter(), repo_root=str(base), claims_root=str(claims)).run(),
                    lambda: PL.cmd_run_check(plan_path, 'VELDO-9106'),
                    lambda: EX.Executor(hooks).run('VELDO-9106', stop_after='proof'),
                    lambda: DSP.Dispatcher(repo_root=str(base), hooks=hooks, reviewer=Reviewer()).dispatch(
                        dict(kind='review', spec='VELDO-9106')),
                    lambda: DSP.Dispatcher(repo_root=str(base), hooks=hooks, eligibility=gate).dispatch(
                        dict(kind='build', spec='VELDO-9106', holder='worker-a')),
                ))
            binding.unlink()
            restore()
            check('eligibility/enrolled-entry-stops',
                   enrolled_ok and stops_seen == ['eligibility_required'] * 5 + ['reservation_required']
                   and hooks.builds == [])

        with region('eligibility/stale-input'):
            # --- AC2: every later station validates the ticket's consumed inputs ---------------------
            put('VELDO-9110', 'execution_unit', dict(state='DONE', repository_uuid=REPOSITORY, revision=1))
            landed('VELDO-9110')
            unit('VELDO-9107', depends=('VELDO-9110',))
            unit('VELDO-9108')
            spec('VELDO-9107', lane='standalone')
            spec('VELDO-9108', lane='standalone')
            for sid in ('VELDO-9107', 'VELDO-9108'):
                claim(sid)
                dispatch_slot(sid)
            ctx = {'holder': 'worker-a', 'reviewer': 'reviewer-b'}
            selected = {sid: gate.decide('selection', sid) for sid in ('VELDO-9107', 'VELDO-9108')}
            fresh_ok = all(gate.decide(st, sid, context=ctx, ticket=t)['eligible']
                           for sid, t in selected.items() for st in ('claim', 'build', 'review', 'publication'))
            project_before = version('project:p1')
            # A withdrawn prerequisite (its landing receipt superseded) and a re-accepted authority input
            # whose predicate still holds: only the version/digest check can see the second one.
            withdrawn = json.loads(writer.execute('SELECT data FROM entities WHERE id=?',
                                                  ('receipt:revision_landed:VELDO-9110:1:0',)).fetchone()[0])
            put('receipt:revision_landed:VELDO-9110:1:0', 'completion_receipt', dict(withdrawn, superseded_by='withdrawal'))
            put('admission:VELDO-9108', 'admission', dict(unit='VELDO-9108', state='accepted', scope_digest='sha256:scope'))
            expected_stale = {'VELDO-9107': 'stale_input:receipts/VELDO-9110', 'VELDO-9108': 'stale_input:admission'}
            hooks, reviewer, lander, before = Hooks(), Reviewer(), Lander(), len(receiver)
            disp = DSP.Dispatcher(repo_root=str(base), hooks=hooks, reviewer=reviewer, lander=lander,
                                  eligibility=gate, calls=calls, worker_id='worker-a')
            stale_ok = fresh_ok and version('project:p1') == project_before
            for sid, ticket in selected.items():
                u = dict(spec=sid, holder='worker-a', dispatch='d-' + sid, eligibility=ticket)
                outcomes = [attempt(lambda: disp.dispatch(dict(u, kind='build'))),
                            attempt(lambda: disp.dispatch(dict(u, kind='review'))),
                            attempt(lambda: disp._land(u, ticket))]
                outcomes.append(gate.decide('claim', sid, ticket=ticket))
                stale_ok &= all(expected_stale[sid] in o.get('refusals', []) for o in outcomes)
                observed['stale_refusals'][sid] = [o.get('refusals') for o in outcomes]
            stale_ok &= gate.decide('build', 'VELDO-9108', context=ctx)['eligible']
            stale_ok &= hooks.builds == [] and reviewer.reviews == [] and lander.lands == [] and receiver[before:] == []
            restore()
            check('eligibility/stale-input', stale_ok)

        with region('completion/readers-agree', 'completion/consumers-from-call-sites'):
            # --- AC3: every completion consumer reads the same four facts from real receipts ----------
            put('VELDO-9120', 'execution_unit', dict(state='BUILT', repository_uuid=REPOSITORY, revision=1))
            receipt('attempt_finished', 'VELDO-9120', 1)
            put('VELDO-9121', 'execution_unit', dict(state='REVIEWED', repository_uuid=REPOSITORY, revision=1))
            receipt('attempt_finished', 'VELDO-9121', 1)
            receipt('artifact_accepted', 'VELDO-9121', 1)
            put('VELDO-9122', 'execution_unit', dict(state='DONE', repository_uuid=REPOSITORY, revision=1))
            landed('VELDO-9122')
            put('VELDO-9123', 'execution_unit', dict(state='DONE', repository_uuid=REPOSITORY, revision=2))
            landed('VELDO-9123', revision=1)
            put('VELDO-9124', 'execution_unit', dict(state='DONE', repository_uuid=REPOSITORY, revision=1))
            landed('VELDO-9124')
            receipt('objective_satisfied', 'VELDO-9124', 1)
            put('VELDO-9125', 'execution_unit', dict(state='DONE', repository_uuid=REPOSITORY, revision=1))
            receipt('attempt_finished', 'VELDO-9125', 1)
            receipt('revision_landed', 'VELDO-9125', 1, publication_receipt={'unit_id': 'VELDO-9125'})
            deps = ['VELDO-912%d' % n for n in range(6)]
            for n, dep in enumerate(deps):
                # The checkout says shipped, and 9120/9121 carry a manifest and a passing verdict.
                spec(dep, status='shipped', lane='standalone')
                spec('VELDO-913%d' % n, depends=(dep,), lane='standalone')
                unit('VELDO-913%d' % n, plan=None, depends=(dep,))
            for dep in ('VELDO-9120', 'VELDO-9121'):
                bundle = base / 'proof' / dep
                bundle.mkdir(parents=True)
                (bundle / 'manifest.json').write_text(json.dumps({'spec_id': dep, 'produced_at': '2026-09-23T00:00:00Z'}))
                (bundle / 'verdict.json').write_text(json.dumps({'verdict': 'pass', 'findings': []}))
            expected_facts = {
                'VELDO-9120': (True, False, False, False), 'VELDO-9121': (True, True, False, False),
                'VELDO-9122': (True, True, True, False), 'VELDO-9123': (False, False, False, False),
                'VELDO-9124': (True, True, True, True), 'VELDO-9125': (True, False, False, False),
            }
            program = base / 'fresh_reader.py'
            program.write_text('\n'.join([
                'import importlib.util, json, sys',
                'from pathlib import Path',
                'base, db, domain, repository = sys.argv[1:5]',
                'deps = sys.argv[5:]',
                'def load(name):',
                '    spec = importlib.util.spec_from_file_location("fresh_" + name, Path(base) / ".veldo" / (name + ".py"))',
                '    module = importlib.util.module_from_spec(spec)',
                '    spec.loader.exec_module(module)',
                '    return module',
                'S, EL, FR, PL, WS = (load(n) for n in ("control_store", "control_eligibility", "frontier", "plan", "work_state"))',
                'gate = EL.Gate(S, S.open_store(db, mode="r"), domain_uuid=domain, repository_uuid=repository)',
                'withheld = {h["spec"] for h in FR.withheld(repo_root=base, eligibility=gate)}',
                'plan = PL._status(gate)',
                'view = WS.completion_view(deps, root=base, eligibility=gate)',
                'dependents = {d: "VELDO-913" + d[-1] for d in deps}',
                'print(json.dumps({"reader": {d: gate.completion(d) for d in deps},',
                '                  "frontier": {d: dependents[d] not in withheld for d in deps},',
                '                  "plan": {d: plan.get(d) == "shipped" for d in deps},',
                '                  "work_state": view,',
                '                  "eligibility": {d: gate.decide("selection", dependents[d])["eligible"] for d in deps}}))',
            ]))
            proc = subprocess.run([sys.executable, '-B', str(program), str(base), str(db), DOMAIN, REPOSITORY] + deps,
                                  capture_output=True, text=True, timeout=60)
            fresh = json.loads(proc.stdout) if proc.returncode == 0 else None
            observed['fresh_reader'] = fresh
            readers_ok = fresh is not None
            if fresh:
                landed_expected = {d: expected_facts[d][2] for d in deps}
                readers_ok &= {d: tuple(fresh['reader'][d][f] for f in EL.CC.FACT_ORDER) for d in deps} == expected_facts
                for consumer in ('frontier', 'plan', 'eligibility'):
                    readers_ok &= fresh[consumer] == landed_expected
                view = fresh['work_state']
                readers_ok &= {d: view[d]['facts']['revision_landed'] for d in deps} == landed_expected
                # Proof accepted (manifest plus passing verdict) is reported and never read as landed.
                readers_ok &= view['VELDO-9120']['proof_accepted'] is True and view['VELDO-9121']['proof_accepted'] is True
            check('completion/readers-agree', readers_ok)
            check('completion/consumers-from-call-sites', consumers == set(EL.COMPLETION_CONSUMERS))

        with region('reservations/forbidden-call-observation'):
            # --- AC4: every build and review subscription call checks usage caps before launch --------
            CASES = [(st, a, b) for st in EL.CALL_STATIONS for a in RT.ADAPTERS for b in RT.ADAPTERS[a]]
            paths_ok = len(CASES) == 12 and set(RT.ADAPTERS) == {'claude_code', 'codex'}
            forbidden_ok = True
            for n, scope in enumerate(RES.SCOPES):
                sid = 'VELDO-914%d' % n
                unit(sid)
                claim(sid)
                dispatch_slot(sid, account='acct-%d' % n, project='proj-%d' % n, caps={scope: {'invocations': len(CASES)}})
                before = len(receiver)
                for rnd in ('allowed', 'over'):
                    for st, adapter, boundary in CASES:
                        ticket = gate.decide(st, sid, context=ctx)
                        handle = calls.handle(st, sid, 'd-' + sid, context=ctx, ticket=ticket)
                        ident = '%s-%s-%s-%s-%s' % (sid, rnd, st, adapter, boundary)
                        try:
                            handle.invoke(adapter, boundary, ident, 10, CONFIG, now=tick())
                            outcome = 'launched'
                        except EL.Refused as error:
                            outcome = error.code
                        wanted = 'launched' if rnd == 'allowed' else 'usage_cap:%s:invocations' % scope
                        forbidden_ok &= outcome == wanted
                seen = receiver[before:]
                forbidden_ok &= len(seen) == len(CASES) and all(c and tools == ['configured-tool'] for _, _, c, tools in seen)
                forbidden_ok &= all('-allowed-' in i for _, i, _, _ in seen)
            check('reservations/forbidden-call-observation', paths_ok and forbidden_ok)

        with region('reservations/unknown-usage-retained'):
            # Unknown usage is retained: an unreported call keeps later calls from launching.
            unit('VELDO-9150')
            claim('VELDO-9150')
            dispatch_slot('VELDO-9150', account='acct-u', project='proj-u', caps={'unit': {'tokens': 5}})
            before = len(receiver)
            handle = calls.handle('review', 'VELDO-9150', 'd-VELDO-9150', context=ctx,
                                  ticket=gate.decide('review', 'VELDO-9150', context=ctx))
            handle.invoke('codex', 'initial', 'u-initial', 10, CONFIG, now=tick())
            outcomes = []
            for boundary in ('follow_on', 'retry'):
                try:
                    handle.invoke('codex', boundary, 'u-' + boundary, 10, CONFIG, now=tick())
                    outcomes.append('launched')
                except EL.Refused as error:
                    outcomes.append(error.code)
            reservations.report('u-final', 'u-initial', 1, dict(invocations=1, wall_seconds=3, tokens=2, messages=1),
                                final=True, outcome='completed', now=tick())
            handle.invoke('codex', 'follow_on', 'u-after', 10, CONFIG, now=tick())
            check('reservations/unknown-usage-retained',
                   outcomes == ['unknown_allowance:tokens'] * 2
                   and [i for _, i, _, _ in receiver[before:]] == ['u-initial', 'u-after'])

        with region('eligibility/observations'):
            # Observability: every decision is recorded with identity, versions, outcome and taxonomy.
            status = gate.status()
            obs_ok = status['accepted'] > 0 and status['refused'] > 0 and 'VELDO-9101' in status['pending']
            obs_ok &= all({'operation', 'unit', 'domain_uuid', 'repository_uuid', 'accepted_inputs', 'outcome',
                           'refusals', 'taxonomy', 'decision_id'} <= set(e) for e in gate.observations)
            obs_ok &= all(t != 'unknown_outcome' or 'clock_uncertain' in ' '.join(e['refusals'])
                          or any(r.startswith(('unknown_', 'usage_refused')) for r in e['refusals'])
                          for e in gate.observations for t in e['taxonomy'])
            obs_ok &= any(o['outcome'] == 'refused' and o['refusal'].startswith('usage_cap') for o in calls.observations)
            observed['gate_status'] = status
            observed['receiver'] = [list(r) for r in receiver]
            observed['call_refusals'] = sorted({o['refusal'] for o in calls.observations if o['outcome'] == 'refused'})
            observed['decision_sample'] = [e for e in gate.observations if e['unit'] == 'VELDO-9105'][:2]
            check('eligibility/observations', obs_ok)
        # One row per region saying it ran to its end: a driven mutation must red its named row by
        # a failed assertion while that row's own region still completes.
        for first in regions:
            check('ran/' + first, first not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V52_OBSERVED'] = observed
        reader.close()
        observer.close()
        writer.close()


_v52_started = __import__('time').monotonic()
_v52_suite()
_V52_SECONDS = __import__('time').monotonic() - _v52_started
