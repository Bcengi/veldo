"""Complete-domain consumer of the independent VELDO-0118 fixture.

No parser or expected values live here. Each record binds both real executions
and the external observation to a derivation and byte digest. Raw observations
are retained even when YAML tags intentionally differ from dialect types.
"""
from collections import Counter
import hashlib
import json
import re


def encoded(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'))


def identity(case):
    return (tuple(case['id']), hashlib.sha256(case['text'].encode()).hexdigest())


def differences(expected, actual, field='$'):
    if type(expected) is not type(actual):
        return [{'field': field, 'expected_type': type(expected).__name__,
                 'actual_type': type(actual).__name__, 'expected': expected, 'actual': actual}]
    if isinstance(expected, dict):
        out = []
        for key in sorted(expected.keys() | actual.keys()):
            if key not in expected or key not in actual:
                out.append({'field': field + '.' + key, 'expected': expected.get(key),
                            'actual': actual.get(key), 'presence_disagreement': True})
            else:
                out.extend(differences(expected[key], actual[key], field + '.' + key))
        return out
    if isinstance(expected, list) and len(expected) == len(actual):
        return [d for i, (a, b) in enumerate(zip(expected, actual))
                for d in differences(a, b, field + '[' + str(i) + ']')]
    return [] if expected == actual else [{'field': field, 'expected_type': type(expected).__name__,
        'actual_type': type(actual).__name__, 'expected': expected, 'actual': actual}]


def qualification(report):
    return (report['oracle_state'] == 'available' and report['inventory_complete']
            and report['compared'] == report['generated'] and report['unobserved'] == 0
            and report['oracle_errors'] == 0 and not report['failures'])


def run(cases, readers, oracle, cap, omit=None):
    required = Counter(identity(case) for case in cases)
    executed = {name: Counter() for name in readers}
    report = dict(generated=len(cases), read={name: 0 for name in readers},
                  refused={name: 0 for name in readers}, compared=0, unobserved=0,
                  oracle_errors=0, oracle_state=cap['state'], oracle_version=cap.get('version'), boundary_yaml={}, failures=[], records=[])
    for index, case in enumerate(cases):
        if index == omit:
            continue
        source = 'grammar:' + encoded(case['id'])
        raw = oracle.observe(case['text'], cap)
        answer = oracle.answer(raw)
        if case['edit']:
            classification = raw.get('syntax', raw['state'])
            report['boundary_yaml'][classification] = report['boundary_yaml'].get(classification, 0) + 1
        record = dict(identity=identity(case), derivation=case['id'], production=case['production'],
                      edit=case['edit'], source=case['text'], raw=raw, expected=answer, readers={})
        if raw['state'] == 'observed':
            report['compared'] += 1
        else:
            report['unobserved'] += 1
            report['oracle_errors'] += raw['state'] == 'oracle_error'
        for name, reader in readers.items():
            executed[name][identity(case)] += 1
            report['read'][name] += 1
            failure = None
            try:
                value = reader.parse(case['text'], source)
                actual = {'state': 'value', 'value': value}
                if case['edit']:
                    failure = {'kind': 'unsupported_input_accepted'}
                elif raw['state'] == 'observed':
                    delta = differences(answer.get('value'), value)
                    if answer['state'] != 'value' or delta:
                        failure = {'kind': 'value_disagreement', 'differences': delta}
            except ValueError as exc:
                actual = {'state': 'refused', 'error': str(exc)}
                report['refused'][name] += 1
                match = re.fullmatch(re.escape(source) + r':([0-9]+): (.+)', str(exc))
                location_ok = bool(match and 1 <= int(match[1]) <= len(case['text'].splitlines()))
                if case['edit'] == 'bad-indentation' and match:
                    tab_lines = [n for n, line in enumerate(case['text'].removeprefix('\ufeff').splitlines(), 1)
                                 if '\t' in line[:len(line) - len(line.lstrip(' \t'))]]
                    location_ok &= int(match[1]) in tab_lines
                if not case['edit']:
                    failure = {'kind': 'supported_input_refused'}
                elif not location_ok:
                    failure = {'kind': 'refusal_location_disagreement'}
            record['readers'][name] = actual
            if failure:
                report['failures'].append(dict(failure, reader=name, identity=identity(case),
                    derivation=case['id'], production=case['production'], edit=case['edit'],
                    source=case['text'], actual=actual, expected=answer))
        report['records'].append(record)
    report['unobserved'] += len(cases) - len(report['records'])
    report['inventory_complete'] = all(seen == required for seen in executed.values())
    report['inventory_digest'] = hashlib.sha256(encoded(sorted(required.items())).encode()).hexdigest()
    report['executed_digests'] = {name: hashlib.sha256(encoded(sorted(seen.items())).encode()).hexdigest()
                                  for name, seen in executed.items()}
    report['qualified'] = qualification(report)
    return report


def summary(report):
    return {k: v for k, v in report.items() if k != 'records'}
