#!/usr/bin/env python3
"""Versioned grammar coverage; historical exhaustive reproduction is opt-in."""
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
# Reconciliation to the written productions; deleting a registry member cannot
# redefine the documented language into a smaller passing inventory.
REQUIRED_STYLES = {'empty', 'plain', 'single', 'double', 'literal', 'folded', 'continuation', 'escape'}
REQUIRED_CONTAINERS = {'block-map', 'block-sequence', 'flow-map', 'flow-sequence',
                       'flow-map-trailing', 'flow-sequence-trailing'}
REQUIRED_EXCLUSIONS = {'duplicate-key', 'bad-indentation', 'missing-delimiter', 'invalid-escape',
                       'unterminated-quote', 'tag', 'anchor', 'alias', 'merge-key', 'directive',
                       'multiple-documents', 'multiline-quote', 'indentation-indicator'}


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


def scalar_counts(data, flow):
    """Arithmetic lexical cardinalities, independent of scalar_options()."""
    words = [''.join(chars) for size in range(data['bounds']['payload_length'] + 1)
             for chars in itertools.product(data['alphabet'], repeat=size)]
    words += list(data['partitions'].values())
    total = sum(len(data['alphabet']) ** size
                for size in range(data['bounds']['payload_length'] + 1)) + len(data['partitions'])
    ordinary = sum(plain(word, flow) for word in words)
    single = sum(all(ord(c) >= 32 and c not in '\x7f\x85\u2028\u2029' for c in word)
                 for word in words)
    blocks = sum(all(ord(c) >= 32 and c != '\x7f' for c in word) for word in words)
    continuable = sum(plain(word) and not re.fullmatch(r'0|-?[1-9][0-9]*', word)
                      for word in words)
    counts = Counter()
    for style in data['styles']:
        if style == 'empty' and flow != 'sequence':
            counts[SCALAR] += 1
        elif style == 'plain':
            counts[SCALAR] += ordinary
        elif style in ('single', 'double', 'escape'):
            counts[SCALAR | QUOTED] += {'single': single, 'double': total,
                                        'escape': len(data['escapes'])}[style]
        elif not flow and style in ('literal', 'folded'):
            counts[SCALAR | BLOCK] += blocks * len(data['chomping']) * len(data['continuations'])
        elif not flow and style == 'continuation':
            counts[SCALAR] += continuable * len(data['continuations'])
    return counts


def expected(data):
    """Count with a feature polynomial; never call the tree/source generator."""
    @lru_cache(None)
    def count(nodes, depth, flow, root=False):
        result = Counter()
        if nodes == 1 and not root:
            result.update(scalar_counts(data, flow))
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
    required = set(data['containers']) | {'scalar/' + style for style in data['styles']}
    required |= {'key/' + key[0] for key in data['keys']}
    required |= {'extra/' + witness['id'] for witness in data['witnesses']}
    gaps = ((REQUIRED_STYLES - set(data['styles'])) |
            (REQUIRED_CONTAINERS - set(data['containers'])) |
            (REQUIRED_EXCLUSIONS - set(data['exclusions'])))
    covered = set()
    for case in cases(data):
        result['generated'] += 1
        result['extra_generated'] += isinstance(case['id'], str)
        alternatives.update(case['production'])
        covered.update('/'.join(p.split('/')[:2]) if p.startswith('scalar/') else p
                       for p in case['production'])
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
                  grammar_inventory_gap=sorted(gaps), zero_witness_productions=sorted(required - covered),
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
    parser.add_argument('--control', action='store_true', help='historical mutation-control domain')
    parser.add_argument('--legacy-exhaustive', action='store_true')
    args = parser.parse_args()
    data = control_domain() if args.control else DATA
    legacy = args.control or args.legacy_exhaustive
    if args.count:
        print(json.dumps(expected(data) if legacy else coverage_count(data), sort_keys=True))
        return
    if args.output:
        with open(args.output, 'w') as out:
            result = inventory(data, args.seconds, out) if legacy else coverage_inventory(data, out)
    else:
        result = inventory(data, args.seconds) if legacy else coverage_inventory(data)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['complete'] else 1)

# Revision 2: coverage construction over the normalized production graph.
# Legacy exhaustive helpers above remain solely for reproducing recorded evidence.
def lexical_options(data, production):
    if production in data['styles']:
        return [(label, raw, mask) for label, raw, mask in scalar_options(data)
                if label.split('/')[0] == production]
    if production.startswith('key-'):
        style = production[4:]
        return [(name, raw, 0) for name, raw, _ in data['keys']
                if ('single' if raw.startswith("'") else 'double' if raw.startswith('"') else 'plain') == style]
    return []


def coverage_targets(data=DATA):
    """Required identities come from grammar declarations, not emitted witnesses."""
    graph = data['coverage']['productions']
    targets = {'production': set(graph), 'lexical': set(), 'pair': set(), 'boundary': set()}
    sites = [('ROOT', 'root', 'document')]
    for parent, spec in graph.items():
        targets['lexical'].update((parent, label) for label, _, _ in lexical_options(data, parent))
        targets['lexical'].update((parent, 'arity/' + str(n)) for n in spec.get('arities', []))
        for slot, children in spec['slots'].items():
            sites.extend((parent, slot, child) for child in children)
            targets['pair'].update((parent, slot, child) for child in children)
    for name in data['coverage']['format_alternatives']:
        targets['lexical'].update(('format/' + name, str(i)) for i in range(len(data[name])))
    for site in sites:
        features = set(graph[site[2]]['features'])
        for rule, predicate in data['coverage']['exclusion_predicates'].items():
            if features.intersection(predicate):
                targets['boundary'].add((rule,) + site)
    return targets


def coverage_count(data=DATA):
    """Independent cardinality arithmetic: no targets, ASTs or rendering calls."""
    graph = data['coverage']['productions']
    incoming = Counter({'document': 1})
    pairs = 0
    for spec in graph.values():
        for children in spec['slots'].values():
            incoming.update(children)
            pairs += len(children)
    lexical = sum(scalar_counts(data, False).values()) + len(data['keys'])
    lexical += sum(len(spec.get('arities', [])) for spec in graph.values())
    lexical += sum(len(data[name]) for name in data['coverage']['format_alternatives'])
    boundaries = sum(incoming[p] * sum(any(f in spec['features'] for f in pred)
                     for pred in data['coverage']['exclusion_predicates'].values())
                     for p, spec in graph.items())
    return dict(production=len(graph), lexical=lexical, pair=pairs, boundary=boundaries)


def coverage_node(production, data=DATA, lexical=None, arity=1):
    graph = data['coverage']['productions']
    node = {'production': production, 'children': []}
    options = lexical_options(data, production)
    if options:
        node['atom'] = next((o for o in options if o[0] == lexical), options[0])
        return node
    spec = graph[production]
    if 'arities' in spec:
        node['arity'] = arity
    for i in range(arity if 'arities' in spec else 1):
        for slot, children in spec['slots'].items():
            # Shortest terminating completion. No production answers are consulted.
            child = ('plain' if 'plain' in children else
                     'key-plain' if 'key-plain' in children else children[0])
            sub = coverage_node(child, data)
            if slot == 'key' and i:
                sub['atom'] = lexical_options(data, child)[1]
            node['children'].append((slot, sub))
    return node


def coverage_context(node, data=DATA):
    """Shortest root path in the grammar; recursive edges need no depth bound."""
    graph = data['coverage']['productions']
    paths = [('document', [])]
    seen = set()
    for current, path in paths:
        if current == node['production']:
            for parent, slot, child in reversed(path):
                wrapper = coverage_node(parent, data)
                index = next(i for i, (s, _) in enumerate(wrapper['children']) if s == slot)
                wrapper['children'][index] = (slot, node)
                node = wrapper
            return node
        if current in seen:
            continue
        seen.add(current)
        for slot, children in graph[current]['slots'].items():
            paths.extend((child, path + [(current, slot, child)]) for child in children)
    raise ValueError('unreachable production: ' + node['production'])


def coverage_site(site, data=DATA, child_arity=1):
    parent, slot, child = site
    node = coverage_node(child, data, arity=child_arity)
    if parent == 'ROOT':
        return node
    wrapper = coverage_node(parent, data)
    index = next(i for i, (s, _) in enumerate(wrapper['children']) if s == slot)
    wrapper['children'][index] = (slot, node)
    return coverage_context(wrapper, data)


def coverage_render(node, unit=1, comment='', level=0, path=()):
    """Render the AST and carry exact production spans through composition."""
    p = node['production']
    spans = []
    text = ''

    def emit(child, child_level, child_path):
        nonlocal text
        source, records = coverage_render(child, unit, comment, child_level, child_path)
        offset = len(text)
        text += source
        spans.extend(dict(r, start=r['start'] + offset, end=r['end'] + offset) for r in records)

    if 'atom' in node:
        raw = node['atom'][1]
        text = raw.replace('\n', '\n' + ' ' * (level + unit))
    elif p in ('document', 'bom'):
        text = '\ufeff' if p == 'bom' else ''
        emit(node['children'][0][1], level, path + (0,))
        if p == 'document':
            text += '\n'
    else:
        flow = p.startswith(('flow-', 'wrapped-'))
        mapping = 'map' in p
        wrapped = p.startswith('wrapped-')
        text = ('{' if mapping else '[') if flow else ''
        values = [(i, child) for i, (slot, child) in enumerate(node['children']) if slot == 'value']
        key_nodes = [(i, child) for i, (slot, child) in enumerate(node['children']) if slot == 'key']
        for n, (i, child) in enumerate(values):
            if n:
                text += (',\n' + ' ' * (level + unit) if wrapped else ', ') if flow else '\n' + ' ' * level
            if mapping:
                ki, key = key_nodes[n]
                emit(key, level, path + (ki,))
                text += ':'
            elif not flow:
                text += '-'
            child_block = child['production'].startswith('block-')
            if child_block:
                text += '\n' + ' ' * (level + unit)
            elif mapping or not flow:
                text += ' '
            # A compact map starts after '- '; its continuation aligns there.
            child_level = level + unit if child_block else level + 2 if child['production'] == 'compact-map' else level
            start = len(text)
            emit(child, child_level, path + (i,))
            if not flow and not child_block:
                end = text.find('\n', start)
                end = len(text) if end < 0 else end
                text = text[:end] + comment + text[end:]
                for r in spans:
                    r['start'] += len(comment) if r['start'] > end else 0
                    r['end'] += len(comment) if r['end'] > end else 0
        if flow:
            text += ',' if p.endswith('trailing') and values else ''
            if wrapped and values:
                text += '\n' + ' ' * (level + unit)
            text += '}' if mapping else ']'
    spans.append({'path': path, 'production': p, 'start': 0, 'end': len(text), 'level': level})
    return text, spans


def coverage_seen(node, data=DATA, parent='ROOT', slot='root'):
    p = node['production']
    result = {'production': {p}, 'lexical': set(), 'pair': set()}
    if 'atom' in node:
        result['lexical'].add((p, node['atom'][0]))
    if 'arity' in node:
        result['lexical'].add((p, 'arity/' + str(node['arity'])))
    if parent != 'ROOT':
        result['pair'].add((parent, slot, p))
    for s, child in node['children']:
        for kind, found in coverage_seen(child, data, p, s).items():
            result[kind].update(found)
    return result


def coverage_accepted(data=DATA):
    required = coverage_targets(data)
    # Construct each target; credit is independently collected from the emitted AST.
    for p in sorted(required['production']):
        yield ('production', p), coverage_context(coverage_node(p, data), data), {}
    for p, label in sorted(required['lexical']):
        if p.startswith('format/'):
            yield ('lexical', p, label), coverage_node('document', data), {p[7:]: int(label)}
        else:
            node = coverage_node(p, data, label, int(label[6:]) if label.startswith('arity/') else 1)
            yield ('lexical', p, label), coverage_context(node, data), {}
    for site in sorted(required['pair']):
        yield ('pair',) + site, coverage_site(site, data), {}


def coverage_edit(text, span, rule):
    a, b, level = span['start'], span['end'], span['level']
    value = text[a:b]
    flow = span['production'].startswith(('flow-', 'wrapped-'))
    if rule in ('duplicate-key', 'merge-key'):
        member = 'a: b' if rule == 'duplicate-key' else '<<: {}'
        value = (value[:-1].rstrip().rstrip(',') + ', ' + member + '}') if flow else value + '\n' + ' ' * level + member
    elif rule == 'bad-indentation':
        # A tab after ': ' is separation, not indentation. Edit a physical
        # continuation line for inline block scalars and compact mappings.
        if span['production'] in ('literal', 'folded', 'continuation', 'compact-map'):
            value = value.replace('\n', '\n\t', 1)
        else:
            value = '\t' + value
    elif rule == 'missing-delimiter':
        value = value[:-1]
    elif rule == 'directive':
        value = '%YAML 1.2\n---\n' + value
    elif rule == 'multiple-documents':
        value += '---\na: a\n'
    elif rule == 'invalid-escape':
        value = '"\\q"'
    elif rule == 'unterminated-quote':
        value = value[:-1]
    elif rule == 'multiline-quote':
        value = value[:1] + '\n' + value[1:]
    elif rule == 'indentation-indicator':
        value = value[:1] + '1' + value[1:]
    elif rule == 'tag':
        value = '!thing ' + value
    elif rule == 'anchor':
        value = '&thing ' + value
    elif rule == 'alias':
        value = '*undefined'
    else:
        raise ValueError(rule)
    return text[:a] + value + text[b:]


def coverage_cases(data=DATA):
    for identity, node, fmt in coverage_accepted(data):
        options = {name: data[name][fmt.get(name, 0)] for name in data['coverage']['format_alternatives']}
        text, _ = coverage_render(node, options['indent'], options['comment'])
        seen = coverage_seen(node, data)
        seen['lexical'].update(('format/' + name, str(fmt.get(name, 0))) for name in options)
        yield {'id': identity, 'text': text.replace('\n', options['newline']), 'edit': None,
               'production': sorted(seen['production']), 'coverage': seen}
    graph = data['coverage']['productions']
    for rule, parent, slot, child in sorted(coverage_targets(data)['boundary']):
        site = (parent, slot, child)
        node = coverage_site(site, data, child_arity=2 if child == 'compact-map' and rule == 'bad-indentation' else 1)
        text, spans = coverage_render(node)
        by_path = {r['path']: r for r in spans}
        span = next(r for r in spans if r['production'] == child and
                    (not r['path'] and parent == 'ROOT' or r['path'] and
                     by_path[r['path'][:-1]]['production'] == parent and
                     # Key and value roles are distinct even with the same parent.
                     slot == ('key' if child.startswith('key-') else 'root' if parent in ('document', 'bom') else 'value')))
        assert set(graph[child]['features']).intersection(data['coverage']['exclusion_predicates'][rule])
        yield {'id': ('boundary', rule) + site, 'text': coverage_edit(text, span, rule),
               'original': text, 'edit': rule, 'site': site, 'production': [parent, child],
               'coverage': {'boundary': {(rule,) + site}}}


def coverage_inventory(data=DATA, output=None):
    started = time.monotonic()
    required = coverage_targets(data)
    seen = {kind: set() for kind in required}
    digest = hashlib.sha256()
    counts = Counter()
    for case in coverage_cases(data):
        counts['boundary' if case['edit'] else 'accepted'] += 1
        for kind, found in case['coverage'].items():
            if kind != 'boundary' or case['text'] != case['original']:
                seen[kind].update(found)
        line = encoded([case['id'], case['production'], case['edit'], case['text']]) + '\n'
        digest.update(line.encode())
        if output:
            output.write(line)
    missing = {k: sorted(required[k] - seen[k]) for k in required}
    unexpected = {k: sorted(seen[k] - required[k]) for k in required}
    expected_counts = coverage_count(data)
    target_counts = {k: len(v) for k, v in required.items()}
    return {'revision': data['revision'], 'expected_targets': expected_counts,
            'enumerated_targets': target_counts, 'covered_targets': {k: len(v) for k, v in seen.items()},
            'missing': missing, 'unexpected': unexpected, 'inputs': dict(counts),
            'complete': not any(missing.values()) and not any(unexpected.values()) and expected_counts == target_counts,
            'input_digest': digest.hexdigest(), 'generation_seconds': time.monotonic() - started}


if __name__ == '__main__':
    main()
