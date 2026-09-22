"""Behavior tests for the single document reader; runnable with stdlib unittest."""
import importlib.util
from pathlib import Path
import unittest

_spec = importlib.util.spec_from_file_location('yamlish', Path(__file__).resolve().parents[1] / '.veldo/yamlish.py')
Y = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Y)


class ReaderTests(unittest.TestCase):
    def test_values(self):
        self.assertEqual(Y.parse('a: 0123456\nb: true # armed\nc: a#b\nd: 123\ne: "123"'),
                         dict(a='0123456', b='true', c='a#b', d=123, e='123'))
        self.assertEqual(Y.parse("a: {note: don't relax, required: true, nest: [a, {b: 2}]}"),
                         {'a': {'note': "don't relax", 'required': 'true', 'nest': ['a', {'b': 2}]}})

    def test_quotes(self):
        self.assertEqual(Y.parse('a: "a # b\\n\\u0063\\\\\\\""\nb: \'it\'\'s\''),
                         {'a': 'a # b\nc\\"', 'b': "it's"})
        for sep in ('\u2028', '\u2029', '\x85', '\v', '\f', '\x1c'):
            self.assertEqual(Y.parse('note: "hello' + sep + 'required: true"'),
                             {'note': 'hello' + sep + 'required: true'})

    def test_structure(self):
        self.assertEqual(Y.parse('items:\n  - id: AC1\n    text: first\n      second\n  - id: AC2\n    data: [1, 2]\nempty:'),
                         {'items': [{'id': 'AC1', 'text': 'first second'}, {'id': 'AC2', 'data': [1, 2]}], 'empty': None})
        self.assertEqual(Y.parse('  a:\n    b: 1\r\n  c: 2\r'), {'a': {'b': 1}, 'c': 2})
        self.assertEqual(Y.parse('a: {b: 1,\n  c: 2}'), {'a': {'b': 1, 'c': 2}})

    def test_blocks(self):
        self.assertEqual(Y.parse('note: |-\n  fix_validation:\n    required: true\nx: 1'),
                         {'note': 'fix_validation:\n  required: true', 'x': 1})
        self.assertEqual(Y.parse('note: >\n  a\n  b\n'), {'note': 'a b\n'})

    def test_blocks_preserve_physical_end_of_file(self):
        for indicator in ('|', '|+', '>', '>+'):
            self.assertEqual(Y.parse('note: ' + indicator + '\n  text'), {'note': 'text'})
            self.assertEqual(Y.parse('note: ' + indicator + '\n  text\n'), {'note': 'text\n'})

    def test_blocks_preserve_paragraphs(self):
        self.assertEqual(Y.parse('x: >-\n  first\n  line\n\n  second\n'), {'x': 'first line\nsecond'})
        self.assertEqual(Y.parse('x: |+\n  first\n\n'), {'x': 'first\n\n'})
        self.assertEqual(Y.parse('x: |-\n  first\n    indented\n  last\n'), {'x': 'first\n  indented\nlast'})

    def test_plain_paragraphs(self):
        self.assertEqual(Y.parse('text: first\n  line\n\n  second'), {'text': 'first line\nsecond'})

    def test_keys_and_lossless_writer(self):
        self.assertEqual(Y.parse('"a key": value\n.veldo/path.py: reason'), {'a key': 'value', '.veldo/path.py': 'reason'})
        self.assertEqual(Y.parse('fix_validation : {required: true}'), {'fix_validation': {'required': 'true'}})
        for value in ('0012', '123', 'a # b', 'a: b', 'it\'s', '"x"', 'a\nb', '', '[x]', 'true'):
            self.assertEqual(Y.parse('value: ' + Y.quote(value)), {'value': value})
        with self.assertRaises(Y.ParseError):
            Y.parse('a: 1\n"a": 2')

    def test_refusals(self):
        for src in ('a: 1\na: 2', 'a: {b: 1, b: 2}', 'a: [1, 2', 'a: {b: 2]','a: "no',
                    'a: "ok" junk', 'a: "bad\\q"', 'a: "x"#bad', 'a: &ref x', 'a: *ref',
                    'a: !tag x', '<<: x', 'a:\n\tb: 1', 'a: value\n  required: true',
                    'a: 1\n  b: 2', 'a: [x,,y]', 'a: [x} rest]', 'a: |2\n  x',
                    '---\na: 1', 'a: x: y', 'a: 1\n- item', 'a: "\\uD800"'):
            with self.subTest(src=src), self.assertRaises(Y.ParseError):
                Y.parse(src, 'fixture')

    def test_front_matter(self):
        self.assertIsNone(Y.front_matter('# prose'))
        self.assertEqual(Y.front_matter('\ufeff---\r\na: [x]\r\n---\r\nbody'), {'a': ['x']})
        for text in ('---\na: 1', '---\n- x\n---\n', '---\na: 1\n---oops\n'):
            with self.assertRaises(Y.ParseError):
                Y.front_matter(text)


if __name__ == '__main__':
    unittest.main()
