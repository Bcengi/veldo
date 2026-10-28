# VELDO-0143 rebased onto VELDO-0161 round 5

Before: agent/claude/veldo-0143 at 649df4d5, five commits on VELDO-0161 round 1 (da39f3fb).
After: the same five commits replayed onto 8f749423 (VELDO-0161 round 5, reviewed sound), then one commit adapting
0143 to 0161's final design, then this evidence. Only agent/claude/veldo-0143 was rewritten.

| Old | New | Commit |
| --- | --- | --- |
| cf1e81b9 | f993e8d7 | a new project from chat, created or adopted and activated on the owner's one answer (conflicts, below) |
| 87b0c00a | 4689067d | footprint and history; finding 143's mutations; suite 106 (applied cleanly) |
| f96e1407 | bc81c1b8 | the owner told by a VELDO-0128 report (applied cleanly) |
| bf6c3911 | dfeb0eca | the provisioner configuration setup lays in the state root (applied cleanly) |
| 649df4d5 | e2fe2e8e | proof bundle of round 1 (applied cleanly; superseded by this directory and the updated README and manifest) |
| (new) | d859b3db | the adaptation to VELDO-0161 round 5 (Adaptations, below) |

The four replayed code commits keep their round-1 content apart from the conflict resolutions below. f993e8d7 to
dfeb0eca do not run on their own: their provisioner still calls the round-1 `Context` and `enroll` of the adoption
effect, which the resolution drops. d859b3db is the first commit on the new base where the creation path runs.
Making each intermediate commit runnable would have meant rewriting them; the adaptation is kept as one commit so
the reviewer sees exactly what the rebase changed.

## Textual conflicts (all in cf1e81b9) and their resolutions

1. **`control_effect_executor_adoption.py` (engine and .veldo).** Round 1 of 0143 refactored the adoption effect's
   tail (identity, signature, binding, the record's wait for the service) into a `Context` class and a shared
   `enroll()` so the creation path could reuse it. Rounds 2 to 5 of 0161 rewrote the same function: the checks
   that change nothing before the push, the INTERRUPTED lock, the record failed for every fault, the signer pinned
   to store, host and generation, and the synchronous take-on over the socket in place of `_await`. **Resolution:
   0161's file is taken whole, byte-identical to 8f749423; the refactoring is dropped.** The creation path's end is
   rebuilt in the provisioner (Adaptations 1). This keeps every one of finding 161's 55 anchors and every round 2
   to 5 behavior exactly as reviewed, and leaves 0143 nothing in the adoption effect to review.
2. **`control_repository.py` (engine and .veldo).** Both sides extended the error taxonomy: 0161 added
   `push_unconfirmed`, 0143 added `directory_not_empty`, `remote_exists`, `token_unavailable` and
   `creation_refused`. **Resolution: the union, 0161's order first.** The rest of 0143's changes (origin
   `created`, `NEW_PROJECT_PREFIX` routed to control_project_proposal's judge, the `created` metric) merged
   cleanly beside 0161's `_REPOSITORY`, `TAKE_ON_*` and `store_generation`.
3. **`control_service.py` (engine and .veldo).** 0161 replaced the instance's `token` with `instance_id` and the
   journal-watermark poll state (`adoption_mark`, `adoption_retry`) with `installed_receivers`, `adoption_faults`
   and `journal_public`; 0143 had added `projects_pass` beside the old fields. **Resolution: 0161's fields, plus
   0143's `projects_pass`.** 0143 never read `token`, `adoption_mark` or `adoption_retry`, so nothing else needed a
   rename. The serve loop merged without a conflict but put 0143's `new_project_pass()` on every loop iteration,
   which is the poll 0161 removed (Adaptations 3).
4. **`scripts/suites/manifest.json`.** 0161 rewrote suite 109's regions and note; 0143 added suite 110's entry
   after it. **Resolution: 0161's 109 entry and 0143's 110 entry.**

The pseudo-refs a rebase deletes (CHERRY_PICK_HEAD, AUTO_MERGE, REBASE_HEAD) could not be removed by git here (the
sandbox refuses `packed-refs.lock` in the shared git directory), so they were removed from this worktree's own git
directory by hand once the rebase had updated the branch.

## What 0143 relied on that 0161 removed or renamed, and how 0143 now uses the new design

1. **The adoption effect's `wait`, `_await` and the record waiting `provisioning` for a polling service.**
   0143's `provision(wait=...)` passed `wait` to `adopt()`, and its creation tail called `Context.enrolled(...,
   wait)`, which polled the record. **Now:** `provision(config, decision, *, clock, signer, client, send)` has no
   wait. The adopt-mode path calls `AD.adopt(..., send=send)` as is. The creation path writes the record
   `enrolled` and hands it over with the adoption effect's own `take_on(config, proposal, request, trust, send)`:
   the service judges it and answers synchronously, and the result is that answer (reason None once active;
   `not_taken_on:authority_unavailable` and still `provisioning` with no service; `not_taken_on:<why>` and `failed`
   when the service refuses). `main()` exits 0 only when the record is active, as 0161's adopt `main()` does.
2. **The shared `enroll(context, ...)` and `Context.failed`.** **Now** in the provisioner: `preflight()`, the
   adoption's store and host checks for a repository not yet made, and `enroll()`, the identity, signature, verify
   and binding steps, with the adoption signer's ids pinned (`host_identity`, `authority_generation`), which 0161's
   signer now requires. Every fault, not only the named refusal classes, ends the record `failed` with a named
   code (0161 B3): a creation step's own refusal keeps its code, anything else is the adoption effect's naming
   (`_code`).
3. **The journal-watermark poll.** The round-1 serve loop ran `take_on()` and then `new_project_pass()` on every
   iteration; the pass returned early when the watermark had not moved, and the provisioner's process was polled
   with `poll()`. 0161 removed the take-on poll. **Now** the service keeps `projects_due`, set at the start, by
   `hint_after` when a packet or channel pass advanced the journal (which covers the take-on the instance answered
   and every owner answer), and by the end of a provisioner's output pipe. The pipe sits in the serve loop's
   existing `select` beside the launch pipes (`provisioner_pipes`, `provisioner_readable`). The loop runs the pass
   only when it is due, the pass wakes the factory loop when it wrote, and `NewProjectPass` keeps no watermark. A
   provisioner's answer is read from its pipe, not from a file.
4. **`token` is now `instance_id`.** 0143's code never read the token. Suite 110's rows now name
   `taken_on.instance_id`.
5. **The adoption_mark timing (take-on at start and after each journal advance).** 0143's `service/provisions` row
   looped `service.take_on()` while the provisioner ran. **Now** the row runs the serve loop's own shape (the socket
   and the provisioner's pipe in one `select`, a pass only when due) and never calls `take_on()` while the
   provisioner runs. Where AF_UNIX is refused, the provisioner's hand-off finds no service, the record waits
   `provisioning` named `not_taken_on:authority_unavailable`, and `take_on()` is called once as an instance's start,
   0161's path for exactly that case.

## Adaptations beyond the renames (each in d859b3db, each with a row and a mutation)

1. **Checks before anything is made** (0161 round 2 B1 and round 4 R3, applied to creation): the host trust and
   the adoption signer's enrollment, the identity binding (check only), the store's binding and the generation are
   judged before the directory step. Row `provision/checks-before-creation`; mutation
   `newproject143-checks-after-creation`.
2. **The created repository's configuration judged before GitHub is asked** (0161 round 4 R2 and round 5 N2):
   `refuse_commands` and `refuse_transport_config` run before the remote step, so no GitHub repository is created
   for a push that would be refused. Row `provision/checks-before-creation`; mutation
   `newproject143-configuration-unchecked-before-remote`. Round 2 B4 and round 5 N1 (fsmonitor, push.followTags)
   need no change here: the creation steps run under git_process's isolated profile (global and system
   configuration nulled) on a repository whose only local keys are the ones the provisioner wrote.
3. **INTERRUPTED and the lock** (0161 round 4 R4, applied to creation): rows `provision/interrupted`; mutations
   `newproject143-interrupted-left-provisioning`, `newproject143-live-run-unheld`. The service starts the
   provisioner once more, once per instance, for a record left `provisioning` with no binding, and never again for
   one its own provisioner left so (no respawn loop while another run holds the lock).
4. **The synchronous hand-off for a created repository**: row `provision/handed-over` (in process, through
   control_client's Authority judging the request, as suite 109's in-process rows do); row `service/hand-off`
   (the service-started provisioner over a real socket the suite's loop serves; red by name where AF_UNIX is
   refused). Mutations `newproject143-take-on-not-sent`, `newproject143-take-on-not-due`,
   `newproject143-provisioner-end-unseen`.

Also fixed while adapting the suite: suite 110's `fenced()` called itself instead of `wire.active()` where AF_UNIX
is allowed, so on the host every fenced row would have raised RecursionError. This sandbox refuses AF_UNIX, so
round 1 never reached that branch.

## Known limit introduced by the event-driven pass

A provisioner started by an earlier instance of the service (it runs in its own session and outlives a restart)
that later writes its record `failed` does not wake the new instance, which did not start it and has no pipe for
it. The decision is failed, and the owner told, at the new instance's next pass, which is due after any journal
advance by a packet or channel pass. A provisioner of the same instance, and every success (the hand-off is a
packet), wakes the pass at once.

## Results (this sandbox: AF_UNIX refused, no systemd user manager, no installed graph runtime)

- Suite 110 (`rebase/observations.json`, on d859b3db): 47 rows passed, 2 red by name: `service/hand-off` (AF_UNIX
  refused) and `pm/new-project-run` (`runtime_unavailable`). Every other row green, the four new ones included.
- Finding 143 (`rebase/falsifiers.json`, through the driver's worker mode, as round 1): 16 of 16 cases killed, the
  nine of round 1 and the seven above; baseline before and after red only on the two host rows.
- Suite 109 (`rebase/suite-109.json`): on this branch and on an archive of 8f749423 in the same sandbox, 49
  passed and the same four AF_UNIX rows red on both (`adoption/taken-on-running`, `adoption/same-process`,
  `adoption/packet-accepted`, `adoption/not-taken-on-named`). The adoption effect, the provisioner module and suite
  109 are byte-identical to 8f749423.
- Finding 161 (`rebase/falsifiers-161.json`, proof/VELDO-0161/run_falsifiers.py on this branch): all 55 cases
  run; 54 are killed by a target row green at baseline. `adoption161-restart-take-on` targets only
  `adoption/same-process`, red at baseline here (AF_UNIX), so it is the host's to judge (host run 4). Baseline
  before and after: the same four AF_UNIX rows red, as on 8f749423.
- Consumer suites (`rebase/consumer-suites.json`), this branch against an archive of 8f749423, one after the
  other in the same sandbox: 31 suites, each with the same count and the same failing rows on both trees. Green
  on both: 108, 26, 46, 66, 68 (both), 69 (both), 72 (both), 73_0078, 73_0089, 75, 76, 77, 82, 84, 86_0168,
  91_0151. Red identically on both (user manager, worker launches, graph runtime): 106, 71_0076, 73_0139, 83, 85,
  86_0189, 91_0167, 92, 93, 94, 96. 71_0130 prints no summary on either tree (install refused).
- Static: lint, template sync, generated, docs, `validate.py all` and the shape gate pass.

## Host runs (required before review)

1. `bash scripts/verify.sh`: the full gate, both legs and the mutation stage.
2. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green, `service/hand-off` (AF_UNIX:
   the service-started provisioner's take-on answered over a real socket) and `pm/new-project-run` (the host's
   LangGraph runtime) included. This is also the first run of the fixed `fenced()` with its recording SSH agent.
3. `python3 scripts/check_teeth_mutations.py --finding 143`: 16 of 16 killed, including
   `newproject143-provisioner-end-unseen` against `service/provisions` and the AF_UNIX side of `service/hand-off`.
4. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption` and `python3 scripts/check_teeth_mutations.py
   --finding 161`: the host results 0161 round 5 reported (suite 109 81/0, 55/55 killed) must be unchanged.
5. The AF_UNIX and user-manager suites the service change touches: 66_veldo_0047_authority,
   83_veldo_0154_factory_loop, 71_veldo_0076_projects, 71_veldo_0130_api, 73_veldo_0139_factory_setup,
   106_veldo_0185_dispatch_setup, 85_veldo_0171_setup_api, 91_veldo_0167_setup_records,
   86_veldo_0189_engine_upgrade, 92_veldo_0088_pm_cycles, 93_veldo_0152_intake_routes,
   94_veldo_0162_configuration_routes, 96_veldo_0204_reservation_policies.
6. The live qualification of round 1, still not run anywhere: a real GitHub token per identity creating a real
   repository, handed to the installed service over its socket, and the new project's first unit built end to end.
