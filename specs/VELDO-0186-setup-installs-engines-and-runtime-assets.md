---
schema: veldo.spec/v1
id: VELDO-0186
title: Factory setup installs every runtime asset and qualification record the installed modules read and pins both qualified engines, so the installed launch receiver binds Claude Code and Codex
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W146
plan_revision: 4
depends_on: [VELDO-0139, VELDO-0155, VELDO-0156, VELDO-0160, VELDO-0172, VELDO-0173]
placement: [engine, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_engine_claude*.py"
  - ".veldo/control_engine_claude*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "engine/runtime/*"
  - ".veldo/runtime/*"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0186_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0186-setup-installs-engines-and-runtime-assets.md"
  - "specs/index.md"
  - "proof/VELDO-0186/*"
behavior_bearing: true
observability:
  logs: >
    Record each runtime asset setup installs with its path and digest and each engine pin with its version
    and digest; never a credential.
  metrics: >
    Count runtime assets installed, pins made, and binds refused after setup.
  traces: >
    Join each launch after setup to the installed qualification record and pin it bound.
  error_taxonomy: >
    Distinguish a module that reads a runtime file the installation lacks
    (missing_evidence:runtime_asset:<path>), an installed engine version the qualification record does not
    list (missing_evidence:engine_baseline:<version>) and a pin whose digest differs from the qualified one
    (binding_mismatch:engine_digest).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The installation carries every runtime file an installed module reads, not only the Python
      modules, so no installed module reads a file the installation lacks. Set and completeness: The
      installer's fixed-point census of the modules a member loads (control_service) also collects every
      runtime file a loaded module names: `runtime/claude-qualification.json`,
      `runtime/codex-qualification.json` and `runtime/langgraph-records.json` today, and any file a later
      module names the same way; each is installed beside the modules with its digest recorded, and a module
      that names a runtime file the source tree lacks refuses installation by name
      (missing_evidence:runtime_asset:<path>). The suite installs a fixture and lists the installed tree
      against every runtime name the loaded modules read. Falsifier: Install only the `.py` modules, as
      setup does today, and the runtime-assets row must fail on `runtime/claude-qualification.json`.
    falsified_by: >
      Install only the `.py` modules, as setup does today, and the runtime-assets row must fail on
      `runtime/claude-qualification.json`.
  - id: AC2
    text: >
      Claim: Setup pins the qualified Claude Code version under the state root and records the qualified
      Codex vendor binary, so a launch through the installed service binds both. Set and completeness: Setup
      runs control_engine_claude `pin` for the version the installed qualification record lists, copying
      the versioned file to `<state root>/engines/claude_code/<version>` at mode 0555, and refuses by name a
      host whose installed version is not listed or whose copy's digest is not the qualified one; it checks
      the Codex vendor binary's digest against its qualification record the same way. After setup,
      control_launch `bind` accepts a `claude_code` adapter naming the pinned version and a `codex` adapter
      naming the vendor binary, the adapters VELDO-0185 AC1 writes. The suite sets up with fixture engines and qualification
      records for their digests. Falsifier: Skip the Claude Code pin, and the bind row must fail on the
      absent pinned copy.
    falsified_by: >
      Skip the Claude Code pin, and the bind row must fail on the absent pinned copy.
required_evidence: [unit, integration]
rollback: >
  Stop the service and remove the pinned copies and installed runtime files by hand; the store and every
  accepted record are unchanged. No automatic rollback is authorized.
---

## Intent

The factory the owner sets up can actually run his engines: the files the engines need are installed and
both engines are pinned, so the installed receiver can launch Claude Code and Codex.

## Context

W146 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The VELDO-0154
review on 2026-09-27 found that setup installs only `.py` modules, so `runtime/claude-qualification.json`
and a pinned Claude Code binary are missing and Claude Code cannot launch through an installed service at
all; the owner's accounts are three Claude Code and one Codex. The qualification records and the pin are
VELDO-0060, VELDO-0155 and VELDO-0156's; the receiver's adapters, the work configuration, the second
setup run and the end-to-end dispatch on every account are VELDO-0185's, which is built after this
specification because its adapters name this pin. VELDO-0139 is a standalone built item, so its edge is kept here and not in the plan graph. A
draft: only the owner marks it ready.

## Out of scope

Replacing installed engine files or pins after an update (Release 2, VELDO-0139's Notes); requalifying a
new engine version (VELDO-0060, VELDO-0061); the Mac's engines (VELDO-0147).

## What the reviewer judges

- Normal use: the owner sets up a fresh host, and the installed tree holds every runtime file its modules
  read and a pinned Claude Code copy, so a launch through the installed receiver binds both engines.
- Threat model: an installed module reading a runtime file that is not there, so a launch fails at run
  time; an engine launched unpinned or from the auto-updating link; a pin whose digest is not the
  qualified one.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as the
  installer's updater removing a version between check and pin (setup refuses by name and a re-run pins);
  files planted in the installed directory.

## Notes

The census finds runtime files the way it finds modules, from the literals the loaded modules name, so a
new runtime file is installed without a list kept by hand.

## History

2026-09-27: new draft for the VELDO-0154 review finding of 2026-09-27 that Claude Code cannot launch through
an installed service. Only the owner marks a specification ready.

2026-09-27, review of the drafts: the order with VELDO-0185 is reversed, since VELDO-0185's adapters need
this pin: this specification no longer depends on VELDO-0185, and its former AC3 (dispatch on every
account after login, and the second setup run) moved to VELDO-0185 AC4 and AC3, where the login check
and control_accounts are. Still a draft.

2026-09-27: marked ready by the owner (Telegram 29301, "All ready otherwise"), with his two points applied: plain-words commands (29299) and smart add on the subscription instead of a paid API (29300).
