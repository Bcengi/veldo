---
schema: veldo.spec/v1
id: VELDO-0123
title: Run both mutation drivers in every gate within a fixed time budget
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0105, VELDO-0107, VELDO-0108, VELDO-0109]
placement: [enforcement]
protected_paths: ["scripts/verify.sh"]
footprint:
  - "scripts/verify.sh"
  - "scripts/check_gate_mutations.py"
  - "scripts/check_teeth_mutations.py"
  - "scripts/check_review_mutations.py"
  - "scripts/suites/*_veldo_0123_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0123-mutation-drivers-in-every-gate.md"
  - "specs/index.md"
  - "proof/VELDO-0123/*"
behavior_bearing: true
observability:
  logs: >
    Record gate-stage invocation, driver and mutation identities, baseline results, named red rows, elapsed times and timeout cleanup.
  metrics: >
    Report registered/executed/rejected mutations, per-driver and combined wall time and any surviving workers.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish mutation_survived, missing_target, invalid_baseline, driver_error, incomplete_inventory and mutation_budget_exceeded.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every canonical repository gate runs both full mutation drivers as a required stage and propagates either driver's failure.
      Set: Every scripts/verify.sh invocation, with both drivers succeeding, either failing, absent or disabled; no finding selector or scheduled-only substitute.
      Completeness: Drive the gate in an isolated fixture with controlled driver outcomes and verify both actual invocations plus the gate exit. Stage receipts require both script identities and full-inventory digests; deleting either invocation cannot leave green. This is repository-specific wiring, not a dependency imposed on installed adopter gates.
      Refutation: gate/both-mutation-drivers-are-required is false if any green gate lacks either complete driver result.
    falsified_by: >
      Remove the check_review_mutations.py invocation from the required stage; gate/both-mutation-drivers-are-required must turn red.
  - id: AC2
    text: >
      Claim: Mutation success means the exact named assertion turns false in a completed run while the corresponding baseline is green.
      Set: All cases returned by check_teeth_mutations.py's case registry and check_review_mutations.py's CASES, including added cases, missing targets, moved anchors, worker crashes and mutations whose targets stay green.
      Completeness: Read both registries to derive the expected case and target inventory, verify each mutation diff landed exactly once, require each target exactly once as false and all baseline rows retained. Require no-op copies to preserve baseline observations; exceptions, absent rows and exit failures are driver errors, never detected mutants.
      Refutation: gate/mutation-results-have-teeth is false if a surviving mutant or invalid drive is accepted.
    falsified_by: >
      Treat a mutated worker's nonzero exit as successful mutation detection; gate/mutation-results-have-teeth must turn red.
  - id: AC3
    text: >
      Claim: The combined mutation stage finishes or fails within 600 seconds of monotonic wall time and reaps its workers within a further 5 seconds.
      Set: Both full drivers together, including a hung worker and slow suite-per-mutation runs; each baseline/mutant worker has at most 120 seconds within the shared remaining budget.
      Completeness: The stage owns one non-resetting deadline, counts setup, all suite processes and teardown, and reports per-driver/mutation elapsed time on the qualification host. Timeout kills the owned process group, records mutation_budget_exceeded and reddens the gate; no subset run or silent scheduling deferral may meet the budget.
      Refutation: gate/mutation-stage-budget-is-enforced is false if the stage reports success after deadline or leaves a child alive after the cleanup allowance.
    falsified_by: >
      Reset the combined deadline before each mutation; gate/mutation-stage-budget-is-enforced must turn red under the deterministic slow-worker schedule.
  - id: AC4
    text: >
      Claim: Removing an assertion's substance is caught by the canonical gate even when the ordinary unmutated suite stays green.
      Set: One controlled assertion-weakening edit per driver's target registry, made in disposable trees, plus an unchanged baseline and a no-op copy.
      Completeness: Generate edits from the registered target rows, replace each target condition with true while preserving row identity, and require the baseline gate green and every weakened tree red through a surviving named mutant. Each fixture invokes the real stage without recursively running this meta-qualification inside its own workers.
      Refutation: gate/removed-teeth-redden-the-gate is false if any assertion weakened to true still passes the gate.
    falsified_by: >
      Ignore the mutation stage's nonzero status when computing the gate result; gate/removed-teeth-redden-the-gate must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Make the already-written negative controls part of the gate's evidence, so later removal of a check's teeth is detected automatically.

## Context

proof/teeth-20260922/README.md:66-73 and proof/fixes-20260922/README.md:41-46 document standalone drivers; scripts/verify.sh at 2d19756 invokes neither. The request identifies this gate-wiring gap independently of the NOT YET DEMONSTRATED prose.

## Out of scope

New domain-specific mutants, changes to adopter engine gates, a scheduled-only lane, reducing the registered mutation set for speed and claiming a timing measurement before implementation.

## Notes

Choose every gate, not a scheduled lane. The 600-second combined stage cap plus 5-second cleanup allowance is an acceptance budget to demonstrate on the repository's supported qualification host; record Python/OS/CPU and case counts so the cost is reviewable. It is not a cap on the entire gate. Baseline sharing within one invocation is permitted only for byte-identical suite/input/implementation identities while preserving per-case target observations. Fixtures may use virtual time for timeout controls, but qualification also records a real full run. Keep repository-only driver wiring in the configured repository check stage; do not copy these project-specific drivers into engine/templates.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
