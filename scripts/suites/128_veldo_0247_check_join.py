"""VELDO-0247: a Check step routes the work by a plain rule over declared fields with a required otherwise path,
parallel branches from one step run at the same time on the real LangGraph runtime and a Join step waits for all
of them, every fan-out is bounded, and no branch can go around the owner's approval.

Only shared ROOT, expect and fast_temp are consumed. One temporary tree holds an installed .veldo copy; the
production anchors below are the registered mutation driver's seam, so a mutation of any of them reaches every
reader, including the runner each cycle stages. The store is the real SQLite authority with OpenSSH journal
signatures; saves go through VELDO-0132's Workflows service; cycles run through VELDO-0132's Cycles service on the
VELDO-0045 activated LangGraph runtime, staged into a temporary directory so the account's stage is never touched.
When that runtime is absent every cycle is refused unavailable_service and every cycle row fails by name.

The role and tool configuration records, admissions and the proof bundles a worker's result stands for are
fixture records written with the store's generic command, as in suite 65.
"""


def _v247_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_workflow.py': ROOT / ".veldo" / "control_workflow.py",
        'control_workflow_cycle.py': ROOT / ".veldo" / "control_workflow_cycle.py",
        'control_workflow_langgraph.py': ROOT / ".veldo" / "control_workflow_langgraph.py",
        'control_graph_langgraph.py': ROOT / ".veldo" / "control_graph_langgraph.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def canon(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

    def sha(text):
        return 'sha256:' + hashlib.sha256(text.encode() if type(text) is str else text).hexdigest()

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
    with tempfile.TemporaryDirectory(prefix='v247-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copytree(ROOT / '.veldo' / 'runtime', mods / 'runtime')
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v247_store', mods / 'control_store.py')
        EL = load('v247_eligibility', mods / 'control_eligibility.py')
        RS = load('v247_readset', mods / 'control_readset.py')
        SIG = load('v247_signer', mods / 'control_signer.py')
        _git_process = load('v247_git', mods / 'git_process.py')
        WF = load('v247_workflow', mods / 'control_workflow.py')
        CY = load('v247_cycle', mods / 'control_workflow_cycle.py')
        DOMAIN, REPOSITORY = 'domain-247', 'repository-247'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'journal', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        work = base / 'work'
        (work / 'specs').mkdir(parents=True)
        UNITS = ['VELDO-97%02d' % n for n in range(1, 11)]
        for sid in UNITS:
            (work / 'specs' / (sid + '-check-fixture.md')).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Check fixture unit', 'status: ready',
                'risk: standard', 'owner: owner', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', '---', '', '## Intent', '', 'Check fixture.', '']))
        (work / 'README').write_text('check fixture\n')

        def git(*args):
            return _git_process.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                                    identity=('Owner', 'owner@example.invalid')).stdout.strip()

        _git_process.run(['git', 'init', '-q', str(work)], check=True, capture_output=True)
        git('add', '-A')
        git('commit', '-q', '-m', 'Check fixture repository')
        commit = git('rev-parse', 'HEAD')

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        snapshots_conn = S.open_store(str(db))
        reader = S.open_store(str(db), mode='r')
        connections = [writer, snapshots_conn, reader]
        serial = [0]

        def entity(identity):
            row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            command_id = 'setup-%d' % serial[0]
            S.execute(writer, dict(command_id=command_id, principal='owner', operation='upsert_entity', nonce=command_id,
                                   artifact_digests=[], expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)
            return entity(identity)

        def ref(identity):
            row = entity(identity)
            return {'id': identity, 'version': row['version'], 'digest': row['digest']}

        def member(principal, kind, **extra):
            put(principal, 'membership', dict(dict(principal_type=kind, roles=[], scope=[REPOSITORY], revoked_at=None,
                                                   expires_at=None), **extra))

        member('owner', 'person', roles=['project_owner'])
        member('cycle-runner', 'service')
        member('builder-agent', 'agent_run')
        put('role-builder', 'role_configuration', dict(role='builder', principal='builder-agent'))
        put('tools-default', 'tool_configuration', dict(tools=['Read', 'Edit']))
        put('project:p1', 'project', dict(name='check'))
        # The fields the check reads: `files` (a number) and `risk` (a choice, marked private).
        FIELDS = {'VELDO-9701': {'files': 25, 'risk': 'low'}, 'VELDO-9702': {'files': 3, 'risk': 'high'},
                  'VELDO-9703': {'files': 3, 'risk': 'low'}, 'VELDO-9704': {'risk': 'low'},
                  'VELDO-9705': {'files': 'lots', 'risk': 'low'}, 'VELDO-9706': {'files': 3, 'risk': 'low'}}
        for sid in UNITS:
            put(sid, 'execution_unit', dict(dict(state='READY', repository_uuid=REPOSITORY,
                                                 backlog_item_uuid='backlog:' + sid, project='p1',
                                                 scope_digest='sha256:scope-' + sid, revision=1, depends_on=[],
                                                 risk='standard'), **FIELDS.get(sid, {})))
            put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
        for sid in ('VELDO-9707', 'VELDO-9708', 'VELDO-9709'):
            put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))

        __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/git_identity.py'))['bind_paths'](
            Path(S.__file__).parent, snapshots_conn, DOMAIN, {REPOSITORY: str(work)})
        revisions = RS.attach_revisions(S, snapshots_conn, DOMAIN, {REPOSITORY: str(work)})
        revisions.accept('revision-247', REPOSITORY, commit, 'owner',
                         documents={'README': sha((work / 'README').read_bytes())},
                         statuses={}, signer='owner', sign=sign, authority_generation=1)
        readsets = RS.attach(S, snapshots_conn, work, DOMAIN, REPOSITORY)
        readsets.enable('upsert_entity', {'revision': 'revision-247', 'entities': {'unit': '$unit'}, 'collections': {}})
        readsets.execute({'command_id': 'snapshot-247', 'principal': 'owner', 'operation': 'accept_snapshot',
                          'parameters': {'snapshot_id': 'snapshot-247', 'operation': 'upsert_entity',
                                         'arguments': {'unit': 'VELDO-9701'}},
                          'expected_versions': {'snapshot-247': 0}, 'artifact_digests': [], 'nonce': 'snapshot-247'},
                         signer='owner', sign=sign, authority_generation=1)
        snapshot = ref('snapshot-247')

        events = []
        workflows = WF.Workflows(S, writer, domain=DOMAIN, repository=REPOSITORY, signer='workflow-service', sign=sign,
                                 observe=events.append)

        def journal_seq():
            return writer.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        def save_refused(body, expected):
            """The save is refused naming `expected` (a prefix) and writes nothing."""
            before = journal_seq()
            answer = attempt(workflows.save, {'definition': body}, principal='owner', base=0)
            codes = answer.get('codes') or []
            return {'answer': answer, 'named': any(code.startswith(expected) for code in codes),
                    'nothing': journal_seq() == before and WF.head_version(writer, DOMAIN, REPOSITORY, body['id']) == 0}

        # -- definitions --------------------------------------------------------------------------------

        CHECK_FIELDS = {'files': {'type': 'number', 'source': {'subject': 'files'}},
                        'risk': {'type': 'choice', 'choices': ['low', 'high', 'critical'], 'source': {'subject': 'risk'},
                                 'private': True}}

        def routed(workflow='routed'):
            """groom -> check: many (files more than 20) -> wait_many; risky (risk is one of high, critical) ->
            wait_risky; otherwise -> wait_other. Each wait admits to the assignment and declines back to groom."""
            nodes = {'groom': {'kind': 'grooming', 'config': {}},
                     'route': {'kind': 'check', 'config': {
                         'branches': [{'name': 'many', 'conditions': [
                                          {'field': 'files', 'comparison': 'more than', 'value': 20}]},
                                      {'name': 'risky', 'conditions': [
                                          {'field': 'risk', 'comparison': 'is one of', 'value': ['high', 'critical']},
                                          {'field': 'files', 'comparison': 'at most', 'value': 20}]}],
                         'otherwise': True}},
                     'wait_many': {'kind': 'owner_wait', 'config': {}},
                     'wait_risky': {'kind': 'owner_wait', 'config': {}},
                     'wait_other': {'kind': 'owner_wait', 'config': {}},
                     'assign': {'kind': 'assignment', 'config': {'role': 'builder', 'tools': ['default']}},
                     'handle': {'kind': 'result_handling', 'config': {}}}
            transitions = [{'id': 't-groomed', 'from': 'groom', 'port': 'groomed', 'to': 'route'},
                           {'id': 't-many', 'from': 'route', 'port': 'many', 'to': 'wait_many'},
                           {'id': 't-risky', 'from': 'route', 'port': 'risky', 'to': 'wait_risky'},
                           {'id': 't-other', 'from': 'route', 'port': 'otherwise', 'to': 'wait_other'},
                           {'id': 't-done', 'from': 'assign', 'port': 'done', 'to': 'handle'}]
            for wait in ('wait_many', 'wait_risky', 'wait_other'):
                transitions += [{'id': 't-admit-' + wait, 'from': wait, 'port': 'admit', 'to': 'assign'},
                                {'id': 't-decline-' + wait, 'from': wait, 'port': 'decline', 'to': 'groom', 'max': 1}]
            return {'schema': 'veldo.workflow/v1', 'id': workflow, 'entry': 'groom', 'terminal': ['handle'],
                    'fields': json.loads(json.dumps(CHECK_FIELDS)), 'nodes': nodes, 'transitions': transitions,
                    'references': {'roles': {'builder': ref('role-builder')}, 'tools': {'default': ref('tools-default')}},
                    'budget': {'steps': 24}}

        def fanned(workflow='fanned', width=2):
            """groom fans out to `width` assignment branches that meet at one join, then the result handling."""
            names = ['copy', 'image'] + ['extra%d' % n for n in range(width - 2)]
            nodes = {'groom': {'kind': 'grooming', 'config': {}},
                     'meet': {'kind': 'join', 'config': {'inputs': list(names)}},
                     'handle': {'kind': 'result_handling', 'config': {}}}
            transitions = [{'id': 't-joined', 'from': 'meet', 'port': 'done', 'to': 'handle'}]
            for name in names:
                nodes['assign_' + name] = {'kind': 'assignment', 'config': {'role': 'builder', 'tools': ['default']}}
                transitions += [{'id': name, 'from': 'groom', 'port': 'groomed', 'to': 'assign_' + name},
                                {'id': 't-arrive-' + name, 'from': 'assign_' + name, 'port': 'done', 'to': 'meet'}]
            return {'schema': 'veldo.workflow/v1', 'id': workflow, 'entry': 'groom', 'terminal': ['handle'],
                    'nodes': nodes, 'transitions': transitions,
                    'references': {'roles': {'builder': ref('role-builder')}, 'tools': {'default': ref('tools-default')}},
                    'budget': {'steps': 24}}

        try:
            # AC1: the check's configuration is closed and checked at save.
            with region('check/configuration-accepted', 'check/configuration-refusals'):
                good = routed('probe')
                accepted = attempt(workflows.save, {'definition': routed('routed')}, principal='owner', base=0)
                ports = sorted(t['port'] for t in good['transitions'] if t['from'] == 'route')
                check('check/configuration-accepted',
                      lambda: WF.definition_problems(good) == [] and (accepted.get('ok') or {}).get('version') == 1
                      and ports == ['many', 'otherwise', 'risky'])

                def variant(mutate):
                    body = json.loads(json.dumps(good))
                    mutate(body)
                    return body

                def condition(body):
                    return body['nodes']['route']['config']['branches'][0]['conditions'][0]

                def text_field(body):
                    body['fields']['title'] = {'type': 'text', 'source': {'subject': 'title'}}
                    condition(body).update(field='title', comparison='contains')

                cases = {
                    'no_otherwise': (lambda d: d['nodes']['route']['config'].pop('otherwise'),
                                     'unsupported_configuration:check_without_otherwise:route'),
                    'undeclared_field': (lambda d: condition(d).update(field='ghost'),
                                         'unsupported_configuration:undeclared_field:route:ghost'),
                    'unknown_comparison': (lambda d: condition(d).update(comparison='matches'),
                                           'unsupported_configuration:unknown_comparison:route:matches'),
                    'type_disallows': (lambda d: condition(d).update(comparison='contains'),
                                       'unsupported_configuration:unknown_comparison:route:contains'),
                    'value_type': (lambda d: condition(d).update(value='twenty'),
                                   'unsupported_configuration:value_type:route:many'),
                    'value_type_bool': (lambda d: condition(d).update(value=True),
                                        'unsupported_configuration:value_type:route:many'),
                    'choice_not_listed': (lambda d: d['nodes']['route']['config']['branches'][1]['conditions'][0]
                                          .update(value=['high', 'severe']),
                                          'unsupported_configuration:value_type:route:risky'),
                    'text_too_long': (lambda d: (text_field(d), condition(d).update(value='a' * 201)),
                                      'unsupported_configuration:value_type:route:many'),
                    'field_from_unrun_step': (lambda d: d['fields'].update(
                        files={'type': 'number', 'source': {'node': 'assign', 'result': 'files'}}),
                        'unsupported_configuration:undeclared_field:route:files'),
                }
                for key in ('expression', 'code', 'script', 'shell', 'template'):
                    cases['extra_condition_' + key] = (lambda d, key=key: condition(d).update({key: 'make build'}),
                                                       'unsupported_configuration:invalid_config:route')
                    cases['extra_branch_' + key] = (
                        lambda d, key=key: d['nodes']['route']['config']['branches'][0].update({key: 'x'}),
                        'unsupported_configuration:invalid_config:route')
                    cases['extra_config_' + key] = (lambda d, key=key: d['nodes']['route']['config'].update({key: 'x'}),
                                                    'unsupported_configuration:invalid_config:route')
                for label, value in (('dollar', '$(rm -rf .)'), ('brace', 'a{b}'), ('backtick', 'a`b`'),
                                     ('quote', "it's"), ('double_quote', 'say "x"'), ('bracket', 'a[0]'),
                                     ('parenthesis', 'f(x)'), ('semicolon', 'a; b'), ('pipe', 'a | b'),
                                     ('angle', 'a > b'), ('equals', 'a=b')):
                    cases['code_like_' + label] = (lambda d, value=value: (text_field(d), condition(d).update(value=value)),
                                                   'unsupported_configuration:code_like_value:route:many')
                results = {name: save_refused(variant(mutate), wanted) for name, (mutate, wanted) in sorted(cases.items())}
                # The plain text the canvas offers is accepted: letters, digits, spaces and . , - _ / : @.
                plain = variant(lambda d: (text_field(d), condition(d).update(value='Release 2.1, part-a_b/c: x@y')))
                observed['configuration'] = {name: {'named': r['named'], 'nothing': r['nothing'],
                                                    'codes': r['answer'].get('codes')} for name, r in results.items()}
                check('check/configuration-refusals',
                      lambda: all(r['named'] and r['nothing'] for r in results.values())
                      and WF.definition_problems(plain) == [])

            # AC4: the approval rule holds on every path through checks, branches and joins.
            with region('approval/branch-around-approval', 'approval/check-after-approval', 'approval/in-branch',
                        'approval/land-in-branch', 'approval/moved-accepted'):
                UNIT_FIELDS = {'size': {'type': 'number', 'source': {'subject': 'size'}}}

                def unit_definition(workflow, nodes, transitions):
                    nodes = dict(nodes, done={'kind': 'end', 'config': {}})
                    return {'schema': 'veldo.workflow/v1', 'id': workflow, 'entry': 'build', 'terminal': ['done'],
                            'fields': json.loads(json.dumps(UNIT_FIELDS)), 'nodes': nodes, 'transitions': transitions,
                            'references': {}, 'budget': {'steps': 32}}

                def size_check(name='big'):
                    return {'kind': 'check', 'config': {'branches': [{'name': name, 'conditions': [
                        {'field': 'size', 'comparison': 'more than', 'value': 20}]}], 'otherwise': True}}

                def land_out(source='land'):
                    return [{'id': 't-%s-%s' % (source, port), 'from': source, 'port': port, 'to': 'done'}
                            for port in WF.LAND_PORTS]

                approval = {'kind': 'owner_approval', 'config': {'approves': 'land'}}
                # (a) the named branch passes the approval, otherwise goes straight to land.
                around = unit_definition('around', {
                    'build': {'kind': 'build', 'config': {}}, 'route': size_check(), 'approval': approval,
                    'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 't-built', 'from': 'build', 'port': 'done', 'to': 'route'},
                    {'id': 't-big', 'from': 'route', 'port': 'big', 'to': 'approval'},
                    {'id': 't-other', 'from': 'route', 'port': 'otherwise', 'to': 'land'},
                    {'id': 't-granted', 'from': 'approval', 'port': 'granted', 'to': 'land'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'}] + land_out())
                around_fixed = unit_definition('around-fixed', {
                    'build': {'kind': 'build', 'config': {}}, 'route': size_check(), 'approval': approval,
                    'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 't-built', 'from': 'build', 'port': 'done', 'to': 'approval'},
                    {'id': 't-granted', 'from': 'approval', 'port': 'granted', 'to': 'route'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'},
                    {'id': 't-big', 'from': 'route', 'port': 'big', 'to': 'land'},
                    {'id': 't-other', 'from': 'route', 'port': 'otherwise', 'to': 'land'}] + land_out())
                # (b) a check after the approval whose otherwise branch leads to a build, then land.
                after = unit_definition('after', {
                    'build': {'kind': 'build', 'config': {}}, 'approval': approval, 'route': size_check('small'),
                    'rebuild': {'kind': 'build', 'config': {}}, 'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 't-built', 'from': 'build', 'port': 'done', 'to': 'approval'},
                    {'id': 't-granted', 'from': 'approval', 'port': 'granted', 'to': 'route'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'},
                    {'id': 't-small', 'from': 'route', 'port': 'small', 'to': 'land'},
                    {'id': 't-other', 'from': 'route', 'port': 'otherwise', 'to': 'rebuild'},
                    {'id': 't-rebuilt', 'from': 'rebuild', 'port': 'done', 'to': 'land'}] + land_out())
                after_fixed = unit_definition('after-fixed', {
                    'build': {'kind': 'build', 'config': {}}, 'approval': approval, 'route': size_check('small'),
                    'rebuild': {'kind': 'build', 'config': {}}, 'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 't-built', 'from': 'build', 'port': 'done', 'to': 'route'},
                    {'id': 't-small', 'from': 'route', 'port': 'small', 'to': 'approval'},
                    {'id': 't-other', 'from': 'route', 'port': 'otherwise', 'to': 'rebuild'},
                    {'id': 't-rebuilt', 'from': 'rebuild', 'port': 'done', 'to': 'approval'},
                    {'id': 't-granted', 'from': 'approval', 'port': 'granted', 'to': 'land'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'}] + land_out())
                # (c) an approval inside one parallel branch with a build in the other.
                inside = unit_definition('inside', {
                    'build': {'kind': 'build', 'config': {}}, 'review': {'kind': 'review', 'config': {}},
                    'approval': approval, 'rebuild': {'kind': 'build', 'config': {}},
                    'meet': {'kind': 'join', 'config': {'inputs': ['pa', 'pb']}}, 'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 't-built', 'from': 'build', 'port': 'done', 'to': 'review'},
                    {'id': 'pa', 'from': 'review', 'port': 'done', 'to': 'approval'},
                    {'id': 'pb', 'from': 'review', 'port': 'done', 'to': 'rebuild'},
                    {'id': 't-granted', 'from': 'approval', 'port': 'granted', 'to': 'meet'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'meet'},
                    {'id': 't-rebuilt', 'from': 'rebuild', 'port': 'done', 'to': 'meet'},
                    {'id': 't-joined', 'from': 'meet', 'port': 'done', 'to': 'land'}] + land_out())
                inside_fixed = unit_definition('inside-fixed', {
                    'build': {'kind': 'build', 'config': {}}, 'review': {'kind': 'review', 'config': {}},
                    'gate': {'kind': 'gate', 'config': {}}, 'rebuild': {'kind': 'build', 'config': {}},
                    'meet': {'kind': 'join', 'config': {'inputs': ['pa', 'pb']}}, 'approval': approval,
                    'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 't-built', 'from': 'build', 'port': 'done', 'to': 'review'},
                    {'id': 'pa', 'from': 'review', 'port': 'done', 'to': 'gate'},
                    {'id': 'pb', 'from': 'review', 'port': 'done', 'to': 'rebuild'},
                    {'id': 't-gated', 'from': 'gate', 'port': 'passed', 'to': 'meet'},
                    {'id': 't-rebuilt', 'from': 'rebuild', 'port': 'done', 'to': 'meet'},
                    {'id': 't-joined', 'from': 'meet', 'port': 'done', 'to': 'approval'},
                    {'id': 't-granted', 'from': 'approval', 'port': 'granted', 'to': 'land'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'}] + land_out())
                # (d) a land inside a branch, even after a granted approval.
                land_inside = unit_definition('land-inside', {
                    'build': {'kind': 'build', 'config': {}}, 'approval': approval, 'gate': {'kind': 'gate', 'config': {}},
                    'meet': {'kind': 'join', 'config': {'inputs': ['la', 'lb']}}, 'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 't-built', 'from': 'build', 'port': 'done', 'to': 'approval'},
                    {'id': 'la', 'from': 'approval', 'port': 'granted', 'to': 'land'},
                    {'id': 'lb', 'from': 'approval', 'port': 'granted', 'to': 'gate'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'},
                    {'id': 't-gated', 'from': 'gate', 'port': 'passed', 'to': 'meet'},
                    {'id': 't-joined', 'from': 'meet', 'port': 'done', 'to': 'done'}]
                    + [{'id': 't-land-' + port, 'from': 'land', 'port': port, 'to': 'meet'} for port in WF.LAND_PORTS])
                land_fixed = unit_definition('land-fixed', {
                    'build': {'kind': 'build', 'config': {}}, 'review': {'kind': 'review', 'config': {}},
                    'gate': {'kind': 'gate', 'config': {}}, 'meet': {'kind': 'join', 'config': {'inputs': ['la', 'lb']}},
                    'approval': approval, 'land': {'kind': 'land', 'config': {}}}, [
                    {'id': 'la', 'from': 'build', 'port': 'done', 'to': 'review'},
                    {'id': 'lb', 'from': 'build', 'port': 'done', 'to': 'gate'},
                    {'id': 't-reviewed', 'from': 'review', 'port': 'done', 'to': 'meet'},
                    {'id': 't-gated', 'from': 'gate', 'port': 'passed', 'to': 'meet'},
                    {'id': 't-joined', 'from': 'meet', 'port': 'done', 'to': 'approval'},
                    {'id': 't-granted', 'from': 'approval', 'port': 'granted', 'to': 'land'},
                    {'id': 't-stopped', 'from': 'approval', 'port': 'stopped', 'to': 'done'}] + land_out())
                refused = {
                    'around': save_refused(around, 'invalid_input:missing_owner_approval:land'),
                    'after': save_refused(after, 'invalid_input:approval_not_last:approval'),
                    'inside': save_refused(inside, 'invalid_input:approval_not_last:approval_in_branch:approval'),
                    'land_inside': save_refused(land_inside, 'invalid_input:missing_owner_approval:outward_in_branch:land'),
                }
                moved = {body['id']: attempt(workflows.save, {'definition': body}, principal='owner', base=0)
                         for body in (around_fixed, after_fixed, inside_fixed, land_fixed)}
                observed['approval'] = {'refused': {k: {'codes': v['answer'].get('codes'), 'named': v['named'],
                                                        'nothing': v['nothing']} for k, v in refused.items()},
                                        'moved': moved}

                def held(name):
                    return refused[name]['named'] and refused[name]['nothing']

                check('approval/branch-around-approval', lambda: held('around'))
                check('approval/check-after-approval', lambda: held('after'))
                check('approval/in-branch', lambda: held('inside'))
                check('approval/land-in-branch', lambda: held('land_inside'))
                check('approval/moved-accepted', lambda: all((m.get('ok') or {}).get('version') == 1
                                                             for m in moved.values()))

            # AC3 at save: a fan-out is bounded and every branch meets its one join.
            with region('fanout/bounded-at-save'):
                nine = save_refused(fanned('nine', 9), 'unsupported_configuration:fan_out_too_wide:groom')
                eight = WF.definition_problems(fanned('eight', 8))
                wrong_join = fanned('wrong-join')
                wrong_join['nodes']['meet']['config']['inputs'] = ['copy']
                escaping = fanned('escaping')
                escaping['transitions'] = [t for t in escaping['transitions'] if t['id'] != 't-arrive-image'] + [
                    {'id': 't-arrive-image', 'from': 'assign_image', 'port': 'done', 'to': 'handle'}]
                joins = save_refused(wrong_join, 'unsupported_configuration:join_inputs:')
                escapes = save_refused(escaping, 'unsupported_configuration:branch_escapes_join:')
                observed['fanout_save'] = {'nine': nine['answer'].get('codes'), 'eight': eight,
                                           'joins': joins['answer'].get('codes'), 'escapes': escapes['answer'].get('codes')}
                check('fanout/bounded-at-save', lambda: nine['named'] and nine['nothing'] and eight == []
                      and WF.FAN_OUT_CEILING == 8 and joins['named'] and joins['nothing']
                      and escapes['named'] and escapes['nothing'])

            # AC2 and AC3 on the actual LangGraph runtime.
            with region('check/one-branch', 'check/field-unsupplied', 'check/forged-branch', 'check/observations',
                        'fanout/dispatched-together', 'fanout/join-waits-for-all', 'fanout/budget-whole-superstep',
                        'fanout/actual-langgraph'):
                tight = fanned('fanned-tight', 4)
                tight['budget'] = {'steps': 3}
                saved = {name: attempt(workflows.save, {'definition': body}, principal='owner', base=0)
                         for name, body in (('fanned', fanned()), ('fanned-tight', tight))}
                gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(work))
                stage = base / 'graph-stage'
                cycles = CY.Cycles(S, writer, workflows, gate=gate, principal='cycle-runner', signer='cycle-runner',
                                   sign=sign, stage=stage, observe=events.append)
                started = time.monotonic()
                runs = {}
                for cycle, unit in (('check-many', 'VELDO-9701'), ('check-risky', 'VELDO-9702'),
                                    ('check-other', 'VELDO-9703'), ('check-missing', 'VELDO-9704'),
                                    ('check-wrong-type', 'VELDO-9705')):
                    runs[cycle] = attempt(cycles.start, cycle, workflow='routed', subject=unit, snapshot=snapshot)
                records = {cycle: cycles.record(cycle) or {} for cycle in runs}

                def waiting_at(record, node):
                    return record.get('state') == 'waiting' and (record.get('waiting') or {}).get('node') == node

                def decided(record):
                    return (record.get('decisions') or [{}])[-1]

                expected = {'check-many': ('wait_many', 'many'), 'check-risky': ('wait_risky', 'risky'),
                            'check-other': ('wait_other', 'otherwise')}
                offered = {cycle: waiting_at(records[cycle], node)
                           and [e for e in records[cycle].get('trace') or [] if e[0] == 'route'] == [['route', port, node]]
                           and decided(records[cycle]).get('branch') == port and decided(records[cycle]).get('rule') == port
                           for cycle, (node, port) in expected.items()}
                many = decided(records['check-many'])
                risky = decided(records['check-risky'])
                other = decided(records['check-other'])
                observed['check_cycles'] = {cycle: {k: r.get(k) for k in ('state', 'trace', 'refusal', 'waiting', 'decisions')}
                                            for cycle, r in records.items()}
                check('check/one-branch',
                      lambda: all(offered.values())
                      and many.get('conditions') == [{'rule': 'many', 'field': 'files', 'comparison': 'more than',
                                                      'value': 20, 'observed': 25, 'holds': True}]
                      and [c['rule'] for c in risky['conditions']] == ['many', 'risky', 'risky']
                      and [c['holds'] for c in risky['conditions']] == [False, True, True]
                      and [c['rule'] for c in other['conditions']] == ['many', 'risky', 'risky']
                      and other['rule'] == 'otherwise' and not any(c['holds'] and c['rule'] == 'risky' and
                                                                   c['field'] == 'risk' for c in other['conditions'])
                      and all(decided(records[c]).get('node') == 'route' for c in expected))
                missing, wrong = records['check-missing'], records['check-wrong-type']
                check('check/field-unsupplied',
                      lambda: all(r.get('state') == 'refused' and r.get('refusal') == 'invalid_input:field_unsupplied:files'
                                  and not [e for e in r.get('trace') or [] if e[0] == 'route'] and not r.get('decisions')
                                  for r in (missing, wrong)))
                # A runner that names a branch the rule does not match: the risky rule always holds.
                genuine = CY.runner_source

                def forged(revision):
                    source = genuine(revision)
                    marker = 'VELDO_HOLDS = all'
                    return source.replace(marker, 'VELDO_HOLDS = (lambda found: True) or all', 1) \
                        if source.count(marker) == 1 else source + '\n# unforged\n'

                CY.runner_source = forged
                try:
                    runs['check-forged'] = attempt(cycles.start, 'check-forged', workflow='routed', subject='VELDO-9706',
                                                   snapshot=snapshot)
                finally:
                    CY.runner_source = genuine
                forged_record = cycles.record('check-forged') or {}
                check('check/forged-branch',
                      lambda: forged_record.get('state') == 'refused'
                      and forged_record.get('refusal') == 'unsupported_workflow:branch_mismatch'
                      and not [e for e in forged_record.get('trace') or [] if e[0] == 'route']
                      and cycles.metrics.get('branch_mismatch') == 1)
                check_events = [e for e in events if e.get('schema') == CY.SCHEMA and e.get('operation') == 'check'
                                and e.get('outcome') == 'accepted']
                text = json.dumps(check_events, sort_keys=True)
                check('check/observations',
                      lambda: len(check_events) == 3
                      and all(e.get('workflow', {}).get('digest') and e.get('node') == 'route' and e.get('branch')
                              and e.get('rule') and e.get('conditions') for e in check_events)
                      and all(('observed_digest' in c and 'observed' not in c) if c['field'] == 'risk'
                              else ('observed' in c) for e in check_events for c in e['conditions'])
                      and '"high"' not in text.replace('"value": ["high", "critical"]', '')
                      and cycles.metrics.get('checks', {}).get('route', {}) == {'many': 1, 'risky': 1}
                      and cycles.metrics.get('otherwise', {}).get('route') == 1)

                # Two assignment branches: both dispatched before either result returns, then run in one
                # superstep; the join waits for both and runs once.
                together = attempt(cycles.start, 'fan-together', workflow='fanned', subject='VELDO-9707', snapshot=snapshot)
                together_waiting = cycles.record('fan-together') or {}
                for name in ('copy', 'image'):
                    put('proof-bundle:9707-' + name, 'proof_bundle', dict(unit='VELDO-9707', domain=DOMAIN, part=name,
                                                                         repository=REPOSITORY, source={'commit': commit}))
                together_done = attempt(cycles.advance, 'fan-together', {'worker_result': {
                    'assign_copy': 'proof-bundle:9707-copy', 'assign_image': 'proof-bundle:9707-image'}})
                together_record = cycles.record('fan-together') or {}
                # One at a time: with one result in, the join has not run.
                one = attempt(cycles.start, 'fan-one', workflow='fanned', subject='VELDO-9708', snapshot=snapshot)
                for name in ('copy', 'image'):
                    put('proof-bundle:9708-' + name, 'proof_bundle', dict(unit='VELDO-9708', domain=DOMAIN, part=name,
                                                                         repository=REPOSITORY, source={'commit': commit}))
                first_in = attempt(cycles.advance, 'fan-one', {'worker_result': {'assign_copy': 'proof-bundle:9708-copy'}})
                one_waiting = cycles.record('fan-one') or {}
                second_in = attempt(cycles.advance, 'fan-one', {'worker_result': {'assign_image': 'proof-bundle:9708-image'}})
                one_record = cycles.record('fan-one') or {}
                cycle_seconds = time.monotonic() - started

                def branches(record):
                    return ((record.get('block') or {}).get('branches')) or {}

                branch_events = [e for e in events if e.get('schema') == CY.SCHEMA and e.get('cycle') == 'fan-together'
                                 and e.get('operation') == 'branch_step' and e.get('outcome') == 'accepted']
                supersteps = {e.get('branch'): e.get('superstep') for e in branch_events}
                joins = lambda record: [e for e in record.get('trace') or [] if e[0] == 'meet']  # noqa: E731
                observed['fan_cycles'] = {
                    'saved': saved, 'answers': {k: v.get('refused') for k, v in dict(
                        together=together, together_done=together_done, one=one, first_in=first_in,
                        second_in=second_in).items()},
                    'together_waiting': {k: together_waiting.get(k) for k in ('state', 'waiting', 'block', 'trace')},
                    'together': {k: together_record.get(k) for k in ('state', 'trace', 'refusal', 'steps', 'proposals')},
                    'one_waiting': {k: one_waiting.get(k) for k in ('state', 'waiting', 'block', 'trace', 'refusal')},
                    'one': {k: one_record.get(k) for k in ('state', 'trace', 'refusal', 'steps')},
                    'supersteps': supersteps, 'seconds': round(cycle_seconds, 2)}
                dispatched = branches(together_waiting)
                check('fanout/dispatched-together',
                      lambda: together_waiting.get('state') == 'waiting'
                      and sorted(dispatched) == ['copy', 'image']
                      and all((b.get('assignment') or {}).get('node') == 'assign_' + n and b.get('waiting') == 'worker_result'
                              for n, b in dispatched.items())
                      and together_record.get('state') == 'proposed'
                      and sorted(supersteps) == ['copy', 'image'] and len(set(supersteps.values())) == 1
                      and None not in supersteps.values()
                      and len(joins(together_record)) == 1
                      and together_record.get('steps') == 5
                      and len({entity('proof-bundle:9707-' + n)['digest'] for n in ('copy', 'image')}) == 2
                      and {entity('proof-bundle:9707-' + n)['digest'] for n in ('copy', 'image')}
                      <= set((together_record.get('proposals') or [{}])[0].get('evidence') or [])
                      and cycles.metrics.get('fan_outs', {}).get(2) == 2)
                parked = branches(one_waiting)
                check('fanout/join-waits-for-all',
                      lambda: one_waiting.get('state') == 'waiting' and not joins(one_waiting)
                      and (parked.get('copy') or {}).get('arrived') is True
                      and (parked.get('image') or {}).get('arrived') is False
                      and (parked.get('image') or {}).get('waiting') == 'worker_result'
                      and one_record.get('state') == 'proposed' and len(joins(one_record)) == 1
                      and [e[0] for e in one_record.get('trace') or []].count('meet') == 1)
                # A budget of 3 and a 4-wide fan-out after one step: the superstep would take the cycle to 5, so it
                # is refused by the budget's own name before any branch runs, never after it has run past.
                tight_start = attempt(cycles.start, 'fan-tight', workflow='fanned-tight', subject='VELDO-9709',
                                      snapshot=snapshot)
                tight_waiting = cycles.record('fan-tight') or {}
                tight_names = ['copy', 'image', 'extra0', 'extra1']
                for name in tight_names:
                    put('proof-bundle:9709-' + name, 'proof_bundle', dict(unit='VELDO-9709', domain=DOMAIN, part=name,
                                                                         repository=REPOSITORY, source={'commit': commit}))
                tight_in = attempt(cycles.advance, 'fan-tight', {'worker_result': {
                    'assign_' + n: 'proof-bundle:9709-' + n for n in tight_names}})
                tight_record = cycles.record('fan-tight') or {}
                tight_branch_events = [e for e in events if e.get('schema') == CY.SCHEMA and e.get('cycle') == 'fan-tight'
                                       and e.get('operation') in ('branch_step', 'superstep')]
                observed['fan_tight'] = {'saved': saved.get('fanned-tight'), 'start': tight_start.get('refused'),
                                         'advance': tight_in.get('refused'),
                                         'waiting': {k: tight_waiting.get(k) for k in ('state', 'steps', 'trace')},
                                         'record': {k: tight_record.get(k) for k in ('state', 'steps', 'trace', 'refusal')},
                                         'branch_events': len(tight_branch_events)}
                check('fanout/budget-whole-superstep',
                      lambda: (saved['fanned-tight'].get('ok') or {}).get('version') == 1
                      and tight_waiting.get('state') == 'waiting' and tight_waiting.get('steps') == 1
                      and tight_record.get('state') == 'refused'
                      and tight_record.get('refusal') == 'budget_exceeded:steps'
                      and tight_record.get('steps') == 1
                      and not [e for e in tight_record.get('trace') or [] if e[0].startswith('assign_')]
                      and tight_branch_events == [])
                evidence = json.dumps(load('v247_graph', mods / 'control_graph.py').runtime_evidence(), sort_keys=True)
                labels = {json.dumps(e.get('runtime'), sort_keys=True) for e in events
                          if e.get('schema') == CY.SCHEMA and e.get('cycle') in ('fan-together', 'fan-one', 'check-many')
                          and e.get('operation') in ('step', 'branch_step', 'propose') and e.get('outcome') == 'accepted'}
                check('fanout/actual-langgraph', lambda: labels == {evidence} and '"langgraph"' in evidence)
        finally:
            for conn in connections:
                with contextlib.suppress(Exception):
                    conn.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V247_OBSERVED'] = observed


_v247_suite()
