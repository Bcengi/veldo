# VELDO-0125 b2 round 18

Starting revision: `0b9d7bfdbb2c424a928ec8fce56ed2047f717149`.
Implementation commit: `15787c7798ace8513279cd5a789a74aaef36d550`.
Scope: the owner's G1-G5 findings, not a full gate or landing claim.

## G1: Git boundary repaired

Both production and engine copies of `control_worker.py` now load `git_process`
and route clone and checkout through its `run` boundary. Both copies of
`project_runner_macos_os.py` route the pinned `/usr/bin/git` commit/tree checks
and clean-worktree status check through the same boundary. The Mac checks retain
the fixed environment, five-second timeout, captured text, and
`OSError('macos_tool_failed:git')` on unsuccessful commands. The worker retains
its clone/checkout timeouts and checked return codes.

`git-boundary-before.log` records all eight original violations (four per copy).
`git-boundary-after.log` records the passing checker. `template-sync.log` records
byte identity of both edited engine/production pairs. No checker patterns changed.

## G2: Exact send inventory declarations

The existing worker transport set in `86_veldo_0168_text.py` now also declares
`Client.release`, `Client.retired`, and `Client.status`, each with receiver `self`
and method `send`. Each sends one signed worker command, not Telegram text.
The existing equality checks still compare both engine and production inventories.
`0168.log` reports 26 suite assertions and 26 shared assertions, zero failures.

## G3: WARP-1404 audit investigation

`warp1404-1.log` and `warp1404-2.log` each report 38 suite assertions and 26 shared
assertions, zero failures. This includes AC5's import/pure/repo/CLI audit windows.

`audit-path-comparison.json` compares 17 audit, dependency and harness files to
`9763249e`; every file is byte-identical. This includes `toe_analogy`, `toe_corpus`,
`toe_normalize`, `estimate`, `metrics`, `validate`, `validate_checks`, `yamlish`,
`git_process`, the WARP suite and the confinement entry points. None of this
branch's changed production modules is imported by the audit path examined.
`branch-paths-vs-main.log` preserves the complete production/scripts path delta.
There is no branch-local audit-path writer, spawn or Git change identified to fix.

A separate attempt to use the real gate confinement launcher for ONLY this suite
was refused before tests started: the outer session has the enforced user namespace
label but the inherited sandbox marker is unavailable. The refusal is preserved in
`warp1404-confined-1.log`. No confinement policy was changed or bypassed. The two
successful runs are selected-suite runs in this session, not a reproduction of the
reviewer's canonical confined unit leg. That exact leg remains for the reviewer.

## G4: Live capture staleness identified; owner re-capture required

`proof/VELDO-0127/evidence.py:45-48` checks schema `veldo.role-live/v1`, engine name,
and equality of the capture's `production` dictionary with SHA-256 digests of five
current `.veldo` files: `control_agent_config.py`, `control_agent_config_handoff.py`,
`control_launch.py`, `control_engine_claude.py`, and `control_engine_codex.py`.
It does not key this message on a timestamp, HEAD, or the entire checkout.

For BOTH `claude-live.json` and `codex-live.json`, the schema and engine match and
exactly one digest is stale: **`.veldo/control_launch.py`**. That file differs from
the main baseline on this branch. The other four captured digests match current
production. `live-staleness.json` records the captured, current and main hashes.
Investigation stops at that identification as requested. No live capture was
edited, fabricated, or re-run; the owner must re-capture.

## G5: Static evidence collected; runtime attribution remains unresolved

The supplied figures (2546 registered, 1227 executed, 1216 rejected) are from the
owner's report. The original stage receipt and case-level failure lines are not in
this checkout. A search of proof JSON/log/text files found no matching aggregate.

In `scripts/check_gate_mutations.py`, `validate_result` requires passing baseline
and no-op controls and the intended failing mutant assertions (lines 276-298).
Only a validated result enters `receipt['results']` (844-851), and `rejected` counts
those completed identities (895-906). Thus **1216 rejected means successful mutant
rejections**, not 1216 errors. Counts alone cannot identify invalid baselines,
surviving mutants, worker failures, unfinished cases, or the stage failure reason.

There is no `main` ref here. The available main baseline is `9763249e`, explicitly
identified by seed merge `95a33d9b`; `main-reference.log` preserves that provenance.
No other branch or worktree was checked out or changed.

`mutation-registration-delta.json` contains the entire mutation-driver delta
against that baseline: three existing `control_store.py` mutation anchors were
updated (`owners37-different-owner-adds`, `owners37-bound-command-added`, and
`owners-may-name-generic-commands`). No registration was added. Static AST call
identity digests match; all three anchors match their respective main/current
production source exactly once. This is static analysis, not a runtime registry
or mutation result. `mutation-static-comparison.json` records these checks and
hash equality for the coordinator and the other inspected mutation support files.

`mutation-suite-changes.log` lists the added 103/104 (VELDO-0124) and 105/106
(VELDO-0125) suites and changed existing suites. The three mutation drivers do not
name 0124/0125 on either main or this branch (`mutation-attribution-notes.json`).
Existing registered cases can still exercise changed shared production code, so
an unchanged registry does NOT establish equal runtime results on main.

Case identities plus `error`, `detail`, `invalid_results` and worker outcomes from
the original receipt, with matching main-run evidence, are needed to finish G5.
They were requested from the owner. No mutation driver was imported or executed,
and no unsupported attribution or speculative fix was made.

## Selected regression results

| Command | Log | Result | Exit |
| --- | --- | --- | --- |
| `python3 scripts/check_git_boundary.py` (after repair) | `git-boundary-after.log` | pass | 0 |
| `python3 scripts/selftest.py --suite 86_veldo_0168_text` | `0168.log` | 52 passed, 0 failed | 2 |
| `python3 scripts/selftest.py --suite 15_warp_1404_historical_analogy` (first) | `warp1404-1.log` | 64 passed, 0 failed | 2 |
| `python3 scripts/selftest.py --suite 15_warp_1404_historical_analogy` (second) | `warp1404-2.log` | 64 passed, 0 failed | 2 |
| `python3 scripts/selftest.py --suite 105_veldo_0125_relay` | `0125-relay.log` | 43 passed, 0 failed | 2 |
| `python3 scripts/selftest.py --suite 106_veldo_0125_routing` | `0125-routing.log` | 250 passed, 0 failed | 2 |

Counts include shared assertions. `run-results.json` and `routing-run-result.json`
record the commands and actual exit statuses, including the failed confinement
launch. `diff-check-implementation.log` and `diff-check-final.log` are empty
successful `git diff --check` outputs. The first staged check warned about a
blank context line in the saved raw patch (`staged-diff-check.log`); the exact patch
is now encoded in JSON to preserve its bytes without introducing trailing
whitespace. `staged-diff-check-final.log` records a second warning solely because
the first warning log itself echoes that raw context line. Both diagnostic logs
are preserved verbatim, including that whitespace; production code has no
whitespace errors. These warnings do not represent test failures.

## Validation limits

Every selftest invocation selected one suite, serially. Exit 2 is the dispatcher's
mandatory partial-run status, including runs with zero failed assertions. These
logs do not constitute canonical verification, an evidence-manifest pass, or a
landing decision. No full selftest, mutation runner, full gate, merge or push ran.
Existing captures and prior run records were left untouched.
