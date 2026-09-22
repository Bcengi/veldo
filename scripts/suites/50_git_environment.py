"""The single Git boundary ignores ambient repository and configuration selectors."""
import importlib.util as _g_ilu
import os as _g_os
import tempfile as _g_tmp
from pathlib import Path as _g_Path


def _g_load(name, path):
    spec = _g_ilu.spec_from_file_location(name, path)
    mod = _g_ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_g_boundary = _g_load('boundary_check', ROOT / 'scripts/check_git_boundary.py')
_g_git = _g_load('shared_git', ROOT / '.veldo/git_process.py')
_g_enroll = _g_load('git_enroll', ROOT / '.veldo/control_enrollment.py')
_g_record = _g_load('git_record', ROOT / '.veldo/fix_validation_record.py')
_g_fix = _g_load('git_fix', ROOT / '.veldo/fix_validation.py')
expect('git-boundary/no-private-git-invocations', not _g_boundary.check(ROOT))
expect('git-boundary/raw-call-mutations-are-rejected', all(_g_boundary.problems(src) for src in (
    'subprocess.run(["git", "status"])',
    'from subprocess import run as invoke\ninvoke(["git", "status"])',
    'cmd = ["git", "status"]\nsubprocess.run(cmd)',
    'subprocess.check_output(["git"] + args)',
    'subprocess.run("git status", shell=True)',
    'os.system("git status")',
    'subprocess.run(["/usr/bin/git", "status"])',
)))
with _g_tmp.TemporaryDirectory(prefix='git-boundary-') as _g_d:
    _g_root = _g_Path(_g_d)
    _g_repos = [_g_root / 'A', _g_root / 'B']
    for _g_repo in _g_repos:
        _g_repo.mkdir()
        for args in (['init', '-q'],):
            _g_git.run(['git', '-C', str(_g_repo), *args], check=True)
        (_g_repo / 'identity').write_text(_g_repo.name)
        _g_git.run(['git', '-C', str(_g_repo), 'add', '.'], check=True)
        _g_git.run(['git', '-C', str(_g_repo), 'commit', '-qm', 'root'],
                   identity=('test', 'test@example.invalid'), check=True)
    _g_a, _g_b = _g_repos
    _g_before = _g_enroll.workspace_identity(_g_a)
    # A malformed global config demonstrably changes raw Git's answer. Disabling
    # config discovery must work even when no GIT_* selectors are present.
    _g_home = _g_root / 'home'; _g_home.mkdir()
    (_g_home / '.gitconfig').write_text('this is not git configuration\n')
    _g_home_env = {key: value for key, value in _g_os.environ.items() if not key.startswith('GIT_')}
    _g_home_env.update(HOME=str(_g_home), XDG_CONFIG_HOME=str(_g_home))
    _g_raw_home = subprocess.run(['git', '-C', str(_g_a), 'rev-list', '--max-parents=0', 'HEAD'],
                                capture_output=True, env=_g_home_env)
    _g_clean_home = _g_git.run(['git', '-C', str(_g_a), 'rev-list', '--max-parents=0', 'HEAD'],
                              capture_output=True, text=True, env=_g_home_env)
    expect('git-boundary/home-configuration-is-neutralized-without-git-selectors',
           _g_raw_home.returncode != 0 and _g_clean_home.returncode == 0
           and _g_clean_home.stdout.strip() == _g_before['root_commits'][0])
    _g_env = dict(_g_os.environ)
    try:
        _g_os.environ.update(HOME=str(_g_home), XDG_CONFIG_HOME=str(_g_home),
                             GIT_DIR=str(_g_b / '.git'), GIT_WORK_TREE=str(_g_b),
                             GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.bare', GIT_CONFIG_VALUE_0='true')
        _g_after = _g_enroll.workspace_identity(_g_a)
        _g_commit = _g_before['root_commits'][0]
        _g_history = _g_record.bundle_landed_at(_g_a, 'identity')
        _g_export = _g_root / 'export'
        _g_fix._checkout(_g_a, _g_commit, _g_export)
        _g_ar = (_g_export / 'identity').read_text()
        _g_exists = _g_record._commit_exists(_g_a, _g_commit)
        _g_root_read = _g_record._git_root(_g_a)
        _g_head = _g_record._git(_g_a, 'rev-parse', 'HEAD')
        _g_ancestry = _g_record._is_ancestor(_g_a, _g_commit, _g_commit)
    finally:
        _g_os.environ.clear(); _g_os.environ.update(_g_env)
    expect('git-boundary/repository-and-config-environment-cannot-redirect-history-or-archive',
           _g_after == _g_before and _g_history == _g_commit and _g_ar == 'A'
           and _g_exists and _g_root_read == _g_a and _g_head == [_g_commit] and _g_ancestry is True)
