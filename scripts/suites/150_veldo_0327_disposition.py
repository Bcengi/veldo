"""VELDO-0327: signed terms, real inbox/presenter/settlement and SQLite transactions.

Only Telegram's send is a fixture transport. Keys are generated in the fixture root;
API answers are signed by an enrolled edge. No engine, remover or host worktree is used.
"""


def _v327_suite():
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
        'authority_contract.py': ROOT / ".veldo" / "authority_contract.py",
        'control_assignment.py': ROOT / ".veldo" / "control_assignment.py",
        'control_channel_presentation.py': ROOT / ".veldo" / "control_channel_presentation.py",
    }
    rows = {}

    def check(row, label, good):
        rows.setdefault(row, []).append((label, bool(good)))

    def load(name):
        spec = importlib.util.spec_from_file_location('v327_' + name, mods / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0327-') as temporary:
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

        def proposal(detached=False):
            return {'discard': ST.SPACE_DISCARD, 'worktrees': [dict(
                item='space-item:fixture', path=str(base / 'worktree'), branch=None if detached else 'work',
                unheld_commits=detached, kept_branch='space-saved-fixture' if detached else None,
                files=['modified.py', 'staged.py', 'notes.txt', '.local-settings', 'line\nbreak'],
                restore="veldo space restore space-item:fixture")]}

        def terms(alias, offered, touchpoint='space_disposition'):
            target = dict(kind='space_item', ref='space-item:fixture', digest=ST.digest('fixture-item'))
            return settlement.terms(signed(command('terms', terms=alias, touchpoint=touchpoint,
                target=target, proposal=offered, required_roles=[], quorum=None)))

        def frame(alias, version=1):
            return presenter.frame(signed(command('frame', alias=alias, request_version=version,
                                                  risk_statement='Work is saved before removal.')))

        def open_request(alias, offered=None, touchpoint='space_disposition', owner='owner', changes=None):
            offered = proposal() if offered is None else offered
            recorded = terms(alias, offered, touchpoint)
            if recorded.get('outcome') != 'recorded':
                return None, recorded
            content = (ST.space_presentation(offered) if touchpoint == 'space_disposition' else
                       dict(kind=ST.JOURNEY[touchpoint]['assignment_kind'], brief='Existing request',
                            choices=['accept', 'reject', 'return_for_elaboration']))
            content.update(owner=owner, scope=['project'], deadline='2099-01-01T00:00:00Z',
                           budget={'owner_minutes': 1}, subject=recorded['subject'])
            content.update(changes or {})
            opened = inbox.apply(signed(command('open', alias=alias, assignment=content)))
            rid = I.assignment_id(ids['repository_uuid'], alias)
            if not opened.get('ok'):
                return rid, opened
            frame(alias)
            return rid, presenter.present(rid)

        def packet(receipt, choice, **changes):
            answer = dict(ids, schema=ST.API_SCHEMA, edge='api-edge', answer_id=next_id(),
                          principal=receipt['owner'], request_id=receipt['request_id'],
                          request_version=receipt['request_version'], presentation_id=receipt['presentation_id'],
                          presentation_digest=receipt['brief_digest'], presentation_version=receipt['presentation_version'],
                          choice=choice, rationale='Keep every piece of work recoverable.')
            answer.update(changes)
            return dict(answer=answer, signature=sign('api-edge', S.canonical_bytes(answer)))

        def entity(eid):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (eid,)).fetchone()
            return json.loads(row[0]) if row else None

        def snapshot():
            return S.materialized_state(conn), conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]

        def answer(rid, choice, **changes):
            receipt = presenter.current(rid)
            return settlement.api_answer(packet(receipt, choice, **changes)) if receipt else {'reason': 'no_presentation'}

        try:
            policy = ST.JOURNEY.get('space_disposition', {})
            check('ac1/policy', 'owner decision with one approving effect', policy == {
                'assignment_kind': 'decision', 'roles': ('project_owner',),
                'quorum': {'count': 1, 'min_independence': 1}, 'effects': {'approve': 'space_disposition_decided'}})
            for choice in ('accept save', 'accept keep', 'accept discard'):
                rid, result = open_request('pick-' + choice.split()[1], proposal(detached=True))
                receipt = presenter.current(rid) if rid else None
                check('ac1/presented', choice + ' published ' + repr(result), receipt is not None
                      and receipt['outcome'] == 'published'
                      and receipt['choices'] == ['accept save', 'accept keep', 'accept discard'])
                if receipt is None:
                    for row in ('ac2/shown', 'ac3/choice', 'ac3/atomic', 'ac3/once'):
                        check(row, choice + ' had no presentation', False)
                    continue
                shown = '\n'.join(receipt['rendered'])
                check('ac2/shown', 'files, saved first, branch and restore visible',
                      all(json.dumps(path) in shown for path in proposal()['worktrees'][0]['files'])
                      and 'space-saved-fixture' in shown and ST.SPACE_DISCARD in shown
                      and 'veldo space restore space-item:fixture' in shown)
                result = answer(rid, choice)
                effect = entity(ST.effect_id(rid, 1)) or {}
                check('ac3/choice', choice + ' remains the effect ' + repr(result), result.get('outcome') == 'settled'
                      and effect.get('choice') == choice and effect.get('ruling') == 'approve'
                      and effect.get('type') == 'space_disposition_decided' and effect.get('state') == 'obligated'
                      and effect.get('proposal') == proposal(detached=True))
                transitions = [json.loads(row[0]) for row in conn.execute(
                    'SELECT transition FROM journal WHERE command_id=?', (ST.settlement_id(rid, 1),))]
                check('ac3/atomic', choice + ' single journal transition', len(transitions) == 1
                      and set(transitions[0]) == {rid, ST.settlement_id(rid, 1), ST.effect_id(rid, 1), ST.receipt_id(rid, 1)}
                      and entity(rid)['state'] == 'SATISFIED')
                before = snapshot()
                retry = settlement.settle(rid)
                again = answer(rid, choice)
                check('ac3/once', 'repeat has no write', retry.get('reason') == 'already_settled'
                      and again.get('reason') == 'request_closed' and snapshot() == before)

            offered = proposal(detached=True)
            offered['worktrees'][0]['files'] = ['nested/%03d-%s.txt' % (n, 'detail' * 8) for n in range(100)]
            rid, result = open_request('long-list', offered)
            receipt = presenter.current(rid) if rid else None
            shown = '\n'.join(receipt['rendered']) if receipt else ''
            check('ac2/whole-list', 'every file survives a multipart presentation', receipt is not None
                  and len(receipt['rendered']) > 1 and all(json.dumps(path) in shown
                      for path in offered['worktrees'][0]['files']) and 'space-saved-fixture' in shown)

            offered = proposal()
            offered['worktrees'][0]['files'] = []
            before = snapshot()
            rid, result = open_request('empty-files', offered)
            receipt = presenter.current(rid) if rid else None
            check('ac2/empty-files', 'no presentation offers Discard with nothing listed ' + repr(result),
                  result.get('reason') == 'invalid_input' and receipt is None and snapshot() == before)

            for name, alter in (
                ('missing-files', lambda p: p['worktrees'][0].pop('files')),
                ('bad-files', lambda p: p['worktrees'][0].update(files=[None])),
                ('missing-kept-branch', lambda p: p['worktrees'][0].update(kept_branch=None)),
                ('missing-save', lambda p: p.update(discard='Discard removes the files.')),
                ('wrong-restore', lambda p: p['worktrees'][0].update(restore='veldo space restore another')),
                ('tier', lambda p: p.update(tier='safe')),
            ):
                offered = proposal(detached=True)
                alter(offered)
                before = snapshot()
                result = terms('invalid-' + name, offered)
                check('ac2/' + name, 'refused before any request ' + repr(result),
                      result.get('reason') == 'invalid_input' and snapshot() == before)

            for name, changes in (('hidden-list', {'brief': 'Discard removes nothing.'}),
                                  ('extra-choice', {'choices': ['accept save', 'accept keep', 'accept discard', 'reject']})):
                rid, result = open_request(name, changes=changes)
                check('ac2/request-binding', name + ' cannot open ' + repr(result),
                      not result.get('ok', True) and entity(rid) is None)
            rid, result = open_request('bad-revision')
            before = snapshot()
            revised = inbox.apply(signed(command('revise', alias='bad-revision', request_version=1,
                                                  changes={'brief': 'The file list is hidden.'})))
            check('ac2/request-binding', 'revision cannot hide the list', not revised['ok'] and snapshot() == before)

            # Fix round 1, F1: the guard is the request write's own, whatever was built last.
            def fix1(row, body):
                try:
                    body()
                except Exception:
                    check(row, traceback.format_exc(), False)

            def hidden_open(box, alias, **changes):
                offered = proposal()
                recorded = terms(alias, offered)
                content = ST.space_presentation(offered)
                content.update(owner='owner', scope=['project'], deadline='2099-01-01T00:00:00Z',
                               budget={'owner_minutes': 1}, subject=recorded['subject'])
                content.update(changes)
                return box.apply(signed(command('open', alias=alias, assignment=content)))

            def late_inbox():
                late = I.Inbox(S, CM, claims, contract, conn, ids, 'steward', journal_sign)
                for alias, changes in (('late-hidden', {'brief': 'Discard removes nothing.'}),
                                       ('late-choice', {'choices': list(ST.SPACE_CHOICES) + ['reject']})):
                    result = hidden_open(late, alias, **changes)
                    check('fix1/late-inbox', alias + ' refused ' + repr(result), not result.get('ok', True)
                          and entity(I.assignment_id(ids['repository_uuid'], alias)) is None)
                result = hidden_open(late, 'late-good')
                check('fix1/late-inbox', 'a matching request still opens ' + repr(result), result.get('ok') is True)
                revised = late.apply(signed(command('revise', alias='late-good', request_version=1,
                                                    changes={'brief': 'The file list is hidden.'})))
                check('fix1/late-inbox', 'revision cannot hide the list ' + repr(revised), not revised.get('ok', True)
                      and entity(I.assignment_id(ids['repository_uuid'], 'late-good'))['request_version'] == 1)

            def no_settlement():
                other = S.open_store(str(base / 'control.sqlite3'))
                try:
                    CM.attach(S)
                    lone = I.Inbox(S, CM, claims, contract, other, ids, 'steward', journal_sign)
                    check('fix1/no-settlement', 'this connection has no settlement command',
                          ST.TERMS not in other.command_registry and ST.SETTLE not in other.command_registry)
                    for alias, changes in (('lone-hidden', {'brief': 'Discard removes nothing.'}),
                                           ('lone-choice', {'choices': list(ST.SPACE_CHOICES) + ['reject']})):
                        result = hidden_open(lone, alias, **changes)
                        check('fix1/no-settlement', alias + ' refused ' + repr(result), not result.get('ok', True)
                              and entity(I.assignment_id(ids['repository_uuid'], alias)) is None)
                    result = hidden_open(lone, 'lone-good')
                    check('fix1/no-settlement', 'a matching request still opens ' + repr(result),
                          result.get('ok') is True)
                finally:
                    other.close()

            def unmatched_presentation():
                # A request an unguarded writer stored: the validator is absent for this one write.
                with patch.dict(I.SUBJECT_VALIDATORS, clear=True):
                    result = hidden_open(inbox, 'stored-hidden', brief='Discard removes nothing.')
                rid = I.assignment_id(ids['repository_uuid'], 'stored-hidden')
                check('fix1/presenter', 'the fixture stored the unmatched request ' + repr(result),
                      result.get('ok') is True and entity(rid) is not None)
                framed = frame('stored-hidden')
                check('fix1/presenter', 'not framed ' + repr(framed), framed.get('outcome') == 'refused'
                      and framed.get('reason') == 'presentation_mismatch'
                      and entity(V.framing_id(rid)) is None)
                with patch.dict(I.SUBJECT_VALIDATORS, clear=True):
                    framed = frame('stored-hidden')
                check('fix1/presenter', 'the fixture stored a framing ' + repr(framed),
                      framed.get('outcome') == 'accepted')
                sent = len(transport.sent)
                shown = presenter.present(rid)
                check('fix1/presenter', 'not presented ' + repr(shown), shown.get('outcome') == 'refused'
                      and shown.get('reason') == 'presentation_mismatch' and presenter.current(rid) is None
                      and len(transport.sent) == sent)

            fix1('fix1/late-inbox', late_inbox)
            fix1('fix1/no-settlement', no_settlement)
            fix1('fix1/presenter', unmatched_presentation)

            rid, result = open_request('unoffered')
            for choice in ('save', 'keep', 'discard', 'reject', 'accept unknown', 'accept keep w2'):
                before = snapshot()
                result = answer(rid, choice)
                check('ac3/unmatched', choice + ' refused ' + repr(result),
                      result.get('reason') == 'unmatched_choice' and snapshot() == before)
            rid, result = open_request('outsider', owner='outsider')
            result = answer(rid, 'accept keep')
            check('ac1/owner', 'person without owner role cannot settle', result.get('reason') == 'role_not_satisfied'
                  and entity(ST.effect_id(rid, 1)) is None and entity(rid)['state'] == 'OFFERED')

            rid, result = open_request('stale')
            receipt = presenter.current(rid)
            changed = proposal()
            changed['worktrees'][0]['files'].append('new.txt')
            recorded = terms('stale-new', changed)
            content = ST.space_presentation(changed)
            content.pop('kind')
            content['subject'] = recorded['subject']
            revised = inbox.apply(signed(command('revise', alias='stale', request_version=1, changes=content)))
            frame('stale', 2)
            presenter.present(rid)
            before = snapshot()
            result = settlement.api_answer(packet(receipt, 'accept discard')) if receipt else {}
            check('ac3/stale', 'old file list cannot authorize current request', revised['ok']
                  and result.get('reason') == 'stale_presentation' and snapshot() == before)
            for changes in ({'presentation_digest': 'sha256:wrong'}, {'presentation_version': 99},
                            {'principal': 'outsider'}, {'request_version': 1}):
                before = snapshot()
                result = answer(rid, 'accept discard', **changes)
                check('ac3/stale', repr(changes) + ' binds nothing', result.get('outcome') == 'refused'
                      and snapshot() == before)

            rid, result = open_request('rollback')
            with patch.object(settlement, 'settle', return_value={'outcome': 'queued'}):
                answer(rid, 'accept keep')
            before = snapshot()
            with patch.object(settlement, 'sign', side_effect=sqlite3.OperationalError('fixture write failure')):
                result = settlement.settle(rid)
            check('ac3/rollback', 'failed transaction writes no effect or terminal state',
                  result.get('reason') == 'unavailable_service' and snapshot() == before)
            result = settlement.settle(rid)
            check('ac3/rollback', 'recorded answer settles after recovery', result.get('outcome') == 'settled'
                  and (entity(ST.effect_id(rid, 1)) or {}).get('choice') == 'accept keep')

            existing = {
                'grooming': ('project_owner', 'decision', ('backlog_item_groomed', 'backlog_item_rejected', 'backlog_item_returned')),
                'admission': ('admission_authority', 'decision', ('work_admitted', 'admission_refused', 'admission_returned')),
                'priority': ('priority_authority', 'decision', ('priority_assigned', 'priority_refused', 'priority_returned')),
                'finding_disposition': ('technical_authority', 'review_disposition', ('finding_accepted', 'finding_rejected', 'finding_returned')),
                'decision_disposition': ('project_owner', 'decision', ('decision_approved', 'decision_rejected', 'decision_returned')),
            }
            rulings = ('approve', 'reject', 'return_for_elaboration')
            check('ac4/rulings', 'closed three ruling set', set(AC.RULINGS) == set(rulings) and len(AC.RULINGS) == 3)
            check('ac4/touchpoints', 'exactly one new touchpoint', set(ST.JOURNEY) == set(existing) | {'space_disposition'})
            for touchpoint, (role, kind, effects) in existing.items():
                check('ac4/touchpoints', touchpoint + ' policy unchanged', ST.JOURNEY[touchpoint] == dict(
                    assignment_kind=kind, roles=(role,), quorum={'count': 1, 'min_independence': 1},
                    effects=dict(zip(rulings, effects))))
                for choice, ruling, effect_type in zip(('accept', 'reject', 'return_for_elaboration'), rulings, effects):
                    rid, result = open_request(touchpoint + '-' + ruling, {}, touchpoint)
                    result = answer(rid, choice)
                    effect = entity(ST.effect_id(rid, 1)) or {}
                    check('ac4/existing-effects', touchpoint + '/' + ruling + ' ' + repr(result),
                          result.get('outcome') == 'settled' and effect.get('type') == effect_type
                          and effect.get('ruling') == ruling and effect.get('choice') == choice)
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            conn.close()

    for row, checks in sorted(rows.items()):
        bad = '; '.join(label for label, good in checks if not good)
        if bad:
            print('DETAIL space327/' + row + ': ' + bad)
        expect('space327/' + row, bool(checks) and all(good for _, good in checks))


_v327_suite()
