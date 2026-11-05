---
schema: veldo.spec/v1
id: VELDO-0243
title: A generate-media step makes an image or video through a catalog server, and because it is paid each use is the owner's approval with the cost shown and the spend checklist recorded, plus a default media definition
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0068, VELDO-0127, VELDO-0132, VELDO-0144, VELDO-0177, VELDO-0241]
placement: [contracts, engine, loop]
protected_paths: []
footprint:
  - "engine/.veldo/control_workflow*.py"
  - ".veldo/control_workflow*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_step_media*.py"
  - ".veldo/control_step_media*.py"
  - "engine/.veldo/workflows/media.json"
  - ".veldo/workflows/media.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0243_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0243-a-paid-media-generation-step-approved-per-use.md"
  - "specs/index.md"
  - "proof/VELDO-0243/*"
behavior_bearing: true
observability:
  logs: >
    Each use records the unit, the node, the catalog server and tool and their versions, the medium (image
    or video), the prompt's digest, the quoted cost and its source, the spend checklist answers, the
    approval id, the cost the server reported after the call and the output digests. Credentials and
    provider keys are never logged.
  metrics: >
    Count uses requested, approved, declined and run, by medium and server; sum quoted and reported cost per
    project and per day.
  traces: >
    Join each output file to the one approval it ran under, its spend checklist record and its server call.
  error_taxonomy: >
    Keep VELDO-0132's names. A use with no approval of its own is missing_authority:spend_approval; an
    approval already consumed is stale_version:spend_approval; a call whose quote exceeds the approved
    ceiling is budget_exceeded:media_cost; a server with no price for the request is
    missing_evidence:media_quote; a server outside the role's capability configuration is
    unsupported_configuration; an unknown call outcome is unknown, never retried by itself.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: every generate-media call is preceded by its own owner approval that shows the cost and records
      the spend checklist. Set: before the call the step asks the owner one decision (VELDO-0068) showing
      the medium, the prompt, the server and the quoted cost with its source, and carrying the spend
      checklist (the owner's configured spend decision items, each answered); his admit records the
      answers and a cost ceiling and is consumed by exactly one call; a retry, a second image, a re-run on
      another account or a loop back to the node asks again. A decline ends the node on its decline port
      with no call.
    falsified_by: >
      Let a second call reuse the approval consumed by the first; the one-approval-one-call row must fail.
  - id: AC2
    text: >
      Claim: the call stays within what was approved and its cost is recorded. Set: the call goes only to
      the catalog server and tool the role's capability configuration names (VELDO-0127, VELDO-0144), with
      credentials from the OS keystore; a quote above the approved ceiling is refused before any call; the
      cost the server reports afterwards is recorded beside the quote, and a reported cost above the ceiling
      is flagged to the owner. Text and code steps never reach a paid server.
    falsified_by: >
      Call the server when the fresh quote is above the approved ceiling; the ceiling row must fail.
  - id: AC3
    text: >
      Claim: the default `media` definition (draft the brief, owner spend approval, generate media, review,
      owner approval naming deliver, deliver) saves and runs end to end against a fixture catalog server,
      and a definition with a generate-media node that is not directly preceded by a spend approval naming
      it is refused at save with invalid_input:missing_spend_approval:<node>.
    falsified_by: >
      Save a definition whose generate-media node is reached straight from the brief; the save-refusal row
      must fail.
required_evidence: [unit, integration]
rollback: >
  Revert the change; the generate-media kind is unregistered and no paid call can be made. Recorded uses,
  approvals and costs stay in the store. No automatic rollback, retry or recovery is authorized.
---

## Intent

Images and video become one step in a workflow, and because they cost money the owner sees the price and
approves each use, every time, with the reasoning recorded.

## Context

Owner, Telegram 39067: paid image and video generation are spend-gated exceptions, each use approved;
text and code stay on the subscriptions (PLAN-0019 NG3 amended 2026-11-04). 39069 to 39071: a unit's
process is a workflow per kind of work (VELDO-0241). The server is an ordinary catalog record with its
credentials in the keystore. The spend checklist is the owner's standing spend decision review (his
ten-item gate), held as configuration so its items can change without code. Codex's own image tool on a
subscription (writer A's ticket T3) is not paid and is not this step.

## Out of scope

Choosing a media provider. Monthly spend budgets and their pacing. Free image generation inside a
subscription engine.

## What the reviewer judges

- Normal use: a brief is drafted, the owner sees "image, this prompt, this server, quoted cost X" with the
  checklist and approves, one call runs, the output is reviewed, approved for delivery and delivered.
- Threat model: a call with no approval, an approval used twice, a loop that regenerates on one approval,
  a quote raised after approval, a server the role was not granted, a key that reaches a log.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); provider price
  accuracy beyond recording quote and reported cost.

## Notes

The spend approval is an owner_approval node with a spend form, so VELDO-0241's save check and VELDO-0068's
settlement apply unchanged; the media step only adds the rule that it must sit directly before the call.

## History

2026-11-04: new draft under owner Telegram 39067 (paid image and video, each use approved) and 39069 to
39071 (process as workflow). Standalone.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.
