# VELDO-0099 proof after round six

Implementation and driver commit: f796087c0a7a1bbc3c35b6ba6f0ee51e677a31cf.
The specification remains ready for external independent review. No self-approval,
landing, or push is claimed. Engine and pack files are unchanged.

## Changes with file and lines

- scripts/suites/24_veldo_0007_install_and_run.py:275 selects only info/alternates
  and info/http-alternates in copied object stores. Line 301 validates these paths;
  ordinary branch refs and reflogs are no longer parsed as alternate paths.
- scripts/suites/24_veldo_0007_install_and_run.py:1006 detects nested .git entries
  and .gitmodules without invoking git. Line 1023 records and prints AC4's stand-down
  before copying or executing a stage, with no expect call or passed-row increment.
  The printer matches the release check's recorded-stand-down wording.
- scripts/suites/24_veldo_0007_install_and_run.py:1267 drives a real submodule in
  both shapes with a valid absolute .git pointer and binary unstaged contents.
  Five marker cases per shape cover the submodule, pointer alone, .git directory,
  .gitmodules alone, and nested .gitmodules. Every case asserts the record, exact
  output, no counted AC4 rows, no copying or subprocess calls, and unchanged bytes.
  The copy tripwire stops the detection mutation before it can destroy fixture data.
  Line 1335 drives branch refs and reflogs named alternates and http-alternates,
  asserting byte fidelity and usable copied substrates in both shapes.
- proof/VELDO-0099/drive.py:144 drives both new mutations and checks their red rows.
  Line 240 adds the real AC4 branch/reflog case, requiring all 14 rows to pass.
  Every prior mutation remains driven with its expected failure set.
- specs/VELDO-0099-worktree-git-shape.md:34 extends the ready criteria with refusal
  and exact alternate-path controls. Line 176 closes the design and names the
  Landlock follow-up without implementing it. specs/index.md regenerated unchanged.
- This README, manifest.json, driven.json, gate-round-six-*.log, ready-check.txt,
  sibling-search.txt and log-redactions.json refresh the evidence. Earlier logs
  and baseline-driven.json are historical records, not round-six results.

## Both full gates

Both commands were ./scripts/verify.sh, exit 0, at f796087c0a7a1bbc3c35b6ba6f0ee51e677a31cf.
The assigned linked checkout and a disposable primary clone used identical committed
source. No source or proof edits occurred during either gate. Both reported
4864 passed, 0 failed, first-use integration passed, and all 8 required catalog checks passed
(15 not applicable, 0 waived, 0 undeclared).

The primary fixture was made with git clone --no-hardlinks --no-checkout from the
assigned checkout, followed by git checkout --detach of that exact commit. No
existing other worktree or branch was modified. Full outputs are
 gate-round-six-linked.log and gate-round-six-primary.log.

## Driven mutations and red rows

Command: python3 proof/VELDO-0099/drive.py, exit 0. driven.json retains all exact
row labels, mutations, source digest, commit, and the randomly selected victims.
The driver and its real AC4 clones ran at f796087c0a7a1bbc3c35b6ba6f0ee51e677a31cf.
The recorded suite digest is unchanged and matches that commit. These are mutation
diagnostics, not selected-suite gate evidence.

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
| Skip nested repository detection | 0/20 | Both shapes, all five markers: AC4 stand-down is recorded, printed, and never passed; original edit survives with no copy or nested git operations |
| Match alternates basename anywhere | 0/2 | Both shapes: branch and reflog named alternates copy cleanly |


Unmutated layout and prior-review controls are 17/0 each. The nested refusal
controls are 20/0; these are assertions about recorded refusals, not passed AC4
observations. Alternates-name copy controls are 2/0. All run with empty HOME and
XDG_CONFIG_HOME, system/global git config disabled, and no caller identity.
Concurrent sibling staging still permits 50 copies per shape with zero raises.

Actual AC4 control, sibling staging, redirected config, sibling heartbeat,
clean split index, and branch/reflog named alternates are each 14/0 in both shapes.
The random deletion cases record and require the victim path in the red sandbox
row, and verify original contents remain intact. The linked directory-shape
mutation still reds the actual substrate row while the primary control passes.

## Design closure and packaging

This is a before-and-after content inventory of an isolated copy. A nested
repository makes the entire AC4 observation stand down visibly, with the reason
"nested repository present; the copied observation is not self-contained".
The existing limits remain: absolute paths, external symlink targets, shared live
stores, restored writes, identical-byte rewrites, timestamp-only or permission-only
changes, and non-atomic copying are not converted into process confinement.
The follow-up is kernel-enforced write confinement of the stage process using
unprivileged Linux Landlock on kernel 5.13 and later, with recorded stand-down on
other hosts. That follow-up is not implemented here.

The selected-suite diagnostic was 125/0 and exited 2 by design; only the full gates
above establish gate results. An initial primary-gate launcher used the temporary
parent directory as cwd and failed before starting a gate; the corrected launcher
created the disposable clone and ran the recorded gate there.

Only the synthetic pkg/dirty.py diagnostic is replaced in stored gate logs.
log-redactions.json records raw/stored digests and line numbers. No outcome or
failure row is removed. Raw logs are in /tmp/veldo-0099-round6/.
Gate byproducts .veldo/last_verify and .veldo/events.jsonl are restored with
 git checkout -- .veldo/last_verify .veldo/events.jsonl before the proof commit.
The reviewer owns independent review and the real landing stamp.
