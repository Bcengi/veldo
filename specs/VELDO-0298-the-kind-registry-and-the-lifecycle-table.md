---
schema: veldo.spec/v1
id: VELDO-0298
title: "The kind registry and the lifecycle table"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0326, VELDO-0331]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_kinds.py"
  - ".veldo/control_space_kinds.py"
  - "scripts/suites/*_veldo_0298_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0298-the-kind-registry-and-the-lifecycle-table.md"
  - "specs/index.md"
  - "proof/VELDO-0298/**"
behavior_bearing: true
observability:
  logs: >
    None of its own: the registry reads no file, process or store. The table version an item was declared
    under is on the item's record.
  error_taxonomy: >
    None of its own. Nothing here defers or removes; the function only answers which action the table
    gives.
acceptance_criteria:
  - id: AC1
    text: >
      For every kind and every event the function returns exactly the action of the table in section 5;
      the rows are the whole table, cell by cell, with the two rows for a worktree owned by a run (a
      review run, and a run of another station), session ended and released by its creator
    falsified_by: >
      Give worktree the action remove at run finished; that cell's row fails
  - id: AC2
    text: >
      A worktree is never returned for removal while a child item is present, due or deferred, an agent
      repository never before its worktree, and due items come back children first
    falsified_by: >
      Return items in ledger order; the row with a deferred build folder gets its worktree first and fails
  - id: AC3
    text: >
      Build output at run finished passes to a queued run of the same ticket on the same worktree when the
      caller says one exists, and is removed when it says none does
    falsified_by: >
      Remove whenever the owning run is finished; the row with the queued-run fact set loses the folder
      and fails
  - id: AC4
    text: >
      An item keeps the table version it was declared under, and a registry change does not alter what an
      existing item ends on
    falsified_by: >
      Read ends_on from the current registry; after a fixture registry change the old item's events differ
      and the row fails
required_evidence: [unit]
rollback: >
  Revert the change. Items already declared keep the table version they carry.
---

## Intent

The lifecycle table of section 5 is data: for each kind and each event, one action. This ticket holds that
table and the one pure function that reads it, with the order in which due items come back.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 5 (kinds and lifecycle: the table,
the events and the rules that complete the table). Section 12 of the design holds the ticket itself; its
acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Kind registry. Pure data and one function; no file, process or store access. Whether the
> ticket has a queued run on the same worktree is a fact the caller passes in.

Build order. It is built together with 0298, 0299, 0330 and 0300, after the first five tickets. The design
states no dependency for this ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: review (verdict FIX), two lead decisions. (1) A worktree or an agent repository is never
  returned for removal while an item inside it is there in any state but removed or gone: kept,
  declared, removing, present, deferred, or due and staying. The review reproduced the loss the earlier
  rule allowed: an agent repository due at ticket ended came back for removal with a worktree the owner
  had answered Keep for, and its uncommitted files, inside it. The suite row that asserted the opposite
  (a kept, declared or removing child does not hold) is corrected, and the reproduction is the row
  ac2/kept-child-holds-parent. Design section 7 and section 5 are amended to say so, and rule 6 of
  VELDO-0330 follows. (2) The function does not trust the caller's list. For each worktree and agent
  repository it would return for removal it calls the look it is given, look(identity, record), which
  answers with what is inside that item now (control_space_signal.inside: the ledger's items inside it
  by parent and by path, and what is on disk inside it that no live item records). With no look, or a
  look that cannot answer, the item comes back with wait and the reason children_not_read; when the
  look finds a child that is neither removed nor gone and that the list does not hold in that state,
  with wait, the reason children_not_passed and the missing children. The module still opens no file
  and no store itself: the look is given to it, and without one it returns no worktree and no agent
  repository for removal. Row ac2/looks-for-children. Not changed: the review's low finding 3 (the row
  of a worktree is read from fields that can change later) is left for the lead. No acceptance
  criterion changed; AC2's words are still true and the function now does more than they ask.
