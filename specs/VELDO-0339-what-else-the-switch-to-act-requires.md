---
schema: veldo.spec/v1
id: VELDO-0339
title: "What else the switch to act requires"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0332, VELDO-0325]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space.py"
  - ".veldo/control_space.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "engine/.veldo/control_api.py"
  - ".veldo/control_api.py"
  - "engine/ui/src/api/routes.json"
  - "engine/ui/src/features/space/**"
  - "engine/ui/src/views/SpaceView.vue"
  - "engine/ui/src/app/navigation.ts"
  - "scripts/suites/*_veldo_0339_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0339-what-else-the-switch-to-act-requires.md"
  - "specs/index.md"
  - "proof/VELDO-0339/**"
behavior_bearing: true
observability:
  logs: >
    A switch to act records what was checked: the three days, that no pending group was unconfirmed, and
    the state of the gate script.
  error_taxonomy: >
    A refused switch names each open group by scope and kind with its count, and each missing gate call.
acceptance_criteria:
  - id: AC1
    text: >
      With three clean days and one unconfirmed pending group the switch is refused and names the group by
      scope and kind with its count; after Confirm or Wrong on it the switch is accepted
    falsified_by: >
      Read only the day records; the row with an open group is switched to act and fails
  - id: AC2
    text: >
      A confirmed item that a rule deferred does not block the switch, and neither does an open adoption
      or a proposed Docker owner
    falsified_by: >
      Count every due or deferred item as unconfirmed; the row whose only pending item is confirmed and in
      use is refused and fails
  - id: AC3
    text: >
      For a bound project the switch is refused while its gate script fails the gate check, and the
      refusal names the missing call; a plain repository and no project are not asked
    falsified_by: >
      Skip the gate check; the fixture project whose gate lacks the verdict call is switched to act and
      fails
  - id: AC4
    text: >
      space.modes and the Modes section show each scope's unconfirmed groups with their counts and the
      state of its gate, and the history of a switch to act records what was checked
    falsified_by: >
      Leave the groups out of the read; the row that expects the open group beside the Act button finds
      none and fails
required_evidence: [unit, integration, ui_states]
rollback: >
  Revert the change. The switch to act asks for the three clean days only.
---

## Intent

Three clean days are not enough to switch a scope to act. The switch is also refused while the scope has a
pending group the owner has neither confirmed nor marked wrong and, for a bound project, while its gate
script lacks a space step.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.1 (an unconfirmed pending group,
exactly; the gate), 4.7 (the mode record's history) and 6.6 (space.modes). Section 12 of the design holds
the ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Ledger (mode), CLI (space gate-check), API, Console. Depends on 0332 and 0325.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. depends_on holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The refusal this ticket lifts. Since the review of VELDO-0331 the ledger refuses every switch to act as
space_act_unbuilt, naming VELDO-0332 and VELDO-0339, until the check of each exists. When this ticket lands
it installs the check of the condition no_unconfirmed_pending_group (ACT_CONDITIONS in control_space.py,
the Ledger's act_checks) and so removes its part of that refusal, the last one: from then a switch to act
is refused only by a check that fails.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-13: after the review of VELDO-0331 (lead decision): act is refused outright until
  VELDO-0332's check and this ticket's exist. Added to Design that this ticket removes its part of the
  space_act_unbuilt refusal when it lands. No acceptance criterion changed.
- 2026-11-13: from the owner's rule that no work is ever lost (Telegram 41209), design section 0. No
  acceptance criterion changed. The switch to act has one more condition, built by VELDO-0348: a proof
  record of the no-work-is-lost suite, passed on this host, for the space modules and the git in use.
  space.modes shows it with the other conditions.
