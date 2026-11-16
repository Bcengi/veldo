"""VELDO-0340: review worktrees with unique work share one request per scope and day.

Real Git worktrees, the keep step and its snapshots, signed terms, the inbox, the presenter and the
settlement on a temporary SQLite store. Only Telegram's send is a fixture transport, and the
Ledger's clock is the fixture's: a row moves it by a day. Keys are generated in the fixture root.
No engine and no host worktree is used.

AC1 rows: ac1/one-request (two review worktrees with tracked edits deferred on one day: one group
record, one request that lists both; the falsifier row), ac1/next-day (a third on the next day
raises a second request, and the first day's request and record are byte for byte what they were).
AC2 rows: ac2/new-version (a later deferral of the day publishes a new version, and an answer bound
to the earlier presentation settles nothing, before and after the new one is presented; the
falsifier row), ac2/clock (the clock moved a day with no deferral: no request, no group, no
version, no message), ac2/unseen-member (an answer that settled before the new version was
published reaches only the members it showed; the other joins a new group).
AC3 rows: ac3/save, ac3/keep, ac3/discard (the falsifier row: a file added to one member after the
request was shown), ac3/closed (the group closes with the pick, and a later deferral of the day
opens the next sequence number),
ac3/answered-takes-no-join (a deferral after the answer and before it is applied opens the next
group). AC4 row: ac4/builder (a detached worktree of a build run keeps its untracked file at run finished
and raises a request of its own, in no group).
Terms rows: terms/group (the widened terms: a group target that names every member; one worktree
without a group as before), worker/group (the service's own disposition task publishes a group's
request and carries its pick in the worker child, unchanged).
"""


def _v340_suite():
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
        spec = importlib.util.spec_from_file_location('v340_' + name, mods / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0340-') as temporary:
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

        try:
            # AC1: two on one day raise one request; a third on the next day raises a second.
            before = set(assignments())
            first, first_path, first_owner = review('one-a')
            second, second_path, second_owner = review('one-b')
            results = [finish(first, first_owner), finish(second, second_owner)]
            day_one = {eid: row for eid, row in assignments().items() if eid not in before}
            gid, group = group_of(first)
            check('ac1/one-request', 'day 1 holds one request for the two worktrees, not %d: %r'
                  % (len(day_one), sorted(row[1].get('alias') for row in day_one.values())), len(day_one) == 1)
            check('ac1/one-request', 'both are deferred as unique work, each still on disk with its edit '
                  + repr(results), all(state_of(one) == 'deferred' for one in (first, second))
                  and contents(first_path / 'base.txt') == 'edited by one-a\n'
                  and contents(second_path / 'base.txt') == 'edited by one-b\n')
            check('ac1/one-request', 'one group record of the scope and day, sequence 1, open ' + repr(group),
                  gid == SP.group_id(scope, today(), 1) == group_of(second)[0] and len(ledger.groups()) == 1
                  and group.get('state') == 'open' and group.get('day') == today() and group.get('sequence') == 1
                  and group.get('scope') == scope)
            members = group.get('members') or []
            check('ac1/one-request', 'the record holds each member with its index, run and file list ' + repr(members),
                  [(one['index'], one['item'], one['run'], one['files']) for one in members]
                  == [(1, first, 'one-a', ['base.txt']), (2, second, 'one-b', ['base.txt'])])
            check('ac1/one-request', 'the record holds the current request with its version '
                  + repr(group.get('request')), (group.get('request') or {}).get('version') == 2
                  and [one['item'] for one in group['request']['proposal']['worktrees']] == [first, second])
            check('ac1/one-request', 'each item names the group in its deferral',
                  all(ledger.item(one)['deferral'].get('review_group') == gid for one in (first, second)))
            if len(day_one) == 1:
                rid = next(iter(day_one))
                sent = len(transport.sent)
                presenter.present(rid)
                brief = '\n'.join(transport.sent[sent:])
                check('ac1/one-request', 'the one request shows both worktrees, each with its path, files and '
                      'restore command ' + repr(brief), all(text in brief for text in (
                          'Review group: ' + json.dumps(gid), 'Worktree 1: ' + json.dumps(str(first_path)),
                          'Worktree 2: ' + json.dumps(str(second_path)), 'Item: ' + json.dumps(first),
                          'Item: ' + json.dumps(second), 'veldo space restore'))
                      and brief.count('"base.txt"') == 2)
                terms = ledger._row(day_one[rid][1]['subject']['ref'], ST.TERMS_KIND)[1] or {}
                check('ac1/one-request', 'its terms target the group and name every member item '
                      + repr(terms.get('target')), (terms.get('target') or {}).get('kind') == 'space_group'
                      and terms['target'].get('ref') == gid and terms['target'].get('members') == [first, second])
            frozen = (assignments(), ledger._row(gid, SP.GROUP_KIND), len(transport.sent))
            next_day()
            third, third_path, third_owner = review('one-c')
            finish(third, third_owner)
            later, later_group = group_of(third)
            added = {eid: row for eid, row in assignments().items() if eid not in frozen[0]}
            check('ac1/next-day', 'the third worktree, a day later, raises a second request ' + repr(sorted(added)),
                  len(added) == 1 and later == SP.group_id(scope, today(), 1) and later != gid
                  and [one['item'] for one in later_group.get('members') or []] == [third])
            check('ac1/next-day', 'the first day request and its record are unchanged',
                  all(assignments().get(eid) == row for eid, row in frozen[0].items())
                  and ledger._row(gid, SP.GROUP_KIND) == frozen[1])
            with patch.dict(ledger.config, {'time_zone': 'Pacific/Auckland'}):
                far = ledger.day_of(now[0])
            check('ac1/next-day', 'the day is read in the installation time zone: noon UTC is %s there' % far,
                  far == (datetime.datetime.fromtimestamp(now[0], datetime.timezone.utc).date()
                          + datetime.timedelta(days=1)).isoformat() and ledger.day_of(now[0]) == today())

            # AC2: a later deferral of the day is a new version; the old presentation settles nothing.
            next_day()
            early, early_path, early_owner = review('version-a')
            finish(early, early_owner)
            gid, group = group_of(early)
            rid = request(early) if gid else None
            if rid:
                presenter.present(rid)
            old = presenter.current(rid) if rid else None
            late, late_path, late_owner = review('version-b')
            finish(late, late_owner)
            same, group = group_of(late)
            record = (ledger._row(rid, 'assignment')[1] or {}) if rid else {}
            check('ac2/new-version', 'the later deferral joins the same group and request ' + repr((gid, same)),
                  bool(gid) and same == gid and bool(rid) and request(late) == rid)
            check('ac2/new-version', 'the request is at a new version, with terms that list both: version %r, '
                  'record version %r' % (record.get('request_version'), (group.get('request') or {}).get('version')),
                  bool(old) and record.get('request_version') == old['request_version'] + 1
                  and (group.get('request') or {}).get('version') == 2
                  and json.dumps(str(late_path)) in record.get('brief', ''))
            if old:
                unpresented = answer(rid, old, 'discard')
                check('ac2/new-version', 'an answer bound to the earlier presentation settles nothing, before the '
                      'new one is presented ' + repr(unpresented), unpresented.get('outcome') == 'refused'
                      and unpresented.get('reason') == 'stale_presentation')
                presenter.present(rid)
                new = presenter.current(rid)
                presented = answer(rid, old, 'discard')
                check('ac2/new-version', 'and after it is presented ' + repr(presented),
                      presented.get('outcome') == 'refused' and presented.get('reason') == 'stale_presentation'
                      and new['presentation_id'] != old['presentation_id']
                      and new['request_version'] == old['request_version'] + 1)
                check('ac2/new-version', 'nothing was settled: the request is open, the group open, both worktrees '
                      'deferred and on disk', ledger._row(rid, 'assignment')[1]['state'] == 'OFFERED'
                      and group_of(early)[1].get('state') == 'open'
                      and all(state_of(one) == 'deferred' for one in (early, late))
                      and contents(early_path / 'base.txt') == 'edited by version-a\n'
                      and contents(late_path / 'base.txt') == 'edited by version-b\n')
                try:
                    ledger.disposition_effect(late, rid)
                    reached = True
                except SP.Refused:
                    reached = False
                check('ac2/new-version', 'the worktree the owner never saw has no settled answer', not reached)

            # AC2: the clock opens and sends nothing.
            def counted():
                return (assignments(), ledger.groups(), len(transport.sent),
                        conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0])
            def shown_again():
                for member in (first, second, third, early, late):
                    ledger.disposition_publish(member)
                    presenter.present(request(member))
            shown_again()
            still = counted()
            next_day()
            other = SIG.signal(ledger, 'run_finished', {'run': 'a-run-with-no-item'}, **given)
            check('ac2/clock', 'with the clock moved a day and no deferral there is no new request, group, '
                  'version or message ' + repr(other.get('items')), other.get('ok') is True
                  and other.get('items') == [] and counted() == still)
            shown_again()
            after = counted()
            check('ac2/clock', 'publishing and presenting again a day later changes no request and no group, '
                  'and writes nothing: journal %d then %d' % (still[3], after[3]), after == still)

            # An answer that settled before the new version was published reaches only what it showed.
            next_day()
            seen, seen_path, seen_owner = review('unseen-a')
            finish(seen, seen_owner)
            rid = request(seen)
            publish = ledger.disposition_publish
            ledger.disposition_publish = None
            unseen, unseen_path, unseen_owner = review('unseen-b')
            finish(unseen, unseen_owner)
            ledger.disposition_publish = publish
            gid, group = group_of(unseen)
            settled = settle(seen, 'discard')
            said = publish(unseen)
            applied = ledger.authorize_disposition(seen, settled)
            closed = ledger.group(gid)
            check('ac2/unseen-member', 'the pick reaches the member it showed and closes the group '
                  + repr((applied, closed.get('answer'))), applied.get('ok') and state_of(seen) == 'due'
                  and closed['state'] == 'closed' and closed['answer']['applied'] == [1]
                  and closed['answer']['unseen'] == [2])
            check('ac2/unseen-member', 'the member that joined unpublished is untouched, and its publish said the '
                  'request was answered ' + repr(said), state_of(unseen) == 'deferred' and unseen_path.exists()
                  and said.get('reason') == 'space_group_answered'
                  and ledger.item(unseen)['disposition']['state'] == 'requested')
            again = publish(unseen)
            moved, moved_group = group_of(unseen)
            check('ac2/unseen-member', 'at its next publish it joins a new group of its day with its own request '
                  + repr(again), again.get('ok') and moved == SP.group_id(scope, today(), 2)
                  and moved_group.get('state') == 'open'
                  and [one['item'] for one in moved_group['members']] == [unseen]
                  and request(unseen) != rid and ledger._row(request(unseen), 'assignment')[1] is not None)
            carried = act(seen)
            check('ac2/unseen-member', 'the shown member is discarded, the other stays ' + repr(carried),
                  state_of(seen) == 'removed' and not seen_path.exists() and unseen_path.exists()
                  and contents(unseen_path / 'base.txt') == 'edited by unseen-b\n')

            # AC3, Save: each on its kept branch, removed without force.
            next_day()
            made = [review('save-a'), review('save-b')]
            for item, path, owner in made:
                finish(item, owner)
            gid, group = group_of(made[0][0])
            rid = settle(made[0][0], 'save')
            applied = ledger.authorize_disposition(made[1][0], rid)
            check('ac3/save', 'one pick makes every member due and closes the group ' + repr(applied),
                  applied.get('ok') and all(state_of(item) == 'due' for item, _, _ in made)
                  and ledger.group(gid)['state'] == 'closed' and ledger.group(gid)['answer']['applied'] == [1, 2])
            for item, path, owner in made:
                label = owner['run']['id']
                result = act(item)
                record = ledger.item(item)
                branch = 'space-saved-' + label
                try:
                    kept = git(repo, 'show', branch + ':base.txt')
                except subprocess.CalledProcessError:
                    kept = None
                check('ac3/save', label + ' is committed on ' + branch + ' and removed without force ' + repr(result),
                      record['state'] == 'removed' and not path.exists() and kept == 'edited by ' + label
                      and record['removal'].get('kept_branch') == branch
                      and '--force' not in str(record['removal'].get('commands')))

            # AC3, Keep: the owner's signed packet for one member keeps each.
            next_day()
            made = [review('keep-a'), review('keep-b')]
            for item, path, owner in made:
                finish(item, owner)
            gid, group = group_of(made[0][0])
            rid = settle(made[0][0], 'keep')
            # Answered and not yet applied: the request takes no join, so a deferral opens the next group.
            after, after_path, after_owner = review('keep-c')
            finish(after, after_owner)
            check('ac3/answered-takes-no-join', 'a deferral after the answer opens the next group of the day '
                  + repr(group_of(after)[0]), group_of(after)[0] == SP.group_id(scope, today(), 2)
                  and [one['item'] for one in ledger.group(gid)['members']] == [made[0][0], made[1][0]]
                  and ledger.group(gid)['request']['version'] == 2
                  and ledger._row(request(after), 'assignment')[1] is not None and request(after) != rid)
            refused = ledger.authorize_disposition(made[0][0], rid)
            start = conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]
            applied = authorize(made[0][0], rid)
            writes = [json.loads(raw) for (raw,) in conn.execute('SELECT transition FROM journal WHERE seq>?', (start,))]
            check('ac3/keep', 'Keep is the owner signed packet, never the authority alone ' + repr(refused),
                  not refused.get('ok'))
            check('ac3/keep', 'one packet sets each member to kept, with the mark, and closes the group, in one write '
                  + repr(applied), applied.get('ok') and all(
                      state_of(item) == 'kept' and ledger.item(item).get('owner_keep') == {'by': 'owner'}
                      and path.exists() and contents(path / 'base.txt') == 'edited by ' + owner['run']['id'] + '\n'
                      for item, path, owner in made)
                  and ledger.group(gid)['state'] == 'closed' and len(writes) == 1
                  and {made[0][0], made[1][0], gid} <= set(writes[0]))
            check('ac3/answered-takes-no-join', 'and the Keep leaves it deferred in its own open group',
                  state_of(after) == 'deferred' and not ledger.item(after).get('owner_keep')
                  and group_of(after)[1].get('state') == 'open')

            # AC3, Discard: saved first; a member whose list changed is deferred again, into a new group.
            next_day()
            made = [review('discard-a'), review('discard-b')]
            for item, path, owner in made:
                finish(item, owner)
            gid, group = group_of(made[0][0])
            rid = request(made[0][0])
            presenter.present(rid)
            (made[1][1] / 'late.txt').write_text('written after the request was shown')
            settle(made[0][0], 'discard')
            applied = ledger.authorize_disposition(made[0][0], rid)
            results = [act(item) for item, _, _ in made]
            item, path, owner = made[0]
            record = ledger.item(item)
            check('ac3/discard', 'the unchanged member is saved in the snapshot store and then removed '
                  + repr(results[0]), applied.get('ok') and record['state'] == 'removed' and not path.exists()
                  and snapshot(item) is not None
                  and contents(snapshot(item) / 'work' / 'base.txt') == 'edited by discard-a\n'
                  and str(snapshot(item)).startswith(str(state / 'space-saved'))
                  and '--force' in str(record['removal'].get('commands')))
            item, path, owner = made[1]
            check('ac3/discard', 'the member with a file added after the request was shown is not removed: the file '
                  'and the edit are on disk ' + repr(results[1]), path.exists() and state_of(item) == 'deferred'
                  and contents(path / 'late.txt') == 'written after the request was shown'
                  and contents(path / 'base.txt') == 'edited by discard-b\n')
            again, again_group = group_of(item)
            ledger.disposition_publish(item)
            check('ac3/discard', 'it is deferred again into a new group, whose request lists the new file '
                  + repr((again, again_group.get('members'))), again == SP.group_id(scope, today(), 2)
                  and again_group.get('state') == 'open'
                  and [(one['item'], one['files']) for one in again_group.get('members') or []]
                  == [(item, ['base.txt', 'late.txt'])]
                  and request(item) != rid and ledger._row(request(item), 'assignment')[1] is not None)
            check('ac3/closed', 'the answered group is closed and is not added to ' + repr(ledger.group(gid)),
                  ledger.group(gid)['state'] == 'closed' and len(ledger.group(gid)['members']) == 2
                  and ledger.group(gid)['request']['version'] == 2)
            fresh, fresh_path, fresh_owner = review('discard-c')
            finish(fresh, fresh_owner)
            check('ac3/closed', 'a later deferral of the day joins the open group with the next sequence number',
                  group_of(fresh)[0] == again and [one['index'] for one in group_of(fresh)[1]['members']] == [1, 2])

            # AC4: a detached worktree of a run of another station keeps its file and asks for itself.
            next_day()
            groups = ledger.groups()
            item, path, owner = tree('builder', ticket=False, station='build')
            result = signal(item, owner, 'run_finished')
            decision = (ledger.item(item) or {}).get('disposition') or {}
            asked = ledger._row(request(item), 'assignment')[1] if decision else None
            check('ac4/builder', 'the builder untracked file is on disk and the worktree deferred ' + repr(result),
                  contents(path / 'draft.txt') == 'draft builder' and state_of(item) == 'deferred'
                  and ledger.item(item)['deferral']['rule'] == 'unique_work')
            check('ac4/builder', 'it raises a request of its own, for that one worktree, in no group '
                  + repr(decision), bool(asked) and 'group' not in decision
                  and decision.get('alias', '').startswith('space-disposition-')
                  and decision['proposal']['worktrees'][0]['files'] == ['draft.txt']
                  and ledger.groups() == groups
                  and 'review_group' not in ledger.item(item)['deferral'])
            scratch, scratch_path, scratch_owner = tree('reviewer-scratch', ticket=False, station='review')
            finish(scratch, scratch_owner)
            check('ac4/builder', 'a review worktree with only an untracked file is in no group either',
                  not (ledger.item(scratch) or {}).get('disposition') and ledger.groups() == groups)

            # The widened terms (the lead's decision, specification History).
            def entry(n):
                name = 'space:item:terms-%d' % n
                return dict(item=name, path='/fixture/terms-%d' % n, branch=None, unheld_commits=True,
                            kept_branch='space-saved-terms-%d' % n, files=['a-%d.txt' % n], commits=[],
                            restore='veldo space restore ' + name)

            def offered(trees, group='space:group:fixture:2026-11-16:1'):
                proposal = {'discard': ST.SPACE_DISCARD, 'worktrees': trees}
                if group is not None:
                    proposal['group'] = group
                return proposal

            def record_terms(proposal, **target):
                target.setdefault('digest', ST.digest(proposal))
                return settlement.terms(signed(command('terms', terms='terms-' + next_id(),
                    touchpoint='space_disposition', target=target, proposal=proposal, required_roles=[], quorum=None)))

            pair = offered([entry(1), entry(2)])
            good = record_terms(pair, kind='space_group', ref=pair['group'],
                                members=[entry(1)['item'], entry(2)['item']])
            check('terms/group', 'terms for a group of two, targeting the group and both items, are recorded '
                  + repr(good), good.get('outcome') == 'recorded')
            shown = ST.space_presentation(pair)
            check('terms/group', 'each member is listed with its own path, files and restore command',
                  all(text in shown['brief'] for n in (1, 2) for text in (
                      'Worktree %d: "/fixture/terms-%d"' % (n, n), '"a-%d.txt"' % n,
                      'Restore: ' + entry(n)['restore']))
                  and shown['choices'] == ['accept save', 'accept keep', 'accept discard'])
            refusals = {
                'the target is one item': dict(kind='space_item', ref=entry(1)['item']),
                'the target names another group': dict(kind='space_group', ref=pair['group'] + '9',
                                                       members=[entry(1)['item'], entry(2)['item']]),
                'the target leaves a member out': dict(kind='space_group', ref=pair['group'],
                                                       members=[entry(1)['item']]),
                'the target names no member': dict(kind='space_group', ref=pair['group']),
            }
            for label, target in refusals.items():
                result = record_terms(pair, **target)
                check('terms/group', label + ' ' + repr(result), result.get('outcome') == 'refused')
            for label, proposal in (
                    ('two worktrees with no group', offered([entry(1), entry(2)], group=None)),
                    ('a group with no worktree', offered([])),
                    ('one worktree listed twice', offered([entry(1), entry(1)])),
                    ('a group that is not a review group record', offered([entry(1)], group='fixture'))):
                try:
                    ST.space_presentation(proposal)
                    refused = False
                except ST.Refused:
                    refused = True
                check('terms/group', label + ' is refused', refused)
            single = offered([entry(1)], group=None)
            check('terms/group', 'one worktree without a group is targeted as that item, as before',
                  record_terms(single, kind='space_item', ref=entry(1)['item']).get('outcome') == 'recorded'
                  and record_terms(single, kind='space_group', ref=pair['group'],
                                   members=[entry(1)['item']]).get('outcome') == 'refused'
                  and ST.space_presentation(single)['brief'].split('\n')[2] == 'Worktree: "/fixture/terms-1"')

            # The service's disposition task, unchanged, publishes a group and carries its pick.
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
            made = [review('worker-a'), review('worker-b')]
            for item, path, owner in made:
                finish(item, owner)
            ledger.disposition_publish = publish
            gid, group = group_of(made[0][0])
            try:
                result = service.space_consumer.run(service._space_dispositions)
                rid = request(made[0][0])
                opened = ledger._row(rid, 'assignment')[1] or {}
                check('worker/group', 'the task publishes the one group request, in the worker ' + repr(result),
                      result.get('ok') and result.get('worker') != os.getpid()
                      and all(json.dumps(str(path)) in opened.get('brief', '') for _, path, _ in made))
                settle(made[0][0], 'discard')
                result = service.space_consumer.run(service._space_dispositions)
                check('worker/group', 'and carries the settled Discard for every member ' + repr(result),
                      result.get('ok') and result.get('worker') != os.getpid()
                      and all(state_of(item) == 'removed' and not path.exists()
                              and contents(snapshot(item) / 'work' / 'base.txt')
                              == 'edited by ' + owner['run']['id'] + '\n' for item, path, owner in made)
                      and ledger.group(gid)['state'] == 'closed')
            finally:
                service.space_consumer.stop()
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            conn.close()

    for row, checks in sorted(rows.items()):
        bad = '; '.join(label for label, good in checks if not good)
        if bad:
            print('DETAIL space340/' + row + ': ' + bad)
        expect('space340/' + row, bool(checks) and all(good for _, good in checks))


_v340_suite()
