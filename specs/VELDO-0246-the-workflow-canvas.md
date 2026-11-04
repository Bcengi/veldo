---
schema: veldo.spec/v1
id: VELDO-0246
title: The owner builds, edits and watches each kind of work's workflow on one canvas, and the canvas never lets an approval go
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0132, VELDO-0131, VELDO-0229]
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
    resulting version, definition digest and named refusal (VELDO-0132, VELDO-0130). Nothing new is logged
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
    approval), unavailable_service and unknown outcome. None is ever shown as saved or answered.
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
      inputs and limits in the inspector in plain words; Save as version N+1 through workflows.save. A fresh
      reads.workflow of that version returns a definition whose canonical digest equals the one the canvas
      sent, with the layout separate from it, and no worker, provider or shell call happened (VELDO-0132 AC3).
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
      name and the head version is unchanged. The per-use approval of a paid step is shown on and locked, with
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
      fail after version N+1 is saved while the run is open.
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the UI change and the route addition together; the definitions, their versions and every run's
  recorded revision are data from VELDO-0132 and VELDO-0241 and stay as they are. The previous canvas
  (VELDO-0131) returns with the revert. No automatic rollback, retry or recovery is authorized.
---

## Intent

The owner sees, builds and edits the process each kind of work follows (code, document or deck, image or
video, social post, deploy) on one canvas, and watches a run of it on the same canvas, on a desktop and on
the phone. The canvas makes the owner's approval impossible to lose: it is the one solid black step, sits on a
full-width line labeled "Runs only after you approve", and every way of removing it is refused with the
reason the moment it is tried. Owner, Telegram 39072 (2026-11-04): "UI Canvas for this needs to be great!
Extra effort to make UX super usable."

## Context

Telegram 39069 to 39071 (2026-11-04): a unit's process becomes a versioned workflow definition per kind of
work, built from step types, and the owner's approval steps can never be skipped. The definitions, step
types and defaults are VELDO-0241 to VELDO-0245 (drafts written in parallel); VELDO-0132 is the definition
document (nodes, transitions, layout kept apart from execution semantics) and its save; the API publishes
`reads.workflow` (GET `/api/v1/domains/{domain}/workflow`, by workflow and optional version) and
`workflows.save` (POST `/api/v1/domains/{domain}/workflows/save`, workflow, base and definition, optional
layout), refused `stale_version` when the base is not the head. The UI's present canvas is VELDO-0131's
`FlowCanvas` and `FlowProperties` (SVG, pan and zoom buttons, a step list), in VELDO-0229's neutral Nuxt UI
look.

The owner's OK on the pilot design comes first: `proof/VELDO-0246/design/` holds the four screens this spec
builds exactly (a: the social post definition open; b: a step selected, the inspector, an inline field error
and the refused removal of the approval; c: a run on the canvas; d: that run at 390 px), the design plan and
the self-critique log. Where a screen and this text differ, the owner's comment on the screens decides.

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
- Out of review scope (filed, not blocking): unlikely edge cases (Telegram 28962); definitions too large to
  lay out legibly (over 40 steps); touch gestures beyond tap, drag and pinch.

## Notes

Design rules the build follows (from the pilot): the definition reads top to bottom so the desktop and the
phone show the same order; branches leave to the right with their outcome named (Changes asked, Declined,
Failed) and end in a named pill (Dropped, Stopped, you are told); flow blue `#2E5BDA` marks connections,
ports, selection and the path a run took, never a button or a state (a new token in both themes, added to
`docs/design/colors.md` with its contrast); state keeps green, amber and red with words; the palette groups
step types by what they do (Work, You, Timing, Going out) with one line each in plain words; the inspector's
sections are Who does it, What it needs, Limits, Cost and approval, Where it goes next.

The run view needs the revision a unit recorded and its per-step states. If VELDO-0241 publishes them in an
existing read, the canvas uses it; otherwise this spec adds one read route (`reads.workflow_run`) to the API's
ROUTES table and the UI's routes table, and the existing route-mirror test covers it. Decide before ready.

Usability rows run as suite 127 in Playwright with system Chrome against the real harness, like suites 118 to
124, each test titled with its row in brackets: ac1/default-opens, ac1/add-and-connect, ac1/save-roundtrip,
ac2/approval-kept, ac2/paid-approval-locked, ac2/server-refusal-shown, ac3/keyboard-only, ac3/undo-exact,
ac3/axe, ac4/run-states, ac4/run-revision, ac4/terminal-one-click, ac4/phone-360, ac4/phone-390.

## History

2026-11-04: new draft (Telegram 39072, on 39069 to 39071). Pilot screens in proof/VELDO-0246/design for the
owner's OK before any build.
