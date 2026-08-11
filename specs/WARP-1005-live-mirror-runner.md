---
schema: veldo.spec/v1
id: WARP-1005
title: The live mirror runner - apply the one-way mirror to a real tracker, opt-in and non-LLM
status: shipped
risk: standard
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0010
work: W5
plan_revision: 1
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A non-LLM mirror RUNNER applies the one-way mirror to a tracker: given the VELDO
      event stream (.veldo/events.jsonl) and an injected adapter, it drives the shipped
      spec mirror and plan mirror (mirror_events / mirror_plan_events) to project the
      current status, comments, artifact links, and the ready-to-test reassignment onto
      the tracker. It is a RECONCILER (recompute the desired state from the stream each
      run and apply it), idempotent under replay with no processed-offset ledger and no
      second store, and it writes only to the tracker, never a spec or plan definition.
  - id: AC2
    text: >
      The runner is OPT-IN and OFF BY DEFAULT. It is an explicit entrypoint the operator
      invokes (a veldo CLI subcommand over the runner); installing VELDO creates no timer,
      daemon, or auto-start, and nothing runs it on its own. It spawns no detached or
      headless process (feedback_no_rogue_processes / PLAN-0007 NG1); a scheduled cadence,
      if wanted, is the poll interval an operator sets when they run it, not a hidden
      background mechanism. The boundary is documented.
  - id: AC3
    text: >
      The live JiraCloud adapter is completed for the writes the mirror needs so the
      runner can drive a real Jira: assign (PUT the issue assignee, the WARP-1004
      deferral) plus the existing comment and status transition, authed by the token_ref
      (keep-tokens decision, a secret reference, never a raw credential) and FAILING
      CLOSED when no token resolves. This live path is a REFERENCE implementation wired
      per repo to a live instance and is NOT run in the gate (the FakeTracker path is
      what the gate runs), matching the honesty of the other live adapters. Epic/child
      creation stays deferred to WARP-1006.
  - id: AC4
    text: >
      Idempotency is proven offline: the runner over the FakeTracker across a growing
      event stream walks the ticket through its mapped statuses, posts the links, and
      reassigns at ready-to-test; and a full replay (or a doubled event) records no
      duplicate transition, comment, or reassignment and leaves tracker state
      byte-identical. Teeth: a stream that has advanced moves the ticket, a replay does
      not.
  - id: AC5
    text: >
      capabilities.yaml gains honest entries (the runner mechanical for its control
      logic; the live JiraCloud writes reference) in both byte-identical copies; every
      edited ENGINE_GLOBS file is re-synced byte-identical across engine and
      all seven packs (template-sync and pack-drift pass). The full gate is GREEN, RULE
      #1 is clean, no protected path is touched, and the change lands in the canonical
      two-commit shape.
required_evidence: [operational]
rollback: >
  Revert the commit. The runner is off by default and the live JiraCloud writes are
  reference (never gate-run), so removing it leaves the mirror as callable-but-not-run
  logic exactly as before, with no migration and nothing to unwind on any instance.
---

## Intent

Everything so far mirrors the ticket in the shipped logic but only against the fake
tracker in tests; nothing applies it to a real Jira. This is the piece that makes
the round-trip actually happen: a deterministic, non-LLM runner an operator turns on
to walk each ticket forward (status, links, and the reassignment handoff) on the live
instance. It is opt-in and off by default, and it drives only the tracker, so the
repository stays the source of truth.

## Context

- Reuse the shipped mirror: .veldo/tracker_mirror.py (mirror_events, mirror_plan_events,
  resolve_status_map, the reassign/links from WARP-1004). The runner is the driver that
  feeds them the event stream and an adapter; it adds no new mirror logic.
- The event stream is .veldo/events.jsonl (the same the guard/executor already append to).
  The runner is a reconciler like update_index.py: recompute and apply, idempotent.
- The live edge is non-LLM Python authed by token_ref (the 2026-07-20 keep-tokens
  decision, because an unattended projection must not need an agent). Complete the
  JiraCloud assign write (deferred from WARP-1004); comment + transition already exist.
- No-rogue-processes: the runner is invoked explicitly and creates no persistent
  background mechanism; if a cadence is wanted it is the operator's poll interval, not a
  hidden daemon. This is the same posture as the fleet supervisor (WARP-0907).

## Out of scope

- Live epic/child creation (WARP-1006, still deferred). The inbound bridge/promote gate.
  No auto-start, no systemd timer, no webhook here (poll-when-run only).
- No live Jira in the gate; the FakeTracker drives every assertion.

## Notes

- Keep the runner pure control logic over an injected adapter + an injected event-stream
  reader so the gate drives it with a FakeTracker and a fixture stream, no network.
  Idempotent everywhere; fail closed on a missing token in the live path.
- Follow the byte-identical engine sync discipline and re-run the drift checks before
  proof. Match the existing runner/mirror selftest conventions and their teeth.
