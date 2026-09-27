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

`scripts/suites/82_veldo_0172_live_formats.py` reports each row once:

| Criterion | Row | Observation |
|---|---|---|
| AC1 | `table/capture` | Every captured event conforms, capture digest matches, and the reconciliation writer rebuilds the table from its binary-only fields. Missing fields and required omissions are named. |
| AC2 | `fake/capture` | A census of protocol-bearing executable literals finds nine suites on batch-0165-0172 (six at the build, plus 0129, 0141 and 0165 from the integration). Each runs its actual launch tests and, before teardown, the observer drives its generated executable and existing line constructors using the production Guard and Terminal. Captured variants have equal recursive field paths; model-name records share one key. Existing format rows check all scripted events, including uncaptured tool and error variants. Login streams, subscription label and streamed/final output counts are read back. |
| AC3 | `capture/allowlist` | The committed capture is unchanged by the allowlist scrub, holds exactly the two selected tap answers and passes the repository secret scanner. |
| AC3 | `capture/planted` | The actual scrubber removes a planted host, pid, home path, arbitrary prose and non-token fraction, preserving token counts and value types. |

The census is computed from all suite files, not a list of suite names. Its generated read-back traces
join each compared line to the suite, row, engine and event. Uncaptured event variants remain checked
against the binary table. No raw source value appears in a comparison diagnostic.

The proof driver is `proof/VELDO-0172/drive.py`, added to the footprint because that requested path did not
exist. It uses the existing mutation registry and Git process boundary, archives the unchanged base
for the red replay, and runs mutation and no-op copies with at most two jobs. Finding 0172 has a scoped
300-second worker timeout because each trial drives every discovered launch suite.

## Verification

`verification.json` records nine normal selectors and the same nine selectors in the specified clean
environment: the six modified fake suites, the new comparison suite, the mutation registry suite and
the scope suite. All passed. The comparison observed six suites and 41 emitted fake lines at the build; after the
integration port it observes nine suites and 61 lines. Fresh binary
extraction matches the table; validation, Git boundary, footprint and anchor checks pass. The secret
inventory has zero outstanding findings, and the captured content has zero scanner findings.

The red replay at `65125030` records all four behavior rows failing by assertion, without observer
errors. Finding 0172 rejects all five registered mutations. `mutations.json` records a green baseline,
three green no-op copies and all five mutations failing their named rows by assertion:

| Mutation | Failing row |
|---|---|
| `formats172-binary-only` | `table/capture` |
| `formats172-login-stdout` | `fake/capture` |
| `formats172-denylist-string` | `capture/planted` |
| `formats172-keep-pid` | `capture/planted` |
| `formats172-required-usage` | `table/capture` |

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
removes `apiProvider` from 0165's handshake answer and reds `fake/capture` on that field.
