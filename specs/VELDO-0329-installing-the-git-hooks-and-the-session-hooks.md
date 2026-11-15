---
schema: veldo.spec/v1
id: VELDO-0329
title: "Installing the git hooks and the session hooks"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop, distribution]
protected_paths: []
footprint:
  - "engine/hooks/post-checkout"
  - "engine/hooks/reference-transaction"
  - "packs/claude/hooks/hooks.json"
  - "packs/claude/scripts/**"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "scripts/suites/*_veldo_0329_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0329-installing-the-git-hooks-and-the-session-hooks.md"
  - "specs/index.md"
  - "proof/VELDO-0329/**"
behavior_bearing: true
observability:
  logs: >
    Each install records the repository or account folder and the hooks folder used. Reconcile lists each
    missing hook under space.reports.
  error_taxonomy: >
    A missing hook is a report, not an error.
acceptance_criteria:
  - id: AC1
    text: >
      Binding a repository, and naming a plain repository, installs both git hooks in the repository's
      shared hooks folder, or in the hooks folder the repository configures, and keeps an existing hook's
      own lines
    falsified_by: >
      Overwrite an existing hook file; the fixture's own hook line is gone and the row fails
  - id: AC2
    text: >
      The session hooks are installed in every client account folder the installation names
    falsified_by: >
      Install in the first account folder only; the row that starts a session under the second finds no
      item and fails
  - id: AC3
    text: >
      Reconcile reports a bound or plain repository whose hook is missing, and a named account folder
      whose session hooks are missing
    falsified_by: >
      Report nothing for a missing hook; the row that deletes the fixture's hook finds an empty report and
      fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Hooks already installed stay where they are; a repository bound afterwards gets none.
---

## Intent

The hooks only help where they are installed. Binding a repository, and naming a plain repository,
installs both git hooks and keeps any hook lines already there. The session hooks go into every client
account folder the installation names. Reconcile reports a repository or an account folder whose hooks are
missing.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.9 (hook installation), 8.8
(reconcile) and 6.6 (space.reports). Section 12 of the design holds the ticket itself; its acceptance
criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Git hooks, Session hooks, Reconciler.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.

- 2026-11-15: build blocked at supplied base 8ef46604e80e6a69909556c82e4e9b17e2acde87.
  The session hook implementation (VELDO-0314), reconcile runner (VELDO-0315), and
  ledger event command (VELDO-0323) are absent from this tree. AC2's second-account
  session cannot create its item, and AC3 has no reconcile runner to drive. The existing
  CLI explicitly returns space_no_command:space_event when that command is absent.
  Installing inert hooks or replacing these integrations with passing stand-ins would
  not prove the acceptance criteria. Implementation is paused without changing the
  criteria, dependencies or runtime code; see proof/VELDO-0329/blocker.md.
