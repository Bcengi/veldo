# VELDO-0099 proof after round nine

Implementation commit: 15a17ae. Both gates and all disposable checkout HEADs are
2e9f4e14beaf583eccff365834a9c7450c334dfb. The specification remains ready for
external independent review. No self-approval, landing, or push is claimed.

## Changes with file and lines

- scripts/suites/24_veldo_0007_install_and_run.py:54 adds optional nanosecond
  modification times to content, kind, size, target, and existence observations.
  Working-tree inventory at line 123 excludes the embedded git directory so it
  is observed separately as metadata. Both sandbox (line 134) and live (line 163)
  inventories use mtimes for working files and content-only for git roots. The
  sandbox HOME snapshots at lines 1181 and 1185 also observe mtimes.
- scripts/suites/24_veldo_0007_install_and_run.py:353 records and skips sockets,
  FIFOs, character devices, and block devices in working-tree copytree. Copy
  fidelity at line 397 excludes those explicitly omitted entries and compares
  ordinary bytes. Controls at line 475 bind sockets and create FIFOs in both
  working and metadata roots, requiring kind records and successful copies.
- scripts/check_first_use.py:150 gives its whole-repository copytree the same
  skip-and-record treatment. This is its only behavior change.
- specs/VELDO-0099-worktree-git-shape.md:15 adds check_first_use.py to the
  footprint. AC3 at line 62 and Notes at line 176 state the root-specific mtime
  boundary and the special-file copy behavior.
- proof/VELDO-0099/drive.py adds real repeated-write, HOME rewrite, working socket,
  live sharedindex corruption, and full first-use drives, plus paired regressions.

## Driven mutations and red rows

Final executed command:
python3 /tmp/veldo-nine-drive-fixed.py "$PWD"
Exit 0. That temporary driver was copied byte for byte to drive.py after the gates
and driver completed. Reproduce with python3 proof/VELDO-0099/drive.py. The driver
uses the same implementation commit in isolated primary and linked fixtures;
driven.json records every full row label, fixture HEAD, and the suite digest.
These are mutation diagnostics, separate from the canonical gate evidence.

| Case | Primary | Linked | Red rows |
| --- | --- | --- | --- |
| Stage rewrites existing CLAUDE.md with identical bytes before and during observation | 12/2 | 12/2 | NOT ONE BYTE of the repository; THIS repository is untouched; both name tree/CLAUDE.md |
| Restore content-only observation for that write | 14/0 | 14/0 | None; reproduces the missed write |
| Stage rewrites existing sandbox HOME sentinel with identical bytes | 13/1 | 13/1 | NOT ONE BYTE outside the repository; names .veldo-write-scope-sentinel |
| Restore content-only observation for HOME | 14/0 | 14/0 | None; reproduces the missed HOME rewrite |
| Clean split index | 14/0 | 14/0 | None |
| Corrupt sharedindex during live stage | 13/1 | 13/1 | THIS repository is untouched; names git-dir/sharedindex.* |
| Bound metadata socket | 14/0 | 14/0 | None |
| Bound working-tree socket | 14/0 | 14/0 | None |
| Restore ordinary working-file copy on bound socket | 0/1 | 0/1 | AC4 block ran to completion rather than raising; copy fails on working.ipc |
| First-use with bound sockets and FIFOs in metadata and working tree | exit 0 | exit 0 | None; full nested suite 4870/0 |
| Restore ordinary first-use copytree with endpoints present | exit 2 | exit 2 | FIRST USE: CANNOT ANSWER; copy cannot read runtime endpoints |

All original and earlier review mutations are re-driven. In particular, restoring
metadata timestamps reds both split-index timestamp-refresh controls, and omitting
sharedindex from primary inventory reds the primary split index corruption control.
The clean layout, earlier review, nested, alternates-name, and special/private-reflog
controls remain 17/0, 19/0, 20/0, 2/0, and 4/0 respectively.

In a primary checkout, first-use explicitly logs skipping the socket inside .git.
In a linked checkout, private metadata is outside the first-use source tree; its
socket is handled by the AC4 metadata copier. In both shapes first-use explicitly
logs the skipped working-tree socket and FIFO. The record asserts skip logs only
for endpoints physically inside that copy's source tree.

Round nine driver setup history:
- The first attempt at 2e9f4e1 stopped at the HOME probe: the injected stage used os without importing it. No complete driver result is claimed for that attempt.
- A corrected temporary driver was interrupted to fix its skip-record assertion for linked checkouts: private metadata is outside the tree copied by first-use, so only in-tree endpoints must appear in that copy log. The HOME probe was also restricted to the observation sandbox.
- The final temporary driver is copied byte for byte to proof/VELDO-0099/drive.py after the gates finish. Its command and both gate commits are recorded separately.

## Both canonical gates

Both commands were ./scripts/verify.sh, exit 0, at 2e9f4e1. The assigned linked
checkout and a disposable primary clone ran identical committed implementation.
No source or proof files changed during either gate. Both reported 4870 passed,
0 failed, first-use integration passed with 4870/0, and all 8 required checks
passed (15 not applicable, 0 waived, 0 undeclared). Full logs:
gate-round-nine-linked.log and gate-round-nine-primary.log.

The primary fixture used git clone --no-hardlinks --no-checkout of this checkout,
then detached checkout of the exact commit. Existing other branches and worktrees
were untouched. Output was captured outside the observed repositories. Only the
preexisting synthetic pkg/dirty.py diagnostic is redacted, with raw and stored
hashes in log-redactions.json. Historical logs remain unchanged.

Gate byproducts .veldo/last_verify and .veldo/events.jsonl are restored before the
final proof commit and excluded from all task commits. Proof packaging follows
the tested commit; no gate result is claimed for the later proof-only commit.

## Observation boundary

This is a before-and-after inventory. Working-tree and sandbox HOME modification
times detect identical-byte rewrites. Git metadata stays content-only to tolerate
index and sharedindex timestamp refresh on reads. Special files are recorded by
kind and skipped by copying; no content-fidelity claim covers them. Permission-only
changes, metadata-only timestamp changes, and writes that restore every observed
value remain outside the claim. This is not a process trace or filesystem
confinement. The earlier boundary for absolute paths, external symlink targets,
shared live stores, nested stand-down, and the queued Landlock follow-up is unchanged.
