---
schema: veldo.spec/v1
id: VELDO-0311
title: "Git hooks: worktrees and landings made with plain git"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/hooks/post-checkout"
  - "engine/hooks/reference-transaction"
  - "engine/.veldo/control_space_spool.py"
  - ".veldo/control_space_spool.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "scripts/suites/*_veldo_0311_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0311-git-hooks-worktrees-and-landings-made-with-plain-git.md"
  - "specs/index.md"
  - "proof/VELDO-0311/**"
behavior_bearing: true
observability:
  logs: >
    Each hook call leaves one item record or one event record with the repository, the ref, the old and
    the new commit. A spooled record is one file, replayed in order.
  error_taxonomy: >
    None reaches git: the git command's result is the same with the hook, without it, and with the
    authority down.
acceptance_criteria:
  - id: AC1
    text: >
      A worktree added with plain git in a bound or plain repository has an item, with its branch, start
      commit and the owner its branch pattern gives, when the git command returns
    falsified_by: >
      Record only through the CLI's record verb; the row that uses plain git finds no item and fails
  - id: AC2
    text: >
      Switching a recorded worktree from branch X to branch Y with plain git updates the item's branch to
      Y and its start commit to Y's commit; a later landing that contains X leaves the worktree in place
    falsified_by: >
      Record at worktree add only; the row lands X after the switch, finds the worktree due, and fails
  - id: AC3
    text: >
      A committed change of the trunk or of a declared landing ref, made with plain git, leaves one event
      record with the repository, the ref, the old and the new commit, and the git command returns with
      nothing removed. The row holds every remover on a fixture latch and the git command still returns
    falsified_by: >
      Remove inside the hook; with the remover held on the latch the row finds the git command still
      waiting and fails
  - id: AC4
    text: >
      With the authority not reachable the git command's result is unchanged, the record or event is in
      the spool, and it is replayed in order at the next CLI call that reaches the authority and at
      service start before reconcile
    falsified_by: >
      Drop the event when the authority is down; after service start the row finds the worktree with no
      item and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The hooks record nothing, and a worktree made with plain git is found by reconcile.
---

## Intent

A worktree added with plain git, a branch switched in it, and a landing made by hand all happen outside
Veldo. Two git hooks record them: post-checkout records the worktree and a branch switch,
reference-transaction records a change of the trunk or of a declared landing ref. A hook records and
returns. It removes nothing, and it never fails or delays the git command; when the authority is down the
record goes to the spool.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.9 (the rows for git commands, what
each mechanism does when the authority is not reachable, and the four limits), 4.5 (event record), 4.6
(spooled event), 8.4 and 8.5. Section 12 of the design holds the ticket itself; its acceptance criteria
and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Git hooks, Event spool, CLI. The hooks record and return. What follows a landing event is
> VELDO-0323; installing the hooks is VELDO-0329.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
