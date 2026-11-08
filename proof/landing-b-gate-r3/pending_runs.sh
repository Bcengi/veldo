#!/usr/bin/env bash
# landing-b gate round 3: runs for the lead, under the shared host gate lock, from the worktree root.
# Red 1 (personal_setup): fe0a171a, verify.sh writes the stamp's host lock path with home as ~;
#   suite 113 reads it as written.
# Red 2 (mutation driver_error): 7a568e94, the mutation anchors VELDO-0260 moved
#   (reland148-stale-left-failed in control_landing_station.py, dest235-local-also-pushes in
#   control_landing.py) follow the rewritten lines.
# Before the gate: the working tree carries the stamp and two gate.failed lines the old writer
# wrote (uncommitted .veldo/last_verify and .veldo/events.jsonl lines 1396-1397, host lock with
# the full home path). The personal-setup stage judges uncommitted lines, so they stay red until
# discarded (git checkout -- .veldo/last_verify .veldo/events.jsonl); the lead decides.
set -eu
cd "$(dirname "$0")/../.."
LOCK=$HOME/.local/state/core-gates/.gate.lock
flock -w 1200 "$LOCK" python3 scripts/selftest.py --suite 113_veldo_0220_gate_host
flock -w 1200 "$LOCK" python3 scripts/selftest.py --suite 86_veldo_0148_re_land
flock -w 1200 "$LOCK" python3 scripts/selftest.py --suite 128_veldo_0235_land_locally
# Drives suite 86's (and 128's) baseline, noop and mutant in mutation workers.
flock -w 1200 "$LOCK" python3 scripts/check_gate_mutations.py --case reland148-stale-left-failed --case dest235-local-also-pushes
python3 scripts/check_personal_setup.py
