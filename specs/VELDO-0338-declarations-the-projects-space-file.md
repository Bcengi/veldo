---
schema: veldo.spec/v1
id: VELDO-0338
title: "Declarations: the project's space file"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0296]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_config.py"
  - ".veldo/control_space_config.py"
  - "scripts/suites/*_veldo_0338_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0338-declarations-the-projects-space-file.md"
  - "specs/index.md"
  - "proof/VELDO-0338/**"
behavior_bearing: true
observability:
  logs: >
    A refused file is logged with the project, the key and the reason.
  error_taxonomy: >
    An unknown key is refused by the key's name. A missing file is not an error: the project gets every
    default. A project's protect entries add to the installation's and cannot remove one.
acceptance_criteria:
  - id: AC1
    text: >
      A project with no space file gets every default of 6.8 and is not refused
    falsified_by: >
      Require the file; the fixture project without one is refused and the row fails
  - id: AC2
    text: >
      An unknown key in a project's file is refused by name
    falsified_by: >
      Ignore unknown keys; the row whose file misspells the keep key is accepted, the census records the
      folder it meant to keep, and the row fails
  - id: AC3
    text: >
      A project's protect entries add to the installation's and cannot remove one
    falsified_by: >
      Let the project list replace the installation list; the installation's protected volume pattern is
      gone from the result and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Project space files stay in their repositories and are not read.
---

## Intent

A project declares its worktree root, branch pattern, landing refs, build output rules, keep list, needs
and protect additions in .veldo/space.yaml. This ticket reads that file, gives the defaults when it is
absent, and refuses an unknown key by name.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.8 (a project's .veldo/space.yaml).
Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are copied here
word for word.

What section 12 says about this ticket:

> Components: Declarations reader.

Build order. It is one of the first five tickets, built in the order 0296, 0338, 0297, 0326, 0331. The
design states no dependency for this ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
