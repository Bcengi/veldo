---
schema: veldo.spec/v1
id: VELDO-0307
title: "Docker ownership by compose's working folder and by bind source"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_docker.py"
  - ".veldo/control_space_docker.py"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "scripts/suites/*_veldo_0307_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0307-docker-ownership-by-composes-working-folder-and-by-bind-source.md"
  - "specs/index.md"
  - "proof/VELDO-0307/**"
behavior_bearing: true
observability:
  logs: >
    A report records the object, the proposed owner and the label or mount that gave it. An adoption
    records the rule that proved the owner.
  error_taxonomy: >
    None of its own. A protected object is listed as protected and gets no proposal and no item.
acceptance_criteria:
  - id: AC1
    text: >
      An object whose compose working folder or configuration file label resolves inside a recorded
      worktree has that worktree as proposed owner; so does a container with a bind mount whose host
      source is inside one
    falsified_by: >
      Match the folder name only; the row whose label names a same-named folder outside every worktree
      gets an owner and fails
  - id: AC2
    text: >
      In report mode such an object is a report showing the proposed owner and is not an item; in act mode
      it is adopted with the worktree as parent
    falsified_by: >
      Adopt in report mode; the report-mode row finds an item and fails
  - id: AC3
    text: >
      An object the protect list covers, by its name, its compose project label or its labelled path, is
      listed as protected and gets neither a proposal nor an item; the rows are a volume, a container and
      an image
    falsified_by: >
      Apply the adoption rule before the protect list; the protected container gets a proposed owner and
      the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Objects without a run label stay reports with no proposed owner.
---

## Intent

An object with no run label can still be tied to a worktree: compose stamps the folder it ran in and the
files it read, and the engine reports a bind mount's host source. When either resolves inside a recorded
worktree, that worktree is the proposed owner. In report mode the object is shown with the proposal; in
act mode it is adopted. A protected object gets neither.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.4 (the last two rows of the
ownership table, and the paragraph under it) and 7 (the protect rule). Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Docker adapter, Reconciler.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

The builder checks on both engines that compose writes these labels before relying on them, and records
the result in the proof (design 6.4).

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
