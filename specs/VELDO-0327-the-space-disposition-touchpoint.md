---
schema: veldo.spec/v1
id: VELDO-0327
title: "The space disposition touchpoint"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0317]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_request_settlement.py"
  - ".veldo/control_request_settlement.py"
  - "scripts/suites/*_veldo_0327_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0327-the-space-disposition-touchpoint.md"
  - "specs/index.md"
  - "proof/VELDO-0327/**"
behavior_bearing: true
observability:
  logs: >
    The settlement's effect record carries the choice that was answered. The request's terms hold the list
    of files Discard would lose.
  error_taxonomy: >
    unmatched_choice for an answer naming a choice that was not offered. An answer that does not bind the
    current presentation settles nothing.
acceptance_criteria:
  - id: AC1
    text: >
      The journey has a touchpoint space disposition, presented as a decision and answered by the project
      owner. Its request for one worktree offers exactly three choices, the picks accept save, accept keep
      and accept discard (a review group's request adds the member picks of VELDO-0342); each settles with
      the ruling approve, and the effect record carries the choice
    falsified_by: >
      Offer the bare words save, keep and discard; none maps to a ruling, the channel does not present the
      request, and the row that waits for the presentation fails
  - id: AC2
    text: >
      The request's terms state that Discard cannot be undone and hold, for each worktree, the list of
      files it would lose and, for a detached worktree with commits no ref holds, the name of the kept
      branch those commits go to. The presentation shows both, and the Ledger raises no request that
      offers the discard pick without that list. The control path has no tier field and none is added
    falsified_by: >
      Raise the request with an empty list; the row that reads the presentation finds discard offered with
      nothing listed and fails
  - id: AC3
    text: >
      The effect is applied once, in the settlement's own transaction, from the recorded choice; an answer
      naming a choice that was not offered is refused as unmatched_choice, and an answer that does not
      bind the current presentation settles nothing
    falsified_by: >
      Read the ruling and not the choice; the row that answers accept keep finds the worktree saved or
      discarded and fails
  - id: AC4
    text: >
      The five existing touchpoints, their rulings and their effects are unchanged, and
      authority_contract's ruling set still has three members
    falsified_by: >
      Add save, keep and discard to the ruling set; the row that reads the set finds six and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. The journey has its five touchpoints again, and a request already raised on space
  disposition can no longer be presented or settled.
---

## Intent

The owner's answer on a worktree with unique work goes through the settlement path that already exists.
This ticket adds one touchpoint to its journey, space disposition, whose three answers are the picks
accept save, accept keep and accept discard. The set of rulings and the five existing touchpoints do not
change.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (which touchpoint, and the choice
paragraph), 6.6 (the answers are not new routes) and 6.11. Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Settlement journey. It adds one entry to the journey configuration of
> control_request_settlement.py. It changes none of the five entries that exist, and it changes neither the
> ruling set of authority_contract.py nor the choice map of control_channel_presentation.py.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
