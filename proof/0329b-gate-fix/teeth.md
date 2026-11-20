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

### Gate 8 (412634ae): one row red, VELDO-0143 activation/name-taken. Cause not found; nothing is fixed

Gate 8 failed one row of the unit stage's unconfined leg, suite 110_veldo_0143_new_project, row
activation/name-taken, on its third part ("its report tells him it could not be set up, and why"). The row
passed in gate 7 (04113d81). This record says what was measured. It does not claim a fix.

Not 412634ae. That commit changed engine/ui/e2e/harness.py and this file. Suite 110 and the fixture it runs
on (proof/VELDO-0152/fixture.py) use neither; their two HTTP stand-ins bind port 0 themselves and keep
listening for the whole suite, so the port the harness now holds is never one of theirs.

What the red is. The part needs both reports of that region (the refused second tidepool and the mussel
decision that found its name taken) to come back `sent`. Every input of the part is decided before the
reports are made, and the row's first two parts, which read those inputs, passed. So one report came back
other than `sent`: its exchange with the fixture's Bot API stand-in failed, or one of its two store writes was
refused. Shown: in a scratch copy where the first report's exchange meets a closed port, the suite fails
exactly this row on exactly this part and passes the other 134, as gate 8 did. The same holds for the only
other red this suite has in the 30 gate logs kept (landing-c 39ddd9e5, provision/adoption-path,
no_settled_decision:not_answered): one presentation or one answer lost.

Not reproduced. Row activation/name-taken, unmutated code:
- suite alone on this host, at ef06ee39: 1 run, then 60 runs twelve at once (load 13 to 15), then 180 runs
  eighteen at once (load 23 to 26): 0 failures of 241.
- pc2, at ef06ee39: 30 runs six at once (load 10 to 14): 0 of 30. (pc2 has no graph runtime; the three PM
  rows are red there for that reason alone.)
- as the gate runs it, one process for the leg: the 35 suites before it and then suite 110, five runs
  (selftest --suite, 1216 rows each), and the whole unconfined unit leg through scripts/gate_legs.py once
  (1131 passed, 0 failed, 1252 s): 0 failures of 6.
- at 2b76ff36: 2 runs alone and 24 runs eight at once: 26 of 26, 135 rows each.

Measured at the row, in the gate-like runs, and found clean: the suite's store connection holds no read
snapshot another connection's commit could make stale (a commit from a second connection followed by BEGIN
IMMEDIATE, at the start of every region and before the reports: accepted every time); 12 to 15 open
descriptors against a limit of 1048576; socket, urllib, http.client, http.server, sqlite3, subprocess and
time are the library's own functions; no signal handler and no timer is set; the main process made no close
call that failed (strace, close calls only); no provisioner process of the pass is running.

Seen, and not shown to matter: threads earlier suites leave behind are alive while suite 110 runs, in some
runs and not others: two from 66_veldo_0042_clones (a TCP listener closed while its thread is in accept;
the thread answers nothing to whatever it accepts) and two from 86_veldo_0189_engine_upgrade (Bridge.serve).

One other row of this suite failed once in the 241 runs, only with twelve copies at once:
service/pm-settled-due ('push_refused:remote', 'not_taken_on:authority_unavailable'). It is a different
part of the suite and was not looked into.

Change (ef06ee39, 2b76ff36), in the suite only, no condition touched: the part's detail now carries each
report made with its outcome and reason, and what the edge raised when a send failed. The scratch run above
prints: ('unknown_outcome', 'unknown_outcome'), EdgeRefused 'no readable platform answer (URLError)' and
the URLError's own cause. The next red of this row names which of the two it was.

Open: the cause. The row can go red again.

### Gate 9 (7f3604f8): five cases voided, no survivor. Cause: a torn reading of /proc/locks in suite 66. Fixed

Gate 9 printed "mutations: failed registered=3597 executed=3597 rejected=3592". No mutant survived. The five
were not judged: all five are init_scaffold.py cases of 66_veldo_0047_authority (target row
authority/installed-assets), and the receipt holds each as invalid_baseline because the one no-op control
they share (66_veldo_0047_authority.py:init_scaffold.py:False:noop, worker 471) failed a row of the
unmutated suite, authority/one-instance-under-the-lock:
authority-service-not-installed, authority-unit-template-not-installed, authority-supervisor-not-installed,
role127-scaffold-omits-role-modules, newproject143-scaffold-not-laid.

Not the three commits since gate 8 (they touch suite 110 and this file), and not a thread left alive: the
mutation stage runs each suite in a process of its own.

Cause. The row asks who holds a flock on the authority's lock file, before and after a second instance is
refused, and read /proc/locks for it. Reproduced through the driver's own worker
(check_teeth_mutations.py --worker authority-service-not-installed, no mutant), 24 at once: 1 run of 48 failed
this row and no other, and the detail the row now carries showed every part right except
holders_during == [('WRITE', pid), ('WRITE', pid)]: the first instance's one exclusive lock, listed twice. Two
exclusive flocks on one file cannot both be held, so the table was misread, not the lock. /proc/locks is
handed out a page per read call and each call resumes by position; a lock taken or dropped by any other
process between two calls shifts the positions. Measured with one lock held throughout: 0 wrong of 129674
readings on a quiet table; with six processes taking and dropping locks, 4093 wrong of 134967 (listed twice
2700, three times 477, not at all 916). The mutation stage runs up to 40 workers at once, each with
services taking locks.

Fix (1b65e546), in the suite only. flock_holders now takes the locks from the fdinfo record of every
descriptor open on the file, in every process: one record, written whole under the file's own lock, naming
the lock in the same words as the table. The row's condition is unchanged: holders_before and
holders_during must still equal [('WRITE', pid)]. Tried first and dropped: accepting what three readings of
the table in a row agree on was still wrong 3 times in 28235. The row's failure now carries what it saw.

Runs, all with no gate holding ~/.local/state/core-gates/.gate.lock:
- the reader alone under the same churn: 4080 answers of 4080 right; an unlocked file reads [].
- the driver's worker, unmutated suite: 96 runs 24 at once with the churn running (load 22), then 128 runs
  16 at once with the churn: 0 failed rows of 224.
- the five cases through scripts/check_gate_mutations.py --case (unconfined leg, as the gate runs them):
  three runs, each "passed registered=5 executed=5 rejected=5".
- loaded, beside 16 copies of the suite and the churn: the five plus the lock row's own two falsifiers
  (authority-two-schedulers, authority-lock-file-replaced): "passed registered=7 executed=7 rejected=7".
- scripts/selftest.py --suite 66_veldo_0047_authority: 56 passed, 0 failed. scripts/check_lint.sh: pass.

Seen and not changed: scripts/gate_host.py (and its engine/ canon) reads /proc/locks once to name the holders
of a gate lock, so the same tear can show it a held lock as unheld or held twice.

### Gate 10 (eece9cf3): 51 cases voided, no survivor. Four causes; three fixed in the suites, one is a defect of the launch and is not fixed here

Gate 10 printed "mutations: failed registered=3597 executed=3597 rejected=3546". No mutant survived. All 51
are in the receipt's invalid_results as invalid_baseline: a control of the unmutated suite failed a row, so
the cases that share the control were not judged. By the row that failed:

| cases | suite | row the control failed | cause |
|---|---|---|---|
| 11 | 127_veldo_0259_installation | VELDO-0259 ac1/fresh-clone, baseline and no-op | the home path this file carried (removed in f37fcca8) |
| 23 | 63_veldo_0040_containment | VELDO-0040 containment/exit-notified (no-op of 22, baseline of 1) | a heartbeat inside the watched window; fixed |
| 16 | 78_veldo_0060_claude_adapter | VELDO-0060 pin/rehash-before-exec, no-op | the launch drops a fast run's artifact report; not fixed here |
| 1 | 120_veldo_0131_factory_ui | VELDO-0131 ac2/refusals, no-op | the test moved the scope under a read still in flight; fixed |

The 11 of suite 127: install259-setup-untraced, install259-builtin-person, writers259-home-kept and the eight
personal259-* cases (red-without-installation, patterns-ignored, uid-shape-dropped, unmasked,
silent-builtin-only, base-guessed, quoted-names-skipped, no-base-silent). Their control ran the personal
setup check on a fresh clone of the candidate and got "1 finding(s) home_path=1", the same finding as the
personal_setup stage; the four controls they share (check_personal_setup.py 8 cases, control_factory_setup.py,
installation.py and qualify.py one each) all failed it, baseline and no-op.
scripts/check_personal_setup.py on a clone of f37fcca8: 0 finding(s).

The 23 of suite 63 (22 on the no-op control of control_containment.py, containment-not-installed on the
baseline control of init_scaffold.py): containment-result-before-settled, -not-found-is-success, -start-activation-lost,
-oom-evidence-lost, -unreadable-result-silent, -launch-outside-group, -shared-group, -unknown-setting-ignored,
-kind-unchecked, -runtime-cap-ignored, -runtime-cap-one-second-late, -memory-cap-ignored, -cpu-cap-ignored,
-file-limit-ignored, -concurrency-uncounted, -required-setting-optional, -zero-seconds-accepted,
-stop-only-parent, -terminate-without-grace, -kill-without-grace, -no-cooperative-step,
-retire-without-looking, -not-installed.

Cause. exit-notified counts the wakes of an idle worker's receiver over a window of at least 1.5 s and
requires none. The window is the time six refused launches take, and the gate recorded 6.86 s and 6.91 s with
6 wakes. The idle worker ran under the main profile, whose wrapper sends a heartbeat every ten seconds, and a
receiver wakes for a heartbeat by right. Reproduced through the driver's worker, unmutated, 80 at once (40 of
this suite beside 40 of suite 78): 80 runs of 80 failed this row, windows of 8 to 15 s, and each failure
carried the heartbeats the receiver itself recorded taking inside the window: one in 78 runs, two in 2.

Fix, in the suite only. The idle worker runs under a profile of its own, the main one with a heartbeat of
120 s (its window 240 s), so its wrapper sends one at the start and none in the worker's 60 s life. The
row's conditions are unchanged, and one is added: the receiver recorded no heartbeat taken inside the
window. A red now carries heartbeats_in_window and heartbeat_seconds.

The 16 of suite 78 (the no-op control of control_launch.py): claude-binding-skipped,
-updater-configured-accepted, -slot-completed-on-exit, -invocation-completed-on-exit, -exit-artifact-unbound,
-artifact-unreturned, -cap-checked-after-launch, -stop-recorded-ended, -stopped-invocation-released,
-wrapper-rehash-skipped, -argv-position-unchecked, -stop-leaves-descendant, -entrance-interpreter-unchecked,
-wrapper-path-unresolved, -wrapper-entrance-unforwarded, -usage-cap-stop-ignored.

Cause. The receipt held the row's name and no words: the suite printed what failed and the mutation stage
keeps a row's words, not the print. With the words added the red was caught 5 times in 1000 loaded runs
(rehash-before-exec 3, rehash-dot-dot 2). The three caught with the full detail were the same: the launch
held no artifact report and its messages ended at "running"; in the two that also carried the receiver, it
had been killed (status -9) and the record showed "exited" 0.03 and 0.10 s after "running". This is the launch, not the row. Launch.start settles from the record when it
reads "running"; when the run has already ended by then (the re-hash refusal ends in a few hundredths of a
second, and a loaded host delays the reader), the record it reads says "exited". Launch.wait reads the
receiver's messages only while the record it holds says "running", so it reads none, stops the receiver at
once and never takes the artifact report and the end the receiver had already written to the pipe. The
receiver is stopped while it may still be between its record and its report (the run-end scan and the space
end are made there). Shown without load: a 0.6 s sleep before that settle, in a scratch copy, makes
pin/rehash-before-exec, pin/rehash-dot-dot, contained/rehash-before-exec and nine more rows red with the
same detail. The row is right to be red, and it stays as it is. Reading the receiver's messages in
Launch.wait while the record says "running" or "exited" turned those rows green again under the same sleep,
in the scratch copy only. .veldo/control_launch.py is not changed here: it is a change of the product's
dispatch path and needs its own specification.

Fixed in the suite, two things beside it:
- every red row of suite 78 now carries its failed checks after the colon; the two re-hash rows carry what the
  receiver reported, the file it names, the receiver's status and log and the record's history; a region
  that raises names the suite line.
- the fake engine wrote its children marker by opening it for writing, and the suite reads that file while
  it waits for the descendant: read empty, a JSONDecodeError that reds every row of the region (contained/*
  ten rows at once, stop/descendant-alive, stop/requested, lifecycle/registration; 8 runs of 1000). Not seen
  in gate 10. The marker is now written whole and renamed, as the engine's own marker is.

The 1 of suite 120: ui131-node-settings-hover-only. In its no-op control (FlowProperties.vue) the browser test
ac2/refusals timed out
on the click of the choice: "element was detached from the DOM, retrying".

Cause. The page reads the inbox twice as it opens, the shell for its badge and then the decisions screen,
and shows the decision from the first answer. The test moved the member's scope as soon as the decision was
visible. Measured on a quiet host: second read sent at 584 ms, decision visible at 623 ms, second read
answered at 625 ms, scope moved at 775 ms. When the API answers the second read after the move, the inbox
no longer lists the decision and the screen takes it away, as it should; the click then waits for an element
that is gone. Shown by holding the second read until the scope had moved: the same error, every time.

Fix, in the test only. The page counts the requests it has sent that the API has not answered, and the test
moves the scope when there is none. Nothing the test asserts is changed. With every inbox read after the
first reaching the API 3 s late, the test waits for it and the refusal is shown beside the action.

Runs, all on a scratch clone, holding ~/.local/state/core-gates/.gate.lock so that no gate ran beside them:
- suite 63 through the driver's worker, unmutated, before the fix: 80 of 80 red on exit-notified (80 at
  once on the host). After it: 0 of 80 (40 at once) and 0 of 200 (80 at once on the host) on exit-notified.
- scripts/check_gate_mutations.py --finding 40 (the 23 and the row's own falsifier containment-exit-polled
  among them): "passed registered=41 executed=41 rejected=41".
- scripts/check_gate_mutations.py --case for the 16 of suite 78 and the 1 of suite 120:
  "passed registered=17 executed=17 rejected=17".
- suite 78 through the driver's worker, unmutated, 70 at once, after the marker fix: 0 failed rows of 400.
- ac2/refusals in a browser: 5 of 5 passed, and passed with the second read 3 s late.
- scripts/selftest.py --suite: 63_veldo_0040_containment 59 passed, 78_veldo_0060_claude_adapter 35 passed,
  120_veldo_0131_factory_ui 14 passed; 0 failed. scripts/check_lint.sh: pass.

Seen and not changed. At twice the gate's load (80 suite processes on 20 cores) suite 63 also failed
containment/cooperative-stop in 5 runs of 280 and containment/runtime-cap in 1 of 280; the first carries no
detail, the second showed a worker that had not started its descendant when its 1.2 s cap ended it. Neither
was red in gate 10 and neither was seen at 40 at once (0 of 80).

### Gate 11 (5430e77a): 45 cases voided, no survivor, and one first-use red. A race of the product, fixed; a browser test whose cause was not reproduced, which now waits on the page and names what it shows; and a third flaky row found while proving, fixed

Gate 11 was red in two stages. integration.confined: the first-use check, family spend_recorded, 9394 passed and
1 failed, VELDO-0313 supervise/wrapper-gone-the-follower-makes-the-end with supervisor_ended False; the untouched
tree passed 9395 of 9395. mutation: registered 3597, executed 3597, rejected 3552. The 45 not rejected are all
invalid_baseline, none is a surviving mutant, and they have two causes:

- 43 cases of finding 313 (the space313 cases of suite 151), on the same row as the first-use red, in the
  control of their suite: supervisor_ended False.
- 2 cases of suite 124, ui131-catalog-first-server-only and ui131-credential-metadata-dropped, on the one
  control run they share: the browser test ac2/priority-save, "toBeVisible getByTestId('backlog') ...
  element(s) not found" after 10000 ms. The gate's summary line names the first of the two.

All teeth findings passed.

**The row of suite 151.** The spend records are not the cause. The first-use check reads a row that is red
with the records and green without them as a row that requires the corpus to be empty; this row is red at
random, and was red once, in the run that happened to carry the records. The row alone (the real
space_supervise with the row's stand-ins), 40 at once beside 20 busy loops, 200 runs each time:

- the untouched tree: 105 failed, then 109 failed.
- the same tree with the two records of the check's "Reproduce by hand" written through .veldo/spend.py: 112
  failed, then 97 failed.
- the tree with the fix below: 0 failed, then 0 failed.

Every failure is the gate's: status 0, the run, the supervisor, made by another process, supervisor_ended
False; the supervisor's state in the table read R. On an idle host the untouched tree failed 4 runs of 40 and
33 of 60, 20 at once. No emptiness arm is made conditional, since no assertion here depends on the records.

Cause. The supervisor's follower slept on the read end of a pipe whose write end the supervisor held, and took
the end of that read for the supervisor's exit. A process that exits has its descriptors closed before its exit
is recorded; between the two the table still shows it as running. A follower woken there makes the end while
the kernel shows the supervisor. In the row the end is a stand-in that records what it saw. In the product it
is _space_finish, which reads the table again, finds the supervisor and makes no end (reason group_not_empty):
the run's items and its hold stay. The row was right to be red; the code was wrong.

Fix, in bin/veldo (engine/bin/veldo and its synced copy). The supervisor opens a pidfd of itself before the
fork; the follower, after the pipe, waits on it. A pidfd is readable once the exit is recorded. On a kernel
with no pidfd the pipe is what is left, as before. This is a change of the product's verb, made here because
the row that guards it was red in the gate; it has no specification of its own.

The row keeps every condition it had. Its stand-ins change in two things:

- the supervisor's descriptors are closed half a second before it exits, as the kernel closes them at every
  exit, only earlier, so the race is not left to the host. With that, the untouched code failed 200 runs of
  200 under the same load, and the fixed code 0 of 200. Falsifier added:
  space313-follower-takes-the-closed-pipe-for-the-exit (the wait on the pidfd removed).
- "ended" is what the product's own reader takes for it: no entry, Z, or X. X is the state of a process its
  parent is reaping, and the follower now wakes at the exit, which is when the suite reaps the supervisor. A
  process read through its pidfd beside a reaping parent read X in 2 of 20000 reads. With the stand-in that
  took only Z, the fixed code failed 0 runs of 2000 under load: this was not seen to redden the row, and is
  changed because the reading is wrong.

**The browser test of suite 124.** The cause was not reproduced. What was measured:

- It is not a page that is slow on a loaded host. With 6 browsers at once beside 30 busy loops the backlog was
  shown 0.57 s after the page was opened at the median and 1.8 s at the worst of 198 opens, against the ten
  seconds the test gave it.
- In the gate the failing control took 99.7 s against 81.4 s for the control that ran beside it, with the
  same processor time (54.7 s and 51.3 s): ten seconds of waiting and a restarted worker, not a slow run. The
  log of another branch's gate (landing-c, gate 16) has the same failure, again on a control of suite 124,
  where the other controls took 42 s: 56.2 s against 43.3 s.
- It did not come back in 244 runs of the suite's eight browser rows under processor load (up to 150 busy
  loops), 32 under a disk storm (twelve loops copying, flushing and removing a tree; I/O pressure 25
  percent), 150 opens of the backlog one after another in one browser, 63 runs of the suite through the
  mutation driver (its nine cases, three times) and 116 runs of the browser suites together (24 cases,
  twice, on the changed test).

So the page was without the backlog for ten seconds for a reason the failure did not give: it said
"element(s) not found" and nothing of what the page showed. Two things are changed in the test
(engine/ui/e2e/factory.spec.ts), and nothing in what it asserts:

- It waits on what the page itself says. The backlog screen's panel is "loading" until its read is answered,
  then ready, empty or error. The test waits for the panel to leave "loading", or the page to leave the
  backlog, for as long as the read takes (120 s at most, inside the test's 180), and then judges what is
  shown with the usual ten seconds. Shown by holding each answer of the work read 12 s: the old wait fails
  with the gate's own error, the panel "loading"; the new one passes. A read that fails is red as before
  (the work read reset: red, panel "error", unavailable:network).
- A backlog that is not shown says which of the test's three opens it was, where the page was, each panel's
  state and words, what the page logged, and every request with its answer or its failure, in order.

This covers an answer that comes late, which is what the failure looks like from the test, and it makes any
other cause name itself the next time. It is not a claim that a late answer is what happened in gate 11.

**A third row, not red in gate 11.** scripts/check_gate_mutations.py --finding 313 (44 cases: 16 runs of
suite 151 at once) was refused invalid_baseline in three runs of four while the fix above was being proved.
Two of the three kept their detail: supervise/stop-after-the-command-ends-nothing, in one control; the first
was run without keeping it. proof/VELDO-0315/README.md has the same row red in a control, cause not found.

Cause, in the suite's fixture. The command that "leaves a process" forks twice and ends at the first fork. The
process between the two lives for an instant, and on a loaded host the supervisor's read at the command's exit
listed it beside the one that stays: two descendants, started one tick apart. The row asks a second and a half
later whether what was listed is still there, and the one between was gone. First the row was given its words
(whether the supervisor stayed, whether what was left is there, its last line, how long the wrapper took):
the wrapper had returned in 0.1 s, so the fixture's ten-second limit was not it. Then shown: with the process
between made to live 0.4 s, the row is red in both controls with the same words.

Fix, in the fixture only: the command collects the process between before it ends, so what it leaves is one
process whenever it is read. With the 0.4 s still in place the row is green and its falsifier
(space313-stop-after-the-command-ends-the-supervisor) is rejected. The row's conditions are unchanged.

Runs, holding the gate lock so that no gate ran beside them, except where said:

- on ae49d608 (the last change to code or tests): the row of suite 151 alone, 40 at once beside 20 busy
  loops, 0 failed of 200. --finding 313 beside 20 busy loops, six times: "passed registered=44 executed=44
  rejected=44" each time (the new falsifier and space313-wrapper-gone-nobody-makes-the-end among them).
  --case ui131-catalog-first-server-only --case ui131-credential-metadata-dropped: "passed registered=2
  executed=2 rejected=2".
- on f30acbe3 (the browser test as it is now): ac2/priority-save alone, 6 at once beside 30 busy loops, 0
  failed of 204; with the suite's other seven rows, 0 failed of 60; the 24 cases of the browser suites,
  twice: "passed registered=24 executed=24 rejected=24".
- without the lock, one case at a time: the two demonstrations of the third row.
- scripts/check_lint.sh: pass. vue-tsc on engine/ui with the changed test: no error.
  scripts/check_template_sync.sh: pass (325 pairs). scripts/check_space_boundary.py: pass.
  scripts/check_personal_setup.py: 0 findings. Every registered case of bin/veldo (57) finds its anchor once.
- scripts/selftest.py --suite 151_veldo_0313_space_run outside the gate's confinement is red here on the
  untouched tree too (7 rows, processes of other accounts read as holders), so suite 151 was run through the
  mutation driver, which confines its workers: its controls are the suite, unmutated.

Not done. scripts/verify.sh was not run. The new case has no measured time in .veldo/gate-schedule.json; the
authority measures it.
