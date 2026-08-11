---
schema: veldo.spec/v1
id: WARP-0411
title: Runner anti-vacuity hardening - no mechanical runner passes a declared-but-empty assertion
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The integration/contract runner (engine/scripts/runners/integration)
      fails loud with a named journey error when a journey has no interactions (an
      empty or missing interactions list), instead of returning passed=true. A
      contract journey that drives nothing asserts nothing and must not pass.
  - id: AC2
    text: The db/migration runner check_invariant (engine/scripts/runners/db)
      fails loud with a named malformed error when a declared invariant is missing
      its query or its expect_rows, instead of silently degrading to a check that
      only confirms the query runs.
  - id: AC3
    text: The db/migration runner check_budget fails loud with a named malformed
      error when a declared budget is missing its query or its max_seconds, instead
      of silently degrading to a check that only confirms the query runs.
  - id: AC4
    text: Each guard is proven non-tautological by a selftest case that passes with
      the guard present and would fail if it were removed; the shipped pass and fail
      fixtures for both runners are unaffected, and the full gate is GREEN.
required_evidence: [unit]
rollback: git revert; the change is three small guard clauses plus their selftest
  cases, no protected path, no behavior change to well-formed journeys.
---

## Intent

Close a rubber-stamp class in the reference-runner suite: a mechanical runner that
PASSES a journey which declares an assertion but supplies nothing to assert. A
verifier that passes when it should fail silently defeats VELDO's core promise, so
these gaps are worth closing even under a tight proportionality bar.

## Context

Three concrete gaps were surfaced by prior wave reviews and confirmed in the code:
the integration runner enforced assert-nothing per interaction but not for a whole
journey with an empty interactions list; the db runner's check_invariant and
check_budget silently passed when expect_rows or max_seconds was missing (the guard
was `if expect is not None` / `if limit is not None`), degrading a declared
assertion into a mere "the query runs" check. Each now fails loud with a named
error, and a selftest negative case proves the guard fires.

## Out of scope

A blanket anti-vacuity audit across the whole runner suite is deliberately NOT in scope
(proportionality). This closes only the three confirmed silent-pass gaps in the two
mechanical runners that run in the gate. The web runner's assert-nothing warning is
left out because it is a reference JS runner not exercised in the gate, so a guard
there could not be gate-proven here; it is tracked for when web runners are wired.

## Notes

Well-formed journeys are unaffected: the shipped pass fixtures already declare
expect_rows, max_seconds, and interactions, and the db fail fixture fails at
reversibility with an empty budgets list, which stays legitimate (no budget to
validate is not the same as a budget that declares nothing).
