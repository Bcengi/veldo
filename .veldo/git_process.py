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
