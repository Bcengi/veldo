---
schema: veldo.spec/v1
id: VELDO-0341
title: "Protected Docker objects, by name and by compose label"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0296, VELDO-0330]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_space_probe.py"
  - ".veldo/control_space_probe.py"
  - "engine/.veldo/control_space_docker.py"
  - ".veldo/control_space_docker.py"
  - "engine/.veldo/control_space_reconcile.py"
  - ".veldo/control_space_reconcile.py"
  - "scripts/suites/*_veldo_0341_*.py"
  - "scripts/suites/137_veldo_0330_space_rules.py"
  - "scripts/suites/145_veldo_0307_space_docker_ownership.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0341-protected-docker-objects-by-name-and-by-compose-label.md"
  - "specs/index.md"
  - "proof/VELDO-0341/**"
behavior_bearing: true
observability:
  logs: >
    A protected object appears in space.protected with the entry that matched it, and in no other read.
  error_taxonomy: >
    None of its own. A Confirm, a discard answer and a released record that would reach a protected object
    remove nothing.
acceptance_criteria:
  - id: AC1
    text: >
      An object is protected when its name matches a pattern or its compose project label equals a
      protected project name, either one, on every engine the installation names; the rows are a volume
      matched by name with no label and a container matched by label under another name, each on two
      contexts
    falsified_by: >
      Test the name only; the row's container named otherwise gets an item and fails
  - id: AC2
    text: >
      A container that mounts a protected volume or path is protected, and so are the image it was made
      from and the networks it is attached to; a container that only runs an image whose name is protected
      is not
    falsified_by: >
      Protect every container of a protected image; the row's run container made from that image is still
      there after run finished and the row fails
  - id: AC3
    text: >
      A protected object has no item, no proposed owner and no Adopt action, and is in no pending group
      and no decision request, in report mode and in act mode; a Confirm, a discard answer and a released
      record that would reach one remove nothing
    falsified_by: >
      Read the list at removal only; the row's protected volume shows under Reports with a proposed owner
      and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. A Docker object is protected by its name pattern only, and a container matched only
  by its compose label is no longer protected.
---

## Intent

The protect list holds things Veldo must never touch: database volumes with real data, a protected
project's containers and images. An object is protected by its name or by its compose project label,
either one, on every engine. A protected object has no item, no proposed owner and no place in any
request, in report mode and in act mode.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 7 (the protect rule), 6.8 (the
protect key), 11 (the protect list) and 6.6 (space.protected). Section 12 of the design holds the ticket
itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Probes (the protect list), Docker adapter, Reconciler. Depends on 0296 and 0330.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). depends_on holds the dependencies the
design states for this ticket.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-15: fix round after the review (verdict FIX, two findings; removal safety held). Finding 1:
  a network or an image seen before its protected container stayed a report with an Adopt action
  until the next full read. A container found protected, on its event or in the snapshot, now has
  its networks and its image asked for and judged again at once, and a network's connect and
  disconnect events are read as its create event is. Finding 2: a pass reads the containers once
  (one list and one inspect for each container; the snapshot uses the records it already holds) and
  judges every image and network by that read; when a container cannot be read, every image and
  network the pass would judge is refused. Rows fix1/compose-order, fix1/snapshot-image,
  fix1/connect-event, fix1/disconnect-event, fix2/one-read-per-pass and fix2/unreadable-refuses,
  with seven registered cases. One anchor of a VELDO-0307 case moved with its line; the case is
  unchanged and still rejected. The removal probe is unchanged.
- 2026-11-15: build footprint includes two earlier suite fixtures. Rule 2 now reads the
  image and network relationships of every container; suite 137 supplies those inspect fields
  and resolves inspect by Id. Suite 145 permits the additional read-only container queries when
  listing protected images. Neither change removes a behavioral assertion. On base 8ef46604
  the public Space reads and owner Confirm-group and Discard handlers are absent. This ticket
  proves discovery has no item or report to offer and exercises both removal purposes at the
  existing shared rules seam; it does not build the absent handlers or claim their integration.
- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
