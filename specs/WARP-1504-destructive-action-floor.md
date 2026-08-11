---
schema: veldo.spec/v1
id: WARP-1504
title: The destructive-action floor - deleting a database is not the same act as adding a DNS record,
  and an unclassified resource kind counts as stateful until somebody says otherwise
status: shipped
risk: standard - a pure classifier over a plan that delegates the key check to the shipped two-key
  module. It is not low because a classifier wrong in the permissive direction lets a stateful
  deletion through the floor, and that is the one mistake here with no undo.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W4
depends_on: [WARP-1502]
placement: [enforcement]
footprint:
  - ".veldo/substrate_floor.py"
  - "engine/.veldo/substrate_floor.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1504-destructive-action-floor.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THREE TIERS, CLASSIFIED FROM WHAT THE PLAN DESTROYS. `standard` when nothing existing is
      destroyed; `high` when a stateless resource is deleted or replaced, which re-applying the
      declaration recovers; `critical` when a STATEFUL one is, which it does not. A selftest drives
      all three from real plans rather than asserting the constant.
  - id: AC2
    text: >
      AN UNCLASSIFIED KIND IS STATEFUL, and this asymmetry is the safety property. Statefulness is
      read from a declared `STATELESS_KINDS` list, so a resource type somebody adds next year and
      forgets to classify gets the CRITICAL treatment rather than sliding under the floor. Deriving
      it as "not in STATEFUL_KINDS" would invert exactly that, and the module says so. A selftest
      drives an invented kind to critical.
  - id: AC3
    text: >
      A DESTRUCTIVE PLAN NEEDS BOTH KEYS, BOUND TO THAT EXACT PLAN. Either key alone refuses by its
      own name, and a key bound to a different digest refuses as foreign. The CONTROL sits beside
      them: both valid keys authorise, so the refusals are the rule and not a broken fixture.
  - id: AC4
    text: >
      NO SECOND TWO-KEY IMPLEMENTATION. The keys are judged by `.veldo/two_key.py`, called exactly as
      the production executor calls it, because a second implementation of "two humans agreed" is a
      second thing to get subtly wrong and a second thing for an attacker to choose between. This
      module decides WHICH plans need the discipline and never re-decides what it IS. A selftest
      asserts the refusal names come from that module's own taxonomy.
  - id: AC5
    text: >
      IT DOES NOT PREVENT DESTRUCTION AND SAYS SO. It makes destruction a decision somebody made on
      the record, bound to an exact plan digest, with two independent humans behind it. A floor that
      made deletion impossible would simply be routed around, and a module that implied otherwise
      would be lying about what it buys.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It is a pure classifier, reads nothing, writes nothing,
  runs at no gate stage yet and changes no behaviour.
---

## Outcome

Deleting a database and adding a DNS record are not the same act, and a method that treats them
alike is either too slow for the second or too dangerous for the first. So the plan is classified by
what it destroys, and only the destructive part carries the weight.

## The asymmetry that is the whole point

Statefulness is read from a declared list of what is definitively STATELESS. Anything else - a kind
nobody has classified, a type added next year, a typo - counts as stateful and lands at critical.

The obvious alternative, deriving it as "not in `STATEFUL_KINDS`", reads identically and behaves in
exactly the opposite direction: an unclassified kind would come out stateless and slide under the
floor. That is a one-line difference with an unrecoverable failure mode, which is why the module
spells out why it is written the way it is.

## Reusing the discipline rather than restating it

The keys are checked by the same `two_key.py` the production responder uses, called the same way.
A second implementation of "two humans agreed" is a second thing to get subtly wrong, and worse, a
second thing an attacker can pick between. This module answers only WHICH changes need it.

## What it is not

It does not prevent destruction. It makes destruction attributable: a decision somebody made, bound
to an exact plan, with two independent humans behind it. A floor that made deletion impossible
would be routed around within a week, and then there would be no record at all.
