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
- 2026-11-14: built. No acceptance criterion changed. What the build found and decided:
  - What compose writes, measured on both engines of the host (contexts default, engine 29.3.0, and
    desktop-linux, 29.2.1; compose 5.0.2) with a project made for the check and taken down after it
    (proof/VELDO-0307/compose-labels.json): a container carries com.docker.compose.project.working_dir
    and com.docker.compose.project.config_files, both as absolute paths, and the engine reports a bind
    mount's source as the host path. A network and a volume carry neither label. So on these engines
    this rule places containers only; a network or a volume of the same compose project stays a report
    with no proposed owner. The adapter reads the labels on every kind all the same. Tying a volume to
    a worktree through its compose project name is not in this ticket and was not built.
  - Which worktree a path is inside is the reconciler's (control_space_reconcile.worktree_inside): by
    where the path leads, every link followed, compared with the worktree's recorded path by whole
    segments. What cannot be decided gives no proposal: a path that is not absolute or holds a ..
    segment (and then nothing is placed by the object's other paths either), paths that lead into two
    recorded worktrees, a worktree that is removed or gone. An object the engine showed without its
    identity gets no proposal, as it gets no item in VELDO-0306.
  - The rule is for an object with no run label: one that carries the run's label, known or not, or a
    known run's compose name, is judged as VELDO-0306 judges it and is never proposed to a worktree.
  - The adapter applies the rule only when it is given the reconciler (Adapter(reconcile=...)). Without
    it an object is a report with no proposed owner, which is the rollback. Nothing sets
    Service.space_docker yet, so no adapter runs in a service; the ticket that builds it passes both.
  - The protect list comes first, in the adapter (covered): by name, by compose project label and by
    labelled path (compose's working folder or one of its files at, above or beneath a protected path,
    on every engine). A covered object is listed (Adapter.protected_objects) and gets nothing else; a
    report written before the list covered it is marked gone, which removes nothing. The ledger still
    refuses a protected name or compose project at adopt and at report.
  - Images are read for the protect list only (Adapter.images): an image the list covers by a name it
    carries (a tag in full, or its repository without the tag or the digest), by its compose project
    label or by its labelled path is listed as protected. Nothing is written for any image, and the
    snapshot does not read images: image tags as items are VELDO-0328.
  - This ticket adds no way to delete. The adapter and the reconciler give an engine ls and inspect
    only. An object adopted in act mode is an item like any other and goes at its owner's ending event
    through Signal, the safety rules, the keep step where it applies and the removers.
  - Seen and left alone, outside this ticket's footprint, for the lead: (1) rule 2 at removal
    (control_space_signal) reads a Docker item's name, compose project and mounts, and not its labelled
    path. A container adopted while nothing covered it, whose compose folder a later edit of the
    protect list covers, is listed as protected by the adapter from its next snapshot on, but its item
    stays and rule 2 would not refuse it. VELDO-0341 or 0330 owns rule 2. (2) The ledger matches an
    image tag item against the image patterns by the tag in full, so the pattern minio/minio does not
    match the tag minio/minio:latest there; the adapter's listing matches the repository too. VELDO-0328
    records image tags and should match the same way.
  - One earlier mutation case moved with the code: space306-compose-project-not-in-the-locator carries
    a second edit, because the adapter now reads the compose project label against the protect list
    itself before the ledger does, and the defect needs both readings gone. Its row is red as before.
