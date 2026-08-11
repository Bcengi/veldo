#!/usr/bin/env bash
# VELDO Antigravity CLI (agy) hook - enforce the push gate from agy's before-tool-call lifecycle hook.
#
# agy runs this before a tool call. If the tool is a shell command that pushes or merges, this
# delegates to the shared engine guard (scripts/veldo-guard.sh), which refuses it unless HEAD has a
# passing commit-bound verdict and any protected path is covered by an approval. The guaranteed gate
# is still the git pre-push hook (hooks/pre-push) plus the CI required status check.
#
# The guard reads the command from a JSON payload on STDIN (tool_input.command), NOT from an env var,
# so this builds that payload from the pending command (json.dumps, injection-safe) and pipes it in.
# agy passes the pending command via the environment or on stdin; this reads both.
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
GUARD="$ROOT/scripts/veldo-guard.sh"

CMD="${AGY_COMMAND:-${ANTIGRAVITY_COMMAND:-}}"
if [ -z "$CMD" ] && [ ! -t 0 ]; then
  CMD="$(cat 2>/dev/null || true)"
fi

case "$CMD" in
  *"git push"*|*"git merge"*|*"gh pr merge"*|*"gh pr create"*)
    if [ -f "$GUARD" ]; then
      python3 -c 'import json,sys; sys.stdout.write(json.dumps({"tool_input":{"command":sys.argv[1]}}))' "$CMD" | bash "$GUARD"
      exit $?
    fi
    ;;
esac
exit 0
