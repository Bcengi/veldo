---
schema: veldo.spec/v1
id: VELDO-0335
title: "Released by its creator"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0323, VELDO-0326]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_space_consumer.py"
  - ".veldo/control_space_consumer.py"
  - "engine/.veldo/control_space_worker.py"
  - ".veldo/control_space_worker.py"
  - "scripts/suites/*_veldo_0335_*.py"
  - "scripts/suites/151_veldo_0313_space_run.py"
  - "scripts/suites/153_veldo_0323_hook_events.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0335-released-by-its-creator.md"
  - "specs/VELDO-0318-the-owner-decides-what-becomes-of-unique-work-at-a-tickets-end.md"
  - "specs/index.md"
  - "proof/VELDO-0335/**"
behavior_bearing: true
observability:
  logs: >
    One released event record per call with the locators it names, then the outcomes of the items it made
    due.
  error_taxonomy: >
    A released event that names an item a Veldo seam declared, or a path with no item, is refused by name.
    An agent worktree whose branch the shared repository does not hold is space_deferred:unique_work and
    is never deleted. Decision requests belong to VELDO-0318.
acceptance_criteria:
  - id: AC1
    text: >
      A released event signed as space-observer, naming a worktree and an agent repository the record verb
      declared, removes both through all seven rules, the worktree first; the CLI call returns with
      nothing removed
    falsified_by: >
      Send worktree abandoned from the script; the Ledger refuses an owner action from a host principal,
      nothing becomes due, and the row finds both folders present and fails
  - id: AC2
    text: >
      The Ledger refuses a released event that names an item a Veldo seam declared, or a path with no
      item, by name
    falsified_by: >
      Accept released for any item; the row that names a fleet worktree finds it due and fails
  - id: AC3
    text: >
      A released agent worktree whose branch the shared repository does not hold is deferred as unique
      work and never deleted, with or without force
    falsified_by: >
      Let the script's force flag reach the remover; the row's unlanded commit is lost and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The Ledger refuses the released type, so a host script keeps its own delete.
---

## Intent

A script outside Veldo that made a worktree or an agent repository can give it up without deleting it. It
sends a released event, signed as space-observer, and the things go through all seven rules. The Ledger
accepts released only for items a hook or the record verb declared.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (released by its creator), 6.9
(the script outside Veldo that gives up what it made), 6.10 (the sandbox script's rows outside the
repository) and 6.11. Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Ledger (the event command), CLI (event), Event consumer, Space worker. Depends on 0323 and
> 0326.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). depends_on holds the dependencies the
design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-15: lead decision, the decision request moves to VELDO-0318
- 2026-11-15: review fix records the CLI emitter as verb event and refuses --force by name
  (invalid_input:force). Direct Ledger protection, repository-only releases, private branches and
  a worktree git lock with an untracked draft have permanent rows and registered falsifiers.

- 2026-11-15: build updates the two existing CLI event expectations: released now reaches the
  ledger's creator check and records valid creations. Other event envelopes are unchanged. The record
  verb accepts an explicit parent agent repository for a new worktree with the same owner, so the
  rules compare the worktree with its shared repository and remove the child first. The legacy force
  flag on released is accepted without authority and is never recorded or passed to Signal.
  This base has no VELDO-0318 implementation or proof bundle; AC3's decision request remains blocked
  on that implementation. Its unique-work deferral and refusal to force removal are tested here.
- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
