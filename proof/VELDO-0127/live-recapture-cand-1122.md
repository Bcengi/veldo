# Live recapture and requalification on the combined candidate cand-1122

Owner approval: Telegram 43144 (answering 43131), at most 5 tiny Claude Code runs and at most 5 tiny
Codex runs, each in an empty scratch folder, no MCP servers outside the factory's own local stub.
Reason: the captures and qualification resources bind engine module digests that this candidate
changed (VELDO-0358 waves 0 and 1, VELDO-0359, the bring-up line).

| Engine | CLI version | Model | Real runs | Result |
| - | - | - | - | - |
| Codex | codex-cli 0.166.0 (vendor binary, sha256 b8a11fed...) | gpt-6-astra | 4 of 5 allowed | codex-live.json written, judge: captured |
| Claude Code | 2.1.317 (sha256 eb224419...) | claude-haiku-4-5-20251001 | 5 of 5 allowed | claude-live.json written, judge: captured |

Codex, first two attempts: refused at launch with `invalid_input:layout:placement` before any engine
started (the redacted diagnostics show the launch and record both `refused`), so neither is a run.
Cause: VELDO-0359's store guard refuses a store beneath a location the engine may write, and live.py
built its factory (store included) under the runtime directory. live.py now keeps only the borrowed
logins on the private runtime tmpfs and builds the factory under /var/lib/veldo, where suite 86 builds
its own. Third attempt: the four factory runs (always and deferred roles, control and planted marker),
all completed. The loopback captures beside them use an empty temporary profile and a local endpoint,
so they are not counted.

Claude Code: the login this session's runner holds was not borrowed (live.py's borrow refuses a lease
held by another process, as in the 0231 capture); a login no other job held was borrowed under its
lease. 5 real runs: the four factory runs, all completed, and the discovery control (returncode 0,
context-size-only). The login's rotated credential was written back and still holds a refresh token.

Requalification: `python3 .veldo/qualify.py --codex <binary> --claude <binary>` on the engines
record's binaries (loopback only, no model call, no account). It rewrote the four
`resources-*.json` fixtures; the runtime qualification records came out byte-identical.

Suites, each run once alone (`scripts/selftest.py --suite`, exit 2 is a passed partial run):
86_veldo_0127_agent_configuration 29 passed, 0 failed (live/claude and live/codex green);
126_veldo_0230_qualify_reproduces 5 passed, 0 failed. scripts/check_personal_setup.py: 0 findings.
