---
schema: veldo.spec/v1
id: VELDO-0241
title: A unit's process is a versioned workflow revision chosen per project or per kind of work, today's code process ships as the default definition unchanged, and no definition can skip the owner's approval
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0042, VELDO-0057, VELDO-0058, VELDO-0068, VELDO-0132, VELDO-0148, VELDO-0154, VELDO-0185]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "packs/*/.veldo/control_workflow*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_landing_station.py"
  - ".veldo/control_landing_station.py"
  - "engine/.veldo/control_project.py"
  - ".veldo/control_project.py"
  - "engine/.veldo/workflows/*.json"
  - ".veldo/workflows/*.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0241_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0241-a-units-process-is-a-versioned-workflow-revision.md"
  - "specs/index.md"
  - "proof/VELDO-0241/*"
behavior_bearing: true
observability:
  logs: >
    Every station a unit is offered records the workflow id, version and digest the unit is bound to and
    the node it runs; a binding change records the project, the kind of work, the old and new revision and
    the owner's command id; a refused save records every named problem. No secret is logged.
  metrics: >
    Count units by bound workflow revision and node, saves accepted and refused by problem name, and
    units whose binding was missing or stale.
  traces: >
    Join each dispatch, gate observation, approval and land record of a unit to the one revision the unit
    recorded at its first station.
  error_taxonomy: >
    Keep VELDO-0132's names. A definition where land, deliver, publish or deploy is reachable without the
    owner's approval is invalid_input:missing_owner_approval:<node>; an approval with a subject-changing
    step between it and the outward step it names is invalid_input:approval_not_last:<node>; a binding to a
    revision that does not exist or is not accepted is missing_workflow; a binding change by anyone but the
    project owner is refused as today's project commands refuse. None is a completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: today's code process ships as the default definition `code` (build, review, gate, the owner's
      landing approval, land, with VELDO-0148's re-land, re-build on conflict and re-approval edges as
      bounded transitions) and a project with no binding runs it with exactly today's behavior. Set and
      completeness: the Line's next-station decision reads the unit's bound revision instead of the fixed
      NEXT_STATION table and the land station's after-land rule; on the existing fixtures the sequence of
      dispatch contracts, gate observations, approval requests and land records is identical before and
      after, field by field except the added revision fields; every existing suite in scripts/suites passes
      with no change to its file.
    falsified_by: >
      Swap review and build in the shipped `code` definition; the default-equivalence row must fail on the
      first unit.
  - id: AC2
    text: >
      Claim: the owner's approval is mandatory in every definition and is checked at save. Set: a node of an
      outward step kind (land here; deliver, publish and deploy as VELDO-0242 and VELDO-0244 register them)
      is reached only through an owner_approval node that names it, on every path from the entry, and no
      step that changes the subject (build, render, generate) lies between that approval and the outward
      node. A definition that breaks either rule is refused at save with the named problem and no revision
      is written; the approval node itself settles through the ordinary owner decision (VELDO-0068) bound to
      the exact subject (VELDO-0057), never through a workflow edge. Rows: removing the approval, routing a
      side edge around it and placing a build after it are each refused.
    falsified_by: >
      Accept a definition whose land node is reachable by one path that skips the owner_approval node; the
      save-refusal row must fail.
  - id: AC3
    text: >
      Claim: the process is chosen per project, or per kind of work within a project, and a unit records the
      revision it ran. Set: the project record holds a binding from kind of work (default when the unit names
      none) to an accepted workflow id and version, set only by the project owner's signed command; a unit
      records that id, version and digest at its first station and every later station reads that record,
      not the head. Saving a new revision or changing the binding while a unit runs leaves that unit on its
      recorded revision; the next new unit takes the new one.
    falsified_by: >
      Read the workflow head at each station instead of the unit's recorded revision; the pinned-revision row
      must fail when a new revision is saved mid-unit.
required_evidence: [unit, integration]
rollback: >
  Revert the change; the Line returns to its fixed stations. Recorded bindings and unit revision fields stay
  in the store and are ignored. No automatic rollback, retry or recovery is authorized.
---

## Intent

A unit's process stops being code. Today the Line hardcodes build then review, and the land station
hardcodes what follows a land. This makes the process a versioned workflow revision (VELDO-0132) that the
project, or a kind of work in the project, is bound to, so code, documents, media, deploys and social posts
are different definitions run by the same engine, and the owner's approval before anything leaves the
factory cannot be configured away.

## Context

Owner, Telegram 39069 to 39071 (agreed): "do we need a workflow? Agent factory might have different
processes for different things (code vs document vs image), are these hardcoded now ... this would allow
some more complex things to be configured, like social media posts that would configure more complex
workflow instead of hardcoding things." Telegram 39067 lifted PLAN-0019 NG3 and NG2 for this work; the
plan's amendment of 2026-11-04 records the scope. VELDO-0132 already stores immutable workflow revisions
with registered step kinds and runs one pinned revision per LangGraph cycle; this spec registers the
unit's station kinds (build, review, gate, owner_approval, land) and makes the Line and the land station
read the unit's revision. The local landing destination (draft VELDO-0235) is a property of the land step
and is unchanged by this spec. The canvas that edits these definitions is VELDO-0246.

## Out of scope

The document, media, deploy, publish and schedule step kinds (VELDO-0242 to VELDO-0245). Batch landing.
Any change to how a single station runs: build, review, the gate, the approval and the land keep their
current specifications. Checkpoint recovery of a unit mid-definition beyond what the store already
records.

## What the reviewer judges

- Normal use: the owner binds a project, or one kind of work in it, to a saved revision; each new unit
  records that revision at its first station and runs node by node, every node still going through the
  role, Gate and result checks; with no binding the `code` definition runs and nothing observable changes.
- Threat model: a definition that reaches land without the owner's approval, by removal, a side edge or a
  build placed after the approval; a running unit that silently changes process because a revision was
  saved; a binding changed by someone other than the project's owner; a definition that asserts completion
  itself (refused by VELDO-0132 AC4).
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery after a
  crash between two nodes beyond today's record.

## Notes

The default definition is data in the engine's workflows directory, laid by the scaffold and saved as an
accepted revision at setup, so "the code process" is visible and editable on the canvas like any other.
Outward step kinds are marked in STEP_KINDS (outward: true); the save check walks every path from the
entry, so later kinds inherit the rule without new code. The approval's subject is the one VELDO-0057 and
VELDO-0148 bind today; a definition chooses where the approval sits, never what it binds to.

## History

2026-11-04: new draft under owner Telegram 39069 to 39071 (agreed: a unit's process is a workflow per kind
of work) and 39067 (NG2 and NG3 lifted, recorded in PLAN-0019 the same day). Standalone; no plan work item.
The parity report's tickets T7, T9 and T16 become step types in VELDO-0242 to VELDO-0245 on top of this.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended by the owner, Telegram 39144 ("Yes", to 39143): under VELDO-0253 the installation loader becomes the only writer of workflow revisions (copies keyed by digest, pins read those copies) and the binding moves to the project file in the installation repository. That change is built by VELDO-0253 (its note proof/VELDO-0253/amend-0241.md); this spec is landed as built.

2026-11-04: plan consistency review (owner Telegram 39145; research/veldo-plan-consistency-review-2026-11-04.md, findings A23, A24, D7, E5) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md, R1, R4). This spec is landed as built and its text is not edited; the changes are carried by follow-up tickets. VELDO-0253 (R1): definitions and bindings live in the installation repository and the loader is the only writer of revisions, so AC3's binding in the project record set by signed command, the rollback's "stay in the store" and the Notes' "engine's workflows directory" are superseded as proof/VELDO-0253/amend-0241.md says, and only the `code` default stays product data. VELDO-0252 with VELDO-0249 as amended (R4): an owner_approval node naming a step that makes an outside write settles as the approval service's approval of that exact request, matched once by the outside gate's check, never a second mechanism.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156).
