---
schema: veldo.spec/v1
id: WARP-0503
title: veldo status --json and veldo watch - project git, events, and the run registry into a read model
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0005
work: R3
plan_revision: 1
human_approval: not_required
protected_paths: []
required_evidence: [unit]
acceptance_criteria:
  - id: AC1
    text: A status(root, runs_root) function assembles one read model with a repo
      section (the current HEAD and branch read from git), a plan burn-down section,
      the live runs, a tail of recent durable events, and the recent verdicts. runs_root
      and the events path are overridable so the reader can be driven over a temporary
      runs root and a synthetic events file with no live build.
  - id: AC2
    text: Each live run in the model carries its classification (active, blocked, stale,
      or done via the R1 registry classify), the current loop phase, the blocked question,
      the heartbeat age, and a blocked-elapsed value shown as a SEPARATE field from
      human_minutes so a blocked wait is never folded into attention time (constraint C3).
  - id: AC3
    text: The plan burn-down is REUSED from .veldo/plan.py (its per-item state and frontier,
      derived from spec status) rather than reimplemented, so the reader reports the same
      truth the specs index does.
  - id: AC4
    text: Tokens are shown only when the run or live data actually carries them and are
      reported as "unknown" when absent, never 0 and never an estimate (constraint C3).
      The reader is a read-only projection: it writes nothing to the registry, the event
      stream, or the repo.
  - id: AC5
    text: A CLI exposes the model - veldo status --json prints it as JSON and veldo status
      prints a compact terminal view, and veldo watch renders the same compact view (a
      single render, or an interruptible refresh loop that is not gate-tested live).
  - id: AC6
    text: A selftest builds synthetic runs in a temporary runs root (an active one, a
      blocked one carrying a question, a stale one, a done one) plus a synthetic events
      tail, calls status(), and asserts each run is listed with the correct classification,
      the blocked question is surfaced, blocked-elapsed is separate from human_minutes,
      tokens are unknown when absent, and the repo and burn-down sections are present; it
      is non-tautological - a mutation that drops a run or misreports a classification
      makes an assertion fail, and a read-only-after-read assertion proves it writes nothing.
rollback: git revert; additive - a new .veldo/runstatus.py, a status_reader entry added to
  both capabilities.yaml copies, a selftest block, the spec, and the regenerated index; no
  protected path is touched and the reader writes nothing at runtime.
---

## Intent

Give a human (or the chat surface) one place to see the live state of VELDO builds without
reading the repo or CLI internals. Project three sources that already exist - git, the
durable event stream, and the R1 run registry - into a single read model, and classify each
run active, blocked, stale, or done. This is the first read surface over the substrate R1
stood up; the local browser view (R4) and the chat wiring (R6) read the same model.

## Context

The registry (WARP-0501) is the live substrate and already classifies a run from its state
and heartbeat. The event stream (WARP-0108) and the plan burn-down (plan.py, feeding the
specs index) are the durable substrate. This item adds no store of its own: it is a pure
reader that assembles the model on demand. Blocked-elapsed is kept separate from
human_minutes and tokens stay "unknown" unless supplied, honoring plan constraint C3.

## Notes

The burn-down is reused from plan.py, not reimplemented, so there is one source of that
truth. The reader takes a runs_root and an events-path override so its control logic is
gate-tested over synthetic runs and a synthetic events file with no live agent or backend,
and the selftest asserts read-only behavior (the runs root and events file are byte-identical
after the read) alongside the classification and burn-down assertions. The refresh loop of
veldo watch is interruptible and deliberately not driven live in the gate.
