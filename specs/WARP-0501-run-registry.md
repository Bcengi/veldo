---
schema: veldo.spec/v1
id: WARP-0501
title: Run registry and run-progress events - the live substrate for the Run Lens
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0005
work: R1
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: A run folder lives under the git common dir at veldo/runs/<run-id>/ so it is
      shared across worktrees and outside git history. The registry resolves that
      path from git and accepts an override for testing, and creating a run writes a
      meta.json (run id, spec id, started at, pid, head) and an initial state.json.
  - id: AC2
    text: state.json is updated by atomic write (temp file plus rename) so a reader
      never sees a half-written state; live progress is appended to live.jsonl with a
      monotonic sequence number so a reader can detect gaps and resume.
  - id: AC3
    text: The registry records the loop phase, a heartbeat timestamp, and a blocked
      question, and classifies a run as active, blocked, stale, or done from its
      status and heartbeat age. A stale run (heartbeat older than the threshold) is
      never reported as blocked unless it explicitly recorded a blocker.
  - id: AC4
    text: The durable run milestones (run.started, run.blocked, run.resumed, run.done,
      run.aborted) are added to the event vocabulary and can be emitted to the tracked
      event stream; the high-volume progress (per-step and heartbeat) stays in the
      run folder live.jsonl only and is never written to the committed event stream.
  - id: AC5
    text: A selftest drives the registry over a temporary run root - create, atomic
      state update, sequenced live append, heartbeat, block, resume, finish, list, and
      classify (active, blocked, stale, done) - and is non-tautological: a mutation
      that drops the atomic rename or misclassifies a stale run makes an assertion fail.
required_evidence: [unit]
rollback: git revert; additive - a new .veldo/runlog.py, five run.* entries added to
  the events vocabulary in both events.py copies, a selftest block, the spec, and the
  PLAN-0005 plan file; no protected path; the run folder is outside git history.
---

## Intent

Stand up the substrate every Run Lens surface reads: a per-run folder that a running
build writes its live state into, plus the run lifecycle event vocabulary. This is
the foundation for veldo run (R2), the readers (R3, R4), and interaction (R5, R6).

## Context

Live run state must not be committed (per-step and heartbeat volume would spam git
history), so it lives under the git common dir, shared across worktrees, outside the
working tree. Durable milestones still enter the tracked event stream beside the
existing loop events. The executor (WARP-0401) will produce these in R2; this item
is the storage and vocabulary only.

## Notes

state.json uses atomic temp-plus-rename; live.jsonl is append-only with a sequence
number; classification uses is-none and explicit-blocker rules so an absent heartbeat
is stale, not silently blocked. The registry module lives in .veldo/ (like the other
feature modules); only the five durable milestone types are added to the events
vocabulary, keeping the committed stream clean of high-volume progress.
