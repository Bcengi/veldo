"""Authority common entry for VELDO-0367. Children receive decisions, never Store credentials.

The only activation switch is gate_changes.SELECTION_ENABLED. A full selection is
handed to weekly admission before executing any check. Node outputs are authenticated
under a per-run nonce; neither an old observation nor a candidate-written file settles it.
"""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
MODULES = {}


def module(name):
    if name not in MODULES:
        path = HERE / (name + '.py')
        spec = importlib.util.spec_from_file_location('execution_' + name, path)
        obj = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(obj)
        MODULES[name] = obj
    return MODULES[name]


def catalog(source):
    """Read the authority's literal declarations, without sourcing executable shell."""
    C = module('gate_changes')
    declarations = dict(re.findall(r'^CHECK_(\w+)="([^"\n]*)"$', source, re.M))
    order = re.search(r'^ORDER="(.*?)"', source, re.M | re.S)
    C.require(order is not None, 'missing catalog order')
    names = order[1].replace('\\\n', ' ').split()
    C.require(len(set(names)) == len(names) and set(names) == set(declarations), 'catalog slot inventory')
    for value in declarations.values():
        C.require(value.startswith(('required:', 'na:', 'waived:')) and value.partition(':')[2].strip(),
                  'undeclared catalog item')
        C.require('$' not in value and '`' not in value, 'nonliteral catalog command')
    return {name: declarations[name] for name in names}


def builtins():
    # These are the three mandatory judging checks after the legacy catalog.
    return {'secret_scan': "if grep -rInE '(api[_-]?key|secret|password|token)[[:space:]]*[:=][[:space:]]*[\"\x27][A-Za-z0-9+/_-]{16,}' --include='*' --exclude-dir={.git,node_modules,venv,.venv,dist,build,proof} --exclude={verify.sh,veldo-guard.sh} . 2>/dev/null | grep -v '\\.veldo/examples/'; then exit 1; fi",
            'contracts': 'python3 .veldo/validate.py all', 'shape': 'python3 .veldo/shape_gate.py'}


def store_for(root):
    R = module('gate_reuse')
    store = R.Store(R.E.configuration()[1]['store'], root)
    module('gate_changes').require(store.secret is not None, 'authority Store unavailable')
    return store


def source_state(root, *, clean=True):
    M = module('check_gate_mutations')
    common = os.environ.get('VELDO_EXPECTED_GIT_COMMON') or M.common_directory(HERE.parent)
    files = M.read_inputs(root, common)
    head = M.git(root, common, 'rev-parse', 'HEAD')
    module('gate_changes').require(not clean or not M.git(root, common, 'status', '--porcelain', '--untracked-files=all'),
                                  'change gate requires a clean immutable checkout')
    return common, files, head


def recheck(context):
    common, files, commit = source_state(Path(context['root']))
    C = module('gate_changes')
    C.require(commit == context['candidate_commit'] and
              module('check_gate_mutations').file_identity(files) == context['files_digest'],
              'candidate changed during common execution')


def full_plan(plan):
    return dict(plan, baseline_commit=None, baseline_record_digest=None, changed_paths=None,
                items=[dict(item, status='run', reason='weekly full execution', evidence=None)
                       if item['status'] in ('run', 'carried') else item for item in plan['items'] if item['status'] != 'removed'])


def reconcile_children(plan):
    """A new child or prerequisite cannot hide beneath a carried parent."""
    C = module('gate_changes')
    indexed = {item['item_id']: item for item in plan['items']}
    for item in list(indexed.values()):
        kind, stage, leg, *_ = json.loads(item['item_id'])
        if item['status'] != 'run':
            continue
        parents = [C.identity('stage', stage)]
        if kind in ('suite', 'case'):
            parents.append(C.identity('leg', stage, leg))
        for key in parents:
            parent = indexed.get(key)
            if parent and parent['status'] == 'carried':
                parent.update(status='run', evidence=None, reason='selected child')
    return plan


def prepare(root, store, *, weekly=False, cases=None, declarations=None, runtime=None):
    C, L, M, S = (module(name) for name in ('gate_changes', 'gate_legs', 'check_gate_mutations', 'gate_schedule'))
    common, files, commit = source_state(root)
    declarations = declarations if declarations is not None else catalog((HERE / 'verify.sh').read_text())
    today = datetime.datetime.fromtimestamp(module('gate_weekly').authority_now(), datetime.timezone.utc).date()
    for value in declarations.values():
        if value.startswith('waived:'):
            fields = value.split(':', 2)
            C.require(len(fields) == 3 and fields[2].strip() and
                      datetime.date.fromisoformat(fields[1]) >= today, 'expired or invalid waiver')
    required = {name: value.split(':', 1)[1] for name, value in declarations.items() if value.startswith('required:')}
    listing = L.load()[0] if L.DECLARATION.exists() else None
    nodes = S.required_nodes(required, listing)
    expanded = {stage: sorted({leg or 'confined' for s, leg in nodes.values() if s == stage}) for stage in required}
    manifest_path, requires_path = root / 'scripts/suites/manifest.json', root / 'scripts/suites/requires.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'suites': []}
    requires = json.loads(requires_path.read_text()) if requires_path.exists() else {'requires': {}}
    cases = cases if cases is not None else (M.inventory(root, common) if 'mutation' in required else [])
    mutation_leg = L.mutation_leg() if 'mutation' in required else None
    runtime = runtime or C.digest({'environment': {k: os.environ[k] for k in
        ('LANG', 'LC_ALL', 'LC_CTYPE', 'TZ', 'PYTHONHASHSEED', 'PYTHONUTF8') if k in os.environ}})
    configurations = {case['identity']: dict(leg=('unconfined' if mutation_leg and
        case['suite'].removesuffix('.py') in mutation_leg['suites'] and not case.get('confined_only') else 'confined'),
        runtime_digest=runtime, fixture_configuration={}) for case in cases}
    if cases:
        expanded['mutation'] = sorted({configurations[c['identity']]['leg'] for c in cases})
    drivers = {name: [] for name in M.DRIVERS}
    # The actual registries, including nonteeth driver names, are authoritative.
    if cases:
        drivers = {name: [] for name in sorted({case['driver'] for case in cases})}
    for case in cases:
        drivers[case['driver']].append(dict(case, leg=configurations[case['identity']]['leg']))
    inventory = C.build_inventory(declarations, expanded, manifest, requires, drivers,
                                  [dict(name=name, command=command) for name, command in builtins().items()])
    if listing:
        whole = {entry['suite'] for entry in listing['suites'] if 'rows' not in entry}
        listed = {entry['suite'] for entry in listing['suites']}
        definitions = []
        for definition in inventory['items']:
            kind, stage, leg, suite, *_ = json.loads(definition['item_id'])
            absent = kind == 'suite' and ((leg == 'confined' and suite in whole) or
                                         (leg == 'unconfined' and suite not in listed))
            definitions.append(dict(definition, state='not-applicable', reason='suite outside declared leg')
                               if absent else definition)
        inventory = C.inventory(definitions)
    repository = str(Path(common).resolve())
    runtimes = {item['item_id']: runtime for item in inventory['items']}
    previous = C.eligible_baseline(root, store, repository, commit)
    if previous:
        for item in previous['receipt']['items']:
            if item['status'] not in ('executed', 'carried'):
                continue
            try:
                dependency = C.item_evidence(store, item)
                key = dependency['runtime_digest']
                runtimes[item['item_id']] = (key if C.runtime_current(store, key, M.fixed_env('/nonexistent')
                    if json.loads(item['item_id'])[0] == 'case' else os.environ, HERE.parent) else None)
            except (OSError, ValueError, KeyError, TypeError):
                pass
    plan = C.select(root, store, repository, commit, inventory, runtimes)
    if weekly:
        plan = full_plan(plan)
    context = dict(root=str(root), repository=repository, candidate_commit=commit, inventory=inventory,
                   runtimes=runtimes, configurations=configurations, plan=plan, full=weekly,
                   catalog=declarations, manifest=manifest, requires=requires, expanded=expanded, verify_runtime=True)
    # Prerequisite execution is part of the authority plan, before signing it.
    if manifest['suites']:
        scope = module('run_scope')
        for stage in ('unit', 'integration'):
            for leg in expanded.get(stage, []):
                selection = scope.change_selection(root, dict(context, store=store, stage=stage, leg=leg),
                                                    manifest=manifest, requires=requires)
                for item in plan['items']:
                    coords = json.loads(item['item_id'])
                    if (coords[:3] == ['suite', stage, leg] and coords[3] in selection['running']
                            and item['status'] in ('run', 'carried')):
                        item.update(status='run', evidence=None, reason='selected suite or prerequisite')
    context['plan'] = reconcile_children(plan)
    context.update(nonce=secrets.token_hex(32), expected_common=str(common), files_digest=M.file_identity(files))
    return context


def save_context(store, context):
    C = module('gate_changes')
    record = C.sealed('veldo.change-run/v1', **dict(
        {k: v for k, v in context.items() if k not in ('schema', 'record_digest')}, owner_pid=os.getpid(),
        owner_start=module('gate_space').process_start(os.getpid()), scope=os.environ.get('VELDO_GATE_SCOPE')))
    C.require(store.change_put(record), 'common plan publication')
    return record['record_digest']


def read_context(store, key):
    C = module('gate_changes')
    value = store.get(key)
    C.require(isinstance(value, dict) and value.get('schema') == 'veldo.change-run/v1'
              and value.get('record_digest') == key and C.digest({k: v for k, v in value.items()
                  if k != 'record_digest'}) == key, 'authenticated common plan required')
    C.validate_inventory(value['inventory'])
    return value


def result_key(run, node):
    return module('gate_changes').digest(['common-node', run, node])


def publish_item(store, dependency):
    C = module('gate_changes')
    C.validate_dependency(dependency)
    result = C.sealed(C.RESULT, item_id=dependency['item_id'], source_commit=dependency['observed_commit'],
                      status='passed', complete=True, dependency_record_digest=dependency['record_digest'])
    C.require(store.change_put(dependency) and store.change_put(result), 'common item publication')
    return dict(item_id=dependency['item_id'], status='executed', dependency_record_digest=dependency['record_digest'],
                result_digest=result['record_digest'], source_commit=dependency['observed_commit'], source_gate_digest=None)


def aggregate(store, context, key, children, reason=None):
    C, O = module('gate_changes'), module('mutation_observer')
    records = []
    for child in children:
        dependency = C.item_evidence(store, child)
        records.append(C.sealed(C.DEPENDENCY, **dict({k: v for k, v in dependency.items()
            if k not in ('schema', 'record_digest')}, observed_commit=context['candidate_commit'])))
    own = O.DependencyReads(context['root'])
    own.reasons.clear()
    for name in ('verify.sh', 'gate_execution.py', 'gate_changes.py', 'gate_schedule.py', 'gate_graph.json'):
        own.read(Path(context['root']) / 'scripts' / name)
    if reason:
        own.unknown(reason)
    records.append(own.record(key, context['candidate_commit']))
    C.publish_runtime(store, own.runtime)
    runtimes = sorted({record['runtime_digest'] for record in records})
    if len(runtimes) > 1:
        C.publish_runtime(store, runtimes)
    return publish_item(store, O.combine_dependencies(records, key, context['candidate_commit']))


def node(run, name, root, directory):
    C, L = module('gate_changes'), module('gate_legs')
    store = store_for(root)
    context = read_context(store, run)
    C.require(C.SELECTION_ENABLED, 'change selection is inactive until increment 5')
    H = module('gate_host')
    C.require(context['owner_pid'] in [os.getpid(), *H.ancestors()] and
              module('gate_space').process_start(context['owner_pid']) == context['owner_start'],
              'common coordinator no longer owns this node')
    if context.get('scope'):
        current = H.own_cgroup()
        C.require(current == context['scope'] or current.startswith(context['scope'] + '/'),
                  'common node outside custody scope')
    common, files, commit = source_state(root, clean=False)
    C.require(commit == context['candidate_commit'] and
              module('check_gate_mutations').file_identity(files) == context['files_digest'],
              'node candidate differs from plan')
    context = dict(context, root=str(root), store=store)
    stage, _, leg = name.partition('.')
    indexed = {item['item_id']: item for item in context['plan']['items']}
    keys = [key for key in indexed if json.loads(key)[1] == stage and json.loads(key)[0] != 'stage'
            and (not leg or json.loads(key)[2] == leg)]
    chosen = [indexed[key] for key in keys]
    executed, carried = [], [i['evidence'] for i in chosen if i['status'] == 'carried']
    if any(i['status'] == 'run' for i in chosen):
        if stage == 'mutation':
            M = module('check_gate_mutations')
            receipt = M.run_change_stage(root, common, context, leg=L.mutation_leg(),
                                        admit=module('gate_schedule').CHANNEL in os.environ)
            C.require(receipt['status'] == 'passed', 'mutation stage failed')
            executed.extend(i for i in receipt['items'] if i['status'] == 'executed')
            for key in keys:
                if json.loads(key)[0] == 'leg' and indexed[key]['status'] == 'run':
                    children = [i for i in receipt['items'] if json.loads(i['item_id'])[2] == json.loads(key)[2]]
                    executed.append(aggregate(store, context, key, children))
        elif stage == 'load':
            parts = sorted(directory.glob('opened.unit.*.json'))
            C.require(parts or 'unit' not in context['expanded'], 'missing current unit observations for load proof')
            if parts:
                L.publish_opened(directory / 'opened_files.json', parts)
            C.require(L.run_load_proof(root, directory / 'load.record', opened=directory / 'opened_files.json') == 0,
                      'load proof failed')
            executed.extend(aggregate(store, context, i['item_id'], [], 'load native coverage unavailable')
                            for i in chosen if i['status'] == 'run')
        else:
            selection = None
            if stage in ('unit', 'integration') and context['manifest']['suites']:
                selection = module('run_scope').change_selection(root, dict(context, stage=stage, leg=leg or 'confined'),
                    manifest=context['manifest'], requires=context['requires'])
            taking = L.TakeOpened(root, directory / ('opened.' + stage + '.' + (leg or 'confined') + '.json'), stage, store=store)
            code = L.run_stage(root, stage, context['catalog'][stage].split(':', 1)[1], directory / 'legs.json',
                leg=leg or None, taking=taking, change_selection=selection)
            code = taking.finish(stage, code)
            C.require(code == 0 and taking.observation_error is None, 'stage failed or observation unavailable: ' + name)
            observations = {}
            for observation in taking.observations:
                dependency = observation['dependency']
                observations.setdefault(dependency['item_id'], []).append(dependency)
            O = module('mutation_observer')
            observations = {key: O.combine_dependencies(values, key, commit) for key, values in observations.items()}
            for item in chosen:
                if item['status'] != 'run':
                    continue
                key = item['item_id']
                coords = json.loads(key)
                if coords[0] == 'suite':
                    C.require(key in observations, 'missing executed suite observation: ' + key)
                    executed.append(publish_item(store, observations[key]))
                elif coords[0] == 'leg':
                    dependency = observations[C.identity('stage', stage)]
                    dependency = C.sealed(C.DEPENDENCY, **dict({k: v for k, v in dependency.items()
                        if k not in ('schema', 'record_digest')}, item_id=key))
                    executed.append(publish_item(store, dependency))
    C.require({i['item_id'] for i in executed} == {i['item_id'] for i in chosen if i['status'] == 'run'},
              'node execution inventory')
    C.require(module('check_gate_mutations').inputs_unchanged(root, common, files, commit), 'node inputs changed')
    payload = dict(run=run, node=name, items=[*executed, *carried])
    C.require(store.put(result_key(run, name), payload), 'node receipt publication')
    return 0


def execute(context, store, directory):
    C, S, L = (module(name) for name in ('gate_changes', 'gate_schedule', 'gate_legs'))
    root = Path(context['root'])
    for name in ('VELDO_SUITE_REUSE', 'VELDO_GATE_CACHE', 'VELDO_SUITE_ORDER'):
        os.environ.pop(name, None)
    run = save_context(store, context)
    required = {name: value.split(':', 1)[1] for name, value in context['catalog'].items() if value.startswith('required:')}
    listing = L.load()[0] if L.DECLARATION.exists() else None
    nodes = S.required_nodes(required, listing)
    if S.GRAPH.exists():
        arguments = ['--root', str(root), '--directory', str(directory), '--record', str(directory / 'legs.json'),
                     '--receipt', str(directory / 'mutation.json'), '--load-opened', str(directory / 'opened_files.json'),
                     '--change-run', run]
        for stage, command in required.items():
            arguments += ['--stage', stage, command]
        code = S.main(arguments)
        result = json.loads((directory / 'receipt.json').read_text())
        for name in nodes:
            path = directory / (name + '.log')
            if path.exists():
                print(path.read_text(), end='', flush=True)
        C.require(code == 0 and result['inputs_unchanged'] and
                  all(v == 'pass' for v in result['stages'].values()), 'graph failed')
    else:
        for name in nodes:
            node(run, name, root, directory)
    executed = {}
    seen = set()
    children = []
    for name in nodes:
        result = store.get(result_key(run, name))
        C.require(isinstance(result, dict) and result.get('run') == run and result.get('node') == name,
                  'missing authenticated node receipt: ' + name)
        children.extend(result['items'])
        for item in result['items']:
            C.require(item['item_id'] not in seen, 'duplicate node item')
            seen.add(item['item_id'])
            if item['status'] == 'executed':
                executed[item['item_id']] = item
    for item in context['plan']['items']:
        if item['status'] != 'run':
            continue
        kind, stage, *_ = json.loads(item['item_id'])
        if kind == 'stage':
            executed[item['item_id']] = aggregate(store, context, item['item_id'],
                [child for child in children if json.loads(child['item_id'])[1] == stage])
        elif kind == 'uncataloged':
            taking = L.TakeOpened(root, None, stage, store=store)
            code = L.run_stage(root, stage, builtins()[stage], directory / 'legs.json', taking=taking)
            C.require(taking.finish(stage, code) == 0 and taking.observation_error is None, 'built-in failed: ' + stage)
            dependency = taking.observations[-1]['dependency']
            dependency = C.sealed(C.DEPENDENCY, **dict({k: v for k, v in dependency.items()
                if k not in ('schema', 'record_digest')}, item_id=item['item_id']))
            executed[item['item_id']] = publish_item(store, dependency)
    return C.assemble(context['plan'], executed)


def write_outputs(root, sink, store, context, gate):
    C = module('gate_changes')
    fields = module('reuse_stamp').change_fields(root, store, gate, context['repository'])
    counts = {'unit': 0, 'mutation': 0}
    for item in gate['receipt']['items']:
        kind, stage, *_ = json.loads(item['item_id'])
        if item['status'] == 'carried' and (kind, stage) in (('suite', 'unit'), ('case', 'mutation')):
            counts[stage] += 1
    document = dict(commit=context['candidate_commit'], status='green', tree='clean', force_fresh=False,
                    validation_mode='change-scoped', reused=counts, veldo_version=None,
                    at=datetime.datetime.fromtimestamp(module('gate_weekly').authority_now(),
                        datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    checks_na=sum(v.startswith('na:') for v in context['catalog'].values()),
                    checks_run=sum(v.startswith('required:') for v in context['catalog'].values()), **fields)
    C.require(not (sink / 'events.jsonl').is_symlink(), 'event sink symlink')
    log = sink / 'events.jsonl'
    original = root / '.veldo/events.jsonl'
    if not log.exists() and original.is_file() and not original.is_symlink():
        log.write_bytes(original.read_bytes())
    try:
        module('gate_weekly').event_module().reconcile_verdicts(repo_root=root, log_path=log)
    except Exception as error:
        print('review events: PRESENT AND ERRORED; non-judging reconciliation: ' + str(error), flush=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=sink, prefix='.stamp-', delete=False) as stream:
        json.dump(document, stream, sort_keys=True)
        stream.write('\n')
    os.replace(stream.name, sink / 'last_verify')
    with (sink / 'events.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(document, schema='veldo.event/v1', type='gate.passed', producer='verify.sh'), sort_keys=True) + '\n')
    for stage, declaration in context['catalog'].items():
        if declaration.startswith('required:'):
            print('== ' + stage + '\n   ' + stage + ': pass', flush=True)
    for label in ('secret scan', 'contracts', 'shape gate'):
        print('== ' + label + ' (built-in)\n   ' + label + ': pass', flush=True)
    print('GATE: GREEN (' + context['candidate_commit'] + ')', flush=True)


class Space:
    """Keep the existing need/classify/verdict/release steps on the common path.

    The authority owns logs outside the immutable candidate. A pipe reader thread
    captures inherited child output; it starts no workload outside weekly custody.
    """
    def __init__(self, root, sink, store):
        self.root, self.sink = root, sink
        self.folder = store.directory / ('gate-space.' + secrets.token_hex(16))
        self.record, self.output = self.folder / 'record.json', self.folder / 'output.log'
        self.reader = None
        self.failed = []

    def step(self, name):
        return module('gate_space').run(name, self.root, self.record, self.output, self.sink / 'last_verify')

    def __enter__(self):
        import threading
        module('gate_changes').require(self.step('need') == 0, 'space admission unavailable')
        if self.folder.exists():
            sys.stdout.flush()
            sys.stderr.flush()
            self.saved = (os.dup(1), os.dup(2))
            read, write = os.pipe()
            log = os.open(self.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            def capture():
                try:
                    while True:
                        data = os.read(read, 65536)
                        if not data:
                            break
                        for descriptor in (self.saved[0], log):
                            remaining = data
                            try:
                                while remaining:
                                    remaining = remaining[os.write(descriptor, remaining):]
                            except OSError as error:
                                self.failed.append(str(error))
                finally:
                    os.close(read)
                    os.close(log)
            self.reader = threading.Thread(target=capture)
            self.reader.start()
            os.dup2(write, 1)
            os.dup2(write, 2)
            os.close(write)
        return self

    def finish(self):
        if self.reader is not None:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(self.saved[0], 1)
            os.dup2(self.saved[1], 2)
            self.reader.join()
            self.reader = None
            for descriptor in self.saved:
                os.close(descriptor)
        module('gate_changes').require(not self.failed, 'gate output capture failed')

    def __exit__(self, kind, error, traceback):
        try:
            if error:
                print('GATE: RED (change execution: %s)' % error, flush=True)
            self.finish()
            if error:
                module('gate_changes').require(self.step('classify') == 0, 'gate failure not judged')
        finally:
            self.step('release')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enabled', action='store_true')
    parser.add_argument('--root', type=Path)
    parser.add_argument('--sink', type=Path)
    parser.add_argument('--weekly', action='store_true')
    parser.add_argument('--weekly-execute', action='store_true')
    parser.add_argument('--run')
    parser.add_argument('--node')
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args(argv)
    C = module('gate_changes')
    if args.enabled:
        print('on' if C.SELECTION_ENABLED else 'off')
        return 0
    C.require(C.SELECTION_ENABLED, 'change selection is inactive until increment 5')
    root = (args.root or HERE.parent).resolve()
    if args.node:
        return node(args.run, args.node, root, args.directory)
    if args.weekly_execute:
        store = store_for(root)
        context = read_context(store, args.run)
        C.require(context['full'], 'weekly child needs full plan')
        H = module('gate_host')
        state = {}
        try:
            name, group = H.make_scope(H.load()['scope'], state=state)
        finally:
            C.require(store.put(context['scope_key'], state), 'weekly scope publication')
        os.environ[H.SCOPE_ENV] = group
        args.directory.mkdir(parents=True)
        receipt = execute(context, store, args.directory)
        C.require(store.put(result_key(args.run, 'complete'), dict(run=args.run, receipt=receipt)),
                  'weekly complete publication')
        return 0
    sink = args.sink.resolve() if args.sink else root / '.veldo'
    if args.sink:
        C.require(sink.is_dir() and sink != root and root not in sink.parents and os.access(sink, os.W_OK), 'invalid sink')
    C.require(not (sink / 'events.jsonl').is_symlink(), 'event sink symlink')
    store = store_for(root)
    context = prepare(root, store, weekly=args.weekly or module('mutation_reuse').truthy(os.environ.get('VELDO_GATE_FORCE_FRESH', '0')))
    required = [i for i in context['plan']['items'] if i['status'] in ('run', 'carried')]
    if context['full'] or required and all(i['status'] == 'run' for i in required):
        sink.mkdir(exist_ok=True)
        with Space(root, sink, store) as space:
            return module('gate_weekly').production(context, store, sink, space=space)
    H = module('gate_host')
    if H.CONFIG.exists() and H.inside(H.load()) is None:
        command = [str(HERE / 'verify.sh')]
        if args.sink:
            command += ['--candidate', str(root), '--sink', str(sink)]
        return H.enter(command, str(root))
    sink.mkdir(exist_ok=True)
    with Space(root, sink, store) as space, tempfile.TemporaryDirectory(prefix='veldo-change-') as temporary:
        receipt = execute(context, store, Path(temporary))
        recheck(context)
        space.finish()
        gate = C.publish_gate(root, store, context['repository'], context['inventory'], receipt)
        write_outputs(root, sink, store, context, gate)
        space.step('verdict')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print('GATE: RED (change execution: %s)' % error, flush=True)
        raise SystemExit(1)
