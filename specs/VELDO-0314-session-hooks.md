---
schema: veldo.spec/v1
id: VELDO-0314
title: "Session hooks"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop, distribution]
protected_paths: []
footprint:
  - "packs/claude/hooks/hooks.json"
  - "packs/claude/scripts/**"
  - "engine/.veldo/control_space_spool.py"
  - ".veldo/control_space_spool.py"
  - "engine/bin/veldo"
  - "bin/veldo"
  - "scripts/suites/*_veldo_0314_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0314-session-hooks.md"
  - "specs/index.md"
  - "proof/VELDO-0314/**"
behavior_bearing: true
observability:
  logs: >
    One session started and one session ended event record per session, with the session id, its working
    folder, its process id and its process start time.
  error_taxonomy: >
    None reaches the client. A hook that fails or cannot reach the authority spools its record. The ledger
    refuses the owner no project for any kind but session scratch.
acceptance_criteria:
  - id: AC1
    text: >
      The SessionStart hook leaves a session started event and a scratch item owned by the session id and
      the project or plain repository of its working folder, with the session's process id and start time
    falsified_by: >
      Record at SessionEnd only; the row for a session that never ends finds no item and fails
  - id: AC2
    text: >
      A session started in a folder inside no project and no plain repository leaves the same item with
      the owner no project, and the ledger refuses that owner for any kind but session scratch
    falsified_by: >
      Drop the record when no project matches; the row finds no item and fails
  - id: AC3
    text: >
      The SessionEnd hook leaves one session ended event and returns with nothing removed, inside the
      client's hook time limit. The row holds every remover on a fixture latch and the hook still returns
    falsified_by: >
      Remove inside the hook; with the remover held on the latch the row finds the hook still running at
      its time limit and fails
  - id: AC4
    text: >
      A hook that fails or cannot reach the authority spools its record and the session starts or ends as
      it would without the hook
    falsified_by: >
      Let the hook's failure reach the client; the row with the authority down finds the session refused
      and fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Sessions start and end with no record.
---

## Intent

A lead session writes scratch that nothing owns today. The client's SessionStart hook records the session
and its scratch; SessionEnd records that it ended. Each records and returns inside the client's time
limit, removes nothing, and never stops a session from starting or ending.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.9 (the lead session row), 8.7 (a
lead session) and 4.5 (event record). Section 12 of the design holds the ticket itself; its acceptance
criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: Session hooks. The hooks record and return. The removal that follows is VELDO-0323; installing
> the hooks is VELDO-0329.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-15: built the session notification hooks and extended the existing spool. New session
  declarations use the first configured scratch root and its session pattern; working_folder in
  that pattern is the UTF-8 hex encoding of the absolute working folder, so distinct folders do
  not alias. Session ids are single safe path components. The declaration precedes creation;
  existing unrecorded folders are refused, including on delayed replay. The hook creates no folder
  of scratch and sends no Signal. It records the exec hook's parent process and kernel start ticks.
  The installer must supply VELDO_SPACE_STATE_ROOT and either veldo on PATH or VELDO_SPACE_CLI;
  installation in client account folders remains VELDO-0329. The event CLI also accepts a state root,
  working folder, process identity and creator; its fallback spool is under the user's XDG state
  folder, in veldo. Released entries preserve the creator name, default record, for VELDO-0335.
  VELDO-0323 still owns the event command, service wiring and consumer: with today's ledger, a
  session start declares its scratch when the authority can be reached and retains the event as
  waiting. The suite's event receiver is explicitly a stand-in. The builder ran targeted rows and
  four manual falsifiers, not the full gate or the teeth driver. No acceptance criterion changed.
- 2026-11-15, fix round 2, from the re-review (verdict FIX, one finding). No acceptance criterion
  changed. `veldo space event` that cannot spool no longer leaves only a line on standard error: it
  runs the hook's chain. What is no entry (an invalid session id) is written whole under refused/
  with why. A spool folder that is refused is noted beside it and the entry is spooled under the
  XDG fallback; a state root that cannot be written is passed over for the same fallback. When no
  root takes it, one line with the verb's arguments and why is appended to
  space-session.unspooled.jsonl under the first root that can be written. The verb still exits 0 and
  still says so on standard error, now naming what was kept. Left: when neither root can be written
  at all, nothing can be recorded and the line on standard error is all there is. Rows
  round2/cli-unwritable-root, round2/cli-invalid-refused and round2/cli-unsafe-folder; four
  falsifiers registered for finding 314, one for each link of the chain (the note and the fallback
  are two). The "known and left" of the entry below is closed by this one.
- 2026-11-15, fix round, from the review of the build (verdict FIX, six findings). No acceptance
  criterion changed. No notification is dropped without a record. (1) The suite's latch is two files
  in its own temporary folder and its child is a plain fork: no semaphore, so the row runs in the
  gate's confined leg, which grants no /dev/shm. (2) The hook resolves the client's folder first (links
  followed, a trailing slash and dot segments gone); a notification that is still no entry is written
  whole under refused/ with why. (3) With no VELDO_SPACE_STATE_ROOT the hook uses the CLI's fallback,
  the user's XDG state folder, veldo. A spool folder that is refused is noted beside it and the entry
  is spooled under the fallback. When no spool takes it, or the module cannot be loaded, one line with
  the notification and why is appended to space-session.unspooled.jsonl under the state root, else
  under the fallback. (4) A deadline that fires where an entry is read ends the replay; the entry
  stays whole. (5) The CLI builds a released entry from the paths the Ledger's checks gave, and with
  no ledger resolves each path and a session's working folder. A session's --path is still checked
  and the verb now says it is not recorded: it is not refused, because suite 151 (VELDO-0313) holds
  rows in which a session event with a path is accepted and one on the protect list is refused by
  name, and that suite is outside this footprint. (6) A .partial file of this account's that is ten
  minutes old is set aside under refused/ by the next replay, under its lock. Thirteen falsifiers are
  registered for finding 314 beside the four of the build. Known and left: when `veldo space event`
  itself cannot spool, it says so on standard error and exits 0, as before.
- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-14: footprint widened, from the review of VELDO-0313 (the lead's question 3). No code is
  built by this entry. The spool holds only the three entry types the git hooks write, and AC4 has a
  hook spool its record. So the footprint gains the spool module, engine/.veldo/control_space_spool.py
  with its synced copy: its types and fields gain session_started and session_ended (the session id,
  the working folder, the process id and the process start time) and released (the paths, and the
  creator record VELDO-0335 checks), and replay hands each to the Ledger's event command as
  space-observer. It also gains both copies of the CLI, engine/bin/veldo and bin/veldo, so that the
  event verb spools when the ledger is not reachable (design 6.9) where today it returns 0 with
  nothing recorded. Since VELDO-0313's fix round the CLI's record verb refuses the kind scratch and any
  path that exists: the SessionStart hook is what declares a session's scratch folder, under the
  installation's session pattern, before the folder is made.
