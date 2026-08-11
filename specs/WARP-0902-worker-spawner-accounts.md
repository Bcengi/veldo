---
schema: veldo.spec/v1
id: WARP-0902
title: In-session worker spawner and the account model - fill the fleet spawn seam and select which account runs each worker
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W2
plan_revision: 1
depends_on: [WARP-0901]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: An account model (.veldo/accounts.py) persists a named account as its own config profile
      and resolves it by name. account_add(name) records an account whose credentials live in its
      own CLAUDE_CONFIG_DIR profile directory (the one-time login into that directory is a documented
      human step; account_add creates and registers the profile, it does not fabricate a login);
      resolve(name) returns that account's CLAUDE_CONFIG_DIR; list_accounts() enumerates them. The
      registry persists across invocations (a file under the git common dir, outside git history,
      shared across worktrees, like the claim ledger), so a registered account is reused with NO
      relogin. A duplicate add and an unknown resolve each fail by name, not silently.
  - id: AC2
    text: The CLAUDE_CONFIG_DIR-per-account model is VERIFIED against real Claude Code behavior (via
      the claude-code-guide surface or the current docs) - that pointing CLAUDE_CONFIG_DIR at a
      directory isolates that account's persisted credentials so a session started with it reuses the
      saved auth without a login prompt - and the account model is implemented to match what is
      verified (the env var name and semantics are grounded, not assumed). The verified behavior is
      recorded in the proof.
  - id: AC3
    text: The fleet WorkerSpawner seam (fleet.py) is filled by a REAL in-session spawner that
      assembles each worker's environment - its account's CLAUDE_CONFIG_DIR, a worker id, the scope,
      and capabilities - tracks the handle, and retires it. It NEVER spawns a detached or rogue
      process: the actual start of a worker is an INJECTED spawn primitive (a fake in the gate; the
      real primitive is the in-session mechanism or the documented one-session-per-account procedure),
      and the reference primitive FAILS LOUD rather than fabricate or detach. This is consistent with
      feedback_no_rogue_processes and PLAN-0007 NG1 (a worker is a vanilla in-session session).
  - id: AC4
    text: Account selection threads through the launcher - a worker is pinned to a chosen account
      (veldo work/fleet --account NAME) or the pool is spread across the registered accounts, so
      multi-account is N concurrent one-account workers that self-divide the one frontier through the
      claim ledger, each worker carrying its account's CLAUDE_CONFIG_DIR. One account is never run as
      two workers at once by the spreader (one account per worker).
  - id: AC5
    text: Gate-tested via the selftest over a throwaway environment with fakes and NO real login and
      NO detached process - account add/resolve/list and cross-invocation persistence (duplicate and
      unknown fail by name); the spawner assembles the right env (the account's CLAUDE_CONFIG_DIR
      threaded to the worker), reconciles up/down, and retires over a FAKE spawn primitive; the
      account spreader gives one account per worker. Non-tautological teeth: a spawner that ignores
      the selected account (wrong or missing CLAUDE_CONFIG_DIR), or a reference primitive that
      fabricates instead of failing loud, turns an assertion red.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/accounts.py (repo-root dogfood machinery, NOT shipped
  engine, not copied into packs), the WorkerSpawner seam filled in fleet.py, a selftest block, and
  this spec. No protected path; pure stdlib; no login is performed and no process is spawned in the
  gate; the real spawn primitive stays injected and fail-loud, never a detached process.
---

## Intent

W2 makes two things real on top of W1's dispatcher: the fleet can be told WHICH account runs each
worker, and the launcher's spawn seam is filled by a real in-session spawner. The account model lets
a founder register several accounts once (each logged in to its own persisted profile) and then run
as many concurrent workers as accounts, one account per worker, with no relogin - the multi-account
capability the founder asked for. The spawner assembles each worker's environment (its account's
CLAUDE_CONFIG_DIR, id, scope) and reconciles the pool, but never spawns a detached process: the
actual worker start is an injected in-session primitive, and the reference fails loud.

## Context

W2 of PLAN-0009, depends on W1 (a worker's dispatch is now real). The launcher already reconciles the
pool over the WorkerSpawner seam (fleet.py FleetLauncher.reconcile spawns up and retires down); the
seam's reference raises NotImplementedError. W2 fills it with a real in-session spawner and adds the
account model the spawner threads. The whole fleet is repo-root dogfood machinery (.veldo/), not the
shipped engine (that is W5); the veldo CLI front door that exposes veldo account add / veldo work
--account is W4, so W2 provides the account model as functions plus a thin account subcommand the CLI
will dispatch to. Per-account pacing (the governor tracking each account's own budget) and the
in-session resume-waiter are W3.

## The no-rogue-processes boundary (load-bearing)

A worker is a vanilla in-session Claude Code session; the fleet NEVER spawns a detached or headless
process (feedback_no_rogue_processes, PLAN-0007 NG1). So the WorkerSpawner does the real mechanical
work - assemble the worker env (account CLAUDE_CONFIG_DIR, id, scope, caps), track handles, retire -
over an INJECTED spawn primitive. The gate uses a fake primitive; the reference primitive fails loud
rather than fabricate or detach; the actual spawn is the in-session sub-agent mechanism (same
machine, same account) or the documented one-session-per-account procedure (across accounts). This
module auto-spawns nothing detached. Hands-free auto-relaunch after full exhaustion is a separate,
opt-in, human-gated decision (W7 / open decision D1), not part of W2.

## Out of scope

The veldo CLI front door (W4), per-account governor pacing and the resume-waiter (W3), shipping the
fleet into the engine (W5), and the opt-in external supervisor for auto-relaunch after full account
exhaustion (W7, gated on D1). No real login is performed by code; account_add prepares and registers
the profile and the human logs in once into it (a documented step).

## Notes

Two commits, the standard shape: an impl commit carrying its own independent review and commit-bound
verdict, then an evidence-only commit (proof/, .veldo/, specs/) inheriting the impl verdict via the
guard's parent rule.

RULE #1: the VELDO gate's docs dash-sweep catches only em/en dashes, not the ASCII double-hyphen; every
new file and comment must be hand-checked so no `--` double-hyphen appears in code or prose (a `---`
YAML delimiter and a markdown table separator are fine). Match the existing fleet module comment style
(plain `# comment` lines, no double-hyphen divider runs). The account registry is persisted under the
git common dir like the claim ledger, outside git history, so it is machine-local and not committed.
