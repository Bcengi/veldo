---
schema: veldo.spec/v1
id: WARP-0904
title: The veldo CLI - a real executable front door for work, fleet, status, and account
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0009
work: W4
plan_revision: 1
depends_on: [WARP-0901, WARP-0902, WARP-0903]
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A real veldo executable (a stdlib script with a shebang, e.g. bin/veldo) is the single front
      door and dispatches subcommands to the EXISTING modules with no new control logic - work, fleet,
      status, watch, account (add/list), and the already-built answer/steer/abort. It parses arguments
      and calls the modules; it does not reimplement the loop, the launcher, the governor, the reader,
      or the registry. An unknown subcommand or bad arguments fail loud (nonzero exit, an honest
      message), never a silent no-op.
  - id: AC2
    text: The read/registry subcommands are wired to the existing modules and run standalone with no
      agent: veldo status / veldo watch to runstatus.py, veldo account add / veldo account list to
      accounts.py, veldo answer / veldo steer / veldo abort to runcmd.py. Each produces the same behavior
      as calling that module directly (the CLI is a router, proven by routing a representative call of
      each to its module).
  - id: AC3
    text: veldo work [--account NAME] assembles the real single-worker loop (frontier + claim + the W1
      dispatcher) and veldo fleet N [--account NAME] assembles the elastic launcher (fleet.py launcher +
      the W2 in-session spawner + the W3 per-account governor and in-session waiter), honoring account
      selection through the W2 account model (--account resolves that account's CLAUDE_CONFIG_DIR; the
      fleet is capped at account capacity). The intelligent build/review and the worker-spawn primitive
      remain DELEGATED seams that FAIL LOUD without an agent or a real spawn wired (no fabrication);
      the CLI NEVER spawns a detached or rogue process (feedback_no_rogue_processes, PLAN-0007 NG1). An
      unknown --account fails by name; the CLI catches the AccountError BASE (fleet.py double-loads
      accounts.py, so a separately-imported accounts error class would not match).
  - id: AC4
    text: The CLI adds NO new control logic - it is only argument parsing plus calls into the existing
      W1-W3 modules and the runstatus/runcmd/accounts CLIs. The deep behavior (claim, dispatch,
      reconcile, pace, wait, read) stays in those modules; a review can diff the CLI and see only
      routing and wiring, no reimplemented mechanics.
  - id: AC5
    text: Gate-tested via the selftest with NO live agent, NO detached process, and NO real fleet run -
      argument routing (each subcommand reaches the right module; an unknown subcommand and bad
      arguments fail loud with a nonzero exit), the read/registry subcommands routed to their modules,
      and honest failure (an unknown --account fails by name; veldo work / veldo fleet without an agent
      or a spawn primitive wired fail loud rather than fabricate a build/verdict or spawn anything).
      Non-tautological teeth: a dispatcher that swallows an unknown subcommand (exit 0), or that
      fabricates a build/spawn instead of failing loud, turns an assertion red.
required_evidence: [unit]
rollback: git revert; additive - a new veldo executable (bin/veldo) plus its thin wiring, a selftest
  block, and this spec, all repo-root dogfood (NOT shipped engine; W5 moves the CLI + fleet into
  engine and /veldo:init). No protected path; pure stdlib; the CLI reimplements nothing, runs
  no agent and spawns no process in the gate, and never launches a detached process.
---

## Intent

The fleet's commands - veldo fleet N, veldo work, veldo status, veldo account - are README syntax today
with nothing behind them. W4 makes them real by adding one veldo executable that dispatches to the
modules W1 through W3 (and the already-built status reader and run inbox). It is the front door only:
no new mechanics, just parsing and wiring, so a founder can actually type veldo fleet 3 --account work
and get the real launcher.

## Context

W4 of PLAN-0009, depends on W1 (the dispatcher), W2 (the spawner + account model), and W3 (the
per-account governor + in-session waiter). The modules already expose their surfaces: runcmd.py has an
argparse CLI with prog veldo for answer/steer/abort, runstatus.py has status/watch, accounts.py has
account add/list (W2). What is missing is a single veldo executable that unifies them and adds work and
fleet. W4 adds that executable and wires work/fleet to the real loop and launcher; the whole thing
stays repo-root dogfood (the veldo script plus .veldo/), not the shipped engine - W5 moves the CLI and
the fleet modules into engine and /veldo:init.

## The no-rogue-processes boundary

veldo work and veldo fleet assemble the real machinery but the intelligent build/review and the
worker-spawn primitive stay delegated seams (the LiveLoop / reviewer / in_session spawn references
fail loud rather than fabricate or detach). The CLI itself spawns nothing detached; run bare with no
agent wired, veldo work and veldo fleet fail loud, which is the honest behavior (they are the entry
points an in-session agent drives). Hands-free relaunch after full exhaustion stays W7 / open decision
D1.

## Out of scope

Shipping the CLI and the fleet into the engine and /veldo:init (W5), the opt-in external supervisor
(W7 / D1). No new loop/launcher/governor/reader logic - the CLI reimplements nothing.

## Notes

Two commits, the standard shape: an impl commit with its own independent review and commit-bound
verdict, then an evidence-only commit (proof/, .veldo/, specs/) inheriting the impl verdict via the
guard's parent rule.

CARRY-FORWARD from W2: fleet.py double-loads accounts.py under a private module name, so its
AccountError classes are distinct objects from a separately-imported accounts module. The CLI must
catch the AccountError base (or the exact module instance fleet.py exposes), not a freshly-imported
accounts.UnknownAccountError, or the except clause will not match. RULE #1: the gate's dash-sweep
catches only em/en dashes, not the ASCII double-hyphen; hand-check that no `--` appears in new code or
prose (a genuine `--flag`/`--account` CLI option, a `---` YAML delimiter, and the `# ---` selftest
block header are fine). The gate must run no agent, spawn no process, and never launch a real fleet.
