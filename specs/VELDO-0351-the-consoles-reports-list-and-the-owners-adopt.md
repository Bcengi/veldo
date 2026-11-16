---
schema: veldo.spec/v1
id: VELDO-0351
title: "The console's Reports list and the owner's Adopt"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0315, VELDO-0319]
placement: [engine, loop]
protected_paths: ["scripts/gate_unconfined.json"]
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/.veldo/control_api_models.py"
  - ".veldo/control_api_models.py"
  - "engine/.veldo/control_api_authority.py"
  - ".veldo/control_api_authority.py"
  - "engine/.veldo/control_api_assertion.py"
  - ".veldo/control_api_assertion.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/api/reads.ts"
  - "engine/ui/src/api/actions.ts"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/docs/views/space.md"
  - "engine/ui/e2e/**"
  - "scripts/suites/*_veldo_0351_*.py"
  - "scripts/suites/71_veldo_0130_api.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/gate_unconfined.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0351-the-consoles-reports-list-and-the-owners-adopt.md"
  - "specs/VELDO-0315-reconcile-at-start-and-on-demand.md"
  - "specs/index.md"
  - "proof/VELDO-0351/**"
behavior_bearing: true
observability:
  logs: >
    Each Adopt is one signed command in the journal, with the owner who sent it and the owner the thing
    was given. Reads write nothing.
  error_taxonomy: >
    unauthorized:not_owner for an Adopt from a member who is not the owner; stale_version:space_item for a
    report that changed since the screen showed it; space_item_exists for a thing that already has an
    owner; the refusals of declare for a locator that is protected or outside every known root;
    unavailable_service:space_ledger with no ledger.
acceptance_criteria:
  - id: AC1
    text: >
      The read space.reports lists every thing reconcile found and could not give an owner: its kind, its
      locator, its size, what was found, and the owner a rule proposes when one does. It is made from the
      item records that have a report and no owner, in one pass over those records. A member whose scope
      is not the whole factory is served none of them, because a report names no project
    falsified_by: >
      List only the reports that have a proposed owner; the row's scratch folder that no rule proposes an
      owner for is not listed and the row fails
  - id: AC2
    text: >
      Adopt is the owner's signed command. It names one report at the version the screen showed and the
      owner the thing is given: a project, a plain repository or no project, and a ticket when the owner
      names one. The Ledger turns that report record into an item in state present with adopted true and
      writes who adopted it from the principal it verified itself inside the transaction, as it does for
      Abandon. A session without the owner's passkey, a member who is not the owner, a version that is
      not the record's, and a thing that already has an owner are each refused with nothing written.
      Reconcile's own adopt, by the rule that proved the owner, is unchanged
    falsified_by: >
      Each of these turns a row of its own red. Take the adopting owner from the command's parameters:
      the row sends Adopt as a member who is not the owner and names the owner, and the thing is adopted.
      Accept Adopt as a plain route with no signed assertion: the unsigned row succeeds
  - id: AC3
    text: >
      The Space screen has a Reports section with one row per reported thing and an Adopt action on each
      row, with the proposed owner filled in when there is one. After an Adopt the row leaves Reports and
      the thing is counted in the usage table under its owner, from the record stream and without a
      reload. Adopt removes nothing: the adopted item meets every rule at its next event. A refused Adopt
      leaves the row in place and says why in words
    falsified_by: >
      Drop the row in the browser when the button is pressed, without reading again; the row whose Adopt
      the Ledger refuses as stale shows the report gone and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The console has no Reports section and no Adopt; reconcile still writes its reports
  and still adopts by rule, and nothing that was adopted is changed back.
---

## Intent

Reconcile reports things it finds on disk that no rule can give an owner. Today nobody can act on such
a report from the console: the screen does not list them, and no command lets the owner say whose a
thing is. This ticket adds the list and the owner's Adopt.

## Context

Found by the independent review of VELDO-0319 (review-veldo-0319.md, the not-built list): "The
reported-things list with Adopt (space.reports read, space.adopt) is owned by NO ticket."

Which spec introduces Adopt's ledger command: none introduces the owner's. The Ledger's adopt
transition is VELDO-0297's and reconcile is its only caller (VELDO-0315). It takes the rule that proved
the owner, and it runs under the authority's own principal. control_space.py already names space_adopt
among the owner's actions, so no host principal may sign one, but no command lets the owner give a
reported thing an owner: there is no operation in control_api_assertion.OPERATIONS, no branch in the
authority, no action in control_api_models.ACTIONS and no service entry. Design 6.6 names the route
space.adopt and the read space.reports, design 10 names the section, and VELDO-0319's amended AC3 hands
Adopt "to the ticket that introduces its ledger command". This is that ticket.

## Design

The design is docs/design/VELDO-0295-design.md. Sections this ticket builds: 6.1 (the adopt and report
rows), 6.6 (space.reports and space.adopt), 6.11 (the owner signs Adopt) and 10 (the Reports section).

The owner's form of adopt. The Ledger's adopt gains a second way in for the owner: in place of a rule,
the command carries the report's item and version, and the transition reads the owner behind the
command with the check Abandon already uses (the Ledger checks the owner itself). The item's adoption
field then holds who adopted it in place of a rule. A command that carries both a rule and an owner's
adoption is refused.

The command chain is the one Abandon uses: an operation in control_api_assertion.py, a branch in
control_api_authority.py, an action in control_api_models.py and a service entry in control_service.py
beside space_abandon. Nothing new reaches the Ledger another way.

The read is built from item records and holds no journal scan (the review's finding F2 on space.removed
is the reason this is said): it selects the items whose owner is null and whose report is set, through
an index the Ledger installs when it opens, as VELDO-0319's fix round did for removals. This ticket
builds the read and the reported-things part only. Design 6.6 also lists repositories whose hooks are
missing under space.reports; VELDO-0329 has reconcile list them in its result, which is not stored, so
no record holds them yet and this ticket does not show them.

Rows this ticket changes. scripts/suites/71_veldo_0130_api.py, session/forgery-refused: bodies gains
space.adopt, as it gained space.abandon. No row of scripts/suites/150_veldo_0319_space_screen.py changes:
VELDO-0319's amendment restates ac3/no-dead-route and ac3/routes-signed as properties (every space
route reaches a command that has a transition; every space read is a GET route with no field), and
space.adopt and space.reports meet them. The teeth cases of finding 319 anchored in
control_api_models.py, control_api.py and control_api_authority.py keep their anchors; one whose line
this change moves is re-anchored on the same code with the same target row, and the teeth of finding
319 are run.

The browser rows live in a spec file of their own, engine/ui/e2e/space-reports.spec.ts, run by this
ticket's own UI suite. They are not added to e2e/space.spec.ts, because row ui/api-only of
150_veldo_0319_space_ui requires that file to hold exactly that suite's rows.

Protected path. This ticket's UI suite needs system Chrome, so it needs an entry in
scripts/gate_unconfined.json, which is protected: the owner approves that entry at landing.

Footprint. The Ledger, the control API chain with synced copies, the Space screen's files, the ticket's
suites, proof and spec, suite 71's one row, and VELDO-0315's spec for the History line that names this
ticket as the owner of Adopt.

Order. VELDO-0325 (gate scripts that lack the space steps) and VELDO-0346 (kept work missing) add their
parts to space.reports, so both depend on this ticket. VELDO-0352 follows this ticket because both add
a read and a section to the same files.

## History

- 2026-11-16: drafted from the review of VELDO-0319 and the lead's decisions of that day
  (space-footprint-decisions-1116.md). Not filed. The number was checked free on every ref of the
  repository: nothing names 0351 to 0356.
- 2026-11-16: reviewed. The 0319 space screen suite left the footprint (its two shared rows are
  properties after VELDO-0319's amendment); suite 71's row session/forgery-refused is named; the browser
  rows get a spec file of their own; the read's index and the 319 teeth anchors are stated; the order
  with VELDO-0325, 0346 and 0352 is stated.
