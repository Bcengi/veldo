---
description: Assemble and validate the Veldo proof manifest for the current change.
allowed-tools: Read, Grep, Glob, Write, Bash
---

Build the proof manifest for: $ARGUMENTS

Requirements: the gate must be green for HEAD (run /veldo:gate first if not).
Write proof/<spec-id>/manifest.json in the veldo.proof/v1 shape (see
.veldo/examples/proof-example.json): every acceptance criterion mapped to
specific evidence, the exact commit, every check executed, and rollback
instructions. A criterion without evidence fails the manifest.

For design-lane specs (design_review, baseline, or figma_composite in the
required evidence): DRIVE the named journeys end to end first and assert
behavior at each step (flows are the primary UI proof; screenshots are the
fidelity layer), then capture the named UI states, record the interaction,
export the design frame via the design tool's API, and build side-by-side
composites with a diff strip into proof/<spec-id>/visual/. Deliver the
composites to the judging human; never ask a human to assemble a comparison.

Record spec_revision in the manifest when the spec declares a revision, so a later spec revision invalidates this proof. Validate: python3 .veldo/validate.py proof <manifest>. Append an
impl.completed event to .veldo/events.jsonl.
