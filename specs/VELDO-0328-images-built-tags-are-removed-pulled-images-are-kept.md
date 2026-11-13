---
schema: veldo.spec/v1
id: VELDO-0328
title: "Images: built tags are removed, pulled images are kept"
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
  - "scripts/suites/*_veldo_0328_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0328-images-built-tags-are-removed-pulled-images-are-kept.md"
  - "specs/index.md"
  - "proof/VELDO-0328/**"
behavior_bearing: true
observability:
  logs: >
    A built tag is an item record with its engine context. A pulled image is recorded once per engine as
    kept.
  error_taxonomy: >
    A tag a container still uses is deferred by the engine's refusal, space_deferred:remove_refused.
acceptance_criteria:
  - id: AC1
    text: >
      An image tag a run built is an item owned by that run's ticket and is removed at landed and at
      ticket ended by the engine's non-forced remove on the tag; a tag a container still uses is deferred
    falsified_by: >
      Remove by image id; the row whose image carries a second tag of another ticket loses that tag and
      fails
  - id: AC2
    text: >
      An image a run pulled is recorded once per engine as kept, has no ending event, and is still present
      after its run's ticket ended
    falsified_by: >
      Record a pulled image as an item of the run that pulled it; the row finds it removed at ticket ended
      and fails
  - id: AC3
    text: >
      An image whose name is on the protect list gets no item on either engine context, even when a run
      tags a build with that name
    falsified_by: >
      Check the protect list on the first context only; the row on the second context gets an item and
      fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Image tags are neither recorded nor removed.
---

## Intent

An image tag a run built belongs to that run's ticket and goes when the ticket lands or ends, by the
engine's non-forced remove on the tag. An image a run pulled is kept, because nothing in Veldo can prove
it can be pulled again. A protected image name gets no item on any engine.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.4 (images), 5 (the image tag row)
and 7 (the protect rule). Section 12 of the design holds the ticket itself; its acceptance criteria and
falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Docker adapter.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
