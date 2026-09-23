---
schema: veldo.spec/v1
id: VELDO-0064
title: Assignment inbox and durable projections on enrolled input surfaces
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W49
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0035, VELDO-0046]
placement: [contracts, tracker, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_projection.py"
  - ".veldo/request_projection.py"
  - "packs/*/.veldo/request_projection.py"
  - "engine/.veldo/request_doorbell.py"
  - ".veldo/request_doorbell.py"
  - "packs/*/.veldo/request_doorbell.py"
  - "engine/.veldo/control_assignment*.py"
  - ".veldo/control_assignment*.py"
  - "packs/*/.veldo/control_assignment*.py"
  - "engine/.veldo/control_channel_projection*.py"
  - ".veldo/control_channel_projection*.py"
  - "packs/*/.veldo/control_channel_projection*.py"
  - "engine/.veldo/control_claim.py"
  - ".veldo/control_claim.py"
  - "packs/*/.veldo/control_claim.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0064_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0064-assignment-inbox-projections.md"
  - "specs/index.md"
  - "proof/VELDO-0064/*"
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
      Claim: The inbox exposes person-required assignments without holding a worker while awaiting
      the answer. Set and completeness: Enumerate enabled pending, answered, declined and canceled
      states from the assignment schema; drive real commands and Telegram projection and compare
      owner, scope, deadline and budget to current authority state, with no waiting model process or
      claim. Falsifier: Retain a worker claim while waiting for the person; the waiting-resource
      check must fail.
    falsified_by: >
      Retain a worker claim while waiting for the person; the waiting-resource check must fail.
  - id: AC2
    text: >
      Claim: Telegram projection retains the actual external message identity and request
      correlation. Set and completeness: Send each enabled assignment kind through the qualified
      Telegram edge; persist the returned chat/message identifiers and compare them with retrieved
      presentation bytes and the inbox request version. Falsifier: Discard the returned message
      identifier; the projection-correlation check must fail.
    falsified_by: >
      Discard the returned message identifier; the projection-correlation check must fail.
  - id: AC3
    text: >
      Claim: Inbox views describe current assignments but do not grant authority. Set and
      completeness: Read pending and changed assignment versions through the actual index/brief
      readers, including an invalid record; require visible invalid state or current accepted
      content, never authority from assignee or display status. Falsifier: Admit work from a
      displayed assigned status alone; the unauthorized-admission check must fail.
    falsified_by: >
      Admit work from a displayed assigned status alone; the unauthorized-admission check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Assignment inbox and durable projections on enrolled input surfaces. Deliver the normal function needed by the running factory journey.

## Context

W49 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Use one authoritative inbox and ordinary Telegram projection; invalid accepted records must be
visible rather than silently skipped. The waiting owner decision must release model workers
and execution claims. The same inbox is read by the later authenticated UI/API.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

Open question for the owner (review r2, 2026-09-23). This item does not say what becomes of the
blocked unit when its assignment is declined or canceled, or when the owner's answer no longer
admits (for example, a key revoked from before the answer was accepted). Such a unit stays
parked: no Release 1 command claims it, resumes it or returns it to the backlog. The inbox lists
every parked unit with its assignment and why it is parked (`parked_units`, and `parked` and
`parked_by_reason` in its metrics), so none is invisible, but the implementation decides
nothing about it. Whether a decline or cancel should release the unit, re-open it for another
holder, retire it, or wait for a new assignment is the owner's decision.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 3: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 lost-
create-ack and AC3 concurrent reassignment/channel-removal matrices moved to Release 2; extra
channels moved to Release 4. Jira-specific projection work is dropped. Telegram inbox and
release of waiting workers remain. The criteria, declared evidence universe, Context and Notes
above now carry only the retained function. No specification status or historical proof was
changed.

2026-09-23, implementation: `scripts/check_teeth_mutations.py` was added to the footprint so the
declared falsifiers can be registered as finding 64 of the existing teeth mutation driver. The
criteria, status and risk are unchanged.

2026-09-23, review r1: the claim organ (`control_claim.py`, VELDO-0031) was added to the
footprint because the parked state is part of this item's contract: a unit whose claim was given
up for a pending person assignment must not be claimable until that assignment admits the
blocked work. The change is made through the claim organ's own transition, as a `park` release
and a `resume` claim that only the inbox's store transaction reaches, and the VELDO-0031 suites
and finding-31 mutations stay green. The criteria, status and risk are unchanged.
