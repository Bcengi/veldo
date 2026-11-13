---
schema: veldo.spec/v1
id: VELDO-0321
title: "The ledger answers an outside cleaner, and the retirement check"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0339]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "scripts/suites/*_veldo_0321_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0321-the-ledger-answers-an-outside-cleaner-and-the-retirement-check.md"
  - "specs/index.md"
  - "proof/VELDO-0321/**"
behavior_bearing: true
observability:
  logs: >
    covers prints one line per path: the item's state, and keep when that applies. The retirement check
    prints each uncovered path with its class.
  error_taxonomy: >
    The retirement check fails naming the class of each path no item holds, and fails while one of the
    five path classes maps to no kind.
acceptance_criteria:
  - id: AC1
    text: >
      covers answers, for each path it is given, whether an item holds it, the item's state, and "keep"
      when the item is deferred, kept or protected, or when the path is on the protect list
    falsified_by: >
      Answer by presence only; the row with a deferred folder is told it may be removed and fails
  - id: AC2
    text: >
      The retirement check lists the cleaner's candidate paths with its age and size tests off, passes
      only when every one is a ledger item, and names the class of a path that is not
    falsified_by: >
      Use the cleaner's own dry run with its filters on; the row's uncovered folder made today is not
      listed, the check passes and the row fails
  - id: AC3
    text: >
      The check fails while any one of the cleaner's five path classes maps to no kind; one row per class
    falsified_by: >
      Leave the build root rule out; the row for folders under the cache folder passes and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The outside cleaner cannot ask the ledger and runs as it did before; it is not
  retired.
---

## Intent

An outside cleaner must not delete what the ledger says to keep, and it can be retired only when the
ledger covers everything it would have cleaned. The CLI's covers verb answers, per path, whether an item
holds it and whether to keep it. The retirement check lists the cleaner's candidates with its age and size
tests off, and passes only when every one is a ledger item.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 11 (the nightly script and its
retirement check) and 6.10 (the paths outside the repository). Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: CLI (covers), Ledger. The outside cleaner on the measured host is the nightly script.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
