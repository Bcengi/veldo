---
schema: veldo.spec/v1
id: VELDO-0123
title: Run every registered mutation fresh in every gate
status: ready
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
    Record gate-stage invocation, driver and mutation identities, input digests, fresh execution counts, baseline results, named red rows, elapsed times and timeout cleanup.
  metrics: >
    Report registered/executed/rejected mutations, per-driver and combined wall time and any surviving workers.
  traces: >
    Bind every result to the input identity, implementation digest and fixture version.
  error_taxonomy: >
    Distinguish mutation_survived, missing_target, invalid_baseline, driver_error, incomplete_inventory and mutation_budget_exceeded.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every canonical repository gate runs every registered case fresh in both mutation drivers and propagates either driver's failure.
      Set: Every scripts/verify.sh invocation, both drivers succeeding, either failing, absent or disabled; no finding selector or scheduled-only substitute.
      Completeness: Enumerate both current registries on every gate and require exact equality between registered case identities and validated results, each executed fresh in this run. Stage receipts require both script identities, full-inventory digests and per-case execution observations; missing drivers, missing cases or disabling the required stage cannot leave green. Drive these states in isolated fixtures and verify the stage receipt and gate exit. This is repository-specific wiring, not a dependency imposed on installed adopter gates.
      Refutation: gate/both-mutation-drivers-are-required is false if any green gate lacks either complete driver result.
    falsified_by: >
      Omit check_review_mutations.py's registry from the required stage; gate/both-mutation-drivers-are-required must turn red.
  - id: AC2
    text: >
      Claim: Mutation success means the exact named assertion turns false in a completed run while the corresponding baseline is green.
      Set: All cases returned by check_teeth_mutations.py's case registry and check_review_mutations.py's CASES, including added cases, missing targets, moved anchors, worker crashes and mutations whose targets stay green.
      Completeness: Read both registries to derive the expected case and target inventory, verify each mutation diff landed exactly once, require each target exactly once as false and all baseline rows retained. Require no-op copies to preserve baseline observations; exceptions, absent rows and exit failures are driver errors, never detected mutants. Validate complete baseline/mutant observations and mutation identity, not just a success bit or exit code.
      Refutation: gate/mutation-results-have-teeth is false if a surviving mutant or invalid drive is accepted.
    falsified_by: >
      Treat a mutated worker's nonzero exit as successful mutation detection; gate/mutation-results-have-teeth must turn red.
  - id: AC3
    text: >
      Claim: The combined mutation stage finishes or fails within its cap of monotonic wall time, the larger of 120 seconds and 2 seconds per registered case, and reaps its workers within a further 5 seconds.
      Set: Both full inventories together, including consecutive fresh runs, a hung worker and slow suite-per-mutation runs; each baseline/mutant worker has at most 120 seconds within the shared remaining budget.
      Completeness: The stage owns one non-resetting deadline, counts snapshotting, setup, all suite processes and teardown, and reports per-driver/mutation elapsed time on the qualification host. Demonstrate a successful real fresh run covering every registered case within 120 seconds. Timeout kills the owned process group, records mutation_budget_exceeded and reddens the gate; no subset run or silent scheduling deferral may meet the budget.
      Refutation: gate/mutation-stage-budget-is-enforced is false if the stage reports success after deadline or leaves a child alive after the cleanup allowance.
    falsified_by: >
      Reset the combined deadline before each mutation; gate/mutation-stage-budget-is-enforced must turn red under the deterministic slow-worker schedule.
  - id: AC4
    text: >
      Claim: Removing an assertion's substance is caught by the canonical gate even when the ordinary unmutated suite stays green.
      Set: One controlled assertion-weakening edit per driver's target registry, made in disposable trees, plus an unchanged baseline and a no-op copy.
      Completeness: Generate edits from the registered target rows, replace each target condition with true while preserving row identity, and require the baseline gate green and every weakened tree red through a surviving named mutant. Every fixture executes the full inventories fresh. Each fixture invokes the real stage without recursively running this meta-qualification inside its own workers.
      Refutation: gate/removed-teeth-redden-the-gate is false if any assertion weakened to true still passes the gate.
    falsified_by: >
      Ignore the mutation stage's nonzero status when computing the gate result; gate/removed-teeth-redden-the-gate must turn red.
required_evidence: [unit, integration]
rollback: >
  Revert this capability and its consumer wiring together; retain the evidence gap as open rather than reporting coverage from the earlier weaker rows.
---

## Intent

Make the already-written negative controls part of every gate's evidence, executing every registered case of both drivers fresh on every canonical gate so later removal of a check's teeth is detected automatically.

## Context

proof/teeth-20260922/README.md:66-73 and proof/fixes-20260922/README.md:41-46 document standalone drivers; scripts/verify.sh at 2d19756 invokes neither. The request identifies this gate-wiring gap independently of the NOT YET DEMONSTRATED prose.

## Out of scope

New domain-specific mutants, changes to adopter engine gates, a scheduled-only lane, reducing the registered mutation set for speed and claiming a timing measurement before implementation.

## Notes

The measured cold mutation-stage time on this machine was 13.8 seconds (13.777 seconds before rounding), covering 38 cases. The hard combined cap is 120 seconds, about 8.7 times that measurement: ample headroom for machine load and inventory growth while bounding a hung stage. Cleanup has a further 5-second allowance. This is not a cap on the entire gate. Report Python/OS/CPU and case counts with each qualification measurement.

Baseline sharing within one invocation is permitted for identical suite/module inputs while preserving per-case target observations. Workers use an isolated snapshot, disable bytecode, and leave the checked tree unchanged. Fixtures may use virtual time for deadline controls; qualification must also time a real full execution. Keep the coordinator and result validation Python standard library only. Keep repository-only driver wiring in the configured repository check stage; do not copy these project-specific drivers into engine/templates.

For each declared falsifier, retain the applied diff, require the named row to become false in an otherwise completed run, and revert the mutation. Drive a second mutation per row and an unmutated control. A crash, missing row or timeout is an invalid drive, not a detected falsifier.

## History

2026-09-22: Fixed the required stage's hard-coded .veldo module base and single-file materialization, which failed closed on fixture-kind registry entries. The teeth driver now owns source selection, whole-directory fixture copies and actual mutated-file digests for both drivers and the gate. Suite 53 qualifies a disposable fixture-kind registry with a named red target, an unmutated control and two driven regressions, including removal of fixtures from the frozen snapshot.

2026-09-22: Reuse was specified on an unmeasured cost estimate. The cold stage was then measured at 13.8 seconds on this machine. Reuse was removed on the owner's approval: Telegram 28800, "Yes", answering 28798, "can I take the reuse part out?" Status remains ready.

2026-09-23: The combined cap now scales with the registered inventory: the larger of 120 seconds and
2 seconds per registered case, recorded in the stage receipt as budget_seconds. Measured on this
machine: 38 cases took 13.8 seconds on 2026-09-22 and 116 cases took 91.8 seconds on 2026-09-23, about
0.36 then 0.79 seconds per case (the per-case cost is rising as suites grow, so the 2 second figure is
about 2.5 times today's rate and must be revisited if it approaches 1.5), so a fixed 120 second cap would turn the gate red for inventory growth alone as
Release 1 adds cases. The per-worker bound of 120 seconds is unchanged. Row
gate/mutation-budget-scales-with-inventory drives the real run_stage and checks the recorded cap, the
enforced worker deadline and the armed alarm; three mutations (fixed cap, deadline ignoring the scaled
cap, alarm not re-armed) each turn it red.
2026-09-23, input closure: the snapshot the mutation workers run in held only .veldo, engine/.veldo,
scripts and proof, so a suite row reading anything else (the front door bin/veldo, a spec, a plan)
failed in every baseline there and passed in the checkout. VELDO-0052's production-entries row did
exactly that and made the gate red with invalid_baseline for all of its cases. read_inputs now
returns the working tree Git does not ignore, tracked and untracked, minus deleted files, bytecode
caches and the gate outputs. Row gate/input-closure-is-the-working-tree drives it over a real
repository; mutations (directory list restored, untracked additions dropped, ignored files kept)
each turn it red.
Its review found three reading defects, fixed the same day: names are read as raw bytes and decoded
with the file system encoding, so a name with leading whitespace is no longer trimmed away and a
name that is not UTF-8 no longer stops the stage; and the closure is stated honestly as the
repository's own ignore rules with no global configuration, so ignored machine-local files (such as
.veldo/trackers.json) are not inputs. Rows now also drive modes, bytecode caches and the refusal of
a symbolic link (gate/input-closure-refuses-symlinks).
Its second review found, fixed the same day: a symbolic link as a DIRECTORY above a tracked file,
hidden by an ignore rule, let the snapshot copy a file from outside the checkout (now refused by
comparing each file's resolved path with its place in the tree); an untracked nested repository's
files silently dropped out (now refused by name); an unreadable file stopped the stage with a
generic error (now refused by name); the docstring now names every ignore source Git applies; and
the closure row no longer leaks its temporary repository. Row gate/snapshot-holds-exactly-the-closure
drives snapshot() itself: names, modes and contents in the worker tree equal the closure.
Its third review (no blockers) led to five follow-ups the same day: a directory Git cannot list,
about which ls-files only warns while listing less, and a directory whose entries cannot be
examined are refused by name (gate/input-closure-refuses-incomplete-listings); the closure read
through a symbolic link to the root is driven (a macOS temporary path is one); the identity the
race check compares is driven for content, mode and name (gate/race-check-sees-content-mode-and-name);
and the snapshot row cleans up even when a read raises.
Follow-ups from the closure's final review, 2026-09-23: the race check is one function,
inputs_unchanged, which the stage calls after the workers have run; row
gate/race-check-rereads-the-tree drives it over a real repository (changed file, mode, added file,
new commit) and drives the real run_stage end to end: a clean fixture passes and a worker writing into
the checkout mid-stage is refused as inputs changed during stage. Git output while listing that is not a listing
warning is refused as unexpected git output rather than mislabeled an incomplete listing, and an
unreadable info/exclude is refused (gate/input-listing-output-is-named).
2026-09-23, parallelism: the stage ran a fixed 8 workers, leaving most of a 20-core host idle while
Release 1 items grew the inventory; it now runs as many workers as the CPUs it may use, clamped to
2..16 and bounded by a cgroup CPU quota (gate/workers-follow-the-host, driven in a pinned child and through
Workers.run). Verdicts do not depend on the count; the combined budget, measured at 8 workers, now scales
inversely with the workers the stage runs, so a small host is not cut off early.
