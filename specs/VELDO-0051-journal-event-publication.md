---
schema: veldo.spec/v1
id: VELDO-0051
title: Canonical event vocabulary and journal-derived publication
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W36
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0049, VELDO-0050]
placement: [metrics, contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/events.py"
  - ".veldo/events.py"
  - "packs/*/.veldo/events.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate.py"
  - "packs/*/.veldo/validate.py"
  - "engine/.veldo/control_event*.py"
  - ".veldo/control_event*.py"
  - "packs/*/.veldo/control_event*.py"
  - "scripts/suites/*_veldo_0051_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0051-journal-event-publication.md"
  - "specs/index.md"
  - "proof/VELDO-0051/*"
behavior_bearing: true
observability:
  logs: >
    Projection records expose journal sequence, unit, dispatch, event identity, output watermark,
    and recovery cursor.
  metrics: >
    Measure canonical type coverage, publication lag, duplicate delivery suppression, and corrupt
    projection refusals.
  traces: >
    Join signed journal record and receipt digest to each deterministic event line and its explicit
    repository destination.
  error_taxonomy: >
    Distinguish unknown type, unauthorized event owner, wrong repository, unpublished record, cursor
    gap, and damaged projection.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: events.make_event, refuse_unknown_type, _append_events, and validate.check_events
      consume one canonical event vocabulary while preserving accepted historical schema spellings.
      Set: Every registered emitted/projected event type, including run, request, incident, proof,
      review, and landing events, serialized into real JSONL files and read by a separate validator
      process. Completeness: Compare producer registrations and canonical registry in both
      directions; emit each allowed type through its actual owner and validate resulting bytes.
      Corrupt type and schema independently, and exercise extra-field type substitution at the real
      writer. Unknown values refuse before any invalid line is published. Falsifier: Remove run.done
      from validator recognition while retaining its registered producer;
      events/vocabulary-roundtrip must fail on that real serialized event.
    falsified_by: >
      Remove run.done from validator recognition while retaining its registered producer;
      events/vocabulary-roundtrip must fail on that real serialized event.
  - id: AC2
    text: >
      Claim: events.reconcile_verdicts and _reconcile_pass route enrolled publication through
      ordered signed journal projection; replay appends each logical event once without merging
      independent authority logs. Set: Real materializer processes, control.sqlite3 published
      journal records, persisted cursors, and .veldo/events.jsonl projections in two enrolled
      clones. Completeness: Race two projectors using real locks; SIGKILL before file publication,
      after publication before cursor acknowledgment, and after cursor commit. Restart and compare
      event identities/order and watermark to the full published journal prefix, preserving existing
      historical bytes and reporting damaged tails rather than truncating them. Falsifier: Advance
      the projection cursor before durable file publication and kill in that window;
      events/cursor-gap must detect the missing journal-derived event.
    falsified_by: >
      Advance the projection cursor before durable file publication and kill in that window;
      events/cursor-gap must detect the missing journal-derived event.
  - id: AC3
    text: >
      Claim: events.emit cannot manufacture enrolled completion or redirect a journal projection
      through ambient ROOT; spec.shipped requires the remote-confirmed replicated landing receipt.
      Set: Direct emit, reconcile_verdicts, and journal projection calls from separate real
      processes with explicit domain/repository identities, two repositories, and a bare remote.
      Completeness: Try forged producer strings, changed unit/dispatch bindings, build-only results,
      an unacknowledged landing export, and a valid replicated landing. Point process cwd and
      imported module ROOT at the other repository; compare both logs and journals and require no
      false shipped event or wrong-root write. Falsifier: Permit direct emit of spec.shipped after a
      build-only attempt without a landing receipt; events/completion-owner must detect the
      unsupported line.
    falsified_by: >
      Permit direct emit of spec.shipped after a build-only attempt without a landing receipt;
      events/completion-owner must detect the unsupported line.
required_evidence: [unit, integration]
rollback: >
  Stop affected enrolled entries, preserve signed history and pending obligations, and restore the
  prior compatible consumer only after current authorization is revalidated.
---

## Intent

Publish a complete, ordered event view from authoritative receipts using one accepted vocabulary.

## Context

Package C, W36 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R23, R28, R51-R54, R70, and R76 govern event consumption. A fabricated completion event or skipped journal record can mislead downstream eligibility. The declared risk floor is critical; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

Full historical migration is H; live channel event production is E; source publication is W42.

## Notes

D1 and D2 block journal authority and publication acknowledgment. D3 and D4 remain inherited A/B package prerequisites, but this projection adds no runner or clone policy. The existing legacy verdict projector is descriptive; its producer string is not authentication. Keep historical exports append-only and qualify explicit cutover routing without fabricating old signatures. control_event is a proposed narrow adapter under metrics/contracts; register its final path before ready and distribute it byte-identically. Mutation proof must show the altered registry or cursor code and the named failing row. Gate observation redirection is W43, not permission to make event history an independently merged source of truth.
