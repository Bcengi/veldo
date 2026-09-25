---
schema: veldo.spec/v1
id: VELDO-0129
title: Real worker adapter wiring for LiveLoop and LiveReviewer
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W92
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0049, VELDO-0050, VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0064, VELDO-0141]
placement: [loop, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/executor.py"
  - ".veldo/executor.py"
  - "packs/*/.veldo/executor.py"
  - "engine/.veldo/dispatch.py"
  - ".veldo/dispatch.py"
  - "packs/*/.veldo/dispatch.py"
  - "engine/.veldo/control_engine*.py"
  - ".veldo/control_engine*.py"
  - "packs/*/.veldo/control_engine*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "scripts/suites/*_veldo_0129_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0129-live-build-review-adapter-wiring.md"
  - "specs/index.md"
  - "proof/VELDO-0129/*"
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
      Claim: The installed LiveLoop.build dispatches the selected real adapter and returns bound
      implementation/evidence artifacts. Set and completeness: Install the reference distribution
      and invoke LiveLoop.build for the chosen Claude Code and Codex configurations without a
      caller-injected build callable; observe actual process invocation in an accepted isolated
      clone and compare returned commit/proof references to the dispatch. Missing configuration must
      refuse before launch. Falsifier: Leave production build dependent on an injected callable; the
      installed default-build journey must fail.
    falsified_by: >
      Leave production build dependent on an injected callable; the installed default-build journey
      must fail.
  - id: AC2
    text: >
      Claim: Both LiveLoop.review and LiveReviewer.review dispatch a fresh independent reviewer
      through the selected real adapter. Set and completeness: For each entry point and both
      configured engines, supply the exact spec, source/diff and proof in fresh context without the
      builder conversation; inspect real reviewer process, distinct eligible identity and subject-
      bound findings/verdict. Apply current policy review count and forbid self-review. Falsifier:
      Reuse the builder context for review; the fresh-context independence observation must fail.
    falsified_by: >
      Reuse the builder context for review; the fresh-context independence observation must fail.
  - id: AC3
    text: >
      Claim: Adapter outcomes feed the authoritative proof/review transition path without
      manufacturing success. Set and completeness: Exercise valid results, nonzero exit, missing
      artifact, malformed review and missing usage through the installed wiring; inspect accepted
      evidence or named refusal, retained charge exposure and no source completion from process exit
      alone. Every build/review call uses the existing pre-call reservation boundary. Falsifier:
      Convert adapter exit zero to passing review without a verdict artifact; the missing-review
      refusal check must fail.
    falsified_by: >
      Convert adapter exit zero to passing review without a verdict artifact; the missing-review
      refusal check must fail.
  - id: AC4
    text: >
      Claim: The Runner and factory loop run inside the authority service; a loop pass runs only on its
      three wake sources (each journal-advancing packet or pass, each run's end seen on the Runner's
      launch pipe, and an account reset timer), offers every assigned eligible unit and every next
      station, and stops offering a paused project's units; the factory loop never polls. Set and
      completeness: Start the installed authority service with the Runner instantiated in it and drive
      each wake source alone: a packet or channel pass that advanced the journal (where the service
      already sends its hint); a receiver reporting `exited` or `unknown` on its output pipe, which the
      Runner owns and the service loop registers in its poll set; and a timer set to the earliest
      account reset a waiting unit needs. After each, compare what the pass offered with every assigned
      eligible unit (offered to the Runner with a selected host and account) and every next station of
      a unit whose run ended, and require nothing offered from a paused project. A build ending must
      lead to its review being offered with no other input. No loop pass starts from anything but those
      three sources, and no timer other than an account reset starts one; the service's own accept
      timeout and channel pass are unchanged and are not loop wake sources. Falsifier: Drop the launch
      pipe from the poll set; the review-offered row must fail.
    falsified_by: >
      Drop the launch pipe from the poll set; the review-offered row must fail.
  - id: AC5
    text: >
      Claim: A launch receiver that dies mid-run still wakes the loop, and its run is recorded
      `outcome_unknown` with its account slot freed. Set and completeness: Kill the receiver mid-run
      before it reports `exited` or `unknown`; the end of file on its launch pipe starts one loop pass,
      the run is recorded `outcome_unknown` under its original dispatch with its usage reservation
      retained, the account slot is free for the next dispatch, and the unit's next station is not
      offered as if the run had succeeded. Falsifier: Ignore end of file on the launch pipe when the
      receiver dies; the receiver-death row must fail.
    falsified_by: >
      Ignore end of file on the launch pipe when the receiver dies; the receiver-death row must fail.
  - id: AC6
    text: >
      Claim: The loop carries out the re-run-or-ask decision VELDO-0062 AC6 makes for a run that ended
      `account_limit`: it dispatches the same station again under a new dispatch identity on another
      account from the same accepted commit, or asks the owner whether to re-run, naming the calls. Set
      and completeness: End a real run as `account_limit` and feed VELDO-0062's decision its execution
      record (VELDO-0141). For a re-run decision observe one new dispatch of the same station, on
      another account of an engine the role allows, from the same accepted commit, and nothing sent to
      the exhausted account before its reported reset. For an ask decision (a record with a call to an
      MCP tool not marked read-only) observe one ordinary decision request to the project's owner
      (VELDO-0064) naming the calls and no dispatch until he answers; his yes dispatches it as a re-run
      would, and his no leaves the unit stopped. Falsifier: Re-dispatch a run whose decision is to ask
      the owner; the ask-before-rerun row must fail.
    falsified_by: >
      Re-dispatch a run whose decision is to ask the owner; the ask-before-rerun row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Installed construction and independent review call the real qualified Claude Code and Codex
adapters instead of stopping at the unimplemented model seams.

## Context

W92 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5 (moved from stage 1
by revision 4, because AC6 reads the stage 5 execution record of VELDO-0141).
Section 4 of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md)
places the Runner and the factory loop in the authority service.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: the installed build and review entry points call the qualified Claude Code and Codex adapters for
  a dispatched unit; the Runner and factory loop run inside the authority service, and each commit,
  each run's end on the launch pipe and each account reset wakes one pass that offers every eligible
  unit and next station; a run stopped by its account's limit is dispatched again on another account
  or put to the owner as VELDO-0062 decides.
- Threat model: a production build or review that depends on an injected callable; a review with the builder's
  context, the builder's identity or no verdict artifact counted as passing; success manufactured
  from an exit code; a build ending that wakes nothing, or a receiver that died leaving its unit and
  account slot stuck; a paused project's unit offered; a loop pass started by polling or by any timer but an account reset;
  a run that may have written through an MCP server re-run without asking, or an account-limited run
  sent back to the exhausted account. The owner's account, the
  store and the installed engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery of an interrupted pass and restart matrices (Release 2); more than one scheduling
  instance; forged rows in our own store and files planted in the installed directory.

## Notes

Inspected at the revision-3 baseline: LiveLoop.build and LiveLoop.review in .veldo/executor.py
and LiveReviewer.review in .veldo/dispatch.py refuse without injected implementations. Engine
qualification alone does not connect these entry points. This concern wires the production
default; it does not relax their refusal when no qualified configuration exists.

Handed on by VELDO-0050 (its review, 2026-09-24): the proof service (.veldo/control_proof.py) is
built but no production path wires one yet, so the dispatcher's default LiveLoop stops every floor
build at proof with missing_authority:proof_service. This concern wires a ProofService into the
dispatcher's LiveLoop; makes the floor's accept_build in .veldo/dispatch.py resolve the stored
bundle rather than the committed manifest alone; makes the executor refuse, with the floor
enabled, a hook set whose accept_proof returns nothing; and has the real build adapter's proof
carry spec_revision and evidence entries that name a path and a digest.

Handed on by VELDO-0067 (its review, 2026-09-24): each production local adapter's configured argv
starts with the key custody wrapper (control_keys_custody.confined, naming the protected key
directory), so a worker cannot read an edge key file directly.

Handed on by VELDO-0042 (its reviews, 2026-09-24): the launch path calls control_clone's
record_group with the worker's VELDO-0040 group before the engine runs, and uses a new dispatch id
for every launch, because a clone whose entrance has no recorded group, or was relaunched under the
same dispatch in a second group, stays in use until the host reboots. Any unconfined Git run over a
used clone (collecting a result) treats that clone's .git/config as hostile, since a worker can write
hooks or core.fsmonitor there.

The factory loop (revision 4). Nothing in the running service starts a dispatch today: the service
does not instantiate the Runner, and it sends its post-commit hint only after a packet or channel
pass it processed itself (`hint_after` in `control_service.py`), while the launch receiver is a
separate process that commits a run's acceptance and termination itself, so a build ending would
wake nothing. The loop and the Runner live inside the authority service, the one scheduling
instance (VELDO-0047); the Runner still starts the launch receiver as a separate process. A paused
project's units are refused by the VELDO-0052 Gate check VELDO-0076 added, so the loop offers none
of them. Starting a PM cycle for a project with new relevant input is VELDO-0088's, run from the same
pass.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 1, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), section 4(e). New AC4: the
Runner and factory loop run inside the authority service and a pass runs on each journal-advancing
packet or pass, each run's end on the launch pipe (including a receiver that died) and account reset
timers, offering every assigned eligible unit and next station and none of a paused project; nothing
polls. Its falsifier drops the launch pipe from the poll set. depends_on adds VELDO-0039, VELDO-0047
and VELDO-0062, and the footprint adds the service, the Runner and the launch receiver. A What the
reviewer judges section is added. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: "nothing polls" is scoped to the factory loop (its passes run
only on the three wake sources, and no timer other than an account reset starts one); the service's own
accept timeout and channel pass exist and are unchanged. AC4's double falsifier is split: AC4 keeps the
launch pipe dropped from the poll set, and new AC5 is the receiver that dies, with end of file ignored as
its falsifier. New AC6 carries out VELDO-0062 AC6's decision for an account-limited run (the re-dispatch
and the question to the owner) with its own falsifier; depends_on adds VELDO-0064 (the question) and
VELDO-0141 (the record the decision reads), so the work item moves to stage 5. The footprint drops
`control_runner`, which does not exist; the Runner is class `Runner` in `control_launch`. Status
unchanged.
