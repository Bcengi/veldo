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
    space_deferred:remove_refused, and space_deferred:keep_failed when an item's commits or its
    uncommitted state could not be saved first. A run that cannot be admitted waits as
    space_wait:<pool>. A run or gate
    that ended on a full pool is environment_failure:no_space, in the unavailable_service class, and is
    never a red verdict. A creator that cannot reach the ledger refuses as
    unavailable_service:space_ledger before it creates anything.
acceptance_criteria:
  - id: AC0
    text: >
      Claim: no work is ever lost. Space management never removes the only copy of work: before a removal
      it saves the work where the owner can get it back with one command, and when it cannot save it, it
      does not remove. This is the first requirement, and every other criterion is read under it. Set:
      work is a commit no kept ref holds, an uncommitted change, an untracked file (an ignored one
      included, unless a committed ignore rule or a declared pattern of the project makes it build
      output), a stash, an unpushed branch or tag, an evidence or proof file, and anything the owner
      marked Keep. Before a worktree, a branch or a private repository (an agent repository, a worker
      clone, a batch clone, a candidate workspace) is removed, every commit reachable from it, the ones
      only a log or a stash names included, is recorded on a kept ref refs/veldo/kept/<ticket>/<item> in
      its main repository and read back, and the removal is refused as keep_failed when that write fails.
      A kept ref stays until the owner drops it with a signed command, and it is never counted as a reason
      to remove. Uncommitted, untracked and stashed changes are never removed without the owner's explicit
      Discard. Discard first saves them as a snapshot outside git, plain files with a manifest under the
      state root and never an object in a repository, and runs only while the worktree still equals what
      was saved; a review's scratch, and a dead run's worker clone, are saved the same way before they
      are removed. An evidence file is removed only when a copy with the same digest, read again at the
      removal, is held by the store or by a commit the trunk or a kept ref reaches. Every probe and every
      rule fails closed: what cannot be read, written or decided keeps the item. The owner gets a removed
      item's work back with veldo space restore, or with plain git from the kept refs. A suite that plants
      each kind of work, nested, linked, locked, unreadable, changed mid-removal and with the process
      killed between steps, and drives every removal path at it, must pass, in the gate and on the host
      for the space modules and the git in use, before any project can be switched to act. Rows: after
      every removal path each planted commit is reachable from a ref of the main repository; a commit that
      only a detached worktree's HEAD log named is on a kept ref after the worktree is gone; after Discard
      and restore the tracked edit, the staged file, the untracked file and the ignored settings file are
      back byte for byte; with the main repository's refs unwritable the worktree is still there, deferred
      as keep_failed; a worker clone with a commit the runner never brought across leaves that commit in
      the main repository; a repository with an unpushed commit in a session's scratch keeps that scratch;
      a process killed between the kept refs and the remove loses nothing after reconcile; the switch to
      act is refused with no proof record for the modules in use.
    falsified_by: >
      Remove a worktree before its kept refs are written; the row that kills the process between the two
      finds the commit its HEAD log named in no ref and fails.
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
      wrapped run belongs to that run and goes at its run finished. When that run is a review, the
      untracked files git does not ignore in the worktree are review scratch and go with it, with no
      decision request and no force option. No timer, schedule or age threshold
      triggers a removal: nothing in Veldo removes by age, with a central installation or without one,
      the sandbox's stale scratch pass and the gate's leg-time store included. Rows: after a gate records
      its verdict its build folder is gone and its evidence
      folder is present before the gate process exits; after a landing the worktree is gone and the branch
      is present; after a commit made by hand on a declared landing ref, the git command returns with
      the landing recorded and nothing removed, and the worktree of a branch that commit contains is
      gone after the service consumes the record, with the clock stopped and no timer; with the clock
      moved forward 30 days and no event, nothing is removed; a sandbox scratch folder two days old
      whose lock is free is still there after a launcher starts, with an installation and without one;
      a review worktree with a stray untracked file is gone after the review's run finished, and no
      request was raised for it.
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
      discard answer, and it keeps every commit: the branch stays, and a detached worktree's commits are
      put on a new kept branch at its HEAD before the worktree goes, so only uncommitted changes are
      lost. Review worktrees with tracked modifications never raise
      a request each: they share one grouped decision request per day, keyed by the day of the deferral
      and never opened or sent by the clock. One answer covers the whole group, and the request also
      allows a per-worktree answer. An answered group closes, and a deferral later that day opens a new
      group with its own request. The protect list always holds the container engine's disk
      image and its folder, every database volume with real data, a protected project's containers and
      images, and images that cannot be pulled again. A Docker object is matched by its name or by its
      compose project label, either one, on every engine the installation names. Nothing on the list is
      removed in any mode, by any event or any answer, and nothing on it is ever proposed for removal.
      Rows: a build folder with a process's working directory inside it, a worktree with an
      uncommitted edit, a worktree whose branch has a commit nothing else contains, a folder with no
      ledger record and a protected volume each survive their ending event, each with its own reason; the
      build folder is removed at the next event after the process exits; two review worktrees with
      tracked edits on one day raise one request; in a group of three the answer accept discard w2
      discards only member 2; a worktree deferred after the day's group was answered gets a new
      request; a detached worktree's commit is on a kept branch after Discard; a protected container matched only by its compose
      label has no record and no proposal on either engine.
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
      wrong; a mark starts the count again. The ledger also refuses the command while the project has
      a pending group the owner has neither confirmed nor marked wrong, and while the project's gate
      script lacks the space steps. The order is core first: core's gate script gets the space
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
      proposal marked wrong on the second of its three days; it is refused for a project with three
      clean days and one unconfirmed group, and accepted after that group is confirmed; the retirement
      check fails while one
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

The first requirement is the owner's (Telegram 41209): "It's very important no work is ever lost. Space
management needs to ensure this very clearly". Everything below removes things to free space. None of it
may remove the only copy of work: a removal saves the work first, where the owner can get it back with one
command, or it does not happen. AC0 states it, and section 0 of the design says how.

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

- Section 0 of the design is the rule that no work is ever lost: what work is, the kept refs under
  refs/veldo/kept in each main repository, the snapshot Discard saves first, the recovery commands, the
  suite that must pass before act mode, and the list of tickets the rule changes. Four tickets were added
  for it, VELDO-0345 to VELDO-0348, and VELDO-0344, the process reader, was added before them.
- The design is docs/design/VELDO-0295-design.md. It holds the components, the data model, the lifecycle
  table, the event sources outside the service, the table of existing removal paths, the flows, the
  deployment view and the forty-eight build tickets, VELDO-0296 to VELDO-0343.
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
  real data, a protected project's containers and images, and images that cannot be pulled again. An
  object is matched by name or by compose project label on every engine. Nothing on it is ever proposed
  or removed by Veldo, in any mode.

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

## Build order

The order of section 12 of the design. Each ticket is its own spec, specs/VELDO-0296 to
specs/VELDO-0348.

1. 0296, 0338, 0297, 0326, 0331.
2. 0298, 0299, 0330 and 0300 together.
3. 0301, then 0345 (the keep step), then 0344 (the process reader).
4. 0302, 0303 and 0305 to 0314 with 0323, 0324, 0328, 0329, 0333, 0335, 0336, 0337 and 0341, in any
   order.
5. 0347, then 0304.
6. 0315, 0316, 0334, 0317, 0327, 0318, 0343, 0340, 0342, 0319, 0346, 0320, 0332, 0325, 0339, 0321, 0322.
7. 0348, the no-work-is-lost suite. Until it lands and has passed on the host, no project can be
   switched to act.

0304, the boundary check, comes after 0302, 0303, 0324 and 0333 on purpose. Until those four have landed,
the paths in the Replaced table of section 6.10 still hold removal primitives and the two removals by
age, and the check would turn the gate red on its first run.

Tickets that touch protected paths and need the owner's recorded approval: 0302 and 0324 (the sandbox),
0309 (the gate script template, and the new helper added to the protected list), 0304 (its check is
called from scripts/verify.sh) and 0333 (the gate's leg timing). 0325 produces a change to the gate
script of each bound project, approved by the owner in that project.

A ticket's depends_on holds the dependencies the design states for it. Where the design states none, it
holds the step before the ticket in this order, so that a ticket cannot be claimed ahead of the order.

## What the reviewer judges

First, whether any path in the design can remove work that was not saved first (section 0, AC0). Then
whether the design can be built from the document alone, whether every removal path passes through the
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
- 2026-11-13: amended from design revision 5, which follows the fourth validation of the same day
  (verdict CHANGES, E1 to E3 and F1 to F6) and carries the lead's decisions (d) and (e) and the complete
  protect list. AC2: a review worktree's stray untracked files are review scratch and go with it at the
  review's end, with no request and no force option. AC3: tracked modifications in review worktrees
  share one grouped decision request per day; the protect list names a protected project's containers
  and images, matches by name or by compose label on every engine, and nothing on it is proposed or
  removed in any mode. AC8: the switch to act is also refused while a pending group is unconfirmed and
  while the project's gate script lacks the space steps. Tickets VELDO-0339 to VELDO-0341 added, so the
  range is VELDO-0296 to VELDO-0341. Still a draft.
- 2026-11-13: amended from design revision 6, which follows the fifth validation of the same day
  (verdict CHANGES, G1 to G4) and carries the lead's decisions (f), (g) and (h). AC3: one answer covers
  a day's review group and the request also allows a per-worktree answer; an answered group closes and
  a deferral later that day opens a new one; Discard keeps every commit, a detached worktree's on a new
  kept branch at its HEAD, and loses only uncommitted changes. Tickets VELDO-0342 and VELDO-0343 added,
  so the range is VELDO-0296 to VELDO-0343. Still a draft.
- 2026-11-13: the sixth validation of the design returned VALID. The forty-eight ticket specs,
  VELDO-0296 to VELDO-0343, were written from design revision 6, and the build order of section 12 was
  added here. One citation in section 7 of the design was corrected from that validation's note N2.
  Still a draft.
- 2026-11-13: the owner's rule (Telegram 41209): "It's very important no work is ever lost. Space
  management needs to ensure this very clearly". Added as AC0, the first requirement, and as section 0 of
  the design. What it adds: every commit a worktree, a branch or a private repository reaches is recorded
  on a kept ref, refs/veldo/kept/<ticket>/<item>, in its main repository before the removal, which is
  refused when that write fails; Discard saves the uncommitted state on a kept ref first, so it can be
  undone; an ignored file that is not build output is work, and a clone is a private repository and not
  scratch; every probe and rule fails closed; the owner restores with veldo space restore or plain git;
  and a suite that plants work and drives every removal path must pass before any project goes to act. The
  error taxonomy gains space_deferred:keep_failed. Every ticket from VELDO-0296 to VELDO-0344 was read
  against the rule: the criteria of ten change (0302, 0304, 0305, 0315, 0318, 0322, 0327, 0336, 0340,
  0343), the eight built tickets keep theirs and carry a History note where the rule reaches their code,
  and four tickets are added, VELDO-0345 to VELDO-0348, numbered after 0344, the highest number a spec
  file or a proof folder held on any ref. The build order gains them and VELDO-0344. Six points are put to
  the owner in section 15 of the design. Still a draft.
- 2026-11-13: the lead answered the six questions section 15 of the design put about section 0, and design
  section 7.1 was revised after its validation (verdict CHANGES). AC0 changes in one place: a snapshot of
  uncommitted, untracked or ignored files is stored outside git, under the state root, so a secret in an
  ignored file never enters a repository's object store; a dead run's worker clone with uncommitted files
  is saved the same way and removed with no request. Review scratch, unlanded commits, session scratch and
  growth stay as designed, and the console shows the count and the size of kept refs and snapshots. The
  criteria of nine unbuilt tickets follow (0318, 0327, 0336, 0340, 0343, 0345, 0346, 0347, 0348 for one
  mutation). VELDO-0344 goes from five criteria to eight: the reader runs in a socket-started user unit of
  its own, reads every thread, is built from the approved commit against a digest the gate recorded, and
  is matched by inode number alone. One capability stays. Section 15 of the design is empty. Still a
  draft.
