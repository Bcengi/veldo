---
schema: veldo.spec/v1
id: VELDO-0154
title: The factory loop runs inside the authority service, woken only by commits, run ends and account resets, and re-dispatches or asks the owner at an account limit
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W114
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0047, VELDO-0062, VELDO-0064, VELDO-0076, VELDO-0129, VELDO-0141, VELDO-0160]
placement: [loop, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "scripts/suites/*_veldo_0154_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0154-factory-loop-in-the-authority-service.md"
  - "specs/index.md"
  - "proof/VELDO-0154/*"
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
      Claim: The Runner and factory loop run inside the authority service; a loop pass runs on each of
      its three wake sources (each journal-advancing packet or pass, each run's end seen on the Runner's
      launch pipe, and an account reset timer), offers every assigned eligible unit and every next
      station, and stops offering a paused project's units. Set and
      completeness: Start the installed authority service with the Runner instantiated in it and drive
      each wake source alone: a packet or channel pass that advanced the journal (where the service
      already sends its hint); a receiver reporting `exited` or `unknown` on its output pipe, which the
      Runner owns and the service loop registers in its poll set; and a timer set to the earliest
      account reset a waiting unit needs. After each, compare what the pass offered with every assigned
      eligible unit (offered to the Runner with a selected host and account) and every next station of
      a unit whose run ended, and require nothing offered from a paused project. A build ending must
      lead to its review being offered with no other input. That nothing else starts a pass is AC4.
      Falsifier: Drop the launch pipe from the poll set; the review-offered row must fail.
    falsified_by: >
      Drop the launch pipe from the poll set; the review-offered row must fail.
  - id: AC2
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
  - id: AC3
    text: >
      Claim: The loop carries out the re-run-or-ask decision VELDO-0160 AC3 makes for a run that ended
      `account_limit`: it dispatches the same station again under a new dispatch identity on another
      account from the same accepted commit, or asks the owner whether to re-run, naming the calls. Set
      and completeness: End a real run as `account_limit` and feed VELDO-0160's decision its execution
      record (VELDO-0141). For a re-run decision observe one new dispatch of the same station, on
      another account of an engine the role allows, from the same accepted commit, and nothing sent to
      the exhausted account before its reported reset. For an ask decision (a record with a call to an
      MCP tool not marked read-only) observe one ordinary decision request to the project's owner
      (VELDO-0064) naming the calls and no dispatch until he answers; his yes dispatches it as a re-run
      would, and his no leaves the unit stopped. A dispatch whose configuration names no catalog revision,
      as every dispatch does until VELDO-0127 is built, has no tool marked read-only, so every MCP call in
      its record decides ask. Falsifier: Re-dispatch a run whose decision is to ask the owner; the
      ask-before-rerun row must fail.
    falsified_by: >
      Re-dispatch a run whose decision is to ask the owner; the ask-before-rerun row must fail.
  - id: AC4
    text: >
      Claim: A loop pass starts only from its three wake sources; no timer other than an account reset
      starts one, and the factory loop never polls. Set and completeness: Keep the installed authority
      service running with a unit waiting for an account whose reported reset is later, with no journal
      advance and no run ending, for longer than every interval the service uses, and count loop passes:
      none starts, while the service's own accept timeout and channel pass run unchanged and start no loop
      pass; then let the reset time arrive and observe exactly one pass at it. Falsifier: Start a loop
      pass from a periodic timer in the service loop; the no-other-timer row must fail.
    falsified_by: >
      Start a loop pass from a periodic timer in the service loop; the no-other-timer row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

The factory loop and the Runner run inside the authority service and start work on their own: each
commit, each run's end and each account reset wakes one pass that offers every eligible unit and next
station, a receiver that dies still frees its account slot, and a run stopped by its account's limit
is dispatched again on another account or put to the owner.

## Context

W114 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5, because AC3 reads
the stage 5 execution record of VELDO-0141. Section 4 of the approved
[operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram 29162)
places the Runner and the factory loop in the authority service. These were VELDO-0129's AC4 to AC6,
split out on the review of revision 4 so each specification keeps one concern: VELDO-0129 owns real
build and review through the Runner, this specification the factory loop that dispatches them. The
[design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22 scope amendments.
This new specification is draft; authoring it supplies neither implementation proof nor operational
activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. The real build and
review adapters are VELDO-0129's. No existing specification status, implementation, test, runtime
policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: the Runner and factory loop run inside the authority service, and each commit, each
  run's end on the launch pipe and each account reset wakes one pass that offers every eligible unit
  and next station; a run stopped by its account's limit is dispatched again on another account or put
  to the owner as VELDO-0160 decides.
- Threat model: a build ending that wakes nothing, or a receiver that died leaving its unit and account
  slot stuck; a paused project's unit offered; a loop pass started by polling or by any timer but an
  account reset; a run that may have written through an MCP server re-run without asking, or an
  account-limited run sent back to the exhausted account. The owner's account, the store and the
  installed engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery of an
  interrupted pass and restart matrices (Release 2); more than one scheduling instance; forged rows in
  our own store and files planted in the installed directory.

## Notes

Nothing in the running service starts a dispatch today: the service does not instantiate the Runner,
and it sends its post-commit hint only after a packet or channel pass it processed itself
(`hint_after` in `control_service.py`), while the launch receiver is a separate process that commits a
run's acceptance and termination itself, so a build ending would wake nothing. The loop and the Runner
live inside the authority service, the one scheduling instance (VELDO-0047); the Runner still starts
the launch receiver as a separate process. A paused project's units are refused by the VELDO-0052 Gate
check VELDO-0076 added, so the loop offers none of them, and this specification depends on VELDO-0076
for that pause. It does not depend on the catalog (VELDO-0144), which the design's section 12 builds
after it: with no catalog revision no tool is marked read-only and every MCP call asks the owner, and
once VELDO-0127 is built the dispatch's configuration names the catalog revisions whose marks the
decision reads. Starting a PM cycle for a project with new
relevant input is VELDO-0088's, run from the same pass. The Runner is class `Runner` in
`control_launch`; this concern registers its launch pipe in the service loop's poll set and dispatches
through it, while VELDO-0129 owns what a build or review run does once launched.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready; this draft does not amend the architecture contract. Inventory
every asset the selected journey installs. Compare executable registrations to each criterion's
declared universe, observe the real named interfaces, and retain the driven negative-control diff and
named failed row. Fixtures cannot certify real platform, engine or host behavior. Required evidence
labels describe future implementation proof, not tests run by this writing revision.

## History

2026-09-25: split from VELDO-0129 (its former AC4, AC5 and AC6, now AC1, AC2 and AC3, criterion text
and falsifiers unchanged) on the review of PLAN-0019 revision 4, so each specification keeps one
concern of at most about four criteria. The service, the Runner's launch pipe, the dependencies on
VELDO-0039, VELDO-0047, VELDO-0062, VELDO-0064 and VELDO-0141, the factory loop Notes and the loop's
part of What the reviewer judges come from VELDO-0129, which keeps VELDO-0039 and `control_launch` as
well, and this specification depends on VELDO-0129 for the real build and review it dispatches.
A draft: only the owner marks a specification ready.

2026-09-25, PLAN-0019 revision 4, third review: the re-run-or-ask decision moved from VELDO-0062 AC6 to
VELDO-0160 AC3, so AC3 names it there and depends_on adds VELDO-0160, which also owns the account
selection and rate-limit windows the reset timer of AC1 reads. Criterion meaning unchanged.

2026-09-25, PLAN-0019 revision 4, third review: depends_on adds VELDO-0076, whose pause AC1 relies on,
and AC3 and the Notes state that with no catalog every MCP call decides ask, so this stage 1 item does not
wait for the stage 2 catalog VELDO-0144.

2026-09-25, PLAN-0019 revision 4, third review: AC1's claim that no timer other than an account reset
starts a pass had no falsifier of its own, so it is new AC4 with one (a periodic timer that starts a
pass reds the no-other-timer row); AC1 keeps the wake sources and the launch-pipe falsifier. Criterion
meaning unchanged.

2026-09-25, PLAN-0019 revision 4, fourth review: AC3 and the Notes name VELDO-0127, not VELDO-0144, as the
specification after which a dispatch's configuration names catalog revisions, because the configuration
a dispatch records is VELDO-0127's; the catalog alone names no revision on a dispatch. Criterion meaning
unchanged.
