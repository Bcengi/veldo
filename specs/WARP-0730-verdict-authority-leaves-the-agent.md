---
schema: veldo.spec/v1
id: WARP-0730
title: Nine rounds of forgery guards each bought exactly one spelling, because a predicate inside the agent's
  own process cannot stop that agent writing bytes - remove the capability instead of guarding it, so the
  gate marks ordinary work done and only the owner can sign off high risk
status: ready
risk: critical - this removes the guard the product's central claim rests on, and removing a guard is the
  move that most deserves suspicion. The danger in the permissive direction is that verdict authority moves
  somewhere weaker rather than nowhere, leaving forgery possible with the defence deleted. The danger in the
  strict direction is that ordinary items stop being able to ship at all, which is what the current
  critical-tier two-review requirement already does in practice: WARP-0725 has needed two independent
  reviews for days and has zero. It is critical rather than high because the change touches
  `.veldo/policy.yaml`, a protected path at floor high, and because getting it wrong reintroduces the exact
  defect the last nine rounds were spent on
owner: dmitry
human_approval: required
approved_by: dmitry
approved_at: 2026-08-01
approval_record: >
  GIVEN ON TELEGRAM, 2026-08-01, in a decision he asked for and then made explicitly. He was shown the
  diagnosis (the forgery guard defends a property that cannot hold from inside the process it defends
  against, which is why nine rounds each bought one spelling) and three options for where verdict authority
  should live: (1) he records verdicts, (2) nothing does except the gate, (3) both, with the gate handling
  ordinary work and his sign-off reserved for genuinely risky items. His answer, verbatim: "Three". Followed
  immediately by "But only high risk for human", which narrows option 3 and is incorporated below. He had
  already said, unprompted, "I agree we should cut forge guard for sure and loosen size requirements", and
  then "Continue working on Veldo".
  RECORDED, NOT PERFORMED. The agent writes down the decision the owner made and never makes one for him.
  Noted for a later reader: this is a Telegram instruction rather than a ticket transition, the same
  evidentiary standard accepted on WARP-0725 and WARP-0727, and accepted here because he initiated the
  rethink, asked for the options in writing, and chose between them by number.
lane: standalone
depends_on: []
placement: [enforcement]
footprint:
  - ".veldo/policy.yaml"
  - ".veldo/policy_check.py"
  - "engine/.veldo/policy.yaml"
  - "engine/.veldo/policy_check.py"
  - "packs/*/.veldo/policy.yaml"
  - "packs/*/.veldo/policy_check.py"
  - "specs/WARP-0730-verdict-authority-leaves-the-agent.md"
acceptance_criteria:
  - id: AC1
    text: >
      VERDICT AUTHORITY LEAVES THE AGENT ENTIRELY, and the property is stated once rather than defended
      route by route. No artifact an agent can write may, by itself, cause an item to be treated as
      reviewed, shipped, or mergeable. The gate is the authority for ordinary work and the OWNER is the
      authority for high risk. Concretely: `policy_check.main()` no longer blocks a push on
      `valid_verdict_for(HEAD)`, and the merge rule no longer names a verdict. What still blocks is the
      gate, and for protected paths a recorded owner approval bound to the commit, which is the one thing
      here an agent cannot produce. A selftest asserts the protected-path approval block still bites.
  - id: AC2
    text: >
      REVIEWS SURVIVE AND LOSE THEIR AUTHORITY, which is the whole point and the part most likely to be
      got wrong. Reviews still run and still produce findings; what changes is that a finding is something
      a human reads, never a token that marks work done. Nothing in this item deletes the ability to run a
      review, and a selftest asserts a review can still be requested and its findings recorded for a human.
      If this item is implemented by deleting reviews rather than by deleting their authority, it has
      failed.
  - id: AC3
    text: >
      HIGH RISK STILL STOPS FOR THE OWNER, and critical stops meaning something separate. Per his
      instruction "only high risk for human", the HUMAN gate is what narrows: nothing below the high tier
      stops for a person. **The `reviews` count in `risk_tiers` is NOT touched, and that is a correction
      made during the build.** That field is read only by `decision_review.py`, which adversarially
      challenges DESIGN DECISIONS and floors at one review by design; it has nothing to do with the code
      verdicts this item removes authority from. Changing it to satisfy "only high risk for human" was
      conflating two mechanisms, the selftest caught it (WARP-1106 AC5 and AC6 went red), and it is
      reverted. Critical decision records still require two independent reviews. A selftest asserts that
      changing a protected path still forces at least the high tier and therefore still requires a recorded
      owner approval bound to the commit.
  - id: AC4
    text: >
      THE MERGE RULE NO LONGER READS A VERDICT. The clause requiring "the verdict is pass or
      pass_with_notes with zero blocking findings" is removed, and what replaces it is the gate being green
      plus, where the tier demands it, a recorded and unexpired owner approval bound to this exact commit.
      Every other existing merge condition is retained verbatim; this item narrows one clause and widens
      nothing.
  - id: AC5
    text: >
      EVERY SHIPPED COPY MOVES WITH THE ENGINE, and there are more of them than the first draft of this
      footprint assumed. `engine/` AND all six packs carry their own `policy_check.py` and
      `policy.yaml`. The existing pack-drift selftests are the assertion and they caught the omission:
      ten of them went red when only the engine and the template were changed. Each pack keeps its own
      tier ladder (the templates use L4 independence where the engine uses L2); only the verdict clause
      and the verdict gate are synced.
  - id: AC6
    text: >
      THE ENTITLEMENT MACHINERY IS NOT DELETED BY THIS ITEM, and that restraint is deliberate. Removing the
      authority is what makes the guard unnecessary; deleting roughly 1,600 lines of it is a separate change
      with its own blast radius across fifteen files, and doing both at once would make a regression
      impossible to attribute. This item states the property. A follow-up removes the code once nothing
      depends on it. A selftest asserts the engine still imports and the gate still runs green with the
      machinery present but no longer authoritative.
required_evidence: [unit, baseline]
rollback: revert the commit. Policy is read at gate time and nothing persists, so reverting restores the
  previous tiers and merge rule immediately. Note that any item merged under the new rule while this was in
  force stays merged; the rollback restores the rule, not the history.
---

## Intent

Nine build rounds were spent stopping an agent forging a verdict. Each closed one spelling and the next
opened another: a path comparison, a work-tree relation, a pathspec-versus-glob divergence, an anchoring
mismatch, a symlink at the log's final component. The most recent fix, built 2026-07-31, closed a sixth
route and declared three more it cannot close.

That is not nine failures. It is one design error, found nine times. **A predicate that runs inside the
agent's own process cannot stop that agent writing bytes**, because the agent has the filesystem, the
repository and the interpreter. The declared limits in `log_entitlement` are the proof: a writer that never
imports the module, arbitrary in-process Python, and a `GIT_DIR` redirect are all named as uncloseable, and
they are uncloseable for the same reason every spelling was.

So the property to state is not "the log cannot be forged". It is **"no artifact an agent can write decides
anything"**. Under that property the forgery has no value, which is a stronger position than any guard,
and it costs nothing to defend because there is nothing to defend.

## What this changes, in one line each

- Ordinary work: the gate decides. A green `scripts/verify.sh` is done. No review verdict is consulted.
- High risk: the owner decides, exactly as today, with the approval recorded and bound to the commit.
- Critical: keeps the owner gate and the expanded checks, loses the two-review requirement that has never
  been met.
- Reviews: still run, still report, no longer certify.

## What this deliberately does not do

It does not delete `verdict_corpus.py`, `log_entitlement`, or the reconciler's append path. Those become
unnecessary rather than wrong, and unnecessary code is removed in its own item where a regression can be
attributed. See AC6.

It also does not touch `veldo-0725-entitlement-keys-on-identity`, the branch carrying the identity fix built
on 2026-07-31. That branch should be **abandoned rather than merged**: it closes a route in machinery this
item makes non-authoritative, and landing it would spend review effort defending something already
superseded.
