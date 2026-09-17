# VELDO-0099 proof after round eight

Implementation and driver commit: 754757683fca4a4598caeefea6c5f405c6b0b1a1.
The specification remains ready for external independent review. No self-approval,
landing, or push is claimed. Engine and pack files are unchanged.

## Changes with file and lines

- scripts/suites/24_veldo_0007_install_and_run.py:45 classifies sockets, FIFOs,
  character devices, and block devices. The inventory at line 54 records each
  special entry's kind and "skipped by metadata copy" without reading its content.
  The copy helper at line 171 omits those entries, including metadata symlinks
  that resolve to special files. Regular metadata still uses copy2.
- scripts/suites/24_veldo_0007_install_and_run.py:125 includes
  logs/refs/{bisect,worktree,rewritten} in primary checkout private state,
  alongside the existing private refs. The comment retains the
  [git-worktree](https://git-scm.com/docs/git-worktree#_refs) citation for the
  per-worktree ref boundary and the gitrepository-layout citation.
- scripts/suites/24_veldo_0007_install_and_run.py:448 adds controls in both
  shapes: a bound socket and FIFO must be inventoried and omitted from copies;
  deleting Git-created reflogs in all three private namespaces must be observed.
- proof/VELDO-0099/drive.py:178 restores the two defects as paired regression
  mutations. Line 298 binds fsmonitor--daemon.ipc during real AC4 execution;
  line 315 deletes a Git-created logs/refs/worktree/round-eight-probe entry
  during the live stage. The primary omission mutation reproduces the old miss.

## Round eight mutations and red rows

Command: python3 proof/VELDO-0099/drive.py, exit 0, at the commit above.
Full labels, suite digest, and each disposable checkout's HEAD are in driven.json.
These are mutation diagnostics, separate from the full canonical gate evidence.

| Case | Passed/failed | Red rows |
| --- | --- | --- |
| Bound socket with fixed copy | Each shape 14/0 | None; all AC4 rows execute |
| Restore copy2 on the bound socket | Each shape 0/1 | VELDO-0007 AC4: the block ran to completion rather than raising (OSError(6, 'No such device or address')) |
| Restore special-file copying in regression controls | 2/2 | Primary and linked socket and FIFO are inventoried by skipped kind and not copied |
| Delete private worktree reflog during live stage | Each shape 13/1 | THIS repository is untouched; names git-dir/logs/refs/worktree/round-eight-probe |
| Omit private reflogs from primary selection | 3/1 | Primary private reflog deletions are observed |
| Live reflog deletion with primary selection omitted | Primary 14/0, linked 13/1 | Reproduces the primary miss; linked THIS repository is untouched remains red |

The unmutated special-file/private-reflog controls are 4/0. All earlier layout,
copy-fidelity, nested-repository, sparse-rule, common-store, alternates, split-index,
sibling-attribution, and identity mutations are re-driven in driven.json with
asserted expected red rows. Unmutated layout controls are 17/0, earlier review
controls 19/0, nested controls 20/0, and alternates-name controls 2/0.

The first driver attempt at ed1d4a3 stopped in fixture setup: updating a ref to
its unchanged value did not recreate its deleted reflog. No completed driver
result was claimed. Commit 7547576 creates a fresh ref before each case and
keeps these new controls out of the historical --baseline mode.

## Both full gates

Both commands were ./scripts/verify.sh, exit 0, at the implementation/driver
commit above. The assigned linked checkout and a disposable primary clone used
identical committed source. No source or proof edits occurred during either gate.
Both reported 4870 passed, 0 failed, first-use integration passed, and all 8
required catalog checks passed (15 not applicable, 0 waived, 0 undeclared).
Full outputs are gate-round-eight-linked.log and gate-round-eight-primary.log.

The primary fixture was made with git clone --no-hardlinks --no-checkout from
the assigned checkout, followed by fetching and checking out the exact commit
detached. No existing other worktree or branch was modified. Gate output was
captured outside the observed checkout before packaging this proof.

The linked checkout's last_verify and events.jsonl are gate byproducts, restored
before the proof commit and excluded from every task commit. Previous gate logs
and baseline-driven.json remain historical records. log-redactions.json binds raw
and stored gate logs; only the preexisting synthetic pkg/dirty.py diagnostic is
replaced, with every result and failure row retained.

## Observation boundary

This remains a before-and-after content inventory, not a process trace or filesystem
confinement. Runtime special files are inventoried by kind but omitted from metadata
copies; no content-fidelity claim covers them. Nested repositories stand down only
the inventory rows; independent network/process checks continue. Absolute paths,
external symlink targets, shared live stores, and writes restored before the second
snapshot remain outside the inventory claim. The queued Landlock follow-up is
unchanged and is not implemented here.
