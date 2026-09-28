---
schema: veldo.spec/v1
id: VELDO-0186
title: Factory setup installs every runtime asset and qualification record and pins both engines, so after the owner logs in each account the installed factory dispatches build and review to both engines on every account
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W146
plan_revision: 4
depends_on: [VELDO-0139, VELDO-0155, VELDO-0156, VELDO-0160, VELDO-0172, VELDO-0173, VELDO-0185]
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
    Record each runtime asset setup installs with its path and digest, each engine pin with its version and
    digest, and each account's first dispatch after setup with its engine and station; never a credential.
  metrics: >
    Count runtime assets installed, pins made, and dispatches per engine and account after setup.
  traces: >
    Join each launch after setup to the installed qualification record and pin it bound.
  error_taxonomy: >
    Distinguish a module that reads a runtime file the installation lacks
    (missing_evidence:runtime_asset:<path>), an installed engine version the qualification record does not
    list (missing_evidence:engine_baseline:<version>), a pin whose digest differs from the qualified one
    (binding_mismatch:engine_digest) and an account not yet logged in (missing_authority:account_login:<id>).
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
      the Codex vendor binary's digest against its qualification record the same way. After setup, `bind`
      accepts both adapters of VELDO-0185 AC1. The suite sets up with fixture engines and qualification
      records for their digests. Falsifier: Skip the Claude Code pin, and the bind row must fail on the
      absent pinned copy.
    falsified_by: >
      Skip the Claude Code pin, and the bind row must fail on the absent pinned copy.
  - id: AC3
    text: >
      Claim: After setup and the owner's one-time login of each account, the installed factory dispatches
      build and review work to both engines on every registered account, and a second setup run changes
      nothing. Set and completeness: With the owner's accounts registered (three Claude Code and one Codex in
      his case) and each logged in once (VELDO-0160 AC1's login step), a unit submitted after setup is built
      and reviewed through the installed service and receiver alone, and over successive units every
      account runs at least one build or review, with the Codex account among them; an account not yet
      logged in is refused by name (missing_authority:account_login:<id>) and takes no work, and the others
      carry on. A second setup run follows VELDO-0171 AC4's rule: every installed file and pin is byte for
      byte the same and nothing is pinned or installed again. The suite uses fake engines that print the
      installed CLIs' output shape (VELDO-0172). Falsifier: Write the receiver's adapters without `codex`,
      and the every-account row must fail on the Codex account with no run.
    falsified_by: >
      Write the receiver's adapters without `codex`, and the every-account row must fail on the Codex
      account with no run.
required_evidence: [unit, integration]
rollback: >
  Stop the service and remove the pinned copies and installed runtime files by hand; the store and every
  accepted record are unchanged. No automatic rollback is authorized.
---

## Intent

The factory the owner sets up can actually run his engines: the files the engines need are installed,
both engines are pinned, and after he logs in each account once, work runs on all of them.

## Context

W146 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The VELDO-0154
review on 2026-09-27 found that setup installs only `.py` modules, so `runtime/claude-qualification.json`
and a pinned Claude Code binary are missing and Claude Code cannot launch through an installed service at
all; the owner's accounts are three Claude Code and one Codex. The qualification records and the pin are
VELDO-0060, VELDO-0155 and VELDO-0156's; the receiver's adapters and the work configuration are
VELDO-0185's. VELDO-0139 is a standalone built item, so its edge is kept here and not in the plan graph. A
draft: only the owner marks it ready.

## Out of scope

Replacing installed engine files or pins after an update (Release 2, VELDO-0139's Notes); requalifying a
new engine version (VELDO-0060, VELDO-0061); the Mac's engines (VELDO-0147).

## What the reviewer judges

- Normal use: the owner sets up a fresh host, logs in each of his four accounts once, sends a unit, and it
  is built and reviewed; over the day every account runs work, the Codex account among them.
- Threat model: an installed module reading a runtime file that is not there, so a launch fails at run
  time; an engine launched unpinned or from the auto-updating link; a pin whose digest is not the
  qualified one; an account that is not logged in taking work; a re-run that repins or reinstalls.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as the
  installer's updater removing a version between check and pin (setup refuses by name and a re-run pins);
  files planted in the installed directory.

## Notes

The census finds runtime files the way it finds modules, from the literals the loaded modules name, so a
new runtime file is installed without a list kept by hand.

## History

2026-09-27: new draft for the VELDO-0154 review finding of 2026-09-27 that Claude Code cannot launch through
an installed service. Only the owner marks a specification ready.
