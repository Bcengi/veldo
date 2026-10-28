# VELDO-0174 on main 59b119a1, 2026-10-28

Status: the ticket's own checks are green on the merged tree, including both production
restart rows, run on a host with AF_UNIX sockets and a user service manager. One item
remains: suite 86's `live/codex` row needs a fresh Codex live capture (below). This is
focused evidence, not a gate stamp, a review verdict or a landing decision. The full gate
was not run (the batch gate runs later).

Results, commands and log digests: results.json. Logs: logs/before-fix and logs/after-fix.
Every run used run_round.sh in this folder, inside the host gate lock:

```sh
flock /home/dmitry/.local/state/core-gates/.gate.lock sh proof/VELDO-0174/merged-main-2026-10-28/run_round.sh /tmp/v174-1028/round2
```

That script runs, in order and serially, each command recorded in logs/after-fix/*.cmd:
`python3 scripts/selftest.py --suite 107_veldo_0174_conversations`, the same for
105_veldo_0182_memory and 86_veldo_0127_agent_configuration, then for each of the ten cases
`python3 proof/VELDO-0174/run_falsifier.py CASE --log-dir LOGDIR/falsifiers` followed by a
restored suite 107 run.

## Merge (4ab7fb43)

Main 59b119a1 was merged with an ordinary merge commit. Conflicts:

- engine/.veldo/control_service.py and its .veldo copy (byte-identical on both sides and
  after): Service.__init__ keeps this ticket's `_conversations` beside main's VELDO-0161 and
  VELDO-0143 instance state. FactoryLoop.__init__ keeps this ticket's work-optional
  `repositories` map and conversation Line, and main's `configured` list and taken-on
  repository lines through `add_line`. With no work configuration there is no line to take
  roles from, so a taken-on repository gets no line, as main's `add_line` already decides.
- scripts/suites/manifest.json: main's suites 107_veldo_0153 to 112 kept; the
  107_veldo_0174_conversations entry appended after them.
- scripts/suites/requires.json regenerated with `python3 scripts/run_scope.py --emit-requires`;
  specs/index.md with `python3 scripts/update_index.py`. scripts/check_generated.sh, template
  sync and `.veldo/validate.py all` pass.

## Failure found and fixed (b1f2d1d2)

On the merged tree suite 107 failed 23 rows in 4.5 s (logs/before-fix/s107.log): main's
FactoryLoop reads `service.repositories`, and the journey's SimpleNamespace service stand-in
in scripts/suites/support/v174_journey.py lacked it, so every journey row raised
AttributeError. The stand-in now carries `repositories={}`, as Service does for an
installation that took on no repository. No production module and no assertion changed. That
red run is the failing-first evidence; the same suite is 64 passed, 0 failed afterwards.

## Results after the fix

| Check | Result |
| --- | --- |
| Suite 107 | 64 passed, 0 failed, exit 2 (a healthy partial run). AC1/restart-open and AC2/restart-turns pass for the first time. |
| Suite 105 | 153 passed, 0 failed, exit 2. The batch-2.md memory backfill failure does not recur. |
| Suite 86 | 52 passed, 1 failed (`live/codex`: missing or stale live capture), exit 1. |
| Ten falsifiers | Each driver exit 0: mutated suite exit 1, every target row red, source restored. Each restored suite 107 run is 64 passed, 0 failed. |

The AC1 declared falsifier, v174-record-memory-only, now has its full demonstration: both
AC1/restart-open and AC1/durable-store red under the mutant, and both green restored.

## Remaining: suite 86 live/codex

proof/VELDO-0127/codex-live.json pins sha256 digests of the production modules it ran on.
This ticket changed .veldo/control_launch.py and .veldo/control_agent_config_handoff.py, so
the pin is stale. It was already stale on the branch before this merge (c1bd8b35 retook only
the Claude capture); on main it is fresh. Clearing it needs a real Codex live capture on an
owner account (proof/VELDO-0127/live.py), which earlier rounds took with owner approval. It
was not taken here. No assertion was changed to hide it.
