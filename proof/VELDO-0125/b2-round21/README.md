# VELDO-0125 B2 round 21

Starting revision: `d2288a28`. Regression commit: `ba642b60`.
Implementation commit: `c5796beb`. This evidence addresses the owner's two
round 21 findings under AC3. The canonical gate, independent review, merged-tree
stamp and native Mac/SSH qualification remain with the reviewer.

## Corrupt previous entry and a fresh release

The receiver now quarantines the corrupt previous entry and durably records the
incoming event under its original dispatch identity before delivery. In
`enqueue_locked`, `read_entry(..., raise_read_errors=True)` returning `None`
means invalid content was successfully quarantined; operational read and
quarantine failures raise. Returning early at that point previously lost the
incoming event while `main` reported `delivery_pending` with exit zero.

Removing that early return lets the existing durable writer record the fresh
event. It retains the pending/active transitions, queue lock, dispatch execution
lock and acknowledgement logic. A write failure propagates through the receiver
as a nonzero exit, so Linux resends. The corrupt bytes remain quarantined.

This chooses immediate recording and delivery, with transport retry when the
record cannot be written. It preserves exactly-once authority effects by using
the same dispatch and contract binding, not creating a new invocation or
re-executing work. Existing signed-command replay and the authority's
`pending` -> `confirmed` retirement transition deduplicate retries; a confirmed
release cannot retire capacity again. Transport retries themselves are not an
exactly-once network guarantee.

Six new subprocess rows in `receiver_checks.py` cover invalid JSON and invalid
entry shape in both `.waiting` and `.pending`, and a fresh-event EIO write failure
in each state. They check exact quarantined bytes, exact incoming request at the
delivery endpoint, one delivery, empty scheduling state after acknowledgement,
and nonzero exit plus successful resend when persistence fails. Launchd install
and the final trusted delivery endpoint are fixture seams. These are Linux logic
observations, not real Mac or SSH qualification.

The round 16 test helper previously expected valid incoming events to disappear
with corrupt previous content. Its enqueue/new-receive assertions now require
the exact fresh release request to be persisted/delivered once. Corrupt-content
quarantine and rejection, healthy-peer delivery and empty-queue assertions remain
enforced. Historical run logs and evidence records are unchanged.

## Background read failures must log, skip and continue

The round 17 helper now puts a healthy peer after the unreadable entry in sorted
filename order. For EIO, EMFILE, ENFILE and EACCES, recovery must return no errors
and move that peer to pending; entries must return only the peer; drain must
deliver it despite the unreadable entry. No escaping OSError is accepted.
Four explicit drain rows supplement the tightened entries and recovery rows.
All retain the original read diagnostic, unchanged-byte and no-quarantine
assertions, then require the unread entry to deliver once after the fault clears.

The negative control changes only `read_entry`'s default `raise_read_errors`
from `False` to `True` in both canonical and installed copies. The exact change
is in `raise-default-mutation.diff`. It is applied to the fixed implementation
only for one selected suite 106 run, then restored before final validation.
`106-raise-default.log` records all 12 strengthened recovery/entries/drain rows
failing under that mutation, with no other failing rows. `mutation-restored.log`
and its zero exit record verify restoration to the committed production files.

## Execution evidence

Every test invocation uses `python3 scripts/selftest.py --suite NAME`, with one
suite running at a time. `106-before.log` uses unchanged production code from
`d2288a28` plus the committed regression tests: 20 failures, including all six
new corrupt-previous-entry rows and 14 strengthened round 16 event assertions.

`results.json` records final run counts, exit codes, source and log digests.
`before-failing-rows.txt` and `mutation-failing-rows.txt` name the negative-control
failures. The successful selected-suite exit is 2 (`PARTIAL_RUN_CANNOT_VERIFY`),
not a full verification pass. No full selftest, mutation checker or gate ran.

| Run | Suite assertions passed | Failures | Exit |
| --- | ---: | ---: | ---: |
| 106, baseline production plus regressions | 219 | 20 | 1 |
| 106, raise-by-default negative control | 227 | 12 | 1 |
| 103_veldo_0124_macos, final | 23 | 0 | 2 |
| 104_veldo_0124_control, final | 6 | 0 | 2 |
| 105_veldo_0125_relay, final | 17 | 0 | 2 |
| 106_veldo_0125_routing, final | 239 | 0 | 2 |

Each run also passed 26 shared assertions. `template-sync.json` records byte
identity for the canonical and installed outbox files. The gate byproducts
`.veldo/last_verify` and `.veldo/events.jsonl` were restored before the final
commit and are not part of this change. Nothing was pushed or merged.
