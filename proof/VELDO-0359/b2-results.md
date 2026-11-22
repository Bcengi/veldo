# VELDO-0359 B2: the agent-run store guard

Fixtures only: no real store and no live engine. This is a partial build report, not a
verification stamp or a landing decision. The real bind-mount and device cases are deferred
by owner approval 2026-11-22 (see "Fix round 2" at the end); they are recorded, never counted
as passed. The protected gate configuration is unchanged; its proposed suite entry is in
b2-gate-unconfined-proposal.txt. Where the sections below describe the state before fix
round 2, the last section supersedes them.

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
| layout/entries | Running/stale exact socket, other sockets, FIFO, symlinks and hardlinks including custom sidecars; socket-exception-removed, special-entries-allowed, links-allowed. Device entry deferred by owner approval 2026-11-22 (mknod EPERM), not counted |
| layout/mounts | Translated directory/ancestor/file mountinfo components and unreadable input, asserted; real namespace/bind cases deferred by owner approval 2026-11-22 (EACCES), printed and not counted; file-binds-allowed is judged on recorded mountinfo only |
| layout/placement | Overlap/equality matrix, runs fallback refused by name and its actual launch not accepted, marker-off fallback launch, explicit external runs; placement-skipped (fallback launch accepted), placement-check-skipped |
| launch/risky-real | Unchanged runner reaches fixture payload and refuses store/lock; guard-before-runner |
| launch/risky-census | Six end-to-end grant/copy exposure routes with marker-off sentinel controls; required-root early refusal; post-exclusion/optional/place controls and two-way qualified grant parity; precondition-skipped, census-prefilter, census-places-as-grants |
| launch/engines | Fixture Codex argument list with exactly one sandbox setting and sampled-off control; role-sandbox-wins, role-sandbox-duplicated. Fresh pinned-engine calls are excluded by this brief; B0's engine measurements remain the engine evidence |
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

## Fix round 2 (2026-11-22, after the independent review: FIX, two findings)

Source commit of the runs below: 350652220d3d6a9337bf34622e5efcd6ce8a77ca. Earlier passes stand; only
suite 158 and the new and changed mutants were run again, once each, through host_heavy.

- F1. store359-placement-skipped now removes the runs check and the placement check together. Row
  layout/placement launches the runs fallback for real: unmutated it is refused before acceptance,
  under the mutant the row sees the launch accepted ("runs fallback launch is not accepted: None").
  The marker-off fallback launch on its old path is a row check too. The placement check alone
  (control_launch.py, the loop after the runs check) has store359-placement-check-skipped: 24 matrix
  assertions go red while the fallback stays refused by the runs check.
- F2. The execution record's header carries the sampled decision (state, marker path, outcome, reason,
  element_path, recovery, directory; never the census grants): pending at acceptance, or off with the
  marker path. A launch the guard refuses before acceptance keeps a header-only record with the reason
  and the fix. Rows launch/ack (pending in the header, then applied on a wrapper line) and switch/off
  (off with the marker path; a refusal's header and no line) read the record through
  control_execution_record.read. Mutants: store359-record-header-dropped, store359-refusal-record-skipped.
  The per-dispatch guard log is unchanged.
- A1. Rows carry an explicit "payload reached" check. store359-guard-before-runner now fails
  launch/risky-real on "real risky runner: payload reached", and store359-socket-exception-removed fails
  layout/entries on "normal bound socket" and the payload-reached checks; neither has a JSONDecodeError.
  The reproduction script counts a mutant only when every bound row is red by an assertion.
- A2. codex_store_guard removes the role's own sandbox_mode pair and adds the guarded one. The row
  asserts the final argument list and exactly one sandbox setting. New mutant
  store359-role-sandbox-duplicated (the old appended duplicate) fails launch/engines.
- A3. A census that cannot be completed refuses as confined_runner_unavailable:census_failed:<item>
  (missing_item, unreadable_item, configuration, qualification, runner; process when the census process
  itself fails), with the item's path, and counts under the refused_census metric. store_reachable is
  left for an actual grant reaching the store directory. New mutant store359-census-failure-as-reachable.
- Carry-in from B1 fix 2: suite 157's "the launch refusal carries that name" row calls the launch
  preparation on a bare receiver; on this branch the B2 guard runs first, so the fixture now carries
  what the guard reads and substitutes the layout check as that suite's other fixtures do. No assertion
  changed; suite 157 has 33 assertions and query/journey expects 33.

Owner decision (Telegram 43030, research/approvals/2026-11-22-veldo-0359-b2-real-mount-deferred.md):
the real bind-mount cases (directory, ancestor, database file and lock file binds in the enforcement
namespace) and the device entry are deferred by owner approval 2026-11-22. The suite prints each as
"DEFERRED, recorded and not passed" with the errno and the follow-up; a deferred case is never an
assertion, so it is never counted as passed. The component checks on recorded mountinfo stay asserted
and row layout/mounts is green on them. store359-file-binds-allowed is rejected on recorded mountinfo
only ("database translated alias; lock translated alias"); its real-mount form is deferred with the
cases. Follow-up: research/specs-pending/VELDO-0359-follow-up-real-mount-fixture.md.

Results. Suite 158 through host_heavy, once: 20 row groups passed, 46 assertions passed, 0 failed
(exit 2 is the partial-run exit), with the two DEFERRED lines. Mutants through host_heavy, once each
(b2-fix2-mutation-results.txt): baseline and the three module no-ops pass; all ten are rejected by
assertion on every bound row: placement-skipped, placement-check-skipped, role-sandbox-wins,
role-sandbox-duplicated, census-failure-as-reachable, record-header-dropped, refusal-record-skipped,
guard-before-runner, socket-exception-removed, file-binds-allowed. Personal setup: 0 findings.
Template sync: pass. scripts/gate_unconfined.json unchanged.

Not run in this round: scripts/verify.sh, the full unit leg, the full mutation stage, suite 157 on pc2
(it ran here only, standalone and inside query/journey), the other B2 mutants (their earlier results
stand, on source that has since changed in the ways listed above) and the suites of VELDO-0141 that
read execution record headers. The landing gate and a fresh-context review of this round remain.
