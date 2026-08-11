---
schema: veldo.spec/v1
id: WARP-0735
title: A release item could not declare what it touches, because the architecture contract had no area
  for documentation - so two of them shipped uncovered by the check that caught four real mistakes
status: shipped
risk: standard - one area added to the architecture contract. It widens what can be declared and
  narrows nothing. It is not low because the contract is what every placement and footprint check
  reads, and an area whose includes are drawn too broadly would let unrelated changes claim a
  placement they have no business claiming.
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [contracts]
footprint:
  - ".veldo/architecture.yaml"
  - "engine/.veldo/architecture.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-0735-docs-area-in-the-architecture-contract.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      A `docs` AREA EXISTS AND ITS INCLUDES ARE THE DOCUMENTS AND RELEASE MANIFESTS - `docs/**`,
      `plans/**`, and the two `.claude-plugin` manifests. Drawn deliberately narrow: it must cover
      what a release item actually touches and nothing that belongs to another area, because an area
      with sloppy includes lets an unrelated change claim a placement it has not earned.
  - id: AC2
    text: >
      A RELEASE ITEM CAN NOW DECLARE ITS FOOTPRINT, which is the entire point. `WARP-1508` had its
      real footprint restored under `placement: [docs]` in the same change that added the area, so
      the fix is demonstrated by the case that motivated it rather than asserted. Before this, such
      an item had to declare NO footprint, and the footprint-versus-diff dogfood did not cover it.
  - id: AC3
    text: >
      IT WIDENS AND NARROWS NOTHING. Every area that existed still exists with its includes
      unchanged, and no existing spec's placement becomes invalid. A selftest asserts the original
      nine are all still present, so a future edit cannot quietly drop one while adding another.
required_evidence: [unit]
rollback: >
  Remove the area and restore `WARP-1508` to declaring no footprint. Nothing executable depends on
  it; the contract simply stops admitting a placement it now admits.
---

## Outcome

The footprint-versus-diff check caught four genuine mistakes of mine in a single night: two suite
files I forgot to declare, a marketplace manifest, and a held-back README. It works.

It did not cover two release items, because those could not declare a footprint at all. The
architecture contract refuses a footprint without a placement - correctly, since a footprint with no
area is placeless - and it had nine areas, none of which was documentation. A release item is two
documents, a version string and a plan status. `distribution` was the nearest and would have been
false.

So both items followed precedent and declared nothing, and both went out uncovered by the one check
most likely to have caught a mistake in them.

## Why it is fixed now rather than the first time

Once is a quirk you work around and note. Twice in one night is a recurring cost, and the second
occurrence is the evidence that the general case is worth fixing rather than the specific one worth
excusing. It was deliberately not done inside either release item, because editing the architecture
contract to make one's own change pass is exactly the shape of scope creep this method exists to
refuse.

## The includes, and why they are narrow

`docs/**`, `plans/**` and the two `.claude-plugin` manifests. That is what a release item touches: a
method document, a setup document, the plan being released, and the version an adopter installs.
Nothing wider, because an area with generous includes becomes the placement of convenience for
anything that does not fit elsewhere, and then the placement field stops meaning anything.
