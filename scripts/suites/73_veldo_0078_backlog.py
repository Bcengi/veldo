"""VELDO-0078: backlog lifecycle and priority-controlled execution over a real signed store.

Run: python3 scripts/selftest.py --suite 73_veldo_0078_backlog

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy every
service loads; the production anchors below are the registered mutation driver's seams, so a mutation of
control_backlog.py, control_eligibility.py, tasks.py or frontier.py reaches the service, the Gate, the
claim entries and the reader in another process. Real SQLite store with OpenSSH command, claim, journal and API signatures; the backlog
items are taken from RAW features of an objective the project's owner accepted through the real VELDO-0077
service; every admission, priority, block resolution and alternative outcome is a real VELDO-0064 request
presented by the VELDO-0065 presenter over a loopback Bot API (no network, no real token), answered through
the authenticated API edge and settled by the real VELDO-0068 settlement. The claim entries are the real
ones: the frontier's offers through the VELDO-0052 Gate over spec files, the VELDO-0031 claim receiver with
signed claim commands, and tasks.claim_task over the file ledger and over claim.py's authority client root
(an in-process client of the same receiver). Landing receipts are completion_receipt records in the shape
VELDO-0057 writes, judged by the one completion reader. A reader in another process opens the store
read-only. Where the backlog service is absent (the pre-change tree, for the red record) every backlog
command is answered no_backlog_service and each row fails by its own assertions.
"""


def _v78_suite():
    import contextlib
    import copy
    import http.server
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import types

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {'control_backlog.py': ROOT / ".veldo" / "control_backlog.py",
                  'control_eligibility.py': ROOT / ".veldo" / "control_eligibility.py",
                  'tasks.py': ROOT / ".veldo" / "tasks.py",
                  'frontier.py': ROOT / ".veldo" / "frontier.py"}
    SCAFFOLD = ROOT / ".veldo" / "init_scaffold.py"
    PREFIX = 'VELDO-0078 '
    CHOICES = ['accept', 'return_for_elaboration', 'reject']
    # AC1's declared set: the four kinds of work, and the claim entries each is driven through.
    AC1_SET = ('intake-only', 'prepared', 'admitted-without-priority', 'prioritized')
    ENTRIES = ('offer', 'receiver', 'task-ledger', 'task-authority')
    # AC3's declared set of DONE attempts.
    AC3_SET = ('path-only output', 'canceled attempt', 'missing required receipt', 'incomplete landing receipt',
               'complete receipts or an authorized alternative')

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    emitted, raised = set(), []

    def check(label, parts):
        """One row: every named part must hold. A part that raises while judging is a failed part."""
        emitted.add(label)
        failed = []
        for name, condition in parts:
            try:
                ok = bool(condition() if callable(condition) else condition)
            except Exception as error:  # noqa: BLE001 - a malformed answer is a failed part, never a raise
                ok, name = False, '%s (%s)' % (name, type(error).__name__)
            if not ok:
                failed.append(name)
        if failed:
            print('  %sdetail: %s: %s' % (PREFIX, label, '; '.join(failed)))
        expect(PREFIX + label, not failed)

    @contextlib.contextmanager
    def region(*labels):
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            print('  %sdetail: %s did not run to its end: %r' % (PREFIX, labels[0], error))
            for label in labels:
                if label not in emitted:
                    check(label, [('region raised', False)])

    def attempt(fn):
        """An entry's answer, or ('error', <type>) when the entry cannot even be asked (the red tree)."""
        try:
            return fn()
        except Exception as error:  # noqa: BLE001 - an entry that cannot answer is a failed part
            return ('error', type(error).__name__)

    def message(st, sender, chat, text, reply_to=None):
        with st['lock']:
            st['next'] += 1
            st['tick'] += 1
            m = {'message_id': st['next'], 'from': dict(sender), 'chat': dict(chat), 'date': 1791300000 + st['tick'],
                 'text': text}
            if reply_to is not None and (chat['id'], reply_to) in st['messages']:
                held = st['messages'][(chat['id'], reply_to)]
                m['reply_to_message'] = copy.deepcopy({k: v for k, v in held.items() if k != 'reply_to_message'})
            st['messages'][(chat['id'], m['message_id'])] = m
            return m

    class BotApi(http.server.BaseHTTPRequestHandler):
        """Loopback getMe, getUpdates and sendMessage in the Bot API shapes, for one bot."""
        state = None

        def log_message(self, *args):
            pass

        def do_POST(self):
            st = self.state
            raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
            body = json.loads(raw) if raw else {}
            _, _, rest = self.path.partition('/bot')
            name, _, method = rest.partition('/')
            if name != 'bot78':
                return self._answer(401, {'ok': False, 'error_code': 401, 'description': 'Unauthorized'})
            if method == 'getMe':
                return self._answer(200, {'ok': True, 'result': dict(st['user'], can_join_groups=True)})
            if method == 'getUpdates':
                return self._answer(200, {'ok': True, 'result': []})
            if method == 'sendMessage':
                chat = {'id': body.get('chat_id'), 'type': 'private'}
                reply = (body.get('reply_parameters') or {}).get('message_id')
                st['sent'].append(body.get('chat_id'))
                return self._answer(200, {'ok': True, 'result': message(st, st['user'], chat, body['text'], reply)})
            return self._answer(404, {'ok': False, 'error_code': 404, 'description': 'Not Found'})

        def _answer(self, code, value):
            payload = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    connections, servers = [], []
    with tempfile.TemporaryDirectory(prefix='v78-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        try:
            with region('install/assets'):
                scaffold = load('v78_scaffold', SCAFFOLD)
                rel = '.veldo/control_backlog.py'
                both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
                if both:
                    scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
                same = [r for r in ('.veldo/tasks.py', '.veldo/frontier.py', '.veldo/init_scaffold.py',
                                    '.veldo/control_eligibility.py')
                        if (ROOT / 'engine' / r).read_bytes() == (ROOT / r).read_bytes()]
                check('install/assets', [
                    (rel + ' installed by the scaffold', rel in scaffold._FILES),
                    (rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE),
                    (rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                    (rel + ' laid by the installer', both and (base / 'laid' / rel).is_file()
                     and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes()),
                    ('tasks, frontier, init_scaffold and control_eligibility engine copies identical', len(same) == 4),
                    ('the task source that loads it is installed beside it', '.veldo/tasks.py' in scaffold._FILES)])

            claims = load('v78_claims', mods / 'control_claim.py')
            S, CM, AC = claims.S, claims.CM, claims.AC
            K = load('v78_keys', mods / 'control_keys.py')
            I = load('v78_inbox', mods / 'control_assignment.py')
            P = load('v78_projection', mods / 'control_channel_projection.py')
            V = load('v78_presentation', mods / 'control_channel_presentation.py')
            EV = load('v78_attribution', mods / 'control_channel_attribution.py')
            E = load('v78_enrollment', mods / 'control_channel_enrollment.py')
            ST = load('v78_settlement', mods / 'control_request_settlement.py')
            IN = load('v78_intake', mods / 'control_intake.py')
            PJ = load('v78_project', mods / 'control_project.py')
            OB = load('v78_objective', mods / 'control_objective.py')
            FR = load('v78_frontier', mods / 'frontier.py')
            TS = load('v78_tasks', mods / 'tasks.py')
            CLF = load('v78_claim', mods / 'claim.py')
            VAL = load('v78_validate', mods / 'validate.py')
            contract = load('v78_contract', mods / 'entity_contract.py')
            CB = load('v78_backlog', mods / 'control_backlog.py') if (mods / 'control_backlog.py').is_file() else None
            CYC = load('v78_cycle', mods / 'control_workflow_cycle.py')
            DOMAIN, REPO = 'domain-78', 'repository-78'
            ids = dict(domain_uuid=DOMAIN, repository_uuid=REPO, store_uuid='store-78')

            keys, protected, edge_dir = base / 'keys', base / 'protected', base / 'edge'
            for d in (keys, protected, edge_dir):
                d.mkdir(mode=0o700)
            people = ('steward', 'olga', 'zed')
            services = ('pm', 'api-edge', 'builder', 'builder-b', 'closer')
            keyfile = {who: keys / who for who in ('authority',) + people + services}
            keyfile['edge'] = protected / 'edge-telegram'
            keyfile['edge-auth'] = edge_dir / 'edge-auth'
            public = {}
            for who, path in keyfile.items():
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v78-' + who, '-f', str(path)],
                               check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
                public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])

            def sign_as(who, data, namespace='veldo-command'):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keyfile[who]), '-n', namespace], input=data,
                                      capture_output=True, check=True, timeout=20).stdout.decode()

            def journal_sign(data):
                return sign_as('authority', data, 'veldo-journal')

            serial = [0]

            def next_id(prefix):
                serial[0] += 1
                return '%s-%d' % (prefix, serial[0])

            (base / 'authority').mkdir()
            db = base / 'authority' / 'control.sqlite3'
            conn = S.open_store(str(db))
            connections.append(conn)
            CM.attach(S)
            K.attach(S)
            signer_repo = base / 'signer-repository'
            signer_repo.mkdir()
            projection = signer_repo / '.veldo' / 'keys' / 'allowed_signers'

            def envelope(command, principal):
                now = CM.authority_state(S, conn)
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

            def enroll(who, principal_type, roles, scope):
                admin('steward', 'enroll_principal', {'principal': who, 'principal_type': principal_type, 'roles': roles,
                                                      'public_key': public[who], 'independence_group': who,
                                                      'scope': scope}, enrollee=who)

            admin('steward', 'enroll_principal', {'principal': 'steward', 'principal_type': 'person',
                                                  'roles': ['membership_steward', 'project_owner'], 'public_key': public['steward'],
                                                  'independence_group': 'steward', 'scope': '*'})
            deciders = ['project_owner', 'admission_authority', 'priority_authority']
            enroll('olga', 'person', deciders, ['proj-a'])
            enroll('zed', 'person', deciders, ['proj-a'])
            enroll('pm', 'service', [], ['proj-a'])
            enroll('api-edge', 'service', [], ['proj-a'])
            enroll('builder', 'service', [], [REPO])
            enroll('builder-b', 'service', [], [REPO])
            # A worker that stops for a person about its claimed unit (VELDO-0133): the project and the repository.
            enroll('closer', 'service', [], ['proj-a', REPO])

            def fixture(eid, kind, data):
                row = conn.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
                return S.execute(conn, dict(command_id=next_id('fixture'), principal='authority', operation='upsert_entity',
                                            parameters=dict(entity_id=eid, kind=kind, data=data),
                                            expected_versions={eid: row[0] if row else 0}, artifact_digests=[],
                                            nonce=next_id('fixture-nonce')), 'authority', journal_sign, 1)

            chats = {'olga': 5780001, 'zed': 5780002}
            for who, chat in chats.items():
                fixture('channel-enrollment:telegram_chat:' + who, 'channel_enrollment',
                        dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal=who, chat_id=chat,
                             revoked_at=None))
            enrollment = E.Enrollment(S, conn, ids, 'authority', journal_sign, projection=projection)
            edge_params = {'channel': 'telegram_chat', 'edge_principal': 'telegram-edge', 'edge_key_id': 'edge-telegram',
                           'public_key': public['edge'], 'connection_public_key': public['edge-auth'], 'scope': ['proj-a']}
            edge_command = {'command_id': next_id('edge'), 'operation': 'enroll_channel_edge',
                            'target': 'channel:telegram_chat', 'parameters': edge_params, 'artifact_digests': [],
                            'expected_versions': {}}
            edge_env = envelope(edge_command, 'steward')
            enrollment.admit(edge_env, edge_command, sign_as('steward', AC.canonical_envelope_bytes(edge_env)),
                             sign_as('edge', AC.canonical_envelope_bytes(edge_env), 'veldo-edge-possession'))

            api = {'tick': 0, 'next': 9000, 'messages': {}, 'sent': [], 'lock': threading.Lock(),
                   'user': {'id': 8000000078, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_backlog_bot'}}
            handler = type('V78Handler', (BotApi,), {'state': api})
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
            servers.append(server)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = 'http://127.0.0.1:%d' % server.server_address[1]

            inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
            presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, 'bot78'), conn, 'authority',
                                    journal_sign, assignment=I)
            settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', journal_sign, assignment=I,
                                       presentation=V, api_edge='api-edge')
            acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, 'bot78'), conn, 'authority',
                                   journal_sign, 'telegram-edge', lambda m: sign_as('edge', m, 'veldo-command'))
            intake = IN.Intake(S, CM, AC, acquirer, conn, domain=DOMAIN, projects=['proj-a'], api_edge='api-edge',
                               journal_signer='authority', sign=journal_sign)
            projects = PJ.Projects(S, CM, conn, ids, 'authority', journal_sign, stop=lambda dispatch, reason: False)
            receiver = claims.Receiver(conn, ids, 'authority', journal_sign)

            def signed(who, body):
                return {'command': body, 'signature': sign_as(who, S.canonical_bytes(body))}

            activation = projects.apply(signed('olga', dict(
                ids, operation='activate', project='proj-a', principal='olga', command_id=next_id('pc'), nonce=next_id('pn'),
                owner='olga', charter={'purpose': 'Sell passes to travelers.'}, execution_repository=REPO,
                authority_policy={'objective_acceptance': ['project_owner'], 'admission': ['admission_authority']},
                coordination_budget={'capacity': 5, 'invocations': 5, 'wall_seconds': 500})))

            # The workspace: ready standalone specs the frontier reads, the task set, declared outputs.
            work = base / 'work'
            (work / 'specs').mkdir(parents=True)
            (work / '.veldo' / 'tasks').mkdir(parents=True)
            (work / 'out').mkdir()
            ledger = base / 'ledger'
            ledger.mkdir()
            SPECS = ('VELDO-9781', 'VELDO-9782', 'VELDO-9783', 'VELDO-9784', 'VELDO-9785', 'VELDO-9786', 'VELDO-9789')
            for sid in SPECS:
                (work / 'specs' / ('%s-backlog-fixture.md' % sid)).write_text('\n'.join([
                    '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Backlog fixture unit', 'status: ready',
                    'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                    'protected_paths: []', 'acceptance_criteria:', '  - id: AC1', '    text: The unit check passes.',
                    'required_evidence: [unit]', 'rollback: git revert', '---', '', '## Intent', '', 'Fixture.', '']))
            TASKS = ('TASK-78-1', 'TASK-78-2', 'TASK-78-3', 'TASK-78-4', 'TASK-78-grow')
            lines = ['schema: veldo.tasks/v1', 'id: TASKSET-78', 'version: 1', 'tasks:']
            for tid in TASKS:
                lines += ['  - id: ' + tid, '    kind: review', '    target: specs/' + tid + '.md',
                          '    produces: out/' + tid + '.md']
            (work / '.veldo' / 'tasks' / 'backlog.yaml').write_text('\n'.join(lines) + '\n')
            tdir = work / '.veldo' / 'tasks'

            reader = S.open_store(str(db), mode='r')
            connections.append(reader)
            events = []
            gate = FR.EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPO, workspace=str(work),
                              observe=events.append)

            service = (CB.Backlog(S, CM, conn, ids, 'authority', journal_sign, workspace=str(work))
                       if CB is not None else None)
            missing = {'ok': False, 'reason': 'no_backlog_service'}

            def entity(eid):
                row = conn.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (eid,)).fetchone()
                return None if row is None else {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])}

            def data_of(eid):
                return (entity(eid) or {}).get('data') or {}

            def item(iid):
                row = entity(iid) if isinstance(iid, str) else None
                return dict(row['data'], version=row['version']) if row and row['kind'] == 'backlog_item' else {}

            def of_kind(kind):
                return [(eid, json.loads(t)) for eid, t in conn.execute('SELECT id, data FROM entities WHERE kind=? ORDER BY id',
                                                                       (kind,))]

            def bsend(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('bc'), nonce=next_id('bn'), **fields)
                return service.apply(signed(who, body)) if service is not None else dict(missing)

            def bop(who, op, iid, **fields):
                return bsend(who, op, item=iid, item_version=item(iid).get('version'), **fields)

            def present(alias, target, brief, owner='olga', touchpoint='decision_disposition', proposal=None):
                """The requester's terms, the inbox request with its framing, and its presentation."""
                terms = settlement.terms(signed('pm', dict(ids, operation='terms', terms=alias, principal='pm',
                                                           command_id=next_id('terms'), nonce=next_id('tn'),
                                                           touchpoint=touchpoint, target=target, proposal=proposal,
                                                           required_roles=[], quorum=None)))
                inbox.apply(signed('pm', dict(ids, operation='open', alias=alias, principal='pm', command_id=next_id('c'),
                                              nonce=next_id('n'), assignment=dict(
                                                  kind='decision', owner=owner, scope=['proj-a'],
                                                  deadline='2026-10-30T17:00:00Z', budget={'owner_minutes': 15}, brief=brief,
                                                  choices=list(CHOICES), subject=terms.get('subject') or {}))))
                rid = I.assignment_id(REPO, alias)
                presenter.frame(signed('pm', dict(ids, operation='frame', alias=alias, principal='pm', request_version=1,
                                                  risk_statement='Low: a wrong choice costs one grooming cycle.',
                                                  command_id=next_id('f'), nonce=next_id('fn'))))
                presenter.present(rid)
                return rid, presenter.current(rid) or {}

            def answer(receipt, choice, who='olga'):
                body = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=next_id('ans'),
                            principal=who, request_id=receipt.get('request_id'), request_version=receipt.get('request_version'),
                            presentation_id=receipt.get('presentation_id'), presentation_digest=receipt.get('brief_digest'),
                            presentation_version=receipt.get('presentation_version'), choice=choice,
                            rationale='I have read the item, its units and their scope.')
                return settlement.api_answer({'answer': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def placeholder(iid):
                return {'kind': 'backlog_item', 'ref': str(iid), 'digest': 'sha256:none'}

            def decide(iid, touchpoint, alias, choice='accept', owner='olga', target=None, brief=None, proposal=None):
                """The owner's settled answer on one touchpoint about the item as it stands now: (request, settled)."""
                record = item(iid)
                if target is None:
                    target = CB.decision_target(record) if CB is not None and record else placeholder(iid)
                if brief is None:
                    shown = {'admission': 'admission_brief', 'priority': 'priority_brief'}.get(touchpoint)
                    brief = getattr(CB, shown)(record) if CB is not None and record and shown else 'Decide %s.' % iid
                rid, receipt = present(alias, target, brief, owner, touchpoint, proposal)
                return rid, answer(receipt, choice, owner)

            def admit(iid, alias, choice='accept'):
                rid, settled = decide(iid, 'admission', alias, choice)
                return rid, settled, bop('pm', 'admit', iid, request=rid)

            def prioritize(iid, alias, choice='accept'):
                rid, settled = decide(iid, 'priority', alias, choice, proposal={'rank': 1})
                return rid, settled, bop('pm', 'prioritize', iid, request=rid)

            def unit_entry(name, produces=None):
                entry = dict(unit=name, specification=name if name.startswith('VELDO-') else 'VELDO-9785',
                             scope=['checkout'], requirements=[], eligible_holders=['builder', 'builder-b'])
                if produces:
                    entry['produces'] = produces
                return entry

            def claim_packet(who, unit, op='claim', generation=0):
                command = dict(ids, operation=op, unit_id=unit, principal=who, command_id=next_id('cl'),
                               nonce=next_id('cn'), generation=generation, capabilities=[])
                return {'command': command, 'signature': sign_as(who, S.canonical_bytes(command))}

            def rclaim(who, unit):
                return receiver.apply(claim_packet(who, unit))

            class Authority:
                """claim.py's authority client root, in process: every claim is a signed command to the receiver."""
                authority_claim_client = True

                def __init__(self, who):
                    self.who = who

                def claim(self, unit, worker, worker_caps=None, requirements=None):
                    result = rclaim(self.who, unit)
                    return bool(result.get('ok')), result.get('reason')

            def offers():
                found = attempt(lambda: FR.claimable(repo_root=str(work), claims_root=str(ledger), eligibility=gate))
                return sorted(u['spec'] for u in found) if isinstance(found, list) else found

            def task_claim(tid, who='builder', root=None):
                return attempt(lambda: TS.claim_task(tid, who, tdir=str(tdir), root=str(work), parse=VAL.parse_yamlish,
                                                     claims_root=root if root is not None else str(ledger),
                                                     eligibility=gate))

            def concluded(tid, with_gate=True):
                task = {'id': tid, 'kind': 'review', 'target': 'specs/%s.md' % tid, 'produces': 'out/%s.md' % tid}
                if not with_gate:
                    return attempt(lambda: TS.concluded(task, root=str(work)))
                return attempt(lambda: TS.concluded(task, root=str(work), eligibility=gate))

            def shown(name, *args, default):
                """The brief the service says its owner must be shown (the default where it names none)."""
                found = getattr(CB, name, None)
                return found(*args) if callable(found) else default

            def executable(uid):
                return CB.executable_problems(reader, uid) if CB is not None else ['no_backlog_service']

            def receipt(uid, revision, n=0, landing=None):
                pub = {f: f + '/' + uid for f in (
                    'implementation_commit', 'proof_digest', 'reviewed_source_digest', 'old_remote_tip',
                    'candidate_commit', 'tested_tree', 'gate_invocation', 'remote_confirmation', 'replication_receipt',
                    'dispatch_id')} | {'gate_output_location': 'outside/' + uid, 'unit_id': uid}
                pub.update(landing or {})
                fixture('receipt:revision_landed:%s:%d:%d' % (uid, revision, n), 'completion_receipt', {
                    'fact': 'revision_landed', 'subject': {'id': uid, 'revision': revision},
                    'publication_receipt': {k: v for k, v in pub.items() if v is not None},
                    'remote_confirmation': 'refs/heads/main', 'replicated': True, 'spec_shipped_event': 'event/' + uid})

            # The accepted objective the backlog items are taken from, and its RAW features.
            body = {'schema': IN.API_SCHEMA, 'domain': DOMAIN, 'request_id': 'api-78-2', 'edge': 'api-edge',
                    'principal': 'olga', 'text': 'For proj-a: travelers can buy a pass in two taps.', 'project': None,
                    'clarifies': None}
            m1 = intake.receive('api_request', {'request': body, 'signature': sign_as('api-edge', S.canonical_bytes(body))})

            def osend(who, op, **fields):
                body = dict(ids, operation=op, principal=who, command_id=next_id('oc'), nonce=next_id('on'), **fields)
                return objectives.apply(signed(who, body))

            objectives = OB.Objectives(S, CM, conn, ids, 'authority', journal_sign, workspace=str(work))
            proposed = osend('pm', 'propose', proposal=m1.get('proposal_id'), outcome='A traveler buys a pass in two taps.',
                             scope=['checkout', 'payments'], authority={'acceptor': 'olga', 'assessor': 'zed'},
                             evidence_requirements=[{'id': 'outcome', 'kind': 'gate_observation'}])
            o1 = proposed.get('objective_id')
            record = OB.read(conn, o1) or {}
            rid_o, receipt_o = present('OBJ-78', OB.acceptance_target(record), OB.acceptance_brief(record))
            answer(receipt_o, 'accept')
            accepted = osend('pm', 'accept', objective=o1, objective_version=(OB.read(conn, o1) or {}).get('version'),
                             request=rid_o)
            features = {}
            for name in ('intake', 'prepared', 'admitted', 'prioritized', 'main', 'rejected', 'returned', 'closed'):
                made = osend('pm', 'propose_feature', objective=o1, objective_version=(OB.read(conn, o1) or {}).get('version'),
                             feature='f-' + name, title='Feature %s' % name, scope=['checkout'])
                features[name] = made.get('feature_id')

            def take(name, who='pm', work_class='PRODUCT_CHANGE'):
                result = bsend(who, 'take', feature=features[name], work_class=work_class)
                return result, result.get('item_id') or (CB.item_id(features[name]) if CB is not None else 'backlog:' + name)

            # AC1: only admitted, prioritized work creates executable engineering units, at every claim entry.
            with region('priority/declared-set', 'priority/missing-priority', 'priority/store-inspection',
                        'priority/owner-decision', 'lifecycle/foreign-sources'):
                stage = {}
                took = {}
                for n, (label, name) in enumerate(zip(AC1_SET, ('intake', 'prepared', 'admitted', 'prioritized')), 1):
                    took[label], stage[label] = take(name)
                    units = [unit_entry('VELDO-978%d' % n), unit_entry('TASK-78-%d' % n)]
                    if label == 'intake-only':
                        continue
                    bop('pm', 'prepare', stage[label], units=units)
                    if label == 'prepared':
                        continue
                    bop('pm', 'request_grooming', stage[label])
                    admit(stage[label], 'ADM-78-%d' % n)
                    if label == 'admitted-without-priority':
                        continue
                    prioritize(stage[label], 'PRI-78-%d' % n)
                offered = offers()

                def assign(subject):
                    """The VELDO-0132 cycle's real assignment step (Cycles._assign) for `subject` over this Gate, with
                    the role check it makes first answered None and its record writes returned instead of stored."""
                    held = types.SimpleNamespace(gate=gate, role_problem=lambda definition, node: None,
                                                 _update=lambda record, action, **fields: dict(record, action=action))
                    held._refuse = lambda record, code, codes=None, **fields: CYC.Cycles._refuse(held, record, code, codes,
                                                                                                 **fields)
                    definition = {'references': {'roles': {'builder': {'id': 'role:b', 'version': 1, 'digest': 'd'}}}}
                    return attempt(lambda: CYC.Cycles._assign(held, {'subject': subject, 'position': 'build'}, definition,
                                                              {'config': {'role': 'builder'}}))
                cycle_prioritized = assign('VELDO-9784')
                table = {}
                for n, label in enumerate(AC1_SET, 1):
                    spec, task = 'VELDO-978%d' % n, 'TASK-78-%d' % n
                    got = rclaim('builder', spec)
                    table[label] = {'offer': isinstance(offered, list) and spec in offered,
                                    'receiver': (bool(got.get('ok')), got.get('reason')),
                                    'task-ledger': task_claim(task),
                                    'task-authority': task_claim(task, root=Authority('builder'))}
                expected = {
                    'intake-only': {'offer': False, 'receiver': (False, 'missing_authority'),
                                    'task-ledger': (False, 'missing_authority:unit'),
                                    'task-authority': (False, 'missing_authority:unit')},
                    'prepared': {'offer': False, 'receiver': (False, 'not_admitted'),
                                 'task-ledger': (False, 'missing_authority:admission'),
                                 'task-authority': (False, 'missing_authority:admission')},
                    'admitted-without-priority': {'offer': False, 'receiver': (False, 'not_admitted'),
                                                  'task-ledger': (False, 'missing_authority:priority'),
                                                  'task-authority': (False, 'missing_authority:priority')},
                    'prioritized': {'offer': True, 'receiver': (True, 'claim'), 'task-ledger': (True, 'granted'),
                                    'task-authority': (True, 'claim')}}
                states = {label: item(stage[label]).get('state') for label in AC1_SET}
                check('priority/declared-set', [
                    ('the four kinds of work stand where they were driven, the prioritized one now active',
                     states == {'intake-only': 'RAW', 'prepared': 'PREPARED', 'admitted-without-priority': 'ADMITTED',
                                'prioritized': 'ACTIVE'}),
                    ('every kind was driven through every entry', set(table) == set(AC1_SET)
                     and all(set(row) == set(ENTRIES) for row in table.values())),
                    ('only prioritized work is offered or claimed, at every entry', table == expected),
                    ('the prioritized item was prioritized by its owner before its first claim',
                     (item(stage['prioritized']).get('priority') or {}).get('ruling') == 'approve'
                     and [h.get('target') for h in item(stage['prioritized']).get('history') or []][-1] == 'PRIORITIZED')])

                adm = 'admitted-without-priority'
                spec3, task3 = 'VELDO-9783', 'TASK-78-3'
                selection3 = gate.decide('selection', spec3)
                stations3 = {s: gate.decide(s, spec3).get('refusals') or [] for s in FR.EL.FLOOR_STATIONS}
                cycle3 = assign(spec3)
                ledger_record = CLF.holder(task3, root=str(ledger))
                check('priority/missing-priority', [
                    ('the admitted item has its owner\'s admission and no priority',
                     item(stage[adm]).get('state') == 'ADMITTED' and item(stage[adm]).get('admission', {}).get('ruling') == 'approve'
                     and item(stage[adm]).get('priority') is None),
                    ('its units are admitted by record and still PLANNED',
                     data_of('admission:' + spec3).get('state') == 'accepted' and data_of(spec3).get('state') == 'PLANNED'
                     and data_of(task3).get('state') == 'PLANNED'),
                    ('the Gate\'s selection refuses it for missing priority, so the frontier does not offer it',
                     selection3.get('eligible') is False and selection3.get('refusals') == ['missing_authority:priority']
                     and not table[adm]['offer']),
                    ('every Gate station (plan run-check and the cycle\'s assignment step included) names its missing priority',
                     len(stations3) == 7 and all('missing_authority:priority' in r for r in stations3.values())),
                    ('the Gate refuses it at claim and at direct execution for missing priority alone',
                     stations3.get('claim') == ['missing_authority:priority']
                     and stations3.get('direct_execution') == ['missing_authority:priority']),
                    ('the VELDO-0132 cycle\'s assignment step refuses it for missing priority, and assigns prioritized work',
                     isinstance(cycle3, dict) and cycle3.get('state') == 'refused'
                     and cycle3.get('refusal') == 'missing_authority:priority'
                     and isinstance(cycle_prioritized, dict) and cycle_prioritized.get('state') == 'waiting'),
                    ('the direct task claim is refused for missing priority, and the ledger was never asked',
                     table[adm]['task-ledger'] == (False, 'missing_authority:priority') and ledger_record is None),
                    ('the task claim through the authority is refused for missing priority',
                     table[adm]['task-authority'] == (False, 'missing_authority:priority')),
                    ('the claim receiver refuses it', table[adm]['receiver'] == (False, 'not_admitted')),
                    ('the backlog names the reason for both units',
                     executable(spec3) == ['missing_authority:priority'] and executable(task3) == ['missing_authority:priority'])])

                executable_units = [(eid, u) for eid, u in of_kind('execution_unit')
                                    if u.get('state') not in ('PLANNED', 'CANCELED', 'COMPLETED')]
                claimed = sorted(c.get('unit_id') for _e, c in of_kind('claim') if c.get('state') == 'owned')

                def covered(eid, u):
                    owner_item = item(u.get('backlog_item_uuid'))
                    return (owner_item.get('state') in ('PRIORITIZED', 'ACTIVE')
                            and (owner_item.get('admission') or {}).get('ruling') == 'approve'
                            and eid in (owner_item.get('priority') or {}).get('units', [])
                            and (owner_item.get('priority') or {}).get('ruling') == 'approve'
                            and data_of('admission:' + eid).get('state') == 'accepted')
                check('priority/store-inspection', [
                    ('the store holds executable units', len(executable_units) == 2),
                    ('every executable unit has its item\'s accepted admission and priority',
                     all(covered(eid, u) for eid, u in executable_units)),
                    ('the only claims are of prioritized units', claimed == ['TASK-78-4', 'VELDO-9784']),
                    ('intake-only work has no unit and prepared work no admission',
                     entity('VELDO-9781') is None and entity('admission:VELDO-9782') is None
                     and data_of('VELDO-9782').get('state') == 'PLANNED')])

                # The owner's answer is the only way in: another touchpoint, another person, another brief,
                # an item not yet admitted, a second use of one answer.
                target3 = CB.decision_target(item(stage[adm])) if CB is not None else placeholder(stage[adm])
                rid_wrong_tp, _ = decide(stage[adm], 'admission', 'PRI-78-tp', target=target3,
                                         brief=CB.priority_brief(item(stage[adm])) if CB is not None else 'x')
                wrong_tp = bop('pm', 'prioritize', stage[adm], request=rid_wrong_tp)
                rid_zed, settled_zed = decide(stage[adm], 'priority', 'PRI-78-zed', owner='zed', proposal={'rank': 1})
                by_zed = bop('pm', 'prioritize', stage[adm], request=rid_zed)
                rid_brief, _ = decide(stage[adm], 'priority', 'PRI-78-brief', brief='Prioritize something harmless.')
                wrong_brief = bop('pm', 'prioritize', stage[adm], request=rid_brief)
                rid_early, _ = decide(stage['prepared'], 'priority', 'PRI-78-early')
                early = bop('pm', 'prioritize', stage['prepared'], request=rid_early)
                reused = bop('pm', 'admit', stage['prioritized'], request=I.assignment_id(REPO, 'ADM-78-4'))
                check('priority/owner-decision', [
                    ('an admission answer does not prioritize', wrong_tp.get('reason') == 'invalid_input:request'),
                    ('another project_owner member\'s settled answer does not prioritize',
                     settled_zed.get('outcome') == 'settled' and by_zed.get('reason') == 'not_owner'),
                    ('an answer to another brief does not prioritize', wrong_brief.get('reason') == 'stale_subject:brief'),
                    ('prepared work is not prioritized', early.get('reason') == 'invalid_transition:PREPARED->PRIORITIZED'),
                    ('an applied admission is not applied again', str(reused.get('reason')).startswith('invalid_transition')),
                    ('the admitted item is unchanged', item(stage[adm]).get('state') == 'ADMITTED'
                     and data_of(spec3).get('state') == 'PLANNED')])

                raw_again, _ = take('intake')
                objective_owned = attempt(lambda: fixture(features['returned'], 'backlog_item', {'state': 'PRIORITIZED'}))
                auto = bsend('pm', 'take', feature=features['returned'], work_class='STANDING_MAINTENANCE')
                not_feature = bsend('pm', 'take', feature=o1, work_class='PRODUCT_CHANGE')
                check('lifecycle/foreign-sources', [
                    ('a feature is taken into the backlog once', raw_again.get('reason') == 'already_exists'),
                    ('the feature record stays VELDO-0077\'s, RAW', data_of(features['intake']).get('state') == 'RAW'
                     and objective_owned == ('error', 'StoreRefused')),
                    ('policy-admitted work classes are not taken in this release',
                     auto.get('reason') == 'unsupported_work_class:STANDING_MAINTENANCE'),
                    ('only a feature is taken', not_feature.get('reason') == 'no_such_feature'),
                    ('the intake-only item carries no admission and no priority',
                     took['intake-only'].get('ok') and item(stage['intake-only']).get('admission') is None
                     and item(stage['intake-only']).get('priority') is None)])

            # AC2: the first claim activates the item; it follows only its approved decomposition.
            with region('activation/first-claim', 'activation/decomposition-growth'):
                U1, U2, U3, U4 = 'VELDO-9785', 'VELDO-9786', 'VELDO-9789', 'TASK-78-grow'
                _t, M = take('main')
                bop('pm', 'prepare', M, units=[unit_entry(U1, produces='out/VELDO-9785.txt'), unit_entry(U2)])
                bop('pm', 'request_grooming', M)
                admit(M, 'ADM-78-M')
                rid_pm, settled_pm, applied_pm = prioritize(M, 'PRI-78-M')
                before = item(M)
                first = rclaim('builder', U1)
                second = rclaim('builder-b', U1)
                stranger = rclaim('builder', 'VELDO-9790')
                claim1 = data_of(claims.claim_id(REPO, U1))
                check('activation/first-claim', [
                    ('the owner prioritized the approved decomposition',
                     applied_pm.get('ok') and before.get('state') == 'PRIORITIZED'
                     and (before.get('priority') or {}).get('units') == [U1, U2]
                     and (before.get('priority') or {}).get('rank') == 1),
                    ('the first claim is granted and activates the item',
                     first.get('ok') and item(M).get('state') == 'ACTIVE'),
                    ('the claim, the unit and the item agree on the owner',
                     claim1.get('holder') == 'builder' and claim1.get('generation') == 1 and claim1.get('state') == 'owned'
                     and data_of(U1).get('state') == 'CLAIMED' and claim1.get('backlog_item_uuid') == M),
                    ('the other approved unit is ready and unclaimed', data_of(U2).get('state') == 'READY'
                     and entity(claims.claim_id(REPO, U2)) is None),
                    ('a second holder is refused', second.get('reason') == 'claimed'),
                    ('a unit outside the decomposition does not exist to claim',
                     stranger.get('reason') == 'missing_authority' and entity('VELDO-9790') is None)])

                grew = bop('pm', 'append', M, unit=unit_entry(U3))
                rid_stale, settled_stale = decide(M, 'priority', 'PRI-78-stale', proposal={'rank': 2})
                grew2 = bop('pm', 'append', M, unit=unit_entry(U4, produces='out/TASK-78-grow.md'))
                appended = {u: data_of(u).get('state') for u in (U3, U4)}
                named = {u: executable(u) for u in (U3, U4)}
                refused3 = rclaim('builder', U3)
                refused4 = task_claim(U4, root=Authority('builder'))
                growth_claim = gate.decide('claim', U4)
                offered_growth = offers()
                continuing = rclaim('builder-b', U2)
                stale = bop('pm', 'prioritize', M, request=rid_stale)
                again = bop('pm', 'prioritize', M, request=rid_pm)
                between = item(M)
                rid_fresh, settled_fresh, fresh = prioritize(M, 'PRI-78-M3')
                readied = {u: (data_of(u).get('state'), data_of(u).get('admitted_revision')) for u in (U3, U4)}
                after3 = rclaim('builder', U3)
                after4 = task_claim(U4)
                check('activation/decomposition-growth', [
                    ('each append is a new decomposition revision of the active item',
                     grew.get('ok') and grew2.get('ok') and between.get('decomposition_revision') == 3
                     and between.get('state') == 'ACTIVE'),
                    ('an appended unit is PLANNED, not executable', appended == {U3: 'PLANNED', U4: 'PLANNED'}
                     and named == {U3: ['missing_authority:priority'], U4: ['missing_authority:priority']}),
                    ('the claim receiver refuses the appended unit', refused3.get('reason') == 'not_admitted'),
                    ('the task claim refuses the appended unit, not admitted and not prioritized at the Gate',
                     refused4 == (False, 'missing_authority:admission')
                     and 'missing_authority:priority' in (growth_claim.get('refusals') or [])),
                    ('the frontier does not offer it', isinstance(offered_growth, list) and U3 not in offered_growth),
                    ('an approved unit continues meanwhile', continuing.get('ok') and data_of(U2).get('state') == 'CLAIMED'),
                    ('the earlier prioritization does not cover the appended units',
                     again.get('reason') == 'already_applied' and (between.get('priority') or {}).get('units') == [U1, U2]),
                    ('an answer to an earlier revision is refused', settled_stale.get('outcome') == 'settled'
                     and stale.get('reason') == 'stale_subject:binding'),
                    ('the fresh prioritization of the current revision makes them executable',
                     fresh.get('ok') and readied == {U3: ('READY', 3), U4: ('READY', 3)}
                     and (item(M).get('priority') or {}).get('units') == [U1, U2, U3, U4]),
                    ('then they are claimed', after3.get('ok') and after4 == (True, 'granted'))])

            # AC3: a clean blocked phase resumes only on its settled binding; DONE needs accepted outcomes.
            with region('blocked/resume-binding', 'done/missing-outcome', 'done/authorized-alternative',
                        'done/accepted-outcomes', 'lifecycle/regular-path'):
                phase, why = 'review of VELDO-9786', 'the owner must choose the payment provider'
                blocked = bop('pm', 'block', M, phase=phase, reason=why)
                held = item(M)
                blockers = [b for _e, b in of_kind('blocker') if b.get('backlog_item_uuid') == M]
                during_claim = task_claim(U4, root=Authority('builder'))
                during_gate = gate.decide('selection', U1)
                no_request = bop('pm', 'resume', M)
                other_subject, _ = decide(M, 'decision_disposition', 'RES-78-unit',
                                          target=CB.unit_target(dict(data_of(U1), uuid=U1)) if CB is not None else placeholder(M),
                                          brief='Decide the unit.')
                by_other = bop('pm', 'resume', M, request=other_subject)
                forged = dict(CB.block_target(held), block='block-9') if CB is not None and held else placeholder(M)
                other_block, _ = decide(M, 'decision_disposition', 'RES-78-forged', target=forged, brief='Resume.')
                by_forged = bop('pm', 'resume', M, request=other_block)
                target_block = CB.block_target(held) if CB is not None and held else placeholder(M)
                resume_text = shown('resume_brief', held, default='Resume %s after: %s' % (phase, why)) if held else 'x'
                other_brief, _ = decide(M, 'decision_disposition', 'RES-78-brief', target=target_block,
                                        brief='Resume %s whatever stopped it.' % phase)
                by_other_brief = bop('pm', 'resume', M, request=other_brief)
                rejected_block, _ = decide(M, 'decision_disposition', 'RES-78-no', choice='reject', target=target_block,
                                           brief=resume_text)
                by_reject = bop('pm', 'resume', M, request=rejected_block)
                still = item(M).get('state')
                resolved, settled_res = decide(M, 'decision_disposition', 'RES-78-yes', target=target_block,
                                               brief=resume_text)
                resumed = bop('pm', 'resume', M, request=resolved)
                last = (item(M).get('history') or [{}])[-1]
                cleared = [b for _e, b in of_kind('blocker') if b.get('backlog_item_uuid') == M]
                after_gate = gate.decide('selection', U1)
                after_claim = task_claim(U4, root=Authority('builder'))
                check('blocked/resume-binding', [
                    ('the block records the interrupted phase and its reason',
                     blocked.get('ok') and held.get('state') == 'BLOCKED'
                     and (held.get('blocks') or [{}])[-1].get('phase') == phase
                     and (held.get('blocks') or [{}])[-1].get('reason') == why),
                    ('every open unit is blocked at the Gate and at the claim',
                     len(blockers) == 4 and not during_gate.get('eligible')
                     and any(str(r).startswith('blocked:') for r in during_gate.get('refusals', []))
                     and during_claim == (False, 'blocked:backlog')),
                    ('no settled answer does not resume', no_request.get('reason') == 'missing_evidence:settlement'),
                    ('an answer about another subject does not resume', by_other.get('reason') == 'invalid_input:request'),
                    ('an answer bound to another block does not resume', by_forged.get('reason') == 'stale_subject:binding'),
                    ('an answer to this block shown another brief does not resume',
                     by_other_brief.get('reason') == 'stale_subject:brief' and resume_text != 'x'
                     and phase in resume_text and why in resume_text),
                    ('the owner\'s refusal keeps it blocked', by_reject.get('reason') == 'not_approved:reject'
                     and still == 'BLOCKED'),
                    ('the owner\'s settled resolution resumes exactly that phase',
                     settled_res.get('outcome') == 'settled' and resumed.get('ok') and item(M).get('state') == 'ACTIVE'
                     and last.get('resumed_phase') == phase and last.get('request_id') == resolved),
                    ('its blockers are cleared and the work continues',
                     len(cleared) == 4 and all(b.get('cleared') for b in cleared) and after_gate.get('eligible')
                     and after_claim == (True, 'claim'))])

                # DONE: path-only output, a canceled attempt, a missing receipt, an incomplete receipt.
                (work / 'out' / 'VELDO-9785.txt').write_text('built\n')
                (work / 'out' / 'TASK-78-grow.md').write_text('reviewed\n')
                outputs = service.outputs(M) if service is not None else {}
                path_only = bop('pm', 'complete', M)
                task_done_path = concluded(U4)
                task_done_file = concluded(U4, with_gate=False)
                fixture('attempt:%s:1' % U1, 'attempt', {'unit_uuid': U1, 'state': 'CANCELED', 'attempt': 1})
                canceled = bop('pm', 'complete', M)
                for u in (U1, U2, U3):
                    receipt(u, 1)
                one_missing = bop('pm', 'complete', M)
                receipt(U4, 1, landing={'replication_receipt': None})
                receipt(U4, 2, n=1)
                incomplete = bop('pm', 'complete', M)
                reader_agrees = [gate.landed(u) for u in (U1, U2, U3, U4)]
                check('done/missing-outcome', [
                    ('the declared outputs exist and are reported', outputs == {U1: True, U2: False, U3: False, U4: True}),
                    ('a path-only output is not DONE', path_only.get('reason') == 'missing_outcome:' + U1),
                    ('the task with its product on disk is not concluded without an accepted outcome',
                     task_done_path is False and task_done_file is True),
                    ('a canceled attempt is not an outcome', canceled.get('reason') == 'missing_outcome:' + U1),
                    ('a missing required receipt is not DONE', one_missing.get('reason') == 'missing_outcome:' + U4),
                    ('an incomplete landing receipt or one for another revision is not DONE',
                     incomplete.get('reason') == 'missing_outcome:' + U4),
                    ('the one completion reader agrees', reader_agrees == [True, True, True, False]),
                    ('the item is still ACTIVE', item(M).get('state') == 'ACTIVE'),
                    ('the declared set was driven', len(AC3_SET) == 5)])

                unsettled = bop('pm', 'dispose_unit', M, unit=U4)
                u4 = dict(data_of(U4), uuid=U4)
                target_u4 = CB.unit_target(u4) if CB is not None and u4.get('revision') else placeholder(U4)
                alt_text = shown('alternative_brief', u4, default='Close %s without a landing.' % U4)
                rid_zed4, _ = decide(M, 'decision_disposition', 'ALT-78-zed', owner='zed', target=target_u4,
                                     brief=alt_text, proposal={'outcome': 'not_required'})
                by_zed4 = bop('pm', 'dispose_unit', M, unit=U4, request=rid_zed4)
                rid_odd, _ = decide(M, 'decision_disposition', 'ALT-78-odd', target=target_u4,
                                    brief=alt_text, proposal={'outcome': 'rewrite'})
                odd = bop('pm', 'dispose_unit', M, unit=U4, request=rid_odd)
                rid_alt_brief, _ = decide(M, 'decision_disposition', 'ALT-78-brief', target=target_u4,
                                          brief='Close %s.' % U4, proposal={'outcome': 'not_required'})
                alt_brief = bop('pm', 'dispose_unit', M, unit=U4, request=rid_alt_brief)
                rid_alt, settled_alt = decide(M, 'decision_disposition', 'ALT-78-yes', target=target_u4,
                                              brief=alt_text, proposal={'outcome': 'not_required'})
                alt = bop('pm', 'dispose_unit', M, unit=U4, request=rid_alt)
                check('done/authorized-alternative', [
                    ('a disposal without a settled answer is refused', unsettled.get('reason') == 'missing_evidence:settlement'),
                    ('another member\'s settled answer does not authorize it', by_zed4.get('reason') == 'not_owner'),
                    ('an outcome this release does not name is refused', odd.get('reason') == 'unsupported_outcome:rewrite'),
                    ('an answer shown another brief does not authorize it', alt_brief.get('reason') == 'stale_subject:brief'
                     and U4 in alt_text and 'not required' in alt_text),
                    ('the owner\'s settled answer authorizes the alternative outcome',
                     settled_alt.get('outcome') == 'settled' and alt.get('ok') and data_of(U4).get('state') == 'CANCELED'
                     and (data_of(U4).get('alternative_outcome') or {}).get('request_id') == rid_alt)])

                done = bop('pm', 'complete', M)
                final = item(M)
                outcomes = (final.get('completion') or {}).get('outcomes') or {}
                check('done/accepted-outcomes', [
                    ('complete receipts and the authorized alternative make it DONE', done.get('ok') and final.get('state') == 'DONE'),
                    ('each unit\'s outcome is recorded by its receipt or its authorization',
                     sorted(outcomes) == sorted([U1, U2, U3, U4])
                     and all(outcomes[u].get('receipt_id') == 'receipt:revision_landed:%s:1:0' % u for u in (U1, U2, U3))
                     and (outcomes[U4].get('alternative_outcome') or {}).get('request_id') == rid_alt),
                    ('the task is concluded from its accepted outcome', concluded(U4) is True),
                    ('DONE is terminal', str(bop('pm', 'block', M, phase='again', reason='again').get('reason')).startswith(
                        'invalid_transition'))])

                # The regular path, with the reject, return and cancel branches.
                _r, R = take('rejected')
                bop('pm', 'prepare', R, units=[unit_entry('VELDO-9787')])
                bop('pm', 'request_grooming', R)
                _rr, _rs, rejected = admit(R, 'ADM-78-R', choice='reject')
                _q, Q = take('returned')
                bop('pm', 'prepare', Q, units=[unit_entry('VELDO-9788')])
                bop('pm', 'request_grooming', Q)
                _qr, _qs, returned = admit(Q, 'ADM-78-Q1', choice='return_for_elaboration')
                back = item(Q).get('state')
                bop('pm', 'request_grooming', Q)
                _qr2, _qs2, readmitted = admit(Q, 'ADM-78-Q2')
                zed_cancel = bop('zed', 'cancel', Q, reason='not now')
                olga_cancel = bop('olga', 'cancel', Q, reason='superseded by the main item')
                path = [(h.get('source'), h.get('target')) for h in final.get('history') or [] if h.get('source') != h.get('target')]
                check('lifecycle/regular-path', [
                    ('the main item walked the regular path to DONE', path == [
                        (None, 'RAW'), ('RAW', 'PREPARED'), ('PREPARED', 'AWAITING_GROOMING'), ('AWAITING_GROOMING', 'ADMITTED'),
                        ('ADMITTED', 'PRIORITIZED'), ('ACTIVE', 'BLOCKED'), ('BLOCKED', 'ACTIVE'), ('ACTIVE', 'DONE')]),
                    ('a rejected item is REJECTED with its units canceled', rejected.get('ok')
                     and item(R).get('state') == 'REJECTED' and data_of('VELDO-9787').get('state') == 'CANCELED'),
                    ('a returned item goes back to PREPARED and is groomed again',
                     returned.get('ok') and back == 'PREPARED' and readmitted.get('ok')),
                    ('only the project\'s owner cancels', zed_cancel.get('reason') == 'not_owner:project'),
                    ('the owner\'s cancel is terminal and cancels its units', olga_cancel.get('ok')
                     and item(Q).get('state') == 'CANCELED' and data_of('VELDO-9788').get('state') == 'CANCELED'
                     and data_of('admission:VELDO-9788').get('state') == 'accepted'
                     and executable('VELDO-9788') == ['missing_authority:backlog/CANCELED'])])

            # A unit a real VELDO-0133 close CANCELED while its item stayed ACTIVE: not an outcome until the owner
            # decides it counts; then the item can be DONE.
            with region('done/closed-unit'):
                N1, N2 = 'VELDO-9791', 'VELDO-9792'
                _c, C = take('closed')
                bop('pm', 'prepare', C, units=[unit_entry(N1), dict(unit_entry(N2), eligible_holders=['closer'])])
                bop('pm', 'request_grooming', C)
                admit(C, 'ADM-78-C')
                prioritize(C, 'PRI-78-C')
                rclaim('builder', N1)
                held_n2 = rclaim('closer', N2)

                def inbox_as(who, op, alias, **fields):
                    body = dict(ids, operation=op, alias=alias, principal=who, command_id=next_id('ic'),
                                nonce=next_id('in'), **fields)
                    return inbox.apply(signed(who, body))
                stop = inbox_as('closer', 'open', 'STOP-78-C', claim_generation=((held_n2.get('claim') or {}).get('generation')),
                                assignment=dict(kind='decision', owner='zed', scope=['proj-a'], deadline='2026-10-30T17:00:00Z',
                                                budget={'owner_minutes': 15}, brief='Pick the payment provider.',
                                                choices=['accept', 'reject'], unit_id=N2,
                                                subject={'kind': 'specification', 'ref': 'specs/%s.md' % N2,
                                                         'digest': 'sha256:' + '7' * 64}))
                declined = inbox_as('zed', 'decline', 'STOP-78-C', request_version=1)
                asked = [d for _e, d in of_kind('assignment') if d.get('kind') == 'disposition'
                         and (d.get('disposition_of') or {}).get('assignment_id') == stop.get('assignment_id')]
                q_alias = asked[0].get('alias') if asked else 'none'
                closed_by = inbox_as('zed', 'answer', q_alias, request_version=1, ruling='close')
                disposed = inbox_as('pm', 'dispose', q_alias, request_version=1)
                n2, c_state = data_of(N2), item(C).get('state')
                receipt(N1, 1)
                refused_done = bop('pm', 'complete', C)
                named = attempt(lambda: CB.outcome_problems(gate, N2))
                u_n2 = dict(n2, uuid=N2)
                rid_c, settled_c = decide(C, 'decision_disposition', 'ALT-78-C',
                                          target=CB.unit_target(u_n2) if CB is not None and n2.get('revision') else placeholder(N2),
                                          brief=shown('alternative_brief', u_n2, default='Close %s.' % N2),
                                          proposal={'outcome': 'not_required'})
                counted = bop('pm', 'dispose_unit', C, unit=N2, request=rid_c)
                after_n2 = data_of(N2)
                done_c = bop('pm', 'complete', C)
                check('done/closed-unit', [
                    ('the VELDO-0133 close canceled the unit on the decliner\'s answer and left its item ACTIVE',
                     stop.get('ok') and declined.get('ok') and closed_by.get('ok') and disposed.get('ruling') == 'close'
                     and n2.get('state') == 'CANCELED' and (n2.get('disposition') or {}).get('ruling') == 'close'
                     and (n2.get('disposition') or {}).get('principal') == 'zed' and n2.get('alternative_outcome') is None
                     and c_state == 'ACTIVE'),
                    ('DONE refuses the closed unit as a missing outcome', refused_done.get('reason') == 'missing_outcome:' + N2),
                    ('the backlog names the closed unit\'s missing outcome', named == ['missing_outcome:' + N2]),
                    ('the owner\'s settled answer counts the closed unit, which stays CANCELED with its close',
                     settled_c.get('outcome') == 'settled' and counted.get('ok') and after_n2.get('state') == 'CANCELED'
                     and (after_n2.get('alternative_outcome') or {}).get('request_id') == rid_c
                     and (after_n2.get('disposition') or {}).get('ruling') == 'close'),
                    ('then the item is DONE with that outcome', done_c.get('ok') and item(C).get('state') == 'DONE'
                     and ((((item(C).get('completion') or {}).get('outcomes') or {}).get(N2) or {}).get('alternative_outcome')
                          or {}).get('request_id') == rid_c)])

            with region('other-process'):
                child = base / 'reader.py'
                child.write_text(_V78_CHILD)
                out = subprocess.run([sys.executable, '-B', str(child), str(mods), str(db),
                                      json.dumps({'domain': DOMAIN, 'repository': REPO,
                                                  'items': [M, stage['admitted-without-priority']],
                                                  'units': ['VELDO-9783', U3, U4]})],
                                     capture_output=True, text=True, timeout=60)
                seen = json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else {}
                check('other-process', [
                    ('the other process read the store read-only', seen.get('read_only') is True),
                    ('it sees the DONE item and the admitted one',
                     seen.get('items', {}).get(M) == 'DONE'
                     and seen.get('items', {}).get(stage['admitted-without-priority']) == 'ADMITTED'),
                    ('it gets the same executable answers',
                     seen.get('executable', {}).get('VELDO-9783') == ['missing_authority:priority']
                     and seen.get('executable', {}).get(U3) == ['missing_authority:backlog/DONE']),
                    ('it gets the same outcome answers', seen.get('outcomes', {}).get(U4) == []
                     and seen.get('outcomes', {}).get('VELDO-9783') == ['missing_outcome:VELDO-9783'])])

            with region('observability'):
                metrics = service.metrics() if service is not None else {}
                observations = service.observations if service is not None else []
                refusals = [o for o in observations if o['outcome'] == 'refused']
                text = json.dumps(observations)
                check('observability', [
                    ('accepted and refused commands are counted',
                     metrics.get('accepted', 0) > 0 and metrics.get('refused', 0) == len(refusals) > 0),
                    ('every observation names its operation, item, command and the versions it accepted',
                     all(o.get('operation') and o.get('command_id') and o.get('domain_uuid') == DOMAIN
                         and isinstance(o.get('accepted_versions'), dict) for o in observations)
                     and all(o.get('accepted_versions') for o in observations if o['outcome'] == 'accepted')),
                    ('every refusal is named and classified, never as success',
                     all(o['refusal'] and o['taxonomy'] not in (None, 'unknown_outcome') for o in refusals)),
                    ('the pending work is exposed', (metrics.get('pending') or {}).get('awaiting_priority') == 1
                     and (metrics.get('pending') or {}).get('awaiting_grooming') == 1
                     and (metrics.get('pending') or {}).get('units_awaiting_priority') == 4),
                    ('observations carry no reason text or signature', why not in text and 'SSH SIGNATURE' not in text
                     and 'I have read' not in text)])
        finally:
            for server in servers:
                server.shutdown()
                server.server_close()
            for connection in connections:
                connection.close()
    if raised:
        print('  %sdetail: regions that raised: %s' % (PREFIX, raised))


# The other process: the installed store and backlog modules over a read-only connection.
_V78_CHILD = '''import importlib.util, json, sqlite3, sys
from pathlib import Path
organs, db, wanted = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
def load(name):
    s = importlib.util.spec_from_file_location('child_' + name, str(Path(organs) / (name + '.py')))
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
S = load('control_store'); CB = load('control_backlog'); EL = load('control_eligibility')
conn = S.open_store(db, mode='r')
reader = EL.Gate(S, conn, domain_uuid=wanted['domain'], repository_uuid=wanted['repository'])
try:
    conn.execute("CREATE TABLE probe (x)")
    read_only = False
except sqlite3.Error:
    read_only = True
out = {'read_only': read_only, 'items': {}, 'executable': {}, 'outcomes': {}}
for iid in wanted['items']:
    out['items'][iid] = (CB.read(conn, iid) or {}).get('state')
for uid in wanted['units']:
    out['executable'][uid] = CB.executable_problems(conn, uid)
    out['outcomes'][uid] = CB.outcome_problems(reader, uid)
conn.close()
print(json.dumps(out))
'''

_v78_started = __import__('time').monotonic()
_v78_suite()
print('VELDO-0078 suite seconds: %.3f' % (__import__('time').monotonic() - _v78_started))
