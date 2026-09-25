"""VELDO-0128: Telegram progress and completion reports projected from committed journal events.

Run: python3 scripts/selftest.py --suite 72_veldo_0128_reports

Only shared ROOT and expect are consumed. The authority is real (scripts/suites/support/v73_authority.py):
SQLite store, OpenSSH signatures on every command and journal record, membership, the owner's chat
enrollment, the VELDO-0067 edge key and the protected signer process. The ingress is the production
construction (control_channel_ingress.open_ingress) from 0600 host configuration files, qualified and
activated by the owner's signed VELDO-0073 commands, and every report goes through its gated presentation
edge. Every Bot API exchange goes to a loopback stand-in in the platform's documented shapes (the VELDO-0073
stand-in, with a switch that answers sendMessage with the Bot API's own 403 error object), and a socket
guard installed for the whole suite refuses and counts every connection to anything but the loopback
interface, so no row and no mutant can reach Telegram, and no real token file is read.

The event set is committed in that authority. The grooming and admission waits are real VELDO-0064 inbox
requests (the grooming one framed and presented by the VELDO-0065 presenter); the stop is a real VELDO-0075
andon stop, raised, noticed and revised by the andon service. The objective, the dispatch records, the unit
transitions out of the gate and review stations, the publication effects and the completion receipts are
store fixtures written with the store's generic signed command, as the VELDO-0051 and VELDO-0075 suites lay
them: their services are proved by their own suites, and the completion predicate this module relies on is
VELDO-0051's own reader. Mutation workers replace the production copies named in PRODUCTION below, never
assertions or fixtures. Where the report module is absent (the pre-change tree, for the red record) every
row asserts its named interface and fails by its own assertions. The real-Telegram send is run once by the
lead with the owner through the running factory; it is reported PENDING here and never counted.
No private key byte, signature or token is printed or retained.
"""
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

_V128_ROWS = ('install/assets', 'registry/declared-set', 'registry/delivery', 'registry/committed-sources',
              'content/running', 'content/awaiting-decision', 'content/gate-rejected', 'content/completed',
              'content/unknown-explicit', 'stop/no-second-notice', 'recipient/owner-chat-only',
              'recipient/substitution-refused', 'send/refusal-recorded', 'observability/named-refusals')
# The spec's declared event universe (AC1), independent of the module's own registry.
_V128_EVENTS = ('objective_accepted', 'decision_awaiting', 'work_progress', 'gate_result', 'stop', 'completion')


def _v128_load(name, path):
    spec = _v128_import.spec_from_file_location(name, path)
    module = _v128_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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

    IA, RD, RL, RC, CR, CA, CG, CC, CU, SN, RO, RS, SR, OB = _V128_ROWS
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {'control_telegram_report.py': ROOT / ".veldo" / "control_telegram_report.py"}
    scaffold_path = ROOT / ".veldo" / "init_scaffold.py"
    # The installed copy lives in a `.veldo` directory, as installed: events.py finds its siblings there.
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
    ing = None
    try:
        for who, kind, roles in (('andon', 'service', []), ('techlead', 'person', ['technical_authority'])):
            path = base / 'authority' / ('key-' + who)
            _v128_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v128-' + who, '-f', str(path)],
                         check=True, capture_output=True, timeout=10, stdin=_v128_sp.DEVNULL)
            A.keyfile[who] = path
            A.public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
            A.admin('steward', 'enroll_principal', {'principal': who, 'principal_type': kind, 'roles': roles,
                                                    'public_key': A.public[who], 'independence_group': who,
                                                    'scope': ['project-a']}, enrollee=who)
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
            """Every entity that is not a report record: what a report must never change."""
            return sorted((r[0], r[1], r[2]) for r in A.conn.execute('SELECT id, version, digest FROM entities WHERE kind != ?',
                                                                    ('telegram_report',)))

        def in_chat(which):
            """The messages the bot published in `which` (a person's own messages to it are not sends)."""
            return sorted(mid for (c, mid), m in bot['messages'].items()
                          if c == which and (m.get('from') or {}).get('id') == bot_user['id'])

        def sends():
            return api['calls'].count('sendMessage')

        ing = IN.open_ingress(str(A.config_path))
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
        andon = AND.Andon(ing, AND.service_signer('andon', str(A.keyfile['andon'])), scope='project-a')
        since = head()

        # ---- the event set, committed in the authority ---------------------------------------------
        repo = ids['repository_uuid']

        def unit(uid, state, **extra):
            A.fixture(uid, 'execution_unit', dict({'unit_id': uid, 'state': state, 'repository_uuid': repo,
                                                   'revision': 1, 'station_contract': None}, **extra))
            return uid

        def dispatch(did, uid, state, **extra):
            contract = {'dispatch_id': did, 'unit': uid, 'station': 'build', 'domain': ids['domain_uuid'],
                        'repository': repo, 'worker': 'worker-' + uid}
            A.fixture('dispatch:' + did, 'dispatch', dict({'schema': 'veldo.dispatch/v1', 'dispatch_id': did,
                                                           'state': state, 'contract': contract,
                                                           'contract_digest': 'sha256:contract-' + did}, **extra))

        def hexed(label):
            return __import__('hashlib').sha1(label.encode()).hexdigest()

        # objective_accepted: proposed, then accepted by its settlement.
        oid = 'objective:%s:o128' % repo
        objective = dict(schema='veldo.objective/v1', uuid=oid, entity_type='objective', domain_uuid=ids['domain_uuid'],
                         repository_uuid=repo, project='project-a', state='PROPOSED', revision=1,
                         bound_digest='sha256:bound-o128', accepted_revision=None, acceptance=None)
        A.fixture(oid, 'objective', objective)
        A.fixture(oid, 'objective', dict(objective, state='ACCEPTED', accepted_revision=1, acceptance={
            'settlement_id': 'request-settlement:o128:1', 'receipt_id': 'settlement-receipt:o128:1', 'ruling': 'approve'}))
        # decision_awaiting: a real grooming request, framed and presented; and a real admission request the
        # presenter has not presented (its presentation is unavailable, said plainly).
        groom_id, groom_shown = A.open_request(ing, 'G128')
        adm_alias = 'A128'
        target = {'kind': 'backlog_item', 'ref': 'backlog:' + adm_alias, 'digest': 'sha256:' + hexed(adm_alias) * 1}
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
        # work_progress: one dispatch through accepted, running and exited, one whose outcome is unknown.
        run_did, lost_did = 'dispatch/U128-run/build', 'dispatch/U128-lost/build'
        dispatch(run_did, 'U128-run', 'prepared')
        dispatch(run_did, 'U128-run', 'accepted')
        dispatch(run_did, 'U128-run', 'running', process={'pid': 4242})
        dispatch(run_did, 'U128-run', 'exited', termination={'exit_status': 0, 'output_digest': 'sha256:out'})
        dispatch(lost_did, 'U128-lost', 'accepted')
        dispatch(lost_did, 'U128-lost', 'unknown')
        # gate_result: the gate rejects one unit (with its failure receipt); the review passes another.
        unit('U128-gate', 'VERIFYING', dispatch_id='dispatch/U128-gate/build')
        unit('U128-gate', 'FAILED', dispatch_id='dispatch/U128-gate/build', failure_receipt='receipt:failure:U128-gate:1')
        unit('U128-review', 'REVIEWING')
        unit('U128-review', 'READY_TO_LAND', review_receipt='receipt:review:U128-review:1')
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
                kind='publication', dispatch_id=did, unit=uid, domain_uuid=ids['domain_uuid'], repository_uuid=repo,
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
        dispatch('dispatch/U128-build/build', 'U128-build', 'exited', termination={})
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
        shipped, judged = EP.Projection(A.S, db, domain=ids['domain_uuid'], repository=repo,
                                        root=_v128_Path(db).parent).derive(
            [(s, c, d, t, None) for s, (c, d, t) in sorted(committed.items())], 0)

        # ---- the reporter, to the configured owner --------------------------------------------------
        reporter = None
        if TR is not None:
            reporter = attempt(lambda: TR.Reporter(ing, owner='owner', project='project-a', since=since))
        entities_before = others()
        owner_before = in_chat(chat)
        sends_before = sends()
        gate_before = len(ing.gate.observations)
        results = attempt(lambda: reporter.run(), []) if reporter is not None else []
        records = attempt(lambda: reporter.records(), []) if reporter is not None else []
        mine = [r for r in records if r.get('owner') == 'owner']
        by_event = {}
        for r in mine:
            by_event.setdefault(r.get('event'), []).append(r)
        delivered_ids = [mid for mid in in_chat(chat) if mid not in owner_before]
        gated = [o for o in ing.gate.observations[gate_before:] if o.get('operation') == 'sendMessage']
        entities_after = others()

        def message(mid, which=chat):
            return bot['messages'].get((which, mid)) or {}

        def one(event, entity_id):
            found = [r for r in by_event.get(event, []) if (r.get('source') or {}).get('entity_id') == entity_id]
            return found[0] if len(found) == 1 else {}

        def delivered(r):
            """The stand-in's own stored message for a record, and whether it matches the record exactly."""
            m = message(r.get('message_id'))
            return (r.get('outcome') == 'sent' and bool(m) and m.get('text') == r.get('text')
                    and (m.get('chat') or {}).get('id') == chat and r.get('chat_id') == chat)

        # AC1: the registry is the declared set.
        with section(RD):
            registry = getattr(TR, 'REGISTRY', ()) if TR is not None else ()
            names = tuple(r[0] for r in registry)
            check(RD, 'the registry names exactly the declared event set [%s]' % ', '.join(names),
                  sorted(names) == sorted(_V128_EVENTS) and len(names) == len(set(names)))
            check(RD, 'each registration has its handler on the reporter', TR is not None and all(
                callable(getattr(TR.Reporter, h, None)) for _n, _k, h in registry))
            check(RD, 'the production ingress is activated by the owner and the reporter is built on it',
                  activated and reporter is not None)

        # AC1: every enabled event committed produces its correlated report to the owner.
        with section(RL):
            expected_sources = {'objective_accepted': [oid], 'decision_awaiting': [groom_id, adm_id],
                                'work_progress': ['dispatch:' + run_did, 'dispatch:' + lost_did,
                                                  'dispatch:dispatch/U128-build/build'],
                                'gate_result': ['U128-gate', 'U128-review'], 'stop': [stop_id],
                                'completion': [land_receipt]}
            for event in _V128_EVENTS:
                got = sorted((r.get('source') or {}).get('entity_id') for r in by_event.get(event, []))
                if event == 'work_progress':
                    got = sorted(set(got))
                check(RL, '%s: a report for every committed source [%s]' % (event, got),
                      got == sorted(expected_sources[event]))
                check(RL, '%s: every report was sent, stored by the platform exactly as recorded, to the owner' % event,
                      bool(by_event.get(event)) and all(delivered(r) for r in by_event.get(event, [])))
            check(RL, 'the registry-to-delivery comparison: the delivered events are the declared set',
                  sorted(by_event) == sorted(_V128_EVENTS))
            correlated = all(
                r.get('project') == 'project-a' and r.get('domain_uuid') == ids['domain_uuid']
                and r.get('repository_uuid') == repo and 'run' in r and 'unit' in r
                and isinstance(r.get('source'), dict) and all(r['source'].get(k) for k in (
                    'journal_seq', 'command_id', 'record_digest', 'entity_id', 'entity_digest'))
                and ('Unit: %s | Run: %s' % (r.get('unit') or 'none', r.get('run') or 'none')) in (r.get('text') or '')
                and ('journal %s, command %s' % (r['source']['journal_seq'], r['source']['command_id'])) in r.get('text', '')
                for r in mine)
            check(RL, 'every report keeps project, unit, run and the source event identity, and shows them',
                  bool(mine) and correlated)
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
                    and entry.get('digest') == s.get('entity_digest') and since < s.get('journal_seq', 0) <= committed_head
            check(RC, 'every report names a committed journal record and entity by digest, after since',
                  bool(mine) and real)
            check(RC, 'no report for the prepared dispatch, the build-only receipts, the presentation records, '
                  'the revised stop or the andon\'s own request',
                  bool(mine) and not any((r.get('source') or {}).get('entity_id') in (
                      'receipt:attempt_finished:U128-build:0', 'receipt:artifact_accepted:U128-build:0', stop_request)
                      or (r.get('source') or {}).get('entity_kind') in ('channel_presentation', 'andon_notice',
                                                                         'presentation_framing') for r in mine)
                  and len([r for r in mine if r.get('event') == 'stop']) == 1
                  and sorted(r.get('text', '').split('\n')[3] for r in by_event.get('work_progress', [])
                             if (r.get('source') or {}).get('entity_id') == 'dispatch:' + run_did)
                  == sorted('Fact: dispatch %s of unit U128-run at station build is %s (worker worker-U128-run)'
                            % (run_did, s) for s in ('accepted', 'running', 'exited')))
            check(RC, 'one message per report: the owner\'s chat received exactly the sent reports',
                  bool(mine) and sorted(r.get('message_id') for r in mine) == sorted(delivered_ids)
                  and sends() - sends_before == len(mine))
            again = attempt(lambda: reporter.run(), None) if reporter is not None else None
            check(RC, 'a second run sends nothing and reports each one as already reported',
                  again is not None and sends() - sends_before == len(mine) and len(again) == len(mine)
                  and all(a.get('outcome') == 'already_reported' for a in again))
            written = set()
            for seq, (cmd, _d, changes) in journal().items():
                if seq > committed_head:
                    written |= {v.get('kind') for v in changes.values()}
            check(RC, 'the reporter writes only its own report records: no admission, settlement, stop or completion',
                  written == {'telegram_report'} and entities_before == entities_after)

        # AC2: running, from the stored dispatch record.
        with section(CR):
            running = [r for r in by_event.get('work_progress', []) if 'is running' in r.get('text', '')]
            r = running[0] if len(running) == 1 else {}
            stored = entity('dispatch:' + run_did) or {}
            check(CR, 'the running report\'s delivered bytes are the recorded text',
                  bool(r) and message(r.get('message_id')).get('text') == r.get('text'))
            check(CR, 'it states the committed fact: dispatch, unit, station, state and worker, from its journal record',
                  bool(r) and (committed.get(r['source']['journal_seq'])[2]['dispatch:' + run_did]['data']['state'] == 'running')
                  and 'Fact: dispatch %s of unit U128-run at station build is running (worker worker-U128-run)' % run_did
                  in r['text'] and r.get('unit') == 'U128-run' and r.get('run') == run_did
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

        # AC2: gate or review rejected, with its receipt.
        with section(CG):
            gr, rv = one('gate_result', 'U128-gate'), one('gate_result', 'U128-review')
            check(CG, 'the gate rejection states the unit, the edge and its failure receipt',
                  delivered(gr) and 'Veldo: Gate rejected' in gr['text']
                  and 'Fact: the gate rejected unit U128-gate: VERIFYING -> FAILED' in gr['text']
                  and 'Evidence: receipt receipt:failure:U128-gate:1' in gr['text']
                  and 'Next: the unit goes back through its stations; nothing lands.' in gr['text'])
            check(CG, 'the review pass states its receipt and does not claim completion',
                  delivered(rv) and 'Veldo: Review passed' in rv['text'] and 'receipt:review:U128-review:1' in rv['text']
                  and 'Completed' not in rv['text'])

        # AC2: completed only from VELDO-0051's confirmed landing, with the revision and proof.
        with section(CC):
            done = by_event.get('completion', [])
            oracle = {(e['unit'], e['receipt'], e['commit']) for e in shipped}
            check(CC, 'every completion report is a spec.shipped VELDO-0051 derives for its receipt [%s]'
                  % [(r.get('unit'), (r.get('source') or {}).get('receipt')) for r in done],
                  bool(done) and all((r.get('unit'), (r.get('source') or {}).get('receipt'), r.get('revision')) in oracle
                                     and (r.get('source') or {}).get('event_id') in {e['id'] for e in shipped}
                                     for r in done))
            check(CC, 'the build-only attempt and the unconfirmed publication are no completion',
                  bool(done) and not any(r.get('unit') in ('U128-build', 'U128-open') for r in done)
                  and not any('Completed' in r.get('text', '') for r in mine if r.get('event') != 'completion'))
            c = one('completion', land_receipt)
            check(CC, 'the completion names the confirmed revision and the proof',
                  delivered(c) and 'unit U128-land landed revision %s through dispatch %s' % (cand, land_did) in c['text']
                  and 'Evidence: proof sha256:proof-U128-land, implementation %s, receipt %s' % (cand, land_receipt)
                  in c['text'])

        # AC2: unknown and unavailable state stays explicit.
        with section(CU):
            lost = [r for r in by_event.get('work_progress', []) if (r.get('source') or {}).get('entity_id') == 'dispatch:' + lost_did
                    and 'is unknown' in r.get('text', '')]
            u = lost[0] if len(lost) == 1 else {}
            check(CU, 'an unknown dispatch outcome is said to be unknown and nothing is assumed',
                  delivered(u) and 'Veldo: Work outcome unknown' in u['text']
                  and 'nothing is assumed and a stop is owed' in u['text'] and 'running' not in u['text'].split('\n')[0])
            o = one('objective_accepted', oid)
            check(CU, 'an objective names no unit or run, and says so',
                  delivered(o) and 'accepted at revision 1 (bound digest sha256:bound-o128)' in o['text']
                  and 'Unit: none | Run: none' in o['text'])
            exited = [r for r in by_event.get('work_progress', []) if 'dispatch/U128-build/build' in r.get('text', '')]
            check(CU, 'an exit with no recorded status says unavailable and is not a completion',
                  len(exited) == 1 and 'exited with status unavailable' in exited[0].get('text', '')
                  and 'this is not a completion' in exited[0].get('text', ''))

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
            check(RO, 'every report send was admitted by the activation gate, one admission each [%d of %d]'
                  % (len(gated), len(mine)), bool(mine) and len(gated) == len(mine)
                  and all(o.get('outcome') == 'admitted' for o in gated))

        # AC3: a reporter configured for another person's chat is refused at the edge; nothing is sent there.
        with section(RS):
            before_tech = since_tech = head()
            dispatch('dispatch/U128-sub/build', 'U128-sub', 'running')
            tech = attempt(lambda: TR.Reporter(ing, owner='techlead', project='project-a', since=since_tech)) \
                if TR is not None else None
            tech_before = others()
            tech_gate_before = len(ing.gate.observations)
            tech_results = attempt(lambda: tech.run(), []) if tech is not None else []
            tech_records = [r for r in (attempt(lambda: tech.records(), []) if tech is not None else [])
                            if r.get('owner') == 'techlead']
            t = tech_records[0] if len(tech_records) == 1 else {}
            check(RS, 'the substituted chat is refused by name at the gate [%s]' % [x.get('reason') for x in tech_results],
                  t.get('outcome') == 'refused' and t.get('refusal') == 'chat_not_enrolled'
                  and t.get('enrolled_chat') == tech_chat and t.get('chat_id') is None and t.get('message_id') is None)
            tech_gate = [o for o in ing.gate.observations[tech_gate_before:] if o.get('operation') == 'sendMessage']
            check(RS, 'nothing reached that chat, and the gate refused the one send by name',
                  not in_chat(tech_chat) and before_tech < head()
                  and [(o.get('outcome'), o.get('reason')) for o in tech_gate] == [('refused', 'chat_not_enrolled')])
            check(RS, 'the refusal is visibly unsent and the source event is kept',
                  bool(t) and t.get('report_id') in [x.get('report_id') for x in (attempt(lambda: tech.unsent(), []) or [])]
                  and kept(t) and tech_before == others())

        # AC3: a normal send refusal at the boundary is recorded as refused, never as delivered.
        with section(SR):
            # The owner's reporter first reports what the substitution row committed, then the blocked send.
            settled = attempt(lambda: reporter.run(), []) if reporter is not None else []
            sub = [x for x in settled if x.get('outcome') != 'already_reported']
            dispatch('dispatch/U128-blocked/build', 'U128-blocked', 'running')
            api['refuse'] = True
            refused_before = len(api['refused'])
            entities_pre = others()
            blocked = [x for x in (attempt(lambda: reporter.run(), []) if reporter is not None else [])
                       if x.get('outcome') != 'already_reported']
            api['refuse'] = False
            b = [r for r in (attempt(lambda: reporter.records(), []) if reporter is not None else [])
                 if (r.get('source') or {}).get('entity_id') == 'dispatch:dispatch/U128-blocked/build']
            b = b[0] if len(b) == 1 else {}
            check(SR, 'the platform answered the send with its own 403 error and published nothing',
                  len(api['refused']) == refused_before + 1 and not [m for (c, m), v in bot['messages'].items()
                                                                    if 'U128-blocked' in v.get('text', '')])
            check(SR, 'the send result observed is the platform\'s: refused by name, no message identity [%s %s]'
                  % (b.get('outcome'), b.get('refusal')),
                  b.get('outcome') == 'refused' and b.get('refusal') == 'channel_refused' and b.get('message_id') is None
                  and [x.get('outcome') for x in blocked] == ['refused'] and [x.get('outcome') for x in sub] == ['sent'])
            check(SR, 'it is visibly unsent in the metrics, and a later run sends nothing again',
                  bool(b) and b.get('report_id') in ((attempt(lambda: reporter.metrics(), {}) or {}).get('unsent') or [])
                  and b.get('report_id') not in ((attempt(lambda: reporter.metrics(), {}) or {}).get('pending') or [])
                  and [x.get('outcome') for x in (attempt(lambda: reporter.run(), []) or [])
                       if x.get('report_id') == b.get('report_id')] == ['refused']
                  and not [m for (c, m), v in bot['messages'].items() if 'U128-blocked' in v.get('text', '')])
            check(SR, 'the source event is kept and no decision was fabricated',
                  kept(b) and entities_pre == others()
                  and (entity('dispatch:dispatch/U128-blocked/build') or {}).get('data', {}).get('state') == 'running')

        # Observability: named refusals with their error class, counts and pending work; no text or token.
        with section(OB):
            obs = reporter.observations if reporter is not None else []
            text = _v128_json.dumps(obs)
            metrics = attempt(lambda: reporter.metrics(), {}) if reporter is not None else {}
            check(OB, 'every refusal is named and classed; unknown is never success',
                  bool(obs) and all(o.get('reason') and o.get('error_class') for o in obs if o.get('outcome') == 'refused')
                  and TR.taxonomy('channel_refused') == 'unavailable_service'
                  and TR.taxonomy('chat_not_enrolled') == 'missing_authority'
                  and TR.taxonomy('no_such_code') == 'unknown_outcome')
            check(OB, 'observations carry the event, report, source sequence and outcome, and no report text or token',
                  bool(obs) and all(o.get('event') and o.get('report_id') and o.get('journal_seq') for o in obs)
                  and 'Fact:' not in text and 'bot128' not in text and 'SSH SIGNATURE' not in text)
            check(OB, 'metrics count accepted and refused operations, the sent and unsent reports, and no pending work '
                  '[%s]' % {k: (v if not isinstance(v, list) else len(v)) for k, v in metrics.items()},
                  metrics.get('accepted', 0) > 0 and metrics.get('refused', 0) > 0
                  and metrics.get('sent') == len(mine) + 1
                  and len(metrics.get('unsent') or []) == 1 and metrics.get('pending') == [])
            check(OB, 'no connection beyond the loopback interface was attempted [%d]' % len(attempts), not attempts)
            check(OB, 'no call raised [%s]' % '; '.join(failures[:3]), not failures)
    finally:
        _v128_socket.create_connection = real_connect
        server.shutdown()
        server.server_close()
        if ing is not None:
            ing.conn.close()
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
