# VELDO-0153 review handoff

The factory lander and protected publication executor use the identity Git profile.
The profile drops inherited Git variables and SSH agent access, disables global and
system configuration, and resolves only the bound credential through Secret Service.
Tokens reach Git through a scoped credential helper; SSH names one key with agent
and default configuration discovery disabled. Missing credentials refuse without fallback.
The network profile retains the operator's transport configuration.

`control_git_identity_transport.check_remote` is the shared push, creation and
adoption owner check. It accepts GitHub HTTPS and SSH URLs for the recorded owner,
including scp syntax. Other owners refuse as `binding_mismatch:remote_owner` before
network writes. Userinfo, unsupported hosts/transports and malformed paths refuse.
Factory publication resolves named remotes from local metadata. It requires one
push destination and refuses local routing or authentication overrides. This is a
compatibility change for fixtures using file remotes, fan-out or ambient credentials.
There is no legacy credential fallback.

The lander emits identity, owner, request and repository observations and counts.
The executor keeps metadata-only operation observations in `git_identity_operations`
and returns per-identity push/refusal metrics. Remote rejections with unchanged refs
are named; an unconfirmed remote state remains unknown and cannot count as landed.

## Executed scope

```sh
TMPDIR="$PWD/.veldo0153-scratch" python3 scripts/selftest.py --suite 107_veldo_0153_identity_push > "$PWD/.veldo0153-suite.log" 2>&1
```

Create the scratch directory first if absent. The suite has 58 named assertions.
Its dispatcher also runs 26 shared setup assertions. All 84 passed; the command
returns 2 by design because it is a partial run. `observations.json` records only
this specification's assertions. This is not aggregate unit evidence, a green gate,
a landing decision or a claim that every acceptance criterion is fully qualified.

The suite uses real Git processes, two distinct synthetic token values and SSH key
paths, SQLite identity records, credential-helper processes, exact bare-remote refs,
and a rejecting receive hook. Secret Service is a generated fake executable. The
SSH wire is an explicit adapter inserted after production profile construction;
it checks the selected key and environment and invokes real receive-pack/upload-pack.
It does not perform SSH cryptography or prove real GitHub authorization. Candidate
policy and gate acceptance are controlled seams; no gate is executed.

| Criterion | Principal assertion rows | Single-change falsifier |
| - | - | - |
| AC1 | `profile/planted-helper`, `profile/direct-push/alpha`, `lander/alpha/alpha`, `executor/own` | `identity153-global-helper` replaces the helper reset with inclusion of the planted global config. `profile/planted-helper` fails after setup succeeds. |
| AC2 | `owner/alpha/push/beta`, `lander/alpha/beta`, `executor/beta` | `identity153-host-only` removes only the owner comparison. These refusal assertions fail after setup succeeds. |

Finding 153 registers both controls. `falsifiers.json` preserves exact replacements,
failing assertions and restored results. Each was driven by the named suite alone,
with both canonical and installed copies restored in a finally block. Neither
repository mutation driver was executed.

## Host qualification not run

Exact command, from this checkout on a host authorized to write the disposable remotes:

```sh
python3 proof/VELDO-0153/host_check.py /absolute/path/to/host-config.json > /absolute/writable/path/veldo-0153-host.log 2>&1
```

The config has a `repositories` array. Each entry supplies a complete VELDO-0142
`identity` record, a `remote` URL to a preexisting disposable GitHub repository, and
`mismatched_owners` containing the other identity's owner and a third owner. Supply
at least two identities and both token and SSH credential kinds. Credentials must
already exist as Secret Service keychain references. SSH credential values are
absolute key paths. An accessible SSH agent must hold a different key; the check
compares its public fingerprint with every selected SSH key. No login is performed.

The driver plants a global helper, a system rewrite, a failing SSH command and the
other-key agent. It creates unique disposable branches and pushes through the direct
profile, lander and executor. It checks the remote tips and named owner refusals.
It retains the branch names in its output for independent inspection and does not
delete them. Its rows are `host/AC1/direct/<identity>`, `host/AC1/lander/<identity>`,
`host/AC1/executor/<identity>`, `host/AC1/planted-helper/<identity>` and
`host/AC2/<operation>/<identity>/<other-owner>`.

Real GitHub, live Secret Service and SSH-agent qualification were not run in this
sandbox. VELDO-0143's provisioner is absent here: creation/adoption calls to this
shared check and initial pushes remain that specification's own integration legs.
The driver tests the shared creation/adoption check, not a nonexistent provisioner.

## Remaining review work

The owner's strict token rule permits only this specification's suites; a later
instruction also requests consumer suites. Clarification was requested. With no
answer, this run retained the strict rule. `consumer-suites.json` lists a conservative
set of directly referencing suites and exact commands for the reviewer. They were
not run, and compatibility is not certified. Existing publication fixtures using
unbound repositories or file remotes will need identity-aware fixtures; production
must continue to refuse them rather than acquire a legacy bypass.

The canonical gate, independent critical-risk review, human approval and host rows
remain outstanding. Specification status remains ready. No verification stamp,
review verdict, approval or shipped claim was manufactured. Canonical and installed
assets match byte for byte; this source tree has no generated pack copies of them.
