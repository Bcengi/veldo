"""Apply and prove the reviewed temporary-tree constraint, one module per commit."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('boundary304', ROOT / 'scripts/check_space_boundary.py')
boundary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boundary)
phases = json.loads((HERE / 'temporary-phases.json').read_text())

for number, (relative, replacements) in enumerate(phases.items()):
    path = ROOT / relative
    source = path.read_text()
    for replacement in replacements:
        assert replacement['old'] in source, (relative, replacement)
        source = source.replace(replacement['old'], replacement['new'], 1)
    path.write_text(source)
    files = [relative]
    if relative.startswith('engine/'):
        installed = relative.removeprefix('engine/')
        (ROOT / installed).write_text(source)
        files.append(installed)
    functions = {replacement['function'] for replacement in replacements}
    errors = boundary.problems(source, relative)
    assert not [error for error in errors if any(name + ':' in error for name in functions)], errors
    with tempfile.TemporaryDirectory(prefix='v304-outside-') as temporary:
        outside = Path(temporary) / 'unique'
        outside.write_bytes(b'only outside copy\n')
        for replacement in replacements:
            manager = eval(replacement['new'], {'tempfile': tempfile})
            with manager as directory:
                (Path(directory) / 'owned-scratch').write_text('private disposable scratch\n')
            assert not Path(directory).exists()
            assert outside.read_bytes() == b'only outside copy\n'
    # Restore one unsafe constructor in memory; its module row must turn red.
    replacement = replacements[0]
    mutant = source.replace(replacement['new'], replacement['old'], 1)
    red = [error for error in boundary.problems(mutant, relative)
           if replacement['function'] + ':' in error]
    assert red, relative
    evidence = HERE / ('temporary-' + path.stem + '.json')
    evidence.write_text(json.dumps({'module': relative, 'functions': sorted(functions),
                                   'baseline_passed': True, 'outside_unique_work_kept': True,
                                   'falsifier': replacement, 'falsifier_red': red}, indent=1) + '\n')
    files.append(str(evidence.relative_to(ROOT)))
    if number == 0:
        files += ['scripts/check_space_boundary.py', 'specs/VELDO-0304-the-boundary-check.md',
                  'proof/VELDO-0304/temporary-phases.json', 'proof/VELDO-0304/build_temporary_phases.py']
    subprocess.run(['git', 'add', *files], cwd=ROOT, check=True)
    subprocess.run(['git', '-c', 'user.name=Dmitry Grinberg', '-c', 'user.email=dmitry@bcengi.com',
                    'commit', '-m', 'VELDO-0304: constrain ' + path.stem + ' temporary cleanup to its own tree'],
                   cwd=ROOT, check=True)
