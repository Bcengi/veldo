---
schema: veldo.spec/v1
id: VELDO-0131
title: Veldo factory UI on phone and desktop
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W94
plan_revision: 3
depends_on: [VELDO-0051, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0089, VELDO-0127, VELDO-0128, VELDO-0130, VELDO-0132]
placement: [loop, distribution]
protected_paths: []
footprint:
  - "engine/ui/**"
  - "packs/*/ui/**"
  - "scripts/suites/*_veldo_0131_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0131-factory-phone-desktop-ui.md"
  - "specs/index.md"
  - "proof/VELDO-0131/*"
behavior_bearing: true
observability:
  logs: >
    Record operation, domain/repository, actor or role, input/configuration versions,
    resulting record identity and named refusal; exclude secrets.
  metrics: >
    Count accepted/refused operations and pending work, with bounded run duration and
    charge attribution where this concern uses a worker.
  traces: >
    Correlate input request, configuration/host, dispatched work and resulting authority evidence.
  error_taxonomy: >
    Distinguish unauthenticated, unauthorized, stale version, unsupported configuration,
    unavailable service, missing evidence and unknown outcome; none is successful completion.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every screen in the screen contract is usable with the selected stack on phone and
      desktop. Set and completeness: Treat every row below as required at 360px and 390px phone
      widths and 1280px and 1440px desktop widths, including loading, empty, live, stopped/error and
      populated states where applicable. Inspect actual rendered screens and keyboard/touch flows;
      no clipped primary action, overlapping controls or page-wide horizontal overflow.
      Tables/canvas/diffs may have clearly bounded internal navigation. Falsifier: Hide an inline
      decision action at 360px width; the phone screen-contract check must fail.
    falsified_by: >
      Hide an inline decision action at 360px width; the phone screen-contract check must fail.
  - id: AC2
    text: >
      Claim: Live views show authoritative state and owner actions use only the authenticated API.
      Set and completeness: Drive real journal updates for assignment, step/tool call, stop,
      gate/review and completion into the UI. Trace message submission to common intake and an
      inline decision answer to exact settlement, including stale/unauthorized errors; verify
      current versions/freshness and absent secrets. Falsifier: Show completion from local
      optimistic build state before its landing receipt; the authoritative-state check must fail.
    falsified_by: >
      Show completion from local optimistic build state before its landing receipt; the
      authoritative-state check must fail.
  - id: AC3
    text: >
      Claim: Phone and desktop interactions support the full owner task path accessibly. Set and
      completeness: For each screen row run keyboard-only desktop and touch phone tasks, including
      focus restoration, labeled controls, visible pending decisions, readable code/diffs, nested-
      unit navigation and workflow node/edge editing. Verify 44px primary touch targets, sufficient
      contrast, screen-reader names and announced result/error states with the actual accessibility
      tree. Falsifier: Make a workflow node setting accessible only by hover; the phone/keyboard
      editing task must fail.
    falsified_by: >
      Make a workflow node setting accessible only by hover; the phone/keyboard editing task must
      fail.
  - id: AC4
    text: >
      Claim: The built UI and its dependency set satisfy the owner stack and provenance rules. Set
      and completeness: Compare the real build manifest, lockfile and imported/served assets to
      React/TypeScript/Vite, shadcn/ui AI chat, TanStack Table, React Flow and Monaco requirements;
      record origin/license/tier evidence for each direct/transitive dependency and bundled asset.
      Reject unresolved origin, Chinese-origin dependencies or any library with free/paid tiers
      before qualification. Falsifier: Allow a dependency flagged with free and paid library tiers
      into the accepted lockfile; the dependency-policy check must fail.
    falsified_by: >
      Allow a dependency flagged with free and paid library tiers into the accepted lockfile; the
      dependency-policy check must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Let the owner see the running factory, answer decisions and edit its configuration/workflows
from a phone as effectively as from a desktop.

## Context

W94 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

The owner requires this UI in Telegram 28857: "otherwise we'll be flying blind". The selected
stack is React + TypeScript + Vite, shadcn/ui including its AI chat parts, TanStack Table,
React Flow for the editor and Monaco for code/diffs. No Chinese-origin dependency anywhere and
no library with free and paid tiers; verify direct and transitive provenance and licenses
before choosing versions. If a selected component conflicts, record an owner decision instead
of silently substituting or exempting it. Bcengi products remain on Vue.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## Screen contract

Every row is part of AC1/AC3, including its stated phone layout. The authenticated API is the only
source of state and mutations. A phone is not a reduced read-only mode.

| Screen | Desktop | Phone |
|---|---|---|
| Objectives and projects | Searchable list, objective evidence/status and project detail; AI chat message box alongside | Stacked project cards and full-width objective detail; persistent accessible message action and chat sheet |
| Backlog and nested units | TanStack Table with expandable specification/unit hierarchy, priority and blockers | Compact cards/rows with expand controls and a detail sheet; reorder/priority actions usable by touch without drag-only requirements |
| Workers per machine | Linux/Mac groups with capability, activity, cap and stop controls | Machine sections with worker cards and visible host labels; inline stop confirmation/result |
| Live agent run | Timeline of LangGraph steps and expandable tool calls beside artifacts/code | Vertical step timeline, tap-open tool arguments/results and artifact view; progress remains visible while reading |
| Pending decisions | Inbox plus exact shown question, choices, rationale and inline answer | Full-width decision cards, readable presentation and inline choices/rationale; stale-answer feedback stays beside the action |
| Gate and review results | Check table, findings, proof links and Monaco source/diff panes | Check/finding cards with navigable proof; Monaco code/diff view supports wrapping and single-pane old/new selection |
| Spend over time | Time-series totals with provider/project/run breakdown and unknown exposure | Readable time range and summary, touch-selectable points and compact breakdown; unknown exposure never shown as zero |
| Team and agent/tool/MCP configuration | Role table and versioned detail forms listing exact effective tools/servers | Role cards and full-width forms; all tools/servers and protected credential references remain inspectable/editable |
| Workflow/pipeline editor | React Flow canvas, palette and node/edge properties with version/save state | Pan/zoom canvas plus an accessible ordered node/edge list and property sheet; add/connect/reorder via touch controls, with visible version/save state |

The workflow canvas edits VELDO-0132 data. It has no engine, shell executor, direct provider call or
local run button that bypasses admission. Any ordinary execution action is an authenticated API
request applying current Veldo authority. Monaco never executes inspected source.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 5, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.
