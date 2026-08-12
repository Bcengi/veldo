---
schema: veldo.spec/v1
id: WARP-0712
title: One 16,000-line test file that every item must edit is what serializes the whole programme - decompose
  it into per-module suites behind an unchanged entry point, so work can run in parallel lanes on disjoint
  files, a developer can run one suite in a second, and the fleet this repository already built becomes usable,
  while the FULL run stays the only thing that means green
status: shipped
risk: high - this restructures the body of the gate, and it is the highest-consequence refactor in the
  repository because the thing being restructured is the thing that proves everything else. A 16k-line script
  accumulated over 145 items almost certainly carries IMPLICIT SEQUENTIAL STATE (module-level fixtures built by
  one assertion block and read by a later one), so a naive split produces suites that pass in aggregate and
  fail alone, or worse, pass alone and silently stop checking what they checked in context. The failure mode is
  therefore not a crash, it is 3112 assertions becoming 3112 assertions that prove less, and it would be
  invisible. It is high and not critical because the entry point and verify.sh stay byte-UNCHANGED, no
  protected path is touched, and the load-bearing criterion is an assertion-label-set identity proof plus a
  per-suite standalone-and-aggregate equivalence proof rather than a reviewer's reading
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-07-26
approval_record: >
  RECORDED ON THE BOARD: VEL-9 (https://bcengi.atlassian.net/browse/VEL-9), transitioned to Approved BY DMITRY
  HIMSELF at 2026-07-25 21:17 EDT, on a ticket carrying the full RISK section. The agent created the ticket and
  moved it to Awaiting Approval but deliberately did NOT fire the Approve transition, although the MCP identity
  in use made it available and although he had already said yes in chat: an agent completing a human's approval
  would make the fence theatre. Recording an approval is the agent's job; performing one never is.
  His original wording, on Telegram at 2026-07-26 00:14 EDT: "Yes split it. Should have always be split, can't
  be locked to 1 file." Given after an evening of engagement with this exact tradeoff, including the measurement
  that one rule change broke ten assertions, so it is a considered decision rather than a rubber stamp. His
  added judgement is stronger than this spec's own framing: the suite should NEVER have been one file, so this
  item corrects an original design error rather than optimizing a reasonable choice.
lane: standalone
depends_on: [WARP-0711, WARP-0716]
placement: [engine]
footprint:
  - scripts/selftest.py
  - scripts/suites/
  - engine/scripts/selftest.py
  - engine/scripts/suites/
  - packs/*/scripts/selftest.py
  - packs/*/scripts/suites/
  - proof/WARP-0712/throughput-baseline.md
  - specs/WARP-0712-suite-decomposition.md
  - specs/index.md
protected_paths: []
behavior_bearing: true
observability:
  logs: The runner reports, per suite, its name, assertion count and elapsed time, so the next cost regression
    is attributable to a suite instead of to a 16k-line file. The aggregate line keeps its current exact
    format ("selftest: N passed, M failed") because the gate and the operator guide both read it.
  error_taxonomy: The names stay closed and gain two structural refusals: SUITE_NOT_ENUMERATED (a suite file
    exists on disk but is absent from the manifest, so it would silently not run) and SUITE_LABEL_COLLISION
    (two suites declare the same assertion label, which would let one silently mask the other in the identity
    proof). Both exist because the decomposition's own integrity is what needs guarding.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Replace the region partition scripts/suite_slice.py imports from WARP-0716 with one re-derived locally
      over topic names, and the assertion at scripts/suites/13_warp_0623_codified_live.py:7784, that the
      partition the slicer uses IS WARP-0716's imported object rather than a re-derivation, must go red.
    text: >
      THE CROSSING-STATE VERDICT FROM WARP-0716 IS CONSUMED, NOT RE-DERIVED, and this item does not begin until
      that verdict says feasible. WARP-0716 mechanically enumerates every module-level name bound in one region
      of scripts/selftest.py and read in another, classifies each, and returns a feasibility verdict that is
      allowed to say NOT FEASIBLE. If it says not feasible, THIS ITEM IS RE-SCOPED OR DROPPED rather than
      attempted, because the failure mode of splitting a tangled suite is silent: suites that pass alone having
      stopped checking what they checked in context. If it says feasible with named preparatory work, that work
      is done first. The suite boundary set used here is the one 0716 derived FROM THE READ PATTERN, not a set
      drawn around topic names, because a boundary drawn where data actually stops crossing produces suites
      independent by construction. The throughput evidence justifying the item at all is
      proof/WARP-0712/throughput-baseline.md, already measured: 139 of 145 items took 1-3 commits, the maximum
      elsewhere is 6, nothing sits between 6 and WARP-1210's 20, so rework is a lone outlier and the 1.19h mean
      is representative.
  - id: AC2
    falsified_by: >
      Reword the aggregate summary line in RunScope.aggregate_line (scripts/run_scope.py:339) from `selftest:
      %d passed, %d failed` to any other spelling, and the assertion pinning that line character-identical
      must go red; that line is the load-bearing leg because scripts/verify.sh, the operator guide and every
      run record parse it, and a full run would still be correct while every parser of it broke.
    text: >
      THE ENTRY POINT DOES NOT MOVE, WHICH IS WHAT KEEPS THIS OUT OF THE PROTECTED SET. `python3
      scripts/selftest.py` remains the invocation, produces the same aggregate summary line in the same format,
      and returns the same exit status semantics, so scripts/verify.sh is byte-UNCHANGED and is asserted so by
      sha256. selftest.py becomes a thin dispatcher over the manifest and holds no assertions of its own. A
      selftest asserts the dispatcher contains no assertion of its own and that its output format for the
      aggregate line is character-identical to the pre-change format, because the gate, the operator guide and
      the run records all parse that line.
  - id: AC3
    falsified_by: >
      Make the crossing detector in scripts/suite_slice.py stop reporting the silent shape, the name a later
      region fills that an earlier one reads through a defensive `or` fallback, and the assertion at
      scripts/suites/13_warp_0623_codified_live.py:7749 that the silent case is proven REACHABLE must go red;
      the silent shape is the load-bearing one, since the loud shape raises NameError and finds itself.
    text: >
      THE IMPLICIT SEQUENTIAL STATE IS FOUND AND MADE EXPLICIT RATHER THAN ASSUMED ABSENT, and this is the
      criterion the whole item lives or dies on. Before splitting, the module-level names that cross assertion
      blocks are ENUMERATED mechanically (by parsing the current file, not by reading it), and each is
      classified as a shared fixture, a per-suite local, or a genuine ordering dependency. Every shared fixture
      becomes an explicit, importable fixture with a declared owner; every genuine ordering dependency is either
      removed or DECLARED in the manifest with its reason so a reader can see the boundary. A selftest asserts
      the enumeration in the code matches the one the suites exercise, so a crossing name cannot be quietly
      dropped. The house lesson applies: when a change claims a class, list the members and cover each or
      declare it uncovered with the reason.
  - id: AC4
    falsified_by: >
      Reduce the comparison in scripts/suite_equiv.py to the aggregate passed and failed totals instead of the
      per-suite label results, and the assertion at scripts/suites/13_warp_0623_codified_live.py:7389, the
      dangerous case where a suite passes alone having stopped checking what it checked in context, must go
      red while the loud case keeps passing.
    text: >
      EVERY SUITE PASSES STANDALONE AND IN AGGREGATE, AND PROVES THE SAME THING BOTH WAYS. Each suite file runs
      alone, in a fresh interpreter, with no dependence on another suite having run first, and its assertion
      results are asserted IDENTICAL to its results within the full run. This is the specific defect a naive
      split produces (suites that pass in aggregate and fail alone, or pass alone while having stopped checking
      what they checked in context), and the equivalence is proven per suite rather than argued once. Suite
      ORDER independence is proven by running the manifest in a deliberately different order and asserting the
      same aggregate outcome, because a suite set whose result depends on its order has not actually been
      decomposed.
  - id: AC5
    falsified_by: >
      Change the identity proof in scripts/suite_labels.py from a comparison of label SETS to a comparison of
      label COUNTS, and the count-survives-it assertion at scripts/suites/13_warp_0623_codified_live.py:7342,
      one label deleted paired with one added, must go red; separately, deleting the ON_DISK against DECLARED
      comparison at scripts/selftest.py:73 must stop a suite file absent from the manifest being refused as
      SUITE_NOT_ENUMERATED.
    text: >
      NOT ONE ASSERTION IS LOST, proven by identity rather than by count. The complete set of assertion LABELS
      is captured before the decomposition and after it and asserted BYTE-IDENTICAL AS A SET, which is strictly
      stronger than 3112 holding, since a count survives one deletion paired with one addition. Two new
      structural refusals guard the decomposition itself: SUITE_NOT_ENUMERATED, so a suite file present on disk
      but missing from the manifest turns the gate RED instead of silently not running, and
      SUITE_LABEL_COLLISION, so two suites cannot declare the same label and mask each other inside the identity
      proof. TEETH AS A MATRIX: each guard is neutralized in memory one at a time and run against every fixture,
      the matrix asserted EXACTLY DIAGONAL with the off-diagonal asserted as an EMPTY LIST, every mutation
      target asserted to appear exactly once, and every touched module asserted sha256-unchanged after all runs.
  - id: AC6
    falsified_by: >
      Change one byte in engine/scripts/suites/shared.py so the engine copy diverges from
      scripts/suites/shared.py, and scripts/check_pack_drift.py must go red naming that path: engine canon is
      the leg with a mechanical check here, while the disjointness demonstration reddens instead by merging
      the fragments back into one manifest entry so the two worked-example footprints collide on a single file
      again.
    text: >
      THE PARALLELISM THIS EXISTS FOR IS DEMONSTRATED, not asserted as a benefit in prose. The suite files are
      partitioned so that the work items on the current frontier touch DISJOINT files, demonstrated concretely
      for at least two real queued items whose footprints collide today under scripts/selftest.py and do not
      collide after (WARP-0711 and the next PLAN-0013 item are the worked example, since 0711 is blocked on
      exactly this collision right now). The manifest, the fixtures and the dispatcher are asserted to be the
      only shared files, so two lanes editing different suites cannot conflict. Engine canon holds: the
      dispatcher, the manifest and the suites are re-synced byte-identical across engine and all six
      packs, the frozen safety core is byte-UNCHANGED, the full gate is GREEN, per-suite timings are printed,
      and RULE #1 is clean.
required_evidence: [unit]
rollback: >
  Revert the commit. The change replaces a single 16k-line assertion script with a thin dispatcher, a manifest,
  an explicit fixture module and a set of per-module suite files, all re-synced byte-identical across
  engine and the packs. Because the entry point, the aggregate output line and the exit semantics are
  unchanged, a revert is invisible to verify.sh and to every caller: it restores the monolith and with it the
  serialization, the absent subset runner and the 16k-line conflict surface. That is a throughput regression
  rather than a return to a good state, and it must not be done to unblock a lane, since the whole purpose is
  to stop lanes blocking each other. No record, event, contract or write path changes, so there is no
  migration.
---

## Intent

Dmitry, 2026-07-25: "It is worth creating a task to review timing everywhere and seeing where things can be
reduced. I would like to see if we can complete everything in 3-4 days, which mean at least 5x speedup from
current estimate."

I measured the timing from git history rather than estimating it, and the finding is that the estimate was the
thing most wrong. 145 items have been delivered in 173.0 hours, a MEAN OF 1.19 HOURS PER ITEM. The 45 remaining
items are therefore about 53 hours serial, not the 135 I quoted, because I had anchored on WARP-1210, the worst
item in the project's history, as if it were typical.

The second finding is that the average is healthy and the TAIL is not: the top 6 items consumed 86.9 hours, 50
percent of all elapsed time for 4 percent of the items. Half of that tail is real rework, identifiable by commit
count, and half is me idle between commits, which is not recoverable and is not counted as if it were.

The third finding is the one worth building against. THE PROGRAMME IS SERIALIZED BY A SINGLE FILE. Every item
must edit scripts/selftest.py, which is 16,000 lines, and that one fact causes three separate problems that
have each been treated as their own annoyance:

- there is no way to run a subset, so a one-line fix pays the entire suite, which is what turned WARP-1210's
  red-gate loop into roughly four hours
- the gate costs 117 seconds a lap, addressed separately by WARP-0711
- and WORK CANNOT RUN IN PARALLEL, because two lanes would fight over the same 16k-line file

That last one is the expensive one, and it is live right now: WARP-0711 cannot start until WARP-1210 lands,
purely because both touch this file. This repository BUILT A FLEET for parallel work. Band 07 is the claim
ledger, the claimable frontier, the serialized lander, worktree isolation, the fleet launcher and claim-race
hardening, all shipped and gate-proven. And work has been running one item at a time regardless, because the
test suite is a single file every lane would collide on. We built the road and then drove single file down it.

So the 5x is not people or agents working faster. It is stopping doing serially what was never dependent. That
is one decomposition, and it dissolves all three problems at once.

## Context

- Why this is riskier than it looks, and where the real engineering is: a 16k-line script grown over 145 items
  will carry module-level names that one assertion block creates and a later block consumes. Splitting without
  finding them yields suites that pass together and fail alone, which is annoying, or suites that pass alone
  having quietly stopped checking what they checked in context, which is dangerous and silent. AC3 makes the
  enumeration mechanical rather than a careful read, because a careful read of 16k lines is exactly the kind of
  assurance this repository has learned not to accept.
- Why the entry point must not move: scripts/verify.sh is a protected path at floor high, and the gate, the
  operator guide and every run record parse the aggregate summary line. Keeping `python3 scripts/selftest.py`
  and that line's exact format means this restructure touches nothing protected, which is the difference
  between an item that can be built now and an item that queues behind an approval.
- Why the subset runner must be structurally incapable of counting as a gate pass: the moment a one-second
  partial run exists, the incentive to treat it as verification exists. The method's central law is that green
  verify.sh is the only definition of done, and a fast path that could be mistaken for it would erode the law
  quietly. Labelling is not enough; AC6 requires it to be unable to write the stamp.
- Dependency on WARP-0711: that item hoists a repeated render, memoizes parsing and indexes the syntax trees
  inside the current single file. Doing it first means this decomposition moves already-cheap code, and doing it
  second would mean re-doing that work across N files. The ordering is deliberate and one way.
- What this unblocks concretely, and why it is worth its own risk: 53 hours serial over 4 lanes is about 13
  hours of wall clock. With this item and WARP-0711 as the enabling work, 3 to 4 days is reachable without
  anyone working faster and without any review being skipped.

## Out of scope

- No change to verify.sh, veldo-guard.sh, policy.yaml or policy_check.py. No protected path.
- No change to the stage list or to what the gate concludes. The gate still runs everything.
- No change to any assertion's meaning. This item MOVES assertions; it does not rewrite them, and the
  label-set identity proof is what holds it to that.
- No deletion of any assertion, and no assertion moved behind a conditional or marked expected-failure.
- No reduction of the deliberate stress costs (the WARP-0710 race detector's volume, the real fsyncs), which
  WARP-0711 already asserts intact.
- No parallel EXECUTION of suites inside one gate run. Running suites concurrently is a further win and a
  different risk (shared temp state, output interleaving), and it is a separate item once the suites are proven
  independent.
- No change to the fleet, the claim ledger or the lander. They already work; they have simply had nothing they
  could safely run in parallel.

## Notes

- Enumerate the crossing names by PARSING, not by reading. The whole point of AC3 is that a human read of 16k
  lines is not evidence.
- Prove each suite standalone AND in aggregate. A suite that only passes in company has not been decomposed,
  and a suite that only passes alone has probably stopped asserting something.
- Do not let the subset runner become the habit. It is for the inner loop of a fix; the gate is the gate.
- Distinguish waste from cost, as in WARP-0711. This item moves cost around; it must not shed any.
- The prose rule, in force: a sentence in the manifest that makes a checkable claim must be backed by an
  assertion, or must not be written.
- RULE #1 clean (ASCII hyphen only, no em dash, no en dash, no prose double-hyphen).
