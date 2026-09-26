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
(`control_accounts.login_environment`) is the inherited one with every provider's profile variable and
every paid-API credential variable (each engine module's `PAID_API`) removed, and that account's own
profile set; `VELDO_ACCOUNT` names the recorded account. MCP server credentials are not touched.

**Every invocation is checked and reserved before it is spawned.** After acceptance, `_invoke` builds
VELDO-0036's `InvocationGuard` over the receiver's own reservations, and its `launch` callback is the
spawn: the invocation (initial, retry or follow-on, `control_reservation_runtime.boundary`) is reserved
against every account, project and unit cap and against the account's reported windows
(`control_reservations._check` reads `control_accounts.blocking` inside the same transaction) before
anything exists. A refusal is recorded by name (`missing_authority:allowance:...`) and launches nothing.
A window reopens only at its reported reset.

**Usage comes from the CLI's own stream.** `control_engine_claude` reads Claude Code's stream JSON
(assistant message usage once per message id, the `result` total once, `rate_limit_event`);
`control_engine_codex` reads Codex's exec JSON (`turn.completed` once per open turn, `rate_limits`
snapshots). The receiver's `Metering` keeps each report line raw in a private receipt file (0600 in a
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

## Suite

`scripts/suites/75_veldo_0062_accounts.py`
(`python3 scripts/selftest.py --suite 75_veldo_0062_accounts`). One temporary tree holds the installed
`.veldo` copy the suite loads and the receiver process executes. Real: a SQLite control store with
OpenSSH journal signatures, account records the owner registers over profiles the helper prepares,
VELDO-0036 reservations under their production authorization, VELDO-0052's Gate, VELDO-0031 claims, a Git
source, the VELDO-0039 Runner and receiver processes and the trusted wrapper. The engines are fake
`claude` and `codex` executables: each records its birth environment and what the store held for its
invocation at its start, then prints the stream lines its packet scripts in the CLIs' own formats. A
shell step before the wrapper records every spawn by dispatch, so a process spawned for a refused
invocation is seen even when its engine never runs. No real engine runs; planted paid-API values are
assembled at run time. Each row is reported once.

| Criterion | Rows |
|---|---|
| AC1 | `login/recorded-account-profile` (declared falsifier), `login/no-paid-api`, `login/substitution-refused` |
| AC2 | `usage/reserved-before-launch` (declared falsifier), `usage/allowance-states`, `usage/competing-remainder`, `usage/cap-stops-worker`, `usage/rate-limit-reset` |
| AC3 | `settle/once`, `settle/missing-retained`, `settle/timeout-retained` (declared falsifier), `settle/cancel-retained` |
| AC4 | `attribution/stored-account` (declared falsifier), `attribution/measurement-removed`, `attribution/watermark` |

`login/*`: with the caller's environment naming another account's Claude and Codex profiles, an ambient
`VELDO_ACCOUNT` and every paid-API variable planted (in the caller's and the adapter's environment), two
Claude Code accounts and one Codex account each run on exactly their registered profile on this host,
no other provider's profile and no paid-API variable; a contract with its account, unit or station
substituted, a passed deadline, a paused account, one with a profile only on another host, one of the
other provider and an unregistered one are each refused by name with nothing spawned or reserved.
`usage/*`: initial, retry and follow-on invocations of both providers are reserved as such before the
engine starts (the engine sees its pending reservation, and the reservation's journal sequence precedes
the run record); a follow-on past the unit's invocation cap is refused before anything is spawned;
available, exhausted and unknown allowance; two invocations racing for one remaining invocation launch
one; the report that reaches a token cap stops the worker; a reported rejected window refuses new work
until its reported reset, then the account takes work again. `settle/*`: repeated message and turn lines
are counted once, a redelivered report changes nothing and a conflicting one is refused, the ledger's
receipt digests are the stored raw lines' and totals recomputed from those lines equal the balances; a
stream with no conclusive report, a timeout and a cancellation each keep the reservation and refuse the
next invocation. `attribution/*`: with ambient labels and a worker claiming another account, the shown
totals per account (all five registered), unit and the journey project equal the stored receipts
grouped by the account each dispatch recorded; an invocation that reported nothing shows its invocation
and wall time, tokens unknown, remaining tokens `None`; every subject's watermark is the journal sequence
of its latest usage.

Plain run: 41 passed (26 preamble, 15 rows), about 26 seconds. Stage environment run (`env -i`, the
stage's variables), together with the suites of every touched module and suite 50: 47 suites, 2314
passed, 0 failed.

## Red record

`red-at-0af8dc0.json`: the current suite over `git archive 0af8dc0`, unchanged. All 15 rows fail by their
own assertion: there are no account records, the receiver launches an engine adapter in the caller's
environment with its profiles and paid-API variables, reserves no invocation, and nothing reads the CLI's
usage reports.

## Mutations (finding 62)

Registered in `scripts/check_teeth_mutations.py` with the `account-` prefix, each declared falsifier
first; `drive.py` records `mutations.json` and one applied diff per mutant. All 17 turn their named row
red by assertion; the baseline and the no-op copies are green.
`check_teeth_mutations.py --finding 62 --jobs 2`: 17 rejected.

| Mutant | Module | Named row |
|---|---|---|
| account-profile-from-caller (AC1 falsifier) | control_accounts.py | login/recorded-account-profile |
| account-paid-api-kept | control_accounts.py | login/no-paid-api |
| account-status-unchecked | control_accounts.py | login/substitution-refused |
| account-follow-on-checked-after-launch (AC2 falsifier) | control_launch.py | usage/reserved-before-launch |
| account-boundary-always-initial | control_reservation_runtime.py | usage/reserved-before-launch |
| account-invocation-unreserved | control_launch.py | usage/allowance-states |
| account-cap-stop-ignored | control_launch.py | usage/cap-stops-worker |
| account-rate-window-unchecked | control_reservations.py | usage/rate-limit-reset |
| account-timeout-releases (AC3 falsifier) | control_launch.py | settle/timeout-retained |
| account-cancel-releases | control_launch.py | settle/cancel-retained |
| account-claude-missing-result-conclusive | control_engine_claude.py | settle/missing-retained |
| account-codex-open-turn-conclusive | control_engine_codex.py | settle/missing-retained |
| account-claude-repeat-counted | control_engine_claude.py | settle/once |
| account-codex-repeat-counted | control_engine_codex.py | settle/once |
| account-caller-label-attributed (AC4 falsifier) | control_launch.py | attribution/stored-account |
| account-unknown-remaining-counted | control_accounts.py | attribution/measurement-removed |
| account-watermark-from-reservation | control_accounts.py | attribution/watermark |

The other findings with mutations in the modules this changes still reject: 36 (20, its
`control_reservations.py` mutants now copy their siblings), 39 (30), 40 (22) and 41 (34).
