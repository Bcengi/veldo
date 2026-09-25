---
schema: veldo.spec/v1
id: VELDO-0069
title: Governing decision binding, supersession, and eligibility updates
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W54
plan_revision: 3
depends_on: [VELDO-0054, VELDO-0068]
placement: [contracts, tracker, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/decision.py"
  - ".veldo/decision.py"
  - "packs/*/.veldo/decision.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/request_reconcile.py"
  - ".veldo/request_reconcile.py"
  - "packs/*/.veldo/request_reconcile.py"
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/control_decision_dependency*.py"
  - ".veldo/control_decision_dependency*.py"
  - "packs/*/.veldo/control_decision_dependency*.py"
  - "engine/.veldo/control_request_settlement*.py"
  - ".veldo/control_request_settlement*.py"
  - "packs/*/.veldo/control_request_settlement*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0069_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0069-governing-decision-bindings.md"
  - "specs/index.md"
  - "proof/VELDO-0069/*"
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
      Claim: A current settlement updates its exact governing decision and subject binding
      atomically. Set and completeness: Drive real signed Telegram settlement for a blocking
      specification question and plan decision; read chosen option, decider, time, framing and
      subject digests plus eligibility from another process. Falsifier: Commit only a receipt
      without the governing binding; the resolved-request-to-eligibility check must fail.
    falsified_by: >
      Commit only a receipt without the governing binding; the resolved-request-to-eligibility check
      must fail.
  - id: AC2
    text: >
      Claim: Wrong framing, subject or current version cannot unblock governed work. Set and
      completeness: Alter each of those three bindings independently under an otherwise valid
      settlement through decision/request reconciliation; inspect unchanged permissions and a named
      blocker in plan and direct floor entry. Falsifier: Ignore subject digest during binding; the
      wrong-subject refusal check must fail.
    falsified_by: >
      Ignore subject digest during binding; the wrong-subject refusal check must fail.
  - id: AC3
    text: >
      Claim: Only the accepted binding resolves a referenced decision at every enabled consumer. Set
      and completeness: Enumerate plan._decision_blocks/item_state/cmd_run_check and shared floor
      consumers; compare unresolved, valid current and inline-status-only cases using real
      snapshots. Falsifier: Treat inline open_decisions text as authority; the inline-bypass check
      must fail.
    falsified_by: >
      Treat inline open_decisions text as authority; the inline-bypass check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Governing decision binding, supersession, and eligibility updates. Deliver the normal function needed by the running factory journey.

## Context

W54 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 3.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: an owner settles a blocking specification question or a plan decision through the
  VELDO-0068 settlement (a signed Telegram answer, later the authenticated API). In the same
  transaction the settlement writes the governing binding: the decision it resolves, the chosen option,
  the decider, the time, and the digests of the framing, the subject and its current version. The plan
  (_decision_blocks, item_state, cmd_run_check) and the shared floor entry then read the item as
  unblocked from that binding alone, and another process sees the same answer.
- Threat model: a receipt committed without its binding; a settlement whose framing, subject or current
  version does not match the governed item unblocking it anyway; inline open_decisions text or a
  detached receipt treated as authority by any enabled consumer; an unsupported subject kind bound
  instead of stopped. The owner's account, the store and the signing edge are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); commit
  barrier crashes, concurrent and restart matrices (Release 2); expiry, reopening, tripwires and reverse
  invalidation (Release 3); forged rows in our own store and files planted in the installed directory.

## Notes

The actual settlement producer updates 0054 decision consumers. Ordinary spec/plan bindings
are in this slice; unsupported subject kinds stop. A detached receipt and inline resolved text
grant no eligibility. UI/API answers later share this binding operation.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC1 commit-
barrier crashes and AC2/AC3 concurrent/restart matrices moved to Release 2; expiry, reopening,
tripwires and reverse invalidation moved to Release 3. Normal settlement updates its exact
governing binding. The criteria, declared evidence universe, Context and Notes above now carry
only the retained function. No specification status or historical proof was changed.

2026-09-24, implementation: the VELDO-0068 settlement service is the binding producer. A request whose
terms target a governing decision (target kind `governing_decision`, only through the decision_disposition
touchpoint) names the exact question: the record, its decision id and revision, and the framing, subject and
scope digests, with the digest of that question. Settling it writes, in the settlement's own store
transaction, a `decision_settlement` binding keyed by the record and the revision ruled on: the chosen
option, the decider, the time and a body in the VELDO-0054 signed shape, signed by the configured decision
signer (a new `decision_signer` of the service, trusted by the hosts through their settlement signers). The
body records the question the owner was shown, never the record at settlement, so a wrong framing, subject
or revision is bound faithfully and every VELDO-0054 consumer names it (unbound_decision) instead of
unblocking; a later revision's binding supersedes an earlier one. An unsupported subject kind, an absent
record or a missing decision signer stops the settlement by name with nothing written. The consumers
(plan.py, the Gate, control_decision_dependency.py) needed no change. The binding kind is owned by the
settlement command. Suite `70_veldo_0069_bindings`, mutations in finding 69, proof in proof/VELDO-0069/.

2026-09-24, review fixes: a governing question at a revision above the record's current one, as read and
pinned in the settling transaction, is refused as `future_revision` (class stale_subject) with nothing
written; before, it settled and its binding cleared the work once the record reached that revision. Terms
are not checked against the record. New rows `refusal/future-revision` (red at 5596c04 by assertion) and
`binding/owner-ruling` (the owner rejects and returns for elaboration; the signed ruling blocks by
`decision_ruling` at every consumer). Mutations `future-revision-accepted` and `ruling-forced-approve`;
`binding-choice-generic` re-aimed as `binding-choice-forced-accept` on the ruling row.
