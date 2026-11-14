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
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_api_assertion.py"
  - ".veldo/control_api_assertion.py"
  - "engine/.veldo/control_api_authority.py"
  - ".veldo/control_api_authority.py"
  - "engine/.veldo/control_api_models.py"
  - ".veldo/control_api_models.py"
  - "scripts/suites/71_veldo_0130_api.py"
  - "specs/VELDO-0302-veldos-own-creators-declare-before-they-create.md"
  - "specs/VELDO-0308-run-finished-from-the-receiver.md"
  - "specs/VELDO-0310-landed-and-contained-from-the-landing-station.md"
  - "specs/VELDO-0315-reconcile-at-start-and-on-demand.md"
  - "specs/VELDO-0318-the-owner-decides-what-becomes-of-unique-work-at-a-tickets-end.md"
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
- 2026-11-14: fix round, after the independent review of bf5ed110 (review-veldo-0312.md, verdict FIX,
  findings F1 to F8), by the lead's decisions. No acceptance criterion changed. The footprint is amended:
  control_space.py (F1, F2, F6: the fix is the ledger's), control_api_assertion.py and
  control_api_authority.py (F3: the signed route), each with its synced copy, and the History lines and
  criteria the lead asked for in the specs of VELDO-0302, 0308, 0310 and 0315. Two more files were needed
  for the route and are in the amendment, FOR THE LEAD: control_api_models.py (and its copy), because
  suite 71_veldo_0130 holds every write route to an action of the published contract, and that suite's
  own file, which lists the body of each write route by name and wants the route's command registered on
  its connection. No protected path is touched.
  - F1 and F2, the owner's Keep is absolute, in the ledger. FOR THE LEAD, a fact the review did not have:
    the state kept is not the owner's Keep alone. Signal writes kept for every table action that removes
    nothing (a worktree measured at run finished, a branch marked contained), and the next event must
    reach those items: a rule on the state would have kept every measured worktree for ever. So the
    owner's Keep is its own mark on the item, owner_keep, written by the outcome kept whose facts carry
    it and by nothing a host principal may sign. An item that holds the mark is never matched by a signal
    that names an owner, whatever the event; signal is the only command that writes due, so a retry, a
    Confirm, a sweep and a reconcile have no other way to it. Only the owner's Abandon of that exact item
    ends it (a signal of worktree abandoned that names the item at its version and says owner_abandon
    for it). The service also sends nothing for a kept worktree when the ticket's next run is
    provisioned elsewhere (the answer says kept). Who writes the mark from the owner's settled Keep is
    VELDO-0318's; until then nothing in the engine writes it, so nothing is kept by the owner yet.
    Design 6.1's signal row ("present, kept or deferred") still reads as before; section 0 holds, and
    the row is the lead's to amend.
  - F6, and the gap VELDO-0308 (N1) and VELDO-0310 (finding 3) recorded: the ledger's signal can name
    items. Its subject is either the parts of an owner, as before, or a list of items, each with the
    version its sender read. The ledger then acts on exactly those items, with no matching by owner, and
    refuses the whole command, writing nothing, when one of them changed, is in no state a signal
    reaches, does not end on the event or holds the owner's Keep. One stale item refuses all: an Abandon
    is one decision on one screen. Abandon uses it: the worktree, the items of its own scope and ticket
    at or beneath it, and its own agent repository. So one of a ticket's two worktrees can be abandoned,
    the ticket's scratch and its runs' things elsewhere are no longer reached by an Abandon (the review's
    F6 route; the earlier build reached them), not_alone is gone, and another ticket's item beneath the
    worktree is not named and holds it by rule 6 (F8).
  - F3, the signed route. space.abandon is a write route of the API (operation abandon_worktree, the item
    and its version), verified by the API authority like every owner action: the edge's signature, a
    current credential, a person, and of persons only the owner (project_owner whose scope covers the
    space scope, the rule of the ledger's own mode switch). The version is required at the authority and
    again in the service; a missing or stale one sends nothing. An instance that serves the API hands its
    space_abandon to the authority at start. Abandon removes no unique work: a worktree with uncommitted
    or untracked work, or a commit only its branch holds, is deferred by rule 5 and stays, and the answer
    names it under discard_required, because only the owner's Discard, which saves first (design 0.3),
    takes it away. The route is refused unavailable_service:space_ledger until VELDO-0315 builds
    Service.space.
  - F5: an agent's worktree is named with its own agent repository, unless another live worktree is
    recorded in that repository. The worktree goes first, by the ledger's child rule.
  - F4: VELDO-0315 gets the criterion that builds Service.space and VELDO-0302 the one that calls
    space_provisioned; no code here.
  - F7 is not done, FOR THE LEAD: an event whose send raised is still passed over until reconcile. It
    loses no work. Stopping the pass on a raise would hold every later event behind one that keeps
    raising, and that choice is not this round's.
  - Rows and falsifiers. Suite 149 is 35 rows (thirteen added, ac4/second-worktree-stays replaced by
    ac4/one-of-two-worktrees). Finding 312 holds 23 falsifiers: the build's ten less the two whose code
    is gone (space312-abandon-sent-past-another-worktree, and space312-stale-version-accepted, written
    again), and fifteen of this round. Each was applied once, by the registry's own case and the
    driver's own materialize and worker, and seen red on its rows; the bundle lists them.
- 2026-11-14: fix round 2, after the re-review of b93f9967 (rereview-veldo-0312.md, verdict FIX: one
  blocking finding in a spec, the code of the first round sound), by the lead's decisions. No acceptance
  criterion of this ticket changed. The footprint is amended: the spec of VELDO-0318, whose AC4 is the
  blocking finding. Nothing here removes anything, and nothing here makes a removal possible that was
  not: every change refuses more than before.
  - F1 (blocking, spec): VELDO-0318 AC4 said "Keep sets the item to kept" and did not know the mark. It
    now says Keep writes owner_keep, in one command from deferred to kept, accepted only as the owner's
    signed packet verified as the mode switch is, with the falsifier the re-review named (Keep without
    the mark: ticket ended makes the item due) and two more. That spec's History holds the reason.
  - F2: the ledger checks the owner itself. The transition that writes owner_keep and the one that takes
    an owner_abandon read this store's membership inside the command's transaction and refuse
    not_authorized unless the command is the one the Ledger sent and its principal is an active person
    holding project_owner over the space scope, at the time the request gives (owner_keep.at,
    owner_abandon.at; the Ledger reads no clock). So the authority's own principal, a person who is not
    the owner, a service and a command given to the store directly write no Keep and end none. Who is
    written on the item is that principal: a request that carries a `by` is refused as invalid input.
    The service sends the owner's Abandon with the owner as the command's principal, and the API
    authority reads the ledger's not_authorized as unauthorized:not_owner. FOR THE LEAD, what this is
    not: a check of the owner's signature. An in-process caller that names the owner as its principal
    is still believed; the Abandon's signature is the edge's, checked by the API authority, and the
    owner's signed Keep is VELDO-0318 AC4.
  - F3: rows for the two guards the re-review's falsifiers Fe and Fi survived. An item the owner marked
    Keep beneath an abandoned worktree is not named, stays kept at its version and holds the worktree,
    which is deferred. The runner and the observer sign no signal that names items, also for a run
    issued to the runner and for the runner's own events; today the runner is allowed to name none.
  - F4: Service.space_abandon has no default cause. The cause is a keyword of its own; a caller that
    leaves it out gets Python's TypeError and not the owner's Abandon.
  - F7: VELDO-0315 gets AC8 (an ending event whose send raised is recorded and retried by reconcile).
    No code here: the service still passes over such an event, which loses no work.
  - Rows and falsifiers. Suite 149 is 40 rows (five added: r2/ledger-checks-the-owner,
    r2/by-is-the-verified-principal, r2/kept-beneath-abandoned-worktree, r2/runner-names-no-items,
    r2/abandon-names-its-cause). Finding 312 holds 30 falsifiers, seven of this round, each applied once
    by the registry's own case and the driver's own materialize and worker and seen red on its row; the
    bundle lists them.
  - One row of the first fix round is tightened, because F2 made its falsifier pass: with the ledger
    checking the owner, a route that let anyone who signed in through
    (space312-abandon-by-anyone-signed-in) was still refused, by the ledger, under the same name. Row
    f3/route-refusals now also sees that the API authority refuses a person who is not the owner before
    the service is asked: no event is logged. Both guards have their falsifier red again.
