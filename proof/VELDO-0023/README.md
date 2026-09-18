# VELDO-0023 proof

Implementation commit: 7009587. Gate GREEN there (selftest 5343 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/control_store.py`, the one writer of domain state: a local SQLite authority at
`<git-common-dir>/veldo/control/control.sqlite3` with foreign keys and full durability read back after
opening, refusing network or undeterminable filesystems; five registered commands whose entity versions,
signed journal record, consumed nonce, reservation rows and effect obligations commit in one transaction
or not at all; identical retries return the original result and altered content under one id is a
content conflict (R21, R22). `.veldo/control_replay.py`, the reader that verifies the whole signed chain
(encoding, sequence, predecessor digests, record digests, signatures) before rebuilding state
deterministically, importing only hashlib and json (R22, R53). Signing and verification are callables
the caller supplies (OpenSSH in production); the store holds no key.

## Driven

`drive.py` records one run of suite 36 as `driven.json`: 17 rows, 17 passed, 3 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The crash matrix and the races run real writer processes
against real SQLite files under a temporary directory; the journal rows sign through the installed
ssh-keygen.

## Approval

VELDO-0023 is a critical-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.

## Review

Codex reviewed the branch at a694369 and found four reproducible problems (reservations, effects and consumed
nonces absent from the signed record so a rebuild lost spend holds and replay protection, receipt references
passed as an iterator signed as one list and stored as another, a read-only open that returned a writable
handle, and filesystem qualification judged at a symlink rather than its target). Each is fixed and pinned
with the reviewer's reproduction in suite 36. The fixes carry no second Codex pass (one review per landing
until 2026-09-22).
