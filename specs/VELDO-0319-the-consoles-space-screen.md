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
depends_on: [VELDO-0318, VELDO-0342]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "scripts/suites/support/v174_journey.py"
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
  - "engine/ui/src/views/DecisionsView.vue"
  - "engine/ui/src/features/decisions/**"
  - "engine/ui/src/features/signin/webauthn.ts"
  - "engine/.veldo/control_service_api.py"
  - ".veldo/control_service_api.py"
behavior_bearing: true
observability:
  logs: >
    Each owner action is a signed command in the journal. Reads write nothing.
  error_taxonomy: >
    An owner action from a session without the owner's passkey is refused. not_authorized for a Keep
    packet the owner's passkey or key did not sign; space_disposition_unsettled for a packet whose
    request has no settled answer; space_disposition_choice for a packet sent to space.keep for a
    request settled as Save or Discard.
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
  - id: AC5
    text: >
      An accept keep that the owner answers in the console is applied with no second press. When the
      owner picks a Keep answer to a space request on the Decisions screen, the console builds the Keep
      command for that item, at the version space.pending shows, and that request; the owner's passkey
      signs it; the answer is sent; and once the answer has settled the console sends the signed packet
      on space.keep, a signed owner route. The Ledger then writes owner_keep by that owner and moves the
      item from deferred to kept in one command
    falsified_by: >
      Leave out the space.keep call after the answer settles; the row's answer settles, the item stays
      deferred, and the row fails
  - id: AC6
    text: >
      The Ledger verifies a passkey-signed Keep itself. The one function that checks the owner behind a
      signed space command (_mode_signer, used by set_mode and by the disposition) gains a passkey form
      beside the SSH key form: the assertion must verify against an enrolled, unrevoked credential of the
      command's principal in the Ledger's own store, with SHA-256 of the canonical command as its
      challenge and the installation's origin and relying-party id. The principal must still be an
      active person holding project_owner over the space scope and the one who answered. space.keep
      applies only a request settled as Keep. A command with the API edge's signature alone, a credential
      of another member, a revoked credential, an assertion made over another item, version or request,
      and a request settled as Save or Discard are each refused with nothing written. A Keep signed with
      the owner's SSH key is taken as before
    falsified_by: >
      Each of these turns a row of its own red. Take the edge's signature in place of the passkey's: the
      row sends space.keep with no assertion and the item is kept. Skip the challenge comparison: the row
      signs the Keep for one item, sends it naming another, and the other item is kept. Apply whatever
      the settlement holds: the row sends a signed packet for a request settled as Discard and the item
      is made due
  - id: AC7
    text: >
      A Keep that settled and was not applied, because the item's version moved, the space.keep call did
      not arrive, or the answer came over a channel that cannot sign (the phone's message channel), is
      listed under Pending removal as answered and not signed, with a Sign Keep action. Sign Keep signs a
      new packet at the item's current version and sends it on space.keep. For a member of a review group
      the packet names that member's own request, the alias the member kept when the group moved on
      (VELDO-0342), and not the group's current request
    falsified_by: >
      Each of these turns a row of its own red. List only items with an open request: the row's settled,
      unsigned Keep is on no screen. Sign the group's current request for a member: the Ledger refuses
      the packet and the member stays deferred
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

### The console signs the owner's Keep (AC5 to AC7, amendment of 2026-11-16)

Keep is the one answer the settlement path cannot finish alone. VELDO-0318 AC4 (amended 2026-11-14)
has the Ledger take Keep only as the owner's own signed packet: "an edge-signed answer alone writes no
owner_keep". The service's dispositions task applies settled Save and Discard and skips Keep, so a Keep
answered in the console settles and then waits for a packet nothing sends.

The signature. Today the Ledger checks the owner's SSH signature under the owner's enrolled key. A
browser does not hold that key; the console's owner has a passkey, and a console session proves only
that the owner signed in. So each Keep gets a passkey ceremony of its own, whose challenge is SHA-256 of
the Keep command's canonical bytes (control_store.canonical_bytes). The console builds the command:
principal, operation space_disposition, a fresh command id and nonce, and parameters item, version and
request. A unit row checks that the console's bytes equal the store's for the same command. The
ceremony is the sign-in feature's assertPasskey, reused; it may move under src/api if the UI's house
rules forbid one feature importing another.

The check is built once. _mode_signer in control_space.py is the only place the Ledger verifies the
owner behind a signed space command, and both set_mode and the disposition call it, inside the
transaction as well as before it. It gains the passkey form here. The Ledger reads the credential from
its own store (the api_credential records of control_api_credentials) and calls
control_api_webauthn.assertion_problems with the origin and relying-party id the service already
holds, passed to the Ledger when the service builds it (control_service.py, control_service_api.py).
VELDO-0332 switches the mode from the console through the same function and builds no second check.

The route. space.keep is a signed owner route like space.abandon: an operation in
control_api_assertion.OPERATIONS whose parameters are the item, the version, the request and the packet;
a branch in the authority that admits the owner only; an action in control_api_models.ACTIONS; a service
entry that calls Ledger.disposition. The answer itself still goes through the settlement path, as design
6.6 says answers do; space.keep carries the owner's signature for an answer that has already settled.
One route serves both AC5 and AC7, so there is one way a Keep packet reaches the Ledger.

Rows this amendment changes, all its own ticket's.

- scripts/suites/150_veldo_0319_space_screen.py, ac3/no-dead-route. Today it pins two lists: the
  published space routes (reconcile, abandon and the four reads) and the space actions (reconcile and
  abandon), and it expects 404 for adopt, confirm, reject, mode, restore and kept. Six later tickets add
  routes (VELDO-0320, 0332, 0339, 0346, 0351, 0352) and each would have to edit those lists. The row is
  restated once, here, as the property it guards: every POST route named space.* carries an operation
  in OPERATIONS, has an authority branch and an action in ACTIONS, and its command
  (authority.commands()) is a Ledger operation that has a transition; and no owner action that the
  Ledger names without a transition (control_space.OWNER_ACTIONS less the transition map) has a route,
  while a POST to its name answers 404. space.keep passes it. A teeth case publishes a route whose
  command has no transition and must turn the row red. No later ticket changes this row.
- The same suite, ac3/routes-signed. The check "the four reads are GET routes that need a session and
  take no field" keeps that property for every entry of SPACE_VIEWS and drops the exact list of four
  names, so VELDO-0339, 0351 and 0352 add their reads without editing it.
- scripts/suites/150_veldo_0319_space_ui.py: BROWSER gains the amendment's browser rows. ui/api-only
  stays as written; it compares that tuple with the titles in e2e/space.spec.ts.
- scripts/suites/71_veldo_0130_api.py, session/forgery-refused: bodies gains space.keep, as it gained
  space.abandon.
- The teeth cases of finding 319 keep their anchors. One whose anchor line this change moves
  (space319-abandon-as-a-plain-read-route in control_api.py and space319-reconcile-for-any-member in
  control_api_authority.py are the likely ones) is re-anchored on the same code with the same target
  row, and the teeth of finding 319 are run.

Rows that do not change. 150_veldo_0318_unique_work: ac4/signature sends SSH packets signed by the
wrong principal and they stay refused; no row pins the packet's shape. 150_veldo_0342_member_picks:
ac1/member-keep and next/settled-keep already prove, with SSH packets, that a member's packet under its
own alias keeps that member alone; this amendment adds the console's way to send one.

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

- 2026-11-16: the proof recorded at 5f3afd34 (proof/VELDO-0319): 34 rows green, 21 at the API and 13 in
  the browser, and 32 screenshots of the screen's states. Teeth for finding 319: the eight API cases
  rejected by the driver. The two browser cases (the declared falsifier of AC4 among them) are
  invalid_baseline in the driver's confined leg, where the browser suite cannot run, and were applied by
  hand in an export of the commit, both red; the gate's mutation stage runs them once the lead has added
  150_veldo_0319_space_ui to scripts/gate_unconfined.json. Suites 121 and 122 (VELDO-0131) are
  load-dependent on this host on this tree and on the base alike, and suite 123 (VELDO-0174) has 17 rows
  red on the base too; the proof's checks.json holds the runs.

- 2026-11-16: FIX round authorized by the lead after the fresh review of 498c20c4.
  Rebased onto the accepted VELDO-0342 fix at bab38780, preserving settlement advancing the
  remaining group after Keep while its member awaits the owner packet. The console Keep signer
  is for the next round. The unowned sections remain for the lead to assign.
  Footprint widened to control_space.py and its synced copy, factory.spec.ts (already under
  e2e), and scripts/suites/support/v174_journey.py. The protect list is unchanged.
  F1: the table cell selector now outranks the shared table rule. A browser row compares the
  numeric text and header right edges at 1440 px in both themes.
  F2: the Ledger stamps removal sequence inside its outcome transaction. Reads obtain commit
  time by publication primary key and find dispatches through their indexed hold link.
  Indexes are installed when the Ledger opens, before serving reads, and maintained atomically
  by SQLite. Older unstamped removals remain visible with unknown order and time; reads do no
  backfill. Two rows count the same SQL steps after 4096 more journal entries and dispatches;
  falsifiers restore the old scans. The screen removes nothing and still follows the stream.
  F3, owner VELDO-0131 (Telegram 41209): repair factory screen tests to release held or dropped
  routes on open failure, register cleanup before navigation, and await the screen's own data
  request or response within its test budget. Failed tests are repaired, never retried to green.
  F4, owner VELDO-0316 at aa1c5560: give the VELDO-0174 stand-in service space=None, matching
  an installation without space admission; prove suite 123 twice alongside 121 and 122 twice.

- 2026-11-16: validation BLOCKED by the mandatory host gate lock. The immutable rebased
  baseline at a5244013 passed all 22 VELDO-0342 rows with no surviving supervisor. The next
  queued job took the lock and entered the three-hour quiet-host guard. Per the lead's stop
  rule, own queued jobs were cancelled before execution. F1 through F4 are committed but
  unverified; 0319, suites 121/122/123 twice, the remaining regressions, fast checks and teeth
  are pending. No gate or guard was bypassed. See proof/VELDO-0319/fix-round-blocked.json.

- 2026-11-16: next round, from the review of VELDO-0342 (finding 1, answer b), the observation in the
  review of VELDO-0318 and the lead's decisions of this day. AC5 to AC7 are added: the console signs
  the owner's Keep with the owner's passkey and sends it on space.keep once the answer has settled, the
  Ledger verifies the passkey itself in _mode_signer, which VELDO-0332 then uses for the mode switch,
  and a Keep that settled and was not applied can be signed later. ac3/no-dead-route and
  ac3/routes-signed are restated as properties so later tickets add routes without editing them. The
  footprint gains the Decisions screen, the sign-in ceremony and control_service_api.py. Four criteria
  became seven.

- 2026-11-18: the amendment BUILT, as 0319's next round, on a0e4bc10 (commits 993e523e and a7f98bf3).
  Status stays ready until the lead's gate and the review. The record is
  proof/VELDO-0319/amendment-round.json.
  - The route. space.keep is one signed owner route (operation keep_worktree, action worktree_keep,
    command space_disposition) and carries every Keep packet: {command, signature}, the Ledger's Keep
    command for one item, version and request, and the owner's passkey assertion. The answer path is
    unchanged: control_request_settlement.py and answer_decision's parameters were not touched. The
    authority admits the owner only and requires the packet's command to be that principal's command
    for exactly what the route names; the service's entry (Service.space_keep) hands it to the Ledger.
  - AC6. _mode_signer takes two forms of the owner's signature: a text is the SSH form, as before, and
    a mapping is the passkey form. The passkey form requires a credential that is current for the
    command's principal in the Ledger's own store (control_api_credentials.current, called and not
    changed), enrolled for this installation's origin and relying party, and an assertion that
    control_api_webauthn.assertion_problems accepts with SHA-256 of the command's canonical bytes as
    its challenge. The service gives the Ledger the origin, the relying-party id and the verifier's
    folder (ServiceApi.passkeys in control_service_api.py); a Ledger given none takes no passkey.
    space.keep applies only a request settled as Keep: Ledger.disposition takes only='keep' and the
    transition refuses space_disposition_choice inside the transaction. Without `only` a signed
    packet applies what was settled, as VELDO-0318 built it.
  - AC5. On the Decisions screen a Keep answer to a space request signs first (one ceremony limited to
    the session's credential), then sends the answer, then sends the packet once the answer settled.
    A ceremony the owner closes sends nothing. A packet the Ledger refuses leaves the answer settled
    and is named on the screen with a link to the Space screen.
  - AC7. space.pending names each item's own request by its store id (request_id), marks an item whose
    request settled as Keep and is still deferred (answered: keep), and names the relying-party id a
    Keep is signed for (signing). The Space screen lists such an item as answered and not signed, with
    Sign Keep, which signs a new packet at the version shown. A member of a review group is listed
    under the alias its own record holds. The screen now finds a request's decision by that id too:
    the decisions read serves a single worktree's alias redacted, so the link by alias never matched.
  - The two shared rows. ac3/no-dead-route: every POST route named space.* has an operation, an
    authority branch, an action, and a command the Ledger has a transition for; a person who is not
    the owner is refused each by name. Read against the code, the second half of the amendment's
    wording could not hold as written: space_abandon is an owner action with no transition of its own
    (the signal carries it) and space.abandon is a published route. The row therefore says: no owner
    action without a transition is the command of any route or action, and a POST to the name of each
    that has no route answers 404. ac3/routes-signed: every entry of SPACE_VIEWS is a GET route with
    a session and no field, and every GET route named space.* is one of them. Neither pins a list.
  - For VELDO-0332. The passkey form is in _mode_signer and so in the mode transition. set_mode's own
    packet check still takes the signature as text before it calls _mode_signer; that ticket opens it
    when it adds the console's switch. No second check is needed.
  - Rows. 150_veldo_0319_space_screen: 33 rows green, among them the eleven new ones (ac5/keep-applied,
    ac5/console-bytes, seven ac6 rows, two ac7 rows) and the two restated ones. Suite 71 green with
    space.keep in session/forgery-refused. The UI type-checks and its Vitest specs pass (59 tests) in
    a scratch copy. Neighbouring suites: proof/VELDO-0319/amendment-round.json, each red one compared
    with the base.
  - RED, from fix round F2 and not from this round: cost/removed-index and cost/carried-index, on this
    head and on the base a0e4bc10 with the same numbers. Every authority read judges its reader through
    control_membership.authority_state, a read of the whole store, so the SQL steps of a read grow with
    the store. control_membership.py and control_store.py are outside the footprint. Lead decision
    needed. While they are red the teeth driver refuses every API case of finding 319 as
    invalid_baseline; the 18 mutants each turn their target rows red in the worker logs, which is
    builder evidence only.
  - Teeth. Seven API cases added (the three declared falsifiers of AC6, both of AC7, a credential of
    another member or a revoked one, and a route whose command has no transition) and two browser
    cases (AC5's declared falsifier, and a Sign Keep that sends nothing).
    space319-abandon-as-a-plain-read-route is re-anchored on the same code with the same target row.
  - Not run: the browser suite 150_veldo_0319_space_ui (its new rows are ac5/keep-applied and
    ac7/sign-keep), the five browser teeth cases, F1 to F4 under the lock, and verify.sh. The entry
    scripts/gate_unconfined.json needs is written out in proof/VELDO-0319/gate-unconfined-entry.md;
    that file was not edited.
  - Open for the lead, from the amendment: a Keep answered over the phone's message channel waits for
    Sign Keep in the console and is not refused on that channel.
