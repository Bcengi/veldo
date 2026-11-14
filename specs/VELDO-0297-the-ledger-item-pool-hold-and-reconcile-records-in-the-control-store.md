---
schema: veldo.spec/v1
id: VELDO-0297
title: "The ledger: item, pool, hold and reconcile records in the control store"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0296, VELDO-0338]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "scripts/suites/*_veldo_0297_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0297-the-ledger-item-pool-hold-and-reconcile-records-in-the-control-store.md"
  - "specs/index.md"
  - "proof/VELDO-0297/**"
behavior_bearing: true
observability:
  logs: >
    Every ledger command is one journal record with the item, its kind, owner, locator and state. Paths
    and object names are recorded; file contents never are.
  metrics: >
    Items by kind and state; refused declares by reason.
  error_taxonomy: >
    declare refuses a locator on the protect list, a locator outside every known root and a second live
    item at the same locator, each by name. confirm refuses an item not in state declared; outcome refuses
    an item not due or removing. The store's generic entity command is refused for the ledger's kinds.
acceptance_criteria:
  - id: AC1
    text: >
      The commands of 6.1 write items through the states of 4.1 and no other move is accepted: confirm
      only from declared, outcome only from due or removing
    falsified_by: >
      Accept outcome removed on a present item; the row that sends it without a signal sees the item
      removed and fails
  - id: AC2
    text: >
      Only the Ledger's module writes these entity kinds; the store's generic entity command is refused
      for them
    falsified_by: >
      Leave the kinds undeclared; the row that writes an item through the generic command succeeds and
      fails
  - id: AC3
    text: >
      declare refuses a second live item at the same locator, a locator outside every known root, and a
      locator on the protect list
    falsified_by: >
      Compare locators as raw text; a second declare through a path with a trailing separator is accepted
      and the row fails
  - id: AC4
    text: >
      A store rebuilt from its journal holds the same items, pools and holds
    falsified_by: >
      Keep sizes in a side table outside the journal; the rebuilt store's item has no size and the row
      fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The records already written stay in the journal and nothing reads them. This ticket
  touches nothing on disk outside the store.
---

## Intent

The ledger is the one record of what Veldo has on disk and in Docker. This ticket adds the item, pool,
hold and reconcile records to the control store, the commands that move an item through its states, and
the refusals of declare. Only the ledger's module writes these records.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 4.1 to 4.4 (item, pool, hold and
reconcile records), 6.1 (the ledger commands) and 6.2 (the seam). Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Depends on 0296 and 0338 for the known roots and the protect list, and on the pool's device identity.
> Components:
> Ledger.

Build order. It is one of the first five tickets, built in the order 0296, 0338, 0297, 0326, 0331.
depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: review (verdict FIX), three decisions recorded here because later tickets build on them.
  (1) outcome takes a fourth value, removing, accepted from due only: 6.1 lists removed, deferred and
  kept, but 4.1 has the state and records the decision to remove before the remover runs, so a command
  must write it. (2) A removing item is removed to the end, as 4.1 says: kept is refused for it
  (space_item_state:removing), and deferred is accepted for it only when the rule that refused is the
  owning tool's refusal, remove_refused (section 7 rule 7), which is read while the remover runs; 4.1
  does not draw that move. (3) AC3's refusals read the path as resolved, not as text: a locator with a
  .. segment is refused (space_locator_parent), a path that goes through a link is refused
  (space_locator_link), and a path that resolves at, above or beneath a protected path or outside every
  known root is refused by those names, so a protected thing gets no item record through a link
  (section 7) and two locators that resolve to one folder are never two live items.
- 2026-11-13: re-review (verdict FIX, narrow). rebranch follows the same rule as declare: a worktree
  whose repository is declared through a link is refused at declare and adopt (space_locator_link, the
  reason asks for the resolved path), never accepted there and refused at rebranch. A repository
  declared by its resolved path rebranches, and its branch items are recorded under that path.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. This
  ticket is built and its criteria are not edited. What the rule adds to the ledger is built elsewhere:
  the keep record on a worktree or private repository item, the keep command, and the refusal of the
  outcome removed for such an item with no keep record (VELDO-0345); the restore and drop kept commands
  (VELDO-0346); the proof record and its command (VELDO-0348). No acceptance criterion changed.
