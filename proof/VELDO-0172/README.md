# VELDO-0172 proof

The scrubbed capture contains the two engine streams, the Claude initialize
answer and the Codex login status with its observed stream. No other tap record is retained.

`allowlist.json` names the only string fields and values preserved and the token-count fields preserved.
All other strings become `<string>`; other numbers become zero of their original numeric type.
`grep_schema_constants` names protocol constants excluded from the exhaustive host grep, including
constants that occur as substrings of retained field names. This list does not permit preserving values.

`readback.json` records the host-only comparison: 462 typed paths equal, two tap answers, and no literal
matches among 810 non-allowlisted source strings longer than three characters. `readback.py` uses a
fixed-string grep with its patterns supplied on stdin, printing no source values. The source is read
only. The repository secret scanner reports no findings in `capture.json`.

## Implementation and rows

The binary schemas and initialize-account emitter are read by the existing extractor. Reconciliation
unions captured fields into them and makes a required field optional when a captured line omits it.
The captured Codex agent-message item also supplies its text field to the item schema. Capture sources,
line numbers, binary versions and digests, capture digest and per-event field counts are in the table.

The fake defaults are frozen separately from the capture and table. Shared constructors fill the
positive fixtures before each suite applies its deliberate corruptions. The generated executables
carry the constructor and defaults, so contained launches read no proof file. The ordinary handshake
uses Claude Team; the Claude baseline streams 3 output tokens and ends with 4. Codex usage has five
fields and login status goes to stderr.

`scripts/suites/82_veldo_0172_live_formats.py` reports four rows, each once, and every suite that builds a
fake engine reports one more row of its own:

| Criterion | Row | Observation |
|---|---|---|
| AC1 | `table/capture` | Every captured event conforms, capture digest matches, and the reconciliation writer rebuilds the table from its binary-only fields. Missing fields and required omissions are named. |
| AC2 | `fake/capture:<suite>` (in each fake-building suite) | At its own teardown the suite calls `compare_formats.conform_fake(locals(), '<suite>')`, which drives its generated executables and line constructors once through the production Guard and Terminal. Captured variants have equal recursive field paths; model-name records share one key; every line conforms to the table. Where the suite prints the event: the handshake names `Claude Team`, 3 output tokens stream and 4 end the result, a rate-limit event carries `unifiedWindows`, Codex login status is on stderr with stdout empty, and `turn.completed` usage has 5 fields. The suite's own `format/` rows check all scripted events, including uncaptured tool and error variants. |
| AC2 | `fake/census` | From every suite's syntax tree, never by running one: each suite with an executable literal that prints a Claude Code or Codex line must call `conform_fake` with its locals and short name inside a `finally`, report `VELDO-0172 fake/capture:<short name>` through `expect` and keep a `format/` row. Across those suites, the events their dict displays declare cover every captured event, and each captured event's shared template in `fake_templates.json` has the capture's exact field paths. |
| AC3 | `capture/allowlist` | The committed capture is unchanged by the allowlist scrub, holds exactly the two selected tap answers and passes the repository secret scanner. |
| AC3 | `capture/planted` | The actual scrubber removes a planted host, pid, home path, arbitrary prose and non-token fraction, preserving token counts and value types. |

The census is computed from all suite files, not a list of suite names; a fake-building suite without the
teardown call or its row reds `fake/census`. Each suite prints its compared line count and events on its
own row, and the trace joins each compared line to the suite, row, engine and event. Uncaptured event
variants remain checked against the binary table. No raw source value appears in a comparison diagnostic.

The observation happens where the fake runs, once. Until 2026-09-27 the census executed every other
fake-engine suite in full inside this suite, so its cost was the sum of theirs (136 s with nine suites)
and grew with each new fake suite, past the gate's 120-second mutation worker budget. Now this suite
takes about 1 s and each fake-building suite adds only its own read-back.

The proof driver is `proof/VELDO-0172/drive.py`, added to the footprint because that requested path did not
exist. It uses the existing mutation registry and Git process boundary, archives the unchanged base
for the red replay, and runs mutation and no-op copies with at most two jobs, each in the suite its
case names. A mutation of a fake engine is a mutation of the suite that embeds it, so that mutated suite
is what runs (the registry's worker does the same). Finding 0172 uses the ordinary worker timeout.

## Verification

`verification.json` records nine normal selectors and the same nine selectors in the specified clean
environment: the six modified fake suites, the new comparison suite, the mutation registry suite and
the scope suite. All passed. The comparison observed six suites and 41 emitted fake lines at the build; after the
integration port it observes nine suites and 61 lines. Fresh binary
extraction matches the table; validation, Git boundary, footprint and anchor checks pass. The secret
inventory has zero outstanding findings, and the captured content has zero scanner findings.

The red replay at `65125030` records all four rows of this suite failing by assertion; there `fake/census`
fails because no suite calls the shared conform function. Finding 0172 rejects all eight registered
mutations. `mutations.json` records a green baseline, five green no-op copies (one per module and the
suite that runs it) and all eight mutations failing their named rows by assertion:

| Mutation | Suite | Failing row |
|---|---|---|
| `formats172-binary-only` | 0172 | `table/capture` |
| `formats172-login-stdout` | 79 | `fake/capture:0061_codex_adapter` (on the stream) |
| `formats172-denylist-string` | 0172 | `capture/planted` |
| `formats172-keep-pid` | 0172 | `capture/planted` |
| `formats172-required-usage` | 0172 | `table/capture` |
| `formats172-emitter-required` | 0172 | `table/capture` |
| `formats172-hygiene-answer-drops-provider` | 0165 | `fake/capture:0165_launch_hygiene` |
| `formats172-census-drops-conform` | 0172 | `fake/census` (suite 79 without its teardown call) |

The mutation drivers take a row's name up to its first colon, so they name the per-suite row
`VELDO-0172 fake/capture`; the suite it ran in says which one.

The final whole selftest passed all 122 suites: 6864 assertions passed, zero failed, exit status 0.
The worktree was left untouched while it ran. Git boundary, footprint, anchors and validation pass.
All 198 corresponding Python engine copies are byte-identical. The configuration files
`architecture.yaml` and `policy.yaml` differ between the engine template and this repository, as they
did at the base commit; all four files are unchanged.
The canonical gate was not run, as instructed.

## Integration port (batch-0165-0172)

Suites 82_veldo_0129_worker_wiring, 82_veldo_0141_execution_record and 82_veldo_0165_launch_hygiene were
written after this change was built. Their fakes now carry the shared constructor (`embed`), complete
their lines with `complete_event` or `live_step`, print `Claude Team`, stream 3 output tokens and report 4,
print Codex usage with five fields and Codex login status on stderr. Each calls `__engine_observer__`
before teardown and has a `format/` row. The observer takes each engine's source from `fake_engine(name)`
or `fake`, names the executable after its engine, uses a suite's `readback_packet` when it has one, and
reports an unreadable source as a named problem. Mutation `formats172-hygiene-answer-drops-provider`
removes `apiProvider` from 0165's handshake answer and reds `fake/capture` on that field. The observer
hook was later replaced by each suite's own `conform_fake` call and row (see the table above).

## Census redesign (batch-0165-0172)

The census no longer runs other suites. `compare_formats.conform_fake` is called by each of the nine
fake-building suites at its own teardown, and each reports `VELDO-0172 fake/capture:<suite>`: 0062_accounts
8 lines, 0060_claude_adapter 10, 0160_account_pool 8, 0061_codex_adapter 7, 0155_claude_baseline 4,
0156_codex_baseline 4, 0129_worker_wiring 4, 0141_execution_record 8 and 0165_launch_hygiene 8, the same
61 lines the executed census compared. This suite now takes about 1 s where it took 136 s. Each
suite passes on its own selector, and findings 172, 141, 129, 165, 160, 60, 61, 62 and 155 reject every
registered mutation from a green baseline with two jobs; finding 172's slowest worker is suite 79 at
about 15 s. `red-at-65125030.json` and `mutations.json` were regenerated by the driver.
