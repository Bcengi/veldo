# VELDO-0142 scoped proof

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

The final suite has 22 identity rows plus 26 shared checks: 48 passed, zero failed. All
fifteen registered negative controls failed their named rows at their recorded checkpoints.
Of 24 consumer suites, six passed and eighteen failed. They include containment, permission,
runtime and gate-observation failures; none is certified as a non-regression without reviewer
execution. No full gate or independent approval is claimed.
