"""VELDO-0262: Veldo runs workflow steps on its own step runner and the LangGraph runtime is removed.

Run: python3 scripts/selftest.py --suite 130_veldo_0262_step_runner

Only shared ROOT and expect are consumed. The production modules are read through the literal anchors in
PRODUCTION (the registered mutation driver substitutes each copy there) and laid into one temporary .veldo,
so a mutation of any of them reaches every row that uses it.

  replay/corpus        AC1: every exchange of proof/VELDO-0262/corpus (recorded on the LangGraph runner before
                       it was removed) replayed on the step runner gives the same answer in canonical JSON,
                       the runtime label aside; a difference names the first exchange and field
  replay/twice         AC1: two replays give identical bytes
  runner/plain         AC1: the runner reads no clock, randomness, thread or environment, keeps no global
                       statement, and its label comes from its declared VERSION, read statically
  fanout/superstep     AC2: two assignment branches run in one superstep and carry one superstep number
  fanout/join-waits-for-all  AC2: with one result in the join has not run; with both it runs once
  fanout/branch-isolation    AC2: a branch that mutates its view leaves its sibling's view unchanged
  fanout/permuted      AC2: the same superstep with the branch names permuted gives identical answer bytes
  fanout/nine-refused  AC2: a resume of nine branches is invalid_input
  leftover/repository  AC3: no retired file under .veldo, engine or packs, no import of langgraph, langchain or
                       langsmith in any Python file outside proof/ and specs/, no lock, records or install path
                       naming them; RESTORED (the falsifier's seam) lays retired files over the tree
  leftover/setup       AC3: a scaffold over a tree holding a retired file refuses leftover_runtime naming it,
                       before writing anything; --upgrade retires it and the scaffold passes
  leftover/upgrade-link  AC3: the upgrade removes a digest-named runtime directory, nothing through a link
                       named by a digest, and the scaffold then refuses leftover_runtime naming the link
  launch/stdlib-only   AC4: the adapter launches the staged runner with -I -S -B, and under those flags the
                       child's importtime shows only standard library modules
  observe/exchange     every exchange observation carries the staged runner's sha256, exit and elapsed ms
"""


def _v262_suite():
    import contextlib
    import hashlib
    import importlib.util
    import io
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
        'control_graph.py': ROOT / ".veldo" / "control_graph.py",
        'control_graph_steps.py': ROOT / ".veldo" / "control_graph_steps.py",
        'control_workflow_steps.py': ROOT / ".veldo" / "control_workflow_steps.py",
        'control_graph_pm.py': ROOT / ".veldo" / "control_graph_pm.py",
        'control_runtime.py': ROOT / ".veldo" / "control_runtime.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
        'control_workflow_cycle.py': ROOT / "engine/.veldo" / "control_workflow_cycle.py",
    }
    # The falsifier's seam for the leftover row: repository paths laid over the tree as if restored.
    RESTORED = ()
    ROWS = ('replay/corpus', 'replay/twice', 'runner/plain', 'fanout/superstep', 'fanout/join-waits-for-all',
            'fanout/branch-isolation', 'fanout/permuted', 'fanout/nine-refused', 'leftover/repository',
            'leftover/setup', 'leftover/upgrade-link', 'launch/stdlib-only', 'observe/exchange')
    rows = {name: [] for name in ROWS}
    started = time.monotonic()

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'))

    def sha(text):
        return 'sha256:' + hashlib.sha256(text.encode()).hexdigest()

    def run(name, body):
        try:
            body()
        except Exception as error:  # noqa: BLE001
            check(name, 'ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:300]), False)

    with tempfile.TemporaryDirectory(prefix='v262-') as directory:
        top = Path(directory)
        tree = top / 'tree'
        (tree / '.veldo').mkdir(parents=True)
        for name in ('control_graph.py', 'control_graph_steps.py', 'control_workflow_steps.py', 'control_graph_pm.py',
                     'control_runtime.py', 'init_scaffold.py'):
            shutil.copyfile(PRODUCTION[name], tree / '.veldo' / name)
        shutil.copyfile(ROOT / '.veldo' / 'git_process.py', tree / '.veldo' / 'git_process.py')
        corpus = load('v262_corpus', ROOT / 'proof/VELDO-0262/corpus.py')
        graph = load('v262_graph', tree / '.veldo' / 'control_graph.py')
        runner = tree / '.veldo' / 'control_graph_steps.py'

        def replay():
            text, first = corpus.replay(tree, python=graph.base_interpreter(), flags=graph.FLAGS)
            count = text.count('\n') + 1 if text else 0
            check('replay/corpus', 'every recorded exchange answered identically, label aside (%d exchanges; first '
                  'difference %s)' % (count, json.dumps(first)), first is None and count >= 2000)
            again, _ = corpus.replay(tree, python=graph.base_interpreter(), flags=graph.FLAGS)
            check('replay/twice', 'two replays give identical bytes (%s, %s)'
                  % (hashlib.sha256(text.encode()).hexdigest()[:12], hashlib.sha256(again.encode()).hexdigest()[:12]),
                  text == again and bool(text))
        run('replay/corpus', replay)

        def plain():
            import ast
            source = runner.read_text()
            parsed = ast.parse(source)
            imported = sorted({alias.name.split('.')[0] for node in ast.walk(parsed) if isinstance(node, ast.Import)
                               for alias in node.names} | {node.module.split('.')[0] for node in ast.walk(parsed)
                                                           if isinstance(node, ast.ImportFrom) and node.module})
            check('runner/plain', 'imports only copy, json, math and sys %s' % imported,
                  imported == ['copy', 'json', 'math', 'sys'])
            check('runner/plain', 'no global statement', not any(isinstance(n, (ast.Global, ast.Nonlocal))
                                                                 for n in ast.walk(parsed)))
            code = source.replace(ast.get_docstring(parsed, clean=False) or '', '')
            check('runner/plain', 'no environment, clock, randomness or thread read',
                  not any(word in code for word in ('os.environ', 'time.', 'random', 'threading', 'getenv')))
            version = graph.declared_version(runner)
            hostile = top / 'hostile_runner.py'
            hostile.write_text('raise SystemExit("imported")\nVERSION = %r\n' % version)
            check('runner/plain', 'the label is read statically from the declared VERSION %r' % version,
                  graph.runtime_evidence() == {'name': 'veldo-steps', 'version': version}
                  and graph.declared_version(hostile) == version)
        run('runner/plain', plain)

        # A fan-out of two assignment branches into one join, through the production splice.
        definition = {'id': 'fan-two', 'entry': 'g', 'fields': {}, 'nodes': {
            'g': {'kind': 'grooming', 'config': {}}, 'left': {'kind': 'assignment', 'config': {}},
            'right': {'kind': 'assignment', 'config': {}}, 'j': {'kind': 'join', 'config': {'inputs': ['tl', 'tr']}},
            'done': {'kind': 'result_handling', 'config': {}}}, 'transitions': [
            {'id': 'tl', 'from': 'g', 'port': 'groomed', 'to': 'left'},
            {'id': 'tr', 'from': 'g', 'port': 'groomed', 'to': 'right'},
            {'id': 'ul', 'from': 'left', 'port': 'done', 'to': 'j'},
            {'id': 'ur', 'from': 'right', 'port': 'done', 'to': 'j'},
            {'id': 'v', 'from': 'j', 'port': 'done', 'to': 'done'}]}
        text = canonical(definition)
        guard = "\nif __name__ == '__main__':\n"
        revision_runner = top / 'fan_runner.py'
        revision_runner.write_text(runner.read_text().replace(guard, '\n' + (tree / '.veldo/control_workflow_steps.py')
                                                              .read_text() + '\nVELDO_DEFINITION = (%r, 1)\n' % text + guard, 1))
        probe_runner = top / 'probe_runner.py'
        probe_runner.write_text(runner.read_text().replace(guard, '\n' + r'''
def _i_fan(view):
    return {'next': {'a': 'ma', 'b': 'mb'}, 'suspend': True, 'notes': {'join': 'j', 'shared': 'kept'}}


def _i_mutate(view):
    view['notes']['shared'] = 'written by a'
    view['supplied_results'].append({'id': 'planted'})
    view['snapshot']['id'] = 'changed by a'
    return {'next': 'j', 'suspend': True, 'notes': {'last': ['ma', 'done', 'j']}}


def _i_observe(view):
    seen = [view['notes'].get('shared'), len(view['supplied_results']), view['snapshot']['id']]
    return {'next': 'j', 'suspend': True, 'notes': {'last': ['mb', 'done', 'j', seen]}}


def _i_join(view):
    return {'next': None, 'proposals': [{'type': 'priority', 'proposal_id': 'p', 'subject': 'u', 'priority': 1}]}


WORKFLOWS['isolation'] = {'version': 1, 'entry': 'f', 'nodes': {'f': _i_fan, 'ma': _i_mutate, 'mb': _i_observe,
                                                                'j': _i_join}}
''' + guard, 1))
        workflow = {'id': 'fan-two', 'version': 1, 'digest': sha(text)}
        snapshot = {'id': 'snapshot-1', 'version': 1, 'digest': sha('snapshot-1')}
        stage = top / 'stage'

        def adapter(path):
            return graph.Adapter({'python': graph.base_interpreter(), 'runner': str(path), 'stage': str(stage)},
                                 'v262-domain', 'v262-repository', evidence=graph.runtime_evidence())

        def result(identifier, value):
            return {'id': identifier, 'version': 1, 'digest': sha(identifier), 'value': value}

        subject = result('subject', {'unit': 'unit-1', 'state': 'ready'})
        fan = {}

        def fanout():
            lane = adapter(revision_runner)
            first = lane.start('fan', 'fan.1', snapshot, workflow)
            groomed = lane.advance('fan', 'fan.2', snapshot, workflow, first['resume'], [subject])
            fan['parallel'] = groomed['resume']
            both = lane.advance('fan', 'fan.3', snapshot, workflow, groomed['resume'],
                                [subject, result('worker_result@left', {'kind': 'proof_bundle'}),
                                 result('worker_result@right', {'kind': 'proof_bundle'})])
            entries = json.loads(both['resume']['notes'])['branches']
            check('fanout/superstep', 'both branches moved in one exchange with one superstep number %s'
                  % {b: (e.get('position'), e.get('superstep')) for b, e in entries.items()},
                  groomed['resume']['position'] == 'veldo_parallel' and both['resume']['position'] == 'veldo_parallel'
                  and {e.get('position') for e in entries.values()} == {'j'}
                  and len({e.get('superstep') for e in entries.values()}) == 1
                  and both['resume']['step'] == groomed['resume']['step'] + 2)
            one = lane.advance('fan', 'fan.4', snapshot, workflow, groomed['resume'],
                               [subject, result('worker_result@left', {'kind': 'proof_bundle'})])
            held = json.loads(one['resume']['notes'])
            check('fanout/join-waits-for-all', 'with one result in the join has not run and the cycle stays suspended '
                  '%s' % {b: e.get('position') for b, e in held['branches'].items()},
                  one['outcome'] == 'suspended' and one['resume']['position'] == 'veldo_parallel'
                  and sorted(e['position'] for e in held['branches'].values()) == ['j', 'right']
                  and 'joined' not in held)
            waiting = lane.advance('fan', 'fan.4b', snapshot, workflow, one['resume'], [subject])
            still = json.loads(waiting['resume']['notes']) if waiting.get('resume') else {}
            check('fanout/join-waits-for-all', 'with the second result still out the join does not run [%s at %s]'
                  % (waiting['outcome'], (waiting.get('resume') or {}).get('position')),
                  waiting['outcome'] == 'suspended' and waiting['resume']['position'] == 'veldo_parallel'
                  and sorted(e['position'] for e in still.get('branches', {}).values()) == ['j', 'right']
                  and 'joined' not in still)
            joined = lane.advance('fan', 'fan.5', snapshot, workflow, both['resume'], [subject])
            notes = json.loads(joined['resume']['notes']) if joined.get('resume') else {}
            check('fanout/join-waits-for-all', 'with both in the join runs once [%s at %s]'
                  % (joined['outcome'], (joined.get('resume') or {}).get('position')),
                  joined['outcome'] == 'suspended' and joined['resume']['position'] == 'done'
                  and notes.get('joined') == ['tl', 'tr'] and notes.get('last') == ['j', 'done', 'done']
                  and joined['resume']['step'] == both['resume']['step'] + 1)
        run('fanout/superstep', fanout)

        def isolation():
            lane = adapter(probe_runner)
            reference = {'id': 'isolation', 'version': 1, 'digest': sha('isolation')}
            first = lane.start('iso', 'iso.1', snapshot, reference)
            after = lane.advance('iso', 'iso.2', snapshot, reference, first['resume'], [subject])
            entries = json.loads(after['resume']['notes'])['branches']
            seen = (entries.get('b') or {}).get('last', [None] * 4)[3]
            check('fanout/branch-isolation', 'the sibling saw the pre-superstep view %s' % seen,
                  seen == ['kept', 1, 'snapshot-1'] and entries['a']['position'] == 'j')
        run('fanout/branch-isolation', isolation)

        def permuted():
            notes = json.loads(fan['parallel']['notes'])
            reordered = dict(notes, branches=dict(reversed(list(notes['branches'].items()))))
            given = [subject, result('worker_result@right', {'kind': 'proof_bundle'})]
            answers = []
            for value in (notes, reordered):
                resume = dict(fan['parallel'], notes=json.dumps(value))
                sent = graph.request('advance', {'cycle_id': 'perm', 'command_id': 'perm.1', 'domain_uuid': 'd',
                                                 'repository_uuid': 'r'}, snapshot=snapshot, workflow=workflow,
                                     resume=resume, supplied_results=given)
                runtime = {'python': graph.base_interpreter(), 'runner': str(revision_runner), 'stage': str(stage)}
                answers.append(canonical(graph.exchange(runtime, sent)))
            check('fanout/permuted', 'the same superstep with the branch names permuted gives identical answer bytes',
                  answers[0] == answers[1] and '"outcome":"suspended"' in answers[0])
            nine = dict(notes, branches={'b%d' % i: {'position': 'left', 'last': None} for i in range(9)})
            lane = adapter(revision_runner)
            refused = lane.advance('nine', 'nine.1', snapshot, workflow, dict(fan['parallel'], notes=json.dumps(nine)),
                                   [subject])
            check('fanout/nine-refused', 'a resume of nine branches is invalid_input %s' % refused.get('failure'),
                  refused['outcome'] == 'failure' and refused['failure']['code'] == 'invalid_input')
        run('fanout/permuted', permuted)

        def observe():
            lane = adapter(revision_runner)
            lane.start('obs', 'obs.1', snapshot, workflow)
            item = lane.observations[-1]
            staged = hashlib.sha256(revision_runner.read_bytes()).hexdigest()
            check('observe/exchange', 'the observation carries the staged runner digest, exit and elapsed ms %s'
                  % {k: item.get(k) for k in ('runner_sha256', 'exit', 'elapsed_ms')},
                  item.get('runner_sha256') == staged and item.get('exit') == 0
                  and type(item.get('elapsed_ms')) is float and item['elapsed_ms'] > 0
                  and graph.exchange_durations(lane.observations).get('start/suspended', {}).get('count') == 1)
        run('observe/exchange', observe)

        scaffold = load('v262_scaffold', tree / '.veldo' / 'init_scaffold.py')

        def leftover_repository():
            found = []
            listed = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout
            names = [n for n in listed.decode().split('\0') if n]
            overlay = top / 'overlay'
            for rel in RESTORED:
                (overlay / rel).parent.mkdir(parents=True, exist_ok=True)
                (overlay / rel).write_text('# restored\n')
            names += [rel for rel in RESTORED if rel not in names]
            retired = {Path(rel).name for rel in scaffold.RETIRED_FILES}
            for rel in names:
                path = (overlay / rel) if rel in RESTORED else ROOT / rel
                top_dir = rel.split('/', 1)[0]
                if top_dir in ('.veldo', 'engine', 'packs') and Path(rel).name in retired:
                    found.append('retired file ' + rel)
                if top_dir in ('proof', 'specs') or rel.startswith('docs/design/'):
                    continue
                lowered = Path(rel).name.lower()
                if any(word in lowered for word in scaffold.RETIRED_PACKAGES) and not rel.endswith('.md'):
                    found.append('lock, records or install path ' + rel)
                if rel.endswith('.py') and path.is_file():
                    for production, copy in PRODUCTION.items():
                        if rel in ('.veldo/' + production, 'engine/.veldo/' + production) and Path(copy) != ROOT / rel:
                            path = Path(copy)
                    imported = scaffold.retired_imports(path.read_text(errors='replace'))
                    if imported:
                        found.append('import of %s in %s' % (', '.join(imported), rel))
            check('leftover/repository', 'nothing of the removed runtime remains outside history %s' % found[:6],
                  not found and len(names) > 1000)
            target = top / 'leftover-target'
            for rel in RESTORED:
                if rel.split('/', 1)[0] == 'engine':
                    laid = target / rel.split('/', 1)[1]
                    laid.parent.mkdir(parents=True, exist_ok=True)
                    laid.write_text('# restored\n')
            if RESTORED:
                try:
                    scaffold.scaffold(target, templates=ROOT / 'engine')
                    refused = None
                except scaffold.ScaffoldError as error:
                    refused = str(error)
                laid = ['leftover_runtime:' + rel.split('/', 1)[1] for rel in RESTORED if rel.startswith('engine/')]
                check('leftover/repository', 'a scaffold of the restored tree refuses leftover_runtime naming it [%s]'
                      % refused, refused is not None and all(name in refused for name in laid))
        run('leftover/repository', leftover_repository)

        def leftover_setup():
            target = top / 'setup-target'
            (target / '.veldo').mkdir(parents=True)
            (target / '.veldo/control_graph_lock.py').write_text('PACKAGES = ()\n')
            (target / '.veldo/stray.py').write_text('def f():\n    import langgraph.graph\n')
            before = sorted(str(p.relative_to(target)) for p in target.rglob('*'))
            try:
                scaffold.scaffold(target, templates=ROOT / 'engine')
                refused = ''
            except scaffold.ScaffoldError as error:
                refused = str(error)
            after = sorted(str(p.relative_to(target)) for p in target.rglob('*'))
            check('leftover/setup', 'refused naming each leftover before writing anything [%s]' % refused,
                  'leftover_runtime:.veldo/control_graph_lock.py' in refused
                  and 'leftover_runtime:.veldo/stray.py' in refused and before == after)
            (target / '.veldo/stray.py').unlink()
            home = top / 'setup-home'
            home.mkdir()
            log = io.StringIO()
            with contextlib.redirect_stderr(log):
                scaffold.scaffold(target, templates=ROOT / 'engine', home=home, upgrade=True)
            check('leftover/setup', 'the upgrade retires the file, logs it, and the scaffold passes [%s]'
                  % log.getvalue().strip()[:200],
                  not (target / '.veldo/control_graph_lock.py').exists() and (target / '.veldo/control_graph.py').is_file()
                  and 'retired .veldo/control_graph_lock.py' in log.getvalue())
        run('leftover/setup', leftover_setup)

        def upgrade_link():
            home = top / 'link-home'
            runtime = home / '.local/share/veldo/langgraph'
            plain_dir, link = runtime / ('a' * 64), runtime / ('b' * 64)
            (plain_dir / 'bin').mkdir(parents=True)
            (plain_dir / 'bin/python').write_text('')
            victim = top / 'victim'
            victim.mkdir()
            (victim / 'keep').write_text('kept')
            link.symlink_to(victim, target_is_directory=True)
            target = top / 'link-target'
            log = io.StringIO()
            try:
                with contextlib.redirect_stderr(log):
                    scaffold.scaffold(target, templates=ROOT / 'engine', home=home, upgrade=True)
                refused = ''
            except scaffold.ScaffoldError as error:
                refused = str(error)
            check('leftover/upgrade-link', 'the digest directory removed, nothing through the link, and the scaffold '
                  'refuses naming the link [%s] [%s]' % (refused, log.getvalue().strip()[:300]),
                  not plain_dir.exists() and link.is_symlink() and (victim / 'keep').read_text() == 'kept'
                  and refused == 'leftover_runtime:' + str(link) and not target.exists()
                  and ('retired runtime directory ' + str(plain_dir)) in log.getvalue()
                  and ('refused ' + str(link) + ': a link') in log.getvalue())
        run('leftover/upgrade-link', upgrade_link)

        def launch():
            import ast
            source = (tree / '.veldo/control_graph.py').read_text()
            parsed = ast.parse(source)
            flags = next((ast.literal_eval(n.value) for n in parsed.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == 'FLAGS' for t in n.targets)), None)
            check('launch/stdlib-only', 'the adapter launches the staged runner with -I -S -B %s' % (flags,),
                  flags == ('-I', '-S', '-B') and tuple(graph.FLAGS) == flags
                  and "subprocess.Popen([runtime['python'], *FLAGS, str(staged)]," in source)
            request = {'schema': 'veldo.graph/v1', 'operation': 'start', 'cycle_id': 'c', 'command_id': 'c.1',
                       'domain_uuid': 'd', 'repository_uuid': 'r', 'snapshot': snapshot, 'workflow': workflow}
            work = top / 'importtime'
            work.mkdir()
            proc = subprocess.run([graph.base_interpreter(), *graph.FLAGS, '-X', 'importtime', str(revision_runner)],
                                  input=json.dumps(request).encode(), capture_output=True, cwd=str(work),
                                  env=dict(graph.ENVIRONMENT), timeout=120)
            modules = [line.rsplit('|', 1)[1].strip() for line in proc.stderr.decode().splitlines()
                       if line.startswith('import time:') and '|' in line and 'self [us]' not in line]
            foreign = sorted({m.split('.')[0] for m in modules} - set(sys.stdlib_module_names))
            check('launch/stdlib-only', 'under those flags the child imports only the standard library (%d modules, '
                  'outside it: %s)' % (len(modules), foreign), proc.returncode == 0 and modules and not foreign
                  and b'"outcome": "suspended"' in proc.stdout)
        run('launch/stdlib-only', launch)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        for label, one in observed:
            if not one or os.environ.get('VELDO_0262_DETAILS'):
                print('  VELDO-0262 %s %s: %s' % (name, 'detail' if not one else 'observed', label))
        if not observed:
            print('  VELDO-0262 %s detail: no check ran' % name)
        failed = next((label for label, one in observed if not one), 'no check ran' if not observed else '')
        expect('VELDO-0262 ' + name + (': ' + failed if failed else ''), ok)
    print('VELDO-0262 suite seconds: %.3f' % (time.monotonic() - started))


_v262_suite()
