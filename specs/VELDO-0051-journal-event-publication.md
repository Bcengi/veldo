---
schema: veldo.spec/v1
id: VELDO-0051
title: Canonical event vocabulary and journal-derived publication
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W36
plan_revision: 4
depends_on: [VELDO-0023, VELDO-0035, VELDO-0050]
placement: [distribution, metrics, contracts, loop]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/events.py"
  - ".veldo/events.py"
  - "packs/*/.veldo/events.py"
  - "engine/.veldo/validate.py"
  - ".veldo/validate.py"
  - "packs/*/.veldo/validate.py"
  - "engine/.veldo/control_event*.py"
  - ".veldo/control_event*.py"
  - "packs/*/.veldo/control_event*.py"
  - "scripts/suites/*_veldo_0051_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0051-journal-event-publication.md"
  - "specs/index.md"
  - "proof/VELDO-0051/*"
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/11_inbound_command_receipt_reconcile.py"
  - "engine/.veldo/spend.py"
  - ".veldo/spend.py"
  - "engine/.veldo/judgment_load.py"
  - ".veldo/judgment_load.py"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "scripts/suites/15_warp_1407_judgment_load.py"
behavior_bearing: true
observability:
  logs: >
    Record the operation, domain, repository, unit or request identity, accepted input versions,
    outcome and named refusal without secrets.
  metrics: >
    Count accepted and refused operations and expose current pending work for this specification.
  traces: >
    Join accepted inputs, actual service observations and resulting authority records by identity.
  error_taxonomy: >
    Distinguish invalid input, missing authority, stale subject, unavailable service,
    missing evidence and unknown outcome where applicable; never label unknown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Enabled event producers and validators use the same canonical vocabulary. Set and
      completeness: Enumerate registered journey events and preserved historical schema spellings,
      serialize each actual owner event into JSONL and validate in another process; unknown
      type/schema and type substitution refuse. Falsifier: Remove run.done from validator
      recognition while keeping its producer; the vocabulary round trip must fail.
    falsified_by: >
      Remove run.done from validator recognition while keeping its producer; the vocabulary round
      trip must fail.
  - id: AC2
    text: >
      Claim: The event projection follows the committed journal in order at an explicit watermark.
      Set and completeness: Materialize the enabled single-domain event prefix once through the
      actual projector; compare event identity/order, stored watermark and unchanged historical
      bytes with the authoritative sequence. Falsifier: Skip a committed event while advancing the
      watermark; the prefix comparison must fail.
    falsified_by: >
      Skip a committed event while advancing the watermark; the prefix comparison must fail.
  - id: AC3
    text: >
      Claim: Only a confirmed landing receipt can produce spec.shipped for its exact unit and
      dispatch. Set and completeness: Exercise direct emit, build-only, wrong-dispatch receipt,
      unconfirmed remote landing and valid confirmed landing with explicit domain/repository
      coordinates; inspect actual journal and projection. Falsifier: Permit direct spec.shipped
      after build-only; the completion-owner check must fail.
    falsified_by: >
      Permit direct spec.shipped after build-only; the completion-owner check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Canonical event vocabulary and journal-derived publication. Deliver the normal function needed by the running factory journey.

## Context

W36 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: every enabled producer and the validator share one canonical event vocabulary, with the
  historical spellings preserved; each owner event serializes to JSONL and validates in another
  process. The projector follows the committed journal of the enabled domain in order and stores an
  explicit watermark, leaving historical bytes unchanged. spec.shipped comes only from a confirmed
  landing receipt for its exact unit and dispatch.
- Threat model: an event type or schema the validator does not know, or one type substituted for
  another; a projection that skips an event while advancing its watermark, or rewrites historical
  bytes; and spec.shipped produced by a direct emit, a build-only run, a receipt for another dispatch or
  an unconfirmed remote landing. The owner's account, the store and the journal signer are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); several
  projectors, two clones, crash replay and replica-failure recovery (Release 2, see History); the
  multi-repository matrix (Release 4); forged rows in our own store, files planted in the installed
  directory and resource exhaustion by our own account.

## Notes

One canonical event vocabulary includes every enabled producer and preserves historical
spellings. The legacy verdict projector is descriptive, not authenticated by its producer
string. Local journal commit is sufficient under amended C3, but source completion still
requires confirmed remote landing.

Implement canonical engine assets with synchronized installed copies where applicable. Register
every asset this journey actually installs. Derive executable check registrations from each
criterion's declared set; retain the actual observations and each driven negative-control diff
and failing row. Real stores, files, processes, Git and signatures are required where named.
Live engine/channel qualification cannot be replaced by model-response or authorization fixtures.
Current authorization, independent engineering review, enforceable pre-call spend caps and exact
tested-tree landing remain mandatory at the boundaries this concern consumes.

## History

2026-09-22, PLAN-0019 revision 3, Release 1 stage 1: the owner narrowed this work under
Telegram 28848 (function now, robustness/recovery later), with Mac retained by 28852 and
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2 multi-
projector/two-clone/crash replay and AC3 replica-failure recovery moved to Release 2; multi-
repository matrix moved to Release 4. Vocabulary and receipt-derived completion remain. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.

2026-09-24, build: the footprint names scripts/check_teeth_mutations.py, where this work's
falsifiers are registered as finding 51, and scripts/suites/11_inbound_command_receipt_reconcile.py,
whose WARP-1208 row pinned the validator's vocabulary as an exact set. One canonical vocabulary
necessarily adds the run, request and decision types the emitter already wrote, so that row now
requires the previously recognized set to be kept (an inclusion), which is the additivity it
states. No criterion, status or historical proof changed.

2026-09-24: implemented on branch build-veldo-0051 (built on 8231708, origin/main merged). Two new
modules with byte-identical engine copies: control_event_vocabulary.py, the one registry of the 31
event types, their owners and the schema spellings, which events.py and validate.py both load; and
control_event_projection.py, which publishes spec.shipped from the committed journal in order at a
stored watermark, only for a confirmed landing receipt for its exact unit and dispatch. events.py
makes spec.shipped projection-owned and refuses a substituted type; init_scaffold.py lays both
modules. Suite 66_veldo_0051_events has 7 criterion rows and 3 region rows. Finding 51 in
scripts/check_teeth_mutations.py registers 18 mutations, among them each criterion's declared
falsifier, all rejected, in the normal shell and under the gate's mutation-stage environment.
scripts/suites/manifest.json gains suite 66, and requires.json is regenerated. Every criterion row
was recorded red at 8231708. The proof README was written by the lead after the builder was cut off
by a usage limit. The status stays ready. Proof: proof/VELDO-0051/.

2026-09-24, review fix: this change broke a landed producer. The spend recorder (.veldo/spend.py,
WARP-0733) wrote each spend record as a hand-emitted spec.shipped, which this work made
projection-owned, so `spend.py record` exited 1 where it exited 0 at 8231708 and spend actuals
stopped being recorded. Spend is not completion: the vocabulary now registers spend.recorded,
owned by spend.py, which writes it under its own producer. The footprint adds exactly the paths
this fix changes: spend.py and judgment_load.py (the one reader of spend actuals keyed on the event
type, which now reads spend.recorded and the historical spec.shipped spend lines as the same bulk
kind) with their engine copies, suite 01, whose injected emitter admitted any type and so masked the
refusal, and suite 1407, whose drift guard pinned the recorder's old type. No hand path to
spec.shipped is reopened. Suite 66 adds the spend recorder to the AC1 producer list and a row,
events/spend-recorded, that runs the real `spend.py record`; finding 51 registers four more
mutations. No criterion or status changed.
