---
schema: veldo.spec/v1
id: VELDO-0163
title: The owner writes a role's capability configuration and a project's team roles in a minimal UI form
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W123
plan_revision: 4
depends_on: [VELDO-0144, VELDO-0145, VELDO-0162]
placement: [loop, distribution]
protected_paths: []
footprint:
  - "engine/ui/**"
  - "packs/*/ui/**"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0163_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0163-role-and-team-form.md"
  - "specs/index.md"
  - "proof/VELDO-0163/*"
behavior_bearing: true
observability:
  logs: >
    Record each configuration save and team save from the form with the revision or team version it was
    edited from, and each named refusal the API returned; never a credential value.
  metrics: >
    Count configuration saves and team saves from the form, and refusals by reason.
  traces: >
    Join each save to the API session, the route and the authority command, and each team save to the
    request the owner answered.
  error_taxonomy: >
    Distinguish unauthenticated, ended session, stale revision, invalid configuration, incomplete roster,
    unresolved configuration reference and API unavailable, each shown beside the action it concerns;
    none is shown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner writes a role's capability configuration in the UI, and each save becomes a new
      revision through VELDO-0162's configuration route. Set and completeness: In the VELDO-0145 shell, in
      a passkey session, open the role form on a 360px phone width and a 1280px desktop width; create the
      configuration of a role `builder_jira` with its engine, native tools, MCP selections chosen from the
      catalog read (VELDO-0144) including the Atlassian server with all its tools or a list, skills,
      instruction files and engine settings, each item with its load mode; save, then edit and save it
      again. Compare every field the form sent with the revisions VELDO-0162 AC1's route stored; a save
      edited from an older revision shows the stale refusal beside the save action and stores nothing; no
      primary action is clipped at phone width. Falsifier: Send the form's save without the revision it
      was edited from; the stale-save row must fail.
    falsified_by: >
      Send the form's save without the revision it was edited from; the stale-save row must fail.
  - id: AC2
    text: >
      Claim: The owner adds, changes and removes a project's team roles in the UI, each naming its
      capability configuration and kind, and a saved team is shown current only once the authority
      accepted his answer. Set and completeness: In the same shell and widths, open a project's team, add
      the specialist role `builder_jira` naming the configuration of AC1, change the implementation role's
      configuration reference, remove a specialist role, and save; the form sends the team through
      VELDO-0162 AC2's route bound to the team version shown, the request VELDO-0162 AC3 opens appears in
      the decisions screen (VELDO-0145 AC3), and after his answer there the form shows the new revision as
      current, read back through the team route. A role with no configuration, an incomplete roster and a
      stale team version each show their named refusal beside the save, with the owner request it opened.
      Falsifier: Show the saved team as current before the authority applied his settled answer; the
      authoritative-team row must fail.
    falsified_by: >
      Show the saved team as current before the authority applied his settled answer; the
      authoritative-team row must fail.
required_evidence: [unit, integration, ui_states]
rollback: >
  Stop serving the form; capability configuration revisions, team revisions and their requests are
  unchanged, and the API routes stay available. No automatic rollback is authorized.
---

## Intent

At the end of the second stage the owner writes "please do BCG-123" and a role that lists the Atlassian
server fetches the ticket; for that he must be able to write that role's configuration and put the role
in the project's team himself, from his phone or desktop, before the rest of the UI exists.

## Context

W123 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Sections 4 and 6
of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner
Telegram 29162) have the owner save capability configurations and teams, and its section 12 promises
"please do BCG-123" at the end of its second stage. VELDO-0162 adds the routes; the "Team and
agent/tool/MCP configuration" row of VELDO-0131 is built in the third stage, so on the fourth review of
revision 4 this minimal form moves earlier, into this specification of the second stage, as VELDO-0159
did for the server form, and VELDO-0131's row keeps the role table and revision history and opens this
form, so it is not built twice. This new specification is draft; authoring it supplies neither
implementation proof nor operational activation.

## Out of scope

The role table with revision history and the effective tools and servers view (VELDO-0131); the MCP
server form (VELDO-0159); every other screen of VELDO-0131.

## What the reviewer judges

- Normal use: the owner signs in on his phone or desktop, writes the configuration of a role that lists
  the Atlassian server, adds that role to his project's team, saves, and answers the team request in the
  decisions screen; the team then shows the new revision as current.
- Threat model: a save that overwrites a newer revision or team version; a team shown current before
  the authority applied his answer; a refusal shown as success or away from its action; a form that
  bypasses the API; a clipped action on a phone. The owner's account, the API and the store are
  trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the screens
  VELDO-0131 owns; a browser extension reading the page; forged rows in our own store and files planted
  in the installed directory.

## Notes

The form reads the catalog through VELDO-0144's route and reads and writes only VELDO-0162's
configuration and team routes, inside the VELDO-0145 shell and its passkey session, with the stack and
provenance rules of VELDO-0131 AC4. It is minimal: one form for a role's configuration and one for a
project's team roles, not the role table.

## History

2026-09-25: written on the fourth review of PLAN-0019 revision 4, so the owner can give a role the
Atlassian server and put it in a team at the end of the design's second stage, as section 12 promises:
the role form moves earlier from VELDO-0131's "Team and agent/tool/MCP configuration" row, which no
longer carries it. A draft: only the owner marks a specification ready.
