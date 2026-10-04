"""Reuse VELDO-0171's installed-host fixture without executing its behavior rows."""
import ast
from pathlib import Path


def run(root, production, exercise, teardown, fake):
    source = (Path(root) / 'scripts/suites/85_veldo_0171_setup_api.py').read_text()
    prefix = source[:source.index('    try:\n        takes =')]
    tree = ast.parse(prefix)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
    assignment = next(n for n in function.body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'PRODUCTION' for t in n.targets))
    lines = prefix.splitlines(keepends=True)
    lines[assignment.lineno - 1:assignment.end_lineno] = ['    PRODUCTION = __production__\n']
    prefix = ''.join(lines)
    prefix = prefix.replace("ROOT / 'proof/VELDO-0186/fixtures.py'",
                            "ROOT / 'proof/VELDO-0162/setup_assets.py'")
    prefix = prefix.replace('engines186 = fixtures186.install(ROOT, base, mods)',
                            'engines186 = fixtures186.install(ROOT, base, mods, __fake__)')
    cleanup = source[source.index('    finally:\n        close_runtime()'):source.index('    if profiler is not None:')]
    body = "    try:\n        __exercise__(dict(locals(), ROOT=ROOT))\n" + cleanup
    # Observe the installation executables before the shared fixture removes them.
    body = body.replace('        close_runtime()',
                        '        __teardown__(dict(locals()))\n        close_runtime()')
    ns = dict(ROOT=Path(root), __production__=production, __exercise__=exercise, __teardown__=teardown, __fake__=fake)
    exec(compile(prefix + body + '\n_v171_suite()\n', __file__, 'exec'), ns)
