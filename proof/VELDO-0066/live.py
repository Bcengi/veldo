#!/usr/bin/env python3
"""VELDO-0066 AC1 live run: the real Acquirer against the Telegram Bot API, then a replay of the same bytes.

    python3 -B proof/VELDO-0066/live.py TOKEN_FILE SAVED_RESPONSE --owner-id ID [--out PATH]

TOKEN_FILE holds the token of the test bot the owner provided for this run. It is read here at run
time and is never printed, logged, written, put on a command line or passed to another process; an
error is reported by its type only, because a request URL carries the token. SAVED_RESPONSE is the
exact body of one getUpdates call made before this run with no parameters at all (no offset, so
nothing was confirmed to the platform), kept in a private scratch folder. ID is the owner's stable
Telegram user id, the enrollment an operator supplies; it is an argument so that no personal id is
written into the repository.

Pass A builds the suite's world (real SQLite store, OpenSSH signed journal, VELDO-0020 membership,
VELDO-0064 projection, VELDO-0065 presenter, edge key) with the owner enrolled as the one person
member whose Telegram chat is ID, and runs the production Acquirer once through the production
TelegramAcquisitionEdge against https://api.telegram.org: getMe, then getUpdates from the fresh
cursor's offset 0, which confirms nothing. Pass B builds a fresh world where the same person is a
member but nobody is enrolled, and runs the production Acquirer against a loopback Bot API: first a
text-only transcript of the same messages served as the getUpdates body, then pass A's live getMe
answer and the exact SAVED_RESPONSE bytes.

Bounds this driver enforces, not only states: the acquisition edge is the production class with one
guard around its request method that refuses any Bot API method other than getMe and getUpdates
before a request is made; the presenter's edge points at a loopback endpoint that publishes nothing
and counts every call. No webhook, deleteWebhook, logOut or sendMessage call is possible.

The stores keep each update as the platform delivered it, so they are created in new directories
beside SAVED_RESPONSE and nowhere else. The record written to --out holds field names, outcomes,
principals, platform counters and booleans: no message text, display name, username, chat title,
token, bot id, user id or raw update. Before writing, the driver checks the record against every
string value in the platform data, the token and both ids, and writes nothing if any appears.
"""
import argparse
import datetime
import hashlib
import http.server
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BOT_API = 'https://api.telegram.org'
PERMITTED = ('getMe', 'getUpdates')
REPLAY_TOKEN = 'replay-token'
# The owner's account of what he sent for this run, by the update ids the platform gave them. The
# opening bot command is the one the Telegram client sends when a chat with a bot is started.
OWNER_ACCOUNT = {575938980: 'opening bot command, sent by the client when the chat was started (not one of the three)',
                 575938981: 'message 1: a plain message',
                 575938982: 'message 2: sent after the owner changed his first name',
                 575938983: 'message 3: forwarded from another chat'}
PLAIN, RENAMED, FORWARD = 575938981, 575938982, 575938983
AUTOMATION_MARKERS = ('sender_chat', 'via_bot', 'sender_business_bot', 'is_from_offline', 'is_automatic_forward')
# Platform enumeration values the record names on purpose (chat, forward origin and entity types).
ENUMERATIONS = ('private', 'user', 'bot_command')


def _quiet_hook(kind, value, trace):
    print('live run failed: %s' % kind.__name__, file=sys.stderr)


def _quiet_thread_hook(args):
    print('live run thread failed: %s' % args.exc_type.__name__, file=sys.stderr)


sys.excepthook = _quiet_hook
threading.excepthook = _quiet_thread_hook


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    return subprocess.run(['git', '-C', str(ROOT)] + list(args), capture_output=True, text=True, env=env,
                          stdin=subprocess.DEVNULL, timeout=30)


def _serve(handler):
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, 'http://127.0.0.1:%d' % server.server_address[1]


class _Loopback(http.server.BaseHTTPRequestHandler):
    """A loopback Bot API endpoint. `state` holds its calls and what it serves."""
    state = None

    def log_message(self, *args):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
        _, _, rest = self.path.partition('/bot')
        token, _, method = rest.partition('/')
        try:
            body = json.loads(raw) if raw else {}
        except ValueError:
            body = None
        self.state['calls'].append({'method': method, 'parameters': body, 'token_is_replay': token == REPLAY_TOKEN})
        kind, code, payload = self.state['answer'](token, method)
        self.send_response(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def _publishes_nothing(token, method):
    return ('application/json', 403, json.dumps({'ok': False, 'error_code': 403,
                                                 'description': 'Forbidden: this run publishes nothing'}).encode())


def world(base, owner_id, enroll_owner, edge_factory, presenter_url):
    """The suite's world in `base`: store, membership, projection, presenter, edge key and, when
    `enroll_owner`, the owner's Telegram enrollment at his stable user id. Returns the modules, the
    connection and the production Acquirer over the edge `edge_factory(A, P)` builds."""
    organs = base / 'organs'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        shutil.copyfile(source, organs / source.name)
    claims = _load('live66_claims_%s' % base.name, organs / 'control_claim.py')
    S, CM, AUTHC = claims.S, claims.CM, claims.AC
    I = _load('live66_inbox_%s' % base.name, organs / 'control_assignment.py')
    P = _load('live66_projection_%s' % base.name, organs / 'control_channel_projection.py')
    V = _load('live66_presentation_%s' % base.name, organs / 'control_channel_presentation.py')
    contract = _load('live66_contract_%s' % base.name, organs / 'entity_contract.py')
    # The production copy, exactly as the suite loads it.
    A = _load('live66_attribution_%s' % base.name, ROOT / '.veldo' / 'control_channel_attribution.py')

    keys = base / 'keys'
    keys.mkdir()
    public = {}
    for who in ('authority', 'owner', 'telegram-edge'):
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'live66-' + who, '-f', str(keys / who)],
                       check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=10)
        public[who] = (keys / (who + '.pub')).read_text().strip()

    def sign_as(who, message, namespace):
        return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys / who), '-n', namespace], input=message,
                              capture_output=True, check=True, timeout=10).stdout.decode()

    def journal_sign(message):
        return sign_as('authority', message, 'veldo-journal')

    def edge_sign(message):
        return sign_as('telegram-edge', message, AUTHC.SIGNATURE_NAMESPACE)

    ids = dict(domain_uuid='live-domain', repository_uuid='live-repository', store_uuid='live-store')
    conn = S.open_store(str(base / 'authority' / 'control.sqlite3'))
    serial = [0]

    def fixture(eid, kind, data):
        serial[0] += 1
        current = S.materialized_state(conn)['entities']
        return S.execute(conn, dict(command_id='fixture-%d' % serial[0], principal='authority', operation='upsert_entity',
                                    parameters=dict(entity_id=eid, kind=kind, data=data),
                                    expected_versions={eid: current.get(eid, {}).get('version', 0)}, artifact_digests=[],
                                    nonce='fixture-n-%d' % serial[0]), 'authority', journal_sign, 1)

    fixture('owner', 'membership', dict(principal_type='person', roles=['project_owner'], scope=['project-a'],
                                        revoked_at=None, expires_at=None))
    fixture('telegram-edge', 'membership', dict(principal_type='service', roles=[], scope=['project-a'],
                                                revoked_at=None, expires_at=None))
    fixture('key-owner', 'verification_key', dict(principal='owner', public_key=public['owner'], effective_at=0))
    fixture(AUTHC.CHANNELS['telegram_chat']['edge_key_id'], 'verification_key',
            dict(principal='telegram-edge', public_key=public['telegram-edge'], effective_at=0))
    if enroll_owner:
        # The enrollment id is spelled here, as the suite spells it, not taken from a module under test.
        fixture('channel-enrollment:telegram_chat:owner', 'channel_enrollment',
                dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='owner', chat_id=owner_id,
                     revoked_at=None))

    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', journal_sign)
    presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, presenter_url, 'publishes-nothing'), conn,
                            'authority', journal_sign, assignment=I)
    edge = edge_factory(A, P)
    acquirer = A.Acquirer(S, CM, P, V, presenter, edge, conn, 'authority', journal_sign, 'telegram-edge', edge_sign)
    return {'A': A, 'P': P, 'conn': conn, 'edge': edge, 'acquirer': acquirer}


def guarded_edge(A, P, base_url, token):
    """The production TelegramAcquisitionEdge, with a guard around its request method that refuses
    any method but getMe and getUpdates before a request is made, and keeps what was asked and the
    answer bytes in memory."""
    class Guarded(A.TelegramAcquisitionEdge):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.calls, self.bodies = [], {}

        def _call(self, method, payload):
            if method not in PERMITTED:
                raise RuntimeError('this run calls only getMe and getUpdates')
            self.calls.append({'method': method, 'parameters': json.loads(json.dumps(payload))})
            result, body = super()._call(method, payload)
            self.bodies[method] = body
            return result, body
    return Guarded(P, base_url, token)


def decisions(built, bot_id, update_ids):
    """Each update's evidence decision in this store: outcome, named refusal and principal."""
    A, acquirer = built['A'], built['acquirer']
    found = {}
    for uid in update_ids:
        record = acquirer.evidence(A.evidence_id(bot_id, uid))
        found[uid] = None if record is None else {'outcome': record.get('outcome'), 'reason': record.get('reason'),
                                                  'principal': record.get('principal'),
                                                  'source_digest': record.get('source_digest'),
                                                  'fields': record.get('fields')}
    return found


def answers(built):
    return built['conn'].execute("SELECT count(*) FROM entities WHERE kind='presentation_answer'").fetchone()[0]


def string_leaves(value, out):
    if isinstance(value, dict):
        for v in value.values():
            string_leaves(v, out)
    elif isinstance(value, list):
        for v in value:
            string_leaves(v, out)
    elif isinstance(value, str):
        out.add(value)
    return out


def carries(text, secrets):
    """Whether `text` carries any of `secrets`: long ones anywhere, ignoring case; short ones as a
    whole JSON string."""
    low = text.lower()
    return any((s.lower() in low) if len(s) >= 4 else ('"%s"' % s) in text for s in secrets if s)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('token_file')
    parser.add_argument('saved_response')
    parser.add_argument('--owner-id', type=int, required=True)
    parser.add_argument('--out', default=str(ROOT / 'proof' / 'VELDO-0066' / 'live-2026-09-24.json'))
    args = parser.parse_args(argv)

    with open(args.token_file, encoding='utf-8') as handle:
        token = handle.read().strip()
    if ':' not in token:
        print('the token file does not hold a Bot API token', file=sys.stderr)
        return 2
    saved_path = Path(args.saved_response).resolve()
    saved = saved_path.read_bytes()
    saved_answer = json.loads(saved)
    if saved_answer.get('ok') is not True or not isinstance(saved_answer.get('result'), list):
        print('the saved response is not a successful getUpdates answer', file=sys.stderr)
        return 2
    saved_updates = {u['update_id']: u for u in saved_answer['result']}
    stamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-%d' % os.getpid()
    base_a, base_b = saved_path.parent / ('live-run-%s-a' % stamp), saved_path.parent / ('live-run-%s-b' % stamp)
    base_a.mkdir(mode=0o700)
    base_b.mkdir(mode=0o700)

    publish_state = {'calls': [], 'answer': _publishes_nothing}
    publish_server, publish_url = _serve(type('Publishes', (_Loopback,), {'state': publish_state}))
    replay_state = {'calls': [], 'mode': 'transcript', 'getme': b'', 'transcript': b''}

    def replay_answer(tok, method):
        if tok != REPLAY_TOKEN or method not in PERMITTED:
            return ('application/json', 404, b'{"ok":false,"error_code":404,"description":"Not Found"}')
        if method == 'getMe':
            return ('application/json', 200, replay_state['getme'])
        if replay_state['mode'] == 'transcript':
            return ('text/plain; charset=utf-8', 200, replay_state['transcript'])
        return ('application/json', 200, saved)
    replay_state['answer'] = replay_answer
    replay_server, replay_url = _serve(type('Replay', (_Loopback,), {'state': replay_state}))

    try:
        # Pass A: live, the owner enrolled at his stable id.
        a = world(base_a, args.owner_id, True, lambda A, P: guarded_edge(A, P, BOT_API, token), publish_url)
        results_a = a['acquirer'].acquire()
        edge_a = a['edge']
        if 'getMe' not in edge_a.bodies:
            print('pass A: getMe gave no readable answer: %s' % [r.get('reason') for r in results_a], file=sys.stderr)
            return 1
        me = json.loads(edge_a.bodies['getMe'])['result']
        bot_id = me['id']
        live_body = edge_a.bodies.get('getUpdates')
        live_updates = {u['update_id']: u for u in (json.loads(live_body)['result'] if live_body else [])}
        update_ids = sorted(set(saved_updates) | set(live_updates))
        found_a = decisions(a, bot_id, update_ids)

        # Pass B: a fresh store, nobody enrolled, the same bytes over loopback. First a text-only
        # transcript of the same messages, then pass A's getMe answer and the saved getUpdates bytes.
        replay_state['getme'] = edge_a.bodies['getMe']
        replay_state['transcript'] = ''.join(
            '%s: %s\n' % ((u['message'].get('from') or {}).get('first_name'), u['message'].get('text'))
            for u in saved_answer['result'] if isinstance(u.get('message'), dict)).encode('utf-8')
        b = world(base_b, args.owner_id, False,
                  lambda A, P: guarded_edge(A, P, replay_url, REPLAY_TOKEN), publish_url)
        transcript_results = b['acquirer'].acquire()
        transcript_kept = b['conn'].execute("SELECT count(*) FROM entities WHERE kind='channel_evidence'").fetchone()[0]
        replay_state['mode'] = 'saved'
        results_b = b['acquirer'].acquire()
        found_b = decisions(b, bot_id, update_ids)
    finally:
        publish_server.shutdown()
        publish_server.server_close()
        replay_server.shutdown()
        replay_server.server_close()

    A = a['A']
    # Observations name the bot id by design (bot_id and evidence ids), and a token begins with it, so
    # they are checked for the whole token and its secret part after the colon.
    token_secret = {token, token.split(':', 1)[1]}
    secrets = string_leaves(saved_answer, set()) | string_leaves(list(live_updates.values()), set()) | string_leaves(me, set())
    secrets = {s for s in secrets if s not in ENUMERATIONS}
    secrets |= {token, token[:8], token.split(':', 1)[0], str(bot_id), str(args.owner_id)}
    names = string_leaves([[u.get('message', {}).get(k) for k in ('from', 'chat', 'forward_origin', 'forward_from')]
                           for u in list(saved_updates.values()) + list(live_updates.values())], set())
    names -= set(ENUMERATIONS)
    texts = {u.get('message', {}).get('text') for u in list(saved_updates.values()) + list(live_updates.values())} - {None}

    per_update = []
    for uid in update_ids:
        update = saved_updates.get(uid) or live_updates[uid]
        kinds = [k for k in update if k != 'update_id']
        message = update.get(kinds[0]) if len(kinds) == 1 and isinstance(update.get(kinds[0]), dict) else {}
        fields = A.platform_fields(update)
        sender, chat = message.get('from') or {}, message.get('chat') or {}
        origin = message.get('forward_origin') if isinstance(message.get('forward_origin'), dict) else None
        da, db = found_a.get(uid), found_b.get(uid)
        entry = {
            'update_id': uid, 'message_id': fields['message_id'],
            'sent_utc': (datetime.datetime.fromtimestamp(fields['date'], datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                         if fields['date'] is not None else None),
            'owner_account': OWNER_ACCOUNT.get(uid, 'not in the owner\'s account of this run'),
            'in_saved_response': uid in saved_updates, 'in_live_response': uid in live_updates,
            'update_type': kinds[0] if len(kinds) == 1 else None,
            'message_field_names': sorted(message),
            'entity_types': sorted({e.get('type') for e in message.get('entities') or [] if isinstance(e, dict)}),
            'canonical_fields_present': {f: fields[f] is not None for f in A.CANONICAL_FIELDS},
            'required_fields_missing': A.missing_fields(fields),
            'automation_markers_present': [f for f in AUTOMATION_MARKERS if f in message],
            'automation_reason_found': A.automation_reason(message) is not None,
            'forward_fields_present': [f for f in A.FORWARD_FIELDS if f in message],
            'is_forward': A.is_forward(message),
            'sender_is_person_account': sender.get('is_bot') is False,
            'sender_is_owner_stable_id': sender.get('id') == args.owner_id,
            'private_chat_of_sender': chat.get('type') == 'private' and chat.get('id') == sender.get('id'),
            'pass_a': None if da is None else {k: da[k] for k in ('outcome', 'reason', 'principal')},
            'pass_b': None if db is None else {k: db[k] for k in ('outcome', 'reason', 'principal')},
            'same_evidence_in_both_passes': (da is not None and db is not None and da['source_digest'] == db['source_digest']
                                             and da['fields'] == db['fields']),
            'evidence_fields_hold_no_name_or_text': all(
                d is None or not any(v in names | texts for v in d['fields'].values() if isinstance(v, str))
                for d in (da, db)),
        }
        if origin is not None:
            origin_user = origin.get('sender_user') if isinstance(origin.get('sender_user'), dict) else {}
            entry['forward'] = {
                'origin_type': origin.get('type'),
                'origin_is_the_sender_himself': origin_user.get('id') == sender.get('id'),
                'evidence_sender_is_the_message_sender': da is not None and da['fields']['sender_id'] == sender.get('id'),
                'attributed_to_anyone': any(d is not None and d['principal'] is not None for d in (da, db)),
            }
        per_update.append(entry)

    def first_name(uid):
        update = saved_updates.get(uid) or live_updates.get(uid) or {}
        return ((update.get('message') or {}).get('from') or {}).get('first_name')

    listed = [uid for uid in (PLAIN, RENAMED) if uid in found_a and found_a[uid] is not None]
    rename = {
        'updates': [PLAIN, RENAMED],
        'first_name_differ': first_name(PLAIN) != first_name(RENAMED),
        'first_names_identical_across_all_updates': len({first_name(uid) for uid in update_ids}) == 1,
        'pass_a_same_principal': (len(listed) == 2 and found_a[PLAIN]['principal'] is not None
                                  and found_a[PLAIN]['principal'] == found_a[RENAMED]['principal']),
        'pass_a_principal': found_a[PLAIN]['principal'] if PLAIN in listed else None,
    }
    record = {
        'specification': 'VELDO-0066', 'criterion': 'AC1', 'run': 'live Telegram Bot API, 2026-09-24',
        'ran_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'tree': {'head': _git('rev-parse', 'HEAD').stdout.strip(),
                 'attribution_module_sha256': hashlib.sha256((ROOT / '.veldo' / 'control_channel_attribution.py').read_bytes()).hexdigest(),
                 'attribution_module_matches_head': _git('diff', '--quiet', 'HEAD', '--', '.veldo/control_channel_attribution.py').returncode == 0},
        'platform': {
            'endpoint': BOT_API,
            'bot': 'the test bot the owner provided for this run; its id is withheld because a Bot API token begins with it',
            'getme_is_a_bot': me.get('is_bot') is True,
            'getme_id_is_the_bot_the_token_names': str(bot_id) == token.split(':', 1)[0],
        },
        'saved_response': {'how': 'one getUpdates call with no parameters (no offset, so nothing confirmed), before pass A',
                           'bytes': len(saved), 'sha256': hashlib.sha256(saved).hexdigest(),
                           'update_ids': sorted(saved_updates)},
        'pass_a': {
            'store': 'fresh; the owner enrolled at his stable Telegram user id as the one person member',
            'bot_api_calls': edge_a.calls,
            'live_update_ids': sorted(live_updates),
            'live_response_identical_to_saved': live_body == saved,
            'acquire_refusals': [r.get('reason') for r in results_a if r.get('update_id') is None],
            'metrics': a['acquirer'].metrics(),
            'answers_recorded': answers(a),
            'observations_hold_no_text_name_or_token': not carries(json.dumps(a['acquirer'].observations),
                                                                   names | texts | token_secret),
        },
        'pass_b': {
            'store': 'fresh; the same person is a member, nobody is enrolled',
            'transcript_probe': {'served': 'a text-only transcript of the same messages as the getUpdates body',
                                 'results': [[r.get('outcome'), r.get('reason')] for r in transcript_results],
                                 'evidence_kept': transcript_kept},
            'bot_api_calls': [c for c in replay_state['calls']],
            'acquire_refusals': [r.get('reason') for r in results_b if r.get('update_id') is None],
            'metrics': b['acquirer'].metrics(),
            'answers_recorded': answers(b),
            'every_update_refused_none_attributed': all(
                found_b.get(uid) is not None and found_b[uid]['outcome'] == 'refused' and found_b[uid]['principal'] is None
                for uid in saved_updates),
            'observations_hold_no_text_name_or_token': not carries(json.dumps(b['acquirer'].observations),
                                                                   names | texts | token_secret),
        },
        'presenter_edge_calls_in_both_passes': len(publish_state['calls']),
        'updates': per_update,
        'rename': rename,
        'privacy': 'no message text, display name, username, chat title, token, bot id, user id or raw update; '
                   'checked by the driver against every string value in the platform data before writing',
    }
    for call in record['pass_b']['bot_api_calls']:
        call.pop('token_is_replay', None)
    text = json.dumps(record, indent=2, sort_keys=False) + '\n'
    if carries(text, secrets):
        print('the record would carry platform text, a name, an id or the token: nothing written', file=sys.stderr)
        return 1
    Path(args.out).write_text(text, encoding='ascii')
    print('written %s (%d bytes); stores in %s and %s' % (args.out, len(text), base_a.name, base_b.name))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
