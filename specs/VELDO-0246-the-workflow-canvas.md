---
schema: veldo.spec/v1
id: VELDO-0246
title: The owner builds, edits and watches each kind of work's workflow on one canvas, and the canvas never lets an approval go
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0132, VELDO-0131, VELDO-0229, VELDO-0241, VELDO-0247, VELDO-0253]
placement: [loop, contracts]
protected_paths: ["engine/.veldo/control_workflow.py", ".veldo/control_workflow.py", "engine/.veldo/control_api_authority.py", ".veldo/control_api_authority.py", "engine/ui/src/api/client.ts"]
footprint:
  - "engine/ui/src/features/workflow/**"
  - "engine/ui/src/views/WorkflowView.vue"
  - "engine/ui/src/api/workflows.ts"
  - "engine/ui/src/api/routes.ts"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/ui/icons.ts"
  - "engine/ui/src/router/index.ts"
  - "engine/ui/src/styles/tokens.css"
  - "engine/ui/src/styles/canvas.css"
  - "engine/ui/e2e/workflow-canvas.spec.ts"
  - "engine/ui/e2e/workflow-fixtures.ts"
  - "engine/ui/e2e/harness.py"
  - "engine/ui/e2e/falsifiers.json"
  - "engine/ui/docs/views/workflows.md"
  - "engine/ui/docs/ui/flow-canvas.md"
  - "engine/ui/docs/design/colors.md"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/.veldo/control_api_authority.py"
  - ".veldo/control_api_authority.py"
  - "scripts/suites/127_veldo_0246_workflow_canvas.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0246-the-workflow-canvas.md"
  - "specs/index.md"
  - "proof/VELDO-0246/**"
behavior_bearing: true
observability:
  logs: >
    The API keeps logging every reads.workflow, workflows.save and run read with actor, workflow, base,
    resulting commit id and version, definition digest and named refusal (VELDO-0132, VELDO-0130,
    VELDO-0253). Nothing new is logged
    in the browser; a refusal shown on the canvas before any request is sent is not a server event.
  metrics: >
    The API's existing accepted and refused counts by reason cover canvas saves; the refusal of a definition
    without its owner approval is counted under its own reason name (VELDO-0241's), so canvas misuse shows up
    as a count, not as noise in unsupported_configuration.
  traces: >
    Every request still goes through src/api/client.ts and names a published route; a save carries the base
    version it was edited from, and a run on the canvas names the revision the unit recorded.
  error_taxonomy: >
    Shown beside the action it concerns, by name: stale_version (with "Load the current version"),
    unauthorized, unsupported_configuration (the server's own reason text, including a missing owner
    approval), installation_invalid (each problem by file and key), unavailable_service and unknown
    outcome. A save waiting for the owner's approval (VELDO-0253 AC2) is shown as waiting, with the link to
    its decision. None is ever shown as saved or answered.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the owner creates a workflow from a default and builds on it on the canvas, and what is saved is
      exactly what the canvas showed. Set: the kinds whose default definitions exist when this lands (code from
      VELDO-0241, and document, media, deploy and social post from VELDO-0242 to VELDO-0245 as each lands; the
      suite reads the list from the API, not from a constant). Completeness: the browser row iterates every
      default the API offers. In a real browser (Playwright, system Chrome, the real factory harness as suites
      118 to 124 use): New workflow, pick a default, the canvas opens that definition laid out top to bottom
      at 100 percent and Fit; add a step from the palette by drag onto a connection and, separately, by
      selecting it and pressing Enter (both insert the step and re-route the connection through it); connect a
      branch by dragging from a port and by pressing C then choosing the target; set the step's role, engine,
      inputs and limits in the inspector in plain words; Save through workflows.save, which commits to the
      installation repository (VELDO-0253 AC3) and answers accepted (commit id and version), waiting for
      approval (with the decision link) or refused (installation_invalid, stale_version), each shown as
      such. A fresh reads.workflow of the version the loader assigned returns a definition whose canonical
      digest equals the one the canvas sent, with the layout separate from it, and no worker, provider or
      shell call happened (VELDO-0132 AC3).
    falsified_by: >
      Make the palette's Enter path insert the node without re-routing the connection through it; row
      ac1/add-and-connect must fail because the saved definition has a step no transition reaches.
  - id: AC2
    text: >
      Claim: the canvas refuses, the moment it is attempted, any edit that would leave a step that sends work
      out (publish, deliver, deploy, land) without the owner's approval before it, and never lets a paid step's
      per-use approval be turned off. Set: every way to remove or bypass an approval on the canvas: Delete on
      the selected approval, the inspector's Remove, deleting the transition into or out of it, dragging a
      step's connection around it, moving an outgoing step above it, and a document loaded that already lacks
      one. Completeness: the canvas's edit operations are one closed set in features/workflow (the command
      module the undo stack also uses); the browser row enumerates that set from the module and drives each.
      Each attempt leaves the definition unchanged, puts a refusal beside the approval that says what was
      refused, why and what to do instead, and adds nothing to the undo stack; a loaded definition lacking an
      approval shows the problem in the checks line and Save is disabled with that reason. If the client check
      is bypassed (the falsifier's build), the API's save refusal (VELDO-0241) is shown beside Save by its
      name and the branch is unchanged, with no commit. The per-use approval of a paid step is shown on and locked, with
      the reason.
    falsified_by: >
      Remove the canvas's approval check from the delete command; row ac2/approval-kept must fail because the
      approval is gone from the canvas after Delete.
  - id: AC3
    text: >
      Claim: everything on the canvas can be done from the keyboard, and every edit can be undone exactly.
      Set: the canvas's edit operations (the same closed set as AC2) plus selection, zoom, Fit and opening the
      terminal. Completeness: the shortcut list the canvas opens with ? is generated from the same command
      module, and the row checks each command has a key and each key appears in the list. In a real browser:
      Tab reaches the canvas, arrow keys move the selection along transitions, Enter opens the inspector,
      Shift with an arrow moves the step, C connects, Delete removes, Ctrl or Cmd with Z undoes and with Shift
      redoes, plus, minus and 1 zoom and fit; focus is always visible (2 px ring); axe reports no violation on
      the canvas, the inspector, the refusal and the run view. Undo after any sequence of 50 mixed edits
      restores a definition and layout canonically equal to the start; redo returns to the end; an undo after
      a save marks the document Edited again; a refused edit is never on the stack.
    falsified_by: >
      Let undo of a move restore the definition but not the layout; row ac3/undo-exact must fail on the
      canonical layout comparison.
  - id: AC4
    text: >
      Claim: a run is shown on the same canvas, against the exact revision the unit ran, with each step's
      state, and the owner answers its approval and reaches its live record from there, on a desktop and on a
      phone. Set: step states done, running, waiting on the owner, failed (including a failed attempt that was
      retried) and not started; widths 360, 390, 1280 and 1440 px. Completeness: the states are the closed set
      of VELDO-0241's unit step record; the row reads them from the API's published enum and seeds one of
      each. The canvas draws the revision the run recorded (VELDO-0241), each state with its word, color and
      shape, the path taken in blue and the steps ahead dashed; a waiting approval shows what is being
      approved with Approve, Ask for changes and Decline answering through the existing decisions route
      (shown answered only when the API says so); Open terminal (one click, or T) opens that run's live record
      (RunTerminal). At 360 and 390 px the steps read top to bottom, the approval and its three actions are
      reachable without sideways scrolling and above the bottom bar, and Terminal is in the header. Saving a
      new version while a run is shown changes nothing on that run's canvas.
    falsified_by: >
      Draw the run against the workflow's head revision instead of the recorded one; row ac4/run-revision must
      fail after a new version is saved while the run is open.
  - id: AC5
    text: >
      Claim: the owner makes a workflow conditional and parallel on the canvas in plain words, and what is
      saved is exactly what the canvas showed. Set: the three ways work branches (a step's named outcomes;
      the Check step; parallel steps with a Join) and the Check's tests (mentions any of, does not mention,
      is, is more than, is less than) over the fields the steps before it produce. Completeness: the tests
      and the fields offered are read from the definition schema VELDO-0241 publishes, not from a constant;
      the row drives every test once. In a real browser (Playwright, system Chrome, the real harness): add a
      Check from the palette's Flow row onto a connection; in the inspector pick Look at, Test and the value
      (words as chips, numbers with their unit), never typing an expression; the Check is drawn with one
      labeled edge per branch plus Otherwise, which is always present and cannot be removed or relabeled away;
      connect one step to two at once ("Both at once") and add a Join, which waits for every incoming branch;
      a loop edge needs a cap (rounds) before Save is offered. Save (VELDO-0253 AC3), and a fresh reads.workflow
      of the version the loader assigned returns the Check's rule, its branches, the parallel transitions and the Join with a canonical digest
      equal to what the canvas sent, layout kept apart.
    falsified_by: >
      Let the inspector's Remove act on a Check's Otherwise branch; row ac5/otherwise-kept must fail because
      the saved Check has no Otherwise transition.
  - id: AC6
    text: >
      Claim: whatever the branches, no path reaches an outgoing step (publish, deliver, deploy, land) without
      passing the owner's approval, and Save is refused with the offending path shown. Set: every path from
      the start to every outgoing step in the definition, through outcome branches, Check branches (Otherwise
      included), parallel branches and Joins, with each loop taken at most once. Completeness: the check
      enumerates the definition's paths from its transitions (the same module the save sends), not from the
      drawing; the row seeds one bypass per branch kind (a Check branch, an outcome branch, one side of a
      parallel pair, an edge dragged across the approval line) and one definition with none. In a real browser:
      for each bypass, Save sends nothing; the checks line says "Not saved: 1 path reaches
      Publish without your approval" (the count and the outgoing step named); the offending edges, the steps
      they run through and the outgoing step are drawn in the error color with "Skips your approval" where the
      path crosses the approval line; the inspector lists the path step by step with the approval marked as
      missing and offers the fixes (connect the branch to a step before the approval, or undo that
      connection); the branch is unchanged, with no commit. The definition with no bypass saves. If the client
      check is bypassed (the falsifier's build), the API's own refusal (VELDO-0241) is shown beside Save by its
      name and the branch is unchanged, with no commit.
    falsified_by: >
      Make the path check follow only each step's first outgoing transition; row ac6/every-path-gated must
      fail because a definition whose Check Yes branch goes around the approval is committed.
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the UI change and the route addition together; the definitions in the installation repository,
  their versions and every run's recorded revision (VELDO-0132, VELDO-0241, VELDO-0253) stay as they are. The previous canvas
  (VELDO-0131) returns with the revert. No automatic rollback, retry or recovery is authorized.
---

## Intent

The owner sees, builds and edits the process each kind of work follows (code, document or deck, image or
video, social post, deploy) on one canvas, and watches a run of it on the same canvas, on a desktop and on
the phone. The canvas makes the owner's approval impossible to lose: it is the one solid black step, sits on a
full-width line labeled "Runs only after you approve", and every way of removing it is refused with the
reason the moment it is tried. The owner (2026-11-04): "UI Canvas for this needs to be great! Extra effort
to make UX super usable."

## Context

2026-11-04: a unit's process becomes a versioned workflow definition per kind of
work, built from step types, and the owner's approval steps can never be skipped. The definitions, step
types and defaults are VELDO-0241 to VELDO-0245 (drafts written in parallel); VELDO-0132 is the definition
document (nodes, transitions, layout kept apart from execution semantics) and its save; the API publishes
`reads.workflow` (GET `/api/v1/domains/{domain}/workflow`, by workflow and optional version) and
`workflows.save` (POST `/api/v1/domains/{domain}/workflows/save`, workflow, base and definition, optional
layout), refused `stale_version` when the base is not the head. Under VELDO-0253 the definitions live in the
installation repository and a save is a commit there, read back as the version the loader assigns. The UI's present canvas is VELDO-0131's
`FlowCanvas` and `FlowProperties` (SVG, pan and zoom buttons, a step list), in VELDO-0229's neutral Nuxt UI
look.

The owner's OK on the pilot design comes first: `proof/VELDO-0246/design/` holds the six screens this spec
builds exactly (a: the social post definition open; b: a step selected, the inspector, an inline field error
and the refused removal of the approval; c: a run on the canvas; d: that run at 390 px; e: conditions and
parallel work, the Check step's rule open; f: a branch that goes around the approval, refused at save with
the path shown), the design plan and the self-critique log. Where a screen and this text differ, the
owner's comment on the screens decides.

The owner on a to d (2026-11-04): "Love it. But what if steps are conditional, not just next
next?" The answer this spec builds: (1) branching on a step's named outcome (review passes or asks for
changes, approval approves or declines, publish goes live or fails); (2) a Check step that routes the work by
a rule set in plain words picked from fields, never code (if the post mentions prices, add a legal review;
if the image costs more than $1, ask before generating; if the channel wants square images, make one), each
branch labeled on the canvas, always with an Otherwise path; (3) parallel branches joined by a Join step
that waits for all of them. Loops are always capped. Whatever the branches, no path reaches Publish,
Deliver or Deploy without the owner's approval, and the canvas checks every path at save.

## Out of scope

The workflow engine, the step types and their defaults (VELDO-0241 to VELDO-0245); the server's rule that a
definition without its approval is refused (VELDO-0241 owns it; this spec only shows it); the decisions route
and the run terminal themselves (used as they are); multiple people editing one definition at once (a stale
save is refused and offered a reload, as today); a free-form drawing surface (steps snap to the flow).

## What the reviewer judges

- Normal use: the owner, signed in with a passkey, on a desktop at 1280 or 1440 px or a phone at 360 or 390
  px, opens Workflows, creates a definition from a default or edits one, saves it as the next version, and
  later watches and answers a run of it. Every read and write goes through the published routes.
- Threat model: an edit on the canvas that removes or bypasses an approval; a save that silently differs
  from what the canvas showed; a run drawn against a revision it did not run; an answer shown before the API
  confirmed it; a stale save overwriting a newer version. The owner's account, the API and the store are
  trusted; the client check is a convenience and the server's refusal is the authority.
- Out of review scope (filed, not blocking): unlikely edge cases (the owner's standing ruling); definitions too large to
  lay out legibly (over 40 steps); touch gestures beyond tap, drag and pinch.

## Notes

Design rules the build follows (from the pilot): the definition reads top to bottom so the desktop and the
phone show the same order; branches leave to the right with their outcome named (Changes asked, Declined,
Failed) and end in a named pill (Dropped, Stopped, you are told); flow blue `#2E5BDA` marks connections,
ports, selection and the path a run took, never a button or a state (a new token in both themes, added to
`docs/design/colors.md` with its contrast); state keeps green, amber and red with words; the palette groups
step types by what they do (Work, Flow, You, Timing, Going out) with one line each in plain words, Flow being
one compact row of Check and Join so the palette still fits a 900 px screen; the inspector's sections are Who
does it, What it needs, Limits, Cost and approval, Where it goes next (a Check's are The rule and Where it goes
next, Otherwise locked). A parallel start is drawn as one edge forking to its steps ("Both at once") and a
Join as a step whose incoming edges meet on one bar; a loop back to an earlier step returns on the side its
target sits; the canvas zooms to Fit when the definition is taller than the view.

The condition editor is the Check step's inspector: Look at (a field one of the earlier steps produces,
named with where it comes from), Test (a closed list in words), and the value (words as removable chips,
amounts with their unit), plus Add another condition (all must hold) and Add a branch. A branch's label on the
canvas is the rule's own words or the owner's short name for it ("Mentions prices?" with Yes and Otherwise).

The run view needs the revision a unit recorded and its per-step states. VELDO-0241 as built publishes them
in no existing read, so this spec adds one read route (`reads.workflow_run`) to the API's ROUTES table and the
UI's routes table, reading the pinned copy by digest (VELDO-0253 AC4), and the existing route-mirror test
covers it.

Usability rows run as suite 127 in Playwright with system Chrome against the real harness, like suites 118 to
124, each test titled with its row in brackets: ac1/default-opens, ac1/add-and-connect, ac1/save-roundtrip,
ac2/approval-kept, ac2/paid-approval-locked, ac2/server-refusal-shown, ac3/keyboard-only, ac3/undo-exact,
ac3/axe, ac4/run-states, ac4/run-revision, ac4/terminal-one-click, ac4/phone-360, ac4/phone-390, ac5/check-rule-roundtrip, ac5/otherwise-kept,
ac5/parallel-join, ac5/loop-capped, ac6/every-path-gated, ac6/refusal-shows-path, ac6/server-refusal-shown.

## History

2026-11-04: new draft (Telegram 39072, on 39069 to 39071). Pilot screens in proof/VELDO-0246/design for the
owner's OK before any build.
2026-11-04: conditions and parallel work (Telegram 39079, "But what if steps are conditional, not just next
next?"): the Check step and its condition editor, parallel steps and Join, capped loops, AC5 and AC6 (every
path to an outgoing step passes the approval, refused at save with the path shown); screens e and f added.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.

2026-11-04: amended under the plan consistency review (owner Telegram 39145; research/veldo-plan-consistency-review-2026-11-04.md, findings A22, B10, D6, D8, E13) and the lead's rulings (research/veldo-plan-rulings-2026-11-04.md, R1): a save is a commit to the installation repository under VELDO-0253 and answers accepted, waiting for approval or refused; "head unchanged" is now "branch unchanged, no commit"; the round trip reads the version the loader assigned; depends on VELDO-0241, VELDO-0247 and VELDO-0253; reads.workflow_run decided; personal setup removed from the text and the design files (neutral sample content, no message ids, the browser path a parameter, screens re-rendered). Dispositions in proof/VELDO-0241/review-dispositions-2026-11-04.md on the veldo-workflow-process branch. Status stays ready.

2026-11-05: the review amendments and new tickets approved by the owner, Telegram 39157 ("Yes", to 39156).
