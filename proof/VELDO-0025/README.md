# VELDO-0025 proof

Implementation commit: b89f9f3. Gate GREEN there (selftest 5371 passed, 0 failed) in the plan-0019 branch
worktree. Author: Ava (Claude); one Codex review per landing until 2026-09-22 by Dmitry's quota ruling.

## What landed

`.veldo/control_membership.py`: the authority's administrative command path. Six transitions
(enroll, change roles, revoke membership, grant, supersede and revoke delegation) register into the
control store and commit atomically with the journal, the nonce and the one authority-versions
entity every command names as its expected version. A command is admitted only from an OpenSSH
envelope whose digest recomputes from the operation, target and complete parameters (an enrollment
public key among them), verified against the signer's active committed key at the store's current
membership and delegation versions (R36, R38); the accepted policy keeps membership changes to an
enrolled person holding membership_steward, refuses every self-grant, requires the enrollee's
co-signature, and preserves the owner bootstrap (R37). Delegated use is judged on every predicate
conjunctively and a delegation cached across its committed supersession is stale. Nothing is
enrolled in this repository.

## Driven

`drive.py` records one run of suite 38 as `driven.json`: 12 rows, 12 passed, 3 DRIVEN rows, the three
declared falsifiers among them, each applied to a copy of the module and required to turn its named row
red while the unmutated module passes it. The crash matrix and the races run real writer processes
against real SQLite files with real Ed25519 keys through the installed ssh-keygen under a temporary directory.

## Approval

VELDO-0025 is a critical-risk item with no protected paths; the spec asks for the owner's approval before
landing. The approval, when recorded, is `approval-dmitry.json` in this directory, attributed to the
channel it arrived on.
