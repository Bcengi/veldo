---
schema: veldo.spec/v1
id: WARP-1010
title: Real in-session worker spawner - fill the fleet spawn seam in-session, never detached
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      The fleet WorkerSpawner start seam (today .veldo/fleet.py in_session_start, a
      fail-loud reference) is filled by a REAL in-session spawn: given a worker's
      assembled env (its account CLAUDE_CONFIG_DIR, worker id, scope, capabilities), it
      starts an IN-SESSION worker - a git-worktree-isolated worker the coordinator drives
      through the same in-session parallel mechanism a human session already uses - and
      returns an opaque handle the launcher hands back to retire. A worker dies with the
      session.
  - id: AC2
    text: >
      It NEVER spawns a detached, headless, or background process. No claude -p run in
      the background, no nohup, no setsid/fork-and-detach, no systemd unit, no daemon, no
      crontab. The spawn path imports and uses no process-spawning primitive at all for
      the worker (any git-worktree provisioning is a plain in-line git call, not a
      detached process). This is the hard boundary (feedback_no_rogue_processes,
      PLAN-0007 NG1); the module honored it as a fail-loud reference before and must honor
      it now that it is filled.
  - id: AC3
    text: >
      The no-detach boundary has TEETH: a selftest asserts the spawn path spawns no
      detached/background process (it uses no subprocess/Popen/os.fork/os.exec/os.spawn/
      nohup/setsid for the worker, or drives them only through an injected seam a fake
      controls), and a mutation that introduces a detached spawn (or a background claude
      -p) FAILS the gate - the same posture as the supervisor's spawn-on-install teeth
      (WARP-0907). The launcher control logic (elastic scaling, one-account-per-worker via
      AccountSpreader, retire releasing the account) stays gate-tested via the fake
      spawner; the live in-session start is a REFERENCE path not run in the gate.
  - id: AC4
    text: >
      Where no in-session spawn mechanism is available (a harness without one, or a
      misconfigured caller), the primitive FAILS LOUD by name rather than fabricating a
      handle or falling back to a detached process, preserving the existing honest
      posture. The coordinator drive is documented: a fleet run procedure states that
      workers are in-session, worktree-isolated, opt-in, and die with the session, and
      that the multi-account path stays one account per worker (never one account run as
      two workers).
  - id: AC5
    text: >
      capabilities.yaml is updated honestly (the worker_spawner control logic mechanical;
      the in-session start a reference live edge, not gate-run) in both byte-identical
      copies; every edited ENGINE_GLOBS file is re-synced byte-identical across
      engine and all seven packs (template-sync and pack-drift pass). The full
      gate is GREEN, RULE #1 is clean, no protected path is touched, and the change lands
      in the canonical two-commit shape.
required_evidence: [operational]
rollback: >
  Revert the commit. The change fills a seam whose reference was fail-loud and adds no
  gate-run behavior (the live spawn is reference, off the gate); reverting returns
  in_session_start to its fail-loud reference and the documented one-session-per-account
  procedure, with no migration and nothing running to unwind.
---

## Intent

This closes the last open fleet seam. Today the WorkerSpawner start primitive
(in_session_start) fails loud on purpose, and multi-account scaling is a human opening
one session per account by hand. Filling it lets the coordinator scale the pool ITSELF,
in-session, without a human opening terminals - but strictly through the in-session,
worktree-isolated worker mechanism, never a detached or background process. The value is
"the coordinator grows and shrinks the fleet"; the hard constraint is "a worker is a
vanilla in-session session that dies with the coordinator, never a rogue process."

## Context

- The seam and control logic already exist and are gate-tested with a fake: FleetLauncher
  (reconcile/run), InSessionSpawner, AccountSpreader (one account per worker), InSessionWaiter
  in .veldo/fleet.py. Only the start primitive is unfilled (in_session_start fails loud).
- A worker is a git-worktree-isolated in-session worker (the same parallel mechanism a
  human uses, e.g. the WARP-0406 ephemeral env + a worktree per worker), driven by the
  coordinator to claim frontier units for its account and land them. The account is
  threaded via CLAUDE_CONFIG_DIR so the worker reuses that account's saved login.
- The live spawn on a given harness is a REFERENCE (like the live tracker adapters and the
  supervisor's session launch): not gate-run, agent-mediated at runtime; the fail-loud
  default stays for contexts without an in-session mechanism.
- HARD RULE, non-negotiable: never detached/headless/background. If the correct in-session
  fill is genuinely agent-mediated (the coordinator dispatches the in-session worker) rather
  than a pure-Python spawn, ship it as the seam + reference + documented procedure, still
  gate-tested via the fake, rather than reaching for a detached process to make it "real".

## Out of scope

- No detached/background workers of any kind. No auto-relaunch after a killed session (that
  is the opt-in external supervisor WARP-0907, already shipped). No live tracker enablement.
- No rewrite of the launcher/governor/waiter control logic (shipped, kept).

## Notes

- Keep the control logic gate-tested via the fake spawner; the live in-session start is a
  reference path. Put teeth on the no-detach boundary so a future change cannot slip a
  detached spawn past the gate. Fail loud, never fabricate a handle, never detach.
- Follow the byte-identical engine sync discipline and re-run the drift checks before proof.
  Today is 2026-07-21; regenerating specs/index.md restamps its date header.
