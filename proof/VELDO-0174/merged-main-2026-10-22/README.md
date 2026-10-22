# VELDO-0174 on main d49581b4, 2026-10-22

Status: BLOCKED on the same two host rows as before; nothing else regressed on the merged tree.
This is focused evidence, not a gate stamp, a review verdict or a landing decision.

Branch agent/claude/fix-VELDO-0174 is agent/codex/veldo-0174-b2 (9d82fcf8) with main d49581b4
merged in (only WARP-1404 evidence and suite 15 came from main; no conflicts). Direct results and
log digests are in results.json beside this file; the per-case falsifier records are the JSON
files next to it.

## What ran here

- `python3 scripts/selftest.py --suite 107_veldo_0174_conversations`: 36 ticket rows pass, 62 of
  64 assertions pass. The two failures are AC1/restart-open and AC2/restart-turns, both raising
  `PermissionError: [Errno 1] Operation not permitted` from `socket.socket(AF_UNIX)` in
  control_client.py. This sandbox denies AF_UNIX; the rows still need a host.
- The two suites batch 2 recorded as failing and never reran now pass on the merged tree:
  105_veldo_0182_memory (127 rows, 0 failed; main's e8abb5f6 made worker/backfill-bounded
  load-tolerant) and 103_veldo_0142_git_identities (23 rows, 0 failed).
- Six further affected suites fail here: 67_veldo_0056_candidates, 92_veldo_0088_pm_cycles,
  93_veldo_0152_intake_routes, 94_veldo_0162_configuration_routes, 95_veldo_0203_owner_revisions,
  96_veldo_0204_reservation_policies. Each was rerun on a detached checkout of main d49581b4 in
  the same sandbox and fails with the identical set of rows (results.json, affected_suites).
  Suites 92 to 96 are in the gate's unconfined leg and need the user service manager; their
  detail lines say runtime_unavailable, unavailable_service:profile:user_manager and "the
  ingress configuration is absent". These are sandbox failures, not VELDO-0174 regressions.
- Every finding-174 mutation anchor occurs exactly once on the merged tree.
- `python3 scripts/check_teeth_mutations.py --finding 174` cannot run here: the nested agent
  sandbox refuses to start (candidate_execution_denied). The ticket's own driver
  run_falsifier.py was used instead, one case at a time, source restored in finally.
- Static checks on the merged tree all exit 0: lint, docs, template sync, secret inventory
  (0 outstanding), validate.py all, check_generated.sh.

## Fix in this round

run_falsifier.py was broken by the ticket's own commit 2cd6c93b: the two proof-meta
registrations (v174-mutation-siblings-missing, v174-signed-commands-bypass-mutant) pass the
suite through the name `S174` and target scripts/ and scripts/suites/ instead of .veldo/, so
`ast.literal_eval` raised on every invocation and no falsifier could be driven at all. The driver
now resolves string-constant names from the registry and locates the module in .veldo, scripts
or scripts/suites. No production module changed.

## Falsifier results (driver repaired)

All ten cases exit 1 under mutation with every target row red and the source restored:
v174-attach-outside-current-scope, v174-attach-another-owners-project,
v174-offer-every-waiting-turn, v174-project-lines-first, v174-no-work-conversation-line-dropped,
v174-ignore-record-version, v174-drop-skills, v174-mutation-siblings-missing,
v174-signed-commands-bypass-mutant and v174-record-memory-only. For the last, AC1/restart-open is
red in the clean run too (AF_UNIX); the sandbox-usable target AC1/durable-store is red only under
the mutant.

## Still outstanding

- Host with AF_UNIX: AC1/restart-open and AC2/restart-turns, then the AC1 falsifier's restored
  green run, and suite 86_veldo_0127_agent_configuration (batch-2.md, "Exact host commands").
- The reviewer's full gate on this tree and the recorded approval (risk high).
- When VELDO-0153 lands too, the second of the two suites numbered 107 resolves a text conflict
  in scripts/suites/manifest.json and requires.json; main already carries duplicate numbers.
