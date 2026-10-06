# VELDO-0208 FIX FIRST follow-up

Work begins at 80b02ff2 on build-gate-reuse. No push, merge, full gate or mutation
stage is run here. The reviewer owns the fresh merged-tree gate and stamp.

## Candidate execution boundary

The gate executes candidate commands through the authority launcher. Registry
imports are confined; mutation worker entry/driver code comes from authority.
The coordinator alone reads/publishes reusable records, validates its launched
worker observations, and writes the receipt outside candidate write grants.
Worker output files are outside worker scratch and observed through inherited
stdout/stderr, with exit status checked. Candidate stage receipts are not ingested.

Targeted suite: `python3 scripts/selftest.py --suite 100_veldo_0208_landing_reuse`.
First pass: 107 passed, 0 failed; selector exit 2 denotes partial, not a gate pass.
Includes a planted suite whose Store.put attempt fails and reddens the command
with an explicit store-denied-domain message. Full gate remains unrun.

## Authority identity

Authenticated records and landing receipts carry the authority engine digest.
Declared case keys include it too. Landing recomputes the digest from its own
trusted installation; correctly signed other-engine records/receipts fail.
The engine now ships the generic observer and reuse boundary modules, including
its config, as canonical byte-identical copies. Candidate drivers only supply
registry data through confined enumeration.

Second targeted pass: 110 passed, 0 failed (partial exit 2). Planted signed records
and receipts with another authority identity are rejected; case keys also change.

## Git guard and persistence

Third targeted pass: 112 passed, 0 failed (partial exit 2). A redirected .git with
plausible commondir/backlink is refused by both the Git wrapper and agent launcher.
Hostile fsmonitor/hooks settings in config and GIT_CONFIG_* cannot execute scripts.
The wrapped agent still adds and commits in its own linked worktree while writes
to shared config/hooks, the authority and another worktree's index are denied.

External codex_work.sh and claude_work.sh must replace candidate Git invocations
with the following exact form, using AUTHORITY and TRUSTED_COMMON set by the owner
from the authority checkout, never read from the candidate or its environment:

```bash
python3 -I -S "$AUTHORITY/.veldo/candidate_git.py" --root "$worktree" --expected-common "$TRUSTED_COMMON" --validate-only || exit 1
python3 -I -S "$AUTHORITY/.veldo/candidate_git.py" --root "$worktree" --expected-common "$TRUSTED_COMMON" -- status --porcelain
```

The helper validates again, strips all inherited GIT_* variables, sets
GIT_CONFIG_NOSYSTEM=1, GIT_CONFIG_SYSTEM=/dev/null, GIT_CONFIG_GLOBAL=/dev/null,
GIT_NO_REPLACE_OBJECTS=1 and GIT_TERMINAL_PROMPT=0, pins GIT_COMMON_DIR and uses:

```text
/usr/bin/git --git-dir=<validated> --work-tree=<candidate> -c core.hooksPath=/dev/null -c core.fsmonitor=false status --porcelain
```

Do not validate then run a separate bare git command: the helper pins discovery
paths for the actual command. Shared ref/object grants expose sibling refs and
objects; authority storage must stay outside all agent-readable gitdirs.
