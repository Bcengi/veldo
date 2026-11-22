# VELDO-0359 B1: receiver query readers

Scope: B1 only. Fixtures only, no live engine and no real store. No filesystem enforcement,
engine sandbox override, layout preflight, mount census, descriptor audit or writer migration.
The lead's B0 disposition and the two host-caused engine findings are recorded in revision-notes.md.

The endpoint is created exclusively under the receiver's runtime directory. Its serving thread opens
its own read-only connection from the installed receiver binding and signals readiness before acceptance.
One bounded JSON frame names one of six operations: hello, decide, decision_blockers, completion,
floor_entry or replication_status. There is no generic dispatch, SQL, connection or path argument.
The default local run receives VELDO_RUN_QUERY; reported and risky launches have no endpoint.
A valid store-guard.off restores the direct read path. Only the launch's sampled marker state is used.

The receiver removes its endpoint on success, refusal and exceptions. Its supervising Launch removes
the reported directory identity only after reaping that receiver, and drains final query counts.
An exclusive-creation collision never transfers ownership. There is no startup sweep. A leftover from
a dead receiver and Runner has no effect on another dispatch. The client never retries by opening a store.

## Fixture coverage

`157_veldo_0359_run_query` uses signed enrollment files, a real SQLite fixture, real Unix sockets,
a serving thread, and Python payload/receiver processes. The lifecycle harness retains production
Receiver.launch, Receiver._spawn, invoke, Launch._take and Launch._end_receiver. It substitutes launch
prerequisite checks, metering, containment and dispatch writes, which belong to other briefs. The payload
uses entry_gate with sqlite3.connect replaced by a failing sentinel and reaches its build decision.
The marker-off payload actually opens the fixture database. No model executable is invoked.

| Row | Observations |
|---|---|
| query/journey | Every station; run-check and bundle to an eligible build, plan hash, plan references, frontier offers/withheld and local callbacks, stored handoff/returned floor records, work floor join, executor context and ticket, stale ticket after a committed change, all four completion facts including true receipts, explicit completion_view, valid/stale/missing coordination, missing unit/dependency, authority override and an actual local replica, status model and text. Direct and remote answers/callbacks compare in order, ignoring only generated decision/offer identities and clock fields. Client authority opens are counted and refused, including failure paths. |
| query/scope | Foreign unit, member-as-unit, foreign reference/cycle, work unit at coordination, other checkout, unsupported attributes/requests, extra path field, oversized context, immutable coordinates, exact response fields and nested metadata, planted bodies, malformed replies, two concurrent repositories, thread-owned read-only transaction, dead receiver and transport deadline. Conversation hello has no repository; risky launch creates no query endpoint. |
| query/lifecycle | Exclusive creation, bind/listen/connection/readiness failure, no acceptance or payload on failed setup, late acceptance refusal, ready before acceptance, normal exit, killed payload, killed receiver with Runner cleanup, counts after final receiver output, A paused between bind/listen while B starts, and dead-receiver/Runner leftover. Events, pipes and process exits synchronize the fixture; deadlines detect hangs or exercise the specified timeout refusal. |
| switch/off | Absent/present marker, real direct read only in the marker-off payload, no inherited query variable, accepted switch sample and OFF status, marker changed after sampling, modes/contents ignored, symlink/directory/foreign-owner/stat-error invalid by name, status on after removal. No ruleset claims in B1. |

## Falsifiers

Registered in scripts/check_teeth_mutations.py, finding 359: store359-events-dropped,
store359-query-any-unit, store359-query-fallback, store359-query-leak,
store359-query-startup-sweep and store359-switch-ignored. The unset-query negative control in the suite
attempts the client open and gets unavailable_service:store. This distinguishes successful remote
reads from an accidental local-store path without requiring B2's ruleset.

## Checks and limits

The user's instruction prohibits the full verification script. All suite observations here are partial
runs, not a full gate result; the selftest dispatcher deliberately returns 2 on a partial run with zero
failed assertions. No canonical verification stamp, shipped status or independent verdict is claimed.

Portable suites run on pc2 using remote_run.sh --share at the recorded commit. The PM-cycle regression ran through host_heavy.sh (56 passed, zero failed). The additional dispatch,
offer and receiver-trust selection and the full mutation coordinator waited for host capacity; they
provide no completed result. The six mutations instead ran through the registered worker API on pc2,
with a whole-suite baseline and one no-op per changed module, all passing. The reproduction helper and
its output are b1-mutation-controls.py and b1-mutation-results.json. Exact summarized results are in
b1-results.json. The launch-hygiene suite's seven failing rows also fail at the original 994599e4d
baseline on pc2, with the same row names; they were not changed by this brief. The first broad
regression selection also included PM-cycle fixtures requiring a user manager and two starter-scaffold
checks from the status suite's prerequisite closure; the scaffold results remain unresolved; the PM-cycle rows passed on the required host route.

No AppArmor, bwrap or socat changes. The live-layout preflight remains for the first real installation.
The design's same-account query visibility and store-wide replication identities remain explicit.

The final source commit is 1cb5bcf1b. Its B1 suite has 31 passed assertions, zero failed (five B1
row groups plus shared checks). The earlier four-suite selection has 135 passed, zero failed.
Personal setup has zero findings; mirrored templates, generated files and source boundary checks pass.
One pc2 invocation returned 97 because no execution slot was available; the normal retry ran without
changing tooling or bypassing admission. Queued host work was cancelled without stopping another job.
