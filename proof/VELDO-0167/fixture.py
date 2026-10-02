"""Reuse VELDO-0171's installed-host fixture without executing its behavior rows."""
import ast
from pathlib import Path


def run(root, production, exercise):
    source = (Path(root) / 'scripts/suites/85_veldo_0171_setup_api.py').read_text()
    prefix = source[:source.index('    try:\n        takes =')]
    tree = ast.parse(prefix)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    assignment = next(n for n in function.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'PRODUCTION' for t in n.targets))
    lines = prefix.splitlines(keepends=True)
    lines[assignment.lineno - 1:assignment.end_lineno] = ['    PRODUCTION = __production__\n']
    prefix = ''.join(lines)
    cleanup = source[source.index('    finally:\n        close_runtime()'):source.index('    if profiler is not None:')]
    body = "    try:\n        __exercise__(locals())\n" + cleanup
    # Installation fakes use the shared constructors and emit no vendor protocol.
    body = body.replace('        close_runtime()',
                        "        compare = load('v167_conform', Path(__fixture__).resolve().parents[2] / 'proof/VELDO-0172/compare_formats.py')\n"
                        "        issues, trace = compare.conform_fake(dict(base=base, fake=engines186['fake']), '0167_setup_records')\n"
                        '        close_runtime()')
    body += "    if issues:\n        raise AssertionError(str(issues))\n"
    ns = dict(ROOT=Path(root), __production__=production, __exercise__=exercise, __fixture__=__file__)
    exec(compile(prefix + body + '\n_v171_suite()\n', __file__, 'exec'), ns)
