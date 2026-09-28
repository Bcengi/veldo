# VELDO-0166 proof

Implementation commit `2c4f250c` on `build-veldo-0166`, after merging local main `9f1a0445` at `3544d4c4`.
Veldo records every reported Claude Code usage window against the account and preserves an
existing profile directory when registering it. All fixtures are generated locally; no engine,
login, real credential, network or user service manager is used.

## Production behavior

The named window takes each top-level reset and utilization when present, otherwise its own
unifiedWindows value. Each companion keeps its own values and no invented status. An unnamed
allowed event records only its map and clears a stream rejection; it never creates a `unified`
window. The raw line and digest remain the receipt for each observation.

A companion preserves an active rejection. If that rejection had no reset, a later numeric reset
fills it in while preserving the rejected status. The account is blocked only until that time,
including when the newly learned reset already passed.

Account registration changes the mode only of a directory it creates, to 0700. The helper counts
successful additions in `ADDED_COUNTS` by created or existing and emits a structured stderr log
containing only the account, directory, directory state and metric increment. Arbitrary metadata
and profile contents never enter that log. `Metering.window_counts` counts observations by window
and status; the receiver emits each observation with its values, digest, account, dispatch,
invocation and metric increment. These events use the existing receiver event stream.

All four changed production modules are byte-identical to their engine copies. No footprint
expansion was needed: control_launch.py and its engine copy were already declared.

## Rows

Suite `83_veldo_0166_usage_windows` drives real `Metering`, `Meter`, the signed SQLite `Accounts`
writer, production membership authorization and `accounts.account_add`. Each row reports once.

| Criterion | Row | What the row proves |
| --- | --- | --- |
| AC1 | `windows/five-hour` | The verbatim live event stores both windows, their values, receipts and attribution. |
| AC1 | `windows/qualified-set` | Every qualified window is recorded once with its own values. |
| AC1 | `windows/status-only-named` | Only the named window carries rejected, allowed_warning or allowed status. |
| AC1 | `windows/missing-reset-receipts` | A missing reset stays null; an unreadable entry is skipped; receipts remain intact. |
| AC1 | `windows/rejection-kept` | A known active rejection survives a companion; an expired one can be replaced. |
| AC1 | `windows/named-fallback` | Both absent top-level fields fall back to the named map entry, including the stream reset. |
| AC1 | `windows/named-precedence` | Explicit fields win independently over the map, including zero utilization. |
| AC1 | `windows/rejection-reset-filled` | Later companions fill unknown resets, with both past and future resets; blocking expires. |
| AC1 | `windows/clear` | A real unnamed clear updates both windows, stores no unified window and clears the stream limit. |
| Observability | `observability/counts-and-log` | Counts separate names, statuses and directory states; structured logs carry required attribution and omit private metadata and contents. |
| AC2 | `profiles/existing` | Both providers preserve mode 0755, file bytes, mtime and entries and record existing. |
| AC2 | `profiles/created` | Both providers create mode 0700 under umask 022 and record created. |

## Red record

`drive.py` with its red option archives an unchanged historical tree and runs the current suite
against its real production modules. `red-at-582cc961.json` records all 12 rows red by assertion
on the original pre-0166 implementation. `red-at-3544d4c4.json` records all five new review rows
red by assertion on the merged commit immediately before these fixes, with the seven existing
rows green. Neither record contains an exception in place of an assertion.

## Mutations

`mutations.json` registers 21 finding-166 mutations and their exact diffs and module digests.
The original 12 include both declared falsifiers and the existing suite-75 journey mutation.
The nine additions pin top-level fallback, map precedence, missing-reset repair, unnamed clear
window handling, stream clearing, both counters, window logging and account directory logging.
The VELDO-0160 reopening mutation's comment anchor was refreshed without changing its defect.

The driver's register-only option refreshes this inventory and parses every mutant without
executing suites. Mutation execution is reserved for the reviewer under this run's instructions.
No mutation rejection is claimed for this revision. The default driver still supports execution
for a reviewer authorized to run it, including its existing suite-75 journey case.

## Verification

The ordinary and isolated gate-environment runs of suite 0166 each passed: 12 behavior rows,
38 assertions including the shared preamble, zero failures. These are partial suite runs,
not gate or landing evidence. requires.json was regenerated and was already current after the
clean merge. The anchor check reports 0 bad anchors. Validation of all specifications passes.
On implementation commit `2c4f250c`, the footprint check reports 40 changed files, none outside
the footprint; all four production modules match their engine copies. All registered mutation names
are unique across findings. The working tree was clean after the implementation commit.
The gate, whole selftest, other suites and mutation checks were not run, as instructed.
