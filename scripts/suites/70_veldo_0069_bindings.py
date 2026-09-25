"""VELDO-0069: the governing decision binding a real signed Telegram settlement writes, and eligibility.

Run: python3 scripts/selftest.py --suite 70_veldo_0069_bindings

Every answer is an owner's reply to a real VELDO-0065 presentation over a loopback Bot API (real HTTP in
the platform's documented shapes; not the Telegram service, no network, no real token), attributed by the
actual VELDO-0066 Acquirer, signed by the actual protected signer process through the VELDO-0067 edge,
accepted by the actual presenter and settled by the VELDO-0068 settlement service, which writes the
governing binding. Every command, journal record and assertion is a real OpenSSH signature on a real
SQLite store; the binding body is signed with a real Ed25519 key and read through the production
VELDO-0054 SettlementTrust by the shared floor Gate, plan.py (_decision_blocks, item_state, cmd_status,
cmd_run_check), the frontier and the run lens, in this process and in another one. The fixture spells
every governing question, digest and signed byte itself, so the writer is judged against an independent
spelling and against the consumers, never against its own reader. Mutation workers replace the
production copies named in PRODUCTION below. Where a pre-change tree has no binding, every row drives the
path that tree has and fails by its own assertions. No private key byte, signature or rationale is
printed or retained.
"""


def _v69_suite():
    import contextlib
    import copy
    import hashlib
    import http.server
    import importlib.util
    import inspect
    import io
    import json
    import os
    from pathlib import Path
    import re
    import shutil
    import subprocess
    import sys
    import tempfile
    import threading
    import time

    ROWS = ('binding/one-transaction', 'eligibility/resolved-request', 'refusal/wrong-framing',
            'refusal/wrong-subject', 'refusal/wrong-version', 'refusal/unsupported-subject-stops',
            'consumers/inline-bypass', 'refusal/future-revision', 'binding/owner-ruling')
    OT, ER, WF, WS, WV, UK, IB, FV, RU = ROWS
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {
        'control_request_settlement.py': ROOT / ".veldo" / "control_request_settlement.py",
        'control_decision_dependency.py': ROOT / ".veldo" / "control_decision_dependency.py",
        'plan.py': ROOT / ".veldo" / "plan.py",
    }
    CHOICES = {'accept': 'approve', 'return_for_elaboration': 'return_for_elaboration', 'reject': 'reject'}
    NAMESPACE = 'veldo-decision-settlement'
    GOVERNING, SETTLEMENT = 'veldo.governing_decision/v1', 'veldo.decision_settlement/v1'
    FX_FIELDS = ('schema', 'domain_uuid', 'decision_id', 'decision_revision', 'framing_digest', 'subject',
                 'scope_digest', 'ruling', 'request_id', 'request_version', 'principals', 'settled_at')
    FX_LIFECYCLE = {'spec': ('state',), 'plan': ('status',)}

    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    class section:
        """An exception is recorded as a failure of each named row and the run goes on."""

        def __init__(self, *names):
            self.names = names

        def __enter__(self):
            return self

        def __exit__(self, kind, value, trace):
            if kind is not None:
                for name in self.names:
                    check(name, 'the section ran to its end (it raised %s: %s)' % (kind.__name__, str(value)[:200]), False)
            return True

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    # The fixture's own spellings: canonical JSON, sha256, the governing question, the signed body.
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

    def fx_digest(value):
        return 'sha256:' + hashlib.sha256(canonical(value)).hexdigest()

    def fx_bytes(body):
        return canonical({k: body.get(k) for k in FX_FIELDS})

    def fx_subject(kind, data):
        return fx_digest({k: v for k, v in data.items() if k not in FX_LIFECYCLE[kind]})

    def fx_scope(scope):
        return fx_digest({'operation': scope.get('operation'), 'target': scope.get('target'),
                          'parameters': scope.get('parameters')})

    def fx_target(rid, question):
        return dict(question, kind='governing_decision', ref=rid, digest=fx_digest(question))

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v69-', dir=fast) as directory:
        base = Path(directory)
        repo = base / 'repo'
        organs = repo / '.veldo'
        organs.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, organs / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, organs / name)
        GP = load('v69_git', organs / 'git_process.py')
        GP.run(['git', '-C', str(repo), 'init', '-q'], check=True, capture_output=True)

        claims = load('v69_claims', organs / 'control_claim.py')
        S, CM, AC = claims.S, claims.CM, claims.AC
        K = load('v69_keys', organs / 'control_keys.py')
        I = load('v69_inbox', organs / 'control_assignment.py')
        P = load('v69_projection', organs / 'control_channel_projection.py')
        V = load('v69_presentation', organs / 'control_channel_presentation.py')
        EV = load('v69_attribution', organs / 'control_channel_attribution.py')
        E = load('v69_enrollment', organs / 'control_channel_enrollment.py')
        A = load('v69_answers', organs / 'control_signer_answers.py')
        contract = load('v69_contract', organs / 'entity_contract.py')
        ST = load('v69_settlement', organs / 'control_request_settlement.py')
        EL = load('v69_eligibility', organs / 'control_eligibility.py')
        DD = EL.DD
        PL = load('v69_plan', organs / 'plan.py')
        FR = load('v69_frontier', organs / 'frontier.py')
        RSN = load('v69_runstatus', organs / 'runstatus.py')

        keys, protected, edge_dir, host = base / 'keys', base / 'protected', base / 'edge', base / 'host'
        for d in (keys, protected, edge_dir, host):
            d.mkdir()
        keyfile = {who: keys / who for who in ('authority', 'steward', 'owner', 'pm')}
        keyfile['edge'] = protected / 'edge-telegram'
        keyfile['edge-auth'] = edge_dir / 'edge-auth'
        # The host's decision settlement signer: its key and the allowed-signers file hosts trust, outside
        # the workspace.
        keyfile['decision'] = host / 'decision_key'
        public = {}
        for who, path in keyfile.items():
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v69-' + who, '-f', str(path)],
                           check=True, capture_output=True, timeout=10)
            public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
        signers = host / 'settlement_signers'
        signers.write_text('veldo-settlement namespaces="%s" %s\n' % (NAMESPACE, public['decision']))

        def sign_as(who, message, namespace='veldo-command'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=message,
                                  capture_output=True, check=True, timeout=10).stdout.decode()

        def decision_sign(message):
            return sign_as('decision', message, NAMESPACE)

        serial = [0]

        def next_id(prefix):
            serial[0] += 1
            return '%s-%d' % (prefix, serial[0])

        def verifies(message, signature):
            """An independent ssh-keygen verification against the trusted signer, in a fresh directory."""
            place = base / next_id('verify')
            place.mkdir()
            (place / 'allowed').write_text('veldo-settlement namespaces="%s" %s\n' % (NAMESPACE, public['decision']))
            (place / 'signature').write_text(signature if isinstance(signature, str) else '')
            done = subprocess.run(['ssh-keygen', '-Y', 'verify', '-f', str(place / 'allowed'), '-I', 'veldo-settlement',
                                   '-n', NAMESPACE, '-s', str(place / 'signature')], input=message, capture_output=True,
                                  timeout=10)
            return done.returncode == 0

        def journal_sign(message):
            return sign_as('authority', message, 'veldo-journal')

        ids = dict(domain_uuid='domain-69', repository_uuid='repository-69', store_uuid='store-69')
        (base / 'authority').mkdir()
        db = base / 'authority' / 'control.sqlite3'
        conn = S.open_store(str(db))
        CM.attach(S)
        K.attach(S)
        signer_repo = base / 'signer-repository'
        signer_repo.mkdir()
        projection = signer_repo / '.veldo' / 'keys' / 'allowed_signers'
        config_path = base / 'authority' / 'signer.json'
        config_path.write_text(json.dumps({'store': str(db), 'repository': str(signer_repo),
                                           'allowed_signers': str(projection), 'key_directory': str(protected),
                                           'authority_ids': ids}))

        def state():
            return CM.authority_state(S, conn)

        def envelope(command, principal):
            now = state()
            return dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=principal,
                        request_revision=1, nonce='nonce-' + command['command_id'], expires_at=time.time() + 600,
                        membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                        command_digest=AC.canonical_command_digest(command))

        def admin(principal, operation, params, enrollee=None):
            command = {'command_id': next_id('admin'), 'operation': operation, 'target': 'authority',
                       'parameters': params, 'artifact_digests': [], 'expected_versions': {}}
            env = envelope(command, principal)
            signature = sign_as(principal, AC.canonical_envelope_bytes(env))
            cosigned = (sign_as(enrollee, AC.canonical_envelope_bytes(dict(env, principal=params['principal'])))
                        if enrollee else None)
            result = CM.admit(S, conn, env, command, signature, ids, time.time(), enrollee_signature=cosigned,
                              journal_signer=('authority', journal_sign))
            K.publish(S, conn, projection)
            return result

        admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                              'roles': ['membership_steward', 'project_owner'],
                                              'public_key': public['steward'], 'independence_group': 'steward',
                                              'scope': '*'})
        admin('steward', 'enroll_principal', {'principal': 'owner', 'principal_type': 'person',
                                              'roles': ['project_owner'], 'public_key': public['owner'],
                                              'independence_group': 'owner', 'scope': ['project-a']}, enrollee='owner')
        admin('steward', 'enroll_principal', {'principal': 'pm', 'principal_type': 'service', 'roles': [],
                                              'public_key': public['pm'], 'independence_group': 'pm',
                                              'scope': ['project-a']}, enrollee='pm')

        def fixture(eid, kind, data):
            row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
            return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                        parameters=dict(entity_id=eid, kind=kind, data=data),
                                        expected_versions={eid: row[0] if row else 0}, artifact_digests=[],
                                        nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

        chat_id = 5690001
        fixture('channel-enrollment:telegram_chat:owner', 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='owner', chat_id=chat_id,
                     revoked_at=None))
        enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
        edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                       'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': ['project-a']}
        edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                        'target': 'channel:telegram_chat', 'parameters': edge_params, 'artifact_digests': [],
                        'expected_versions': {}}
        edge_env = envelope(edge_command, 'steward')
        enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                         sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))
        admin('owner', 'grant_delegation', {'id': 'delegation-owner', 'principal': 'owner', 'channel': 'telegram_chat',
                                            'assertion_kinds': ['decision_answer', 'review_disposition'],
                                            'authority_scope': ['project-a'], 'request_version': 1,
                                            'presentation_version': 1, 'expires_at': time.time() + 1800,
                                            'edge_key_id': 'edge-telegram'})

        api = {'tick': 0, 'lock': threading.Lock(), 'next': 9000, 'update_next': 720000000, 'messages': {},
               'updates': [], 'user': {'id': 8000000069, 'is_bot': True, 'first_name': 'Veldo',
                                       'username': 'veldo_binding_bot'}}
        person = {'id': chat_id, 'is_bot': False, 'first_name': 'Owner'}
        chat = {'id': chat_id, 'type': 'private', 'first_name': 'Owner'}

        def message(sender, text, reply_to=None):
            with api['lock']:
                api['next'] += 1
                api['tick'] += 1
                m = {'message_id': api['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791100000 + api['tick'],
                     'text': text}
                if reply_to is not None and (chat['id'], reply_to) in api['messages']:
                    held = api['messages'][(chat['id'], reply_to)]
                    m['reply_to_message'] = copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
                api['messages'][(chat['id'], m['message_id'])] = m
                return m

        class BotApi(http.server.BaseHTTPRequestHandler):
            """Loopback endpoint with the Bot API getMe, getUpdates and sendMessage shapes."""

            def log_message(self, *args):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                body = json.loads(raw) if raw else {}
                _, _, rest = self.path.partition('/bot')
                name, _, method = rest.partition('/')
                if name != 'bot69':
                    return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
                if method == 'getMe':
                    return self._answer(200, {'ok': True, 'result': dict(api['user'], can_join_groups=True)})
                if method == 'getUpdates':
                    offset = body.get('offset') or 0
                    if offset:
                        api['updates'] = [u for u in api['updates'] if u['update_id'] >= offset]
                    return self._answer(200, {'ok': True, 'result': api['updates'][:body.get('limit') or 100]})
                if method == 'sendMessage':
                    reply = (body.get('reply_parameters') or {}).get('message_id')
                    return self._answer(200, {'ok': True, 'result': message(api['user'], body['text'], reply)})
                return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

            def _answer(self, code, value):
                payload = json.dumps(value).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), BotApi)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = 'http://127.0.0.1:%d' % server.server_address[1]
        takes_signer = 'decision_signer' in inspect.signature(ST.Settlement).parameters

        def services(connection, signed=True):
            """The inbox, presenter and settlement service of one connection to the authority store."""
            inbox_ = I.Inbox(S, CM, claims, contract, connection, ids, 'authority', journal_sign)
            presenter_ = V.Presenter(S, CM, P, inbox_, V.TelegramPresentationEdge(P, url, 'bot69'), connection,
                                     'authority', journal_sign, assignment=I)
            extra = {'decision_signer': ('veldo-settlement', decision_sign)} if signed and takes_signer else {}
            service_ = ST.Settlement(S, CM, inbox_, presenter_, connection, 'authority', journal_sign, assignment=I,
                                     presentation=V, **extra)
            return inbox_, presenter_, service_

        try:
            inbox, presenter, service = services(conn)
            adapter = A.EdgeSigner(S, CM, conn, config_path, 'edge-telegram', keyfile['edge-auth'])
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot69'), conn,
                                   'authority', journal_sign, 'telegram-edge', adapter)

            def signed_command(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            def terms(name, target, touchpoint='decision_disposition'):
                body = dict(ids, operation='terms', terms=name, principal='pm', command_id=next_id('terms'),
                            nonce=next_id('terms-nonce'), touchpoint=touchpoint, target=target, proposal=None,
                            required_roles=[], quorum=None)
                return service.terms(signed_command('pm', body))

            def open_request(alias, target, touchpoint='decision_disposition'):
                """Terms, the inbox request, its framing and its presentation: (request id, receipt, terms result)."""
                got = terms(alias, target, touchpoint)
                subject = got.get('subject') or {}
                kind = 'decision'
                inbox.apply(signed_command('pm', dict(ids, operation='open', alias=alias, principal='pm',
                                                      command_id=next_id('c'), nonce=next_id('n'), assignment=dict(
                                                          kind=kind, owner='owner', scope=['project-a'],
                                                          deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                                          brief='Rule on %s.' % alias, choices=list(CHOICES),
                                                          subject=subject))))
                rid = I.assignment_id(ids['repository_uuid'], alias)
                presenter.frame(signed_command('pm', dict(ids, operation='frame', alias=alias, principal='pm',
                                                          request_version=1,
                                                          risk_statement='Low: a wrong choice costs one review cycle.',
                                                          command_id=next_id('f'), nonce=next_id('fn'))))
                presenter.present(rid)
                return rid, presenter.current(rid) or {}, got

            def reply(receipt, text):
                with api['lock']:
                    api['update_next'] += 1
                    update_id = api['update_next']
                update = {'update_id': update_id, 'message': message(person, text, (receipt.get('message_ids') or [None])[-1])}
                api['updates'].append(update)
                return update

            def acquire():
                return {r['update_id']: (r.get('outcome'), r.get('reason')) for r in acquirer.acquire()
                        if r.get('update_id') is not None}

            def entity(eid):
                row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

            def of_kind(kind, field=None, value=None):
                found = []
                for eid, text in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id', (kind,)):
                    data = json.loads(text)
                    if field is None or data.get(field) == value:
                        found.append((eid, data))
                return found

            def bindings(rid):
                return of_kind('decision_settlement', 'decision', rid)

            def written(request):
                """Everything a settlement of `request` writes: its settlements, effects, receipts and the
                bindings that name it."""
                return (of_kind('request_settlement', 'request_id', request), of_kind('settlement_effect', 'request_id', request),
                        of_kind('settlement_receipt', 'request_id', request),
                        [b for b in of_kind('decision_settlement') if (b[1].get('settlement') or {}).get('request_id') == request])

            def seen(result):
                return ' [observed: %s, %s]' % (result.get('outcome'), result.get('reason'))

            # The governed work: every unit admitted, claimed, approved and dependency-free under a ready
            # plan, so the only thing that can hold one back is its governing decision.
            put = fixture
            put('project:p1', 'project', dict(name='bindings'))
            put('authority:' + ids['domain_uuid'], 'authority', dict(state='active', generation=1))
            CLM = EL._organ('control_claim')

            def unit(sid, plan):
                put(sid, 'execution_unit', dict(state='CLAIMED', repository_uuid=ids['repository_uuid'],
                                                backlog_item_uuid='backlog:' + sid, requirements=[],
                                                eligible_holders=['worker-a'], plan=plan, project='p1', depends_on=[],
                                                scope_digest='sha256:scope', revision=1, producer='builder-a',
                                                approvals_required=['owner']))
                put('backlog:' + sid, 'backlog_item', dict(state='ACTIVE', repository_uuid=ids['repository_uuid']))
                put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope'))
                put('approval:%s:owner' % sid, 'approval', dict(unit=sid, name='owner', state='granted', revision=1))
                put(CLM.claim_id(ids['repository_uuid'], sid), 'claim',
                    dict(unit_id=sid, holder='worker-a', generation=1, state='owned', heartbeat_at=CLM.CL._now()))

            PLANS = {'PLAN-9601': ['VELDO-9601', 'VELDO-9611', 'VELDO-9612', 'VELDO-9613', 'VELDO-9614', 'VELDO-9621',
                                   'VELDO-9623', 'VELDO-9631', 'VELDO-9632', 'VELDO-9633', 'VELDO-9634', 'VELDO-9635',
                                   'VELDO-9636', 'VELDO-9615', 'VELDO-9616', 'VELDO-9617'],
                     'PLAN-9602': ['VELDO-9602']}
            for pid, sids in PLANS.items():
                for sid in sids:
                    unit(sid, pid)
            # The accepted plan records: PLAN-9601 carries the inline reference the store-backed stations
            # read, stating it is resolved and approved; its file carries that and a file-only one.
            store_refs = [dict(id='DEC-9634', blocks=['VELDO-9634'], status='resolved', ruling='approve',
                               resolution='approved in the planning meeting')]
            file_refs = store_refs + [dict(id='DEC-9633', blocks=['VELDO-9633'], status='resolved', ruling='approve',
                                           resolution='approved in the planning meeting')]
            put('plan:PLAN-9601', 'plan', dict(status='ready', revision=1, open_decisions=store_refs))
            put('plan:PLAN-9602', 'plan', dict(status='ready', revision=1, charter='the plan decision fixture'))
            records = {}

            def decision(rid, kind, subject_id, blocks, revision=1, framing=None, scope=None, **extra):
                entity_id = subject_id if kind == 'spec' else 'plan:' + subject_id
                current = (entity(entity_id) or {}).get('data')
                record = dict(schema=GOVERNING, decision_id=rid.split(':', 1)[1], revision=revision,
                              framing_digest=framing or fx_digest({'framing': rid}),
                              subject=dict(kind=kind, id=subject_id,
                                           digest=fx_subject(kind, current) if kind in FX_LIFECYCLE and current else 'sha256:none'),
                              scope=scope or dict(operation='proceed', target=subject_id, parameters={'approach': 'A'}),
                              blocks=list(blocks), obligations=[])
                record.update(extra)
                records[rid] = record
                put(rid, 'decision', record)
                return record

            def question(rid, **change):
                """The question a requester asks about `rid`: the record's own binding, with `change` applied."""
                rec = records[rid]
                q = dict(decision_id=rec['decision_id'], revision=rec['revision'], framing_digest=rec['framing_digest'],
                         subject=dict(rec['subject']), scope_digest=fx_scope(rec['scope']))
                q.update(change)
                return fx_target(rid, q)

            for sid in ('VELDO-9601', 'VELDO-9611', 'VELDO-9612', 'VELDO-9613', 'VELDO-9614', 'VELDO-9623',
                        'VELDO-9631', 'VELDO-9632', 'VELDO-9636', 'VELDO-9615', 'VELDO-9616', 'VELDO-9617'):
                decision('decision:D-' + sid[-4:], 'spec', sid, [sid])
            decision('decision:P-9602', 'plan', 'PLAN-9602', ['plan:PLAN-9602'])
            decision('decision:D-9621', 'contract', 'CONTRACT-1', ['VELDO-9621'],
                     scope=dict(operation='proceed', target='CONTRACT-1', parameters={}))
            decision('decision:D-9633', 'spec', 'VELDO-9633', [], decision_id='DEC-9633')
            decision('decision:D-9634', 'spec', 'VELDO-9634', [], decision_id='DEC-9634')
            # The record's own inline status: it SAYS it is settled and approved, and nothing settled it.
            decision('decision:D-9635', 'spec', 'VELDO-9635', ['VELDO-9635'], state='settled', ruling='approve',
                     resolved=True)

            # The checkout the plan readers read.
            (repo / 'specs').mkdir()
            (repo / 'plans').mkdir()
            for pid, sids in PLANS.items():
                lines = []
                for n, sid in enumerate(sids, 1):
                    (repo / 'specs' / (sid + '-fixture.md')).write_text('\n'.join([
                        '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Binding fixture ' + sid, 'status: ready',
                        'risk: low', 'owner: dmitry', 'lane: planned', 'plan: ' + pid, 'work: W%d' % n,
                        'plan_revision: 1', 'depends_on: []', '---', '', 'Fixture.', '']))
                    lines += ['  - item: W%d' % n, '    spec: ' + sid, '    order: %d' % n]
                block = []
                if pid == 'PLAN-9601':
                    block = ['open_decisions:']
                    for entry in file_refs:
                        block += ['  - id: ' + entry['id'], '    blocks: [%s]' % ', '.join(entry['blocks'])]
                        block += ['    %s: %s' % (k, v) for k, v in entry.items() if k not in ('id', 'blocks')]
                (repo / 'plans' / (pid + '-fixture.md')).write_text('\n'.join(
                    ['---', 'schema: veldo.plan/v1', 'id: ' + pid, 'title: Binding fixture plan', 'status: ready',
                     'revision: 1', 'work:'] + lines + block + ['---', '', 'Fixture plan.', '']))

            reader = S.open_store(str(db), mode='r')
            gate = EL.Gate(S, reader, domain_uuid=ids['domain_uuid'], repository_uuid=ids['repository_uuid'],
                           workspace=str(repo), settlement_trust=DD.SettlementTrust(signers.read_text()))
            DECIDING = [s for s in EL.FLOOR_STATIONS if 'decisions_settled' in EL.STATION_PREDICATES[s]]
            CONTEXT = {'build': {'holder': 'worker-a'}, 'publication': {'holder': 'worker-a'},
                       'review': {'holder': 'worker-a', 'reviewer': 'reviewer-b'}}
            claims_root = base / 'claims'

            def plan_path(pid):
                return str(repo / 'plans' / (pid + '-fixture.md'))

            def sweep(sids):
                """Every enabled consumer's answer for each unit: the shared floor stations, the frontier,
                the run lens, plan._decision_blocks, item_state, the plan burn-down and run-check."""
                out = {sid: {'stations': {}} for sid in sids}
                for station in DECIDING:
                    for sid in sids:
                        out[sid]['stations'][station] = sorted(
                            gate.decide(station, sid, context=CONTEXT.get(station))['refusals'])
                offered = {u['spec'] for u in FR.claimable(repo_root=str(repo), claims_root=str(claims_root),
                                                           eligibility=gate)}
                lens = {i['spec']: i['state'] for p_ in RSN._burndown(repo, eligibility=gate) for i in p_['items']}
                for pid, members in PLANS.items():
                    wanted = [sid for sid in members if sid in out]
                    if not wanted:
                        continue
                    _, fm = PL.load_plan(plan_path(pid))
                    blocks = PL._decision_blocks(fm, gate)
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        PL.cmd_status(plan_path(pid), eligibility=gate)
                    burn = {m.group(1): m.group(2).strip() for m in re.finditer(r'^\s+W\d+\s+(VELDO-\d+)\s+(.*)$',
                                                                                buffer.getvalue(), re.M)}
                    status = PL._status(gate)
                    shipped = PL._shipped_set(fm, status)
                    states = {w['spec']: PL.item_state(w, status, shipped, blocks) for w in PL._work(fm)}
                    for sid in wanted:
                        buffer = io.StringIO()
                        with contextlib.redirect_stdout(buffer):
                            rc = PL.cmd_run_check(plan_path(pid), sid, eligibility=gate)
                        out[sid].update(offered=sid in offered, blocks=sorted(blocks.get(sid, [])), burn=burn.get(sid),
                                        lens=lens.get(sid), item_state=states.get(sid), run_check=rc,
                                        run_codes=sorted(set(re.findall(r'refused: (\S+)', buffer.getvalue()))))
                return out

            def verdict(o, codes, stations=True):
                """True when the unit is held back by exactly `codes` at every consumer that sees its decision
                (the file readers only for a file-only reference) and clear at every other; with no codes,
                clear everywhere."""
                station_codes = set(codes) if stations else set()
                stations_ok = all(set(r) == station_codes for r in o['stations'].values())
                if not codes:
                    return (stations_ok and o['offered'] and not o['blocks'] and o['burn'].endswith('(frontier)')
                            and (o['lens'] or '').endswith('(frontier)') and o['item_state'].endswith('(frontier)')
                            and o['run_check'] == 0 and not o['run_codes'])
                return (stations_ok and not o['offered'] and set(o['blocks']) == set(codes)
                        and o['burn'].startswith('blocked: decision') and (o['lens'] or '').startswith('blocked: decision')
                        and o['item_state'].startswith('blocked: decision') and o['run_check'] == 1
                        and set(o['run_codes']) == set(codes))

            def show(o):
                return ' [observed: %s]' % json.dumps({k: o.get(k) for k in ('stations', 'blocks', 'item_state', 'run_codes',
                                                                             'offered')}, sort_keys=True)[:600]

            def ask(alias, target, text, touchpoint='decision_disposition'):
                rid, receipt, got = open_request(alias, target, touchpoint)
                update = reply(receipt, text)
                return dict(rid=rid, receipt=receipt, terms=got, update=update, text=text)

            before = sweep([s for members in PLANS.values() for s in members])

            # AC1: a blocking specification question and a plan decision, answered on Telegram, bind their
            # exact governing decision in the settlement's own transaction.
            with section(OT, ER):
                q_spec = ask('Q-9601', question('decision:D-9601'), 'accept: the approach is right for this spec')
                q_plan = ask('Q-9602', question('decision:P-9602'), 'accept: the plan should proceed this way')
                acquired = acquire()
                settled_spec = service.settle(q_spec['rid'])
                settled_plan = service.settle(q_plan['rid'])
                after_ac1 = sweep(['VELDO-9601', 'VELDO-9602'])
            with section(OT):
                for label, q, got, rid in (('spec question', q_spec, settled_spec, 'decision:D-9601'),
                                           ('plan decision', q_plan, settled_plan, 'decision:P-9602')):
                    rec = records[rid]
                    s, e, r, b = written(q['rid'])
                    sdata = s[0][1] if len(s) == 1 else {}
                    rdata = r[0][1] if len(r) == 1 else {}
                    bid, bdata = b[0] if len(b) == 1 else (None, {})
                    body = bdata.get('settlement') or {}
                    check(OT, '%s: the owner\'s signed Telegram reply was accepted and settled' % label + seen(got),
                          acquired.get(q['update']['update_id']) == ('answered', None) and got.get('outcome') == 'settled'
                          and len(s) == len(e) == len(r) == 1)
                    check(OT, '%s: exactly one governing binding, for the record it resolves' % label,
                          len(b) == 1 and len(bindings(rid)) == 1 and bdata.get('decision') == rid)
                    check(OT, '%s: the binding is the chosen option, the decider and the time' % label,
                          bdata.get('choice') == 'accept' and body.get('ruling') == 'approve'
                          and body.get('principals') == ['owner'] and bdata.get('decided_by') == ['owner']
                          and isinstance(body.get('settled_at'), str) and body.get('settled_at') == bdata.get('decided_at')
                          and re.match(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$', body.get('settled_at') or '') is not None)
                    check(OT, '%s: the binding is the exact question: decision, revision, framing, subject and scope '
                              'digests, request and version' % label,
                          body.get('schema') == SETTLEMENT and body.get('domain_uuid') == ids['domain_uuid']
                          and body.get('decision_id') == rec['decision_id'] and body.get('decision_revision') == 1
                          and body.get('framing_digest') == rec['framing_digest'] and body.get('subject') == rec['subject']
                          and body.get('scope_digest') == fx_scope(rec['scope']) and body.get('request_id') == q['rid']
                          and body.get('request_version') == 1)
                    check(OT, '%s: the body is signed by the trusted decision signer (independent verification)' % label,
                          bdata.get('signer') == 'veldo-settlement' and verifies(fx_bytes(body), bdata.get('signature')))
                    check(OT, '%s: the settlement, its receipt and the binding name each other' % label,
                          bdata.get('settlement_id') == (s[0][0] if s else None) and bdata.get('receipt_id') == (r[0][0] if r else None)
                          and sdata.get('binding_id') == bid and rdata.get('binding_id') == bid)
                    journal = [set(json.loads(t)) for (t,) in conn.execute('SELECT transition FROM journal ORDER BY seq')]
                    together = [t for t in journal if bid in t]
                    check(OT, '%s: the binding committed in the settlement\'s one journal transaction, with the '
                              'settlement, effect, receipt and terminal request' % label,
                          len(together) == 1 and {s[0][0], e[0][0], r[0][0], q['rid']} <= together[0] if s and e and r else False)
                observed = [o for o in service.observations if o.get('operation') == 'settle'
                            and o.get('request_id') in (q_spec['rid'], q_plan['rid'])]
                check(OT, 'observations join the settlement to its binding and say it is current, without signatures',
                      len(observed) == 2 and all(o.get('binding_id') and o.get('binding_current') is True
                                                 and o.get('binding_refusals') == [] for o in observed)
                      and 'SSH SIGNATURE' not in json.dumps(service.observations))
                # No decision signer: the governing question is refused by name and nothing is written, then the
                # signed service settles the same answer with its binding.
                blind_conn = S.open_store(str(db))
                try:
                    _i, _p, blind = services(blind_conn, signed=False)
                    q_blind = ask('Q-9623', question('decision:D-9623'), 'accept: settle this through the signed service')
                    acquire()
                    refused = blind.settle(q_blind['rid'])
                    nothing = written(q_blind['rid'])
                    pending = (entity(q_blind['rid']) or {}).get('data', {}).get('state') in I.PENDING
                finally:
                    blind_conn.close()
                check(OT, 'without a decision signer a governing question is refused by name (unavailable_service) and '
                          'nothing is written: no settlement, receipt or binding' + seen(refused),
                      refused.get('outcome') == 'refused' and refused.get('reason') == 'unavailable_service'
                      and nothing == ([], [], [], []) and pending)
                settled_blind = service.settle(q_blind['rid'])
                s, e, r, b = written(q_blind['rid'])
                check(OT, 'the signed service then settles the same answer with its binding' + seen(settled_blind),
                      settled_blind.get('outcome') == 'settled' and len(s) == len(r) == len(b) == 1)
                metrics = service.metrics()
                check(OT, 'metrics count the bindings written',
                      metrics.get('bound') == len(of_kind('decision_settlement')) and metrics.get('bound', 0) >= 3)

            # AC1: the resolved request makes the governed work eligible, read here and in another process.
            with section(ER):
                for sid, rid in (('VELDO-9601', 'decision:D-9601'), ('VELDO-9602', 'decision:P-9602')):
                    check(ER, '%s was blocked by its unresolved decision before the settlement' % sid + show(before[sid]),
                          verdict(before[sid], ['unresolved_decision:' + rid]))
                    check(ER, '%s is eligible at every consumer after the settlement' % sid + show(after_ac1[sid]),
                          verdict(after_ac1[sid], []))
                child = base / 'child.py'
                child.write_text(_V69_CHILD)
                done = subprocess.run([sys.executable, '-B', str(child), str(organs), str(db), str(signers), str(repo),
                                       ids['domain_uuid'], ids['repository_uuid']], capture_output=True, text=True,
                                      timeout=120)
                other = json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else {}
                check(ER, 'another process ran to its answer' + ('' if other else ' [stderr: %s]' % done.stderr[-300:]),
                      bool(other))
                for sid, rid, pid in (('VELDO-9601', 'decision:D-9601', 'PLAN-9601'),
                                      ('VELDO-9602', 'decision:P-9602', 'PLAN-9602')):
                    got = (other.get('units') or {}).get(sid) or {}
                    rec = records[rid]
                    read = (other.get('bindings') or {}).get(rid) or {}
                    check(ER, 'another process reads %s eligible: no decision blocker, direct execution clear, '
                              'run-check clear' % sid + ' [observed: %s]' % json.dumps(got)[:300],
                          got.get('blockers') == [] and got.get('direct') == [] and got.get('run_check') == 0)
                    check(ER, 'another process reads the binding of %s: chosen option, decider, time, framing and '
                              'subject digests' % rid,
                          read.get('choice') == 'accept' and read.get('decided_by') == ['owner']
                          and isinstance(read.get('decided_at'), str) and read.get('framing_digest') == rec['framing_digest']
                          and read.get('subject') == rec['subject'] and read.get('verified') is True)

            # AC2: wrong framing, subject or current version under an otherwise valid settlement.
            with section(WF, WS, WV):
                older = dict(records['decision:D-9612']['subject'], digest=fx_digest({'an earlier version': 'VELDO-9612'}))
                other_subject = dict(records['decision:D-9601']['subject'])
                cases = {
                    WF: [('Q-9611', 'decision:D-9611', 'VELDO-9611',
                          question('decision:D-9611', framing_digest=fx_digest({'framing': 'the question before it was reframed'})),
                          'framing')],
                    WS: [('Q-9612', 'decision:D-9612', 'VELDO-9612', question('decision:D-9612', subject=older), 'subject'),
                         ('Q-9613', 'decision:D-9613', 'VELDO-9613', question('decision:D-9613', subject=other_subject),
                          'subject')],
                    WV: [('Q-9614', 'decision:D-9614', 'VELDO-9614', question('decision:D-9614'), 'revision')],
                }
                asked = {}
                for row, items in cases.items():
                    for alias, rid, sid, target, _field in items:
                        asked[alias] = ask(alias, target, 'accept: ruling on the question as shown')
                # The record is revised after the version question was presented (same framing and subject).
                revised = dict(records['decision:D-9614'], revision=2)
                records['decision:D-9614'] = revised
                put('decision:D-9614', 'decision', revised)
                acquire()
                results = {alias: service.settle(a['rid']) for alias, a in asked.items()}
                after_ac2 = sweep(['VELDO-9611', 'VELDO-9612', 'VELDO-9613', 'VELDO-9614'])
            for row, items in cases.items():
                with section(row):
                    for alias, rid, sid, target, field in items:
                        got = results[alias]
                        b = [x for x in bindings(rid) if (x[1].get('settlement') or {}).get('request_id') == asked[alias]['rid']]
                        body = (b[0][1].get('settlement') or {}) if len(b) == 1 else {}
                        named = 'unbound_decision:%s/%s' % (rid, field)
                        check(row, '%s: the owner\'s answer settles as an otherwise valid settlement' % alias + seen(got),
                              got.get('outcome') == 'settled' and len(b) == 1)
                        shown = {'framing': body.get('framing_digest') == target['framing_digest'],
                                 'subject': body.get('subject') == target['subject'],
                                 'revision': body.get('decision_revision') == target['revision']}[field]
                        check(row, '%s: the binding records the %s the owner was shown, not the record\'s' % (alias, field),
                              shown and body.get('decision_id') == records[rid]['decision_id'])
                        check(row, '%s: %s was blocked (unresolved) before and stays blocked, now by %s, at the plan and '
                                   'the direct floor entry' % (alias, sid, named) + show(after_ac2[sid]),
                              verdict(before[sid], ['unresolved_decision:' + rid]) and verdict(after_ac2[sid], [named])
                              and not gate.decide('direct_execution', sid)['eligible'])
                        trace = [o for o in service.observations if o.get('operation') == 'settle'
                                 and o.get('request_id') == asked[alias]['rid']]
                        check(row, '%s: the settlement observation names the binding as not current (%s)' % (alias, named),
                              len(trace) == 1 and trace[0].get('binding_current') is False
                              and trace[0].get('binding_refusals') == [named])
            with section(WV):
                # Supersession: a question at the record's current revision binds and clears the work.
                fresh = ask('Q-9614b', question('decision:D-9614'), 'accept: ruling on the revised question')
                acquire()
                got = service.settle(fresh['rid'])
                now_ = sweep(['VELDO-9614'])['VELDO-9614']
                check(WV, 'a question at the current revision supersedes the stale binding and clears the work' + seen(got)
                      + show(now_), got.get('outcome') == 'settled' and len(bindings('decision:D-9614')) == 2
                      and verdict(now_, []))

            # Threat: a question at a revision the record has not reached. It is refused by name with nothing
            # written, so when the record is revised to it (same framing, subject and scope) the work stays
            # blocked until the genuine question at that revision settles.
            with section(FV):
                rid, sid = 'decision:D-9615', 'VELDO-9615'
                early = ask('Q-9615', question(rid, revision=2), 'accept: ruling on a revision not yet written')
                acquire()
                got = service.settle(early['rid'])
                trace = [o for o in service.observations if o.get('operation') == 'settle'
                         and o.get('request_id') == early['rid']]
                check(FV, 'a question at revision 2 while the record is at revision 1 is refused by name '
                          '(future_revision, a stale subject)' + seen(got),
                      got.get('outcome') == 'refused' and got.get('reason') == 'future_revision'
                      and len(trace) == 1 and trace[0].get('error_class') == 'stale_subject')
                check(FV, 'nothing is written: no settlement, effect, receipt or binding, no binding id for revision 2, '
                          'and the request stays pending',
                      written(early['rid']) == ([], [], [], []) and not bindings(rid)
                      and entity('decision-settlement:%s:2' % rid) is None
                      and (entity(early['rid']) or {}).get('data', {}).get('state') in I.PENDING)
                held = sweep([sid])[sid]
                check(FV, '%s stays blocked as unresolved after the refusal' % sid + show(held),
                      verdict(before[sid], ['unresolved_decision:' + rid]) and verdict(held, ['unresolved_decision:' + rid]))
                # The record is revised to revision 2 with the same framing, subject and scope.
                revised = dict(records[rid], revision=2)
                records[rid] = revised
                put(rid, 'decision', revised)
                reached = sweep([sid])[sid]
                check(FV, 'once the record reaches revision 2, %s is still blocked as unresolved: nothing bound that '
                          'revision early' % sid + show(reached), verdict(reached, ['unresolved_decision:' + rid]))
                genuine = ask('Q-9615b', question(rid), 'accept: ruling on the real revision two')
                acquire()
                settled = service.settle(genuine['rid'])
                b = bindings(rid)
                body = (b[0][1].get('settlement') or {}) if len(b) == 1 else {}
                cleared = sweep([sid])[sid]
                check(FV, 'the genuine revision 2 question settles with its binding and clears %s at every consumer'
                      % sid + seen(settled) + show(cleared),
                      settled.get('outcome') == 'settled' and len(b) == 1 and b[0][0] == 'decision-settlement:%s:2' % rid
                      and body.get('decision_revision') == 2 and body.get('request_id') == genuine['rid']
                      and verdict(cleared, []))

            # The owner's ruling is the signed body's ruling: reject and return for elaboration on a current
            # exact question are bound as ruled, and the work stays blocked by that ruling at every consumer.
            with section(RU):
                ruled = {'VELDO-9616': ('reject', 'reject: not this approach'),
                         'VELDO-9617': ('return_for_elaboration', 'return_for_elaboration: say how it is tested')}
                asked_ru = {sid: ask('Q-' + sid[-4:], question('decision:D-' + sid[-4:]), text)
                            for sid, (_choice, text) in sorted(ruled.items())}
                acquire()
                got_ru = {sid: service.settle(a['rid']) for sid, a in sorted(asked_ru.items())}
                after_ru = sweep(sorted(ruled))
                for sid, (choice, _text) in sorted(ruled.items()):
                    rid, ruling = 'decision:D-' + sid[-4:], CHOICES[choice]
                    named = 'decision_ruling:%s/%s' % (rid, ruling)
                    s, e, r, b = written(asked_ru[sid]['rid'])
                    bdata = b[0][1] if len(b) == 1 else {}
                    body = bdata.get('settlement') or {}
                    check(RU, '%s: the owner\'s %s settles with one binding' % (sid, choice) + seen(got_ru[sid]),
                          got_ru[sid].get('outcome') == 'settled' and got_ru[sid].get('ruling') == ruling
                          and len(s) == len(r) == len(b) == 1 and len(bindings(rid)) == 1)
                    check(RU, '%s: the signed body carries the ruling %s, the binding the chosen option %s, and the '
                              'signature verifies' % (sid, ruling, choice),
                          body.get('ruling') == ruling and bdata.get('choice') == choice
                          and body.get('decision_revision') == records[rid]['revision']
                          and verifies(fx_bytes(body), bdata.get('signature')))
                    check(RU, '%s: blocked (unresolved) before, and blocked by %s at every consumer after'
                          % (sid, named) + show(after_ru[sid]),
                          verdict(before[sid], ['unresolved_decision:' + rid]) and verdict(after_ru[sid], [named])
                          and not gate.decide('direct_execution', sid)['eligible'])
                    trace = [o for o in service.observations if o.get('operation') == 'settle'
                             and o.get('request_id') == asked_ru[sid]['rid']]
                    check(RU, '%s: the settlement observation names the binding as not current (%s)' % (sid, named),
                          len(trace) == 1 and trace[0].get('binding_current') is False
                          and trace[0].get('binding_refusals') == [named])

            # Threat: an unsupported subject kind, another touchpoint, or an absent record stops by name.
            with section(UK):
                contract_q = fx_target('decision:D-9621', dict(
                    decision_id='D-9621', revision=1, framing_digest=records['decision:D-9621']['framing_digest'],
                    subject=dict(records['decision:D-9621']['subject']), scope_digest=fx_scope(records['decision:D-9621']['scope'])))
                refused_terms = terms('T-contract', contract_q)
                check(UK, 'terms asking about an unsupported subject kind are refused (unsupported_subject) and not '
                          'recorded' + seen(refused_terms),
                      refused_terms.get('outcome') == 'refused' and refused_terms.get('reason') == 'unsupported_subject'
                      and not of_kind('settlement_terms', 'target', contract_q))
                other_tp = terms('T-grooming', question('decision:D-9631'), touchpoint='grooming')
                check(UK, 'a governing question on another touchpoint is refused (unsupported_touchpoint)' + seen(other_tp),
                      other_tp.get('outcome') == 'refused' and other_tp.get('reason') == 'unsupported_touchpoint')
                # A question that names a supported subject for a record whose governed subject is a contract.
                masked = ask('Q-9621', fx_target('decision:D-9621', dict(
                    decision_id='D-9621', revision=1, framing_digest=records['decision:D-9621']['framing_digest'],
                    subject=dict(kind='spec', id='VELDO-9621', digest=fx_digest({'masked': 'VELDO-9621'})),
                    scope_digest=fx_scope(records['decision:D-9621']['scope']))), 'accept: bind the contract')
                absent = ask('Q-absent', fx_target('decision:D-ABSENT', dict(
                    decision_id='D-ABSENT', revision=1, framing_digest=fx_digest({'framing': 'nothing'}),
                    subject=dict(kind='spec', id='VELDO-9621', digest=fx_digest({'absent': 1})),
                    scope_digest=fx_digest({'scope': 'nothing'}))), 'accept: bind a record nobody wrote')
                acquire()
                stop = service.settle(masked['rid'])
                gone = service.settle(absent['rid'])
                check(UK, 'a record whose governed subject kind is unsupported stops the settlement (unsupported_subject); '
                          'nothing is written and the request stays pending' + seen(stop),
                      stop.get('outcome') == 'refused' and stop.get('reason') == 'unsupported_subject'
                      and written(masked['rid']) == ([], [], [], []) and not bindings('decision:D-9621')
                      and (entity(masked['rid']) or {}).get('data', {}).get('state') in I.PENDING)
                check(UK, 'a question naming no recorded governing decision stops (missing_decision); nothing is '
                          'written' + seen(gone),
                      gone.get('outcome') == 'refused' and gone.get('reason') == 'missing_decision'
                      and written(absent['rid']) == ([], [], [], []))
                kept = sweep(['VELDO-9621'])['VELDO-9621']
                check(UK, 'the work the unsupported record governs stays blocked' + show(kept),
                      verdict(kept, ['unresolved_decision:decision:D-9621']))

            # AC3: only the accepted binding resolves a referenced decision, at every enabled consumer.
            with section(IB):
                driven = {('plan.py', 'cmd_status'), ('plan.py', 'cmd_run_check'), ('plan.py', '_decision_blocks'),
                          ('frontier.py', '_plan_build_candidates'), ('runstatus.py', '_burndown'),
                          ('control_eligibility.py', 'Gate._predicate'), ('control_eligibility.py', 'Gate.decision_blockers'),
                          ('control_eligibility.py', 'Gate._decision_codes')}
                check(IB, 'the consumers driven here are every enabled consumer the decision service registers',
                      set(DD.CONSUMERS) == driven)
                # The detached receipt: a decision disposition settled against the record under another target
                # kind, so a receipt exists and no binding does.
                detached = ask('Q-9636-receipt', {'kind': 'decision_record', 'ref': 'decision:D-9636',
                                                  'digest': fx_digest(records['decision:D-9636'])},
                               'accept: a receipt without a binding')
                unresolved = ask('Q-9631', question('decision:D-9631'), 'accept: never settled')
                acquire()
                receipt_only = service.settle(detached['rid'])
                cases3 = {'VELDO-9631': (['unresolved_decision:decision:D-9631'], True),
                          'VELDO-9632': (['unresolved_decision:decision:D-9632'], True),
                          'VELDO-9633': (['unresolved_decision:decision:D-9633'], False),
                          'VELDO-9634': (['unresolved_decision:decision:D-9634'], True),
                          'VELDO-9635': (['unresolved_decision:decision:D-9635'], True),
                          'VELDO-9636': (['unresolved_decision:decision:D-9636'], True)}
                held = sweep(sorted(cases3))
                check(IB, 'the detached receipt is a settled request with no binding' + seen(receipt_only),
                      receipt_only.get('outcome') == 'settled' and not bindings('decision:D-9636')
                      and len(written(detached['rid'])[2]) == 1)
                for sid, (codes, everywhere) in sorted(cases3.items()):
                    what = {'VELDO-9631': 'unresolved', 'VELDO-9632': 'not yet settled', 'VELDO-9633': 'inline resolved '
                            'text in the plan file only', 'VELDO-9634': 'inline resolved text in the accepted plan',
                            'VELDO-9635': 'the record\'s own settled status', 'VELDO-9636': 'a detached receipt'}[sid]
                    check(IB, '%s (%s) is blocked by name at every consumer that sees it' % (sid, what) + show(held[sid]),
                          verdict(held[sid], codes, everywhere))
                # The owner then settles each governing question on Telegram, except the unresolved one.
                settled3 = {}
                for sid in ('VELDO-9632', 'VELDO-9633', 'VELDO-9634', 'VELDO-9635', 'VELDO-9636'):
                    rid = 'decision:D-' + sid[-4:]
                    settled3[sid] = ask('Q-%s' % sid[-4:], question(rid), 'accept: settled on the record')
                acquire()
                results3 = {sid: service.settle(a['rid']) for sid, a in settled3.items()}
                cleared = sweep(sorted(cases3))
                check(IB, 'VELDO-9631, never answered, stays blocked as unresolved at every consumer' + show(cleared['VELDO-9631']),
                      verdict(cleared['VELDO-9631'], ['unresolved_decision:decision:D-9631']))
                for sid, got in sorted(results3.items()):
                    check(IB, '%s clears at every consumer only once its accepted binding exists' % sid + seen(got)
                          + show(cleared[sid]), got.get('outcome') == 'settled' and verdict(cleared[sid], []))
        finally:
            server.shutdown()
            server.server_close()
            conn.close()
    return rows


# The other process: the installed store, snapshot, eligibility and plan modules over a read-only
# connection; each unit's decision answer, direct execution and run-check, and each binding read back
# through the digest-verified snapshot reader.
_V69_CHILD = '''import contextlib, importlib.util, io, json, sys
from pathlib import Path
organs, db, signers, repo, domain, repository = sys.argv[1:7]
def load(name):
    s = importlib.util.spec_from_file_location('child_' + name, str(Path(organs) / (name + '.py')))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
EL = load('control_eligibility'); S = load('control_store'); SN = load('control_snapshot'); PL = load('plan')
conn = S.open_store(db, mode='r')
gate = EL.Gate(S, conn, domain_uuid=domain, repository_uuid=repository, workspace=repo,
               settlement_trust=EL.DD.SettlementTrust(Path(signers).read_text()))
out = {'units': {}, 'bindings': {}}
for sid, pid in (('VELDO-9601', 'PLAN-9601'), ('VELDO-9602', 'PLAN-9602')):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = PL.cmd_run_check(str(Path(repo) / 'plans' / (pid + '-fixture.md')), sid, eligibility=gate)
    out['units'][sid] = {'blockers': gate.decision_blockers(sid), 'run_check': rc,
                         'direct': gate.decide('direct_execution', sid)['refusals']}
for (eid, text) in conn.execute("SELECT id, data FROM entities WHERE kind='decision_settlement' ORDER BY id").fetchall():
    item = SN.entity(S, conn, eid)
    data = item['value']['data']
    body = data.get('settlement') or {}
    trusted = EL.DD.SettlementTrust(Path(signers).read_text())
    out['bindings'].setdefault(data.get('decision'), {
        'choice': data.get('choice'), 'decided_by': body.get('principals'), 'decided_at': body.get('settled_at'),
        'framing_digest': body.get('framing_digest'), 'subject': body.get('subject'),
        'verified': trusted.verify(EL.DD.settlement_bytes(body), data.get('signature'), data.get('signer'))})
conn.close()
print(json.dumps(out))
'''

_v69_started = __import__('time').monotonic()
_v69_rows = _v69_suite()
for _v69_name, _v69_observed in _v69_rows.items():
    _v69_ok = bool(_v69_observed) and all(ok for _, ok in _v69_observed)
    if not _v69_ok:
        for _v69_label, _v69_one in _v69_observed:
            if not _v69_one:
                print('  VELDO-0069 %s detail: %s' % (_v69_name, _v69_label))
    expect('VELDO-0069 ' + _v69_name, _v69_ok)
print('VELDO-0069 suite seconds: %.3f' % (__import__('time').monotonic() - _v69_started))
