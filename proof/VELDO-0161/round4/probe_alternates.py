"""VELDO-0161 round 4, R2: the reviewer's scenario, run through a provisioner's own git() and refuse_commands().

    python3 proof/VELDO-0161/round4/probe_alternates.py <checkout> <commit> [<commit> ...]

For each commit, its .veldo (git archive, never the working tree) is unpacked in a temporary directory and
its control_repository_provisioner loaded from there. A repository `repo` borrows objects from a lender
(objects/info/alternates) and names `core.alternateRefsCommand = touch <tmp>/RAN; true` in its own
.git/config. The probe does what prepare does before it lays the scaffold: refuse_commands(repo), and, when
that passes, the fetch lay_scaffold makes into the repository (fetch -q --no-tags <clone>
+HEAD:refs/veldo/adoption/x). It prints, per commit, the refusal (or none) and whether the command ran.
"""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def load(directory):
    spec = importlib.util.spec_from_file_location('probe_provisioner', str(Path(directory) / 'control_repository_provisioner.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def plain(*args):
    subprocess.run(['git', *args], check=True, capture_output=True,
                   env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1'))


def scenario(PR, work):
    lender, repo, clone = work / 'lender', work / 'repo', work / 'clone'
    for path in (lender, repo):
        plain('init', '-q', '-b', 'main', str(path))
        (path / 'README').write_text(path.name + '\n')
        plain('-C', str(path), 'add', '-A')
        plain('-C', str(path), '-c', 'user.name=Probe', '-c', 'user.email=probe@example.invalid', 'commit', '-q', '-m',
              path.name)
    plain('clone', '-q', str(repo), str(clone))
    (clone / 'SCAFFOLD').write_text('scaffold\n')
    plain('-C', str(clone), 'add', '-A')
    plain('-C', str(clone), '-c', 'user.name=Probe', '-c', 'user.email=probe@example.invalid', 'commit', '-q', '-m', 'scaffold')
    (repo / '.git' / 'objects' / 'info' / 'alternates').write_text(str(lender / '.git' / 'objects') + '\n')
    ran = work / 'RAN'
    plain('-C', str(repo), 'config', 'core.alternateRefsCommand', 'touch %s; true' % ran)
    try:
        PR.refuse_commands(str(repo))
        refused = None
    except PR.Refused as error:
        refused = error.code
    if refused is None:
        PR.git(str(repo), 'fetch', '-q', '--no-tags', str(clone), '+HEAD:refs/veldo/adoption/x')
    return {'refused': refused, 'command_ran': ran.exists(),
            'repository_commands': PR.repository_commands(str(repo))}


def main(argv):
    checkout, commits = Path(argv[0]), argv[1:]
    results = {}
    for commit in commits:
        with tempfile.TemporaryDirectory(prefix='v161-r2-') as directory:
            archive = subprocess.run(['git', '-C', str(checkout), 'archive', '--format=tar', commit, '.veldo'],
                                     check=True, capture_output=True).stdout
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(directory, filter='data')
            work = Path(directory) / 'work'
            work.mkdir()
            results[commit] = scenario(load(Path(directory) / '.veldo'), work)
    print(json.dumps(results, indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
