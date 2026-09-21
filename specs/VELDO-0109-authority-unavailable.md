---
schema: veldo.spec/v1
id: VELDO-0109
title: An unreachable authority stops mutation and admission, and never becomes a local one
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W86
plan_revision: 2
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0025, VELDO-0029, VELDO-0107, VELDO-0108]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_client.py"
  - ".veldo/control_client.py"
  - "scripts/suites/*_veldo_0109_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0109-authority-unavailable.md"
  - "specs/index.md"
  - "proof/VELDO-0109/*"
behavior_bearing: true
observability:
  logs: >
    Every refusal names AUTHORITY_UNAVAILABLE, the service identity it was trying to reach, and the
    last watermark it saw; every stale read is labeled stale with that watermark.
  metrics: >
    Count unavailable refusals by client kind, so a fleet that has quietly stopped is visible.
  error_taxonomy: >
    Distinguish an authority that never answered, one that died mid-request, and a relay that died
    while the authority lives.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: With the authority killed, every registered mutating client refuses with
      AUTHORITY_UNAVAILABLE naming the service and the last watermark, and none of them starts one,
      creates a database, or writes a ledger. Set: Enrolled claim, command and dispatch-admission
      clients, with the authority SIGKILLed after enrollment, and separately the relay killed while
      the authority lives. Completeness: The filesystem under every clone and the process census
      are compared before and after, so a file or a process created by the refusal path is visible
      rather than assumed absent. Falsifier: Fall back to a clone-local ledger after socket loss;
      unavailable/no-local-authority-appears must fail.
    falsified_by: >
      Fall back to a clone-local ledger after socket loss;
      unavailable/no-local-authority-appears must fail.
  - id: AC2
    text: >
      Claim: Inspection still answers, and every answer it gives is LABELED stale and carries the
      watermark it was last sure of. Set: Every inspection call, before and after the kill.
      Completeness: An unlabeled answer fails the row, so silence about staleness is a failure and
      not merely a missing nicety. Falsifier: Return the last known state unlabeled;
      unavailable/a-stale-read-says-so must fail.
    falsified_by: >
      Return the last known state unlabeled; unavailable/a-stale-read-says-so must fail.
  - id: AC3
    text: >
      Claim: Nothing auto-starts the authority. A client that cannot reach it refuses; starting one
      is an operator act. Set: Every client, run with the authority absent and with its socket
      present but dead. Completeness: The process census after every call is compared with the one
      before. Falsifier: Start the authority on first use;
      unavailable/no-client-starts-the-authority must fail.
    falsified_by: >
      Start the authority on first use; unavailable/no-client-starts-the-authority must fail.
required_evidence: [unit, integration]
rollback: >
  None needed: the behaviour is refusal. Restoring the authority restores service.
---

## Intent

When the authority cannot be reached, work stops and says so, and no second authority quietly appears to take its place.

## Context

PLAN-0019 W86, revision 2. Design clauses R20 and R26. Split out of VELDO-0029 by Dmitry on 2026-09-21.

This is the item where the convenient behaviour is the dangerous one. A client that cannot reach the authority and writes locally "until it comes back" has created a second authority, and the two will disagree about work that was accepted. R26's recovery rules assume one history; a local fallback silently breaks that assumption at exactly the moment nobody is watching.

Stale inspection is allowed because refusing to answer a question about the past helps nobody. Answering it without saying the answer is old is the failure.

## Out of scope

Recovery, replay and reconciliation after the authority returns are W-later items under R26. This item covers the window in which it is gone.

## Notes

The kill matrix here is the same shape control_store already uses for its own crash points, so the fixture is a sibling of one that exists rather than a new one.
