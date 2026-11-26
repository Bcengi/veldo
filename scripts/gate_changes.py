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
