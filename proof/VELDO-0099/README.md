# VELDO-0099 proof after the third review

Implementation and mutation-driver commit: 499bbd5a3fad1820bc40ebdf775eb95da17f3483. The specification remains ready
for external independent review. No self-approval, landing, or push is claimed.
Engine and pack files are unchanged.

## Fixes and observation boundary

In scripts/suites/24_veldo_0007_install_and_run.py:

- Lines 169-173 include veldo/ in the copied common store. Claims and runs now
  enter the sandbox inventory. Lines 125-147 still exclude shared live stores.
  Lines 504-526 assert copied claim/run bytes and detect a deleted copied claim
  in both shapes while preserving the source claim.
- Lines 199-274 read C-quoted alternate entries as filesystem bytes, including
  named escapes and three-digit octal escapes. Resolution and rewriting preserve
  quoting, and missing alternate directories or malformed quoting fail by name.
  Lines 569-595 drive both relative and absolute quoted entries in both shapes.
  Git validates the source with cat-file before copying; the copy must also pass
  cat-file and preserve working bytes, index entries, and HEAD.
- specs/VELDO-0099-worktree-git-shape.md:135-150 names the isolated sandbox surface:
  working tree, private git directory, copied common store including claims/runs,
  and materialized alternates. Shared stores written by other workers are observed
  only through this copy. Live inventory covers only this checkout and its private
  git state. The separate sandbox HOME check does not cover arbitrary host paths.

The byte decoder follows the escape set in Git's unquote_c_style:
https://github.com/git/git/blob/master/quote.c
The quoted fixtures contain a quote, backslash, tab, newline, and an octal-escaped
UTF-8 filename. The code and this proof's text remain ASCII.

This is a snapshot comparison, not process file-operation tracing or OS confinement.
It depends on faithful copying and normalized paths. It cannot prove absence of
writes to arbitrary absolute paths, external working-tree symlink targets, shared
live stores, or writes that restore all inventoried state before the second snapshot.
Copying mutable shared state is also not an atomic snapshot of all live records.

## Full gates

Every invocation is ./scripts/verify.sh. Logs retain all gate outcomes and rows.

| Run | Commit | Exit | Top-level selftests | Result |
| --- | --- | ---: | --- | --- |
| Before, assigned linked checkout | 482fa12 | 1 | 4832 passed, 0 failed | RED in first-use integration |
| After, assigned linked checkout | 499bbd5 | 0 | 4838 passed, 0 failed | GREEN |
| After, disposable primary checkout | 499bbd5 | 0 | 4838 passed, 0 failed | GREEN |

The before run began clean, and no repository source or proof edits were made while
it ran. Its first-use mutated copy reported 4831 passed and 1 failed, on VELDO-0007
AC4's live-inventory row (THIS repository is untouched). The untouched-copy rerun
reported 4832/0, so first-use returned failure. Its diagnostic truncates the row
before the changed-entry details. The cause of that before-run failure is not
established; this proof does not claim the two fixes caused it or repaired it.

Both after gates started at the same committed implementation and driver. No source
or proof files were edited during those gates. Receipt packaging followed them.
The primary repository was created using git clone --no-hardlinks --no-checkout of
the assigned checkout, then checkout --detach of the exact implementation commit.
It is disposable and independent of all existing branches and worktrees.

Full logs: gate-third-review-before.log, gate-third-review-linked.log, and
 gate-third-review-primary.log. Historical gate logs are retained but are not
current evidence. All complete gates ran 8 catalog checks with 15 not applicable,
0 waived, and 0 undeclared. See manifest.json for exact commits and commands.

## Every driven mutation

Run python3 proof/VELDO-0099/drive.py. The final driven.json binds the source hash,
exact commit, complete row labels and all expected red-row sets. The driver asserts
that it did not modify the live suite. These are diagnostics, not full gates.

| Mutation | Passed/failed | Red rows |
| --- | --- | --- |
| Restore .git directory requirement | 16/1 | Linked copied substrate resolves inside its sandbox |
| Substitute clone of HEAD | 15/2 | Primary and linked dirty stage/index/untracked copy fidelity |
| Restore shared live inventory | 15/2 | Primary and linked sibling staging leaves live inventory unchanged |
| Inventory only sandbox working tree | 15/2 | Linked private and common metadata write is observed |
| Treat alternate quotes as filename characters | 9/4 | Both shapes, relative and absolute C-quoted alternate has objects and copy fidelity |
| Omit copied veldo/ ledger | 11/2 | Both shapes, copied claims and runs retain bytes and claim deletion is observed |
| Skip config normalization | 11/2 | Both shapes, redirected config and alternates are isolated and original edit survives checkout-index |
| Copy sibling private state | 11/2 | Both shapes, 50 copies during sibling staging have zero raises and no sibling state |
| Raise on vanished entry | 12/1 | An entry vanishing after enumeration does not raise |
| Omit primary sharedindex observation | 12/1 | Primary split index corruption is observed |
| Skip alternate rewriting | 7/6 | Both redirected-config rows and all four quoted-alternate rows |
| Restore caller identity reads | 0/1 | Checkout shape controls block completes rather than raising |
| Actual AC4 directory requirement | Primary 14/0, linked 13/1 | Linked THE OBSERVATION'S OWN SUBSTRATE |
| Actual AC4 shared live inventory during sibling staging | Each shape 13/1 | THIS repository is untouched |
| Actual AC4 stage writes copied common store | Each shape 13/1 | NOT ONE BYTE of the repository under check changed |
| Actual AC4 stage deletes copied claim | Each shape 13/1 | NOT ONE BYTE of the repository under check changed, naming veldo/claims/probe.json |
| Actual AC4 shared live inventory during sibling heartbeat | Each shape 13/1 | THIS repository is untouched |

Unmutated layout and review controls are 17/0 and 13/0 with empty HOME and
XDG_CONFIG_HOME, disabled system/global Git config, and no caller identity. The
review controls include 50 copies per shape during concurrent sibling staging.

Actual AC4 control, sibling-staging, redirected-config, and sibling-heartbeat runs
are each 14/0 in both shapes. The heartbeat invokes the real claim module from a
disposable sibling subprocess within the live before/after inventory window. The
first worker's claim is granted and the second is refused as claimed before and
after each observation. Only then does the driver release the first worker's claim.
The deletion mutation edits only the copied stage's __main__ path; the original
claim survives. The sandbox row, not the live row, detects the deletion.

The first diagnostic drive passed before the final implementation commit. A fresh
complete drive at the committed implementation produced driven.json. Temporary
preview probes caught a syntax error in a generated test edit and an overbroad
expected failure set for the config mutation; both were corrected before the final
drive. They are not reported as successful evidence.

## Packaging and remaining review

Readiness is revalidated in ready-check.txt. sibling-search.txt records the suite
search for .git directory assumptions; remaining matches are fixture checks.
Only the existing synthetic pkg/dirty.py diagnostic is redacted from gate logs.
log-redactions.json records raw/stored hashes and line numbers; no gate result,
failure row, or stand-down is removed. Raw logs remain outside this repository.

Gate byproducts .veldo/events.jsonl and .veldo/last_verify are restored with
 git checkout -- .veldo/last_verify .veldo/events.jsonl before receipt commits.
The external reviewer owns independent review and any real landing stamp.

## Design judgment

Another class of omitted store or path redirection that lets the stage mutate
repository state while this observation stays green would justify replacing the
copy-and-diff design with process-attributed file-operation observation. A requirement
to detect transient writes restored before the second snapshot would independently
justify that change. Another parser bug that fails loudly would warrant a local fix.

That replacement would cost macOS adopters a native observation component and platform
maintenance beyond the current Python standard library. DTrace cannot inspect
SIP-protected system processes. An Endpoint Security route requires an entitled,
signed helper, root execution, and user-granted Full Disk Access; a system extension
also has installation approval. A VM-based alternative adds a runtime and resource
cost. Neither alternative is implemented or verified by this proof.

Sources: Apple's runtime protection guide
https://developer.apple.com/library/archive/documentation/Security/Conceptual/System_Integrity_Protection_Guide/RuntimeProtections/RuntimeProtections.html
and Endpoint Security client/setup documentation
https://developer.apple.com/documentation/endpointsecurity/client
https://developer.apple.com/documentation/endpointsecurity/monitoring-system-events-with-endpoint-security

## Final gate with refreshed proof

The final ./scripts/verify.sh in this linked checkout at 90641482aecfbf637758dbe267a2e02c20decbce
exited 0, GREEN, with the refreshed proof committed: 4838 passed, 0 failed;
first-use integration passed; 8 required catalog checks passed, 15 not applicable,
0 waived, and 0 undeclared. gate-third-review-final.log records the output.
This receipt changes proof records only; it does not claim a new implementation
verification or a landing stamp. The two gate byproducts are restored before the
receipt commit.
