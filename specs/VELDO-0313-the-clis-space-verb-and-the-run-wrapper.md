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
- 2026-11-14: FIX ROUND after the review (verdict FIX, six findings, three of them the lead's decisions).
  Code in engine/bin/veldo and its copy bin/veldo and nowhere else. The suite has 23 rows and finding 313
  has 26 falsifiers, each applied once and seen red on its row. Where a line of the entry above says
  otherwise, this entry holds.
  - Finding 1 (critical, the owner's rule). The record verb let a host script declare an existing folder
    as a session's scratch, and session ended then removed it unsaved. Now the verb records a worktree or
    an agent repository and nothing else: the kind scratch is refused (space_record_kind:scratch), and so
    are build output and evidence, and a session as the owner (space_record_session). A path that exists
    is refused whatever the kind (space_record_exists), and so is a path inside a recorded worktree or
    agent repository (space_record_inside). The verb follows design 6.2: record with a kind and a path
    declares before the creation, record with the option confirm confirms after it, and only an item the
    verb itself declared, with something now at its path. So no verb relabels existing work as something
    that is removed unsaved. Scratch is declared only by what creates it, at creation, for a path that
    did not exist: the wrapper for a run, the SessionStart hook for a session (VELDO-0314). Row
    fix1/existing-work-is-never-scratch is the reviewer's case, with session ended signalled as the
    consumer will: nothing becomes due and every planted file is on disk. Not done here, for the lead:
    the Ledger's own rule (control_space.permit, the observed thing branch) still lets space-observer
    declare session scratch at any path inside a root. Narrowing it to the session pattern folder needs
    a ticket whose footprint holds control_space.py. The verb does not look for a git repository above a
    path that does not exist yet: a project may keep its worktree root inside its repository.
  - Finding 2 (high, the lead's decision 1). The wrapper returns the command's exit status as soon as
    the command exits. It waits for nothing else, has no time limit of its own, and never stops or kills
    a process: the one signal it sends is the stop it was itself sent, passed on to the command while
    the command runs. What the command left is named on standard error and in the report, and the run's
    end follows its exit. How the processes are recorded as holding the run's items: the Ledger has one
    recorded process per item and no command by which space-runner could add more, so the scratch root
    is declared with the run's supervisor as its recorded process. The supervisor is started before the
    declare and starts the command only when told. It is the child subreaper of everything the command
    starts, and it stays for exactly as long as a descendant, a member of the group or a labelled
    process lives. Rule 3 of any judge in any process then holds the item for as long as the kernel
    shows that supervisor, with no wiring. Each wait is one poll with no time limit on a pidfd of every
    holder: an exit wakes it and the table is read again. There is no interval and no timer anywhere in
    the block (row paths/canon reads the source for it). The supervisor takes "no child left" from the
    kernel's one answer to its wait call and not from a pass over the process table: the registered
    falsifier run found that a pass can miss a child started while the table is read. The CLI's module text said it spawns nothing
    detached. It now names the one exception: this supervisor.
  - Who sends the run's end when the command left something. The supervisor, when the last holder has
    gone, by a process that follows it (the scratch root records the supervisor, so the end cannot be
    made by the supervisor itself), with the wiring that process resolves for itself. Nothing serves the
    ledger to a CLI process until VELDO-0323, so on a host today that process reaches no ledger, sends
    nothing, and the run's items and hold stay as they are for reconcile. The suite drives the same
    function (_space_ended) in its own process with its own wiring. The few lines in the supervisor that
    resolve a wiring and hand over to the follower cannot run before VELDO-0323 and have no row.
  - Finding 3 (high). The forced answer "group empty" is gone. Whether a run is over is three reads of
    the kernel, made again each time the question is asked: the supervisor has ended; the house's
    containment group was read and is empty; no process in the table carries the run's label. The group
    is the house's own provider (control_containment, the one the receiver uses for a dispatch): a
    transient scope of the owner's user manager, named for the run by the house's unit name rule and
    read through its cgroup. Two differences from a dispatch's group, both on purpose: it is in a slice
    of its own (veldo-runs.slice), because the workers' slice counts its scopes against the worker
    concurrency cap; and it carries none of the worker profile's caps and is never stopped, because a
    cap that fires is a kill, and the lead's decision is that the wrapper never kills. A host that
    cannot make the scope has no group, which is a group nobody read: nothing is sent and the hold
    stays. Rule 3 for the run is answered by the same read when the rule asks, never by a kept answer,
    and the hold is released only if the read still finds nothing after Signal. Row
    fix3/handed-outside-the-tree is the reviewer's case: a server that was running before the run starts
    a worker with the run's label; nothing is sent while the worker lives.
  - Unread processes, for the lead. The review says an environment that cannot be read counts as
    holding the run. Taken whole, that ends no run on this host: another session's sandboxed compiler
    processes are unreadable to this account and start many times a second (195 in 20 seconds on
    2026-11-14). So it is bounded as design section 7 bounds rule 4. An unread process of the owner's
    holds the run when it started at or after the run's supervisor and, going up its parents, a process
    of the run is among them or nobody whose environment was read stands above it (an orphan). It does
    not hold when it started before the run, or when the first parent that was read does not carry the
    label. The run's end sleeps on the exit of such a process as on any other holder's, so the end
    follows it and is not given up. What this does not see: a process that cannot be read and was started, with the label, by a
    process that does not itself carry it; and a process that started before the run and replaced its
    own program afterwards. Rule 4 still judges both by their files. The process reader gives no
    environment, so it does not change this. Only processes of the owner's uid are read for the label.
  - Finding 4 (the lead's decision 2). The wrapper calls the Docker part of the census (design 6.3,
    step 3) before Signal: on every engine the installation names, each container, network and volume
    that carries the run's label or its compose project name is declared as space-runner, owned by the
    run, with the identity the engine showed, and confirmed. Whose an object is is the adapter's own
    rule (owner_of), asked for this run alone. An object the protect list covers, a container that
    mounts what is protected, and one shown with no identity get no item. An engine that cannot be read
    is named and nothing of it is recorded. The suite's engine is a stand-in; no row asks a real one.
  - Finding 5. The wrapper never issues its own run. The wiring carries the authority's issue as a
    callable (issue(label, scope)), which VELDO-0323's socket request will be; the wrapper also reads
    back that the run was issued to space-runner. A wiring with no issuer records no run and the command
    runs unchanged. The block holds no call of the Ledger's issue (row paths/canon).
  - Finding 6. A scratch folder that could not be made leaves its item declared, and the wrapper says
    so; reconcile ends it. No gone is sent as space-runner, which the Ledger's rule refuses.
  - AC1 says the census, run finished and the release run "before it exits". That holds for a run whose
    group has ended when the command exits. For a run whose command left a process the lead's decision 1
    replaces it: the wrapper exits with the status and the end follows. The criterion's text is the
    design's (section 12) and is not edited here; the design's 6.9 row and this criterion want the
    lead's amendment.
  - A shared host. Run unconfined on a host where another session's sandbox starts orphaned processes
    this account cannot read, a row's end can meet one of them. The suite then lets the end follow
    that process's exit, as the supervisor does, and goes on; the row that plants such a process
    itself does not. Inside the gate's confinement the suite sees its own process table only.
  - Suite and gate. Suite 151 runs inside the gate's confinement, which has no user manager, so its
    rows are given a stand-in group, and the one row that makes the house's own scope
    (fix3/the-house-group) stands down by name there. On a host with a manager it runs for real and was
    seen green. The suite claims no manager slot and is not on the unconfined list: both are the
    lead's and the owner's to change.
