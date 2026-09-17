---
schema: veldo.spec/v1
id: VELDO-0054
title: Decision-record dependency evaluation for the floor slice
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W39
plan_revision: 1
depends_on: [VELDO-0016, VELDO-0017, VELDO-0018, VELDO-0019, VELDO-0020, VELDO-0021, VELDO-0022, VELDO-0023, VELDO-0024, VELDO-0025, VELDO-0026, VELDO-0027, VELDO-0028, VELDO-0029, VELDO-0030, VELDO-0031, VELDO-0032, VELDO-0033, VELDO-0034, VELDO-0035, VELDO-0036, VELDO-0037, VELDO-0038, VELDO-0039, VELDO-0040, VELDO-0041, VELDO-0042, VELDO-0043, VELDO-0044, VELDO-0045, VELDO-0046, VELDO-0047, VELDO-0048, VELDO-0052]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/plan.py"
  - ".veldo/plan.py"
  - "packs/*/.veldo/plan.py"
  - "engine/.veldo/frontier.py"
  - ".veldo/frontier.py"
  - "packs/*/.veldo/frontier.py"
  - "engine/.veldo/control_eligibility*.py"
  - ".veldo/control_eligibility*.py"
  - "packs/*/.veldo/control_eligibility*.py"
  - "engine/.veldo/control_decision_dependency*.py"
  - ".veldo/control_decision_dependency*.py"
  - "packs/*/.veldo/control_decision_dependency*.py"
  - "scripts/suites/*_veldo_0054_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0054-floor-decision-dependencies.md"
  - "specs/index.md"
  - "proof/VELDO-0054/*"
behavior_bearing: true
observability:
  logs: >
    Decision blockers identify exact framing, subject revision, settlement receipt, governing
    observation, and affected unit.
  metrics: >
    Count unresolved references, stale settlements, expired observations, withdrawn offers, and
    impacted completed dependents.
  traces: >
    Trace each plan open-decision reference through the accepted combined graph to the published
    ruling and reverse invalidation closure.
  error_taxonomy: >
    Distinguish absent or ambiguous decision, changed framing, wrong subject, insufficient
    authority, expired observation, and pending settlement export.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: plan._decision_blocks, item_state, cmd_run_check, and frontier._plan_build_candidates
      resolve governing decision references against current accepted decision bindings. Set: Real
      plan and decision artifacts plus signed fixture settlements in control.sqlite3, across
      project, release execution, plan, backlog item, spec, and contract bindings supported by A.
      Completeness: Enumerate A binding kinds and unresolved target states; drive each through
      actual plan CLI, frontier, and direct executor/review eligibility. Change framing bytes
      without changing the displayed ID/version, substitute subject digests, and remove referenced
      decisions. Unpublished, stale, or unsupported rulings remain blockers by name; valid current
      fixtures unblock only their bound scope. Falsifier: Treat the presence of a settlement receipt
      as resolution without checking full framing digest; decisions/framing-substitution must detect
      unauthorized eligibility.
    falsified_by: >
      Treat the presence of a settlement receipt as resolution without checking full framing digest;
      decisions/framing-substitution must detect unauthorized eligibility.
  - id: AC2
    text: >
      Claim: Decision supersession, expiry, or invalidation withdraws queued and running permissions
      and preserves completed history with impact obligations. Set: plan._decision_blocks and shared
      floor eligibility over mixed plan/spec/decision edges stored in the real combined graph, with
      real claimant and reviewer processes. Completeness: Construct all edge families from A,
      including a cycle spanning separately acyclic families. Compute reverse closure independently.
      Race signed invalidation against claim, direct review, and publication eligibility, then
      SIGKILL after invalidation commit before notification. Replay must retain every affected
      blocker and completed impact record without authorizing the previous graph. Falsifier: Keep
      cached resolved decisions after supersession commits and restart the consumer;
      decisions/restart-invalidation must detect a running dependent still permitted to publish.
    falsified_by: >
      Keep cached resolved decisions after supersession commits and restart the consumer;
      decisions/restart-invalidation must detect a running dependent still permitted to publish.
  - id: AC3
    text: >
      Claim: Decision eligibility consumes current trusted governing observations and accepted
      review dispositions; missing or stale measurements cannot authorize work. Set:
      plan.cmd_run_check and frontier.claimable plus direct floor entries consuming persisted R71
      observation and decision-review fixtures, including explicit advisory assumptions.
      Completeness: Derive observation/source/subject/freshness requirements from each accepted
      decision. Expire measured and manual records, corrupt signatures, introduce contradictory
      readings, duplicate one principal across review records, and remove blocking-objection
      dispositions. Query real SQLite snapshots and signed files in separate processes; only
      explicit non-authorizing advisory assumptions may warn without blocking. Falsifier: Accept a
      stale measured governing observation after its maximum age expires;
      decisions/stale-observation must detect a newly granted floor entry.
    falsified_by: >
      Accept a stale measured governing observation after its maximum age expires;
      decisions/stale-observation must detect a newly granted floor entry.
required_evidence: [unit, integration]
rollback: >
  Stop affected enrolled entries, preserve signed history and pending obligations, and restore the
  prior compatible consumer only after current authorization is revalidated.
---

## Intent

Connect existing plan decision blockers to exact accepted settlements and current governing evidence.

## Context

Package C, W39 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A and B contracts govern this repair. This is a draft, not implementation or activation authority.

R14, R51, R58, R70-R71 require decision consumption before the slice. Incorrect binding or invalidation can keep work executable after its authority changes. The declared risk floor is high; required approval must bind the eventual change and proof and is not recorded by this declaration.

## Out of scope

No live channel or tripwire is activated, and no fixture assertion certifies an actual owner decision.

## Notes

D1/D2 block the backing store and published settlement boundary. D3/D4 remain inherited prerequisites for floor execution; fixture rulings do not resolve any of D1-D4. The baseline _decision_blocks reads inline blocks only; it neither authenticates settlement nor evaluates observation freshness. Proposed control_decision_dependency paths belong to contracts/fleet and need explicit inventory and architecture mapping before ready. Use real OpenSSH signatures on recorded fixture commands, including canonical operation/target/parameter digests. Mutating those parameters under the original envelope must refuse before state change. Preserve mutation diffs and failed rows. E owns real decision review production, tripwire acquisition, channel attribution, atomic settlement, and interrupted decision journeys.
