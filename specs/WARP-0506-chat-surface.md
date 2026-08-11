---
schema: veldo.spec/v1
id: WARP-0506
title: Chat surface wiring - veldo answer/steer/abort CLI over the run inbox for an assistant
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0005
work: R6
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A CLI exposes veldo answer <run-id> <text>, veldo steer <run-id> <text>, and
      veldo abort <run-id> [reason], each posting the matching command (answer, steer,
      abort) to that run's inbox via runlog.post_command and printing the command id.
      An unknown run-id or an empty required text fails loud with a nonzero exit, and
      the payload posted is exactly the text the human supplied.
  - id: AC2
    text: The commands the CLI posts are the same ones the R5 run loop consumes at a
      safe checkpoint - an answer resumes a blocked run, an abort stops it aborted at
      the next checkpoint, a steer is recorded - so the CLI is a front door over the
      existing inbox, not a second path (it calls runlog.post_command, it does not
      reimplement inbox writing or command handling).
  - id: AC3
    text: The chat-surface procedure is documented for an assistant (for example one
      on Telegram): read veldo status --json to see the live runs and any blocked
      question, then issue veldo answer/steer/abort for a run. The rule that an answer
      changing a requirement or durable decision must be committed to the spec (never
      left as hidden chat truth) is restated where the procedure lives.
  - id: AC4
    text: A selftest drives the CLI over a temporary runs root - answer, steer, and
      abort each land the correct kind and exact payload in the target run's inbox,
      and an unknown command kind or a missing run is rejected - and is
      non-tautological: a mutation that posts the wrong kind or drops the payload
      makes an assertion fail. The CLI writes only through runlog (no repo/events
      writes of its own).
required_evidence: [unit]
rollback: git revert; additive - a .veldo/runcmd.py CLI over runlog.post_command, a
  chat-surface procedure note in the run skill, a selftest block, one capability
  entry (both copies), and the spec; no protected path.
---

## Intent

Close the Run Lens loop for a human who lives in a chat surface, not a terminal: a
thin CLI (veldo answer/steer/abort) over the R5 run inbox, plus the documented
procedure for an assistant to watch (veldo status --json) and act. This is the front
door that lets you unblock or stop a running build from Telegram.

## Context

R5 (WARP-0505) built the inbox primitives (runlog.post_command/read_inbox/
ack_command) and the cooperative safe-point handling in the run loop. This item adds
only the human-facing CLI over post_command and the assistant procedure; it
reimplements nothing. The assistant already exists (the Telegram surface), so there
is no new service - just the commands it calls and the documented way it uses them.

## Notes

The CLI posts a plain-text payload exactly as supplied (matching how R5's handler
reads it). The assistant deciding when to answer, steer, or abort is agent judgment
(procedure); the CLI that posts to the inbox is mechanical and gate-tested. The
requirement-change-must-commit rule is restated with the procedure so a chat answer
never becomes hidden engineering truth.
