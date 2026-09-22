"""Grammar fixture qualification and independently driven assertion controls."""
import hashlib as _g_hashlib
import importlib.util as _g_importlib
import sys as _g_sys
import time as _g_time
import types as _g_types

_g_started = _g_time.monotonic()
_g_fixture = ROOT / "scripts" / "fixtures"


def _g_load(name):
    spec = _g_importlib.spec_from_file_location('fixture_' + name, _g_fixture / (name + '.py'))
    module = _g_importlib.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_g_cases = _g_load('grammar_cases')
_g_oracle = _g_load('yaml_oracle')
_g_control = globals().get('_grammar_teeth_control', False)
_g_data = _g_cases.control_domain() if _g_control else _g_cases.DATA
_g_report = _g_cases.inventory(_g_data, seconds=0 if _g_control else 60)
expect('grammar/all-bounded-derivations-exist: generated inventory equals independent count',
       _g_report['complete'] and _g_report['generated'] == _g_report['expected']['derivations'])
expect('grammar/all-boundary-edits-exist: every registry edit has all its neighbors',
       _g_report['complete'] and _g_report['rules'] == _g_report['expected']['rules']
       and set(_g_report['rules']) == set(_g_data['exclusions']))

_g_cap = _g_oracle.capability()
_g_sources = ['a: true\nb: 01\nc: -1\n', 'a: "a # b"\n', 'a: a\na: b\n']
_g_fake = _g_types.ModuleType('yamlish')
_g_previous = _g_sys.modules.get('yamlish')
_g_independent = True
try:
    _g_sys.modules['yamlish'] = _g_fake
    _g_fake.parse = lambda *args, **kwargs: {'defective': 1}
    _g_fake.front_matter = _g_fake.parse
    _g_raw = [_g_oracle.observe(source, _g_cap) for source in _g_sources]
    _g_before = [_g_oracle.answer(raw) for raw in _g_raw]
    _g_fake.parse = lambda *args, **kwargs: {'defective': 2}
    _g_fake.front_matter = _g_fake.parse
    _g_after_raw = [_g_oracle.observe(source, _g_cap) for source in _g_sources]
    _g_after = [_g_oracle.answer(raw) for raw in _g_after_raw]
    _g_independent = _g_raw == _g_after_raw and _g_before == _g_after
    if _g_cap['state'] == 'available':
        _g_independent = _g_independent and _g_before[0] == {
            'state': 'value', 'value': {'a': 'true', 'b': '01', 'c': -1}}
        _g_independent = _g_independent and _g_before[2]['state'] == 'refused'
finally:
    if _g_previous is None:
        _g_sys.modules.pop('yamlish', None)
    else:
        _g_sys.modules['yamlish'] = _g_previous
expect('grammar/oracle-is-independent: fixed defective reader cannot change observations', _g_independent)


def _g_missing(name):
    raise ModuleNotFoundError('No module named yaml', name='yaml')


def _g_broken_import(name):
    raise ImportError('installed oracle failed during import')


def _g_missing_dependency(name):
    raise ModuleNotFoundError('oracle dependency failed', name='yaml_dependency')


class _g_BrokenOracle:
    __version__ = 'broken-control'
    SafeLoader = object
    YAMLError = ValueError

    @staticmethod
    def compose(*args, **kwargs):
        raise RuntimeError('installed oracle failed at runtime')


_g_outcomes = {}
_g_honest_absence = True
for _g_consumer in ('reader', 'policy'):
    for _g_label, _g_capability in (
        ('absent', _g_oracle.capability(_g_missing)),
        ('import-failure', _g_oracle.capability(_g_broken_import)),
        ('dependency-failure', _g_oracle.capability(_g_missing_dependency)),
        ('runtime-failure', _g_oracle.capability(lambda _: _g_BrokenOracle)),
        ('installed', _g_cap),
    ):
        _g_observed = _g_oracle.consumer(_g_consumer, _g_sources, _g_capability)
        _g_outcomes[_g_consumer + '/' + _g_label] = {
            k: v for k, v in _g_observed.items() if k != 'observations'}
        _g_honest_absence &= _g_observed['agreed'] == 0 and _g_observed['state'] == 'unproven'
        if _g_label == 'installed' and _g_cap['state'] == 'available':
            _g_honest_absence &= _g_observed['compared'] == len(_g_sources) and _g_observed['unobserved'] == 0
        elif _g_label != 'installed':
            _g_honest_absence &= _g_observed['compared'] == 0 and _g_observed['unobserved'] == len(_g_sources)
            _g_honest_absence &= _g_observed['errors'] == (0 if _g_label == 'absent' else len(_g_sources))
expect('grammar/missing-oracle-is-unproven: absence and broken installation are distinct', _g_honest_absence)

# A completed inventory is a prerequisite for full observation. An interrupted
# inventory remains red and never pretends its prefix is a qualification domain.
_g_compared = 0
_g_disagreements = []
_g_observation_digest = _g_hashlib.sha256()
_g_reader_digest = _g_hashlib.sha256((ROOT / '.veldo/yamlish.py').read_bytes()).hexdigest()
_g_fixture_digest = _g_hashlib.sha256(b''.join((_g_fixture / p).read_bytes() for p in
    ('yamlish_grammar.json', 'grammar_cases.py', 'yaml_oracle.py'))).hexdigest()
_g_refusal_errors = []
_g_oracle_errors = []
if _g_report['complete'] and not _g_control:
    for _g_case in _g_cases.cases(_g_data):
        _g_inputs = [(None, _g_case['text'])] + [
            (rule, _g_cases.edit(_g_case, rule)) for rule in _g_cases.applicable(_g_case['mask'], _g_data)]
        for _g_rule, _g_text in _g_inputs:
            try:
                _g_actual = {'state': 'value', 'value': V._yamlish.parse(_g_text)}
            except ValueError as _g_error:
                _g_actual = {'state': 'refused', 'error': str(_g_error)}
            if _g_rule and _g_actual['state'] != 'refused':
                _g_refusal_errors.append({'derivation': _g_case['id'], 'edit': _g_rule,
                                          'source': _g_text, 'answer': _g_actual})
            _g_raw = _g_oracle.observe(_g_text, _g_cap)
            _g_observation_digest.update((_g_cases.encoded(_g_raw) + '\n').encode())
            if _g_raw['state'] == 'oracle_error':
                _g_oracle_errors.append(_g_raw)
            if _g_raw['state'] != 'observed':
                continue
            _g_compared += 1
            _g_expected = {'state': 'refused'} if _g_rule else _g_oracle.answer(_g_raw)
            _g_equal = (_g_actual['state'] == _g_expected['state'] and
                        (_g_actual['state'] != 'value' or _g_actual['value'] == _g_expected.get('value')))
            if not _g_equal:
                _g_disagreements.append({'source': _g_text, 'input_bytes_hex': _g_text.encode().hex(),
                    'derivation': _g_case['id'], 'production': _g_case['production'], 'edit': _g_rule,
                    'reader': _g_actual, 'oracle': _g_raw, 'dialect_answer': _g_expected})
_g_total = _g_report['expected']['derivations'] + _g_report['expected']['boundary_edits']
_g_report.update(compared=_g_compared, unobserved=_g_total - _g_compared,
                 oracle_state=_g_cap['state'], oracle_version=_g_cap.get('version'),
                 observation_digest=_g_observation_digest.hexdigest(), reader_digest=_g_reader_digest,
                 fixture_digest=_g_fixture_digest, disagreements=_g_disagreements,
                 refusal_errors=_g_refusal_errors, oracle_errors=_g_oracle_errors,
                 domain='mutation-control' if _g_control else 'baseline',
                 suite_seconds=_g_time.monotonic() - _g_started)
for _g_consumer in ('reader', 'policy'):
    if _g_cap['state'] == 'oracle_unavailable':
        print('grammar/' + _g_consumer + ': oracle_unavailable STANDS DOWN (unproven; compared=0)')
    elif not _g_report['complete']:
        print('grammar/' + _g_consumer + ': generation_incomplete; independent agreement UNPROVEN')
# Reader disagreement is evidence for the follow-up, not a change to this fixture's domain.
expect('grammar/oracle-observations-complete: installed oracle has no missing cases or crashes',
       _g_control or (_g_report['complete'] and not _g_oracle_errors and
                     (_g_cap['state'] == 'oracle_unavailable' or _g_compared == _g_total)))
print('grammar/qualification: ' + json.dumps(_g_report, sort_keys=True))
print('grammar/capability-controls: ' + json.dumps(_g_outcomes, sort_keys=True))
