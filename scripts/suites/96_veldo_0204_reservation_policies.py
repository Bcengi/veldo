"""VELDO-0204: the factory provisions the reservation policy of every registered account, every project and every
engineering unit from the owner's configuration, offline on setup's connection and in each pass of the service.

Run: python3 scripts/selftest.py --suite 96_veldo_0204_reservation_policies

Only shared ROOT and expect are consumed. proof/VELDO-0204/host.py lays a fresh host down with VELDO-0139's setup
steps (VELDO-0088's production-setup fixture), holds the store's lock as setup does, and writes the owner's
configuration through its production writers: the `authority` principal's reservation_service enrollment, signed
project activations with different budgets, proj-a's own team (accepted through the owner's settled amendment),
the default team through VELDO-0203's offline owner revision, three accounts of two engines, and units in both
projects, one with a team assignment naming a specialist build role. control_service's Service, factory loop,
Line, Runner and account pool run in this process on the host's connection with that lock: a signed packet through
Service.apply wakes a pass, as serve's loop does. The workers are a plain protocol process: no engine, no model,
no login and no credential. Every row is reported once and fails by assertion.
"""


def _v204_suite():
    import ast
    import contextlib
    import importlib.util
    import json
    from pathlib import Path
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_reservation_policies.py': ROOT / ".veldo" / "control_reservation_policies.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
        'control_account_pool.py': ROOT / ".veldo" / "control_account_pool.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    names = ('derive/values', 'fresh/dispatch', 'rerun/unchanged', 'source/project', 'source/team', 'source/account',
             'source/unit', 'source/windows', 'source/absent', 'lock/second-connection', 'service/start',
             'service/added', 'service/team', 'service/pm-assigned', 'service/rerun', 'refuse/missing-source',
             'refuse/principal', 'census/writer')
    rows = {name: [] for name in names}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    @contextlib.contextmanager
    def region(*row_names):
        try:
            yield
        except Exception as exc:  # noqa: BLE001 - a raise reds its rows by assertion, never skips them
            for row in row_names:
                check(row, 'the row ran to its end (it raised %s: %s)' % (type(exc).__name__, str(exc)[:300]), False)

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    here = Path(globals().get('__suite_file__', str(ROOT / 'scripts' / 'suites' / 'x.py'))).resolve().parents[2]
    fixture88 = load('v204_fixture88', here / 'proof/VELDO-0088/fixture.py')
    HOST = load('v204_host', here / 'proof/VELDO-0204/host.py')

    def caps(capacity, invocations, wall_seconds, **more):
        return dict(capacity=capacity, invocations=invocations, wall_seconds=wall_seconds, **more)

    # The owner's signed budgets. proj-a's is VELDO-0088's fixture's (capacity 5, invocations 12, wall 500).
    P = {'factory': caps(2, 10, 300), 'proj-a': caps(5, 12, 500), 'proj-b': dict(caps(6, 30, 900), owner_minutes=20),
         'proj-c': dict(caps(3, 8, 400), tokens=50000, messages=40, owner_minutes=10), 'proj-d': caps(4, 9, 450)}
    ROLE, PAY, REVIEW = caps(1, 2, 100), caps(2, 4, 300), caps(1, 2, 120)
    DEFAULT = {1: caps(2, 3, 150), 2: caps(3, 5, 200), 3: caps(3, 6, 250)}
    IMPLEMENTATION = caps(2, 4, 200)
    U = {name: 'v204-unit-' + name for name in ('a1', 'a2', 'b1', 'b2', 'a3', 'a4')}

    def project_caps(name):
        return {k: v for k, v in P[name].items() if k != 'owner_minutes'}

    def total(*projects):
        return {k: sum(P[p][k] for p in projects) for k in ('capacity', 'invocations', 'wall_seconds')}

    def plus(one, other):
        return {k: one[k] + other[k] for k in one if k in other}

    def subjects(answer, outcome=None, scope=None):
        return {(e['scope'], e['subject']) for e in (answer or {}).get('subjects') or []
                if (outcome is None or e['outcome'] == outcome) and (scope is None or e['scope'] == scope)}

    def entry(answer, scope, subject):
        return next((e for e in (answer or {}).get('subjects') or [] if (e['scope'], e['subject']) == (scope, subject)), {})

    def configured(answers):
        return {(e['scope'], e['subject']) for answer in answers or [] for e in (answer or {}).get('subjects') or []
                if e['outcome'] == 'configured'}

    def unchanged_except(before, after, changed):
        return all(after.get(key) == value for key, value in before.items() if key not in changed)

    def cap(policies, scope, subject):
        return ((policies.get((scope, subject)) or (0, None))[1] or {}).get('caps')

    def offered(report, unit):
        return [o for o in (report or {}).get('offered') or [] if o['unit'] == unit]

    def passed_over(h, unit, after):
        """Each refused worker reservation of `unit` since `after`: its refusal and every account's passed-over reason."""
        return [(event.get('refusal'), event.get('passed')) for event in h.observed[after:]
                if event.get('outcome') == 'refused' and ('/' + unit + '/') in str(event.get('request'))]

    def worker(h, dispatch_id):
        row = h.conn.execute('SELECT data FROM entities WHERE id=?',
                             (h.RES.entity('worker', [h.DOMAIN, dispatch_id]),)).fetchone()
        return json.loads(row[0]) if row else {}

    def committed_before(h, answers, scope, subject, dispatch_id):
        seqs = [e.get('seq') for a in answers or [] for e in (a or {}).get('subjects') or []
                if (e['scope'], e['subject']) == (scope, subject) and e['outcome'] == 'configured']
        reserved = worker(h, dispatch_id).get('reserved_seq')
        return bool(seqs) and isinstance(reserved, int) and all(isinstance(s, int) and s < reserved for s in seqs)

    try:
        with fixture88.fixture(ROOT, PRODUCTION, production_setup=True) as f:
            h = HOST.Host(ROOT, f)
            present = h.RP is not None
            for name in names:
                check(name, 'control_reservation_policies is installed beside the production modules', present)

            def provision(**kwargs):
                return h.provision(**kwargs) if present else {'outcome': 'absent', 'subjects': []}

            # A fresh host: the owner's configuration, each through its writer, while the setup holds the lock.
            with region(*names):
                h.source()
                h.service()
                h.agent('w-any')
                enrolled = h.enroll_authority()
                for name in ('factory', 'proj-b'):
                    h.activate(name, P[name])
                accepted = f['accept'](h.specialist(f['team'](), 'payments', PAY))
                h.review_policy()
                for account, provider in (('acc-c1', 'claude_code'), ('acc-c2', 'claude_code'), ('acc-x1', 'codex')):
                    h.register(account, provider)
                for name, project in (('a1', 'proj-a'), ('b1', 'proj-b')):
                    h.unit(U[name], project)
                    h.claim(U[name])
                    h.admit(U[name])
                h.unit(U['a2'], 'proj-a', holder='w-build2', document=True)
                h.admit(U['a2'])
                assigned = h.assign(U['a2'], 'payments')
                ready = (h.lock not in (None, -1) and enrolled is not None and accepted.get('ok')
                         and assigned.get('ok'))
                for name in names:
                    check(name, 'the fresh host is laid down [lock %s, team %s, assignment %s]' % (
                        h.lock, accepted.get('reason'), assigned.get('reason')), ready)

            # AC4 refuse/principal: a principal without reservation_service is refused by the writer, subject by subject.
            with region('refuse/principal'):
                before = h.head()
                answer = provision(principal='pm')
                sourced = {(s, n) for s, n, c, _ in (h.RP.derive(h.conn) if present else []) if c is not None}
                refusals = {e.get('refusal') for e in answer['subjects'] if (e['scope'], e['subject']) in sourced}
                check('refuse/principal', 'every subject with a source was refused missing_authority by the writer '
                      '[%s]' % sorted(refusals), sourced and subjects(answer, 'refused') >= sourced
                      and refusals == {'missing_authority'}
                      and all(entry(answer, *key).get('taxonomy') == 'missing_authority' for key in sourced))
                check('refuse/principal', 'nothing was written', h.head() == before and not h.policies())

            # AC1: provisioning on the setup's connection; a unit with no team and no default team is refused by name.
            with region('derive/values', 'fresh/dispatch', 'refuse/missing-source'):
                first = provision()
                refused = entry(first, 'unit', U['b1'])
                check('refuse/missing-source', 'the unit of a project with no team on a store with no default team is '
                      'refused by name, with its class [%s]' % refused,
                      refused.get('outcome') == 'refused' and refused.get('taxonomy') == 'missing_evidence'
                      and refused.get('refusal') == 'missing_evidence:reservation_source:unit:' + U['b1'])
                check('refuse/missing-source', 'it has no unit policy, while the other units have theirs',
                      h.policy('unit', U['b1'])[1] is None and h.policy('unit', U['a1'])[1] is not None
                      and h.policy('unit', U['a2'])[1] is not None)
                counted = {}
                if present:
                    counter = h.RP.Provisioning()
                    counter.run(h.conn, h.lock, h.writer(), caller='setup')
                    counted = counter.metrics()
                check('refuse/missing-source', 'the refusal is counted by name in the provisioning metrics [%s]' % counted,
                      counted.get('refusals') == {refused.get('refusal'): 1}
                      and counted.get('subjects', {}).get('unit:refused') == 1
                      and counted.get('passes') == {'setup:done': 1})

                loop0 = h.fit(h.SV.FactoryLoop(h.svc, {'repositories': {h.REPO: json.loads(
                    Path(h.config['work']).read_text())['repositories'][h.REPO]}}))
                line = loop0.lines[h.REPO]
                registered = {'acc-c1', 'acc-c2', 'acc-x1'}
                report = dict(offered=[], refused=[], waiting=[], decisions=[], asked=[], stopped=[])
                mark = len(h.observed)
                line.next(U['a1'], line.latest(), report)
                got = offered(report, U['a1'])
                slot = worker(h, got[0]['dispatch_id']) if got else {}
                check('fresh/dispatch', 'the unit dispatched through the Line\'s Runner and account pool on a registered '
                      'account [%s %s %s]' % (got, report['waiting'], passed_over(h, U['a1'], mark)),
                      got and got[0]['account'] in registered and (slot.get('context') or {}).get('account')
                      == got[0]['account'] and slot.get('type') == 'worker')
                writers = h.policy_writers()
                check('fresh/dispatch', 'with no configure call of the suite\'s own: every policy was written by '
                      'provisioning [%s]' % writers, writers and all(c.startswith('reservation-policy/') for c in writers))
                mark = len(h.observed)
                line.next(U['b1'], line.latest(), report)
                refusals = [r['refusals'] for r in report['refused'] if r['unit'] == U['b1']]
                # VELDO-0160: a unit's missing ceiling refuses the dispatch itself (the pool passes over accounts
                # only for an account's own refusals), so the unit is refused by that name and never offered.
                check('refuse/missing-source', 'its dispatch is refused missing_ceiling:unit by the reservation service, '
                      'while the other unit dispatched [%s %s %s]' % (refusals, passed_over(h, U['b1'], mark),
                                                                       report['waiting']),
                      refusals == [['missing_ceiling:unit']] and passed_over(h, U['b1'], mark)
                      and all(code == 'missing_ceiling:unit' for code, _p in passed_over(h, U['b1'], mark))
                      and not offered(report, U['b1']) and got)
                h.drain(loop0)

                saved = h.save_default(h.team(implementation=DEFAULT[1], independent_review=REVIEW), 0)
                second = provision()
                check('derive/values', 'the default team saved through VELDO-0203\'s offline route [%s]' % saved.get('reason'),
                      saved.get('ok'))
                expected = {('project', p): project_caps(p) for p in ('factory', 'proj-a', 'proj-b')}
                expected.update({('account', a): total('factory', 'proj-a', 'proj-b') for a in registered})
                expected.update({('unit', U['a1']): plus(ROLE, ROLE), ('unit', U['a2']): plus(PAY, ROLE),
                                 ('unit', U['b1']): plus(DEFAULT[1], REVIEW)})
                stored = {key: data['caps'] for key, (version, data) in h.policies().items()}
                check('derive/values', 'every stored policy has exactly the derived caps, per scope [%s]' % {
                    k: (stored.get(k), v) for k, v in expected.items() if stored.get(k) != v},
                      stored == expected)
                check('derive/values', 'owner_minutes is no reservation kind',
                      all('owner_minutes' not in c for c in stored.values()))
                every = [e for a in (first, second) for e in a.get('subjects') or []]
                check('derive/values', 'each subject is answered with its scope, source, caps and outcome, a configured '
                      'one with the command id its policy version names, committed in the journal',
                      every and all({'scope', 'subject', 'source', 'caps', 'outcome'} <= set(e) for e in every)
                      and all(e['command_id'] == 'reservation-policy/%s/%s/0' % (e['scope'], e['subject'])
                              and h.conn.execute('SELECT 1 FROM journal WHERE command_id=?', (e['command_id'],)).fetchone()
                              for e in every if e['outcome'] == 'configured'))
                check('derive/values', 'a unit\'s source names its team, revision and roles',
                      entry(second, 'unit', U['a2']).get('source', {}).get('roles') == ['payments', 'independent_review']
                      and entry(second, 'unit', U['b1']).get('source', {}).get('team') == 'default-team:1')

            # AC2: reconciliation.
            with region('rerun/unchanged', 'source/project', 'source/windows', 'source/team', 'source/account',
                        'source/unit'):
                before = h.head()
                rerun = provision()
                check('rerun/unchanged', 'a second run leaves every subject unchanged and the journal head where it was',
                      rerun.get('subjects') and subjects(rerun) == subjects(rerun, 'unchanged') and h.head() == before)

                window = h.writer().window(h.next_id('window'), 'acc-x1', 'tokens', 1000, time.time() + 3600, 1,
                                           now=time.time()) if h.policy('account', 'acc-x1')[1] else None
                held = (h.policy('account', 'acc-x1')[1] or {}).get('windows')
                prior = h.policies()
                h.activate('proj-c', P['proj-c'])
                added = provision()
                sums = total('factory', 'proj-a', 'proj-b', 'proj-c')
                accounts = {('account', a) for a in ('acc-c1', 'acc-c2', 'acc-x1')}
                after = h.policies()
                check('source/project', 'a third project updates every account policy to the new sums',
                      subjects(added, 'configured') == accounts | {('project', 'proj-c')}
                      and all(cap(after, *k) == sums for k in accounts))
                check('source/project', 'the new project has its policy with the kinds it states, tokens and messages '
                      'included and owner_minutes left out', cap(after, 'project', 'proj-c') == project_caps('proj-c'))
                check('source/project', 'the existing project and unit policies are unchanged',
                      prior and unchanged_except(prior, after, accounts))
                check('source/windows', 'the account\'s reported window is kept after its caps are updated [%s]' % held,
                      window and held and ((after.get(('account', 'acc-x1')) or (0, {}))[1] or {}).get('windows') == held
                      and cap(after, 'account', 'acc-x1') == sums)

                prior = h.policies()
                amended = f['accept'](h.specialist(h.team(implementation=IMPLEMENTATION), 'payments', PAY))
                team_pass = provision()
                after = h.policies()
                check('source/team', 'the amended team updates exactly that project\'s units derived from the changed '
                      'role, through the writer [%s]' % amended.get('reason'), amended.get('ok')
                      and subjects(team_pass, 'configured') == {('unit', U['a1'])}
                      and cap(after, 'unit', U['a1']) == plus(IMPLEMENTATION, ROLE)
                      and unchanged_except(prior, after, {('unit', U['a1'])}))
                prior = h.policies()
                saved = h.save_default(h.team(implementation=DEFAULT[2], independent_review=REVIEW), 1)
                default_pass = provision()
                after = h.policies()
                check('source/team', 'a new default team revision updates only the units of the project without a team',
                      saved.get('ok') and subjects(default_pass, 'configured') == {('unit', U['b1'])}
                      and cap(after, 'unit', U['b1']) == plus(DEFAULT[2], REVIEW)
                      and unchanged_except(prior, after, {('unit', U['b1'])}))

                prior = h.policies()
                h.register('acc-c3', 'claude_code')
                h.unit(U['b2'], 'proj-b')
                h.claim(U['b2'])
                h.admit(U['b2'])
                grown = provision()
                after = h.policies()
                check('source/account', 'a fourth account has exactly its policy added, at the sums',
                      ('account', 'acc-c3') in subjects(grown, 'configured')
                      and cap(after, 'account', 'acc-c3') == sums and ('account', 'acc-c3') not in prior)
                check('source/unit', 'a new unit has exactly its policy added, from its source',
                      ('unit', U['b2']) in subjects(grown, 'configured')
                      and cap(after, 'unit', U['b2']) == plus(DEFAULT[2], REVIEW))
                for row in ('source/account', 'source/unit'):
                    check(row, 'and nothing else is written', subjects(grown, 'configured')
                          == {('account', 'acc-c3'), ('unit', U['b2'])} and unchanged_except(prior, after, set()))

            # AC3: the lock, and the running service.
            with region('lock/second-connection'):
                second_conn = h.S.open_store(str(f['db']))
                try:
                    taken = h.F.take_lock(str(h.state))
                    before = h.head()
                    answer = provision(conn=second_conn, lock=taken)
                    check('lock/second-connection', 'a second connection, which cannot take the lock this host holds, is '
                          'refused not_the_authority first [%s %s]' % (taken, answer.get('refusal')),
                          taken is None and answer.get('refusal') == 'missing_authority:not_the_authority'
                          and answer.get('outcome') == 'refused' and not answer.get('subjects'))
                    other = h.RP.provision(h.conn, h.lock, h.writer(conn=second_conn), caller='setup') if present else {}
                    check('lock/second-connection', 'and so is a writer on another connection than the lock holder\'s',
                          other.get('refusal') == 'missing_authority:not_the_authority' and not other.get('subjects'))
                    check('lock/second-connection', 'the journal head is unchanged', h.head() == before)
                finally:
                    second_conn.close()

            with region('service/start', 'service/added', 'service/team', 'service/pm-assigned', 'service/rerun'):
                h.register('acc-c4', 'claude_code')
                h.activate('proj-d', P['proj-d'])
                sums = total('factory', 'proj-a', 'proj-b', 'proj-c', 'proj-d')
                before = h.head()
                try:
                    loop, refusal = h.open_loop()
                except TypeError:  # the service before this change takes no lock
                    loop, refusal = h.SV.open_loop(h.config, h.svc)
                    h.svc.loop = loop
                started = h.start_records()
                record = started[-1] if started else {}
                answers = record.get('provisioning') or []
                check('service/start', 'the loop opened [%s]' % refusal, loop is not None and refusal is None)
                check('service/start', 'its start record carries the provisioning, which committed the account and '
                      'project added while the service was stopped [%s]' % [a.get('refusal') for a in answers],
                      answers and answers[0].get('caller') == 'start'
                      and {('account', 'acc-c4'), ('project', 'proj-d')} <= configured(answers)
                      and loop is not None and loop.passes == 0)
                check('service/start', 'every account policy has the new sums, committed at start',
                      all(cap(h.policies(), 'account', a) == sums for a in ('acc-c1', 'acc-c2', 'acc-c3', 'acc-x1', 'acc-c4'))
                      and h.commands('reservation-policy/', before))
                installed = list(Path(f['setup_report']['home']).rglob('control_reservation_policies.py'))
                scaffold = load('v204_scaffold', h.mods / 'init_scaffold.py')
                check('service/start', 'the module is an installed runtime asset: in the scaffold inventory, and the setup '
                      'installation carries it byte for byte', '.veldo/control_reservation_policies.py' in scaffold._FILES
                      and installed and installed[0].read_bytes() == (h.mods / 'control_reservation_policies.py').read_bytes())
                h.fit(loop)

                def settle(limit=8):
                    """Passes until one offers nothing, each run drained before the next pass."""
                    seen = []
                    for _ in range(limit):
                        loop.wake('journal')
                        seen.append(loop.run() or {})
                        h.drain(loop)
                        if not seen[-1].get('offered') and not loop.wakes:
                            break
                    return seen

                settled = settle()
                check('service/start', 'the passes after start run without a provisioning fault [%s]' % [
                    p.get('faults') for p in settled], settled and all(
                        not any('provisioning' in x for x in p.get('faults') or []) for p in settled))

                # service/rerun: a pass with nothing added sends no reservation command.
                before = h.head()
                h.route('note:v204-quiet', 'note', {'n': 1})
                quiet = (loop.run() or {}).get('provisioning') or []
                check('service/rerun', 'the pass ran its provisioning at its start and in the line [%s %s]' % ([
                    a.get('caller') for a in quiet], loop.last.get('faults')), [a.get('caller') for a in quiet] == ['pass', 'line:' + h.REPO]
                      and all(a.get('outcome') == 'done' for a in quiet))
                check('service/rerun', 'and sent no reservation command',
                      not h.commands('reservation-policy/', before) and not h.commands('pm-ceiling/', before)
                      and all(subjects(a) == subjects(a, 'unchanged') for a in quiet))
                h.drain(loop)

                # service/added: a unit admitted through a service route has its policy at the pass it wakes.
                h.unit(U['a3'], 'proj-a')
                h.claim(U['a3'])
                mark = len(h.observed)
                routed = h.route(*h.admission(U['a3']))
                woke = list(loop.wakes)
                added = loop.run() or {}
                got = offered(added, U['a3'])
                check('service/added', 'the admission through the service woke the pass [%s]' % routed.get('reason'),
                      routed.get('ok') and 'journal' in [w['source'] for w in woke] and added)
                check('service/added', 'that pass committed the unit\'s policy from its source [%s]' % [
                    (a.get('caller'), sorted(configured([a]))) for a in added.get('provisioning') or []],
                      ('unit', U['a3']) in configured(added.get('provisioning'))
                      and cap(h.policies(), 'unit', U['a3']) == plus(IMPLEMENTATION, ROLE))
                check('service/added', 'and dispatched the unit, after its policy committed [%s %s %s %s]' % (
                    added.get('waiting'), passed_over(h, U['a3'], mark), added.get('refused'), added.get('faults')), got and committed_before(
                        h, added.get('provisioning'), 'unit', U['a3'], got[0]['dispatch_id']))
                h.drain(loop)
                settle()

                # service/team: a default team revision through VELDO-0203's service route.
                prior = h.policies()
                saved = h.svc.apply(h.owner_packet('save_default_team', dict(
                    team=h.team(implementation=DEFAULT[3], independent_review=REVIEW), base=2)),
                    {'repository_uuid': h.REPO, 'workspace': str(h.workspace)})
                team_pass = loop.run()
                after = h.policies()
                derived = {('unit', U['b1']), ('unit', U['b2'])}
                check('service/team', 'the owner\'s signed save went through the service [%s]' % saved.get('reason'),
                      saved.get('ok') and team_pass is not None)
                check('service/team', 'the next pass updated exactly the units derived from the default team [%s]' % (
                    sorted(configured((team_pass or {}).get('provisioning')))),
                      configured((team_pass or {}).get('provisioning')) == derived
                      and all(cap(after, *k) == plus(DEFAULT[3], REVIEW) for k in derived)
                      and unchanged_except(prior, after, derived))
                h.drain(loop)
                settle()

                # service/pm-assigned: a unit the PM cycle assigns in a pass has its policy before that pass offers it.
                line = loop.lines[h.REPO]
                for _ in range(6):
                    cycles = getattr(line, 'pm_cycles', None)
                    if cycles is None or not [r for r in cycles.records('proj-a') if r['state'] not in ('proposed', 'no_action', 'refused', 'waiting_owner')]:
                        break
                    loop.wake('journal')
                    loop.run()
                    h.drain(loop)
                h.unit(U['a4'], 'proj-a', holder='w-build2', document=True)
                h.admit(U['a4'])
                command = h.assign_command(U['a4'], 'payments')
                command.pop('subject')
                command['reviewers'] = ['w-rev1']
                h.result_file.write_text(json.dumps(dict(schema='veldo.pm_proposals/v1', owner_questions=[],
                                                         decomposition=[], proposals=[dict(
                                                             name='assign', type='assignment', command=command)])))
                h.accept_revision('Accepted project source, revised.\n')
                h.route('note:v204-assign', 'note', {'n': 2})
                coordinating = loop.run()
                before_caps = (h.policy('unit', U['a4'])[1] or {}).get('caps')
                h.drain(loop)
                assigning = loop.run()
                cycles = (assigning or {}).get('pm_cycles') or []
                applied = [p for c in cycles for p in c.get('proposals') or [] if p.get('type') == 'assignment']
                got = offered(assigning, U['a4'])
                lines = [a for a in (assigning or {}).get('provisioning') or [] if a.get('caller') == 'line:' + h.REPO]
                check('service/pm-assigned', 'the PM cycle started on the new unit and assigned it in the next pass [%s]'
                      % [(c.get('state'), c.get('refusal')) for c in cycles + ((coordinating or {}).get('pm_cycles') or [])],
                      (coordinating or {}).get('pm_cycles') and applied and applied[0]['result'].get('ok'))
                check('service/pm-assigned', 'that pass\'s line provisioning committed the policy of its assigned role '
                      '[%s -> %s]' % (before_caps, (h.policy('unit', U['a4'])[1] or {}).get('caps')),
                      ('unit', U['a4']) in configured(lines)
                      and cap(h.policies(), 'unit', U['a4']) == plus(PAY, ROLE) and before_caps == plus(IMPLEMENTATION, ROLE))
                check('service/pm-assigned', 'and that same pass offered the unit after the commit, never left waiting '
                      '[%s %s %s]' % ([w for w in (assigning or {}).get('waiting') or []], (assigning or {}).get('refused'),
                                      (assigning or {}).get('faults')),
                      got and committed_before(h, lines, 'unit', U['a4'], got[0]['dispatch_id'])
                      and not [w for w in (assigning or {}).get('waiting') or [] if w['unit'] == U['a4']])
                h.drain(loop)

            # AC2 source/absent: no policy without a source record, and the PM cycle's own unit policy left alone.
            with region('source/absent'):
                prior = h.policies()
                pm_policies = {k: v for k, v in prior.items() if k[0] == 'unit' and k[1].startswith('pm-cycle:')}
                last = provision()
                after = h.policies()
                check('source/absent', 'no policy for an account id with no account record or a unit id with no '
                      'execution_unit record', ('account', 'acc-ghost') not in after
                      and ('unit', 'v204-unit-ghost') not in after
                      and not [k for k in subjects(last) if k[1] in ('acc-ghost', 'v204-unit-ghost')])
                check('source/absent', 'the PM cycle\'s own unit policies exist and are left as the PM cycle wrote them',
                      pm_policies and all(after[k] == v for k, v in pm_policies.items())
                      and not [k for k in subjects(last) if k[1].startswith('pm-cycle:')])
                check('source/absent', 'a run with nothing changed writes nothing', unchanged_except(prior, after, set())
                      and set(after) == set(prior))

            # AC4 census/writer: Reservations.configure's production callers, and no other policy writer.
            with region('census/writer'):
                callers, writers = set(), set()
                for path in sorted(h.mods.glob('*.py')):
                    tree = ast.parse(path.read_text())
                    for node in ast.walk(tree):
                        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                                and node.func.attr == 'configure'):
                            callers.add(path.name)
                        if isinstance(node, ast.Dict):
                            pairs = {k.value: v for k, v in zip(node.keys, node.values)
                                     if isinstance(k, ast.Constant) and isinstance(k.value, str)}
                            value = pairs.get('kind')
                            if isinstance(value, ast.Constant) and value.value == 'subscription_reservation':
                                writers.add(path.name)
                        if isinstance(node, ast.keyword) and node.arg == 'kind' and isinstance(node.value, ast.Constant) \
                                and node.value.value == 'subscription_reservation':
                            writers.add(path.name)
                check('census/writer', 'the production callers of Reservations.configure are control_reservation_policies '
                      'and control_workflow_cycle_pm [%s]' % sorted(callers),
                      callers == {'control_reservation_policies.py', 'control_workflow_cycle_pm.py'})
                check('census/writer', 'no production module but control_reservations writes a subscription_reservation '
                      'entity [%s]' % sorted(writers), writers == {'control_reservations.py'})
    except Exception as error:  # noqa: BLE001 - a fixture that did not run reds every row by assertion
        for name in names:
            check(name, 'the fixture ran to its end (it raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)
    for name, observations in rows.items():
        for label, passed in observations:
            if not passed:
                print('VELDO-0204 ' + name + ' detail: ' + label)
        expect('VELDO-0204 ' + name, len(observations) > 1 and all(passed for _, passed in observations))


_v204_suite()
