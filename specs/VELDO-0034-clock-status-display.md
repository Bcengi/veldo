---
schema: veldo.spec/v1
id: VELDO-0034
title: Clock uncertainty in the status display
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W19
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0031]
placement: [loop, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/status_server.py"
  - ".veldo/status_server.py"
  - "packs/*/.veldo/status_server.py"
  - "engine/.veldo/runstatus.py"
  - ".veldo/runstatus.py"
  - "packs/*/.veldo/runstatus.py"
  - "engine/.veldo/work_state.py"
  - ".veldo/work_state.py"
  - "packs/*/.veldo/work_state.py"
  - "scripts/suites/*_veldo_0034_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0034-clock-status-display.md"
  - "specs/index.md"
  - "proof/VELDO-0034/*"
behavior_bearing: true
observability:
  logs: >
    Status diagnostics identify the uncertain run or claim and the observation watermark without
    changing its ownership.
  metrics: >
    Show uncertain counts separately from active and stale counts, retaining terminal run counts.
  traces: >
    Connect JSON classification to the rendered badge and clock detail for the same run
    observation.
  error_taxonomy: >
    Distinguish unanswerable clock, unconfirmed liveness, stale observation, terminal run, and
    unavailable authority.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The existing status JSON, text, and browser rendering distinguish clock uncertainty
      with visible text, a dedicated badge treatment, and clock details. Set: runstatus and
      status_server reading real run registry and claim data, including work_state future-stamp
      LIVENESS_UNCONFIRMED. Completeness: Launch the real loopback HTTP server over fixture Git
      common-directory records, fetch JSON and load the page in a real browser, inspect the
      rendered badge and text, and compare each surface against installed runlog.classify and
      work_state.liveness. Inject a future timestamp and require both clocks, tolerance, and
      operations reconciliation guidance, not color alone. Falsifier: Render unanswerable using
      the active badge and label after corrupting a stored heartbeat into the future;
      clock-status/visible-uncertainty must fail.
    falsified_by: >
      Render unanswerable using the active badge and label after corrupting a stored heartbeat
      into the future; clock-status/visible-uncertainty must fail.
  - id: AC2
    text: >
      Claim: Unknown liveness never appears as available capacity or ordinary active work, and
      terminal outcomes remain terminal. Set: Displayed counts and rows for active, stale,
      blocked, done, aborted, and unanswerable run records. Completeness: Derive the
      classification set from runlog and work_state, populate real records for each, and compare
      totals to an independent expected table. Race a heartbeat update with a status read and
      require one coherent observation per row with its timestamp. Falsifier: Count an
      unanswerable nonterminal run as active when aggregating the real registry;
      clock-status/counts must detect the wrong total.
    falsified_by: >
      Count an unanswerable nonterminal run as active when aggregating the real registry;
      clock-status/counts must detect the wrong total.
  - id: AC3
    text: >
      Claim: Status inspection and reconnect preserve uncertainty without mutating claims or
      implying that process silence resolved it. Set: HTTP status and event-stream reads plus
      command-line status over an uncertain holder during reporter restart. Completeness: SIGSTOP
      the holder and SIGKILL the status process, then reconnect a client after restarting the
      server. Compare claim generations and run state before and after reads and require the named
      uncertainty until a newer authoritative observation exists. Falsifier: Clear the uncertain
      classification on server startup because the holder emitted no output;
      clock-status/reconnect must detect the false healthy display.
    falsified_by: >
      Clear the uncertain classification on server startup because the holder emitted no output;
      clock-status/reconnect must detect the false healthy display.
required_evidence: [unit, integration]
rollback: >
  Revert display changes without changing stored liveness or ownership; retain explicit
  uncertainty in machine-readable output.
---

## Intent

Display clock uncertainty prominently and consistently in the existing status surfaces.

## Context

Package B, W19 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) clauses are R25, R52, R57. Package A contracts must be accepted before implementation; this draft grants no implementation or activation authority.

Misstating uncertain liveness across run and claim surfaces could direct operators to release ownership or capacity without evidence. The declared risk floor is high. Required approval must bind the eventual change and proof; this field does not record approval.

Implementation belongs in engine/ with byte-identical repository and pack copies. Resolve proposed module globs and their area mapping before ready; register each new asset in the distribution inventory and scaffolder as applicable. Proof must compare the declared test universe with executable registrations, drive each falsified_by mutation to its named failing row, retain the applied diff, and revert the mutation. Only model responses may be faked; the named store, processes, signatures, files, and Git operations are real.

## Out of scope

New management consoles, clock remediation, and service installation are excluded.

## Notes

The existing browser surface lacks a dedicated badge for runlog unanswerable. Preserve work_state LIVENESS_UNCONFIRMED with its future-stamp reason instead of forcing every source into a different state vocabulary. D1 is inherited for the enrolled claim view; W32 owns actual socket-boundary loopback enforcement. This item changes the existing status presentation only.

