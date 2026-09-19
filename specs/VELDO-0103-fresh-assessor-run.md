---
schema: veldo.spec/v1
id: VELDO-0103
title: Assessor - a fresh headless Claude Code run reads the whole fix diff and answers per finding
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0020
work: W3
plan_revision: 2
depends_on: []
placement: [engine]
protected_paths: []
footprint:
  - "engine/.veldo/fix_assessor.py"
  - ".veldo/fix_assessor.py"
  - "scripts/suites/*_veldo_0103_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0103-fresh-assessor-run.md"
  - "specs/index.md"
  - "proof/VELDO-0103/*"
behavior_bearing: true
observability:
  logs: >
    Each assessment names the reviewed commit, the fixed commit, the findings given, the harness and
    model reported by the run, the token count, and the verdict per finding.
  metrics: >
    Count verdicts closed, not closed, and new-defect, and runs refused for a missing provenance line.
  traces: >
    Join the assessment to the diff digest it read and to the validation record it feeds.
  error_taxonomy: >
    Distinguish harness-not-available, verdict-unparseable, finding-missing-from-verdict, and
    provenance-missing.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The assessor is started as a separate headless process of the logged-in Claude Code
      subscription with a clean context, read-only tools, and a brief that contains the findings, the
      capsule results and the complete diff from the reviewed commit to the fixed commit; it never
      receives the author's conclusions or the author's session. Set: A fake harness command that
      records what it was given. Completeness: The brief contains every finding id and the full diff
      digest; the process environment carries no API key variable. Falsifier: Pass the author's
      "closed" summary into the brief; assessor/no-author-conclusions must fail.
    falsified_by: >
      Pass the author's "closed" summary into the brief; assessor/no-author-conclusions must fail.
  - id: AC2
    text: >
      Claim: The verdict is parsed per finding into closed, not_closed or new_defect with a one-line
      reason, and a verdict missing any finding is recorded as not_closed for that finding. Set: A
      fake harness answering two of three findings. Completeness: Unparseable output is recorded as
      unparseable and closes nothing. Falsifier: Default a missing finding to closed;
      assessor/missing-verdict-is-not-closed must fail.
    falsified_by: >
      Default a missing finding to closed; assessor/missing-verdict-is-not-closed must fail.
  - id: AC3
    text: >
      Claim: The assessment record names the harness, the model the run reported, the wall time and
      the token count the harness reported; a run that reports none of these is recorded as
      provenance-missing and closes nothing. Set: Fake harness output with and without the
      provenance line. Completeness: The record fields are written by the runner from the process
      output, not copied from free text. Falsifier: Accept a verdict without provenance;
      assessor/provenance-required must fail.
    falsified_by: >
      Accept a verdict without provenance; assessor/provenance-required must fail.
required_evidence: [unit, integration]
rollback: >
  The assessor writes one record into the proof bundle's validation directory; removing it returns
  the bundle to the runner's results alone.
---

## Intent

Give every fix a second reader that is not its author: a fresh run with none of the author's context, reading the whole diff, answering per finding.

## Context

PLAN-0020, W3. Dmitry's rulings of 2026-09-18: no paid model APIs (subscriptions only), and the second reader is not the author's own session. A headless run of the same subscription with a clean context is that reader. Codex remains the one reviewer of the initial candidate and is not spent on fixes.

## Out of scope

Running reproductions (W2) and refusing the bundle (W4). No sandbox claim: read-only tools bound what the run can do, not what hostile code could do.

## Notes

The brief asks three questions per finding: does the fix restore the behavior rather than special-case the reproduction; does every changed hunk belong to a finding; did the change touch error handling, persistence, transactions, signatures or process coordination in a way that needs another look.
