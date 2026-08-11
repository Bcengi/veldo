---
schema: veldo.spec/v1
id: WARP-1507
title: Ephemeral environments that are provably gone - a destroy call returning success is not a
  teardown, and the residue check is the half that matters
status: shipped
risk: standard - a lifecycle over a fake provider that reaches nothing. It is not low because an
  environment believed torn down and actually still running is a silent, permanent cost and attack
  surface that nobody looks for, since nobody inspects a thing that stopped existing.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0015
work: W7
depends_on: [WARP-1501]
placement: [contracts]
footprint:
  - ".veldo/substrate_ephemeral.py"
  - "engine/.veldo/substrate_ephemeral.py"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1507-ephemeral-environments.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      TEARDOWN IS VERIFIED AGAINST THE PROVIDER'S LEDGER, NEVER ASSUMED FROM A RETURN CODE. After
      destroy, the provider is asked what it still holds, and anything left is named RESIDUE resource
      by resource. A selftest drives a provider that returns success while keeping an object store -
      the way real providers leave a disk behind when the instance is deleted - and requires the
      state `leaked` rather than `torn_down`.
  - id: AC2
    text: >
      THE ENVIRONMENT ID IS DERIVED FROM THE CHANGE, NOT MINTED. Creating twice for one change gives
      ONE environment and adopts what exists, so a retry after a crash cannot double the bill and
      orphan the first attempt with nobody looking for it. A random id would make idempotence
      untestable, which is the same thing as untrue.
  - id: AC3
    text: >
      A LEAK IS VISIBLE ON THE EVENT STREAM, not only in the terminal of whoever ran the teardown. A
      clean lifecycle emits created then done; a leaked one emits blocked and says how many resources
      survived, so the failure lands in the same log as everything else.
  - id: AC4
    text: >
      THE SHIPPED PROVIDER IS FAKE AND REACHES NOTHING (D5). Real provisioning stays behind
      per-system human-approved wiring. The fake keeps a ledger in memory and takes a `leaks`
      argument, so the residue check is proven against a provider that misbehaves the way real ones
      do rather than a perfect one. A lifecycle whose only tested path needs real infrastructure is
      a lifecycle nobody tests.
  - id: AC5
    text: >
      RESIDUE IS NAMED, NOT COUNTED. "Teardown incomplete" tells an operator nothing; "the object
      store `data-vol` is still there" tells them what to go and delete. The detail line says
      explicitly that a success code is not a teardown, so the next reader inherits the reasoning.
required_evidence: [unit]
rollback: >
  Delete the module and its capability entry. It reaches nothing, writes no state and runs at no gate
  stage.
---

## Outcome

A per-change environment is worth having only if it reliably disappears. One that *usually* tears
down is a slow leak of money and attack surface, and the leak is invisible precisely because nobody
inspects a thing that was supposed to stop existing.

So the interesting half of this module is not create. It is the residue check.

## Why a return code is not evidence

`destroy` returning success means the call was accepted, not that the resources are gone. Deleting a
compute instance commonly leaves its disk. Deleting a database commonly leaves its backups. Both
return success. The only honest way to know is to ask the provider what it still holds, so that is
what `teardown` does, and it reports what survived by name.

The fake provider takes a `leaks` argument specifically so this is proven against a provider that
misbehaves the way real ones do. A residue check tested only against a perfect provider proves
nothing about the case it exists for.

## Why the id is derived

Creating twice for one change must yield one environment. A minted id would make a crashed retry
create a second environment and orphan the first, which is the leak this module is about, arriving
through the front door.
