# VELDO-0231 live captures for suite 86 (review F4), 2026-11-21

Owner approval: Telegram 42874 (answering 42872), at most 5 tiny Claude Code runs and at most 5 tiny
Codex runs, each in an empty scratch folder, no MCP servers. Procedure: proof/VELDO-0127/live.py with
the binaries pinned in .veldo/runtime/engines.json, one engine at a time (the `only` option).

| Engine | CLI version | Model | Real runs | Result |
| - | - | - | - | - |
| Codex | codex-cli 0.166.0 (vendor binary, sha256 b8a11fed...) | gpt-6-astra | 4 of 5 allowed | codex-live.json written, judge: captured |
| Claude Code | 2.1.317 (sha256 eb224419...) | claude-haiku-4-5-20251001 | 0 of 5 allowed | not captured |

Codex: the four runs are always and deferred roles, each control and planted marker. The four loopback
captures beside them run the same binary with an empty temporary profile against a local endpoint (no
login, no provider), so they are not counted as real runs. Run directory uids written as UID.

Claude Code: not run. The Claude login this run was given is the one its own runner leases for the
session that drives this capture, so live.py's borrow refused before any engine started
("borrowed login is busy: <login>/.runner-lease is held by another run"). The capture needs a Claude
login no other job holds, taken by whoever holds that login's lease.

Suite 86 (scripts/selftest.py, this suite alone): before 26 of 28 (live/claude, live/codex red, both
"missing or stale live capture"); after 27 of 28, live/codex green, live/claude red (stale capture).
