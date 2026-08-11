---
description: Show Veldo status for this repository - in-flight specs, gate state, open judgment calls, emergency debt.
allowed-tools: Read, Grep, Glob, Bash
---

Report the repository's Veldo state ($ARGUMENTS filters to one spec id):

- Specifications by status, from specs/index.md (regenerate first if stale).
- The gate: .veldo/last_verify vs the current HEAD - green, red, or stale.
- In-flight specs: whether proof and verdict exist for the current state.
- Emergency debt: any emergency.push event in .veldo/events.jsonl without a
  closing backfill (spec + proof + review landed after it).
- Metrics: run `python3 .veldo/metrics.py` for the derived numbers - spec-to-
  ship latency, proof latency, total human minutes (the scarce-resource
  metric), gate pass rate, and open emergency debt - all computed from the
  event stream by correlation_id, never hand-maintained.
- Live runs (Run Lens): run `python3 .veldo/runstatus.py status --json` for the
  read model over git plus the event stream plus the R1 run registry - each
  live run classified active, blocked, stale, or done, with its current phase,
  any blocked question, its heartbeat age, and blocked-elapsed shown SEPARATELY
  from human_minutes; tokens appear only when the run supplies them, otherwise
  "unknown", never estimated. `python3 .veldo/runstatus.py watch` renders a
  compact terminal view (add `--interval N` for an interruptible refresh loop).
  The reader is read-only: it writes nothing to the registry, events, or repo.
- Live runs in a browser (Run Lens): run `python3 .veldo/runstatus.py status
  --serve` (the `veldo status --serve [--port N]` front door) to start a thin
  read-only local server on 127.0.0.1. GET /status serves the SAME read model
  as `veldo status --json` (one projection, no drift), GET / is a self-contained
  page that refreshes it, and GET /events is a live SSE stream. It binds
  loopback only (never 0.0.0.0) and writes nothing; it is `.veldo/status_server.py`.
- End with the single next action a human owes, if any; otherwise say
  nothing is waiting on a human.
