---
schema: veldo.spec/v1
id: VELDO-0326
title: "Host principals for space commands"
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
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_factory_setup.py"
  - ".veldo/control_factory_setup.py"
  - "scripts/suites/*_veldo_0326_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0326-host-principals-for-space-commands.md"
  - "specs/index.md"
  - "proof/VELDO-0326/**"
behavior_bearing: true
observability:
  logs: >
    Each ledger command records the principal that signed it. A refused command is logged with the
    principal and the command's name.
  error_taxonomy: >
    A command a host principal may not sign is refused by the command's name. Every owner action is
    refused from both host principals.
acceptance_criteria:
  - id: AC1
    text: >
      Installing the service makes the keys of space-observer and space-runner and enrolls both; a hook's
      command signed as space-observer is accepted without the owner's key being readable by the hook
    falsified_by: >
      Sign hook commands with the owner's key; the row that runs the hook with the owner's key unreadable
      finds no record and fails
  - id: AC2
    text: >
      space-observer may sign declare and confirm for a worktree, a branch and session scratch, rebranch,
      event and the read behind covers, and is refused every other ledger command by name
    falsified_by: >
      Accept signal from space-observer; the row that sends it gets items marked due and fails
  - id: AC3
    text: >
      space-runner may also sign measure, hold, admit, release, signal and outcome, only for the run or
      gate it declared
    falsified_by: >
      Let it signal for any owner; the row that signals for another run's items gets them due and fails
  - id: AC4
    text: >
      Adopt, Abandon, Confirm, Reconcile, marking a proposal wrong, the mode switch, a protect list change
      and an answer to a space disposition request are refused from both host principals
    falsified_by: >
      Accept Abandon from space-runner; the row that sends it finds the worktree due and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The two keys stay in the installation folder, and commands signed with them are
  refused.
---

## Intent

A git hook and a gate helper must be able to write to the ledger without holding the owner's key. This
ticket adds two host principals, space-observer and space-runner, each with its own key made at install,
and the Ledger's rule for what each may sign.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.11 (who signs a space command).
Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here
word for word.

What section 12 says about this ticket:

> Components: Host principals, Ledger, CLI. Depends on 0297.

Build order. It is one of the first five tickets, built in the order 0296, 0338, 0297, 0326, 0331.
depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: footprint extended to control_factory_setup.py and its engine copy, by the lead's decision.
  The installer made and enrolled the two keys only when it was handed the installation folder and the
  owner's enrollment, and veldo factory setup handed it neither, so on a real factory neither principal
  was ever enrolled and every space command was refused. Setup now takes the installation folder its
  reader resolved, has the installer make both keys there, and enrolls both through the owner's signed
  enroll_principal on its own connection; a re-run over a factory laid down before enrolls the ones the
  store does not hold, only while the service is stopped. With no installation folder no key is made and
  the answer names the step deferred. Acceptance criteria and falsifiers are unchanged; suite 133 gains
  two rows that run factory setup on the fixture and sign a command as each principal. Known and left
  for the lead: the setup suites that call the command surface resolve the installation folder from the
  ambient environment, so on a host that has one they would make the two keys there.
