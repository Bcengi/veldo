---
schema: veldo.spec/v1
id: WARP-0707
title: Fleet launcher, grouping, and multi-account procedure - elastic in-session worker pool governed by the pacer
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0007
work: Y7
plan_revision: 2
depends_on: [WARP-0703, WARP-0704, WARP-0705, WARP-0706]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A FleetLauncher runs an elastic control loop that, each tick, asks a controller for
      the governor's desired active worker count, caps it at the launched maximum N, and
      RECONCILES the active pool to that target - spawning workers to scale up and retiring
      them to scale down, via an injected WorkerSpawner seam - so the pool tracks the paced
      count. reconcile is idempotent (reconciling to the current size does nothing) and never
      exceeds N or goes negative.
  - id: AC2
    text: When the governed target is zero the loop distinguishes two cases - the frontier is
      DRAINED (no work left in scope) so it stops and retires every worker, versus the governor
      is BACKING OFF (a window's budget spent or a limit) while work remains, so it releases the
      workers, waits until the governor's resume time, and then RE-CHECKS the desired count
      before spawning again, so it never resumes straight into the limit.
  - id: AC3
    text: A worker is a real IN-SESSION worker, never a detached or headless process - the
      WorkerSpawner seam's real implementation spawns in-session (the same in-session parallel
      mechanism a human session uses), and the multi-account path (one session per account,
      CLAUDE_CONFIG_DIR on Linux) is a documented procedure, not an auto-spawner this module
      runs. The resume WAIT is likewise an injected seam, so the module never sleeps or spawns
      anything itself and the opt-in in-session waiter is wired by the caller.
  - id: AC4
    text: Grouping is expressed as a scope (a plan id, a label, or a workspace) that the
      launcher threads to every worker it spawns, so a fleet can be scoped to a slice of the
      frontier and different groups can work different slices while sharing the one claim ledger.
  - id: AC5
    text: A selftest drives the launcher over fake spawner, controller, and waiter seams
      (spawning no process and sleeping nothing) and proves the control logic and its
      non-tautology - elastic scale-up, retire-on-scale-down, cap-at-N, scope threading,
      drain-stops-and-retires-all, backoff-waits-then-re-checks-and-respawns, and
      terminate-on-drain-after-backoff - and the full gate is GREEN.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/fleet.py, a selftest block, one capability entry
  (both copies), and the WARP-0707 spec; no protected path; pure stdlib control logic with
  spawning and waiting as injected seams, so the gate runs no process and sleeps nothing.
---

## Intent

Make running the fleet a single command. `veldo fleet N` launches up to N workers that pull
from the global frontier and land their work, with the token governor deciding how many are
actually active so the budget is used without running out. Add more workers or more accounts
for throughput; the pool sizes itself and pauses and resumes with the budget.

## Context

Y7 of PLAN-0007, the capstone, on the worker loop (WARP-0703), the serialized lander (WARP-0704),
env provisioning (WARP-0705), and the token governor (WARP-0706). It is the elastic control
loop plus the grouping scope; the actual in-session worker spawning and the in-session resume
wait are injected seams (their real implementations live in the launcher's front door and the
worker skill), and the multi-account and terminal-count guidance is a documented procedure. The
governor's resume_at note is honored here: after waiting, the loop RE-CHECKS desired before
spawning, so a wake never resumes straight into the limit.

## Notes

The two hard constraints are architectural, not incidental: no detached or headless process
(feedback_no_rogue_processes) - a worker is a real in-session session, so multi-account is one
session per account (CLAUDE_CONFIG_DIR on Linux lets several run on one machine; macOS shares
the keychain so it is one worker per account there), and the resume waiter is opt-in and
in-session; and terminals are the unit of parallelism, not of project count - one
workspace-scoped terminal covers all the VELDO repos it can see, and you add terminals for
throughput, never one-terminal-per-project. Both spawning and waiting are seams so the control
loop is proven deterministically in the gate with no process and no sleep, and the real
in-session mechanism is supplied by the caller.
