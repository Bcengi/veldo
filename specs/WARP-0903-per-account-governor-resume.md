---
schema: veldo.spec/v1
id: WARP-0903
title: Per-account token governor and the in-session resume-waiter
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W3
plan_revision: 1
depends_on: [WARP-0902]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The governor tracks budget PER ACCOUNT. Each account has its own session and weekly
      windows and its own measured burn, and the desired active-worker count is computed per account
      by REUSING the WARP-0706 control law (desired_workers / resume_at), not a reimplementation. An
      account whose window budget is spent (or is in a limit-error cooldown) contributes zero desired
      workers while every OTHER account keeps pacing, so the pool never fully stalls while any account
      still has budget. The fleet-wide desired count is the sum across accounts, capped at the pool
      max.
  - id: AC2
    text: Burn is attributed per account. The measured burn feeding each account's windows is the
      burn produced under that account (keyed by the account identifier the worker carries, VELDO_ACCOUNT
      from W2), so one account's spend never counts against another's budget; an account with no
      measured burn yet bootstraps exactly as the single-pool control law does (allow up to its share
      until burn is on the stream).
  - id: AC3
    text: Resume timing is per account. resume_at is computed for each backed-off account over its own
      windows and burn, so an account resumes when ITS window rolls, independent of the others; a
      fleet with one account spent and another with budget keeps the second running and schedules the
      first to resume at its own reset.
  - id: AC4
    text: The launcher's wait seam is filled by a REAL in-session resume-waiter. wait_until(epoch)
      performs an in-session blocking wait (a real wait in the running session, which dies with it -
      NOT a detached process, no spawn, consistent with feedback_no_rogue_processes and PLAN-0007
      NG1); tick() advances one control interval while workers run. On resume the launcher re-checks
      the per-account desired counts before spawning, so it never resumes straight into a still-spent
      window. The gate drives a FAKE clock/waiter (deterministic now_epoch, no real sleeping).
  - id: AC5
    text: Gate-tested via the selftest over synthetic per-account event streams and a fake clock (no
      real sleeping) - per-account pacing (one account spent, another with budget: the second keeps
      running, the pool is NOT stalled, and the desired count is the per-account sum capped at max);
      per-account resume timing (the spent account resumes at its own reset, computed from its own
      windows); and the waiter re-checks desired before resuming. Non-tautological teeth: a governor
      that zeroes the WHOLE pool when any single account is spent, or a waiter that resumes without
      re-checking desired, turns an assertion red.
required_evidence: [unit]
rollback: git revert; additive - a per-account layer over the existing governor plus the in-session
  resume-waiter filling the launcher wait seam, a selftest block, and this spec, all repo-root dogfood
  machinery (.veldo/, NOT shipped engine, not copied into packs). No protected path; pure stdlib; the
  single-pool control law (desired_workers/resume_at) is reused unchanged so its existing selftests
  still pass; the gate uses a fake clock and never sleeps or spawns.
---

## Intent

W3 makes the fleet's pacing per account so multiple accounts run productively together: each account
paces against its own session and weekly budget, an account that hits its limit backs off on its own
while the others keep working, and a real in-session waiter sleeps a backed-off account until its
reset and resumes it after re-checking. This is what makes running several accounts at once actually
use each account's budget without the whole pool stalling when one runs out, and it is the in-session
half of the auto-resume the founder asked for (the cross-full-exhaustion external supervisor stays
opt-in and human-gated at W7 / open decision D1).

## Context

W3 of PLAN-0009, depends on W2 (accounts exist and each worker carries its account, VELDO_ACCOUNT).
The governor (WARP-0706, .veldo/governor.py) is the single-pool control law today: desired_workers and
resume_at are pure arithmetic over a set of Windows and the burn measured from the event stream, and
it explicitly never sleeps or spawns (a detached background resumer is forbidden; wiring an actual
in-session waiter is the launcher's concern). The launcher (fleet.py FleetLauncher.run) already
consumes a waiter seam (wait_until(epoch), tick()) whose reference is unfilled. W3 adds a per-account
layer that reuses the control law per account and fills the wait seam with a real in-session waiter.

## The no-rogue-processes boundary

The resume-waiter waits IN-SESSION: a real blocking wait in the running worker/launcher session that
dies with it, spawning nothing and detaching nothing (feedback_no_rogue_processes, PLAN-0007 NG1).
The governor still only COMPUTES times; it never sleeps or spawns. Hands-free relaunch after an
account is FULLY exhausted and the session itself is killed needs an external supervisor - that is
opt-in, off by default, and human-gated at W7 / open decision D1, NOT part of W3.

## Out of scope

The veldo CLI front door (W4), shipping the fleet into the engine (W5), and the opt-in external
supervisor for auto-relaunch after full exhaustion (W7 / D1). The single-pool control-law arithmetic
is reused unchanged, not rewritten.

## Notes

Two commits, the standard shape: an impl commit with its own independent review and commit-bound
verdict, then an evidence-only commit (proof/, .veldo/, specs/) inheriting the impl verdict via the
guard's parent rule.

RULE #1: the gate's docs dash-sweep catches only em/en dashes, not the ASCII double-hyphen; hand-check
that no `--` appears in new code or prose (a genuine `--flag` CLI option, a `---` YAML delimiter, and
the established `# ---` selftest block header are fine; do not introduce `# -- divider ----` runs -
match the plain `# comment` fleet-module style). The gate must never sleep: drive the waiter with a
fake clock and a deterministic now_epoch so the per-account pacing and resume timing are exercised
without real time passing.
