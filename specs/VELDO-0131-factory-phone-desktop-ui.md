---
schema: veldo.spec/v1
id: VELDO-0131
title: Veldo factory UI on phone and desktop
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W94
plan_revision: 4
depends_on: [VELDO-0051, VELDO-0076, VELDO-0077, VELDO-0078, VELDO-0089, VELDO-0127, VELDO-0128, VELDO-0130, VELDO-0132, VELDO-0141, VELDO-0142, VELDO-0143, VELDO-0144, VELDO-0145, VELDO-0159, VELDO-0160, VELDO-0162, VELDO-0163]
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
      React/TypeScript/Vite, shadcn/ui AI chat, TanStack Table, React Flow, Monaco and
      Chart.js with react-chartjs-2 requirements; explicitly reject shadcn charts and Recharts;
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

W94 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5.
Sections 3, 5, 7 and 8 of the approved
[operating-model design](../docs/design/PLAN-0019-operating-model-design.md) add screen rows; its first slice is VELDO-0145.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: the owner opens the UI on his phone or desktop over his tailnet, in a passkey session, and uses
  every screen row: objectives and projects, backlog, workers, the live run terminal, decisions,
  gate and review, usage per account, team and capability configuration, MCP servers and
  credentials, repositories and identities, and the workflow editor; every read and action goes
  through the authenticated API.
- Threat model: a screen that is clipped, overlapping or reduced to read-only on a phone; completion or any state
  shown from local optimistic state before its authoritative record; an action that bypasses the
  API, intake or settlement; a credential value shown or read back; a run shown as a summary instead
  of its record; a workflow edit that executes work; a dependency outside the owner's stack or
  provenance rules. The owner's account, the store and the API are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); recovery and offline behavior (Release 2); an optional form for creating repositories; a
  connection test button for MCP servers; forged rows in our own store and files planted in the
  installed directory.

## Notes

The owner requires this UI in Telegram 28857: "otherwise we'll be flying blind". The selected
stack is React + TypeScript + Vite, shadcn/ui including its AI chat parts, TanStack Table,
React Flow for the editor, Monaco for code/diffs and Chart.js with react-chartjs-2 for charts. No Chinese-origin dependency anywhere and
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

### Allowed dependencies

The allowed direct UI dependency list is React, TypeScript, Vite, shadcn/ui AI chat and UI
components (excluding shadcn charts), TanStack Table, React Flow, Monaco, Chart.js and
react-chartjs-2. Chart.js and react-chartjs-2 are both MIT licensed. Chart.js is the charting
library Bcengi's Vue apps already use. Use Chart.js through react-chartjs-2 for the
spend-over-time screen; shadcn charts and Recharts are prohibited under the owner's
no-Chinese-origin rule. Exact versions and transitive dependencies still require the
provenance/license checks in AC4.

## Screen contract

Every row is part of AC1/AC3, including its stated phone layout. The authenticated API is the only
source of state and mutations. A phone is not a reduced read-only mode.

| Screen | Desktop | Phone |
|---|---|---|
| Objectives and projects | Searchable list, objective evidence/status and project detail; AI chat message box alongside | Stacked project cards and full-width objective detail; persistent accessible message action and chat sheet |
| Backlog and nested units | TanStack Table with expandable specification/unit hierarchy, priority and blockers | Compact cards/rows with expand controls and a detail sheet; reorder/priority actions usable by touch without drag-only requirements |
| Workers per machine | Linux/Mac groups with capability, activity, cap and stop controls | Machine sections with worker cards and visible host labels; inline stop confirmation/result |
| Live agent run | The run's live terminal, built first by VELDO-0145 AC2 over the record route of VELDO-0141: every event of the execution record in order, tool calls with inputs and results, command output in monospace, edits as Monaco diffs, errors marked, follow mode and search, beside a pipeline strip showing the unit's station | The same terminal full width, with follow mode, search and tap-open tool calls; the pipeline strip stays visible while reading; never a summary in place of the record |
| Pending decisions | Inbox plus exact shown question, choices, rationale and inline answer | Full-width decision cards, readable presentation and inline choices/rationale; stale-answer feedback stays beside the action |
| Gate and review results | Check table, findings, proof links and Monaco source/diff panes | Check/finding cards with navigable proof; Monaco code/diff view supports wrapping and single-pane old/new selection |
| Subscription usage over time (spend view) | Chart.js via react-chartjs-2 time series in invocation/time/CLI-reported token or message units, with provider/account/project/run breakdown, each account's rate-limit windows, reset times and active runs, "no account until" the earliest reset, and unknown usage; no invented per-call price | Readable time range and summary, touch-selectable points and a compact per-account breakdown with reset times; unknown exposure never shown as zero |
| Team and agent/tool/MCP configuration | Role table with each team and configuration revision's history and versioned detail listing exact effective tools/servers, opening the role and team form, which VELDO-0163 builds earlier over VELDO-0162's routes | Role cards and full-width detail opening the same form; all tools/servers and protected credential references remain inspectable, and editable through that form |
| MCP servers and credentials | Catalog table of servers (VELDO-0144) with revision history, transport, hosts and read-only tools, and each credential's label, set at and set by, opening the server form with its write-only credential fields, which VELDO-0159 builds earlier | Server cards opening the same form; no value is ever shown or read back |
| Repositories and identities | Read-only table of Git identities (label, author, remote owner, projects root, default visibility) and repositories (identity, path, remote, origin created or adopted, state with its named reason) | Identity and repository cards with the same fields; read-only |
| Workflow/pipeline editor | React Flow canvas, palette and node/edge properties with version/save state | Pan/zoom canvas plus an accessible ordered node/edge list and property sheet; add/connect/reorder via touch controls, with visible version/save state |

The workflow canvas edits VELDO-0132 data. It has no engine, shell executor, direct provider call or
local run button that bypasses admission. Any ordinary execution action is an authenticated API
request applying current Veldo authority. Monaco never executes inspected source.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 5, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), sections 3(e), 5(e), 7(e)
and 8(e). The screen contract's "Live agent run" row is replaced by the live terminal that VELDO-0145
AC2 builds first over VELDO-0141's record route; it gains an "MCP servers and credentials" row and a read-only
"Repositories and identities" row; and the usage row adds the per-account breakdown. depends_on adds
VELDO-0141 to VELDO-0145, which own those rows. A What the reviewer judges section is added. Status
unchanged.

2026-09-25, PLAN-0019 revision 4, third review: the server form with its write-only credential fields
moves earlier, to the new stage 2 draft VELDO-0159, so the owner can enter the Atlassian credential
before this specification is built; the "MCP servers and credentials" row keeps the catalog table, the
revision history and the credential list and opens that form, so it is not built twice, and depends_on
adds VELDO-0159. Status unchanged.

2026-09-25, PLAN-0019 revision 4, third review: depends_on adds VELDO-0160, which now owns the
per-account rate-limit windows, reset times and "no account until" the usage row shows (split out of
VELDO-0062). Status unchanged.

2026-09-25, PLAN-0019 revision 4, fourth review: the role and team form moves earlier, to the new stage 2
draft VELDO-0163 over the configuration and team routes of the new draft VELDO-0162, so the owner can
give a role the Atlassian server and put it in a team before this specification is built; the "Team and
agent/tool/MCP configuration" row keeps the role table, the revision history and the effective
tools/servers detail and opens that form, so it is not built twice, and depends_on adds VELDO-0162 and
VELDO-0163. Status unchanged.
