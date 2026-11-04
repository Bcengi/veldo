"""VELDO-0241: a unit's process is a versioned workflow revision chosen per project or per kind of work, today's
code process ships as the default definition unchanged, and no definition can skip the owner's approval.

Only shared ROOT, expect and fast_temp are consumed. One temporary tree holds an installed .veldo copy; the
production anchors below are the registered mutation driver's seam, so a mutation of any of them reaches every
reader. The store is the real SQLite authority with OpenSSH journal and owner command signatures; workflow
revisions are saved through VELDO-0132's Workflows service and bindings through VELDO-0076's project service.

THE ORACLE OF DEFAULT EQUIVALENCE is today's Line: control_service.py as committed at BASELINE (the commit this
change was built on), read from history and loaded beside the same modules. Both Lines are driven over the same
unit states with their station methods (offer, limited, re-land, grant) recorded instead of dispatched, and the
recorded station sequence and pass report must be identical, except the revision fields the new Line adds. The
existing suites that run the real Line (83 factory loop, 86 re-land, 92 PM cycles, 116 project lines) are the
end-to-end half of that claim and run unchanged.
"""


def _v241_suite():
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
        'control_project.py': ROOT / ".veldo" / "control_project.py",
        'workflows/code.json': ROOT / ".veldo" / "workflows/code.json",
    }
    BASELINE = 'f6b081a47b8fe26e6887a62c01a820f4b1d2d414'

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def canon(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=repr)

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
        expect('VELDO-0241 ' + label, bool(condition))

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
    with tempfile.TemporaryDirectory(prefix='v241-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        (mods / 'workflows').mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        baseline = subprocess.run(['git', '-C', str(ROOT), 'show', BASELINE + ':.veldo/control_service.py'],
                                  capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
        if baseline.returncode == 0:
            (mods / 'control_service_v0240.py').write_bytes(baseline.stdout)
        S = load('v241_store', mods / 'control_store.py')
        SIG = load('v241_signer', mods / 'control_signer.py')
        CM = load('v241_membership', mods / 'control_membership.py')
        AC = CM.AC
        WF = load('v241_workflow', mods / 'control_workflow.py')
        WU = load('v241_workflow_unit', mods / 'control_workflow_unit.py')
        PJ = load('v241_project', mods / 'control_project.py')
        CS = load('v241_service', mods / 'control_service.py')
        DOMAIN, REPO, STORE = 'domain-241', 'repository-241', 'store-241'
        private = base / 'private'
        private.mkdir(mode=0o700)
        public = {}
        for who in ('journal', 'owner', 'other-owner'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', who, '-f', str(private / who)],
                           check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = (private / (who + '.pub')).read_text().strip()

        def signer(who, namespace):
            return lambda data: SIG.sign_bytes(private / who, data, namespace)
        journal_sign = signer('journal', 'veldo-journal')

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

        def member(principal, kind, roles):
            put(principal, 'membership', dict(principal_type=kind, roles=roles, scope='*', revoked_at=None,
                                              expires_at=None))

        member('owner', 'person', ['project_owner'])
        member('other-owner', 'person', ['project_owner'])
        member('agent-x', 'agent_run', ['project_owner'])
        for who in ('owner', 'other-owner'):
            put('key:%s:1' % who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
        ids = {'domain_uuid': DOMAIN, 'repository_uuid': REPO, 'store_uuid': STORE}
        projects = PJ.Projects(S, CM, writer, ids, 'setup', journal_sign, stop=lambda dispatch_id, reason: False)
        workflows = WF.Workflows(S, writer, domain=DOMAIN, repository=REPO, signer='setup', sign=journal_sign)

        def project_command(operation, name, principal='owner', **fields):
            serial[0] += 1
            body = dict(ids, operation=operation, project=name, principal=principal, command_id='pc-%d' % serial[0],
                        nonce='pn-%d' % serial[0], **fields)
            sign = signer(principal if principal in public else 'owner', AC.SIGNATURE_NAMESPACE)
            return projects.apply({'command': body, 'signature': sign(S.canonical_bytes(body))})

        activated = project_command('activate', 'alpha', owner='owner',
                                    charter={'purpose': 'Deliver the alpha work.', 'exclusions': []},
                                    execution_repository=REPO, authority_policy={'grooming': ['project_owner']},
                                    coordination_budget={'capacity': 20, 'invocations': 200, 'wall_seconds': 10 ** 6})
        observed['activated'] = activated

        def unit(name, project='alpha', **extra):
            put(name, 'execution_unit', dict(dict(state='READY', repository_uuid=REPO, project=project, revision=1,
                                                  depends_on=[], scope_digest='sha256:scope-' + name), **extra))

        def code(workflow_id='code', **changes):
            body = json.loads(json.dumps(WU.CODE))
            body['id'] = workflow_id
            body.update(changes)
            return body

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

            def __init__(self, lands):
                self.lands = lands

            def latest(self, name):
                return (self.lands.get(name) or [None])[-1]

            def records(self, name):
                return list(self.lands.get(name) or [])

        def report():
            return {key: [] for key in ('refused', 'offered', 'waiting', 'asked', 'awaiting', 'stopped', 'decisions',
                                        'lands', 'ended', 'released')}

        def make_line(module, lands=None, roles=None):
            line = object.__new__(module.Line)
            line.service, line.repository, line.gate = Service(), REPO, Gate()
            line.roles = roles or ROLES
            line.station = Station(lands) if lands is not None else None
            line.calls, line.pins = [], []

            def bare(payload):
                return {k: v for k, v in payload.items() if k != 'workflow'} if isinstance(payload, dict) else payload

            def offer(rep, name, station, role, **fields):
                line.pins.append(fields.pop('workflow', None))
                fields['payload'] = bare(fields.get('payload'))
                line.calls.append(['offer', name, station, role['identity'], fields])
                return 'offered:' + station

            def limited(record, rep):
                line.calls.append(['limited', record['dispatch_id']])
                return None

            def reland(name, last, rep, **fields):
                line.pins.append(fields.get('workflow'))
                line.calls.append(['reland', name, last['dispatch_id']])
                return 'relanded'

            def grant(name, last, rep, **fields):
                line.pins.append(fields.get('workflow'))
                line.calls.append(['grant', name, last['dispatch_id']])
                return 'granted'
            line.offer, line.limited, line.reland, line.grant = offer, limited, reland, grant
            return line

        def record(name, did, station, state='exited', rc=0, follows=None, holder='builder-a', workflow=None):
            payload = {'follows': follows}
            if workflow is not None:
                payload['workflow'] = workflow
            return {'dispatch_id': did, 'state': state, 'artifact': None,
                    'termination': {'returncode': rc, 'signal': None, 'deadline_stop': False},
                    'contract': {'unit': name, 'station': station, 'attempt': 1, 'source': {'commit': 'commit-' + did},
                                 'input': {'context': {'holder': holder}, 'payload': payload}}}

        def land(name, did, state, follows=None):
            return {'dispatch_id': did, 'unit': name, 'state': state, 'evidence': 'evidence-' + did, 'follows': follows,
                    'watermark': 'watermark-' + did, 'conflicts': ['README'], 'attempt': 1}

        # Every unit state the Line distinguishes today: (records, land records, roles).
        def scenarios():
            out = {}

            def add(key, records=(), lands=None, roles=None):
                out[key] = (list(records), lands, roles)
            add('nothing-yet')
            add('nothing-yet-no-station', lands=None)
            add('build-held', [('b1', 'build', dict(state='running'))])
            add('build-failed', [('b1', 'build', dict(rc=1))])
            add('build-completed', [('b1', 'build', {})])
            add('build-completed-no-independent-reviewer', [('b1', 'build', {})],
                roles={'builder': ROLES['builder'], 'reviewers': [ROLES['reviewers'][0]]})
            add('review-held', [('b1', 'build', {}), ('r1', 'review', dict(state='running', follows='b1'))])
            add('review-failed', [('b1', 'build', {}), ('r1', 'review', dict(rc=1, follows='b1'))])
            add('review-completed', [('b1', 'build', {}), ('r1', 'review', dict(follows='b1'))])
            for end in ('running', 'landed', 'unknown', 'failed', 'trunk_moved', 'awaiting_approval'):
                add('land-' + end, [('b1', 'build', {}), ('r1', 'review', dict(follows='b1'))],
                    lands=[('l1', end)])
            add('land-conflict', [('b1', 'build', {}), ('r1', 'review', dict(follows='b1'))], lands=[('l1', 'conflict')])
            add('rebuild-held', [('b2', 'build', dict(state='running', follows='l1')),
                                 ('r1', 'review', dict(follows='b1'))], lands=[('l1', 'conflict')])
            add('rebuild-failed', [('b2', 'build', dict(rc=1, follows='l1')), ('r1', 'review', dict(follows='b1'))],
                lands=[('l1', 'conflict')])
            add('rebuild-completed', [('b2', 'build', dict(follows='l1')), ('r1', 'review', dict(follows='b1'))],
                lands=[('l1', 'conflict')])
            add('rebuild-review-held', [('b2', 'build', dict(follows='l1')),
                                        ('r2', 'review', dict(state='running', follows='b2'))], lands=[('l1', 'conflict')])
            add('rebuild-reviewed', [('b2', 'build', dict(follows='l1')), ('r2', 'review', dict(follows='b2'))],
                lands=[('l1', 'conflict')])
            add('second-land-trunk-moved', [('b1', 'build', {}), ('r1', 'review', dict(follows='b1'))],
                lands=[('l1', 'trunk_moved'), ('l2', 'trunk_moved')])
            return out

        def drive(module, key, spec, pin=None):
            records, lands, roles = spec
            name = 'unit-%s' % key
            latest = {}
            for did, station, fields in records:
                latest[(name, station)] = record(name, '%s-%s' % (name, did), station, workflow=pin, **dict(
                    fields, **({'follows': '%s-%s' % (name, fields['follows'])} if fields.get('follows') else {})))
            land_records = None
            if lands is not None or key != 'nothing-yet-no-station':
                land_records = {name: [land(name, '%s-%s' % (name, did), end) for did, end in (lands or [])]}
            line = make_line(module, land_records, roles)
            rep = report()
            value = line.next(name, latest, rep)
            return line, {'value': value, 'calls': line.calls, 'report': rep}

        try:
            # AC1: the shipped `code` definition, as data, is today's process and passes the save checks.
            with region('default/shipped'):
                text = PRODUCTION['workflows/code.json'].read_text()
                shipped = json.loads(text)
                kinds = {name: node['kind'] for name, node in shipped['nodes'].items()}
                edges = {(t['from'], t['port']): t for t in shipped['transitions']}
                observed['shipped'] = {'problems': WU.unit_problems(shipped), 'kinds': kinds}
                check('default/shipped', lambda: WU.unit_problems(shipped) == [] and WF.definition_problems(shipped) == []
                      and WF.canonical(shipped) == WF.canonical(WU.CODE) and WF.canonical(WU.shipped()) == WF.canonical(WU.CODE)
                      and shipped['id'] == 'code' and shipped['entry'] == 'build'
                      and sorted(kinds.values()) == sorted(['build', 'review', 'gate', 'owner_approval', 'land', 'end'])
                      and [edges[('build', 'done')]['to'], edges[('review', 'done')]['to'], edges[('gate', 'passed')]['to'],
                           edges[('approval', 'granted')]['to']] == ['review', 'gate', 'approval', 'land']
                      and edges[('land', 'trunk_moved')]['to'] == 'land' and 'max' in edges[('land', 'trunk_moved')]
                      and edges[('land', 'conflict')]['to'] == 'build' and 'max' in edges[('land', 'conflict')]
                      and edges[('land', 'awaiting_approval')]['to'] == 'approval'
                      and 'max' in edges[('land', 'awaiting_approval')]
                      and WF.STEP_KINDS['land'].get('outward') is True and text.isascii())

            # AC1: on every unit state, today's Line and this Line offer the same stations with the same fields and
            # report the same pass, except the revision fields this Line adds.
            with region('default/equivalence'):
                OLD = load('v241_service_v0240', mods / 'control_service_v0240.py')
                compared, differing = {}, []
                for key, spec in sorted(scenarios().items()):
                    _old_line, old = drive(OLD, key, spec)
                    _new_line, new = drive(CS, key, spec)
                    compared[key] = {'old': old, 'new': new}
                    if canon(old) != canon(new):
                        differing.append(key)
                observed['equivalence'] = {'differing': differing, 'compared': compared}
                check('default/equivalence', lambda: baseline.returncode == 0 and len(compared) == 22 and not differing
                      and any(c['old']['calls'] for c in compared.values()))

            # AC1: a project with no binding runs `code` as the shipped revision, and the unit's first station
            # records it; a unit whose stations predate the record runs it too.
            with region('default/unbound-runs-code'):
                unit('unit-unbound', project='no-binding')
                line_first, _first = drive(CS, 'unbound', ([], {}, None))
                legacy_line, legacy = drive(CS, 'legacy', ([('b1', 'build', {})], {}, None))
                expected = dict(WU.pin(WU.CODE, 0), node='build')
                observed['unbound'] = {'pins': line_first.pins, 'legacy': legacy_line.pins}
                check('default/unbound-runs-code', lambda: line_first.pins == [expected]
                      and [c[2] for c in line_first.calls] == ['build'] and expected['version'] == WU.SHIPPED
                      and legacy_line.pins == [dict(expected, node='review')]
                      and not getattr(line_first, 'process_missing', {}))

            # AC2: the owner's approval is mandatory in every definition, checked at save, and nothing is written.
            with region('approval/code-saves', 'approval/removed', 'approval/side-edge', 'approval/build-after',
                        'approval/build-after-land', 'approval/later-outward-kinds'):
                saved = attempt(workflows.save, {'definition': code('code')}, principal='owner', base=0)
                check('approval/code-saves', lambda: saved['ok']['version'] == 1
                      and saved['ok']['definition_digest'] == WF.definition_digest(WU.CODE))

                def refused(name, definition, wanted):
                    before = journal_seq()
                    result = attempt(workflows.save, {'definition': definition}, principal='owner', base=0)
                    observed.setdefault('refusals', {})[name] = result
                    check('approval/' + name, lambda: wanted in (result.get('codes') or [])
                          and journal_seq() == before and WF.head_version(writer, DOMAIN, REPO, definition['id']) == 0
                          and WF.taxonomy(wanted) == 'unsupported_configuration')

                removed = code('removed')
                del removed['nodes']['approval']
                next(t for t in removed['transitions'] if t['id'] == 'gated')['to'] = 'land'
                next(t for t in removed['transitions'] if t['id'] == 're-approval')['to'] = 'land'
                removed['transitions'] = [t for t in removed['transitions'] if t['from'] != 'approval']
                refused('removed', removed, 'invalid_input:missing_owner_approval:land')
                side = code('side-edge')
                next(t for t in side['transitions'] if t['id'] == 'stopped')['to'] = 'land'
                refused('side-edge', side, 'invalid_input:missing_owner_approval:land')
                after = code('build-after')
                after['nodes']['rebuild'] = {'kind': 'build', 'config': {}}
                next(t for t in after['transitions'] if t['id'] == 'approved')['to'] = 'rebuild'
                after['transitions'].append({'id': 'rebuilt', 'from': 'rebuild', 'port': 'done', 'to': 'land'})
                refused('build-after', after, 'invalid_input:approval_not_last:approval')
                around = code('build-after-land')
                around['nodes']['rebuild'] = {'kind': 'build', 'config': {}}
                next(t for t in around['transitions'] if t['id'] == 're-build')['to'] = 'rebuild'
                around['transitions'].append({'id': 'rebuilt', 'from': 'rebuild', 'port': 'done', 'to': 'land',
                                              'max': 4})
                refused('build-after-land', around, 'invalid_input:approval_not_last:approval')
                # A later outward kind (deliver, publish, deploy) inherits the rule by being registered outward.
                WF.STEP_KINDS['deliver'] = {'ports': ('done',), 'config': {}, 'input': None, 'terminal': False,
                                            'station': True, 'outward': True}
                try:
                    later = code('later-kind')
                    later['nodes']['deliver'] = {'kind': 'deliver', 'config': {}}
                    next(t for t in later['transitions'] if t['id'] == 'landed')['to'] = 'deliver'
                    later['transitions'].append({'id': 'delivered', 'from': 'deliver', 'port': 'done', 'to': 'done'})
                    before = journal_seq()
                    result = attempt(workflows.save, {'definition': later}, principal='owner', base=0)
                    approved = code('later-approved')
                    approved['nodes']['deliver'] = {'kind': 'deliver', 'config': {}}
                    approved['nodes']['deliver-approval'] = {'kind': 'owner_approval', 'config': {'approves': 'deliver'}}
                    next(t for t in approved['transitions'] if t['id'] == 'landed')['to'] = 'deliver-approval'
                    approved['transitions'] += [
                        {'id': 'deliver-granted', 'from': 'deliver-approval', 'port': 'granted', 'to': 'deliver'},
                        {'id': 'deliver-stopped', 'from': 'deliver-approval', 'port': 'stopped', 'to': 'done'},
                        {'id': 'delivered', 'from': 'deliver', 'port': 'done', 'to': 'done'}]
                    accepted = WF.definition_problems(approved)
                finally:
                    del WF.STEP_KINDS['deliver']
                observed['later'] = {'refused': result, 'accepted': accepted}
                check('approval/later-outward-kinds', lambda: 'invalid_input:missing_owner_approval:deliver'
                      in result.get('codes', []) and journal_seq() == before and accepted == [])

            # AC3: the project owner binds a kind of work to an accepted revision by his signed command.
            with region('binding/owner-binds', 'binding/refusals', 'binding/kind-of-work', 'binding/pinned-revision'):
                flow1 = attempt(workflows.save, {'definition': code('flow')}, principal='owner', base=0)['ok']
                docs = code('docs-flow')
                docs['nodes'].pop('review')
                next(t for t in docs['transitions'] if t['id'] == 'built')['to'] = 'gate'
                docs['transitions'] = [t for t in docs['transitions'] if t['id'] != 'reviewed']
                docs1 = attempt(workflows.save, {'definition': docs}, principal='owner', base=0)['ok']
                cycle = {'schema': WF.SCHEMA, 'id': 'cycle', 'entry': 'groom', 'terminal': ['handle'],
                         'nodes': {'groom': {'kind': 'grooming', 'config': {}},
                                   'handle': {'kind': 'result_handling', 'config': {}}},
                         'transitions': [{'id': 'groomed', 'from': 'groom', 'port': 'groomed', 'to': 'handle'}],
                         'references': {}, 'budget': {'steps': 4}}
                cycle1 = attempt(workflows.save, {'definition': cycle}, principal='owner', base=0)

                def version():
                    return entity('project:alpha')['version']
                bound = project_command('bind_workflow', 'alpha', kind_of_work='default', workflow='flow', version=1,
                                        project_version=version())
                bound_docs = project_command('bind_workflow', 'alpha', kind_of_work='docs', workflow='docs-flow',
                                             version=1, project_version=version())
                data = entity('project:alpha')['data']
                observation = projects.observations[-1]
                observed['bindings'] = {'bound': bound, 'docs': bound_docs, 'workflows': data.get('workflows'),
                                        'log': data.get('workflow_bindings'), 'cycle': cycle1}
                check('binding/owner-binds', lambda: bound['ok'] and bound_docs['ok']
                      and data['workflows'] == {'default': {'workflow': 'flow', 'version': 1,
                                                            'digest': flow1['definition_digest']},
                                                'docs': {'workflow': 'docs-flow', 'version': 1,
                                                         'digest': docs1['definition_digest']}}
                      and [(b['kind_of_work'], b['old'], b['new']['workflow'], b['by'], b['project'])
                           for b in data['workflow_bindings']] == [('default', None, 'flow', 'owner', 'alpha'),
                                                                     ('docs', None, 'docs-flow', 'owner', 'alpha')]
                      and all(b['command_id'].startswith('pc-') and b['at'] for b in data['workflow_bindings'])
                      and observation['binding']['kind_of_work'] == 'docs'
                      and data['state'] == 'ACTIVE' and data['history'] == activated['project']['history'])

                before = (version(), journal_seq())
                refusals = {
                    'not_owner': project_command('bind_workflow', 'alpha', principal='other-owner', workflow='flow',
                                                 version=1, project_version=version())['reason'],
                    'agent': project_command('bind_workflow', 'alpha', principal='agent-x', workflow='flow', version=1,
                                             project_version=version())['reason'],
                    'absent': project_command('bind_workflow', 'alpha', workflow='flow', version=9,
                                              project_version=version())['reason'],
                    'not_a_unit_workflow': project_command('bind_workflow', 'alpha', workflow='cycle', version=1,
                                                           project_version=version())['reason'],
                    'stale': project_command('bind_workflow', 'alpha', workflow='flow', version=1,
                                             project_version=version() - 1)['reason'],
                }
                observed['binding_refusals'] = refusals
                check('binding/refusals', lambda: refusals == {
                    'not_owner': 'not_owner', 'agent': 'not_authorized', 'absent': 'missing_workflow',
                    'not_a_unit_workflow': 'missing_workflow:not_a_unit_workflow', 'stale': 'stale_subject'}
                      and (version(), journal_seq()) == before and 'ok' in cycle1
                      and PJ.taxonomy('missing_workflow') == 'missing_evidence')

                # The unit's kind of work picks the binding; one the project does not bind takes `default`.
                unit('unit-plain')
                unit('unit-docs', kind_of_work='docs')
                unit('unit-media', kind_of_work='media')
                chosen = {}
                for name in ('unit-plain', 'unit-docs', 'unit-media'):
                    line = make_line(CS, {})
                    line.next(name, {}, report())
                    chosen[name] = line.pins
                observed['kinds'] = chosen
                check('binding/kind-of-work', lambda: chosen == {
                    'unit-plain': [{'id': 'flow', 'version': 1, 'digest': flow1['definition_digest'], 'node': 'build'}],
                    'unit-docs': [{'id': 'docs-flow', 'version': 1, 'digest': docs1['definition_digest'],
                                   'node': 'build'}],
                    'unit-media': [{'id': 'flow', 'version': 1, 'digest': flow1['definition_digest'], 'node': 'build'}]})

                # A unit stays on the revision it recorded when a new revision is saved and bound mid-unit; the next
                # new unit takes the new one.
                unit('unit-early')
                line = make_line(CS, {})
                line.next('unit-early', {}, report())
                early_pin = line.pins[0]
                flow2_body = json.loads(json.dumps(docs))
                flow2_body['id'] = 'flow'
                flow2 = attempt(workflows.save, {'definition': flow2_body}, principal='owner', base=1)['ok']
                rebound = project_command('bind_workflow', 'alpha', kind_of_work='default', workflow='flow', version=2,
                                          project_version=version())
                built = {('unit-early', 'build'): record('unit-early', 'early-b1', 'build', workflow=early_pin)}
                line = make_line(CS, {})
                line.next('unit-early', built, report())
                early_next = (line.calls, line.pins)
                unit('unit-late')
                line = make_line(CS, {})
                line.next('unit-late', {}, report())
                late_pin = line.pins[0] if line.pins else None
                late_built = {('unit-late', 'build'): record('unit-late', 'late-b1', 'build', workflow=late_pin)}
                line = make_line(CS, {})
                late_value = line.next('unit-late', late_built, report())
                late_next = (line.calls, line.pins)
                observed['pinned'] = {'early': early_pin, 'early_next': early_next, 'late': late_pin,
                                      'late_next': late_next, 'rebound': rebound, 'flow2': flow2}
                check('binding/pinned-revision', lambda: rebound['ok'] and flow2['version'] == 2
                      and early_pin['version'] == 1
                      and [c[2] for c in early_next[0]] == ['review'] and early_next[1] == [dict(early_pin, node='review')]
                      and late_pin == {'id': 'flow', 'version': 2, 'digest': flow2['definition_digest'], 'node': 'build'}
                      and late_value is None and late_next == ([], []))
        finally:
            with contextlib.suppress(Exception):
                writer.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V241_OBSERVED'] = observed


_v241_started = __import__('time').monotonic()
_v241_suite()
_V241_SECONDS = __import__('time').monotonic() - _v241_started
