---
schema: veldo.spec/v1
id: VELDO-0295
title: Veldo records everything it creates on disk and in Docker, removes each thing at the event that ends it, and admits a run only when the space it needs is free
status: draft
risk: high
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0036, VELDO-0039, VELDO-0041, VELDO-0042, VELDO-0057, VELDO-0068, VELDO-0107, VELDO-0133, VELDO-0145, VELDO-0158, VELDO-0220]
placement: [engine, loop]
protected_paths: []
footprint:
  - "specs/VELDO-0295-veldo-records-what-it-creates-and-removes-it-at-the-event-that-ends-it.md"
  - "docs/design/VELDO-0295-design.md"
  - "specs/index.md"
behavior_bearing: true
observability:
  logs: >
    Every ledger change is one journal record: an item declared, confirmed present, measured, made due by
    an event, removed, deferred or reported. A removal records the event that caused it, the method used,
    the item's size just before, and the pool's free space before and after. A deferral records the first
    safety rule that refused, by name, and the event that will retry it. Paths and object names are
    recorded; file contents never are.
  metrics: >
    Per pool: capacity, free, floor, held by admitted runs. Per project, ticket and kind: items present and
    their measured bytes, items pending removal by reason, bytes removed. Per reconcile: things found,
    matched, adopted, reported and missing. Admissions: admitted, queued by reason, environment failures.
  traces: >
    Every item carries its owner: project, ticket, run, gate and lane where each applies. A removal joins
    the item to the event and to the process that emitted it, so "what did landing this ticket free" is
    one read.
  error_taxonomy: >
    A removal that a safety rule refuses is a deferral, never an error: space_deferred:in_use,
    space_deferred:unique_work, space_deferred:protected, space_deferred:not_in_ledger,
    space_deferred:remove_refused. A run that cannot be admitted waits as space_wait:<pool>. A run or gate
    that ended on a full pool is environment_failure:no_space, in the unavailable_service class, and is
    never a red verdict. A creator that cannot reach the ledger refuses as
    unavailable_service:space_ledger before it creates anything.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: everything a Veldo process creates on disk or in Docker has a ledger record before it exists,
      and everything an agent's own commands create inside a run has one at the run's next event. A thing
      made by a process Veldo does not start (a worktree added with plain git, a gate run from a shell, a
      lead session, a builder started by a script) is recorded by a hook or a wrapper that runs inside
      that process, never by an instruction someone has to remember. Set: the kinds are worktree, branch,
      agent repository (the private repository the sandbox makes for one agent), build output (a folder
      of any name), scratch folder, log and evidence folder, container, volume, network and image tag.
      Each record names its owner, its kind, its path or object id, its pool, and the events that end
      it. The owner is a project, a plain repository the installation names, or no project for the
      scratch of a session started outside every project; the ticket, run, gate, lane and session are
      added where they apply. The set of creation points in Veldo's own code is complete by a gate check that
      refuses a creation primitive outside the ledger's seam. Rows: one run that makes a worktree, a
      branch, a build folder with an unusual name, a scratch folder, a container, a volume, a network and
      an image tag leaves eight records with the right owner and kind; a worktree added with plain git has
      a record when the git command returns; a session started in a folder that belongs to no project
      has its scratch recorded under the owner no project; a creator inside Veldo that cannot reach the
      ledger creates nothing.
    falsified_by: >
      Record build output by the folder name "target" only; the row's unusually named build folder has no
      record and the row fails.
  - id: AC2
    text: >
      Claim: each kind has a lifecycle table, and removal happens at the event. A run, a gate and a
      landing station remove in their own process before they report themselves finished. A git hook and
      a session hook only record their event and return; the authority service consumes the record as
      soon as it is written and removes what it ended. Set: the events are run finished, verdict
      recorded, branch landed, branch contained in the trunk, a landing ref or another branch, ticket
      ended (the authority's existing transitions: the item's complete or cancel, the unit's disposal,
      the VELDO-0133 close), project ended (the project's cancel or complete), worktree abandoned and
      session ended. A landing made by hand with plain git is recorded by a git hook, and the hook
      removes nothing inside the git command. A branch that has not moved past the commit it started at
      is never contained, and a worktree follows the branch checked out in it now. Build output and
      scratch go when their run finishes or its verdict is recorded;
      a worktree goes by git's own non-forced remove when its branch has landed or is contained; evidence
      is kept and only its caches are dropped; a branch is kept. A detached worktree added inside a
      wrapped run belongs to that run and goes at its run finished. No timer, schedule or age threshold
      triggers a removal: nothing in Veldo removes by age, with a central installation or without one,
      the sandbox's stale scratch pass and the gate's leg-time store included. Rows: after a gate records
      its verdict its build folder is gone and its evidence
      folder is present before the gate process exits; after a landing the worktree is gone and the branch
      is present; after a commit made by hand on a declared landing ref, the git command returns with
      the landing recorded and nothing removed, and the worktree of a branch that commit contains is
      gone after the service consumes the record, with the clock stopped and no timer; with the clock
      moved forward 30 days and no event, nothing is removed; a sandbox scratch folder two days old
      whose lock is free is still there after a launcher starts, with an installation and without one.
    falsified_by: >
      Remove build output from a pass that runs on a schedule; the row that checks the folder is gone
      before the gate process exits finds it present and fails.
  - id: AC3
    text: >
      Claim: nothing in use, nothing with uncommitted or unique work, nothing outside the ledger and
      nothing on the protect list is ever removed. Set: in use means a process has its working directory,
      an open file or a mapped file beneath the path, a container mounts it, or its owning run or session
      is live; unique
      work means a tracked change, an untracked file git does not ignore, or a commit no other branch,
      landed receipt or trunk contains; the protect list is read from the installation and from the
      project. A refused item is deferred with the rule's name, retried at its next event, and listed on
      the console. No removal passes a tool's force option, and every removal path that exists today goes
      through these rules. A worktree with unique work at its ticket's end raises one decision request
      to the owner with three answers: save as a commit on a kept branch, keep, or discard. Veldo never
      commits on its own. The three answers are offered as picks of the existing settlement path, so its
      set of rulings does not change. Discard is the one forced removal, allowed only after the owner's
      discard answer, and it keeps the branch. The protect list always holds the container engine's disk image
      and its folder, database volumes with real data and images that cannot be pulled again, and
      nothing on it is removed by any event or any answer. Rows: a build folder with a process's working directory inside it, a worktree with an
      uncommitted edit, a worktree whose branch has a commit nothing else contains, a folder with no
      ledger record and a protected volume each survive their ending event, each with its own reason; the
      build folder is removed at the next event after the process exits.
    falsified_by: >
      Check the working directory only and not open files; the row whose process holds an open file in the
      build folder finds the folder removed and fails.
  - id: AC4
    text: >
      Claim: at service start and on demand Veldo takes a snapshot of the known roots and of each Docker
      engine, subscribes to their events, and reconciles the snapshot with the ledger. Set: the roots are
      each bound repository's own list of worktrees, each agent repository's own list, each project's
      worktree root, the worktree roots of the plain repositories the installation names, the state
      root, the scratch roots and the build roots the installation names; the engines are the contexts the
      installation names. A thing with a record is matched; a record with no thing is marked gone; a thing
      with no record is adopted when a stated rule proves its owner, and reported otherwise. Reconcile
      itself removes nothing that was not already due. Rows: a planted worktree on a ticket branch is
      adopted with that ticket as owner; a planted folder with no provable owner is reported and left; a
      record whose folder was deleted by hand is marked gone.
    falsified_by: >
      Adopt every folder found under a root; the planted folder with no provable owner gets a record and
      an owner, and the row that expects a report fails.
  - id: AC5
    text: >
      Claim: a run or gate states the space it needs per pool and starts only when the pool's free space
      covers that need, the needs already held by admitted runs, and the pool's floor. Otherwise it waits,
      with the numbers that refused it shown, and is judged again only after a write that frees space:
      a removal that finished, or a run that ended and gave back its hold. A pass woken by a timer does
      nothing for it. A dispatch is asked before it is prepared, so a waiting unit holds no slot and has no
      deadline. A gate is asked by the gate script itself, with or without a host
      configuration. A repository initialized after the change has the steps from the template; an
      existing project's gate script is its own file and gets them by its own change, reconcile reports
      a project whose gate lacks them, and until then its gates run through the run wrapper, which
      admits them and removes their build output. Report or act is set per project. In report mode
      admission advises ("would wait") and does not block; it blocks only in act mode. A run or gate that
      ends on a full pool is recorded as an environment failure and is
      queued again behind admission; it never records a red verdict. Rows: with free space under need plus
      floor the run waits and the console shows need, free, held and floor; after a removal frees enough
      it starts with no other action; a gate whose build fails with the system's no-space error on a pool
      under its floor records environment_failure:no_space and no verdict; a waiting unit offered on
      three passes, one of them woken by the account-reset timer, causes one retry of the pool's
      deferred items.
    falsified_by: >
      Compare free space with the need alone and ignore the floor; the row with free space between need
      and need plus floor starts the run and fails.
  - id: AC6
    text: >
      Claim: the console shows space by project, by ticket and by kind, what is pending removal with its
      reason, what was removed with the event that removed it, and what reconcile reported. Set: every
      figure is read from ledger records; a size is the last measurement and names the event it was
      measured at. Rows: the screen's totals equal the sum of the fixture's records per project, ticket and
      kind; a deferred item shows its reason and its next retry event; a removed item shows its event, its
      size and the pool's free space before and after.
    falsified_by: >
      Drop deferred items from the pending list; the row that expects the in-use build folder with its
      reason finds nothing and fails.
  - id: AC7
    text: >
      Claim: space management works for every project the installation manages, from the project's own
      declaration, and the generic documents name no project. Set: a project declares its worktree root,
      its build output rules, its needs per station and its protect entries in one file that init lays
      down; a project with no file gets the defaults and is still recorded, reconciled and admitted. Rows:
      two fixture projects with different build tools and different worktree roots each have their items
      recorded and removed by the same code; a project with no declaration is reconciled and its build
      output found; the docs check passes on the changed documents.
    falsified_by: >
      Read the worktree root from a constant; the second fixture project's worktrees are not found by
      reconcile and its row fails.
  - id: AC8
    text: >
      Claim: the things that exist today are adopted into the ledger without removing anything, and the
      nightly cleanup script is retired only after the events cover each of its cases. Set: every
      project starts in report mode; what Veldo would remove is listed as pending and is removed only
      after the owner confirms it per project and kind, and the owner can mark a proposal wrong. A
      project goes to act mode by the owner's signed command, which the ledger refuses until that
      project has three consecutive report-mode days, each with activity and with no proposal marked
      wrong; a mark starts the count again. The order is core first: core's gate script gets the space
      steps while core is in report mode, core goes to act after its three clean days, and each other
      project follows the same way. The three days are read from the records when the owner acts; no
      timer counts them. The nightly script's five candidate
      classes (build folders in worktrees, named build folders, build folders under the session scratch
      root, per-session scratch folders, build caches under the user's cache folder) each map to a kind
      and an event; while both run the script asks the ledger and skips what a safety rule kept; and the script's schedule entry is removed
      only when a listing of its candidates on the live host, with its age and size tests off, holds
      nothing the ledger does not already hold. Rows: a
      first reconcile over a fixture with 20 worktrees removes nothing and lists the due items; after the
      owner's confirmation exactly those are removed; the switch to act is refused for a project with a
      proposal marked wrong on the second of its three days; the retirement check fails while one
      candidate class has no ledger kind.
    falsified_by: >
      Let the first reconcile act on what it finds due; the row that expects nothing removed before the
      owner's confirmation fails.
required_evidence: [unit, integration]
rollback: >
  This spec adds two documents and removes nothing. The build tickets it names each carry their own
  rollback. For the capability as a whole: switch space management off in the installation, which stops
  every removal and every admission check and leaves the ledger readable; the nightly script stays
  installed until VELDO-0321 retires it, so switching off returns the host to today's behavior.
---

## Intent

Veldo makes worktrees, branches, build folders, scratch folders, logs, containers, volumes, networks and
image tags, and today nothing in Veldo knows which of them still matter. The disk fills, a run dies with
its work uncommitted, a gate goes red for a reason that has nothing to do with the change, and someone
cleans up by hand or a nightly script deletes by age. The owner asked for the opposite (Telegram 41152):
keep track of what is created, changed and merged, and make cleanup part of the process.

So Veldo keeps a ledger. A thing is recorded when it is made, with who it belongs to and which event ends
it. When that event happens, the process that emits it removes the thing, unless a safety rule says no, in
which case the thing waits for its next event and shows on the console with the reason. A run declares the
space it needs and waits when the disk cannot cover it.

## Context

- The design is docs/design/VELDO-0295-design.md. It holds the components, the data model, the lifecycle
  table, the event sources outside the service, the table of existing removal paths, the flows, the
  deployment view and the forty-three build tickets, VELDO-0296 to VELDO-0338.
- VELDO-0042 already retires a worker clone only after every user of it has ended, read from the kernel.
  VELDO-0041 already retries a refused retirement when the obligation it waits on completes. Space
  management uses the same two ideas for every kind.
- VELDO-0220 already has a gate answer that is not a verdict: NOT STARTED, exit 75. Admission and the
  no-space failure use it.
- VELDO-0036 reserves capacity and usage in the store before a run starts. A space hold is a record of
  the same store and is checked just before that reservation is made.
- VELDO-0068 already settles a request to the owner once, with a typed effect per answer. The owner's
  answer on a worktree with unique work is one more touchpoint of that service, and its three answers
  use the pick form that service already has.
- VELDO-0107 already gives a local process an authenticated way to reach the authority. The hooks use
  it, signed by a host principal and never by the owner's key.
- VELDO-0158 already removes a run's own directory once the kernel shows the run gone. That removal moves
  behind the safety rules with every other one.
- Two places in the engine remove by age today: the sandbox's pass over stale scratch
  (engine/scripts/agent_sandbox.py) and the 30-day branch of the gate's leg-time store
  (engine/scripts/gate_legs.py). Both go.
- The protect list always holds the container engine's disk image and its folder, database volumes with
  real data, and images that cannot be pulled again. Nothing on it is ever removed by Veldo.

## Out of scope

- No removal of anything Veldo did not create or adopt. Databases, data volumes and images that cannot be
  pulled again are never candidates, whatever their size.
- No pruning command of any tool. Every removal names one recorded thing.
- No removal by age anywhere in Veldo, with or without a central installation.
- No removal of unlabelled Docker objects in the first release. They are reported.
- No "superseded" transition. The authority has none today; the events use the transitions that exist.
- No action on a container engine's own disk image file.
- No deletion of branches. A contained branch is marked and kept.
- No build in this spec. It is the design's contract; each build ticket becomes its own spec.

## What the reviewer judges

Whether the design can be built from the document alone, whether every removal path passes through the
safety rules in section 7 of the design, and whether any mechanism in it is a timer under another name.

## History

- 2026-11-13: drafted with the design (commits 2bc5fc06 and 1b1a26de), from the owner's request Telegram
  41152.
- 2026-11-13: amended from design revision 2, which follows the validation of the same day (verdict
  CHANGES, B1 to B6 and M1 to M9) and the lead's decisions on its four open questions. AC1: the agent
  repository kind, and things made outside Veldo recorded by a hook or wrapper. AC2: the events named
  after the transitions that exist, session ended, contained through a git hook, the start commit rule.
  AC3: mapped files, no force, every existing removal path behind the rules, the owner's decision on
  unique work. AC4: agent repositories and plain repositories among the roots. AC5: admission before a
  dispatch is prepared, in the gate script for every repository, advising only in report mode. AC8: five
  classes, not four. Tickets renumbered VELDO-0296 to VELDO-0322. Still a draft.
- 2026-11-13: amended from design revision 3, which follows the second validation of the same day
  (verdict CHANGES, R1 to R4 and S1 to S11) and carries the lead's decisions. AC1: the owner may be no
  project for a session outside every project; the row leaves eight records, not nine. AC2: a hand
  landing is recorded by the git hook and removed by the authority service right after, never inside
  the git command; a worktree follows the branch checked out in it. AC3: discard is the one forced
  removal, only after the owner's discard answer, and keeps the branch; the protect list's standing
  entries. AC5: an existing project's gate gets the space steps by its own change, is reported until
  then, and is covered by the run wrapper. Tickets VELDO-0323 to VELDO-0330 added, so the range is
  VELDO-0296 to VELDO-0330. Still a draft.
- 2026-11-13: amended from design revision 4, which follows the third validation of the same day
  (verdict CHANGES, C1 to C6 and D1 to D7) and carries the lead's decisions. AC2: no removal by age
  anywhere in Veldo, with or without an installation; a detached worktree made inside a wrapped run
  belongs to the run. AC3: the three answers are picks of the existing settlement path. AC5: a waiting
  unit is judged again only after a write that frees space, never on a timer-woken pass; report or act
  is per project. AC8: per-project report then act, the three clean days, core first; the retirement
  check runs with the script's age and size tests off. Tickets VELDO-0331 to VELDO-0338 added, so the
  range is VELDO-0296 to VELDO-0338. Still a draft.
