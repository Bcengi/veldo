#!/usr/bin/env python3
"""VELDO account registry: name a Claude Code login once, reuse it for a fleet worker.

A founder registers several accounts once (each is a Claude Code config profile carrying its
own persisted credentials), and the fleet then runs one worker per account concurrently with
NO relogin. This module is the persistent name to profile map behind that.

The mechanism is Claude Code's CLAUDE_CONFIG_DIR environment variable. Pointing it at a
directory makes Claude Code read and write THAT directory's persisted login (on Linux the
.credentials.json file, mode 0600, lives under it), so a session started with
CLAUDE_CONFIG_DIR=<dir> reuses the saved auth in <dir> with no login prompt. Verified against
the current Claude Code authentication docs (the env var name is CLAUDE_CONFIG_DIR and the
per-directory .credentials.json persists across sessions). Two caveats the operator must know:
higher-precedence auth env vars (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN,
Bedrock/Vertex flags) override the saved credentials, so they must stay unset for per-account
isolation to hold; and on macOS credentials live in the Keychain regardless of this env var, so
per-directory isolation is a Linux (and Windows) mechanism.

account_add(name) creates and registers a profile directory (its CLAUDE_CONFIG_DIR); the
ONE-TIME login into that directory is a documented human step (run `CLAUDE_CONFIG_DIR=<dir>
claude` once, then /login as that account). This module PREPARES and REGISTERS the profile, it
never fabricates or performs a login. resolve(name) returns that account's CLAUDE_CONFIG_DIR;
list_accounts() enumerates. A duplicate add and an unknown resolve each fail BY NAME
(DuplicateAccountError / UnknownAccountError), never silently.

The registry persists as a JSON file under the git common dir (veldo/accounts/registry.json,
shared across worktrees, outside git history, machine-local), the same place and pattern as the
claim ledger, so a registered account survives across invocations and worktrees with no relogin.
Pure stdlib; the registry root is overridable for tests."""
import argparse
import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone

SCHEMA = "veldo.accounts/v1"
CONFIG_DIR_ENV = "CLAUDE_CONFIG_DIR"


class AccountError(Exception):
    """Base for account registry errors, so a caller can catch the whole family."""


class DuplicateAccountError(AccountError):
    """account_add was called for a name that is already registered."""


class UnknownAccountError(AccountError):
    """resolve/get was called for a name that is not registered."""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def accounts_root(override=None):
    """Resolve veldo/accounts under the git common dir (shared across worktrees, machine-local,
    outside git history), or an explicit override (VELDO_RUNS_ROOT env or argument) for tests.
    This is the same resolution the claim ledger uses, so the account registry lives beside the
    claim ledger and is reused across every worktree of the repo."""
    root = override or os.environ.get("VELDO_RUNS_ROOT")
    if not root:
        common = subprocess.check_output(
            ["git", "rev-parse", "--git-common-dir"], text=True).strip()
        root = os.path.join(os.path.abspath(common), "veldo")
    return os.path.join(root, "accounts")


def _registry_path(root=None):
    return os.path.join(accounts_root(root), "registry.json")


def _safe(name):
    """A filesystem-safe basename for an account name (used only for the default profile dir)."""
    s = re.sub(r"[^A-Za-z0-9._-]", "_", str(name))
    return s or "_"


@contextlib.contextmanager
def _registry_lock(root=None):
    """Serialize registry read-modify-write on one flock, so a concurrent add from another
    worktree cannot lose an entry. Same arbiter discipline as the claim ledger's per-unit lock;
    the lock file is not a registry record and is ignored by readers."""
    d = accounts_root(root)
    os.makedirs(d, exist_ok=True)
    lf = os.open(os.path.join(d, "registry.json.lock"), os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        fcntl.flock(lf, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lf, fcntl.LOCK_UN)
        os.close(lf)


def _load(root=None):
    """Read the registry, tolerating an absent or corrupt file (fresh empty registry)."""
    try:
        with open(_registry_path(root)) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {"schema": SCHEMA, "accounts": {}}
    if not isinstance(data, dict) or not isinstance(data.get("accounts"), dict):
        return {"schema": SCHEMA, "accounts": {}}
    return data


def _save(data, root=None):
    """Publish the registry with an atomic os.replace, so a lock-free reader always sees a
    complete old-or-new file. Called only while holding the registry lock."""
    d = accounts_root(root)
    os.makedirs(d, exist_ok=True)
    path = _registry_path(root)
    tmp = os.path.join(d, ".tmp.%d.%s" % (os.getpid(), uuid.uuid4().hex))
    with open(tmp, "w") as f:
        f.write(json.dumps(data, indent=2) + "\n")
    try:
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def account_add(name, config_dir=None, root=None, **meta):
    """Register a new account and prepare its CLAUDE_CONFIG_DIR profile directory.

    Creates the profile directory (default veldo/accounts/profiles/<name> beside the registry,
    mode 0700 because a login will persist .credentials.json there) and records name to that
    directory. It does NOT log in: the one-time `CLAUDE_CONFIG_DIR=<dir> claude` then /login into
    the directory is a documented human step, run once per account, and the saved credentials
    then persist there for every future worker. Returns the stored record. Raises
    DuplicateAccountError if the name is already registered, so an existing login is never
    silently overwritten."""
    name = str(name)
    with _registry_lock(root):
        data = _load(root)
        if name in data["accounts"]:
            raise DuplicateAccountError(
                "account %r already registered (resolve it, or add under a different name)" % (name,))
        cdir = os.path.abspath(config_dir) if config_dir else os.path.join(
            accounts_root(root), "profiles", _safe(name))
        os.makedirs(cdir, exist_ok=True)
        try:
            os.chmod(cdir, 0o700)  # credentials will live here; keep the profile private
        except OSError:
            pass
        rec = {"name": name, "config_dir": cdir, "added_at": _now()}
        rec.update({k: v for k, v in meta.items() if v is not None})
        data["accounts"][name] = rec
        _save(data, root)
        return dict(rec)


def resolve(name, root=None):
    """Return the CLAUDE_CONFIG_DIR of a registered account (the directory a worker points
    CLAUDE_CONFIG_DIR at to reuse that account's saved login). Raises UnknownAccountError for an
    unregistered name, never a silent empty string."""
    rec = _load(root)["accounts"].get(str(name))
    if rec is None:
        raise UnknownAccountError(
            "no account %r registered (add it with `veldo account add %s`)" % (name, name))
    return rec["config_dir"]


def get(name, root=None):
    """Return the full stored record for a registered account, or raise UnknownAccountError."""
    rec = _load(root)["accounts"].get(str(name))
    if rec is None:
        raise UnknownAccountError("no account %r registered" % (name,))
    return dict(rec)


def list_accounts(root=None):
    """The registered account names, sorted."""
    return sorted(_load(root)["accounts"].keys())


def _cmd_add(args):
    rec = account_add(args.name, config_dir=args.config_dir)
    print("registered account %r" % rec["name"])
    print("  CLAUDE_CONFIG_DIR: %s" % rec["config_dir"])
    print("  one-time login (run once; the saved login then persists for every worker):")
    print("    CLAUDE_CONFIG_DIR=%s claude   # then /login as this account" % rec["config_dir"])
    return 0


def _cmd_list(args):
    names = list_accounts()
    if not names:
        print("no accounts registered")
        return 0
    for n in names:
        print("%-20s %s" % (n, resolve(n)))
    return 0


def main(argv=None):
    """Thin `veldo account add/list` subcommand logic. The unified veldo CLI (W4) dispatches to
    this; here it stands alone so the account model is usable and gate-testable now."""
    ap = argparse.ArgumentParser(
        prog="veldo account",
        description="Register and list Claude Code accounts (one CLAUDE_CONFIG_DIR profile each) for the fleet.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="register a new account and prepare its config profile directory")
    a.add_argument("name", help="the account name")
    a.add_argument("--config-dir", default=None, dest="config_dir",
                   help="use this directory as the account's CLAUDE_CONFIG_DIR (default: veldo/accounts/profiles/<name>)")
    a.set_defaults(fn=_cmd_add)
    lst = sub.add_parser("list", help="list registered accounts and their CLAUDE_CONFIG_DIR")
    lst.set_defaults(fn=_cmd_list)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except AccountError as ex:
        print("account error: %s" % ex, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
