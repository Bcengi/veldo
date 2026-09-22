#!/usr/bin/env python3
"""Versioned finite grammar enumeration. No production or third-party imports."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import itertools
import json
from pathlib import Path
import re
import time

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / 'yamlish_grammar.json').read_text())
SCALAR, QUOTED, BLOCK, FLOW = 1, 2, 4, 8


def encoded(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'))


def payloads(data):
    for size in range(data['bounds']['payload_length'] + 1):
        for i, chars in enumerate(itertools.product(data['alphabet'], repeat=size)):
            yield f'word/{size}/{i}', ''.join(chars)
    yield from data['partitions'].items()


def plain(word, flow=False):
    return (bool(word) and word == word.strip() and
            word[0] not in ",[]{}#&*!|>'\"%@`" and
            not re.match(r"[-?:](?:\s|$)", word) and
            not re.search(r'\s#|:(?:\s|$)', word) and
            not (flow and any(c in word for c in ',[]{}')))


def double(word):
    # JSON surrogate pairs are not YAML escapes: use one Unicode escape per code point.
    return '"' + ''.join('\\U%08x' % ord(c) if ord(c) > 0xffff else
                         json.dumps(c, ensure_ascii=True)[1:-1] for c in word) + '"'


def scalar_options(data, flow=False):
    for style in data['styles']:
        if style == 'empty' and flow != 'sequence':
            yield (style, '', SCALAR)
        elif style == 'escape':
            for name in data['escapes']:
                yield ('escape/' + name, '"\\' + name + '"', SCALAR | QUOTED)
        else:
            for pid, word in payloads(data):
                label = style + '/' + pid
                if style == 'plain' and plain(word, flow):
                    yield (label, word, SCALAR)
                elif style == 'single' and all(ord(c) >= 32 and c not in '\x7f\x85\u2028\u2029' for c in word):
                    yield (label, "'" + word.replace("'", "''") + "'", SCALAR | QUOTED)
                elif style == 'double':
                    yield (label, double(word), SCALAR | QUOTED)
                elif not flow and style in ('literal', 'folded') and all(ord(c) >= 32 and c != '\x7f' for c in word):
                    for chomp in data['chomping']:
                        for lines in data['continuations']:
                            yield (label + '/' + (chomp or 'clip') + '/' + str(lines),
                                   ('|' if style == 'literal' else '>') + chomp + '\n' + '\n'.join([word] * lines),
                                   SCALAR | BLOCK)
                elif not flow and style == 'continuation' and plain(word) and not re.fullmatch(r'0|-?[1-9][0-9]*', word):
                    for lines in data['continuations']:
                        yield (label + '/' + str(lines), '\n'.join([word] * (lines + 1)), SCALAR)


def partitions(total, length):
    if length == 0:
        if total == 0:
            yield ()
    elif length == 1:
        if total >= 1:
            yield (total,)
    else:
        for first in range(1, total):
            for rest in partitions(total - first, length - 1):
                yield (first,) + rest


def key_choices(data, count):
    for keys in itertools.product(data['keys'], repeat=count):
        if len({k[2] for k in keys}) == count:
            yield keys


def expected(data):
    """Count with a feature polynomial; never call the tree/source generator."""
    @lru_cache(None)
    def count(nodes, depth, flow, root=False):
        result = Counter()
        if nodes == 1 and not root:
            result.update(mask for _, _, mask in scalar_options(data, flow))
        if depth > data['bounds']['depth']:
            return Counter()
        for kind in data['containers']:
            if root and kind.startswith('flow') or flow and kind.startswith('block'):
                continue
            nested_flow = kind.split('-')[1] if kind.startswith('flow') else False
            for arity in range(data['bounds']['children'] + 1):
                if not arity and (not nested_flow or kind.endswith('trailing')):
                    continue
                weight = sum(1 for _ in key_choices(data, arity)) if kind.split('-')[1] == 'map' else 1
                for sizes in partitions(nodes - 1, arity):
                    product = Counter({FLOW if nested_flow else 0: weight})
                    for size in sizes:
                        nxt = Counter()
                        for a, av in product.items():
                            for b, bv in count(size, depth + 1, nested_flow).items():
                                nxt[a | b] += av * bv
                        product = nxt
                    # Root map status is tracked separately from recursive features.
                    for mask, n in product.items():
                        result[mask | (16 if root and kind.split('-')[1] == 'map' else 0)] += n
        return result

    masks = Counter()
    for nodes in range(1, data['bounds']['nodes'] + 1):
        masks.update(count(nodes, 0, False, True))
    formats = len(data['indent']) * len(data['newline']) * len(data['comment'])
    base_count = sum(masks.values()) * formats
    for witness in data['witnesses']:
        masks[witness['mask']] += 1
    edits = Counter()
    for mask, n in masks.items():
        for rule in applicable(mask, data):
            edits[rule] += n * formats
    return {'base_derivations': base_count, 'extra_derivations': len(data['witnesses']) * formats,
            'derivations': sum(masks.values()) * formats, 'boundary_edits': sum(edits.values()),
            'rules': dict(sorted(edits.items())), 'feature_counts': {str(k): v * formats for k, v in sorted(masks.items())}}


def trees(data, nodes, depth=0, flow=False, root=False):
    if depth > data['bounds']['depth']:
        return
    if nodes == 1 and not root:
        for atom in scalar_options(data, flow):
            yield ('scalar', atom, ())
    for kind in data['containers']:
        if root and kind.startswith('flow') or flow and kind.startswith('block'):
            continue
        for arity in range(data['bounds']['children'] + 1):
            if not arity and (kind.startswith('block') or kind.endswith('trailing')):
                continue
            for sizes in partitions(nodes - 1, arity):
                # At the baseline bound each pool is small; no full document corpus is held.
                pools = [tuple(trees(data, size, depth + 1, kind.split('-')[1] if kind.startswith('flow') else False)) for size in sizes]
                for children in itertools.product(*pools):
                    keys = key_choices(data, arity) if kind.split('-')[1] == 'map' else [()]
                    for members in keys:
                        yield (kind, members, children)


def render(tree, unit, comment, level=0):
    """Return text and scalar spans as emitted, without searching/parsing text."""
    kind, detail, children = tree
    if kind == 'scalar':
        label, raw, mask = detail
        parts = raw.split('\n')
        text = parts[0] + ''.join('\n' + ' ' * (level + unit) + p for p in parts[1:])
        return text, [(0, len(parts[0]), mask)], mask, ['scalar/' + label]
    flow = kind.startswith('flow')
    mapping = kind.split('-')[1] == 'map'
    text, spans, mask, derivation = '', [], FLOW if flow else 0, [kind]
    if flow:
        text = '{' if mapping else '['
    for i, child in enumerate(children):
        if i:
            text += ', ' if flow else '\n'
        prefix = (detail[i][1] + ':' if mapping else '-')
        if flow and not mapping:
            prefix = ''
        child_block = child[0].startswith('block')
        if flow:
            lead = prefix + (' ' if mapping else '')
        else:
            lead = ' ' * level + prefix + ('\n' if child_block else ' ')
        childtext, childspans, childmask, childderivation = render(
            child, unit, comment, level + unit if child_block else level)
        start = len(text) + len(lead)
        text += lead + childtext
        spans.extend((start + a, start + b, m) for a, b, m in childspans)
        if not flow and not child_block:
            # A comment is on the syntax header, before any continuation.
            header_end = text.find('\n', start)
            if header_end < 0:
                header_end = len(text)
            text = text[:header_end] + comment + text[header_end:]
            spans = [(a + (len(comment) if a > header_end else 0),
                      b + (len(comment) if b > header_end else 0), m) for a, b, m in spans]
        mask |= childmask
        derivation.extend(childderivation)
        if mapping:
            derivation.append('key/' + detail[i][0])
    if flow:
        if kind.endswith('trailing'):
            text += ','
        text += '}' if mapping else ']'
        spans.insert(0, (0, len(text), FLOW))
    return text, spans, mask, derivation


def applicable(mask, data):
    conditions = {'duplicate-key': bool(mask & 16), 'merge-key': bool(mask & 16),
                  'missing-delimiter': bool(mask & FLOW), 'invalid-escape': bool(mask & QUOTED),
                  'unterminated-quote': bool(mask & QUOTED), 'multiline-quote': bool(mask & QUOTED),
                  'tag': bool(mask & SCALAR), 'anchor': bool(mask & SCALAR), 'alias': bool(mask & SCALAR),
                  'indentation-indicator': bool(mask & BLOCK)}
    return [rule for rule in data['exclusions'] if conditions.get(rule, True)]


def edit(case, rule):
    text = case['text']
    nl = case['newline']
    spans = case['spans']
    if rule == 'duplicate-key':
        return text + case['first_key'] + ': a' + nl
    if rule == 'merge-key':
        return '<<: {}' + nl + text
    if rule == 'bad-indentation':
        return '\t' + text
    if rule == 'directive':
        return '%YAML 1.2' + nl + '---' + nl + text
    if rule == 'multiple-documents':
        return text + '---' + nl + 'a: a' + nl
    if rule == 'missing-delimiter':
        position = next(b - 1 for a, b, mask in spans if mask & FLOW)
        return text[:position] + text[position + 1:]
    flag = BLOCK if rule == 'indentation-indicator' else QUOTED if rule in (
        'invalid-escape', 'unterminated-quote', 'multiline-quote') else SCALAR
    a, b, _ = next(s for s in spans if s[2] & flag)
    value = text[a:b]
    replacement = {'tag': '!thing ' + value, 'anchor': '&thing ' + value,
                   'alias': '*undefined', 'invalid-escape': '"\\q"',
                   'unterminated-quote': value[:-1], 'multiline-quote': value[:1] + nl + value[1:],
                   'indentation-indicator': value[:1] + '1' + value[1:]}[rule]
    return text[:a] + replacement + text[b:]


def extra_cases(data):
    for witness in data['witnesses']:
        for unit, nl, comment in itertools.product(data['indent'], data['newline'], data['comment']):
            text, spans, openings = '', [], []
            for token in witness['tokens']:
                if isinstance(token, str):
                    text += token.replace('\t', ' ' * unit)
                elif 'scalar' in token:
                    value = token['scalar']
                    spans.append((len(text), len(text) + len(value), SCALAR))
                    text += value
                elif 'open' in token:
                    openings.append(len(text))
                    text += token['open']
                else:
                    text += token['close']
                    spans.insert(0, (openings.pop(), len(text), FLOW))
            end = text.index('\n')
            text = text[:end] + comment + text[end:]
            spans = [(a + (len(comment) if a > end else 0),
                      b + (len(comment) if b > end else 0), m) for a, b, m in spans]
            spans = [(a + text[:a].count('\n') * (len(nl) - 1),
                      b + text[:b].count('\n') * (len(nl) - 1), m) for a, b, m in spans]
            yield {'id': 'extra/' + witness['id'], 'text': text.replace('\n', nl),
                   'spans': spans, 'mask': witness['mask'], 'production': ['extra/' + witness['id']],
                   'newline': nl, 'indent': unit, 'comment': comment, 'first_key': witness['key']}


def cases(data=DATA):
    serial = 0
    for size in range(1, data['bounds']['nodes'] + 1):
        for tree in trees(data, size, root=True):
            for unit, nl, comment in itertools.product(data['indent'], data['newline'], data['comment']):
                text, spans, mask, derivation = render(tree, unit, comment)
                if tree[0].endswith('map'):
                    mask |= 16
                # Convert offsets together with the newline encoding.
                spans = [(a + text[:a].count('\n') * (len(nl) - 1),
                          b + text[:b].count('\n') * (len(nl) - 1), m) for a, b, m in spans]
                text = text.replace('\n', nl) + nl
                serial += 1
                yield {'id': serial, 'text': text, 'spans': spans, 'mask': mask,
                       'production': derivation, 'newline': nl, 'indent': unit, 'comment': comment,
                       'first_key': tree[1][0][1] if mask & 16 else None}

    yield from extra_cases(data)


def inventory(data=DATA, seconds=60, output=None):
    started = time.monotonic()
    result = {'expected': expected(data), 'generated': 0, 'boundary_edits': 0,
              'complete': False, 'extra_generated': 0, 'rules': {}, 'alternatives': {}, 'revision': data['revision']}
    digest = hashlib.sha256()
    rules, alternatives = Counter(), Counter()
    for case in cases(data):
        result['generated'] += 1
        result['extra_generated'] += isinstance(case['id'], str)
        alternatives.update(case['production'])
        entries = [(None, case['text'])] + [(rule, edit(case, rule)) for rule in applicable(case['mask'], data)]
        for rule, text in entries:
            if rule:
                rules[rule] += 1
                result['boundary_edits'] += 1
            record = encoded([case['id'], case['production'], case['indent'], case['newline'], case['comment'], rule, text]) + '\n'
            digest.update(record.encode())
            if output:
                output.write(record)
        if seconds and time.monotonic() - started > seconds:
            break
    else:
        result['complete'] = True
    result.update(seconds=time.monotonic() - started, digest=digest.hexdigest(),
                  rules=dict(sorted(rules.items())), alternatives=dict(sorted(alternatives.items())),
                  error=None if result['complete'] else 'generation_incomplete')
    return result


def control_domain():
    """Explicit assertion-drive domain, never a substitute for baseline qualification."""
    data = json.loads(json.dumps(DATA))
    data.update(alphabet=['a'], partitions={}, escapes={'n': '\n'},
                keys=[['identifier-a', 'a', 'a'], ['identifier-b', 'b', 'b']],
                indent=[1], newline=['\n'], comment=[''], chomping=[''], continuations=[1])
    data['bounds']['payload_length'] = 0
    # Empty payload exercises both block scalar alternatives; one plain lexical witness too.
    data['partitions'] = {'text': 'a'}
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', action='store_true')
    parser.add_argument('--count', action='store_true')
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--output')
    parser.add_argument('--control', action='store_true')
    args = parser.parse_args()
    data = control_domain() if args.control else DATA
    if args.count:
        print(json.dumps(expected(data), sort_keys=True))
        return
    if args.output:
        with open(args.output, 'w') as out:
            result = inventory(data, args.seconds, out)
    else:
        result = inventory(data, args.seconds)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['complete'] else 1)


if __name__ == '__main__':
    main()
