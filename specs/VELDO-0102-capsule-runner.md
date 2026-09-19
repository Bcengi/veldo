---
schema: veldo.spec/v1
id: VELDO-0102
title: Capsule runner - reproductions and pinned rows against the reviewed and the fixed candidate
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0020
work: W2
plan_revision: 1
depends_on: [VELDO-0101]
placement: [engine]
protected_paths: []
footprint:
  - "engine/.veldo/fix_validation.py"
  - ".veldo/fix_validation.py"
  - "scripts/suites/*_veldo_0102_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0102-capsule-runner.md"
  - "specs/index.md"
  - "proof/VELDO-0102/*"
behavior_bearing: true
observability:
  logs: >
    Each run names the finding, the commit it ran against, the command, exit status, duration and the
    observation compared.
  metrics: >
    Count findings reproduced on the reviewed commit, closed on the fixed commit, pinned rows driven,
    mutants that failed to apply, and runs that hit the deadline.
  traces: >
    Join every run to its capsule, its commit and the validation record it feeds.
  error_taxonomy: >
    Distinguish still-reproduces, does-not-reproduce-on-reviewed-commit, mutant-invalid, deadline,
    and child-processes-left-running.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: For each finding the runner produces four results: the capsule reproduces the defect on
      the reviewed commit, the same capsule passes on the fixed commit, the pinned row reds with its
      declared mutant applied to a copy of the fixed commit, and the pinned row is green on a fresh
      copy. Set: A review with two findings, one fixed and one not. Completeness: All four results are
      recorded per finding; a missing result is recorded as missing, never as passed. Falsifier: Skip
      the run on the reviewed commit and report the finding closed; fixval/four-results-required
      must fail.
    falsified_by: >
      Skip the run on the reviewed commit and report the finding closed;
      fixval/four-results-required must fail.
  - id: AC2
    text: >
      Claim: Every run is one subprocess in its own temporary copy of the commit, with a deadline;
      on the deadline the runner kills the process group and records deadline, and the author's
      worktree is never the run directory. Set: A capsule that sleeps past the deadline and spawns a
      child. Completeness: No process from the run survives; the worktree is unchanged by digest.
      Falsifier: Run the capsule inside the worktree; fixval/never-in-the-worktree must fail.
    falsified_by: >
      Run the capsule inside the worktree; fixval/never-in-the-worktree must fail.
  - id: AC3
    text: >
      Claim: A declared mutant that does not apply to the fixed commit exactly once is recorded as
      INVALID_MUTATION and the finding is not closed; the runner never searches for a new anchor.
      Set: A fixed commit that renamed the mutated function. Completeness: Zero and two matches both
      refuse; the record names the file and the anchor. Falsifier: Treat a mutant with zero matches
      as covered; fixval/invalid-mutation-not-covered must fail.
    falsified_by: >
      Treat a mutant with zero matches as covered; fixval/invalid-mutation-not-covered must fail.
required_evidence: [unit, integration]
rollback: >
  The runner writes only into the proof bundle's validation directory; deleting that directory
  returns the bundle to its pre-validation state.
---

## Intent

Run the reviewer's reproduction and the author's pinned row against the fixed candidate, in a disposable copy, and record what happened, including when nothing could run.

## Context

PLAN-0020, W2. The author's pinned row proves the author's understanding; the capsule proves the reviewer's. Both must hold on the fixed commit, and the mutant must still apply, or the finding is not closed.

## Out of scope

Reading the diff for new defects (W3) and refusing the bundle (W4).

## Notes

Deadline default is twice the capsule's duration on the reviewed commit, minimum 60 seconds.
