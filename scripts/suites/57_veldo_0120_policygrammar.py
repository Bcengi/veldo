"""Generated policy settings, refusals and complete independent qualification."""
import hashlib as _p_hash
import importlib.util as _p_import
import shutil as _p_shutil
import tempfile as _p_temp
import time as _p_time
from pathlib import Path as _p_Path

_p_started = _p_time.monotonic()
_p_fixture = ROOT / "scripts" / "fixtures"


def _p_load(name, path):
    spec = _p_import.spec_from_file_location('policy_grammar_' + name, path)
    module = _p_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_p_grammar = _p_load('grammar', _p_fixture / 'grammar_cases.py')
_p_oracle = _p_load('oracle', _p_fixture / 'yaml_oracle.py')
_p_consumer = _p_load('consumer', _p_fixture / 'policy_agreement.py')
_p_paths = {'repository': ROOT / ".veldo" / "fix_validation_record.py",
            'engine': ROOT / "engine" / ".veldo" / "fix_validation_record.py"}
_p_cases = list(_p_consumer.cases(_p_grammar))
_p_expected = _p_consumer.expected_ids(_p_grammar)
_p_cap = _p_oracle.capability()


def _p_missing(name):
    raise ModuleNotFoundError('No module named yaml', name='yaml')


def _p_broken(name):
    raise ImportError('installed oracle is broken')


class _p_RuntimeBroken:
    __version__ = 'broken'
    SafeLoader = object
    YAMLError = ValueError

    @staticmethod
    def compose(*args, **kwargs):
        raise RuntimeError('broken external parser')


with _p_temp.TemporaryDirectory(prefix='policy-readers-') as _p_directory:
    _p_readers = {}
    for _p_name, _p_path in _p_paths.items():
        # The mutation driver supplies one changed module. Keep its real sibling
        # imports alongside it without ever modifying either shipped reader.
        _p_copy = _p_Path(_p_directory) / _p_name
        _p_shutil.copytree(ROOT / '.veldo', _p_copy, ignore=_p_shutil.ignore_patterns('__pycache__'))
        (_p_copy / 'fix_validation_record.py').write_bytes(_p_path.read_bytes())
        _p_readers[_p_name] = _p_load(_p_name, _p_copy / 'fix_validation_record.py')
    _p_result = _p_consumer.run(_p_cases, _p_expected, _p_readers, _p_oracle, _p_cap)
    _p_controls = {}
    _p_controls_ok = True
    for _p_name, _p_control_cap, _p_omit in (
        ('absent', _p_oracle.capability(_p_missing), None),
        ('broken-import', _p_oracle.capability(_p_broken), None),
        ('broken-runtime', _p_oracle.capability(lambda _: _p_RuntimeBroken), None),
        ('omitted', _p_cap, 0),
    ):
        _p_control = _p_consumer.run(_p_cases, _p_expected, _p_readers, _p_oracle, _p_control_cap, omit=_p_omit)
        _p_controls[_p_name] = _p_consumer.summary(_p_control)
        _p_controls_ok &= not _p_control['qualified']
        _p_controls_ok &= all(sum(counts.values()) == len(_p_cases) - (_p_omit is not None)
                              for counts in _p_control['outcomes'].values())
        if _p_name == 'omitted':
            _p_controls_ok &= not _p_control['inventory_complete'] and not _p_control['comparison_complete']
        else:
            _p_controls_ok &= (_p_control['inventory_complete'] and _p_control['compared'] == 0
                               and _p_control['unobserved'] == len(_p_cases)
                               and _p_control['oracle_errors'] == (0 if _p_name == 'absent' else len(_p_cases))
                               and not _p_control['failures'])

_p_complete = (_p_result['inventory_complete'] and len(_p_cases) == sum(_p_expected.values())
               and {kind: len(values) for kind, values in _p_grammar.coverage_targets().items()}
               == _p_grammar.coverage_count())
if _p_cap['state'] == 'oracle_unavailable':
    print('policyread/generated-settings-agree: oracle_unavailable STANDS DOWN; independent qualification open')
expect('policyread/generated-settings-agree: supported schema-valid settings retain exact flag and start line',
       _p_complete and not any(f['expected'] is None or f['expected']['state'] == 'settings'
                              for f in _p_result['failures'])
       and (_p_cap['state'] == 'oracle_unavailable' or
            (_p_result['comparison_complete'] and _p_result['oracle_errors'] == 0)))
expect('policyread/generated-invalid-is-not-absent: syntax and schema refusals never become defaults',
       _p_complete and not any(f['expected'] and f['expected']['state'] != 'settings'
                              for f in _p_result['failures']))
_p_controls_ok &= (_p_result['qualified'] if _p_cap['state'] == 'available' else not _p_result['qualified'])
expect('policyread/generated-oracle-coverage-is-honest: absent, broken and missing-result runs cannot qualify',
       _p_controls_ok)
_p_result['implementation_digests'] = {name: _p_hash.sha256(path.read_bytes()).hexdigest()
                                       for name, path in _p_paths.items()}
_p_result['fixture_version'] = _p_grammar.DATA['revision']
_p_result['fixture_digest'] = _p_hash.sha256(b''.join((_p_fixture / p).read_bytes() for p in
    ('grammar_cases.py', 'yaml_oracle.py', 'policy_agreement.py', 'yamlish_grammar.json'))).hexdigest()
_p_result['suite_seconds'] = _p_time.monotonic() - _p_started
print('policyread/agreement: ' + json.dumps(_p_consumer.summary(_p_result), sort_keys=True))
print('policyread/oracle-controls: ' + json.dumps(_p_controls, sort_keys=True))
