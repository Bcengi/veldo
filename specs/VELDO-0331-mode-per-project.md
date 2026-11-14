---
schema: veldo.spec/v1
id: VELDO-0331
title: "Mode per project"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0297]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_admission.py"
  - ".veldo/control_space_admission.py"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "scripts/suites/*_veldo_0331_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0331-mode-per-project.md"
  - "specs/index.md"
  - "proof/VELDO-0331/**"
behavior_bearing: true
observability:
  logs: >
    Every mode switch is a journal record with the scope, the old and the new mode and the owner's
    command.
  error_taxonomy: >
    A mode command not signed by the owner is refused. A scope with no record is in report mode, which is
    not an error. The conditions of a switch to act are VELDO-0332 and VELDO-0339.
acceptance_criteria:
  - id: AC1
    text: >
      Each project, each plain repository and no project has its own mode, kept as a ledger record; a
      scope with no record is in report mode; the record's history holds every switch with the owner's
      command
    falsified_by: >
      Keep one mode for the installation; the row with project A in act and project B in report finds B's
      due folder removed and fails
  - id: AC2
    text: >
      Signal, admission and reconcile's adoption rule each read the mode of the scope the item or the run
      belongs to: on one pool a run of an act-mode project waits where a run of a report-mode project is
      advised, and the advised hold still counts as held
    falsified_by: >
      Leave advised holds out of what is held; the act-mode row is admitted into space an advised run was
      promised and fails
  - id: AC3
    text: >
      A switch back to report is accepted at once, and from then that project's events write due and
      remove nothing
    falsified_by: >
      Refuse the switch back; the row that sends it stays in act and fails
required_evidence: [unit, integration]
rollback: >
  Switch every scope back to report, then revert the change. Mode records stay in the journal.
---

## Intent

Report or act is set per scope: each project, each plain repository, and no project. This ticket keeps the
mode as a ledger record, makes Signal, admission and reconcile read the mode of the scope they are working
for, and accepts a switch back to report at once.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 2 (scope and mode), 4.7 (mode
record), 6.1 (the mode command) and 6.7 (mode). Section 12 of the design holds the ticket itself; its
acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Ledger (the mode record), Signal, Admission, Reconciler. Depends on 0297.

Build order. It is one of the first five tickets, built in the order 0296, 0338, 0297, 0326, 0331.
depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: review (verdict FIX), three lead decisions. (1) The ledger checks the owner's signature
  and the sender inside the mode transition itself and trusts no caller: a space_mode command from the
  authority with a signature that is not the owner's is refused. (2) A hold records the scope it was
  placed under (the scope its run was issued with, before any other), and admit refuses the answer
  advised for a hold of a scope in act mode. (3) Act is refused outright, as
  space_act_unbuilt:VELDO-0332,VELDO-0339, until the checks of VELDO-0332 (three clean report days) and
  VELDO-0339 (no unconfirmed pending group) exist; each of those tickets removes its part when it lands,
  and its spec says so. No acceptance criterion changed.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. This
  ticket is built and its criteria are not edited. The space_act_unbuilt refusal also names VELDO-0348
  until that ticket lands, and from then a scope in act with no proof record for the space modules and the
  git in use writes due and removes nothing (VELDO-0348 AC4). No acceptance criterion changed.
