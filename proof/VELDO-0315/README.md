# VELDO-0315 fix round 4

Implementation: `b53dc968079c81964034959c6e72c2220edb2ab7`, on `veldo-space-0315b`, from `031f1db6`
(fix round 3, whose README is in that commit). The second re-review
(rereview2-veldo-0315.md, verdict FIX) was read in full with its probes before any edit. One commit
for each finding, all by Dmitry Grinberg <dmitry@bcengi.com>, no trailers. No protected path changed.
The policy check and the full gate were not run: they are the lead's.

| Finding | Cause and correction | Commit |
| --- | --- | --- |
| 1 HIGH | Fix round 3 (0878d745) made the run's supervisor leave when its report pipe closed and on a stop sent after the command ended. The wrapper closes its end of the report after the staying line, so every run whose command left a process lost its supervisor and never got its end. Reverted: a report nobody reads ends the reporting and nothing else, a stop after the command ended ends nothing, and a wrapper that went while its command ran still gets the run's end from the supervisor's follower. The wait reads the process table again only when every holder the last read named has exited (the CPU result below). | `ca222518` |
| 2 MEDIUM | After a worker task that answered ok false, or whose worker was lost, the consumer advanced only when another task was queued, so a record received during the task waited for a later hook. After a task it always advances; stopping is the rule of a failed event dispatch alone. | `02d530ac` |
| 3 LOW | The owner's reconcile request waited for its worker task inside the request, in a reduced copy of the serve loop. Now the request's connection is kept on the task's ticket and SpacePending passes the layers that judged it; when the task completes the request is judged again by the same judge, as of the moment it was first judged, with the task's answer as its reconcile's, and answered. The reduced loop is gone. At the service's start, before the serve loop exists, the wait is on the worker's pipe alone. | `b53dc968` |

## What the "leaked" supervisors were, and the supervisor's CPU

Measured on this host before any change to the wait. The supervisors that outlived the suites
were not staying on what a fixture left. Other accounts' containers on this host start processes
many times a second (postgres connections, health checks). This account cannot read their
environment, each started after the run, so each holds the run (fail closed, VELDO-0313 fix round
2). A supervisor whose command left nothing therefore stays, and with processes of that kind always
starting it never ends. The suite's fixtures did end what their commands left.

The same processes were the CPU. The wait is on pidfds with no time limit: there is no timer and
no sleep loop. But it read the whole process table again at every exit of a holder, and with
holders exiting many times a second that was a busy process.

| Supervisor | Phase | CPU over 30 s | Wakes | Table reads |
| --- | --- | ---: | ---: | --- |
| before fix round 3 (0878d745^) | the left process alive | 0.00 s, 0.00 % | 0 | none |
| before fix round 3 (0878d745^) | left process ended, 110 unread holders | 3.78 s, 12.60 % | 407 | one at each exit |
| this round | the left process alive | 0.00 s, 0.00 % | 0 | none |
| this round | left process ended, 11 unread holders | 0.00 s, 0.00 % | 5 | none |

The first supervisor of a suite 151 run on the old wait had used 43.9 s of CPU after 6.5 minutes
(11 %). The change: the run cannot be over while one holder of the last read lives, so the table is
read again only when the last of them has exited; an earlier exit costs one wake and no read. A
holder that stops being one without exiting (its label is read later by the process reader) is
waited for until it exits: later than before, never earlier. Row supervise/staying-is-idle holds
this on any host: twelve unreadable processes end one by one over 30 s while the supervisor stays,
it uses under 1 % of a core and its count of read calls (/proc/PID/io) does not move.

For the owner (design section 7, the re-review's note): on a host like this one a run's supervisor
stays for as long as other accounts' processes keep starting, so the run's end is not made until
the process reader is installed or such processes are bounded another way. Nothing is removed
meanwhile, so no work is lost; the cost is space that is not freed. This round changes what that
costs in CPU, not the rule.

## Rows

Suite 151 (VELDO-0313's, the supervisor's home):

- supervise/report-loss-keeps-supervising, supervise/report-loss-end-is-made: the wrapper goes
  while the command runs; the supervisor is there 1.5 s later, the command runs to its own last
  line, the supervisor ends with the command's status, and the run's end is made.
- supervise/stop-after-the-command-ends-nothing, supervise/stop-after-the-command-end-is-made:
  SIGTERM and SIGHUP after the command ended leave the supervisor there, rule 3 holds the scratch
  root by it, nothing was sent; run finished follows the exit of the process the command left.
- supervise/staying-is-idle: above.
- fix2/end-follows-their-exit also finds the supervisor there 1.5 s after the wrapper returned.
  The end of fix2/captured-output-ends-at-return's run is now the row fix2/captured-end-follows.
- The fixture's pool holds every run of the suite, so a run whose end could not be made no longer
  turns every later row into exit 75. The suite ends every supervisor it started that is still
  there at its end.

Suite 156: ac3/failed-task-advances (finding 2, the probe's shape, for a refused task and for a
lost worker). ac3/reconcile-responsive and cli/slow-client (finding 3): the owner's signed request
goes through the real serve_one and the service's own apply; a hook packet and a client that sent
half a request and stalled are answered while the request is kept, and the request is answered ok
with no refusal set. The fix round 3 row supervise/closed-pipes asserted the reverted behavior
and is removed.

## Suites

Each ran alone with `nice -n 10 python3 -u -B scripts/selftest.py --suite NAME`. Counts include
the shared preamble. A selected run returns 2 by design when it passes. These are partial
regression results, not a landing decision. After each suite no `space supervise` process of the
run was left (checked by the runner after every suite).

| Suite | Passed | Failed | Seconds | Tree |
| --- | ---: | ---: | ---: | --- |
| 156_veldo_0315_reconcile | 60 | 0 | 27.42 | c09a5d02 |
| 153_veldo_0323_hook_events | 66 | 0 | 12.76 | c09a5d02 |
| 153_veldo_0337_verdict_recorded | 47 | 0 | 4.17 | c09a5d02 |
| 153_veldo_0314_session_hooks | 54 | 0 | 2.49 | c09a5d02 |
| 154_veldo_0335_released | 58 | 0 | 2.96 | c09a5d02 |
| 151_veldo_0313_space_run | 48 | 12 | 774.26 | b53dc968 |
| 66_veldo_0047_authority (extra) | 56 | 0 | 16.45 | c09a5d02 |
| 71_veldo_0130_api (extra) | 71 | 0 | 141.21 | c09a5d02 |

c09a5d02 was the first form of the third commit. b53dc968 differs from it in suite 151 alone (the
idle row ends its own helper processes in a finally), so the other suites' bytes and the
production bytes are the ones that ran.

Suite 151 on this host, unconfined. Longest silence 774 s, under the 20 minute limit. The three
fix2 rows of the known list passed: fix2/returns-at-the-commands-exit,
fix2/captured-output-ends-at-return, fix2/end-follows-their-exit. So did fix2/captured-end-follows.
The 12 failing rows:

- in the known host-bound list (review-fix/run-baseline.txt and
  review-fix/151_veldo_0313_space_run-final.txt), 10: ac1/build-output-has-item-and-goes,
  ac1/declared-started-ended, ac1/only-the-runs-own-items, ac2/act-waits-75, ac2/command-status,
  ac2/report-starts, fix3/handed-outside-the-tree, fix3/rewritten-environment-open-file-in-worktree,
  fix3/the-house-group, fix4/docker-objects-are-items;
- new rows of this round, 2: supervise/report-loss-end-is-made,
  supervise/stop-after-the-command-end-is-made.

Every one of the 12 fails the same way: a run's end was not made, or was held, because processes
this account cannot read hold the run ("still asleep after 120s on processes that hold the run",
label_unread, or a hold left admitted). That is the cause named above, not the fixture. Which rows
meet such a process differs from run to run: two earlier runs of this round's code gave 46/14 and
43/17, and fix2/end-follows-their-exit failed in both. A row that needs a run's end cannot be made
independent of this host by the fixture's pool; the pool fix is what lets
fix2/returns-at-the-commands-exit and fix2/captured-output-ends-at-return pass here in every run.
In a process table of its own the whole suite is green: the confined baseline of the final teeth
run for 313 observed 60 rows, 0 failed, all 34 rows of the suite among them.

## The reviewer's probes

| Probe | 031f1db6 (the re-review) | Now |
| --- | --- | --- |
| P2 probe_wrapper.py | supervisor gone under 5 s after the wrapper returned, holder alive | `staying True`, supervisor gone within 5 s: False, holder alive. After the probe ended its holder the supervisor stayed on the host's unread processes in one run (ended by me) and ended by itself in another. |
| P3 probe_strand.py | no further spawn: STRANDED | spawns `['task', 'event']`: dispatched |

## Teeth ran last

Order 313, 315, 323, each `nice -n 10 python3 -u -B scripts/check_teeth_mutations.py --finding N
--jobs 4`, at b53dc968 with a clean tree. Nothing in the worktree was written while they ran: the
digest over every tracked file was `8b2a160de7e917968b67be9043f4a4b05a8e745731a1d1160c6d8deabbb5bb3d` before and after, and `git status` was
empty. This README was written after the last one returned. No test ran after them.

| Finding | Registered | Executed | Rejected | Reused | Invalid | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 313 | 40 | 40 | 40 | 0 | 0 | 0 |
| 315 | 24 | 24 | 24 | 0 | 0 | 0 |
| 323 | 16 | 16 | 16 | 0 | 0 | 0 |

Input digest of all three receipts:
`e7a5e19bad3c70a6cacaa1ad66a0bfe537a905036665f51fb9d4b3407c4ab9a5`. No teeth worker was left. The
runner's check at the instant the last run returned counted one `space supervise` process of this
account; eleven seconds later there was none.

Fix round 3 registered no teeth case for the supervisor's exit; it had only the suite row
supervise/closed-pipes, now removed. The restored behavior has cases of its own:

| New case | Mutation | Row it turns red |
| --- | --- | --- |
| space313-report-loss-cancels-the-supervision | a failed report write exits the supervisor | supervise/report-loss-keeps-supervising |
| space313-stop-after-the-command-ends-the-supervisor | the stop handler exits after the command ended | supervise/stop-after-the-command-ends-nothing |
| space313-table-read-at-every-exit | the wait returns to a table read after one exit | supervise/staying-is-idle |
| space315-failed-task-stops-the-dispatcher | the advance after a task depends on its answer | ac3/failed-task-advances |
| space315-reconcile-waited-inside-the-request | the request is never kept: the wait is inside it | ac3/reconcile-responsive, cli/slow-client |

Two existing 313 cases kept their defect and moved their anchor with the wait:
space313-what-the-command-left-is-killed and space313-end-waits-on-a-timer.

An earlier teeth sequence of this round, at c09a5d02, gave 315 24/24, 323 16/16 and 313 39/40:
space313-supervisor-does-not-stay ran past its worker deadline (129 s), because under that mutant
the idle row raised early and left its twelve helper processes to the suite's end, which waits 30 s
for each. The row now ends them in a finally; the three commits were rebuilt with that one change
and every teeth run was repeated, which is the table above.

## Fix round 5 (the third re-review, FIX small)

Commits on 83b3e7df: 1231231b (finding 1), d4081b83 (finding 2), 7914c83e (finding 3), then two
repairs of this round's own cases and row, 7c87cfd7 and a5bfee60, and this README.

Finding 1, the wait. The reviewer's probe_wait.py (a run holder `sleep 1` and an unread holder
`sleep 20` that the next read no longer names), run by me:

| Tree | The wait returned after | Reads |
| --- | ---: | ---: |
| 031f1db6 | 1.0 s | 2 |
| 83b3e7df | 20.0 s | 2 |
| this round | 1.0 s | 2 |

The exit of an unread holder while another holder lives is still one wake and no read
(supervise/staying-is-idle and the second check of the new row).

| New row | Suite | What it shows |
| --- | --- | --- |
| supervise/wait-reads-again-at-a-read-holders-exit | 151 | the probe's shape; and no read at an unread exit |
| supervise/wrapper-gone-the-follower-makes-the-end | 151 | the real space_supervise, wrapper gone, nothing left: its follower makes the end after it ended. Stand-ins: the end writes a file, an unreadable process is no holder |
| supervise/none-stays-on-nothing | 151 | each surviving supervisor is classified before it is ended |
| f3/first-not-behind-second | 156 | the first owner reconcile is answered while a second, for another project, still runs |

| New case | Mutation | Row it turns red |
| --- | --- | --- |
| space313-wait-sleeps-on-what-holds-nothing | the wait reads again only when every named holder exited | supervise/wait-reads-again-at-a-read-holders-exit |
| space313-wait-reads-at-every-unread-exit | every exit is a read | supervise/wait-reads-again-at-a-read-holders-exit |
| space313-wrapper-gone-nobody-makes-the-end | the reviewer's falsifier 5 | supervise/wrapper-gone-the-follower-makes-the-end |
| space315-reconcile-wait-nested-in-the-request | the wait inside the request, serving both sockets from there | f3/first-not-behind-second, alone, in 44 s |

Suites, each alone with nice -n 10, on the tree of 7914c83e (before the two repairs; the repair
a5bfee60 changes one check of one row of suite 151, and that suite was not run on the host again:
its run after that is the teeth baseline below). No `space supervise` process was left after either.

| Suite | Passed | Failed | Seconds |
| --- | ---: | ---: | ---: |
| 156_veldo_0315_reconcile | 61 | 0 | 37.66 |
| 151_veldo_0313_space_run | 51 | 12 | 426.64 |

The 12 red rows of 151, on a host where another gate ran at the time. Eight are in the list of
11 (9 host rows and the 2 end-is-made rows): ac2/act-waits-75, ac2/command-status,
ac2/report-starts, fix2/end-follows-their-exit, fix3/handed-outside-the-tree,
fix3/rewritten-environment-cwd-in-scratch, fix3/unread-process-holds,
supervise/stop-after-the-command-end-is-made. Three of the 11 were green:
ac1/build-output-has-item-and-goes, ac1/declared-started-ended, supervise/report-loss-end-is-made.
Four are not in the list: fix2/captured-end-follows, fix3/rewritten-environment-open-file-in-worktree,
fix3/the-house-group (each: the run's end still asleep after 120 s on unread processes of the host)
and fix4/docker-objects-are-items (an item deferred). They read as the same host cause, and I did
not prove that for each. In the teeth baseline, in a process table of its own, every row of the
suite is green. The three new rows of 151 were green on the host.

Teeth ran last, 313 then 315, `--jobs 4`, at a5bfee60 with a clean tree. The digest over every
tracked file was `efa8f12a8f7a92a39dab5edd93ab91b3d84d5293765f6ce736c6ba21bfdb25d2` before and
after, `git status` was empty, and no supervisor or teeth worker was left. This README was
written after the last one returned. No test ran after them.

| Finding | Registered | Executed | Rejected | Reused | Invalid | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 313 | 43 | 43 | 43 | 0 | 0 | 0 |
| 315 | 25 | 25 | 25 | 0 | 0 | 0 |

Input digest of both receipts: `3b29f937b1bdc3c9eb27ed2f532448676dc9f6b819063da53e4dcea1f3462494`.

Two earlier teeth sequences of this round were not green, and each led to a commit:

- At 7914c83e: 313 stopped at 12 of 16 executed, because space313-what-the-command-left-is-killed
  anchored on the line finding 1 changed; 315 gave 24 of 25, the new nested case ran past its
  120 s limit because its nested wait did not serve the packet socket. Repaired in 7c87cfd7.
- At 7c87cfd7: 315 gave 25 of 25; 313 was refused as an invalid baseline. Under the unchanged code
  two rows were red in the no-change control: the new follower row, which read the supervisor's
  collection where it meant its end (repaired in a5bfee60), and
  supervise/stop-after-the-command-ends-nothing, an existing row, whose cause I did not find. It
  was green in that run's baseline and in both controls of the final run.

Finding 323 was not run in this round.

## Not proven here

- No CLI process is served a ledger yet (bin/veldo, _space_wired), so a real supervisor's follower
  never reaches _space_finish. As everywhere in suite 151, the "end is made" rows call the
  follower's function in the suite's process. Since fix round 5 the branch that makes the end
  when the wrapper is gone and nothing is left has a row and a teeth case, with a stand-in for
  the end (below).
- cli/slow-client holds on the old code too: the reduced loop's missing handling was never reached
  by a client that only stalls. What turns red under the old shape is ac3/reconcile-responsive,
  through the case space315-reconcile-waited-inside-the-request.
- A kept API request is judged again when its task ends. The API judge's clock is held at the
  moment of the first judging for that call, and the service's count of API calls is put back by
  one when the request is kept, so the call is counted once. Suite 156's API row calls the judge
  directly and suite 71 passes; no row sends a kept API reconcile through the socket.

Only summaries are stored here. Logs, receipts, diffs and the probe scripts are in `/tmp/v315-r4/`
(round 4) and `/tmp/r5/` (round 5) on the build host. Historical proof under `review-fix/` is unchanged.

## Gate fix round, 2026-11-16

Targeted checks at `50c69b7ee35a36f6ea8fa729ea3e913058a24624`; no full gate was run or claimed.
Group commits: integration `2823e011`, 0315 `ae0009b3`, 0329 `94952250`, host `50c69b7e`.
The only protected file changed was the explicitly authorized `scripts/gate_unconfined.json`.

All 19 selected suites ran with `nice -n 10 python3 scripts/selftest.py --suite NAME`.
16 selections had zero failed rows. Passing selections: `03_plugin_extension_loading_runner`, `104_veldo_0210_mutation_workers`, `107_veldo_0153_identity_push`, `108_veldo_0153_executor_profile`, `126_veldo_0230_qualify_reproduces`, `127_veldo_0259_installation`, `134_veldo_0331_space_mode`, `143_veldo_0305_space_census`, `144_veldo_0306_space_docker`, `145_veldo_0307_space_docker_ownership`, `14_warp_0717_subset_runner`, `150_veldo_0329_hook_install`, `155_veldo_0304_space_boundary`, `156_veldo_0315_reconcile`, `86_veldo_0168_text`, `86_veldo_0189_engine_upgrade`.
Personal-setup checking reports zero findings. State-root error naming was checked directly.

Remaining rows were preserved: 0208 has two failing kernel-double rows (unavailable/old ABI);
0215 store-pruned expects age deletion, conflicting with accepted 0304 removal only for a gone
authority, and a row correction still needs the lead ruling requested during this run;
0344 ac6/installed reports `no_pin`, because the host space section names no reader digest.
The compiler builds themselves succeeded with their temporary files inside fixture folders.

Teeth ran last, with no worktree writes during any run:

| Finding | Status | Executed | Rejected | Reused | Surviving workers |
| --- | --- | ---: | ---: | ---: | ---: |
| 154 | passed | 10 | 10 | 0 | 0 |
| 307 | passed | 37 | 37 | 0 | 0 |
| 315 | passed | 25 | 25 | 0 | 0 |
| 329 | passed | 18 | 18 | 0 | 0 |

The first direct 154 run was invalid because standalone teeth confines every worker; its final
run uses `check_gate_mutations.py --finding 154`, which reads the existing authority declaration
and runs the same teeth driver in its declared host leg. The first 315 run was invalid because
the retained worker-log path exceeded the Unix socket path limit; its final run uses a short
worker directory. Neither rerun changed code or rows. All final receipts have zero invalid
results and zero surviving workers. No space supervisor from this round remained.

Logs and receipts are retained in `/tmp/space-0329b-gate-fix/` on this host.
