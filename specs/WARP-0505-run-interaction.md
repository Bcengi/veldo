---
schema: veldo.spec/v1
id: WARP-0505
title: Answer, steer, and abort a running build - cooperative command inbox with safe-point handling
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0005
work: R5
plan_revision: 1
protected_paths: []
required_evidence: [unit]
acceptance_criteria:
  - id: AC1
    text: The run registry gains inbox primitives - post_command(run_id, kind, payload)
      writes an atomic command file (temp file plus rename) to commands/inbox/ with a
      kind of answer, steer, or abort and rejects an unknown kind; read_inbox returns the
      pending commands oldest-first; and ack_command moves a command to commands/acked/
      so it is processed exactly once. All are stdlib and honor the runs-root override.
  - id: AC2
    text: A running build acts on its inbox at SAFE CHECKPOINTS only - between loop steps
      and while blocked waiting on a human - through a checkpoint handler that drains the
      inbox and acts, acking each command exactly once so a drained command is never
      reprocessed on a later checkpoint.
  - id: AC3
    text: An answer to a blocked run records the answer on the run and RESUMES it
      (runlog.resume); an abort makes the owning loop stop and finish the run aborted at
      the next checkpoint (never mid-step); a steer is recorded and surfaced to the agent
      for its next turn and is treated as neither an answer nor an abort (it does not
      resume or abort). The interaction is COOPERATIVE only - the run process that owns the
      build acts; nothing external signals or preempts a process.
  - id: AC4
    text: The high-volume interaction progress (run.command) stays live-only in the run
      folder and is never added to the committed events vocabulary; resume rides the
      existing run.resumed milestone and abort the existing run.aborted milestone.
  - id: AC5
    text: A documented PROCEDURE (in the run skill) requires that an answer which changes a
      requirement or a durable decision be committed to the spec (or an ADR) before the
      build is accepted, so a chat answer never becomes hidden engineering truth. This is
      agent-instructed, not code-enforced, and is called out as such.
  - id: AC6
    text: A selftest drives the cooperative handling over a temporary runs root with a FAKE
      checkpoint loop (no live agent or backend) - posting an answer to a blocked run
      resumes it and the loop completes and the command is ack'd once (not reprocessed);
      posting an abort finishes the run aborted at the next checkpoint and stops with no
      step run; posting a steer is surfaced without resuming or aborting - and is
      non-tautological: a mutation that ignores the inbox (never resumes on an answer) or
      never aborts makes an assertion fail.
rollback: git revert; additive - inbox primitives (post_command, read_inbox, ack_command)
  added to .veldo/runlog.py, a cooperative handler and checkpoint driver added to
  .veldo/executor.py, a run_interaction entry added to both capabilities.yaml copies, a
  documented procedure added to the run skill, a selftest block, the spec, and the
  regenerated index; no protected path is touched and the run inbox is outside git history.
---

## Intent

Let a human answer, steer, or abort a running or blocked VELDO build without reading the
repo or reaching into a process. A build already streams its live state into the run
registry (R1) and is driven by the observed executor (R2); this item adds the return
channel - a per-run command inbox the human posts into and the running build drains at
its own safe checkpoints, so the loop stays in control of its own build.

## Context

Preemptive process control is explicitly out of scope (plan non-goal NG3): steering and
abort are COOPERATIVE checkpoints honored by the run process that owns the build, not
signals from the viewer. The inbox lives in the run folder R1 already creates
(commands/inbox/), outside git history, beside the live state. Command files are written
atomically and moved to commands/acked/ when processed, so each command acts exactly once
even if a checkpoint is drained more than once. An answer that unblocks a run resumes it
through the existing run.resumed milestone; an abort finishes it through run.aborted; the
per-command progress is live-only, so the committed event stream is never spammed.

## Notes

post_command / read_inbox / ack_command are the mechanical inbox on runlog;
handle_run_commands is the cooperative safe-point handler (drain, act, ack once, return a
decision) and run_checkpoint_loop is the reference driver that runs the build's units of
work and consults the handler at each checkpoint - honoring an abort by finishing aborted
and STOPPING (no further step runs, so abort lands at a checkpoint and never mid-step) and
a blocked-wait by resuming only on an answer. The requirement-change-must-commit rule is a
PROCEDURE documented in the run skill, not code enforced: a chat answer that changes a
durable decision must be written back to the spec (or an ADR) before the build is accepted.
The selftest drives all of this over a temp runs root with a fake checkpoint loop and is
mutation-proven (ignore-the-inbox and ignore-abort each turn an assertion red).
