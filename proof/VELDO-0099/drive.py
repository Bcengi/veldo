#!/usr/bin/env python3
"""Drive the gate's real layout controls and three mutations without editing the suite."""
import ast
import hashlib
import importlib.util
import re
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/24_veldo_0007_install_and_run.py'
source = SUITE.read_text()
before = hashlib.sha256(SUITE.read_bytes()).hexdigest()
names = {'_iar_inventory', '_iar_changed', '_iar_git', '_iar_git_dirs',
         '_iar_repository_inventory', '_iar_copy_tree', '_iar_substrate',
         '_iar_copy_matches', '_iar_layout_controls'}
nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in names]
assert {n.name for n in nodes} == names
module = ast.Module(body=nodes, type_ignores=[])
mutations = {
    'control': None,
    'restore_directory_shape': '''def _iar_substrate(repo):
    return original_substrate(repo) and (repo / '.git').is_dir()
''',
    'substitute_clone_of_head': '''def _iar_copy_tree(source, target):
    _iar_git(source, 'clone', '--no-hardlinks', '-q', str(source), str(target))
''',
    'omit_external_git_inventory': '''def _iar_repository_inventory(root):
    return _iar_inventory(root)
''',
}
expected_failures = {
    'control': [],
    'restore_directory_shape': [
        'VELDO-0099 AC1: linked copied substrate resolves inside its sandbox'],
    'substitute_clone_of_head': [
        'VELDO-0099 AC2: primary copy preserves dirty stage, index, and untracked bytes',
        'VELDO-0099 AC2: linked copy preserves dirty stage, index, and untracked bytes'],
    'omit_external_git_inventory': [
        'VELDO-0099 AC3: linked private metadata write is observed',
        'VELDO-0099 AC3: linked common metadata write is observed'],
}
results = []
for case, mutation in mutations.items():
    rows = []
    ns = dict(ROOT=ROOT, Path=Path, tempfile=tempfile, _iar_os=os, _iar_sp=subprocess,
              _iar_sh=shutil, _iar_hl=hashlib,
              expect=lambda label, ok: rows.append({'label': label, 'passed': bool(ok)}))
    exec(compile(module, str(SUITE), 'exec'), ns)
    ns['original_substrate'] = ns['_iar_substrate']
    if mutation:
        exec(compile(mutation, '<' + case + '>', 'exec'), ns)
    ns['_iar_layout_controls']()
    failures = [r['label'] for r in rows if not r['passed']]
    assert len(rows) == 13, (case, rows)
    assert failures == expected_failures[case], (case, failures)
    results.append({'case': case, 'mutation': mutation, 'passed': len(rows) - len(failures),
                    'failed': len(failures), 'rows': rows})

# Drive the existing AC4 function, including its real compose-install-gate path,
# in separate disposable primary and linked checkouts of the same source commit.
ac4_results = []
constants = {'_IAR_LAUNCHERS', '_IAR_DETACHING', '_IAR_LAUNCH_OK', '_IAR_NETWORK', '_IAR_NET_CMDS'}
ac4_nodes = [n for n in ast.parse(source).body
             if (isinstance(n, ast.FunctionDef) and n.name in names | {'_iar_ac4', '_iar_dotted'})
             or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants
                                                  for t in n.targets))]
with tempfile.TemporaryDirectory(prefix='veldo-0099-ac4-') as d:
    base = Path(d)
    primary, linked = base / 'primary', base / 'linked'
    def git(*args, cwd=ROOT):
        return subprocess.run(['git', '-C', str(cwd), *args], check=True,
                              capture_output=True, text=True, timeout=60).stdout.strip()
    git('clone', '--no-hardlinks', '--no-checkout', str(ROOT), str(primary))
    git('checkout', '--detach', git('rev-parse', 'HEAD'), cwd=primary)
    git('worktree', 'add', '--detach', str(linked), 'HEAD', cwd=primary)
    old_pyc = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        for shape, tree in (('primary', primary), ('linked', linked)):
            spec = importlib.util.spec_from_file_location('iar_proof_' + shape,
                                                          tree / 'scripts/check_install_and_run.py')
            iar = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(iar)
            ok, report = iar.check(only='claude')
            assert ok, report
            for restored in (False, True):
                rows = []
                ns = dict(ROOT=tree, Path=Path, tempfile=tempfile, _iar_os=os,
                          _iar_sp=subprocess, _iar_sh=shutil, _iar_hl=hashlib,
                          _iar_ast=ast, _iar_sys=sys, _iar_re=re, IAR=iar, _IAR_REP=report,
                          expect=lambda label, ok: rows.append({'label': label, 'passed': bool(ok)}))
                exec(compile(ast.Module(body=ac4_nodes, type_ignores=[]), str(SUITE), 'exec'), ns)
                if restored:
                    ns['original_substrate'] = ns['_iar_substrate']
                    exec(compile(mutations['restore_directory_shape'], '<restore-shape>', 'exec'), ns)
                ns['_iar_ac4']()
                failures = [r['label'] for r in rows if not r['passed']]
                expected = int(shape == 'linked' and restored)
                assert len(failures) == expected, (shape, restored, failures)
                if expected:
                    assert "VELDO-0007 AC4 THE OBSERVATION'S OWN SUBSTRATE" in failures[0]
                assert len(rows) > 10, rows
                ac4_results.append({'shape': shape, 'restored_directory_assertion': restored,
                                    'commit': git('rev-parse', 'HEAD', cwd=tree),
                                    'passed': len(rows) - len(failures), 'failed': len(failures),
                                    'rows': rows})
    finally:
        sys.dont_write_bytecode = old_pyc

assert hashlib.sha256(SUITE.read_bytes()).hexdigest() == before
print(json.dumps({'commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                                  text=True).strip(),
                  'suite_sha256': before, 'suite_unchanged': True,
                  'description': 'Paired mutation controls, not a selected-suite gate claim',
                  'results': results, 'original_ac4': ac4_results}, indent=2))
