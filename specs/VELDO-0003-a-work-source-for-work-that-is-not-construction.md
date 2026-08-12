---
schema: veldo.spec/v1
id: VELDO-0003
title: A work source for work that is not construction - review, audit and authoring become claimable
  units the EXISTING fleet drains, with the produced artifact deciding done and never a worker's word
status: ready
risk: standard - it adds one artifact contract and one read model, and deliberately adds NO control
  loop, NO spawner and NO pacing, because all three already exist and are already governed. It is NOT
  low because it is the surface through which a pool of workers divides work, so a wrong claim answer
  means two workers doing one task or a task nobody takes. It is not high because it enforces nothing:
  no build is refused, no gate stage consults it, and an absent task directory stands the whole read
  model down
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0018
work: W2
placement: [contracts]
footprint:
  - ".veldo/tasks.py"
  - "engine/.veldo/tasks.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "scripts/suites/20_veldo_0003_task_source.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0003-a-work-source-for-work-that-is-not-construction.md"
  - "specs/index.md"
protected_paths: []
behavior_bearing: true
observability:
  logs: >
    Every refusal names the task by id and the file it was read from, and every claim answer names
    which of the four reasons applied. The read model's report says how many tasks are open, claimed,
    concluded and unclaimable, and for each unclaimable one WHY, because "no work left" and "work left
    that nobody here can do" send an operator in opposite directions.
  error_taxonomy: >
    Task-set refusals: TASK_UNREADABLE, TASK_MISSING_FIELD, TASK_KEY_UNRECOGNIZED, TASK_KIND_UNKNOWN,
    TASK_DECLARED_TWICE and TASK_PRODUCES_UNBOUND, each named separately because each is a different
    author mistake. Claim answers reuse the EXISTING ledger's vocabulary (granted, capability, claimed)
    rather than inventing a second spelling, and add CONCLUDED for a task whose product already exists.
acceptance_criteria:
  - id: AC1
    falsified_by: >
      Widen KINDS in .veldo/tasks.py to accept any string, and the assertion that a task declaring
      kind build is refused with TASK_KIND_UNKNOWN and the allowed kinds named must go red.
    text: >
      A TASK SET IS A CLOSED CONTRACT, VALIDATED THE WAY EVERY OTHER ARTIFACT HERE IS. Each task
      carries an id, a kind from a closed set, a target, and the artifact it produces. The key set is
      closed, an unknown kind is refused with the allowed kinds named, and a task id declared by two
      files is refused with BOTH files named. `build` is deliberately NOT a kind: construction already
      has a work source and a second one would be two enumerations of one set. NEGATIVE CONTROL: a
      task set differing only in a valid kind is accepted, so the refusal discriminates.
  - id: AC2
    falsified_by: >
      Read done from a task's own status field in .veldo/tasks.py instead of from the existence of its
      produced artifact, and the assertion that a task whose status says done while its product is
      absent is still OPEN must go red.
    text: >
      DONE IS THE PRODUCT EXISTING, NEVER A STATUS A WORKER WROTE. A review task concludes when its
      review exists on disk; an audit concludes when its audit does. A task declaring status done whose
      produced path is absent is still OPEN, for the same reason VELDO-0002 refuses a run's own word: a
      worker that announced success and left nothing behind is the failure this method keeps finding.
      Because a task set is an authored file, `produces` must name a path INSIDE the repository and a
      task whose produces is empty or absolute is refused with TASK_PRODUCES_UNBOUND, so no task can be
      concluded by pointing outside the tree. NEGATIVE CONTROL: the same task WITH its product on disk
      reads CONCLUDED even though its status field still says open.
  - id: AC3
    falsified_by: >
      Make claimable() skip the ledger consultation in .veldo/tasks.py and return every open task, and
      the assertion that a task held live by another worker is NOT claimable, driven through the real
      .veldo/claim.py ledger, must go red.
    text: >
      TWO WORKERS NEVER GET ONE TASK, THROUGH THE LEDGER THAT ALREADY GUARANTEES THAT. Claimability is
      answered by consulting .veldo/claim.py, the existing per-unit-lock ledger, and NOT by a second
      mechanism: a task held live by another worker is refused `claimed`, a task whose requirements
      exceed the worker's capabilities is refused `capability`, and a task whose product exists is
      refused `concluded`. DRIVEN THROUGH THE REAL LEDGER, never a stub, because the property being
      relied on is that ledger's locking and a stub would prove only that the stub agrees with itself.
      NEGATIVE CONTROL: two claims for two DIFFERENT tasks both succeed, so the refusal is arbitration
      rather than a ledger that refuses everything.
  - id: AC4
    falsified_by: >
      Add a control loop, a worker spawner or a pacing decision to .veldo/tasks.py, and the assertion
      that this module references no spawner, no sleep and no governor, and that veldo_fleet drives a
      task controller UNCHANGED, must go red.
    text: >
      IT ADDS NO SECOND FLEET. The elastic control loop, the token governor, the in-session spawner and
      the resume waiter already exist and are already governed; this item supplies only a controller
      satisfying the EXISTING FleetController contract, and the proof is that fleet.veldo_fleet drains a
      queue of tasks with no change to fleet.py at all. Asserted BOTH ways: the loop is driven to
      completion over a task queue, and this module is scanned for a spawner, a sleep or a governor
      reference and must contain none. THE CONSTRAINT IS THE POINT (PLAN-0018 NG2): a work source that
      grew its own loop would be an ungoverned second pool, which is the shape that must never exist.
  - id: AC5
    falsified_by: >
      Remove the absent-directory stand-down from the read model in .veldo/tasks.py so a repository
      with no .veldo/tasks/ raises or reports zero, and the assertion that an absent directory stands
      down with its reason named while the report keeps ONE key shape must go red.
    text: >
      ADOPTION SAFE, AND IT ENFORCES NOTHING. A repository with no .veldo/tasks/ directory stands the
      read model down and says which condition fired, never reporting zero open tasks as though it had
      looked and found none. No gate stage consults this, no build is refused because a task is open,
      and nothing here blocks a landing: a queue that could block work would make an advisory organ a
      gate, which PLAN-0018 NG3 forbids in those words. NEGATIVE CONTROL: with a task directory present
      the same report answers, so the stand-down is a measurement and not the module's only behaviour.
required_evidence: [unit]
rollback: >
  Delete .veldo/tasks.py and its suite fragment. Nothing else imports it, fleet.py is untouched by
  construction, and the claim ledger is unaware of who its units belong to, so the retreat removes one
  file and leaves every existing mechanism exactly as it was.
---

# A work source for work that is not construction

## What is actually missing, measured against what already exists

`veldo fleet N` runs an elastic pool of workers whose size the token governor paces, which stops when
its work runs out and waits rather than resuming into a limit. That loop is already work-agnostic: the
whole contract it asks of a controller is four methods, `desired`, `work_remains`, `resume_at` and
`now`. The claim ledger that stops two workers taking one unit is already generic over a unit id, and
already arbitrates the entire claim decision under one per-unit lock.

So the fleet is not the gap. **The only work source is ready specs to build.** Review, audit,
authoring, investigation and migration have no queue, which is why the nine independent reviews, eight
document audits and five plan critiques of this migration were dispatched by hand.

This item is therefore deliberately small: an artifact contract, a read model over it, and a controller
against the interface that already exists. It adds no loop and no pacing, and AC4 asserts that it did
not, because the failure mode for an item like this is growing a second ungoverned pool beside the
governed one.

## Why the product decides, and not the worker

VELDO-0002 landed the same rule for construction: the artifacts say what finished and a run's own claim
of success is exactly what must not be trusted. The same reasoning applies harder here, because a review
that concluded without producing a review is indistinguishable from a review that never ran. So a task
declares what it produces, and that path existing is what concludes it.

That also makes the queue honest under a dead session, for free: a worker that died mid-review leaves a
stale claim the ledger already ages out, and a task whose product never appeared simply becomes
claimable again. Nothing has to remember what happened.
