---
schema: veldo.spec/v1
id: VELDO-0077
title: Objective acceptance and signed outcome assessment
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W62
plan_revision: 3
depends_on: [VELDO-0076, VELDO-0069, VELDO-0126]
placement: [contracts, engine, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/authorization.py"
  - ".veldo/authorization.py"
  - "packs/*/.veldo/authorization.py"
  - "engine/.veldo/control_objective*.py"
  - ".veldo/control_objective*.py"
  - "packs/*/.veldo/control_objective*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0077_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0077-objective-acceptance-outcome-assessment.md"
  - "specs/index.md"
  - "proof/VELDO-0077/*"
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
      Claim: Objective acceptance binds the exact observable outcome, scope, authority and evidence
      requirements. Set and completeness: Create an objective in one project through the shared
      intake and present it for current owner acceptance; alter a bound field and refuse the stale
      answer. After acceptance propose a later feature and inspect absent admission/priority until
      separately authorized. Falsifier: Admit a feature when its objective is accepted; the later-
      feature check must fail.
    falsified_by: >
      Admit a feature when its objective is accepted; the later-feature check must fail.
  - id: AC2
    text: >
      Claim: Satisfaction requires an authorized evidence assessment of the accepted objective
      revision. Set and completeness: Exercise a specification-supported objective with proven
      outcome, shipped specs but unproven outcome, missing evidence, wrong signer and stale
      objective revision; only complete current evidence may satisfy it. Falsifier: Treat all specs
      shipped as sufficient; the unproven-outcome refusal check must fail.
    falsified_by: >
      Treat all specs shipped as sufficient; the unproven-outcome refusal check must fail.
  - id: AC3
    text: >
      Claim: Objective cancellation records explicit disposition of its unfinished work and
      preserves its owner/history. Set and completeness: Cancel a one-project objective with active
      backlog work; inspect the authorized disposition and retained prior receipts, and reject
      reopening a terminal objective without a linked new objective. Falsifier: Cancel contributing
      units without an authorized disposition; the work-disposition check must fail.
    falsified_by: >
      Cancel contributing units without an authorized disposition; the work-disposition check must
      fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Objective acceptance and signed outcome assessment. Deliver the normal function needed by the running factory journey.

## Context

W62 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: a message becomes an objective in one project through the VELDO-0126 common intake and
  is presented to the current owner, whose acceptance (through the VELDO-0068 settlement) binds its
  exact observable outcome, scope, authority and evidence requirements. An accepted objective permits
  bounded elaboration only: features proposed under it still need their own admission and priority.
  It is satisfied only by an authorized evidence assessment of its accepted revision; it is canceled
  only with an explicit, authorized disposition of its unfinished work, and its owner and history are
  kept.
- Threat model: a stale answer accepted after a bound field changed; a feature admitted or
  prioritized because its objective was accepted; satisfaction inferred from shipped specification
  counts, or from missing evidence, a wrong signer or a stale objective revision; contributing units
  canceled without an authorized disposition; a terminal objective reopened without a linked new
  objective; accepted history or receipts changed by cancellation. The owner's account, the store and
  the signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); objectives
  spanning projects and additional owners (Release 3); recovery and restart (Release 2); forged rows in
  our own store and files planted in the installed directory.

## Notes

An accepted objective permits bounded elaboration only. 0059 starts at common message intake
before this acceptance; generated features require separate admission and priority. Outcome
satisfaction must be assessed against evidence, never inferred from shipped specification
counts.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 4: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 full
transition/channel and AC2 release-contribution breadth moved to Releases 3/4; AC2 replay and
AC3 restart moved to Release 2; cross-project depth moved to Release 3. Exact objective
acceptance and evidence-based satisfaction remain. The criteria, declared evidence universe,
Context and Notes above now carry only the retained function. No specification status or
historical proof was changed.

2026-09-25, build: `.veldo/control_objective.py` (new, installed by the scaffold) is the one writer of
objective records and the features under them; acceptance applies a VELDO-0068 settlement on the
decision_disposition touchpoint bound to the objective's current revision, digest and shown brief;
features are RAW and never admitted or prioritized by it; satisfaction is the bound assessor's signed
assessment of the accepted revision over kept evidence records; cancellation needs the owner's
disposition of every unfinished feature. `request.py` and `authorization.py` were not changed: they are
not on the control store path. Proof in `proof/VELDO-0077/`; status stays ready.
