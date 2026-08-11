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

# Only guard merge-ish and push-ish commands; everything else passes through.
if ! printf '%s' "$CMD" | grep -qE '(git (push|merge)|gh pr (merge|create))'; then
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
