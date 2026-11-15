---
schema: veldo.spec/v1
id: VELDO-0333
title: "The gate's leg-time store loses its removal by age"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [enforcement]
protected_paths: ["engine/scripts/gate_legs.py", "scripts/gate_legs.py"]
footprint:
  - "engine/scripts/gate_legs.py"
  - "scripts/gate_legs.py"
  - "scripts/suites/*_veldo_0333_*.py"
  - "scripts/suites/111_veldo_0214_first_use_budget.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0333-the-gates-leg-time-store-loses-its-removal-by-age.md"
  - "specs/index.md"
  - "proof/VELDO-0333/**"
behavior_bearing: true
observability:
  logs: >
    The line a gate prints when it removes a timing file names the missing checkout only.
  error_taxonomy: >
    None new.
acceptance_criteria:
  - id: AC1
    text: >
      A leg-time file older than 30 fixture days whose authority checkout exists stays when a gate writes
      its timing
    falsified_by: >
      Leave the age branch in prune_times; the row finds the old file gone and fails
  - id: AC2
    text: >
      A leg-time file whose authority checkout is gone is still removed at a gate's own write, and the
      file just written never is
    falsified_by: >
      Drop the whole function; the row finds the file of the missing checkout present and fails
  - id: AC3
    text: >
      prune_times reads no file time and no clock and leaves a .pending- file alone; its description, the
      module text and the line a gate prints name the missing checkout only; the canon and the synced copy
      under scripts/ agree
    falsified_by: >
      Change the canon alone; the row that reads the synced copy finds the age test and fails
  - id: AC4
    text: >
      read_resources still ignores a resource measurement older than 30 days, under a constant whose name
      says it bounds a read, and deletes nothing: the old file is there after the read
    falsified_by: >
      Delete the constant with the age branch; the row's 31-day-old measurement is returned as current and
      the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change in the canon and in the synced copy. Leg-time files older than 30 days are deleted at
  a gate's write again.
---

## Intent

The gate's leg-time store deletes a timing file for being older than 30 days. That is a removal by age,
and nothing in Veldo removes by age. This ticket deletes that branch. A timing file whose authority
checkout is gone is still removed, at a gate's own write. The 30-day value stays only where it bounds a
read.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.10 (the gate_legs.py row of the
Replaced table), 6.2 (the rule for removal by age) and 13 (the decision that nothing removes by age).
Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here
word for word.

What section 12 says about this ticket:

> Components: Gate leg timing (protected, policy.yaml:54-55; the owner's recorded approval is required). The
> synced copy under scripts/ changes with the canon.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

engine/scripts/gate_legs.py and its synced copy under scripts/ are protected paths (policy.yaml:54-55).
The owner's recorded approval, bound to the commit and the proof, is required.

## History

- 2026-11-15: build footprint includes the existing VELDO-0214 budget suite: its timing-store row
  expected age removal of an old live-checkout file and a pending file. Those two expectations now
  require retention, with the missing-checkout and keep checks preserved. Its registered keep
  falsifier follows the simplified condition. No acceptance criterion changed. The missing-checkout
  probe uses stat and accepts only FileNotFoundError as absence; an unreadable checkout stays.
- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
