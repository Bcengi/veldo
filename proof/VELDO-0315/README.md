# VELDO-0315 small round after 3b13a979

The failing row was `VELDO-0337 safety/review-scratch-in-use`: both the on-demand
lost-verdict recovery fixture and the borrowed-login safety fixture used `planted('22')`.
The second call raised `FileExistsError` for `scratch/22`, before its safety assertions
and the later wiring/canon row could run. The reproduced result was 45 passed, 1 failed.
The fix gives the on-demand fixture ID `23`. Every assertion remains intact, including
Runtime leaving verdict recovery to the start reconcile and the longer engine-canon list.
Production code is unchanged. Both recovery and scratch safety now execute successfully.

On 2026-11-15, all requested suites ran through
`nice -n 10 python3 -B scripts/selftest.py --suite NAME`, with bytecode writes disabled.
The suite driver also ran at niceness 10, so these suite processes inherited niceness 19.
Counts include the shared preamble; these are partial regression results, not aggregate
unit evidence or a landing decision. Green selected runs return 2 by design.

| Suite NAME | Passed | Failed | Exit |
| --- | ---: | ---: | ---: |
| 156_veldo_0315_reconcile | 51 | 0 | 2 |
| 153_veldo_0323_hook_events | 66 | 0 | 2 |
| 153_veldo_0337_verdict_recorded | 47 | 0 | 2 |
| 153_veldo_0314_session_hooks | 54 | 0 | 2 |
| 154_veldo_0335_released | 58 | 0 | 2 |
| 151_veldo_0313_space_run | 37 | 17 | 1 |

The 0313 failure names exactly match all 17 known host-bound rows in
`review-fix/151_veldo_0313_space_run-final.txt`, with no new failing row. Its shared-host
process/lifecycle limits remain unchanged; the run took 382.14 seconds.

Teeth ran LAST, sequentially for findings 314, 315, 323, 335 and 337, using
`nice -n 10 python3 -B scripts/check_teeth_mutations.py --finding N --jobs 4`, plus
`--worker-log-dir /tmp/v315-small/wN --diff-dir /tmp/v315-small/dN`.
No worktree file was written while any teeth stage ran. Tracked-file SHA-256 values,
sizes and modification times were identical before and after the entire sequence;
the worktree status still contained only the one-line suite edit. This README was
updated after all five stages finished. No test was run after teeth.

| Finding | Executed | Rejected | Reused | Surviving workers | Exit |
| --- | ---: | ---: | ---: | ---: | ---: |
| 314 | 20 | 20 | 0 | 0 | 0 |
| 315 | 22 | 22 | 0 | 0 | 0 |
| 323 | 16 | 16 | 0 | 0 | 0 |
| 335 | 14 | 14 | 0 | 0 | 0 |
| 337 | 22 | 22 | 0 | 0 | 0 |

All five receipts report `passed`, no invalid results, and input digest
`9b3d64f25aa7ddcef08d3369e4a07a1f6fa8489d5fe27bf2eb6769631cf041df`.
Full diagnostic logs, receipts and mutation diffs remain outside the worktree at
`/tmp/v315-small/`; these are local artifacts, not durable aggregate gate evidence.
Only this README and the unprotected 0337 suite changed. No protected path changed.
Policy checking and the full verification gate were not run; both remain with the lead.

# Earlier VELDO-0315 review fixes

The implementation is committed at 361211d50f448a5d83bc3fe5a6cd1e4a1761cb7a, after carry-over commits d412260f and ba390ad9
on integration base 9b5ca496. All six requested fixes are implemented. This bundle records
partial regression runs and selected teeth stages. It is not an aggregate unit result, an
independent review, or a landing decision. Every acceptance criterion remains pending the
lead's full gate and review. No protected path changed. Policy checking and the full gate
were not run.

1. Service startup synchronously bootstraps, replays and reconciles, then starts the 0323
   consumer. Shutdown stops and reaps its child. The real serve-order row checks both edges;
   received-event recovery runs once after pending records drain.
2. Reconciler.run invokes FloorAuthority.reconcile_verdicts before compare; Runtime no longer
   invokes it at startup. The 0337 lost-send row uses Service.space_start and the on-demand
   service method, verifies the lost verdict is sent, and checks repeat calls send nothing.
3. Recovery and Signal use the same per-item filesystem lock. Recovery rereads the item under
   that lock before acting. The stale-read row was red before the fix (race-before.txt), then
   green. The cross-process row holds the lock over a marked folder and proves reconcile
   cannot restore it before release, independently of Signal's nested lock.
4. Docker subscribes before disk reconciliation, remains subscribed after a named startup
   failure, and retries on the next event. On demand restores a missing stream. The startup
   snapshot contributes to counts once.
5. A removing worktree absent at both names and lacking a keep record must become deferred
   with keep_failed. Its mutation removes the absent-item completion guard and turns the
   designated row red.
6. veldo space reconcile signs an owner command and sends it through the authority service.
   The API route reaches the same service method. An optional project selects one project;
   omission selects all. Removal safety still reads foreign-project children from the full
   ledger, so selecting a project cannot hide work nested inside a due parent.

The final targeted runs used nice -n 10 and the repository selftest entry point. Of 22 suites,
19 have no failed assertions. The primary totals are 0315: 51/0, 0323: 66/0, and 0337: 45/0.
These totals include the shared preamble; ticket rows are 25, 40 and 19 respectively. Selected
selftest runs intentionally return nonzero even when green and cannot satisfy aggregate unit
evidence. See review-fix/targeted-results.json for all commands, counts, logs and row names.

Three failing suites were compared with an unchanged archive of 9b5ca496 on this host:
census has 51/1 on both (invalid owner.scope); Docker has 54/1 on both (a static poll-set
assertion); run-wrapper has 37/17 here and 36/18 at base, with no current-only failing row.
The API suite failed its restart row in two slower runs, passed 71/0 at base, and passed 71/0
on the final rerun with fuller diagnostics and no production change. Its cause is unproven.
Both failure and passing outputs are retained. The temporary baseline archive was removed
with a plain command before teeth.

The final teeth sequence was 315, 323, then 337, all at nice -n 10 with four workers. Results
are 22/22, 16/16 and 19/19 rejected mutations, zero reuse and zero surviving workers. The
receipts share one input digest. No worktree file was edited while those stages ran; this
proof was written only after all three completed. Full receipts and exact mutation diffs
are retained. Earlier 315 attempts are retained too: the first had invalid baseline controls
because the long output path exceeded the Unix socket pathname limit; the next exposed two
test gaps; both corrected mutations then passed a focused check before the final sequence.

Validation, generated files, template sync, lint and diff checks passed before the final
teeth sequence. Later changes after the broad checks only strengthened test diagnostics,
the lock row and the mutation anchor; lint and the affected suite were rerun. Protected-path
comparison was empty. Acceptance criteria and production safety prerequisites were not relaxed.

Fixture limits: suite 156 uses temporary real Git repositories and SQLite ledgers, real
removers, real forked workers and real owner signatures. Docker and process observations are
fixtures. The CLI transport is a fixture that reaches real Service.apply; the floor provider
in the lost-send row supplies real FloorAuthority objects with fixture materialization.
Act prerequisites are fixture inputs; these runs do not authorize production act mode.
A removing item whose recorded carrier is still this service process remains protected by
AC5 until that process ends, including the review's same-process left_at case.

The root-level files other than this README and manifest are historical carry-over evidence.
The current evidence is under review-fix/. Original README and manifest copies are retained
there for provenance; they do not describe the current integration state.
