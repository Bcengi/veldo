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
  - "engine/.veldo/control_space_remove.py"
  - ".veldo/control_space_remove.py"
  - "scripts/suites/*_veldo_0328_*.py"
  - "scripts/suites/138_veldo_0300_space_remove.py"
  - "scripts/suites/147_veldo_0310_landed_contained.py"
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

- 2026-11-15: built the adapter completion seams `built(engine, tag, label, image_id)` and
  `pulled(engine, name)`, and image pull event handling. A trusted build creator names its tag,
  known run and expected image identity; inherited image labels and tag events alone prove no
  build. The adapter records only that tag, never its sibling tags. Project build-command wiring
  is not part of this adapter ticket; no service sets the adapter up yet on this branch.
- A pulled image is an ownerless ledger report, keyed by image identity and engine, with disposition
  kept and no ending events. Repeated pulls and adapter restarts reuse it. The footprint adds the
  existing remover and its synced copy: AC2 also holds when the pull follows a build, so that
  remover reads the durable kept report before removing a built tag. No removal primitive or
  lifecycle event was added. The existing keep step for repositories and snapshots is unchanged.
- Proof uses two strict stand-in engines and real ledger, Signal, rules, owner signatures and
  removers. A non-forced remove by image id with multiple tags is refused by the stand-in; the
  declared AC1 falsifier turns the row red because the owned tag remains, while the row also checks
  the other ticket's planted content survives. No acceptance criterion was changed.
- Targeted checks only. The lead runs `./scripts/verify.sh` through the gate lock. The existing
  VELDO-0127 captures, policy check, real engines and protected host data were not touched.

- 2026-11-15, fix round after review (verdict FIX, three findings). No acceptance criterion was changed.
  1. The image remover now runs `image rm --no-prune <tag>`. Without the option a classic image store
     deletes, with a build's last tag, the image's untagged parents that have no other child: an image
     Veldo did not build, a `docker commit` result for example. Row ac1/untagged-parent: such a parent
     and its planted content survive the removal on both engines. The stand-in engine now prunes as the
     classic store does unless it is given exactly that option.
  2. The row "an unread pull inventory refuses removal" gave no reader of free space, so the removal was
     refused before the pulled-image check and the row proved nothing. It now gives one, shows the same
     call on a read ledger removing a twin tag, and holds that the unread inventory raises out of
     remove() with nothing removed; a second check drives it through Signal. The docstring of
     `_pulled_image` said the error became the remover's refusal; it raises out of remove(), and now
     says so.
  3. Rows ac1/unknown-run (an unlabelled image built for an unknown run gets no item and is kept) and
     safety/option-name (a name starting with "-" is refused before the client is called).
  Four cases are registered for finding 328, one per row above. The footprint adds two suites, each for
  the one assertion that reads the remover's exact command: 138 (VELDO-0300), whose reading of a prune
  command and of the source's strings now tells `--no-prune` from a prune, and 147 (VELDO-0310).
