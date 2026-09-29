# VELDO-0166 proof

Implementation commit `7431b9e4` repairs unnamed warning clears and concurrent observation
ordering at `75f45d77` on `build-veldo-0166`.
The preceding implementation `73ab391a` repaired the stored unified clear regression at `9cca7766`.
The preceding implementation was `7f54fdfe`, fixing the re-check at `1b7d225e`.
The earlier implementation was `2c4f250c`, after the local main merge at `3544d4c4`.
Veldo records every reported Claude Code usage window against the account and preserves an
existing profile directory when registering it. All fixtures are generated locally; no engine,
login, real credential, network or user service manager is used.

## Production behavior

The named window takes each top-level reset and utilization when present, otherwise its own
unifiedWindows value. Each companion keeps its own values and no invented status. An unnamed
allowed or allowed_warning event records only its map and clears a stream rejection; it never creates a `unified`
window. An unnamed rejection is stored as rejected under `unified`, the window reported by
`limit()`. The pool passes that account over until its reset, or indefinitely if none was reported.
The raw line and digest remain the receipt for each observation.

An ordinary companion preserves an active rejection. If that rejection had no reset, a later numeric reset
fills it in while preserving the rejected status. The account is blocked only until that time,
including when the newly learned reset already passed. An unnamed allowed or allowed_warning clear instead carries
`clear_rejection` through Metering to the signed account writer. Its reported companions replace
active rejections, including those with no reset, keeping their status absent. Both Meter and store
then agree that the rejection was cleared. The writer also lifts an existing `unified` rejection,
including one persisted by an earlier dispatch, marking it allowed with the clearing dispatch and
observation time. It preserves the reported reset and utilization. A bare allowed or allowed_warning event forwards a
clear signal with its receipt and no window id; it creates and counts no window. An account without
a stored unified window still acquires none.

If a companion observation is older than its stored window, the writer preserves that newer
window while keeping the unified lift it just applied. A clear lifts a unified rejection only
when its observation time is at least the rejection's time. Older clears preserve the newer
rejection. The ordering row checks all three timestamp relations through real Metering and
signed account writes, using a controlled receiver clock and distinct dispatches.

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
| AC1 | `windows/unnamed-rejection` | An unnamed rejection stores unified, its reset and receipt; the real pool blocks until the reset or indefinitely without one. |
| AC1 | `windows/clear-active-rejection` | A clear event lifts both no-reset and future-reset rejections in Meter and the real pool, without inventing statuses or a unified observation. |
| AC1 | `windows/clear-unified-no-reset` | A real clear map reopens an unnamed no-reset rejection, in the same dispatch and a later dispatch. |
| AC1 | `windows/clear-unified-reset` | The same clear reopens a future-reset rejection immediately, in both dispatch cases. |
| AC1 | `windows/clear-unified-bare` | A bare allowed event reopens a persisted unnamed rejection without inventing a window observation. |
| AC1 | `windows/clear-warning` | Unnamed warnings with a real map or bare signal reopen persisted unified rejections in the same or a later dispatch; mapped warnings also clear a named stream rejection, retaining receipts and absent companion statuses. |
| AC1 | `windows/clear-observation-order` | A newer companion survives a clear; a unified lift survives that companion losing its write. Older clears preserve a newer unified rejection, while equal and later clears lift it with the correct time and dispatch. |
| Observability | `observability/counts-and-log` | Counts separate names, statuses and directory states; structured logs carry required attribution and omit private metadata and contents. |
| AC2 | `profiles/existing` | Both providers preserve mode 0755, file bytes, mtime and entries and record existing. |
| AC2 | `profiles/created` | Both providers create mode 0700 under umask 022 and record created. |

## Red record

`drive.py` with its red option archives an unchanged historical tree and runs the current suite
against its real production modules. `red-at-582cc961.json` records all 12 rows red by assertion
on the original pre-0166 implementation. `red-at-3544d4c4.json` records all five new review rows
red by assertion on the merged commit immediately before these fixes, with the seven existing
rows green. `red-at-1b7d225e.json` records both re-check rows red by assertion on the commit immediately
before this repair, with the 12 existing rows green. Every new behavior row is red on its
pre-change implementation. `red-at-9cca7766.json` records all three new unified-clear rows red by assertion on the commit
immediately before this repair; the 14 existing rows remain green. None of these records contains
an exception in place of an assertion.

`red-at-75f45d77.json` records both new behavior rows red by assertion on the commit immediately
before this repair; the 17 existing rows remain green. The ordering row fails at equal and later
clear times because the old writer discards the unified lift with the stale companion. Its
older-clear case is a passing regression control for the existing timestamp guard. Removing
that guard is separately registered as a mutation targeting the same ordering row.

## Mutations

`mutations.json` registers 32 finding-166 mutations and their exact diffs and module digests.
The original 12 include both declared falsifiers and the existing suite-75 journey mutation.
The nine additions pin top-level fallback, map precedence, missing-reset repair, unnamed clear
window handling, stream clearing, both counters, window logging and account directory logging.
Four re-check additions drop the unnamed rejection, drop the Meter's clear signal, omit its
forwarding in Metering, or ignore it in the store. Each targets its corresponding new row.
Two further mutations drop the unified rejection lift or the bare clear signal and target the
new unified-clear rows. Five further mutations target the two new rows: omit the warning clear
signal, omit warning stream clearing, omit the bare warning signal, discard a lift with a stale
companion, or remove the observed_at guard. Changed mutation anchors were refreshed without
changing the existing defects.

The driver's register-only option refreshes this inventory and parses every mutant without
executing suites. Mutation execution is reserved for the reviewer under this run's instructions.
No mutation rejection is claimed for this revision. The default driver still supports execution
for a reviewer authorized to run it, including its existing suite-75 journey case. Neither the default driver nor any mutation worker
was executed for this repair.

## Verification

The ordinary and isolated gate-environment runs of suite 0166 each passed: 19 behavior rows,
45 assertions including the shared preamble, zero failures. The isolated run used Python's
`/usr/bin` directory first on PATH, an empty environment, HOME and TMPDIR in /dev/shm, UTC,
C.UTF-8 and the requested Python and Git isolation settings. Selftest returns exit 2 for a
successful partial run; these are partial suite results, not gate or landing evidence.

requires.json was regenerated and remained current. The anchor check reports 0 bad anchors.
Validation of all specifications exits 0. On implementation commit `7431b9e4`, the footprint
check reports 54 changed files, none outside the footprint. All four production modules match
their engine copies. All mutation names are unique across findings. The existing suite manifest
registration and proof driver were reused. Searches covered the Meter observation producers,
Metering forwarding and receipt handling, account observation writer and authorization, blocking
and usage readers in the reservation service and pool, and their suite callers. No footprint expansion was needed.

The gate, whole selftest, other suites and mutation execution were not run, as instructed.
Mutation registration parsed all 32 mutant sources; no mutation rejection is claimed for this
revision. The spec History names VELDO-0160 / Release 2 follow-up tickets for named windows absent
from the real clear map (seven_day_opus, seven_day_sonnet and overage), named five_hour rejection
followed by bare allowed, and unnamed rejection followed by five_hour rejected then allowed
while the Meter tracks one limit. These cases predate this branch and remain outside this repair,
as does the earlier VELDO-0160 ticket for expiring no-reset rejections.
