"""VELDO-0190: owner SSH saves before API enrollment and through the installed service."""


def _v190_suite():
    import copy
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import sqlite3
    import time

    PRODUCTION = {
        'control_owner_revisions.py': ROOT / ".veldo" / "control_owner_revisions.py",
        'control_agent_config.py': ROOT / ".veldo" / "control_agent_config.py",
        'control_membership.py': ROOT / ".veldo" / "control_membership.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    names = ('offline/saves', 'writer/configuration-stale', 'writer/team-stale', 'writer/roster',
        'writer/credential', 'authentication/unsigned', 'authentication/other-key', 'authentication/revoked',
        'authentication/not-owner', 'authentication/definition', 'authentication/base', 'authentication/team',
        'authentication/membership', 'authentication/delegation', 'authentication/domain', 'authentication/store',
        'authentication/repository', 'authentication/expiry', 'authentication/command-id', 'authentication/operations',
        'replay/identical', 'replay/content-conflict', 'replay/consumed-nonce', 'replay/nonce-binding', 'lock/second-connection',
        'format/fake-lines', 'service/saves', 'service/forged', 'service/writer-refusal', 'service/unconfigured', 'install/asset')
    rows = {name: [] for name in names}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    here = Path(__suite_file__).resolve().parents[2]
    helper = load('v190_fixture', here / 'proof/VELDO-0190/fixture.py')
    journey = load('v190_journey', here / 'proof/VELDO-0190/journey.py')
    conform_formats = load('v190_conform', ROOT / 'proof/VELDO-0172/compare_formats.py')
    fake_formats = load('v190_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    fake = fake_formats.embed('''import json,sys
from pathlib import Path
def emit(event):
    print(json.dumps(complete_event(event)), flush=True)
if sys.argv[1:3] == ['login', 'status']:
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
if Path(sys.argv[0]).name == 'claude':
    opening = json.loads(sys.stdin.readline())
    if opening['type'] != 'control_request':
        raise ValueError('expected initialize')
    emit({'type': 'control_response', 'response': {'subtype': 'success',
          'request_id': opening['request_id'], 'response': {'account': {
          'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'}}}})
    sys.stdin.readline()
    emit({'type': 'assistant', 'message': {'usage': {'input_tokens': 2, 'output_tokens': 3}}})
    emit({'type': 'result', 'subtype': 'success', 'is_error': False,
          'usage': {'input_tokens': 2, 'output_tokens': 4}})
else:
    sys.stdin.read()
    emit({'type': 'thread.started', 'thread_id': 'fixture-thread'})
    emit({'type': 'turn.started'})
    emit({'type': 'turn.completed', 'usage': {'input_tokens': 2, 'output_tokens': 4}})
''')
    fake_capture = (['teardown not reached'], [])

    def exercise(h):
        path = h['mods'] / 'control_owner_revisions.py'
        present = path.is_file()
        for row in rows:
            check(row, 'owner revision entry point exists', present)
        if not present:
            return
        OR = load('v190_owner', path)
        scaffold = load('v190_scaffold', h['mods'] / 'init_scaffold.py')
        check('install/asset', 'runtime asset in scaffold inventory', '.veldo/control_owner_revisions.py' in scaffold._FILES)
        root, manager, code, report = journey.host(h, 'offline', partial=True)
        check('offline/saves', 'setup steps completed before API', code == 0)
        w = journey.Writers(h, root, OR)
        try:
            owner = h['owner']
            check('offline/saves', 'signed factory activation', w.activate().get('ok'))
            check('offline/saves', 'no api key, passkey or session',
                  not (root / 'keys/edge-api').exists() and not any(
                      'api_credential' in e['kind'] for e in w.S.materialized_state(w.conn)['entities'].values()))
            packets, saved = [], []
            for role in w.CT.REQUIRED_ROLES:
                packet = w.packet('save_capability_configuration', dict(definition=w.definition(role), base=0))
                packets.append(packet)
                answer = w.writer.apply(packet)
                saved.append(answer)
                check('offline/saves', role + ' saved: ' + str(answer.get('reason')), answer.get('ok'))
                if answer.get('ok'):
                    read = w.CG.read(w.conn, w.ids['domain_uuid'], w.ids['repository_uuid'], role, 1)
                    check('offline/saves', role + ' read-back', read == {k:v for k,v in answer['result'].items() if k != 'replayed'})
                    check('offline/saves', role + ' envelope provenance', read.get('assertion_digest') ==
                          'sha256:' + hashlib.sha256(w.AC.canonical_envelope_bytes(packet['envelope'])).hexdigest())
                    check('offline/saves', role + ' complete definition', all(read[k] == v for k,v in w.definition(role).items()))
            team = w.team()
            team_packet = w.packet('save_default_team', dict(team=team, base=0))
            answer = w.writer.apply(team_packet)
            check('offline/saves', 'default saved: ' + str(answer.get('reason')), answer.get('ok'))
            packets.append(team_packet)
            if answer.get('ok'):
                read = w.routes.read_default(1)
                digest = 'sha256:' + hashlib.sha256(w.AC.canonical_envelope_bytes(team_packet['envelope'])).hexdigest()
                check('offline/saves', 'default read-back and signed envelope digest',
                      read['team'] == team and read['assertion_digest'] == digest and read['saved_by'] == owner
                      and read['digest'] == answer['result']['digest'])
            journal = {r['command_id']: r for r in w.S.export_journal(w.conn)}
            for packet in packets:
                cid = packet['command']['command_id']
                rec = journal.get(cid, {})
                check('offline/saves', cid + ' journal principal and nonce', rec.get('principal') == owner
                      and rec.get('nonce') == cid and w.S.materialized_state(w.conn)['nonces'].get(cid) == cid)
            check('offline/saves', 'only safe observations', all(
                not {'signature', 'definition', 'settings', 'public_key'} & set(e) for e in w.writer.observations))

            def refused(row, packet, reason, writer=None):
                writer = writer or w.writer
                before = w.head()
                result = writer.apply(packet)
                event = writer.observations[-1]
                check(row, 'named refusal: ' + str(result.get('reason')), not result.get('ok') and result.get('reason') == reason)
                check(row, 'journal unchanged', w.head() == before)
                check(row, 'refused observation with signer and class', event.get('refusal') == reason
                      and event.get('outcome') == 'refused' and event.get('taxonomy') == OR.taxonomy(reason)
                      and event.get('principal') == packet['envelope']['principal'])
                return result

            params = dict(definition=w.definition(), base=1)
            stale = w.packet('save_capability_configuration', dict(definition=w.definition(), base=0))
            refused('writer/configuration-stale', stale, 'stale_version:agent_configuration')
            refused('writer/team-stale', w.packet('save_default_team', dict(team=team, base=0)), 'stale_version:default_team')
            incomplete = copy.deepcopy(team); del incomplete['roles']['implementation']
            refused('writer/roster', w.packet('save_default_team', dict(team=incomplete, base=1)),
                    'incomplete_roster:missing_staffing:implementation')
            bad = w.definition(); bad['settings']['api_key'] = 'Bearer ' + os.urandom(24).hex()
            refused('writer/credential', w.packet('save_capability_configuration', dict(definition=bad, base=1)),
                    'invalid_input:agent_configuration')
            w.admin('enroll_principal', dict(principal='co-owner', principal_type='person',
                roles=['project_owner', 'membership_steward'], public_key=h['derived'](h['other_key']),
                independence_group='co-owner', scope='*'), h['other_key'])
            unsigned = w.packet('save_capability_configuration', params); unsigned.pop('signature')
            auth = 'missing_authority:owner_command:'
            refused('authentication/unsigned', unsigned, auth + 'signature_invalid')
            refused('authentication/other-key', w.packet('save_capability_configuration', params, key=h['other_key']), auth + 'signature_invalid')
            refused('authentication/not-owner', w.packet('save_capability_configuration', params,
                who='co-owner', key=h['other_key']), auth + 'not_factory_owner')
            for field in ('definition', 'base', 'team'):
                packet = w.packet('save_default_team', dict(team=team, base=1)) if field == 'team' else w.packet('save_capability_configuration', params)
                p = packet['command']['parameters']
                if field == 'base': p[field] = 0
                elif field == 'definition': p[field]['settings']['model'] = 'changed'
                else: p[field]['roles']['implementation']['expertise'] = ['changed']
                refused('authentication/' + field, packet, auth + 'envelope_refused')
            state = w.CM.authority_state(w.S, w.conn)
            edits = {'membership': {'membership_version': state['membership_version'] - 1},
                'delegation': {'delegation_version': state['delegation_version'] - 1},
                'domain': {'domain_uuid': 'another-domain'}, 'store': {'store_uuid': 'another-store'},
                'repository': {'repository_uuid': 'another-repository'}, 'expiry': {'expires_at': time.time() - 1}}
            for row, edit in edits.items():
                refused('authentication/' + row, w.packet('save_capability_configuration', params, **edit), auth + 'envelope_refused')
            wrong_id = copy.deepcopy(packets[0]); wrong_id['envelope']['command_id'] += '-other'
            refused('authentication/command-id', wrong_id, auth + 'envelope_refused')
            for operation in (*w.CM.ADMIN_OPERATIONS, 'propose_team', 'unknown', 'save_agent_skill'):
                refused('authentication/operations', w.packet(operation, params), 'invalid_input:owner_command:operation')
            for packet in (packets[0], team_packet):
                before = w.head()
                try:
                    w.CM.admit(w.S, w.conn, packet['envelope'], packet['command'], packet['signature'],
                        w.ids, time.time(), journal_signer=(w.principal, w.sign))
                    code = None
                except w.CM.MembershipRefused as error:
                    code = error.code
                check('authentication/operations', 'admit still refuses revisions first', code == 'policy_refused' and w.head() == before)
            for packet in (packets[0], team_packet):
                before = w.head()
                result = w.writer.apply(packet)
                check('replay/identical', 'saved retry read back', result.get('ok') and result['result'].get('replayed')
                      and result['result']['revision'] == 1 and w.head() == before)
            altered = copy.deepcopy(params); altered['definition']['settings']['model'] = 'changed'
            refused('replay/content-conflict', w.packet('save_capability_configuration', dict(altered, base=0),
                command_id=packets[2]['command']['command_id']), 'stale_subject:owner_command:command_content_conflict')
            changed_team = copy.deepcopy(team); changed_team['roles']['implementation']['expertise'] = ['changed']
            refused('replay/content-conflict', w.packet('save_default_team', dict(team=changed_team, base=0),
                command_id=team_packet['command']['command_id']), 'stale_subject:owner_command:command_content_conflict')
            refused('replay/consumed-nonce', w.packet('save_capability_configuration', params,
                nonce=packets[0]['envelope']['nonce']), auth + 'envelope_refused')
            refused('replay/nonce-binding', w.packet('save_capability_configuration', params, nonce='unused-nonce'),
                    auth + 'envelope_refused')
            check('offline/saves', 'metrics cover both operations and named refusals',
                  w.writer.metrics()['operations']['save_capability_configuration']['accepted'] >= 4
                  and w.writer.metrics()['refused_by_reason'].get(auth + 'signature_invalid') == 2)
            w.admin('revoke_membership', dict(principal=owner, revoked_at=time.time() - 1))
            refused('authentication/revoked', w.packet('save_capability_configuration', params), auth + 'envelope_refused')
        finally:
            w.close()

        root, manager, code, report = journey.host(h, 'online')
        check('service/saves', 'full setup: ' + str(report.get('reason')), code == 0)
        if code:
            return
        home = Path(report['home'])
        config = json.loads((home / 'config/service.json').read_text())
        installed = home / 'bin' / '.veldo'
        # Discover the installed canonical module through the installation's runtime inventory.
        copies = list(home.rglob('control_owner_revisions.py'))
        check('install/asset', 'module installed byte-identically', bool(copies) and copies[0].read_bytes() == path.read_bytes())
        if not copies:
            return
        w = journey.Writers(h, root, OR, copies[0].parent)
        try:
            check('service/saves', 'factory project activated by signed writer', w.activate().get('ok'))
            packets = [w.packet('save_capability_configuration', dict(definition=w.definition(role), base=0)) for role in w.CT.REQUIRED_ROLES]
            team_packet = w.packet('save_default_team', dict(team=w.team(), base=0))
            packets.append(team_packet)
            forged = w.packet('save_capability_configuration', dict(definition=w.definition(), base=1), key=h['other_key'])
            stale = w.packet('save_default_team', dict(team=w.team(), base=0))
            db, ids = w.config['store_path'], w.ids
            # A missing API judge has its own refusal before any writer is constructed.
            dummy = object.__new__(h['CS'].Service)
            dummy.api = None
            try:
                dummy.owner_revision(packets[0]); reason = None
            except h['CS'].Refused as error:
                reason = error.code
            check('service/unconfigured', 'API absence named', reason == 'unavailable_service:api:not_configured')
        finally:
            w.close()
        started = manager.start(report['unit'])
        check('service/saves', 'installed authority started', started[0] == 0)
        if started[0]:
            return
        connect = sqlite3.connect
        opened = []
        def record_connect(database, *args, **kwargs):
            opened.append(str(database))
            return connect(database, *args, **kwargs)
        try:
            second = journey.Writers(h, root, OR, copies[0].parent)
            try:
                before = second.head()
                result = second.writer.apply(packets[0])
                check('lock/second-connection', 'second connection refused before writers',
                      result.get('reason') == 'missing_authority:not_the_authority'
                      and second.head() == before and second.writer.observations[-1]['taxonomy'] == 'missing_authority')
            finally:
                second.close()
            sqlite3.connect = record_connect
            with sqlite3.connect('file:' + str(db) + '?mode=ro', uri=True) as read:
                for packet in packets:
                    result = h['service_send'](root, packet)
                    check('service/saves', 'socket save: ' + str(result), result.get('result', {}).get('ok') is True)
                    rec = read.execute('SELECT principal, nonce, signer FROM journal WHERE command_id=?',
                        (packet['command']['command_id'],)).fetchone()
                    check('service/saves', 'service journal records verified owner and nonce',
                          rec is not None and rec[0] == h['owner'] and rec[1] == packet['envelope']['nonce'])
                before = read.execute('SELECT max(seq) FROM journal').fetchone()[0]
                for packet in packets:
                    retry = h['service_send'](root, packet)
                    check('service/saves', 'socket replay is read-back without a write',
                          retry.get('result', {}).get('result', {}).get('replayed') is True
                          and read.execute('SELECT max(seq) FROM journal').fetchone()[0] == before)
                for row, packet, reason in (('service/forged', forged, 'missing_authority:owner_command:signature_invalid'),
                    ('service/writer-refusal', stale, 'stale_version:default_team')):
                    result = h['service_send'](root, packet)
                    check(row, 'socket refusal: ' + str(result), result.get('result', {}).get('reason') == reason)
                    check(row, 'refusal leaves journal unchanged', read.execute('SELECT max(seq) FROM journal').fetchone()[0] == before)
                observations = [json.loads(line) for line in Path(config['observations']).read_text().splitlines()]
                for packet in packets:
                    event = next((e for e in observations if e.get('command_id') == packet['command']['command_id']), {})
                    check('service/saves', 'service observes committed revision and digest',
                          event.get('revision') == 1 and isinstance(event.get('digest'), str))
                check('service/saves', 'sender opens only a read-only store while sending',
                      opened and all('?mode=ro' in name for name in opened))
                for row, packet, reason in (('service/forged', forged, 'missing_authority:owner_command:signature_invalid'),
                    ('service/writer-refusal', stale, 'stale_version:default_team')):
                    event = next((e for e in observations if e.get('command_id') == packet['command']['command_id']), {})
                    check(row, 'service observes operation, signer, refusal and class', event.get('principal') == h['owner']
                        and event.get('operation') == packet['command']['operation'] and event.get('refusal') == reason
                        and event.get('outcome') == 'refused' and event.get('taxonomy') == OR.taxonomy(reason))
        finally:
            sqlite3.connect = connect
            manager.stop(report['unit'])

    def teardown(h):
        nonlocal fake_capture
        base, fake = h['base'], h['engines186']['fake']
        L = load('v190_format_launch', h['mods'] / 'control_launch.py')
        try:
            pass
        finally:
            fake_capture = conform_formats.conform_fake(locals(), '0190_owner_revisions')
            check('format/fake-lines', 'generated CLI lines conform to the capture', not fake_capture[0] and bool(fake_capture[1]))

    try:
        helper.run(ROOT, PRODUCTION, exercise, teardown, fake)
    except Exception as error:
        for row in rows:
            check(row, 'ran to its end (raised ' + type(error).__name__ + ': ' + str(error)[:250] + ')', False)
    for line in conform_formats.describe('0190_owner_revisions', *fake_capture):
        print(line)
    expect('VELDO-0172 fake/capture:0190_owner_revisions', not fake_capture[0])
    for row, observations in rows.items():
        for label, passed in observations:
            if not passed:
                print('VELDO-0190 ' + row + ' detail: ' + label)
        expect('VELDO-0190 ' + row, len(observations) > 1 and all(passed for _, passed in observations))


_v190_suite()
