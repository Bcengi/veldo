# VELDO-0041 proof: heartbeat, bounded stopping and retirement

The trusted wrapper (`.veldo/control_launch.py exec --contained --heartbeat`) starts a heartbeat
process of its own just before it becomes the engine. It is forked twice and takes a session and
process group of its own between the two forks, before the engine exists, so a signal the engine sends
its own process group never reaches it. It lives in a child group of the dispatch's VELDO-0040 scope
and writes one line to the receiver every `heartbeat_seconds` on a pipe the receiver passed, whatever
the engine is doing (`.veldo/control_heartbeat.py`); the wrapper closes its own end before the exec, so
the engine holds no end of that pipe. The receiver takes each line on its own monotonic clock, renews
the build claim through VELDO-0031's `renew` transition as the dispatch authority, and stops a worker
whose heartbeats stop for `heartbeat_window_seconds` (cause `heartbeat_missing`) through VELDO-0040's
escalation, which is timed and recorded on the monotonic clock with its graces reported. The runner
returns a worker slot through `.veldo/control_retirement.py`, which observes termination, the group,
the outcome, the clone files (removed through VELDO-0042's teardown) and the accounting inside
VELDO-0036's own retire transaction, and releases the slot once. Shipped defaults: 10 s heartbeat,
30 s window, 10 s before termination, 5 s more before killing. Engine copies are identical; both
modules are installed by `.veldo/init_scaffold.py`.

## How a refused retirement is retried

A refused retirement stays pending in the runner's retirement service with each open obligation, its
group and the outcome the runner gave. It is retried when an obligation it waits on is completed, and
never needs a caller to ask again:

**At once, when the service observes the completion itself.** Its own teardown of a clone removes
files another pending retirement waits on: those retirements are retried in the same pass (basis
`clone_removed`, and the record names the retirement whose teardown removed the clone). The service
also listens on the reservation service's one observation seam (`observe`, called after every
operation it accepts or refuses): one dispatcher is installed on each service, once, after the
observer it already had, and fans each event out to the retirement services listening, held weakly,
so the chain never grows with the runners made over one service. An accepted usage report of a call
under a dispatch that waits on its accounting retries that retirement (basis `accounting_reported`),
so a final report releases the slot inside the report call.

**On every sweep.** `Runner.sweep()` runs before each preparation (and so each submit) and after each
wait, and a scheduler may call it at any time, so a completion the service did not observe (a report
made through another connection, a group the kernel emptied) strands nothing.

**Only when something changed.** A retry first re-reads the obligations and is attempted only when the
open obligations differ from its last attempt's, when its clone can now be removed (every user of the
clone has ended, by the provisioner's own `observe`), or when its last refusal named no obligation (an
unavailable service, a stale version). An unknown outcome, which nothing in Release 1 completes, is
therefore not attempted again and again. Every retry is the same single release: the same gate, the
same command identity `retire/<dispatch id>` and the `already_retired` refusal. `status()` counts
accepted, refused and retried attempts; every event carries its basis.

## Rows

Suite `scripts/suites/67_veldo_0041_heartbeat.py`: 23 rows, 12 assertion rows and 11 rows saying each
region ran to its end. Real systemd user manager, cgroup v2, pidfds, real receiver, wrapper, heartbeat,
worker, model and descendant processes, the real store, clone, teardown and VELDO-0036 InvocationGuard.
Every release reaches the slot through the runner's production paths (submit, wait, its sweep, its
teardown and its listener on the reservation service); no row calls the runner's private `_retire`.
The timed rows run with configured values (0.25 s heartbeat and 1.0 s window; 1.0 s and 0.5 s graces)
and assert those were used; `heartbeat/shipped-defaults` asserts the shipped values exactly, as the
profile's defaults and as a real receiver reports them. Declared measurement tolerance: 0.35 s.

| Criterion | Rows |
|-|-|
| AC1 heartbeat independent of a blocked call, renewal, missed-heartbeat stop | heartbeat/blocked-call-liveness, heartbeat/missing-heartbeat-stop, heartbeat/channel-not-held, heartbeat/engine-group-signal, heartbeat/shipped-defaults |
| AC2 bounded escalation over the whole group | stop/bounded-group-exit |
| AC3 retirement after actual termination, obligations kept and retried, one release | retirement/live-descendant, retirement/missing-accounting, retirement/clone-files, retirement/unknown-outcome |
| Observability and installation | retirement/observations, retirement/installed-assets |

What the changed and new rows drive:

**heartbeat/channel-not-held (new).** While a contained worker runs, the suite reads from /proc the
open descriptors of its heartbeat, its receiver and its engine: the heartbeat holds exactly one pipe,
the receiver holds that same pipe, the engine holds pipes of its own and not that one.

**heartbeat/engine-group-signal (new).** The engine sends SIGTERM to its own process group (it leads
that group and ignores the signal itself) and runs two seconds more: heartbeats keep coming from the
same heartbeat process, the worker is never stopped as `heartbeat_missing`, and it exits 0.

**retirement/live-descendant (changed).** A launch whose refusal reports its group while a process it
left is still in the dispatch's own scope is handed to `Runner.submit` (the receiver seam: a receiver
that could not start, settled by VELDO-0039's `invoke`, with the group a VELDO-0040 refusal reports).
The submit's retirement is refused `cleanup_incomplete` with the group populated; the next submit's
sweep attempts nothing while the process lives; the process ends, and the next wait's sweep releases
the slot once, observed after that process's death. The real dispatch beside it (a signal-ignoring
descendant outliving its worker) is released by its own wait after the descendant's death, and a
second wait is refused `already_retired` with one release commit.

**retirement/missing-accounting (changed).** The adapter's InvocationGuard reserves a model call; the
wait's retirement is refused `missing_accounting`; the guard's final report is what releases the slot,
inside the report call (basis `accounting_reported`), with the units it left unknown retained; a
second wait is refused `already_retired`, still one commit.

**retirement/clone-files (changed).** Two submits through a receiver seam composed with the clone
provisioner (the first creates the clone, the second attaches to it, as VELDO-0129 will wire it). The
owner ends first and its retirement is refused `cleanup_incomplete:clone` (`clone_in_use`, files on
disk). When the consumer's wait retires the consumer, its teardown removes the clone and, in the same
pass, the owner's retirement is retried and released (basis `clone_removed`, removed by the consumer);
no pin is left, one commit each, and a second wait on the owner is refused `already_retired`.

**retirement/unknown-outcome (changed).** The receiver ends without recording how the dispatch ended;
the wait's retirement is refused `worker_alive`. After the group is killed, the next preparation's
sweep retries it once (`outcome_unknown`, open `outcome`), and the preparation after that attempts
nothing: the slot stays held, nothing committed.

One recorded run: `observations.json` (23 passed, 0 failed, 11.3 s), written by `drive.py`. Its
monotonic timings: during a 2.016 s blocked model call, 8 heartbeats taken, sent every 0.249 to
0.250 s and taken at most 0.250 s apart, each one renewing the claim (9 renewals, claim version 1 to
10, 9 signed journal records by the receiver); with the heartbeat stopped, the lapse came 1.001 s after
the last one taken and the cooperative stop at the lapse itself; the requested stop's steps at 0,
+1.001 and +1.502 s (1.0 s and 0.5 s configured), the cooperative child gone at +1.002 s, the
signal-ignoring descendant beating until +1.488 s and gone at +1.503 s, the group empty at +1.503 s;
with the shipped profile, one heartbeat 0.010 s after release and no second; after the engine signaled
its own group, 8 more heartbeats at most 0.250 s apart from the same process, and exit 0.

## Red records

Written by `red.py`: the CURRENT suite over an earlier commit's launch path (its control_launch.py,
control_containment.py, control_reservations.py, init_scaffold.py, control_heartbeat.py and
control_retirement.py, or the empty stand-in in `prefix/` for a module the commit does not have). Every
other installed module is the current tree's, and each one that differs from the commit is named in
the record. In both records every failing row fails by assertion, nothing raised, and every region row
passes.

**`red-5f53aa3.json`, the reviewed tip before these fixes.** 6 of 12 assertion rows fail.
`heartbeat/engine-group-signal`: the heartbeat died with the engine's group signal, no heartbeat came
after it, and the worker was stopped as `heartbeat_missing` and killed. The four retirement rows: no
release came when its obligation completed. The planted group's slot was never released by any sweep;
the final report released nothing; the consumer's teardown removed the clone and the owner stayed held;
the unknown outcome was never tried again after its group ended. For the accounting and clone rows the
slot was released only when the row waited on that dispatch a second time, which is no production path.
`retirement/observations`: no retried attempt was counted, and no retirement was ever refused
`outcome_unknown`, since none was tried again. `heartbeat/channel-not-held` passes there,
as it should: 5f53aa3 already closes the channel, and the row guards it (its mutation is below).

**`red-e231721.json`, before VELDO-0041.** All 12 assertion rows fail: no heartbeat exists (a profile
declaring one is refused as an unknown setting), the escalation's steps are timed and recorded on the
wall clock only, the runner's retirement forgets the group after its first attempt, keeps no pending
list and holds no outcome, clone or accounting obligation. The substituted and differing modules are
named in the record (the new ones all came from main).

## Mutations

34 registered as finding 41 in `scripts/check_teeth_mutations.py`, each diff in `mutations/`, the run
in `mutations.json` (`python3 -B proof/VELDO-0041/mutations.py`): every target row red by assertion with
its region completing, baseline green. The declared falsifiers: `heartbeat-after-model-return` (AC1),
`stop-terminate-only-parent` (AC2), `retire-before-descendant-termination` (AC3). Every assertion row
has at least one further, different mutation. Added for the review of 5f53aa3:

| Mutation | Defect | Row |
|-|-|-|
| retire-report-not-subscribed | the final accounting report is never listened for | retirement/missing-accounting |
| retire-retry-releases-twice | each attempt is a request of its own and a released slot is not looked at (two edits) | retirement/missing-accounting |
| retire-clone-removal-not-retried | the retirements waiting on a removed clone are not retried | retirement/clone-files |
| retire-pending-never-retried | a pending retirement is never tried again | retirement/clone-files |
| retire-no-sweep-on-wait | a wait sweeps no pending retirement | retirement/live-descendant |
| retire-no-sweep-on-prepare | a preparation sweeps no pending retirement | retirement/unknown-outcome |
| retire-sweep-retries-unchanged | a retirement is tried again whether or not anything it waits on changed | retirement/unknown-outcome |
| heartbeat-shares-engine-session | the heartbeat stays in the engine's session and process group | heartbeat/engine-group-signal |
| heartbeat-channel-left-to-engine | the wrapper does not close the channel before the exec | heartbeat/channel-not-held |

The earlier registrations against the four changed retirement rows still red them through the new
production paths (the declared falsifier now through the planted group's first attempt).

## Costs

The suite takes about 11.3 s (1.1 s more than at 5f53aa3, for the two new heartbeat rows); finding 41
takes about 143 s with 4 jobs. Each running worker adds one heartbeat process and, every heartbeat, one
signed store write (the claim renewal). A sweep costs one slot read per pending retirement and, for
each, one read of its obligations (kernel files, the dispatch record, the reservation records, and for
a clone the provisioner's observation); a retirement is attempted, one store transaction, only when
something it waits on changed. Each accepted reservation operation adds one entity read in the
listener.

## The gate's mutation stage

Both were run on the final tree under `env -i` with PATH a new short directory under /dev/shm holding a
python3 symlink, then /usr/bin:/bin, HOME and TMPDIR that directory, no XDG_RUNTIME_DIR, LANG and LC_ALL
C.UTF-8, TZ UTC, PYTHONDONTWRITEBYTECODE, PYTHONNOUSERSITE, PYTHONHASHSEED=0, GIT_CONFIG_NOSYSTEM,
GIT_CONFIG_GLOBAL /dev/null and GIT_TERMINAL_PROMPT=0: the suite passed (23 rows) and finding 41
rejected all 34 with its baseline green and no region raised. The suite gives its own run the owner's
session (XDG_RUNTIME_DIR /run/user/<uid>) as suite 66 of VELDO-0047 does, so its systemctl, the
receiver and the receiver's systemd tools reach the user manager there; it keeps its tree in that
runtime directory, because the clone layout refuses a protected target beneath a temporary directory.

## Integration with main

Merged origin/main 5ba4a02 (9102e27), which brought VELDO-0051's event vocabulary and projection.
Conflicts: the suite manifest and requires.json (both entries kept; requires.json regenerated with
`python3 scripts/run_scope.py --emit-requires`, identical to the hand merge). After it: suites 67 (23),
63 of VELDO-0040, 62 of VELDO-0039, 58 of VELDO-0036, 63 of VELDO-0049, 66 of VELDO-0042 and 50 pass;
findings 41 (34), 40 and 39 are all rejected; no slice or scope of these runs is left loaded.

## Not done here

An unknown outcome keeps its slot: establishing it is recovery, Release 2. What the retirement tracks
lives in the runner's memory, so retirement across a runner crash is Release 2, as are leadership
fencing and a stopped orchestrator. A final report made through another connection is not heard by the
listener; the next sweep retries it. A lost claim is recorded on the heartbeat that found it and does
not stop the worker (fencing, Release 2). Filed from the review of 5f53aa3 and left for later: heartbeat
lines forged by a hostile engine that reaches the channel through /proc, the retirement's use of the
private `Clones._is_live`, and a refused renewal not stopping the worker. The Mac's heartbeat is its own
profile's (VELDO-0124). Wiring the production adapters to the clone entrance and composing create and
attach with the runner is VELDO-0129; the suite composes them in its receiver seam.
