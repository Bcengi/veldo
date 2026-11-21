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
