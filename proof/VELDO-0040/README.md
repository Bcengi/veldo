# VELDO-0040 proof: Linux worker groups, caps, stop and exit

Every local worker the launch receiver starts runs in its own systemd scope inside the profile's
slice, through the user service manager (no root). The profile's caps (runtime, memory, CPU, file
size, concurrency) are installed on the scope before the worker runs, an unqualified or
incomplete profile is refused before any spawn, a stop is cooperative first and then escalates over
the whole group, the exit is detected from kernel notifications rather than by polling, and the
dispatch retires only after its group is observed empty. The module is `.veldo/control_containment.py`
(engine copy identical), installed by `.veldo/init_scaffold.py`; the receiver in
`.veldo/control_launch.py` (VELDO-0039) is still the one spawn point.

## Rows

Suite `scripts/suites/63_veldo_0040_containment.py`: 20 rows, 12 assertion rows and 8 rows saying
each region ran to its end. Real systemd user manager, cgroup v2, real worker processes with
ordinary descendants.

| Criterion | Rows |
|-|-|
| AC1 dedicated group, refusal before spawn | containment/dedicated-group, containment/ordinary-exit, containment/unqualified-profile-refused, containment/required-settings-refused, containment/exit-notified |
| AC2 caps installed and holding | containment/caps-installed, containment/runtime-cap |
| AC3 stop, exit and retirement | containment/cooperative-stop, containment/stop-escalation, containment/retire-after-empty |
| Observability and installation | containment/observations, containment/installed-assets |

One recorded run: `observations.json` (20 passed, 0 failed, 6.8 s), written by `drive.py`.

## Red record

`red-f5aebae.json`, written by `red.py`: the CURRENT suite over the pre-change code. Substituted:
`control_launch.py` and `init_scaffold.py` at f5aebae, and `prefix/control_containment.py`, a stand-in
that supplies only the names the suite calls and contains nothing. Every other installed module is
identical to f5aebae. All 12 assertion rows fail by assertion, nothing raised, and all 8 region rows pass.

## Mutations

22 registered as finding 40 in `scripts/check_teeth_mutations.py`, each diff in `mutations/`, the run
in `mutations.json` (`python3 -B scripts/check_teeth_mutations.py --finding 40 --jobs 4 --diff-dir
proof/VELDO-0040/mutations`): every target row red by assertion with its region completing, baseline
green. The declared falsifiers: `containment-launch-outside-group` (AC1, dedicated-group),
`containment-runtime-cap-ignored` (AC2, runtime-cap), `containment-stop-only-parent` (AC3,
stop-escalation). Every assertion row has at least one further, different mutation. Three VELDO-0039
closed-output mutations were re-pointed at the notification loop that replaced the polling they named.

## Costs

The suite adds about 7 s to the gate. Finding 40's mutations take about 57 s with 4 jobs. The suites of
VELDO-0049 (63) and VELDO-0050 (64) now also start their workers contained, which adds about 5 s and
4 s to them.

## Integration with main

Merged origin/main 5a5dfcd (8dbe2f4). VELDO-0049's and VELDO-0050's suites landed after this branch was
cut and gave the receiver no worker profile, which this change requires before any spawn, so every
build they launched was refused. f6d217e gives both suites this host's profile and stops their own
slice at the end. After it: suites 63 (0040), 62 (0039), 58 (0036), 60 (0053), 63 (0049), 64 (0050)
and 50 pass, 154 rows; findings 39 (30), 40 (22), 49 (36) and 50 (24) all rejected; no slice left behind.

## Not done here

The Mac profile is VELDO-0124. Aggregate resource-exhaustion qualification and recovery after
authority loss are Release 2. Production receiver configuration names its profile at installation.

## Initial runtime-cap investigation, 2026-10-02 (historical)

At this stage the reported gate red was not yet explained. The late-origin diagnosis was wrong:
the receiver records running after activation, so subtracting running_at makes
the old gap smaller. It cannot explain an old-row upper-bound failure.

The row now reports every false conjunct after its name, in the format consumed
by the mutation worker's failed_details. It includes the compared clocks and
gaps, complete supervision record, descendant identity and liveness, term count,
LoadState and unchanged 1.2 + 0.5 + 1.0 second bound. All predicates are evaluated
and the exact LoadState observation used by the assertion is recorded.

The original suite and all production modules at f1e1abb9 were extracted with
git archive into a temporary tree. Only the row's diagnostics were added; its
wall-clock beats, running_at origin and predicates were retained. The saved
original-row-diagnostics.diff recreates the exact measured suite hash. Ten rounds
ran two suite copies simultaneously with one pinned busy loop on each of the
20 available CPUs. All 20 suite runs passed 46 rows. No conjunct failed.
The closest original gap was 1.6435189247131348 seconds, leaving
1.0564810752868652 seconds below the 2.7 second bound. Every run reported exited,
deadline_stop true, cause runtime_cap, result timeout, a present but nonliving
stubborn descendant, beats, at least one term, supervision empty true and
LoadState not-found. This does not establish the cause of the historical red.

No production failure was measured, so this investigation adds no speculative
production fix. The existing monotonic activation origin is retained because
it matches RuntimeMaxSec's scope lifetime. It is a stricter measurement, not a
proven flake fix. The manager timestamps are retained by the existing result
read before clearing the scope; both engine copies match. No assertion bound,
settle window or tool timeout was increased.

runtime_cap_check.py is a foreground driver that runs only suite 63. Its
original-load mode extracts the original tree and adds diagnostics; load mode
uses the checkout. A loaded round has two concurrent suite processes, plus the
CPU load processes. It records exact child PIDs and terminates and reaps only
its own load children. Per-process CPU ticks confirm each burner ran. Logs and
full suite observations stay under /tmp; runtime-cap-runs.json retains the
compared values, failed_details, source hashes and cleanup results.

Normal and gate modes run one selected suite; gate uses the gate's bash -c
invocation and inherited environment. A temporary Python startup observer adds
observation capture, without replacing assertions or production behavior.
Mutation mode changes a temporary module copy with both registered edits of
containment-runtime-cap-ignored. Partial selftest exit code 2 is expected even
when all rows pass; PASS, FAIL, raised regions and row details are recorded.

The current suite passed normally, in the inherited gate shell environment,
and in ten loaded rounds with the same two suite copies and 20 pinned burners.
All 22 current-code runs passed 46 rows without raised regions. The largest
activation-based gap in the loaded series was 1.9125582007691264 seconds,
leaving 0.7874417992308738 seconds below the unchanged bound. Both loaded series
reaped all 20 burners, and every burner's CPU tick count was positive.

The runtime-cap-disabled mutation was applied only to a temporary production
copy. It produced 44 passed and 2 failed, with no raised region. Both
caps-installed and runtime-cap failed by assertion. The runtime row named all
six false conjuncts: deadline_stop, cause_runtime_cap, result_timeout,
timestamps_ordered, last_beat_before_inactive and runtime_bound. The dispatch
exited with deadline_stop false, cause exit and result success. The manager
timestamps were zero after the successful scope was collected; the old-style
wall gap was 9.955755949020386 seconds. There was one term marker, the group was
empty and LoadState was not-found. The emitted JSON failed_details was checked
against the captured runtime observation, including every false predicate.
No new mutation was introduced.

All 22 saved mutation diffs apply to the current sources. Their refreshed source
positions and context preserve the registered defect targets. Only the runtime
mutation was rerun here; the other mutation results above are historical.

The canonical gate and mutation drivers are reserved for the reviewer and were
not run. The gate byproducts are excluded. This is selected-suite evidence, not
a gate stamp or a reproduced fix. The reported historical red remains unresolved;
a future red should now carry the missing per-conjunct evidence.

## Recorded cause after scope collection, 2026-10-02

The measured sequence at the reviewer's 074dbdcd supersedes the earlier
conclude-too-early explanation. RuntimeMaxSec sent SIGTERM; the adapter exited
143; Stop.adapter_exited started terminate then cgroup.kill; the group emptied;
and conclude read a collected scope. The not-found unit supplied inactive,
success and zero clocks. The six false conjuncts were deadline_stop,
cause_runtime_cap, result_timeout, timestamps_ordered,
last_beat_before_inactive and runtime_bound. The reported last beat was 2.74
seconds after running, term_count was 2, and the stubborn process was dead.
The earlier settlement change cannot recover collected evidence, and cleanup
can also change the manager result. More waiting is not a solution.

Group.attach records scope_start from the loaded scope before engine release:
ActiveEnterTimestampMonotonic, installed RuntimeMaxUSec and TimeoutStopUSec.
Receiver._reap retains the adapter-exit monotonic time and its own escalation
steps. A signal exit (negative signal or shell-style 128 plus signal), terminate
or kill at or after activation plus the installed runtime cap establishes
runtime_cap and deadline_stop. The explicit causes requested, usage_cap,
deadline, paid_api, configuration_stop and heartbeat_missing win over inferred
caps. The receiver also retains its contract deadline.

For memory, the minimal additional witness is memory.events oom_kill, sampled
on population observations and immediately before terminate or kill. The maximum
observed count survives removal of the cgroup. A retained OOM kill or loaded
manager oom-kill establishes memory_cap, ahead of elapsed runtime evidence.
This does not claim to recover a counter that disappeared before any observation.

Group.conclude accepts manager results and terminal clocks only with
LoadState=loaded. Not-found ends the read as unknown. Supervision preserves
manager_result separately from the effective result: inferred runtime_cap
records timeout, even when manager_result is unknown or success. No manager
clock is synthesized. The live row uses saved scope_start activation,
stop_monotonic and empty_monotonic. All existing predicates remain, including
the timeout result, timestamp order, empty group, absent unit and unchanged
1.2 + 0.5 + 1.0 runtime bound.

| Deterministic row | Mutation |
|-|-|
| containment/start-evidence | containment-start-activation-lost |
| containment/recorded-runtime-after-collection | containment-recorded-runtime-ignored |
| containment/not-found-unknown | containment-not-found-is-success |
| containment/normal-exit-before-cap | containment-normal-exit-unknown |
| containment/recorded-cap-explicit-precedence | containment-recorded-cap-overrides-explicit |
| containment/retained-oom-before-cleanup | containment-oom-evidence-lost |

The fake receiver drives real begin(), adapter exit, terminate and kill, with
both 143 and negative SIGTERM statuses. The ordinary-exit row uses both collected and loaded units before the cap. The precedence row
drives all six explicit paths with both runtime and memory evidence. Existing
manager precedence, bounded settlement and unreadable-result rows remain.

recorded_cause_check.py runs only suite 63, one copy at a time. It reads the
nine selected mutation registrations as AST data without importing or running
the mutation driver, and saves exact diffs and source hashes. Its pre-fix mode
replaces both complete production files with engine sources from 9a48b4ea in
a temporary copy, keeping the current suite. The normal and gate modes run
the selected suite directly and through the gate's bash -c shell with inherited
environment. Detailed observations and results are in recorded-cause-runs.json.

Earlier manager-result-runs.json, manager-result-mutations.json and
review-correction-runs.json are historical evidence for the superseded approach.
Their old loaded passes did not establish a reliable cause witness. No load
mode, full selftest, canonical gate, gate mutation driver or VELDO-0127 live
capture runs in this continuation. Partial-suite all-green status exits 2 by
design; these results are not a gate stamp or independent approval.

Verification for implementation commit 0f289ab8: normal and inherited gate-shell
suite 63 each passed 64 assertions with zero failures and no raised regions.
Both live runtime rows passed every conjunct. The recorded activation-based
last-beat gaps were 1.683642 seconds normally and 1.683204 seconds in the gate shell,
against the unchanged 2.7 second bound.

| Temporary-copy check | Passed | Failed | Named row red by assertion |
|-|-:|-:|-|
| containment-normal-exit-unknown | 62 | 2 | yes |
| containment-not-found-is-success | 61 | 3 | yes |
| containment-oom-evidence-lost | 63 | 1 | yes |
| containment-recorded-cap-overrides-explicit | 60 | 4 | yes |
| containment-recorded-runtime-ignored | 63 | 1 | yes |
| containment-resolved-exit-hides-cap | 59 | 5 | yes |
| containment-result-before-settled | 59 | 5 | yes |
| containment-start-activation-lost | 55 | 9 | yes |
| containment-unreadable-result-silent | 60 | 4 | yes |
| pre-fix | 58 | 6 | yes, both required rows |

All nine registered mutations complete every region. The complete pre-fix
rebuild fails recorded-runtime-after-collection and not-found-unknown by
assertion, with both regions completing. It reports cause exit and raw success
for the collected scope. Its separate retained-OOM region raises because the
old Group has no sample_memory method; that exception is not counted as either
required falsification. Source and rebuilt hashes and the exact rebuild diff
are retained with the results.

All 31 current mutation registrations match their source anchors. Saved current
mutation diffs were refreshed and checked for application with zero-context
diff support; only the nine recorded here were executed in this continuation.
Both production files in .veldo are byte-identical to engine/.veldo. The initial
development run had one exit-notified failure while absent units consumed the
settle budget. Returning unknown immediately for not-found resolved that
failure; the recorded final runs use that version.


## Empty collected scope review, 2026-10-02

Implementation d38ab988 closes D1, D2 and the final memory sample race without
changing the installed caps, escalation or existing precedence. Seven new
named rows in suite 63 cover the review findings:

| Row suffix under containment/ | Behavior checked |
|-|-|
| empty-shell-signal-after-cap | Status 143 at activation plus cap plus 0.1 seconds establishes runtime_cap |
| empty-native-signal-after-cap | Status -15 at the same instant establishes runtime_cap |
| empty-shell-signal-before-cap | Status 143 before the cap does not establish runtime_cap |
| empty-native-signal-before-cap | Status -15 before the cap does not establish runtime_cap |
| empty-failure-after-cap | Status 1 after the cap does not establish runtime_cap |
| empty-ordinary-after-cap-unknown | Ordinary statuses 0 and 1 at or after the boundary remain unknown when manager evidence is unavailable |
| oom-after-final-populated-sample | A final memory sample retains an OOM that occurs between memory.events and cgroup.events reads |

The five D1 rows make populated false immediately after the pidfd event and
again when the receive loop checks for emptiness. Every row requires an empty
group, zero receiver steps and no inferred Stop cause. Thus the two positive
rows can obtain the stop clock only from the signaled adapter exit. The first
two rows test behavior added since 9572210b; the next three guard existing
behavior. Negative rows assert absence of runtime_cap, timeout and deadline_stop,
without requiring a new unknown-result representation from the old code.

D2 distinguishes an ordinary exit before the cap from one at or after it.
When manager_result is unknown or absent, and the adapter exit was observed
at or beyond saved activation plus RuntimeMaxSec, the ordinary exit remains
unknown, including status 0. Signal, receiver stop or manager cap evidence
still applies first. The row covers collected and unreadable units and an
absent result, both statuses, the exact boundary and 0.1 seconds afterward.
Controls retain status-0 exit before the boundary and with loaded success.
An unknown ordinary exit does not assert deadline_stop without cap evidence.

The minor fix calls sample_memory after the receive loop and before conclude.
Its row uses the real Group.populated and sample_memory methods with a
controlled read sequence: memory 0, populated 1, memory 0, populated 0,
memory 1, conclude. The last member dies between the final memory and
population reads, and the manager result is collected/unknown. The final
sample makes the result oom-kill and cause memory_cap. This is a deterministic
read-order check; it does not claim recovery after memory.events has vanished.

empty_scope_check.py runs only suite 63, one copy at a time. Its normal and
gate modes use the direct command and the gate's inherited bash shell,
respectively. Both passed 78 assertions, zero failures and no raised regions;
both live runtime rows passed every conjunct. The initial development run also
passed 78 assertions. These are partial-suite results, not a gate stamp or
independent approval. The full gate, load modes, global mutation drivers and
VELDO-0127 live capture were not run in this continuation.

The proof helper reads just the four new registrations as AST data, without
executing the global mutation driver. Each temporary copy has one defect.
Exact source hashes, observations and applied diffs are recorded in
empty-scope-runs.json and mutations/empty-scope-*.diff.

| Mutation | Named row suffix | Passed | Failed |
|-|-|-:|-:|
| containment-adapter-stop-time-dropped | empty-shell-signal-after-cap | 76 | 2 |
| containment-adapter-signal-guard-dropped | empty-failure-after-cap | 76 | 2 |
| containment-ordinary-after-cap-is-exit | empty-ordinary-after-cap-unknown | 77 | 1 |
| containment-final-memory-sample-dropped | oom-after-final-populated-sample | 77 | 1 |

Every named row failed by assertion, with no raised regions. Dropping the
adapter clock append also fails the native-signal row. Dropping the signal
guard also fails D2 by misclassifying ordinary statuses as runtime_cap.

The pre-fix mode replaces both complete production modules with engine sources
from 9572210b in a temporary copy, keeping the new suite. It passed 68 assertions
and failed 10. Both positive D1 rows failed by assertion and all three negative
D1 rows passed. Source hashes and the exact rebuild diff are retained. The old
retained-oom-before-cleanup region raises because that Group lacks sample_memory;
that unrelated exception is not counted as a D1 falsification. The current
engine and repository copies of both production modules are byte-identical.
