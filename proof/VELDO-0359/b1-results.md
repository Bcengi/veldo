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

The receiver removes its endpoint on success, refusal and exceptions, before its end is recorded.
Its supervising Launch removes the reported directory identity only after reaping that receiver, and
drains final query counts. Removal never raises: a directory something else was put in is left, named
(left:ENOTEMPTY) on the final count line and in the receiver log, and the end is still recorded.
Each request's name and outcome is written to a file beside the run's records; the serving thread
writes nothing to the launch pipe, so answers do not depend on the Runner reading it.
An exclusive-creation collision never transfers ownership. There is no startup sweep. A leftover from
a dead receiver and Runner has no effect on another dispatch. The client never retries by opening a store.

## Fixture coverage

`157_veldo_0359_run_query` uses signed enrollment files, a real SQLite fixture, real Unix sockets,
a serving thread, and Python payload/receiver processes. The lifecycle harness retains production
Receiver.launch, Receiver._spawn, Receiver._finish, invoke, Launch._take and Launch._end_receiver. It
substitutes launch prerequisite checks, containment, the dispatch store and the end's scan, which belong
to other briefs. The payload
uses entry_gate with sqlite3.connect replaced by a failing sentinel and reaches its build decision.
The marker-off payload actually opens the fixture database. No model executable is invoked.

| Row | Observations |
|---|---|
| query/journey | Every station; run-check and bundle to an eligible build, plan hash, plan references, frontier offers/withheld and local callbacks, stored handoff/returned floor records, work floor join, executor context and ticket, stale ticket after a committed change, all four completion facts including true receipts, explicit completion_view, valid/stale/missing coordination, missing unit/dependency, authority override and an actual local replica, status model and text. Direct and remote answers/callbacks compare in order, ignoring only generated decision/offer identities and clock fields. Client authority opens are counted and refused, including failure paths. |
| query/scope | Foreign unit, member-as-unit, foreign reference/cycle, work unit at coordination, other checkout, unsupported attributes/requests, extra path field, oversized context, immutable coordinates, exact response fields and nested metadata, planted bodies, malformed replies, two concurrent repositories, thread-owned read-only transaction, dead receiver and transport deadline. Conversation hello has no repository; risky launch creates no query endpoint. |
| query/lifecycle | Exclusive creation, bind/listen/connection/readiness failure, no acceptance or payload on failed setup, late acceptance refusal, ready before acceptance, normal exit, killed payload, killed receiver with Runner cleanup, counts after final receiver output, A paused between bind/listen while B starts, and dead-receiver/Runner leftover. Fix round 1: removal observed from inside the receiver as the production _finish records the end; a file dropped in the endpoint directory; 3000 requests with no line on the launch pipe. Events, pipes and process exits synchronize the fixture; the one hang detector is 120 s and the protocol deadline is raised to it except in the two rows that exercise its refusal. |
| query/cost | Fix round 1. Module executions counted over 25 repeated entries: a frontier pass over a store-holding Gate executes none (and the Gate's module holds no frontier), direct floor entries none, served floor entries, replication requests and entry gates none. |
| switch/off | Absent/present marker, real direct read only in the marker-off payload, no inherited query variable, accepted switch sample and OFF status, marker changed after sampling, modes/contents ignored, symlink/directory/foreign-owner/stat-error invalid by name, symlink and directory markers refused by name at a real launch before acceptance, status on after removal. No ruleset claims in B1. |

## Falsifiers

Registered in scripts/check_teeth_mutations.py, finding 359: store359-events-dropped,
store359-query-any-unit, store359-query-fallback, store359-query-leak,
store359-query-startup-sweep and store359-switch-ignored, and the nine of fix round 1 listed below. The unset-query negative control in the suite
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
checks from the status suite's prerequisite closure; they fail identically at 994599e4d (fix round 1 below), so they are baseline failures; the PM-cycle rows passed on the required host route.

No AppArmor, bwrap or socat changes. The live-layout preflight remains for the first real installation.
The design's same-account query visibility and store-wide replication identities remain explicit.

The first build's final source commit was 1cb5bcf1b (superseded by fix round 1 below). Its B1 suite had 31 passed assertions, zero failed (five B1
row groups plus shared checks). The earlier four-suite selection has 135 passed, zero failed.
Personal setup has zero findings; mirrored templates, generated files and source boundary checks pass.
One pc2 invocation returned 97 because no execution slot was available; the normal retry ran without
changing tooling or bypassing admission. Queued host work was cancelled without stopping another job.

## Fix round 1 (review verdict FIX, findings 0 to 6)

What changed and why is in revision-notes.md, "B1 fix round 1". Final source commit 647d1f421.
No row of an existing suite was edited, loosened or skipped; the diff under scripts/suites is suite
157 and its manifest entry.

| Finding | Fix | Row or falsifier, red with the defect and green without |
|---|---|---|
| 0 three existing suites red | Receiver.launch keeps its body; cleanup is a module function a stand-in receiver tolerates; the VELDO-0024 status line is restored | The suites' own rows: 37 replica/status-pending, 127 ac3/one-decision and ac3/selftest-cached, and the six rows of 63_veldo_0040_containment. Cause of the six: _finish called a new method the suite's stand-in receiver does not have |
| 1 module reload per floor entry | Organs loaded once; the frontier passes its own reading | query/cost; store359-floor-reload, store359-frontier-not-own-reader |
| 2 stray file stops the end | remove, Server.close and close_query never raise; what is left is recorded | query/lifecycle stray-file rows; store359-cleanup-raises, store359-finish-cleanup-raises |
| 3 answers wait on the launch pipe | Per-request lines go to a file; the pipe gets one final count line after the end | query/lifecycle "answers do not wait for the Runner to read"; store359-log-on-launch-pipe |
| 4 LOAD RULE | One 120 s hang detector; the reached-peer check waits on its event | Suite text; no deadline below 120 s remains outside the two timeout-refusal rows |
| 5 two rows passed with the behaviour removed | Production _finish in the fixture, removal probed inside the receiver; invalid markers launched | store359-receiver-keeps-server, store359-invalid-marker-launches |
| 6 scope and wording | Acceptance value no longer added to the scan's own list; a conversation receiver serves no record; label corrected; scaffold row recorded as baseline | query/scope rows; store359-acceptance-own, store359-conversation-any-record |

Falsifiers: b1-mutation-controls.py at 647d1f421 on pc2: one whole-suite baseline and four no-ops pass,
fifteen mutants (the six of B1 and nine new) each turn their own row red; b1-mutation-results.json.

Suite 157 at 647d1f421 on pc2: 32 passed, 0 failed (six row groups).

Wider regression on pc2, base 994599e4d against head 647d1f421: the review's 17 suites were not
recorded by name, so every suite carrying one of its numbers was run, 24 in all (a superset).
Base 3556 passed, 151 failed; head 3556 passed, 151 failed over the same 24; no row is red at head
that is not red at base. Per-suite counts and times are in b1-fix1-regression.txt. The three rows
the review found red (suites 37 and 127) are green. 67_veldo_0135_offers takes 8.7 s at head against
11.4 s at base (171.75 s at the reviewed head). The 151 are baseline failures on pc2, identical at
both commits, including the starter-scaffold row of suite 03.

63_veldo_0040_containment in full through host_heavy at 647d1f421: 85 passed, 0 failed (base 85
passed, 0 failed; the reviewed head 79 passed, 6 failed). A first run of this round, one commit
earlier, was 84 passed, 1 failed on containment/observations: the store guard and query lines had
entered the launch's message trace, which that row reads as accepted, running, exited. They are now
kept in Launch.query_notices, apart from that trace. The six other host launch suites the review
ran were not rerun in this round.

Limits. The full verification script was not run, by instruction; nothing here is a gate result.
A foreign-owner and a stat-error marker are covered at the switch function only, since a fixture
cannot create them without privilege. The per-request log is capped at 1 MiB per dispatch; after
that the counts alone continue.
