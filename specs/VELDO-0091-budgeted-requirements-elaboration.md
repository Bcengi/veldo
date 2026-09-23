---
schema: veldo.spec/v1
id: VELDO-0091
title: Budgeted requirements elaboration
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W76
plan_revision: 3
depends_on: [VELDO-0037, VELDO-0062, VELDO-0079, VELDO-0085, VELDO-0088, VELDO-0090]
placement: [contracts, loop, metrics, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/tasks.py"
  - "packs/*/.veldo/tasks.py"
  - "engine/.veldo/control_elaboration*.py"
  - ".veldo/control_elaboration*.py"
  - "packs/*/.veldo/control_elaboration*.py"
  - "engine/.veldo/control_reservation*.py"
  - ".veldo/control_reservation*.py"
  - "packs/*/.veldo/control_reservation*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0091_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0091-budgeted-requirements-elaboration.md"
  - "specs/index.md"
  - "proof/VELDO-0091/*"
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
      Claim: Elaboration publishes versioned requirements, assumptions, alternatives, specs,
      dependencies and questions. Set and completeness: Enumerate these output roles against real
      artifacts allocated by 0037/0085 for an accepted objective; ensure required scope/acceptance
      questions reach the owner and dependencies reach shared eligibility, with no self-admission.
      Falsifier: Admit a generated feature automatically; the generated-work authority check must
      fail.
    falsified_by: >
      Admit a generated feature automatically; the generated-work authority check must fail.
  - id: AC2
    text: >
      Claim: Finite reasoning limits bound every continuation and repeated unchanged proposal. Set
      and completeness: Derive cycle/token/time/repetition limits from the accepted coordination
      policy and drive below, at and above each bound with actual adapter processes; retain cycle
      receipts and produce a named owner stop at exhaustion, releasing workers while waiting.
      Falsifier: Reset unchanged-proposal count on each continuation; the repetition-limit check
      must fail.
    falsified_by: >
      Reset unchanged-proposal count on each continuation; the repetition-limit check must fail.
  - id: AC3
    text: >
      Claim: Every elaboration subscription CLI invocation checks and reserves usage allowance
      before launch. Set and completeness: Enumerate initial, retry and follow-on paths using
      0036/0062 invocation/time caps, CLI-reported tokens/messages and exposed rate-limit windows;
      observe available, exhausted and unbounded unknown remaining allowance after recorded usage
      and outstanding reservations. Refusals launch nothing and workers stop at their caps.
      No price or per-request monetary maximum is required. Falsifier: Raise the
      budget after a pre-call refusal; the exhausted-budget stop check must fail.
    falsified_by: >
      Raise the budget after a pre-call refusal; the exhausted-budget stop check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Budgeted requirements elaboration. Deliver the normal function needed by the running factory journey.

## Context

W76 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

Elaboration creates requirements and specifications, dependencies and authentic owner
questions; it never admits its output. Bound cycles, tokens, elapsed time and unchanged
proposals in Veldo. 0062 supplies qualified subscription usage controls and live accounting for
both engines, with conservative treatment of unknown usage.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, pre-invocation subscription usage caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 concurrent-
author/retry, AC2 checkpoint-deletion recovery and AC3 delayed-report/cancellation/concurrent-
allocation qualification moved to Release 2. Elaboration, questions, finite reasoning limits
and pre-call caps remain. The criteria, declared evidence universe, Context and Notes above
now carry only the retained function. No specification status or historical proof was changed.
