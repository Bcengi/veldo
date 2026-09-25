---
schema: veldo.spec/v1
id: VELDO-0159
title: The owner defines an MCP server and sets its credential in a minimal UI form, whose credential field is write-only
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W119
plan_revision: 4
depends_on: [VELDO-0144, VELDO-0145]
placement: [loop, distribution]
protected_paths: []
footprint:
  - "engine/ui/**"
  - "packs/*/ui/**"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0159_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0159-mcp-server-and-credential-form.md"
  - "specs/index.md"
  - "proof/VELDO-0159/*"
behavior_bearing: true
observability:
  logs: >
    Record each form save with the server id and the revision it was edited from, each credential set,
    replaced or deleted by id, and each named refusal the API returned; never a credential value.
  metrics: >
    Count server saves and credential writes from the form, and refusals by reason.
  traces: >
    Join each save and credential write to the API session, the route and the authority command.
  error_taxonomy: >
    Distinguish unauthenticated, ended session, stale revision, invalid definition, keystore locked and
    API unavailable, each shown beside the action it concerns; none is shown as success.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The owner defines an MCP server in the UI and each save becomes a new catalog revision
      through the API's catalog route. Set and completeness: In the VELDO-0145 shell, in a passkey
      session, open the server form on a 360px phone width and a 1280px desktop width; enter a stdio
      server (command, arguments, environment as literals or credential references, hosts, read-only
      tools) and an http server (url, headers as credential references, hosts, read-only tools),
      including the Atlassian server; save each, then edit and save it again. Compare every field the
      form sent with the revisions the catalog route (VELDO-0144 AC1) stored; a save edited from an
      older revision shows the stale refusal beside the save action and stores nothing; no primary
      action is clipped at phone width. Falsifier: Send the form's save without the revision it was
      edited from; the stale-save row must fail.
    falsified_by: >
      Send the form's save without the revision it was edited from; the stale-save row must fail.
  - id: AC2
    text: >
      Claim: The form's credential field is write-only: a value typed into it goes once to the API's
      credential route and is never shown, kept or read back. Set and completeness: Set the Atlassian
      server's credential through the field, then replace it and delete it (VELDO-0144 AC2); after each,
      the form shows only the credential's label, set at and set by. Inspect the rendered page, its
      accessibility tree, the browser's local and session storage, IndexedDB, the URL and history, and
      every request the page made: the value appears only in the body of the one request to the
      credential route, and nowhere after it is sent; reopening the form shows an empty field. Falsifier:
      Keep the typed value in the browser's session storage after the save; the no-value-kept row must
      fail.
    falsified_by: >
      Keep the typed value in the browser's session storage after the save; the no-value-kept row must
      fail.
required_evidence: [unit, integration, ui_states]
rollback: >
  Stop serving the form; catalog revisions, credential records and keystore items are unchanged, and the
  API routes stay available. No automatic rollback is authorized.
---

## Intent

At the end of the second stage the owner writes "please do BCG-123" and the factory fetches the ticket
through the Atlassian server; for that he must be able to enter the Atlassian server and its credential
himself, from his phone or desktop, before the rest of the UI exists.

## Context

W119 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 3 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the server form with write-only credential fields, and its section 12 promises that
"please do BCG-123" works at the end of its second stage; its one-time setup (section 10) has the owner
add the Atlassian credential through the UI. VELDO-0144 AC2 is the API route only, and the "MCP servers
and credentials" row of VELDO-0131 is built in the third stage, so on the third review of revision 4 the
form moves earlier, into this specification of the second stage, and VELDO-0131's row keeps the catalog
table and credential list without it, so the form is not built twice. This new specification is draft;
authoring it supplies neither implementation proof nor operational activation.

## Out of scope

The catalog table with revision history and the credential list (VELDO-0131); a connection test
button; every other screen of VELDO-0131.

## What the reviewer judges

- Normal use: the owner signs in on his phone or desktop, opens the server form, enters the Atlassian
  server and types its credential into the write-only field, saves, and later replaces or deletes that
  value; a role can then select the server.
- Threat model: a credential value shown, kept in the browser or sent anywhere but the credential route;
  a save that overwrites a newer revision; a form that bypasses the API; a clipped action on a phone. The
  owner's account, the API and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the screens
  VELDO-0131 owns; a browser extension reading the page; forged rows in our own store and files planted
  in the installed directory.

## Notes

The form reads and writes only VELDO-0144's catalog and credential routes, inside the VELDO-0145 shell
and its passkey session, with the stack and provenance rules of VELDO-0131 AC4. It is minimal: one form
for a server and its credential fields, not the catalog table.

## History

2026-09-25: written on the third review of PLAN-0019 revision 4, on the lead's decision, so the owner can
enter the Atlassian credential at the end of the design's second stage as section 12 promises: the
server form with its write-only credential field moves earlier from VELDO-0131's "MCP servers and
credentials" row, which no longer carries it. A draft: only the owner marks a specification ready.
