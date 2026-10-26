# VELDO-0161 round 4: the review of rounds 2 and 3 (R1 to R4, one weakness) and the setup161 host result

Branch agent/claude/agent/claude/veldo-0161, from 0511a31a. Review: proof/VELDO-0161/REVIEW-claude-2026-10-23.md
(d9f06df4, added unchanged in e4d45551). Code at 39772b77, rows and mutations at a3b1904d. Nothing here is a
gate result, a review verdict or an approval. This sandbox refuses AF_UNIX sockets and has no user manager, so
the parts named below are the host's.

| Finding | Fix | Row | Falsifier(s), result here |
| --- | --- | --- | --- |
| R1, a lost hand-off waits for a restart | control_service.serve reads the records once more right after CC.bind (no periodic check; a hand-off after the bind waits in the backlog). The effect's take_on never raises: a refusal keeps its code (ssh-keygen's timeout or OSError is unavailable_service:journal_key), a timeout is not_taken_on:timeout (also when control_client wrapped it as authority_unavailable), no socket is not_taken_on:authority_unavailable, anything else not_taken_on:unknown_outcome:<type> | adoption/taken-on-while-starting (the installed serve() under a wrapper held on a FIFO after its first read of the records; the row adopts in that window, the hand-off finds no socket, and the same instance serves it once ready; here the bind is a stand-in, on the host the real socket); adoption/take-on-faults-named | take-on-after-bind-missing, take-on-timeout-unavailable, take-on-fault-raised, take-on-refusal-unnamed: killed |
| R2, the prepare fetch runs core.alternateRefsCommand | The repository's configuration is judged against LOCAL_CONFIGURATION, an allowlist of keys local steps read as data; every other key is invalid_input:repository_command:<key>. objects/info/alternates is invalid_input:repository_alternates, at prepare, in the effect's checks and before the merge | adoption/repository-commands: core.alternateRefsCommand alone, the reviewer's scenario (alternates and the command), a repository that came to borrow objects after prepare | configuration-denylist, alternates-unchecked: killed. probe-alternates.json: the reviewer's scenario through each provisioner's own refuse_commands and fetch: at 0511a31a nothing refused and the command ran; at 39772b77 refused by name and it did not run |
| R3, store-decided refusals after the push | Before the branch moves: configure_identities check_only, the store's binding of the id against the path, the configured generation against store_generation, each with the code its later step would give | adoption/store-checks-before-push (the path already another id's identity binding; the store binding the id elsewhere; the store's journal at generation 2): refused by name, record failed, branch and remote unmoved, ref removed | identity-after-push, store-binding-after-push, generation-after-push: killed |
| R4, an interrupted run stays provisioning | Each run holds a per-repository flock beside the store (lock_path), released by the kernel however the process ends. A run that finds its request's record provisioning without enrollment and takes the lock writes it failed, unknown_outcome:interrupted, at the step the record names, and removes the scaffold ref; while the lock is held it refuses stale_subject:adoption_in_progress, touching nothing. The scaffold step is recorded before the branch moves | adoption/interrupted (record written as a run killed during the push leaves it; lock held, then released, then a third run) | interrupted-left-provisioning, live-run-unheld: killed |
| Weakness: signer-no-agent not exact | The stand-in ssh-keygen records -f and -n; the row requires as many -Y sign of the adoption key in veldo-enrollment as journaled signatures (the fixture row take-on-refusals plants is excluded by name) | adoption/signer-no-agent | signature-unwatched (adoption signatures made outside AdoptionSigner.sign, so outside the watch): killed |

`falsifiers.json`: every finding-161 adoption case (49) through the driver's worker mode, in 7 shards; each
target row red, worker exit 0, 77 rows. adoption161-restart-take-on's row (same-process) is red at baseline
here, so it is the host's. Each shard's baseline before and after is the same four AC2 rows (AF_UNIX). Other
rows a broad mutant also reddens are listed per case (other_new_failures); none is a missed kill. One existing
anchor moved: push-before-checks' second edit now includes the recorded scaffold step.
Finding 161 now registers 52 cases: 37 adoption cases before this round, 12 added here (commit a3b1904d's
message says thirteen; it is twelve), and the 3 setup161 cases.

## The setup161 cases (item 6)

The three setup161 cases run suite 73, whose baseline inside the confined mutation domain fails 16 rows with
unavailable_service:profile:user_manager. The gate does not run them there: scripts/gate_unconfined.json names
73_veldo_0139_factory_setup (and 106_veldo_0185_dispatch_setup) whole, and check_gate_mutations.py, the
stage verify.sh runs, puts every case of a listed suite in its unconfined leg (in_leg), as it does finding
139's suite 73 cases. `scripts/check_teeth_mutations.py --finding 161` passes no leg, so there every case is
confined: that is the invalid_baseline the host saw, the same for finding 139. Nothing in the driver changes.
`drive_setup.py` follows proof/VELDO-0185/drive.py: the teeth worker as an ordinary process, baseline then
each case; exit 0 only when the baseline is green and each case reddens setup/lays-down with no row lost.
Here (drive-setup-sandbox.json) the baseline itself is red for want of the user manager, so nothing is
judged killed here.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`: every row green.
2. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: every row green (77), the AC2 rows and
   taken-on-while-starting with the real socket, signer-no-agent with its recording socket, no HermeticViolation.
3. `python3 scripts/check_gate_mutations.py --finding 161`: the gate's own stage with its unconfined leg; 52
   cases killed, the three setup161 cases in the unconfined leg.
   (`python3 scripts/check_teeth_mutations.py --finding 161` still confines every case: 49 killed and the three
   setup161 cases invalid_baseline, as finding 139's.)
4. `python3 proof/VELDO-0161/round4/drive_setup.py proof/VELDO-0161/round4/drive-setup-host.json`: exit 0,
   "setup161: all killed".
5. `./scripts/verify.sh`: green.
