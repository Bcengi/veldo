# VELDO-0359 B2: the agent-run store guard

Fixtures only: no real store and no live engine. This is a partial build report, not a
verification stamp or a landing decision. The real bind-mount cases could not run on this
host, so B2's exit is not met. The protected gate configuration is unchanged; its proposed
suite entry is in b2-gate-unconfined-proposal.txt.

## Implementation

Both product trees have the same changes. Local agent launches sample the existing switch
once. An absent marker means on; a valid marker means off; an invalid marker refuses.
The sampled decision controls the query path, preflight, wrapper and Codex override.
The preflight follows D7: structured probe, risky floor, resolved database directory,
recursive entries with only the owned authority.sock exception, translated mount aliases,
runs location, then placement. The risky census models post-exclusion grants separately
from placement inputs and copy sources, and never prepares client state.

The wrapper audits every descriptor immediately after parsing. An early refusal reports
only through a validated setup pipe; the receiver handles it before identity/release and
keeps containment cleanup. A default run installs the existing clone ruleset after release
and before the heartbeat. Failure bytes name audit/probe/create/add/restrict. Acceptance
records pending; only the success byte records applied. Risky runs get no extra layer and
record runner_started. Decisions are on owner-visible lines, execution records and a
finite per-dispatch guard log, including pre-acceptance refusals. Codex's override is
applied from the sample, after the role configuration; it is never a failure fallback.

The existing clone ABI function, confined runner and configuration, store-opening path,
signer, lock, authority socket, control client and runs location were not changed.
The VELDO-0254 AC3 amendment is also recorded in that specification.

## Fixture boundaries and rows

Suite 158 copies the installed modules into an exclusively created fixture directory,
creates a SQLite database and authority-protocol listener, and runs production
Receiver.launch, preflight, containment and wrapper code. Dispatch/prerequisite accounting
and the final reap are fixture substitutes. The risky payload uses the unchanged runner.
Suite 157 remains portable; its optional guarded journey forks the query client, drops
inherited descriptors, audits and installs the real ruleset, then compares its answers and
ordered callbacks with the direct receiver Gate. No model executable is used.

| Row | Fixture and falsifier |
|---|---|
| launch/guard-default | Engine, conversation and workflow launches; parent and descendant content/name attacks, each with a successful marker-off control; database digest and unsigned socket refusal; guard-skipped |
| ruleset/primitive-symlink-out | Primitive target-resolution control outside launch preflight; no mutant required by design |
| launch/guard-read | Write-only ruleset permits read-only lock open and flock without a competing holder; real guard denies open; write-only-guard |
| launch/enforce-fail | Argument-matched seccomp for probe/create/add/restrict; named failure, no payload; guard-skipped |
| launch/descriptors-early | Poisoned standard streams/setup, unchanged bytes and stdin offset, durable early audit report, ordinary external log accepted; fd-check-late and audit-late-reader-only |
| launch/descriptors-leaked | Extra sidecar/lock/directory/deleted handle, inspection/enumeration/store-inventory failures and clean control; fd-check-skipped |
| launch/ack | Pending before acceptance, applied only after success, no applied on restrict failure; ack-early |
| launch/receiver-memory | Receiver proc FD/memory, process_vm read/write and pidfd_getfd; successful unguarded controls; guard-skipped |
| launch/abi | Real receiver seccomp and parameter ABI/platform refusals, supported default/risky controls; low-abi-accepted and risky-floor-skipped |
| layout/entries | Running/stale exact socket, other sockets, FIFO, symlinks and hardlinks including custom sidecars; socket-exception-removed, special-entries-allowed, links-allowed. Device creation NOT RUN (EPERM) |
| layout/mounts | Translated directory/ancestor/file mountinfo components and unreadable input; real namespace/bind fixture NOT RUN (EACCES), row fails; file-binds-allowed is NOT RUN, not a kill |
| layout/placement | Overlap/equality matrix, runs fallback refusal and marker-off fallback launch, explicit external runs; placement-skipped |
| launch/risky-real | Unchanged runner reaches fixture payload and refuses store/lock; guard-before-runner |
| launch/risky-census | Six end-to-end grant/copy exposure routes with marker-off sentinel controls; required-root early refusal; post-exclusion/optional/place controls and two-way qualified grant parity; precondition-skipped, census-prefilter, census-places-as-grants |
| launch/engines | Fixture Codex role/config precedence and sampled-off control; role-sandbox-wins. Fresh pinned-engine calls are excluded by this brief; B0's engine measurements remain the engine evidence |
| query/journey | Suite 157 differential journey under the real ruleset; its existing unset-query negative control and B1 events-dropped falsifier remain registered in suite 157 |
| switch/off | Real unguarded read, sample/record and invalid-marker controls; B1 switch-ignored remains registered in suite 157 |
| switch/run-cannot-flip | Default and risky payload marker/name attempts plus next-launch check; switch-outside |
| switch/transitions | Event-held old off/on runs across both marker transitions; no mutant required by design |
| paths/canon | Resolved aliases and canonical fixture paths |

Mutant names in the table carry the store359- prefix. B1 query/scope, query/lifecycle and
query/cost remain in suite 157; its portable harness substitutes B2 preflight/containment,
and its bounded-notice expectation includes the new pending observation. No pre-existing
non-ticket suite was edited. The B1 reproduction helper selects suite 157 explicitly so
adding B2 registrations does not expand its original fifteen-case scope.

## Checks and remaining work

Final implementation commit: 4c6e5d249ed471236c0719b5121330884381151b. Suite 157 on pc2:
32 assertions passed, zero failed (six row groups). Suite 158 through host_heavy:
45 assertions passed, one failed (19 passing row groups and the incomplete mount row).
The guarded differential query journey passes. Eighteen B2 mutants each turn every bound
row red; the nineteenth, file-binds-allowed, is NOT RUN because its baseline row is
incomplete. Baseline and both module no-op controls pass on the mutation target rows,
while retaining the mount-row failure. The mutation receipt's overall passed value is
therefore false. Personal setup has zero findings; template sync, generated requirements,
source-boundary and whitespace checks pass.

Exact source identity, counts, routes and digests are in b2-checks.txt. The own-row mutation
receipt is b2-mutation-results.txt; b2-mutation-controls.py reproduces only suite 158's
registered cases, with baseline and module no-op controls. Worker errors or absent rows
never count as kills. A mutant whose unmutated row is incomplete is NOT RUN.

Namespace setup in the actual bind fixture cannot write the user namespace's setgroups
control (EACCES). Creating a device returns EPERM. Neither missing facility is counted as
evidence, and no host security setting was changed. The component mount checks are useful
but do not satisfy the required real mounts. The five receiver-access controls succeeded
on this host; their guarded denials are counted. No loaded run was needed.

By the owner's cost rule, the full verification script, full unit leg and full mutation
stage were not run. The landing gate must still do its canonical spec/proof/generated,
template, source-boundary and secret checks; the full unit manifest, including legacy
dispatch, containment, heartbeat, clone, engine adapters/configuration, execution records,
risky-runner and launch-hygiene suites; the full registered mutation stage; and its
integration/first-use checks. Real mount cases need a host with the required fixture
facility. Fresh-context independent review and owner approval of the protected gate entry
remain pending. No full-gate, shipped-status or landing claim follows from this report.
