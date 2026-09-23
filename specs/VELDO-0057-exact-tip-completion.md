---
schema: veldo.spec/v1
id: VELDO-0057
title: Exact-tip publication, lost acknowledgement recovery, and completion receipt
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W42
plan_revision: 3
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

Exact-tip publication, lost acknowledgement recovery, and completion receipt. Deliver the normal function needed by the running factory journey.

## Context

W42 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its dated
2026-09-22 scope amendments. This revision changes the work contract, not its status,
implementation or historical evidence. Risk and approval requirements remain unchanged.

## Out of scope

The deferred obligations in History are not part of this Release 1 criterion or evidence universe.
No automatic recovery, extra channel activation or broader host qualification is implied.

## Notes

VELDO-0056 supplies candidates and 0058 supplies the final trusted external observation.
Remote confirmation is required even though off-host receipt replication moves to Release 2.
Lost or ambiguous publication stays stopped under its original identity; no recovery is
implemented by this MVP spec.

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
