---
schema: veldo.spec/v1
id: WARP-0701
title: Claim ledger with capability matching - the atomic self-dividing coordination primitive
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0007
work: Y1
plan_revision: 2
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A claim lives as a file under the git common dir at veldo/claims/<unit-id>.json
      (shared across worktrees, outside git history), carrying the holder worker id, its
      requirements, and a heartbeat. The claims root resolves from git with a VELDO_RUNS_ROOT
      style override for tests. A unit id is sanitized so it is safe as a filename.
  - id: AC2
    text: Claiming a currently unclaimed unit is ATOMIC under real concurrency - the claim
      is published by writing the full record to a temp file and os.link-ing it onto the
      target (link fails if the target exists), so the target is never visible half-written
      and two threads racing for the same fresh unit result in exactly one winner, the
      other told it is already claimed. A live claim (fresh heartbeat) held by another
      worker is never stolen.
  - id: AC3
    text: A claim is granted only when the unit's requirements are a subset of the worker's
      capabilities; a worker missing any required capability is refused with a capability
      reason and takes nothing. Capabilities and requirements are free-form string tags, not
      a hardcoded OS or machine set.
  - id: AC4
    text: A claim whose heartbeat is older than the staleness threshold is stale (the holder
      is presumed dead) and is reclaimable by another capable worker; heartbeat refreshes it;
      release frees it; the same worker re-claiming its own unit is allowed (idempotent).
  - id: AC5
    text: A selftest drives the ledger over a temporary claims root - a CONCURRENT threaded
      race on one fresh unit grants exactly one winner (many threads, repeated), capability
      mismatch is refused while a match is granted, a live claim is not stealable, a stale
      claim is reclaimed, heartbeat and release behave - and is non-tautological: a mutation
      that skips the capability check, or that reverts the publish so the target is visible
      before it is fully written, makes an assertion fail under the concurrent race.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/claim.py, a selftest block, one capability entry
  (both copies), the WARP-0701 spec, and the PLAN-0007 plan; no protected path; claims live
  outside git history.
---

## Intent

The atomic primitive that lets independent vanilla workers self-divide work with no central
coordinator: a claim ledger where a worker exclusively claims a unit of work only if it can
actually run it (its capabilities cover the unit's requirements), so two workers never grab
the same unit and capability-gated work (iOS on a Mac, GPU on a GPU box) routes correctly.

## Context

This is Y1 of PLAN-0007 (the fleet), the base the frontier (Y2) and the worker loop (Y3)
build on. It lives beside the run registry (WARP-0501) under the git common dir so all
worktrees of one clone share it. Capability matching generalizes the macOS-gated iOS runner
(WARP-0308) to arbitrary tags. This item is the claim mechanics and capability match only;
computing WHICH units are claimable (across plans, bugs, reviews, scope) is Y2.

## Notes

Fresh claims are atomic by publishing a fully-written temp record via os.link onto the
target (link fails if the target exists), so the target never appears half-written and a
racing loser reads a complete record and is refused, not a torn one; a live claim is never
stolen. Stale-takeover (reclaiming a presumed-dead worker's unit) is serialized by a per-unit lock
(flock) with a re-check under the lock, so concurrent takeovers of one stale unit yield
exactly one winner and never overwrite a claim that turned fresh while a contender waited. Capabilities and
requirements are plain string sets; the match is requirements-subset-of-capabilities, so new
hardware or tools are just new tags with no code change.
