---
description: Run the whole Veldo pipeline for one ready specification - implement, gate, proof, review - and report merge readiness. The normal way to execute a spec.
---

Run the full pipeline for: $ARGUMENTS

This starts a RUN: it allocates a run in the WARP-0501 registry (a per-run folder
under the git common dir, outside git history) and drives the spec through the
executor with the run observer ON, so the build streams its live progress - which
loop step it is on, a heartbeat while it works, and any blocked question - into
the registry while the agent still builds and the human still approves. The
durable milestones (run.started, run.blocked, run.resumed, run.done, run.aborted)
and the high-volume per-step and heartbeat progress land in the run folder's
live.jsonl, never the committed events.jsonl. Surface the run id when you start,
so a reader (veldo status / veldo watch) can follow along; report it again with the
receipt at the end. The thin driver is `veldo_run(spec_id, hooks)` in
`.veldo/executor.py`: it allocates the run, wires the RunLogObserver, drives the
executor, and hands back the receipt plus the run id. Wire the build, review, and
approve hooks to the agent and human steps below - the driver fabricates none of
them.

1. Resolve the specification. It must be `ready`; if it is a draft, stop and
   say what is unresolved instead of guessing.
1a. If it is a PLANNED spec (lane: planned, with plan and work), enforce the
   plan before building: run `python3 .veldo/plan.py run-check <plan> <SPEC>`.
   If it REFUSES (a dependency is unshipped, or the plan has revised since the
   spec was pulled so its context is stale), STOP - do not build out of order
   or against stale context; pull it again or ship its dependencies first.
   Then load the plan context bundle so the agent building the part sees the
   whole: `python3 .veldo/plan.py bundle <plan> <SPEC>`. Record the plan hash
   (`python3 .veldo/plan.py hash <plan>`) to include in the proof, binding the
   change to the exact plan state it was built against.
2. Dispatch the veldo-implementer to build the smallest complete change with
   meaningful tests.
3. Run /veldo:gate until green. Fix defects, never checks.
4. Run /veldo:proof to produce the manifest for the final state.
5. Run /veldo:review for the fresh-context verdict. On fail, return to
   implementation; after two failed cycles, stop and bring in the human.
6. Evaluate the merge policy: if protected paths or human lanes apply, list
   exactly which approvals are missing and from whom; otherwise report
   ready-to-merge (and merge only if the human has said to).

Finish with the receipt: criteria proven, gate result, verdict, and the one
thing (if any) that awaits a human. The six underlying skills remain
available for inspection and debugging; this command is the normal path.

## Answering, steering, and aborting a running build

While a run is going, a human can answer a blocked question, steer the build,
or abort it - COOPERATIVELY, through the run inbox, never by killing a process.
A command is posted with `runlog.post_command(run_id, kind, payload)` (kind is
answer, steer, or abort) and the running build drains its inbox at SAFE
CHECKPOINTS only (between loop steps, and while it is blocked waiting on a
human) via `handle_run_commands` / `run_checkpoint_loop` in `.veldo/executor.py`:

- answer: a blocked run records the answer and RESUMES.
- abort: the loop stops and finishes the run aborted at the next checkpoint
  (never mid-step); nothing external signals or preempts the process.
- steer: recorded and surfaced to you for your next turn - it is not an answer
  and does not resume or abort.

Each command is ack'd exactly once, so it is never reprocessed.

THE RULE - answers do not become hidden truth. If an answer you deliver through
the inbox CHANGES A REQUIREMENT or a durable decision (not just an
implementation detail), you MUST commit that change to the specification (or
record it as an ADR) before the build is accepted. A chat answer that alters
what the system must do, left only in the run log, is hidden engineering truth:
the next reader sees a spec that no longer matches the build. Write it back to
the spec first, then let the build proceed. This is a PROCEDURE you follow, not
something the code enforces - the inbox and the resume are mechanical; deciding
that an answer changed a requirement, and committing it, is your judgment.

The executor (.veldo/executor.py) drives this sequence so you approve and steer
rather than hand-drive every step. It sequences the steps, runs the mechanical
ones itself (the gate over scripts/verify.sh, assembling and validating the
proof, emitting the loop events including human_minutes, assembling the
receipt), and HALTS on the first failed step: a red gate does not proceed to
proof or review or merge, a fail verdict does not proceed to merge, and two
failed review cycles stop and return the change to the human. It DELEGATES and
pauses for the steps that are your judgment - the build, the fresh-context
review, and the approve/steer - so the executor never fabricates a build, a
verdict, or an approval; the reference LiveLoop fails loud rather than pretend
one happened. It returns a state (halted at a named step with the reason, or
ready with the receipt) and records the human minutes the run cost. Sequencing
and halting are mechanical; you still build, review, and approve.

## Acting from a chat surface (veldo answer / steer / abort)

You do not need a terminal to unblock a build. An assistant (for example one on
Telegram) watches with `veldo status --json` - which lists every live run, its
classification, and any blocked question - and acts through the same inbox with a
thin CLI:

    veldo answer <run-id> <text>     resume a blocked run with the answer
    veldo steer  <run-id> <text>     record a steer for the agent's next turn
    veldo abort  <run-id> [reason]   stop the run aborted at its next checkpoint

These post the same commands handle_run_commands drains at a safe checkpoint (see
above); the CLI is only the front door, it does not bypass the loop. THE RULE still
holds: if an answer changes a requirement or a durable decision, commit it to the
spec (or an ADR) before the build is accepted, so a chat answer never becomes
hidden engineering truth.
