---
schema: veldo.spec/v1
id: WARP-0504
title: Thin read-only local status server - serve the Run Lens read model live on localhost
status: shipped
risk: standard
owner: dmitry
lane: planned
plan: PLAN-0005
work: R4
plan_revision: 1
human_approval: not_required
protected_paths: []
required_evidence: [unit]
acceptance_criteria:
  - id: AC1
    text: A thin stdlib http server serves the R3 read model live. GET /status returns
      runstatus.status() as JSON - the SAME projection veldo status --json prints, with
      no second model assembled - and GET / returns a self-contained HTML and JS page
      (inline CSS and JS, no external asset or CDN) that fetches /status and refreshes.
      A GET /events Server-Sent-Events stream that pushes the model on an interval is
      provided for live push, with the page falling back to polling.
  - id: AC2
    text: The server binds 127.0.0.1 ONLY and never 0.0.0.0, so it exposes no remote
      surface. The roots (root, runs_root, events_path) are overridable so the control
      logic is driven over a temporary runs root and a real ephemeral 127.0.0.1 port
      with no external service.
  - id: AC3
    text: The server is READ-ONLY. Only GET is implemented, so any other method is the
      stdlib 501, and every endpoint reads through runstatus and writes nothing to the
      registry, the event stream, or the repo. The served model already excludes
      secrets; if a control endpoint is ever added it must require an ephemeral token.
  - id: AC4
    text: A CLI front door starts the server - veldo status --serve with an optional
      --port - wired through the reader by lazy import so the reader keeps no load-time
      dependency on the server, and the module is also runnable directly via its main().
  - id: AC5
    text: A selftest starts a REAL server on an ephemeral 127.0.0.1 port over a temporary
      runs root with a synthetic run, makes a real GET /status with urllib, and asserts
      the JSON model comes back with the run and its classification; asserts the bound
      host is 127.0.0.1 (not 0.0.0.0); asserts the page is self-contained HTML with no
      external URL; and asserts a before/after snapshot of the runs root is unchanged
      (read-only). It is non-tautological - a mutant that binds 0.0.0.0 or serves an
      empty or stale model makes an assertion fail - and the server is shut down cleanly.
rollback: git revert; additive - a new .veldo/status_server.py, a --serve/--port flag added
  to the runstatus status CLI, a status_server entry added to both capabilities.yaml copies,
  a selftest block, the spec, and the regenerated index; no protected path is touched and
  the server writes nothing at runtime.
---

## Intent

Serve the Run Lens read model live in a browser, so a human can watch a running VELDO build
without a terminal. This is the third read surface over the R1 substrate, beside veldo status
--json and veldo watch: the same model, projected once, over a small local http server. It
stays proportionate - git plus the event stream plus the per-run folder, read on demand -
with no hosted app, no database, no message bus, and no daemon (plan non-goal NG2).

## Context

The R3 reader (WARP-0503) already assembles the read model from git, the event stream, and
the R1 run registry (WARP-0501), and classifies each run active, blocked, stale, or done.
This item adds a thin http surface in front of that one function. It assembles NO model of
its own: GET /status calls runstatus.status() and serves exactly what it returns, so the
browser view and the CLI can never disagree. The local browser view and the chat wiring
(R6) read the same model.

## Notes

The server binds the loopback interface only and implements GET only, so it has no remote
surface and no write path; that is why it needs no authentication, and the gate selftest
asserts both the loopback bind and read-only behavior (a before/after snapshot of the runs
root is byte-identical). The page is self-contained - inline CSS and JS, no external asset
or CDN - and prefers the /events stream, falling back to polling /status. runs_root and the
events path are overridable so the control logic is gate-tested over a temporary runs root
and a real ephemeral 127.0.0.1 port with no live agent or backend, and the server is shut
down cleanly. A 0.0.0.0 bind or an empty/stale model each turns a selftest assertion red.
