---
schema: veldo.spec/v1
id: WARP-0703
title: The veldo work loop - claim, dispatch, release, drain
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0007
work: Y3
plan_revision: 2
depends_on: [WARP-0701, WARP-0702]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A WorkLoop, given a worker id, capabilities, an optional scope, and an injected
      dispatcher, repeatedly claims the next claimable unit (via the frontier WARP-0702 and
      an atomic claim WARP-0701), dispatches it, and releases the claim - looping until the
      frontier is empty (drained), with a max_units runaway backstop that is not the normal
      stop.
  - id: AC2
    text: The loop holds the claim across the dispatch so no other worker can take the same
      unit while it runs, and always releases the claim after the dispatch, even if the
      dispatch raises (a crashed dispatch is a failed unit, not a stuck claim). Because
      claimable() is a snapshot and the claim gates ownership not done-ness, after each claim
      the loop re-checks the unit is still the work it saw (still ready for a build, still in
      review for a review) and releases + skips it if another worker finished it in the
      claim-time window, so two workers never dispatch the same unit even across that window.
  - id: AC3
    text: Dispatch is a seam, not inlined agent work - building a spec and reviewing one are
      delegated to a real Dispatcher (the executor / veldo run for a build, a fresh-context
      reviewer for a review) whose durable outcome (a landed build flips the spec to shipped)
      is what removes a unit from the frontier; the loop itself only orchestrates.
  - id: AC4
    text: A unit whose dispatch fails is released for a human, another worker, or a later
      retry, but this worker does not re-claim it, so a single worker never hot-loops its own
      failing unit and still drains the rest of the frontier.
  - id: AC5
    text: A selftest drives the WorkLoop over a temporary repo and claims root with a fake
      dispatcher (no live agent) - asserting every claimable unit is dispatched, the claim is
      held across each dispatch, only successful units leave the frontier, the loop drains via
      the empty frontier (not the backstop) leaving no claim held, and a failed unit is
      released yet dispatched exactly once - and is non-tautological: dropping the release
      leaves the failed unit claimed, and dropping the self-skip hot-loops the failed unit.
      A further selftest runs several WorkLoops concurrently (barrier-synchronized threads)
      over one shared frontier and claims root and asserts every unit is dispatched exactly
      once across the whole fleet, proving claim-then-recheck closes the done-ness window.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/work.py, a selftest block, one capability entry
  (both copies), and the WARP-0703 spec; no protected path; the loop is pure control logic
  with dispatch injected, so nothing runs a live agent by construction.
---

## Intent

The heart of the fleet: a worker's run loop. With no central coordinator, each worker
repeatedly asks the frontier what it may claim, atomically claims the next unit, dispatches
it, releases the claim, and loops - stopping when the shared frontier is drained. Many such
loops on many machines and accounts divide the whole repo's ready work among themselves
purely through the shared claim ledger, with no boss to fail.

## Context

Y3 of PLAN-0007, sitting on the claim ledger (WARP-0701) and the global claimable frontier
(WARP-0702). It is the control logic only: claim, dispatch, release, drain. The DISPATCH -
actually building a spec (the executor / veldo run) or reviewing one (a fresh-context
reviewer) - is delegated to an injected Dispatcher, exactly as the executor delegates the
build step behind a LoopSteps seam, so the loop is gate-testable with a fake dispatcher and
no live agent. The serialized lander that turns a built unit into an evidence commit on main
is Y4; here a successful dispatch is modeled as making its own outcome durable (spec shipped),
which is what removes the unit from the frontier.

## Notes

The loop holds the claim across the dispatch (mutual exclusion) and always releases after in
a finally (no stuck claims on a crash). A failed unit is released - so a human, another
worker, or a later retry can pick it up - but the failing worker records it and does not
re-claim it, so it never hot-loops its own failure and still drains the rest. Success is the
dispatcher's durable effect (a landed build is shipped, a resolved review leaves status
review), so the loop needs no special-casing to stop offering a finished unit; the frontier
simply no longer lists it. max_units is a runaway backstop, not the normal termination -
drain (an empty frontier) is.
