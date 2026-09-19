---
schema: veldo.plan/v1
id: PLAN-0020
title: Fix validation - every fix to a review finding is checked by someone other than its author, and the loop terminates
kind: iteration
status: ready
revision: 2
owner: dmitry
approved_by: dmitry
approved_at: 2026-09-19
risk: high

outcomes:
  - id: O1
    becomes_true: >
      A fix to a review finding does not count as done until the reviewer's own reproduction has been
      run against the fixed candidate, the pinned row and its mutant have been driven, and a fresh model
      on a different harness has read the fix diff and answered per finding.
    measure: >
      The proof bundle of every landing with a fix commit carries validation.json naming, per finding,
      the reproduction run, the driven row, and the assessor's verdict; the proof check refuses a bundle
      with a fix commit and no validation.json, or with any finding lacking one of the three.
  - id: O2
    becomes_true: >
      Validation terminates. After two fix rounds an item parks with one blocking reason; nobody starts a
      third round without the owner reshaping the item.
    measure: >
      The round counter lives in the proof bundle and in the control store; a third fix commit against
      the same review is refused by the proof check; a parked item's shipped state is unchanged.

non_goals:
  - id: NG1
    text: No second OS identity, trusted landing service, server-side hook, or HMAC receipt. Trust rests on the process and on the record of who ran what. Named future work, not this plan.
  - id: NG2
    text: No second Codex review of repaired candidates. Codex reviews the initial candidate once and saves reproductions; repairs are assessed by the fresh model.
  - id: NG3
    text: The repository gate and suite fragments are unchanged. The Validator adds a check; it does not rewrite scripts/verify.sh.

constraints:
  - id: C1
    text: Standard library only (json, sqlite3, hashlib, subprocess, ast). The assessor is a separate headless run of the logged-in Claude Code subscription (claude -p, clean context, read-only tools, the frozen candidate as its only input); never a paid API, never the author's own session, never a second Codex review.
  - id: C2
    text: Reproductions are preserved byte for byte; a wrapper may arrange directories and assert, never replace the sequence that exposed the defect. Each capsule runs in its own process and temporary workspace with a deadline and child cleanup.
  - id: C3
    text: Budget per review - two fix rounds, one assessor run per round, 60,000 tokens per run. Counters are written before the run starts and survive restarts.
  - id: C4
    text: ASCII hyphen only; US spelling; no client names in the public repository.

feature_tree:
  - id: F1
    title: Codex saves a reproduction capsule per confirmed defect
    outcome_refs: [O1]
  - id: F2
    title: The validation script - reproductions, driven rows, assessor, validation.json
    outcome_refs: [O1, O2]
  - id: F3
    title: The proof check enforces validation and the round cap
    outcome_refs: [O1, O2]

work:
  - item: W1
    spec: VELDO-0101
    title: Codex review contract saves a reproduction capsule per confirmed defect
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: VELDO-0102
    title: Capsule runner - reproduction against reviewed and fixed candidates, pinned row and mutant, one process per capsule
    feature_refs: [F2]
    depends_on: [VELDO-0101]
    order: 20
  - item: W3
    spec: VELDO-0103
    title: Assessor as a fresh headless Claude Code run - fix diff plus findings in, per-finding verdict out, provenance recorded
    feature_refs: [F2]
    depends_on: []
    order: 30
  - item: W4
    spec: VELDO-0104
    title: validation.json in the proof bundle, round cap, and the proof check refusing unvalidated fixes
    feature_refs: [F2, F3]
    depends_on: [VELDO-0102, VELDO-0103]
    order: 40

regression:
  journeys:
    - id: RJ1
      title: A fix that passes the reproduction by special-casing it is marked not closed by the assessor and the bundle is refused
      activation: {when: after:VELDO-0104}
      owner_spec: VELDO-0104
      profiles: [per_spec, release]
      suite: scripts/suites (VELDO-0104 rows)
    - id: RJ2
      title: A third fix commit against the same review is refused and the item shows as parked
      activation: {when: after:VELDO-0104}
      owner_spec: VELDO-0104
      profiles: [per_spec, release]
      suite: scripts/suites (VELDO-0104 rows)

release:
  milestone: Fix validation v1 - no fix lands unvalidated, no review loops past two rounds
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: The proof check's validation requirement is a flag the owner alone flips off; capsules and validation records are append-only.
  observation:
    duration: The first three landings after activation, including the batch validation of the fix commits landed since the quota ruling.

open_decisions:
  - id: D1
    text: Whether the fresh headless Claude Code run is enough separation from the author session for the assessor, or whether the assessor waits for Codex quota on the 22nd for the first batch only. Owner decides before VELDO-0103 starts.
    blocks: [VELDO-0103]
---

## Intent

**Purpose.** Landings today rest on one Codex review of the first candidate and on the author's own gate for everything after it. The fixes to the review findings get no second reader, and nothing stops a review-fix-review loop from running forever. This plan closes both with the smallest thing that closes them: Codex saves its reproductions as it reviews; one script runs them against the fixed candidate, drives the pinned rows and their mutants, and asks a fresh model on a different harness whether each finding is closed and whether the diff opened anything next to it; the answer goes into the proof bundle; the proof check refuses a bundle without it; two rounds, then park.

**Trust.** The script runs under the owner's own account. It could in principle be forged by the author; the record names who ran it, when, against which commit, with which model. The heavier boundary (separate identity, landing service, signed receipt) is deliberately not in this plan.

## Ordered delivery rationale

The Codex contract (W1) ships first so the next review already saves capsules. The runner (W2) and the assessor call (W3) are independent and can be built in parallel. The proof check (W4) needs both and is the switch that makes the rule bind.
