---
schema: veldo.spec/v1
id: VELDO-0306
title: "Docker objects: label, snapshot, events, removal"
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
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "scripts/suites/*_veldo_0306_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0306-docker-objects-label-snapshot-events-removal.md"
  - "specs/index.md"
  - "proof/VELDO-0306/**"
behavior_bearing: true
observability:
  logs: >
    Each object found is an item record or a report, with its engine context, object id and name. Each
    engine event handled is one ledger write or one report.
  error_taxonomy: >
    A volume a container of another run still uses is deferred by the engine's own refusal,
    space_deferred:remove_refused. End of file on an engine's event pipe is not an error: the adapter
    takes a new snapshot and subscribes again.
acceptance_criteria:
  - id: AC1
    text: >
      An object carrying the run's label or compose project name is an item owned by that run, on the
      context it was created on
    falsified_by: >
      Read one context only; the object on the second context has no item and fails
  - id: AC2
    text: >
      An object with no label, no compose project name of a run and no path inside a recorded worktree is
      a report, is never an item, and is never removed
    falsified_by: >
      Attribute it to the only live run; the row with two live runs gives it an owner and fails
  - id: AC3
    text: >
      At run finished the run's containers are stopped and removed, then its networks and volumes, each by
      the engine's non-forced remove; a volume a container of another run still uses is deferred
    falsified_by: >
      Remove volumes first; the engine refuses, the item is deferred, and the row that expects it gone
      fails
  - id: AC4
    text: >
      The engine's event stream is a pipe in the service loop's poll set: an engine event is handled with
      the fixture clock stopped, and end of file on the pipe causes a new snapshot before a new
      subscription
    falsified_by: >
      Read the stream on an interval; with the clock stopped the row's event is never handled and the row
      fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Docker objects are neither recorded nor removed by Veldo.
---

## Intent

A run's containers, networks and volumes are owned through the run's label or its compose project name.
This ticket adds the Docker adapter: the snapshot per engine context, the event stream read as a pipe in
the service loop's poll set, and removal at run finished in the order containers, networks, volumes. An
object nobody can attribute is reported and never removed.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.4 (Docker) and 5 (the container,
network and volume rows). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Docker adapter, Authority service (the poll set). Rows run against a stand-in engine; one
> integration row runs against a real one with objects the row itself creates.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
