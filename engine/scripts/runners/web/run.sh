#!/usr/bin/env bash
# Thin harness for the VELDO web journey runner. Resolves the Playwright module
# from the global node install so the runner can be a standalone script, then
# drives one journey. A consuming repo points this at its own journeys and
# wires it into the gate's journeys slot.
#
#   run.sh <journey.json> [outdir]
#
# Exit code is the runner's: 0 = flow proven and a11y clean, 1 = failure.
set -u
here="$(cd "$(dirname "$0")" && pwd)"
if ! command -v node >/dev/null 2>&1; then
  echo "web runner: node not found" >&2; exit 2
fi
export NODE_PATH="${NODE_PATH:-$(npm root -g 2>/dev/null)}"
exec node "$here/veldo-web-runner.mjs" "$@"
