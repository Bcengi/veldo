#!/usr/bin/env python3
"""Drive layout, identity, and real AC4 regressions without editing the live suite."""
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
import threading

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/24_veldo_0007_install_and_run.py'
source = SUITE.read_text()
before = hashlib.sha256(SUITE.read_bytes()).hexdigest()
names = {'_iar_block', '_iar_inventory', '_iar_changed', '_iar_git', '_iar_git_dirs',
         '_iar_repository_inventory', '_iar_live_inventory', '_iar_copy_tree', '_iar_substrate',
         '_iar_copy_matches', '_iar_layout_controls', '_iar_private_paths',
         '_iar_copy_entry', '_iar_common_entries', '_iar_normalize_config',
         '_iar_copy_alternates', '_iar_resolve_alternates', '_iar_assert_isolated',
         '_iar_review_controls', '_iar_git_environment'}
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
    'restore_shared_live_inventory': '''def _iar_live_inventory(root):
    return _iar_repository_inventory(root)
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
    'restore_shared_live_inventory': [
        'VELDO-0099 AC3: primary sibling staging leaves live inventory unchanged',
        'VELDO-0099 AC3: linked sibling staging leaves live inventory unchanged'],
    'omit_external_git_inventory': [
        'VELDO-0099 AC3: linked private metadata write is observed',
        'VELDO-0099 AC3: linked common metadata write is observed'],
}
identity_environment = dict(os.environ)
with tempfile.TemporaryDirectory(prefix='veldo-0099-no-identity-') as d:
    home, identity_root = Path(d) / 'home', Path(d) / 'repo'
    home.mkdir()
    identity_root.mkdir()
    for key in list(os.environ):
        if key.startswith(('GIT_CONFIG', 'GIT_AUTHOR_', 'GIT_COMMITTER_')) or key == 'EMAIL':
            os.environ.pop(key)
    os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(home),
                      GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    try:
        subprocess.run(['git', '-C', str(identity_root), 'init', '-q'], check=True)
        for key in ('user.name', 'user.email'):
            assert subprocess.run(['git', '-C', str(identity_root), 'config', '--get', key],
                                  capture_output=True).returncode == 1
        results = []
        for case, mutation in mutations.items():
            rows = []
            ns = dict(ROOT=identity_root, Path=Path, tempfile=tempfile, _iar_os=os, _iar_sp=subprocess,
                      _iar_sh=shutil, _iar_hl=hashlib, _iar_threading=threading,
                      expect=lambda label, ok: rows.append({'label': label, 'passed': bool(ok)}))
            exec(compile(module, str(SUITE), 'exec'), ns)
            ns['original_substrate'] = ns['_iar_substrate']
            if mutation:
                exec(compile(mutation, '<' + case + '>', 'exec'), ns)
            ns['_iar_layout_controls']()
            failures = [r['label'] for r in rows if not r['passed']]
            assert len(rows) == 17, (case, rows)
            assert failures == expected_failures[case], (case, failures)
            results.append({'case': case, 'mutation': mutation, 'passed': len(rows) - len(failures),
                            'failed': len(failures), 'rows': rows})

        review_mutations = {
            'review_control': None,
            'omit_copied_ledger': "def _iar_common_entries(common, primary): return [p for p in original_common_entries(common, primary) if p.name != 'veldo']",
            'skip_config_normalization': 'def _iar_normalize_config(common, private): pass',
            'copy_sibling_state': "def _iar_common_entries(common, primary): return list(common.iterdir())",
            'raise_on_vanished_entry': "def _iar_copy_entry(source, target, *, skip=()):\n    if source.is_dir():\n        target.mkdir(parents=True, exist_ok=True)\n        for child in source.iterdir(): _iar_copy_entry(child, target / child.name)\n        _iar_sh.copystat(source, target)\n    else: _iar_sh.copy2(source, target)",
            'omit_sharedindex': "def _iar_live_inventory(root):\n    result = original_live_inventory(root)\n    if _iar_git_dirs(root)[0] == _iar_git_dirs(root)[1]:\n        result = {k: v for k, v in result.items() if not k.startswith('git-dir/sharedindex.')}\n    return result",
            'skip_alternate_rewrite': 'def _iar_copy_alternates(objects, sandbox, copied=None): pass',
        }
        for case, mutation in review_mutations.items():
            rows = []
            ns = dict(ROOT=identity_root, Path=Path, tempfile=tempfile, _iar_os=os,
                      _iar_sp=subprocess, _iar_sh=shutil, _iar_hl=hashlib,
                      _iar_threading=threading,
                      expect=lambda label, ok: rows.append({'label': label, 'passed': bool(ok)}))
            exec(compile(module, str(SUITE), 'exec'), ns)
            ns['original_live_inventory'] = ns['_iar_live_inventory']
            ns['original_common_entries'] = ns['_iar_common_entries']
            if mutation:
                exec(compile(mutation, '<' + case + '>', 'exec'), ns)
            ns['_iar_review_controls']()
            failures = [r['label'] for r in rows if not r['passed']]
            expected = {
                'review_control': [],
                'omit_copied_ledger': [r['label'] for r in rows if 'copied claims and runs' in r['label']],
                'skip_config_normalization': [r['label'] for r in rows if 'redirected config' in r['label']],
                'copy_sibling_state': [r['label'] for r in rows if '50 copies' in r['label']],
                'raise_on_vanished_entry': [r['label'] for r in rows if 'vanishing after' in r['label']],
                'omit_sharedindex': ['VELDO-0099 AC3: primary split index corruption is observed'],
                'skip_alternate_rewrite': [r['label'] for r in rows if 'redirected config' in r['label']],
            }[case]
            assert len(rows) == 9, (case, rows)
            assert failures == expected, (case, failures, expected)
            results.append({'case': case, 'mutation': mutation, 'passed': len(rows) - len(failures),
                            'failed': len(failures), 'rows': rows})

        # Reintroduce exactly the caller-config reads that prevented fixture setup.
        identity_rows = []
        ns['expect'] = lambda label, ok: identity_rows.append({'label': label, 'passed': bool(ok)})
        exec(compile(module, str(SUITE), 'exec'), ns)
        fixed_git = ns['_iar_git']
        def caller_identity(root, *args, **kwargs):
            if 'commit' in args:
                fixed_git(identity_root, 'config', 'user.name')
                fixed_git(identity_root, 'config', 'user.email')
            return fixed_git(root, *args, **kwargs)
        ns['_iar_git'] = caller_identity
        ns['_iar_block']('VELDO-0099 checkout shape controls', ns['_iar_layout_controls'])
        assert len(identity_rows) == 1 and not identity_rows[0]['passed'], identity_rows
        assert 'rather than raising' in identity_rows[0]['label'], identity_rows
        results.append({'case': 'restore_caller_identity', 'passed': 0, 'failed': 1,
                        'mutation': 'Read ROOT config user.name and user.email before fixture commit',
                        'rows': identity_rows})
    finally:
        os.environ.clear()
        os.environ.update(identity_environment)

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
            for case in ('control', 'restore_directory_shape', 'sibling_staging',
                         'sibling_staging_shared_live', 'sandbox_common_write', 'redirected_config',
                         'sandbox_claim_delete', 'sibling_heartbeat', 'sibling_heartbeat_shared_live'):
                rows = []
                ns = dict(ROOT=tree, Path=Path, tempfile=tempfile, _iar_os=os,
                          _iar_sp=subprocess, _iar_sh=shutil, _iar_hl=hashlib, _iar_threading=threading,
                          _iar_ast=ast, _iar_sys=sys, _iar_re=re, IAR=iar, _IAR_REP=report,
                          expect=lambda label, ok: rows.append({'label': label, 'passed': bool(ok)}))
                exec(compile(ast.Module(body=ac4_nodes, type_ignores=[]), str(SUITE), 'exec'), ns)
                restored = case == 'restore_directory_shape'
                if restored:
                    ns['original_substrate'] = ns['_iar_substrate']
                    exec(compile(mutations['restore_directory_shape'], '<restore-shape>', 'exec'), ns)
                original_check = iar.check
                stage = tree / 'scripts/check_install_and_run.py'
                stage_bytes = stage.read_bytes()
                saved_configs = {}
                if case == 'redirected_config':
                    private, common = ns['_iar_git_dirs'](tree)
                    for config in {common / 'config', private / 'config.worktree'}:
                        saved_configs[config] = config.read_bytes() if config.exists() else None
                    git('config', '--file', str(common / 'config'), 'extensions.worktreeConfig', 'true', cwd=tree)
                    for config in saved_configs:
                        git('config', '--file', str(config), 'core.worktree', str(tree), cwd=tree)
                    stage.write_bytes(stage_bytes + b'\n# uncommitted original stage sentinel\n')
                    dirty_stage = stage.read_bytes()
                if case.startswith('sibling_staging'):
                    sibling = base / (shape + '-' + case)
                    git('worktree', 'add', '--detach', str(sibling), 'HEAD', cwd=primary)
                    def sibling_check(*args, **kwargs):
                        outcome = original_check(*args, **kwargs)
                        (sibling / 'staging-probe').write_text(shape + case + '\n')
                        git('add', 'staging-probe', cwd=sibling)
                        return outcome
                    iar.check = sibling_check
                    if case == 'sibling_staging_shared_live':
                        ns['_iar_live_inventory'] = ns['_iar_repository_inventory']
                if case in ('sandbox_claim_delete', 'sibling_heartbeat', 'sibling_heartbeat_shared_live'):
                    claim_spec = importlib.util.spec_from_file_location('proof_claim', tree / '.veldo/claim.py')
                    claims = importlib.util.module_from_spec(claim_spec)
                    claim_spec.loader.exec_module(claims)
                    _, common = ns['_iar_git_dirs'](tree)
                    ledger_root = str(common / 'veldo')
                    assert claims.claim('probe', 'first', root=ledger_root) == (True, 'granted')
                    assert claims.claim('probe', 'second', root=ledger_root) == (False, 'claimed')
                    if case.startswith('sibling_heartbeat'):
                        sibling = base / (shape + '-' + case)
                        git('worktree', 'add', '--detach', str(sibling), 'HEAD', cwd=primary)
                        def heartbeat_check(*args, **kwargs):
                            outcome = original_check(*args, **kwargs)
                            code = "import sys; sys.path.insert(0, '.veldo'); import claim; assert claim.heartbeat('probe', 'first')"
                            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
                            env.pop('VELDO_RUNS_ROOT', None)
                            subprocess.run([sys.executable, '-c', code], cwd=sibling, env=env, check=True)
                            return outcome
                        iar.check = heartbeat_check
                        if case == 'sibling_heartbeat_shared_live':
                            ns['_iar_live_inventory'] = ns['_iar_repository_inventory']
                    else:
                        anchor = '    sys.exit(main())'
                        injected = """    common = _run(['git', 'rev-parse', '--git-common-dir']).stdout.strip()
    (Path(common) / 'veldo/claims/probe.json').unlink(missing_ok=True)
"""
                        stage.write_text(stage_bytes.decode().replace(anchor, injected + anchor))
                if case == 'sandbox_common_write':
                    anchor = '    sys.exit(main())'
                    assert stage_bytes.decode().count(anchor) == 1
                    injected = """    common = _run(['git', 'rev-parse', '--git-common-dir']).stdout.strip()
    (Path(common) / 'common-write-probe').write_text('must red the sandbox row\\n')
"""
                    stage.write_text(stage_bytes.decode().replace(anchor, injected + anchor))
                try:
                    ns['_iar_ac4']()
                    if case == 'redirected_config':
                        assert stage.read_bytes() == dirty_stage
                finally:
                    iar.check = original_check
                    if case in ('sandbox_common_write', 'sandbox_claim_delete', 'redirected_config'):
                        stage.write_bytes(stage_bytes)
                    for config, saved in saved_configs.items():
                        if saved is None:
                            config.unlink()
                        else:
                            config.write_bytes(saved)
                if case in ('sandbox_claim_delete', 'sibling_heartbeat', 'sibling_heartbeat_shared_live'):
                    assert claims.claim('probe', 'second', root=ledger_root) == (False, 'claimed')
                    assert claims.release('probe', 'first', root=ledger_root)
                failures = [r['label'] for r in rows if not r['passed']]
                expected = int((shape == 'linked' and restored) or case in
                               ('sibling_staging_shared_live', 'sandbox_common_write',
                                'sandbox_claim_delete', 'sibling_heartbeat_shared_live'))
                assert len(failures) == expected, (shape, case, failures)
                if expected:
                    label = ("THE OBSERVATION'S OWN SUBSTRATE" if restored else
                             'THIS repository is untouched' if case in ('sibling_staging_shared_live', 'sibling_heartbeat_shared_live')
                             else 'NOT ONE BYTE of the repository under check')
                    assert label in failures[0], failures
                assert len(rows) == 14, rows
                ac4_results.append({'shape': shape, 'case': case,
                                    'commit': git('rev-parse', 'HEAD', cwd=tree),
                                    'passed': len(rows) - len(failures), 'failed': len(failures),
                                    'rows': rows})
    finally:
        sys.dont_write_bytecode = old_pyc

assert hashlib.sha256(SUITE.read_bytes()).hexdigest() == before
print(json.dumps({'commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'],
                                                  text=True).strip(),
                  'suite_sha256': before, 'suite_unchanged': True,
                  'layout_environment': 'Empty HOME and XDG_CONFIG_HOME; system/global git config disabled; no identity in fixture repo or environment',
                  'description': 'Paired mutation controls, not a selected-suite gate claim',
                  'results': results, 'original_ac4': ac4_results}, indent=2))
