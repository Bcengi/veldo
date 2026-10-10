# VELDO-0142 scoped proof

## Mutation-stage follow-ups

VELDO-0142 added the repository path-conflict check before Git identity resolution in
`control_store.bind_repositories`. The original mutation disabled the later insert-loop check,
which cannot see a conflict after that preflight in the same transaction. The case now disables
the preflight check. The existing alias row is unchanged and still requires the exact
`repository_binding_conflict` refusal for foreign repositories and clones.

The account cap-stop row used the ordinary `run` helper's wait, with no row-specific timeout,
while each fake engine slept for 30 seconds. Its Claude and Codex cases now pump the launch
pipe with a five-second deadline, request cleanup on expiry, and bound the final receiver wait
to five seconds. Every original cap, cancellation, usage and charge assertion remains. Failure
diagnostics are included in the assertion label so the gate's worker retains them in its receipt.

Scoped results are recorded in `mutation-followups.json`:

- `python3 scripts/selftest.py --suite 59_veldo_0037_aliases`: 79 passed, zero failed.
- `python3 scripts/selftest.py --suite 75_veldo_0062_accounts`: 49 passed, zero failed.
- Both suite commands returned 2, the self-test dispatcher's successful partial-run status.
- Direct gate workers: both cases passed baseline and no-op controls, and their mutants failed
  only the required row. Alias mutant: 20.7 seconds. Cap mutant: 59.1 seconds for the whole suite;
  the cap cases timed out and cleaned up in 5.4 seconds (Claude) and 5.5 seconds (Codex).
- Confined workers: both attempts stopped before executing tests because this agent's outer
  launcher did not preserve the tree marker. An explicit-runtime confinement diagnostic also
  failed before tests with `agent sandbox broker unavailable`. Confined kills remain unverified.

Replay one case and leg at a time with the same worker launcher, ownership cleanup and result
validator that the gate uses (the output directory must not already exist):

```sh
python3 proof/VELDO-0142/mutation_followups.py --case repository-binding-unchecked --leg direct --output "$TMPDIR/alias-direct" > "$TMPDIR/alias-direct.log" 2>&1
python3 proof/VELDO-0142/mutation_followups.py --case account-cap-stop-ignored --leg direct --output "$TMPDIR/cap-direct" > "$TMPDIR/cap-direct.log" 2>&1
```

Use `--leg confined` and a fresh output path for each confined replay from a launcher that
preserves its tree marker. The scoped helper imports the registry and driver APIs; it never
invokes either full mutation-stage entry point. No full self-test, mutation stage or gate ran.

## Earlier scoped proof

The review fixes implement immutable setup additions, store refusals, complete launch scrubbing
and validation of incoming worker commits. The implementation and fixture commits are d439af66, 90293601, e04a8f0a, b6d1790a 30e97110 and 1242de16.
Specification status stays ready. The full gate, independent approval, push and merge remain
reserved for the reviewer and owner.

| Review item | Suite 103 rows | Registered falsifiers |
| --- | --- | --- |
| 1. Environment configuration injection, including spawn and engine overrides | launch/no-config-overrides; launch/spawn-config-commit-authors; launch/no-author-overrides | identity142-config-overrides-kept; identity142-spawn-strip-omitted; identity142-engine-config-reinjected; identity142-environment-overrides-kept |
| 2. Every incoming implementation, evidence and ancestor commit must match | lander/worker-commit-mismatch; lander/identity-and-reland-authors | identity142-worker-authors-unchecked; identity142-lander-caller-author |
| 3. Existing setup adds missing bindings and identities, preserving existing records | setup/existing-store-adds-binding; setup/rerun-adds-identity; setup/rerun-change-refused; setup/full-command-and-rerun; binding/immutable | identity142-rerun-binding-not-written; identity142-setup-binding-omitted; identity142-binding-replaced |
| 4. Store records and both registration callers refuse an absent identity without writes | binding/store-and-callers-missing; binding/missing | identity142-store-unbound-written |
| Keychain references follow VELDO-0144 | setup/keychain-reference-pattern; setup/reference-only-and-unchanged | identity142-reference-too-loose |
| Setup emits each configured identity | setup/configured-log | identity142-setup-log-omitted |
| Land station uses only its repository record | lander/station-record-authority | identity142-station-caller-config |
| Caller supplied lander identity refuses | lander/caller-identity-refused | identity142-caller-identity-ignored |
| Independent clone refusal fixture and direct author comparison | clone/unbound-refused; clone/identity-authors | identity142-clone-global-author |
| Clone layout rule under the fixture's temporary directories | clone/layout-refused | none registered (a no-op layout check fails the row; the rule is VELDO-0042's) |

Rerun identity additions now succeed and report the git_identities step as done; changes to an
existing identity retain binding_mismatch:git_identity_change. Existing repository bindings
retain binding_mismatch:repository_identity_change. Missing store identity metadata refuses
missing_authority:repository_identity before DDL, rows or caller ownership registration.

The land station no longer accepts an identity configuration or supplies one to GitLandOps.
Suite 103 lander/station-record-authority constructs the station against the real identity
store, reads its bound author, accepts a configuration without a caller identity and refuses
a legacy caller identity. identity142-station-caller-config restores the dead configuration
read and fails that row. The VELDO-0148 install/land-station consumer assertions are retained. The lander docstring describes the
authority reader requirement. The specification explicitly scopes out control_replica's
standalone authority audit exports; it is not wired into the factory. These documentation
changes do not require a behavioral falsifier.

The setup fixture uses a real SQLite store, signing keys, enrollment and installer. Tailscale,
engine binaries, service management and host qualification are controlled local stand-ins.
It removes identity tables from a completed store to model a VELDO-0139 factory, then proves
that rerunning setup writes its explicit binding. It adds one identity and refuses an edit
without changing stored contents. Tokens and key values are never resolved.

Worker fixtures provision real clones under two identities with a conflicting global identity.
They make real Git commits with counted and parameterized environment configuration injections.
The actual Receiver._spawn runs with both engine bindings and unbound adapters, each through
local and reported launch paths. Credential resolution, execution recording, baseline construction
and containment are controlled seams; actual processes and commits are real. The environment
assertions enumerate forbidden names independently of the implementation scrubber.

The fixture tree lives in the process temporary directory, the one place the confined gate domain,
a mutation worker and first use's copy under /tmp all let the suite write. The VELDO-0042 layout
rule refuses a protected target beneath a temporary directory, so while the provisioner runs the
tree's own tmp, var-tmp and shm stand for the system's temporary directories, as suite 66 lays out
production's. Row clone/layout-refused proves the rule still refuses a clone root, cache root or
store beneath the real system's temporary directory and beneath each of the tree's, making nothing.
A setup block that ends early emits each of its later rows as failed, so no falsifier removes a
baseline row.

The lander inspects every commit reachable from evidence but absent from the trunk watermark,
including earlier worker ancestors. Negative controls separately alter author and committer for
implementation and evidence, plus an earlier ancestor. Refusal precedes all merge commits.
Positive fixtures land and re-land units for both identities, inspecting twelve merge and
projection commits. Gates and policy acceptance are controlled seams, not gate verdicts.

observations.json records actual identity records and worker and landed authors. verification.json
records suite results, each exact mutant diff and source digest, named failed rows and diagnostics.
The clone mutant fails on the author comparison showing Global Stranger, before local settings
are read. The scoped drive.py invokes only suite 103 serially and restores each mutated source
in finally; the repository mutation drivers are never invoked. consumer-verification.json records
the permitted touched consumer suites individually, with honest failure lines and log digests.
Partial suite exits and scoped assertions do not establish a full gate result or landing approval.

The first fourteen negative controls ran at 90293601; the final station row and its control
ran at 30e97110. Each mutation records its suite digest, allowing exact replay of either
checkpoint. One premature identity suite attempt was stopped after it overlapped a consumer
retry. It supplies no result; the final identity checks were rerun after the consumer process
finished. Consumer results retain the initial startup failures and owned-runtime retries.

The final suite has 23 identity rows plus 26 shared checks: 49 passed, zero failed, unconfined,
in the confined gate domain and from a copy under /tmp. All fifteen registered negative controls
failed their named rows at b4540fbc (drive.py) and in the gate's mutation stage, confined
(the stage for finding 142: 15 registered, 15 rejected).
Of 24 consumer suites, six passed and eighteen failed. They include containment, permission,
runtime and gate-observation failures; none is certified as a non-regression without reviewer
execution. No full gate or independent approval is claimed.
