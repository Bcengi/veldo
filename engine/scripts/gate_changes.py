"""VELDO-0367 foundations. No gate entry calls this module until increment 5.

The authority supplies the complete catalog and expanded identities; this module
never executes candidate catalog commands or infers success from a tree hash.
"""
import hashlib
import json
import re
import subprocess

DEPENDENCY = 'veldo.dependency/v1'
INVENTORY = 'veldo.change-inventory/v1'
RECEIPT = 'veldo.change-receipt/v1'
RESULT = 'veldo.change-result/v1'
RESULT_V2 = 'veldo.change-result/v2'
GATE = 'veldo.change-gate/v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def hex_id(value, lengths=(64,)):
    return isinstance(value, str) and len(value) in lengths and re.fullmatch('[0-9a-f]+', value) is not None


def commit_id(value):
    return hex_id(value, (40, 64))


def path_ok(value, directory=False):
    return (isinstance(value, str) and bool(value) and '\x00' not in value
            and (directory and value == '.' or all(p not in ('', '.', '..') for p in value.split('/'))))


def sealed(schema, **fields):
    value = dict(schema=schema, **fields)
    return dict(value, record_digest=digest(value))


def check_seal(value, schema, fields):
    require(isinstance(value, dict) and set(value) == set(fields) | {'schema', 'record_digest'}, 'record fields')
    require(value['schema'] == schema, 'record version')
    require(hex_id(value['record_digest']) and value['record_digest'] ==
            digest({k: v for k, v in value.items() if k != 'record_digest'}), 'record digest')


def validate_dependency(value):
    check_seal(value, DEPENDENCY, ('item_id', 'observed_commit', 'paths', 'directories', 'absent_paths',
                                   'runtime_digest', 'complete', 'unknown_reason'))
    require(isinstance(value['item_id'], str) and bool(value['item_id']), 'item identity')
    require(commit_id(value['observed_commit']), 'observed commit')
    require(hex_id(value['runtime_digest']), 'runtime digest')
    for field in ('paths', 'directories', 'absent_paths'):
        paths = value[field]
        require(isinstance(paths, list) and all(path_ok(p, field == 'directories') for p in paths), 'dependency paths')
        require(paths == sorted(set(paths)), 'canonical dependency paths')
    require(type(value['complete']) is bool, 'observation completeness')
    require(value['unknown_reason'] is None if value['complete'] else
            isinstance(value['unknown_reason'], str) and bool(value['unknown_reason'].strip()), 'unknown reason')
    return value


def identity(kind, stage, leg='', suite='', driver='', case=''):
    parts = (kind, stage, leg, suite, driver, case)
    require(all(isinstance(p, str) for p in parts) and bool(stage), 'identity coordinates')
    return json.dumps(parts, separators=(',', ':'), ensure_ascii=True)


def inventory(items):
    """Definitions are content digests, never candidate/tree hashes. Reasons survive."""
    items = sorted(items, key=lambda item: item['item_id'])
    value = sealed(INVENTORY, items=items)
    validate_inventory(value)
    return value


def validate_inventory(value):
    check_seal(value, INVENTORY, ('items',))
    require(isinstance(value['items'], list) and bool(value['items']), 'empty inventory')
    seen = set()
    for item in value['items']:
        require(isinstance(item, dict) and set(item) == {'item_id', 'definition_digest', 'state', 'reason'}, 'inventory fields')
        require(isinstance(item['item_id'], str) and bool(item['item_id']) and item['item_id'] not in seen, 'duplicate identity')
        seen.add(item['item_id'])
        require(hex_id(item['definition_digest']), 'definition digest')
        require(item['state'] in ('required', 'not-applicable', 'waived'), 'catalog state')
        require(item['reason'] is None if item['state'] == 'required' else
                isinstance(item['reason'], str) and bool(item['reason'].strip()), 'catalog reason')
    require([i['item_id'] for i in value['items']] == sorted(seen), 'inventory order')
    return value


def build_inventory(catalog, expanded, manifest, requires, drivers, uncataloged=()):
    """Normalize authority snapshots, without importing either mutation driver.

    catalog maps every CHECK slot to its declaration, expanded maps each required
    stage to its scheduler legs. drivers maps each driver name to case definitions
    carrying name, suite and leg. Callers must provide both driver registries.
    Suite definitions include their manifest entry and prerequisite closure.
    """
    items = []

    def add(key, definition, state='required', reason=None):
        items.append(dict(item_id=key, definition_digest=digest(definition), state=state, reason=reason))

    required = set()
    for stage, declaration in catalog.items():
        state, separator, reason = declaration.partition(':')
        require(separator and reason.strip() and state in ('required', 'na', 'waived'), 'catalog declaration')
        state = 'not-applicable' if state == 'na' else state
        add(identity('stage', stage), declaration, state, None if state == 'required' else reason)
        if state == 'required':
            required.add(stage)
    require(set(expanded) == required, 'expanded stages')
    for stage, legs in expanded.items():
        require(isinstance(legs, list) and legs and all(isinstance(x, str) and x for x in legs), 'expanded legs')
        for leg in legs:
            add(identity('leg', stage, leg), [catalog[stage], leg])
    suites = {entry['name']: entry for entry in manifest['suites']}
    require(len(suites) == len(manifest['suites']) and set(requires['requires']) == set(suites), 'suite inventory')
    for name, entry in suites.items():
        closure = requires['requires'][name]
        require(isinstance(closure, list) and name in closure and len(set(closure)) == len(closure)
                and set(closure) <= set(suites), 'suite closure')
        # Each suite identity is present in every suite-running stage/leg; later
        # observation can retain a not-applicable reason for an empty leg.
        for stage in ('unit', 'integration'):
            for leg in expanded.get(stage, ()):
                add(identity('suite', stage, leg, name), [entry, [suites[n] for n in closure]])
    require(len(drivers) == 2, 'both mutation registries required')
    for driver, cases in drivers.items():
        require(isinstance(driver, str) and bool(driver) and isinstance(cases, list), 'driver registry')
        for case in cases:
            require(case['suite'] in suites and case['leg'] in expanded.get('mutation', ()), 'case coordinates')
            add(identity('case', 'mutation', case['leg'], case['suite'], driver, case['name']), case)
    for entry in uncataloged:
        add(identity('uncataloged', entry['name']), entry)
    return inventory(items)


def reconcile(current, previous=None):
    """Identity/definition reconciliation only; unchanged does not authorize carry."""
    validate_inventory(current)
    if previous is not None:
        validate_inventory(previous)
    old = {item['item_id']: item for item in previous['items']} if previous else {}
    rows = []
    for item in current['items']:
        prior = old.pop(item['item_id'], None)
        reason = 'new' if prior is None else 'unchanged' if prior == item else 'definition-changed'
        rows.append(dict(item_id=item['item_id'], state=item['state'], reason=reason,
                         catalog_reason=item['reason']))
    rows.extend(dict(item_id=key, state='removed', reason='removed', catalog_reason=None) for key in sorted(old))
    return rows


def validate_receipt(value, current):
    validate_inventory(current)
    check_seal(value, RECEIPT, ('candidate_commit', 'baseline_commit', 'baseline_record_digest',
                                'changed_paths_digest', 'inventory_digest', 'items'))
    require(commit_id(value['candidate_commit']), 'candidate commit')
    require((value['baseline_commit'] is None and value['baseline_record_digest'] is None) or
            (commit_id(value['baseline_commit']) and hex_id(value['baseline_record_digest'])), 'baseline pin')
    require(hex_id(value['changed_paths_digest']) and value['inventory_digest'] == current['record_digest'], 'receipt inventory')
    expected = {i['item_id']: i for i in current['items']}
    seen = set()
    require(isinstance(value['items'], list), 'receipt items')
    for item in value['items']:
        require(isinstance(item, dict) and set(item) == {'item_id', 'status', 'dependency_record_digest',
                'result_digest', 'source_commit', 'source_gate_digest'}, 'receipt item fields')
        key, status = item['item_id'], item['status']
        require(isinstance(key, str) and key not in seen, 'duplicate receipt identity')
        seen.add(key)
        require(status in ('executed', 'carried', 'failed', 'removed', 'not-applicable', 'waived'), 'receipt status')
        if status == 'removed':
            require(key not in expected, 'removed current identity')
        else:
            require(key in expected, 'unexpected receipt identity')
            state = expected[key]['state']
            require(status in ('executed', 'carried', 'failed') if state == 'required' else status == state, 'receipt state')
        if status in ('executed', 'carried', 'failed'):
            require(all(hex_id(item[f]) for f in ('dependency_record_digest', 'result_digest')), 'receipt references')
            require(commit_id(item['source_commit']), 'result source')
            require(item['source_commit'] == value['candidate_commit'] if status != 'carried' else
                    hex_id(item['source_gate_digest']), 'execution provenance')
            if status != 'carried':
                require(item['source_gate_digest'] is None, 'execution gate is enclosing record')
        else:
            require(all(item[f] is None for f in ('dependency_record_digest', 'result_digest', 'source_commit',
                                                'source_gate_digest')), 'non-pass credit')
    require(set(expected) <= seen, 'incomplete receipt inventory')
    return value


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE).stdout


def pin(root, commit):
    require(commit_id(commit), 'immutable commit required')
    require(git(root, 'rev-parse', '--verify', commit + '^{commit}').decode().strip() == commit, 'commit pin')
    return commit


def first_parents(root, candidate):
    pin(root, candidate)
    return git(root, 'rev-list', '--first-parent', candidate).decode().splitlines()


def tree(root, commit):
    pin(root, commit)
    entries = {}
    for row in git(root, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if row:
            metadata, name = row.split(b'\t', 1)
            entries[name.decode('utf-8', 'surrogateescape')] = metadata.decode('ascii')
    return entries


def changed_paths(root, baseline, candidate):
    """Blob identity covers symlink targets; modes and both rename endpoints count."""
    before, after = tree(root, baseline), tree(root, candidate)
    return sorted(path for path in before.keys() | after.keys() if before.get(path) != after.get(path))


def baseline(root, candidate, store, repository):
    """Nearest authenticated complete green on first-parent history, including a rerun."""
    for commit in first_parents(root, candidate):
        record = store.change_gate(repository, commit)
        if record is not None:
            return dict(candidate_commit=candidate, baseline_commit=commit,
                        baseline_record_digest=record['record_digest'],
                        changed_paths=changed_paths(root, commit, candidate))
    return dict(candidate_commit=candidate, baseline_commit=None, baseline_record_digest=None,
                changed_paths=None)


# Only increment 5 changes this authority-owned switch. Environment variables and
# candidate receipts cannot enable selection.
SELECTION_ENABLED = False


def intersects(dependency, changed):
    """Reads, failed lookups and directory discovery all participate in selection."""
    validate_dependency(dependency)
    return any(path in dependency['paths'] or path in dependency['absent_paths'] or
               any(directory == '.' or path == directory or path.startswith(directory + '/')
                   for directory in dependency['directories']) for path in changed)


def referenced(store, key, schema, fields):
    require(hex_id(key), 'reference digest')
    value = store.get(key)  # Store.get also checks authentication and revocation.
    check_seal(value, schema, fields)
    require(value['record_digest'] == key, 'reference binding')
    return value


def item_evidence(store, item):
    dependency = store.get(item['dependency_record_digest'])
    validate_dependency(dependency)
    require(dependency['record_digest'] == item['dependency_record_digest'] and
            dependency['item_id'] == item['item_id'] and
            dependency['observed_commit'] == item['source_commit'], 'dependency source')
    raw = store.get(item['result_digest'])
    scoped = isinstance(raw, dict) and raw.get('schema') == RESULT_V2
    result = referenced(store, item['result_digest'], RESULT_V2 if scoped else RESULT,
                        ('item_id', 'source_commit', 'status', 'complete', 'dependency_record_digest') +
                        (('execution_record_digest',) if scoped else ()))
    require(result['item_id'] == item['item_id'] and result['source_commit'] == item['source_commit']
            and result['status'] == 'passed' and result['complete'] is True and
            result['dependency_record_digest'] == dependency['record_digest'], 'result source')
    try:
        coordinates = json.loads(item['item_id'])
    except ValueError:
        coordinates = None
    if isinstance(coordinates, list) and coordinates and coordinates[0] == 'case':
        require(scoped, 'mutation execution reference required')
    if scoped:
        execution_evidence(store, result, dependency, coordinates)
    return dependency


def execution_evidence(store, result, dependency, coordinates):
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path
    execution = referenced(store, result['execution_record_digest'], 'veldo.mutation-kill/v1',
                           ('source_commit', 'dependency', 'result'))
    require(execution['dependency'] == dependency and execution['source_commit'] == result['source_commit'],
            'execution dependency source')
    spec = spec_from_file_location('change_mutations', Path(__file__).with_name('check_gate_mutations.py'))
    gate = module_from_spec(spec)
    spec.loader.exec_module(gate)
    mutation = execution['result']
    case = mutation['case']
    require(isinstance(coordinates, list) and len(coordinates) == 6 and coordinates[0:2] == ['case', 'mutation']
            and coordinates[3:] == [case['suite'], case['driver'], case['name']], 'execution identity')
    require(mutation['schema'] == 'veldo.mutation-result/v2', 'scoped execution required')
    try:
        gate.validate_result(mutation, case, store=store)
    except gate.Refused as error:
        raise ValueError('invalid mutation execution: ' + str(error)) from error
    controls = store.get(mutation['control_receipt_digest'])
    require(controls['suite']['leg'] == coordinates[2] and all(k['kill_by'] in ('assertion', 'terminal')
            for k in mutation['kills']), 'execution leg and rejection')


def historical_gate(store, key, repository):
    """A baseline was green when published; missing siblings do not erase its identity.

    Revalidate all evidence actually carried by the new gate, rather than forcing
    every item to rerun because an unrelated historical reference was revoked.
    """
    gate = referenced(store, key, GATE, ('repository', 'inventory', 'receipt', 'status', 'complete'))
    require(gate['repository'] == repository and gate['status'] == 'green' and gate['complete'] is True,
            'historical green gate')
    validate_receipt(gate['receipt'], gate['inventory'])
    require(all(i['status'] != 'failed' for i in gate['receipt']['items']), 'failed historical item')
    return gate


def green_record(root, store, gate, repository, seen=()):
    """Validate the entire authenticated chain, including original execution provenance."""
    check_seal(gate, GATE, ('repository', 'inventory', 'receipt', 'status', 'complete'))
    require(gate['record_digest'] not in seen, 'cyclic provenance')
    seen = (*seen, gate['record_digest'])
    require(gate['repository'] == repository and gate['status'] == 'green' and gate['complete'] is True,
            'eligible green gate')
    receipt = validate_receipt(gate['receipt'], gate['inventory'])
    candidate = receipt['candidate_commit']
    prior = None
    if receipt['baseline_record_digest'] is not None:
        prior = historical_gate(store, receipt['baseline_record_digest'], repository)
        require(prior['record_digest'] == receipt['baseline_record_digest'] and
                prior['receipt']['candidate_commit'] == receipt['baseline_commit'] and
                receipt['baseline_commit'] in first_parents(root, candidate), 'baseline provenance')
        changed = changed_paths(root, receipt['baseline_commit'], candidate)
        require(digest(changed) == receipt['changed_paths_digest'], 'changed paths binding')
    old = {i['item_id']: i for i in prior['receipt']['items']} if prior else {}
    definitions = {i['item_id']: i for i in prior['inventory']['items']} if prior else {}
    current = {i['item_id']: i for i in gate['inventory']['items']}
    for item in receipt['items']:
        require(item['status'] != 'failed', 'failed item')
        if item['status'] == 'removed':
            require(item['item_id'] in definitions, 'unknown removed identity')
        if item['status'] not in ('executed', 'carried'):
            continue
        dependency = item_evidence(store, item)
        if item['status'] == 'carried':
            key = item['item_id']
            require(prior is not None and definitions.get(key) == current[key], 'carried definition')
            source = old.get(key)
            require(source is not None and source['status'] in ('executed', 'carried'), 'missing baseline item')
            expected = dict(source, status='carried', source_gate_digest=(prior['record_digest']
                            if source['status'] == 'executed' else source['source_gate_digest']))
            require(item == expected, 'carried provenance')
            require(dependency['complete'] and not intersects(dependency, changed), 'stale carried evidence')
            origin = historical_gate(store, item['source_gate_digest'], repository)
            require(item['source_commit'] in first_parents(root, candidate), 'source ancestry')
            require(origin['record_digest'] == item['source_gate_digest'] and
                    origin['receipt']['candidate_commit'] == item['source_commit'] and
                    dict(item, status='executed', source_gate_digest=None) in origin['receipt']['items'],
                    'original execution')
    return gate


def eligible_baseline(root, store, repository, candidate):
    history = first_parents(root, candidate)
    for commit in history:
        try:
            index = store.get(store.change_gate_key(repository, commit))
            require(index['repository'] == repository and index['commit'] == commit, 'index provenance')
            visited = set()
            while True:
                previous = index['record_digest']
                require(previous not in visited, 'index cycle')
                visited.add(previous)
                successor = store.get(successor_key(repository, commit, previous))
                if successor is None:
                    break
                require(set(successor) == {'schema', 'repository', 'commit', 'previous_record_digest', 'record_digest'}
                        and successor['schema'] == 'veldo.change-successor/v1'
                        and successor['repository'] == repository and successor['commit'] == commit
                        and successor['previous_record_digest'] == previous, 'successor binding')
                index = successor
            gate = store.get(index['record_digest'])
            check_seal(gate, GATE, ('repository', 'inventory', 'receipt', 'status', 'complete'))
            require(gate['repository'] == repository and gate['status'] == 'green' and gate['complete'] is True,
                    'eligible baseline')
            validate_receipt(gate['receipt'], gate['inventory'])
            require(all(i['status'] != 'failed' for i in gate['receipt']['items']), 'failed baseline')
            require(gate['record_digest'] == index['record_digest'] and
                    gate['receipt']['candidate_commit'] == commit, 'index binding')
            return gate
        except (OSError, ValueError, TypeError, KeyError):
            continue
    return None


def select(root, store, repository, candidate, current, runtimes):
    """Plan every identity. Unknown evidence runs just that item; there are no audits."""
    validate_inventory(current)
    pin(root, candidate)
    prior = eligible_baseline(root, store, repository, candidate)
    changed = changed_paths(root, prior['receipt']['candidate_commit'], candidate) if prior else None
    old = {i['item_id']: i for i in prior['receipt']['items']} if prior else {}
    rows = []
    for item in reconcile(current, prior['inventory'] if prior else None):
        key = item['item_id']
        status, reason, evidence = item['state'], item['reason'], None
        if status == 'required':
            status = 'run'
            if reason == 'unchanged':
                try:
                    source = old[key]
                    if source['status'] == 'carried':
                        origin = historical_gate(store, source['source_gate_digest'], repository)
                        require(source['source_commit'] in first_parents(root, candidate), 'source ancestry')
                        require(origin['record_digest'] == source['source_gate_digest'] and
                                dict(source, status='executed', source_gate_digest=None) in origin['receipt']['items'],
                                'original source binding')
                    require(source['status'] in ('executed', 'carried'), 'missing green result')
                    dependency = item_evidence(store, source)
                    require(dependency['complete'], 'unknown dependency')
                    require(dependency['runtime_digest'] == runtimes.get(key), 'runtime changed')
                    require(not intersects(dependency, changed), 'dependency changed')
                    status, reason = 'carried', 'dependencies unchanged'
                    evidence = dict(source, status='carried', source_gate_digest=(prior['record_digest']
                                    if source['status'] == 'executed' else source['source_gate_digest']))
                except (OSError, ValueError, TypeError, KeyError) as error:
                    reason = str(error) or 'unknown evidence'
            rows.append(dict(item_id=key, status=status, reason=reason, evidence=evidence))
        else:
            rows.append(dict(item_id=key, status=status, reason=item['catalog_reason'] or reason, evidence=None))
    return dict(candidate_commit=candidate, baseline_commit=prior['receipt']['candidate_commit'] if prior else None,
                baseline_record_digest=prior['record_digest'] if prior else None,
                changed_paths=changed, inventory=current, items=rows)


def assemble(plan, executed):
    """No worker runs for carried entries; diagnostics cannot fill missing executions."""
    require(set(executed) == {i['item_id'] for i in plan['items'] if i['status'] == 'run'},
            'execution inventory')
    entries = []
    for item in plan['items']:
        if item['status'] == 'run':
            entry = executed[item['item_id']]
            require(entry['item_id'] == item['item_id'] and entry['status'] == 'executed', 'execution identity')
        elif item['status'] == 'carried':
            entry = item['evidence']
        else:
            entry = dict(item_id=item['item_id'], status=item['status'], dependency_record_digest=None,
                         result_digest=None, source_commit=None, source_gate_digest=None)
        entries.append(entry)
    receipt = sealed(RECEIPT, candidate_commit=plan['candidate_commit'], baseline_commit=plan['baseline_commit'],
                     baseline_record_digest=plan['baseline_record_digest'], changed_paths_digest=digest(plan['changed_paths']),
                     inventory_digest=plan['inventory']['record_digest'], items=entries)
    return validate_receipt(receipt, plan['inventory'])


def dispatch(plan, execute):
    """The common child dispatcher, callable only by the authority's inactive path."""
    require(SELECTION_ENABLED, 'change selection is inactive until increment 5')
    return assemble(plan, {i['item_id']: execute(i['item_id']) for i in plan['items'] if i['status'] == 'run'})


def row_source(source, selected_rows):
    """Skip independent assertion bodies before evaluation, retaining suite setup.

    Only literal expect calls are selectable. Computed labels and wrapper-driven
    suites need a complete run until they expose independently addressable rows.
    This conservative refusal also handles missing or changed prior row identities.
    """
    import ast
    require(isinstance(selected_rows, list) and selected_rows and
            len(set(selected_rows)) == len(selected_rows), 'selected row inventory')
    selected = {name.split()[-1] for name in selected_rows}
    tree = ast.parse(source)
    found = []
    expressions = {id(node.value) for node in tree.body if isinstance(node, ast.Expr)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'expect':
            require(id(node) in expressions, 'row body is not independently addressable')

    class Rows(ast.NodeTransformer):
        def visit_Expr(self, node):
            call = node.value
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'expect':
                require(call.args and isinstance(call.args[0], ast.Constant) and
                        isinstance(call.args[0].value, str), 'unaddressable row')
                label = call.args[0].value.split(':', 1)[0].split()[-1]
                if label in selected:
                    found.append(label)
                    return node
                # Removing this expression also removes its condition's evaluation.
                return ast.copy_location(ast.Pass(), node)
            return self.generic_visit(node)
    tree = Rows().visit(tree)
    require(sorted(found) == sorted(selected) and len(found) == len(selected_rows), 'prior rows unavailable')
    return ast.unparse(ast.fix_missing_locations(tree)) + '\n'


def successor_key(repository, commit, previous):
    return digest(dict(schema='veldo.change-successor/v1', repository=repository,
                       commit=commit, previous_record_digest=previous))


def publish_gate(root, store, repository, current, receipt):
    """Append authenticated green records, including successive gates of one commit.

    The initial index stays immutable. Same-commit refreshes append a single
    authenticated successor; concurrent conflicting publications fail closed.
    """
    gate = sealed(GATE, repository=repository, inventory=current, receipt=receipt, status='green', complete=True)
    green_record(root, store, gate, repository)
    commit = receipt['candidate_commit']
    require(store.change_put(gate), 'gate publication')
    if receipt['baseline_commit'] == commit:
        previous = receipt['baseline_record_digest']
        key = successor_key(repository, commit, previous)
        index = dict(schema='veldo.change-successor/v1', repository=repository, commit=commit,
                     previous_record_digest=previous, record_digest=gate['record_digest'])
    else:
        key = store.change_gate_key(repository, commit)
        index = dict(repository=repository, commit=commit, record_digest=gate['record_digest'])
    require(store.put(key, index), 'gate index publication')
    return gate
