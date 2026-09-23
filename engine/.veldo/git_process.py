"""One subprocess boundary for Git. Caller environment cannot select a repository or config.

Repository-local configuration remains authoritative. System/global config (including HOME and
XDG_CONFIG_HOME discovery), replacement objects, and all inherited GIT_* knobs are disabled.
Writers needing a synthetic identity pass it explicitly; ambient identity is never trusted.

Two profiles. The default, "isolated", is everything above and serves every local operation.
"network" is for transport operations only (push, fetch, ls-remote to a remote) and for the
read-only queries that decide where such an operation goes. It exists because a transport
operation run in the isolated profile loses what a plain `git push` from the same clone uses:
global and system credential helpers, url.*.insteadOf rewrites, http.proxy and core.sshCommand,
and the operator's GIT_SSH_COMMAND or GIT_ASKPASS. The neutralization exists to stop ambient
values overriding EXPLICIT coordinates, not to reduce what configured tools can do, so the network
profile still strips every GIT_* variable by prefix (repository, work tree, index, object store,
alternates, namespace, injected configuration and config-file selectors among them) and adds back
only the named transport and credential variables below. Global and system configuration are
discovered the ordinary way, from HOME and XDG_CONFIG_HOME and the installation's system file.
"""
import os
import subprocess

PROFILES = ("isolated", "network")

# Transport and credential variables a plain `git push` from the operator's shell honors. None
# names a repository, object store, index, namespace, configuration file or configuration value.
# Variables outside GIT_* (SSH_AUTH_SOCK, SSH_ASKPASS, proxy variables) pass in every profile.
TRANSPORT_VARIABLES = frozenset((
    "GIT_SSH_COMMAND", "GIT_SSH", "GIT_SSH_VARIANT", "GIT_ASKPASS", "GIT_TERMINAL_PROMPT",
    "GIT_PROXY_COMMAND", "GIT_HTTP_PROXY_AUTHMETHOD", "GIT_PROXY_SSL_CERT", "GIT_PROXY_SSL_KEY",
    "GIT_PROXY_SSL_CERT_PASSWORD_PROTECTED", "GIT_PROXY_SSL_CAINFO",
    "GIT_SSL_NO_VERIFY", "GIT_SSL_CERT", "GIT_SSL_KEY", "GIT_SSL_CERT_PASSWORD_PROTECTED",
    "GIT_SSL_CAINFO", "GIT_SSL_CAPATH", "GIT_SSL_VERSION", "GIT_SSL_CIPHER_LIST",
    "GIT_HTTP_USER_AGENT", "GIT_HTTP_LOW_SPEED_LIMIT", "GIT_HTTP_LOW_SPEED_TIME",
    "GIT_HTTP_MAX_REQUESTS", "GIT_ALLOW_PROTOCOL", "GIT_PROTOCOL_FROM_USER",
))


def clean_env(env=None, identity=None, profile="isolated"):
    if profile not in PROFILES:
        raise ValueError("unknown Git environment profile: %r" % (profile,))
    source = os.environ if env is None else env
    result = {k: v for k, v in source.items() if not k.startswith("GIT_")}
    if profile == "network":
        result.update({k: v for k, v in source.items() if k in TRANSPORT_VARIABLES})
        # The executor that runs transport operations has no terminal: a prompt would only stall
        # until the timeout. An operator who sets the variable keeps their value.
        result.setdefault("GIT_TERMINAL_PROMPT", "0")
        result.update(GIT_NO_REPLACE_OBJECTS="1")
    else:
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
    kwargs["env"] = clean_env(kwargs.pop("env", None), kwargs.pop("identity", None),
                              kwargs.pop("profile", "isolated"))
    return kwargs


def run(args, **kwargs):
    return subprocess.run(args, **_options(args, kwargs))


def check_output(args, **kwargs):
    return subprocess.check_output(args, **_options(args, kwargs))
