# VELDO-0160 build notes (builder's working notes)

Base: 52f817d5 (main, VELDO-0062 landed). Branch build-veldo-0160.

## Design decisions

- Selection lives in a new module `control_account_pool.py` (footprint `control_account*.py`). It is
  called INSIDE the VELDO-0036 reservation transaction: `Reservations.reserve_pooled` is a new worker
  action whose transition chooses the account and reserves its slot atomically, so two preparations
  cannot both take an account's last slot.
- The Runner takes a `Pool` as its `account` (duck-typed: an object with `reserve`). control_launch.py
  changes are two small separate hunks: Runner.prepare (pool branch) and Metering.settle
  (classification). The VELDO-0060/0061 branch rewrites the engine hooks elsewhere in that file.
- Candidates: active accounts of the adapter's engine with a profile on the adapter's host, outside
  every reported rate-limit window (control_accounts.blocking), under their concurrency; an account
  with no observation (no window on its record and no CLI-reported usage in the ledger) is bounded at
  one run. Order: lowest last reported utilization on the tightest window (unknown sorts after every
  known one: unknown is never zero), then fewest active runs, then least recently used, then id.
  The account's VELDO-0036 account caps are checked per candidate; a project or unit cap refuses.
- No candidate: refused `no_account_until:<earliest reset>` (or `no_account`), each account passed
  over with its reason on the refusal.
- One registration per account: an id already registered, or a profile directory (per host) that is
  already another account's, is refused `duplicate_account:<existing id>`.
- account_limit: each engine meter keeps the last limit its stream stated (`limit()`: window, reset,
  signal `stream` or `result`). Claude Code: a `rate_limit_event` rejected (stream) or a `result` with
  `is_error` whose text is the usage-limit message "You've hit your <limit> ... resets <time> (<zone>)"
  (result; window from the binary's limit-name table, reset parsed from the stated time and zone, end
  of the stated minute). Codex: the usage-limit / exhaustion message in an `error` event (stream) or a
  `turn.failed` (result). `control_accounts.classify` turns the outcome into `account_limit` with the
  window and reset: a result signal always, a stream signal unless the run completed. The final ledger
  report carries outcome `account_limit` and `limit`.
- The re-run-or-ask decision is `control_account_limit.decide(record, servers, marks, provider)` over
  the fixture record form of the spec's Notes; MCP calls read by each engine module's `mcp_calls`.
- extract_formats.py (VELDO-0062 proof) extended: Claude's usage-limit message pieces and limit names,
  Codex's exec `mcp_tool_call` item. Footprint gains proof/VELDO-0062/extract_formats.py and
  cli-formats.json (the lead allowed extending it).

## Progress log
- 2026-09-26T11:57:42Z suite 78 written, 14 rows green in 9.8 s; next: red record, mutations
- 2026-09-26T12:18:41Z consumer suites green (47); next: validate, footprint, anchors, drive, README, History
