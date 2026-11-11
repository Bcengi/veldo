# VELDO-0294 design: a build as short fresh phases, with a token record per run

Design for the spec at specs/VELDO-0294-builds-run-as-short-fresh-phases-with-per-run-token-records.md
(approved at a385da5e, amended at 3b6a5a0e). Revision 3 follows that amendment (section 12). Line
numbers are those of engine/.veldo at b1180439, where the files this design touches are unchanged
since 6ee5bb5f. Every engine/.veldo file named here has a synced copy under .veldo that changes
with it.

The design keeps the spec's shape: Runtime.build becomes a loop of build dispatches, the receiver
stops a run at its step cap and settles it in the ledger from what its meter saw, the stopped
clone's head is read as bytes, each settle writes one small token file, and the Telegram reporter
gains one event.

Two things the lead must know before the build starts:

1. A run stopped at its cap is settled at stop (AC10, sections 4.7 and 5.2a). The figures are lower
   bounds. A tokens cap can therefore be passed by what a stopped run used after its last counted
   line, and a Codex run stopped inside its first turn is settled with 0 tokens, because Codex
   prints a turn's usage only when the turn completes. The flag judges that figure, so such a run
   is not reported (D4, D15).
2. The ledger changes in one place only: it accepts and stores the settlement mark. Its caps and
   its admission check are not touched.

## 1. Components

| Component | File | Today | Change | Responsibility after the change |
| :- | :- | :- | :- | :- |
| Phase loop | control_launch_work.py, Runtime.build (238) | One payload, one _run call | Rewritten as a loop | Runs edit, test, proof in order; counts dispatches; advances the source commit; refuses phase_budget:build; returns the proof phase's result |
| Brief builder | control_launch_work.py, new function brief | Payload built inline (242 to 246) | New | Builds one dispatch payload from the loop state, applies the cuts and the size fit, refuses a skeleton that cannot fit |
| Preflight | control_launch_work.py, Runtime.limits | None | New | Validates the overrides and the worst-case brief skeleton before the first dispatch |
| Run step | control_launch_work.py, Runtime._run (142) | Refuses every run that did not complete | One exception added | Returns a capped build run to the loop instead of refusing it |
| Bound artifact read | control_launch_work.py, artifact (52) | Digest check and completion check in one function | Split in two | New function bound does the read, the digest check and the dispatch check; artifact calls it and keeps its completion check |
| Stop cause read | control_launch_work.py, new function stopped_by, beside answer (41) | None | New | Returns the stop cause of an artifact document by its engine: Claude Code exit.cause, Codex cause |
| Collector | control_launch_work.py, Runtime._collect (183) | Directory checks, then import of the commit the answer names | Split in three | _gitdir (the directory checks), _import (the object copy, the two fetches, the descent check, the scan), _collect (both, with the answer's commit) |
| Head reader | control_launch_work.py, new method Runtime._head and one private file reader | None | New | Reads the stopped clone's head commit id from regular files only; refuses invalid_input:build_head |
| Note reader | control_launch_work.py, new method Runtime._state | None | New | Reads proof/<unit>/phase-state.md at a commit in the authority's repository; returns the note or why it is missing |
| Cap check | control_launch.py, Metering.__init__ (2540) and Metering.feed (2603) | No cap of its own | Extended | Reads payload.phase.messages of a build contract; says when the run's step count has reached it |
| Stop cause | control_launch.py, take inside Receiver._reap (2316) | Every metering stop is usage_cap | Extended | Begins the stop with the cause Metering names: usage_cap or phase_cap |
| Settle | control_launch.py, Metering.settle (2684) | Writes the artifact, then sends the final report | Extended | Settles phase_cap as cancelled; for that cause sends the observed figures with the settlement mark; after the final report, writes the run token record and prunes |
| Observed figures | control_engine_claude.py and control_engine_codex.py, Meter | final gives figures only when the engine ended by itself | New method observed | What the meter saw up to the stop: tokens, messages, which of them are lower bounds, and the turns in flight |
| Report pass-through | control_reservation_runtime.py, InvocationGuard.observe (47) | Passes session and limit to the ledger's report | One optional argument added | Passes the settlement mark to the ledger's report |
| Settlement mark | control_reservations.py, Reservations.report (254) and the report action of _transition (374) | A final report may carry session and limit | One optional field added | Validates the mark, refuses a malformed one, stores it on the invocation record |
| Token record store | control_launch.py, new functions run_tokens_directory and run_tokens | None | New | One place that resolves the directory; one reader that returns the valid kept records newest first |
| Remote finish | control_launch.py, Receiver._finish (1626) | Stop causes requested and usage_cap | One name added | Treats phase_cap as a stop on a remote transport |
| Step count | control_engine_claude.py and control_engine_codex.py, Meter | cumulative and final only | New method steps (D1) | The live count the cap is compared with, defined per engine |
| Stop names | STOPS in both engine modules (claude 1215, codex 474) | No phase_cap | One name added | The artifact document gets verdict stopped and names the cause |
| Flag | control_telegram_report.py, REGISTRY (140) and new handler Reporter._run_tokens | No event reads the ledger | New event run_over_tokens | One report per settled run over the threshold or with tokens unknown; a run settled at stop is judged by its figure |
| Stand-in engine | scripts/suites/82_veldo_0129_worker_wiring.py | Does a whole build in one run; writes its output record only at a normal exit | Phase aware, with new fixture modes, and records as it goes | Answers per phase; can run on past the cap; can damage its own head or note; leaves its session id, commit and printed events behind when killed |
| Row prefixes | suites 82, 75, 72 | Each prints one hard-coded prefix (82: 740 to 746; 75: 1731 to 1739; 72: 1037 to 1043) | A row-to-prefix lookup | The ten new rows print VELDO-0294; every existing row keeps its prefix |
| Rows | suites 82, 75, 72 | | Ten new rows | Section 8 |
| Mutants | scripts/check_teeth_mutations.py | | Nineteen new cases | Section 8 |

Nothing changes in control_dispatch.py, control_clone.py, control_proof.py or dispatch.py. None of
them is in the footprint. In control_reservations.py the admission check (143 to 176), the caps and
the settling rule of a final report (399 to 414) stay as they are. A final report that carries
tokens and messages already takes both out of the record's unknown list today. What is new is that
the receiver sends such a report for a run it stopped at the cap, and that the report says the
figures are lower bounds.

### Component view

```
 AUTHORITY SIDE (the worker Runtime's process)            RECEIVER SIDE (one process per dispatch)

 Runtime.build  (phase loop)
   |  Runtime.limits: overrides and worst-case skeleton, before any dispatch
   |  state: phase, dispatch count, source commit,
   |         done list, remains, state note
   |
   +-> brief()  ..................  payload
   |
   +-> Runtime._run  ->  L.Runner.submit  ->  L.invoke  =====>  Receiver.launch
   |        |          (ledger admission, on settled figures)    |
   |        |                                                   Receiver._reap
   |        |                                                     |  take(chunk)
   |        |                                                     +-> Metering.feed
   |        |                                                     |     Meter.feed  -> ledger reports
   |        |                                                     |     Meter.steps -> cap reached?
   |        |                                                     +-> begin(usage_cap | phase_cap)
   |        |                                                     |
   |        |                                                   Receiver._finish
   |        |                                                     +-> Metering.settle
   |        |                                                     |     Metering._artifact -> artifacts/
   |        |                                                     |     Meter.observed (phase_cap only)
   |        |                                                     |     final report -> guard -> ledger
   |        |                                                     |       (phase_cap: figures + mark)
   |        |                                                     |     read back the committed record
   |        |                                                     |     run token record -> run_tokens/
   |        |                                                     |     prune run_tokens/
   |        |                                                     +-> Dispatches.exit (record: exited)
   |        |  <=== launch pipe: artifact report, exited ==========+
   |        |
   |        |  (all of the following before Runner.wait retires the clone)
   |        +-> bound()  reads the artifact document by path and digest
   |        +-> returned:   _collect  = _gitdir + _import(answer's commit)
   |        +-> phase_cap:  stopped_by() + _gitdir + _head + _import(head commit)
   |
   +-> Runtime._state  (git ls-tree and cat-file in the authority's repository)
   +-> Runtime.events  (one phase entry per dispatch)

 Reporter.run  (control_telegram_report, the channel's pass)
   +-> journal rows -> Reporter._run_tokens -> report run_over_tokens -> Telegram

 run_tokens(config)  reads run_tokens/  (no caller in this spec besides the suite)
```

The loop state lives only in the local variables of one Runtime.build call. Nothing new is stored
in the control store.

## 2. Constants and configuration

All in control_launch_work.py unless said otherwise.

| Name | Value | Meaning |
| :- | :- | :- |
| PHASES | edit, test, proof | The phase names in order |
| PHASE_MESSAGES | 80 | Default step cap of one dispatch |
| PHASE_DISPATCHES | 6 | Default number of dispatches one build may use |
| SOFT_MARGIN | 10 | phase.soft is messages minus this, and never below 1 |
| READING_RULE | Text, at most 110 bytes of ASCII | Read only the parts of a large file you need, by search and line range; never a whole large file |
| NOTE_RULE | Text, at most 200 bytes of ASCII | Keep the state note current in every commit, under its four headings; after phase.soft steps stop new work, commit and finish the note |
| OUTPUT | One text per phase, at most 340 bytes of ASCII each after the unit's path is filled in | What the phase returns (section 3.2) |
| CAPPED_NOTE | Text, at most 100 bytes of ASCII | The done note of a dispatch that hit the cap: it was stopped at the cap and its uncommitted work is lost |
| NOTE_PATH | proof/<unit>/phase-state.md, one path per unit | Where the builder keeps the state note |
| NOTE_BYTES | 8,192 | Largest note that is carried |
| BRIEF_BYTES | 4,096 | Largest payload without its spec text and state.note |
| REMAINS_LINES, LINE_CHARS | 10, 200 | The upper limits of the cuts on remains and on each done note |
| SETTLED_AT_STOP (control_reservations.py) | phase_cap | The stop causes whose final report may carry a settlement mark |
| RUN_TOKENS_SCHEMA (control_launch.py) | veldo.run_tokens/v1 | Schema of the token record |
| RUN_TOKENS_BYTES (control_launch.py) | 2,048 | Largest token record |
| RUN_TOKENS_DAYS (control_launch.py) | 30 | Age at which a record is removed |
| RUN_TOKENS_FLAG (control_telegram_report.py) | 15,000,000 | The flag threshold |

The byte limits on the texts are not in the spec. They are design constraints from the size
arithmetic in D5. The literal texts are written at build time; the row phase/brief asserts each
limit on the real constants, with the proof OUTPUT measured after the unit's path is filled in, so
a text that grows past its limit turns the row red.

NOTE_RULE names the unit the builder counts in: its own steps, which D1 defines per engine. The
builder is not told to count conversational turns against a budget of work items.

### Overrides and the preflight

A role may override two numbers in the worker configuration, under work.builder.phase: messages and
dispatches. Runtime.limits reads them and returns messages, soft and dispatches. It refuses
missing_authority:worker_configuration/build, the name Runtime.role already uses for a bad builder
role, before any dispatch is made, in each of these cases:

| Case | Detail of the refusal |
| :- | :- |
| phase is present and is not an object | phase |
| messages or dispatches is present and is not an integer (a boolean is not one) | the key's name |
| messages below 1 | messages |
| dispatches below 3 (a build cannot finish in fewer) | dispatches |
| The worst-case brief skeleton of this build does not fit BRIEF_BYTES | brief_bytes |

An absent phase object means the defaults.

The last case is the size envelope (D5). The worst-case skeleton is the payload the last allowed
dispatch could need with everything cuttable already cut: the proof phase, dispatches minus 1 done
entries each with an empty note, an empty remains list, state.missing with its longest value, and
the build's real producer, spec revision, unit and limits. It is measured the way section 4.4
measures a payload. With the default-size fixed fields and the text limits above, a done entry with
an empty note costs 79 bytes, so the preflight passes up to roughly 39 dispatches and refuses
beyond; an unusually long producer identity lowers that. There is no separate numeric maximum: the
measurement is the rule, and it runs once, before the first dispatch, so a build never discovers
part way through that its brief cannot be built.

The receiver configuration gains one optional key, run_tokens, a directory path. Absent, the
directory is run_tokens beside the store, the rule receipts (2593) and artifacts (2671) follow.

## 3. Interfaces

### 3.1 Functions

**brief(spec, spec_text, role, phase, limits, source, done, remains, state)** in
control_launch_work.py. Pure: no I/O, no Git. spec is the record Runtime.build receives (id, base,
revision, spec_path; it holds no text, executor.py 281 to 292). spec_text is the spec file's text,
which Runtime.build reads once with P.blob as it does today (241) and passes in. role gives the
producer identity. phase is the index 0 to 2. source is the commit this dispatch starts from. done
and remains are the lists so far. state is None for the first dispatch, otherwise what
Runtime._state returned. It returns the payload dict of section 3.2 after the cuts and the fit of
section 4.4, or refuses missing_authority:worker_configuration/build with the detail brief_bytes
when the skeleton cannot fit. The suite calls it directly for the oversized cases, without a
repository.

**Runtime.limits(spec, role)** returns the three numbers of section 2 or refuses, including the
skeleton preflight. It builds the worst-case skeleton through brief, so the measurement and the
real payload cannot drift apart.

**Runtime._run(unit, station, role, revision, payload, context)** keeps its arguments. It now
returns three values: the result (a dict, or None for a capped run), the reference and the ending,
which is the word returned or the word phase_cap. Both callers are updated together:
Runtime.build takes all three, Runtime.review (276) takes the first two and ignores the third. The
reference keeps dispatch and artifact and gains commit: the commit the dispatch ended on. For a
returned run that is the answer's commit. For a capped run it is the head commit read from the
clone, and there is no result to compare it with.

The decision inside _run, in this order, all inside the existing try block so that every read of
the clone happens before Runner.wait retires it (175 to 181):

1. The record completed (L.D.completed) and binds an artifact: today's path. The answer is parsed
   and, for a build, done is checked to be a boolean here (section 3.3) before _collect runs.
   Ending returned.
2. Otherwise, if the station is build, the record's state is exited, it binds an artifact, and
   stopped_by of the document that bound returns is phase_cap: the capped path. _run calls _gitdir,
   then _head, then _import when the head differs from the revision, and returns result None with
   the ending phase_cap.
3. Otherwise: today's refusal, unchanged (the record's refusal, or unknown_outcome:engine). A
   refusal the ledger made at admission arrives here under the ledger's own name.

**bound(record, reference)** is the first half of today's artifact function: read the file the
reference names, check its digest against the record's artifact digest and its dispatch id against
the record, refuse with today's names (the build and review names stay distinct, 54 and 60 to 64),
return the document. artifact(record, reference) becomes bound plus the completion check, so the
floor (dispatch.py 909) sees no change.

**stopped_by(document)** sits beside answer (41) and is engine aware the same way. For engine
claude_code it returns the document's exit.cause (control_engine_claude.py 1924 to 1925). For
engine codex it returns the document's cause (control_engine_codex.py 1061). For anything else it
returns None. There is no common path: a single top-level lookup would send every capped Claude
Code build down the refusal path. The suite reads stream lines the same engine-aware way: Claude
Code stream.lines, Codex lines.

**Runtime._gitdir(handle)** is lines 185 to 194 of today's _collect: it returns the clone's .git
path after refusing a symlink, a non-directory, commondir and the two alternates files. The three
forbidden entries keep their exists-without-following test, so a dangling link still refuses.

**Runtime._import(gitdir, commit, revision)** is lines 198 to 236 of today's _collect, unchanged in
behavior: copy the object files, fetch into the authority's temporary repository, require the commit
to exist and to descend from revision, fetch into the authority's repository, run the candidate
scan. It keeps today's refusal names. A failed fetch refuses as today; the design promises no
recovery from every interrupted object layout.

**Runtime._collect(handle, result, revision)** is _gitdir, the check that the answer's commit is a
commit id, then _import. Same behavior as today.

**Runtime._head(gitdir)** returns a commit id of exactly 40 lowercase hex characters or refuses
invalid_input:build_head. The rules are section 4.5. It never runs Git. Every file it reads, it
reads through one private reader that holds all the link defenses. The old collector's own check
(P._hex) also accepts 64-character ids; _head is narrower on purpose, because the spec fixes 40.

**Runtime._state(commit, unit)** returns a dict with exactly one key: note (the text) or missing
(absent, oversize or not_a_file). It runs Git only in the authority's own repository, on a commit
that _import has already fetched there. Steps: list the tree entry at the unit's NOTE_PATH in the
commit; no entry means absent; an entry whose mode is not a regular file (100644 or 100755) means
not_a_file, which covers a symlink, a directory and a submodule; ask Git for the blob's size and
return oversize above NOTE_BYTES without reading it; read the blob as bytes, with no newline
conversion; decode strictly as UTF-8, never with replacement, and return not_a_file when that
fails (D9). A missing or damaged note refuses nothing. A failure of Git itself (it cannot run, it
times out, it exits with an error on a commit that was just imported, or its size answer is not a
number) is not a missing note: _state refuses binding_mismatch:build_commit with the detail
state_note, the name _import uses when an imported commit cannot be found.

**Metering.capped** (new attribute) and **Metering.stop_cause()** (new method) in control_launch.py.
Metering.__init__ keeps a cap only when all of these hold: the contract's station is build, the
payload is a dict, phase is a dict, and messages is an integer (not a boolean) of at least 1.
Otherwise there is no cap, so a review or coordination run is never capped even if its payload
carried a phase. Metering.feed first passes the chunk's observations to the ledger as today, then,
whether or not the chunk produced any observation (a Codex item produces none), sets capped when a
cap exists and Meter.steps() is at or above it. feed returns true when either stop or capped is
set. stop_cause returns usage_cap when stop is set and phase_cap otherwise, so a ledger cap wins
when both happen in one chunk. The login and configuration stops that take checks first keep their
priority.

The check runs once per chunk, not once per line. The receiver reads up to 65,536 bytes at a time
(2361) and the meter consumes every line of a chunk before feed compares, and output still in the
pipe after the stop is metered too (2423 to 2429). So the guarantee is: the stop begins at the
first chunk boundary at or after the step that reached the cap, and the final step count of a
capped run is at least the cap. It is not exactly the cap, and no row may assert that it is.

**take(chunk)** inside Receiver._reap begins the stop with metering.stop_cause() where it says
usage_cap today (2322). begin already ignores a second cause.

**Meter.steps()** in both engine modules returns an integer that only grows while the stream is
read. The definition is per engine (D1):

| Engine | A step is | Not a step |
| :- | :- | :- |
| Claude Code | One distinct assistant message id that carries readable token usage: the size of the meter's message map (1120 to 1130). Messages of nested work are counted, as the ledger counts them today | A repeat of the same id; an assistant event with no id or no readable usage; the result line's turn count |
| Codex | One distinct item id seen on item.completed whose type is agent_message, command_execution, file_change, mcp_tool_call, web_search or collab_tool_call | item.started and item.updated; a repeat of the same id; items of type reasoning, todo_list or error; turn events |

The ledger's messages keep today's meaning in both engines. Meter.cumulative and Meter.final do not
change.

**Meter.observed()** in both engine modules returns what the meter saw, for a run that was stopped.
It is called after Meter.close. It returns three things:

| Key | Claude Code | Codex |
| :- | :- | :- |
| usage | tokens and messages of Meter.cumulative: the latest usage of each distinct assistant message id, summed, and the number of those ids (1092 to 1099) | tokens and messages of Meter.cumulative: the usage of the completed turns, summed, and their number (343 to 344) |
| lower_bound | The units Meter.final does not give: both when no result line was read, tokens alone when the result line had no token total, none when it had one | Both, unless every turn that opened also completed with valid usage; then none |
| in_flight | None. The stream does not show a request in flight | 1 when a turn was open or broken at the stop, else 0 |

A Codex turn in flight has printed no usage, so its lower bound is 0 tokens and nothing is added
for it; in_flight says that the turn existed. Meter.cumulative, Meter.final and the live reports do
not change.

**Metering.settle(termination, cause)** adds phase_cap to the causes at 2702, keeping the deadline
and account-limit precedence. Its order stays as it is today and gains three steps:

1. Close the meter, decide the outcome, write the artifact (Metering._artifact, 2708). The artifact
   is written before the final report, today and after this change.
2. New: when the cause is phase_cap and the outcome is cancelled, the usage of the final report is
   Meter.observed's usage with invocations and wall_seconds, and the report carries the settlement
   mark of section 4.7. For every other cause, and for a run its deadline stopped, the usage is
   Meter.final's, as today, and there is no mark.
3. Send the final report to the ledger (guard.observe, 2713), catching what it catches today.
4. New: read back the invocation's record and, when it holds a committed final report, call the new
   private method Metering._record(record, outcome, now).
5. New: prune.

Section 4.2 gives the record and the rule of step 4. Section 6 gives the failures. Metering._record
is not Receiver._record (1374).

**InvocationGuard.observe(..., settlement=None)** in control_reservation_runtime.py passes the mark
to Reservations.report when it is given, the way it passes session and limit (57 to 60). Nothing
else in the guard changes.

**Reservations.report(..., settlement=None)** in control_reservations.py refuses invalid_input, the
name it already uses for a malformed report, unless all of these hold: the report is final; its
outcome is cancelled; its usage carries tokens and messages; the mark is an object with exactly the
keys at, cause, lower_bound and in_flight; at is the word stop; cause is in SETTLED_AT_STOP;
lower_bound is a list without repeats drawn from tokens and messages; in_flight is None or an
integer of at least 0 (a boolean is not one). The mark goes into the report's payload. The report
action stores it on the invocation record as settlement, the way it stores session and limit (395
to 398). The rest of the action is today's: the figures raise the charge, a final report takes
each unit it carries out of the unknown list, and the record's state becomes settled.

The mark gives the receiver no new power. A final report with tokens and messages settles a record
today, whoever sends it under the receiver's authority. The mark makes a lower bound visible as
one, where without it the figures would read as a total.

**run_tokens_directory(config)** in control_launch.py returns the configured path or run_tokens
beside the store. Metering._record, the pruning and run_tokens all call it, so the rule exists once.

**run_tokens(config)** in control_launch.py returns a list of record dicts, newest ended_at first,
ties ordered by invocation. A file counts as a record only when it can be read, is a JSON object,
has the right schema, has ended_at as a number (not a boolean), has invocation as text, and has
tokens and messages each a number or null. Every other file is skipped. A directory that does not
exist gives an empty list. The reader never raises on a file's content.

**Reporter._run_tokens(eid, entry, prior, state)** in control_telegram_report.py has the signature
of every REGISTRY handler and returns a fact dict or None. REGISTRY gains the row run_over_tokens,
listening to the kind subscription_reservation. Section 4.6 gives its rule and text.

### 3.2 The brief: payload fields

| Field | Type | Value | First dispatch |
| :- | :- | :- | :- |
| operation | text | build | same |
| spec | text | spec_text: the spec file at the spec's base, as today | same |
| spec_revision | text | As today | same |
| producer | text | The builder's identity, as today | same |
| phase | object | name, index (1 to 3), of (3), messages, soft | name edit, index 1 |
| source | object | commit: the commit this dispatch starts from, equal to the contract's source commit | the spec's base |
| done | list | One entry per ended build dispatch of this build, oldest first: phase, commit, note | empty list |
| remains | list of text | What the last returned phase said is left | empty list |
| reading | text | READING_RULE | same |
| note | text | NOTE_RULE | same |
| output | text | OUTPUT of this phase | edit's text |
| state | object | note (the whole state note) or missing (absent, oversize, not_a_file); never both | not present |

All of these travel inside the contract's input payload; no contract field is added.

No field named resume exists. So control_reservation_runtime.boundary never answers follow_on, and
Metering, which only does the accounting of a resumed session (2550 to 2554), never treats a phase
as one. The absence of the key is not by itself proof that the CLI started a fresh session; the row
phase/fresh-dispatches proves that from the session ids the engines report.

The key note appears three times with three meanings: at the top level it is the rule, in a done
entry it is that dispatch's one-line summary, and under state it is the builder's file. The spec
fixes all three names and the rows compare them, so the design keeps them.

OUTPUT, per phase, in words:

- edit and test: return JSON with commit (the last commit you made, or your source commit if you
  made none), done (true when this phase's work is finished, false when it is not), note (one line
  on what this run did) and remains (a list of lines on what is left). Do not change the
  specification.
- proof: today's instruction (commit implementation and evidence, then the veldo.proof/v1 manifest
  at proof/<unit>/manifest.json in a second commit, return that commit and the proof), plus two
  things: delete proof/<unit>/phase-state.md in the commit that adds the manifest, and return done
  true. This instruction takes precedence over NOTE_RULE for that last commit.

### 3.3 The answer a phase returns

The spec names commit, done and remains and leaves the rest open (D6). The design fixes it:

| Key | Required | Rule |
| :- | :- | :- |
| commit | yes | A commit id; _collect imports it and requires it to descend from the dispatch's source commit. Equal to the source commit is allowed and means no commit was made |
| done | yes | A boolean, checked in _run before the commit is collected. Anything else refuses missing_evidence:build_result, the existing name for an answer that is not usable |
| note | no | Text. Missing or not text becomes an empty note |
| remains | no | A list. Entries that are not text are dropped. Missing or not a list becomes an empty list |
| proof | proof phase with done true | As today: a dict whose spec_revision equals the spec's, else missing_evidence:build_proof. Deeper proof checks stay with the floor |

Only done is strict, because only done changes what the loop does next.

### 3.4 Runtime.events

_run keeps appending its entry for every returned run, unchanged (operation build or review, outcome
artifact). Runtime.build appends one more entry per build dispatch, returned or capped, so a capped
dispatch, which has no artifact entry, still leaves one:

| Key | Value |
| :- | :- |
| operation | phase |
| unit | The spec id |
| phase | The phase name |
| index | 1 to 3 |
| dispatch | The dispatch id |
| identity | The builder's identity |
| source | The commit the dispatch started from |
| commit | The commit it ended on |
| ended | returned or phase_cap |

The list is in memory, like today's. It is not durable state.

## 4. Data model

### 4.1 The state note

| Property | Value |
| :- | :- |
| Path | proof/<unit>/phase-state.md in the builder's clone, committed |
| Written by | The builder, in every commit it makes (NOTE_RULE) |
| Content | UTF-8 text under four headings: done, left, decisions made, approaches tried and rejected |
| Bound | 8,192 bytes; a larger note is not carried and the next brief says oversize |
| Read by | Runtime._state, from the commit a dispatch ended on, after that commit is in the authority's repository |
| Carried as | state.note, whole. The bytes are read without newline conversion and decoded strictly, so the text encodes back to the same bytes |
| Lifetime | Deleted by the proof phase in the commit that adds the manifest. This is an instruction; nothing checks the deletion |

The headings are an instruction to the builder. Nothing parses the note.

### 4.2 The run token record

One file per settled subscription invocation, in the run_tokens directory (mode 0700). The file name
is the sha256 hex digest of the invocation id plus .json, the naming artifacts use. Mode 0600. At
most 2,048 bytes. One JSON object:

| Field | Source |
| :- | :- |
| schema | veldo.run_tokens/v1 |
| dispatch | The contract's dispatch id |
| invocation | Metering.invocation |
| unit | The contract's unit |
| station | The contract's station |
| phase | payload.phase.name when the payload has a phase object with a text name, else null (review, coordination) |
| attempt | The contract's attempt |
| account | The contract's reservation account |
| provider | The engine's PROVIDER |
| boundary | Metering.boundary |
| tokens | The tokens value of the charge of the ledger's invocation record, or null when the charge holds none |
| messages | The same rule, for messages |
| wall_seconds | The charge's wall_seconds |
| outcome | The outcome of the committed final report |
| ended_at | The time settle took for its final report (its now), in seconds since the epoch |

Absent and zero are different: the charge is read with a lookup that returns nothing for an absent
key, and a real zero is written as 0. A run that was never executed has a charge of all zeros by
the ledger's own rule, and its record says 0, truthfully. A capped run's record carries its settled
figure, which is the charge. The token record does not carry the settlement mark; AC4 fixes its
fields, and a reader who needs to know whether a figure is a lower bound asks the ledger.

**When a record is written.** The numbers come from the ledger, never from the meter. After the
final report call returns, whether it returned normally or raised, Metering reads the invocation's
record the way InvocationGuard.observe does (the reservations' record map, the entry of type
invocation with this invocation id and domain; control_reservation_runtime.py 61 to 63). The record
is written when that entry holds a report at settle's sequence that is final. This matters because
observe commits the report first (57 to 60) and can raise afterwards, during its policy reads (61
to 88): an exception does not mean that nothing committed. When no final report at that sequence
is there, or the read itself fails, no record is written and the error is named (section 6).

**How it is written.** To a temporary name in the same directory, then renamed, so a file under its
final name is always whole. A rename replaces a file already at that name. That can only be an
earlier record of the same invocation, since the name is the invocation's digest, and settle runs
once per invocation (2686 to 2688). A record that would be over 2,048 bytes is not written: the
contract's own text fields (unit, account, dispatch id) have no length limit the receiver enforces,
so the bound is a named failure for an oversize record, not a promise that every record fits.

**Pruning.** On every settle, each file in the directory that is a valid record (by run_tokens'
rule) is removed when its ended_at is more than 30 days before settle's now. A file that is not a
valid record is removed when its modification time is that old. A leftover temporary file follows
the second rule.

### 4.3 The done list and the remains list

Both live in the loop's local variables and in the payloads built from them. Neither is stored
anywhere else.

A done entry has three keys: phase (the phase name of that dispatch), commit (the commit it ended
on) and note. For a returned dispatch the note is the answer's note and nothing else of the answer.
For a capped dispatch it is CAPPED_NOTE. This is where the brief says that uncommitted work was
lost.

remains is the list the last returned answer gave. After a capped dispatch the list is left as it
was, since a capped run returns nothing, and the state note of its last commit is the fresher
source.

### 4.4 Cuts and the size fit

brief applies these in order:

1. remains is cut to at most its first 10 lines, and each line to at most its first 200 characters.
   This is one step at one place.
2. Each done note is cut to at most its first 200 characters.
3. The payload without spec and without state.note is encoded with P.canonical (compact, sorted,
   ASCII escaped) and measured in bytes. While it is over 4,096: empty the oldest done note that is
   not yet empty; when all are empty, drop the last remains line; when remains is empty too, stop.
4. If the payload is still over 4,096 bytes after step 3, brief refuses
   missing_authority:worker_configuration/build with the detail brief_bytes. It never loops on
   lists that are already empty and never returns an oversize payload.

phase, source, reading, note, output, producer, spec_revision and the phase and commit of each done
entry are never cut. They are the skeleton, and step 4 is what happens when the skeleton alone is
too large. Because Runtime.limits measured the worst-case skeleton of this build before the first
dispatch (section 2), step 4 cannot be reached from the loop. It exists for a direct caller.

So the bound is a validated envelope, not an unbounded guarantee: every brief the loop sends is at
most 4,096 bytes, and a configuration whose briefs could not be is refused before it spends a
dispatch. The limits of steps 1 and 2 are upper limits; step 3 may leave fewer lines and shorter
notes (D5). Characters and bytes differ: a character outside ASCII costs six or twelve bytes
escaped, and a quote or backslash two, which is why the fit measures bytes after encoding.

The state note and the spec text are outside the bound, as the spec says.

### 4.5 Reading the head of a stopped clone

Runtime._head runs only after _gitdir has passed and only for a record in state exited. A record
reaches that state only when the worker's containment group is empty (Receiver._finish records
unknown otherwise, at 1632), so nothing is writing the clone while it is read. This holds for the
installed local clone; Runtime.role refuses any other adapter.

Every rule below that fails ends in the one refusal invalid_input:build_head. The reason goes in the
refusal's detail, not in its code, so the row can compare the code exactly.

**The file reader.** One private reader takes a path and a byte limit and holds every defense: a
status call that does not follow links must say regular file; the open uses the no-follow flag; the
status of the open descriptor must say regular file again; the size must be at most the limit. A
file over the limit refuses. The reader never returns a valid-looking prefix of a longer file. HEAD
and the ref file are read by two separate calls of this reader, each its own statement, so each can
be replaced on its own by a mutant (section 8).

1. .git/HEAD is read with the reader, limit 1,024 bytes.
2. Its content, less one trailing newline, is either a commit id of exactly 40 lowercase hex
   characters, which is the answer, or the text ref: refs/heads/<name>. Anything else refuses,
   including a ref outside refs/heads.
3. <name> must be at most 255 characters and made of path components joined by a slash. Each
   component holds only letters, digits, dot, underscore and hyphen, is not empty, does not start
   with a dot and does not end in .lock. This keeps the path inside .git/refs/heads.
4. Every directory on the way from .git to the ref file (refs, refs/heads and any directory inside
   <name>) that exists must be a real directory by a status call that does not follow links. A
   link or a non-directory there refuses (D8). A directory that does not exist means the loose ref
   does not exist, and rule 6 applies.
5. If anything exists at .git/refs/heads/<name>, by a test that does not follow links, it is read
   with the reader, limit 1,024 bytes, and must hold exactly 40 lowercase hex characters and at
   most one trailing newline. A link, a dangling link or anything else there refuses; it does not
   fall through to packed-refs.
6. If nothing exists there, .git/packed-refs is read with the reader, limit 1 MiB. Comment lines
   and peel lines are skipped. Exactly one line must name refs/heads/<name>, and the id on that
   line must be exactly 40 lowercase hex characters; it is the answer. No such line, more than
   one, or a malformed id refuses.

The id is then handed to _import with the dispatch's source commit. _import requires the commit to
exist in the copied objects and to descend from the source, whatever file the id was read from. A
crafted HEAD, ref or packed-refs line can name any id, and an id that is not a descendant of the
source is refused by the same check that guards a returned commit (binding_mismatch:build_commit,
D7). When the head equals the source commit, _import is skipped: the phase made no commit, and the
source is a commit the authority already holds.

### 4.6 The flag

Reporter._run_tokens looks at a journal change to an entity of kind subscription_reservation. The
entry and the prior value are decoded the way the other handlers decode theirs.

It returns a fact only when all of these hold: the record's type is invocation; the record after
the change holds a final report; the record before the change held no final report at any
sequence. The last condition is on the record's whole report history, not only on its latest
report, because the ledger accepts a later non-final report after a final one (control_reservations
378 to 414), and a rule that looked only at the latest report could fire a second time. A report is
also recorded under an id made of the event, the domain, the repository, the owner, the journal
sequence and the source entity (report_id, 223 to 226), so a second pass over the same journal row
sends nothing more. The two rules together give at most one report per invocation.

Then (D4):

| Case | Result |
| :- | :- |
| The outcome is not_executed | None. The ledger settles such a record with all usage zero and nothing unknown |
| tokens is in the record's unknown list | Fact: tokens unknown. When the charge holds a live figure the text adds "at least" and the figure |
| The record carries settlement, and its tokens are above RUN_TOKENS_FLAG | Fact: over the threshold. The text says "at least" before the tokens |
| The record carries settlement, and its tokens are at or below RUN_TOKENS_FLAG | None |
| tokens is known, with no settlement, and above RUN_TOKENS_FLAG | Fact: over the threshold |
| tokens is known, with no settlement, and at or below RUN_TOKENS_FLAG | None |

"Unknown" is the ledger's word: the unit is still in the record's unknown list after its final
report. A run settled at stop is not in that state, so a capped run is not reported for being
capped. A run that ends at its deadline, or whose stream ends without a total, is still unknown and
is still reported.

The fact has the keys every handler returns: unit (the record's context unit), run (the record's
dispatch), project (the context project), headline, fact, next and evidence (None). The fact text
names the unit, the dispatch, the tokens, the messages and the threshold. The unknown text says the
tokens are unknown and gives the messages if the ledger has them.

The flag reads the ledger, not the token file, so a token file that failed to write does not
silence it.

### 4.7 Settlement at stop

The settlement mark is one object. It travels in the final report's payload and is stored on the
ledger's invocation record under the key settlement. Nothing else stores it.

| Key | Value | Meaning |
| :- | :- | :- |
| at | stop | The record was settled because Veldo stopped the run, from what the meter had seen |
| cause | phase_cap | Why Veldo stopped it. SETTLED_AT_STOP holds the causes the ledger accepts |
| lower_bound | A list drawn from tokens and messages | The units whose figure in the charge is a lower bound and not a total |
| in_flight | None, or an integer | Codex: the turns open at the stop, 0 or 1, for which no usage was printed. Claude Code: None |

The figures themselves are not in the mark. They are the tokens and messages of the final report's
usage, and the ledger keeps them in the record's charge, where balances, caps and windows already
read them. So the record of a run settled at stop looks like this: state settled, an empty unknown
list, outcome cancelled, the charge holding the observed tokens and messages, and settlement saying
which of the two are lower bounds.

How a lower bound is shown. In the ledger: the unit's name in settlement.lower_bound. For a Codex
turn in flight: settlement.in_flight is 1, and the bound for that turn is 0 tokens, which is why
nothing was added. In the Telegram report: the words "at least" before the figure (section 4.6).
The run token record shows the figure alone.

What the figures leave out. For Claude Code: a request that was in flight at the stop, and any
usage of a message whose line never reached the receiver. For Codex: the whole turn in flight. A
Codex run stopped inside its first turn has no completed turn, so its settled tokens and messages
are 0, both named as lower bounds, with in_flight 1. That is the smallest figure the ledger can
hold, and it is what the owner's decision gives such a run: the ledger admits the continuation, and
the flag, which judges the figure, stays quiet. The step cap bounds what such a run can have used,
since it was stopped after at most the cap's steps and the output already in the pipe.

## 5. Data flows of one build

In every flow the dispatch itself is today's path: Runtime._run asks the gate, L.Runner.submit asks
the ledger for admission and prepares a contract with the next attempt number, the clone is made at
the contract's source commit, the receiver runs the engine, settles and records the exit.

### 5.1 First phase

1. Runtime.build takes the role, reads the spec text at the spec's base, takes the limits (which
   includes the skeleton preflight), and sets phase edit, dispatch count 0, source commit the
   spec's base, done and remains empty, state none.
2. brief builds the payload with phase edit, index 1, source.commit the base, and no state field.
3. _run dispatches it. The clone is at the base. The engine starts a new session.
4. The builder edits, commits with the state note, and answers with commit, done, note, remains.
5. The run completes. _run takes path 1: it checks done is a boolean, and _collect imports the
   commit into the authority's repository.
6. The loop reads the note at that commit with _state, appends the done entry, takes the answer's
   remains, sets the source commit to the answer's commit, appends the phase event, and counts the
   dispatch. done true moves it to phase test; done false keeps it in edit.

### 5.2 A phase capped at the step limit

1. The payload carries phase.messages (80 by default). Metering keeps it as the cap, because the
   station is build.
2. Each chunk of the engine's stream goes through take, Metering.feed and the engine's Meter. At
   the end of the first chunk in which Meter.steps() is at or above the cap, feed returns true and
   stop_cause says phase_cap.
3. take begins the stop with that cause. The stop is today's: a termination signal to the engine's
   process, then to its group, then a kill, on the configured graces. Output already in the pipe is
   still metered, so the final count can pass the cap.
4. Receiver._finish calls Metering.settle with the cause. The outcome is cancelled. The artifact
   document is written with verdict stopped and the cause phase_cap, and is not complete. Then the
   final report goes to the ledger with the figures Meter.observed gives and the settlement mark.
   The ledger takes tokens and messages out of the record's unknown list and the record is
   settled. Then the token record is written from the committed record. The dispatch record is
   exited with the artifact's digest.
5. In _run the record is not completed. Path 2 applies: bound returns the document, stopped_by
   says phase_cap, _gitdir passes, _head reads the head commit, _import brings it into the
   authority's repository when it differs from the source. All of this is inside _run's try block,
   before the clone is retired.
6. The loop gets ending phase_cap and the head commit. It appends a done entry with CAPPED_NOTE and
   that commit, leaves remains as it was, reads the note at the head commit, sets the source commit
   to the head commit, appends the phase event with ended phase_cap, counts the dispatch and stays
   in the same phase.

### 5.2a Admission of the next dispatch after a cap

The capped run's invocation record is settled, with nothing unknown. The ledger's admission check
(control_reservations 143 to 176), unchanged, then decides the next invocation on the figures:

| Policies that match the unit's context | Next dispatch |
| :- | :- |
| No cap on tokens or messages and no window in those units | Admitted. The phase continues as in 5.3 |
| A cap on tokens or messages, with the balance under it | Admitted |
| A cap on tokens or messages, with the balance at or over it | Refused usage_cap, naming the scope and the unit. The cap is really used up |
| A window whose unit is tokens or messages, with room left | Admitted |
| Such a window with no room left | Refused window_exhausted |

At 6ee5bb5f the second and fourth rows are refusals: a stopped run leaves tokens and messages
unknown, and the ledger refuses unknown_allowance or unknown_window_usage (suite 75's rows at 1434
to 1483). The row phase/settled-at-stop pins the new behavior for both.

A refusal in the third or fifth row reaches _run as path 3 and Runtime.build stops with it, under
the ledger's name. Nothing is retried. The capped run's commits are already imported.

Because the figures are lower bounds, the balance the ledger compares is a lower bound too. A cap
on tokens can be passed by what stopped runs used after their last counted line. With Claude Code
that is the requests in flight at the stop. With Codex it is the turn in flight (section 4.7).

### 5.3 The next phase from the state note

1. The loop builds the next payload. source.commit is the commit the dispatch before ended on. done
   has one more entry. state carries the note read at that commit, or the reason it is missing.
2. _run dispatches it with that commit as the revision. The contract's attempt is one higher. The
   clone is new and at that commit, so the note file is also on disk for the builder. The engine
   session is new.
3. The builder starts from the brief: the spec, the done list, remains, the state note. It has no
   earlier conversation.

### 5.4 The last phase

1. The proof phase's payload carries the proof OUTPUT text.
2. The builder writes the evidence, commits, writes the manifest, deletes the state note in the
   manifest's commit, and answers with commit, proof and done true.
3. _collect imports the commit. The loop checks the proof as today (a dict whose spec_revision
   matches) and leaves the loop.
4. Runtime.build makes the candidate checkout of that commit and returns what it returns today: the
   result with ok, producer, the dispatch and artifact of this last dispatch, and the workspace.
5. The floor is unchanged. _build_dispatch takes the unit's newest build dispatch, which is this
   one and exited cleanly, and compares its answer's commit and proof with the bundle.

A proof phase that answers done false, or is capped, repeats like any other phase while dispatches
remain.

### 5.5 A build refused at the dispatch limit

The check is at the top of the loop, before a payload is built: if the dispatch count equals
limits.dispatches, Runtime.build refuses phase_budget:build with the current phase's name in the
detail. With the AC6 set (cap 5, 4 dispatches, a stand-in that never ends) dispatches 1 to 4 are all
edit and all capped, the fifth pass through the loop refuses naming edit, and no fifth dispatch
record exists. Commits the capped runs made stay in the authority's repository without a ref, like
any unaccepted build's commits today. The count is local to one Runtime.build call. A build can
also end sooner than its budget, when a cap or a window is used up (5.2a).

### 5.6 A run flagged over the token threshold

1. Metering.settle writes the artifact and sends the final report. The ledger commits it: one
   journal row changing the invocation's subscription_reservation record.
2. settle reads the record back, writes the token record and prunes.
3. On the channel's next pass, Reporter.sources walks the journal rows after its cursor. The row
   reaches _run_tokens, which finds a final report where the record before had none, and a charge
   above 15,000,000 or tokens still unknown, and returns the fact. For a record settled at stop
   the charge is the settled figure.
4. Reporter.report stores the report intent, renders and sends it. A later pass finds the report
   recorded and sends nothing, whatever the outcome of the first send, as for every other event.

A run under the threshold with known tokens produces no fact, so nothing is sent and nothing is
recorded.

### Sequence: one capped phase and its continuation

```
 Runtime.build      Runtime._run       Receiver / Metering        Engine           Ledger
      |                  |                     |                    |                |
      | limits, preflight|                     |                    |                |
      | brief(edit,1)    |                     |                    |                |
      |================> | submit ==================================================>| admit
      |                  | clone @S0           |                    |                |
      |                  |===================> | spawn, prompt      |                |
      |                  |                     |==================> | new session    |
      |                  |                     |   stream           |                |
      |                  |                     | <================= | commit C1      |
      |                  |                     | feed: report       |   (with note)  |
      |                  |                     |=====================================>|
      |                  |                     | end of chunk:      |                |
      |                  |                     |  steps >= cap      |                |
      |                  |                     | begin(phase_cap)   |                |
      |                  |                     |=== stop signal ==> | ends           |
      |                  |                     | drain, still metered                |
      |                  |                     | settle: cancelled  |                |
      |                  |                     | artifact (stopped, phase_cap)       |
      |                  |                     | Meter.observed: figures, bounds     |
      |                  |                     |=====================================>| final +
      |                  |                     | read back the record                | mark:
      |                  |                     | token record, prune                 | settled
      |                  |                     | Dispatches.exit                     |
      |                  | <=== exited ========|                    |                |
      |                  | bound, stopped_by: phase_cap             |                |
      |                  | _gitdir, _head -> C1                     |                |
      |                  | _import(C1, S0)                          |                |
      |                  | Runner.wait retires the clone            |                |
      | <== None, C1, phase_cap                |                    |                |
      | _state(C1) -> note                     |                    |                |
      | done += (edit, C1, capped)             |                    |                |
      | count = 1, phase stays edit            |                    |                |
      |                  |                     |                    |                |
      | brief(edit,1) with source C1, done, state.note              |                |
      |================> | submit ==================================================>| admit, on
      |                  |                     |                    |                | the settled
      |                  |                     |                    |                | figures
      |                  | new clone @C1       |                    |                |
      |                  |===================> | spawn, prompt      |                |
      |                  |                     |==================> | new session    |
      |                  |                     | <================= | commit C2,     |
      |                  |                     |                    | answer done    |
      |                  |                     | settle: completed  |                |
      |                  |                     | artifact (complete)                 |
      |                  |                     |=====================================>| final
      |                  |                     | token record, prune                 |
      |                  | <=== exited ========|                    |                |
      |                  | artifact, answer, done is bool, _collect(C2, C1)          |
      | <== answer, C2, returned               |                    |                |
      | _state(C2), done += (edit, C2, note)   |                    |                |
      | count = 2, phase -> test               |                    |                |
```

S0 is the spec's base. The second dispatch has a new dispatch id, a new clone and a new engine
session; the only things it shares with the first are the unit and commit C1. If the settled
figures have used up a cap or a window, the second submit is refused and the build stops there with
C1 imported (5.2a).

## 6. Failure and recovery

| Failure | What happens | What is lost | Recovery |
| :- | :- | :- | :- |
| The settlement cannot be written: the ledger refuses the final report of a capped run, or the store fails | Today's handling of a failed final report: the error name goes on Metering.errors and settle does not try again. The invocation record keeps tokens and messages unknown. No token record is written (run_tokens:unsettled). Under a cap or window on tokens or messages the next dispatch is refused unknown_allowance or unknown_window_usage and Runtime.build stops with that; without one it is admitted | Under such a cap, the rest of the build. The capped run's commits stay imported, without a ref | The ledger's existing handling of an invocation that was not settled. The next Runtime.build call starts from the spec's base |
| The mark is malformed | Reservations.report refuses invalid_input and nothing commits. Same as the row above | Same | A defect in the receiver, not an operating condition |
| A Codex run is stopped at the cap before any turn completed, so the meter has no figure | It is settled with tokens 0 and messages 0, both in lower_bound, in_flight 1. The next dispatch is admitted. The flag judges 0 and sends nothing | The ledger does not count what that turn used | None in this spec. Section 4.7 says what bounds the amount |
| A run is killed or dies before the meter saw anything, for a cause other than the cap | Not a capped run: the cap needs counted steps. No settlement at stop. Its final report carries no tokens or messages and the record stays unknown, as today. The flag reports it as unknown | Nothing new | Today's handling of an unknown invocation |
| The receiver's process dies between the stop and the final report | No final report is sent. The invocation stays pending, as today when a receiver dies | Under a cap on tokens or messages, the rest of the build | Today's handling of a pending invocation |
| The settled figures use up a cap or a window (5.2a) | The next dispatch is refused usage_cap or window_exhausted and Runtime.build stops with it | The rest of the build. The commits stay imported | The owner raises the cap, or the window resets |
| The overrides are invalid, or the worst-case brief skeleton does not fit | Runtime.limits refuses missing_authority:worker_configuration/build with the detail, before any dispatch | Nothing | Correct the worker configuration |
| A phase is stopped in the middle of a commit | Git moves the branch only after the commit object exists, so the ref names either the old commit or the new one, and _head reads whichever it is. If the object store was left in a state the copy or the fetch cannot use, _import refuses with today's name | The work of the commit that did not finish; in the refused case, the capped run's commits | The next dispatch starts from the commit the ref names. In the refused case the build stops and the next Runtime.build call starts from the base |
| The stopped clone's head cannot be read (a link, a linked directory above the ref, a ref outside refs/heads, an oversize file, no matching packed line, a reftable clone) | _head refuses invalid_input:build_head. Runtime.build stops with that refusal. No next dispatch is made | The capped run's commits are not imported | None in this build. The next Runtime.build call for the unit starts again from the spec's base |
| The head is readable but does not descend from the source | _import refuses binding_mismatch:build_commit | Same | Same |
| The note is missing, too large, a link, or not text | _state returns missing with the reason. The next brief carries state.missing and no note. Nothing is refused | What the note would have told the next phase | The next phase works from the commits, the done list and remains |
| Git fails while the note is read from an imported commit | _state refuses binding_mismatch:build_commit with the detail state_note | The rest of the build | Next build call starts from the base |
| The token record cannot be written (directory not creatable, disk full, record over 2,048 bytes) | The error name goes on Metering.errors (run_tokens:write, or run_tokens:oversize), as for an artifact that cannot be kept. The failure is caught inside settle and cannot escape _finish; the dispatch ends as it would have | One file | None needed. The ledger holds the numbers and the flag reads the ledger |
| The final report is refused before it commits | Today's handling: the error name goes on Metering.errors. The read-back finds no final report at settle's sequence, so no token record is written and run_tokens:unsettled is named (D14) | The file for that run | The ledger's own handling of an unsettled invocation |
| The final report commits and the call raises afterwards, in its policy reads | Today's handling of the error. The read-back finds the committed final report, so the token record is written from it | Nothing | None needed |
| The read-back itself fails | run_tokens:unsettled goes on Metering.errors. No record is written | The file for that run | None needed; the ledger is the record |
| Pruning fails for a file | The error name goes on Metering.errors (run_tokens:prune); the other files are still pruned | Nothing | The next settle tries again |
| A file in run_tokens is unreadable, not JSON, or schema-shaped with a bad ended_at, invocation, tokens or messages | run_tokens skips it. Pruning removes it once its modification time is more than 30 days old | Nothing | None needed |
| The artifact of a capped run was not kept | bound refuses as today, so the cause cannot be confirmed and _run refuses as today | The capped run's commits | Next build call starts from the base |
| The capped run ends on a remote transport | _finish records unknown (remote_stop_unconfirmed) and the unit and station stay held. Runtime.role refuses a non-local adapter before this can happen for an installed build | | Today's handling of an unknown outcome |
| The worker Runtime's process dies between two phases | The loop state is gone. The next Runtime.build call starts at edit from the spec's base with a fresh dispatch count; the contract's attempt goes on counting. It may itself be refused, if an earlier dispatch of the unit is unknown or the ledger refuses admission | The earlier phases' work | None in this spec (D13) |

Each import leaves the commit in the authority's repository without a ref, as today's build does
before review. The next dispatch clones at that commit by id. Review already does this with the
built commit, so the phases add no new requirement on the clone path.

## 7. Existing rows that will move, and what the suites need

**Three dispatches per build.** A build in suite 82 is now three dispatches, each a fresh process.
The valid stand-in mode has to answer per phase: edit makes the implementation commit and returns
done true; test returns its source commit and done true; proof makes the manifest commit and
returns commit, proof and done true. The proof process cannot use a variable left by the edit
process (today's stand-in keeps the implementation in one), so what proof needs it rebuilds from
its clone and its payload. Rows that assume one build dispatch per unit, attempt 1, or a count of
invocations need their numbers updated, and the fixture's ceilings (200 invocations, capacity 40)
are checked against the tripled count.

**The stand-in records as it goes.** Today the stand-in's marker holds the working directory, the
packet, the manifest and the arguments, and its record of printed events is written only at a
normal exit (357). A killed run would leave no session id and no events. The stand-in therefore
writes, as it runs: its session id (Claude Code) or thread id (Codex) into its marker at start; the
id of each commit it makes into its marker when it makes it; and each event to its record at the
moment it prints it. The format rows that iterate those records (674, 703) then cover killed runs
too.

**The capped mode.** It commits one file (with the state note the variant calls for), then prints
one counted event at a short fixed interval until it is killed. The interval keeps chunks small and
gives the stop time to arrive; nothing depends on an exact count. The events are those of the
binaries' recorded tables: for Claude Code, assistant events with a distinct message id and valid
usage each; for Codex, item.completed events with distinct item ids of a counted type, all inside
one open turn, with no fabricated turn.completed. The role's seconds for these fixtures is short,
so a mutant that removes the cap ends at the deadline quickly.

**The settled mode.** The row phase/settled-at-stop uses the capped mode with one addition for
Codex: the stand-in first prints one whole turn, opened, completed and carrying usage, and then
opens the turn it is stopped in. Its fixture project has a policy with a cap on tokens and a cap on
messages, both far above what the stand-in prints, and its account has a window whose unit is
tokens with room left. They are set through the ledger's own configure and window calls.

**Prefixes.** The three suites print one hard-coded prefix each: VELDO-0129, VELDO-0062 and
VELDO-0128. Appending the new rows would print them under those. Each suite gets one lookup from
row name to prefix, used by every line the emitter prints for a row (the detail line, the
unavailable line in 82, the expect line). The ten new row names map to VELDO-0294; every other
row falls back to the suite's own prefix, so no existing row's text changes. The nineteen mutation
cases are registered under spec 294 and name their rows as printed, with the VELDO-0294 prefix.

**The ledger's own suites.** The report gains an optional argument and the record an optional
field. Suite 58 and the other suites that drive control_reservations are run unmodified after the
change; a row that compares a whole record or a whole report payload would show there.

**Suite 72** has rows that compare the registry with the kinds the real writers commit. The new
event is added to the declared set, to the kind checks and to the real-writer fixture data, with
kind subscription_reservation.

**Suite 86 0127** goes red until the two live captures and the four resource records are retaken,
as the spec's section on the VELDO-0127 captures says. Section 11 orders that.

## 8. Acceptance criteria

The mutation runner applies exact text replacements to one module. Every anchor must occur exactly
once; a case may carry further replacements in the same module (its also list). By default it reads
the module under .veldo, and the suites load .veldo too (suite 82, 23 to 29), so the runtime copies
must be in sync before any baseline or mutant run (section 11). A red mutant is evidence only
after the unmodified baseline of the same row is green on the synced modules.

| AC | Components | Row (suite) | Mutant | Site the mutant edits |
| :- | :- | :- | :- | :- |
| AC1 | Runtime.build loop, brief, _run | phase/fresh-dispatches (82) | phase294-single-dispatch | The loop in Runtime.build: the phase advance, so that one dispatch is told to do all three phases and the build returns after it. The exact replacement is written with the loop |
| | | | phase294-session-resumed | The loop's call of brief: the replacement itself reads the session id of the dispatch before from the artifact Runtime.last names (Codex: the document's thread; Claude Code: the session id in its stream) and adds it to the payload as resume. No production code carries a session id for this |
| | | | phase294-source-not-advanced | The loop's assignment of the next source commit after a returned dispatch |
| AC2 | brief, the constants | phase/brief (82) | phase294-brief-without-reading-rule | brief: the reading field |
| | | | phase294-brief-carries-prior-answer | The loop's done entry: the whole answer text in place of the note |
| | | | phase294-brief-unbounded | brief: step 1 of section 4.4, the cut of remains, lines and characters together |
| | | | phase294-brief-without-note-rule | brief: the note field |
| AC3 | Metering cap check, take, STOPS, settle, stopped_by, _run path 2, the loop | phase/step-cap (82) | phase294-cap-unenforced | Metering.feed: the comparison of steps with the cap |
| | | | phase294-capped-work-dropped | The loop: the next source after a capped dispatch |
| AC4 | Metering.settle, Metering._record, run_tokens | tokens/run-record (75) | tokens294-record-unwritten | settle: the call to _record |
| | | | tokens294-unknown-as-zero | _record: the null for an absent tokens value |
| AC5 | REGISTRY, Reporter._run_tokens | report/run-over-tokens (72) | tokens294-flag-threshold-ignored | _run_tokens: the comparison with RUN_TOKENS_FLAG |
| | | | tokens294-unknown-not-flagged | _run_tokens: the unknown case |
| AC6 | Runtime.build loop, Runtime.limits | phase/budget (82) | phase294-dispatches-unbounded | The loop's check of the dispatch count |
| AC7 | Metering.settle prune | tokens/pruned (75) | tokens294-never-pruned | settle: the prune call |
| AC8 | Runtime._head and its file reader | phase/head-read (82) | phase294-head-symlink-followed | _head: the call that reads HEAD through the reader is replaced by a plain read that follows links |
| | | | phase294-ref-symlink-followed | _head: the call that reads the ref file through the reader is replaced by a plain read that follows links |
| AC9 | Runtime._state, brief | phase/state-note (82) | phase294-state-note-not-carried | The loop's call to _state |
| AC10 | Meter.observed, Metering.settle, InvocationGuard.observe, Reservations.report | phase/settled-at-stop (82) | phase294-capped-left-unknown | Metering.settle: step 2, so that the final report of a capped run carries Meter.final's usage and no mark |

**Why the AC8 mutants are built this way.** Revision 1 had each mutant remove one check. That
cannot turn the row red: with the first status check gone the no-follow open still refuses the
link, and with the descriptor check gone the first two still do. The defenses are deliberately
redundant, so a mutant that removes one of them proves nothing. In this revision all the defenses
of one file read live inside the reader, HEAD and the ref file are read by two separate calls, and
each mutant replaces one call with a read that really follows a link. Under the HEAD mutant the
linked HEAD yields the stopped commit, the build continues and a second dispatch record appears;
the same for the ref mutant. Production keeps every defense, and no production parameter exists
that could turn them off. The mutants keep the names and the meaning the spec gives them.

What each row has to observe, beyond the spec's wording:

- phase/fresh-dispatches: the three session ids and the three working directories come from the
  stand-in's markers, written at start (section 7). The source commits come from the dispatch
  records' contracts. The edit phase makes a distinct commit, so a source that was not advanced
  shows; the test phase may make none.
- phase/brief:
  - soft is asserted directly as the larger of 1 and messages minus 10, for the default and for a
    small messages value, since no mutant covers wrong arithmetic.
  - The fixture's answer carries a short, recognizable field besides note and remains. The row
    requires each done note to equal that dispatch's answer note exactly, and requires the
    recognizable text to be nowhere in a later payload. Total length alone would not catch the
    mutant, because the cuts could trim the forbidden text away.
  - Three direct calls of brief: the spec's oversized case (40 lines of 400 characters, five notes
    of 2,000), required to be at most 4,096 bytes with at most 10 lines of at most 200 characters
    and notes of at most 200; forty short lines that fit the byte bound, required to come back as
    at most 10 lines, which the byte fit alone would not enforce; one line of 400 characters,
    required to come back at most 200. The oversized case is run for all three phases, so the
    longer proof OUTPUT cannot hide behind the edit phase.
  - A skeleton that cannot fit (many done entries) is required to refuse with the detail
    brief_bytes, and Runtime.limits is required to refuse the same configuration before a
    dispatch.
  - The byte limits of READING_RULE, NOTE_RULE, CAPPED_NOTE and each OUTPUT are asserted.
- phase/step-cap, for each engine:
  - The first dispatch's artifact names phase_cap (read with the engine-aware accessor) and its
    verdict is stopped; the ledger invocation ended cancelled.
  - The counted events in the artifact's lines are at least 5. The row does not require exactly 5
    (section 3.1).
  - A control run that prints 4 counted events and then ends normally completes with no stop. For
    Codex the control also prints a repeated item id and items of type reasoning, todo_list and
    error, which must not count, and the capped run's items all sit inside one open turn.
  - The commit the stopped run made is taken from the stand-in's marker, not from the loop. The
    second dispatch's contract source and its done entry must both equal it, and it must differ
    from the spec's base.
- phase/settled-at-stop, for each engine:
  - The first dispatch's invocation record is read from the ledger: state settled, an empty unknown
    list, outcome cancelled.
  - Its charge is compared with figures the row adds up itself from the usage lines in the
    artifact (read the engine-aware way), never with a number the production code reports. For
    Codex that is the one completed turn.
  - Its settlement names at stop, cause phase_cap, both units in lower_bound, and in_flight 1 for
    Codex and None for Claude Code.
  - The second dispatch has a dispatch record for the same phase, and the stand-in's marker for it
    shows the engine started. Under the mutant the record keeps tokens and messages unknown, the
    ledger refuses the second dispatch unknown_allowance:tokens, and neither exists.
  - The window is part of the same fixture, so the row would also go red on unknown_window_usage
    if only the cap were satisfied.
  - Two direct calls of Reservations.report keep the mark honest: a mark on a report that is not
    final, and a mark whose cause is not in SETTLED_AT_STOP, each refuse invalid_input.
- phase/budget: the fixture's project has an invocations ceiling one above the budget, so the
  mutant that drops the count cannot run forever: it makes a fifth dispatch and then stops on the
  ledger. The row requires the exact code phase_budget:build, the detail naming edit, four dispatch
  records and no fifth.
- phase/head-read: each of the spec's three variants must refuse with the exact code and leave no
  second dispatch record. Three more observations keep the row from passing on an unrelated error:
  a linked refs/heads directory refuses the same way (D8); a clone whose ref exists only in
  packed-refs continues, with the right commit; and the step-cap row is the loose-ref control.
- phase/state-note: the second payload is inspected in every variant, whatever happens later in
  the build. The 6,000-byte note contains non-ASCII text and both newline forms and must come back
  equal byte for byte when encoded again. The other three variants must have no state.note key.
- tokens/run-record: the third invocation's stream carries no usage at all, so the ledger's charge
  has no tokens value. The second is stopped by settle with the cause phase_cap after live reports,
  so its charge is the figure settled at stop.
  Further checks: a real zero total is written as 0; a not_executed invocation is written as 0; a
  final report that commits while the observe call raises afterwards still yields a record; a
  schema-shaped file with a bad ended_at is skipped by the reader.
- tokens/pruned: age is judged by the record's ended_at. The 31-day file is given a fresh
  modification time and the 29-day file an old one, so the file's own time cannot make the row
  pass.
- report/run-over-tokens: the records are written through the real Reservations service, the two
  settled at stop with a real mark. Beyond the spec's five: exactly 15,000,000 sends nothing; a
  record whose tokens are unknown with a live figure under the threshold is reported as unknown
  with "at least"; a non-final report after the final one does not send a second report.

## 9. Where the spec and the code disagree, and choices the spec leaves open

**D1. What the cap counts, per engine.** The spec compares the meter's message count with the cap.
For Claude Code the live count is the number of distinct assistant message ids that carried
readable usage (control_engine_claude.py 1120 to 1130), which grows through the run; steps returns
exactly that. For Codex the live count is completed turns, and a turn is counted only when an open
turn completes with valid input and output counts (393 to 407). Nothing within a turn moves it, so
a cap of 80 turns cannot stop any work inside one outer turn, however much the run does; only a cap
of 1 could trigger, and only on the turn's final line. Revision 1 cited
proof/VELDO-0061/codex-exec.json as showing one turn per run. That file is a table of event and
item names extracted from the binary, not a transcript, and the claim that the cap never fires on
Codex was too absolute. The validation points to the recorded loopback runs in
proof/VELDO-0127/codex-live.json as examples of single-turn runs; neither they nor the meter prove
that every run is one turn, and the design does not rely on it.

Recommendation: compare the cap with Meter.steps(), defined per engine in section 3.1. For Codex a
step is a distinct completed work item of six types. It is a budget of observable work, not a count
of model requests: one model response can produce several items, and a collab item hides the work
of the agent it drives. No exact per-request counter is exposed by this code. Counting every
completed item would be wrong, because startup error items would count. The ledger's messages keep
their meaning. AC3, as amended, names this unit.

**D2. "A cancelled record whose supervision cause is phase_cap" does not exist as written.** The
dispatch record has no cancelled state and no supervision field. Cancelled is the ledger's outcome,
and supervision travels only as a message on the launch pipe. Recommendation: decide from the
artifact document, read through bound, because that document is tied to the exit record by digest.
The cause is read per engine by stopped_by (Claude Code exit.cause, Codex cause); revision 1's
single lookup was wrong.

**D3. P.blob cannot tell a regular file from a symlink.** It runs cat-file blob and returns the
whole result (control_proof.py 195 to 200); a symlink is a blob too, and there is no mode or size
guard. control_proof.py is outside the footprint. Recommendation: Runtime._state lists the tree
entry and checks its mode and the blob's size itself, in control_launch_work.py, because the
not_a_file and oversize cases of AC9 cannot be met otherwise. The spec's prose says the note is
read "with P.blob"; the read still ends in the same Git call, behind those two checks.

**D4. What "unknown" means for the flag.** In the ledger, unknown means the unit is in the record's
unknown list after its final report. Revision 2 built that meaning and so reported every capped
run, since a capped run never got a total. The owner's decision removes the cause: a capped run is
settled at stop, is not unknown, and is judged by its figure (section 4.6). A run with no figure,
one that ends at its deadline or whose stream ends without a total, is still unknown and still
reported. One consequence is accepted with the decision: a Codex run stopped inside its first turn
settles 0 tokens and is not reported, whatever that turn used. AC4 is not affected: it asks for the
charge, and null only where the charge holds nothing.

**D5. The 4,096-byte bound is an envelope with a named failure.** In AC2's oversized case, ten
remains lines of 200 characters take 2,041 bytes and five done entries with 200-character notes
take about 1,408. The fixed fields take about 325. That leaves about 320 bytes for READING_RULE,
NOTE_RULE and OUTPUT together, and today's proof instruction alone is about 330. So the cuts alone
cannot meet the bound. Revision 1 added a fit step and claimed the bound then holds for any input.
That was false: the done entries' phases and commits cannot be cut and grow with the dispatch
override (sixty entries with empty notes are already over the bound), and the producer and the
texts cannot be cut either. This revision: the fit step empties notes and drops remains lines, and
when the skeleton still does not fit, brief refuses by name; Runtime.limits measures the worst
case before the first dispatch, so the refusal comes before any work is spent (sections 2 and
4.4). AC2, as amended, states the cuts as upper limits and gives the drop order.

**D6. The answer's fields.** The spec gives commit, done and remains, and AC2 speaks of each ended
phase's note without saying where it comes from. Recommendation: section 3.3, with note as an
optional answer field, because it is the smallest addition that gives the done list its text.

**D7. A head that does not descend from the source.** The spec says the head "is kept only if it
descends", which could mean refuse or could mean continue from the source. Recommendation: refuse
with the existing binding_mismatch:build_commit, because a builder that left its source's history
has rewritten it, and continuing as if nothing happened would hide that.

**D8. Linked directories above the ref file.** AC8 tests a linked HEAD, a linked ref file and a ref
outside refs/heads. A linked refs or refs/heads directory redirects the read the same way.
Recommendation: check every directory on the path (rule 4 of section 4.5). The row gains a linked
directory variant and a packed-refs control; the spec requires neither.

**D9. A note that is not valid UTF-8.** The spec has three reasons: absent, oversize, not_a_file. A
JSON payload cannot carry arbitrary bytes. Recommendation: report not_a_file, decode only after the
size check, and never decode with replacement, because the carry is promised byte for byte.

**D10. Where the phase name goes in phase_budget:build.** Recommendation: the code is exactly
phase_budget:build and the phase is the refusal's detail, because callers and rows match on the
code. The same rule gives invalid_input:build_head one code with its reason in the detail.

**D11. Overrides that cannot work.** The spec lets a role set messages and dispatches and says
nothing about bad values. Recommendation: the table in section 2. Minimums alone do not bound the
brief, so the skeleton preflight is part of this decision.

**D12. phase_cap in the remote stop list (_finish, 1626).** The spec asks for it. Runtime.role
refuses any adapter that is not local, so no installed build reaches that line. Recommendation: add
the name as the spec says, because a remote capped run that fell through to Dispatches.exit would
be recorded as ended without proof that the remote engine stopped.

**D13. A build interrupted between phases starts over.** The loop state is in memory. The spec adds
no durable record of a build's progress. Recommendation: accept this in VELDO-0294. A restarted
build spends its dispatches again, the budget counts per Runtime.build call, and the restart can be
refused if an earlier dispatch is unknown or the ledger refuses admission.

**D14. No token record without a committed final report.** Recommendation: write nothing from the
meter's own numbers. But a raised exception does not show that nothing committed, because the
ledger commits the report before the guard's policy reads. So settle reads the record back and
decides from what is there (section 4.2).

**D15. A capped run is settled at stop.** Revision 2 found that a capped run left its usage unknown
and that the ledger then refused the next invocation under any cap or window on tokens or messages.
It left the ledger alone and proposed to say so in AC3. The owner decided otherwise (Telegram 40821
and 40822): fix the cause, and settle the stopped run from what the meter saw. Three choices in how
that is built:

- The figures go into the ordinary final report, and the ledger's existing rule settles the record.
  No second settling path is added to the ledger, and its admission check is not touched.
- The mark is separate from the figures and is validated by the ledger, so a lower bound cannot be
  stored without saying that it is one.
- Only phase_cap settles this way. A run stopped by its deadline, by a usage cap or on request
  stays unknown as today. Those stops are not Veldo ending a phase on purpose, and widening the
  rule to them would change VELDO-0036's behavior outside this spec.

The cost is the one revision 2 named: the figures are lower bounds, so a cap can be passed by what
stopped runs used unseen. Section 5.2a gives the size per engine.

Two smaller facts, with no decision needed. Runner.wait retires the slot of a capped run with the
word failed (control_launch.py 963 to 964), since the record is not a clean exit; the token record
and the ledger both say cancelled. And the contract's attempt labels phases two and three retry, as
the spec already says.

## 10. Spec changes

None are open. Revision 2 proposed four, S1 to S4, and all were decided with the owner's approval
(Telegram 40821 and 40822). The spec's History line of 2026-11-11 records each decision, and the
spec was amended at 3b6a5a0e.

## 11. Build order

The rule for every step below: after any edit to an engine/.veldo module, sync its .veldo copy
before running a suite or a mutant, because both read .veldo.

1. control_reservations.py and control_reservation_runtime.py: the settlement mark and its
   pass-through. Sync. Run suite 58 and the other ledger suites unmodified before going on.
2. Engine modules: STOPS, Meter.steps and Meter.observed. Then control_launch.py: the cap check
   with its station condition, stop_cause, the settle cause, the observed figures and the mark in
   the final report, the read-back, the token record, pruning, run_tokens and its validation, the
   remote stop name. Sync.
3. control_launch_work.py, helpers first: stopped_by, bound, the split of _collect, the file
   reader and _head, _state, brief with spec_text and its refusal, limits with the preflight.
   Then _run: the done check on path 1, the capped path as path 2 inside the try block, the third
   return value, and Runtime.review's unpacking in the same change. Then the loop. Sync.
4. control_telegram_report.py: the event and its handler. Sync.
5. Suites 82, 75 and 72, alongside steps 2 to 4 where a row needs them: the stand-in's per-phase
   answers and its recording as it goes, the capped mode, the settled mode and the head and note
   variants, the prefix lookup, the ten rows, the moved rows of section 7.
6. With every copy in sync, run the three suites unmodified and get every new row green. This is
   the baseline.
7. check_teeth_mutations.py: register the nineteen cases and run each red against that baseline.
   Any production edit a mutant forces (a statement split so an anchor is unique) goes back
   through sync and step 6 first.
8. When control_launch.py and both engine modules have stopped changing and are synced: refresh
   the four VELDO-0127 resource records through qualification, then retake the two live captures,
   then make no further change to a bound module. The Claude Code capture runs in a context that
   does not already hold the same login lease. Suites 82, 75 and 72 do not need fresh captures;
   suite 86 and the gate do. The captures bind control_launch.py and the two engine modules, not
   the two ledger modules.
9. Run the gate last.

## 12. History

- Revision 1, b1180439: the design before the build.
- Revision 2: revised from Codex's validation of revision 1
  (design-veldo-0294-validation-2026-11-11.md, verdict CHANGES; owner order, Telegram 40818: Fable
  designs, Codex validates, then the build). Each finding was checked against the cited lines
  before it was accepted.
  - Accepted and fixed: continuation after a cap under a tokens or messages ceiling (5.2a, D15,
    S1); the per-engine step count and the wrong VELDO-0061 citation (3.1, D1, S2); the brief's
    size envelope and named failure (2, 4.4, D5, S3); the missing spec text argument of brief; the
    per-engine stop cause; the cap checked per chunk, so no exact count; the settle order and the
    read-back after the final report (3.1, 4.2, D14); record validation and pruning rules; the
    once-per-invocation flag rule; the AC8 mutants that could not turn red, now real unsafe reads
    (8); the row prefixes (7); the killed stand-in's markers (7); the bounded AC6 harness and the
    sharper AC2 and AC3 rows (8); the build order, with sync before baselines and mutants (11);
    the smaller wording corrections (40 lowercase hex, the station condition on the cap, a
    non-object phase override, Git failures in _state, the path number in _run).
  - Accepted as a spec question, not built: the narrower meaning of unknown for the flag (D4, S4).
    Revision 1 had built it; this revision builds the approved text.
  - Not accepted, with the evidence: the validation marks as false a claim that P.blob can
    validate a regular file's mode and size, citing the design's D3. D3 says the opposite, that
    P.blob cannot tell a regular file from a symlink, and the validation's own verdict on D3 is
    TRUE. The claim it corrects is the spec's prose, not the design's, and no design change
    follows. Likewise revision 1 never said the new rows would get their prefix automatically; it
    was silent, which was an omission and is fixed, not a false claim.
  - Not re-verified here: the validation's reading of the single-turn loopback captures in
    proof/VELDO-0127/codex-live.json and of the qualification order in .veldo/qualify.py. The
    design uses the first only as an example and takes the second as the safer order.
- Revision 3: follows the spec's amendment at 3b6a5a0e (owner approval, Telegram 40821 and 40822).
  - S2 and S3 are in the spec, so D1 and D5 no longer ask for them.
  - S1 was rejected as written. A run stopped at its phase cap is settled at stop instead: new
    components for the observed figures, the pass-through and the ledger's mark (1, 3.1), the
    mark's data (4.7), the changed flows (5.2, 5.2a, the sequence), the failure cases (6), the
    row and mutant of AC10 (7, 8), and D15 rewritten.
  - S4 is replaced by the same decision: the flag judges a settled figure (4.6, D4).
  - Section 10 has no open items. The build order starts with the ledger (11).
