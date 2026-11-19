# VELDO-0329b gate fix: the anchor round (group C)

Gate 99zz3 (head 20377f1f) stopped its mutation stage at the first moved anchor and executed 0 of 3596.
A static count of every registered case (each `old` and `also` text must occur exactly once in its module,
through `mutation_observer.mutate`) gave 16 moved of 3591 at 20377f1f and gives 0 moved of 3591 after this round.

Disposition: all 16 are re-anchored, none is retired. In every case the defect still has a home. The 13 cases
VELDO-0304 moved mutate the no-ledger removal, which 0304 took out and then put back behind
`control_space_remove.remove_standalone` (the look, the keep step and the delete in one call the caller cannot
answer for); each case now injects the same defect at the caller's call of it. No row, suite or production
file changed; only `old`/`new` in scripts/check_teeth_mutations.py.

Shown rejected: each case was applied once through the driver's own `materialize()` and `worker()`, the
unchanged copy and then the mutated copy, outside the gate (every suite is numbered below 151). "Unchanged"
is the target rows on the unchanged copy, "mutated" on the mutated copy; in brackets the count of all false rows.
This is not the mutation stage: that runs only under the gate lock.

| Case | Suite, module | Moved by | Where the defect lives now | Unchanged | Mutated | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| authority-refusal-not-observed | 66 (66_veldo_0047_authority), control_service.py | VELDO-0312 (e4678ecf) | the count of the observation, which now stands before `self.space_pass()`; a refused command is still not counted | authority/observations true [0] | authority/observations false [1] | re-anchored, rejected |
| space312-abandon-defaults-to-the-owners | 149 (149_veldo_0312_ticket_ended), control_service.py | VELDO-0315 (d412260f) | the signature of `space_abandon`, which gained `_retry=False`; the cause still defaults to the owner's | r2/abandon-names-its-cause true [0] | r2/abandon-names-its-cause false [1] | re-anchored, rejected |
| space306-volumes-first | 144 (144_veldo_0306_space_docker), control_space_kinds.py | VELDO-0337 (8f99aeaa) | the `ORDER` line with the two review run kinds; volume still before container | ac3/order-and-non-forced true [0] | ac3/order-and-non-forced false [2] | re-anchored, rejected |
| worker129-worker-config-executed | 82 (82_veldo_0129_worker_wiring), control_launch_work.py | VELDO-0304 | the `import-` temporary folder, which no longer names the candidates folder; git still runs in the worker's tree first | build/config-neutralization true [0] | build/config-neutralization false [1] | re-anchored, rejected |
| delivery158-run-directory-kept | 85 (85_veldo_0158_credential_delivery), control_launch.py | VELDO-0304 | the receiver's call of `remove_standalone(run, 'folder')`; the answer is given as clear and nothing is removed | delivery/private-dir-removed true [0] | delivery/private-dir-removed false [2] | re-anchored, rejected |
| role127-staged-skill-outlives-run | 86 (86_veldo_0127_agent_configuration), control_launch.py | VELDO-0304 | the `_unstage_skills()` before that same call; the links are left for close() alone | review/skill-commit true [2] | review/skill-commit false [3] | re-anchored, rejected |
| space303-fleet-owner-of-another-worktree-signalled | 142 (142_veldo_0303_space_paths), fleet.py | VELDO-0304 | the `alone` test in fleet.space_signal, which reads the owner's other live repository items itself now; the test finds none | ac1/fleet-alone true [0] | ac1/fleet-alone false [1] | re-anchored, rejected |
| space303-fleet-removes-without-the-keep-step | 142 (142_veldo_0303_space_paths), fleet.py | VELDO-0304 | fleet.remove's call of `remove_standalone`; git's remove runs directly and the answer is given as kept | loss/fleet-reset-commit true [0] | loss/fleet-reset-commit false [4] | re-anchored, rejected |
| space303-clone-provision-direct-delete | 142 (142_veldo_0303_space_paths), control_clone.py | VELDO-0304 | the `if self.space is None:` of a failed provision (its comment was reworded); a clone with a ledger goes the no-ledger way | ac2/failed-provision true [0] | ac2/failed-provision false [6] | re-anchored, rejected |
| space303-receiver-deletes-a-run-directory-without-the-look | 142 (142_veldo_0303_space_paths), control_launch.py | VELDO-0304 | the receiver's call of `remove_standalone(run, 'folder')`; the folder is deleted directly and the answer given as clear | loss/run-directory-repository true [0] | loss/run-directory-repository false [1] | re-anchored, rejected |
| space303-sweep-deletes-a-run-directory-without-the-look | 142 (142_veldo_0303_space_paths), control_launch.py | VELDO-0304 | the sweep's call of `remove_standalone(place, 'folder')`; the same | loss/run-directory-repository true [0] | loss/run-directory-repository false [1] | re-anchored, rejected |
| space303-landing-line-deletes-a-candidate-without-the-look | 142 (142_veldo_0303_space_paths), control_launch_work.py | VELDO-0304 | the landing line's call of `remove_standalone(directory, 'agent_repository', ...)`; deleted directly, answer given as kept | loss/candidate-commits true [0] | loss/candidate-commits false [1] | re-anchored, rejected |
| space303-lander-deletes-a-workspace-without-the-look | 142 (142_veldo_0303_space_paths), lander.py | VELDO-0304 | what the lander does with a workspace the remover did not remove; it is deleted where it was recorded as staying | loss/candidate-commits true [0] | loss/candidate-commits false [7] | re-anchored, rejected |
| space303-lander-keeps-every-candidate | 142 (142_veldo_0303_space_paths), lander.py | VELDO-0304 | the `candidate=c` the lander gives the remover; with none the rebuildable look is never made and every candidate is kept on refs | fix/candidate-rebuildable true [0] | fix/candidate-rebuildable false [5] | re-anchored, rejected |
| space303-lander-removes-a-candidate-without-either-look | 142 (142_veldo_0303_space_paths), lander.py | VELDO-0304 | the lander's call of `remove_standalone` for the workspace; deleted directly, answer given as rebuildable | fix/candidate-fail-closed true, loss/candidate-commits true [0] | fix/candidate-fail-closed false, loss/candidate-commits false [8] | re-anchored, rejected |
| space303-lander-gives-the-look-no-remote | 142 (142_veldo_0303_space_paths), lander.py | VELDO-0304 | the `remote=` the lander gives the remover; None | fix/candidate-rebuildable true [0] | fix/candidate-rebuildable false [5] | re-anchored, rejected |

role127-staged-skill-outlives-run: the 2 false rows on the unchanged copy are VELDO-0127 live/claude and
live/codex (stale live captures, group D, the lead's recapture); the target row is true there and false on the
mutated copy.

Two pairs now share an anchor line with another registered case and differ in what they put there:
delivery158-run-directory-kept and space303-receiver-deletes-a-run-directory-without-the-look (the first
removes nothing, the second deletes without the look), and each of the receiver, sweep, landing line and
lander cases with its space304-*-direct-* neighbour (those add a delete before the call and are judged by
suite 155's boundary rows; these replace the call and are judged by suite 142's loss rows).

For the lead, under the lock: `python3 scripts/check_gate_mutations.py --finding N` for N in 47, 127, 129, 158,
303, 306, 312, then the full stage in the gate. No teeth case has yet executed on this branch in a gate, so
survivors of other tickets can still appear once the stage runs.

## Gate fix 3: the case that did not compile (gate 99zzD)

Gate 99zzD stopped its mutation stage at newproject143-take-on-not-due: its anchor still occurred once, but
VELDO-0323 (e466bed0) had put the space consumer's lines inside the `if` the case replaced with `pass`, so the
mutant left an indented orphan block (IndentationError at control_service.py:2251).

| case | suite, module | moved by | re-anchored at | disposition |
|---|---|---|---|---|
| newproject143-take-on-not-due | 110 (110_veldo_0143_new_project), control_service.py | VELDO-0323 (e466bed0) | the `if self.watermark() > before:`, `self.projects_due = True` and the first consumer line; the defect replaces only the assignment and keeps the consumer block under the if | re-anchored, rejected: suite 110 unchanged 109 of 109; mutated, provision/handed-over false and 108 passed |

Static check over every registered case after the change (each mutant applied in memory, every Python one parsed
with ast): 3591 cases, 3473 Python mutants, 0 moved, 0 that do not parse. The case was executed by hand (suite 110
run with nice in a scratch worktree holding the mutant, not the teeth runner); the stage itself runs under the lock.

## Gate fix 4: the 19 survivors of gate 99zzF (head 7aa9ea2a)

Gate 99zzF ran the mutation stage to its end for the first time: 19 cases survived, 17 of suite 142 (finding
303) and 2 of suite 146 (finding 308). All 19 were stale teeth of one cause, shown from the code and by running
each mutant: VELDO-0304 moved the deciding check into the remover (control_space_remove.py), and the two suites
still gave the copy under test only to the callers.

From the code. With no ledger every delete goes through `remove_standalone`, which loads the look from the
`control_space_standalone.py` beside itself and makes it there ("A caller cannot supply an earlier safe
answer"). Suite 142 loaded the five callers from .veldo and handed them the mutated look only as their own
earlier look (`module._SPACE['standalone'] = SA.standalone`), so the remover those callers reached looked with
the unmutated file. A pin is released only by `Clones._release`, which is `remove_ref`, and that refuses any
ledger item that is not removed; so a release the retirement asks too early is refused one layer down.

By running. Every case of findings 303 and 308 was applied once through the driver's own `materialize()` and
`worker()`, each in its own process under `nice -n 10`, before (7aa9ea2a) and after this round; a case counts
as rejected only when every target row is false on the mutated copy, as the stage judges it. Before: 27 of 44
and 36 of 38 rejected, and the 19 survivors are exactly the gate's. After: 44 of 44 and 39 of 39 rejected,
the unchanged copy and the no-op copies green (64 of 64 observed rows). Every line is in gate4-cases.txt.
Suites 142 and 146 alone through scripts/selftest.py: 38 rows, 64 passed, each. This is not the mutation
stage, which runs only under the gate lock.

No case is retired and no product check was missing. What changed:

1. Suite 142 loads the modules under test from the folder of the copy under test (HOME: the whole copy of
   .veldo the driver makes for a mutant, .veldo itself otherwise), so each finds its siblings, the remover and
   through it the look, beside itself; fleet.py, which names its siblings from the repository root, has its
   .veldo ones taken from HOME. No production file changed and no seam was added.
2. Suite 146 does the same, and names control_space_remove.py as a module a case may mutate.
3. One case is re-anchored, one is added, two rows gained checks, one fixture was made independent of the clock.

| # | Case | Module | Target rows before (7aa9ea2a) | Target rows after | Disposition |
| --- | --- | --- | --- | --- | --- |
| 1 | space303-standalone-ignored-work-not-looked-for | control_space_standalone.py | loss/fleet-ignored-file true | false | rejected again, case unchanged: the remover looks with the copy under test |
| 2 | space303-standalone-nested-repository-not-looked-for | control_space_standalone.py | loss/fleet-nested-repository true | false | same |
| 3 | space303-candidate-fetched-trunk-holds-nothing | control_space_standalone.py | fix/candidate-rebuildable true | false | same |
| 4 | space303-candidate-unaccounted-commit-goes | control_space_standalone.py | fix/candidate-fail-closed, loss/candidate-commits, fix2/unrecorded-commit-kept true | all false | same |
| 5 | space303-candidate-any-head-commit-is-the-landers | control_space_standalone.py | fix/candidate-fail-closed, fix2/unrecorded-commit-kept true | all false | same |
| 6 | space303-candidate-head-commit-by-its-parents | control_space_standalone.py | fix2/unrecorded-commit-kept true | false | same |
| 7 | space303-candidate-noted-commit-not-the-landers | control_space_standalone.py | fix2/unrecorded-commit-kept true | false | same |
| 8 | space303-candidate-record-commit-is-the-landers | control_space_standalone.py | fix3/generator-commit-kept true | false | same |
| 9 | space303-candidate-untracked-file-goes | control_space_standalone.py | fix/candidate-fail-closed, fix2/step-in-progress-exact true | all false | same |
| 10 | space303-candidate-step-in-progress-only-untracked-looked-at | control_space_standalone.py | fix2/step-in-progress-exact true | false | same |
| 11 | space303-candidate-left-files-not-read | control_space_standalone.py | fix2/step-in-progress-exact true | false | same |
| 12 | space303-candidate-trunk-read-from-the-workspace | control_space_standalone.py | fix2/trunk-from-record true | false | same |
| 13 | space303-candidate-workspace-trunk-held-unasked | control_space_standalone.py | fix2/remote-holds-trunk false, fix2/trunk-from-record true | all false | same |
| 14 | the space303-candidate-any-...-is-the-landers case registered after space303-lander-notes-no-commit-of-its-own (the lander's fifth git verb taken for its own) | control_space_standalone.py | fix/candidate-fail-closed true | false | same |
| 15 | space303-candidate-changed-file-goes | control_space_standalone.py | fix/candidate-fail-closed, loss/candidate-commits true | all false | same, and its second row no longer depends on the clock (below) |
| 16 | space303-candidate-ignored-work-goes | control_space_standalone.py | fix/candidate-fail-closed true | false | same |
| 17 | space303-clone-teardown-deletes-without-the-look | control_clone.py | loss/clone-refused-build true | false | re-anchored at what the teardown's own look still decides (below) |
| 18 | space308-pins-released-at-hand-over | control_retirement.py | ac4/pins-held-while-deferred true | false | rejected again, case unchanged: the row reads what the remover was asked (below) |
| 19 | space308-pins-released-while-the-item-is-not-removed | control_retirement.py | ac4/pins-held-while-deferred true | false | same |

Case 15, the clock. Its row loss/candidate-commits holds a workspace with a file in no commit. The workspace's
own commit has the same bytes in every fixture workspace but git's time stamp, so it was already on a kept ref
(put there for the workspace before it) only when git stamped the two in the same second; in any other second
the look refused for the commit and never reached the file, and the mutant survived on that row. Seen: both
target rows false in one run, the second true in five runs in a row, at the same code. The fixture's record now
names that commit as the lander's own (`made`), so the file alone decides: six runs of six rejected. The row is
unchanged on the unchanged copy. This was true before VELDO-0304 too; the case's rejection on 2026-11-14 was
by the clock.

Case 17, re-anchored. The planted defect was both looks of the teardown answered without looking. The work
tree's look cannot be gone without any more: its delete is `remove_standalone`, which makes the look itself and
refused under the old mutant (row true, the draft kept). What the teardown's own look still decides alone is
the rest of the clone, before anything of it goes. The case now answers only the root's look as clear, and row
loss/clone-refused-build gained a clone with a repository beside its work tree: unchanged, the clone stays
whole (work tree, that repository, manifest, pin; space_deferred:in_use) and retires once that repository is
gone; mutated, the work tree is kept and deleted and the pin released while the root stays.

Cases 18 and 19. The retirement can no longer take a pin by asking early: `remove_ref` refuses. Asking early
is still a defect of the retirement, and the suite already reads it that way elsewhere (pin_events in
f4/clone-being-made-keeps-its-pin, which case 19 also turns false). Row ac4/pins-held-while-deferred now reads
it too: through the hand-over, the sweeps and the work tree under its marked name the remover was asked for no
release (`ref_outcomes` of the provisioner is empty). Both mutants ask, and the row is false.

Added, the code that now decides: space308-remover-releases-for-an-item-not-removed (control_space_remove.py,
the `state != 'removed'` test of `remove_ref` deleted), judged by the same row through a new check that asks
the remover itself for the deferred work tree's own item: refused as not_in_ledger, the pin where it was.
Rejected. What the row sees under this mutant is the refusal's name changing to keep_failed: the pin is still
held there by the keep verification that follows the state test, since a deferred item has no verified keep.
A fixture whose item has a verified keep and is not removed would show the pin itself going; that state is
not made by this suite, and the case is recorded with that limit.

Counts: finding 303 stays 44 cases; finding 308 is 39 (38 and the added one); the driver registers 3592.
Static check over every registered case after the change (each mutant applied in memory, every Python one
parsed with ast): 3592 cases, 3474 Python mutants, 0 moved, 0 that do not parse.

Not touched, by ruling: VELDO-0344 ac6/installed (stays red until the owner pins the reader), VELDO-0127
live/claude and live/codex (the lead recaptures), VELDO-0131 browser rows (host load).

For the lead, under the lock: `python3 scripts/check_gate_mutations.py --finding 303`, then `--finding 308`,
then the gate.

## Gate fix 7: the worker deadline of gate 99zzL (head 79d9c29c)

Gate 99zzL ended its mutation stage at 9181 s of a 185654 s stage budget: registered 3597, executed 2620,
rejected 2614, 0 survivors, 0 invalid baselines. The 6 executed and not rejected are one worker killed at its
own deadline and five workers cancelled when the stage stopped on it; 977 cases were never started.

| case | finding | what the gate recorded | after this round |
|---|---|---|---|
| v185-registration-left-out | 185 | worker deadline (120s), killed at 120.2 s with 8.8 s of CPU | rejected, 16.9 s |
| v185-refused-unit-stranded | 185 | worker_cancelled at 110.7 s of 120 | rejected, 21.9 s |
| identity153-finalize-event | 153 | worker_cancelled at 56.9 s of 195 | rejected, 91.1 s of 242 |
| identity153-common-dir-reread | 153 | worker_cancelled at 53.6 s of 195 | rejected, 92.2 s of 242 |
| adoption161-signer-agent | 161 | worker_cancelled at 33.7 s of 121 | rejected, 62.5 s of 165 |
| adoption161-push-before-checks | 161 | worker_cancelled at 33.9 s of 120 | rejected, 62.3 s of 165 |

Disposition: none is a survivor and no case, row or registry entry changed. The four cancelled cases of
findings 153 and 161 needed nothing.

The cause is in suite 106, not in the cases. Its journey waits for the installed service to build and review
three units, with a 90 s failure bound written to stay under the driver's 120 s floor for a case with no
recorded time. Four cases take away what the journey waits for (v185-work-not-installed,
v185-principals-without-role, v185-registration-left-out, v185-refused-unit-stranded), so each waited the whole
bound: 106.9 to 108.4 s at 7aa9ea2a, 104.4 to 107.5 s at c594c6e5, 108.8 s to the kill at 79d9c29c, and 103.4
to 104.5 s alone on this host before the change, with 9 to 13 s of CPU each time. The other sixteen cases of
the finding take 17 to 25 s. A case at 87 to 91 percent of its deadline on every run is killed by any 15 s of
delay; the host gave that once in three gates.

The journey now also ends on the service's own word. The loop passes only when something wakes it and answers
`inspect` in the thread that runs the passes; when it has passed since the submission, watches no run, no
orphan and no tree, has no timer, and says so twice with no pass between, nothing is left that could wake
it, and the rows judge what the store holds. The 90 s bound stays for a service that is busy and slow. No
row's condition changed, and the unchanged suite never takes the new exit (it is printed when taken).

Runs (`nice -n 10 python3 scripts/check_gate_mutations.py --finding N`, no gate):
- finding 185 before the change, the four cases alone: 4 of 4 rejected, 103.4 to 104.5 s each.
- finding 185 after: registered 20, executed 20, rejected 20 in 66.9 s; the four at 16.8, 16.9, 16.9 and
  21.9 s; each fails the same rows as before the change (compared row by row).
- findings 153 and 161: registered 79, executed 79, rejected 79 in 367.5 s; no case past 43 percent of its
  deadline.
- suite 106 alone after the change: 20 rows pass; 76 runs of 76 clean in batches of four and eight at once.
  One run of four, made while the driver ran findings 344 and 259 beside it, failed reservation/principals
  once (authority refused no_account) with every journey row passing and the new exit not taken; not
  reproduced, cause not established, recorded here and not fixed.

Not fixed here, same shape in other suites, for the lead: dispatch-spawn-before-contract (102.2, 102.9 and
104.8 s of 120 in the last three gates, 12 to 14 s of CPU) and dispatch-receiver-store-only-gate (97.8, 98.2,
99.7 s) of suite 62, and owner-command-unrouted (82 s). The driver that sets the 120 s floor is a protected
path and was not touched.

### Gate fix 7, second cause: a row of suite 141 that a raise removed (finding 344, not reached by the gate)

All 52 cases gate 99zzI left unjudged (41 of finding 344, 11 of finding 259) were among the 977 that gate
99zzL never started, so gate fixes 5 and 6 had not been seen by the mutation stage. Run here: findings 344 and
259, registered 52, executed 52, rejected 50, and two refused as missing_target, "baseline rows removed":
space344-probe-executes-the-reader and space344-reader-maps-not-read.

Both mutants make suite 141 raise before the same-program read (the second one does not compile: read_maps
is then unused under -Werror). Row reader/same-program, added on 2026-11-15 (f730283a), was written into the
row table where it is judged and was missing from the list the table starts from, so a run that raised
earlier printed 90 rows where the unchanged suite prints 91, and the driver refuses a mutant that removes a
row. Hidden until now: the baseline of every 344 case was invalid on ac6/installed in gates 99zzF and 99zzI.

The row is now in the list. A run that never reaches it prints it as failed, as it does every other row.
Unchanged suite: 65 passed, as before. Finding 344 after: registered 41, executed 41, rejected 41 in 46.3 s;
both cases 91 rows against 91, each false on its declared row. Finding 259: 11 of 11 rejected (the run above).

### Gate fix 7, third cause: suite 62 waited ten seconds, nine times, for workers that would never start (finding 39)

dispatch-spawn-before-contract and dispatch-receiver-store-only-gate make every dispatch refused. The suite's
wait for a worker's marker had only its 10 s bound, so each of nine waits ran it out for a dispatch whose record
already said refused: regions measured at 20.5, 20.7, 10.2, 20.3, 10.1 and 10.1 s, and the cases at 101.7 and
97.6 s of the 120 s worker deadline (run here before the change, both rejected).

The wait now also ends on the record of the dispatch: a worker is started only under a record that is
prepared, accepted or running, so any other state ends the wait after one more reading of the markers. The
packet wait is skipped when no marker names a worker. No row's condition and no bound changed (17eaba1f).

Finding 39 after: registered 30, executed 30, rejected 30 in 72.9 s; the two cases at 12.6 and 8.3 s with the
same failed rows as before. The slowest case is now dispatch-closed-output-late-deadline at 52.5 s, which is
its own defect (a deadline 30 s late). Unchanged suite: 51 passed in 9.7 s.

### Gate fix 7, fourth cause: suite 106 stopped the service before the last run's account slot was returned

This replaces "cause not established" above. The stray failure of reservation/principals (authority refused
no_account, once in 81 runs) is a race in the suite, not in the product.

A receiver commits its run's exit, then asks the manager for the ended scope's result, and only then tells the
service. The service returns the run's account slot in the loop pass that message wakes, and its loop makes
no pass once it is told to stop. The journey ended on the committed records alone, so the suite could stop
the service between the last review's commit and that pass; the slot then stayed held on codex-a, the only
Codex account, and the probe made after the stop was refused (the pool passes codex-a over as
account_concurrency, which the reservation reports as no_account).

Shown, not inferred: in a scratch copy with that gap widened to 3 s the row fails on every run with the same
message and that one slot held, and no other 0185 row fails; 144 loaded runs without the widening did not
hit it. With the change the same widened run passes the row.

The journey's wait now also needs the store to show no worker slot of the domain still held (4aa6752b). The
90 s bound and the idle exit are unchanged; no row's condition changed.

After: suite alone 46 passed; 96 runs of 96 clean, sixteen at once, load average 30. Finding 185: registered
20, executed 20, rejected 20 in 62.1 s, slowest case 22.8 s, each case's failed rows the same as in the run
recorded above.

Still open, not touched: owner-command-unrouted (suite 71, about 82 s of 120).

### Gate 7 (04113d81): the one case not rejected was an unmeasured baseline, not a surviving mutant

Mutation: registered 3597, executed 3597, rejected 3596. The one case is check_teeth_mutations.py
ui131-decision-action-hidden-360 (finding 131, suite 121_veldo_0131_factory_screens_narrow, row
ac1/screens-360): it adds v-show="!hideAt360" with useMedia('(max-width: 360px)') to the send-answer block of
DecisionDetail.vue, hiding the inline answer on a 360 px phone. The stage ended invalid_baseline: the control
run on the unmutated code failed row ac1/screens-360 in its browser test at http.server server_bind, so the
mutant was never judged. No row misses a defect and the mutant is not equivalent.

Cause, in the e2e harness (engine/ui/e2e/harness.py): free_port() bound port 0, read the number and closed
the socket; the factory was then built (seconds, with its own listeners on port 0) before API.listen bound
that number. Under the gate's load another bind to port 0 could take it in between and the API server's bind
failed EADDRINUSE. Shown: a port released the old way and taken by another socket makes ThreadingHTTPServer
raise [Errno 98] Address already in use.

Change: the harness holds the port's socket bound (SO_REUSEADDR, not listening) from the factory's start until
API.listen has bound it, then closes it. In 20,000 binds to port 0 the held port was handed out 0 times, and
ThreadingHTTPServer (allow_reuse_address) binds the held port. No row's condition changed.

After: suite 121 alone (nice -n 19), unmutated: 2 rows passed. With the case's three edits applied: row
ac1/screens-360 fails ('primary action [data-testid="send-answer"] not visible'), ac1/screens-390 passes;
restored. The standalone driver (--case) could not judge it here: its sandbox has no node_modules and npm ci
crashed ('Exit handler never called'), an invalid_baseline of the local run, not of the gate.

The gate log's "GATE: NOT JUDGED (space unread: pool free space unread)" is output of suite 153's row
safe/unread-free (VELDO-0309), which gives classify an unreadable pool and expects exit 75; the real gate
printed "space: no central installation" and judged RED on the mutation stage alone.
