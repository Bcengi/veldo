---
schema: veldo.spec/v1
id: VELDO-0275b
title: A new Claude Code or Codex version is qualified automatically and reported in the owner's daily summary, and engine environment and new capabilities are decided by named patterns
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0275, VELDO-0272]
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
  - "scripts/check_teeth_mutations.py"
  - "scripts/suites/**"
  - "specs/VELDO-0275b-new-agent-cli-versions-qualify-automatically-and-environment-by-named-patterns.md"
  - "specs/index.md"
  - "proof/VELDO-0275b/**"
behavior_bearing: true
observability:
  logs: >
    Each qualification run prints one line per check (name, outcome, duration) and one line naming the
    version, its digest and the verdict. Each launch line lists every new capability left off by name.
  metrics: >
    The qualification summary per version (per check: name, outcome, duration).
  traces: >
    A failed check keeps its summary in proof; no raw transcript.
  error_taxonomy: >
    Unchanged from VELDO-0275; a failed qualification is a notice to the owner, not a refusal of any run.
acceptance_criteria:
  - id: AC1
    text: >
      A new version is qualified automatically, with the same rigor as today and no ticket. Owner,
      Telegram 39751 to 39753 (2026-11-07): "Upgrades for harnesses are very important to do right. I
      don't want to wing it", and yes to automated qualification. When the installer or the service
      loop finds a version that is not approved, Veldo runs the qualification suite on it by itself,
      outside every work run and with no work credentials: the stream probe of VELDO-0275 AC3; a fixed set of
      sample tasks through the real adapter end to end in a scratch repository (read a file, edit and
      commit, run a command, refuse a tool the role does not list, the permission mode the role sets);
      a credential-shaped variable in the caller environment withheld (AC2); and result, usage and limit
      frames parsed by the run's own stream reader. Only when every check passes does Veldo commit the
      new version, its digest and a qualification summary (per check: name, outcome, duration; under
      1 MB, no raw transcript) to runtime/engines.json and proof, and report it in the owner's daily
      summary. Any failure leaves the approved version in place, keeps the failed summary, and sends the
      owner one line naming the version and the failed check. A version is qualified at most once per
      digest; a failed digest is not retried until the owner asks.
    falsified_by: >
      The suite drives fake engines: one that passes every check is approved with a summary naming every
      check; one that mishandles one check (prints an unknown frame, uses an unlisted tool, or receives the
      credential-shaped variable) is not approved, the approved version is unchanged, and the notice names
      that check. Registered mutations: (1) approval written before the last check finishes: the
      unlisted-tool row goes red; (2) a failed check counted as passed: the unknown-frame row goes red;
      (3) a failed digest re-qualified on every loop: the at-most-once row goes red.
  - id: AC2
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
  Revert the commit; versions are approved again by the qualify.py run and commit of VELDO-0275, and the
  environment is decided by the per-name decisions of today.
---

## Intent

The second half of the weight audit's item 6 (Telegram 39708, 39710; owner's word 39751 to 39753): no
ticket per CLI upgrade, and no decision entry per environment name or new capability. Split out of
VELDO-0275 because neither half could be built on main 918e7c0e.

## Dependencies (why this is a draft)

- AC1 posts into the owner's daily summary. That summary is not on main. VELDO-0272 AC4 provides it
  (control_telegram_report event daily_landed, and .veldo/landed_summary.py until the factory runs); it is
  ready and unlanded, on agent/claude/veldo-approval-scope. AC1 also needs VELDO-0275 (the digest pin,
  the summary format and the launch probe it reuses). Where the failure notice is sent from and which
  service loop module starts a qualification still has to be named in the footprint.
- AC2 withholds variables matching "the credential name patterns of VELDO-0254". None exist: VELDO-0254 is
  wholly on main and delivered credential value formats (.veldo/secret_scan.py FORMATS) read by a launch
  scan that refuses the launch (.veldo/control_launch.py launch_scan, credential_delivery_site:environment:
  <name>), not name patterns that withhold a variable. The owner decides whether AC2 withholds by a name
  pattern list this spec defines, or relies on that launch refusal; until then AC2 is not buildable.

## Out of scope

Credential delivery (VELDO-0158), the role capability lists (VELDO-0127), the digest pin and the launch
probe (VELDO-0275).

## What the reviewer judges

- No version is approved unless every check passed, and a failure leaves the approved version in place.
- No credential-shaped variable reaches an engine except through delivery; nothing new turns on without a
  named rule.

## History

2026-11-08: split out of VELDO-0275 by the lead (proof/VELDO-0275/README.md, blockers 2 and 3). AC1 here is
VELDO-0275's AC2 and AC2 here is its AC4, each with the same required behaviour and falsifier; only the
cross-references were renamed (AC3 to VELDO-0275 AC3, AC4 to AC2). Draft: it depends on VELDO-0272 AC4 for
the daily summary and on an owner decision for the credential name patterns that VELDO-0254 did not provide.
