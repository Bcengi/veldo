# VELDO-0161 round 10: the full gate at 928918a5 was red

Branch agent/claude/agent/claude/veldo-0161, from 928918a5 (VELDO-0161 on VELDO-0153 b44736c0, neither landed).
Run on the host. Nothing here is a gate result, a review verdict or an approval: the selftest runs are partial
runs and `./scripts/verify.sh` was not run. Every result is in `host-runs.json` beside this file.

Commits: 3cced949 (A), aff38e10 (B: the fence, suite 107, suite 67), 2c1daca3 (suite 109 uses the wire's fence),
9cd90894 (B: suite 67's boundary holds the pushes of every land a row judges), then this evidence and the
specifications' history.

## A. Caused by VELDO-0161: git-boundary/no-private-git-invocations (suite 50)

`scripts/check_git_boundary.py` accepts a Git argument vector only as the first argument of `_git_process.run`
or `_git_process.check_output`. control_repository_provisioner.py named the organ `GP` (line 54) and called
`GP.run` at lines 70, 175 and 333. The alias is now `_git_process`, as control_effect_executor.py:27 names it,
in .veldo/ and engine/.veldo/ (identical files). Naming only: the calls already went through git_process.
Finding 161's adoption161-provisioner-hooks anchor (check_teeth_mutations.py:10681-10682) follows the rename.
`check_git_boundary.py`: pass. Suite 50 confined: 30 passed, 0 failed.

## B. Pre-existing from VELDO-0153: the hermetic fence where AF_UNIX sockets are refused

The gate's own domain allows AF_UNIX sockets (its broker mediates them). A launcher started inside that domain
installs the strict filter instead, and there `socket(AF_UNIX)` is EPERM (agent_sandbox.py, Handoff.install).
Suite 104's VELDO-0210 row starts the mutation stage inside the unit stage's domain, so its workers are nested,
and identity_wire.py:168 raised PermissionError in every fenced suite there. Reproduced on the host by nesting
gate_candidate.py: suite 67 died before its first row at 3cced949; suite 104 at 928918a5 reports
`driver_error: 67_veldo_0056_candidates.py:lander.py:False:noop: worker exit 1`.

The fix is in the fence, not the gate: `Fence.active()` tries its recording agent's socket once. A
PermissionError (EPERM or EACCES) means no process under this confinement can open a socket to any SSH agent,
so the confinement is the guard. The fence records that as an observation (`agent_observation`,
`fence-observations.jsonl`, one stderr line), runs without the agent, and points SSH_AUTH_SOCK at a path in its
own directory where nothing listens. It is not a pass of the agent wall. Any other socket failure is raised,
every other wall is unchanged, and where local sockets are allowed the recording agent stands as before.
scripts/gate_unconfined.json is unchanged.

Suite 107's fence/keyring-socket-refused judges the wall that stands in each domain. Where local sockets are
allowed it judges the fence's audit hook and agent, as before. Where they are refused it judges that neither the
keyring nor the named agent can be reached, that the name is a path in the fence's directory where nothing
exists, and that the fence recorded the observation. Suite 109's own copy of this fallback is gone: its
`fenced()` is the wire's fence.

## B, finding 56: candidate-trunk-moved-before-policy

The mutant pushes the candidate through the network profile before the policy answers, in every land that
reaches finalize. That push named https://github.com/fixture/remote.git, so the fence refused it and raised
at the suite's end, and the worker exited 1. At aff38e10 this run still had two violations: the rejection row's
valid land and detached-held-trunk's land. Following round 3 (adoption/signer-no-agent owns what it watches),
suite 67's lander boundary now holds the pushes of every land a row judges. In a land the row expects refused it
holds any push. In a land the row expects to land it holds any push not through the identity profile (VELDO-0153
AC1). A held push is answered as a failed push without running and kept in `pushes`.
candidate/rejection-leaves-trunk (all six of its lands) and candidate/detached-held-trunk require none held.
Lands no row judges this way keep the fence alone. Result at 9cd90894: killed, with
rejection-leaves-trunk and detached-held-trunk red, worker exit 0 and no fence violation.

## B, finding 28: the eight survivors are not the fence's

The mutation stage's workers run at the top of a gate domain, where AF_UNIX is allowed. Suite 58 ran to its end
in every one of these workers (all exit 0), and it runs green confined and nested (77 passed, 0 failed). The
eight cases still survive because VELDO-0153 rewrote the rows they target. Those rows now judge the identity
profile, or a refusal made before anything is recorded, so the mutated code cannot reach them. The classification
found the same survivals at b44736c0. The registrations are unchanged here. Each is a real gap for the owner or
reviewer:

| Case (module) | Target row still green | Why | Row that fails today / should fail |
| --- | --- | --- | --- |
| effects-push-by-send-pack (control_effect_executor) | publication-url-rewrite | The row now expects `binding_mismatch:identity_transport_config` before any push (0153 AC3), so the push command is never reached | pre-push-hook and smart-http turn red; url-rewrite cannot observe the push form |
| effects-destination-not-recorded (control_effects) | publication-destination-without-credentials | The credential-bearing URL is refused (`binding_mismatch:remote_host`) before any record, so a dropped record leaks nothing | records-resolved-destination turns red |
| effects-destination-with-credentials, effects-destinations-not-scrubbed (control_effect_executor) | publication-destination-without-credentials; also scrub-transport-prefix for the second | `check_remote` refuses userinfo (other than ssh `git`), query, fragment and other ports before the record is built, and the scrub rows call `scrubbed_url` directly, so the record-site scrub never sees a credential | None can: a row would need a destination that passes the owner check and that the scrub changes |
| effects-network-profile-without-global-config (git_process) | global-insteadof, global-credential-helper, global-ssh-command, config-selection-parity | Publication runs in the identity profile; these rows were rewritten to judge it | publication-network-profile-strips-coordinates turns red (not a registered target) |
| effects-network-profile-drops-transport-variables (git_process) | publication-env-ssh-command | Same: identity profile | publication-network-profile-strips-coordinates turns red (not a registered target) |
| effects-network-profile-drops-config-selection, -drops-config-injection (git_process) | publication-config-selection-parity | Same: identity profile | publication-network-profile-strips-coordinates (registered) turns red |

## Host results

Confined, `python3 -I -S scripts/gate_candidate.py --root $PWD -- bash -c 'python3 scripts/selftest.py --suite S'`
at 9cd90894: suite 50 30/0, 58 77/0, 67 37/0, 107 146/0, 104 33/0. Suite 104 ran in a standalone clone
(/tmp/v161f/c), because the confined domain cannot read this linked worktree's common Git directory, which its
mutation snapshot clones. The same clone at 928918a5 gave 32/1 with the gate's driver_error.

Nested (strict, AF_UNIX refused): suite 67 37/0 (at 3cced949 it died at identity_wire.py:168), 58 77/0, 107
146/0, each with the fence's observation. Suite 109 75/4 at head and at 928918a5, the same four AC2 rows red by
name (no authority service can serve without local sockets).

Mutations, `python3 -I -S scripts/check_gate_mutations.py --root $(pwd -P)`: candidate-trunk-moved-before-policy
killed. `--finding 161 --finding 28 --finding 56`: 152 registered and executed, 144 killed (161: 57 of 57;
56: 22 of 22; 28: 65 of 73), the eight finding-28 cases above survived, 180 workers all exit 0, no
driver_error.

Unconfined, `python3 scripts/selftest.py --suite S` at 9cd90894: 109 81/0, 86_veldo_0189_engine_upgrade 60/0,
73 43/0, 85_veldo_0171_setup_api 44/0, as at round 9.

Static at 9cd90894: check_git_boundary, lint, generated, template sync and docs pass; secret inventory 0
outstanding.
