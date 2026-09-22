"""Generated value properties and an independent YAML oracle for the one writer."""
import importlib.util
import itertools
import random
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Y = load('writer_yamlish', ROOT / '.veldo/yamlish.py')
try:
    import yaml
except ImportError:
    yaml = None


def differences(before, after, field='$'):
    """Compare types as well as values; report exact fields, never bool == int."""
    if type(before) is type(after) and isinstance(before, dict):
        return [d for key in sorted(before.keys() | after.keys()) for d in
                (differences(before[key], after[key], field + '.' + key)
                 if key in before and key in after else
                 [{'field': field + '.' + key, 'before': before.get(key), 'after': after.get(key),
                   'presence': 'missing' if key in before else 'added'}])]
    if type(before) is type(after) and isinstance(before, list) and len(before) == len(after):
        return [d for i, (a, b) in enumerate(zip(before, after))
                for d in differences(a, b, f'{field}[{i}]')]
    return [] if type(before) is type(after) and before == after else [
        {'field': field, 'before': before, 'after': after,
         'before_type': type(before).__name__, 'after_type': type(after).__name__}]


def generated_values():
    atoms = ['', 'Claim: the signer validates the delegation', 'a:b', '# hash', 'a # b',
             "it's", '"quoted"', '\\', '\n', '\r\n', '\t', '- item', '? question', '&anchor',
             '*alias', '!tag', '|', '>', '%directive', '@', '`', '[a, b]', '{a: b}',
             ' leading', 'trailing ', ' ', '---', '...', '0', '-12', '0123', '1.0', '1e3',
             '.nan', '.inf', 'true', 'false', 'yes', 'no', 'on', 'off', 'null', '~', '2026-09-22',
             'caf\u00e9', '\u4e16\u754c', '\U0001f680', '\u0085', '\u2028', '\u2029', '\ufeff']
    yield from atoms
    yield from (chr(i) for i in range(128))
    yield from (a + b for a, b in itertools.product(atoms, repeat=2))
    rng = random.Random(110)
    for _ in range(400):
        yield ''.join(rng.choice(atoms) for _ in range(rng.randrange(1, 9)))
    for _ in range(200):
        # Sample across all Unicode planes, excluding non-scalar surrogates.
        yield ''.join(chr(c) for c in (rng.randrange(0x110000) for _ in range(20))
                      if not 0xd800 <= c <= 0xdfff)


def generated_documents():
    for value in generated_values():
        yield {'value': value, 'list': [value, None, [], {}, [value]],
               'mapping': {value: value}, 'integer': -123, 'empty': None}

    rng = random.Random(111)
    leaves = [None, '', 0, -1, 123456789012345678901234567890, 'true', '01', 'a: b', '\n']
    def tree(depth):
        kind = rng.randrange(3) if depth else 0
        if kind == 0:
            return rng.choice(leaves)
        if kind == 1:
            return [tree(depth - 1) for _ in range(rng.randrange(5))]
        return {str(i): tree(depth - 1) for i in range(rng.randrange(5))}
    for _ in range(200):
        yield {'value': tree(5)}


class WriterTests(unittest.TestCase):
    def test_generated_round_trip(self):
        for doc in generated_documents():
            with self.subTest(value=doc['value']):
                emitted = Y.render_document(doc, 'body\n---\nunchanged')
                self.assertEqual(differences(doc, Y.front_matter(emitted)), [])
                self.assertTrue(emitted.endswith('body\n---\nunchanged'))

    @unittest.skipIf(yaml is None, 'writer/generated-real-yaml-oracle STANDS DOWN: PyYAML unavailable')
    def test_generated_real_yaml_oracle(self):
        for doc in generated_documents():
            with self.subTest(value=doc['value']):
                emitted = Y.dump(doc)
                self.assertEqual(differences(doc, yaml.safe_load(emitted)), [])
                self.assertEqual(differences(Y.parse(emitted), yaml.safe_load(emitted)), [])

    @unittest.skipIf(yaml is None, 'writer/oracle-to-writer-to-both-readers STANDS DOWN: PyYAML unavailable')
    def test_oracle_in_other_direction(self):
        # The input bytes here come from the outside implementation, not our emitter.
        for doc in itertools.islice(generated_documents(), 0, None, 7):
            external = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False)
            expected = yaml.safe_load(external)
            emitted = Y.dump(expected)
            self.assertEqual(differences(expected, Y.parse(emitted)), [])
            self.assertEqual(differences(expected, yaml.safe_load(emitted)), [])

    def test_refusals(self):
        cycle = []; cycle.append(cycle)
        for value in (True, False, 1.5, object(), ('tuple',), {1: 'key'}, '\ud800', cycle):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                Y.dump({'value': value})
        for root in ({}, [], 'scalar'):
            with self.assertRaises(ValueError):
                Y.dump(root)

    def test_tracker_guard_is_unchanged_and_precedes_writer(self):
        intake = load('writer_intake', ROOT / '.veldo/tracker_intake.py')
        for value in generated_values():
            guarded = ' '.join(''.join(' ' if ord(c) < 32 else c for c in value).split())
            doc = {'title': value, 'nested': [{'text': value}], 'list': [value], 'id': 'real'}
            for render in (intake.render_spec_markdown, intake.render_plan_markdown):
                actual = Y.front_matter(render({'front_matter': doc, 'body': 'body'}))
                self.assertEqual(actual, {'title': guarded, 'nested': [{'text': guarded}],
                                          'list': [guarded], 'id': 'real'})

    def test_oracle_catches_old_reader_based_quoting(self):
        # Deliberately reproduce the original mutual-agreement defect.
        text = 'value: true\n'
        self.assertEqual(Y.parse(text), {'value': 'true'})
        if yaml is not None:
            self.assertTrue(differences(Y.parse(text), yaml.safe_load(text)))
        self.assertEqual(Y.quote('true'), '"true"')


if __name__ == '__main__':
    unittest.main(verbosity=2)
