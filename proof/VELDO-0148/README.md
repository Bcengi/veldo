# VELDO-0148 proof

A land refused because another factory moved main ends its original dispatch. The installed
factory service offers a new land dispatch, with a new watermark, merge, candidate gate and
compare-and-swap. A conflict returns to the builder and then review. A lost lease is refused
only when the fetched destination tip does not contain the candidate; containment stays unknown.
A prior grant is bound to the candidate tree. Replacement requests are allowed only when every approval problem is a tree-only binding
mismatch for a prior grant at this revision. A mixed refusal keeps no subject and asks no question.
A grant is applied at most once per dispatch, failed dispatches never receive a grant, and the
station rechecks every prior grant before writing any replacement.

Suite: `scripts/suites/86_veldo_0148_re_land.py`, registered with its own prerequisite closure.
It drives real Git repositories and a disposable bare remote, the SQLite store and signed
production writers, build and review child processes, the floor and proof services, the lander,
installed candidate gate, effect executor and publication receipts. The authority service and
factory loop load from the installed executable closure and are stepped synchronously through
their production interfaces. Signed requests use Authority.judge; real receiver children still
run the installed launch executable. Another local clone moves the remote before listing or in the
publication clone's pre-push hook. Engine output comes from a generated fake; no real model,
login, external service or real credential is used. Each row reports once.

## Census binding review repair at 3caa6d1c

Group.retain now binds the seven libsystemd functions through explicit attributes
and passes bound functions to checked. Argument types, return types, bus calls,
cleanup and OSError names are preserved. Both containment copies are identical.
The census remains unchanged. [census-binding.json](census-binding.json) records
the baseline assertion failure in VELDO-0169 census/writers and its passing
rerun in the empty gate environment. The matching suite selector is
84_veldo_0169_project_handouts. These scoped runs are not a full gate verdict.

The census suite and suites 86 (re-land), 63 (containment), 67 (heartbeat),
80, 81 and 62 (dispatch) each pass alone in ordinary and empty gate
environments: 14 runs, zero failures, expected partial-run exit 2. The gate
environment includes the supplied runtime directory and session bus.
Requires.json regenerated unchanged; Git boundary and validate.py all pass,
and the anchor check reports 0 bad anchors. The footprint checker still reports
the same 58 inherited paths outside the footprint as at 3caa6d1c; this repair
adds none. The alternate scratchpadanchor_check.py path is absent.

The existing criterion red records and 27 finding-148 mutations are preserved.
The proof driver, mutation runners, full selftest and gate were not rerun, in
accordance with the token rules. No proof/VELDO-0127 files were changed.

## Report handshake review repair at 1ab79713

The wrapper starts its five-second startup budget before its identity line, which
precedes the receiver's release by construction. It checks that budget immediately
before reporting success and executing the engine. The receiver keeps its bound
from the same SETUP_SECONDS constant, plus SETTLE_SECONDS and one second for the
report. A wrapper stalled after release cannot reset its deadline. EOF before a
report is now heartbeat_wrapper_exited, distinct from heartbeat_report_timeout.
Only control_launch.py and its byte-identical engine copy change in production.
No footprint expansion is needed.

Three suite-86 rows drive the real contained receiver and wrapper in disposable
scopes. The fixture wraps the real release reader and injects a fault only after
it consumes the receiver's release. Each row checks the fault was reached, the
named refusal, settled containment and absence of the engine's marker.

| Row | Fault and assertion | Finding 148 falsifier |
| --- | --- | --- |
| receiver/report-timeout | SIGSTOP leaves the wrapper unable to answer; the receiver returns heartbeat_report_timeout. An outer timeout becomes an assertion failure. | receiver148-report-wait-unbounded |
| receiver/late-wrapper | Delay after release exceeds the wrapper budget; heartbeat_timeout is returned and the engine never executes. | receiver148-late-wrapper-execs |
| receiver/wrapper-exited | Wrapper exits immediately after release; EOF is heartbeat_wrapper_exited. | receiver148-wrapper-eof-is-timeout |

[red-at-1ab79713.json](red-at-1ab79713.json) was collected before the production
edit. Late-wrapper and wrapper-exited fail by assertion, with no raised row and
all other rows green. Report-timeout is necessarily green on this baseline: the
seven-second receiver bound already exists. Its negative proof is the unbounded
poll mutation, not a fabricated baseline failure. The baseline record was
committed separately as 6f66e56e.

The proof driver's report-mutants mode reads the three registrations as syntax
and applies each to a disposable archive, then invokes only suite 86, one at a
time. It never executes the mutation checker. The normal proof-driver mutation
mode and the full mutation checker remain reserved for the reviewer.
[manual-report-mutants.json](manual-report-mutants.json) records all three new
mutants rejected by assertion, each with only its own named row red. The unbounded
poll hits the fixture's outer timeout while the wrapper remains stopped. All 27
finding-148 registrations have refreshed exact diffs and source/mutant digests in
[mutations.json](mutations.json); execution evidence is current for these three,
with the other registrations explicitly left for reviewer execution.

[handshake-verification.json](handshake-verification.json) records 14 passing
selectors: suites 86, 62 (dispatch), 63 (containment), 67 (heartbeat), 80, 81 and
82 (execution record), serially in ordinary and exact empty gate environments.
Every gate run uses a fresh HOME in /dev/shm and the specified session bus.
Each returns the expected partial-run exit 2 with zero failures. These scoped
checks are not a full gate verdict. Requires.json was regenerated unchanged.
The Git boundary check passes, all mutation anchors are unique (0 bad), and
validate.py all exits 0. No protected path changed.

The supplied footprint checker compares origin/main to HEAD and reports 58
inherited out-of-footprint paths, already present at baseline 1ab79713. The
repair-only comparison has none, as recorded in
[handshake-footprint.json](handshake-footprint.json). The spec footprint was not
expanded to include unrelated inherited work. The alternate path ending in
scratchpadanchor_check.py does not exist; the supplied scratchpad/anchor_check.py
was used. The full selftest, gate, mutation checker and load tests were not run,
following the explicit token and concurrent-gate restrictions.

## Fast-exit review repair at e1009abc

The heartbeat previously moved itself only after enumerating its inherited file
descriptors. The intermediate child had already exited, so the wrapper could exec
a fast engine while the heartbeat still belonged to the worker cgroup. That made
an ordinary exit look like a surviving engine descendant needing termination.

The intermediate child now enters `veldo-wrapper` before its second fork. Its
heartbeat inherits that membership. The wrapper waits for successful intermediate
child exit before exec, and refuses startup if setup failed. Session separation,
pidfd lifetime, descriptor isolation, scope caps and subtree cleanup stay intact.
The engine copy is byte-identical. Only control_heartbeat.py and its engine copy
were added to the footprint, for AC1's clean conflict rebuild and review exits.

The new `receiver/fast-exit` row instruments disposable module copies with FIFOs.
At `_beat` entry, before descriptor enumeration, the heartbeat announces its real
PID and cgroup to the fake engine and blocks. The engine consumes that announcement
and exits zero. The receiver samples real `Group.members()` before releasing the
heartbeat. The row asserts that both heartbeat PIDs already belong to the wrapper
cgroup, both membership samples are empty, and both exits have no cause or stop
steps. There is no scheduler sleep. Existing normal-exit and settled-scope rows
continue to check real launch records, live supervision and retained manager state.

[red-at-e1009abc.json](red-at-e1009abc.json) records the pre-fix replay: the new
fast-exit row and existing normal-exit row fail by assertion, all other suite rows
pass. Both launches return zero yet receive cause `exit` and a terminate step;
the recorded cgroup samples contain the held heartbeat PIDs. The red driver uses
a read-only archive and neither checks out nor changes another branch or worktree.
Earlier red records below cover the original AC1, AC2 and AC3 behavior changes.

Finding 148 now has 22 registered mutations. The new
`receiver148-heartbeat-moves-after-exec` restores late movement and targets
`receiver/fast-exit`. [mutations.json](mutations.json) records current source and
mutant digests, exact diffs and named rows. All anchors and mutant syntax were
checked, including finding 40's existing anchors. Mutation execution, five
consecutive finding-148 baselines, finding 40 execution and the whole selftest
remain for the reviewer under the explicit token rules. No new mutation rejection
or gate verdict is claimed.

[fast-exit-verification.json](fast-exit-verification.json) records all 12 serial
selector runs: suites 86, 63, 67, 80, 81 and 62 each pass in the ordinary environment
and the exact empty gate environment with a fresh HOME in /dev/shm and the named
session bus. All return the expected partial-run exit 2 with zero failures.
Suite 86 reports 19 rows, 45 including the shared preamble. These scoped runs do
not constitute gate evidence. The saved pre-fix replay predates the production
edit, so its source hashes labeled `now` still equal the archived pre-fix hashes.

The anchor checker reports 0 bad anchors and no duplicate names; validation and
the Git boundary check pass. Suite registration is unchanged and requires.json
regenerates unchanged. The single-spec footprint checker still reports 58
inherited VELDO-0040 and VELDO-0127 paths; this repair has none outside VELDO-0148,
and checking all three merged concerns reports none outside. The separately
requested scratchpadanchor_check.py path does not exist; the supplied
scratchpad/anchor_check.py is the working checker. Gate byproducts are restored
and excluded before the final commit. Nothing was pushed.

## Receiver regression repair at a90e5a85

The read-only archive bisect in [receiver-bisect.json](receiver-bisect.json) identifies
`0f289ab824e7aa88ef6271cb0d8a664ca676876f` as the first bad commit. Each probe runs
suites 67, 80 and 81 serially in the exact empty gate environment, with the session
bus explicitly named. Both main f1e1abb9 and the first bad commit's parent 9572210b
pass all three. No branch or other worktree was checked out or changed.

That commit unconditionally assigned cause `exit` to a clean adapter completion,
replacing the established absence of a stop cause. Its new LoadState check also
correctly rejected the default success printed for an already collected scope,
but successful scopes had no reference keeping their actual terminal result
available. Removing that guard would lose the containment work's uncertainty rule.

The receiver now acquires a private libsystemd RefUnit connection for its own scope
before releasing the wrapper. It reads the real loaded terminal result and clocks,
then Group.close releases the connection. The connection also drops on receiver
death, and is created after spawning the wrapper, so the engine never inherits it.
This uses Python ctypes and the Linux provider's existing systemd library, with no
new Python package. The manager-call timeout remains TOOL_SECONDS. The loaded-state,
terminal-state and settle-budget checks are unchanged. Explicit stops, runtime-cap
inference and retained OOM evidence still precede ordinary completion. Clean
completion keeps the actual cleanup cause if one exists and otherwise has no cause.

Suite 86 now runs its real conflict rebuild and review as local contained workers,
using its existing profile and fixture engine, and stops only its own transient
slice at teardown. It adds two rows:

* `receiver/normal-exit`: both production launches exit zero with live heartbeat,
  empty group, no stop steps and no stop cause.
* `receiver/settled-scope`: both launches retain the actual manager success and
  ordered terminal clocks, instead of accepting a collected unit's defaults.

The heartbeat and engine-baseline failing rows are unchanged. Suite 63's
`empty-ordinary-after-cap-unknown` controls incorrectly required cause `exit` even
though they model an already empty group with no inferred stop. Their exact
expectation is now None, plus explicit assertions that no stop was inferred and
no steps occurred. Every after-cap unknown assertion is preserved, and every other
suite-63 assertion is unchanged. The finding-40 normal-exit mutation keeps its row
and follows the corrected production expression.

[red-at-a90e5a85.json](red-at-a90e5a85.json) records both new suite-86 rows red by
assertion, with its previous rows green. The same file records the unchanged
`heartbeat/blocked-call-liveness`, `heartbeat/engine-group-signal` and both
`strip/user-manager` rows red by assertion through normal selftest selectors.
The proof driver's red mode can include these serial receiver regression runs with
its receiver-regressions option; no mutation driver is loaded in that mode.

Suite 63 passes alone at a90e5a85 as well as after this repair in the gate environment.
The supplied mutation-stage `invalid_baseline` label does not name the failed row;
its exact cause cannot be established from that label. The reviewer must supply its
failing assertion detail or rerun finding 40, including containment-result-before-settled.
Mutation and full-gate execution are prohibited during this builder run. No new
mutation rejection is claimed. All 21 finding-148 registrations, including the two
receiver falsifiers, have current hashes, exact diffs and unique compiling anchors.

The repair adds only the two production modules, their engine copies and suite 63
to the footprint, and project_runner to placement. These are needed by AC1's real
rebuild and review completion. The supplied footprint checker compares the entire
branch to origin/main and also sees inherited VELDO-0040 containment evidence and
VELDO-0127 live-capture files. Those pre-existing paths are not added to this spec's
footprint. Checking the three merged concerns together reports none outside; the
repair delta alone is fully inside VELDO-0148. The alternate supplied path ending
in scratchpadanchor_check.py does not exist; scratchpad/anchor_check.py does.

The detailed [verification record](receiver-verification.json) has 12 green
selector runs: suites 62 dispatch, 63 containment, 67 heartbeat, 80 Claude baseline,
81 Codex baseline and 86 re-land, each in ordinary and empty gate environments.
All run one at a time. Suite 86 has 18 passing rows, 44 with the shared preamble.
The other totals with the preamble are 47, 78, 49, 44 and 48 respectively. Selector
exit 2 is expected and does not claim a full gate. Validation and Git-boundary
checks pass, the anchor checker reports zero bad anchors and no duplicate names,
both changed engine copies match, suite registration remains singular, and
requires.json regenerates unchanged.

## Criterion rows

| Criterion | Row | What it proves |
|---|---|---|
| AC1 | `install/land-station` | The installation and scaffold include the land station and its production dependencies; malformed station configuration is refused by name; engine copies match and service passes have wake sources. |
| AC1 | `reland/stale-subject` | A stale-subject refusal ends the original dispatch without another attempt under it. Exactly one new dispatch follows, takes the new watermark, re-merges unchanged build evidence, re-gates and lands with its own receipt. Status counts dispatches and refusals. |
| AC1 | `reland/review-kept` | A clean re-merge retains the review of the unchanged evidence commit and the existing floor record, without another build or review. |
| AC1 | `reland/conflict-rebuild` | A real merge conflict publishes nothing, names the conflicting path and offers one new build instructed to merge the new main, followed by that build's review. |
| AC1 | `reland/end-wakes-pass` | Actual conflict and approval land ends queue their dispatch wakes. An immediate second loop call consumes those wakes and starts the next pass without a timer, pipe event or added journal command. |
| AC1 | `reland/never-forced` | Every recorded remote update is a fast-forward and every publication uses the exact watermark of its own land as its lease. |
| AC2 | `lease/trunk-moved` | A push between listing and publication loses the lease; the executor fetches the moved tip, refuses as trunk-moved and the service re-lands under a new dispatch. |
| AC2 | `lease/contains-unknown` | A moved tip containing the candidate remains unknown, judged at the push URL; its named stop leaves no receipt, retry or re-land. |
| AC3 | `grant/never-granted` | A never-granted security approval is refused by name, sends no owner question and writes no approval or publication. |
| AC3 | `grant/mixed-approvals` | A mismatched owner grant and missing security approval stay failed with both named reasons, no subject, question, approval write or loop action. |
| AC3 | `grant/mixed-proof` | An owner tree mismatch together with a security proof-only mismatch stays failed with both reasons and no subject, question or grant. |
| AC3 | `grant/once-per-dispatch` | Replaying an applied grant emits no accepted event and writes nothing. Three extra loop passes grow neither accepted events, refused entries nor approvals. A failed dispatch persisted through the station writer with G's real replacement subject and eligible prior grant refuses a direct grant without an approval write or accepted event. |
| AC3 | `grant/revoked-before-answer` | The owner answers a real question after security is revoked. The station refuses security by name before writing any replacement, including the still-valid owner grant. |
| AC3 | `grant/fresh-request` | The old tree's grant is refused by name for the re-merged tree without publishing. One owner request survives repeated passes; answering creates an exact-tree grant and the next dispatch lands that tree. |

The control row `format/fake-lines` checks each scripted engine event against the captured binary
format. The separate VELDO-0172 row `fake/capture:0148_re_land` drives the installed fake through
the shared conformance checker.

The new approval rows drive the final authorization with an owner policy update after the real
CandidatePolicy accepts and before Landing publishes. This reaches the final approval check even
though a missing approval already present at the earlier policy check stops there. These rows use
the signed store writer, real land station, installed service inbox and signed owner answers.

## Deterministic scheduling repair

At 7ee372ed, setup and every wait shared a 100-second wall-clock deadline. Socket
startup had 10 seconds; state waits had 20 seconds and polled every 50 milliseconds.
The first missed wait set a shared stalled flag, making every later wait return
immediately. A land end could be visible before its pass report was appended, and
waiting for any later pass did not establish that the desired action had completed.

The four reported failures shared the unfinished approval journey:

* `reland/stale-subject` also checks final station metrics, including G's third land
  and its resulting outcome. An unanswered approval leaves those counts incomplete.
* `reland/never-forced` checks at least eight publications and trunk updates. G's
  final publication supplies part of that evidence, so a stalled journey missed it.
* `grant/fresh-request` needs the pass after G's second land to open its question,
  then an answered question and a completed third land before comparing trees.
* `grant/once-per-dispatch` needs that replacement grant before replaying it and
  comparing accepted events and approvals across three completed later passes.

The suite now finishes each production pass before taking snapshots. An explicit
signed journal command drives the pass needed by the behavior rows independently
of the land-end wake. Actual launch-pipe events drive rebuild and review completion;
no pipe means there is no child event left to await. The wake row is isolated before
that explicit command and checks the real queued dispatch identities and next pass.
The original behavior assertions remain, including the metrics and minimum counts.

There is no scenario deadline, stalled flag, sleep or polling-count verdict.
Subprocess I/O bounds (formerly 20, 60 or 120 seconds) are 600 seconds. Build/review
dispatch deadlines and the installed runtime bound are 600 seconds; the installed
role allowance was increased from 240 to 600. Launch-pipe waiting has a monotonic
600-second stuck-child bound. Teardown requests stop and waits for each owned launch
with a 30-second bound. Time readings otherwise supply real production timestamps
and elapsed-time reporting. Two grant replays and three extra passes are explicit
behavior checks, not polling attempts. No production timeout or code changed.

## Red record

[red-at-ad916989.json](red-at-ad916989.json) preserves the earlier suite replay against an unchanged archive
of the original pre-concern commit: its 14 behavior rows fail by assertion and the format control
stays green. [red-at-b33e82f8.json](red-at-b33e82f8.json) preserves the earlier suite replay against the commit
before the first review repair: its two new approval rows fail by assertion; the existing rows stay green.
[red-at-f59b3136.json](red-at-f59b3136.json) records this re-check: all four changed or new
behavior rows fail by assertion, with the existing behavior and format rows green.
No exception counts as evidence. [drive.py](drive.py) records module digests and assertion details.

[manual-failed-state-guard.json](manual-failed-state-guard.json) records the proof repair's
manual experiment: copy the station module into a temporary tree, restore only the old
state guard, then run this suite through drive.run's production-copy anchor. Only
`grant/once-per-dispatch` fails, by assertion; the original production file is unchanged.
The record carries the exact replacement, source, mutant and suite digests and failure detail.
To replay, apply [the guard diff](grant148-failed-dispatch-accepted.diff) to a temporary
copy and pass its absolute path as the `control_landing_station.py` entry to drive.run.

[red-at-41340bc1.json](red-at-41340bc1.json) is the requested replay against the commit
immediately before this proof repair. It has no red rows: that commit already has the
correct production guard. It is a green control, not evidence of a production regression.
The refreshed original ad916989 record supplies all 14 behavior rows red by assertion;
the manual guard revert supplies the specific falsification for this repair.

[red-at-7ee372ed.json](red-at-7ee372ed.json) records the current suite against the
immediate pre-repair commit. It is green: this is a proof-only repair and that commit
already implements all production behavior. Making every behavior row red there
would misrepresent this change. The original implementation baseline above supplies
the complete red record. [manual-wake.json](manual-wake.json) supplies this repair's
specific falsification: only `reland/end-wakes-pass` is red, by assertion; every other
finding-148 row stays green, including all four reported timing failures.
Replay the isolated copy experiment with the proof driver's `--wake-only` option.

## Mutations

[mutations.json](mutations.json) records the lead's reported run at f59b3136: 14 of 14
mutations rejected. This is attributed evidence supplied in the owner's brief, not a builder run.
It separately records all 21 current finding-148 registrations, source and mutant digests, exact
applied diffs and named rows. Their anchors and syntax are statically checked; execution on this
repair is pending for all 21. The manual wake and historical state-guard experiments are recorded separately;
no mutation-checker rejection is claimed for this repair.
[mutations-before-review.json](mutations-before-review.json) preserves the earlier builder's
12 rejections as historical evidence.

The repeated-question mutation varies both alias and command identity. The updated missing-grant
mutations restore an invalid replacement subject. The four added mutations restore the mixed-case
question, allow a proof mismatch, reapply a grant and overwrite a revoked approval.

| Mutation | Named row |
|---|---|
| `receiver148-clean-exit-invents-stop` | `receiver/normal-exit` |
| `receiver148-success-collected-before-read` | `receiver/settled-scope` |
| `reland148-stale-left-failed` (AC1 falsifier) | `reland/stale-subject` |
| `lease148-loss-unknown` (AC2 falsifier) | `lease/trunk-moved` |
| `grant148-old-tree-accepted` (AC3 falsifier) | `grant/fresh-request` |
| `reland148-loop-offers-nothing` | `reland/stale-subject` |
| `reland148-conflict-relanded` | `reland/conflict-rebuild` |
| `reland148-rebuild-not-reviewed` | `reland/conflict-rebuild` |
| `reland148-landed-rebuilt` | `reland/review-kept` |
| `reland148-end-wakes-nothing` | `reland/end-wakes-pass` |
| `lease148-contained-refused` | `lease/contains-unknown` |
| `lease148-tip-not-fetched` | `lease/trunk-moved` |
| `never148-forced-push` | `reland/never-forced` |
| `grant148-asked-every-pass` | `grant/fresh-request` |
| `grant148-missing-treated-as-replacement` | `grant/never-granted` |
| `grant148-replacement-includes-missing` | `grant/mixed-approvals` |
| `grant148-mixed-question-restored` | `grant/mixed-approvals` |
| `grant148-proof-mismatch-replaceable` | `grant/mixed-proof` |
| `grant148-applied-again` | `grant/once-per-dispatch` |
| `grant148-failed-dispatch-accepted` | `grant/once-per-dispatch` |
| `grant148-revoked-overwritten` | `grant/revoked-before-answer` |

## Replay

Run the suite with `python3 scripts/selftest.py --suite 86_veldo_0148_re_land`.
Replay the original red record with `python3 -B proof/VELDO-0148/drive.py --red ad916989`, or the
earlier review regression with `python3 -B proof/VELDO-0148/drive.py --red b33e82f8`, or this
re-check with `python3 -B proof/VELDO-0148/drive.py --red f59b3136`.
For reviewer use, `python3 -B proof/VELDO-0148/drive.py` regenerates mutation evidence with at most
two workers. The builder did not run that mutation mode or the mutation checker.

## Earlier deterministic repair checks

The repair from 7ee372ed changes no production bytes or acceptance criteria, and
needs no footprint expansion. [verification.json](verification.json) records the
normal, empty gate-environment and loaded runs. Each of those runs
passes all 16 suite rows (42 including the shared preamble), with zero failures and
the expected subset exit 2. These are partial checks, not a full gate verdict.
[verify_load.py](verify_load.py) owns one load process with 18 busy native threads
on the 20 available cores, runs only suite 86, then terminates and reaps that exact
PID. [cpu-load.json](cpu-load.json) records 429.6 CPU-seconds of artificial load
during the 25.15-second suite run and confirms the process was reaped.

[refresh_mutations.py](refresh_mutations.py) reads the registry as syntax without
executing it. It refreshes all 19 exact diffs and source/mutant hashes, checks unique
anchors and compiling mutants, and asserts that no other mutation target changed.
The manual wake experiment alone demonstrates a new rejection; the other 18 are
registered for reviewer execution. The suite registry describes the new wake row,
and requires.json was regenerated. Full gate and mutation checker execution remain
reserved for the reviewer. The supplied footprint checker reports 55 paths with
none outside; the anchor checker reports 0 bad anchors and no duplicate mutation
names across findings. Validation exits 0 and all eight engine copies match.
Production readers and writers of loop wakes, pass reports, signed requests and
grant events were searched alongside their suite consumers.

## Earlier completion checks

The proof repair at 41340bc1 changes only the suite, mutation registration and proof
records within the existing footprint. Suite 86 passes in ordinary and empty gate
environments, serially: 15 suite rows, 41 including the shared preamble, zero failures,
expected subset exit 2. All 19 saved diffs were applied to disposable copies and their
resulting SHA-256 digests checked against mutations.json. All eight engine copies match.
The suite remains registered once and requires.json was regenerated unchanged. The
supplied footprint and anchor checks report nothing outside and 0 bad anchors;
validate.py all exits 0. The manual guard revert is the one new rejection demonstrated
here. The 19 registered mutations await reviewer execution through the mutation checker;
the lead's 14 earlier rejections remain historical evidence.

The 2026-09-29 adaptation after main 82b185f2 adds only the runtime-directory copy to
the suite fixture, matching VELDO-0186's suite 83 change. The fake Codex already has
its production-generated qualification record and executable binding. No production
module, assertion, acceptance criterion or footprint changed. Repair commit b3e40a45
passes all 15 suite rows in both ordinary and empty gate environments, serially
(41 with the shared preamble, zero failures, expected subset exit 2).

The current suite was replayed against the original pre-implementation ad916989:
all 13 behavior rows fail by assertion, with the format control green. This is the
original implementation's red baseline; bf035770 already contains that behavior
and this adaptation repairs its fixture. All 18 mutation registrations have valid
anchors and syntax. That adaptation claimed to refresh seven service digests and
diff offsets, but left stale records. The proof repair at 41340bc1 regenerates all
19 registrations from current production bytes: the registry's ordered replacements,
SHA-256 of source and mutant bytes, and difflib.unified_diff with n=0, following
drive.py and the recent VELDO-0169 proof. The seven control_service.py entries now
bind source digest e7f3b51fdd1f9ab1e8386ed0858f31fadeb07d198b6980b65f086f65b6970e75.
No mutation checker was executed;
the recorded 14 rejections remain historical. All eight production modules match
their engine copies, requires.json was regenerated unchanged, the supplied footprint
check reports 46 paths and none outside, and the anchor check reports 0 bad anchors.
Validation passes. Full gate and mutation execution remain with the reviewer.

This re-check runs only suite `86_veldo_0148_re_land`, serially, in the ordinary environment
and the requested empty gate environment. These are partial checks, not a full gate verdict;
subset mode intentionally exits 2. Final counts and the footprint, anchor and validation results
are recorded in the specification History. Both environments pass 15 suite rows (41 with shared
preamble), zero failures. The footprint check reports 46 paths, none outside; the anchor check
reports 0 bad anchors and validation exits 0. Engine copies match their repository counterparts.
The suite remains registered once and requires.json was regenerated. No other suites, full gate
or mutation checker ran in this repair.


## Bytecode-cache FIFO fixture follow-up

The suite-12 closure fixture used a metrics invocation to create `__pycache__` before
installing its FIFO. With `PYTHONDONTWRITEBYTECODE=1` that directory never appeared.
The fixture now creates the parent of `cache_from_source(validate.py)` explicitly,
without warming the engine. The FIFO is itself the cache entry a module load would
open; a compiled file is unnecessary. All twenty surface/path checks remain intact.

[bytecode-cache-followup.json](bytecode-cache-followup.json) records the scoped suite
runs with and without the flag, the cache-assumption audit, and the negative control.
These are targeted regression results, not a gate result or a landing verdict.
The full selftest, integration first-use check (which runs the full selftest), gate,
and mutation runners were not run, as instructed.

[bytecode-cache-mutant.patch](bytecode-cache-mutant.patch) reproduces the negative
control: apply it to the repaired suite, run the same suite selector with bytecode
writes disabled, then restore the suite. It changes only the cache cell's relocated
engine diagnostic to omit the cache filename, leaving every assertion unchanged.
The patch is evidence for replay and is not applied to the committed suite.


## Runtime cap during concurrent manager reloads

The gate0148l journal identifies a shared-manager stall, not a later cap origin or
late receiver observation. At monotonic 2695544.483654 the user manager began a
994 ms daemon-reload across three scope deadlines. All three scopes then received
TERM at 2695545.862, as both manager ActiveExitTimestampMonotonic and the children's
TERM logs attest. Their activations were 2695543.301358, .375281 and .447167.
[The journal excerpt](runtime-cap-manager-journal.txt) preserves the original host
evidence; [the investigation](runtime-cap-investigation.json) preserves the clone
comparisons. The mutation stage reused shared controls across its 22 failing cases.

Sixteen simultaneous suite-63 runs in separate detached clones and the gate's fixed
environment pass on both 8af57369 and f1e1abb9 without reloads. Replaying the observed
reload interference delays enforcement on both: five branch runtime rows fail the
existing beat bound; main's sixteen runtime rows fail its older result attribution,
and its actual first TERM is also delayed. Thus VELDO-0148 did not introduce the
manager stall, and measuring from activation is correct. On the branch, traced
attach, retain and heartbeat setup maxima were 51, 24 and 30 ms respectively.
Conclusion runs after the group is empty and cannot cause continued child beats.

The receiver now includes the saved scope activation plus RuntimeMaxUSec in its
existing event wait. At expiry it sends TERM directly to the whole group and uses
the existing kill grace, without waiting for the manager or adding cooperative
grace. RuntimeMaxSec remains installed. Receiver enforcement records timeout even
when the manager, resuming later, records success; manager_result remains separate.
The new deterministic row proves enforcement with a live adapter and a manager
that reports success, including 0.4 seconds of startup already spent.

The live runtime row retains the original 2.7-second last-beat bound. It also checks
the child's first monotonic TERM by activation +1.2+0.5 seconds: the former bound
alone could hide a one-second enforcement delay inside its grace and slack. The
new mutation installs a cap one second late and changes its readback expectation
so the engine really runs; it leaves the owner's profile and every row assertion
unchanged. The receiver-only omission has a separate deterministic falsifier.

[runtime_parallel.py](runtime_parallel.py) invokes only
`python3 scripts/selftest.py --suite 63_veldo_0040_containment`; `--ref` selects a
commit and `--out` a new absolute scratch directory. It never runs a gate or mutation
checker. `--rounds 5` repeats sixteen concurrent runs, `--trace` times the startup
paths, `--reload` reproduces the observed manager interference, and `--delay-cap`
applies the exact timing fault to disposable production copies. Successful row
observations are exported without changing assertions. Scoped subset exit 2 is
expected; these results never certify a gate or landing.


Final checks on implementation `fb7a9cd1` are recorded in
[runtime-cap-verification.json](runtime-cap-verification.json), with source digests,
per-run assertions, activation/TERM/beat times, reload intervals and mutant hashes:

- Five successive sixteen-way honest rounds: 80/80 runtime rows green and zero
  failures in every complete scoped suite. Latest first TERM: activation +1.2040s.
- Five successive sixteen-way rounds with three manager reloads across the cap in
  each round: 80/80 runtime rows green, zero scoped-suite failures. Latest first
  TERM: activation +1.2024s; maximum memory sample time: 0.000223s.
- The [one-second-late production mutant](runtime-cap-one-second-late.diff) fails
  `containment/runtime-cap` in all sixteen clones, always including cap_stop_bound.
  The independent receiver timer omission fails only its new deterministic row.
- Serial suite 63: 54 suite rows, 80 including shared preamble, zero failures.
  Suite 86: 24 suite rows, 50 including shared preamble, zero failures. Honest
  scoped runs exit 2 as required; both negative controls exit 1.
- Canonical/root production copies match, changed modules compile, the 27 existing
  finding-148 mutation diffs and hashes are statically refreshed, and the new
  registrations plus the updated cooperative-stop anchor are unique and compile.

The missing receiver-timer mutation is a diagnostic of actual enforcement: merely
inferring timeout afterward from a late adapter signal cannot satisfy its
`Stop.cause == runtime_cap` assertion. The late-cap mutation changes no test
assertion or owner profile. No whole selftest, gate, mutation checker or push ran.

## Heartbeat setup clock follow-up

The original gate0148o failure has **not been reproduced**. Its 43 invalid case
results reuse two failed no-op controls (34 dispatch.py cases and nine executor.py
cases). Neither the original record nor the journal identifies a heartbeat
refusal for those controls, so attributing them to the five-second bound would
exceed the evidence.

[load-followup.json](load-followup.json) records the comparisons on 62adf17b and
f1e1abb9, with sixteen disposable clones, one selected suite per process, and the
gate environment. It also records five no-op rounds, a private-bin gate-environment
round, three mixed rounds with containment, and six further rounds without
receiver/wrapper timing instrumentation. All completed suites passed. The initial
comparison's PATH was /usr/bin:/bin; the later gate-environment runs reproduce the
private python3 symlink as well. Some of the further untraced rounds overlapped the
new deterministic regression and are explicitly not quiet-machine comparisons.
Temporary phase/refusal instrumentation existed only in the disposable clones.

The largest identity-to-final-setup-check interval in the branch's ordinary
sixteen-way runs was 0.135501 seconds. Across the five no-op rounds, the maximum
was 0.129836 seconds, including heartbeat placement of at most 0.038162 seconds.
Main's maximum identity-to-release interval was 0.071123 seconds. These measurements
do not justify increasing SETUP_SECONDS.

A separate deterministic regression proves a clock-origin defect. Delaying the
receiver's preparation by 5.250 seconds before release causes the old wrapper to
refuse a healthy launch with `spawn_failed:containment:heartbeat_timeout`; the
engine never starts. [release-origin-red.json](release-origin-red.json) records
that sole failing row against unchanged production. This injected delay proves
the defect but does not establish the cause of gate0148o.

The receiver now sends an absolute monotonic deadline with its release, after
containment preparation. The wrapper uses that deadline at its existing final
setup check. The five-second setup allowance, placement timeout, seven-second
report wait, and activation-based runtime cap remain in force. A wrapper delayed
after consuming the release cannot reset its deadline. The release parser rejects
nonfinite or invalid deadlines and leaves the following engine packet unread.

The new row tests delayed preparation and the release parser. Two new launch
mutations restore the early origin or restart the deadline after reading the
release; a third accepts an infinite deadline. The existing late-wrapper, frozen
wrapper, placement failure, placement timeout, and containment escape falsifiers
continue to exercise the production boundary.

[review_parallel.py](review_parallel.py) reproduces the honest comparison without
instrumentation or fault injection, for example:

```
python3 proof/VELDO-0148/review_parallel.py --ref 07ffafc4 --out /tmp/review-origin-check --rounds 5
```

It invokes only the two selected selftests, writes every log under the fresh output
directory, and records each run in results.json. Selected selftest exit 2 is
expected; none of these results is a gate stamp or landing approval.

[release-origin-verification.json](release-origin-verification.json) records the
completed checks on implementation 07ffafc4:

- Five rounds of sixteen honest runs for each review suite: 80/80 floor and 80/80
  proof runs green, with no timing instrumentation or concurrent extra workload.
- Suite 86: 51 assertions passed, including the shared preamble; suite 40: 80.
- Ten named mutants rejected at their designated rows: nine finding-148 setup,
  report, placement, deadline and heartbeat mutants, plus the finding-40 wrapper
  escape mutant whose source anchor changed. Both honest mutation controls passed.
  Each driver command uses `--finding`, `--worker NAME`, and `--jobs 2`; mutant
  invocations ran through a two-worker pool. The exact commands and row outcomes
  are in the evidence record. No full mutation run or repository gate was run.
