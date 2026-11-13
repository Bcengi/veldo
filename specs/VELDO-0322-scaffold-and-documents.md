---
schema: veldo.spec/v1
id: VELDO-0322
title: "Scaffold and documents"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0321]
placement: [engine, docs]
protected_paths: []
footprint:
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "docs/setup.md"
  - "docs/installation.md"
  - "docs/runbook.md"
  - "scripts/suites/*_veldo_0322_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0322-scaffold-and-documents.md"
  - "specs/index.md"
  - "proof/VELDO-0322/**"
behavior_bearing: true
observability:
  logs: >
    None beyond what init already reports about the files it lays down.
  error_taxonomy: >
    None new. The docs check refuses a document that names a project.
acceptance_criteria:
  - id: AC1
    text: >
      init lays .veldo/space.yaml in a new project, with every key of 6.8 present and commented
    falsified_by: >
      Leave the file out of the scaffold; the row that runs init finds no file and fails
  - id: AC2
    text: >
      docs/setup.md and docs/installation.md describe the space section, the project file, the hooks and
      the run wrapper, and pass the docs check
    falsified_by: >
      Write a project name into either document; the docs check row fails
  - id: AC3
    text: >
      docs/runbook.md gains the situations "the disk is full or a run is waiting for space" and "a
      worktree is waiting for the owner's answer", and passes the docs check
    falsified_by: >
      Name the measured host's project in the runbook; the docs check row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. init lays no space file, and a project without one gets the defaults.
---

## Intent

A new project gets its space file from init, and the documents say how space management is set up and what
to do when the disk is full or a worktree waits for the owner's answer. The documents are generic: they
name no project.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.8 (declarations) and 3 (the
scaffold). Section 12 of the design holds the ticket itself; its acceptance criteria and falsifiers are
copied here word for word.

What section 12 says about this ticket:

> Components: Scaffold, documents.

Build order. It is in the closing sequence 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319,
0320, 0332, 0325, 0339, 0321, 0322. The design states no dependency for this ticket, so depends_on holds
the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
