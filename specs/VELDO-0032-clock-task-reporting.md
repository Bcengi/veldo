---
schema: veldo.spec/v1
id: VELDO-0032
title: Clock uncertainty in task reporting
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W17
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
placement: [fleet]
protected_paths: []
footprint:
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "scripts/suites/*_veldo_0032_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0032-clock-task-reporting.md"
  - "specs/index.md"
  - "proof/VELDO-0032/*"
behavior_bearing: true
observability:
  logs: >
    Task reports name unanswerable claims, holder, stored heartbeat, reader time, tolerance, and
    required operations reconciliation.
  metrics: >
    Report uncertain task count separately from ordinary claimed and open counts; unknown liveness
    contributes no available capacity.
  traces: >
    Bind each report row to task alias, canonical claim observation, source file, and authority
    watermark when enrolled.
  error_taxonomy: >
    Preserve distinct granted, concluded, capability-refused, claimed, and unanswerable reasons
    across machine and text reports.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: task_report and report_lines expose a distinct unanswerable result instead of
      bucketing clock disagreement as ordinary claimed work. Set: Real task files and installed
      claim records in a temporary Git common directory, with enrolled records served by the
      authority API. Completeness: Build fresh, expired, boundary-tolerance, and beyond-tolerance
      heartbeat records; compare every task row and count with claim.liveness. Corrupt only the
      stored heartbeat to a future value and require holder, both clocks, tolerance, and
      reconciliation text in the report. Falsifier: Map the future-heartbeat row to
      REFUSED_CLAIMED; task-clock/named-report must fail.
    falsified_by: >
      Map the future-heartbeat row to REFUSED_CLAIMED; task-clock/named-report must fail.
  - id: AC2
    text: >
      Claim: Reporting is read-only and never makes an uncertain task claimable or terminates its
      holder. Set: task_report, report_lines, claimable, and TaskController reads while a separate
      real claimant owns the task. Completeness: Race repeated reports with heartbeat writes and a
      second claimant; compare ledger bytes or authority versions before and after reads and
      require zero new grants for future-beyond-tolerance observations. SIGSTOP the holder without
      changing its future timestamp and retain uncertainty. Falsifier: Treat an uncertain report
      row as open and race a second claimant; task-clock/no-offer must detect the offered held
      task.
    falsified_by: >
      Treat an uncertain report row as open and race a second claimant; task-clock/no-offer must
      detect the offered held task.
  - id: AC3
    text: >
      Claim: Ordinary task results and terminal outcomes retain their existing meaning while
      uncertainty survives serialization and restart. Set: All existing task report reason
      families, including missing task directory, no tasks, concluded, capability refusal, and
      ordinary live claims. Completeness: Derive reason coverage from tasks.py and VELDO-0015
      liveness states, execute real CLI/report reads, then restart the reporting process over
      unchanged stored records. Compare each expected classification without fixed population
      counts. Falsifier: Serialize unanswerable as claimed before restarting the reporting reader;
      task-clock/restart-reason must detect the lost distinction.
    falsified_by: >
      Serialize unanswerable as claimed before restarting the reporting reader;
      task-clock/restart-reason must detect the lost distinction.
required_evidence: [unit, integration]
rollback: >
  Revert the report presentation only while retaining canonical claim stand-down; never clear
  claims to make reporting appear healthy.
---

## Intent

Make task reporting distinguish clock uncertainty from ordinary claim contention without releasing ownership.

## Context

Package B, W17 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R25, R51-R52, R57. Package A supplies the accepted contracts; this draft grants no implementation or activation authority.

The high risk floor reflects the consequences of failure in this boundary. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

Clock detection, landing refusal, and status styling are outside this report concern.

## Notes

The baseline tasks.claim_answer calls is_claimed and task_report groups REFUSED_CLAIMED without exposing uncertainty. Reuse claim.liveness rather than adding another skew threshold. D1 is inherited for the enrolled W16 path; the existing common-directory reporting fixture remains useful before activation. This spec does not change legacy task completion semantics, which broader migration work owns.

