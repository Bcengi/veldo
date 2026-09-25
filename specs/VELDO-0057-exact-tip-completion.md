---
schema: veldo.spec/v1
id: VELDO-0057
title: Exact-tip publication and confirmed completion receipt
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W42
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0051, VELDO-0052, VELDO-0053, VELDO-0054, VELDO-0056, VELDO-0058]
placement: [distribution, fleet, contracts, metrics]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "packs/*/.veldo/lander.py"
  - "engine/.veldo/control_landing*.py"
  - ".veldo/control_landing*.py"
  - "packs/*/.veldo/control_landing*.py"
  - "scripts/suites/*_veldo_0057_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0057-exact-tip-completion.md"
  - "specs/index.md"
  - "proof/VELDO-0057/*"
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
      Claim: Publication compare-and-swaps the exact old remote tip to the verified candidate. Set
      and completeness: Run protected Git publication to a disposable bare remote using the recorded
      old tip, candidate commit/tree and receipt; move the remote tip before a second attempt and
      require refusal without overwrite. Falsifier: Publish without checking the exact old tip; the
      moved-tip refusal check must fail.
    falsified_by: >
      Publish without checking the exact old tip; the moved-tip refusal check must fail.
  - id: AC2
    text: >
      Claim: Publication validates current authority, applicable approval and the exact
      tested/reviewed subjects. Set and completeness: At the real effect boundary substitute
      approval, source, proof, candidate tree or current dependency version separately; each must
      refuse and preserve trunk. The valid current combination publishes. Falsifier: Accept an
      approval for a different candidate tree; the exact-subject check must fail.
    falsified_by: >
      Accept an approval for a different candidate tree; the exact-subject check must fail.
  - id: AC3
    text: >
      Claim: An unconfirmed publication cannot establish completion or authorize another attempt.
      Set and completeness: Present confirmed, failed and unknown target results to the original
      dispatch; observe exact remote evidence for success and a named stop for unknown without
      additional receive attempts. Falsifier: Create a new publication attempt for an unknown
      result; the repeat-attempt check must fail.
    falsified_by: >
      Create a new publication attempt for an unknown result; the repeat-attempt check must fail.
  - id: AC4
    text: >
      Claim: Completion is committed locally only after confirmed exact landing and records its full
      evidence chain. Set and completeness: Enumerate R76 implementation, proof, reviewed digests,
      old tip, candidate, tested tree, gate and final receipt bindings; corrupt each and test build-
      only, push-disabled and valid remote-confirmed results through work/plan/frontier readers.
      Falsifier: Complete after local finalize with push disabled; the remote-confirmation check
      must fail.
    falsified_by: >
      Complete after local finalize with push disabled; the remote-confirmation check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern, preserve accepted evidence and unresolved obligations,
  and require an explicit operations decision before using a prior compatible configuration.
---

## Intent

Exact-tip publication and confirmed completion receipt. Deliver the normal function needed by the running factory journey.

## Context

W42 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## What the reviewer judges

- Normal use: a landing candidate that VELDO-0056 prepared and VELDO-0058's trusted gate observed
  green is published by compare-and-swap from the exact recorded old remote tip to the verified
  candidate, only while current authority, the applicable approval and the exact tested and reviewed
  subjects (source, proof, candidate tree, dependency versions) all still hold. The remote's own
  answer decides: confirmed exact landing writes the confirmed-landing receipt for that exact unit
  and dispatch, with its full evidence chain, and then runs the VELDO-0051 projection, which alone
  derives spec.shipped; a failed or unknown result stops under its original identity.
- Threat model: a publication that overwrites a remote tip that moved; an approval, proof, source,
  tree or dependency version for a different subject accepted; an unknown or failed result treated
  as success or answered with a new publication attempt; completion recorded after a local finalize,
  with push disabled, from a build only, or with any link of the evidence chain corrupted; a unit
  shown as shipped by anything but the projection over a confirmed receipt. The owner's account, the
  installed engine, Git and the remote are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery of
  a lost or ambiguous publication and off-host receipt replication (Release 2); forged rows in our
  own store and files planted in the installed directory; a hostile gate process reaching the caller
  through the same account (the same-account class filed by VELDO-0040, VELDO-0058 and VELDO-0067).

## Notes

VELDO-0056 supplies candidates and 0058 supplies the final trusted external observation.
Remote confirmation is required even though off-host receipt replication moves to Release 2.
Lost or ambiguous publication stays stopped under its original identity; no recovery is
implemented by this MVP spec.

Handed on by VELDO-0051 (its review, 2026-09-24): nothing in the engine writes a confirmed-landing
receipt yet, and nothing runs the journal projection after a landing, so no unit can show as shipped
without a manual step. This concern writes the receipt for its exact unit and dispatch and then runs
the VELDO-0051 projection (.veldo/control_event_projection.py), which alone derives spec.shipped.

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
Telegram/API/UI scope and configured capabilities governed by 28857/28859. Old AC2
replacement-generation fencing, AC3 lost-ack recovery and AC4 replica-failure recovery moved
to Release 2. Current approval, exact-old-tip publication and confirmed landing remain. The
criteria, declared evidence universe, Context and Notes above now carry only the retained
function. No specification status or historical proof was changed.

2026-09-24, implementation: .veldo/control_landing.py (engine copy byte-identical) publishes the
exact tip through the protected effect executor, writes the confirmed-landing receipt and runs the
VELDO-0051 projection; .veldo/lander.py wires a factory land to it and leases every push on the
exact watermark. A confirmed publication of another unit or dispatch refuses as
binding_mismatch:publication/unit, an unconfirmed one as unknown_outcome. Suite 70, the red record
against b53e7b1, finding 57 (29 mutations) and proof/VELDO-0057/ carry the evidence. No
specification status was changed.

2026-09-24, first critical review: the publication's contract payload carries the unit revision
its approvals were checked for, and the receipt is about that revision. A unit whose revision moved
after its publication refuses as stale_subject:landing/revision and writes nothing, and the receipt
transition refuses a receipt about any other revision. A completion whose projection was refused
is not ok and names it (class:projection/reason), and a refusal naming another unit's dispatch no
longer reports that unit's publication as this one's. Suite 70 rows completion/revision-moved,
completion/projection-refused and completion/foreign-dispatch, the red record against cc300b6 and
finding 57 (33 mutations) carry the evidence. No specification status was changed.
