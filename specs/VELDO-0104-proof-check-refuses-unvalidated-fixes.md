---
schema: veldo.spec/v1
id: VELDO-0104
title: validation.json in the proof bundle, the two-round cap, and the proof check refusing unvalidated fixes
status: shipped
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0020
work: W4
plan_revision: 3
depends_on: [VELDO-0102, VELDO-0103]
placement: [engine]
protected_paths: []
footprint:
  - "engine/.veldo/validate.py"
  - ".veldo/validate.py"
  - "engine/.veldo/fix_validation.py"
  - ".veldo/fix_validation.py"
  - "engine/.veldo/fix_validation_record.py"
  - ".veldo/fix_validation_record.py"
  - "engine/.veldo/validate_checks.py"
  - ".veldo/validate_checks.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0104_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0104-proof-check-refuses-unvalidated-fixes.md"
  - "specs/index.md"
  - "proof/VELDO-0104/*"
behavior_bearing: true
observability:
  logs: >
    The proof check names, for a refused bundle, the fix commit, the finding and which of the four
    results or the verdict is missing or negative; a parked item names its round count.
  metrics: >
    Count bundles refused for missing validation, findings not closed, items parked, and rounds used.
  traces: >
    Join validation.json to the runner records, the assessment record, the fix commits and the review.
  error_taxonomy: >
    Distinguish no-validation-record, finding-not-closed, assessor-not-closed, round-cap-exceeded,
    and validation-record-does-not-name-this-commit.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A proof bundle whose item has a fix commit after its review carries validation.json
      naming that fix commit, and per finding the four runner results and the assessor verdict; the
      proof check refuses a bundle with a fix commit and no validation.json, or with any finding whose
      results or verdict are missing or negative. Set: Bundles with no record, a complete record, one
      finding not_closed, and a record naming a different commit. Completeness: The check is in
      validate.py proof and in validate.py all. Falsifier: Accept a bundle whose validation.json
      names a different commit than the landing's fix commit; proofcheck/record-binds-commit must
      fail.
    falsified_by: >
      Accept a bundle whose validation.json names a different commit than the landing's fix commit;
      proofcheck/record-binds-commit must fail.
  - id: AC2
    text: >
      Claim: Rounds are counted in validation.json as fix commits after the review; a third round is
      refused and the item is marked parked with the open findings listed, and nothing in the item
      can change to shipped while parked. Set: Two rounds with an open finding, then a third fix
      commit. Completeness: The count is derived from the commits, not from a field the author edits.
      Falsifier: Reset the round count when the finding is renamed; proofcheck/round-cap-survives-
      rename must fail.
    falsified_by: >
      Reset the round count when the finding is renamed; proofcheck/round-cap-survives-rename must
      fail.
  - id: AC3
    text: >
      Claim: The validation requirement is one owner flag in .veldo/policy; off, the proof check
      reports validation absent as a warning and never refuses; on, it refuses; the flag's state is
      printed in every proof check result. Set: Both flag states over the same bundles.
      Completeness: The flag lives in a protected path. Falsifier: Refuse with the flag off;
      proofcheck/flag-off-is-a-warning must fail.
    falsified_by: >
      Refuse with the flag off; proofcheck/flag-off-is-a-warning must fail.
required_evidence: [unit, integration]
rollback: >
  Turn the owner flag off; bundles, capsules and records stay in place and are read as warnings.
---

## Intent

Make the rule bind: a fix that nobody but its author has checked cannot be part of a landed proof, and a fix loop stops after two rounds.

## Context

PLAN-0020, W4. This is the switch. W1 to W3 produce evidence; this item makes the existing proof check demand it and refuses without it. The queue item of 2026-09-18 ("proof validator must refuse unverified fixes") is this spec.

## Out of scope

Landing services, hooks, signed receipts and separate identities (PLAN-0020 NG1).

## Notes

validation.json is written by fix_validation.py from the runner and assessor records; the author never edits it by hand, and the check recomputes the round count from Git.
