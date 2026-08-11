---
schema: veldo.spec/v1
id: WARP-0104
title: Regression plan mechanics - activation, owners, profiles (W4 of PLAN-0001)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0001
work: W4
human_approval: not_required
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The plan validator enforces the regression journey contract - each
      journey needs id, title, and an activation whose when is start,
      after:<work-item-spec>, or manual; after:<unknown-spec>, a malformed
      when, an owner_spec that is not a work item, and a profiles list that is
      not a subset of {per_spec, release} or is empty are all rejected.
      Unit-tested.
  - id: AC2
    text: .veldo/plan.py regression computes the active journeys for a context
      (per_spec:<SPEC> or release) - start always active, after:<X> active
      once X is shipped, manual never auto-active, and the per_spec/release
      profiles gate participation; manual journeys are surfaced separately at
      release, never silently skipped. Exercised live against PLAN-0001 and
      unit-tested for the activation function.
  - id: AC3
    text: The gate-slot wiring is documented and honest - the plan skill states
      that a repo points its journeys slot at the active per-spec suite, and
      capabilities.yaml marks the contract and computation mechanical while
      marking the per-repo gate-slot execution reference (not overclaimed as
      shipped for every repo).
  - id: AC4
    text: PLAN-0001 is upgraded to the contract as revision 3 (RJ1 gains
      owner_spec and profiles; RJ2 modelled as activation manual with
      profiles [release] so the mechanics agree with its note) and remains
      valid, with a Revisions entry recording the no-scope-change upgrade.
required_evidence: [unit, operational]
rollback: git revert; regression validation fires only on the fields it
  defines (plans without them are unaffected in shape, though PLAN-0001 now
  uses them), plan.py regression is additive, and the skill/capabilities
  changes are documentation; the 63 prior selftest cases pass within the 77.
---

## Intent

Regression stops being an afterthought and becomes a designed, computed part
of the plan. Each iteration declares up front which journeys must stay green,
when each becomes active (from the start, after a particular spec ships, or
only on a manual trigger), who owns it, and whether it runs per-spec, at
release, or both. The layer then computes the active suite for any build
context, so the gate runs exactly the regression the plan designed - not a
pile accumulated at random.

## Context

W4 of PLAN-0001, depends only on W1 (shipped). Complements W2's authoring
skill with the regression half of a plan. Run-time integration of the
context bundle is W3; this spec provides the regression computation that W3
and a repo's gate consume. The veldo repo has no user interface, so its own
journeys slot stays na; the mechanism is validated and computed here and
demonstrated against PLAN-0001, and wired into the gate by consuming repos.

## Out of scope

Executing browser or device journeys (W5 web runner, W7 mobile runner). The
run-time context bundle and dependency refusal (W3).
