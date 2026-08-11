---
schema: veldo.spec/v1
id: WARP-1003
title: The promote gate - Approved-for-dev plus Agent flips the draft spec to ready
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W3
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The inbound bridge gains a promote reconciler: for a ticket that is fully
      eligible (is_eligible == Agent AND status in the ready-for-dev set AND a
      resolvable repo, the full WARP-1001 triple) and that already has a drafted spec
      (linked by its intake_source), it flips that spec's front-matter status from
      draft to ready, making it a claimable frontier unit. This wires the human
      validation gate: the human's Jira action (move to Approved-for-dev, keep it
      assigned to Agent) is the ONLY thing that promotes a draft.
  - id: AC2
    text: >
      The promote is idempotent and fail-closed: a spec already ready (or beyond) is
      left untouched (no-op, no churn); a ticket that is not fully eligible does NOT
      promote; a ticket with no drafted spec does not promote (nothing to flip). It is
      a reconciler over the durable intake_source link, no processed-offset ledger and
      no second store, so re-running it changes nothing already promoted.
  - id: AC3
    text: >
      Human control is preserved: a draft whose ticket a human reassigned away from
      Agent, or moved out of the ready set, is NOT promoted (the eligibility triple
      catches it), so a human can pull a ticket back from the fleet before it builds.
      The promote only advances the spec's own lifecycle gate (draft to ready); it
      writes nothing else on the spec and nothing back to the tracker (the repository
      stays the single source of truth; the outbound writes are WARP-1004).
  - id: AC4
    text: >
      Gate-tested over the FakeTracker with teeth: an eligible (Approved-for-dev +
      Agent + resolvable repo) ticket WITH a drafted spec flips that spec draft to
      ready; and single-leg negatives each leave the draft unpromoted - a status not
      in the ready set, a non-Agent or reassigned assignee, and a ticket with no
      drafted spec - non-tautologically (restoring the missing leg promotes it).
      Idempotency is asserted (a second pass leaves the ready spec byte-identical).
  - id: AC5
    text: >
      capabilities.yaml gains an honest entry for the promote gate (mechanical, its
      shipped home) in both byte-identical copies; every edited ENGINE_GLOBS file is
      re-synced byte-identical across engine and all seven packs
      (template-sync and pack-drift pass). The full gate is GREEN, RULE #1 is clean,
      no protected path is touched, and the change lands in the canonical two-commit
      shape.
required_evidence: [unit]
rollback: >
  Revert the commit. The promote is additive to the bridge and nothing runs it
  automatically yet (the unattended runner is a later item); removing it leaves the
  drafts sitting un-promoted exactly as before, harming nothing.
---

## Intent

This is the human validation gate, wired. WARP-1002 drafts a spec from an
Agent-destined ticket and shows it on the ticket; a human reads it and, if it is
right, moves the ticket to Approved-for-dev (keeping it assigned to Agent). That
Jira action, and only that, promotes the draft to ready so a fleet worker can
claim it. The machine never promotes its own draft (PLAN-0010 NG1); the human's
approval in Jira is the trigger.

## Context

- Reuse: is_eligible (WARP-1001, the full triple) in .veldo/tracker.py, and the
  bridge's spec store + intake_source oracle (WARP-1002) in .veldo/tracker_bridge.py.
  The promote is a sibling reconciler in the bridge, not a new subsystem.
- The distinction from WARP-1002: the DRAFT trigger is the two-leg subset (Agent +
  repo); the PROMOTE trigger is the full triple that adds the ready-status leg
  (Approved-for-dev). Same eligibility function, different call site.
- The flip is only draft to ready on the spec's front matter (reuse the spec-store
  write path); it never touches the tracker (WARP-1004 owns outbound) and never
  writes anything else on the spec, so the repository stays the source of truth.
- Fail closed and idempotent, matching the mirror/bridge reconciler pattern.

## Out of scope

- No outbound tracker writes (status, comment, links, reassign) - that is WARP-1004.
- No unattended runner/poller - the promote is a callable reconciler here; the live
  service is a later item. No live Jira in the gate.

## Notes

- Keep the promote pure control logic over the injected adapter + spec store so the
  gate drives it with a FakeTracker and a temp repo. Fail closed: any doubt about
  eligibility or an absent draft resolves to no promotion.
- Follow the byte-identical engine sync discipline and re-run the drift checks before
  proof. Match the existing tracker/bridge selftest conventions.
