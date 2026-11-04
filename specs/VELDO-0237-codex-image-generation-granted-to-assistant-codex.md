---
schema: veldo.spec/v1
id: VELDO-0237
title: A capability decision grants Codex image generation to the assistant_codex role only, and a live capture proves the generated image lands in the turn's workspace
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0062, VELDO-0127, VELDO-0163, VELDO-0177, VELDO-0189, VELDO-0230]
placement: [engine, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_agent_config*.py"
  - ".veldo/control_agent_config*.py"
  - "engine/.veldo/control_engine_codex.py"
  - ".veldo/control_engine_codex.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/runtime/capability-decisions.json"
  - ".veldo/runtime/capability-decisions.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0237_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0237-codex-image-generation-granted-to-assistant-codex.md"
  - "specs/index.md"
  - "proof/VELDO-0237/*"
behavior_bearing: true
observability:
  logs: >
    Record, for each Codex launch, whether image_generation was on and the role revision that granted it;
    for each image a turn produced, its path relative to the workspace, size and digest. Never the prompt
    text or the image bytes.
  metrics: >
    Count Codex launches with image_generation on by role, and images produced per turn.
  traces: >
    Join each produced image to its turn, its launch and the role revision that granted the feature.
  error_taxonomy: >
    Keep VELDO-0127's and VELDO-0230's names. A launch whose image_generation state differs from its role
    revision is a capability mismatch as VELDO-0127 AC4 names it; an image the turn produced outside its
    workspace is binding_mismatch:conversation_workspace (VELDO-0177).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: image_generation is a granted Codex capability that a launch turns on only for a role revision
      listing it. Set: runtime/capability-decisions.json records codex.features.image_generation as granted
      with its one-line reason and the owner decision; control_agent_config_handoff moves image_generation
      from the features no role is granted to the features that deliver a grant (native tool
      image_generation); a Codex launch turns the feature on exactly when the bound revision lists that native
      tool and off otherwise, compared on the wire as VELDO-0127 AC4 compares tools. Rows: grant/on launches
      a revision with the grant and requires the image tool in the request; grant/off launches the
      implementation role and requires it absent.
    falsified_by: >
      Turn image_generation on for every Codex launch, and the grant/off row must fail on the image tool in
      the implementation role's request.
  - id: AC2
    text: >
      Claim: setup grants it to assistant_codex and to no other role of the default team. Set: setup saves one
      new assistant_codex capability configuration revision adding the native tool image_generation, signed
      as VELDO-0203 signs, and an upgraded host gets it through VELDO-0189's re-run; a second run saves
      nothing; every other role in the default team is unchanged; the owner removes or adds the grant in the
      role form (VELDO-0163). Rows: setup/assistant requires the new revision and exactly one; census/roles
      requires image_generation in no other default role.
    falsified_by: >
      Add image_generation to the implementation role as well, and the census/roles row must fail.
  - id: AC3
    text: >
      Claim: a live capture shows an image generated in a conversation turn on assistant_codex landing in that
      turn's workspace, on the account's subscription login. Set: proof/VELDO-0237/ holds a capture made with
      the proof/VELDO-0127/live.py pattern on the qualified Codex binary: the init tool list with the image
      tool, a turn asked for one small image, the image file's path inside the workspace with its size, digest
      and dimensions, the account's login method (ChatGPT, no API key in the environment), and a listing of the
      account's profile directory and the host's temporary directory showing no copy of the image there. If
      the binary writes images elsewhere by default, the launch directs the output into the workspace, and the
      capture says how. A row replays the capture's checks against a fake engine.
    falsified_by: >
      Have the fake engine write the image under the account's profile directory instead of the workspace, and
      the replayed capture row must fail on the file outside the workspace.
required_evidence: [unit, integration, operational]
rollback: >
  Save an assistant_codex revision without image_generation by the owner's command, then revert the
  classification and the decision record. Images already in workspaces stay as ordinary files.
---

## Intent

The owner's image work needs a model that makes images. Codex 0.154 and 0.166 list image_generation as a
stable feature, and it runs on the Codex subscription login the factory already uses, with no paid API key.
Today Veldo's classification puts it among the features no role is granted, so no conversation can make an
image. This grants it to the conversation role on Codex only, by the capability decision VELDO-0230 records,
and proves where the image goes.

## Context

- control_agent_config_handoff.CODEX_FEATURES_UNGRANTED lists image_generation; CODEX_FEATURE_GRANTS maps
  features to the native tools a role can grant (VELDO-0127).
- runtime/capability-decisions.json is the record of each Codex feature's decision (VELDO-0230 AC3).
- assistant_codex is saved by setup with the workspace-write sandbox, network and web search (VELDO-0177
  AC2); each turn runs in its conversation's own workspace (VELDO-0177 AC1).
- Parity report research/veldo-parity-2026-11-04.md (myday), kind 19 gap 1, ticket T3.

## Out of scope

Sending the image to the owner (VELDO-0238); paid image or video APIs and catalog servers that carry their
keys, which the owner allowed only as spend-gated exceptions approved per use (VELDO-0243, a separate
draft); granting the feature to any project role.

## What the reviewer judges

- Normal use: the owner asks a conversation on assistant_codex for a slide illustration and the PNG is in
  the turn's workspace.
- Threat model: the feature reaching a project run that was not granted it; an image left in a shared
  account profile where another conversation could read it.

## History

- 2026-11-04: drafted from the Veldo parity report, ticket T3, under the owner's decisions to move the
  factory work to Veldo (Telegram 39047, 39049) and that text and code work stays on the subscriptions
  while paid image and video APIs are separate spend-gated exceptions (Telegram 39067). Not implemented;
  the owner approves it before it is claimed.

2026-11-04: approved by the owner, Telegram 39096 ("Yes covers both", to 39089-39092 asking approval of VELDO-0236 to VELDO-0249, the PLAN-0019 amendment and the connectors plan). Status ready.
