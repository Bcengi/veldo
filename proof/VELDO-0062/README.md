# VELDO-0062 proof: each invocation on its own account's subscription login, and live usage accounting

## The design as built

**Accounts are store records.** `control_accounts` is the `account` record family at factory scope in
the control store: an id, a provider (`claude_code` or `codex`), a label, a status (`active`, `paused`,
`disabled`), a profile directory per host, the rate-limit windows the CLI reported (status, reset,
utilization, observed at, source dispatch) and a concurrency of one by default. Only the owner (a person
holding `project_owner` or `operations_authority`) registers an account or changes its status; only the
reservation service (the launch receiver) records a reported window, and an older observation never
replaces a newer one. `.veldo/accounts.py` stays the local helper: it now prepares a profile for either
provider, prints its one login step (`CLAUDE_CONFIG_DIR=... claude` then `/login`, or
`CODEX_HOME=... codex login`) and gives the fields of the store's `register` command
(`registration`).

**The login comes from the dispatch record.** Before acceptance, the launch receiver
(`control_launch.Receiver._login`) reads the account the accepted contract's reservation records. An
unregistered, paused or disabled account, one of the other provider, or one with no profile on this host
is refused by name and nothing is reserved or spawned. The engine's environment
(`control_accounts.login_environment`) is the inherited one with every login variable removed and that
account's own profile set; `VELDO_ACCOUNT` names the recorded account. What is removed from the inherited environment
(`control_accounts.strips`) is decided by family and by the binaries' own lists: every name under
`ANTHROPIC_`, `OPENAI_`, `CODEX_` (the recorded `CODEX_HOME` is set again after) and `CLAUDE_CODE_USE_`,
and every name the installed binaries' own lists make a login or a Claude Code setting of the owner's
shell (each engine module's `CREDENTIALS` and `SETTINGS`, the receiver passes their union). Claude Code's
lists are its auth credentials, provider switches, endpoints, skip-auth switches, Anthropic secrets,
session, bridge, trusted-device, background-session and file-descriptor tokens, the variables a host
credentials file may set, and the logins and credential and settings redirects of the set it refuses
to take from a settings file (`CLAUDE_SECURESTORAGE_CONFIG_DIR`, `CLAUDE_CODE_HOST_CREDS_FILE`, the managed
and remote settings paths, the OAuth, staging, bridge and federation overrides); Codex's are its auth
variables, agent identity, login endpoint, client, issuer, refresh and revoke overrides, ChatGPT backend,
model endpoints, organization and `CODEX_SQLITE_HOME`. No name is stripped for a word in it: a count or
threshold (`CLAUDE_CODE_MAX_OUTPUT_TOKENS`, `CLAUDE_CODE_IDLE_TOKEN_THRESHOLD`) is not a login. General
proxy, CA, runtime, home, cloud and tool credentials stay (the AWS keys, Azure, Google, package
registries): the worker's tools need them, and neither CLI sends a model request through them once the
provider switches are gone. What the adapter configures is added after the strip and never silently
reduced: a configured model (`ANTHROPIC_MODEL` and the rest of the binary's model table) or setting
reaches the engine as configured, and a configured name that is a login, a redirect or a provider switch
(a profile variable, a `CLAUDE_CODE_USE_` switch or a name in `CREDENTIALS`) is refused by name when the
configuration is loaded (`control_accounts.refused`, `invalid_input:adapter_environment:NAME`), and nothing
runs. MCP
server credentials are not touched. The provider-to-variable map is named once, `accounts.PROFILE_ENV`;
`control_accounts` and `fleet.py` read it from there, and `fleet.py` gives a Claude Code session only a
Claude Code account (its default pool leaves Codex logins out, and naming one is refused by name).

**Every invocation is checked and reserved before it is spawned.** After acceptance, `_invoke` builds
VELDO-0036's `InvocationGuard` over the receiver's own reservations, and its `launch` callback is the
spawn: the invocation (initial, retry or follow-on, `control_reservation_runtime.boundary`) is reserved
against every account, project and unit cap and against the account's reported windows
(`control_reservations._check` reads `control_accounts.blocking` inside the same transaction) before
anything exists. A refusal is recorded by name (`missing_authority:allowance:...`) and launches nothing.
A window reopens only at its reported reset.

**Usage comes from the CLI's own stream.** `control_engine_claude` reads Claude Code's stream JSON:
assistant message usage once per message id (main loop and subagents alike) as the live observations a
cap is checked against, and the `result`'s `modelUsage`, summed over every model (input, output, cache
read and cache creation tokens), as the conclusive total. The result's `usage` is never used for
accounting: the binary's own schema says it is "MAIN AGENT LOOP ONLY" and to prefer `modelUsage`. A
result without a readable `modelUsage` leaves tokens unknown, never zero and never the main loop's.
The binary says a resumed session continues from the totals its transcript saved, so a
resumed invocation's first result already carries the earlier turns: when the CLI reports the session
id the contract's `resume` names, it is charged its running total less the session's running total the
ledger settled last (`Reservations.session`, written by each final report), and its tokens are unknown
when that earlier total is unknown or larger. When the CLI reports another session id (it started a
fresh session, or forked one), its whole running total is charged: a fork that carried the earlier turns
is over-counted, never under-counted. Each final report records which case charged it (the session's
`charged`: `whole`, `difference` or `whole_other_session`; a Codex thread is always `whole`). A resumed Codex thread
is never subtracted: the binary does not say whether `turn.completed` copies the thread total or the
turn's own, and the sum of the invocation's own turns never under-counts under either reading.
`rate_limit_event` gives the windows. `control_engine_codex` reads Codex's exec JSON (`turn.completed`
once per open turn) and its real limit signal: `codex exec --json` prints no rate-limit snapshot (the
`rate_limits` payload lives only in an internal event exec does not emit, and `resets_in_seconds` does
not exist in 0.154.0), so the usage-limit message (in the `error` event and the failed turn) is the
`usage_limit` window, exhausted, with its reset at the end of the local minute it states in the engine's
zone, or no reset when it says "Try again later." (the account then stays refused until a later
observation says otherwise). The rest of Codex's error table is read too: the workspace out of
credits, the workspace spend cap, the quota exceeded and a plan without Codex are each their own
exhausted window with no reset. The receiver's `Metering` keeps each report line raw in a private receipt file (0600 in a
0700 directory, with a header naming dispatch, account, project, unit, provider and boundary), reports
the usage in sequence with the line's digest to the ledger, records windows on the account, and stops
the worker when a report reaches a cap or cannot be recorded. At the end, one final report settles the
invocation: its count, wall time and the CLI's conclusive totals; when there are none (no `result`, an
open turn), tokens and messages stay unknown and their reservation is retained, and the next invocation
under that cap is refused `unknown_allowance`. Timeout and cancellation never release it.

**Totals are read from the ledger.** `control_accounts.usage` shows per account (with label, provider,
status and windows), project and unit the totals in each declared unit, the remaining allowance per cap
(`None` where unknown usage makes it unknowable), the units still unknown, open calls and the watermark
(the journal sequence of the latest recorded usage, `reported_seq`). Attribution is the stored
reservation context, never a caller's or worker's label.

Out of this build: the pool, choosing among accounts and the limit rule (VELDO-0160); the Mac read-back
(VELDO-0147); separating the login from the worker's tools (Release 2); the live run of the real CLIs on
the owner's registered subscriptions.

## Where each format comes from

The first build's fake engines were written to match our own reader, so writer and reader agreed and
nothing checked either against the real CLIs; the second review found three defects that way. Every
line the fakes print is now built in a shape the installed binary declares, and `cli-formats.json` is
that declaration, read out of the binaries' bytes by `extract_formats.py` (nothing is executed, no model
runs, nothing logs in, and no profile, credential or configuration file is opened):

- **Claude Code 2.1.281** (`~/.local/share/claude/versions/2.1.281`, digest in the table): the zod
  schema its binary embeds for the SDK stream messages, parsed from the text of each object: `system`
  `init`, `assistant` (with the Messages API `message` and its `usage`, whose `cache_creation` and
  `server_tool_use` are nested objects), `result` `success` and error variants (with `usage`, described
  "MAIN AGENT LOOP ONLY ... Prefer modelUsage for token/cost accounting", and `modelUsage`, a record per
  model of `inputTokens`, `outputTokens`, `cacheReadInputTokens`, `cacheCreationInputTokens` and more,
  "Per-model totals for every model call ... main loop, Task subagents, sidechains"), and
  `rate_limit_event` (`status` one of `allowed`, `allowed_warning`, `rejected`; `resetsAt` an integer of
  Unix seconds). Its credential tables are the arrays the binary itself holds: the auth credentials, the
  provider selection switches with their companions, the endpoint overrides, the skip-auth switches, its
  list of Anthropic secrets (with the `INPUT_` forms it derives), and the session token sets; two tables
  are kept by decision and say why (the Bedrock wizard's AWS keys, and the tool-secret scrub list).
- **Codex 0.154.0** (the vendor binary of `@openai/codex`, digest in the table): the serde names of
  `codex exec`'s `ThreadEvent` (tag `type`: `thread.started`, `turn.started`, `turn.completed`,
  `turn.failed`, `item.started`, `item.updated`, `item.completed`, `error`) and its payloads
  (`thread_id`; `usage` with `input_tokens`, `cached_input_tokens`, `cache_write_input_tokens`,
  `output_tokens`, `reasoning_output_tokens`; `error.message`), packed in the binary's literals; the
  usage-limit message ("You've hit your usage limit", " Try again at ", " or try again at ",
  " Try again later.", the time formats `%-I:%M %p` and `%b %-d<st|nd|rd|th>, %Y %-I:%M %p`); and its
  credential tables (the auth variables beside `auth.json`, the agent identity variables, the Bedrock
  provider's keys, the exec server's and the shell policy's scrub lists). The strings name fields but do
  not say which are always present, so every Codex usage field is marked optional.

`python3 -B proof/VELDO-0062/extract_formats.py --check` compares the table with a fresh extraction of
the installed binaries and exits 1 when a CLI update moved anything; regenerating the table then reds the
suite's format rows at every fake line that no longer matches, with no live run.

## Suite

`scripts/suites/75_veldo_0062_accounts.py`
(`python3 scripts/selftest.py --suite 75_veldo_0062_accounts`). One temporary tree holds the installed
`.veldo` copy the suite loads and the receiver process executes. Real: a SQLite control store with
OpenSSH journal signatures, account records the owner registers over profiles the helper prepares,
VELDO-0036 reservations under their production authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git
source, the VELDO-0039 Runner and receiver processes and the trusted wrapper. The engines are fake
`claude` and `codex` executables: each records its birth environment (every variable name, and the
profile variables' values) and what the store held for its invocation at its start, then prints the
stream lines its packet scripts, keeping its own copy of what it printed. Every scripted line is built
in the installed CLI's shape (above) and the two format rows check each one against the table. A shell
step before the wrapper records every spawn by dispatch, so a process spawned for a refused invocation
is seen even when its engine never runs. No real engine runs; planted login values are assembled at run
time. Each row is reported once.

| Criterion | Rows |
|---|---|
| AC1 | `login/recorded-account-profile` (declared falsifier), `login/no-paid-api`, `login/configured-environment`, `login/substitution-refused`, `login/fleet-provider` |
| AC2 | `usage/reserved-before-launch` (declared falsifier), `usage/allowance-states`, `usage/competing-remainder`, `usage/cap-stops-worker`, `usage/rate-limit-reset` |
| AC3 | `settle/once`, `settle/model-usage`, `settle/resumed-delta`, `settle/resumed-other-session`, `settle/missing-retained`, `settle/timeout-retained` (declared falsifier), `settle/cancel-retained` |
| AC4 | `attribution/stored-account` (declared falsifier), `attribution/measurement-removed`, `attribution/watermark` |
| Fixtures | `format/claude-fake-lines`, `format/codex-fake-lines` |

`login/*`: with the caller's environment naming another account's Claude and Codex profiles, an ambient
`VELDO_ACCOUNT`, and planted in it every name the binaries' lists strip (read from
`cli-formats.json`, never from production), the nine names the second review found passing the old fixed
list, the redirects the third review found, and a probe of every stripped family with a random suffix (a
name no table lists yet), two Claude Code
accounts and one Codex account each run on exactly their registered profile on this host, with none of
those names and no other provider's profile in the engine's environment, while a neutral variable, a
Claude Code count setting (`CLAUDE_CODE_MAX_OUTPUT_TOKENS`) and two kept tool credentials still reach it
(the strip takes no capability that is not a login), and every name its adapter configures (for Claude
Code the whole model table, the settings and a threshold) arrives with its configured value; an adapter
configuring `ANTHROPIC_API_KEY`, `CLAUDE_SECURESTORAGE_CONFIG_DIR` or `OPENAI_BASE_URL` is refused by name
with nothing launched or reserved, and on the production refusal every listed login is refused and no
model, setting or kept name is; a contract with its account, unit or station
substituted, a passed deadline, a paused account, one with a profile only on another host, one of the
other provider and an unregistered one are each refused by name with nothing spawned or reserved; the
fleet's default pool is the five Claude Code accounts on their own profiles, and a Codex account pinned
or listed for it is refused by name before any worker starts.
`usage/*`: initial, retry and follow-on invocations of both providers are reserved as such before the
engine starts (the engine sees its pending reservation, and the reservation's journal sequence precedes
the run record); a follow-on past the unit's invocation cap is refused before anything is spawned;
available, exhausted and unknown allowance; two invocations racing for one remaining invocation launch
one; the report that reaches a token cap stops the worker; a Claude Code `rate_limit_event` rejected
window and a Codex usage-limit message each refuse new work on their account until the reported reset
(Codex's: the end of the minute its message states, in three zones), refused one second before it and
allowed at it on the account record, the reservation check and the Codex reader with a fixed clock (no
wait), then the account takes work again; every message of Codex's error table is read as its window or
as none, and a message stating no reset (or a workspace out of credits) keeps its account refused
however long. `settle/*`: repeated message and turn
lines are counted once, a redelivered report changes nothing and a conflicting one is refused, the
ledger's receipt digests are the stored raw lines', and totals recomputed by the suite from those stored
lines, and from the lines the engine itself printed, equal the balances; a main-loop message, a subagent
message and a result settle the result's `modelUsage` total over both models (101620 tokens, where the
main loop's `usage` is 5012), and on the production reader a result without `modelUsage` leaves tokens
unknown; a resumed Claude Code session is charged its running total less the total the ledger
settled for that session, unknown when none was settled, and a resumed Codex thread its own turns; a
follow-on whose contract resumes a session settled at 1000 but whose CLI reports another session with a
running total of 5000 is charged all 5000, the named session's settled total stays 1000, and the ledger
records the other session as `whole_other_session`, a later resumption the CLI reports as the named
session as `difference` (charged 200 of 1200) and the initial invocation as `whole`; a
stream with no conclusive report, a timeout and a cancellation each keep the reservation and
refuse the next invocation. `attribution/*`: with ambient labels naming another account, the shown
totals per account (all five registered that ran), unit and the journey project equal the stored
receipts grouped by the account each dispatch recorded; an invocation that reported nothing shows its
invocation and wall time, tokens unknown, remaining tokens `None`; every subject's watermark is the
journal sequence of its latest usage. `format/*`: every line the fakes were scripted to print (over 20
per engine) conforms to its event's schema in the table (required fields present, no field the CLI does
not declare, enum and literal values, integer counts), the fixtures print every event the readers settle
from, and each Codex usage-limit message matches the binary's own message, retry phrases and time
formats. They check the fixtures, not production, so they are green at the pre-change commit too.

Plain run: 47 passed (26 preamble, 21 rows) in 25 seconds, measured three times at 25.4, 25.4 and
25.5 seconds. Stage environment run (`env -i`, the stage's variables, TZ=UTC): 47 passed in 32 seconds.
The run no longer waits for a stated minute to end: the reset boundary is tested at the seams that take a
clock.

## Red record

`red-at-0af8dc0.json`: the current suite over `git archive 0af8dc0`, unchanged. All 19 behavior rows fail
by their own assertion: there are no account records, the receiver launches an engine adapter in the
caller's environment with its profiles and login variables, refuses no configured login, reserves no
invocation, nothing reads the CLI's usage reports, its usage-limit message or its error table, no
session is settled, and the helper registers no Codex login for the fleet to keep out. Where the tree has
no refusal or engine map, the row records that as data rather than raising. The two `format/*` rows are
green there, as they must be: they check the suite's own fixtures against the extracted table, not
production.

## Mutations (finding 62)

Registered in `scripts/check_teeth_mutations.py` with the `account-` prefix, each declared falsifier
first; `drive.py` records `mutations.json` and one applied diff per mutant. All 48 turn their named row
red by assertion; the baseline and the no-op copies are green.
`check_teeth_mutations.py --finding 62`: 48 rejected.

| Mutant | Module | Named row |
|---|---|---|
| account-profile-from-caller (AC1 falsifier) | control_accounts.py | login/recorded-account-profile |
| account-login-fixed-list (back to the fixed list) | control_accounts.py | login/no-paid-api |
| account-login-families-ignored | control_accounts.py | login/no-paid-api |
| account-credential-tables-ignored | control_accounts.py | login/no-paid-api |
| account-claude-lists-ignored | control_engine_claude.py | login/no-paid-api |
| account-securestorage-redirect-passes | control_engine_claude.py | login/no-paid-api |
| account-host-creds-passes | control_engine_claude.py | login/no-paid-api |
| account-session-tokens-path-passes | control_engine_claude.py | login/no-paid-api |
| account-settings-inherited | control_launch.py | login/no-paid-api |
| account-token-word-strips | control_accounts.py | login/no-paid-api |
| account-claude-old-tables (back to the old strip tables) | control_engine_claude.py | login/no-paid-api |
| account-codex-old-tables (back to the old strip tables) | control_engine_codex.py | login/configured-environment |
| account-claude-sensitive-list-dropped (the sensitive-variable table dropped) | control_engine_claude.py | login/no-paid-api |
| account-configured-login-accepted (a configured login passed) | control_accounts.py | login/configured-environment |
| account-codex-lists-ignored | control_engine_codex.py | login/configured-environment |
| account-configured-stripped | control_accounts.py | login/configured-environment |
| account-configured-model-dropped (a configured model dropped) | control_launch.py | login/configured-environment |
| account-fleet-codex-to-claude | fleet.py | login/fleet-provider |
| account-status-unchecked | control_accounts.py | login/substitution-refused |
| account-follow-on-checked-after-launch (AC2 falsifier) | control_launch.py | usage/reserved-before-launch |
| account-boundary-always-initial | control_reservation_runtime.py | usage/reserved-before-launch |
| account-invocation-unreserved | control_launch.py | usage/allowance-states |
| account-cap-stop-ignored | control_launch.py | usage/cap-stops-worker |
| account-rate-window-unchecked | control_reservations.py | usage/rate-limit-reset |
| account-timeout-releases (AC3 falsifier) | control_launch.py | settle/timeout-retained |
| account-cancel-releases | control_launch.py | settle/cancel-retained |
| account-claude-missing-result-conclusive | control_engine_claude.py | settle/missing-retained |
| account-claude-main-loop-usage (result.usage read again) | control_engine_claude.py | settle/model-usage |
| account-claude-missing-model-usage-main-loop | control_engine_claude.py | settle/model-usage |
| account-codex-limit-unobserved (the usage-limit message ignored) | control_engine_codex.py | usage/rate-limit-reset |
| account-codex-workspace-unobserved (the workspace credit messages ignored) | control_engine_codex.py | usage/rate-limit-reset |
| account-codex-spend-cap-unobserved (the spend cap messages ignored) | control_engine_codex.py | usage/rate-limit-reset |
| account-codex-exhaustion-reset-invented | control_engine_codex.py | usage/rate-limit-reset |
| account-window-reopens-early (the reset allowed one second early) | control_accounts.py | usage/rate-limit-reset |
| account-window-reopens-late | control_accounts.py | usage/rate-limit-reset |
| account-codex-unstated-reset-invented | control_engine_codex.py | usage/rate-limit-reset |
| account-codex-reset-at-minute-start | control_engine_codex.py | usage/rate-limit-reset |
| account-codex-open-turn-conclusive | control_engine_codex.py | settle/missing-retained |
| account-claude-resume-whole-total (a resumed session charged its whole total) | control_engine_claude.py | settle/resumed-delta |
| account-claude-resume-unknown-prior-whole (a guess when the earlier total is unknown) | control_engine_claude.py | settle/resumed-delta |
| account-resume-prior-unread | control_launch.py | settle/resumed-delta |
| account-session-unsettled | control_launch.py | settle/resumed-delta |
| account-codex-resume-subtracted | control_engine_codex.py | settle/resumed-delta |
| account-claude-repeat-counted | control_engine_claude.py | settle/once |
| account-codex-repeat-counted | control_engine_codex.py | settle/once |
| account-caller-label-attributed (AC4 falsifier) | control_launch.py | attribution/stored-account |
| account-unknown-remaining-counted | control_accounts.py | attribution/measurement-removed |
| account-watermark-from-reservation | control_accounts.py | attribution/watermark |

The first build's `account-paid-api-kept` is gone with the fixed list it mutated. The other findings with
mutations in the modules this changes still reject: 36 (20; its report-order mutant now follows the
session the final report settles), 39 (30), 40 (22) and 41 (34). Main merged at a166d14. Suites run,
plain and under the stage environment, all green: `75_veldo_0062_accounts`, the VELDO-0036, 0039, 0040,
0041, 0047 and 0050 suites (58, 62, 63, 67, 66, 64), `36_veldo_0023_journal`, `39_veldo_0026_revocation`,
`40_veldo_0101_capsules`, `41_veldo_0103_assessor`, `47_veldo_0107_ipc` and `50_git_environment`.
