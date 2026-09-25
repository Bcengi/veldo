#!/usr/bin/env python3
"""The VELDO-0073 live qualification run: one decision through the real Telegram edge, with the owner.

    python3 -B proof/VELDO-0073/qualify_live.py --token-file /abs/path/to/bot-token --owner-chat <his user id>

Run it ONCE, by the lead, with the owner at his phone (the owner approved the test bot sending him
messages for this run, Telegram 29081). It contacts https://api.telegram.org and nothing else. It never
prints, logs or writes the token: the token is read from its file (which must be the account's own 0600
file) into memory, and the ingress host configuration names that same file, so no copy of the token is
ever written. Every message printed has the token masked.

WHAT IT DOES, IN ORDER.
 1. Builds a fresh authority in a private work directory (scripts/suites/support/v73_authority.py):
    signed store, membership, the owner's chat enrollment at --owner-chat, the VELDO-0067 edge key and
    the ingress host configuration naming the Telegram origin.
 2. Constructs the activated ingress with the production construction (control_channel_ingress.
    open_ingress) and records the owner-signed qualification run (the qualify action) for the Telegram
    origin. Before this record the edge refuses everything; the run lasts at most 15 minutes.
 3. Opens one decision request and presents it: ONE real sendMessage to the owner's chat.
 4. Polls: each tick is a notification that only wakes canonical getUpdates acquisition. The owner
    replies to the message in Telegram with `accept: <his reason>` (or reject, or
    return_for_elaboration). The reply is attributed by its platform sender, message, chat and time,
    signed by the protected signer and settled by the production settlement service.
 5. The unauthorized actor: the owner has no second person (Telegram 29047), so one update from an
    unenrolled sender id is acquired from a loopback stand-in and refused as unknown_sender; the record
    marks its provenance `stand_in`.
 6. Records the qualification (control_channel_activation.Activations.qualify): refused by name unless
    every presentation, answer and settlement exchange was made with api.telegram.org over TLS verified
    against this host's compiled-in trust store with a certificate naming that host, and the answer
    evidence is the bytes of a recorded getUpdates answer. Then the owner's signed activation names the
    record, the gate is asked (no message is sent), and an explicit stop leaves the run's edge stopped.
 7. Writes proof/VELDO-0073/live/qualification.json: the qualification record (identities, digests,
    TLS peer facts, no message text, no names, no token), its digest, the activation and stop states,
    the settlement's choice and ruling, the commit and this runner's digest. The suite's
    qualification/live-record-consistent row checks its consistency (not its provenance); until it
    exists that row is PENDING.

REHEARSAL. `--rehearse --out <dir>` runs the same steps against a loopback stand-in Bot API instead,
with the owner's reply delivered by the stand-in; it contacts nothing, needs no token file, and its
record is a stand-in record (platform `stand_in`) that the live row refuses. It exists so the runner
itself is exercised before the one live run.

Exit status: 0 recorded; 2 the presentation was not published; 3 no answer within --wait seconds;
4 qualification, activation or stop refused (the reason is printed); 5 anything else (type printed).
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TELEGRAM = 'https://api.telegram.org'
# The rehearsal stand-in's bot name; not a credential.
REHEARSAL = 'rehearsal'
sys.path.insert(0, str(ROOT / 'scripts' / 'suites' / 'support'))
import v73_authority as H  # noqa: E402


class Masked(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description='VELDO-0073 live qualification with the owner (contacts Telegram)')
    parser.add_argument('--token-file', help='absolute path of the 0600 file holding the bot token')
    parser.add_argument('--rehearse', action='store_true', help='run against a loopback stand-in (contacts nothing)')
    parser.add_argument('--owner-chat', required=True, type=int, help='the owner\'s Telegram user id (his private chat id)')
    parser.add_argument('--wait', type=int, default=600, help='seconds to wait for his reply (at most 840)')
    parser.add_argument('--out', default=str(HERE / 'live'), help='where qualification.json is written')
    args = parser.parse_args()
    IN = H.load('live_ingress', ROOT / '.veldo' / 'control_channel_ingress.py')
    if args.rehearse:
        if Path(args.out).resolve() == (HERE / 'live').resolve():
            print('a rehearsal never writes the live record: pass --out', flush=True)
            return 5
        token = REHEARSAL
    else:
        if not args.token_file:
            print('--token-file is required for the live run', flush=True)
            return 5
        try:
            token = IN.read_token(os.path.abspath(args.token_file))
        except IN.Refused as exc:
            print('the token file is refused: %s' % exc.detail, flush=True)
            return 5
    work = Path(tempfile.mkdtemp(prefix='veldo-0073-live-'))

    def say(text):
        print(str(text).replace(token, '[token]'), flush=True)
    try:
        return run(args, token, work, say)
    except Masked as exc:
        say(str(exc))
        return 4
    except Exception as exc:  # noqa: BLE001 - the type is printed, never the message, which may carry the URL
        say('failed: %s' % type(exc).__name__)
        return 5
    finally:
        # A rehearsal's stand-in name file (the live run writes no token file).
        copy = work / 'authority' / 'host' / 'bot-token'
        if copy.is_file():
            os.unlink(str(copy))


def run(args, token, work, say):
    organs = ROOT / '.veldo'
    origin, rehearsal = TELEGRAM, None
    if args.rehearse:
        owner_user = {'id': args.owner_chat, 'is_bot': False, 'first_name': 'Owner'}
        origin, rehearsal, stop_rehearsal = H.stand_in({token: {'id': 8000000099, 'is_bot': True, 'first_name': 'Rehearsal'}})
        rehearsal['chats'][args.owner_chat] = {'id': args.owner_chat, 'type': 'private', 'first_name': 'Owner'}
    A = H.build(work / 'authority', organs, args.owner_chat, origin, token,
                token_path=None if args.rehearse else os.path.abspath(args.token_file))
    IN = H.load('live_ingress_run', organs / 'control_channel_ingress.py')
    ACT = H.load('live_activation', organs / 'control_channel_activation.py')
    EV = H.load('live_attribution', organs / 'control_channel_attribution.py')
    P = H.load('live_projection', organs / 'control_channel_projection.py')
    V = H.load('live_presentation', organs / 'control_channel_presentation.py')
    ing = IN.open_ingress(str(A.config_path))
    opened = A.authorize(ing.activations, 'qualify')
    if opened.get('outcome') != 'accepted':
        raise Masked('the qualification run was refused: %s' % opened.get('reason'))
    alias = 'LIVE-%d' % int(time.time())
    rid, receipt = A.open_request(ing, alias)
    if receipt.get('outcome') != 'published':
        say('the decision was not published: %s %s' % (receipt.get('outcome'), receipt.get('refusal')))
        return 2
    say('Sent one decision to chat %d (message %s). Reply to THAT message in Telegram with:  accept: <your reason>'
        % (args.owner_chat, receipt.get('message_ids')))
    if rehearsal is not None:
        H.deliver(rehearsal, token, owner_user, 'accept: a rehearsal', reply_to=receipt['message_ids'][-1])
    deadline = time.time() + min(args.wait, 840)
    owner = None
    while time.time() < deadline and owner is None:
        woke = ing.wake({'source': 'qualify_live', 'at': time.time()})
        for row in woke.get('acquired', []):
            say('update %s: %s %s' % (row.get('update_id'), row.get('outcome'), row.get('reason') or ''))
            if row.get('outcome') == 'answered' and row.get('request_id') == rid:
                owner = row
        if woke.get('outcome') != 'woken':
            raise Masked('wake refused: %s' % woke.get('reason'))
        if owner is None:
            time.sleep(3)
    if owner is None:
        say('no answer within the wait; nothing recorded')
        return 3
    settled = ing.settlement.settlement(rid, 1) or {}
    say('settled: %s (%s)' % (settled.get('choice'), settled.get('ruling')))
    evidence = ing.acquirer.evidence(owner['evidence_id']) or {}
    bot = evidence.get('bot_id')
    # The unauthorized actor: an update from an unenrolled sender id, acquired from a loopback stand-in of
    # the same bot, after every real update (Telegram 29047: the owner has no second person).
    url, api, stop = H.stand_in({'stand-in': {'id': bot, 'is_bot': True, 'first_name': 'stand-in'}})
    try:
        api['bots']['stand-in']['update_next'] = evidence.get('update_id', 0) + 1000
        stranger = {'id': args.owner_chat + 1, 'is_bot': False, 'first_name': 'Unenrolled'}
        update = H.deliver(api, 'stand-in', stranger, 'accept: an unenrolled sender')
        standin = EV.Acquirer(A.S, A.CM, P, V, ing.presenter, EV.TelegramAcquisitionEdge(P, url, 'stand-in'), ing.conn,
                              'authority', A.journal_sign, 'telegram-edge', ing.acquirer.edge_sign)
        refused = {r.get('update_id'): r.get('reason') for r in standin.acquire()}
    finally:
        stop()
    say('unenrolled sender: %s' % refused.get(update['update_id']))
    try:
        qid, qd, record = ing.activations.qualify(ing.gate, ing.presenter, ing.acquirer, ing.settlement, rid,
                                                  owner['evidence_id'], EV.evidence_id(bot, update['update_id']))
    except Exception as exc:
        raise Masked('qualification refused: %s' % getattr(exc, 'code', type(exc).__name__)) from None
    activated = A.authorize(ing.activations, 'activate', qualification_id=qid, qualification_digest=qd)
    if activated.get('outcome') != 'accepted':
        raise Masked('activation refused: %s' % activated.get('reason'))
    ing.gate.admit('getUpdates', origin)
    active = ing.activations.current()
    stopped = A.authorize(ing.activations, 'stop')
    if stopped.get('outcome') != 'accepted':
        raise Masked('stop refused: %s' % stopped.get('reason'))
    git = H.load('live_git', organs / 'git_process.py')
    commit = git.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    document = {'schema': 'veldo.proof-live-qualification/v1', 'spec_id': 'VELDO-0073',
                'recorded_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'commit': commit, 'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'qualification_id': qid, 'qualification_digest': qd, 'qualification': record,
                'journal': [o for o in ing.activations.observations if o.get('operation') == ACT.QUALIFY],
                'activation': {k: active.get(k) for k in ('state', 'origin', 'platform', 'bot_id', 'qualification_id',
                                                          'qualification_digest', 'edge_key_id', 'enrollment_version')},
                'stopped': (ing.activations.current() or {}).get('state'),
                'settlement': {k: settled.get(k) for k in ('settlement_id', 'choice', 'ruling', 'originating_channel')},
                'unauthorized_provenance': record['unauthorized']['provenance'],
                'note': 'Real platform legs: presentation, answer and settlement, each exchange with api.telegram.org over '
                        'verified TLS. The unauthorized leg is an unenrolled sender id from a loopback stand-in '
                        '(Telegram 29047).'}
    text = json.dumps(document, indent=1, sort_keys=True) + '\n'
    if token in text:
        raise Masked('refusing to write: the record would carry the token')
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'qualification.json').write_text(text)
    say('recorded %s (qualification %s); the run\'s edge is left stopped' % (out / 'qualification.json', qd))
    if rehearsal is not None:
        stop_rehearsal()
    return 0


if __name__ == '__main__':
    sys.exit(main())
