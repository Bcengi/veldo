#!/usr/bin/env python3
"""Compare the real corpus to frozen pre-migration readers. Never a production reader.

Run before migration: python3 scripts/parser_corpus_audit.py
The archive's definitions are loaded from Git, not copied into live source. JSON carries
all value/type differences per reader and every refusal, plus a complete corpus inventory.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import types
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = '34342c3'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = load('audit_git', ROOT / '.veldo/git_process.py')
def git_text(revision, path):
    return _git_process.check_output(['git', 'show', f'{revision}:{path}'], cwd=ROOT, text=True)


def archived_module(revision, path):
    module = types.ModuleType('archived_' + Path(path).stem)
    module.__file__ = str(ROOT / path)
    exec(compile(git_text(revision, path), path, 'exec'), module.__dict__)
    return module


Y = archived_module('6b2135a', '.veldo/yamlish.py')


def archive(path, names):
    text = _git_process.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)
    tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = {'re': re, '_KEY_RE': re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):(.*)$')}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), scope)
    return scope


def outcome(fn, arg):
    try:
        return {'value': fn(arg)}
    except ValueError as e:
        return {'refusal': str(e)}


def differences(a, b, path='$'):
    if type(a) is type(b) and isinstance(a, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            if key not in a or key not in b:
                result.append({'field': path + '.' + key, 'old': a.get(key), 'new': b.get(key),
                               'presence': 'added' if key not in a else 'removed'})
            else:
                result.extend(differences(a[key], b[key], path + '.' + key))
        return result
    if type(a) is type(b) and isinstance(a, list) and len(a) == len(b):
        return [d for i, (left, right) in enumerate(zip(a, b))
                for d in differences(left, right, f'{path}[{i}]')]
    return [] if type(a) is type(b) and a == b else [{'field': path, 'old': a, 'new': b}]


def main():
    old = archive('.veldo/validate.py', {'front_matter', 'parse_yamlish', '_split_top', '_scalar',
                                       '_parse_block', '_parse_map', '_parse_list'})
    index = archive('scripts/update_index.py', {'front_matter'})
    tracked = _git_process.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    corpus = [ROOT / p for p in tracked if len(Path(p).parts) == 2 and Path(p).parts[0] in ('specs', 'plans') and p.endswith('.md')]
    rows = []
    for p in corpus:
        text = git_text(BASE, p.relative_to(ROOT))
        m = re.match(r'^---\n(.*?)\n---', text, re.S)
        after = outcome(Y.front_matter, text)
        readers = {'validate.front_matter': outcome(old['front_matter'], text),
                   'update_index.front_matter': outcome(index['front_matter'], text)}
        if m:
            readers['validate.parse_yamlish (also release/cost readers)'] = outcome(old['parse_yamlish'], m[1])
        row = {'path': str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(text.encode()).hexdigest(),
               'has_front_matter': bool(m), 'comparisons': {}}
        for name, before in readers.items():
            delta = differences(before, after)
            if delta:
                row['comparisons'][name] = delta
        rows.append(row)
    # Configs/templates outside the historical 331-document denominator also matter.
    additional = []
    policy_reader = archived_module(BASE, '.veldo/fix_validation_record.py')
    for p in [ROOT / name for name in tracked if name.startswith('.veldo/') and name.endswith('.yaml')]:
        text = git_text(BASE, p.relative_to(ROOT))
        before = outcome(old['parse_yamlish'], text)
        after = outcome(Y.parse, text)
        row = {'path': str(p.relative_to(ROOT)), 'comparisons': differences(before, after)}
        if p.name == 'policy.yaml':
            with tempfile.TemporaryDirectory() as tmp:
                policy = Path(tmp) / 'policy.yaml'
                policy.write_text(text)
                strict_before = outcome(policy_reader.read_policy, policy)
            strict_after = outcome(lambda text: {k: v for k, v in Y.parse(text).items() if k == 'fix_validation'}, text)
            row['strict_policy_reader'] = differences(strict_before, strict_after)
        additional.append(row)
    report = {'baseline': BASE, 'parser_commit': '6b2135a',
              'documents': len(rows), 'with_front_matter': sum(r['has_front_matter'] for r in rows),
              'different': sum(bool(r['comparisons']) for r in rows), 'corpus': rows,
              'additional_yaml': additional}
    target = ROOT / 'proof/one-parser/corpus-before.json'
    target.write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n')
    refused = [r for r in rows if any(any(d['field'].startswith('$.refusal') for d in ds)
                                    for ds in r['comparisons'].values())]
    lines = ['# Parser corpus comparison before migration', '',
             f'Baseline: `{BASE}`. New reader: `6b2135a`. No caller or corpus document changed before this measurement.', '',
             f"Enumerated **{len(rows)}** real specification/plan documents; **{report['with_front_matter']}** have front matter.",
             f"**{report['different']}** differ for at least one existing reader; **{len(refused)}** are refused by the new reader.", '',
             'The JSON report lists every document, its input digest, and exact old/new values at each changed field for each reader. '
             'A refusal records the diagnostic and the old value rather than pretending the document is absent. '
             'The additional YAML section measures substrate configurations separately from the historical denominator.', '',
             '## New-reader refusals', '']
    for row in refused:
        ds = next(ds for ds in row['comparisons'].values() if any(d['field'] == '$.refusal' for d in ds))
        reason = next(d['new'] for d in ds if d['field'] == '$.refusal')
        lines.append(f"- `{row['path']}`: {reason}")
    lines += ['', '## Interpretation before migration', '',
              'Unquoted colon-bearing prose, indentation that resembles a nested mapping under a scalar, '
              'and broken flow delimiters are not accepted as text by the new reader. Those require explicit quoting '
              'or a block scalar. The old full parse is preserved in the report for review. Comments inside intended '
              'prose must become quoted content. Actual status/risk annotations must become comments, not status values. '
              'Flattened-reader differences also expose lists, numbers, and quote delimiters that used to be strings. '
              'No refusal is resolved by this report, and historical proof bindings must not be fabricated after document edits.', '']
    (target.parent / 'corpus-before.md').write_text('\n'.join(lines))
    print(f'{len(rows)} documents, {report["different"]} differ, {len(refused)} refused; report: {target}')


if __name__ == '__main__':
    main()
