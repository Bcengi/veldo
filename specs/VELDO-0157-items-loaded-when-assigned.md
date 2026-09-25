---
schema: veldo.spec/v1
id: VELDO-0157
title: The capability items a staffing choice assigns load with that run, and no other when-assigned item does
status: draft
risk: high
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W117
plan_revision: 4
depends_on: [VELDO-0090, VELDO-0127]
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
  - "scripts/suites/*_veldo_0157_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0157-items-loaded-when-assigned.md"
  - "specs/index.md"
  - "proof/VELDO-0157/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch's configuration revision, the `when assigned` items its dispatch recorded, the
    launch set handed over and any named stop; exclude secrets.
  metrics: >
    Count launches with assigned items, assigned items by kind, and launches stopped for a difference.
  traces: >
    Join each launch to its dispatch, assignment, staffing choice and configuration revision.
  error_taxonomy: >
    Distinguish an assigned item missing at launch, an unassigned item present, and an assigned item
    the role does not list; none lets the run take a first turn.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The `when assigned` items a dispatch records load with that run, so the engine's launch set
      equals the role's `always` items plus the assigned ones. Set and completeness: For Claude Code and
      Codex on Linux, dispatch a role whose staffing choice assigns one `when assigned` MCP selection,
      one skill and one instruction file, recorded on the assignment and its dispatch as
      `optional_capabilities` (VELDO-0090 AC1). Compare the engine's reported tools, MCP servers, skills
      and plugins at launch (Claude Code's init event, Codex's own MCP listing and generated
      configuration) with the role's `always` items plus the recorded ones, in both directions, and stop
      the run by name on any difference before its first turn; prove the assigned instruction file by the
      marker qualification of VELDO-0127 AC4. Falsifier: Drop an assigned `when assigned` skill at
      handoff; the assigned-launch-set comparison must fail.
    falsified_by: >
      Drop an assigned `when assigned` skill at handoff; the assigned-launch-set comparison must fail.
  - id: AC2
    text: >
      Claim: A `when assigned` item loads only on a dispatch that records it, never because the role lists
      it or an earlier dispatch assigned it. Set and completeness: Dispatch the same role twice, the first
      assigning a `when assigned` MCP selection and the second assigning nothing, and a third time
      assigning a different item; each launch set equals the role's `always` items plus exactly that
      dispatch's recorded items, and nothing assigned to one dispatch reaches another. Falsifier: Load
      every `when assigned` item the role lists whether or not the dispatch assigned it; the
      unassigned-item row must fail.
    falsified_by: >
      Load every `when assigned` item the role lists whether or not the dispatch assigned it; the
      unassigned-item row must fail.
required_evidence: [unit, integration]
rollback: >
  Stop honoring assigned items and launch roles with their `always` items only, with a named stop for a
  dispatch that recorded any; accepted assignments and configuration revisions are kept. No automatic
  rollback is authorized.
---

## Intent

A role can list capabilities it needs only for some work, so a lean role stays lean: the project
manager's staffing choice names the `when assigned` items a piece of work needs, and exactly those load
with that run.

## Context

W117 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 6 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the load modes, and its section 12 builds them in its third stage with VELDO-0090 (item
16), after VELDO-0127 runs with every item `always` in the second (item 11). This is the `when
assigned` leg of the design's VELDO-0127 AC4, split out on the third review of revision 4 so VELDO-0127
ships in the second stage whole; VELDO-0127 AC4 keeps the `always` leg, and VELDO-0090 AC1 checks each
assigned item belongs to the role and records it. This new specification is draft; authoring it
supplies neither implementation proof nor operational activation.

## Out of scope

Choosing capabilities by token cost; loading a capability part way through a run; the Mac handoff
(VELDO-0147 covers VELDO-0127's); VELDO-0090's selection and its refusal of an item the role does not
list.

## What the reviewer judges

- Normal use: the project manager staffs a unit with a role and names the `when assigned` items it needs;
  the dispatch records them, and the worker starts with the role's `always` items plus exactly those, on
  Claude Code or Codex.
- Threat model: an assigned item dropped at handoff; a `when assigned` item loaded because the role
  lists it or an earlier dispatch assigned it; a run whose reported set differs from the recorded one
  allowed a first turn. The owner's account, the store and the installed engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); VELDO-0090's
  selection predicates; forged rows in our own store and files planted in the installed directory.

## Notes

The factory never adds an item beyond the configuration and never drops an `always` or assigned one,
so C15 holds. The launch set is computed from the dispatch record alone, never from the role's list or
from memory of an earlier dispatch.

Use canonical engine assets and synchronize installed copies. Inventory every asset the selected
journey installs. Compare executable registrations to each criterion's declared universe, observe the
real named interfaces, and retain the driven negative-control diff and named failed row. Fixtures
cannot certify real engine or host behavior. Required evidence labels describe future implementation
proof, not tests run by this writing revision.

## History

2026-09-25: split from VELDO-0127 AC4 on the third review of PLAN-0019 revision 4, because the design's
section 12 puts VELDO-0127 in its second stage with every item `always` and the load modes in its third
with VELDO-0090 ("VELDO-0090 with load modes and VELDO-0127 AC4"), and a specification ships whole. AC1
carries the design's "`always` items plus the assigned ones" with a run that assigns an item; AC2 checks
that the assignment comes from the dispatch alone. A draft: only the owner marks a specification ready.
