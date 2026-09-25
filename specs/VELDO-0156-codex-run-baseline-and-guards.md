---
schema: veldo.spec/v1
id: VELDO-0156
title: Every Codex run starts on the everything-off baseline, behind the paid-API guard and the environment strip
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W116
plan_revision: 4
depends_on: [VELDO-0039, VELDO-0061]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_engine_codex*.py"
  - ".veldo/control_engine_codex*.py"
  - "packs/*/.veldo/control_engine_codex*.py"
  - "engine/runtime/codex-qualification*.json"
  - ".veldo/runtime/codex-qualification*.json"
  - "packs/*/runtime/codex-qualification*.json"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0156_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0156-codex-run-baseline-and-guards.md"
  - "specs/index.md"
  - "proof/VELDO-0156/*"
behavior_bearing: true
observability:
  logs: >
    Record each launch's baseline options, the variable names removed from the engine environment, the
    login method the run reports and any named stop; never a variable's value.
  metrics: >
    Count launches, runs stopped before their first turn by reason, and removed variables by name.
  traces: >
    Join each launch to its dispatch, account profile and the pinned executable digest it ran.
  error_taxonomy: >
    Distinguish a profile source that loaded, a paid-API variable present, a login that is not through
    ChatGPT, and a stripped variable present; none lets the run take a first turn.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Every Codex run starts with every profile source off, so the account profile (`CODEX_HOME`)
      supplies only the login and the same role behaves the same on every account. Set and completeness:
      Launch the pinned vendor binary (VELDO-0061 AC1) with the `ignore-user-config` and `ignore-rules`
      options and a generated configuration, `project_doc_max_bytes` at zero and no hooks in the generated
      configuration. Plant a user configuration, rules, a project document and a hook in the account
      profile and the clone, each where only its own switch keeps it out, and require none of them in the
      run, read from its event stream and its effective configuration, one row per planted item. Each
      internal setting is qualified on the pinned version before use. Falsifier: Four mutants, one per
      switch, each with the others in place: drop the `ignore-user-config` option, and the
      planted-user-configuration row must fail; drop the `ignore-rules` option, and the planted-rules row
      must fail; leave `project_doc_max_bytes` at its default, and the planted-project-document row must
      fail; generate the configuration with the account profile's hooks copied into it, and the
      planted-hook row must fail.
    falsified_by: >
      Four mutants, one per switch, each with the others in place: drop the `ignore-user-config` option,
      and the planted-user-configuration row must fail; drop the `ignore-rules` option, and the
      planted-rules row must fail; leave `project_doc_max_bytes` at its default, and the
      planted-project-document row must fail; generate the configuration with the account profile's hooks
      copied into it, and the planted-hook row must fail.
  - id: AC2
    text: >
      Claim: No paid-API credential variable reaches a Codex engine environment. Set and completeness:
      Plant `OPENAI_API_KEY` and `CODEX_API_KEY` in the caller's environment, launch a run, and read back
      the engine's environment: the receiver removed both. Falsifier: Leave a planted `OPENAI_API_KEY` in
      the engine environment; the engine-environment read-back row must fail.
    falsified_by: >
      Leave a planted `OPENAI_API_KEY` in the engine environment; the engine-environment read-back row
      must fail.
  - id: AC3
    text: >
      Claim: A Codex run that is not logged in through ChatGPT is stopped by name before its first turn,
      and the engine itself accepts only a ChatGPT login read from the account profile's file. Set and
      completeness: The generated configuration sets `forced_login_method` to ChatGPT and the credentials
      store to file. Launch a run on a profile logged in through ChatGPT and on profiles with no login and
      with an API-key login; the first takes its first turn with the login read from its profile's file
      (the file-login row), and each other is stopped by name before its first turn with no model turn
      sent (the paid-API stop row). With the adapter's own stop turned off for that row only, launch the
      API-key profile and require the engine itself to refuse the login because of `forced_login_method`
      (the engine-refusal row). Falsifier: Let a run that is not logged in through ChatGPT take its first
      turn, and the paid-API stop row must fail; generate the configuration without `forced_login_method`,
      and the engine-refusal row must fail; set the credentials store to the keyring, and the file-login
      row must fail.
    falsified_by: >
      Let a run that is not logged in through ChatGPT take its first turn, and the paid-API stop row must
      fail; generate the configuration without `forced_login_method`, and the engine-refusal row must
      fail; set the credentials store to the keyring, and the file-login row must fail.
  - id: AC4
    text: >
      Claim: The trusted wrapper strips the SSH agent, the session bus and the Git tokens from the
      environment it execs Codex with, and the engine gets a runtime directory of its own. Set and
      completeness: Plant `SSH_AUTH_SOCK`, `SSH_AGENT_PID`, `DBUS_SESSION_BUS_ADDRESS`, `GH_TOKEN` and
      `GITHUB_TOKEN` in the receiver's environment, launch a contained Codex run, and read back the
      engine's environment: none of them is present (the strip read-back row), and `XDG_RUNTIME_DIR` names
      an empty directory of the run's own, never the receiver's (the private-runtime-directory row); the
      receiver's own `systemd-run` and `systemctl` calls still reach the user manager (the user-manager
      row). Falsifier: Leave a planted `SSH_AUTH_SOCK` in the environment the wrapper execs Codex with,
      and the strip read-back row must fail; pass the receiver's own `XDG_RUNTIME_DIR` to the engine, and
      the private-runtime-directory row must fail; strip the session bus from the receiver's own
      environment instead of the one it execs, and the user-manager row must fail.
    falsified_by: >
      Leave a planted `SSH_AUTH_SOCK` in the environment the wrapper execs Codex with, and the strip
      read-back row must fail; pass the receiver's own `XDG_RUNTIME_DIR` to the engine, and the
      private-runtime-directory row must fail; strip the session bus from the receiver's own environment
      instead of the one it execs, and the user-manager row must fail.
required_evidence: [unit, integration]
rollback: >
  Disable new Codex launches while preserving accepted records and unresolved work; no run launches
  without these guards. No automatic rollback is authorized.
---

## Intent

Every Codex run the factory starts behaves the same on every account, never reaches a paid model API,
and never carries the owner's SSH agent, session bus or Git tokens into the engine.

## Context

W116 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 1. Section 6 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs the everything-off baseline and the paid-API guard, and section 3 the environment strip;
its section 12 builds them with the Codex adapter (item 3). They were VELDO-0061 AC5, one criterion
under one falsifier that tested only the paid-API guard, and are split out so each guard has its own
criterion and a falsifier that breaks exactly that guard. VELDO-0061 keeps the adapter lifecycle, the
pinned executable, stopping and the usage caps. This new specification is draft; authoring it supplies
neither implementation proof nor operational activation.

## Out of scope

The role's own selections (VELDO-0127); separating the engine login from the worker's tools (Release 2,
owner Telegram 29163); the Mac leg (VELDO-0147); the Claude Code guards (VELDO-0155).

## What the reviewer judges

- Normal use: the Runner launches Codex for a dispatched unit on Linux; the account profile gives the
  login and nothing else, the engine environment holds no paid-API key, SSH agent, session bus or Git
  token, and the run takes its first turn on a ChatGPT login.
- Threat model: a run that picks up the account's own configuration, rules, project documents or hooks;
  a paid-API key reaching the engine; a run that is not logged in through ChatGPT getting a first turn;
  the SSH agent, the session bus or a Git token reaching the engine environment, or the engine sharing
  the receiver's runtime directory. The owner's account and the installed engine are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); a worker's
  tools reading their own engine login (Release 2, owner Telegram 29163); a worker deliberately
  reaching the keystore or the agent through the owner's unconfined keyring daemon (the stated MVP
  boundary of the design's section 3); other versions and host kinds (Release 4).

## Notes

The strip is the same trusted wrapper VELDO-0155 AC4 qualifies for Claude Code; this specification reads
back the Codex engine's environment against the same list, so whichever of the two is built first
implements the wrapper's strip and the other qualifies it for its engine.

Use canonical engine assets and synchronize installed copies. Inventory every asset the selected
journey installs. Compare executable registrations to each criterion's declared universe, observe the
real named interfaces, and retain the driven negative-control diff and named failed row. Fixtures
cannot certify real engine or host behavior. Required evidence labels describe future implementation
proof, not tests run by this writing revision.

## History

2026-09-25: split from VELDO-0061 AC5 on the third review of PLAN-0019 revision 4, so the everything-off
baseline, the paid-API guard and the environment strip each have their own criterion and a falsifier
that breaks exactly that guard: a planted profile item that must not load (AC1), a planted key that must
be absent from the engine environment read-back (AC2), the stop that must fire on a login that is not
through ChatGPT (AC3), and a planted agent socket the strip must remove (AC4). The criteria carry
VELDO-0061 AC5's text, and AC4 also checks that the user manager stays reachable, which is why the
design's section 3 puts the strip in the wrapper; no function is added or cut. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4, fourth review: AC1's falsifier dropped one of its four switches, so it
now drives one mutant per switch, each against its own planted item placed where only that switch keeps
it out. AC3's `forced_login_method` and file credentials store get falsifiers of their own (a row where
the engine itself refuses an API-key login with the adapter's stop off, and a row where the login is read
from the profile's file), and AC4's private runtime directory and the user manager staying reachable get
theirs beside the strip's. Criterion meaning unchanged. A draft.
