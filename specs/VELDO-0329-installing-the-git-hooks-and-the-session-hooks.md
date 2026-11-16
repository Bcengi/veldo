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
depends_on: [VELDO-0301, VELDO-0311, VELDO-0314, VELDO-0315, VELDO-0323]
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
    Each install records the repository or account folder and the hooks folder used. For a repository
    the record also lists the keys of its local git configuration the hooks read, each written or
    present: veldo.space.stateroot, veldo.space.cli, veldo.space.installation and veldo.space.trunk.
    A refused install records why. Reconcile lists each missing hook under space.reports, and a hooks
    folder or a state root that is not this installation's to write with the reason.
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

- 2026-11-15: a first build attempt stopped at base 8ef46604 because the session hooks (VELDO-0314),
  the reconcile runner (VELDO-0315) and the Ledger's event command (VELDO-0323) were not in that tree.
  Nothing was built then.

- 2026-11-16: built on a base that holds them. depends_on now names what this ticket installs and
  drives: the two git hooks (VELDO-0311), the session hook script (VELDO-0314), the reconcile runner
  (VELDO-0315) and the event command a session's start reaches (VELDO-0323), beside the build step
  before it (VELDO-0301). The design states no dependency for this ticket; these are the ones the
  build needs. The installer and the two reports are in control_space_reconcile.py, and the service's
  start (bootstrap) calls the installer, so a repository gets its hooks at the first start after it
  is bound. By the owner's rule that no work is ever lost (2026-11-16), an existing hook is chained
  when it is an executable shell script and refused otherwise, and the install record says which;
  a refused hook is left byte for byte and reconcile reports it as missing. The hook files, the
  pack's hooks.json and the session script are unchanged. Acceptance criteria are unchanged.

- 2026-11-16: fix round after the independent review (verdict FIX, six findings). (1) core.hooksPath
  is read as the owner's git reads it, with the global and the system file; set outside the
  repository's local configuration the install is refused and reconcile reports it. (2) The hooks
  folder must be the repository's alone: a relative hooks path, a folder that is a link or is reached
  through one, and a folder inside a work tree or another repository are refused, so no tracked file
  is edited and no unbound repository gains a hook. (3) A git that did not run is a failure. (4) An
  installation touches only what carries its own state root. Another installation's session entries
  and veldo.space.stateroot are kept and the conflict is refused and reported; a second entry was not
  added, because the git hook reads one state root and a session reported to two ledgers would have
  two owners. (5) The settings file is rewritten under a lock beside it and read again after the
  rename; a key written twice is refused; text that is not ASCII is kept. (6) The marked hook lines
  run under timeout(1) with a deadline of 10 seconds; without timeout(1) the bound is the CLI's own
  wait for the authority. The install record lists the veldo.space.* keys, and the observability
  section names them. Acceptance criteria are unchanged.
