# VELDO-0019 proof

Implementation commit: aa8f0ee. Gate GREEN there (selftest 5246 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/graph_contract.py`, a pure contract organ: the union of the five R14 edge families and its
acyclicity, independent of the release membership forest; dependency resolution to exact accepted
revisions or completion receipts, never a status string; the reverse-closure invalidation an amended
or withdrawn prerequisite causes (R14, R39); and the decision bindings, settlement and observation
freshness rules that decide whether a governing decision authorizes anything (R40, R71).

## Driven

`drive.py` records one run of suite 32 as `driven.json`: 25 rows, 25 passed, 4 DRIVEN rows, the four
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it.

## Approval

VELDO-0019 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at 0a9ba90 and found eight reproducible problems (labels counted as
authenticated reviewers and machine names accepted as deciders, settled decisions losing their
invalidation edges, alias and uuid references splitting one node, settlement without any framing
digest, resolution without an exact revision, observations without source or subject authorizing, a
NaN timestamp reading as fresh, and rewritten completed history passing the checker). Each is fixed and
pinned with the reviewer's reproduction in suite 32. The fixes carry no second Codex pass (one review
per landing until 2026-09-22).
