#!/usr/bin/env bash
# VELDO guard hook (PreToolUse). Mechanical enforcement of the merge rules on
# the developer machine. Exit 2 blocks the tool call and shows stderr to the
# agent. This is the first line, not the last: branch protection and CI
# enforce the same rules server-side, where local hooks cannot be edited away.
#
# Wire-up (in .claude/settings.json): PreToolUse matcher "Bash" -> this script.
# Reads the hook JSON payload on stdin; inspects Bash commands for merge and
# push attempts and blocks them unless the gate is green for HEAD and a proof
# manifest exists for HEAD.
#
# ONLY A PROTECTED DESTINATION IS JUDGED (VELDO-0268). The checks below run for a push or merge
# that moves a ref .veldo/policy.yaml names in protected_refs (main, master, release branches and
# tags as the engine ships it), read through policy_check.protected_ref. A working branch pushes
# freely: the gate and the approvals bind where the trunk moves. The destination is git's own
# answer, never read from the command text: a porcelain dry run of the same push with hooks
# disabled, the checked-out branch for git merge, the base gh reports for gh pr merge. A git
# pre-push hook calls this script once per ref with VELDO_GUARD_REF (and VELDO_GUARD_COMMIT) set
# and no tool payload on stdin. A destination that cannot be resolved is protected.
#
# THE GUARD RUNS NOTHING THE COMMAND, THE CONFIGURATION OR THE ENVIRONMENT CHOOSES (VELDO-0268 fix
# round 3). Its dry run contacts the remote, and git runs programs on the way: a receive-pack, an
# ssh command, a transport helper, a credential helper, an askpass. A push naming such a program
# (an option outside the guard's allowlist, a -c key outside it) or a configuration naming a
# receive-pack is unresolved without running anything. For the dry run itself every other such
# program is pinned to a fixed value placed after the user's options, the environment's GIT_
# variables that choose programs are dropped, and only the file, ssh, http and https transports are
# allowed (GIT_ALLOW_PROTOCOL, which overrides any configuration). A credential helper runs only
# when every one configured comes from the global or system configuration, in a file outside the
# repository (owner decision Telegram 39895: the user's own login, trusted as ~/.ssh/config is); a
# helper from the repository's configuration, a file it includes under the repository, or the
# command line makes the push unresolved without running it. A push that cannot be resolved that
# way is unresolved. An alias that expands to push or merge is judged as that command, looked up in
# the repository the command runs in; where that cannot be determined (a cd before it, an
# environment assignment, a global option other than -C and -c), a subcommand that is neither a
# builtin nor a git-<name> program is unresolved. A lookup that cannot run or read the configuration
# (a -C directory that does not exist), and a -C or -c value the shell expands, make such a subcommand
# unresolved, never "no alias" (fix round 5). A simple command whose first word is not git (sh -c,
# bash -c) has its text judged for aliases as a compound command is. The dry run's one line beside
# the ref lines that names no destination, "Would set upstream of ...", is read; any other is not.
#
# ONLY THE TEXT THE SHELL WOULD RUN IS JUDGED (VELDO-0292). Before any of the above, one scanner
# reads the command over the part of the shell grammar POSIX fixes and writes its live text: each
# comment dropped, and each heredoc body and quoted string that is data written as a placeholder
# word. A string is data when the shell does not expand it and every command of its pipeline is a
# plain text tool (echo, cat, grep and the rest of one fixed set), in a command that names no git
# or gh anywhere else. The text git and gh store and never run (a commit or tag message, a log
# pattern, an issue or pull request title and body) is data too. A construct outside that grammar
# (a substitution, a function, a reserved word, an assignment, a shell builtin outside nine
# allowed ones) sends the whole command to the judgment as written. So does a write the guard
# cannot show lands outside git's configuration (a redirection or a writing tool whose path names
# git or config in any form, or holds an expansion or a glob), the word config outside data, and
# an expansion, a substitution, a brace, a glob, a tilde or a joined line in text a program other
# than a plain text tool may run. None of these reads how a later command spells git, and each can
# only refuse. The judgment itself is the one described above, and it reads the live text. When it
# refuses a command that is not one simple git or gh command, the "destination unresolved" line
# ends with what it found and where.
set -u
cd "${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Guard only VELDO-initialized repositories; stand down everywhere else.
[ -d .veldo ] || exit 0

PAYLOAD=$(cat 2>/dev/null || true)
CMD=$(printf '%s' "$PAYLOAD" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    print(d.get("tool_input",{}).get("command",""))
except Exception:
    print("")
' 2>/dev/null || true)

# Only guard merge-ish and push-ish commands; everything else passes through. Any command naming
# git goes on to the destination step below, which decides with the guard's own git global option
# parsing whether it is a push or merge (git -C dir push and git -c k=v push included); only those
# are judged. Without a tool payload, a git pre-push hook's call names its one destination in
# VELDO_GUARD_REF. The match reads the command without its quote characters and backslashes, so a
# command word written 'git' or g\it goes on to the destination step too (VELDO-0292).
if [ -n "$CMD" ]; then
  if ! printf '%s' "$CMD" | tr -d "'\"\\\\" | grep -qE '(git|gh pr (merge|create))'; then
    exit 0
  fi
  GUARD_PATH=tool
elif [ -n "${VELDO_GUARD_REF+set}" ]; then
  GUARD_PATH=pre-push
else
  exit 0
fi
TOOL_CWD=$(printf '%s' "$PAYLOAD" | python3 -c '
import json,sys
try:
    print(json.load(sys.stdin).get("cwd") or "")
except Exception:
    print("")
' 2>/dev/null || true)

# The destinations (VELDO-0268): one line per destination on standard error, and on standard
# output the protected ones, each as its full ref name or "unresolved". Nothing printed means no
# protected ref moves, and the push or merge passes without the checks below.
JUDGED=$(VELDO_GUARD_PATH="$GUARD_PATH" VELDO_GUARD_CMD="$CMD" VELDO_GUARD_CWD="$TOOL_CWD" python3 - <<'PY'
import importlib.util, os, re, shlex, shutil, subprocess, sys
from pathlib import Path

CHECKS = "runs the gate stamp, reuse evidence, proof manifest and policy_check checks"
OPERATOR = set("();<>|&")
EXPANSION = ("$", "\x60", "\n")


FOUND = []  # what the judged text held and where, for the unresolved line (VELDO-0292)


def log(ref, text):
    note = FOUND[0] if ref == "unresolved" and FOUND else ""
    print("VELDO guard: destination %s: %s%s" % (ref, text, note), file=sys.stderr)


def unresolved(reason):
    return [(None, reason)]


def words_of(command):
    """The words of one simple command, or None when the text is anything else (a list, a pipe,
    a redirection, an expansion, a substitution or more than one line)."""
    if any(c in command for c in EXPANSION):
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError:
        return None
    if not words or any(w and set(w) <= OPERATOR for w in words):
        return None
    return words


# Git's global options that take their value as the next word.
GIT_VALUE = ("-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix",
             "--attr-source")
# The same options in the raw text, for a command that is not one simple command: git, any global
# options, then push or merge.
WORD = r"""(?:"[^"]*"|'[^']*'|\\.|[^\s"'\\])+"""
PUSHISH = re.compile(r"git (push|merge)(?!-)|gh pr merge|git(?:\s+(?:(?:%s)\s+%s|-\S*))*\s+(?:push|merge)\b(?!-)"
                     % ("|".join(GIT_VALUE), WORD))


def git_split(words):
    """(every global option before the subcommand, the subcommand or None, its arguments)."""
    at, opts = 1, []
    while at < len(words) and words[at].startswith("-"):
        step = 2 if words[at] in GIT_VALUE else 1
        opts += words[at:at + step]
        at += step
    if at >= len(words):
        return opts, None, []
    return opts, words[at], words[at + 1:]


def git_globals(words):
    """(the global options before the subcommand, the subcommand, its arguments), or None when an
    option other than -C and -c, each with its value, precedes the subcommand."""
    kept, sub, rest = git_split(words)
    if sub is None or len(kept) % 2 or any(o not in ("-C", "-c") for o in kept[0::2]):
        return None
    return kept, sub, rest


def names_push_or_merge(command, words):
    """Whether the command is, or may be, a git push, git merge or gh pr merge."""
    if PUSHISH.search(command):
        return True
    if words and (words[0] == "git" or words[0].endswith("/git")):
        return git_split(words)[1] in ("push", "merge")
    return False


# The git push options the guard reproduces, by their full names (an abbreviation is unresolved).
# None of them names a program; --receive-pack, --exec, --signed and --recurse-submodules are absent.
PUSH_LONG = ("--all", "--branches", "--mirror", "--delete", "--tags", "--follow-tags", "--no-follow-tags",
             "--force", "--no-force", "--force-with-lease", "--no-force-with-lease", "--force-if-includes",
             "--no-force-if-includes", "--atomic", "--no-atomic", "--prune", "--no-prune", "--set-upstream",
             "--no-set-upstream", "--thin", "--no-thin", "--quiet", "--no-quiet", "--verbose", "--no-verbose",
             "--progress", "--no-progress", "--verify", "--no-verify", "--dry-run", "--porcelain", "--ipv4",
             "--ipv6", "--no-signed", "--no-recurse-submodules", "--push-option", "--no-push-option", "--repo")
PUSH_LONG_VALUE = ("--push-option", "--repo")  # their value is the next word unless written with =
PUSH_SHORT = "nvqfud46"  # and -o, which takes a value
# Placed after the user's options, so they win whatever the user wrote: a dry run that prints its
# porcelain ref lines (never quiet) and runs no hook.
FORCED = ["--no-quiet", "--dry-run", "--porcelain", "--no-verify"]
# The only -c keys a reproduced push may carry; any other may name a program the dry run would run.
SAFE_KEYS = ("push.default", "core.hookspath", "push.autosetupremote")
# Pinned for the dry run after the user's options: every program git may run on the way to the
# remote gets a fixed value (ssh without a proxy or local command, no askpass). The credential helper
# is the user's own from the global or system configuration, or the push is unresolved
# (credential_program, owner decision Telegram 39895).
SSH = "ssh -o ProxyCommand=none -o PermitLocalCommand=no -o KnownHostsCommand=none -o BatchMode=yes"
PINNED = ["core.sshCommand=" + SSH,
          "ssh.variant=ssh",
          "core.askPass=",
          "core.fsmonitor=false",
          "core.alternateRefsCommand=true",
          "push.negotiate=false",
          "push.gpgSign=false",
          "push.recurseSubmodules=no"]
# The environment's GIT_ variables the dry run keeps: they say which repository, never which program.
GIT_ENV_KEPT = ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES",
                "GIT_DISCOVERY_ACROSS_FILESYSTEM", "GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM")
ALIAS_DEPTH = 10
SHELL_ALIAS = re.compile(r"\b(git|push|merge)\b")
GITSUB = re.compile(r"\bgit(?:\s+(?:(?:%s)\s+%s|-\S*))*\s+(%s)" % ("|".join(GIT_VALUE), WORD, WORD))
BUILTINS = []
# The line a dry run with -u, --set-upstream or push.autoSetupRemote prints beside its ref lines.
UPSTREAM = re.compile(r"Would set upstream of '[^']*' to '[^']*' of '[^']*'")


class AliasUnreadable(Exception):
    """An alias lookup that could not run or read the configuration: the subcommand may be an alias."""


def dry_env():
    """The guard's environment without the GIT_ variables that choose a program (GIT_SSH_COMMAND,
    GIT_SSH, GIT_ASKPASS, GIT_EXEC_PATH, GIT_CONFIG_PARAMETERS and the rest), with only the file, ssh,
    http and https transports allowed and no prompt."""
    env = {k: v for k, v in os.environ.items()
           if not (k.startswith("GIT_") and k not in GIT_ENV_KEPT) and k != "SSH_ASKPASS"}
    env["GIT_ALLOW_PROTOCOL"] = "file:ssh:http:https"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["SSH_ASKPASS_REQUIRE"] = "never"
    return env


def pairs_of(kept):
    """The -C and -c pairs among git global options."""
    out, at = [], 0
    while at < len(kept):
        if kept[at] in ("-C", "-c") and at + 1 < len(kept):
            out += kept[at:at + 2]
        at += 2 if kept[at] in GIT_VALUE else 1
    return out


def builtin(sub, cwd):
    """Whether git runs the subcommand as a builtin (git ignores an alias named after one)."""
    if not BUILTINS:
        r = subprocess.run(["git", "--list-cmds=builtins"], cwd=cwd, env=dry_env(), capture_output=True,
                           text=True, timeout=60, stdin=subprocess.DEVNULL)
        BUILTINS.extend(r.stdout.split() or ["push"])
    return sub in BUILTINS


def maybe_alias(sub, cwd):
    """Whether the subcommand may be an alias: git runs a builtin, then a git-<name> program, and only
    then an alias, so a subcommand that is neither may be one."""
    if builtin(sub, cwd):
        return False
    r = subprocess.run(["git", "--exec-path"], cwd=cwd, env=dry_env(), capture_output=True, text=True,
                       timeout=60, stdin=subprocess.DEVNULL)
    path = os.pathsep.join([r.stdout.strip(), os.environ.get("PATH", "")])
    return shutil.which("git-" + sub, path=path) is None


def alias_of(kept, sub, cwd):
    """What git expands the subcommand to when it is an alias, or None. Reading the configuration
    runs no program."""
    if builtin(sub, cwd):
        return None
    r = subprocess.run(["git"] + pairs_of(kept) + ["config", "--get", "alias." + sub], cwd=cwd, env=dry_env(),
                       capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    if r.returncode == 1 and not r.stdout:
        return None
    if r.returncode != 0:
        raise AliasUnreadable(sub)
    return r.stdout.rstrip("\n")


# Text before a git command that changes the repository or configuration it reads (VELDO-0268 fix
# round 4): a directory change, or an assignment of a GIT_ variable, HOME or XDG_CONFIG_HOME.
ELSEWHERE = re.compile(r"(?:^|[\s;&|()])(?:cd|pushd|popd)(?:$|[\s;&|()])|\b(?:GIT_\w*|HOME|XDG_CONFIG_HOME)=")


def alias_in_text(command, cwd):
    """Whether a command the guard cannot reproduce sets an alias or runs one that may push or merge.
    The alias is looked up where the git command runs (its -C and -c pairs); when the text before it
    may run it in another repository or configuration, a subcommand that may be an alias counts."""
    if re.search(r"alias\.\S*=", command, re.I):
        return True
    # Every git in the text, overlapping ones too: a git inside another's -c value (an editor or a
    # pager) or inside a wrapper's argument is judged on its own (VELDO-0268 fix round 6).
    for start in (m.start() for m in re.finditer(r"(?<![\w.-])git(?=\s)", command)):
        match = GITSUB.match(command, start)
        if match is None:
            continue
        sub = match.group(1).strip("\"'")
        try:
            split = git_globals(shlex.split(match.group(0)))
        except ValueError:
            split = None
        if split is not None and any(c in w for w in split[0] for c in ("$", "\x60")):
            split = None  # a -C or -c value the shell expands: where git runs is not known
        if split is None or ELSEWHERE.search(command[:match.start()]):
            if sub not in ("push", "merge") and maybe_alias(sub, cwd):
                return True
            continue
        kept = split[0]
        for _ in range(ALIAS_DEPTH):
            value = None if sub in ("push", "merge") else alias_of(kept, sub, cwd)
            if value is None:
                break
            if value.startswith("!") or re.search(r"\b(push|merge)\b", value):
                return True
            first = [w for w in value.split() if not w.startswith("-")]
            if not first:
                break
            sub = first[0]
        else:
            return True
    return False


def push_options(rest):
    """(where git push's options end: the "--" that is not an option's value, or the end; the reason
    an option is not reproduced, or None)."""
    at = 0
    while at < len(rest):
        word = rest[at]
        if word == "--":
            return at, None
        if word.startswith("--"):
            name = word.split("=", 1)[0]
            if name not in PUSH_LONG:
                return at, "git push with an option the guard does not reproduce: %s" % name
            at += 2 if name in PUSH_LONG_VALUE and "=" not in word else 1
            continue
        if word.startswith("-") and len(word) > 1:
            for i, c in enumerate(word[1:]):
                if c == "o":
                    at += 1 if i == len(word) - 2 else 0  # -o with its value in the next word
                    break
                if c not in PUSH_SHORT:
                    return at, "git push with an option the guard does not reproduce: -%s" % c
        at += 1
    return len(rest), None


def configured_program(kept, cwd, env):
    """The reason the configuration makes this push unreproducible, or None: a remote's receivepack
    names the program a push runs, so the guard neither runs it nor judges a push it would run."""
    r = subprocess.run(["git"] + kept + ["config", "--name-only", "-z", "--get-regexp", r"^remote\..*\.receivepack$"],
                       cwd=cwd, env=env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    if r.returncode == 1 and not r.stdout:
        return None
    if r.returncode != 0:
        return "the configuration could not be read"
    return "the configuration names a receive-pack program (%s), which the guard does not run" % (
        ", ".join(n for n in r.stdout.split("\0") if n)[:200])


def credential_program(kept, cwd, env):
    """The reason a credential helper makes this push unreproducible, or None (owner decision
    Telegram 39895). Every helper configured (credential.helper and every URL-scoped
    credential.<url>.helper, for any URL) must come from the global or system configuration, in a file
    outside the repository; a helper from the repository's configuration, a file under the repository
    that any configuration includes, or the command line is not run. An empty value runs nothing."""
    r = subprocess.run(["git"] + kept + ["config", "--show-scope", "--show-origin", "-z", "--get-regexp",
                                         r"^credential\..*helper$"],
                       cwd=cwd, env=env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    if r.returncode == 1 and not r.stdout:
        return None
    if r.returncode != 0:
        return "the configuration could not be read"
    where = subprocess.run(["git"] + kept + ["rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir",
                                             "--show-toplevel"],
                           cwd=cwd, env=env, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    repo = [os.path.realpath(p) for p in where.stdout.splitlines() if p.startswith("/")]
    fields = r.stdout.split("\0")
    for at in range(0, len(fields) - 2, 3):
        scope, origin, entry = fields[at:at + 3]
        name, _, value = entry.partition("\n")
        if not value:
            continue
        path = origin[5:] if origin.startswith("file:") else ""
        real = os.path.realpath(path) if path.startswith("/") else ""
        if (scope not in ("global", "system") or not real
                or any(real == d or real.startswith(d.rstrip("/") + "/") for d in repo)):
            return ("the configuration names a credential helper outside the global and system "
                    "configuration (%s from %s %s), which the guard does not run" % (name, scope, origin[:120]))
    return None


def dry_run(kept, rest, cwd):
    """Git's own answer for where this push goes: the same push, dry run, porcelain, no hooks. The
    user's quiet, verbosity and verify options are overridden by options placed after theirs, and the
    hooks path is set after their global options, so neither can silence the answer or run a hook.
    It never runs a program the command, the configuration or the environment chooses."""
    if any(w.startswith(("--no-dry", "--no-porc")) for w in rest):
        return unresolved("the command turns the dry run off, so it cannot be reproduced")
    unsafe = [v.split("=", 1)[0] for o, v in zip(kept[0::2], kept[1::2])
              if o == "-c" and not (v.split("=", 1)[0].lower() in SAFE_KEYS or v.lower().startswith("alias."))]
    if unsafe:
        return unresolved("git -c %s may name a program, so the guard does not reproduce it" % unsafe[0])
    end, problem = push_options(rest)
    if problem:
        return unresolved(problem)
    env = dry_env()
    problem = configured_program(kept, cwd, env)
    if problem:
        return unresolved(problem)
    problem = credential_program(kept, cwd, env)
    if problem:
        return unresolved(problem)
    kept = kept + [w for pin in PINNED for w in ("-c", pin)]
    try:
        r = subprocess.run(["git"] + kept + ["-c", "core.hooksPath=/dev/null", "push"]
                           + rest[:end] + FORCED + rest[end:],
                           cwd=cwd, env=env, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:
        return unresolved("the dry run did not run (%s)" % type(error).__name__)
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["exit %d" % r.returncode])[-1]
        return unresolved("the dry run failed: %s" % tail[:200])
    found = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and len(parts[0]) == 1 and ":" in parts[1]:
            ref = parts[1].rsplit(":", 1)[1]
            if not ref.startswith("refs/"):
                return unresolved("the dry run named a destination that is not a full ref name")
            found.append((ref, None))
        elif not (line.startswith("To ") or line == "Done" or not line.strip() or UPSTREAM.fullmatch(line)):
            return unresolved("the dry run printed a line the guard cannot read")
    if not found:
        return unresolved("the dry run named no destination")
    return found


def merge_target(kept, cwd):
    """The branch git merge moves: the one checked out where it runs."""
    r = subprocess.run(["git"] + kept + ["symbolic-ref", "-q", "HEAD"], cwd=cwd, env=dry_env(),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    ref = r.stdout.strip()
    if r.returncode != 0 or not ref.startswith("refs/"):
        return unresolved("git merge with no branch checked out")
    return [(ref, None)]


GH_VALUE = {"-t", "--subject", "-b", "--body", "-F", "--body-file", "-A", "--author-email",
            "--match-head-commit", "-R", "--repo"}
GH_BOOL = {"--admin", "--auto", "-d", "--delete-branch", "--disable-auto", "-m", "--merge",
           "-r", "--rebase", "-s", "--squash"}


def gh_base(rest, cwd):
    """The base branch of the pull request gh pr merge would merge, as gh reports it."""
    selector, repo, at = [], [], 0
    while at < len(rest):
        word = rest[at]
        flag = word.split("=", 1)[0]
        if word.startswith("-") and flag in GH_VALUE:
            if "=" in word:
                value, step = word.split("=", 1)[1], 1
            elif at + 1 < len(rest):
                value, step = rest[at + 1], 2
            else:
                return unresolved("gh pr merge with a flag missing its value")
            if flag in ("-R", "--repo"):
                repo = ["--repo", value]
            at += step
            continue
        if word.startswith("-"):
            if word not in GH_BOOL:
                return unresolved("gh pr merge with a flag the guard does not know: %s" % word)
        elif not selector:
            selector = [word]
        else:
            return unresolved("gh pr merge with more than one pull request named")
        at += 1
    try:
        r = subprocess.run(["gh", "pr", "view"] + selector + repo + ["--json", "baseRefName", "-q", ".baseRefName"],
                           cwd=cwd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:
        return unresolved("gh did not report the base (%s)" % type(error).__name__)
    base = r.stdout.strip()
    if r.returncode != 0 or not base or "\n" in base:
        return unresolved("gh did not report the base")
    return [("refs/heads/" + base, None)]


# THE LIVE TEXT (VELDO-0292). The judgment reads the text the shell would run, not every word of the
# command. One scanner reads the command over the part of the shell grammar POSIX fixes: simple
# commands joined by newlines, ; && || | and &, words of unquoted text, quotes and backslash escapes,
# $NAME and ${NAME} in arguments, redirections with a word target, heredocs and comments. Anything
# else is outside it, and the whole command is then judged as written: a substitution, a subshell, a
# brace, a function, a reserved word, an expansion or a glob character in a command word, an
# assignment word, a shell builtin other than the nine allowed, an unterminated quote or heredoc.
# Only the shell itself can change which program a name runs, and only by a function, a builtin or
# an assignment, so inside the subset every bare command word runs the program it named when the
# command started. Inside it a comment is dropped, and a quoted string or heredoc body is written as
# a placeholder word when it is data: the shell does not expand it and every command of its pipeline
# is a plain text tool, so no program it reaches can run it. Each command word is written after
# quote removal, so a quoted or escaped spelling of git reaches the judgment as git.
#
# Three tests then decide whether anything in the command is data at all. None of them asks how a
# later command spells git, and each can only move a command toward refusal. Test 1, a write to
# git configuration: when a place the command writes is not shown to be outside git's
# configuration, or the word config stands outside data, the whole command is judged as written.
# Test 2, a construct in text a program may run: when text that reaches a program other than a
# plain text tool holds an expansion, a substitution, a brace, a glob, a tilde or a joined line,
# the whole command is judged as written. Test 3, a command that names git or gh: when git or gh
# is named anywhere outside data, nothing is data but the text git and gh store and never run.
PLACEHOLDER = "_data_"
# The plain text tools: programs that never execute their arguments or their input. The membership
# test: no option of this program runs another program. sort fails it (its compress program option
# runs any program on sort's own temporary data), so sort is not here. A name missing here can only
# cause a refusal. Adding one changes a protected path, and its reviewer checks that the program
# cannot run text.
PLAIN = {"echo", "printf", "cat", "tee", "grep", "egrep", "fgrep", "head", "tail", "wc", "uniq",
         "cut", "tr", "ls", "mkdir", "touch", "rm", "cp", "mv", "chmod", "ln", "diff", "cmp",
         "sha256sum", "base64", "test", "[", "true", "false", ":"}
# The plain text tools that write nothing. Every other one writes, moves or removes a file (tee, cp,
# mv, ln, touch, mkdir, chmod, rm and uniq today), and each of its arguments is a place test 1
# judges. A tool added to PLAIN later counts as writing unless this list names it.
NO_WRITE = {"echo", "printf", "cat", "grep", "egrep", "fgrep", "head", "tail", "wc", "cut", "tr", "ls",
            "diff", "cmp", "sha256sum", "base64", "test", "[", "true", "false", ":"}
WRITERS = PLAIN - NO_WRITE
# What the guard does not read: an expansion or a substitution, a glob, a brace, a tilde, and a
# backslash before a newline. In a place a command writes, the path is then not known. In text a
# program may run, the name it spells is then not known.
CONSTRUCT = re.compile(r"[$\x60*?\[\]{}~]|\\\n")
# git or config anywhere in a place, in any letter case, not only as a whole word: .git/config, a
# hook under .git/hooks, .gitconfig, a path under .config/git.
CONFIGURATION = re.compile(r"git|config", re.I)
# Every builtin of bash, as enable -a lists them. A builtin can change which program a name runs or
# keep text for later, so a command word in this list and not in ALLOWED_BUILTINS puts the command
# outside the subset. Suite 141 fails on a host whose bash has a builtin this list lacks.
SHELL_BUILTINS = frozenset("""
    . : [ alias bg bind break builtin caller cd command compgen complete compopt continue declare
    dirs disown echo enable eval exec exit export false fc fg getopts hash help history jobs kill
    let local logout mapfile popd printf pushd pwd read readarray readonly return set shift shopt
    source suspend test times trap true type typeset ulimit umask unalias unset wait
""".split())
# The nine that change nothing a later command word depends on. Allowing one more is a change to a
# protected path, judged like a new plain text tool. printf stays here only without a -v word.
ALLOWED_BUILTINS = {"echo", "printf", "test", "[", "true", "false", ":", "cd", "pwd"}
RESERVED = {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case", "esac",
            "select", "function", "time", "coproc", "in", "!", "[[", "]]"}
STRINGS = ("single", "double", "body")  # what can be data: a quoted string, a heredoc body
SHELL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[[^\]]*\])?\+?=")
DELIMITER = re.compile("\\\\?([A-Za-z0-9_.-]+)|'([A-Za-z0-9_.-]+)'|\"([A-Za-z0-9_.-]+)\"")
BARE = re.compile(r"[A-Za-z0-9_./+@%:,~-]+")
# git or gh in any letter case wherever no letter, digit or underscore stands right before or after
# it: a command word, part of a path (/usr/bin/git, .git/config), an argument, a string given to a
# shell.
GIT_NAME = re.compile(r"(?<![A-Za-z0-9_])(?:git|gh)(?![A-Za-z0-9_])", re.I)
UNQUOTE = str.maketrans("", "", "'\"\\")  # every quote character and backslash, deleted before that test
# The text git and gh store and never run: the value of these options, for these subcommands only.
GIT_STORED = {"commit": ("-m", "--message"), "tag": ("-m", "--message"), "notes": ("-m", "--message"),
              "stash": ("-m", "--message"), "log": ("--grep",), "show": ("--grep",), "rev-list": ("--grep",)}
GH_STORED = (("issue", "create"), ("issue", "comment"), ("issue", "edit"), ("pr", "create"), ("pr", "comment"),
             ("pr", "edit"), ("pr", "review"), ("release", "create"))
GH_FLAGS = ("-t", "--title", "-b", "--body", "-n", "--notes")


class Unparsed(Exception):
    """A construct outside the subset: the scanner gives up and the whole command is judged as written."""


class Part:
    """One stretch of the command: a run of unquoted text, a quoted string or a heredoc body. `expands`
    says the shell expands it (a $ or a backquote in it)."""

    def __init__(self, kind, start, end, expands=False):
        self.kind, self.start, self.end, self.expands = kind, start, end, expands
        self.role, self.command = None, None


class Word:
    """A word: its parts, and its text after quote removal (an expansion stays as written)."""

    def __init__(self, start):
        self.start, self.end, self.text, self.parts, self.glob = start, start, "", [], False

    def expands(self):
        return any(part.expands for part in self.parts)

    def quoted(self):
        return any(part.kind != "bare" for part in self.parts)


class Command:
    """A simple command: its command word and arguments, the pipeline it belongs to, and the target
    of each of its redirections that is not an input (`writes`)."""

    def __init__(self, pipeline, index):
        self.pipeline, self.index, self.words, self.writes = pipeline, index, [], []


def comment_end(text, at):
    """Where the comment starting at `at` ends: the next newline. A backslash before that newline
    does not continue a comment."""
    end = text.find("\n", at)
    return len(text) if end < 0 else end


def scan(text):
    """(the simple commands of `text`, their parts in text order, the comments), or Unparsed. The
    scanner must never read as a string, a comment or a heredoc body what bash reads as a command."""
    n, at = len(text), 0
    commands, parts, comments, pending = [], [], [], []
    state = {"command": None, "pipeline": 0, "joined": False}

    def expansion(at):
        """Where the $NAME or ${NAME} starting at `at` ends."""
        name = SHELL_NAME.match(text, at + 1)
        if name:
            return name.end()
        if text.startswith("{", at + 1):
            name = SHELL_NAME.match(text, at + 2)
            if name and text.startswith("}", name.end()):
                return name.end() + 1
        if text.startswith("\x28", at + 1):
            raise Unparsed("a command substitution or arithmetic")
        if text.startswith("'", at + 1):
            raise Unparsed("a $'...' string")
        raise Unparsed("an expansion other than $NAME or ${NAME}")

    def word(at):
        """(the word starting at `at`, where it ends). Digits right before a redirection operator are
        that redirection's descriptor: (None, where the operator starts)."""
        w, bare = Word(at), None
        while at < n:
            c = text[at]
            if c in " \t\n;&|()":  # where a word ends; a # inside a word is an ordinary character
                break
            if c in "<>":
                if w.parts and not w.quoted() and re.fullmatch(r"[0-9]+", text[w.start:at]):
                    return None, at
                break
            if c == "'":
                end = text.find("'", at + 1)  # nothing escapes inside single quotes
                if end < 0:
                    raise Unparsed("an unterminated quote")
                w.parts.append(Part("single", at, end + 1))
                w.text += text[at + 1:end]
                at, bare = end + 1, None
                continue
            if c == '"':
                end, expands = at + 1, False
                while end < n and text[end] != '"':
                    if text[end] == "\\" and end + 1 < n and text[end + 1] in "$\x60\"\\\n":
                        w.text += "" if text[end + 1] == "\n" else text[end + 1]
                        expands = expands or text[end + 1] in "$\x60"
                        end += 2
                        continue
                    if text[end] == "$":
                        after = expansion(end)
                        w.text += text[end:after]
                        end, expands = after, True
                        continue
                    if text[end] == "\x60":
                        raise Unparsed("a command substitution")
                    w.text += text[end]
                    end += 1
                if end >= n:
                    raise Unparsed("an unterminated quote")
                w.parts.append(Part("double", at, end + 1, expands))
                at, bare = end + 1, None
                continue
            if bare is None:
                bare = Part("bare", at, at)
                w.parts.append(bare)
            if c == "\\":
                if text.startswith("\n", at + 1):
                    at += 2  # a backslash before a newline joins the lines
                elif at + 1 < n:
                    w.text += text[at + 1]
                    at += 2
                else:
                    w.text += c
                    at += 1
            elif c == "$":
                after = expansion(at)
                w.text += text[at:after]
                at, bare.expands = after, True
            elif c == "\x60":
                raise Unparsed("a command substitution")
            elif c in "{}":
                raise Unparsed("a brace")
            else:
                w.glob = w.glob or c in "*?["
                w.text += c
                at += 1
            bare.end = at
        w.end = at
        return w, at

    def current():
        if state["command"] is None:
            state["command"] = Command(state["pipeline"], len(commands))
            commands.append(state["command"])
        return state["command"]

    def close(joined):
        """End the simple command being read. `joined`: a | carries its pipeline on to the next one."""
        state["command"], state["joined"] = None, joined
        state["pipeline"] += 0 if joined else 1

    def place(w, role, command):
        for part in w.parts:
            part.role, part.command = role, command.index
            parts.append(part)

    def bodies(at):
        """Read the body of every pending heredoc, the first one starting at `at`. Returns where the
        commands go on: the line after the last delimiter line."""
        while pending:
            delimiter, strip, quoted, command = pending.pop(0)
            start = at
            while True:
                end = text.find("\n", at)
                line = text[at:] if end < 0 else text[at:end]
                if (line.lstrip("\t") if strip else line) == delimiter:
                    break
                if end < 0:
                    raise Unparsed("an unterminated heredoc")
                if not quoted and line.endswith("\\"):
                    raise Unparsed("a line joined by a backslash in a heredoc body")
                at = end + 1
            body = Part("body", start, at, not quoted and any(c in text[start:at] for c in "$\x60"))
            body.role, body.command = "body", command
            parts.append(body)
            at = n if end < 0 else end + 1
        return at

    def redirect(at):
        """Read the redirection whose operator starts at `at`; returns where it ends."""
        command = current()
        if text.startswith("<<<", at):
            raise Unparsed("a here-string")
        if text.startswith("<<", at):
            at += 2
            dash = text.startswith("-", at)
            at += dash
            strip = dash  # <<- strips the leading tabs of the delimiter line
            while at < n and text[at] in " \t":
                at += 1
            name = DELIMITER.match(text, at)
            if name is None or (name.end() < n and text[name.end()] not in " \t\n;&|<>"):
                raise Unparsed("a heredoc delimiter the guard does not read")
            delimiter = name.group(1) or name.group(2) or name.group(3)
            pending.append((delimiter, strip, name.group(0) != delimiter, command.index))
            return name.end()  # the body starts after the next newline, not right after this word
        operator = next(op for op in ("<>", "<&", ">>", ">&", ">|", "<", ">") if text.startswith(op, at))
        at += len(operator)
        while at < n and text[at] in " \t":
            at += 1
        if at >= n or text[at] in "\n;&|()<>#":
            raise Unparsed("a redirection without a word target")
        target, at = word(at)
        if target is None:
            raise Unparsed("a redirection without a word target")
        place(target, "target", command)
        if operator not in ("<", "<&"):
            command.writes.append(target)  # a place the command writes
        return at

    while at < n:
        c = text[at]
        if c in " \t":
            at += 1
        elif text.startswith("\\\n", at):
            at += 2
        elif c == "\n":
            at = bodies(at + 1)
            if state["command"] is not None or not state["joined"]:
                close(False)  # a newline after | does not end the pipeline
        elif c == "#":
            end = comment_end(text, at)
            comments.append((at, end))
            at = end
        elif c == ";":
            if text.startswith((";;", ";&"), at):
                raise Unparsed("a case clause")
            close(False)
            at += 1
        elif c == "&":
            if text.startswith("&>", at):
                raise Unparsed("a redirection without a word target")
            close(False)
            at += 2 if text.startswith("&&", at) else 1
        elif c == "|":
            if text.startswith("|&", at):
                raise Unparsed("a pipe of standard error")
            close(not text.startswith("||", at))
            at += 2 if text.startswith("||", at) else 1
        elif c in "()":
            raise Unparsed("a parenthesis: a subshell, a function or a substitution")
        elif c in "<>":
            at = redirect(at)
        else:
            w, at = word(at)
            if w is None:
                at = redirect(at)
                continue
            command = current()
            first = not command.words
            name = ASSIGNMENT.match(text, w.start) if first and w.parts[0].kind == "bare" else None
            if name and name.end() <= w.parts[0].end:
                raise Unparsed("the assignment %s" % name.group(1))
            if first and text[w.start:w.end] in RESERVED:
                raise Unparsed("the reserved word %s" % w.text)
            if first and w.expands():
                raise Unparsed("an expansion in a command word")
            if first and w.glob and w.text != "[":
                raise Unparsed("a glob character in a command word")
            command.words.append(w)
            place(w, "command" if first else "argument", command)
    if pending:
        raise Unparsed("an unterminated heredoc")
    for command in commands:
        head = command.words[0].text if command.words else ""
        if head in SHELL_BUILTINS and head not in ALLOWED_BUILTINS:
            raise Unparsed("the builtin %s" % head)
        if head == "printf" and any(w.text.startswith("-v") for w in command.words[1:]):
            raise Unparsed("the builtin printf with a word that starts with -v")
    return commands, parts, comments


def program(command):
    """The command's program as written: its command word after quote removal."""
    return command.words[0].text[:60] if command.words else "a command with no command word"


def plain(command):
    """Whether the command is a plain text tool: a bare name with no slash, in the fixed set. A copy
    of a shell named cat and called by its path is not one."""
    name = command.words[0].text if command.words else ""
    return name in PLAIN


def plain_pipelines(commands):
    """The pipelines whose every command is a plain text tool."""
    tools = {}
    for command in commands:
        tools.setdefault(command.pipeline, []).append(plain(command))
    return {pipeline for pipeline, each in tools.items() if all(each)}


def held(commands, parts):
    """The parts that are data where they stand: a quoted string or a heredoc body the shell does not
    expand, in a pipeline whose every command is a plain text tool."""
    quiet = plain_pipelines(commands)
    return [part for part in parts
            if part.kind in STRINGS and not part.expands and part.role in ("argument", "target", "body")
            and commands[part.command].pipeline in quiet]


def configuration_write(command, commands, outside):
    """Test 1: the reason the command may write git configuration, or None. The places a command
    writes are the target of every redirection that is not an input and every argument of a plain
    text tool that writes. A place is outside git's configuration only when its word as written
    holds no construct the guard does not read and its text after quote removal holds neither git
    nor config anywhere. `outside` is the text outside comments and data strings: the word config in
    it, with quotes and backslashes deleted, counts too (git config, the GIT_CONFIG variables,
    XDG_CONFIG_HOME). The test never asks how a later command spells git."""
    sites = [w for one in commands for w in one.writes]
    sites += [w for one in commands if one.words and one.words[0].text in WRITERS for w in one.words[1:]]
    for w in sorted(sites, key=lambda site: site.start):
        written = command[w.start:w.end]
        if CONSTRUCT.search(written) or CONFIGURATION.search(w.text):
            return "a write the guard reads as git configuration: %s" % written[:120]
    if "config" in outside.translate(UNQUOTE).lower():
        return "the word config outside data, which the guard reads as a write to git configuration"
    return None


def run_construct(commands, parts, outside):
    """Test 2: the reason text a program may run holds a construct the guard does not read, or None.
    The text read is `outside` (the command without its comments and data strings) without the
    words, redirection targets and heredoc bodies of the plain text tools in a pipeline of only
    plain text tools: those reach the output or a file, and every file is a place test 1 judges.
    What is left is every string given to a shell, a wrapper or an interpreter and the command word
    and arguments of every program that is not a plain text tool."""
    quiet = plain_pipelines(commands)
    run = list(outside)
    for part in parts:
        own = commands[part.command]
        if plain(own) and own.pipeline in quiet:
            run[part.start:part.end] = " " * (part.end - part.start)
    hit = CONSTRUCT.search("".join(run))
    if hit is None:
        return None
    what = "a backslash before a newline" if hit.group(0).startswith("\\") else "the construct " + hit.group(0)
    return what + " in text a program may run"


def stored(command):
    """The words of a git or gh command that hold text it stores and never runs. Git, as the bare
    word git with no global option other than -C: the value of -m or --message for commit, tag, notes
    and stash, and of --grep for log, show and rev-list. Gh, as the bare word gh: the value of -t, -b,
    -n, --title, --body or --notes for the listed subcommands. A value the shell expands stays live."""
    words = command.words
    texts = [w.text for w in words]
    flags, at = (), 1
    if texts[:1] == ["git"]:
        while texts[at:at + 1] == ["-C"]:
            at += 2
        flags = GIT_STORED.get(texts[at] if at < len(texts) else None, ())
        at += 1
    elif texts[:1] == ["gh"] and tuple(texts[1:3]) in GH_STORED:
        flags, at = GH_FLAGS, 3
    out = []
    while flags and at < len(words) and texts[at] != "--":
        if texts[at] in flags:
            out += words[at + 1:at + 2]
            at += 2
            continue
        if texts[at].startswith("--") and "=" in texts[at] and texts[at].split("=", 1)[0] in flags:
            out.append(words[at])
        at += 1
    return [w for w in out if not w.expands()]


def names_git(text):
    """Test 3: whether the text names git or gh once every quote character and backslash is deleted.
    It reads no expansion and no escape: an expansion or a joined line in text a program may run is
    test 2's, and one in a path is test 1's."""
    return bool(GIT_NAME.search(text.translate(UNQUOTE)))


def live_text(command):
    """(the text the judgment reads, what the scanner saw): the command with each comment dropped,
    each heredoc body and quoted string that is data written as a placeholder word, and each command
    word written after quote removal. A command outside the subset is returned as written, with the
    construct that put it there. So is a command test 1 or test 2 refuses to read, with the reason."""
    try:
        commands, parts, comments = scan(command)
    except Unparsed as error:
        return command, str(error)  # outside the subset: the whole command is judged as written
    dropped = list(comments)  # a comment is never run
    strings = held(commands, parts)
    values = [w for one in commands for w in stored(one)]  # standing alone or in a longer command
    outside = list(command)
    for start, end in dropped + [(part.start, part.end) for part in strings]:
        outside[start:end] = " " * (end - start)
    outside = "".join(outside)
    reason = configuration_write(command, commands, outside)  # test 1
    reason = reason or run_construct(commands, parts, outside)  # test 2
    if reason:
        return command, reason  # the whole command is judged as written, with no part of it read as data
    spans = [(0, len(outside))]  # the whole text of the Bash call, across all its lines
    named = [span for span in spans if names_git(outside[span[0]:span[1]])]
    data = [part for part in strings if not any(a <= part.start < b for a, b in named)]
    swaps = [(start, end, "") for start, end in dropped]
    swaps += [(part.start, part.end, PLACEHOLDER + "\n" * (part.kind == "body")) for part in data]
    swaps += [(w.start, w.end, PLACEHOLDER) for w in values]
    swaps += [(w.start, w.end, w.text) for w in (c.words[0] for c in commands if c.words) if BARE.fullmatch(w.text)]
    live, marks, at, size = [], [(0, 0, False)], 0, 0
    for start, end, new in sorted(swaps, key=lambda swap: swap[:2]):
        if start < at:
            continue
        live += [command[at:start], new]
        size += start - at
        marks += [(size, start, True), (size + len(new), end, False)]
        size, at = size + len(new), end
    live.append(command[at:])
    return "".join(live), (commands, parts, strings, marks)


def position(at, seen):
    """Where the judged text at offset `at` sits in the command, in words."""
    commands, parts, strings, marks = seen
    live, raw, swapped = [mark for mark in marks if mark[0] <= at][-1]
    raw += 0 if swapped else at - live
    part = next((p for p in parts if p.start <= raw < p.end), None)
    if part is None or part.role == "command":
        return "as a command of a list or pipeline" if len(commands) > 1 else "as the command word"
    if part in strings:
        return "in text in a command that also names git or gh"
    own = commands[part.command]
    runner = next((c for c in [own] + [c for c in commands if c.pipeline == own.pipeline] if not plain(c)), None)
    if runner is not None:
        return "in the argument or input of %s, which is not a plain text tool" % program(runner)
    return "in words of %s that are not quoted or that the shell expands" % program(own)


def finding(text, seen):
    """What the judged text held and where, for the unresolved line of a command that is not one
    simple git or gh command: the matched text to the end of its line, cut at 120 characters."""
    match = PUSHISH.search(text) or re.search(r"alias\.\S*=", text, re.I)
    if match is None:
        return ""
    end = text.find("\n", match.start())
    shown = " ".join(text[match.start():len(text) if end < 0 else end].split())[:120]
    if isinstance(seen, str):
        return '; found "%s" in text the guard does not parse (%s)' % (shown, seen)
    return '; found "%s" %s' % (shown, position(match.start(), seen))


def destinations():
    """[(full ref name, None)] for each destination, or (None, reason) for one not resolved."""
    if os.environ.get("VELDO_GUARD_PATH") == "pre-push":
        ref = os.environ.get("VELDO_GUARD_REF", "")
        return [(ref, None)] if ref.startswith("refs/") else unresolved("VELDO_GUARD_REF is not a full ref name")
    # The judgment reads the live text: the command as the shell would run it (VELDO-0292).
    command, seen = live_text(os.environ.get("VELDO_GUARD_CMD", ""))
    cwd = os.environ.get("VELDO_GUARD_CWD") or "."
    if not os.path.isdir(cwd):
        cwd = "."
    words = words_of(command)
    if words is None or words[0] not in ("git", "gh"):
        FOUND.append(finding(command, seen))  # not one simple git or gh command
    if words is None:
        if names_push_or_merge(command, words):
            return unresolved("the command is not one simple git or gh command, so it cannot be reproduced")
        if alias_in_text(command, cwd):
            return unresolved("a git alias that may push or merge, in a command the guard cannot reproduce")
        return []
    if words[0] == "gh":
        if words[1:3] == ["pr", "create"]:
            return []  # gh pr create moves no ref
        if words[1:3] == ["pr", "merge"]:
            return gh_base(words[3:], cwd)
        if names_push_or_merge(command, words):
            return unresolved("the command is not one simple git or gh command, so it cannot be reproduced")
        return []
    at = next((i for i, w in enumerate(words) if w == "git" or w.endswith("/git")), None)
    if at is None:
        if names_push_or_merge(command, words):
            return unresolved("the command is not one simple git or gh command, so it cannot be reproduced")
        if alias_in_text(command, cwd):
            return unresolved("a git alias that may push or merge, in a command whose first word is not git")
        return []
    return judge_git(command, words[at:], cwd, at == 0 and words[0] == "git", words[:at])


def judge_git(command, words, cwd, reproduce, prefix=()):
    """The destinations of a git command, its aliases expanded as git expands them: an alias that
    expands to push or merge is judged as that command. Only a simple command starting with git is
    reproduced; any other that pushes or merges is unresolved. The alias is looked up where git runs
    (its -C and -c pairs); when an environment assignment before git or another global option may
    change where that is, a subcommand that may be an alias is unresolved."""
    elsewhere = git_globals(words) is None or any("=" in w or w == "env" for w in prefix)
    for _ in range(ALIAS_DEPTH):
        kept, sub, rest = git_split(words)
        if elsewhere and sub not in (None, "push", "merge") and maybe_alias(sub, cwd):
            return unresolved("git %s may be an alias in a repository or configuration the guard cannot "
                              "determine" % sub)
        elsewhere = False
        value = None if sub in (None, "push", "merge") else alias_of(kept, sub, cwd)
        if value is None:
            break
        if value.startswith("!"):
            if SHELL_ALIAS.search(value):
                return unresolved("git %s is a shell alias that may push or merge" % sub)
            break
        try:
            words = words[:1] + kept + shlex.split(value) + rest
        except ValueError:
            return unresolved("git %s is an alias the guard cannot read" % sub)
    else:
        return unresolved("git aliases nested deeper than the guard follows")
    if sub not in ("push", "merge"):
        if PUSHISH.search(command):
            return unresolved("git %s is not a push or merge the guard can reproduce" % sub)
        if alias_in_text(command, cwd):
            return unresolved("a git alias that may push or merge, in the text of a command that runs "
                              "another program (a wrapper's argument, an editor or a pager)")
        return []
    if not reproduce:
        return unresolved("the command is not one simple git or gh command, so it cannot be reproduced")
    split = git_globals(words)
    if split is None:
        return unresolved("git with options the guard does not reproduce")
    kept, sub, rest = split
    if sub == "push":
        return dry_run(kept, rest, cwd)
    return merge_target(kept, cwd)


def main():
    try:
        found = destinations()
    except AliasUnreadable as error:
        found = unresolved("git %s may be an alias, and the configuration where git runs could not be read"
                           % str(error)[:80])
    if not found:
        return 0
    path = Path(".veldo/policy_check.py")
    check = None
    if path.is_file():
        spec = importlib.util.spec_from_file_location("veldo_policy_check_refs", path)
        check = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check)
    protected = []
    for ref, reason in found:
        if ref is None:
            log("unresolved", "%s; treated as protected; %s" % (reason, CHECKS))
            protected.append("unresolved")
            continue
        if check is None:
            log(ref, "protected by * (no .veldo/policy_check.py to read protected_refs); %s" % CHECKS)
            protected.append(ref)
            continue
        try:
            hit = check.protected_ref(ref)
        except check.ProtectedRefsUnreadable as error:
            print("VELDO guard: blocked. %s" % error, file=sys.stderr)
            return 3
        if hit:
            log(ref, "protected by %s from %s; %s" % (hit[0], hit[1], CHECKS))
            protected.append(ref)
        else:
            log(ref, "not protected: the gate check applies when this lands")
    for ref in protected:
        print(ref)
    return 0


sys.exit(main())
PY
)
JUDGED_RC=$?
if [ "$JUDGED_RC" = "3" ]; then
  exit 2
fi
if [ "$JUDGED_RC" != "0" ]; then
  echo "VELDO guard: destination unresolved: the destination check failed (exit ${JUDGED_RC}); treated as protected" >&2
  JUDGED=unresolved
fi
if [ -z "$JUDGED" ]; then
  exit 0
fi

HEAD=$(git rev-parse --verify HEAD 2>/dev/null || echo "no-git")

# An evidence-only commit (touching only proof/, .veldo/, specs/) inherits its
# parent's proof: evidence does not need evidence about itself.
PARENT=$(git rev-parse HEAD^ 2>/dev/null || echo "")
EVIDENCE_ONLY=1
while IFS= read -r f; do
  [ -z "$f" ] && continue
  case "$f" in proof/*|.veldo/*|specs/*) ;; *) EVIDENCE_ONLY=0 ;; esac
done <<EOF
$(git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null)
EOF
ok_commit () {
  [ "$1" = "$HEAD" ] && return 0
  [ "$EVIDENCE_ONLY" = "1" ] && [ -n "$PARENT" ] && [ "$1" = "$PARENT" ] && return 0
  return 1
}

# Emergency lane: a human-set VELDO_EMERGENCY=1 allows the push and records it.
if [ "${VELDO_EMERGENCY:-0}" = "1" ]; then
  printf '{"schema":"veldo.event/v1","type":"emergency.push","commit":"%s","at":"%s","producer":"veldo-guard"}\n' \
    "$HEAD" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> .veldo/events.jsonl
  echo "VELDO guard: emergency lane used; backfill the specification, proof, and review within the policy window." >&2
  exit 0
fi

# Guard 0 (VELDO-0270): proof is small summaries, never raw bulk. When git's pre-push ref lines
# are handed over (VELDO_PUSH_REFS, set by the packs' hooks/pre-push, remote in
# VELDO_PUSH_REMOTE), every commit a push to a protected ref sends that the remote does not
# already have is judged, not only the tip: a proof file over proof.max_file_bytes or a base64
# encoded archive is refused, naming the ref and the commit that added it. One implementation,
# the contract validator's, so the gate and the guard cannot disagree.
if [ -n "${VELDO_PUSH_REFS:-}" ] && [ -f .veldo/validate.py ]; then
  if ! printf '%s\n' "$VELDO_PUSH_REFS" | python3 .veldo/validate.py push-proof "${VELDO_PUSH_REMOTE:-}" >&2; then
    echo "VELDO guard: blocked. The push adds a proof file over the limit or an encoded archive; proof is small summaries, never raw bulk." >&2
    exit 2
  fi
fi

# Guard 1: the gate must be green for exactly this commit.
if [ -f .veldo/last_verify ]; then
  V_COMMIT=$(python3 -c 'import json;print(json.load(open(".veldo/last_verify"))["commit"])' 2>/dev/null || echo "")
  V_STATUS=$(python3 -c 'import json;print(json.load(open(".veldo/last_verify"))["status"])' 2>/dev/null || echo "")
else
  V_COMMIT=""; V_STATUS=""
fi
if [ "$V_STATUS" != "green" ] || ! ok_commit "$V_COMMIT"; then
  echo "VELDO guard: blocked. The canonical gate is not green for HEAD (${HEAD})." >&2
  echo "Run ./scripts/verify.sh on the current state first. Proof is valid only for the state it ran against." >&2
  exit 2
fi

# Positive reuse must carry authenticated non-agent records bound to this commit.
if ! python3 -I -c '
import importlib.util, json, pathlib, sys
stamp = json.load(open(".veldo/last_verify"))
base = pathlib.Path(sys.argv[1]).resolve().parents[1]
source = base / ".veldo/reuse_evidence.py"
if not source.is_file():
    source = base.parent.parent / "engine/.veldo/reuse_evidence.py"
spec = importlib.util.spec_from_file_location("reuse_evidence", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
if module.landing_problem(stamp):
    raise SystemExit(1)
' "${BASH_SOURCE[0]}"; then
  echo "VELDO guard: blocked. Landing requires authenticated non-agent reuse evidence or zero reused results." >&2
  exit 2
fi

# Guard 2: a proof manifest must exist for exactly this commit.
# THROUGH THE ONE CORPUS ENUMERATION (WARP-0727), not a shell glob. `proof/*/manifest.json`
# here was a FOURTH implementation of one set, after the projection, the contract validator and
# the policy reader, and a shell glob's reach is its own: it does not cross `/`, and dotglob,
# nullglob, GLOBIGNORE and the locale's collation all change what it answers. It computed the
# same set as the owner on this platform, which is what made it a law violation rather than a
# live divergence. THE FAILURE DIRECTION HERE, STATED AS MEASURED AND NOT AS HOPED: if the owner
# module is missing, unreadable or raises, FOUND stays empty and the push is BLOCKED, which is the
# same direction the shell glob already failed in (driven three ways: no module, corrupt module,
# no manifest). THAT IS NOT TRUE OF python3 ITSELF, and the earlier claim that it was is deleted
# rather than softened: with no python3 on PATH the payload parse at the top of this script
# returns an EMPTY command, the push-and-merge match above therefore does not fire, and the guard
# stands down at exit 0 having checked nothing. That fail-open predates this item (it is
# byte-identical at ffaab41), it is a property of the payload parse and not of this lookup, and
# closing it is a separate item: it needs a python3-independent way to read the hook JSON, or a
# refusal when the parse itself could not run.
FOUND=$(VELDO_HEAD="$HEAD" VELDO_PARENT="$PARENT" VELDO_EVIDENCE_ONLY="$EVIDENCE_ONLY" python3 - <<'PY' 2>/dev/null
import importlib.util, json, os
from pathlib import Path

ROOT = Path(".").resolve()
_s = importlib.util.spec_from_file_location("veldo_verdict_corpus",
                                            ROOT / ".veldo" / "verdict_corpus.py")
_vc = importlib.util.module_from_spec(_s)
_s.loader.exec_module(_vc)
head = os.environ.get("VELDO_HEAD", "")
parent = os.environ.get("VELDO_PARENT", "")
evidence_only = os.environ.get("VELDO_EVIDENCE_ONLY", "") == "1"


def ok_commit(c):
    """The same rule the shell function of that name applies: exactly HEAD, or the parent when
    this commit only touched evidence."""
    if c and c == head:
        return True
    return bool(evidence_only and parent and c == parent)


for rel in _vc.disk_corpus(ROOT, _vc.MANIFEST_PATTERN):
    try:
        m = json.loads((ROOT / rel).read_text())
    except Exception:
        continue
    if ok_commit(m.get("commit", "")):
        print(rel)
        break
PY
)
if [ -z "$FOUND" ]; then
  echo "VELDO guard: blocked. No proof manifest found for HEAD (${HEAD})." >&2
  echo "Produce proof/<spec-id>/manifest.json mapping every acceptance criterion to evidence (/veldo:proof)." >&2
  exit 2
fi

# Guard 3: policy - protected paths need a live approval; open emergency debt
# blocks ordinary pushes (the mechanical reader of .veldo/policy.yaml).
if [ -f .veldo/policy_check.py ]; then
  if ! python3 .veldo/policy_check.py >&2; then
    exit 2
  fi
fi

exit 0
