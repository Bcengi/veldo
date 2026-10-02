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

## Runtime-cap investigation, 2026-10-02

The reported gate red is not yet explained. The late-origin diagnosis was wrong:
the receiver records running after activation, so subtracting running_at makes
the old gap smaller. It cannot explain an old-row upper-bound failure.

The row now reports every false conjunct after its name, in the format consumed
by the mutation worker's failed_details. It includes the compared clocks and
gaps, complete supervision record, descendant identity and liveness, term count,
LoadState and unchanged 1.2 + 0.5 + 1.0 second bound. All predicates are evaluated
and the exact LoadState observation used by the assertion is recorded.

The original suite and all production modules at f1e1abb9 were extracted with
git archive into a temporary tree. Only the row's diagnostics were added; its
wall-clock beats, running_at origin and predicates were retained. Ten rounds
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

The canonical gate and mutation drivers are reserved for the reviewer and were
not run. This is selected-suite evidence, not a gate stamp or a reproduced fix.
