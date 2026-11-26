"""Classify the round 2 receipt without launching workers or reading other worktrees."""
import ast
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OLD = json.loads((ROOT / 'proof/VELDO-0368/eligibility.json').read_text())
BASE = OLD['receipt_commit']
for number, line in enumerate(Path(OLD['source']).open(), 1):
    if number == OLD['source_line']:
        receipt = json.loads(line[line.index('{'):])
        assert hashlib.sha256(line.encode()).hexdigest() == OLD['receipt_sha256']
        break

@lru_cache(None)
def source(name):
    return subprocess.check_output(['git', 'show', BASE + ':' + name], cwd=ROOT)

names = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines())
python_names = {n for n in names if n.endswith('.py')}
by_base = defaultdict(set)
for n in python_names:
    by_base[Path(n).name].add(n)
requires = json.loads(source('scripts/suites/requires.json')).get('requires', {})
declarations = json.loads(source('scripts/mutation_case_inputs.json'))['cases']
current_declarations = json.loads((ROOT / 'scripts/mutation_case_inputs.json').read_text())['cases']
cases = {r['case']['identity']: r['case'] for r in receipt['results']}
workers = {w['name']: w for w in receipt['worker_outcomes']}
assert len(cases) == 4023 and len(workers) == 5495

@lru_cache(None)
def imports(name):
    body = source(name).decode()
    tree = ast.parse(body)
    if name in ('scripts/check_teeth_mutations.py', 'scripts/check_review_mutations.py'):
        tree.body = [n for n in tree.body if not (
            isinstance(n, ast.If) or
            isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in ('cases', 'main', 'reuse_definition') or
            isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CASES' for t in n.targets))]
    found, unresolved = set(), []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or '']
            if isinstance(node, ast.ImportFrom):
                modules += [(node.module + '.' if node.module else '') + a.name for a in node.names]
            for module in modules:
                relative = module.replace('.', '/')
                for prefix in (str(Path(name).parent), 'scripts', '.veldo', 'scripts/suites/support', ''):
                    for suffix in ('.py', '/__init__.py'):
                        candidate = (prefix + '/' if prefix else '') + relative + suffix
                        if candidate in python_names:
                            found.add(candidate)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Literal filenames catch the existing support-loader convention. This
            # deliberately includes every repository match with that basename.
            value = node.value
            if value.endswith('.py') and '\n' not in value and len(value) < 180:
                found.update(by_base.get(Path(value).name, ()))
        if isinstance(node, ast.Call):
            label = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
            if label in ('import_module', '__import__') and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                module = node.args[0].value.replace('.', '/')
                for prefix in (str(Path(name).parent), 'scripts', '.veldo', 'scripts/suites/support', ''):
                    for suffix in ('.py', '/__init__.py'):
                        candidate = (prefix + '/' if prefix else '') + module + suffix
                        if candidate in python_names:
                            found.add(candidate)
            elif label in ('spec_from_file_location', 'import_module', '__import__', 'exec', 'eval', 'run_path'):
                unresolved.append((node.lineno, label))
    return found, unresolved

@lru_cache(None)
def closure(seeds):
    seen, pending, dynamic = set(), list(seeds), []
    missing = sorted(n for n in seeds if n not in names)
    while pending:
        name = pending.pop()
        if name in seen or name not in python_names:
            continue
        seen.add(name)
        found, hazards = imports(name)
        dynamic.extend([name, line, label] for line, label in hazards)
        pending.extend(found - seen)
    return sorted(seen), dynamic, missing

rows, suite_rows = [], defaultdict(lambda: dict(cases=0, declarations=0, reviewed=0, proposal_cases=0, closed_cases=0))
for identity, case in sorted(cases.items()):
    if workers[identity]['leg'] != 'confined':
        continue
    suite = case['suite']
    target = ('scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo')) + '/' + case['module']
    seeds = {'scripts/suites/' + suite, 'scripts/suites/shared.py', target,
             'scripts/reuse_worker.py', 'scripts/mutation_observer.py', 'scripts/' + case['driver']}
    pending = [Path(suite).stem]
    done = set()
    while pending:
        s = pending.pop()
        if s in done:
            continue
        done.add(s)
        children = requires.get(s, [])
        seeds.update('scripts/suites/' + x + '.py' for x in children)
        pending.extend(children)
    files, dynamic, missing = closure(tuple(sorted(seeds)))
    declared = identity in declarations
    reviewed = declarations.get(identity, {}).get('reviewed') is True
    proposal = not missing and bool(files)
    closed = proposal and not dynamic
    group = suite + ':' + case['module'] + ':' + str(case.get('fixture') is True)
    if case.get('confined_only') is True:
        group += ':confined'
    controls = [group + ':' + m for m in ('baseline', 'noop')]
    assert all(workers[c]['leg'] == 'confined' for c in controls)
    rows.append(dict(identity=identity, suite=suite, declared=declared, reviewed=reviewed,
        current_declared=identity in current_declarations, proposal=proposal, closed=closed,
        files=len(files), dynamic_sites=len(dynamic), missing=missing, controls=controls))
    dest = suite_rows[suite]
    for key, value in [('cases', 1), ('declarations', declared), ('reviewed', reviewed), ('proposal_cases', proposal), ('closed_cases', closed)]:
        dest[key] += value

def weight(selected):
    mutant = {r['identity'] for r in selected}
    controls = {c for r in selected for c in r['controls']}
    return dict(cases=len(mutant), controls=len(controls),
        mutant_seconds=sum(workers[x]['elapsed'] for x in mutant),
        control_seconds=sum(workers[x]['elapsed'] for x in controls))

result = dict(receipt=OLD['source'], source_line=OLD['source_line'], receipt_sha256=OLD['receipt_sha256'],
    receipt_commit=BASE, classification_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    all_cases=len(cases), all_workers=len(workers), total_worker_seconds=OLD['original_measurement']['total_worker_seconds'],
    target_worker_seconds=OLD['still_unknown_seconds'],
    categories={key: weight([r for r in rows if test(r)]) for key, test in {
        'confined': lambda r: True, 'declared': lambda r: r['declared'],
        'reviewed': lambda r: r['reviewed'], 'current_declared': lambda r: r['current_declared'],
        'generated_proposal': lambda r: r['proposal'], 'closed_static_imports': lambda r: r['closed'],
        'declaration_or_closed_imports': lambda r: r['declared'] or r['closed']}.items()},
    import_file_count=dict(min=min(r['files'] for r in rows), median=statistics.median(r['files'] for r in rows), max=max(r['files'] for r in rows)),
    dynamic_site_count=dict(min=min(r['dynamic_sites'] for r in rows), median=statistics.median(r['dynamic_sites'] for r in rows), max=max(r['dynamic_sites'] for r in rows)),
    declaration_file_sha256=hashlib.sha256(source('scripts/mutation_case_inputs.json')).hexdigest(),
    current_declaration_file_sha256=hashlib.sha256((ROOT/'scripts/mutation_case_inputs.json').read_bytes()).hexdigest(),
    suites=dict(sorted(suite_rows.items())), cases=rows,
    method='Static imports and literal Python filenames form proposals only. Literal module-name imports are resolved; other dynamic loaders remain unresolved, even when some file targets have literal names. No Python execution or fixture/data inference. Controls counted once within each category; categories overlap. No narrowed historical execution or new eligibility is claimed.')
assert result['categories']['confined']['cases'] == 2874
assert result['categories']['confined']['controls'] == 1000
for row in result['categories'].values():
    row['total_seconds'] = row['mutant_seconds'] + row['control_seconds']
    row['share_target_percent'] = 100 * row['total_seconds'] / result['target_worker_seconds']
    row['share_all_percent'] = 100 * row['total_seconds'] / result['total_worker_seconds']
case_rows = result.pop('cases')
print(json.dumps(result, indent=2, sort_keys=True)[:-2] + ',\n  \"cases\": [\n' +
      ',\n'.join('    ' + json.dumps(row, sort_keys=True, separators=(',', ':')) for row in case_rows) + '\n  ]\n}')
