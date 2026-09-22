"""One document reader: boundary teeth, complete corpus, and reader agreement."""
import unittest as _y_unittest
import hashlib as _y_hashlib


def _y_load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_y_boundary = _y_load('parser_boundary', ROOT / 'scripts/check_parser_boundary.py')
_y_tests = _y_load('reader_tests', ROOT / 'scripts/test_yamlish.py')
_y_result = _y_unittest.TextTestRunner().run(_y_unittest.defaultTestLoader.loadTestsFromModule(_y_tests))
expect('parser/strict-values-structures-and-refusals', _y_result.wasSuccessful())
expect('parser/no-private-readers', not _y_boundary.check(ROOT))
_y_copies = (
    'def parse_yamlish(src):\n    return {}\n',
    'def renamed(text):\n    for line in text.splitlines():\n        key, _, value = line.partition(":")\n',
    'def other(text):\n    lines = text.splitlines()\n    for row in lines:\n        pair = row.split(":", 1)\n',
    'm = re.match(r"^---\\n(.*?)\\n---", text, re.S)',
    'KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(.*)$")',
    'for line in text.splitlines():\n    m = re.match(r"^status: *(.*)$", line)\n',
    'import yaml\nvalue = yaml.safe_load(text)',
    'def read(text):\n    return text.split("\\n---")[0]\n',
)
expect('parser/renamed-copies-and-foreign-readers-are-rejected',
       all(_y_boundary.problems(src) for src in _y_copies))
with tempfile.TemporaryDirectory() as _y_dir:
    _y_tree = Path(_y_dir)
    (_y_tree / '.veldo').mkdir()
    (_y_tree / '.veldo/new_reader.py').write_text(_y_copies[1])
    expect('parser/new-module-copy-fails-the-tree-check', bool(_y_boundary.check(_y_tree)))
    (_y_tree / '.veldo/new_reader.py').write_text('value = reader.front_matter(text)\n')
    expect('parser/delegating-reader-is-allowed-control', not _y_boundary.check(_y_tree))

_y_reader = V._yamlish
_y_report = json.loads((ROOT / 'proof/VELDO-0110/corpus-before.json').read_text())
_y_git = _y_load('parser_audit_git', ROOT / '.veldo/git_process.py')
_y_paths = _y_git.check_output(['git', 'ls-tree', '-r', '--name-only', _y_report['baseline']], cwd=ROOT, text=True).splitlines()
_y_baseline = {p for p in _y_paths if len(Path(p).parts) == 2 and Path(p).parts[0] in ('specs', 'plans') and p.endswith('.md')}
expect('parser/baseline-report-inventory-is-complete',
       _y_baseline == {r['path'] for r in _y_report['corpus']} and len(_y_baseline) == 331)
_y_hashes = all(_y_hashlib.sha256(_y_git.check_output(
    ['git', 'show', _y_report['baseline'] + ':' + row['path']], cwd=ROOT)).hexdigest() == row['sha256']
    for row in _y_report['corpus'])
expect('parser/baseline-report-hashes-name-real-inputs', _y_hashes)
_y_docs = sorted(list((ROOT / 'specs').glob('*.md')) + list((ROOT / 'plans').glob('*.md')))
_y_current = [(p, _y_reader.front_matter(p.read_text(), str(p))) for p in _y_docs]
expect('parser/entire-current-corpus-is-readable',
       len(_y_current) >= 331 and all(fm is not None or p.name == 'index.md' for p, fm in _y_current))
_y_index = _y_load('parser_index', ROOT / 'scripts/update_index.py')
expect('parser/validator-and-index-return-identical-structures',
       all(V.front_matter(p.read_text()) == _y_index.front_matter(p.read_text()) == fm
           for p, fm in _y_current))
_y_fv = _y_load('parser_policy', ROOT / '.veldo/fix_validation_record.py')
_y_release = _y_load('parser_release', ROOT / '.veldo/release_contract.py')
expect('parser/release-reader-agrees-on-every-corpus-document',
       all(_y_release.front_matter(p, V.parse_yamlish) == (fm, None)
           for p, fm in _y_current if fm is not None))
_y_migrations = json.loads((ROOT / 'proof/VELDO-0110/document-migration.json').read_text())
_y_preserved = True
for _y_row in _y_migrations:
    _y_path = ROOT / _y_row['path']
    _y_value = (_y_reader.front_matter(_y_path.read_text()) if _y_path.suffix == '.md'
                else _y_reader.read(_y_path))
    _y_preserved = _y_preserved and _y_value[_y_row['field']] == _y_row['new'][_y_row['field']]
expect('parser/migrated-prose-retains-every-recorded-field-value', _y_preserved)
with tempfile.TemporaryDirectory() as _y_dir:
    _y_root = Path(_y_dir)
    _y_policy = _y_root / 'policy.yaml'
    _y_policy.write_text('fix_validation: {required: true, from_commit: 0' + '1' * 39 + '} # armed\n')
    expect('parser/shared-policy-syntax-cannot-disarm-the-owner',
           _y_fv.read_policy(_y_policy)['fix_validation'] == _y_reader.read(_y_policy)['fix_validation'])
    _y_bad = _y_root / 'S.md'
    for _y_text in ('---\nstatus: ready\nstatus: draft\n---\n', '---\n- a\n---\n', '---\nstatus: [bad\n---\n'):
        _y_bad.write_text(_y_text)
        _y_refused = []
        for _y_fn in (V.front_matter, _y_index.front_matter):
            try:
                _y_fn(_y_text)
                _y_refused.append(False)
            except ValueError:
                _y_refused.append(True)
        _y_fm, _y_error = _y_release.front_matter(_y_bad, V.parse_yamlish)
        expect('parser/malformed-front-matter-refuses-across-all-surfaces-' + str(len(_y_text)),
               all(_y_refused) and _y_fm is None and bool(_y_error))
_y_scaffold = _y_load('parser_scaffold', ROOT / '.veldo/init_scaffold.py')
expect('parser/init-required-substrate-includes-the-transitive-reader',
       '.veldo/yamlish.py' in _y_scaffold.REQUIRED_SUBSTRATE
       and (ROOT / '.veldo/init_scaffold.py').read_text().count('".veldo/yamlish.py"') == 2)
expect('parser/shared-reader-engine-mirror-is-identical',
       (ROOT / '.veldo/yamlish.py').read_bytes() == (ROOT / 'engine/.veldo/yamlish.py').read_bytes())

# A strict reader cannot help if an index catches its refusal and reports absence.
_y_mirror = _y_load('parser_mirror', ROOT / '.veldo/tracker_mirror.py')
_y_estimate = _y_load('parser_estimate', ROOT / '.veldo/estimate.py')
_y_projection = _y_load('parser_projection', ROOT / '.veldo/request_projection.py')
_y_floor = _y_load('parser_floor', ROOT / '.veldo/behavior_floor.py')
with tempfile.TemporaryDirectory() as _y_dir:
    _y_root = Path(_y_dir)
    _y_specs = _y_root / 'specs'
    _y_plans = _y_root / 'plans'
    _y_specs.mkdir()
    _y_plans.mkdir()
    _y_bad = _y_specs / 'bad.md'
    _y_bad.write_text('---\nid: A\nid: B\n---\n')
    _y_calls = [
        ('tracker-spec-index', lambda: _y_mirror.build_spec_index(_y_specs)),
        ('tracker-plan-status-index', lambda: _y_mirror.build_plan_index(_y_plans, _y_specs)),
        ('release-index', lambda: _y_release.release_registry(_y_specs, V.parse_yamlish)),
        ('duplicate-index', lambda: _y_release.id_paths([_y_bad], V.parse_yamlish)),
    ]
    _y_private = _y_root / '.veldo'
    _y_private.mkdir()
    (_y_private / 'policy.yaml').write_text('protected_paths: [bad\n')
    _y_calls.append(('estimate-policy', lambda: _y_estimate.protected_paths(_y_root)))
    _y_requests = _y_private / 'requests'
    _y_requests.mkdir()
    (_y_requests / 'bad.yaml').write_text('id: A\nid: B\n')
    _y_calls.extend([
        ('request-projection', lambda: _y_projection.build_request_index(_y_requests)),
        ('floor-request-index', lambda: _y_floor._load_requests(_y_root, V.parse_yamlish)),
    ])
    for _y_name, _y_call in _y_calls:
        try:
            _y_call()
            _y_refused = False
        except ValueError:
            _y_refused = True
        expect('parser/no-malformed-input-becomes-absence-' + _y_name, _y_refused)
    expect('parser/release-corpus-reports-unreadable-metadata',
           any(cause == _y_release.CAUSE_UNREADABLE for _, cause, _ in
               _y_release.release_problems(_y_specs, _y_plans, V.parse_yamlish)))
