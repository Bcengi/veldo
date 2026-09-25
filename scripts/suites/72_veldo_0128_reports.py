"""VELDO-0128: Telegram progress and completion reports projected from committed journal events.

Run: python3 scripts/selftest.py --suite 72_veldo_0128_reports

Only shared ROOT and expect are consumed. The authority is real (scripts/suites/support/v73_authority.py):
SQLite store, OpenSSH signatures on every command and journal record, membership, the owner's chat
enrollment, the VELDO-0067 edge key and the protected signer process. The reports are made by the running
service's channel: control_service_channel.Channel, constructed from the 0600 VELDO-0073 ingress host
configuration file, qualified and activated by the owner's signed commands, and driven pass by pass with
Channel.tick, which runs the reporter; nothing here calls the reporter for the owner. Every Bot API
exchange goes to a loopback stand-in in the platform's documented shapes (the VELDO-0073 stand-in, with a
switch that answers sendMessage with the Bot API's own 403 error object), and a socket guard installed for
the whole suite refuses and counts every connection to anything but the loopback interface, so no row and
no mutant can reach Telegram, and no real token file is read.

THE SOURCES ARE WRITTEN BY THEIR REAL WRITERS. Work progress is the VELDO-0039 dispatch records the one
dispatch writer commits (control_dispatch.Dispatches: prepare with a complete contract binding a VELDO-0036
worker slot and, for a build, the VELDO-0031 claim; then the receiver's accept, run, exit, refuse and
unknown). The gate results are the gate observations LiveLoop.gate records with the VELDO-0050 proof
service (control_verification.observe_gate running a verifier in candidate mode over the real repository,
one green and one red), and the floor steps dispatch.py's FloorAuthority commits (accept_build over the
built commit, its accepted proof and its exited build dispatch; assign_review; record_review with the
reviewer's OpenSSH-signed receipt printed by its own exited review dispatch, one passing and one returning
the unit; handoff under the review policy). The grooming and admission waits are real VELDO-0064 inbox
requests; the stop is a real VELDO-0075 andon stop, raised, noticed and revised by the andon service. The
objective and the completion receipts are store fixtures written with the store's generic signed command,
as the VELDO-0051 and VELDO-0075 suites lay them: their services are proved by their own suites, and the
completion predicate this module relies on is VELDO-0051's own reader. Inputs the writers judge (units,
backlog items, the review policy, reservation ceilings) are fixtures too; no report source is.

Mutation workers replace the production copies named in PRODUCTION below, never assertions or fixtures.
Where the reworked module or its wiring is absent (the pre-rework tree, for the red record) every row
asserts its named interface and fails by its own assertions. The real-Telegram send is run once by the
lead with the owner through the running factory; it is reported PENDING here and never counted. No
private key byte, signature or token is printed or retained.
"""
import hashlib as _v128_hashlib
import http.server as _v128_http
import importlib.util as _v128_import
import json as _v128_json
from pathlib import Path as _v128_Path
import shutil as _v128_shutil
import socket as _v128_socket
import subprocess as _v128_sp
import tempfile as _v128_temp
import threading as _v128_threading
import time as _v128_time
import uuid as _v128_uuid

_V128_ROWS = ('install/assets', 'registry/declared-set', 'registry/delivery', 'registry/committed-sources',
              'content/running', 'content/awaiting-decision', 'content/gate-rejected', 'content/completed',
              'content/unknown-explicit', 'stop/no-second-notice', 'recipient/owner-chat-only',
              'recipient/substitution-refused', 'send/refusal-recorded', 'observability/named-refusals',
              'sources/real-writers', 'wiring/tick-reports', 'wiring/restart', 'wiring/stopped-edge')
# The spec's declared event universe (AC1), independent of the module's own registry.
_V128_EVENTS = ('objective_accepted', 'decision_awaiting', 'work_progress', 'gate_result', 'stop', 'completion')


def _v128_load(name, path):
    spec = _v128_import.spec_from_file_location(name, path)
    module = _v128_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v128_sha(data):
    return 'sha256:' + _v128_hashlib.sha256(data).hexdigest()


def _v128_checks(base):
    rows = {name: [] for name in _V128_ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    class section:
        """Criterion sections: an exception is recorded as a failure of each named row and the run goes on."""

        def __init__(self, *names):
            self.names = names

        def __enter__(self):
            return self

        def __exit__(self, kind, value, trace):
            if kind is not None:
                for name in self.names:
                    check(name, 'the section ran to its end (it raised %s: %s)' % (kind.__name__, str(value)[:200]), False)
            return True

    def attempt(fn, default=None):
        """A call whose failure under a mutant is observed by the row's own assertion, never raised."""
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - the row asserts on the default
            failures.append('%s: %s' % (type(exc).__name__, str(exc)[:160]))
            return default
    failures = []

    (IA, RD, RL, RC, CR, CA, CG, CC, CU, SN, RO, RS, SR, OB, SW, WT, WR, WS) = _V128_ROWS
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {'control_telegram_report.py': ROOT / ".veldo" / "control_telegram_report.py",
                  'control_service_channel.py': ROOT / ".veldo" / "control_service_channel.py"}
    scaffold_path = ROOT / ".veldo" / "init_scaffold.py"
    # The installed copy lives in a `.veldo` directory, as installed: every module finds its siblings there.
    organs = base / 'installed' / '.veldo'
    organs.mkdir(parents=True)
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v128_shutil.copyfile(source, organs / source.name)
    for name, source in PRODUCTION.items():
        target = organs / name
        if target.exists():
            target.unlink()
        if _v128_Path(source).is_file():
            _v128_shutil.copyfile(source, target)
    H = _v128_load('v128_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')

    with section(IA):
        scaffold = _v128_load('v128_scaffold', scaffold_path)
        rel = '.veldo/control_telegram_report.py'
        both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
        check(IA, rel + ' installed by the scaffold', rel in scaffold._FILES)
        check(IA, rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
        check(IA, rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
        channel_rel = '.veldo/control_service_channel.py'
        check(IA, channel_rel + ' engine copy identical, and installed by the scaffold',
              (ROOT / 'engine' / channel_rel).read_bytes() == (ROOT / channel_rel).read_bytes()
              and channel_rel in scaffold._FILES)
        if both and rel in scaffold._FILES:
            scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
        check(IA, rel + ' laid by the installer', (base / 'laid' / rel).is_file()
              and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes())

    TR = _v128_load('v128_report', organs / 'control_telegram_report.py') \
        if (organs / 'control_telegram_report.py').is_file() else None
    IN = _v128_load('v128_ingress', organs / 'control_channel_ingress.py')
    EV = _v128_load('v128_attribution', organs / 'control_channel_attribution.py')
    AND = _v128_load('v128_andon', organs / 'control_andon.py')
    EP = _v128_load('v128_events', organs / 'control_event_projection.py')
    D = _v128_load('v128_dispatch_records', organs / 'control_dispatch.py')
    RES = _v128_load('v128_reservations', organs / 'control_reservations.py')
    CP = _v128_load('v128_proof', organs / 'control_proof.py')
    GP = _v128_load('v128_git', organs / 'git_process.py')
    DSP = _v128_load('v128_floor', organs / 'dispatch.py')
    OBJ = _v128_load('v128_objective', organs / 'control_objective.py')
    ASG = _v128_load('v128_assignment', organs / 'control_assignment.py')
    CH = attempt(lambda: _v128_load('v128_channel', organs / 'control_service_channel.py'))

    # The socket guard: nothing but the loopback interface is reached, and every other attempt is counted.
    attempts = []
    real_connect = _v128_socket.create_connection

    def guarded(address, *args, **kwargs):
        if address[0] != '127.0.0.1':
            attempts.append(address[0])
            raise OSError('suite guard: no network beyond the loopback interface')
        return real_connect(address, *args, **kwargs)
    _v128_socket.create_connection = guarded

    # The VELDO-0073 stand-in, with a switch: while `refuse` is set, sendMessage is answered with the Bot
    # API's own error object (HTTP 403, ok false, error_code 403) and nothing is published.
    owner_user = {'id': 5580128, 'is_bot': False, 'first_name': 'Owner'}
    stranger = {'id': 5589928, 'is_bot': False, 'first_name': 'Stranger'}
    bot_user = {'id': 8000000128, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_report_bot'}
    api = {'tick': 0, 'bots': {'bot128': {'user': dict(bot_user), 'next': 9000, 'update_next': 730000000,
                                          'messages': {}, 'updates': []}},
           'chats': {}, 'calls': [], 'lock': _v128_threading.Lock(), 'refuse': False, 'refused': []}

    class Handler(H._BotApi):
        state = api

        def do_POST(self):
            if api['refuse'] and self.path.endswith('/sendMessage'):
                raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                api['calls'].append('sendMessage')
                api['refused'].append(_v128_json.loads(raw) if raw else {})
                return self._answer(403, {'ok': False, 'error_code': 403,
                                          'description': 'Forbidden: bot was blocked by the user'})
            return H._BotApi.do_POST(self)
    server = _v128_http.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    _v128_threading.Thread(target=server.serve_forever, daemon=True).start()
    url = 'http://127.0.0.1:%d' % server.server_address[1]
    chat = owner_user['id']
    api['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': 'Owner'}
    bot = api['bots']['bot128']
    A = H.build(base / 'authority', organs, chat, url, 'bot128')
    ids = A.ids
    repo = ids['repository_uuid']
    domain = ids['domain_uuid']
    channel = channel2 = None
    ing = None
    try:
        for who, kind in (('andon', 'service'), ('techlead', 'person'), ('runner', 'service'), ('receiver', 'service'),
                          ('floor-service', 'service'), ('proof-service', 'service'), ('builder', 'agent_run'),
                          ('reviewer', 'agent_run')):
            path = base / 'authority' / ('key-' + who)
            _v128_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v128-' + who, '-f', str(path)],
                         check=True, capture_output=True, timeout=10, stdin=_v128_sp.DEVNULL)
            A.keyfile[who] = path
            A.public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
            A.admin('steward', 'enroll_principal', {
                'principal': who, 'principal_type': kind, 'roles': ['technical_authority'] if who == 'techlead' else [],
                'public_key': A.public[who], 'independence_group': who,
                'scope': ['project-a'] if who in ('andon', 'techlead') else ['project-a', repo]}, enrollee=who)
        # Another person's own enrolled private chat: the substitution target.
        tech_chat = 5570128
        api['chats'][tech_chat] = {'id': tech_chat, 'type': 'private', 'first_name': 'Techlead'}
        A.fixture('channel-enrollment:telegram_chat:techlead', 'channel_enrollment',
                  dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='techlead',
                       chat_id=tech_chat, revoked_at=None))

        def entity(eid):
            row = A.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
            return None if row is None else {'kind': row[0], 'version': row[1], 'data': _v128_json.loads(row[2])}

        def head():
            return A.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        def journal():
            return {r[0]: (r[1], r[2], _v128_json.loads(r[3])) for r in
                    A.conn.execute('SELECT seq, command_id, record_digest, transition FROM journal ORDER BY seq')}

        def kept(record):
            """Whether a report's source is still the committed journal record and entity it names."""
            src = (record or {}).get('source') or {}
            row = journal().get(src.get('journal_seq'))
            entry = (row[2] if row else {}).get(src.get('entity_id')) or {}
            return bool(row) and row[0] == src.get('command_id') and row[1] == src.get('record_digest') \
                and bool(entry) and entry.get('digest') == src.get('entity_digest')

        def others():
            """Every entity that is not a reporter record: what a report must never change."""
            return sorted((r[0], r[1], r[2]) for r in A.conn.execute(
                'SELECT id, version, digest FROM entities WHERE kind NOT IN (?, ?)', ('telegram_report', 'telegram_report_cursor')))

        def reports(owner='owner'):
            return [r for r in (_v128_json.loads(d) for (d,) in A.conn.execute(
                "SELECT data FROM entities WHERE kind='telegram_report' ORDER BY id")) if r.get('owner') == owner]

        def cursor(owner='owner'):
            found = [_v128_json.loads(d) for (d,) in A.conn.execute(
                "SELECT data FROM entities WHERE kind='telegram_report_cursor'")]
            return [c.get('since') for c in found if c.get('owner') == owner]

        def in_chat(which):
            """The messages the bot published in `which` (a person's own messages to it are not sends)."""
            return sorted(mid for (c, mid), m in bot['messages'].items()
                          if c == which and (m.get('from') or {}).get('id') == bot_user['id'])

        def sends():
            return api['calls'].count('sendMessage')

        def message(mid, which=chat):
            return bot['messages'].get((which, mid)) or {}

        def fact(r):
            return next((line for line in (r.get('text') or '').split('\n') if line.startswith('Fact: ')), '')

        # ---- the running service's channel, qualified and activated by the owner ---------------------
        channel = attempt(lambda: CH.Channel(str(A.config_path)))
        ing = channel.ingress if channel is not None else IN.open_ingress(str(A.config_path))
        acts = ing.activations
        A.authorize(acts, 'qualify')
        rid0, first = A.open_request(ing, 'Q128')
        owner0 = H.deliver(api, 'bot128', owner_user, 'accept: the activation run qualifies',
                           reply_to=(first.get('message_ids') or [None])[-1])
        stranger0 = H.deliver(api, 'bot128', stranger, 'accept: I am not enrolled')
        ing.wake({'tick': 0})
        qid, qd, _record = acts.qualify(ing.gate, ing.presenter, ing.acquirer, ing.settlement, rid0,
                                        EV.evidence_id(bot_user['id'], owner0['update_id']),
                                        EV.evidence_id(bot_user['id'], stranger0['update_id']))
        A.authorize(acts, 'activate', qualification_id=qid, qualification_digest=qd)
        activated = (acts.current() or {}).get('state') == 'active'
        activated_at = head()
        andon = AND.Andon(ing, AND.service_signer('andon', str(A.keyfile['andon'])), scope='project-a')

        # ---- the real writers of the gate, the review floor and the dispatch records -----------------
        work = _v128_Path(A.config['workspace'])
        ACCOUNT = 'acct-128'
        CONFIG = {'tools': ['Read', 'Edit'], 'model': 'configured-model'}

        def git(*args):
            return GP.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                          identity=('Builder', 'builder@example.invalid')).stdout.strip()

        def serve(conn, command):
            row = conn.execute('SELECT kind, data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            return bool(row) and row[0] == 'membership' and _v128_json.loads(row[1]).get('principal_type') == 'service'
        reservations = RES.Reservations(A.S, A.conn, domain=domain, repository=repo, principal='runner', authorize=serve,
                                        signer='authority', sign=A.journal_sign)
        CEILING = dict(capacity=50, invocations=500, wall_seconds=50000)
        for scope, subject in (('account', ACCOUNT), ('project', 'project-a')):
            reservations.configure('policy/' + subject, scope, subject, CEILING, now=_v128_time.time())
        runner = D.Dispatches(A.S, A.conn, domain=domain, repository=repo, principal='runner', signer='authority',
                              sign=A.journal_sign)
        receiver = D.Dispatches(A.S, A.conn, domain=domain, repository=repo, principal='receiver', signer='authority',
                                sign=A.journal_sign)
        CLM = A.claims
        A.conn.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}
        proofs = CP.ProofService(A.S, A.conn, domain=domain, repository=repo, repo=str(work), principal='proof-service',
                                 signer='authority', sign=A.journal_sign)
        A.fixture(DSP.review_policy_id(repo), 'review_policy', {
            'schema': 'veldo.review_policy/v1', 'tiers': {'standard': 1}, 'source': {'path': 'policy.yaml', 'digest': _v128_sha(b'v128')}})
        floor = DSP.FloorAuthority(A.S, A.conn, domain=domain, repository=repo, repo=str(work),
                                   projections=str(base / 'projections'), principal='floor-service', signer='authority',
                                   sign=A.journal_sign)

        def unit(uid, state='READY'):
            A.fixture('backlog:' + uid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=repo))
            A.fixture(uid, 'execution_unit', dict(unit_id=uid, state=state, repository_uuid=repo, backlog_item_uuid='backlog:' + uid,
                                                  requirements=[], eligible_holders=['builder'], project='project-a',
                                                  scope_digest='sha256:scope-' + uid, revision=1, depends_on=[],
                                                  risk='standard', station_contract=None))
            reservations.configure('policy/' + uid, 'unit', uid, CEILING, now=_v128_time.time())
            return uid

        def claim_op(action, uid, generation=0):
            cid = CLM.claim_id(repo, uid)
            ids_ = [uid, 'backlog:' + uid, cid]
            A.S.execute(A.conn, dict(command_id=A.next_id('claim'), principal='builder', operation='claim_operation',
                                     nonce=A.next_id('claim-nonce'), artifact_digests=[],
                                     expected_versions={i: (entity(i) or {}).get('version', 0) for i in ids_},
                                     parameters=dict(action=action, unit_id=uid, backlog_item_uuid='backlog:' + uid,
                                                     claim_id=cid, holder='builder', generation=generation,
                                                     capabilities=[], repository_uuid=repo)), 'authority', A.journal_sign, 1)
            return (entity(cid) or {}).get('data', {}).get('generation')

        pids = [41280]

        def identity(principal=None):
            pids[0] += 1
            found = {'platform': 'linux', 'host': 'v128-host', 'boot_id': 'boot-v128', 'pid': pids[0],
                     'start': 'start-%d' % pids[0]}
            if principal:
                found['principal'] = principal
            return found

        def prepare(uid, station, payload, context, commit=None, claim=None):
            """A complete VELDO-0039 contract, as control_launch.Runner.prepare builds it, recorded by the runner."""
            did = 'dispatch/%s/%s' % (uid, _v128_uuid.uuid4().hex)
            reservations.reserve_worker('worker/' + did, did, ACCOUNT, 'project-a', uid, now=_v128_time.time())
            slot = RES.entity('worker', [domain, did])
            version, slot_digest = A.conn.execute('SELECT version, digest FROM entities WHERE id=?', (slot,)).fetchone()
            commit = commit or git('rev-parse', 'HEAD')
            decision = {'decision_id': 'decision/%s/%s' % (station, did), 'station': station, 'unit': uid,
                        'domain_uuid': domain, 'watermark': head(), 'inputs': {'unit': uid}}
            contract = {'schema': D.SCHEMA, 'dispatch_id': did, 'domain': domain, 'repository': repo, 'unit': uid,
                        'station': station, 'attempt': runner.attempts(uid, station) + 1,
                        'source': {'commit': commit, 'tree': git('rev-parse', commit + '^{tree}'), 'repository_uuid': repo},
                        'input': {'decision': decision, 'context': context, 'payload': payload,
                                  'payload_digest': D.digest(payload)},
                        'capability': {'adapter': 'engine-v128', 'configuration': CONFIG,
                                       'configuration_digest': D.digest(CONFIG)},
                        'reservation': {'entity': slot, 'version': version, 'digest': slot_digest, 'account': ACCOUNT,
                                        'project': 'project-a'},
                        'claim': claim, 'deadline': _v128_time.time() + 600, 'authority_generation': 1}
            runner.prepare(contract, now=_v128_time.time())
            return did, runner.record(did)['contract_digest']

        def terminated(output, returncode=0, signal=None, deadline_stop=False):
            return {'returncode': returncode, 'signal': signal, 'output_digest': _v128_sha(output),
                    'output_bytes': len(output), 'deadline_stop': deadline_stop}

        def launched(did, cdigest):
            process = identity()
            receiver.accept(did, cdigest, identity('receiver'), now=_v128_time.time())
            receiver.run(did, cdigest, process, now=_v128_time.time())
            return process

        green_dir, red_dir = base / 'verifier-green', base / 'verifier-red'
        for where, ok in ((green_dir, True), (red_dir, False)):
            (where / 'scripts').mkdir(parents=True)
            (where / 'scripts' / 'verify.sh').write_text('\n'.join([
                '#!/bin/bash', '# veldo-gate-interface: candidate-sink/v1', 'CHECK_unit="required:true"', 'ORDER="unit"',
                'candidate="$2"; sink="$4"', 'commit=$(git -C "$candidate" rev-parse HEAD)', 'echo "== unit"',
                ('echo "   unit: pass"; printf \'{"commit":"%s","status":"green"}\' "$commit" > "$sink/last_verify"; '
                 'printf \'{"type":"gate.passed","commit":"%s","producer":"verify.sh"}\\n\' "$commit" >> "$sink/events.jsonl"; '
                 'echo "GATE: GREEN ($commit)"; exit 0') if ok else
                'echo "   unit: FAIL"; echo "GATE: RED ($commit)"; exit 1', '']))

        def gate(installation):
            return DSP.EX.LiveLoop(root=str(work), proofs=proofs, installation=str(installation)).gate()

        def build(uid):
            """The build station: claim, dispatch, the builder's commits, the gate, then accept_build."""
            generation = claim_op('claim', uid)
            did, cdigest = prepare(uid, 'build', {'unit': uid}, {'holder': 'builder', 'generation': generation},
                                   claim={'entity': CLM.claim_id(repo, uid), 'holder': 'builder', 'generation': generation})
            process = launched(did, cdigest)
            source = work / 'src' / (uid.lower().replace('-', '_') + '.py')
            source.parent.mkdir(exist_ok=True)
            source.write_text('OK = True\n')
            git('add', '--', str(source.relative_to(work)))
            git('commit', '-q', '-m', 'Implement ' + uid)
            implementation = git('rev-parse', 'HEAD')
            manifest = {'schema': 'veldo.proof/v1', 'spec_id': uid, 'producer': 'builder', 'commit': implementation,
                        'criteria': [{'id': 'AC1', 'status': 'passed', 'evidence': [str(source.relative_to(work))]}],
                        'checks': [{'name': 'unit', 'status': 'passed'}], 'rollback': 'git revert'}
            (work / 'proof' / uid).mkdir(parents=True)
            (work / 'proof' / uid / 'manifest.json').write_text(_v128_json.dumps(manifest, indent=1, sort_keys=True) + '\n')
            git('add', '--', 'proof/' + uid)
            git('commit', '-q', '-m', 'Proof for ' + uid)
            tip = git('rev-parse', 'HEAD')
            printed = _v128_json.dumps({'commit': tip}).encode()
            receiver.exit(did, cdigest, process, terminated(printed), now=_v128_time.time())
            observed = gate(green_dir)
            floor.accept_build(uid, commit=tip, gate={'green': observed.get('green') is True, 'detail': observed.get('detail')},
                               holder='builder', generation=generation)
            claim_op('release', uid, generation)
            return {'dispatch': did, 'process': process, 'tip': tip, 'gate': observed, 'implementation': implementation}

        def review(uid, verdict):
            """The review station: the assignment, the reviewer's own dispatch printing its signed receipt,
            and record_review."""
            payload = floor.assign_review(uid, 'reviewer')
            tip = payload['source']['commit']
            did, cdigest = prepare(uid, 'review', payload, {'holder': 'builder', 'reviewer': 'reviewer'}, commit=tip)
            process = launched(did, cdigest)
            body = {'schema': 'veldo.review_receipt/v1', 'assignment': payload['assignment'], 'unit': uid,
                    'reviewer': 'reviewer', 'source': tip, 'proof': payload['proof']['digest'], 'verdict': verdict,
                    'findings': [] if verdict == 'pass' else [{'severity': 'blocking', 'text': 'the failure path is never driven'}]}
            signature = A.sign_as('reviewer', DSP.canonical(body), 'veldo-review')
            printed = _v128_json.dumps({'body': body, 'signature': signature}, sort_keys=True, separators=(',', ':'))
            receiver.exit(did, cdigest, process, terminated(printed.encode()), now=_v128_time.time())
            record = floor.record_review(uid, payload['assignment'], {'dispatch': did, 'output': printed}, return_to='ready')
            return {'dispatch': did, 'record': record, 'output_digest': _v128_sha(printed.encode())}

        def hexed(label):
            return _v128_hashlib.sha1(label.encode()).hexdigest()

        # ---- the event set, committed in the authority ---------------------------------------------
        # objective_accepted: proposed, then accepted by its settlement.
        oid = 'objective:%s:o128' % repo
        objective = dict(schema='veldo.objective/v1', uuid=oid, entity_type='objective', domain_uuid=domain,
                         repository_uuid=repo, project='project-a', state='PROPOSED', revision=1,
                         bound_digest='sha256:bound-o128', accepted_revision=None, acceptance=None)
        A.fixture(oid, 'objective', objective)
        A.fixture(oid, 'objective', dict(objective, state='ACCEPTED', accepted_revision=1, acceptance={
            'settlement_id': 'request-settlement:o128:1', 'receipt_id': 'settlement-receipt:o128:1', 'ruling': 'approve'}))
        # decision_awaiting: a real grooming request, framed and presented; and a real admission request the
        # presenter has not presented (its presentation is unavailable, said plainly).
        groom_id, groom_shown = A.open_request(ing, 'G128')
        adm_alias = 'A128'
        target = {'kind': 'backlog_item', 'ref': 'backlog:' + adm_alias, 'digest': 'sha256:' + hexed(adm_alias)}
        terms_body = dict(ids, operation='terms', terms=adm_alias, principal='pm', command_id=A.next_id('terms'),
                          nonce=A.next_id('terms-nonce'), touchpoint='admission', target=target, proposal=None,
                          required_roles=[], quorum=None)
        adm_subject = attempt(lambda: ing.settlement.terms(A.signed_command('pm', terms_body)).get('subject'))
        attempt(lambda: ing.inbox.apply(A.signed_command('pm', dict(ids, operation='open', alias=adm_alias, principal='pm',
                command_id=A.next_id('c'), nonce=A.next_id('n'), assignment=dict(
                    kind='decision', owner='owner', scope=['project-a'], deadline='2026-10-01T17:00:00Z',
                    budget={'owner_minutes': 15}, brief='Admit backlog item A128 to the project.',
                    choices=['accept', 'return_for_elaboration', 'reject'], subject=adm_subject)))))
        adm_id = A.assignment_id(adm_alias)
        # The build, gate and review floor, by the real writers: one unit passes review and is handed off,
        # one is returned by its review, and one change is refused by a red gate.
        (work / 'README').write_text('v128\n')
        git('add', '--', 'README')
        git('commit', '-q', '-m', 'v128 base')
        passing, returning = unit('U128-pass'), unit('U128-return')
        built = {uid: build(uid) for uid in (passing, returning)}
        reviewed = {passing: review(passing, 'pass'), returning: review(returning, 'fail')}
        handed = floor.handoff(passing)
        (work / 'src' / 'red.py').write_text('OK = False\n')
        git('add', '--', 'src/red.py')
        git('commit', '-q', '-m', 'A change the gate refuses')
        red_commit = git('rev-parse', 'HEAD')
        red = gate(red_dir)
        # Work progress that ends otherwise: a launch whose outcome is unknown, a worker ended by a signal at
        # its deadline, and a launch the receiver refused.
        lost, killed, refused_unit = unit('U128-lost'), unit('U128-killed'), unit('U128-refused')
        lost_did, lost_digest = prepare(lost, 'review', {'unit': lost}, {'reviewer': 'reviewer'})
        receiver.accept(lost_did, lost_digest, identity('receiver'), now=_v128_time.time())
        receiver.unknown(lost_did, lost_digest, 'launch_evidence_missing', now=_v128_time.time())
        killed_did, killed_digest = prepare(killed, 'review', {'unit': killed}, {'reviewer': 'reviewer'})
        killed_process = launched(killed_did, killed_digest)
        receiver.exit(killed_did, killed_digest, killed_process, terminated(b'', returncode=None, signal=9, deadline_stop=True),
                      now=_v128_time.time())
        refused_did, refused_digest = prepare(refused_unit, 'review', {'unit': refused_unit}, {'reviewer': 'reviewer'})
        runner.refuse(refused_did, refused_digest, 'receiver_unavailable', now=_v128_time.time())
        # stop: a real andon stop, noticed by the andon service, then revised (a new request version).
        unit('U128-stop', 'RUNNING')
        raise_body = dict(ids, operation='raise', principal='pm', command_id=A.next_id('raise'), nonce=A.next_id('rn'),
                          unit='U128-stop', station='build', reason='reason-v128: the build needs the owner',
                          resolving={'principal': 'owner', 'roles': ['project_owner']}, effect='clean')
        raised = attempt(lambda: andon.raise_stop(A.signed_command('pm', raise_body)), {})
        stop_id = raised.get('stop_id')
        stop_request = raised.get('request_id')
        notices_after_raise = len(andon.notices(stop_id)) if stop_id else 0
        revise_body = dict(ids, operation='revise', principal='pm', command_id=A.next_id('revise'),
                           nonce=A.next_id('revise-nonce'), stop_id=stop_id or 'none', reason='reason-v128: more')
        revised = attempt(lambda: andon.revise_stop(A.signed_command('pm', revise_body)), {})
        # completion: a confirmed landing of U128-land; a build-only attempt of U128-build; an unconfirmed
        # publication of U128-open. Only the first is a completion.
        land_did, open_did = 'dispatch/U128-land/land', 'dispatch/U128-open/land'
        old, cand, cand_open = hexed('trunk'), hexed('land'), hexed('open')

        def publication(did, uid, candidate, confirmed):
            A.fixture('effect:' + did, 'protected_effect', dict(
                kind='publication', dispatch_id=did, unit=uid, domain_uuid=domain, repository_uuid=repo,
                status='completed' if confirmed else 'unknown', completed=confirmed,
                destination={'destinations': [{'outcome': 'at-tip' if confirmed else 'unknown'}]},
                payload={'commit': candidate, 'old_tip': old}))

        def landed(uid, did, candidate, n=0):
            landing = {'implementation_commit': candidate, 'proof_digest': 'sha256:proof-' + uid,
                       'reviewed_source_digest': 'sha256:source-' + uid, 'old_remote_tip': old,
                       'candidate_commit': candidate, 'tested_tree': hexed('tree-' + uid),
                       'gate_invocation': 'verify/' + uid, 'gate_output_location': 'observations/' + uid,
                       'unit_id': uid, 'dispatch_id': did, 'replication_receipt': 'local-journal',
                       'remote_confirmation': {'remote': 'origin', 'ref': 'refs/heads/main', 'commit': candidate}}
            rid = 'receipt:revision_landed:%s:%d' % (uid, n)
            A.fixture(rid, 'completion_receipt', {
                'fact': 'revision_landed', 'subject': {'id': uid, 'revision': 1}, 'publication_receipt': landing,
                'remote_confirmation': landing['remote_confirmation'], 'replicated': 'local-journal',
                'spec_shipped_event': 'spec.shipped/%s/%s' % (uid, did)})
            return rid
        unit('U128-land', 'LANDING')
        publication(land_did, 'U128-land', cand, True)
        land_receipt = landed('U128-land', land_did, cand)
        unit('U128-build', 'VERIFYING')
        A.fixture('receipt:attempt_finished:U128-build:0', 'completion_receipt', dict(
            fact='attempt_finished', subject={'id': 'U128-build', 'revision': 1}, trusted_exit=True,
            accounting_observation='observation/U128-build', containment_empty=True))
        A.fixture('receipt:artifact_accepted:U128-build:0', 'completion_receipt', dict(
            fact='artifact_accepted', subject={'id': 'U128-build', 'revision': 1}, station='build',
            artifact_digests=['sha256:proof-U128-build'], acceptor='owner'))
        unit('U128-open', 'LANDING')
        publication(open_did, 'U128-open', cand_open, False)
        landed('U128-open', open_did, cand_open)
        committed_head = head()
        committed = journal()
        # VELDO-0051's own reader over the same store, as the independent completion oracle.
        db = A.conn.execute('PRAGMA database_list').fetchone()[2]
        shipped, judged = EP.Projection(A.S, db, domain=domain, repository=repo, root=_v128_Path(db).parent).derive(
            [(s, c, d, t, None) for s, (c, d, t) in sorted(committed.items())], 0)
        # Every dispatch record, by the suite's own reading of the store (never the reporter's).
        dispatch_ids = sorted({eid for s, (c, d, t) in committed.items() for eid, e in t.items()
                               if s > activated_at and e.get('kind') == 'dispatch'})
        observation_ids = sorted({eid for s, (c, d, t) in committed.items() for eid, e in t.items()
                                  if s > activated_at and e.get('kind') == 'gate_observation'})

        # ---- one pass of the running service's channel -------------------------------------------------
        before_tick = reports()
        entities_before = others()
        owner_before = in_chat(chat)
        sends_before = sends()
        gate_before = len(ing.gate.observations)
        summary1 = attempt(lambda: channel.tick(), {}) if channel is not None else {}
        tick_head = max((s for s, (c, d, t) in journal().items()
                         if not c.startswith('telegram_report_record:')), default=0)
        mine = reports()
        by_event = {}
        for r in mine:
            by_event.setdefault(r.get('event'), []).append(r)
        delivered_ids = [mid for mid in in_chat(chat) if mid not in owner_before]
        gated = [o for o in ing.gate.observations[gate_before:] if o.get('operation') == 'sendMessage']
        entities_after = others()
        since1 = cursor()

        def one(event, entity_id, text=None):
            found = [r for r in by_event.get(event, []) if (r.get('source') or {}).get('entity_id') == entity_id
                     and (text is None or text in r.get('text', ''))]
            return found[0] if len(found) == 1 else {}

        def delivered(r):
            """The stand-in's own stored message for a record, and whether it matches the record exactly."""
            m = message(r.get('message_id'))
            return (r.get('outcome') == 'sent' and bool(m) and m.get('text') == r.get('text')
                    and (m.get('chat') or {}).get('id') == chat and r.get('chat_id') == chat)

        floor_pass, floor_return = DSP.floor_id(repo, passing), DSP.floor_id(repo, returning)

        # AC1: the registry is the declared set.
        with section(RD):
            registry = getattr(TR, 'REGISTRY', ()) if TR is not None else ()
            names = tuple(r[0] for r in registry)
            check(RD, 'the registry names exactly the declared event set [%s]' % ', '.join(names),
                  sorted(names) == sorted(_V128_EVENTS) and len(names) == len(set(names)))
            check(RD, 'each registration has its handler on the reporter', TR is not None and all(
                callable(getattr(TR.Reporter, h, None)) for _n, _k, h in registry))
            check(RD, 'the production ingress is activated by the owner and the running service\'s channel runs on it',
                  activated and channel is not None)

        # The sources are the real writers' records, and each report reads their own fields.
        with section(SW):
            kinds = {n: tuple(k or ()) for n, k, _h in (getattr(TR, 'REGISTRY', ()) if TR is not None else ())}
            check(SW, 'each registration listens to the kinds its real writer commits [%s]' % kinds,
                  kinds.get('work_progress') == (D.RECORD_KIND,)
                  and sorted(kinds.get('gate_result', ())) == sorted((CP.OBSERVATION_KIND, DSP.FLOOR_KIND))
                  and kinds.get('objective_accepted') == (OBJ.KIND,) and kinds.get('decision_awaiting') == (ASG.ENTITY_KIND,)
                  and kinds.get('stop') == (AND.STOP_KIND,) and kinds.get('completion') == ())
            writers = {'work_progress': 'dispatch/', 'gate_result': ('proof/observe/', 'floor/')}
            ok = True
            for event, prefix in writers.items():
                for r in by_event.get(event, []):
                    ok = ok and (r.get('source') or {}).get('command_id', '').startswith(prefix)
            check(SW, 'every progress and gate report\'s source was committed by the dispatch, proof or floor writer',
                  bool(by_event.get('work_progress')) and bool(by_event.get('gate_result')) and ok)
            b = built.get(passing) or {}
            build_record = (entity('dispatch:' + b.get('dispatch', '')) or {}).get('data') or {}
            accepted = one('work_progress', 'dispatch:' + b.get('dispatch', ''), 'accepted by')
            exited = one('work_progress', 'dispatch:' + b.get('dispatch', ''), 'exited')
            check(SW, 'the accepted report names the receiver the dispatch record holds [%s]' % fact(accepted),
                  fact(accepted) == 'Fact: dispatch %s of unit %s at station build, attempt 1, accepted by the receiver %s'
                  % (b.get('dispatch'), passing, (build_record.get('receiver') or {}).get('principal'))
                  and (build_record.get('receiver') or {}).get('principal') == 'receiver')
            check(SW, 'the exited report states the return code the termination records [%s]' % fact(exited),
                  fact(exited) == 'Fact: dispatch %s of unit %s at station build, attempt 1, exited with return code 0'
                  % (b.get('dispatch'), passing) and (build_record.get('termination') or {}).get('returncode') == 0)
            check(SW, 'no report names a worker: the dispatch contract has none',
                  bool(mine) and not any('worker' in fact(r) for r in mine)
                  and 'worker' not in (build_record.get('contract') or {}))
            rv = (reviewed.get(returning) or {}).get('record') or {}
            back = one('gate_result', floor_return, 'Review rejected')
            last = (rv.get('reviews') or [{}])[-1]
            check(SW, 'the review report names the stored reviewer, verdict, review dispatch and findings',
                  delivered(back) and last.get('reviewer') == 'reviewer' and last.get('verdict') == 'fail'
                  and 'review receipt printed by dispatch %s (output %s), blocking findings %s'
                  % (last.get('dispatch'), last.get('output_digest'), ', '.join(last.get('raised') or [])) in back.get('text', '')
                  and last.get('output_digest') == (reviewed.get(returning) or {}).get('output_digest'))

        # AC1: every enabled event committed produces its correlated report to the owner.
        with section(RL):
            expected_sources = {'objective_accepted': [oid], 'decision_awaiting': sorted([groom_id, adm_id]),
                                'work_progress': dispatch_ids,
                                'gate_result': sorted(observation_ids + [floor_pass, floor_return]),
                                'stop': [stop_id], 'completion': [land_receipt]}
            for event in _V128_EVENTS:
                got = sorted(set((r.get('source') or {}).get('entity_id') for r in by_event.get(event, [])))
                check(RL, '%s: a report for every committed source [%s]' % (event, got),
                      got == sorted(expected_sources[event]) and bool(got))
                check(RL, '%s: every report was sent, stored by the platform exactly as recorded, to the owner' % event,
                      bool(by_event.get(event)) and all(delivered(r) for r in by_event.get(event, [])))
            check(RL, 'the registry-to-delivery comparison: the delivered events are the declared set',
                  sorted(by_event) == sorted(_V128_EVENTS))
            check(RL, 'three gate observations: two green builds and the red change [%d]' % len(observation_ids),
                  len(observation_ids) == 3)
            correlated = all(
                r.get('domain_uuid') == domain and r.get('repository_uuid') == repo and 'run' in r and 'unit' in r
                and isinstance(r.get('source'), dict) and all(r['source'].get(k) for k in (
                    'journal_seq', 'command_id', 'record_digest', 'entity_id', 'entity_digest'))
                and ('Project: %s |' % (r.get('project') or 'unavailable')) in (r.get('text') or '')
                and ('Unit: %s | Run: %s' % (r.get('unit') or 'none', r.get('run') or 'none')) in (r.get('text') or '')
                and ('journal %s, command %s' % (r['source']['journal_seq'], r['source']['command_id'])) in r.get('text', '')
                for r in mine)
            check(RL, 'every report keeps project, unit, run and the source event identity, and shows them',
                  bool(mine) and correlated)
            check(RL, 'the project is the one the source record or its unit names',
                  bool(mine) and all(r.get('project') == 'project-a' for r in mine
                                     if (r.get('source') or {}).get('entity_kind') != 'gate_observation'
                                     and (r.get('source') or {}).get('entity_id') not in (groom_id, adm_id))
                  and all(r.get('project') is None for r in by_event.get('gate_result', [])
                          if (r.get('source') or {}).get('entity_kind') == 'gate_observation'))
            check(RL, 'the stop and the completion name their unit and run',
                  one('stop', stop_id).get('unit') == 'U128-stop' and one('stop', stop_id).get('run') == stop_id
                  and one('completion', land_receipt).get('unit') == 'U128-land'
                  and one('completion', land_receipt).get('run') == land_did)

        # AC1: a report exists only for a committed enabled event, once.
        with section(RC):
            real = True
            for r in mine:
                s = r.get('source') or {}
                row = committed.get(s.get('journal_seq'))
                entry = (row[2] if row else {}).get(s.get('entity_id')) or {}
                real = real and bool(row) and row[0] == s.get('command_id') and row[1] == s.get('record_digest') \
                    and entry.get('digest') == s.get('entity_digest') and activated_at < s.get('journal_seq', 0) <= committed_head
            check(RC, 'every report names a committed journal record and entity by digest, after the activation',
                  bool(mine) and real)
            b = built.get(passing) or {}
            progress = sorted(fact(r).split(', attempt 1, ')[-1].split(' ')[0] for r in by_event.get('work_progress', [])
                              if (r.get('source') or {}).get('entity_id') == 'dispatch:' + b.get('dispatch', ''))
            steps = sorted(r.get('text', '').split('\n')[0] for r in by_event.get('gate_result', [])
                           if (r.get('source') or {}).get('entity_id') == floor_pass)
            check(RC, 'no report for a prepared dispatch, the review assignment, the build-only receipts, the presentation '
                  'records, the revised stop or the andon\'s own request [%s | %s]' % (progress, steps),
                  bool(mine) and not any((r.get('source') or {}).get('entity_id') in (
                      'receipt:attempt_finished:U128-build:0', 'receipt:artifact_accepted:U128-build:0', stop_request, rid0)
                      or (r.get('source') or {}).get('entity_kind') in ('channel_presentation', 'andon_notice',
                                                                         'presentation_framing') for r in mine)
                  and len([r for r in mine if r.get('event') == 'stop']) == 1
                  and progress == ['accepted', 'exited', 'running']
                  and steps == ['Veldo: Build accepted for review', 'Veldo: Handed off to landing', 'Veldo: Review passed'])
            check(RC, 'one message per report: the owner\'s chat received exactly the sent reports',
                  bool(mine) and sorted(r.get('message_id') for r in mine) == sorted(delivered_ids)
                  and sends() - sends_before == len(mine) + (summary1 or {}).get('published', 0))
            sends_now = sends()
            again = attempt(lambda: channel.tick(), None) if channel is not None else None
            check(RC, 'a second pass reports nothing and sends nothing',
                  again is not None and again.get('reported') == [] and sends() == sends_now and len(reports()) == len(mine))
            written, foreign = set(), set()
            for seq, (cmd, _d, changes) in journal().items():
                if seq > committed_head and cmd.startswith('telegram_report_record:'):
                    written |= {v.get('kind') for v in changes.values()}
                elif seq > committed_head:
                    foreign |= {v.get('kind') for v in changes.values()} & {'telegram_report', 'telegram_report_cursor'}
            check(RC, 'the reporter writes only its own report and since records: no admission, settlement, stop or '
                  'completion [%s]' % sorted(written),
                  written == {'telegram_report', 'telegram_report_cursor'} and not foreign
                  and entities_before == entities_after and before_tick == [])

        # AC2: running, from the committed dispatch record.
        with section(CR):
            b = built.get(passing) or {}
            r = one('work_progress', 'dispatch:' + b.get('dispatch', ''), 'running as')
            stored = entity('dispatch:' + b.get('dispatch', '')) or {}
            check(CR, 'the running report\'s delivered bytes are the recorded text',
                  bool(r) and message(r.get('message_id')).get('text') == r.get('text'))
            check(CR, 'it states the committed fact: dispatch, unit, station, attempt and process, from its journal record '
                  '[%s]' % fact(r),
                  bool(r) and committed.get(r['source']['journal_seq'])[2]['dispatch:' + b['dispatch']]['data']['state'] == 'running'
                  and fact(r) == 'Fact: dispatch %s of unit %s at station build, attempt 1, running as process %s on v128-host'
                  % (b['dispatch'], passing, (b.get('process') or {}).get('pid'))
                  and r.get('unit') == passing and r.get('run') == b['dispatch']
                  and stored.get('data', {}).get('state') == 'exited')
            check(CR, 'and its next action', bool(r) and 'Next: no action; the worker is running.' in r['text'])

        # AC2: awaiting decision links to its current presentation; none published is said plainly.
        with section(CA):
            g, a = one('decision_awaiting', groom_id), one('decision_awaiting', adm_id)
            current = ing.presenter.current(groom_id) or {}
            pmid = (current.get('message_ids') or [None])[-1]
            gm = message(g.get('message_id'))
            check(CA, 'the grooming wait names its touchpoint and the request it waits on',
                  delivered(g) and 'Veldo: Decision waiting: grooming' in g['text']
                  and 'request %s version 1 offered to owner by pm' % groom_id in g['text'])
            check(CA, 'it is sent as a reply to the request\'s current presentation and names it [%s %s]'
                  % (g.get('reply_to'), pmid), pmid is not None and g.get('reply_to') == pmid
                  and (gm.get('reply_to_message') or {}).get('message_id') == pmid
                  and ('Decide on presentation %s (message %s' % (current.get('presentation_id'), pmid)) in g['text'])
            check(CA, 'the admission wait with no presentation says so plainly and links nothing',
                  delivered(a) and 'Decision waiting: admission' in a['text'] and a.get('reply_to') is None
                  and 'Presentation: none published yet; the request is OFFERED.' in a['text']
                  and not message(a.get('message_id')).get('reply_to_message'))
            check(CA, 'a report offers no choices and records no answer',
                  bool(g) and 'accept |' not in g['text'] and 'Choices' not in g['text']
                  and (entity(groom_id) or {}).get('data', {}).get('state') == 'OFFERED')

        # AC2: gate or review rejected, from the real gate observation and floor record.
        with section(CG):
            red_id = (red or {}).get('observation', {}).get('id')
            red_obs = (entity(red_id) or {}).get('data') or {}
            gr = one('gate_result', red_id)
            check(CG, 'the red gate observation is reported failed with its commit, exit and last line [%s]' % fact(gr),
                  delivered(gr) and red_obs.get('green') is False and red_obs.get('exit') == 1
                  and 'Veldo: Gate failed' in gr['text']
                  and fact(gr) == 'Fact: the gate failed at commit %s: exit 1, last line GATE: RED (%s) (the observation '
                  'names no unit)' % (red_commit, red_commit)
                  and 'Next: nothing is offered for review from this commit' in gr['text']
                  and 'Evidence: observation %s, output %s' % (red_id, red_obs.get('stdout_digest')) in gr['text'])
            back = one('gate_result', floor_return, 'Review rejected')
            check(CG, 'the returned review is reported rejected: reviewer, verdict, and nothing lands [%s]' % fact(back),
                  delivered(back) and (entity(floor_return) or {}).get('data', {}).get('state') == 'returned'
                  and fact(back) == 'Fact: reviewer reviewer returned unit %s attempt 1 with verdict fail' % returning
                  and 'Next: the unit goes back for a fix (ready); nothing lands.' in back['text']
                  and back.get('run') == (reviewed.get(returning) or {}).get('dispatch'))
            passed = one('gate_result', floor_pass, 'Review passed')
            handoff = one('gate_result', floor_pass, 'Handed off')
            accepted = one('gate_result', floor_pass, 'Build accepted')
            green_ids = [(built.get(u) or {}).get('gate', {}).get('observation', {}).get('id') for u in (passing, returning)]
            check(CG, 'the passing review, the handoff and the build acceptance are reported, none as a completion',
                  delivered(passed) and delivered(handoff) and delivered(accepted)
                  and fact(passed) == 'Fact: reviewer reviewer passed unit %s attempt 1 with verdict pass' % passing
                  and 'met the review policy: 1 of 1 required reviews for risk standard (reviewer)' in handoff['text']
                  and 'the built commit %s passed its gate with accepted proof' % (built.get(passing) or {}).get('tip') in accepted['text']
                  and not any('Completed' in x.get('text', '') for x in (passed, handoff, accepted)))
            check(CG, 'each green observation is reported passed',
                  all(delivered(one('gate_result', i)) and 'Veldo: Gate passed' in one('gate_result', i).get('text', '')
                      for i in green_ids) and all(green_ids))

        # AC2: completed only from VELDO-0051's confirmed landing, with the revision and proof.
        with section(CC):
            done = by_event.get('completion', [])
            oracle = {(e['unit'], e['receipt'], e['commit']) for e in shipped}
            check(CC, 'every completion report is a spec.shipped VELDO-0051 derives for its receipt [%s]'
                  % [(r.get('unit'), (r.get('source') or {}).get('receipt')) for r in done],
                  bool(done) and all((r.get('unit'), (r.get('source') or {}).get('receipt'), r.get('revision')) in oracle
                                     and (r.get('source') or {}).get('event_id') in {e['id'] for e in shipped}
                                     for r in done))
            check(CC, 'the build-only attempt, the unconfirmed publication and the handoff are no completion',
                  bool(done) and not any(r.get('unit') in ('U128-build', 'U128-open', passing) for r in done)
                  and not any('Completed' in r.get('text', '') for r in mine if r.get('event') != 'completion'))
            c = one('completion', land_receipt)
            check(CC, 'the completion names the confirmed revision and the proof',
                  delivered(c) and 'unit U128-land landed revision %s through dispatch %s' % (cand, land_did) in c['text']
                  and 'Evidence: proof sha256:proof-U128-land, implementation %s, receipt %s' % (cand, land_receipt)
                  in c['text'])

        # AC2: unknown and unavailable state stays explicit.
        with section(CU):
            u = one('work_progress', 'dispatch:' + lost_did, 'unknown')
            check(CU, 'an unknown dispatch outcome is said to be unknown, with the recorded reason [%s]' % fact(u),
                  delivered(u) and 'Veldo: Work outcome unknown' in u['text']
                  and fact(u) == 'Fact: dispatch %s of unit %s at station review, attempt 1, its outcome is unknown: '
                  'launch_evidence_missing' % (lost_did, lost)
                  and 'nothing is assumed and a stop is owed' in u['text'] and 'running' not in u['text'].split('\n')[0])
            k = one('work_progress', 'dispatch:' + killed_did, 'signal')
            check(CU, 'a worker ended by a signal has no return code, and the report says so [%s]' % fact(k),
                  delivered(k) and fact(k) == 'Fact: dispatch %s of unit %s at station review, attempt 1, was ended by '
                  'signal 9, with no return code, stopped at its deadline' % (killed_did, killed)
                  and 'this is not a completion' in k['text'])
            f = one('work_progress', 'dispatch:' + refused_did)
            check(CU, 'a refused launch names its refusal [%s]' % fact(f),
                  delivered(f) and fact(f).endswith('refused: receiver_unavailable') and 'Veldo: Work refused' in f['text'])
            o = one('objective_accepted', oid)
            gr = one('gate_result', (red or {}).get('observation', {}).get('id'))
            check(CU, 'an objective names no unit or run, and a gate observation no unit or project, and each says so',
                  delivered(o) and 'accepted at revision 1 (bound digest sha256:bound-o128)' in o['text']
                  and 'Unit: none | Run: none' in o['text'] and delivered(gr) and 'Project: unavailable |' in gr['text']
                  and 'Unit: none |' in gr['text'])

        # The stop is reported once, as progress; the andon's own notice stays the one decision message.
        with section(SN):
            s = one('stop', stop_id)
            notice = sorted(andon.notices(stop_id), key=lambda n: n.get('request_version') or 0) if stop_id else []
            first_notice = (notice[0].get('message_id') if notice else None)
            check(SN, 'the stop was raised and noticed by the andon service, then revised [%s %s]'
                  % (raised.get('outcome'), revised.get('outcome')),
                  raised.get('outcome') == 'stopped' and notices_after_raise == 1 and len(notice) == 2)
            check(SN, 'one stop report: unit, station, interrupted state and the awaited authority',
                  delivered(s) and 'Veldo: Stopped: unit U128-stop at the build station' in s['text']
                  and 'interrupts RUNNING; effect clean; awaiting owner' in s['text'] and 'reason-v128' not in s['text'])
            check(SN, 'it replies to the stop request\'s current presentation, the andon\'s latest notice',
                  bool(s) and s.get('reply_to') == (notice[-1].get('message_id') if notice else -1)
                  and first_notice != s.get('reply_to'))
            check(SN, 'the andon\'s own request is never reported as a waiting decision, nor its revision',
                  bool(s) and not [r for r in mine if (r.get('source') or {}).get('entity_id') == stop_request]
                  and 'Choices' not in s['text'])

        # AC3: only the configured owner's enrolled chat.
        with section(RO):
            enrolled = (entity('channel-enrollment:telegram_chat:owner') or {}).get('data', {}).get('chat_id')
            check(RO, 'every report went to the configured owner\'s enrolled chat, the activation\'s chat',
                  bool(mine) and enrolled == chat == (acts.current() or {}).get('enrolled_chat')
                  and all(r.get('enrolled_chat') == chat and r.get('chat_id') == chat for r in mine))
            check(RO, 'no other chat received anything', not in_chat(tech_chat) and not in_chat(stranger['id']))
            check(RO, 'every send of the pass was admitted by the activation gate, one admission each [%d of %d]'
                  % (len(gated), len(mine)), bool(mine)
                  and len(gated) == len(mine) + (summary1 or {}).get('published', 0)
                  and all(o.get('outcome') == 'admitted' for o in gated))

        # AC3: a reporter configured for another person's chat is refused at the edge; nothing is sent there.
        with section(RS):
            tech = attempt(lambda: TR.Reporter(ing, owner='techlead')) if TR is not None else None
            tech_before = others()
            tech_gate_before = len(ing.gate.observations)
            tech_results = attempt(lambda: tech.run(), []) if tech is not None else []
            tech_records = reports('techlead')
            tech_gate = [o for o in ing.gate.observations[tech_gate_before:] if o.get('operation') == 'sendMessage']
            check(RS, 'every substituted send is refused by name at the gate [%s]'
                  % sorted({x.get('reason') for x in tech_results}),
                  bool(tech_records) and len(tech_records) == len(mine)
                  and all(t.get('outcome') == 'refused' and t.get('refusal') == 'chat_not_enrolled'
                          and t.get('enrolled_chat') == tech_chat and t.get('chat_id') is None
                          and t.get('message_id') is None for t in tech_records))
            check(RS, 'nothing reached that chat, and the gate refused each send by name',
                  not in_chat(tech_chat) and len(tech_gate) == len(tech_records)
                  and all((o.get('outcome'), o.get('reason')) == ('refused', 'chat_not_enrolled') for o in tech_gate))
            check(RS, 'each refusal is visibly unsent and its source event is kept',
                  bool(tech_records) and sorted(t.get('report_id') for t in tech_records)
                  == sorted(x.get('report_id') for x in (attempt(lambda: tech.unsent(), []) or []))
                  and all(kept(t) for t in tech_records) and tech_before == others())

        # AC3: a normal send refusal at the boundary is recorded as refused, never as delivered.
        with section(SR):
            blocked, blocked_digest = prepare(unit('U128-blocked'), 'review', {'unit': 'U128-blocked'}, {'reviewer': 'reviewer'})
            receiver.accept(blocked, blocked_digest, identity('receiver'), now=_v128_time.time())
            api['refuse'] = True
            refused_before = len(api['refused'])
            entities_pre = others()
            blocked_pass = attempt(lambda: channel.tick(), {}) if channel is not None else {}
            api['refuse'] = False
            b = [r for r in reports() if (r.get('source') or {}).get('entity_id') == 'dispatch:' + blocked]
            b = b[0] if len(b) == 1 else {}
            check(SR, 'the platform answered the send with its own 403 error and published nothing',
                  len(api['refused']) == refused_before + 1 and not [m for (c, m), v in bot['messages'].items()
                                                                    if blocked in v.get('text', '')])
            check(SR, 'the send result observed is the platform\'s: refused by name, no message identity [%s %s]'
                  % (b.get('outcome'), b.get('refusal')),
                  b.get('outcome') == 'refused' and b.get('refusal') == 'channel_refused' and b.get('message_id') is None
                  and [x.get('outcome') for x in (blocked_pass or {}).get('reported') or []] == ['refused'])
            reporter = getattr(channel, 'reporter', None)
            metrics = attempt(lambda: reporter.metrics(), {}) or {}
            later = attempt(lambda: channel.tick(), {}) if channel is not None else {}
            check(SR, 'it is visibly unsent in the metrics, and a later pass sends nothing again',
                  bool(b) and b.get('report_id') in (metrics.get('unsent') or [])
                  and b.get('report_id') not in (metrics.get('pending') or [])
                  and (later or {}).get('reported') == [] and (reports_b := [r for r in reports() if r.get('report_id') == b.get('report_id')])
                  and reports_b[0].get('outcome') == 'refused'
                  and not [m for (c, m), v in bot['messages'].items() if blocked in v.get('text', '')])
            check(SR, 'the source event is kept and no decision was fabricated',
                  kept(b) and entities_pre == others()
                  and (entity('dispatch:' + blocked) or {}).get('data', {}).get('state') == 'accepted')

        # Observability: named refusals with their error class, counts and pending work; no text or token.
        with section(OB):
            reporter = getattr(channel, 'reporter', None)
            obs = list(getattr(reporter, 'observations', []) or []) + list(getattr(tech, 'observations', []) or [])
            text = _v128_json.dumps(obs)
            metrics = attempt(lambda: reporter.metrics(), {}) if reporter is not None else {}
            check(OB, 'every refusal is named and classed; unknown is never success',
                  bool(obs) and all(o.get('reason') and o.get('error_class') for o in obs if o.get('outcome') == 'refused')
                  and any(o.get('outcome') == 'refused' for o in obs)
                  and TR.taxonomy('channel_refused') == 'unavailable_service'
                  and TR.taxonomy('chat_not_enrolled') == 'missing_authority'
                  and TR.taxonomy('no_such_code') == 'unknown_outcome')
            check(OB, 'observations carry the event, report, source sequence and outcome, and no report text or token',
                  bool(obs) and all(o.get('event') and o.get('report_id') and o.get('journal_seq') for o in obs)
                  and 'Fact:' not in text and 'bot128' not in text and 'SSH SIGNATURE' not in text)
            check(OB, 'metrics count accepted and refused operations, the sent and unsent reports, the since and no '
                  'pending work [%s]' % {k: (v if not isinstance(v, list) else len(v)) for k, v in (metrics or {}).items()},
                  (metrics or {}).get('accepted', 0) > 0 and (metrics or {}).get('refused', 0) > 0
                  and (metrics or {}).get('sent') == len(mine)
                  and len((metrics or {}).get('unsent') or []) == 1 and (metrics or {}).get('pending') == []
                  and (metrics or {}).get('since') == (cursor() or [None])[0])
            check(OB, 'no connection beyond the loopback interface was attempted [%d]' % len(attempts), not attempts)

        # The reporter runs in the running service's pass, with its since stored.
        with section(WT):
            reported = (summary1 or {}).get('reported') or []
            check(WT, 'the pass itself made every report, and nothing was reported before it [%d of %d]'
                  % (len(reported), len(mine)),
                  before_tick == [] and bool(mine) and sorted(x.get('report_id') for x in reported)
                  == sorted(r.get('report_id') for r in mine) and all(x.get('outcome') == 'sent' for x in reported)
                  and (summary1 or {}).get('notable') is True)
            check(WT, 'the reporter the pass ran reports to the activation record\'s owner',
                  getattr(getattr(channel, 'reporter', None), 'owner', None) == (acts.current() or {}).get('owner') == 'owner')
            check(WT, 'the since is stored in the authority at the last sequence the pass read [%s, head %s]'
                  % (since1, tick_head), since1 == [tick_head] and tick_head >= committed_head)

        # A restart neither repeats nor drops a report.
        with section(WR):
            stored_before = cursor()
            reports_before = {r['report_id'] for r in reports()}
            attempt(lambda: channel.close())
            channel = None
            down, down_digest = prepare(unit('U128-down'), 'review', {'unit': 'U128-down'}, {'reviewer': 'reviewer'})
            receiver.accept(down, down_digest, identity('receiver'), now=_v128_time.time())
            down_process = identity()
            receiver.run(down, down_digest, down_process, now=_v128_time.time())
            sends_down = sends()
            channel2 = attempt(lambda: CH.Channel(str(A.config_path)))
            restart = attempt(lambda: channel2.tick(), {}) if channel2 is not None else {}
            fresh = [r for r in reports() if r['report_id'] not in reports_before]
            examined = list(getattr(getattr(channel2, 'reporter', None), 'observations', []) or [])
            check(WR, 'the first pass after the restart reports exactly what was committed while the service was down '
                  '[%s]' % sorted(fact(r)[:60] for r in fresh),
                  sorted((r.get('source') or {}).get('entity_id') for r in fresh) == ['dispatch:' + down] * 2
                  and all(delivered(r) for r in fresh) and sends() - sends_down == 2
                  and [x.get('outcome') for x in (restart or {}).get('reported') or []] == ['sent', 'sent'])
            check(WR, 'it repeats nothing: it read only after the stored since, with no report already made [%d]'
                  % len(examined), bool(examined) and not any(o.get('outcome') == 'already_reported' for o in examined)
                  and len(examined) == 2 and bool(stored_before) and cursor()[0] > stored_before[0])
            quiet = attempt(lambda: channel2.tick(), {}) if channel2 is not None else {}
            check(WR, 'and the next pass has nothing to report', (quiet or {}).get('reported') == [] and sends() - sends_down == 2)

        # Nothing is sent or recorded while the edge is stopped; it is reported once the owner activates it again.
        with section(WS):
            acts2 = channel2.ingress.activations if channel2 is not None else acts
            stop_edge = attempt(lambda: A.authorize(acts2, 'stop'))
            paused, paused_digest = prepare(unit('U128-paused'), 'review', {'unit': 'U128-paused'}, {'reviewer': 'reviewer'})
            receiver.accept(paused, paused_digest, identity('receiver'), now=_v128_time.time())
            stopped_since, stopped_sends, stopped_reports = cursor(), sends(), len(reports())
            halted = attempt(lambda: channel2.tick(), {}) if channel2 is not None else {}
            check(WS, 'while the edge is stopped the pass is refused and reports nothing: no send, no record, the since '
                  'unchanged [%s]' % (halted or {}).get('reason'),
                  (acts2.current() or {}).get('state') == 'stopped' and (halted or {}).get('reason') == 'edge_stopped'
                  and (halted or {}).get('reported') == [] and sends() == stopped_sends
                  and len(reports()) == stopped_reports and cursor() == stopped_since)
            resumed = attempt(lambda: A.authorize(acts2, 'activate', qualification_id=qid, qualification_digest=qd))
            after = attempt(lambda: channel2.tick(), {}) if channel2 is not None else {}
            got = [r for r in reports() if (r.get('source') or {}).get('entity_id') == 'dispatch:' + paused]
            check(WS, 'once the owner activates the edge again, what was committed meanwhile is reported once [%s]'
                  % [x.get('outcome') for x in (after or {}).get('reported') or []],
                  (acts2.current() or {}).get('state') == 'active' and len(got) == 1 and delivered(got[0])
                  and [x.get('outcome') for x in (after or {}).get('reported') or []] == ['sent']
                  and sends() == stopped_sends + 1 and stop_edge is not None and resumed is not None)

        with section(OB):
            check(OB, 'no call raised [%s]' % '; '.join(failures[:3]), not failures)
    finally:
        _v128_socket.create_connection = real_connect
        server.shutdown()
        server.server_close()
        for held in (channel, channel2):
            if held is not None:
                try:
                    held.close()
                except Exception:  # noqa: BLE001 - teardown
                    pass
        if ing is not None and channel is None and channel2 is None:
            try:
                ing.conn.close()
            except Exception:  # noqa: BLE001 - teardown
                pass
        A.conn.close()
    return rows


_v128_started = _v128_time.monotonic()
_v128_fast = '/dev/shm' if _v128_Path('/dev/shm').is_dir() else None
with _v128_temp.TemporaryDirectory(prefix='v128-', dir=_v128_fast) as _v128_dir:
    _v128_rows = _v128_checks(_v128_Path(_v128_dir))
for _v128_name, _v128_observed in _v128_rows.items():
    _v128_ok = bool(_v128_observed) and all(ok for _, ok in _v128_observed)
    if not _v128_ok:
        for _v128_label, _v128_one in _v128_observed:
            if not _v128_one:
                print('  VELDO-0128 %s detail: %s' % (_v128_name, _v128_label))
    expect('VELDO-0128 ' + _v128_name, _v128_ok)
print('VELDO-0128 send/real-telegram: PENDING the lead\'s run with the owner through the running factory; '
      'the rows use a loopback stand-in; not counted as passed')
print('VELDO-0128 suite seconds: %.3f' % (_v128_time.monotonic() - _v128_started))
