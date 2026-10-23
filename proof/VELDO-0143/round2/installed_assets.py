"""VELDO-0143 round 2: the comparison suite 66's authority/installed-assets makes, without the systemd user manager
that suite needs before it reaches the row. The installer's closure derived over a whole engine copy (what an
installation records) against the closure an adopter's tree derives, that tree holding exactly the .veldo files
the scaffold lays (init_scaffold._FILES). Prints one JSON line.

    python3 proof/VELDO-0143/round2/installed_assets.py <tree>
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

root = Path(sys.argv[1])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory() as directory:
    full = Path(directory) / 'src' / '.veldo'
    shutil.copytree(root / '.veldo', full, ignore=shutil.ignore_patterns('__pycache__', '*.jsonl'))
    files = set(load('v143_assets_scaffold', full / 'init_scaffold.py')._FILES)
    laid = Path(directory) / 'laid' / '.veldo'
    (laid / 'services').mkdir(parents=True)
    for rel in sorted(files):
        if rel.startswith('.veldo/') and (rel.endswith('.py') or rel.endswith('.service')) and (full / rel[7:]).is_file():
            shutil.copyfile(full / rel[7:], laid / rel[7:])
    installed = sorted(load('v143_assets_full', full / 'control_service.py').closure())
    try:
        adopter, error = sorted(load('v143_assets_laid', laid / 'control_service.py').closure()), None
    except Exception as failure:  # noqa: BLE001 - the refusal is the finding
        adopter, error = None, '%s: %s' % (type(failure).__name__, str(failure).replace(directory, '<tmp>')[:300])
print(json.dumps({'installed': len(installed), 'not_laid': sorted(n for n in installed if '.veldo/' + n not in files),
                  'adopter': None if adopter is None else len(adopter), 'adopter_error': error,
                  'row_condition': adopter == installed and all('.veldo/' + n in files for n in installed)},
                 sort_keys=True))
