"""VELDO-0169: census and signed handouts over the Gate's project check, the claim organ's, and the store's.

Only ROOT and expect come from shared. Projects, memberships, claims, parks, answers,
stops, settlements and contracts use their production writers. Admitted units and backlog
items are the claim organ's accepted-admission fixture seam. The paths that forget the caller's
check are the claim organ registered bare on the suite's connection and the station contract writer
called from a probe command, as a new engine path would reach them; the paths that skip the organ
are transitions that build a claim record by hand and the generic upsert. A second process (the owner's
project commands, written below as _V169_FLIPPER) pauses and resumes a project while claims run. No model
or external host.
"""

_V169_FLIPPER = r'''"""VELDO-0169 suite 84: the owner pauses and resumes one project, from a second process."""
import importlib.util, json, subprocess, sys, time
from pathlib import Path
mods, db, ids, owner_key, journal_key, project, flips, out = (sys.argv[1], sys.argv[2], json.loads(sys.argv[3]),
                                                           sys.argv[4], sys.argv[5], sys.argv[6], int(sys.argv[7]), sys.argv[8])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


claims = load('flip_claims', Path(mods) / 'control_claim.py')
S, CM = claims.S, claims.CM
CM.attach(S)
load('flip_keys', Path(mods) / 'control_keys.py').attach(S)
PJ = load('flip_projects', Path(mods) / 'control_project.py')


def sign(key, message, namespace):
    return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', key, '-n', namespace], input=message,
                          capture_output=True, check=True, timeout=10).stdout.decode()


conn = S.open_store(db)
projects = PJ.Projects(S, CM, conn, ids, 'authority', lambda m: sign(journal_key, m, 'veldo-journal'),
                       stop=lambda dispatch, reason: dict(outcome='stopped'))
log = []
for i in range(flips):
    record = S.materialized_state(conn)['entities'].get('project:' + project)
    action = 'pause' if record['data'].get('state') == 'ACTIVE' else 'resume'
    body = dict(ids, operation=action, principal='project-owner', command_id='flip-%d-%f' % (i, time.time()),
                nonce='flip-n-%d-%f' % (i, time.time()), project=project, project_version=record['version'],
                reason='Owner stops new work', disposition='Retain accepted history')
    result = projects.apply({'command': body, 'signature': sign(owner_key, S.canonical_bytes(body), 'veldo-command')})
    log.append((action, bool(result.get('ok'))))
    time.sleep(0.01)
conn.close()
Path(out).write_text(json.dumps(log))
'''


def _v169_suite():
    import ast
    import collections
    import contextlib
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import sys
    import tempfile
    import time

    production = {
        'control_assignment.py': ROOT / ".veldo" / "control_assignment.py",
        'control_claim.py': ROOT / ".veldo" / "control_claim.py",
        'control_andon.py': ROOT / ".veldo" / "control_andon.py",
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
        'control_store.py': ROOT / ".veldo" / "control_store.py",
    }
    rows = {}

    def check(row, label, condition):
        rows.setdefault(row, []).append((label, bool(condition)))

    @contextlib.contextmanager
    def region(*labels):
        """A raise reds the rows it interrupts by name, and never takes the other rows with it."""
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise is a failed row, never a skipped one
            for label in labels:
                check(label, 'ran to its end: %r' % (error,), False)

    DECLARED = (['census/writers', 'census/planted']
                + [p + '/' + s for p in ('resume', 'dispose', 'andon')
                   for s in ('PAUSED', 'CANCELED', 'COMPLETED', 'owner_not_current', 'race')]
                + ['claim/absent', 'claim/null', 'organ/stopped', 'organ/outside', 'store/invariant', 'guard/forge',
                   'organ/race', 'guard/resume-again', 'andon/subject-race', 'store/upgrade'])

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    CEN = load('v169_census', ROOT / 'scripts' / 'suites' / 'support' / 'v169_census.py')

    def engine_sources():
        """Every engine module's source; a mutation replaces its installed copy, read in its place."""
        sources = {}
        for path in sorted((ROOT / 'engine' / '.veldo').glob('*.py')):
            replacement = production.get(path.name)
            use = replacement if replacement is not None and replacement != ROOT / '.veldo' / path.name else path
            sources[path.stem] = use.read_text()
        return sources

    def resume_again(a, writer):
        """The reviewer's falsifier of AC1 (rv169a): a copy of Inbox._resume as _resume_again without the
        project check, wired into OPERATIONS and the dispatch, and into _transition with a claim write of
        its own ('own'), through the resume's write ('shared'), or not at all ('none')."""
        start = a.find('    def _resume(self, state, entities, current, principal, now, command, params, observation):')
        end = a.find('\n    def ', start + 10)
        original = a[start:end]
        again = original.replace('def _resume(', 'def _resume_again(').replace(
            '        self._check_project(unit, entities, observation)\n', '')

        def edit(text, old, new):
            if start < 0 or text.count(old) != 1 or '_check_project' in again:
                raise LookupError(old[:60])
            return text.replace(old, new)
        wired = edit(edit(edit(a, "'resume', 'ask', 'dispose')", "'resume', 'ask', 'dispose', 'resume_again')"),
                          "            elif op == 'resume':\n",
                          "            elif op == 'resume_again':\n"
                          "                touched.update(self._resume_again(state, entities, current, principal, now, command, params, observation))\n"
                          "            elif op == 'resume':\n"), original, original + again)
        if writer == 'own':
            return edit(wired, "        if op == 'resume':\n", "        if op == 'resume_again':\n"
                        "            return self.claims.transition(self.conn, params['resume'], before)\n        if op == 'resume':\n")
        if writer == 'shared':
            return edit(wired, "        if op == 'resume':\n", "        if op in ('resume', 'resume_again'):\n")
        return wired

    def planted(sources):
        """The reviewer's planted writers (rv169a) and more of the same shape, each over these sources."""
        a, n = sources['control_assignment'], sources['control_andon']

        def edit(text, old, new):
            if text.count(old) != 1:
                raise LookupError(old[:60])
            return text.replace(old, new)
        yield 'resume-again-dispatch-only', 'Inbox._resume_again', lambda: {'control_assignment': resume_again(a, 'none')}
        yield 'resume-again-own-writer', 'Inbox._resume_again', lambda: {'control_assignment': resume_again(a, 'own')}
        yield 'resume-again-shared-writer', 'Inbox._resume_again', lambda: {'control_assignment': resume_again(a, 'shared')}
        fast = lambda body: {'control_fastlane': 'class Fast:\n    def __init__(self, inbox):\n        self.inbox = inbox\n' + body}
        yield 'module-local-alias', 'Fast.take', lambda: fast(
            '    def take(self, conn, params, before):\n        organ = self.inbox.claims\n        return organ.transition(conn, params, before)\n')
        yield 'renamed-attribute', 'Fast.take', lambda: fast(
            '    def take(self, conn, params, before):\n        return self.inbox.claim_organ.transition(conn, params, before)\n')
        yield 'getattr-call', 'Fast.take', lambda: fast(
            "    def take(self, conn, params, before):\n        return getattr(self.inbox.claims, 'transition')(conn, params, before)\n")
        yield 'plain-attribute', 'Fast.take', lambda: fast(
            '    def take(self, conn, params, before):\n        return self.inbox.claims.transition(conn, params, before)\n')
        yield 'bound-method-alias', 'Fast.take', lambda: fast(
            '    def take(self, conn, params, before):\n        write = self.inbox.claims.transition\n        return write(conn, params, before)\n')
        yield 'dynamic-getattr', 'Fast.take', lambda: fast(
            '    def take(self, name, conn, params, before):\n        return getattr(self.inbox.claims, name)(conn, params, before)\n')
        yield 'bare-registration', 'Fast.attach', lambda: fast(
            "    def attach(self, conn):\n        conn.command_registry['fast'] = {'transaction_transition': self.inbox.claims.transition}\n")
        yield 'hand-built-claim', 'Fast.take', lambda: fast(
            "    def take(self, cid, data):\n        return {cid: {'kind': 'claim', 'data': data}}\n")
        yield 'hand-built-claim-registered', 'Fast.attach.<lambda>', lambda: fast(
            "    def attach(self, conn, cid):\n        conn.command_registry['fast'] = {'transition': lambda params, before: {cid: dict(\n"
            "            kind='claim', data=dict(state='owned', holder='worker'))}}\n")
        yield 'andon-second-resume', 'Andon.resume_quick', lambda: {'control_andon': edit(
            n, '    def run(self):\n',
            "    def resume_quick(self, sid, contract, permission, evidence, expected, command_id):\n"
            "        self._commit(dict(action='resume', stop_id=sid, unit_id=contract['unit'], contract=contract,\n"
            "                          permission=permission, evidence=evidence), expected, self.journal_signer, command_id, command_id)\n\n"
            '    def run(self):\n')}
        yield 'contract-without-writer', 'Andon.quick_contract', lambda: {'control_andon': edit(
            n, '    def run(self):\n',
            "    def quick_contract(self, contract):\n"
            "        return {contract['contract_id']: {'kind': CONTRACT_KIND, 'data': contract}}\n\n"
            '    def run(self):\n')}
        yield 'check-in-a-branch', 'Inbox._resume', lambda: {'control_assignment': edit(
            a, "        self._check_project(unit, entities, observation)\n        params['resume']",
            "        if params.get('urgent'):\n            self._check_project(unit, entities, observation)\n        params['resume']")}

    def census():
        sources = engine_sources()
        records, failures = CEN.census(sources)
        print('  VELDO-0169 census: ' + json.dumps(dict(writers=records, failures=failures,
              counts=dict(collections.Counter(r['classification'] for r in records))), sort_keys=True))
        check('census/writers', '; '.join(failures) or 'every discovered writer classified and checked', not failures)
        # What AC1 says the census finds today, so a census that finds nothing cannot pass.
        def found(module, classification, action=None, writer=CEN.ORGAN):
            return any(r['module'] == module and r['classification'] == classification and r['writer'] == writer
                       and (action is None or action in r.get('actions', ())) for r in records)
        for module, classification, action, writer in (
                ('control_claim', 'handout', 'claim', CEN.ORGAN), ('control_assignment', 'handout', 'resume', CEN.ORGAN),
                ('control_assignment', 'handout', 'unpark', CEN.ORGAN), ('control_andon', 'handout', None, CEN.CONSTRUCTOR),
                ('control_assignment', 'nothing', 'park', CEN.ORGAN), ('control_claim', 'nothing', 'release', CEN.ORGAN),
                ('control_heartbeat', 'nothing', 'renew', CEN.ORGAN)):
            check('census/writers', 'finds %s %s %s' % (module, classification, action or writer),
                  found(module, classification, action, writer))
        for name, function, build in planted(sources):
            try:
                change = build()
            except LookupError as missing:
                check('census/planted', '%s built on these sources (anchor %r)' % (name, str(missing)), False)
                continue
            _, planted_failures = CEN.census(dict(sources, **change))
            check('census/planted', name + ' refused at ' + function,
                  any(('.' + function + ':') in f for f in planted_failures))

    with region('census/writers', 'census/planted'):
        census()
    with tempfile.TemporaryDirectory(prefix='v169-', dir='/dev/shm') as directory:
        base = Path(directory)
        mods = base / 'installed'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in production.items():
            shutil.copyfile(source, mods / name)
        H = load('v169_support', ROOT / 'scripts/suites/support/v73_authority.py')
        IN = load('v169_ingress', mods / 'control_channel_ingress.py')
        EV = load('v169_attribution', mods / 'control_channel_attribution.py')
        PJ = load('v169_projects', mods / 'control_project.py')
        AND = load('v169_andon', mods / 'control_andon.py')
        owner_user = dict(id=5580169, is_bot=False, first_name='Owner')
        bot_user = dict(id=8000000169, is_bot=True, first_name='Veldo', username='veldo_fixture_bot')
        real_connect = socket.create_connection
        def guarded(address, *args, **kwargs):
            if address[0] != '127.0.0.1':
                raise OSError('only loopback is permitted')
            return real_connect(address, *args, **kwargs)
        socket.create_connection = guarded
        url, api, stop = H.stand_in({'bot169': bot_user})
        api['chats'][owner_user['id']] = dict(id=owner_user['id'], type='private', first_name='Owner')
        A = H.build(base / 'authority', mods, owner_user['id'], url, 'bot169')
        ing = None
        try:
            for who, kind, roles in (('worker', 'agent_run', []), ('andon', 'service', []),
                                      ('project-owner', 'person', ['project_owner'])):
                path = base / ('key-' + who)
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(path)],
                               check=True, capture_output=True, timeout=10)
                A.keyfile[who] = path
                A.public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
                A.admin('steward', 'enroll_principal', dict(principal=who, principal_type=kind, roles=roles,
                        public_key=A.public[who], independence_group=who, scope='*'), enrollee=who)
            ing = IN.open_ingress(str(A.config_path))
            A.authorize(ing.activations, 'qualify')
            rid, first = A.open_request(ing, 'Q169')
            good = H.deliver(api, 'bot169', owner_user, 'accept: qualify the fixture', reply_to=first['message_ids'][-1])
            bad = H.deliver(api, 'bot169', dict(id=5589169, is_bot=False, first_name='Stranger'), 'accept: unknown')
            ing.wake({'tick': 0})
            qid, qd, _ = ing.activations.qualify(ing.gate, ing.presenter, ing.acquirer, ing.settlement, rid,
                       EV.evidence_id(bot_user['id'], good['update_id']), EV.evidence_id(bot_user['id'], bad['update_id']))
            A.authorize(ing.activations, 'activate', qualification_id=qid, qualification_digest=qd)
            inbox, S = ing.inbox, ing.inbox.store
            claims = inbox.claims
            receiver = claims.Receiver(ing.conn, A.ids, 'authority', A.journal_sign)
            EL = claims.organ('control_eligibility')
            gate = EL.Gate(S, ing.conn, domain_uuid=A.ids['domain_uuid'], repository_uuid=A.ids['repository_uuid'])
            projects = PJ.Projects(S, inbox.membership, ing.conn, A.ids, 'authority', A.journal_sign,
                                    stop=lambda dispatch, reason: dict(outcome='stopped'))
            andon = AND.Andon(ing, AND.service_signer('andon', str(A.keyfile['andon'])), scope='project-a')
            def entity(eid):
                return S.materialized_state(ing.conn)['entities'].get(eid)
            def packet(who, operation, **extra):
                body = dict(A.ids, operation=operation, principal=who, command_id=A.next_id('cmd'),
                            nonce=A.next_id('nonce'), **extra)
                return A.signed_command(who, body)
            def activate(name):
                return projects.apply(packet('project-owner', 'activate', project=name, owner='project-owner',
                    charter=dict(purpose='Prove stopped handouts', exclusions=['billing']),
                    execution_repository=A.ids['repository_uuid'], authority_policy={'grooming': ['project_owner']},
                    coordination_budget=dict(capacity=4, invocations=40, wall_seconds=3600, owner_minutes=120)))
            def change(name, action):
                return projects.apply(packet('project-owner', action, project=name,
                    project_version=(entity('project:' + name) or {}).get('version'),
                    reason='Owner stops new work', disposition='Retain accepted history'))
            def unit(uid, project, state='READY'):
                A.fixture('backlog:' + uid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=A.ids['repository_uuid']))
                data = dict(state=state, repository_uuid=A.ids['repository_uuid'], backlog_item_uuid='backlog:' + uid,
                            requirements=[], eligible_holders=['worker'])
                if project != 'absent':
                    data['project'] = project
                A.fixture(uid, 'execution_unit', data)
            def claim(uid):
                return receiver.apply(packet('worker', 'claim', unit_id=uid, generation=0, capabilities=[]))
            def command(who, op, alias, **extra):
                return inbox.apply(packet(who, op, alias=alias, **extra))
            def release_held():
                for eid, record in list(S.materialized_state(ing.conn)['entities'].items()):
                    data = record['data']
                    if record['kind'] == 'claim' and data.get('state') == 'owned':
                        receiver.apply(packet('worker', 'release', unit_id=data['unit_id'], capabilities=[],
                                              generation=data['generation']))
            def prepare(path, uid, name, ruling='backlog', complete=False):
                release_held()
                unit(uid, name, 'RUNNING' if path == 'andon' else 'READY')
                if path == 'andon':
                    result = andon.raise_stop(packet('worker', 'raise', unit=uid, station='build', reason='Owner decision',
                           resolving=dict(principal='owner', roles=['project_owner']), effect='clean'))
                    sid = result.get('stop_id')
                    kept = andon.stop(sid) or {}
                    shown = ing.presenter.current(kept.get('request_id', '')) or {}
                    answer = dict(A.ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=A.next_id('api'),
                                  principal='owner', request_id=kept.get('request_id'), request_version=shown.get('request_version'),
                                  presentation_id=shown.get('presentation_id'), presentation_digest=shown.get('brief_digest'),
                                  presentation_version=shown.get('presentation_version'), choice='accept', rationale='Resume the unit')
                    answered = ing.settlement.api_answer(dict(answer=answer, signature=A.sign_as('api-edge', S.canonical_bytes(answer))))
                    return lambda: andon.resume(sid), [uid, sid], andon, result.get('outcome') == 'stopped' and answered.get('outcome') == 'settled'
                granted = claim(uid)
                completed = change(name, 'complete') if complete else {'ok': True}
                opened = command('worker', 'open', uid, claim_generation=granted.get('claim', {}).get('generation'),
                    assignment=dict(kind='decision', owner='owner', scope=['project-a'], deadline='2027-01-01T00:00:00Z',
                                    budget={'owner_minutes': 10}, brief='Decide the unit', choices=['accept'],
                                    subject=dict(kind='specification', ref='fixture-spec', digest=S.digest_of(uid))))
                alias = uid
                if path == 'dispose':
                    ended = command('owner', 'decline', uid, request_version=1)
                    question = inbox.read(ended.get('question_id') or '') or {}
                    alias = (question.get('data') or {}).get('alias', 'missing')
                extras = {}
                if ruling == 'other' and path == 'dispose':
                    request = dict(schema='veldo.intake_api_request/v1', domain=A.ids['domain_uuid'], edge='api-edge',
                                   request_id=A.next_id('intake'), principal='owner', text='Keep this instruction',
                                   project='project-a', clarifies=None)
                    extras = dict(instruction='Keep this instruction', arrived_on=dict(source_kind='api_request', request=request,
                                  signature=A.sign_as('api-edge', S.canonical_bytes(request))))
                answer = command('owner', 'answer', alias, request_version=1,
                                 ruling=ruling if path == 'dispose' else 'accept', **extras)
                ids = [uid, 'backlog:' + uid, claims.claim_id(A.ids['repository_uuid'], uid), A.assignment_id(alias)]
                return (lambda: command('worker', 'dispose' if path == 'dispose' else 'resume', alias,
                                        request_version=1, capabilities=[])), ids, inbox, all(x.get('ok') for x in (granted, completed, opened, answer))

            states = ('PAUSED', 'CANCELED', 'COMPLETED', 'owner_not_current', 'race')
            for path in ('resume', 'dispose', 'andon'):
                for state in states:
                    with region(path + '/' + state):
                        row = path + '/' + state
                        name, uid = 'p-' + path + '-' + state.lower(), 'u-' + path + '-' + state.lower()
                        check(row, 'project activated by its owner', activate(name).get('ok'))
                        action, watched, service, ready = prepare(path, uid, name, complete=state == 'COMPLETED' and path != 'andon')
                        check(row, 'real park or stop and admitted answer', ready)
                        expected_reason = 'stale_version' if state == 'race' else 'project_not_active:' + state
                        if state in ('PAUSED', 'CANCELED', 'COMPLETED') and not (state == 'COMPLETED' and path != 'andon'):
                            check(row, 'owner committed lifecycle command', change(name, dict(PAUSED='pause', CANCELED='cancel', COMPLETED='complete')[state]).get('ok'))
                        elif state == 'owner_not_current':
                            A.admin('steward', 'change_roles', dict(principal='project-owner', roles=[]))
                        before = {eid: entity(eid) for eid in watched}
                        count = ing.conn.execute('SELECT count(*) FROM entities WHERE kind=?', ('andon_station_contract',)).fetchone()[0]
                        pause = []
                        original = S.execute
                        def racing(conn, cmd, *args, **kwargs):
                            if not pause and cmd.get('operation') in ('assignment_operation', AND.OPERATION):
                                pause.append(change(name, 'pause'))
                            return original(conn, cmd, *args, **kwargs)
                        if state == 'race':
                            S.execute = racing
                        try:
                            result = action()
                        finally:
                            S.execute = original
                        check(row, 'Gate refusal ' + str(result.get('reason')), result.get('reason') == expected_reason)
                        check(row, 'claim, park, stop and unit unchanged', before == {eid: entity(eid) for eid in watched})
                        check(row, 'no station contract issued', count == ing.conn.execute('SELECT count(*) FROM entities WHERE kind=?', ('andon_station_contract',)).fetchone()[0])
                        obs = service.observations[-1]
                        check(row, 'refusal names project and read versions', obs.get('project') == name
                              and {'project:' + name, 'project-owner'} <= obs.get('accepted_versions', {}).keys() and obs.get('reason') == expected_reason)
                        check(row, 'refusal counted by reason', service.counts.get('refused_by_reason', {}).get(expected_reason, 0) > 0)
                        if state == 'race':
                            check(row, 'pause committed between check and write', bool(pause) and pause[0].get('ok'))
                        if state == 'owner_not_current':
                            A.admin('steward', 'change_roles', dict(principal='project-owner', roles=['project_owner']))
                        if state == 'race':
                            owner_project = name + '-owner'
                            activate(owner_project)
                            owner_action, owner_watched, _, owner_ready = prepare(path, uid + '-owner', owner_project)
                            owner_before = {eid: entity(eid) for eid in owner_watched}
                            moved = []
                            def owner_racing(conn, cmd, *args, **kwargs):
                                if not moved and cmd.get('operation') in ('assignment_operation', AND.OPERATION):
                                    moved.append(True)
                                    A.admin('steward', 'change_roles', dict(principal='project-owner', roles=[]))
                                return original(conn, cmd, *args, **kwargs)
                            S.execute = owner_racing
                            try:
                                owner_result = owner_action()
                            finally:
                                S.execute = original
                            check(row, 'owner read pinned through commit', owner_ready and moved
                                  and owner_result.get('reason') == 'stale_version'
                                  and owner_before == {eid: entity(eid) for eid in owner_watched})
                            A.admin('steward', 'change_roles', dict(principal='project-owner', roles=['project_owner']))
                        # Each row also has a positive control on the same production path.
                        live = name + '-active'
                        activate(live)
                        proceed, _, _, prepared = prepare(path, uid + '-active', live)
                        accepted = proceed()
                        check(row, 'active control takes work', prepared and (accepted.get('ok') or accepted.get('outcome') == 'resumed'))
                        if path == 'resume' and accepted.get('ok'):
                            receiver.apply(packet('worker', 'release', unit_id=uid + '-active', capabilities=[],
                                                  generation=(entity(claims.claim_id(A.ids['repository_uuid'], uid + '-active')) or {})['data']['generation']))
            for project in ('absent', None):
                with region('claim/' + ('absent' if project == 'absent' else 'null')):
                    row = 'claim/' + ('absent' if project == 'absent' else 'null')
                    uid = 'unit-' + row.replace('/', '-')
                    unit(uid, project)
                    before = S.materialized_state(ing.conn)
                    result = claim(uid)
                    check(row, 'missing project refused', result.get('reason') == 'missing_authority:project')
                    check(row, 'nothing written', before == S.materialized_state(ing.conn))
                    obs = receiver.observations[-1]
                    check(row, 'missing project refusal observed and counted', obs.get('unit_id') == uid
                          and obs.get('reason') == 'missing_authority:project'
                          and obs.get('accepted_versions', {}).get('project:None') == 0
                          and receiver.counts.get('refused_by_reason', {}).get('missing_authority:project', 0) > 0)
                    check(row, 'same Gate refusal', gate.project_problems(uid)[0] == ['missing_authority:project'])
                    live = uid + '-active'
                    activate(live)
                    unit(live, live)
                    accepted = claim(live)
                    check(row, 'active project accepted', accepted.get('ok'))
            with region('dispose/PAUSED'):
                # Non-handout dispositions still apply while the project is paused.
                IT = load('v169_intake', mods / 'control_intake.py')
                activate('factory')
                inbox.intake = IT.Intake(S, inbox.membership, inbox.AC, ing.acquirer, ing.conn,
                                        domain=A.ids['domain_uuid'], projects=['project-a', 'factory'], api_edge='api-edge',
                                        journal_signer='authority', sign=A.journal_sign)
                for ruling in ('close', 'other'):
                    row = 'dispose/PAUSED'
                    name = 'p-no-handout-' + ruling
                    activate(name)
                    action, _, _, prepared = prepare('dispose', 'u-no-handout-' + ruling, name, ruling)
                    change(name, 'pause')
                    check(row, ruling + ' remains available', prepared and action().get('ok'))

            # VELDO-0169 lead decisions: the claim organ and the station contract writer ask the Gate's project
            # check themselves inside the write transaction, callers pass nothing, and the store writes a claim
            # only as the organ returned it in that same transaction.
            repository = A.ids['repository_uuid']
            DIRECT = 'v169_direct_handout'
            # A path that forgot the caller's check: the organ registered bare, pinning only the claim's own
            # records, never the project's.
            ing.conn.command_registry[DIRECT] = {'transaction_transition': claims.transition,
                                                 'writes': ('entities', 'journal', 'commands', 'nonces')}

            def pins(uid):
                cid = claims.claim_id(repository, uid)
                return {eid: (entity(eid) or {}).get('version', 0) for eid in (uid, 'backlog:' + uid, cid)}

            def run(operation, params, versions):
                """(outcome, nothing written): a store command, accepted or refused by name."""
                before = S.materialized_state(ing.conn)
                try:
                    S.execute(ing.conn, dict(command_id=A.next_id('direct'), principal='worker', operation=operation,
                                             parameters=params, expected_versions=versions, artifact_digests=[],
                                             nonce=A.next_id('direct-n')), 'authority', A.journal_sign, 1)
                    outcome = 'accepted'
                except S.StoreRefused as exc:
                    outcome = exc.code
                except Exception as exc:  # noqa: BLE001 - a raise is an outcome the row names, never a pass
                    outcome = 'raised %s' % type(exc).__name__
                return outcome, before == S.materialized_state(ing.conn)

            def direct(uid, action, parked_on=None, **extra):
                params = dict(action=action, unit_id=uid, backlog_item_uuid='backlog:' + uid,
                              claim_id=claims.claim_id(repository, uid), holder='worker', generation=0,
                              capabilities=[], repository_uuid=repository, **extra)
                if parked_on is not None:
                    params['parked_on'] = parked_on
                return run(DIRECT, params, pins(uid))

            HAND = 'v169_hand_built'

            def hand_built(conn, params, before):
                # A transition that builds its claim record by hand, as any module could, and says what it likes
                # about itself on the connection (the reviewer's inject probe, rv169c): only the store decides.
                conn.organ_writes = {params['claim']: S.digest_of({'kind': 'claim', 'data': params['data']})}
                return dict({params['claim']: {'kind': 'claim', 'data': params['data']}}, **params['also'])
            ing.conn.command_registry[HAND] = {'transaction_transition': hand_built,
                                               'writes': ('entities', 'journal', 'commands', 'nonces')}

            def record(uid, handout, parked_on=None, unit_id=None):
                """The claim record a handout (or a renewal or release) of `uid` writes, built by hand."""
                current = dict((entity(claims.claim_id(repository, uid)) or {}).get('data') or {})
                named = unit_id or uid
                if handout in ('claim', 'resume'):
                    data = dict(unit_id=named, backlog_item_uuid='backlog:' + named, repository_uuid=repository,
                                holder='worker', generation=current.get('generation', 0) + 1, state='owned',
                                heartbeat_at=claims.CL._now())
                    if handout == 'resume':
                        data['resumed_from'] = parked_on
                    return data
                if handout == 'unpark':
                    return dict({k: v for k, v in current.items() if k != 'parked_on'}, state='released', holder=None,
                                unparked_from=parked_on)
                if handout == 'renew':
                    return dict(current, heartbeat_at=claims.CL._now())
                return dict(current, state='released', holder=None)

            def hand(uid, handout, parked_on=None, also=None, unit_id=None):
                """(outcome, nothing written) of a hand-built claim record of `uid`, with `also` in the same write; a
                claim or resume also marks the unit claimed and its backlog item active, as the organ's own does."""
                also = dict(also or {})
                if handout in ('claim', 'resume'):
                    held = also.get(uid) or entity(uid)
                    also[uid] = {'kind': 'execution_unit', 'data': dict(held['data'], state='CLAIMED')}
                    also['backlog:' + uid] = {'kind': 'backlog_item', 'data': dict(entity('backlog:' + uid)['data'], state='ACTIVE')}
                params = dict(claim=claims.claim_id(repository, uid), data=record(uid, handout, parked_on, unit_id),
                              also=also)
                versions = dict(pins(uid), **{eid: (entity(eid) or {}).get('version', 0) for eid in params['also']})
                return run(HAND, params, versions)

            def ineligible(uid, name):
                """A unit of project `name` the worker may not hold, so the claim organ has a second reason to refuse."""
                unit(uid, name)
                A.fixture(uid, 'execution_unit', dict(entity(uid)['data'], eligible_holders=['someone-else']))

            def parks(uids, name, stop=None):
                """Units of project `name`, each claimed, parked on an assignment and answered in turn (an opener
                holds one claim), and the assignment each waits on; `stop` runs after the last claim and before
                its assignment opens (a completed project takes no new claim, but its parked work is answered)."""
                release_held()
                steps = []
                for uid in uids:
                    unit(uid, name)
                    granted = claim(uid)
                    steps.append(granted.get('ok'))
                    if stop is not None and uid == uids[-1]:
                        steps.append(stop().get('ok'))
                    steps.append(command('worker', 'open', uid, claim_generation=granted.get('claim', {}).get('generation'),
                        assignment=dict(kind='decision', owner='owner', scope=['project-a'], deadline='2027-01-01T00:00:00Z',
                                        budget={'owner_minutes': 10}, brief='Decide the unit', choices=['accept'],
                                        subject=dict(kind='specification', ref='fixture-spec', digest=S.digest_of(uid)))).get('ok'))
                    steps.append(command('owner', 'answer', uid, request_version=1, ruling='accept').get('ok'))
                return all(steps), {uid: A.assignment_id(uid) for uid in uids}

            ISSUE = 'v169_station_probe'
            issued = []

            def station_probe(params, before):
                # The station contract writer inside a command transaction, reached without Andon.resume's
                # check; what it returns is recorded, and nothing is written (the kind is the andon's own).
                issued.append(andon.issue_station_contract(params['contract'], before))
                return {}
            ing.conn.command_registry[ISSUE] = {'transition': station_probe, 'writes': ('entities', 'journal', 'commands', 'nonces')}

            def station(uid):
                contract = dict(contract_id='andon-station-contract:v169-probe:' + uid, unit=uid)
                del issued[:]
                outcome, unchanged = run(ISSUE, dict(contract=contract), {uid: (entity(uid) or {}).get('version', 0)})
                return outcome, unchanged and not (outcome != 'accepted' and issued)

            with region('organ/stopped'):
                # Each handout path with no caller check and nothing passed: the organ's claim, resume and unpark,
                # and the station contract writer, over a paused, canceled, completed and owner-not-current project.
                row = 'organ/stopped'
                for state in ('PAUSED', 'CANCELED', 'COMPLETED', 'owner_not_current'):
                    name = 'p-organ-' + state.lower()
                    check(row, state + ': project activated by its owner', activate(name).get('ok'))
                    # One parked unit takes both the resume and the unpark, each refused with nothing written (a
                    # project completes only with no open assignment, so it has one parked unit at most).
                    parked_u, fresh = ('u-organ-%s-%s' % (state.lower(), k) for k in ('parked', 'fresh'))
                    lifecycle = lambda: change(name, dict(PAUSED='pause', CANCELED='cancel', COMPLETED='complete')[state])
                    ready, source = parks([parked_u], name, stop=lifecycle if state == 'COMPLETED' else None)
                    check(row, state + ': real parks on answered assignments', ready)
                    if state == 'owner_not_current':
                        A.admin('steward', 'change_roles', dict(principal='project-owner', roles=[]))
                    elif state != 'COMPLETED':
                        check(row, state + ': owner committed lifecycle command', lifecycle().get('ok'))
                    unit(fresh, name)
                    expected = 'project_not_active:' + state
                    for label, (outcome, unchanged) in (
                            ('claim', direct(fresh, 'claim')),
                            ('resume', direct(parked_u, 'resume', parked_on=source[parked_u])),
                            ('unpark', direct(parked_u, 'unpark', parked_on=source[parked_u])),
                            ('station contract', station(fresh)),
                            ('hand-built claim', hand(fresh, 'claim')),
                            ('hand-built resume', hand(parked_u, 'resume', source[parked_u])),
                            ('hand-built unpark', hand(parked_u, 'unpark', source[parked_u]))):
                        check(row, '%s: %s refused as %s, nothing written' % (state, label, outcome),
                              outcome == expected and unchanged)
                    # The organ's own check refuses first: a unit the worker may not hold is refused by the Gate's name.
                    ineligible(fresh + '-other', name)
                    outcome, unchanged = direct(fresh + '-other', 'claim')
                    check(row, '%s: the organ names the project before any other reason (%s)' % (state, outcome),
                          outcome == expected and unchanged)
                    if state == 'owner_not_current':
                        A.admin('steward', 'change_roles', dict(principal='project-owner', roles=['project_owner']))
                live = 'p-organ-active'
                check(row, 'control: project activated by its owner', activate(live).get('ok'))
                ready, source = parks(['u-organ-active-resume', 'u-organ-active-unpark'], live)
                unit('u-organ-active', live)
                for label, outcome in (('claim', direct('u-organ-active', 'claim')[0]),
                                       ('resume', direct('u-organ-active-resume', 'resume', parked_on=source['u-organ-active-resume'])[0]),
                                       ('unpark', direct('u-organ-active-unpark', 'unpark', parked_on=source['u-organ-active-unpark'])[0])):
                    check(row, 'control: the same %s of an active project is taken (%s)' % (label, outcome),
                          ready and outcome == 'accepted')
                unit('u-organ-active-hand', live)
                outcome, _ = hand('u-organ-active-hand', 'claim')
                check(row, 'control: a hand-built claim of an active project is written (%s)' % outcome, outcome == 'accepted')
                ineligible('u-organ-active-other', live)
                outcome, _ = direct('u-organ-active-other', 'claim')
                check(row, 'control: the organ refuses the unit the worker may not hold (%s)' % outcome, outcome == 'not_authorized')
                outcome, _ = station('u-organ-active')
                check(row, 'control: the station contract writer issues it for an active project (%s)' % outcome,
                      outcome == 'accepted' and issued and list(issued[-1]) == ['andon-station-contract:v169-probe:u-organ-active'])
                release_held()

            with region('organ/outside'):
                # No station contract is issued before the write transaction holds its lock (a claim record is
                # decided wherever it is built, and the store checks it in the commit path: store/invariant).
                row = 'organ/outside'
                release_held()
                name, uid = 'p-organ-outside', 'u-organ-outside'
                check(row, 'project activated by its owner', activate(name).get('ok'))
                unit(uid, name)
                params = dict(action='claim', unit_id=uid, backlog_item_uuid='backlog:' + uid,
                              claim_id=claims.claim_id(repository, uid), holder='worker', generation=0,
                              capabilities=[], repository_uuid=repository)
                snapshot = {eid: dict(record) for eid, record in S.materialized_state(ing.conn)['entities'].items()}
                for label, attempt in (('the station contract writer', lambda: andon.issue_station_contract(
                                           dict(contract_id='andon-station-contract:v169-outside', unit=uid), snapshot)),):
                    try:
                        attempt()
                        outcome = 'decided outside a transaction'
                    except S.StoreRefused as exc:
                        outcome = exc.code
                    except Exception as exc:  # noqa: BLE001 - a raise is an outcome the row names
                        outcome = 'raised %s' % type(exc).__name__
                    check(row, '%s refuses to decide outside a command transaction (%s)' % (label, outcome),
                          outcome == 'outside_transaction')
                outcome, _ = direct(uid, 'claim')
                check(row, 'control: the same claim inside its transaction is taken (%s)' % outcome, outcome == 'accepted')
                release_held()

            with region('store/invariant', 'guard/forge'):
                # The store's commit path refuses every claim record that hands out work of a stopped project, whoever
                # built it: the reviewer's inject probe, a claim built by hand, the generic upsert, a resume and an
                # unpark built by hand, a record whose id names another unit than its fields, and one transaction
                # that moves a unit into a paused project and claims it. A renewal and a release of a claim already
                # held pass unchanged, and a claim built by hand for an active project is written.
                row = 'store/invariant'
                release_held()
                name, live = 'p-store-paused', 'p-store-live'
                check(row, 'projects activated by their owner', activate(name).get('ok') and activate(live).get('ok'))
                ready, source = parks(['u-store-parked'], name)
                check(row, 'a real park on an answered assignment', ready)
                unit('u-store-held', name)
                check(row, 'a claim held before the pause', claim('u-store-held').get('ok'))
                for uid in ('u-store-fresh', 'u-store-live', 'u-store-moved'):
                    unit(uid, live if uid != 'u-store-fresh' else name)
                check(row, 'the owner paused the project', change(name, 'pause').get('ok'))
                expected = 'project_not_active:PAUSED'
                fresh_cid = claims.claim_id(repository, 'u-store-fresh')
                moved = {'u-store-moved': {'kind': 'execution_unit', 'data': dict(entity('u-store-moved')['data'],
                                                                                  project=name)}}
                built = record('u-store-fresh', 'claim')
                for label, (outcome, unchanged) in (
                        ('the inject probe (a hand-built claim that sets conn.organ_writes itself)',
                         hand('u-store-fresh', 'claim')),
                        ('a claim entity built by hand, alone', run(HAND, dict(claim=fresh_cid, data=built, also={}),
                                                                   pins('u-store-fresh'))),
                        ('a claim written by the generic upsert', run('upsert_entity', dict(entity_id=fresh_cid, kind='claim',
                                                                                            data=built), pins('u-store-fresh'))),
                        ('a resume built by hand', hand('u-store-parked', 'resume', source['u-store-parked'])),
                        ('an unpark built by hand', hand('u-store-parked', 'unpark', source['u-store-parked'])),
                        ('a record whose id names the paused unit and whose fields name an active one',
                         hand('u-store-fresh', 'claim', unit_id='u-store-live')),
                        ('one transaction moving an active unit into the paused project and claiming it',
                         hand('u-store-moved', 'claim', also=moved))):
                    check(row, '%s refused as %s, nothing written' % (label, outcome), outcome == expected and unchanged)
                # A claim written under another kind at a claim id: its readers find a claim by id, never by kind.
                outcome, unchanged = run('upsert_entity', dict(entity_id=fresh_cid, kind='Claim', data=built), pins('u-store-fresh'))
                check(row, 'a claim written under another kind at a claim id refused as %s, nothing written' % outcome,
                      outcome == 'invalid_input:claim_kind' and unchanged)
                check(row, 'no claim of the paused project\'s fresh unit exists', entity(fresh_cid) is None)
                for label in ('renew', 'release'):
                    outcome, _ = hand('u-store-held', label)
                    check(row, 'a %s of the claim held before the pause passes (%s)' % (label, outcome), outcome == 'accepted')
                outcome, _ = hand('u-store-live', 'claim')
                check(row, 'control: a claim built by hand for an active project is written (%s)' % outcome,
                      outcome == 'accepted' and (entity(claims.claim_id(repository, 'u-store-live')) or {}).get(
                          'data', {}).get('holder') == 'worker')
                release_held()

                # The forge probe (rv169b) on a paused project, with no receipt anywhere to forge: a claim carrying a
                # literal project check, one carrying another unit's rewritten check, and a claim entity built by hand.
                row = 'guard/forge'
                forged, other = 'p-forge', 'p-forge-other'
                check(row, 'projects activated by their owner', activate(forged).get('ok') and activate(other).get('ok'))
                unit('u-forge', forged)
                unit('u-forge-other', other)
                read = dict(gate.project_problems('u-forge')[1])
                check(row, 'the paused project is refused by the Gate', change(forged, 'pause').get('ok')
                      and gate.project_problems('u-forge')[0] == ['project_not_active:PAUSED'])
                literal = {'schema': 'veldo.project_check/v1', 'unit': 'u-forge', 'project': forged, 'read': read}
                rewritten = dict(unit='u-forge-other', project=other, read=dict(gate.project_problems('u-forge-other')[1]))
                rewritten.update(unit='u-forge', project=forged, read=read)
                fcid = claims.claim_id(repository, 'u-forge')
                for label, (outcome, unchanged), expected in (
                        ('a literal project check', direct('u-forge', 'claim', project_check=literal), 'project_not_active:PAUSED'),
                        ('another unit\'s check, rewritten', direct('u-forge', 'claim', project_check=rewritten),
                         'project_not_active:PAUSED'),
                        ('a claim entity built by hand', hand('u-forge', 'claim'), 'project_not_active:PAUSED')):
                    check(row, '%s on the paused project refused as %s, nothing written' % (label, outcome),
                          outcome == expected and unchanged)
                check(row, 'no claim of the paused project\'s unit exists', entity(fcid) is None
                      and (entity('project:' + forged) or {}).get('data', {}).get('state') == 'PAUSED')
                check(row, 'control: the project resumed, the same claim is taken',
                      change(forged, 'resume').get('ok') and direct('u-forge', 'claim')[0] == 'accepted')
                release_held()

            with region('organ/race'):
                # The owner pauses and resumes the project from a second process while claims run, several rounds,
                # with a delay between the receiver's check and its write, and through the organ bare (no caller
                # check, nothing pinned): no claim is ever written while the project is not ACTIVE.
                row = 'organ/race'
                release_held()
                name = 'p-organ-race'
                check(row, 'project activated by its owner', activate(name).get('ok'))
                unit('u-race-seq', name)
                # A check reused from an earlier transaction is a check outside this one.
                first = direct('u-race-seq', 'claim')[0]
                release_held()
                paused = change(name, 'pause').get('ok')
                # The worker may no longer hold the unit either, so only the organ's own check, made in this
                # transaction, names the project.
                A.fixture('u-race-seq', 'execution_unit', dict(entity('u-race-seq')['data'], eligible_holders=['someone-else']))
                second = direct('u-race-seq', 'claim')[0]
                check(row, 'a claim taken, released, the project paused: the next claim is refused (%s, %s)' % (first, second),
                      first == 'accepted' and paused and second == 'project_not_active:PAUSED')
                check(row, 'the project is resumed', change(name, 'resume').get('ok'))
                flipper = base / 'v169_flipper.py'
                flipper.write_text(_V169_FLIPPER)
                db = [r[2] for r in ing.conn.execute('PRAGMA database_list').fetchall() if r[1] == 'main'][0]
                original = S.execute

                def slow(conn, command, *args, **kwargs):
                    if command.get('operation') in ('claim_operation', DIRECT):
                        time.sleep(0.02)
                    return original(conn, command, *args, **kwargs)
                taken, refused_while, flips = 0, collections.Counter(), collections.Counter()
                units = []
                for round_ in range(3):
                    batch = ['u-race-%d-%d' % (round_, i) for i in range(4)]
                    for uid in batch:
                        unit(uid, name)
                    units += batch
                    log = base / ('v169_flips_%d.json' % round_)
                    process = subprocess.Popen([sys.executable, str(flipper), str(mods), db, json.dumps(A.ids),
                                                str(A.keyfile['project-owner']), str(A.keyfile['authority']), name, '24', str(log)])
                    S.execute = slow
                    try:
                        while process.poll() is None:
                            for i, uid in enumerate(batch):
                                if i % 2:
                                    outcome = direct(uid, 'claim')[0]
                                else:
                                    result = claim(uid)
                                    outcome = 'accepted' if result.get('ok') else result.get('reason')
                                refused_while[outcome] += 1
                                if outcome == 'accepted':
                                    release_held()
                    finally:
                        S.execute = original
                    process.wait(timeout=60)
                    flips.update(tuple(x) for x in json.loads(log.read_text()))
                    if (entity('project:' + name) or {}).get('data', {}).get('state') != 'ACTIVE':
                        change(name, 'resume')
                state, bad = None, []
                for seq, transition in ing.conn.execute('SELECT seq, transition FROM journal ORDER BY seq'):
                    records = json.loads(transition)
                    if 'project:' + name in records:
                        state = records['project:' + name]['data'].get('state')
                    for eid, record in records.items():
                        if record['kind'] == 'claim' and record['data'].get('unit_id') in units + ['u-race-seq'] \
                                and record['data'].get('state') == 'owned':
                            taken += 1
                            if state != 'ACTIVE':
                                bad.append((seq, eid, state))
                check(row, 'the second process paused and resumed the project (%s)' % dict(flips),
                      flips.get(('pause', True), 0) >= 6 and flips.get(('resume', True), 0) >= 6)
                check(row, 'claims were taken and refused while it did (%s)' % dict(refused_while),
                      refused_while.get('accepted', 0) > 0 and sum(v for k, v in refused_while.items() if k != 'accepted') > 0)
                check(row, 'no claim written while the project was not ACTIVE (%d taken, %s)' % (taken, bad[:3]),
                      taken > 0 and not bad)
                print('  VELDO-0169 race: ' + json.dumps(dict(flips={'%s %s' % k: v for k, v in flips.items()},
                                                              outcomes=dict(refused_while), taken=taken, bad=bad[:3]), sort_keys=True))

            # The reviewer's falsifier at run time: a copy of the resume without the project check, wired into
            # the inbox with a write of its own or through the resume's write, over a paused project: the claim
            # organ refuses it by the Gate's name and writes nothing.
            for writer in ('own', 'shared'):
                with region('guard/resume-again'):
                    row = 'guard/resume-again'
                    name, uid = 'p-again-' + writer, 'u-again-' + writer
                    check(row, 'project activated by its owner', activate(name).get('ok'))
                    _, watched, _, ready = prepare('resume', uid, name)
                    check(row, writer + ' writer: the project paused', change(name, 'pause').get('ok'))
                    path = base / ('control_assignment_again_' + writer + '.py')
                    try:
                        path.write_text(resume_again((mods / 'control_assignment.py').read_text(), writer))
                    except LookupError as missing:
                        check(row, 'the copy is built on the installed inbox (%s)' % missing, False)
                        continue
                    AG = load('v169_again_' + writer, path)
                    saved = ing.conn.command_registry[AG.OPERATION]
                    try:
                        again = AG.Inbox(S, inbox.membership, claims, inbox.contract, ing.conn, dict(inbox.ids),
                                         inbox.journal_signer, inbox.sign, authority_generation=inbox.authority_generation,
                                         clock=inbox.clock, intake=inbox.intake)
                        before = {eid: entity(eid) for eid in watched}
                        try:
                            result = again.apply(packet('worker', 'resume_again', alias=uid, request_version=1, capabilities=[]))
                        except Exception as error:  # noqa: BLE001 - a raise is an outcome the row names
                            result = {'ok': False, 'reason': 'raised %s' % type(error).__name__}
                    finally:
                        ing.conn.command_registry[AG.OPERATION] = saved
                    check(row, writer + ' writer: parked work and answered assignment', ready)
                    check(row, writer + ' writer: refused by the claim organ as ' + str(result.get('reason')),
                          result.get('reason') == 'project_not_active:PAUSED')
                    check(row, writer + ' writer: claim, park and unit unchanged', before == {eid: entity(eid) for eid in watched})
                    resumed = change(name, 'resume').get('ok') and command('worker', 'resume', uid, request_version=1, capabilities=[])
                    check(row, writer + ' writer: control: the project resumed, the real resume takes the same work',
                          bool(resumed) and resumed.get('ok'))
                    release_held()

            with region('andon/subject-race'):
                # A resume race that is not a project race keeps its VELDO-0075 name, stale_subject.
                row = 'andon/subject-race'
                name, uid = 'p-andon-subject', 'u-andon-subject'
                check(row, 'project activated by its owner', activate(name).get('ok'))
                action, watched, service, ready = prepare('andon', uid, name)
                check(row, 'real stop and settled answer', ready)
                before = {eid: entity(eid) for eid in watched}
                count = ing.conn.execute('SELECT count(*) FROM entities WHERE kind=?', ('andon_station_contract',)).fetchone()[0]
                bumped = []
                original = S.execute

                def subject_racing(conn, cmd, *args, **kwargs):
                    if not bumped and cmd.get('operation') == AND.OPERATION:
                        bumped.append(A.admin('steward', 'change_roles', dict(principal='worker', roles=[])))
                    return original(conn, cmd, *args, **kwargs)
                S.execute = subject_racing
                try:
                    result = action()
                finally:
                    S.execute = original
                check(row, 'a membership write, not a project one, committed between check and write', bool(bumped))
                check(row, 'refused as ' + str(result.get('reason')), result.get('reason') == 'stale_subject')
                check(row, 'stop and unit unchanged, no station contract', before == {eid: entity(eid) for eid in watched}
                      and count == ing.conn.execute('SELECT count(*) FROM entities WHERE kind=?', ('andon_station_contract',)).fetchone()[0])
                check(row, 'control: the same stop then resumes', action().get('outcome') == 'resumed')

            with region('store/upgrade'):
                # A store written before VELDO-0169 (the reviewer's upgrade probe, rv169c): claims held, released and
                # parked on units that name no project, as main's claim organ wrote them. This branch's claim
                # receiver and assignment inbox attach to it unchanged, the held claim is renewed and released, and a
                # new claim is refused by the Gate's name until its unit's project is active.
                row = 'store/upgrade'
                PLANT = load('v169_rows', ROOT / 'scripts' / 'suites' / 'support' / 'v169_rows.py')
                (base / 'upgrade' / 'authority').mkdir(parents=True)
                old = S.open_store(str(base / 'upgrade' / 'authority' / 'control.sqlite3'))
                try:
                    old_ids = dict(domain_uuid='domain-upgrade', repository_uuid='repo-upgrade', store_uuid='store-upgrade')
                    old_repo = old_ids['repository_uuid']

                    def old_entity(eid):
                        return S.materialized_state(old)['entities'].get(eid)

                    def old_run(operation, params, ids):
                        try:
                            S.execute(old, dict(command_id=A.next_id('upgrade'), principal='authority', operation=operation,
                                                parameters=params, artifact_digests=[], nonce=A.next_id('upgrade-n'),
                                                expected_versions={eid: (old_entity(eid) or {}).get('version', 0) for eid in ids}),
                                      'authority', A.journal_sign, 1)
                            return 'accepted'
                        except S.StoreRefused as exc:
                            return exc.code
                        except Exception as exc:  # noqa: BLE001 - a raise is an outcome the row names, never a pass
                            return 'raised %s' % type(exc).__name__

                    def old_put(eid, kind, data):
                        return old_run('upsert_entity', dict(entity_id=eid, kind=kind, data=data), [eid])

                    old_put('holder-u', 'membership', dict(principal_type='service', roles=[], scope=[old_repo],
                                                           revoked_at=None, expires_at=None))
                    units = ('u-old-held', 'u-old-released', 'u-old-parked')
                    for uid in units:
                        old_put('backlog:' + uid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=old_repo))
                        old_put(uid, 'execution_unit', dict(state='READY', repository_uuid=old_repo, backlog_item_uuid='backlog:' + uid,
                                                            requirements=[], eligible_holders=['holder-u']))

                    def organ(uid, action, generation=0, **extra):
                        return dict(action=action, unit_id=uid, backlog_item_uuid='backlog:' + uid,
                                    claim_id=claims.claim_id(old_repo, uid), holder='holder-u', generation=generation,
                                    capabilities=[], repository_uuid=old_repo, **extra)

                    # The records main's claim organ writes for a claim, and then for its release or park, planted as a
                    # store written before the handout invariant holds them.
                    for uid, then in (('u-old-held', None), ('u-old-released', 'release'), ('u-old-parked', 'park')):
                        data = dict(unit_id=uid, backlog_item_uuid='backlog:' + uid, repository_uuid=old_repo, holder='holder-u',
                                    generation=1, state='owned', heartbeat_at=claims.CL._now())
                        if then is not None:
                            data.update(state='released', holder=None)
                        if then == 'park':
                            data['parked_on'] = 'assignment:old'
                        PLANT.plant(S, old, claims.claim_id(old_repo, uid), 'claim', data)
                        PLANT.plant(S, old, uid, 'execution_unit', dict(old_entity(uid)['data'], state='CLAIMED'))
                        PLANT.plant(S, old, 'backlog:' + uid, 'backlog_item', dict(old_entity('backlog:' + uid)['data'], state='ACTIVE'))
                    held = {uid: (old_entity(claims.claim_id(old_repo, uid)) or {}).get('data', {}) for uid in units}
                    check(row, 'the store holds a held, a released and a parked claim (%s)' % {
                          k: (v.get('state'), v.get('parked_on')) for k, v in held.items()},
                          [(held[u].get('state'), held[u].get('parked_on')) for u in units]
                          == [('owned', None), ('released', None), ('released', 'assignment:old')])
                    for label, attach in (('the claim receiver', lambda: claims.Receiver(old, old_ids, 'authority', A.journal_sign)),
                                          ('the assignment inbox', lambda: type(inbox)(S, inbox.membership, claims, inbox.contract, old,
                                                                                       dict(old_ids), 'authority', A.journal_sign))):
                        try:
                            attach()
                            outcome = 'attached'
                        except Exception as exc:  # noqa: BLE001 - a refusal at attach is the defect this row names
                            outcome = '%s %s' % (type(exc).__name__, getattr(exc, 'code', exc))
                        check(row, '%s attaches to the earlier store (%s)' % (label, outcome), outcome == 'attached')
                    old.command_registry[DIRECT] = {'transaction_transition': claims.transition,
                                                    'writes': ('entities', 'journal', 'commands', 'nonces')}

                    def old_organ(uid, action, **extra):
                        cid = claims.claim_id(old_repo, uid)
                        generation = (old_entity(cid) or {}).get('data', {}).get('generation', 0)
                        return old_run(DIRECT, organ(uid, action, generation, **extra), [uid, 'backlog:' + uid, cid])
                    renewed, released = old_organ('u-old-held', 'renew'), old_organ('u-old-held', 'release')
                    check(row, 'the claim held before the upgrade is renewed and released (%s, %s)' % (renewed, released),
                          renewed == released == 'accepted')
                    before = S.materialized_state(old)
                    refused = old_organ('u-old-released', 'claim')
                    check(row, 'a new claim of a unit naming no project is refused by the Gate\'s name (%s)' % refused,
                          refused == 'missing_authority:project' and before == S.materialized_state(old))
                    old_put('owner-u', 'membership', dict(principal_type='person', roles=['project_owner'], scope='*',
                                                          revoked_at=None, expires_at=None))
                    old_put('project:p-upgrade', 'project', dict(name='p-upgrade', state='ACTIVE', owner='owner-u'))
                    old_put('u-old-released', 'execution_unit', dict(old_entity('u-old-released')['data'], project='p-upgrade'))
                    taken = old_organ('u-old-released', 'claim')
                    check(row, 'control: with its project active the same unit is claimed (%s)' % taken, taken == 'accepted')
                finally:
                    old.close()
        finally:
            if ing is not None:
                ing.conn.close()
            A.conn.close()
            stop()
            socket.create_connection = real_connect
    for row in DECLARED:
        if row not in rows:
            check(row, 'ran to its end: not reached', False)
    for row, parts in rows.items():
        failed = [label for label, ok in parts if not ok]
        if failed:
            print('  VELDO-0169 detail: ' + row + ': ' + '; '.join(failed))
        expect('VELDO-0169 ' + row, not failed)


_v169_suite()
