---
schema: veldo.spec/v1
id: WARP-0714
title: The suite parses 86 source files 4,460 times, walks 21 million AST nodes and opens 112,451 files to
  read 9,096 - compute each derivation ONCE, with every optimized value asserted equal to the naive one
status: ready
risk: high - this changes the body of the GATE, and the failure mode is the worst available here: a suite that
  runs faster because it proves LESS, while still printing green. Memoizing a parse, indexing a tree, caching a
  read or hoisting a render each LOOK safe and each can silently change what an assertion observes. Two
  specific ways it could manufacture a false green: a cached read serving pre-mutation bytes to a mutation
  test, and a memoized tree served to an assertion that expected a freshly parsed one. Both are closed by
  proof rather than by care - every optimized value is asserted EQUAL to the naive value, and the read cache
  carries its own invalidation proof. No protected path, no runner, no engine module, no change to what any
  assertion means
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [WARP-1210, WARP-0712]
placement: [engine]
footprint:
  - scripts/selftest.py
  - proof/WARP-0714/measured.md
  - specs/WARP-0714-compute-once.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The suite reports its own elapsed time and the counts it collapsed (parses, tree walks, file opens), so
    the saving is visible as a number rather than asserted in prose, and a future regression in any of the
    three is attributable to a count rather than to a stopwatch.
  error_taxonomy: No new failure names, and no existing failure renamed. Every assertion that fails today for
    a reason fails with the same label and the same message.
acceptance_criteria:
  - id: AC1
    text: >
      EACH DERIVATION IS COMPUTED ONCE, and the four offenders are named with the counts that were measured
      rather than described. (a) PARSING: 4,460 ast.parse calls serve only 86 DISTINCT source texts, one of them
      parsed 120 times, so the source-text-to-tree mapping is memoized and the parse count drops to the number
      of distinct sources. (b) TREE WALKING: 21.4M iter_child_nodes and 10.8M ast.walk calls come from
      assertions re-walking trees already walked, so nodes are indexed once per tree and assertions query the
      index. (c) FILE READS: 112,451 opens serve 9,096 distinct paths, with individual runner modules and
      guardrail fixtures opened about 200 times each, so reads of repository-tracked files are cached by path
      within the run. (d) THE REPEATED RENDER at scripts/selftest.py:16977, where render_text sits INSIDE a
      generator expression iterating over its own output lines and re-renders the whole dashboard per line, is
      hoisted to a single value. proof/WARP-0714/measured.md records each count with the command that produced
      it.
  - id: AC2
    text: >
      NOTHING PROVES LESS, PROVEN BY EQUALITY RATHER THAN BY INSPECTION. For every assertion whose computation
      is memoized, indexed, cached or hoisted, the optimized value is asserted EQUAL to the naive value computed
      the old way, so an optimization that changes an outcome FAILS the gate rather than passing it faster. And
      the assertion LABEL SET is captured before and after and asserted BYTE-IDENTICAL AS A SET, which is
      strictly stronger than the count holding, because a count survives one deletion paired with one addition.
      No assertion may be skipped, weakened, marked expected-failure or moved behind a conditional: each is
      asserted absent.
  - id: AC3
    text: >
      THE READ CACHE CANNOT SERVE A STALE BYTE, which is the one way this item could manufacture a false green
      and therefore gets its own criterion. The suite WRITES files and then asserts over them, and several teeth
      mutate a module in memory or on disk and require the assertion to observe the mutation. So the cache is
      asserted to be invalidated by any write the suite itself performs, and a selftest proves the specific
      hostile case: mutate a cached file, re-read it through the cache, and assert the MUTATED bytes come back.
      A tooth that passes against pre-mutation content is a tooth that has been deleted, so this is proven in
      both directions - the mutation is seen, and the unmutated file still reads unchanged.
  - id: AC4
    text: >
      IT IS FASTER AND THE FIGURE IS THE REAL ONE. The suite's elapsed time and the three collapsed counts are
      recorded beside the baseline; if the saving is smaller than the counts suggest, the real figure is what
      the manifest states and the shortfall is named. THE DELIBERATE COSTS STAY, asserted so that this item
      cannot buy time from them: the WARP-0710 claim-race detector still runs 16 threads times 400 rounds times
      3 trials against real filesystem locks (its volume IS its detection power), and the durability tests still
      call real fsync. scripts/verify.sh is byte-UNCHANGED and so is the stage list, proven by sha256, no
      protected path is touched, no engine module changes, the frozen safety core is byte-UNCHANGED, the full
      gate is GREEN, and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change memoizes source parsing, indexes AST nodes once per tree, caches reads of
  tracked files with an invalidation rule, and hoists one repeated render, all inside scripts/selftest.py.
  Nothing outside the suite is touched, so a revert is invisible to every caller and simply restores the
  redundant work. It is a cost regression rather than a return to a good state, and no record, event, contract
  or engine file changes, so there is no migration.
---

## Intent

Measured on the gate: 117.1 seconds total, of which the selftest is 102.4. Of that, 84.2 seconds is BLOCKING
and is handled by two sibling items. This item takes the REAL COMPUTE, and the striking thing about it is how
much of it is the same work done again.

4,460 calls to `ast.parse` serve 86 DISTINCT source texts. One source is parsed 120 times. 112,451 file opens
serve 9,096 distinct paths, with individual runner modules and guardrail fixtures opened about 200 times each.
21.4 million calls to `iter_child_nodes` walk trees that were already walked. And at
`scripts/selftest.py:16977` the dashboard render sits inside a generator expression over its own output lines,
so it re-renders per line.

None of that repetition proves anything the first pass did not. This is not a design cost being traded away,
it is the same answer being recomputed, and the counts came from instrumenting the run rather than from
reading the code.

## Context

- Why this is its own item, per the smaller-tickets decision: the sibling work is the mobile-runner clock
  (WARP-0713), the lint stage (WARP-0711) and the contested process-runner fixture windows (WARP-0715). This
  one touches ONLY scripts/selftest.py, so it is reviewable on its own and lands on its own.
- Why it must come BEFORE the suite decomposition (WARP-0712) and AFTER WARP-1210: doing it before the split
  means the split moves already-cheap code rather than re-doing this work across N files; doing it after 1210
  avoids a conflict in the same 16k-line file, which is the collision that has serialized this whole
  programme.
- Why AC3 exists separately from AC2: the read cache is the ONE optimization here that can create a false
  green rather than merely a wrong number, because the suite's teeth depend on observing mutations. A general
  equality proof does not cover it; the hostile case has to be written.
- Why the deliberate costs are asserted in AC4: an item with a speed target has every incentive to cut the
  19,200-operation race detector and the real fsyncs, and those are BOUGHT coverage, not waste.

## Out of scope

- The blocking time (84.2s of sleep and poll). WARP-0713 and WARP-0715 own that.
- The lint stage. WARP-0711 owns it.
- Decomposing the suite into per-module files. WARP-0712 owns that, and depends on this.
- Any change to what an assertion means, to any engine module, or to any runner.
- Any reduction of the WARP-0710 race detector's volume or of any real fsync.
- No protected path, no change to verify.sh or the stage list.

## Notes

- Write the equality assertions FIRST, then optimize. Written afterwards they will be written to match
  whatever the new code happens to do, which is the failure this project has paid for repeatedly.
- The hostile cache case is the one to write before anything else: mutate, re-read, assert the mutation is
  seen. If that is not provable, the cache does not ship.
- Report the collapsed counts, not just the seconds. Seconds are machine-specific; a parse count of 86 against
  4,460 is not.
- NO UNBACKED UNIVERSAL: "nothing proves less", "every optimized value" and "the deliberate costs stay" each
  need the assertion that enumerates them. And MEASURE FIRST, then write the sentence from the output.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
