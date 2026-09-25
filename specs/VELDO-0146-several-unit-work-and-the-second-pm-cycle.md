---
schema: veldo.spec/v1
id: VELDO-0146
title: Work of several units gets a separate elaboration run and a second PM cycle that stages the units against the published requirements
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W106
plan_revision: 4
depends_on: [VELDO-0085, VELDO-0088, VELDO-0091, VELDO-0154]
placement: [contracts, loop, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_graph*.py"
  - ".veldo/control_graph*.py"
  - "packs/*/.veldo/control_graph*.py"
  - "engine/.veldo/control_workflow_cycle*.py"
  - ".veldo/control_workflow_cycle*.py"
  - "packs/*/.veldo/control_workflow_cycle*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0146_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0146-several-unit-work-and-the-second-pm-cycle.md"
  - "specs/index.md"
  - "proof/VELDO-0146/*"
behavior_bearing: true
observability:
  logs: >
    Record each cycle's judgment of one or several units, the elaboration dispatch it led to, the
    publication the second cycle read and each unit it staged, or the named refusal.
  metrics: >
    Count several-unit objectives, elaboration runs, second cycles and units staged per publication.
  traces: >
    Join the first cycle, the elaboration dispatch, the published requirements revision and the second
    cycle's staged units by identity.
  error_taxonomy: >
    Distinguish unpublished requirements, a unit the publication does not contain, a stale publication
    revision and a refused proposal; none stages a unit.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: When the PM judges the work to be several units, the cycle dispatches a separate elaboration
      run, and a second PM cycle stages the units only against the requirements that run published. Set
      and completeness: For an admitted objective the PM judges to be several units, run the first cycle
      on the default pipeline: its proposal names the decomposition, and the elaborate station dispatches
      one elaboration run through the Runner (VELDO-0039, VELDO-0091), with no unit staged by that cycle.
      After the requirements and specifications are published (VELDO-0085), the factory loop starts the
      second cycle from the new accepted snapshot, and its proposals stage the units. Falsifier: Stage the
      units of several-unit work in the first cycle, before its requirements are published; the
      second-cycle staging row must fail.
    falsified_by: >
      Stage the units of several-unit work in the first cycle, before its requirements are published; the
      second-cycle staging row must fail.
  - id: AC2
    text: >
      Claim: The second cycle stages every unit of the published decomposition, each bound to the
      published requirements revision it cites, and nothing the publication does not contain. Set and
      completeness: Compare the units the second cycle staged, with their staffing choices, to the
      published decomposition and its requirements revision; publish a new revision during the cycle and
      require the cycle's pending follow-up (VELDO-0088 AC3) to stage against it; propose a unit the
      publication does not contain and require its refusal by name, with the rest of that cycle's
      proposals stopped. Falsifier: Stage a unit the published decomposition does not contain; the
      published-units row must fail.
    falsified_by: >
      Stage a unit the published decomposition does not contain; the published-units row must fail.
required_evidence: [unit, integration]
rollback: >
  Treat every objective as one unit, as the thin VELDO-0088 does; cycle receipts, publications and staged
  units are kept. No automatic rollback is authorized.
---

## Intent

A piece of work too large for one unit needs its requirements and specifications written first, by an
elaboration run, and only then units staged against what was published.

## Context

W106 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 4 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs it: "work of several units gets a separate elaboration run and a second PM cycle that
stages the units against the published requirements." Its section 12 builds this as "the rest of
VELDO-0088" in stage 3 of the critical path, after the thin VELDO-0088 of stage 2. This specification is
that part of VELDO-0088's revision 4 amendment, split out because a specification ships whole.

## Out of scope

One-unit work (VELDO-0088); writing the requirements themselves (VELDO-0091); publication and its
concurrency (VELDO-0085); specialist selection (VELDO-0090); atomic proposal groups (VELDO-0092,
Release 2).

## What the reviewer judges

- Normal use: the owner asks for work the PM judges to be several units; one elaboration run writes and
  publishes the requirements and specifications, and a second PM cycle stages each unit against them.
- Threat model: a unit staged before the requirements it depends on are published, or bound to a stale
  publication revision; a unit staged that the publication does not contain; the elaboration done inside
  the cycle runner instead of as a dispatched run; a second cycle that never starts. The owner's account,
  the store and the installed runtime are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); persistent
  checkpoints and recovery (Release 2); forged rows in our own store and files planted in the installed
  directory.

## Notes

The first and second cycles are ordinary cycles of the one default pipeline revision, one cycle per
project with one bounded follow-up (VELDO-0088 AC3); proposals take effect one owning command at a time
as VELDO-0088 states.

## History

2026-09-25: split from VELDO-0088's revision 4 amendment (approved operating-model design, Telegram
29162, section 4(e)) on the review of PLAN-0019 revision 4, because a specification ships whole and the
design builds several-unit work in a later stage than one-unit work. The criterion text is that
amendment's several-unit clause, with a falsifier of its own for each part. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4 review: depends_on adds VELDO-0154, the factory loop that starts
the second cycle, split from VELDO-0129. Criteria unchanged; a draft.

2026-09-25, PLAN-0019 revision 4, third review: the footprint named `control_project_cycle*.py`, which
does not exist; the cycle runner is `.veldo/control_workflow_cycle.py`, so the footprint names
`control_workflow_cycle*.py`. Criteria and status unchanged.
