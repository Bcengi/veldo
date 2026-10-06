"""Authority-owned Git boundary. Inspect a linked marker without invoking Git first."""
import argparse
import importlib.util
import os
from pathlib import Path
import sys


def common_directory(authority):
    authority = Path(authority).resolve()
    installed = authority / '.veldo/authority_git_common'
    if installed.is_file():
        return Path(installed.read_text().strip()).resolve(strict=True)
    for root in (authority, *authority.parents):
        marker = root / '.git'
        if marker.is_dir():
            return marker.resolve(strict=True)
        if marker.is_file():
            line = marker.read_text().strip()
            if not line.startswith('gitdir: '):
                raise ValueError('invalid authority Git marker')
            directory = (root / line[8:]).resolve(strict=True)
            common = directory / 'commondir'
            return ((directory / common.read_text().strip()).resolve(strict=True)
                    if common.is_file() else directory)
    raise ValueError('expected shared gitdir is unavailable from authority')


def validate(root, expected_common=None):
    root = Path(root).resolve(strict=True)
    marker = root / '.git'
    if marker.is_symlink():
        raise ValueError('candidate .git must not be a symlink')
    if marker.is_dir():
        expected = expected_common or os.environ.get('VELDO_EXPECTED_GIT_COMMON')
        if expected is not None and marker.resolve() != Path(expected).resolve():
            raise ValueError('candidate .git redirects outside expected shared gitdir')
        return marker, marker
    if not marker.is_file():
        raise ValueError('candidate Git marker is absent')
    if expected_common is None:
        expected_common = os.environ.get('VELDO_EXPECTED_GIT_COMMON') or common_directory(
            Path(__file__).resolve().parents[1])
    common = Path(expected_common).resolve(strict=True)
    line = marker.read_text().strip()
    if not line.startswith('gitdir: '):
        raise ValueError('invalid candidate Git marker')
    directory = (root / line[8:]).resolve(strict=True)
    if (directory.parent != common / 'worktrees' or directory.is_symlink()
            or (directory / 'commondir').is_symlink()
            or (directory / 'gitdir').is_symlink()
            or (directory / (directory / 'commondir').read_text().strip()).resolve() != common
            or Path((directory / 'gitdir').read_text().strip()).resolve() != marker):
        raise ValueError('candidate .git redirects outside expected shared gitdir')
    return directory, common


def _load_git_process():
    """The repository's one Git subprocess boundary, beside this module: it strips every inherited
    GIT_* variable and disables system and global configuration, as this guard requires."""
    spec = importlib.util.spec_from_file_location('candidate_git_process',
                                                  Path(__file__).with_name('git_process.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(root, args, expected_common=None, **kwargs):
    directory, common = validate(root, expected_common)
    _git_process = _load_git_process()
    # Explicit paths pin discovery even if the writable marker changes after validation, and the
    # validated common directory is pinned in the environment.
    return _git_process.run(['/usr/bin/git', '--git-dir=' + str(directory),
                             '--work-tree=' + str(Path(root).resolve()), '-c', 'core.hooksPath=/dev/null',
                             '-c', 'core.fsmonitor=false', *args], cwd=root, common_dir=common, **kwargs)


def clone(root, destination, expected_common=None, **kwargs):
    # Git takes a pinned work tree as the clone's own, so a clone cannot go through run(). The source
    # is the validated common directory, never the writable marker read a second time.
    _, common = validate(root, expected_common)
    _git_process = _load_git_process()
    return _git_process.run(['/usr/bin/git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                             'clone', '-q', '--no-checkout', '--no-hardlinks', '--', str(common),
                             str(destination)], **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root')
    parser.add_argument('--authority-common', action='store_true')
    parser.add_argument('--expected-common')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--clone-to')
    parser.add_argument('args', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if args.authority_common:
            print(common_directory(Path(__file__).resolve().parents[1]))
            return 0
        if not args.root:
            raise ValueError('--root is required')
        if args.validate_only:
            validate(args.root, args.expected_common)
            return 0
        if args.clone_to:
            return clone(args.root, args.clone_to, args.expected_common).returncode
        command = args.args[1:] if args.args[:1] == ['--'] else args.args
        return run(args.root, command, args.expected_common).returncode
    except (OSError, ValueError) as error:
        print('candidate Git refused: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
