#!/usr/bin/env python3
"""Reproduce VELDO-0123 qualification and drive its named refutations on temporary copies.

No committed artifact is ever offered to the mutation result cache. This script's output
is documentary proof only; the real stage independently measures and publishes its results.
"""
import argparse
import ast
import copy
import difflib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Q = load(ROOT / 'scripts/suites/53_veldo_0123_mutations.py', 'qualification')
SOURCE = ROOT / 'scripts/check_gate_mutations.py'


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def refutations(out):
    baseline = Q.import_gate(SOURCE)
    answers, evidence = Q.qualification(baseline, ROOT)
    write(out / 'qualification.json', dict(rows=answers, evidence=evidence))
    if not all(answers.values()):
        raise RuntimeError(answers)
    source = SOURCE.read_text()
    gate_source = (ROOT / 'scripts/verify.sh').read_text()
    mutations = []
    def add(name, row, old, new, matrix=None, shell=False):
        mutations.append((name, row, old, new, matrix, shell))
    add('omit-review-registry', Q.ROWS[0],
        "DRIVERS = ('check_teeth_mutations.py', 'check_review_mutations.py')",
        "DRIVERS = ('check_teeth_mutations.py',)")
    add('omit-teeth-registry', Q.ROWS[0],
        "DRIVERS = ('check_teeth_mutations.py', 'check_review_mutations.py')",
        "DRIVERS = ('check_review_mutations.py',)")
    add('worker-exit-as-detection', Q.ROWS[1],
        "                    if proc.returncode != 0:\n                        raise Refused('driver_error', name + ': ' + stderr.decode(errors='replace')[-2000:])",
        "                    if proc.returncode != 0:\n                        stdout = canonical({'observations': [['fixture/teeth', False], ['fixture/control', True]], 'count': 2, 'row_names': ['fixture/teeth', 'fixture/control'], 'failed_rows': ['fixture/teeth']})")
    add('disable-required-stage', Q.ROWS[0],
        'CHECK_extra="required:bash scripts/check_template_sync.sh && python3 -B scripts/check_gate_mutations.py"',
        'CHECK_extra="na:disabled mutation stage"', shell=True)
    add('accept-surviving-target', Q.ROWS[1], "            if after != [False]:", "            if False:")
    add('reset-combined-deadline', Q.ROWS[2],
        '    def check(self):\n        if time.monotonic() >= self.deadline:',
        '    def check(self):\n        self.deadline = time.monotonic() + BUDGET\n        if time.monotonic() >= self.deadline:')
    add('accept-at-deadline', Q.ROWS[2], '        if time.monotonic() >= self.deadline:',
        '        if time.monotonic() > self.deadline:')
    add('ignore-stage-status', Q.ROWS[3],
        'echo "   ${name}: FAIL"; FAIL=1; RAN=$((RAN+1))',
        'echo "   ${name}: FAIL"; FAIL=0; RAN=$((RAN+1))', shell=True)
    add('accept-removed-teeth', Q.ROWS[3], "            if after != [False]:", "            if False:")
    matrix = [entry['input'] for entry in evidence['matrix']]
    key_anchor = "    return digest({'inputs': components, 'case': case})"
    for item in matrix:
        if item in ('addition', 'deletion'):
            removed = '.veldo/untracked_import.py' if item == 'addition' else 'scripts/suites/support/transitive.py'
            edit = "    components = dict(components, files={k: v for k, v in components['files'].items() if k != " + repr(removed) + "})\n"
        elif item == 'mode':
            edit = "    components = dict(components, files={k: [0, v[1]] for k, v in components['files'].items()})\n"
        elif item.startswith('runtime:'):
            edit = "    components = dict(components, runtime={k: v for k, v in components['runtime'].items() if k != " + repr(item.split(':')[1]) + "})\n"
        elif item == 'case-definition':
            edit = "    case = dict(case, finding=0)\n"
        elif item in ('interpreter', 'history', 'schema', 'fixture-version'):
            field = {'interpreter': 'runtime', 'fixture-version': 'fixture_version'}.get(item, item)
            edit = "    components = {k: v for k, v in components.items() if k != " + repr(field) + "}\n"
        else:
            edit = "    components = dict(components, files={k: v for k, v in components['files'].items() if k != " + repr(item) + "})\n"
        add('omit-input-' + item, Q.ROWS[4], key_anchor, edit + key_anchor, item)
        # The malformed reuse policy explicitly rebinds an old observation to a new input.
        add('reuse-stale-' + item, Q.ROWS[5],
            "        path = directory / (key + '.json')",
            "        for prior in directory.glob('*.json'):\n"
            "            previous = json.loads(prior.read_text())\n"
            "            if previous['case']['identity'] == case['identity']:\n"
            "                previous.update(key=key, case=case, schema=SCHEMA, fixture_version=FIXTURE_VERSION)\n"
            "                return validate_result(previous, case, key)\n"
            "        path = directory / (key + '.json')", item)
    add('ignore-file-bytes', Q.ROWS[4],
        "hashlib.sha256(body).hexdigest()]", "'constant']", '.veldo/fixture.py')
    add('discard-all-reusable-results', Q.ROWS[5],
        'def read_record(directory, key, case):\n    try:',
        'def read_record(directory, key, case):\n    return None\n    try:')
    results = []
    for index, (name, row, old, new, single, shell) in enumerate(mutations):
        with tempfile.TemporaryDirectory(prefix='v123-falsifier-') as directory:
            repo = Path(directory)
            (repo / 'scripts').mkdir()
            shutil.copytree(ROOT / '.veldo', repo / '.veldo', ignore=shutil.ignore_patterns('__pycache__'))
            before = gate_source if shell else source
            # The shell has two catalog arms, both must propagate failure.
            count = before.count(old)
            if count != (2 if name == 'ignore-stage-status' else 1):
                raise RuntimeError((name, 'anchor count', count))
            after = before.replace(old, new)
            (repo / 'scripts/check_gate_mutations.py').write_text(source if shell else after)
            (repo / 'scripts/verify.sh').write_text(after if shell else gate_source)
            mutant = Q.import_gate(repo / 'scripts/check_gate_mutations.py')
            observed, detail = Q.qualification(mutant, repo, selected=row, matrix_only=single)
            if observed != {row: False}:
                raise RuntimeError((name, 'named assertion did not turn false', observed))
            result = dict(mutation=name, row=row, observations=observed, completed=True,
                          input=single, diff=''.join(difflib.unified_diff(before.splitlines(True),
                              after.splitlines(True), fromfile='original', tofile='mutant')),
                          evidence=detail)
            results.append(result)
            print(f'{index + 1}/{len(mutations)} {name}: {row} = false', flush=True)
            write(out / 'falsifiers.json', results)
    print('all declared falsifiers and second mutations rejected', flush=True)


def weaken(source, label):
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    replacements = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'expect' and len(node.args) == 2):
            continue
        name, condition = node.args
        name_text = ast.get_source_segment(source, name)
        if label not in name_text and not (label.startswith('ipc/signature-covers/')
                                           and 'ipc/signature-covers/' in name_text):
            continue
        start = offsets[condition.lineno - 1] + condition.col_offset
        end = offsets[condition.end_lineno - 1] + condition.end_col_offset
        replacement = ('(True if (' + name_text + ').split(":", 1)[0].split()[-1] == '
                       + repr(label) + ' else (' + source[start:end] + '))')
        replacements.append((start, end, replacement))
    if len(replacements) != 1:
        raise RuntimeError((label, 'target assertion anchor', len(replacements)))
    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def removed_teeth(out):
    module = Q.import_gate(SOURCE)
    cases = module.inventory(ROOT)
    targets = sorted({(c['driver'], c['suite'], r) for c in cases for r in c['rows']})
    with tempfile.TemporaryDirectory(prefix='v123-real-') as directory:
        repo = Path(directory) / 'input'
        module.snapshot(ROOT, repo, module.read_inputs(ROOT), module.git(ROOT, 'rev-parse', 'HEAD'))
        results = []
        control = module.run_stage(repo)
        if control['status'] != 'passed':
            raise RuntimeError(control)
        write(out / 'assertion-control.json', control)
        for driver, suite, target in targets:
            warm = module.run_stage(repo)
            if warm['status'] != 'passed' or warm['worker_invocations'] != 0:
                raise RuntimeError('prewarming did not reuse every case')
            path = repo / 'scripts/suites' / suite
            before = path.read_text()
            after = weaken(before, target)
            path.write_text(after)
            try:
                weakened = module.run_stage(repo)
            finally:
                path.write_text(before)
            invalid = weakened['invalid_results']
            matched = [r for r in invalid if r['case']['driver'] == driver and
                       target in r['case']['rows'] and r['error'] == 'mutation_survived']
            if weakened['status'] != 'failed' or not matched:
                raise RuntimeError((target, weakened))
            results.append(dict(driver=driver, target=target, prewarm=warm['reused'],
                                elapsed=weakened['elapsed'], workers=weakened['worker_invocations'],
                                diff=''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                               fromfile=suite, tofile=suite)),
                                surviving_mutations=matched))
            write(out / 'removed-teeth.json', results)
            print(f'{len(results)}/{len(targets)} {driver} {target}: mutation_survived', flush=True)
        # A no-op copy changes bytes, invalidates records, and preserves all observations.
        path = repo / 'scripts/suites/shared.py'
        path.write_text(path.read_text() + '\n# no-op qualification control\n')
        noop = module.run_stage(repo)
        if noop['status'] != 'passed' or noop['computed'] != len(cases):
            raise RuntimeError(noop)
        write(out / 'assertion-noop.json', noop)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('refutations', 'removed-teeth'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    (refutations if args.mode == 'refutations' else removed_teeth)(args.output)


if __name__ == '__main__':
    main()
