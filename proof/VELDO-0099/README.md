# VELDO-0099 proof

The implementation is bound to commit 64413f029ff5479ab583a8a8d01bd24279bacc9b.
The changed suite is scripts/suites/24_veldo_0007_install_and_run.py. Engine and
pack files do not change. Independent review and landing are outside this run.

## ID and readiness

The initial draft used VELDO-0023, the next number after the highest ID in specs/.
It was committed as f808846 and promoted after a successful ready check in 62e0be1.
Full contract validation then found that PLAN-0019 already reserves that ID for W8.
It reserves VELDO-0023 through VELDO-0098 for uncreated specs. The same standalone
spec was renamed to VELDO-0099 in bc71777, returned to draft, checked again, and
promoted in bb00ca6. No plan reservation was changed. ready-check.txt records a
repeat of both structural and ready checks against the implementation commit.

## Search and scope

Searches performed:

```
rg -n "THE OBSERVATION'S OWN SUBSTRATE" scripts/suites
rg -n '\.git' scripts/suites
rg -n '\.git.*is_dir|\.git.*isdir|isdir.*\.git|\[.*-d.*\.git' scripts/suites
```

The sole assertion over the live checkout's .git directory shape was the
VELDO-0007 AC4 substrate row, originally at line 472. Two sibling observations
inventoried only the sandbox working tree and live working tree. They included
metadata only when .git happened to be a directory, so both now inventory roots
resolved by git rev-parse --git-dir and --git-common-dir as well.

The AC3 negative fixture deliberately writes a malformed .git pointer. Its test
stays intact; its comment now distinguishes malformed content from a valid file.
The .git/index literals in 13_warp_0623_codified_live.py address a disposable
repository just created by git init for hostile environment-variable controls.
They do not assume the shape of the live checkout. Other matches exclude git
metadata from source/bytecode scans, address .github, or test .gitkeep entries.
The new is_dir/is_file pair asserts the shapes of fixtures this test constructs,
not the shape of the repository running the gate.

## Evidence and reproduction

Both full gates run ./scripts/verify.sh at the implementation commit above. The
linked run is in the assigned persistent worktree. The primary run is in a
separate disposable clone, with no registration in this repository's common
store. It was prepared using git clone --no-hardlinks --no-checkout, followed by
git checkout --detach at the recorded commit. Its local user.name and user.email
were copied from git config in the assigned worktree. No other existing branch
or worktree was modified and nothing was pushed.

Gate stdout and stderr are recorded in gate-linked.log and gate-primary.log,
with the synthetic selftest diagnostic redaction described below.
The gate's own linked-worktree event is retained in .veldo/events.jsonl, with its
stamp in .veldo/last_verify. The manifest records exit codes, counts, and hashes.
A gate checks working bytes; subsequent proof-only commits carry the evidence
rather than pretending the evidence was present at the earlier implementation
commit.

Run the paired mutation proof with:

```
python3 proof/VELDO-0099/drive.py
```

The driver compiles the suite's actual helper and assertion functions from its
AST. It applies mutations only in memory and verifies that the suite's on-disk
SHA-256 is unchanged. It builds real disposable primary and linked repositories
at equal HEADs, with an unstaged stage edit, a staged-only file, and an untracked
file. It drives real clones as negative controls and plants writes in the copied
private and shared stores. Expected results, all asserted by the driver:

| Drive | Passed | Failed | Required failure |
| --- | ---: | ---: | --- |
| Layout controls | 13 | 0 | None |
| Restore .git directory requirement | 12 | 1 | Linked substrate |
| Substitute clone of HEAD | 11 | 2 | Copy fidelity in both shapes |
| Inventory working tree only | 11 | 2 | Linked private and common store writes |
| Original AC4, primary, fixed | 14 | 0 | None |
| Original AC4, primary, old shape requirement | 14 | 0 | None |
| Original AC4, linked, fixed | 14 | 0 | None |
| Original AC4, linked, old shape requirement | 13 | 1 | Original substrate row |

The last four drives run the existing _iar_ac4 function, including its real
compose-install-gate operation, in disposable checkouts of the recorded commit.
They do not replace the full gate. driven.json contains every observed row and
the exact mutations. The copied metadata is isolated before observation begins;
this setup is distinct from the stage whose writes are being measured.

## Earlier failures and limits

baseline-gate.log preserves the initial exploratory RED run. It found the
original substrate failure plus two corpus assertions affected by the temporary
VELDO-0023 plan collision: 4805 passed, 3 failed. The run began at 6dba187 while
spec drafting proceeded, so it is not evidence about one clean commit. Its gate
stamp names bb00ca6, which was HEAD when it ended. The independent paired AC4
drives above provide the controlled shape differential at one fixed commit.

An early selected-suite diagnostic also caught a fixture commit that lacked a
local git identity. The fixture now uses the repository's configured identity.
After that correction, the selected diagnostic had no failures and deliberately
exited 2 because selected runs cannot mean gate green. No selected-suite run is
cited as passed unit evidence in the manifest.

The no-write observation remains an observation over the duration of a run that
returns. It does not prove cleanup after a killed process. Existing flattened-
history stand-downs remain visible in the full logs; they are not claimed as
newly measured history. Independent review has not been performed by this agent.

## Proof packaging correction

The first full gate after adding the proof bundle, at 7d0ee961f9abae8a7ee7495812f4266105eb7bec,
passed all 4821 unit checks and first-use integration but failed secret inventory.
Line 46 of each saved log contained a pattern-shaped synthetic diagnostic from the
pkg/dirty.py selftest fixture. The scanner correctly refused both the saved text
and its reachable history. gate-proof-packaging-red.log records that RED result.

Only that diagnostic match is replaced by a redaction marker in each stored log.
log-redactions.json records line numbers and raw/stored SHA-256 values. The
transformation applies the existing secret scanner's PATTERNS to log lines and
replaces each match with the marker; it does not remove any result or failure row.
The latest unpushed proof commit was amended to remove the diagnostic from
reachable history. No implementation commit, policy, or secret disposition was
changed. The failed gate event remains in the append-only event log with the
commit it actually named, even though that proof commit was replaced.
