# VELDO-0099 proof after the second review

The implementation and mutation driver are bound to c63df48ae9087dfdaddab83a9f34d0a8ceabd329. The spec remains
ready for the external independent reviewer. No self-approval or landing is claimed.
Engine and pack files do not change.

## Corrections

All code changes are in scripts/suites/24_veldo_0007_install_and_run.py:

- Lines 84-97, 176-293: rebuild config using only non-path storage settings;
  discard includes, core.worktree, hooks and execution paths; clear inherited Git
  redirects; rewrite .git, commondir and gitdir; materialize symlinked metadata
  and recursive object alternates without hardlinks. Alternate stores live under
  the copied common store so writes to them remain observed. Static path/config
  assertions precede Git discovery in the copy, then Git's resolved working tree,
  private directory, common directory, index, objects, HEAD, config and hooks are
  checked before the copied stage can execute.
- Lines 150-173, 261-293: select common objects, refs, packed-refs, shallow and HEAD,
  plus config and this checkout's private state. Never traverse sibling worktrees.
  Recursive metadata copying tolerates FileNotFoundError at enumeration and copy;
  other failures remain failures. No common index is copied for a linked checkout.
- Lines 111-147: the primary private inventory includes sharedindex.*, index,
  config.worktree, uppercase pseudorefs and operation files (including HEAD,
  ORIG_HEAD and MERGE_HEAD), sequencer/rebase directories, logs/HEAD, and the
  per-worktree bisect/worktree/rewritten refs. Linked private state stays recursive.
- Lines 370-500: real fixtures exercise concurrent sibling activity, deterministic
  disappearance, corrupt split index bases, external configs and relative alternates.

The redirect fixture enables worktree config, sets core.worktree in common and
private configs, adds an external config include and hooks path, and supplies all
objects through a relative external alternate. It executes checkout-index -f -a
inside the copy and requires committed bytes there and byte-identical dirty bytes
in the source. It also checks object availability and observation of an alternate
store write. Skipping normalization reds this row before any unsafe Git write runs.
The real AC4 stage additionally runs with redirected config and a dirty original
stage in each checkout shape: 14 passed, 0 failed, original bytes unchanged.

## Full gates

All full gates use ./scripts/verify.sh:

| Run | Commit | Exit | Selftest | Catalog |
| --- | --- | ---: | --- | --- |
| Before, assigned linked checkout | f3ac2e7 | 0 | 4825 passed, 0 failed | 8 run |
| After, assigned linked checkout | c63df48 | 0 | 4832 passed, 0 failed | 8 run |
| After, disposable primary checkout | c63df48 | 0 | 4832 passed, 0 failed | 8 run |

Each complete gate is GREEN and includes passing first-use integration. Catalogs
also report 15 not applicable, 0 waived and 0 undeclared. Full outputs are
 gate-second-review-before.log, gate-second-review-linked.log, and
 gate-second-review-primary.log. The before run launched from a clean tree;
 specification edits began while it was running. Its suite counts reflect the
 prior implementation, but it is not claimed as an immutable all-file snapshot.
The after runs started from the same clean implementation commit; no implementation
or proof bytes were edited while those runs executed. These receipts are packaged
afterward. Historical stand-downs remain visible and are not newly proven history.

The primary fixture was created with:

```
git clone --no-hardlinks --no-checkout <assigned-worktree> <temporary-primary>
git -C <temporary-primary> checkout --detach c63df48ae9087dfdaddab83a9f34d0a8ceabd329
cd <temporary-primary>
./scripts/verify.sh
```

It is an independent disposable repository. No other existing branch or worktree
was changed. Nothing was pushed. The assigned checkout's .veldo/last_verify and
.veldo/events.jsonl are restored with git checkout before receipt commits.

## Driven mutations

Reproduce with python3 proof/VELDO-0099/drive.py. The driver extracts the actual
suite functions through their AST, mutates them only in memory or in disposable
fixtures, asserts each exact expected red-row set, and records the live suite hash
before and after. driven.json contains every complete row label and result.
These are paired diagnostics, not selected-suite results claimed as full gates.

| Mutation | Passed/failed | Red row |
| --- | --- | --- |
| Restore .git directory requirement | 16/1 | Linked copied substrate resolves inside its sandbox |
| Substitute clone of HEAD | 15/2 | Primary and linked dirty stage, index and untracked copy fidelity |
| Inventory only sandbox working tree | 15/2 | Linked private and common metadata write is observed |
| Restore shared live inventory | 15/2 | Primary and linked sibling staging leaves live inventory unchanged |
| Restore caller identity reads | 0/1 | Checkout shape controls block raises during setup |
| Skip config normalization | 5/2 | Primary and linked redirected config and alternates are isolated and original edit survives checkout-index |
| Copy sibling state | 5/2 | Primary and linked 50 copies during sibling staging have zero raises and no sibling state |
| Raise on vanished entries | 6/1 | An entry vanishing after enumeration does not raise |
| Omit sharedindex from primary observation | 6/1 | Primary split index corruption is observed |
| Skip alternate rewrite | 5/2 | Primary and linked redirected config and alternates are isolated and original edit survives checkout-index |
| Actual AC4 directory requirement | Primary 14/0, linked 13/1 | Linked THE OBSERVATION'S OWN SUBSTRATE |
| Actual AC4 shared live inventory during sibling staging | Each shape 13/1 | THIS repository is untouched |
| Actual AC4 stage writes copied common store | Each shape 13/1 | NOT ONE BYTE of the repository under check changed |

Unmutated layout controls are 17/0 and review controls are 7/0 under empty HOME,
empty XDG_CONFIG_HOME, disabled global/system config and no caller identity.
The review control performs 50 copies per shape while a sibling continuously
stages and unstages; all 100 complete without a raise or copied sibling state.
A separate deterministic control deletes index.lock after enumeration and before
copying it. Both primary and linked fixtures corrupt a real sharedindex base:
Git ls-files fails, and the inventory identifies the changed sharedindex entry.
Real AC4 controls, sibling staging controls, and redirected-config controls each
pass 14/0 in both shapes.

## Scope, unsuccessful probes and limits

Readiness is validated by the command in ready-check.txt. sibling-search.txt records:

```
rg -n '\.git.*is_dir|\.git.*isdir|isdir.*\.git|\[.*-d.*\.git' scripts/suites
```

Remaining directory checks are fixture controls or repositories created with
Git init; the live substrate has no .git directory requirement.

An early config mutation also tripped the race rows because the assertion rejected
the harmless core.logallrefupdates default; that setting is now preserved.
An early split-index mutation removed sharedindex from both copying and observation,
so checkout-index failed before the observation probe. The final mutation removes
only primary observation entries, isolating the reviewed defect. Those interrupted
probe attempts are not claimed as successful mutation evidence.

Two gate attempts at 1e9b2c0 were deliberately stopped before completion after
inspection showed alternate copies should live inside the inventoried common root.
They are not gate evidence. The complete runs above verify the corrected location.

Independent review and landing remain with the external reviewer, as the spec's
scope requires. No implementation self-approval is recorded. Old gate logs remain
as historical artifacts; their results do not describe this correction.

## Log redaction

Only pattern-shaped pkg/dirty.py synthetic diagnostics are replaced by
[REDACTED synthetic selftest diagnostic]. No result, failure, or stand-down row is
removed. log-redactions.json records affected lines and raw/stored SHA-256 values.
Unredacted logs remain outside the repository. Manifest artifact hashes cover the
stored files. No scanner exemption or protected-path change was made.
