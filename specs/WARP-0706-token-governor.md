---
schema: veldo.spec/v1
id: WARP-0706
title: Token pacing governor - use the whole budget over each window without running out early
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0007
work: Y6
plan_revision: 2
depends_on: [WARP-0703]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The governor MEASURES burn from the event stream (the same tokens metrics.compute
      reads) within each rolling window rather than querying a live remaining-token count
      (Claude Code exposes none outside the limit error). windowed_spend sums the tokens on
      events within the trailing horizon of a window, and measure_per_worker_rate estimates
      tokens per second per worker from recent windowed burn - both horizon-scoped, so spend
      older than the window does not count.
  - id: AC2
    text: desired_workers is a pure control law that paces the active worker count so measured
      burn tracks the target rate (budget / window) for the TIGHTER of the configured windows
      (typically a session window and a weekly window) - the min over windows of target_rate
      divided by the measured per-worker rate, capped at max_workers. It runs at least one
      worker while budget remains (so the budget is actually used and does not sit idle), and
      when burn is not yet measured it bootstraps to max_workers and paces for real next tick.
  - id: AC3
    text: The governor backs off to zero workers when a window's budget is already spent within
      its trailing horizon (waiting for the oldest spend to roll off) or during a limit-error
      backoff (now before a configured cooldown), so the pool never runs the budget out and
      then keeps hammering the limit.
  - id: AC4
    text: resume_at computes WHEN a backed-off pool may resume - the earliest time enough of
      the oldest in-window spend has aged out of every over-budget window (assuming no new
      spend), or now if already runnable. The governor only COMPUTES this time; it never sleeps
      or spawns anything. A detached background resumer is forbidden (feedback_no_rogue_processes) -
      wiring an actual opt-in, in-session resume waiter is the launcher's concern (Y7), so this
      item ships the timing computation, not a persistent process.
  - id: AC5
    text: A selftest over synthetic event streams with a deterministic now_epoch (never the
      wall clock) proves the control law and its non-tautology - tighter-window pacing,
      bootstrap-to-max, the spent-out and limit backoffs, at-least-one-while-budget-remains,
      resume timing, per-worker measurement, and horizon-scoping - such that taking the looser
      window (max instead of min) or ignoring the spent-out backoff turns it red; the full gate
      is GREEN.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/governor.py, a selftest block, one capability
  entry (both copies), and the WARP-0706 spec; no protected path; pure stdlib control law over
  the event stream, no process spawned.
---

## Intent

Use the token budget fully over each window without burning out early. The founder's ask was
direct: use it all every four hours and all every seven days, without running out too fast.
Since Claude Code exposes no live remaining-token count, the governor measures burn from the
event stream and paces the number of active workers to track the tighter window's target rate,
backing off when a window's budget is spent and computing when it may resume.

## Context

Y6 of PLAN-0007, on the worker loop (WARP-0703) and the existing token accounting on the event
stream (metrics.compute, the same aggregation the budget enforcer reads, so the governor's
numbers never fork from the enforcer's). It is the control law only; the worker loop and the
launcher (WARP-0707) consume desired_workers to size the pool and resume_at to time an opt-in
in-session resume. The resume waiter itself is deliberately NOT built here: a worker runs in a
real interactive session and pausing on token-out then resuming is an explicit, opt-in,
in-session step, never a detached background process (feedback_no_rogue_processes).

## Notes

Rolling windows (at most B tokens in any trailing W) rather than fixed reset points, so the
pacing is a single steady target rate B/W per window with the tighter one winning. The
at-least-one-worker-while-budget-remains rule means a single worker that outpaces a tight
window is not starved to zero; it runs, trips the spent-out backoff, and resumes when the
window rolls - averaging the target rate at coarse (worker-count) granularity. The limit-error
cooldown is the safety net for the case the measured pacing still hit the ceiling (a burst, an
unmeasured cost). All functions take now_epoch as a parameter so the gate is deterministic and
never depends on the wall clock.
