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
        'git_process.py': ROOT / ".veldo" / "git_process.py",
        'dispatch.py': ROOT / ".veldo" / "dispatch.py",
        'work.py': ROOT / ".veldo" / "work.py",
        'work_state.py': ROOT / ".veldo" / "work_state.py",
        'frontier.py': ROOT / ".veldo" / "frontier.py",
        'plan.py': ROOT / ".veldo" / "plan.py",
        'executor.py': ROOT / ".veldo" / "executor.py",
        'runstatus.py': ROOT / ".veldo" / "runstatus.py",
    }
    # The front door the production-entry row runs as a real process in the enrolled fixture.
    FRONT_DOOR = ROOT / "bin" / "veldo"
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
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
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
        CONFIG = {'mcp_servers': ['configured'], 'tools': ['configured-tool']}
        clock = [100.0]

        def tick():
            clock[0] += 1
            return clock[0]

        # The runner's calls: every station dispatch reserves its own worker slot under this
        # runner's subscription account and the unit's accepted project (p1), before any call.
        calls = EL.StationCalls(gate, guards, account='acct-floor', clock=tick)
        CEILING = dict(capacity=50, invocations=100, wall_seconds=10000)
        reservations.configure('ceiling-account-acct-floor', 'account', 'acct-floor', CEILING, now=tick())
        reservations.configure('ceiling-project-p1', 'project', 'p1', CEILING, now=tick())

        def ceilings(tag, sid, account='acct-floor', project='p1'):
            for scope, subject in zip(RES.SCOPES, (account, project, sid)):
                reservations.configure('ceiling-%s-%s-%s' % (tag, scope, subject), scope, subject, CEILING, now=tick())

        def observe_effect(fn):
            # What an entry did, or the named stop or refusal it raised: a raise is an observation
            # the row asserts on, so the row fails by its assertion and its region still completes.
            try:
                return ('ok', fn())
            except Exception as error:  # noqa: BLE001 - recorded, then asserted
                name = getattr(error, 'reason', None) or getattr(error, 'code', None) or str(error)
                return ('raised', '%s:%s' % (type(error).__name__, name))

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
            # Direct execution of the valid unit reaches its build through a reserved handle: the claim
            # and the ceilings are what that build's call needs at its provider_request boundary, which
            # every launch is decided at before it is entered. Every scenario is claimed and has its
            # ceilings, so only the station decision can hold back a unit whose defect that boundary
            # does not ask about (a draft plan, an open decision, an unresolved dependency).
            for sid in SCENARIOS:
                claim(sid)
                ceilings('exec-' + sid, sid)

            class ExecHooks(Hooks):
                def build(self, spec, calls=None):
                    self.builds.append(spec['id'])
                    if calls is not None:
                        calls.invoke('claude_code', 'initial', 'exec-build-' + spec['id'], 10, CONFIG, now=tick())
                    return {'ok': True, 'commit': 'c', 'evidence': {}}

            hooks, before = ExecHooks(), len(receiver)
            ran_exec = {sid: observe_effect(lambda: EX.Executor(hooks, eligibility=gate, calls=calls, context={
                'holder': 'worker-a'}).run(sid, stop_after='proof')) for sid in SCENARIOS}
            halted = {sid: r[1] if r[0] == 'ok' else {'state': r[1], 'halted_at': None} for sid, r in ran_exec.items()}
            check('eligibility/entry-executor',
                   hooks.builds == ['VELDO-9106'] and halted['VELDO-9106']['state'] == 'built'
                   and all(halted[s]['halted_at'] == EX.ELIGIBILITY_STEP for s in SCENARIOS if s != 'VELDO-9106')
                   and [(a, i, c) for a, i, c, _ in receiver[before:]] == [('claude_code', 'exec-build-VELDO-9106', True)])

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
            hooks, before, opened_before = Hooks(), len(receiver), len(calls.observations)
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
            # The dispatcher's own decision comes first: a refused unit is not even given a worker slot.
            opened = [o['unit'] for o in list(calls.observations)[opened_before:] if o.get('operation') == 'open_dispatch']
            observed['launches']['dispatch_builds'] = list(hooks.builds)
            check('eligibility/entry-dispatch-build',
                   hooks.builds == ['VELDO-9106'] and built['VELDO-9106']['ok']
                   and all(built[s]['halted_at'] == 'eligibility' for s in SCENARIOS if s != 'VELDO-9106')
                   and unclaimed.get('refusals') == ['missing_authority:claim'] and opened == ['VELDO-9106']
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
                'gate = EL.Gate(S, S.open_store(db, mode="r"), domain_uuid=domain, repository_uuid=repository, workspace=base)',
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

        # --- The six reproduced defects and the production entries (2026-09-23 review) -----------
        ctx_x = {'holder': 'worker-a'}

        class Direct(Hooks):
            """A direct run's builder and reviewer: each records whether it was handed a handle and,
            when it was, makes its subscription calls through it."""
            reviewer_identity = 'reviewer-b'

            def __init__(self, tag):
                super().__init__()
                self.tag, self.reviews = tag, []

            def build(self, spec, calls=None):
                self.builds.append((spec['id'], calls is not None))
                if calls is not None:
                    calls.invoke('claude_code', 'initial', '%s-build-%d' % (self.tag, len(self.builds)), 10,
                                 CONFIG, now=tick())
                return {'ok': True, 'commit': 'c', 'evidence': {}}

            def review(self, spec, proof, calls=None):
                self.reviews.append(calls is not None)
                if calls is not None:
                    n = len(self.reviews)
                    calls.invoke('codex', 'initial', '%s-review-%d' % (self.tag, n), 10, CONFIG, now=tick())
                    calls.invoke('codex', 'follow_on', '%s-review-more-%d' % (self.tag, n), 10, CONFIG, now=tick())
                return {'verdict': 'pass'}

            def merge_ready(self, spec, proof, verdict):
                return True, None

            def approve(self, spec, info):
                return {'decision': 'approved'}

        with region('eligibility/executor-station-decisions'):
            # DEFECT a. The direct executor launches its build and its review through the same station
            # decisions and reserved handles as the dispatcher, and without them stops by the same name.
            sid = 'VELDO-9106'
            bare = Direct('xa')
            unwired = observe_effect(lambda: EX.Executor(bare, eligibility=gate).run(sid))
            wired, before = Direct('xb'), len(receiver)
            full = observe_effect(lambda: EX.Executor(wired, eligibility=gate, calls=calls, context=ctx_x).run(sid))
            launched = [(a, c) for a, _, c, _ in receiver[before:]]
            producer = Direct('xc')
            producer.reviewer_identity = 'builder-a'
            same = observe_effect(lambda: EX.Executor(producer, eligibility=gate, calls=calls, context=ctx_x).run(sid))
            restore()
            observed['executor'] = {'unwired': list(unwired) if unwired[0] == 'raised' else unwired[1]['state'],
                                    'unwired_builds': list(bare.builds), 'unwired_reviews': list(bare.reviews),
                                    'wired_launches': launched,
                                    'producer_as_reviewer': same[1]['reason'] if same[0] == 'ok' else list(same)}
            check('eligibility/executor-station-decisions',
                   unwired == ('raised', 'Stopped:reservation_required') and bare.builds == [] and bare.reviews == []
                   and full[0] == 'ok' and full[1]['state'] == 'ready'
                   and wired.builds == [(sid, True)] and wired.reviews == [True]
                   and launched == [('claude_code', True), ('codex', True), ('codex', True)]
                   and same[0] == 'ok' and same[1]['halted_at'] == EX.ELIGIBILITY_STEP
                   and 'reviewer_not_independent' in (same[1]['reason'] or '')
                   and producer.builds == [(sid, True)] and producer.reviews == [])

        with region('eligibility/executor-rechecks-every-launch'):
            # DEFECT b. Every launch of a direct run first re-decides its station over the complete current
            # read set, against the last accepted decision as its ticket: an admission withdrawn during
            # review, or re-accepted with its predicate still true, stops cycle 2 before its build.
            sid = 'VELDO-9106'
            accepted = dict(unit=sid, state='accepted', scope_digest='sha256:scope')
            runs = {}
            for tag, moved in (('withdrawn', dict(accepted, state='withdrawn')), ('reaccepted', accepted)):
                class Moves(Direct):
                    def review(self, spec, proof, calls=None, moved=moved):
                        self.reviews.append(calls is not None)
                        put('admission:' + sid, 'admission', moved)
                        return {'verdict': 'fail'}

                hooks = Moves('xr-' + tag)
                runs[tag] = (hooks, observe_effect(lambda: EX.Executor(hooks, eligibility=gate, calls=calls, context=ctx_x).run(
                    sid, max_review_cycles=2)))
                put('admission:' + sid, 'admission', accepted)
            restore()
            recheck_ok = True
            for tag, code in (('withdrawn', 'missing_authority:admission'), ('reaccepted', 'stale_input:admission')):
                hooks, (kind, result) = runs[tag]
                recheck_ok &= (kind == 'ok' and hooks.builds == [(sid, True)] and hooks.reviews == [True]
                               and result['halted_at'] == EX.ELIGIBILITY_STEP and code in (result['reason'] or ''))
            observed['executor']['rechecks'] = {tag: {'builds': len(h.builds), 'outcome': r[1]['reason'] if r[0] == 'ok' else list(r)}
                                                for tag, (h, r) in runs.items()}
            check('eligibility/executor-rechecks-every-launch', recheck_ok)

        with region('eligibility/enrollment-git-error-stops'):
            # DEFECT c. A git error while determining enrollment stops by name; only a directory in which
            # Git's own discovery finds no repository at all is "not enrolled".
            binding = Path(EL.E.binding_path(str(base)))
            binding.parent.mkdir(parents=True, exist_ok=True)
            binding.write_text('{}')
            config = base / '.git' / 'config'
            healthy_config = config.read_bytes()
            try:
                config.write_bytes(healthy_config + b'\n[broken\n')
                broken = {'root': observe_effect(lambda: EL.gate_for(str(base), None)),
                          'subdirectory': observe_effect(lambda: EL.gate_for(str(base / 'specs'), None)),
                          'frontier': observe_effect(lambda: FR.claimable(repo_root=str(base), claims_root=str(claims)))}
            finally:
                config.write_bytes(healthy_config)
                binding.unlink()
            with tempfile.TemporaryDirectory(prefix='v52-plain-', dir=fast) as plain:
                unrepository = observe_effect(lambda: EL.enrolled(plain))
            # An enrollment that exists but cannot be READ is not an absent one.
            binding.parent.mkdir(parents=True, exist_ok=True)
            binding.write_text('{}')
            os.chmod(binding.parent, 0)
            try:
                unreadable = (observe_effect(lambda: EL.enrolled(str(base))) if os.geteuid() != 0
                              else ('raised', 'Stopped:enrollment_unanswerable'))
            finally:
                os.chmod(binding.parent, 0o755)
                binding.unlink()
            broken['unreadable'] = unreadable
            healthy = observe_effect(lambda: EL.gate_for(str(base), None))
            observed['enrollment_git_error'] = {k: [v[0], sorted(u['spec'] for u in v[1]) if k == 'frontier' and v[0] == 'ok'
                                                    else v[1]] for k, v in broken.items()}
            stop = ('raised', 'Stopped:enrollment_unanswerable')
            check('eligibility/enrollment-git-error-stops',
                   all(v == stop for v in broken.values()) and unrepository == ('ok', False) and healthy == ('ok', None))

        with region('completion/status-reader-agrees'):
            # DEFECT d. `veldo status` reads completion through the one reader plan status uses, and stops
            # by the same name where plan status stops.
            RS = load('v52_runstatus', mods / 'runstatus.py')
            text = base / 'specs' / 'VELDO-9106-fixture.md'
            text.write_text(text.read_text().replace('status: ready', 'status: shipped'))
            quiet = dict(runs_root=str(Path(directory) / 'runs'), events_path=str(Path(directory) / 'no-events.jsonl'),
                         control_db=str(Path(directory) / 'no-store.sqlite3'))
            binding = Path(EL.E.binding_path(str(base)))
            try:
                burn = observe_effect(lambda: RS._burndown(base, eligibility=gate))
                fm = PL.load_plan(plan_path)[1]
                plan_view = PL._status(gate)
                shipped = PL._shipped_set(fm, plan_view)
                # VELDO-0054: plan status reads decisions through the Gate, so veldo status must too.
                wanted = {w['spec']: PL.item_state(w, plan_view, shipped, PL._decision_blocks(fm, gate)) for w in PL._work(fm)}
                binding.parent.mkdir(parents=True, exist_ok=True)
                binding.write_text('{}')
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        plan_stop = observe_effect(lambda: PL.cmd_status(plan_path))
                    model = observe_effect(lambda: RS.status(root=base, **quiet))
                finally:
                    binding.unlink()
            finally:
                restore()
            items = ({i['spec']: i['state'] for p_ in burn[1] for i in p_['items']} if burn[0] == 'ok' else None)
            observed['status_reader'] = {'items': items, 'plan_items': wanted, 'plan_enrolled': list(plan_stop),
                                         'status_enrolled': model[1].get('burndown_stopped') if model[0] == 'ok' else list(model)}
            check('completion/status-reader-agrees',
                   burn[0] == 'ok' and items == wanted and items['VELDO-9106'] != 'shipped'
                   and items['VELDO-9104'].startswith('blocked: decision unresolved_decision:decision:9104')
                   and [p_['shipped'] for p_ in burn[1]] == [len(shipped)]
                   and plan_stop == ('raised', 'Stopped:eligibility_required')
                   and model[0] == 'ok' and model[1].get('burndown_stopped') == 'eligibility_required'
                   and model[1].get('burndown') == [])

        with region('reservations/work-loop-dispatch-identity'):
            # DEFECT e. The real path with nothing hand-built, WorkLoop -> Dispatcher -> executor ->
            # builder: the dispatcher reserves this dispatch's worker slot, and the builder's call launches.
            sid = 'VELDO-9106'
            handed = []

            class LoopHooks(Hooks):
                def build(self, spec, calls=None):
                    self.builds.append(spec['id'])
                    if calls is not None:
                        calls.invoke('claude_code', 'initial', 'loop-build-' + spec['id'], 10, CONFIG, now=tick())
                    return {'ok': True, 'commit': 'c', 'evidence': {}}

            class Seen(DSP.Dispatcher):
                def dispatch(self, unit):
                    handed.append(sorted(unit))
                    return super().dispatch(unit)

            hooks, before = LoopHooks(), len(receiver)
            disp = Seen(repo_root=str(base), hooks=hooks, eligibility=gate, calls=calls, worker_id='worker-a')
            drained = observe_effect(lambda: WK.WorkLoop('worker-a', [], disp, scope={'plan': 'PLAN-9001'}, repo_root=str(base),
                                                  claims_root=str(claims) + '-loop', eligibility=gate).run())
            restore()
            launched = [(a, i, c) for a, i, c, _ in receiver[before:]]
            records = reservations._records()
            call = [r for r in records.values() if r['type'] == 'invocation' and r['invocation'] == 'loop-build-' + sid]
            slot = [r for r in records.values() if r['type'] == 'worker' and call and r['dispatch'] == call[0]['dispatch']]
            observed['work_loop'] = {'handed_keys': handed, 'launched': launched,
                                     'slot_context': slot[0]['context'] if slot else None}
            check('reservations/work-loop-dispatch-identity',
                   drained[0] == 'ok' and hooks.builds == [sid] and handed and all('dispatch' not in keys for keys in handed)
                   and launched == [('claude_code', 'loop-build-' + sid, True)]
                   and len(slot) == 1 and slot[0]['retired']
                   and slot[0]['context'] == dict(domain=DOMAIN, repository=REPOSITORY, account='acct-floor',
                                                  project='p1', unit=sid))

        with region('reservations/dispatch-slot-retired'):
            # DEFECT g. A worker slot is opened only after every pre-launch decision passed, and retired when
            # the launch it was opened for returns, so a unit whose ceiling is ONE slot is dispatched again
            # and again. Its calls' exposure stays: an unreported call is retained as unknown usage.
            sid, one = 'VELDO-9170', dict(CEILING, capacity=1)
            unit(sid)
            claim(sid)
            spec_file = base / 'specs' / (sid + '-fixture.md')
            spec(sid, lane='standalone')
            ready_text = spec_file.read_text()
            reservations.configure('ceiling-unit-' + sid, 'unit', sid, one, now=tick())

            class Resolves(Hooks):
                """What each dispatch's builder did: `calls` says whether it was handed a handle."""
                def __init__(self, halt=None, invoke=True):
                    super().__init__()
                    self.halt, self.invoke = halt, invoke

                def resolve(self, s):
                    spec_view = super().resolve(s)
                    return dict(spec_view, status='review') if self.halt == 'resolve' else spec_view

                def run_check(self, spec_view):
                    if self.halt == 'recheck':
                        # An input the dispatcher's own decision consumed moves before the launch.
                        put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope'))
                    return (False, 'plan refuses') if self.halt == 'plan_check' else (True, 'checked')

                def build(self, spec_view, calls=None):
                    self.builds.append(spec_view['id'])
                    if calls is not None and self.invoke:
                        calls.invoke('claude_code', 'initial', 'slot-build-%d' % len(receiver), 10, CONFIG, now=tick())
                    return {'ok': True, 'commit': 'c', 'evidence': {}}

            def slots(s):
                return [r for r in reservations._records().values() if r['type'] == 'worker' and r['context']['unit'] == s]

            before, outcomes = len(receiver), {}
            for tag, hooks in (('resolve', Resolves('resolve')), ('plan_check', Resolves('plan_check')),
                               ('recheck', Resolves('recheck')), ('no-call', Resolves(invoke=False)),
                               ('first', Resolves()), ('second', Resolves())):
                disp = DSP.Dispatcher(repo_root=str(base), hooks=hooks, eligibility=gate, calls=calls, worker_id='worker-a')
                result = observe_effect(lambda: disp.dispatch(dict(kind='build', spec=sid, holder='worker-a')))
                spec_file.write_text(ready_text)
                outcomes[tag] = (result[1].get('halted_at') or result[1].get('status') if result[0] == 'ok'
                                 else list(result), list(hooks.builds), len(slots(sid)))
            launched = [i for _, i, c, _ in receiver[before:] if c]
            held = slots(sid)
            spent = reservations.balances('unit', sid)
            unknown = [r for r in reservations._records().values() if r['type'] == 'invocation' and r['invocation'] in launched]
            # A review station dispatch of the same one-slot unit, twice: each opens and retires its own slot.
            class Reviews(Reviewer):
                def review(self, spec_view, u, calls=None):
                    self.reviews.append(spec_view['id'])
                    if calls is not None:
                        calls.invoke('codex', 'initial', 'slot-review-%d' % len(receiver), 10, CONFIG, now=tick())
                    return {'verdict': 'pass', 'findings': []}

            reviewer, lander = Reviews(), Lander()
            disp = DSP.Dispatcher(repo_root=str(base), reviewer=reviewer, lander=lander, eligibility=gate, calls=calls,
                                  worker_id='worker-a')
            reviews = []
            for _ in range(2):
                reviews.append(observe_effect(lambda: disp.dispatch(dict(kind='review', spec=sid, holder='worker-a'))))
                spec_file.write_text(ready_text)
            # A direct run of another one-slot unit: its build's slot is retired before its review needs one.
            direct_sid = 'VELDO-9171'
            unit(direct_sid)
            claim(direct_sid)
            spec(direct_sid, lane='standalone')
            reservations.configure('ceiling-unit-' + direct_sid, 'unit', direct_sid, one, now=tick())
            direct = Direct('slot-direct')
            ran_direct = observe_effect(lambda: EX.Executor(direct, eligibility=gate, calls=calls, context=ctx_x).run(direct_sid))
            (base / 'specs' / (direct_sid + '-fixture.md')).unlink()
            spec_file.unlink()
            observed['slot_retirement'] = {
                'dispatches': outcomes, 'launched': launched, 'unit_balance': spent,
                'slots': [dict(retired=r['retired'], retirement=r.get('retirement')) for r in held],
                'calls': [dict(state=r['state'], unknown=r['unknown'], charge=r['charge']) for r in unknown],
                'reviews': [r[1].get('status') if r[0] == 'ok' else list(r) for r in reviews],
                'direct': ran_direct[1]['state'] if ran_direct[0] == 'ok' else list(ran_direct),
                'direct_slots': [r['retired'] for r in slots(direct_sid)]}
            check('reservations/dispatch-slot-retired',
                   # Every pre-launch halt reserves nothing; each launch holds one slot and retires it.
                   outcomes == {'resolve': ('resolve', [], 0), 'plan_check': ('plan_check', [], 0),
                                'recheck': ('eligibility', [], 0), 'no-call': ('review', [sid], 1),
                                'first': ('review', [sid], 2), 'second': ('review', [sid], 3)}
                   and len(launched) == 2 and len(held) == 3 and all(r['retired'] for r in held)
                   and sorted(r['retirement']['calls'] for r in held) == [0, 1, 1]
                   and spent['capacity'] == 0 and spent['invocations'] == 2 and spent['wall_seconds'] == 20
                   and len(unknown) == 2 and all(r['state'] == 'unknown' and r['unknown'] == ['tokens', 'messages']
                                                 for r in unknown)
                   and [r[1].get('status') if r[0] == 'ok' else r for r in reviews] == ['shipped', 'shipped']
                   and reviewer.reviews == [sid, sid] and len(slots(sid)) == 5 and all(r['retired'] for r in slots(sid))
                   and ran_direct[0] == 'ok' and ran_direct[1]['state'] == 'ready'
                   and direct.builds == [(direct_sid, True)] and direct.reviews == [True]
                   and [r['retired'] for r in slots(direct_sid)] == [True, True])

        with region('eligibility/provider-refusal-halts'):
            # A refusal at a launched call's own boundary (its usage reservation, or the provider_request
            # decision over an input that moved during the launch) ends the run as a NAMED halt, like
            # every other refusal, never a raised exception; the review station reports it as refused.
            capped, moved_sid = 'VELDO-9172', 'VELDO-9173'
            for s in (capped, moved_sid):
                unit(s)
                claim(s)
                spec(s, lane='standalone')
            reservations.configure('ceiling-unit-' + capped, 'unit', capped, dict(CEILING, invocations=0), now=tick())
            reservations.configure('ceiling-unit-' + moved_sid, 'unit', moved_sid, CEILING, now=tick())
            accepted_admission = dict(unit=moved_sid, state='accepted', scope_digest='sha256:scope')

            class Withdraws(Direct):
                def build(self, spec_view, calls=None):
                    put('admission:' + moved_sid, 'admission', dict(accepted_admission, state='withdrawn'))
                    return super().build(spec_view, calls=calls)

            before = len(receiver)
            capped_hooks, moved_hooks = Direct('prov-cap'), Withdraws('prov-moved')
            runs_p = {'direct-cap': observe_effect(lambda: EX.Executor(capped_hooks, eligibility=gate, calls=calls,
                                                                        context=ctx_x).run(capped, stop_after='proof')),
                      'direct-moved': observe_effect(lambda: EX.Executor(moved_hooks, eligibility=gate, calls=calls,
                                                                          context=ctx_x).run(moved_sid, stop_after='proof'))}
            put('admission:' + moved_sid, 'admission', accepted_admission)
            build_hooks = Direct('prov-dispatch')
            disp = DSP.Dispatcher(repo_root=str(base), hooks=build_hooks, reviewer=Reviewer(), lander=Lander(),
                                  eligibility=gate, calls=calls, worker_id='worker-a')
            runs_p['dispatch-build'] = observe_effect(lambda: disp.dispatch(dict(kind='build', spec=capped, holder='worker-a')))
            capped_file = base / 'specs' / (capped + '-fixture.md')
            capped_file.write_text(capped_file.read_text().replace('status: ready', 'status: review'))
            runs_p['dispatch-review'] = observe_effect(lambda: disp.dispatch(dict(kind='review', spec=capped, holder='worker-a')))
            review_status = FR.current_status(capped, str(base))
            for s in (capped, moved_sid):
                (base / 'specs' / (s + '-fixture.md')).unlink()
            summary = {name: (dict(state=r[1].get('state'), halted_at=r[1].get('halted_at'), reason=r[1].get('reason'),
                                   refusals=r[1].get('refusals')) if r[0] == 'ok' else list(r)) for name, r in runs_p.items()}
            observed['provider_refusal'] = dict(summary, review_status=review_status,
                                                launched=[i for _, i, c, _ in receiver[before:]])

            def halted_by(name, code):
                kind, result = runs_p[name]
                return (kind == 'ok' and result.get('halted_at') == EX.ELIGIBILITY_STEP
                        and code in (result.get('reason') or ''))

            check('eligibility/provider-refusal-halts',
                   halted_by('direct-cap', 'usage_cap:unit:invocations')
                   and runs_p['direct-cap'][1].get('state') == 'halted' and capped_hooks.builds == [(capped, True)]
                   and halted_by('direct-moved', 'missing_authority:admission') and moved_hooks.builds == [(moved_sid, True)]
                   and halted_by('dispatch-build', 'usage_cap:unit:invocations') and runs_p['dispatch-build'][1]['ok'] is False
                   and runs_p['dispatch-review'][0] == 'ok' and runs_p['dispatch-review'][1].get('state') == 'refused'
                   and runs_p['dispatch-review'][1].get('refusals') == ['usage_cap:unit:invocations']
                   and review_status == 'review' and receiver[before:] == []
                   and all(r['retired'] for r in reservations._records().values()
                           if r['type'] == 'worker' and r['context']['unit'] in (capped, moved_sid)))

        with region('eligibility/launch-decides-its-calls'):
            # r52b probe i. Direct execution asks no claim question, but every call a launched builder or
            # reviewer makes is decided at provider_request, which does. So a launch is first decided at
            # that boundary too: a claim taken by another holder during review stops cycle 2 BEFORE its
            # builder is entered, and a unit this run does not hold is never built at all.
            taken_sid, unheld_sid = 'VELDO-9174', 'VELDO-9175'
            for s in (taken_sid, unheld_sid):
                unit(s)
                spec(s, lane='standalone')
                reservations.configure('ceiling-unit-' + s, 'unit', s, CEILING, now=tick())
            claim(taken_sid)
            held_claim = CLM.claim_id(REPOSITORY, taken_sid)

            class TakenDuringReview(Direct):
                def review(self, spec_view, proof, calls=None):
                    self.reviews.append(calls is not None)
                    current = json.loads(writer.execute('SELECT data FROM entities WHERE id=?', (held_claim,)).fetchone()[0])
                    put(held_claim, 'claim', dict(current, holder='worker-z', generation=2))
                    return {'verdict': 'fail'}

            taken, unheld = TakenDuringReview('calls-taken'), Direct('calls-unheld')
            runs_c = {'taken': observe_effect(lambda: EX.Executor(taken, eligibility=gate, calls=calls, context=ctx_x).run(
                          taken_sid, max_review_cycles=2)),
                      'unheld': observe_effect(lambda: EX.Executor(unheld, eligibility=gate, calls=calls, context=ctx_x).run(
                          unheld_sid, stop_after='proof'))}
            for s in (taken_sid, unheld_sid):
                (base / 'specs' / (s + '-fixture.md')).unlink()
            observed['launch_calls'] = {name: (dict(halted_at=r[1].get('halted_at'), reason=r[1].get('reason'))
                                               if r[0] == 'ok' else list(r)) for name, r in runs_c.items()}
            observed['launch_calls'].update(taken_builds=len(taken.builds), unheld_builds=len(unheld.builds))

            def refused_before_build(name, code):
                kind, result = runs_c[name]
                return (kind == 'ok' and result.get('halted_at') == EX.ELIGIBILITY_STEP
                        and (result.get('reason') or '').startswith('eligibility refused before build')
                        and code in result['reason'])

            check('eligibility/launch-decides-its-calls',
                   refused_before_build('taken', 'missing_authority:claim') and taken.builds == [(taken_sid, True)]
                   and taken.reviews == [True]
                   and refused_before_build('unheld', 'missing_authority:claim') and unheld.builds == [])

        with region('completion/landed-units-not-reoffered'):
            # DEFECT f. Every lane asks the one completion reader, never the front matter: a landed unit is
            # offered for neither a build nor a review, whatever its file still says.
            extra = (('VELDO-9161', 'ready'), ('VELDO-9162', 'review'), ('VELDO-9163', 'ready'))
            for sid, st in extra:
                unit(sid, plan=None)
                spec(sid, status=st, lane='standalone')
            landed('VELDO-9161')
            landed('VELDO-9162')
            try:
                offers = observe_effect(lambda: {u['spec']: u['kind'] for u in FR.claimable(
                    repo_root=str(base), claims_root=str(claims) + '-landed', eligibility=gate)})
            finally:
                for sid, _ in extra:
                    (base / 'specs' / (sid + '-fixture.md')).unlink()
            mine = ({k: v for k, v in offers[1].items() if k in dict(extra)} if offers[0] == 'ok' else list(offers))
            observed['landed_offers'] = mine
            check('completion/landed-units-not-reoffered',
                   mine == {'VELDO-9163': 'build'} and gate.landed('VELDO-9161') and gate.landed('VELDO-9162'))

        with region('eligibility/production-entries-build-the-gate'):
            # Every command-line entry in an enrolled repository builds its Gate from the workspace's own
            # signed enrollment binding, verified against what the HOST trusts (never a file the workspace
            # carries), and then reaches the next named boundary instead of eligibility_required.
            host = Path(directory) / 'host'
            (host / 'veldo').mkdir(parents=True)
            key = host / 'enroll_key'
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'dmitry', '-f', str(key)],
                           check=True, capture_output=True)
            key_type, key_blob = (host / 'enroll_key.pub').read_text().split()[:2]
            signers = host / 'enrollment_signers'
            signers.write_text('dmitry namespaces="veldo-enrollment" %s %s\n' % (key_type, key_blob))

            def enrollment_sign(message):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', 'veldo-enrollment'],
                                      input=message, capture_output=True, check=True).stdout.decode()

            trust_file = host / 'veldo' / 'host_trust.json'
            trust_file.write_text(json.dumps({'schema': 'veldo.host_trust/v1', 'host_identity': 'host-52',
                                              'enrollment_signers': str(signers)}))
            (Path(directory) / 'untrusted-host').mkdir()
            GP.run(['git', '-C', str(base), 'commit', '-q', '--allow-empty', '-m', 'enrolled fixture'], check=True,
                   capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
            EL.E.enroll(str(base), DOMAIN, 'store-52', str(db), 'host-52', 1, enrollment_sign, 'dmitry',
                        '2026-09-23T00:00:00Z', repository_uuid=REPOSITORY)
            binding = Path(EL.E.binding_path(str(base)))
            (base / 'bin').mkdir(exist_ok=True)
            shutil.copyfile(FRONT_DOOR, base / 'bin' / 'veldo')
            text = base / 'specs' / 'VELDO-9102-fixture.md'
            text.write_text(text.read_text().replace('status: ready', 'status: shipped'))
            env = {k: v for k, v in os.environ.items() if not k.startswith(('VELDO_', 'GIT_'))}
            commands = {
                'executor': [sys.executable, '-B', str(mods / 'executor.py'), 'VELDO-9106'],
                'plan': [sys.executable, '-B', str(mods / 'plan.py'), 'run-check', plan_path, 'VELDO-9101'],
                'work': [sys.executable, '-B', str(base / 'bin' / 'veldo'), 'work'],
                'status': [sys.executable, '-B', str(mods / 'runstatus.py'), 'status', '--json'],
                'untrusted': [sys.executable, '-B', str(mods / 'executor.py'), 'VELDO-9106'],
            }
            homes = dict.fromkeys(commands, str(host), ) | {'untrusted': str(Path(directory) / 'untrusted-host')}
            try:
                procs = {name: subprocess.Popen(argv, cwd=str(base), env=dict(env, XDG_CONFIG_HOME=homes[name]),
                                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                         for name, argv in commands.items()}
                ran = {}
                for name, proc in procs.items():
                    out, err = proc.communicate(timeout=120)
                    ran[name] = (proc.returncode, out, err)
                trust = observe_effect(lambda: EL.load_host_trust(str(trust_file)))
                built = observe_effect(lambda: EL.entry_gate(str(base), trust=trust[1]))
                decided = (observe_effect(lambda: {s: built[1].decide('selection', s)['refusals'] for s in ('VELDO-9101', 'VELDO-9106')})
                           if built[0] == 'ok' else built)
                genuine = binding.read_text()
                forged = json.loads(genuine)
                forged['domain_uuid'] = 'domain-elsewhere'
                binding.write_text(json.dumps(forged))
                tampered = observe_effect(lambda: EL.entry_gate(str(base), trust=trust[1]))
                binding.write_text(genuine)
                moved = observe_effect(lambda: EL.entry_gate(str(base), trust=EL.HostTrust('host-other', str(signers))))
            finally:
                for path in (binding, Path(EL.E.clone_uuid_path(str(base)))):
                    if path.exists():
                        path.unlink()
                restore()

            def said(name, words):
                code, out, err = ran[name]
                return words in out + err

            try:
                status_model = json.loads(ran['status'][1])
            except ValueError:
                status_model = {}
            observed['production_entries'] = {name: {'exit': code, 'said': (out + err).strip().splitlines()[-1:]}
                                              for name, (code, out, err) in ran.items()}
            check('eligibility/production-entries-build-the-gate',
                   ran['executor'][0] == 2 and said('executor', 'stopped: reservation_required')
                   and ran['plan'][0] == 1 and said('plan', 'eligibility refused: missing_authority:admission')
                   and ran['work'][0] == 2 and said('work', 'stopped: authority_required')
                   and ran['status'][0] == 0 and 'burndown_stopped' not in status_model
                   and [p_['shipped'] for p_ in status_model.get('burndown', [])] == [0]
                   and ran['untrusted'][0] == 2 and said('untrusted', 'stopped: host_trust_required')
                   and not any(said(name, 'eligibility_required') for name in ran)
                   and decided == ('ok', {'VELDO-9101': ['missing_authority:admission'], 'VELDO-9106': []})
                   and tampered == ('raised', 'Stopped:enrollment_refused:signature_invalid')
                   and moved == ('raised', 'Stopped:enrollment_refused:host_binding_stale'))
            if built[0] == 'ok':
                built[1].conn.close()

        with region('eligibility/host-trust-outside-workspace'):
            # DEFECT h. What the HOST trusts must be the host's: an allowed-signers path inside the checked
            # workspace, a relative one (resolved against wherever the process runs, the workspace), or a
            # host path that is a symlink into the workspace is refused by name, and the genuine signer's
            # key in that file changes nothing. The host's own file, reached through a symlink, is accepted.
            GP.run(['git', '-C', str(base), 'commit', '-q', '--allow-empty', '-m', 'host trust fixture'], check=True,
                   capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
            EL.E.enroll(str(base), DOMAIN, 'store-52', str(db), 'host-52', 1, enrollment_sign, 'dmitry',
                        '2026-09-23T00:00:00Z', repository_uuid=REPOSITORY)
            carried = base / '.veldo' / 'keys' / 'allowed_signers'
            carried.parent.mkdir(parents=True, exist_ok=True)
            carried.write_text(signers.read_text())
            into_workspace, to_host = host / 'signers-into-workspace', host / 'signers-to-host'
            into_workspace.symlink_to(carried)
            to_host.symlink_to(signers)
            cases_h = {'inside': str(carried), 'relative': '.veldo/keys/allowed_signers',
                       'symlink-into-workspace': str(into_workspace), 'git-directory': None,
                       'host': str(signers), 'host-through-symlink': str(to_host)}
            in_git = Path(EL.E.git_common_dir(str(base))) / 'veldo-allowed-signers'
            in_git.write_text(signers.read_text())
            cases_h['git-directory'] = str(in_git)
            trusted, cwd = {}, os.getcwd()
            try:
                os.chdir(str(base))
                for name, path in cases_h.items():
                    record = host / ('trust-%s.json' % name)
                    record.write_text(json.dumps({'schema': 'veldo.host_trust/v1', 'host_identity': 'host-52',
                                                  'enrollment_signers': path}))
                    got = observe_effect(lambda: EL.entry_gate(str(base), trust=EL.load_host_trust(str(record))))
                    trusted[name] = ('ok', 'Gate') if got[0] == 'ok' else got
                    if got[0] == 'ok':
                        got[1].conn.close()
            finally:
                os.chdir(cwd)
                for path in (binding, Path(EL.E.clone_uuid_path(str(base))), in_git, into_workspace, to_host, carried):
                    if os.path.lexists(str(path)):
                        path.unlink()
                carried.parent.rmdir()
            observed['host_trust'] = trusted
            inside = ('raised', 'Stopped:host_trust_refused:signers_inside_workspace')
            check('eligibility/host-trust-outside-workspace',
                   trusted == {'inside': inside, 'relative': ('raised', 'Stopped:host_trust_refused:signers_not_absolute'),
                               'symlink-into-workspace': inside, 'git-directory': inside,
                               'host': ('ok', 'Gate'), 'host-through-symlink': ('ok', 'Gate')})

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
