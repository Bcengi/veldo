# VELDO-0024 proof

Implementation commit: e4d2490. Gate GREEN there (selftest 5359 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/control_replica.py`: every committed journal record becomes one signed immutable export (the
record, its signature and the BYTES of every referenced artifact) whose identity is a function of
sequence and record digest, published in order to `refs/veldo/audit` on the repository remote through
a local bare audit repository with a compare-and-swap lease; the acknowledgement is the remote's own
answer, persisted in the store's new publication cursor; success, dispatch and dependent publication
are withheld until then, a lost acknowledgement is reconciled against the exact remote ref under the
same identity, and a divergent remote pauses publication (R23, R26, R27). `.veldo/control_store.py`
gains the `publication` and `publication_control` tables and their store-owned cursor writes.
`.veldo/runstatus.py` renders the R23 surface read-only. `remote_contract_problems` names a local
remote as protocol-only; no live remote is provisioned and no host-loss survival is claimed.

## Driven

`drive.py` records one run of suite 37 as `driven.json`: 16 rows, 16 passed, 3 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The crash matrix and the races run real writer processes
against real SQLite files and real local bare Git remotes under a temporary directory.

## Approval

VELDO-0024 is a critical-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at c7fb61f and found six reproducible problems (off-host durability never enforced and
relative local remotes accepted, an audit commit reused by subject alone without checking its export or
signature, an upgrade that left existing journal history out of the replica, a remote rolled back behind
acknowledged history neither repaired nor paused, a persisted pause that stopped nothing, and a crash after
acknowledgement that skipped dispatch forever). Each is fixed and pinned with the reviewer's reproduction in
suite 37. The fixes carry no second Codex pass (one review per landing until 2026-09-22).
