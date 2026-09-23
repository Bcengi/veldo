"""One subprocess boundary for Git. Caller environment cannot select a repository or config.

Repository-local configuration remains authoritative. System/global config (including HOME and
XDG_CONFIG_HOME discovery), replacement objects, and all inherited GIT_* knobs are disabled.
Writers needing a synthetic identity pass it explicitly; ambient identity is never trusted.
"""
import os
import subprocess


def clean_env(env=None, identity=None):
    source = os.environ if env is None else env
    result = {k: v for k, v in source.items() if not k.startswith("GIT_")}
    result.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_SYSTEM=os.devnull,
                  GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0",
                  GIT_NO_REPLACE_OBJECTS="1")
    if identity is not None:
        name, email = identity
        result.update(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email,
                      GIT_COMMITTER_NAME=name, GIT_COMMITTER_EMAIL=email)
    return result


def _options(args, kwargs):
    if isinstance(args, (str, bytes)) or not args or args[0] != "git":
        raise ValueError("the Git boundary accepts a git argument vector only")
    if kwargs.get("shell"):
        raise ValueError("the Git boundary does not invoke a shell")
    kwargs["env"] = clean_env(kwargs.pop("env", None), kwargs.pop("identity", None))
    return kwargs


def run(args, **kwargs):
    return subprocess.run(args, **_options(args, kwargs))


def check_output(args, **kwargs):
    return subprocess.check_output(args, **_options(args, kwargs))


def claims_a_repository(path):
    """Whether Git's own discovery from `path` would reach a repository: a `.git` entry, or a bare
    git directory, at `path` or at any ancestor on the same filesystem. git_process strips GIT_DIR and
    GIT_CEILING_DIRECTORIES, and discovery stops at a filesystem boundary, so this walk is exactly the
    set of places a failing Git could have been reading. Nothing is parsed from Git's own messages."""
    current = os.path.realpath(str(path))
    try:
        device = os.stat(current).st_dev
    except OSError:
        device = None
    while True:
        if os.path.lexists(os.path.join(current, '.git')) or all(
                os.path.exists(os.path.join(current, part)) for part in ('HEAD', 'objects', 'refs')):
            return True
        parent = os.path.dirname(current)
        if parent == current:
            return False
        try:
            if device is not None and os.stat(parent).st_dev != device:
                return False
        except OSError:
            return True  # an ancestor that cannot be read cannot be ruled out
        current = parent


def entry_exists(path):
    """Whether a directory entry exists, telling ABSENT apart from UNREADABLE: only a missing entry
    (or a missing directory on the way) is False; any other failure (permission denied, an I/O
    error) is raised, because os.path.lexists would read it as absent and an unreadable enrollment
    would then look like no enrollment."""
    try:
        os.lstat(path)
        return True
    except (FileNotFoundError, NotADirectoryError):
        return False
