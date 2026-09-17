# VELDO-0017 proof

Implementation commit: 3d1e05c. Gate GREEN there (selftest 5198 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/entity_contract.py`, a pure contract organ: the identity envelope every new durable entity
carries (R04, R22) with the scope revision kept apart from the concurrency version; six lifecycle
vocabularies (R05, R06, R11, R13, R18, R65) as declared edges with named entry predicates and
terminal states with no exits; the ownership cardinality registry (R04, R10, R13, R18, R65) with its
refusals; the alias rules (R04) over the repository's own historical identifiers; and
`admit_unit_artifact`, which calls the installed `claim.unit_id_problem` before any artifact write
(R10, R73). It persists and allocates nothing.

## Driven

`drive.py` records one run of suite 30 as `driven.json`: 29 rows, 29 passed, 4 DRIVEN rows, the four
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it.

## Approval

VELDO-0017 is a high-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at 7dac59d and found seven reproducible problems (identity swapped under a
transfer, duplicate uuids uncounted, retry accepting absent scope digests, mutable provenance, terminal
links replaceable, a list reference crashing the ownership walk, and a falsifier not driven as one
mutant). Each is fixed and pinned with the reviewer's reproduction in suite 30. The fixes carry no
second Codex pass (one review per landing until 2026-09-22).
