"""One document writer: generated properties, outside oracle, corpus and boundary teeth."""
import unittest as _w_unittest
import sys as _w_sys

# Standalone scripts are importable both here and from their CLI entry points.
_w_sys.path.insert(0, str(ROOT / 'scripts'))
import test_document_writer as _w_tests
import writer_corpus_audit as _w_audit
import check_writer_boundary as _w_boundary
_w_sys.path.pop(0)
_w_result = _w_unittest.TextTestRunner(verbosity=2).run(
    _w_unittest.defaultTestLoader.loadTestsFromModule(_w_tests))
expect('writer/generated-values-round-trip-and-oracle', _w_result.wasSuccessful())
_w_report = _w_audit.audit()
expect('writer/entire-corpus-round-trips-with-exact-field-diagnostics',
       _w_report['baseline_documents'] == 331 and _w_report['documents'] >= 331
       and _w_report['re_emitted'] >= 330 and _w_report['failures'] == 0)
if _w_tests.yaml is None:
    print('writer/corpus-real-yaml-oracle STANDS DOWN: PyYAML unavailable (not passed)')
else:
    expect('writer/corpus-real-yaml-oracle',
           all(row.get('oracle') == 'checked' and not row['oracle_differences']
               for row in _w_report['corpus'] if row.get('status') == 're-emitted'))
for _w_row in _w_report['corpus']:
    if _w_row.get('refusal') or _w_row['differences'] or _w_row.get('oracle_differences'):
        print('writer/corpus difference: ' + json.dumps(_w_row))
expect('writer/no-private-serializers', not _w_boundary.check(ROOT))
_w_copies = (
    'def _fm_scalar(v):\n    return str(v)\n',
    'def renamed(fm):\n    lines = [f"{k}: {v}" for k, v in fm.items()]\n    return "\\n".join(lines)\n',
    'def renamed(fm):\n    lines = []\n    for k, v in fm.items():\n        lines.append("%s: %s" % (k, v))\n    return "\\n".join(lines)\n',
    'def renamed(v):\n    return "title: %s\\n" % v\n',
    'def renamed(v):\n    return f"title: {v}\\n"\n',
    'def renamed(v):\n    return "\\n".join(["schema: x", "title: %s" % v])\n',
    'import yaml\ndef renamed(v):\n    return yaml.safe_dump(v)\n',
)
expect('writer/renamed-private-writers-refuse', all(_w_boundary.problems(src) for src in _w_copies))
with tempfile.TemporaryDirectory() as _w_tmp:
    _w_root = Path(_w_tmp)
    (_w_root / '.veldo').mkdir()
    _w_path = _w_root / '.veldo/new_writer.py'
    _w_path.write_text(_w_copies[1])
    expect('writer/planted-second-writer-fails-tree-check', bool(_w_boundary.check(_w_root)))
    _w_path.write_text('def render(value):\n    return writer.dump(value)\n')
    expect('writer/delegation-is-allowed-control', not _w_boundary.check(_w_root))
# Both intake entry points are the very same adapter, and the guard's code is frozen.
_w_git = _w_tests.load('writer_git', ROOT / '.veldo/git_process.py')
import ast as _w_ast
_w_before = _w_git.check_output(['git', 'show', '23e1a2b:.veldo/tracker_intake.py'], cwd=ROOT, text=True)
_w_after = (ROOT / '.veldo/tracker_intake.py').read_text()
def _w_guard(source):
    node = next(n for n in _w_ast.parse(source).body if isinstance(n, _w_ast.FunctionDef) and n.name == '_fm_safe')
    return _w_ast.get_source_segment(source, node)
expect('writer/tracker-injection-guard-is-byte-identical', _w_guard(_w_before) == _w_guard(_w_after))
expect('writer/transitive-substrate-is-in-both-init-lists',
       (ROOT / '.veldo/init_scaffold.py').read_text().count('".veldo/yamlish.py"') == 2)
expect('writer/shared-code-engine-mirror-is-identical',
       (ROOT / '.veldo/yamlish.py').read_bytes() == (ROOT / 'engine/.veldo/yamlish.py').read_bytes())
