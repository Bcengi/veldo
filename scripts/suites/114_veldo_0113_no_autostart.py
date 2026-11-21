"""VELDO-0113: registry/state consumers, with separate absence and protocol results.

The named consumer results are printed as structured statuses. A passing protocol
assertion means no counterexample and honest stand-down propagation, NOT absence
on a host whose lifecycle qualification is incomplete.
"""
import importlib.util as _v113_import
import json as _v113_json
from pathlib import Path as _v113_Path
import shutil as _v113_shutil
import tempfile as _v113_tempfile


def _v113_run(root):
    # Explicit production/fixture anchors are consumed by the teeth driver.
    fixture_directory = ROOT / "scripts" / "fixtures"
    client = ROOT / ".veldo" / "control_client.py"
    claim = ROOT / ".veldo" / "claim.py"
    with _v113_tempfile.TemporaryDirectory(prefix='v113-source-') as temporary:
        candidate = _v113_Path(temporary)
        for tree in ('.veldo', 'engine/.veldo'):
            _v113_shutil.copytree(root / tree, candidate / tree,
                                  ignore=_v113_shutil.ignore_patterns('__pycache__'))
        _v113_shutil.copy2(client, candidate / '.veldo/control_client.py')
        _v113_shutil.copy2(claim, candidate / '.veldo/claim.py')
        _v113_shutil.copytree(fixture_directory, candidate / 'scripts/fixtures',
                              ignore=_v113_shutil.ignore_patterns('__pycache__'))
        path = candidate / 'scripts/fixtures/no_autostart.py'
        spec = _v113_import.spec_from_file_location('no_autostart_suite', path)
        module = _v113_import.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.qualify(candidate)
        return result


if 'expect' in globals():
    _v113_result = _v113_run(_v113_Path(ROOT))
    for _v113_name, _v113_row in _v113_result['rows'].items():
        print('VELDO-0113 consumer ' + _v113_name + ': ' + _v113_json.dumps(_v113_row, sort_keys=True))
        if _v113_name == 'unavailable/store-write-grant':
            expect('VELDO-0113 protocol unavailable/store-grant-gap-is-explicit',
                   _v113_row['status'] == 'GAP' and _v113_row['observation']['writable'])
        else:
            expect('VELDO-0113 protocol ' + _v113_name, _v113_row['status'] != 'FAIL')
    expect('VELDO-0113 protocol unavailable/registry-state-product-is-exact',
           _v113_result['expected'] == sorted(_v113_result['completed'])
           and len(_v113_result['completed']) == len(set(_v113_result['completed'])))
    expect('VELDO-0113 protocol unavailable/faults-preserve-all-three-rows', _v113_result['faults_ok'])
elif __name__ == '__main__':
    ROOT = _v113_Path(__file__).resolve().parents[2]
    print(_v113_json.dumps(_v113_run(ROOT)))
