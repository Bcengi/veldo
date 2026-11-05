---
schema: veldo.spec/v1
id: VELDO-0245
title: A schedule step runs the next step at the time the owner approved, and a default social post definition proves a new kind of work is a definition, not code
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0068, VELDO-0132, VELDO-0154, VELDO-0240, VELDO-0241, VELDO-0243, VELDO-0244, VELDO-0249, VELDO-0251, VELDO-0252, VELDO-0253]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/installation_template/workflows/social_post.json"
  - ".veldo/installation_template/workflows/social_post.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0245_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0245-a-schedule-step-and-a-social-post-definition.md"
  - "specs/index.md"
  - "proof/VELDO-0245/*"
behavior_bearing: true
observability:
  logs: >
    A schedule records the unit, the node, the approved time with its time zone, the approval id, the wake
    the service set, the time the next step actually started and any cancel with the owner's command id.
  metrics: >
    Count schedules pending, run, cancelled and missed; lateness between the approved time and the start.
  traces: >
    Join each scheduled run to its approval and to the step it started.
  error_taxonomy: >
    Keep VELDO-0132's names. A time not covered by an approval is missing_authority:schedule_time; a time in
    the past at approval is invalid_input:schedule_time; a wake that finds the unit cancelled ends with no
    step; a service down at the due time records missed and asks the owner, never running late by itself.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the schedule step holds the unit until the approved time, then the next step runs once. Set:
      the time is part of the approval's subject, so a changed time needs a new approval; that approval is
      submitted to and given through the approval service (VELDO-0252), the same mechanism as every
      workflow approval node, and confers no write approval beyond what it names: each outside write the
      next step makes is the exact request or release the owner approved, matched by the outside gate's
      check or performed by the control plane's executor (VELDO-0244); the hold is a one-time schedule in the VELDO-0240 schedule store, of a kind this spec adds (workflow_step, target
      the unit and node, approved by the workflow's approval step rather than a /schedule command), so it
      uses VELDO-0240's timer, its once-only start record, its missed record and its list and cancel, and
      there is no second store, timer or list; nothing runs before the time; at the time the next node is
      offered exactly once; a due time the service was down for is recorded missed and put to the owner.
    falsified_by: >
      Offer the publish node when the approval settles instead of at the approved time; the hold-until row
      must fail.
  - id: AC2
    text: >
      Claim: the default `social post` definition is data only and runs end to end. Set: the definition
      (draft copy, generate image under its spend approval, review, owner approval naming the time, the
      channel and the publish, schedule, publish) is one file of the installation template (VELDO-0253),
      naming its channel generically, using only kinds registered by VELDO-0241 to VELDO-0244 and this spec; adding it changes no engine module, and no engine
      module names a kind of work. It runs on a fixture outside service through publish and the post's id is
      read back.
    falsified_by: >
      Add a branch in the Line that tests for the social post kind; the no-kind-specific-code row must fail.
required_evidence: [unit, integration]
rollback: >
  Revert the change; the schedule kind is unregistered, pending schedules end with no step and the `social
  post` definition stays in the installation repository unused. A later installation commit that still
  holds a definition using the schedule kind is refused as a whole (VELDO-0253 AC1) until that file is
  changed. No automatic rollback, retry or recovery is authorized.
---

## Intent

Some work has to happen at a chosen time. A schedule step waits for the time the owner approved, and the
social post definition shows the point of VELDO-0241: a whole new kind of work arrives as a definition,
with no new code.

## Context

The owner (2026-11-04), citing social posts as the example of a more complex process that should be
configured, not hardcoded; NG2 and NG3 were lifted (PLAN-0019 amended 2026-11-04), so a post is published
only on the owner's approval of that post. The standing schedules spec is VELDO-0240; this step adds no
schedule store, timer or list of its own: its hold is a one-time schedule of kind workflow_step in
VELDO-0240's store (AC1), listed and cancelled there. Recurring schedules (a post every Monday) belong to
that spec, not this one.

## Out of scope

Recurring and standing schedules; scheduled conversation turns and batch gates (T9). Choosing posting
times. Social channel analytics.

## What the reviewer judges

- Normal use: copy is drafted, an image is made on its own spend approval, both are reviewed, the owner
  approves "post this to channel X at 09:00 Tuesday", the unit waits, and at 09:00 the publish step posts it
  and reads the post back.
- Threat model: a publish before the approved time or at a time the owner never approved; a schedule that runs
  twice after a restart; a cancel that does not stop it; a kind of work that sneaks in as code.
- Out of review scope (filed, not blocking): unlikely edge cases (the owner's standing ruling); clock skew
  beyond the host clock.

## Notes

Schedule is not outward; the publish after it is, so VELDO-0241's rule puts the owner's approval before
both, and the approval names the time.

## History

2026-11-04: new draft under owner Telegram 39069 to 39071 (process as workflow; social posts configured,
not hardcoded) and 39067 (NG2 and NG3). Reconciled with writer A's T9 by reuse, not duplication.
Standalone.

2026-11-04: the lead made the schedule step reuse VELDO-0240's schedule store, timer, once-only and missed
records, list and cancel (a one-time schedule of kind workflow_step), so Veldo has one scheduler, not two.
Acceptance criteria otherwise unchanged.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended under the plan consistency review (owner Telegram 39145; research/veldo-plan-consistency-review-2026-11-04.md, findings A23, A24, D8, D14, E4, E5) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md, R1, R3, R4): the schedule's approval goes through the approval service and confers no write approval beyond what it names; the default social post definition ships in the installation template with a generic channel; definitions stay in the installation repository on rollback; Context states the one schedule store; depends on VELDO-0249, VELDO-0251, VELDO-0252 and VELDO-0253. Status stays ready.
