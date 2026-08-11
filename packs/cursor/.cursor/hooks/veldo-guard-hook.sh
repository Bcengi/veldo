#!/usr/bin/env bash
# VELDO Cursor hook - early enforcement of the push gate from inside the editor.
#
# Cursor runs this before a shell execution. If the command Cursor is about to run is a push or
# merge, this delegates to the shared engine guard (scripts/veldo-guard.sh), which refuses it unless
# HEAD has a passing commit-bound verdict and any protected path is covered by an approval. This is
# EARLY feedback; the guaranteed gate is the git pre-push hook (hooks/pre-push) plus the CI required
# status check, because Cursor's editor commands are not the only push path.
#
# The guard reads the command from a JSON payload on STDIN (tool_input.command), NOT from an env
# var, so this builds that payload from the pending command and pipes it in.
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
GUARD="$ROOT/scripts/veldo-guard.sh"

# Read the pending command from the environment Cursor provides, else from stdin (JSON or raw).
CMD="${CURSOR_COMMAND:-${CURSOR_SHELL_COMMAND:-}}"
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
