---
schema: veldo.spec/v1
id: WARP-0401
title: The Executor v1 - drive a ready spec through the loop with human approve and steer and recorded human_minutes (X1 of PLAN-0004)
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0004
work: X1
plan_revision: 3
human_approval: not_required
protected_paths: []
required_evidence: [unit, operational]
acceptance_criteria:
  - id: AC1
    text: A stdlib module .veldo/executor.py ships an Executor that sequences the
      loop as explicit steps behind a seam (resolve a ready spec, a plan
      run-check for a planned spec, build, gate, proof, review, merge readiness).
      The step surfaces are a LoopSteps interface; the mechanical steps (running
      the gate, assembling and validating the proof, emitting the loop events,
      assembling the receipt) the Executor runs itself, and the agent and human
      steps (build, review, approve or steer) it delegates to injected callables
      and pauses for. Executor.run(spec_id) drives the steps in order and returns
      a result. A spec that is not ready halts at resolve and a planned spec whose
      run-check refuses halts at plan_check, each before any build runs.
  - id: AC2
    text: Halt-on-failure is enforced and load-bearing (XJ1). A failed step halts
      the loop and does not proceed to the downstream steps - a red gate does NOT
      reach proof, review, or merge; a fail verdict does NOT reach merge; and two
      failed review cycles stop and return the change to the human (at that point
      the defect is almost always in the specification). The run returns a state
      that is either halted at the named step with the reason, or ready with the
      receipt, and never fabricates a missing step result. loop_respected(result)
      is a pure invariant exposed for direct test: a result with a proof, review,
      or merge step after a failed gate, or a merge step after a failing final
      verdict, is not respected.
  - id: AC3
    text: The run records the human minutes it cost and assembles a receipt. Human
      minutes come from the delegated human-attention steps (the review cycles and
      the approve or steer) and are summed for the run and emitted on their
      canonical events (verdict.recorded and approval.recorded) so the run total
      equals what the metrics reader derives from the event stream (no fork). The
      receipt carries the criteria proven, the gate result, the verdict, the run
      human_minutes, and the ONE thing (if any) awaiting a human, matching the run
      skill receipt.
  - id: AC4
    text: Capabilities coverage is honest and complete. Both .veldo/capabilities.yaml
      and engine/.veldo/capabilities.yaml carry, byte-identically, an
      executor_driver entry (status mechanical, home .veldo/executor.py) and an
      executor_agent_dispatch entry (status procedure, home skills/run), each with
      a status drawn from the manifest vocabulary. mechanical is honest because the
      step sequencing, halt-on-failure, human_minutes recording, and receipt
      assembly are stdlib and run end to end in the gate here over a fake seam with
      no live agent, gate, or backend; procedure is honest because the build and
      review dispatch and the human approval are skill-instructed and not
      transactionally enforced (the reference LiveLoop fails loud rather than
      fabricate them).
  - id: AC5
    text: The control logic is gate-tested with no external surface. The selftest
      (CHECK_unit) imports .veldo/executor.py and drives the Executor over a FAKE
      LoopSteps seam through a full successful loop (asserting the steps run in
      order, evidence is reached, human_minutes are recorded, and the receipt has
      the right shape) AND through the failure cases (a red gate halts before
      proof, review, and merge; a fail verdict halts before merge; two failed
      review cycles re-drive then stop for a human; a fail then a pass recovers; a
      non-ready spec, a plan run-check refusal, a build failure, and an invalid
      proof each halt at their step; a resolve error is a clean halt not a crash).
      Non-tautology is proven: a mutant that proceeds past a red gate, and one that
      merges after a fail verdict, both FAIL the loop_respected invariant while the
      real halted runs pass it, and the reference LiveLoop fails loud on the
      delegated steps.
  - id: AC6
    text: The deliverable is generic (zero company, product, or person names and
      zero absolute host paths in the module, the skill edit, the capabilities
      entries, and this spec beyond the standard owner field) and hygienic (ASCII
      only, no em or en dash, no double hyphen). The run skill notes that the
      executor drives and halts the steps while the agent still builds and reviews.
      The specs index regenerates to include this spec, and the full gate (lint,
      unit, generated, docs, template sync, secret scan, contract validation) stays
      green with every prior selftest case still passing.
rollback: git revert; X1 is additive - a stdlib module .veldo/executor.py, a
  selftest block, two capabilities entries in both manifest copies, a run-skill
  paragraph, and this spec. It touches no protected path, no synced core
  (validate.py, policy_check.py, update_index.py, veldo-guard.sh), and adds no new
  required CHECK_ slot, so reverting removes the executor and its unit block with
  no effect on any running gate; prior selftest cases are unchanged.
---

## Intent

PLAN-0004 turns VELDO into an executable system. Feature F1 is the executor: a
runtime that DRIVES a ready spec through the whole loop so the human only
APPROVES and STEERS rather than hand-driving every step. Today /veldo:run is a
procedure an agent follows step by step; X1 makes the sequencing, the halting,
the human-minutes accounting, and the receipt into mechanical control logic that
cannot skip a step, cannot proceed past a failure, and cannot fabricate a build,
a verdict, or an approval. The scarce resource the method protects is human
attention, so the executor records the human minutes each run costs and hands
back a receipt whose last line is the one thing (if any) awaiting a human.

## Context

X1 of PLAN-0004, feature F1, depends on nothing (order 10). It follows the
shipped platform pattern: a stdlib module under .veldo/ (like events.py,
metrics.py, and release.py), no third-party dependency, control logic gate-tested
in the unit slot with no live surface. The seeds it grows from are the current
run procedure (packs/claude/skills/run/SKILL.md) and the human_minutes envelope field
and emitter in .veldo/events.py. It is a driver and a state machine over the
existing seams, deliberately NOT a daemon or a service: the executor sequences
and halts, and the real gate, the event log, the spec files, and the plan check
are surfaces behind a seam. The driver is mechanical (sequencing, halt-on-failure,
human_minutes, receipt run in the gate here over a fake seam); the build and
review dispatch stay procedure, because dispatching an implementer and a
fresh-context reviewer and pausing for a human approval are agent and human work,
not a transaction the plugin can enforce. This is the same honest split the
manifest already draws for human_minutes_events and fresh_context_review.

## Out of scope

Wiring the executor to a live agent implementer, a live reviewer, or a real
approval surface - those are the delegated callables an adopting runtime injects,
and the reference LiveLoop fails loud rather than pretend. Emitting lessons
automatically from a run (X3 owns the lessons store; automated emission is a
later, additive caller). The server-side control plane and the human-identity
approval gateway (X8 and X9, feature F2) - the executor produces a ready receipt
and names what awaits a human, it does not itself merge or attest an identity.
Rendering run metrics (X4 owns the dashboard).

## Notes

Why the driver is mechanical and the dispatch is procedure: Executor.run and
loop_respected are pure enough to run end to end in the gate over a fake
LoopSteps seam with no network, no model, and no product surface, so their status
is mechanical and the selftest proves it. Dispatching the implementer and the
reviewer, and pausing for the human approval, are things an agent and a human do
by instruction; claiming them as mechanical would overclaim, so
executor_agent_dispatch is procedure, homed in the run skill, and the reference
LiveLoop refuses to fabricate them.

Why halt-on-failure is proven adversarially: the whole value of the executor is
that a red gate or a fail verdict STOPS the loop rather than shipping, so the
selftest drives the failure cases directly (a red gate reaches neither proof nor
review nor merge; a fail verdict never reaches merge; two failed cycles stop for a
human) AND proves the assertions are not vacuous with a mutant driver that ignores
the failure and pushes on - it fails the loop_respected invariant that the real
run satisfies. The human_minutes assertion is checked against the sum carried on
the emitted events, so a driver that recorded a number the events do not back
would be caught as a fork.

The reviewer should confirm by rerunning the selftest and the standalone CLI:
(1) the Executor over a fake seam runs the full loop, reaches a ready receipt, and
records human_minutes equal to the emitted events' sum; (2) each failure case
halts at its step and does not proceed past it; (3) the mutant fails
loop_respected while the real halted runs pass it; (4) the reference LiveLoop
fails loud on build, review, and approve; (5) the capabilities entries are
byte-identical across both manifest copies and their statuses are honest; (6) the
docs, secret, lint, and template-sync gates stay green.
