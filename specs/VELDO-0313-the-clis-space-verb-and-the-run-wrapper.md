---
schema: veldo.spec/v1
id: VELDO-0313
title: "The CLI's space verb and the run wrapper"
status: ready
risk: high
owner: dmitry
human_approval: required
lane: standalone
parent: VELDO-0295
depends_on: [VELDO-0301]
placement: [engine, loop]
protected_paths: []
footprint:
  - "engine/bin/veldo"
  - "bin/veldo"
  - "scripts/suites/*_veldo_0313_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0313-the-clis-space-verb-and-the-run-wrapper.md"
  - "specs/index.md"
  - "proof/VELDO-0313/**"
behavior_bearing: true
observability:
  logs: >
    space run prints the numbers when the run would wait, and records the run's items, census and outcomes
    as a receiver does.
  error_taxonomy: >
    space run exits with the command's own status. In act mode with too little space it exits 75 with the
    numbers and does not start the command. record and event refuse an unknown kind or event type, a path
    outside every known root and a path on the protect list, each by name. With no central installation
    each verb says so and space run runs the command unchanged.
acceptance_criteria:
  - id: AC1
    text: >
      space run declares the run with its station, scratch root, label and compose project name, starts
      the command in its own containment group, and after the command and the group end runs the census,
      run finished and release before it exits
    falsified_by: >
      Skip the census; the build folder the command made has no item, stays, and the row fails
  - id: AC2
    text: >
      space run exits with the command's own status. In act mode with too little space it exits 75 with
      the numbers and does not start the command; in report mode it prints the numbers and starts it
    falsified_by: >
      Start the command anyway in act mode; the row finds the command's marker file and fails
  - id: AC3
    text: >
      record and event refuse an unknown kind or event type, a path outside every known root and a path on
      the protect list, each by name; the event types are ref changed, session started, session ended and
      released
    falsified_by: >
      Accept any path; the row that records a folder outside the roots gets an item and fails
  - id: AC4
    text: >
      With no central installation each verb says so, and space run runs the command unchanged
    falsified_by: >
      Refuse to run; the row's command never starts and the row fails
required_evidence: [unit, integration]
rollback: >
  Revert the change. Commands started from a shell run unwrapped, with no admission and no removal at
  their end.
---

## Intent

A builder or a gate started from a shell is outside the receiver. The CLI's space run wraps such a
command: it asks admission, declares the run with its station, scratch root, label and compose project
name, starts the command in its own containment group, and afterwards runs the census, run finished and
the release. The record and event verbs let a host script report what it made and what it gave up.

## Design

This is one of the forty-eight build tickets of VELDO-0295. The design is
docs/design/VELDO-0295-design.md. Design sections this ticket builds: 6.9 (the run wrapper rows), 6.3
(what a run is given), 6.7 (admission) and 3 (the CLI's verb space). Section 12 of the design holds the
ticket itself; its acceptance criteria and falsifiers are copied here word for word.

What section 12 says about this ticket:

> Components: CLI.

Build order. It is built after 0301, in any order with the other tickets of that step (0302, 0303, 0305 to
0314, 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341). The design states no dependency for this
ticket, so depends_on holds the step before it in the build order.

Footprint. The files are the ones the design's component table (section 3) gives for this ticket's
components, each engine file with its synced copy, and the ticket's suite, proof and spec.

## History

- 2026-11-13: written from design revision 6 (commit 5d9d3ce0), after its sixth validation (verdict
  VALID). Status ready.
- 2026-11-14: built, in engine/bin/veldo and its copy bin/veldo and nowhere else. Suite
  scripts/suites/151_veldo_0313_space_run.py, 14 rows; eleven falsifiers registered under finding 313, the
  four declared ones among them, each applied once and seen red on its row. What the build decided, and
  what it leaves to other tickets:
  - Nothing here deletes anything and there is no new way to remove. At a run's end the wrapper calls
    Signal (control_space_signal) with run finished; what goes is removed by the removers after the seven
    rules and the keep step, as for the receiver. The census is the receiver's own (control_launch
    space_census): what is work gets no item and stays.
  - No verb acts as the authority or as the owner, and none falls back to either. The wrapper writes as
    space-runner and the record and event verbs as space-observer, each through the Ledger's own apply,
    which runs the Ledger's rule for that principal before the command. The one command that is not the
    runner's is the issue of the run, which is the authority's. So the wrapper signals only run finished,
    with exactly its own run as the subject: the Ledger refuses it a signal for another run, a signal that
    names items, worktree abandoned and the owner's Keep, and never makes an item due that the owner
    marked Keep.
  - Run finished is sent only when the kernel says the run is over. The command runs under a supervisor
    process (the CLI's own verb supervise) that is the child subreaper of everything the command starts,
    so a process that forks twice or leaves its session is still counted. The wrapper waits for the
    command and for every such process. A group nobody could read (a host with no subreaper, a
    supervisor that died) sends nothing: no census, no signal, no release, and the hold stays held.
    Nothing here stops or kills a process of the run; a stop sent to the wrapper is passed on to the
    command.
  - The need of a wrapped run is what the project's space file declares for the station, else the pool's
    default from the installation. The measured need and the freed mark are VELDO-0316 and 0334. A run
    that must wait in act mode is not queued: its hold is released and it exits 75.
  - A run inside no project and no plain repository gets its hold and its label and no folder: the
    Ledger accepts no project as an owner only for a session's scratch.
  - The Docker part of the census (design 6.3, step 3) is not called from the wrapper: the receiver's
    census does not call it either, and a run's labelled objects are recorded by the adapter's own
    snapshot and event stream (VELDO-0306). The build root is given by the receiver's seam only.
  - WIRING, NOT BUILT HERE. The verbs take the mapping an installation wires in (the one the receiver is
    given). Nothing serves the ledger to a CLI process yet: the authority's socket is VELDO-0323's. Until
    then a CLI started from a shell on a host with an installation says the space ledger is not
    reachable; the wrapper then runs its command unchanged, and record and event record nothing. The
    suite makes the wiring itself.
  - The event verb checks the type and every path it names and hands the event to the Ledger's event
    command as space-observer. That command is VELDO-0323's (released: VELDO-0335). Until it is built the
    Ledger answers space_no_command:space_event, the verb says the event is not recorded, and nothing
    becomes due. The spool (control_space_spool) holds only the three entry types the git hooks write;
    which ticket lets it hold a session event or a released event is open, and is a question for the
    lead: the footprints of VELDO-0314, 0323 and 0335 do not name that module.
  - The declared falsifier of AC3 says the row "gets an item". With the CLI's own check taken out the
    Ledger still refuses the path, so no item is made; the row is red because the refusal no longer has
    its name.
