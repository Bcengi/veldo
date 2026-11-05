"""VELDO-0236: the owner pauses an account until a window resets, resumes it, or sets a ceiling on one window, from
Telegram or the UI; every pause and ceiling carries its reset, ends by itself and is recorded in the journal.

Run: python3 scripts/selftest.py --suite 139_veldo_0236_account_pacing

Only ROOT, expect and fast_temp are consumed. A real signed SQLite authority (VELDO-0073's support,
scripts/suites/support/v73_authority.py) whose steward is the factory owner by VELDO-0203's rule (a person who enrolled
himself holding every bootstrap role) and whose owner is a project owner who is not; the production account records
(control_accounts) and pool (control_account_pool) over generated profile directories, the window observations written
by the reservation service member as the launch receiver writes them (VELDO-0166), the production factory loop's
lapse (control_service.FactoryLoop.lapse) as each pass runs it; the production intake (control_intake) over the
production VELDO-0066 Acquirer and a loopback Bot API stand-in for the Telegram route; the production ControlApi over
the production ApiAuthority holding the authority's lock, its writes assertions the API edge's real key signs (the
api channel edge enrolled by the steward's signed command), for the UI route and the pacing read's history. The UI's
pacing logic and component states are its Vitest spec (src/features/usage/pacing.spec.ts), which suite
120_veldo_0131_factory_ui runs with every usage spec. No real engine, login, Telegram or network beyond loopback; no
credential exists. Writes only temporary fixtures.
"""


def _v236_suite():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import time
    from types import SimpleNamespace

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_accounts.py': ROOT / ".veldo" / "control_accounts.py",
        'control_account_pool.py': ROOT / ".veldo" / "control_account_pool.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_intake.py': ROOT / ".veldo" / "control_intake.py",
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'control_api_authority.py': ROOT / ".veldo" / "control_api_authority.py",
        'control_api_assertion.py': ROOT / ".veldo" / "control_api_assertion.py",
        'control_api_models.py': ROOT / ".veldo" / "control_api_models.py",
    }
    ROWS = ('pause/ends', 'pause/no-reset', 'ceiling/relative', 'ceiling/lapse', 'resume/early',
            'ceiling/no-utilization', 'route/telegram', 'route/ui', 'route/other', 'journal/history', 'journal/once',
            'observability/counts')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def report():
        for row, checks in rows.items():
            failed = [label for label, ok in checks if not ok]
            expect('VELDO-0236 ' + row + ': ' + '; '.join(failed), bool(checks) and not failed)
            for label in failed:
                print('VELDO-0236 detail: ' + row + ': ' + label)

    H = load('v236_authority_support', ROOT / 'scripts/suites/support/v73_authority.py')
    base = Path(tempfile.mkdtemp(prefix='v236-', dir=fast_temp()))
    stops = []
    try:
        mods = base / 'modules'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        for name, path in PRODUCTION.items():
            shutil.copyfile(path, mods / name)
        authority = H.build(base / 'authority', mods, 23236, 'http://127.0.0.1:1', 'fixture', scope='activation-repository')
        S, CM, AC, conn, js = authority.S, authority.CM, authority.AC, authority.conn, authority.journal_sign
        authority.fixture('launch-receiver', 'membership', {'principal_type': 'service', 'roles': ['reservation_service'],
                                                            'scope': '*', 'revoked_at': None, 'expires_at': None})
        AA = load('v236_accounts', mods / 'control_accounts.py')
        POOL = load('v236_pool', mods / 'control_account_pool.py')
        CS = load('v236_service', mods / 'control_service.py')
        logged = []
        import inspect
        # The pre-change writer takes no observer: then each row fails by its own assertions (the red record).
        held = ({'observe_pacing': logged.append} if 'observe_pacing' in inspect.signature(AA.Accounts).parameters
                else {})
        # One writer on the connection, its principal set per command as suite 83_0166 does: the owner registers, the
        # reservation service observes, the factory loop's service principal records an end.
        pacer = AA.Accounts(S, conn, principal='authority', signer='authority', sign=js, **held)

        class As:
            def __init__(self, principal):
                self.who = principal

            def __getattr__(self, name):
                pacer.principal = self.who
                return getattr(pacer, name)
        registry, observer = As('owner'), As('launch-receiver')
        has_pacing = all(hasattr(pacer, n) for n in ('pause', 'ceiling', 'resume', 'lapse'))
        serial = [0]

        def register(*names):
            for name in names:
                profile = base / 'profiles' / name
                profile.mkdir(parents=True)
                registry.register('register/' + name, name, 'claude_code', name, {'host': str(profile)}, now=1)

        def observe(name, window, utilization, reset, at):
            serial[0] += 1
            observer.observe('observe/%d' % serial[0], name, window, status='allowed', reset_at=reset,
                             utilization=utilization, source_dispatch='dispatch/%s/%d' % (name, serial[0]), now=at)

        def choose(now, exclude=()):
            request = {'engine': 'claude_code', 'host': 'host'}
            if exclude:
                request['exclude'] = list(exclude)
            return POOL.choose(conn, {}, request, now, lambda account: None)

        def refused(call):
            try:
                call()
            except Exception as error:  # noqa: BLE001 - the named refusal of control_accounts or the store
                return getattr(error, 'code', type(error).__name__)
            return None

        def journal():
            return conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def pace(kind, *args, now, principal='steward', route='ui'):
            if not has_pacing:
                raise AttributeError('no pacing operation ' + kind)
            serial[0] += 1
            return getattr(pacer, kind)('pace/%d' % serial[0], *args, principal=principal, now=now, route=route)

        def lapse(now, passes):
            """One factory loop pass's lapse, as FactoryLoop.run runs it, on a service of this authority."""
            service = SimpleNamespace(conn=conn, principal='authority', sign=js, generation=1)
            pacer.principal = 'authority'
            loop = SimpleNamespace(service=service, accounts=pacer if has_pacing else None, clock=lambda: now,
                                   passes=passes)
            found = {'faults': []}
            if not hasattr(CS.FactoryLoop, 'lapse'):
                return found, []
            return found, CS.FactoryLoop.lapse(loop, found)

        def history(account=None):
            return AA.history(conn, account) if hasattr(AA, 'history') else []

        T = 1_900_000_000

        # AC1 pause/ends: two accounts; account-a ranks first (lower utilization); paused until its reset.
        register('account-a', 'account-b')
        observe('account-a', 'five_hour', 0.1, T + 1000, T)
        observe('account-b', 'five_hour', 0.3, T + 1000, T)
        check('pause/ends', 'account-a is chosen before any pause', choose(T + 10).get('account') == 'account-a')
        event = {}
        try:
            event = pace('pause', 'account-a', 'five_hour', now=T + 20)
        except Exception as error:  # noqa: BLE001
            check('pause/ends', 'the pause is accepted (%s)' % getattr(error, 'code', error), False)
        record = AA.read(conn, 'account-a') or {}
        check('pause/ends', 'the pause is stored with the window\'s reset as its end',
              (record.get('pause') or {}).get('until') == T + 1000 and event.get('until') == T + 1000)
        check('pause/ends', 'the indefinite paused status is never set', record.get('status') == 'active')
        before = choose(T + 500)
        check('pause/ends', 'before the reset the paused account is passed over paused_until:<reset> [%s]'
              % before.get('trace', {}).get('passed'),
              before.get('account') == 'account-b'
              and before.get('trace', {}).get('passed', {}).get('account-a') == 'paused_until:%d' % (T + 1000))
        check('pause/ends', 'the pass-over names the pause command that caused it',
              before.get('trace', {}).get('paced', {}).get('account-a') == event.get('command_id'))
        waiting = choose(T + 500, exclude=['account-b'])
        check('pause/ends', 'with no other account the end is the reset the loop\'s timer waits for [%s]'
              % POOL.refusal(waiting), waiting.get('account') is None and waiting.get('until') == T + 1000
              and POOL.refusal(waiting) == 'no_account_until:%d' % (T + 1000))
        observe('account-a', 'five_hour', 0.15, T + 4000, T + 600)
        check('pause/ends', 'a later observation of the window does not move the end',
              ((AA.read(conn, 'account-a') or {}).get('pause') or {}).get('until') == T + 1000)
        after = choose(T + 1000)
        check('pause/ends', 'from the end on the account is selected again with no command [%s]'
              % after.get('trace', {}).get('passed'), after.get('account') == 'account-a')

        # AC1 pause/no-reset: a window observed with no reset, and one whose reset has passed.
        register('account-c')
        observe('account-c', 'seven_day', 0.2, None, T)
        observe('account-c', 'five_hour', 0.2, T + 5, T)
        count = journal()
        check('pause/no-reset', 'a window with no reported reset is refused invalid_input:pause_reset',
              refused(lambda: pace('pause', 'account-c', 'seven_day', now=T + 10)) == 'invalid_input:pause_reset')
        check('pause/no-reset', 'a window whose reset is not later than now is refused invalid_input:pause_reset',
              refused(lambda: pace('pause', 'account-c', 'five_hour', now=T + 10)) == 'invalid_input:pause_reset')
        check('pause/no-reset', 'an unknown window or account is refused invalid_input:account',
              refused(lambda: pace('pause', 'account-c', 'weekly_opus', now=T + 10)) == 'invalid_input:account'
              and refused(lambda: pace('pause', 'account-z', 'five_hour', now=T + 10)) == 'invalid_input:account')
        check('pause/no-reset', 'nothing is written for a refusal',
              journal() == count and (AA.read(conn, 'account-c') or {}).get('pause') is None)

        # AC2 ceiling/relative: +10 on a window observed at 40 percent stores 50; selected at 49, passed over at 50.
        register('account-d', 'account-e')
        U = T + 10_000
        observe('account-d', 'five_hour', 0.40, U + 1000, U)
        observe('account-e', 'five_hour', 0.60, U + 1000, U)
        try:
            capped = pace('ceiling', 'account-d', 'five_hour', '+10', now=U + 1)
        except Exception as error:  # noqa: BLE001
            capped = {}
            check('ceiling/relative', 'the ceiling is accepted (%s)' % getattr(error, 'code', error), False)
        stored = ((AA.read(conn, 'account-d') or {}).get('ceilings') or {}).get('five_hour') or {}
        check('ceiling/relative', 'the relative ceiling is stored as the absolute result 50 with the reset as its end',
              stored.get('value') == 50 and stored.get('until') == U + 1000 and capped.get('value') == 50
              and capped.get('utilization') == 40)
        observe('account-d', 'five_hour', 0.49, U + 1000, U + 2)
        at49 = choose(U + 3, exclude=['account-a', 'account-b', 'account-c'])
        check('ceiling/relative', 'at 49 percent the account is selected [%s]' % at49.get('trace', {}).get('passed'),
              at49.get('account') == 'account-d')
        observe('account-d', 'five_hour', 0.50, U + 1000, U + 4)
        at50 = choose(U + 5, exclude=['account-a', 'account-b', 'account-c'])
        check('ceiling/relative', 'at 50 percent it is passed over ceiling:five_hour:50 [%s]'
              % at50.get('trace', {}).get('passed'), at50.get('account') == 'account-e'
              and at50.get('trace', {}).get('passed', {}).get('account-d') == 'ceiling:five_hour:50')
        try:
            pace('ceiling', 'account-d', 'five_hour', 60, now=U + 6)
        except Exception as error:  # noqa: BLE001
            check('ceiling/relative', 'a second ceiling is accepted (%s)' % getattr(error, 'code', error), False)
        replaced = ((AA.read(conn, 'account-d') or {}).get('ceilings') or {})
        check('ceiling/relative', 'a new ceiling on the same window replaces the old one',
              list(replaced) == ['five_hour'] and replaced['five_hour'].get('value') == 60
              and choose(U + 7, exclude=['account-a', 'account-b', 'account-c']).get('account') == 'account-d')
        try:
            pace('ceiling', 'account-d', 'five_hour', 50, now=U + 8)
        except Exception:  # noqa: BLE001
            pass

        # AC2 ceiling/lapse: after the reset, still at 50 percent, the account is selected again.
        lapsed = choose(U + 1000, exclude=['account-a', 'account-b', 'account-c'])
        check('ceiling/lapse', 'after the reset at 50 percent the capped account is selected again [%s]'
              % lapsed.get('trace', {}).get('passed'), lapsed.get('account') == 'account-d')
        check('ceiling/lapse', 'just before the reset it is still passed over',
              choose(U + 999, exclude=['account-a', 'account-b', 'account-c']).get('account') == 'account-e')

        # AC2 resume/early: a paused and capped account selected right after resume.
        register('account-f')
        V = T + 20_000
        observe('account-f', 'five_hour', 0.70, V + 1000, V)
        observe('account-f', 'seven_day', 0.20, V + 9000, V)
        others = ['account-a', 'account-b', 'account-c', 'account-d', 'account-e']
        try:
            pace('pause', 'account-f', 'five_hour', now=V + 1)
            pace('ceiling', 'account-f', 'seven_day', 10, now=V + 2)
            held_back = choose(V + 2.5, exclude=others)
            resumed = pace('resume', 'account-f', now=V + 3)
        except Exception as error:  # noqa: BLE001
            held_back, resumed = {}, {}
            check('resume/early', 'the pause, ceiling and resume are accepted (%s)' % getattr(error, 'code', error), False)
        check('resume/early', 'paused and capped, it is passed over before the resume [%s]' % held_back.get('passed'),
              held_back.get('account') is None
              and str((held_back.get('passed') or {}).get('account-f')).startswith('paused_until:'))
        check('resume/early', 'right after resume the account is selected',
              choose(V + 4, exclude=others).get('account') == 'account-f')
        check('resume/early', 'the resume ends its pause and its ceilings at once',
              sorted(e.get('kind') for e in resumed.get('ended') or []) == ['ceiling', 'pause']
              and (AA.read(conn, 'account-f') or {}).get('pause') is None
              and not (AA.read(conn, 'account-f') or {}).get('ceilings'))

        # AC2 ceiling/no-utilization: a window observed with a reset and no utilization.
        register('account-g')
        observe('account-g', 'five_hour', None, V + 1000, V)
        observe('account-g', 'seven_day', 0.3, None, V)
        count = journal()
        check('ceiling/no-utilization', 'an absolute ceiling on a window with no observed utilization is refused '
              'invalid_input:ceiling', refused(lambda: pace('ceiling', 'account-g', 'five_hour', 50, now=V + 1))
              == 'invalid_input:ceiling')
        check('ceiling/no-utilization', 'a relative one is refused the same way',
              refused(lambda: pace('ceiling', 'account-g', 'five_hour', '+10', now=V + 1)) == 'invalid_input:ceiling')
        check('ceiling/no-utilization', 'a window with no reset is refused invalid_input:ceiling_reset',
              refused(lambda: pace('ceiling', 'account-g', 'seven_day', 50, now=V + 1)) == 'invalid_input:ceiling_reset')
        observe('account-g', 'five_hour', 0.95, V + 1000, V + 2)
        check('ceiling/no-utilization', 'a value outside 1 to 100 is refused invalid_input:ceiling',
              all(refused(lambda value=value: pace('ceiling', 'account-g', 'five_hour', value, now=V + 3))
                  == 'invalid_input:ceiling' for value in (0, 101, '+10', 'ten')))
        check('ceiling/no-utilization', 'nothing is written for a refusal',
              journal() == count + 1 and not (AA.read(conn, 'account-g') or {}).get('ceilings'))

        # AC4 journal/history: a pause, a ceiling, a resume and an end at reset, exactly those four in order.
        register('account-h', 'account-i')
        W = T + 30_000
        observe('account-h', 'five_hour', 0.2, W + 1000, W)
        observe('account-i', 'five_hour', 0.2, W + 1000, W)
        try:
            pace('pause', 'account-h', 'five_hour', now=W + 1)
            pace('ceiling', 'account-i', 'five_hour', 30, now=W + 2)
            pace('resume', 'account-i', now=W + 3)
        except Exception as error:  # noqa: BLE001
            check('journal/history', 'the commands are accepted (%s)' % getattr(error, 'code', error), False)
        observe('account-h', 'five_hour', 0.9, W + 1000, W + 4)
        lapse(W + 999, 1)
        report_end, ended = lapse(W + 1000, 2)
        found = [e for e in history() if e.get('account') in ('account-h', 'account-i')]
        check('journal/history', 'exactly four records in order: pause, ceiling, resume, end [%s]'
              % [e.get('type') for e in found], [e.get('type') for e in found] == ['pause', 'ceiling', 'resume', 'end'])
        need = set(getattr(AA, 'EVENT_FIELDS', ()))
        check('journal/history', 'each record carries command id, principal, account, window, end and value',
              bool(need) and all(set(e) - {'seq'} == need for e in found)
              and [e.get('principal') for e in found] == ['steward', 'steward', 'steward', 'authority']
              and found and found[1].get('value') == 30 and found[0].get('until') == W + 1000
              and found[-1].get('until') == W + 1000 and found[-1].get('pass') == 2)
        rows_journal = {r['command_id']: r for r in S.export_journal(conn)}
        check('journal/history', 'each is one signed journal record of its own command',
              all(rows_journal.get(e.get('command_id'), {}).get('signature') and
                  rows_journal[e['command_id']]['seq'] == e['seq'] for e in found))
        check('journal/history', 'the pass reports what ended',
              [e.get('account') for e in report_end.get('paces_ended') or []] == ['account-h'] and not report_end['faults'])

        # AC4 journal/once: two passes after the end commit one end record.
        again, more = lapse(W + 1001, 3)
        third, _ = lapse(W + 5000, 4)
        ends = [e for e in history('account-h') if e.get('type') == 'end']
        check('journal/once', 'two passes after the end commit one end record [%d]' % len(ends),
              len(ends) == 1 and more == [] and again.get('paces_ended') == [] and third.get('paces_ended') == [])

        # Observability: each command and end observed with its fields and counted by type, route and outcome.
        counts = getattr(pacer, 'pacing_counts', {})
        check('observability/counts', 'pauses, ceilings, resumes and ends counted by route and outcome [%s]' % counts,
              counts.get('pause/ui/accepted', 0) >= 3 and counts.get('ceiling/ui/refused', 0) >= 3
              and counts.get('end/pass/accepted', 0) >= 1 and counts.get('resume/ui/accepted', 0) >= 2)
        check('observability/counts', 'each observation names command, principal, route, account, window and end',
              any(e.get('operation') == 'pause' and e.get('outcome') == 'accepted' and e.get('until')
                  and e.get('principal') == 'steward' and e.get('route') == 'ui' for e in logged)
              and any(e.get('operation') == 'end' and e.get('pass') == 2 for e in logged)
              and not any('profiles' in json.dumps(e) for e in logged))
        check('observability/counts', 'dispatches passed over for a pause or a ceiling counted by reason',
              POOL.metrics({'w1': {'type': 'worker', 'context': {'account': 'account-b'},
                                   'selection': before.get('trace')},
                            'w2': {'type': 'worker', 'context': {'account': 'account-e'},
                                   'selection': at50.get('trace')}}).get('passed_over')
              == {'paused_until': 1, 'ceiling': 1})

        # AC3: the routes. The loopback Bot API, the steward's (factory owner's) chat and the owner's.
        IN = load('v236_intake', mods / 'control_intake.py')
        API = load('v236_api', mods / 'control_api.py')
        AUTH = load('v236_judge', mods / 'control_api_authority.py')
        EVP = load('v236_publication', mods / 'control_event_projection.py')
        P = load('v236_projection', mods / 'control_channel_projection.py')
        PV = load('v236_presentation', mods / 'control_channel_presentation.py')
        EV = load('v236_attribution', mods / 'control_channel_attribution.py')
        I = load('v236_inbox', mods / 'control_assignment.py')
        contract = load('v236_contract', mods / 'entity_contract.py')
        CR, AS = AUTH.CR, AUTH.AS
        ids, domain = authority.ids, authority.ids['domain_uuid']
        bot = {'id': 8000000236, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_v236_bot'}
        url, bot_api, stop_bot = H.stand_in({'bot236': bot})
        stops.append(stop_bot)
        steward_user = {'id': 23999, 'is_bot': False, 'first_name': 'Steward'}
        owner_user = {'id': 23236, 'is_bot': False, 'first_name': 'Owner'}
        authority.fixture('channel-enrollment:telegram_chat:steward', 'channel_enrollment',
                          dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='steward',
                               chat_id=steward_user['id'], revoked_at=None))
        project = 'activation-repository'
        authority.fixture('project:' + project, 'project', {'name': project, 'owner': 'owner', 'state': 'ACTIVE',
                                                            'ticket_key_prefixes': []})
        authority.fixture('project:factory', 'project', {'name': 'factory', 'owner': 'steward', 'state': 'ACTIVE',
                                                         'ticket_key_prefixes': []})
        inbox = I.Inbox(S, CM, authority.claims, contract, conn, ids, 'authority', js)
        presenter = PV.Presenter(S, CM, P, inbox, PV.TelegramPresentationEdge(P, url, 'bot236'), conn, 'authority', js,
                                 assignment=I)
        acquirer = EV.Acquirer(S, CM, P, PV, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot236'), conn,
                               'authority', js, 'api-edge', lambda b: authority.sign_as('api-edge', b))
        import inspect
        intake_extra = {'accounts': pacer} if 'accounts' in inspect.signature(IN.Intake).parameters else {}
        intake = IN.Intake(S, CM, AC, acquirer, conn, domain=domain, projects=[project, 'factory'], api_edge='api-edge',
                           journal_signer='authority', sign=js, asker=presenter.edge, **intake_extra)

        def telegram(sender, text):
            update = H.deliver(bot_api, 'bot236', sender, text)
            acquirer.acquire()
            return intake.receive('telegram_message', EV.evidence_id(bot['id'], update['update_id']))

        def sent_texts():
            return [m['text'] for (_chat, _id), m in sorted(bot_api['bots']['bot236']['messages'].items())
                    if (m.get('from') or {}).get('is_bot')]

        # The API's own edge, enrolled by the steward's signed command, and the passkey credentials of both members.
        edge_key = base / 'edge-api-key'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v236-api-edge', '-f', str(edge_key)],
                       check=True, capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        edge_public = ' '.join(edge_key.with_name(edge_key.name + '.pub').read_text().split()[:2])

        def edge_sign(message, namespace='veldo-command'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(edge_key), '-n', namespace], input=message,
                                  capture_output=True, check=True, timeout=10).stdout.decode()
        EDGE = 'api-edge-236'
        edge = {'channel': 'api', 'edge_principal': EDGE, 'edge_key_id': 'edge-api', 'public_key': edge_public,
                'connection_public_key': authority.public['settler'], 'scope': [project]}
        command = {'command_id': authority.next_id('edge'), 'operation': 'enroll_channel_edge', 'target': 'channel:api',
                   'parameters': edge, 'artifact_digests': [], 'expected_versions': {}}
        envelope = authority.envelope(command, 'steward')
        authority.E.Enrollment(S, conn, ids, 'authority', js, projection=authority.projection).admit(
            envelope, command, authority.sign_as('steward', AC.canonical_envelope_bytes(envelope)),
            edge_sign(AC.canonical_envelope_bytes(envelope), 'veldo-edge-possession'))
        for who in ('steward', 'owner'):
            cid = 'v236-passkey-' + who
            authority.fixture(CR.entity_id(cid), CR.KIND, {'credential_id': cid, 'principal': who, 'effective_at': 0,
                                                           'revoked_at': None, 'label': who})
        (base / 'publication').mkdir()
        publication = EVP.Projection(S, str(authority.db), domain=ids['domain_uuid'], repository=ids['repository_uuid'],
                                     root=str(base / 'publication'))
        lock = CS.acquire(str(authority.db.parent / 'authority.lock'), {'principal': 'authority'})
        judge = AUTH.ApiAuthority(S, CM, conn, ids=ids, domain=domain, edge=EDGE, intake=intake, settlement=None,
                                  credentials=None, publication=publication, authority_lock=lock, accounts=pacer)

        def signer(assertion):
            derived = AS.domain_request(assertion)
            return (edge_sign(S.canonical_bytes(assertion)),
                    edge_sign(S.canonical_bytes(derived)) if derived is not None else None)
        host = 'veldo.v236.test'
        ui = API.ControlApi({'origin': 'https://' + host, 'rp_id': host, 'host': host, 'domain': domain, 'ids': ids,
                             'edge': EDGE, 'state_dir': str(base / 'api-state')}, judge, signer)
        sessions = {who: ui.sessions.create(who, 'v236-passkey-' + who) for who in ('steward', 'owner')}

        def call(method, route, body=None, who='steward'):
            cookie, session = sessions[who]
            sent = {'Host': host, 'Cookie': '%s=%s' % (API.COOKIE, cookie)}
            if method == 'POST':
                sent.update({'Origin': 'https://' + host, 'Sec-Fetch-Site': 'same-origin',
                             'Content-Type': 'application/json', API.TOKEN_HEADER: session['token']})
            status, _headers, value = ui.handle(method, '/api/v1/domains/%s/%s' % (domain, route), sent,
                                                json.dumps(body or {}).encode() if method == 'POST' else b'')
            return status, value

        now = time.time()
        reset = int(now) + 3 * 3600
        register('account-tg', 'account-ui')
        for name in ('account-tg', 'account-ui'):
            observe(name, 'five_hour', 0.40, reset, now - 5)

        def records_of(name, start):
            return [e for e in history(name) if e['seq'] > start]

        start = conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        answers = {}
        for text in ('/pause account-tg five_hour', '/ceiling account-tg five_hour +10', '/resume account-tg'):
            answers[text.split()[0]] = telegram(steward_user, text)
        tg = records_of('account-tg', start)
        texts = sent_texts()
        hhmm = time.strftime('%H:%M', time.gmtime(reset))
        print('  VELDO-0236 telegram:', {k: (v.get('outcome'), v.get('reason')) for k, v in answers.items()})
        check('route/telegram', 'each typed command is decided as a command and accepted [%s]'
              % {k: v.get('reason') for k, v in answers.items()},
              all(v.get('outcome') == 'account_command' for v in answers.values()))
        check('route/telegram', 'its records are the pause, ceiling and resume with their ends and value',
              [e.get('type') for e in tg] == ['pause', 'ceiling', 'resume'] and tg[0].get('until') == reset
              and tg[1].get('value') == 50 and all(e.get('route') == 'telegram' for e in tg))
        check('route/telegram', 'each answer names the account, the window and the end in words [%s]' % texts[-3:],
              any('account-tg paused until %s UTC, when its five_hour window resets' % hhmm in t for t in texts)
              and any('account-tg capped at 50 percent of its five_hour window until %s UTC' % hhmm in t for t in texts)
              and any(t.startswith('account-tg resumed') for t in texts))
        telegram(steward_user, '/pause account-tg five_hour')
        paused = AA.read(conn, 'account-tg') or {}
        free = choose(reset, exclude=[n for n in ('account-%s' % c for c in 'abcdefghi')] + ['account-ui'])
        check('route/telegram', 'the pause carries its end: no indefinite status, the account selected at its reset',
              paused.get('status') == 'active' and (paused.get('pause') or {}).get('until') == reset
              and free.get('account') == 'account-tg')
        check('route/telegram', 'no message became a proposal',
              not [r for r in conn.execute("SELECT data FROM entities WHERE kind='intake_proposal'").fetchall()
                   if 'account-tg' in r[0]])

        start = conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]
        posted = [call('POST', 'accounts/pause', {'account': 'account-ui', 'window': 'five_hour'}),
                  call('POST', 'accounts/ceiling', {'account': 'account-ui', 'window': 'five_hour', 'value': '+10'}),
                  call('POST', 'accounts/resume', {'account': 'account-ui'})]
        print('  VELDO-0236 ui:', [(s, (v or {}).get('outcome'), (v or {}).get('refusal')) for s, v in posted])
        uir = records_of('account-ui', start)
        check('route/ui', 'each route answers 200 with its outcome [%s]' % [(s, (v or {}).get('refusal')) for s, v in posted],
              [s for s, _v in posted] == [200, 200, 200]
              and [(v or {}).get('outcome') for _s, v in posted] == ['paused', 'capped', 'resumed'])
        check('route/ui', 'each answer names the account, the window and the end in words',
              'account-ui paused until %s UTC, when its five_hour window resets' % hhmm in str((posted[0][1] or {}).get('words'))
              and (posted[1][1] or {}).get('value') == 50)
        check('route/ui', 'the same journal record types and fields as the Telegram route\'s',
              [e.get('type') for e in uir] == [e.get('type') for e in tg] and len(uir) == 3
              and all(set(a) == set(b) for a, b in zip(uir, tg)) and all(e.get('route') == 'ui' for e in uir)
              and all(str(e.get('provenance', '')).startswith('sha256:') for e in uir))
        table = {r.name: r for r in API.ROUTES}
        check('route/ui', 'the routes, operations and UI actions are published together',
              all(n in table for n in ('accounts.pause', 'accounts.resume', 'accounts.ceiling'))
              and ui.route_problems() == []
              and {a.name for a in API.MO.ACTIONS} >= {'account_pause', 'account_resume', 'account_ceiling'})
        status, spend = call('GET', 'accounts/pacing')
        served = [e for e in (spend or {}).get('pacing') or [] if e.get('account') in ('account-ui', 'account-tg')]
        _status, plain = call('GET', 'spend')
        check('route/ui', 'the spend read keeps its representation (no pacing field)', 'pacing' not in (plain or {}))
        check('route/ui', 'the pacing read serves the accounts and the history from the journal [%s]' % status,
              status == 200 and [e.get('seq') for e in served] == [e['seq'] for e in history() if e.get('account')
                                                                  in ('account-ui', 'account-tg')] and len(served) >= 7)

        version = conn.execute("SELECT version FROM entities WHERE id='account:account-ui'").fetchone()[0]
        count = journal()
        other_tg = telegram(owner_user, '/pause account-ui five_hour')
        other_ui = call('POST', 'accounts/pause', {'account': 'account-ui', 'window': 'five_hour'}, who='owner')
        other_cap = call('POST', 'accounts/ceiling', {'account': 'account-ui', 'window': 'five_hour', 'value': 20},
                         who='owner')
        print('  VELDO-0236 other:', other_tg.get('reason'), other_ui, other_cap[0])
        check('route/other', 'a non-owner\'s Telegram command is refused as VELDO-0203 refuses it [%s]'
              % other_tg.get('reason'), other_tg.get('outcome') == 'refused'
              and other_tg.get('reason') == 'missing_authority:owner_command:not_factory_owner')
        check('route/other', 'a non-owner\'s UI commands are refused by that name [%s]' % (other_ui,),
              other_ui[0] >= 400 and 'not_factory_owner' in str((other_ui[1] or {}).get('refusal'))
              and other_cap[0] >= 400)
        check('route/other', 'nothing is written for them: no pacing record, the account unchanged',
              conn.execute("SELECT version FROM entities WHERE id='account:account-ui'").fetchone()[0] == version
              and not [e for e in history('account-ui') if e.get('principal') == 'owner']
              and not [r for r in S.export_journal(conn) if r['seq'] > count
                       and 'account:account-ui' in r['transition']])

    except Exception as error:  # noqa: BLE001 - a fixture that broke fails every row still empty, by name
        import traceback
        traceback.print_exc()
        for row, checks in rows.items():
            if not checks:
                check(row, 'the fixture ran (%s: %s)' % (type(error).__name__, error), False)
    finally:
        for stop in stops:
            try:
                stop()
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(base, ignore_errors=True)
    report()


_v236_suite()
