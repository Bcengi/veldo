# VELDO-0166 proof

Implementation: `f6e0654f` on `build-veldo-0166`, based on `582cc961`.

The Claude Code meter emits one observation for every readable entry of `unifiedWindows`, plus
`rateLimitType` when that window is absent from the map. Each observation carries its own utilization
and reset and the original line and digest. The named window retains the existing allowed/rejected
normalization; companions have a null status. The account writer accepts that absence without
inventing allowance. The production receiver keeps each raw receipt and records the observation
against its dispatch's account. Window names and statuses remain countable in the signed account
journal. Missing resets remain null; an unreadable entry emits no observation.

The profile helper chmods only a directory it creates. Its persisted record names the directory and
whether it was `created` or `existing`, so additions can be counted by those outcomes. Existing
contents and permissions are left intact. The three changed engine modules are byte-identical to
the installed copies.

The spec footprint adds `control_accounts.py` and its engine copy because AC1 needs the account
writer to accept an absent status. It adds `scripts/drive.py` because the requested proof driver was
absent. No protected file changed.

## Rows

Suite: `83_veldo_0166_usage_windows`, six rows, one report per row. It drives the real `Metering`
receiver seam, `Accounts` writer and production membership authorization over a signed SQLite store.
The journal key, profiles and receipt directories are generated temporary fixtures. No model runs,
login or real credential is used. The fake Claude in suite 75 also prints the complete source event
from the spec, including both windows and all outer fields.

| Criterion | Row | Evidence |
| --- | --- | --- |
| AC1 | `windows/five-hour` | The verbatim source line records both windows with their exact utilization and resets, one raw receipt and digest each, bound to the account and dispatch. |
| AC1 | `windows/qualified-set` | All six windows in the 2.1.281 qualification record are stored exactly once with their own values. |
| AC1 | `windows/status-only-named` | Rejected, allowed-warning and allowed events apply status only to the named window; companions have null status and are not declared rejected. |
| AC1 | `windows/missing-reset-receipts` | A readable companion without a reset stays null, an unreadable entry is skipped, and the named window absent from the map is retained, with receipts and dispatch attribution. |
| AC2 | `profiles/existing` | Both providers register a generated 0755 directory without changing its mode, file bytes, file mtime or entries, and persist its existing-directory outcome. |
| AC2 | `profiles/created` | Both providers create a missing directory exactly 0700 and persist its created-directory outcome and resolvable path. |

## Red record and mutations

`scripts/drive.py` with the red option and `582cc961` archives the unchanged pre-change tree and
runs the current suite against it. `red-at-582cc961.json` records all six rows red by assertion.
The created-directory row fails because the old helper does not record the created outcome;
its existing 0700 behavior is a positive control.

`mutations.json` records nine finding-166 mutations, green baseline and unmodified-copy controls,
source digests, exact applied diffs, and the failing named rows. All nine reject by assertion,
including the declared named-window-only and unconditional-chmod falsifiers. The independent
registry command with finding 0166 and two jobs also rejects all nine. The additional mutations
cover invented companion status, borrowed resets and utilization, duplicated named observations,
rejection of missing status, and public permissions on a new directory.

## Validation

The new suite has six passing rows and 26 shared preamble checks. Targeted suite runs return 2
when passing because the repository explicitly distinguishes a partial run from full verification.
The footprint checker reports no paths outside the spec; the anchor checker reports zero bad
anchors; the Git boundary checker and repository validation pass. The canonical gate is not run,
as instructed. Final targeted and whole-selftest results are recorded below when completed.
