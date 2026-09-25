"""VELDO-0075: andon stops, their Telegram notice and their authorized resumption, over a real signed store.

Run: python3 scripts/selftest.py --suite 72_veldo_0075_andon

Only shared ROOT and expect are consumed. The authority is real (scripts/suites/support/v73_authority.py):
SQLite store, OpenSSH signatures on every command and journal record, membership with a worker (an agent
run with no role), a service without roles, the owner and a steward, the owner's chat enrollment, the
VELDO-0067 edge key and the actual protected signer process. The ingress is the production construction
(control_channel_ingress.open_ingress) from a host configuration of 0600 files, qualified and activated by
the owner's signed VELDO-0073 commands; the andon service signs with its own enrolled key. Every Bot API
exchange goes to a loopback stand-in in the platform's documented shapes, and a socket guard installed for
the whole suite refuses and counts every connection to anything but the loopback interface, so no row and
no mutant can reach Telegram, and no real token file is read. Execution units and one dispatch record of
unknown outcome are laid as store fixtures; every stop, notice, answer, settlement and resumption goes
through the real signed commands. Mutation workers replace the production copies named in PRODUCTION
below, never assertions or fixtures. Where the andon module is absent (the pre-change tree, for the red
record) every row asserts its named interface and fails by its own assertions. AC2's real-Telegram leg is
run by the lead with the owner through the running factory (VELDO-0138); it is reported PENDING here and
never counted as passed. No private key byte, signature or token is printed or retained.
"""
import importlib.util as _v75_import
import json as _v75_json
from pathlib import Path as _v75_Path
import shutil as _v75_shutil
import socket as _v75_socket
import subprocess as _v75_sp
import tempfile as _v75_temp
import time as _v75_time

_V75_ROWS = ('install/assets', 'stop/any-authenticated-requester', 'stop/unauthenticated-refused',
             'notice/each-stop-kind', 'notice/new-version-same-status', 'resume/acknowledgement-grants-nothing',
             'resume/stale-or-wrong-actor', 'resume/owner-settlement-fresh-contract', 'resume/unknown-effect-stays-stopped',
             'observability/named-refusals')
# Every enabled stop point by the unit states it interrupts (entity_contract's edges into AWAITING_AUTHORITY).
_V75_POINTS = (('build', 'DISPATCHING'), ('build', 'RUNNING'), ('build', 'VERIFYING'), ('review', 'REVIEWING'),
               ('coordination', 'CLAIMED'), ('coordination', 'READY_TO_LAND'), ('coordination', 'LANDING'))


def _v75_load(name, path):
    spec = _v75_import.spec_from_file_location(name, path)
    module = _v75_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _v75_checks(base):
    rows = {name: [] for name in _V75_ROWS}

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

    IA, RA, RU, NE, NV, RK, RW, RF, RX, OB = _V75_ROWS
    # The production copies under test; mutation workers replace exactly these paths.
    PRODUCTION = {'control_andon.py': ROOT / ".veldo" / "control_andon.py"}
    scaffold_path = ROOT / ".veldo" / "init_scaffold.py"
    organs = base / 'installed'
    organs.mkdir()
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        _v75_shutil.copyfile(source, organs / source.name)
    for name, source in PRODUCTION.items():
        target = organs / name
        if target.exists():
            target.unlink()
        if _v75_Path(source).is_file():
            _v75_shutil.copyfile(source, target)
    H = _v75_load('v75_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')

    with section(IA):
        scaffold = _v75_load('v75_scaffold', scaffold_path)
        rel = '.veldo/control_andon.py'
        both = (ROOT / rel).is_file() and (ROOT / 'engine' / rel).is_file()
        check(IA, rel + ' installed by the scaffold', rel in scaffold._FILES)
        check(IA, rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
        check(IA, rel + ' engine copy identical', both and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
        if both and rel in scaffold._FILES:
            scaffold._lay(ROOT / 'engine' / rel, base / 'laid' / rel, rel, [], [])
        check(IA, rel + ' laid by the installer', (base / 'laid' / rel).is_file()
              and (base / 'laid' / rel).read_bytes() == (ROOT / rel).read_bytes())

    AND = _v75_load('v75_andon', organs / 'control_andon.py') if (organs / 'control_andon.py').is_file() else None
    IN = _v75_load('v75_ingress', organs / 'control_channel_ingress.py')
    EV = _v75_load('v75_attribution', organs / 'control_channel_attribution.py')

    # The socket guard: nothing but the loopback interface is reached, and every other attempt is counted.
    attempts = []
    real_connect = _v75_socket.create_connection

    def guarded(address, *args, **kwargs):
        if address[0] != '127.0.0.1':
            attempts.append(address[0])
            raise OSError('suite guard: no network beyond the loopback interface')
        return real_connect(address, *args, **kwargs)
    _v75_socket.create_connection = guarded

    owner_user = {'id': 5580075, 'is_bot': False, 'first_name': 'Owner'}
    stranger = {'id': 5589975, 'is_bot': False, 'first_name': 'Stranger'}
    bot_user = {'id': 8000000075, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_andon_bot'}
    url, api, stop = H.stand_in({'bot75': bot_user})
    chat = owner_user['id']
    api['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': 'Owner'}
    A = H.build(base / 'authority', organs, chat, url, 'bot75')
    ids = A.ids
    bot = api['bots']['bot75']
    ing = None
    try:
        # The worker (an agent run holding no role) and the andon service, each enrolled with its own key.
        for who, kind in (('worker', 'agent_run'), ('andon', 'service')):
            path = base / 'authority' / ('key-' + who)
            _v75_sp.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v75-' + who, '-f', str(path)],
                        check=True, capture_output=True, timeout=10, stdin=_v75_sp.DEVNULL)
            A.keyfile[who] = path
            A.public[who] = ' '.join(path.with_name(path.name + '.pub').read_text().split()[:2])
            A.admin('steward', 'enroll_principal', {'principal': who, 'principal_type': kind, 'roles': [],
                                                    'public_key': A.public[who], 'independence_group': who,
                                                    'scope': ['project-a']}, enrollee=who)

        def unit(uid, state):
            A.fixture(uid, 'execution_unit', {'unit_id': uid, 'state': state, 'repository_uuid': ids['repository_uuid'],
                                              'station_contract': None})
            return uid

        def entity(eid):
            row = A.conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
            return None if row is None else {'kind': row[0], 'version': row[1], 'data': _v75_json.loads(row[2])}

        def unit_state(uid):
            return ((entity(uid) or {}).get('data') or {}).get('state')

        def sends():
            return api['calls'].count('sendMessage')

        def message(mid):
            return bot['messages'].get((chat, mid)) or {}

        def signed(who, body, signer=None):
            return {'command': body, 'signature': A.sign_as(signer or who, A.S.canonical_bytes(body))}

        def raise_packet(who, uid, station, reason, effect='clean', roles=('project_owner',), signer=None):
            body = dict(ids, operation='raise', principal=who, command_id=A.next_id('raise'),
                        nonce=A.next_id('raise-nonce'), unit=uid, station=station, reason=reason,
                        resolving={'principal': 'owner', 'roles': list(roles)}, effect=effect)
            return signed(who, body, signer)

        def revise_packet(who, sid, reason):
            return signed(who, dict(ids, operation='revise', principal=who, command_id=A.next_id('revise'),
                                    nonce=A.next_id('revise-nonce'), stop_id=sid, reason=reason))

        # The production ingress, qualified and activated by the owner's own signed VELDO-0073 commands.
        ing = IN.open_ingress(str(A.config_path))
        acts = ing.activations
        A.authorize(acts, 'qualify')
        rid0, first = A.open_request(ing, 'Q75')
        owner0 = H.deliver(api, 'bot75', owner_user, 'accept: the activation run qualifies',
                           reply_to=(first.get('message_ids') or [None])[-1])
        stranger0 = H.deliver(api, 'bot75', stranger, 'accept: I am not enrolled')
        ing.wake({'tick': 0})
        qid, qd, _record = acts.qualify(ing.gate, ing.presenter, ing.acquirer, ing.settlement, rid0,
                                        EV.evidence_id(bot_user['id'], owner0['update_id']),
                                        EV.evidence_id(bot_user['id'], stranger0['update_id']))
        A.authorize(acts, 'activate', qualification_id=qid, qualification_digest=qd)
        activated = (acts.current() or {}).get('state') == 'active'

        andon = None
        if AND is not None:
            andon = AND.Andon(ing, AND.service_signer('andon', str(A.keyfile['andon'])), scope='project-a')

        def raise_stop(packet):
            return andon.raise_stop(packet) if andon is not None else {}

        def stop_of(sid):
            return (andon.stop(sid) if andon is not None and sid else None) or {}

        def notices_of(sid):
            return andon.notices(sid) if andon is not None and sid else []

        def resume(sid):
            return andon.resume(sid) if andon is not None and sid else {}

        def reply(sid, text, version=None, sender=owner_user):
            """The owner (or `sender`) replies in Telegram to the stop's notice of `version` (the newest by default)."""
            kept = sorted(notices_of(sid), key=lambda n: n.get('request_version') or 0)
            if version is not None:
                kept = [n for n in kept if n.get('request_version') == version]
            target = (kept[-1].get('answer_path') or {}).get('reply_to_message_id') if kept else None
            update = H.deliver(api, 'bot75', sender, text, reply_to=target if sender is owner_user else None)
            return update, ing.wake({'tick': A.next_id('tick')})

        def settled(sid):
            s = stop_of(sid)
            item = ing.inbox.read(s['request_id']) if s.get('request_id') else None
            data = (item or {}).get('data') or {}
            return ing.settlement.settlement(s['request_id'], data.get('request_version')) if data else None

        # AC1: an authenticated worker or service raises a stop at every enabled stop point.
        stops = {}
        with section(RA, NE):
            check(RA, 'the production ingress is activated by the owner', activated)
            check(RA, 'the andon module is installed and constructed on the ingress', andon is not None)
            worker = A.AC.membership_entry(A.CM.authority_state(A.S, A.conn)['membership'], 'worker') or {}
            check(RA, 'the worker is an active agent run with no role at all',
                  worker.get('principal_type') == 'agent_run' and worker.get('roles') == [])
            for n, (station, state) in enumerate(_V75_POINTS):
                uid = unit('unit-%s' % state.lower(), state)
                who = 'pm' if station == 'coordination' else 'worker'
                reason = 'reason-%s: the %s station needs an owner decision' % (state.lower(), station)
                result = raise_stop(raise_packet(who, uid, station, reason))
                sid = result.get('stop_id')
                s = stop_of(sid)
                stops[state] = sid
                u = (entity(uid) or {}).get('data') or {}
                check(RA, '%s raised by %s at the %s stop point is recorded [%s %s]' % (state, who, station,
                      result.get('outcome'), result.get('reason')),
                      result.get('outcome') == 'stopped' and s.get('state') == 'stopped' and s.get('raised_by') == who)
                check(RA, '%s: the stop keeps reason, interrupted station and state, and the resolving predicate' % state,
                      s.get('reason') == reason and s.get('station') == station and s.get('interrupted_state') == state
                      and s.get('resolving') == {'principal': 'owner', 'roles': ['project_owner']}
                      and s.get('effect') == 'clean')
                check(RA, '%s: the unit is AWAITING_AUTHORITY along its declared edge, carrying the interruption' % state,
                      u.get('state') == 'AWAITING_AUTHORITY' and (u.get('interruption') or {}).get('stop_id') == sid
                      and (u.get('interruption') or {}).get('station') == station)
                item = ing.inbox.read(s.get('request_id') or '') if s else None
                check(RA, '%s: the request is addressed to the resolving authority, not the requester' % state,
                      item is not None and item['data']['owner'] == 'owner' and item['data']['requested_by'] == 'andon'
                      and who not in (item['data']['owner'], item['data']['requested_by']))
            wrong = raise_stop(raise_packet('worker', unit('unit-wrong-station', 'RUNNING'), 'review', 'reason-wrong'))
            check(RA, 'a stop at a station that does not hold the unit is refused as stale_subject [%s]' % wrong.get('reason'),
                  wrong.get('reason') == 'stale_subject' and unit_state('unit-wrong-station') == 'RUNNING')
            other = raise_stop(raise_packet('worker', 'unit-wrong-station', 'deployment', 'reason-disabled'))
            check(RA, 'a stop point that is not enabled is refused as invalid_input [%s]' % other.get('reason'),
                  other.get('reason') == 'invalid_input' and unit_state('unit-wrong-station') == 'RUNNING')

        # AC1: authentication is what raising needs; a forged or unenrolled signer records nothing.
        with section(RU):
            uid = unit('unit-unauthenticated', 'RUNNING')
            before = len(andon.stops()) if andon is not None else None
            forged = raise_stop(raise_packet('worker', uid, 'build', 'reason-forged', signer='pm'))
            check(RU, 'a command for the worker signed with another member\'s key is refused as not_authorized [%s]'
                  % forged.get('reason'), forged.get('reason') == 'not_authorized')
            stranger_body = dict(ids, operation='raise', principal='settler', command_id=A.next_id('raise'),
                                 nonce=A.next_id('raise-nonce'), unit=uid, station='build', reason='reason-unenrolled',
                                 resolving={'principal': 'owner', 'roles': ['project_owner']}, effect='clean')
            unenrolled = raise_stop(signed('settler', stranger_body))
            check(RU, 'a command signed by a key of no member is refused as not_authorized [%s]' % unenrolled.get('reason'),
                  unenrolled.get('reason') == 'not_authorized')
            check(RU, 'nothing was recorded and the unit still runs',
                  andon is not None and len(andon.stops()) == before and unit_state(uid) == 'RUNNING')

        # AC2: each enabled stop kind reaches the owner's Telegram chat with its current presentation.
        with section(NE):
            for station, state in (('build', 'RUNNING'), ('review', 'REVIEWING'), ('coordination', 'LANDING')):
                sid = stops.get(state)
                s = stop_of(sid)
                kept = notices_of(sid)
                current = ing.presenter.current(s.get('request_id') or '') or {}
                n = kept[0] if len(kept) == 1 else {}
                text = message(n.get('message_id')).get('text') or ''
                check(NE, '%s stop: one notice kept for request version 1 and the current presentation' % station,
                      len(kept) == 1 and n.get('request_version') == 1 and n.get('presentation_id') == current.get('presentation_id')
                      and n.get('presentation_digest') == current.get('brief_digest') and current.get('outcome') == 'published')
                check(NE, '%s stop: the message the platform returned is in the owner\'s chat and shows the stop' % station,
                      n.get('chat_id') == chat and n.get('message_ids') == current.get('message_ids')
                      and n.get('message_id') in (n.get('message_ids') or []) and s.get('reason', '?') in text
                      and station in text and 'https://' not in text)
                check(NE, '%s stop: the answer path is a reply to that message offering the request\'s choices' % station,
                      (n.get('answer_path') or {}).get('reply_to_message_id') == n.get('message_id')
                      and (n.get('answer_path') or {}).get('choices') == current.get('choices')
                      and 'accept' in (current.get('choices') or []))
            check(NE, 'every stop point\'s stop was sent once to the owner\'s chat',
                  all(len(notices_of(stops.get(state))) == 1 for _s, state in _V75_POINTS))

        # AC2 (declared falsifier): a new request version with the same status is a new notice.
        build = stops.get('RUNNING')
        with section(NV):
            s = stop_of(build)
            rid = s.get('request_id') or ''
            state_before = ((ing.inbox.read(rid) or {}).get('data') or {}).get('state')
            sent = sends()
            refused = andon.revise_stop(revise_packet('pm', build, 'reason-not-mine')) if andon is not None else {}
            check(NV, 'another member cannot add to the worker\'s stop [%s]' % refused.get('reason'),
                  refused.get('reason') == 'not_authorized' and sends() == sent)
            revised = (andon.revise_stop(revise_packet('worker', build, 'reason-update: the build also broke its cache'))
                       if andon is not None else {})
            data = ((ing.inbox.read(rid) or {}).get('data') or {})
            check(NV, 'the revision is request version 2 with the same status [%s %s]' % (revised.get('outcome'), revised.get('reason')),
                  revised.get('outcome') == 'revised' and data.get('request_version') == 2 and data.get('state') == state_before)
            kept = {n['request_version']: n for n in notices_of(build)}
            current = ing.presenter.current(rid) or {}
            v2 = kept.get(2) or {}
            text = message(v2.get('message_id')).get('text') or ''
            check(NV, 'the changed presentation was sent: one more message, the update shown [%s]' % (revised.get('notice') or {}).get('outcome'),
                  sends() == sent + 1 and 'reason-update' in text and (revised.get('notice') or {}).get('outcome') == 'notified')
            check(NV, 'its correlation is its own: version 2, the new presentation, the new message',
                  sorted(kept) == [1, 2] and v2.get('presentation_id') == current.get('presentation_id')
                  and v2.get('presentation_id') != kept[1].get('presentation_id') and v2.get('message_id') != kept[1].get('message_id')
                  and v2.get('message_ids') == current.get('message_ids') and v2.get('request_state') == state_before)
            again = andon.notify(build) if andon is not None else {}
            check(NV, 'the same version and presentation again is suppressed and sends nothing [%s]' % again.get('outcome'),
                  again.get('outcome') == 'suppressed' and sends() == sent + 1 and len(notices_of(build)) == 2)

        # AC3 (declared falsifier): a notification, a publication or a platform acknowledgement grants nothing.
        with section(RK):
            early = resume(build)
            check(RK, 'a stop noticed, published and acknowledged by the platform but not answered does not resume [%s]'
                  % early.get('reason'), early.get('outcome') == 'refused' and early.get('reason') == 'no_settlement'
                  and unit_state('unit-running') == 'AWAITING_AUTHORITY' and stop_of(build).get('state') == 'stopped')
            passed = andon.run() if andon is not None else []
            check(RK, 'a pass of the service over the pending stops resumes none of them',
                  andon is not None and all(r.get('outcome') != 'resumed' for r in passed)
                  and all(unit_state('unit-%s' % state.lower()) == 'AWAITING_AUTHORITY' for _s, state in _V75_POINTS))
            review = stops.get('REVIEWING')
            _u, woke = reply(review, 'reject: the review must be redone')
            rejected = settled(review) or {}
            refusal = resume(review)
            check(RK, 'the owner\'s settled reject does not resume the review stop [%s %s]' % (rejected.get('ruling'), refusal.get('reason')),
                  rejected.get('ruling') == 'reject' and refusal.get('outcome') == 'refused'
                  and unit_state('unit-reviewing') == 'AWAITING_AUTHORITY' and stop_of(review).get('state') == 'stopped')

        # AC3: a stale presentation or a wrong actor settles nothing and resumes nothing.
        with section(RW):
            reply(build, 'accept: answered on the superseded message', version=1)
            check(RW, 'the owner\'s answer to the superseded version 1 message settles nothing',
                  settled(build) is None)
            reply(build, 'accept: I am not the owner', sender=stranger)
            check(RW, 'an answer from a sender who is not enrolled settles nothing', settled(build) is None)
            s, current = stop_of(build), ing.presenter.current(stop_of(build).get('request_id') or '') or {}
            api_refusals = []
            for who in ('steward', 'worker'):
                answer = dict(ids, schema='veldo.settlement_api_answer/v1', edge='api-edge', answer_id=A.next_id('api'),
                              principal=who, request_id=s.get('request_id'), request_version=current.get('request_version'),
                              presentation_id=current.get('presentation_id'), presentation_digest=current.get('brief_digest'),
                              presentation_version=current.get('presentation_version'), choice='accept',
                              rationale='answered by a member who is not the designated authority')
                api_refusals.append(ing.settlement.api_answer({'answer': answer, 'signature': A.sign_as(
                    'api-edge', A.S.canonical_bytes(answer))}).get('reason'))
            check(RW, 'the steward and the worker answering through the authenticated API are refused as not_owner [%s]'
                  % api_refusals, api_refusals == ['not_owner', 'not_owner'] and settled(build) is None)
            wrong = resume(build)
            check(RW, 'after stale and wrong-actor answers the stop does not resume [%s]' % wrong.get('reason'),
                  wrong.get('reason') == 'no_settlement' and unit_state('unit-running') == 'AWAITING_AUTHORITY')
            # A wrong actor at resume: the settlement's author no longer holds the resolving roles.
            uid = unit('unit-demoted', 'VERIFYING')
            held = raise_stop(raise_packet('worker', uid, 'build', 'reason-demoted', roles=('project_owner', 'technical_authority')))
            sid = held.get('stop_id')
            reply(sid, 'accept: resume it')
            ok = (settled(sid) or {}).get('ruling') == 'approve'
            A.admin('steward', 'change_roles', {'principal': 'owner', 'roles': ['project_owner', 'admission_authority',
                                                                                 'priority_authority']})
            demoted = resume(sid)
            check(RW, 'a settlement whose author no longer holds the resolving roles does not resume [%s]' % demoted.get('reason'),
                  ok and demoted.get('reason') == 'not_authorized' and unit_state(uid) == 'AWAITING_AUTHORITY')
            A.admin('steward', 'change_roles', {'principal': 'owner', 'roles': ['project_owner', 'admission_authority',
                                                                                 'priority_authority', 'technical_authority']})

        # AC3: the designated authority's current settlement resumes a clean stop with a fresh station contract.
        with section(RF):
            for sid, uid, version in ((build, 'unit-running', 2), (stops.get('LANDING'), 'unit-landing', 1)):
                if version == 2:
                    head = ing.presenter.current(stop_of(sid).get('request_id') or '') or {}
                    A.delegate(request_version=2, presentation_version=head.get('presentation_version') or 0)
                reply(sid, 'accept: resume it')
                settlement = settled(sid) or {}
                check(RF, '%s: the owner\'s accept settled the request\'s current version %d' % (uid, version),
                      settlement.get('ruling') == 'approve' and settlement.get('principals') == ['owner']
                      and settlement.get('request_version') == version)
                done = resume(sid)
                u = entity(uid) or {}
                cid = (u.get('data') or {}).get('station_contract')
                contract = andon.station_contract(cid) if andon is not None and cid else {}
                contract = contract or {}
                permission = contract.get('permission') or {}
                check(RF, '%s: resumed to READY with the interruption cleared [%s %s]' % (uid, done.get('outcome'), done.get('reason')),
                      done.get('outcome') == 'resumed' and u.get('data', {}).get('state') == 'READY'
                      and u.get('data', {}).get('interruption') is None and stop_of(sid).get('state') == 'resumed')
                check(RF, '%s: a fresh station contract names the station, the next attempt and the unit version it was issued at'
                      % uid, contract.get('station') == stop_of(sid).get('station') and contract.get('attempt') == 1
                      and contract.get('issued_at_unit_version') == u.get('version') and contract.get('unit') == uid
                      and contract.get('stop_id') == sid)
                check(RF, '%s: the permission is that settlement, its receipt and effect, by the designated owner' % uid,
                      permission.get('settlement_id') == settlement.get('settlement_id')
                      and permission.get('receipt_id') == settlement.get('receipt_id')
                      and permission.get('effect_id') == settlement.get('effect_id') and permission.get('principal') == 'owner'
                      and permission.get('request_version') == version
                      and permission.get('presentation_id') == settlement.get('presentation_id')
                      and stop_of(sid).get('resumption') == permission)
                twice = resume(sid)
                check(RF, '%s: a second resume is refused and issues no second contract [%s]' % (uid, twice.get('reason')),
                      twice.get('reason') == 'not_stopped' and (entity(uid) or {}).get('version') == u.get('version'))

        # AC3: an unknown-effect stop never resumes on an answer; its dispatch stays as it was.
        with section(RX):
            declared = unit('unit-declared-unknown', 'RUNNING')
            dispatched = unit('unit-dispatch-unknown', 'DISPATCHING')
            did = 'dispatch:%s:1' % dispatched
            A.fixture(did, 'dispatch', {'dispatch_id': did, 'state': 'unknown', 'contract': {
                'unit': dispatched, 'repository': ids['repository_uuid'], 'station': 'build', 'attempt': 1}})
            dispatch_before = entity(did)
            one = raise_stop(raise_packet('worker', declared, 'build', 'reason-declared-unknown', effect='unknown'))
            two = raise_stop(raise_packet('pm', dispatched, 'build', 'reason-dispatch-unknown', effect='clean'))
            check(RX, 'a declared unknown effect and an unknown dispatch both record an unknown-effect stop',
                  stop_of(one.get('stop_id')).get('effect') == 'unknown' and stop_of(two.get('stop_id')).get('effect') == 'unknown'
                  and stop_of(two.get('stop_id')).get('outstanding_effects') == [did])
            for label, result, uid in (('declared', one, declared), ('dispatch', two, dispatched)):
                sid = result.get('stop_id')
                reply(sid, 'accept: resume it anyway')
                answer = settled(sid) or {}
                refusal = resume(sid)
                check(RX, '%s unknown effect: the owner\'s settled accept does not resume it [%s %s]' % (label, answer.get('ruling'),
                      refusal.get('reason')), answer.get('ruling') == 'approve' and refusal.get('reason') == 'unknown_outcome'
                      and unit_state(uid) == 'AWAITING_AUTHORITY' and stop_of(sid).get('state') == 'stopped')
            passed = andon.run() if andon is not None else []
            check(RX, 'a pass of the service leaves both stopped and the dispatch record untouched',
                  andon is not None and not any(r.get('outcome') == 'resumed' and r.get('stop_id') in (one.get('stop_id'), two.get('stop_id'))
                                                for r in passed)
                  and unit_state(declared) == unit_state(dispatched) == 'AWAITING_AUTHORITY' and entity(did) == dispatch_before)

        # Observability: named refusals with their error class, counts and pending work, no reason text or signature.
        with section(OB):
            observed = _v75_json.dumps(andon.observations if andon is not None else [])
            metrics = andon.metrics() if andon is not None else {}
            check(OB, 'every refusal is named and classed; unknown is never success',
                  andon is not None and all(o.get('reason') and o.get('error_class') for o in andon.observations
                                            if o.get('outcome') == 'refused')
                  and AND.taxonomy('unknown_outcome') == 'unknown_outcome' and AND.taxonomy('no_such_code') == 'unknown_outcome')
            check(OB, 'no reason text, signature or key is observed',
                  bool(andon and andon.observations) and 'reason-' not in observed and 'SSH SIGNATURE' not in observed)
            check(OB, 'metrics count accepted and refused operations and list the pending stops',
                  metrics.get('accepted', 0) > 0 and metrics.get('refused', 0) > 0
                  and stops.get('REVIEWING') in (metrics.get('pending') or []) and build not in (metrics.get('pending') or []))
            check(OB, 'no connection beyond the loopback interface was attempted [%d]' % len(attempts), not attempts)
    finally:
        _v75_socket.create_connection = real_connect
        stop()
        if ing is not None:
            ing.conn.close()
        A.conn.close()
    return rows


_v75_started = _v75_time.monotonic()
_v75_fast = '/dev/shm' if _v75_Path('/dev/shm').is_dir() else None
with _v75_temp.TemporaryDirectory(prefix='v75-', dir=_v75_fast) as _v75_dir:
    _v75_rows = _v75_checks(_v75_Path(_v75_dir))
for _v75_name, _v75_observed in _v75_rows.items():
    _v75_ok = bool(_v75_observed) and all(ok for _, ok in _v75_observed)
    if not _v75_ok:
        for _v75_label, _v75_one in _v75_observed:
            if not _v75_one:
                print('  VELDO-0075 %s detail: %s' % (_v75_name, _v75_label))
    expect('VELDO-0075 ' + _v75_name, _v75_ok)
print('VELDO-0075 notice/real-telegram: PENDING the lead\'s run with the owner through the running factory '
      '(VELDO-0138); the rows use a loopback stand-in; not counted as passed')
print('VELDO-0075 suite seconds: %.3f' % (_v75_time.monotonic() - _v75_started))
