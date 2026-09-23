"""Policy envelopes over the shared grammar, plus an independent schema adapter.

This is a consumer, not a YAML parser. Rendering and edits belong to grammar_cases;
external composition and dialect interpretation belong to yaml_oracle.
"""
from collections import Counter
import hashlib
import json
import tempfile
from pathlib import Path
import time

SITES = ('root', 'fix_validation', 'required', 'from_commit')
BOOLEAN_WORDS = tuple(form for word in ('true', 'false', 'yes', 'no', 'on', 'off')
                      for form in (word, word.title(), word.upper()))
COMMITS = {'hex': 'abcdef0123456789abcdef0123456789abcdef01',
           'upper': 'ABCDEF0123456789ABCDEF0123456789ABCDEF01',
           'decimal': '1' * 40, 'leading-zero': '0' + '1' * 39,
           'zeros': '0' * 40, 'short': 'abc123', 'long': 'a' * 41,
           'branch': 'main', 'negative': '-1', 'zero': '0',
           'empty': '', 'quoted-hash': 'abc # data', 'plain-hash': 'abc#data',
           'null-word': 'null', 'null-tilde': '~'}
DEFAULT = 'required: true\nfrom_commit: 0' + '1' * 39 + '\n'


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def indent(text, width=2):
    return '\n'.join(' ' * width + line if line.strip() else line
                     for line in text.split('\n'))


def envelope(text, site, mapping=True):
    # BOM belongs to the document even when its witness moves into a policy value.
    bom = '\ufeff' if text.startswith('\ufeff') else ''
    text = text.removeprefix('\ufeff')
    nl = '\r\n' if '\r\n' in text else '\n'
    defaults = DEFAULT.replace('\n', nl)
    if site == 'root':
        body = text + ('fix_validation:' + nl + indent(defaults) if mapping else '')
    elif site == 'fix_validation':
        body = 'fix_validation:' + nl + indent(text + (defaults if mapping else ''))
    else:
        other = 'from_commit: baseline\n' if site == 'required' else 'required: true\n'
        body = 'fix_validation:' + nl + indent(other.replace('\n', nl))
        body += '  ' + site + ':' + nl + indent(text, 4)
    return bom + body


def schema(tree):
    """Independent policy schema: no production imports or accessor calls."""
    refused = {'state': 'policy_shape_refused'}
    if not isinstance(tree, dict):
        return refused
    if 'fix_validation' not in tree:
        return {'state': 'settings', 'required': False, 'from_commit': ''}
    block = tree['fix_validation']
    if not isinstance(block, dict) or not block or not {'required', 'from_commit'} & block.keys():
        return refused
    if any(type(value) not in (str, int) for value in block.values()):
        return refused
    flag = False
    if 'required' in block:
        word = str(block['required']).casefold()
        if word not in ('true', 'false', 'yes', 'no', 'on', 'off'):
            return refused
        flag = word in ('true', 'yes', 'on')
    return {'state': 'settings', 'required': flag, 'from_commit': str(block.get('from_commit', ''))}


def partitions():
    for word in BOOLEAN_WORDS:
        for style, raw in (('plain', word), ('single', "'" + word + "'"), ('double', json.dumps(word))):
            yield ('boolean', word, style), 'fix_validation: {required: ' + raw + ', from_commit: baseline}\n'
    for name, word in COMMITS.items():
        for style, raw in (('single', "'" + word + "'"), ('double', json.dumps(word))):
            yield ('commit', name, style), 'fix_validation: {required: true, from_commit: ' + raw + '}\n'
        if name not in ('empty', 'quoted-hash'):
            yield ('commit', name, 'plain'), 'fix_validation: {required: true, from_commit: ' + word + '}\n'
    for name, text in {
        'absent': '', 'unrelated': 'other: yes\n',
        'required-absent': 'fix_validation: {from_commit: abc}\n',
        'start-absent': 'fix_validation: {required: true}\n',
        'root-list': '- true\n', 'root-scalar': 'true\n',
        'block-empty': 'fix_validation: {}\n', 'block-null': 'fix_validation:\n',
        'block-scalar': 'fix_validation: true\n', 'block-list': 'fix_validation: [true]\n',
        'neither-setting': 'fix_validation: {note: yes}\n',
        'unknown-nested': 'fix_validation: {required: true, note: {a: b}}\n',
    }.items():
        yield ('shape', name), text
    for style in ('plain', 'single', 'double'):
        quote = lambda word: word if style == 'plain' else repr(word) if style == 'single' else json.dumps(word)
        for form in ('block', 'flow', 'bom', 'crlf'):
            block = (quote('required') + ': YES, ' + quote('from_commit') + ': \"abc # data\"')
            text = quote('fix_validation') + ': {' + block + '}\n'
            if form == 'block':
                text = quote('fix_validation') + ':\n  ' + block.replace(', ', '\n  ') + '\n'
            if form == 'bom':
                text = '\ufeff' + text
            if form == 'crlf':
                text = text.replace('\n', '\r\n')
            yield ('keys', style, form), text
    for site in ('required', 'from_commit'):
        for name, value in (('map', '{}'), ('list', '[]'), ('null', ''), ('integer', '1'),
                            ('unknown', 'maybe'), ('quoted-empty', '""')):
            yield ('shape', site, name), 'fix_validation: {' + site + ': ' + value + '}\n'


def expected_ids(grammar):
    targets = grammar.coverage_targets()
    witnesses = [('production', p) for p in sorted(targets['production'])]
    witnesses += [('lexical',) + x for x in sorted(targets['lexical'])]
    witnesses += [('pair',) + x for x in sorted(targets['pair'])]
    witnesses += [('boundary',) + x for x in sorted(targets['boundary'])]
    ids = [('witness', site) + w for w in witnesses for site in SITES]
    ids += [('scalar', site, label) for label, _, _ in grammar.scalar_options(grammar.DATA)
            for site in ('required', 'from_commit')]
    ids += [('partition',) + key for key, _ in partitions()]
    return Counter(ids)


def cases(grammar):
    for witness in grammar.coverage_cases():
        # Supported roots are block mappings or sequences. Inspect grammar text,
        # never a production parse or result, to choose the envelope completion.
        mapping = not witness.get('original', witness['text']).removeprefix('\ufeff').lstrip().startswith('-')
        for site in SITES:
            yield dict(id=('witness', site) + tuple(witness['id']), site=site,
                       text=envelope(witness['text'], site, mapping), edit=witness['edit'])
    # Scalar lexical witnesses also occupy the settings directly: enclosing a
    # complete grammar document there intentionally exercises invalid map/list shapes.
    for label, raw, mask in grammar.scalar_options(grammar.DATA):
        node = {'production': label.split('/')[0], 'atom': (label, raw, mask), 'children': []}
        source, _ = grammar.coverage_render(node, unit=2, level=2)
        for site in ('required', 'from_commit'):
            other = 'from_commit: baseline' if site == 'required' else 'required: true'
            yield dict(id=('scalar', site, label), site=site, edit=None,
                       text='fix_validation:\n  ' + other + '\n  ' + site + ': ' + source + '\n')
    for key, text in partitions():
        yield dict(id=('partition',) + key, site='schema', text=text, edit='root-scalar' if key == ('shape', 'root-scalar') else None)


def qualification(report):
    return (report['oracle_state'] == 'available' and report['inventory_complete']
            and report['comparison_complete'] and not report['failures']
            and report['unobserved'] == 0 and report['oracle_errors'] == 0)


def run(cases, expected, readers, oracle, cap, omit=None, retain=False):
    started = time.monotonic()
    executed = {name: Counter() for name in readers}
    compared = Counter()
    report = dict(generated=len(cases), oracle_state=cap['state'], oracle_version=cap.get('version'),
                  compared=0, unobserved=0, oracle_errors=0, failures=[], records=[],
                  outcomes={name: Counter() for name in readers}, boundary_yaml=Counter())
    with tempfile.TemporaryDirectory(prefix='policy-grammar-') as directory:
        path = Path(directory) / 'policy.yaml'
        for index, case in enumerate(cases):
            if index == omit:
                continue
            key = tuple(case['id'])
            raw = oracle.observe(case['text'], cap)
            answer = oracle.answer(raw)
            wanted = ({'state': 'syntax_refused'} if case['edit'] else
                      schema(answer['value']) if answer['state'] == 'value' else None)
            if raw['state'] == 'observed':
                compared[key] += 1
                report['compared'] += 1
            else:
                report['unobserved'] += 1
                report['oracle_errors'] += raw['state'] == 'oracle_error'
            if case['edit']:
                report['boundary_yaml'][raw.get('syntax', raw['state'])] += 1
            record = dict(identity=key, input_sha256=hashlib.sha256(case['text'].encode()).hexdigest(),
                          source=case['text'], edit=case['edit'], expected=wanted, readers={})
            if retain:
                record['raw'] = raw
            path.write_bytes(case['text'].encode())
            for name, reader in readers.items():
                executed[name][key] += 1
                # With no oracle, still require grammar acceptance/refusal and
                # schema enforcement. This is explicitly NOT independent agreement.
                local_expected = wanted
                if local_expected is None and raw['state'] != 'observed':
                    try:
                        local_expected = schema(reader._yamlish.parse(case['text']))
                    except ValueError:
                        local_expected = {'state': 'syntax_refused'}
                try:
                    policy = reader.read_policy(path)
                    actual = dict(state='settings', required=reader.flag_from_policy(policy),
                                  from_commit=reader.start_line_from_policy(policy))
                except reader.ValidationError as exc:
                    actual = {'state': 'syntax_refused' if isinstance(exc.__cause__, ValueError)
                              else 'policy_shape_refused'}
                report['outcomes'][name][actual['state']] += 1
                record['readers'][name] = actual
                if actual != local_expected or (not case['edit'] and actual['state'] == 'syntax_refused'):
                    report['failures'].append(dict(identity=key, reader=name, expected=local_expected,
                        actual=actual, kind='setting_disagreement', edit=case['edit'], source=case['text']))
            if retain:
                report['records'].append(record)
    report['unobserved'] += len(cases) - sum(executed[next(iter(readers))].values())
    report['inventory_complete'] = all(seen == expected for seen in executed.values())
    report['comparison_complete'] = compared == expected
    digest = lambda counts: hashlib.sha256(encoded(sorted(counts.items())).encode()).hexdigest()
    report['expected_digest'] = digest(expected)
    report['executed_digests'] = {name: digest(seen) for name, seen in executed.items()}
    report['compared_digest'] = digest(compared)
    report['qualified'] = qualification(report)
    report['seconds'] = time.monotonic() - started
    return report


def summary(report):
    return {key: value for key, value in report.items() if key != 'records'}
