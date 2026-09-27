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
the stream ends. Partial content blocks are parsed to redact spans crossing deltas; no line is merged, summarized or dropped.

**Redaction, before a line is kept.** `redact(text, resolved)` first replaces every value in the run's set of
resolved credential values (`Resolved`), longest first, in each form a line carries it (as printed, and as a JSON
string escapes it, ASCII-escaped or not), by `[REDACTED:<kind>]`; only then does secret_scan (its own
`PATTERNS`, `_CANDIDATE`, `_is_digest` and `shannon`, reused) replace its known patterns
(`[REDACTED:pattern:<shape>]`, the pattern's own description as a name, `pattern:github_token` for "a GitHub
token") and its high-entropy spans (`[REDACTED:entropy]`, a hex digest's shape excepted). Between the two, in the
engine's handshake answer and its init line only, the account identifiers are replaced by field
(`[REDACTED:account:<field>]` for `email`, `organization`, `accountUuid`, `organizationUuid` and their snake-case
forms, at any depth; a string's content, so the line stays JSON). The entropy step scores a path rooted at a
boundary (`/`, `~/`, `./`, `../`) segment by segment (split at `/`, a backslash and JSON's escaped forms of both)
and a URL (`scheme://`) by component (authority, each path segment, each query and fragment key and value), each
segment judged by the scanner's own rule, so only a segment that is itself high-entropy goes; a segment that is a
hex digest of a digest width named by a lowercase word (`clone-<32 hex>`, `sha256-<64 hex>`) is kept as the bare
digest is. A token naming a live path in the run's clone is kept whole by the entropy
step, with git diff prefixes removed for lookup and safe new leaves accepted under existing directories. Other slash-bearing tokens (including base64 values) and every other candidate are scored whole. The gate's own scan (`secret_scan.scan_text`) is untouched: this is
the record's own entropy loop. The set is filled once
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

- **Paths are scored by segment.** secret_scan's candidate class includes `/`, so judged whole an absolute path of
  32 characters or more scored 4.1 to 4.4 bits per character (`/home/dmitry/projects/veldo-worktrees/build-veldo-0141/src/main`
  4.38) and showed as `[REDACTED:entropy]`, the init event's working directory and tool inputs among them. On the
  lead's decision the record scores a rooted path by segment and a URL by component (above). What stays whole:
  a relative path with no root (`scripts/suites/x.py`), because a rootless slash-joined token is the shape of a
  base64 key such as a cloud secret key; and the scanner's gate scan. The initialize request id the receiver
  writes (`veldo-initialize-<16 hex>`, not a digest width) still scores high about three times in four and is
  replaced in the handshake answer.
- **Account identifiers.** Claude Code's handshake answer carries the account's email and organization (its
  Kfe(): `email:ie?.email,organization:ie?.organization`, proof/VELDO-0155's `input_protocol.account`); the record
  replaces them by field, and keeps the fields that say how the run logged in.
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
| AC4, redaction by component and field | `redaction/paths-kept`, `redaction/path-segment`, `redaction/url-component`, `redaction/account-fields` |
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
GitHub pattern finds. `redaction/paths-kept`: the live run's init line and Edit tool call are kept as printed,
the working directory (the clone under the runtime directory) and the absolute file path whole, each one the
scanner judging it whole replaces; typical real paths (the clone path, a clone directory named by a digest, a
worktree's `.veldo/control_launch.py`, a pinned engine path with its version and a bare and a named digest
segment, Codex's vendor binary path), alone, in a command and in a tool input, kept whole through the production
`redact`. `redaction/path-segment`: a path with an embedded 40-character random segment keeps the rest and
replaces that segment, alone, in a tool input and in a backslash path as JSON carries it; a resolved value inside
a path is replaced first, whole, and a high-entropy segment joined to it still goes. `redaction/url-component`:
a URL with a token query value keeps host, path and key and replaces only the value; a high-entropy URL path
segment goes; an ordinary URL is kept. `redaction/account-fields`: in both Claude runs (plain login and token
login) the handshake answer's email and organization are replaced by field and appear nowhere in the record, the
rest of `account` kept; an init line's account and organization uuid and email are replaced by field, its working
directory kept. `format/fake-lines`: every event line the fakes printed has the binary's own fields and
required fields, Codex's items their table's fields, and the error-stream warning is the binary's text.

Current suite: 53 passed (26 preamble, 27 rows), zero failures. All 95 suites selected through module
dependencies passed, and the 20 suites directly naming a changed module were repeated against the final
implementation with zero failures. Each used the selftest suite selector and returned its documented
partial-run status 2. [checks.json](checks.json) lists every suite and result. Repository validation passed;
the five changed engine modules are byte-identical to their installed copies. The repository gate was not
run, as instructed.

## Red record

`red-at-3c85f33b.json`: the current suite over `git archive 3c85f33b`, unchanged. All 25 behavior rows fail by
their own assertions (none raised): that tree's receiver discards the error stream and keeps nothing of a run,
its API has no record route and no record call, its dispatch commits no record and its Claude Code baseline has
no stream options. The two fixture rows are green there, as they must be.

## Mutations (finding 141)

Registered in `scripts/check_teeth_mutations.py`, each declared falsifier first; `drive.py` records
`mutations.json` and one applied diff per mutant. `check_teeth_mutations.py --finding 141 --jobs 2`: all 34
rejected, each on its named rows.

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
| redaction-path-scored-whole (the lead's falsifier: score the whole path again) | control_execution_record.py | redaction/paths-kept, redaction/path-segment, redaction/url-component |
| redaction-path-segment-unscored | control_execution_record.py | redaction/path-segment, redaction/url-component |
| redaction-named-digest-scored | control_execution_record.py | redaction/paths-kept |
| redaction-url-query-whole | control_execution_record.py | redaction/url-component |
| redaction-account-fields-kept | control_execution_record.py | redaction/account-fields |

## Not built (outside the criteria)

Retention, archival, replay and editing of a record, and the Mac leg (VELDO-0147 AC3).


## Review fixes, 2026-09-27

Local main at a4769f68 was merged before these fixes. Seven new rows join the original twenty.

| Row | What it proves |
|---|---|
| redaction/partial-blocks | Resolved and GitHub-shaped values split into 7-character text and 9-character tool-input deltas never survive in joined output; every affected line names its kind. Safe prefixes arrive before block stop; interleaved messages flush independently at message end. |
| redaction/clone-relative-paths | The tracked repository path corpus, git stat, git status, tracebacks and an untracked file survive whole. Root and cwd names both resolve; slash-bearing opaque values still redact; the initialize id survives. |
| redaction/encoded-values | Base64, URL percent encoding, URL plus encoding, uppercase and nested JSON strings receive the resolved kind. |
| api/scope-before-existence | Outsiders receive the same scoped refusal for present and absent dispatches, on page and stream routes. |
| api/registration-race | An end hint during the first page read or first fill still closes the subscription. |
| api/slow-reader | Frame and byte bounds close with `slow_reader`; queued frames remain a contiguous prefix and the last received cursor resumes without a gap. |
| route/unknown-committed | A real receiver with an uncertain containment observation commits its record; the authority rejects truncation, append and changed bytes. |

The recorder holds accumulated block text by session, parent message, message id, block index and delta
kind. It withholds at least the longest resolved form and the bounded scanner width. Since some scanner
patterns have no finite maximum, it also retains any open lexical candidate and incomplete pattern start.
A replacement intersecting several delta lines places the kind marker on every affected line. Original
receive times, order and byte counts survive buffering. The stream queue holds at most 32 frames and
4 MiB of serialized frame data. On overflow the client drains that prefix, receives `slow_reader`, and
reconnects with its last received cursor.

The receiver locates the clone root once. At redaction time it checks path membership live, relative to
both repository root and engine cwd, using directory descriptors and lstat without following symlinks.
Membership exempts only the entropy step: exact values and known patterns still redact.


The refreshed red records cover the original branch base (`red-at-3c85f33b.json`), the merged main base
(`red-at-a4769f68.json`), and the reviewed tree (`red-at-e9e418d8.json`). The two bases fail all 25 behavior
rows by assertion; the reviewed tree fails exactly the seven new rows by assertion. Fixture controls stay
green. The reviewer's original partial-message reproduction also reports neither planted value nor
GitHub-shaped value recoverable, with both redaction kinds on the affected lines.

The proof driver runs two isolated subprocesses at a time. Every baseline and module no-op is green;
every registered mutant is rejected by its named row, by assertion. The additional twelve mutations are:

| Mutant | Named row |
|---|---|
| record141-partials-line-by-line | redaction/partial-blocks |
| record141-partials-tail-too-short | redaction/partial-blocks |
| record141-clone-path-check-skipped | redaction/clone-relative-paths |
| record141-handshake-id-scored | redaction/clone-relative-paths |
| record141-stream-registers-after-fill | api/registration-race |
| record141-existence-before-scope | api/scope-before-existence |
| record141-reader-queue-unbounded | api/slow-reader |
| record141-encoded-forms-skipped | redaction/encoded-values |
| record141-unknown-record-unbound | route/unknown-committed |
| record141-unknown-record-uncommitted | route/unknown-committed |
| record141-receiver-clone-unlisted | redaction/clone-relative-paths |
| record141-concurrent-fills-interleave | api/registration-race |

The partial-block row additionally covers nonempty initial text, patterns and entropy candidates longer
than the fixed tail, and arbitrarily long whitespace in an assigned-value pattern. Encoded-value tests
include eight nested JSON layers; the exact set expands with observed escaping depth. A receiver row uses
a file present only in its bound clone, so falling back to the receiver's own directory is rejected. A two-thread fill test proves that a
concurrent hint cannot interleave the initial catch-up cursor or frames.


## Second review fixes, 2026-09-27

Six new rows exercise the findings from the review at 9dbda25f. All values used to test secret
redaction are generated at runtime. No credential value is retained in the proof.

| Row | Assertion |
| --- | --- |
| redaction/thinking-and-unknown | Seven-character thinking fragments redact both resolved and patterned values, including every affected fragment. An unknown delta with multiple string fields waits for block stop, then redacts each field. |
| redaction/live-paths | Git diff prefixes, files created after launch, truncated stat paths and safe new leaves survive; opaque slash-bearing values and symlink escapes do not gain path exemptions. |
| redaction/offset-encodings | Base64 values embedded after Basic auth and assignment prefixes at every byte alignment, plus lowercase hex, receive the exact resolved kind. |
| api/byte-pages | The authority splits 600 lines of 9 KB into pages below the byte budget, delivered completely without a slow-reader close. A single oversized line still advances the cursor. |
| api/fast-catchup | A fast reader drains during page reads and receives 100,000 lines in order without reconnecting. |
| route/runner-unknown | Both runner fallback outcomes commit the final record bytes; changing a byte causes the authority to refuse the record. |

The assembler collects every string field except the delta's type discriminator, keyed by message,
block and field. Known text, input JSON and thinking fields can release a safe prefix; unknown delta
types hold all their fields until the block ends. Each line retains all replacement kinds when several
fields are redacted. Base64 exact forms include the stable substring for all three byte alignments.

Path membership no longer enumerates the tree. Git's a/ and b/ prefixes are removed before checking.
Directory traversal uses directory descriptors with O_NOFOLLOW at every step. A missing leaf is accepted
only when its parent exists and the leaf itself does not score as high entropy, even below the
scanner's usual minimum token length. Git stat's three-dot
prefix is a path root, so each remaining segment is scored independently.

Record pages have a 1 MiB encoded-line budget and always contain at least one line when any remain.
The stream permits one oversized frame in an empty queue, so an oversized line cannot make every
reconnect fail at the same cursor. A dedicated fill lock serializes concurrent hints and catch-up;
page reads never hold the condition used by the reader to drain frames. The ordinary 32-frame and
4 MiB queue limits still close a reader that falls behind.

The runner reads the record only after stopping and reaping the receiver, then commits its byte count,
complete line count and SHA-256 for launch_evidence_missing and outcome_unknown. If the receiver died
before opening the record, the runner creates and commits an empty record bound to the dispatch.

The new finding-141 mutations are:

| Mutation | Row |
| --- | --- |
| record141b-thinking-unassembled | redaction/thinking-and-unknown |
| record141b-unknown-delta-released | redaction/thinking-and-unknown |
| record141b-diff-prefix-unstripped | redaction/live-paths |
| record141b-path-snapshot-restored | redaction/live-paths |
| record141b-short-leaf-unscored | redaction/live-paths |
| record141b-count-pages-restored | api/byte-pages |
| record141b-reader-locked-during-page | api/fast-catchup |
| record141b-runner-commitment-omitted | route/runner-unknown |
| record141b-offset-base64-omitted | redaction/offset-encodings |
| record141b-lower-hex-omitted | redaction/offset-encodings |

The current results are in [checks.json](checks.json), the mutation observations in
[mutations.json](mutations.json), and the reviewed tree's failing assertions in
[red-at-9dbda25f.json](red-at-9dbda25f.json). The required partial selftests are recorded as partial runs,
with their intentional exit code 2; no gate or verification stamp is claimed for this checkout.


## Clone leaf and uppercase hex regression fixes

Missing clone leaves must pass both whole-leaf entropy scoring and scoring of every scanner candidate
inside the leaf. The `redaction/clone-leaf-candidates` row generates a 36-character alphanumeric value
at run time and appends 30 dots. It requires redaction with clone paths set, then creates a file with
the same leaf and requires that real clone file name to remain readable. The
`record141c-leaf-candidates-unscored` mutation restores the whole-leaf-only check.

Resolved values include uppercase hex alongside lowercase hex. The `redaction/uppercase-hex` row
requires both cases to carry the resolved marker, and `record141c-upper-hex-omitted` removes the
uppercase form. Both new mutation names are unique across all findings.

[red-at-76510207.json](red-at-76510207.json) runs the current suite against the reviewed commit:
exactly these two rows fail, both by assertion. The refreshed [mutations.json](mutations.json) records
all finding-141 mutations and their controls. [checks.json](checks.json) records this review fix's
validation. The partial suite result carries its required exit code 2 and does not claim a gate run.


## Git boundary review fix

The recorder builds path membership from the receiver's known clone work root and the run's cwd.
The clone entrance supplies the dispatch record's work directory; direct launches may name a
containing `clone_root` in trusted receiver configuration. Without a supplied root, membership
uses cwd. It never starts Git or reads Git configuration to discover a root.

The new `redaction/clone-without-git` row covers a gitfile redirected outside the clone and a
planted fsmonitor command. It writes and reads execution records with generated high entropy file
names relative to both root and cwd, exercises the configured receiver root and cwd fallback,
spies on subprocess calls, and requires the marker to remain absent. The globally unique
`record141d-clone-git-discovery-restored` mutation restores the removed rev-parse call and must
fail this row. All existing clone_paths callers and mutation anchors use the new interface.

[git-boundary-review.json](git-boundary-review.json) records the full selftest, all finding-141
mutations, the Git boundary checker, validation, and engine copy comparisons for this fix.
The canonical gate was not run, and no verification stamp is claimed.


The first complete selftest found three VELDO-0041 failures: `retirement/live-descendant`,
`retirement/observations`, and `ran/retirement/live-descendant`. The first row deliberately invokes
an absent receiver configuration. Execution-record directory lookup raised FileNotFoundError before
normal launch settlement, which also prevented the dependent observation checks. The launcher now
lets an unavailable configuration follow the existing receiver failure path, retaining cleanup
obligations. The unchanged heartbeat suite then passed all 23 rows alongside all 36 record rows.
The validation record retains the initial failing result and the full rerun after this fix.


A second complete run passed those retirement rows but reported one intermittent failure in
VELDO-0068 `terminal/materialized-settlement`: acquisition returned no result for a late reply.
That unchanged row passed in the first full run and in an isolated rerun. Its cause was not
established. The validation record retains that failed run and the isolated result as well.

The final complete run passed all 6,896 assertions across 122 suites with zero failures. All 47 finding-141 mutations were rejected on the final implementation; the Git boundary checker and validator passed, and both changed engine copies matched byte for byte.

## Receiver configuration review fix

`invoke` loads the receiver configuration and resolves the execution-record directory before
`Popen`. Missing files, malformed JSON and configurations with no usable `records`, `state_root`
or `store` take the existing `receiver_unavailable` refusal path with no receiver child.
The record directory fallback order is unchanged.

Three new suite 82 rows assert the named refusal, zero receiver spawn calls and an unchanged
process census scoped to the suite's temporary tree. The census includes unreaped child PIDs;
cleanup happens after the assertions, including when a mutant leaks a receiver. `config/malformed`
uses malformed JSON generated at runtime, `config/incomplete` omits all three record-directory
keys, and `config/missing-file` names an absent file in that same temporary tree.

Finding 141 adds `record141e-config-catches-only-oserror` and
`record141e-config-read-after-spawn`. Finding 41 adds `retire41-config-oserror-unhandled`,
which removes OSError from the launch refusal handling and must fail the existing retirement row.
[receiver-config-review.json](receiver-config-review.json) records the checks for this fix.

The reviewed launch module at 7469b64a fails exactly the three new rows by assertion. Local main's
launcher and real receiver settle the same malformed, incomplete and absent configurations as
`receiver_unavailable`; that comparison uses an in-memory prepared-dispatch seam. The fixed suite
passes all 39 rows. Finding 141 rejects all 49 mutants, and finding 41 rejects all 35, including
`retirement/live-descendant`, `retirement/observations` and its completion assertion for the new
OSError mutant. All 1,912 mutation names are unique across findings. The whole selftest passed on
its first run with 6,899 assertions and zero failures across 122 suites; the worktree was not edited
while it ran. Git boundary checking and repository validation pass, and template sync compares
232 pairs successfully. The gate was not run and no verification stamp is claimed.
