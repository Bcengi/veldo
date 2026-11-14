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
- 2026-11-14: built. No acceptance criterion changed. In control_service.py: Service.space (the ledger and
  what Signal is given, wired in by the installation), space_pass, space_events, space_send, space_abandon
  and space_provisioned. Suite scripts/suites/149_veldo_0312_ticket_ended.py, 22 rows; ten falsifiers
  registered under finding 312, the four declared ones among them, each applied once and seen red on its
  row. What the build decided, and what it leaves to other tickets:
  - Nothing here removes anything. The service sends an event through Signal and through nothing else:
    the rules, the keep step and the removers are Signal's. A worktree with uncommitted or untracked
    work, with a commit only its branch holds, or one git or a process holds, is deferred and stays.
  - After the commit, from the journal. The six transitions are committed by their own organs (the
    backlog, the assignment inbox, the project service), which this ticket does not touch. After a
    packet, a channel pass and a factory loop pass the service reads the journal records committed
    since the last one it read, outside any transaction, and sends for a record only what that record
    committed: the record's command is the one the last history entry of the item, the unit or the
    project names, with the state it moved to, or the one the disposition record of a close names. So
    a refused command and a rolled back transaction, which leave no record, send nothing, and a later
    write to an ended entity is not read as an end again. The terminal states have no exit, so no
    ticket is reopened; a pause is not an end.
  - What a ticket is. The unit: ticket ended is sent with the subject {the unit's project, the unit},
    as landed is. An item's complete and cancel end every unit of its decomposition. A project the
    ledger does not name is sent nothing.
  - Signal runs in the service's own process, inside the pass (VELDO-0301). The space worker the design
    gives the service for its own events is VELDO-0323's. Until then a large removal holds the service
    loop. FOR THE LEAD.
  - A service that starts reads the journal from its head: an end committed while no service ran, or
    before a ledger was wired in, is not sent. Those items wait for reconcile (VELDO-0315). FOR THE
    LEAD.
  - Nothing in the engine builds Service.space yet (the ledger for the installation is built at start
    by VELDO-0315), so an installation sends nothing until that wiring lands. FOR THE LEAD.
  - AC4, the owner's Abandon, FOR THE LEAD: NOT BUILT AS A ROUTE. The authority's side is built and
    proven (Service.space_abandon: one worktree, at the version the screen showed). The console's
    signed route space.abandon is not: a write route needs its operation in
    control_api_assertion.OPERATIONS and its dispatch in control_api_authority.ApiAuthority._apply,
    and neither file is in this footprint. A route added to control_api.py alone would be refused at
    the assertion's shape and would turn suite 71_veldo_0130 red (it holds the write routes equal to
    the assertion's operations). So control_api.py, its synced copy and engine/ui/src/api/routes.json
    are unchanged. What is needed: a footprint amendment for those two files (and their synced
    copies), or the route in VELDO-0319, whose AC3 already covers the signed owner commands.
  - AC4, provisioned in another worktree, FOR THE LEAD. The entry is Service.space_provisioned(unit,
    worktree, dispatch): every other worktree the ledger records for that ticket is sent worktree
    abandoned. The provisioner that calls it is in control_launch.py and control_clone.py, outside
    this footprint; the suite calls the entry directly. It must be called before the new worktree's
    own item is confirmed (see the next point).
  - The ledger's signal names an owner, not an item (the same limit VELDO-0310 recorded). So worktree
    abandoned for one worktree is sent with the whole owner of each live item at or beneath it, and
    only when the event would reach no other worktree and no agent repository of that owner; for an
    owner that is a scope alone (a branch no pattern maps to a ticket) it must reach nothing else that
    the event removes. Otherwise nothing is sent (not_alone, with what it would have reached). Two
    consequences. A ticket with two recorded worktrees cannot have one abandoned: both stay, and no
    work is lost, but space is. And the event reaches what the ticket owns elsewhere (its scratch, its
    ended runs' containers and volumes), as the worktree abandoned column says, also when the ticket
    goes on in another worktree; a run that has not ended holds its things by rule 3. Closing both
    needs a signal that names items, which is the ledger's. FOR THE LEAD.
  - The state kept is one the ledger's signal reaches: ticket ended and project ended make an item the
    owner marked Keep due again (design 0.4 says only Abandon ends Keep). That is the ledger's to
    settle with VELDO-0318, as VELDO-0310's history says of landed. FOR THE LEAD.
  - The unit's dispose_unit and the assignment's close are driven in the suite by journal records a
    fixture command commits on the real store, holding the entities those transitions write. The two
    need the owner's settled answer through the settlement chain, which this suite does not build. The
    item's complete and cancel and the project's four commands are the real organs' own.
