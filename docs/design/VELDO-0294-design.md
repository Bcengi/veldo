# VELDO-0294 design: a build as short fresh phases, with a token record per run

Design for the spec at specs/VELDO-0294-builds-run-as-short-fresh-phases-with-per-run-token-records.md
(approved at a385da5e). Written before the build, from the spec, its three reviews and the code at
6ee5bb5f. Line numbers are those of engine/.veldo at that commit. Every engine/.veldo file named here
has a synced copy under .veldo that changes with it.

The design keeps the spec's shape: Runtime.build becomes a loop of build dispatches, the receiver
stops a run at its message cap, the stopped clone's head is read as bytes, each settle writes one
small token file, and the Telegram reporter gains one event. Section 9 lists fourteen places where
the spec and the code disagree or the spec leaves a choice open. Three of them change what gets
built (D1, D4, D5) and need the lead's answer before the build starts.

## 1. Components

| Component | File | Today | Change | Responsibility after the change |
| :- | :- | :- | :- | :- |
| Phase loop | control_launch_work.py, Runtime.build (238) | One payload, one _run call | Rewritten as a loop | Runs edit, test, proof in order; counts dispatches; advances the source commit; refuses phase_budget:build; returns the proof phase's result |
| Brief builder | control_launch_work.py, new function brief | Payload built inline (242 to 246) | New | Builds one dispatch payload from the loop state, applies the cuts and the size fit |
| Run step | control_launch_work.py, Runtime._run (142) | Refuses every run that did not complete | One exception added | Returns a capped build run to the loop instead of refusing it |
| Bound artifact read | control_launch_work.py, artifact (52) | Digest check and completion check in one function | Split in two | New function bound does the digest and dispatch check; artifact calls it and keeps its completion check |
| Collector | control_launch_work.py, Runtime._collect (183) | Directory checks, then import of the commit the answer names | Split in three | _gitdir (the directory checks), _import (the object copy, the two fetches, the descent check, the scan), _collect (both, with the answer's commit) |
| Head reader | control_launch_work.py, new method Runtime._head | None | New | Reads the stopped clone's head commit id from regular files only; refuses invalid_input:build_head |
| Note reader | control_launch_work.py, new method Runtime._state | None | New | Reads proof/<unit>/phase-state.md at a commit in the authority's repository; returns the note or why it is missing |
| Cap check | control_launch.py, Metering.__init__ (2540) and Metering.feed (2603) | No cap of its own | Extended | Reads payload.phase.messages; says when the run's step count reaches it |
| Stop cause | control_launch.py, take inside Receiver._reap (2316) | Every metering stop is usage_cap | Extended | Begins the stop with the cause Metering names: usage_cap or phase_cap |
| Settle | control_launch.py, Metering.settle (2684) | Sends the final report | Extended | Settles phase_cap as cancelled; writes the run token record; prunes old records |
| Token record store | control_launch.py, new functions run_tokens_directory and run_tokens | None | New | One place that resolves the directory; one reader that returns the kept records newest first |
| Remote finish | control_launch.py, Receiver._finish (1626) | Stop causes requested and usage_cap | One name added | Treats phase_cap as a stop on a remote transport |
| Step count | control_engine_claude.py and control_engine_codex.py, Meter | cumulative and final only | New method steps (see D1) | The live count the cap is compared with |
| Stop names | STOPS in both engine modules (claude 1215, codex 474) | No phase_cap | One name added | The artifact document gets verdict stopped and names the cause |
| Flag | control_telegram_report.py, REGISTRY (140) and new handler Reporter._run_tokens | No event reads the ledger | New event run_over_tokens | One report per settled run over the threshold or with no token count |
| Stand-in engine | scripts/suites/82_veldo_0129_worker_wiring.py | Does a whole build in one run | Phase aware, with new fixture modes | Answers per phase; can run on past the cap; can damage its own head or note |
| Rows | suites 82, 75, 72 | | Nine new rows | Section 8 |
| Mutants | scripts/check_teeth_mutations.py | | Eighteen new cases | Section 8 |

Nothing changes in control_dispatch.py, control_reservations.py, control_reservation_runtime.py,
control_clone.py, control_proof.py or dispatch.py. None of them is in the footprint, and the design
needs no change in any of them.

### Component view

```
 AUTHORITY SIDE (the worker Runtime's process)            RECEIVER SIDE (one process per dispatch)

 Runtime.build  (phase loop)
   |  state: phase, dispatch count, source commit,
   |         done list, remains, state note
   |
   +-> brief()  ..................  payload
   |
   +-> Runtime._run  ->  L.Runner.submit  ->  L.invoke  =====>  Receiver.launch
   |        |                                                     |
   |        |                                                   Receiver._reap
   |        |                                                     |  take(chunk)
   |        |                                                     +-> Metering.feed
   |        |                                                     |     Meter.feed  -> ledger reports
   |        |                                                     |     Meter.steps -> cap reached?
   |        |                                                     +-> begin(usage_cap | phase_cap)
   |        |                                                     |
   |        |                                                   Receiver._finish
   |        |                                                     +-> Metering.settle
   |        |                                                     |     final report -> ledger
   |        |                                                     |     Metering._artifact -> artifacts/
   |        |                                                     |     run token record -> run_tokens/
   |        |                                                     |     prune run_tokens/
   |        |                                                     +-> Dispatches.exit (record: exited)
   |        |  <=== launch pipe: artifact report, exited ==========+
   |        |
   |        +-> bound()  reads the artifact document by path and digest
   |        +-> returned:   _collect  = _gitdir + _import(answer's commit)
   |        +-> phase_cap:  _gitdir + _head + _import(head commit)
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
| PHASE_MESSAGES | 80 | Default message cap of one dispatch |
| PHASE_DISPATCHES | 6 | Default number of dispatches one build may use |
| SOFT_MARGIN | 10 | phase.soft is messages minus this, and never below 1 |
| READING_RULE | Text, at most 110 bytes of ASCII | Read only the parts of a large file you need, by search and line range; never a whole large file |
| NOTE_RULE | Text, at most 200 bytes of ASCII | Keep the state note current in every commit, under its four headings; after phase.soft messages stop new work, commit and finish the note |
| OUTPUT | One text per phase, at most 340 bytes of ASCII each | What the phase returns (section 3.2) |
| CAPPED_NOTE | Text, at most 100 bytes | The done note of a dispatch that hit the cap: it was stopped at the message cap and its uncommitted work is lost |
| NOTE_PATH | proof/<unit>/phase-state.md | Where the builder keeps the state note |
| NOTE_BYTES | 8,192 | Largest note that is carried |
| BRIEF_BYTES | 4,096 | Largest payload without its spec text and state.note |
| REMAINS_LINES, LINE_CHARS | 10, 200 | The cuts on remains and on each done note |
| RUN_TOKENS_SCHEMA (control_launch.py) | veldo.run_tokens/v1 | Schema of the token record |
| RUN_TOKENS_BYTES (control_launch.py) | 2,048 | Largest token record |
| RUN_TOKENS_DAYS (control_launch.py) | 30 | Age at which a record is removed |
| RUN_TOKENS_FLAG (control_telegram_report.py) | 15,000,000 | The flag threshold |

The byte limits on the three texts are not in the spec. They come from the size arithmetic in D5
and the suite should assert them.

A role may override two numbers in the worker configuration, under work.builder.phase: messages and
dispatches. Runtime.build reads them through a new helper, Runtime.limits, which returns messages,
soft and dispatches. Each override must be an integer (a boolean is not one), messages at least 1
and dispatches at least 3, because a build cannot finish in fewer than three dispatches. Anything
else refuses missing_authority:worker_configuration/build, the name Runtime.role already uses for a
bad builder role, before any dispatch is made. An absent phase object means the defaults.

The receiver configuration gains one optional key, run_tokens, a directory path. Absent, the
directory is run_tokens beside the store, the rule receipts (2593) and artifacts (2671) follow.

## 3. Interfaces

### 3.1 Functions

**brief(spec, role, phase, limits, source, done, remains, state)** in control_launch_work.py. Pure:
no I/O, no Git. It takes the spec record Runtime.build receives, the role, the phase index (0 to 2),
the limits, the source commit of this dispatch, the done list so far, the remains list and the state
(None for the first dispatch, otherwise what Runtime._state returned). It returns the payload dict
of section 3.2 after the cuts and the fit of section 4.4. The spec text is passed in already read,
so the function can be called by the suite for the oversized case without a repository.

**Runtime.limits()** returns the three numbers described in section 2 or refuses.

**Runtime._run(unit, station, role, revision, payload, context)** keeps its arguments. It now
returns three values: the result (a dict, or None for a capped run), the reference (dispatch and
artifact, as today) and the ending, which is the word returned or the word phase_cap. Runtime.review
takes the first two and ignores the third. The decision inside _run, in this order:

1. The record completed (L.D.completed) and binds an artifact: today's path, unchanged. Ending
   returned.
2. Otherwise, if the station is build, the record's state is exited, it binds an artifact, and the
   document that bound returns names the cause phase_cap: the capped path. _run calls _gitdir, then
   _head, then _import when the head differs from the revision, and returns result None with the
   ending phase_cap. The head commit goes back to the loop in the reference, under the key commit.
3. Otherwise: today's refusal, unchanged (the record's refusal, or unknown_outcome:engine).

**bound(record, reference)** is the first half of today's artifact function: read the file the
reference names, check its digest against the record's artifact digest and its dispatch id against
the record, refuse with today's names, return the document. artifact(record, reference) becomes
bound plus the completion check, so the floor (dispatch.py 909) sees no change.

**Runtime._gitdir(handle)** is lines 185 to 194 of today's _collect: it returns the clone's .git
path after refusing a symlink, a non-directory, commondir and the two alternates files.

**Runtime._import(gitdir, commit, revision)** is lines 198 to 236 of today's _collect, unchanged in
behavior: copy the object files, fetch into the authority's temporary repository, require the commit
to exist and to descend from revision, fetch into the authority's repository, run the candidate
scan. It keeps today's refusal names.

**Runtime._collect(handle, result, revision)** is _gitdir, the check that the answer's commit is a
commit id, then _import. Same behavior as today.

**Runtime._head(gitdir)** returns a 40-digit commit id or refuses invalid_input:build_head. The
rules are section 4.5. It never runs Git and never opens a path without first checking, with a
no-follow status call, that it is a regular file.

**Runtime._state(commit, unit)** returns a dict with exactly one key: note (the text) or missing
(absent, oversize or not_a_file). It runs Git only in the authority's own repository, on a commit
that _import has already fetched there. Steps: list the tree entry at NOTE_PATH in the commit; no
entry means absent; an entry whose mode is not a regular file (100644 or 100755) means not_a_file,
which covers a symlink, a directory and a submodule; ask Git for the blob's size and return oversize
above NOTE_BYTES without reading it; read the blob; bytes that are not valid UTF-8 mean not_a_file
(D9). It refuses nothing.

**Metering.capped** (new attribute) and **Metering.stop_cause()** (new method) in control_launch.py.
Metering.__init__ reads payload.phase.messages from the contract. It keeps the number as the cap
when the payload is a dict, phase is a dict and messages is an integer of at least 1, and keeps no
cap otherwise, so review and coordination runs are never capped. After Metering.feed has passed the
chunk's observations to the ledger, it sets capped when a cap exists and Meter.steps() has reached
it. feed returns true when either stop or capped is set. stop_cause returns usage_cap when stop is
set and phase_cap otherwise, so a ledger cap wins when both happen in one chunk.

**take(chunk)** inside Receiver._reap begins the stop with metering.stop_cause() where it says
usage_cap today (2322). begin already ignores a second cause.

**Meter.steps()** in both engine modules returns an integer that only grows while the stream is
read. Claude Code: the number of distinct assistant messages seen, the same number
cumulative reports as messages before a result arrives. Codex: the number of completed items whose
type is agent_message, command_execution, file_change, mcp_tool_call, web_search or
collab_tool_call. The reason for a second count in Codex is D1.

**Metering.settle(termination, cause)** adds phase_cap to the causes at 2702. After the final report
to the ledger returns without an error, it calls a new private method, Metering._record(outcome,
now), then prunes. Section 4.2 gives the record and section 6 the failures.

**run_tokens_directory(config)** in control_launch.py returns the configured path or run_tokens
beside the store. Metering._record and run_tokens both call it, so the rule exists once.

**run_tokens(config)** in control_launch.py returns a list of record dicts, newest ended_at first,
ties ordered by invocation. It skips any file that is not a JSON object with the right schema. A
directory that does not exist gives an empty list.

**Reporter._run_tokens(eid, entry, prior, state)** in control_telegram_report.py has the signature
of every REGISTRY handler and returns a fact dict or None. REGISTRY gains the row run_over_tokens,
listening to the kind subscription_reservation. Section 4.6 gives its rule and text.

### 3.2 The brief: payload fields

| Field | Type | Value | First dispatch |
| :- | :- | :- | :- |
| operation | text | build | same |
| spec | text | The spec file at the spec's base, as today | same |
| spec_revision | text | As today | same |
| producer | text | The builder's identity, as today | same |
| phase | object | name, index (1 to 3), of (3), messages, soft | name edit, index 1 |
| source | object | commit: the commit this dispatch starts from, equal to the contract's source commit | the spec's base |
| done | list | One entry per ended build dispatch of this build, oldest first: phase, commit, note | empty list |
| remains | list of text | What the phase before said is left | empty list |
| reading | text | READING_RULE | same |
| note | text | NOTE_RULE | same |
| output | text | OUTPUT of this phase | edit's text |
| state | object | note (the whole state note) or missing (absent, oversize, not_a_file); never both | not present |

No field named resume exists, so control_reservation_runtime.boundary never answers follow_on and
Metering never resumes a CLI session.

The key note appears three times with three meanings: at the top level it is the rule, in a done
entry it is that dispatch's one-line summary, and under state it is the builder's file. The spec
fixes all three names and the rows compare them, so the design keeps them (the second re-review
called this out as not blocking).

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
| done | yes | A boolean. Anything else refuses missing_evidence:build_result, the existing name for an answer that is not usable |
| note | no | Text. Missing or not text becomes an empty note |
| remains | no | A list. Entries that are not text are dropped. Missing or not a list becomes an empty list |
| proof | proof phase with done true | As today: a dict whose spec_revision equals the spec's, else missing_evidence:build_proof |

Only done is strict, because only done changes what the loop does next.

### 3.4 Runtime.events

_run keeps appending its entry for every returned run, unchanged (operation build or review, outcome
artifact). Runtime.build appends one more entry per build dispatch, returned or capped:

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

A separate entry keeps the shape of the existing one, which other rows read.

## 4. Data model

### 4.1 The state note

| Property | Value |
| :- | :- |
| Path | proof/<unit>/phase-state.md in the builder's clone, committed |
| Written by | The builder, in every commit it makes (NOTE_RULE) |
| Content | UTF-8 text under four headings: done, left, decisions made, approaches tried and rejected |
| Bound | 8,192 bytes; a larger note is not carried and the next brief says oversize |
| Read by | Runtime._state, from the commit a dispatch ended on, after that commit is in the authority's repository |
| Carried as | state.note, whole, byte for byte |
| Lifetime | Deleted by the proof phase in the commit that adds the manifest. Nothing checks the deletion (the second re-review accepted that) |

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
| phase | payload.phase.name, or null when the payload has no phase (review, coordination) |
| attempt | The contract's attempt |
| account | The contract's reservation account |
| provider | The engine's PROVIDER |
| boundary | Metering.boundary |
| tokens | The charge of the ledger's invocation record, or null when that charge holds no tokens value (D4) |
| messages | The same rule, for messages |
| wall_seconds | The charge's wall_seconds |
| outcome | The outcome settle reported to the ledger (completed, failed, timeout, cancelled, not_executed or the account limit outcome) |
| ended_at | The time settle took for its final report, in seconds since the epoch |

The numbers are read back from the ledger after the final report commits, not taken from the meter.
Metering reads the invocation record the way InvocationGuard.observe already does (the reservations'
record map, the entry of type invocation with this invocation id and domain), because
control_reservation_runtime.py is outside the footprint and has no reader to call.

The record is written to a temporary name in the same directory and renamed, so a file under its
final name is always whole.

### 4.3 The done list and the remains list

Both live in the loop's local variables and in the payloads built from them. Neither is stored
anywhere else.

A done entry has three keys: phase (the phase name of that dispatch), commit (the commit it ended
on) and note. For a returned dispatch the note is the answer's note. For a capped dispatch it is
CAPPED_NOTE. This is where the brief says that uncommitted work was lost.

remains is the list the last returned answer gave. After a capped dispatch the list is left as it
was, since a capped run returns nothing, and the state note of its last commit is the fresher
source.

### 4.4 Cuts and the size fit

brief applies these in order:

1. remains is cut to its first 10 lines, and each line to its first 200 characters.
2. Each done note is cut to its first 200 characters.
3. The payload without spec and without state.note is encoded with P.canonical (compact, sorted,
   ASCII escaped). If that is over 4,096 bytes, done notes are emptied oldest first until it fits,
   then remains lines are dropped from the end until it fits. phase, source, reading, note, output
   and the commits of the done entries are never cut.

Step 3 is needed because the cuts alone do not guarantee the bound (D5). The state note and the spec
text are outside the bound, as the spec says.

### 4.5 Reading the head of a stopped clone

Runtime._head runs only after _gitdir has passed and only for a record in state exited. A record
reaches that state only when the worker's containment group is empty (Receiver._finish records
unknown otherwise, at 1632), so nothing is writing the clone while it is read.

Every rule below that fails ends in the one refusal invalid_input:build_head. The reason goes in the
refusal's detail, not in its code, so the row can compare the code exactly.

1. .git/HEAD must be a regular file by a status call that does not follow links. It is opened with
   the no-follow flag and checked again on the open descriptor. At most 1,024 bytes are read.
2. Its content, less one trailing newline, is either a commit id of 40 hex digits, which is the
   answer, or the text ref: refs/heads/<name>.
3. <name> must be at most 255 characters and made of path components joined by a slash. Each
   component holds only letters, digits, dot, underscore and hyphen, is not empty, does not start
   with a dot and does not end in .lock. This keeps the path inside .git/refs/heads.
4. Every directory on the way from .git to the ref file (refs, refs/heads and any directory inside
   <name>) must be a real directory, not a link. AC8 tests only a linked ref file; a linked refs
   directory is the same attack one level up (D8).
5. If something exists at .git/refs/heads/<name>, it must be a regular file, read like HEAD, holding
   40 hex digits and at most one trailing newline. A link or anything else there refuses; it does
   not fall through to packed-refs.
6. If nothing exists there, .git/packed-refs must be a regular file of at most 1 MiB, read the same
   way. Comment lines and peel lines are skipped. Exactly one line must name refs/heads/<name>, and
   its id is the answer. No such line, or more than one, refuses.

The id is then handed to _import with the dispatch's source commit. _import requires the commit to
exist in the copied objects and to descend from the source, whatever file the id was read from. So
the reviewer's question has one answer in one place: a crafted HEAD, ref or packed-refs line can
name any id, and an id that is not a descendant of the source is refused by the same check that
guards a returned commit (binding_mismatch:build_commit, see D7). When the head equals the source
commit, _import is skipped: the phase made no commit.

### 4.6 The flag

Reporter._run_tokens looks at a journal change to an entity of kind subscription_reservation.

It returns a fact only when all of these hold: the record's type is invocation; the record's latest
report (the one at its sequence) is final; the same was not true of the record before this change.
The last condition makes the event fire on the journal row where the final report committed and on
no later change to the same record. Reports are keyed by event, journal sequence and owner
(report_id), so a second pass over the same journal sends nothing more.

Then, with tokens being the record's charge tokens:

| Case | Result |
| :- | :- |
| The charge holds no tokens value and the outcome is not not_executed | Fact: tokens unknown |
| tokens above RUN_TOKENS_FLAG | Fact: over the threshold |
| tokens at or below RUN_TOKENS_FLAG | None |

The fact has the keys every handler returns: unit (the record's context unit), run (the record's
dispatch), project (the context project), headline, fact, next and evidence (None). The fact text
names the unit, the dispatch, the tokens, the messages and the threshold. When the ledger still
lists tokens as unknown but has a number from reports made while the run was live, the text says
"at least" before the number. The unknown text says the tokens are unknown and gives the messages if
the ledger has them.

The flag reads the ledger, not the token file, so a token file that failed to write does not
silence it.

## 5. Data flows of one build

In every flow the dispatch itself is today's path: Runtime._run asks the gate, L.Runner.submit
prepares a contract with the next attempt number, the clone is made at the contract's source commit,
the receiver runs the engine, settles and records the exit.

### 5.1 First phase

1. Runtime.build takes the role and the limits, reads the spec text at the spec's base, and sets
   phase edit, dispatch count 0, source commit the spec's base, done and remains empty, state none.
2. brief builds the payload with phase edit, index 1, source.commit the base, and no state field.
3. _run dispatches it. The clone is at the base. The engine starts a new session.
4. The builder edits, commits with the state note, and answers with commit, done, note, remains.
5. The run completes. _run takes path 1: _collect imports the commit into the authority's
   repository.
6. The loop reads the note at that commit with _state, appends the done entry, takes the answer's
   remains, sets the source commit to the answer's commit, appends the phase event, and counts the
   dispatch. done true moves it to phase test; done false keeps it in edit.

### 5.2 A phase capped at the message limit

1. The payload carries phase.messages (80 by default). Metering keeps it as the cap.
2. Each chunk of the engine's stream goes through take, Metering.feed and the engine's Meter. When
   Meter.steps() reaches the cap, feed returns true and stop_cause says phase_cap.
3. take begins the stop with that cause. The stop is today's: a termination signal to the engine's
   process, then to its group, then a kill, on the configured graces.
4. Receiver._finish calls Metering.settle with the cause. The outcome is cancelled. The artifact
   document gets verdict stopped and the cause phase_cap, and is not complete. The token record is
   written. The dispatch record is exited with the artifact's digest.
5. In _run the record is not completed. Path 2 applies: bound returns the document, its cause is
   phase_cap, _gitdir passes, _head reads the head commit, _import brings it into the authority's
   repository when it differs from the source.
6. The loop gets ending phase_cap and the head commit. It appends a done entry with CAPPED_NOTE and
   that commit, leaves remains as it was, reads the note at the head commit, sets the source commit
   to the head commit, appends the phase event with ended phase_cap, counts the dispatch and stays
   in the same phase.

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
any unaccepted build's commits today.

### 5.6 A run flagged over the token threshold

1. Metering.settle sends the final report. The ledger commits it: one journal row changing the
   invocation's subscription_reservation record.
2. settle writes the token record and prunes.
3. On the channel's next pass, Reporter.sources walks the journal rows after its cursor. The row
   reaches _run_tokens, which finds a final report that was not there before and a charge above
   15,000,000 (or no token count), and returns the fact.
4. Reporter.report renders and sends it and records the report. A later pass finds the report
   recorded and sends nothing.

A run under the threshold produces no fact, so nothing is sent and nothing is recorded.

### Sequence: one capped phase and its continuation

```
 Runtime.build      Runtime._run       Receiver / Metering        Engine           Ledger
      |                  |                     |                    |                |
      | brief(edit,1)    |                     |                    |                |
      |================> | submit, clone @S0   |                    |                |
      |                  |===================> | spawn, prompt      |                |
      |                  |                     |==================> | new session    |
      |                  |                     |   stream           |                |
      |                  |                     | <================= | commit C1      |
      |                  |                     | feed: report       |   (with note)  |
      |                  |                     |=====================================>|
      |                  |                     | steps == cap       |                |
      |                  |                     | begin(phase_cap)   |                |
      |                  |                     |=== stop signal ==> | ends           |
      |                  |                     | settle: cancelled  |                |
      |                  |                     |=====================================>| final
      |                  |                     | artifact (stopped, phase_cap)       |
      |                  |                     | token record, prune                 |
      |                  |                     | Dispatches.exit                     |
      |                  | <=== exited ========|                    |                |
      |                  | bound: cause phase_cap                   |                |
      |                  | _gitdir, _head -> C1                     |                |
      |                  | _import(C1, S0)                          |                |
      | <== None, C1, phase_cap                |                    |                |
      | _state(C1) -> note                     |                    |                |
      | done += (edit, C1, capped)             |                    |                |
      | count = 1, phase stays edit            |                    |                |
      |                  |                     |                    |                |
      | brief(edit,1) with source C1, done, state.note              |                |
      |================> | submit, new clone @C1                    |                |
      |                  |===================> | spawn, prompt      |                |
      |                  |                     |==================> | new session    |
      |                  |                     | <================= | commit C2,     |
      |                  |                     |                    | answer done    |
      |                  |                     | settle: completed  |                |
      |                  |                     |=====================================>| final
      |                  |                     | artifact (complete), token record   |
      |                  | <=== exited ========|                    |                |
      |                  | artifact, answer, _collect(C2, C1)       |                |
      | <== answer, returned                   |                    |                |
      | _state(C2), done += (edit, C2, note)   |                    |                |
      | count = 2, phase -> test               |                    |                |
```

S0 is the spec's base. The second dispatch has a new dispatch id, a new clone and a new engine
session; the only things it shares with the first are the unit and commit C1.

## 6. Failure and recovery

| Failure | What happens | What is lost | Recovery |
| :- | :- | :- | :- |
| A phase is stopped in the middle of a commit | Git writes objects under temporary names and moves the branch only after the commit object exists, so the ref names either the old commit or the new one. _head reads whichever it is. Leftover lock files and temporary object files are regular files; _import copies them and Git ignores them | The work of the commit that did not finish | The next dispatch starts from the commit the ref names; its done entry says uncommitted work was lost |
| The stopped clone's head cannot be read (a link, a ref outside refs/heads, no matching packed line, a reftable clone) | _head refuses invalid_input:build_head. Runtime.build stops with that refusal. No next dispatch is made | The capped run's commits are not imported | None in this build. The next Runtime.build call for the unit starts again from the spec's base |
| The head is readable but does not descend from the source | _import refuses binding_mismatch:build_commit | Same | Same |
| The note is missing, too large, a link, or not text | _state returns missing with the reason. The next brief carries state.missing and no note. Nothing is refused | What the note would have told the next phase | The next phase works from the commits, the done list and remains |
| The token record cannot be written (directory not creatable, disk full, file exists, over 2,048 bytes) | The error name goes on Metering.errors, as for an artifact that cannot be kept. settle goes on; the dispatch ends as it would have | One file | None needed. The ledger holds the numbers and the flag reads the ledger |
| The final report to the ledger fails | Today's handling: the error name goes on Metering.errors. No token record is written, because the record promises ledger-committed numbers (D14) | The file for that run | The ledger's own handling of an unsettled invocation |
| Pruning fails for a file | The error name goes on Metering.errors; the other files are still pruned | Nothing | The next settle tries again |
| A file in run_tokens cannot be parsed | run_tokens skips it. Pruning removes it once its modification time is more than 30 days old | Nothing | None needed |
| The artifact of a capped run was not kept | bound refuses as today, so the cause cannot be confirmed and _run refuses as today | The capped run's commits | Next build call starts from the base |
| The capped run ends on a remote transport | _finish records unknown (remote_stop_unconfirmed) and the unit and station stay held. Runtime.role refuses a non-local adapter before this can happen for an installed build | | Today's handling of an unknown outcome |
| The worker Runtime's process dies between two phases | The loop state is gone. The next Runtime.build call starts at edit from the spec's base with a fresh dispatch count; the contract's attempt goes on counting | The earlier phases' work | None in this spec (D13) |

Each import leaves the commit in the authority's repository without a ref, as today's build does
before review. The next dispatch clones at that commit by id. Review already does this with the
built commit, so the phases add no new requirement on the clone path.

## 7. Existing rows that will move

A build in suite 82 is now three dispatches. The valid stand-in mode has to answer per phase: edit
makes the implementation commit and returns done true; test returns its source commit and done
true; proof makes the manifest commit and returns commit, proof and done true. Rows that assume one
build dispatch per unit, attempt 1, or a count of invocations will need their numbers updated, and
the fixture's ledger ceilings (200 invocations, capacity 40) should be checked against the tripled
count. The role's seconds is 30 and the profile's runtime 60 in that suite, so the mode that runs
past the cap must print its messages without delay.

Every line the stand-in prints must be an event of the binaries' recorded tables (rows
installation/assets and format/fake-lines). Repeated assistant events for Claude Code and repeated
item.completed events for Codex are in those tables.

Suite 72 has rows that compare the registry with the kinds the real writers commit. The new event
has to be added there with kind subscription_reservation.

Suite 86 0127 goes red until the two live captures and the four resource records are retaken, as
the spec's section on the VELDO-0127 captures says. That is the last step of the build, after the
three production files stop changing.

## 8. Acceptance criteria

The mutation runner applies exact text replacements to one module. Each behavior a mutant removes
should therefore sit at one place in the source, named in the last column.

| AC | Components | Row (suite) | Mutant | Site the mutant edits |
| :- | :- | :- | :- | :- |
| AC1 | Runtime.build loop, brief, _run | phase/fresh-dispatches (82) | phase294-single-dispatch | The loop in Runtime.build: all three phases in one _run call |
| | | | phase294-session-resumed | brief: adds resume with the session of the dispatch before |
| | | | phase294-source-not-advanced | The loop's assignment of the next source commit |
| AC2 | brief, the constants | phase/brief (82) | phase294-brief-without-reading-rule | brief: the reading field |
| | | | phase294-brief-carries-prior-answer | The loop's done entry: the whole answer text in place of the note |
| | | | phase294-brief-unbounded | brief: the cut of remains |
| | | | phase294-brief-without-note-rule | brief: the note field |
| AC3 | Metering cap check, take, STOPS, settle, _run path 2, the loop | phase/step-cap (82) | phase294-cap-unenforced | Metering.feed: the comparison of steps with the cap |
| | | | phase294-capped-work-dropped | The loop: the next source after a capped dispatch |
| AC4 | Metering.settle, Metering._record, run_tokens | tokens/run-record (75) | tokens294-record-unwritten | settle: the call to _record |
| | | | tokens294-unknown-as-zero | _record: the null for an absent tokens value |
| AC5 | REGISTRY, Reporter._run_tokens | report/run-over-tokens (72) | tokens294-flag-threshold-ignored | _run_tokens: the comparison with RUN_TOKENS_FLAG |
| | | | tokens294-unknown-not-flagged | _run_tokens: the unknown case |
| AC6 | Runtime.build loop, Runtime.limits | phase/budget (82) | phase294-dispatches-unbounded | The loop's check of the dispatch count |
| AC7 | Metering.settle prune | tokens/pruned (75) | tokens294-never-pruned | settle: the prune call |
| AC8 | Runtime._head | phase/head-read (82) | phase294-head-symlink-followed | _head: the regular-file check on HEAD |
| | | | phase294-ref-symlink-followed | _head: the regular-file check on the ref file |
| AC9 | Runtime._state, brief | phase/state-note (82) | phase294-state-note-not-carried | The loop's call to _state |

What each row has to observe, beyond the spec's wording:

- phase/fresh-dispatches: the three session ids come from the stand-in's markers (the init event's
  session id for Claude Code, the thread id for Codex). The three clone directories come from the
  markers' working directories. The source commits come from the dispatch records' contracts.
- phase/brief: the oversized case calls brief directly. The row measures P.canonical of the payload
  without spec and state.note. It also asserts the byte limits of READING_RULE, NOTE_RULE and
  OUTPUT from section 2.
- phase/step-cap: the count of 5 is read from the artifact document's own lines (assistant events,
  or completed items), not from the ledger, because the ledger's messages of a stopped Codex run
  are unknown. "Ends as it does today" for a run under the cap is covered by the suite's existing
  build rows staying green.
- phase/head-read: the two mutants remove one check each, so the HEAD check and the ref check must
  be separate statements. The third variant (a ref outside refs/heads) has no mutant and guards
  rule 2 of section 4.5.
- phase/state-note: the 8,193-byte variant must come back oversize without the blob being put in
  the payload; the row checks the payload has no state.note key.
- tokens/run-record: the third invocation's stream must carry no usage at all, so the ledger's
  charge has no tokens value (D4). The second is stopped by calling settle with the cause phase_cap
  after live reports.
- tokens/pruned: age is judged by the record's ended_at, not by the file's time.
- report/run-over-tokens: the three records are written through the real Reservations service, so
  the handler reads what the ledger writes.

## 9. Where the spec and the code disagree, and choices the spec leaves open

**D1. The Codex meter cannot see a run reach 80 messages.** The spec compares the meter's message
count with the cap. For Claude Code that count is distinct assistant messages and grows through the
run. For Codex it is completed turns (control_engine_codex.py 398 to 404), and one codex exec run is
one turn that completes at the very end (proof/VELDO-0061/codex-exec.json shows one turn.started and
one turn.completed). A live Codex build would never be capped, while a stand-in that prints several
turns would make the row green. Recommendation: add Meter.steps() to both engines and compare the
cap with it, counting completed work items for Codex, because otherwise the cap is proven in the
suite and does nothing on the engine the spec expects to carry the largest builds. The ledger's
messages stay as they are. The cost: for Codex the cap counts items, which is close to but not the
same as model requests, and the token record's messages stays the ledger's turn count. This needs
the lead's answer.

**D2. "A cancelled record whose supervision cause is phase_cap" does not exist as written.** The
dispatch record has no cancelled state and no supervision field. Cancelled is the ledger's outcome,
and supervision travels only as a message on the launch pipe (Launch.supervision). Recommendation:
decide from the artifact document's cause, read through bound, because that document is tied to the
exit record by digest and the pipe message is tied to nothing.

**D3. P.blob cannot tell a regular file from a symlink.** It returns a symlink's target as bytes.
control_proof.py is outside the footprint. Recommendation: Runtime._state lists the tree entry and
checks its mode itself, in control_launch_work.py, because the not_a_file case of AC9 cannot be met
otherwise.

**D4. A capped run's tokens are "unknown" to the ledger.** A run stopped before its result line
gives the meter no conclusive total, so Meter.final is empty for both engines. The ledger then keeps
tokens in the record's unknown list while its charge holds the highest live figure (suite 75 row
settle/missing-retained shows this today). Two parts of the spec read this differently. AC4 wants
the capped run's record to equal the charge and wants null for a stream with no usage total. AC5 and
the prose flag every run whose tokens are "still unknown", which taken literally sends the owner a
report for every capped phase, and capped phases are expected. Recommendation: in both places
"unknown" means the charge holds no tokens value at all; a live figure is used as the number, and
the report says "at least". One reason: a build can cap up to three times by design, and three
reports per build would bury the one that matters. For Codex, live reports carry no tokens before
the turn completes, so a capped Codex run is reported as unknown each time; D1's answer does not
change that. This needs the lead's answer.

**D5. The 4,096-byte bound leaves about 320 bytes for the three instruction texts.** In AC2's
oversized case, in compact JSON, ten remains lines of 200 characters take 2,041 bytes and five done
entries with 200-character notes take 1,408. The fixed fields (operation, spec_revision, producer,
phase, source, state.missing, key names) take about 325. That leaves about 320 bytes for
READING_RULE, NOTE_RULE and OUTPUT together, and today's proof instruction alone is about 330.
Non-ASCII text makes it worse: one character can cost six bytes escaped. A role that sets more than
6 dispatches adds more done entries. Recommendation: treat the cuts as upper limits and add the fit
step of section 4.4, which empties the oldest done notes first, because the bound then holds for any
input and what is dropped is the least useful text in the brief. If the row is written to require
exactly ten lines of 200 and five notes of 200 beside the proof instruction, it cannot pass; the
oversized case should use the edit phase, whose OUTPUT is short, or accept emptied notes. This needs
the lead's answer.

**D6. The answer's fields.** The spec gives commit, done and remains, and AC2 speaks of each ended
phase's note without saying where it comes from. Recommendation: section 3.3, with note as an
optional answer field, because it is the smallest addition that gives the done list its text.

**D7. A head that does not descend from the source.** The spec says the head "is kept only if it
descends", which could mean refuse or could mean continue from the source. Recommendation: refuse
with the existing binding_mismatch:build_commit, because a builder that left its source's history
has rewritten it, and continuing as if nothing happened would hide that.

**D8. Linked directories above the ref file.** AC8 tests a linked HEAD, a linked ref file and a ref
outside refs/heads. A linked refs or refs/heads directory redirects the read the same way.
Recommendation: check every directory on the path (rule 4 of section 4.5), because the claim is
"read only from regular files" and a followed directory link breaks it. A fourth variant in the row
would prove it; the spec does not require one.

**D9. A note that is not valid UTF-8.** The spec has three reasons: absent, oversize, not_a_file. A
JSON payload cannot carry arbitrary bytes. Recommendation: report not_a_file, because it keeps the
spec's three values and the rows compare them exactly.

**D10. Where the phase name goes in phase_budget:build.** Recommendation: the code is exactly
phase_budget:build and the phase is the refusal's detail, because callers and rows match on the
code. The same rule gives invalid_input:build_head one code with its reason in the detail, although
the neighboring invalid_input:build_gitdir family puts the reason after a slash.

**D11. Overrides that cannot work.** The spec lets a role set messages and dispatches and says
nothing about bad values. Recommendation: refuse dispatches below 3 and messages below 1 before the
first dispatch, because a build that cannot finish should not spend a dispatch finding out.

**D12. phase_cap in the remote stop list (_finish, 1626).** The spec asks for it. Runtime.role
refuses any adapter that is not local, so no installed build reaches that line. Recommendation: add
the name as the spec says, because a remote capped run that fell through to Dispatches.exit would be
recorded as ended without proof that the remote engine stopped.

**D13. A build interrupted between phases starts over.** The loop state is in memory. The spec adds
no durable record of a build's progress and says no record shape changes. Recommendation: accept
this in VELDO-0294, because resuming needs a stored phase record and that is a spec of its own. The
lead should know that a restarted build spends its dispatches again and that the dispatch budget
counts per Runtime.build call, not per unit.

**D14. No token record when the final report does not commit.** The spec says every settled
invocation gets a record with the numbers the ledger committed. When the final report is refused
there are no committed numbers. Recommendation: write nothing and name the error, because a record
with the meter's own numbers would claim something the ledger did not accept.

Two smaller facts, with no decision needed. Runner.wait retires the slot of a capped run with the
word failed (control_launch.py 963 to 964), since the record is not a clean exit; the token record
and the ledger both say cancelled. And the contract's attempt labels phases two and three retry, as
the spec already says.

## 10. Build order

1. Engine modules: STOPS and Meter.steps. Then control_launch.py: the cap check, stop_cause, the
   settle cause, the token record, pruning, run_tokens, the remote stop name.
2. control_launch_work.py: bound, the split of _collect, _head, _state, limits, brief, _run's third
   path, the loop.
3. control_telegram_report.py: the event and its handler.
4. Suites 82, 75 and 72: the stand-in modes, the nine rows, the moved rows of section 7.
5. check_teeth_mutations.py: the eighteen cases, each run red.
6. Sync the .veldo copies, retake the VELDO-0127 captures and resource records, run the gate.
