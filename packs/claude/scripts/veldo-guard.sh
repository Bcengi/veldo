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

# Only guard merge-ish and push-ish commands; everything else passes through. Without a tool
# payload, a git pre-push hook's call names its one destination in VELDO_GUARD_REF.
if [ -n "$CMD" ]; then
  if ! printf '%s' "$CMD" | grep -qE '(git (push|merge)|gh pr (merge|create))'; then
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
import importlib.util, os, re, shlex, subprocess, sys
from pathlib import Path

CHECKS = "runs the gate stamp, reuse evidence, proof manifest and policy_check checks"
OPERATOR = set("();<>|&")
EXPANSION = ("$", "\x60", "\n")


def log(ref, text):
    print("VELDO guard: destination %s: %s" % (ref, text), file=sys.stderr)


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


def git_globals(words):
    """(the global options before the subcommand, the subcommand, its arguments), or None."""
    at, kept = 1, []
    while at < len(words) and words[at] in ("-C", "-c"):
        if at + 1 >= len(words):
            return None
        kept += words[at:at + 2]
        at += 2
    if at >= len(words) or words[at].startswith("-"):
        return None
    return kept, words[at], words[at + 1:]


def dry_run(kept, rest, cwd):
    """Git's own answer for where this push goes: the same push, dry run, porcelain, no hooks."""
    if any(w.startswith(("--no-dry", "--no-porc")) for w in rest):
        return unresolved("the command turns the dry run off, so it cannot be reproduced")
    try:
        r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null"] + kept
                           + ["push", "--dry-run", "--porcelain", "--no-verify"] + rest,
                           cwd=cwd, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:
        return unresolved("the dry run did not run (%s)" % type(error).__name__)
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["exit %d" % r.returncode])[-1]
        return unresolved("the dry run failed: %s" % tail[:200])
    found = []
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and len(parts[0]) == 1 and ":" in parts[1]:
            found.append((parts[1].rsplit(":", 1)[1], None))
    return found


def merge_target(kept, cwd):
    """The branch git merge moves: the one checked out where it runs."""
    r = subprocess.run(["git"] + kept + ["symbolic-ref", "-q", "HEAD"], cwd=cwd,
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


def destinations():
    """[(full ref name, None)] for each destination, or (None, reason) for one not resolved."""
    if os.environ.get("VELDO_GUARD_PATH") == "pre-push":
        ref = os.environ.get("VELDO_GUARD_REF", "")
        return [(ref, None)] if ref.startswith("refs/") else unresolved("VELDO_GUARD_REF is not a full ref name")
    command = os.environ.get("VELDO_GUARD_CMD", "")
    cwd = os.environ.get("VELDO_GUARD_CWD") or "."
    if not os.path.isdir(cwd):
        cwd = "."
    words = words_of(command)
    if words is None:
        if not re.search(r"(git (push|merge)|gh pr merge)", command):
            return []  # gh pr create only: it moves no ref
        return unresolved("the command is not one simple git or gh command, so it cannot be reproduced")
    if words[0] == "gh" and words[1:3] == ["pr", "create"]:
        return []
    if words[0] == "gh" and words[1:3] == ["pr", "merge"]:
        return gh_base(words[3:], cwd)
    if words[0] != "git":
        return unresolved("the command is not one simple git or gh command, so it cannot be reproduced")
    split = git_globals(words)
    if split is None:
        return unresolved("git with options the guard does not reproduce")
    kept, sub, rest = split
    if sub == "push":
        return dry_run(kept, rest, cwd)
    if sub == "merge":
        return merge_target(kept, cwd)
    return unresolved("git %s is not a push or merge the guard can reproduce" % sub)


def main():
    path = Path(".veldo/policy_check.py")
    check = None
    if path.is_file():
        spec = importlib.util.spec_from_file_location("veldo_policy_check_refs", path)
        check = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(check)
    protected = []
    for ref, reason in destinations():
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
