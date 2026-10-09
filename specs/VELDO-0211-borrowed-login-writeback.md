---
schema: veldo.spec/v1
id: VELDO-0211
title: Borrowed engine logins retain rotated credentials
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
placement: [enforcement]
protected_paths: [scripts/agent_sandbox.py, engine/scripts/agent_sandbox.py]
footprint:
  - scripts/agent_sandbox.py
  - engine/scripts/agent_sandbox.py
  - proof/VELDO-0127/live.py
  - scripts/suites/103_veldo_0211_borrowed_login.py
  - scripts/suites/102_veldo_0210_agent_profile_runtime.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0211-borrowed-login-writeback.md
  - specs/index.md
  - proof/VELDO-0211/*
behavior_bearing: true
observability:
  logs: Credential paths and failure categories on stderr, never credential values.
  metrics: Engine exit status on successful write-back; refusal or recovery error otherwise.
  traces: Offline fake-engine evidence only; no production credentials in proof.
  error_taxonomy: Busy login, unavailable write-back, invalid credentials, and recovery required.
acceptance_criteria:
  - id: AC1
    text: >
      Both borrowed-login callers, the live capture and sandbox launcher, lock each resolved
      credential source before copying and retain the lock until the engine has stopped and
      write-back finishes. The source receives an atomic engine rotation on success, exception,
      nonzero exit and handled termination. Repository searches enumerate the borrowers;
      suite 103 drives both integrations with fake engines and suite 102 covers launcher teardown.
    falsified_by: Disable write_back; the fake engine rotation row must fail.
  - id: AC2
    text: >
      A busy source or source that cannot be atomically replaced refuses before engine execution.
      Locks use the existing sibling credential lock, including canonical source aliases.
      Suite 103 checks contention and denied replacement and proves no engine marker was written.
    falsified_by: Remove the preflight replacement; the refused-before-launch row must fail.
  - id: AC3
    text: >
      Write-back retains private permissions, rejects a rotated JSON object that drops an existing
      refresh token, and never silently discards valid rotated credentials on an unexpected late
      storage failure. Recovery data remains private and the caller reports failure. Suite 103
      exercises late replacement failure and missing refresh tokens, while suite 102 retains
      coverage of unsafe scratch links and a separate login superseding the borrowed source.
    falsified_by: Suppress the write-back storage error; the recovery row must fail.
required_evidence: [unit]
rollback: Revert the implementation commits and stop borrowed-login runs until fixed.
---

## Intent

A production Claude login reportedly lost refreshability after two live captures on 2026-10-09.
A temporary credential symlink is replaced by an engine's atomic save, leaving the original
refresh token stale. The sandbox copies credentials and writes back, but its old lock covers
only compare and rename, allowing overlapping borrowers and no start-time write-back check.

## What the reviewer judges

Normal use: local file-backed Claude and Codex logins borrowed by these two tools. Both callers
share the same lock convention. Direct engine use of the original profile does not honor Veldo's
lock and must not run concurrently; a separate login replacing the source is preserved.

Threat model: accidental refresh loss, cooperating concurrent Veldo borrowers, and ordinary
permission failures. Existing sandbox confinement and scratch link defenses remain intact.
Out of review scope: hostile owner processes, uncatchable termination, hardware failure, or
permissions revoked after launch. Late storage failures cannot promise persistence to an
unwritable source: they must fail loudly and retain private recovery data instead of deleting it.

## Verification boundary

Only suites 103 and 102 are run, sequentially through the selftest suite selector. No whole gate,
mutation runner, production engine, production login, push, merge or independent approval is
performed by this implementation run. The reviewer owns the complete gate and landing approval.
