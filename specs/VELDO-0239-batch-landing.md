---
schema: veldo.spec/v1
id: VELDO-0239
title: Batch landing - several reviewed units of a project are assembled onto trunk in one candidate, colliding migrations are renumbered by the project's own hook, the candidate is gated once with every red inventoried, and all land together on one owner approval
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0042, VELDO-0057, VELDO-0058, VELDO-0068, VELDO-0148, VELDO-0216, VELDO-0220, VELDO-0235]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_batch*.py"
  - ".veldo/control_batch*.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "engine/.veldo/control_landing*.py"
  - ".veldo/control_landing*.py"
  - "engine/.veldo/control_verification.py"
  - ".veldo/control_verification.py"
  - "engine/.veldo/control_project.py"
  - ".veldo/control_project.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "engine/.veldo/control_intake*.py"
  - ".veldo/control_intake*.py"
  - "engine/.veldo/control_channel_presentation*.py"
  - ".veldo/control_channel_presentation*.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "engine/ui/src/**"
  - "scripts/suites/*_veldo_0239_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0239-batch-landing.md"
  - "specs/index.md"
  - "proof/VELDO-0239/*"
behavior_bearing: true
observability:
  logs: >
    Record each batch with its project, trunk watermark, the units in it in merge order with each unit's
    reviewed commit, each unit left out and why, each renumber hook run with its exit status and the files it
    renamed (old and new name), the batch tip, the gate observation, the red inventory, the approval and the
    landing receipt.
  metrics: >
    Count batches by outcome (green, red, landed, trunk_moved, refused), units per batch, units left out by
    reason, reds per batch and gate duration per batch.
  traces: >
    Join each landed unit to its batch, the batch to its gate observation and approval, and each red to the
    stage and check that reported it.
  error_taxonomy: >
    Keep the landing's names (VELDO-0057, VELDO-0148, VELDO-0235). A unit whose merge conflicts is left out as
    conflict:<unit>; a renumber hook that exits non-zero leaves out the unit just merged as
    hook_failed:renumber:<unit>; a batch with no reviewed unit is empty and runs nothing; an approval bound to
    another batch tip or unit list is stale_subject:batch; a red batch asked to land is refused as
    missing_evidence:gate.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a batch assembles every reviewed unit of a project onto its trunk in one candidate, and colliding
      migrations are renumbered only by the project's own hook. Set: the owner's command (Telegram /batch
      <project>, or the UI's project view) starts a batch of every unit of that project whose independent
      review has passed and that has not landed, merged in review-completion order onto the trunk watermark in
      a VELDO-0042 isolated clone. After each merge the project's renumber hook, a command named in the
      project's work configuration, runs in the clone with the watermark and the merge commit; its changes are
      committed as a separate renumber commit and recorded; the factory itself renames no file. A unit whose
      merge conflicts, or whose hook run fails, is left out by name and the batch goes on with the others; a
      project with no hook merges with no renumbering. Rows on a fixture repository with two units that each
      add migration 037 and a hook that renumbers to the next free number: batch/renumber requires 037 and 038
      in the batch tip and the hook's commit recorded; batch/conflict adds a third conflicting unit and
      requires it left out and the other two in.
    falsified_by: >
      Merge the units without running the hook, and the batch/renumber row must fail on two files numbered 037.
  - id: AC2
    text: >
      Claim: the batch is gated once and every red is inventoried. Set: the batch tip is gated by one
      VELDO-0058 candidate gate under the host lock (VELDO-0220); in batch mode no stage of the declared graph
      (VELDO-0216) is skipped because another stage is red, so the observation lists every stage as green or
      red with every failing check it reports. The inventory names each red with its stage, check and the
      units whose changes touch the paths it names (or none), and goes to the owner and into the batch
      record; each named unit returns to its own fix round, and nothing of a red batch lands. Rows:
      gate/once requires exactly one gate run per batch; gate/inventory makes two stages red and requires both
      in the inventory with their checks.
    falsified_by: >
      Stop the gate at the first red stage, and the gate/inventory row must fail on the second red stage
      missing.
  - id: AC3
    text: >
      Claim: a green batch lands together on one owner approval. Set: one approval request (VELDO-0068) shows
      every unit with its review, the renumber commits, the gate observation and the project's landing
      destination (VELDO-0235); its bound subject is the batch tip and the unit list, so a change to either
      refuses the landing as stale_subject:batch and asks again. Any other approval a unit already needs, such
      as a protected path, is still asked; the batch approval never replaces it. Publication is one
      compare-and-swap of the trunk from the watermark to the batch tip, push or local as the project's
      destination says; each unit gets its revision_landed receipt naming the batch. A trunk moved after the
      watermark re-lands the batch under VELDO-0148: re-merge, re-run the hook, re-gate and ask again. Rows:
      land/together requires the trunk at the batch tip and a receipt per unit; land/stale changes the unit
      list after the grant and requires the refusal.
    falsified_by: >
      Land each unit of the batch by its own compare-and-swap, and the land/together row must fail on more
      than one trunk move.
  - id: AC4
    text: >
      Claim: landing a single unit is unchanged. Set: a unit not in a batch is gated and landed exactly as
      today; the landing suites of VELDO-0057, VELDO-0148 and VELDO-0235 pass unchanged.
    falsified_by: >
      Route a single unit's landing through the batch path, and VELDO-0057's exact-tip row must fail on the
      batch record it does not expect.
required_evidence: [unit, integration, ui_states]
rollback: >
  Stop starting batches, then revert; units of an unlanded batch return to single-unit landing with their
  reviews intact. A landed batch is ordinary commits on the trunk and stays. No automatic rollback is
  authorized.
---

## Intent

The owner's rule for gates (Telegram 37189, 37201) is the QA rule: never a full gate per ticket, but one
gate for a batch of everything finished, every failure from that run back to its ticket, and the batch
landed together. Veldo gates and lands each unit by itself, so a project like core, with a full gate of about
an hour, would gate dozens of times a day and the migrations two tickets add with the same number would
collide on trunk. This adds a batch: assemble, renumber through the project's own hook, gate once, inventory
every red, land on one approval.

## Context

- The lander builds a candidate on a watermark and merges the build onto it; publication is a
  compare-and-swap of that watermark (VELDO-0057, lander.py, control_landing.py); a moved trunk re-lands (VELDO-0148).
- The gate runs the project's own verify.sh in candidate mode on a declared stage graph, under the host lock
  (VELDO-0058, VELDO-0216, VELDO-0220).
- A project lands by push or locally (VELDO-0235).
- Parity report research/veldo-parity-2026-11-04.md (myday), kinds 2 and 14, ticket T8.

## Out of scope

When a batch starts by itself (VELDO-0240); the fix rounds themselves, which are each unit's existing
flow; batches across projects; any change to a project's verify.sh or to the gate's stages.

## What the reviewer judges

- Normal use: the owner starts the core batch, two units' migrations are renumbered by core's own script,
  one red goes back to its unit, and after the fix the next batch lands on one approval.
- Threat model: a batch approval covering a unit or tip the owner did not see; a hook run reaching outside
  the clone; a red hidden by an early stop.

## History

- 2026-11-04: drafted from the Veldo parity report, ticket T8, under the owner's decisions to move the work
  to Veldo with local landing for core (Telegram 39047, 39049) and his approval of VELDO-0235 (Telegram
  39065). Not implemented; the owner approves it before it is claimed.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.
