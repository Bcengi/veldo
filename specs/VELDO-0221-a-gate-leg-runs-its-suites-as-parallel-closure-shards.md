---
schema: veldo.spec/v1
id: VELDO-0221
title: A gate leg runs its suites as parallel closure shards, checked against the ordered run
status: draft
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0208, VELDO-0214, VELDO-0216]
placement: [enforcement]
protected_paths: ["scripts/selftest.py", "scripts/run_scope.py", "scripts/suites/shared.py", "scripts/check_first_use.py", "scripts/gate_legs.py", "engine/scripts/gate_legs.py"]
footprint:
  - scripts/selftest.py
  - scripts/run_scope.py
  - scripts/suites/shared.py
  - scripts/check_first_use.py
  - scripts/gate_legs.py
  - engine/scripts/gate_legs.py
  - scripts/check_teeth_mutations.py
  - scripts/suites/*_veldo_0221_*.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0221-a-gate-leg-runs-its-suites-as-parallel-closure-shards.md
  - specs/index.md
  - proof/VELDO-0221/*
behavior_bearing: true
observability:
  logs: Each shard prints its target suite, its closure, its pass and fail counts and its wall time; the leg prints its shard count, its parallelism and, in a force-fresh gate, the result of the ordered comparison.
  metrics: Per suite shard seconds and CPU seconds; leg wall time, which VELDO-0214 records as before.
  traces: Each shard's result names the suite, the closure from scripts/suites/requires.json and the leg; the aggregate line is composed from target-suite counts only.
  error_taxonomy: A shard that exits without a verdict, asserts nothing for its target or exceeds its deadline is a failure of its suite; a closure that leaves a name undefined fails its shard (never a skip); an ordered and sharded disagreement is order_dependence, RED, naming the suite.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: in a gate leg, selftest.py runs every suite of the leg as one shard, a fresh
      interpreter that executes the suite's prerequisite closure from scripts/suites/requires.json
      in manifest order in one namespace and then the suite, with the leg's row ownership applied
      exactly as today, and runs shards in parallel up to the allowance the authority's leg runner
      hands it (a caller's value is dropped, as for the leg variables). Set: the full manifest in
      both legs, a leg with one failing suite, a shard that dies without a verdict and a shard whose
      target asserts nothing. Completeness: every suite of the leg is a target exactly once, by
      construction from the manifest the dispatcher already enumerates; row
      suite-shards/coverage requires the target set equal to the leg's suite set and each failure
      to fail the leg.
    falsified_by: >
      Skip a shard whose process exits without a verdict. Registered mutant shards221-lost-shard
      must fail suite-shards/coverage.
  - id: AC2
    text: >
      Claim: sharding proves at least what the ordered run proves for each suite. The aggregate
      line counts each target suite's own rows once; any failing row in a shard, closure suites'
      rows included, fails the leg; a closure that omits a needed prerequisite fails the shard
      instead of passing. In every force-fresh gate each leg also runs the ordered single
      namespace run as today, and the two must agree per suite on the set of row labels and every
      row's value; a disagreement is RED as order_dependence naming the suite. Set: a fixture
      manifest with a hidden prerequisite missing from requires.json, one suite that pollutes a
      later suite's state, and a clean manifest. Completeness: row suite-shards/ordered-agreement
      drives all three through both modes and requires the hidden prerequisite to fail its shard
      and the pollution to be reported as order_dependence.
    falsified_by: >
      Compare only the pass counts of the two modes, not the labels. Registered mutant
      shards221-counts-only must fail suite-shards/ordered-agreement.
  - id: AC3
    text: >
      Claim: shards keep the host resources their suites declare. A suite that declares the
      systemd user manager exclusive (63_veldo_0040_containment, 66_veldo_0047_authority) runs
      while no other shard of its leg uses the manager, and shared users stay within the manifest's
      capacity; the leg as a whole keeps VELDO-0216's hold. Set: a fixture leg with two exclusive
      and three shared manager suites at a parallelism of 8. Completeness: row
      suite-shards/manager-exclusive records each shard's start and end and requires no overlap of
      an exclusive shard with any manager user.
    falsified_by: >
      Ignore the manifest's resource declarations in the shard scheduler. Registered mutant
      shards221-resources-ignored must fail suite-shards/manager-exclusive.
  - id: AC4
    text: >
      Claim: on the qualification host each confined leg of unit and integration finishes in at
      most 600 seconds and each unconfined leg in at most 420, against the measured 1,913, 1,795,
      892 and 834 seconds. Set: one canonical gate at the landing candidate with the allowance
      VELDO-0216 hands each leg. Completeness: the proof records every shard's wall and CPU time and
      each leg's critical shard.
    falsified_by: >
      Run shards one at a time (an allowance of 1). The confined unit leg takes about 2,000 seconds
      and the 600-second check fails.
required_evidence: [unit, integration]
rollback: Revert the shard mode; every leg runs the ordered single namespace run, as before.
---

## Intent

The unit and integration stages are the largest cost before mutation: their four legs took 5,434 of
the 5,502 pre-mutation seconds on 2026-10-25, each on about one core (0.75 to 1.00), because
selftest.py executes every suite in one interpreter, one after another. Running the legs beside
each other (VELDO-0216) still leaves the confined unit leg at 1,913 seconds, which alone is more
than the 30 minutes the owner wants for a typical landing. The suites themselves are mostly
independent: of the 167 suites in the pending stack's scripts/suites/requires.json, 156 need no
other suite, and the remaining 11 (fragments 01 to 13 of the original monolith) need between 2 and
12 earlier fragments. The mutation stage already runs each suite on its own in a fresh worker, and
the isolated baseline times there are at most about 100 seconds per suite.

## Design

selftest.py keeps its ordered mode for a bare run, a selector and the force-fresh comparison. In a
gate leg it adds the shard mode: it builds one job per suite of the leg from the manifest and
requires.json, starts each job as a child interpreter of the same dispatcher with the suite
selector (which already runs exactly the closure in manifest order and refuses to print an
aggregate line), and collects each child's per-suite counts and row labels from a structured
result file in the leg's scratch directory rather than from text. The parent composes the leg's
aggregate line from target-suite counts. All children inherit the leg's domain: a confined leg's
shards are confined by the same Landlock and seccomp domain, an unconfined leg's run as today.

Parallelism comes from the authority. gate_legs.py hands each leg its allowance in a leg variable
it alone sets, from VELDO-0216's scheduler; with no allowance the dispatcher runs one shard at a
time, which is the ordered run's cost and never faster than it. Exclusive manager suites run alone
among the leg's manager users, in manifest order.

What changes for the evidence, stated for the owner's decision. The ordered run also showed whether
one suite leaves state that changes a later suite's result. Shards do not show that in a landing
gate; they show each suite's result on clean state, which is what each assertion is about, and they
fail a suite that silently depended on an undeclared earlier suite (the ordered run hid that). The
ordered run is kept in every force-fresh gate (release and the owner's full runs), and AC2 turns
any disagreement red there. A landing therefore runs every assertion of every suite fresh, and the
cross-suite pollution check runs at the next force-fresh gate rather than at that landing.

Expected time. CPU per confined leg rises by the replayed closures (61 extra suite executions, all
among fragments 01 to 13) and one interpreter start per suite, from about 1,900 to about 2,500 CPU
seconds; at an allowance of 8 to 12 cores that is about 210 to 320 seconds, with the longest shard
(about 100 seconds confined, about 240 seconds for suite 101's traced rows in the unconfined leg)
as the floor. A force-fresh gate pays the ordered legs as well, about 5,000 extra CPU seconds, in
parallel with everything else.

## Out of scope

Suite result reuse (VELDO-0206), which this makes possible by isolating suites; the suites and their
assertions; the unconfined list; the mutation stage.

## What the reviewer judges

Normal use: the canonical and landing gates, and a force-fresh gate. Threat model: as in
VELDO-0208; the dispatcher and run_scope.py stay protected, so a candidate cannot change how
shards are counted. Out of review scope: pollution between suites that appears only in an ordered
run and is introduced between two force-fresh gates; it is caught at the next one.

## Notes

The integration stage's nested run uses the same dispatcher, so its legs shard the same way; its
budget input from VELDO-0214 becomes the 1800-second floor because the measured unit leg time falls
far below 900 seconds.
