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
