---
schema: veldo.spec/v1
id: VELDO-0147
title: The Mac legs of the engine, account, capability, execution record and credential qualifications built on Linux first
status: draft
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W107
plan_revision: 4
depends_on: [VELDO-0060, VELDO-0061, VELDO-0062, VELDO-0124, VELDO-0125, VELDO-0127, VELDO-0141, VELDO-0144]
placement: [fleet, loop, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/fleet.py"
  - ".veldo/fleet.py"
  - "packs/*/.veldo/fleet.py"
  - "engine/.veldo/control_launch*.py"
  - ".veldo/control_launch*.py"
  - "packs/*/.veldo/control_launch*.py"
  - "engine/.veldo/control_engine*.py"
  - ".veldo/control_engine*.py"
  - "packs/*/.veldo/control_engine*.py"
  - "engine/.veldo/control_relay*.py"
  - ".veldo/control_relay*.py"
  - "packs/*/.veldo/control_relay*.py"
  - "engine/.veldo/control_execution_record*.py"
  - ".veldo/control_execution_record*.py"
  - "packs/*/.veldo/control_execution_record*.py"
  - "engine/.veldo/control_credential*.py"
  - ".veldo/control_credential*.py"
  - "packs/*/.veldo/control_credential*.py"
  - "engine/.veldo/project_runner_macos*.py"
  - ".veldo/project_runner_macos*.py"
  - "packs/*/.veldo/project_runner_macos*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "engine/runtime/claude-qualification*.json"
  - ".veldo/runtime/claude-qualification*.json"
  - "packs/*/runtime/claude-qualification*.json"
  - "engine/runtime/codex-qualification*.json"
  - ".veldo/runtime/codex-qualification*.json"
  - "packs/*/runtime/codex-qualification*.json"
  - "scripts/suites/*_veldo_0147_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0147-mac-legs-of-the-linux-first-qualifications.md"
  - "specs/index.md"
  - "proof/VELDO-0147/*"
behavior_bearing: true
observability:
  logs: >
    Record each Mac qualification run with the engine, its pinned version and digest, the account and
    profile the dispatch recorded, the capability set compared, the record's line count and digest and
    the credential ids delivered, or the named refusal; never a credential value.
  metrics: >
    Count Mac runs qualified and refused per engine, record lines and bytes relayed, and secrets frames
    written and removed.
  traces: >
    Join each Mac run to its dispatch, account, capability configuration revision, execution record and
    delivered credential ids.
  error_taxonomy: >
    Distinguish an unqualified or changed Mac executable, a paid-API credential or non-subscription
    login, a capability set that differs, a record line lost on the relay and an undeliverable secret;
    none is reported as a qualified run.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: The Claude Code configuration VELDO-0060 qualifies on Linux is qualified on the Mac through
      the relay, with the account and capabilities its dispatch recorded. Set and completeness: On the
      real Mac (VELDO-0124), dispatched through the relay (VELDO-0125), repeat VELDO-0060's lifecycle
      (launch, acceptance, observation streaming, stop, exit, artifact return), its pinned executable,
      everything-off baseline, paid-API guard, environment strip and pre-launch usage caps; read back
      that the engine environment carries exactly the profile of the account the dispatch recorded for
      the Mac and no paid-API credential (VELDO-0062 AC1); and compare the capabilities the engine
      reports at launch with the role's accepted revision in both directions (VELDO-0127 AC2).
      Falsifier: Skip executable binding on the Mac after the pinned copy's digest changes; the Mac
      unexpected-launch check must fail.
    falsified_by: >
      Skip executable binding on the Mac after the pinned copy's digest changes; the Mac
      unexpected-launch check must fail.
  - id: AC2
    text: >
      Claim: The Codex configuration VELDO-0061 qualifies on Linux is qualified on the Mac through the
      relay, with the account and capabilities its dispatch recorded. Set and completeness: On the real
      Mac through the relay, repeat VELDO-0061's lifecycle, pinned vendor binary, everything-off
      baseline, paid-API guard (`OPENAI_API_KEY` and `CODEX_API_KEY` removed, a ChatGPT login required
      before the first turn), environment strip and pre-launch usage caps; read back that the engine
      environment carries exactly the `CODEX_HOME` of the account the dispatch recorded for the Mac
      (VELDO-0062 AC1); and compare the capabilities at launch with the role's accepted revision
      (VELDO-0127 AC2). Falsifier: Leave `OPENAI_API_KEY` in the Mac engine environment; the Mac paid-API
      stop row must fail.
    falsified_by: >
      Leave `OPENAI_API_KEY` in the Mac engine environment; the Mac paid-API stop row must fail.
  - id: AC3
    text: >
      Claim: A Mac run's streams arrive over SSH through the relay into the Linux launch receiver and are
      kept as that run's execution record exactly as a Linux run's are. Set and completeness: Run real
      Claude Code and Codex workers on the Mac on a unit whose work calls tools, runs a command that
      writes to its error stream and edits a file; compare the record kept on Linux, line by line and in
      order, with what the engine emitted on the Mac, including the error stream, with the run's exact
      credential values replaced before the scanner runs (VELDO-0141 AC1). Falsifier: Drop the Mac run's
      error stream at the relay; the Mac complete-record check must fail.
    falsified_by: >
      Drop the Mac run's error stream at the relay; the Mac complete-record check must fail.
  - id: AC4
    text: >
      Claim: A Mac run receives exactly the credential values its configuration's servers reference
      through one secrets frame, never through a command line, the packet, the contract, the journal or
      the Mac's keychain. Set and completeness: After the release and before the wrapper execs, the
      receiver writes one secrets frame over the same SSH channel; the wrapper reads exactly that frame,
      writes the run's private file (mode 0600 in a 0700 directory) and only then execs; the receiver
      removes that directory over SSH when the run ends, and the journal records only the credential ids
      delivered (VELDO-0144 AC3). Inspect every launched process's command line and environment on the
      Mac, the packet, the contract, the journal and the Mac's keychain. Falsifier: Put a credential value
      in the packet sent to the Mac instead of the secrets frame; the Mac no-value-in-packet row must
      fail.
    falsified_by: >
      Put a credential value in the packet sent to the Mac instead of the secrets frame; the Mac
      no-value-in-packet row must fail.
required_evidence: [unit, integration]
rollback: >
  Mark the Mac profile unqualified so no unit is routed to it; Linux work, recorded runs, records and
  credential records are unchanged. No automatic rollback is authorized.
---

## Intent

The owner needs the Mac in Release 1 because iOS builds need macOS. The engine, account, capability,
execution record and credential qualifications are built on Linux first, so the owner can watch real
runs sooner; this specification qualifies each of them on the Mac once the Mac worker and its relay
exist.

## Context

W107 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. A specification
ships whole, and the run-check refuses one whose dependencies are not shipped, so a Mac leg inside a
specification built before the Mac stage would hold that specification unshipped until the Mac lands.
Section 12 of the approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md)
(owner Telegram 29162) builds VELDO-0060, 0061, 0062, 0141 in its stage 1 and VELDO-0127 and 0144 in its
stage 2, and the Mac worker (VELDO-0124, VELDO-0125) in its stage 3. The Mac legs of those
specifications move here: VELDO-0060's and VELDO-0061's Mac configuration, the Mac read-back of
VELDO-0062 AC1, the Mac handoff of VELDO-0127 AC2, the Mac run of VELDO-0141 AC1 and the Mac secrets
frame of VELDO-0144 AC3. Owner Telegram 28852 keeps the Mac in Release 1.

## Out of scope

Separating the engine login from worker tools (Release 2, owner Telegram 29163); other Mac or macOS
versions and host kinds (Release 4); machine loss and relay reconnect (Release 2); the Linux legs, which
their own specifications keep.

## What the reviewer judges

- Normal use: the Runner routes a unit to the Mac; the pinned Claude Code or Codex executable runs there
  with the account and capabilities its dispatch recorded, its streams are kept on Linux as its execution
  record, and its MCP servers get their credentials through one secrets frame.
- Threat model: a Mac run of a changed or unknown executable; a paid API key or a non-subscription login
  reaching a Mac run's first turn; another account's profile on the Mac; a capability dropped or added
  on the Mac; a Mac record line lost, reordered or kept unredacted; a credential value on a Mac command
  line, in the packet, the contract, the journal or the Mac's keychain, or a private directory left
  behind. The owner's account, the Mac over SSH and the installed engines are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); the items in
  Out of scope above; forged rows in our own store and files planted in the installed directory.

## Notes

Each criterion repeats on the Mac what its Linux specification already qualified, against the same
recorded configuration, so a Mac difference is found as a difference rather than rewritten as a new
requirement. The Linux specifications keep their own evidence; this one records the Mac runs and their
negative controls. It is built after VELDO-0124 and VELDO-0125 in stage 3 of the design's critical path.

## History

2026-09-25: written on the review of PLAN-0019 revision 4, which moved every Mac leg out of the
specifications built in stages 1 and 2 of the design's critical path. The legs of VELDO-0060, 0061, 0062,
0127 and 0141 came from ready specifications and the leg of VELDO-0144 from a draft, so this
specification is a draft; the owner decides readiness.
