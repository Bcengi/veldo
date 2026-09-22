---
schema: veldo.spec/v1
id: VELDO-0123
title: Require every mutation result in every gate with content-addressed reuse
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
    Record gate-stage invocation, driver and mutation identities, input digests, computed/reused provenance, baseline results, named red rows, elapsed times and timeout cleanup.
  metrics: >
    Report registered/computed/reused/rejected mutations, cache misses and key failures, per-driver and combined wall time and any surviving workers.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish mutation_survived, missing_target, invalid_baseline, driver_error, incomplete_inventory and mutation_budget_exceeded.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every canonical repository gate requires a valid result for every registered case in both mutation drivers and propagates either driver's failure.
      Set: Every scripts/verify.sh invocation, with cold, warm and mixed records, both drivers succeeding, either failing, absent or disabled; no finding selector or scheduled-only substitute.
      Completeness: Enumerate both current registries on every gate and require exact equality between registered case identities and validated results, each computed in this run or reused under AC5. Stage receipts require both script identities, full-inventory digests and per-case provenance; missing drivers, missing cases or disabling the required stage cannot leave green. Drive these states in isolated fixtures and verify the stage receipt and gate exit. This is repository-specific wiring, not a dependency imposed on installed adopter gates.
      Refutation: gate/both-mutation-drivers-are-required is false if any green gate lacks either complete driver result.
    falsified_by: >
      Omit check_review_mutations.py's registry from the required stage; gate/both-mutation-drivers-are-required must turn red.
  - id: AC2
    text: >
      Claim: Mutation success means the exact named assertion turns false in a completed run while the corresponding baseline is green.
      Set: All cases returned by check_teeth_mutations.py's case registry and check_review_mutations.py's CASES, including added cases, missing targets, moved anchors, worker crashes and mutations whose targets stay green.
      Completeness: Read both registries to derive the expected case and target inventory, verify each mutation diff landed exactly once, require each target exactly once as false and all baseline rows retained. Require no-op copies to preserve baseline observations; exceptions, absent rows and exit failures are driver errors, never detected mutants. A reusable record must contain these complete baseline/mutant observations and mutation identity, not just a success bit or exit code; validate them under the current result schema before accepting reuse.
      Refutation: gate/mutation-results-have-teeth is false if a surviving mutant or invalid drive is accepted.
    falsified_by: >
      Treat a mutated worker's nonzero exit as successful mutation detection; gate/mutation-results-have-teeth must turn red.
  - id: AC3
    text: >
      Claim: The combined mutation stage finishes or fails within 600 seconds of monotonic wall time and reaps its workers within a further 5 seconds.
      Set: Both full inventories together, including a cold run with no reusable results, warm and mixed runs, a hung worker and slow suite-per-mutation runs; each baseline/mutant worker has at most 120 seconds within the shared remaining budget.
      Completeness: The stage owns one non-resetting deadline, counts hashing, lookups, setup, all suite processes and teardown, and reports per-driver/mutation elapsed time on the qualification host. Demonstrate a successful real cold run covering every registered case within 600 seconds, without prepopulating records. Timeout kills the owned process group, records mutation_budget_exceeded and reddens the gate; no subset run or silent scheduling deferral may meet the budget.
      Refutation: gate/mutation-stage-budget-is-enforced is false if the stage reports success after deadline or leaves a child alive after the cleanup allowance.
    falsified_by: >
      Reset the combined deadline before each mutation; gate/mutation-stage-budget-is-enforced must turn red under the deterministic slow-worker schedule.
  - id: AC4
    text: >
      Claim: Removing an assertion's substance is caught by the canonical gate even when the ordinary unmutated suite stays green.
      Set: One controlled assertion-weakening edit per driver's target registry, made in disposable trees, plus an unchanged baseline and a no-op copy.
      Completeness: Generate edits from the registered target rows, replace each target condition with true while preserving row identity, and require the baseline gate green and every weakened tree red through a surviving named mutant. Prewarm records before each edit and require invalidation and recomputation of affected cases. Each fixture invokes the real stage without recursively running this meta-qualification inside its own workers.
      Refutation: gate/removed-teeth-redden-the-gate is false if any assertion weakened to true still passes the gate.
    falsified_by: >
      Ignore the mutation stage's nonzero status when computing the gate result; gate/removed-teeth-redden-the-gate must turn red.
  - id: AC5
    text: >
      Claim: Reuse is permitted only from a complete content-addressed record produced by a successful local drive for exactly the current outcome-affecting inputs.
      Set: Every registered case and all its inputs, including the driver bytes, canonical case definition (mutation, anchors and target rows), suite file, scripts/suites/shared.py, the whole .veldo/ tree the suite can import, and full interpreter implementation/version identity.
      Completeness: Digest actual working-tree bytes and paths, including additions, deletions and untracked importable files, not commit IDs, mtimes or a hand-selected list of production modules. Include transitive support/fixture code, read data and configuration, result-schema/stage logic, interpreter executable/runtime identity and any outcome-affecting external tool, host capability or environment input; otherwise fix that input in the isolated execution environment or disable reuse. Prefer coarse tree digests to incomplete dependency inference. Keep records only in this checkout's private Git administrative directory, resolved by git rev-parse --absolute-git-dir, under mutation-results/, never in the committed tree or a shared worktree cache. Only completed validated local drives publish atomic records; never import committed receipts. A missing, corrupt, partial or mismatched record runs the case. A key that cannot be computed runs the case without reading or publishing a reusable record. Inputs must remain identical from key computation through result acceptance, using an immutable input snapshot or verified stability; a race cannot publish or accept a stale result.
      Refutation: gate/mutation-reuse-is-input-complete is false if any changed input reuses a stale result or a committed artifact supplies a result.
    falsified_by: >
      Independently omit each input component from the key, one mutant per component; gate/mutation-reuse-is-input-complete must turn red for every omission under the corresponding single-input change.
  - id: AC6
    text: >
      Claim: Incremental reuse saves worker execution without weakening full-inventory coverage or invalidation.
      Set: A cold stage, unchanged warm stage, documentation-only edit, one added case, missing/corrupt records and key-computation failures, plus independently changed driver, case definition, suite file, shared.py, each importable .veldo/ file and interpreter version; extend this matrix to every additional keyed input.
      Completeness: Seed valid local records, change exactly one input per drive and record old/new keys, computed/reused case identities and worker invocations. Every affected case must recompute with no stale reuse, even for byte changes preserving size/mtime; exercise tree additions/deletions and transitive imports too. Drive interpreter-version changes through a controlled identity provider and qualify with two real supported interpreter versions. The unchanged and README-only warm runs must reuse every case and launch zero baseline/mutant workers. A new case, unusable record or uncomputable key must execute the affected case; denial of cache writes must still allow fresh results. Plant a plausible committed receipt with the external cache empty and require recomputation. Report exact inventory coverage and cold/warm wall times for all drives.
      Refutation: gate/mutation-reuse-invalidates-per-input is false if any single-input change reuses a stale result, any required case goes missing, or a warm documentation-only edit reruns all workers.
    falsified_by: >
      Reuse the previous result after an input digest changes; gate/mutation-reuse-invalidates-per-input must turn red separately for each input in the generated matrix.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Make the already-written negative controls part of every gate's evidence, recomputing only cases without a valid result for the current inputs so later removal of a check's teeth is detected automatically.

## Context

proof/teeth-20260922/README.md:66-73 and proof/fixes-20260922/README.md:41-46 document standalone drivers; scripts/verify.sh at 2d19756 invokes neither. The request identifies this gate-wiring gap independently of the NOT YET DEMONSTRATED prose.

## Out of scope

New domain-specific mutants, changes to adopter engine gates, a scheduled-only lane, reducing the registered mutation set for speed and claiming a timing measurement before implementation.

## Notes

Every gate requires every case's result, not fresh execution of every case. For a documentation-only change after a successful run on unchanged execution inputs, the expected additional mutation-stage cost is hashing the input trees and validating/reading records (seconds, to be measured), with zero baseline/mutant workers. It should leave today's roughly eleven-minute gate close to that cost rather than add another full mutation run. A new checkout or unavailable cache pays the cold cost. Documentation outside the actual input set does not enter the key; any documentation a suite reads does. Generated gate receipts are outputs, not reusable mutation results: workers must not read them as inputs if they are excluded from keys, and their routine rewrites must not invalidate otherwise unchanged cases.

The 600-second combined stage cap plus 5-second cleanup allowance applies even to a cold run with no reusable results and is an acceptance budget to demonstrate on the repository's supported qualification host; record Python/OS/CPU and case counts so the cost is reviewable. It is not a cap on the entire gate. Baseline sharing within one invocation is permitted only for byte-identical suite/input/implementation identities while preserving per-case target observations. Fixtures may use virtual time for timeout controls, but qualification also records real cold and warm runs. Keep the coordinator, key construction and result validation Python standard library only. Keep repository-only driver wiring in the configured repository check stage; do not copy these project-specific drivers into engine/templates.

This is planned work, not implementation evidence. All named rows below this contract are obligations for a future ready implementation. For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. A crash, missing row or timeout is an invalid drive, not a detected falsifier.
