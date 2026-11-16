# VELDO-0315 fix round 3

Implementation: `0878d74524e027cc0b061afb0df0a4fa6d0e2102`, on `veldo-space-0315b`, from `daa49a1e`.
The independent re-review was read in full before editing. Each finding has its own
commit, followed by the separate supervise fix. All commits use Dmitry Grinberg
<dmitry@bcengi.com>, with no trailers. No protected path changed.

| Finding | Cause and correction | Commit |
| --- | --- | --- |
| F1 | Startup omitted the land entry before the loop existed. Read installed work roles and pass land data to replay, including retries. Real serve replays, records and consumes a trunk event. | `60c7e87b` |
| F2 | Replay ran git and observer signing in the service. Run it in the space worker with the replay deadline, waiting on its pipe before reconcile. The row records git-launching PIDs across startup. | `85d0bc75` |
| F3 | Inline reconcile waited on item locks in the service. Coalesce worker tasks, keep serving packets while CLI/API wait for their result, and queue at most one Docker retry. Docker subscriptions stay in the service. | `dac93409` |
| F4 | Owner refusal, pre-reconciler failure, child reaping and repeat-write checks were absent. Add them; avoid unchanged measurement writes so repeat reconcile adds only space_reconcile records. Update mutation anchors without weakening their defects. | `de1a5622` |
| Supervise | Broken report writes were ignored; SIGTERM only forwarded to a live command. A blocking pipe watcher exits on report-reader loss, control EOF before startup cancels, and SIGTERM exits after forwarding. | `0878d745` |

Pipe cancellation leaves the run pending; it does not manufacture a run-finished event.
The supervise row covers control EOF, report-reader loss before and during a command,
and SIGTERM. Tests clean up only their own fixture commands.

## Requested suites

Each ran sequentially with `nice -n 10 python3 -u -B scripts/selftest.py --suite NAME`.
The final 156 rerun follows the one-line row-registration correction. Other suite
implementation bytes are unchanged since their final runs. Counts include the shared
preamble. Successful selected runs return 2 by design; these are partial regression
results, not aggregate unit evidence or a landing decision.

| Suite | Passed | Failed | Seconds |
| --- | ---: | ---: | ---: |
| 156_veldo_0315_reconcile | 59 | 0 | 37.72 |
| 153_veldo_0323_hook_events | 66 | 0 | 13.23 |
| 153_veldo_0337_verdict_recorded | 47 | 0 | 4.44 |
| 153_veldo_0314_session_hooks | 54 | 0 | 2.57 |
| 154_veldo_0335_released | 58 | 0 | 3.00 |
| 151_veldo_0313_space_run | 36 | 18 | 486.81 |

151 completed without the 20-minute no-output watchdog firing. Its 18 failing row
names exactly match the union of the retained known host-bound failures in
`review-fix/run-baseline.txt` and `review-fix/151_veldo_0313_space_run-final.txt`.
No supervise process from these runs survived any suite; the final 156 rerun was
also checked. Engine copies, ASCII, syntax, diff whitespace and protected-path
exclusion were checked before the final teeth sequence.

## Scratch falsifiers

The reviewer's exact M3, M5 and M6 replacements were applied separately in
`/tmp/v315-r3/mut`, outside the worktree, restored after each run, and run at niceness 10.

| Falsifier | Failing row | Passed / failed |
| --- | --- | --- |
| M3 | space315/ac7/stop-reaps | 58 / 1 |
| M5 | space315/cli/non-owner | 58 / 1 |
| M6 | space315/ac3/failure-before-reconciler | 58 / 1 |
| CLI-no-service | space315/cli/service-project | 57 / 2 |

All three surviving falsifiers now turn exactly their new row red. The extra
CLI-no-service check confirms the authorization row remains registered when the
CLI returns early. No supervise process survived these scratch runs.

## Teeth ran last

Final order: 314, 315, 323, 335, 337; each used `nice -n 10 python3 -u -B
scripts/check_teeth_mutations.py --finding N --jobs 4`, with worker logs and diffs
under `/tmp/v315-r3/final-teeth/`. Bytecode writes were disabled. No worktree file
was written during the sequence; all 8,489 tracked files retained identical SHA-256
contents, sizes and mtimes. This README was written only after all five completed.
No test was run after final teeth.

| Finding | Executed | Rejected | Reused | Invalid | Surviving workers | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 314 | 20 | 20 | 0 | 0 | 0 | 0 |
| 315 | 22 | 22 | 0 | 0 | 0 | 0 |
| 323 | 16 | 16 | 0 | 0 | 0 | 0 |
| 335 | 14 | 14 | 0 | 0 | 0 | 0 |
| 337 | 22 | 22 | 0 | 0 | 0 | 0 |

All five final receipts report `passed`, with input digest
`b3b3e45a37bc139fd96d7b48bc50f14a4c693ce131ad0598854e3f3143619e9b`.

Iteration results retained outside the worktree: the initial 0323 replay-list crash
was fixed by normalizing task results; the restored 0337 guard initially failed
(46/1) on repeated measurements and now passes. Initial 151 was 35/19: its extra
timer assertion led to the blocking pipe watcher; final 151 has only the 18 known
host-bound failures. The first teeth sequence passed 314/323/335/337 but 315 was
21/22 with one invalid CLI-no-service result because its early return removed the
non-owner row. That row now always executes. After the correction, 156 and all
three reviewer falsifiers were rerun, followed by the full successful final teeth
sequence. The first frozen sequence also had no tracked-file changes or survivors.

Only small summaries are stored here. Full logs, receipts, diffs and scratch data
remain in `/tmp/v315-r3/`; these are local diagnostic artifacts. Historical proof
under `review-fix/` is unchanged. Policy checking and the full verification gate
were left to the lead, as requested.
