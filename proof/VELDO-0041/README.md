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

Suite `scripts/suites/67_veldo_0041_heartbeat.py`: 19 rows, 10 assertion rows and 9 rows saying each
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

One recorded run: `observations.json` (19 passed, 0 failed, 9.7 s), written by `drive.py`. Its
monotonic timings: during a 2.016 s blocked model call, 8 heartbeats taken, sent every 0.249 to 0.250 s
and taken at most 0.251 s apart, each one renewing the claim (9 renewals, claim version 1 to 10, 9
signed journal records by the receiver); with the heartbeat stopped, the lapse came 1.001 s after the
last one taken and the cooperative stop at the lapse itself; the requested stop's steps at 0, +1.001 and
+1.502 s (1.0 s and 0.5 s configured), the cooperative child terminated and gone at +1.002 s, the
signal-ignoring descendant beating until +1.491 s and gone at +1.503 s, the group empty at +1.504 s; with
the shipped profile, one heartbeat 0.016 s after release and no second in the 1.5 s run.

## Red record

`red-e231721.json`, written by `red.py`: the CURRENT suite over the pre-change code. Substituted:
`control_launch.py`, `control_containment.py`, `control_reservations.py` and `init_scaffold.py` at
e231721, and `prefix/control_heartbeat.py` and `prefix/control_retirement.py`, empty stand-ins for the
modules that do not exist there. The other installed modules are the current tree's; the ones that
differ from e231721 are named in the record, and all came from main (control_client.py, env_provision.py,
and the new control_clone.py and control_service.py). All 10 assertion rows fail by assertion, nothing
raised, and all 9 region rows pass. What each shows at e231721: no heartbeat exists (a profile declaring
one is refused as an unknown setting); the escalation already stopped the group on time (VELDO-0040 built
it), so `stop/bounded-group-exit` is red only because the steps were timed and recorded on the wall clock
and the graces were not reported; the runner's second retirement attempt released the slot while the
signal-ignoring descendant was alive, because the first attempt forgot the group; a model call whose
final report left tokens and messages unknown was retired with those units recorded nowhere and no
pending list existed; the slot was released with the clone's files and pins left on disk, and for a
dispatch whose outcome is unknown.

## Mutations

25 registered as finding 41 in `scripts/check_teeth_mutations.py`, each diff in `mutations/`, the run
in `mutations.json` (`python3 -B proof/VELDO-0041/mutations.py`): every target row red by assertion with
its region completing, baseline green. The declared falsifiers: `heartbeat-after-model-return` (AC1),
`stop-terminate-only-parent` (AC2), `retire-before-descendant-termination` (AC3). Every assertion row has
at least one further, different mutation. Two finding 39 and two finding 40 registrations were re-pointed
at the reap loop's least-timer wait and at the worker's exit, which now gives the wrapper's heartbeat a
moment to end before what is left is stopped.

## Costs

The suite adds about 10 s to the gate; finding 41 takes about 91 s with 4 jobs. Each running worker adds
one heartbeat process and, every heartbeat, one signed store write (the claim renewal). The suites of
VELDO-0040, VELDO-0049 and VELDO-0050 run as before (7.1 s, 10.9 s, 6.5 s).

## The gate's mutation stage

Both were run under `env -i` with PATH a new directory holding a python3 symlink, then /usr/bin:/bin,
HOME and TMPDIR a new temporary directory, no XDG_RUNTIME_DIR, LANG and LC_ALL C.UTF-8, TZ UTC,
PYTHONDONTWRITEBYTECODE, PYTHONNOUSERSITE, PYTHONHASHSEED=0, GIT_CONFIG_NOSYSTEM, GIT_CONFIG_GLOBAL
/dev/null and GIT_TERMINAL_PROMPT=0: the suite passed (19 rows, 9.8 s) and finding 41 rejected all 25
with its baseline green and no region raised. The suite gives its own run the owner's session
(XDG_RUNTIME_DIR /run/user/<uid>) as suite 66 of VELDO-0047 does, so its systemctl, the receiver and the
receiver's systemd tools reach the user manager there; it keeps its tree in that runtime directory,
because the clone layout refuses a protected target beneath a temporary directory.

## Integration with main

Merged origin/main b893aa2 (d133a1b), which brought VELDO-0042's control_clone.py that the clone row
retires through. Conflicts: both copies of init_scaffold.py (both sides add entries; both kept) and the
suite manifest (both entries kept; requires.json regenerated). After it: suites 67 (19), 63 of VELDO-0040
(20), 62 of VELDO-0039 (21), 58 of VELDO-0036 (10), 63 of VELDO-0049 (20), 66 of VELDO-0042 (20), 60 of
VELDO-0053 (39), 50 (4), 64 of VELDO-0050 (14) and 66 of VELDO-0047 (30) pass; findings 41 (25), 40 (22)
and 39 (30) are all rejected; no slice or scope of these runs is left loaded.

## Not done here

An unknown outcome keeps its slot: establishing it is recovery, Release 2. What the retirement tracks
lives in the runner's memory, so retirement across a runner crash is Release 2, as are leadership
fencing and a stopped orchestrator. A lost claim is recorded on the heartbeat that found it and does not
stop the worker (fencing, Release 2). The Mac's heartbeat is its own profile's (VELDO-0124). Wiring the
production adapters to the clone entrance and composing create and attach with the runner is VELDO-0129;
the suite composes them itself.
