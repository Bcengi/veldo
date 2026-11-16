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
