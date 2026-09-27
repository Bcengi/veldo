"""VELDO-0169: census and signed handouts over the Gate's project check.

Only ROOT and expect come from shared. Projects, memberships, claims, parks, answers,
stops, settlements and contracts use their production writers. Admitted units and backlog
items are the claim organ's accepted-admission fixture seam. No model or external host.
"""


def _v169_suite():
    import ast
    import collections
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import tempfile

    production = {
        'control_assignment.py': ROOT / ".veldo" / "control_assignment.py",
        'control_claim.py': ROOT / ".veldo" / "control_claim.py",
        'control_andon.py': ROOT / ".veldo" / "control_andon.py",
        'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
    }
    rows = {}

    def check(row, label, condition):
        rows.setdefault(row, []).append((label, bool(condition)))

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

    def planted(sources):
        """The reviewer's planted writers (rv169a) and more of the same shape, each over these sources."""
        a, n = sources['control_assignment'], sources['control_andon']
        start = a.find('    def _resume(self, state, entities, current, principal, now, command, params, observation):')
        end = a.find('\n    def ', start + 10)
        original = a[start:end]
        again = original.replace('def _resume(', 'def _resume_again(').replace(
            '        self._check_project(unit, entities, observation)\n', '')

        def edit(text, old, new):
            if start < 0 or text.count(old) != 1 or '_check_project' in again:
                raise LookupError(old[:60])
            return text.replace(old, new)
        wired = edit(edit(a, "            elif op == 'resume':\n",
                          "            elif op == 'resume_again':\n"
                          "                touched.update(self._resume_again(state, entities, current, principal, now, command, params, observation))\n"
                          "            elif op == 'resume':\n"), original, original + again)
        fast = lambda body: {'control_fastlane': 'class Fast:\n    def __init__(self, inbox):\n        self.inbox = inbox\n' + body}
        yield 'resume-again-shared-writer', 'Inbox._resume_again', {'control_assignment': wired}
        yield 'resume-again-own-writer', 'Inbox._transition', {'control_assignment': edit(
            wired, "        if op == 'resume':\n", "        if op == 'resume_again':\n"
            "            return self.claims.transition(params['resume'], before)\n        if op == 'resume':\n")}
        yield 'module-local-alias', 'Fast.take', fast(
            '    def take(self, params, before):\n        organ = self.inbox.claims\n        return organ.transition(params, before)\n')
        yield 'renamed-attribute', 'Fast.take', fast(
            '    def take(self, params, before):\n        return self.inbox.claim_organ.transition(params, before)\n')
        yield 'getattr-call', 'Fast.take', fast(
            "    def take(self, params, before):\n        return getattr(self.inbox.claims, 'transition')(params, before)\n")
        yield 'plain-attribute', 'Fast.take', fast(
            '    def take(self, params, before):\n        return self.inbox.claims.transition(params, before)\n')
        yield 'bound-method-alias', 'Fast.take', fast(
            '    def take(self, params, before):\n        write = self.inbox.claims.transition\n        return write(params, before)\n')
        yield 'dynamic-getattr', 'Fast.take', fast(
            '    def take(self, name, params, before):\n        return getattr(self.inbox.claims, name)(params, before)\n')
        yield 'bare-registration', 'Fast.attach', fast(
            "    def attach(self, conn):\n        conn.command_registry['fast'] = {'transition': self.inbox.claims.transition}\n")
        yield 'minted-receipt', 'Fast.take', fast(
            "    def take(self, unit):\n        return self.inbox.claims.project_check_receipt(unit, 'p', {})\n")
        yield 'andon-second-resume', 'Andon.resume_quick', {'control_andon': edit(
            n, '    def run(self):\n',
            "    def resume_quick(self, sid, contract, permission, evidence, expected, command_id):\n"
            "        self._commit(dict(action='resume', stop_id=sid, unit_id=contract['unit'], contract=contract,\n"
            "                          permission=permission, evidence=evidence), expected, self.journal_signer, command_id, command_id)\n\n"
            '    def run(self):\n')}
        yield 'contract-without-writer', 'Andon.quick_contract', {'control_andon': edit(
            n, '    def run(self):\n',
            "    def quick_contract(self, contract):\n"
            "        return {contract['contract_id']: {'kind': CONTRACT_KIND, 'data': contract}}\n\n"
            '    def run(self):\n')}
        yield 'check-in-a-branch', 'Inbox._transition', {'control_assignment': edit(
            a, "            receipt = self._project_receipt(params['resume']['unit_id'])\n",
            "            receipt = None\n            if data.get('urgent'):\n"
            "                receipt = self._project_receipt(params['resume']['unit_id'])\n")}

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
        try:
            variants = list(planted(sources))
        except LookupError as missing:
            check('census/planted', 'planted writers built on these sources (%s)' % missing, False)
            variants = []
        for name, function, change in variants:
            _, planted_failures = CEN.census(dict(sources, **change))
            check('census/planted', name + ' refused at ' + function,
                  any(('.' + function + ':') in f for f in planted_failures))

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
            # Non-handout dispositions still apply while the project is paused.
            IT = load('v169_intake', mods / 'control_intake.py')
            inbox.intake = IT.Intake(S, inbox.membership, inbox.AC, ing.acquirer, ing.conn,
                                    domain=A.ids['domain_uuid'], projects=['project-a'], api_edge='api-edge',
                                    journal_signer='authority', sign=A.journal_sign)
            for ruling in ('close', 'other'):
                row = 'dispose/PAUSED'
                name = 'p-no-handout-' + ruling
                activate(name)
                action, _, _, prepared = prepare('dispose', 'u-no-handout-' + ruling, name, ruling)
                change(name, 'pause')
                check(row, ruling + ' remains available', prepared and action().get('ok'))
        finally:
            if ing is not None:
                ing.conn.close()
            A.conn.close()
            stop()
            socket.create_connection = real_connect
    for row, parts in rows.items():
        failed = [label for label, ok in parts if not ok]
        if failed:
            print('  VELDO-0169 detail: ' + row + ': ' + '; '.join(failed))
        expect('VELDO-0169 ' + row, not failed)


_v169_suite()
