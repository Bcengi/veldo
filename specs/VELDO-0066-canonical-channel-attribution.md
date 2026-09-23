---
schema: veldo.spec/v1
id: VELDO-0066
title: Canonical channel attribution including platform-derived chat message, sender, and time
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W51
plan_revision: 3
depends_on: [VELDO-0020, VELDO-0065]
placement: [tracker, engine, contracts, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_channel_attribution*.py"
  - ".veldo/control_channel_attribution*.py"
  - "packs/*/.veldo/control_channel_attribution*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0066_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0066-canonical-channel-attribution.md"
  - "specs/index.md"
  - "proof/VELDO-0066/*"
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
      Claim: Telegram acquisition retains canonical sender, message, timestamp and conversation
      identity. Set and completeness: Use a real Telegram sandbox with enrolled and unknown actors;
      inspect the actual platform response for every required field, rename display names and try
      text-only transcripts. Map only stable sender identity to membership. Falsifier: Use display
      name as principal identity; a duplicate-name answer must be misattributed and fail the check.
    falsified_by: >
      Use display name as principal identity; a duplicate-name answer must be misattributed and fail
      the check.
  - id: AC2
    text: >
      Claim: Canonical evidence binds the actual answer to its presented request version. Set and
      completeness: Acquire a real reply to a known presentation and compare reply/message/chat
      references and offered ruling; try another chat, omitted reference and altered source bytes.
      Unproven attribution or presentation relation refuses. Falsifier: Accept a reply to another
      presentation; the canonical-binding check must fail.
    falsified_by: >
      Accept a reply to another presentation; the canonical-binding check must fail.
  - id: AC3
    text: >
      Claim: Person-required decisions accept only the current authorized enrolled person. Set and
      completeness: Exercise authorized owner, unrecognized sender and automation identity through
      the real edge and authority; missing canonical fields and caller-supplied actor labels must
      not grant person authority. Falsifier: Treat an automation sender as the enrolled owner; the
      person-required refusal check must fail.
    falsified_by: >
      Treat an automation sender as the enrolled owner; the person-required refusal check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Canonical channel attribution including platform-derived chat message, sender, and time. Deliver the normal function needed by the running factory journey.

## Context

W51 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Canonical Telegram evidence comes from the authenticated platform exchange, never pasted
transcript text. The edge attests acquisition rather than inventing a personal local
signature. Signed CLI, Jira and email decision-channel acquisition are not part of this
specification revision.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC3 signed-CLI
and AC1/AC2 email history breadth moved to Release 4; interrupted history qualification moved
to Release 2. Jira acquisition/normalizer work is dropped. Canonical Telegram identity and
answer binding remain. The criteria, declared evidence universe, Context and Notes above now
carry only the retained function. No specification status or historical proof was changed.
