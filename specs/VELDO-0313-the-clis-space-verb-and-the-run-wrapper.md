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
  - "scripts/gate_unconfined.json"
  - "scripts/suites/101_veldo_0208_landing_reuse.py"
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
- 2026-11-14: FIX ROUND 2, the lead's decision. Code in engine/bin/veldo and its copy bin/veldo and
  nowhere else. The suite has 23 rows and finding 313 has 30 falsifiers. Where a line above says
  otherwise, this entry holds.
  - REVERSED: unread processes. The first fix round bounded "an environment that cannot be read counts
    as holding the run" by the process's parents, so that runs end on this host. That was fail open
    and is gone. Per design section 7 and the owner's decision (Telegram 41204 and 41205): a process
    whose environment cannot be read may carry the run's label, so it holds the run for as long as it
    lives, whoever it belongs to and whatever started it. Processes of every uid are read now, not
    only the owner's. One thing takes a process out, and it is what the kernel says with no
    environment read: it started before the run began (before the start of the run's supervisor, field
    22 of its stat file) and it is no descendant of the supervisor and no member of the run's
    containment group. Nothing else takes one out: not its uid, not its name, not the process that
    started it. A kernel thread is not read at all: it has no environment (PF_KTHREAD in its stat
    file). What the one exclusion does not see: a process from before the run that later replaced its
    own program with one given the label. Rule 4 still judges that one by its files.
  - WHAT THIS COSTS, RECORDED AS ASKED. On a host without the process reader (VELDO-0344), a run whose
    processes cannot all be read ends only when those processes exit. The run's supervisor stays, the
    wrapper names them, run finished is not sent, nothing of the run is judged or removed, and the
    hold stays held. On this host, measured on 2026-11-14: 423 processes this account cannot read,
    190 of them younger than 20 minutes (database backends in containers, container proxies, another
    session's sandbox), and new ones every second. So here, today, no wrapped run ends: each stays
    open until every such process that started after it has exited, and others start meanwhile.
    Nothing is lost by that; nothing is cleaned either.
  - THE OWNER'S READER INSTALL REMOVES THIS. The wrapper asks the process reader through the probe's
    own read (control_space_probe.reader_read, with every check that function makes), and only when a
    process is unread. When the reader's state is used, a process it shows with a whole block and the
    start time the kernel shows is read: it is no unread holder, and rule 4 judges it by the files it
    holds, as the probe does. With the reader installed every process has such a block, so nothing is
    unread and a run ends when its own processes have. A reader that is absent or refused, a process
    with no block, a block that is not whole and a block with another start time change nothing: the
    process holds. Said plainly: the reader prints files, not environments, so with it a process is
    judged by what it holds and not by a label nobody read.
  - The row and its falsifiers. fix3/unread-process-holds: an unread process that started after the
    run began keeps the run open, an orphan and one the suite itself started alike; nothing is sent
    or written and the hold stays; the one from before the run is not named. A reader that shows no
    block for it, a block that is not whole, a block with another start time, or that is refused,
    changes nothing. With the reader used and a whole block the run is over while the process lives.
    Falsifiers, each red on that row: space313-unread-bounded-by-a-read-parent (the first fix round's
    bound put back), space313-unread-started-after-the-run-left-out,
    space313-unread-process-not-counted, space313-reader-block-not-checked,
    space313-reader-not-used-taken-as-used.
  - Note 2, the scope's slice and caps. A wrapped run's scope is in veldo-runs.slice and carries no
    cap. It stays so. In the workers' slice a wrapped run would count against the worker concurrency
    cap and take a worker's place. A cap of the worker profile that fires is a kill by the kernel or
    by the manager, and the lead's decision 1 is that the wrapper never kills. What it costs: a
    wrapped command is limited in memory and in tasks by nothing of Veldo's, as a command started
    from a shell is. Putting a limit on it is the lead's to decide, and would be a kill.
  - Note 3, the follower and the ledger. When a run is not over at the command's exit, the end is
    made later by the process that follows the run's supervisor. Nothing serves the ledger to a CLI
    process until VELDO-0323, so on a host today that process reaches no ledger and sends nothing:
    the run's items and its hold stay as they are, for reconcile. Until fix round 2 that was the case
    of a command that left a process. With unread processes holding, it is the usual case on a host
    without the reader: until VELDO-0323 is built and the reader is installed, most wrapped runs on
    such a host end with no run finished. Nothing is removed that should not be; what the run left is
    not cleaned until reconcile.
  - Note 4, fix3/the-house-group. The gate's confinement has no user manager, so there the row
    stands down by name and asserts nothing: the gate does not prove the house's own scope for a
    wrapped run. It needs a host with a manager, which means unconfined, which on this host means a
    process table shared with other sessions. In the first fix round it was seen green here. In this
    round it cannot be: the run's end waits for other sessions' unread processes, as decided, and the
    row is red after the suite's limit. To have it proven by the gate the suite needs a row on the
    unconfined list and a host with the reader, or a process table of its own with a manager in it.
    Both are the lead's and the owner's.
  - The suite. In a process table of its own (the gate's confinement, the mutation workers) all 23
    rows are green. Unconfined on this host, 8 rows were green and 15 red in the one run made: an end
    held by other sessions' processes, and what follows from a hold that was not released. The suite
    no longer waits without bound for such a process: a row that follows an end is red after 120
    seconds and says what held it. The first fix round's "seen green 8 times on this host" was under
    the bound that is now gone.
- 2026-11-14: FIX ROUND 3 after the re-review of rounds 1 and 2 (verdict FIX: two HIGH, one MEDIUM).
  Code in engine/bin/veldo and its copy bin/veldo. The owner's rule (Telegram 41209): no work is ever
  lost.
  - Finding 1 (HIGH), the reader's block is not a read of the label. Round 2 left an unread process
    out when the process reader's state was used and its block for the process was whole with the
    kernel's start time. A block holds the files of a process and no environment, so with the reader
    installed a live process that carried the run's label and could not be read had the run's scratch
    removed under it. That exclusion is gone: a block rules nothing out, whole or not, and round 2's
    paragraph "THE OWNER'S READER INSTALL REMOVES THIS" is withdrawn. Two things, and nothing else,
    take an unread process out. One is the lead's decision of round 2, unchanged: it started before
    the run began and is no descendant of the supervisor and no member of the group. The other is the
    label itself, read by the reader, which VELDO-0344 adds in its own change; until that lands and
    the reader is installed, an unread process that started after the run holds it on every host.
    Row fix3/unread-process-holds now ends the other way: with a reader used and a whole block the
    run stays open, its file is on disk and the hold is held, and the run ends only when the process
    has ended. Falsifier space313-reader-block-taken-as-label-read is the code as it was. Cases
    space313-reader-block-not-checked and space313-reader-not-used-taken-as-used mutated lines that
    no longer exist and are withdrawn with them.
  - Finding 2 (HIGH), the supervisor kept the caller's output. A supervisor that stays held the
    wrapper's descriptors 0, 1 and 2, so a caller that read the wrapper's output to its end waited
    for what the command left: with a daemon, without bound. Before it writes the status line, a
    supervisor that has something to stay for points 0, 1 and 2 at /dev/null (_space_let_go); the
    process that follows it inherits that. Nothing is closed and nothing is signalled. Row
    fix2/captured-output-ends-at-return: the suite puts a pipe on the wrapper's standard output and
    standard error, as a shell's $(...) does, around a command that leaves "sleep infinity"; the
    wrapper returns at once, the read of the pipe ends at once with the command's own line, the
    supervisor's three descriptors are /dev/null and the run is held until the suite ends the sleep.
    Falsifier space313-supervisor-keeps-the-callers-output.
  - Finding 3 (MEDIUM), the row that did not prove the supervisor stays. The supervisor now writes
    one more line, staying, from inside its wait: true when the pidfd of every holder is open and its
    first sleep is about to begin, false when it had nothing to sleep on. The wrapper reads to that
    line, or to the end of the supervisor's lines, and reports it. This is a read of the supervisor,
    bounded by the supervisor's own next pass over the process table, and not a wait for what the
    command left. Row fix2/returns-at-the-commands-exit requires that word and reads rule 3 only
    after it; fix2/end-follows-their-exit reads rule 3 once more just before the suite lets the
    process end. Falsifier space313-supervisor-does-not-stay (the supervisor returns where it should
    wait) writes no such line and is red on the first of the two. A supervisor that writes the line
    and then leaves is not registered: no read of rule 3 right after the line tells it apart without
    a timer.
  - The house's group. fix3/the-house-group is split, as the re-review asked. What does not depend
    on a run's end is in a suite of its own, scripts/suites/152_veldo_0313_house_group.py, which
    needs no ledger and places no hold: the command runs in the scope named for the run in the
    slice of wrapped runs, a process it left is listed in that group and named as a holder, a record
    that is not the run's scope is a group nobody read, and the group is read empty once the process
    has gone. It was seen green on this host, with the manager. Suite 151 keeps the part that needs
    the end (run finished after the group is empty); in the confinement it stands down as before,
    and unconfined on a shared host it stays red until the reader reads the label.
  - WHY A SUITE OF ITS OWN, AND WHAT NEEDS THE OWNER. The gate's unconfined list can name rows of a
    suite, but the mutation stage refuses every case of a suite listed for some rows
    (check_gate_mutations, rows_scoped_unconfined_case), and suite 151 has 31 cases. So the checks
    are a suite listed whole. That adds one entry to scripts/gate_unconfined.json, which is a
    protected path and the owner's decision, and moves two pinned counts in VELDO-0208's suite
    (scripts/suites/101_veldo_0208_landing_reuse.py: the suites listed whole, 46 to 47, in row
    unconfined-leg/declared-list, and all entries, 48 to 49, in row
    unconfined-leg/dispatcher-is-protected; the second was found by running the suite and is in
    the commit of the proof bundle). Both rows were then seen green. Three other rows of that suite
    were red in the same run and read nothing this round changed (proof/VELDO-0313/suite-green.txt
    names them). The edits are in this change on the lead's word and are outside what this ticket could decide: the
    gate reads the list from the authority checkout, so the entry takes effect only when the owner
    approves it there. The footprint names both files for that reason.
  - The suite. Suite 151 has 24 rows, all green in a process table of its own. Finding 313 has 31
    cases.
- 2026-11-14: THE READER'S LABEL DECIDES (with VELDO-0344's change of the same day, which makes the
  process reader read the run label of every task). In _space_holders the reader is asked again, only
  when a process is unread, and of its block only the label is used: with the reader's state used, a
  block that is whole, has the start time the kernel shows and has a label that was read, a process
  whose label is this run's is a holder by its label (the reason is label_carried), and one whose
  label is another run's or none is no holder, and rule 4 judges it by the files it holds. A block
  with no label read, no block, a block that is not whole, one with another start time and a reader
  that is absent or refused take nothing out: the process holds. Row fix3/unread-process-holds reads
  each of those, then this run's label, then a label of another run beside a process with none, where
  the run is over while both live. Falsifiers: space313-reader-block-taken-as-label-read is now one
  line (a label that was not read taken as none); space313-reader-block-not-checked and
  space313-reader-not-used-taken-as-used are back on the new lines; and
  space313-readers-label-of-the-run-not-counted is new. Finding 313 has 34 cases. On a host with no
  reader installed nothing changes: an unread process that started after the run holds it.
- 2026-11-15: AN ENVIRONMENT IS READ WHOLE OR NOT AT ALL (the review of VELDO-0344's run label,
  findings 1 and 2). Owner rule (Telegram 41209): no work is ever lost.
  - Finding 1, in the CLI's own scan. _space_holders read a process's environ once and took whatever
    came back as its environment. The kernel returns nothing for a process that is executing a
    program, so a process that carries the run's label could be read as carrying none and the run
    could end while it lived. The scan now reads through _space_environment: what the process is
    (start time, the two ends of the environment, its program's device and inode) is taken before the
    read and after it, and the read counts only when the two agree, at least one byte came back, and
    exactly as many as the ends are apart. It is made once more otherwise, and a process whose
    environment was not read whole is unread: it holds the run, or the reader is asked. An
    environment of no bytes is never whole, so a process that really has none is unread and holds.
  - Row fix3/environment-not-whole-holds: a process that carries the run's label and executes itself
    again without end is a holder in each of 150 reads, by its label or unread, never missing; a
    process with an environment of no bytes is unread; one with an environment and no label is no
    holder. Falsifiers: space313-environment-taken-as-it-was-read (the scan as it was) and
    space313-empty-environment-taken-as-read. Suite 151 has 25 rows; finding 313 has 36 cases. The
    comparison of the read's length alone has no falsifier in this suite: the row makes no
    environment that ends early (suite 141's reader/whole-read does, for the reader).
  - Finding 2, AN ACCEPTED LIMIT: A LABEL IS WHAT THE ENVIRONMENT AREA SAYS NOW. A process that
    overwrites its own environment area (programs that set their process title that way: database
    backends, web server workers) reads as carrying no label, by this account's own read and, since
    VELDO-0344's change of 2026-11-14, by the reader's for every uid. Nothing in /proc says whether
    the area is as the execution left it, so the rule cannot tell. THE LIMIT AFFECTS ONLY WHEN RUN
    FINISHED IS SENT, NEVER WHETHER AN ITEM IN USE IS REMOVED. When such a process is also outside
    the run's tree and outside its containment group, nothing shows it as the run's, and run
    finished is sent while it lives. Every removal that follows still passes the rule that reads
    what processes hold (rule 4 of the probe, process_use in Signal), and that rule reads no
    label: it takes the working directory, the open files and the mappings of every process, by
    path for a process this account can read and by inode through the process reader for one it
    cannot, and an item one of them holds is deferred as in use and stays on disk. An item of the
    run that no process holds is removed then, as it is for any run that is over. Proved by rows
    on 2026-11-15, below. The answer for a daemon a run starts is still the house's group, not the
    label. Rewritten on 2026-11-15 after the proof; the line before it said only that such a
    process is held by a file of an item.
- 2026-11-15: THE PROOF OF THAT CHANGE. Case space313-label-not-read moved with the line it changes
  (the scan's read through _space_environment). On the tree of d2e00c364f52 the registered driver,
  every worker confined: registered 36, executed 36, rejected 36. Suite 151 in the gate's
  confinement: 25 rows, 51 passed, 0 failed.
- 2026-11-15: THE ACCEPTED LIMIT PUT TO THE PROOF, AND THE COMPARISON OF WHAT A PROCESS IS (the
  review of VELDO-0344's fix, finding 1, and the lead's claim about finding 2 of the review before).
  Suite 151 only, with one registered case; bin/veldo is not changed.
  - The lead's claim: a process that rewrites its environment area can lose its label, but removal
    of any item still passes the in-use rule, which needs no label. HOLDS, both rows green:
    - fix3/rewritten-environment-cwd-in-scratch. A server that ran before the run starts a worker
      for the command with the run's label; the worker writes over its own environment area and
      changes its working directory to the run's scratch root. It is the server's child, no
      descendant of the supervisor, in no group, and the kernel shows no label: it is no holder, and
      run finished is sent while it lives (the limit). The scratch root is NOT removed: its item is
      deferred, rule in_use, refused by process_use, the deferral names the worker alone by its
      working directory, and the folder and its file are on disk.
    - fix3/rewritten-environment-open-file-in-worktree. The same worker with a file open in the
      build folder the command made in the run's worktree, which is the run's build output item
      there. The build folder is NOT removed: deferred, in_use, process_use, the worker named by its
      open file, the file on disk whole; the probe names the worker for the worktree itself as well.
      The scratch root of that run, which the worker does not hold, is removed by the same judge.
    In both rows rule 4 reads a table that holds the kernel's own entry of the worker and of no
    other process, through a link. On the whole table of the gate's confinement, and of a shared
    host, there are processes this account cannot read in full, and each alone defers every item
    (seen while the rows were written: the scratch root of the second row stayed, for eight such
    processes), so a row on the whole table would keep its item whatever the worker held. The
    reader's half of the claim is suite 141's row reader/rewritten-environment (VELDO-0344): the
    built reader writes l - for such a process and its block is whole and names the working
    directory and the open file by inode.
    NOT SHOWN: a process of another uid read through an installed reader; this host has none.
  - fix3/same-program-holds, with case space313-identity-not-compared (before == after taken as
    true, the other two conditions in place). A process made by posix_spawn shares its parent's
    memory until it executes; the row holds it in the open of a fifo, one of posix_spawn's own file
    actions, and lets it go on from inside the scan's open of its environ entry. The read then
    returns the parent's environment, which has no label and is as long as the ends taken before
    are apart. The scan reads once more and the process holds the run by its label. With the case
    applied the process is no holder: red, seen in the registered driver's confined worker; the
    no-op copy green. The line of 2026-11-15 above that says the comparison has no falsifier was
    about the length; the comparison of what the process is had none either until this row.
  - Suite 151 has 28 rows; finding 313 has 37 cases.
