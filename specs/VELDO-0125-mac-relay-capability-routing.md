---
schema: veldo.spec/v1
id: VELDO-0125
title: Mac worker dispatch through the relay with host-capability routing
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W88
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0108, VELDO-0124]
placement: [fleet, project_runner, contracts]
protected_paths: []
footprint:
  - "scripts/suites/86_veldo_0168_text.py"
  - "scripts/suites/68_veldo_0134_acceptance.py"
  - "engine/.veldo/control_channel_enrollment.py"
  - ".veldo/control_channel_enrollment.py"
  - "scripts/suites/33_veldo_0020_authority.py"
  - "scripts/suites/36_veldo_0023_journal.py"
  - "engine/.veldo/authority_contract.py"
  - ".veldo/authority_contract.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_store.py"
  - "engine/.veldo/control_membership.py"
  - ".veldo/control_membership.py"
  - "engine/.veldo/control_claim.py"
  - ".veldo/control_claim.py"
  - "engine/.veldo/control_assignment.py"
  - ".veldo/control_assignment.py"
  - "engine/.veldo/control_dispatch.py"
  - ".veldo/control_dispatch.py"
  - "engine/.veldo/control_reservations.py"
  - ".veldo/control_reservations.py"
  - "engine/.veldo/project_runner_macos_os.py"
  - ".veldo/project_runner_macos_os.py"
  - "engine/.veldo/project_runner_macos_wrapper.py"
  - ".veldo/project_runner_macos_wrapper.py"
  - "engine/.veldo/project_runner_macos.py"
  - ".veldo/project_runner_macos.py"
  - "engine/.veldo/project_runner_macos_profile.py"
  - ".veldo/project_runner_macos_profile.py"
  - "scripts/suites/*_veldo_0124_*.py"
  - "proof/VELDO-0124/*.py"
  - "proof/VELDO-0124/manifest.json"
  - "engine/.veldo/control_worker*.py"
  - ".veldo/control_worker*.py"
  - "packs/*/.veldo/control_worker*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/control_routing*.py"
  - ".veldo/control_routing*.py"
  - "packs/*/.veldo/control_routing*.py"
  - "scripts/suites/*_veldo_0125_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0125-mac-relay-capability-routing.md"
  - "specs/index.md"
  - "proof/VELDO-0125/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Mac worker claim, launch acceptance and result commands reach the same Linux authority
      through VELDO-0108. Set and completeness: For those three enabled remote command families,
      compare signed commands sent on the real Mac with records committed by the configured Linux
      SQLite authority; carry explicit domain/repository/store/workspace identities and observe no
      Mac authority store or local mutation fallback. Falsifier: Create a Mac-local authority store
      when remote submission fails; the one-authority check must fail.
    falsified_by: >
      Create a Mac-local authority store when remote submission fails; the one-authority check must
      fail.
  - id: AC2
    text: >
      Claim: Dispatch selects only a qualified worker satisfying every required host capability. Set
      and completeness: Register the selected Linux and Mac profiles and submit host-neutral, macOS-
      required and iOS-build units. Compare accepted requirements, selected host and actual worker
      launch; both macOS-required and iOS work go only to the Mac. With the Mac unavailable, those
      units remain visibly blocked. Falsifier: Fall back to Linux for an iOS build when the Mac is
      unavailable; the host-routing refusal check must fail.
    falsified_by: >
      Fall back to Linux for an iOS build when the Mac is unavailable; the host-routing refusal
      check must fail.
  - id: AC3
    text: >
      Claim: Remote result and spend records retain the original unit, host and dispatch identity.
      Set and completeness: Complete real Mac work through the relay and compare output/proof
      references, usage and terminal observations to the Linux authority record and owner-visible
      machine/run state. Submit a result for another dispatch and require refusal; SSH
      authentication alone cannot authorize it. Falsifier: Apply a relayed result to a caller-
      supplied different dispatch; the remote-result binding check must fail.
    falsified_by: >
      Apply a relayed result to a caller-supplied different dispatch; the remote-result binding
      check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Dispatch work to the qualified host capable of running it, with Mac workers using the existing
SSH relay to the Linux authority.

## Context

W88 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 2.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

Owner Telegram 28852 brings the Mac and built VELDO-0108 relay into the MVP. Reuse that relay
and its production authenticated IPC endpoint. Transport identity is not command authority.
Worker host capabilities are accepted configuration, not a claim made by a model. Cloud/other
hosts are Release 4; transport-failure and reconnect/recovery matrices are Release 2.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 2, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-10-10: candidate build on agent/codex/veldo-0125. Four canonical routing and
worker assets, with identical installed copies and seven-pack composition checks,
implement the three signed worker command families on the existing Linux
service/relay path, all-required-capability selection with durable blocked state,
and bound result/spend records. The Mac bridge consumes the 0124 supervisor.
Suites 105_veldo_0125_relay and 106_veldo_0125_routing supply named Linux logic
rows; proof/VELDO-0125/README.md records their scope and three single-change
falsifiers. The sandbox refuses Unix socket creation, so real IPC is explicitly
not run here; its runnable check is retained. Real Mac and SSH rows are declared
through the synthetic-engine native roundtrip driver and remain pending. No
provider login, live capture, deployed service, qualification or activation was
changed. Existing fleet, project_runner and contracts placements describe these
assets; no architecture contract amendment is made. Criteria, risk, approval and
status are unchanged. The reviewer owns the canonical gate and merged-tree stamp.

2026-10-10: the owner's assistant decided to amend the footprint to include
engine/.veldo/control_launch.py and .veldo/control_launch.py because AC2 cannot
hold in production otherwise. Production Runner preparation now selects the
qualified host before submission. The same review authorizes the listed service,
store, membership, dispatch, reservation and containment fixes and their 0124
regressions. Criteria and approval requirements are unchanged.

2026-10-15: B2 independent-review corrections bind remote acceptance to the current
eligibility decision inside its authority transaction, and wire factory submission
to a configured Mac receiver with a tracked asynchronous launch. Regression rows
cover withdrawn/replaced admission, factory delivery, missing-receiver retirement
and transport output that attempts to impersonate completion. Targeted falsifiers
remove the eligibility recheck, restore the unowned/no-contact submission, and drop
pending factory tracking. Configuration and evidence limits are recorded in
proof/VELDO-0125/README.md; acceptance criteria and approval requirements are unchanged.

2026-10-15: the owner explicitly requests durable result delivery and retries until
acknowledged, collection before cleanup, release from signed cleanup when exit
evidence is lost, and a scoped operator-signed release path for every remote hold.
This authorizes retrying delivery of the same terminal command, never re-executing
the unit. Deadline capacity release wakes waiting work. The recovery correction
and targeted falsifiers are recorded in proof/VELDO-0125/b2-recovery.md; broader
recovery, host qualification and activation remain outside this correction.

2026-10-15: further owner-requested corrections separate local Mac capacity
retirement from cleanup, propagate committed releases to the configured receiver,
replay release wakes after crashes, preserve TMPDIR deliverables, correct late
usage on the original invocation and bound delivery retries with exponential
backoff. The signed receiver status query reads the existing authority; it creates
no additional store. Targeted regression and falsifier records accompany this
correction. The reviewer retains responsibility for the full gate and real-host
qualification; no independent approval is claimed here.

2026-10-15: the owner's second B2 review requires Mac-confirmed retirement before
Linux capacity release, retained-result flushing on release wakes, the installed
engine usage reader, uncapped result delivery with bounded backoff and restart
replay, and indexed unconfirmed-release delivery without a startup connection
storm. The signed worker_retired command, launch-agent outbox resumer and targeted
regressions implement this correction. proof/VELDO-0125/b2-delivery.md records the
protocol, named rows and isolated falsifiers. The canonical gate and native host
qualification remain the reviewer's responsibility under the owner's run limits.

2026-10-15: the owner requires event-driven Mac delivery with a durable pending
index, no recurring idle timer or completed-history startup scan, per-dispatch
error isolation and permanent-refusal parking. Linux release wakes must retry
failed SSH handoffs with bounded backoff; the Mac must retain busy release events
and flush measured engine output even after a crash before result evidence.
Unknown outcomes retain measured usage on the original invocation exactly once.
Round 9 regressions and isolated falsifiers are added without changing historical
proof records. Native Mac/SSH qualification and the full gate remain with the reviewer.

2026-10-16: the owner requires active receiver entries to remain outside the
watched delivery queue, operator holds to await an explicit event without status
polling, and upgraded release events to survive permanent result refusals.
Recovery must preserve late wrapper output and original-dispatch replay usage;
execution-lock failures must be recorded with bounded retries. Mac admission now
uses a live slot index, and parking persists its parent before removing pending
work. New lifecycle regression rows and isolated falsifiers extend the evidence
without rewriting earlier proof records. The reviewer still owns the full gate,
merged-tree stamp and real Mac qualification under the owner's run restrictions.

2026-10-16: the owner requires crash reconciliation of local slot records and their
live index, migration before admission, active-owner replay on worker startup,
fail-loud recorder errors, blocking native process and startup waits, and a
regression for evidence plus an unauthorized release event. Round 11 adds new
proof modules and records under proof/VELDO-0125/b2-crash-events, preserving the
prior proof corpus. Heartbeat timeouts remain accepted profile fields for
compatibility; healthy runs use exit events and the existing runtime deadline.
The updated simulator models blocking exit events. The reviewer owns the full
gate and native macOS qualification under the owner's explicit suite limits.

2026-10-16, round 12: the owner requires recorder-failure parking without a
launchd relaunch loop, new-request isolation from retained deliveries, recovery
of future-due orphaned active entries, migration outside receiver admission,
runtime-cap precedence during cooperative stop, and safe exit-watch lifetime.
The delivery worker migrates the live slot index at its RunAtLoad startup;
receiver construction disables migration and requires that installed index.
Recovery schedules orphaned entries with their original deadline and attempt
count. It does not perform backlog network calls on the receiver's stdin path.
Recorder failures retain the original entry in .parked using rename, outside
launchd's watched queue. Explicit new events can retry operator-repaired work.

The macOS worker profile changes from veldo.macos_worker_profile/v1 to v2.
Both heartbeat_seconds and heartbeat_window_seconds are removed, including
from the serialized profile whose digest binds qualification. v2 rejects either
retired field and refuses v1; operators must remove those fields, set schema v2,
and qualify the resulting profile digest before activation. Existing native
qualification is not silently reused. Runtime, startup and shutdown deadlines
remain required. Healthy wrappers use NOTE_EXIT; a stalled live wrapper is
terminated at the runtime cap. The VELDO-0124 heartbeat-missing assertion is
restored to its prior content as historical v1 evidence. Its heartbeat-loss
liveness check is superseded for profile v2 by the NEW VELDO-0125
AC3/stalled-wrapper-event-or-runtime-cap row, not by editing its expected result.
The unmodified v1 row is not a v2 qualification claim. Round 13 below corrects the compatibility gap; the historical suite remains
mandatory and its assertions are not waived.
New correction records identify the completed round 11 routing log without
rewriting that log or its earlier README. Full gate and native qualification
remain with the reviewer under the owner's run restrictions.

Before enabling the receiver, run `python3 .veldo/control_worker.py CONFIG --install`
on the trusted worker to migrate the index and install its launch agent. The
RunAtLoad delivery worker also initializes the index as an upgrade/startup step.
An uninstalled receiver refuses with `unavailable_service:slot_migration_required`
before acquiring admission.lock, so a history scan cannot hold that receiver
inside admission. Installation precedes dispatch eligibility; this is not an
automatic retry of execution or reuse of an old qualification.


2026-10-16, round 13: the owner requires the 0124 suites to remain green with
unchanged recorded assertions, retryable missing-index refusals, orphan recovery
on failed receiver starts, diagnostics even when an unwritable outbox prevents
parking, and per-entry active recovery. Complete v1 profiles retain their
original qualification and liveness contract. The product migration API returns
a v2 profile requiring new qualification; the event fixture uses this path.
Explicit v1 wrapper requests alone enable legacy heartbeat compatibility; v2
field rejection, runtime-cap precedence and exit-watch lifetime are unchanged.
Missing migration schedules pending delivery so an already installed launch
agent wakes on upgrades without a plist change. Receiver finalization schedules
orphans regardless of incoming success. Recorder errors log before best-effort
parking and remain visible when parking fails. Unreadable active entries are
quarantined individually while healthy work drains. New regression rows and
before/after selected-suite logs are under proof/VELDO-0125/b2-round13. These
corrections supersede the round 12 requirement to install manually before any
dispatch can recover and its known-red historical-suite caveat. Native
qualification and the canonical merged-tree gate remain pending reviewer runs;
no criterion or recorded historical test assertion is weakened.

2026-10-16, round 16: the owner requires one outbox entry validator at every
read boundary, covering recovery, drain, receive and queue transitions. Required
fields are request (dict), attempts (non-negative int, excluding bool), and due
(int or float, excluding bool); request.dispatch_id is a non-empty str whose
SHA-256 key equals the entry filename. The only optional field is reason (str),
which failure() writes. No other top-level fields are accepted. Due must be
finite and in [0, now + 300 seconds], retaining the writer's immediate sentinel
and old retries while bounding future deadlines by its maximum backoff. Invalid
entries are logged and quarantined as original bytes on first read. Operational
lock failures such as ENOSPC retain readable active entries for later recovery.
Drain sleeps are bounded to 1-300 seconds, with invalid computed delays logged
and clamped. The regression matrix and before/after selected-suite observations
live under proof/VELDO-0125/b2-round16; the full gate and native qualification
remain the reviewer's responsibility under the owner's run restrictions.

2026-10-16, round 17: the owner narrows quarantine to invalid entry content.
Opening or reading an entry with an OSError logs and retains the original file
for another pass, including EIO, EMFILE, ENFILE and EACCES. This supersedes
round 16's read-time deadline bound: due remains a non-negative finite int or
float (never bool), bounded only by sys.float_info.max, independent of the
wall clock. A backward clock step cannot invalidate a writer-created retry.
The existing 1-300 second drain sleep clamp bounds far-future waits. The
round 16 invalid-entry matrix now tests the absolute float boundary in place
of formerly rejected finite future deadlines; all other content checks remain.
Selected-suite before/after observations and regression rows live under
proof/VELDO-0125/b2-round17 and round17_checks.py. The reviewer retains the
full gate and native qualification; no merge or independent approval is claimed.
