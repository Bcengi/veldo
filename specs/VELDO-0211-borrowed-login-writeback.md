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
  - scripts/suites/104_veldo_0210_mutation_workers.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/VELDO-0211-borrowed-login-writeback.md
  - specs/VELDO-0210-agent-profile-runtime.md
  - specs/index.md
  - proof/VELDO-0211/*
behavior_bearing: true
observability:
  logs: Credential paths, lease paths and failure categories on stderr, never credential values.
  metrics: Engine exit status on success; refusal (2) or credential recovery (74) otherwise.
  traces: Offline fake-engine evidence only; no production credentials in proof.
  error_taxonomy: Busy login, login without a lease, unavailable write-back, invalid credentials, recovery required.
acceptance_criteria:
  - id: AC1
    text: >
      Both borrowed-login callers, the live capture and the sandbox launcher, hold each login's
      runner lease (<login dir>/.runner-lease, the flock the runners' account_lease.sh takes)
      from before copying a credential until every engine has stopped and write-back finished.
      The launcher accepts the lease its runner holds and passes on (an inherited descriptor),
      otherwise takes it itself, never waiting and never creating the file. A live capture killed
      outright leaves a guard that stops the factory slice, then writes back, then releases the
      lease. The source receives an atomic engine rotation on success, exception, nonzero exit
      and handled termination. Suite 103 drives both integrations with fake engines and the
      guard with a killed capture; suite 102 covers launcher teardown.
    falsified_by: Skip settle_borrow; the fake engine rotation row must fail.
  - id: AC2
    text: >
      A login another run holds, a login without a lease file, or a source that cannot be
      atomically replaced refuses before engine execution. Replaceability is probed with a
      sibling temporary file: the credential itself is never rewritten at the start. A second
      borrow of a login in the same process, including through a canonical alias, is busy.
      Suite 103 checks contention, a missing lease, denied replacement and the untouched
      credential, and proves no engine marker was written.
    falsified_by: Skip the replacement probe; the refused-before-launch preflight row must fail.
  - id: AC3
    text: >
      Write-back retains private permissions, rejects a rotated JSON object that drops an existing
      refresh token, and treats invalid or unreadable copies and late storage failures as a
      credential recovery: the copies are kept privately on persistent storage
      ($XDG_STATE_HOME/veldo/borrowed-logins), the launcher exits 74 (never the refusal status)
      with a message naming the run's own exit status and the restore command, and the scratch is
      kept when even the recovery cannot be written. A run killed outright is recovered by the
      next start's sweep, which never deletes a rotated copy silently. restore-login restores a
      recovery under the lease and refuses a source that changed since the run unless forced.
      Suites 103 and 102 exercise each path.
    falsified_by: Drop the failures in settle_borrow; the recovery row must fail.
required_evidence: [unit]
rollback: Revert the implementation commits and stop borrowed-login runs until fixed.
---

## Intent

A production Claude login reportedly lost refreshability after two live captures on 2026-10-09.
A temporary credential symlink is replaced by an engine's atomic save, leaving the original
refresh token stale. The sandbox copies credentials and writes back, but its old lock covered
only compare and rename, allowing overlapping borrowers and no start-time write-back check.

## One lease per login

Every user of a file-backed login takes the same lock: flock on <login dir>/.runner-lease. The
runners (account_lease.sh, sourced by claude_work.sh, codex_work.sh, codex_review.sh and
claude_accounts.sh) take it before their launcher starts and hold it through the run, the
unconfined fallback path included; the launcher inherits that descriptor and checks it holds the
lease rather than taking a second, different lock. live.py takes the same lease through the
launcher's take_lease. The login directory is the canonical directory the credential is named in,
and the directory its file really lies in when that differs. A launcher started without a runner
takes the lease itself, never waiting; neither caller creates the file, so a borrow leaves nothing
in the login (the runners create it the first time they use a login). The earlier sibling
<source>.veldo-lock of VELDO-0210 is gone. A Claude or Codex CLI started directly on the login,
outside every runner, still takes no part in this lock and must not run concurrently.

## Credential recovery and how to restore it

A rotation that cannot be written back is kept, never discarded. Each borrow first records a
journal at $XDG_STATE_HOME/veldo/borrowed-logins/<scratch name>/borrow.json (default
~/.local/state; private, outside every login, scratch and tree, and denied to the confined run):
the sources and the digests of what was copied in. At the end, under the lease, the journal is
dropped after a successful write-back, or becomes a recovery: the copies in private files beside a
recovery.json naming each source, the digest it held at the start and the reason. The launcher
then exits 74 with "CREDENTIAL RECOVERY REQUIRED", the run's own exit status and the restore
command; live.py exits 74 with the same message. Should even the recovery store fail, the scratch
is kept as it is and its journal stays, so the next start recovers it.

A launcher killed outright (a runner's SIGKILL after its stop grace) leaves its journal. Every
launcher and live capture start first turns each journal whose scratch no process holds into a
recovery when a copy differs from what was copied in, and reports it, or drops it when nothing
changed; the stale-scratch sweep never removes a scratch whose journal is not settled.

To restore:

1. List what is waiting: python3 scripts/agent_sandbox.py restore-login
2. Stop every run on that login (a runner holding its lease makes the restore refuse as busy).
3. Restore: python3 scripts/agent_sandbox.py restore-login <recovery directory>. Under the lease,
   each kept copy replaces its source atomically, mode kept, when the source still holds the bytes
   it held at the start, the copy is one JSON object and no refresh token is lost; the recovery is
   then removed. If the account was logged in again meanwhile, the restore refuses and leaves the
   source alone; its force option replaces it anyway, which is only right when the new login is
   not wanted.
4. A recovery whose entries kept nothing (an unreadable copy) only records what happened:
   restore-login prints each entry and removes it; log the account in again.

## Starting tree and stops

A stop that lands while the tree is starting is recorded and the launcher kills the tree; it is no
longer forwarded first. The forwarded TERM raced the kill and could reach a command that had
already started (suite 102 scratch/stop-during-fork-forwarded-to-child failed intermittently, on
main rarely and on the first VELDO-0211 implementation often). Stops after the start are
forwarded as before.

## What the reviewer judges

Normal use: local file-backed Claude and Codex logins borrowed by these two tools and the
runners. Threat model: accidental refresh loss, cooperating concurrent borrowers, killed runs and
ordinary permission failures. Existing sandbox confinement and scratch link defenses remain
intact. Out of review scope: hostile owner processes, a direct CLI run on a leased login, a reboot
during a live capture (its copies live in the runtime directory), hardware failure, or
permissions revoked after launch. A confined agent can still force a recovery by corrupting or
deleting its copy (the source is left alone, the run ends with 74).

## Verification record

Run on the host, foreground, with python3 scripts/selftest.py: suites 102, 103 and 104, plus
proof/VELDO-0211/falsify.py, which mutates the sources one at a time and requires suite 103 to
fail the named row. The myday runner changes (a preflight or run ending in recovery exits 74 and
never falls back) are proved by that repository's scripts/test_runner_sandbox_dry.sh against this
checkout. The full gate, push, merge and independent approval are not part of this run.

Suite 102 previously invoked the mutation coordinator. Its unchanged mutation worker checks
moved to suite 104, still registered in the full gate.
