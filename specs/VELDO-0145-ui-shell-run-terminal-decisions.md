---
schema: veldo.spec/v1
id: VELDO-0145
title: The UI shell, the live run terminal and the decisions screen on phone and desktop
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W105
plan_revision: 4
depends_on: [VELDO-0130, VELDO-0141]
placement: [loop, distribution]
protected_paths: []
footprint:
  - "engine/ui/**"
  - "packs/*/ui/**"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "packs/*/.veldo/control_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0145_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0145-ui-shell-run-terminal-decisions.md"
  - "specs/index.md"
  - "proof/VELDO-0145/*"
behavior_bearing: true
observability:
  logs: >
    Record each UI session start and end, each decision answer sent with its request and presentation
    version, and each named refusal the API returned; never a credential or an unredacted line.
  metrics: >
    Count sessions, live record followers, reconnects and answers accepted or refused by reason.
  traces: >
    Join each screen's reads and each answer to the API session, the request and the settlement.
  error_taxonomy: >
    Distinguish unauthenticated, ended session, out of scope, stale presentation, already settled and
    API unavailable, each shown beside the action it concerns; none is shown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner opens the factory UI on his phone and desktop in a passkey session, and every
      screen reads and acts only through the authenticated API. Set and completeness: Build the UI with
      the owner's stack (React, TypeScript, Vite, shadcn/ui, Monaco) and serve it from the API on
      loopback behind Tailscale Serve; sign in with an enrolled passkey (VELDO-0130), reach the shell's
      navigation, the run screens and the decisions screen, and sign out. Before sign-in, after the
      session ends, and for a member whose scope does not cover a project, every screen shows the
      named refusal and no data. Trace every request each screen makes to an API route. Falsifier: Serve
      a screen's data before the passkey session is established; the unauthenticated-access check must
      fail.
    falsified_by: >
      Serve a screen's data before the passkey session is established; the unauthenticated-access check
      must fail.
  - id: AC2
    text: >
      Claim: The run screen is a live terminal of the run's execution record, with every event in the
      order the engine produced it, never a summary. Set and completeness: Follow a real worker run
      through VELDO-0141's record route while it writes and after it ends: every line in sequence, tool
      calls with their inputs and results, command output in monospace, edits as diffs in Monaco, errors
      marked, a follow mode and search, beside a pipeline strip showing the unit's station; drop the
      connection mid-run and require the view to resume from its cursor with no line missing or
      repeated. Compare the lines shown with the record, line by line. Falsifier: Show a summarized step
      list in place of the record; the full-detail check must fail.
    falsified_by: >
      Show a summarized step list in place of the record; the full-detail check must fail.
  - id: AC3
    text: >
      Claim: The decisions screen shows each pending decision exactly as presented and answers it inline
      through the API, settling once with Telegram. Set and completeness: For pending requests from
      VELDO-0064 and VELDO-0065, show the inbox and each request's exact shown question, choices and
      rationale; answer inline through the API's decision route (VELDO-0130) bound to the presentation
      version shown, and observe one settlement (VELDO-0068). Answer the same request from Telegram
      first and then from the UI, answer after the presentation changed, and answer as a member outside
      the project's scope; each shows its named refusal beside the action. Falsifier: Send an answer
      without the presentation version it answers; the stale-answer refusal row must fail.
    falsified_by: >
      Send an answer without the presentation version it answers; the stale-answer refusal row must
      fail.
  - id: AC4
    text: >
      Claim: The shell and its two screens meet VELDO-0131's phone, desktop, accessibility and
      dependency rules. Set and completeness: Render each at 360px and 390px phone widths and 1280px and
      1440px desktop widths in loading, empty, live, stopped or error and populated states, with no
      clipped primary action, overlapping controls or page-wide horizontal overflow; run keyboard-only
      desktop and touch phone tasks with 44px primary touch targets, labeled controls, sufficient
      contrast and screen-reader names from the actual accessibility tree; and check the lockfile and
      served assets against VELDO-0131 AC4's origin, license and tier rules. Falsifier: Hide the inline
      answer action at 360px width; the phone decisions check must fail.
    falsified_by: >
      Hide the inline answer action at 360px width; the phone decisions check must fail.
required_evidence: [unit, integration, ui_states]
rollback: >
  Stop serving the UI; the API, the records and every decision path through Telegram are unchanged.
  No automatic rollback is authorized.
---

## Intent

The owner needs to watch real runs and answer decisions from his phone or desktop before the rest of
the UI exists, so he can stop using the terminal: the first slice is the shell, the live run terminal
and the decisions screen.

## Context

W105 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Sections 7 and 12
of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner
Telegram 29162) split this slice out of VELDO-0131 so it comes in the first stage of the critical path,
right after the execution record (VELDO-0141). VELDO-0131 keeps every other screen and its screen
contract, whose "Live agent run" row is now the terminal of VELDO-0141 AC3 that this slice builds.
The stack and provenance rules are C16 of the plan.

## Out of scope

Every other screen of VELDO-0131; replay or editing of a record; typing into a running worker; search
across all runs; offline use.

## What the reviewer judges

- Normal use: the owner signs in with his passkey on his phone or desktop over his tailnet, opens a
  running unit, watches its worker's every tool call, command, edit and error live, and answers a
  pending decision inline; the same decision answered in Telegram settles once.
- Threat model: data served before sign-in or after the session ends, or to a member outside the
  project's scope; a summary shown in place of the record, or lines lost or repeated on reconnect; an
  answer applied to a presentation other than the one shown, or twice; an action that bypasses the API;
  a clipped or hidden action on a phone; a dependency outside the owner's stack or provenance rules.
  The owner's account, the API and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the screens
  VELDO-0131 owns; very large records before the first live runs measure their size; forged rows in our
  own store and files planted in the installed directory.

## Notes

The UI is served by the API on loopback behind Tailscale Serve and reads only its routes; it has no
engine, shell executor or direct provider call. The terminal reads VELDO-0141's record route, which
streams from a cursor on the receiver's hint and never serves a line before redaction.

## History

2026-09-25: written as a draft for PLAN-0019 revision 4 from the approved operating-model design
(Telegram 29162), section 7(e). Draft; the owner decides readiness.
