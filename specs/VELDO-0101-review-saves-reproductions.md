---
schema: veldo.spec/v1
id: VELDO-0101
title: The Codex review saves a reproduction capsule per confirmed defect
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0020
work: W1
plan_revision: 1
depends_on: []
placement: [engine]
protected_paths: []
footprint:
  - "engine/.veldo/capsule.py"
  - ".veldo/capsule.py"
  - "scripts/suites/*_veldo_0101_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0101-review-saves-reproductions.md"
  - "specs/index.md"
  - "proof/VELDO-0101/*"
behavior_bearing: true
observability:
  logs: >
    Each capsule names the review, the finding, the reviewed commit, the files saved and their digests.
  metrics: >
    Count findings with a capsule, findings without one, and capsules that fail to run against the
    reviewed commit.
  traces: >
    Join a capsule to the review markdown finding it came from and to every later run of it.
  error_taxonomy: >
    Distinguish missing capsule, capsule that does not reproduce on the reviewed commit, capsule with
    an unpinned command, and capsule whose bytes changed after saving.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The review brief tells Codex to save, for every confirmed defect, the script, fixtures,
      command and observed output as files under a capsule directory named by the finding, before it
      writes the finding text. Set: The generated prompt of codex_review.sh and a review run with a
      fake Codex that follows the brief. Completeness: The prompt names the directory, the required
      files and the rule that a finding without a capsule is reported as unconfirmed. Falsifier:
      Remove the capsule instruction from the brief; capsule/brief-requires-capsule must fail.
    falsified_by: >
      Remove the capsule instruction from the brief; capsule/brief-requires-capsule must fail.
  - id: AC2
    text: >
      Claim: A capsule is a directory with manifest.json (finding id, reviewed commit, command,
      expected observation), the reviewer's files byte for byte, and a digest of each file; the
      loader refuses a capsule whose digests do not match its bytes. Set: Load a saved capsule,
      change one byte of the script, load again. Completeness: Every file in the directory is
      digested; an extra undigested file refuses. Falsifier: Skip the digest comparison in the
      loader; capsule/tampered-bytes-refused must fail.
    falsified_by: >
      Skip the digest comparison in the loader; capsule/tampered-bytes-refused must fail.
  - id: AC3
    text: >
      Claim: The reviewer's sequence is never rewritten. The runner executes the saved command in a
      fresh temporary copy of the reviewed commit and compares the observation; an adapter may set the
      working directory and environment, never edit the saved files. Set: A capsule whose script
      prints evidence rather than asserting. Completeness: The saved script's digest before and after
      the run is identical; the observation compare is a separate function. Falsifier: Let the runner
      rewrite the script to an assertion before running it; capsule/reviewer-bytes-preserved must fail.
    falsified_by: >
      Let the runner rewrite the script to an assertion before running it;
      capsule/reviewer-bytes-preserved must fail.
required_evidence: [unit, integration]
rollback: >
  The brief change is one block of text; removing it returns the review to findings without capsules,
  and saved capsules remain readable.
---

## Intent

Make the reviewer's own reproduction the evidence that a fix is later checked against, instead of a rewrite by the author.

## Context

PLAN-0020, W1. Today Codex describes a reproduction in prose and the author translates it into a suite row; the translation is where the author's understanding replaces the reviewer's. Saving the files during the review costs no review allocation and gives the fix validation of W2 a fixed object to run.

## Out of scope

Running capsules against fixed candidates (W2), the assessor (W3), and enforcement in the proof check (W4).

## Notes

A capsule is a directory in the proof bundle of the item under review, so it lands with the item and is reviewed with it. No store outside the repository.
