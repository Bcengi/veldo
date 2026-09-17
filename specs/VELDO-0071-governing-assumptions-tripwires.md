---
schema: veldo.spec/v1
id: VELDO-0071
title: Governing assumption observations and tripwire review flow
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W56
plan_revision: 1
depends_on: [VELDO-0049, VELDO-0050, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0055, VELDO-0056, VELDO-0057, VELDO-0058, VELDO-0059, VELDO-0069, VELDO-0070]
placement: [contracts, tracker, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/tripwire.py"
  - ".veldo/tripwire.py"
  - "packs/*/.veldo/tripwire.py"
  - "engine/.veldo/decision.py"
  - ".veldo/decision.py"
  - "packs/*/.veldo/decision.py"
  - "engine/.veldo/decision_review.py"
  - ".veldo/decision_review.py"
  - "packs/*/.veldo/decision_review.py"
  - "engine/.veldo/request.py"
  - ".veldo/request.py"
  - "packs/*/.veldo/request.py"
  - "engine/.veldo/control_decision_dependency*.py"
  - ".veldo/control_decision_dependency*.py"
  - "packs/*/.veldo/control_decision_dependency*.py"
  - "engine/.veldo/control_assumption*.py"
  - ".veldo/control_assumption*.py"
  - "packs/*/.veldo/control_assumption*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0071_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0071-governing-assumptions-tripwires.md"
  - "specs/index.md"
  - "proof/VELDO-0071/*"
behavior_bearing: true
observability:
  logs: >
    Observation records name assumption, trusted source, subject/framing digest, observation time,
    maximum age, current state, and permission impact.
  metrics: >
    Count missing, expired, contradictory and invalid governing observations, advisory warnings,
    withdrawn permissions, and open review requests by decision.
  traces: >
    Trace trusted reading acquisition through expiration or breach to atomic invalidation,
    replacement review delivery, accepted ruling, and current eligibility.
  error_taxonomy: >
    Distinguish untrusted source, wrong subject, measured expiry, manual expiry, contradictory
    observations, advisory-only warning, and unresolved review.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every governing assumption is evaluated from current trusted observations bound to
      its exact subject, including measured-reading expiry. Set:
      tripwire._validate_reading/_state_for/evaluate_readings and decision.validate_record for
      measured and manual_review observations under every A governing-assumption schema.
      Completeness: Enumerate type, source, subject digest, maximum age and failure treatment from
      accepted assumptions; compare all assumptions to acquired signed observation records. Drive
      real acquisition and authority processes, testing fresh, absent, expired, wrong-source,
      wrong-subject, invalid timestamp/signature and contradictory readings. Check exact freshness
      boundaries for measured and manual evidence; latest text timestamp alone cannot resolve
      contradictory evidence. Falsifier: Leave _state_for measured readings exempt from age
      checks; tripwire/measured-expiry must detect permission based on an expired measurement.
    falsified_by: >
      Leave _state_for measured readings exempt from age checks; tripwire/measured-expiry must
      detect permission based on an expired measurement.
  - id: AC2
    text: >
      Claim: Missing or invalid governing evidence blocks dependent permissions and opens a
      durable review request; only explicitly non-authorizing advisory assumptions may merely
      warn. Set: tripwire.evaluate_tripwires/check_tripwires/draft_redecisions and C
      control_decision_dependency invalidation over all governing/advisory classes and affected
      binding kinds. Completeness: Compare the assumption registry to permission and
      review-obligation rows. Remove a required reading, introduce a breach or contradiction, and
      expire evidence while another process requests a claim or publication. Kill after the
      invalidation transaction before notification; replay must preserve blocked closure and one
      version-bound review request on each required enrolled surface with no worker held for
      waiting. Falsifier: Keep UNMONITORED in the warning-only path for a governing assumption;
      tripwire/missing-governing must detect an allowed dependent operation.
    falsified_by: >
      Keep UNMONITORED in the warning-only path for a governing assumption;
      tripwire/missing-governing must detect an allowed dependent operation.
  - id: AC3
    text: >
      Claim: Tripwire review and resumption use current decision framing and shared settlement
      rather than file existence or a new good reading alone. Set:
      tripwire.draft_redecisions/_render_redecision, decision_review.bind_review and
      request.validate_record with W54 binding updates for Telegram chat, Jira, signed CLI, and
      email when enrolled. Completeness: Trigger successive breaches across decision revisions
      through real stored observations; retain prior redecision artifacts and create/reuse
      requests by exact source revision. Answer an old presentation after restart and refuse it.
      Settle a current authorized review with fresh independent evidence as the positive control,
      requiring current eligibility and explicit disposition before resumption; machine-drafted
      redecisions cannot decide themselves. Falsifier: Reuse an existing decision-ID redecision
      file after a second framing revision breaches; tripwire/revision-reopen must detect the
      missing current review obligation.
    falsified_by: >
      Reuse an existing decision-ID redecision file after a second framing revision breaches;
      tripwire/revision-reopen must detect the missing current review obligation.
required_evidence: [unit, integration]
rollback: >
  Keep affected permissions withdrawn and observations immutable; use a current authorized review
  to resolve the stop before restoring qualified observation processing.
---

## Intent

Turn failed or unproven governing assumptions into durable review obligations that remove the permissions depending on them.

## Context

Package E, W56 of PLAN-0019 revision 1. The controlling [design](../docs/design/PLAN-0019-dark-factory-design.md) and accepted A/B/C contracts govern implementation. This draft grants no implementation or activation authority.

R39, R60 and R71 require evidence-backed assumptions. The inspected tripwire treats missing readings as warnings and never expires measured readings, while redecision drafting stops at a permanent filename. The declared risk floor is critical; required approval must bind the eventual change and proof. This declaration records no approval.

## Out of scope

Automatic technical redesign, admission of remediation work, and generic monitoring infrastructure are excluded.

## Notes

D1/D2 block stored observations, atomic invalidation and publication; D3/D4 remain inherited execution prerequisites. Before ready, name each trusted source adapter, finite freshness policy and failure treatment; unavailable acquisition is an explicit blocker. Observation evidence cannot be supplied by a model assertion labeled measured. Existing condition comparators may be reused, but accepted assumption policy owns thresholds, not an untrusted reading. Map tripwire/control_assumption and inventory engine assets through W30. W54 owns binding effects and W55 independent review; this producer drives them with real observations. Preserve acquisition evidence, expiration times, mutation diffs and named failed rows without exposing channel secrets.
