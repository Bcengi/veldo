"""VELDO-0132: versioned workflow definitions stored as immutable revisions, loaded without executing,
and executed by the actual LangGraph runtime one exact revision per cycle, every step through the
ordinary checks.

Only shared ROOT and expect are consumed. One temporary tree holds an installed .veldo copy that the
workflow service, the cycle service, the eligibility Gate, the VELDO-0035 snapshot service, the
VELDO-0043 adapter, the VELDO-0045 activation and the runner all load; the three production anchors
below are the registered mutation driver's seam, so a mutation of any of them reaches every reader,
including the child process that saves and loads under an audit hook. The store is the real SQLite
authority with OpenSSH journal signatures; the snapshot is a real accepted VELDO-0035 snapshot of a
real Git commit; the graph is the locked LangGraph installed for this account, staged into a
temporary directory so the account's stage is never touched. When that runtime is absent the cycles
are refused unavailable_service and every cycle row fails by name; the suite never installs.

The role and tool configuration records, admissions, blockers and the proof bundle a worker's result
stands for are fixture records written with the store's generic command; their own services are
VELDO-0127, VELDO-0022 and VELDO-0050, which this suite does not re-prove.
"""


def _v132_suite():
    import contextlib
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_workflow.py': ROOT / ".veldo" / "control_workflow.py",
        'control_workflow_cycle.py': ROOT / ".veldo" / "control_workflow_cycle.py",
        'control_workflow_langgraph.py': ROOT / ".veldo" / "control_workflow_langgraph.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def canon(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

    def sha(body):
        return 'sha256:' + hashlib.sha256(body).hexdigest()

    observed = {}
    emitted, raised, regions = set(), [], []

    def check(label, condition):
        """A row. `condition` may be a predicate: an exception while judging a malformed answer is a
        failed condition, recorded, never a raise."""
        emitted.add(label)
        if callable(condition):
            try:
                condition = condition()
            except Exception as error:  # noqa: BLE001
                observed.setdefault('condition_errors', []).append((label, repr(error)))
                condition = False
        expect('VELDO-0132 ' + label, bool(condition))

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

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v132-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        shutil.copytree(ROOT / '.veldo' / 'runtime', mods / 'runtime')
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v132_store', mods / 'control_store.py')
        EL = load('v132_eligibility', mods / 'control_eligibility.py')
        RS = load('v132_readset', mods / 'control_readset.py')
        SIG = load('v132_signer', mods / 'control_signer.py')
        _git_process = load('v132_git', mods / 'git_process.py')
        WF = load('v132_workflow', mods / 'control_workflow.py')
        CY = load('v132_cycle', mods / 'control_workflow_cycle.py')
        DOMAIN, REPOSITORY = 'domain-132', 'repository-132'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'journal', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        # The workspace: a real Git repository holding the units' specifications, the Gate's workspace
        # and the accepted revision the snapshot reads.
        work = base / 'work'
        (work / 'specs').mkdir(parents=True)
        UNITS = ['VELDO-96%02d' % n for n in range(1, 10)]
        for sid in UNITS:
            (work / 'specs' / (sid + '-workflow-fixture.md')).write_text('\n'.join([
                '---', 'schema: veldo.spec/v1', 'id: ' + sid, 'title: Workflow fixture unit', 'status: ready',
                'risk: standard', 'owner: dmitry', 'human_approval: not_required', 'lane: standalone',
                'protected_paths: []', '---', '', '## Intent', '', 'Workflow fixture.', '']))
        (work / 'README').write_text('workflow fixture\n')

        def git(*args):
            return _git_process.run(['git', '-C', str(work), *args], check=True, capture_output=True, text=True,
                                    identity=('Owner', 'owner@example.invalid')).stdout.strip()

        _git_process.run(['git', 'init', '-q', str(work)], check=True, capture_output=True)
        git('add', '-A')
        git('commit', '-q', '-m', 'Workflow fixture repository')
        commit = git('rev-parse', 'HEAD')
        spec_bytes = {p.name: p.read_bytes() for p in (work / 'specs').glob('*.md')}

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        snapshots_conn = S.open_store(str(db))
        reader = S.open_store(str(db), mode='r')
        connections = [writer, snapshots_conn, reader]
        serial, fixture_commands, fixture_state = [0], set(), {}

        def entity(identity, conn=None):
            row = (conn or writer).execute('SELECT kind, version, digest, data FROM entities WHERE id=?',
                                           (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            command_id = 'setup-%d' % serial[0]
            fixture_commands.add(command_id)
            S.execute(writer, dict(command_id=command_id, principal='owner', operation='upsert_entity', nonce=command_id,
                                   artifact_digests=[], expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)
            row = entity(identity)
            fixture_state[identity] = (row['kind'], row['version'], row['digest'])
            return row

        def ref(identity):
            row = entity(identity)
            return {'id': identity, 'version': row['version'], 'digest': row['digest']}

        def member(principal, kind, **extra):
            put(principal, 'membership', dict(dict(principal_type=kind, roles=[], scope=[REPOSITORY], revoked_at=None,
                                                   expires_at=None), **extra))

        member('owner', 'person', roles=['project_owner'])
        member('architect', 'person', roles=['technical_authority'])
        member('reader-person', 'person')
        member('agent-editor', 'agent_run', roles=['project_owner'])
        member('elsewhere-owner', 'person', roles=['project_owner'], scope=['another-repository'])
        member('former-owner', 'person', roles=['project_owner'], revoked_at=1.0)
        member('cycle-runner', 'service')
        member('builder-agent', 'agent_run')
        member('intruder', 'service')
        put('role-builder', 'role_configuration', dict(role='builder', principal='builder-agent'))
        put('role-intruder', 'role_configuration', dict(role='intruder', principal='intruder'))
        put('tools-default', 'tool_configuration', dict(tools=['Read', 'Edit']))
        put('project:p1', 'project', dict(name='workflow'))
        for sid in UNITS:
            put(sid, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + sid,
                                            project='p1', scope_digest='sha256:scope-' + sid, revision=1, depends_on=[],
                                            risk='standard'))
            put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))

        def admit(sid, state='accepted'):
            put('admission:' + sid, 'admission', dict(unit=sid, state=state, scope_digest='sha256:scope-' + sid))

        for sid in ('VELDO-9602', 'VELDO-9604', 'VELDO-9605', 'VELDO-9607'):
            admit(sid)
        for sid in ('VELDO-9606', 'VELDO-9608'):
            admit(sid, 'declined')
        put('blocker-9604', 'blocker', dict(unit='VELDO-9604', reason='fixture blocker'))

        # A real accepted VELDO-0035 snapshot of the workspace commit, on its own connection.
        revisions = RS.attach_revisions(S, snapshots_conn, DOMAIN, {REPOSITORY: str(work)})
        revisions.accept('revision-132', REPOSITORY, commit, 'owner', documents={'README': sha((work / 'README').read_bytes())},
                         statuses={}, signer='owner', sign=sign, authority_generation=1)
        readsets = RS.attach(S, snapshots_conn, work, DOMAIN, REPOSITORY)
        readsets.enable('upsert_entity', {'revision': 'revision-132', 'entities': {'unit': '$unit'}, 'collections': {}})
        readsets.execute({'command_id': 'snapshot-132', 'principal': 'owner', 'operation': 'accept_snapshot',
                          'parameters': {'snapshot_id': 'snapshot-132', 'operation': 'upsert_entity',
                                         'arguments': {'unit': 'VELDO-9601'}},
                          'expected_versions': {'snapshot-132': 0}, 'artifact_digests': [], 'nonce': 'snapshot-132'},
                         signer='owner', sign=sign, authority_generation=1)
        fixture_commands.add('snapshot-132')
        snapshot = ref('snapshot-132')

        def definition(workflow='delivery', role='builder', review=False, budget=12, decline_max=3):
            nodes = {'groom': {'kind': 'grooming', 'config': {}}, 'owner': {'kind': 'owner_wait', 'config': {}},
                     'assign': {'kind': 'assignment', 'config': {'role': role, 'tools': ['default']}},
                     'handle': {'kind': 'result_handling', 'config': {}}}
            transitions = [{'id': 't-groomed', 'from': 'groom', 'port': 'groomed', 'to': 'owner'},
                           {'id': 't-admit', 'from': 'owner', 'port': 'admit', 'to': 'review' if review else 'assign'},
                           {'id': 't-decline', 'from': 'owner', 'port': 'decline', 'to': 'groom', 'max': decline_max},
                           {'id': 't-done', 'from': 'assign', 'port': 'done', 'to': 'handle'}]
            if review:
                nodes['review'] = {'kind': 'grooming', 'config': {}}
                transitions.append({'id': 't-reviewed', 'from': 'review', 'port': 'groomed', 'to': 'assign'})
            return {'schema': 'veldo.workflow/v1', 'id': workflow, 'entry': 'groom', 'terminal': ['handle'],
                    'nodes': nodes, 'transitions': transitions,
                    'references': {'roles': {role: ref('role-' + role)}, 'tools': {'default': ref('tools-default')}},
                    'budget': {'steps': budget}}

        events = []
        workflows = WF.Workflows(S, writer, domain=DOMAIN, repository=REPOSITORY, signer='workflow-service', sign=sign,
                                 observe=events.append)

        def journal_seq():
            return writer.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        def attempt(call, *args, **kwargs):
            try:
                return {'ok': call(*args, **kwargs)}
            except Exception as error:  # noqa: BLE001 - recorded as the answer, never raised
                return {'refused': getattr(error, 'code', type(error).__name__),
                        'codes': list(getattr(error, 'codes', None) or [])}

        def ok(answer):
            value = answer.get('ok') if isinstance(answer, dict) else None
            return value if isinstance(value, dict) else {}

        try:
            # AC1: every problem of the schema's fields refused by name through the save interface.
            with region('workflow/validation'):
                good = definition('probe')
                bad = {}

                def case(name, mutate, layout=None):
                    body = json.loads(json.dumps(good))
                    mutate(body)
                    bad[name] = (body, layout)

                def edge(to=None, source=None):
                    def change(d):
                        d['transitions'][0] = dict(d['transitions'][0], **({'to': to} if to else {'from': source}))
                    return change

                case('dangling_edge', edge(to='ghost'))
                case('dangling_source', edge(source='ghost'))
                case('unknown_step_kind', lambda d: d['nodes']['groom'].update(kind='shell'))
                case('invalid_config', lambda d: d['nodes']['groom'].update(config={'shell': 'make build'}))
                case('unknown_port', lambda d: d['transitions'][0].update(port='finished'))
                case('missing_transition', lambda d: d['transitions'].pop(3))
                case('duplicate_transition', lambda d: d['transitions'].append(dict(d['transitions'][0], id='t-again')))
                case('missing_reference', lambda d: d['nodes']['assign']['config'].update(role='reviewer'))
                case('unresolved_reference', lambda d: d['references']['roles']['builder'].update(id='role-absent'))
                case('stale_reference', lambda d: d['references']['roles']['builder'].update(digest='sha256:' + 'a' * 64))
                case('wrong_kind_reference', lambda d: d['references']['roles'].update(builder=ref('tools-default')))
                case('unused_reference', lambda d: d['references']['tools'].update(spare=ref('tools-default')))
                case('unbounded_cycle', lambda d: d['transitions'][2].pop('max'))
                case('invalid_bound', lambda d: d['transitions'][2].update(max=0))
                case('unreachable_node', lambda d: d['nodes'].update(orphan={'kind': 'grooming', 'config': {}}))
                case('terminal_mismatch', lambda d: d.update(terminal=['owner']))
                case('unknown_entry', lambda d: d.update(entry='start'))
                case('reserved_node', lambda d: d['nodes'].update(veldo_intake=d['nodes'].pop('groom')))
                case('invalid_budget', lambda d: d.update(budget={'steps': 65}))
                case('schema', lambda d: d.update(schema='veldo.workflow/v0'))
                case('unknown_field', lambda d: d.update(script='print(1)'))
                case('not_plain', lambda d: d['budget'].update(steps=4.5))
                case('layout_names_no_node', lambda d: None, layout={'nodes': {'ghost': {'x': 1, 'y': 2}}})
                expected = {
                    'dangling_edge': 'unsupported_configuration:dangling_edge:t-groomed',
                    'dangling_source': 'unsupported_configuration:dangling_edge:t-groomed',
                    'unknown_step_kind': 'unsupported_configuration:unknown_step_kind:groom',
                    'invalid_config': 'unsupported_configuration:invalid_config:groom',
                    'unknown_port': 'unsupported_configuration:unknown_port:t-groomed',
                    'missing_transition': 'unsupported_configuration:missing_transition:assign.done',
                    'duplicate_transition': 'unsupported_configuration:duplicate_transition:t-again',
                    'missing_reference': 'unsupported_configuration:missing_reference:assign:roles/reviewer',
                    'unresolved_reference': 'unsupported_configuration:missing_reference:roles/builder',
                    'stale_reference': 'unsupported_configuration:missing_reference:roles/builder',
                    'wrong_kind_reference': 'unsupported_configuration:missing_reference:roles/builder',
                    'unused_reference': 'unsupported_configuration:unused_reference:tools/spare',
                    'unbounded_cycle': 'unsupported_configuration:unbounded_cycle:',
                    'invalid_bound': 'unsupported_configuration:invalid_bound:t-decline',
                    'unreachable_node': 'unsupported_configuration:unreachable_node:orphan',
                    'terminal_mismatch': 'unsupported_configuration:terminal_mismatch:handle',
                    'unknown_entry': 'unsupported_configuration:unknown_entry:start',
                    'reserved_node': 'unsupported_configuration:reserved_or_invalid_node_id:veldo_intake',
                    'invalid_budget': 'unsupported_configuration:invalid_budget',
                    'schema': 'unsupported_configuration:schema:',
                    'unknown_field': 'invalid_input:definition has unknown field script',
                    'not_plain': 'invalid_input:definition.budget.steps is not an allowed number',
                    'layout_names_no_node': 'invalid_input:layout.nodes.ghost names no node',
                }
                seq_before = journal_seq()
                results = {}
                for name, (body, layout) in sorted(bad.items()):
                    document = {'definition': body} if layout is None else {'definition': body, 'layout': layout}
                    results[name] = attempt(workflows.save, document, principal='owner', base=0)
                named = {name: any(code.startswith(expected[name]) for code in (r.get('codes') or [r.get('refused') or '']))
                         for name, r in results.items()}
                unchanged = journal_seq() == seq_before and WF.head_version(writer, DOMAIN, REPOSITORY, 'probe') == 0
                valid = WF.definition_problems(definition()) == [] and set(bad) == set(expected)
                observed['validation'] = {'results': results, 'named': named}
                check('workflow/validation', lambda: valid and all(named.values()) and unchanged
                      and all(WF.taxonomy(r['refused']) == 'unsupported_configuration' for r in results.values()))

            # AC1: only an authorized editor saves, and nothing is written for anyone else.
            with region('workflow/authorized-editor'):
                seq_before = journal_seq()
                who = {'unknown': 'nobody', 'no_role': 'reader-person', 'agent': 'agent-editor',
                       'other_scope': 'elsewhere-owner', 'revoked': 'former-owner'}
                refused = {k: attempt(workflows.save, {'definition': definition('guarded')}, principal=p, base=0)
                           for k, p in who.items()}
                wanted = {'unknown': 'unauthenticated:editor', 'no_role': 'missing_authority:editor',
                          'agent': 'missing_authority:editor', 'other_scope': 'missing_authority:editor',
                          'revoked': 'missing_authority:editor'}
                nothing = journal_seq() == seq_before and WF.head_version(writer, DOMAIN, REPOSITORY, 'guarded') == 0
                architect = attempt(workflows.save, {'definition': definition('reviewed')}, principal='architect', base=0)
                observed['editors'] = {'refused': refused, 'architect': architect}
                check('workflow/authorized-editor', lambda: nothing and all(refused[k].get('refused') == wanted[k] for k in who)
                      and ok(architect).get('version') == 1)

            # AC1 and AC3: new revisions keep every earlier byte; the canvas document round-trips with its
            # layout separated from the execution identity.
            with region('workflow/revisions-immutable', 'workflow/canvas-round-trip'):
                layout1 = {'nodes': {'groom': {'x': 1234.5625, 'y': -3}, 'owner': {'x': 180, 'y': 40.25}},
                           'transitions': {'t-groomed': {'points': [[60.5, 10], [120, 22.75]]}},
                           'viewport': {'x': -20.5, 'y': 4, 'zoom': 1.375}}
                document1 = {'definition': definition('canvas'), 'layout': layout1}
                first = ok(attempt(workflows.save, document1, principal='owner', base=0))
                row1 = entity(first.get('revision', '-'))
                loaded1 = ok(attempt(workflows.load, 'canvas', 1))
                layout2 = dict(layout1, viewport={'x': 4321.0625, 'y': -8.5, 'zoom': 0.5})
                second = ok(attempt(workflows.save, {'definition': definition('canvas'), 'layout': layout2},
                                    principal='owner', base=1))
                stale = attempt(workflows.save, {'definition': definition('canvas', budget=10)}, principal='owner', base=1)
                overwrite = attempt(S.execute, writer, dict(
                    command_id='overwrite-1', principal='owner', operation='upsert_entity', nonce='overwrite-1',
                    artifact_digests=[], expected_versions={first.get('revision', '-'): 1},
                    parameters=dict(entity_id=first.get('revision', '-'), kind='workflow_revision',
                                    data=dict((row1 or {}).get('data') or {}, definition=definition('canvas', budget=3)))),
                    'owner', sign, 1)
                again = entity(first.get('revision', '-'))
                reloaded1, loaded2 = ok(attempt(workflows.load, 'canvas', 1)), ok(attempt(workflows.load, 'canvas'))
                listed = attempt(workflows.history, 'canvas').get('ok')
                versions = [h.get('version') for h in listed] if isinstance(listed, list) else None
                check('workflow/revisions-immutable',
                      lambda: first.get('version') == 1 and second.get('version') == 2 and row1 is not None and again == row1
                      and reloaded1 and canon(reloaded1) == canon(loaded1)
                      and stale.get('refused') == 'stale_version' and overwrite.get('refused') == 'entity_owned'
                      and versions == [1, 2]
                      and loaded2.get('previous') == {'version': 1, 'revision': first.get('revision'),
                                                      'digest': sha(canon(row1['data']))}
                      and WF.head_version(writer, DOMAIN, REPOSITORY, 'canvas') == 2)
                # The layout is canvas metadata only: the layout-only edit is a new revision with the same
                # definition digest, and neither runner carries any layout.
                source1 = attempt(CY.runner_source, loaded1).get('ok') or ''
                source2 = attempt(CY.runner_source, loaded2).get('ok') or ''
                text = canon(document1['definition']).decode()
                registration = 'veldo_register_workflow(%r, %d)' % (text, 1)
                observed['canvas'] = {'first': first, 'second': second, 'stale': stale, 'overwrite': overwrite}
                check('workflow/canvas-round-trip',
                      lambda: bool(loaded1) and canon(loaded1.get('definition')) == canon(document1['definition'])
                      and canon(loaded1.get('layout')) == canon(layout1)
                      and loaded1.get('definition_digest') == sha(canon(document1['definition'])) == first.get('definition_digest')
                      and loaded1.get('layout_digest') == sha(canon(layout1))
                      and second.get('definition_digest') == first.get('definition_digest')
                      and second.get('layout_digest') != first.get('layout_digest')
                      and canon(loaded2.get('layout')) == canon(layout2)
                      and source1.count(registration) == 1
                      and source2.replace('%r, %d)' % (text, 2), '%r, %d)' % (text, 1)) == source1
                      and not any(token in source1 + source2 for token in ('viewport', '4321.0625', '1234.5625', '22.75')))

            # AC3: saving an edge and loading run nothing: an audited child process with an in-process signer.
            with region('workflow/edit-without-execution'):
                edited = definition('canvas')
                edited['nodes']['refine'] = {'kind': 'grooming', 'config': {}}
                edited['transitions'][0] = dict(edited['transitions'][0], to='refine')
                edited['transitions'].append({'id': 't-refined', 'from': 'refine', 'port': 'groomed', 'to': 'owner'})
                child = r'''
import hashlib, importlib.util, json, os, sys
mods, db, domain, repository = sys.argv[1:5]
LAUNCH = ('subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn', 'os.spawn', 'os.fork', 'os.forkpty', 'pty.spawn')
NETWORK = ('socket.connect', 'socket.getaddrinfo', 'socket.gethostbyname', 'socket.sendto', 'socket.sendmsg', 'socket.bind')
launches, network = [], []
def audit(event, args):
    if event in LAUNCH:
        launches.append(event)
    elif event in NETWORK:
        network.append(event)
sys.addaudithook(audit)
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
S = load('child_store', os.path.join(mods, 'control_store.py'))
WF = load('child_workflow', os.path.join(mods, 'control_workflow.py'))
edit = json.loads(sys.stdin.read())
conn = S.open_store(db)
signed = []
def sign(body):
    signed.append(len(body))
    return 'in-process:' + hashlib.sha256(body).hexdigest()
service = WF.Workflows(S, conn, domain=domain, repository=repository, signer='editor-session', sign=sign)
saved = service.save(edit['document'], principal='owner', base=edit['base'])
loaded = service.load(edit['workflow'])
history = service.history(edit['workflow'])
files = sorted({os.path.basename(getattr(m, '__file__', None) or '') for m in list(sys.modules.values())} - {''})
print(json.dumps({'saved': saved, 'loaded': loaded, 'history': history, 'launches': launches, 'network': network,
                  'files': files, 'signed': len(signed)}))
'''
                tables = ('reservations', 'effects')
                counts_before = {t: writer.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] for t in tables}
                seq_before = journal_seq()
                proc = subprocess.run([sys.executable, '-B', '-c', child, str(mods), str(db), DOMAIN, REPOSITORY],
                                      input=json.dumps({'document': {'definition': edited}, 'base': 2, 'workflow': 'canvas'}),
                                      capture_output=True, text=True, timeout=60)
                result = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else {'failed': proc.stderr[-600:]}
                records = writer.execute('SELECT command_id, transition FROM journal WHERE seq > ? ORDER BY seq',
                                         (seq_before,)).fetchall()
                kinds = {change['kind'] for _, transition in records for change in json.loads(transition).values()}
                forbidden = {'control_graph.py', 'control_graph_langgraph.py', 'control_workflow_cycle.py',
                             'control_workflow_langgraph.py', 'control_runtime.py', 'control_graph_install.py',
                             'control_dispatch.py', 'control_launch.py', 'dispatch.py', 'executor.py'}
                observed['edit'] = {'result': {k: result.get(k) for k in ('launches', 'network', 'files', 'signed', 'failed')},
                                    'records': [r[0] for r in records], 'kinds': sorted(kinds)}
                check('workflow/edit-without-execution',
                      lambda: 'failed' not in result and result['launches'] == [] and result['network'] == []
                      and not forbidden & set(result['files']) and result['signed'] == 1
                      and result['saved']['version'] == 3 and canon(result['loaded']['definition']) == canon(edited)
                      and [h['version'] for h in result['history']] == [1, 2, 3]
                      and len(records) == 1 and records[0][0].startswith('workflow/save/')
                      and kinds == {'workflow_revision', 'workflow_head'}
                      and {t: writer.execute('SELECT COUNT(*) FROM ' + t).fetchone()[0] for t in tables} == counts_before)

            # AC2 and AC4: cycles on the actual LangGraph runtime.
            with region('workflow/pinned-revision', 'workflow/actual-langgraph', 'workflow/ordinary-authorization',
                        'workflow/no-workflow-authority', 'workflow/observations'):
                non_workflow_before = {r[0]: (r[1], r[2], r[3]) for r in writer.execute(
                    "SELECT id, kind, version, digest FROM entities WHERE kind NOT IN "
                    "('workflow_revision', 'workflow_head', 'workflow_cycle')")}
                seq_cycles = journal_seq()
                saves = {name: attempt(workflows.save, {'definition': body}, principal='owner', base=0) for name, body in {
                    'delivery': definition(), 'intruding': definition('intruding', role='intruder'),
                    'tight': definition('tight', budget=4),
                    'asserting': {'schema': 'veldo.workflow/v1', 'id': 'asserting', 'entry': 'groom',
                                  'terminal': ['handle'], 'references': {}, 'budget': {'steps': 6},
                                  'nodes': {'groom': {'kind': 'grooming', 'config': {}},
                                            'handle': {'kind': 'result_handling', 'config': {}}},
                                  'transitions': [{'id': 't-groomed', 'from': 'groom', 'port': 'groomed', 'to': 'handle'}]},
                }.items()}
                gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(work))
                stage = base / 'graph-stage'
                import pwd
                account_stage = Path(pwd.getpwuid(os.getuid()).pw_dir) / '.local/state/veldo/graph-stage'

                def account_listing():
                    return {str(p): p.lstat().st_mtime_ns for p in sorted(account_stage.rglob('*'))} \
                        if account_stage.is_dir() else {}

                account_before = account_listing()
                cycles = CY.Cycles(S, writer, workflows, gate=gate, principal='cycle-runner', signer='cycle-runner',
                                   sign=sign, stage=stage, observe=events.append)
                started = time.monotonic()
                # Cycle A binds delivery 1 and waits for the owner; delivery 2 is saved while it waits.
                a1 = attempt(cycles.start, 'cycle-a', workflow='delivery', subject='VELDO-9601', snapshot=snapshot)
                v2 = attempt(workflows.save, {'definition': definition(review=True)}, principal='owner', base=1)
                admit('VELDO-9601')
                a2 = attempt(cycles.advance, 'cycle-a')
                put('proof-bundle:9601', 'proof_bundle', dict(unit='VELDO-9601', domain=DOMAIN, repository=REPOSITORY,
                                                              source={'commit': commit}))
                a3 = attempt(cycles.advance, 'cycle-a', {'worker_result': 'proof-bundle:9601'})
                # Cycle B starts after the edit: it binds delivery 2.
                b1 = attempt(cycles.start, 'cycle-b', workflow='delivery', subject='VELDO-9602', snapshot=snapshot)
                # Cycle C waits for its owner and is canceled through the graph.
                c1 = attempt(cycles.start, 'cycle-c', workflow='delivery', subject='VELDO-9603', snapshot=snapshot)
                c2 = attempt(cycles.cancel, 'cycle-c')
                # AC4: the ordinary checks, each after the actual graph ran.
                refusals = {
                    'blocked_unit': attempt(cycles.start, 'cycle-blocked', workflow='delivery', subject='VELDO-9604',
                                            snapshot=snapshot),
                    'unauthorized_role': attempt(cycles.start, 'cycle-intruder', workflow='intruding',
                                                 subject='VELDO-9605', snapshot=snapshot),
                    'cycle_budget': attempt(cycles.start, 'cycle-tight', workflow='tight', subject='VELDO-9606',
                                            snapshot=snapshot),
                    'asserted_completion': attempt(cycles.start, 'cycle-asserting', workflow='asserting',
                                                   subject='VELDO-9607', snapshot=snapshot),
                    'loop_bound': attempt(cycles.start, 'cycle-loop', workflow='delivery', subject='VELDO-9608',
                                          snapshot=snapshot),
                }
                cycle_seconds = time.monotonic() - started
                records = {name: cycles.record(name) or {} for name in (
                    'cycle-a', 'cycle-b', 'cycle-c', 'cycle-blocked', 'cycle-intruder', 'cycle-tight', 'cycle-asserting',
                    'cycle-loop')}
                steps = [e for e in events if e.get('schema') == CY.SCHEMA and e.get('operation') in ('step', 'propose', 'cancel')
                         and e.get('outcome') == 'accepted']

                def executed(cycle):
                    return [e.get('executed') for e in steps if e['cycle'] == cycle and e['operation'] == 'step']

                def labels(cycle):
                    return {json.dumps(e.get('runtime'), sort_keys=True) for e in steps if e['cycle'] == cycle}

                evidence = json.dumps(load('v132_graph', mods / 'control_graph.py').runtime_evidence(), sort_keys=True)
                stored1, stored2 = ok(attempt(workflows.load, 'delivery', 1)), ok(attempt(workflows.load, 'delivery', 2))

                def within(record, stored):
                    # Every step of the trace is a transition of the stored revision; a proposal only at a terminal.
                    edges = {(t['from'], t['port'], t['to']) for t in stored['definition']['transitions']}
                    trace = record.get('trace') or []
                    return bool(trace) and all(tuple(e) in edges or (e[1] == 'proposed' and e[0] in stored['definition']['terminal'])
                                               for e in trace)

                ident1 = {'id': 'delivery', 'version': 1, 'digest': stored1.get('definition_digest')}
                ident2 = {'id': 'delivery', 'version': 2, 'digest': stored2.get('definition_digest')}
                ra, rb = records['cycle-a'], records['cycle-b']
                nodes1 = (stored1.get('definition') or {}).get('nodes') or {}
                kinds_a = {nodes1[e[0]].get('kind') for e in ra.get('trace') or [] if e[0] in nodes1}
                observed['cycles'] = {'records': {k: {f: v.get(f) for f in ('state', 'trace', 'refusal', 'binding', 'steps',
                                                                             'proposals', 'waiting')}
                                                  for k, v in records.items()},
                                      'answers': {k: {'refused': v.get('refused')} for k, v in
                                                  dict(a1=a1, a2=a2, a3=a3, b1=b1, c1=c1, c2=c2, v2=v2, **refusals).items()},
                                      'seconds': round(cycle_seconds, 2)}
                check('workflow/pinned-revision',
                      lambda: (v2.get('ok') or {}).get('version') == 2
                      and ra.get('binding') == dict(ident1, revision=stored1.get('revision'), entity_digest=stored1.get('entity_digest'))
                      and ra.get('state') == 'proposed' and within(ra, stored1)
                      and [e[0] for e in ra['trace']] == ['groom', 'owner', 'assign', 'handle']
                      and kinds_a == {'grooming', 'owner_wait', 'assignment', 'result_handling'}
                      and executed('cycle-a') and all(x == ident1 for x in executed('cycle-a'))
                      and rb.get('binding', {}).get('version') == 2 and within(rb, stored2)
                      and 'review' in [e[0] for e in rb.get('trace') or []]
                      and executed('cycle-b') and all(x == ident2 for x in executed('cycle-b'))
                      and rb.get('state') == 'waiting' and (rb.get('waiting') or {}).get('input') == 'worker_result'
                      and ra['proposals'] and ra['proposals'][0]['subject'] == 'VELDO-9601'
                      and entity('proof-bundle:9601')['digest'] in ra['proposals'][0]['evidence'])
                # Every exchange ran the actual locked LangGraph, from the bound revision's own staged runner.
                staged = sorted((stage / 'runners').glob('*.py')) if (stage / 'runners').is_dir() else []
                staged_text = [p.read_text() for p in staged]
                texts = {canon(ok(attempt(workflows.load, w, v)).get('definition')).decode(): (w, v) for w, v in (
                    ('delivery', 1), ('delivery', 2), ('intruding', 1), ('tight', 1), ('asserting', 1))}
                registered = [[(w, v) for t, (w, v) in texts.items() if 'veldo_register_workflow(%r, %d)' % (t, v) in s]
                              for s in staged_text]
                production = (mods / 'control_graph_langgraph.py').read_text().split("\nif __name__ == '__main__':\n")[0]
                rc = records['cycle-c']
                check('workflow/actual-langgraph',
                      lambda: all(labels(c) == {evidence} for c in ('cycle-a', 'cycle-b', 'cycle-c'))
                      and staged and all(s.startswith(production) for s in staged_text)
                      and all(len(r) == 1 for r in registered)
                      and {r[0] for r in registered} == set(texts.values())
                      and rc.get('state') == 'canceled'
                      and any(e['operation'] == 'cancel' and e['cycle'] == 'cycle-c' and e.get('runtime') for e in steps)
                      and account_listing() == account_before)
                wanted = {'blocked_unit': ('cycle-blocked', 'blocked:blocker-9604'),
                          'unauthorized_role': ('cycle-intruder', 'missing_authority:role/intruder'),
                          'cycle_budget': ('cycle-tight', 'budget_exceeded:steps'),
                          'asserted_completion': ('cycle-asserting', 'missing_evidence:completion'),
                          'loop_bound': ('cycle-loop', 'budget_exceeded:loop/t-decline')}
                ran = {name: bool(labels(cycle) - {'null'}) and labels(cycle) <= {evidence} and len(executed(cycle)) >= 2
                       for name, (cycle, _) in wanted.items()}
                named = {name: records[cycle].get('state') == 'refused' and records[cycle].get('refusal') == code
                         and not records[cycle].get('proposals') and not records[cycle].get('waiting')
                         for name, (cycle, code) in wanted.items()}
                observed['authorization'] = {'ran': ran, 'named': named}

                def status_now():
                    return cycles.status()
                check('workflow/ordinary-authorization',
                      lambda: all(ran.values()) and all(named.values())
                      and records['cycle-intruder'].get('assignment') is None
                      and records['cycle-blocked'].get('assignment') is None
                      and records['cycle-tight'].get('steps') == 4
                      and not [p for p in status_now()['pending'] if p['cycle'] in {c for c, _ in wanted.values()}])
                # No workflow authority: every domain record is what the suite itself wrote, every journal
                # record the cycles and saves wrote is a workflow record, no unit completed or shipped.
                non_workflow_after = {r[0]: (r[1], r[2], r[3]) for r in writer.execute(
                    "SELECT id, kind, version, digest FROM entities WHERE kind NOT IN "
                    "('workflow_revision', 'workflow_head', 'workflow_cycle')")}
                expected_after = dict(non_workflow_before, **{k: v for k, v in fixture_state.items()})
                foreign = []
                for command_id, transition in writer.execute('SELECT command_id, transition FROM journal WHERE seq > ?',
                                                             (seq_cycles,)):
                    if command_id in fixture_commands:
                        continue
                    for change in json.loads(transition).values():
                        if change['kind'] not in ('workflow_cycle', 'workflow_revision', 'workflow_head'):
                            foreign.append((command_id, change['kind']))
                completion = {sid: gate.completion(sid) for sid in UNITS}
                specs_now = {p.name: p.read_bytes() for p in (work / 'specs').glob('*.md')}
                observed['authority'] = {'foreign': foreign, 'spec_changed': sorted(n for n in specs_now
                                                                                    if specs_now[n] != spec_bytes.get(n))}
                check('workflow/no-workflow-authority',
                      lambda: ra.get('state') == 'proposed' and not foreign and non_workflow_after == expected_after
                      and all(not any(v.values()) for v in completion.values())
                      and all(entity(sid)['data']['state'] == 'READY' for sid in UNITS)
                      and specs_now == spec_bytes and git('rev-parse', 'HEAD') == commit
                      and git('status', '--porcelain') == ''
                      and writer.execute('SELECT COUNT(*) FROM reservations').fetchone()[0] == 0
                      and writer.execute('SELECT COUNT(*) FROM effects').fetchone()[0] == 0)
                # Observations: every operation reported with its identities and taxonomy class; the counts and
                # the pending work are what the store holds.
                status = ok(attempt(cycles.status))
                refused_events = [e for e in events if e.get('outcome') == 'refused']
                classes = {'unauthenticated', 'unauthorized', 'stale_version', 'unsupported_configuration',
                           'unavailable_service', 'missing_evidence', 'unknown_outcome'}
                fields = ('operation', 'domain', 'repository', 'workflow', 'outcome')
                cycle_events = [e for e in events if e.get('schema') == CY.SCHEMA]
                text = json.dumps(events, default=str)
                observed['observations'] = {'status': status, 'events': len(events), 'refused': len(refused_events)}
                check('workflow/observations',
                      lambda: events and all(all(k in e for k in fields) for e in events)
                      and all(e.get('taxonomy') in classes and e.get('refusal') for e in refused_events)
                      and all(e.get('actor') for e in events if e['operation'] in ('save', 'start', 'step', 'wait'))
                      and {e['operation'] for e in cycle_events} >= {'start', 'step', 'wait', 'propose', 'refuse', 'cancel'}
                      and status['accepted'] == sum(1 for e in cycle_events if e['outcome'] == 'accepted')
                      and status['refused'] == sum(1 for e in cycle_events if e['outcome'] == 'refused')
                      and status['pending'] == [{'cycle': 'cycle-b', 'subject': 'VELDO-9602', 'node': 'assign',
                                                 'input': 'worker_result', 'workflow': 'delivery', 'version': 2}]
                      and workflows.counts['refused'] == sum(1 for e in events if e.get('schema') == WF.REVISION_SCHEMA
                                                             and e['outcome'] == 'refused')
                      and 'PRIVATE KEY' not in text and str(private) not in text)
        finally:
            for conn in connections:
                with contextlib.suppress(Exception):
                    conn.close()
        # One row per region saying it ran to its end: a driven mutation must red its named row by a
        # failed assertion while that row's own region still completes.
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V132_OBSERVED'] = observed


_v132_started = __import__('time').monotonic()
_v132_suite()
_V132_SECONDS = __import__('time').monotonic() - _v132_started
