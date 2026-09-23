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
plan_revision: 3
depends_on: [VELDO-0023, VELDO-0035, VELDO-0050]
placement: [distribution, metrics, contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
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
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Enabled event producers and validators use the same canonical vocabulary. Set and
      completeness: Enumerate registered journey events and preserved historical schema spellings,
      serialize each actual owner event into JSONL and validate in another process; unknown
      type/schema and type substitution refuse. Falsifier: Remove run.done from validator
      recognition while keeping its producer; the vocabulary round trip must fail.
    falsified_by: >
      Remove run.done from validator recognition while keeping its producer; the vocabulary round
      trip must fail.
  - id: AC2
    text: >
      Claim: The event projection follows the committed journal in order at an explicit watermark.
      Set and completeness: Materialize the enabled single-domain event prefix once through the
      actual projector; compare event identity/order, stored watermark and unchanged historical
      bytes with the authoritative sequence. Falsifier: Skip a committed event while advancing the
      watermark; the prefix comparison must fail.
    falsified_by: >
      Skip a committed event while advancing the watermark; the prefix comparison must fail.
  - id: AC3
    text: >
      Claim: Only a confirmed landing receipt can produce spec.shipped for its exact unit and
      dispatch. Set and completeness: Exercise direct emit, build-only, wrong-dispatch receipt,
      unconfirmed remote landing and valid confirmed landing with explicit domain/repository
      coordinates; inspect actual journal and projection. Falsifier: Permit direct spec.shipped
      after build-only; the completion-owner check must fail.
    falsified_by: >
      Permit direct spec.shipped after build-only; the completion-owner check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Canonical event vocabulary and journal-derived publication. Deliver the normal function needed by the running factory journey.

## Context

W36 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

One canonical event vocabulary includes every enabled producer and preserves historical
spellings. The legacy verdict projector is descriptive, not authenticated by its producer
string. Local journal commit is sufficient under amended C3, but source completion still
requires confirmed remote landing.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 multi-
projector/two-clone/crash replay and AC3 replica-failure recovery moved to Release 2; multi-
repository matrix moved to Release 4. Vocabulary and receipt-derived completion remain. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.
