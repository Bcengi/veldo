---
schema: veldo.spec/v1
id: VELDO-0352
title: "The console's Protected section"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0315, VELDO-0319, VELDO-0330, VELDO-0341, VELDO-0351]
placement: [engine, loop]
protected_paths: ["scripts/gate_unconfined.json"]
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "engine/.veldo/control_space_docker.py"
  - ".veldo/control_space_docker.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/.veldo/control_api_models.py"
  - ".veldo/control_api_models.py"
  - "engine/.veldo/control_api_authority.py"
  - ".veldo/control_api_authority.py"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/api/reads.ts"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/docs/views/space.md"
  - "engine/ui/e2e/**"
  - "scripts/suites/*_veldo_0352_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/gate_unconfined.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0352-the-consoles-protected-section.md"
  - "specs/index.md"
  - "proof/VELDO-0352/**"
behavior_bearing: true
observability:
  logs: >
    Reconcile's record names, per protect entry and engine, what the entry matched and any engine it
    could not read. The read writes nothing.
  error_taxonomy: >
    None of its own. The read is refused as every read model is for a session that is not a member.
acceptance_criteria:
  - id: AC1
    text: >
      The read space.protected lists every protect entry in force, once, with where it comes from: the
      installation's space section, a named project's space file, a keep entry of a project's space file,
      or the Ledger's own entry for the snapshot store. A member whose scope is not the whole factory is
      served the installation's entries and those of their own projects
    falsified_by: >
      List the installation's entries only; the row's entry from a project's space file is missing and
      the row fails
  - id: AC2
    text: >
      For each entry that names Docker objects, the read gives the objects it matched on each engine as
      the last reconcile recorded them, and when that reconcile ran. The read asks no engine and reads no
      disk. An engine that reconcile could not read is shown as not read, never as matching nothing
    falsified_by: >
      Each of these turns a row of its own red. Ask the engine in the read: the row stops the fixture's
      engine after reconcile and the read fails or shows nothing. Show an engine that could not be read
      as no matches: the row whose engine was down at reconcile reads "matches nothing"
  - id: AC3
    text: >
      A protected thing appears in space.protected and in no other space read, and the section has no
      action: no route, no operation and no button acts on an entry or on a matched object. The list
      changes only when the declarations change
    falsified_by: >
      Each of these turns a row of its own red. Count matched objects in the usage table: the row's
      protected volume has a usage row. Add a POST route that removes an entry: the row that sends a
      POST to space.protected gets anything but 404
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The console has no Protected section; the protect rule itself is unaffected and
  keeps what it kept.
---

## Intent

The protect rule keeps some paths and Docker objects out of space management altogether: they get no
item and nothing removes them. The owner cannot see today what that list holds or what it matches. The
Protected section shows it, read only.

## Context

Found by the independent review of VELDO-0319 (review-veldo-0319.md, the not-built list): "VELDO-0341
AC3 only constrains it. The space.protected read and the section are owned by NO ticket."

## Design

The design is docs/design/VELDO-0295-design.md. Sections this ticket builds: 6.6 (the space.protected
row), 10 (the Protected row) and section 7 where it defines the protect rule's list.

Where an entry comes from (control_space.py). protect_list joins the installation's entries, each
project's additions and the Ledger's own entry for the snapshot store. A sibling function gives the
same entries with the source of each, and the read uses it. The entries the Ledger holds in
Ledger.protect keep their shape ({type, value, engines}), because rule 2, the Docker reader and suites
144, 145 and 153 read them.

What an entry matches. A read measures nothing (VELDO-0319's History says so for pool figures, and the
same holds here). Reconcile already reads each engine's objects and already leaves protected ones
without an item (VELDO-0341). It now also hands Ledger.reconcile, per entry and per engine, the names it
matched and the engines it could not read, and the Ledger writes them on the reconcile record. The new
argument is a keyword with a default that records nothing as matched and every engine as not read, so
the callers that pass four arguments today keep working: suites 132 (ac4/rebuilt-pools-holds), 133,
150_veldo_0317 and 150_veldo_0334, and the Reconciler itself until it passes the matches. The read
serves the newest reconcile record, found through an index the Ledger installs when it opens. A path
entry matches its own path and needs no engine.

VELDO-0341 AC3 stays as written and its row stays green: a protected object has no item, no proposed
owner and no Adopt. This ticket adds the one read where such an object may be named.

Rows this ticket changes: none. Checked on 837fa81a and on VELDO-0319's branch. No row compares a whole
reconcile record (132 ac4/rebuilt-pools-holds reads started_by, counts and engines by key) or a whole
protect entry. The two rows of 150_veldo_0319_space_screen that list space routes and reads are
properties after VELDO-0319's amendment, which space.protected meets as a GET route with no field. A
GET route adds no body to suite 71's session/forgery-refused. The teeth cases of finding 319 anchored in
control_api_models.py keep their anchors; one whose line this change moves is re-anchored on the same
code with the same target row, and the teeth of finding 319 are run.

The browser rows live in a spec file of their own, engine/ui/e2e/space-protected.spec.ts, run by this
ticket's own UI suite, and not in e2e/space.spec.ts (row ui/api-only of 150_veldo_0319_space_ui).

Protected path. This ticket's UI suite needs an entry in scripts/gate_unconfined.json, which is
protected: the owner approves that entry at landing.

Footprint. The Ledger (the entry's source, the reconcile record's field and its index), reconcile and
its Docker reader, the read's part of the control API chain with synced copies, the Space screen's
files, and the ticket's suites, proof and spec. control_api_assertion.py and control_service.py are not
in it: the section has no command. No accepted suite is in it.

Order. This ticket follows VELDO-0351, which adds a read and a section to the same files.

## History

- 2026-11-16: drafted from the review of VELDO-0319. Not filed. The number was checked free on every
  ref of the repository.
- 2026-11-16: reviewed. The rows named only by kind were looked for and none exists, so suites 71, 156
  and 150_veldo_0319_space_screen left the footprint. The new reconcile argument has a default so its
  four positional callers keep working, Ledger.protect keeps its shape, the browser rows get a spec file
  of their own, AC3's second falsifier names a row this ticket owns, and depends_on adds VELDO-0351.
