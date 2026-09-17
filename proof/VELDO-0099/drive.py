#!/usr/bin/env python3
"""Drive layout, identity, and real AC4 regressions without editing the live suite."""
import ast
import contextlib
import io
import hashlib
import importlib.util
import re
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/24_veldo_0007_install_and_run.py'
source = SUITE.read_text()
baseline = '--baseline' in sys.argv
before = hashlib.sha256(SUITE.read_bytes()).hexdigest()
names = {'_iar_block', '_iar_inventory', '_iar_changed', '_iar_git', '_iar_git_dirs',
         '_iar_repository_inventory', '_iar_live_inventory', '_iar_copy_tree', '_iar_substrate',
         '_iar_copy_matches', '_iar_layout_controls', '_iar_private_paths',
         '_iar_copy_entry', '_iar_common_entries', '_iar_normalize_config',
         '_iar_copy_alternates', '_iar_resolve_alternates', '_iar_assert_isolated',
         '_iar_review_controls', '_iar_git_environment', '_iar_unquote_alternate',
         '_iar_read_alternates', '_iar_write_alternates', '_iar_alternate_paths',
         '_iar_nested_repository', '_iar_ac4', '_iar_ac4_inventory', '_iar_ac4_process', '_iar_nested_controls',
         '_iar_alternates_name_controls', '_iar_special_kind', '_iar_special_and_reflog_controls'}
if baseline:
    names -= {'_iar_ac4_inventory', '_iar_ac4_process', '_iar_alternate_paths', '_iar_nested_repository', '_iar_nested_controls',
              '_iar_alternates_name_controls', '_iar_special_kind', '_iar_special_and_reflog_controls'}
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
            ns = dict(_iar_contextlib=contextlib, _iar_io=io, _IAR_STOOD_DOWN=[], ROOT=identity_root, Path=Path, tempfile=tempfile, _iar_os=os, _iar_sp=subprocess,
                      _iar_sh=shutil, _iar_hl=hashlib, _iar_threading=threading, _iar_socket=socket, _iar_stat=stat,
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
            **({} if baseline else {
                'restore_common_allowlist': "def _iar_common_entries(common, primary): return [p for p in original_common_entries(common, primary) if p.name in {'objects', 'refs', 'packed-refs', 'shallow', 'HEAD', 'veldo', 'index', 'config', 'config.worktree'} or p.name.startswith('sharedindex.')]",
                'restore_timestamps': "def _iar_inventory(root, *, entries=None):\n    result = original_inventory(root, entries=entries)\n    return {k: (v, (Path(root) / k).lstat().st_mtime_ns) for k, v in result.items()}",
            }),
            'quotes_as_filename_characters': "def _iar_resolve_alternates(original, copied):\n    path = copied / 'info/alternates'\n    if path.exists():\n        _iar_write_alternates(path, [(original / line).resolve() for line in path.read_text().splitlines()])",
            'omit_copied_ledger': "def _iar_common_entries(common, primary): return [p for p in original_common_entries(common, primary) if p.name != 'veldo']",
            'skip_config_normalization': 'def _iar_normalize_config(common, private): pass',
            'copy_sibling_state': "def _iar_common_entries(common, primary): return list(common.iterdir())",
            'raise_on_vanished_entry': "def _iar_copy_entry(source, target, *, skip=()):\n    if source.is_dir():\n        target.mkdir(parents=True, exist_ok=True)\n        for child in source.iterdir(): _iar_copy_entry(child, target / child.name)\n        _iar_sh.copystat(source, target)\n    else: _iar_sh.copy2(source, target)",
            'omit_sparse_checkout': "def _iar_private_paths(private): return [p for p in original_private_paths(private) if p.name != 'sparse-checkout']",
            'omit_sharedindex': "def _iar_live_inventory(root):\n    result = original_live_inventory(root)\n    if _iar_git_dirs(root)[0] == _iar_git_dirs(root)[1]:\n        result = {k: v for k, v in result.items() if not k.startswith('git-dir/sharedindex.')}\n    return result",
            'skip_alternate_rewrite': 'def _iar_copy_alternates(objects, sandbox, copied=None): pass',
        }
        for case, mutation in review_mutations.items():
            rows = []
            ns = dict(_iar_contextlib=contextlib, _iar_io=io, _IAR_STOOD_DOWN=[], ROOT=identity_root, Path=Path, tempfile=tempfile, _iar_os=os,
                      _iar_sp=subprocess, _iar_sh=shutil, _iar_hl=hashlib,
                      _iar_threading=threading, _iar_socket=socket, _iar_stat=stat,
                      expect=lambda label, ok: rows.append({'label': label, 'passed': bool(ok)}))
            exec(compile(module, str(SUITE), 'exec'), ns)
            ns['original_private_paths'] = ns['_iar_private_paths']
            ns['original_inventory'] = ns['_iar_inventory']
            ns['original_live_inventory'] = ns['_iar_live_inventory']
            ns['original_common_entries'] = ns['_iar_common_entries']
            if mutation:
                exec(compile(mutation, '<' + case + '>', 'exec'), ns)
            ns['_iar_review_controls']()
            failures = [r['label'] for r in rows if not r['passed']]
            expected = {
                'review_control': [],
                'restore_common_allowlist': [r['label'] for r in rows if 'whole common directory' in r['label']],
                'restore_timestamps': [r['label'] for r in rows if 'timestamp refresh' in r['label']],
                'quotes_as_filename_characters': [r['label'] for r in rows if 'C-quoted alternate' in r['label']],
                'omit_copied_ledger': [r['label'] for r in rows if 'copied claims and runs' in r['label']],
                'skip_config_normalization': [r['label'] for r in rows if 'redirected config' in r['label']],
                'copy_sibling_state': [r['label'] for r in rows if '50 copies' in r['label'] or 'whole common directory' in r['label']],
                'raise_on_vanished_entry': [r['label'] for r in rows if 'vanishing after' in r['label']],
                'omit_sparse_checkout': ['VELDO-0099 AC3: primary sparse-checkout rule changes are observed'],
                'omit_sharedindex': ['VELDO-0099 AC3: primary split index corruption is observed'],
                'skip_alternate_rewrite': [r['label'] for r in rows if 'redirected config' in r['label'] or 'C-quoted alternate' in r['label']],
            }[case]
            assert len(rows) == (13 if baseline else 19), (case, rows)
            assert failures == expected, (case, failures, expected)
            results.append({'case': case, 'mutation': mutation, 'passed': len(rows) - len(failures),
                            'failed': len(failures), 'rows': rows})

        if not baseline:
            for case, control, mutation, count in (
                ('nested_control', '_iar_nested_controls', None, 20),
                ('restore_nested_early_return', '_iar_nested_controls',
                 'def _iar_ac4(): _iar_ac4_inventory()', 20),
                ('skip_nested_detection', '_iar_nested_controls',
                 'def _iar_nested_repository(root): return False', 20),
                ('alternates_name_control', '_iar_alternates_name_controls', None, 2),
                ('match_alternates_basename_anywhere', '_iar_alternates_name_controls',
                 'def _iar_alternate_paths(common): return list(common.rglob("alternates"))', 2),
            ):
                rows = []
                ns = dict(_iar_contextlib=contextlib, _iar_io=io, _IAR_STOOD_DOWN=[],
                          ROOT=identity_root, Path=Path, tempfile=tempfile, _iar_os=os,
                          _iar_sp=subprocess, _iar_sh=shutil, _iar_hl=hashlib,
                          _iar_threading=threading, _iar_socket=socket, _iar_stat=stat,
                          expect=lambda label, ok: rows.append({'label': label, 'passed': bool(ok)}))
                exec(compile(module, str(SUITE), 'exec'), ns)
                if mutation:
                    exec(compile(mutation, '<' + case + '>', 'exec'), ns)
                ns[control]()
                failures = [r['label'] for r in rows if not r['passed']]
                assert len(rows) == count, (case, rows)
                assert len(failures) == (10 if case == 'restore_nested_early_return' else count if mutation else 0), (case, failures)
                if case == 'skip_nested_detection':
                    assert sum('stand-down is recorded' in label for label in failures) == 10
                results.append({'case': case, 'mutation': mutation,
                                'passed': count - len(failures), 'failed': len(failures), 'rows': rows})

        if not baseline:
            for case, mutation in (
                ('special_and_reflog_control', None),
                ('restore_special_copy', "def _iar_copy_entry(source, target, *, skip=()):\n    if source.is_socket(): _iar_sh.copy2(source, target)\n    else: original_copy_entry(source, target, skip=skip)"),
                ('omit_private_reflogs', "def _iar_private_paths(private): return [p for p in original_private_paths(private) if not p.relative_to(private).as_posix().startswith('logs/refs/')]")
            ):
                rows = []
                ns['expect'] = lambda label, ok: rows.append({'label': label, 'passed': bool(ok)})
                exec(compile(module, str(SUITE), 'exec'), ns)
                ns['original_private_paths'] = ns['_iar_private_paths']
                ns['original_copy_entry'] = ns['_iar_copy_entry']
                if mutation:
                    exec(compile(mutation, '<' + case + '>', 'exec'), ns)
                ns['_iar_special_and_reflog_controls']()
                failures = [r['label'] for r in rows if not r['passed']]
                assert len(rows) == 4 and len(failures) == {
                    'special_and_reflog_control': 0, 'restore_special_copy': 2,
                    'omit_private_reflogs': 1}[case], (case, rows)
                results.append({'case': case, 'mutation': mutation, 'passed': 4 - len(failures),
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
                         'sandbox_claim_delete', 'sibling_heartbeat', 'sibling_heartbeat_shared_live',
                         'split_index', 'sandbox_reflog_delete',
                         *(() if baseline else ('sandbox_random_delete', 'split_index_reflog_delete', 'branch_alternates',
                                               'nested_only', 'nested_detached', 'nested_network',
                                               'sparse_rules', 'sparse_rules_omitted',
                                               'bound_socket', 'bound_socket_old_copy',
                                               'private_log_delete', 'private_log_delete_omitted'))):
                rows = []
                ns = dict(_iar_contextlib=contextlib, _iar_io=io, _IAR_STOOD_DOWN=[], ROOT=tree, Path=Path, tempfile=tempfile, _iar_os=os,
                          _iar_sp=subprocess, _iar_sh=shutil, _iar_hl=hashlib, _iar_threading=threading, _iar_socket=socket, _iar_stat=stat,
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
                nested_case = case.startswith('nested_')
                sparse_case = case.startswith('sparse_rules')
                if nested_case:
                    (tree / '.gitmodules').write_text('')
                    if case == 'nested_detached':
                        anchor = 'capture_output=True, text=True, timeout=timeout)'
                        assert stage_bytes.decode().count(anchor) == 1
                        stage.write_text(stage_bytes.decode().replace(
                            anchor, 'capture_output=True, text=True, timeout=timeout, start_new_session=True)'))
                    if case == 'nested_network':
                        stage.write_bytes(stage_bytes + b'\ndef network_probe():\n    return urlopen("unused")\n')
                    mutated = importlib.util.module_from_spec(spec)
                    exec(compile(stage.read_bytes(), str(stage), 'exec'), mutated.__dict__)
                    ns['IAR'] = mutated
                if sparse_case:
                    sparse_private, _ = ns['_iar_git_dirs'](tree)
                    sparse = sparse_private / 'info/sparse-checkout'
                    sparse.parent.mkdir(exist_ok=True)
                    sparse.write_text('/*\n')
                    def sparse_check(*args, **kwargs):
                        outcome = original_check(*args, **kwargs)
                        sparse.write_text('/scripts/\n')
                        return outcome
                    iar.check = sparse_check
                    if case == 'sparse_rules_omitted':
                        private_paths = ns['_iar_private_paths']
                        ns['_iar_private_paths'] = lambda private: [
                            p for p in private_paths(private) if p.name != 'sparse-checkout']
                socket_case = case.startswith('bound_socket')
                private_log_case = case.startswith('private_log_delete')
                if socket_case:
                    socket_private, socket_common = ns['_iar_git_dirs'](tree)
                    endpoint = socket_private / 'fsmonitor--daemon.ipc'
                    bound = socket.socket(socket.AF_UNIX)
                    bound.bind(str(endpoint))
                    assert ns['_iar_inventory'](socket_private)[endpoint.name] == (
                        'socket', 0, 'skipped by metadata copy')
                    if case == 'bound_socket_old_copy':
                        original_copy = ns['_iar_copy_entry']
                        def old_copy(source, target, *, skip=()):
                            if source.is_socket():
                                shutil.copy2(source, target)
                            else:
                                original_copy(source, target, skip=skip)
                        ns['_iar_copy_entry'] = old_copy
                if private_log_case:
                    private_log_dir, _ = ns['_iar_git_dirs'](tree)
                    git('update-ref', '-d', 'refs/worktree/round-eight-probe', cwd=tree)
                    git('-c', 'user.name=Veldo fixture', '-c', 'user.email=fixture@example.invalid',
                        'update-ref', '--create-reflog', 'refs/worktree/round-eight-probe', 'HEAD', cwd=tree)
                    private_log = private_log_dir / 'logs/refs/worktree/round-eight-probe'
                    assert private_log.is_file()
                    def private_log_check(*args, **kwargs):
                        outcome = original_check(*args, **kwargs)
                        private_log.unlink()
                        return outcome
                    iar.check = private_log_check
                    if case == 'private_log_delete_omitted':
                        private_paths = ns['_iar_private_paths']
                        ns['_iar_private_paths'] = lambda private: [
                            p for p in private_paths(private)
                            if not p.relative_to(private).as_posix().startswith('logs/refs/')]
                random_path = None
                split = case in ('split_index', 'split_index_reflog_delete')
                if case == 'branch_alternates':
                    git('branch', '--force', '--create-reflog', 'alternates', 'HEAD', cwd=tree)
                    _, branch_common = ns['_iar_git_dirs'](tree)
                    assert (branch_common / 'refs/heads/alternates').is_file()
                    assert (branch_common / 'logs/refs/heads/alternates').is_file()
                if split:
                    git('update-index', '--split-index', cwd=tree)
                private, common = ns['_iar_git_dirs'](tree)
                reflog = 'logs/refs/heads/round-five-probe'
                if 'reflog_delete' in case:
                    git('branch', '--force', 'round-five-probe', 'HEAD', cwd=tree)
                    assert (common / reflog).is_file()
                    reflog_bytes = (common / reflog).read_bytes()
                if case == 'sandbox_random_delete':
                    # Choose from an actual copied store; no list of allowed store names.
                    import random
                    with tempfile.TemporaryDirectory() as sample:
                        sample_tree = Path(sample) / 'repo'
                        ns['_iar_copy_tree'](tree, sample_tree)
                        _, sample_common = ns['_iar_git_dirs'](sample_tree)
                        candidates = [p.relative_to(sample_common).as_posix()
                                      for p in sample_common.rglob('*') if p.is_file()
                                      and p.relative_to(sample_common).parts[0] != 'worktrees'
                                      and not p.relative_to(sample_common).as_posix().startswith(
                                          ('logs/refs/', 'veldo/', 'sharedindex.'))
                                      and p.name not in ('HEAD', 'index', 'config', 'config.worktree')]
                        random_path = random.SystemRandom().choice(sorted(candidates))
                    random_bytes = (common / random_path).read_bytes()
                if 'reflog_delete' in case or case == 'sandbox_random_delete':
                    anchor = '    sys.exit(main())'
                    victim = random_path if random_path is not None else reflog
                    injected = ("    result = main()\n"
                                "    common = _run(['git', 'rev-parse', '--git-common-dir']).stdout.strip()\n"
                                "    (Path(common) / " + repr(victim) + ").unlink(missing_ok=" + str(baseline) + ")\n"
                                "    sys.exit(result)")
                    assert stage_bytes.decode().count(anchor) == 1
                    stage.write_text(stage_bytes.decode().replace(anchor, injected))
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
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        ns['_iar_block']('AC4', ns['_iar_ac4'])
                    if case == 'redirected_config':
                        assert stage.read_bytes() == dirty_stage
                finally:
                    iar.check = original_check
                    if socket_case:
                        bound.close()
                        endpoint.unlink()
                    if nested_case:
                        (tree / '.gitmodules').unlink()
                        stage.write_bytes(stage_bytes)
                    if sparse_case:
                        sparse.unlink()
                    if case in ('sandbox_common_write', 'sandbox_claim_delete', 'redirected_config', 'sandbox_random_delete') or 'reflog_delete' in case:
                        stage.write_bytes(stage_bytes)
                    for config, saved in saved_configs.items():
                        if saved is None:
                            config.unlink()
                        else:
                            config.write_bytes(saved)
                if split:
                    git('update-index', '--no-split-index', cwd=tree)
                if 'reflog_delete' in case:
                    assert (common / reflog).read_bytes() == reflog_bytes
                if random_path is not None:
                    assert (common / random_path).read_bytes() == random_bytes
                if case in ('sandbox_claim_delete', 'sibling_heartbeat', 'sibling_heartbeat_shared_live'):
                    assert claims.claim('probe', 'second', root=ledger_root) == (False, 'claimed')
                    assert claims.release('probe', 'first', root=ledger_root)
                failures = [r['label'] for r in rows if not r['passed']]
                expected = int((shape == 'linked' and restored) or case in
                               ('sibling_staging_shared_live', 'sandbox_common_write',
                                'sandbox_claim_delete', 'sibling_heartbeat_shared_live',
                                *(() if baseline else ('sandbox_reflog_delete', 'sandbox_random_delete', 'split_index_reflog_delete'))))
                if baseline and case == 'split_index':
                    expected = 2
                if nested_case:
                    expected = {'nested_only': 0, 'nested_detached': 2, 'nested_network': 1}[case]
                    assert len(rows) == 8, rows
                    assert len(ns['_IAR_STOOD_DOWN']) == 1
                    assert 'STANDS DOWN, recorded rather than passed' in output.getvalue()
                    assert not any('NOT ONE BYTE' in r['label'] or 'THIS repository' in r['label'] for r in rows)
                    if case == 'nested_detached':
                        assert all(any(label in r for r in failures) for label in
                                   ('STARTS NO DETACHED PROCESS', 'THE LAUNCH IS DRIVEN')), failures
                    if case == 'nested_network':
                        assert len(failures) == 1 and 'it makes no network call' in failures[0], failures
                if sparse_case:
                    expected = int(case == 'sparse_rules' or shape == 'linked')
                    if expected:
                        assert len(failures) == 1 and 'THIS repository is untouched' in failures[0], failures
                        assert 'git-dir/info/sparse-checkout' in failures[0], failures
                if socket_case:
                    expected = int(case == 'bound_socket_old_copy')
                    if expected:
                        assert len(rows) == 1 and 'No such device or address' in failures[0], rows
                if private_log_case:
                    expected = int(case == 'private_log_delete' or shape == 'linked')
                    if expected:
                        assert len(failures) == 1 and 'THIS repository is untouched' in failures[0], failures
                        assert 'git-dir/logs/refs/worktree/round-eight-probe' in failures[0], failures
                assert len(failures) == expected, (shape, case, failures)
                if expected and not nested_case and not sparse_case and not socket_case and not private_log_case and not (baseline and case == 'split_index'):
                    label = ("THE OBSERVATION'S OWN SUBSTRATE" if restored else
                             'THIS repository is untouched' if case in ('sibling_staging_shared_live', 'sibling_heartbeat_shared_live')
                             else 'NOT ONE BYTE of the repository under check')
                    assert label in failures[0], failures
                    if random_path is not None or 'reflog_delete' in case:
                        assert victim in failures[0], failures
                assert len(rows) == (1 if case == 'bound_socket_old_copy' else 8 if nested_case else 14), rows
                ac4_results.append({'shape': shape, 'case': case,
                                    'commit': git('rev-parse', 'HEAD', cwd=tree),
                                    'random_deleted_path': random_path,
                                    'stand_down': ns['_IAR_STOOD_DOWN'],
                                    'output': output.getvalue(),
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
