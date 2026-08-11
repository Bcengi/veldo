---
schema: veldo.spec/v1
id: WARP-0901
title: Real fleet dispatcher - fill the work-loop dispatch seam with build (executor) and review (fresh-context) paths
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W1
plan_revision: 1
depends_on: []
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A real Dispatcher (.veldo/dispatch.py) fills the work.py Dispatcher seam. dispatch(unit)
      routes by unit kind - a build unit (spec status ready) is driven through the executor's build
      path, a review unit (spec status review) is driven through a fresh-context reviewer - and
      returns {ok: bool, ...} so the WorkLoop's existing release/failed semantics apply unchanged (a
      failed dispatch returns ok False and the loop releases the claim for a retry, never a stuck
      claim).
  - id: AC2
    text: The BUILD path drives the executor (WARP-0401) over the spec through resolve, plan
      run-check, build, gate, and proof, and STOPS at review - the built spec is flipped to status
      review so it becomes a claimable review unit on the frontier, and the build worker does NOT
      review its own work (independence is preserved by making review a separate unit). A red gate or
      a failed build halts (ok False) and does not flip the spec to review. The mechanical steps are
      the executor's; the intelligent build step stays a delegated procedure (LiveLoop fails loud
      rather than fabricate a build).
  - id: AC3
    text: The REVIEW path drives a fresh-context reviewer over the built commit and records a
      commit-bound verdict; on a passing verdict (pass or pass_with_notes, zero blocking findings)
      the serialized lander (WARP-0704) lands the evidence and the spec becomes shipped (leaving the
      frontier); on a failing verdict the spec returns to ready (or blocked) for a fix, not shipped.
      The intelligent review step stays a delegated procedure (the reference path fails loud rather
      than fabricate a verdict).
  - id: AC4
    text: The durable outcome drives the frontier - a shipped spec (build then review then land) is
      gone from claimable(), and the build/review split means the two unit kinds hand off through
      the spec's status (ready then review then shipped) with no shared state beyond the repo, so two
      workers never both build or both review the same unit (the WorkLoop's claim-then-recheck plus
      the status handoff).
  - id: AC5
    text: The dispatcher is gate-tested via the selftest over a THROWAWAY repo with a
      controllable/fake executor and reviewer (no live agent) - a build unit drives the build path
      and leaves the spec in review; a review unit with a passing verdict lands and ships the spec;
      a failing build and a failing verdict each return ok False and leave the spec un-shipped; the
      real LiveLoop/reviewer path fails loud rather than fabricate. Non-tautological teeth: a mutant
      that ships without a passing verdict, or that reviews its own build, turns an assertion red.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/dispatch.py (repo-root dogfood machinery, NOT shipped
  engine, so not copied into packs and no re-assembly), a selftest block, and this spec; plus any
  thin build-only support added to the executor kept behind a default that leaves the existing
  executor selftests unchanged. No protected path; pure stdlib control logic; the intelligent
  build/review remain delegated procedures driven by the in-session agent, never a detached process.
---

## Intent

The fleet's worker loop (work.py, WARP-0703) claims a unit and dispatches it through an injected
Dispatcher seam whose reference is unfilled (raises NotImplementedError). W1 fills that seam with a
real Dispatcher so a claimed unit is actually worked: a build unit is built through the executor and
a review unit is reviewed by a fresh context, and the durable outcome (the spec's status advancing
ready then review then shipped) is what removes the unit from the frontier. This is the piece that
turns "the fleet claims work" into "the fleet does work."

## Context

W1 of PLAN-0009, no dependencies. The machinery it wires already exists: the executor (WARP-0401,
.veldo/executor.py) drives a spec through resolve, build, gate, proof, review, merge over a LoopSteps
seam where the intelligent build/review steps are delegated (executor_agent_dispatch, a procedure -
the LiveLoop fails loud rather than fabricate); the frontier (WARP-0702) already splits a build unit
(spec status ready) from a review unit (spec status review); the serialized lander (WARP-0704) lands
a built spec to the trunk. W1 adds the Dispatcher that connects the WorkLoop to these: build unit to
the executor's build path, review unit to a fresh-context reviewer plus the lander.

The whole fleet (executor, work, frontier, claim, lander, this dispatcher) lives in the repo-root
.veldo/ as dogfood machinery - it is NOT in the shipped engine (engine/.veldo), so it is not
copied into packs and forces no re-assembly. Shipping it into the engine so adopters get it is W5;
the real veldo CLI front door is W4; W1 only makes the dispatch real.

## The build/review split (why the build worker stops at review)

Independence is the VELDO invariant: a change ships only on a fresh-context verdict from a reviewer
that is not the builder. The fleet realizes this by making build and review SEPARATE claimable units
keyed on the spec's status. So the build path deliberately stops at status review (build, gate, proof
done, spec flipped to review) rather than reviewing its own work; a review unit then becomes
claimable and a different worker (a genuinely fresh context) reviews it and, on a pass, lands it to
shipped. The status is the handoff; there is no shared state beyond the repo.

## Out of scope

Spawning agents or any detached process - the intelligent build and review steps remain delegated
procedures performed by the in-session agent (the LiveLoop / reviewer fail loud rather than
fabricate), consistent with the no-rogue-processes rule and PLAN-0007 NG1. The in-session worker
spawner and account selection are W2; the veldo CLI is W4; shipping the fleet in the engine is W5.

## Notes

Two commits, the standard shape: an impl commit that also BUNDLES the approved PLAN-0009 plan file
(the plan-entry pattern, as WARP-0801 bundled PLAN-0008 with its first work item) plus this spec and
carries its own independent review and commit-bound verdict; then an evidence-only commit (proof,
.veldo, specs) inheriting the impl verdict via the guard's parent rule.

Any build-only support added to the executor (to stop cleanly at review without reviewing) is kept
behind a default that leaves every existing executor selftest unchanged, so the executor's proven
halt-on-failure invariants are not disturbed. The dispatcher is gate-tested with a fake executor and
reviewer over a throwaway repo so no live agent runs in the gate; the real path is the LiveLoop and a
fresh-context reviewer, which fail loud rather than fabricate a build or a verdict.
