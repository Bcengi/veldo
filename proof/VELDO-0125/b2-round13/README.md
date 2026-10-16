# Round 13 profile compatibility and delivery recovery

This is development evidence for VELDO-0125, not a canonical gate stamp or native
Mac qualification. Only individually selected suites run here, as required by
the owner. The reviewer runs the canonical gate on the final/merged tree.

## Corrections

1. Profile v2 still rejects either heartbeat field and uses the existing event
   waits, runtime cap and exit-watch lifetime. Complete, explicitly versioned v1
   profiles remain readable with their original qualified digest and heartbeat
   liveness contract. The product `project_runner_macos_profile.migrate(profile)`
   validates v1, returns v2 without heartbeat fields, and leaves its input alone.
   The old qualification fails against the migrated digest; new qualification
   is required. The 0124 fixture now declares v1 literally instead of borrowing
   the current schema constant, and implements the current OS wake interface.
   Its recorded test rows, including the heartbeat assertion, are unchanged.
   The event fixture used by suite 104 uses the real migration API before
   constructing its explicitly synthetic v2 qualification.
2. Missing slot migration is retryable in both the durable outbox and receiver
   transport response. It schedules bounded backoff in `.pending`, which wakes
   QueueDirectories even when an upgrade leaves the installed plist unchanged.
   The drain initializes the index before retrying. Admission still never scans
   completed history. `--install` remains useful but skipping it does not park
   dispatches permanently.
3. Receiver startup schedules orphaned active entries in `finally`, including
   permanent refusals and unavailable authority responses. It preserves due
   dates and attempt counts and performs no backlog network delivery.
4. Recorder diagnostics precede best-effort parking. If the filesystem prevents
   parking too, a second diagnostic reports that failure and RecorderFailure
   still reaches the drain. The original active bytes remain retained, execution
   locks close, and the failed entry is outside launchd's pending directory.
5. Active recovery contains errors per entry. An unreadable entry is logged and
   renamed to `.parked` without decoding it. Healthy pending work proceeds.
   Unrecoverable parking errors are reported after the drain attempts due peers.

## Reproduction

`round13_checks.py`, registered by suite 106, adds these named regression rows:

| Finding | Row | Baseline observation |
| --- | --- | --- |
| Profile/gate | AC1/v1-profile-migration | Product migration API missing |
| Missing index | AC3/missing-index-retries | Dispatch permanently parked |
| Startup recovery | AC3/refused-receiver-recovers-orphans | Orphan still active |
| Recorder | AC3/unwritable-outbox-reports-failure | Recorder failure silently swallowed |
| Active recovery | AC3/unreadable-active-isolated | PermissionError aborts the drain |

All five fail with product files from 71436363 in `before-106.log`. Baseline
103 and 104 runs reproduce 18 and 6 failures respectively. The recorder row
chmods the outbox root and active directory, using the actual non-root filesystem:
it does not stub OUT.failure or the park rename. The unreadable row chmods the
active file and verifies healthy delivery, quarantine and a second idle drain.
The missing-index row models an already loaded, unchanged launch agent; a real
Supervisor migration and retry finish the queued event without operator resend.

Intermediate failing runs are retained. The first 103 correction exposed the
historical fixture's missing wake method. The first 106 correction caught an
unversioned wrapper request's leftover heartbeat field; legacy behavior must
require an explicit v1 marker. Final selected-suite results and source/log
hashes are recorded separately. All selected runs report PARTIAL and are not
accepted unit or gate proof.
