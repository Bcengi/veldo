# VELDO-0016 proof

Implementation commit: a970266. Gate GREEN there (selftest 5142 passed, 0 failed) in the plan-0019
branch worktree. Author: Ava (Claude); Codex reviews only until 2026-09-22 by Dmitry's quota ruling, so
this is the first Package A item written by the reviewer's counterpart and reviewed by Codex once.

## What landed

**AC3, the loader.** `.veldo/contract_loader.py` is the one tri-state architecture contract loader:
absent, valid or invalid, with a six-word kind taxonomy and the required flag in force. Presence is
decided by lexists and only a regular file is ever opened, so a directory, a dangling link, a FIFO or a
socket at the path is present, unreadable and never read. `validate_checks` wraps it as
`load_contract_state`, `load_repo_contract` (raises `ContractRefused` for every state but valid and
optional absence) and `check_arch`. Fifteen consumers refuse by name, registered in
`policy_contract.LOADER_ADAPTERS` and driven as a product of adapters, states and flags. The
repository declares its contract required with one policy line.

**AC1, activation.** `POLICY_BOUNDARIES` names the six governed boundaries and the decision record,
version and option that may activate each; `activation_authority` accepts only a decided,
person-decided, version-bound record choosing that option with its tier's bound supporting reviews.
Six records exist, all drafts; nothing is activated.

**AC2, the runner's obligations.** Fifteen R43/R44 obligations with empty test slots; the profile is
ineligible until every slot is filled; retirement needs four proofs. Architecture contract revision 2
adds the `project_runner` area and one scoped exception clause, effective only through activation.

**AC4, the boundary table.** One refusing predicate per clause (R21, R35, R46, R50, R53), each with a
seeded violation the suite drives.

## Driven

`drive.py` records one run of the fragment as `driven.json`: 272 rows, 272 passed, 8 DRIVEN rows, the
four declared falsifiers among them, each applied to a copy and required to turn its named row red
while the unmutated copy passes it.

## Approvals

Dmitry approved the protected policy line and contract revision 2 over Telegram on 2026-09-17
(message 27900); `approval-dmitry.json` binds the first to commit 2106b03, the contract carries the
second. Recorded once, attributed to the channel the answer arrived on.

## Pins moved on the record

Suite 12's read-closure counts (25 roots over 11 patterns to 29 over 12, the policy line the loader
reads, class OPENER); suite 01's area count (10 to 11); suite 07 accepts the contract validator's
by-name refusal of an unknown budget kind, which the loader now reaches first.
