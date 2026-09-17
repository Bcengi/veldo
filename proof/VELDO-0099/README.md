# VELDO-0099 proof after round seven

Implementation and driver commit: 8be2b35301a64ef5602a5f9f4e3a207dbde5f717.
The specification remains ready for external independent review. No self-approval,
landing, or push is claimed. Engine and pack files are unchanged.

## Changes with file and lines

- scripts/suites/24_veldo_0007_install_and_run.py:1039 separates the six inventory
  rows from the eight independent process and network rows. Only the inventory
  helper at line 1046 records nested-repository stand-down. The process helper at
  line 1144 still inspects the current stage, and line 1279 launches its real child
  from an empty temporary directory that requires no repository copy.
- scripts/suites/24_veldo_0007_install_and_run.py:110 selects checkout-owned state
  using Git's documented per-worktree boundary, cited in the comment. The existing
  index, sharedindex.*, HEAD and uppercase pseudorefs, operation state, logs/HEAD,
  private refs, and config.worktree selection now includes info/sparse-checkout
  and its lock. Line 523 drives sparse-rule content changes in both shapes.
- scripts/suites/24_veldo_0007_install_and_run.py:1344 extends the existing nested
  fixture controls to require reaching the process helper while copying and nested
  git operations remain blocked and the original dirty submodule bytes survive.
- proof/VELDO-0099/drive.py:110 removes sparse selection as a regression mutation;
  line 150 restores the old stand-down short circuit. Line 245 drives a nested
  marker alone, real start_new_session=True injection, an uncalled network probe,
  and sparse-rule writes during the real live observation in both checkout shapes.
- specs/VELDO-0099-worktree-git-shape.md:184 records these two corrections without
  changing the acceptance criteria. This bundle refreshes the proof; earlier gate
  logs and baseline-driven.json are historical records.

## Both full gates

Both commands were ./scripts/verify.sh, exit 0, at 8be2b35301a64ef5602a5f9f4e3a207dbde5f717.
The assigned linked checkout and a disposable primary clone used identical committed
source. No source or proof edits occurred during either gate. Both reported
4866 passed, 0 failed, first-use integration passed, and all 8 required catalog checks
passed (15 not applicable, 0 waived, 0 undeclared).

The primary fixture was made with git clone --no-hardlinks --no-checkout from the
assigned checkout, followed by git checkout --detach of that exact commit. No
existing other worktree or branch was modified. Full outputs are
 gate-round-seven-linked.log and gate-round-seven-primary.log.
The first linked invocation was red in first-use integration: its mutated fixture
reported 4865/1 and its untouched control 4866/0. The live-inventory row failed;
the integration report truncates its label before the changed entries. The same
implementation passed on a subsequent linked invocation with no concurrent gate
or mutation jobs. This does not identify the cause of the first failure. The full
red result is retained in gate-round-seven-linked-first-red.log. The retry set
VELDO_FIRST_USE_KEEP=1; check_first_use.py does not read that variable, so it had
no effect on fixture retention or the checks.

The linked checkout's last_verify and events.jsonl are gate byproducts, restored
before the proof commit and excluded from every task commit.

## Round seven mutations and red rows

Command: python3 proof/VELDO-0099/drive.py, exit 0, at 8be2b35301a64ef5602a5f9f4e3a207dbde5f717.
The suite digest and every clone's HEAD are bound in driven.json. These are mutation
diagnostics; the full gates above provide gate evidence. Both shapes use the real
stage and real compose-install-gate path for the applicable AC4 rows.

| Case | Passed/failed | Red rows or recorded stand-down |
| --- | --- | --- |
| Empty untracked .gitmodules alone | Each shape 8/0 | Inventory stand-down recorded and printed; all eight process/network rows pass |
| Nested marker plus start_new_session=True | Each shape 6/2 | STARTS NO DETACHED PROCESS; THE LAUNCH IS DRIVEN; inventory still stands down |
| Nested marker plus urlopen identifier | Each shape 7/1 | it makes no network call; inventory still stands down; probe is never called |
| Restore the early-return behavior | 10/10 | All ten nested fixture stand-down rows fail because the process helper is skipped |
| Change sparse rules during the live run | Each shape 13/1 | THIS repository is untouched, naming git-dir/info/sparse-checkout |
| Remove primary sparse selection | 18/1 | Primary sparse-checkout rule changes are observed |
| Live sparse writes with primary selection removed | Primary 14/0, linked 13/1 | Reproduces the primary miss; linked live row still names git-dir/info/sparse-checkout |

## Prior mutations re-driven

| Mutation | Passed/failed | Red rows |
| --- | --- | --- |
| Restore .git directory requirement | 16/1 | Linked copied substrate resolves inside its sandbox |
| Substitute clone of HEAD | 15/2 | Both shapes: dirty stage/index/untracked copy fidelity |
| Restore shared live inventory | 15/2 | Both shapes: sibling staging leaves live inventory unchanged |
| Inventory only sandbox working tree | 15/2 | Linked private and common metadata write is observed |
| Restore common-store allowlist | 17/2 | Both shapes: whole common directory except worktrees retains content |
| Restore timestamp comparisons | 17/2 | Both shapes: split index timestamp refresh leaves both inventories unchanged |
| Treat alternate quotes as filename characters | 15/4 | Both shapes, relative and absolute C-quoted alternate has objects and copy fidelity |
| Omit copied veldo/ ledger | 17/2 | Both shapes: copied claims and runs retain bytes and claim deletion is observed |
| Skip config normalization | 17/2 | Both shapes: redirected config and alternates are isolated and original edit survives checkout-index |
| Copy sibling private state | 15/4 | Both shapes: 50 concurrent copies have zero raises and no sibling state; whole common directory except worktrees retains content |
| Raise on vanished entry | 18/1 | An entry vanishing after enumeration does not raise |
| Omit primary sharedindex observation | 18/1 | Primary split index corruption is observed |
| Skip alternate rewriting | 13/6 | Both redirected-config rows and all four quoted-alternate rows |
| Restore caller identity reads | 0/1 | Checkout shape controls block completes rather than raising |
| Actual AC4 directory requirement | Primary 14/0, linked 13/1 | Linked THE OBSERVATION'S OWN SUBSTRATE |
| Actual AC4 shared live inventory during sibling staging | Each shape 13/1 | THIS repository is untouched |
| Actual AC4 stage writes copied common store | Each shape 13/1 | NOT ONE BYTE of the repository under check changed |
| Actual AC4 stage deletes copied claim | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming veldo/claims/probe.json |
| Actual AC4 shared live inventory during sibling heartbeat | Each shape 13/1 | THIS repository is untouched |
| Actual AC4 stage deletes branch reflog | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming logs/refs/heads/round-five-probe |
| Actual AC4 stage deletes randomly selected copied file | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming the selected file |
| Actual AC4 stage deletes branch reflog with split index | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming logs/refs/heads/round-five-probe |
| Skip nested repository detection | 0/20 | Both shapes, all five markers: AC4 stand-down is recorded, printed, and never passed; original edit survives with no copy or nested git operations |
| Match alternates basename anywhere | 0/2 | Both shapes: branch and reflog named alternates copy cleanly |

Unmutated layout controls are 17/0 and review controls are 19/0. Nested controls
are 20/0 and alternates-name controls are 2/0. The layout fixtures retain the empty
HOME and no-caller-identity environment. All earlier expected red rows were observed.
Normal AC4, sibling staging, redirected config, sibling heartbeat, clean split
index, and branch/reflog named alternates remain 14/0 in both shapes. Random copied
file deletion records its victim and the red sandbox row names it. Original bytes
survive every destructive sandbox mutation.

## Observation boundary

This remains a before-and-after content inventory, not a process trace or filesystem
confinement. Nested repositories stand down only the inventory rows; the independent
network/process checks continue. Absolute paths, external symlink targets, shared
live stores, and writes restored before the second snapshot remain outside the
inventory claim. The previously specified Landlock follow-up is not implemented.

The comment's sources are [git-worktree](https://git-scm.com/docs/git-worktree) and
[gitrepository-layout](https://git-scm.com/docs/gitrepository-layout).
log-redactions.json binds raw and stored gate logs; only the preexisting synthetic
pkg/dirty.py diagnostic is replaced, with every result and failure row retained.
