"""VELDO-0342: an answer for one worktree of a review group, and a second group on the same day.

Real Git worktrees, the keep step and its snapshots, signed terms, the inbox, the presenter and the
settlement on a temporary SQLite store, as the VELDO-0340 suite has them. Only Telegram's send is a
fixture transport, and the Ledger's clock is the fixture's. Keys are generated in the fixture root.
No engine and no host worktree is used.

AC1 rows: ac1/offer (the three group picks and three member picks for each member, each worktree
named beside its index), ac1/member-discard (the falsifier row: in a group of three accept discard
w2 discards member 2 alone, in one write that raises a new request for members 1 and 3 on the same
record), ac1/request-closed (an answer to the settled request is refused as request_closed),
ac1/member-keep (Keep for one member is the owner's signed packet naming that member),
ac1/last-member (the group closes when its last member leaves), ac1/changed-member (a member whose
file list changed after the request was shown is not discarded by its pick, and joins the open
group again under a new index).
AC2 rows: ac2/fit (the falsifier row: 74 members; the group picks and the member picks of the
lowest indexes that fit one message part, the text naming the members without one, the presentation
rendered, and one more member's picks refused by the presenter), ac2/next (after a member pick the
next request reaches the members after).
AC3 rows: ac3/one-open (while a group is open a deferral joins it, also after a member pick),
ac3/next-sequence (the falsifier row: after the day's group is closed by an answer, a deferral the
same day opens the next sequence number with its own request), ac3/pending-join (a deferral between
a settled member pick and its application joins the same group and is listed by the request raised
when the pick is applied).
More rows: pick/ledger, pick/signal, pick/remover (a member pick is an answer for no other member,
for the Ledger, for Signal and for the remover, each on its own), pick/single (a request for one
worktree offers and takes no member pick), terms/indexes (the terms carry each worktree's index and
the indexes offered a pick), next/settled-keep, next/keep-join, next/keep-text (Keep settlement
advances the others and later deferrals while its own packet stays pending), next/left-member
(a member being judged again leaves and can rejoin under a new index), next/gone (the member a
settled pick names is gone: the next publish raises the request for the members left), worker/member-pick (the service's own disposition task,
unchanged, carries a member pick and raises the next request).
"""


def _v342_suite():
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import sqlite3
    import subprocess
    import tempfile
    import time
    import traceback
    from unittest.mock import patch

    production = {
        'control_request_settlement.py': ROOT / ".veldo" / "control_request_settlement.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    rows = {}

    def check(row, label, good):
        rows.setdefault(row, []).append((label, bool(good)))

    def load(name):
        spec = importlib.util.spec_from_file_location('v342_' + name, mods / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0342-') as temporary:
        base = Path(temporary)
        mods = base / 'modules'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        for name, source in production.items():
            shutil.copyfile(source, mods / name)
        claims = load('control_claim')
        S, CM, AC = claims.S, claims.CM, claims.AC
        I, V, P = (load(name) for name in ('control_assignment', 'control_channel_presentation',
                                          'control_channel_projection'))
        ST, contract = load('control_request_settlement'), load('entity_contract')
        keys, public = {}, {}
        for who in ('steward', 'owner', 'requester', 'api-edge', 'outsider'):
            keys[who] = base / who
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(keys[who])],
                           check=True, capture_output=True, timeout=10)
            public[who] = ' '.join(keys[who].with_suffix('.pub').read_text().split()[:2])

        def sign(who, message, namespace='veldo-command'):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(keys[who]), '-n', namespace],
                                  input=message, capture_output=True, check=True, timeout=10).stdout.decode()

        def journal_sign(message):
            return sign('steward', message, 'veldo-journal')

        serial = 0

        def next_id():
            nonlocal serial
            serial += 1
            return 'fixture-' + str(serial)

        ids = dict(domain_uuid='space-domain', repository_uuid='space-repo', store_uuid='space-store')
        conn = S.open_store(str(base / 'control.sqlite3'))
        CM.attach(S)

        def member(who, principal_type, roles):
            state = CM.authority_state(S, conn)
            command = dict(command_id=next_id(), operation='enroll_principal', target='authority',
                           parameters=dict(principal=who, principal_type=principal_type, roles=roles,
                                           public_key=public[who], independence_group=who, scope='*'),
                           artifact_digests=[], expected_versions={})
            envelope = dict(ids, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal='steward',
                            request_revision=1, nonce=next_id(), expires_at=time.time() + 600,
                            membership_version=state['membership_version'], delegation_version=state['delegation_version'],
                            command_digest=AC.canonical_command_digest(command))
            return CM.admit(S, conn, envelope, command, sign('steward', AC.canonical_envelope_bytes(envelope)),
                            ids, time.time(), enrollee_signature=None if who == 'steward' else
                            sign(who, AC.canonical_envelope_bytes(dict(envelope, principal=who))),
                            journal_signer=('steward', journal_sign))

        member('steward', 'person', ['membership_steward', 'project_owner'])
        member('owner', 'person', ['project_owner', 'admission_authority', 'priority_authority', 'technical_authority'])
        member('outsider', 'person', [])
        member('requester', 'service', [])
        member('api-edge', 'service', [])

        for who, chat in (('owner', 32701), ('outsider', 32702)):
            eid = 'channel-enrollment:telegram_chat:' + who
            S.execute(conn, dict(command_id=next_id(), nonce=next_id(), principal='steward', operation='upsert_entity',
                                 parameters=dict(entity_id=eid, kind='channel_enrollment',
                                     data=dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat',
                                               principal=who, chat_id=chat, revoked_at=None)),
                                 expected_versions={eid: 0}, artifact_digests=[]), 'steward', journal_sign, 1)

        class Transport:
            def __init__(self):
                self.sent = []

            def send(self, chat, text, reply_to):
                self.sent.append(text)
                return dict(chat_id=chat, message_id=len(self.sent), date=int(time.time()), text=text,
                            reply_to_message_id=reply_to)

        transport = Transport()
        inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'steward', journal_sign)
        presenter = V.Presenter(S, CM, P, inbox, transport, conn, 'steward', journal_sign, assignment=I)
        settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'steward', journal_sign,
                                   assignment=I, presentation=V, api_edge='api-edge')

        def signed(body, who='requester'):
            return dict(command=body, signature=sign(who, S.canonical_bytes(body)))

        def command(operation, **fields):
            return dict(ids, operation=operation, principal='requester', command_id=next_id(), nonce=next_id(), **fields)

        import os
        import types
        SP, SIG, RM, KP, K, PR, CFG = (load(name) for name in (
            'control_space', 'control_space_signal', 'control_space_remove', 'control_space_keep',
            'control_space_kinds', 'control_space_probe', 'control_space_config'))
        repo, trees, state, proc = (base / name for name in ('repo', 'trees', 'state', 'proc'))
        for folder in (repo, trees, state, proc):
            folder.mkdir()
        (proc / 'mounts').write_text('proc /proc proc rw 0 0\n')
        def git(path, *args):
            done = subprocess.run(['git', '-C', str(path), *args], check=True,
                capture_output=True, env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
            return done.stdout.decode().strip()
        git(repo, 'init', '-q')
        git(repo, 'config', 'user.name', 'Owner Fixture')
        git(repo, 'config', 'user.email', 'owner@example.invalid')
        git(repo, 'config', 'commit.gpgsign', 'false')
        (repo / 'base.txt').write_text('base\n')
        (repo / '.gitignore').write_text('.settings\n.late-settings\n')
        git(repo, 'add', '.')
        git(repo, 'commit', '-q', '-m', 'base')
        head = git(repo, 'rev-parse', 'HEAD')
        config = CFG.check({'enabled': True, 'time_zone': 'UTC',
            'pools': {'host': {'floor': 0, 'needs': {'build': 1, 'review': 1, 'gate': 1}}},
            'engines': ['fixture'], 'scratch_roots': {'roots': [], 'session_pattern': 'sessions/{working_folder}/{session_id}'},
            'build_roots': [], 'plain_repositories': [{'repository': str(repo), 'worktree_root': str(trees)}],
            'client_accounts': [], 'protect': {'paths': [], 'volumes': [], 'containers': [],
                                            'images': [], 'networks': [], 'compose_projects': []}})
        ledger = SP.Ledger(S, conn, 'steward', journal_sign, config=config, state_root=str(state), host='fixture',
            lifecycle={'version': K.REGISTRY['version'], **{k: K.REGISTRY['tables'][K.REGISTRY['version']][k]
                                                          for k in ('events', 'ends_on')}})
        assert ledger.set_pool('host', 'filesystem', device=ledger.device(str(repo)))['ok']
        scope = {'type': 'plain_repository', 'id': str(repo)}
        # The mode prerequisites belong to their own suites; this fixture starts in act.
        mode = {'scope': scope, 'mode': 'act'}
        conn.execute('INSERT INTO entities(id,kind,version,digest,data) VALUES(?,?,?,?,?)',
                     (SP.mode_id(scope), SP.MODE_KIND, 1, S.digest_of(mode), json.dumps(mode)))
        conn.commit()
        given = dict(probe=PR, kinds=K, remover=RM, keep=KP.keeper(ledger), free=lambda pool: 1000000,
                     run=lambda argv, cwd=None: (0, '') if argv[0] == 'docker' else RM._run(argv, cwd),
                     proc=str(proc), owner_live=lambda owner: {'conclusive': True, 'group_empty': True})
        ledger.disposition_publish = lambda item: ledger.publish_disposition(
            item, settlement, inbox, presenter, ('requester', lambda data: sign('requester', data)), 'owner')

        def tree(label, dirty=True, ticket=True, station='build', shared=None, draft='draft.txt'):
            # shared: the ticket, or the run, this worktree has in common with another one.
            path = trees / label
            git(repo, 'worktree', 'add', '-q', *(['-b', label] if ticket else ['--detach']), str(path), head)
            owner = {'scope': scope}
            if ticket:
                owner['ticket'] = shared or label
            else:
                owner['run'] = {'id': shared or label, 'station': station}
            if dirty:
                (path / draft).write_text('draft ' + label)
            made = ledger.declare('worktree', {'path': str(path)}, owner, 'record', branch=label if ticket else None, start=head)
            assert made['ok'], made
            item = made['item']
            assert ledger.confirm(item)['ok']
            return item, path, owner

        def signal(item, owner, event='ticket_ended'):
            subject = dict(owner)
            if isinstance(subject.get('run'), dict):
                subject['run'] = subject['run']['id']
            result = SIG.signal(ledger, event, subject, **given)
            return result

        def request(item):
            decision = ledger.item(item)['disposition']
            return I.assignment_id(ids['repository_uuid'], decision['alias'])

        def settle(item, choice):
            rid = request(item)
            result = presenter.present(rid)
            receipt = presenter.current(rid)
            assert receipt, (result, ledger.item(item))
            body = dict(ids, schema=ST.API_SCHEMA, edge='api-edge', answer_id=next_id(),
                principal='owner', request_id=rid, request_version=receipt['request_version'],
                presentation_id=receipt['presentation_id'], presentation_digest=receipt['brief_digest'],
                presentation_version=receipt['presentation_version'], choice='accept ' + choice, rationale='Owner answer')
            result = settlement.api_answer(dict(answer=body, signature=sign('api-edge', S.canonical_bytes(body))))
            assert result.get('outcome') == 'settled', result
            return rid

        def authorize(item, rid, who='owner', signer=None, **extra):
            body = dict(operation='space_disposition', principal=who, command_id=next_id(), nonce=next_id(),
                        parameters=dict(item=item, version=ledger._row(item, SP.ITEM_KIND)[0], request=rid, **extra))
            return ledger.disposition(dict(command=body, signature=sign(signer or who, S.canonical_bytes(body))),
                                      CM, time.time())

        def act(item):
            return SIG.disposition(ledger, PR, RM, item, **{k: v for k, v in given.items()
                                                          if k not in ('probe', 'remover')})

        def snapshot(item):
            attempts = ledger.item(item).get('kept', {}).get('snapshots', [])
            return Path(attempts[-1]['path']) if attempts else None

        def contents(path):
            try:
                return path.read_text()
            except FileNotFoundError:
                return None

        # The Ledger's clock is the fixture's. Noon, so a day is a day in UTC.
        import datetime
        now = [datetime.datetime(2026, 11, 16, 12, 0, tzinfo=datetime.timezone.utc).timestamp()]
        ledger.clock = lambda: now[0]

        def today():
            return datetime.datetime.fromtimestamp(now[0], datetime.timezone.utc).date().isoformat()

        def next_day():
            now[0] += 86400

        def review(label, text=None, station='review'):
            item, path, owner = tree(label, dirty=False, ticket=False, station=station)
            (path / 'base.txt').write_text(text or 'edited by ' + label + '\n')
            return item, path, owner

        def finish(item, owner):
            return signal(item, owner, 'run_finished')

        def assignments(prefix=''):
            found = {}
            for eid, version, raw in conn.execute("SELECT id, version, data FROM entities WHERE kind='assignment'"):
                data = json.loads(raw)
                if data.get('alias', '').startswith(prefix):
                    found[eid] = (version, data)
            return found

        def group_of(item):
            decision = (ledger.item(item) or {}).get('disposition') or {}
            return decision.get('group'), ledger.group(decision.get('group')) or {}

        def answer(rid, receipt, choice):
            body = dict(ids, schema=ST.API_SCHEMA, edge='api-edge', answer_id=next_id(),
                principal='owner', request_id=rid, request_version=receipt['request_version'],
                presentation_id=receipt['presentation_id'], presentation_digest=receipt['brief_digest'],
                presentation_version=receipt['presentation_version'], choice='accept ' + choice,
                rationale='Owner answer')
            return settlement.api_answer(dict(answer=body, signature=sign('api-edge', S.canonical_bytes(body))))

        def state_of(item):
            return (ledger.item(item) or {}).get('state')

        publish = ledger.disposition_publish

        def broke(named):
            # A part that raises fails its own rows, and the parts after it still run.
            for row in named:
                check(row, traceback.format_exc(), False)

        def day_groups():
            return {key: one for key, one in ledger.groups().items() if one['day'] == today()}

        def asked(rid):
            return ledger._row(rid, 'assignment')[1] or {}

        def refusal(item, rid):
            # The code the Ledger refuses a settled answer for this item with, or None when it takes it.
            try:
                ledger.disposition_effect(item, rid)
            except SP.Refused as error:
                return error.code
            return None

        def head_seq():
            return conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]

        def written(start):
            return [json.loads(raw) for (raw,) in conn.execute('SELECT transition FROM journal WHERE seq>?', (start,))]

        def effect_of(rid):
            eid = asked(rid)['settlement']['effect_id']
            return json.loads(conn.execute('SELECT data FROM entities WHERE id=?', (eid,)).fetchone()[0])

        def force(item, effect, rid):
            # Written directly, past the Ledger: the item's record as if the pick had been given to it.
            record = ledger._decided(dict(ledger.item(item)), effect, 'owner', rid)
            conn.execute('UPDATE entities SET data=?, digest=? WHERE id=?', (json.dumps(record), S.digest_of(record), item))
            conn.commit()

        GROUP_PICKS = ['accept save', 'accept keep', 'accept discard']

        def picks(*indexes):
            return GROUP_PICKS + ['accept %s w%d' % (word, index) for index in indexes
                                  for word in ('save', 'keep', 'discard')]

        try:
            try:
                ledger.disposition_publish = publish
                # AC1: a group of three; accept discard w2 discards member 2 alone.
                made = [review('pick-a'), review('pick-b'), review('pick-c')]
                for item, path, owner in made:
                    finish(item, owner)
                (a, a_path, _), (b, b_path, _), (c, c_path, _) = made
                gid, group = group_of(a)
                rid = request(a)
                sent = len(transport.sent)
                presenter.present(rid)
                receipt = presenter.current(rid)
                text = '\n'.join(transport.sent[sent:])
                opened = asked(rid)
                check('ac1/offer', 'the request offers the three group picks and three member picks for each member '
                      + repr(opened.get('choices')), opened.get('choices') == picks(1, 2, 3)
                      == ST.space_group_choices([1, 2, 3]) and len(opened['choices']) == 12
                      and (receipt or {}).get('choices') == picks(1, 2, 3))
                check('ac1/offer', 'the message names each worktree beside its index and shows the picks ' + repr(text),
                      all(one in text for one in (
                          'Worktree 1: ' + json.dumps(str(a_path)), 'Worktree 2: ' + json.dumps(str(b_path)),
                          'Worktree 3: ' + json.dumps(str(c_path)), 'accept discard w2 | accept save w3',
                          'An answer for one worktree adds w and its number')))
                check('ac1/offer', 'the record, the terms and each member disposition hold the index '
                      + repr(group.get('request')), [one['index'] for one in group['members']] == [1, 2, 3]
                      and group['request']['proposal']['indexes'] == [1, 2, 3]
                      and group['request']['proposal']['picks'] == [1, 2, 3] and group['request']['number'] == 1
                      and [ledger.item(one)['disposition']['index'] for one in (a, b, c)] == [1, 2, 3])
                frozen = ledger._row(gid, SP.GROUP_KIND)
                settled = answer(rid, receipt, 'discard w2')
                check('ac1/member-discard', 'the answer accept discard w2 settles the request ' + repr(settled),
                      settled.get('outcome') == 'settled' and asked(rid)['state'] == 'SATISFIED')
                early = publish(a)
                check('ac1/member-discard', 'before the pick is applied a publish says the request is answered and '
                      'writes nothing on the record ' + repr(early), early.get('reason') == 'space_group_answered'
                      and ledger._row(gid, SP.GROUP_KIND) == frozen)
                others = [ledger.authorize_disposition(one, rid) for one in (a, c)]
                check('ac1/member-discard', 'the pick is not applied through member 1 or member 3 ' + repr(others),
                      all(not one.get('ok') and one.get('reason') == 'space_disposition_unsettled' for one in others)
                      and ledger._row(gid, SP.GROUP_KIND) == frozen)
                start = head_seq()
                applied = ledger.authorize_disposition(b, rid)
                writes = written(start)
                check('ac1/member-discard', 'member 2 alone is due for Discard; members 1 and 3 are deferred with a '
                      'request, in the one write ' + repr(applied), applied.get('ok') and state_of(b) == 'due'
                      and ledger.item(b)['disposition']['choice'] == 'discard'
                      and all(state_of(one) == 'deferred' and ledger.item(one)['disposition']['state'] == 'requested'
                              for one in (a, c)) and len(writes) == 1 and {a, b, c, gid} <= set(writes[0]))
                carried = [act(one) for one in (a, b, c)]
                check('ac1/member-discard', 'only member 2 is discarded, saved in the snapshot store first; members 1 '
                      'and 3 are on disk with their edits ' + repr(carried), state_of(b) == 'removed'
                      and not b_path.exists() and snapshot(b) is not None
                      and contents(snapshot(b) / 'work' / 'base.txt') == 'edited by pick-b\n'
                      and contents(a_path / 'base.txt') == 'edited by pick-a\n'
                      and contents(c_path / 'base.txt') == 'edited by pick-c\n'
                      and state_of(a) == 'deferred' and state_of(c) == 'deferred'
                      and snapshot(a) is None and snapshot(c) is None)
                group = ledger.group(gid)
                new = group['request']
                check('ac1/member-discard', 'the same group record, open: member 2 is recorded with its answer and the '
                      'settled request with its answer ' + repr(group.get('requests')),
                      group_of(a)[0] == gid == group_of(c)[0] and group['state'] == 'open' and len(day_groups()) == 1
                      and [(one['index'], (one.get('answer') or {}).get('choice')) for one in group['members']]
                      == [(1, None), (2, 'accept discard w2'), (3, None)]
                      and [(one['alias'], one['id'], one['number'], one['answer']['member'], one['answer']['applied'])
                           for one in group.get('requests') or []]
                      == [(frozen[1]['request']['alias'], rid, 1, 2, [2])])
                check('ac1/member-discard', 'the record holds a new request for members 1 and 3, their indexes '
                      'unchanged ' + repr(new), new['number'] == 2 and new['version'] == 1
                      and new['alias'] != frozen[1]['request']['alias'] and new['proposal']['indexes'] == [1, 3]
                      and new['proposal']['picks'] == [1, 3]
                      and [one['item'] for one in new['proposal']['worktrees']] == [a, c]
                      and all(ledger.item(one)['disposition']['alias'] == new['alias']
                              and ledger.item(one)['deferral']['decision_request'] == new['alias'] for one in (a, c)))
                said = publish(a)
                rid2 = request(a)
                second = asked(rid2)
                check('ac1/member-discard', 'the new request is raised: it names worktrees 1 and 3 and offers their '
                      'picks alone ' + repr(said), said.get('ok') and rid2 != rid and request(c) == rid2
                      and second.get('state') == 'OFFERED' and second.get('choices') == picks(1, 3)
                      and 'Worktree 1: ' + json.dumps(str(a_path)) in second.get('brief', '')
                      and 'Worktree 3: ' + json.dumps(str(c_path)) in second['brief']
                      and json.dumps(str(b_path)) not in second['brief'] and 'Worktree 2' not in second['brief'])
                group = ledger.group(gid)
                closed = [answer(rid, receipt, 'discard'), answer(rid, receipt, 'discard w2'),
                          answer(rid, receipt, 'keep w1')]
                check('ac1/request-closed', 'an answer to the settled request is refused as request_closed '
                      + repr(closed), all(one.get('outcome') == 'refused' and one.get('reason') == 'request_closed'
                                          for one in closed))
                check('ac1/request-closed', 'and changes nothing: members 1 and 3 are deferred on disk, the new request open',
                      state_of(a) == 'deferred' and state_of(c) == 'deferred' and a_path.exists() and c_path.exists()
                      and asked(rid2).get('state') == 'OFFERED' and ledger.group(gid) == group
                      and refusal(a, rid) == 'space_disposition_unsettled')

                # Keep for one member: the owner's signed packet naming that member.
                presenter.present(rid2)
                receipt2 = presenter.current(rid2)
                kept_answer = answer(rid2, receipt2, 'keep w1')
                by_authority = ledger.authorize_disposition(a, rid2)
                for_other = authorize(c, rid2)
                check('ac1/member-keep', 'accept keep w1 is settled; the authority alone does not keep, and the owner '
                      'packet naming member 3 keeps nothing ' + repr((by_authority, for_other)),
                      kept_answer.get('outcome') == 'settled' and not by_authority.get('ok')
                      and by_authority.get('reason') == 'not_authorized' and not for_other.get('ok')
                      and state_of(a) == 'deferred' and state_of(c) == 'deferred'
                      and not ledger.item(c).get('owner_keep'))
                kept = authorize(a, rid2)
                group = ledger.group(gid)
                check('ac1/member-keep', 'the owner packet naming member 1 keeps it alone, and member 3 gets the third '
                      'request of the same record ' + repr(kept), kept.get('ok') and state_of(a) == 'kept'
                      and ledger.item(a).get('owner_keep') == {'by': 'owner'}
                      and contents(a_path / 'base.txt') == 'edited by pick-a\n' and state_of(c) == 'deferred'
                      and not ledger.item(c).get('owner_keep') and group['state'] == 'open'
                      and group['request']['number'] == 3 and group['request']['proposal']['indexes'] == [3]
                      and group['request']['proposal']['picks'] == [3])

                # The last member leaves by a member pick: the group closes.
                publish(c)
                rid3 = settle(c, 'save w3')
                applied = ledger.authorize_disposition(c, rid3)
                result = act(c)
                group = ledger.group(gid)
                try:
                    saved = git(repo, 'show', 'space-saved-pick-c:base.txt')
                except subprocess.CalledProcessError:
                    saved = None
                check('ac1/last-member', 'accept save w3 saves member 3 on its kept branch and removes it without force '
                      + repr(result), applied.get('ok') and state_of(c) == 'removed' and not c_path.exists()
                      and saved == 'edited by pick-c'
                      and '--force' not in str(ledger.item(c)['removal'].get('commands')))
                check('ac1/last-member', 'when its last member leaves the group closes, each member recorded with its '
                      'answer ' + repr(group.get('state')), group['state'] == 'closed'
                      and [(one.get('answer') or {}).get('choice') for one in group['members']]
                      == ['accept keep w1', 'accept discard w2', 'accept save w3']
                      and [one['number'] for one in group['requests']] == [1, 2, 3])
                fresh, fresh_path, fresh_owner = review('pick-d')
                finish(fresh, fresh_owner)
                check('ac1/last-member', 'and a deferral the same day opens the next sequence number '
                      + repr(group_of(fresh)[0]), group_of(fresh)[0] == SP.group_id(scope, today(), 2)
                      and ledger.group(gid) == group)
            except Exception:
                broke(('ac1/offer', 'ac1/member-discard', 'ac1/request-closed', 'ac1/member-keep', 'ac1/last-member'))

            try:
                ledger.disposition_publish = publish
                # A member that changed after the request was shown is not discarded by its member pick.
                next_day()
                made = [review('changed-a'), review('changed-b')]
                for item, path, owner in made:
                    finish(item, owner)
                (a, a_path, _), (b, b_path, _) = made
                gid, group = group_of(a)
                rid = request(a)
                presenter.present(rid)
                (b_path / 'late.txt').write_text('written after the request was shown')
                settle(a, 'discard w2')
                applied = ledger.authorize_disposition(b, rid)
                result = act(b)
                check('ac1/changed-member', 'the member whose file list changed is not removed: the new file and the '
                      'edit are on disk ' + repr(result), applied.get('ok') and b_path.exists()
                      and contents(b_path / 'late.txt') == 'written after the request was shown'
                      and contents(b_path / 'base.txt') == 'edited by changed-b\n' and state_of(b) == 'deferred')
                again, group = group_of(b)
                said = publish(b)
                check('ac1/changed-member', 'it is deferred again into the open group of the day, the same record, as '
                      'a new member with the next index and its new file list ' + repr(group.get('members')),
                      again == gid and len(day_groups()) == 1 and group['state'] == 'open'
                      and [(one['index'], one['item'], one['files'], bool(one.get('answer'))) for one in group['members']]
                      == [(1, a, ['base.txt'], False), (2, b, ['base.txt'], True),
                          (3, b, ['base.txt', 'late.txt'], False)]
                      and ledger.item(b)['disposition']['index'] == 3)
                check('ac1/changed-member', 'and the current request lists members 1 and 3 with the new file '
                      + repr(said), said.get('ok') and group['request']['number'] == 2
                      and group['request']['proposal']['indexes'] == [1, 3] and request(b) == request(a) != rid
                      and '"late.txt"' in asked(request(b)).get('brief', '')
                      and asked(request(b)).get('choices') == picks(1, 3)
                      and contents(a_path / 'base.txt') == 'edited by changed-a\n' and state_of(a) == 'deferred')
            except Exception:
                broke(('ac1/changed-member',))

            try:
                ledger.disposition_publish = publish
                # A member pick is an answer for no other member: the Ledger, Signal and the remover each say so.
                next_day()
                made = [review('other-a'), review('other-b')]
                for item, path, owner in made:
                    finish(item, owner)
                (a, a_path, _), (b, b_path, _) = made
                rid = settle(a, 'discard w2')
                effect = effect_of(rid)
                check('pick/ledger', 'the settled accept discard w2 is no settled answer for member 1, and is one for '
                      'member 2 ' + repr(effect.get('choice')), effect.get('choice') == 'accept discard w2'
                      and refusal(a, rid) == 'space_disposition_unsettled' and refusal(b, rid) is None)
                check('pick/ledger', 'the action it gives: discard to member 2, none to member 1',
                      ledger.settled_action(effect, ledger.item(b)['disposition']) == 'discard'
                      and ledger.settled_action(effect, ledger.item(a)['disposition']) is None
                      and ledger.settled_action(dict(effect, choice='accept save'), ledger.item(a)['disposition']) == 'save')
                force(a, effect, rid)
                with patch.object(ledger, 'disposition_effect', lambda item, request_id: (effect, 'owner')):
                    said = act(a)
                check('pick/signal', 'with member 1 written as authorized past the Ledger, and a Ledger that lets the '
                      'effect through, Signal carries nothing ' + repr(said), said.get('ok') is False
                      and said.get('reason') == 'space_disposition_unsettled' and state_of(a) == 'due'
                      and contents(a_path / 'base.txt') == 'edited by other-a\n')
                with patch.object(ledger, 'disposition_effect', lambda item, request_id: (effect, 'owner')), \
                        patch.object(ledger, 'settled_action', lambda effect_, decision: 'discard'):
                    said = act(a)
                check('pick/remover', 'with Signal let through as well, the remover refuses: member 1 is on disk with '
                      'its edit ' + repr(said), a_path.exists()
                      and contents(a_path / 'base.txt') == 'edited by other-a\n' and state_of(a) == 'deferred'
                      and 'names another member' in json.dumps(ledger.item(a).get('deferral')))
                check('pick/remover', 'and member 2, which the pick names, is untouched until its own authorization',
                      state_of(b) == 'deferred' and contents(b_path / 'base.txt') == 'edited by other-b\n')
            except Exception:
                broke(('pick/ledger', 'pick/signal', 'pick/remover'))

            try:
                ledger.disposition_publish = publish
                # A request for one worktree offers no member pick and takes none.
                next_day()
                item, path, owner = tree('single', ticket=False, station='build')
                signal(item, owner, 'run_finished')
                rid = request(item)
                presenter.present(rid)
                receipt = presenter.current(rid)
                unoffered = answer(rid, receipt, 'discard w1')
                check('pick/single', 'a request for one worktree offers exactly the three picks, and a member pick is no '
                      'offered choice ' + repr(unoffered), asked(rid).get('choices') == GROUP_PICKS
                      and unoffered.get('outcome') == 'refused' and unoffered.get('reason') == 'unmatched_choice')
                settle(item, 'discard')
                reference = asked(rid)['settlement']
                true = {eid: conn.execute('SELECT data FROM entities WHERE id=?', (eid,)).fetchone()[0]
                        for eid in (reference['settlement_id'], reference['effect_id'])}
                taken = refusal(item, rid)
                # Written directly, past the Settlement: the settled choice with a member index.
                for eid, raw in true.items():
                    conn.execute('UPDATE entities SET data=? WHERE id=?',
                                 (json.dumps(dict(json.loads(raw), choice='accept discard w1')), eid))
                conn.commit()
                refused = refusal(item, rid)
                for eid, raw in true.items():
                    conn.execute('UPDATE entities SET data=? WHERE id=?', (raw, eid))
                conn.commit()
                check('pick/single', 'a member pick written past the Settlement is no settled answer for one worktree: '
                      + repr((taken, refused)), taken is None and refused == 'space_disposition_unsettled'
                      and refusal(item, rid) is None and path.exists())
                shapes = {'accept discard w2': ('discard', 2), 'accept save': ('save', None), 'accept keep w10': ('keep', 10),
                          'accept discard w0': None, 'accept discard w02': None, 'accept discard 2': None,
                          'accept discard w2 w3': None, 'accept drop w2': None, 'discard w2': None, None: None}
                check('pick/single', 'a space pick is accept, the action and at most one member index',
                      all(ST.space_pick(choice) == found for choice, found in shapes.items()))
            except Exception:
                broke(('pick/single',))

            try:
                ledger.disposition_publish = publish
                # The terms of a group: each worktree's index, and the picks of the lowest indexes.
                def entry(n):
                    name = 'space:item:terms-%d' % n
                    return dict(item=name, path='/fixture/terms-%d' % n, branch=None, unheld_commits=True,
                                kept_branch='space-saved-terms-%d' % n, files=['a-%d.txt' % n], commits=[],
                                restore='veldo space restore ' + name)

                def offered(numbers, offered_picks, **changed):
                    proposal = {'discard': ST.SPACE_DISCARD, 'group': 'space:group:fixture:2026-11-16:1',
                                'worktrees': [entry(n) for n in numbers], 'indexes': numbers, 'picks': offered_picks}
                    proposal.update(changed)
                    return proposal

                shown = ST.space_presentation(offered([2, 5, 9], [2, 5]))
                check('terms/indexes', 'each worktree is named by its index in the group, not by its place in the list',
                      all(one in shown['brief'] for one in ('Worktree 2: "/fixture/terms-2"',
                                                            'Worktree 5: "/fixture/terms-5"',
                                                            'Worktree 9: "/fixture/terms-9"'))
                      and 'Worktree 1:' not in shown['brief'] and 'Worktree 3:' not in shown['brief'])
                check('terms/indexes', 'the choices are the group picks and the member picks of the offered indexes; the '
                      'text names the member without one ' + repr(shown['choices']), shown['choices'] == picks(2, 5)
                      and 'Worktrees with no answer of their own in this request: 9.' in shown['brief'])
                whole = ST.space_presentation(offered([2, 5, 9], [2, 5, 9]))
                check('terms/indexes', 'with a pick for every member no member is named as without one',
                      whole['choices'] == picks(2, 5, 9) and 'no answer of their own' not in whole['brief'])
                target = dict(kind='space_group', ref='space:group:fixture:2026-11-16:1',
                              members=[entry(n)['item'] for n in (2, 5, 9)])
                good = offered([2, 5, 9], [2, 5])
                recorded = settlement.terms(signed(command('terms', terms='terms-' + next_id(),
                    touchpoint='space_disposition', target=dict(target, digest=ST.digest(good)), proposal=good,
                    required_roles=[], quorum=None)))
                check('terms/indexes', 'such terms are recorded ' + repr(recorded), recorded.get('outcome') == 'recorded')
                for label, proposal in (
                        ('an index for another number of worktrees', offered([2, 5, 9], [2], indexes=[2, 5])),
                        ('indexes out of order', offered([2, 5, 9], [], indexes=[2, 9, 5])),
                        ('an index given twice', offered([2, 5, 9], [], indexes=[2, 5, 5])),
                        ('an index of zero', offered([2, 5, 9], [], indexes=[0, 5, 9])),
                        ('an index that is no number', offered([2, 5, 9], [], indexes=[2, 5, '9'])),
                        ('a pick for a member not listed', offered([2, 5, 9], [2, 7])),
                        ('a pick that skips a lower index', offered([2, 5, 9], [5])),
                        ('picks out of order', offered([2, 5, 9], [5, 2])),
                        ('no list of indexes', {key: value for key, value in good.items() if key != 'indexes'}),
                        ('no list of picks', {key: value for key, value in good.items() if key != 'picks'})):
                    try:
                        ST.space_presentation(proposal)
                        refused = False
                    except ST.Refused:
                        refused = True
                    check('terms/indexes', label + ' is refused', refused)
                single = {'discard': ST.SPACE_DISCARD, 'worktrees': [entry(1)]}
                for label, proposal in (('indexes', dict(single, indexes=[1])), ('picks', dict(single, picks=[1]))):
                    try:
                        ST.space_presentation(proposal)
                        refused = False
                    except ST.Refused:
                        refused = True
                    check('terms/indexes', 'terms for one worktree with ' + label + ' are refused', refused)
                check('terms/indexes', 'terms for one worktree offer the three picks, as before',
                      ST.space_presentation(single)['choices'] == GROUP_PICKS)
            except Exception:
                broke(('terms/indexes',))

            try:
                ledger.disposition_publish = publish
                # AC2: more members than one message part has room for.
                next_day()
                COUNT = 74
                ledger.disposition_publish = None
                many = [review('fit-%02d' % n) for n in range(1, COUNT + 1)]
                for item, path, owner in many:
                    finish(item, owner)
                ledger.disposition_publish = publish
                first = many[0][0]
                gid, group = group_of(first)
                proposal = group['request']['proposal']
                offered_picks = proposal['picks']
                k = len(offered_picks)
                said = publish(first)
                rid = request(first)
                sent = len(transport.sent)
                presented = presenter.present(rid)
                receipt = presenter.current(rid) or {}
                parts = transport.sent[sent:]
                opened = asked(rid)
                check('ac2/fit', 'the request offers the group picks and the member picks of the lowest %d of %d '
                      'members' % (k, COUNT), 0 < k < COUNT and offered_picks == list(range(1, k + 1))
                      and proposal['indexes'] == list(range(1, COUNT + 1))
                      and opened.get('choices') == picks(*offered_picks))
                check('ac2/fit', 'the presentation is rendered and sent, the choices in its last part '
                      + repr((said.get('ok'), presented.get('outcome') if isinstance(presented, dict) else presented)),
                      receipt.get('outcome') == 'published' and receipt.get('choices') == picks(*offered_picks)
                      and len(parts) > 1 and 'Choices: accept save | accept keep | accept discard | accept save w1 |'
                      in parts[-1] and parts[-1].rstrip().endswith('<choice>: <your reason>')
                      and 'accept discard w%d\n' % k in parts[-1] and 'w%d' % (k + 1) not in parts[-1]
                      and all(V.utf16_units(part) <= V.MESSAGE_LIMIT for part in parts))
                without = ', '.join('%d' % n for n in range(k + 1, COUNT + 1))
                check('ac2/fit', 'its text names the members without a pick: ' + without,
                      'Worktrees with no answer of their own in this request: %s.' % without in opened.get('brief', '')
                      and all('Worktree %d: %s' % (n, json.dumps(str(path))) in opened['brief']
                              for n, (_, path, _) in enumerate(many, 1)))
                more = dict(receipt, choices=list(receipt.get('choices') or [])
                            + ['accept %s w%d' % (word, k + 1) for word in ('save', 'keep', 'discard')])
                try:
                    V.render(more)
                    too_long = False
                except ValueError as error:
                    too_long = str(error) == 'presentation_too_long'
                check('ac2/fit', 'the picks of member %d would not fit: the presenter refuses to render them' % (k + 1),
                      too_long and bool(receipt) and V.render(receipt) == receipt.get('rendered'))
                beyond = answer(rid, receipt, 'discard w%d' % COUNT) if receipt else {}
                check('ac2/fit', 'an answer for a member without a pick names no offered choice ' + repr(beyond),
                      beyond.get('outcome') == 'refused' and beyond.get('reason') == 'unmatched_choice'
                      and state_of(many[-1][0]) == 'deferred' and many[-1][1].exists())

                # A member pick makes the next request shorter: it reaches the members after.
                tenth, tenth_path, _ = many[9]
                picked = answer(rid, receipt, 'discard w10') if receipt else {}
                applied = ledger.authorize_disposition(tenth, rid)
                carried = act(tenth)
                later = ledger.group(gid)['request']['proposal']
                publish(first)
                rid2 = request(first)
                presenter.present(rid2)
                receipt2 = presenter.current(rid2) or {}
                reached = [n for n in range(1, k + 2) if n != 10]
                check('ac2/next', 'accept discard w10 discards member 10 alone ' + repr((picked.get('outcome'), carried)),
                      applied.get('ok') and state_of(tenth) == 'removed' and not tenth_path.exists()
                      and contents(snapshot(tenth) / 'work' / 'base.txt') == 'edited by fit-10\n'
                      and sum(1 for item, path, _ in many if path.exists() and state_of(item) == 'deferred') == COUNT - 1)
                check('ac2/next', 'the next request offers picks to the members after: member %d has one now '
                      % (k + 1) + repr(later['picks'][-3:]), later['indexes'] == [n for n in range(1, COUNT + 1) if n != 10]
                      and later['picks'] == reached and rid2 != rid
                      and receipt2.get('outcome') == 'published' and receipt2.get('choices') == picks(*reached)
                      and 'Worktrees with no answer of their own in this request: %s.'
                      % ', '.join('%d' % n for n in range(k + 2, COUNT + 1)) in asked(rid2).get('brief', ''))
            except Exception:
                broke(('ac2/fit', 'ac2/next'))

            try:
                ledger.disposition_publish = publish
                # AC3: while a group is open a deferral joins it, also after a member pick.
                next_day()
                (a, a_path, a_owner), (b, b_path, b_owner) = review('open-a'), review('open-b')
                finish(a, a_owner)
                gid, _ = group_of(a)
                finish(b, b_owner)
                check('ac3/one-open', 'while the day group is open a deferral joins it ' + repr(group_of(b)[0]),
                      group_of(b)[0] == gid == SP.group_id(scope, today(), 1) and len(day_groups()) == 1
                      and request(b) == request(a))
                rid = settle(a, 'discard w1')
                applied = ledger.authorize_disposition(a, rid)
                act(a)
                c, c_path, c_owner = review('open-c')
                finish(c, c_owner)
                joined, group = group_of(c)
                check('ac3/one-open', 'after a member pick the group is still the one open group of the day, and the '
                      'next deferral joins it under the next index ' + repr(group.get('request')),
                      applied.get('ok') and joined == gid and len(day_groups()) == 1 and group['state'] == 'open'
                      and [(one['index'], one['item']) for one in group['members']] == [(1, a), (2, b), (3, c)]
                      and group['request']['number'] == 2 and group['request']['version'] == 2
                      and group['request']['proposal']['indexes'] == [2, 3])
                check('ac3/one-open', 'its request is the group current request, at a new version that lists it',
                      request(c) == request(b) != rid and asked(request(c)).get('state') == 'OFFERED'
                      and json.dumps(str(c_path)) in asked(request(c)).get('brief', '')
                      and asked(request(c)).get('choices') == picks(2, 3))
            except Exception:
                broke(('ac3/one-open',))

            try:
                ledger.disposition_publish = publish
                # AC3: after the day's group is closed by an answer, a deferral opens the next sequence number.
                next_day()
                x, x_path, x_owner = review('next-a')
                finish(x, x_owner)
                gid, _ = group_of(x)
                rid = settle(x, 'save')
                applied = ledger.authorize_disposition(x, rid)
                act(x)
                closed = ledger.group(gid)
                y, y_path, y_owner = review('next-b')
                result = finish(y, y_owner)
                decision = (ledger.item(y) or {}).get('disposition') or {}
                second, group = group_of(y)
                check('ac3/next-sequence', 'the day group is closed by the answer ' + repr(applied),
                      applied.get('ok') and closed['state'] == 'closed' and closed['sequence'] == 1)
                check('ac3/next-sequence', 'the worktree deferred the same day has a request ' + repr(result.get('items')),
                      bool(decision) and decision.get('state') == 'requested'
                      and asked(I.assignment_id(ids['repository_uuid'], decision.get('alias', ''))).get('state') == 'OFFERED')
                check('ac3/next-sequence', 'in a new group with the next sequence number, with its own request '
                      + repr(second), second == SP.group_id(scope, today(), 2) and group.get('sequence') == 2
                      and group.get('state') == 'open' and [one['item'] for one in group.get('members') or []] == [y]
                      and bool(decision) and request(y) != rid and len(day_groups()) == 2
                      and sum(1 for one in day_groups().values() if one['state'] == 'open') == 1)
                check('ac3/next-sequence', 'the closed group is as it was closed, and the worktree is on disk with its edit',
                      ledger.group(gid) == closed and contents(y_path / 'base.txt') == 'edited by next-b\n')
            except Exception:
                broke(('ac3/next-sequence',))

            try:
                ledger.disposition_publish = publish
                # A deferral between a settled member pick and its application joins the same group.
                next_day()
                (a, a_path, a_owner), (b, b_path, b_owner) = review('window-a'), review('window-b')
                finish(a, a_owner)
                finish(b, b_owner)
                gid, _ = group_of(a)
                rid = settle(a, 'discard w1')
                frozen = ledger.group(gid)['request']
                c, c_path, c_owner = review('window-c')
                finish(c, c_owner)
                joined, group = group_of(c)
                check('ac3/pending-join', 'the deferral joins the same group: one open group that day ' + repr(joined),
                      joined == gid and len(day_groups()) == 1
                      and [(one['index'], one['item']) for one in group.get('members') or []] == [(1, a), (2, b), (3, c)])
                waits = publish(c)
                check('ac3/pending-join', 'it is on no request yet: the settled request is not revised ' + repr(waits),
                      group.get('request') == frozen and asked(rid).get('state') == 'SATISFIED'
                      and waits.get('reason') == 'space_group_answered' and state_of(c) == 'deferred'
                      and contents(c_path / 'base.txt') == 'edited by window-c\n')
                applied = ledger.authorize_disposition(a, rid)
                act(a)
                said = publish(c)
                group = ledger.group(gid)
                check('ac3/pending-join', 'the request raised when the pick is applied lists it ' + repr(said),
                      applied.get('ok') and said.get('ok') and group['request']['number'] == 2
                      and group['request']['proposal']['indexes'] == [2, 3] and request(c) == request(b) != rid
                      and json.dumps(str(c_path)) in asked(request(c)).get('brief', '')
                      and state_of(a) == 'removed' and b_path.exists() and c_path.exists())
            except Exception:
                broke(('ac3/pending-join',))

            try:
                ledger.disposition_publish = publish
                next_day()
                made = [review('keep-next-a'), review('keep-next-b'), review('keep-next-c')]
                for item, path, owner in made:
                    finish(item, owner)
                (a, a_path, _), (b, b_path, _), (c, c_path, _) = made
                gid, _ = group_of(a)
                rid = settle(a, 'keep w2')
                old = dict(ledger.item(b)['disposition'])
                said = publish(a)
                rid2 = request(a)
                group = ledger.group(gid)
                check('next/settled-keep', 'settled Keep raises request 2 for members 1 and 3 without an owner packet',
                      said.get('ok') and rid2 != rid and request(c) == rid2
                      and group['request']['number'] == 2 and asked(rid2).get('choices') == picks(1, 3)
                      and ledger.item(b)['disposition'] == old and state_of(b) == 'deferred'
                      and not ledger.item(b).get('owner_keep')
                      and all(contents(path / 'base.txt') == 'edited by ' + label + '\n'
                              for path, label in ((a_path, 'keep-next-a'), (b_path, 'keep-next-b'),
                                                  (c_path, 'keep-next-c'))))
                check('next/keep-text', 'the brief explains settlement advances others while Keep awaits its packet',
                      'For Keep, the others get their new request after settlement' in asked(rid)['brief']
                      and 'the picked worktree stays pending the owner signed packet' in asked(rid)['brief']
                      and rid2 != rid and state_of(b) == 'deferred')
                d, d_path, d_owner = review('keep-next-d')
                finish(d, d_owner)
                check('next/keep-join', 'a later same-day deferral joins request 2, with one group and no duplicate',
                      group_of(d)[0] == gid and len(day_groups()) == 1 and request(d) == rid2
                      and asked(rid2).get('choices') == picks(1, 3, 4)
                      and len(assignments(SP.group_alias(gid))) == 2 and d_path.exists())
                # Close the remaining group before the original Keep packet arrives.
                current = settle(a, 'discard')
                authorized = ledger.authorize_disposition(a, current)
                for item in (a, c, d):
                    act(item)
                publish(b)
                late = authorize(b, rid)
                check('next/settled-keep', 'the old alias accepts only the original member packet after group closure',
                      authorized.get('ok') and late.get('ok') and state_of(b) == 'kept'
                      and ledger.item(b).get('owner_keep') == {'by': 'owner'}
                      and request(b) == rid and group_of(b)[0] == gid and len(day_groups()) == 1
                      and contents(b_path / 'base.txt') == 'edited by keep-next-b\n')
            except Exception:
                broke(('next/settled-keep', 'next/keep-join', 'next/keep-text'))

            try:
                ledger.disposition_publish = publish
                next_day()
                made = [review('left-a'), review('left-b'), review('left-c')]
                for item, path, owner in made:
                    finish(item, owner)
                (a, a_path, _), (b, b_path, _), (c, c_path, c_owner) = made
                gid, _ = group_of(a)
                rid = settle(a, 'discard w2')
                # An event starts judging member 3 again before member 2 is authorized.
                subject = dict(c_owner, run=c_owner['run']['id'])
                judging = ledger.signal('run_finished', subject)
                applied = ledger.authorize_disposition(b, rid)
                act(b)
                group = ledger.group(gid)
                check('next/left-member', 'member 3 left during the pick write and is marked gone',
                      judging.get('ok') and applied.get('ok') and state_of(c) == 'due'
                      and group['members'][2].get('gone') is True
                      and group['request']['proposal']['indexes'] == [1])
                rejudged = SIG._carry(ledger, PR, K, RM, 'run_finished', [c],
                    **{key: value for key, value in given.items() if key not in ('probe', 'kinds', 'remover')})
                publish(a)
                group = ledger.group(gid)
                check('next/left-member', 'survivor 1 cannot block member 3 from rejoining under index 4 '
                      + repr((rejudged, ledger.item(c)['disposition'], group['request'])),
                      state_of(c) == 'deferred' and group_of(c)[0] == gid
                      and ledger.item(c)['disposition']['index'] == 4
                      and group['request']['proposal']['indexes'] == [1, 4]
                      and asked(request(c)).get('choices') == picks(1, 4)
                      and contents(c_path / 'base.txt') == 'edited by left-c\n' and a_path.exists())
            except Exception:
                broke(('next/left-member',))

            try:
                ledger.disposition_publish = publish
                # The member a settled pick names has gone before the pick is applied.
                next_day()
                made = [review('gone-a'), review('gone-b'), review('gone-c')]
                for item, path, owner in made:
                    finish(item, owner)
                (a, a_path, _), (b, b_path, b_owner), (c, c_path, _) = made
                gid, _ = group_of(a)
                rid = settle(a, 'discard w2')
                # The fixture's own worktree, removed by the fixture, and the Ledger told it is gone, as
                # reconcile tells it of an item that is no longer on disk.
                git(repo, 'worktree', 'remove', '--force', str(b_path))
                went = ledger.gone(b)
                refused = ledger.authorize_disposition(b, rid)
                check('next/gone', 'member 2 is gone and its pick cannot be applied ' + repr((went, refused)),
                      went.get('ok') and state_of(b) == 'gone' and not refused.get('ok'))
                said = publish(a)
                group = ledger.group(gid)
                check('next/gone', 'the next publish raises the new request for the members left, on the same record '
                      + repr(said), said.get('ok') and group['state'] == 'open' and group['request']['number'] == 2
                      and group['request']['proposal']['indexes'] == [1, 3]
                      and [bool(one.get('gone')) for one in group['members']] == [False, True, False]
                      and group['requests'][0]['answer']['member'] == 2 and group['requests'][0]['answer']['applied'] == []
                      and request(a) == request(c) != rid and asked(request(a)).get('state') == 'OFFERED'
                      and asked(request(a)).get('choices') == picks(1, 3))
                check('next/gone', 'members 1 and 3 are deferred on disk with their edits',
                      all(state_of(item) == 'deferred' and contents(path / 'base.txt') == 'edited by ' + label + '\n'
                          for item, path, label in ((a, a_path, 'gone-a'), (c, c_path, 'gone-c'))))
                start = head_seq()
                again = ledger._group_next(gid)
                check('next/gone', 'with no settled pick waiting, nothing is raised and nothing written ' + repr(again),
                      not again.get('ok') and written(start) == [])
            except Exception:
                broke(('next/gone',))

            try:
                ledger.disposition_publish = publish
                # The service's disposition task, unchanged, carries a member pick and raises the next request.
                next_day()
                SV, CON = load('control_service'), load('control_space_consumer')
                service = object.__new__(SV.Service)
                service._space = dict(given, ledger=ledger)
                service.conn, service.domain, service.store = conn, ids['domain_uuid'], ids['store_uuid']
                service.principal, service.sign, service.generation = 'steward', journal_sign, 1
                service.config = {'journal_key': str(keys['steward'])}
                service.channel = types.SimpleNamespace(record=lambda: {'owner': 'owner'},
                    ingress=types.SimpleNamespace(activations=types.SimpleNamespace(ids=ids)))
                service.space_consumer = CON.Consumer(ledger, given)
                ledger.disposition_publish = None
                made = [review('worker-a'), review('worker-b'), review('worker-c')]
                for item, path, owner in made:
                    finish(item, owner)
                ledger.disposition_publish = publish
                (a, a_path, _), (b, b_path, _), (c, c_path, _) = made
                gid, _ = group_of(a)
                try:
                    result = service.space_consumer.run(service._space_dispositions)
                    rid = request(a)
                    check('worker/member-pick', 'the task publishes the group request with its member picks '
                          + repr(result.get('ok')), result.get('ok') and result.get('worker') != os.getpid()
                          and asked(rid).get('choices') == picks(1, 2, 3))
                    settle(a, 'discard w2')
                    result = service.space_consumer.run(service._space_dispositions)
                    check('worker/member-pick', 'one pass carries the Discard of member 2 alone, in the worker '
                          + repr(result), result.get('ok') and result.get('worker') != os.getpid()
                          and state_of(b) == 'removed' and not b_path.exists()
                          and contents(snapshot(b) / 'work' / 'base.txt') == 'edited by worker-b\n'
                          and all(state_of(item) == 'deferred' and path.exists() for item, path in ((a, a_path), (c, c_path))))
                    result = service.space_consumer.run(service._space_dispositions)
                    group = ledger.group(gid)
                    check('worker/member-pick', 'and the request for members 1 and 3 is raised by the task '
                          + repr(group.get('request', {}).get('number')), group['state'] == 'open'
                          and group['request']['number'] == 2 and request(a) == request(c) != rid
                          and asked(request(a)).get('state') == 'OFFERED'
                          and asked(request(a)).get('choices') == picks(1, 3))
                    # The journal notification the service wakes on: the members left are written with the pick.
                    wake = [value for change in written(0) for key, value in change.items()
                            if key in (a, c) and value.get('kind') == 'space_item'
                            and value['data'].get('state') == 'deferred'
                            and (value['data'].get('disposition') or {}).get('alias') == group['request']['alias']]
                    check('worker/member-pick', 'the write of the pick names the members left as deferred with a '
                          'requested disposition, which is what the service wakes on', len(wake) >= 2
                          and all((value['data'].get('disposition') or {}).get('state') == 'requested' for value in wake))
                    kept_rid = settle(a, 'keep w1')
                    result = service.space_consumer.run(service._space_dispositions)
                    check('worker/member-pick', 'the worker advances a settled Keep without an owner packet',
                          result.get('ok') and result.get('worker') != os.getpid()
                          and state_of(a) == 'deferred' and request(a) == kept_rid
                          and not ledger.item(a).get('owner_keep') and a_path.exists()
                          and ledger.group(gid)['request']['number'] == 3
                          and asked(request(c)).get('choices') == picks(3))
                finally:
                    service.space_consumer.stop()
            except Exception:
                broke(('worker/member-pick',))
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            conn.close()

    for row, checks in sorted(rows.items()):
        bad = '; '.join(label for label, good in checks if not good)
        if bad:
            print('DETAIL space342/' + row + ': ' + bad)
        expect('space342/' + row, bool(checks) and all(good for _, good in checks))


_v342_suite()
