---
schema: veldo.spec/v1
id: WARP-0732
title: A review that says REWORK does not stop anything, which is theater - gate on unresolved blocking
  findings rather than on a pass verdict, because objecting is safe to forge and approving is not
status: ready
risk: high - it adds a new way for the gate to BLOCK a push, and a blocking check that is wrong in the
  strict direction stops all work in the repository. It touches `.veldo/policy_check.py`, which is a
  protected path at floor high, so it requires a recorded owner approval bound to the commit.
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-08-02
approval_record: >
  GIVEN ON TELEGRAM, 2026-08-02, in answer to a question he asked and a recommendation I made. I told
  him WARP-0730 and WARP-0731 had left a real gap: `valid_verdict_for` is kept but no longer consulted
  (`.veldo/policy_check.py:315`), so a change whose review said REWORK still merges when the mechanical
  checks are green, unless a person reads the finding. I proposed gating on unresolved blocking findings
  instead of on a pass verdict, and explained the asymmetry that makes it safe. His answer, verbatim:
  "Not good if werdict is rework still would merge. That's fluff and real theater."
  RECORDED, NOT PERFORMED. That is an unambiguous instruction to build it. Same evidentiary standard as
  WARP-0730, accepted for the same reasons: he raised the question, he was given the trade in writing,
  and he decided in his own words.
lane: standalone
depends_on: [WARP-0730, WARP-0731]
placement: [enforcement]
footprint:
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy_check.py"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-0732-blocking-findings-stop-the-merge.md"
acceptance_criteria:
  - id: AC1
    text: >
      AN UNRESOLVED BLOCKING FINDING STOPS THE PUSH. For each spec id carrying a verdict bound to a
      commit in the push range, the gate takes the verdict bound to the NEWEST such commit; if that
      verdict carries blocking findings, `policy_check.main()` returns non-zero and names the spec, the
      verdict file and the finding. Selftests cover both levels: `unresolved_blocking` over a fixture
      corpus, and `main()` itself with only that function stubbed so every other check runs for real.
      Each has its negative control beside it - no objection means no block - so neither can pass by
      refusing everything.
  - id: AC2
    text: >
      THE CHECK NEVER REQUIRES A VERDICT TO EXIST, AND THAT IS THE WHOLE SECURITY ARGUMENT. Absence of
      any verdict is not a block: authority for ordinary work stays with the gate and for protected
      paths with the owner, exactly as WARP-0730 left it. What is added is one-directional. Forging a
      finding blocks the forger, which no attacker wants; and forging a CLEAN verdict to clear an
      objection gains nothing, because simply never writing the objection reaches the same place more
      easily. So the newest-verdict-wins rule costs nothing that was not already free, and this AC
      exists to stop a later reader from "hardening" it back into a required pass.
  - id: AC3
    text: >
      RESOLUTION IS THE FIX, AND SUPERSESSION IS BY COMMIT ORDER. A blocking verdict is resolved by
      re-review after the fix: a later verdict for the same spec, bound to a newer commit in the range,
      replaces it. Two verdicts binding the SAME commit fail closed, blocking wins. A selftest drives
      the full sequence - REWORK blocks, then a clean verdict on a newer commit unblocks - because a
      check that cannot be cleared by doing the work correctly is a check that gets disabled.
  - id: AC4
    text: >
      THE OWNER CAN OVERRIDE, THROUGH THE MECHANISM THAT ALREADY EXISTS. A valid, unexpired,
      commit-bound `veldo.approval/v1` whose approver is not the proof producer overrides the findings
      block, and the gate says so in its output rather than going silently green. No new artifact type
      and no new field: the approval block is the one thing here an agent cannot produce, and reusing
      it keeps the override on that footing. A selftest asserts that a recorded approval turns the
      block into a pass. SELF-SEPARATION IS NOT RE-TESTED HERE and is not this item's property: it is
      enforced inside `valid_approval_for`, which this item calls unmodified and does not weaken.
  - id: AC5
    text: >
      FAIL CLOSED ON A FINDING IT CANNOT READ, which `blocking_findings` already does for anything
      outside the two canonical shapes, and this item must not weaken it. A selftest drives a verdict
      whose findings field is a shape the parser does not recognise and requires the block.
  - id: AC6
    text: >
      THE LIMIT IS STATED IN THE CODE, NOT ONLY HERE. This is NOT a forgery defense and the docstring
      says so in those words. An agent that can write the repository can also delete an inconvenient
      verdict file, and WARP-0730 conceded that fight on purpose. What this buys is that HONEST work
      does not merge past an outstanding objection, and that evading it now requires an affirmative
      destructive act visible in the diff rather than the mere absence of a file. Claiming more than
      that is how the last nine rounds started.
required_evidence: [unit]
rollback: >
  Revert the commit. The check is purely additive at the gate and reads artifacts that already exist in
  their existing shapes; no format changes, no migration, no persisted state. Reverting restores exactly
  the WARP-0731 behaviour, in which blocking findings are recorded and not enforced.
---

## Outcome

Dmitry, 2026-08-02: "Not good if werdict is rework still would merge. That's fluff and real theater."

He is right, and the gap is one I introduced by only telling half the story. WARP-0730 removed verdict
authority because a pass verdict is an artifact an agent can write. That reasoning is sound against a
malicious agent and it cost nine build rounds to establish. But the old rule was doing two jobs, and
only one of them was theater:

- Against a **subverted** agent, requiring a pass verdict never worked. Nine rounds proved it.
- Against an **honest** agent that produced bad work, a REWORK verdict mechanically stopped the merge
  with no human involved. That worked, and WARP-0730 threw it away with the part that did not.

The result today, verified in code rather than assumed: `valid_verdict_for` is kept but not consulted at
`.veldo/policy_check.py:315`, so a change whose review said REWORK merges when the mechanical checks are
green, unless a person reads the finding and acts. That is labor moved back onto the owner, which is the
opposite of what the method is for, and it makes the review look decorative.

## The asymmetry, which is the reason this is not a re-run of WARP-0722

Requiring a **pass** is forgeable in the dangerous direction: an agent mints its own approval and merges.
Blocking on a recorded **objection** is forgeable only in the safe direction: an agent that forges a
finding blocks itself, and no attacker wants that.

The same asymmetry answers the obvious follow-up. If a later clean verdict can clear an objection, can
an agent forge the clean verdict? Yes, and it gains nothing, because **no verdict is required at all** -
simply never writing the objection reaches the same outcome with less work. A rule can safely admit a
forgery that buys the forger nothing.

## Out of scope

- Requiring a review to have run. That is where the forgeable-pass problem lives, and it stays out.
- `valid_verdict_for` itself. Still unconsulted, still kept; the new check reads findings directly.
- Any change to the protected-path approval block, which is reused as the override and not modified.

## Notes for the implementer

The push range, not HEAD, is the binding domain, for the reason `valid_approval_for` already documents:
a verdict lands in an evidence commit that cannot name its own hash. That means the branch's own older
candidate commits are in range too, which is exactly why AC3's newest-commit-wins rule exists rather
than "any blocking verdict in range blocks".
