---
schema: veldo.spec/v1
id: VELDO-0312
title: "Ticket ended, project ended and worktree abandoned"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/ui/src/api/routes.json"
  - "scripts/suites/*_veldo_0312_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0312-ticket-ended-project-ended-and-worktree-abandoned.md"
  - "specs/index.md"
  - "proof/VELDO-0312/**"
behavior_bearing: true
observability:
  logs: >
    Each event sent records the transition that caused it and the command that committed it.
  error_taxonomy: >
    A command that is refused, or a transaction that rolls back, sends nothing.
acceptance_criteria:
  - id: AC1
    text: >
      Each of the four existing transitions (item complete, item cancel, unit dispose_unit, assignment
      dispose with ruling close) sends ticket ended after its command commits; one row per transition
    falsified_by: >
      Leave the assignment's close unwired; that row's scratch stays present and the row fails
  - id: AC2
    text: >
      A project's cancel and complete each send project ended, which ends the items of the project that
      have no ticket as well as those that have
    falsified_by: >
      Send it for complete only; the canceled project's worktree stays with no due record and the row
      fails
  - id: AC3
    text: >
      A command that is refused, or a transaction that rolls back, sends nothing
    falsified_by: >
      Send from inside the transition before the commit; the row that rolls the command back finds items
      due and fails
  - id: AC4
    text: >
      Worktree abandoned is sent when a ticket's next run is provisioned in another worktree and when the
      owner presses Abandon; a month without activity sends nothing
    falsified_by: >
      Send it for a worktree unchanged for 30 fixture days; the row finds it due and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The six transitions commit as before and send no event.
---

## Intent

A ticket's leftovers go when the ticket ends. The authority already commits four transitions that end a
ticket and two that end a project. This ticket sends ticket ended and project ended after each of those
commits, and worktree abandoned when a ticket's next run is provisioned in another worktree or the owner
presses Abandon. Age sends nothing.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (ticket ended, project ended and
worktree abandoned) and 6.6 (space.abandon). Section 12 of the design holds the ticket itself; its
acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Authority service, API.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
