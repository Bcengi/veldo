# VELDO-0099 proof after round five

Implementation and mutation-driver commit: 6e1179560b8871014d059e6322d2bc523e66ec0d.
The specification remains ready for external independent review. No self-approval,
landing, or push is claimed. Engine and pack files are unchanged.

## Changes with file and lines

- scripts/suites/24_veldo_0007_install_and_run.py:41-73 compares entry kind,
  content digest, size, symlink target and existence, without timestamps. Both
  sandbox and live observations use this inventory. AC4 labels at 1027 and 1076
  state the same content-only claim.
- scripts/suites/24_veldo_0007_install_and_run.py:165-168 copies the whole common
  directory except worktrees/. The store allowlist is gone. Lines 304-332 retain
  separate private-state copying, config normalization, alternate materialization
  and containment checks. The redundant separate config copy is removed.
- scripts/suites/24_veldo_0007_install_and_run.py:485-524 drives actual split-index
  timestamp refreshes against both inventories, preserves corruption detection,
  and compares source and copied common-store contents in both shapes. Each run
  creates an unpredictable future-store name, so fidelity cannot be satisfied
  by enumerating known stores. Normalized configs are checked separately.
- proof/VELDO-0099/drive.py:92-137 adds allowlist and timestamp regressions;
  lines 184-334 add real AC4 clean split-index runs, branch-reflog deletion,
  random copied-file deletion, and reflog deletion with a split index. Each
  deletion must name its victim in the sandbox row; original source bytes survive.
- specs/VELDO-0099-worktree-git-shape.md:58-76 defines the complete copied set,
  content comparison and driven cases. Lines 158-166 record the boundary.
- proof/VELDO-0099/manifest.json, driven.json, baseline-driven.json, gate-round-five-*.log,
  ready-check.txt, sibling-search.txt and log-redactions.json bind current evidence,
  full row labels, commands, source digest, commits and disclosed log substitutions.
  Historical gate logs remain historical evidence. specs/index.md regenerated
  without a content change.

## Full gates before and after, both shapes

Every invocation is ./scripts/verify.sh, exit 0. No source or proof edits occurred
while these gates ran. Both shapes used the same commit for each pair.

| Run | Commit | Selftests | Gate |
| --- | --- | --- | --- |
| Before, assigned linked checkout | 0f69276 | 4838 passed, 0 failed | GREEN |
| Before, disposable primary checkout | 0f69276 | 4838 passed, 0 failed | GREEN |
| After, assigned linked checkout | 6e11795 | 4842 passed, 0 failed | GREEN |
| After, disposable primary checkout | 6e11795 | 4842 passed, 0 failed | GREEN |

All four gates passed first-use integration and all 8 required catalog checks,
with 15 not applicable, 0 waived and 0 undeclared. Logs are named
 gate-round-five-{before,after}-{linked,primary}.log. Disposable primary repositories
were created with git clone --no-hardlinks --no-checkout from this checkout and
 git checkout --detach of the exact commit. No existing other branch or worktree
was modified.

## Defects reproduced before implementation

baseline-driven.json records the driver prepared outside the repository and run
against 0f69276 before any edits. Both normal AC4 controls passed 14/0. In each shape,
a stage mutation targeting a branch reflog still passed 14/0: the omitted store
never entered the sandbox. A clean split index failed 12/2, naming sharedindex.*
in both the sandbox and live rows. These are diagnostic results, distinct from
the ordinary full baseline gates, which were green.

To reproduce, create an isolated primary checkout of 0f69276 and run the current
 proof/VELDO-0099/drive.py with that checkout's absolute path followed by --baseline.
Baseline mode expects the old suite's row count and the two demonstrated defects;
it is not an option for validating the fixed suite.

## Every driven mutation and its red row

Command: python3 proof/VELDO-0099/drive.py. driven.json records every full label,
expected red-row set, source hash, commit and random victim. The live suite digest
is unchanged. These mutation diagnostics are not selected-suite gate claims.

| Mutation | Passed/failed | Red rows |
| --- | --- | --- |
| Restore .git directory requirement | 16/1 | Linked copied substrate resolves inside its sandbox |
| Substitute clone of HEAD | 15/2 | Both shapes: dirty stage/index/untracked copy fidelity |
| Restore shared live inventory | 15/2 | Both shapes: sibling staging leaves live inventory unchanged |
| Inventory only sandbox working tree | 15/2 | Linked private and common metadata write is observed |
| Restore common-store allowlist | 15/2 | Both shapes: whole common directory except worktrees retains content |
| Restore timestamp comparisons | 15/2 | Both shapes: split index timestamp refresh leaves both inventories unchanged |
| Treat alternate quotes as filename characters | 13/4 | Both shapes, relative and absolute C-quoted alternate has objects and copy fidelity |
| Omit copied veldo/ ledger | 15/2 | Both shapes: copied claims and runs retain bytes and claim deletion is observed |
| Skip config normalization | 15/2 | Both shapes: redirected config and alternates are isolated and original edit survives checkout-index |
| Copy sibling private state | 13/4 | Both shapes: 50 concurrent copies have zero raises and no sibling state; whole common directory except worktrees retains content |
| Raise on vanished entry | 16/1 | An entry vanishing after enumeration does not raise |
| Omit primary sharedindex observation | 16/1 | Primary split index corruption is observed |
| Skip alternate rewriting | 11/6 | Both redirected-config rows and all four quoted-alternate rows |
| Restore caller identity reads | 0/1 | Checkout shape controls block completes rather than raising |
| Actual AC4 directory requirement | Primary 14/0, linked 13/1 | Linked THE OBSERVATION'S OWN SUBSTRATE |
| Actual AC4 shared live inventory during sibling staging | Each shape 13/1 | THIS repository is untouched |
| Actual AC4 stage writes copied common store | Each shape 13/1 | NOT ONE BYTE of the repository under check changed |
| Actual AC4 stage deletes copied claim | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming veldo/claims/probe.json |
| Actual AC4 shared live inventory during sibling heartbeat | Each shape 13/1 | THIS repository is untouched |
| Actual AC4 stage deletes branch reflog | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming logs/refs/heads/round-five-probe |
| Actual AC4 stage deletes randomly selected copied file | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming the selected file |
| Actual AC4 stage deletes branch reflog with split index | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming logs/refs/heads/round-five-probe |

Unmutated layout and review controls are 17/0 each, with empty HOME and
XDG_CONFIG_HOME, system/global git config disabled, and no caller identity.
Review controls include 50 copies per shape during concurrent sibling staging.
Real sharedindex corruption is detected in both shapes; removing primary
sharedindex observation makes the primary corruption row red.

Actual AC4 control, sibling-staging, redirected-config, sibling-heartbeat and
clean split-index cases are each 14/0 in both shapes. The heartbeat invokes the
real claim module from a disposable sibling subprocess during the live inventory
window. Claims remain held until explicitly released by the driver.

For random deletion, the driver samples an actual copied common directory,
excluding worktrees/ and the named reflog, ledger, split-index and normalized
config/index/HEAD controls. No positive store list selects candidates. It records
the selected path, then injects deletion into the copied stage after its real
compose-install-gate work. Requiring that the path appear in the sandbox row
proves the deletion was inventoried. Source bytes are asserted unchanged.

Final committed-drive victims:

- primary: objects/98/7a57c3dbbd0a3f11835d7a94b6780c25a3f70f
- linked: objects/27/b287e4fbc39dd54d37a040cd94c93734204ee4

The initial preview drive failed its expected-row assertion because copying
sibling state now also reds both whole-store fidelity rows. The expected red set
was corrected, then the complete preview and committed-implementation drives
passed. A selected suite diagnostic reported 103/0 and exited 2 by design; it is
not full-gate evidence and does not support the manifest's gate claims.

## Snapshot boundary and next review

The sandbox surface is the working tree, private git directory and whole common
directory except worktrees/, including materialized alternates. Shared live stores
remain excluded because their writers cannot be attributed to this stage. The
live surface is this checkout's working tree and private git state. Configs and
pointers are normalized before the stage runs. This is a before-and-after content
inventory, not a process trace or operating system confinement.

A fifth independent review could still find writes to arbitrary absolute paths,
external working-tree symlink targets or shared live stores; transient writes
restored before the second snapshot; identical-byte rewrites; timestamp-only or
permission-only changes; or copy races that produce an inconsistent snapshot.
Future path-redirection semantics that the retained normalization and containment
checks do not understand are also outside what these driven cases establish.
The separate sandbox HOME inventory does not extend coverage to the host filesystem.
Closing a named-store omission by copying the whole common directory does not
establish process-attributed write tracing.

## Packaging

ready-check.txt revalidates the ready spec. sibling-search.txt records the suite-wide
search for .git directory assumptions; remaining matches are explicit fixture checks.
Only the synthetic pkg/dirty.py diagnostic is replaced in gate logs;
log-redactions.json records raw/stored digests and line numbers. Gate outcomes and
failure rows are retained. Raw logs are in /tmp/veldo-0099-round5/.

Gate byproducts .veldo/events.jsonl and .veldo/last_verify are restored with
 git checkout -- .veldo/last_verify .veldo/events.jsonl before proof commits.
The external reviewer owns independent review and the real landing stamp.

## Final gate with refreshed proof

The full ./scripts/verify.sh at 640a65d66ed771d46ceeae393f40dac109ba0ad1 in the assigned linked
checkout exited 0: GREEN, 4842 passed, 0 failed; first-use integration passed;
8 required catalog checks passed, 15 not applicable, 0 waived, 0 undeclared.
The output is gate-round-five-final.log. This final receipt changes proof records
only and does not claim a landing stamp or a new implementation verification.
The two gate byproducts are restored before committing the receipt.
