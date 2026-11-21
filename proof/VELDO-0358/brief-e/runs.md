# Brief E: runs

Every loaded run went through the builders' host-heavy wrapper (outside the repository). The generator is
scripts/gate_load.py with 4 slots (12 spinners, 1 writer, no delegated scope so no memory.high); each batch
ran each suite fifty times, four at a time, each run in its own dispatcher process.

## Idle

Each suite alone after its conversion: 62 56 passed, 63 90 passed, 78 65 passed, 106 48 passed, 0 failed
(base fb7705e1: 52, 86, 64, 47 including the dispatcher's own rows).

## Fifty runs per suite under the generator

| Batch | Tree | Suites | Probe slowdown (data) | Result |
| - | - | - | - | - |
| load50 (load50-summary.txt) | 6ae16638, with 73710940 reaching 106 from its run 8 on | 62, 63, 78, 106 | 5.2 | 63 50/50, 78 50/50 green. 106 run 7 red (red-106-run7.txt): the journey's impossible condition fired with a worker slot still held; fixed in 73710940 (a held slot is a message still to come). 62 run 45 red (red-62-run45.txt): the jobs' 120 s contract deadline passed in a long run; fixed in c42aa7e4 (an hour away) |
| load50b (load50b-summary.txt) | c42aa7e4 | 62, 106 | 7.5 | 106 50/50 green. 62 46 of 50 red on dispatch/remote-stop-holds-unit (red-62-remote.txt): the remote row's real 2 s contract deadline raced the wrapped launch (it was green 50/50 at 5.2); fixed in 06a092e7 (the supplied clock, as the closed-output row) |
| load50c (load50c-summary.txt) | 06a092e7 | 62 | 7.9 | 49 of 50 green. One red, dispatch/owner-stop (red-62-owner-stop.txt): open, below |

Every generator process was alive to the end of every batch (load_not_applied never).

### Open: suite 62, dispatch/owner-stop, 1 run in 50 at slowdown 7.9

The row's own sweep (runner.honor_stops) returned nothing to ask, yet the Launch shows the stop written to its
receiver (stop_requested true), the receiver ended the worker for 'requested' (SIGTERM), and the stop
request's result was recorded by the runner as not asked, 0.27 s after the request. Read with the product:
honor_stops records "not asked" only for a dispatch whose record has left running and of which it holds no
Launch, and a runner also sweeps inside each preparation and wait (Runner.sweep). The order in which a sweep
saw the record leave running and recorded not asked, while another call asked the receiver, is not
established from this run's evidence. It is reported, not worked around (specification Notes: a race a busy
machine shows is fixed in the test or the product). The fix and its cause are the next item for this row.

## Registered cases through the gate's driver

See mutants.md (the 135 cases of suites 62, 63, 78 and 106 with brief E's three falsifiers).

## Affected suites (affected-suites.txt, affected-reruns.txt)

The 77 suites that load the six engine modules, the timers table, the mutation registry or the census lists,
each alone, at 6ae16638. Reds and their disposition:

| Suite | Red | Disposition |
| - | - | - |
| 66_veldo_0047_authority (installed-assets), 82_veldo_0129_worker_wiring (29 rows) | init_scaffold did not lay down .veldo/timers.py | Fixed in a48602c9; both green after |
| 126_veldo_0230_qualify_reproduces (qualify/reproduces), 86_veldo_0127_agent_configuration (live/claude, live/codex) | proof/VELDO-0127's qualify resource fixtures and live captures are bound to the digests of control_launch and the engine modules; both green at the base | Release acts outside this brief: rerun qualify on the recorded engines and the owner-approved live recapture (precedents fe9eb598, f5055400). lead-items.md |
| 66_veldo_0042_clones, 86_veldo_0189_engine_upgrade (residue) | serve threads | Wave 1 briefs G and F, as at the base |
| 151_veldo_0313_space_run | nine rows | Inherited (red at the base, integration.md); brief G |

## Round 2 (2026-11-21)

Where: every run below is local, through the builders' host-heavy wrapper. pc2 was tried first at 190c4e90
(remote_run): its Python has no os.pidfd_open and its runs have no systemd user manager, so suite 62 raised
AttributeError on pidfd_open and suites 106 and 85 were refused `unavailable_service:profile:user_manager`
there; the suites of this brief need this host. The generator itself needs no delegation (memory.high none).

| Run | Tree | Result |
| - | - | - |
| Idle (r2-idle-and-falsifier.txt) | 190c4e90 | 62 58, 78 65, 106 48, 85_veldo_0171 45, 63 90, 91_veldo_0167 36, 95_veldo_0203 63, 87_veldo_0170 39 passed, 0 failed |
| Falsifier of dispatch/owner-stop-ends-first (same file) | 190c4e90 with honor_stops recording through dispatches.stop_result directly | 57 passed, 1 failed: only the new row, with the loaded red's signature (swept [], asked False, cause requested) |
| r2-load50 (r2-load50-summary.txt) | 190c4e90, slowdown 4.7 | 78 50/50, 106 50/50; 62 49/50: run 45 red (r2-red-62-enodev.txt), below |
| r2-load50b (r2-load50b-summary.txt) | d1b18d13, slowdown 4.9 | 62 50/50, 78 50/50, 106 50/50; 12 of 12 spinners and the writer alive to the end |
| Suite 83 with brief F (r2-suite83-with-f.txt) | temporary combination of 190c4e90 and d5450c70, uncommitted | 10 of 10 green, idle, four at a time (brief F saw 8 of 8 hang there) |
| Suite 83 with brief F, loaded (r2-load50-suite83-with-f.txt) | same combination, slowdown 4.8 | 49 of 50 green, no hang; one red, loop/reset-timer-wake (brief F's row, below) |
| Affected suites (r2-affected-suites.txt) | 190c4e90 moving to d1b18d13 | the 42 suites that open the converted files: 39 green; 86_veldo_0127 live/claude, live/codex (lead item 8, digests); 86_veldo_0189 residue (brief F); 86_veldo_0168 three rows, fixed in 481bd6fc and green after |

### Closed: suite 62, dispatch/owner-stop (round 1's open red)

A product race, fixed in 69961820. Runner.honor_stops asks the receiver (Launch.stop) and then records the ask
with control_dispatch.stop_result, whose command pins the dispatch record at the version it reads. The receiver
it just asked ends the worker and writes the same record (the exit). When that commit lands between the version
read and the result's commit, the store refuses the result stale_version; honor_stops records the refusal as an
observation and returns nothing; the runner's next sweep (inside runner.wait, after the Launch is popped) finds
the request still waiting on an ended dispatch it holds no Launch of, and records it not asked. That is round 1's
red exactly: swept [], stop_requested true, cause requested, result asked False 0.27 s later, by runner. The
store's expected version is the only guard the order could break; stop_transition judges nothing else of the
record. The fix (Runner._stop_result): a stale refusal with the record's version moved since it was read commits
the same result at the version now there; any other refusal, or a stale one with the version unmoved, is raised
as before. No bound changed, no row retried.

The new row dispatch/owner-stop-ends-first makes that order on every run: the runner's result reads the version,
waits (on the store and the receiver's pidfd) until the receiver has recorded the end, then commits with the read
version. Red on the old code (falsifier above), green on the fix, and 50 of 50 under load with dispatch/owner-stop.

### Closed: suite 62 run 45 of r2-load50, transitions-from-schema raised OSError(19)

Round 1's own code: _await_gone opened the orphan's cgroup.events and read it once before polling, unguarded.
The row kills the receiver and calls runner.orphaned, which writes cgroup.kill and then waits: a scope the manager
removes between the open and that first read makes the read fail with ENODEV (a removed cgroup's files answer so),
which escaped release_orphans ('orphan' is [] in that run's timers row: nothing was recorded). Every other read of a
cgroup file on this path is already guarded (containment._read, Group.populated). Fixed in d1b18d13: a group gone
at that read is the cleaned reading, and the source is dropped as the loop already drops it. 50 of 50 after.

### Brief F's lead item 6b (suite 83 hung at loop/receiver-death with brief E)

Fixed in 69961820: _await_gone took the worker's pidfd readiness as an event but still judged the worker by
containment.alive, which reads /proc and sees the unreaped zombie (its parent, the receiver, was killed, so it is
reaped later by its new parent), and then polled an empty set until ORPHAN_SECONDS (the hang bound under the suite's
profile). The pidfd's readiness is now the process's exit (the pidfd is opened before the identity check, so it
names the recorded process and not a reused pid), and a wait with no source left ends at once.

The single loaded red with F, loop/reset-timer-wake (run 17): at the reset pass the waiting unit VELDO-9154-L4 was
refused missing_authority:claim, so the pass offered nothing. The receiver-death row passed in that
run; the refusal's cause was not traced here. It is the same row as brief F's own unexplained loaded
red (brief F lead item 6: a real one-minute reset, its LEAD raised to 30 s). Not changed here: suite 83 is brief F's.
