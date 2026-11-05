---
schema: veldo.spec/v1
id: VELDO-0240
title: Owner-approved standing schedules - a scheduled conversation turn or a scheduled batch gate runs at the times the owner approved, and every schedule is listed, cancellable and recorded
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0068, VELDO-0154, VELDO-0160, VELDO-0174, VELDO-0175, VELDO-0181, VELDO-0239]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_schedule*.py"
  - ".veldo/control_schedule*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/control_conversation*.py"
  - ".veldo/control_conversation*.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/ui/src/**"
  - "scripts/suites/*_veldo_0240_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0240-owner-approved-standing-schedules.md"
  - "specs/index.md"
  - "proof/VELDO-0240/*"
behavior_bearing: true
observability:
  logs: >
    Record each schedule's proposal, approval, cancel and end with its id, kind, target, recurrence and time
    zone and the command or approval id; record each occurrence with its due time, the time it started, its
    outcome (ran, empty, missed, ended) and the turn or batch it started. Never the turn text beyond its digest.
  metrics: >
    Count schedules by kind and state, occurrences by outcome, and lateness between due time and start.
  traces: >
    Join each occurrence to its schedule and approval, and to the conversation turn or batch it started.
  error_taxonomy: >
    A schedule with no settled owner approval is missing_authority:schedule; a recurrence that cannot be read
    or names no future time is invalid_input:schedule_time; a target that is not the owner's open
    conversation or project is missing_authority:schedule_target; an approval for another subject is
    stale_subject:schedule; a due time the service was down for is missed, never run late by itself.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: no schedule runs anything until the owner approves it, and the approval binds what runs and when.
      Set: a schedule record has a kind (conversation_turn or batch_gate), a target (one of the owner's open
      conversations, or one project), a recurrence (one time, or one or more daily times on named weekdays, with
      its time zone) and, for a turn, its exact text. The owner proposes one by command (Telegram /schedule, or the UI's
      schedules screen); a turn may propose one only as a decision (VELDO-0181), never with authority. It
      becomes active only when the owner settles the approval (VELDO-0068) whose subject is the kind, target,
      recurrence and text; any change is a new proposal and a new approval. Rows: approve/required proposes a
      schedule, passes its time unapproved and requires nothing run; approve/bound changes the time after
      approval and requires the old approval refused as stale_subject:schedule.
    falsified_by: >
      Activate a schedule at its proposal, and the approve/required row must fail on an occurrence that ran.
  - id: AC2
    text: >
      Claim: each due occurrence runs once, at its time, and a missed one is recorded and told, not run late.
      Set: the service's loop sets its timer for the earliest due occurrence beside the account resets it
      waits for (VELDO-0154 AC1; this adds schedules to that timer and to the wake sources AC4 of VELDO-0154
      counts); schedules are read from the store, so a restart keeps them. At its time an occurrence starts
      once, recorded by its schedule id and due time so a second pass never starts it again; an occurrence
      whose time passed while the service was down is recorded missed and the owner is told, and the next one
      runs as usual. Rows: run/once drives a fake clock across a due time with two passes and requires one
      start; run/restart stops and starts the service before the due time and requires the start; run/missed
      requires a missed record and a message, and no start, for a time the service was down for.
    falsified_by: >
      Start every occurrence whose time has passed at service start, and the run/missed row must fail on a
      late start.
  - id: AC3
    text: >
      Claim: a scheduled turn is a turn of its conversation, and a scheduled batch gate is a batch of its
      project, each with no more authority than the owner's own command would have. Set: a conversation_turn
      occurrence appends a turn with the approved text to its conversation, marked as started by the schedule,
      run by the conversation's role as any turn (VELDO-0174); a closed conversation ends the schedule,
      recorded. A batch_gate occurrence starts a VELDO-0239 batch of the project; a batch with no reviewed unit
      is recorded empty and runs nothing; a green batch still waits for the owner's landing approval. A schedule's
      approval starts the turn or the batch gate only and approves no outside write: each outside write an
      occurrence needs is submitted as its exact request and waits for the owner's approval of that request,
      the same mechanism as any other write (ruling R4, the outside gate of VELDO-0251 and VELDO-0252), and a
      write sent without one is refused approval_required and the owner is told. A message or file the turn
      sends the owner through Veldo's own channel is not an outside write (ruling R6). Durable engine cron
      stays outward and asks (VELDO-0160 rule A). Rows: kind/turn requires the turn with the
      approved text in the conversation; kind/batch requires a batch and its gate and no landing; kind/empty
      requires an empty record and no gate.
    falsified_by: >
      Have a batch_gate occurrence land a green batch without the owner's approval, and the kind/batch row
      must fail on the trunk moved.
  - id: AC4
    text: >
      Claim: every schedule is listed, cancellable and recorded. Set: /schedules in Telegram and the UI's
      schedules screen list every active schedule with its id, kind, target, recurrence in words and next due
      time in the owner's time zone; /cancel_schedule <id> and the screen's cancel end it by the owner's
      command, so no later occurrence starts, while an occurrence already running finishes. Each proposal,
      approval, occurrence, cancel and end is one journal record, and the list reads the records. Rows:
      list/all requires both kinds listed; cancel/stops cancels before a due time and requires no start and a
      cancel record.
    falsified_by: >
      Hide a cancelled schedule from the list but keep its timer, and the cancel/stops row must fail on the
      occurrence that started.
required_evidence: [unit, integration, ui_states]
rollback: >
  Cancel every schedule by the owner's command, then revert; nothing then runs by time. Records stay as
  accepted journal records. No automatic rollback is authorized.
---

## Intent

The owner relies on work that happens at a time: the daily batch gate of each project at its own hour and
recurring checks such as a sweep run by a conversation. Veldo has no
scheduler; VELDO-0082 is a parked draft that excludes generic time scheduling, and a durable engine cron is
outward under VELDO-0160 rule A. This is the narrow part he needs: schedules he approves, of two kinds only,
each listed, cancellable and recorded.

## Context

- The loop already wakes on a timer for the earliest account reset (VELDO-0154 AC1).
- A conversation turn is appended and run in order (VELDO-0174); decisions a turn raises go through the
  owner's decision flow and carry no authority (VELDO-0181).
- A batch gate is VELDO-0239. VELDO-0245's schedule steps (a separate draft) may be shown in this list, but
  they are timed by their workflow, not by this scheduler, and add no kind here.
- A schedule is runtime state in the store, like runs and approvals, not installation configuration
  (VELDO-0253 AC1 declares no kind for schedules).

## Out of scope

Other kinds of scheduled work, schedules the factory proposes and approves by itself, catching up missed
occurrences, and the host's own crontab jobs, which stay as they are.

## What the reviewer judges

- Normal use: the owner approves a weekday 10am batch gate for a project and a 6-hourly sweep turn in a
  conversation, sees both in /schedules, and cancels one.
- Threat model: a schedule that runs without approval or after cancel; a turn that grants itself a
  schedule; a missed occurrence run hours late without the owner knowing.

## History

- 2026-11-04: drafted from the Veldo parity report, ticket T9, under the owner's decisions to move the work
  to Veldo (Telegram 39047, 39049) and that Veldo runs non-software projects (Telegram 39067). Not
  implemented; the owner approves it before it is claimed.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended under the plan consistency review (veldo-plan-consistency-review-2026-11-04.md) and the
lead's rulings (veldo-plan-rulings-2026-11-04.md), owner request Telegram 39145: a schedule's approval starts the turn or gate only and every outside write in an occurrence
needs its own approval of the exact request (A24, R4); messages to the owner through Veldo's channel are not
writes (C24, R6); VELDO-0245's steps are listed but timed by their workflow (D14); schedules stay runtime
state (R1); no project names, owner report or message ids outside History (B2, B9). Status stays ready; the
owner approves the amendments in one message. Dispositions: proof/VELDO-0236/review-dispositions-2026-11-04.md.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156).
