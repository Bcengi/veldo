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
