---
schema: veldo.spec/v1
id: VELDO-0211
title: First use reruns suites selected by observed filesystem reads
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
placement: [enforcement]
protected_paths: [scripts/check_first_use.py, scripts/selftest.py, scripts/first_use_reads.py, scripts/case_trace.py, engine/scripts/case_trace.py, .veldo/policy.yaml]
footprint:
  - scripts/check_first_use.py
  - scripts/selftest.py
  - scripts/first_use_reads.py
  - scripts/case_trace.py
  - engine/scripts/case_trace.py
  - scripts/suites/103_veldo_0211_first_use_reads.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - .veldo/policy.yaml
  - specs/index.md
  - proof/VELDO-0211/working-notes.md
acceptance_criteria:
  - id: AC1
    text: For every suite in the current gate leg, selection uses syscall observations from that gate's unit run, including Python and other children, metadata probes and parent directory listings. Only complete evidence bound to the same repository contents permits keeping a result; selected suites include their prerequisite closure.
    falsified_by: Discard child reads and observe the child reader fixture being kept.
  - id: AC2
    text: Every mutation family measures changed paths by comparing pristine and mutated filesystem inventories after its sanctioned writer runs, including additions, removals, metadata and symlink changes. Selection intersects observations with that measured set.
    falsified_by: Substitute a fixed event store path and observe an additional changed file being missed.
  - id: AC3
    text: Missing tracing, incomplete evidence, a nested gate, stale contents or an unreadable observation never permits skipping a suite. Global uncertainty uses the existing full nested run; individual uncertainty reruns that suite with its prerequisites.
    falsified_by: Treat an incomplete trace as empty and observe an uncertain suite being kept.
  - id: AC4
    text: Every assertion newly failing after first use is reported by name and makes the check fail. The baseline remains lazy, runs the same selection, and inability to determine a verdict exits nonzero. Each run prints selected suites with changed path reasons, kept suites, incomplete evidence reasons and wall time.
    falsified_by: Suppress the mutated failure and observe the recorded spend emptiness regression passing.
required_evidence: [unit]
rollback: Revert the selective check and observation integration together to restore full nested runs.
---

## Intent

Keep the first use regression property while avoiding a second execution of suites whose
observed inputs are disjoint from the sanctioned mutation. Unit results remain the authority
for kept suites. The historical measurement was about 1919 seconds across both integration
legs, not the obsolete ninety second estimate in the check's documentation.

## Context

The gate already observes filesystem syscalls for mutation workers. A gate run has a unique
reuse receipt path that can scope unit observations without accepting a prior gate's evidence.
The dispatcher executes fragments in one shared namespace and provides prerequisite closures.
Uncertainty about dependencies must preserve execution rather than authorize a skip.

## Out of scope

Changing the sanctioned writers, changing assertions to pass, distributing this repository
only check to installed packs, changing gate confinement, pushing or approving landing.

## What the reviewer judges

Normal use is a sequential unit stage followed by first use in each existing gate leg.
The threat model is accidental stale, missing or incomplete observations on the owner's host.
Deliberately forged observations by code already executing as that owner and resource exhaustion
are outside this change. Incorrect selection during normal execution remains in scope.

## Notes

The owner restricts this work to focused suites and reserves full gate verification and landing
approval for the reviewer. No gate byproducts belong in this change's commits.
