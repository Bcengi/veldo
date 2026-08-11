---
schema: veldo.spec/v1
id: WARP-0407
title: Release and rollback automation (reference) - X7 of PLAN-0004
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0004
work: X7
plan_revision: 3
human_approval: not_required
protected_paths: []
required_evidence: [unit, operational]
acceptance_criteria:
  - id: AC1
    text: A release-automation module ships at .veldo/release.py. It models a
      staged rollout as an ordered ReleasePlan of stages (for example canary,
      then partial, then full), each stage carrying a traffic percentage, a set
      of feature flags to enable or disable, and a health gate (a per-stage
      health callable, or the deploy surface's health check for the stage). The
      deploy surface is a seam, Deployer, exposing deploy(stage), set_flag(name,
      value), health(stage), and rollback(to), so the control logic is surface
      agnostic. A malformed plan (no stages, duplicate stage names, a baseline
      that collides with a stage) and a malformed stage (an out-of-range
      percent, an empty name) fail loud, never accepted.
  - id: AC2
    text: The runner roll_out(plan, deployer) drives the rollout and promotes a
      stage only when its health gate passes. Health is a real observation of
      the seam for every stage, never assumed. A healthy rollout promotes every
      stage in order, sets each stage's feature flags on the deployer, and ends
      at the final stage with ok true and no rollback.
  - id: AC3
    text: On the first stage whose health gate FAILS the runner halts: it does
      NOT promote the failing stage, it executes a rollback to the last-good
      stage, and it reports the halt (ok false, halted_at names the failing
      stage, rolled_back_to names the recovery target). When nothing was
      promoted the last-good stage is the plan baseline, so a canary failure is
      a full rollback to baseline; when an earlier stage was promoted the
      rollback returns to that last-good stage, not all the way to baseline.
  - id: AC4
    text: The rollback is EXECUTABLE, not merely logged - it drives the deploy
      surface (deployer.rollback and set_flag calls that a fake deployer records
      as real actions), it is idempotent (execute_rollback to the same target
      re-asserts the same observed state), and it is observable (the result and
      the deployer's recorded actions reflect it). Feature flags are set and
      cleared per stage: on rollback the failed stage's flags are reconciled
      back to the last-good configuration (a flag not in that configuration is
      disabled, a good flag is driven to its good value).
  - id: AC5
    text: The live reference deployer, LiveDeployer, ships with no real deploy
      surface and FAILS LOUD on every operation (deploy, set_flag, health,
      rollback) rather than silently no-op, so a rollout against a missing
      surface refuses to run instead of pretending a deployment or a rollback
      happened. An adopting repo wires a real deploy target, feature-flag store,
      and health endpoint through the seam.
  - id: AC6
    text: The control logic is unit-tested in scripts/selftest.py with a fake
      deployer and no live surface: a healthy canary promotes through to full, an
      unhealthy canary halts and rolls back to baseline (asserted, the result
      reflects failure), a mid-stage failure rolls back to the last-good stage,
      feature flags are set and cleared per stage, and the rollback is
      idempotent. Non-tautology is proven: a promote-anyway mutant that ignores
      the health gate FAILS the gate_respected invariant while the real runner
      passes it, so the health-gate assertion has teeth. The LiveDeployer is
      shown to fail loud without a surface. All prior selftest cases keep
      passing and the gate stays green.
  - id: AC7
    text: The deliverable is generic (zero company, product, or person names and
      zero absolute host paths in the module, the selftest block, the
      capabilities note, and this spec beyond the standard owner field) and
      hygienic (ASCII only, no em or en dash, no double hyphen). Both
      .veldo/capabilities.yaml and engine/.veldo/capabilities.yaml
      (kept byte-identical) declare release_rollback_automation status reference
      (a real rollout needs a deploy surface the home repo lacks; the live path
      fails loud and the control logic is fake-tested), never mechanical. The
      specs index regenerates to include this spec and the full gate (lint,
      unit, generated, docs, template sync, secret scan, contract validation)
      stays green.
---

## Intent

PLAN-0004 turns VELDO from a method plus runners into an executable system.
Feature F3 is the operational platform: metrics, budgets, ephemeral
environments, and this work item, X7, release and rollback automation. The
outcome that should become true is that a change can be rolled out in stages
behind health gates and pulled back safely the moment a stage is unhealthy,
without a human hand-driving each step. A rollout is only trustworthy if a
failed health gate cannot promote and if the rollback actually runs against the
deploy surface, so the control logic here promotes a stage solely on an observed
healthy gate and executes an idempotent rollback to the last-good stage on the
first failure, reconciling feature flags as it goes.

## Context

X7 of PLAN-0004, feature F3 (operational platform), pulled against plan revision
3, with no dependency. It follows the shipped-capability pattern: a stdlib
module under .veldo/ for a core capability, control logic gate-tested in the unit
slot with no live surface, and an honest capability manifest entry in both the
repository instance and the template canon. The deploy surface is a seam
(Deployer) so the same control logic serves any target: a real deployer drives a
platform, the reference LiveDeployer fails loud until wired, and a fake deployer
lets the gate prove the promotion and rollback logic deterministically. A stage
carries a traffic percentage and feature-flag hooks so a rollout can widen
exposure and flip flags per stage, and a health gate so promotion is earned, not
assumed.

## Out of scope

Any specific deploy technology, traffic router, or feature-flag vendor: those
are the adopting repo's, reached through the Deployer seam. Progressive-delivery
analysis beyond a boolean health gate (statistical canary scoring, automated
bake windows) - the reference gate is a health observation the adopting repo
supplies. A live rollout in the home gate, because the veldo repo has no deploy
target of its own; the honest evidence is the fake-deployer control-logic test.
This spec adds no enforcer and touches no protected path.

## Notes

Why reference (not mechanical): a real rollout needs a deploy target, a
feature-flag store, and a health endpoint the veldo home repo does not have, so
the honest evidence is the fake-deployer unit test, not a live run. The live
reference (LiveDeployer) fails loud on every operation without a configured
surface, so the live path cannot pass vacuously. required_evidence is [unit,
operational]: unit is the selftest control-logic block, operational is the
end-to-end drive of a healthy rollout, an unhealthy-canary rollback to baseline,
and a mid-stage rollback to the last-good stage through the fake deployer.
capabilities.yaml states status reference, never mechanical.

The adversarial properties a reviewer should confirm by rerunning the selftest:
(1) a healthy canary promotes through to full and sets every stage's flags; (2)
an unhealthy canary halts with ok false and rolls back to baseline (a full
rollback), and a mid-stage failure rolls back only to the last-good stage; (3)
the rollback drives the deployer (recorded rollback and set_flag calls), is
idempotent, and reconciles the failed stage's flags back to the last-good
configuration; (4) a promote-anyway mutant that ignores the health gate fails
the gate_respected invariant while the real runner passes it, proving the
assertion is not a rubber stamp; (5) LiveDeployer fails loud on deploy, set_flag,
health, and rollback without a surface.
