---
schema: veldo.spec/v1
id: VELDO-0235
title: Each project has a landing destination, land and push or land locally, so a repository that never pushes can run through the factory
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0057, VELDO-0076, VELDO-0148, VELDO-0153, VELDO-0145]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_project.py"
  - ".veldo/control_project.py"
  - "engine/.veldo/control_landing.py"
  - ".veldo/control_landing.py"
  - "engine/.veldo/control_landing_station.py"
  - ".veldo/control_landing_station.py"
  - "engine/.veldo/lander.py"
  - ".veldo/lander.py"
  - "engine/.veldo/control_effect_executor.py"
  - ".veldo/control_effect_executor.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_api*.py"
  - ".veldo/control_api*.py"
  - "engine/ui/src/features/**"
  - "scripts/suites/*_veldo_0235_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0235-a-project-can-land-locally-without-pushing.md"
  - "specs/index.md"
  - "proof/VELDO-0235/*"
behavior_bearing: true
observability:
  logs: >
    Every land dispatch records the project's landing destination it ran under; a local landing records
    the trunk ref, the old tip and the new tip it moved; a change of destination records the project, the
    old and new value and the owner's command id.
  metrics: >
    Count landings by destination and outcome (landed, trunk_moved, refused, unknown).
  traces: >
    Join each landing to the destination value its approval was bound to and to the command that set it.
  error_taxonomy: >
    Keep the landing's names (VELDO-0057, VELDO-0148). A destination outside the two values is
    invalid_input:landing_destination; a change by anyone but the project's owner is refused as today's
    project commands refuse; an approval bound to another destination is stale_subject:landing/destination;
    a local trunk that moved since the watermark is trunk_moved, re-landed as VELDO-0148 says.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: the project record holds a landing destination with exactly two values, land_and_push and
      land_locally, set only by the project owner's signed command. Set and completeness: a record without
      the field reads as land_and_push and is never rewritten for it, so every existing project keeps
      today's landing; a new control_project operation sets it, signed and checked as the existing
      operations are (active person, project_owner in scope, the owner the record names); any other value
      is refused as invalid_input:landing_destination and an unsigned or other principal's command is
      refused, writing nothing.
    falsified_by: >
      Read a record without the field as land_locally, and the existing-project row must fail on a land
      that publishes nothing.
  - id: AC2
    text: >
      Claim: land locally makes the approved candidate the project's local trunk and pushes nothing. Set:
      every check before publication is today's (subject re-read, gate observation, each required approval
      bound to the exact subject); publication is a compare-and-swap of the local refs/heads/<trunk> from
      the recorded watermark (the local trunk tip) to the candidate commit; completion re-reads that local
      ref and writes the same revision_landed receipt. No remote is listed, fetched or pushed and no push
      credential is read. A local trunk moved after the watermark ends as trunk_moved and re-lands under
      VELDO-0148. Rows on a fixture repository whose origin is a bare repository wrapped by a logging Git:
      main equals the candidate, the receipt exists, the bare repository is byte for byte unchanged and the
      log shows no push, fetch or ls-remote; a moved local main is refused and never overwritten.
    falsified_by: >
      Have land locally also push, and the local row must fail on the bare repository's changed ref and
      the logged push.
  - id: AC3
    text: >
      Claim: the destination is shown and bound. Set: the project view in the UI and every landing brief
      the owner answers (the approval request and VELDO-0148's re-land grant) name the destination in
      words, "land and push to <remote>" or "land locally on <trunk>, nothing pushed", and the approval's
      bound subject includes it, so a destination changed after a grant refuses the landing as
      stale_subject:landing/destination and asks again.
    falsified_by: >
      Leave the destination out of the bound subject, and the row that changes it after the grant must
      fail by landing.
  - id: AC4
    text: >
      Claim: land and push is unchanged. Set: with land_and_push, set or absent, the effect contract, the
      push, the remote re-read and the receipt are byte for byte today's; the existing landing suites of
      VELDO-0057, VELDO-0148 and VELDO-0153 pass unchanged.
    falsified_by: >
      Route land_and_push through the local path, and VELDO-0057's exact-tip row must fail on the remote
      that never moved.
required_evidence: [unit, integration, ui_states]
rollback: >
  Set every land_locally project back to land_and_push by the owner's signed command, then revert. A
  local landing already made is an ordinary commit on the local main and stays; nothing was pushed.
---

## Intent

Veldo's landing ends by pushing the approved commit to the project's GitHub remote. Some projects never
push: our core repository lands by moving its local branch only. The owner wants such a project to run
through the factory with the same gate and the same approval, and only the last step different: the
approved commit becomes the local main and nothing leaves the host. Owner decision, Telegram 39047
(2026-11-04); background in the cutover research, gap 5.

## Context

- control_landing.Landing.publish asks the VELDO-0028 effect executor for a force-with-lease push of the
  exact old tip, and complete re-reads the remote (control_landing.py, steps 4 and 5).
- control_landing_station builds GitLandOps with push=True always (line 310). lander.GitLandOps already has
  push=False, which builds, gates and accepts but publishes and completes nothing; land locally is a real
  publication and a real completion, local instead of remote.
- Project records are written only by control_project's signed commands (OPERATIONS, ACTIVATION_FIELDS).

## Out of scope

Pushing a locally landed commit later, other remotes or hosts than VELDO-0153 allows, and per-unit choice.

## What the reviewer judges

- Normal use: the owner sets one project to land locally and approves its landings as today.
- Threat model: as VELDO-0057; an agent run cannot set the destination, only the owner's signed command.

## History

- 2026-11-04: drafted from the owner's decision (Telegram 39047) on the factory cutover research, gap 5.
  Not implemented; the owner approves it before it is claimed.
