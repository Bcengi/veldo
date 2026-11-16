---
schema: veldo.spec/v1
id: VELDO-0319
title: "The console's Space screen"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0342]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/src/app/navigation.ts"
  - "engine/.veldo/control_api_models.py"
  - ".veldo/control_api_models.py"
  - "engine/.veldo/control_api_authority.py"
  - ".veldo/control_api_authority.py"
  - "engine/.veldo/control_api_assertion.py"
  - ".veldo/control_api_assertion.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "scripts/suites/71_veldo_0130_api.py"
  - "engine/ui/src/router/index.ts"
  - "engine/ui/src/api/reads.ts"
  - "engine/ui/src/api/actions.ts"
  - "engine/ui/src/features/run/**"
  - "engine/ui/src/stores/runs.ts"
  - "engine/ui/src/ui/icons.ts"
  - "engine/ui/docs/views/**"
  - "engine/ui/e2e/**"
  - "specs/VELDO-0320-migration-report-mode-and-confirm.md"
  - "specs/VELDO-0332-wrong-proposals-and-the-switch-to-act.md"
  - "specs/VELDO-0315-reconcile-at-start-and-on-demand.md"
  - "scripts/suites/*_veldo_0319_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0319-the-consoles-space-screen.md"
  - "specs/index.md"
  - "proof/VELDO-0319/**"
behavior_bearing: true
observability:
  logs: >
    Each owner action is a signed command in the journal. Reads write nothing.
  error_taxonomy: >
    An owner action from a session without the owner's passkey is refused.
acceptance_criteria:
  - id: AC1
    text: >
      The usage table's figures per project, ticket and kind equal the sums of the fixture's item records,
      with each plain repository and "No project" as rows of their own
    falsified_by: >
      Sum only present items and leave out deferred ones; the totals row fails
  - id: AC2
    text: >
      Pending removal lists every due and deferred item with its reason in words, its retry event and its
      open decision request; Removed lists every removal with its event, size and free space before and
      after
    falsified_by: >
      Hide deferred items; the row that expects the in-use folder finds nothing and fails
  - id: AC3
    text: >
      Reconcile, Adopt, Abandon, Confirm, Wrong and the mode switch are signed owner commands; a session
      without the owner's passkey is refused each
    falsified_by: >
      Accept Abandon as a plain read route; the unsigned row succeeds and fails
  - id: AC4
    text: >
      A waiting run, and in report mode a run that would have waited, shows need, free, held and floor on
      the runs list and the Pools section, and the screen updates from the record stream without a reload
    falsified_by: >
      Poll on an interval; the row that stops the fixture clock sees no update and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The console has no Space screen; the ledger and the CLI are unaffected.
---

## Intent

The owner needs to see where the space is and what Veldo is about to do with it. The Space screen shows
usage by project, ticket and kind, what is pending removal and why, what was removed and by which event,
and the pools with the runs waiting on them. Every figure is read from ledger records, and every action is
a signed owner command.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 10 (console) and 6.6 (API and
console actions). Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers
are copied here word for word.

What section 12 says about this ticket:

> Components: API, Console.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-16: BLOCKER, recorded by the builder before any code was written. Status stays ready; nothing
  is built. Read on the base bf962cfc (VELDO-0342). The footprint holds the API's HTTP edge
  (control_api.py), the route mirror, the feature folder, the view and the navigation. Every criterion
  needs files outside it:
  - AC1, AC2, AC4, the reads. control_api.py holds no store connection and serves nothing of its own
    (its docstring, READS AND EVENTS): a read is authority.read(model, principal), which refuses any
    name outside control_api_models.READ_MODELS (control_api_authority.py:317-321). No read model
    holds a space kind (item, pool, hold, mode, group, event), and the inspection takes identities, so
    it cannot list them. Needed: engine/.veldo/control_api_models.py (the space reads of design 6.6,
    with the kinds' project rules) and engine/.veldo/control_api_authority.py (the grouping of usage,
    pending with its reason, retry event and request, removed, pools with their holds), each with its
    synced copy. The VELDO-0130 suite (scripts/suites/71_veldo_0130_api.py) pins the read models and
    may need its tables extended.
  - AC3, the signed commands. space.reconcile and space.abandon exist (VELDO-0315, VELDO-0312). Adopt,
    Confirm, Wrong and the mode switch need an operation each in control_api_assertion.OPERATIONS
    (shape_problems refuses an unknown operation, :113), a branch in control_api_authority.apply, an
    action in control_api_models.ACTIONS and a service entry in control_service.py beside
    space_abandon. The Ledger has adopt and set_mode; space_confirm_group and space_reject are only
    named in control_space.py (:466-470, "Commands of later tickets"): the commands themselves are
    VELDO-0320 and VELDO-0332, which come after this ticket in the build order. So "Confirm and Wrong
    are signed owner commands" cannot be shown end to end here; what can be shown is that the routes
    are POST, signed and refused without the owner's passkey, with the authority answering a named
    refusal until those tickets land. That needs a lead decision.
  - The screen is not reachable: engine/ui/src/router/index.ts holds every route and is outside the
    footprint; the navigation entry would point at a route name that does not exist.
  - AC4, the runs list: engine/ui/src/features/run/RunList.vue and runs.ts, engine/ui/src/stores/runs.ts
    and engine/ui/src/api/reads.ts (the house place of every read; src/api is "the only code that
    calls fetch or EventSource").
  - The house rules of engine/ui/CLAUDE.md, which bind every UI ticket: a page per screen
    (engine/ui/docs/views/space.md, and runs.md changed), the browser states at four widths in light
    and dark (engine/ui/e2e/space.spec.ts with its harness and fixtures, e2e/falsifiers.json for the
    falsifiers, the source of the ui_states evidence and of the screenshots), and a new glyph in
    engine/ui/src/ui/icons.ts if no bundled icon fits.
  Needed from the lead: the footprint widened by control_api_models.py, control_api_authority.py,
  control_api_assertion.py and control_service.py (engine and synced copies; the lead says whether any
  is protected), engine/ui/src/router/index.ts, engine/ui/src/api/reads.ts and actions.ts,
  engine/ui/src/features/run/**, engine/ui/src/stores/runs.ts, engine/ui/src/ui/icons.ts,
  engine/ui/docs/views/**, engine/ui/e2e/** and scripts/suites/71_veldo_0130_api.py; and the decision
  on Confirm and Wrong above. Not built as a workaround: reads served by control_api.py from the store
  or from files, a feature-local fetch, a screen with no route.
- 2026-11-16: the lead's decisions on the blocker above, recorded as given. None of the files named is a
  protected path.
  - (1) The footprint is widened, as the list above now says: control_api_models.py,
    control_api_authority.py, control_api_assertion.py and control_service.py (each with its synced copy)
    for the space reads and the commands this ticket carries; scripts/suites/71_veldo_0130_api.py only
    where its tables must list the new read models; in engine/ui the router, src/api/reads.ts and
    actions.ts, src/features/run/** and src/stores/runs.ts (only what AC4 needs), docs/views/**, e2e/**
    and src/ui/icons.ts. The history lines of (2) are why three other specifications are in the list.
  - (2) No dead routes: no route is signed that is refused by name, and no button is shown that cannot
    work. AC3 IS AMENDED. This ticket builds the command path for the commands that exist today:
    space.reconcile, space.abandon, and the owner's answers to space requests through the existing
    settlement path, and the screen's places where the later commands go. Confirm belongs to VELDO-0320;
    Wrong and the mode switch to VELDO-0332; Adopt to the ticket that introduces its ledger command.
    Each of those tickets adds its own button with its command. The criterion's words in the header are
    the design's and are left as written; this entry is what was built against.
  - (3) Every space read and command goes through control_api_authority as the other models do, with no
    new way in, and the owner's commands stay the owner's.
- 2026-11-16: built on VELDO-0342 at bf962cfc. Status stays ready until the lead's gate and the review.
  - The reads. Four GET routes, space.pools, space.usage, space.pending and space.removed (design 6.6),
    each one view of the ledger's records. control_api_models names the ledger's kinds with their project
    rules (SPACE_MODEL) and makes the views; the authority serves them through `read`, the one call the
    API has for a read model, so the API process reaches them over the service socket as it reaches
    every other and control_client_api.py and control_service_api.py did not change. A view is made from
    the records and then redacted as a view: redacted first, an alias could not be joined and a path
    could not be shown. An identity is kept. A path is judged by the secret scanner part by part,
    because the scanner reads a whole path as one long token and would replace every worktree's path; a
    part it finds is still replaced. A member whose scope is not the whole factory is served the items,
    holds and groups of their projects only; pools are the installation's.
  - AC1. space.usage sums every item that is still there (declared, present, due, deferred, removing,
    kept) by scope, ticket and kind. It also lists the worktrees an Abandon can be sent for, which is
    where the screen's Abandon acts.
  - AC2. space.pending gives each due and deferred item its reason in words (control_api_models
    deferral_words, from what the refusing rule found), the event it was refused at, its retry events
    and its request; a review group's worktrees are under their one request by index, with the indexes
    the request offers an answer of their own for (VELDO-0342). space.removed is newest first by the
    journal record that last wrote each item.
  - AC3, as amended. Reconcile and Abandon already had their routes, operations and authority branches
    (VELDO-0315, VELDO-0312); control_api_assertion.py and control_service.py did not change. This
    ticket adds their place on the screen, their functions in src/api/actions.ts and the route
    space.reconcile in the UI's route table. An answer to a space request is given on the Decisions
    screen, which already binds an answer to the presentation shown: the Space screen lists the request
    with its worktrees and links there, and sends no answer of its own.
  - AC4. space.pools gives each pool its floor and what is held on it, and the waiting and advised holds
    with the four numbers of their judgment. The runs list shows a run that would have waited with one
    line on its row. A waiting run has a hold and no dispatch (admission is asked before a dispatch is
    prepared), so it is a row of its own in the list, with no run to open. The screen follows the
    record stream as the factory screens do (useLiveRead); nothing reads on a timer.
  - Adopt. No specification of the design's list builds the owner's Adopt of a reported thing: the
    ledger's adopt transition is VELDO-0297's, reconcile calls it and writes the reports (VELDO-0315),
    and the signed owner command space.adopt and the read space.reports are named only by this ticket's
    AC3 and by design 6.6 and 10. The history line the lead asked for is on VELDO-0315, the ticket whose
    reports the owner adopts from, and says that the owner is still to be confirmed by the lead.
  - Not built, and why. The Modes, Kept work missing, Reports and Protected sections, the run view's
    space panel and the overview's pool under its floor: design 10 lists them and no criterion of this
    ticket does. A pool's capacity and its free space now: no ledger record holds them (a pool record
    holds its floor; free space is recorded on a judged hold and on a removal), and a read measures
    nothing. The unit of a waiting run: the hold record names its project and not its unit. A group of
    its own for waiting runs on the runs screen: engine/ui/src/views/RunsView.vue is outside the
    footprint, so a waiting run is listed in the Stopped card with the blocked runs. A link to the
    screen from the phone's You screen: engine/ui/src/views/YouView.vue is outside the footprint; on a
    phone the screen is reached by its address. The page of the runs list component
    (engine/ui/docs/ui/run-list.md) is outside the footprint and does not yet name the space line.
    A client that signs the owner's Keep packet: none exists (VELDO-0318, VELDO-0340, VELDO-0342), so
    an accept keep answered on the Decisions screen settles and is not applied.
  - The gate. The browser suite 150_veldo_0319_space_ui needs system Chrome and the npm registry, as
    suites 120 to 124 do. Those are listed in scripts/gate_unconfined.json, a protected path this ticket
    does not touch: the lead adds the entry.

