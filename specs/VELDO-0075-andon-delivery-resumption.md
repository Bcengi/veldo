---
schema: veldo.spec/v1
id: VELDO-0075
title: Andon delivery and authorized resumption through enrolled channels
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W60
plan_revision: 3
depends_on: [VELDO-0046, VELDO-0069, VELDO-0073]
placement: [tracker, engine, fleet, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_andon*.py"
  - ".veldo/control_andon*.py"
  - "packs/*/.veldo/control_andon*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0075_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0075-andon-delivery-resumption.md"
  - "specs/index.md"
  - "proof/VELDO-0075/*"
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
      Claim: An authenticated worker or service can request a recorded AWAITING_AUTHORITY stop. Set
      and completeness: Exercise enabled build, review and coordination stop points through real
      commands; preserve reason, interrupted station and resolving-authority predicate even when the
      requester has no right to resume. Falsifier: Require the resolving role merely to raise a
      stop; the missing-stop observation must fail.
    falsified_by: >
      Require the resolving role merely to raise a stop; the missing-stop observation must fail.
  - id: AC2
    text: >
      Claim: The stop reaches Telegram with the current versioned presentation and answer path. Set
      and completeness: For each enabled stop kind use qualified real Telegram sending; change the
      request version with unchanged status and compare message identity, shown content and stored
      correlation. No tracker link is needed. Falsifier: Key the notice only by request ID/status;
      the changed-presentation notice must be suppressed and fail the check.
    falsified_by: >
      Key the notice only by request ID/status; the changed-presentation notice must be suppressed
      and fail the check.
  - id: AC3
    text: >
      Claim: Only the current designated authority settlement resumes a clean decision stop. Set and
      completeness: Answer a clean decision stop with valid owner, wrong actor and stale
      presentation; compare permission and fresh station contract. Also attempt the same answer on
      an unknown-effect stop and require it to remain stopped. Falsifier: Resume on a notification
      acknowledgement without the resolving authority; the unauthorized-resume check must fail.
    falsified_by: >
      Resume on a notification acknowledgement without the resolving authority; the unauthorized-
      resume check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Andon delivery and authorized resumption through enrolled channels. Deliver the normal function needed by the running factory journey.

## Context

W60 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: an authenticated worker or service raises a recorded AWAITING_AUTHORITY stop at an
  enabled build, review or coordination stop point, recording its reason, the interrupted station and
  the predicate for who may resolve it, even when the requester may not resume it. The stop reaches
  the owner in Telegram through the activated edge (VELDO-0073) with the current versioned
  presentation and answer path; a new request version with the same status sends a new notice. A
  clean owner-decision stop resumes only through the current settlement (VELDO-0068) by the
  designated authority, with a fresh station contract.
- Threat model: raising a stop refused because the requester lacks the resolving role; a notice keyed
  only by request id and status, so a changed presentation is never sent; a resume from a
  notification acknowledgement, a wrong actor, a stale presentation or anything but the resolving
  authority's current settlement; an unknown-effect stop resumed by an answer. The owner's account,
  the store, the signer and the Telegram edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery,
  automatic retry and risk disposition of unknown external effects (Release 2); forged rows in our own
  store and files planted in the installed directory. The real-Telegram leg of AC2 is run once by the
  lead with the owner through the running factory (VELDO-0138) and recorded; the rows use a loopback
  stand-in.

## Notes

A clean owner-decision stop may resume after its current authorized settlement. Unknown
external effects remain stopped with their original dispatch and reservations; this
specification grants no recovery, automatic retry or risk-disposition substitute for evidence.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 crash, AC2
lost-send/reconnect and AC3 uncertain-effect/automatic recovery moved to Release 2. Ordinary
stop, Telegram notice and authorized clean decision-stop resumption remain. The criteria,
declared evidence universe, Context and Notes above now carry only the retained function. No
specification status or historical proof was changed.

2026-09-25, build: `.veldo/control_andon.py` (engine copy identical, scaffolded) judged against the
criteria and the reviewer's threat model with no change needed; suite
`scripts/suites/72_veldo_0075_andon.py` with rows for AC1, AC2 and AC3 over the build, review and
coordination stop points, against the production ingress activated by the owner's signed VELDO-0073
commands and a loopback Bot API stand-in; red record against 9fa7e4d by assertion; 19 teeth
mutations as finding 75, each declared falsifier first. AC2's real-Telegram leg is PENDING (the lead
with the owner, VELDO-0138). Status unchanged.
