---
schema: veldo.spec/v1
id: VELDO-0332
title: "Wrong proposals and the switch to act"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0331, VELDO-0320]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/src/app/navigation.ts"
  - "scripts/suites/*_veldo_0332_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0332-wrong-proposals-and-the-switch-to-act.md"
  - "specs/index.md"
  - "proof/VELDO-0332/**"
behavior_bearing: true
observability:
  logs: >
    One wrong-proposal record per mark, with the scope, the subject, the owner's reason and the day. A
    switch's history records the three days that were counted.
  error_taxonomy: >
    A refused switch names the day that failed and why. reject is refused when it is not signed by the
    owner, or when its subject is not a due item, an adopted item or a report with a proposed owner.
acceptance_criteria:
  - id: AC1
    text: >
      Marking a proposal wrong writes one record with the scope, the subject, the owner's reason and the
      day in the installation's time zone. A due item goes to kept and leaves its Confirm group, an
      adoption becomes a report with no owner, a proposed Docker owner is dropped
    falsified_by: >
      Leave the marked item in its group; the row that confirms the group afterwards finds the marked
      folder gone and fails
  - id: AC2
    text: >
      The switch to act for a scope is refused until its three calendar days before today were each a
      clean report day and no wrong mark is dated today; the refusal names the day that failed and why. A
      mark on day 2 restarts the count
    falsified_by: >
      Count days without reading the wrong-proposal records; the row with a mark on day 2 is switched to
      act on day 4 and fails
  - id: AC3
    text: >
      A day with no event, Signal call or reconcile for the scope is not clean: three idle days do not
      allow the switch
    falsified_by: >
      Count every day in report mode as clean; the row with three idle days is switched to act and fails
  - id: AC4
    text: >
      The three days are read from the records when the owner sends the command, and nothing switches a
      mode by itself: with the fixture clock moved thirty days and no command, every scope is still in
      report mode
    falsified_by: >
      Switch to act by itself once three clean days exist; the clock row finds a scope in act with no
      owner command and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Switch every scope back to report, then revert the change. Wrong-proposal records stay in the journal.
---

## Intent

The owner can mark a proposal wrong, and a project earns act mode by not needing that. The switch to act
is the owner's signed command, refused until the scope's three calendar days before today were each a
clean report day. The days are read from the records when the owner sends the command. Nothing counts them
down, and nothing switches a mode by itself.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 4.7 (mode record), 4.8
(wrong-proposal record), 6.1 (reject and mode) and 11 (migration). Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Ledger (reject, mode, the wrong-proposal record), API, Console. Depends on 0331 and 0320.
> The two other conditions of the switch are VELDO-0339.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
