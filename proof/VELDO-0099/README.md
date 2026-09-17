# VELDO-0099 proof

## Review corrections

The corrected implementation is bound to 74ae1daa2136f0025e933a9761ccdea103db09fd.
The changes are in scripts/suites/24_veldo_0007_install_and_run.py. The spec remains
ready. Engine and pack files do not change. Independent review and landing belong
to the external reviewer; this implementing agent does not approve its own work.

Finding 1: the sandbox inventory still covers the working tree, resolved private
Git directory, and copied common store. The live inventory covers only this
checkout's working bytes and private Git state. It prunes the primary .git tree
before traversal and selects private state from it; linked metadata is read from
that checkout's private directory. Shared objects, refs, and sibling indexes are
excluded from the live comparison. AC3 now states this attribution boundary.

Finding 2: the layout fixture commits with fixed user.name and user.email options
and fixed GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME, and
GIT_COMMITTER_EMAIL values. It never reads the caller's identity. The proof driver
uses an empty HOME and XDG_CONFIG_HOME, disables global/system Git configuration,
removes inherited identity/configuration environment variables, and verifies
that neither identity setting exists in its disposable source repository.

## Full gate evidence

Every full gate command is ./scripts/verify.sh. The baseline ran in the assigned
linked worktree at b43e0f28db06abd3feae645fae47b741340f7318 before edits: exit 0,
4821 passed, 0 failed. It used the caller's configured identity and did not inject
sibling activity. This GREEN does not refute either reviewer finding.
Its complete output is gate-review-before.log.

The corrected linked and disposable primary runs are gate-linked.log and
gate-primary.log, at 74ae1daa2136f0025e933a9761ccdea103db09fd: exit 0, 4825 passed,
0 failed. Both first-use integration runs passed. Each catalog ran 8 checks,
with 15 not applicable, 0 waived, and 0 undeclared. Existing history stand-downs
remain visible and are not claimed as newly measured history.

The primary checkout was created in a fresh temporary directory with:

```
git clone --no-hardlinks --no-checkout <assigned-worktree> <temporary-primary>
git -C <temporary-primary> checkout --detach 74ae1daa2136f0025e933a9761ccdea103db09fd
```

No identity was copied from the caller into that clone. It has its own object
store and no registration in this repository's common directory. Sibling staging
is performed only in disposable fixture repositories, never in another existing
worktree. Nothing was pushed. Gate-generated .veldo/last_verify and
.veldo/events.jsonl in the assigned checkout are restored before the final commit
and are not included in any correction commit.

A gate verifies working bytes. The linked run included the sanitized baseline
log and redaction-record update as uncommitted proof changes; its suite and
spec bytes match the named implementation commit. Later proof commits package
the observed results rather than claiming those receipts existed before the run.

## Driven regressions

Reproduce with python3 proof/VELDO-0099/drive.py. This is a paired mutation driver,
not a partial selftest cited as a full gate. It extracts the actual suite functions
from their AST, mutates only the in-memory functions or disposable fixture files,
and verifies that the live suite SHA-256 is unchanged. driven.json includes all
row labels, outcomes, source hash, environment description, and commit IDs.

| Drive | Passed | Failed | Red row |
| --- | ---: | ---: | --- |
| Layout controls with empty HOME and no identity | 17 | 0 | None |
| Restore .git directory requirement | 16 | 1 | Linked copied substrate |
| Substitute clone of HEAD | 15 | 2 | Primary and linked dirty-copy fidelity |
| Inventory sandbox working tree only | 15 | 2 | Linked private and common metadata writes |
| Restore shared live inventory | 15 | 2 | Primary and linked sibling staging |
| Restore caller-identity lookup | 0 | 1 | Checkout-shape fixture setup raises |
| Actual AC4 control, either shape | 14 | 0 | None |
| Actual AC4 old shape requirement, primary | 14 | 0 | None |
| Actual AC4 old shape requirement, linked | 13 | 1 | Observation substrate |
| Actual AC4 sibling staging, either shape | 14 | 0 | None |
| Actual AC4 sibling staging with shared live inventory, either shape | 13 | 1 | THIS repository is untouched |
| Actual AC4 stage writes copied common store, either shape | 13 | 1 | NOT ONE BYTE of the repository under check changed |

The sibling control wraps the real IAR.check call and stages a new file in the
sibling after that real call succeeds, before the live after-snapshot. The common
store mutation modifies the disposable stage's __main__ path to resolve and write
its own Git common directory, so the real sandboxed stage does the forbidden write
and still completes successfully. The sandbox row alone goes red. The first draft
of this probe used an additional subprocess launcher and also reddened the existing
single-funnel row; the final probe uses the stage's existing _run funnel to isolate
the common-store write. No production launcher rule was changed.

The earlier diagnostic selected-suite run after finding 1 reported 86 passed,
0 failed and exit 2, the runner's deliberate PARTIAL status. It is not evidence
of a full gate pass. Readiness was validated with:

```
python3 .veldo/validate.py ready specs/VELDO-0099-worktree-git-shape.md
```

## Scope search and historical evidence

The sibling search was repeated with:

```
rg -n '\.git.*is_dir|\.git.*isdir|isdir.*\.git|\[.*-d.*\.git' scripts/suites
```

The live shape assertion was unique to VELDO-0007 AC4. Other .git/index literals
in the codified-live suite address repositories it creates with git init. The
malformed-pointer fixture in this suite is deliberately invalid, and the layout
controls deliberately assert both shapes they construct. None is a live shape pin.

Historical logs are retained: baseline-gate.log records the original pre-fix run
(4805 passed, 3 failed, including a temporary reserved-ID collision);
gate-proof-packaging-red.log records the earlier secret-inventory failure while
packaging synthetic diagnostics; gate-final.log records the original 4821/0 green
with proof present at 08a7a748f7e9e25d07e61f96093ee65874045a03. Those logs predate
these review corrections and are not evidence that the corrected implementation
passed. The previous manifest and narrative remain available in branch history.

The initial draft used VELDO-0023, then moved to VELDO-0099 after validation found
PLAN-0019 reserved VELDO-0023 through VELDO-0098. No plan reservation changed.

## Log redaction

Full gate logs contain one pattern-shaped diagnostic emitted by the synthetic
pkg/dirty.py selftest fixture. The existing .veldo/secret_scan.py PATTERNS replace
only matching text with [REDACTED synthetic selftest diagnostic]. No result,
failure, or stand-down row is removed. log-redactions.json records each stored
log's affected line numbers and raw/stored SHA-256 digests. Unredacted output was
kept outside the repository and was never committed. The manifest hashes the
stored artifacts, including the redaction record.
