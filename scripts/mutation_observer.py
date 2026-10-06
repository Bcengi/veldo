"""Authority-owned materialization and observation, with no candidate driver imports."""
import ast
import contextlib
import hashlib
import io
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def edits(case):
    return [(case['old'], case['new'])] + [tuple(pair) for pair in case.get('also', ())]


def mutate(text, case):
    """Apply every replacement of `case` to `text` (str or bytes); each anchor must occur exactly
    once in the text it is applied to."""
    for old, new in edits(case):
        if isinstance(text, bytes):
            old, new = old.encode(), new.encode()
        if text.count(old) != 1:
            raise RuntimeError((case['name'], 'mutation anchor moved', text.count(old)))
        text = text.replace(old, new)
    return text


def materialize(case, mode, directory, root=ROOT):
    """Own case paths, exact replacement and file/directory copies for every driver.

    Digests describe the actual module bytes, even when the suite receives a directory.
    Baselines use the original input; no-op and mutant copies never edit that input.
    """
    if mode not in ('baseline', 'noop', 'mutant'):
        raise ValueError('unknown mutation mode: ' + mode)
    fixture = case.get('fixture') is True
    # `dir`: the directory a production module lives in, relative to the root (.veldo by default;
    # VELDO-0058's gate script lives in scripts).
    base = root / 'scripts/fixtures' if fixture else root / case.get('dir', '.veldo')
    source = base / case['module']
    before = source.read_bytes()
    old = case['old'].encode()
    count = before.count(old)
    if count != 1:
        raise RuntimeError((case['name'], 'mutation anchor moved', count))
    mutated = mutate(before, case)
    mutant = None
    after = before
    if mode != 'baseline':
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        mutant = destination / ('fixtures' if fixture else case['module'])
        if fixture:
            shutil.copytree(base, mutant, ignore=shutil.ignore_patterns('__pycache__'))
        elif case.get('siblings') is True:
            # A module that loads its siblings by its own path (control_membership loads
            # authority_contract and control_store next to itself) gets a whole .veldo copy.
            shutil.copytree(base, destination / 'veldo', ignore=shutil.ignore_patterns('__pycache__'))
            mutant = destination / 'veldo' / case['module']
        target = mutant / case['module'] if fixture else mutant
        target.parent.mkdir(parents=True, exist_ok=True)
        for name in case.get('companions', ()):
            # A module that loads a named sibling by its own path runs beside an unchanged copy of it.
            shutil.copyfile(base / name, target.parent / name)
        target.write_bytes(before if mode == 'noop' else mutated)
        after = target.read_bytes()
    return dict(source=source, mutant=mutant, replacement_count=count,
                old_digest=hashlib.sha256(before).hexdigest(),
                new_digest=hashlib.sha256(after).hexdigest())


def worker(case, mutant=None):
    """Capture every assertion, including the shared preamble, with exact row identities."""
    shared = ROOT / 'scripts/suites/shared.py'
    rows = []
    details = []  # a false row's own words after its colon: what the check saw, kept beside the row

    def observe(name, condition):
        rows.append([name.split(':', 1)[0], bool(condition)])
        if not condition and ':' in name:
            details.append([rows[-1][0], name.split(':', 1)[1].strip()])
    ns = {'__file__': str(shared), '__observe__': observe}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        suite = ROOT / 'scripts/suites' / case['suite']
        source = suite.read_text()
        if case.get('fixture'):
            if mutant:
                source = source.replace('ROOT / "scripts" / "fixtures"',
                                        '__import__("pathlib").Path(' + repr(mutant) + ')')
        elif mutant and case.get('dir') == 'scripts/suites' and case['module'] == case['suite']:
            # The mutated module is the suite itself (a fake engine it embeds): its copy is what runs.
            source = Path(mutant).read_text()
        elif mutant:
            anchor = 'ROOT / "' + case.get('dir', '.veldo') + '" / "' + case['module'] + '"'
            if not source.count(anchor):
                raise RuntimeError('suite production-copy anchor moved')
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(mutant) + ')')
        ns['__suite_file__'] = str(suite)
        exec(compile(source, str(suite), 'exec'), ns)
    return {'count': len(rows), 'observations': rows,
            'row_names': [name for name, _ in rows],
            'failed_rows': [name for name, ok in rows if not ok],
            'failed_details': details,
            'targets': {label: [ok for name, ok in rows if name.split()[-1] == label]
                        for label in case['rows']}}

