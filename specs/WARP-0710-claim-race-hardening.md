---
schema: veldo.spec/v1
id: WARP-0710
title: Claim ledger race hardening - one lock arbitrates every write path, no double grant
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: The claim ledger (.veldo/claim.py) grants a unit under a SINGLE per-unit lock that
      arbitrates the whole decision - it refuses a live claim by another worker and otherwise
      (unclaimed, stale, corrupt, or the worker's own) publishes a fully-written record with an
      atomic os.replace - so the fresh-publish and the stale or own takeover share one arbiter
      and can never both grant the same unit; the previous design's separate lock-free fresh
      os.link path and flock-guarded takeover os.replace path are gone.
  - id: AC2
    text: Mutual exclusion holds under claim/release CHURN - with the trunk not stale, many
      workers repeatedly claiming and releasing one unit never produces two live holders,
      because a fresh claim can no longer be published (unlocked) underneath a takeover's
      re-check-then-replace. The specific defect fixed - a takeover's os.replace clobbering a
      freshly-linked live claim after a release removed the file - no longer occurs.
  - id: AC3
    text: Lock-free readers (is_claimed, holder, claimed_units) remain correct because the
      record is published by an atomic os.replace, so a reader always sees a complete old-or-
      new record and never a half-written one; and all previously passing claim behaviors
      (capability refuse-vs-grant, live-claim refusal, stale reclaim, heartbeat, release,
      claimed_units) are unchanged.
  - id: AC4
    text: A selftest reproduces the race and proves the fix non-tautological - a churn clobber
      detector (many workers claim, verify they are the holder, release, at default staleness)
      asserts zero clobbers with the single-lock arbiter, and reverting to the split
      fresh/takeover paths turns it RED; the existing barrier fresh-unit race and stale-
      takeover race still pass, and the full gate is GREEN.
  - id: AC5
    text: The OTHER write paths - heartbeat and release - also run under the per-unit lock, so
      their read-modify-write cannot clobber a concurrent takeover either: a heartbeat of a
      claim taken over since it was last seen refuses instead of overwriting the new holder,
      and a release removes only if the worker is still the holder under the lock. A selftest
      fires a heartbeat against a concurrent stale-takeover and asserts the takeover's grant
      stands (the holder is the taker, not the heartbeater), and is non-tautological - the
      pre-fix lock-free heartbeat clobbers the takeover in a large fraction of rounds.
required_evidence: [unit]
rollback: git revert; the change is confined to the claim() function in .veldo/claim.py, its
  docstrings, one claim_ledger capability note (both copies), and a selftest block; the claims
  root lives outside git history, so reverting leaves no tracked residue.
---

## Intent

Close a class of mutual-exclusion defects in the fleet claim primitive found by the
independent reviews of the serialized lander (WARP-0704): a ledger WRITE path that runs
outside the per-unit lock can clobber a concurrent takeover, granting the same unit to two
workers. The claim() path had it (a lock-free fresh os.link racing a takeover's os.replace),
and so did heartbeat() and release() (each a lock-free read-modify-write). The fix routes
EVERY write path through one per-unit arbiter. Since the lander's land lock and every
worker's claim and heartbeat rest on this primitive, the fix is foundational.

## Context

Found while building WARP-0704 (Y4 of PLAN-0007). The lander's land lock is a claim on a
well-known unit, so the lander's at-most-one-lander guarantee inherits this defect. The fix
collapses the two paths into one: a single per-unit lock is held across the whole claim
decision (read the current record, refuse a live claim by another, otherwise publish with an
atomic os.replace). Readers stay lock-free because os.replace is an atomic rename. This is a
standalone hardening of WARP-0701, not a plan item; WARP-0704 lands on top of it.

## Notes

Reproduced before the fix with a churn clobber detector (16 workers, claim/verify-holder/
release, default staleness): 368 clobbers of a live just-granted claim; and a heartbeat-vs-
takeover probe clobbered the takeover in ~46% of rounds. After the fix: zero in both, across
~1.2M claim operations. claim, heartbeat, and release now share one _unit_lock context
manager and publish via one atomic _publish helper (os.replace), so the design is also
simpler (one arbiter, not a split). The lock file (path + .lock) is created per unit and is
not itself a claim record (it is not a .json file, so claimed_units ignores it). Contention
on the lock occurs only when workers race for the SAME unit, which is exactly when
serialization is needed; distinct units use distinct lock files and never contend.
