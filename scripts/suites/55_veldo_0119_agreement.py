"""Both shipped readers agree with every independent grammar observation."""
import hashlib as _r_hash
import importlib.util as _r_import
import time as _r_time

_r_start = _r_time.monotonic()
_r_fixture = ROOT / "scripts" / "fixtures"


def _r_load(name, path):
    spec = _r_import.spec_from_file_location('agreement_' + name, path)
    module = _r_import.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_r_cases = _r_load('cases', _r_fixture / 'grammar_cases.py')
_r_oracle = _r_load('oracle', _r_fixture / 'yaml_oracle.py')
_r_consumer = _r_load('consumer', _r_fixture / 'reader_agreement.py')
_r_paths = {'repository': ROOT / ".veldo" / "yamlish.py",
            'engine': ROOT / "engine" / ".veldo" / "yamlish.py"}
_r_readers = {name: _r_load(name, path) for name, path in _r_paths.items()}
_r_inventory = list(_r_cases.coverage_cases())
_r_coverage = _r_cases.coverage_inventory()
_r_cap = _r_oracle.capability()
_r_result = _r_consumer.run(_r_inventory, _r_readers, _r_oracle, _r_cap)
_r_result['coverage'] = _r_coverage
_r_result['implementation_digests'] = {name: _r_hash.sha256(path.read_bytes()).hexdigest()
                                       for name, path in _r_paths.items()}
_r_result['fixture_version'] = _r_cases.DATA['revision']
_r_result['grammar_digest'] = _r_hash.sha256((_r_fixture / 'yamlish_grammar.json').read_bytes()).hexdigest()
_r_result['fixture_digest'] = _r_hash.sha256(b''.join((_r_fixture / p).read_bytes() for p in
    ('grammar_cases.py', 'yaml_oracle.py', 'reader_agreement.py', 'yamlish_grammar.json'))).hexdigest()
_r_counts = _r_coverage['inputs']
_r_complete = (_r_result['inventory_complete'] and _r_coverage['complete']
               and _r_result['generated'] == sum(_r_counts.values()))
_r_supported_ok = not any(not f['edit'] for f in _r_result['failures'])
if _r_cap['state'] == 'oracle_unavailable':
    print('reader/generated-grammar-agrees: oracle_unavailable STANDS DOWN; provisioned qualification outstanding')
expect('reader/generated-grammar-agrees: both complete inventories preserve exact typed trees',
       _r_complete and _r_supported_ok and (_r_cap['state'] == 'oracle_unavailable' or
       (_r_result['compared'] == len(_r_inventory) and _r_result['oracle_errors'] == 0)))
expect('reader/generated-boundaries-refuse: every boundary refuses with source and physical line',
       _r_complete and not any(f['edit'] for f in _r_result['failures'])
       and all(n == _r_counts['boundary'] for n in _r_result['refused'].values()))


def _r_missing(name):
    raise ModuleNotFoundError('No module named yaml', name='yaml')


def _r_broken(name):
    raise ImportError('installed oracle is broken')


class _r_RuntimeBroken:
    __version__ = 'broken'
    SafeLoader = object
    YAMLError = ValueError

    @staticmethod
    def compose(*args, **kwargs):
        raise RuntimeError('broken external parser')


_r_controls = {}
_r_controls_ok = True
for _r_name, _r_control_cap, _r_omit in (
    ('absent', _r_oracle.capability(_r_missing), None),
    ('broken-import', _r_oracle.capability(_r_broken), None),
    ('broken-runtime', _r_oracle.capability(lambda _: _r_RuntimeBroken), None),
    ('omitted', _r_cap, 0),
):
    _r_control = _r_consumer.run(_r_inventory, _r_readers, _r_oracle, _r_control_cap, omit=_r_omit)
    _r_controls[_r_name] = _r_consumer.summary(_r_control)
    _r_controls_ok &= not _r_control['qualified']
    _r_controls_ok &= all(n == len(_r_inventory) - (_r_omit is not None) for n in _r_control['read'].values())
    if _r_name == 'omitted':
        _r_controls_ok &= not _r_control['inventory_complete']
    else:
        _r_controls_ok &= (_r_control['compared'] == 0 and _r_control['unobserved'] == len(_r_inventory)
                           and _r_control['inventory_complete'])
        _r_controls_ok &= _r_control['oracle_errors'] == (0 if _r_name == 'absent' else len(_r_inventory))
_r_controls_ok &= (_r_result['qualified'] if _r_cap['state'] == 'available' else not _r_result['qualified'])
expect('reader/agreement-requires-full-oracle-domain: absent, broken and omitted runs cannot qualify', _r_controls_ok)
_r_result['suite_seconds'] = _r_time.monotonic() - _r_start
print('reader/agreement: ' + json.dumps(_r_consumer.summary(_r_result), sort_keys=True))
print('reader/oracle-controls: ' + json.dumps(_r_controls, sort_keys=True))
