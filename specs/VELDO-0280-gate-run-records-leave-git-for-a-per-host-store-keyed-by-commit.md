---
schema: veldo.spec/v1
id: VELDO-0280
title: Gate run records (the verify stamp, gate events and reconciled verdict events) leave git for a per-host store keyed by commit, while proof bundles and emergency records stay committed
status: draft
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0268, VELDO-0271]
placement: [enforcement]
protected_paths: ["scripts/verify.sh", "engine/scripts/verify.sh", "scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", ".veldo/policy_check.py", "engine/.veldo/policy_check.py", ".veldo/control_verification.py", "engine/.veldo/control_verification.py", "scripts/run_scope.py"]
footprint:
  - "scripts/verify.sh"
  - "engine/scripts/verify.sh"
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - ".veldo/*.py"
  - "engine/.veldo/**"
  - "scripts/*.py"
  - "bin/veldo"
  - ".veldo/events.jsonl"
  - ".veldo/last_verify"
  - ".gitignore"
  - "scripts/suites/**"
  - "specs/VELDO-0280-gate-run-records-leave-git-for-a-per-host-store-keyed-by-commit.md"
  - "specs/index.md"
  - "proof/VELDO-0280/**"
behavior_bearing: true
observability:
  logs: >
    The gate's last line names the store path it wrote the stamp to. The guard, on a refusal, names the
    store path it looked in and the commit.
  metrics: >
    Metrics, dashboard and budget readers read gate events from the store; their outputs are unchanged.
  traces: >
    None added.
  error_taxonomy: >
    No new names. The guard's "gate is not green for HEAD" refusal now also covers "no stamp for this
    commit in the store". The evidence-only parent allowance is removed, since recording a gate no longer
    makes a commit.
acceptance_criteria:
  - id: AC1
    text: >
      Every gate writes its stamp and its gate event to the per-host store, never to the tree: one file per
      commit, <state>/gates/<repository id>/<commit>.json, holding the stamp, and an append-only events log
      beside it, under the authority's state directory where VELDO-0267's nightly records live. The
      existing candidate-mode sink rules apply to it (no symlinks, rename into place, any write failure is
      red). The verdict reconciliation appends to that log. .veldo/last_verify and the gate and verdict
      lines of .veldo/events.jsonl stop being written; last_verify is untracked and ignored; emergency.push
      and emergency.closed lines stay in the tracked .veldo/events.jsonl, which only the guard writes.
    falsified_by: >
      A fixture gate run leaves git status clean and writes <commit>.json in a fixture state root.
      Registered mutations from a green baseline: (1) verify.sh still appends the gate event to the tree:
      the clean-status row goes red; (2) the store follows a planted symlink: the symlink row goes red.
  - id: AC2
    text: >
      Every reader of gate records reads the store by commit: the push guard and policy_check for landing,
      control_verification.py, lander.py, run_scope.py, bin/veldo status, and the metrics, dashboard, budget
      and verdict corpus readers, found by a scan for last_verify and gate event types. The guard requires
      a green stamp for exactly the pushed commit; the evidence-only parent allowance goes, because no
      commit is made to record a gate. A stamp found only in the tree is ignored.
    falsified_by: >
      The guard over a fixture repository refuses a push whose commit has no stamp in the store and passes
      after a green stamp for that commit is written; a green stamp for the parent commit does not pass.
      Registered mutations: (1) the guard keeps reading .veldo/last_verify: the store row, with a green
      tree stamp and none in the store, goes red; (2) the parent allowance is kept: the parent row goes red.
  - id: AC3
    text: >
      Proof bundles stay the committed evidence. A proof manifest for the commit is still required at
      landing (the guard's second check, unchanged), and the stamp a landing relied on is copied into the
      landing's proof bundle by the lander, so the evidence that a gate was green travels with the code
      while per-run records do not. The existing tracked gate lines of .veldo/events.jsonl are moved once
      into this host's store by a one-time command the proof runs, and removed from the tracked file.
    falsified_by: >
      A fixture landing ends with the stamp in proof/<spec>/ equal to the store's file for the landed
      commit. Registered mutation: the lander skips the copy: the proof row goes red. The one-time command
      over a fixture log moves every gate and verdict line and keeps every emergency line.
required_evidence: [unit, integration]
rollback: >
  Revert the commit; gates write to the tree again. Records in the store stay readable by nothing; the
  moved history is in git.
---

## Intent

Weight audit decision H, Veldo part: stop rewriting tracked files on every gate run, and stop the
practice of copying a green stamp out of a worktree before any checkout. Proof bundles stay the evidence.

## Context

Verified on main at afa292f0: .veldo/events.jsonl and .veldo/last_verify are both tracked; 223 commits
touch events.jsonl and 213 touch last_verify. The log holds 1,395 lines: 1,012 gate.passed, 189
gate.failed and 194 verdict.recorded (written by the gate's verdict reconciliation, events.py
reconcile-verdicts). It holds no emergency lines today, but the guard appends emergency.push to it and
policy_check reads emergency debt from it, so those stay tracked. verify.sh already has a candidate mode
that writes the stamp and events to a sink outside the candidate (--candidate, --sink); this spec makes a
per-host store keyed by commit the only destination.

Owner approval: not required. The landing check keeps its meaning (a green gate for exactly this commit);
only where the record lives changes, under the same single-user model in which the tracked file was
already writable by the same account. Lands after VELDO-0268 and VELDO-0271, which change the guard,
policy_check and verify.sh.

## Out of scope

Core's records (the audit's core half); proof bundle format; emergency lane semantics.

## What the reviewer judges

- Normal use: gates, pushes and landings on this host.
- No path lets a push pass without a green stamp for its exact commit; no gate writes to the tree.
- Out of review scope: per the template; a second host landing the same commit gates it there.

## History

2026-11-07: drafted by the lead from the weight audit's decision H (Telegram 39708, 39710). A draft.
