"""VELDO-0247, the Line part: a unit's process may use Check and Join steps, and the Line (control_service.py)
dispatches the parallel branches of a fan-out without waiting for one another, with the same bound (at most 8
wide, every branch's nodes counted in the step budget), the same join rule (the join passes on only when every
branch has arrived) and the same approval rule (checked at save on every path) as the workflow cycles.

Only shared ROOT, expect and fast_temp are consumed. One temporary tree holds an installed .veldo copy; the
production anchors below are the registered mutation driver's seam, so a mutation of any of them reaches every
reader. The store is the real SQLite authority with OpenSSH journal signatures; unit workflow revisions are saved
through VELDO-0132's Workflows service and read back through control_workflow_unit.bound_revision. The Line is
driven as in suite 127: its station methods (offer, limited, re-land, grant) are recorded instead of dispatched, and
its dispatch records are fixture records read through the Line's own `latest`.
"""


def _v247_line_suite():
    import contextlib
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_workflow.py': ROOT / ".veldo" / "control_workflow.py",
        'control_workflow_unit.py': ROOT / ".veldo" / "control_workflow_unit.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    observed = {}
    emitted, raised, regions = set(), [], []

    def check(label, condition):
        """A row. `condition` may be a predicate: an exception while judging is a failed condition, recorded."""
        emitted.add(label)
        if callable(condition):
            try:
                condition = condition()
            except Exception as error:  # noqa: BLE001
                observed.setdefault('condition_errors', []).append((label, repr(error)))
                condition = False
        expect('VELDO-0247 ' + label, bool(condition))

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            for label in labels:
                if label not in emitted:
                    check(label, False)

    def attempt(call, *args, **kwargs):
        try:
            return {'ok': call(*args, **kwargs)}
        except Exception as error:  # noqa: BLE001
            return {'refused': getattr(error, 'code', type(error).__name__),
                    'codes': list(getattr(error, 'codes', None) or [getattr(error, 'code', '')])}

    fast = fast_temp()
    with tempfile.TemporaryDirectory(prefix='v247l-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        (mods / 'workflows').mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v247l_store', mods / 'control_store.py')
        SIG = load('v247l_signer', mods / 'control_signer.py')
        WF = load('v247l_workflow', mods / 'control_workflow.py')
        WU = load('v247l_workflow_unit', mods / 'control_workflow_unit.py')
        CS = load('v247l_service', mods / 'control_service.py')
        DOMAIN, REPO = 'domain-247l', 'repository-247l'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'journal', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def journal_sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        serial = [0]

        def entity(identity):
            row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def journal_seq():
            return writer.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            command_id = 'setup-%d' % serial[0]
            S.execute(writer, dict(command_id=command_id, principal='setup', operation='upsert_entity', nonce=command_id,
                                   artifact_digests=[], expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'setup', journal_sign, 1)

        put('owner', 'membership', dict(principal_type='person', roles=['project_owner'], scope='*', revoked_at=None,
                                        expires_at=None))
        workflows = WF.Workflows(S, writer, domain=DOMAIN, repository=REPO, signer='setup', sign=journal_sign)

        def unit(name, **extra):
            put(name, 'execution_unit', dict(dict(state='READY', repository_uuid=REPO, project='alpha', revision=1,
                                                  depends_on=[], scope_digest='sha256:scope-' + name), **extra))

        def graph(workflow_id, kinds, edges, configs=None, fields=None, steps=64):
            """A unit definition from {node: kind} and [(id, from, port, to)]; land's ports all end."""
            body = {'schema': WF.SCHEMA, 'id': workflow_id, 'entry': 'build', 'terminal': ['done'],
                    'nodes': {name: {'kind': kind, 'config': json.loads(json.dumps((configs or {}).get(name, {})))}
                              for name, kind in kinds.items()},
                    'transitions': [{'id': i, 'from': f, 'port': p, 'to': t} for i, f, p, t in edges],
                    'references': {}, 'budget': {'steps': steps}}
            if 'land' in kinds:
                body['transitions'] += [{'id': 'land-' + port, 'from': 'land', 'port': port, 'to': 'done'}
                                        for port in WF.LAND_PORTS]
            if fields is not None:
                body['fields'] = fields
            return body

        TAIL = [('gated', 'gate', 'passed', 'approval'), ('approved', 'approval', 'granted', 'land'),
                ('stopped', 'approval', 'stopped', 'done')]
        APPROVES = {'approval': {'approves': 'land'}}
        FIELDS = {'files': {'type': 'number', 'source': {'subject': 'files'}}}
        ROUTE = {'branches': [{'name': 'big', 'conditions': [{'field': 'files', 'comparison': 'more than',
                                                             'value': 20}]}], 'otherwise': True}

        # A check after review: more than 20 files goes to a second reviewer, otherwise on to the gate.
        checked = graph('checked', {'build': 'build', 'review': 'review', 'route': 'check', 'second': 'review',
                                    'gate': 'gate', 'approval': 'owner_approval', 'land': 'land', 'done': 'end'},
                        [('built', 'build', 'done', 'review'), ('reviewed', 'review', 'done', 'route'),
                         ('to-second', 'route', 'big', 'second'), ('to-gate', 'route', 'otherwise', 'gate'),
                         ('seconded', 'second', 'done', 'gate')] + TAIL,
                        configs=dict(APPROVES, route=ROUTE), fields=FIELDS)
        # A fan-out after the build: a design review and a docs build run at the same time and meet at a join.
        PARALLEL_KINDS = {'build': 'build', 'design': 'review', 'docs': 'build', 'meet': 'join', 'final': 'review',
                          'gate': 'gate', 'approval': 'owner_approval', 'land': 'land', 'done': 'end'}
        PARALLEL_EDGES = [('to-design', 'build', 'done', 'design'), ('to-docs', 'build', 'done', 'docs'),
                          ('designed', 'design', 'done', 'meet'), ('documented', 'docs', 'done', 'meet'),
                          ('met', 'meet', 'done', 'final'), ('finalled', 'final', 'done', 'gate')] + TAIL
        MEET = {'meet': {'inputs': ['to-design', 'to-docs']}}

        def parallel(workflow_id='parallel', steps=64):
            return graph(workflow_id, PARALLEL_KINDS, PARALLEL_EDGES, configs=dict(APPROVES, **MEET), steps=steps)

        # The Line, driven with its station methods recorded instead of dispatched.
        ROLE = {'adapter': 'engine-a', 'configuration': {'model': 'fixture'}, 'seconds': 600}
        ROLES = {'builder': dict(ROLE, identity='builder-a', payload={'task': 'build the unit'}),
                 'reviewers': [dict(ROLE, identity='builder-a', payload={'task': 'review the unit'}),
                               dict(ROLE, identity='reviewer-b', payload={'task': 'review the unit'})]}

        class Service:
            conn, domain, principal = writer, DOMAIN, 'authority'

        class Gate:
            def unit_record(self, name):
                row = entity(name)
                return row['data'] if row and row['kind'] == 'execution_unit' else None

        class Station:
            land_config = {'trunk': 'main'}

            def latest(self, name):
                return None

            def records(self, name):
                return []

        def report():
            return {key: [] for key in ('refused', 'offered', 'waiting', 'asked', 'awaiting', 'stopped', 'decisions',
                                        'lands', 'ended', 'released')}

        def make_line(found, definition, records):
            line = object.__new__(CS.Line)
            line.service, line.repository, line.gate = Service(), REPO, Gate()
            line.roles = ROLES
            line.station = Station()
            line.calls = []
            line._rows = lambda kind: list(records) if kind == CS.L.D.RECORD_KIND else []
            line.process = lambda name, latest, rep: (found, definition)

            def offer(rep, name, station, role, **fields):
                line.calls.append({'unit': name, 'station': station, 'identity': role['identity'],
                                   'workflow': fields.get('workflow'), 'revision': fields.get('revision'),
                                   'follows': fields.get('follows')})
                return 'offered:' + station

            def limited(record, rep):
                line.calls.append({'limited': record['dispatch_id']})
                return None
            line.offer, line.limited = offer, limited
            line.reland = lambda *a, **k: line.calls.append({'reland': True})
            line.grant = lambda *a, **k: line.calls.append({'grant': True})
            return line

        def record(name, did, station, found, node, state='exited', rc=0, follows=None, branch=None, route=None,
                   attempt_number=1):
            workflow = dict(found, node=node)
            if branch is not None:
                workflow['branch'] = branch
            if route is not None:
                workflow['route'] = route
            return {'dispatch_id': did, 'state': state, 'artifact': None,
                    'termination': {'returncode': rc, 'signal': None, 'deadline_stop': False},
                    'contract': {'domain': DOMAIN, 'repository': REPO, 'unit': name, 'station': station,
                                 'attempt': attempt_number, 'source': {'commit': 'commit-' + did},
                                 'input': {'context': {'holder': 'builder-a'},
                                           'payload': {'follows': follows, 'workflow': workflow}}}}

        def drive(name, found, definition, records):
            line = make_line(found, definition, records)
            rep = report()
            value = line.next(name, line.latest(), rep)
            return {'value': value, 'calls': line.calls, 'report': rep, 'line': line}

        def offers(run):
            return [(c['station'], (c.get('workflow') or {}).get('node')) for c in run['calls'] if 'station' in c]

        try:
            # A unit's process may hold checks, a fan-out and its join: it saves and is accepted as a unit workflow.
            with region('line/unit-accepts-check-join'):
                saved = {name: attempt(workflows.save, {'definition': body}, principal='owner', base=0)
                         for name, body in (('checked', checked), ('parallel', parallel()))}
                bound = {name: attempt(WU.bound_revision, S, writer, DOMAIN, REPO, name, 1)
                         for name in ('checked', 'parallel')}
                observed['accepted'] = {'saved': saved, 'bound': bound,
                                        'problems': {'checked': WU.unit_problems(checked),
                                                     'parallel': WU.unit_problems(parallel())}}
                check('line/unit-accepts-check-join', lambda: all('ok' in v for v in saved.values())
                      and all('ok' in v for v in bound.values())
                      and bound['parallel']['ok'][0]['digest'] == WF.definition_digest(parallel())
                      and WU.unit_problems(checked) == [] and WU.unit_problems(parallel()) == [])
            PIN_CHECKED = WU.pin(checked, 1)
            PIN_PARALLEL = WU.pin(parallel(), 1)

            # A check in a unit's process: exactly one branch, the decision recorded with its rule and observed values.
            with region('line/check-one-branch', 'line/check-field-unsupplied', 'line/check-recorded-mismatch'):
                runs = {}
                for key, extra in (('big', {'files': 30}), ('small', {'files': 5}), ('missing', {}),
                                   ('wrong', {'files': 'many'})):
                    name = 'unit-check-' + key
                    unit(name, **extra)
                    records = [record(name, name + '-b1', 'build', PIN_CHECKED, 'build'),
                               record(name, name + '-r1', 'review', PIN_CHECKED, 'review', follows=name + '-b1')]
                    runs[key] = drive(name, PIN_CHECKED, checked, records)
                big, small = runs['big'], runs['small']
                decision = ((big['calls'] or [{}])[0].get('workflow') or {}).get('route') or [{}]
                observed['check'] = {k: {'calls': v['calls'], 'report': v['report']} for k, v in runs.items()}
                check('line/check-one-branch', lambda: offers(big) == [('review', 'second')]
                      and decision[0]['node'] == 'route' and decision[0]['branch'] == 'big'
                      and decision[0]['rule'] == 'big'
                      and decision[0]['conditions'] == [{'rule': 'big', 'field': 'files', 'comparison': 'more than',
                                                         'value': 20, 'observed': 30, 'holds': True}]
                      and [(c['node'], c['decision']['branch']) for c in big['report'].get('checks', [])]
                      == [('route', 'big')]
                      and big['calls'][0]['revision'] == 'commit-unit-check-big-b1'
                      and offers(small) == []
                      and [(c['node'], c['decision']['branch'], c['decision']['rule'])
                           for c in small['report'].get('checks', [])] == [('route', 'otherwise', 'otherwise')]
                      and small['report']['refused'] == [])
                check('line/check-field-unsupplied', lambda: all(
                    offers(runs[k]) == [] and not runs[k]['report'].get('checks')
                    and [r['refusals'] for r in runs[k]['report']['refused']]
                    == [['invalid_input:field_unsupplied:files']] for k in ('missing', 'wrong')))
                # A station after the check recorded the branch it took; the subject now says otherwise: refused.
                name = 'unit-check-moved'
                unit(name, files=5)
                recorded = [dict(decision[0])]
                records = [record(name, name + '-b1', 'build', PIN_CHECKED, 'build'),
                           record(name, name + '-r1', 'review', PIN_CHECKED, 'review', follows=name + '-b1'),
                           record(name, name + '-r2', 'review', PIN_CHECKED, 'second', state='running',
                                  follows=name + '-b1', route=recorded, attempt_number=2)]
                moved = drive(name, PIN_CHECKED, checked, records)
                observed['check_moved'] = {'calls': moved['calls'], 'report': moved['report']}
                check('line/check-recorded-mismatch', lambda: offers(moved) == []
                      and [r['refusals'] for r in moved['report']['refused']]
                      == [['unsupported_workflow:branch_mismatch']])

            # A fan-out: both branches' stations are offered in the same pass, before either result is in.
            with region('line/dispatched-together', 'line/join-waits-for-all', 'line/budget-counts-branches'):
                name = 'unit-fan'
                unit(name)
                b1 = record(name, 'fan-b1', 'build', PIN_PARALLEL, 'build')
                together = drive(name, PIN_PARALLEL, parallel(), [b1])
                pins = {(c.get('workflow') or {}).get('node'): c.get('workflow') for c in together['calls']}
                observed['together'] = {'calls': together['calls'], 'report': together['report']}
                check('line/dispatched-together', lambda: sorted(offers(together)) == [('build', 'docs'),
                                                                                       ('review', 'design')]
                      and pins['design'].get('branch') == 'to-design' and pins['docs'].get('branch') == 'to-docs'
                      and {c['identity'] for c in together['calls'] if c['station'] == 'review'} == {'reviewer-b'}
                      and together['report']['refused'] == [])

                design_running = record(name, 'fan-r1', 'review', PIN_PARALLEL, 'design', state='running',
                                        follows='fan-b1', branch='to-design')
                design_done = record(name, 'fan-r1', 'review', PIN_PARALLEL, 'design', follows='fan-b1',
                                     branch='to-design')
                docs_running = record(name, 'fan-d1', 'build', PIN_PARALLEL, 'docs', state='running',
                                      branch='to-docs', attempt_number=2)
                docs_done = record(name, 'fan-d1', 'build', PIN_PARALLEL, 'docs', branch='to-docs', attempt_number=2)
                only_docs = drive(name, PIN_PARALLEL, parallel(), [b1, design_running, docs_done])
                only_design = drive(name, PIN_PARALLEL, parallel(), [b1, design_done, docs_running])
                both = drive(name, PIN_PARALLEL, parallel(), [b1, design_done, docs_done])
                final_running = record(name, 'fan-r2', 'review', PIN_PARALLEL, 'final', state='running',
                                       follows='fan-d1', attempt_number=2)
                after = drive(name, PIN_PARALLEL, parallel(), [b1, design_done, docs_done, final_running])
                observed['join'] = {k: {'calls': v['calls'], 'report': v['report']} for k, v in
                                    (('only_docs', only_docs), ('only_design', only_design), ('both', both),
                                     ('after', after))}
                check('line/join-waits-for-all', lambda: offers(only_docs) == [] and offers(only_design) == []
                      and offers(both) == [('review', 'final')]
                      and both['calls'][0]['revision'] == 'commit-fan-d1' and both['calls'][0]['follows'] == 'fan-d1'
                      and 'branch' not in both['calls'][0]['workflow']
                      and offers(after) == []
                      and only_docs['report']['refused'] == [] and only_design['report']['refused'] == [])

                # The step budget counts every node of every branch: build, design, docs, meet is four steps.
                tight = parallel('tight', steps=4)
                roomy = parallel('roomy', steps=5)
                short = drive(name, WU.pin(tight, 1), tight, [b1, design_done, docs_done])
                enough = drive(name, WU.pin(roomy, 1), roomy, [b1, design_done, docs_done])
                observed['budget'] = {'short': short['report'], 'enough': enough['calls']}
                check('line/budget-counts-branches', lambda: offers(short) == []
                      and [r['refusals'] for r in short['report']['refused']] == [['budget_exceeded:steps']]
                      and offers(enough) == [('review', 'final')])

            # The bound: at most 8 wide, and a unit's branches never hold two stations of one kind or the gate.
            with region('line/fan-out-bounded'):
                def wide(width):
                    kinds = {'build': 'build', 'meet': 'join', 'gate': 'gate', 'approval': 'owner_approval',
                             'land': 'land', 'done': 'end'}
                    edges, ids = [], []
                    for index in range(width):
                        kinds['check%d' % index] = 'check'
                        ids.append('to-%d' % index)
                        edges += [(ids[-1], 'build', 'done', 'check%d' % index),
                                  ('a%d' % index, 'check%d' % index, 'big', 'meet'),
                                  ('o%d' % index, 'check%d' % index, 'otherwise', 'meet')]
                    configs = dict(APPROVES, meet={'inputs': ids}, **{'check%d' % i: ROUTE for i in range(width)})
                    return graph('wide-%d' % width, kinds, edges + [('met', 'meet', 'done', 'gate')] + TAIL,
                                 configs=configs, fields=FIELDS)
                two_reviews = graph('two-reviews', dict(PARALLEL_KINDS, docs='review'), PARALLEL_EDGES,
                                    configs=dict(APPROVES, **MEET))
                gated = graph('gate-in-branch', dict(PARALLEL_KINDS, docs='gate'), PARALLEL_EDGES,
                              configs=dict(APPROVES, **MEET))
                problems = {'nine': WU.unit_problems(wide(9)), 'eight': WU.unit_problems(wide(8)),
                            'two_reviews': WU.unit_problems(two_reviews), 'gated': WU.unit_problems(gated)}
                observed['bounded'] = problems
                check('line/fan-out-bounded', lambda: 'unsupported_configuration:fan_out_too_wide:build'
                      in problems['nine'] and problems['eight'] == []
                      and problems['two_reviews'] == ['unsupported_configuration:parallel_station:docs']
                      and problems['gated'] == ['unsupported_configuration:parallel_station:docs'])

            # The approval rule on every path of a unit's process, checked at save; nothing is written.
            with region('line/approval-every-path'):
                around = graph('around', {'build': 'build', 'review': 'review', 'route': 'check', 'gate': 'gate',
                                          'approval': 'owner_approval', 'land': 'land', 'done': 'end'},
                               [('built', 'build', 'done', 'review'), ('reviewed', 'review', 'done', 'route'),
                                ('to-gate', 'route', 'big', 'gate'), ('to-land', 'route', 'otherwise', 'land')]
                               + TAIL, configs=dict(APPROVES, route=ROUTE), fields=FIELDS)
                # The docs branch lands; the approval after the join names it, so it is reached unapproved too.
                land_branch = graph('land-in-branch', dict(PARALLEL_KINDS, docs='land'), PARALLEL_EDGES,
                                    configs=dict(APPROVES, **MEET))
                land_branch['transitions'] = [t for t in land_branch['transitions'] if t['id'] != 'documented'] + [
                    {'id': 'land-' + port, 'from': 'docs', 'port': port, 'to': 'meet'} for port in WF.LAND_PORTS]
                land_branch['nodes'].pop('land')
                land_branch['nodes']['approval']['config'] = {'approves': 'docs'}
                land_branch['transitions'] = [t for t in land_branch['transitions']
                                              if t['from'] != 'land' and t['to'] != 'land']
                land_branch['transitions'].append({'id': 'approved', 'from': 'approval', 'port': 'granted',
                                                   'to': 'done'})
                approval_branch = graph('approval-in-branch', dict(PARALLEL_KINDS, design='owner_approval'),
                                        [e for e in PARALLEL_EDGES if e[0] != 'designed']
                                        + [('designed', 'design', 'granted', 'meet'),
                                           ('design-stopped', 'design', 'stopped', 'meet')],
                                        configs=dict(APPROVES, design={'approves': 'land'}, **MEET))
                after_join = parallel('after-join')
                cases = {'around': (around, 'invalid_input:missing_owner_approval:land'),
                         'land_branch': (land_branch, 'invalid_input:missing_owner_approval:outward_in_branch:docs'),
                         'approval_branch': (approval_branch, 'invalid_input:approval_not_last:approval_in_branch:design')}
                results = {}
                for key, (body, wanted) in cases.items():
                    before = journal_seq()
                    result = attempt(workflows.save, {'definition': body}, principal='owner', base=0)
                    results[key] = {'save': result, 'unit': WU.unit_problems(body), 'written': journal_seq() != before,
                                    'wanted': wanted}
                accepted = attempt(workflows.save, {'definition': after_join}, principal='owner', base=0)
                observed['approval'] = {'results': results, 'accepted': accepted}
                check('line/approval-every-path', lambda: all(
                    r['wanted'] in (r['save'].get('codes') or []) and r['wanted'] in r['unit'] and not r['written']
                    and WF.head_version(writer, DOMAIN, REPO, cases[k][0]['id']) == 0 for k, r in results.items())
                      and 'ok' in accepted and WU.unit_problems(after_join) == [])
        finally:
            with contextlib.suppress(Exception):
                writer.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V247_LINE_OBSERVED'] = observed


_v247_line_suite()
