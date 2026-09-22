"""Optional test oracle. Composition precedes a separate dialect adapter.

This module deliberately imports neither production readers nor writers.
"""
import hashlib
import importlib
import re


def capability(importer=importlib.import_module):
    try:
        yaml = importer('yaml')
        return {'state': 'available', 'version': yaml.__version__, 'module': yaml}
    except ModuleNotFoundError as exc:
        state = 'oracle_unavailable' if exc.name == 'yaml' else 'oracle_error'
        return {'state': state, 'error': type(exc).__name__ + ': ' + str(exc)}
    except Exception as exc:
        return {'state': 'oracle_error', 'error': type(exc).__name__ + ': ' + str(exc)}


def mark(value):
    return {'line': value.line + 1, 'column': value.column + 1, 'index': value.index}


def structure(node, source, seen=None):
    if node is None:
        return None
    seen = set() if seen is None else seen
    if id(node) in seen:
        return {'kind': 'alias', 'start': mark(node.start_mark)}
    seen.add(id(node))
    out = {'kind': node.id, 'tag': node.tag, 'start': mark(node.start_mark),
           'end': mark(node.end_mark), 'spelling': source[node.start_mark.index:node.end_mark.index]}
    if node.id == 'scalar':
        out.update(value=node.value, style=node.style)
    elif node.id == 'mapping':
        out['pairs'] = [[structure(k, source, seen), structure(v, source, seen)] for k, v in node.value]
        out['flow_style'] = node.flow_style
    else:
        out['items'] = [structure(v, source, seen) for v in node.value]
        out['flow_style'] = node.flow_style
    return out


def observe(text, cap=None):
    cap = capability() if cap is None else cap
    result = {'source': text, 'input_sha256': hashlib.sha256(text.encode()).hexdigest(),
              'oracle_version': cap.get('version'), 'state': cap['state']}
    if cap['state'] != 'available':
        result['error'] = cap.get('error')
        return result
    yaml = cap['module']
    try:
        loader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
        node = yaml.compose(text, Loader=loader)
        result.update(state='observed', syntax='valid_yaml', tree=structure(node, text))
    except yaml.YAMLError as exc:
        result.update(state='observed', syntax='invalid_yaml', error=str(exc),
                      error_type=type(exc).__name__)
        if getattr(exc, 'problem_mark', None):
            result['location'] = mark(exc.problem_mark)
        if '\x7f' in text:
            result['literal_del'] = observe_literal_del(text, yaml)
    except Exception as exc:
        result.update(state='oracle_error', error=type(exc).__name__ + ': ' + str(exc))
    return result


def observe_literal_del(text, yaml):
    """Observe the documented plain-DEL extension without consulting a reader.

    A fresh printable code point preserves character offsets and YAML syntax.
    The original invalid-YAML observation remains the primary observation.
    Only plain scalar values may carry the substitution; keys and styled
    scalars are not covered by the written literal-DEL permission.
    """
    replacement = next(chr(n) for n in range(0xe000, 0xf900) if chr(n) not in text)
    translated = text.replace('\x7f', replacement)
    try:
        node = yaml.compose(translated, Loader=getattr(yaml, 'CSafeLoader', yaml.SafeLoader))
        tree = structure(node, translated)
    except yaml.YAMLError as exc:
        return {'state': 'refused', 'error': str(exc)}
    return {'state': 'observed', 'rule': 'literal DEL in plain/continuation styles',
            'replacement': replacement, 'source': translated, 'tree': tree}


def restore_literal_del(node, replacement, key=False):
    if node is None:
        return None
    out = dict(node)
    if node['kind'] == 'scalar':
        if replacement in node['value'] and (key or node['style']):
            raise DialectDifference('literal DEL outside plain scalar value')
        out['value'] = node['value'].replace(replacement, '\x7f')
    elif node['kind'] == 'sequence':
        out['items'] = [restore_literal_del(n, replacement) for n in node['items']]
    elif node['kind'] == 'mapping':
        out['pairs'] = [[restore_literal_del(k, replacement, True),
                         restore_literal_del(v, replacement)] for k, v in node['pairs']]
    return out


class DialectDifference(ValueError):
    pass


def adapt_node(node, key=False):
    if node is None:
        return {}
    if node['kind'] == 'scalar':
        word = node['value']
        if key or node['style']:
            return word
        if word == '':
            return None
        return int(word) if re.fullmatch(r'0|-?[1-9][0-9]*', word) else word
    if node['kind'] == 'sequence':
        return [adapt_node(child) for child in node['items']]
    if node['kind'] == 'mapping':
        result = {}
        for k, value in node['pairs']:
            if k['kind'] != 'scalar':
                raise DialectDifference('non-scalar key')
            name = adapt_node(k, key=True)
            if name in result:
                raise DialectDifference('duplicate key: ' + repr(name))
            if name == '<<':
                raise DialectDifference('merge key')
            result[name] = adapt_node(value)
        return result
    raise DialectDifference('alias')


def answer(raw):
    if raw['state'] != 'observed':
        return {'state': raw['state']}
    if raw['syntax'] != 'valid_yaml':
        extension = raw.get('literal_del', {})
        if extension.get('state') == 'observed':
            try:
                tree = restore_literal_del(extension['tree'], extension['replacement'])
                return {'state': 'value', 'value': adapt_node(tree)}
            except DialectDifference as exc:
                return {'state': 'refused', 'reason': str(exc)}
        return {'state': 'refused', 'reason': 'invalid_yaml'}
    try:
        return {'state': 'value', 'value': adapt_node(raw['tree'])}
    except DialectDifference as exc:
        return {'state': 'refused', 'reason': str(exc)}


def consumer(name, sources, cap=None):
    """Shared capability accounting for reader and policy fixture consumers."""
    result = {'consumer': name, 'generated': 0, 'compared': 0, 'unobserved': 0,
              'agreed': 0, 'errors': 0, 'state': 'unproven', 'observations': []}
    for source in sources:
        result['generated'] += 1
        raw = observe(source, cap)
        result['observations'].append(raw)
        if raw['state'] == 'observed':
            result['compared'] += 1
        else:
            result['unobserved'] += 1
            result['errors'] += raw['state'] == 'oracle_error'
    # Obtaining an observation alone says nothing about agreement with a reader.
    return result


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    cap = capability()
    total = compared = 0
    digest = hashlib.sha256()
    with open(args.inventory) as inputs, open(args.output, 'w') as output:
        for line in inputs:
            case = json.loads(line)
            raw = observe(case[-1], cap)
            record = json.dumps({'identity': case[:-1], 'raw': raw, 'answer': answer(raw)},
                                ensure_ascii=True, sort_keys=True) + '\n'
            output.write(record)
            digest.update(record.encode())
            total += 1
            compared += raw['state'] == 'observed'
    print(json.dumps({'generated': total, 'compared': compared, 'unobserved': total - compared,
                      'capability': cap['state'], 'sha256': digest.hexdigest()}))


if __name__ == '__main__':
    main()
