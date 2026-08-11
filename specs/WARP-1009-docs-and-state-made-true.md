---
schema: veldo.spec/v1
id: WARP-1009
title: Documentation and repo state made true - close the accuracy loose ends before parking VELDO
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      specs/WARP-0909-clean-context-dispatch-loop.md front-matter status is corrected
      from ready to shipped. WARP-0909 landed on origin (its implementation, proof
      manifest, and independent verdict are all committed), so ready is stale and wrongly
      leaves it as a claimable BUILD unit on the frontier; after the fix the frontier no
      longer offers WARP-0909.
  - id: AC2
    text: >
      The capabilities.yaml tracker_assign_op entry (both byte-identical copies and all
      packs) is corrected to state the live JiraCloud assign is WIRED (per WARP-1005),
      not that it raises "later increment"; the note stays honest (mechanical seam op;
      live JiraCloud write is reference, token-authed, not gate-run). No other capability
      claim is changed.
  - id: AC3
    text: >
      The shipped trackers.json template (engine/.veldo/trackers.json) token_ref
      example is corrected from a secrets: reference the default resolver cannot read to
      env:JIRA_TOKEN, which the shipped env-only resolver actually resolves, so the
      template example is true to the code. Any trivial stale header comment in
      .veldo/tracker_intake.py naming a not-yet-done increment is corrected.
  - id: AC4
    text: >
      No shipped spec's revision is bumped and no proof is invalidated (the changes are
      status/manifest/template accuracy only, not a spec-contract change); policy_check's
      spec-revision and ready-boundary checks stay clean. The WARP-0908 AC6 descriptive
      prose is intentionally left as-is (a historical shipped spec; editing it would risk
      staling its bound proof for no functional gain) and this deferral is noted.
  - id: AC5
    text: >
      Every edited ENGINE_GLOBS file (capabilities.yaml, and any .veldo/*.py touched) is
      re-synced byte-identical across engine and all seven packs (template-sync
      and pack-drift pass). The full gate is GREEN, RULE #1 is clean, no protected path is
      touched, and the change lands in the canonical two-commit shape.
required_evidence: [operational]
rollback: >
  Revert the commit. The changes are pure accuracy corrections (a spec status, a manifest
  note, a template example, a comment); reverting restores the prior stale text with no
  functional effect.
---

## Intent

Before VELDO is parked (live-enablement waits on the mobile release), close the small
accuracy gaps so the repository tells the truth about itself: WARP-0909 is shipped, the
live Jira assign is wired, and the shipped config template resolves as written. These
are documentation and state corrections, not new behavior.

## Context

- WARP-0909 (the clean-context dispatch loop, the OOM fix) is fully landed on origin but
  its spec status never flipped past ready, so frontier.claimable still lists it. Flip it
  to shipped.
- capabilities.yaml tracker_assign_op predates WARP-1005 wiring the live JiraCloud assign;
  the entry still says the live adapter raises. Correct it (safe: it is an under-claim
  now, but the manifest should be true).
- engine/.veldo/trackers.json uses secrets:jira_token as its token_ref example,
  but the shipped default resolver reads only env: references (a prior review noted this).
  Change the example to env:JIRA_TOKEN.
- Keep it proportionate and safe: do NOT bump any shipped spec's revision or touch its
  acceptance criteria (that would stale bound proofs). Leave the WARP-0908 prose note.

## Out of scope

- No new features, no WorkerSpawner auto-spawn wiring (parked, ASK-gated), no live
  enablement (waits on the mobile release), no method change.

## Notes

- These are accuracy edits; keep the gate green and the packs byte-identical. This is the
  last VELDO change before it is parked; after it ships, leave VELDO be.
