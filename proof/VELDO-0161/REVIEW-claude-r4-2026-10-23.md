VERDICT: HAS DEFECTS (N1 low, N2 low)

# VELDO-0161 round 4: independent review

Reviewer: Claude, a fresh context that wrote none of this code. Range 0511a31a..d65e573e, worktree at d65e573e.
Read: the specification's round 4 history, proof/VELDO-0161/round4 (README.md, falsifiers.json, drive_setup.py,
probe_alternates.py and their outputs), the diffs of control_effect_executor_adoption.py,
control_repository_provisioner.py and control_service.py (engine/.veldo and .veldo are byte-identical; there
are no pack copies; check_template_sync.sh exits 0), the new rows of suite 109 and the twelve new finding-161
mutations in scripts/check_teeth_mutations.py, and, for context, control_client.send and bind,
control_git_identity_transport and git_process. This review is not an approval.

All four findings of the previous review and its one weakness are fixed, each with a row that a mutation of the
fix turns red here. Two new defects of low severity remain, both in what the new allowlist lets through to the
push.

## Findings

### N1 (low): the scaffold push also sends the repository's annotated tags when its configuration asks

Files: engine/.veldo/control_repository_provisioner.py:118 (LOCAL_CONFIGURATION allows push.followtags as
data) and :318 (the push names neither the no-follow-tags flag nor push.followTags=false).

The specification says the push sends exactly the scaffold commit the owner answered. The repository's own
configuration stays authoritative under the identity profile (git_process.py line 3), and the profile adds only
credential and transport options. The VELDO-0153 effect push, control_effect_executor.py:211-212, sets
push.followTags=false and passes the no-follow-tags flag for this reason, and checked_argv in the identity
transport already accepts both. The adoption push sets neither, and round 4's allowlist now names followtags
as a key that is safe to accept.

Concrete scenario, reproduced here with git 2.43.0: the repository's own .git/config has push.followTags=true,
and an annotated tag `private-tag` on the base exists only locally. repository_commands() returns [] and
alternates() returns False, so prepare and every check pass. The push the provisioner makes (porcelain, URL,
`<commit>:refs/heads/main`) also creates `private-tag` on the remote. The owner approved one commit, but a
tag he never saw is now published under the identity.

Fix: pass `-c push.followTags=false` and the no-follow-tags flag in push(), as the effect executor does, or
remove followtags from the allowlist. Add a case to adoption/repository-commands (an annotated local tag, the
key set, the remote's tags unchanged after adoption) with a mutation that drops the flag.

### N2 (low): a key in the remote section named by the URL passes the allowlist, then the push refuses it after the branch has moved

Files: engine/.veldo/control_repository_provisioner.py:114 (the `remote` section allows push, fetch, mirror,
tagopt and more, under any subsection) with engine/.veldo/control_git_identity_transport.py:137
(config_overrides refuses every key of the section named by the literal URL except a url or pushurl equal to
it) and engine/.veldo/control_effect_executor_adoption.py:314 (advance runs before push).

The two judges of the same configuration disagree. The effect's checks (refuse_commands) accept
`remote.<url>.push`, but the identity profile refuses it at the push with
binding_mismatch:identity_transport_config. That is the same class as B1 and R3: a refusal that is knowable
before anything moves, made only after the move.

Concrete scenario, reproduced here through both modules' own functions: the repository's configuration has
`remote.https://github.com/owner/r.git.push = refs/heads/main:refs/heads/other`, with the proposal's remote
set to that URL. repository_commands() returns [], while config_overrides() on the same `git config` listing
returns True. At adoption, P.advance fast-forwards the checked-out default branch, then P.push is refused. The
record ends `failed` and the ref is removed, but the owner's working branch now sits on the scaffold commit.

Fix: in the effect's checks (and at prepare), run the identity transport's config_overrides over the
repository's configuration for proposal['remote'] and refuse by the same code before advance. Alternatively,
allow in the `remote` section, for the subsection equal to the URL, only url and pushurl equal to it. Add a row
case and a mutation.

## 1. The findings of the previous review

| Finding | Judgment |
| --- | --- |
| R1, a lost hand-off waits for a restart | Fixed. serve() calls service.take_on() once more immediately after CC.bind (control_service.py:2547), before READY. CC.bind calls listen before it returns, so any connect after that waits in the backlog (16) and is answered. A connect before it fails (ENOENT, or ECONNREFUSED between unlink, bind and listen), and the record it wrote is already committed, so the read after the bind sees it. No record falls between the two reads. No polling and no periodic check was added. The only other take_on call is the existing fault timer (adoption_due), which this round does not change. The effect's take_on now names every fault: R.Refused keeps its code, ssh-keygen's OSError or TimeoutExpired is unavailable_service:journal_key, a RoutingRefused whose cause or context is TimeoutError is not_taken_on:timeout (control_client raises inside its `except OSError` without `from`, so __context__ carries the socket.timeout), and anything else is not_taken_on:unknown_outcome:<type>. Row adoption/taken-on-while-starting runs the installed serve() under a wrapper that blocks on a FIFO after its first read. The adoption made in that window gets authority_unavailable, and the same instance (same instance_id and pid) serves the repository once it is ready. Here the bind is a stand-in; the host uses the real socket. |
| R2, alternateRefsCommand in the prepare fetch | Fixed as a class. The configuration (local, worktree and included scopes; command-line values skipped; global and system are not read under the isolated profile) is checked against an allowlist by section and name, and anything else is refused by name. That covers filters, fsmonitor, alternateRefsCommand, the editor, pager, ssh command, askpass, credential, url.*, include and includeIf, gpg.program, diff and merge drivers, uploadpack, receivepack and vcs, submodule, gc and maintenance. objects/info/alternates, looked up through rev-parse git-path in the common directory, is refused separately as invalid_input:repository_alternates, at prepare, in the effect's checks and before the merge. The prepare clone and the clone's commit read only the clone's fresh configuration. I found no allowlisted key that makes a local step run a command. Two allowlisted keys change what the push does (N1, N2). The allowlist also refuses common harmless keys (submodule.*, maintenance.*, gc.*, lfs.*); that is conservative and named, not a defect. probe_alternates.py re-run here at 0511a31a, 39772b77 and d65e573e: the command ran at 0511a31a and was refused by name, without running, at the other two. |
| R3, store-decided refusals after the push | Fixed. Before the scaffold step: configure_identities with check_only and the same arguments as the later call, S.bound_repository compared with realpath(path) (bind_repositories compares the same way), and generation compared with store_generation (the signer's own `<`). Each uses the code its later step would give. Row adoption/store-checks-before-push: three repositories, each refused by name, with branch, remote and ref unmoved. |
| R4, interrupted run left provisioning | Fixed, and decided by the kernel, not by a timer. hold() takes flock with LOCK_EX and LOCK_NB on a per-repository file beside the store. The descriptor is O_CLOEXEC, so no git child inherits it. The lock is taken before the record is read and held until the finally block, through the hand-off. A second run at the same time gets EWOULDBLOCK and refuses stale_subject:adoption_in_progress without touching anything. Locks belong to the open file description, so two runs cannot both hold it, and the kernel releases it however the process ends. A run that gets the lock and finds its own request's record `provisioning` without enrollment writes it failed with unknown_outcome:interrupted at the recorded step, and removes the scaffold ref. The scaffold step is now written before advance. The service never takes on such a record, so the two do not race. Row adoption/interrupted holds the lock from another descriptor in the row's own process, then releases it. Residuals: nothing re-runs the effect by itself after a reboot, which is what the previous review asked for; and a git push orphaned by a killed run can still finish after the record is marked failed, which "the commit may be on the remote" covers. |
| Weakness, signer-no-agent | Fixed. The stand-in records -f and -n. The row requires the number of `-Y sign` calls with the adoption key in veldo-enrollment to equal the journaled signatures (the planted tk-signer fixture excluded by name), and at least two. adoption161-signature-unwatched (signing outside AdoptionSigner.sign) turns it red here. |

## 2. The setup161 driver and the gate

drive_setup.py follows proof/VELDO-0185/drive.py. It loads the teeth driver, runs its worker as an ordinary
process for the baseline, then once per case on a materialized copy (the source is never edited). A case is
judged killed only when setup/lays-down passed at baseline and is false under the mutant, no baseline-passing
row is lost, and the worker exits 0. all_killed also requires a baseline with no failing rows. Neither
scripts/check_gate_mutations.py nor scripts/gate_unconfined.json is in the range; the stage is not changed or
weakened. gate_unconfined.json names 73_veldo_0139_factory_setup whole, and in_leg() puts every case of that
suite, the three setup161 cases included, in the unconfined leg, as it does finding 139's. So the README's
account of the invalid_baseline the host saw under check_teeth_mutations.py for finding 161 holds. Whether the
three cases are killed I could not judge here: suite 73's baseline is red for want of the user manager
(below). That is the host's to show (README host runs 3 and 4). A small difference from run_falsifiers.py:
drive_setup does not re-run the baseline after the cases.

## 3. Other observations in the range (not defects)

- The take-on-faults-named region defines a helper `wrapped` that it never uses.
- A hand-off whose connect times out because the backlog is full is reported not_taken_on:timeout and waits for
  the next start. Under the no-polling rule this is the accepted residual, and it is now named.
- check_teeth_mutations.py: one existing anchor (push-before-checks' second edit) was moved to the new
  scaffold-step write. The case is still killed (round4/falsifiers.json).

## 4. What I ran here (the sandbox refuses AF_UNIX sockets and has no user manager)

- selftest.py, suite 109_veldo_0161_adoption: 73 passed, 4 failed, exit 1. The failures are exactly the four
  AC2 rows (taken-on-running, same-process, packet-accepted, not-taken-on-named), each "AF_UNIX sockets are
  refused on this host". taken-on-while-starting (stand-in bind), take-on-faults-named, repository-commands,
  store-checks-before-push, interrupted and signer-no-agent passed, with no HermeticViolation.
- proof/VELDO-0161/run_falsifiers.py on the twelve round-4 cases: each target row is red, each worker exits 0
  with 77 rows, and no other row is newly failed. take-on-fault-raised also reddens its own ran/ row, because
  the region raises. The baseline before and after is the same four AC2 rows. Exit 0.
- probe_alternates.py at 0511a31a, 39772b77 and d65e573e: exit 0, results as in section 1.
- A probe of my own, outside the tree, for N1 and N2 (plain git with the push's arguments to a local bare
  repository, plus the provisioner's repository_commands and alternates and the transport's config_overrides):
  both reproduced as described.
- selftest.py, suite 73_veldo_0139_factory_setup: 27 passed, 16 failed, all
  unavailable_service:profile:user_manager (setup/lays-down among them). Exit 1.
- drive_setup.py: exit 1. The baseline has the same 16 failing rows, so no case is judged killed:
  "setup161: NOT all killed". That is expected here and says nothing about the host.
- selftest.py, 66_veldo_0047_authority: 27 passed, 0 failed, exit 2. 46_veldo_0029_enrollment: 33 passed,
  0 failed, exit 2. (Exit 2 is the partial-run status.)
- check_template_sync.sh: exit 0. validate.py spec and ready on the specification: exit 0.
- Not run here: the four AC2 rows and taken-on-while-starting with a real socket, adoption161-restart-take-on,
  the setup161 cases on a real setup, check_gate_mutations.py for finding 161, the suites that need sockets or
  the user manager (103, 107, 58, 47, 85, 91, 106, 86), and scripts/verify.sh. These are the host's.
