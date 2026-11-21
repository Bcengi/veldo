# VELDO-0358 brief G: space run, isolation and ownership

Scope: revision-notes section 3.3, brief G (the task text said "brief A"; the brief named in its title,
its files and its reading list is G, and G is what was built). Criteria AC10 and AC15 for its suites.
Files: scripts/suites/151_veldo_0313_space_run.py, scripts/suites/66_veldo_0042_clones.py,
scripts/suites/support/v171_tailscale.py, scripts/mutation_ownership.py (and its engine/scripts canon),
engine/bin/veldo (the acknowledgement line only), brief G's block of scripts/check_teeth_mutations.py, and
the entries of scripts/suites/wallclock_baseline.json for those files. bin/veldo is changed with
engine/bin/veldo because suite 151's paths/canon row requires the two to be equal (it is not in the
specification's footprint: an item for the lead).

## What was built

| Site (design 4.2 and A.1) | Before | Now |
| - | - | - |
| mutation_ownership.py:599-603, 286, 361, 517 | 20 ms poll with a 5 s deadline; systemctl timeouts 60, 10, 5 s | wait_for_empty sleeps on the cgroup's own notification (select on cgroup.events, an exceptional condition) with WAIT_HANG_SECONDS as its only bound, raised as a hang; the systemctl calls take the same named constant |
| v171_tailscale.py:123-128 | free_port() bound to 0, read, released | the port holder of support/ports.py (C11) keeps it bound until release_ports(); the server's bind and listen with SO_REUSEADDR succeed, any other bind is refused |
| 66_veldo_0042:553-585 | listener thread left in accept; 25 s engine poll; 2 s socket timeout | the listener is shut down (wakes accept) and joined; the engine wait wakes on its pidfd and on a byte per request line the listener records; no socket timeout |
| 66_veldo_0042 probes, scope, groups | 30 s marker poll, 10 s scope poll, sleeping hold and orphan probes, wait_empty(10) | the result's path and the probe's pidfd; the manager's writes to the scope's cgroup.procs (path watch with modify) and the probe's pidfd; holding probes block on their standard input, a latch only the suite holds; cgroup.events, a removed group taken as empty |
| 66_veldo_0042 data and child calls | time.time() deadline, timings, git/ssh/systemctl 20-60 s | a fixed far date as the dispatch deadline (the product only compares it); timings dropped (data only); child calls bounded by WAIT_HANG_SECONDS |
| 151:1010, 1020 (LINGER holder, "still there 1.5 s after SIGTERM and SIGHUP") | sleeping holder, 1.5 s window | fifo latches; engine/bin/veldo's supervisor now acknowledges each stop on its report (stop, passed_on); the row keeps its own copy of the report's read end and reads presence after both acknowledgements |
| 151:1119-1123, 1198, 1205 (2 s sleeps, a 30 s window, took under 4.0) | timed churn and a CPU-share bound | the idle supervisor is the production space_supervise with a counting stand-in (w per sleep, r per pass over the table); after each exit the row causes it waits for the next sleep and requires no pass; the wait row counts sleeps and reads through a seam on the CLI's poll and ends each holder only once the wait sleeps on it |
| 151:903, 1287, 1594, 1611, 1702 (5, 15, 30 s) | bounded polls | the captured-output read is a wait whose terminal condition is the supervisor keeping the pipe; report-loss waits on the path and the supervisor's pidfd; same-program finds its child by a fifo open (two gates) and the child's exec by a byte it writes; workers end on their pidfd |
| 151 follow() (120 s alarm) | red after 120 s | the end is released only once it is asleep (then=); a holder another account owns, or for settled() any unread holder (no part of the fixture by that function's own rule), is red at once and named; any other end that never comes is hung at the wait hang bound |
| 151 took < LINGER (fix2, handed) | an upper bound on the wrapper's return | the wrapper's wait on its supervisor while a guarded latch is held releases the latch first (seam): a wrapper that waits for what the command left returns only after it exited, and the row sees that |

New rows: timers/profile-applied and wave1/no-sites in both suites (the census over brief G's four files,
each read through its literal anchor); wave1/port-held in 66_veldo_0042. No row was removed; rows-kept.txt
lists both suites' labels before and after.

Timers (AC15): brief G owns no engine timer. Both suites set the timers table's profile (every entry at the
wait hang bound) on the table the copies they load share, under the key brief E's modules use, and the row
requires every effective value at the bound; 66_veldo_0042 also requires the containment module's two
entries once that module reads the table (brief E). On this branch the table has no entries.

## Falsifiers (brief G's block, finding 358)

| Case | Module | Suite | Target row | Result |
| - | - | - | - | - |
| wave358-space-window-restored | 151 (the 1.5 s window) | 66_veldo_0042 | wave1/no-sites | rejected: target row red, baseline and no-op green |
| wave358-clones-socket-timeout-restored | 66_veldo_0042 (the 2 s timeout) | 151 | wave1/no-sites | rejected: target row red, baseline and no-op green |
| wave358-cleanup-polled | mutation_ownership.py (the 5 s poll) | 66_veldo_0042 | wave1/no-sites | rejected: target row red, baseline and no-op green |
| wave358-port-released | v171_tailscale.py (read and release) | 66_veldo_0042 | wave1/port-held | rejected: target row red, baseline and no-op green |

mutants.txt also drives the registered space313 cases whose target rows brief G rewrote. Each mutant made
its target row red by assertion or terminal condition, and none hung: waits-for-what-the-command-left,
report-loss-cancels-the-supervision, stop-after-the-command-ends-the-supervisor (terminal: the supervisor
ended before both acknowledgements), table-read-at-every-exit (12 passes counted where 0 are allowed),
supervisor-keeps-the-callers-output, wait-sleeps-on-what-holds-nothing, wait-reads-at-every-unread-exit,
wrapper-gone-nobody-makes-the-end, follower-takes-the-closed-pipe-for-the-exit (re-run after 5a fix below).
what-the-command-left-is-killed cannot be judged on this host: its target row fix2/end-follows-their-exit is
red in the unmutated runs too, because processes outside the fixture hold the run (see below).

## Runs, and what this host could not show

| Run | Log | Result |
| - | - | - |
| Census over the tree; personal setup; canon copies | census.txt | pass; brief G's files have no site; 89 baseline entries (105 sites) removed; 0 personal-setup findings; copies equal |
| Suites 66_veldo_0042 and 151 unloaded, and the base | suites-unloaded.txt, rows-kept.txt | 66_veldo_0042 green, its residue row (red at base: two serve threads) green. Rows: superset of the base in both |
| Suites that load v171_tailscale.py or mutation_ownership.py, and the census suite | affected-suites.txt | all green except residue/86_veldo_0189 (brief F's item, as at base) |
| Mutants | mutants.txt | above |
| 66_veldo_0042 fifty times under the generator (2 slots, 6 spinners, 1 writer alive, probe slowdown 7.9) | loaded-66-first.txt, loaded-66-enodev-repro.txt | 49 green, 1 red: a cgroup removed while its cgroup.events was read answered ENODEV. Reproduced under the generator (run 13), fixed in the suite (5479ec5d). The fifty loaded runs on the final code were not run: host_heavy.sh had no free builder slot for over an hour, and the queued job was stopped |
| 151 under the generator | loaded-151-first.txt | abandoned: the suite was being edited while it ran |

Suite 151 is not green on this host, at base or now. Its own docstring states the reason: what holds a run
is read from the kernel's process table, and a process nobody here can read that started after the run holds
it (fail closed). This host runs hundreds of other accounts' processes, and unprivileged user namespaces are
refused (unshare and bwrap: uid map not permitted), so no private process table is available. The reds vary
from run to run, and every one is a run held or deferred by such processes (label_unread, owner_live, held
by other runs). Base fb7705e1 had 5 such reds in its one run here. The conversion removed the 120 s limit
that bounded these follows. To keep them from hanging, each now has a terminal condition: a holder another
account owns, or, in settled(), any unread holder, makes the row red at once and names it.

## Items for the lead

1. scripts/suites/support/waits.py (brief A): cgroup_populated() and CgroupEmpty treat only ENOENT as gone.
   A cgroup that is being removed answers ENODEV on read. Load showed this in suite 66_veldo_0042, which now
   catches it itself. Any other caller of waits.cgroup_populated can hit the same thing.
2. bin/veldo is changed together with engine/bin/veldo (paths/canon requires them equal). It is not in the
   specification's footprint.
3. Suite 151 and the AC10 fifty loaded runs need the gate's confinement: on this host they cannot be green.
4. AC15: brief G owns no table entry. On this branch the profile rows see an empty table. Their teeth come
   with brief E's entries (66_veldo_0042 requires control_containment's two entries once that module reads the
   table) and with E's and F's timers358 falsifiers.
5. Suite 151 emits its rows at its end, under names built at run time. A hung wait in it therefore prints no
   SELFTEST NOT RUN list (waits.static_rows reads literal names). This structure is inherited from the suite.
