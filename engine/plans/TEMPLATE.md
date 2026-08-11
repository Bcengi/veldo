---
schema: veldo.plan/v1
id: PLAN-0000
title: One line: the product increment this plan delivers
kind: iteration            # iteration | mvp | release
status: draft              # draft -> ready -> in_progress -> released -> closed
revision: 1                # bump on any scope change after approval; stale
                           # revisions invalidate dependent context
owner: who-answers-for-this
# approved_by / approved_at: required the moment status leaves draft.
# A plan is approved by a human, on the record, or it is not approved.

outcomes:                  # what becomes TRUE for users, each measurable
  - id: O1
    becomes_true: State the observable change in the product, not the work.
    measure: How anyone verifies it happened.

non_goals:                 # what this plan deliberately does not do
  - id: NG1
    text: Named exclusions kill scope drift before it starts.

constraints:               # cross-cutting rules every work item inherits
  - id: C1
    text: Budgets, invariants, platform rules that bind all specs below.

feature_tree:              # the decomposition: features, not tasks
  - id: F1
    title: A capability a user can name
    outcome_refs: [O1]

work:                      # the ordered DAG; every spec binds back via
                           # 'plan:' and 'work:' in its front matter
  - item: W1
    spec: VELDO-0000        # the spec id this item becomes
    title: Small, independently provable, one review in one sitting
    feature_refs: [F1]
    depends_on: []         # spec ids; [] is a declaration, absence is an error
    order: 10

regression:                # designed up front, not accumulated by accident
  journeys:
    - id: RJ1
      title: The journey that must stay green across every item of this plan
      activation: {when: start}   # start | after:<spec-id>
      suite: where it runs

release:
  milestone: What done is called
  mode: continuous         # continuous (merge as green) | coordinated (cut together)
  require_all_work_shipped: true
  require_full_regression: true
  rollback: How the increment retreats if observation says so
  observation:
    duration: what watching it in production means here

open_decisions:            # every decision names what it blocks; [] means
                           # nothing waits and work proceeds around it
  - id: D1
    text: The question, who answers it, and by when it matters.
    blocks: []
---

## Intent

Two or three paragraphs of the holistic view: why this increment, for whom,
and what the product is afterward. This is the context bundle every spec
pulled from this plan inherits, so write it for the agent who will see one
work item at a time.

## Ordered delivery rationale

Why the DAG has this shape: what genuinely blocks what, what is deliberately
parallel, and what the frontier should look like at each stage.
