---
schema: veldo.spec/v1
id: VELDO-0230
title: Upgrading an agent CLI is one command
status: ready
risk: high
owner: Dmitry Grinberg
human_approval: required
lane: standalone
depends_on: [VELDO-0060, VELDO-0061, VELDO-0127, VELDO-0165, VELDO-0173]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - ".veldo/qualify.py"
  - "engine/.veldo/qualify.py"
  - ".veldo/control_engine_codex.py"
  - "engine/.veldo/control_engine_codex.py"
  - ".veldo/control_engine_claude.py"
  - "engine/.veldo/control_engine_claude.py"
  - ".veldo/control_agent_config_handoff.py"
  - "engine/.veldo/control_agent_config_handoff.py"
  - ".veldo/control_factory_setup_engines.py"
  - "engine/.veldo/control_factory_setup_engines.py"
  - ".veldo/control_launch.py"
  - "engine/.veldo/control_launch.py"
  - "packs/*/.veldo/**"
  - "engine/runtime/**"
  - ".veldo/runtime/**"
  - "packs/*/runtime/**"
  - "scripts/suites/**"
  - "scripts/suites/manifest.json"
  - "scripts/check_teeth_mutations.py"
  - "scripts/mutation_case_inputs.json"
  - "scripts/engine_census.py"
  - ".veldo/init_scaffold.py"
  - "engine/.veldo/init_scaffold.py"
  - "proof/VELDO-0156/capture_mentions.py"
  - "proof/VELDO-0156/render_offline.py"
  - "proof/VELDO-0162/setup_assets.py"
  - "proof/VELDO-0182/integration_fixtures.py"
  - "proof/VELDO-0186/fixtures.py"
  - "proof/VELDO-0172/fake_templates.json"
  - "proof/VELDO-0188/round2/served_scenario.py"
  - "proof/VELDO-0060/extract_cli.py"
  - "proof/VELDO-0060/cli-options.json"
  - "proof/VELDO-0061/extract_items.py"
  - "proof/VELDO-0061/codex-exec.json"
  - "proof/VELDO-0062/extract_formats.py"
  - "proof/VELDO-0062/cli-formats.json"
  - "proof/VELDO-0127/**"
  - "proof/VELDO-0141/extract_stream.py"
  - "proof/VELDO-0141/stream-formats.json"
  - "proof/VELDO-0155/extract_baseline.py"
  - "proof/VELDO-0155/claude-baseline.json"
  - "proof/VELDO-0156/extract_baseline.py"
  - "proof/VELDO-0156/codex-baseline.json"
  - "proof/VELDO-0165/extract_environment.py"
  - "proof/VELDO-0165/claude-environment.json"
  - "proof/VELDO-0165/codex-environment.json"
  - "proof/VELDO-0173/extract_tools.py"
  - "proof/VELDO-0173/claude-tools.json"
  - "proof/VELDO-0185/extract_login_status.py"
  - "proof/VELDO-0185/login-status.json"
  - "specs/VELDO-0230-upgrading-an-agent-cli-is-one-command.md"
  - "specs/index.md"
  - "proof/VELDO-0230/**"
behavior_bearing: true
observability:
  logs: >
    The qualify command prints each engine it qualified (version, binary path, digest), each file it
    wrote, and by name every Codex feature and every Claude Code tool the current classification does not
    know, recorded as not granted.
  metrics: >
    None added.
  traces: >
    The engines record and each qualification record name the version, binary path and digest every
    gate row and every launch compares against.
  error_taxonomy: >
    Unchanged refusals for a binary that differs from its qualification (stale_subject:engine_version,
    stale_subject:engine_digest). codex_unknown_default_feature is no longer raised: such a feature is off.
acceptance_criteria:
  - id: AC1
    text: >
      One engines record (engine/runtime/engines.json and its byte-identical mirrors) names the qualified
      Codex and Claude Code versions and binary paths. No engine module, suite, mutation, extractor or
      fixture builder carries a literal agent version, digest, binary path, model catalog, tool registry or
      feature list: each reads the engines record or the files the qualify command writes. A census row in
      the gate finds no such literal outside the generated files.
    falsified_by: >
      Planting '0.154.0' (or a digest) as a literal in a suite makes the census row red.
  - id: AC2
    text: >
      One command, python3 .veldo/qualify.py (with --codex <vendor binary> and --claude <version or path>;
      with no arguments it qualifies what is installed), runs every extractor in write mode, regenerates the
      VELDO-0127 fixtures, writes the Codex and the Claude qualification records (a new writer for Claude)
      to every runtime copy, and takes the Codex model tool modes from the catalog instead of code. Run
      against the currently qualified binaries it reproduces the shipped files byte for byte.
    falsified_by: >
      Its output differing from the shipped files on the qualified binaries; after qualifying a newer
      installed binary, any gate row still comparing against the old version.
  - id: AC3
    text: >
      A newer binary never blocks: a Codex feature or a Claude tool that the current classification does
      not know is recorded as not granted (off, outward) by default, listed by name in the qualify output
      and in the record, and launch proceeds with it off.
    falsified_by: >
      A fake binary that lists an extra default-on feature (or an extra tool) stopping the launch (today
      codex_unknown_default_feature), or the extra feature not being listed.
  - id: AC4
    text: >
      Setup and launch use the qualified Claude copy named by the engines record, never whatever claude is
      on PATH.
    falsified_by: >
      PATH pointing claude at a newer unqualified version and setup picking it.
required_evidence: [unit, integration]
rollback: >
  Revert the change: the literals return to the modules, suites and extractors, and the records are again
  written by hand (Claude) or by control_engine_codex.py qualify (Codex). No stored run record depends on
  the engines record.
---

## Intent

Owner decision, Telegram 38756-38760 (2026-11-03). A Codex CLI upgrade from 0.154.0 to 0.166.0 made the
gate fail 115 checks. The owner: "I don't want to waste time like this all the time. We will need to
upgrade, that's a waste of a cycle. Need a much simple upgrade path. All this red tape, I hate it!",
"Veldo needs to be a lot more hands off" and "There is so much innovation, veldo can't be a handcuff".

Upgrading Codex or Claude Code becomes one command that reads the new binary, writes every reference the
gate compares against, and lets the gate keep its meaning: each row still compares the installed binary
with its qualification; only where the reference comes from changes.

## Context

The measured inventory of 2026-11-03: the 0.154.0 model tool modes live in control_engine_codex.py
(MODEL_TOOL_MODES, and qualified_baseline refuses any record that differs); the 2.1.281 built-in plugin
and skill lists live in control_agent_config_handoff.py; a Codex feature the classification in
codex_features does not know, if on by default, stops every launch (codex_unknown_default_feature); the
qualified versions, digests and binary paths are literals in suites 78, 79, 80, 82 and 85, in about ten fake
package manifests, in check_teeth_mutations.py and in the extractors of VELDO-0060, 0061, 0062, 0141, 0155,
0156, 0165, 0173 and 0185 and the VELDO-0127 wire fixture. The Codex record has a writer
(control_engine_codex.py qualify); the Claude record was assembled by hand. Setup finds claude on PATH,
which now points at 2.1.317, not the qualified 2.1.281.

## Out of scope

Shipping the 0.166.0 and 2.1.317 records: the owner upgrades after landing with the one command. Any
change to what a run is granted: the classifications (which Codex feature maps to which grant, which
Claude tool is in-run) stay Veldo's own policy.

## What the reviewer judges

- Normal use: on the qualified binaries the command rewrites nothing; on a newer binary it writes every
  reference and record in one run and the affected gate rows then compare against the newer binary.
- Threat model: a newer binary that adds a tool source (a default-on feature, a registered tool) reaching a
  run granted; a gate row silently left comparing against nothing.
- Out of review scope (filed, not blocking): qualifying a version whose binary formats moved beyond what
  the extractors read; that is a named failure of the command, not a silent pass.
