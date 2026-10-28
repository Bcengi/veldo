"""VELDO-0080 ordinary defects through the production signed services.

Only this ticket's checks run. Channels use loopback Bot API and real signatures.
The fixture has no tests of its own. Every refusal is asserted before its control.
"""


def _v80_suite():
    import copy
    import hashlib
    import json
    import os
    from pathlib import Path
    import runpy
    from types import SimpleNamespace

    production = {name: ROOT / '.veldo' / name for name in (
        'control_defect.py', 'control_backlog.py', 'control_grooming_request.py',
        'control_backlog_priority.py', 'dispatch.py')}
    overrides = json.loads(os.environ.get('VELDO_0080_MUTANTS', '{}'))
    for name, path in overrides.items():
        if name not in production:
            raise ValueError('unknown mutation target: ' + name)
        production[name] = Path(path)
    setup = runpy.run_path(str(ROOT / 'proof/VELDO-0080/fixture.py'))['fixture']
    observed = {}

    def require(value, description):
        if not value:
            raise AssertionError(description)

    def check(label, fn):
        try:
            fn()
        except Exception as error:
            print('VELDO-0080 detail: %s: %r' % (label, error))
            expect('VELDO-0080 ' + label, False)
        else:
            expect('VELDO-0080 ' + label, True)

    with setup(ROOT, production) as env:
        f = SimpleNamespace(**env)

        def objective(source, suffix, own=False):
            text = 'Fix this bug: checkout returns the wrong total. Severity: high. ' + suffix
            if source == 'telegram_message':
                chat = f.chats['olga']
                message = f.message(f.api, {'id': chat, 'is_bot': False, 'first_name': 'Olga'},
                                    {'id': chat, 'type': 'private'}, text)
                f.api.setdefault('updates', []).append({'update_id': 1000000 + message['message_id'], 'message': message})
                f.acquirer.acquire()
                results = f.intake.take_telegram()
                result = next((r for r in results if r.get('proposal_id')), {})
                source_ref = '%d:%d:%d' % (f.api['user']['id'], chat, message['message_id'])
            else:
                text = 'For proj-a: Fix this bug: checkout returns the wrong total. Severity: high. ' + suffix
                result, body = f.by_api('olga', text)
                source_ref = body['request_id']
            require(result.get('proposal_id'), 'intake: ' + str(result))
            if f.intake.proposal(result['proposal_id']).get('state') == 'AWAITING_ROUTE':
                result = f.intake.route(dict(schema='veldo.intake_route/v1', proposal_id=result['proposal_id'],
                    route='existing_project', project='proj-a', reason='The checkout report belongs to proj-a.'),
                    dispatch='fixture-pm-route', proposal_id=result['proposal_id'])
                require(result.get('ok'), 'plain prose route: ' + str(result))
            made = f.osend('olga' if own else 'pm', 'propose', proposal=result['proposal_id'],
                          outcome='Checkout returns the accepted total.', scope=['checkout', 'payments'],
                          authority={'acceptor': 'olga', 'assessor': 'asha'}, evidence_requirements=f.EVIDENCE)
            require(made.get('ok'), 'objective: ' + str(made))
            oid = made['objective_id']
            record = f.OB.read(f.conn, oid)
            if own:
                command = f.first_writer(f.IN.source_key(source, source_ref))
                accepted = f.osend('pm', 'accept_message', objective=oid, objective_version=record['version'],
                                   revision=record['revision'], bound_digest=record['bound_digest'], intake_command=command)
            else:
                rid, receipt = f.present_terms(f.next_id('objective'), f.OB.acceptance_target(record),
                                               f.OB.acceptance_brief(record))
                f.answer(receipt)
                accepted = f.osend('pm', 'accept', objective=oid, objective_version=record['version'], request=rid)
            require(accepted.get('ok'), 'objective acceptance: ' + str(accepted))
            return oid, text, source_ref

        def defect(oid, **report):
            made = f.osend('pm', 'propose_feature', objective=oid, objective_version=f.OB.read(f.conn, oid)['version'],
                          feature=f.next_id('bug'), title='Restore accepted checkout total', scope=['checkout'])
            took = f.bsend('pm', 'take', feature=made['feature_id'], work_class='POLICY_DEFECT',
                          defect=dict({'severity': 'high'}, **report))
            require(took.get('ok'), 'take: ' + str(took))
            iid = took['item_id']
            unit = f.unit_entry('VELDO-9792')
            sid = 'VELDO-%d' % (9800 + f.units_made[0])
            f.spec_file(sid, [])
            unit.update(unit=sid, specification=sid)
            require(f.bop('pm', 'prepare', iid, units=[unit]).get('ok'), 'prepare')
            require(f.bop('pm', 'request_grooming', iid).get('ok'), 'grooming request')
            return iid, unit['unit']

        def settle(iid, touchpoint, choice='accept'):
            result, _ = f.answer(f.shown(iid, touchpoint), choice)
            require(result.get('outcome') == 'settled', 'answer: ' + str(result))
            f.apply_rulings(iid)

        completed_input = []

        def admission():
            scaffold = f.load('v80_scaffold', ROOT / '.veldo/init_scaffold.py')
            for name in ('control_defect.py', 'control_backlog.py', 'control_grooming_request.py', 'init_scaffold.py'):
                rel = '.veldo/' + name
                require((ROOT / rel).read_bytes() == (ROOT / 'engine' / rel).read_bytes(), 'distribution copy: ' + name)
            rel = '.veldo/control_defect.py'
            require(rel in scaffold._FILES, 'defect module is installed')
            destination = f.base / 'laid' / rel
            scaffold._lay(ROOT / 'engine' / rel, destination, rel, [], [])
            require(destination.read_bytes() == (ROOT / rel).read_bytes(), 'installed bytes')
            for source in ('telegram_message', 'api_request'):
                oid, text, ref = objective(source, source)
                iid, uid = defect(oid)
                require(f.executable(uid) == ['missing_authority:admission'], 'label admitted without owner')
                require(f.gpropose('pm', iid).get('ok'), 'propose grooming')
                record = f.request_record(iid)
                require(record['content']['class'] == 'POLICY_DEFECT', 'class')
                held = f.item(iid)['provenance']['defect']
                require(held['severity'] == 'high' and held['source']['text'] == text
                        and held['source']['ref'] == ref and held['source']['kind'] == source
                        and held['source']['principal'] == 'olga', 'source and severity retained')
                require(record['content']['evidence']['defect'] == held, 'report in exact binding')
                require(record['content']['specifications'] == [{'id': uid, 'digest': f.file_digest(uid)}],
                        'shaped specification digest')
                require(not f.admit_message(iid).get('ok'), 'objective answered: no own-message shortcut')
                f.groom(iid)
                require(f.executable(uid) == ['missing_authority:admission'], 'presentation is not admission')
                brief = f.GR.brief(record, 'admission')
                require('high' in brief and ref in brief and 'POLICY_DEFECT' in brief, 'complete brief')
                # A revision of any defect field invalidates the accepted material.
                for field, value in [('severity', 'low'), ('reproduction', 'I reproduced it'),
                                     ('scope_changes', ['interface']), ('source', dict(held['source'], text='another bug'))]:
                    changed = copy.deepcopy(f.item(iid))
                    changed['provenance']['defect'][field] = value
                    require('stale_subject:evidence' in f.GR.live_problems(record['content'], changed,
                            f.OB.read(f.conn, oid), f.data_of('project:proj-a')), 'binding: ' + field)
                settle(iid, 'admission')
                require(f.item(iid)['state'] == 'ADMITTED' and f.executable(uid) == ['missing_authority:priority'],
                        'admission without priority cannot execute')
                settle(iid, 'priority')
                item = f.item(iid)
                require(item['state'] == 'PRIORITIZED' and f.executable(uid) == [], 'ordinary execution admitted')
                require(item['admission']['request_digest'] == record['digest']
                        and item['admission']['request_revision'] == record['revision']
                        and item['admission']['principals'] == ['olga'], 'exact owner decision')
                observed[source] = dict(item=item, request=record)
                completed_input.append((iid, uid))

        def automatic():
            oid, _, _ = objective('api_request', 'model assertion')
            iid, uid = defect(oid, reproduction='Agent says the failure was reproduced cleanly.')
            f.gpropose('pm', iid)
            f.groom(iid)
            require(f.executable(uid) == ['missing_authority:admission']
                    and not f.admit_message(iid).get('ok'), 'model assertion admitted automatically')
            require(not f.bop('pm', 'admit', iid, request='agent-reproduction').get('ok'), 'agent receipt is not authority')
            for cls in ('STANDING_MAINTENANCE', 'SECURITY_EMERGENCY'):
                made = f.osend('pm', 'propose_feature', objective=oid, objective_version=f.OB.read(f.conn, oid)['version'],
                              feature=f.next_id('policy'), title='Critical occurrence', scope=['checkout'])
                count = len(f.of_kind('execution_unit'))
                result = f.bsend('pm', 'take', feature=made['feature_id'], work_class=cls,
                                 defect={'severity': 'critical', 'reproduction': 'Agent assertion'})
                require(result.get('reason') == 'unsupported_work_class:' + cls and not result.get('ok')
                        and len(f.of_kind('execution_unit')) == count, cls + ' has no governing authority')
            # A fresh owner's message supplies real authority without reproduction.
            own, _, _ = objective('api_request', 'ordinary message', own=True)
            ordinary, unit = defect(own)
            f.gpropose('pm', ordinary)
            require(f.groom(ordinary).get('outcome') == 'admitted' and f.executable(unit) == [],
                    'ordinary admission must not require automatic reproduction')
            require(f.item(ordinary)['priority']['rank'] == 3, 'severity supplies no queue precedence')
            changes = ('contract', 'criterion', 'public_behavior', 'interface', 'data_model',
                       'dependency_policy', 'protected_scope', 'release_policy', 'compatibility')
            require(tuple(f.CB.DF.SCOPE_CHANGES) == changes, 'scope dimension completeness')
            for dimension in changes:
                own, _, _ = objective('api_request', dimension, own=True)
                changed, unit = defect(own, scope_changes=[dimension], severity='critical')
                before = copy.deepcopy(f.item(changed)['provenance']['defect'])
                f.gpropose('pm', changed)
                result = f.groom(changed)
                require(f.item(changed)['state'] == 'AWAITING_GROOMING' and f.executable(unit)
                        and not f.admit_message(changed).get('ok'), 'scope-changing restoration bypassed grooming')
                settle(changed, 'admission', 'return_for_elaboration')
                require(f.item(changed)['state'] == 'PREPARED', 'owner return')
                require(f.bop('pm', 'request_grooming', changed).get('ok'), 'return to grooming')
                require(f.item(changed)['state'] == 'AWAITING_GROOMING'
                        and f.item(changed)['provenance']['defect'] == before, 'return lost severity or source')
            observed['scope_changes'] = list(changes)

        check('defects/ordinary-admission', admission)
        check('defects/no-automatic-admission', automatic)
        # AC2 uses the same admitted records, not a fixture admission.
        def completion():
            require(completed_input, 'AC1 must provide admitted work')
            runpy.run_path(str(ROOT / 'proof/VELDO-0080/completion.py'))['check'](ROOT, f, completed_input[-1], observed)
        check('defects/ordinary-completion', completion)

    if os.environ.get('VELDO_0080_EVIDENCE'):
        Path(os.environ['VELDO_0080_EVIDENCE']).write_text(json.dumps(observed, indent=2, sort_keys=True) + '\n')


_v80_suite()
