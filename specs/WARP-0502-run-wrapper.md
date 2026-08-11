---
schema: veldo.spec/v1
id: WARP-0502
title: veldo run wrapper - an observed run streams its live loop progress to the registry
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0005
work: R2
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The executor takes an OPTIONAL run-observer seam that is DEFAULT OFF. With no
      observer injected the executor is pure control logic - every existing executor
      selftest passes unchanged and nothing about the run's return value or halt
      semantics differs from before, and no run folder is written.
  - id: AC2
    text: When an observer is injected the executor reports a step for each loop phase it
      enters (resolve, plan_check for a planned spec, build, gate, proof, review,
      merge_ready) and a heartbeat while it works, through the run registry's live layer,
      so a reader can watch the build move through the loop.
  - id: AC3
    text: The executor blocks with a question when it pauses for a human (the approve or
      steer decision, and the two-failed-review adjudication) and records a terminal
      finish - done when the run is ready with the receipt, aborted with the reason
      recorded when it halted at a step - and a halt writes no phase step past the failed
      step.
  - id: AC4
    text: The high-volume per-step and heartbeat progress lands in the run folder live.jsonl
      and never reaches the committed events.jsonl (the durable milestones stay the run
      lifecycle vocabulary); the observer is a pure side effect that can never change the
      executor's return value or halt semantics.
  - id: AC5
    text: A thin driver (veldo run) allocates a run via the registry, drives the ready spec
      through the observed executor with the observer on, and returns the receipt plus the
      run id while the agent still builds and the human still approves. A selftest drives
      the instrumented executor over a fake LoopSteps seam and a temp runs root and is
      non-tautological - a mutation that skips a step emission or finishes done after a halt
      makes an assertion fail.
required_evidence: [unit]
rollback: git revert; additive - an optional run-observer seam plus a RunLogObserver and a
  thin veldo_run driver added to .veldo/executor.py, one capabilities entry in both copies, a
  selftest block, and this spec; no protected path; the run folder is outside git history
  and the observer defaults off so existing behavior is unchanged.
---

## Intent

Make a running VELDO build write its live progress into the R1 run registry as it moves
through the loop, so the readers (R3 and later) can watch it. A build should report which
loop step it is on, a heartbeat while it works, the question it is blocked on, and its
terminal outcome - without the executor losing its identity as pure control logic when no
one is watching.

## Context

The executor (WARP-0401) already sequences the loop over the LoopSteps seam and halts on the
first failed step. This item instruments it over a SECOND, optional seam - a run observer -
rather than forking the loop. The observer is default off and no-op, so the executor stays
pure control logic by default and every existing executor selftest passes unchanged. The
reference RunLogObserver bridges the observer hooks to the WARP-0501 registry (runlog): the
durable milestones (run.started, run.blocked, run.resumed, run.done, run.aborted) and the
high-volume per-step and heartbeat progress all land in the run folder live.jsonl, never the
committed events.jsonl. A thin veldo_run driver allocates the run, wires the observer, drives
the executor, and returns the receipt plus the run id; the agent-backed build and review and
the human-backed approve remain delegated, unchanged.

## Notes

The observer hooks are on_start, on_step, on_heartbeat, on_block, on_resume, and on_finish.
run() ignores every return value, so an observed run and an unobserved run reach byte-identical
results and the halt semantics do not change. A hard halt (a red gate, a failed build, an
invalid proof, a refused plan check, a non-ready spec) finishes the run aborted with the reason
recorded; a ready run finishes done; a halt that pauses for a human (the two-failed-review
adjudication) is a block that awaits the human rather than a terminal abort. The selftest drives
the instrumented executor over the fake LoopSteps seam and a temp runs root: a full success loop
writes run.started, a step per phase, and run.done; a red-gate halt writes an aborted finish
with the reason and no phase step past the gate; a human-pause writes a blocked question; and
the default-off path is proven to leave the result identical. Two mutations (skip a step
emission, finish done after a halt) each turn an assertion red, so the assertions are not
vacuous.
