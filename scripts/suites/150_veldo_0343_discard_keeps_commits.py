"""VELDO-0343: Discard keeps every commit. Real Git worktrees, the real keep step, snapshot, Ledger,
signed disposition and removers, in a temporary folder.

Only Telegram's send is a fixture transport, and the process table and the pool's free space are
fixture inputs. No engine and no host worktree is used. The fixture is the one of VELDO-0318.
"""


def _v343_suite():
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
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        'control_space_reconcile.py': ROOT / ".veldo" / "control_space_reconcile.py",
    }
    rows = {}

    def check(row, label, good):
        rows.setdefault(row, []).append((label, bool(good)))

    def load(name):
        spec = importlib.util.spec_from_file_location('v343_' + name, mods / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0343-') as temporary:
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
        REC = load('control_space_reconcile')
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


        SPOOL = load('control_space_spool')
        trunk = git(repo, 'symbolic-ref', '--short', 'HEAD')
        seen = base / 'reference-transactions'
        seen.write_text('')
        hook = repo / '.git' / 'hooks' / 'reference-transaction'
        hook.parent.mkdir(exist_ok=True)
        hook.write_text('#!/bin/sh\n[ "$1" = committed ] || exit 0\ncat >> ' + str(seen) + '\nexit 0\n')
        hook.chmod(0o755)

        def detached(label, ticket=False, commit=True, dirty=True):
            # A worktree with no branch. With `commit`, a commit made on its detached HEAD: no ref holds it.
            path = trees / label
            git(repo, 'worktree', 'add', '-q', '--detach', str(path), head)
            owner = {'scope': scope}
            if ticket:
                owner['ticket'] = label
            else:
                owner['run'] = {'id': label, 'station': 'build'}
            if commit:
                (path / 'made.txt').write_text('committed in ' + label)
                git(path, 'add', 'made.txt')
                git(path, 'commit', '-q', '-m', 'made in ' + label)
            if dirty:
                (path / 'draft.txt').write_text('draft ' + label)
            made = ledger.declare('worktree', {'path': str(path)}, owner, 'record', branch=None, start=head)
            assert made['ok'], made
            assert ledger.confirm(made['item'])['ok']
            return made['item'], path, owner, git(path, 'rev-parse', 'HEAD')

        def shown(item):
            decision = ledger.item(item).get('disposition') or {}
            return ((decision.get('proposal') or {}).get('worktrees') or [{}])[0]

        def discard(item, owner, between=None):
            # The owner's settled and authorized Discard, carried. None when no request was raised.
            signal(item, owner, 'ticket_ended' if owner.get('ticket') else 'run_finished')
            if not shown(item):
                return None
            rid = settle(item, 'discard')
            assert ledger.authorize_disposition(item, rid)['ok']
            if between:
                between(shown(item))
            return act(item)

        def holders(path, commit):
            out = git(path, 'for-each-ref', '--format=%(refname)', '--contains', commit,
                      'refs/heads', 'refs/tags', 'refs/remotes')
            return [name for name in out.split('\n') if name]

        def branches(path):
            return git(path, 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/heads')

        def commits(path):
            # Every commit object in the repository's store, reachable or not.
            found = git(path, 'cat-file', '--batch-all-objects', '--batch-check=%(objecttype) %(objectname)')
            return sorted(line.split()[1] for line in found.split('\n') if line.startswith('commit '))

        def branch_items(name=None):
            return {identity: record for identity, record in ledger.items().items()
                    if record['kind'] == 'branch' and (name is None or record['locator']['ref'] == name)}

        def order(item, branch_item):
            # The journal's own order: the kept branch's record, then the worktree's outcome removed.
            at = {}
            for number, one in enumerate(ledger.observations):
                if one.get('outcome') != 'accepted' or one.get('item') != item:
                    continue
                if one['operation'] == SP.KEEP_BRANCH:
                    at.setdefault('branch', number)
                if one['operation'] == SP.OUTCOME and one.get('state') == 'removed':
                    at.setdefault('removed', number)
            return 'branch' in at and 'removed' in at and at['branch'] < at['removed'] and bool(branch_item)

        try:
            # AC1 and AC4: a commit made on a detached HEAD, and an uncommitted file beside it.
            for ticket in (True, False):
                label = 'unheld-' + ('ticket' if ticket else 'run')
                item, path, owner, tip = detached(label, ticket)
                unheld = holders(repo, tip) == []
                objects, events, entities = commits(repo), len(ledger.events()), conn.execute(
                    "SELECT COUNT(*) FROM entities WHERE kind=?", (SP.EVENT_KIND,)).fetchone()[0]
                mark = len(seen.read_text())
                result = discard(item, owner)
                record = ledger.item(item)
                name = shown(item).get('kept_branch')
                check('ac1/name', label + ' ' + repr(name), name == 'space-saved-' + label
                      and name == RM.disposition_branch(record))
                if result is None or not name:
                    for row in ('ac1/kept-branch', 'ac1/branch-item', 'ac1/snapshot', 'ac4/no-commit', 'ac4/no-event'):
                        check(row, label + ' no request was raised', False)
                    continue
                code = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', 'refs/heads/' + name],
                                      capture_output=True)
                at = code.stdout.decode().strip()
                check('ac1/kept-branch', label + ' ' + repr(result) + ' branch at ' + repr(at),
                      unheld and record['state'] == 'removed' and not path.exists() and at == tip
                      and holders(repo, tip) == ['refs/heads/' + name]
                      and '--force' in str(record.get('removal', {}).get('commands'))
                      and (record.get('removal') or {}).get('kept_branch') == name)
                check('ac1/kept-branch', label + ' the committed file is on the branch', at == tip
                      and git(repo, 'show', name + ':made.txt') == 'committed in ' + label)
                found = branch_items(name)
                kept = list(found.values())[0] if len(found) == 1 else {}
                check('ac1/branch-item', label + ' ' + repr(found), len(found) == 1 and kept.get('state') == 'kept'
                      and kept.get('locator') == {'repository': str(repo), 'ref': name}
                      and kept.get('start') == tip and (kept.get('kept_branch') or {}).get('commit') == tip
                      and (kept.get('kept_branch') or {}).get('worktree') == item
                      and (record.get('kept_branch') or {}).get('item') in found)
                check('ac1/branch-item', label + ' recorded before the discard outcome', order(item, found))
                saved = snapshot(item)
                check('ac1/snapshot', label + ' ' + repr(saved), not (path / 'draft.txt').exists()
                      and saved is not None and contents(saved / 'work' / 'draft.txt') == 'draft ' + label)
                on_branches = set(git(repo, 'rev-list', '--branches').split())
                check('ac4/no-commit', label + ' %d commits before, %d after' % (len(objects), len(commits(repo))),
                      tip in objects and objects == commits(repo) and tip in on_branches
                      and on_branches <= set(objects))
                lines = [line for line in seen.read_text()[mark:].split('\n') if line]
                made = [line for line in lines if line.endswith(' refs/heads/' + name)]
                sent = SPOOL.ref_changes(lines, str(repo / '.git'), 'fixture', trunk)
                check('ac4/no-event', label + ' hook lines ' + repr(lines) + ' sent ' + repr(sent),
                      len(made) == 1 and made[0].split()[1] == tip and sent == []
                      and events == len(ledger.events()) and entities == conn.execute(
                          "SELECT COUNT(*) FROM entities WHERE kind=?", (SP.EVENT_KIND,)).fetchone()[0])

            # AC1: only a commit no ref holds gets a branch. A detached worktree at a commit the trunk
            # holds, and a worktree on its own branch, are discarded and no branch is made.
            item, path, owner, tip = detached('held-by-trunk', commit=False)
            before, items = branches(repo), set(branch_items())
            result = discard(item, owner)
            check('ac1/only-unheld', 'detached at a held commit ' + repr(result),
                  result is not None and ledger.item(item)['state'] == 'removed' and not path.exists()
                  and branches(repo) == before and set(branch_items()) == items)
            item, path, owner = tree('on-a-branch')
            git(path, 'add', 'draft.txt')
            git(path, 'commit', '-q', '-m', 'on a branch')
            (path / 'more.txt').write_text('uncommitted on a branch')
            tip = git(path, 'rev-parse', 'HEAD')
            before, items = branches(repo), set(branch_items())
            result = discard(item, owner)
            check('ac1/only-unheld', 'on a branch ' + repr(result),
                  result is not None and ledger.item(item)['state'] == 'removed' and not path.exists()
                  and branches(repo) == before and set(branch_items()) == items
                  and git(repo, 'rev-parse', 'refs/heads/on-a-branch') == tip)

            # AC2: the kept branch cannot be created, and nothing is discarded.
            def stays(row, label, item, path, tip, result, name):
                record = ledger.item(item)
                check(row, label + ' ' + repr(result), result is not None and path.exists()
                      and contents(path / 'draft.txt') == 'draft ' + label
                      and contents(path / 'made.txt') == 'committed in ' + label
                      and git(path, 'rev-parse', 'HEAD') == tip
                      and git(path, 'status', '--porcelain') == '?? draft.txt')
                check(row, label + ' deferred as remove_refused ' + repr(record.get('deferral')),
                      record['state'] == 'deferred' and (record.get('deferral') or {}).get('rule') == 'remove_refused')
                check(row, label + ' no branch item, and no ref holds the commit', branch_items(name) == {}
                      and holders(repo, tip) == [])

            item, path, owner, tip = detached('name-taken')
            taken = {}
            result = discard(item, owner, lambda terms: (taken.update(name=terms['kept_branch']),
                                                         git(repo, 'branch', terms['kept_branch'], head)))
            stays('ac2/name-taken', 'name-taken', item, path, tip, result, taken.get('name'))
            check('ac2/name-taken', 'the branch that had the name is where it was',
                  bool(taken) and git(repo, 'rev-parse', 'refs/heads/' + taken['name']) == head)
            # The refusal spent the answer. The next request names the next free name, and its Discard runs.
            again = shown(item).get('kept_branch')
            check('ac2/next-name', repr(again), bool(taken) and again == taken['name'] + '-2')
            if taken and again == taken['name'] + '-2':
                result = discard(item, owner)
                check('ac2/next-name', 'discarded onto it ' + repr(result), ledger.item(item)['state'] == 'removed'
                      and not path.exists() and git(repo, 'rev-parse', 'refs/heads/' + again) == tip
                      and git(repo, 'rev-parse', 'refs/heads/' + taken['name']) == head
                      and len(branch_items(again)) == 1)

            item, path, owner, tip = detached('git-refuses')
            result = discard(item, owner, lambda terms: (taken.update(name=terms['kept_branch']),
                                                         git(repo, 'branch', terms['kept_branch'] + '/in-the-way', head)))
            stays('ac2/git-refuses', 'git-refuses', item, path, tip, result, taken.get('name'))
            check('ac2/git-refuses', 'git made no such branch', subprocess.run(
                ['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', 'refs/heads/' + taken['name']],
                capture_output=True).returncode == 1)

            # The Ledger did not record the branch: a branch nobody recorded is not a kept branch.
            item, path, owner, tip = detached('not-recorded')
            with patch.object(ledger, 'keep_branch', lambda *given, **named: {'ok': False, 'reason': 'fixture'}):
                result = discard(item, owner)
            record = ledger.item(item)
            check('ac2/not-recorded', repr(result), result is not None and path.exists()
                  and contents(path / 'draft.txt') == 'draft not-recorded' and git(path, 'rev-parse', 'HEAD') == tip
                  and record['state'] == 'deferred' and (record.get('deferral') or {}).get('rule') == 'remove_refused')

            # The Ledger reads what it records: a branch that is not there, a commit that is not the
            # worktree's, a worktree on a branch, and a worktree no Discard is authorized for.
            item, path, owner, tip = detached('ledger-reads')
            refused = [ledger.keep_branch(item, 'space-saved-ledger-reads', tip).get('reason')]
            signal(item, owner, 'run_finished')
            rid = settle(item, 'discard')
            assert ledger.authorize_disposition(item, rid)['ok']
            assert ledger.outcome(item, 'removing', {'event': 'run_finished', 'action': 'discard'})['ok']
            refused.append(ledger.keep_branch(item, 'space-saved-ledger-reads', tip).get('reason'))
            git(repo, 'branch', 'space-saved-ledger-reads', head)
            refused.append(ledger.keep_branch(item, 'space-saved-ledger-reads', tip).get('reason'))
            refused.append(ledger.keep_branch(item, 'space-saved-ledger-reads', head).get('reason'))
            refused.append(ledger.keep_branch(item, 'refs/heads/space-saved-ledger-reads', tip).get('reason'))
            # A worktree on a branch: the branch named is there at the worktree's commit, and the
            # Ledger still records nothing, because the worktree's own branch holds the commit.
            git(repo, 'branch', 'space-saved-ledger-reads-on', tip)
            git(path, 'switch', '-q', '-c', 'ledger-reads-own')
            refused.append(ledger.keep_branch(item, 'space-saved-ledger-reads-on', tip).get('reason'))
            check('ac2/ledger-reads', repr(refused), refused == [
                'space_keep_branch_state', 'space_keep_branch_ref', 'space_keep_branch_ref',
                'space_keep_branch_head', 'invalid_input:branch', 'space_keep_branch_attached']
                and branch_items('space-saved-ledger-reads') == {}
                and branch_items('space-saved-ledger-reads-on') == {})

            # The kept name appears between the remover's look and its write (the look is made to say
            # there is no such branch). The write is create-only, so git refuses it: the branch that
            # took the name is not moved, and nothing is discarded.
            item, path, owner, tip = detached('create-only')
            signal(item, owner, 'run_finished')
            name = shown(item).get('kept_branch')
            result = None
            if name:
                rid = settle(item, 'discard')
                assert ledger.authorize_disposition(item, rid)['ok']
                git(repo, 'branch', name, head)
                with patch.object(RM, '_branch_holds', lambda *given, **named: None):
                    result = act(item)
            stays('ac2/create-only', 'create-only', item, path, tip, result, name)
            check('ac2/create-only', 'the branch that took the name is where it was', bool(name)
                  and git(repo, 'rev-parse', 'refs/heads/' + str(name)) == head)

            # Only a branch holds a commit. A tag can be moved or deleted and a remote-tracking ref
            # goes with a prune, so a commit only one of them reaches gets a kept branch like any other,
            # and is still on that branch once the tag or the remote-tracking ref is gone.
            for label, ref in (('held-by-tag', 'refs/tags/held-by-tag'),
                               ('held-by-remote', 'refs/remotes/origin/held-by-remote')):
                item, path, owner, tip = detached(label)
                git(repo, 'update-ref', ref, tip)
                held = holders(repo, tip) == [ref]
                result = discard(item, owner)
                record, name = ledger.item(item), shown(item).get('kept_branch')
                at = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet',
                                     'refs/heads/' + str(name)], capture_output=True).stdout.decode().strip()
                found = branch_items(name)
                kept = list(found.values())[0] if len(found) == 1 else {}
                check('ac1/only-a-branch-holds', '%s %r, branch %r at %r, items %r' % (label, result, name, at, found),
                      result is not None and held and name == 'space-saved-' + label
                      and record['state'] == 'removed' and not path.exists() and at == tip
                      and sorted(holders(repo, tip)) == sorted(['refs/heads/' + name, ref])
                      and len(found) == 1 and kept.get('state') == 'kept' and kept.get('start') == tip
                      and (kept.get('kept_branch') or {}).get('worktree') == item
                      and (record.get('removal') or {}).get('kept_branch') == name and order(item, found))
                git(repo, 'update-ref', '-d', ref)
                check('ac1/only-a-branch-holds', label + ' the commit is on the branch after the ref is deleted',
                      bool(name) and holders(repo, tip) == ['refs/heads/' + str(name)])

            # A kept name whose branch item is on its way out (due, deferred or removing) is taken:
            # the Ledger records no kept branch onto such an item. The request names the next name
            # and its Discard runs, where every Discard under the first name would be refused.
            def leaving(name, at=None):
                # A branch item under the kept name, deferred. With `at`, its branch is there at that commit.
                if at:
                    git(repo, 'branch', name, at)
                made = ledger.declare('branch', {'repository': str(repo), 'ref': name}, {'scope': scope},
                                      'record', start=at or head)
                assert made['ok'], made
                assert ledger.confirm(made['item'])['ok']
                version = ledger._row(made['item'], SP.ITEM_KIND)[0]
                assert ledger.signal('ticket_ended', {'items': [{'item': made['item'], 'version': version}]})['ok']
                assert ledger.outcome(made['item'], 'deferred', {'rule': 'keep_failed', 'said': 'fixture'})['ok']
                return made['item']

            item, path, owner, tip = detached('leaving-item')
            other = leaving('space-saved-leaving-item')
            result = discard(item, owner)
            record, name = ledger.item(item), shown(item).get('kept_branch')
            check('ac2/name-of-a-leaving-item', 'no branch under the name: %r, named %r, %r'
                  % (result, name, record.get('deferral')),
                  result is not None and name == 'space-saved-leaving-item-2' and record['state'] == 'removed'
                  and not path.exists() and git(repo, 'rev-parse', 'refs/heads/' + str(name)) == tip
                  and len(branch_items(name)) == 1 and list(branch_items(name).values())[0]['state'] == 'kept'
                  and ledger.item(other)['state'] == 'deferred' and 'kept_branch' not in ledger.item(other)
                  and subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet',
                                      'refs/heads/space-saved-leaving-item'], capture_output=True).returncode == 1)
            # The same with the leaving item's branch at the worktree's own commit: that branch holds
            # the commit, so the Discard runs under the next name and writes nothing.
            item, path, owner, tip = detached('leaving-branch')
            other = leaving('space-saved-leaving-branch', tip)
            before = branches(repo)
            result = discard(item, owner)
            record, name = ledger.item(item), shown(item).get('kept_branch')
            check('ac2/name-of-a-leaving-item', 'a branch at the commit under the name: %r, named %r, %r'
                  % (result, name, record.get('deferral')),
                  result is not None and name == 'space-saved-leaving-branch-2' and record['state'] == 'removed'
                  and not path.exists() and branches(repo) == before
                  and holders(repo, tip) == ['refs/heads/space-saved-leaving-branch']
                  and (record.get('removal') or {}).get('commit_held_by') == ['refs/heads/space-saved-leaving-branch']
                  and ledger.item(other)['state'] == 'deferred' and 'kept_branch' not in ledger.item(other))

            # A Discard that stops between the branch write and its record (the process dies inside
            # keep_branch): the branch is there and no item records it. Reconcile defers the removing
            # worktree, and the next Discard records that same branch: one branch, one item, no -2.
            class Stopped(BaseException):
                pass

            def stop(*given, **named):
                raise Stopped()

            item, path, owner, tip = detached('stopped')
            stopped = False
            with patch.object(ledger, 'keep_branch', stop):
                try:
                    discard(item, owner)
                except Stopped:
                    stopped = True
            name, record = shown(item).get('kept_branch'), ledger.item(item)
            left = bool(name) and subprocess.run(
                ['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet', 'refs/heads/' + name],
                capture_output=True).stdout.decode().strip()
            check('ac1/stopped-before-record', 'stopped after the branch write: %r, branch at %r, items %r'
                  % (record['state'], left, branch_items(name)),
                  stopped and name == 'space-saved-stopped' and left == tip and branch_items(name) == {}
                  and record['state'] == 'removing' and path.exists()
                  and contents(path / 'draft.txt') == 'draft stopped' and git(path, 'rev-parse', 'HEAD') == tip)
            # What reconcile writes for a removing item it finds at its path, before the event is sent again.
            deferred = REC.Reconciler(dict(given, ledger=ledger)).defer(item, record, 'retry from rule 1')
            result = discard(item, owner) if deferred.get('ok') else None
            again, record = shown(item).get('kept_branch'), ledger.item(item)
            family = [line for line in branches(repo).split('\n') if line.startswith('refs/heads/space-saved-stopped')]
            found = branch_items(name)
            kept = list(found.values())[0] if len(found) == 1 else {}
            check('ac1/stopped-before-record', 'the next Discard names the same branch and removes: %r, named %r, '
                  'branches %r' % (result, again, family),
                  result is not None and again == name and record['state'] == 'removed' and not path.exists()
                  and family == ['refs/heads/%s %s' % (name, tip)] and holders(repo, tip) == ['refs/heads/' + name])
            check('ac1/stopped-before-record', 'one kept branch item records it, and no second name: ' + repr(found),
                  len(found) == 1 and kept.get('state') == 'kept' and kept.get('start') == tip
                  and (kept.get('kept_branch') or {}).get('commit') == tip
                  and (kept.get('kept_branch') or {}).get('worktree') == item
                  and (record.get('kept_branch') or {}).get('item') in found
                  and (record.get('removal') or {}).get('kept_branch') == name
                  and branch_items(str(name) + '-2') == {} and order(item, found))
            saved = snapshot(item)
            check('ac1/stopped-before-record', 'the uncommitted file is in the snapshot ' + repr(saved),
                  saved is not None and contents(saved / 'work' / 'draft.txt') == 'draft stopped')

            # The branch a stopped Discard left is recorded by reconcile, as it defers the removing
            # worktree, and not only by the next Discard. The owner then answers Keep: the worktree
            # stays, and the branch is a recorded kept branch all the same.
            item, path, owner, tip = detached('left')
            stopped = False
            with patch.object(ledger, 'keep_branch', stop):
                try:
                    discard(item, owner)
                except Stopped:
                    stopped = True
            name, record = shown(item).get('kept_branch'), ledger.item(item)
            unrecorded = branch_items(name) == {} and record['state'] == 'removing'
            deferred = REC.Reconciler(dict(given, ledger=ledger)).defer(item, record, 'retry from rule 1')
            found, record = branch_items(name), ledger.item(item)
            kept = list(found.values())[0] if len(found) == 1 else {}
            check('ac1/reconcile-records', 'reconcile deferred %r and recorded %r' % (deferred, found),
                  stopped and unrecorded and name == 'space-saved-left' and deferred.get('ok') is True
                  and record['state'] == 'deferred' and path.exists()
                  and len(found) == 1 and kept.get('state') == 'kept' and kept.get('start') == tip
                  and kept.get('locator') == {'repository': str(repo), 'ref': name}
                  and (kept.get('kept_branch') or {}).get('commit') == tip
                  and (kept.get('kept_branch') or {}).get('worktree') == item
                  and (record.get('kept_branch') or {}).get('item') in found
                  and git(repo, 'rev-parse', 'refs/heads/' + str(name)) == tip)
            signal(item, owner, 'run_finished')
            result = authorize(item, settle(item, 'keep')) if shown(item) else None
            record = ledger.item(item)
            check('ac1/reconcile-records', 'the owner answers Keep: %r, items %r' % (result, branch_items(name)),
                  result is not None and result.get('ok') is True and record['state'] == 'kept'
                  and record.get('owner_keep') == {'by': 'owner'} and path.exists()
                  and contents(path / 'draft.txt') == 'draft left' and git(path, 'rev-parse', 'HEAD') == tip
                  and branch_items(name) == found and git(repo, 'rev-parse', 'refs/heads/' + str(name)) == tip
                  and branch_items(str(name) + '-2') == {})

            # AC3: an agent's worktree, on its branch in the agent repository.
            agent = trees / 'agent'
            git(trees, 'clone', '-q', str(repo), str(agent))
            git(agent, 'config', 'user.name', 'Owner Fixture')
            git(agent, 'config', 'user.email', 'owner@example.invalid')
            agent_tree = trees / 'agent-tree'
            git(agent, 'worktree', 'add', '-q', '-b', 'private-work', str(agent_tree))
            (agent_tree / 'only.txt').write_text('only in agent')
            git(agent_tree, 'add', 'only.txt')
            git(agent_tree, 'commit', '-q', '-m', 'private work')
            (agent_tree / 'second.txt').write_text('a second commit')
            git(agent_tree, 'add', 'second.txt')
            git(agent_tree, 'commit', '-q', '-m', 'more private work')
            (agent_tree / 'draft.txt').write_text('draft agent')
            tip = git(agent_tree, 'rev-parse', 'HEAD')
            owner = {'scope': scope, 'ticket': 'agent-ticket'}
            parent = ledger.declare('agent_repository', {'path': str(agent)}, owner, 'record')['item']
            ledger.confirm(parent)
            item = ledger.declare('worktree', {'path': str(agent_tree)}, owner, 'record', parent=parent,
                                  branch='private-work', start=head)['item']
            ledger.confirm(item)
            before, items = branches(agent), set(branch_items())
            signal(item, owner, 'released')
            # The agent repository met the same event: rule 5 keeps it while its branch is not landed.
            was = ledger.item(parent)['state']
            result = None
            if shown(item):
                rid = settle(item, 'discard')
                assert ledger.authorize_disposition(item, rid)['ok']
                result = act(item)
            there = agent.exists() and (agent / '.git').is_dir()
            check('ac3/agent', repr(result) + ' agent repository ' + repr(ledger.item(parent)),
                  result is not None and ledger.item(item)['state'] == 'removed' and not agent_tree.exists()
                  and there and git(agent, 'rev-parse', 'refs/heads/private-work') == tip
                  and git(agent, 'rev-list', '--count', head + '..refs/heads/private-work') == '2'
                  and git(agent, 'show', 'private-work:only.txt') == 'only in agent')
            check('ac3/agent', 'the agent repository item is as it was, and no branch was made: was %r, is %r %r'
                  % (was, ledger.item(parent)['state'], ledger.item(parent).get('deferral')),
                  there and ledger.item(parent)['state'] == was and was in ('present', 'kept', 'deferred')
                  and branches(agent) == before and set(branch_items()) == items)
            saved = snapshot(item)
            check('ac3/agent', 'the uncommitted file is in the snapshot ' + repr(saved),
                  saved is not None and contents(saved / 'work' / 'draft.txt') == 'draft agent')

            # A detached worktree of the agent repository, with a commit no ref holds. Its kept branch
            # is written and recorded in the shared repository, where the commit's kept ref is: the
            # agent repository is private and goes later, so nothing is written there.
            def agent_detached(label):
                path = trees / label
                git(agent, 'worktree', 'add', '-q', '--detach', str(path))
                (path / 'made.txt').write_text('committed in ' + label)
                git(path, 'add', 'made.txt')
                git(path, 'commit', '-q', '-m', 'made in ' + label)
                (path / 'draft.txt').write_text('draft ' + label)
                owner = {'scope': scope, 'ticket': label}
                made = ledger.declare('worktree', {'path': str(path)}, owner, 'record', parent=parent,
                                      branch=None, start=head)
                assert made['ok'], made
                assert ledger.confirm(made['item'])['ok']
                return made['item'], path, owner, git(path, 'rev-parse', 'HEAD')

            def agent_discard(item, owner, between=None):
                signal(item, owner, 'released')
                if not shown(item):
                    return None
                rid = settle(item, 'discard')
                assert ledger.authorize_disposition(item, rid)['ok']
                if between:
                    between(shown(item))
                return act(item)

            def agent_rows():
                item, path, owner, tip = agent_detached('agent-detached')
                before, unheld = branches(agent), holders(agent, tip) == []
                result = agent_discard(item, owner)
                record, name = ledger.item(item), shown(item).get('kept_branch')
                at = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '--quiet',
                                     'refs/heads/' + str(name)], capture_output=True).stdout.decode().strip()
                check('ac3/detached', '%r %r, branch %r in the shared repository at %r' % (
                          result, record.get('deferral'), name, at),
                      result is not None and unheld and name == 'space-saved-agent-detached'
                      and record['state'] == 'removed' and not path.exists() and at == tip
                      and holders(repo, tip) == ['refs/heads/' + name]
                      and git(repo, 'show', name + ':made.txt') == 'committed in agent-detached')
                found = branch_items(name)
                kept = list(found.values())[0] if len(found) == 1 else {}
                check('ac3/detached', 'recorded there, as one kept branch item: ' + repr(found),
                      len(found) == 1 and kept.get('state') == 'kept'
                      and kept.get('locator') == {'repository': str(repo), 'ref': name}
                      and kept.get('start') == tip and (kept.get('kept_branch') or {}).get('worktree') == item
                      and order(item, found))
                check('ac3/detached', 'nothing was written in the agent repository: ' + repr(branches(agent)),
                      agent.exists() and branches(agent) == before and holders(agent, tip) == []
                      and not any(one['locator'].get('repository') == str(agent) and one.get('kept_branch')
                                  for one in branch_items().values()))
                saved = snapshot(item)
                check('ac3/detached', 'the uncommitted file is in the snapshot ' + repr(saved),
                      saved is not None and contents(saved / 'work' / 'draft.txt') == 'draft agent-detached')

                # The shared repository cannot take the branch: the name is taken there by other work.
                # The Discard does not run, and no branch is made in the agent repository instead.
                item, path, owner, tip = agent_detached('agent-taken')
                before, taken = branches(agent), {}
                result = agent_discard(item, owner, lambda terms: (taken.update(name=terms['kept_branch']),
                                                                   git(repo, 'branch', terms['kept_branch'], head)))
                stays('ac3/detached-refused', 'agent-taken', item, path, tip, result, taken.get('name'))
                check('ac3/detached-refused', 'the branch that had the name is where it was, and the agent repository '
                      'has no new branch', bool(taken) and git(repo, 'rev-parse', 'refs/heads/' + taken['name']) == head
                      and branches(agent) == before)
                check('ac3/detached-refused', 'the next request names the next free name: '
                      + repr(shown(item).get('kept_branch')),
                      bool(taken) and shown(item).get('kept_branch') == taken['name'] + '-2')

            # With no agent repository there is no worktree to make: both rows are red, never absent.
            if (agent / '.git').is_dir():
                agent_rows()
            else:
                for row in ('ac3/detached', 'ac3/detached-refused'):
                    check(row, 'the agent repository is gone', False)
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            conn.close()

    for row, checks in sorted(rows.items()):
        bad = '; '.join(label for label, good in checks if not good)
        if bad:
            print('DETAIL space343/' + row + ': ' + bad)
        expect('space343/' + row, bool(checks) and all(good for _, good in checks))


_v343_suite()
