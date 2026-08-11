# Split plan - the gate-cost work, applying Dmitry's 2026-07-25 "yes to smaller tickets"

The original WARP-0711 had EIGHT acceptance criteria, which is the WARP-1210 shape (about 8 ACs, 9 rounds,
~26h, and one rule change breaking ten assertions). Authored the same day I diagnosed over-size as the
disease. Superseded by four items, each ONE concern with 3-4 ACs, each independently landable.

The shared baseline artifact is `proof/WARP-0711/baseline.md` (per-stage wall clock, the in-selftest profile,
the instrumented redundancy counts). The three later items CITE it rather than re-measuring.

**Order matters only where noted. The four are otherwise footprint-disjoint enough to run in separate lanes,
which is the point of splitting this way.**

---

## WARP-0711 - lint: one interpreter instead of 662 (WRITTEN, ready)

`scripts/check_lint.sh` + 7 copies, plus its selftest block. Measured 14.07s to 0.82s. Fully measured, trivially
reviewable, zero contested judgement. Lands first and alone.

Spec: `WARP-0711-lint-one-interpreter.md`.

## WARP-0713 - the mobile runners take an injected clock

`engine/scripts/runners/mobile/veldo_android_runner.py` (12 sleep sites) and `veldo_ios_runner.py` (9),
7 copies each, plus selftest. Recovers about 46s of the 84.2s of blocking, PROTOTYPE-MEASURED at zero assertion
impact.

The three ACs that matter: (1) the seam defaults to the real `time.sleep` and `time.monotonic` so shipped
behaviour is byte-identical, asserted by constructing each runner with no arguments and checking the resolved
waiter IS `time.sleep`; (2) every settle constant keeps its NUMERIC VALUE, asserted, because the seam is what
changes and not the values; (3) the injected clock RECORDS what was asked of it, so the requested durations and
their ORDER become assertable for the first time - launch requests its settle window, tap one second, type half
a second, redrive terminate-then-launch in that order. That third one is why this is a coverage item and not
only a speed item: today those waits are unobservable and the gate learns nothing from them.

Follows the house pattern already at `.veldo/fleet.py:377` (`clock=time.time, sleep=time.sleep`) and
`.veldo/tracker_mirror_runner.py:172`.

## WARP-0714 - compute each derivation once

`scripts/selftest.py` only. Four named offenders, each with its measured count:
- 4,460 `ast.parse` calls serving only 86 DISTINCT source texts, one parsed 120 times - memoize source-to-tree
- 21.4M `iter_child_nodes` and 10.8M `ast.walk` calls - index nodes once per tree, assertions query the index
- 112,451 file opens over 9,096 distinct paths, individual runner and fixture files opened about 200 times each
  - cache reads of tracked files, WITH an invalidation proof, because the suite writes files and then asserts
  over them and a stale read would make a mutation test pass against pre-mutation bytes
- `scripts/selftest.py:16977` calls `DB10.render_text(_M10_EVENTS)` INSIDE a generator expression over its own
  output lines, re-rendering the whole dashboard per line - hoist it

The governing AC for all four: the optimized value is asserted EQUAL to the naive value, so an optimization that
changes an outcome fails the gate rather than passing it faster.

CONFLICTS WITH WARP-1210 and with WARP-0712 on `scripts/selftest.py`. Sequence after 1210 lands; sequence BEFORE
0712 so the split moves already-cheap code.

## WARP-0715 - the process runner's fixture windows (CONTESTED, do last)

`engine/scripts/runners/process/fixtures/pass.lifecycle.json` and `fail.lifecycle.json` + 7 copies.

Why it is separate and last: a GLOBAL virtual clock breaks EXACTLY SEVEN process-runner assertions, measured,
because that runner spawns REAL subprocesses and asserts real signal delivery, force-kill and orphan reaping.
Those are operating-system properties, so faking the subprocess is REFUSED - it would delete the only coverage
those seven give. `POLL = 0.05` is the only SHIPPED constant in the module and does NOT move.

What may move is fixture parameters, which are test inputs: `grace_seconds` 3.0, `kill_tree_window_seconds` 4.0,
`spawn_settle_seconds` 0.3. Any reduction carries a RELIABILITY PROOF, not an argument: the process-runner block
run at least 50 consecutive times at the proposed values with zero flaky results. If 50 runs are not clean, the
value goes back UP and the wall-clock target moves instead. An intermittently red gate is worse than a slow one.

## What the whole set is worth, stated honestly

Committed: the gate under 20 seconds from 117.1. The under-12 stretch depends entirely on WARP-0715's flakiness
proof holding, which is unproven. The original spec's 12-second bar was an estimate that a prototype refuted:
it assumed all 84.2s of blocking was recoverable, and seven assertions say otherwise.
