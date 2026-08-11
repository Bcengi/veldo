---
schema: veldo.spec/v1
id: WARP-0403
title: Lessons store - capture failure modes and surface the relevant ones into review (X3 of PLAN-0004)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0004
work: X3
plan_revision: 3
human_approval: not_required
protected_paths: []
required_evidence: [unit, operational]
acceptance_criteria:
  - id: AC1
    text: A stdlib module .veldo/lessons.py ships an append-only lesson store.
      add(lesson) validates a lesson envelope (schema veldo.lesson/v1, id,
      created_at, category, scope, text, optional source) and appends it as one
      JSON line to .veldo/lessons.jsonl. The category is drawn from a fixed
      vocabulary (bug_class, regression, review_finding, emergency). add rejects
      an unknown category, an empty or missing text, and a malformed scope as a
      named LessonError (a ValueError subclass), and stores nothing when it
      rejects, so a bad lesson is loud, never silently filed.
  - id: AC2
    text: relevant(context) returns only the lessons whose scope matches the
      context, most-recent-first, so an unrelated lesson is not surfaced. A scope
      is exactly one of a path glob (matched against the context touched paths)
      or a plan-or-spec tag (matched against the context plan id or its tags).
      An empty store, and a context that matches nothing, both return the empty
      list - relevant() filters, it does not pass everything through.
      scope_matches(scope, context) is a pure predicate exposed for direct test,
      and case is significant so matching is deterministic across platforms.
  - id: AC3
    text: Surfacing is a review-skill procedure, not a mechanism.
      packs/claude/skills/review/SKILL.md instructs the reviewer to compute the change
      context (touched paths, plan id, spec tags), include the relevant(context)
      output in what it checks so a failure mode that broke once is re-checked on
      any change touching the same scope, and record a review.failed finding as a
      new lesson. The instruction states plainly that the store and relevant()
      are mechanical while deciding the context and writing the lesson text are
      agent judgment.
  - id: AC4
    text: Capabilities coverage is honest and complete. Both .veldo/capabilities.yaml
      and engine/.veldo/capabilities.yaml carry, byte-identically, a
      lessons_store entry (status mechanical, home .veldo/lessons.py) and a
      lessons_surfacing entry (status procedure, home skills/review), each with a
      status drawn from the manifest vocabulary. mechanical is honest because the
      store and relevant() are stdlib and run end to end in the gate here;
      procedure is honest because the surfacing into the review prompt is
      skill-instructed and not transactionally enforced.
  - id: AC5
    text: The control logic is gate-tested with no external surface. The selftest
      (CHECK_unit) imports .veldo/lessons.py and drives add and relevant over a
      crafted temporary store, asserting a matching lesson is returned, an
      unrelated path lesson and a tag lesson are EXCLUDED from a path-only
      context, an empty store returns [], a context that matches nothing returns
      [], most-recent-first ordering holds across two matches, and every
      malformed lesson (unknown category, empty text, missing text, two-key
      scope, non-dict scope, empty scope value, unknown scope key) is rejected as
      a named LessonError and not stored. The unrelated-excluded assertions fail
      if relevant() were mutated to return every lesson, so the filter cannot
      rubber-stamp.
  - id: AC6
    text: The deliverable is generic (zero company, product, or person names and
      zero absolute host paths in the module, the skill edit, the capabilities
      entries, and this spec beyond the standard owner field) and hygienic (ASCII
      only, no em or en dash, no double hyphen). The specs index regenerates to
      include this spec, and the full gate (lint, unit, generated, docs, template
      sync, secret scan, contract validation) stays green with every prior
      selftest case still passing.
rollback: git revert; X3 is additive - a stdlib module .veldo/lessons.py, its
  seeded lessons.jsonl, a selftest block, two capabilities entries in both
  manifest copies, a review-skill paragraph, and this spec. It touches no
  protected path, no synced core (validate.py, policy_check.py, update_index.py,
  veldo-guard.sh), and adds no new required CHECK_ slot, so reverting removes the
  store and its unit block with no effect on any running gate; prior selftest
  cases are unchanged.
---

## Intent

PLAN-0004 turns VELDO into an executable system. Feature F4 (adoption) covers the
last mile of the method actually being lived across iterations, and the most
valuable thing to carry across iterations is what broke. A team that fixes a bug
class or a regression once and never records it re-learns it the hard way. X3
gives VELDO a durable, cross-iteration memory of failure: a small append-only
store of lessons and a way to put ONLY the relevant ones in front of the
reviewer of the next change, so what broke once is checked next time and an
unrelated lesson never buries the one that matters.

## Context

X3 of PLAN-0004, feature F4, depends on nothing (order 30, alongside the other
adoption work). It follows the shipped platform pattern: a stdlib module under
.veldo/ (like events.py and metrics.py), no third-party dependency, control logic
gate-tested in the unit slot with no live surface. The store is mechanical (the
envelope validation and the scope-matched retrieval run in the gate here); the
surfacing into the review prompt is a procedure, added to the review skill,
because putting a lesson in front of a reviewer and writing a new lesson from a
finding are agent judgment, not a transaction the plugin can enforce. This is
the same honest split the manifest already draws for human_minutes_events and
fresh_context_review.

## Out of scope

Auto-classifying or de-duplicating lessons, scoring their relevance beyond a
scope match, or expiring them - the store is deliberately a flat append-only log
with an exact scope filter, proportionate to the need and no heavier. Enforcing
that a reviewer actually consulted the surfaced lessons (that is procedure, not a
gate). A UI or a dashboard over the store (X4 owns metrics rendering). Wiring the
executor (X1) to emit lessons automatically - the store and its CLI are the
seam; automated emission is a later, additive caller.

## Notes

Why the store is mechanical and the surfacing is procedure: add() and relevant()
are pure enough to run end to end in the gate over a crafted store with no
network, no model, and no product surface, so their status is mechanical and the
selftest proves it. Putting the relevant lessons into a review prompt, and
distilling a failed verdict into a new lesson, are things an agent does by
instruction; claiming them as mechanical would overclaim, so lessons_surfacing
is procedure, homed in the review skill.

Why relevant() is proven adversarially: the whole value of the store is that it
surfaces the relevant lesson and NOT the unrelated one, so the selftest adds a
lesson scoped to one path glob and another scoped to a different glob, drives a
context that touches only the first, and asserts the second is excluded. A
mutation that returned every lesson (the classic rubber-stamp for a filter)
fails those exclusion assertions. The malformed-lesson cases assert that a bad
lesson raises a named LessonError and that the store size is unchanged after the
attempt, so a validator that silently accepted garbage would turn the gate red.

The reviewer should confirm by rerunning the selftest and the standalone CLI:
(1) add then relevant over a temp store surfaces the match and excludes the rest;
(2) an empty store and a no-match context both return []; (3) each malformed
shape is rejected as a named error and nothing is stored; (4) the capabilities
entries are byte-identical across both manifest copies and their statuses are
honest; (5) the docs, secret, lint, and template-sync gates stay green.
