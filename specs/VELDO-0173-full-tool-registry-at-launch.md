---
schema: veldo.spec/v1
id: VELDO-0173
title: A Claude Code run is offered its launch tool set with every other registered tool switched off
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W133
plan_revision: 4
depends_on: [VELDO-0165, VELDO-0160]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "scripts/suites/85_veldo_0158_credential_delivery.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0173_*.py"
  - "scripts/suites/78_veldo_0060_claude_adapter.py"
  - "scripts/suites/80_veldo_0155_claude_baseline.py"
  - "scripts/suites/75_veldo_0062_accounts.py"
  - "scripts/suites/78_veldo_0160_account_pool.py"
  - "scripts/suites/82_veldo_0129_worker_wiring.py"
  - "scripts/suites/82_veldo_0141_execution_record.py"
  - "scripts/suites/82_veldo_0165_launch_hygiene.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0173-full-tool-registry-at-launch.md"
  - "specs/index.md"
  - "proof/VELDO-0173/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch's tool options and registry classification, as names only, bound to the
    qualification record and role revision; never a credential.
  metrics: >
    Count launches and launches refused for a missing registry or classification.
  traces: >
    Join each launch to its dispatch, the pinned executable digest and the qualification record version
    whose tool list it applied.
  error_taxonomy: >
    Distinguish a version whose qualified baseline lacks the tool registry or its classification
    (missing_evidence:engine_baseline) from a tool outside the list found in the init event; neither
    lets the run take a first turn.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: A Claude Code run is offered exactly its launch tool set, and every other tool the binary
      registers is switched off at launch, not only caught. The launch tool set is a default, never a
      ceiling on the owner's grant. Set and completeness: When a role revision is bound, the launch tool
      set is that revision's native tools (VELDO-0127, the owner's grant, which may go beyond the in-run
      list); until then it is the in-run list of the pinned version. The launch passes the `tools` option
      naming exactly the launch tool set, and the `disallowedTools` option naming every tool in the
      binary's full tool registry that falls outside it; the registry is every tool the binary registers,
      read from its bytes by an extractor this specification commits in proof/VELDO-0173, not the
      22-name `claude_code.tool_forms.builtin_tools` table of proof/VELDO-0062/cli-formats.json.
      Before anything is switched off, a classification step records in proof/VELDO-0173 every tool of
      the pinned 2.1.281 registry as in-run or outward, each with the reason read from its definition.
      The in-run list is `claude_code.tool_forms.in_run.tools` in proof/VELDO-0062/cli-formats.json
      from the VELDO-0160 build at 14ce04f8, with 18 names; outward means a registry tool not on that
      list. The suite requires the classification's in-run tools to equal that list. The live init of
      2026-09-26 offered 25 tools, among them CronList, CronDelete, EnterWorktree, ExitWorktree,
      ListAgents, ScheduleWakeup and ReportFindings.
      Launch a run with no revision bound and read the init event's tool list: it equals the in-run list,
      and RemoteTrigger, SendMessage, PushNotification, the Artifact and other claude.ai-writing tools and
      self_hosted_runner are absent. The registry row compares the actual disallowedTools option with
      the binary's full registry minus the launch tool set, including ReportFindings in that comparison.
      Falsifiers: Launch with neither the
      `tools` nor the `disallowedTools` option, and the no-revision init-tools row must fail on
      RemoteTrigger. Build disallowedTools from the 22-name table instead of the binary's full registry;
      the registry row must fail on ReportFindings.
    falsified_by: >
      Launch with neither the `tools` nor the `disallowedTools` option, and the no-revision init-tools
      row must fail on RemoteTrigger. Build disallowedTools from the 22-name table instead of the binary's
      full registry; the registry row must fail on ReportFindings.
  - id: AC2
    text: >
      Claim: The tool registry and its classification are part of the qualified baseline, so a version
      without them launches nothing. Set and completeness: The Claude Code qualification record's
      baseline for a version carries the tool registry and the classification of every registry tool
      (AC1), all read from that version's bytes; the receiver derives the `tools` and `disallowedTools` options from the record
      and the bound revision, never from a list in the code. A record whose baseline lacks any of them, or
      whose classification leaves a registry tool unclassified, refuses every launch of that version by
      name before anything is spawned (missing_evidence:engine_baseline:<version>).
      Falsifier: Accept a record whose classification leaves one
      registry tool unclassified, and the baseline-required row must fail.
    falsified_by: >
      Accept a record whose classification leaves one registry tool unclassified, and the
      baseline-required row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new Claude Code launches while preserving accepted records and unresolved work; no run
  launches without these guards. No automatic rollback is authorized.
---

## Intent

A Claude Code worker is offered the tools its role was granted, or by default only the tools that act
inside its run, with every other tool the binary registers switched off at launch.

## Context

W133 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1, after VELDO-0165
and VELDO-0160. This concern is split from VELDO-0165's former AC3 and AC4; VELDO-0165 keeps the parent
session environment strip. The live init of 2026-09-26 offered 25 tools, more than the 22-name built-in
table names. The reviews of VELDO-0160 found outward tools one at a time, so the lead chose the binary's
full registry and a classification of every tool before switch-off. VELDO-0160 produces the tool_forms
table of proof/VELDO-0062/cli-formats.json that this classification reads. VELDO-0127 depends on this
specification and proves the bound role's grant, including PushNotification, in its AC4; this
specification does not wait on VELDO-0127. This is a draft, not implementation proof or activation.

## Out of scope

The environment strip (VELDO-0165); the role revision's capability handoff proof (VELDO-0127 AC4);
VELDO-0160's call decision, which stays as the second check, including input-dependent outward forms
of an in-run tool (remote Agent isolation, durable CronCreate); a Bash tool starting another CLI
(filed for VELDO-0127 and VELDO-0158); the Codex tool surface; the Mac leg (VELDO-0147).

## What the reviewer judges

- Normal use: the Runner launches Claude Code on Linux with the bound role's native tools, or the
  pinned version's in-run list when no role revision is bound.
- Threat model: a registered tool outside the launch set offered to the run; a tool the owner granted
  switched off; a registry tool left unclassified; a version launched without its qualified registry
  or classification. The owner's account and the installed binary are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); other versions
  and host kinds (Release 4).

## Notes

An extractor this specification commits in proof/VELDO-0173 records every registered tool with its
byte offset so a reviewer can check it against the pinned binary. The classification is data in
proof/VELDO-0173, one row per registry tool with its reason, read against VELDO-0160's tool_forms output; the lead reviews it before switch-off is
built. The launch list is a default, never a ceiling: only the owner widens a role's tools through
VELDO-0127, and the launch then passes that revision's native tools in place of the in-run list.

## History

2026-09-27: split VELDO-0165's tool registry and qualified-baseline criteria into this draft on the
lead's decision, with a full-registry falsifier that must fail on ReportFindings; the bound
PushNotification grant row moves to VELDO-0127 AC4. Only the owner marks a specification ready.

2026-09-27: marked ready by the owner (Telegram 29229, "all ready").

2026-09-28: implemented. A committed extractor, proof/VELDO-0173/extract_tools.py, reads the Bun module
graph of the pinned 2.1.281 bytes and resolves every item of the array getAllBaseTools returns: 86
registered tools, each with the offset of its name literal, and seven compiled-out slots. The
classification reads the 18-name in-run list of cli-formats.json; every other registry tool is outward,
each reason quoting its definition. The build registers no REPL tool (its slot's getter returns null), so
REPL keeps an in-run row marked unregistered and the init row expects the in-run list less REPL. The
Claude Code record's entry carries tool_registry and tool_classification; a missing or malformed one, or
an unclassified registry tool, refuses before acceptance as missing_evidence:engine_baseline:<version>.
The launch passes the tools option (the bound role revision's native tools, read from the contract's
capability configuration role_revision, else the in-run tools) and the disallowedTools option (the
registry less that set), each as one option=value argument; the baseline event names both, the source and
the revision. Suite 82_veldo_0173_tool_registry has seven behavior rows and three controls; all seven are
red by assertion at 7851ae9b, and all nine finding 173 mutations are rejected. The footprint adds the
VELDO-0062, VELDO-0160, VELDO-0129, VELDO-0141 and VELDO-0165 suites for their fake qualification
writers. No gate, real engine run or push was performed. Status unchanged; evidence is in
proof/VELDO-0173/README.md.

2026-09-28, integration with VELDO-0158 on main: the footprint adds suite 85 (VELDO-0158), whose test qualification record now carries the tool registry and classification this specification requires; no criterion changes.
