"""VELDO-0318: real Git worktrees, keep snapshots, signed disposition and SQLite transactions.

Only Telegram's send is a fixture transport. Keys are generated in the fixture root;
API answers are signed by an enrolled edge. No engine, remover or host worktree is used.
"""


def _v318_suite():
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
        spec = importlib.util.spec_from_file_location('v318_' + name, mods / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0318-') as temporary:
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

        def tree(label, dirty=True, ticket=True, station='build'):
            path = trees / label
            git(repo, 'worktree', 'add', '-q', *(['-b', label] if ticket else ['--detach']), str(path), head)
            owner = {'scope': scope}
            if ticket:
                owner['ticket'] = label
            else:
                owner['run'] = {'id': label, 'station': station}
            if dirty:
                (path / 'draft.txt').write_text('draft ' + label)
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

        try:
            for event in ('ticket_ended', 'project_ended', 'worktree_abandoned', 'released', 'run_finished'):
                item, path, owner = tree('request-' + event, ticket=event != 'run_finished')
                if event == 'released':
                    git(path, 'add', 'draft.txt')
                    git(path, 'commit', '-q', '-m', 'unlanded')
                before = git(path, 'rev-parse', 'HEAD')
                result = signal(item, owner, event)
                check('ac1/events', event + ' request ' + repr(result), 'disposition' in ledger.item(item))
                if 'disposition' not in ledger.item(item):
                    continue
                rid = request(item)
                first = conn.execute("SELECT COUNT(*) FROM entities WHERE kind='assignment'").fetchone()[0]
                signal(item, owner, event)
                second = conn.execute("SELECT COUNT(*) FROM entities WHERE kind='assignment'").fetchone()[0]
                check('ac1/one-request', event, first == second and request(item) == rid)
                check('ac2/no-unsettled-commit', event, git(path, 'rev-parse', 'HEAD') == before and path.exists())
                check('ac1/files', event, ledger.item(item)['disposition']['proposal']['worktrees'][0]['files']
                      == RM.disposition_files(ledger, ledger.item(item), str(path)))

            # VELDO-0327 fix round 1, F2: a clean tree whose only unique work is unlanded commits.
            def committed(label, ticket=True):
                item, path, owner = tree(label, ticket=ticket)
                git(path, 'add', 'draft.txt')
                git(path, 'commit', '-q', '-m', 'unlanded ' + label)
                return item, path, owner, git(path, 'rev-parse', 'HEAD')

            def shown(item):
                decision = ledger.item(item).get('disposition') or {}
                return ((decision.get('proposal') or {}).get('worktrees') or [{}])[0]

            for ticket in (True, False):
                label = 'commits-request-' + str(ticket)
                item, path, owner, tip = committed(label, ticket)
                sent = len(transport.sent)
                result = signal(item, owner, 'ticket_ended' if ticket else 'run_finished')
                terms = shown(item)
                if terms:
                    presenter.present(request(item))
                held = label if ticket else RM.disposition_branch(ledger.item(item))
                brief = '\n'.join(transport.sent[sent:])
                check('commits/request', label + ' terms ' + repr(terms) + repr(result),
                      terms.get('files') == [] and terms.get('commits') == [tip]
                      and terms.get('branch') == (label if ticket else None)
                      and terms.get('kept_branch') == (None if ticket else held))
                check('commits/request', label + ' brief ' + repr(brief),
                      'Discard removes no uncommitted file; the commits stay on "' + held + '"' in brief
                      and '"' + tip + '"' in brief and 'Files Discard would remove' not in brief)
                check('commits/request', label + ' nothing moved', path.exists()
                      and git(path, 'rev-parse', 'HEAD') == tip)

            item, path, owner, tip = committed('commits-discard')
            signal(item, owner)
            if shown(item):
                rid = settle(item, 'discard')
                assert ledger.authorize_disposition(item, rid)['ok']
                result = act(item)
                record = ledger.item(item)
                check('commits/discard-keeps', repr(result), record['state'] == 'removed' and not path.exists()
                      and git(repo, 'rev-parse', 'commits-discard') == tip
                      and '--force' in str(record.get('removal', {}).get('commands')))
            else:
                check('commits/discard-keeps', 'no request was raised', False)

            for ticket in (True, False):
                item, path, owner, tip = committed('commits-save-' + str(ticket), ticket)
                signal(item, owner, 'ticket_ended' if ticket else 'run_finished')
                if not shown(item):
                    check('commits/save', 'no request was raised', False)
                    continue
                rid = settle(item, 'save')
                assert ledger.authorize_disposition(item, rid)['ok']
                result = act(item)
                record = ledger.item(item)
                check('commits/save', str(ticket) + repr(result), record['state'] == 'removed' and not path.exists()
                      and git(repo, 'rev-parse', RM.disposition_branch(record)) == tip
                      and '--force' not in str(record.get('removal', {}).get('commands')))

            for choice in ('save', 'discard'):
                item, path, owner, tip = committed('commits-late-' + choice)
                signal(item, owner)
                if not shown(item):
                    check('commits/late-commit', 'no request was raised', False)
                    continue
                rid = settle(item, choice)
                assert ledger.authorize_disposition(item, rid)['ok']
                (path / 'later.txt').write_text('committed after the request was shown')
                git(path, 'add', 'later.txt')
                git(path, 'commit', '-q', '-m', 'not shown')
                late = git(path, 'rev-parse', 'HEAD')
                result = act(item)
                check('commits/late-commit', choice + repr(result), path.exists()
                      and ledger.item(item)['state'] == 'deferred' and git(path, 'rev-parse', 'HEAD') == late
                      and git(repo, 'rev-parse', 'commits-late-' + choice) == late)
                check('commits/late-commit', choice + ' the next request names the new tip ' + repr(shown(item)),
                      shown(item).get('commits') == [late] and shown(item).get('files') == []
                      and request(item) != rid)

            agent = trees / 'agent'
            git(trees, 'clone', '-q', str(repo), str(agent))
            git(agent, 'config', 'user.name', 'Owner Fixture')
            git(agent, 'config', 'user.email', 'owner@example.invalid')
            agent_tree = trees / 'agent-tree'
            git(agent, 'worktree', 'add', '-q', '-b', 'private-work', str(agent_tree))
            (agent_tree / 'only.txt').write_text('only in agent')
            git(agent_tree, 'add', 'only.txt')
            git(agent_tree, 'commit', '-q', '-m', 'private work')
            tip = git(agent_tree, 'rev-parse', 'HEAD')
            owner = {'scope': scope, 'ticket': 'agent-ticket'}
            parent = ledger.declare('agent_repository', {'path': str(agent)}, owner, 'record')['item']
            ledger.confirm(parent)
            item = ledger.declare('worktree', {'path': str(agent_tree)}, owner, 'record', parent=parent,
                                  branch='private-work', start=head)['item']
            ledger.confirm(item)
            signal(item, owner, 'released')
            # Every row is observed under a defect too: a request that was not raised is a red row,
            # and the rows after it still run.
            if shown(item):
                rid = request(item)
                count = conn.execute("SELECT COUNT(*) FROM entities WHERE kind='assignment'").fetchone()[0]
                signal(item, owner, 'released')
                check('ac1/released-agent', repr(ledger.item(item)), request(item) == rid and agent_tree.exists()
                      and shown(item).get('commits') == [tip]
                      and git(agent_tree, 'rev-parse', 'HEAD') == tip and count == conn.execute(
                          "SELECT COUNT(*) FROM entities WHERE kind='assignment'").fetchone()[0])
            else:
                check('ac1/released-agent', 'no request was raised ' + repr(ledger.item(item)), False)

            item, path, owner = tree('save-committed')
            git(path, 'add', 'draft.txt')
            git(path, 'commit', '-q', '-m', 'already committed')
            before = git(path, 'rev-parse', 'HEAD')
            signal(item, owner)
            if shown(item):
                rid = settle(item, 'save')
                assert ledger.authorize_disposition(item, rid)['ok']
                result = act(item)
                check('ac2/no-empty-commit', repr(result), ledger.item(item)['state'] == 'removed'
                      and git(repo, 'rev-parse', RM.disposition_branch(ledger.item(item))) == before)
            else:
                check('ac2/no-empty-commit', 'no request was raised', False)

            # Installed owner identity wins over an agent's repository-local identity.
            conn.execute('CREATE TABLE git_identity_repositories(domain TEXT,repository TEXT,path TEXT,identity TEXT)')
            conn.execute('CREATE TABLE git_identities(domain TEXT,identity TEXT,data TEXT)')
            conn.execute('INSERT INTO git_identity_repositories VALUES(?,?,?,?)',
                         ('fixture', 'fixture', str(repo), 'owner-git'))
            conn.execute('INSERT INTO git_identities VALUES(?,?,?)', ('fixture', 'owner-git', json.dumps(
                dict(id='owner-git', author_name='Owner Fixture', author_email='owner@example.invalid'))))
            conn.commit()
            git(repo, 'config', 'user.name', 'Agent identity')
            git(repo, 'config', 'user.email', 'agent@example.invalid')
            for ticket in (True, False):
                item, path, owner = tree('save-' + str(ticket), ticket=ticket)
                (path / '.settings').write_text('private settings')
                signal(item, owner, 'ticket_ended' if ticket else 'run_finished')
                rid = settle(item, 'save')
                result = ledger.authorize_disposition(item, rid)
                assert result['ok'], result
                result = act(item)
                record = ledger.item(item)
                branch = RM.disposition_branch(record)
                check('ac2/save', repr(record), record['state'] == 'removed' and not path.exists())
                if record['state'] != 'removed':
                    continue
                check('ac2/identity', branch, git(repo, 'show', '-s', '--format=%an <%ae>', branch)
                      == 'Owner Fixture <owner@example.invalid>')
                check('ac2/ignored-outside-git', branch, '.settings' not in git(repo, 'ls-tree', '-r', branch)
                      and contents(snapshot(item) / 'work' / '.settings') == 'private settings')
                check('ac2/nonforce', branch, '--force' not in str(record.get('removal', {}).get('commands')))

            for choice in ('save', 'discard'):
                item, path, owner = tree(choice + '-unsettled')
                signal(item, owner)
                before = git(path, 'rev-parse', 'HEAD')
                result = ledger.authorize_disposition(item, request(item))
                raw = RM.remove(ledger, PR, item, ledger.item(item), action=choice, free=given['free'],
                                run=given['run'], proc=str(proc))
                check('safety/unsettled', choice, not result['ok'] and not raw['ok'] and path.exists()
                      and git(path, 'rev-parse', 'HEAD') == before)

            for barrier in ('protect', 'live', 'child'):
                item, path, owner = tree('barrier-' + barrier)
                signal(item, owner)
                rid = settle(item, 'discard')
                assert ledger.authorize_disposition(item, rid)['ok']
                if barrier == 'protect':
                    ledger.protect.append({'type': 'path', 'value': str(path), 'engines': []})
                    result = act(item)
                    ledger.protect.pop()
                elif barrier == 'live':
                    with patch.dict(SIG.RULES, process_use=lambda *args: {'in_use': True}):
                        result = act(item)
                else:
                    (path / 'nested').mkdir()
                    git(path / 'nested', 'init', '-q')
                    result = act(item)
                check('safety/rules', barrier + repr(result), path.exists()
                      and ledger.item(item)['state'] == 'deferred' and snapshot(item) is None)

            for choice in ('save', 'discard'):
                item, path, owner = tree(choice + '-late')
                signal(item, owner)
                rid = settle(item, choice)
                assert ledger.authorize_disposition(item, rid)['ok']
                original = RM._kept
                wrote = []
                def late(ctx, identity, record):
                    result = original(ctx, identity, record)
                    if not wrote:
                        wrote.append(True)
                        (path / '.late-settings').write_text('arrived after snapshot')
                    return result
                move = RM._worktree_move
                def before_move(ctx, repository, source, target):
                    if source == str(path) and not wrote:
                        wrote.append(True)
                        (path / '.late-settings').write_text('arrived after snapshot')
                    return move(ctx, repository, source, target)
                with patch.object(RM, '_worktree_move', before_move) if choice == 'save' else patch.object(RM, '_kept', late):
                    result = act(item)
                check('ac2/snapshot-comparison' if choice == 'save' else 'ac3/snapshot-comparison', repr(result),
                      path.exists() and contents(path / '.late-settings') == 'arrived after snapshot'
                      and ledger.item(item)['state'] == 'deferred')

            for choice in ('save', 'discard'):
                item, path, owner = tree(choice + '-path-race')
                signal(item, owner)
                rid = settle(item, choice)
                assert ledger.authorize_disposition(item, rid)['ok']
                original = RM._worktree_remove
                attempted, written = [], []
                def write_at_original(ctx, repository, where):
                    attempted.append(where)
                    try:
                        (path / '.late-settings').write_text('writer won')
                        written.append(True)
                    except FileNotFoundError:
                        written.append(False)
                    return original(ctx, repository, where)
                with patch.object(RM, '_worktree_remove', write_at_original):
                    result = act(item)
                check('ac2/marked-path' if choice == 'save' else 'ac3/marked-path', repr(result),
                      bool(attempted) and all(where != str(path) for where in attempted)
                      and written == [False] and ledger.item(item)['state'] == 'removed')

            for choice in ('save', 'discard'):
                for alteration in ('content', 'mode'):
                    item, path, owner = tree(choice + '-changed-' + alteration)
                    (path / '.settings').write_text('saved original')
                    signal(item, owner)
                    rid = settle(item, choice)
                    assert ledger.authorize_disposition(item, rid)['ok']
                    second = RM._second_probe
                    def change_marked(ctx, where):
                        target = Path(where) / '.settings'
                        if alteration == 'content':
                            target.write_text('new content')
                        else:
                            target.chmod(0o600)
                        return second(ctx, where)
                    with patch.object(RM, '_second_probe', change_marked):
                        result = act(item)
                    check('safety/marked-difference', choice + '/' + alteration + repr(result),
                          path.exists() and ledger.item(item)['state'] == 'deferred'
                          and contents(snapshot(item) / 'work' / '.settings') == 'saved original'
                          and (contents(path / '.settings') == 'new content' if alteration == 'content'
                               else (path / '.settings').stat().st_mode & 0o777 == 0o600))

            item, path, owner = tree('discard-list')
            signal(item, owner)
            rid = settle(item, 'discard')
            assert ledger.authorize_disposition(item, rid)['ok']
            (path / 'late.txt').write_text('not shown')
            result = act(item)
            check('ac3/list-comparison', repr(result), path.exists() and contents(path / 'late.txt') == 'not shown'
                  and ledger.item(item)['state'] == 'deferred')

            item, path, owner = tree('discard-keeps')
            git(path, 'add', 'draft.txt')
            git(path, 'commit', '-q', '-m', 'unique commit')
            tip = git(path, 'rev-parse', 'HEAD')
            (path / 'draft.txt').write_text('edited after commit')
            signal(item, owner)
            rid = settle(item, 'discard')
            assert ledger.authorize_disposition(item, rid)['ok']
            result = act(item)
            check('ac3/keeps-commits', repr(result), ledger.item(item)['state'] == 'removed' and not path.exists()
                  and git(repo, 'rev-parse', 'discard-keeps') == tip
                  and contents(snapshot(item) / 'work' / 'draft.txt') == 'edited after commit')

            for failure in ('write', 'sync', 'readback', 'rename'):
                item, path, owner = tree('discard-failure-' + failure)
                signal(item, owner)
                rid = settle(item, 'discard')
                assert ledger.authorize_disposition(item, rid)['ok']
                real = RM._sibling
                def organ(name):
                    return KP if name == 'control_space_keep' else real(name)
                seam = {'write': '_put', 'sync': '_sync_folder', 'readback': '_stored', 'rename': '_rename'}[failure]
                with patch.object(RM, '_sibling', organ), patch.object(KP, seam, side_effect=OSError(failure)):
                    result = act(item)
                check('ac3/snapshot-failures', failure + repr(result), path.exists()
                      and contents(path / 'draft.txt') == 'draft discard-failure-' + failure
                      and ledger.item(item)['state'] == 'deferred')

            item, path, owner = tree('discard-retry')
            signal(item, owner)
            rid = settle(item, 'discard')
            assert ledger.authorize_disposition(item, rid)['ok']
            original = RM._second_probe
            with patch.object(RM, '_second_probe', return_value={'held': True}):
                act(item)
            first = snapshot(item)
            before = (first / 'manifest.json').read_bytes()
            (path / 'draft.txt').write_text('second attempt')
            signal(item, owner)
            rid = settle(item, 'discard')
            assert ledger.authorize_disposition(item, rid)['ok']
            result = act(item)
            check('ac3/append-attempt', repr(result), snapshot(item) != first and first.exists()
                  and (first / 'manifest.json').read_bytes() == before
                  and contents(snapshot(item) / 'work' / 'draft.txt') == 'second attempt')

            SV, CON = load('control_service'), load('control_space_consumer')
            service = object.__new__(SV.Service)
            service._space = dict(given, ledger=ledger)
            service.conn, service.domain, service.store = conn, ids['domain_uuid'], ids['store_uuid']
            service.principal, service.sign, service.generation = 'steward', journal_sign, 1
            service.config = {'journal_key': str(keys['steward'])}
            service.channel = types.SimpleNamespace(record=lambda: {'owner': 'owner'},
                ingress=types.SimpleNamespace(activations=types.SimpleNamespace(ids=ids)))
            service.space_consumer = CON.Consumer(ledger, given)
            item, path, owner = tree('worker-request')
            publish = ledger.disposition_publish
            ledger.disposition_publish = None
            signal(item, owner)
            ledger.disposition_publish = publish
            try:
                result = service.space_consumer.run(service._space_dispositions)
                check('worker/reconnect-request', repr(result), result.get('ok')
                      and result.get('worker') != os.getpid()
                      and ledger._row(request(item), 'assignment')[1] is not None)
                rid = settle(item, 'discard')
                result = service.space_consumer.run(service._space_dispositions)
                check('worker/settled-effect', repr(result), result.get('ok') and result.get('worker') != os.getpid()
                      and ledger.item(item)['state'] == 'removed' and not path.exists())
            finally:
                service.space_consumer.stop()
            # A journal notification during the active task must cause one more task,
            # even when the first child failed. No timer, no inline filesystem work.
            tasks, submissions = {}, []
            def submit(key, task, complete):
                submissions.append(task)
                tasks[key] = {'task': task, 'complete': complete}
                return tasks[key]
            service.space_consumer = types.SimpleNamespace(tasks=tasks, submit=submit)
            first = service.space_dispositions()
            second = service.space_dispositions()
            check('worker/no-inline', 'queued callable', first is second and len(submissions) == 1
                  and callable(submissions[0]))
            ticket = tasks.pop(('dispositions',))
            ticket['complete']({'ok': False})
            check('worker/no-lost-wakeup', 'one followup after a failed active task', len(submissions) == 2)

            for who, signer in (('outsider', 'outsider'), ('steward', 'steward'), ('owner', 'outsider')):
                item, path, owner = tree('signature-' + who)
                signal(item, owner)
                rid = settle(item, 'keep')
                before = ledger.item(item)
                result = authorize(item, rid, who, signer=signer)
                check('ac4/signature', who + repr(result), not result['ok'] and ledger.item(item) == before)
            item, path, owner = tree('transaction-owner')
            signal(item, owner)
            rid = settle(item, 'keep')
            member_before = conn.execute("SELECT data FROM entities WHERE id='owner'").fetchone()[0]
            send = ledger._send
            def revoke_before_transition(*args, **kwargs):
                data = json.loads(member_before)
                data['roles'] = []
                conn.execute("UPDATE entities SET data=? WHERE id='owner'", (json.dumps(data),))
                conn.commit()
                return send(*args, **kwargs)
            try:
                with patch.object(ledger, '_send', revoke_before_transition):
                    result = authorize(item, rid)
                check('ac4/transaction-owner', repr(result), not result['ok']
                      and not ledger.item(item).get('owner_keep') and ledger.item(item)['state'] == 'deferred')
            finally:
                conn.execute("UPDATE entities SET data=? WHERE id='owner'", (member_before,))
                conn.commit()

            item, path, owner = tree('keep')
            signal(item, owner)
            rid = settle(item, 'keep')
            result = authorize(item, rid, by='outsider')
            check('ac4/by', repr(result), not result['ok'])
            begin = conn.execute('SELECT COALESCE(MAX(seq),0) FROM journal').fetchone()[0]
            result = authorize(item, rid)
            record = ledger.item(item)
            check('ac4/state', repr(result), record['state'] == 'kept')
            check('ac4/mark', repr(result), record.get('owner_keep') == {'by': 'owner'})
            transitions = [json.loads(raw)[item]['data'] for (raw,) in conn.execute(
                'SELECT transition FROM journal WHERE seq>?', (begin,)) if item in json.loads(raw)]
            check('ac4/atomic', repr(transitions), len(transitions) == 1 and all(
                row['state'] == 'kept' and row.get('owner_keep') == {'by': 'owner'} for row in transitions))
            # Make the retained worktree clean. Without the mark a later event can remove it.
            git(path, 'add', 'draft.txt')
            git(path, 'commit', '-q', '-m', 'owner saved elsewhere')
            git(repo, 'branch', 'holds-keep', git(path, 'rev-parse', 'HEAD'))
            before = conn.execute("SELECT COUNT(*) FROM entities WHERE kind='assignment'").fetchone()[0]
            for event in ('ticket_ended', 'project_ended', 'run_finished', 'released'):
                signal(item, owner, event)
            after = conn.execute("SELECT COUNT(*) FROM entities WHERE kind='assignment'").fetchone()[0]
            check('ac4/no-retry', repr(ledger.item(item)), path.exists() and ledger.item(item)['state'] == 'kept'
                  and before == after)
            check('ac4/unsigned-outcome', 'old Keep path refused', not ledger.outcome(
                item, 'kept', {'owner_keep': {'at': time.time()}}, principal='owner')['ok'])
            if path.exists():
                (path / 'another-draft.txt').write_text('new work after Keep')
                version = ledger._row(item, SP.ITEM_KIND)[0]
                result = SIG.signal(ledger, 'worktree_abandoned', {'items': [{'item': item, 'version': version}],
                    'owner_abandon': {'item': item, 'at': time.time()}}, principal='owner', **given)
                check('ac4/abandon', repr(result), path.exists() and ledger.item(item)['state'] == 'deferred'
                      and not ledger.item(item).get('owner_keep') and request(item) != rid)
            else:
                check('ac4/abandon', 'Keep lost its worktree', False)
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            conn.close()

    for row, checks in sorted(rows.items()):
        bad = '; '.join(label for label, good in checks if not good)
        if bad:
            print('DETAIL space318/' + row + ': ' + bad)
        expect('space318/' + row, bool(checks) and all(good for _, good in checks))


_v318_suite()
