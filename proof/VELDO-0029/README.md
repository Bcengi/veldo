# VELDO-0029 proof

PLAN-0019 W14, revision 2. Author: Ava (Claude), under Dmitry's rule that when Codex is out the
author writes and Codex validates. Codex validates this item in the batch of 2026-09-22.

## Why this item exists, measured rather than argued

`control_store.control_db_path` decides which SQLite authority to open by reading `VELDO_CONTROL_DB`
from the environment, and otherwise by running `git rev-parse --git-common-dir` in whatever directory
the process happens to be in. Two throwaway repositories and one call show it:

```
standing in repoA  ->  .../repoA/.git/veldo/control/control.sqlite3
standing in repoB  ->  .../repoB/.git/veldo/control/control.sqlite3
VELDO_CONTROL_DB set ->  /tmp/anywhere-at-all/control.sqlite3
```

A command carries the repository it means, it is signed, and the signature verifies. Then this
decides where to write, from the caller's position rather than from the command. A correctly signed
command naming one repository can commit into another, and nothing in the chain notices, because
nothing in the chain ever compares the two. R20 is the design clause that says the coordinate comes
from the command.

Nothing today runs the authority as a service or across clones, so the two have never disagreed in
practice. It is a loaded gun rather than a wound, and it is why this item is first of the four.

## What landed

`.veldo/control_enrollment.py`, mirrored byte for byte into `engine/.veldo/`. One signed binding per
clone naming the repository, the domain, the store, the host and the authority generation.
`resolve_store(workspace, ...)` takes the workspace as a required argument, reads the binding that
workspace carries, and refuses by a name from a closed list of ten, handing back no path at all when
it refuses.

**Identity is two things, because one is not enough.** The repository's root commits, which a
different repository does not share, and a per-clone uuid written into that clone's own git common
directory at enrollment, which git never tracks and a fresh clone therefore does not have. A
directory replaced under the same path fails one or the other. The absolute path is recorded so a
person can read the error and is never an input to the decision.

## The defect the row caught before this item landed

Taking the workspace as an argument and running `git -C <workspace>` is not enough, and that is not
obvious. **`GIT_DIR` in the environment overrides `-C`.** With it set, the module's own
`git -C repoA rev-list --max-parents=0 HEAD` answered repoB's root commit while believing it had
named repoA, so the identity check compared the wrong repository against the binding.
`GIT_WORK_TREE`, `GIT_COMMON_DIR` and `GIT_OBJECT_DIRECTORY` do the same.

`_git` now strips every variable whose name begins `GIT_` from the child environment, **by prefix
rather than by a list of names**, because git grows more of them and a list of names goes stale
silently. That filter is the module's only reading of the environment and it never takes a value from
it: it only takes values away. The row asserts that sentence as well as the behaviour, by counting
`os.environ` in the source.

It was caught by the row and not by a review, and only because the row points four ambient sources at
a second repository that is real and really enrolled. A row that had pointed them at a directory that
did not exist would have passed.

## What the evidence is, and what it is not

Five rows in `scripts/suites/46_veldo_0029_enrollment.py`, over real git repositories built under a
temporary directory: two clones of different repositories, a linked worktree of the first, a
directory swapped for a clone of another repository with the old binding restored into it, a fresh
clone of the same repository with the binding restored but not the clone uuid, and a directory that
is not a repository at all. Every one of the ten refusal reasons is produced by a real binding and a
real workspace rather than a hand-built record, and the row asserts the list is **exhausted**, so a
reason added later without a case fails it.

Each declared falsifier is driven against a copy of the organ, plus one drive against the
repository's own file that rebuilds the pre-fix state the row caught:

| falsifier | mutation | result |
|---|---|---|
| AC1 | the signature check skipped | a binding edited after signing resolves |
| AC2 | resolution from the process's current directory | the answer moves to the other repository |
| AC2, pre-fix | `_git` stops stripping the GIT_ environment | AC2 red, the other four pass |
| AC3 | the repository identity check skipped | the swapped directory resolves |
| AC4 | the store returned alongside the problems | a caller receives a path it may not use |

The fifth row is the negative control: a copy carrying only an added comment, required to agree with
the original on all four cases the other rows turn on.

**What this is NOT.** It is not evidence that anything reaches the authority. This item answers WHICH
store and stops there. The local socket is VELDO-0107, the SSH relay VELDO-0108, and the unreachable
authority VELDO-0109.

**And a correction to an earlier reading of the danger.** `control_db_path` had NO CALLERS anywhere in
the repository: every place that opens the store passes an explicit path. So nothing was reaching the
wrong database. What existed was the means to, sitting where the next person to need a default would
find it. It is now closed: it requires an explicit path and derives nothing. An earlier version of
this file said `control_db_path` is still what `control_store` uses, which was wrong, and evidence
that overstates a danger is as bad as evidence that understates it.

**And the signer is a fixture.** The suite supplies an HMAC because the module holds no key material
and takes signing and verification as callables. The rows turn on the signature being CHECKED, not on
how strong it is. Key lifecycle is VELDO-0027, which is back in draft.
