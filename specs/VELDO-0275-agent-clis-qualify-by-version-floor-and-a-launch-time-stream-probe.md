---
schema: veldo.spec/v1
id: VELDO-0275
title: Claude Code and Codex qualify by a minimum version and a launch-time stream probe instead of a binary digest, with environment and new capabilities decided by named patterns
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0230]
placement: [fleet]
protected_paths: []
footprint:
  - ".veldo/qualify.py"
  - "engine/.veldo/qualify.py"
  - ".veldo/control_engine_claude.py"
  - "engine/.veldo/control_engine_claude.py"
  - ".veldo/control_engine_codex.py"
  - "engine/.veldo/control_engine_codex.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - ".veldo/control_containment.py"
  - "engine/.veldo/control_containment.py"
  - ".veldo/control_factory_setup_engines.py"
  - "engine/.veldo/control_factory_setup_engines.py"
  - ".veldo/runtime/**"
  - "engine/runtime/**"
  - "scripts/engine_census.py"
  - "scripts/check_teeth_mutations.py"
  - "proof/VELDO-0127/**"
  - "scripts/suites/**"
  - "specs/VELDO-0275-agent-clis-qualify-by-version-floor-and-a-launch-time-stream-probe.md"
  - "specs/index.md"
  - "proof/VELDO-0275/**"
behavior_bearing: true
observability:
  logs: >
    Each launch prints one line naming the engine, the resolved binary, its version, the floor it was
    held to and the probe result (parsed, or the first frame that failed to parse). Setup prints the same
    line once per engine.
  metrics: >
    The execution record carries the engine version and the probe result in place of the binary digest.
  traces: >
    A failed probe keeps the raw frames it read (bounded) in the run's evidence.
  error_taxonomy: >
    Added: below_version_floor, stream_probe_failed (with the frame). Removed: stale_subject:engine_digest,
    binding_mismatch:engine_digest and missing_evidence:engine_qualification for a version not in the
    record. Unchanged: every credential and capability refusal.
acceptance_criteria:
  - id: AC1
    text: >
      An engine is accepted by version, not digest. runtime/engines.json holds, per engine, a minimum
      version and the binary resolution rule (the versioned copy the installer keeps, as today); any
      installed version at or above the floor is accepted without a new record, a commit or a ticket.
      control_engine_codex.py no longer refuses on the binary's sha256, control_launch.py's wrapper no
      longer binds the digest, and control_engine_claude.py no longer needs a per-version entry. The
      per-binary qualification records (codex-qualification.json, 793 KB; claude-qualification.json,
      96 KB) are deleted with the extractors that only fed them; tables the stream reader still needs
      stay as a small reviewed file in .veldo/runtime.
    falsified_by: >
      A new suite launches a fake engine reporting a version above the floor whose bytes differ from any
      recorded binary: accepted. One reporting a version below the floor: refused below_version_floor.
      Registered mutations from a green baseline: (1) the floor comparison is lexical: the row with
      2.1.99 against a floor of 2.1.317 goes red; (2) the digest check is restored: the different-bytes
      row goes red.
  - id: AC2
    text: >
      Every launch starts with a stream probe: before the prompt is sent the engine runs the zero-turn
      probe the adapters already run (assistants_before_prompt, num_turns 0), and every frame it prints is
      parsed by the same stream reader the run uses. A frame the reader cannot classify, or a missing
      result frame, refuses the launch as stream_probe_failed with the frame, so a CLI that changed its
      stream format never starts a run.
    falsified_by: >
      The suite drives a fake engine that prints one frame of an unknown type in the probe: refused with
      that frame; a fake whose probe matches today's format: accepted. Registered mutation: the launch
      skips the probe when the version is above the floor: the unknown-frame row goes red.
  - id: AC3
    text: >
      Environment and new capabilities are decided by rules, not one decision per item. The variables
      handed to an engine are those matching named allow patterns in the reviewed decisions file; every
      variable matching the credential name patterns of VELDO-0254 (on its branch, not yet on main) is withheld unless the credential
      delivery of VELDO-0158 hands it, exactly as today. A tool, feature, option or plugin the role does
      not list stays off (VELDO-0127 AC4 unchanged); a new one is off unless a named pattern grants it,
      and the launch line lists it by name. No upgrade ever needs a decision entry to start.
    falsified_by: >
      The suite launches with a caller environment holding one allowed name, one unlisted name and one
      credential-shaped name (GH_TOKEN): only the first reaches the fake engine. A fake engine announcing a
      new default-on feature runs with it off and listed. Registered mutations: (1) the allow rule matches
      everything: the unlisted-name row goes red; (2) the credential filter is skipped: the GH_TOKEN row
      goes red; (3) new features default on: the new-feature row goes red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit and run python3 .veldo/qualify.py on the installed binaries to rewrite the deleted
  records; launches are held to the digest again.
---

## Intent

Weight audit item 6: stop paying a ticket per CLI upgrade. Claude Code ships often (four versions on this
host); 81 commits on main since 2026-09-01 mention qualification (verified); the 2.1.317 and 0.166.0
upgrade took VELDO-0230 plus three fix rounds.

## Context

Verified on main at afa292f0: .veldo/qualify.py is 696 lines; .veldo/runtime holds
codex-qualification.json (793,287 bytes), claude-qualification.json (96,204) and
capability-decisions.json (27,943), as the audit says. engines.json pins a path, version and sha256 per
engine. Codex is refused on a digest mismatch (stale_subject:engine_digest); Claude Code is keyed by
version entries in its record. capability-decisions.json holds 82 Claude Code entries (19 of them
environment names) and 24 Codex entries, plus seven rules that cite the specs they protect.

Owner approval: required. This changes what reaches an agent process (environment, features, tools),
which is security under the owner's scope (Telegram 39708).

## Out of scope

Credential delivery (VELDO-0158), the role capability lists (VELDO-0127), account pools and usage windows.

## What the reviewer judges

- Normal use: factory setup and every launch on this host after an upgrade.
- No credential-shaped variable reaches an engine except through delivery; nothing new turns on without a
  named rule; a stream format change refuses before the prompt.
- Out of review scope: a new CLI that changes behavior without changing its stream format (the audit's
  accepted risk).

## History

2026-11-07: drafted by the lead from the weight audit's item 6 (Telegram 39708, 39710). A draft; needs
the owner.
