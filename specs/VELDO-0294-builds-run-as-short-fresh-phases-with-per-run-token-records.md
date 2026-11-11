---
schema: veldo.spec/v1
id: VELDO-0294
title: A build runs as short fresh phases, and every run's token use is recorded and flagged when it balloons
status: ready
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0039, VELDO-0042, VELDO-0062, VELDO-0128, VELDO-0129]
placement: [loop, fleet]
protected_paths: []
footprint:
  - engine/.veldo/control_launch_work.py
  - .veldo/control_launch_work.py
  - engine/.veldo/control_launch.py
  - .veldo/control_launch.py
  - engine/.veldo/control_engine_claude.py
  - .veldo/control_engine_claude.py
  - engine/.veldo/control_engine_codex.py
  - .veldo/control_engine_codex.py
  - engine/.veldo/control_telegram_report.py
  - .veldo/control_telegram_report.py
  - scripts/suites/82_veldo_0129_worker_wiring.py
  - scripts/suites/75_veldo_0062_accounts.py
  - scripts/suites/72_veldo_0128_reports.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0294-builds-run-as-short-fresh-phases-with-per-run-token-records.md
  - specs/index.md
  - proof/VELDO-0294/**
  - proof/VELDO-0127/claude-live.json
  - proof/VELDO-0127/codex-live.json
  - proof/VELDO-0127/resources-*.json
behavior_bearing: true
observability:
  logs: >
    Runtime.events (control_launch_work.py) gains one entry per phase dispatch: the unit, the phase
    name and index, the dispatch, the source commit, the commit the phase ended on and how it ended
    (returned, phase_cap). A build that uses up its dispatches is refused phase_budget:build, with
    the phase it stopped in.
  metrics: >
    One run token record per settled subscription invocation, in the receiver's run_tokens
    directory: tokens, messages, wall seconds, outcome, unit, station, phase and account.
    run_tokens(config) reads them.
  traces: >
    None. The phases of one build are joined by the unit and by each phase's source commit, which
    is the commit the phase before it ended on.
  error_taxonomy: >
    Three new names. phase_cap is a stop cause of one engine run (the run reached its message cap).
    phase_budget:build is a refusal of Runtime.build (the build used every dispatch it is allowed
    and the last phase is not done). invalid_input:build_head is a refusal of a capped run whose clone
    head cannot be read as plain bytes from .git/HEAD and its ref (a link, or anything not a commit
    id or a branch ref). No existing refusal changes its name or meaning.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Runtime.build runs a build as the phases edit, test and proof, in that order. Each
      phase is its own build dispatch with its own clone and its own engine session, no phase
      resumes a session, and each phase after the first starts from the commit the phase before it
      ended on. Set: one build of a fixture unit through suite 82's stand-in engines, once with the
      Claude Code engine and once with Codex. Completeness: row phase/fresh-dispatches (printed
      with the prefix VELDO-0294) requires, for each engine, three dispatch records at station
      build for the unit, with three different dispatch ids and three different clone directories;
      no contract payload with a resume key, so control_reservation_runtime.boundary names none of
      them follow_on; three different engine session ids in the stand-in's markers; the first
      contract's source commit equal to the spec's base; the second's equal to the commit the first
      phase returned, and the third's to the commit the second returned; and the result Runtime.build
      returns naming the commit and proof of the third phase, which is the newest build dispatch the
      floor reads (dispatch.py _build_dispatch). Red at 6ee5bb5f, where Runtime.build makes one
      _run call (control_launch_work.py:247) and the unit has one build dispatch.
    falsified_by: >
      Run the three phases inside one dispatch. Registered mutant phase294-single-dispatch must
      turn phase/fresh-dispatches red. Put the session id of the phase before into the next
      payload as resume. Registered mutant phase294-session-resumed must turn phase/fresh-dispatches
      red. Start every phase from the spec's base. Registered mutant phase294-source-not-advanced
      must turn phase/fresh-dispatches red.
  - id: AC2
    text: >
      Claim: the brief of a phase is its dispatch payload, and it carries the committed state, what
      is done, what remains and the partial-read rule, and nothing of an earlier session's
      conversation. Set: the three payloads of the build in AC1, and one payload built from a
      phase result whose remains list is 40 lines of 400 characters, following five ended phases
      whose notes are 2,000 characters each. Completeness: row
      phase/brief (prefix VELDO-0294) requires each payload to carry phase (name, index, of,
      messages and soft, with soft equal to messages minus 10 and never below 1),
      source.commit equal to the contract's source commit, done (one entry per ended
      phase dispatch: phase, commit and a note), remains (the list the phase before returned),
      reading equal to READING_RULE, note equal to NOTE_RULE, and output naming what this
      phase returns. It requires the
      payload without its spec text and its state note to be at most 4,096 bytes of JSON, for
      the oversized result
      too, where remains is cut to 10 lines of 200 characters and each done note to 200
      characters, with five done entries whose notes are 2,000 characters each. And it requires no
      payload to hold
      the final answer text of an earlier phase beyond its note and remains. Red at 6ee5bb5f, where
      the build payload has none of phase, source, done, remains, reading or note
      (control_launch_work.py:242 to 246).
    falsified_by: >
      Build the payload without the reading rule. Registered mutant phase294-brief-without-reading-rule
      must turn phase/brief red. Copy the whole final answer of the phase before into the payload.
      Registered mutant phase294-brief-carries-prior-answer must turn phase/brief red. Leave remains
      uncut. Registered mutant phase294-brief-unbounded must turn phase/brief red.
      Build the payload without the note rule. Registered mutant phase294-brief-without-note-rule must
      turn phase/brief red.
  - id: AC3
    text: >
      Claim: an engine run that reaches its phase's message cap is stopped with the cause
      phase_cap, the commits it made are kept, and the next dispatch continues the same phase from
      the last of them. Set: suite 82's
      stand-in engine in a mode that commits one file and then keeps answering without ending, with
      phase.messages 5 and phase.dispatches 4. Completeness: row phase/step-cap (prefix VELDO-0294)
      requires the first dispatch's artifact document to name the stop phase_cap after the meter
      counted 5 messages; its ledger invocation to end cancelled; the second dispatch to be the
      same phase, with a source commit equal to the commit the stopped run made and with that commit
      in its done list. A run that stays under
      the cap ends as it does today. Red at
      6ee5bb5f, where nothing counts a run's messages against a cap of its own and the stand-in runs
      to the role's deadline.
    falsified_by: >
      Never compare the meter's messages with the cap. Registered mutant phase294-cap-unenforced
      must turn phase/step-cap red. Start the next dispatch from the stopped phase's source
      commit. Registered mutant phase294-capped-work-dropped must turn phase/step-cap red.
  - id: AC4
    text: >
      Claim: Metering.settle writes one run token record for every subscription invocation it
      settles, with the numbers the ledger committed. Set: three invocations in suite 75: one
      completed, one stopped by phase_cap, and one whose stream ends without a usage total.
      Completeness: row tokens/run-record (prefix VELDO-0294) requires one file per invocation in
      the run_tokens directory, mode 0600, at most 2,048 bytes, holding schema veldo.run_tokens/v1,
      the dispatch, invocation, unit, station, phase, attempt, account, provider, boundary, tokens,
      messages, wall_seconds, outcome and ended_at. tokens, messages and wall_seconds equal the
      charge of the ledger's invocation record (control_reservations) for the first two. tokens is
      null for the third and never 0. run_tokens(config) returns the three, newest first. Red at
      6ee5bb5f, where the receiver writes no such file.
    falsified_by: >
      Skip the write. Registered mutant tokens294-record-unwritten must turn tokens/run-record red.
      Write 0 where the ledger holds tokens as unknown. Registered mutant tokens294-unknown-as-zero
      must turn tokens/run-record red.
  - id: AC5
    text: >
      Claim: the Telegram report tells the owner once about every run whose settled tokens are over
      RUN_TOKENS_FLAG (15,000,000) or unknown, and says nothing about a run under it. Set: three
      settled invocation records in suite 72's store: 8,000,000 tokens, 15,000,001 tokens, and
      tokens unknown. Completeness: row report/run-over-tokens (prefix VELDO-0294) requires no
      report for the first; one report of event run_over_tokens for the second, whose text names
      the unit, the dispatch, the tokens, the messages and the threshold; one for the third, whose
      text says the tokens are unknown; and a second pass over the same journal to send nothing
      more. Red at 6ee5bb5f, where REGISTRY (control_telegram_report.py:140) has no event that
      reads a subscription_reservation record.
    falsified_by: >
      Report every settled run. Registered mutant tokens294-flag-threshold-ignored must turn
      report/run-over-tokens red. Treat unknown tokens as under the threshold. Registered mutant
      tokens294-unknown-not-flagged must turn report/run-over-tokens red.
  - id: AC6
    text: >
      Claim: Runtime.build refuses phase_budget:build once a build has used phase.dispatches
      dispatches and the proof phase has not returned. Set: suite 82's stand-in in the mode of AC3,
      with phase.messages 5 and phase.dispatches 4. Completeness: row phase/budget (prefix VELDO-0294)
      requires Runtime.build to raise phase_budget:build naming the phase it stopped in after the
      fourth dispatch, and no fifth dispatch record for the unit. Red at 6ee5bb5f, where a build is one
      dispatch and nothing counts them.
    falsified_by: >
      Drop the dispatch count. Registered mutant phase294-dispatches-unbounded must turn phase/budget
      red.
  - id: AC7
    text: >
      Claim: Metering.settle removes every run token record whose ended_at is more than 30 days
      before it and keeps the rest. Set: in suite 75, one record dated 31 days and one dated 29 days
      before a settle. Completeness: row tokens/pruned (prefix VELDO-0294) requires the 31-day file to
      be gone and the 29-day file and the new record to remain after that settle. Red at 6ee5bb5f,
      where no record is written or removed.
    falsified_by: >
      Never remove an old record. Registered mutant tokens294-never-pruned must turn tokens/pruned
      red.
  - id: AC8
    text: >
      Claim: the head commit of a capped run is read only from regular files, and a head that cannot
      be read that way is refused. Set: suite 82's stand-in in the mode of AC3, with phase.messages
      5, in three variants: .git/HEAD a symlink to a file naming the stopped commit, .git/HEAD naming
      a ref whose file under .git/refs/heads is a symlink, and .git/HEAD holding a ref outside
      refs/heads. Completeness: row phase/head-read (prefix VELDO-0294) requires each variant to end
      refused invalid_input:build_head with no second dispatch record for the unit. Red at 6ee5bb5f,
      where a capped run is not collected at all.
    falsified_by: >
      Follow a symlinked .git/HEAD. Registered mutant phase294-head-symlink-followed must turn
      phase/head-read red. Follow a symlinked ref file. Registered mutant
      phase294-ref-symlink-followed must turn phase/head-read red.
  - id: AC9
    text: >
      Claim: the brief of every build dispatch after the first carries, in full, the phase state note
      found at proof/<unit>/phase-state.md in the commit the dispatch before it ended on. Set: suite
      82's stand-in in the mode of AC3, with phase.messages 15, in four variants of the commit it
      makes before it is stopped: a note of 6,000 bytes, a note of 8,193 bytes, no note, and a
      symlink at the note's path. Completeness: row phase/state-note (prefix VELDO-0294)
      requires the second dispatch's payload to carry state.note equal, byte for byte, to the
      6,000-byte note in the
      first variant; and in the other three to carry no state.note and state.missing equal to
      oversize, absent and not_a_file, in that order. Red at 6ee5bb5f, where the build payload
      has no state field (control_launch_work.py:242 to 246).
    falsified_by: >
      Build the next payload without reading the note. Registered mutant
      phase294-state-note-not-carried must turn phase/state-note red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. Runtime.build again runs a build as one dispatch, no run has a message cap of
  its own, and no run token record or run_over_tokens report is written. The run_tokens directory
  can be deleted. Nothing else reads it. Dispatch, ledger and floor records written while this
  change was in place stay valid, because none of their shapes change.
  A revert changes control_launch.py and both engine modules again, so the VELDO-0127 live captures
  and resource records are retaken with the revert.
---

## Intent

Owner requirement, Dmitry, Telegram 40759, 2026-11-11: "veldo should also build this way!"

"This way" is how the assistant that builds his own projects changed its builds that day. A build
used to be one long engine
session. Measured on 2026-11-11, two such builds used 64M and 70M tokens, one of them in 217 turns.
Almost all of that is the session's context, a few hundred thousand tokens in this repository, read
again at every turn. After builds were split into short sessions that each start fresh, no run used
more than 8M.

Veldo's own builder still works the old way. Runtime.build (control_launch_work.py:238) writes one
payload holding the whole task and makes one _run call (line 247). That is one dispatch
(control_dispatch), one clone (control_clone), and one engine session that lasts until the role's
deadline. Nothing in the payload tells the builder to read parts of large files. The ledger
(control_reservations) does record each invocation's tokens and messages, but nobody is told when one
run uses ten times what it should.

A phase is one build dispatch. Runtime.build runs the phases edit, test and proof. Edit traces the
code paths and makes the change. Test runs the tests and fixes what fails. Proof writes the evidence
and the manifest. Each phase is a _run call, so it gets a new dispatch id, a new clone and a new
engine session through the path VELDO-0129 already built. No payload carries resume, the key that
makes Metering continue a CLI session (control_launch.py:2551), so a phase never inherits a context.

The brief is the dispatch payload. Besides the spec text and the fields it has today, it carries the
phase (name, index, of, messages, soft), the source commit, a done list with one entry per phase
dispatch
that has ended, the remains list the phase before returned, and READING_RULE, a constant in
control_launch_work.py: read only the parts of a large file you need, by search and line range,
and never a whole large file. Without the spec text and the state note the payload is at most
4,096 bytes.

The phase state note is how a phase tells the next one what it knows. The owner asked (Telegram
40812) whether a new session loses the context and makes mistakes afterwards. It keeps only what is
written down: the commits, the spec and this note. The note is the file proof/<unit>/phase-state.md
in the builder's clone, at most 8,192 bytes of UTF-8 text, with four headings: done, left, decisions
made, and approaches tried and rejected.

The request was to tell the running builder once, 10 messages before the cap, to commit and write
the note. Nothing can deliver that message today. The receiver writes a run's input once and then
closes it: the feed thread in Receiver._reap (control_launch.py:2258 to 2275) closes the worker's
input after the prompt. Codex takes its one prompt from that input and reads nothing after it
(control_engine_codex.py:966). The Claude Code engine holds its input open only until the prompt,
which is its last write (control_engine_claude.py:1709). The only thing the receiver can send a
running engine is a stop.

So the phase writes the note at commit time. NOTE_RULE, a constant in control_launch_work.py that
every payload carries as note, tells the builder to bring the note up to date in every commit it
makes, and to stop new work once it has used phase.soft messages, then commit and finish the note.
phase.soft is phase.messages minus 10, and never below 1: 70 of the default 80. The builder counts
its own messages, and nothing checks that it does. That is why the note goes into every commit: a
run stopped at the hard cap still leaves the note of its last commit. The hard cap is unchanged.

Runtime.build reads the note from the commit a dispatch ended on, after that commit is imported
into the authority's repository, with P.blob. The path must be a regular file in the commit's tree
and at most 8,192 bytes. The next payload then carries it whole as state.note. Otherwise the payload
carries state.missing with absent, oversize or not_a_file, and no note text. A missing note refuses
nothing. The proof phase deletes the note in the commit that adds the manifest, because the note is
working state and not evidence.

A phase ends in one of two ways. The engine returns its JSON answer with commit, done and remains,
and _collect (line 183) imports that commit as it does today. Or the run reaches the phase's message
cap. Metering already counts messages from the engine's stream for the ledger. It now also compares
that count with payload.phase.messages, and the receiver stops the engine with the cause phase_cap
where it stops one for usage_cap today (control_launch.py:2322). phase_cap joins STOPS in both
engine modules, so the artifact document names it.

phase_cap is added to the causes Metering.settle settles as cancelled (control_launch.py:2702) and to
the causes the remote path treats as a stop (_finish, line 1626). _run returns a capped build run to
Runtime.build instead of refusing it: a cancelled record whose supervision cause is phase_cap is the
one exception to the completed-record check at control_launch_work.py:165, and it carries no answer.
Runtime.build then reads the stopped clone's head commit as plain bytes, never by running Git and
never by following a link. After _collect's directory checks it reads .git/HEAD, which must be a
regular file holding either 40 hex digits or "ref: refs/heads/<name>". A ref is read from
.git/refs/heads/<name>, which must be a regular file, or from the one matching line of
.git/packed-refs. Anything else refuses invalid_input:build_head. The id is then imported exactly as
_collect imports a returned commit, from a copy of the objects into the authority's own temporary
repository, and it is kept only if it descends from the phase's source commit. If it equals the
source commit, the phase made no commit and the next dispatch starts from the same commit. Work that
was not committed is lost with the clone, and the brief says so.

The next phase starts from the commit the last one ended on. If the answer said done, it is the
next phase in order. Otherwise it is the same phase again with the new remains. A build may use
phase.dispatches dispatches. When they are used up and the proof phase has not returned, Runtime.build
refuses phase_budget:build. The defaults are constants in control_launch_work.py: 80 messages per
phase and 6 dispatches per build. A role may set others under work.builder.phase in the worker
configuration. The role's seconds stays the deadline of each dispatch.

The token record is a small file. Metering.settle (control_launch.py:2684) already sends the final
usage report to the ledger. Right after it, settle writes one JSON file into the run_tokens
directory, which lies beside the store unless the receiver configuration names run_tokens, the same
rule as receipts and artifacts. The file is named by the digest of the invocation and holds what AC4
lists. On every settle the receiver removes the files whose ended_at is more than 30 days old.
run_tokens(config) in control_launch.py returns the kept records, newest first. Review and
coordination runs get a record too, since settle is the same for every station.

The flag is a Telegram report. control_telegram_report already walks the committed journal and sends
the owner one report per enabled event. REGISTRY gains run_over_tokens, read from the
subscription_reservation records the ledger writes. Its handler reports an invocation record when its
final report commits and its charged tokens are above RUN_TOKENS_FLAG, or its tokens are still
unknown. The threshold is 15,000,000, the figure the owner's own check uses. The report goes out on
the channel's next pass, so the owner hears about a run that used too many tokens on the reporter's
next pass after it settles.

## VELDO-0127 captures

The change to control_launch.py, control_engine_claude.py and control_engine_codex.py makes the
VELDO-0127 live captures and resource records stale, because they bind those files by digest.
Retaking them is part of this ticket: .veldo/qualify.py for the four resource records, and
proof/VELDO-0127/live.py once for codex and once for claude for the two captures. The Claude capture is
taken from outside a run, because a run holds the login lease. Suite 86 0127 passes every row before
review.

## Owner decisions

Three numbers are Dmitry's to set. Each has a default the build uses unless he picks another, and the
spec does not become ready until he has answered.

Messages per phase, default 80. A turn in this repository re-reads a context of a few hundred thousand
tokens, so 80 turns of a fresh session come to roughly 8M, the most any phased run used on
2026-11-11. The 217-turn build that used 70M would have been stopped well before a quarter of its
length. A lower cap stops more phases mid-work and costs a continuation dispatch each time. The soft
limit is the cap minus 10, so 70 at the default.

Dispatches per build, default 6. That is the three phases plus one continuation each. A build that
needs more than that is larger than one spec should be, and is refused rather than left to run.

Flag threshold, default 15,000,000 tokens. It is the number his own check of his assistant's runs
already uses. It is about twice the largest phased run measured on 2026-11-11 (7.9M), so a normal
phase stays quiet and a run that goes back to the old one-session pattern is reported.

## What this spec leaves alone

The floor. dispatch.py still accepts a build from the unit's newest build dispatch and compares that
dispatch's answer with the commit and the proof manifest. The proof phase is that dispatch, and its
answer has the shape a whole build returns today.

The dispatch contract and its record. CONTRACT_FIELDS, the states and the exit fields in
control_dispatch.py don't change. The phase lives in the payload. The contract's attempt goes on
counting the unit's build dispatches, so control_reservation_runtime.boundary names the second and
third phases retry. That label is wrong for a phase and this spec does not fix it. The run token
record carries the phase beside the boundary.

The ledger. control_reservations and its caps are untouched. A phase's message cap is not a ledger
cap: it stops one run and refuses nothing.

Review. A review is already one short dispatch on a fresh clone. It gets a run token record and
nothing else changes.

The worker configuration setup writes (control_factory_setup_dispatch.py). The defaults live in
control_launch_work.py, so an installed factory builds in phases without a new setup run.

The Usage screen of the UI. It reads the ledger's totals and does not list runs. Showing the run
token records there is separate work.

Which engine builds. Preferring Codex for the largest builds is a choice of the team's roles, not of
this code.

## What the reviewer judges

Whether the head commit of a stopped clone is read only as the bytes of regular files, and whether a
crafted HEAD, ref or packed-refs file can name a commit that does not descend from the phase's source.

## History

2026-11-11: drafted from the owner's requirement (Telegram 40759) and the note on builds in
short phases
2026-11-11: amended from its independent review (spec-veldo-0294-review-2026-11-11.md, verdict
CHANGES), findings F1 to F6 applied with the review's replacement text. Where the text differs from
the review: F2 adds the function name _finish to the remote path at control_launch.py:1626, and its
replacement starts a new paragraph; F4's new criteria are AC6 (dispatch budget) and AC7 (pruning),
after AC5, so AC3 keeps phase.dispatches 4 in its set without a claim on it; F6a leaves "the lead's
runs" in the Owner decisions section because that sentence is the review's own F3 text. Not in the
review and left for the owner: error_taxonomy still says "two new names" although F2 adds the
refusal invalid_input:build_head, and the three owner values are not yet answered, so status stays
draft.

2026-11-11: error_taxonomy corrected to name the three new names, including invalid_input:build_head.
2026-11-11: re-review N1 to N3 applied: the head-read refusal is its own criterion, AC8.
2026-11-11: owner concern (Telegram 40812, answered in 40813) applied: the phase state note. Added AC9
and the note's design. No running engine can be sent a message, so the note is written at commit
time and the soft limit (the cap minus 10) is given in the brief. AC2's 4,096-byte bound now excludes
the state note. No new footprint path: the code, the suite and the mutant registry are already
listed, and this unit's own note falls under proof/VELDO-0294/**.
2026-11-11: re-review 2 C1 and C2 applied: the note rule and phase.soft belong to AC2 with their own
mutant; AC9 keeps one claim.
2026-11-11: approved by the owner with the defaults 80 messages per phase, 6 dispatches per build and a 15,000,000 token flag (Telegram 40816; the state note written at every commit instead of a soft-limit message was explained to him in 40817). Status ready.
