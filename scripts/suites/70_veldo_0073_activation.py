"""VELDO-0073: per-channel live ingress activation of the Telegram edge, over a real signed store.

Run: python3 scripts/selftest.py --suite 70_veldo_0073_activation

Every exchange runs against a loopback Bot API server in the platform's documented shapes (real HTTP;
not the Telegram service, no real token), and a socket guard installed for the whole suite refuses and
counts every connection to anything but the loopback interface, so no row and no mutant can reach
Telegram. The authority is real: SQLite store, OpenSSH signatures on every command and journal record,
the owner's signed activation commands, the VELDO-0067 edge key and the actual protected signer
process. The ingress is the production construction (control_channel_ingress.open_ingress) from a host
configuration of 0600 files. Mutation workers replace the production copies named in PRODUCTION below,
never assertions or fixtures. Where the activation or ingress module is absent (the pre-change tree,
for the red record) every row asserts its named interface and drives the path that tree has, so each
row fails by its own assertions. The real-platform row (qualification/live-telegram) passes only on a
recorded live run (proof/VELDO-0073/live/qualification.json); until then it is reported PENDING and is
never counted as passed. No private key byte, signature or token is printed or retained.
"""
import ast as _v73_ast
import copy as _v73_copy
import importlib.util as _v73_import
import json as _v73_json
import os as _v73_os
import re as _v73_re
from pathlib import Path as _v73_Path
import shutil as _v73_shutil
import socket as _v73_socket
import ssl as _v73_ssl
import subprocess as _v73_sp
import threading as _v73_threading
import http.server as _v73_http
import urllib.request as _v73_urlreq
import tempfile as _v73_temp
import time as _v73_time

_V73_ROWS = ('install/assets', 'entry-points/enumerated', 'activation/no-implicit', 'activation/explicit-bound-operates',
             'qualification/real-platform-proof', 'settlement/production-construction', 'notification/wakes-only',
             'stop/halts-edge', 'stale/key-and-configuration')
_V73_TELEGRAM = 'https://api.telegram.org'
# The stand-in bot name a resolving secret reference yields in these rows; not a credential.
_V73_STAND_IN = 'stand-in-token'
_V73_LIVE = ('proof', 'VELDO-0073', 'live', 'qualification.json')


def _v73_load(name, path):
    spec = _v73_import.spec_from_file_location(name, path)
    module = _v73_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v73_checks(base):
    rows = {name: [] for name in _V73_ROWS}

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

    IA, EP, NI, EB, RP, SP, NW, SH, SK = _V73_ROWS
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {
        'control_channel_activation.py': ROOT / ".veldo" / "control_channel_activation.py",
        'control_channel_ingress.py': ROOT / ".veldo" / "control_channel_ingress.py",
        'control_channel_projection.py': ROOT / ".veldo" / "control_channel_projection.py",
        'control_channel_presentation.py': ROOT / ".veldo" / "control_channel_presentation.py",
        'control_channel_attribution.py': ROOT / ".veldo" / "control_channel_attribution.py",
        'request_doorbell.py': ROOT / ".veldo" / "request_doorbell.py",
    }
    scaffold_path = ROOT / ".veldo" / "init_scaffold.py"
    organs = base / 'installed'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v73_shutil.copyfile(source, organs / source.name)
    for name, source in PRODUCTION.items():
        target = organs / name
        if target.exists():
            target.unlink()
        if _v73_Path(source).is_file():
            _v73_shutil.copyfile(source, target)
    new = (organs / 'control_channel_activation.py').is_file() and (organs / 'control_channel_ingress.py').is_file()
    support = _v73_Path(globals().get('__v73_support__') or ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')
    H = _v73_load('v73_support', support)

    with section(IA):
        scaffold = _v73_load('v73_scaffold', scaffold_path)
        for rel in ('.veldo/control_channel_activation.py', '.veldo/control_channel_ingress.py'):
            both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
            check(IA, rel + ' installed by the scaffold', rel in scaffold._FILES)
            check(IA, rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
            check(IA, rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
            if both:
                scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
            check(IA, rel + ' laid by the installer', both and (base / 'laid' / rel).is_file()
                  and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes())
        for rel in ('.veldo/control_channel_projection.py', '.veldo/control_channel_presentation.py',
                    '.veldo/control_channel_attribution.py'):
            check(IA, rel + ' engine copy identical', (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())

    P = _v73_load('v73_projection', organs / 'control_channel_projection.py')
    V = _v73_load('v73_presentation', organs / 'control_channel_presentation.py')
    EV = _v73_load('v73_attribution', organs / 'control_channel_attribution.py')
    DB = _v73_load('v73_doorbell', organs / 'request_doorbell.py')
    ACT = _v73_load('v73_activation', organs / 'control_channel_activation.py') if new else None
    IN = _v73_load('v73_ingress', organs / 'control_channel_ingress.py') if new else None

    # The socket guard: nothing but the loopback interface is reached, and every other attempt is counted.
    attempts = []
    real_connect = _v73_socket.create_connection

    def guarded(address, *args, **kwargs):
        if address[0] != '127.0.0.1':
            attempts.append(address[0])
            raise OSError('suite guard: no network beyond the loopback interface')
        return real_connect(address, *args, **kwargs)
    _v73_socket.create_connection = guarded

    owner_user = {'id': 5580073, 'is_bot': False, 'first_name': 'Owner'}
    stranger = {'id': 5589973, 'is_bot': False, 'first_name': 'Stranger'}
    bot_user = {'id': 8000000073, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_activation_bot'}
    url, api, stop = H.stand_in({'bot73': bot_user, 'other73': {'id': 8000000074, 'is_bot': True, 'first_name': 'Other'}})
    url2, api2, stop2 = H.stand_in({'bot73': bot_user})
    api['chats'][owner_user['id']] = {'id': owner_user['id'], 'type': 'private', 'first_name': 'Owner'}
    A = H.build(base / 'authority-a', organs, owner_user['id'], url, 'bot73')
    chat = owner_user['id']

    def calls(which, method, st=None):
        return (st or api)['calls'].count(method)

    def refused_as(fn, code):
        try:
            fn()
        except Exception as exc:
            # Each organ loads its own projection copy, so the edge's refusal type is matched by name.
            return type(exc).__name__ == 'EdgeRefused' and getattr(exc, 'code', None) == code
        return False

    def receipt_of(ing, rid):
        return (ing.presenter.current(rid) or {}) if ing is not None else {}

    def pending(ing, rid):
        entry = next((e for e in ing.inbox.index()['entries'] if e['id'] == rid), {}) if ing is not None else {}
        return entry.get('category') == 'pending'

    def settlement_of(ing, rid):
        return ing.settlement.settlement(rid, 1) if ing is not None else None

    def evidence_of(update):
        return A.conn.execute('SELECT data FROM entities WHERE id=?',
                              (EV.evidence_id(bot_user['id'], update['update_id']),)).fetchone()

    ing = None
    try:
        # AC1: every installed send and receive entry point, found in the installed source itself.
        with section(EP):
            points = getattr(ACT, 'ENTRY_POINTS', ()) if ACT is not None else ()
            check(EP, 'the activation module names the installed entry points', len(points) == 5)
            sites = set()
            for path in sorted(organs.glob('*.py')):
                tree = _v73_ast.parse(path.read_text())
                for cls in [n for n in tree.body if isinstance(n, _v73_ast.ClassDef)]:
                    for fn in [n for n in cls.body if isinstance(n, _v73_ast.FunctionDef)]:
                        text = _v73_ast.get_source_segment(path.read_text(), fn) or ''
                        if '/bot%s' in text:
                            sites.add((path.name, '%s.%s' % (cls.name, fn.name), 'gated_open(' in text and 'urlopen(' not in text))
            named = {(m, q) for m, q, _ in points}
            covered = {(m, q) for m, q, _ in sites if (m, q) in named or (q.endswith('._call') and {
                (m, q.rsplit('.', 1)[0] + '.get_me'), (m, q.rsplit('.', 1)[0] + '.get_updates')} <= named)}
            check(EP, 'every Bot API call site in the installed source is a named entry point [sites: %s]'
                  % sorted(q for _, q, _ in sites), len(sites) >= 4 and covered == {(m, q) for m, q, _ in sites})
            check(EP, 'every Bot API call site opens through the activation gate, never urlopen',
                  bool(sites) and all(g for _, _, g in sites))
            for module, qual, method in points:
                cls, _, fn = qual.partition('.')
                holder = {'control_channel_projection.py': P, 'control_channel_presentation.py': V,
                          'control_channel_attribution.py': EV, 'request_doorbell.py': DB}.get(module)
                check(EP, '%s %s exists' % (module, qual), callable(getattr(getattr(holder, cls, None), fn, None)))

        # AC1 (declared falsifier): a token that resolves, or the source having landed, is never activation.
        with section(NI):
            token = _V73_STAND_IN
            gate = ACT.Gate(A.S, A.conn) if ACT is not None else None
            kw = {'activation': gate} if gate is not None else {}
            cases = {
                'TelegramEdge.send': lambda k: P.TelegramEdge(_V73_TELEGRAM, token, **k).send(chat, 'x'),
                'TelegramPresentationEdge.send': lambda k: V.TelegramPresentationEdge(P, _V73_TELEGRAM, token, **k).send(chat, 'x'),
                'TelegramAcquisitionEdge.get_me': lambda k: EV.TelegramAcquisitionEdge(P, _V73_TELEGRAM, token, **k).get_me(),
                'TelegramAcquisitionEdge.get_updates': lambda k: EV.TelegramAcquisitionEdge(P, _V73_TELEGRAM, token, **k).get_updates(0),
            }
            before = len(attempts)
            for name, call in sorted(cases.items()):
                check(NI, '%s at the Telegram origin with a resolving token and no gate refuses as not_activated' % name,
                      refused_as(lambda: call({}), 'not_activated'))
                check(NI, '%s with the gate and no activation record (edge key and chat enrolled) refuses as not_activated' % name,
                      gate is not None and refused_as(lambda: call(kw), 'not_activated'))
            sink = DB.TelegramSink(chat, 'env:VELDO_V73_STAND_IN', resolve_secret=lambda ref: token)
            check(NI, 'TelegramSink.send with a token that resolves and no activation refuses as not_activated',
                  refused_as(lambda: sink.send('notice', 'https://tracker.invalid/X'), 'not_activated'))
            gated_sink = DB.TelegramSink(chat, 'env:VELDO_V73_STAND_IN', resolve_secret=lambda ref: token,
                                         **({'activation': gate} if gate is not None else {}))
            check(NI, 'TelegramSink.send with the gate and no activation record refuses as not_activated',
                  gate is not None and refused_as(lambda: gated_sink.send('notice', 'https://tracker.invalid/X'), 'not_activated'))
            check(NI, 'ring reports the refused doorbell as failed and raises nothing',
                  DB.ring({'id': 'REQ-73', 'status': 'needs_decision', 'touchpoint': 'spec_approval', 'tier': 'standard',
                           'tracker': {'url': 'https://tracker.invalid/X'}}, sink)['outcome'] == 'failed')
            check(NI, 'no connection beyond the loopback interface was attempted [%d]' % (len(attempts) - before),
                  len(attempts) == before)

        # AC1: only the owner's separately signed activation, bound to the current enrollment, operates.
        with section(EB, SP):
            check(EB, 'the activated ingress is installed', IN is not None)
            ing = IN.open_ingress(str(A.config_path)) if IN is not None else None
        with section(EB):
            rid1, first = A.open_request(ing, 'Q1') if ing is not None else (None, {})
            woke = ing.wake({'tick': 0}) if ing is not None else {}
            got = ing.acquirer.acquire() if ing is not None else []
            check(EB, 'before any record: the production presentation refuses and sends nothing [%s]' % first.get('outcome'),
                  first.get('outcome') == 'refused' and calls('bot73', 'sendMessage') == 0)
            check(EB, 'before any record: acquisition and wake refuse as not_activated and ask the platform nothing',
                  got == [{'outcome': 'refused', 'reason': 'not_activated'}] and woke.get('reason') == 'not_activated'
                  and calls('bot73', 'getMe') == 0 and calls('bot73', 'getUpdates') == 0)
            acts = ing.activations if ing is not None else None
            by_steward = A.authorize(acts, 'qualify', who='steward') if acts else {}
            by_pm = A.authorize(acts, 'qualify', who='pm') if acts else {}
            check(EB, 'a steward cannot authorize the owner\'s edge (not_owner) and a service cannot (not_a_person)',
                  by_steward.get('reason') == 'not_owner' and by_pm.get('reason') == 'not_a_person'
                  and acts is not None and acts.current() is None)
            other_origin = A.authorize(acts, 'qualify', origin='http://192.0.2.1:80') if acts else {}
            check(EB, 'an origin that is neither Telegram nor a loopback stand-in is refused', other_origin.get('reason') == 'invalid_input')
            opened = A.authorize(acts, 'qualify') if acts else {}
            check(EB, 'the owner\'s signed qualification run is recorded, bound to his enrollment and the edge key',
                  opened.get('outcome') == 'accepted' and (acts.current() or {}).get('state') == 'qualifying'
                  and acts.current().get('enrolled_chat') == chat and acts.current().get('edge_key_id') == 'edge-telegram')
            if ing is not None:
                ing.presenter.present(rid1)
            shown = receipt_of(ing, rid1)
            check(EB, 'inside the run the presentation is published to the owner\'s enrolled chat',
                  shown.get('outcome') == 'published' and shown.get('chat_id') == chat and calls('bot73', 'sendMessage') == 1)
            edge = ing.presenter.edge if ing is not None else None
            check(EB, 'a send to any chat but the owner\'s enrolled one refuses as chat_not_enrolled',
                  edge is not None and refused_as(lambda: edge.send(stranger['id'], 'x'), 'chat_not_enrolled')
                  and calls('bot73', 'sendMessage') == 1)
            owner_update = H.deliver(api, 'bot73', owner_user, 'accept: the activation run qualifies',
                                     reply_to=(shown.get('message_ids') or [None])[-1])
            stranger_update = H.deliver(api, 'bot73', stranger, 'accept: I am not enrolled')
            woke = ing.wake({'tick': 1}) if ing is not None else {}
            outcomes = {r.get('update_id'): (r.get('outcome'), r.get('reason')) for r in woke.get('acquired', [])}
            check(EB, 'the owner\'s answer is acquired and the unenrolled sender is refused as unknown_sender',
                  outcomes.get(owner_update['update_id']) == ('answered', None)
                  and outcomes.get(stranger_update['update_id']) == ('refused', 'unknown_sender'))
            settled1 = settlement_of(ing, rid1) or {}
            check(EB, 'the answer settled once through the production settlement service', settled1.get('choice') == 'accept')

        # AC2: the real-platform-proof check; fixture evidence never qualifies the Telegram origin.
        with section(RP, EB):
            eid = lambda u: EV.evidence_id(bot_user['id'], u['update_id'])
            qid, qd, record, refused_run = None, None, {}, None
            if ing is not None:
                try:
                    qid, qd, record = ing.activations.qualify(ing.gate, ing.presenter, ing.acquirer, ing.settlement, rid1,
                                                              eid(owner_update), eid(stranger_update))
                except Exception as exc:
                    refused_run = getattr(exc, 'code', type(exc).__name__)
            check(RP, 'the stand-in run is recorded [refused: %s]' % refused_run, refused_run is None and qid is not None)
            check(RP, 'the stand-in run is recorded as stand-in qualification, every leg bound',
                  ACT is not None and ACT.qualification_problems(record, url) == [] and record.get('platform') == 'stand_in'
                  and record['owner_answer']['sender_id'] == chat
                  and record['owner_answer']['reply_to_message_id'] in record['presentation']['message_ids']
                  and record['unauthorized']['reason'] == 'unknown_sender' and record['unauthorized']['provenance'] == 'platform'
                  and record['settlement']['answer_id'] == record['owner_answer']['answer_id'])
            relabeled = _v73_copy.deepcopy(record)
            relabeled.update(origin=_V73_TELEGRAM, platform='telegram')
            for x in relabeled.get('exchanges', []):
                x['origin'], x['host'] = _V73_TELEGRAM, 'api.telegram.org'
            problems = ACT.qualification_problems if ACT is not None else (lambda r, o: ['absent'])
            check(RP, 'stand-in exchanges relabeled as Telegram are fixture_only_evidence', problems(relabeled, _V73_TELEGRAM) == ['fixture_only_evidence'])
            forged = _v73_copy.deepcopy(relabeled)
            tls = {'verified': True, 'host': 'api.telegram.org', 'version': 'TLSv1.3', 'peer_certificate': 'sha256:' + '0' * 64,
                   'dns_names': ['api.telegram.org'], 'subject': 'api.telegram.org', 'issuer': 'x', 'not_after': 'x'}
            for x in forged.get('exchanges', []):
                x['tls'] = dict(tls, host='api.telegram.org.invalid', dns_names=['api.telegram.org.invalid'])
            check(RP, 'TLS naming another host is fixture_only_evidence', problems(forged, _V73_TELEGRAM) == ['fixture_only_evidence'])
            for x in forged.get('exchanges', []):
                x['tls'] = dict(tls)
            check(RP, 'control: with TLS facts for api.telegram.org the same legs prove the platform', problems(forged, _V73_TELEGRAM) == [])
            unlinked = _v73_copy.deepcopy(forged)
            unlinked.setdefault('owner_answer', {})['response_digest'] = 'sha256:' + '1' * 64
            check(RP, 'an answer whose evidence is not the bytes of a recorded getUpdates answer is answer_unproven',
                  problems(unlinked, _V73_TELEGRAM) == ['answer_unproven'])
            # Through the organ: a Telegram run fed the stand-in's exchanges records nothing and cannot activate.
            run = A.authorize(ing.activations, 'qualify', origin=_V73_TELEGRAM) if ing is not None else {}
            fake = ACT.Gate(A.S, ing.conn) if ACT is not None else None
            refusal = None
            if fake is not None:
                fake.exchanges = [dict(x, mode='qualifying') for x in relabeled.get('exchanges', [])]
                try:
                    ing.activations.qualify(fake, ing.presenter, ing.acquirer, ing.settlement, rid1, eid(owner_update),
                                            eid(stranger_update))
                except Exception as exc:
                    refusal = getattr(exc, 'code', None)
            stored = [r for r in A.conn.execute('SELECT id FROM entities WHERE kind=?', ('channel_qualification',))]
            check(RP, 'a Telegram run fed fixture exchanges records no qualification (fixture_only_evidence)',
                  run.get('outcome') == 'accepted' and refusal == 'fixture_only_evidence' and len(stored) == 1)
            # A fixture cannot make TLS evidence by pointing the trust store elsewhere: a TLS stand-in whose
            # certificate SSL_CERT_FILE names is still refused by the gate's transport, and records no peer.
            tls_dir = base / 'tls'
            tls_dir.mkdir()
            made = _v73_sp.run(['openssl', 'req', '-x509', '-newkey', 'ed25519', '-nodes', '-keyout', str(tls_dir / 'key.pem'),
                                '-out', str(tls_dir / 'cert.pem'), '-days', '1', '-subj', '/CN=api.telegram.org',
                                '-addext', 'subjectAltName=DNS:api.telegram.org,IP:127.0.0.1'],
                               capture_output=True, timeout=30, stdin=_v73_sp.DEVNULL)
            peers, verdict, saved = [], None, _v73_os.environ.get('SSL_CERT_FILE')
            if made.returncode == 0 and ACT is not None:
                class _Tls(_v73_http.BaseHTTPRequestHandler):
                    def log_message(self, *args):
                        pass

                    def do_POST(self):
                        body = b'{"ok": true, "result": {"id": 8000000073, "is_bot": true}}'
                        self.send_response(200)
                        self.send_header('Content-Length', str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                tls_server = _v73_http.HTTPServer(('127.0.0.1', 0), _Tls)
                context = _v73_ssl.SSLContext(_v73_ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(str(tls_dir / 'cert.pem'), str(tls_dir / 'key.pem'))
                tls_server.socket = context.wrap_socket(tls_server.socket, server_side=True)
                _v73_threading.Thread(target=tls_server.serve_forever, daemon=True).start()
                try:
                    _v73_os.environ['SSL_CERT_FILE'] = str(tls_dir / 'cert.pem')
                    ACT._opener(peers).open(_v73_urlreq.Request('https://127.0.0.1:%d/botx/getMe' % tls_server.server_address[1],
                                                                data=b'{}', method='POST'), timeout=5).read()
                    verdict = 'verified'
                except Exception as exc:
                    verdict = 'refused' if 'CERTIFICATE_VERIFY_FAILED' in str(exc) else type(exc).__name__
                finally:
                    if saved is None:
                        _v73_os.environ.pop('SSL_CERT_FILE', None)
                    else:
                        _v73_os.environ['SSL_CERT_FILE'] = saved
                    tls_server.shutdown()
                    tls_server.server_close()
            check(RP, 'a TLS stand-in trusted only through SSL_CERT_FILE is refused and records no peer [%s]' % verdict,
                  verdict == 'refused' and peers == [])
            to_telegram = A.authorize(ing.activations, 'activate', origin=_V73_TELEGRAM, qualification_id=qid,
                                      qualification_digest=qd) if ing is not None else {}
            check(RP, 'the stand-in qualification never activates the Telegram origin', to_telegram.get('outcome') == 'refused'
                  and (ing.activations.current() or {}).get('state') == 'qualifying')
            active = A.authorize(ing.activations, 'activate', qualification_id=qid, qualification_digest=qd) if ing is not None else {}
            now = (ing.activations.current() or {}) if ing is not None else {}
            check(EB, 'the owner\'s signed activation names the committed qualification and binds its bot',
                  active.get('outcome') == 'accepted' and now.get('state') == 'active' and now.get('qualification_digest') == qd
                  and now.get('bot_id') == bot_user['id'] and now.get('origin') == url)
            rid2, second = A.open_request(ing, 'Q2') if ing is not None else (None, {})
            check(EB, 'the activated edge operates: a new decision is published to the enrolled chat',
                  second.get('outcome') == 'published' and second.get('chat_id') == chat)

        # AC2 / review finding: the settlement is the production construction's, from host configuration.
        with section(SP):
            check(SP, 'the ingress holds the VELDO-0068 settlement service on its own store connection',
                  ing is not None and type(ing.settlement).__name__ == 'Settlement' and ing.settlement.conn is ing.conn
                  and ing.settlement.presenter is ing.presenter)
            results = getattr(getattr(ing, 'acquirer', None), 'edge_sign', None)
            signed = [r for r in getattr(results, 'results', [])]
            check(SP, 'the owner\'s answer was signed by the actual protected signer process',
                  bool(signed) and signed[0].get('accepted') is True and isinstance(signed[0].get('signer_pid'), int))
            assertion = (settled1.get('assertion') or {}).get('attribution') or {}
            message = owner_update['message']
            check(SP, 'the settlement carries the platform message: id, sender, chat, date and the presentation replied to',
                  assertion.get('platform_message_id') == message['message_id'] and assertion.get('sender_id') == owner_user['id']
                  and assertion.get('chat_id') == chat and assertion.get('platform_timestamp') == message['date']
                  and settled1.get('originating_channel') == 'telegram_chat')

            def construct(**changes):
                config = dict(A.config, **changes)
                path = A.host / ('ingress-%s.json' % A.next_id('variant'))
                fd = _v73_os.open(str(path), _v73_os.O_WRONLY | _v73_os.O_CREAT | _v73_os.O_EXCL, 0o600)
                with _v73_os.fdopen(fd, 'w') as handle:
                    handle.write(_v73_json.dumps(config))
                try:
                    IN.open_ingress(str(path))
                except IN.Refused as exc:
                    return exc.code
                return 'constructed'
            check(SP, 'no host trust installed: the ingress is not constructed',
                  IN is not None and construct(host_trust=str(A.host / 'absent.json')) == 'missing_authority')
            check(SP, 'a decision signer the host does not trust for settlements is refused',
                  IN is not None and construct(decision_signer={'principal': 'steward'}) == 'missing_authority')
            loose = A.host / 'loose-token'
            loose.write_text('stand-in-token\n')
            loose.chmod(0o644)
            check(SP, 'a token file others can read is refused', IN is not None and construct(
                bot_api={'origin': url, 'token_file': str(loose)}) == 'invalid_input')

        # AC3: a notification only wakes acquisition; only what the platform returns settles.
        with section(NW):
            rid3, third = A.open_request(ing, 'Q3') if ing is not None else (None, {})
            replied = (third.get('message_ids') or [None])[-1]
            # The invented payload is faithful: the owner's own update shape, replying to the message exactly as
            # the platform holds it. Only the platform never returned it.
            held = _v73_copy.deepcopy(api['bots']['bot73']['messages'].get((chat, replied)) or {})
            held.pop('reply_to_message', None)
            invented = {'update_id': 730009999, 'message': {
                'message_id': 99999, 'date': 1791099999, 'text': 'accept: a notification says so',
                'from': dict(owner_user), 'chat': dict(api['chats'][chat]), 'reply_to_message': held}}
            woken = [ing.wake(invented), ing.wake(_v73_json.dumps(invented).encode())] if ing is not None else []
            kept = A.conn.execute('SELECT count(*) FROM entities WHERE id=?',
                                  (EV.evidence_id(bot_user['id'], invented['update_id']),)).fetchone()[0]
            check(NW, 'an invented notification payload wakes acquisition and is kept only as its digest',
                  len(woken) == 2 and all(w.get('outcome') == 'woken' and w.get('woken_by', '').startswith('sha256:') for w in woken)
                  and kept == 0)
            check(NW, 'the payload settles nothing: no answer, no settlement, the request still pending',
                  ing is not None and settlement_of(ing, rid3) is None and pending(ing, rid3)
                  and ing.presenter.answer_record(rid3, 1, 'owner') is None)
            real = H.deliver(api, 'bot73', owner_user, 'reject: the platform carried this one', reply_to=replied)
            after = ing.wake({'tick': 2}) if ing is not None else {}
            row = next((r for r in after.get('acquired', []) if r.get('update_id') == real['update_id']), {})
            check(NW, 'an ordinary platform event is acquired with its platform message id preserved',
                  row.get('outcome') == 'answered' and row.get('message_id') == real['message']['message_id'])
            third_settled = settlement_of(ing, rid3) or {}
            source = (third_settled.get('assertion') or {}).get('attribution') or {}
            check(NW, 'the request settles from the acquired platform evidence, not the payload',
                  third_settled.get('choice') == 'reject' and source.get('platform_message_id') == real['message']['message_id']
                  and source.get('platform_message_id') != invented['message']['message_id'])

        # AC4 (declared falsifier): an explicit stop halts send and answer acceptance; pending stays pending.
        with section(SH):
            rid4, fourth = A.open_request(ing, 'Q4') if ing is not None else (None, {})
            stopped = A.authorize(ing.activations, 'stop') if ing is not None else {}
            sends = calls('bot73', 'sendMessage')
            pulls = calls('bot73', 'getUpdates')
            check(SH, 'the owner\'s signed stop is recorded', stopped.get('outcome') == 'accepted'
                  and (ing.activations.current() or {}).get('state') == 'stopped' if ing is not None else False)
            rid5, fifth = A.open_request(ing, 'Q5') if ing is not None else (None, {})
            check(SH, 'a stopped edge sends nothing: a new decision is refused and the platform is not asked',
                  fifth.get('outcome') == 'refused' and calls('bot73', 'sendMessage') == sends)
            late = H.deliver(api, 'bot73', owner_user, 'accept: after the stop', reply_to=(fourth.get('message_ids') or [None])[-1])
            woke = ing.wake({'tick': 3}) if ing is not None else {}
            got = ing.acquirer.acquire() if ing is not None else []
            check(SH, 'a stopped edge accepts no answer: wake and acquisition refuse as edge_stopped',
                  woke.get('reason') == 'edge_stopped' and got == [{'outcome': 'refused', 'reason': 'edge_stopped'}]
                  and calls('bot73', 'getUpdates') == pulls and evidence_of(late) is None)
            gated_sink = DB.TelegramSink(chat, 'env:VELDO_V73_STAND_IN', resolve_secret=lambda ref: 'stand-in-token',
                                         **({'activation': ing.gate} if ing is not None else {}))
            check(SH, 'the doorbell refuses too', refused_as(lambda: gated_sink.send('notice', 'https://tracker.invalid/X'), 'edge_stopped'))
            check(SH, 'no fresh authority: the pending requests stay pending, unanswered and unsettled',
                  ing is not None and pending(ing, rid4) and pending(ing, rid5) and settlement_of(ing, rid4) is None
                  and ing.presenter.answer_record(rid4, 1, 'owner') is None)
            again = A.authorize(ing.activations, 'activate', qualification_id=qid, qualification_digest=qd) if ing is not None else {}
            resumed = ing.wake({'tick': 4}) if ing is not None else {}
            check(SH, 'an explicit activation resumes the edge and the kept pending request then settles',
                  again.get('outcome') == 'accepted' and resumed.get('outcome') == 'woken' and bool(settlement_of(ing, rid4)))

        # AC4: stale key or configuration bindings produce no authority.
        with section(SK):
            gate = ing.gate if ing is not None else None
            before = len(attempts)
            check(SK, 'an edge configured with another origin refuses as stale_configuration and reaches nothing',
                  gate is not None and refused_as(lambda: V.TelegramPresentationEdge(P, url2, 'bot73', activation=gate).send(chat, 'x'),
                                                  'stale_configuration') and calls('bot73', 'sendMessage', api2) == 0)
            check(SK, 'a token naming another bot refuses as stale_configuration after getMe',
                  gate is not None and refused_as(lambda: EV.TelegramAcquisitionEdge(P, url, 'other73', activation=gate).get_me(),
                                                  'stale_configuration'))
            wrong = IN.Ingress(gate, EV.Acquirer(A.S, A.CM, P, V, ing.presenter,
                                                 EV.TelegramAcquisitionEdge(P, url2, 'bot73', activation=gate), ing.conn,
                                                 'authority', A.journal_sign, 'telegram-edge', ing.acquirer.edge_sign),
                               ing.settlement) if ing is not None else None
            check(SK, 'a wake over an acquirer of another origin refuses as stale_configuration',
                  wrong is not None and wrong.wake({'tick': 5}).get('reason') == 'stale_configuration')
            rid6, sixth = A.open_request(ing, 'Q6') if ing is not None else (None, {})
            A.enroll_chat(chat)
            answer6 = H.deliver(api, 'bot73', owner_user, 'accept: stale enrollment', reply_to=(sixth.get('message_ids') or [None])[-1])
            woke = ing.wake({'tick': 6}) if ing is not None else {}
            check(SK, 'a changed chat enrollment refuses as stale_enrollment: nothing acquired or settled',
                  woke.get('reason') == 'stale_enrollment' and evidence_of(answer6) is None and pending(ing, rid6)
                  and settlement_of(ing, rid6) is None)
            A.edge_command('retire_channel_edge', {'channel': 'telegram_chat', 'edge_key_id': 'edge-telegram'})
            woke = ing.wake({'tick': 7}) if ing is not None else {}
            sends = calls('bot73', 'sendMessage')
            rid7, seventh = A.open_request(ing, 'Q7') if ing is not None else (None, {})
            check(SK, 'a retired edge key refuses as stale_key: no send, no acquisition, pending kept',
                  woke.get('reason') == 'stale_key' and gate is not None
                  and refused_as(lambda: ing.presenter.edge.send(chat, 'x'), 'stale_key')
                  and calls('bot73', 'sendMessage') == sends and pending(ing, rid6)
                  and pending(ing, rid7) and evidence_of(answer6) is None)
            halted = A.authorize(ing.activations, 'stop') if ing is not None else {}
            check(SK, 'a stale edge can still be stopped by the owner, and stays stopped',
                  halted.get('outcome') == 'accepted' and (ing.activations.current() or {}).get('state') == 'stopped'
                  and ing.wake({'tick': 8}).get('reason') == 'edge_stopped')
            check(SK, 'no connection beyond the loopback interface was attempted', len(attempts) == before)
            metrics = ing.activations.metrics() if ing is not None else {}
            observed = _v73_json.dumps(ing.gate.observations + ing.activations.observations) if ing is not None else ''
            check(SK, 'metrics and observations: counts, state and pending work, named refusals, no token or text',
                  metrics.get('accepted', 0) > 0 and metrics.get('refused', 0) > 0 and metrics.get('state') == 'stopped'
                  and metrics.get('pending') == ['telegram_chat']
                  and 'stand-in-token' not in observed and 'bot73' not in observed and 'stale enrollment' not in observed
                  and all(o.get('error_class') for o in ing.gate.observations if o.get('outcome') == 'refused'))
    finally:
        _v73_socket.create_connection = real_connect
        stop()
        stop2()
        if ing is not None:
            ing.conn.close()
        A.conn.close()
    return rows


_v73_started = _v73_time.monotonic()
_v73_fast = '/dev/shm' if _v73_os.path.isdir('/dev/shm') and _v73_os.access('/dev/shm', _v73_os.W_OK) else None
with _v73_temp.TemporaryDirectory(prefix='v73-', dir=_v73_fast) as _v73_dir:
    _v73_rows = _v73_checks(_v73_Path(_v73_dir))
for _v73_name, _v73_observed in _v73_rows.items():
    _v73_ok = bool(_v73_observed) and all(ok for _, ok in _v73_observed)
    if not _v73_ok:
        for _v73_label, _v73_one in _v73_observed:
            if not _v73_one:
                print('  VELDO-0073 %s detail: %s' % (_v73_name, _v73_label))
    expect('VELDO-0073 ' + _v73_name, _v73_ok)
# AC2's real-platform leg: fixtures cannot certify it. It is a row only once the live run is recorded.
_v73_live = ROOT.joinpath(*_V73_LIVE)
if _v73_live.is_file():
    _v73_act = _v73_load('v73_live_activation', ROOT.joinpath('.veldo', 'control_channel_activation.py'))
    _v73_text = _v73_live.read_text()
    _v73_doc = _v73_json.loads(_v73_text)
    _v73_record = _v73_doc.get('qualification') or {}
    expect('VELDO-0073 qualification/live-telegram',
           _v73_act.qualification_problems(_v73_record, _V73_TELEGRAM) == [] and _v73_record.get('platform') == 'telegram'
           and _v73_act.digest(_v73_record) == _v73_doc.get('qualification_digest')
           and not _v73_re.search(r'[0-9]{5,}:[A-Za-z0-9_-]{30,}', _v73_text))
else:
    print('VELDO-0073 qualification/live-telegram: PENDING the live run (%s is not recorded); not counted as passed'
          % '/'.join(_V73_LIVE))
print('VELDO-0073 suite seconds: %.3f' % (_v73_time.monotonic() - _v73_started))
