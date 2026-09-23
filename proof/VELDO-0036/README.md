# VELDO-0036 proof

Implements Release 1 capacity and subscription usage reservations on the existing
VELDO-0023 SQLite authority. Specification status and policy remain unchanged.

## Contract and integration seams

`control_reservations.Reservations` accepts the authority's explicit store module,
connection, domain/repository coordinates, authenticated principal, current
`authorize(connection, command)` callback and journal signer. Each instance owns
its connection and store module; use one instance per serialized authority client.
The authorization callback must check current membership/scope and the operation's
required evidence, including conclusive non-execution reports. It runs inside the
same `BEGIN IMMEDIATE` transaction as ceiling checks and allocation. Store-owned,
journaled `subscription_reservation` entity rows hold policies, worker slots and
per-invocation allocation/report records. No additional database or schema is needed.
The existing membership service is not repurposed as a second enrollment mechanism.

Configure account, project and unit policies before dispatch. All require capacity,
invocation-count and wall-seconds ceilings; tokens/messages are optional only when
telemetry is available. Reserve a worker before dispatch and use `InvocationGuard`
for every registered initial, retry and follow-on boundary. It commits the reservation
before calling the runner's launch function and passes its complete configuration
object unchanged. An identical accepted-command retry never launches again.
Reports are cumulative and identified by invocation plus sequence; duplicates do not
charge twice. Unknown usage keeps reserved invocation/time exposure. Unbounded token
or message usage blocks the next invocation when that unit has an applicable cap or
window. Partial telemetry is not a per-request maximum. Independent named windows record units, provider
observation watermark, store watermark, outstanding calls and reported reset time.
A refresh cannot erase an unresolved call. No price or quota is invented.

The runtime seam registers Claude Code and Codex subscription boundaries. The live
VELDO-0060/0061 adapters, VELDO-0062 supervisor and the authority service are being
built separately and are absent here. This specification supplies only their narrow
consumption seam: launch/stop callbacks, supervisor observations/deadline ticks, and
current authorization/signing callbacks. The supervisor must call `observe` during
execution and at the reserved wall-time deadline even if the CLI is silent. Retirement
requires its actual termination, cleanup and outcome observations plus settled or
explicitly retained unknown accounting. No model API is used or implemented.
The launch fixtures do not constitute live Claude Code/Codex qualification, Mac
process qualification, or the full installed factory journey. Those remain with
the owning specifications. No recovery, fencing or broader host matrix is added.

Accepted operations are journaled with input versions and identities. The observer
receives accepted/refused operations, domain/repository/request/subject, versions,
watermarks and named refusals, without payloads or credentials. `status()` exposes
current workers, pending/unknown calls and per-service accepted/refused counts.

Both new engine modules are byte-identical with the repository copies and registered
in the scaffold install list. Neither is loaded by the validator, so neither belongs
in `REQUIRED_SUBSTRATE`. The suite consumes the existing store by injection; the
reservation modules import only the Python standard library.

## Criteria and driven negative controls

The suite is `58_veldo_0036_reservations`. Every row below has an unmutated green
control and two different defects registered in `scripts/check_teeth_mutations.py`
(finding 36). Each defective temporary copy completes all assertions; its named row
is false. Exceptions, absent rows and timeouts do not count as detections. Exact
zero-context diffs are in `mutations/`; `mutations.json` retains observed red rows.

| Criterion | Named row (`reservations/` prefix) | Mutation 1 | Mutation 2 |
|---|---|---|---|
| AC1 | `ceilings` | `reservation-extra-slot` | `reservation-ignore-ceiling` |
| AC1 | `atomic-last-slot` | `reservation-check-outside-transaction` | `reservation-ignore-capacity-and-count` |
| AC2 | `pre-call-order` | `reservation-follow-on-after-launch` | `reservation-retry-after-launch` |
| AC2 | `usage-controls` | `reservation-ignore-wall-time` | `reservation-ignore-window` |
| AC3 | `settles-once` | `reservation-duplicate-settlement` | `reservation-double-reported-usage` |
| AC3 | `unknown-retained` | `reservation-timeout-frees-exposure` | `reservation-cancel-frees-exposure` |
| AC4 | `retirement` | `reservation-parent-exit-releases-slot` | `reservation-ignore-cleanup` |

AC1 exercises below, equal and above capacity, invocation, wall-time and available
reported token/message ceilings in each scope and compares committed balances.
Two concurrent clients use separate connections to one real SQLite database and
compete for the last capacity slot and invocation allowance. The declared mutation
moves the ceiling read outside the transaction; both clients admit and the named
atomicity row becomes false.

AC2 enumerates both adapter registrations and their three boundaries. Launch observes
its already committed allocation; exhausted caps launch nothing. Replays do not launch,
current membership withdrawal refuses, configuration identity is preserved, and
observability joins are checked. Invocation-count, wall-time and token/message caps stop the worker;
windows exercise remaining, exhausted, unknown, reset and refreshed observations.
Partial/missing reports cannot erase outstanding window usage.

AC3 compares normal, duplicate and conflicting reports with real allocation balances
and verifies journal signatures using a randomly generated temporary HMAC signing key.
Timeout, cancellation and missing reports retain invocation/time allowances; a later
invocation remains refused. No fixture credentials or key bytes enter committed logs.

AC4 creates a real parent and descendant, observes the parent exit, and attempts slot
reuse while its descendant remains alive. Linux subreaper ownership lets the suite
kill and reap that descendant without leaving a process or zombie. Separate retirement
attempts withhold clone cleanup, outcome and accounting. Only complete observations
plus settled/retained usage allow reuse; unknown usage survives retirement.

SQLite tests use real temporary files and locking, preferring Linux tmpfs to avoid disk
sync latency in repeated mutation runs. Production still uses the existing store's WAL,
foreign-key and FULL synchronous settings. This tests ordinary transactions, not crash
or filesystem durability qualification. Every temporary store and process is cleaned up.

## Gate and timing

Clean-tree canonical verification of `862538f5cc1c620bc58e39d81721eab025fa68a6`:

```text
selftest: 5685 passed, 0 failed
mutations: passed registered=98 executed=98 rejected=98 workers=130 elapsed=61.878s
GATE: GREEN (862538f5cc1c620bc58e39d81721eab025fa68a6)
```

The full log stays outside the repository. `gate-summary.json` records its SHA-256
digest and summary lines. Gate byproducts are restored and excluded from every commit.

Measured added suite work: **4.877 seconds**, below the 60-second limit.
`timing.json` records a conservative serial wall-time bound: the normal unit run,
the first-use integration run, and all 18 added mutation workers (14 defects plus
baseline/no-op controls for both modules). The real gate parallelizes those workers;
no concurrency discount was applied. This is incremental suite cost, not total gate
duration, which includes the existing corpus.

The proof does not assert an independent review verdict.

## Review fixes, 2026-09-23

Baseline: `a284cd0c873abce8eb977279a25ac71ad5cbcc68`. All three supplied
capsules reproduced. Before changing production code, the suite performed their
scenarios and completed with three false assertions, not exceptions. The exact
rows, exit status, capsule script digests and outputs are retained in
`review-20260923/baseline.json`, `baseline-suite.log` and `baseline-capsules.json`.
These targeted runs demonstrate regression detection; only the canonical gate
below establishes completion.

R1: `reservations/partial-final-retained` reserves five seconds, reports one
partial second, supplies an empty final timeout, and attempts a four-second retry.
It also covers cancellation, unspecified outcome and a partial observation above
the reservation. Final settlement now uses only totals supplied in that final
report; missing totals retain the conservative charge and unknown state.
`reservation-final-reuses-partial` reintroduces the finding;
`reservation-final-forgets-reservation` independently discards missing wall usage.
Both produce the named false row. `review-20260923/R1-green.log` and
`R1-mutations.jsonl` record the green control and all 16 rejected mutations;
`review-20260923/mutations/` holds exact applied diffs.

R2: `reservations/report-failure-stops` launches a real child, revokes its
reporting membership in SQLite, and submits the deadline tick. It checks that
the child has already stopped when reporting begins, the authority refusal is
preserved, and stop is called once. A separate pre-deadline failure also must stop
the child. Cleanup kills and reaps any child left by a defective implementation.
The guard now enforces the deadline before reporting and stops on exceptions
throughout the tick. `reservation-report-before-enforcement` restores the unsafe
report-first path; `reservation-report-error-keeps-worker` drops exception-time
stopping. Both fail the named row. `review-20260923/R2-green.log` and
`R2-mutations.jsonl` retain the green control and all 18 rejected mutations.

R3: `reservations/current-caps` first verifies an unstopped worker under ample
ceilings, lowers one current cap, and observes again before the invocation's
original deadline. It repeats for account, project and unit, with wall seconds,
tokens, messages, capacity and invocations. The guard reads all current caps;
usage reaching a ceiling stops the worker, while allocated capacity/invocation
counts may finish at equality and must stop if a lowered cap is exceeded.
`reservation-active-ignores-wall-cap` reintroduces the missing wall check;
`reservation-active-skips-project-cap` omits a different scope's enforcement.
Both fail the named row. `review-20260923/R3-green.log` and
`R3-mutations.jsonl` retain the green control and all 20 rejected mutations.

Final replay of the three original, unchanged capsules: **none reproduces**.
`review-20260923/final-capsules.json` records script digests, successful exits and
outputs: R1 retains five seconds and refuses the retry; R2 reports
`missing_authority` after stopping and reaping the child; R3 requests and performs
stop in all three scopes.

Clean-tree canonical verification of `54b237407c9f0f91a7e8ac24d38e94d40b80e36c`:

```text
selftest: 5688 passed, 0 failed
mutations: passed registered=104 executed=104 rejected=104 workers=136 elapsed=66.305s
GATE: GREEN (54b237407c9f0f91a7e8ac24d38e94d40b80e36c)
```

`review-20260923/gate-summary.json` binds the result to the implementation commit,
tested file digests and full external log digest. Gate byproducts were restored
and excluded from the evidence commit. This records verification, not an
independent review verdict.
