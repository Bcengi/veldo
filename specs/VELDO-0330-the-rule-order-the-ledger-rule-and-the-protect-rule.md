---
schema: veldo.spec/v1
id: VELDO-0330
title: "The rule order, the ledger rule and the protect rule"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0299]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_signal.py"
  - ".veldo/control_space_signal.py"
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "scripts/suites/*_veldo_0330_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0330-the-rule-order-the-ledger-rule-and-the-protect-rule.md"
  - "specs/index.md"
  - "proof/VELDO-0330/**"
behavior_bearing: true
observability:
  logs: >
    A deferral records the first rule that refused, by name, the event it was refused at and the event
    that retries it.
  error_taxonomy: >
    space_deferred:not_in_ledger, space_deferred:protected, space_deferred:in_use,
    space_deferred:unique_work and space_deferred:remove_refused. One per refusal, named by the first rule
    that refused.
acceptance_criteria:
  - id: AC1
    text: >
      The rules run in the order of section 7 and the first refusal names the deferral
    falsified_by: >
      Run unique work before protect; the protected worktree with an edit is deferred as unique_work and
      the row fails
  - id: AC2
    text: >
      Rule 1 refuses a thing that is not the item recorded: a path that now resolves elsewhere through a
      link, a folder replaced by another repository's worktree, a Docker name now held by another object
      id
    falsified_by: >
      Compare the locator's text only; the row replaces the folder with a link, finds the link's target
      removed, and fails
  - id: AC3
    text: >
      A locator at or above a protect entry, or with one beneath it, is protected, and no event, no
      Confirm and no Discard removes it
    falsified_by: >
      Skip the protect rule in the discard remover; the row's protected worktree is removed on a discard
      answer and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change together with the removers. Without the rule order nothing may be removed.
---

## Intent

Every removal passes seven rules in one order, and the first that refuses names the deferral. This ticket
fixes that order and adds the two rules that are not probes of use: the ledger rule, which refuses a thing
that is no longer the item recorded, and the protect rule.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (the safety rules: their order,
rule 1 and rule 2). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: the rule order of section 7. Depends on 0299.

Build order. It is built together with 0298, 0299, 0330 and 0300, after the first five tickets. depends_on
holds the dependencies the design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The design's component table names no module for the rule order. The footprint takes Signal, which runs
the rules, and Probes, which holds the protect list.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
