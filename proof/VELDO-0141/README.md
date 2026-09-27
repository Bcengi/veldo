# VELDO-0141 proof: every worker run's full live execution record, redacted, served for the live terminal view

Built on branch build-veldo-0141 from main at 3c85f33b.

## The design as built

**What is kept.** The launch receiver alone holds a worker's pipes, so it alone writes the record
(`control_execution_record.Recorder`, opened by `control_launch.Receiver._spawn` before the worker exists). The
worker's error stream, which the receiver used to send to `/dev/null`, is now piped to it (the contained spawn and
a transport's alike) and read in the same reap loop as the output, woken by the same poll. The record is one
append-only file per dispatch, `<records>/<sha256 of the dispatch id>.jsonl`, where `<records>` is the receiver
configuration's `records`, else `<state root>/records`, else `records` beside the store; the file is 0600 in a
0700 directory, created exclusively. Its first line is the header binding it to the dispatch and run: schema,
dispatch id, contract digest, unit, station, project, account, host. Each further line is one line the run
printed, in the order the receiver read it: `seq` (gapless from 1), `at` (the receiver's clock), `stream`
(`wrapper` for the trusted wrapper's identity line, written before it became the engine; `engine` for each line
of the engine's standard output, its stream JSON or exec JSON event; `stderr` for each raw line of the error
stream), `redacted` (the kinds replaced, sorted) and `payload` (the line as printed, without its newline, except
for redacted spans; bytes that are not UTF-8 kept as surrogate escapes). A last line with no newline is kept when
the stream ends. Nothing is parsed, merged, summarized or dropped.

**Redaction, before a line is kept.** `redact(text, resolved)` first replaces every value in the run's set of
resolved credential values (`Resolved`), longest first, in each form a line carries it (as printed, and as a JSON
string escapes it, ASCII-escaped or not), by `[REDACTED:<kind>]`; only then does secret_scan (its own
`PATTERNS`, `_CANDIDATE`, `_is_digest` and `shannon`, reused) replace its known patterns
(`[REDACTED:pattern:<shape>]`, the pattern's own description as a name, `pattern:github_token` for "a GitHub
token") and its high-entropy spans (`[REDACTED:entropy]`, a hex digest's shape excepted). The set is filled once
per run, as the worker is spawned, by `control_launch.RESOLVERS`: each `resolver(receiver, contract, adapter,
environment)` returns `[(kind, value)]` and may deliver its value into the engine's environment. The built-in one
is the account's subscription token (`subscription_token`, VELDO-0155 AC2's file); VELDO-0158 AC3 adds the
keystore's. The receiver's end event names the kinds in the set and the redactions by kind, never a value.

**Committed at the end, hinted as it goes.** After each batch the reap loop hints each socket the receiver
configuration's `record_hints` names (the API process's own hint socket, `control_client_api.Hints`) with
`{schema: veldo.execution_record_hint/v1, dispatch_id, seq, ended}`, written only to this account's own socket in
a directory nobody else can enter, its peer checked with SO_PEERCRED; a hint only wakes. The record is closed
when the worker's streams are drained, and `control_dispatch.exit` commits `execution_record: {lines, bytes,
digest}` (the count of record lines, the file's size and SHA-256) in the exit record; the receiver then sends a
last hint marked ended and tells the runner the run ended, its end event carrying the record's account (`record`:
path, line and byte counts per stream, redactions by kind, the resolved kinds, the hints sent, the commitment).

**Served.** `control_api_authority.ApiAuthority.record(principal, dispatch_id, after, limit)` reads the dispatch
record from the store and the file from its `records` directory: the member must be a current person member
(`unauthenticated:member_not_current`) whose scope covers one of the intake's projects (`unauthorized:no_project`,
as every read) and the run's own project, the one its contract reserved (`unauthorized:out_of_scope`); an unknown
run is `missing_evidence:unknown_run`, a cursor past the end `invalid_input:cursor_past_end`, a file bound to
another dispatch or contract `unknown_outcome:record_binding`, and once the dispatch has ended, a file whose line
count, size or digest differ from the committed ones `unknown_outcome:record_digest`. The answer carries the lines
after the cursor (at most 512), the next cursor, how many lines the file holds, the run's identity (unit,
station, project, account, host, state, process) and, once ended, the committed record. The API adds two routes
in its events family: `runs.record` (`GET /api/v1/domains/{domain}/runs/record?dispatch=&after=`, one page) and
`runs.record_stream` (`GET .../runs/record/stream?dispatch=&after=`, text/event-stream, `event: record`, each
frame's id its cursor, Last-Event-ID resuming). A stream is filled from its cursor at once, then on each record
hint (`ControlApi.deliver` hands a record hint to `deliver_record`), page after page to the lines the file holds;
it closes as `ended` once the run has ended and every line is out, and as a session's end closes the event stream
(`signed_out`, `session_expired`, `revoked`). The API process reaches the authority only over the service socket,
so the call is carried there too: `record` in `control_api_assertion.CALLS`, `ServiceApi._call` (bounds checked),
`ServiceAuthority.record`; the service configuration may name `records`.

**The stream options.** Claude Code's baseline gains `stream_options`: `--include-partial-messages` and
`--forward-subagent-text`, appended after the everything-off options. Both are read from the 2.1.281 bytes
(`proof/VELDO-0155/extract_baseline.py`, now reading them as two more switches, and
`proof/VELDO-0060/cli-options.json`): boolean options whose help says "only works with --print and
--output-format=stream-json", and whose check in the main action drops them with an error otherwise, which the
qualified flags satisfy; `--forward-subagent-text` forwards "subagent text and thinking blocks as assistant/user
messages with parent_tool_use_id set". `--verbose` was already a qualified flag. Both qualification records carry
the extended baseline, so VELDO-0155's check that the record's baseline equals the module's stays the one
qualification check; suite 80 now expects the two options after the others.

## What the code does that a reader should know

- **The scanner redacts most long absolute paths.** secret_scan's candidate class includes `/`, so an absolute
  path of 32 characters or more is one candidate token, and measured paths score 4.1 to 4.4 bits per character
  (`/home/dmitry/projects/veldo-worktrees/build-veldo-0141/src/main` 4.38), over the 4.0 threshold. So the record
  shows `[REDACTED:entropy]` for many file paths in tool inputs and results, the init event's working directory
  among them. The criteria say the scanner redacts high-entropy spans and this build does not change the
  scanner; it is the owner's call whether the terminal view should keep paths.
- **The planted resolver.** No resolver of a real credential exists in stage 1 besides the subscription token.
  The suite's planted resolver is a function a small driver adds to `RESOLVERS` in the receiver process before
  calling the installed `control_launch.main`, delivering its value as `V141_PLANTED`.
- **Wiring.** `record_hints` (receiver) and `records` (API service) are new configuration keys; the factory
  setup (VELDO-0139) does not write them yet. Without `records` the route answers
  `unavailable_service:records`; without `record_hints` a record is kept but the live route wakes only at a new
  request.
- **Finding 60's exit anchor.** The exit call gained the `execution_record` keyword on its next line;
  `claude-exit-artifact-unbound` now anchors on the call's first line and still drops only the artifact.

## Suite

`scripts/suites/82_veldo_0141_execution_record.py` (`python3 scripts/selftest.py --suite
82_veldo_0141_execution_record`). Real: a SQLite store with OpenSSH journal signatures; the owner's bootstrap
and a member of another project enrolled through control_membership's signed commands (the runner and the launch
receiver hold the reservation service role, which no membership command grants, as VELDO-0062's suites write
it); account records over profiles the helper prepares; VELDO-0036 reservations, VELDO-0052's Gate, VELDO-0031
claims, a Git source bound to the store, VELDO-0042 clones confined with Landlock, the VELDO-0039 Runner and
receiver processes, the trusted wrapper and VELDO-0040 transient scopes in a slice of the run's own; the
VELDO-0130 ControlApi and ApiAuthority (holding the authority's lock), passkeys registered through the API's own
ceremonies with an openssl P-256 key, enrolled by the steward's signed `enroll_api_credential` and signed in,
`control_client_api.Hints` receiving the receiver's record hints, `serve_stream` writing each stream, and
`ServiceAuthority.record` carried by `ServiceApi.call`. The engines are a fake `claude` pinned by the production
`pin` and a fake Codex vendor package qualified by the production `qualification`. Each prints only the binaries'
own shapes: VELDO-0062's `cli-formats.json` and this proof's `stream-formats.json` (`extract_stream.py`, from the
bytes: the `user` and `stream_event` message schemas read with VELDO-0062's own zod reader, the warning Claude
Code writes on its error stream when NODE_EXTRA_CA_CERTS names a missing file, the line `codex exec` writes on its
error stream when it reads its prompt from standard input, and Codex's ChatGPT login status line). Each really
runs its unit's commands and edits its file in the clone, and keeps its own copy of every line it printed on each
stream. The Claude Code fake prints partial messages only with `--include-partial-messages` and a subagent's text
only with `--forward-subagent-text`, as the binary does.

| Criterion | Rows |
|---|---|
| AC1 | `record/claude-complete` and `record/codex-complete` (declared falsifier), `record/stream-options` |
| AC2 | `api/live`, `api/cursor`, `api/refusals`, `api/no-secret-served` (declared falsifier), `api/service-call` |
| AC3 | `route/served-lines` (declared falsifier), `route/committed` |
| AC4 | `redaction/planted-value` (declared falsifier), `redaction/known-pattern`, `redaction/kinds-field`, `redaction/exact-set` |
| Fixtures | `fixture/planted-control`, `format/fake-lines` |

`record/*-complete`: the kept record against the engine's own copy, stream by stream: every output and
error-stream line in order and nothing else, the wrapper's identity line first naming the engine's pid, gapless
sequences, receive times in order. A kept line equals the printed one, or differs only in spans each of which is
what its marker names (a resolved value in a form a line carries it, a match of one of the scanner's patterns, or
a candidate-shaped span of at least the threshold entropy that is not a digest), matched by the suite from the
marker's kind, not by the production redactor. Claude Code's unit: a Bash command writing to both streams, a
failing command (an error result), an Edit, a Task subagent, a text message; the record holds every tool call with
its input and each result with the command's output and error stream, and the fake's own warning on its error
stream. Codex's unit: two command executions (one failing with its exit code), a file change, an error item, a
message, and its prompt line on the error stream. `record/stream-options`: the run's argv carries the three
options, each declared by the binary and listed by the baseline and the shipped record; the forwarded subagent
message and partial messages (one of them the subagent's) are in the record. `api/live`: the owner's stream,
opened as soon as the worker runs, received record frames before the exit was recorded, woken by at least two
hints, served every line once in sequence, and closed as ended; each frame's id is its cursor. `api/cursor`: a
stream resumed with Last-Event-ID at the middle serves exactly the rest; a page from the middle starts after it.
`api/refusals`: the outsider's page and stream refused `unauthorized:out_of_scope`; an unknown run and a cursor
past the end refused by name; a second session of the owner, following the live record, signed out while the run
wrote: its stream closed as `signed_out` and its next read is `unauthenticated:no_session`.
`api/no-secret-served`: every page and frame served of the planted run holds no part of any secret the run
printed. `api/service-call`: over the service call the owner gets the file's lines and the outsider the named
refusal. `route/served-lines`: the pages and the live stream serve exactly the kept lines, field for field; every
engine event served is the one printed. `route/committed`: after the run the route names it ended with the exit
record's committed count and digest, which the file matches; a line changed in place, or one line more, is
refused `unknown_outcome:record_digest`; the Codex run's file put in its place is refused as bound to another run
(`unknown_outcome:record_binding`), which is judged before the digest; the file is 0600 in a 0700 directory. `redaction/planted-value`: the
planted value (three low-entropy words, no pattern), printed alone in the command's output, inside it, on the
command's and the engine's error stream and joined to a high-entropy span, is replaced by
`[REDACTED:v141_planted]` exactly as often as it was printed on each line, no word of it survives, the joined
lines carry both markers, and the receiver's end event names the planted kind and the subscription token.
`redaction/known-pattern`: a GitHub-shaped token redacted as `pattern:github_token` in the messages and the error
stream; the account's subscription token replaced as `subscription_token`. `redaction/kinds-field`: each line's
`redacted` names exactly the kinds its markers name. `redaction/exact-set`: a low-entropy word no resolver named
is kept; every other line is the printed one with only redacted spans replaced. `fixture/planted-control`: the
planted value is one the scanner alone misses, and the scanner run first on the joined line takes the value's
first word with the span and leaves the rest, so the order decides the result; the token is one the scanner's
GitHub pattern finds. `format/fake-lines`: every event line the fakes printed has the binary's own fields and
required fields, Codex's items their table's fields, and the error-stream warning is the binary's text.

RUNS_LINE

## Red record

RED_LINE

## Mutations (finding 141)

Registered in `scripts/check_teeth_mutations.py`, each declared falsifier first; `drive.py` records
`mutations.json` and one applied diff per mutant. `check_teeth_mutations.py --finding 141 --jobs 2`: all
rejected.

| Mutant | Module | Named rows |
|---|---|---|
| record-error-stream-discarded (AC1 falsifier) | control_launch.py | record/claude-complete, record/codex-complete |
| record-served-unredacted (AC2 falsifier) | control_execution_record.py | api/no-secret-served |
| route-summarized-steps (AC3 falsifier) | control_api_authority.py | route/served-lines |
| redaction-scanner-first (AC4 falsifier) | control_execution_record.py | redaction/planted-value |
| record-stream-options-dropped | control_engine_claude.py | record/stream-options |
| record-hint-unsent | control_execution_record.py | api/live |
| record-wrapper-line-dropped | control_launch.py | record/claude-complete, record/codex-complete |
| record-exit-uncommitted | control_launch.py | route/committed |
| record-exit-unbound | control_dispatch.py | route/committed |
| route-digest-unchecked | control_execution_record.py | route/committed |
| route-binding-unchecked | control_execution_record.py | route/committed |
| route-scope-unchecked | control_api_authority.py | api/refusals, api/service-call |
| route-cursor-past-end-served | control_execution_record.py | api/refusals |
| route-record-hint-unrouted | control_api.py | api/live |
| route-service-call-unlisted | control_api_assertion.py | api/service-call |
| redaction-token-unresolved | control_launch.py | redaction/known-pattern |
| redaction-kinds-unnamed | control_execution_record.py | redaction/kinds-field |

## Not built (outside the criteria)

Retention, archival, replay and editing of a record, and the Mac leg (VELDO-0147 AC3). A record of a run whose
end is unknown carries no commitment (its dispatch has no exit record), so it is served with its state and
without a digest. A credential value containing a newline is replaced line by line only in its JSON-escaped form.
