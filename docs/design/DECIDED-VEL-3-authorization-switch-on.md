# VEL-3 DECIDED - the values for the policy.yaml switch-on

VEL-3 (https://bcengi.atlassian.net/browse/VEL-3) reached **Decided** at 2026-07-25 21:31 EDT, fired by Dmitry.
All four questions are answered. This file exists so whoever authors the protected-path edit does not have to
reconstruct the decision from three Jira comments and a Telegram thread.

## The answers, verbatim where he gave them

| Q | Answer | Source |
|---|---|---|
| Q1 role identifier | **`founder`** | VEL-3 comment 21:31 EDT: "Q1 founder" |
| Q2 min_independence | **0** while a single approver exists | VEL-3 comment 21:16 EDT: "Agree with your recommendations. With 1 appover, 1 should be enough, not 2" |
| Q3 critical quorum | **count 1** today, rising automatically | same comment, plus the 02:24 EDT instruction |
| Q4 two-key | **degrade to 1 key**, never block, rise to 2 automatically when a second approver is registered | Telegram 02:24 EDT: "Degrading to 1 key from 2 is fine, when there is only 1 appover. If there are multiple, we can then use 2 keys. Veldo should support this out of the box, for other projects" |

## What that means for the edit

The block below is what the answers produce, using the shape read from authorization.py:210 / :222 / :225 /
:239-245 and the vocabularies from request.py:74-92.

```yaml
human_decisions:
  roles:
    spec_approval:              [founder]
    plan_approval:              [founder]
    decision_choice:            [founder]
    review_disposition:         [founder]
    risky_action_authorization: [founder]
    escalation:                 [founder]
  tier_roles:
    high:     [founder]
    critical: [founder]
  quorum:
    low:      {count: 1, min_independence: 0}
    standard: {count: 1, min_independence: 0}
    high:     {count: 1, min_independence: 0}
    critical: {count: 1, min_independence: 0}
```

**BUT DO NOT WRITE THOSE HARD-CODED ONES YET.** Q4 says the DECLARED number should be the one we actually want,
with the engine satisfying it against the registry. So once WARP-0719 ships, the counts above become the real
intent (two keys where two keys are wanted) and the engine degrades. Writing `count: 1` by hand is exactly the
hand-weakened policy that WARP-0719 exists to eliminate. **Sequence: WARP-0719 ships, THEN this block is
authored with honest declared numbers, THEN the protected-path edit is approved.**

## Two blockers that remain, neither of them his

1. **The approver registry has no source.** `is_authorized()` takes `approver_registry` as a RUNTIME parameter
   (authorization.py:439, shape at :453 as `{approver_id: {roles, independence, actor}}`) and nothing in the
   repository populates it. The policy block alone would refuse everyone with `unknown_approver`. Deciding where
   the registry comes from (a declared file, derived from the tracker's approver group, or supplied per request)
   is an unwritten item and should be raised as its own ticket.
2. **The edit is a protected-path push.** policy_check.py:287-307 blocks a push touching a protected path unless
   there is an approved, unexpired `veldo.approval/v1` whose `scope.commit` is a commit in the push, whose
   `scope.paths` covers the file, and whose approver is NOT the proof producer. So the agent may write and commit
   the block but cannot push it without that record. VEL-3 being Decided is the decision; the approval RECORD for
   the specific commit is a separate act.

## The process failure that produced this file

His 21:16 comment answering Q2 and Q3 sat on VEL-3 for 57 minutes while I rewrote that ticket's description
asking him four questions, one of which he had already answered. I did not read the comments before editing.
`feedback_read_jira_comments` already exists as a rule. **Read the comments before touching a ticket, and poll
comment bodies rather than only status in the loop's board check** - a status poll would never have shown this,
because answering in a comment does not change the status.

---

## UPDATE 2026-07-26 04:10 EDT - VEL-11 DECIDED, and the first blocker is now answered

The second blocker named above (the approver registry has no source) is settled. VEL-11
(https://bcengi.atlassian.net/browse/VEL-11) reached **Decided** at 04:10 EDT, fired by Dmitry, comment
verbatim: **"Option 1"**.

So the registry lives **IN THE REPOSITORY, on a protected path**, with the tracker group demoted to a
reconciliation check that fails loudly on divergence. Deriving it from the tracker group was rejected (it makes
authorization depend on a live network call and moves control of the approver set into Jira administration);
taking it from the caller was rejected (the caller would decide its own approver set).

**Spec written: `WARP-0720-approver-registry-declared.md`** in this directory. 4 acceptance criteria, spec-validated
and ready-gate green. Its load-bearing criterion is the THREE-WAY distinction, not the file: an ABSENT
declaration, an UNREADABLE one, and a READABLE ONE DECLARING NOBODY are three different facts, and collapsing
the middle into either of the others is how this becomes dangerous. That conflation has cost this repository
four times in the metrics module.

### The switch-on chain, as it now stands

1. **WARP-0719** (degrading quorum) - APPROVED on VEL-10. Must ship first, so the policy block can declare the
   numbers actually wanted instead of hand-written weakened ones.
2. **WARP-0720** (this registry) - DIRECTION decided on VEL-11, but the DIFF still needs its own recorded
   approval, because it registers a new protected path (a policy.yaml edit) and VEL-11 was explicitly a
   decision about direction rather than a sign-off on code that did not exist.
3. **VEL-3** (the policy block itself) - all four answers recorded above, role identifier `founder`. Blocked
   only on 1 and 2 now.
4. The protected-path push still needs an approved, unexpired `veldo.approval/v1` naming that commit and path
   with approver != producer (policy_check.py:287-307). Being Decided on the board is the DECISION; the
   approval record for the specific commit is a separate act.

Note the ordering dependency that is easy to get wrong: WARP-0720 depends on WARP-0719 because 0719 degrades
quorum against the NUMBER of registered approvers, so "unreadable registry" must not present as "small
registry". 0719 refuses on an unreadable registry; 0720 is where unreadable gets its meaning. They are asserted
together.
