---
schema: veldo.spec/v1
id: WARP-0704
title: Serialized lander - land a completed build to the trunk under concurrency
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0007
work: Y4
plan_revision: 2
depends_on: [WARP-0703]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A Lander serializes landing across the whole fleet through a single land lock (a
      well-known unit in the claim ledger, WARP-0701) - it waits to acquire the lock, runs the
      land, and releases the lock in a finally so a crash never wedges the trunk; a selftest
      with many concurrent landers shows at most one is ever inside the land at a time.
  - id: AC2
    text: The land MERGES the build branch into the trunk rather than cherry-picking, so the
      build's implementation and evidence commits keep their shas and the digest-bound proof
      and verdict stay valid after landing; a selftest over a real temporary git repo confirms
      the build's implementation commit sha is present in the trunk history after a land onto a
      trunk that advanced independently.
  - id: AC3
    text: When the trunk advanced under the build, the merge union-resolves the known shared
      APPEND-ONLY files (the selftest, the capability catalogs, the event log) so both sides'
      additions survive with no conflict markers, and regenerates derived files (the spec
      index) deterministically; an unsafe union (a binary file, where a union would truncate
      the content to empty) is rejected rather than committed. A selftest over a real temporary
      git repo confirms a diverged trunk lands with both sides' additions present and no
      markers, and that a binary union-listed file is rejected (the merge aborted, not truncated).
  - id: AC4
    text: A conflict in any file that is NOT a known append-only file is a real conflict the
      lander refuses to guess at - it aborts the merge (leaving a clean tree) and reports the
      conflicting paths so the build is revised, rather than auto-resolving; a selftest over a
      real temporary git repo confirms a real conflict is rejected and the merge aborted.
  - id: AC5
    text: The land runs its steps in order (sync trunk, reconcile, gate, finalize) and a
      failing step aborts the land at that step while still releasing the lock; finalize
      policy-checks and pushes fast-forward-only so a trunk that advanced under a held lock is
      never clobbered (the push simply fails and the land is retried). The lock is held with a
      heartbeat keep-alive so a long land never looks stale. A selftest over a fake LandOps
      shows a failing step aborts-and-releases (a later land then acquires the freed lock), a
      rejected push fails the land without clobbering, and the heartbeat thread runs while
      the lock is held and stops after release - non-tautological on the release and the lock.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/lander.py, a selftest block, one capability entry
  (both copies), and the WARP-0704 spec; no protected path; the control logic is a seam with
  the real git steps in GitLandOps, and the selftest's git steps run over throwaway temp repos.
---

## Intent

Turn many workers' finished builds into commits on the trunk safely. Parallel workers finish
at overlapping moments; without coordination their pushes would race and clobber. The lander
serializes the land through a single fleet-wide lock and lands by MERGING (not rewriting), so
each build's proof stays bound to its unchanged implementation commit, the shared append-only
files carry every worker's additions, and a genuine conflict is surfaced rather than guessed.

## Context

Y4 of PLAN-0007, on the claim ledger (WARP-0701, which supplies the atomic lock primitive and
the heartbeat) and the worker loop (WARP-0703, whose dispatcher relies on a build being landed
as the durable outcome that removes a unit from the frontier). The land lock is just another
claim on a well-known unit, so it reuses the same atomicity, staleness, and heartbeat already
proven for work claims; the fast-forward-only push is a second, git-level guarantee so
correctness never rests on the lock alone.

## Notes

MERGE, not cherry-pick, is the deliberate choice: cherry-pick would rewrite the build's commit
shas and break the proof/verdict digest binding to the implementation commit, so the lander
merges and only the merge commit is new. The union set is the append-only files two lands can
both extend (scripts/selftest.py, both .veldo/capabilities.yaml copies, .veldo/events.jsonl);
specs/index.md is regenerated, not merged; anything else that conflicts is rejected. The
lander is the CONTROL logic plus a real GitLandOps; the concurrency-critical parts (the lock
serialization, abort-and-release, the ff-push guard, the heartbeat keep-alive) are gate-tested
over a fake LandOps, and the real git merge/union/reject path is gate-tested over throwaway
temporary git repositories. Which branch or worktree a build lives on is the worker loop's and
the launcher's concern (Y3, Y7); the lander takes a build ref and lands it.
