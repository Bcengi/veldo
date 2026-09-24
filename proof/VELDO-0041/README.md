# VELDO-0041 proof: heartbeat, bounded stopping and retirement

The trusted wrapper (`.veldo/control_launch.py exec --contained --heartbeat`) starts a heartbeat
process of its own just before it becomes the engine. It lives in a child group of the dispatch's
VELDO-0040 scope and writes one line to the receiver every `heartbeat_seconds` on a pipe the receiver
passed, whatever the engine is doing (`.veldo/control_heartbeat.py`). The receiver takes each line on
its own monotonic clock, renews the build claim through VELDO-0031's `renew` transition as the dispatch
authority, and stops a worker whose heartbeats stop for `heartbeat_window_seconds` (cause
`heartbeat_missing`) through VELDO-0040's escalation, which is now timed and recorded on the monotonic
clock with its graces reported. The runner returns a worker slot through `.veldo/control_retirement.py`,
which observes termination, the group, the outcome, the clone files (removed through VELDO-0042's
teardown) and the accounting inside VELDO-0036's own retire transaction, and releases the slot once.
Shipped defaults: 10 s heartbeat, 30 s window, 10 s before termination, 5 s more before killing.
Engine copies are identical; both modules are installed by `.veldo/init_scaffold.py`.

## Rows

Suite `scripts/suites/67_veldo_0041_heartbeat.py`: FILL rows, 10 assertion rows and 9 rows saying each
region ran to its end. Real systemd user manager, cgroup v2, pidfds, real receiver, wrapper, heartbeat,
worker, model and descendant processes, the real store, clone and teardown. The timed rows run with
configured values (0.25 s heartbeat and 1.0 s window; 1.0 s and 0.5 s graces) and assert those were
used; `heartbeat/shipped-defaults` asserts the shipped values exactly, as the profile's defaults and as a
real receiver reports them. Declared measurement tolerance: 0.35 s.

| Criterion | Rows |
|-|-|
| AC1 heartbeat independent of a blocked call, renewal, missed-heartbeat stop | heartbeat/blocked-call-liveness, heartbeat/missing-heartbeat-stop, heartbeat/shipped-defaults |
| AC2 bounded escalation over the whole group | stop/bounded-group-exit |
| AC3 retirement after actual termination, obligations kept, one release | retirement/live-descendant, retirement/missing-accounting, retirement/clone-files, retirement/unknown-outcome |
| Observability and installation | retirement/observations, retirement/installed-assets |

One recorded run: `observations.json` (FILL), written by `drive.py`. Its monotonic timings: FILL.

## Red record

`red-e231721.json`, written by `red.py`: the CURRENT suite over the pre-change code. Substituted:
`control_launch.py`, `control_containment.py`, `control_reservations.py` and `init_scaffold.py` at
e231721, and `prefix/control_heartbeat.py` and `prefix/control_retirement.py`, empty stand-ins for the
modules that do not exist there. The other installed modules are the current tree's; the ones that
differ from e231721 are named in the record (FILL). All 10 assertion rows fail by assertion, nothing
raised, and all 9 region rows pass. What each shows at e231721: no heartbeat exists (a profile declaring
one is refused as an unknown setting); the escalation already stopped the group on time (VELDO-0040 built
it), so `stop/bounded-group-exit` is red only because the steps were timed and recorded on the wall clock
and the graces were not reported; the runner's second retirement attempt released the slot while the
signal-ignoring descendant was alive, because the first attempt forgot the group; the slot was released
with a model call's accounting retained nowhere, with the clone's files and pins left on disk, and for a
dispatch whose outcome is unknown.

## Mutations

FILL registered as finding 41 in `scripts/check_teeth_mutations.py`, each diff in `mutations/`, the run
in `mutations.json` (`python3 -B proof/VELDO-0041/mutations.py`): every target row red by assertion with
its region completing, baseline green. The declared falsifiers: `heartbeat-after-model-return` (AC1),
`stop-terminate-only-parent` (AC2), `retire-before-descendant-termination` (AC3). Every assertion row has
at least one further, different mutation. Two finding 39 and two finding 40 registrations were re-pointed
at the reap loop's least-timer wait and at the worker's exit, which now gives the wrapper's heartbeat a
moment to end before what is left is stopped.

## Costs

FILL

## The gate's mutation stage

FILL

## Integration with main

FILL

## Not done here

An unknown outcome keeps its slot: establishing it is recovery, Release 2. What the retirement tracks
lives in the runner's memory, so retirement across a runner crash is Release 2, as are leadership
fencing and a stopped orchestrator. A lost claim is recorded on the heartbeat that found it and does not
stop the worker (fencing, Release 2). The Mac's heartbeat is its own profile's (VELDO-0124). Wiring the
production adapters to the clone entrance and composing create and attach with the runner is VELDO-0129;
the suite composes them itself.
