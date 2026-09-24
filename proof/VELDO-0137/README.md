# VELDO-0137 proof: policy_check reads a digest-form spec revision

`policy_check.spec_revision_stale` read every proof's `spec_revision` with `int()`. VELDO-0050 writes
it as `sha256:` and the digest of the exact spec bytes, so every factory proof counted as stale, and
because the check reads every manifest in the repository, one such proof on trunk refused every later
`policy_check` run there. `policy_check.py` is a protected path; the owner approved this change
(Telegram 29057 asked, 29058 "Approved", 2026-09-24).

## The change

A digest-form revision is judged by `_digest_revision_stale`: the proof is current when its digest
equals the SHA-256 of the spec document committed at the proof's own implementation commit (read
through `_git_process`: `git ls-tree` for the one spec file of that id, then `git show`), and the
spec's declared `revision` has not been raised since that commit. A commit that is not a full object
id, a missing or ambiguous spec file, a Git refusal, an unparsable front matter and a spec with no
readable front matter at the commit are all stale (fail closed; the last was a review finding, fixed). Integer-form revisions are judged exactly as before. Both copies are byte-identical.

## Rows

Suite `68_veldo_0137_policy_revision` (2 rows, about 0.2 s) drives the real `policy_check` over a
temporary Git repository laid from this tree's `.veldo/` modules, with the module under test copied
from its production anchor.

| Criterion | Row |
|-|-|
| AC1 | `policy/digest-revision-current`: a digest-form proof bound to its commit is current before and after a committed History-only edit, beside a current integer proof |
| AC2 | `policy/digest-revision-stale`: a raised declared revision makes both forms stale; a digest naming no committed spec, a short commit, an absent commit and a committed spec with no readable front matter are each stale |

## Red record

`red-at-cae421a.json`: the current suite over the production tree at cae421a. The current-proof row
is red by assertion (the fresh digest proof and the History-edited one both counted stale); the
stale-proof row is green there because the old check counts every digest proof as stale, so that
row's teeth are its mutations.

## Mutations

Finding 137 in `scripts/check_teeth_mutations.py`, 5 cases, each red on its named row by assertion,
baseline green: `policy-digest-read-as-integer` (AC1's declared falsifier) and `policy-digest-bound-to-head`
red the current-proof row; `policy-digest-binding-unchecked` (AC2's declared falsifier) and
`policy-digest-revision-raise-ignored` red the stale-proof row, and `policy-digest-no-front-matter-current`
(the review finding put back: no front matter read as an empty mapping) reds it too.
