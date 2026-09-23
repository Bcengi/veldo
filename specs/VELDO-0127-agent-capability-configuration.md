---
schema: veldo.spec/v1
id: VELDO-0127
title: Versioned per-role MCP server and tool configuration
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W90
plan_revision: 3
depends_on: [VELDO-0025, VELDO-0035, VELDO-0089]
placement: [contracts, fleet]
protected_paths: []
footprint:
  - "engine/.veldo/control_agent_config*.py"
  - ".veldo/control_agent_config*.py"
  - "packs/*/.veldo/control_agent_config*.py"
  - "engine/.veldo/control_engine*.py"
  - ".veldo/control_engine*.py"
  - "packs/*/.veldo/control_engine*.py"
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
      Claim: Each role has an accepted immutable version of its MCP/tool configuration. Set and
      completeness: Compare the schema against role, engine, native tools, MCP server
      identities/endpoints or commands, arguments/settings, tool selections and credential
      references; create an authorized revision and reject stale or unauthorized edits. No secret
      value is copied into ordinary views or proof. Falsifier: Overwrite an accepted configuration
      in place; the version/digest history check must fail.
    falsified_by: >
      Overwrite an accepted configuration in place; the version/digest history check must fail.
  - id: AC2
    text: >
      Claim: Worker handoff preserves exactly the configured servers and tools for each engine. Set
      and completeness: For actual Claude Code and Codex workers on Linux and Mac, enumerate
      effective engine-native and MCP capabilities at launch and compare set equality and settings
      with the accepted role revision in both directions. Include a configured Jira-capable MCP tool
      as an ordinary tool, with no special factory channel. Falsifier: Remove one configured MCP
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
required_evidence: [unit, integration]
rollback: >
  Disable new operations for this concern while preserving accepted records, configuration
  revisions and unresolved work. No automatic rollback, retry or recovery is authorized.
---

## Intent

Workers receive exactly the MCP servers and tools their versioned role configuration gives
them, preserving the configured capability surface available today.

## Context

W90 of [PLAN-0019 revision 3](../plans/PLAN-0019-dark-factory.md), Release 1 stage 4.
The [design](../docs/design/PLAN-0019-dark-factory-design.md) applies with its 2026-09-22
scope amendments. This new specification is draft; authoring it supplies neither implementation
proof nor operational activation. Implementation still requires readiness and applicable approval.

## Out of scope

Automatic recovery, durability/scale qualification and additional host/channel types beyond
this declared concern. These belong to later releases as assigned by the plan. No existing
specification status, implementation, test, runtime policy or deployed service changes in this draft.

## Notes

Owner Telegram 28859 forbids the factory silently reducing agent capability. Configuration
describes engine-native tools and MCP server/tool selections, launch arguments, enabled
settings and protected credential references. The handoff must preserve them for Claude Code
and Codex; an unsupported configuration produces a visible refusal, not a reduced run.
Credentials remain protected and tool use still obeys the execution contract and C13
attachments.

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
