---
schema: veldo.spec/v1
id: VELDO-0127
title: Versioned per-role MCP server and tool configuration
status: ready
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W90
plan_revision: 4
depends_on: [VELDO-0025, VELDO-0035, VELDO-0089, VELDO-0141, VELDO-0144, VELDO-0155, VELDO-0156, VELDO-0158]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_agent_config*.py"
  - ".veldo/control_agent_config*.py"
  - "packs/*/.veldo/control_agent_config*.py"
  - "engine/.veldo/control_engine*.py"
  - ".veldo/control_engine*.py"
  - "packs/*/.veldo/control_engine*.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "scripts/suites/*_veldo_0127_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "specs/VELDO-0127-agent-capability-configuration.md"
  - "specs/index.md"
  - "proof/VELDO-0127/*"
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
      Claim: Each role has an accepted immutable version of its capability configuration, whose MCP
      servers are references to catalog revisions, with skills, instruction files and load modes.
      Set and completeness: Compare the schema against role, revision, engine, native tools, MCP
      selections (catalog server id and revision, all tools or a list, load mode), skills (skill
      catalog id and revision, load mode), instruction files (source, the project repository or the
      factory, path, load mode), and engine settings such as the model; a server's definition and
      credentials live only in the VELDO-0144 catalog and are never embedded in a role. Every item's
      load mode is `always` or `when assigned`. Create an authorized revision and reject stale or
      unauthorized edits. No secret value is copied into ordinary views or proof. Falsifier:
      Overwrite an accepted configuration in place; the version/digest history check must fail.
    falsified_by: >
      Overwrite an accepted configuration in place; the version/digest history check must fail.
  - id: AC2
    text: >
      Claim: Worker handoff preserves exactly the configured servers and tools for each engine. Set
      and completeness: For actual Claude Code and Codex workers on Linux (the Mac handoff is
      VELDO-0147), enumerate
      effective engine-native and MCP capabilities at launch and compare set equality and settings
      with the accepted role revision in both directions. Include a configured Jira-capable MCP tool
      as an ordinary tool, with no special factory channel. Verify each server authenticates
      using exactly its configured credential delivery, including the Atlassian catalog server's
      keystore credential, without gaining another server's credentials.
      Compare redacted credential-source identities, never secret values. Falsifier: Remove one configured MCP
      tool while allowing launch; the exact-handoff comparison must fail.
    falsified_by: >
      Remove one configured MCP tool while allowing launch; the exact-handoff comparison must fail.
  - id: AC3
    text: >
      Claim: The dispatch records the configuration revision actually used and refuses an
      unsupported handoff. Set and completeness: Launch under revision A, author revision B and
      inspect the running worker remaining bound to A and later dispatch binding B. Try an
      unsupported setting or unavailable required server/tool; expose a named configuration stop
      without dropping it or adding fallback capabilities. Falsifier: Add a default tool absent from
      the configured set; the unexpected-capability check must fail.
    falsified_by: >
      Add a default tool absent from the configured set; the unexpected-capability check must fail.
  - id: AC4
    text: >
      Claim: Nothing loads unless the role lists it; the engine's reported tools, MCP servers,
      skills and plugins at launch equal the role's `always` items; instruction files are proved by
      the marker qualification. A `when assigned` item loads only when its dispatch assigns it, which
      is VELDO-0157. Set and completeness: For Claude
      Code, compare the init event's `tools`, `mcp_servers`, `slash_commands`, `skills` and
      `plugins` with the set the dispatch recorded, in both directions, and stop the run by name on
      any difference before its first turn; for Codex, compare its own MCP listing and the generated
      configuration where its stream reports less. Listed instruction files reach Claude Code joined
      into one generated file for the `append-system-prompt-file` option and Codex through developer
      instructions. Because the init event names no loaded instruction files, plant a marker
      CLAUDE.md in the clone and in the account profile with discovery turned off, and compare the
      debug log and the first turn's context size with and without it; the first turn's context size
      is kept in the execution record. Run one role with only `always` items and one that also lists
      a `when assigned` item, dispatched with nothing assigned. Falsifier: Let the engine load a skill
      the role does not list; the launch-set comparison must fail.
    falsified_by: >
      Let the engine load a skill the role does not list; the launch-set comparison must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Workers receive exactly the MCP servers and tools their versioned role configuration gives
them, preserving the configured capability surface available today.

## Context

W90 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5 (moved from stage 4 by revision 4, because it depends on
the stage 5 catalog VELDO-0144). Section 6 of the approved
[operating-model design](../docs/design/PLAN-0019-operating-model-design.md) designs the per-work handoff.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## What the reviewer judges

- Normal use: the owner saves a role's capability configuration as a new revision, choosing catalog servers,
  native tools, skills and instruction files, each `always` or `when assigned`; a dispatch records
  the revision, and the worker starts with exactly its `always` items, on Claude Code or Codex, on
  Linux (on the Mac through VELDO-0147); the items a staffing choice assigns load through VELDO-0157.
- Threat model: an accepted configuration overwritten in place; a server definition or credential embedded in a
  role; a capability dropped, added or defaulted at handoff, including an instruction file, skill,
  memory or hook the account profile would have added; a run whose reported tools, servers, skills
  or plugins differ from the recorded set allowed a first turn; a running worker rebound to a newer
  revision; a secret value in a view, journal payload or proof. The owner's account, the store and
  the installed engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); choosing capabilities by token cost, per-tool usage analytics and managing instruction file
  content; loading a capability part way through a run; forged rows in our own store and files
  planted in the installed directory.

## Notes

Owner Telegram 28859 forbids the factory silently reducing agent capability. Configuration
describes engine-native tools and MCP server/tool selections, launch arguments, enabled
settings and protected credential references. The handoff must preserve them for Claude Code
and Codex; an unsupported configuration produces a visible refusal, not a reduced run.
Each MCP server receives exactly the credentials its accepted configuration gives it today:
configured environment values or protected references are resolved into that server's launch;
configured profile files, paths or mounts remain available to that server; remote transport
authentication uses that server's configured headers or credential mechanism. Inherited values
are passed only when that server's configuration includes them. Atlassian is an ordinary catalog
server with its credential in the keystore; the claude.ai connectors are not used, because Claude
Code turns them off under the strict MCP mode this handoff needs. Do not replace, strip or broaden
these mechanisms.
A missing or unsupported credential source causes a named configuration stop, not a reduced
capability run. Secret values never enter ordinary views, journal payloads or proof.

The adapter turns off the engine's own discovery and every profile source (VELDO-0155, VELDO-0156)
and then hands in exactly the role's items, so each account profile supplies only the login and a
role behaves the same on every account. Separating the provider login from tool and build children is
Release 2 hardening (owner, Telegram 29163); nothing here prohibits an MCP server from using its own
configured credentials.
Tool use still obeys the execution contract and C13 attachments.

Use canonical engine assets and synchronize installed copies. Resolve the proposed footprint's
architecture mapping before ready, including the new UI assets where applicable; this draft does
not amend the architecture contract. Inventory every asset the selected journey installs. Compare
executable registrations to each criterion's declared universe, observe the real named interfaces,
and retain the driven negative-control diff and named failed row. Fixtures cannot certify real
platform, engine or host behavior. Required evidence labels describe future implementation proof,
not tests run by this writing revision.

## History

2026-09-22: new draft for PLAN-0019 revision 3, Release 1 stage 4, under the owner's
complete-factory MVP decisions. Simple function and its meaningful refusal checks are in this
release; recovery and robustness are Release 2, governance depth Release 3, broader hosts/channels,
installation, adoption, migration and rollback Release 4.

2026-09-25, PLAN-0019 revision 4: amended on the approved operating-model design
(docs/design/PLAN-0019-operating-model-design.md, owner Telegram 29162), sections 3(e) and 6(e).
AC1: the schema gains skills, instruction files and load modes, and MCP servers are catalog
references (VELDO-0144), which depends_on now names. AC2 names the Atlassian catalog server's
keystore credential and drops the provider-login clause, which is Release 2 hardening (Telegram
29163). New AC4: nothing loads unless the role lists it, proved against the engine's launch report
and, for instruction files, by the marker qualification. The work item moves from stage 4 to stage 5
because the catalog is stage 5. A What the reviewer judges section is added. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: a specification ships whole and the run-check refuses one whose
dependencies are not shipped, so the Mac leg of this Linux-first qualification moves to VELDO-0147,
which is built after VELDO-0124 and VELDO-0125. Status unchanged.

2026-09-25, PLAN-0019 revision 4 review: depends_on adds VELDO-0141, because AC4 keeps the first turn's
context size in the execution record, and the footprint adds `control_launch`, where the Runner (class
`Runner`) and the launch receiver that hands the configuration over live. Status unchanged.

2026-09-25, PLAN-0019 revision 4, third review: depends_on adds VELDO-0155 and VELDO-0156, where the
everything-off baseline this handoff builds on now lives (it was VELDO-0060 AC5 and VELDO-0061 AC5), and
the Notes name them. Status unchanged.

2026-09-25, PLAN-0019 revision 4, third review: the design's section 12 builds this specification in
its stage 2 with every item `always` (item 11) and the load modes with VELDO-0090 in its stage 3 (item
16), so AC4 keeps the `always` leg (the launch set equals the role's `always` items, and a `when
assigned` item with nothing assigned does not load) and the `when assigned` leg, where the items a
staffing choice assigns load with the run, is the new draft VELDO-0157, built with VELDO-0090. AC4's
falsifier is unchanged. Status unchanged.

2026-09-25, PLAN-0019 revision 4, third review: depends_on adds VELDO-0158, because AC2 verifies each
server authenticates with exactly its configured credential delivery, which VELDO-0158 now owns after
its split from VELDO-0144. Criteria and status unchanged.
